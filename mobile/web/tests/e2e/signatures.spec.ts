import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { buildWorld, type Runtime, type Spawn } from "../../src/engine";
import { difficultyQuestionsFor, quizModes, type Difficulty } from "../../src/quizzes";
import { markerLabel } from "../../src/presentation";
import { signatureProject } from "../../src/signatures";

const data = JSON.parse(readFileSync(new URL("../../src/data/runtime.json", import.meta.url), "utf8")) as Runtime;
const bySpecies = new Map<string, Spawn>();
for (let i = 0; i < 24; i++) {
  const date = new Date(Date.UTC(2026, 9, 18 + i)).toISOString().slice(0, 10);
  for (const s of buildWorld(data, date, "demo"))
    if (s.rarity === "signature" && !bySpecies.has(s.speciesId)) bySpecies.set(s.speciesId, s);
}
if (bySpecies.size !== 12) throw Error("Both city demos must expose every approved Signature over a rotation");

for (const spawn of bySpecies.values()) for (const mode of Object.keys(quizModes) as Difficulty[]) {
  const species = data.modedex.modemon[spawn.speciesId];
  test(`${species.name}: ${mode} scheduled Demo encounter, attribution, persisted ${mode === "expert" ? "escape" : "capture"}`, async ({ page }, info) => {
    await page.clock.setFixedTime(new Date(`${spawn.date}T16:00:00Z`));
    await page.goto("/");
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: "Start Playing", exact: true }).click();
    await page.getByRole("button", { name: "Try Demo Mode", exact: true }).click();
    await page.getByRole("combobox", { name: "Browse city" }).selectOption(spawn.poi.region.startsWith("RAL") ? "Raleigh" : "Durham");
    const row = page.locator(`.encounter-row[data-poi-id="${spawn.poi.id}"]`);
    await expect(row).toHaveCount(1);
    await expect(row).toContainText("Signature");
    await expect(row).not.toContainText(species.name);
    await expect(page.getByRole("button", { name: markerLabel(data, spawn), exact: true })).toBeVisible();
    await row.click();
    await expect(page.getByRole("heading", { name: "Mystery Modémon · Signature", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Enter encounter", exact: true })).toBeDisabled();
    await expect(page.getByRole("dialog").getByText("DEMO LOCATION — not your GPS", { exact: true })).toBeVisible();
    if (spawn.poi.id === "DUR-01_osm_node_5844548329")
      await expect(page.getByRole("note", { name: "Site access notice" })).toContainText("GoDurham stop 6680");
    await page.getByRole("button", { name: "Simulate walking here (Demo)", exact: true }).click();
    await page.getByRole("button", { name: "Enter encounter", exact: true }).click();
    const art = page.getByRole("img", { name: species.name, exact: true });
    await expect.poll(() => art.evaluate((img) => (img as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
    await expect(art).toHaveAttribute("src", new RegExp(`/art/${spawn.speciesId}\\.`));
    await page.getByRole("button", { name: /^Inspect / }).click();
    const project = signatureProject(species)!;
    await expect(page.locator(".signature-inspiration")).toHaveText(project.introduction!);
    await expect(page.getByRole("link", { name: `Learn about the real project for ${species.name} (opens in a new tab)` })).toHaveAttribute("href", project.href!);
    await expect(page.getByText(/not a claim that this system runs at your/)).toBeVisible();
    await page.getByRole("radio", { name: `${quizModes[mode].label} ${quizModes[mode].count} questions` }).check();
    await expect(page.locator(".difficulty-picker")).not.toContainText(/correct|required/);
    for (const size of [{ width: 320, height: 568 }, { width: 393, height: 852 }, { width: 844, height: 390 }]) {
      await page.setViewportSize(size);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    }
    await page.setViewportSize({ width: 393, height: 852 });
    if (mode === "novice") await page.screenshot({ path: info.outputPath(`${spawn.speciesId}-project.png`) });
    await page.getByRole("button", { name: `Capture · ${quizModes[mode].count} questions`, exact: true }).click();
    const qs = difficultyQuestionsFor(spawn, data, mode);
    for (const [i, q] of qs.entries()) {
      const right = mode !== "expert";
      await page.getByRole("button", { name: q.options[right ? q.correct : (q.correct + 1) % 4], exact: true }).click();
      await expect(page.locator(right ? ".feedback--correct" : ".feedback--incorrect")).toBeVisible();
      await page.getByRole("button", { name: i === qs.length - 1 ? "Show result" : "Next question", exact: true }).click();
    }
    await expect(page.getByRole("heading", { name: mode === "expert" ? "It escaped." : "Captured!", exact: true })).toBeVisible();
    await page.reload();
    const attempt = await page.evaluate((id) => JSON.parse(localStorage.getItem("modemon-go:playable:v1:progress:demo")!).attempts[id], spawn.id);
    expect(attempt.speciesId).toBe(spawn.speciesId);
    expect(attempt.difficulty).toBe(mode);
    expect(attempt.status).toBe(mode === "expert" ? "escaped" : "captured");
    expect(attempt.questions).toEqual(qs);
    // City resets on reload; select it again before testing absence.
    await page.getByRole("combobox", { name: "Browse city" }).selectOption(spawn.poi.region.startsWith("RAL") ? "Raleigh" : "Durham");
    await expect(row).toHaveCount(0);
    await page.getByRole("button", { name: "Exit Demo Mode", exact: true }).click();
    await expect(page.locator("header")).toContainText("0 captured");
    expect(await page.evaluate(() => JSON.parse(localStorage.getItem("modemon-go:playable:v1:progress:real")!).attempts)).toEqual({});
  });
}

for (const id of ["extractor_specimen", "scheduler_ride_booking", "scheduler_transit_flow"]) test(`${id}: real Signature uses outdoor placement and requires GPS plus an explicit safe-approach acknowledgement`, async ({ page, context }) => {
  const spawn = [...bySpecies.values()].find((s) => s.speciesId === id)!;
  await page.clock.setFixedTime(new Date(`${spawn.date}T16:00:00Z`));
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({ latitude: spawn.poi.lat, longitude: spawn.poi.lon, accuracy: 5 });
  // Browser emulation supplies wall-clock timestamps, not the fixture's date.
  await page.addInitScript(() => {
    const watch = navigator.geolocation.watchPosition.bind(navigator.geolocation);
    navigator.geolocation.watchPosition = (success, error, options) => watch((p) => success({ coords: p.coords, timestamp: Date.now() } as GeolocationPosition), error, options);
  });
  await page.goto("/");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Start Playing", exact: true }).click();
  await page.getByRole("button", { name: /Allow foreground location/ }).click();
  await page.getByRole("combobox", { name: "Browse city" }).selectOption(spawn.poi.region.startsWith("RAL") ? "Raleigh" : "Durham");
  await page.locator(`.encounter-row[data-poi-id="${spawn.poi.id}"]`).click();
  if (id.startsWith("scheduler_")) {
    await expect(page.getByRole("note", { name: "Site access notice" })).toContainText("GoDurham stop 6680");
    await expect(page.getByRole("link", { name: "Official access notice", exact: true }))
      .toHaveAttribute("href", "https://godurhamtransit.org/durham-station-renovations/");
  }
  await expect(page.getByText(/You're close enough to discover/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Enter encounter", exact: true })).toBeDisabled();
  await page.getByRole("checkbox", { name: /I am stopped safely on an open public pedestrian approach/ }).check();
  await page.getByRole("button", { name: "Enter encounter", exact: true }).click();
  await expect(page.getByRole("button", { name: `Inspect ${data.modedex.modemon[id].name}` })).toBeVisible();
});

test("Demo date preview exposes the full rare rotation without faking GPS or resetting saved attempts", async ({ page }) => {
  await page.clock.setFixedTime(new Date("2026-10-18T16:00:00Z"));
  const spawn = bySpecies.get("extractor_history")!;
  await page.goto("/");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Start Playing", exact: true }).click();
  await page.getByRole("button", { name: "Try Demo Mode", exact: true }).click();
  const select = page.getByRole("combobox", { name: "Demo rotation (simulated date)" });
  await select.selectOption(spawn.date);
  const open = async () => {
    await page.locator(`.encounter-row[data-poi-id="${spawn.poi.id}"]`).click();
    await page.getByRole("button", { name: "Simulate walking here (Demo)", exact: true }).click();
    await page.getByRole("button", { name: "Enter encounter", exact: true }).click();
    await page.getByRole("button", { name: /^Inspect / }).click();
  };
  await open();
  await page.getByRole("radio", { name: "Expert 7 questions" }).check();
  const bank = difficultyQuestionsFor(spawn, data, "expert");
  await page.getByRole("button", { name: "Capture · 7 questions", exact: true }).click();
  await page.getByRole("button", { name: bank[0].options[bank[0].correct], exact: true }).click();
  // Tick past the app's midnight-check interval: the simulated day stays open.
  await page.waitForTimeout(1100);
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.reload();
  await select.selectOption(spawn.date);
  await open();
  await expect(page.getByRole("radio", { name: "Expert 7 questions" })).toBeChecked();
  await expect(page.getByRole("radio", { name: "Novice 3 questions" })).toBeDisabled();
  await expect(page.getByRole("dialog")).toContainText("DEMO LOCATION — not your GPS");
  const saved = await page.evaluate((id) => JSON.parse(localStorage.getItem("modemon-go:playable:v1:progress:demo")!).attempts[id], spawn.id);
  expect(saved.answers).toHaveLength(1);
  expect(saved.questions).toEqual(bank);
});
