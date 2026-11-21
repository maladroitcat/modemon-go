"""Owner-approved outdoor associations must be exact, scoped and reproducible."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

import yaml

from scripts import build_web_runtime as bridge
from scripts.healthcare_approvals import apply_healthcare_approvals, CONFIG

ROOT = Path(__file__).resolve().parents[1]
APPROVED = {
    'DUR-01_osm_node_13917907872', 'DUR-01_osm_node_14165026701',
    'DUR-01_osm_node_1659112337', 'DUR-01_osm_node_7674513212',
    'DUR-02_osm_node_5808304716', 'RAL-01_osm_node_14232394214',
    'RAL-01_osm_node_3248743365', 'RAL-01_osm_node_3305289269',
    'RAL-01_osm_node_4533068539', 'RAL-01_osm_node_7967845007',
    'RAL-01_osm_way_47776939', 'RAL-03A_osm_way_47917752',
}


class HealthcareApprovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = bridge.build_payload()
        cls.config = yaml.safe_load((ROOT / CONFIG).read_text())
        cls.before = copy.deepcopy(cls.payload['pois'])
        for p in cls.before:
            approval = p.pop('public_approach_approval', None)
            if approval:
                p.update(eligible=False, exclusion_reasons=approval['previous_exclusions'],
                         association_note=approval['previous_association_note'],
                         access_status=approval['previous_access_status'])

    def apply(self, change=None, anchors=None):
        config = copy.deepcopy(self.config)
        if change:
            change(config)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / CONFIG).parent.mkdir(parents=True)
            (root / CONFIG).write_text(yaml.safe_dump(config))
            return apply_healthcare_approvals(root, anchors or self.before)

    def test_exact_twelve_approved_ids_and_only_those_become_eligible(self):
        updated, metadata = self.apply()
        self.assertEqual(set(metadata['approved_poi_ids']), APPROVED)
        before = {p['id']: p for p in self.before}
        self.assertEqual({p['id'] for p in updated if p['eligible'] != before[p['id']]['eligible']}, APPROVED)
        self.assertEqual(sum(p['eligible'] for p in updated), 563)
        self.assertEqual(sum(p['special_destination'] for p in updated), 17)
        for p in updated:
            original = before[p['id']]
            if p['id'] not in APPROVED:
                self.assertEqual(p, original)
                continue
            self.assertTrue(p['eligible'])
            self.assertEqual(p['exclusion_reasons'], [])
            self.assertEqual(p['public_approach_approval']['effective_date'], '2026-11-21')
            self.assertEqual(p['public_approach_approval']['previous_exclusions'], original['exclusion_reasons'])
            for key in ('lat', 'lon', 'x', 'y', 'primary', 'secondary', 'zone_ids', 'zone_habitats', 'current_status'):
                self.assertEqual(p[key], original[key])
            self.assertIn('Do not enter healthcare buildings', p['association_note'])

    def test_hemp_and_other_unapproved_clinical_sites_stay_excluded(self):
        updated, _ = self.apply()
        by_id = {p['id']: p for p in updated}
        for poi_id in ['RAL-01_osm_way_47663698', 'RAL-01_osm_node_8412073792',
                       'DUR-02_osm_way_305879102', 'RAL-05_osm_way_198168608']:
            self.assertFalse(by_id[poi_id]['eligible'])
        self.assertFalse(any(p['eligible'] for p in updated if p['region'] == 'RAL-05'))

    def test_new_access_adult_or_closure_blocks_cannot_be_cleared(self):
        for reason in ('restricted_access', 'adult_or_security_restricted_feature', 'new_safety_hold'):
            anchors = copy.deepcopy(self.before)
            next(p for p in anchors if p['id'] in APPROVED)['exclusion_reasons'].append(reason)
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                self.apply(anchors=anchors)
        for state in ('closed', 'unknown'):
            anchors = copy.deepcopy(self.before)
            next(p for p in anchors if p['id'] == 'RAL-03A_osm_way_47917752')['current_status'] = state
            with self.subTest(state=state), self.assertRaises(ValueError):
                self.apply(anchors=anchors)

    def test_missing_mismatched_duplicate_excluded_and_unscoped_approvals_fail(self):
        changes = [
            lambda c: c['locations'][0].update(poi_id='missing'),
            lambda c: c['locations'][0].update(name='wrong identity'),
            lambda c: c['locations'].append(c['locations'][0]),
            lambda c: c['excluded_poi_ids'].append(c['locations'][0]['poi_id']),
            lambda c: c['locations'][0].update(override_exclusions=['restricted_access']),
            lambda c: c.update(scope='indoor'),
        ]
        for change in changes:
            with self.assertRaises(ValueError):
                self.apply(change)

    def test_input_immutable_source_hash_recorded_and_duke_uncertainty_preserved(self):
        before = copy.deepcopy(self.before)
        updated, metadata = apply_healthcare_approvals(ROOT, self.before)
        self.assertEqual(self.before, before)
        self.assertEqual(metadata['source_hashes'][CONFIG], hashlib.sha256((ROOT / CONFIG).read_bytes()).hexdigest())
        self.assertEqual(updated, self.payload['pois'])
        duke = next(p for p in updated if p['id'] == 'DUR-02_osm_node_5808304716')
        self.assertIn('name/existence is unverified', duke['association_note'])


if __name__ == '__main__':
    unittest.main()
