"""Explicit ownership, boundary routing, and read-only habitat integration QA."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import yaml
from shapely.geometry import Point, box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import resolve_game_region as routing


def synthetic_regions(ids, geometries):
    return gpd.GeoDataFrame({"region_id": ids}, geometry=geometries, crs="EPSG:4326")


def synthetic_config(ids, edges=()):
    return {"canonical_region_ids": ids, "known_overlap_pairs": [],
            "overlap_precedence": [{"winner": a, "loser": b, "reason": "test rule"}
                                   for a, b in edges]}


def area_frame(ids, parents, geometries, habitats=None):
    fields = {"zone_id": ids, "region_id": parents}
    if habitats is not None:
        fields["habitat_primary"] = habitats
    return gpd.GeoDataFrame(fields, geometry=geometries, crs="EPSG:4326")


class RegionResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = routing.canonical_input_hashes()
        cls.resolver = routing.RegionResolver()
        cls.regions = cls.resolver.regions.set_index("region_id")
        with routing.CONFIG_PATH.open() as stream:
            cls.config = yaml.safe_load(stream)

    @classmethod
    def tearDownClass(cls):
        routing.assert_canonical_inputs_unchanged(cls.before)

    def test_each_actual_overlap_selects_configured_owner(self):
        for rule in self.config["overlap_precedence"]:
            with self.subTest(winner=rule["winner"]):
                point = self.regions.loc[rule["winner"]].geometry.intersection(
                    self.regions.loc[rule["loser"]].geometry).representative_point()
                result = self.resolver.resolve(point.x, point.y)
                self.assertEqual(result["resolution_method"], "explicit_overlap_precedence")
                self.assertEqual(result["resolved_region_id"], rule["winner"])
                self.assertEqual(result["winning_region_id"], rule["winner"])
                self.assertEqual(result["overridden_region_ids"], [rule["loser"]])
                self.assertEqual(set(result["matching_region_ids"]), {rule["winner"], rule["loser"]})

    def test_actual_single_region(self):
        rest = self.regions.drop("RAL-05")
        point = self.regions.loc["RAL-05"].geometry.difference(unary_union(rest.geometry)).representative_point()
        result = self.resolver.resolve(point.x, point.y)
        self.assertEqual(result["resolved_region_id"], "RAL-05")
        self.assertEqual(result["resolution_method"], "single_match")

    def test_outside_actual_regions(self):
        _, _, maxx, maxy = self.resolver.regions.total_bounds
        result = self.resolver.resolve(maxx + 0.1, maxy + 0.1)
        self.assertEqual(result["resolution_method"], "outside_game_regions")
        self.assertEqual(result["matching_region_ids"], [])
        self.assertIsNone(result["resolved_region_id"])

    def test_actual_region_boundary_is_covered(self):
        geometry = self.regions.loc["RAL-05"].geometry
        part = geometry if geometry.geom_type == "Polygon" else list(geometry.geoms)[0]
        point = Point(part.exterior.coords[0])
        self.assertFalse(geometry.contains(point))
        result = self.resolver.resolve(point.x, point.y)
        self.assertEqual(result["resolved_region_id"], "RAL-05")

    def test_unconfigured_synthetic_overlap_is_unresolved(self):
        resolver = routing.RegionResolver(synthetic_regions(["A", "B"], [box(0, 0, 2, 2), box(1, 1, 3, 3)]),
                                          synthetic_config(["A", "B"]))
        result = resolver.resolve(1.5, 1.5)
        self.assertEqual(result["resolution_method"], "unresolved_overlap")
        self.assertIsNone(result["resolved_region_id"])

    def test_shared_boundary_obeys_precedence(self):
        resolver = routing.RegionResolver(synthetic_regions(["A", "B"], [box(0, 0, 1, 1), box(1, 0, 2, 1)]),
                                          synthetic_config(["A", "B"], [("B", "A")]))
        result = resolver.resolve(1, 0.5)
        self.assertEqual(result["matching_region_ids"], ["A", "B"])
        self.assertEqual(result["resolved_region_id"], "B")

    def test_input_order_does_not_decide_winner(self):
        shuffled = self.resolver.regions.sample(frac=1, random_state=13)
        other = routing.RegionResolver(shuffled, self.config)
        for rule in self.config["overlap_precedence"]:
            point = self.regions.loc[rule["winner"]].geometry.intersection(
                self.regions.loc[rule["loser"]].geometry).representative_point()
            self.assertEqual(self.resolver.resolve(point.x, point.y), other.resolve(point.x, point.y))

    def test_invalid_coordinates_fail(self):
        for lon, lat in [(181, 0), (0, 91), (float("nan"), 0), (0, float("inf")), (True, 0)]:
            with self.subTest(longitude=lon, latitude=lat), self.assertRaises(ValueError):
                self.resolver.resolve(lon, lat)

    def test_unknown_configured_region_fails(self):
        config = copy.deepcopy(self.config)
        config["overlap_precedence"][0]["winner"] = "MISSING"
        with self.assertRaisesRegex(ValueError, "does not exist"):
            routing.RegionResolver(self.resolver.regions, config)

    def test_canonical_id_inventory_mismatch_fails(self):
        config = copy.deepcopy(self.config)
        config["canonical_region_ids"].append("MISSING")
        with self.assertRaises(ValueError):
            routing.RegionResolver(self.resolver.regions, config)

    def test_same_winner_and_loser_fails(self):
        config = copy.deepcopy(self.config)
        config["overlap_precedence"][0]["loser"] = config["overlap_precedence"][0]["winner"]
        with self.assertRaisesRegex(ValueError, "must differ"):
            routing.RegionResolver(self.resolver.regions, config)

    def test_duplicate_and_contradictory_rules_fail(self):
        for reverse in [False, True]:
            config = copy.deepcopy(self.config)
            rule = config["overlap_precedence"][0].copy()
            if reverse:
                rule["winner"], rule["loser"] = rule["loser"], rule["winner"]
            config["overlap_precedence"].append(rule)
            with self.subTest(reverse=reverse), self.assertRaises(ValueError):
                routing.RegionResolver(self.resolver.regions, config)

    def test_missing_known_overlap_rule_fails(self):
        for i in range(3):
            config = copy.deepcopy(self.config)
            del config["overlap_precedence"][i]
            with self.subTest(rule=i), self.assertRaisesRegex(ValueError, "no resolution rule"):
                routing.RegionResolver(self.resolver.regions, config)

    def test_cycle_fails(self):
        regions = synthetic_regions(["A", "B", "C"], [box(0, 0, 1, 1)] * 3)
        config = synthetic_config(["A", "B", "C"], [("A", "B"), ("B", "C"), ("C", "A")])
        with self.assertRaisesRegex(ValueError, "cycle"):
            routing.RegionResolver(regions, config)

    def test_multi_match_requires_one_explicit_winner(self):
        regions = synthetic_regions(["A", "B", "C"], [box(0, 0, 1, 1)] * 3)
        resolver = routing.RegionResolver(regions, synthetic_config(["A", "B", "C"], [("A", "B")]))
        self.assertEqual(resolver.resolve(0.5, 0.5)["resolution_method"], "unresolved_overlap")
        resolver = routing.RegionResolver(regions, synthetic_config(["A", "B", "C"], [("A", "B"), ("B", "C")]))
        self.assertEqual(resolver.resolve(0.5, 0.5)["resolved_region_id"], "A")

    def test_absent_intermediate_region_cannot_decide_precedence(self):
        regions = synthetic_regions(["A", "B", "C"], [box(0, 0, 1, 1), box(3, 3, 4, 4), box(0, 0, 1, 1)])
        resolver = routing.RegionResolver(regions, synthetic_config(["A", "B", "C"], [("A", "B"), ("B", "C")]))
        self.assertEqual(resolver.resolve(0.5, 0.5)["resolution_method"], "unresolved_overlap")

    def test_zone_lookup_only_searches_resolved_parent(self):
        for rule in self.config["overlap_precedence"]:
            geometry = self.regions.loc[rule["winner"]].geometry.intersection(self.regions.loc[rule["loser"]].geometry)
            point = geometry.representative_point()
            zones = area_frame(["losing_zone", "winning_zone"], [rule["loser"], rule["winner"]],
                               [geometry, geometry], ["Retail", "Entertainment"])
            result = routing.resolve_habitat_zone(point.x, point.y, self.resolver, zones)
            self.assertEqual(result["matching_zone_ids"], ["winning_zone"])
            self.assertEqual(result["resolved_zone_id"], "winning_zone")

    def test_zone_lookup_neutral_and_discarded_fragment(self):
        regions = synthetic_regions(["A"], [box(0, 0, 3, 1)])
        resolver = routing.RegionResolver(regions, synthetic_config(["A"]))
        zones = area_frame(["zone"], ["A"], [box(0, 0, 1, 1)], ["Retail"])
        neutral = area_frame(["neutral"], ["A"], [box(1, 0, 2, 1)])
        result = routing.resolve_habitat_zone(1.5, 0.5, resolver, zones, neutral)
        self.assertEqual(result["habitat_lookup_status"], "neutral_match")
        self.assertIsNone(result["resolved_zone_id"])
        self.assertEqual(result["matching_neutral_area_ids"], ["neutral"])
        self.assertEqual(routing.resolve_habitat_zone(2.5, 0.5, resolver, zones, neutral)["habitat_lookup_status"], "no_retained_cell")

    def test_shared_zone_boundary_is_explicitly_unresolved(self):
        resolver = routing.RegionResolver(synthetic_regions(["A"], [box(0, 0, 2, 1)]), synthetic_config(["A"]))
        zones = area_frame(["one", "two"], ["A", "A"], [box(0, 0, 1, 1), box(1, 0, 2, 1)], ["Retail", "Entertainment"])
        result = routing.resolve_habitat_zone(1, 0.5, resolver, zones)
        self.assertEqual(result["habitat_lookup_status"], "unresolved_zone_overlap")
        self.assertIsNone(result["resolved_zone_id"])

    def test_unresolved_parent_does_not_load_habitat_files(self):
        resolver = routing.RegionResolver(synthetic_regions(["A", "B"], [box(0, 0, 1, 1)] * 2), synthetic_config(["A", "B"]))
        result = routing.resolve_habitat_zone(0.5, 0.5, resolver)
        self.assertEqual(result["habitat_lookup_status"], "parent_unresolved")
        self.assertIsNone(result["resolved_zone_id"])

    def test_canonical_mutation_guard_fails_on_byte_change(self):
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            folder = root / "data/processed"
            folder.mkdir(parents=True)
            target = folder / "regions.geojson"
            target.write_bytes(b"original")
            before = routing.canonical_input_hashes(root)
            target.write_bytes(b"changed")
            with self.assertRaisesRegex(RuntimeError, "Canonical inputs changed"):
                routing.assert_canonical_inputs_unchanged(before, root)

    def test_canonical_committed_zone_integration(self):
        zones = gpd.read_file(routing.ZONES_PATH)
        neutral = gpd.read_file(routing.NEUTRAL_PATH)
        for rule in self.config["overlap_precedence"]:
            pair_overlap = self.regions.loc[rule["winner"]].geometry.intersection(self.regions.loc[rule["loser"]].geometry)
            available = unary_union(zones.loc[zones.region_id == rule["winner"]].geometry)
            point = pair_overlap.intersection(available).representative_point()
            result = routing.resolve_habitat_zone(point.x, point.y, self.resolver)
            self.assertEqual(result["resolved_region_id"], rule["winner"])
            self.assertEqual(result["habitat_lookup_status"], "zone_match")
            owner = zones.loc[zones.zone_id == result["resolved_zone_id"], "region_id"].iloc[0]
            self.assertEqual(owner, rule["winner"])
        for area in neutral.itertuples():
            point = area.geometry.representative_point()
            result = routing.resolve_habitat_zone(point.x, point.y, self.resolver)
            self.assertEqual(result["habitat_lookup_status"], "neutral_match")


if __name__ == "__main__":
    unittest.main()
