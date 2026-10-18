"""Validate explicit gameplay approval and reproducible outdoor OSM placements."""
import hashlib
import json
from datetime import date
from urllib.parse import urlsplit

import yaml
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import transform

CONFIG = 'mobile/web/config/signature_encounters.yaml'
EVIDENCE = 'mobile/web/config/signature_access_osm.json'
ALTERNATIVES = 'mobile/web/config/durham_pedestrian_alternatives_osm.json'
STOPS = 'mobile/web/config/godurham_stop_evidence.json'


def https(value):
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username:
        raise ValueError(f'Expected public HTTPS evidence: {value}')
    return value


def build_signatures(root, dex, pois, curation, regions, precedence, project, unit):
    hashes = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in (CONFIG, EVIDENCE, ALTERNATIVES, STOPS)}
    config = yaml.safe_load((root / CONFIG).read_text())
    evidence = json.loads((root / EVIDENCE).read_text())['response']
    if evidence.get('remark'):
        raise ValueError('Incomplete Signature placement evidence')
    alternatives = json.loads((root / ALTERNATIVES).read_text())['response']
    official = json.loads((root / STOPS).read_text())
    https(official['source_url'])
    if alternatives.get('remark'):
        raise ValueError('Incomplete alternative placement evidence')
    datasets = {'default': evidence['elements'], 'durham_alternatives': alternatives['elements']}
    mappings = config['mappings']
    expected = {key for key, s in dex['modemon'].items() if s['stage'] == 3}
    if set(mappings) != expected or len(mappings) != 12:
        raise ValueError('Approval must explicitly cover exactly the 12 canonical Signatures')
    if set(config['anchors']) != set(mappings.values()):
        raise ValueError('Unmapped or missing Signature anchor')
    https(config['approval_issue'])
    schedule = config['schedule']
    if not isinstance(schedule['period_days'], int) or schedule['period_days'] < 2:
        raise ValueError('Signature schedule must retain days without a spawn')
    date.fromisoformat(schedule['epoch'])
    anchors = {p['id']: p for p in pois}
    entries = []
    for species_id, poi_id in sorted(mappings.items()):
        if poi_id not in anchors or curation.get(poi_id, {}).get('selection_status') != 'primary':
            raise ValueError(f'Unapproved curated Signature destination: {poi_id}')
        poi = anchors[poi_id]
        source = dex['modemon'][species_id]['signature']
        https(source['source_url'])
        if not source['verified_use'] or not source['anchor_scope']:
            raise ValueError(f'Missing canonical project attribution: {species_id}')
        spec = config['anchors'][poi_id]
        https(spec['evidence_url'])
        if not spec['association_note'].strip() or not spec['review_note'].strip():
            raise ValueError(f'Missing safety explanation: {poi_id}')
        for blocked in spec['blocked_dates']:
            date.fromisoformat(blocked)
        status = spec['safety_status']
        if status not in ('mapped_public_approach', 'withheld_pending_safe_approach'):
            raise ValueError(f'Unknown placement safety status: {poi_id}')
        placement = None
        for notice in spec.get('site_notices', []):
            https(notice['source_url'])
            start = date.fromisoformat(notice['start_date'])
            if notice['end_date'] and date.fromisoformat(notice['end_date']) < start:
                raise ValueError('Invalid site notice date range')
            if notice['scope'] not in ('associated_building', 'nearby_construction') or not notice['message'].strip():
                raise ValueError('Site notice must distinguish building access from walkway safety')
        if status == 'mapped_public_approach':
            if not poi['eligible']:
                raise ValueError(f'Ineligible Signature destination: {poi_id}')
            elements = datasets[spec.get('evidence_dataset', 'default')]
            objects = {e['id']: e for e in elements if e['type'] == 'way'}
            buildings = [Polygon([(g['lon'], g['lat']) for g in e['geometry']])
                         for e in objects.values() if e.get('tags', {}).get('building')
                         and len(e.get('geometry', [])) >= 4
                         and e['geometry'][0] == e['geometry'][-1]]
            way = objects[spec['osm_way_id']]
            tags = way.get('tags', {})
            if (tags.get('highway') not in ('footway', 'pedestrian', 'path')
                    or tags.get('footway') == 'crossing'
                    or tags.get('access') in ('private', 'no', 'military', 'customers')
                    or tags.get('foot') in ('no', 'private')
                    or any(tags.get(key) for key in ('construction', 'indoor', 'tunnel', 'golf'))):
                raise ValueError(f'Not an outdoor public pedestrian approach: {poi_id}')
            index = way['nodes'].index(spec['osm_node_id'])
            coord = way['geometry'][index]
            point = Point(coord['lon'], coord['lat'])
            if any(b.covers(point) for b in buildings):
                raise ValueError(f'Placement inside building: {poi_id}')
            construction = [Polygon([(g['lon'], g['lat']) for g in e['geometry']])
                            for e in objects.values() if e.get('tags', {}).get('landuse') == 'construction'
                            and len(e.get('geometry', [])) >= 4 and e['geometry'][0] == e['geometry'][-1]]
            if any(c.covers(point) for c in construction):
                raise ValueError(f'Placement in construction: {poi_id}')
            matches = {rid for rid, geom in regions.items() if geom.covers(point)}
            owner = matches - {r['loser'] for r in precedence if r['winner'] in matches}
            if owner != {poi['region']}:
                raise ValueError(f'Wrong resolved placement region: {poi_id}')
            x, y = project.transform(point.x, point.y)
            offset = ((x * unit - poi['x']) ** 2 + (y * unit - poi['y']) ** 2) ** .5
            limit = spec.get('maximum_offset_meters', schedule['maximum_placement_offset_meters'])
            if not 0 < limit <= 300 or offset > limit:
                raise ValueError(f'Approach too far from approved anchor: {poi_id}')
            if spec.get('osm_stop_id'):
                stop = next(e for e in elements if e['type'] == 'node' and e['id'] == spec['osm_stop_id'])
                tags = stop.get('tags', {})
                record = next((s for s in official['stops'] if s['StopId'] == spec['official_stop_id']), None)
                if (not record or tags.get('highway') != 'bus_stop' or 'GoDurham' not in tags.get('network', '')
                        or str(record['StopId']) != tags.get('ref')):
                    raise ValueError('Alternative requires an official, matching GoDurham public stop')
                stop_xy = project.transform(stop['lon'], stop['lat'])
                agency_xy = project.transform(record['Longitude'], record['Latitude'])
                if (Point(x, y).distance(Point(*stop_xy)) * unit > 20
                        or Point(*stop_xy).distance(Point(*agency_xy)) * unit > 30
                        or offset < spec['minimum_station_distance_meters']):
                    raise ValueError('Alternative stop/sidewalk mismatch or too close to station works')
                roads = [LineString([(g['lon'], g['lat']) for g in e['geometry']])
                         for e in objects.values() if e.get('tags', {}).get('highway') in
                         ('primary', 'secondary', 'tertiary', 'residential', 'service', 'unclassified')
                         and len(e.get('geometry', [])) > 1]
                if any(transform(project.transform, road).distance(Point(x, y)) * unit < 2 for road in roads):
                    raise ValueError('Alternative lies in a road, not on a separate pedestrian approach')
            placement = dict(lat=point.y, lon=point.x, x=round(x * unit, 3), y=round(y * unit, 3))
        elif spec['osm_way_id'] is not None or spec['osm_node_id'] is not None:
            raise ValueError('Withheld placement must not carry an unverified real coordinate')
        entries.append(dict(species_id=species_id, poi_id=poi_id, placement=placement,
                            project_source_url=source['source_url'], **spec))
    if hashes != {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in hashes}:
        raise ValueError('Signature evidence changed during build')
    return dict(version=config['version'], placement_policy_version=config.get('placement_policy_version', 1),
                schedule=schedule, entries=entries,
                enabled=[e['species_id'] for e in entries if e['placement']],
                demo_enabled=sorted(mappings),
                source_hashes=hashes)
