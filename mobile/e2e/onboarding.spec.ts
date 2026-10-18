import { expect, test, type Page } from "@playwright/test";

const errors = new WeakMap<Page, string[]>();
test.beforeEach(({ page }) => {
  const list: string[] = [];
  errors.set(page, list);
  page.on("pageerror", (e) => list.push(e.message));
});
test.afterEach(({ page }) => {
  expect(errors.get(page)).toEqual([]);
});
async function acknowledge(page: Page) {
  await expect(
    page.getByRole("button", { name: "Start Playing", exact: true }),
  ).toBeDisabled();
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Start Playing", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Nearby encounters", exact: true }),
  ).toBeVisible();
}
test("denied location permits safety onboarding, browsable street map, demo and navigation", async ({
  page,
}) => {
  await page.goto("/");
  await acknowledge(page);
  await page
    .getByRole("button", { name: "Allow foreground location", exact: true })
    .click();
  await expect(page.getByText(/Location permission denied/)).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Street map", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Modédex", exact: true }).click();
  await expect(page.getByText(/No discoveries yet/)).toBeVisible();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page
    .getByRole("button", { name: "Read player-safety notice", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "The real world comes first.",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText(/Never play while driving or cycling/),
  ).toBeVisible();
});
test("granted browser location and acknowledgment persist without requiring another safety agreement", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({
    latitude: 35.7796,
    longitude: -78.6382,
    accuracy: 12,
  });
  await page.goto("/");
  await acknowledge(page);
  await page
    .getByRole("button", { name: "Allow foreground location", exact: true })
    .click();
  await expect(page.getByText(/Real GPS · accuracy/)).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Street map", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(() =>
      localStorage.getItem("modemon-go:playable:safety:v1"),
    ),
  ).toBe("1");
  await page.reload();
  await expect(page.getByRole("checkbox")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Heads up/ })).toBeVisible();
});
test("direct encounter links cannot bypass safety acknowledgment", async ({
  page,
}) => {
  await page.goto("/encounter");
  await expect(
    page.getByRole("button", { name: "Start Playing", exact: true }),
  ).toBeDisabled();
  await expect(page.getByRole("checkbox")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Nearby encounters", exact: true }),
  ).toHaveCount(0);
});
test("storage failure warns honestly and requires safety agreement on next launch", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Storage.prototype.getItem = () => {
      throw Error("Unavailable");
    };
    Storage.prototype.setItem = () => {
      throw Error("Unavailable");
    };
  });
  await page.goto("/");
  await acknowledge(page);
  await expect(page.getByRole("alert")).toContainText("Capture is disabled");
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Start Playing", exact: true }),
  ).toBeDisabled();
});
test("onboarding and map remain usable at narrow, landscape and desktop sizes", async ({
  page,
}) => {
  for (const viewport of [
    { width: 320, height: 640 },
    { width: 844, height: 390 },
    { width: 1280, height: 800 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await page
      .getByRole("checkbox")
      .or(page.getByRole("region", { name: "Street map", exact: true }))
      .first()
      .waitFor();
    if (await page.getByRole("checkbox").count()) await acknowledge(page);
    await expect(
      page.getByRole("region", { name: "Street map", exact: true }),
    ).toBeVisible();
    await page
      .getByRole("heading", { name: "Nearby encounters", exact: true })
      .scrollIntoViewIfNeeded();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
});
