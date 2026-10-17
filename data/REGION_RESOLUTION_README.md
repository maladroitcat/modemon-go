# Gameplay Region Resolution (Step 7C)

Region precedence is a gameplay routing rule, not a modification of the underlying geographic source data.

Canonical analytical geometry preserves inherited overlaps so the original
region, cell, and zone coverage stays auditable. Runtime coordinates still need
one owning parent region to select gameplay context. This layer reads those
datasets without changing their geometry, scores, habitat assignments, or bytes.

## Explicit Decisions

`data/config/region_resolution.yaml` contains the canonical region inventory,
known overlap pairs, and the following precedence decisions:

| Winning Region | Overridden Region | Reason |
| --- | --- | --- |
| DUR-02 Duke University | DUR-01 Downtown Durham | More specific university gameplay environment |
| RAL-02 Dorothea Dix Park | RAL-04 NC State Centennial Campus | More specific recreational gameplay environment |
| RAL-03B Pullen Park | RAL-03A NC State Central Campus | More specific recreational gameplay environment |

No geometry size, region ID order, name order, or centroid distance determines
ownership. IDs are sorted only to make result lists reproducible.

## API and CLI

```sh
python3 -B scripts/resolve_game_region.py --lat 35.8 --lon -78.6
```

The CLI prints one compact JSON object. `RegionResolver` can be loaded once and
reused via `resolver.resolve(longitude, latitude)`. The convenience function
`resolve_game_region(longitude, latitude, resolver=None)` exposes the same result.
Both accept longitude first. Invalid, nonfinite, or out-of-range WGS84 coordinates
raise an error.

The resolver creates an EPSG:4326 point and tests each canonical region with
`covers`, including its boundary:

- No matches: `outside_game_regions`, with null `resolved_region_id`.
- One match: `single_match`.
- Multiple matches with one explicit winner: `explicit_overlap_precedence`, with
  `winning_region_id` and `overridden_region_ids`.
- Multiple matches without one explicit winner: `unresolved_overlap`, with null
  `resolved_region_id`. Every match is preserved in `matching_region_ids`.

For more than two matches, an owner must reach every other matching region
through explicit precedence edges among the matching regions. A region absent
from the coordinate cannot act as an intermediate precedence decision. Multiple
unrelated winners remain unresolved.

Configuration validation rejects missing region IDs, identical winners/losers,
duplicate or contradictory rules, cycles, and missing rules for known overlaps.
The separate known-overlap inventory ensures deleting a rule fails validation.
Unknown overlaps are reported explicitly at resolution time rather than assigned
an arbitrary owner.

## Habitat-zone Selection

`resolve_habitat_zone(longitude, latitude, resolver=None, zones=None, neutral=None)`
first resolves the parent. It searches habitat zones only in that owning region,
using `covers` again. A single hit returns `zone_match`, the zone ID, and primary
habitat. With no zone hit, it checks only that parent's neutral areas, returning
`neutral_match` or `no_retained_cell`. The latter preserves Step 7A's discarded
edge fragments as uncovered space. Unresolved or outside parent results never
activate a zone.

Two zones in the same parent can both cover a shared boundary. That case returns
`unresolved_zone_overlap` with candidate IDs and no selected zone. This step does
not invent a secondary zone-boundary precedence policy. Only one parent region
is active after explicit parent resolution.

For default canonical habitat lookup:

```sh
python3 -B scripts/resolve_game_region.py --lat 35.8 --lon -78.6 --include-habitat-zone
```

Zone lookup and integration QA read the committed canonical files directly:
`data/processed/habitat_zones.geojson` and
`data/processed/habitat_unclassified_areas.geojson`. Both are available from
updated `main`. Missing files fail explicitly; no alternate zone copies or
environment-variable overrides are used.

## Reproducible QA

Overlap test points are derived from actual region intersections. Areas use
EPSG:2264 square feet and acres. The report distinguishes full parent-region
overlaps from retained-cell overlaps, which can differ at discarded edge pieces.
Outside and single-region test points are also derived from source bounds and
geometry differences. Boundary tests use actual exterior vertices.

```sh
python3 -B -m unittest discover -s tests -v
python3 -B scripts/qa_region_resolution.py
```

The integration test exercises the default habitat lookup paths for all three
real overlaps and the canonical neutral area. Missing canonical data fails the
test instead of skipping it. Synthetic tests separately cover unresolved parent
overlaps and ambiguous shared zone boundaries.

`output/region_resolution_qa.json` records each derived coordinate, full resolver
and zone-lookup results, overlap areas, and source SHA-256 hashes. Zone provenance
records repository paths, Git blob IDs, and the last content commit for the
canonical files. The QA runner verifies their bytes match committed repository
data. The CLI and QA runner hash all files under `data/processed`,
`data/raw`, and `data/config` before and after, failing on any byte change,
addition, or deletion. The tests exercise the mutation guard with temporary data.
No spawn behavior or changes to analytical geography are part of this layer.
