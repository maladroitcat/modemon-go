import { attemptRules, type Progress, type Runtime } from "./engine.ts";
import type { Difficulty } from "./quizzes.ts";

// Encounter IDs are the unique keys in attempts. Count each saved success once;
// discoveries, unfinished quizzes and escapes never contribute.
export function captureHistory(progress: Progress) {
  const counts = new Map<string, number>();
  const mastery = new Map<string, Set<Difficulty>>();
  for (const attempt of Object.values(progress.attempts)) {
    if (attempt.status !== "captured") continue;
    counts.set(attempt.speciesId, (counts.get(attempt.speciesId) ?? 0) + 1);
    const earned = mastery.get(attempt.speciesId) ?? new Set<Difficulty>();
    earned.add(attemptRules(attempt).difficulty);
    mastery.set(attempt.speciesId, earned);
  }
  return { collected: new Set(counts.keys()), counts, mastery };
}

export type Achievement = {
  id: string;
  name: string;
  description: string;
  group: "collection" | "family";
  current: number;
  total: number;
  unit: string;
  unlocked: boolean;
  unavailable: number;
};

// Coverage advisory only. This never changes eligibility or completion totals.
// Absence from a short daily rotation is not proof of inaccessibility.
export function speciesWithoutAnchors(data: Runtime) {
  return new Set(Object.entries(data.modedex.modemon).filter(([id, species]) => {
    if (species.stage === 3)
      return !data.signatures?.entries.some((e) =>
        e.species_id === id && e.safety_status === "mapped_public_approach" &&
        e.placement && data.pois.some((p) => p.id === e.poi_id && p.eligible && p.special_destination));
    return !data.pois.some((p) => p.eligible &&
      !data.signatures?.entries.some((e) => e.poi_id === p.id &&
        (e.safety_status === "withheld_pending_safe_approach" || e.ordinary_anchor_withheld)) &&
      species.habitats.some((h) => [p.primary, p.secondary, ...p.zone_habitats].includes(h)));
  }).map(([id]) => id));
}

export function calculateAchievements(progress: Progress, data: Runtime): Achievement[] {
  const { collected, counts, mastery } = captureHistory(progress);
  const entries = Object.entries(data.modedex.modemon);
  const all = entries.map(([id]) => id);
  const unavailable = speciesWithoutAnchors(data);
  const families = [...new Set(entries.map(([, s]) => s.family_id))];
  const speciesGoal = (id: string, name: string, description: string, ids: string[],
    group: Achievement["group"] = "collection", expert = false): Achievement => {
    const current = ids.filter((id) => expert ? mastery.get(id)?.has("expert") : collected.has(id)).length;
    return { id, name, description, group, current, total: ids.length,
      unit: expert ? "species mastered at Expert level" : "species collected",
      unlocked: ids.length > 0 && current === ids.length,
      unavailable: ids.filter((id) => unavailable.has(id) &&
        !(expert ? mastery.get(id)?.has("expert") : collected.has(id))).length };
  };
  const familyCount = families.filter((family) => entries.some(([id, s]) =>
    s.family_id === family && collected.has(id))).length;
  const most = Math.max(0, ...all.map((id) => counts.get(id) ?? 0));
  return [
    { id: "hoarder", name: "Hoarder", description: "Capture five distinct encounters of the same species.",
      group: "collection", current: Math.min(most, 5), total: 5,
      unit: "captures of the same species", unlocked: most >= 5, unavailable: 0 },
    { id: "connoisseur", name: "Connoisseur", description: "Collect at least one species from every AI family.",
      group: "collection", current: familyCount, total: families.length,
      unit: "AI families collected", unlocked: families.length > 0 && familyCount === families.length, unavailable: 0 },
    speciesGoal("model-master", "Model Master", "Collect every Modémon species.", all),
    ...([ ["common", "Common Collector"], ["rare", "Rare Collector"], ["signature", "Special Collector"] ] as const)
      .map(([rarity, name]) => speciesGoal(`${rarity}-collector`, name,
        `Collect every ${rarity === "signature" ? "Signature" : rarity === "rare" ? "Rare" : "Common"} species.`,
        entries.filter(([, s]) => s.rarity === rarity).map(([id]) => id))),
    speciesGoal("master-scholar", "Master Scholar", "Earn an Expert mastery badge for every species.", all, "collection", true),
    ...families.map((family) => speciesGoal(`family-${family}`,
      `${data.modedex.families?.[family]?.name ?? family} Family Expert`,
      "Collect every species in this AI family.",
      entries.filter(([, s]) => s.family_id === family).map(([id]) => id), "family")),
  ];
}

export function newlyUnlocked(before: Achievement[], after: Achievement[]) {
  const earned = new Set(before.filter((a) => a.unlocked).map((a) => a.id));
  return after.filter((a) => a.unlocked && !earned.has(a.id));
}
