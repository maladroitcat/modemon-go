# Modemon GO Habitat Labels

This stage translates neutral OpenStreetMap POIs into auditable Modemon GO gameplay habitats. It does not create habitat polygons, spawn pools, rarity, model-family assignments, spawn probabilities, or individual Modemon.

Habitat labels describe the type of real-world environment represented by a POI. They do not assert that a specific organization uses a particular AI system.

## Taxonomy

The canonical habitat taxonomy has exactly nine values:

- Healthcare
- Finance
- Retail
- Food & Hospitality
- Education & Research
- Transportation
- Civic & Government
- Entertainment
- Office & Business

Each POI can receive one `habitat_primary` and, when useful, one `habitat_secondary`. The primary habitat describes what the place fundamentally is. The secondary habitat captures a genuinely useful alternate gameplay context, such as a pharmacy being Healthcare primary and Retail secondary.

## Rulebook

Rules live in `data/config/habitat_rules.yaml`. Each rule has a stable `rule_id`, tag conditions, priority, primary and optional secondary habitat, confidence, and notes. The Python script `scripts/label_habitats.py` evaluates the rules generically rather than burying the mapping in hard-coded if/else blocks.

Rule priority is deterministic. Lower numeric priority wins. The documented strategy is:

1. highly specific overrides
2. healthcare
3. finance
4. transportation
5. civic/government
6. education/research
7. food/hospitality
8. entertainment
9. office/business
10. generic `shop=*` Retail fallback
11. review/unclassified fallback

Specific rules intentionally override generic rules. For example, `amenity=pharmacy` is Healthcare primary and Retail secondary even if a POI also has shop-like tags.

## Confidence

- `high`: direct, unambiguous OSM source tag.
- `medium`: reasonable source-data interpretation or broad fallback.
- `low`: ambiguous or fallback classification; generally review-required.

`habitat_review_required=true` is used for unclassified POIs, low-confidence POIs, ambiguous review categories, and conflicting top-priority matches.

## Full OSM Tags

Labeling uses the full `raw_tags` dictionary where useful, not only `primary_osm_key` and `primary_osm_value`. The neutral primary OSM category is still retained for reporting and inspection, but habitat rules can inspect any original OSM tag.

## Campus Context

Campus location alone does not imply Education & Research. A restaurant, cafe, clinic, bank, shop, or theater inside Duke or NC State remains classified by its own OSM tags. Education & Research is assigned only when the POI itself has supporting education, university, school, training, research, library, public-bookcase, or information tags.

Healthcare POIs may receive Education & Research as a secondary habitat only when the POI's own tags indicate academic or research context.

## Unclassified Behavior

The labeler does not require 100% classification. Ambiguous categories such as `amenity=place_of_worship`, vague historic tags, `amenity=fountain`, `amenity=social_facility`, `craft=yes`, and unclear lodging/apartment records are left unclassified or review-required unless another explicit rule applies.

This is intentional. A review queue is preferable to forcing a misleading gameplay label.

## Outputs

- `data/processed/pois_labeled.csv`: source POI table plus habitat fields.
- `data/processed/pois_labeled.geojson`: source POI geometry plus habitat fields.
- `data/processed/habitat_counts.csv`: primary and secondary counts by habitat.
- `data/processed/habitat_counts_by_region.csv`: primary and secondary counts by region and habitat.
- `data/processed/unclassified_pois.csv`: POIs with no primary habitat.
- `data/processed/habitat_review_queue.csv`: unclassified, low-confidence, ambiguous, or conflicting POIs.
- `data/processed/habitat_labeling_report.csv`: one-row QA summary.
- `output/habitat_validation_raleigh.png`: Raleigh habitat QA map.
- `output/habitat_validation_durham.png`: Durham habitat QA map.

## Known Limitations

OpenStreetMap tags vary in detail and consistency. Some POIs may be missing useful tags, duplicated, overly generic, or tagged in ways that require manual review. These labels are gameplay/educational categories for Modemon GO, not legal classifications, official institutional designations, or claims about AI deployment at any real-world organization.
