# Reproducing the Modémon GO Artifact

Start with the [root setup and test commands](../README.md#how-to-run-and-reproduce).
All commands here run at the repository root with the Python 3.12 virtualenv
activated, unless a block explicitly changes directory. No local-only art,
private dataset, API secret, publisher login or old Git snapshot is required.

The original `data/README.md`, `MODEDEX_README.md` and
`HABITAT_ZONES_README.md` are byte-frozen by a pre-existing playtest integrity
fixture. This documentation-only task leaves them unchanged rather than editing
test code/fixtures. This guide supplies the current commands and supersedes their
old setup assumptions: no root import-reference YAML is required, and the
canonical zone build needs explicit inherited-overlap approval as shown below.

## Choose the Reproduction Level

1. **Play/run the release snapshot:** use the hosted app or `npm run play:web`
   from `mobile/`. Committed runtime JSON and optimized images are sufficient.
2. **Rebuild the same app:** validate/rebuild content, art and runtime overlays
   from committed sources below. No live OSM/GIS/source crawling is involved.
3. **Reproduce analytical stages:** run the existing pipelines on the committed
   source snapshots in a disposable checkout. Inspect differences rather than
   adopting new outputs automatically. Figures/float serialization can vary.
4. **Refresh research data:** a different operation requiring online services,
   attribution, rate limits and new human safety/content review. Today's services
   may not return the historical data. Never describe a refresh as byte-identical
   reproduction or run it as an undocumented application prerequisite.

## Required Committed Resources

| Layer | Source / artifact | Why it is needed |
| --- | --- | --- |
| Geography | `data/raw/`, `data/processed/regions.geojson` | Authoritative/OSM snapshots and eight gameplay containers |
| Neutral POIs | `data/processed/pois.{csv,geojson}` | 927 retained objects with OSM identities/tags and representative points |
| Habitats | `data/config/habitat_rules.yaml`, `habitat_spatial_config.yaml`; labeled POIs, cells, zones, neutral areas | Auditable functional labels and spatial context |
| Region ownership | `data/config/region_resolution.yaml` | Explicit cross-region overlap precedence |
| Human selection | Candidate tables plus `data/config/special_poi_curation.yaml` | 42 reviewed candidates, 17 approved destinations; not automatic safety certification |
| Modédex | `data/config/modedex.yaml`, `data/schema/modedex.schema.json` | Eight families, 51 species, stable IDs, task/data/limitation/XAI fields and Signature sources |
| Signature access | `mobile/web/config/signature_encounters.yaml` and committed OSM/agency evidence there | Twelve explicit species/anchor mappings, safe-approach checks and calendar |
| Learning | `data/config/modedex_learning_links.yaml`, `data/research/` approvals/evidence | Exact approved readings and owner authorization |
| Artwork | `assets/artwork_sources.json`, `assets/modemon/approved/originals/`, `assets/brand/originals/` | 51 transparent full-resolution masters and logo with source hashes |
| Browser runtime | `mobile/web/src/data/{runtime,art,learning}.json`, `mobile/web/public/art/` | Validated static app resources, already committed |

The manifest, not root-level name-matched PNGs, is the normal art source. Neither
untracked `assets/modemon/concepts/` nor a local `presentation/` directory is an
application dependency. `mobile/package-lock.json` pins npm resolution. Python
direct requirements are pinned; not every transitive dependency or system library
is locked. Wheel/platform/encoder differences must be reported, not silently
accepted as equivalent bytes.

## Deterministic Application Build

```sh
python -B scripts/build_modedex.py
python -B scripts/build_game_art.py
python -B scripts/build_web_runtime.py
python -B scripts/build_modedex_learning.py
git diff --exit-code -- data/processed/modedex.json mobile/web/src/data mobile/web/public/art
cd mobile
npm run build:playable
```

The diff check validates unchanged **tracked** runtime/content/art resources. The
art tests also validate expected IDs, master hashes, derivative inventory and
budgets. On the verified encoder stack, derivatives reproduced exactly. See
[artwork](../assets/ARTWORK_README.md): a changed WebP encoder may change bytes.
Do not commit regenerated images as part of a documentation change.

`build:playable` validates all 153 quiz banks and learning-overlay source hashes,
builds `mobile/web/dist/`, enforces payload budgets, and writes
`deployment-provenance.json` identifying the application commit and asset hashes.
Production JS hashes may differ with toolchain changes; provenance distinguishes
the application commit from a hosting packaging commit/version. Merely building
does not update the existing public site or require a hosting credential.

## Analytical Stage Order and QA

Keep canonical input snapshots unchanged when checking the browser. To evaluate
pipeline reproduction, use a **disposable checkout** first. From the root:

```sh
export MPLBACKEND=Agg
python -B scripts/label_habitats.py
python -B scripts/score_habitat_cells.py
python -B scripts/build_habitat_zones.py --allow-inherited-region-overlaps
python -B scripts/qa_region_resolution.py
python -B scripts/score_special_poi_candidates.py
python -B scripts/apply_special_poi_curation.py
```

These overwrite derived analytical outputs in that checkout. The input to
labeling is the committed 927-POI snapshot; raw re-ingestion is not needed. The
canonical cell baseline is **1,998** cells, **1,993** classified and **5** neutral.
The exact-cell dissolve yields **62** habitat zones, **18** micro-zones and **55**
review-required zones. All classified cells belong to exactly one zone; all five
neutral cells are represented in one RAL-01 area of about **6.010529 acres**.
Coverage differences are only floating-point residue; no new overlap is allowed.

The overlap flag is an **explicit provenance-preserving policy**, not a validation
bypass: retain inherited cross-region overlap, reject within-region overlap and
any newly introduced overlap. Omitting it intentionally fails on known source
overlaps. Runtime ownership is separate: Duke over Downtown Durham, Dix over
Centennial, Pullen over Central. See [zones](HABITAT_ZONES_README.md) and
[resolution](REGION_RESOLUTION_README.md). Never remove overlaps to force a pass.

Figures are visual QA, not authoritative boundaries. Reprojection/serialization,
fonts, plotting libraries and optional basemap availability can affect output
bytes. Content IDs, geometry/coverage tolerances and protected-input hashes are
the relevant acceptance checks; do not promise bit-identical maps everywhere.

| Inspect | Files relative to repository root |
| --- | --- |
| Region boundaries | `output/region_validation_map.png`, `output/raleigh_validation.png`, `output/durham_validation.png`; `data/processed/regions_summary.csv` |
| POI inclusion/filtering | `output/poi_validation_{raleigh,durham}.png`; `data/processed/poi_ingestion_report.csv`, `excluded_poi_candidates.csv`, `possible_duplicate_pois.csv` |
| Habitat labels | `output/habitat_validation_{raleigh,durham}.png`; `data/processed/habitat_review_queue.csv`, `unclassified_pois.csv` |
| Cell influence/confidence | `output/habitat_cells_{raleigh,durham}.png`, matching `_confidence.png`; `data/processed/habitat_cell_contributions.csv`, `habitat_cell_summary_by_region.csv` |
| Zone topology/review | `output/habitat_zones_{raleigh,durham}.png`, matching `_review.png`; `output/habitat_zone_qa_report.md`; `data/processed/habitat_zone_cell_membership.csv`, `habitat_zone_coverage.csv`, `habitat_zone_overlap_diagnostics.csv` |
| Parent overlap routing | `output/region_resolution_qa.json` |
| Candidate discovery vs decisions | `output/special_poi_candidates_{raleigh,durham}.png`, `output/special_poi_curation_{raleigh,durham}.png`, associated reports/provenance |
| Artwork | `output/artwork_mapping_report.json`, `output/artwork_contact_sheet.jpg` |
| Species/quiz/link coverage | `mobile/web/coverage.json`, `quiz-audit.json`, `src/data/learning.json` |

In brace patterns above, substitute `raleigh` or `durham`; these are file indexes,
not literal shell arguments. GeoJSON is EPSG:4326; area/distance analysis uses
EPSG:2264 with its feet units. Never calculate QA area in latitude/longitude.

## Live Source Retrieval Is Not Required to Run

[Region sources](README.md), [OSM POIs](POI_README.md), and
[Signature evidence](../mobile/web/SIGNATURE_ENCOUNTERS.md) document their queries,
filters, snapshots and review boundaries. `scripts/ingest_regions.py` retrieves
live city/university/OSM sources; it is not an offline rebuild command.
`scripts/ingest_pois.py` prefers per-region raw cache; `--refresh` bypasses it and
may change results or need network fallback. Signature evidence refresh likewise
does not approve a new location. Do not crawl publishers or call these services
as a prerequisite to launching/rebuilding the committed browser artifact.

If refreshing intentionally, follow the stage README and respect source service
terms, application identification and rate limits. Retain raw responses, record
dates, resolve ambiguities explicitly and rerun downstream validation/human
review. OSM completeness, named objects, municipal services, source URLs,
closures and public access can change. Human-curation and approved reading
decisions must never be overwritten by an automatic score or new search result.

## Deterministic Audits and Tests

After [root tests](../README.md#tests-and-checks), optional fixed-date audits from
`mobile/` are:

```sh
node --experimental-strip-types web/scripts/validate-quizzes.ts --write
node --experimental-strip-types web/scripts/report-coverage.ts 2026-10-18
git diff --exit-code -- web/quiz-audit.json web/coverage.json
```

Coverage audits include 32 calendar dates from the supplied date. Specifying the
same date avoids changing the report merely because the clock advanced. Current
coverage has **551** eligible public association anchors in seven regions, all
12 real-eligible Signatures, and no WakeMed spawns. Content support is not a
guarantee of every species appearing in a rotation.

For exact public deployment verification, use the command in
[web QA](../mobile/web/QA.md); `EXPECTED_APPLICATION_SHA` must identify what is
actually deployed, not necessarily today's main merge commit. No application or
analytical output should be committed just because a documentation check ran.

## Attribution and Reuse

OSM data is ODbL and requires attribution; city/university sources retain their
terms. Keep source provenance and derived-boundary disclaimers. Owner-supplied
images are available in the repository for reproduction, without an invented
license to reuse them elsewhere. Publisher readings and Signature sources remain
external copyrighted content, not locally redistributed lessons. Follow the
linked stage READMEs and [learning policy](../mobile/web/LEARNING_LINKS.md).
