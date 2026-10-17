#!/usr/bin/env python3
"""Derive region-resolution QA coordinates and record read-only routing results."""

import argparse
import hashlib
import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import unary_union

import resolve_game_region as routing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zone-qa-dir", type=Path, default=routing.ROOT / "data/processed")
    parser.add_argument("--zone-source-commit", help="Commit identifying a separate committed zone QA snapshot")
    args = parser.parse_args()
    before = routing.canonical_input_hashes()
    resolver = routing.RegionResolver()
    regions = resolver.regions.set_index("region_id")
    projected = resolver.regions.to_crs("EPSG:2264").set_index("region_id")
    cells = gpd.read_file(routing.ROOT / "data/processed/habitat_cells.geojson").to_crs("EPSG:2264")
    zone_paths = [args.zone_qa_dir / "habitat_zones.geojson",
                  args.zone_qa_dir / "habitat_unclassified_areas.geojson"]
    snapshots = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in zone_paths}
    zones, neutral = [gpd.read_file(p) for p in zone_paths]
    cases = []
    for rule in resolver.rules:
        winner, loser = rule["winner"], rule["loser"]
        overlap = regions.loc[winner].geometry.intersection(regions.loc[loser].geometry)
        point = overlap.representative_point()
        area = projected.loc[winner].geometry.intersection(projected.loc[loser].geometry).area
        retained_area = unary_union(cells.loc[cells.region_id == winner].geometry).intersection(
            unary_union(cells.loc[cells.region_id == loser].geometry)).area
        result = resolver.resolve(point.x, point.y)
        if result["resolved_region_id"] != winner:
            raise AssertionError(f"Wrong owner for {winner}/{loser}")
        cases.append({"winner": winner, "loser": loser, "reason": rule["reason"],
                      "canonical_overlap_area_sqft": area, "canonical_overlap_area_acres": area / 43560,
                      "retained_cell_overlap_area_acres": retained_area / 43560,
                      "derived_point": {"longitude": point.x, "latitude": point.y},
                      "resolver_result": result,
                      "zone_lookup_result": routing.resolve_habitat_zone(point.x, point.y, resolver, zones, neutral)})

    single_point = regions.loc["RAL-05"].geometry.difference(
        unary_union(regions.drop("RAL-05").geometry)).representative_point()
    _, _, maxx, maxy = resolver.regions.total_bounds
    geometry = regions.loc["RAL-05"].geometry
    polygon = geometry if geometry.geom_type == "Polygon" else list(geometry.geoms)[0]
    boundary = Point(polygon.exterior.coords[0])
    report = {
        "overlap_cases": cases,
        "single_region_case": resolver.resolve(single_point.x, single_point.y),
        "outside_region_case": resolver.resolve(maxx + 0.1, maxy + 0.1),
        "boundary_case": resolver.resolve(boundary.x, boundary.y),
        "zone_snapshot_provenance": {"source_commit": args.zone_source_commit, "sha256": snapshots},
        "canonical_input_file_count": len(before), "canonical_input_sha256": before,
        "canonical_inputs_byte_for_byte_unchanged": True,
    }
    routing.assert_canonical_inputs_unchanged(before)
    for path in zone_paths:
        if hashlib.sha256(path.read_bytes()).hexdigest() != snapshots[path.name]:
            raise RuntimeError(f"Zone QA snapshot changed: {path.name}")
    destination = routing.ROOT / "output/region_resolution_qa.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"overlap_cases": cases, "single_region_case": report["single_region_case"],
                      "outside_region_case": report["outside_region_case"],
                      "canonical_input_file_count": len(before),
                      "canonical_inputs_byte_for_byte_unchanged": True}, indent=2))


if __name__ == "__main__":
    main()
