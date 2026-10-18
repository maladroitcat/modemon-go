import pointInPolygon from "@turf/boolean-point-in-polygon";
import type { Feature, Polygon, MultiPolygon } from "geojson";
import { rules } from "./rules.ts";
import {
  difficultyQuestionsFor,
  isDifficulty,
  quizModes,
  type Difficulty,
  type GroundedQuestion,
} from "./quizzes.ts";

export type Species = {
  name: string;
  family_id: string;
  stage: number;
  rarity: string;
  role: string;
  habitats: string[];
  ai_tasks: string[];
  models_algorithms: string[];
  input_data: string;
  output_data: string;
  biases_limitations: string[];
  explainability: string[];
  dex_entry: string;
  evolves_from: string | null;
  signature: unknown;
};
export type Area = Feature<Polygon | MultiPolygon, Record<string, string>>;
export type Poi = {
  id: string;
  name: string;
  region: string;
  lat: number;
  lon: number;
  x: number;
  y: number;
  primary: string | null;
  secondary: string | null;
  zone_habitats: string[];
  zone_ids: string[];
  eligible: boolean;
  exclusion_reasons: string[];
  association_note: string;
  special_destination: boolean;
  current_status: string;
  access_status: string;
};
export type Runtime = {
  data_version: string;
  art?: { approved: Record<string, boolean> };
  modedex: {
    modemon: Record<string, Species>;
    families?: Record<string, { name: string }>;
  };
  regions: Area[];
  zones: Area[];
  neutral: Area[];
  pois: Poi[];
  precedence: { winner: string; loser: string }[];
  habitats: Record<string, string>;
  signatures?: {
    version: string;
    schedule: { period_days: number; epoch: string };
    entries: {
      species_id: string;
      poi_id: string;
      safety_status: string;
      placement: { lat: number; lon: number; x: number; y: number } | null;
      association_note: string;
      evidence_url: string;
      blocked_dates: string[];
      ordinary_anchor_withheld?: boolean;
      site_notices?: SiteNotice[];
    }[];
  };
};
export type SiteNotice = {
  title: string;
  message: string;
  scope: "associated_building" | "nearby_construction";
  source_url: string;
  start_date: string;
  end_date: string | null;
};
export type Spawn = {
  id: string;
  date: string;
  speciesId: string;
  rarity: string;
  poi: Poi;
  basis: string[];
  siteNotices?: SiteNotice[];
};
export type Fix = {
  lat: number;
  lon: number;
  accuracy: number;
  timestamp: number;
};
export type Question = {
  id: string;
  prompt: string;
  options: string[];
  correct: number;
  explanation: string;
};
export type Attempt = {
  answers: number[];
  status: "in_progress" | "captured" | "escaped";
  speciesId: string;
  poiName: string;
  date: string;
  quiz_version?: 2;
  difficulty?: Difficulty;
  questions?: GroundedQuestion[];
};
export type Progress = {
  version: 1 | 2;
  discovered: string[];
  attempts: Record<string, Attempt>;
};
export const emptyProgress = (): Progress => ({
  version: 1,
  discovered: [],
  attempts: {},
});

export function hash(text: string) {
  let n = 2166136261;
  for (let i = 0; i < text.length; i++)
    n = Math.imul(n ^ text.charCodeAt(i), 16777619);
  return n >>> 0;
}
export function dayKey(date = new Date()) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: rules.timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  return ["year", "month", "day"]
    .map((k) => parts.find((p) => p.type === k)!.value)
    .join("-");
}
export function distance(
  a: { lat: number; lon: number },
  b: { lat: number; lon: number },
) {
  const rad = Math.PI / 180;
  const n =
    Math.sin(((b.lat - a.lat) * rad) / 2) ** 2 +
    Math.cos(a.lat * rad) *
      Math.cos(b.lat * rad) *
      Math.sin(((b.lon - a.lon) * rad) / 2) ** 2;
  return 6371008.8 * 2 * Math.atan2(Math.sqrt(n), Math.sqrt(1 - n));
}
export function resolvedRegion(data: Runtime, lon: number, lat: number) {
  const matches = data.regions
    .filter((r) => pointInPolygon([lon, lat], r))
    .map((r) => r.properties.region_id);
  const remaining = matches.filter(
    (id) =>
      !data.precedence.some(
        (r) => r.loser === id && matches.includes(r.winner),
      ),
  );
  return remaining.length === 1 ? remaining[0] : null;
}
export function habitatAt(data: Runtime, lon: number, lat: number) {
  const region = resolvedRegion(data, lon, lat);
  const zones = data.zones.filter(
    (z) => z.properties.region_id === region && pointInPolygon([lon, lat], z),
  );
  return {
    region,
    zones,
    neutral: data.neutral.some(
      (n) => n.properties.region_id === region && pointInPolygon([lon, lat], n),
    ),
  };
}

type XY = { x: number; y: number };
// A densest fixed-radius disk can be translated/rotated until two points lie on
// its boundary. Testing these pair-defined centres also catches empty-centre clusters.
export function maximumInCircle(
  points: XY[],
  radius = rules.densityRadiusMeters + rules.densityProjectionGuardMeters,
) {
  if (!points.length) return 0;
  let maximum = 1;
  const count = (c: XY) =>
    points.reduce(
      (n, p) => n + (Math.hypot(p.x - c.x, p.y - c.y) <= radius + 1e-6 ? 1 : 0),
      0,
    );
  for (let i = 0; i < points.length; i++) {
    const a = points[i];
    maximum = Math.max(maximum, count(a));
    for (let j = i + 1; j < points.length; j++) {
      const b = points[j],
        dx = b.x - a.x,
        dy = b.y - a.y,
        d = Math.hypot(dx, dy);
      if (d > radius * 2 || d < 1e-9) continue;
      const h = Math.sqrt(Math.max(0, radius * radius - (d * d) / 4));
      for (const sign of [-1, 1])
        maximum = Math.max(
          maximum,
          count({
            x: (a.x + b.x) / 2 - (sign * dy * h) / d,
            y: (a.y + b.y) / 2 + (sign * dx * h) / d,
          }),
        );
    }
  }
  return maximum;
}
export function scheduledSignatures(
  data: Runtime,
  date = dayKey(),
  mode: "real" | "demo" = "real",
): Spawn[] {
  const config = data.signatures;
  if (!config) return [];
  const ordinal = Math.floor(
    (Date.parse(date + "T12:00:00Z") -
      Date.parse(config.schedule.epoch + "T12:00:00Z")) /
      86400000,
  );
  if (
    !Number.isFinite(ordinal) ||
    !Number.isInteger(config.schedule.period_days) ||
    config.schedule.period_days < 2
  )
    throw Error("Invalid Signature schedule");
  const period = config.schedule.period_days;
  const block = Math.floor(ordinal / period);
  const day = ((ordinal % period) + period) % period;
  const anchors = [...new Set(config.entries.map((e) => e.poi_id))].sort();
  const result: Spawn[] = [];
  for (const id of anchors) {
    const seed = `${config.version}:${id}`;
    if (day !== hash(seed + ":day") % period) continue;
    const choices = config.entries
      .filter((e) => e.poi_id === id)
      .sort((a, b) => a.species_id.localeCompare(b.species_id));
    const index =
      (((block + hash(seed + ":species")) % choices.length) + choices.length) %
      choices.length;
    const chosen = choices[index];
    const source = data.pois.find((p) => p.id === id);
    const species = data.modedex.modemon[chosen.species_id];
    if (
      !source?.eligible || !source.special_destination ||
      species?.stage !== 3 || !species.signature
    )
      throw Error(`Invalid approved Signature mapping: ${chosen.species_id}`);
    const safe =
      chosen.safety_status === "mapped_public_approach" && chosen.placement;
    if (chosen.blocked_dates.includes(date) || (!safe && mode !== "demo"))
      continue;
    if (!safe && chosen.safety_status !== "withheld_pending_safe_approach") continue;
    const poi = {
      ...source, ...(safe || {}), association_note: chosen.association_note,
    };
    if (safe && resolvedRegion(data, poi.lon, poi.lat) !== source.region)
      throw Error(`Signature approach outside resolved parent: ${id}`);
    result.push({
      id: `${rules.version}:${config.version}:${date}:${id}:${chosen.species_id}`,
      date,
      speciesId: chosen.species_id,
      rarity: "signature",
      poi,
      basis: [...species.habitats],
      siteNotices: (chosen.site_notices ?? []).filter((n) => n.start_date <= date && (!n.end_date || n.end_date >= date)),
    });
  }
  return result.sort(
    (a, b) =>
      hash(`${config.version}:${date}:${a.poi.id}`) -
        hash(`${config.version}:${date}:${b.poi.id}`) ||
      a.id.localeCompare(b.id),
  );
}

export function buildWorld(
  data: Runtime,
  date = dayKey(),
  mode: "real" | "demo" = "real",
): Spawn[] {
  const salt = `${rules.version}:${data.data_version}:${date}`;
  const candidates = data.pois
    .filter((p) => p.eligible)
    .map((p) => ({ p, rank: hash(`${salt}:${p.id}`) }))
    .sort((a, b) => a.rank - b.rank || a.p.id.localeCompare(b.p.id));
  const accepted: Spawn[] = [];
  const fits = (p: Poi) => {
    const nearby = accepted.filter(
      (s) => Math.hypot(s.poi.x - p.x, s.poi.y - p.y) <=
        (rules.densityRadiusMeters + rules.densityProjectionGuardMeters) * 2,
    );
    return maximumInCircle([...nearby.map((s) => s.poi), p]) <=
      rules.maximumInCircle;
  };
  // Signature slots are admitted first; neither an escape nor a capture backfills
  // their slot or rerolls the date. Ordinary IDs and quiz seeds remain unchanged.
  for (const signature of scheduledSignatures(data, date, mode))
    if (fits(signature.poi)) accepted.push(signature);
  for (const { p } of candidates) {
    if (accepted.some((s) => s.poi.id === p.id)) continue;
    // Never direct ordinary encounters to a known unsafe Signature anchor either.
    if (data.signatures?.entries.some(
      (e) => e.poi_id === p.id &&
        (e.safety_status === "withheld_pending_safe_approach" ||
          e.ordinary_anchor_withheld ||
          e.blocked_dates.includes(date)),
    )) continue;
    const basis = [
      ...new Set(
        [p.primary, p.secondary, ...p.zone_habitats].filter(
          (h): h is string => !!h,
        ),
      ),
    ];
    const eligible = Object.entries(data.modedex.modemon)
      .filter(
        ([, s]) => s.stage < 3 && s.habitats.some((h) => basis.includes(h)),
      )
      .sort(([a], [b]) => a.localeCompare(b));
    const rare = hash(`${salt}:${p.id}:rarity`) / 2 ** 32 < rules.rareFraction;
    const pool = eligible.filter(([, s]) => s.stage === (rare ? 2 : 1));
    const choices = pool.length ? pool : eligible;
    if (!choices.length) continue;
    if (!fits(p)) continue;
    const [speciesId, species] =
      choices[hash(`${salt}:${p.id}:species`) % choices.length];
    accepted.push({
      id: `${salt}:${p.id}`,
      date,
      speciesId,
      rarity: species.rarity,
      poi: p,
      basis,
    });
  }
  return accepted;
}
export function interaction(spawn: Spawn, fix: Fix | null, now = Date.now()) {
  if (!fix)
    return {
      allowed: false,
      reason: "A current foreground GPS fix is required.",
      meters: null,
    };
  if (
    ![fix.lat, fix.lon, fix.timestamp].every(Number.isFinite) ||
    Math.abs(fix.lat) > 90 ||
    Math.abs(fix.lon) > 180
  )
    return {
      allowed: false,
      reason: "GPS coordinates are invalid. Retry location.",
      meters: null,
    };
  if (now - fix.timestamp > rules.maximumFixAgeMs || fix.timestamp > now + 1000)
    return {
      allowed: false,
      reason: "GPS fix is stale. Retry location.",
      meters: null,
    };
  if (
    !Number.isFinite(fix.accuracy) ||
    fix.accuracy > rules.maximumAccuracyMeters ||
    fix.accuracy < 0
  )
    return {
      allowed: false,
      reason: "GPS accuracy must be 50 m or better. Wait in a safe open place.",
      meters: null,
    };
  const meters = distance(fix, spawn.poi);
  const allowance = Math.min(
    rules.maximumAccuracyAllowanceMeters,
    fix.accuracy / 2,
  );
  return {
    allowed: meters <= rules.interactionMeters + allowance,
    meters,
    reason: `${Math.round(meters)} m away. Interaction: 75 m plus at most 10 m GPS tolerance. Never enter an unsafe place.`,
  };
}
export function questionsFor(spawn: Spawn, data: Runtime): Question[] {
  const s = data.modedex.modemon[spawn.speciesId];
  const specs: {
    field: "role" | "input_data" | "output_data";
    prompt: string;
  }[] = [
    { field: "role", prompt: `What is ${s.name}'s real-world job?` },
    {
      field: "input_data",
      prompt: `According to the Modédex, what input does ${s.name} use?`,
    },
    {
      field: "output_data",
      prompt: `According to the Modédex, what output does ${s.name} produce?`,
    },
  ];
  return specs.map(({ field, prompt }, i) => {
    const correct = s[field];
    const distractors = [
      ...new Set(
        Object.values(data.modedex.modemon)
          .filter((o) => o.family_id !== s.family_id)
          .map((o) => o[field]),
      ),
    ]
      .filter((v) => v !== correct)
      .sort(
        (a, b) =>
          hash(`${spawn.id}:${i}:${a}`) - hash(`${spawn.id}:${i}:${b}`) ||
          a.localeCompare(b),
      )
      .slice(0, 3);
    const options = [correct, ...distractors].sort(
      (a, b) =>
        hash(`${spawn.id}:option:${i}:${a}`) -
          hash(`${spawn.id}:option:${i}:${b}`) || a.localeCompare(b),
    );
    return {
      id: `${spawn.id}:q${i + 1}`,
      prompt,
      options,
      correct: options.indexOf(correct),
      explanation: `${s.name} is a ${s.role}. Its input is ${s.input_data}. Its output is ${s.output_data}.`,
    };
  });
}
export function beginAttempt(progress: Progress, spawn: Spawn): Progress {
  if (progress.attempts[spawn.id]) return progress;
  return {
    ...progress,
    discovered: [...new Set([...progress.discovered, spawn.speciesId])].sort(),
    attempts: {
      ...progress.attempts,
      [spawn.id]: {
        answers: [],
        status: "in_progress",
        speciesId: spawn.speciesId,
        poiName: spawn.poi.name,
        date: spawn.date,
      },
    },
  };
}

export function attemptRules(attempt: Attempt | null | undefined) {
  if (
    !attempt ||
    (attempt.quiz_version === undefined &&
      attempt.difficulty === undefined &&
      attempt.questions === undefined)
  )
    return {
      ...quizModes.novice,
      difficulty: "novice" as Difficulty,
      legacy: true,
    };
  if (
    attempt.quiz_version !== 2 ||
    !isDifficulty(attempt.difficulty) ||
    !Array.isArray(attempt.questions)
  )
    throw Error(
      "Saved quiz version or difficulty is unreadable. It was not overwritten.",
    );
  return {
    ...quizModes[attempt.difficulty],
    difficulty: attempt.difficulty,
    legacy: false,
  };
}
export function startAttempt(
  progress: Progress,
  spawn: Spawn,
  data: Runtime,
  difficulty: Difficulty = "novice",
): Progress {
  if (progress.attempts[spawn.id]) return progress;
  const next = beginAttempt(progress, spawn);
  return {
    ...next,
    version: 2,
    attempts: {
      ...next.attempts,
      [spawn.id]: {
        ...next.attempts[spawn.id],
        quiz_version: 2,
        difficulty,
        questions: difficultyQuestionsFor(spawn, data, difficulty),
      },
    },
  };
}
export function changeDifficulty(
  progress: Progress,
  spawn: Spawn,
  data: Runtime,
  difficulty: Difficulty,
): Progress {
  const attempt = progress.attempts[spawn.id];
  if (
    !attempt ||
    attemptRules(attempt).legacy ||
    attempt.status !== "in_progress" ||
    attempt.answers.length
  )
    throw Error("Difficulty is locked for this encounter.");
  if (attempt.difficulty === difficulty) return progress;
  return {
    ...progress,
    attempts: {
      ...progress.attempts,
      [spawn.id]: {
        ...attempt,
        difficulty,
        questions: difficultyQuestionsFor(spawn, data, difficulty),
      },
    },
  };
}
export function questionsForAttempt(
  spawn: Spawn,
  data: Runtime,
  attempt: Attempt,
): Question[] {
  return attemptRules(attempt).legacy
    ? questionsFor(spawn, data)
    : attempt.questions!;
}
export function answerQuestion(
  progress: Progress,
  spawn: Spawn,
  answer: number,
  questions: Question[],
): Progress {
  const attempt = progress.attempts[spawn.id];
  const mode = attemptRules(attempt);
  if (
    !attempt ||
    attempt.status !== "in_progress" ||
    attempt.answers.length >= mode.count
  )
    throw Error("This encounter cannot be answered again.");
  const q = questions[attempt.answers.length];
  if (
    !q ||
    !Number.isInteger(answer) ||
    answer < 0 ||
    answer >= q.options.length ||
    questions.length !== mode.count ||
    (!mode.legacy &&
      JSON.stringify(questions) !== JSON.stringify(attempt.questions))
  )
    throw Error("Invalid question response");
  const answers = [...attempt.answers, answer];
  const correct = answers.filter((v, i) => v === questions[i].correct).length;
  const status =
    answers.length === mode.count
      ? correct >= mode.required
        ? "captured"
        : "escaped"
      : "in_progress";
  return {
    ...progress,
    attempts: {
      ...progress.attempts,
      [spawn.id]: { ...attempt, answers, status },
    },
  };
}
export const progressKey = (mode: string) =>
  `modemon-go:playable:v1:progress:${mode}`;
export function readProgress(
  storage: Pick<Storage, "getItem">,
  mode: string,
): Progress {
  const text = storage.getItem(progressKey(mode));
  if (!text) return emptyProgress();
  const p = JSON.parse(text) as Progress;
  if (
    !p ||
    (p.version !== 1 && p.version !== 2) ||
    !Array.isArray(p.discovered) ||
    !p.discovered.every((id) => typeof id === "string" && id.length > 0) ||
    !p.attempts ||
    typeof p.attempts !== "object" ||
    Array.isArray(p.attempts)
  )
    throw Error("Saved progress is unreadable. It was not overwritten.");
  for (const a of Object.values(p.attempts)) {
    const config = attemptRules(a);
    if (!config.legacy && p.version !== 2)
      throw Error(
        "Difficulty-aware encounters require progress version 2. Nothing was overwritten.",
      );
    if (!config.legacy) {
      const qs = a.questions!;
      if (
        qs.length !== config.count ||
        qs.some(
          (q) =>
            !q ||
            typeof q.id !== "string" ||
            !q.id ||
            typeof q.prompt !== "string" ||
            !q.prompt.trim() ||
            typeof q.explanation !== "string" ||
            !q.explanation.trim() ||
            !Array.isArray(q.options) ||
            q.options.length !== 4 ||
            q.options.some((v) => typeof v !== "string" || !v.trim()) ||
            new Set(q.options).size !== 4 ||
            !Number.isInteger(q.correct) ||
            q.correct < 0 ||
            q.correct > 3,
        ) ||
        new Set(qs.map((q) => q.id)).size !== qs.length
      )
        throw Error(
          "Saved questions are unreadable. They were not overwritten.",
        );
    }
    if (
      !Array.isArray(a.answers) ||
      a.answers.length > config.count ||
      !a.answers.every((v) => Number.isInteger(v) && v >= 0 && v < 4) ||
      !["in_progress", "captured", "escaped"].includes(a.status)
    )
      throw Error("Saved encounter is unreadable. It was not overwritten.");
    if (
      typeof a.speciesId !== "string" ||
      typeof a.poiName !== "string" ||
      typeof a.date !== "string" ||
      (a.status === "in_progress"
        ? a.answers.length === config.count
        : a.answers.length !== config.count)
    )
      throw Error(
        "Saved encounter metadata is unreadable. It was not overwritten.",
      );
    if (!config.legacy && a.status !== "in_progress") {
      const correct = a.answers.filter(
        (v, i) => v === a.questions![i].correct,
      ).length;
      const expected = correct >= config.required ? "captured" : "escaped";
      if (a.status !== expected)
        throw Error(
          "Saved quiz result is inconsistent. It was not overwritten.",
        );
    }
  }
  return p;
}
export function persist(
  storage: Pick<Storage, "setItem" | "getItem">,
  mode: string,
  p: Progress,
) {
  const value = JSON.stringify(p);
  storage.setItem(progressKey(mode), value);
  if (storage.getItem(progressKey(mode)) !== value)
    throw Error("Browser storage did not retain progress.");
}
