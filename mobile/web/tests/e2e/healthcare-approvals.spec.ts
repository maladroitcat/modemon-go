import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { buildWorld, type Runtime } from "../../src/engine";
import { difficultyQuestionsFor } from "../../src/quizzes";

const data = JSON.parse(readFileSync(new URL("../../src/data/runtime.json", import.meta.url), "utf8")) as Runtime;
const report = JSON.parse(readFileSync(new URL("../../coverage.json", import.meta.url), "utf8")) as {
  healthcare_rotation_audit: { first_observed: { species_id: string; date: string; poi_id: string }[] };
};
async function setup(page: Page, date: string, mode: "real" | "demo") {
  await page.clock.setFixedTime(new Date(`${date}T16:00:00Z`));
  await page.addInitScript((mode) => {
    localStorage.setItem("modemon-go:playable:safety:v1", "1");
    localStorage.setItem("modemon-go:playable:mode", mode);
  }, mode);
  await page.goto("/");
}

test("all five Healthcare-only species can be captured on actual rotations; mastery and Demo progress persist", async ({ page }, info) => {
  test.setTimeout(60000);
  const records = report.healthcare_rotation_audit.first_observed;
  expect(records).toHaveLength(5);
  await setup(page, records[0].date, "demo");
  let captures = 0;
  for (const record of records) {
    await page.clock.setFixedTime(new Date(`${record.date}T16:00:00Z`));
    await page.reload();
    const spawn = buildWorld(data, record.date, "demo").find((s) => s.poi.id === record.poi_id)!;
    expect(spawn.speciesId).toBe(record.species_id);
    expect(spawn.poi.public_approach_approval).toBeTruthy();
    await page.getByRole("combobox", { name: "Browse city" }).selectOption(spawn.poi.region.startsWith("DUR") ? "Durham" : "Raleigh");
    await page.locator(`.encounter-row[data-poi-id="${spawn.poi.id}"]`).click();
    await expect(page.getByRole("dialog")).toContainText("Do not enter healthcare buildings");
    await expect(page.getByRole("button", { name: "Enter encounter", exact: true })).toBeDisabled();
    await page.getByRole("button", { name: "Simulate walking here (Demo)", exact: true }).click();
    await page.getByRole("button", { name: "Enter encounter", exact: true }).click();
    await page.getByRole("button", { name: /^Inspect / }).click();
    await page.getByRole("button", { name: "Capture · 3 questions", exact: true }).click();
    for (const [i, q] of difficultyQuestionsFor(spawn, data, "novice").entries()) {
      await page.getByRole("button", { name: q.options[q.correct], exact: true }).click();
      await page.getByRole("button", { name: i === 2 ? "Show result" : "Next question", exact: true }).click();
    }
    await expect(page.getByRole("heading", { name: "Captured!", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Return to map", exact: true }).click();
    captures++;
    await expect(page.locator("header")).toContainText(`${captures} captured`);
    await page.reload();
    await expect(page.locator(`.encounter-row[data-poi-id="${spawn.poi.id}"]`)).toHaveCount(0);
  }
  await page.getByRole("button", { name: "Modédex", exact: true }).click();
  await expect(page.locator(".dex-row .mastery-badge.novice.earned")).toHaveCount(5);
  await page.getByRole("button", { name: "Badges", exact: true }).click();
  await expect(page.locator(".coverage-note")).toHaveCount(0);
  await expect(page.getByRole("article", { name: "Model Master", exact: true })).toContainText("5 of 51");
  await page.screenshot({ path: info.outputPath("healthcare-coverage.png"), fullPage: true });
  await page.getByRole("button", { name: "Exit Demo Mode", exact: true }).click();
  await expect(page.locator("header")).toContainText("0 captured");
});

test("Student Health exterior needs real proximity plus public-approach acknowledgment", async ({ page, context }, info) => {
  const date = "2026-12-08";
  const spawn = buildWorld(data, date).find((s) => s.poi.id === "RAL-03A_osm_way_47917752")!;
  expect(spawn).toBeTruthy();
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({ latitude: spawn.poi.lat, longitude: spawn.poi.lon, accuracy: 5 });
  // Match the browser API's timestamps to the fixed rotation clock.
  await page.addInitScript(() => {
    const native = navigator.geolocation;
    Object.defineProperty(navigator, "geolocation", { configurable: true, value: {
      watchPosition: (success: PositionCallback, error?: PositionErrorCallback, options?: PositionOptions) =>
        native.watchPosition((p) => success({ coords: p.coords, timestamp: Date.now() } as GeolocationPosition), error, options),
      clearWatch: native.clearWatch.bind(native),
    } });
  });
  await setup(page, date, "real");
  await page.getByRole("button", { name: "Allow foreground location", exact: true }).click();
  await expect(page.getByText(/Real GPS · accuracy/)).toBeVisible();
  await page.locator(`.encounter-row[data-poi-id="${spawn.poi.id}"]`).click();
  const enter = page.getByRole("button", { name: "Enter encounter", exact: true });
  await expect(enter).toBeDisabled();
  await expect(page.getByRole("dialog")).toContainText("patient-only areas remain excluded");
  await page.getByRole("checkbox", { name: /I am stopped safely/ }).check();
  await expect(enter).toBeEnabled();
  await context.setGeolocation({ latitude: spawn.poi.lat + .002, longitude: spawn.poi.lon, accuracy: 5 });
  await expect(enter).toBeDisabled();
  await context.setGeolocation({ latitude: spawn.poi.lat, longitude: spawn.poi.lon, accuracy: 5 });
  await expect(enter).toBeEnabled();
  await page.screenshot({ path: info.outputPath("student-health-public-approach.png") });
  await enter.click();
  await expect(page.getByRole("button", { name: /^Inspect / })).toBeVisible();
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem("modemon-go:playable:v1:progress:real")!));
  expect(saved.attempts[spawn.id].status).toBe("in_progress");
  expect(await page.evaluate(() => localStorage.getItem("modemon-go:playable:v1:progress:demo"))).toBeNull();
});
