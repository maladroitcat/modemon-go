import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import type { Runtime } from "../../src/engine";
import { approximateDistance } from "../../src/presentation";
import { signatureProject } from "../../src/signatures";

const data = JSON.parse(
  readFileSync(new URL("../../src/data/runtime.json", import.meta.url), "utf8"),
) as Runtime;
const signatures = Object.entries(data.modedex.modemon).filter(
  ([, s]) => s.stage === 3,
);

test("all twelve standalone Signature details identify documented inspiration and link accessibly without creating captures", async ({
  page,
}, info) => {
  // Discovered entries are seeded for rendering QA only; no capture is created.
  // Production encounters now use the separately approved issue-21 crosswalk.
  await page.addInitScript(
    (ids) => {
      localStorage.setItem(
        "modemon-go:playable:v1:progress:demo",
        JSON.stringify({ version: 1, discovered: ids, attempts: {} }),
      );
      localStorage.setItem("modemon-go:playable:mode", "demo");
    },
    signatures.map(([id]) => id),
  );
  await page.goto("/");
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Start Playing", exact: true })
    .click();
  await page.getByRole("button", { name: "Modédex", exact: true }).click();
  for (const [id, species] of signatures) {
    await page
      .getByRole("button", { name: new RegExp(`^${species.name} `) })
      .click();
    const project = signatureProject(species)!;
    const intro = page.locator(".signature-inspiration");
    await expect(intro).toContainText(project.source!.anchor_name);
    await expect(intro).toContainText(project.source!.verified_use);
    await expect(intro).toContainText(project.source!.source_title);
    const link = page.getByRole("link", {
      name: `Learn about the real project for ${species.name} (opens in a new tab)`,
    });
    await expect(link).toContainText("Learn about the real project");
    await expect(link).toHaveAttribute("href", project.href!);
    await expect(link).toHaveAttribute("rel", "noopener noreferrer");
    await expect(link).toHaveAttribute("target", "_blank");
    await expect(page.locator(".signature-project")).toContainText(
      "not a claim that this system runs at your location",
    );
    await expect(page.getByRole("button", { name: /^Capture/ })).toHaveCount(0);
    for (const [width, height] of [
      [320, 568],
      [393, 852],
      [844, 390],
    ]) {
      await page.setViewportSize({ width, height });
      await link.scrollIntoViewIfNeeded();
      await expect(link).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      expect(
        await intro.evaluate((el) => el.scrollWidth <= el.clientWidth),
      ).toBe(true);
      if (id === "recommender_ai_curator" || id === "extractor_history")
        await page.screenshot({
          path: info.outputPath(`${id}-${width}x${height}.png`),
        });
    }
    if (id === "recommender_ai_curator") {
      // Verify actual link navigation without repeatedly fetching third-party sites
      // or treating their content/network availability as an application test.
      await page.context().route(project.href!, (route) =>
        route.fulfill({
          contentType: "text/html",
          body: "<title>Project navigation QA</title>",
        }),
      );
      const popupPromise = page.waitForEvent("popup");
      await link.click();
      const popup = await popupPromise;
      await expect(popup).toHaveURL(project.href!);
      await popup.close();
    }
    await page
      .getByRole("button", { name: "Back to discoveries", exact: true })
      .click();
  }
  await page.getByRole("button", { name: "Map", exact: true }).click();
  await expect(page.locator("header")).toContainText("0 captured");
  for (const row of await page.locator(".encounter-row").all()) {
    const poiId = await row.getAttribute("data-poi-id");
    if ((await row.innerText()).includes("Signature"))
      expect(data.signatures!.entries.some((e) => e.poi_id === poiId)).toBe(true);
    for (const [, species] of signatures) await expect(row).not.toContainText(species.name);
  }
});

test("real GPS accuracy, nearby distances, Demo distances and map instructions use US display units", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({
    latitude: 35.7796,
    longitude: -78.6382,
    accuracy: 25,
  });
  await page.goto("/");
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Start Playing", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Allow foreground location", exact: true })
    .click();
  await expect(
    page.getByText(`Real GPS · accuracy ${approximateDistance(25)}`, {
      exact: true,
    }),
  ).toBeVisible();
  const first = page.locator(".encounter-row").first();
  await expect(first).toContainText(/\b(ft|mi)\b/);
  await expect(page.locator(".nearby")).not.toContainText(
    /\b\d+(?:\.\d+)?\s*(?:m|km|meters|kilometers)\b/,
  );
  await first.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("about 82 ft");
  await expect(dialog).not.toContainText(
    /\b\d+(?:\.\d+)?\s*(?:m|km|meters|kilometers)\b/,
  );
  await page
    .getByRole("button", { name: "Close encounter", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Try Demo Mode", exact: true })
    .click();
  await first.click();
  await page
    .getByRole("button", { name: "Simulate walking here (Demo)", exact: true })
    .click();
  await expect(dialog).toContainText("not your GPS");
  await expect(page.locator(".encounter-row").first()).toContainText(
    "0 ft simulated",
  );
});
