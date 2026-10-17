# Modemon GO Habitat Zones (Step 7B)

Habitat zones are gameplay abstractions derived from scored environmental context. They do not assert that a specific organization deploys a particular AI system.

## Source and Reproduction

The canonical analytical inputs are `data/processed/habitat_cells.geojson`
and `data/processed/regions.geojson`. The baseline is 1,998 cells: 1,993
classified and five unclassified. Step 7B never rescores, relabels, smooths,
simplifies, or merges small zones. Step 7A cells remain the source of truth.

Run from the repository root:

```sh
python3 -B scripts/build_habitat_zones.py
python3 -B -m unittest discover -s tests -v
```

The default run fails if any meaningful zone overlap is found. The canonical
regions and their retained cells currently overlap across Downtown Durham/Duke,
Dix/Centennial, and Central/Pullen. These source overlaps are recorded in
`habitat_zone_overlap_diagnostics.csv`; dissolving exact cells cannot remove them.
The CLI supports `--allow-inherited-region-overlaps` for an explicitly approved
preservation of these source overlaps. That option still rejects within-region
overlaps and any overlap introduced by the dissolve. Per-region coverage remains
fully accounted. No geography is reassigned to resolve cross-region overlaps.

## Adjacency and Components

All topology and area calculations use EPSG:2264 (US survey feet). A spatial
index finds candidate cell pairs within each region and primary habitat. A
rook edge requires more than 0.01 feet of shared boundary; corner-only contacts
never connect. For coordinate roundoff, the predicate may snap a boundary copy
within 0.000001 feet (about 0.3 micrometers). This only affects the predicate:
unions always use the exact, untouched source cell geometry. No buffers, hulls,
nearest-neighbor connections, or morphological operations are used.

Deterministic graph traversal finds connected components. Each component is
dissolved with `unary_union`, independently of other primary habitats and regions.
IDs have the form `region_habitat_slug_hash`, where the hash is the first 12 hex
characters of SHA-256 over the JSON list of sorted source cell IDs.

A source cell can already be a MultiPolygon. To preserve exactly one zone
membership per cell, such a cell remains an atomic graph node. Its disconnected
fragments stay disconnected in the exact union. Multipart zone geometry is
explicitly flagged as suspicious and sent for review. No component is connected
through another habitat or across a canonical region boundary.

## Aggregation

Weights are the areas of the canonical clipped cell geometries measured in
EPSG:2264. This uses the delivered geometry rather than the rounded Step 7A
`clipped_area_sqft` field, which was recorded before its final WGS84 clipping.
Stored area differences beyond the configured numerical tolerance are flagged
as inconsistent source metadata. Both values can be audited against the inputs.

Top score, second score, and ratio means are area-weighted. Undefined ratios
(no second score or an unclassified cell) are omitted from the ratio mean;
`finite_ratio_area_pct` records its denominator coverage. Null is never treated
as zero or invented infinity.

Secondary distributions are percentages of the whole zone's classified clipped
area. Cells without a secondary habitat remain in the denominator. Secondary
shares may therefore sum to less than 100%. The strongest secondary is populated
only at a share of at least 30%; ties use alphabetical habitat order. Secondary
habitats never influence primary topology.

Confidence is retained as High/Medium/Low cell counts and area-weighted shares,
without assigning a single confidence label to the whole zone. Review is required
for more than 30% Low area, micro-zones, multipart/suspicious geometry, or
inconsistent metadata. A micro-zone has one source cell or less than two acres.
Small zones are retained as-is.

## Neutral Areas and Coverage

Unclassified cells form their own rook-connected components within each region
in `habitat_unclassified_areas.geojson`. They receive no habitat. The membership
CSV includes all cells, with `classified=false` for neutral components, so every
retained cell is auditable exactly once.

Coverage checks compare classified zone plus neutral area to retained cell area
per region, not the full parent region. The absolute area tolerance is 0.01 square
feet, with relative tolerance of 1e-8 for large geometry comparisons. Meaningful
pairwise overlap uses 0.01 square feet. The coverage CSV also reports symmetric
difference against exact source unions.

## Outputs

- `data/processed/habitat_zones.geojson` and `.csv`: zones and aggregate metadata;
  GeoJSON and CSV WKT geometry use EPSG:4326.
- `data/processed/habitat_unclassified_areas.geojson`: neutral components.
- `data/processed/habitat_zone_cell_membership.csv`: exact cell/zone membership,
  original confidence/secondary labels, and clipped area.
- `data/processed/habitat_zone_summary_by_region.csv` and
  `habitat_zone_summary_global.csv`: zone counts, areas, and review statistics.
- `data/processed/habitat_zone_coverage.csv`: per-region coverage accounting.
- `data/processed/habitat_zone_overlap_diagnostics.csv`: source/new overlap audit,
  written before validation so strict failures can be inspected.
- `output/habitat_zones_{raleigh,durham}.png`: primary habitat and neutral maps.
- `output/habitat_zones_{raleigh,durham}_review.png`: review and micro-zone maps.
- `output/habitat_zone_qa_report.md`: complete review report, ecology breakdowns,
  low-confidence zones, extrema, coverage, maps, and canonical input hashes.

## Validation and Limitations

The pipeline fails for missing inputs, baseline count or region drift, invalid
source or output geometry, duplicate IDs, incomplete or repeated membership,
mixed region/habitat components, invalid habitat values, meaningful overlap,
outside-region geometry, material area differences, or missing neutral coverage.
It verifies input hashes after execution and checks exact union agreement.

Floating-point reprojection can leave tiny cracks or multipart union artifacts;
these are preserved and reviewed rather than silently repaired. Zones preserve
the original cell resolution and do not fill discarded Step 7A edge fragments.
Confidence and secondary signals describe the input ecology rather than a new
classification. This step creates no spawn or model-family assignments.
