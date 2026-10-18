import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { buildWorld, type Runtime } from "../../src/engine";

const data = JSON.parse(readFileSync(new URL("../../src/data/runtime.json", import.meta.url), "utf8")) as Runtime;
const art = JSON.parse(readFileSync(new URL("../../src/data/art.json", import.meta.url), "utf8")) as {
  creatures: Record<string, { urls: Record<string, string> }>;
};

test("logo loads alone on map; all 51 discoveries use correct lazy artwork and fit mobile panels", async ({ page }, info) => {
  const requests: string[] = [];
  page.on("request", (request) => { if (request.url().includes("/art/")) requests.push(request.url()); });
  await page.addInitScript((ids) => {
    localStorage.setItem("modemon-go:playable:safety:v1", "1");
    localStorage.setItem("modemon-go:playable:v1:progress:real", JSON.stringify({ version: 1, attempts: {}, discovered: ids }));
  }, Object.keys(data.modedex.modemon));
  await page.goto("/");
  await expect(page.locator(".brand-logo img")).toBeVisible();
  expect(await page.locator(".brand-logo img").evaluate((img) => (img as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  expect(requests.every((url) => url.includes("/art/logo."))).toBe(true);
  // Panning the live map must not fetch anonymous creatures' images.
  const map = await page.locator(".leaflet-container").boundingBox();
  await page.mouse.move(map!.x + map!.width / 2, map!.y + map!.height / 2);
  await page.mouse.down();
  await page.mouse.move(map!.x + map!.width / 2 + 30, map!.y + map!.height / 2 + 30, { steps: 5 });
  await page.mouse.up();
  expect(requests.every((url) => url.includes("/art/logo."))).toBe(true);
  await page.getByRole("button", { name: "Modédex", exact: true }).click();
  for (const [id, species] of Object.entries(data.modedex.modemon)) {
    await page.locator(".dex-row").filter({ hasText: species.name }).click();
    const image = page.getByRole("img", { name: species.name, exact: true });
    await image.scrollIntoViewIfNeeded();
    await expect(image).toBeVisible();
    await expect.poll(() => image.evaluate((img) => (img as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
    expect(Object.values(art.creatures[id].urls)).toContain(
      await image.evaluate((img) => new URL((img as HTMLImageElement).currentSrc).pathname));
    await expect(image).toHaveAttribute("loading", "lazy");
    await expect(image).toHaveAttribute("decoding", "async");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    if (id === "detector_base") await page.screenshot({ path: info.outputPath("seeklet-dex.png"), fullPage: true });
    await page.getByRole("button", { name: "Back to discoveries", exact: true }).click();
  }
  // Responsive images, never full-resolution masters, are the only art requests.
  expect(requests.every((url) => /\.(webp|png)$/.test(url) && !url.includes("originals"))).toBe(true);
});

for (const pngWorks of [true, false]) test(`artwork network failure: PNG fallback ${pngWorks ? "works" : "becomes explicit placeholder"}`, async ({ page }) => {
  await page.clock.setFixedTime(new Date("2026-10-17T16:00:00Z"));
  await page.route("**/art/**", (route) => {
    const url = route.request().url();
    return !url.includes("/art/logo.") && (url.endsWith(".webp") || !pngWorks)
      ? route.fulfill({ status: 404, body: "missing" }) : route.continue();
  });
  await page.addInitScript(() => {
    localStorage.setItem("modemon-go:playable:safety:v1", "1");
    localStorage.setItem("modemon-go:playable:mode", "demo");
  });
  await page.goto("/");
  const spawn = buildWorld(data, "2026-10-17").find((s) => s.poi.region.startsWith("RAL"))!;
  await page.locator(`.encounter-row[data-poi-id="${spawn.poi.id}"]`).click();
  await page.getByRole("button", { name: "Simulate walking here (Demo)", exact: true }).click();
  await page.getByRole("button", { name: "Enter encounter", exact: true }).click();
  if (pngWorks) {
    const image = page.getByRole("img", { name: data.modedex.modemon[spawn.speciesId].name, exact: true });
    await expect.poll(() => image.evaluate((img) => (img as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
    expect(await image.evaluate((img) => (img as HTMLImageElement).currentSrc)).toMatch(/\.png$/);
  } else await expect(page.getByLabel(`Artwork unavailable for ${data.modedex.modemon[spawn.speciesId].name}`)).toBeVisible();
  await page.getByRole("button", { name: /^Inspect / }).click();
  await expect(page.getByRole("button", { name: "Capture · 3 questions", exact: true })).toBeVisible();
});
