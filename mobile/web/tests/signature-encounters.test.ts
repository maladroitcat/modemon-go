import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  answerQuestion, buildWorld, emptyProgress, interaction, maximumInCircle,
  persist, progressKey, readProgress, resolvedRegion, scheduledSignatures,
  startAttempt, type Runtime,
} from "../src/engine.ts";
import { difficultyQuestionsFor, quizModes, type Difficulty } from "../src/quizzes.ts";
import { markerLabel } from "../src/presentation.ts";
import { signatureProject } from "../src/signatures.ts";

const data = JSON.parse(readFileSync(new URL("../src/data/runtime.json", import.meta.url), "utf8")) as Runtime;
const crosswalk = {
  extractor_history: "RAL-04_osm_node_2470661698",
  extractor_specimen: "RAL-01_osm_way_197842115",
  generator_catalog: "RAL-04_osm_way_177166351",
  generator_classroom_chatbot: "RAL-04_osm_node_2470661698",
  generator_lesson_planner: "RAL-04_osm_node_2470661698",
  recommender_adaptive_learning: "RAL-04_osm_node_2470661698",
  recommender_ai_curator: "DUR-02_osm_way_30424777",
  recommender_research: "RAL-04_osm_way_177166351",
  retriever_semantic_search: "DUR-02_osm_way_391474817",
  scheduler_ride_booking: "DUR-01_osm_node_5844548329",
  scheduler_traffic_signal: "RAL-01_osm_node_13659913892",
  scheduler_transit_flow: "DUR-01_osm_node_5844548329",
};
const dates = Array.from({ length: 32 }, (_, i) => new Date(Date.UTC(2026, 9, 18 + i)).toISOString().slice(0, 10));
const rotation = dates.flatMap((date) => scheduledSignatures(data, date, "demo"));

test("exact owner-approved twelve canonical IDs map only to approved stable primary IDs", () => {
  assert.deepEqual(Object.fromEntries(data.signatures!.entries.map((e) => [e.species_id, e.poi_id])), crosswalk);
  assert.equal(new Set(rotation.map((s) => s.speciesId)).size, 12);
  for (const s of rotation) {
    assert.equal(s.poi.id, crosswalk[s.speciesId as keyof typeof crosswalk]);
    assert.equal(s.poi.special_destination, true);
    assert.equal(s.rarity, "signature");
    const project = signatureProject(data.modedex.modemon[s.speciesId])!;
    assert.ok(project.href?.startsWith("https://"));
    assert.ok(project.introduction);
    assert.doesNotMatch(markerLabel(data, s), new RegExp(data.modedex.modemon[s.speciesId].name));
    assert.match(markerLabel(data, s), /Mystery Modémon · Signature/);
  }
});

test("one scarce slot per anchor, all shared species rotate, deterministic under reordered inputs", () => {
  const reversed = structuredClone(data);
  reversed.pois.reverse();
  reversed.signatures!.entries.reverse();
  for (const date of dates) {
    const daily = scheduledSignatures(data, date, "demo");
    assert.deepEqual(scheduledSignatures(reversed, date, "demo"), daily);
    assert.equal(new Set(daily.map((s) => s.poi.id)).size, daily.length);
  }
  for (const id of Object.values(crosswalk)) {
    const days = rotation.filter((s) => s.poi.id === id);
    assert.ok(days.length <= 8 && days.length >= 7); // one known Hunt closure
    assert.equal(new Set(days.map((s) => s.speciesId)).size, Object.values(crosswalk).filter((v) => v === id).length);
  }
  assert.ok(dates.some((date) => scheduledSignatures(data, date).length === 0));
});

test("mapped safe positions replace centroids; alternatives avoid the real station construction", () => {
  for (const date of dates) {
    for (const s of scheduledSignatures(data, date)) {
      assert.equal(resolvedRegion(data, s.poi.lon, s.poi.lat), s.poi.region);
      const source = data.pois.find((p) => p.id === s.poi.id)!;
      assert.notDeepEqual([s.poi.lat, s.poi.lon], [source.lat, source.lon]);
      assert.match(s.poi.association_note, /outdoor|public/);
      assert.equal(interaction(s, { ...s.poi, accuracy: 0, timestamp: 100000 }, 100000).allowed, true);
      assert.equal(interaction(s, { ...s.poi, lat: s.poi.lat + .0009, accuracy: 0, timestamp: 100000 }, 100000).allowed, false);
      if (s.poi.id === crosswalk.scheduler_ride_booking) assert.match(s.poi.association_note, /GoDurham stop 6680/);
    }
    assert.ok(buildWorld(data, date).every((s) => s.poi.id !== crosswalk.scheduler_ride_booking || s.rarity === "signature"));
  }
  assert.equal(new Set(dates.flatMap((date) => scheduledSignatures(data, date)).map((s) => s.speciesId)).size, 12);
  assert.ok(scheduledSignatures(data, "2026-10-19", "demo").every((s) => s.poi.id !== crosswalk.generator_catalog));
  const closed = structuredClone(data);
  closed.signatures!.entries.filter((e) => e.poi_id === crosswalk.generator_catalog).forEach((e) => e.blocked_dates.push("2026-10-18"));
  assert.ok(scheduledSignatures(data, "2026-10-18").some((s) => s.poi.id === crosswalk.generator_catalog));
  assert.ok(buildWorld(closed, "2026-10-18", "demo").every((s) => s.poi.id !== crosswalk.generator_catalog));
  const broken = structuredClone(data);
  broken.signatures!.entries.forEach((e) => { e.safety_status = "unknown"; e.placement = null; });
  assert.deepEqual(dates.flatMap((date) => scheduledSignatures(broken, date, "real")), []);
});

test("closure notices are date-scoped, linked and do not override an independently safe open approach", () => {
  const candidate = structuredClone(data);
  const hunt = candidate.signatures!.entries.filter((e) => e.poi_id === crosswalk.generator_catalog);
  // Put the actual sourced closure on an eligible calendar day without changing
  // production's approved four-day calendar, which doesn't schedule Hunt on 19th.
  for (const e of hunt) e.site_notices![0] = { ...e.site_notices![0], start_date: "2026-10-18", end_date: "2026-10-18" };
  const s = scheduledSignatures(candidate, "2026-10-18").find((s) => s.poi.id === crosswalk.generator_catalog)!;
  assert.ok(s);
  assert.equal(s.siteNotices!.length, 1);
  assert.equal(s.siteNotices![0].source_url, "https://www.lib.ncsu.edu/hunt/visit");
  assert.equal(scheduledSignatures(candidate, "2026-10-22").find((s) => s.poi.id === crosswalk.generator_catalog)!.siteNotices!.length, 0);
});

test("Signature priority precedes ordinary markers, global disk cap and one marker per anchor hold in both modes", () => {
  for (const mode of ["demo", "real"] as const) for (const date of dates.slice(0, 16)) {
    const world = buildWorld(data, date, mode);
    assert.ok(maximumInCircle(world.map((s) => s.poi)) <= 7);
    assert.equal(new Set(world.map((s) => s.poi.id)).size, world.length);
    const expected = scheduledSignatures(data, date, mode);
    assert.deepEqual(world.filter((s) => s.rarity === "signature"), expected);
    assert.ok(world.slice(0, expected.length).every((s) => s.rarity === "signature"));
  }
});

test("all twelve support all three grounded modes, saved capture/escape and demo/real separation", () => {
  const seen = new Map(rotation.map((s) => [s.speciesId, s]));
  let banks = 0;
  for (const spawn of seen.values()) for (const mode of Object.keys(quizModes) as Difficulty[]) {
    const bank = difficultyQuestionsFor(spawn, data, mode);
    assert.equal(bank.length, quizModes[mode].count);
    for (const passes of [true, false]) {
      let p = startAttempt(emptyProgress(), spawn, data, mode);
      for (const q of bank) p = answerQuestion(p, spawn, passes ? q.correct : (q.correct + 1) % 4, bank);
      assert.equal(p.attempts[spawn.id].status, passes ? "captured" : "escaped");
      const entries = new Map<string, string>();
      const storage = { getItem: (k: string) => entries.get(k) ?? null, setItem: (k: string, v: string) => { entries.set(k, v); } };
      persist(storage, "demo", p);
      assert.deepEqual(readProgress(storage, "demo"), p);
      assert.deepEqual(readProgress(storage, "real"), emptyProgress());
      assert.notEqual(progressKey("demo"), progressKey("real"));
      assert.equal(startAttempt(p, spawn, data, "novice"), p);
      assert.ok(!buildWorld(data, spawn.date, "demo").some((s) => s.poi.id === spawn.poi.id && s.id !== spawn.id));
    }
    banks++;
  }
  assert.equal(banks, 36);
});
