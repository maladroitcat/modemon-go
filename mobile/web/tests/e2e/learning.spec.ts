import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import type { Runtime } from "../../src/engine";
import { buildWorld } from "../../src/engine";
import { learningFor } from "../../src/learning";
import { signatureProject } from "../../src/signatures";

const data = JSON.parse(readFileSync(new URL("../../src/data/runtime.json", import.meta.url), "utf8")) as Runtime;
async function discovered(page: Page, ids: string[] = []) {
  await page.addInitScript((ids) => {
    localStorage.setItem("modemon-go:playable:safety:v1", "1");
    localStorage.setItem("modemon-go:playable:v1:progress:real", JSON.stringify({ version: 1, discovered: ids, attempts: {} }));
  }, ids);
  await page.goto("/");
  await page.getByRole("button", { name: "Modédex", exact: true }).click();
}

test("all 39 learning sections and 12 project-only entries fit iPhone layouts without creating progress", async ({ page }, info) => {
  test.setTimeout(90000);
  const educationRequests: string[] = [];
  page.on("request", (r) => { if (/workbook\.com|news\.mit\.edu|ibm\.com|blog\.optibus\.com/.test(r.url())) educationRequests.push(r.url()); });
  await discovered(page, Object.keys(data.modedex.modemon));
  const progress = await page.evaluate(() => localStorage.getItem("modemon-go:playable:v1:progress:real"));
  for (const [id, species] of Object.entries(data.modedex.modemon)) {
    await page.locator(".dex-row").filter({ hasText: species.name }).click();
    const links = learningFor(id, species);
    if (species.stage === 3) {
      await expect(page.locator(".learning-links")).toHaveCount(0);
      await expect(page.locator(".dex-entry a")).toHaveCount(1);
      await expect(page.locator(".signature-project a")).toHaveAttribute("href", signatureProject(species)!.href!);
    } else {
      const section = page.getByRole("region", { name: `Learn about this kind of AI for ${species.name}`, exact: true });
      await expect(section.getByRole("link")).toHaveCount(links.length);
      for (const link of links) {
        const anchor = section.getByRole("link", { name: `Read ${link.title} from ${link.source} (opens in a new tab)`, exact: true });
        await expect(anchor).toHaveAttribute("href", link.url);
        await expect(anchor).toHaveAttribute("target", "_blank");
        await expect(anchor).toHaveAttribute("rel", "noopener noreferrer");
      }
      for (const [width, height] of [[320, 568], [393, 852], [844, 390]]) {
        await page.setViewportSize({ width, height });
        const anchor = section.getByRole("link").first();
        await anchor.scrollIntoViewIfNeeded();
        await expect(anchor).toBeVisible();
        expect((await anchor.boundingBox())!.height).toBeGreaterThanOrEqual(44);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
        if (id === "scheduler_transit" || id === "detector_disease")
          await page.screenshot({ path: info.outputPath(`${id}-${width}.png`) });
      }
    }
    await page.getByRole("button", { name: "Back to discoveries", exact: true }).click();
  }
  expect(educationRequests).toEqual([]);
  expect(await page.evaluate(() => localStorage.getItem("modemon-go:playable:v1:progress:real"))).toBe(progress);
});

for (const id of ["detector_base", "scheduler_hospital", "recommender_ai_curator"]) {
  test(`keyboard-accessible ${id} link opens exact source in a safe new tab and preserves progress`, async ({ page }) => {
    const species = data.modedex.modemon[id];
    await discovered(page, [id]);
    await page.locator(".dex-row").filter({ hasText: species.name }).click();
    const href = species.stage === 3 ? signatureProject(species)!.href! : learningFor(id, species)[0].url;
    const anchor = page.locator(species.stage === 3 ? ".signature-project a" : ".learning-links a").first();
    const before = await page.evaluate(() => JSON.stringify(localStorage));
    await page.context().route(href, (r) => r.fulfill({ contentType: "text/html", body: "<title>Educational navigation QA</title>" }));
    await anchor.focus();
    await expect(anchor).toBeFocused();
    const pending = page.waitForEvent("popup");
    await page.keyboard.press("Enter");
    const popup = await pending;
    await popup.waitForLoadState("domcontentloaded");
    await expect(popup).toHaveURL(href);
    expect(await popup.evaluate(() => window.opener === null)).toBe(true);
    await popup.close();
    await expect(page.locator(".dex-entry h2")).toHaveText(species.name);
    expect(await page.evaluate(() => JSON.stringify(localStorage))).toBe(before);
  });
}

test("locked species reveal no identity or learning section", async ({ page }) => {
  await discovered(page);
  await expect(page.locator(".dex-row")).toHaveCount(0);
  await expect(page.locator(".learning-links, .signature-project")).toHaveCount(0);
  for (const species of Object.values(data.modedex.modemon))
    await expect(page.getByRole("button", { name: new RegExp(`^${species.name} `) })).toHaveCount(0);
});

test("learning link is also available during an encounter without changing its saved attempt", async ({ page }) => {
  await page.clock.setFixedTime(new Date("2026-10-17T16:00:00Z"));
  await page.addInitScript(() => {
    localStorage.setItem("modemon-go:playable:safety:v1", "1");
    localStorage.setItem("modemon-go:playable:mode", "demo");
  });
  await page.goto("/");
  const spawn = buildWorld(data, "2026-10-17", "demo").find((s) => s.poi.region.startsWith("RAL") && s.rarity !== "signature")!;
  await page.locator(`.encounter-row[data-poi-id="${spawn.poi.id}"]`).click();
  await page.getByRole("button", { name: "Simulate walking here (Demo)", exact: true }).click();
  await page.getByRole("button", { name: "Enter encounter", exact: true }).click();
  await page.getByRole("button", { name: /^Inspect / }).click();
  await expect(page.getByRole("dialog").locator(".learning-links a").first()).toHaveAttribute("href",
    learningFor(spawn.speciesId, data.modedex.modemon[spawn.speciesId])[0].url);
  const before = await page.evaluate(() => localStorage.getItem("modemon-go:playable:v1:progress:demo"));
  await page.getByRole("button", { name: "Close encounter", exact: true }).click();
  expect(await page.evaluate(() => localStorage.getItem("modemon-go:playable:v1:progress:demo"))).toBe(before);
});

if (process.env.EXPECTED_APPLICATION_SHA) test("public deployment serves the expected feature commit and exact production assets", async ({ request }) => {
  expect(process.env.PLAYABLE_BASE_URL).toMatch(/^https:\/\//);
  const response = await request.get("/deployment-provenance.json");
  expect(response.status()).toBe(200);
  const provenance = await response.json();
  expect(provenance.application_commit).toBe(process.env.EXPECTED_APPLICATION_SHA);
  expect(provenance.application_branch).toBe("dev/modedex-learning-links");
  expect(provenance.optimized_creature_count).toBe(51);
  expect(provenance.logo_present).toBe(true);
  const overlay = readFileSync(new URL("../../src/data/learning.json", import.meta.url));
  expect(provenance.learning_overlay_sha256).toBe(createHash("sha256").update(overlay).digest("hex"));
  for (const [path, hash] of Object.entries(provenance.assets)) {
    const asset = await request.get(path);
    expect(asset.status()).toBe(200);
    expect(createHash("sha256").update(await asset.body()).digest("hex")).toBe(hash);
  }
});
