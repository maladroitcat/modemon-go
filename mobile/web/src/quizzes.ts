import {
  hash,
  questionsFor,
  type Question,
  type Runtime,
  type Spawn,
} from "./engine.ts";

export const quizModes = {
  novice: { label: "Novice", count: 3, required: 2 },
  intermediate: { label: "Intermediate", count: 5, required: 3 },
  expert: { label: "Expert", count: 7, required: 4 },
} as const;
export type Difficulty = keyof typeof quizModes;
export type Source = { path: string; value: string };
export type QuizTopic =
  | "role"
  | "input_data"
  | "output_data"
  | "family_id"
  | "habitats"
  | "models_algorithms"
  | "explainability"
  | "biases_limitations";
export type GroundedQuestion = Question & {
  topic: QuizTopic;
  source: Source;
  option_sources: Source[];
};
export function isDifficulty(value: unknown): value is Difficulty {
  return typeof value === "string" && Object.hasOwn(quizModes, value);
}
const habitatLabels: Record<string, string> = {
  healthcare: "Healthcare",
  finance: "Finance",
  retail: "Retail",
  food_hospitality: "Food & Hospitality",
  education_research: "Education & Research",
  transportation: "Transportation",
  civic_government: "Civic & Government",
  entertainment: "Entertainment",
  office_business: "Office & Business",
};
const ordered = <T>(items: T[], seed: string, value: (item: T) => string) =>
  [...items].sort(
    (a, b) =>
      hash(`${seed}:${value(a)}`) - hash(`${seed}:${value(b)}`) ||
      value(a).localeCompare(value(b)),
  );
const norm = (s: string) => s.trim().toLowerCase().replace(/\s+/g, " ");

function sources(data: Runtime, id: string, topic: QuizTopic): Source[] {
  const species = data.modedex.modemon[id];
  if (topic === "family_id") {
    const family = data.modedex.families?.[species.family_id];
    if (!family?.name) throw Error(`Missing canonical family for ${id}`);
    return [{ path: `families.${species.family_id}.name`, value: family.name }];
  }
  const value = species[topic];
  return typeof value === "string"
    ? [{ path: `modemon.${id}.${topic}`, value }]
    : value.map((text, i) => ({
        path: `modemon.${id}.${topic}.${i}`,
        value: text,
      }));
}
function label(source: Source, topic: QuizTopic) {
  return topic === "habitats" ? habitatLabels[source.value] : source.value;
}

export function difficultyQuestionsFor(
  spawn: Spawn,
  data: Runtime,
  difficulty: Difficulty,
): GroundedQuestion[] {
  if (!isDifficulty(difficulty)) throw Error("Unknown quiz difficulty");
  const species = data.modedex.modemon[spawn.speciesId];
  if (!species || (species.stage === 3 && !data.signatures?.entries.some((e) => e.species_id === spawn.speciesId)))
    throw Error("Quizzes require a canonical Modémon with explicit Signature approval");
  const basic: GroundedQuestion[] = questionsFor(spawn, data).map((q, i) => {
    const topic = (["role", "input_data", "output_data"] as const)[i];
    const option_sources = q.options.map((value) => {
      const match = Object.keys(data.modedex.modemon)
        .sort()
        .flatMap((id) => sources(data, id, topic))
        .find((source) => source.value === value);
      if (!match)
        throw Error(`Unsupported ${topic} option for ${spawn.speciesId}`);
      return match;
    });
    const explanation =
      topic === "role"
        ? `${species.name}'s role in the Modédex is ${species.role}.`
        : `${species.name}'s Modédex ${topic === "input_data" ? "input" : "output"} is ${species[topic]}.`;
    return {
      ...q,
      explanation,
      topic,
      source: sources(data, spawn.speciesId, topic)[0],
      option_sources,
    };
  });
  if (difficulty === "novice")
    return validateQuiz(basic, data, spawn.speciesId, difficulty);

  // A deterministic two-of-three rotation keeps the five-question tier balanced.
  const questions = ordered(basic, `${spawn.id}:basics`, (q) => q.topic).slice(
    0,
    2,
  );
  const topics: QuizTopic[] = ["family_id", "habitats", "models_algorithms"];
  if (difficulty === "expert")
    topics.push("explainability", "biases_limitations");
  const prompts: Partial<Record<QuizTopic, string>> = {
    family_id: `Which AI family does ${species.name} belong to in the Modédex?`,
    habitats: `Which habitat is listed for ${species.name} in the Modédex? Think environment, not a claim about this place's software.`,
    models_algorithms: `Which representative technique is listed for ${species.name} in the Modédex?`,
    explainability: `Which way to inspect or explain results is listed for ${species.name} in the Modédex?`,
    biases_limitations: `Which limitation does ${species.name}'s Modédex entry explicitly warn about?`,
  };
  for (const topic of topics) {
    const seed = `${spawn.id}:quiz-v2:${topic}`;
    const own = sources(data, spawn.speciesId, topic);
    if (!own.length || own.some((s) => !s.value.trim()))
      throw Error(`Missing ${topic} for ${spawn.speciesId}`);
    const answer = ordered(own, seed, (s) => s.value)[0];
    // Exclude the entire family's listed values, not just the chosen answer.
    // Wording asks what this entry lists, never claims other techniques cannot work.
    const excluded = new Set(
      Object.entries(data.modedex.modemon)
        .filter(([, s]) => s.family_id === species.family_id)
        .flatMap(([id]) => sources(data, id, topic))
        .map((s) => norm(s.value)),
    );
    const distinct = new Map<string, Source>();
    for (const id of Object.keys(data.modedex.modemon).sort())
      for (const source of sources(data, id, topic))
        if (
          !excluded.has(norm(source.value)) &&
          !distinct.has(norm(source.value))
        )
          distinct.set(norm(source.value), source);
    // A broad family's habitat union can cover everything; only the target's own
    // habitats are correct for this explicitly entry-scoped question.
    if (topic === "habitats") {
      distinct.clear();
      for (const id of Object.keys(data.modedex.modemon).sort())
        for (const source of sources(data, id, topic))
          if (
            !own.some((s) => s.value === source.value) &&
            !distinct.has(source.value)
          )
            distinct.set(source.value, source);
    }
    const wrong = ordered(
      [...distinct.values()],
      seed + ":distractors",
      (s) => s.value,
    ).slice(0, 3);
    if (wrong.length !== 3)
      throw Error(
        `Cannot make four supported choices: ${spawn.speciesId}/${topic}`,
      );
    const option_sources = ordered(
      [answer, ...wrong],
      seed + ":options",
      (s) => s.value,
    );
    const value = label(answer, topic);
    const explanations: Partial<Record<QuizTopic, string>> = {
      family_id: `${species.name} belongs to the ${value} family in the Modédex.`,
      habitats: `${species.name}'s listed habitats include ${value}. A habitat is environmental context, not proof of deployment at this place.`,
      models_algorithms: `The Modédex lists ${value} as a representative technique for ${species.name}. This is an example, not an exclusive technique or a deployment claim.`,
      explainability: `For inspecting or explaining ${species.name}, its entry lists ${value}. This describes a supported analysis approach, not a claim about live monitoring here.`,
      biases_limitations: `${species.name}'s entry warns: ${value}. This is a possible limitation to consider, not a claim that every use fails this way.`,
    };
    questions.push({
      id: `${seed}`,
      topic,
      prompt: prompts[topic]!,
      options: option_sources.map((s) => label(s, topic)),
      correct: option_sources.indexOf(answer),
      explanation: explanations[topic]!,
      source: answer,
      option_sources,
    });
  }
  return validateQuiz(questions, data, spawn.speciesId, difficulty);
}

export function sourceValue(data: Runtime, path: string): unknown {
  return path
    .split(".")
    .reduce<unknown>(
      (value, key) =>
        value && typeof value === "object"
          ? (value as Record<string, unknown>)[key]
          : undefined,
      data.modedex,
    );
}
export function validateQuiz(
  questions: GroundedQuestion[],
  data: Runtime,
  speciesId: string,
  difficulty: Difficulty,
) {
  if (
    questions.length !== quizModes[difficulty].count ||
    new Set(questions.map((q) => q.topic)).size !== questions.length
  )
    throw Error(
      `Invalid question count or repeated topic: ${speciesId}/${difficulty}`,
    );
  for (const q of questions) {
    const own = sources(data, speciesId, q.topic);
    if (
      q.options.length !== 4 ||
      new Set(q.options.map(norm)).size !== 4 ||
      q.options.some((o) => !o?.trim() || o.length > 180) ||
      !q.prompt.trim() ||
      !q.explanation.trim() ||
      !own.some(
        (s) => s.path === q.source.path && s.value === q.source.value,
      ) ||
      q.option_sources.length !== 4 ||
      !Number.isInteger(q.correct) ||
      q.correct < 0 ||
      q.correct > 3
    )
      throw Error(`Invalid or excessive quiz choices: ${speciesId}/${q.topic}`);
    q.option_sources.forEach((source, i) => {
      if (
        sourceValue(data, source.path) !== source.value ||
        label(source, q.topic) !== q.options[i]
      )
        throw Error(`Unsupported source: ${speciesId}/${q.topic}/${i}`);
      if (
        i !== q.correct &&
        own.some((s) => norm(label(s, q.topic)) === norm(q.options[i]))
      )
        throw Error(`Another supported answer: ${speciesId}/${q.topic}/${i}`);
    });
    if (q.options[q.correct] !== label(q.source, q.topic))
      throw Error(`Incorrect source key: ${speciesId}/${q.topic}`);
  }
  return questions;
}
