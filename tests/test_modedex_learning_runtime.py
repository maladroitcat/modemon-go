"""Approved source integrity and read-only runtime learning-overlay builds."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts import build_modedex_learning as learning
from scripts import build_workbook_research_review as workbook
from scripts import review_external_learning_references as external


class LearningRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canon = learning.load_yaml(learning.ROOT / learning.INPUTS[0])
        cls.mappings = learning.load_yaml(learning.ROOT / learning.INPUTS[1])
        cls.proposals = learning.load_yaml(learning.ROOT / learning.INPUTS[2])
        cls.decisions = learning.load_yaml(learning.ROOT / learning.INPUTS[3])
        cls.we = json.loads((learning.ROOT / learning.INPUTS[4]).read_text())
        cls.ee = json.loads((learning.ROOT / learning.INPUTS[5]).read_text())
        cls.review = learning.load_yaml(learning.ROOT / learning.INPUTS[6])

    def payload(self, **changes):
        inputs = {k: copy.deepcopy(getattr(self, k)) for k in
                  ("canon", "mappings", "proposals", "decisions", "we", "ee", "review")}
        inputs.update(changes)
        return learning.make_overlay(inputs["canon"], inputs["mappings"], inputs["proposals"],
                                     inputs["decisions"], inputs["we"], inputs["ee"], inputs["review"])

    def test_exactly_39_ordinary_ids_and_no_12_signature_supplements(self):
        result = self.payload()["species"]
        self.assertEqual(set(result), {k for k, s in self.canon["modemon"].items() if s["stage"] < 3})
        self.assertEqual(len(result), 39)
        self.assertEqual(sum(s["stage"] == 3 for s in self.canon["modemon"].values()), 12)
        self.assertEqual(sum(r["primary"]["kind"] == "workbook" for r in result.values()), 35)
        self.assertEqual(sum(r["primary"]["kind"] == "external" for r in result.values()), 4)

    def test_exact_primary_and_distinct_secondary_workbook_urls_titles_sources(self):
        for key, row in self.payload()["species"].items():
            approved = self.mappings["species"][key]
            for kind in ("primary", "secondary"):
                ref = approved.get(kind + "_lesson")
                if ref:
                    source = self.mappings["lessons"][ref]
                    self.assertEqual(row[kind]["url"], source["url"])
                    self.assertEqual(row[kind]["title"], source["article_title"])
                    self.assertEqual(row[kind]["source"], source["workbook"])
                elif kind == "secondary":
                    self.assertIsNone(row[kind])
            if row["secondary"]:
                self.assertNotEqual(row["primary"]["url"], row["secondary"]["url"])

    def test_four_exact_external_urls_and_correct_publisher_not_workbook(self):
        urls = {
            "scheduler_hospital": "https://news.mit.edu/2016/robot-helps-nurses-schedule-tasks-on-labor-floor-0713",
            "scheduler_workforce": "https://www.ibm.com/think/topics/contact-center-workforce-optimization",
            "scheduler_delivery": "https://www.ibm.com/think/topics/dispatch-management",
            "scheduler_transit": "https://blog.optibus.com/transportation/can-artificial-intelligence-prevent-bus-bunching",
        }
        for key, url in urls.items():
            row = self.payload()["species"][key]["primary"]
            self.assertEqual(row["url"], url)
            self.assertEqual(row["source"], self.proposals["proposals"][key]["publisher"])
            self.assertEqual(row["kind"], "external")
            self.assertNotIn("Workbook", row["source"])

    def test_component_matches_have_honest_scope_not_complete_system_claim(self):
        for key, row in self.payload()["species"].items():
            source = self.mappings["species"][key]
            if source["primary_lesson"] and source["match_scope"] != "task":
                self.assertIn("Supporting concept", row["primary"]["scope_note"])
                self.assertIn("not a description of the complete system", row["primary"]["scope_note"])

    def test_no_ui_authorization_or_signature_authorization_fails(self):
        for field in ("non_signature_ui", "signature_supplementary_links"):
            mappings = copy.deepcopy(self.mappings)
            mappings["authorization"][field] = not mappings["authorization"][field]
            with self.assertRaisesRegex(ValueError, "owner authorization"):
                self.payload(mappings=mappings)
        decisions = copy.deepcopy(self.decisions)
        decisions.pop("implementation_authorization")
        with self.assertRaisesRegex(ValueError, "implementation authorization"):
            self.payload(decisions=decisions)

    def test_pending_held_or_replaced_external_sources_cannot_ship(self):
        for key in self.proposals["proposals"]:
            proposals = copy.deepcopy(self.proposals)
            proposals["proposals"][key]["approval_status"] = external.PENDING
            with self.assertRaisesRegex(ValueError, "not owner-approved"):
                self.payload(proposals=proposals)
            decisions = copy.deepcopy(self.decisions)
            decisions["decisions"][key]["decision"] = "held_for_replacement"
            with self.assertRaisesRegex(ValueError, "Unapproved outside"):
                self.payload(decisions=decisions)

    def test_bad_urls_and_empty_text_fail_instead_of_being_repaired(self):
        for url in ("javascript:alert(1)", "//www.ibm.com/think/x", "http://news.mit.edu/2016/x",
                    "https://deeplearningworkbook.com.evil.test/a", "https://www.ibm.com/",
                    "https://user@www.ibm.com/think/x", "https://www.ibm.com:443/think/x",
                    "https://www.ibm.com/think/x#script", "https://www.ibm.com/think/x?redirect=evil",
                    "https://www.ibm.com/think/x\n", "https://www.ibm.com\\evil.test/think/x"):
            with self.assertRaises(ValueError):
                learning.safe_url(url)
        for value in ("", "  ", None, "bad\x00text"):
            with self.assertRaisesRegex(ValueError, "learning text"):
                learning.text(value, "title")

    def test_repeat_builds_match_committed_json_and_do_not_modify_inputs_or_gameplay(self):
        before = workbook.protected_hashes()
        watched = [*learning.INPUTS, "mobile/web/src/data/runtime.json", "mobile/web/src/camera.ts",
                   "mobile/web/src/engine.ts", "mobile/web/src/quizzes.ts"]
        hashes = {p: hashlib.sha256((learning.ROOT / p).read_bytes()).hexdigest() for p in watched}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "learning.json"
            learning.build(path)
            first = path.read_bytes()
            learning.build(path)
            self.assertEqual(first, path.read_bytes())
            self.assertEqual(first, learning.DESTINATION.read_bytes())
        self.assertEqual(before, workbook.protected_hashes())
        self.assertEqual(hashes, {p: hashlib.sha256((learning.ROOT / p).read_bytes()).hexdigest() for p in watched})

    def test_cannot_overwrite_canonical_or_unrelated_files(self):
        for path in (learning.ROOT / learning.INPUTS[0], learning.ROOT / "mobile/web/src/Game.tsx"):
            with self.assertRaisesRegex(ValueError, "cannot overwrite"):
                learning.build(path)


if __name__ == "__main__":
    unittest.main()
