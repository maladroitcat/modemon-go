import pointInPolygon from "@turf/boolean-point-in-polygon";
import type { Feature, Polygon, MultiPolygon } from "geojson";
import { rules } from "./rules.ts";

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
  modedex: { modemon: Record<string, Species> };
  regions: Area[];
  zones: Area[];
  neutral: Area[];
  pois: Poi[];
  precedence: { winner: string; loser: string }[];
  habitats: Record<string, string>;
};
export type Spawn = {
  id: string;
  date: string;
  speciesId: string;
  rarity: string;
  poi: Poi;
  basis: string[];
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
};
export type Progress = {
  version: 1;
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
export function buildWorld(data: Runtime, date = dayKey()): Spawn[] {
  const salt = `${rules.version}:${data.data_version}:${date}`;
  const candidates = data.pois
    .filter((p) => p.eligible)
    .map((p) => ({ p, rank: hash(`${salt}:${p.id}`) }))
    .sort((a, b) => a.rank - b.rank || a.p.id.localeCompare(b.p.id));
  const accepted: Spawn[] = [];
  for (const { p } of candidates) {
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
    const nearby = accepted.filter(
      (s) =>
        Math.hypot(s.poi.x - p.x, s.poi.y - p.y) <=
        (rules.densityRadiusMeters + rules.densityProjectionGuardMeters) * 2,
    );
    if (
      maximumInCircle([...nearby.map((s) => s.poi), p]) > rules.maximumInCircle
    )
      continue;
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
export function answerQuestion(
  progress: Progress,
  spawn: Spawn,
  answer: number,
  questions: Question[],
): Progress {
  const attempt = progress.attempts[spawn.id];
  if (
    !attempt ||
    attempt.status !== "in_progress" ||
    attempt.answers.length >= 3
  )
    throw Error("This encounter cannot be answered again.");
  const q = questions[attempt.answers.length];
  if (
    !Number.isInteger(answer) ||
    answer < 0 ||
    answer >= q.options.length ||
    questions.length !== 3
  )
    throw Error("Invalid question response");
  const answers = [...attempt.answers, answer];
  const correct = answers.filter((v, i) => v === questions[i].correct).length;
  const status =
    answers.length === 3
      ? correct >= 2
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
    p.version !== 1 ||
    !Array.isArray(p.discovered) ||
    !p.discovered.every((id) => typeof id === "string" && id.length > 0) ||
    !p.attempts ||
    typeof p.attempts !== "object" ||
    Array.isArray(p.attempts)
  )
    throw Error("Saved progress is unreadable. It was not overwritten.");
  for (const a of Object.values(p.attempts)) {
    if (
      !Array.isArray(a.answers) ||
      a.answers.length > 3 ||
      !a.answers.every((v) => Number.isInteger(v) && v >= 0 && v < 4) ||
      !["in_progress", "captured", "escaped"].includes(a.status)
    )
      throw Error("Saved encounter is unreadable. It was not overwritten.");
    if (
      typeof a.speciesId !== "string" ||
      typeof a.poiName !== "string" ||
      typeof a.date !== "string" ||
      (a.status === "in_progress"
        ? a.answers.length === 3
        : a.answers.length !== 3)
    )
      throw Error(
        "Saved encounter metadata is unreadable. It was not overwritten.",
      );
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
