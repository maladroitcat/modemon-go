#!/usr/bin/env python3
"""Derive region-resolution QA coordinates and record read-only routing results."""

import hashlib
import json
import subprocess

import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import unary_union

import resolve_game_region as routing


def main():
    before = routing.canonical_input_hashes()
    resolver = routing.RegionResolver()
    regions = resolver.regions.set_index("region_id")
    projected = resolver.regions.to_crs("EPSG:2264").set_index("region_id")
    cells = gpd.read_file(routing.ROOT / "data/processed/habitat_cells.geojson").to_crs("EPSG:2264")
    zone_paths = [routing.ZONES_PATH, routing.NEUTRAL_PATH]
    zone_files = []
    for path in zone_paths:
        relative = path.relative_to(routing.ROOT).as_posix()
        committed = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=routing.ROOT)
        contents = path.read_bytes()
        if contents != committed:
            raise RuntimeError(f"Canonical zone file differs from committed data: {relative}")
        zone_files.append({
            "repository_path": relative,
            "sha256": hashlib.sha256(contents).hexdigest(),
            "git_blob_id": subprocess.check_output(
                ["git", "rev-parse", f"HEAD:{relative}"], cwd=routing.ROOT, text=True).strip(),
            "last_content_commit": subprocess.check_output(
                ["git", "log", "-1", "--format=%H", "--", relative], cwd=routing.ROOT, text=True).strip(),
        })
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
                      "zone_lookup_result": routing.resolve_habitat_zone(point.x, point.y, resolver)})

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
        "zone_provenance": {"source": "canonical_committed_repository_files", "files": zone_files},
        "canonical_input_file_count": len(before), "canonical_input_sha256": before,
        "canonical_inputs_byte_for_byte_unchanged": True,
    }
    routing.assert_canonical_inputs_unchanged(before)
    destination = routing.ROOT / "output/region_resolution_qa.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"overlap_cases": cases, "single_region_case": report["single_region_case"],
                      "outside_region_case": report["outside_region_case"],
                      "canonical_input_file_count": len(before),
                      "canonical_inputs_byte_for_byte_unchanged": True}, indent=2))


if __name__ == "__main__":
    main()
