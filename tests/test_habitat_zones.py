"""Topology and aggregation regressions for Step 7B."""

import json
import sys
import unittest
from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPolygon, box

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_habitat_zones as zones


def cell_frame(geometries):
    return gpd.GeoDataFrame({
        "cell_id": [f"cell_{i}" for i in range(len(geometries))],
        "region_id": ["RAL-01"] * len(geometries),
        "parent_city": ["Raleigh"] * len(geometries),
        "cell_habitat_primary": ["Retail"] * len(geometries),
        "cell_habitat_secondary": [""] * len(geometries),
        "cell_confidence": ["high"] * len(geometries),
        "top_score": [2.0] * len(geometries),
        "second_score": [1.0] * len(geometries),
        "top_to_second_ratio": [2.0] * len(geometries),
        "clipped_area_sqft": [g.area for g in geometries],
    }, geometry=geometries, crs=zones.ANALYSIS_CRS)


class TopologyTests(unittest.TestCase):
    def test_edge_corner_and_gap(self):
        square = box(0, 0, 100, 100)
        self.assertTrue(zones.rook_adjacent(square, box(100, 0, 200, 100)))
        self.assertFalse(zones.rook_adjacent(square, box(100, 100, 200, 200)))
        self.assertFalse(zones.rook_adjacent(square, box(100.001, 0, 200, 100)))

    def test_numerical_roundoff_does_not_modify_geometry(self):
        a = box(0, 0, 100, 100)
        b = box(100 + 1e-8, 0, 200, 100)
        self.assertTrue(zones.rook_adjacent(a, b))
        component = zones.connected_components(cell_frame([a, b]))[0]
        result = zones.aggregate(component, "Retail")
        self.assertAlmostEqual(result["geometry"].area, a.area + b.area)
        self.assertEqual(result["geometry"].geom_type, "MultiPolygon")
        self.assertTrue(result["review_required"])

    def test_deterministic_components_and_ids(self):
        cells = cell_frame([box(0, 0, 100, 100), box(100, 0, 200, 100), box(200, 100, 300, 200)])
        original = zones.connected_components(cells)
        shuffled = zones.connected_components(cells.sample(frac=1, random_state=17))
        ids = lambda components: [zones.component_id("RAL-01", "Retail", c.cell_id) for c in components]
        self.assertEqual(ids(original), ids(shuffled))
        self.assertEqual([len(c) for c in original], [2, 1])

    def test_clipped_multipart_cell_keeps_disconnected_parts(self):
        geometry = MultiPolygon([box(0, 0, 100, 100), box(200, 0, 300, 100)])
        result = zones.aggregate(cell_frame([geometry]), "Retail")
        self.assertTrue(result["geometry"].equals(geometry))
        self.assertEqual(result["cell_count"], 1)
        self.assertTrue(result["micro_zone"])

    def test_weighted_secondary_confidence_and_null_ratios(self):
        cells = cell_frame([box(0, 0, 100, 100), box(100, 0, 400, 100)])
        cells.loc[0, "cell_habitat_secondary"] = "Finance"
        cells.loc[0, "cell_confidence"] = "low"
        cells.loc[1, "top_to_second_ratio"] = None
        result = zones.aggregate(cells, "Retail")
        self.assertEqual(result["low_confidence_area_pct"], 25)
        self.assertEqual(result["dominant_secondary_habitat"], "")
        self.assertEqual(json.loads(result["secondary_habitat_distribution_json"]), {"Finance": 25})
        self.assertEqual(result["mean_top_to_second_ratio"], 2)
        self.assertEqual(result["finite_ratio_area_pct"], 25)

    def test_low_area_review_threshold_and_secondary_threshold(self):
        cells = cell_frame([box(0, 0, 200, 500), box(200, 0, 500, 500)])
        cells.loc[0, "cell_confidence"] = "low"
        cells.loc[0, "cell_habitat_secondary"] = "Finance"
        result = zones.aggregate(cells, "Retail")
        self.assertFalse(result["micro_zone"])
        self.assertEqual(result["low_confidence_area_pct"], 40)
        self.assertTrue(result["review_required"])
        self.assertEqual(result["dominant_secondary_habitat"], "Finance")
        self.assertEqual(result["dominant_secondary_area_pct"], 40)

    def test_mixed_region_or_habitat_fails(self):
        cells = cell_frame([box(0, 0, 100, 100), box(100, 0, 200, 100)])
        cells.loc[1, "region_id"] = "DUR-01"
        with self.assertRaises(ValueError):
            zones.aggregate(cells, "Retail")
        cells.loc[1, "region_id"] = "RAL-01"
        cells.loc[1, "cell_habitat_primary"] = "Finance"
        with self.assertRaises(ValueError):
            zones.aggregate(cells, "Retail")

    def test_inherited_overlap_requires_explicit_option(self):
        cells = cell_frame([box(0, 0, 100, 100), box(50, 0, 150, 100)])
        cells.loc[1, "region_id"] = "DUR-01"
        cells.loc[1, "parent_city"] = "Durham"
        parents = gpd.GeoDataFrame({"region_id": ["RAL-01", "DUR-01"]},
                                  geometry=list(cells.geometry), crs=cells.crs)
        classified, neutral, membership = zones.build_zones(cells.assign(
            cell_habitat_primary=["Retail", ""]))
        source = cells.assign(cell_habitat_primary=["Retail", ""])
        overlap = zones.overlap_diagnostics(source, classified, neutral)
        self.assertEqual(len(overlap), 1)
        self.assertEqual(overlap.iloc[0].introduced_overlap_sqft, 0)
        with self.assertRaises(ValueError):
            zones.validate(source, parents, classified, neutral, membership, overlap)
        coverage = zones.validate(source, parents, classified, neutral, membership, overlap, True)
        self.assertTrue(coverage.coverage_difference_sqft.eq(0).all())


if __name__ == "__main__":
    unittest.main()
