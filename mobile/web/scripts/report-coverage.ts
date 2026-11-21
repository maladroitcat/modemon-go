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
  habitats = new Set<string>(),
  demoSignatures = new Set<string>();
const dates = Array.from({ length: 32 }, (_, i) => new Date(Date.parse(date + "T12:00:00Z") + i * 86400000).toISOString().slice(0, 10));
const healthcareOnly = Object.entries(data.modedex.modemon).filter(([, s]) =>
  s.stage < 3 && s.habitats.length === 1 && s.habitats[0] === "healthcare").map(([id]) => id);
const healthcareFirst = new Map<string, { species_id: string; name: string; date: string; poi_id: string; poi_name: string }>();
// Longer audit distinguishes infrequent rotation from missing location coverage.
const extendedDates = Array.from({ length: 128 }, (_, i) =>
  new Date(Date.parse(date + "T12:00:00Z") + i * 86400000).toISOString().slice(0, 10));
for (const day of extendedDates) {
  for (const s of buildWorld(data, day)) if (healthcareOnly.includes(s.speciesId) && !healthcareFirst.has(s.speciesId))
    healthcareFirst.set(s.speciesId, { species_id: s.speciesId, name: data.modedex.modemon[s.speciesId].name, date: day, poi_id: s.poi.id, poi_name: s.poi.name });
}
for (const day of dates) {
  for (const s of buildWorld(data, day)) {
    reachable.add(s.speciesId);
    s.basis.forEach((h) => habitats.add(h));
  }
  for (const s of buildWorld(data, day, "demo"))
    if (s.rarity === "signature") demoSignatures.add(s.speciesId);
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
      question_counts: { novice: 3, intermediate: 5, expert: 7 },
    })),
  signatures: {
    version: data.signatures!.version,
    schedule: data.signatures!.schedule,
    approved_mappings: data.signatures!.entries,
    real_enabled: data.signatures!.entries.filter((e) => e.placement).map((e) => e.species_id),
    real_withheld: data.signatures!.entries.filter((e) => !e.placement).map((e) => ({ id: e.species_id, name: data.modedex.modemon[e.species_id].name, reason: e.association_note })),
    demo_observed: [...demoSignatures].sort(),
    reason: "Explicit owner-approved associations. All twelve have reviewed outdoor placement evidence; Durham Station uses the alternative sidewalk by GoDurham stop 6680, not the construction area. On-site closures always override a marker.",
  },
  artwork: {
    approved_creature_images: Object.keys(data.art?.approved ?? {}).length,
    missing_creature_images: 51 - Object.keys(data.art?.approved ?? {}).length,
    used_concepts: [],
    reason:
      "Issue 23 approves the 51 local creature masters and logo. Old Seeklet concepts are not used. Responsive transparent derivatives load on demand, with PNG and explicit missing-art fallbacks.",
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
  healthcare_approvals: data.healthcare_approvals,
  healthcare_rotation_audit: {
    dates: `${extendedDates[0]} through ${extendedDates.at(-1)}`,
    first_observed: [...healthcareFirst.values()],
    unobserved_species: healthcareOnly.filter((id) => !healthcareFirst.has(id)),
  },
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
    dates: `${dates[0]} through ${dates.at(-1)}`,
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
    note: "Twelve existing Healthcare associations have explicit owner approval for outdoor public approaches, effective 2026-11-21. Both Hemp Farmacy records and all other unapproved sensitive facilities remain excluded. Eligible anchors establish possibility; any day's rotation still follows the existing rarity and density rules. RAL-05 remains empty. All twelve Signatures retain their reviewed placements and calendar.",
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
