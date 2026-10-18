#!/usr/bin/env python3
"""Import owner-approved local masters once; reproducibly derive browser assets."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageOps, features

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'assets/artwork_sources.json'
PUBLIC = ROOT / 'mobile/web/public/art'
MANIFEST = ROOT / 'mobile/web/src/data/art.json'
SIZES = (96, 320, 640)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def import_local(catalog):
    expected = {r['name'].lower(): key for key, r in catalog.items()}
    paths = sorted(p for p in ROOT.iterdir() if p.is_file() and p.suffix.lower() == '.png')
    resolved = {}
    for path in paths:
        key = 'logo' if path.name == 'modemongologo.png' else expected.get(path.stem.lower())
        if not key or key in resolved:
            raise ValueError(f'Unknown or ambiguous root image: {path.name}; owner review required')
        resolved[key] = path
    if set(resolved) != set(catalog) | {'logo'}:
        raise ValueError(f'Missing images: {sorted((set(catalog) | {"logo"}) - set(resolved))}')
    records = {}
    for key, path in sorted(resolved.items()):
        destination = ROOT / ('assets/brand/originals/modemon-go.png' if key == 'logo'
                              else f'assets/modemon/approved/originals/{key}.png')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and digest(destination) != digest(path):
            raise ValueError(f'Existing master differs: {destination}; never overwrite silently')
        if not destination.exists():
            shutil.copyfile(path, destination)
        records[key] = dict(original_filename=path.name, master=str(destination.relative_to(ROOT)),
                            sha256=digest(path))
    write_json(SOURCES, dict(version=1, approval_issue=23, records=records,
                            excluded_concepts=['assets/modemon/concepts/detector_base/v01.png',
                                               'assets/modemon/concepts/detector_base/v02.png']))


def derive(key, record):
    source = ROOT / record['master']
    if digest(source) != record['sha256']:
        raise ValueError(f'Master integrity mismatch: {key}')
    with Image.open(source) as original:
        original.load()
        image = original.convert('RGBA')
    alpha = image.getchannel('A')
    if alpha.getextrema()[0] != 0 or not alpha.getbbox():
        raise ValueError(f'Missing actual transparent background: {key}')
    bbox = alpha.getbbox()
    # Crop only fully transparent exterior pixels; fit the intact artwork without
    # stretching, recoloring, background removal or any creative alteration.
    cropped = image.crop(bbox)
    urls, outputs = {}, []
    for size in SIZES:
        if key == 'logo':
            canvas = ImageOps.contain(image, (size, size), Image.Resampling.LANCZOS)
        else:
            fitted = ImageOps.contain(cropped, (round(size * .94), round(size * .94)), Image.Resampling.LANCZOS)
            canvas = Image.new('RGBA', (size, size))
            canvas.paste(fitted, ((size - fitted.width) // 2, (size - fitted.height) // 2))
        prefix = f'{key}.{record["sha256"][:12]}.{size}'
        for extension in ('webp', 'png') if size == 320 else ('webp',):
            path = PUBLIC / f'{prefix}.{extension}'
            if extension == 'webp':
                canvas.save(path, 'WEBP', quality=84, method=6, exact=True)
            else:
                canvas.save(path, 'PNG', optimize=True)
            budget = 220_000 if extension == 'png' else 130_000
            if path.stat().st_size > budget:
                raise ValueError(f'Derivative exceeds {budget}-byte budget: {path.name}')
            urls[f'{extension}_{size}'] = f'/art/{path.name}'
            outputs.append(dict(path=urls[f'{extension}_{size}'], bytes=path.stat().st_size,
                                sha256=digest(path), width=canvas.width, height=canvas.height))
    return dict(**record, width=image.width, height=image.height, alpha_bbox=list(bbox),
                urls=urls, outputs=outputs)


def build(import_images=False):
    if not features.check('webp'):
        raise ValueError('Pillow needs WebP support')
    catalog = json.loads((ROOT / 'data/processed/modedex.json').read_text())['modemon']
    if import_images:
        import_local(catalog)
    records = json.loads(SOURCES.read_text())['records']
    if set(records) != set(catalog) | {'logo'}:
        raise ValueError('Artwork IDs must cover the 51 canonical IDs and logo exactly')
    PUBLIC.mkdir(parents=True, exist_ok=True)
    result = {key: derive(key, record) for key, record in sorted(records.items())}
    manifest = dict(version=1, creatures={key: value for key, value in result.items() if key != 'logo'},
                    logo=result['logo'])
    write_json(MANIFEST, manifest)
    write_json(ROOT / 'output/artwork_mapping_report.json', dict(
        canonical_count=len(catalog), matched_count=len(records) - 1,
        missing=[], ambiguous=[], unknown=[], duplicate_sources=[],
        original_bytes=sum((ROOT / r['master']).stat().st_size for r in records.values()),
        derivative_bytes=sum(o['bytes'] for r in result.values() for o in r['outputs']),
        records=result,
        note='Root originals remain untouched. Earlier Seeklet concepts are not approved game assets.'))
    # A contact sheet is QA only, not a newly generated creature image.
    sheet = Image.new('RGB', (7 * 170, 8 * 190), '#eef7fc')
    from PIL import ImageDraw
    draw = ImageDraw.Draw(sheet)
    for i, key in enumerate(sorted(catalog)):
        sprite = Image.open(ROOT / 'mobile/web/public' / result[key]['urls']['png_320'].lstrip('/')).convert('RGBA')
        sprite.thumbnail((150, 150))
        x, y = i % 7 * 170, i // 7 * 190
        sheet.paste(sprite, (x + 10, y + 4), sprite)
        draw.text((x + 8, y + 156), catalog[key]['name'], fill='#102653')
        draw.text((x + 8, y + 173), key, fill='#102653')
    sheet.save(ROOT / 'output/artwork_contact_sheet.jpg', quality=90)
    print(f'Artwork: 51/51 + logo; {sum(o["bytes"] for r in result.values() for o in r["outputs"]):,} derivative bytes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-local', action='store_true', help='Validate and copy owner-approved root PNGs to immutable tracked masters')
    build(parser.parse_args().import_local)
