# Modémon GO

A location-based educational game connecting recognizable places to the jobs AI
systems do: detect, spot anomalies, forecast, recommend, extract, schedule,
generate, and retrieve. Meet a creature, inspect its Modédex entry, and answer a
source-grounded quiz to capture it.

**[Play the browser app](https://modemon-go-playable.astralgnat19.chatgpt.site/)**
on iPhone Safari or another modern browser. No login, Expo Go, Apple developer
account or native installation is required. Outside Raleigh/Durham, explicitly
choose **Try Demo Mode**; movement and date previews are labeled simulations.
Read and acknowledge safety before playing. Never approach an unsafe location.

## How to Run and Reproduce

### Prerequisites and clean checkout

- Git, **Python 3.12**, **Node 24.22.0** (see
  [mobile/.node-version](mobile/.node-version)), and npm bundled with Node.
  Select that Node version with your version manager first.
- macOS or Linux with support for the pinned geospatial Python wheels. Clean-
  checkout verification used macOS arm64; Linux CI also validates the app.
- Internet for dependencies, browsers, street tiles and linked readings. No
  API key or fresh GIS download is required for browser play.

```sh
git clone https://github.com/maladroitcat/modemon-go.git
cd modemon-go
python3.12 -m venv .venv
source .venv/bin/activate
python --version
node --version
python -m pip install -r requirements.txt
cd mobile
npm ci
npm run play:web -- --port 5173
```

Open **http://127.0.0.1:5173/** on the development computer; stop with Ctrl-C.
The launch uses committed runtime data and optimized artwork. Python is needed
for validation/rebuilds, not to serve the game. Do not open the HTML directly.
On an iPhone use the public HTTPS URL: an HTTP LAN address is not a secure
camera/geolocation test environment.

### Rebuild canonical content, artwork and browser overlays

From the repository root with the virtual environment activated:

```sh
python -B scripts/build_modedex.py
python -B scripts/build_game_art.py
python -B scripts/build_web_runtime.py
python -B scripts/build_modedex_learning.py
cd mobile
npm run build:playable
```

The static artifact is **`mobile/web/dist/`**, not the separate Expo export.
Art precedes runtime because the runtime hashes its manifest. All 51 creature
masters and the logo, their source manifest, 208 derivatives, and required
canonical GIS/POI files are tracked. **No root PNG drops, untracked concepts,
temporary snapshot, hosting credential or private research file is needed.**
Do not use `--import-local` for normal reproduction. See
[artwork](assets/ARTWORK_README.md) for encoder limitations.

Rebuilding the artifact is different from fetching today's OSM/GIS data. See
[data reproduction](data/REPRODUCIBILITY.md) for stage order, caches, tolerances
and QA paths. Do not refresh geography or re-score habitats just to run the app.

### Tests and checks

From the root after dependency installation:

```sh
python -B -m unittest discover -s tests -v
cd mobile
npm run check
npm run check:playable
npm run test:playable
npx playwright install chromium webkit
npm run test:e2e
npm run test:playable:e2e
npm run build:playable
npx expo install --check
npx expo export --platform all --output-dir dist
```

On Linux use `npx playwright install --with-deps chromium webkit` instead (OS
package installation may require administrator rights). Browser suites start
their own local servers on **8082** (Expo web route) and **5173** (playable app);
keep these ports free. `check` includes native typecheck/lint/unit tests;
`check:playable` and `test:playable` cover the browser separately. Expo exports
verify JavaScript bundles, **not signed native apps or physical devices**.

To test the actual public host, stop local servers first; from `mobile/` run:

```sh
PLAYABLE_BASE_URL=https://modemon-go-playable.astralgnat19.chatgpt.site npm run test:playable:e2e
```

This does not deploy. [Web QA](mobile/web/QA.md) records release identity,
exact-SHA verification, test results and physical-device limitations.

## What Is Playable

| Capability | Current browser implementation |
| --- | --- |
| Map and modes | Real street map, foreground GPS, explicit Raleigh/Durham Demo Mode |
| Encounters | Anonymous rarity-colored markers, localized POI/habitat eligibility, deterministic Eastern-day rotations |
| Proximity and density | 75 m interaction with bounded accuracy allowance; globally at most 7 markers in any 0.5-mile-radius circle |
| Artwork | All **51** creatures and logo, responsive lazy-loaded images, PNG and missing-art fallbacks |
| Signatures | All **12** have approved outdoor associations, scarce scheduling, shared-anchor rotation and density priority |
| Quizzes | Novice **3**, Intermediate **5**, Expert **7** questions; **2/3, 3/5, 4/7** correct to capture |
| Progress | Green/check or red/cross plus text; saved attempts/captures/daily escapes; separate real and Demo collections |
| Camera | Optional live video with 2D creature overlay, remembered opt-in, off/re-enable controls, equivalent no-camera play |
| Readings | **39** non-Signatures: 35 workbook primaries + 4 approved outside readings; **12** Signatures: only canonical project links |

All 51 have art, content and validated quizzes, **not guaranteed spawns today or
everywhere**. Five Healthcare-only ordinary forms lack accepted public anchors;
WakeMed/RAL-05 intentionally has no encounters. [Coverage](mobile/web/coverage.json)
is a fixed-date 32-day audit, not a live promise. Discovered entries and encounter
inspection unlock details; the Modédex does not reveal unencountered identities.

## Architecture and Resources

```text
data/raw + reviewed data/config + data/research
    -> Python ingestion / labeling / cells / zones / curation
    -> data/processed: canonical snapshots, provenance and QA tables

modedex.yaml -> build_modedex.py -> modedex.json
committed masters -> build_game_art.py -> art.json + public/art
canonical data + safety approvals -> build_web_runtime.py -> runtime.json
approved mappings + decision ledger -> build_modedex_learning.py -> learning.json
    -> mobile/web: React + TypeScript + Vite + Leaflet/Turf
    -> static web artifact + browser-local progress
```

Stable species/OSM POI IDs join layers; names are not keys. Human curation stays
separate from scores. WGS84 geography is retained; analysis uses EPSG:2264.
Explicit parent precedence resolves inherited overlaps without deleting geometry.
Cells remain the analytical source of truth; zones are gameplay abstractions.
Public-approach filters and reviewed Signature placements take priority over
filling every region with encounters.

World generation is deterministic, not live ML inference. Readings are separate
from world identity, so adding them cannot reroll encounters or reset progress.
Questions/difficulty are snapshotted; reload or mode changes cannot reset answers
or escapes. External readings are linked, not embedded or prefetched.

**Native is not the shipped game.** `mobile/src/` is an incomplete Expo/React
Native foundation: onboarding, foreground permission, safety, native map and
placeholder Modédex/encounters. Its web route loads the browser component; this
does not implement native captures or camera encounters. The playable code is
in `mobile/web/`. [Native setup](mobile/README.md) describes device signing and
Android map-key requirements, unnecessary for browser play.

## Responsible AI, XAI and Teaching Use

The progression is **real-world job -> AI task -> representative techniques ->
input/output -> limitations/biases -> explainability**. Eight families and nine
habitats make these concepts approachable. Expert questions use the entry's
supported inspection and limitation fields, not invented telemetry or claims
that an algorithm exclusively belongs to one task.

For a class session: use Demo, inspect a creature's job/data, complete a quiz,
follow its reading, and discuss a failure mode or explanation. Compare a general
form with a Signature's documented example. Component lessons are labeled
supporting concepts, not complete-system explanations. Quiz success is gameplay,
not validated learning efficacy; no assessment data goes to an instructor.

Preferred readings come from Explainable AI Workbook, Data Science Workbook and
Deep Learning Workbook. The four approved gaps use MIT News (Wardray), IBM Think
(Shiftshark and Parcelprawn) and Optibus (Routeopus); these remain clearly
attributed outside references. Exact approved lesson URLs and scope labels are
documented in the [learning overlay guide](mobile/web/LEARNING_LINKS.md), not
invented from creature names.

**Habitat labels and special destinations describe educational context, not
proof that an organization deploys an AI system.** Signature citations preserve
their documented project/use case and scope. Representative algorithms are not
deployed-architecture claims. Institution/system-level examples do not imply
installation at a player's coordinate. Signatures retain only project links.

## Privacy, Safety and Known Limits

- No account, project backend, analytics, GPS history or camera recording/uploads.
  Latest fixes are transient. Video stops on exit/background and can always be
  disabled; a saved preference is not browser permission. See
  [camera behavior](mobile/web/CAMERA_PREFERENCE.md).
- Browser storage holds captures, answers, acknowledgment and preferences.
  Clearing it/changing browser loses progress; corrupt/blocked storage fails
  explicitly. No cloud sync, anti-cheat or server-enforced clock is claimed.
- Coordinates associate places; they do not instruct entry or exact-point
  occupation. Signs override markers. Outdoor safety evidence is desk research,
  not field certification or live closure detection. Never obstruct passengers,
  emergency services or sensitive facilities.
- OSM tiles, publisher links and hosting use third-party networks. Providers can
  see request metadata. Internet/attribution are required; no offline-launch or
  production-scale OSM tile-service promise is made.
- Mobile WebKit automation is not physical iPhone Safari acceptance. Real GPS,
  camera, accessibility and safe paths need human/device review. No live AI,
  evolution mechanics, multiplayer or native feature parity. Dependency
  advisories remain; functional checks are not a security waiver.

## Data, QA and Further Reading

The original region, Modédex and habitat-zone data READMEs are frozen historical
references in an existing integrity fixture. Their bytes are preserved here.
Use the new reproduction guide for current commands: in particular the canonical
zone build **requires `--allow-inherited-region-overlaps`**, and no root-level
`modedex.yaml` import copy is needed. Historical statements that this data layer
does not implement gameplay do not describe the current browser app.

- [Reproduction and geospatial QA index](data/REPRODUCIBILITY.md).
- [Regions](data/README.md), [POIs](data/POI_README.md),
  [habitat labeling](data/HABITAT_README.md), [cells](data/HABITAT_CELLS_README.md),
  [zones](data/HABITAT_ZONES_README.md), [resolution](data/REGION_RESOLUTION_README.md).
- [Candidate scoring](data/SPECIAL_POI_CANDIDATES_README.md),
  [human curation](data/SPECIAL_POI_CURATION_README.md),
  [Modédex](data/MODEDEX_README.md), [artwork](assets/ARTWORK_README.md).
- [Playable app](mobile/web/README.md), [quizzes](mobile/web/QUIZZES.md),
  [Signature safety](mobile/web/SIGNATURE_ENCOUNTERS.md),
  [learning overlay](mobile/web/LEARNING_LINKS.md), [web QA](mobile/web/QA.md).

OSM-derived data requires OSM/ODbL attribution; city/university data retains its
source terms. Owner-supplied artwork is committed for this artifact, not a
general redistribution license. Linked publishers retain their content. Review
the provenance READMEs before reuse. Historical milestone handoffs are not the
current feature inventory; the [product specification](https://github.com/maladroitcat/modemon-go/issues/9)
also describes future work, not only implemented features.
