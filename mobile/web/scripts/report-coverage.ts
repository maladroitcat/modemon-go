import { readFileSync, writeFileSync } from "node:fs";
import { buildWorld, maximumInCircle, type Runtime } from "../src/engine.ts";
const data = JSON.parse(
  readFileSync(new URL("../src/data/runtime.json", import.meta.url), "utf8"),
) as Runtime;
const date = process.argv[2];
if (!/^\d{4}-\d{2}-\d{2}$/.test(date ?? ""))
  throw Error("Usage: node web/scripts/report-coverage.ts YYYY-MM-DD");
const world = buildWorld(data, date);
const count = (values: string[]) =>
  Object.fromEntries(
    [...new Set(values)]
      .sort()
      .map((v) => [v, values.filter((x) => x === v).length]),
  );
const reachable = new Set<string>(),
  habitats = new Set<string>();
for (let d = 1; d <= 14; d++)
  for (const s of buildWorld(data, `2026-10-${String(d).padStart(2, "0")}`)) {
    reachable.add(s.speciesId);
    s.basis.forEach((h) => habitats.add(h));
  }
const report = {
  date,
  timezone: "America/New_York",
  data_version: data.data_version,
  canonical: {
    species: 51,
    regions: 8,
    zones: 62,
    pois: 927,
    curated_special_destinations: 17,
  },
  enabled_non_signature_catalog: Object.entries(data.modedex.modemon)
    .filter(([, s]) => s.stage < 3)
    .map(([id, s]) => ({
      id,
      name: s.name,
      habitats: s.habitats,
      question_count: 3,
    })),
  signatures: {
    enabled: [],
    disabled: Object.entries(data.modedex.modemon)
      .filter(([, s]) => s.stage === 3)
      .map(([id, s]) => ({ id, name: s.name })),
    reason: "No approved deployment-to-destination schedule/crosswalk.",
  },
  artwork: {
    approved_creature_images: 0,
    missing_creature_images: 51,
    used_concepts: [],
    reason:
      "design.md explicitly marks both existing Seeklet concepts awaiting approval. All rendered creatures use a labeled missing-art placeholder.",
  },
  eligible_anchor_counts: count(
    data.pois.filter((p) => p.eligible).map((p) => p.region),
  ),
  eligible_anchors: data.pois
    .filter((p) => p.eligible)
    .map((p) => ({
      poi_id: p.id,
      name: p.name,
      region: p.region,
      habitats: [p.primary, p.secondary].filter(Boolean),
    })),
  daily_world: {
    total: world.length,
    maximum_in_half_mile_circle: maximumInCircle(world.map((s) => s.poi)),
    by_region: count(world.map((s) => s.poi.region)),
    by_rarity: count(world.map((s) => s.rarity)),
    spawns: world.map((s) => ({
      encounter_id: s.id,
      species_id: s.speciesId,
      species_name: data.modedex.modemon[s.speciesId].name,
      poi_id: s.poi.id,
      poi_name: s.poi.name,
      region: s.poi.region,
      rarity: s.rarity,
      basis: s.basis,
      latitude: s.poi.lat,
      longitude: s.poi.lon,
    })),
  },
  simulation: {
    dates: "2026-10-01 through 2026-10-14",
    observed_species: [...reachable].sort(),
    observed_habitats: [...habitats].sort(),
    unobserved_non_signature_species: Object.entries(data.modedex.modemon)
      .filter(([id, s]) => s.stage < 3 && !reachable.has(id))
      .map(([id, s]) => ({ id, name: s.name })),
    unreachable_non_signature_species: Object.entries(data.modedex.modemon)
      .filter(
        ([, s]) =>
          s.stage < 3 &&
          !data.pois.some(
            (p) =>
              p.eligible &&
              [p.primary, p.secondary, ...p.zone_habitats].some(
                (h) => h && s.habitats.includes(h),
              ),
          ),
      )
      .map(([id, s]) => ({ id, name: s.name })),
    note: "Healthcare-only forms have no eligible public association anchors under the conservative access filter. RAL-05 has no spawns. These are coverage limitations, not claims of 39 reachable forms.",
  },
};
writeFileSync(
  new URL("../coverage.json", import.meta.url),
  JSON.stringify(report, null, 2) + "\n",
);
console.log(
  JSON.stringify({
    world: world.length,
    eligible_anchors: report.eligible_anchors.length,
    observed_species: reachable.size,
    habitats: [...habitats].sort(),
    maximum_in_circle: report.daily_world.maximum_in_half_mile_circle,
  }),
);
