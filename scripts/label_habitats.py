#!/usr/bin/env python3
"""Assign Modemon GO gameplay habitats to retained OSM POIs."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import pandas as pd
import yaml
from shapely.geometry import Point


ROOT = Path(__file__).resolve().parents[1]
SOURCE_POIS_GEOJSON = ROOT / "data" / "processed" / "pois.geojson"
SOURCE_POIS_CSV = ROOT / "data" / "processed" / "pois.csv"
REGIONS_GEOJSON = ROOT / "data" / "processed" / "regions.geojson"
RULES_PATH = ROOT / "data" / "config" / "habitat_rules.yaml"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "output"

EXPECTED_POI_COUNT = 927
HABITAT_FIELDS = [
    "habitat_primary",
    "habitat_secondary",
    "habitat_rule_id",
    "habitat_confidence",
    "habitat_reason",
    "habitat_review_required",
    "habitat_candidate_rule_ids",
    "habitat_conflict",
]

CONFIDENCE_ORDER = {"high": 3, "medium": 2, "low": 1}
ACADEMIC_HEALTHCARE_SIGNALS = {
    ("office", "research"),
    ("amenity", "university"),
    ("amenity", "college"),
    ("amenity", "school"),
}
ACADEMIC_SIGNAL_KEYS = {
    "university",
    "research",
    "research_institution",
    "school",
    "college",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-count-change",
        action="store_true",
        help="Allow source POI count to differ from the expected merged POI baseline.",
    )
    return parser.parse_args()


def load_rules(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Habitat rulebook missing: {path}")
    with path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict) or "rules" not in config or "habitats" not in config:
        raise ValueError(f"Invalid habitat rulebook: {path}")
    return config


def load_pois() -> gpd.GeoDataFrame:
    if not SOURCE_POIS_GEOJSON.exists():
        raise FileNotFoundError(f"Source POI GeoJSON missing: {SOURCE_POIS_GEOJSON}")
    if not SOURCE_POIS_CSV.exists():
        raise FileNotFoundError(f"Source POI CSV missing: {SOURCE_POIS_CSV}")
    pois = gpd.read_file(SOURCE_POIS_GEOJSON)
    if pois.empty:
        raise ValueError("Source POI file contains zero rows.")
    return pois


def parse_raw_tags(raw_tags: Any) -> dict[str, str]:
    if raw_tags is None or (isinstance(raw_tags, float) and math.isnan(raw_tags)):
        return {}
    if isinstance(raw_tags, dict):
        return {str(k): "" if v is None else str(v) for k, v in raw_tags.items()}
    try:
        parsed = json.loads(str(raw_tags))
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(k): "" if v is None else str(v) for k, v in parsed.items()}


def get_tag(tags: dict[str, str], row: pd.Series, key: str) -> str | None:
    if key in tags and tags[key] not in ("", "nan", "None"):
        return str(tags[key])
    if row.get("primary_osm_key") == key:
        value = row.get("primary_osm_value")
        if pd.notna(value):
            return str(value)
    return None


def has_name(row: pd.Series, tags: dict[str, str]) -> bool:
    name = row.get("name")
    if pd.notna(name) and str(name).strip():
        return True
    tag_name = tags.get("name")
    return bool(tag_name and tag_name.strip())


def condition_matches(condition: dict[str, Any], row: pd.Series, tags: dict[str, str]) -> bool:
    key = str(condition["key"])
    value = get_tag(tags, row, key)
    if value is None:
        return False
    values = condition.get("values")
    if values is None:
        return True
    normalized_values = [str(v) for v in values]
    return "*" in normalized_values or value in normalized_values


def rule_matches(rule: dict[str, Any], row: pd.Series, tags: dict[str, str]) -> bool:
    if rule.get("require_name") and not has_name(row, tags):
        return False
    any_conditions = rule.get("any", [])
    if any_conditions and not any(condition_matches(c, row, tags) for c in any_conditions):
        return False
    all_conditions = rule.get("all", [])
    if all_conditions and not all(condition_matches(c, row, tags) for c in all_conditions):
        return False
    return True


def matching_condition_keys(
    rule: dict[str, Any], row: pd.Series, tags: dict[str, str]
) -> set[str]:
    keys: set[str] = set()
    for condition in rule.get("any", []) + rule.get("all", []):
        if condition_matches(condition, row, tags):
            keys.add(str(condition["key"]))
    return keys


def has_academic_healthcare_context(row: pd.Series, tags: dict[str, str]) -> bool:
    for key, value in ACADEMIC_HEALTHCARE_SIGNALS:
        if get_tag(tags, row, key) == value:
            return True
    for key in ACADEMIC_SIGNAL_KEYS:
        if key in tags and str(tags[key]).strip():
            return True
    return False


def strongest_confidence(a: str, b: str) -> str:
    return a if CONFIDENCE_ORDER.get(a, 0) >= CONFIDENCE_ORDER.get(b, 0) else b


def classify_row(
    row: pd.Series,
    rules: list[dict[str, Any]],
    review_rules: list[dict[str, Any]],
    habitats: set[str],
) -> dict[str, Any]:
    tags = parse_raw_tags(row.get("raw_tags"))
    matches = [rule for rule in rules if rule_matches(rule, row, tags)]
    review_matches = [rule for rule in review_rules if rule_matches(rule, row, tags)]
    candidate_rule_ids = [rule["rule_id"] for rule in matches + review_matches]

    if matches:
        matches = sorted(matches, key=lambda r: (int(r.get("priority", 9999)), str(r["rule_id"])))
        top_priority = int(matches[0].get("priority", 9999))
        top_matches = [r for r in matches if int(r.get("priority", 9999)) == top_priority]
        selected = top_matches[0]
        outputs = {
            (
                r.get("habitat_primary", ""),
                r.get("habitat_secondary", ""),
            )
            for r in top_matches
        }
        conflict = len(outputs) > 1
        primary = selected.get("habitat_primary", "")
        secondary = selected.get("habitat_secondary", "")
        confidence = selected.get("confidence", "medium")
        review_required = bool(selected.get("review_required", False) or conflict)
        reason = selected.get("notes", "")
        rule_id = selected["rule_id"]

        if (
            primary == "Healthcare"
            and not secondary
            and has_academic_healthcare_context(row, tags)
        ):
            secondary = "Education & Research"
            confidence = strongest_confidence(confidence, "medium")
            reason = f"{reason} Academic or research source tag adds Education & Research secondary."

        material_review_matches = review_matches
        if (
            confidence == "high"
            and not selected.get("review_required", False)
            and not conflict
        ):
            material_review_matches = [
                rule
                for rule in review_matches
                if matching_condition_keys(rule, row, tags) != {"historic"}
            ]

        if material_review_matches:
            review_required = True
            review_notes = "; ".join(r.get("reason", "") for r in material_review_matches)
            reason = f"{reason} Review signal: {review_notes}".strip()
    else:
        primary = ""
        secondary = ""
        confidence = "low"
        review_required = True
        conflict = False
        rule_id = ""
        if review_matches:
            reason = "; ".join(r.get("reason", "") for r in review_matches)
        else:
            reason = "No defensible habitat rule matched this POI."

    if primary and primary not in habitats:
        raise ValueError(f"Invalid primary habitat {primary!r} for {row.get('poi_id')}")
    if secondary and secondary not in habitats:
        raise ValueError(f"Invalid secondary habitat {secondary!r} for {row.get('poi_id')}")
    if primary and secondary and primary == secondary:
        raise ValueError(f"Primary and secondary habitat match for {row.get('poi_id')}")

    return {
        "habitat_primary": primary,
        "habitat_secondary": secondary,
        "habitat_rule_id": rule_id,
        "habitat_confidence": confidence,
        "habitat_reason": reason,
        "habitat_review_required": bool(review_required),
        "habitat_candidate_rule_ids": json.dumps(candidate_rule_ids, sort_keys=True),
        "habitat_conflict": bool(conflict),
    }


def validate_labeled(
    source_count: int,
    labeled: gpd.GeoDataFrame,
    habitats: set[str],
    allow_count_change: bool,
) -> None:
    if source_count != EXPECTED_POI_COUNT and not allow_count_change:
        raise ValueError(
            f"Unexpected source POI count: {source_count}; expected {EXPECTED_POI_COUNT}. "
            "Use --allow-count-change only after reviewing upstream POI changes."
        )
    if len(labeled) != source_count:
        raise ValueError("Labeled output row count differs from source input.")
    if labeled["poi_id"].duplicated().any():
        dupes = labeled.loc[labeled["poi_id"].duplicated(), "poi_id"].head().tolist()
        raise ValueError(f"Duplicate poi_id values in labeled output: {dupes}")

    for field in ("habitat_primary", "habitat_secondary"):
        values = set(v for v in labeled[field].fillna("").astype(str) if v)
        invalid = values - habitats
        if invalid:
            raise ValueError(f"Invalid habitat values in {field}: {sorted(invalid)}")

    same = labeled[
        (labeled["habitat_primary"].fillna("") != "")
        & (labeled["habitat_primary"] == labeled["habitat_secondary"])
    ]
    if not same.empty:
        raise ValueError(f"Primary and secondary habitats match on {len(same)} POIs.")


def write_counts(labeled: gpd.GeoDataFrame, habitats: list[str]) -> None:
    rows = []
    for habitat in habitats:
        primary_count = int((labeled["habitat_primary"] == habitat).sum())
        secondary_count = int((labeled["habitat_secondary"] == habitat).sum())
        rows.append(
            {
                "habitat": habitat,
                "primary_count": primary_count,
                "secondary_count": secondary_count,
                "total_mentions": primary_count + secondary_count,
            }
        )
    pd.DataFrame(rows).to_csv(PROCESSED_DIR / "habitat_counts.csv", index=False)

    region_rows = []
    for region_id in sorted(labeled["region_id"].unique()):
        region_df = labeled[labeled["region_id"] == region_id]
        for habitat in habitats:
            region_rows.append(
                {
                    "region_id": region_id,
                    "habitat": habitat,
                    "primary_count": int((region_df["habitat_primary"] == habitat).sum()),
                    "secondary_count": int((region_df["habitat_secondary"] == habitat).sum()),
                }
            )
    pd.DataFrame(region_rows).to_csv(PROCESSED_DIR / "habitat_counts_by_region.csv", index=False)


def write_review_outputs(labeled: gpd.GeoDataFrame) -> None:
    unclassified = labeled[labeled["habitat_primary"].fillna("") == ""].copy()
    review_queue = labeled[
        (labeled["habitat_primary"].fillna("") == "")
        | (labeled["habitat_confidence"] == "low")
        | (labeled["habitat_review_required"])
        | (labeled["habitat_conflict"])
    ].copy()

    review_fields = [
        "poi_id",
        "region_id",
        "parent_city",
        "name",
        "primary_osm_key",
        "primary_osm_value",
        "raw_tags",
        "habitat_primary",
        "habitat_secondary",
        "habitat_rule_id",
        "habitat_candidate_rule_ids",
        "habitat_confidence",
        "habitat_reason",
        "habitat_review_required",
        "habitat_conflict",
    ]
    unclassified[review_fields].to_csv(PROCESSED_DIR / "unclassified_pois.csv", index=False)
    review_queue[review_fields].to_csv(PROCESSED_DIR / "habitat_review_queue.csv", index=False)


def write_report(labeled: gpd.GeoDataFrame) -> dict[str, Any]:
    total = len(labeled)
    classified = int((labeled["habitat_primary"].fillna("") != "").sum())
    unclassified = total - classified
    review_count = int(labeled["habitat_review_required"].sum())
    conflict_count = int(labeled["habitat_conflict"].sum())
    primary_counts = labeled["habitat_primary"].replace("", pd.NA).dropna().value_counts().to_dict()
    secondary_counts = labeled["habitat_secondary"].replace("", pd.NA).dropna().value_counts().to_dict()
    confidence_counts = labeled["habitat_confidence"].value_counts().to_dict()

    unclassified_df = labeled[labeled["habitat_primary"].fillna("") == ""]
    top_unclassified = (
        unclassified_df.groupby(["primary_osm_key", "primary_osm_value"])
        .size()
        .sort_values(ascending=False)
        .head(20)
        .to_dict()
    )
    rule_counts = labeled["habitat_rule_id"].replace("", pd.NA).dropna().value_counts().head(20).to_dict()

    report = {
        "total_pois": total,
        "classified_count": classified,
        "unclassified_count": unclassified,
        "classification_percentage": round(classified / total * 100, 2) if total else 0,
        "review_queue_count": review_count,
        "conflict_count": conflict_count,
        "primary_habitat_counts": json.dumps(primary_counts, sort_keys=True),
        "secondary_habitat_counts": json.dumps(secondary_counts, sort_keys=True),
        "confidence_counts": json.dumps(confidence_counts, sort_keys=True),
        "top_unclassified_osm_categories": json.dumps(
            {f"{k[0]}={k[1]}": v for k, v in top_unclassified.items()},
            sort_keys=True,
        ),
        "top_rule_ids": json.dumps(rule_counts, sort_keys=True),
    }
    pd.DataFrame([report]).to_csv(PROCESSED_DIR / "habitat_labeling_report.csv", index=False)
    return report


def write_maps(labeled: gpd.GeoDataFrame, habitats: list[str]) -> None:
    if not REGIONS_GEOJSON.exists():
        raise FileNotFoundError(f"Region GeoJSON missing: {REGIONS_GEOJSON}")
    regions = gpd.read_file(REGIONS_GEOJSON).to_crs("EPSG:4326")
    labeled = labeled.to_crs("EPSG:4326")
    point_geometry = [
        Point(float(row.representative_longitude), float(row.representative_latitude))
        for row in labeled.itertuples()
    ]
    labeled_points = gpd.GeoDataFrame(
        labeled.drop(columns="geometry"),
        geometry=point_geometry,
        crs="EPSG:4326",
    )

    palette = {
        "Healthcare": "#d62728",
        "Finance": "#2ca02c",
        "Retail": "#ff7f0e",
        "Food & Hospitality": "#8c564b",
        "Education & Research": "#1f77b4",
        "Transportation": "#17becf",
        "Civic & Government": "#9467bd",
        "Entertainment": "#e377c2",
        "Office & Business": "#7f7f7f",
        "Unclassified/Review": "#111111",
    }

    for city, filename in [
        ("Raleigh", "habitat_validation_raleigh.png"),
        ("Durham", "habitat_validation_durham.png"),
    ]:
        city_regions = regions[regions["parent_city"] == city]
        city_pois = labeled_points[labeled_points["parent_city"] == city].copy()
        fig, ax = plt.subplots(figsize=(14, 10))
        city_regions.boundary.plot(ax=ax, linewidth=1.8, edgecolor="#222222")
        for _, region in city_regions.iterrows():
            point = region.geometry.representative_point()
            ax.text(
                point.x,
                point.y,
                region["region_id"],
                fontsize=10,
                fontweight="bold",
                ha="center",
                va="center",
            )
        for habitat in habitats:
            subset = city_pois[city_pois["habitat_primary"] == habitat]
            if not subset.empty:
                subset.plot(
                    ax=ax,
                    markersize=22,
                    color=palette[habitat],
                    alpha=0.75,
                )
        review_subset = city_pois[
            (city_pois["habitat_primary"].fillna("") == "")
            | (city_pois["habitat_review_required"])
        ]
        if not review_subset.empty:
            review_subset.plot(
                ax=ax,
                markersize=55,
                facecolor="none",
                edgecolor=palette["Unclassified/Review"],
                linewidth=0.8,
            )
        ax.set_title(f"{city} Habitat Label Validation")
        ax.set_axis_off()
        handles = [
            Line2D(
                [0],
                [0],
                marker="o",
                color="none",
                markerfacecolor=palette[habitat],
                markeredgecolor=palette[habitat],
                markersize=6,
                label=habitat,
            )
            for habitat in habitats
            if (city_pois["habitat_primary"] == habitat).any()
        ]
        if (
            (city_pois["habitat_primary"].fillna("") == "")
            | (city_pois["habitat_review_required"])
        ).any():
            handles.append(
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="none",
                    markerfacecolor="none",
                    markeredgecolor=palette["Unclassified/Review"],
                    markersize=7,
                    label="Review/unclassified",
                )
            )
        ax.legend(handles=handles, loc="best", fontsize=8, frameon=True)
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / filename, dpi=200)
        plt.close(fig)


def print_summary(report: dict[str, Any], labeled: gpd.GeoDataFrame) -> None:
    print("Habitat labeling complete")
    for key, value in report.items():
        print(f"{key}: {value}")
    print("\nPrimary habitat counts")
    print(labeled["habitat_primary"].replace("", pd.NA).dropna().value_counts().to_string())
    print("\nSecondary habitat counts")
    print(labeled["habitat_secondary"].replace("", pd.NA).dropna().value_counts().to_string())
    print("\nConfidence distribution")
    print(labeled["habitat_confidence"].value_counts().to_string())


def main() -> None:
    args = parse_args()
    config = load_rules(RULES_PATH)
    habitats = list(config["habitats"])
    habitat_set = set(habitats)
    rules = config.get("rules", [])
    review_rules = config.get("review_rules", [])

    pois = load_pois()
    source_count = len(pois)

    labels = [
        classify_row(row, rules, review_rules, habitat_set)
        for _, row in pois.iterrows()
    ]
    labeled = pois.copy()
    for field in HABITAT_FIELDS:
        labeled[field] = [label[field] for label in labels]

    validate_labeled(source_count, labeled, habitat_set, args.allow_count_change)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    labeled.to_file(PROCESSED_DIR / "pois_labeled.geojson", driver="GeoJSON")
    csv_df = pd.DataFrame(labeled.drop(columns="geometry"))
    csv_df["geometry_wkt"] = labeled.geometry.to_wkt()
    csv_df.to_csv(PROCESSED_DIR / "pois_labeled.csv", index=False)

    write_counts(labeled, habitats)
    write_review_outputs(labeled)
    report = write_report(labeled)
    write_maps(labeled, habitats)
    print_summary(report, labeled)


if __name__ == "__main__":
    main()
