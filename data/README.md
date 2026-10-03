# Modemon GO Region Data

Retrieval date: 2026-10-03T18:39:59Z

These GeoJSON files are Modemon GO gameplay containers. They are not represented as legal municipal, property, university, or medical-campus boundaries unless the underlying authoritative dataset explicitly defines them that way.

Top-level regions are broad physical gameplay containers. They are not intended to encode all meaningful neighborhoods, campus divisions, or Modémon habitats. Internal gameplay regions are derived separately.

## Outputs

- `processed/raleigh_regions.geojson`: Raleigh child regions
- `processed/durham_regions.geojson`: Durham child regions
- `processed/regions.geojson`: all 8 child regions
- `processed/city_game_areas.geojson`: Raleigh and Durham parent gameplay areas, derived by unary-unioning child polygons without filling gaps
- `processed/regions_summary.csv`: QA area calculations in EPSG:2264
- `output/region_validation_map.png`, `output/raleigh_validation.png`, `output/durham_validation.png`: visual QA maps

## Region Sources

### DUR-01 - Downtown Durham

- Represents: Downtown Durham gameplay container beneath Durham
- Source: City/County of Durham PublicServices/Planning Place Type
- Authority class: authoritative source
- Query/filter: `PlaceType = 'DT'`
- Retrieved: 2026-10-03T18:39:57Z
- Review required: no
- Notes: Dissolved Downtown Place Type polygons; not Bullpen social district.

### DUR-02 - Duke University

- Represents: Duke University gameplay container beneath Durham
- Source: OpenStreetMap
- Authority class: OSM fallback
- Query/filter: `Duke University, Durham, North Carolina`
- Retrieved: 2026-10-03T18:39:58Z
- Review required: yes
- Notes: Broad physical gameplay container. Internal Duke campus, healthcare, research, and other gameplay subregions will be derived later.

### RAL-01 - Downtown Raleigh

- Represents: Downtown Raleigh gameplay container beneath Raleigh
- Source: City of Raleigh Municipal_Service_Districts
- Authority class: authoritative source
- Query/filter: `Name = 'Downtown'`
- Retrieved: 2026-10-03T18:39:56Z
- Review required: no
- Notes: Downtown municipal service district, not police district or older downtown boundary.

### RAL-02 - Dorothea Dix Park

- Represents: Dorothea Dix Park gameplay container beneath Raleigh
- Source: City of Raleigh Developed_Parks
- Authority class: authoritative source
- Query/filter: `NAME contains 'Dix', selected NAME = 'Dix Park'`
- Retrieved: 2026-10-03T18:39:56Z
- Review required: no
- Notes: Dissolved all polygons for selected park name without convex hull or simplification.

### RAL-03A - NC State Central Campus

- Represents: NC State Central Campus gameplay container beneath Raleigh
- Source: NC State Facilities Campus Perimeters shapefile
- Authority class: authoritative source
- Query/filter: `Precinct_N = 'Central Campus'`
- Retrieved: 2026-10-03T18:39:57Z
- Review required: no
- Notes: Official NC State campus perimeter precinct record dissolved if multipart.

### RAL-03B - Pullen Park

- Represents: Pullen Park gameplay container beneath Raleigh
- Source: City of Raleigh Developed_Parks
- Authority class: authoritative source
- Query/filter: `NAME contains 'Pullen', selected NAME = 'Pullen'`
- Retrieved: 2026-10-03T18:39:56Z
- Review required: no
- Notes: Dissolved all polygons for selected park name without convex hull or simplification.

### RAL-04 - NC State Centennial Campus

- Represents: NC State Centennial Campus gameplay container beneath Raleigh
- Source: NC State Facilities Campus Perimeters shapefile
- Authority class: authoritative source
- Query/filter: `Precinct_N = 'Centennial Campus'`
- Retrieved: 2026-10-03T18:39:57Z
- Review required: no
- Notes: Official NC State campus perimeter precinct record dissolved if multipart.

### RAL-05 - WakeMed Raleigh Campus

- Represents: WakeMed Raleigh Campus gameplay container beneath Raleigh
- Source: OpenStreetMap polygon fallback
- Authority class: OSM fallback
- Query/filter: `WakeMed Raleigh Campus, Raleigh, North Carolina`
- Retrieved: 2026-10-03T18:39:57Z
- Review required: yes
- Notes: OSM fallback; no authoritative public campus-perimeter layer identified. Nominatim returned Polygon/MultiPolygon.

## Licensing And Attribution

- City of Raleigh, City/County of Durham, and NC State source data should be attributed according to their public GIS/open-data terms.
- OpenStreetMap fallback geometries require OpenStreetMap attribution and are subject to the Open Database License (ODbL).
- This pipeline preserves raw downloaded responses under `data/raw/` for auditability.
