# Modemon GO Habitat Cell Scores

This stage converts labeled POIs into a reproducible, QA-oriented habitat score grid. It does not dissolve cells into habitat zones and does not create spawn pools, rarity, model-family assignments, spawn probabilities, or Modemon.

## Inputs

- `data/processed/pois_labeled.geojson`
- `data/processed/regions.geojson`
- `data/config/habitat_spatial_config.yaml`

Only the eight canonical Modemon GO gameplay regions are processed.

## Spatial Model

Grid generation and distance calculations use `EPSG:2264` North Carolina State Plane. Output GeoJSON is transformed back to `EPSG:4326`.

The analysis grid uses approximately 100 meter square cells. Because EPSG:2264 uses feet, the configured cell size is converted using `3.280839895` feet per meter. Complete square cells are generated in projected space, then intersected with each canonical region. Final cell geometries never extend beyond their assigned region.

Each output cell stores:

- full square-cell area
- clipped in-region area
- retained area percentage
- tiny edge-fragment flag
- all nine habitat scores
- assigned primary and secondary cell habitats
- confidence
- top contributing POIs by habitat for QA

## Scoring

Each cell combines:

- regional prior from `habitat_spatial_config.yaml`
- primary-habitat POI influence
- secondary-habitat POI influence
- repeated-feature dampening

Regional priors are gentle baseline scores, not hard overrides. Downtown Raleigh and Downtown Durham have no regional prior. Duke, NC State Central, and NC State Centennial receive Education & Research priors. Dorothea Dix Park and Pullen Park receive Entertainment priors. WakeMed Raleigh Campus receives a Healthcare prior.

POI influence uses:

```text
contribution = weight * exp(-distance / radius)
```

Distance is measured from each POI representative point to each cell centroid in EPSG:2264 feet. Tier weights and radii are configured for anchor, standard, and micro POIs. Secondary habitat contributions use the configured secondary multiplier.

POIs only contribute to a cell when the cell centroid is within the configured cutoff distance for that POI's tier:

```text
distance <= radius * distance_cutoff_multiplier
```

In the v1 baseline, `distance_cutoff_multiplier` is `3.0`, so anchor, standard, and micro POIs contribute within approximately 750 m, 375 m, and 180 m respectively.

Repeated-feature dampening uses explicit configured multipliers. Within each cell, habitat, and OSM source-category group, contributions are sorted strongest first and multiplied by rank-specific values: rank 1 = `1.0`, rank 2 = `0.5`, rank 3 = `0.25`, and rank 4+ = `0.1`. This reduces the effect of many repeated nearby POIs with the same source category without removing them.

Cell confidence uses the top-to-second score ratio. High confidence means the top score is at least 1.75x the second score, medium means at least 1.25x but less than 1.75x, and low means less than 1.25x. If no habitat reaches the configured minimum primary score, the cell remains unclassified and review-required.

## Outputs

- `data/processed/habitat_cells.geojson`: canonical cell score layer in EPSG:4326.
- `data/processed/habitat_cells.csv`: flat inspection table with cell geometry as WKT.
- `data/processed/habitat_cell_contributions.csv`: one row per actual POI-to-cell contribution inside the cutoff, including raw contribution, secondary multiplier, repeated-subtype rank, dampening multiplier, and final contribution.
- `data/processed/habitat_cell_counts_by_region.csv`: cell counts by region, primary habitat, and confidence.
- `data/processed/habitat_cell_report.csv`: QA summary by region.
- `data/processed/habitat_cell_summary_by_region.csv`: compact per-region summary with classified/unclassified counts, habitat counts, confidence counts, and mean contributing POIs.
- `data/processed/habitat_cell_summary_global.csv`: global summary.
- `output/habitat_cells_raleigh.png`: Raleigh cell QA map.
- `output/habitat_cells_durham.png`: Durham cell QA map.
- `output/habitat_cells_raleigh_confidence.png`: Raleigh confidence QA map.
- `output/habitat_cells_durham_confidence.png`: Durham confidence QA map.

## Interpretation

The cell scoring layer is a transparent debug surface for habitat QA. A cell's assigned primary habitat is the highest scoring habitat after priors and POI influence. Secondary habitat is assigned only when the second score is strong enough relative to the primary score.

These cell labels describe gameplay/educational environmental context. They do not assert that a specific organization uses a particular AI system.
