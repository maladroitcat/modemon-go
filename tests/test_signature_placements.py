"""Fail closed on individual unsafe placements; never mutate research or geography."""
import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path

import yaml
from pyproj import CRS, Transformer
from shapely.geometry import shape

from scripts import build_web_runtime as bridge
from scripts.signature_placements import build_signatures, CONFIG, EVIDENCE, ALTERNATIVES, STOPS

ROOT = Path(__file__).resolve().parents[1]


class SignaturePlacementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        payload = bridge.build_payload()
        with (ROOT / 'data/processed/special_poi_curation.csv').open() as stream:
            curation = {r['poi_id']: r for r in csv.DictReader(stream)}
        cls.args = (payload['modedex'], payload['pois'], curation,
                    {r['properties']['region_id']: shape(r['geometry']) for r in payload['regions']},
                    payload['precedence'], Transformer.from_crs(4326, 2264, always_xy=True),
                    CRS(2264).axis_info[0].unit_conversion_factor)
        cls.config = yaml.safe_load((ROOT / CONFIG).read_text())
        cls.evidence = json.loads((ROOT / EVIDENCE).read_text())
        cls.alternatives = json.loads((ROOT / ALTERNATIVES).read_text())

    def validate(self, change=None, evidence_change=None, args=None):
        config, evidence = copy.deepcopy(self.config), copy.deepcopy(self.evidence)
        if change:
            change(config)
        if evidence_change:
            evidence_change(evidence)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / CONFIG).parent.mkdir(parents=True)
            (root / CONFIG).write_text(yaml.safe_dump(config))
            (root / EVIDENCE).write_text(json.dumps(evidence))
            for extra in (ALTERNATIVES, STOPS):
                (root / extra).write_bytes((ROOT / extra).read_bytes())
            return build_signatures(root, *(args or self.args))

    def test_all_twelve_approved_real_placements_have_individual_evidence(self):
        result = self.validate()
        self.assertEqual(len(result['entries']), 12)
        self.assertEqual(len(result['enabled']), 12)
        self.assertEqual(result['demo_enabled'], sorted(self.config['mappings']))
        self.assertFalse(any(e['placement'] is None for e in result['entries']))
        for e in result['entries']:
            if e['placement']:
                dataset = self.alternatives if e.get('evidence_dataset') else self.evidence
                way = next(w for w in dataset['response']['elements'] if w['id'] == e['osm_way_id'])
                source = way['geometry'][way['nodes'].index(e['osm_node_id'])]
                self.assertEqual((source['lat'], source['lon']), (e['placement']['lat'], e['placement']['lon']))
            self.assertEqual(e['project_source_url'], self.args[0]['modemon'][e['species_id']]['signature']['source_url'])

    def test_missing_mapping_unknown_species_non_primary_and_ineligible_fail(self):
        with self.assertRaises(ValueError):
            self.validate(lambda c: c['mappings'].pop('extractor_history'))
        with self.assertRaises(ValueError):
            self.validate(lambda c: c['mappings'].update({'made_up': 'RAL-04_osm_node_2470661698'}))
        args = copy.deepcopy(self.args)
        args[2]['RAL-04_osm_node_2470661698']['selection_status'] = 'rejected'
        with self.assertRaises(ValueError):
            self.validate(args=args)
        args = copy.deepcopy(self.args)
        next(p for p in args[1] if p['id'] == 'RAL-04_osm_node_2470661698')['eligible'] = False
        with self.assertRaises(ValueError):
            self.validate(args=args)

    def test_private_crossing_indoor_or_incomplete_osm_evidence_fail(self):
        for tags in [{'access': 'private'}, {'footway': 'crossing'}, {'indoor': 'yes'}, {'highway': 'busway'}]:
            def change(evidence):
                next(w for w in evidence['response']['elements'] if w['id'] == 758590635)['tags'].update(tags)
            with self.subTest(tags=tags), self.assertRaises(ValueError):
                self.validate(evidence_change=change)
        with self.assertRaises(ValueError):
            self.validate(evidence_change=lambda e: e['response'].update(remark='timeout'))

    def test_missing_node_wrong_region_and_unsafe_evidence_url_fail(self):
        key = 'RAL-04_osm_node_2470661698'
        with self.assertRaises(ValueError):
            self.validate(lambda c: c['anchors'][key].update(osm_node_id=-1))
        with self.assertRaises(ValueError):
            self.validate(lambda c: c['anchors'][key].update(evidence_url='javascript:alert(1)'))
        args = copy.deepcopy(self.args)
        args[3].pop('RAL-04')
        with self.assertRaises(ValueError):
            self.validate(args=args)

    def test_building_closure_is_sourced_and_does_not_block_public_sidewalk(self):
        result = self.validate()
        hunt = next(e for e in result['entries'] if e['species_id'] == 'generator_catalog')
        self.assertNotIn('2026-10-19', hunt['blocked_dates'])
        notice = hunt['site_notices'][0]
        self.assertEqual(notice['scope'], 'associated_building')
        self.assertEqual(notice['start_date'], '2026-10-19')
        self.assertEqual(notice['source_url'], 'https://www.lib.ncsu.edu/hunt/visit')
        self.assertIn('You do not need to enter', notice['message'])
        with self.assertRaises(ValueError):
            self.validate(lambda c: c['anchors'][hunt['poi_id']]['site_notices'][0].update(source_url=''))

    def test_alternative_stop_requires_matching_official_identity(self):
        key = 'DUR-01_osm_node_5844548329'
        with self.assertRaises(ValueError):
            self.validate(lambda c: c['anchors'][key].update(official_stop_id=6305))
        with self.assertRaises(ValueError):
            self.validate(lambda c: c['anchors'][key].update(minimum_station_distance_meters=400))
        station = next(e for e in self.validate()['entries'] if e['poi_id'] == key)
        self.assertTrue(station['ordinary_anchor_withheld'])


if __name__ == '__main__':
    unittest.main()
