#!/usr/bin/env python3
"""Render the research overlay for owner review; never wire links into the app."""
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from scripts.audit_workbook_lessons import DOMAINS

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "data/research"
INVENTORY_FIELDS = (
    "family_id", "stage", "role", "ai_tasks", "models_algorithms", "input_data",
    "output_data", "habitats", "explainability", "biases_limitations",
)


def protected_hashes():
    paths = sorted({p for folder in ("data/config", "data/processed")
                    for p in (ROOT / folder).rglob("*") if p.is_file()
                    and p.name != "modedex_learning_links.yaml"})
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def check_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in DOMAINS
            or len(parsed.path.strip("/").split("/")) < 3
            or parsed.query or parsed.fragment or parsed.username or parsed.port):
        raise ValueError(f"Not a precise authorized lesson URL: {url}")


def validate(data, canon, evidence):
    if data["status"] != "research_only_pending_owner_review":
        raise ValueError("This artifact is research only, not UI approval")
    species, lessons = data["species"], data["lessons"]
    if len(species) != 51 or set(species) != set(canon["modemon"]):
        raise ValueError("Research must inventory exactly all 51 canonical IDs")
    if set(evidence) != set(lessons):
        raise ValueError("Missing or stale live verification evidence")
    used = set()
    for key, lesson in lessons.items():
        check_url(lesson["url"])
        e = evidence[key]
        if (e["url"] != lesson["url"] or e["final_url"] != lesson["url"]
                or e["article_title"] != lesson["article_title"]
                or e["toc_url"] != lesson["toc_url"] or not e["toc_link_label"]
                or e["http_status"] != 200
                or set(e["verification_terms_found"]) != set(lesson["verification_terms"])
                or not all(e["verification_terms_found"].values())
                or len(e["main_text_sha256"]) != 64 or not e["verified_at_utc"]):
            raise ValueError(f"Invalid live lesson evidence: {key}")
    for key, row in species.items():
        if row["name"] != canon["modemon"][key]["name"]:
            raise ValueError(f"Canonical name mismatch: {key}")
        if row["confidence"] not in {"high", "medium", "low"}:
            raise ValueError(f"Invalid confidence: {key}")
        if row["match_scope"] not in {"task", "representative_technique", "input_representation", "related_context", "unresolved"}:
            raise ValueError(f"Invalid match scope: {key}")
        for text in ("rationale", "limitations"):
            if not row[text].strip():
                raise ValueError(f"Missing {text}: {key}")
        primary, secondary = row["primary_lesson"], row.get("secondary_lesson")
        if primary is None and (row["confidence"] != "low" or row["match_scope"] != "unresolved" or secondary):
            raise ValueError(f"Unresolved entry must not imply an approved link: {key}")
        if row["confidence"] != "high" and row["review_required"] is not True:
            raise ValueError(f"Weak/partial match needs review: {key}")
        if row["review_required"] and not row.get("scope_label", "").strip():
            raise ValueError(f"Review entry needs an honest component/gap scope label: {key}")
        if secondary and (secondary == primary or not row.get("secondary_rationale", "").strip()):
            raise ValueError(f"Secondary needs an independent purpose: {key}")
        for ref in [primary, secondary, *row.get("candidate_lessons", [])]:
            if ref:
                if ref not in lessons:
                    raise ValueError(f"Unknown lesson {ref}: {key}")
                used.add(ref)
    if used != set(lessons):
        raise ValueError(f"Unused lesson catalog entries: {set(lessons) - used}")


def rows_for(data, canon):
    rows = []
    for key, row in sorted(data["species"].items()):
        original = canon["modemon"][key]
        result = dict(species_id=key, name=row["name"])
        result.update({field: original[field] for field in INVENTORY_FIELDS})
        # Signature evidence is context only, never a workbook lesson or source.
        result["signature_project_source_url"] = (original.get("signature") or {}).get("source_url", "")
        result.update({field: row[field] for field in ("confidence", "match_scope", "rationale", "limitations", "review_required")})
        result["scope_label"] = row.get("scope_label", row["match_scope"].replace("_", " "))
        for kind in ("primary", "secondary"):
            ref = row.get(f"{kind}_lesson")
            lesson = data["lessons"].get(ref, {})
            result[f"{kind}_lesson_id"] = ref or ""
            for field in ("workbook", "unit", "chapter", "article_title", "url"):
                result[f"{kind}_{field}"] = lesson.get(field, "")
        result["secondary_rationale"] = row.get("secondary_rationale", "")
        result["candidate_lessons_not_approved"] = row.get("candidate_lessons", [])
        rows.append(result)
    return rows


def csv_text(rows, fields):
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()})
    return buf.getvalue()


def render(root=RESEARCH):
    before = protected_hashes()
    data = yaml.safe_load((ROOT / "data/config/modedex_learning_links.yaml").read_text(encoding="utf-8"))
    canon = yaml.safe_load((ROOT / "data/config/modedex.yaml").read_text(encoding="utf-8"))
    evidence = json.loads((RESEARCH / "workbook_lesson_verification.json").read_text())
    validate(data, canon, evidence)
    rows = rows_for(data, canon)
    root.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    (root / "modedex_learning_inventory.csv").write_text(csv_text(rows, fields), encoding="utf-8")
    queue = [r for r in rows if r["review_required"]]
    (root / "modedex_learning_review_queue.csv").write_text(csv_text(queue, fields), encoding="utf-8")
    linked = sum(bool(r["primary_lesson_id"]) for r in rows)
    counts = Counter(r["confidence"] for r in rows)
    lines = ["# Table A: Preferred Workbook Mappings", "",
             "Research only. No links are wired into the game; no canonical fields were changed.", "",
             f"51 inventoried; {linked} proposed primary links; {51-linked} unresolved; {len(queue)} review rows. Confidence: {dict(sorted(counts.items()))}.", "",
             "High means a direct task, input concept, or explicitly canonical representative technique, not complete coverage of every algorithm or a deployment claim. Medium includes useful component-level coverage with explicit boundaries. Null lessons are intentional gaps, not broken URLs. All mappings remain research proposals.", "",
             "External fallback proposals are exclusively in [Table B](modedex_external_owner_review.md), all marked PENDING_OWNER_APPROVAL. They do not fill nulls in this table or enter the application.", "",
             "The CSV inventory also contains verbatim canonical roles, algorithms, tasks, inputs, outputs, habitats, limitations, explainability and separate Signature project sources.", "",
             "| Species ID / name | Represented job | Proposed lesson | Confidence / scope | Match rationale and boundary | Optional second lesson |", "|---|---|---|---|---|---|"]
    def escape(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    for r in rows:
        primary = f'[{r["primary_article_title"]}]({r["primary_url"]})' if r["primary_url"] else "**UNRESOLVED**"
        if r["primary_url"]:
            primary += f'<br>{r["primary_workbook"]}: {r["primary_unit"]} / {r["primary_chapter"]}'
        secondary = f'[{r["secondary_article_title"]}]({r["secondary_url"]}) — {r["secondary_rationale"]}' if r["secondary_url"] else "—"
        lines.append("| " + " | ".join(map(escape, [f'`{r["species_id"]}`<br>{r["name"]}', r["role"], primary, f'{r["confidence"]}: {r["scope_label"]}<br>({r["match_scope"]})', r["rationale"] + " Boundary: " + r["limitations"], secondary])) + " |")
    lines += ["", "## Unresolved IDs", "", *[f'- `{r["species_id"]}` ({r["name"]}): {r["rationale"]}' for r in rows if not r["primary_lesson_id"]],
              "", "## Integrity", "", "Protected configuration and processed canonical files were SHA-256 checked before/after rendering and are unchanged. See modedex_learning_source_hashes.json. Live lesson checks are recorded separately; none are evidence of a Signature deployment.", ""]
    (root / "modedex_learning_mapping.md").write_text("\n".join(lines), encoding="utf-8")
    if protected_hashes() != before:
        raise ValueError("Protected canonical input changed during research render")
    (root / "modedex_learning_source_hashes.json").write_text(json.dumps(before, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"Inventoried {len(rows)}; proposed {linked}; unresolved {51-linked}; review {len(queue)}; protected files unchanged.")


if __name__ == "__main__":
    render()
