import type { Fix, Poi, Runtime, Spawn } from "./engine.ts";
import { interaction } from "./engine.ts";
import { rules } from "./rules.ts";

export function regionLabel(data: Runtime, id: string) {
  return (
    data.regions.find((region) => region.properties.region_id === id)
      ?.properties.display_name ?? "the nearby game area"
  );
}
export function placeLabel(data: Runtime, poi: Poi) {
  return `Near ${poi.name} in ${regionLabel(data, poi.region)}`;
}
export function rarityLabel(rarity: string) {
  return (
    { common: "Common", rare: "Rare", signature: "Signature" }[rarity] ??
    "Mystery"
  );
}
export function markerLabel(data: Runtime, spawn: Spawn) {
  return `Mystery Modémon · ${rarityLabel(spawn.rarity)} · ${placeLabel(data, spawn.poi)}`;
}
export function approximateDistance(meters: number) {
  if (!Number.isFinite(meters) || meters < 0) return "distance unavailable";
  const miles = meters / 1609.344;
  if (meters >= 1609.344 / 4)
    return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: miles < 1 ? 2 : 1 }).format(miles)} mi`;
  const feet = meters / 0.3048;
  const rounded =
    feet < 100
      ? Math.max(meters > 0 ? 1 : 0, Math.round(feet))
      : Math.round(feet / 10) * 10;
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(rounded)} ft`;
}

// These are presentation messages only. The existing interaction() result still
// controls permission to enter, including all accuracy/staleness tolerances.
export function proximityCopy(
  mode: string,
  fix: Fix | null,
  gate: ReturnType<typeof interaction>,
) {
  if (mode === "demo") {
    if (!fix || gate.meters === null)
      return "Tap Simulate walking here to try this encounter without traveling.";
    return gate.allowed
      ? "Your simulated location is close enough to discover this Modémon. This is not your GPS location."
      : `Simulated distance: about ${approximateDistance(gate.meters)}. Tap Simulate walking here to try this encounter without traveling.`;
  }
  if (!fix)
    return "Allow location access to see how close you are, or try Demo Mode without traveling.";
  if (gate.meters === null)
    return "Your phone's location estimate is not accurate or recent enough yet. Wait somewhere safe and try location again.";
  return gate.allowed
    ? `You're about ${approximateDistance(gate.meters)} away. You're close enough to discover this Modémon.`
    : `You're about ${approximateDistance(gate.meters)} away. Get within roughly ${approximateDistance(rules.interactionMeters)} to discover this Modémon, but only if there is a safe public way to get closer.`;
}
export const publicLocationSafety =
  "This Modémon is linked to the nearby location. Stay in public areas; you don't need to enter the business.";
export function extraLocationSafety(poi: Poi) {
  if (poi.id === "RAL-02_osm_way_583072635")
    return "Enjoy the wider public plaza and garden. Do not approach or linger around children's play equipment for the game.";
  const defaultNote =
    "Association only. Never enter restricted areas or obstruct other people.";
  return poi.association_note !== defaultNote ? poi.association_note : null;
}
