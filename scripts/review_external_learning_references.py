#!/usr/bin/env python3
"""Verify/render pending external research, never add links to the app or canon."""
import argparse
import hashlib
import io
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
import yaml

from scripts.audit_workbook_lessons import Page
from scripts.build_workbook_research_review import ROOT, RESEARCH, csv_text, protected_hashes

PENDING = "PENDING_OWNER_APPROVAL"
# Network safety allowlist for this research only, NOT source-use approval.
RESEARCH_HOSTS = {"developers.google.com", "huggingface.co", "web.stanford.edu"}
FIELDS = {"name", "approval_status", "publisher", "article_title", "proposed_url",
          "relevant_topic", "match_rationale", "confidence", "scope_label",
          "why_workbooks_insufficient", "limitations", "verification_terms", "discovery_url"}


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


def validate(data, workbooks, canon, review, evidence=None):
    if data["approval_status"] != PENDING:
        raise ValueError("Research cannot approve external references")
    gaps = {k for k, r in review["species"].items() if r["outcome"] == "genuine_gap"}
    if set(data["proposals"]) != gaps:
        raise ValueError("External proposals must correspond exactly to genuine reviewed workbook gaps")
    for key, row in data["proposals"].items():
        if row["approval_status"] != PENDING:
            raise ValueError(f"Every external proposal must remain {PENDING}: {key}")
        if set(row) - FIELDS:
            raise ValueError(f"Unexpected field could masquerade as approved mapping: {key}")
        for field in FIELDS - {"discovery_url", "verification_terms"}:
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"Missing external review field {field}: {key}")
        if row["name"] != canon["modemon"][key]["name"] or workbooks["species"][key]["primary_lesson"]:
            raise ValueError(f"Must preserve canonical identity and unpopulated workbook gap: {key}")
        if row["confidence"] not in {"high", "medium", "low"}:
            raise ValueError(f"Invalid confidence: {key}")
        if not row.get("verification_terms") or not all(isinstance(t, str) and t.strip() for t in row["verification_terms"]):
            raise ValueError(f"Missing content checks: {key}")
        check_external_url(row["proposed_url"])
        if row.get("discovery_url"):
            check_external_url(row["discovery_url"])
        if evidence is not None:
            item = evidence[row["proposed_url"]]
            if (item["approval_status"] != PENDING or item["http_status"] != 200
                    or item["article_title"] != row["article_title"]
                    or item["final_url"] != row["proposed_url"]
                    or not all(item["verification_terms_found"].get(t) for t in row["verification_terms"])
                    or len(item["content_sha256"]) != 64 or not item["verified_at_utc"]):
                raise ValueError(f"Invalid pending-source verification: {key}")
            if row.get("discovery_url") and item.get("discovery_url") != row["discovery_url"]:
                raise ValueError(f"Missing source TOC verification: {key}")


def get(url):
    check_external_url(url)
    response = requests.get(url, timeout=60, allow_redirects=False, headers={
        "User-Agent": "ModemonGO-LessonResearch/1.0 (+https://github.com/maladroitcat/modemon-go/issues/26)"})
    # An unexpected redirect needs a fresh human check, not a guessed replacement.
    if response.status_code != 200:
        raise ValueError(f"External research source returned {response.status_code}: {url}")
    return response


def verify(data):
    evidence = {}
    for row in data["proposals"].values():
        url = row["proposed_url"]
        if url in evidence:
            continue
        time.sleep(.5)
        response = get(url)
        pdf = response.content.startswith(b"%PDF")
        if pdf:
            try:
                from pypdf import PdfReader
            except ImportError as error:
                raise RuntimeError("Live PDF audit requires pypdf; offline review/tests do not") from error
            reader = PdfReader(io.BytesIO(response.content))
            first_page = " ".join((reader.pages[0].extract_text() or "").split())
            if row["article_title"] not in first_page:
                raise ValueError("PDF first-page title mismatch")
            text = " ".join(" ".join((page.extract_text() or "") for page in reader.pages).split())
            observed = [row["article_title"]]
        else:
            page = Page()
            page.feed(response.text)
            observed = [heading for tag, heading in page.headings if tag == "h1"]
            # Google puts collection-widget copy inside its H1. Keep the raw
            # heading as evidence and remove only that known non-title suffix.
            titles = [h.split(" Stay organized with collections", 1)[0] for h in observed]
            if row["article_title"] not in titles:
                raise ValueError(f"Actual article title mismatch: {url}; {observed}")
            text = " ".join(" ".join(page.parts).split())
        terms = {term: term.casefold() in text.casefold() for term in row["verification_terms"]}
        if not all(terms.values()) or len(text) < 300:
            raise ValueError(f"External lesson topic mismatch: {url}; {terms}")
        item = {"approval_status": PENDING, "article_title": row["article_title"],
                "observed_headings": observed, "http_status": response.status_code,
                "final_url": response.url, "media_type": "pdf" if pdf else "html",
                "verification_terms_found": terms, "content_sha256": hashlib.sha256(response.content).hexdigest(),
                "verified_at_utc": datetime.now(timezone.utc).isoformat()}
        if row.get("discovery_url"):
            time.sleep(.5)
            toc = get(row["discovery_url"])
            page = Page()
            page.feed(toc.text)
            if url not in {urljoin(toc.url, href) for href, _ in page.links}:
                raise ValueError("Reference is not linked from the claimed source TOC")
            item["discovery_url"] = toc.url
        evidence[url] = item
    return evidence


def render(root=RESEARCH):
    before = protected_hashes()
    data, workbooks, canon, review = load_inputs()
    evidence = json.loads((RESEARCH / "external_reference_verification.json").read_text(encoding="utf-8"))
    validate(data, workbooks, canon, review, evidence)
    rows = [{"species_id": key, **row} for key, row in sorted(data["proposals"].items())]
    fields = list(dict.fromkeys(k for row in rows for k in row))
    root.mkdir(parents=True, exist_ok=True)
    (root / "modedex_external_owner_review.csv").write_text(csv_text(rows, fields), encoding="utf-8")
    lines = ["# Table B: External Fallbacks - PENDING_OWNER_APPROVAL", "",
             "Every row is pending individual owner approval, including independently reviewed species sharing a URL. Verified does not mean approved. No row populates a Modedex, workbook-mapping, or runtime link.", "",
             "These six proposals follow the full 360-lesson preferred-source review. The [preferred workbook table](modedex_learning_mapping.md) remains separate and its six genuine gaps remain blank.", "",
             "| Species | Status | Exact proposed title / URL | Publisher | Topic / rationale | Confidence / scope | Why workbook coverage was insufficient | Limits |", "|---|---|---|---|---|---|---|---|"]
    def esc(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    for r in rows:
        cells = [f'`{r["species_id"]}` ({r["name"]})', r["approval_status"],
                 f'[{r["article_title"]}]({r["proposed_url"]})', r["publisher"],
                 r["relevant_topic"] + ": " + r["match_rationale"],
                 r["confidence"] + ": " + r["scope_label"], r["why_workbooks_insufficient"], r["limitations"]]
        lines.append("| " + " | ".join(map(esc, cells)) + " |")
    lines += ["", "Confidence describes educational topic fit, not approval, clinical validity, production suitability, or proof of a Signature deployment. Source evidence is in external_reference_verification.json; existing Signature project URLs remain unchanged and separate.",
              "", "Owner decisions: accept/reject each species/reference pair or request alternatives. A future explicitly authorized change would be needed before any approved external link could enter the app. This research renderer has no approval or deployment command.", ""]
    (root / "modedex_external_owner_review.md").write_text("\n".join(lines), encoding="utf-8")
    if protected_hashes() != before:
        raise ValueError("Protected canonical input changed during external research rendering")
    print(f"Rendered {len(rows)} external proposals, all {PENDING}; no approved links written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Explicit live network audit; does not approve anything")
    args = parser.parse_args()
    data, workbooks, canon, review = load_inputs()
    validate(data, workbooks, canon, review)
    if args.verify:
        evidence = verify(data)
        (RESEARCH / "external_reference_verification.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render()
