#!/usr/bin/env python3
"""Optional refresh of placement evidence, never a runtime routing service."""
import json
import argparse
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'mobile/web/config/signature_access_osm.json'
IDS = [
    'RAL-04_osm_node_2470661698', 'RAL-01_osm_way_197842115',
    'RAL-04_osm_way_177166351', 'DUR-02_osm_way_30424777',
    'DUR-02_osm_way_391474817', 'DUR-01_osm_node_5844548329',
    'RAL-01_osm_node_13659913892',
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--durham-alternatives', action='store_true')
    args = parser.parse_args()
    runtime = json.loads((ROOT / 'mobile/web/src/data/runtime.json').read_text())
    pois = {p['id']: p for p in runtime['pois']}
    clauses = []
    for poi_id in IDS:
        p = pois[poi_id]
        clauses.append(f'way(around:150,{p["lat"]},{p["lon"]})'
                       '[highway~"^(footway|path|pedestrian)$"];')
        clauses.append(f'way(around:150,{p["lat"]},{p["lon"]})[building];')
    query = '[out:json][timeout:90];(' + ''.join(clauses) + ');out geom;'
    target = TARGET
    if args.durham_alternatives:
        p = pois['DUR-01_osm_node_5844548329']
        around = f'(around:650,{p["lat"]},{p["lon"]})'
        query = ('[out:json][timeout:90];('
                 f'node{around}[highway=bus_stop];node{around}[public_transport];'
                 f'way{around}[highway];way{around}[building];way{around}[amenity=bus_station];'
                 f'way{around}[landuse=construction];);out geom;')
        target = ROOT / 'mobile/web/config/durham_pedestrian_alternatives_osm.json'
    response = requests.get('https://overpass-api.de/api/interpreter',
                            params={'data': query}, timeout=120,
                            headers={'User-Agent': 'ModemonGO/SignaturePlacementQA '
                                     '(https://github.com/maladroitcat/modemon-go)'})
    response.raise_for_status()
    payload = response.json()
    if payload.get('remark') or not payload.get('elements'):
        raise ValueError('Incomplete access evidence; keep previous snapshot')
    target.write_text(json.dumps(dict(query=query, response=payload),
                                 indent=2, sort_keys=True) + '\n')
    print(f'Saved {len(payload["elements"])} OSM evidence objects to {target}')


if __name__ == '__main__':
    main()
