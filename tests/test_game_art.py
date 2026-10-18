"""Approved owner masters and budgeted derivatives must be auditable by stable ID."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from scripts import build_game_art as art

ROOT = Path(__file__).resolve().parents[1]


class GameArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(art.SOURCES.read_text())['records']
        cls.manifest = json.loads(art.MANIFEST.read_text())
        cls.catalog = json.loads((ROOT / 'data/processed/modedex.json').read_text())['modemon']

    def test_51_exact_ids_and_logo_no_unknown_or_missing_or_duplicate_sources(self):
        self.assertEqual(set(self.sources), set(self.catalog) | {'logo'})
        self.assertEqual(set(self.manifest['creatures']), set(self.catalog))
        self.assertEqual(len(set(r['sha256'] for r in self.sources.values())), 52)
        for key, record in self.sources.items():
            self.assertEqual(record['original_filename'], 'modemongologo.png' if key == 'logo'
                             else self.catalog[key]['name'].lower() + '.png')

    def test_masters_are_byte_preserved_and_local_drop_copies_untouched(self):
        for record in self.sources.values():
            self.assertEqual(art.digest(ROOT / record['master']), record['sha256'])
            drop = ROOT / record['original_filename']
            if drop.exists():
                self.assertEqual(art.digest(drop), record['sha256'])
            self.assertFalse((ROOT / record['master']).is_relative_to(ROOT / 'mobile/web/public'))

    def test_every_derivative_has_real_alpha_correct_dimensions_and_integrity(self):
        records = [*self.manifest['creatures'].values(), self.manifest['logo']]
        for record in records:
            self.assertEqual(len(record['outputs']), 4)
            for output in record['outputs']:
                path = ROOT / 'mobile/web/public' / output['path'].lstrip('/')
                self.assertEqual(art.digest(path), output['sha256'])
                self.assertEqual(path.stat().st_size, output['bytes'])
                self.assertLessEqual(output['bytes'], 220_000 if path.suffix == '.png' else 130_000)
                with Image.open(path) as image:
                    self.assertEqual(image.size, (output['width'], output['height']))
                    alpha = image.convert('RGBA').getchannel('A')
                    self.assertEqual(alpha.getextrema()[0], 0)
                    self.assertGreater(alpha.getextrema()[1], 0)

    def test_derivatives_fit_intact_silhouettes_and_total_payload_budget(self):
        records = [*self.manifest['creatures'].values(), self.manifest['logo']]
        self.assertLess(sum(o['bytes'] for r in records for o in r['outputs']), 12_000_000)
        for record in self.manifest['creatures'].values():
            for output in record['outputs']:
                self.assertEqual(output['width'], output['height'])
                with Image.open(ROOT / 'mobile/web/public' / output['path'].lstrip('/')) as image:
                    bbox = image.convert('RGBA').getchannel('A').getbbox()
                    self.assertGreater(bbox[0], 0)
                    self.assertGreater(bbox[1], 0)
                    self.assertLess(bbox[2], image.width)
                    self.assertLess(bbox[3], image.height)

    def test_derivation_determinism_and_no_canonical_mutation(self):
        protected = {p: art.digest(p) for p in (ROOT / 'data/processed').iterdir() if p.is_file()}
        with tempfile.TemporaryDirectory() as directory, patch.object(art, 'PUBLIC', Path(directory)):
            first = art.derive('logo', self.sources['logo'])
            second = art.derive('logo', self.sources['logo'])
        self.assertEqual(first, second)
        self.assertEqual(protected, {p: art.digest(p) for p in protected})


if __name__ == '__main__':
    unittest.main()
