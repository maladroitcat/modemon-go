"""The browser bridge must not mutate any analytical source."""
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('web_runtime', ROOT / 'scripts/build_web_runtime.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class WebRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = bridge.build_payload()

    def test_runtime_counts(self):
        self.assertEqual(len(self.payload['pois']), 927)
        self.assertEqual(len(self.payload['zones']), 62)
        self.assertEqual(len(self.payload['regions']), 8)
        self.assertEqual(len(self.payload['modedex']['modemon']), 51)
        self.assertEqual(sum(p['special_destination'] for p in self.payload['pois']), 17)

    def test_deterministic_and_committed_artifact_matches(self):
        self.assertEqual(self.payload, bridge.build_payload())
        expected = json.loads(bridge.DESTINATION.read_text())
        for index, poi in enumerate(self.payload['pois']):
            for key, value in poi.items():
                self.assertEqual(value, expected['pois'][index][key],
                                 f"POI mismatch: {poi['id']}.{key}")
        self.assertEqual(self.payload, expected)

    def test_all_source_hashes_match_and_sources_unchanged(self):
        bridge.build_payload()
        for f, digest in self.payload['source_hashes'].items():
            self.assertEqual(digest, hashlib.sha256((ROOT / f).read_bytes()).hexdigest())

    def test_geometries_are_exact_not_simplified(self):
        for source, key in [('regions.geojson', 'regions'), ('habitat_zones.geojson', 'zones'),
                            ('habitat_unclassified_areas.geojson', 'neutral')]:
            features = json.loads((ROOT / 'data/processed' / source).read_text())['features']
            self.assertEqual([f['geometry'] for f in features], [f['geometry'] for f in self.payload[key]])

    def test_sensitive_and_unapproved_associations_disabled(self):
        self.assertEqual(self.payload['signatures']['enabled'], [])
        self.assertEqual(self.payload['art']['approved'], {})
        self.assertFalse(any(p['eligible'] for p in self.payload['pois'] if p['region'] == 'RAL-05'))
        for p in self.payload['pois']:
            self.assertEqual(p['eligible'], not p['exclusion_reasons'])


if __name__ == '__main__':
    unittest.main()
