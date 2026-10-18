# Approved Signature encounters (issue 21)

This is a gameplay association overlay, not new research or geographic data.
The owner approved all twelve mappings in
<https://github.com/maladroitcat/modemon-go/issues/21>.
Canonical Modedex facts, source URLs, POI identities, regions, zones and habitat
assignments are read-only. No creature artwork is approved; placeholders remain.

## Explicit crosswalk

| Canonical species ID | Creature | Curated primary POI ID | Real placement |
| --- | --- | --- | --- |
| extractor_history | Archivole | RAL-04_osm_node_2470661698 | Friday Institute sidewalk |
| extractor_specimen | Specimunk | RAL-01_osm_way_197842115 | Bicentennial Mall pedestrian space |
| generator_catalog | Catalogar | RAL-04_osm_way_177166351 | Hunt Library outdoor plaza |
| generator_classroom_chatbot | Lecturlynx | RAL-04_osm_node_2470661698 | Friday Institute sidewalk |
| generator_lesson_planner | Planthera | RAL-04_osm_node_2470661698 | Friday Institute sidewalk |
| recommender_adaptive_learning | Mentamorph | RAL-04_osm_node_2470661698 | Friday Institute sidewalk |
| recommender_ai_curator | Muselect | DUR-02_osm_way_30424777 | Nasher outdoor sidewalk |
| recommender_research | Referaptor | RAL-04_osm_way_177166351 | Hunt Library outdoor plaza |
| retriever_semantic_search | Semantiff | DUR-02_osm_way_391474817 | Perkins outdoor walkway |
| scheduler_ride_booking | Cabcrab | DUR-01_osm_node_5844548329 | Withheld individually; Demo only |
| scheduler_traffic_signal | Signalquid | RAL-01_osm_node_13659913892 | West Street sidewalk near RUS BUS |
| scheduler_transit_flow | Flowfin | DUR-01_osm_node_5844548329 | Withheld individually; Demo only |

## Safety evidence and limits

`config/signature_encounters.yaml` is the versioned approval/safety overlay.
For each anchor it records an official visitor/status URL, a review note, an
association instruction, and either a selected OSM pedestrian way/node pair or
an explicit withholding status. No manually invented coordinates or automatic
nearest-path snapping is used. `config/signature_access_osm.json` preserves the
Overpass query, full response and upstream snapshot timestamp (OSM/ODbL).
The runtime builder derives coordinates directly from that selected node.

Validation rejects non-primary/ineligible destinations, unknown/missing species,
incomplete responses, restricted ways, road crossings, indoor/tunnel/golf ways,
points in building footprints, points outside their resolved canonical parent,
and offsets exceeding the configured 200m association limit. The runtime keeps
the canonical POI unchanged and applies the outdoor placement only to the
Signature encounter. Its distance display and interaction gate use that approach,
not the building centroid. The real flow also requires an affirmative public-path
safety acknowledgement in addition to foreground GPS proximity.

This is **desk-based mapping/site evidence, not an in-field access inspection,
pedestrian routing, a legal access guarantee, or an obstruction detector**. The
75m interaction circle does not identify which side of a fence someone is on.
Signs, opening hours, closures and conditions on the ground always override a
marker. No entering buildings or standing on the exact mapped node is required.
The Friday placement is on the mapped Main Campus Drive sidewalk, not the
institute interior, adjacent K-12 school or private golf paths.

The [GoDurham renovation update](https://godurhamtransit.org/durham-station-renovations/)
reviewed October 18 describes ongoing construction, west-side concrete work and
north platform work. A suitable unaffected pedestrian game association spot was
not established. **Only Cabcrab and Flowfin real placements are withheld** pending
that review. No fallback to the station centroid or ordinary station encounter is
allowed. In Demo they use the canonical association coordinate, with a prominent
DEMO ONLY construction notice; this is not a safe real placement approval.

The [Hunt visitor page](https://www.lib.ncsu.edu/hunt/visit) announces an October 19,
2026 electrical-work closure. Its two mappings have that date blocked in both
modes. Museums and libraries have published visitor hours; these encounters are
outdoor associations, not an invitation to enter after hours. Re-review evidence
when conditions change. Refreshing OSM never automatically approves a new point:
`python3 -B scripts/fetch_signature_access.py` only updates the evidence snapshot;
review the selected IDs and rerun validation before release.

## Deterministic scarcity, shared anchors and density

The current version uses four-day blocks relative to 2026-10-18, in the existing
America/New_York daily rotation. Each anchor has one hash-selected eligible day
per block, so an appearance is not forced every day. Its sorted species list is
rotated by the block number plus a stable anchor offset. Friday's four species
cycle across four blocks; Hunt and Durham Station alternate across two blocks.
There is at most one Signature marker per anchor and no ordinary marker at that
anchor while its Signature slot is active. Escapes/captures never backfill a slot.

Eligible Signature slots are considered **before** ordinary candidates. The
existing pair-defined-disk density check, global across regions and rarities,
still caps every half-mile-radius circle at seven. It uses the actual encounter
positions and retains the existing one-metre projection guard. If future approved
Signature anchors themselves exceed the cap, stable daily hash order chooses
which slots fit; the cap is never raised.

Ordinary seed/data version, storage keys, quiz snapshots, existing captures and
escapes are preserved. Signature IDs contain schedule version, Eastern date,
stable anchor ID and species ID; updating descriptive text does not reset them.
The new priority layer can displace ordinary markers, but does not rewrite any
saved record. Existing in-progress records remain stored, including the exact
difficulty/question snapshots; a displaced ordinary marker may not be offered
in that day's new world. There is no new reroll or reset option.

## Demo and capture QA

Demo is opt-in and uses its own browser progress key. Both cities use the same
daily scheduling and density model; the two withheld Durham forms are explicitly
simulation-only. A **Demo rotation (simulated date)** selector previews today and
the next fifteen days. It does not change the real GPS date or erase any previous
attempt. Reload defaults the preview to today; reselecting a preview date resumes
its existing attempt. This is an educational testing sandbox, not real movement.

Novice has 3 questions (2 correct), Intermediate 5 (3 correct), Expert 7 (4 correct).
Selectors show question counts only. Every correct answer and all distractors
are grounded in the existing canonical fields. All 51 species support these
banks (153 banks, 765 questions in `quiz-audit.json`); real eligibility remains
separate from content availability. Difficulty and bank snapshots persist before
the first answer and lock on answering. Correct feedback stays green, wrong red,
with text and icon distinctions. A failed attempt escapes for its date.

Identity remains hidden behind anonymous rarity-colored Signature markers until
the encounter opens. Each detail identifies the documented real project/use case
and links to the exact canonical provenance source. Representative techniques
are not asserted deployed architectures. A station/library/campus anchor is not
proof the system runs at that coordinate. No research facts or sources are inferred.

## Reproduce

```sh
python3 -B scripts/build_web_runtime.py
python3 -B -m unittest discover -s tests -v
cd mobile
npm run check
npm run check:playable
npm run test:playable
node --experimental-strip-types web/scripts/validate-quizzes.ts --write
npm run test:e2e
npm run test:playable:e2e
npm run build:playable
```

Use Node >=22.13 (the project pins Node 24). Browser tests use Chromium and mobile
WebKit, not a physical iPhone. They cover all twelve scheduled forms in all three
modes, both city demos, real GPS/safety gating, anonymous pins, canonical links,
reload persistence, daily escape, separate progress and narrow/landscape layouts.
Unit tests also cover exact crosswalk, every shared-anchor cycle, scarcity,
priority, global density, invalid access evidence and unchanged source hashes.

No spawn pools, rarity probabilities beyond this explicitly requested calendar,
new artwork, native behavior changes or automatic merge are introduced here.
