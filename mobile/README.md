# Modémon GO Native Foundation And Playable Web

For the public playable browser experience from issue #15, use
**https://modemon-go-playable.astralgnat19.chatgpt.site** and read
[web/README.md](web/README.md). Web progress, camera, and gameplay are documented
separately; this native guide does not claim that they exist on native.

Implements [task #10](https://github.com/maladroitcat/modemon-go/issues/10), following
the approved [product contract #9](https://github.com/maladroitcat/modemon-go/issues/9).
The foundation and subsequent browser work are merged into main through PR #32.
Historical foundation/playable branches are not setup inputs. Only the web target
reads the generated runtime bundle; native modules do not import browser gameplay
data. Native gameplay remains incomplete despite its playable web route.

For a clean checkout, reproducible content/art builds and browser checks, start
with [the root guide](../README.md#how-to-run-and-reproduce). The browser has 51
approved creature images and logo, 12 Signature encounters, three difficulties
and approved readings. The assets and masters are committed; no untracked art
or private snapshot is needed.

## Toolchain and installation

- Node **24.22.0** is recorded in `.node-version`; SDK 58 needs at least 22.13.x.
- Expo **58.0.14**, React Native **0.88.0**, React **19.3.0**, Expo Router
  **58.0.23**, `expo-location` **58.0.17**, and `react-native-maps` **1.29.11**.
- Native AsyncStorage persists only safety acknowledgment. Native encounter and
  Modédex views are placeholders; approved creature artwork is used by the browser
  game, not an assertion of native encounter support. Lucide supplies UI icons.

Versions were checked against the [SDK 58 reference](https://docs.expo.dev/versions/v58.0.0/),
[Router installation guide](https://docs.expo.dev/router/installation/),
[native-map guide](https://docs.expo.dev/versions/v58.0.0/sdk/map-view/), and
[location guide](https://docs.expo.dev/versions/v58.0.0/sdk/location/), then installed
through `expo install`. All direct dependencies are exact pins; commit the
`package-lock.json` and use `npm ci`. Do not run a forced audit fix or mix arbitrary
React Native / Expo versions. System Node 20 is not sufficient for this app.

```sh
cd mobile
# Select Node 24.22.0 with your Node version manager first.
npm ci
npm start
```

For Expo web QA: `npm run web -- --port 8082`. It now loads the same playable game
as `npm run play:web` (port 5173), including a real Leaflet street map. Browser
checks do not prove that native iOS/Android map gestures work.

## Physical-device setup

Use a physical iOS or Android device for the actual native map/GPS checks.

1. Install the Node version above. For local native builds, install the SDK 58
   compatible Xcode/iOS tools or Android SDK/JDK tools described in Expo's
   [environment setup](https://docs.expo.dev/get-started/set-up-your-environment/).
2. Choose approved app identifiers and set `IOS_BUNDLE_IDENTIFIER` and/or
   `ANDROID_APPLICATION_ID` in your local environment. These identifiers are not
   assigned by this PR. `.env.example` lists the available variables.
3. Android development binaries require a Google Maps SDK key restricted to the
   application's package and signing-certificate fingerprint. Set
   `ANDROID_GOOGLE_MAPS_API_KEY` locally or in your build service. `app.config.ts`
   passes it to the map config plugin only when supplied. Do not commit keys.
   iOS uses Apple Maps by default, without a Google Maps key.
4. Build/install a development client with `npx expo run:ios --device` or
   `npx expo run:android --device`. These commands generate ignored native folders.
   Alternatively use `npx eas-cli@latest build --profile development --platform ios`
   (or `android`) after the project owner configures EAS, signing, and the same
   environment variables. Account/signing setup and potentially paid cloud builds
   are deliberately not performed automatically.
5. Run `npm start`, connect phone and development computer to the same trusted
   network, and open the development-client URL/QR. When prompted by iOS, allow
   local-network access for the development server as appropriate.
6. Test the complete checklist in [QA.md](QA.md), including denied permission,
   returning from Settings, disabled GPS, pan/zoom/recenter, and backgrounding.

If using Expo Go instead, first verify a compatible SDK 58 build at
[expo.dev/go](https://expo.dev/go). Do not assume the installed store app supports
this project. Use `npx expo start --go` only with a compatible build; development
binaries are the reliable path when versions differ. Neither is needed for the
public browser artifact.

## Onboarding, safety, and privacy

- Each cold launch opens Welcome. Start Playing checks existing **foreground**
  permission without prompting again if already granted. Otherwise it explains
  permission before the user explicitly requests it. Denial, permanent denial,
  unsupported APIs, disabled services, and a slow first fix are recoverable.
- Location may be skipped; safety may not. A checkbox plus Enter map is required
  before any gameplay tab, including a direct/deep link. `Stack.Protected` gates
  the tabs. Root onboarding and the default `/map` route have distinct paths.
- The full notice covers traffic and crossings, driving/cycling, safe stopping,
  terrain/weather, private/restricted/sensitive locations, schools/hospitals,
  emergency access, venue hours, privacy, minors, and skipping inaccessible places.
  It remains available from Settings and the prominent map reminder.
- AsyncStorage key `modemon-go:safety-acknowledgment` stores **only**
  `{"version":1}`. Changing the notice version requires re-acknowledgment. Invalid,
  old, or unreadable state fails closed. On write failure, explicit agreement is
  valid for this session with a warning; the next launch asks again.
- GPS fixes are watched only after safety acknowledgment and while the app is active. The watcher is
  removed when backgrounded, and late subscription setup is also cleaned up.
  Only the latest fix exists in memory. It is cleared on backgrounding; there is
  no location storage, log, timeline, backend, account, analytics, or tracking SDK.
- Native configuration disables background location, foreground services,
  motion recognition, and iOS Always-location purpose descriptions. No camera
  permission is requested. Approximate device location is accepted.
- Street maps use the device's online map provider. Map providers may receive
  requests needed to supply the map under their own terms; the app does not claim
  that online maps work offline. No user data is sent to a project backend.

## Map and placeholders

On iOS/Android, a standard `react-native-maps` view starts at the available device
position and displays the native player-location indicator. Its initial camera
zoom is just a starting view, not a visibility radius, geofence, or movement
constraint. Users can pan/zoom normally and explicitly recenter. That native map
does not render regions, encounters or spawns; those exist in the browser game.

There are loading, permission-denied, GPS-unavailable, and map-startup timeout
states. The "Map not loading?" action lets the user report tile failure manually
because the native map API does not reliably expose individual tile-download
failure. Retry is available. The offline nearby-encounters list is visibly marked
**PLACEHOLDER**, contains no invented entries, and remains visible without tiles.
It is not yet the useful populated offline list described for a later milestone.

Modédex and Encounter are navigable placeholders, not an inventory, camera,
capture quiz, or an implicit implementation of the rest of #9.

## Checks

```sh
npm run typecheck
npm run lint
npm test
npx expo install --check
npx playwright install chromium
npm run test:e2e
npx expo export --platform all --output-dir dist
```

`npm run check` combines typecheck, lint, and the 18 Node tests. Playwright runs
five browser tests against localhost:8082 (starts the server if needed). It covers
denial, existing permission, safety gating, persisted/rejected storage, direct
links, tab navigation, and narrow/landscape/desktop onboarding. The separate web
experience has opt-in Demo Mode; simulated coordinates are never called real GPS.
Native device coordinates are not simulated at runtime.

TypeScript explicitly includes owned source/tests and excludes generated exports:
the minified production bundle is not TypeScript input. Build outputs, test
screenshots/traces, generated native projects, keys, and dependencies are ignored.
The mobile CI workflow repeats the checks, browser tests, compatibility check, and
three-platform JS export. JS export is **not** a signed native build or device pass.

Python regression checks run from the repository root, using the pinned Python
environment: `.venv/bin/python -B -m unittest discover -s tests -v`.

## Limitations and next task

See [QA.md](QA.md) for actual results and unverified native acceptance criteria.
Upstream dependency advisories remain; they are not waived by a successful Expo
Doctor result. The generated launcher icons are Expo template placeholders with
the template license retained in `LICENSE`, not approved game artwork. Approved
browser assets and masters are committed separately; concepts are not consumed.

The compact read-only bridge and browser encounter/capture loop are under
[web/](web/README.md). Native gameplay expansion remains future work. Neither
target adds accounts/backend, GPS history, telemetry or unapproved Signature
assignments. [Current browser QA](web/QA.md) is separate from the
[historical native handoff](QA.md) and physical native acceptance checklist.
