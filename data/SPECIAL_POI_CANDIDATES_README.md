# Special POI Candidates (Step 8A)

Special spawn candidates indicate educational and gameplay potential. They do not assert that a particular organization uses a specific AI system.

A POI coordinate associates an encounter with a place; it does not instruct a player to enter a building, restricted area, or exact mapped coordinate.

## Purpose and Scope

Ordinary encounters may eventually be associated with ordinary POIs. A small
curated subset may later become special destinations associated with a better
rarity pool, offering specialized or distinctive educational context. This stage
only scores candidates and prepares a human-review shortlist. It assigns no final
locations, rarity, models, probabilities, timing, or active spawns. Approximately
one to three final locations per region will be chosen manually in a later step.

Run from the repository root:

```sh
python3 -B scripts/score_special_poi_candidates.py
python3 -B -m unittest discover -s tests -v
```

Inputs are the canonical labeled POI GeoJSON and CSV (927 rows), regions,
habitat zones, and neutral areas. IDs and existing primary/secondary habitat
assignments are preserved. The scorer checks CSV/GeoJSON consistency and hashes
all pre-existing canonical datasets and configuration before/after execution.
Canonical source bytes never change. Legacy dictionary text in the labeled CSV
is read with `ast.literal_eval`, alongside JSON and native dictionary inputs;
new audit outputs serialize full original tags as JSON.

## Four Dimensions

`data/config/special_poi_candidate_config.yaml` defines the v1 rules, rule IDs,
points, thresholds, exclusions, and selection parameters. The four dimension
bounds are 35 + 25 + 20 + 20 = 100. Total score is the sum of dimension scores;
it is an educational/gameplay ranking, not a probability or an access guarantee.

### Specialization (0-35)

Use the strongest matching source-tag rule; category points do not stack. Rule
ties use the stable rule ID. Every matched specialization rule remains in
`scoring_rationale`. Examples: research/hospitals 35, museums 33, scientific or
engineering function 32, universities/courts/incubators 30, transit facilities
and libraries 28, stadiums 27, cultural venues 26, general care 25, civic and
school functions 24, structured recreation/events 23, history/finance/markets
21, explicit production/community functions 20, parks/gardens 18, local stop
areas 12, small features 10, ordinary businesses 8, generic fallback 5.

Speciality tags can distinguish clinical contexts without making them more
accessible. `public_transport=stop_area` alone does not establish a major transit
facility: explicit station/bus-station tags or a stop area also tagged
`railway=facility` support the higher score. Neither fame nor geometry size
determines specialization. Full OSM tags are used.

### Habitat Distinctiveness (0-25)

Use actual POI and zone statistics within the POI's original parent region:

```text
10 * (1 - primary-habitat POI count / all regional POIs)
+ 10 * (1 - primary-habitat zone area / classified regional zone area)
+ 5 * (1 - secondary-habitat primary-POI frequency), if secondary exists
```

Missing or invalid primary habitats receive zero primary rarity components.
Missing zone context receives zero zone rarity points and a review flag. Absence
of a primary zone for a valid habitat means area share zero, rather than missing
context. Thus Finance POIs can receive ecological variety credit even though no
Finance primary zone exists. Neutral area is excluded from the classified zone
denominator. Projected EPSG:2264 zone geometry supplies area. Original parent IDs
are retained in inherited region overlaps; this scorer does not reroute or relabel
POIs. Covering zone/neutral IDs at each representative point are recorded.

### Discovery Value (0-20)

Components are explicit: meaningful name 4; a normalized name unique within
the retained dataset 3 (otherwise 1); non-generic source function 6 when
specialization is at least 18; POI Wikidata 2 and Wikipedia 2; primary/secondary
pair context up to 3 using one minus that pair's regional POI frequency. A
tagged brand incurs a 2-point penalty; results are bounded to 0-20.

Uniqueness refers only to this dataset. Missing brand metadata never establishes
independent/local ownership, and repeated operator names do not establish a
chain. No popularity, visitor counts, obscurity, or actual AI deployment are
inferred. Generic placeholders and numbered court/field labels fail the
meaningful-name gate. All matching and generic-name patterns are documented in
configuration rather than inferred from subjective place-name interpretation.

### Accessibility Confidence (0-20)

First matching configured rule wins. Explicit private/no/staff-only and
non-pedestrian access, secure detention/military contexts, childcare/K-12 signals,
and emergency-only features are `restricted_or_inappropriate` with zero access
points. An `amenity=school` of unverified level receives a conservative
safeguarding hold; this is not a claim that every such record is a K-12 school.
Adult or university-school exceptions require human verification, not guesses
from names. These records remain auditable and can enter the manual-review queue.

Conditional access, age-limited venues, healthcare, public-safety operations,
offices/research, university anchors, and courts generally receive
`public_context_access_uncertain`. Sensitive facility safeguards precede positive
public-access tags. Hospital `emergency=yes` alone does not mean emergency-only
access and does not exclude a hospital campus. Universities are not automatically
excluded. Clinical tags alone cannot prove a safe public approach.

Explicit public/permissive access supports 20 points; customers access 16.
Public-facing cultural/outdoor/transit/library function supports 18, ticketed
event/recreation context 14, and ordinary public-facing commerce 16. Office or
unknown access receives 6, healthcare/age-limited context 7, courts 10, and
university anchors 12. These are confidence proxies. No pedestrian routing,
coordinate snapping, opening-hours verification, or safe-entrance determination
is attempted.

## Eligibility, Shortlists, and Review

`candidate_eligible` requires a meaningful name, valid source geometry and
representative coordinates covered by a valid parent, a canonical primary
habitat, no habitat-classification review hold, and no restricted/inappropriate
status. Eligibility is separate from the stronger shortlist score threshold.
All 927 POIs remain in the audit, including exclusions and low scores. Exclusion
reason totals can exceed excluded POIs because a record can fail several gates.

The shortlist quality gate is raw score at least 55 and specialization at least
18. From this pool, choose at most eight per region, with at most two identical
`primary_osm_key/value` subtypes. Already selected venue names or nonempty
Wikidata identities are not repeated on the shortlist. This only limits review
redundancy: source objects are not merged or deleted.

Selection priority is raw score plus a 3-point bonus for a primary habitat not
yet represented in the region's shortlist. Ties use raw score then `poi_id`.
This bonus never changes the stored raw score or admits candidates below the
quality gate.

Prefer at least 250 m separation using representative points in EPSG:2264 with
its US survey foot conversion. Consider only spacing-compliant candidates first.
If none remain, a small region (under 100 acres or bounding diagonal at most
1,000 m) may relax to 100 m without changing quality/category gates. The process
stops when no suitable choice remains; it does not force eight. Nearest selected
distance is recomputed against the final set, so both members of a close pair
are flagged. Singletons have a null distance. Region rank is a review rank, never
a final special-location ID.

The audit additionally records final-set spacing conflicts and category/venue
limits for strong unshortlisted candidates. These explain current-set constraints
without asserting one constraint was the sole historical cause of exclusion.

Uncertain-access candidates may appear on the shortlist with explicit access
status and review rationale. They are not access endorsements. Potentially
interesting candidates (score at least 50 or specialization at least 20) with
uncertain/restricted access, habitat review status, source `fixme`, ambiguous
function, or missing zone context also appear in the manual-review queue.
Habitat-review holds can never enter the primary shortlist. Restricted candidates
can never enter it regardless of score. The report separately lists every
restricted record scoring at least 55.

## Outputs and QA

- `data/processed/special_poi_candidate_scores.csv`: all evaluated POIs, scores,
  original tags, eligibility/exclusions, review flags, regional context statistics,
  per-rule/component rationale, and shortlist audit reasons.
- `data/processed/special_poi_candidates_by_region.csv`: review ranks, score and
  habitat fields, access status, nearest selected distance, spacing/category
  metadata, and recommendation rationale.
- `data/processed/special_poi_candidate_review_queue.csv`: potentially interesting
  candidates that require human judgment, including excluded sensitive records.
- `data/processed/special_poi_candidate_summary.csv`: regional counts, thresholds,
  habitat distributions, score means, spacing conflicts, and weak coverage flags
  (fewer than three shortlisted candidates).
- `output/special_poi_candidates_raleigh.png` and
  `output/special_poi_candidates_durham.png`: region/zone context, candidate access
  colors, and review rank labels. Numbers correspond to the regional shortlist.
- `output/special_poi_candidate_report.md`: full shortlist, reasons, exclusions,
  weak regions, clustering, and high-scoring restricted candidates.
- `output/special_poi_candidate_provenance.json`: configuration version and source
  hashes proving canonical inputs were unchanged.

OSM data is attributed to OpenStreetMap contributors under ODbL. Completeness and
access tagging vary, and names/functions may be stale or duplicated. A rare
habitat may reflect incomplete mapping rather than real-world rarity. Clusters
and high-scoring clinical/office sites need human judgment. These shortlists are
only material for the team's later manual selection.
