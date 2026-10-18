# Playable Web Verification

Public URL: https://modemon-go-playable.astralgnat19.chatgpt.site

## Passed

- Fresh unauthenticated browser: HTTPS 200, safety acknowledgment and actual
  loaded OpenStreetMap street tiles, no sign-in or native-app dependency.
- Public-site Chromium and WebKit: full demo capture, three MCQs, correct-answer
  feedback, persistent collection after reload, failed encounter stays escaped,
  mid-quiz reload cannot reset answers, demo/real collections isolated, real GPS
  far away cannot enter, denied storage cannot claim a capture, both cities and
  responsive layouts. These are browser tests, **not physical-device acceptance**.
- Local expanded suite: 14 Chromium/WebKit checks, including mocked media-stream
  cleanup on pagehide/exit and foreground GPS shutdown without coordinate storage.
  Positive camera lifecycle is mocked; real hardware/OS prompts remain unverified.
- 12 new deterministic-engine tests; 14 daily rotations satisfy the global
  seven-per-half-mile-circle cap. An eight-point rim fixture catches the case
  where no spawn is at the offending circle's centre.
- All 18 existing Node tests unchanged; Expo web's five onboarding/navigation/
  safety/privacy/responsive regressions adapted to its now-playable web route.
- 102 Python tests, zero skips, using `.venv/bin/python` with pinned dependencies.
- TypeScript and ESLint checks for both native and web; Vite production build;
  three-platform Expo JavaScript export. Native bundles are 4.9 MB and do not
  include Leaflet or camera-game strings after platform loader isolation.
- 179 pre-existing data/art files hash-checked; no canonical geography, content,
  classification, curation or local concept artwork changed. No art staged.

## Exact Coverage

See [coverage.json](coverage.json) for all 551 eligible POI IDs/names, 39 supported
non-Signature catalog IDs, 12 disabled Signatures, all 60 encounters in the
2026-10-17 Eastern rotation, and the 14-day observed species/habitats.

| Region | Eligible public anchors | 2026-10-17 encounters |
| --- | ---: | ---: |
| DUR-01 | 153 | 9 |
| DUR-02 | 52 | 15 |
| RAL-01 | 277 | 13 |
| RAL-02 | 17 | 7 |
| RAL-03A | 26 | 8 |
| RAL-03B | 7 | 1 |
| RAL-04 | 19 | 7 |
| RAL-05 | 0 | 0 |

Eight habitat IDs observed across fourteen dates: civic_government,
education_research, entertainment, finance, food_hospitality, office_business,
retail, transportation. Healthcare is retained analytically but has no accepted
public association anchors here. Beatling, Pathogaze, Clinink, Wardwisp, and Wardray
have canonical content/questions but are not reachable in this access-filtered
world. **31 distinct species observed**, not 51 rendered/encounterable forms.
Swindlisk, Geargoyle, and Routeopus are eligible but did not happen to appear in
those fourteen rotations; they are not disabled.

0 approved creature image assets. 51 explicit missing-art records. The two Seeklet
concepts are not approved and are not bundled. No creative replacement art.

## Required Owner Acceptance / Decisions

1. **Physical iPhone Safari gate is pending.** On an unrelated phone: open public
   URL, acknowledge safety, opt into Demo Mode, simulate walking to an encounter,
   test denied camera, finish quiz, reload and verify capture. Then safely test
   real GPS and allowed camera. WebKit automation is not that device test.
2. Approve final transparent creature sprites before replacing placeholders.
3. Supply/review explicit Signature-to-curated-destination associations and
   scheduling; none are inferred from institution names or exact coordinates.
4. Review safe public Healthcare anchors before enabling those five forms or
   any WakeMed encounters. Clinical/patient areas remain excluded.
5. Approve the v1 70/30 pre-density common/rare mix and bounded GPS tolerance;
   these are transparent MVP defaults, not final ecology tuning.
6. Pick a production map-tile provider before larger public distribution. This
   small QA site uses attributed OSM standard tiles, normal caching, no prefetch.

## Limitations

No signed native build, physical-device acceptance, pedestrian routing/current
hours guarantee, synchronized accounts, backend enforcement, offline launch,
evolution mechanics, or Signature deployment claims. Browser clock/local storage
are trusted in this local prototype. Clearing site data deletes progress.

`npm audit` reports 28 dependency nodes: 20 high, 7 moderate (inherited Expo/native
toolchain), and one low (esbuild's Windows development-server advisory). No
critical advisories. Public hosting serves static output, not a development server.
Do not force a downgrade to an incompatible Expo version as an audit workaround.
Vite warns about bundle size (about 444 KB gzip including exact canonical geometry)
and ignored React Server Component directives in Lucide; the client build succeeds.
