# Approved Modedex Learning Links

Issue #30 adds readings to encountered/discovered non-Signature entries only.
It does not change introductions, quizzes, world identities, encounters, camera
preferences, artwork, geography, or saved progress.

## Approval and Data Flow

`data/config/modedex_learning_links.yaml` preserves all 45 workbook mappings,
including original scope, confidence, and historical review metadata. Its new
authorization metadata records the owner's approval for non-Signature UI use.
Of these matches, 35 belong to non-Signatures. Existing matches for Signatures
remain in research provenance but never become supplementary UI links.

Four additional non-Signature readings are explicitly approved in issue #30:
Wardray (MIT News), Shiftshark and Parcelprawn (IBM Think), and Routeopus
(Optibus). They remain attributed as outside references, not workbook lessons.
The separate owner-decision ledger binds approval to the exact species and URL;
the previous Routeopus hold remains historical. HTTP evidence cannot approve a
reference. A new or changed source needs new owner approval.

```text
approved workbook mappings + outside references + owner decision ledger
    -> scripts/build_modedex_learning.py
    -> mobile/web/src/data/learning.json (39 stable species IDs)
    -> learning.ts -> LearningLinks.tsx -> existing DexEntry.tsx
```

The generated JSON is read-only application data, not a new source of canon.
Its deterministic source hashes detect stale builds. No learning content enters
the gameplay runtime fingerprint, so adding readings cannot reroll spawns or
invalidate saved encounters, quizzes, captures, or daily escapes.

All 39 non-Signatures have a primary reading, with a distinct secondary lesson
where already provided. Component matches are explicitly labeled supporting
concepts rather than complete-system explanations. All 12 Signatures retain
only the existing canonical real-project section/link, unchanged. A hard stage
gate prevents supplementary learning sections even if a Signature has a
historical workbook mapping.

## UI and Safety

The existing Game discovery/encounter gate is unchanged. The learning component
uses canonical IDs only, with no name-based guesses or links for unknown IDs.
Locked entries do not acquire a new browsing route. This is UI discovery gating,
not a claim that public static game data is encrypted or secret.

Readable article titles and publisher names are visible. Partial-match scope is
shown below the link. Links have 48px minimum tap targets, visible keyboard focus,
screen-reader labels announcing new-tab behavior, decorative icons hidden from
assistive technology, and `target="_blank" rel="noopener noreferrer"`.
React renders text normally; no HTML injection or embedded publisher content is
used. Neither link rendering nor browsing prefetches third-party lessons.

Both build-time and runtime checks reject unsafe URLs. Runtime navigation is
limited to the exact URLs emitted from approved inputs, not arbitrary pages on
an allowed publisher domain. External pages remain outside the game's control;
source availability, publisher accessibility, and content can change.

## Rebuild and Checks

```sh
python3 -B scripts/build_modedex_learning.py
python3 -B -m scripts.build_workbook_research_review
python3 -B -m scripts.review_external_learning_references
python3 -B -m unittest discover -s tests -v
cd mobile
npm run check
npm run check:playable
npm run test:playable
npm run test:playable:e2e
npm run build:playable
```

CI rebuilds the overlay and rejects a committed artifact that differs. Production
builds validate its source hashes and emit `deployment-provenance.json` with the
application commit and JS/CSS hashes. This is distinct from Sites' packaging
repository commit and hosting version.

Public-host regression, with local servers stopped:

```sh
PLAYABLE_BASE_URL=https://modemon-go-playable.astralgnat19.chatgpt.site \
EXPECTED_APPLICATION_SHA=<verified-feature-commit> npm run test:playable:e2e
```

Tests check all 39 learning entries, 12 Signature-only sections, safe exact URLs,
locked entries, responsive 320px/393px/landscape layouts, tap targets, keyboard
new-tab navigation for a workbook, an outside reading, and a Signature, and
unchanged progress. Existing camera, quiz, artwork, spawning, capture, and escape
regressions still run. Publisher navigation is intercepted only in click-through
tests to avoid making third-party availability an app test; the public app itself
and deployed asset hashes are fetched from the actual HTTPS host.

Browser QA uses Chromium and WebKit with iPhone-sized viewports. It is not a claim
of testing on a physical iPhone or guaranteeing third-party page accessibility.
Preview deployment is authorized; this branch must not merge automatically.
