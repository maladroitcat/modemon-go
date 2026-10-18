# Modémon GO

A location-based educational game about the AI and machine-learning tasks that
appear in everyday environments. Gameplay context is not a claim that a particular
organization deploys a particular AI system.

The approved product contract is [issue #9](https://github.com/maladroitcat/modemon-go/issues/9).
The first mobile implementation is scoped by [issue #10](https://github.com/maladroitcat/modemon-go/issues/10).
Product decisions in those issues are not all implemented features.

## Mobile foundation

`mobile/` is an independent Expo + React Native + TypeScript app using Expo
Router. It contains Welcome / Start Playing, foreground-location permission with
denial fallback, mandatory safety acknowledgment, a native street map, and basic
Map, Modédex, Encounter, and Settings navigation.

```sh
cd mobile
# Use Node 24.22.0 (mobile/.node-version), then:
npm ci
npm start
```

See [mobile/README.md](mobile/README.md) for physical-device setup, native map
credentials, browser-preview limitations, privacy behavior, and acceptance checks.
The browser preview intentionally does not pretend to render a native map.

```sh
cd mobile
npm run check
npx playwright install chromium
npm run test:e2e
npx expo install --check
npx expo export --platform all --output-dir dist
```

There are no spawns, active encounters, region rendering, capture mechanics,
camera access, accounts, backend, telemetry, or bundled analysis datasets in this
foundation. Modédex, Encounter, and the offline nearby list are explicit
placeholders. Only the safety-notice version is persisted; no GPS history is saved.

## Canonical research and content

Python pipelines and human-edited configuration remain authoritative:

- [Regions](data/README.md) and [POIs](data/POI_README.md).
- [Habitat labeling](data/HABITAT_README.md), [cells](data/HABITAT_CELLS_README.md),
  and [zones](data/HABITAT_ZONES_README.md).
- [Gameplay region resolution](data/REGION_RESOLUTION_README.md).
- [Special-POI candidates](data/SPECIAL_POI_CANDIDATES_README.md) and
  [human curation](data/SPECIAL_POI_CURATION_README.md).
- [Canonical Modédex](data/MODEDEX_README.md): YAML content validated into JSON.

The mobile app does not import these datasets yet. A compact, versioned data
bridge is a separate future task; do not ship raw research inputs or contribution
tables inside the app.

With Python 3.12 and the pinned requirements installed in your project environment:

```sh
python3 -m pip install -r requirements.txt
python3 -B -m unittest discover -s tests -v
```

Use `.venv/bin/python` when working in the existing local project virtualenv.
All canonical analysis files and curated safety exclusions must be preserved.

## Safety and review

The real world comes first. The app requires a versioned safety acknowledgment,
keeps the complete notice in Settings, and displays a brief reminder on each map
session. Native-device behavior and public-play suitability require human review;
a browser test or successful JavaScript export is not a device/field-test pass.
See [mobile/QA.md](mobile/QA.md) for checks, limitations, and product-owner decisions.
