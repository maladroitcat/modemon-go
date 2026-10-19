#!/usr/bin/env python3
"""Build the approved, non-Signature-only learning overlay without changing canon."""
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from scripts.build_modedex import load_yaml
from scripts import build_workbook_research_review as workbook
from scripts import review_external_learning_references as external

DESTINATION = ROOT / "mobile/web/src/data/learning.json"
INPUTS = (
    "data/config/modedex.yaml", "data/config/modedex_learning_links.yaml",
    "data/research/modedex_external_proposals.yaml",
    "data/research/modedex_external_owner_decisions.yaml",
    "data/research/workbook_lesson_verification.json",
    "data/research/external_reference_verification.json",
    "data/research/workbook_component_review.yaml",
)
HOSTS = workbook.DOMAINS | external.RESEARCH_HOSTS


def safe_url(value):
    if not isinstance(value, str) or re.search(r"[\s\\\x00-\x1f\x7f]", value):
        raise ValueError(f"Unsafe learning URL: {value!r}")
    url = urlsplit(value)
    if (url.scheme != "https" or url.hostname not in HOSTS or url.netloc != url.hostname
            or not url.path.strip("/") or url.query or url.fragment):
        raise ValueError(f"Unapproved learning URL: {value!r}")
    return value


def text(value, label):
    if not isinstance(value, str) or not value.strip() or re.search(r"[\x00-\x1f\x7f]", value):
        raise ValueError(f"Missing or invalid learning text: {label}")
    return value


def make_overlay(canon, mappings, proposals, decisions, workbook_evidence, external_evidence, review):
    workbook.validate(mappings, canon, workbook_evidence)
    external.validate(proposals, mappings, canon, review, external_evidence)
    approved = external.owner_decision_fields(proposals, decisions)
    if decisions.get("implementation_authorization") != mappings["authorization"]["issue_url"]:
        raise ValueError("Missing issue 30 implementation authorization")
    species = canon["modemon"]
    ordinary = {key for key, row in species.items() if row["stage"] < 3}
    if len(ordinary) != 39 or len(species) - len(ordinary) != 12:
        raise ValueError("Expected 39 non-Signatures and 12 Signatures")
    if sum(bool(row["primary_lesson"]) for row in mappings["species"].values()) != 45:
        raise ValueError("Expected all 45 existing workbook matches to be preserved")

    def lesson(ref, note):
        row = mappings["lessons"][ref]
        return {"title": text(row["article_title"], ref),
                "source": text(row["workbook"], ref), "url": safe_url(row["url"]),
                "kind": "workbook", "scope_note": text(note, ref)}

    result = {}
    for key in sorted(ordinary):
        row = mappings["species"][key]
        ref = row["primary_lesson"]
        if ref:
            note = ("Task overview; educational context, not evidence of a particular deployment."
                    if row["match_scope"] == "task" else
                    "Supporting concept: " + row.get("scope_label", row["match_scope"].replace("_", " "))
                    + ". This is not a description of the complete system or a specific deployment.")
            primary = lesson(ref, note)
        else:
            source = proposals["proposals"][key]
            if approved[key]["approval_status"] != external.APPROVED:
                raise ValueError(f"Unapproved outside reference: {key}")
            primary = {"title": text(source["article_title"], key),
                       "source": text(source["publisher"], key),
                       "url": safe_url(source["proposed_url"]), "kind": "external",
                       "scope_note": text("Related example: " + source["scope_label"]
                                          + ". Not evidence of a deployment at this place.", key)}
        secondary = None
        if row.get("secondary_lesson"):
            secondary = lesson(row["secondary_lesson"], "Supporting concept: " + row["secondary_rationale"])
            if secondary["url"] == primary["url"]:
                raise ValueError(f"Duplicate educational links: {key}")
        result[key] = {"primary": primary, "secondary": secondary}
    if set(result) != ordinary or sum(r["primary"]["kind"] == "external" for r in result.values()) != 4:
        raise ValueError("Incomplete non-Signature learning coverage")
    return {"version": 1, "species": result}


def build(destination=DESTINATION):
    destination = Path(destination).resolve()
    if destination.is_relative_to(ROOT / "data") or (destination.exists() and destination != DESTINATION
                                                     and destination.is_relative_to(ROOT)):
        raise ValueError("Learning builder cannot overwrite canonical data or unrelated repository files")
    before = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in INPUTS}
    canon, mappings, proposals, decisions, we, ee, review = [ROOT / p for p in INPUTS]
    result = make_overlay(load_yaml(canon), load_yaml(mappings), load_yaml(proposals), load_yaml(decisions),
                          json.loads(we.read_text()), json.loads(ee.read_text()), load_yaml(review))
    result["source_hashes"] = before
    if before != {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in INPUTS}:
        raise ValueError("Learning inputs changed during build")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    try:
        overlay = build()
        print(f"Built learning overlay: {len(overlay['species'])} non-Signatures; no supplementary Signature links")
    except (ValueError, KeyError, OSError) as error:
        sys.exit(f"Learning overlay validation failed: {error}")
