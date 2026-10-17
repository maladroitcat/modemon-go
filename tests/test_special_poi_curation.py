"""Human decision coverage, safety, source integrity, and deterministic outputs."""

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import apply_special_poi_curation as curation


class CurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = curation.protected_hashes()
        cls.source, cls.fields = curation.read_rows(curation.SHORTLIST)
        cls.config = curation.load_config()
        cls.rows = curation.apply_curation(cls.source, cls.config)

    @classmethod
    def tearDownClass(cls):
        curation.assert_unchanged(cls.before)

    def changed_config(self, name, **changes):
        config = copy.deepcopy(self.config)
        row = next(r for r in self.source if r["name"] == name)
        config["decisions"][row["poi_id"]].update(changes)
        return config

    def test_complete_one_to_one_inventory(self):
        self.assertEqual(len(self.source), 42)
        self.assertEqual(len(self.config["decisions"]), 42)
        self.assertEqual({r["poi_id"] for r in self.source}, set(self.config["decisions"]))
        self.assertEqual(len({r["poi_id"] for r in self.rows}), 42)

    def test_missing_or_outside_decisions_fail(self):
        for outside in [False, True]:
            config = copy.deepcopy(self.config)
            key = next(iter(config["decisions"]))
            decision = config["decisions"].pop(key)
            if outside:
                config["decisions"]["outside_shortlist"] = decision
            with self.assertRaisesRegex(ValueError, "Decision IDs"):
                curation.apply_curation(self.source, config)

    def test_duplicate_or_wrong_size_shortlist_fails(self):
        for rows in [self.source[:-1], self.source + [self.source[0]], self.source[:-1] + [self.source[0]]]:
            with self.assertRaisesRegex(ValueError, "42 unique"):
                curation.apply_curation(rows, self.config)

    def test_names_resolve_exactly_without_guessing(self):
        for r in self.rows:
            self.assertEqual(curation.resolve_candidate_id(self.source, r["region_id"], r["name"]), r["poi_id"])
        for rows, name in [(self.source, "not a candidate"), (self.source + [self.source[0]], self.source[0]["name"])]:
            with self.assertRaisesRegex(ValueError, "match exactly once"):
                curation.resolve_candidate_id(rows, "DUR-01", name)
        config = self.changed_config("Artspace", candidate_name="artspace")
        with self.assertRaisesRegex(ValueError, "match exactly once"):
            curation.apply_curation(self.source, config)

    def test_decision_key_must_match_candidate_identity(self):
        config = self.changed_config("Artspace", candidate_name="Finch Library")
        with self.assertRaisesRegex(ValueError, "Decision key"):
            curation.apply_curation(self.source, config)

    def test_duplicate_yaml_decisions_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.yaml"
            path.write_text("decisions:\n  same: {}\n  same: {}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate YAML key"):
                curation.load_config(path)

    def test_exact_primary_and_selection_counts(self):
        counts = {s: sum(r["selection_status"] == s for r in self.rows) for s in curation.SELECTIONS}
        self.assertEqual(counts, {"primary": 17, "alternate": 12, "deferred": 1, "not_selected": 2, "rejected": 10})
        self.assertEqual([r["name"] for r in self.rows if r["selection_status"] == "deferred"], ["Lilly Library"])

    def test_approved_primary_sets_and_order(self):
        expected = {
            "DUR-01": ["Hayti Heritage Center", "Museum of Durham History", "Durham Station"],
            "DUR-02": ["Nasher Museum of Art", "Perkins Library", "Jack Katz Stadium"],
            "RAL-01": ["North Carolina Museum of Natural Sciences", "Raleigh Union Station Bus Facility", "Artspace"],
            "RAL-02": ["Big Field", "Gipson Play Plaza"],
            "RAL-03A": ["NC State Crafts Center", "SOL Garden"],
            "RAL-03B": ["Pullen Park Amusement Center", "Theater In The Park"],
            "RAL-04": ["James B. Hunt Jr. Library", "William and Ida Friday Institute for Educational Innovation"],
            "RAL-05": [],
        }
        for region, names in expected.items():
            actual = [curation.display_name(r) for r in self.rows if r["region_id"] == region and r["selection_status"] == "primary"]
            self.assertEqual(actual, names)
            self.assertLessEqual(len(actual), 3)

    def test_sensitive_closed_unknown_never_selected(self):
        for name, field, value in [
            ("Artspace", "gameplay_suitability", "sensitive_not_recommended"),
            ("Artspace", "current_status", "closed"),
            ("Artspace", "current_status", "unknown"),
            ("Marbles Kids Museum", "gameplay_suitability", "sensitive_not_recommended"),
            ("Marbles Kids Museum", "current_status", "closed"),
            ("Marbles Kids Museum", "current_status", "unknown"),
        ]:
            with self.subTest(name=name, value=value), self.assertRaisesRegex(ValueError, "Unsafe or unavailable"):
                curation.apply_curation(self.source, self.changed_config(name, **{field: value}))

    def test_conditional_primaries_are_documented(self):
        conditional = [r for r in self.rows if r["selection_status"] == "primary" and r["gameplay_suitability"] == "conditional"]
        self.assertEqual({r["name"] for r in conditional}, {"Durham Station", "Gipson Play Plaza", "Pullen Park Amusement Center"})
        for field in ["verification_note", "selection_rationale"]:
            with self.assertRaisesRegex(ValueError, "Missing human documentation"):
                curation.apply_curation(self.source, self.changed_config("Gipson Play Plaza", **{field: ""}))
        gipson = next(r for r in conditional if r["name"] == "Gipson Play Plaza")
        self.assertIn("children's play equipment", gipson["association_anchor_note"])

    def test_primary_and_alternate_ranks_unique_contiguous(self):
        for region in curation.REGIONS:
            for status, field in [("primary", "primary_rank"), ("alternate", "alternate_rank")]:
                ranks = sorted(r[field] for r in self.rows if r["region_id"] == region and r["selection_status"] == status)
                self.assertEqual(ranks, list(range(1, len(ranks) + 1)))
        for changes in [{"primary_rank": 2}, {"primary_rank": 4}, {"primary_rank": True}, {"alternate_rank": 1}]:
            with self.assertRaises(ValueError):
                curation.apply_curation(self.source, self.changed_config("Artspace", **changes))
        with self.assertRaises(ValueError):
            curation.apply_curation(self.source, self.changed_config("Durham Athletic Park", alternate_rank=2))

    def test_source_names_scores_coordinates_and_all_fields_unchanged(self):
        original = {r["poi_id"]: r for r in self.source}
        for row in self.rows:
            self.assertEqual({k: row[k] for k in self.fields}, original[row["poi_id"]])
        museum = next(r for r in self.rows if r["name"] == "The History Hub Museum")
        self.assertEqual(museum["verified_name"], "Museum of Durham History")
        self.assertEqual(sum(bool(r["verified_name"]) for r in self.rows), 3)

    def test_validation_rejects_score_name_or_coordinate_mutation(self):
        for field, value in [("raw_candidate_score", "100"), ("name", "Changed name"),
                             ("representative_latitude", "0"), ("representative_longitude", "0")]:
            rows = copy.deepcopy(self.rows)
            rows[0][field] = value
            with self.assertRaisesRegex(ValueError, "Step 8A values changed"):
                curation.validate(rows, self.source)

    def test_enum_and_date_validation(self):
        for changes in [{"current_status": "made_up"}, {"selection_status": "spawn"},
                        {"gameplay_suitability": "safe"}, {"verification_date": "2026-10-18"}]:
            with self.assertRaises(ValueError):
                curation.apply_curation(self.source, self.changed_config("Artspace", **changes))

    def test_dates_and_no_invented_evidence_urls(self):
        self.assertEqual({r["verification_date"] for r in self.rows}, {"2026-10-17"})
        for name in ["Jack Katz Stadium", "Raleigh Union Station Bus Facility", "WakeMed Health & Hospitals: Raleigh Campus"]:
            row = next(r for r in self.rows if r["name"] == name)
            self.assertIsNone(row["verification_source_url"])

    def test_summary_accounts_for_all_candidates_and_null_suitability(self):
        summary = curation.summarize(self.rows)
        self.assertEqual(len(summary), 9)
        self.assertEqual(summary[-1]["shortlist_candidates"], 42)
        self.assertEqual(summary[-1]["suitability_not_assessed"], 2)
        for row in summary:
            for fields in [curation.STATUSES, curation.SELECTIONS, curation.SUITABILITIES + ["suitability_not_assessed"]]:
                self.assertEqual(sum(row[k] for k in fields), row["shortlist_candidates"])

    def test_shuffled_source_and_config_produce_identical_decisions(self):
        config = copy.deepcopy(self.config)
        config["decisions"] = dict(reversed(list(config["decisions"].items())))
        self.assertEqual(curation.apply_curation(list(reversed(self.source)), config), self.rows)

    def test_geojson_preserves_association_coordinates_and_fields(self):
        rows = [r for r in self.rows if r["selection_status"] == "primary"]
        collection = curation.geojson(rows)
        self.assertEqual(len(collection["features"]), 17)
        for row, feature in zip(rows, collection["features"]):
            self.assertEqual(feature["geometry"]["type"], "Point")
            self.assertEqual(feature["geometry"]["coordinates"], [float(row["representative_longitude"]), float(row["representative_latitude"])])
            self.assertEqual(feature["properties"], row)
        json.dumps(collection, allow_nan=False)

    def test_unknown_fields_cannot_silently_modify_source_values(self):
        with self.assertRaisesRegex(ValueError, "Unknown curation fields"):
            curation.apply_curation(self.source, self.changed_config("Artspace", raw_candidate_score=100))

    def test_protected_input_hash_guard_detects_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data/processed").mkdir(parents=True)
            (root / "scripts").mkdir()
            path = root / "data/processed/special_poi_candidate_scores.csv"
            path.write_text("original", encoding="utf-8")
            (root / "scripts/score_special_poi_candidates.py").write_text("source", encoding="utf-8")
            before = curation.protected_hashes(root)
            path.write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Protected source files changed"):
                curation.assert_unchanged(before, root)

    def test_generated_outputs_byte_stable_and_sources_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            curation.run(output_root=output)
            first = {p: hashlib.sha256((output / p).read_bytes()).hexdigest() for p in curation.OUTPUT_FILES}
            curation.run(output_root=output)
            second = {p: hashlib.sha256((output / p).read_bytes()).hexdigest() for p in curation.OUTPUT_FILES}
            self.assertEqual(first, second)
            serialized, fields = curation.read_rows(output / "data/processed/special_poi_curation.csv")
            self.assertEqual(fields, self.fields + curation.FIELDS)
            original = {r["poi_id"]: r for r in self.source}
            for row in serialized:
                self.assertEqual({k: row[k] for k in self.fields}, original[row["poi_id"]])
            self.assertEqual(len(curation.read_rows(output / "data/processed/special_poi_primary.csv")[0]), 17)
            self.assertEqual(len(curation.read_rows(output / "data/processed/special_poi_alternates.csv")[0]), 12)
        curation.assert_unchanged(self.before)


if __name__ == "__main__":
    unittest.main()
