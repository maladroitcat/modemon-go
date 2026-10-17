#!/usr/bin/env python3
"""Dissolve canonical scored cells into auditable rook-connected gameplay zones."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch
from shapely import snap
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
OUTPUT = ROOT / "output"
HABITATS = [
    "Healthcare", "Finance", "Retail", "Food & Hospitality",
    "Education & Research", "Transportation", "Civic & Government",
    "Entertainment", "Office & Business",
]
REGIONS = {"DUR-01", "DUR-02", "RAL-01", "RAL-02", "RAL-03A", "RAL-03B", "RAL-04", "RAL-05"}
ANALYSIS_CRS = "EPSG:2264"
OUTPUT_CRS = "EPSG:4326"
# Tolerance is for floating-point reprojection only; geometries are never snapped for union.
COORD_TOL_FT = 1e-6
MIN_SHARED_EDGE_FT = 0.01
AREA_ABS_TOL_SQFT = 0.01
AREA_REL_TOL = 1e-8
COLORS = dict(zip(HABITATS, [
    "#d62728", "#2ca02c", "#ff7f0e", "#8c564b", "#1f77b4",
    "#17becf", "#9467bd", "#e377c2", "#7f7f7f",
]))


def area_tolerance(area):
    return max(AREA_ABS_TOL_SQFT, abs(area) * AREA_REL_TOL)


def slug(habitat):
    return habitat.lower().replace(" & ", "_").replace(" ", "_") or "unclassified"


def component_id(region_id, habitat, cell_ids):
    digest = hashlib.sha256(json.dumps(sorted(cell_ids), separators=(",", ":")).encode()).hexdigest()[:12]
    return f"{region_id}_{slug(habitat)}_{digest}"


def rook_adjacent(a, b):
    """Require an edge, allowing only sub-micrometer coordinate roundoff."""
    if a.boundary.intersection(b.boundary).length > MIN_SHARED_EDGE_FT:
        return True
    if a.distance(b) > COORD_TOL_FT:
        return False
    # Snap boundaries for the predicate only. The dissolve always uses untouched cells.
    return max(
        snap(a.boundary, b.boundary, COORD_TOL_FT).intersection(b.boundary).length,
        snap(b.boundary, a.boundary, COORD_TOL_FT).intersection(a.boundary).length,
    ) > MIN_SHARED_EDGE_FT


def connected_components(group):
    group = group.sort_values("cell_id").reset_index(drop=True)
    graph = {i: set() for i in range(len(group))}
    index = group.sindex
    for i, geom in enumerate(group.geometry):
        x0, y0, x1, y1 = geom.bounds
        candidates = index.intersection((x0-COORD_TOL_FT, y0-COORD_TOL_FT,
                                         x1+COORD_TOL_FT, y1+COORD_TOL_FT))
        for j in candidates:
            j = int(j)
            if j > i and rook_adjacent(geom, group.geometry.iloc[j]):
                graph[i].add(j)
                graph[j].add(i)
    unseen = set(graph)
    components = []
    while unseen:
        pending = [min(unseen)]
        members = []
        unseen.remove(pending[0])
        while pending:
            i = pending.pop()
            members.append(i)
            for j in sorted(graph[i]):
                if j in unseen:
                    unseen.remove(j)
                    pending.append(j)
        components.append(group.iloc[sorted(members)].copy())
    return components


def weighted_mean(values, areas):
    mask = values.notna() & values.map(lambda v: pd.isna(v) or math.isfinite(v))
    if not mask.any():
        return None
    return float((values[mask] * areas[mask]).sum() / areas[mask].sum())


def aggregate(component, habitat):
    if component.region_id.nunique() != 1 or component.cell_habitat_primary.nunique(dropna=False) != 1:
        raise ValueError("Mixed region or primary habitat in connected component")
    geometry = unary_union(component.geometry.tolist())
    if geometry.is_empty or not geometry.is_valid or geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Invalid dissolved geometry; source cells require investigation")
    areas = component.geometry.area
    source_area = float(areas.sum())
    if abs(geometry.area - source_area) > area_tolerance(source_area):
        raise ValueError("Zone union disagrees with source-cell area")
    cell_ids = sorted(component.cell_id.tolist())
    ratio = pd.to_numeric(component.top_to_second_ratio, errors="coerce")
    secondary_areas = component.assign(weight=areas).groupby("cell_habitat_secondary").weight.sum()
    distribution = {str(k): float(v / source_area * 100) for k, v in secondary_areas.items() if k}
    dominant = sorted(distribution, key=lambda h: (-distribution[h], h))
    best = dominant[0] if dominant else ""
    dominant_pct = distribution.get(best, 0.0)
    micro = len(component) == 1 or geometry.area < 2 * 43560
    metadata_issues = []
    if component.parent_city.nunique() != 1:
        metadata_issues.append("inconsistent_parent_city")
    if ((component.clipped_area_sqft - areas).abs() > areas.map(area_tolerance)).any():
        metadata_issues.append("stored_clipped_area_differs_from_geometry")
    if not component.cell_confidence.isin(["high", "medium", "low"]).all():
        metadata_issues.append("inconsistent_confidence")
    suspicious = geometry.geom_type == "MultiPolygon"
    reasons = list(metadata_issues)
    if suspicious:
        reasons.append("multipart_exact_source_union")
    if micro:
        reasons.append("micro_zone")
    row = {
        "zone_id": component_id(component.region_id.iloc[0], habitat, cell_ids),
        "region_id": component.region_id.iloc[0], "parent_city": component.parent_city.iloc[0],
        "habitat_primary": habitat, "cell_count": len(component),
        "source_cell_ids": json.dumps(cell_ids, separators=(",", ":")),
        "area_sqft": geometry.area, "area_acres": geometry.area / 43560,
        "area_sq_miles": geometry.area / 27878400,
        "mean_top_score": weighted_mean(component.top_score, areas),
        "mean_second_score": weighted_mean(component.second_score, areas),
        "mean_top_to_second_ratio": weighted_mean(ratio, areas),
        "finite_ratio_area_pct": float(areas[ratio.notna()].sum() / source_area * 100),
        "secondary_habitat_distribution_json": json.dumps(distribution, sort_keys=True),
        "dominant_secondary_habitat": best if dominant_pct >= 30 else "",
        "dominant_secondary_area_pct": dominant_pct if dominant_pct >= 30 else 0.0,
        "micro_zone": bool(micro), "suspicious_geometry": suspicious,
        "source_metadata_inconsistent": bool(metadata_issues), "geometry": geometry,
    }
    for confidence in ["high", "medium", "low"]:
        mask = component.cell_confidence == confidence
        row[f"{confidence}_confidence_cell_count"] = int(mask.sum())
        row[f"{confidence}_confidence_area_pct"] = float(areas[mask].sum() / source_area * 100)
    if row["low_confidence_area_pct"] > 30:
        reasons.append("low_confidence_area_over_30pct")
    row["review_required"] = bool(reasons)
    row["review_reasons"] = json.dumps(reasons)
    return row


def load_inputs():
    cells = gpd.read_file(DATA / "habitat_cells.geojson")
    regions = gpd.read_file(DATA / "regions.geojson")
    if cells.crs is None or regions.crs is None:
        raise ValueError("Missing source CRS")
    cells["cell_habitat_primary"] = cells.cell_habitat_primary.fillna("")
    cells["cell_habitat_secondary"] = cells.cell_habitat_secondary.fillna("")
    if len(cells) != 1998 or (cells.cell_habitat_primary != "").sum() != 1993:
        raise ValueError("Expected canonical baseline: 1998 cells, 1993 classified, 5 unclassified")
    if cells.cell_id.isna().any() or cells.cell_id.duplicated().any():
        raise ValueError("Missing or duplicate source cell IDs")
    if set(regions.region_id) != REGIONS or len(regions) != 8 or set(cells.region_id) != REGIONS:
        raise ValueError("Expected exactly eight canonical regions")
    if set(cells.cell_habitat_primary) - set(HABITATS) - {""}:
        raise ValueError("Invalid primary habitat")
    if set(cells.cell_habitat_secondary) - set(HABITATS) - {""}:
        raise ValueError("Invalid secondary habitat")
    if not cells.geometry.is_valid.all() or cells.geometry.is_empty.any():
        raise ValueError("Invalid source cell geometry")
    cells = cells.to_crs(ANALYSIS_CRS)
    regions = regions.to_crs(ANALYSIS_CRS)
    if not cells.cell_confidence.isin(["high", "medium", "low"]).all():
        raise ValueError("Missing or invalid cell confidence")
    return cells, regions


def build_zones(cells):
    zones, neutral, membership = [], [], []
    for (_, habitat), group in cells.groupby(["region_id", "cell_habitat_primary"], sort=True):
        for component in connected_components(group):
            row = aggregate(component, habitat)
            (zones if habitat else neutral).append(row)
            for cell in component.itertuples():
                membership.append({
                    "zone_id": row["zone_id"], "cell_id": cell.cell_id,
                    "region_id": cell.region_id, "habitat_primary": habitat,
                    "cell_confidence": cell.cell_confidence,
                    "cell_secondary_habitat": cell.cell_habitat_secondary,
                    "clipped_cell_area_sqft": cell.geometry.area,
                    "classified": bool(habitat),
                })
    return (gpd.GeoDataFrame(zones, geometry="geometry", crs=ANALYSIS_CRS).sort_values("zone_id"),
            gpd.GeoDataFrame(neutral, geometry="geometry", crs=ANALYSIS_CRS).sort_values("zone_id"),
            pd.DataFrame(membership).sort_values(["zone_id", "cell_id"]))


def all_areas(zones, neutral):
    return gpd.GeoDataFrame(zones.to_dict("records") + neutral.to_dict("records"),
                            geometry="geometry", crs=ANALYSIS_CRS).reset_index(drop=True)


def overlap_diagnostics(cells, zones, neutral):
    areas = all_areas(zones, neutral)
    source = cells.set_index("cell_id")
    rows = []
    for i, geometry in enumerate(areas.geometry):
        for j in areas.sindex.query(geometry, predicate="intersects"):
            if j <= i:
                continue
            overlap = geometry.intersection(areas.geometry.iloc[j])
            if overlap.area <= AREA_ABS_TOL_SQFT:
                continue
            a, b = areas.iloc[i], areas.iloc[j]
            inherited = unary_union(source.loc[json.loads(a.source_cell_ids)].geometry).intersection(
                unary_union(source.loc[json.loads(b.source_cell_ids)].geometry))
            rows.append({
                "zone_id_a": a.zone_id, "zone_id_b": b.zone_id,
                "region_id_a": a.region_id, "region_id_b": b.region_id,
                "overlap_area_sqft": overlap.area, "overlap_area_acres": overlap.area / 43560,
                "inherited_source_overlap_sqft": inherited.area,
                "introduced_overlap_sqft": overlap.difference(inherited).area,
                "cross_region": a.region_id != b.region_id,
            })
    return pd.DataFrame(rows, columns=[
        "zone_id_a", "zone_id_b", "region_id_a", "region_id_b", "overlap_area_sqft",
        "overlap_area_acres", "inherited_source_overlap_sqft", "introduced_overlap_sqft", "cross_region",
    ])


def validate(cells, regions, zones, neutral, membership, overlaps, allow_inherited_overlaps=False):
    all_zones = all_areas(zones, neutral)
    if all_zones.zone_id.duplicated().any():
        raise ValueError("Duplicate zone IDs")
    counts = membership.cell_id.value_counts()
    if set(counts.index) != set(cells.cell_id) or not counts.eq(1).all():
        raise ValueError("Every classified and unclassified cell must have exactly one membership")
    source = cells.set_index("cell_id")
    for zone in all_zones.itertuples():
        ids = json.loads(zone.source_cell_ids)
        part = source.loc[ids]
        if set(part.region_id) != {zone.region_id} or set(part.cell_habitat_primary) != {zone.habitat_primary}:
            raise ValueError(f"Inconsistent cell metadata in {zone.zone_id}")
        entries = membership[membership.zone_id == zone.zone_id]
        if set(entries.cell_id) != set(ids) or set(entries.habitat_primary) != {zone.habitat_primary}:
            raise ValueError("Membership does not match zone provenance")
        if not zone.geometry.is_valid or zone.geometry.is_empty:
            raise ValueError(f"Invalid zone {zone.zone_id}")
        if zone.geometry.symmetric_difference(unary_union(part.geometry)).area > area_tolerance(zone.area_sqft):
            raise ValueError("Zone does not match exact source union")
        parent = regions[regions.region_id == zone.region_id].geometry.iloc[0]
        if zone.geometry.difference(parent).area > area_tolerance(zone.area_sqft):
            raise ValueError(f"Zone outside canonical region: {zone.zone_id}")
    # Exceptions require an explicit invocation; default validation remains strict.
    for overlap in overlaps.itertuples():
        if (not allow_inherited_overlaps or not overlap.cross_region
                or overlap.introduced_overlap_sqft > AREA_ABS_TOL_SQFT):
            raise ValueError(
                f"Meaningful zone overlap: {overlap.zone_id_a}, {overlap.zone_id_b}: "
                f"{overlap.overlap_area_sqft:.6f} sq ft. See habitat_zone_overlap_diagnostics.csv."
            )
    coverage = []
    for region_id, group in cells.groupby("region_id"):
        parts = all_zones[all_zones.region_id == region_id]
        retained = float(group.geometry.area.sum())
        difference = float(parts.area_sqft.sum() - retained)
        symdiff = unary_union(parts.geometry).symmetric_difference(unary_union(group.geometry)).area
        if abs(difference) > area_tolerance(retained) or symdiff > area_tolerance(retained):
            raise ValueError(f"Coverage mismatch: {region_id}: {difference} sq ft")
        coverage.append({"region_id": region_id, "retained_cell_area_sqft": retained,
                         "zone_plus_neutral_area_sqft": float(parts.area_sqft.sum()),
                         "coverage_difference_sqft": difference, "symmetric_difference_sqft": symdiff})
    return pd.DataFrame(coverage)


def json_counts(series):
    return json.dumps({str(k): int(v) for k, v in series.value_counts().items()}, sort_keys=True)


def write_outputs(zones, neutral, membership, coverage):
    for name, frame in [("habitat_zones", zones), ("habitat_unclassified_areas", neutral)]:
        exported = frame.to_crs(OUTPUT_CRS)
        if not exported.geometry.is_valid.all():
            raise ValueError("Invalid geometry after export reprojection")
        exported.to_file(DATA / f"{name}.geojson", driver="GeoJSON")
        if name == "habitat_zones":
            flat = pd.DataFrame(exported.drop(columns="geometry"))
            flat["geometry_wkt"] = exported.geometry.to_wkt()
            flat.to_csv(DATA / f"{name}.csv", index=False)
    membership.to_csv(DATA / "habitat_zone_cell_membership.csv", index=False)
    coverage.to_csv(DATA / "habitat_zone_coverage.csv", index=False)
    summaries = []
    for region_id in sorted(REGIONS):
        part = zones[zones.region_id == region_id]
        summaries.append({
            "region_id": region_id, "total_zones": len(part),
            "zones_by_primary_habitat": json_counts(part.habitat_primary),
            "total_classified_area_sqft": part.area_sqft.sum(),
            "total_classified_area_acres": part.area_acres.sum(),
            "unclassified_area_sqft": neutral.loc[neutral.region_id == region_id, "area_sqft"].sum(),
            "micro_zone_count": int(part.micro_zone.sum()),
            "review_required_zone_count": int(part.review_required.sum()),
            "mean_zone_area_acres": part.area_acres.mean(),
            "median_zone_area_acres": part.area_acres.median(),
        })
    pd.DataFrame(summaries).to_csv(DATA / "habitat_zone_summary_by_region.csv", index=False)
    global_summary = {
        "total_zones": len(zones), "zones_by_habitat": json_counts(zones.habitat_primary),
        "total_area_acres_by_habitat": json.dumps(zones.groupby("habitat_primary").area_acres.sum().to_dict(), sort_keys=True),
        "micro_zone_count": int(zones.micro_zone.sum()),
        "review_required_count": int(zones.review_required.sum()),
        "unclassified_area_sqft": neutral.area_sqft.sum(),
        "unclassified_area_acres": neutral.area_acres.sum(),
    }
    pd.DataFrame([global_summary]).to_csv(DATA / "habitat_zone_summary_global.csv", index=False)


def write_maps(zones, neutral, regions):
    OUTPUT.mkdir(exist_ok=True)
    for city in ["Raleigh", "Durham"]:
        part = zones[zones.parent_city == city]
        gaps = neutral[neutral.parent_city == city]
        parents = regions[regions.parent_city == city]
        for review in [False, True]:
            fig, ax = plt.subplots(figsize=(14, 10))
            handles = []
            if review:
                categories = [
                    (part[~part.review_required], "#d5e8dc", "No review flag"),
                    (part[part.review_required & ~part.micro_zone], "#f0a35b", "Review required"),
                    (part[part.micro_zone], "#c7568b", "Micro-zone (review)"),
                ]
            else:
                categories = [(part[part.habitat_primary == h], COLORS[h], h) for h in HABITATS]
            for subset, color, label in categories:
                if not subset.empty:
                    subset.plot(ax=ax, color=color, edgecolor="#444444", linewidth=0.65, alpha=0.85)
                    handles.append(Patch(facecolor=color, edgecolor="#444444", label=label))
            if not gaps.empty:
                gaps.plot(ax=ax, color="#eeeeee", edgecolor="#555555", hatch="///", linewidth=0.8)
            handles.append(Patch(facecolor="#eeeeee", edgecolor="#555555", hatch="///", label="Unclassified"))
            parents.boundary.plot(ax=ax, color="#111111", linewidth=1.4)
            for region in parents.itertuples():
                point = region.geometry.representative_point()
                ax.text(point.x, point.y, region.region_id, fontsize=10, weight="bold", ha="center")
            ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8)
            ax.set_title(f"{city} Habitat Zones" + (": Review QA" if review else ": Primary Habitat QA"))
            ax.set_axis_off()
            ax.set_aspect("equal")
            fig.tight_layout()
            suffix = "_review" if review else ""
            fig.savefig(OUTPUT / f"habitat_zones_{city.lower()}{suffix}.png", dpi=180)
            plt.close(fig)


def markdown_table(frame):
    # No optional tabulate dependency needed for reproducible reports.
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"]*len(columns)) + " |"]
    for row in frame.itertuples(index=False, name=None):
        values = [f"{v:.4f}" if isinstance(v, float) else str(v) for v in row]
        lines.append("| " + " | ".join(v.replace("|", "\\|") for v in values) + " |")
    return "\n".join(lines)


def write_report(zones, neutral, coverage, source_hashes, overlaps):
    lines = ["# Step 7B Habitat Zone QA", "", f"Total habitat zones: {len(zones)}.",
             f"Micro-zones: {int(zones.micro_zone.sum())}; review required: {int(zones.review_required.sum())}.",
             "All 1,993 classified cells and all 5 neutral cells have exactly one membership. Cell inputs are unchanged.", "",
             "## Zones and Area by Habitat", ""]
    totals = zones.groupby("habitat_primary").agg(zones=("zone_id", "size"), area_acres=("area_acres", "sum"))
    lines.append(markdown_table(totals.reindex(HABITATS, fill_value=0).reset_index()))
    lines += ["", "## Region Breakdowns", ""]
    for region_id in sorted(REGIONS):
        part = zones[zones.region_id == region_id]
        lines += [f"### {region_id}", "", f"Zones: {len(part)}. Neutral area: {neutral.loc[neutral.region_id == region_id, 'area_acres'].sum():.6f} acres.", ""]
        by_habitat = part.groupby("habitat_primary").agg(zones=("zone_id", "size"), cells=("cell_count", "sum"), area_acres=("area_acres", "sum"))
        lines += [markdown_table(by_habitat.reset_index()), ""]
    lines += ["## Largest Zone per Region", "", markdown_table(zones.loc[zones.groupby("region_id").area_acres.idxmax(), ["zone_id", "cell_count", "area_acres"]]), "",
              "## Smallest Five Zones", "", markdown_table(zones.nsmallest(5, "area_acres")[["zone_id", "cell_count", "area_acres", "review_reasons"]]), "",
              "## Zones with More Than 30% Low-confidence Area", "", markdown_table(zones[zones.low_confidence_area_pct > 30][["zone_id", "cell_count", "area_acres", "low_confidence_area_pct"]]), "",
              "## Dominant Secondary Counts", "", markdown_table(zones.dominant_secondary_habitat.replace("", "(none)").value_counts().rename_axis("habitat").reset_index(name="zones")), "",
              "## Coverage", "", markdown_table(coverage), "",
              "Coverage uses retained cell area, not full region area. No unexplained coverage differences exceed the numerical tolerance.", "",
              "## Geometry Review", "", f"Exact unions with multiple polygon parts: {int(zones.suspicious_geometry.sum())}; source metadata inconsistencies: {int(zones.source_metadata_inconsistent.sum())}.",
              "MultiPolygon source cells remain atomic membership units. Their disconnected fragments remain disconnected in exact zone geometry and are flagged for review.", "",
              "## Inherited Cross-region Overlaps", "", markdown_table(overlaps), "",
              "These overlaps exist in canonical cells. No overlap was introduced by the dissolve. Coverage is accounted per region.", "",
              "## Input SHA-256", "", json.dumps(source_hashes, indent=2), "",
              "## Maps", "", "![Raleigh primary](habitat_zones_raleigh.png)", "![Durham primary](habitat_zones_durham.png)",
              "![Raleigh review](habitat_zones_raleigh_review.png)", "![Durham review](habitat_zones_durham_review.png)"]
    (OUTPUT / "habitat_zone_qa_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def input_hashes():
    paths = [DATA / "habitat_cells.geojson", DATA / "habitat_cells.csv", DATA / "regions.geojson",
             ROOT / "data/config/habitat_spatial_config.yaml"]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-inherited-region-overlaps", action="store_true",
                        help="Explicitly preserve and report canonical cross-region overlaps; new or within-region overlaps still fail.")
    args = parser.parse_args()
    before = input_hashes()
    cells, regions = load_inputs()
    zones, neutral, membership = build_zones(cells)
    overlaps = overlap_diagnostics(cells, zones, neutral)
    overlaps.to_csv(DATA / "habitat_zone_overlap_diagnostics.csv", index=False)
    coverage = validate(cells, regions, zones, neutral, membership, overlaps,
                        allow_inherited_overlaps=args.allow_inherited_region_overlaps)
    write_outputs(zones, neutral, membership, coverage)
    write_maps(zones, neutral, regions)
    if input_hashes() != before:
        raise ValueError("Canonical input files changed during zone construction")
    write_report(zones, neutral, coverage, before, overlaps)
    print(f"Zones: {len(zones)}; micro: {int(zones.micro_zone.sum())}; review: {int(zones.review_required.sum())}")
    print(f"Neutral components: {len(neutral)}; neutral cells: {int(neutral.cell_count.sum())}")
    print(coverage.to_string(index=False))


if __name__ == "__main__":
    main()
