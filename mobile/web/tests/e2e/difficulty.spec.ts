import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { buildWorld, type Runtime } from "../../src/engine";
import {
  difficultyQuestionsFor,
  quizModes,
  type Difficulty,
} from "../../src/quizzes";

const data = JSON.parse(
  readFileSync(new URL("../../src/data/runtime.json", import.meta.url), "utf8"),
) as Runtime;
const date = "2026-10-17";
test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(new Date(`${date}T16:00:00Z`));
});
async function setup(page: Page) {
  await page.goto("/");
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Start Playing", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Try Demo Mode", exact: true })
    .click();
  const row = page.locator(".encounter-row").first();
  const id = await row.getAttribute("data-poi-id");
  const spawn = buildWorld(data, date).find((s) => s.poi.id === id)!;
  await row.click();
  await page
    .getByRole("button", { name: "Simulate walking here (Demo)", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Enter encounter", exact: true })
    .click();
  await page.getByRole("button", { name: /^Inspect / }).click();
  return spawn;
}
async function reopen(page: Page, poiId: string) {
  await page.locator(`.encounter-row[data-poi-id="${poiId}"]`).click();
  await page
    .getByRole("button", { name: "Simulate walking here (Demo)", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Enter encounter", exact: true })
    .click();
  await page.getByRole("button", { name: /^Inspect / }).click();
}
for (const difficulty of Object.keys(quizModes) as Difficulty[]) {
  for (const passes of [true, false]) {
    const config = quizModes[difficulty];
    test(`${config.label}: ${passes ? "passes" : "escapes"} at majority boundary, saves all answers and survives reload`, async ({
      page,
    }, info) => {
      const spawn = await setup(page);
      await expect(
        page.getByRole("radio", { name: "Novice 3 questions · 2 correct" }),
      ).toBeChecked();
      await page
        .getByRole("radio", {
          name: `${config.label} ${config.count} questions · ${config.required} correct`,
        })
        .check();
      const saved = await page.evaluate(
        (id) =>
          JSON.parse(
            localStorage.getItem("modemon-go:playable:v1:progress:demo")!,
          ).attempts[id],
        spawn.id,
      );
      expect(saved.difficulty).toBe(difficulty);
      expect(saved.answers).toEqual([]);
      expect(saved.questions).toHaveLength(config.count);
      // The selection is persisted even before the first answer.
      await page.reload();
      await reopen(page, spawn.poi.id);
      await expect(
        page.getByRole("radio", {
          name: `${config.label} ${config.count} questions · ${config.required} correct`,
        }),
      ).toBeChecked();
      await page
        .getByRole("button", {
          name: `Capture · ${config.count} questions`,
          exact: true,
        })
        .click();
      const qs = difficultyQuestionsFor(spawn, data, difficulty);
      const target = passes ? config.required : config.required - 1;
      for (const [i, q] of qs.entries()) {
        await expect(
          page.getByText(
            `Question ${i + 1} of ${config.count} · at least ${config.required} correct to capture`,
            { exact: true },
          ),
        ).toBeVisible();
        const correct = i < target;
        const answer = correct ? q.correct : (q.correct + 1) % 4;
        await page
          .getByRole("button", { name: q.options[answer], exact: true })
          .click();
        const feedback = page.locator(
          `.feedback--${correct ? "correct" : "incorrect"}`,
        );
        await expect(feedback).toBeVisible();
        await expect(feedback).toContainText(
          correct ? "Correct." : "Not quite.",
        );
        await expect(feedback).toContainText(q.options[q.correct]);
        await expect(feedback.locator("svg")).toHaveAttribute(
          "aria-hidden",
          "true",
        );
        await expect(feedback).toHaveCSS(
          "color",
          correct ? "rgb(18, 63, 47)" : "rgb(127, 29, 29)",
        );
        await expect(page.locator(".quiz-score")).toContainText(
          `${config.label} · ${Math.min(i + 1, target)} correct from ${i + 1} answered`,
        );
        if (i === 0) {
          // Close, switch browser modes and reload: same attempt, answers and mode.
          await page
            .getByRole("button", { name: "Close encounter", exact: true })
            .click();
          await page
            .getByRole("button", { name: "Exit Demo Mode", exact: true })
            .click();
          await page
            .getByRole("button", { name: "Try Demo Mode", exact: true })
            .click();
          await page.reload();
          await reopen(page, spawn.poi.id);
          await expect(page.getByRole("radio")).toHaveCount(3);
          for (const radio of await page.getByRole("radio").all())
            await expect(radio).toBeDisabled();
          await page
            .getByRole("button", {
              name: `Capture · ${config.count} questions`,
              exact: true,
            })
            .click();
          await expect(feedback).toBeVisible();
        }
        if (i === config.count - 1) {
          await page.screenshot({
            path: info.outputPath(
              `${difficulty}-${passes ? "pass" : "fail"}-feedback.png`,
            ),
          });
        }
        await page
          .getByRole("button", {
            name: i === config.count - 1 ? "Show result" : "Next question",
            exact: true,
          })
          .click();
      }
      await expect(
        page.getByRole("heading", {
          name: passes ? "Captured!" : "It escaped.",
          exact: true,
        }),
      ).toBeVisible();
      const final = await page.evaluate(
        (id) =>
          JSON.parse(
            localStorage.getItem("modemon-go:playable:v1:progress:demo")!,
          ).attempts[id],
        spawn.id,
      );
      expect(final.difficulty).toBe(difficulty);
      expect(final.answers).toHaveLength(config.count);
      expect(final.status).toBe(passes ? "captured" : "escaped");
      expect(final.questions).toEqual(saved.questions);
      await page.reload();
      await expect(
        page.locator(`.encounter-row[data-poi-id="${spawn.poi.id}"]`),
      ).toHaveCount(0);
      await expect(page.locator("header")).toContainText(
        passes ? "1 captured" : "0 captured",
      );
      await page
        .getByRole("button", { name: "Exit Demo Mode", exact: true })
        .click();
      await expect(page.locator("header")).toContainText("0 captured");
    });
  }
}

test("difficulty controls and Expert long-answer questions fit narrow, portrait and landscape layouts", async ({
  page,
}, info) => {
  const spawn = await setup(page);
  for (const [width, height] of [
    [320, 568],
    [393, 852],
    [844, 390],
  ]) {
    await page.setViewportSize({ width, height });
    const radio = page.getByRole("radio", {
      name: "Expert 7 questions · 4 correct",
    });
    await radio.check();
    await page
      .getByRole("button", { name: "Capture · 7 questions", exact: true })
      .scrollIntoViewIfNeeded();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: info.outputPath(`selector-${width}x${height}.png`),
    });
  }
  await page
    .getByRole("button", { name: "Capture · 7 questions", exact: true })
    .click();
  const qs = difficultyQuestionsFor(spawn, data, "expert");
  for (const [i, q] of qs.entries()) {
    if (i >= 4) {
      for (const [width, height] of [
        [320, 568],
        [393, 852],
        [844, 390],
      ]) {
        await page.setViewportSize({ width, height });
        const choices = page.locator("button.answer");
        await expect(choices).toHaveCount(4);
        for (const choice of await choices.all()) {
          await choice.scrollIntoViewIfNeeded();
          await expect(choice).toBeVisible();
          expect(
            await choice.evaluate((el) => el.scrollWidth <= el.clientWidth),
          ).toBe(true);
        }
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBe(true);
        await page.screenshot({
          path: info.outputPath(`question-${i + 1}-${width}x${height}.png`),
        });
      }
    }
    await page
      .getByRole("button", { name: q.options[q.correct], exact: true })
      .click();
    await page
      .getByRole("button", {
        name: i === 6 ? "Show result" : "Next question",
        exact: true,
      })
      .click();
  }
  await expect(
    page.getByRole("heading", { name: "Captured!", exact: true }),
  ).toBeVisible();
});
