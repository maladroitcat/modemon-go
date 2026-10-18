import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import {
  answerQuestion,
  beginAttempt,
  buildWorld,
  emptyProgress,
  interaction,
  progressKey,
  questionsFor,
  readProgress,
  type Runtime,
} from "../src/engine.ts";
import {
  approximateDistance,
  extraLocationSafety,
  markerLabel,
  placeLabel,
  proximityCopy,
  publicLocationSafety,
  regionLabel,
} from "../src/presentation.ts";
const data = JSON.parse(
  readFileSync(new URL("../src/data/runtime.json", import.meta.url), "utf8"),
) as Runtime;
const baseline = JSON.parse(
  readFileSync(
    new URL("./fixtures/mvp-gameplay.json", import.meta.url),
    "utf8",
  ),
);
const digest = (value: unknown) =>
  createHash("sha256").update(JSON.stringify(value)).digest("hex");
const world = buildWorld(data, "2026-10-17"),
  spawn = world[0];

test("all sixteen frozen daily worlds from PR 16 remain exactly unchanged", () => {
  assert.equal(data.data_version, baseline.data_version);
  for (const [date, hash] of Object.entries(baseline.world_sha256))
    assert.equal(digest(buildWorld(data, date)), hash, date);
});
test("all 39 quiz banks remain unchanged after introductory copy revisions", () => {
  const bank = Object.entries(data.modedex.modemon)
    .filter(([, s]) => s.stage < 3)
    .map(([speciesId]) => questionsFor({ ...spawn, speciesId }, data));
  assert.equal(bank.length, 39);
  assert.equal(digest(bank), baseline.question_bank_sha256);
});
test("old captures, daily escapes, in-progress answers and storage keys still resolve", () => {
  const old = baseline.saved_progress;
  const restored = readProgress({ getItem: () => JSON.stringify(old) }, "demo");
  assert.deepEqual(restored, old);
  assert.equal(progressKey("demo"), "modemon-go:playable:v1:progress:demo");
  const statuses = ["captured", "escaped", "in_progress"];
  for (const [i, sample] of baseline.saved_encounters.entries()) {
    const current = world.find((s) => s.id === sample.id)!;
    assert.ok(current);
    assert.equal(restored.attempts[current.id].status, statuses[i]);
    assert.deepEqual(beginAttempt(restored, current), restored);
    if (i < 2)
      assert.throws(() =>
        answerQuestion(restored, current, 0, questionsFor(current, data)),
      );
    else assert.equal(restored.attempts[current.id].answers.length, 1);
  }
  assert.deepEqual(
    readProgress({ getItem: () => null }, "real"),
    emptyProgress(),
  );
});
test("player labels use actual region names and never expose region IDs", () => {
  for (const s of world) {
    assert.ok(regionLabel(data, s.poi.region).length);
    assert.ok(
      placeLabel(data, s.poi).startsWith("Near " + s.poi.name + " in "),
    );
    assert.ok(
      markerLabel(data, s).includes(s.rarity === "common" ? "Common" : "Rare"),
    );
    assert.doesNotMatch(markerLabel(data, s), /\b(?:RAL|DUR)-\d/);
  }
  assert.equal(regionLabel(data, "unknown"), "the nearby game area");
});
test("friendly approximate distance and GPS guidance does not change the 75m gate", () => {
  assert.equal(approximateDistance(381), "380 m");
  assert.equal(approximateDistance(1250), "1.3 km");
  const fix = {
    lat: spawn.poi.lat + 0.0034,
    lon: spawn.poi.lon,
    accuracy: 10,
    timestamp: 100000,
  };
  const gate = interaction(spawn, fix, 100000);
  const message = proximityCopy("real", fix, gate);
  assert.match(message, /You're about 380 m away/);
  assert.match(message, /roughly 75 m/);
  assert.doesNotMatch(message, /tolerance|foreground|GPS fix/);
  assert.equal(gate.allowed, false);
  assert.match(
    proximityCopy("real", null, interaction(spawn, null)),
    /Allow location access/,
  );
  assert.match(
    proximityCopy(
      "real",
      { ...fix, accuracy: 100 },
      interaction(spawn, { ...fix, accuracy: 100 }, 100000),
    ),
    /not accurate or recent enough/,
  );
});
test("demo guidance never presents simulation as actual GPS or GPS accuracy", () => {
  assert.match(
    proximityCopy("demo", null, interaction(spawn, null)),
    /without traveling/,
  );
  const fix = {
    lat: spawn.poi.lat,
    lon: spawn.poi.lon,
    accuracy: 0,
    timestamp: 100000,
  };
  assert.match(
    proximityCopy("demo", fix, interaction(spawn, fix, 100000)),
    /simulated location/,
  );
  assert.doesNotMatch(
    proximityCopy("demo", fix, interaction(spawn, fix, 100000)),
    /accuracy|tolerance/,
  );
});
test("public safety wording retains the curated playground restriction", () => {
  assert.match(publicLocationSafety, /Stay in public areas/);
  assert.match(publicLocationSafety, /don't need to enter the business/);
  const plaza = data.pois.find((p) => p.id === "RAL-02_osm_way_583072635")!;
  assert.match(
    extraLocationSafety(plaza)!,
    /Do not approach or linger around children's play equipment/,
  );
});
