import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { answerQuestion, beginAttempt, buildWorld, emptyProgress, questionsFor, startAttempt, type Progress, type Runtime, type Spawn } from "../../src/engine";
import { difficultyQuestionsFor, quizModes, type Difficulty } from "../../src/quizzes";
import { markerLabel } from "../../src/presentation";

const data = JSON.parse(readFileSync(new URL("../../src/data/runtime.json", import.meta.url), "utf8")) as Runtime;
const date = "2026-10-17";
const world = buildWorld(data, date, "demo");
const target = world.find((s) => s.speciesId === "recommender_base" && s.poi.region === "RAL-01")!;
const duplicates = world.filter((s) => s.speciesId === target.speciesId && s.id !== target.id);
function captured(p: Progress, s: Spawn, difficulty?: Difficulty) {
  let next = difficulty ? startAttempt(p, s, data, difficulty) : beginAttempt(p, s);
  const qs = next.attempts[s.id].questions ?? questionsFor(s, data);
  for (const q of qs) next = answerQuestion(next, s, q.correct, qs);
  return next;
}
async function setup(page: Page, progress = emptyProgress(), mode = "demo", real = emptyProgress()) {
  await page.clock.setFixedTime(new Date(`${date}T16:00:00Z`));
  await page.addInitScript(({ progress, real, mode }) => {
    // Seed once: reload must exercise actual persistence, never replace results.
    if (localStorage.getItem("progression-fixture")) return;
    localStorage.setItem("progression-fixture", "1");
    localStorage.setItem("modemon-go:playable:safety:v1", "1");
    localStorage.setItem("modemon-go:playable:mode", mode);
    localStorage.setItem("modemon-go:playable:v1:progress:demo", JSON.stringify(progress));
    localStorage.setItem("modemon-go:playable:v1:progress:real", JSON.stringify(real));
  }, { progress, real, mode });
  await page.goto("/");
}
async function enter(page: Page, s = target) {
  await page.locator(`.encounter-row[data-poi-id="${s.poi.id}"]`).click();
  await page.getByRole("button", { name: "Simulate walking here (Demo)", exact: true }).click();
  await page.getByRole("button", { name: "Enter encounter", exact: true }).click();
  await page.getByRole("button", { name: /^Inspect / }).click();
}
async function complete(page: Page, difficulty: Difficulty, pass = true, s = target) {
  const config = quizModes[difficulty];
  await page.getByRole("radio", { name: `${config.label} ${config.count} questions` }).check();
  await page.getByRole("button", { name: `Capture · ${config.count} questions`, exact: true }).click();
  const qs = difficultyQuestionsFor(s, data, difficulty);
  for (const [i, q] of qs.entries()) {
    await page.getByRole("button", { name: q.options[pass ? q.correct : (q.correct + 1) % 4], exact: true }).click();
    await page.getByRole("button", { name: i === qs.length - 1 ? "Show result" : "Next question", exact: true }).click();
  }
  await page.getByRole("button", { name: "Return to map", exact: true }).click();
}
const row = (page: Page, s = target) => page.locator(`.encounter-row[data-poi-id="${s.poi.id}"]`);
const marker = (page: Page, s = target, collected = false) => page.locator(".encounter-pin").filter({ has: page.locator(collected ? ".pin.collected" : ".pin:not(.collected)") }).and(page.getByRole("button", { name: markerLabel(data, s, collected), exact: true }));

test("new rarity colors, collected shapes and accessible anonymous labels include Signatures", async ({ page }, info) => {
  await setup(page);
  for (const [rarity, color] of [["common", "rgb(20, 125, 101)"], ["rare", "rgb(36, 98, 205)"], ["signature", "rgb(255, 226, 57)"]]) {
    // Use a scheduled Signature date without altering any encounter rules.
    if (rarity === "signature") await page.getByRole("combobox", { name: "Demo rotation (simulated date)" }).selectOption("2026-10-18");
    await expect(page.locator(`.pin.${rarity}:not(.collected)`).first()).toHaveCSS("background-color", color);
  }
  const signature = buildWorld(data, "2026-10-18", "demo").find((s) => s.rarity === "signature")!;
  expect(signature).toBeTruthy();
  // A real completed Signature record from its scheduled rotation; another day
  // of the same species remains eligible and becomes gray.
  const p = captured(emptyProgress(), signature, "expert");
  await page.evaluate((p) => {
    localStorage.setItem("modemon-go:playable:v1:progress:demo", JSON.stringify(p));
  }, p);
  await page.reload();
  for (let i = 1; i <= 15; i++) {
    const d = new Date(Date.parse(date + "T12:00:00Z") + i * 86400000).toISOString().slice(0, 10);
    if (d === signature.date) continue;
    const s = buildWorld(data, d, "demo").find((s) => s.speciesId === signature.speciesId);
    if (!s) continue;
    await page.getByRole("combobox", { name: "Demo rotation (simulated date)" }).selectOption(d);
    await page.getByRole("combobox", { name: "Browse city" }).selectOption(s.poi.region.startsWith("DUR") ? "Durham" : "Raleigh");
    await expect(marker(page, s, true).locator(".pin")).toHaveCSS("background-color", "rgb(100, 116, 139)");
    await expect(marker(page, s, true).locator(".pin")).toHaveCSS("border-style", "double");
    await expect(row(page, s)).toContainText("Previously collected species");
    await page.screenshot({ path: info.outputPath("collected-signature.png"), fullPage: true });
    return;
  }
  throw Error("Deterministic preview fixture needs a second scheduled encounter of the Signature");
});

for (const difficulty of ["novice", "intermediate", "expert"] as const) {
  test(`${difficulty} capture updates map/list and independent mastery after reload`, async ({ page }, info) => {
    await setup(page);
    await expect(row(page)).not.toHaveClass(/collected/);
    await enter(page);
    await expect(page.getByRole("dialog").getByRole("heading", { name: "AI in the Wild" })).toHaveCount(0);
    await complete(page, difficulty);
    const other = duplicates.find((s) => s.poi.region === "RAL-01")!;
    await expect(row(page, other)).toContainText("Previously collected species");
    await expect(marker(page, other, true).locator(".pin")).toHaveCSS("background-color", "rgb(100, 116, 139)");
    await expect(marker(page, other, true)).not.toHaveAttribute("aria-label", new RegExp(data.modedex.modemon[target.speciesId].name));
    if (difficulty === "novice") {
      await page.screenshot({ path: info.outputPath("collected-and-new-map.png"), fullPage: true });
      await page.locator(".map-frame").screenshot({ path: info.outputPath("map-marker-comparison.png") });
    }
    await page.reload();
    await expect(row(page)).toHaveCount(0);
    await expect(row(page, other)).toContainText("Previously collected species");
    await page.getByRole("button", { name: "Modédex", exact: true }).click();
    const dex = page.locator(".dex-row");
    await expect(dex.locator(".mastery-badge.earned")).toHaveCount(1);
    await expect(dex.locator(".mastery-badge.locked")).toHaveCount(2);
    await expect(dex.locator(`.mastery-badge.${difficulty}`)).toHaveClass(/earned/);
    await dex.click();
    await expect(page.locator(".dex-entry .mastery-badge.earned")).toHaveCount(1);
    const card = page.locator(".trading-card");
    for (const heading of ["Ability / Job", "How It Works", "Weaknesses / Limitations", "Explainability", "AI in the Wild", "Further Learning"])
      await expect(card.getByRole("heading", { name: heading, exact: true })).toHaveCount(1);
    await expect(card.locator(".everyday-example")).toHaveCount(2);
    await expect(card).toContainText(data.modedex.modemon[target.speciesId].input_data);
    await expect(card).toContainText(data.modedex.modemon[target.speciesId].biases_limitations[0]);
    if (difficulty === "expert") {
      await page.screenshot({ path: info.outputPath("trading-card-and-mastery.png"), fullPage: true });
    }
    await page.getByRole("button", { name: "Exit Demo Mode", exact: true }).click();
    await expect(row(page, other)).not.toHaveClass(/collected/);
    await expect(marker(page, other).locator(".pin")).toHaveCSS("background-color", "rgb(20, 125, 101)");
    await page.getByRole("button", { name: "Badges", exact: true }).click();
    await expect(page.getByRole("article", { name: "Model Master", exact: true })).toContainText("0 of 51");
  });
}

test("legacy history, mastery accumulation, Hoarder transition and one nonblocking celebration", async ({ page }, info) => {
  let p = emptyProgress();
  for (const [i, s] of duplicates.slice(0, 4).entries()) p = captured(p, s, i === 1 ? "intermediate" : undefined);
  await setup(page, p);
  await expect(page.locator(".achievement-notice")).toHaveCount(0);
  await page.getByRole("button", { name: "Badges", exact: true }).click();
  await expect(page.getByRole("article", { name: "Hoarder", exact: true })).toContainText("4 of 5");
  await expect(page.getByRole("article", { name: "Model Master", exact: true })).not.toContainText("no eligible public encounter locations");
  await expect(page.locator(".coverage-note")).toHaveCount(0);
  await page.getByRole("button", { name: "Map", exact: true }).click();
  await enter(page);
  await complete(page, "expert");
  const notice = page.locator(".achievement-notice");
  await expect(notice).toContainText("Achievement Unlocked!");
  await expect(notice).toContainText("Hoarder");
  await expect(notice).toHaveCount(1);
  await page.screenshot({ path: info.outputPath("achievement-unlock.png"), fullPage: true });
  await page.getByRole("button", { name: "Dismiss achievement notification" }).click();
  await page.getByRole("button", { name: "Modédex", exact: true }).click();
  await expect(page.locator(".dex-row .mastery-badge.earned")).toHaveCount(3);
  await page.screenshot({ path: info.outputPath("species-mastery.png"), fullPage: true });
  await page.getByRole("button", { name: "Badges", exact: true }).click();
  await expect(page.getByRole("article", { name: "Hoarder", exact: true })).toContainText("Earned · Complete");
  await expect(page.getByRole("article", { name: "Hoarder", exact: true })).toContainText("5 of 5");
  await expect(page.getByRole("article", { name: "Master Scholar", exact: true })).toContainText("1 of 51");
  await page.setViewportSize({ width: 960, height: 800 });
  await page.screenshot({ path: info.outputPath("trainer-gallery.png"), fullPage: true });
  await page.setViewportSize({ width: 393, height: 852 });
  await page.reload();
  await expect(notice).toHaveCount(0);
  await page.getByRole("button", { name: "Badges", exact: true }).click();
  await expect(page.getByRole("article", { name: "Hoarder", exact: true })).toContainText("Earned · Complete");
});

test("failed and unfinished captures stay uncollected; real captures do not color Demo", async ({ page }) => {
  const real = captured(emptyProgress(), duplicates[0]);
  await setup(page, emptyProgress(), "demo", real);
  await expect(row(page)).not.toHaveClass(/collected/);
  await enter(page);
  await page.getByRole("button", { name: "Close encounter", exact: true }).click();
  await expect(row(page)).not.toHaveClass(/collected/);
  await enter(page);
  await complete(page, "expert", false);
  await expect(row(page, duplicates.find((s) => s.poi.region === "RAL-01")!)).not.toHaveClass(/collected/);
  await page.getByRole("button", { name: "Modédex", exact: true }).click();
  await expect(page.locator(".mastery-badges")).toHaveCount(0);
  await page.getByRole("button", { name: "Exit Demo Mode", exact: true }).click();
  await expect(row(page)).toContainText("Previously collected species");
});

test("one capture combines simultaneous collection and family awards without replaying history", async ({ page }) => {
  const past = Array.from({ length: 32 }, (_, i) =>
    new Date(Date.parse(date + "T12:00:00Z") - (i + 1) * 86400000).toISOString().slice(0, 10));
  const pool = past.flatMap((d) => buildWorld(data, d, "demo"));
  let p = emptyProgress();
  for (const [id, s] of Object.entries(data.modedex.modemon)) {
    if (id === target.speciesId || (s.rarity !== "common" && s.family_id !== "recommender")) continue;
    const previous = pool.find((encounter) => encounter.speciesId === id);
    expect(previous, `${id} has a deterministic eligible prior encounter`).toBeTruthy();
    p = captured(p, previous!);
  }
  await setup(page, p);
  await expect(page.locator(".achievement-notice")).toHaveCount(0);
  await enter(page);
  await complete(page, "novice");
  const notice = page.locator(".achievement-notice");
  await expect(notice).toHaveCount(1);
  await expect(notice).toContainText("Common Collector");
  await expect(notice).toContainText("Recommender Family Expert");
  await expect(notice).not.toContainText("Connoisseur");
  await page.reload();
  await expect(notice).toHaveCount(0);
});

test("portrait, landscape, both cities and keyboard-accessible badge information", async ({ page }) => {
  await setup(page, captured(emptyProgress(), duplicates[0]));
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const [width, height] of [[320, 568], [844, 390]]) {
    await page.setViewportSize({ width, height });
    for (const city of ["Durham", "Raleigh"]) {
      await page.getByRole("combobox", { name: "Browse city" }).selectOption(city);
      await expect(page.locator(".encounter-row").first()).toBeVisible();
    }
    const badges = page.getByRole("button", { name: "Badges", exact: true });
    await badges.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: "Trainer Badges", exact: true })).toBeVisible();
    await expect(page.getByRole("progressbar")).toHaveCount(15);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.getByRole("button", { name: "Modédex", exact: true }).click();
    const dex = page.locator(".dex-row");
    await expect(dex.getByRole("img", { name: /Beginner Badge: earned/ })).toBeVisible();
    await expect(dex.getByRole("img", { name: /Expert Badge: locked.*passing an Expert quiz/ })).toBeVisible();
    await dex.focus();
    await page.keyboard.press("Enter");
    await page.getByRole("heading", { name: "AI in the Wild", exact: true }).scrollIntoViewIfNeeded();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.getByRole("button", { name: "Back to discoveries", exact: true }).click();
    await page.getByRole("button", { name: "Map", exact: true }).click();
    await enter(page);
    const capture = page.getByRole("button", { name: "Capture · 3 questions", exact: true });
    await capture.scrollIntoViewIfNeeded();
    await capture.focus();
    await expect(capture).toBeFocused();
    expect(await page.getByRole("dialog").evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(true);
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(row(page)).toBeFocused();
  }
});
