import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  answerQuestion,
  attemptRules,
  beginAttempt,
  buildWorld,
  changeDifficulty,
  emptyProgress,
  persist,
  questionsFor,
  questionsForAttempt,
  readProgress,
  startAttempt,
  type Runtime,
} from "../src/engine.ts";
import {
  difficultyQuestionsFor,
  quizModes,
  sourceValue,
  validateQuiz,
  type Difficulty,
} from "../src/quizzes.ts";

const data = JSON.parse(
  readFileSync(new URL("../src/data/runtime.json", import.meta.url), "utf8"),
) as Runtime;
const spawn = buildWorld(data, "2026-10-17")[0];
const modes = Object.keys(quizModes) as Difficulty[];

test("all 39 species and three modes produce distinct, source-grounded, deterministic four-choice questions", () => {
  let banks = 0,
    items = 0;
  for (const [speciesId, species] of Object.entries(
    data.modedex.modemon,
  ).filter(([, s]) => s.stage < 3)) {
    for (const mode of modes) {
      const s = { ...spawn, speciesId };
      const qs = difficultyQuestionsFor(s, data, mode);
      assert.equal(qs.length, quizModes[mode].count);
      assert.deepEqual(difficultyQuestionsFor(s, data, mode), qs);
      assert.equal(new Set(qs.map((q) => q.id)).size, qs.length);
      assert.equal(new Set(qs.map((q) => q.prompt)).size, qs.length);
      for (const q of qs) {
        assert.equal(q.options.length, 4);
        assert.equal(new Set(q.options).size, 4);
        assert.equal(sourceValue(data, q.source.path), q.source.value);
        assert.ok(q.explanation.includes(q.options[q.correct]));
        assert.ok(q.prompt.includes(species.name));
        assert.ok(q.options.every((o) => o.trim() && o.length <= 180));
        for (const source of q.option_sources)
          assert.equal(sourceValue(data, source.path), source.value);
        assert.doesNotMatch(q.prompt, /deploy|telemetry|latency|monitoring/i);
      }
      if (mode !== "novice")
        for (const topic of ["family_id", "habitats", "models_algorithms"])
          assert.ok(qs.some((q) => q.topic === topic));
      if (mode === "expert")
        for (const topic of ["explainability", "biases_limitations"])
          assert.ok(qs.some((q) => q.topic === topic));
      banks++;
      items += qs.length;
    }
  }
  assert.equal(banks, 117);
  assert.equal(items, 585);
});

test("all answer partitions obey strict majority and never end the quiz early", () => {
  for (const mode of modes) {
    const config = quizModes[mode];
    for (let bits = 0; bits < 2 ** config.count; bits++) {
      let p = startAttempt(emptyProgress(), spawn, data, mode);
      const qs = questionsForAttempt(spawn, data, p.attempts[spawn.id]);
      let correct = 0;
      qs.forEach((q, i) => {
        const right = !!(bits & (1 << i));
        if (right) correct++;
        p = answerQuestion(
          p,
          spawn,
          right ? q.correct : (q.correct + 1) % 4,
          qs,
        );
        assert.equal(
          p.attempts[spawn.id].status,
          i < config.count - 1
            ? "in_progress"
            : correct >= config.required
              ? "captured"
              : "escaped",
        );
      });
      assert.equal(p.attempts[spawn.id].answers.length, config.count);
      assert.throws(() => answerQuestion(p, spawn, 0, qs));
      assert.equal(startAttempt(p, spawn, data, "expert"), p);
      assert.throws(() => changeDifficulty(p, spawn, data, "novice"));
    }
  }
});

test("difficulty and exact questions persist before the first answer; they lock after one answer", () => {
  const entries = new Map<string, string>();
  const storage = {
    getItem: (key: string) => entries.get(key) ?? null,
    setItem: (key: string, value: string) => {
      entries.set(key, value);
    },
  };
  let p = startAttempt(emptyProgress(), spawn, data);
  p = changeDifficulty(p, spawn, data, "intermediate");
  persist(storage, "demo", p);
  p = readProgress(storage, "demo");
  assert.equal(p.attempts[spawn.id].difficulty, "intermediate");
  const saved = questionsForAttempt(spawn, data, p.attempts[spawn.id]);
  p = answerQuestion(p, spawn, saved[0].correct, saved);
  persist(storage, "demo", p);
  assert.deepEqual(readProgress(storage, "real"), emptyProgress());
  p = readProgress(storage, "demo");
  assert.equal(startAttempt(p, spawn, data, "expert"), p);
  assert.throws(() => changeDifficulty(p, spawn, data, "expert"), /locked/);
  const changedData = structuredClone(data);
  changedData.modedex.modemon[spawn.speciesId].models_algorithms = [
    "Future edit",
  ];
  assert.deepEqual(
    questionsForAttempt(spawn, changedData, p.attempts[spawn.id]),
    saved,
  );
  assert.equal(p.attempts[spawn.id].answers.length, 1);
});

test("saved question snapshots cannot be replaced by a different bank while answering", () => {
  const p = startAttempt(emptyProgress(), spawn, data, "expert");
  assert.equal(p.version, 2);
  const mislabeled = { ...p, version: 1 };
  assert.throws(() =>
    readProgress({ getItem: () => JSON.stringify(mislabeled) }, "demo"),
  );
  assert.throws(() =>
    answerQuestion(p, spawn, 0, difficultyQuestionsFor(spawn, data, "novice")),
  );
  const altered = structuredClone(p.attempts[spawn.id].questions!);
  altered[0].correct = (altered[0].correct + 1) % 4;
  assert.throws(() => answerQuestion(p, spawn, 0, altered));
});

test("legacy unversioned attempts retain their original Novice bank and results byte-for-byte", () => {
  const fixture = JSON.parse(
    readFileSync(
      new URL("./fixtures/mvp-gameplay.json", import.meta.url),
      "utf8",
    ),
  );
  const old = JSON.stringify(fixture.saved_progress);
  const p = readProgress({ getItem: () => old }, "demo");
  assert.equal(JSON.stringify(p), old);
  for (const sample of fixture.saved_encounters) {
    const s = buildWorld(data, "2026-10-17").find((s) => s.id === sample.id)!;
    assert.deepEqual(
      questionsForAttempt(s, data, p.attempts[s.id]),
      questionsFor(s, data),
    );
    assert.equal(attemptRules(p.attempts[s.id]).required, 2);
    assert.equal(startAttempt(p, s, data, "expert"), p);
    assert.throws(() => changeDifficulty(p, s, data, "expert"));
  }
  let legacy = beginAttempt(emptyProgress(), spawn);
  const qs = questionsFor(spawn, data);
  for (const [i, q] of qs.entries())
    legacy = answerQuestion(
      legacy,
      spawn,
      i < 2 ? q.correct : (q.correct + 1) % 4,
      qs,
    );
  assert.equal(legacy.attempts[spawn.id].status, "captured");
  assert.deepEqual(
    readProgress({ getItem: () => JSON.stringify(legacy) }, "real"),
    legacy,
  );
});

test("all mode escapes remain encounter/day scoped and real/demo remain separate", () => {
  for (const mode of modes) {
    let p = startAttempt(emptyProgress(), spawn, data, mode);
    const qs = questionsForAttempt(spawn, data, p.attempts[spawn.id]);
    for (const q of qs) p = answerQuestion(p, spawn, (q.correct + 1) % 4, qs);
    for (const next of [
      { ...spawn, id: spawn.id + ":other-poi" },
      { ...spawn, id: spawn.id + ":tomorrow", date: "2026-10-18" },
    ]) {
      p = startAttempt(p, next, data, "novice");
      assert.equal(p.attempts[next.id].status, "in_progress");
    }
    assert.equal(p.attempts[spawn.id].status, "escaped");
  }
});

test("missing topics, unsupported sources and invalid modes fail instead of inventing facts", () => {
  for (const field of [
    "models_algorithms",
    "explainability",
    "biases_limitations",
  ] as const) {
    const missing = structuredClone(data);
    missing.modedex.modemon[spawn.speciesId][field] = [];
    assert.throws(
      () => difficultyQuestionsFor(spawn, missing, "expert"),
      /Missing/,
    );
  }
  assert.throws(() => difficultyQuestionsFor(spawn, data, "bad" as Difficulty));
  const bad = structuredClone(difficultyQuestionsFor(spawn, data, "expert"));
  bad[6].options[bad[6].correct] = "An invented claim";
  assert.throws(() => validateQuiz(bad, data, spawn.speciesId, "expert"));
  const signature = Object.entries(data.modedex.modemon).find(
    ([, s]) => s.stage === 3,
  )![0];
  assert.throws(() =>
    difficultyQuestionsFor({ ...spawn, speciesId: signature }, { ...data, signatures: undefined }, "expert"),
  );
});

test("malformed version, mode, question count, duplicate options, and inconsistent results fail closed", () => {
  const p = startAttempt(emptyProgress(), spawn, data, "expert");
  const corruptions = [
    (a: Record<string, unknown>) => {
      a.quiz_version = 99;
    },
    (a: Record<string, unknown>) => {
      a.difficulty = "bad";
    },
    (a: Record<string, unknown>) => {
      delete a.questions;
    },
    (a: Record<string, unknown>) => {
      a.questions = [];
    },
    (a: Record<string, unknown>) => {
      a.answers = [4];
    },
    (a: Record<string, unknown>) => {
      a.status = "captured";
      a.answers = [];
    },
  ];
  for (const corrupt of corruptions) {
    const broken = structuredClone(p);
    corrupt(broken.attempts[spawn.id] as unknown as Record<string, unknown>);
    assert.throws(() =>
      readProgress({ getItem: () => JSON.stringify(broken) }, "demo"),
    );
  }
  const broken = structuredClone(p);
  broken.attempts[spawn.id].questions![0].options.fill("Duplicate");
  assert.throws(() =>
    readProgress({ getItem: () => JSON.stringify(broken) }, "demo"),
  );
});

test("bank generation is independent of catalog object iteration order and does not mutate input", () => {
  const before = JSON.stringify(data);
  const shuffled = {
    ...data,
    modedex: {
      ...data.modedex,
      modemon: Object.fromEntries(
        Object.entries(data.modedex.modemon).reverse(),
      ),
    },
  };
  for (const mode of modes)
    assert.deepEqual(
      difficultyQuestionsFor(spawn, data, mode),
      difficultyQuestionsFor(spawn, shuffled, mode),
    );
  assert.equal(JSON.stringify(data), before);
});

test("new-version progress retains every legacy record when a difficulty-aware encounter is added", () => {
  const fixture = JSON.parse(
    readFileSync(
      new URL("./fixtures/mvp-gameplay.json", import.meta.url),
      "utf8",
    ),
  );
  const old = fixture.saved_progress;
  const next = startAttempt(
    old,
    { ...spawn, id: spawn.id + ":new-encounter" },
    data,
    "expert",
  );
  assert.equal(next.version, 2);
  for (const [id, attempt] of Object.entries(old.attempts))
    assert.deepEqual(next.attempts[id], attempt);
  assert.deepEqual(
    readProgress({ getItem: () => JSON.stringify(next) }, "demo"),
    next,
  );
});
