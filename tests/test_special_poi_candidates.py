"""Candidate safety, deterministic ranking, and geographic diversity checks."""

import json
import sys
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
import yaml
from shapely.geometry import Point, box

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import score_special_poi_candidates as candidates


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = candidates.input_hashes()
        with candidates.CONFIG.open() as stream:
            cls.config = yaml.safe_load(stream)
        cls.pois, cls.regions, cls.zones, cls.neutral = candidates.load_inputs(cls.config)
        cls.context = candidates.build_context(cls.pois, cls.regions, cls.zones, cls.neutral, cls.config)
        cls.scores = candidates.score_all(cls.pois, cls.context, cls.config)

    @classmethod
    def tearDownClass(cls):
        if candidates.input_hashes() != cls.before:
            raise AssertionError("Canonical input or source POI bytes changed")

    def sample_row(self, **changes):
        row = self.pois.iloc[0].copy()
        row["name"] = "Test Institution"
        row["habitat_primary"] = "Healthcare"
        row["habitat_secondary"] = ""
        row["habitat_review_required"] = False
        row["raw_tags"] = {"amenity": "hospital", "name": "Test Institution"}
        for key,value in changes.items():
            row[key] = value
        return row

    def selection_fixture(self, offsets, *, small=False, subtypes=None, habitats=None, raw_score=75):
        crs = self.config["analysis_crs"]
        unit = self.regions.to_crs(crs).crs.axis_info[0].unit_conversion_factor
        x0,y0 = 2100000, 735000
        size = (500 if small else 3000) / unit
        regions = gpd.GeoDataFrame({"region_id": ["RAL-01"], "parent_city": ["Raleigh"]},
                                  geometry=[box(x0,y0,x0+size,y0+size)], crs=crs).to_crs(4326)
        points = gpd.GeoSeries([Point(x0+x/unit,y0+100/unit) for x in offsets], crs=crs).to_crs(4326)
        rows=[]
        for i,point in enumerate(points):
            row = self.scores.iloc[0].to_dict()
            row.update(poi_id=f"test_{i}", region_id="RAL-01", parent_city="Raleigh", name=f"Destination {i}",
                       representative_longitude=point.x, representative_latitude=point.y,
                       candidate_eligible=True, raw_candidate_score=raw_score-i/10,
                       specialization_score=28, primary_osm_key="amenity",
                       primary_osm_value=subtypes[i] if subtypes else f"type_{i}",
                       habitat_primary=habitats[i] if habitats else "Entertainment",
                       raw_tags=json.dumps({"name":f"Destination {i}"}))
            rows.append(row)
        return pd.DataFrame(rows), regions

    def test_scoring_is_deterministic_under_shuffled_inputs(self):
        shuffled = self.pois.sample(frac=1, random_state=31)
        context = candidates.build_context(shuffled, self.regions, self.zones, self.neutral, self.config)
        actual = candidates.score_all(shuffled, context, self.config)
        pd.testing.assert_frame_equal(self.scores, actual)

    def test_dimension_bounds_and_total(self):
        for field,bound in zip(candidates.SCORE_FIELDS,[35,25,20,20]):
            self.assertTrue(self.scores[field].between(0,bound).all())
        self.assertTrue(self.scores.raw_candidate_score.between(0,100).all())
        self.assertLess((self.scores[candidates.SCORE_FIELDS].sum(axis=1)-self.scores.raw_candidate_score).abs().max(), 1e-6)

    def test_explicit_restricted_access_excludes_even_high_scores(self):
        for access in ["private", "no", "staff"]:
            row = self.sample_row(raw_tags={"amenity":"hospital","access":access})
            result = candidates.score_poi(row,self.context,self.config)
            self.assertFalse(result["candidate_eligible"])
            self.assertEqual(result["candidate_access_status"],"restricted_or_inappropriate")
            scores,regions = self.selection_fixture([100])
            scores.loc[0,"candidate_eligible"] = result["candidate_eligible"]
            scores.loc[0,"raw_candidate_score"] = 100
            self.assertTrue(candidates.shortlist_candidates(scores,regions,self.config).empty)

    def test_sensitive_categories_are_held(self):
        for tags in [{"amenity":"prison"}, {"amenity":"school"}, {"amenity":"childcare"},
                     {"landuse":"military"}, {"emergency":"emergency_ward_entrance"}]:
            with self.subTest(tags=tags):
                result = candidates.score_poi(self.sample_row(raw_tags=tags),self.context,self.config)
                self.assertEqual(result["candidate_access_status"],"restricted_or_inappropriate")
                self.assertFalse(result["candidate_eligible"])

    def test_hospital_emergency_yes_is_uncertain_not_excluded(self):
        result = candidates.score_poi(self.sample_row(raw_tags={"amenity":"hospital","emergency":"yes"}),self.context,self.config)
        self.assertEqual(result["candidate_access_status"],"public_context_access_uncertain")
        self.assertTrue(result["candidate_eligible"])

    def test_local_stop_area_is_not_assumed_to_be_major_facility(self):
        row = self.sample_row(raw_tags={"public_transport":"stop_area"})
        result = candidates.score_poi(row,self.context,self.config)
        self.assertEqual(result["specialization_rule_id"], "SP_LOCAL_TRANSIT")
        row["raw_tags"] = {"public_transport":"stop_area", "railway":"facility"}
        result = candidates.score_poi(row,self.context,self.config)
        self.assertEqual(result["specialization_rule_id"], "SP_TRANSIT_COMPLEX")

    def test_public_tag_cannot_override_sensitive_or_private_tags(self):
        for tags in [{"tourism":"museum","access":"private"}, {"amenity":"school","access":"yes"}]:
            result = candidates.score_poi(self.sample_row(raw_tags=tags),self.context,self.config)
            self.assertEqual(result["candidate_access_status"],"restricted_or_inappropriate")

    def test_missing_invalid_or_review_habitats_cannot_enter_pool(self):
        for change in [{"habitat_primary":""}, {"habitat_primary":"Made up"}, {"habitat_review_required":True}]:
            with self.subTest(change=change):
                result = candidates.score_poi(self.sample_row(**change),self.context,self.config)
                self.assertFalse(result["candidate_eligible"])
                scores,regions = self.selection_fixture([100])
                scores.loc[0,"candidate_eligible"] = result["candidate_eligible"]
                self.assertTrue(candidates.shortlist_candidates(scores,regions,self.config).empty)

    def test_invalid_geometry_and_parent_cannot_enter_pool(self):
        for change in [{"geometry":None}, {"region_id":"MISSING"}]:
            result = candidates.score_poi(self.sample_row(**change),self.context,self.config)
            self.assertFalse(result["candidate_eligible"])

    def test_shortlist_is_deterministic_under_shuffling(self):
        expected = candidates.shortlist_candidates(self.scores,self.regions,self.config)
        actual = candidates.shortlist_candidates(self.scores.sample(frac=1,random_state=9),self.regions,self.config)
        pd.testing.assert_frame_equal(expected,actual)

    def test_preferred_geographic_spacing(self):
        scores,regions = self.selection_fixture([100,200,500])
        shortlist = candidates.shortlist_candidates(scores,regions,self.config)
        self.assertEqual(set(shortlist.poi_id),{"test_0","test_2"})
        self.assertTrue(shortlist.spacing_preference_satisfied.all())
        self.assertTrue(shortlist.nearest_selected_candidate_distance_m.ge(250).all())

    def test_small_region_relaxes_spacing_and_records_both_neighbors(self):
        scores,regions = self.selection_fixture([100,250,150],small=True)
        shortlist = candidates.shortlist_candidates(scores,regions,self.config)
        self.assertEqual(set(shortlist.poi_id),{"test_0","test_1"})
        self.assertFalse(shortlist.spacing_preference_satisfied.any())
        self.assertTrue(shortlist.nearest_selected_candidate_distance_m.between(149,151).all())

    def test_category_cap_and_no_forced_eight(self):
        scores,regions = self.selection_fixture([100,450,800,1150,1500],subtypes=["museum"]*5)
        shortlist = candidates.shortlist_candidates(scores,regions,self.config)
        self.assertEqual(len(shortlist),2)
        self.assertTrue(shortlist.same_subtype_shortlist_count.eq(2).all())
        scores,regions = self.selection_fixture([100],small=True,raw_score=40)
        self.assertTrue(candidates.shortlist_candidates(scores,regions,self.config).empty)

    def test_duplicate_venue_names_are_not_repeated_in_shortlist(self):
        scores,regions = self.selection_fixture([100,450])
        scores["name"]="Same Venue"
        self.assertEqual(len(candidates.shortlist_candidates(scores,regions,self.config)),1)

    def test_distinctiveness_uses_actual_poi_and_zone_shares(self):
        row = self.sample_row(habitat_primary="Finance",habitat_secondary="Office & Business")
        result = candidates.score_poi(row,self.context,self.config)
        self.assertEqual(result["region_primary_habitat_zone_area_share"],0)
        rationale=json.loads(result["scoring_rationale"])
        self.assertEqual(rationale["distinctiveness"]["primary_zone_rarity"],10)
        self.assertGreater(result["region_primary_habitat_poi_share"],0)

    def test_legacy_csv_tags_and_json_tags_agree(self):
        original={"name":"O'Brien's Museum","tourism":"museum","access":"yes"}
        self.assertEqual(candidates.raw_tags(str(original)),original)
        self.assertEqual(candidates.raw_tags(json.dumps(original)),original)

    def test_canonical_source_files_are_unchanged(self):
        self.assertEqual(candidates.input_hashes(),self.before)


if __name__ == "__main__":
    unittest.main()
