import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  answerQuestion,
  beginAttempt,
  buildWorld,
  dayKey,
  emptyProgress,
  habitatAt,
  interaction,
  maximumInCircle,
  persist,
  progressKey,
  questionsFor,
  readProgress,
  resolvedRegion,
  type Runtime,
} from "../src/engine.ts";
const data = JSON.parse(
  readFileSync(new URL("../src/data/runtime.json", import.meta.url), "utf8"),
) as Runtime;
const date = "2026-10-17",
  world = buildWorld(data, date),
  spawn = world[0];
test("canonical runtime counts, safe anchors, only explicitly approved Signature scheduling", () => {
  assert.equal(Object.keys(data.modedex.modemon).length, 51);
  assert.equal(data.regions.length, 8);
  assert.equal(data.zones.length, 62);
  assert.equal(data.pois.length, 927);
  assert.ok(world.length > 0);
  for (const s of world) {
    assert.ok(s.poi.eligible);
    if (s.rarity === "signature") assert.ok(data.signatures?.entries.some((e) => e.species_id === s.speciesId && e.poi_id === s.poi.id && e.safety_status === "mapped_public_approach"));
    assert.ok(
      s.basis.some((h) =>
        data.modedex.modemon[s.speciesId].habitats.includes(h),
      ),
    );
  }
});
test("daily worlds are deterministic across order, position and viewport; rotate by date", () => {
  assert.deepEqual(
    buildWorld({ ...data, pois: [...data.pois].reverse() }, date),
    world,
  );
  assert.deepEqual(buildWorld(data, date), world);
  assert.notDeepEqual(
    buildWorld(data, "2026-10-18").map((s) => s.id),
    world.map((s) => s.id),
  );
});
test("Eastern daily rotation uses a date rather than local browser timezone", () => {
  assert.equal(dayKey(new Date("2026-10-18T03:59:59Z")), "2026-10-17");
  assert.equal(dayKey(new Date("2026-10-18T04:00:00Z")), "2026-10-18");
});
test("density catches a circle centred between markers, including eight on its rim", () => {
  const ring = Array.from({ length: 8 }, (_, i) => ({
    x: 800 * Math.cos((i * Math.PI) / 4),
    y: 800 * Math.sin((i * Math.PI) / 4),
  }));
  assert.equal(maximumInCircle(ring), 8);
  assert.equal(
    maximumInCircle([
      { x: 0, y: 0 },
      { x: 2000, y: 0 },
    ]),
    1,
  );
  assert.equal(maximumInCircle(Array(8).fill({ x: 0, y: 0 })), 8);
});
test("seven cap holds globally, across regions and rarities for fourteen rotations", () => {
  for (let d = 1; d <= 14; d++) {
    const w = buildWorld(data, `2026-10-${String(d).padStart(2, "0")}`);
    assert.ok(maximumInCircle(w.map((s) => s.poi)) <= 7);
    assert.equal(new Set(w.map((s) => s.id)).size, w.length);
  }
});
test("region routing respects actual configured overlap ownership at all eligible anchors", () => {
  for (const p of data.pois.filter((p) => p.eligible))
    assert.equal(resolvedRegion(data, p.lon, p.lat), p.region);
  assert.equal(resolvedRegion(data, 0, 0), null);
  const context = habitatAt(data, spawn.poi.lon, spawn.poi.lat);
  assert.equal(context.region, spawn.poi.region);
  assert.ok(
    context.zones.every((z) => z.properties.region_id === context.region),
  );
});
test("75m proximity, bounded accuracy allowance, stale/poor/absent GPS", () => {
  const now = 100000,
    fix = { ...spawn.poi, accuracy: 0, timestamp: now };
  assert.equal(interaction(spawn, fix, now).allowed, true);
  assert.equal(
    interaction(spawn, { ...fix, lat: fix.lat + 0.00067 }, now).allowed,
    true,
  );
  assert.equal(
    interaction(spawn, { ...fix, lat: fix.lat + 0.0009 }, now).allowed,
    false,
  );
  assert.equal(
    interaction(spawn, { ...fix, lat: fix.lat + 0.00072, accuracy: 20 }, now)
      .allowed,
    true,
  );
  assert.equal(
    interaction(spawn, { ...fix, accuracy: 51 }, now).allowed,
    false,
  );
  assert.equal(
    interaction(spawn, { ...fix, timestamp: now - 31000 }, now).allowed,
    false,
  );
  assert.equal(interaction(spawn, null, now).allowed, false);
});
test("each enabled species has exactly three distinct grounded questions with four unique choices", () => {
  for (const [speciesId, s] of Object.entries(data.modedex.modemon).filter(
    ([, s]) => s.stage < 3,
  )) {
    const questions = questionsFor({ ...spawn, speciesId }, data);
    assert.equal(questions.length, 3);
    assert.equal(new Set(questions.map((q) => q.id)).size, 3);
    assert.deepEqual(
      questions.map((q) => q.options[q.correct]),
      [s.role, s.input_data, s.output_data],
    );
    for (const q of questions) {
      assert.equal(new Set(q.options).size, 4);
      assert.ok(q.explanation.includes(s.input_data));
    }
    assert.deepEqual(questionsFor({ ...spawn, speciesId }, data), questions);
  }
});
test("capture requires at least two of exactly three; completed attempts cannot retry", () => {
  const qs = questionsFor(spawn, data);
  for (const total of [0, 1, 2, 3]) {
    let p = beginAttempt(emptyProgress(), spawn);
    qs.forEach(
      (q, i) =>
        (p = answerQuestion(
          p,
          spawn,
          i < total ? q.correct : (q.correct + 1) % 4,
          qs,
        )),
    );
    assert.equal(
      p.attempts[spawn.id].status,
      total >= 2 ? "captured" : "escaped",
    );
    assert.throws(() => answerQuestion(p, spawn, 0, qs));
    assert.deepEqual(beginAttempt(p, spawn), p);
  }
});
test("escape is exact-encounter/day scoped, not species scoped", () => {
  const q = questionsFor(spawn, data);
  let p = beginAttempt(emptyProgress(), spawn);
  for (const question of q)
    p = answerQuestion(p, spawn, (question.correct + 1) % 4, q);
  const next = { ...spawn, id: spawn.id + "different-poi" };
  p = beginAttempt(p, next);
  assert.equal(p.attempts[next.id].status, "in_progress");
  assert.equal(p.attempts[spawn.id].status, "escaped");
});
test("capture, mid-quiz answers and escape survive serialization without reset; demo separate", () => {
  const entries = new Map<string, string>();
  const storage = {
    getItem: (key: string) => entries.get(key) ?? null,
    setItem: (key: string, value: string) => {
      entries.set(key, value);
    },
  };
  const q = questionsFor(spawn, data);
  let p = beginAttempt(emptyProgress(), spawn);
  p = answerQuestion(p, spawn, q[0].correct, q);
  persist(storage, "demo", p);
  assert.deepEqual(readProgress(storage, "demo"), p);
  assert.deepEqual(readProgress(storage, "real"), emptyProgress());
  p = answerQuestion(readProgress(storage, "demo"), spawn, q[1].correct, q);
  p = answerQuestion(p, spawn, q[2].correct, q);
  persist(storage, "demo", p);
  assert.equal(
    readProgress(storage, "demo").attempts[spawn.id].status,
    "captured",
  );
  assert.notEqual(progressKey("demo"), progressKey("real"));
});
test("storage denial/corruption fails honestly without silently resetting existing data", () => {
  assert.throws(() =>
    persist(
      {
        setItem: () => {
          throw Error("QuotaExceeded");
        },
        getItem: () => null,
      },
      "real",
      emptyProgress(),
    ),
  );
  assert.throws(() => readProgress({ getItem: () => "{broken" }, "real"));
  assert.throws(() =>
    persist(
      { setItem: () => {}, getItem: () => null },
      "real",
      emptyProgress(),
    ),
  );
});
