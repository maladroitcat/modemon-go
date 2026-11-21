import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { buildWorld, interaction, maximumInCircle, questionsFor, type Runtime } from "../src/engine.ts";
import { speciesWithoutAnchors } from "../src/achievements.ts";

const data = JSON.parse(readFileSync(new URL("../src/data/runtime.json", import.meta.url), "utf8")) as Runtime;
const approved = new Set(data.healthcare_approvals!.approved_poi_ids);
const original = { ...data, pois: data.pois.map((p) => approved.has(p.id) ? { ...p, eligible: false } : p) };
const days = Array.from({ length: 128 }, (_, i) => new Date(Date.UTC(2026, 10, 21 + i)).toISOString().slice(0, 10));
const worlds = days.map((d) => buildWorld(data, d));

test("exact twelve existing Healthcare locations are eligible; both Hemp Farmacy records stay excluded", () => {
  assert.equal(approved.size, 12);
  assert.equal(data.pois.filter((p) => p.eligible).length, 563);
  for (const p of data.pois.filter((p) => approved.has(p.id))) {
    assert.equal(p.eligible, true);
    assert.equal(p.primary, "healthcare");
    assert.ok(p.public_approach_approval);
    assert.match(p.association_note, /Do not enter healthcare buildings/);
  }
  for (const id of ["RAL-01_osm_way_47663698", "RAL-01_osm_node_8412073792"])
    assert.equal(data.pois.find((p) => p.id === id)!.eligible, false);
  assert.ok(data.pois.filter((p) => p.region === "RAL-05").every((p) => !p.eligible));
});

test("dated approvals preserve historical rotations; surviving existing encounters retain exact identity and quizzes", () => {
  for (const day of ["2026-10-17", "2026-10-18", "2026-11-20"])
    assert.deepEqual(buildWorld(data, day), buildWorld(original, day));
  assert.equal(data.data_version, "0f51a954e4340dea");
  for (const [i, day] of days.slice(0, 16).entries()) {
    const before = new Map(buildWorld(original, day).map((s) => [s.id, s]));
    for (const spawn of worlds[i].filter((s) => !approved.has(s.poi.id))) {
      // New anchors can change density admission. If a previously crowded-out
      // ordinary POI now fits, compare its seed against the original generator
      // with that single candidate, rather than inventing a prior encounter.
      const prior = before.get(spawn.id) ?? buildWorld({ ...original,
        signatures: undefined, pois: original.pois.filter((p) => p.id === spawn.poi.id) }, day)[0];
      assert.deepEqual(spawn, prior);
      assert.deepEqual(questionsFor(spawn, data), questionsFor(prior, original));
    }
  }
});

test("all five formerly unavailable species occur through normal rotations; density, safety and modes stay intact", () => {
  const healthcareOnly = Object.entries(data.modedex.modemon).filter(([, s]) => s.stage < 3 && s.habitats.length === 1 && s.habitats[0] === "healthcare").map(([id]) => id);
  assert.equal(healthcareOnly.length, 5);
  const observed = new Set(worlds.flat().map((s) => s.speciesId));
  for (const id of healthcareOnly) assert.ok(observed.has(id), id);
  assert.equal(speciesWithoutAnchors(data).size, 0);
  for (const [i, day] of days.slice(0, 32).entries()) {
    const real = worlds[i], demo = buildWorld(data, day, "demo");
    assert.ok(maximumInCircle(real.map((s) => s.poi)) <= 7);
    assert.ok(maximumInCircle(demo.map((s) => s.poi)) <= 7);
    assert.deepEqual(real.filter((s) => approved.has(s.poi.id)), demo.filter((s) => approved.has(s.poi.id)));
    assert.deepEqual(buildWorld({ ...data, pois: [...data.pois].reverse() }, day), real);
  }
  const s = worlds.flat().find((s) => healthcareOnly.includes(s.speciesId))!;
  assert.ok(approved.has(s.poi.id));
  assert.equal(interaction(s, null, 100000).allowed, false);
  assert.equal(interaction(s, { ...s.poi, accuracy: 0, timestamp: 100000 }, 100000).allowed, true);
  assert.equal(interaction(s, { ...s.poi, lat: s.poi.lat + .0009, accuracy: 0, timestamp: 100000 }, 100000).allowed, false);
  assert.equal(interaction(s, { ...s.poi, accuracy: 51, timestamp: 100000 }, 100000).allowed, false);
  assert.equal(interaction(s, { ...s.poi, accuracy: 0, timestamp: 60000 }, 100000).allowed, false);
});
