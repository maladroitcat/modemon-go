import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { buildWorld, questionsFor, type Runtime } from "../../src/engine";
import { markerLabel, placeLabel } from "../../src/presentation";
const legacy = JSON.parse(
  readFileSync(
    new URL("../fixtures/mvp-gameplay.json", import.meta.url),
    "utf8",
  ),
) as {
  saved_progress: import("../../src/engine").Progress;
  saved_encounters: {
    id: string;
    poi_id: string;
    name: string;
    speciesId: string;
  }[];
};
const data = JSON.parse(
  readFileSync(new URL("../../src/data/runtime.json", import.meta.url), "utf8"),
) as Runtime;
test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(new Date("2026-10-17T16:00:00Z"));
});
async function onboard(page: Page) {
  await page.goto("/");
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Start Playing", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Nearby encounters", exact: true }),
  ).toBeVisible();
}
async function demo(page: Page) {
  await onboard(page);
  await page
    .getByRole("button", { name: "Try Demo Mode", exact: true })
    .click();
}
async function openFirst(page: Page) {
  const button = page.locator(".encounter-row").first();
  const text = await button.innerText();
  await button.click();
  const spawn = buildWorld(data, "2026-10-17").find(
    (s) => text.includes(s.poi.name) && s.poi.region.startsWith("RAL"),
  )!;
  expect(spawn).toBeTruthy();
  return spawn;
}
async function begin(page: Page) {
  const s = await openFirst(page);
  await expect(
    page.getByRole("button", { name: "Enter encounter", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Simulate walking here (Demo)", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Enter encounter", exact: true })
    .click();
  return s;
}
async function quiz(page: Page) {
  await page.getByRole("button", { name: /^Inspect / }).click();
  await page
    .getByRole("button", { name: "Capture · 3 questions", exact: true })
    .click();
}
test("demo full capture survives reload; real collection stays separate", async ({
  page,
}, info) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: async () => {
          throw new DOMException("Denied", "NotAllowedError");
        },
      },
    });
  });
  await demo(page);
  const s = await begin(page);
  await page
    .getByRole("button", { name: "Enable camera", exact: true })
    .click();
  await expect(page.getByText(/Camera unavailable or denied/)).toBeVisible();
  await page
    .getByRole("button", { name: "Use without camera", exact: true })
    .click();
  await expect(
    page.getByLabel(
      `Artwork unavailable for ${data.modedex.modemon[s.speciesId].name}`,
    ),
  ).toBeVisible();
  await quiz(page);
  for (const [i, q] of questionsFor(s, data).entries()) {
    await expect(
      page.getByText(`Question ${i + 1} of 3 · at least 2 correct to capture`, {
        exact: true,
      }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: q.options[q.correct], exact: true })
      .click();
    await expect(page.locator(".feedback")).toHaveClass(/feedback--correct/);
    await expect(page.locator(".feedback")).toHaveCSS(
      "background-color",
      "rgb(234, 244, 237)",
    );
    await expect(page.locator(".feedback")).toHaveCSS(
      "border-left-color",
      "rgb(20, 125, 101)",
    );
    await expect(page.locator(".feedback .lucide-circle-check")).toBeVisible();
    if (i === 0)
      await page.screenshot({
        path: info.outputPath("feedback-correct.png"),
        fullPage: true,
      });
    await page
      .getByRole("button", {
        name: i === 2 ? "Show result" : "Next question",
        exact: true,
      })
      .click();
  }
  await expect(
    page.getByRole("heading", { name: "Captured!", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: info.outputPath("capture.png"),
    fullPage: true,
  });
  await page.reload();
  await expect(page.getByText("1 captured", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Modédex", exact: true }).click();
  await expect(page.getByText(/1 discovered of 51/)).toBeVisible();
  await page
    .getByRole("button", { name: "Exit Demo Mode", exact: true })
    .click();
  await expect(page.getByText("0 captured", { exact: true })).toBeVisible();
});
test("quiz progress cannot be reset by closing or reload; failed encounter remains escaped", async ({
  page,
}, info) => {
  await demo(page);
  const s = await begin(page);
  await quiz(page);
  const qs = questionsFor(s, data);
  await page
    .getByRole("button", {
      name: qs[0].options[(qs[0].correct + 1) % 4],
      exact: true,
    })
    .click();
  await expect(page.getByText(/Not quite. Correct answer:/)).toBeVisible();
  await expect(page.locator(".feedback")).toHaveClass(/feedback--incorrect/);
  await expect(page.locator(".feedback")).toHaveCSS(
    "background-color",
    "rgb(255, 240, 239)",
  );
  await expect(page.locator(".feedback")).toHaveCSS(
    "border-left-color",
    "rgb(172, 47, 47)",
  );
  await expect(page.locator(".feedback .lucide-circle-x")).toBeVisible();
  await page.screenshot({
    path: info.outputPath("feedback-incorrect.png"),
    fullPage: true,
  });
  await page.reload();
  await page
    .locator(".encounter-row")
    .filter({ hasText: s.poi.name })
    .first()
    .click();
  await page
    .getByRole("button", { name: "Simulate walking here (Demo)", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Enter encounter", exact: true })
    .click();
  await quiz(page);
  await page
    .getByRole("button", { name: "Next question", exact: true })
    .click();
  for (let i = 1; i < 3; i++) {
    await expect(
      page.getByText(`Question ${i + 1} of 3 · at least 2 correct to capture`, {
        exact: true,
      }),
    ).toBeVisible();
    await page
      .getByRole("button", {
        name: qs[i].options[(qs[i].correct + 1) % 4],
        exact: true,
      })
      .click();
    await page
      .getByRole("button", {
        name: i === 2 ? "Show result" : "Next question",
        exact: true,
      })
      .click();
  }
  await expect(
    page.getByRole("heading", { name: "It escaped.", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.locator(".encounter-row").filter({ hasText: s.poi.name }),
  ).toHaveCount(0);
});
test("real GPS far away cannot enter; demo requires explicit opt-in", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({ latitude: 40.7, longitude: -74, accuracy: 5 });
  await onboard(page);
  await page
    .getByRole("button", { name: "Allow foreground location", exact: true })
    .click();
  await expect(page.getByText(/Real GPS · accuracy/)).toBeVisible();
  await openFirst(page);
  await expect(
    page.getByRole("button", { name: "Enter encounter", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", {
      name: "Simulate walking here (Demo)",
      exact: true,
    }),
  ).toHaveCount(0);
});
test("storage denial is explicit and cannot claim persistent capture", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Storage.prototype.setItem = () => {
      throw Error("Storage disabled");
    };
  });
  await demo(page);
  await openFirst(page);
  await page
    .getByRole("button", { name: "Simulate walking here (Demo)", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Enter encounter", exact: true }),
  ).toBeDisabled();
  await expect(page.getByRole("alert")).toContainText("Capture is disabled");
});
test("both city demos and responsive street map remain usable", async ({
  page,
}, info) => {
  await demo(page);
  await page
    .getByRole("combobox", { name: "Browse city" })
    .selectOption("Durham");
  await expect(page.locator(".encounter-row").first()).toContainText(
    /in (Downtown Durham|Duke University)/,
  );
  await expect(page.locator(".nearby")).not.toContainText(/\b(?:DUR|RAL)-\d/);
  for (const size of [
    { width: 320, height: 640 },
    { width: 844, height: 390 },
    { width: 1280, height: 800 },
  ]) {
    await page.setViewportSize(size);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
  await page.setViewportSize({ width: 393, height: 852 });
  await page.screenshot({
    path: info.outputPath("durham-map.png"),
    fullPage: true,
  });
});
test("camera is user-gesture only, stops on background and on leaving overlay", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const state = { requests: 0, stops: 0 };
    Object.assign(window, { cameraQA: state });
    Object.defineProperty(HTMLMediaElement.prototype, "play", {
      configurable: true,
      value: async () => {},
    });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: async () => {
          state.requests++;
          const stream = new MediaStream();
          Object.defineProperty(stream, "getTracks", {
            value: () => [
              {
                stop: () => {
                  state.stops++;
                },
              } as MediaStreamTrack,
            ],
          });
          return stream;
        },
      },
    });
  });
  await demo(page);
  await begin(page);
  expect(
    await page.evaluate(
      () =>
        (window as unknown as { cameraQA: { requests: number } }).cameraQA
          .requests,
    ),
  ).toBe(0);
  await page
    .getByRole("button", { name: "Enable camera", exact: true })
    .click();
  await expect(
    page.getByText("Camera active. No video is recorded or uploaded.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.evaluate(() => window.dispatchEvent(new Event("pagehide")));
  expect(
    await page.evaluate(
      () =>
        (window as unknown as { cameraQA: { stops: number } }).cameraQA.stops,
    ),
  ).toBe(1);
  await page
    .getByRole("button", { name: "Enable camera", exact: true })
    .click();
  await page.getByRole("button", { name: /^Inspect / }).click();
  expect(
    await page.evaluate(
      () =>
        (window as unknown as { cameraQA: { stops: number } }).cameraQA.stops,
    ),
  ).toBe(2);
});
test("foreground GPS stops when hidden and no GPS history enters browser storage", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const state = { started: 0, stopped: 0 };
    Object.assign(window, { gpsQA: state });
    navigator.geolocation.watchPosition = (success) => {
      state.started++;
      success({
        coords: { latitude: 35.7796, longitude: -78.6382, accuracy: 10 },
        timestamp: Date.now(),
      } as GeolocationPosition);
      return 99;
    };
    navigator.geolocation.clearWatch = () => {
      state.stopped++;
    };
  });
  await onboard(page);
  await page
    .getByRole("button", { name: "Allow foreground location", exact: true })
    .click();
  await expect(page.getByText(/Real GPS · accuracy/)).toBeVisible();
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", {
      value: true,
      configurable: true,
    });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  expect(
    await page.evaluate(
      () => (window as unknown as { gpsQA: { stopped: number } }).gpsQA.stopped,
    ),
  ).toBeGreaterThan(0);
  const storage = await page.evaluate(() =>
    JSON.stringify({ ...localStorage }),
  );
  expect(storage).not.toContain("35.7796");
  expect(storage).not.toContain("-78.6382");
});

test("tap dialogs and marker tooltips use friendly place, distance and safety wording", async ({
  page,
  context,
}, info) => {
  const s = buildWorld(data, "2026-10-17").find(
    (s) => s.poi.region === "RAL-01",
  )!;
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({
    latitude: s.poi.lat + 381 / 111195,
    longitude: s.poi.lon,
    accuracy: 12,
  });
  // Native geolocation timestamps use wall time; align this fixture with the
  // frozen daily-rotation clock while retaining the browser's location API.
  await page.addInitScript(() => {
    const native = navigator.geolocation;
    Object.defineProperty(navigator, 'geolocation', { configurable: true, value: {
      watchPosition: (success: PositionCallback, error?: PositionErrorCallback, options?: PositionOptions) =>
        native.watchPosition(p => success({coords:p.coords,timestamp:Date.now()} as GeolocationPosition), error, options),
      clearWatch: native.clearWatch.bind(native),
    }});
  });
  await onboard(page);
  await page
    .getByRole("button", { name: "Allow foreground location", exact: true })
    .click();
  await expect(page.getByText(/Real GPS · accuracy/)).toBeVisible();
  await expect(
    page.getByTitle(markerLabel(data, s), { exact: true }),
  ).toHaveAttribute("aria-label", markerLabel(data, s));
  const titles = await page
    .locator(".encounter-pin")
    .evaluateAll((nodes) => nodes.map((n) => n.getAttribute("title")));
  expect(titles.every((t) => t && !/\b(?:RAL|DUR)-\d/.test(t))).toBe(true);
  await page.locator(`[data-poi-id="${s.poi.id}"]`).click();
  const modal = page.getByRole("dialog");
  await expect(
    modal.getByText(placeLabel(data, s.poi), { exact: true }),
  ).toBeVisible();
  await expect(modal).toContainText(
    "You're about 1,250 ft away. Get within roughly 250 ft",
  );
  await expect(modal).toContainText(
    "Stay in public areas; you don't need to enter the business.",
  );
  await expect(modal).not.toContainText(
    /Association only|GPS tolerance|\b(?:RAL|DUR)-\d/,
  );
  await page.screenshot({
    path: info.outputPath("friendly-location.png"),
    fullPage: true,
  });
});

test("long Modédex panels scroll and Capture stays reachable on small mobile screens", async ({
  page,
}, info) => {
  const s = buildWorld(data, "2026-10-17")
    .filter((s) => s.poi.region.startsWith("RAL"))
    .sort(
      (a, b) =>
        data.modedex.modemon[b.speciesId].dex_entry.length -
        data.modedex.modemon[a.speciesId].dex_entry.length,
    )[0];
  await demo(page);
  for (const [index, viewport] of [
    { width: 320, height: 568 },
    { width: 393, height: 852 },
    { width: 844, height: 390 },
  ].entries()) {
    await page.setViewportSize(viewport);
    await page.locator(`[data-poi-id="${s.poi.id}"]`).click();
    await expect(page.getByText(index===0
      ? /Tap Simulate walking here to try this encounter without traveling/
      : /Your simulated location is close enough/)).toBeVisible();
    await page
      .getByRole("button", {
        name: "Simulate walking here (Demo)",
        exact: true,
      })
      .click();
    await expect(
      page.getByText(/Your simulated location is close enough/),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Enter encounter", exact: true })
      .click();
    await page.getByRole("button", { name: /^Inspect / }).click();
    const modal = page.getByRole("dialog"),
      capture = page.getByRole("button", {
        name: "Capture · 3 questions",
        exact: true,
      });
    expect(
      await modal.evaluate((el) => el.scrollHeight > el.clientHeight),
    ).toBe(true);
    await capture.scrollIntoViewIfNeeded();
    await expect(capture).toBeVisible();
    const box = await capture.boundingBox(),
      parent = await modal.boundingBox();
    expect(box!.y + box!.height).toBeLessThanOrEqual(
      parent!.y + parent!.height,
    );
    expect(
      await modal.evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
    ).toBe(true);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: info.outputPath(`intro-${viewport.width}x${viewport.height}.png`),
      fullPage: true,
    });
    await capture.click();
    await expect(
      page.getByText("Question 1 of 3 · at least 2 correct to capture", {
        exact: true,
      }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Close encounter", exact: true })
      .click();
  }
});

test("pre-update captures, escape state and unfinished quiz survive the copy update", async ({
  page,
}) => {
  await page.addInitScript((progress) => {
    localStorage.setItem("modemon-go:playable:safety:v1", "1");
    localStorage.setItem("modemon-go:playable:mode", "demo");
    localStorage.setItem(
      "modemon-go:playable:v1:progress:demo",
      JSON.stringify(progress),
    );
  }, legacy.saved_progress);
  await page.goto("/");
  await expect(page.getByText("1 captured", { exact: true })).toBeVisible();
  for (const saved of legacy.saved_encounters.slice(0, 2))
    await expect(page.locator(`[data-poi-id="${saved.poi_id}"]`)).toHaveCount(
      0,
    );
  const ongoing = legacy.saved_encounters[2];
  await page.locator(`[data-poi-id="${ongoing.poi_id}"]`).click();
  await page
    .getByRole("button", { name: "Simulate walking here (Demo)", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Enter encounter", exact: true })
    .click();
  await quiz(page);
  await expect(page.locator(".feedback")).toHaveClass(/feedback--correct/);
  await page
    .getByRole("button", { name: "Next question", exact: true })
    .click();
  await expect(
    page.getByText("Question 2 of 3 · at least 2 correct to capture", {
      exact: true,
    }),
  ).toBeVisible();
  expect(
    await page.evaluate(() =>
      JSON.parse(localStorage.getItem("modemon-go:playable:v1:progress:demo")!),
    ),
  ).toEqual(legacy.saved_progress);
});
