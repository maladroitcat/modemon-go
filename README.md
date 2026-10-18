# Modémon GO

A location-based educational game about the AI and machine-learning tasks that
appear in everyday environments. Gameplay context is not a claim that a particular
organization deploys a particular AI system.

The approved product contract is [issue #9](https://github.com/maladroitcat/modemon-go/issues/9).
The first mobile implementation is scoped by [issue #10](https://github.com/maladroitcat/modemon-go/issues/10).
Product decisions in those issues are not all implemented features.

## Playable Browser Preview

**https://modemon-go-playable.astralgnat19.chatgpt.site** opens without login,
Expo Go, or a native build. Acknowledge safety, explicitly opt into Demo Mode for
remote testing, select an encounter, simulate walking to it, read the Modédex, and
answer three questions. Two correct captures; progress survives reload in the
same browser. Real GPS mode retains its proximity gate.

See [playable web documentation](mobile/web/README.md), [coverage](mobile/web/coverage.json),
and [QA](mobile/web/QA.md). Creature art and Signature encounters are not approved/
enabled. Physical iPhone Safari acceptance remains separate from automated WebKit.

## Native Mobile Foundation

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
credentials, privacy behavior, and acceptance checks. The web route loads the
playable browser experience; native routes and the native map remain unchanged.

```sh
cd mobile
npm run check
npx playwright install chromium
npm run test:e2e
npx expo install --check
npx expo export --platform all --output-dir dist
```

The native foundation still has placeholder encounter/Modédex screens. The public
web experience implements daily encounters, camera/non-camera play, capture quizzes,
and browser-local collections. Neither implementation stores GPS history or uses
a player account, project backend, or telemetry.

## Canonical research and content

Python pipelines and human-edited configuration remain authoritative:

- [Regions](data/README.md) and [POIs](data/POI_README.md).
- [Habitat labeling](data/HABITAT_README.md), [cells](data/HABITAT_CELLS_README.md),
  and [zones](data/HABITAT_ZONES_README.md).
- [Gameplay region resolution](data/REGION_RESOLUTION_README.md).
- [Special-POI candidates](data/SPECIAL_POI_CANDIDATES_README.md) and
  [human curation](data/SPECIAL_POI_CURATION_README.md).
- [Canonical Modédex](data/MODEDEX_README.md): YAML content validated into JSON.

`scripts/build_web_runtime.py` generates a compact, hash-versioned browser bridge
from these read-only inputs. Raw research inputs and contribution tables are not
shipped. Canonical content and analytical geometry remain unchanged.

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
