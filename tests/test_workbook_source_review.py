"""Research coverage and explicit approval isolation; no live network in tests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

from scripts import build_workbook_research_review as workbook
from scripts import review_external_learning_references as external
from scripts import review_workbook_coverage as coverage

INITIAL_REVIEW_IDS = {
    "anomaly_machine", "anomaly_network", "recommender_ai_curator", "recommender_learning",
    "recommender_adaptive_learning", "extractor_base", "extractor_medical", "extractor_government",
    "extractor_research", "extractor_history", "extractor_archive", "extractor_specimen",
    "scheduler_base", "scheduler_hospital", "scheduler_transit", "scheduler_transit_flow",
    "scheduler_ride_booking", "scheduler_traffic_signal", "scheduler_workforce", "scheduler_delivery",
    "generator_catalog",
}
NEW_COMPONENT_IDS = {"extractor_base", "extractor_medical", "extractor_government", "extractor_archive", "scheduler_transit_flow"}
GAP_IDS = {"extractor_specimen", "scheduler_hospital", "scheduler_transit", "scheduler_ride_booking", "scheduler_workforce", "scheduler_delivery"}


class SourceReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.workbooks, cls.canon, cls.review = external.load_inputs()
        cls.evidence = json.loads((external.RESEARCH / "external_reference_verification.json").read_text())
        cls.corpus = json.loads((external.RESEARCH / "workbook_full_review.json").read_text())
        cls.toc = json.loads((external.RESEARCH / "workbook_toc_inventory.json").read_text())

    def test_all_discovered_lesson_bodies_in_all_three_workbooks_were_indexed(self):
        urls = {url for unit in self.toc.values() for url, _ in unit["lessons"]}
        self.assertEqual(self.corpus["lesson_count"], 360)
        self.assertEqual(self.corpus["unit_count"], 15)
        self.assertEqual(set(self.corpus["pages"]), urls)
        self.assertEqual(self.corpus["failed_urls"], [])
        self.assertEqual({urlsplit(url).hostname for url in urls}, coverage.DOMAINS)
        for url, item in self.corpus["pages"].items():
            self.assertEqual(item["http_status"], 200)
            self.assertEqual(item["url"], url)
            self.assertTrue(item["article_title"])
            self.assertGreater(item["text_characters"], 200)
            self.assertEqual(len(item["main_text_sha256"]), 64)
            self.assertNotIn("text", item)  # No article bodies republished.

    def test_every_original_weak_or_unresolved_species_received_a_recorded_review(self):
        self.assertEqual(set(self.review["species"]), INITIAL_REVIEW_IDS)
        self.assertEqual(sum(r["previous_outcome"] == "unresolved" for r in self.review["species"].values()), 11)
        self.assertEqual(sum(r["previous_outcome"] == "partial" for r in self.review["species"].values()), 10)
        for key, row in self.review["species"].items():
            self.assertTrue(row["finding"].strip())
            self.assertTrue(self.workbooks["species"][key]["scope_label"].strip())
            for lesson_id in row["considered_lessons"]:
                url = self.workbooks["lessons"][lesson_id]["url"]
                self.assertIn(url, self.corpus["pages"])

    def test_new_component_matches_stay_honestly_scoped_and_reviewable(self):
        rows = self.workbooks["species"]
        for key in NEW_COMPONENT_IDS:
            self.assertIsNotNone(rows[key]["primary_lesson"])
            self.assertEqual(rows[key]["confidence"], "medium")
            self.assertTrue(rows[key]["review_required"])
            self.assertTrue(rows[key]["limitations"])
            self.assertIn("not", rows[key]["scope_label"].casefold())
        self.assertEqual(sum(bool(r["primary_lesson"]) for r in rows.values()), 45)

    def test_genuine_gaps_remain_unpopulated_and_external_only_proposed(self):
        self.assertEqual(set(self.data["proposals"]), GAP_IDS)
        for key in GAP_IDS:
            self.assertIsNone(self.workbooks["species"][key]["primary_lesson"])
            self.assertEqual(self.review["species"][key]["outcome"], "genuine_gap")
            self.assertTrue(self.data["proposals"][key]["why_workbooks_insufficient"])

    def test_rejected_keyword_leads_are_documented_with_actual_fetched_urls(self):
        self.assertGreaterEqual(len(self.review["rejected_keyword_matches"]), 5)
        for row in self.review["rejected_keyword_matches"]:
            self.assertIn(row["url"], self.corpus["pages"])
            self.assertTrue(row["reason"])

    def test_every_external_reference_including_evidence_remains_pending(self):
        external.validate(self.data, self.workbooks, self.canon, self.review, self.evidence)
        self.assertEqual(len(self.data["proposals"]), 6)
        self.assertEqual(len(self.evidence), 5)
        for row in self.data["proposals"].values():
            self.assertEqual(row["approval_status"], external.PENDING)
            self.assertEqual(self.evidence[row["proposed_url"]]["approval_status"], external.PENDING)

    def test_verification_or_shared_url_does_not_confer_approval(self):
        a, b = self.data["proposals"]["scheduler_hospital"], self.data["proposals"]["scheduler_workforce"]
        self.assertEqual(a["proposed_url"], b["proposed_url"])
        for key in GAP_IDS:
            changed = copy.deepcopy(self.data)
            changed["proposals"][key]["approval_status"] = "APPROVED"
            with self.assertRaisesRegex(ValueError, "must remain PENDING_OWNER_APPROVAL"):
                external.validate(changed, self.workbooks, self.canon, self.review, self.evidence)
        changed = copy.deepcopy(self.data)
        changed["approval_status"] = "APPROVED"
        with self.assertRaisesRegex(ValueError, "cannot approve"):
            external.validate(changed, self.workbooks, self.canon, self.review)

    def test_external_proposals_cannot_masquerade_as_shipped_mappings(self):
        changed = copy.deepcopy(self.data)
        changed["proposals"]["extractor_specimen"]["shipped_url"] = "https://example.com/"
        with self.assertRaisesRegex(ValueError, "masquerade"):
            external.validate(changed, self.workbooks, self.canon, self.review)
        for lesson in self.workbooks["lessons"].values():
            self.assertIn(urlsplit(lesson["url"]).hostname, coverage.DOMAINS)

    def test_external_proposals_need_genuine_gaps_and_correct_canonical_names(self):
        changed = copy.deepcopy(self.data)
        changed["proposals"]["generator_base"] = changed["proposals"].pop("extractor_specimen")
        with self.assertRaisesRegex(ValueError, "genuine reviewed workbook gaps"):
            external.validate(changed, self.workbooks, self.canon, self.review)
        changed = copy.deepcopy(self.data)
        changed["proposals"]["extractor_specimen"]["name"] = "Renamed"
        with self.assertRaisesRegex(ValueError, "canonical identity"):
            external.validate(changed, self.workbooks, self.canon, self.review)

    def test_external_urls_and_verification_fail_closed(self):
        for url in ["http://developers.google.com/optimization/routing", "https://example.com/lesson",
                    "https://developers.google.com/", "https://developers.google.com/optimization/routing?guess=yes"]:
            with self.assertRaises(ValueError):
                external.check_external_url(url)
        changed = copy.deepcopy(self.evidence)
        changed[next(iter(changed))]["http_status"] = 404
        with self.assertRaisesRegex(ValueError, "Invalid pending-source"):
            external.validate(self.data, self.workbooks, self.canon, self.review, changed)
        with patch.object(external.requests, "get") as get:
            get.return_value.status_code = 302
            with self.assertRaisesRegex(ValueError, "returned 302"):
                external.get("https://developers.google.com/optimization/routing")

    def test_full_article_cache_cannot_be_written_into_repository(self):
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            coverage.scan(coverage.ROOT / "data/research/article_bodies")

    def test_no_external_proposal_has_entered_canon_runtime_or_game(self):
        paths = [external.ROOT / p for p in ["data/config/modedex.yaml", "data/processed/modedex.json",
                 "mobile/web/src/data/runtime.json", "mobile/web/src/Game.tsx"]]
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for row in self.data["proposals"].values():
                self.assertNotIn(row["proposed_url"], text)

    def test_external_tables_are_deterministic_and_protect_source_bytes(self):
        before = workbook.protected_hashes()
        self.assertEqual(before, json.loads((external.RESEARCH / "modedex_learning_source_hashes.json").read_text()))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external.render(root)
            first = {p.name: p.read_bytes() for p in root.iterdir()}
            external.render(root)
            self.assertEqual(first, {p.name: p.read_bytes() for p in root.iterdir()})
            for name, content in first.items():
                self.assertEqual(content, (external.RESEARCH / name).read_bytes())
        self.assertEqual(before, workbook.protected_hashes())


if __name__ == "__main__":
    unittest.main()
