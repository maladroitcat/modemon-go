"""Canonical content integrity, strict validation, and deterministic JSON builds."""

from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_modedex as modedex


def unrelated_hashes():
    paths = [p for folder in ["data", "output", "scripts", "tests"]
             for p in (modedex.ROOT / folder).rglob("*")
             if p.is_file() and p != modedex.OUTPUT_PATH and "__pycache__" not in p.parts and p.name != ".DS_Store"]
    supplied = modedex.ROOT / "modedex.yaml"
    if supplied.exists():
        paths.append(supplied)
    return {str(p.relative_to(modedex.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


class ModedexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = unrelated_hashes()
        cls.document = modedex.load_yaml()
        cls.schema = modedex.load_schema()

    @classmethod
    def tearDownClass(cls):
        if unrelated_hashes() != cls.before:
            raise AssertionError("Modedex tests changed unrelated files or canonical source bytes")

    def changed_record(self, modemon_id="detector_disease", **changes):
        document = copy.deepcopy(self.document)
        document["modemon"][modemon_id].update(changes)
        return document

    def assert_invalid(self, document, message=None):
        with self.assertRaises(modedex.ModedexValidationError) as caught:
            modedex.validate(document, self.schema)
        if message:
            self.assertIn(message, str(caught.exception))

    def test_canonical_yaml_loads_and_validates(self):
        self.assertIsInstance(self.document, dict)
        modedex.validate(self.document, self.schema)

    def test_json_schema_is_valid_and_canonical_content_passes(self):
        Draft202012Validator.check_schema(self.schema)
        Draft202012Validator(self.schema, format_checker=modedex.format_checker()).validate(self.document)

    def test_semantic_validation_passes(self):
        modedex.validate_semantics(self.document)

    def test_exact_inventory_stage_and_family_counts(self):
        records = self.document["modemon"]
        self.assertEqual(len(records), 51)
        self.assertEqual(Counter(r["stage"] for r in records.values()), {1: 8, 2: 31, 3: 12})
        self.assertEqual(set(self.document["families"]), modedex.FAMILY_IDS)
        self.assertEqual(len(self.document["families"]), 8)
        self.assertEqual(Counter(r["family_id"] for r in records.values()), {
            "detector": 4, "anomaly": 5, "forecast": 5, "recommender": 8,
            "extractor": 7, "scheduler": 8, "generator": 8, "retriever": 6,
        })

    def test_family_bases_and_visual_themes(self):
        expected = {
            "detector": ("Seeklet", "eyeball_scanner"),
            "anomaly": ("Quirkle", "reptile"),
            "forecast": ("Forespirit", "ghost_spirit"),
            "recommender": ("Suggestle", "bird"),
            "extractor": ("Scribbit", "small_rodent"),
            "scheduler": ("Plancton", "ocean_creature"),
            "generator": ("Purrrompt", "cat"),
            "retriever": ("Searchound", "dog"),
        }
        for family_id, (name, theme) in expected.items():
            family = self.document["families"][family_id]
            self.assertEqual(family["base_modemon_id"], family_id + "_base")
            self.assertEqual(family["visual_family"], theme)
            self.assertEqual(self.document["modemon"][family["base_modemon_id"]]["name"], name)

    def test_evolution_references_resolve_in_same_family_and_previous_stage(self):
        records = self.document["modemon"]
        for record in records.values():
            if record["stage"] == 1:
                self.assertIsNone(record["evolves_from"])
            else:
                parent = records[record["evolves_from"]]
                self.assertEqual(parent["family_id"], record["family_id"])
                self.assertEqual(parent["stage"], record["stage"] - 1)

    def test_stage_specific_signature_metadata_and_sources(self):
        signatures = []
        for record in self.document["modemon"].values():
            if record["stage"] < 3:
                self.assertIsNone(record["signature"])
            else:
                signature = record["signature"]
                signatures.append(record["name"])
                self.assertIsInstance(signature, dict)
                url = signature["source_url"]
                self.assertTrue(url)
                self.assertTrue(modedex.format_checker().conforms(url, "uri"))
                self.assertTrue(url.startswith(("https://", "http://")))
        self.assertEqual(set(signatures), {"Muselect", "Mentamorph", "Referaptor", "Archivole", "Specimunk", "Flowfin",
                                           "Cabcrab", "Signalquid", "Planthera", "Lecturlynx", "Catalogar", "Semantiff"})

    def test_unknown_documented_technology_remains_empty(self):
        for modemon_id in ["extractor_history", "extractor_specimen", "scheduler_transit_flow",
                           "scheduler_ride_booking", "scheduler_traffic_signal"]:
            self.assertEqual(self.document["modemon"][modemon_id]["signature"]["documented_technology"], [])

    def test_signature_anchors_preserved(self):
        expected = {
            "Muselect": "Nasher Museum of Art", "Mentamorph": "Friday Institute",
            "Referaptor": "NC State University Libraries", "Archivole": "Friday Institute",
            "Specimunk": "NC Museum of Natural Sciences", "Flowfin": "GoDurham",
            "Cabcrab": "GoDurham ACCESS", "Signalquid": "City of Raleigh Transportation",
            "Planthera": "Friday Institute", "Lecturlynx": "Friday Institute",
            "Catalogar": "NC State University Libraries", "Semantiff": "Duke University Libraries",
        }
        actual = {r["name"]: r["signature"]["anchor_name"] for r in self.document["modemon"].values() if r["signature"]}
        self.assertEqual(actual, expected)

    def test_canonical_generated_json_matches_yaml_and_schema(self):
        with modedex.OUTPUT_PATH.open(encoding="utf-8") as stream:
            generated = json.load(stream)
        self.assertEqual(generated, self.document)
        modedex.validate(generated, self.schema)

    def test_build_is_byte_identical_utf8_and_preserves_array_order(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "modedex.json"
            modedex.build(output_path=output)
            first = output.read_bytes()
            modedex.build(output_path=output)
            self.assertEqual(first, output.read_bytes())
            self.assertTrue(first.endswith(b"\n"))
            self.assertFalse(first.endswith(b"\n\n"))
            self.assertIn("Beyonc\u00e9".encode("utf-8"), first)
            self.assertEqual(json.loads(first), self.document)
            self.assertEqual(first, modedex.OUTPUT_PATH.read_bytes())

    def test_key_order_does_not_change_build_bytes(self):
        def reverse_mappings(value):
            if isinstance(value, dict):
                return {k: reverse_mappings(v) for k, v in reversed(list(value.items()))}
            if isinstance(value, list):
                return [reverse_mappings(v) for v in value]
            return value

        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "source.yaml", Path(directory) / "output.json"
            source.write_text(yaml.safe_dump(reverse_mappings(self.document), sort_keys=False, allow_unicode=True), encoding="utf-8")
            modedex.build(source, output)
            self.assertEqual(output.read_bytes(), modedex.OUTPUT_PATH.read_bytes())

    def test_build_and_cli_do_not_mutate_unrelated_files(self):
        before = unrelated_hashes()
        result = subprocess.run([sys.executable, "-B", str(modedex.ROOT / "scripts/build_modedex.py")],
                                cwd=modedex.ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("51 Modemon", result.stdout)
        self.assertEqual(unrelated_hashes(), before)

    def test_missing_source_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                modedex.build(Path(directory) / "missing.yaml", Path(directory) / "output.json")

    def test_duplicate_ids_and_fields_are_rejected_before_overwriting(self):
        cases = [
            "version: 1\nversion: 1\n",
            "modemon:\n  detector_base: {}\n  detector_base: {}\n",
            "modemon:\n  detector_base:\n    name: Seeklet\n    name: replacement\n",
            "families:\n  detector: {}\n  detector: {}\n",
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.yaml"
            for text in cases:
                path.write_text(text, encoding="utf-8")
                with self.assertRaisesRegex(modedex.ModedexValidationError, "Duplicate YAML key"):
                    modedex.load_yaml(path)

    def test_nonstring_keys_and_yaml_merge_keys_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.yaml"
            for text in ["1: invalid\n", "defaults: &defaults {name: test}\nrecord: {<<: *defaults}\n"]:
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(modedex.ModedexValidationError):
                    modedex.load_yaml(path)

    def test_missing_unexpected_or_legacy_fields_fail(self):
        for field in self.document["modemon"]["detector_base"]:
            document = copy.deepcopy(self.document)
            del document["modemon"]["detector_base"][field]
            self.assert_invalid(document, "modemon.detector_base")
        document = copy.deepcopy(self.document)
        document["spawn_rates"] = {}
        self.assert_invalid(document, "Additional properties")
        self.assert_invalid(self.changed_record(input_output="Images to predictions"), "input_output")
        document = copy.deepcopy(self.document)
        del document["version"]
        self.assert_invalid(document, "version")

    def test_unknown_ids_habitats_and_scalar_arrays_fail(self):
        self.assert_invalid(self.changed_record(family_id="unknown"), "family_id")
        self.assert_invalid(self.changed_record(habitats=["unknown"]), "habitats")
        self.assert_invalid(self.changed_record(habitats="healthcare / finance"), "habitats")
        self.assert_invalid(self.changed_record(models_algorithms="CNN; ViT; YOLO"), "models_algorithms")
        document = copy.deepcopy(self.document)
        document["families"]["unknown"] = document["families"]["detector"]
        self.assert_invalid(document, "unknown")

    def test_whitespace_text_empty_and_nonstring_array_values_fail(self):
        for field in ["name", "role", "input_data", "output_data", "dex_entry"]:
            self.assert_invalid(self.changed_record(**{field: " \n\t"}), field)
        for field in ["ai_tasks", "models_algorithms", "biases_limitations", "explainability"]:
            for value in [[], [""], ["  "], [42]]:
                self.assert_invalid(self.changed_record(**{field: value}), field)
        self.assert_invalid(self.changed_record(input_data=["images"]), "input_data")
        self.assert_invalid(self.changed_record(output_data=None), "output_data")

    def test_signature_urls_are_checked_not_just_annotated(self):
        checker = modedex.format_checker()
        for url in ["", "not a uri", "/relative/source", "https://example.org/space here", "https://example.org/%ZZ"]:
            self.assertFalse(checker.conforms(url, "uri"))
            document = copy.deepcopy(self.document)
            document["modemon"]["recommender_ai_curator"]["signature"]["source_url"] = url
            self.assert_invalid(document, "source_url")
        for url in ["urn:example:source", "https://"]:
            document = copy.deepcopy(self.document)
            document["modemon"]["recommender_ai_curator"]["signature"]["source_url"] = url
            self.assert_invalid(document, "HTTP(S)")

    def test_stage_and_rarity_mismatches_fail(self):
        for changes in [{"stage": 0}, {"stage": 4}, {"stage": True}, {"rarity": "legendary"},
                        {"rarity": "common"}, {"rarity": "signature"}]:
            self.assert_invalid(self.changed_record(**changes))

    def test_missing_and_inappropriate_signature_metadata_fail(self):
        self.assert_invalid(self.changed_record("recommender_ai_curator", signature=None), "signature")
        signature = self.document["modemon"]["recommender_ai_curator"]["signature"]
        for modemon_id in ["detector_base", "detector_disease"]:
            self.assert_invalid(self.changed_record(modemon_id, signature=signature), "signature")
        document = copy.deepcopy(self.document)
        document["modemon"]["recommender_ai_curator"]["signature"]["documented_technology"] = [""]
        self.assert_invalid(document, "documented_technology")

    def test_wrong_record_and_stage_counts_fail(self):
        document = copy.deepcopy(self.document)
        del document["modemon"]["detector_disease"]
        self.assert_invalid(document, "Expected exactly 51")
        document = self.changed_record("detector_disease", stage=1, rarity="common", evolves_from=None)
        self.assert_invalid(document, "Expected stage counts")

    def test_family_base_missing_wrong_or_not_unique_fails(self):
        for base_id in ["detector_missing", "anomaly_base", "detector_disease"]:
            document = copy.deepcopy(self.document)
            document["families"]["detector"]["base_modemon_id"] = base_id
            self.assert_invalid(document, "base_modemon_id")
        document = self.changed_record("anomaly_base", family_id="detector")
        self.assert_invalid(document, "expected exactly one base")

    def test_parent_must_exist_be_same_family_and_immediately_previous_stage(self):
        for parent_id, message in [("detector_missing", "unknown parent"), ("anomaly_base", "same family"),
                                   ("detector_defect", "stage-1 parent")]:
            self.assert_invalid(self.changed_record(evolves_from=parent_id), message)
        self.assert_invalid(self.changed_record("recommender_ai_curator", evolves_from="recommender_base"), "stage-2 parent")
        self.assert_invalid(self.changed_record("detector_base", evolves_from="detector_disease"), "evolves_from")

    def test_evolution_cycles_fail_explicitly(self):
        self.assert_invalid(self.changed_record(evolves_from="detector_disease"), "Evolution cycle")
        document = self.changed_record(evolves_from="detector_defect")
        document["modemon"]["detector_defect"]["evolves_from"] = "detector_disease"
        self.assert_invalid(document, "Evolution cycle")

    def test_stable_id_family_prefix_is_validated(self):
        document = copy.deepcopy(self.document)
        document["modemon"]["seeklet_new"] = document["modemon"].pop("detector_disease")
        self.assert_invalid(document, "stable ID")

    def test_invalid_build_does_not_replace_previous_json(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "bad.yaml", Path(directory) / "modedex.json"
            source.write_text("version: 1\n", encoding="utf-8")
            output.write_bytes(b"previous valid build\n")
            with self.assertRaises(modedex.ModedexValidationError):
                modedex.build(source, output)
            self.assertEqual(output.read_bytes(), b"previous valid build\n")

    def test_build_cannot_overwrite_its_inputs(self):
        for path in [modedex.SOURCE_PATH, modedex.SCHEMA_PATH]:
            with self.assertRaisesRegex(modedex.ModedexValidationError, "must not overwrite"):
                modedex.build(output_path=path)


if __name__ == "__main__":
    unittest.main()
