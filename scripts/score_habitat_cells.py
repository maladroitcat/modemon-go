#!/usr/bin/env python3
"""Build weighted Modemon GO habitat score cells from labeled POIs."""

from __future__ import annotations

import argparse
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import yaml
from matplotlib.lines import Line2D
from shapely.geometry import Point, box
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "data" / "config" / "habitat_spatial_config.yaml"
POIS_PATH = ROOT / "data" / "processed" / "pois_labeled.geojson"
REGIONS_PATH = ROOT / "data" / "processed" / "regions.geojson"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "output"

EXPECTED_REGIONS = {
    "RAL-01",
    "RAL-02",
    "RAL-03A",
    "RAL-03B",
    "RAL-04",
    "RAL-05",
    "DUR-01",
    "DUR-02",
}
EXPECTED_POI_COUNT = 927


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", help="Optional single region_id to process.")
    parser.add_argument(
        "--allow-count-change",
        action="store_true",
        help="Allow labeled POI count to differ from the current expected baseline.",
    )
    return parser.parse_args()


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing spatial config: {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    required = ["crs", "grid", "habitats", "regional_priors", "influence_tiers", "tier_rules"]
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"Spatial config missing required keys: {missing}")
    return config


def load_inputs(config: dict[str, Any], allow_count_change: bool) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    if not POIS_PATH.exists():
        raise FileNotFoundError(f"Missing labeled POIs: {POIS_PATH}")
    if not REGIONS_PATH.exists():
        raise FileNotFoundError(f"Missing canonical regions: {REGIONS_PATH}")

    pois = gpd.read_file(POIS_PATH)
    regions = gpd.read_file(REGIONS_PATH)
    if len(pois) != EXPECTED_POI_COUNT and not allow_count_change:
        raise ValueError(
            f"Unexpected labeled POI count {len(pois)}; expected {EXPECTED_POI_COUNT}. "
            "Use --allow-count-change only after reviewing upstream changes."
        )
    region_ids = set(regions["region_id"])
    if region_ids != EXPECTED_REGIONS:
        raise ValueError(f"Canonical region mismatch: found {sorted(region_ids)}")
    if set(config["regional_priors"]) != EXPECTED_REGIONS:
        raise ValueError("Spatial config regional priors must cover exactly the eight canonical regions.")

    habitats = set(config["habitats"])
    for field in ["habitat_primary", "habitat_secondary"]:
        values = set(v for v in pois[field].fillna("").astype(str) if v)
        invalid = values - habitats
        if invalid:
            raise ValueError(f"Invalid habitat values in {field}: {sorted(invalid)}")

    analysis_crs = config["crs"]["analysis"]
    return pois.to_crs(analysis_crs), regions.to_crs(analysis_crs)


def parse_raw_tags(raw_tags: Any) -> dict[str, str]:
    if raw_tags is None or (isinstance(raw_tags, float) and math.isnan(raw_tags)):
        return {}
    try:
        parsed = json.loads(str(raw_tags))
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(k): "" if v is None else str(v) for k, v in parsed.items()}


def tag_value(row: pd.Series, tags: dict[str, str], key: str) -> str | None:
    if key in tags and tags[key] not in ("", "nan", "None"):
        return str(tags[key])
    if row.get("primary_osm_key") == key and pd.notna(row.get("primary_osm_value")):
        return str(row.get("primary_osm_value"))
    return None


def condition_matches(condition: dict[str, Any], row: pd.Series, tags: dict[str, str]) -> bool:
    value = tag_value(row, tags, str(condition["key"]))
    if value is None:
        return False
    values = [str(v) for v in condition.get("values", [])]
    return "*" in values or value in values


def assign_tier(row: pd.Series, config: dict[str, Any]) -> str:
    tags = parse_raw_tags(row.get("raw_tags"))
    for tier in ["anchor", "micro"]:
        for condition in config["tier_rules"].get(tier, []):
            if condition_matches(condition, row, tags):
                return tier
    return "standard"


def representative_points(pois: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    points = [
        Point(float(row.representative_longitude), float(row.representative_latitude))
        for row in pois.to_crs("EPSG:4326").itertuples()
    ]
    return gpd.GeoDataFrame(
        pois.drop(columns="geometry"),
        geometry=points,
        crs="EPSG:4326",
    ).to_crs(pois.crs)


def generate_region_cells(
    region_id: str,
    region_geom,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    cell_size = (
        float(config["grid"]["cell_size_meters"])
        * float(config["grid"]["meters_to_feet"])
    )
    full_area = cell_size * cell_size
    min_pct = float(config["grid"]["minimum_retained_area_pct"])
    tiny_pct = float(config["grid"]["tiny_fragment_area_pct"])
    minx, miny, maxx, maxy = region_geom.bounds
    x0 = math.floor(minx / cell_size) * cell_size
    y0 = math.floor(miny / cell_size) * cell_size

    cells: list[dict[str, Any]] = []
    row_idx = 0
    y = y0
    while y < maxy:
        col_idx = 0
        x = x0
        while x < maxx:
            square = box(x, y, x + cell_size, y + cell_size)
            if square.intersects(region_geom):
                clipped = square.intersection(region_geom)
                if not clipped.is_empty:
                    clipped_area = clipped.area
                    retained_pct = clipped_area / full_area * 100
                    if retained_pct >= min_pct:
                        cells.append(
                            {
                                "region_id": region_id,
                                "grid_row": row_idx,
                                "grid_col": col_idx,
                                "full_cell_area_sqft": full_area,
                                "clipped_area_sqft": clipped_area,
                                "retained_area_pct": retained_pct,
                                "tiny_edge_fragment": retained_pct < tiny_pct,
                                "geometry": clipped,
                            }
                        )
            col_idx += 1
            x += cell_size
        row_idx += 1
        y += cell_size
    return cells


def decay_contribution(weight: float, radius_feet: float, distance_feet: float) -> float:
    return weight * math.exp(-distance_feet / radius_feet)


def cell_scores(
    cell_centroid,
    region_id: str,
    region_pois: gpd.GeoDataFrame,
    config: dict[str, Any],
) -> tuple[dict[str, float], dict[str, Any]]:
    habitats = list(config["habitats"])
    scores = {habitat: 0.0 for habitat in habitats}
    for habitat, value in config["regional_priors"].get(region_id, {}).items():
        scores[habitat] += float(value)

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    tier_meta = config["influence_tiers"]
    meters_to_feet = float(config["grid"]["meters_to_feet"])
    secondary_multiplier = float(config["secondary_habitat_multiplier"])

    for poi in region_pois.itertuples():
        tier = poi.influence_tier
        weight = float(tier_meta[tier]["weight"])
        radius_feet = float(tier_meta[tier]["radius_meters"]) * meters_to_feet
        distance = cell_centroid.distance(poi.geometry)
        base = decay_contribution(weight, radius_feet, distance)
        category = f"{poi.primary_osm_key}={poi.primary_osm_value}"

        if poi.habitat_primary:
            grouped[(poi.habitat_primary, category)].append(
                {
                    "value": base,
                    "poi_id": poi.poi_id,
                    "tier": tier,
                    "category": category,
                    "distance": distance,
                }
            )
        if poi.habitat_secondary:
            grouped[(poi.habitat_secondary, category)].append(
                {
                    "value": base * secondary_multiplier,
                    "poi_id": poi.poi_id,
                    "tier": tier,
                    "category": category,
                    "distance": distance,
                }
            )

    habitat_contribs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (habitat, _category), contribs in grouped.items():
        ranked = sorted(contribs, key=lambda item: item["value"], reverse=True)
        for rank, contrib in enumerate(ranked, start=1):
            damped = contrib["value"] / math.sqrt(rank)
            scores[habitat] += damped
            habitat_contribs[habitat].append({**contrib, "damped_value": damped})

    top_by_habitat = {}
    for habitat, contribs in habitat_contribs.items():
        top = sorted(contribs, key=lambda item: item["damped_value"], reverse=True)[:5]
        top_by_habitat[habitat] = [
            {
                "poi_id": item["poi_id"],
                "tier": item["tier"],
                "category": item["category"],
                "score": round(item["damped_value"], 4),
                "distance_feet": round(item["distance"], 1),
            }
            for item in top
        ]
    meta = {
        "top_contributors_json": json.dumps(top_by_habitat, sort_keys=True),
        "nearby_poi_count": int(len(region_pois)),
    }
    return scores, meta


def assign_cell_habitats(scores: dict[str, float], config: dict[str, Any]) -> dict[str, Any]:
    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    primary, primary_score = sorted_scores[0]
    secondary, secondary_score = sorted_scores[1]
    assignment = config["assignment"]

    if primary_score < float(assignment["minimum_primary_score"]):
        primary = ""
        secondary = ""
        confidence = "low"
        reason = "No regional prior or POI influence reached the minimum score."
    else:
        if (
            secondary_score >= float(assignment["secondary_minimum_score"])
            and secondary_score / primary_score >= float(assignment["secondary_minimum_ratio"])
        ):
            chosen_secondary = secondary
        else:
            chosen_secondary = ""

        margin = primary_score - secondary_score
        ratio = primary_score / secondary_score if secondary_score > 0 else float("inf")
        if (
            primary_score >= float(assignment["high_confidence_min_score"])
            and (
                margin >= float(assignment["high_confidence_min_margin"])
                or ratio >= float(assignment["high_confidence_min_ratio"])
            )
        ):
            confidence = "high"
        elif (
            primary_score >= float(assignment["medium_confidence_min_score"])
            and margin >= float(assignment["medium_confidence_min_margin"])
        ):
            confidence = "medium"
        else:
            confidence = "low"
        secondary = chosen_secondary
        reason = (
            f"Top score {primary_score:.2f}; second score {secondary_score:.2f}; "
            f"margin {margin:.2f}; ratio {ratio:.2f}."
        )

    return {
        "cell_habitat_primary": primary,
        "cell_habitat_secondary": secondary,
        "cell_confidence": confidence,
        "cell_assignment_reason": reason,
        "top_score": round(primary_score, 6),
        "second_score": round(secondary_score, 6),
    }


def build_cells(
    regions: gpd.GeoDataFrame,
    pois: gpd.GeoDataFrame,
    config: dict[str, Any],
    selected_region: str | None = None,
) -> gpd.GeoDataFrame:
    habitats = list(config["habitats"])
    poi_points = representative_points(pois)
    poi_points["influence_tier"] = poi_points.apply(assign_tier, axis=1, config=config)

    rows: list[dict[str, Any]] = []
    target_regions = regions
    if selected_region:
        if selected_region not in EXPECTED_REGIONS:
            raise ValueError(f"Unknown region_id: {selected_region}")
        target_regions = regions[regions["region_id"] == selected_region]

    for region in target_regions.itertuples():
        region_geom = region.geometry
        region_pois = poi_points[poi_points["region_id"] == region.region_id].copy()
        raw_cells = generate_region_cells(region.region_id, region_geom, config)
        for idx, cell in enumerate(raw_cells, start=1):
            centroid = cell["geometry"].centroid
            scores, meta = cell_scores(centroid, region.region_id, region_pois, config)
            assignment = assign_cell_habitats(scores, config)
            cell_id = f"{region.region_id}_cell_{idx:05d}"
            row = {
                "cell_id": cell_id,
                "region_id": region.region_id,
                "parent_city": region.parent_city,
                "display_name": region.display_name,
                "grid_row": cell["grid_row"],
                "grid_col": cell["grid_col"],
                "full_cell_area_sqft": round(cell["full_cell_area_sqft"], 3),
                "clipped_area_sqft": round(cell["clipped_area_sqft"], 3),
                "retained_area_pct": round(cell["retained_area_pct"], 3),
                "tiny_edge_fragment": bool(cell["tiny_edge_fragment"]),
                "regional_prior_json": json.dumps(
                    config["regional_priors"].get(region.region_id, {}),
                    sort_keys=True,
                ),
                "nearby_poi_count": meta["nearby_poi_count"],
                "top_contributors_json": meta["top_contributors_json"],
                "geometry": cell["geometry"],
                **assignment,
            }
            for habitat in habitats:
                key = "score_" + habitat.lower().replace(" & ", "_").replace(" ", "_")
                row[key] = round(scores[habitat], 6)
            rows.append(row)

    cells = gpd.GeoDataFrame(rows, geometry="geometry", crs=config["crs"]["analysis"])
    if cells.empty:
        raise ValueError("No habitat cells generated.")
    return cells


def clip_output_to_regions(
    cells_out: gpd.GeoDataFrame, regions: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    regions_out = regions.to_crs(cells_out.crs)
    region_geoms = regions_out.set_index("region_id").geometry.to_dict()
    clipped = cells_out.copy()
    clipped["geometry"] = [
        geom.intersection(region_geoms[region_id])
        for geom, region_id in zip(clipped.geometry, clipped["region_id"])
    ]
    if clipped.geometry.is_empty.any():
        empty_ids = clipped.loc[clipped.geometry.is_empty, "cell_id"].head().tolist()
        raise ValueError(f"Output clipping created empty cell geometries: {empty_ids}")
    return clipped


def write_outputs(cells: gpd.GeoDataFrame, regions: gpd.GeoDataFrame, config: dict[str, Any]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_crs = config["crs"]["output"]
    cells_out = clip_output_to_regions(cells.to_crs(output_crs), regions)
    cells_out.to_file(PROCESSED_DIR / "habitat_cells.geojson", driver="GeoJSON")

    csv_df = pd.DataFrame(cells_out.drop(columns="geometry"))
    csv_df["geometry_wkt"] = cells_out.geometry.to_wkt()
    csv_df.to_csv(PROCESSED_DIR / "habitat_cells.csv", index=False)

    summary = (
        cells.groupby(["region_id", "cell_habitat_primary", "cell_confidence"], dropna=False)
        .size()
        .reset_index(name="cell_count")
    )
    summary.to_csv(PROCESSED_DIR / "habitat_cell_counts_by_region.csv", index=False)

    rows = []
    for region_id, group in cells.groupby("region_id"):
        rows.append(
            {
                "region_id": region_id,
                "cell_count": len(group),
                "tiny_edge_fragments": int(group["tiny_edge_fragment"].sum()),
                "mean_retained_area_pct": round(group["retained_area_pct"].mean(), 3),
                "low_confidence_cells": int((group["cell_confidence"] == "low").sum()),
                "unclassified_cells": int((group["cell_habitat_primary"].fillna("") == "").sum()),
            }
        )
    pd.DataFrame(rows).to_csv(PROCESSED_DIR / "habitat_cell_report.csv", index=False)


def write_maps(cells: gpd.GeoDataFrame, regions: gpd.GeoDataFrame, config: dict[str, Any]) -> None:
    habitats = list(config["habitats"])
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
        "Unclassified": "#f2f2f2",
    }
    cells_4326 = cells.to_crs("EPSG:4326")
    regions_4326 = regions.to_crs("EPSG:4326")

    for city, filename in [
        ("Raleigh", "habitat_cells_raleigh.png"),
        ("Durham", "habitat_cells_durham.png"),
    ]:
        city_cells = cells_4326[cells_4326["parent_city"] == city]
        city_regions = regions_4326[regions_4326["parent_city"] == city]
        fig, ax = plt.subplots(figsize=(14, 10))
        for habitat in habitats:
            subset = city_cells[city_cells["cell_habitat_primary"] == habitat]
            if not subset.empty:
                subset.plot(
                    ax=ax,
                    color=palette[habitat],
                    edgecolor="white",
                    linewidth=0.15,
                    alpha=0.72,
                )
        unclassified = city_cells[city_cells["cell_habitat_primary"].fillna("") == ""]
        if not unclassified.empty:
            unclassified.plot(
                ax=ax,
                color=palette["Unclassified"],
                edgecolor="#999999",
                linewidth=0.15,
                alpha=0.8,
            )
        low = city_cells[city_cells["cell_confidence"] == "low"]
        if not low.empty:
            low.boundary.plot(ax=ax, color="#111111", linewidth=0.35, alpha=0.6)
        city_regions.boundary.plot(ax=ax, linewidth=1.4, edgecolor="#111111")
        for region in city_regions.itertuples():
            point = region.geometry.representative_point()
            ax.text(point.x, point.y, region.region_id, fontsize=10, fontweight="bold", ha="center")
        handles = [
            Line2D([0], [0], marker="s", color="none", markerfacecolor=palette[h], markersize=7, label=h)
            for h in habitats
            if (city_cells["cell_habitat_primary"] == h).any()
        ]
        handles.append(
            Line2D([0], [0], color="#111111", linewidth=1, label="Low confidence outline")
        )
        ax.legend(handles=handles, loc="best", fontsize=8, frameon=True)
        ax.set_title(f"{city} Habitat Cell Score QA")
        ax.set_axis_off()
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / filename, dpi=200)
        plt.close(fig)


def validate_cells(cells: gpd.GeoDataFrame, regions: gpd.GeoDataFrame, config: dict[str, Any]) -> None:
    habitats = set(config["habitats"])
    invalid_primary = set(v for v in cells["cell_habitat_primary"].fillna("").astype(str) if v) - habitats
    invalid_secondary = set(v for v in cells["cell_habitat_secondary"].fillna("").astype(str) if v) - habitats
    if invalid_primary or invalid_secondary:
        raise ValueError(f"Invalid cell habitats: primary={invalid_primary}, secondary={invalid_secondary}")
    same = cells[
        (cells["cell_habitat_primary"].fillna("") != "")
        & (cells["cell_habitat_primary"] == cells["cell_habitat_secondary"])
    ]
    if not same.empty:
        raise ValueError(f"Cells have identical primary and secondary habitats: {len(same)}")
    if cells["cell_id"].duplicated().any():
        raise ValueError("Duplicate cell_id values generated.")

    region_geoms = regions.set_index("region_id").geometry.to_dict()
    for cell in cells.itertuples():
        outside = cell.geometry.difference(region_geoms[cell.region_id])
        if not outside.is_empty and outside.area > 1e-6:
            raise ValueError(f"Cell extends outside region: {cell.cell_id}")


def print_summary(cells: gpd.GeoDataFrame) -> None:
    print("Habitat cell scoring complete")
    print(f"total_cells: {len(cells)}")
    print("\nCells by region")
    print(cells.groupby("region_id").size().to_string())
    print("\nPrimary habitat cells")
    print(cells["cell_habitat_primary"].replace("", pd.NA).dropna().value_counts().to_string())
    print("\nConfidence")
    print(cells["cell_confidence"].value_counts().to_string())
    print("\nTiny edge fragments by region")
    print(cells.groupby("region_id")["tiny_edge_fragment"].sum().astype(int).to_string())


def main() -> None:
    args = parse_args()
    config = load_config()
    pois, regions = load_inputs(config, args.allow_count_change)
    cells = build_cells(regions, pois, config, selected_region=args.region)
    validate_cells(cells, regions, config)
    write_outputs(cells, regions, config)
    write_maps(cells, regions, config)
    print_summary(cells)


if __name__ == "__main__":
    main()
