"""Research coverage and explicit approval isolation; no live network in tests."""
import copy
import hashlib
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
GAP_IDS = {"scheduler_hospital", "scheduler_transit", "scheduler_workforce", "scheduler_delivery"}


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
        self.assertEqual(len(self.data["proposals"]), 4)
        self.assertEqual(len(self.evidence), 4)
        for row in self.data["proposals"].values():
            self.assertEqual(row["approval_status"], external.PENDING)
            self.assertEqual(self.evidence[row["proposed_url"]]["approval_status"], external.PENDING)

    def test_verification_does_not_confer_approval(self):
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
        changed["proposals"]["scheduler_hospital"]["shipped_url"] = "https://example.com/"
        with self.assertRaisesRegex(ValueError, "masquerade"):
            external.validate(changed, self.workbooks, self.canon, self.review)
        for lesson in self.workbooks["lessons"].values():
            self.assertIn(urlsplit(lesson["url"]).hostname, coverage.DOMAINS)

    def test_external_proposals_need_genuine_gaps_and_correct_canonical_names(self):
        changed = copy.deepcopy(self.data)
        changed["proposals"]["generator_base"] = changed["proposals"].pop("scheduler_hospital")
        with self.assertRaisesRegex(ValueError, "uncovered non-Signature workbook gaps"):
            external.validate(changed, self.workbooks, self.canon, self.review)
        changed = copy.deepcopy(self.data)
        changed["proposals"]["scheduler_hospital"]["name"] = "Renamed"
        with self.assertRaisesRegex(ValueError, "canonical identity"):
            external.validate(changed, self.workbooks, self.canon, self.review)

    def test_external_urls_and_verification_fail_closed(self):
        for url in ["http://news.mit.edu/2015/example", "https://example.com/lesson",
                    "https://www.ibm.com/", "https://www.ibm.com/think/topics/dispatch-management?guess=yes"]:
            with self.assertRaises(ValueError):
                external.check_external_url(url)
        changed = copy.deepcopy(self.evidence)
        changed[next(iter(changed))]["http_status"] = 404
        with self.assertRaisesRegex(ValueError, "Invalid pending-source"):
            external.validate(self.data, self.workbooks, self.canon, self.review, changed)
        with patch.object(external.requests, "get") as get:
            get.return_value.status_code = 302
            with self.assertRaisesRegex(ValueError, "returned 302"):
                external.get("https://www.ibm.com/think/topics/dispatch-management")

    def test_all_existing_workbook_matches_and_snapshots_are_byte_frozen(self):
        expected = {
            "data/config/modedex_learning_links.yaml": "3a0f58da272eebe6a356904d5cfb37b9255f31690518a5b44f33d7c1a5bab81d",
            "data/research/modedex_learning_inventory.csv": "67473fda6038a4afb1f89f9ea9035b8c31fa4ab6e9d78ed1fd493b14c6251a90",
            "data/research/workbook_lesson_verification.json": "33b1715f36ad2eb9d3bb9a6cc562204b2aefbb05c8d1ba2dd3c43f8745356a98",
        }
        for path, digest in expected.items():
            self.assertEqual(hashlib.sha256((external.ROOT / path).read_bytes()).hexdigest(), digest, path)

    def test_scope_intersection_excludes_all_twelve_signatures(self):
        scope = external.reference_scope(self.workbooks, self.canon, self.review)
        self.assertEqual((scope["initial_workbook_matches"], scope["initial_workbook_blanks"]), (40, 11))
        self.assertEqual(len(scope["initial_blank_signature_ids"]), 3)
        self.assertEqual(len(scope["initial_blank_non_signature_ids"]), 8)
        self.assertEqual((scope["current_workbook_matches"], scope["current_workbook_blanks"]), (45, 6))
        self.assertEqual(len(scope["current_blank_signature_ids"]), 2)
        self.assertEqual(set(scope["outside_research_non_signature_ids"]), GAP_IDS)
        self.assertEqual((scope["non_signature_count"], scope["non_signature_workbook_matches"]), (39, 35))
        self.assertEqual(scope["signature_count"], 12)
        for key, url in scope["canonical_signature_project_sources"].items():
            self.assertTrue(url.startswith("https://"))
            self.assertNotIn(key, self.data["proposals"])

    def test_supplementary_signature_proposals_are_rejected_even_for_blank_workbooks(self):
        for key, record in self.canon["modemon"].items():
            if record["stage"] == 3:
                changed = copy.deepcopy(self.data)
                changed["proposals"][key] = copy.deepcopy(changed["proposals"]["scheduler_hospital"])
                changed["proposals"][key]["name"] = record["name"]
                with self.assertRaisesRegex(ValueError, "Signature forms already have sufficient"):
                    external.validate(changed, self.workbooks, self.canon, self.review)

    def test_sources_require_general_audience_scope_not_implementation(self):
        for key, row in self.data["proposals"].items():
            self.assertEqual(row["audience"], "general_public_no_ml_prerequisites")
            self.assertTrue(row["accessibility_reason"])
            changed = copy.deepcopy(self.data)
            changed["proposals"][key]["resource_type"] = "implementation_tutorial"
            with self.assertRaisesRegex(ValueError, "general audience, not implementation"):
                external.validate(changed, self.workbooks, self.canon, self.review)

    def test_article_audit_reads_body_sections_not_navigation(self):
        page = external.ExternalPage()
        page.feed('<nav>delivery fake</nav><h1>Title</h1><div class="body-article-8 container">'
                  'Real <div>article <script>ignore</script>words</div></div><footer>skip footer</footer>')
        self.assertEqual(" ".join(page.parts), "Real  article  words")
        self.assertEqual(page.headings, [("h1", "Title")])
        page = external.ExternalPage()
        page.feed('<main>Real <div>main</div></main><nav>skip</nav>')
        self.assertEqual(" ".join(page.parts), "Real  main")

    def test_stale_signature_source_evidence_is_rejected(self):
        changed = copy.deepcopy(self.evidence)
        changed["https://example.com/old-signature-supplement"] = {}
        with self.assertRaisesRegex(ValueError, "only the current non-Signature"):
            external.validate(self.data, self.workbooks, self.canon, self.review, changed)

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
