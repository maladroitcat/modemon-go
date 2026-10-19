# Public Playable Web MVP

The playable browser app is merged into main, including approved artwork,
Signature encounters, camera preference and educational links through PR #32.
Historical issue/branch handoffs are not the current feature inventory.

Public HTTPS: **https://modemon-go-playable.astralgnat19.chatgpt.site**

## Try It

1. Open the URL in Safari, read the safety notice, check the acknowledgment, and
   select Start Playing. No login, Expo Go, native build, or developer account.
2. Outside Raleigh/Durham, explicitly select **Try Demo Mode**. The persistent
   **DEMO LOCATION — not your GPS** banner means all player movement is simulated.
   Choose Raleigh or Durham, select an anonymous encounter, then choose
   **Simulate walking here (Demo)** and **Enter encounter**.
3. Enable the camera if appropriate, or use the complete non-camera encounter.
   Tap the creature, read its Modédex entry, then Capture.
4. Choose Novice (3 questions), Intermediate (5), or Expert (7).
   Answer every question; too few correct escapes for that exact encounter/day.
   Read feedback, show the result, then reload to check the
   saved collection. Demo captures are separate from real captures.
5. Report the browser/iOS version, mode, date, POI, and steps in the repository's
   [issue tracker](https://github.com/maladroitcat/modemon-go/issues). Do not
   attach private GPS coordinates, images of people, or clinical spaces.

Real mode requires a fresh foreground fix, accuracy at most 50 m, and distance
within 75 m plus `min(accuracy / 2, 10 m)`. Denied GPS permits browsing/demo, not
remote real-world capture. Never approach an unsafe or inaccessible location.
Player-facing distances and accuracy use rounded feet below 0.25 mile and miles
above it. The roughly 250 ft instruction is an approximation of the unchanged
metric interaction rule, not a new fixed 250-foot gate.

## Architecture

`scripts/build_web_runtime.py` reads canonical files only. It exports exact region,
zone, and neutral geometries; compact POI association points/context/access flags;
all 51 Modédex entries; all 17 curated destinations; explicit region precedence;
source SHA-256 digests and deterministic content/gameplay versions. No raw cells, contribution
tables, Python runtime, backend, player account, or geolocation history ships.
The version includes the explicit `public-anchors-v1` bridge policy; bump that
policy when changing eligibility, and bump gameplay rules when changing scoring.

`content_version` tracks the full canonical input bytes. The gameplay fingerprint
excludes only Modédex `dex_entry` prose, so editorial fixes cannot reroll daily
encounters or reset saved attempts. `config/world_identity.json` explicitly aliases
the unchanged PR #16 gameplay fingerprint to its already-published data version
`0f51a954e4340dea`. Other structured content still participates in the fingerprint;
new gameplay data receives a new version. Do not update that compatibility alias
merely to make a changed world look unchanged. Frozen worlds, quizzes, and browser
progress fixtures verify the original identity independently of the new copy.

The browser uses Turf for boundary-inclusive polygon lookup and Leaflet for a
normal pannable/zoomable street map. The native map and native onboarding routes
are unchanged. `index.web.tsx` loads this same Game through a platform-specific
loader: browser libraries do not enter the iOS/Android bundles. A small Vite static
entry serves the identical component without Expo's larger routing runtime.

## World Rules

`src/rules.ts` is the explicit versioned v1 rule configuration. Eastern calendar
date + canonical data version + rules version seed stable encounter and question
IDs. Viewport, player position, browser mode, panning, and reload never seed the
world. Common/rare selection is 70/30 **before** density selection, not a guarantee
about final proportions. All twelve stage-3 forms use explicit approved outdoor
associations and the separate rare Signature calendar, never guessed anchors.

Each safe POI receives eligibility from its own primary/secondary habitat plus
the primary zone context at that location, inside its resolved parent region.
Unconfigured parent overlaps fail closed. Local POIs can supply a habitat absent
from the surrounding zone. Neutral areas are not relabeled. Ordinary encounters
use public POI associations rather than invented placements in inaccessible land.

Global deterministic greedy placement rejects a candidate if any fixed-radius
0.5-mile disk could contain more than seven markers, across regions and rarities.
It tests pair-defined circle centres, not just circles centred on markers. Uses
EPSG:2264 projected metres converted from **US survey feet**, with a conservative
one-metre guard. Captures/escapes remove markers; they never refill or reroll the
world. The issue-21 overlay now admits explicitly approved Signature slots first;
see [SIGNATURE_ENCOUNTERS.md](SIGNATURE_ENCOUNTERS.md) for all twelve mappings,
shared-anchor rotation, outdoor placements and individual safety holds.

Generated metric POI helper coordinates are rounded to one millimetre for stable
macOS/Linux builds. Original latitude/longitude and all polygon geometry remain
exact. The Python requirements pin Fiona 1.9.6 for GeoPandas 0.14 compatibility.

Sensitive, age-restricted, private, closed, unknown/rejected curated, unclassified,
and habitat-review candidates are excluded. Public-facing accessibility evidence
or an approved curated destination is required. No guarantee of current hours or
safe approach is implied. Clinical facilities and WakeMed are not destinations in
this build. **RAL-05 has zero encounters intentionally**, pending a safe anchor.

## Quizzes And Persistence

All 51 entries (including twelve approved Signatures) support Novice (3 questions, 2 correct), Intermediate
(5 questions, 3 correct), and Expert (7 questions, 4 correct). Novice tests role,
input, and output; Intermediate adds family, habitat, and representative techniques;
Expert adds supported inspection/explainability and limitations. All answers and
distractors come from canonical structured fields, with source-scoped wording rather
than claims of exclusive techniques or actual POI deployments. Every item has four
distinct choices. Feedback shows the correct answer and a source-grounded explanation.
Correct feedback is green with a check icon and "Correct."; incorrect feedback is
red with a cross icon and "Not quite.". Text and live announcements distinguish
the states without depending on color. The answer and capture rules are unchanged.

Browser local storage writes each answer before progressing. Encounter IDs include
date/version/POI; closing and re-entering resumes answered-question progress, and
escaped/captured markers remain unavailable for that rotation. No retry resets.
Another encounter of the same species is unaffected. Discovered entries only are
visible in the Modédex. Separate real/demo keys; coordinates are never persisted.
Storage denial/corruption is explicit and disables capture rather than claiming a
save. Clearing site data or changing browser loses progress. No cloud sync or
anti-cheat claim; this is a local educational prototype.

Difficulty and the full question bank are saved before the first answer; difficulty
locks after the first answer. Outer progress v2 prevents older clients from writing
incompatible three-question results. Existing v1 attempts remain readable under their
original Novice rules without regrading captures or escapes. See [QUIZZES.md](QUIZZES.md)
for the compatibility policy and [quiz-audit.json](quiz-audit.json) for all 153 banks.

The first successful Enable camera action remembers opt-in. Later encounters
auto-attempt video only when the page is visible and browser permissions permit;
this preference does not grant permission or bypass Safari. Use without camera
always stops it and remembers off; re-enable is available. Failure falls back
without a retry loop. HTTPS, `playsInline`, stream cleanup and late-permission
handling are preserved; no frames/audio are recorded or uploaded. Non-camera play
is equivalent. This is a 2D overlay, not 3D AR. See
[camera preference](CAMERA_PREFERENCE.md).

All 39 non-Signatures have approved learning sections: 35 workbook primaries,
four owner-approved external readings, and distinct secondary lessons where
already supplied. Exact species IDs and approval/source hashes are validated in
a separate `learning.json` overlay, outside world identity. Partial matches are
labeled supporting concepts. All 12 Signatures keep **only** canonical project
links, with no supplemental reading section. Links are keyboard/screen-reader
accessible, safe new tabs, and not prefetched. See [learning links](LEARNING_LINKS.md).

## Coverage And Limits

Exact species IDs/names, eligible POI IDs/names, daily encounters, habitat coverage,
and individually withheld forms are recorded in [coverage.json](coverage.json),
including a 32-day rotation audit. All 51 entries now have quiz support; all twelve Signatures have
real placement eligibility and all twelve are available over the Demo rotation.
Five Healthcare-only ordinary forms have no suitable public anchors under the
conservative access policy. Eight of nine habitats appeared; Healthcare did not.
There are **551** eligible association anchors across seven regions. Today's
rotation is not promised to expose every enabled species or every habitat.

**51 approved creature assets and the local logo.** Full-resolution masters are
byte-preserved under `assets/`; responsive transparent WebP derivatives and PNG
fallbacks are committed under `web/public/art`. Old Seeklet concepts remain unused
and untouched. Images load lazily in encounters and discoveries, never on anonymous
map markers. Missing images have an explicit placeholder. See
[artwork pipeline](../../assets/ARTWORK_README.md). No new creative artwork or
inferred deployed architectures. Signature coordinates derive
from individually reviewed OSM pedestrian nodes, not invented locations.

OSM street tiles are attributed and browser-cached normally. No bulk download,
offline prefetch, proxy, cache suppression, or offline-launch promise. The public
OSM tile service is suitable only for this small QA preview, not an unlimited CDN;
choose a production tile provider before broader distribution. Requests reveal
viewed map tiles to the provider, not a stored project-side GPS history.

Other limits: client clock controls rotation; device/browser-local progress only;
no current opening-hours enforcement or pedestrian routing; public association
confidence is not physical-access verification. No signed native build, physical
iPhone acceptance, background location, service worker, account, or backend.

Signature detail rendering names the real project/use-case from canonical evidence
and provides "Learn about the real project" with a safe source link. See
[SIGNATURE_SOURCE_REVIEW.md](SIGNATURE_SOURCE_REVIEW.md) for source availability
and two recorded-title review flags. Encounter approval is separate and explicit
in [SIGNATURE_ENCOUNTERS.md](SIGNATURE_ENCOUNTERS.md). Demo's labeled simulated-date
selector lets remote testers explore the rare calendar without changing real GPS
or resetting previous attempts.

## Reproduce

First follow the [clean-checkout prerequisites and installation](../../README.md#how-to-run-and-reproduce).
The commands below use the activated Python 3.12 virtualenv from the repository
root. All source masters and derived game assets are committed; root PNG drops
and old snapshot workarounds are not required.

```sh
python -B scripts/build_modedex.py
python -B scripts/build_game_art.py
python -B scripts/build_web_runtime.py
python -B scripts/build_modedex_learning.py
python -B -m unittest discover -s tests -v
cd mobile
# Node 24.22.0
npm ci
npm run check
npm run check:playable
npm run test:playable
npm run validate:quizzes
npx playwright install chromium webkit
npm run test:e2e
npm run test:playable:e2e
npm run build:playable
node --experimental-strip-types web/scripts/report-coverage.ts 2026-10-18
npx expo export --platform all --output-dir dist
# Local playable browser entry:
npm run play:web -- --port 5173
# Test actual public site, without a local server:
PLAYABLE_BASE_URL=https://modemon-go-playable.astralgnat19.chatgpt.site npm run test:playable:e2e
```

Run local launch and public testing separately; stop the local server with Ctrl-C
before a public-only test. Linux browser installation can require
`npx playwright install --with-deps chromium webkit`. The production playable
artifact is `mobile/web/dist/`; Expo's `mobile/dist/` is a different export.
For analytical rebuilds and map/table locations see
[data reproduction](../../data/REPRODUCIBILITY.md).

## Hosting And Acceptance

[`.openai/hosting.json`](.openai/hosting.json) inside this web directory records
the public Sites project, not a credential. Static
`web/dist` is deployed through an isolated Sites source checkout; the application
GitHub branch is not merged to deploy. No token or host login is bundled. Rebuild,
publish that exact artifact with Sites, and rerun public-site tests after updates.

Physical iPhone Safari remains an **owner acceptance gate**: open the public URL
on an unrelated iPhone, complete a Demo capture and reload, then test camera allow/
deny and real GPS from a safe field location. Playwright WebKit is not a physical
iPhone test. See [QA.md](QA.md) for the verification record and open decisions.

Issue [#17](https://github.com/maladroitcat/modemon-go/issues/17) follow-up:
[playtest review](PLAYTEST_REVIEW.md) and the complete
[51-entry before/after introduction audit](INTRODUCTION_REVIEW.md). Region display
names and approximate distances replace internal IDs and location-gate jargon in
encounter text; the original GPS gate and additional curated safety notes remain.
