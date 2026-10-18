#!/usr/bin/env python3
"""Audit readings and render explicit owner decisions; never ship links."""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
import yaml

from scripts.audit_workbook_lessons import Page
from scripts.build_workbook_research_review import ROOT, RESEARCH, csv_text, protected_hashes

PENDING = "PENDING_OWNER_APPROVAL"
APPROVED = "APPROVED_BY_OWNER"
OWNER_DECISIONS = RESEARCH / "modedex_external_owner_decisions.yaml"
# Network safety allowlist for this research only, NOT source-use approval.
RESEARCH_HOSTS = {"news.mit.edu", "www.ibm.com", "blog.optibus.com"}
FIELDS = {"name", "approval_status", "publisher", "article_title", "proposed_url",
          "relevant_topic", "match_rationale", "confidence", "scope_label",
          "why_workbooks_insufficient", "limitations", "verification_terms",
          "audience", "resource_type", "accessibility_reason"}


class ExternalPage(Page):
    """Read main content or the publishers' explicitly marked article sections."""

    def __init__(self):
        super().__init__()
        self.article_div_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            classes = dict(attrs).get("class", "").split()
            if (self.article_div_depth or "post-body" in classes
                    or any(c.startswith("body-article-") for c in classes)):
                self.article_div_depth += 1
        super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "div" and self.article_div_depth:
            self.article_div_depth -= 1
        super().handle_endtag(tag)

    def handle_data(self, data):
        if self.article_div_depth and not self.in_main and not self.skip:
            self.parts.append(data)
        super().handle_data(data)


def reference_scope(workbooks, canon, review):
    signatures = {key for key, row in canon["modemon"].items() if row["stage"] == 3}
    initial = {key for key, row in review["species"].items() if row["previous_outcome"] == "unresolved"}
    current = {key for key, row in workbooks["species"].items() if not row["primary_lesson"]}
    return {
        "policy": "Preserve every existing workbook match; outside research only for uncovered non-Signatures.",
        "initial_workbook_matches": len(canon["modemon"]) - len(initial),
        "initial_workbook_blanks": len(initial),
        "initial_blank_signature_ids": sorted(initial & signatures),
        "initial_blank_non_signature_ids": sorted(initial - signatures),
        "current_workbook_matches": len(canon["modemon"]) - len(current),
        "current_workbook_blanks": len(current),
        "current_blank_signature_ids": sorted(current & signatures),
        "outside_research_non_signature_ids": sorted(current - signatures),
        "non_signature_count": len(canon["modemon"]) - len(signatures),
        "non_signature_workbook_matches": len(set(canon["modemon"]) - signatures - current),
        "signature_count": len(signatures),
        "signature_policy": "Canonical real-project links are sufficient; no supplementary references proposed or researched.",
        "canonical_signature_project_sources": {
            key: canon["modemon"][key]["signature"]["source_url"] for key in sorted(signatures)},
    }


def read_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def check_external_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in RESEARCH_HOSTS
            or not parsed.path.strip("/") or parsed.username or parsed.password
            or parsed.port or parsed.query or parsed.fragment):
        raise ValueError(f"Not a precise research-authorized URL: {url}")


def load_inputs():
    return (read_yaml(RESEARCH / "modedex_external_proposals.yaml"),
            read_yaml(ROOT / "data/config/modedex_learning_links.yaml"),
            read_yaml(ROOT / "data/config/modedex.yaml"),
            read_yaml(RESEARCH / "workbook_component_review.yaml"))


def owner_decision_fields(data, ledger):
    """Bind human approval to an exact species/URL, independently of HTTP checks."""
    commit = ledger.get("reviewed_commit", "")
    if (ledger.get("version") != 1 or len(commit) != 40
            or any(c not in "0123456789abcdef" for c in commit)
            or not ledger.get("decision_source") or not ledger.get("policy")):
        raise ValueError("Owner decisions need source attribution and the reviewed commit")
    decisions = ledger["decisions"]
    if set(decisions) != set(data["proposals"]):
        raise ValueError("Owner decision ledger must cover exactly the four reviewed species")
    result = {}
    for key, row in decisions.items():
        if set(row) != {"decision", "reference_url", "note"} or not row["note"].strip():
            raise ValueError(f"Incomplete owner decision: {key}")
        check_external_url(row["reference_url"])
        if row["decision"] == "approved":
            if row["reference_url"] != data["proposals"][key]["proposed_url"]:
                raise ValueError(f"Changed URL cannot inherit owner approval: {key}")
            status = APPROVED
        elif row["decision"] == "held_for_replacement":
            status = ("HELD_FOR_REPLACEMENT" if row["reference_url"] == data["proposals"][key]["proposed_url"]
                      else PENDING)
        else:
            raise ValueError(f"Unknown owner decision: {key}")
        result[key] = {"approval_status": status, "owner_reviewed_commit": commit,
                       "owner_reviewed_url": row["reference_url"], "owner_decision_note": row["note"]}
    return result


def validate(data, workbooks, canon, review, evidence=None):
    if data["approval_status"] != PENDING:
        raise ValueError("Research cannot approve external references")
    gaps = set(reference_scope(workbooks, canon, review)["outside_research_non_signature_ids"])
    if any(key in canon["modemon"] and canon["modemon"][key]["stage"] == 3 for key in data["proposals"]):
        raise ValueError("Signature forms already have sufficient canonical project sources; no supplementary proposals")
    if set(data["proposals"]) != gaps:
        raise ValueError("External proposals must correspond exactly to uncovered non-Signature workbook gaps")
    if evidence is not None and set(evidence) != {row["proposed_url"] for row in data["proposals"].values()}:
        raise ValueError("External evidence must cover only the current non-Signature proposals")
    for key, row in data["proposals"].items():
        if row["approval_status"] != PENDING:
            raise ValueError(f"Every external proposal must remain {PENDING}: {key}")
        if set(row) - FIELDS:
            raise ValueError(f"Unexpected field could masquerade as approved mapping: {key}")
        for field in FIELDS - {"verification_terms"}:
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"Missing external review field {field}: {key}")
        if row["name"] != canon["modemon"][key]["name"] or workbooks["species"][key]["primary_lesson"]:
            raise ValueError(f"Must preserve canonical identity and unpopulated workbook gap: {key}")
        if row["confidence"] not in {"high", "medium", "low"}:
            raise ValueError(f"Invalid confidence: {key}")
        if (row["audience"] != "general_public_no_ml_prerequisites"
                or row["resource_type"] not in {"concept_overview", "plain_language_research_news"}):
            raise ValueError(f"Outside sources must explain the AI job for a general audience, not implementation: {key}")
        if not row.get("verification_terms") or not all(isinstance(t, str) and t.strip() for t in row["verification_terms"]):
            raise ValueError(f"Missing content checks: {key}")
        check_external_url(row["proposed_url"])
        if evidence is not None:
            item = evidence[row["proposed_url"]]
            if (item["approval_status"] != PENDING or item["http_status"] != 200
                    or item["article_title"] != row["article_title"]
                    or item["final_url"] != row["proposed_url"]
                    or not all(item["verification_terms_found"].get(t) for t in row["verification_terms"])
                    or len(item["content_sha256"]) != 64 or not item["verified_at_utc"]):
                raise ValueError(f"Invalid pending-source verification: {key}")


def get(url):
    check_external_url(url)
    response = requests.get(url, timeout=60, allow_redirects=False, headers={
        "User-Agent": "ModemonGO-LessonResearch/1.0 (+https://github.com/maladroitcat/modemon-go/issues/26)"})
    # An unexpected redirect needs a fresh human check, not a guessed replacement.
    if response.status_code != 200:
        raise ValueError(f"External research source returned {response.status_code}: {url}")
    return response


def verify(data, previous=None):
    evidence = {}
    for row in data["proposals"].values():
        url = row["proposed_url"]
        if url in evidence:
            continue
        if previous is not None and url in previous:
            evidence[url] = previous[url]
            continue
        time.sleep(.5)
        response = get(url)
        page = ExternalPage()
        page.feed(response.text)
        observed = [heading for tag, heading in page.headings if tag == "h1"]
        if row["article_title"] not in observed:
            raise ValueError(f"Actual article title mismatch: {url}; {observed}")
        text = " ".join(" ".join(page.parts).split())
        terms = {term: term.casefold() in text.casefold() for term in row["verification_terms"]}
        if not all(terms.values()) or len(text) < 300:
            raise ValueError(f"External lesson topic mismatch: {url}; {terms}")
        item = {"approval_status": PENDING, "article_title": row["article_title"],
                "observed_headings": observed, "http_status": response.status_code,
                "final_url": response.url, "media_type": "html",
                "verification_terms_found": terms, "content_sha256": hashlib.sha256(response.content).hexdigest(),
                "verified_at_utc": datetime.now(timezone.utc).isoformat()}
        evidence[url] = item
    return evidence


def render(root=RESEARCH):
    before = protected_hashes()
    data, workbooks, canon, review = load_inputs()
    evidence = json.loads((RESEARCH / "external_reference_verification.json").read_text(encoding="utf-8"))
    validate(data, workbooks, canon, review, evidence)
    decisions = owner_decision_fields(data, read_yaml(OWNER_DECISIONS))
    rows = [{"species_id": key, **row, **decisions[key]} for key, row in sorted(data["proposals"].items())]
    fields = list(dict.fromkeys(k for row in rows for k in row))
    root.mkdir(parents=True, exist_ok=True)
    (root / "modedex_external_owner_review.csv").write_text(csv_text(rows, fields), encoding="utf-8")
    lines = ["# Table B: Outside Readings and Owner Decisions", "",
             "Wardray, Shiftshark, and Parcelprawn are APPROVED_BY_OWNER for their exact educational references reviewed at 79dd9ce. Routeopus's replacement remains PENDING_OWNER_APPROVAL. The prior MIT trip-planning article was held as insufficiently direct. See [owner decision ledger](modedex_external_owner_decisions.yaml).", "",
             "Approval is recorded from explicit human decisions, never inferred from verification. No row populates a Modedex, workbook-mapping, or runtime link. This does not authorize UI integration, merging, or deployment.", "",
             "Only four uncovered non-Signatures need outside references. All 45 existing workbook matches are unchanged, including component-level matches. All 12 Signatures already have sufficient canonical real-project sources and receive no supplementary proposals. See [scope accounting](modedex_reference_scope.json).", "",
             "These public HTML articles explain what the AI-assisted job is, what it does, and where it is used; they are not implementation tutorials. Relevance and reading-level judgments remain reviewable.", "",
             "| Species | Status | Exact proposed title / URL | Publisher | Topic / rationale | Confidence / scope | General-audience suitability | Why workbook coverage was insufficient | Limits |", "|---|---|---|---|---|---|---|---|---|"]
    def esc(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    for r in rows:
        cells = [f'`{r["species_id"]}` ({r["name"]})', r["approval_status"],
                 f'[{r["article_title"]}]({r["proposed_url"]})', r["publisher"],
                 r["relevant_topic"] + ": " + r["match_rationale"],
                 r["confidence"] + ": " + r["scope_label"], r["accessibility_reason"],
                 r["why_workbooks_insufficient"], r["limitations"]]
        lines.append("| " + " | ".join(map(esc, cells)) + " |")
    lines += ["", "Confidence describes educational topic fit, not approval, clinical validity, production suitability, or proof of a Signature deployment. Source evidence is in external_reference_verification.json; existing Signature project URLs remain unchanged and separate.",
              "", "Owner decision needed: approve/reject the Routeopus replacement. The other three exact references already have approval. A future explicitly authorized change would be needed before readings enter the app. This renderer cannot grant approval, merge, or deploy.", ""]
    (root / "modedex_external_owner_review.md").write_text("\n".join(lines), encoding="utf-8")
    (root / "modedex_reference_scope.json").write_text(
        json.dumps(reference_scope(workbooks, canon, review), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if protected_hashes() != before:
        raise ValueError("Protected canonical input changed during external research rendering")
    approved = sum(row["approval_status"] == APPROVED for row in rows)
    print(f"Rendered {len(rows)} readings: {approved} explicitly owner-approved; {len(rows)-approved} awaiting approval; no app links written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    network = parser.add_mutually_exclusive_group()
    network.add_argument("--verify", action="store_true", help="Live audit of all four readings; does not approve anything")
    network.add_argument("--verify-new", action="store_true", help="Audit only uncached replacement URLs; preserve existing evidence")
    args = parser.parse_args()
    data, workbooks, canon, review = load_inputs()
    validate(data, workbooks, canon, review)
    if args.verify or args.verify_new:
        previous = (json.loads((RESEARCH / "external_reference_verification.json").read_text(encoding="utf-8"))
                    if args.verify_new else None)
        evidence = verify(data, previous)
        validate(data, workbooks, canon, review, evidence)
        (RESEARCH / "external_reference_verification.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render()
