# Capture Quizzes: Issue 19

Built on the issue #17 playtest improvements (`4bddfd2`), not an older MVP.
No canonical Modédex fields, habitat data, geography, POIs, artwork, spawn seeds,
GPS gates, or encounter IDs are changed.

## Modes

| Difficulty | Questions | Correct To Capture | Content |
| --- | ---: | ---: | --- |
| Novice | 3 | 2 | Role, input, output |
| Intermediate | 5 | 3 | Two deterministic basics, family, habitat, representative technique |
| Expert | 7 | 4 | Intermediate plus explainability and limitations |

All questions are presented, even when the final outcome is already mathematically
decided. Feedback preserves issue #17's green/check/Correct and red/cross/Not quite
states, useful source-grounded explanation, and correct answer. The score and chosen
difficulty remain visible. Failure still removes only this encounter for its daily
rotation; another POI hosting the same species is unaffected.

## Grounding And Question Quality

`src/quizzes.ts` uses only existing structured canonical fields. The Modédex job
family is `family_id` resolved through `families.*.name`, not an invented deployed
architecture. Habitats are canonical IDs rendered with readable labels. Techniques
come from `models_algorithms`; Expert inspection comes from `explainability`, and
failure/bias examples from `biases_limitations`. No web research, inferred telemetry,
invented deployment claims, AI question generation, or new creature facts are used.

Every question has four distinct options and one entry-supported correct answer.
Both correct options and distractors carry source paths and exact source values.
For advanced questions, the prompt explicitly asks **what this entry lists**.
An algorithm or analysis method absent from an entry is not scientifically impossible
for that task. This source-scoped wording is important: generic ML techniques and
biases often apply to more than one job, so questions must not imply exclusivity.
Other listed answers for the target entry are excluded from distractors; advanced
non-habitat distractors also exclude all values listed for its family. A habitat's
presence never claims the surrounding POI deploys a system.

Intermediate always tests family, habitat, and a representative technique, plus two
of role/input/output selected deterministically by encounter ID. Expert retains those
same five and appends inspection and limitation questions. New basic feedback explains
only the asked field, rather than giving away the next input/output answer. Legacy
feedback remains unchanged for already-saved attempts.

`npm run validate:quizzes` checks all **51 entries x 3 modes = 153
banks**, containing **765 question instances** for a fixed audit encounter. It fails
on missing topics, fewer than four supported options, duplicate/another listed correct
choice, unsupported provenance, or options longer than 180 characters. Current maximum
option length is **106 characters**; no missing topics, duplicate options, or excessive
options were found. `quiz-audit.json` contains the complete deterministic audit with
options, answers, explanations, and provenance. It is a review aid, not proof of
pedagogical quality or a claim that synonyms can never overlap conceptually.

```sh
cd mobile
npm run validate:quizzes
# Regenerate the detailed audit intentionally:
node --experimental-strip-types web/scripts/validate-quizzes.ts --write
npm run test:playable
npm run test:playable:e2e
npm run build:playable  # validation runs before the production build
```

## Persistence And Legacy Compatibility

The existing storage keys and independent Demo/real collections are preserved.
New encounters use `startAttempt` and save `quiz_version: 2`, the chosen difficulty,
and the **exact complete question snapshot** before any answer. Difficulty defaults
to Novice and can change only while no answer exists. Reopening, reloading, or leaving
and returning to Demo cannot reset answers or change a locked difficulty. Snapshot
answers remain stable even if later canonical editorial content changes.

Progress with a new attempt uses outer `version: 2`. Older clients only understand
version 1 and fail closed on version 2, preventing an older open tab from silently
converting a five/seven-question attempt into a three-question result. A deployment
rollback to the old client therefore cannot safely resume new attempts; roll forward
or restore a compatible client, never clear player storage as an upgrade strategy.

The reader supports both outer versions. Pre-existing unversioned attempt records
use an explicit legacy-Novice adapter: original `questionsFor` bank, three answers,
two-correct threshold, and original feedback. Their records are not rewritten or
regraded, including completed captures and escapes. Even zero-answer legacy attempts
remain Novice to preserve their question identity. `beginAttempt` is retained as the
legacy helper; the current UI exclusively uses `startAttempt`. The outer version is
upgraded only when a new v2 attempt starts, not by wiping or replacing legacy records.
Unknown versions, malformed banks, invalid answers, and inconsistent new results
fail closed without overwriting storage. This is browser-local persistence, not a
server-enforced anti-cheat system; manual storage edits are not prevented.

## QA And Limits

Unit tests cover all 153 banks, every correct/incorrect partition of 3/5/7 answers,
strict-majority boundaries, no early completion, snapshot and difficulty locks,
old captures/escapes/in-progress fixtures, corrupted data, source integrity, and
unchanged frozen worlds. Browser tests run pass and fail boundaries for all modes,
reload before/after answers, Demo/real switching, disabled mode controls after an
answer, color/text/icon feedback, and long options at 320 x 568, 393 x 852, and
844 x 390. Existing native and playable regressions remain required.

The expanded issue-21 playable suite has 114 cases across Chromium and mobile WebKit. These are
not physical iPhone Safari tests; owner field/device acceptance remains necessary.
Five Healthcare-only forms still have no suitable public gameplay anchors under
the existing conservative policy, but their quiz content is validated. All twelve
Signatures now have explicit approved mappings and real outdoor placements;
the two Durham Station forms use the alternative public sidewalk by GoDurham stop 6680. See
[SIGNATURE_ENCOUNTERS.md](SIGNATURE_ENCOUNTERS.md). No quiz claim extends their
deployment provenance or locations.

`coverage.json` reports scheduled geography/species coverage; `quiz-audit.json`
is the current three-mode question content audit. Human
review can still improve distractor pedagogy, but must retain source-scoped wording
and must not infer task-exclusive techniques or unverified deployed systems.

## Owner Follow-up: October 18

The difficulty picker now shows only Novice 3 questions, Intermediate 5 questions,
and Expert 7 questions. It deliberately omits required-correct counts next to the
choices. Strict-majority scoring and the existing progress migration remain unchanged;
in-quiz score/progress, feedback, and final outcomes still explain the result.

Player distance text uses the single `approximateDistance(meters)` display helper:
feet below an unrounded 0.25 mile (402.336 meters), miles at/above it. Feet under 100
are rounded to whole feet (positive distances never round to zero); larger feet
round to tens with US grouping. Miles under one use up to two decimal places, then
one decimal place. Examples: 75 meters displays roughly 250 ft; 381 meters displays
1,250 ft. The proximity instruction derives its approximate value from the unchanged
75-meter rule; a rounded display never grants access. GPS accuracy/uncertainty and
Demo distances use the same helper. Invalid distances are explicitly unavailable.
No GIS, accuracy allowance, freshness, or half-mile density calculations changed.

Signature details now explicitly introduce recorded real-world inspiration and link
to canonical evidence, with safe missing/unsafe-source states. See
[SIGNATURE_SOURCE_REVIEW.md](SIGNATURE_SOURCE_REVIEW.md) for all sources and two
recorded-title review flags. Canonical content and provenance are unchanged.

The expanded suite contains 38 browser tests across Chromium/mobile WebKit, including
all 12 Signature details and links, selector labels without passing thresholds, US
distance display, and the existing complete quiz/capture/progress regressions.
Additional unit tests exercise distance boundaries, metric gates, source URL safety,
and actual standalone detail markup. Physical iPhone Safari acceptance remains separate.
