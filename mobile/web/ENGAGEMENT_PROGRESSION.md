# Engagement and progression

The browser game derives collection, quiz mastery and Trainer Badges from the
existing successful capture attempts in the current mode. No migration, new
storage key, account, backend, analytics or location history is introduced.
Real and Demo collections remain independent.

## Playing

- Anonymous map markers retain their rarity shapes and question marks. Green,
  blue and gold indicate Common, Rare and Signature encounters. Slate gray means
  that species has already been captured; the tooltip/accessibility label and
  nearby row also say **Previously collected species**. Its identity stays
  hidden until entry. Collection never changes encounter eligibility.
- Discovered Modédex entries use the existing artwork in a reusable trading
  card: Ability / Job, How It Works, Weaknesses / Limitations, Explainability,
  AI in the Wild, and Further Learning. All canonical fields and project sources
  remain available. The encounter version omits everyday examples and mastery
  explanations to keep Capture and difficulty selection reachable.
- Every species has two separately authored everyday examples in
  `src/data/everydayExamples.ts`, keyed by its stable ID. These are explicitly
  hypothetical applications, including Durham/Raleigh examples, not claims of
  deployment. Signature documented projects and their original citations remain
  separate. The overlay never enters quiz inputs or world fingerprints.
- Each captured species displays **Beginner**, **Intermediate** and **Expert**
  mastery positions in its list row and detail. Locked badges describe their
  requirement; earned badges show their state in text and color. Passing Novice
  earns Beginner. Passing a higher difficulty earns only that difficulty's
  badge. Another eligible encounter is required to earn another badge; finished
  encounters cannot be retried. Historical version-1 captures count as Novice
  through `attemptRules()`, without regrading them.
- **Badges** opens fifteen achievement cards, with numeric progress and earned,
  locked or in-progress text. Eight family cards use canonical family labels.
  Family Expert means collecting that family, not passing an Expert quiz.
- Newly earned Trainer Badges share one dismissible, polite notification. It
  appears after leaving the encounter, lasts nine seconds, and never animates
  or moves keyboard focus. History loads, reloads, storage events and mode
  switches do not celebrate old awards. Switching modes clears pending notices.

## Calculations and compatibility

`src/achievements.ts` is a pure calculation layer. Only records whose status is
`captured` contribute. Encounter IDs are unique object keys, so each completed
record contributes once. Hoarder counts successful distinct encounters of the
same species; the other collection milestones use unique species IDs.
Master Scholar counts species with an actual successful Expert capture.

Family, rarity and overall requirements are filtered from the canonical runtime
catalog, not maintained as species lists. Special Collector uses `signature`;
there is no `special` rarity. New species automatically enter applicable totals.
No achievement or mastery state is separately persisted. Corrupt/blocked storage
still disables capture without deleting saved data.

Canonical YAML/schema, `quizzes.ts`, `rules.ts`, learning links and source
citations are unchanged. All eight regions, 927 source POIs, coordinates and
habitat assignments remain intact. The subsequent owner-approved Healthcare
overlay enables twelve existing locations from 2026-11-21; the engine applies
that effective date using existing rarity and density rules. The 75 m gate, GPS
accuracy checks, camera and quiz thresholds are preserved. Historical frozen
worlds, quiz banks and legacy progress fixtures continue to pass.

The old issue-23 UI snapshot intentionally predates the requested new legend
and card layout. `engagement-copy-baseline.json` freezes the new UI wording
separately; the historical snapshot stays intact. The copy regression test
retains its original quiz, feedback and Signature-source hashes; separate
frozen-world and safety suites protect gameplay contracts. The new card rendering
test additionally verifies every canonical educational field and Signature
source for all 51 entries.

## Current coverage

The owner’s subsequent approval of twelve existing Healthcare locations resolves
the missing-anchor gap described below. All 51 species now have eligible
locations, with 563 eligible anchors in total. Both Hemp Farmacy records and
other unapproved clinical sites remain excluded. The updated 32-day audit sees
49 species; a longer 128-day audit confirms actual encounters for all five
formerly unavailable species. Daily rotations still limit what appears today.
See [the exact approvals, effective date and audit](HEALTHCARE_ENCOUNTERS.md).

## Historical coverage audit — before owner approval

Before the 2026-11-21 owner approval, these five ordinary species had no eligible
locations in either mode. All five are canonical **Rare** species:

| Stable ID | Modémon | Canonical family |
| --- | --- | --- |
| `anomaly_vitals` | Beatling | Anomaly Watcher |
| `detector_disease` | Pathogaze | Detector |
| `extractor_medical` | Clinink | Document Extractor |
| `forecast_patient` | Wardwisp | Demand Forecaster |
| `scheduler_hospital` | Wardray | Scheduler |

These were missing eligible anchors, rather than simply absent from a short
rotation sample. The conditions below are retained as the pre-approval audit. `speciesWithoutAnchors()` derives that advisory from runtime
habitats, eligible public POIs and approved Signature placements. It is never
used by the encounter generator and does not reduce completion requirements.
The affected cards displayed a non-alarming coverage explanation. Already-saved
qualifying successes still count, including any historical records for these
species; the advisory counts only requirements still missing for that player.

| Unattainable before owner approval | Canonical requirement | Coverage ceiling |
| --- | ---: | ---: |
| Model Master | 51 species | 46 |
| Master Scholar | 51 Expert-mastered species | 46 |
| Rare Collector | 31 Rare species | 26 |
| Anomaly Watcher Family Expert | 5 species | 4 |
| Detector Family Expert | 4 species | 3 |
| Document Extractor Family Expert | 7 species | 6 |
| Demand Forecaster Family Expert | 5 species | 4 |
| Scheduler Family Expert | 8 species | 7 |

Hoarder, Connoisseur (8 families), Common Collector (8 species), Special
Collector (12 Signatures), Generator Family Expert (8), Recommender Family
Expert (8), and Retriever Family Expert (6) have no such missing-anchor
requirement. This is not a promise about any particular day's rotation.
Commutoracle (`forecast_transit`) was unobserved in the existing 32-day report
but **does** have eligible anchors and is not counted as inaccessible.
The later, explicitly authorized access additions resolve these historical
limits without changing canonical achievement requirements.

## Validation and review artifacts

Validation on 2026-11-21 used Node 24.22.0 and the documented Python 3.12.2 virtual environment.
Tests use deterministic canonical encounters and separate real/Demo storage.
New coverage includes successful/failed/unfinished distinctions, duplicate
counts, independent mastery, v1/v2 compatibility, exact family/rarity totals,
simultaneous unlocks, missing-anchor warnings, all 51 example entries, canonical
card content, unchanged worlds and immutable completed attempts.

Browser checks cover Chromium and WebKit, reloads, both cities, all difficulty
badges, anonymous map/list updates (including Signature CSS), combined notices,
320 px portrait/844 px landscape, reduced motion, keyboard navigation, Escape
and focus restoration, source links and reachable Capture controls.

| Command | Result |
| --- | --- |
| `npm ci` | Passed with pinned lockfile; no dependency changes |
| `npm run check` | Passed: native TypeScript, lint and 18 unit tests |
| `npm run check:playable` | Passed: browser TypeScript and lint |
| `npm run test:playable` | Passed: 67 tests |
| `npm run validate:quizzes` | Passed: 153 banks, 765 questions |
| `npm run validate:learning` | Passed: 35 workbook + 4 approved outside readings; 12 Signature exclusions |
| `npm run test:e2e` | Passed: 5 Expo browser tests |
| `npm run test:playable:e2e` | Passed: 164 Chromium/WebKit tests in 5.2 minutes, no retries |
| `npm run build:playable` | Passed: 474,677 gzip JS bytes / 550,000 budget; 27,673 CSS bytes / 30,000 budget |
| `.venv/bin/python -B -m unittest discover -s tests -v` | Passed: 165 tests |
| `npx expo export --platform all --output-dir dist` | Passed: web, iOS and Android bundles |
| `npx expo install --check` | Online check reports existing pinned-version drift; see below |

After shortening the Healthcare encounter instructions for mobile readability,
the four focused Chromium/WebKit cases, all 67 browser unit tests, all 165 Python
tests and the production build were rechecked successfully.

The sandbox initially blocked npm registry access and local server binding.
Rerunning those operations with the normal tool approval succeeded. The initial
full browser run overlapped a UI edit and was not used as final acceptance.
An actual WebKit pointer-focus failure was corrected by remembering the
encounter's trigger explicitly, rather than relying on Safari focusing a tapped
button. No failing test was removed or given weaker assertions.

Expo's offline check reports that the pinned local dependency map is satisfied.
The **online** check exits 1 because the current Expo compatibility endpoint
recommends newer patch/minor versions: Expo 58.0.26, constants 58.0.16,
dev-client 58.0.21, linking 58.0.17, location 58.0.22, router 58.0.32,
status-bar 58.0.5, React Native 0.88.1, safe-area-context 5.11.1, screens 4.30.1
and `@types/react-dom` 19.3.0. `mobile/package.json` and the lockfile are
byte-unchanged from main. This is a pre-existing toolchain compatibility result;
the brief excludes unrelated upgrades. The export also emits existing Leaflet
CSS-resource warnings in Metro, while the playable Vite build completes normally.

Screenshots from deterministic Demo fixtures are saved under
[`screenshots/engagement/`](screenshots/engagement/). They show local QA, not a
deployment or a physical-device acceptance record. Street tiles may be absent
in automated captures; anonymous markers and canonical boundaries remain visible.

| Review image | File |
| --- | --- |
| Gray collected and original rarity markers | [Map](screenshots/engagement/map-markers.png) |
| Full trading-card entry and Expert mastery | [Card](screenshots/engagement/trading-card.png) |
| Three independently earned mastery badges | [Mastery](screenshots/engagement/species-mastery.png) |
| Trainer achievement gallery | [Gallery](screenshots/engagement/trainer-gallery.png) |
| Newly earned Hoarder notification | [Unlock](screenshots/engagement/achievement-unlock.png) |
| Current Healthcare collection coverage | [Coverage](screenshots/engagement/healthcare-coverage.png) |
| Student Health outdoor public approach | [Access](screenshots/engagement/student-health-public-approach.png) |

No public deployment was performed. Mobile Safari on a physical iPhone,
field GPS, safe public approaches and camera permission behavior still need
human/device acceptance; browser automation does not establish production
acceptance.
