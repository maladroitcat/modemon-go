"""Offline research integrity; live URL checks are explicit, paced opt-in audits."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import yaml

from scripts import build_workbook_research_review as research
from scripts.audit_workbook_lessons import Page


class WorkbookResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = yaml.safe_load((research.ROOT / "data/config/modedex_learning_links.yaml").read_text())
        cls.canon = yaml.safe_load((research.ROOT / "data/config/modedex.yaml").read_text())
        cls.evidence = json.loads((research.RESEARCH / "workbook_lesson_verification.json").read_text())

    def test_all_51_canonical_ids_and_names_are_inventoried(self):
        research.validate(self.data, self.canon, self.evidence)
        self.assertEqual(len(self.data["species"]), 51)
        self.assertEqual(set(self.data["species"]), set(self.canon["modemon"]))

    def test_inventory_preserves_actual_canonical_fields_and_separate_signature_sources(self):
        rows = research.rows_for(self.data, self.canon)
        for row in rows:
            original = self.canon["modemon"][row["species_id"]]
            for field in research.INVENTORY_FIELDS:
                self.assertEqual(row[field], original[field])
            self.assertEqual(row["signature_project_source_url"], (original["signature"] or {}).get("source_url", ""))
        self.assertEqual(sum(bool(r["signature_project_source_url"]) for r in rows), 12)

    def test_precise_authorized_links_have_live_content_and_toc_evidence(self):
        for lesson_id, lesson in self.data["lessons"].items():
            research.check_url(lesson["url"])
            evidence = self.evidence[lesson_id]
            self.assertEqual(evidence["http_status"], 200)
            self.assertTrue(all(evidence["verification_terms_found"].values()))
            self.assertEqual(evidence["article_title"], lesson["article_title"])
            self.assertEqual(evidence["toc_url"], lesson["toc_url"])
            self.assertTrue(evidence["toc_link_label"])

    def test_all_15_unit_tocs_were_inspected_and_selected_urls_are_discovered(self):
        toc = json.loads((research.RESEARCH / "workbook_toc_inventory.json").read_text())
        self.assertEqual(len(toc), 15)
        domains = {research.urlsplit(url).hostname for url in toc}
        self.assertEqual(domains, research.DOMAINS)
        for lesson in self.data["lessons"].values():
            self.assertIn(lesson["url"], [url for url, _ in toc[lesson["toc_url"]]["lessons"]])

    def test_partial_and_unresolved_matches_are_reviewed_not_forced(self):
        rows = research.rows_for(self.data, self.canon)
        unresolved = [r for r in rows if not r["primary_url"]]
        self.assertEqual(len(unresolved), 6)
        for row in unresolved:
            self.assertEqual(row["confidence"], "low")
            self.assertEqual(row["match_scope"], "unresolved")
            self.assertTrue(row["review_required"])
        for row in rows:
            if row["confidence"] != "high":
                self.assertTrue(row["review_required"])
            if row["secondary_url"]:
                self.assertTrue(row["secondary_rationale"])
                self.assertNotEqual(row["primary_url"], row["secondary_url"])

    def test_homepages_guessed_domains_and_non_https_urls_are_rejected(self):
        for url in ["https://deeplearningworkbook.com/", "https://deeplearningworkbook.com/nlp",
                    "http://datascienceworkbook.com/a/b/c", "https://example.com/a/b/c",
                    "https://deeplearningworkbook.com/nlp/a/b?guess=yes"]:
            with self.assertRaises(ValueError):
                research.check_url(url)

    def test_missing_species_false_evidence_and_bad_references_fail(self):
        data = copy.deepcopy(self.data)
        del data["species"]["detector_base"]
        with self.assertRaisesRegex(ValueError, "51"):
            research.validate(data, self.canon, self.evidence)
        data = copy.deepcopy(self.data)
        data["species"]["detector_base"]["primary_lesson"] = "made_up"
        with self.assertRaisesRegex(ValueError, "Unknown lesson"):
            research.validate(data, self.canon, self.evidence)
        evidence = copy.deepcopy(self.evidence)
        evidence["detection"]["http_status"] = 404
        with self.assertRaisesRegex(ValueError, "Invalid live lesson evidence"):
            research.validate(self.data, self.canon, evidence)

    def test_names_cannot_be_changed_and_weak_matches_cannot_skip_review(self):
        data = copy.deepcopy(self.data)
        data["species"]["detector_base"]["name"] = "Changed"
        with self.assertRaisesRegex(ValueError, "name mismatch"):
            research.validate(data, self.canon, self.evidence)
        data = copy.deepcopy(self.data)
        data["species"]["scheduler_transit"]["review_required"] = False
        with self.assertRaisesRegex(ValueError, "needs review"):
            research.validate(data, self.canon, self.evidence)

    def test_parser_ignores_script_body_and_captures_article(self):
        page = Page()
        page.feed('<h2>Navigation</h2><main><h1>Actual Lesson</h1><p>Useful concept.</p><script>not evidence</script><a href="/unit/chapter/lesson">Lesson</a></main>')
        self.assertIn(("h1", "Actual Lesson"), page.headings)
        self.assertNotIn("not evidence", " ".join(page.parts))
        self.assertIn(("/unit/chapter/lesson", "Lesson"), page.links)

    def test_reports_are_deterministic_and_protected_inputs_unchanged(self):
        before = research.protected_hashes()
        committed = json.loads((research.RESEARCH / "modedex_learning_source_hashes.json").read_text())
        self.assertEqual(before, committed)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            research.render(root)
            first = {p.name: p.read_bytes() for p in root.iterdir()}
            research.render(root)
            second = {p.name: p.read_bytes() for p in root.iterdir()}
            self.assertEqual(first, second)
            for name, content in first.items():
                self.assertEqual(content, (research.RESEARCH / name).read_bytes(), name)
            with (root / "modedex_learning_inventory.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 51)
            with (root / "modedex_learning_review_queue.csv").open() as stream:
                queue = list(csv.DictReader(stream))
            self.assertEqual(len(queue), sum(r["review_required"] == "True" for r in rows))
            self.assertEqual(len({r["species_id"] for r in queue}), len(queue))
        self.assertEqual(before, research.protected_hashes())


if __name__ == "__main__":
    unittest.main()
