# Task 001 QA handoff

**Historical native-foundation record, not the current browser feature list.**
The original results and limitations below are retained as milestone evidence.
Subsequent browser gameplay, 51 approved artworks, 12 Signature encounters,
three quiz modes, camera preference and learning links are merged through PR #32.
Use [current web QA](web/QA.md), [clean-checkout setup](../README.md#how-to-run-and-reproduce)
and [native setup](README.md) for today's workflow. Native gameplay placeholders
and physical-device acceptance limits still apply; old test/advisory counts are
not current release metrics. The former proposed data-bridge task is complete
for web, not a remaining prerequisite.

Scope: [#10](https://github.com/maladroitcat/modemon-go/issues/10), governed by
[#9](https://github.com/maladroitcat/modemon-go/issues/9). Branch
`dev/mobile-foundation`, based on updated `main` at
`b10409d9a7a1453b05eb435709544db40a8080e7`.

## Implemented

- Isolated Expo 58 / React Native / TypeScript / Expo Router application.
- Branded Welcome and Start Playing; a foreground-location explanation, reuse of
  existing permission, explicit permission request, retry/settings guidance, and
  continuation without location.
- Mandatory readable safety notice and explicit checkbox. Gameplay routes cannot
  bypass the gate through deep links. Versioned acknowledgment is local-only;
  invalid/read-failed state requires agreement again. Write failure is visibly
  session-only. A brief reminder remains on subsequent map sessions.
- Map, Modedex, Encounter, Settings, and a later-accessible complete safety notice.
- iOS/Android native standard street map, initial device-location camera, player
  indicator, unrestricted pan/zoom, explicit recenter, loading/error/retry states.
- Explicit offline-nearby-list placeholder without invented entries or spawns.
- Accessible controls, scrolling long-form safety text, short-screen layout, and
  narrow/landscape/desktop browser checks.
- Exact dependency pins/lockfile, local/EAS development setup instructions,
  regression tests, mobile CI, meaningful root README, and artifact/secret ignores.

## Actual local checks

| Check | Result |
|---|---|
| Required baseline `python3 -B -m unittest discover -s tests -v` | Environment failure: system Python lacks `rfc3986_validator`; 68 tests passed and the Modedex test module could not import. No Python code was changed to hide this. |
| Project `.venv/bin/python -B -m unittest discover -s tests -v` before implementation | 97 passed, no skips |
| Same virtualenv suite after implementation | 97 passed, no skips |
| Clean `npm ci` | Passed with pinned lockfile; audit advisories remain below |
| `npm run typecheck` | Passed |
| `npm run lint` | Passed, zero lint errors/warnings |
| `npm test` | 18 passed, no skips |
| `npx expo install --check` | Passed; SDK-compatible dependencies |
| `expo-doctor` (1.21.5) | 20/20 checks passed |
| `npm run test:e2e` | 5 Chromium tests passed, no unhandled browser page errors |
| `expo export --platform all --output-dir dist` | iOS, Android, web JS exports passed; native bundles approximately 4.9 MB each |
| `expo config --type introspect --json` | Passed; iOS When In Use purpose present, no Always purpose or background-location mode; Android background/foreground-service-location permissions marked for removal |
| Source integrity | All 219 protected data/output/Python/test/art files byte-for-byte unchanged |

Node 24.22.0 was used in isolation; the existing system Node 20 and Python
installation were not replaced. Node's test runner emits a benign module-type
detection warning for TypeScript ES-module tests. Existing Python geospatial
tests emit pyproj/NumPy deprecation warnings. Neither warning was suppressed by
weakening a check.

The five browser cases cover denied location and all tabs, pre-granted location
and reload persistence, blocked direct gameplay links, storage failures, and
320x640 / 844x390 / 1280x800 layouts. Screenshots were visually inspected at mobile
size. Screenshots, traces, exports, dependencies, and generated native folders
remain ignored, not committed. The native-map browser fallback is intentional.

## Security limitation: not a production-release approval

Online `npm audit` / clean installation reports **27 vulnerable dependency nodes:
20 high, 7 moderate**, inherited through Expo/React Native tooling. This count
includes transitive chains; it is not 27 distinct app-code vulnerabilities.
Root advisories reported include:

- `braces`: [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm).
- `node-forge`: [GHSA-86w9-cpqp-85rv](https://github.com/advisories/GHSA-86w9-cpqp-85rv).
- `uuid`: [GHSA-w5hq-g745-h8pq](https://github.com/advisories/GHSA-w5hq-g745-h8pq).

The compatible `npm audit fix` was attempted; these remained. npm suggests a
forced Expo downgrade to SDK 44, which was deliberately **not** performed. No
unverified overrides or compatibility-check exclusions were added. Offline
audit output is not evidence that advisories disappeared. This branch is for
development/review, not a security waiver or production distribution approval.
Reassess upstream fixes before releasing. Expo Doctor does not replace an audit.

## Native acceptance still requires a physical device

No iOS simulator/Xcode device tooling or connected phone was available here
(`xcrun simctl` is unavailable). No signed native build, live-device map, map-tile
download, device pan/zoom, real sensor fix, or OS Settings round trip was claimed
as passed. JavaScript export and browser simulations are not substitutes.

Before merging as fully device-accepted, a reviewer should run these on iOS and
Android with the compatible development client:

- [ ] First launch: foreground prompt follows the explanation; no background,
  motion, camera, or unrelated runtime permission prompt.
- [ ] Grant, deny, permanently deny, and approximate/Allow Once cases; retry and
  return from Settings; disabling location services; delayed GPS acquisition.
- [ ] Safety text is readable with large accessibility fonts and screen reader;
  checkbox announces checked state; Enter map is unavailable without agreement.
- [ ] Relaunch respects acknowledgment, keeps the map reminder, and opens the
  complete notice through Settings. Changed/corrupt notice version asks again.
- [ ] Native map loads actual tiles and the player indicator, starts at available
  device location, pans and zooms freely, and recenters without locking the camera.
- [ ] Poor connectivity and map-startup failure permit retry; nearby placeholder
  remains accessible. No fake encounters appear.
- [ ] Backgrounding removes the watcher; foregrounding refreshes permission and
  location. No coordinates are persisted or logged.
- [ ] Map, Modedex, Encounter, Settings and Back behave correctly in portrait,
  landscape, and device accessibility settings without overlapping controls.

## Decisions and resources for the product owner

1. Provide approved iOS/Android application identifiers, signing/EAS ownership,
   and a restricted Android Maps SDK key/billing configuration for native builds.
   No credentials or final identifiers were invented or committed.
2. Confirm SDK 58-compatible device distribution. Store Expo Go rollout is not
   assumed complete; use the documented development-client path if needed.
3. Review the safety copy and persistence policy: write failure permits explicitly
   acknowledged play for that session only, with a warning and a new notice on the
   next launch. Read/corrupt/version failure never bypasses acknowledgment.
4. Review the upstream dependency risk before any broader or production release;
   do not infer security approval from passing functional checks.

The next proposed implementation task is the compact, versioned, validated data
bridge from #9, only after review. There is no automatic data migration, backend,
login, telemetry, GPS history, spawn engine/rules/markers, Signature assignment,
camera, quiz, captures, or final artwork in this branch. No product milestone or
physical-device acceptance is marked complete solely from this handoff.

## Changed-file scope

Root changes are `README.md`, `.gitignore`, and the new
`.github/workflows/mobile.yml`. Everything else added is under `mobile/`:

- Configuration: `package.json`, `package-lock.json`, `.npmrc`, `.node-version`,
  `.gitignore`, `.env.example`, `app.json`, `app.config.ts`, `eas.json`,
  `tsconfig.json`, `eslint.config.js`, `playwright.config.ts`.
- Documentation/template attribution: `README.md`, `QA.md`, `LICENSE`.
- Template launcher/splash bitmaps: `assets/*.png`; no existing concept art used.
- Routes: `src/app/_layout.tsx`, `index.tsx`, `safety.tsx`, and
  `(tabs)/{_layout,map,modedex,encounter,settings}.tsx`.
- Components: `src/components/{ui,LocationPermission,SafetyNotice}.tsx`,
  `MapSurface.tsx`, `MapSurface.native.tsx`, `map-props.ts`.
- State/content/logic: `src/state/AppState.tsx`, `src/content/safety.ts`,
  `src/lib/{onboarding,location}.ts`.
- Tests: `tests/{config,onboarding,location}.test.ts`, `e2e/onboarding.spec.ts`.

No tracked `data/`, `output/`, Python `scripts/` or `tests/` file is changed.
The user's existing untracked root `assets/` directory is preserved and excluded
from this PR, not deleted or quietly folded into the mobile project.
