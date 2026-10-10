# Modemon GO POI Data

This pipeline extracts neutral OpenStreetMap points of interest inside the eight canonical Modemon GO gameplay regions.

OSM source categories are not Modemon gameplay habitats. Habitat labels are derived separately in the next stage.

## POI Definition

A POI is a named or categorically meaningful OSM feature representing a place a player could plausibly encounter or associate with human activity. The pipeline targets commercial, civic, institutional, healthcare, entertainment, educational, recreation, transit, tourism, office, government, historic, and craft features.

## Included Tag Families

The Overpass query requests objects with at least one of: `amenity`, `shop`, `office`, `healthcare`, `tourism`, `leisure`, `public_transport`, `railway`, `historic`, `government`, or `craft`.

## Exclusion Logic

Filtering is centralized in `is_meaningful_candidate()`. Named POIs are generally retained unless they are low-value infrastructure. Public transport platforms and stop positions are excluded; transit stations, stop areas, and bus stations remain eligible. Railway track/infrastructure values such as rail, abandoned, disused, signal, signal_box, switch, level_crossing, and miniature are excluded even when named; railway stations and halts remain eligible. Unnamed sports pitches are excluded, while named pitches, stadiums, sports centres, and named recreation facilities remain eligible. Other unnamed features are retained only when their source category is inherently meaningful, such as hospitals, pharmacies, schools, libraries, museums, and similar places. Low-value objects such as benches, trash cans, post boxes, toilets, recycling points, generic parking, street lamps, utility-like railway features, and unnamed line features are excluded.

## Spatial Assignment

Each candidate keeps its original OSM geometry when practical. A representative point is calculated for deterministic indexing. A candidate is assigned to a region only when that representative point is covered by the canonical region polygon. This avoids duplicating one POI across neighboring gameplay containers.

## Primary Category Precedence

`primary_osm_key` and `primary_osm_value` are neutral source-data categories, not habitats. Precedence is: healthcare, amenity, shop, office, tourism, leisure, public_transport, railway, government, historic, craft.

## Deduplication

POIs are never merged solely because names match. Primary identity is deterministic by region plus OSM type and ID: `REGION_osm_TYPE_ID`. `possible_duplicate_pois.csv` reports likely real-world duplicates for manual review only. Duplicate candidates are restricted to the same `region_id`; normalized names must match; and at least one condition must hold: representative points are within 150 feet, exact non-empty normalized addresses match, or points are within 300 feet and share brand or operator. Same brand or same operator alone is not sufficient.

## Outputs

- `data/processed/pois.geojson`: retained POIs with source geometry
- `data/processed/pois.csv`: flat inspection table with representative coordinates and raw tags as JSON text
- `data/processed/poi_counts_by_region.csv`: count summary by gameplay region
- `data/processed/poi_counts_by_osm_category.csv`: source category counts by region
- `data/processed/possible_duplicate_pois.csv`: likely duplicate candidates, not merged
- `data/processed/excluded_poi_candidates.csv`: excluded candidates only
- `data/processed/poi_candidate_audit.csv`: full retained/excluded candidate audit trail
- `data/processed/poi_ingestion_report.csv`: QA report by region
- `output/poi_validation_raleigh.png` and `output/poi_validation_durham.png`: region boundaries and retained representative points

## Source And Attribution

Data source: OpenStreetMap via Overpass API. OpenStreetMap data is available under the Open Database License (ODbL) and requires OpenStreetMap attribution. Raw Overpass responses are cached by region under `data/raw/pois/`.

## Known Limitations

OpenStreetMap completeness varies by area. Some real-world places may be missing, duplicated, represented only as buildings, or represented by both a point and polygon. This stage intentionally avoids habitat labeling, rarity assignment, spawn logic, and Modemon model-family decisions.
