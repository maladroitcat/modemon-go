import { expect, test, type Page } from "@playwright/test";
import { cameraPreferenceKey } from "../../src/camera";

async function setup(page: Page, options: { remembered?: string; deferred?: boolean; denied?: boolean } = {}) {
  await page.clock.setFixedTime(new Date("2026-10-17T16:00:00Z"));
  await page.addInitScript(({ key, options }) => {
    localStorage.setItem("modemon-go:playable:safety:v1", "1");
    localStorage.setItem("modemon-go:playable:mode", "demo");
    if (options.remembered && !localStorage.getItem(key)) localStorage.setItem(key, options.remembered);
    const state = { requests: 0, stops: 0, denied: !!options.denied, deferred: !!options.deferred,
      release: (() => {}) as () => void };
    Object.assign(window, { cameraPreferenceQA: state });
    Object.defineProperty(HTMLMediaElement.prototype, "play", { configurable: true, value: async () => {} });
    Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: {
      getUserMedia: async (constraints: MediaStreamConstraints) => {
        if (constraints.audio !== false) throw Error("Audio must never be requested");
        state.requests++;
        if (state.denied) throw new DOMException("Denied", "NotAllowedError");
        if (state.deferred) await new Promise<void>((resolve) => { state.release = resolve; });
        const stream = new MediaStream();
        Object.defineProperty(stream, "getTracks", { value: () => [{ stop: () => { state.stops++; } }] });
        return stream;
      },
    } });
  }, { key: cameraPreferenceKey, options });
  await page.goto("/");
}
async function stats(page: Page) {
  return page.evaluate(() => {
    const qa = (window as unknown as { cameraPreferenceQA: { requests: number; stops: number } }).cameraPreferenceQA;
    return { requests: qa.requests, stops: qa.stops };
  });
}
async function open(page: Page) {
  await page.locator(".encounter-row").first().click();
  await page.getByRole("button", { name: "Simulate walking here (Demo)", exact: true }).click();
  await page.getByRole("button", { name: "Enter encounter", exact: true }).click();
}
const close = (page: Page) => page.getByRole("button", { name: "Close encounter", exact: true }).click();
const active = (page: Page) => expect(page.getByText("Camera active. No video is recorded or uploaded.", { exact: true })).toBeVisible();

test("first opt-in, next encounter automatic camera, persistent off, re-enable and reload", async ({ page }) => {
  await setup(page);
  expect((await stats(page)).requests).toBe(0);
  await open(page);
  const initialProgress = await page.evaluate(() => JSON.parse(localStorage.getItem("modemon-go:playable:v1:progress:demo")!));
  expect((await stats(page)).requests).toBe(0);
  await page.getByRole("button", { name: "Enable camera", exact: true }).click(); await active(page);
  expect(await page.evaluate((key) => localStorage.getItem(key), cameraPreferenceKey)).toBe("enabled");
  await close(page); expect((await stats(page)).stops).toBe(1);
  expect((await stats(page)).requests).toBe(1);
  await open(page); await active(page); expect((await stats(page)).requests).toBe(2);
  await page.getByRole("button", { name: "Use without camera", exact: true }).click();
  expect((await stats(page)).stops).toBe(2);
  expect(await page.evaluate((key) => localStorage.getItem(key), cameraPreferenceKey)).toBe("disabled");
  await close(page); await open(page); expect((await stats(page)).requests).toBe(2);
  await page.reload(); expect((await stats(page)).requests).toBe(0);
  await open(page); expect((await stats(page)).requests).toBe(0);
  await page.getByRole("button", { name: "Enable camera", exact: true }).click(); await active(page);
  await page.reload(); expect((await stats(page)).requests).toBe(0);
  await open(page); await active(page); expect((await stats(page)).requests).toBe(1);
  await page.getByRole("button", { name: /^Inspect / }).click();
  expect((await stats(page)).stops).toBe(1);
  // Camera preference does not create captures or alter real/demo progress.
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem("modemon-go:playable:v1:progress:demo")!))).toEqual(initialProgress);
});

test("remembered opt-in is encounter-only; rejection falls back once and allows explicit retry", async ({ page }) => {
  await setup(page, { remembered: "enabled", denied: true });
  expect((await stats(page)).requests).toBe(0);
  await open(page);
  await expect(page.getByText(/Camera unavailable or denied/)).toBeVisible();
  expect((await stats(page)).requests).toBe(1);
  await close(page); await open(page); expect((await stats(page)).requests).toBe(1);
  await page.evaluate(() => { (window as unknown as { cameraPreferenceQA: { denied: boolean } }).cameraPreferenceQA.denied = false; });
  await page.getByRole("button", { name: "Enable camera", exact: true }).click(); await active(page);
  await page.getByRole("button", { name: "Use without camera", exact: true }).click();
  await page.getByRole("button", { name: /^Inspect / }).click();
  await expect(page.getByRole("button", { name: "Capture · 3 questions", exact: true })).toBeVisible();
});

test("off during permission prompt wins; no overlap or late preference enable", async ({ page }) => {
  await setup(page, { deferred: true }); await open(page);
  await page.getByRole("button", { name: "Enable camera", exact: true }).click();
  await expect(page.getByRole("button", { name: "Enable camera", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Use without camera", exact: true }).click();
  await page.evaluate(() => { (window as unknown as { cameraPreferenceQA: { release: () => void } }).cameraPreferenceQA.release(); });
  await expect.poll(async () => (await stats(page)).stops).toBe(1);
  expect(await page.evaluate((key) => localStorage.getItem(key), cameraPreferenceKey)).toBe("disabled");
  await close(page); await open(page); expect((await stats(page)).requests).toBe(1);
});

test("pagehide and hidden visibility stop remembered cameras without foreground retries", async ({ page }) => {
  await setup(page, { remembered: "enabled" }); await open(page); await active(page);
  await page.evaluate(() => window.dispatchEvent(new Event("pagehide")));
  expect((await stats(page)).stops).toBe(1);
  await page.getByRole("button", { name: "Enable camera", exact: true }).click(); await active(page);
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", { configurable: true, value: true });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  expect((await stats(page)).stops).toBe(2);
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", { configurable: true, value: false });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  expect((await stats(page)).requests).toBe(2);
  await close(page); await open(page); await active(page);
  expect((await stats(page)).requests).toBe(3);
});
