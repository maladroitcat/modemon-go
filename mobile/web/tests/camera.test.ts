import { test } from "node:test";
import assert from "node:assert/strict";
import { CameraPreferences, EncounterCamera, cameraPreferenceKey, type CameraState } from "../src/camera.ts";

function deferred<T>() {
  let resolve!: (value: T) => void, reject!: (error: Error) => void;
  const promise = new Promise<T>((ok, fail) => { resolve = ok; reject = fail; });
  return { promise, resolve, reject };
}
function fixture() {
  const values = new Map<string, string>([["progress", "unchanged"]]);
  const storage = { getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => { values.set(key, value); } };
  const preferences = new CameraPreferences(() => storage);
  const request = deferred<MediaStream>();
  const playback = deferred<void>();
  let requests = 0, stops = 0, hidden = false, available = true, slowPlay = false;
  const stream = { getTracks: () => [{ stop: () => { stops++; } }] } as unknown as MediaStream;
  const video = { srcObject: null as HTMLVideoElement["srcObject"], play: () => slowPlay ? playback.promise : Promise.resolve() };
  const states: CameraState[] = [];
  const gate = { busy: false };
  const create = () => new EncounterCamera({ preferences, video: () => video,
    getUserMedia: (constraints) => { assert.equal(constraints.audio, false); requests++; return request.promise; },
    available: () => available, hidden: () => hidden, changed: (s) => states.push(s), gate });
  return { values, storage, preferences, request, playback, stream, video, states, gate, create,
    get requests() { return requests; }, get stops() { return stops; },
    set hidden(value: boolean) { hidden = value; }, set available(value: boolean) { available = value; },
    set slowPlay(value: boolean) { slowPlay = value; } };
}

test("unset, corrupt, disabled or unavailable storage never auto-starts; unrelated progress is untouched", async () => {
  for (const value of [null, "broken", "disabled"]) {
    const f = fixture();
    if (value) f.values.set(cameraPreferenceKey, value);
    await f.create().autoStart();
    assert.equal(f.requests, 0);
    assert.equal(f.values.get("progress"), "unchanged");
  }
  const preferences = new CameraPreferences(() => { throw Error("blocked"); });
  assert.equal(preferences.read(), "unset");
  assert.equal(preferences.write("enabled"), false);
  assert.equal(preferences.read(), "unset");
  assert.equal(preferences.write("disabled"), false);
  assert.equal(preferences.read(), "disabled");
});

test("only successful explicit approval remembers enabled; next scene auto-starts; off and re-enable persist", async () => {
  const f = fixture(), first = f.create();
  const started = first.start();
  assert.equal(f.values.get(cameraPreferenceKey), undefined);
  f.request.resolve(f.stream); await started;
  assert.equal(f.preferences.read(), "enabled");
  assert.equal(f.states.at(-1)!.active, true);
  first.dispose();
  const second = f.create(); await second.autoStart();
  assert.equal(f.requests, 2);
  second.disable();
  assert.equal(f.video.srcObject, null);
  assert.equal(f.preferences.read(), "disabled");
  const third = f.create(); await third.autoStart();
  assert.equal(f.requests, 2);
  await third.start();
  assert.equal(f.preferences.read(), "enabled");
  third.dispose();
  assert.equal(f.values.get("progress"), "unchanged");
});

test("permission rejection disables auto attempts, does not loop, permits a later explicit retry", async () => {
  const f = fixture(); f.values.set(cameraPreferenceKey, "enabled");
  const camera = f.create(), started = camera.autoStart();
  f.request.reject(Error("Denied")); await started;
  assert.equal(f.preferences.read(), "disabled");
  await camera.autoStart(); await f.create().autoStart();
  assert.equal(f.requests, 1);
  await camera.start();
  assert.equal(f.requests, 2);
  assert.match(f.states.at(-1)!.status, /unavailable or denied/);
});

test("off while a prompt is pending wins over late success and blocks overlapping requests", async () => {
  const f = fixture(), camera = f.create(), started = camera.start();
  await camera.start();
  camera.disable();
  await camera.start();
  assert.equal(f.requests, 1);
  f.request.resolve(f.stream); await started;
  assert.equal(f.stops, 1);
  assert.equal(f.preferences.read(), "disabled");
  assert.equal(f.video.srcObject, null);
  assert.equal(f.states.at(-1)!.pending, false);
  assert.match(f.states.at(-1)!.status, /Non-camera/);
});

test("unmount and immediate replacement cannot overlap prompts or adopt a stale stream", async () => {
  const f = fixture(); f.values.set(cameraPreferenceKey, "enabled");
  const first = f.create(), started = first.autoStart();
  first.dispose(); const count = f.states.length;
  const second = f.create(); await second.autoStart();
  assert.equal(f.requests, 1);
  assert.match(f.states.at(-1)!.status, /previous camera request/);
  f.request.resolve(f.stream); await started;
  assert.equal(f.stops, 1);
  assert.equal(f.states.length, count + 1);
  await second.start();
  assert.equal(f.requests, 2);
  second.dispose();
});

test("hide pauses live camera without revoking preference; no foreground automatic retry", async () => {
  const f = fixture(), camera = f.create(), started = camera.start();
  f.request.resolve(f.stream); await started;
  f.hidden = true; camera.pause();
  assert.equal(f.stops, 1); assert.equal(f.video.srcObject, null);
  assert.equal(f.preferences.read(), "enabled");
  f.hidden = false;
  assert.equal(f.requests, 1);
  camera.dispose(); assert.equal(f.stops, 1);
});

test("hide, off or unmount during delayed playback stop tracks and never persist late approval", async () => {
  for (const action of ["hide", "off", "unmount"] as const) {
    const f = fixture(); f.slowPlay = true;
    const camera = f.create(), started = camera.start();
    f.request.resolve(f.stream); await Promise.resolve();
    if (action === "hide") { f.hidden = true; camera.pause(); }
    if (action === "off") camera.disable();
    if (action === "unmount") camera.dispose();
    f.playback.resolve(); await started;
    assert.equal(f.stops, 1); assert.equal(f.video.srcObject, null);
    assert.notEqual(f.preferences.read(), "enabled");
  }
});

test("late rejection after off never overwrites off status; playback denial releases tracks", async () => {
  const f = fixture(), camera = f.create(), started = camera.start();
  camera.disable(); f.request.reject(Error("late denial")); await started;
  assert.match(f.states.at(-1)!.status, /Non-camera/);
  const g = fixture(); g.slowPlay = true;
  const playback = g.create().start(); g.request.resolve(g.stream); await Promise.resolve();
  g.playback.reject(Error("Autoplay blocked")); await playback;
  assert.equal(g.stops, 1); assert.equal(g.preferences.read(), "disabled");
});

test("unavailable devices never request; write-blocked stored opt-in cannot auto-open after reload", async () => {
  const f = fixture(); f.available = false;
  await f.create().start(); assert.equal(f.requests, 0);
  f.values.set(cameraPreferenceKey, "enabled");
  f.storage.setItem = () => { throw Error("write blocked"); };
  assert.equal(new CameraPreferences(() => f.storage).read(), "unset");
  f.preferences.write("disabled");
  assert.equal(f.preferences.read(), "disabled");
});
