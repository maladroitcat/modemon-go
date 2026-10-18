"""Content-only edits must preserve all structured teaching and gameplay data."""
import copy
import hashlib
import json
import re
import unittest
from pathlib import Path

from scripts import build_web_runtime as bridge

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'mobile/web/tests/fixtures/intro-audit.json'


class PlaytestCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = json.loads(FIXTURE.read_text())
        cls.catalog = json.loads((ROOT / 'data/processed/modedex.json').read_text())

    def test_exactly_51_revised_standalone_brief_introductions(self):
        records = self.catalog['modemon']
        report = (ROOT / 'mobile/web/INTRODUCTION_REVIEW.md').read_text()
        self.assertEqual(len(records), 51)
        self.assertEqual(set(records), set(self.audit['before_introductions']))
        for key, record in records.items():
            text = record['dex_entry']
            with self.subTest(modemon=key):
                self.assertNotEqual(text, self.audit['before_introductions'][key])
                self.assertIn(text, report)
                self.assertIn(self.audit['before_introductions'][key], report)
                self.assertTrue(text.startswith(record['name'] + ' represents '))
                self.assertIn('AI', text)
                self.assertGreaterEqual(len(text.split()), 45)
                self.assertLessEqual(len(text.split()), 70)
                self.assertLess(len(text), 700)
                self.assertNotRegex(text, r'\b(CNN|NLP|OCR|LLM|ViT|GPS|CV|RAG)\b')
                self.assertNotIn('cousin', text.lower())
                for other in records.values():
                    if other['name'] != record['name']:
                        self.assertNotRegex(text, r'\b' + re.escape(other['name']) + r'\b')

    def test_all_non_intro_content_and_signature_evidence_unchanged(self):
        structured = copy.deepcopy(self.catalog)
        for record in structured['modemon'].values():
            record.pop('dex_entry')
        digest = hashlib.sha256(json.dumps(structured, sort_keys=True,
                                          separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(digest, self.audit['catalog_structure_sha256'])

    def test_protected_canonical_data_unchanged(self):
        for name, digest in self.audit['protected_hashes'].items():
            with self.subTest(path=name):
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)

    def test_copy_changes_content_version_not_gameplay_identity(self):
        payload = bridge.build_payload()
        fixture = json.loads((ROOT / 'mobile/web/tests/fixtures/mvp-gameplay.json').read_text())
        self.assertEqual(payload['data_version'], fixture['data_version'])
        self.assertNotEqual(payload['content_version'], payload['data_version'])
        hashes = {name: payload['source_hashes'][name] for name in bridge.INPUTS}
        changed = copy.deepcopy(self.catalog)
        changed['modemon']['detector_base']['dex_entry'] = 'A future editorial revision.'
        self.assertEqual(bridge.gameplay_fingerprint(hashes, changed), payload['gameplay_fingerprint'])
        changed['modemon']['detector_base']['role'] = 'A changed quiz answer'
        self.assertNotEqual(bridge.gameplay_fingerprint(hashes, changed), payload['gameplay_fingerprint'])


if __name__ == '__main__':
    unittest.main()
