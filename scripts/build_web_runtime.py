#!/usr/bin/env python3
"""Read-only canonical-data bridge for the static browser MVP."""
import csv
import hashlib
import json
from pathlib import Path

import yaml
from pyproj import Transformer
from shapely.geometry import Point, shape

if __name__ == '__main__':
    from signature_placements import build_signatures
else:
    from scripts.signature_placements import build_signatures

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / 'mobile/web/src/data/runtime.json'
POLICY_VERSION = 'public-anchors-v1'
WORLD_IDENTITY = 'mobile/web/config/world_identity.json'
HABITATS = dict(zip(
    ['Healthcare', 'Finance', 'Retail', 'Food & Hospitality', 'Education & Research',
     'Transportation', 'Civic & Government', 'Entertainment', 'Office & Business'],
    ['healthcare', 'finance', 'retail', 'food_hospitality', 'education_research',
     'transportation', 'civic_government', 'entertainment', 'office_business']))
INPUTS = ['data/processed/' + f for f in (
    'modedex.json', 'regions.geojson', 'habitat_zones.geojson',
    'habitat_unclassified_areas.geojson', 'pois_labeled.geojson',
    'special_poi_primary.geojson', 'special_poi_curation.csv',
    'special_poi_candidate_scores.csv')] + ['data/config/region_resolution.yaml']


def gameplay_fingerprint(hashes, dex):
    """Copy edits must not reroll encounters or change persisted attempt IDs."""
    structured = {**dex, 'modemon': {
        key: {field: value for field, value in record.items() if field != 'dex_entry'}
        for key, record in dex['modemon'].items()}}
    sources = {**hashes, 'data/processed/modedex.json': hashlib.sha256(
        json.dumps(structured, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}
    return hashlib.sha256(json.dumps(dict(sources=sources, policy=POLICY_VERSION),
                                     sort_keys=True).encode()).hexdigest()


def build_payload(root=ROOT):
    hashes = {f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in INPUTS}
    identity_bytes = (root / WORLD_IDENTITY).read_bytes()
    identity = json.loads(identity_bytes)
    if (set(identity) != {'schema_version', 'legacy_data_version', 'gameplay_fingerprint'}
            or identity['schema_version'] != 1
            or not isinstance(identity['legacy_data_version'], str)
            or len(identity['legacy_data_version']) != 16
            or not isinstance(identity['gameplay_fingerprint'], str)
            or len(identity['gameplay_fingerprint']) != 64):
        raise ValueError('Invalid compatibility identity; do not silently reset player progress')
    def load(name):
        return json.loads((root / 'data/processed' / name).read_text())
    def table(name):
        with (root / 'data/processed' / name).open(newline='') as stream:
            return {r['poi_id']: r for r in csv.DictReader(stream)}
    regions = load('regions.geojson')['features']
    zones = load('habitat_zones.geojson')['features']
    neutral = load('habitat_unclassified_areas.geojson')['features']
    pois = load('pois_labeled.geojson')['features']
    dex = load('modedex.json')
    fingerprint = gameplay_fingerprint(hashes, dex)
    data_version = (identity['legacy_data_version']
                    if fingerprint == identity['gameplay_fingerprint'] else fingerprint[:16])
    if (len(regions), len(zones), len(pois), len(dex['modemon'])) != (8, 62, 927, 51):
        raise ValueError('Unexpected canonical counts; review runtime bridge before changing baseline')
    precedence = yaml.safe_load((root / 'data/config/region_resolution.yaml').read_text())['overlap_precedence']
    region_shapes = {r['properties']['region_id']: shape(r['geometry']) for r in regions}
    zone_shapes = [(z, shape(z['geometry'])) for z in zones]
    scores = table('special_poi_candidate_scores.csv')
    curation = table('special_poi_curation.csv')
    # State Plane is US survey feet, not international feet.
    project = Transformer.from_crs(4326, 2264, always_xy=True)
    from pyproj import CRS
    unit_to_m = CRS(2264).axis_info[0].unit_conversion_factor
    anchors = []
    for feature in pois:
        p = feature['properties']
        lon, lat = p['representative_longitude'], p['representative_latitude']
        point = Point(lon, lat)
        matches = {rid for rid, geom in region_shapes.items() if geom.covers(point)}
        remaining = matches - {r['loser'] for r in precedence if r['winner'] in matches}
        owner = next(iter(remaining)) if len(remaining) == 1 else None
        tags = p['raw_tags']
        if isinstance(tags, str):
            tags = json.loads(tags)
        human = curation.get(p['poi_id'], {})
        reasons = []
        if owner != p['region_id']:
            reasons.append('not_resolved_parent_owner')
        if not p['habitat_primary'] or p['habitat_review_required']:
            reasons.append('unclassified_or_habitat_review')
        if not p['name']:
            reasons.append('unnamed')
        if tags.get('access') in ('private', 'no', 'customers_only', 'military'):
            reasons.append('restricted_access')
        if (tags.get('shop') in ('alcohol', 'tobacco', 'e-cigarette', 'cannabis', 'erotic')
                or str(tags.get('min_age', '')).isdigit() and int(tags['min_age']) >= 18
                or tags.get('military') or tags.get('landuse') == 'military'):
            reasons.append('adult_or_security_restricted_feature')
        if tags.get('amenity') in ('school', 'kindergarten', 'childcare', 'prison',
                                  'hospital', 'clinic', 'doctors', 'police', 'fire_station',
                                  'bar', 'pub', 'nightclub') or tags.get('healthcare') in (
                                      'hospital', 'clinic', 'doctor', 'rehabilitation'):
            reasons.append('sensitive_or_age_restricted_facility')
        if human.get('gameplay_suitability') == 'sensitive_not_recommended' or human.get('current_status') in ('closed', 'unknown'):
            reasons.append('human_curation_exclusion')
        if human.get('selection_status') == 'rejected':
            reasons.append('human_curation_rejected')
        if scores[p['poi_id']]['candidate_access_status'] != 'likely_public' and human.get('selection_status') not in ('primary', 'alternate'):
            reasons.append('public_approach_not_established')
        contexts = [z['properties'] for z, geom in zone_shapes
                    if z['properties']['region_id'] == owner and geom.covers(point)]
        x, y = project.transform(lon, lat)
        anchors.append(dict(
            id=p['poi_id'], name=human.get('verified_name') or p['name'],
            # Metric helper coordinates only: millimetre quantization removes
            # platform libm residue, far below the one-metre density guard.
            region=p['region_id'], lat=lat, lon=lon,
            x=round(x*unit_to_m, 3), y=round(y*unit_to_m, 3),
            primary=HABITATS.get(p['habitat_primary']), secondary=HABITATS.get(p['habitat_secondary']),
            zone_ids=[z['zone_id'] for z in contexts],
            zone_habitats=sorted({HABITATS[z['habitat_primary']] for z in contexts}),
            eligible=not reasons, exclusion_reasons=reasons,
            association_note=human.get('association_anchor_note') or 'Association only. Never enter restricted areas or obstruct other people.',
            special_destination=human.get('selection_status') == 'primary',
            current_status=human.get('current_status') or 'not_human_verified',
            access_status=scores[p['poi_id']]['candidate_access_status']))
    def compact(feature, fields):
        return dict(type='Feature', geometry=feature['geometry'],
                    properties={k: feature['properties'][k] for k in fields})
    result = dict(
        version=1, bridge_policy_version=POLICY_VERSION,
        data_version=data_version, gameplay_fingerprint=fingerprint,
        content_version=hashlib.sha256(json.dumps(dict(sources=hashes, policy=POLICY_VERSION), sort_keys=True).encode()).hexdigest()[:16],
        source_hashes={**hashes, WORLD_IDENTITY: hashlib.sha256(identity_bytes).hexdigest()}, modedex=dex,
        regions=[compact(r, ['region_id', 'display_name', 'parent_city']) for r in regions],
        zones=[compact(z, ['zone_id', 'region_id', 'habitat_primary', 'dominant_secondary_habitat']) for z in zones],
        neutral=[compact(n, ['region_id']) for n in neutral],
        precedence=precedence, habitats=HABITATS, pois=sorted(anchors, key=lambda p: p['id']),
        signatures=build_signatures(root, dex, anchors, curation, region_shapes,
                                    precedence, project, unit_to_m),
        art=dict(approved={}, reason='Local Seeklet images are concepts awaiting approval; no final artwork is approved.'))
    if (hashes != {f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in INPUTS}
            or (root / WORLD_IDENTITY).read_bytes() != identity_bytes):
        raise RuntimeError('Canonical input changed during build')
    result['source_hashes'].update(result['signatures']['source_hashes'])
    result['content_version'] = hashlib.sha256(json.dumps(result['source_hashes'], sort_keys=True).encode()).hexdigest()[:16]
    return result


def main():
    result = build_payload()
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n', encoding='utf-8')
    print(f"Runtime {result['data_version']}: 51 species, 8 regions, 62 zones, 927 POIs, "
          f"{sum(p['eligible'] for p in result['pois'])} conservative public association anchors; "
          f"{len(result['signatures']['enabled'])} real / 12 demo Signature associations")


if __name__ == '__main__':
    main()
