# Playable Browser QA and Reproduction

Public URL: **https://modemon-go-playable.astralgnat19.chatgpt.site/**

This is the current browser handoff, superseding the early issue-15 placeholder
and three-question-only reports. It does not certify physical iPhone behavior,
native gameplay parity, source freshness, access safety or production security.

## Release Identity

The last verified application deployment is hosting **version 12**:

- Application commit: `62cc20d4f64b7fbfaee585f17c894f7afcb78e34`.
- Application branch at packaging: `dev/modedex-learning-links`.
- Separate Sites source/packaging commit: `b2154b6cbbff484f2b3683e274166b89f815b002`.
- Main after PR #32: `63bda5787f3fc7db0183f077cbaad00cf85036f7`; its application
  tree matches that deployed feature commit. Merge SHA and deployed SHA differ.
- [CI for the deployed commit](https://github.com/maladroitcat/modemon-go/actions/runs/39181294034)
  passed canonical-data, native/web checks, browsers, production build and exports.

The [public provenance file](https://modemon-go-playable.astralgnat19.chatgpt.site/deployment-provenance.json)
exposes application identity, overlay digest, image count/logo presence and
production JS/CSS hashes. A future deployment can supersede this dated record;
inspect provenance rather than assuming a README is the live release authority.
This documentation-only update does not deploy or modify the application.

## Verified Checks

The issue-30 release passed **146 public-host tests, zero skips**, in iPhone-sized
Chromium and WebKit with local servers stopped. They cover captures/reload,
daily escapes, answer/difficulty persistence, Demo/real isolation, all three
difficulties, camera preference, image loading and approved link behavior. Actual
un-intercepted workbook, MIT and Nasher click-through checks returned HTTP 200 at
the expected URLs with null openers. Routine browser navigation tests intercept
publisher responses; third-party uptime is not treated as an application test.

The documentation reproducibility check starts at main after PR #32 and uses a
separate clean checkout: new Python virtualenv, clean `npm ci`, no root artwork
drops, concepts, private snapshot or reused `node_modules`. See
[the reproducibility guide](../../data/REPRODUCIBILITY.md) for commands and the
documentation PR for the final execution record. The following are release
baseline checks, not an assertion that native hardware was tested:

| Check | Verified baseline |
| --- | --- |
| Python unit/integrity suite | 160 passed, zero skips |
| Native foundation typecheck, lint, unit tests | Passed; 18 unit tests |
| Playable typecheck, lint, unit tests | Passed; 54 unit tests |
| Expo-web foundation browser regressions | 5 passed |
| Local playable browser regressions | 144 passed |
| Public-host regressions with exact-SHA verification | 146 passed, zero skips |
| Quiz validation | 51 species x 3 modes = 153 banks, 765 question instances |
| Learning overlay | 39 IDs: 35 workbook primary + 4 approved outside; zero Signature supplements |
| Artwork | 51 creature masters + logo; 208 derivatives, 10,827,827 bytes |
| Rebuild checks | Modédex, artwork, runtime and learning JSON agree with committed resources |
| Production playable build | Passed payload checks; output `mobile/web/dist/` |
| Expo dependency compatibility / export | Passed; iOS, Android, web JavaScript exports, not signed apps |

### Documentation-only reproduction check (2026-10-18 EDT)

The clean checkout independently passed the 160 Python, 18 native unit, 54 web
unit, 5 Expo-web browser and **144 playable browser** cases above, plus
typecheck/lint, online Expo dependency compatibility and all-platform export.
The documented local launch served HTTP 200. Modédex, all artwork derivatives,
runtime/learning JSON and fixed-date quiz/coverage audits rebuilt with **no
tracked changes**. A focused **14-case public HTTPS** repeat passed with local
servers stopped, verifying the deployed SHA, production asset hashes, all link
sections, keyboard navigation, lock/progress integrity and narrow/landscape UI.
The full 146 public cases are the earlier release run, not a claim of another
full public rerun in this documentation task.

A second disposable checkout ran labeling, cell scoring, exact zone dissolution,
region QA, candidate scoring and curation on committed inputs. It reproduced
927 POIs, 1,998 cells (1,993 classified/5 neutral), 62 zones (18 micro/55 review),
824 eligible candidates, 42 shortlist entries and 17 human-selected primaries.
No live GIS/OSM retrieval or publisher crawl was necessary. Regenerated figures
can differ in PNG metadata; they are not copied into this documentation PR.

The edited-branch integrity run initially rejected edits to three historical
data READMEs because an existing fixture freezes those documents along with
canonical inputs. Those edits were removed; current guidance lives in the new
reproduction guide instead. The final suite passes without changing a test,
fixture, canonical dataset or application file.

All local Markdown destinations/anchors and HTTPS references in the updated
guides were checked. Referenced URLs returned HTTP 200 (some redirect to a
canonical page). Reachability is point-in-time evidence, not a guarantee of
future availability or endorsement of third-party privacy/accessibility.

Benign Node module-type/color-environment warnings and Vite/Lucide build warnings
were visible. A unit-test markup helper also emitted a dependency-prebundling
warning for `expo/tsconfig.base`; the tests, actual local browser launch and
production build passed. No application/dependency changes were made to suppress
these warnings. A nonzero command result must still be investigated.

An earlier public WebKit artwork check exposed a readiness race: a reserved image
box could be visible before the logo decoded. PR #32 changed only the test to wait
for nonzero natural width, retaining the strict decode assertion. Final public
and CI runs passed; artwork and gameplay were not changed to hide the race.

## Coverage: Content Is Not Availability

[coverage.json](coverage.json) is a deterministic audit for **2026-10-18 through
2026-11-18**, not a claim about the user's current date. It records exact species,
POIs, Signature schedule, anchor counts and exclusions. Baseline inputs are 51
species, eight regions, 927 POIs, 62 zones and 17 curated destinations.

| Region | Eligible ordinary public association anchors |
| --- | ---: |
| DUR-01 | 153 |
| DUR-02 | 52 |
| RAL-01 | 277 |
| RAL-02 | 17 |
| RAL-03A | 26 |
| RAL-03B | 7 |
| RAL-04 | 19 |
| RAL-05 | 0 |
| Total | 551 |

All **51** creatures have approved responsive art and quiz support; **all 12**
Signatures have explicitly approved real outdoor associations and appear across
the Demo rotation. Shared anchors host one Signature at a time; schedule/density
can omit a form on any given date. No specific-location deployment is inferred.

The 32-day snapshot observed 45 species and eight habitats. Commutoracle is
eligible but unobserved in that window. Beatling, Pathogaze, Clinink, Wardwisp and
Wardray have validated content but no eligible public Healthcare anchors. RAL-05
intentionally has no encounters. Do not change safety filtering to force 51
reachable forms or nine spawned habitats. See
[Signature safety evidence](SIGNATURE_ENCOUNTERS.md) and [art audit](../../assets/ARTWORK_README.md).

Learning coverage is independent of spawn availability: all **39** non-Signatures
have at least one approved reading, and all **12** Signatures keep only their
canonical real-project link. Locked discoveries remain locked. The 45 existing
workbook mapping records are preserved, including historical research matches
for Signatures that are deliberately not shown. See [learning policy](LEARNING_LINKS.md).

## Re-run Against the Actual Public Host

Install the root prerequisites and Playwright browsers first. Stop local Vite
and Expo servers (Ctrl-C in their terminals). From `mobile/`:

```sh
PLAYABLE_BASE_URL=https://modemon-go-playable.astralgnat19.chatgpt.site \
EXPECTED_APPLICATION_SHA=62cc20d4f64b7fbfaee585f17c894f7afcb78e34 \
npm run test:playable:e2e
```

When `PLAYABLE_BASE_URL` is set, Playwright does not launch a local server. The
optional SHA adds two provenance/asset checks, one per browser, giving 146 rather
than 144 cases. Update it only to an independently verified deployment, not just
the latest merge SHA. To run a focused repeat, append `-- learning.spec.ts`;
that runs 14 link/layout/accessibility/provenance cases across the two browsers.
Tests use isolated browser contexts and do not alter a visitor's saved progress.
Camera/GPS paths use test doubles where required; real OS prompts are not verified.

## Physical iPhone / Field Acceptance Still Required

- [ ] Open public HTTPS on a physical iPhone, confirm logo, readability, touch
  targets, screen-reader announcements and portrait/landscape scrolling.
- [ ] Acknowledge safety, opt into Demo, capture and reload; attempt a failing
  quiz and confirm that exact encounter stays escaped for its rotation.
- [ ] Test all difficulty boundaries (2/3, 3/5, 4/7), saved mid-quiz answers and
  locked difficulty, correct green/check and incorrect red/cross feedback.
- [ ] Allow camera, see creature overlay, exit and confirm it stops. Enter another
  encounter to test remembered opt-in, disable, reload, re-enable, deny permission,
  and background. No-camera play must remain equivalent throughout.
- [ ] From a safe, stationary public path, test real foreground GPS, stale/poor
  accuracy, far-away denial, and the actual 75 m rule/accuracy allowance. Displayed
  feet/miles are rounded and never redefine the metric gate.
- [ ] Check current signs, hours and closures at reviewed outdoor anchors,
  especially GoDurham stop 6680 and Hunt's street-side approach. Do not enter
  construction, clinical areas or blocked paths. Skip any unsuitable encounter.

## Open Limits and Decisions

No signed native app, completed native game, field-certified routes, live
opening-hours/obstruction enforcement, cloud sync, backend anti-cheat, offline
launch, multiplayer or evolution mechanics. Browser time and storage are trusted;
clearing site data removes progress. System/institutional AI examples do not
assert installation at the mapped point. Stored camera opt-in never grants OS
permission. Third-party map/hosting/publisher requests have their own privacy terms.

Clean npm installation reports **28 vulnerable dependency nodes: 20 high,
7 moderate, 1 low**, inherited from the locked toolchain; no critical nodes were
reported. Counts can change with registry advisories. Do not force an incompatible
Expo downgrade or change dependency/source code in a documentation PR. Functional
CI and Expo compatibility do not waive security review. Vite's large-chunk warning
and Lucide directive warnings do not prevent the verified static build; payload
budgets remain enforced. Python transitive/system libraries are not fully locked.

Owner follow-up remains physical-device/accessibility and safe-path acceptance,
dependency-risk review, and a production tile-provider decision before broader
distribution. Approval of art, all twelve Signature associations and the four
outside learning references is **complete**, not an outstanding product decision.
