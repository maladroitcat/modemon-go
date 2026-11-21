import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { captureHistory, calculateAchievements, newlyUnlocked, speciesWithoutAnchors } from "../src/achievements.ts";
import { everydayExamples } from "../src/data/everydayExamples.ts";
import { answerQuestion, attemptRules, beginAttempt, buildWorld, emptyProgress, persist, progressKey, questionsFor, readProgress, startAttempt, type Progress, type Runtime, type Spawn } from "../src/engine.ts";
import { markerLabel } from "../src/presentation.ts";
import type { Difficulty } from "../src/quizzes.ts";

const data = JSON.parse(readFileSync(new URL("../src/data/runtime.json", import.meta.url), "utf8")) as Runtime;
const world = buildWorld(data, "2026-10-17");
const spawn = world[0];
const entries = Object.entries(data.modedex.modemon);
function capture(p: Progress, s = spawn, difficulty?: Difficulty, pass = true) {
  let next = difficulty ? startAttempt(p, s, data, difficulty) : beginAttempt(p, s);
  const qs = next.attempts[s.id].questions ?? questionsFor(s, data);
  for (const q of qs) next = answerQuestion(next, s, pass ? q.correct : (q.correct + 1) % 4, qs);
  return next;
}
function at(id: string, encounter = id): Spawn { return { ...spawn, speciesId: id, id: encounter }; }
const find = (p: Progress, id: string) => calculateAchievements(p, data).find((a) => a.id === id)!;

test("only successful encounters count; discovered, escaped and ongoing records do not", () => {
  let p = beginAttempt(emptyProgress(), spawn);
  assert.equal(captureHistory(p).collected.size, 0);
  p = capture(p, spawn, undefined, false);
  assert.ok(p.discovered.includes(spawn.speciesId));
  assert.equal(captureHistory(p).collected.size, 0);
  p = capture(p, at(spawn.speciesId, "other-encounter"));
  const history = captureHistory(p);
  assert.deepEqual([...history.collected], [spawn.speciesId]);
  assert.equal(history.counts.get(spawn.speciesId), 1);
  assert.deepEqual([...history.mastery.get(spawn.speciesId)!], ["novice"]);
});

test("legacy v1 and difficulty-aware v2 captures independently accumulate mastery in any order", () => {
  let p = capture(emptyProgress(), spawn, "expert");
  assert.deepEqual([...captureHistory(p).mastery.get(spawn.speciesId)!], ["expert"]);
  p = capture(p, at(spawn.speciesId, "legacy"));
  p = capture(p, at(spawn.speciesId, "intermediate"), "intermediate");
  p = capture(p, at(spawn.speciesId, "failed-novice"), "novice", false);
  assert.deepEqual(captureHistory(p).mastery.get(spawn.speciesId), new Set(["expert", "novice", "intermediate"]));
  assert.equal(captureHistory(p).counts.get(spawn.speciesId), 3);
  assert.equal(attemptRules(p.attempts.legacy).difficulty, "novice");
});

test("Hoarder needs five distinct successes of one species, never five attempts or five species", () => {
  let p = emptyProgress();
  for (let i = 0; i < 4; i++) p = capture(p, at(spawn.speciesId, `encounter-${i}`));
  p = capture(p, at(spawn.speciesId, "escaped"), "expert", false);
  p = beginAttempt(p, at(spawn.speciesId, "ongoing"));
  assert.equal(find(p, "hoarder").current, 4);
  assert.equal(find(p, "hoarder").unlocked, false);
  const completed = JSON.stringify(p.attempts["encounter-0"]);
  assert.equal(beginAttempt(p, at(spawn.speciesId, "encounter-0")), p);
  assert.throws(() => answerQuestion(p, at(spawn.speciesId, "encounter-0"), 0, questionsFor(spawn, data)));
  p = capture(p, at(spawn.speciesId, "fifth"));
  assert.equal(find(p, "hoarder").unlocked, true);
  assert.equal(JSON.stringify(p.attempts["encounter-0"]), completed);
  assert.deepEqual(captureHistory(p), captureHistory(JSON.parse(JSON.stringify(p))));
  const spread = entries.slice(0, 5).reduce((p, [id]) => capture(p, at(id)), emptyProgress());
  assert.equal(find(spread, "hoarder").current, 1);
});

test("canonical family and rarity membership drive exact unique species completion", () => {
  assert.equal(Object.keys(data.modedex.families!).length, 8);
  for (const [family, info] of Object.entries(data.modedex.families!)) {
    const members = entries.filter(([, s]) => s.family_id === family);
    let p = emptyProgress();
    for (const [id] of members.slice(0, -1)) p = capture(p, at(id));
    const goal = find(p, `family-${family}`);
    assert.equal(goal.name, `${info.name} Family Expert`);
    assert.equal(goal.total, members.length);
    assert.equal(goal.unlocked, false);
    p = capture(p, at(members.at(-1)![0]));
    assert.equal(find(p, `family-${family}`).unlocked, true);
  }
  for (const rarity of ["common", "rare", "signature"]) {
    const members = entries.filter(([, s]) => s.rarity === rarity);
    const p = members.reduce((p, [id]) => capture(p, at(id)), emptyProgress());
    const goal = find(p, `${rarity}-collector`);
    assert.equal(goal.total, members.length);
    assert.equal(goal.current, members.length);
    assert.equal(goal.unlocked, true);
    if (rarity === "signature") { assert.equal(goal.name, "Special Collector"); assert.equal(goal.total, 12); }
    assert.equal(find(p, "model-master").unlocked, false);
  }
});

test("all-species collection and Expert-only Master Scholar; simultaneous transitions", () => {
  let p = entries.reduce((p, [id]) => capture(p, at(id)), emptyProgress());
  assert.equal(find(p, "model-master").total, 51);
  assert.equal(find(p, "model-master").unlocked, true);
  assert.equal(find(p, "connoisseur").current, 8);
  assert.equal(find(p, "master-scholar").current, 0);
  const before = emptyProgress();
  for (const [id] of entries.slice(0, -1)) p = capture(p, at(id, `expert-${id}`), "expert");
  assert.equal(find(p, "master-scholar").current, 50);
  p = capture(p, at(entries.at(-1)![0], "last-expert"), "expert", false);
  assert.equal(find(p, "master-scholar").current, 50);
  p = capture(p, at(entries.at(-1)![0], "success-expert"), "expert");
  assert.equal(find(p, "master-scholar").unlocked, true);
  assert.equal(newlyUnlocked(calculateAchievements(p, data), calculateAchievements(p, data)).length, 0);
  assert.equal(newlyUnlocked(calculateAchievements(before, data), calculateAchievements(p, data)).length, 14);
  let nearly = entries.slice(0, -1).reduce((p, [id]) => capture(p, at(id), "expert"), emptyProgress());
  const old = calculateAchievements(nearly, data);
  nearly = capture(nearly, at(entries.at(-1)![0]), "expert");
  assert.deepEqual(newlyUnlocked(old, calculateAchievements(nearly, data)).map((a) => a.id).sort(),
    ["model-master", "master-scholar", "rare-collector", "family-scheduler"].sort());
});

test("mode isolation, serialization, corruption protections and immutable world identity", () => {
  const values = new Map<string, string>();
  const storage = { getItem: (k: string) => values.get(k) ?? null, setItem: (k: string, v: string) => { values.set(k, v); } };
  const canonical = JSON.stringify(data), original = JSON.stringify(world);
  const legacy = capture(emptyProgress());
  persist(storage, "real", legacy);
  persist(storage, "demo", capture(emptyProgress(), spawn, "expert"));
  assert.deepEqual(captureHistory(readProgress(storage, "real")).mastery.get(spawn.speciesId), new Set(["novice"]));
  assert.deepEqual(captureHistory(readProgress(storage, "demo")).mastery.get(spawn.speciesId), new Set(["expert"]));
  calculateAchievements(readProgress(storage, "real"), data);
  assert.equal(JSON.stringify(buildWorld(data, "2026-10-17")), original);
  assert.equal(JSON.stringify(data), canonical);
  const label = markerLabel(data, spawn, true);
  assert.ok(label.includes("Previously collected species"));
  assert.ok(!label.includes(data.modedex.modemon[spawn.speciesId].name));
  values.set(progressKey("real"), "{corrupt");
  assert.throws(() => readProgress(storage, "real"));
  assert.equal(values.get(progressKey("real")), "{corrupt");
});

test("coverage audit faithfully warns for blocked goals without reducing requirements", () => {
  // Keep the original blocked-world test. Only explicitly approved locations
  // are disabled to reconstruct its pre-approval eligibility.
  const previous = { ...data, pois: data.pois.map((p) => p.public_approach_approval ? { ...p, eligible: false } : p) };
  const missing = speciesWithoutAnchors(previous);
  assert.deepEqual([...missing].sort(), ["anomaly_vitals", "detector_disease", "extractor_medical", "forecast_patient", "scheduler_hospital"]);
  const blocked = calculateAchievements(emptyProgress(), previous).filter((a) => a.unavailable);
  assert.deepEqual(blocked.map((a) => a.id).sort(), ["model-master", "master-scholar", "rare-collector",
    "family-anomaly", "family-detector", "family-extractor", "family-forecast", "family-scheduler"].sort());
  assert.equal(find(emptyProgress(), "model-master").total, 51);
  assert.equal(speciesWithoutAnchors(data).size, 0);
  assert.equal(calculateAchievements(emptyProgress(), data).filter((a) => a.unavailable).length, 0);
});

test("canonical catalog extensions automatically enter overall, family and rarity requirements", () => {
  const extended: Runtime = { ...data, modedex: { ...data.modedex,
    families: { ...data.modedex.families, future: { name: "Future Family" } },
    modemon: { ...data.modedex.modemon,
      future_species: { ...data.modedex.modemon.detector_base, family_id: "future" } } } };
  const goals = calculateAchievements(emptyProgress(), extended);
  assert.equal(goals.find((a) => a.id === "model-master")!.total, 52);
  assert.equal(goals.find((a) => a.id === "master-scholar")!.total, 52);
  assert.equal(goals.find((a) => a.id === "common-collector")!.total, 9);
  assert.equal(goals.find((a) => a.id === "connoisseur")!.total, 9);
  assert.equal(goals.find((a) => a.id === "family-future")!.name, "Future Family Family Expert");
  assert.equal(goals.find((a) => a.id === "family-future")!.total, 1);
});

test("every one of 51 stable species IDs has 2–3 distinct concise illustrative examples", () => {
  assert.deepEqual(Object.keys(everydayExamples).sort(), entries.map(([id]) => id).sort());
  for (const [id, items] of Object.entries(everydayExamples)) {
    assert.ok(items.length >= 2 && items.length <= 3, id);
    assert.equal(new Set(items.map((e) => e.title)).size, items.length);
    for (const item of items) {
      assert.ok(item.title.length > 3 && item.title.length < 70, id);
      assert.ok(item.description.length > 40 && item.description.length < 260, id);
      assert.equal(item.illustrative, true, id);
    }
  }
});
