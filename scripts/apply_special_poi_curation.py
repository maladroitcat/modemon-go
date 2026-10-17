#!/usr/bin/env python3
"""Apply human Step 8B/8C decisions without rescoring or editing source data."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from datetime import date
from pathlib import Path
import textwrap

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data/config/special_poi_curation.yaml"
SHORTLIST = ROOT / "data/processed/special_poi_candidates_by_region.csv"
FIELDS = [
    "verification_date", "current_status", "verified_name", "gameplay_suitability",
    "selection_status", "primary_rank", "alternate_rank", "verification_note",
    "selection_rationale", "verification_source_name", "verification_source_url",
    "association_anchor_note", "additional_verification_sources_json",
]
STATUSES = ["active", "temporarily_impacted", "relocated_renamed", "closed", "unknown"]
SUITABILITIES = ["suitable", "conditional", "sensitive_not_recommended"]
SELECTIONS = ["primary", "alternate", "deferred", "not_selected", "rejected"]
REGIONS = ["DUR-01", "DUR-02", "RAL-01", "RAL-02", "RAL-03A", "RAL-03B", "RAL-04", "RAL-05"]
OUTPUT_FILES = [
    "data/processed/special_poi_curation.csv",
    "data/processed/special_poi_primary.csv",
    "data/processed/special_poi_primary.geojson",
    "data/processed/special_poi_alternates.csv",
    "data/processed/special_poi_alternates.geojson",
    "data/processed/special_poi_curation_summary.csv",
    "output/special_poi_curation_raleigh.png",
    "output/special_poi_curation_durham.png",
    "output/special_poi_curation_report.md",
    "output/special_poi_curation_provenance.json",
]


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject YAML duplicate keys instead of silently dropping a human decision."""


def unique_mapping(loader, node):
    pairs = loader.construct_pairs(node)
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate YAML key: {key}")
        result[key] = value
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def read_rows(path):
    # CSV strings preserve every source field, including exact score/coordinate text.
    with Path(path).open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        if not fields or len(fields) != len(set(fields)):
            raise ValueError("Missing or duplicate CSV columns")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("Malformed source CSV row")
    return rows, fields


def load_config(path=CONFIG):
    with Path(path).open(encoding="utf-8") as stream:
        config = yaml.load(stream, Loader=UniqueKeyLoader)
    if not isinstance(config, dict) or not isinstance(config.get("decisions"), dict):
        raise ValueError("Curation config must contain a decision mapping keyed by poi_id")
    if (config.get("expected_shortlist_count") != 42 or config.get("expected_primary_count") != 17
            or config.get("canonical_region_ids") != REGIONS):
        raise ValueError("Curation inventory must remain 42 candidates, 17 primaries, eight regions")
    return config


def resolve_candidate_id(rows, region_id, candidate_name):
    matches = [r for r in rows if r["region_id"] == region_id and r["name"] == candidate_name]
    if len(matches) != 1:
        raise ValueError(f"Candidate name must match exactly once: {region_id} / {candidate_name!r}; {len(matches)} matches")
    return matches[0]["poi_id"]


def protected_hashes(root=ROOT):
    excluded = set(OUTPUT_FILES)
    paths = [p for folder in ["data", "output"] for p in (root / folder).rglob("*")
             if p.is_file() and p.name != ".DS_Store" and "__pycache__" not in p.parts
             and str(p.relative_to(root)) not in excluded]
    paths.append(root / "scripts/score_special_poi_candidates.py")
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def assert_unchanged(before, root=ROOT):
    after = protected_hashes(root)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    if changed:
        raise ValueError(f"Protected source files changed: {changed}")


def apply_curation(rows, config):
    ids = [r["poi_id"] for r in rows]
    if len(rows) != 42 or len(ids) != len(set(ids)) or not all(ids):
        raise ValueError("Exactly 42 unique Step 8A shortlist candidates are required")
    if set(ids) != set(config["decisions"]):
        raise ValueError("Decision IDs must match all 42 shortlist IDs exactly; missing or outside decision")
    if set(r["region_id"] for r in rows) != set(REGIONS):
        raise ValueError("Unexpected shortlist region inventory")
    if set(rows[0]) & set(FIELDS):
        raise ValueError("Curation fields must not overwrite Step 8A columns")
    if set(config.get("defaults", {})) - set(FIELDS):
        raise ValueError("Unknown default curation fields")
    result = []
    for row in rows:
        decision = config["decisions"][row["poi_id"]]
        if not isinstance(decision, dict) or set(decision) - set(FIELDS + ["region_id", "candidate_name"]):
            raise ValueError(f"Unknown curation fields: {row['poi_id']}")
        resolved = resolve_candidate_id(rows, decision["region_id"], decision["candidate_name"])
        if resolved != row["poi_id"]:
            raise ValueError("Decision key does not match exact candidate name and region")
        values = {**config.get("defaults", {}), **decision}
        missing = set(FIELDS) - set(values)
        if missing:
            raise ValueError(f"Missing curation fields: {missing}")
        result.append({**row, **{field: values[field] for field in FIELDS}})
    validate(result, rows)
    return sorted(result, key=lambda r: (
        r["region_id"], SELECTIONS.index(r["selection_status"]),
        r["primary_rank"] or r["alternate_rank"] or int(r["region_candidate_rank"]), r["poi_id"]))


def validate(curated, source):
    if len(curated) != 42 or len({r["poi_id"] for r in curated}) != 42:
        raise ValueError("Curation changed shortlist inventory")
    by_id = {r["poi_id"]: r for r in source}
    if set(by_id) != {r["poi_id"] for r in curated}:
        raise ValueError("Curation changed shortlist IDs")
    for row in curated:
        if any(row.get(field) != value for field, value in by_id[row["poi_id"]].items()):
            raise ValueError("Step 8A values changed, including name, scores, or coordinates")
        if row["current_status"] not in STATUSES or row["selection_status"] not in SELECTIONS:
            raise ValueError("Invalid status enumeration")
        suitability = row["gameplay_suitability"]
        if suitability not in SUITABILITIES + [None]:
            raise ValueError("Invalid gameplay suitability")
        if suitability is None and row["current_status"] not in {"closed", "relocated_renamed", "unknown"}:
            raise ValueError("Null suitability requires an unavailable or unverified mapped identity")
        if row["verification_date"] != "2026-10-17":
            raise ValueError("Human verification date must be 2026-10-17")
        date.fromisoformat(row["verification_date"])
        for field in FIELDS:
            if field not in {"primary_rank", "alternate_rank"} and row[field] is not None and not isinstance(row[field], str):
                raise ValueError(f"Expected text or null: {field}")
        for field in ["verification_note", "selection_rationale"]:
            if not row[field] or not row[field].strip():
                raise ValueError(f"Missing human documentation: {field}")
        selected = row["selection_status"] in {"primary", "alternate"}
        if selected and (suitability not in {"suitable", "conditional"}
                         or row["current_status"] in {"closed", "unknown"}):
            raise ValueError("Unsafe or unavailable candidate cannot be primary or alternate")
        for status, field in [("primary", "primary_rank"), ("alternate", "alternate_rank")]:
            rank = row[field]
            if row["selection_status"] == status:
                if type(rank) is not int or rank < 1:
                    raise ValueError("Selected ranks must be positive integers")
            elif rank is not None:
                raise ValueError("Rank must be null outside its selection status")
        if row["additional_verification_sources_json"] is not None:
            sources = json.loads(row["additional_verification_sources_json"])
            if not isinstance(sources, list) or not all(isinstance(s, dict) and s.get("url") for s in sources):
                raise ValueError("Additional evidence must be a JSON source list")
        lon, lat = float(row["representative_longitude"]), float(row["representative_latitude"])
        if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError("Invalid inherited WGS84 representative coordinate")
    if sum(r["selection_status"] == "primary" for r in curated) != 17:
        raise ValueError("Expected exactly 17 primary destinations")
    for region in REGIONS:
        part = [r for r in curated if r["region_id"] == region]
        primary_count = sum(r["selection_status"] == "primary" for r in part)
        if not 0 <= primary_count <= 3 or (region == "RAL-05" and primary_count):
            raise ValueError("Invalid per-region primary count; RAL-05 must have zero")
        for status, field in [("primary", "primary_rank"), ("alternate", "alternate_rank")]:
            ranks = sorted(r[field] for r in part if r["selection_status"] == status)
            if ranks != list(range(1, len(ranks) + 1)):
                raise ValueError("Ranks must be unique and contiguous beginning at 1")


def summarize(rows):
    summaries = []
    for region in REGIONS + ["TOTAL"]:
        part = rows if region == "TOTAL" else [r for r in rows if r["region_id"] == region]
        record = {"region_id": region, "shortlist_candidates": len(part)}
        for field, categories in [("current_status", STATUSES), ("gameplay_suitability", SUITABILITIES),
                                  ("selection_status", SELECTIONS)]:
            record.update({value: sum(r[field] == value for r in part) for value in categories})
        record["suitability_not_assessed"] = sum(r["gameplay_suitability"] is None for r in part)
        summaries.append(record)
    return summaries


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def geojson(rows):
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [
            float(r["representative_longitude"]), float(r["representative_latitude"])]}, "properties": r}
        for r in rows]}


def display_name(row):
    return row["verified_name"] or row["name"]


def draw_maps(rows, root, output_root):
    regions = gpd.read_file(root / "data/processed/regions.geojson").to_crs(2264)
    zones = gpd.read_file(root / "data/processed/habitat_zones.geojson").to_crs(2264)
    if set(regions.region_id) != set(REGIONS) or regions.region_id.duplicated().any():
        raise ValueError("Expected eight canonical map regions")
    selected = [r for r in rows if r["selection_status"] in {"primary", "alternate"}]
    points = gpd.GeoDataFrame(selected, geometry=gpd.points_from_xy(
        [float(r["representative_longitude"]) for r in selected],
        [float(r["representative_latitude"]) for r in selected]), crs=4326).to_crs(2264)
    styles = {
        "suitable_primary": ("*", "#16734b", 150, "Suitable primary"),
        "conditional_primary": ("^", "#c86309", 85, "Conditional primary"),
        "alternate": ("o", "#4666a3", 36, "Alternate"),
    }
    for city in ["Raleigh", "Durham"]:
        fig, (ax, key) = plt.subplots(1, 2, figsize=(17, 11), gridspec_kw={"width_ratios": [1.5, 1]})
        parents = regions[regions.parent_city == city]
        context = zones[zones.region_id.isin(parents.region_id)]
        context.plot(ax=ax, color="#e7e9ec", edgecolor="#c7cbd0", linewidth=0.35)
        parents.boundary.plot(ax=ax, color="#303944", linewidth=1.2)
        part = points[points.parent_city == city]
        for kind, (marker, color, size, _) in styles.items():
            mask = part.selection_status.eq("alternate") if kind == "alternate" else (
                part.selection_status.eq("primary") & part.gameplay_suitability.eq(
                    "conditional" if kind == "conditional_primary" else "suitable"))
            picked = part[mask]
            if len(picked):
                picked.plot(ax=ax, marker=marker, color=color, markersize=size, edgecolor="white", linewidth=0.6, zorder=4)
        for row in part.itertuples():
            rank = row.primary_rank if row.selection_status == "primary" else row.alternate_rank
            tag = ("P" if row.selection_status == "primary" else "A") + str(int(rank))
            ax.annotate(tag, (row.geometry.x, row.geometry.y), xytext=(5, 5), textcoords="offset points",
                        fontsize=8, zorder=5, bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none", "pad": 0.5})
        for row in parents.itertuples():
            point = row.geometry.representative_point()
            ax.annotate(row.region_id, (point.x, point.y), xytext=(0, -15), textcoords="offset points",
                        fontsize=9, fontweight="bold", color="#303944", zorder=3)
        handles = [Line2D([], [], marker=s[0], color="none", markerfacecolor=s[1], markersize=10, label=s[3])
                   for s in styles.values()]
        ax.legend(handles=handles, loc="lower left", fontsize=9)
        ax.set_title(f"{city}: curated special destinations\nStep 8B/8C human decisions, 2026-10-17")
        ax.set_axis_off()
        key.set_axis_off()
        lines = []
        for region in parents.sort_values("region_id").region_id:
            lines.append(region)
            region_rows = [r for r in selected if r["region_id"] == region]
            if not region_rows:
                lines.append("  No selected special destinations (intentional).")
            for row in region_rows:
                rank = row["primary_rank"] or row["alternate_rank"]
                tag = ("P" if row["selection_status"] == "primary" else "A") + str(rank)
                label = f"{tag}  {display_name(row)}" + (" [conditional]" if row["gameplay_suitability"] == "conditional" else "")
                lines.extend(textwrap.wrap(label, 56, initial_indent="  ", subsequent_indent="      "))
            lines.append("")
        key.text(0, 1, "\n".join(lines), va="top", fontsize=9, linespacing=1.45)
        fig.text(0.02, 0.015, "QA only. Coordinates are association anchors, not directions to enter a building or restricted area. No active encounters defined.", fontsize=9)
        fig.tight_layout(rect=(0, 0.035, 1, 1))
        fig.savefig(output_root / f"output/special_poi_curation_{city.lower()}.png", dpi=160, metadata={"Software": "Modemon GO curation QA"})
        plt.close(fig)


def report(rows, summary, protected_count):
    lines = ["# Special POI human-curation audit", "", "Verification date: 2026-10-17. Decisions supplied by the project team; no new web verification or scoring.", ""]
    for status in SELECTIONS:
        lines += [f"## {status.replace('_', ' ').title()}", ""]
        for r in rows:
            if r["selection_status"] == status:
                rank = r["primary_rank"] or r["alternate_rank"]
                lines.append(f"- {r['region_id']} {'#'+str(rank)+' ' if rank else ''}{display_name(r)}: {r['selection_rationale']}")
        lines.append("")
    groups = [
        ("Current-status anomalies", lambda r: r["current_status"] != "active"),
        ("Display-name overrides (source names retained)", lambda r: bool(r["verified_name"])),
        ("Sensitive/not recommended", lambda r: r["gameplay_suitability"] == "sensitive_not_recommended"),
        ("Conditional primaries", lambda r: r["selection_status"] == "primary" and r["gameplay_suitability"] == "conditional"),
    ]
    for title, predicate in groups:
        lines += [f"## {title}", ""]
        for r in rows:
            if predicate(r):
                lines.append(f"- {r['region_id']} {r['name']} -> {display_name(r)} ({r['current_status']}): {r['verification_note']}")
                if r["association_anchor_note"]:
                    lines.append(f"  Anchor limitation: {r['association_anchor_note']}")
        lines.append("")
    lines += ["## Coverage and integrity", ""]
    for row in summary[:-1]:
        if row["primary"] < 3:
            lines.append(f"- {row['region_id']}: {row['primary']} primary destinations; fewer than three is intentional.")
    lines += ["", "RAL-05 intentionally has zero primaries. WakeMed remains an ordinary Healthcare POI, not a special-gameplay destination.",
              "", f"All {protected_count} protected files hashed before/after; no changes. All original shortlist fields preserved exactly.",
              "Automated curation validation passed. Run the complete unit suite with `python3 -B -m unittest discover -s tests -v`.",
              "", "Primary means an approved destination, not a currently active spawn. No timing, rarity, geofencing, or model-family assignments are defined.", ""]
    return "\n".join(lines)


def run(root=ROOT, output_root=None):
    root = Path(root)
    output_root = Path(output_root) if output_root is not None else root
    before = protected_hashes(root)
    try:
        config = load_config(root / "data/config/special_poi_curation.yaml")
        source, fields = read_rows(root / "data/processed/special_poi_candidates_by_region.csv")
        rows = apply_curation(source, config)
        for folder in ["data/processed", "output"]:
            (output_root / folder).mkdir(parents=True, exist_ok=True)
        summary = summarize(rows)
        for suffix, subset in [("curation", rows), ("primary", [r for r in rows if r["selection_status"] == "primary"]),
                               ("alternates", [r for r in rows if r["selection_status"] == "alternate"])]:
            path = output_root / f"data/processed/special_poi_{suffix}.csv"
            write_csv(path, subset, fields + FIELDS)
            restored, _ = read_rows(path)
            if any(any(a[k] != b[k] for k in fields) for a, b in zip(subset, restored)):
                raise ValueError("Source field changed during CSV serialization")
            if suffix != "curation":
                (output_root / f"data/processed/special_poi_{suffix}.geojson").write_text(
                    json.dumps(geojson(subset), ensure_ascii=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        write_csv(output_root / "data/processed/special_poi_curation_summary.csv", summary, list(summary[0]))
        draw_maps(rows, root, output_root)
        (output_root / "output/special_poi_curation_report.md").write_text(report(rows, summary, len(before)), encoding="utf-8")
    finally:
        assert_unchanged(before, root)
    provenance = {"verification_date": "2026-10-17", "protected_inputs_unchanged": True,
                  "protected_sha256": before, "shortlist_count": len(rows), "primary_count": summary[-1]["primary"],
                  "source_field_integrity": "All original CSV field strings preserved; coordinates unchanged; no rescoring.",
                  "decision_source": "Human decisions; not independently re-verified by this script."}
    (output_root / "output/special_poi_curation_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rows, summary


if __name__ == "__main__":
    _, summaries = run()
    print(json.dumps(summaries, indent=2))
