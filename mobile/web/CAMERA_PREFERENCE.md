# Camera preference (issue 25)

Only the playable web encounter scene requests a camera. A fresh browser has no
opt-in: the map, onboarding, discovered entries and quizzes never open it.
The first successful **Enable camera** action remembers `enabled` at
`modemon-go:playable:camera-preference:v1`. This single value is separate from
captures, scores, daily escapes and real/Demo storage. It applies to both modes.

A later encounter automatically attempts video-only camera access when this
preference is enabled and the page is visible. This is an application preference,
**not a browser permission grant**. Safari may prompt again, deny the request,
require a gesture for playback, or have no suitable device. No native prompt is
overridden. A failed request/playback falls back and disables future automatic
attempts until a new explicit enable. There is no retry loop.

**Use without camera** always remains available, including during a permission
prompt. It immediately stops tracks and remembers disabled for future scenes.
**Enable camera** permits a later reversal. Unavailable storage is handled
conservatively: camera use still works after a gesture, but the status explains
that the preference could not be saved. Stored enabled is not trusted for auto
start if storage cannot save a later reversal. Off also has an in-memory guard.

Requests are single-flight across scene replacements. An unresolved old prompt
is not adopted by a new scene; its eventual stream is stopped. Generation checks
prevent late success/rejection from overriding an explicit off choice or updating
an exited scene. A pending request leaves no-camera controls usable.

Page hide, backgrounding, leaving the scene, inspecting the creature and unmount
stop all video tracks and clear the video element. Returning to the foreground
does not silently restart the same scene; Enable camera remains available. A new
encounter may use the remembered opt-in. No audio, frames, coordinates or media
are recorded, uploaded or persisted. Creature artwork is unchanged.

Run `npm run check:playable`, `npm run test:playable` and
`npm run test:playable:e2e` from `mobile/`. Unit tests cover storage, async races,
late playback, denial, cleanup and single-flight requests; Chromium and mobile
WebKit tests cover first opt-in, subsequent scenes, reload, off and re-enable.
Physical iPhone Safari permission/foreground behavior still requires device QA.
This feature is merged in main and included in the existing public preview.
See [current QA](QA.md) for verified deployment identity and the remaining
physical-device checks; this document describes behavior, not a deployment tool.
