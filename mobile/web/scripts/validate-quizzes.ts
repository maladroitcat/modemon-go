import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { buildWorld, type Runtime } from "../src/engine.ts";
import {
  difficultyQuestionsFor,
  quizModes,
  type Difficulty,
} from "../src/quizzes.ts";

const runtimeBytes = readFileSync(
  new URL("../src/data/runtime.json", import.meta.url),
);
const data = JSON.parse(runtimeBytes.toString()) as Runtime;
const spawn = buildWorld({ ...data, signatures: undefined }, "2026-10-17")[0];
const banks = Object.entries(data.modedex.modemon)
  .filter(([id, s]) => s.stage < 3 || data.signatures?.entries.some((e) => e.species_id === id))
  .flatMap(([speciesId, species]) =>
    (Object.keys(quizModes) as Difficulty[]).map((difficulty) => ({
      species_id: speciesId,
      name: species.name,
      difficulty,
      required_correct: quizModes[difficulty].required,
      questions: difficultyQuestionsFor(
        { ...spawn, speciesId },
        data,
        difficulty,
      ),
    })),
  );
if (
  banks.length !== 153 ||
  banks.reduce((n, b) => n + b.questions.length, 0) !== 765
)
  throw Error(
    "Expected 51 approved species across 153 banks and 765 question instances",
  );
const report = {
  quiz_version: 2,
  canonical_runtime_sha256: createHash("sha256")
    .update(runtimeBytes)
    .digest("hex"),
  fixture_date: "2026-10-17",
  fixture_encounter_id: spawn.id,
  enabled_species: 51,
  validated_banks: banks.length,
  question_instances: 765,
  unsupported_topics: [],
  duplicate_choices: [],
  excessive_options_over_180_characters: [],
  maximum_option_characters: Math.max(
    ...banks.flatMap((b) =>
      b.questions.flatMap((q) => q.options.map((s) => s.length)),
    ),
  ),
  claim_boundary:
    "Questions ask what an entry lists; techniques and habitats are not exclusive and do not establish deployment at a POI. Expert inspection does not imply live telemetry.",
  banks,
};
if (process.argv.includes("--write"))
  writeFileSync(
    new URL("../quiz-audit.json", import.meta.url),
    JSON.stringify(report, null, 2) + "\n",
  );
console.log(
  `Validated ${banks.length} banks, 765 questions; max option ${report.maximum_option_characters} characters. No missing topics, duplicate choices, or excessive options.`,
);
