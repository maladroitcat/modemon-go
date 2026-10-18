#!/usr/bin/env python3
"""Optional refresh of placement evidence, never a runtime routing service."""
import json
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
    runtime = json.loads((ROOT / 'mobile/web/src/data/runtime.json').read_text())
    pois = {p['id']: p for p in runtime['pois']}
    clauses = []
    for poi_id in IDS:
        p = pois[poi_id]
        clauses.append(f'way(around:150,{p["lat"]},{p["lon"]})'
                       '[highway~"^(footway|path|pedestrian)$"];')
        clauses.append(f'way(around:150,{p["lat"]},{p["lon"]})[building];')
    query = '[out:json][timeout:90];(' + ''.join(clauses) + ');out geom;'
    response = requests.get('https://overpass-api.de/api/interpreter',
                            params={'data': query}, timeout=120,
                            headers={'User-Agent': 'ModemonGO/SignaturePlacementQA '
                                     '(https://github.com/maladroitcat/modemon-go)'})
    response.raise_for_status()
    payload = response.json()
    if payload.get('remark') or not payload.get('elements'):
        raise ValueError('Incomplete access evidence; keep previous snapshot')
    TARGET.write_text(json.dumps(dict(query=query, response=payload),
                                 indent=2, sort_keys=True) + '\n')
    print(f'Saved {len(payload["elements"])} OSM evidence objects to {TARGET}')


if __name__ == '__main__':
    main()
