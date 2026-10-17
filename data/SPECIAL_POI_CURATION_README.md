# Special POI human curation (Steps 8B/8C)

## Separate layers

Step 8A is data-driven candidate discovery: 927 evaluated POIs, 824 eligible
candidates, a 42-row regional shortlist, and a 103-row broader review queue.
Step 8B is human current-world verification. Step 8C is human gameplay selection.
This overlay records the project team's decisions dated **2026-10-17**; the
script does not independently browse, verify, score, or rerank places.

The authoritative file is `config/special_poi_curation.yaml`. Decisions are keyed
by existing `poi_id`. Initial IDs were resolved from exact `region_id` and
candidate `name`, with exactly one match required. Every run repeats that identity
check. All 42 shortlisted candidates must have exactly one decision; candidates
outside that shortlist cannot enter this overlay. YAML duplicate keys fail.
Defaults supply common date and null fields to each decision. There are no scores
in the YAML. The additional JSON source-list field retains the museum research
article and Hunt bookBot link alongside the primary verification source URL.
Absent evidence URLs remain null, not invented.

## Reproduction and audit

From the repository root:

```sh
python3 -B scripts/apply_special_poi_curation.py
python3 -B -m unittest discover -s tests -v
```

The script joins decisions onto `processed/special_poi_candidates_by_region.csv`
and preserves **every original field string**, including original name, score,
candidate rank, rationale, access assessment, habitat labels, and coordinates.
Step 8A access flags and human suitability judgments remain separate fields;
neither overwrites the other. A stale source assessment is auditable rather than
retroactively rewritten. Output order is region, primary/alternate/deferred/
not-selected/rejected, human rank (where applicable), then original candidate rank.
No algorithm determines which destinations win.

Every pre-existing file under `data/` and `output/`, other than the ten explicit
curation output paths, plus the Step 8A scoring script, is hashed before and after
execution. This includes canonical POIs, regions, cells, zones, classifications,
Step 8A scores/review/summary/maps, and the curation config. A change fails loudly.
The provenance JSON records the SHA-256 inventory. Unit tests also verify all
curation output bytes, including maps, are stable across repeated runs.

## Decisions and outputs

There are **17 primaries**, **12 alternates**, **1 deferred**, **2 not selected**,
and **10 rejected** candidates. Each region may have 0-3 primaries. Primary and
alternate ranks are unique, contiguous, and start at one within each region.

- `processed/special_poi_curation.csv`: all 42 candidates and all human fields.
- `processed/special_poi_primary.csv` / `.geojson`: 17 approved destinations.
- `processed/special_poi_alternates.csv` / `.geojson`: 12 approved fallbacks only.
- `processed/special_poi_curation_summary.csv`: eight regions and a total row;
  includes null/unassessed suitability so counts reconcile.
- `../output/special_poi_curation_{raleigh,durham}.png`: boundaries and light zone
  context; green stars are suitable primaries, orange triangles conditional
  primaries, blue circles alternates. P/A labels refer to human ranks within the
  labeled region; the name key includes display overrides.
- `../output/special_poi_curation_report.md`: full selection, anomaly, sensitivity,
  and conditional-primary audit.
- `../output/special_poi_curation_provenance.json`: protected-input hashes.

GeoJSON uses WGS84 representative candidate coordinates unchanged from Step 8A,
not source polygon centroids recalculated here. Original CSV fields remain text
in GeoJSON properties, while human ranks are integers and missing human fields
are JSON null (empty CSV cells). Display logic may prefer `verified_name` when
non-null, otherwise `name`; canonical names never change.

`primary` means an approved human-curated destination, **not a currently active
spawn**. `alternate` is an approved substitution. `deferred` awaits later review;
`not_selected` is viable but not chosen; `rejected` is unsuitable under current
evidence. Sensitive/not-recommended, closed, or unknown candidates cannot be
primary or alternate. Conditional primaries require a verification note and
selection rationale. Closed or stale identities may have null suitability.

## Why human curation stays separate

OSM names and organizations can be stale; organizations close or move. Temporary
work can affect access. Public-facing does not necessarily mean appropriate for
unrelated game traffic, and educational relevance does not establish suitability.
None of these findings silently mutates the source GIS/habitat data:

- Shodor ceased operations June 30, 2024: rejected as closed.
- Museum of Durham History replaces the stale display name The History Hub
  Museum only in `verified_name`; no relocation of its coordinate is implied.
- Durham Station is the GoDurham **bus** center at 515 W. Pettigrew Street, not
  Amtrak. Active but renovation-impacted in October 2026: conditional primary.
- Lilly Library is temporarily unavailable for renovation until Spring 2027;
  temporary operations were disrupted in September 2026: deferred, not deleted.
- RUMAH is active but moving in late 2026, with a sensitive mutual-aid/resource
  context: rejected as a special destination, not removed as a contextual POI.
- WakeMed is an excellent Healthcare/AI environment but an inappropriate
  deliberate special-gameplay destination because of acute-care, emergency,
  pediatric, patient, and clinical contexts.

## Educational and access boundaries

> Special locations support plausible or educational AI/ML contexts. Selection
> does not assert that a specific model is deployed at that organization unless
> independently verified.

Institution-level evidence is different from specific model deployment at the
player's exact location. The Natural Sciences Museum's documented AI specimen
transcription work and the Friday Institute's AI-in-education activity may enrich
educational content, but are not evidence of a particular model running at a
gameplay coordinate. Hunt Library's publicly viewable bookBot is an educational
technology context, not a model-family assignment.

> A POI coordinate associates an encounter with a place; it does not instruct a
> player to enter a building, restricted area, or exact mapped coordinate.

Gipson Play Plaza associates gameplay with the broader public plaza, garden, and
common spaces, not individual children's play equipment. Do not encourage
approaching, occupying, or lingering around those structures. Published hours,
event access, seasonal conditions, and temporary work still apply. This overlay
does not route pedestrians, relocate/snap coordinates, or guarantee physical access.

## Zero-selection regions

**RAL-05 intentionally has zero primary special POIs.** WakeMed remains part of
ordinary Healthcare habitat/game ecology. A region must never receive an unsafe
or inappropriate special destination merely for numerical symmetry.

Human decisions are a dated snapshot and need future review. This branch creates
no Modemon, model-family pools, rarity probabilities, spawn timing, geofences,
encounter triggers, cooldowns, or active runtime state. Canonical OSM attribution
and ODbL provenance remain in the source POI documentation and preserved fields.
