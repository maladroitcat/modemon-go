# iPhone Playtest Follow-up: Issue 17

Based on playable MVP commit `1d24c9e29600d098e0e981d0a532d89c9083f72a`.
The feature branch is stacked on `dev/playable-web-mvp`; PR #16 and the native
foundation are not merged or replaced by this change.

## Content And Presentation

- All 51 canonical `dex_entry` introductions were reviewed and rewritten as
  standalone explanations of the represented AI job, with personality and a
  limitation. The [complete audit](INTRODUCTION_REVIEW.md) preserves every old
  paragraph next to its replacement. New introductions are 49-57 words
  (mean 53.5), versus 26-55 words (mean 38.3) before. These are length measures,
  not a certified reading-level score. Structured teaching fields, evolution,
  habitats, representative algorithms, and Signature evidence are unchanged.
- Encounter dialogs, lists, and marker labels use canonical region display names
  and nearby POI names rather than region IDs. Approximate distances explain how
  to get within roughly 75 m only when a safe public approach exists. Phone-location
  uncertainty and Demo simulation are explained separately.
- Public-space instructions replace "Association only". The curated Gipson Play
  Plaza restriction remains explicit: do not approach or linger around children's
  play equipment for the game. No stored destination or safety metadata changed.
- Correct feedback is green with a check and "Correct."; incorrect feedback is
  red with a cross and "Not quite.". Both retain the right answer and explanation
  and use a polite live status. Color is not the only distinction.

## Behavior Preservation

The game engine, rule configuration, 75 m interaction gate, three-question quiz,
two-correct capture rule, daily escape handling, storage keys, and camera lifecycle
are unchanged. The build-time content/gameplay version distinction prevents
editorial changes from resetting the already-published encounter identities.

`tests/fixtures/mvp-gameplay.json` was derived from the unmodified base commit,
not from the revised runtime. Tests compare sixteen complete daily worlds and all
39 playable quiz banks, restore old captures/escapes/in-progress answers, and resume
an existing attempt in the browser. Only `dex_entry` is excluded from the new
gameplay fingerprint. All other source digests and bridge-policy version remain
inputs. Geography, POIs, habitat labels, curated destinations, and native sources
remain unchanged; no creature artwork was created or edited.

## Verification

- Python: 106 tests, including protected-data hashes, all 51 introductions,
  unchanged structured Modédex evidence, and content/gameplay identity separation.
- Playable unit tests: 19, including frozen pre-update worlds and saved progress.
- Native-foundation unit tests: 18; Expo browser regressions: 5.
- Playable browser suite: 20 tests across Chromium and mobile WebKit. Exercises
  capture/reload, escape/reload, resumed quiz, privacy/camera paths, friendly
  proximity wording, red/green computed styles, and explicit text/icon states.
- Inspected WebKit screenshots of correct/incorrect feedback and long introduction
  dialogs. Layout checks cover 320 x 568, 393 x 852, and 844 x 390; the introduction
  remains scrollable and Capture reachable without horizontal page overflow.
- Native typecheck/lint, playable typecheck/lint, and Android/iOS/web exports pass.
- Canonical Modédex and runtime builders are checked for byte-identical repeat builds.

The public host is the existing
https://modemon-go-playable.astralgnat19.chatgpt.site. The PR records the exact
application commit and public deployment verification. No server-side progress
migration or player-data upload is introduced.

## Limits And Owner Acceptance

The owner reported successful physical iPhone playtesting of the previous MVP.
This follow-up is tested using mobile WebKit, not a physical iPhone. A fresh owner
Safari check of the new text, colors, camera permission, and saved collection is
still needed. Automated GPS tests simulate a browser fix; they are not field GPS
validation. No new gameplay tuning or product decision is required for this fix.

Existing limitations remain: browser-local progress, no approved creature artwork
(honest placeholders), no enabled Signature encounters, no pedestrian routing,
and no guarantee of current public access. See the MVP README for full coverage.
