#!/usr/bin/env python3
"""Route WGS84 coordinates to one gameplay region using explicit precedence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import geopandas as gpd
import yaml
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[1]
REGIONS_PATH = ROOT / "data/processed/regions.geojson"
CONFIG_PATH = ROOT / "data/config/region_resolution.yaml"
ZONES_PATH = ROOT / "data/processed/habitat_zones.geojson"
NEUTRAL_PATH = ROOT / "data/processed/habitat_unclassified_areas.geojson"


def canonical_input_hashes(root=ROOT):
    """Snapshot analytical datasets/configuration without touching their bytes."""
    paths = []
    for directory in ["data/processed", "data/raw", "data/config"]:
        paths.extend(p for p in (Path(root) / directory).rglob("*") if p.is_file())
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths) if p.name != ".DS_Store"}


def assert_canonical_inputs_unchanged(before, root=ROOT):
    after = canonical_input_hashes(root)
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    if changed:
        raise RuntimeError(f"Canonical inputs changed: {changed}")


def wgs84_point(longitude, latitude):
    if isinstance(longitude, bool) or isinstance(latitude, bool):
        raise ValueError("Longitude and latitude must be finite WGS84 coordinates")
    longitude, latitude = float(longitude), float(latitude)
    if not math.isfinite(longitude) or not math.isfinite(latitude):
        raise ValueError("Longitude and latitude must be finite")
    if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
        raise ValueError("Longitude/latitude outside WGS84 ranges")
    return Point(longitude, latitude)


class RegionResolver:
    """Load once and reuse; supplied frames also support isolated synthetic tests."""

    def __init__(self, regions=None, config=None):
        if regions is None:
            regions = gpd.read_file(REGIONS_PATH)
        if config is None:
            with CONFIG_PATH.open(encoding="utf-8") as stream:
                config = yaml.safe_load(stream)
        if not isinstance(config, dict):
            raise ValueError("Region-resolution configuration must be a mapping")
        ids = config.get("canonical_region_ids", [])
        if not ids or any(not isinstance(v, str) for v in ids) or len(ids) != len(set(ids)):
            raise ValueError("canonical_region_ids must list distinct region IDs")
        if regions.crs is None:
            raise ValueError("Canonical regions must declare a CRS")
        if regions.region_id.isna().any() or regions.region_id.duplicated().any():
            raise ValueError("Canonical region IDs must be present and unique")
        if set(ids) != set(regions.region_id):
            raise ValueError("Configured canonical region IDs do not match existing geometry")
        self.regions = regions.to_crs("EPSG:4326").copy()
        if (self.regions.geometry.is_empty.any() or not self.regions.geometry.is_valid.all()
                or not self.regions.geom_type.isin(["Polygon", "MultiPolygon"]).all()):
            raise ValueError("Canonical region geometry must be valid Polygon/MultiPolygon")
        self.edges = {region_id: set() for region_id in ids}
        self.rules = config.get("overlap_precedence", [])
        seen = set()
        for rule in self.rules:
            winner, loser = rule["winner"], rule["loser"]
            if winner not in self.edges or loser not in self.edges:
                raise ValueError(f"Configured region ID does not exist: {winner}, {loser}")
            if winner == loser:
                raise ValueError("Precedence winner and loser must differ")
            if (loser, winner) in seen:
                raise ValueError("Contradictory precedence rules")
            if (winner, loser) in seen:
                raise ValueError("Duplicate precedence rule")
            seen.add((winner, loser))
            self.edges[winner].add(loser)
        self._validate_acyclic()
        for pair in config.get("known_overlap_pairs", []):
            if len(pair) != 2 or pair[0] == pair[1] or not set(pair) <= set(ids):
                raise ValueError(f"Invalid known overlap pair: {pair}")
            if (pair[0], pair[1]) not in seen and (pair[1], pair[0]) not in seen:
                raise ValueError(f"Known canonical overlap has no resolution rule: {pair}")

    def _validate_acyclic(self):
        active, complete = set(), set()

        def visit(region_id):
            if region_id in active:
                raise ValueError("Precedence rules form a cycle")
            if region_id in complete:
                return
            active.add(region_id)
            for loser in self.edges[region_id]:
                visit(loser)
            active.remove(region_id)
            complete.add(region_id)

        for region_id in self.edges:
            visit(region_id)

    def resolve(self, longitude, latitude):
        point = wgs84_point(longitude, latitude)
        matches = sorted(self.regions.loc[self.regions.geometry.covers(point), "region_id"])
        result = {"longitude": point.x, "latitude": point.y,
                  "matching_region_ids": matches, "resolved_region_id": None,
                  "resolution_method": "outside_game_regions"}
        if not matches:
            return result
        if len(matches) == 1:
            result.update(resolved_region_id=matches[0], resolution_method="single_match")
            return result

        # Only explicit paths among regions that actually cover this point apply.
        matching = set(matches)
        winners = []
        for region_id in matches:
            reached, pending = set(), [region_id]
            while pending:
                current = pending.pop()
                for loser in self.edges[current] & matching:
                    if loser not in reached:
                        reached.add(loser)
                        pending.append(loser)
            if reached == matching - {region_id}:
                winners.append(region_id)
        if len(winners) != 1:
            result["resolution_method"] = "unresolved_overlap"
            return result
        winner = winners[0]
        result.update(resolved_region_id=winner, resolution_method="explicit_overlap_precedence",
                      winning_region_id=winner,
                      overridden_region_ids=[v for v in matches if v != winner])
        return result


def resolve_game_region(longitude, latitude, resolver=None):
    return (resolver if resolver is not None else RegionResolver()).resolve(longitude, latitude)


def _matching_areas(frame, parent_region_id, point):
    if frame.crs is None:
        raise ValueError("Habitat areas must declare a CRS")
    part = frame.loc[frame.region_id == parent_region_id].to_crs("EPSG:4326")
    if part.zone_id.isna().any() or part.zone_id.duplicated().any():
        raise ValueError("Habitat area IDs must be present and unique within the region")
    if not part.geometry.is_valid.all() or part.geometry.is_empty.any():
        raise ValueError("Invalid habitat area geometry")
    return part.loc[part.geometry.covers(point)].sort_values("zone_id")


def resolve_habitat_zone(longitude, latitude, resolver=None, zones=None, neutral=None):
    """Select habitat only in the owning region; expose same-parent boundary ties."""
    result = resolve_game_region(longitude, latitude, resolver)
    result.update(habitat_lookup_status="parent_unresolved", matching_zone_ids=[],
                  resolved_zone_id=None, habitat_primary=None, matching_neutral_area_ids=[])
    owner = result["resolved_region_id"]
    if owner is None:
        if result["resolution_method"] == "outside_game_regions":
            result["habitat_lookup_status"] = "outside_game_regions"
        return result
    point = wgs84_point(longitude, latitude)
    zones = gpd.read_file(ZONES_PATH) if zones is None else zones
    matches = _matching_areas(zones, owner, point)
    result["matching_zone_ids"] = matches.zone_id.tolist()
    if len(matches) > 1:
        result["habitat_lookup_status"] = "unresolved_zone_overlap"
    elif len(matches) == 1:
        result.update(habitat_lookup_status="zone_match", resolved_zone_id=matches.zone_id.iloc[0],
                      habitat_primary=matches.habitat_primary.iloc[0])
    else:
        neutral = gpd.read_file(NEUTRAL_PATH) if neutral is None else neutral
        matches = _matching_areas(neutral, owner, point)
        result["matching_neutral_area_ids"] = matches.zone_id.tolist()
        result["habitat_lookup_status"] = "neutral_match" if len(matches) else "no_retained_cell"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lon", required=True, type=float)
    parser.add_argument("--lat", required=True, type=float)
    parser.add_argument("--include-habitat-zone", action="store_true",
                        help="Also look up the resolved parent's habitat zone or neutral area")
    args = parser.parse_args()
    before = canonical_input_hashes()
    try:
        result = (resolve_habitat_zone if args.include_habitat_zone else resolve_game_region)(
            args.lon, args.lat)
    finally:
        assert_canonical_inputs_unchanged(before)
    print(json.dumps(result, separators=(",", ":"), allow_nan=False))


if __name__ == "__main__":
    main()
