import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";
import { fileURLToPath } from "node:url";
import { approximateDistance, proximityCopy } from "../src/presentation.ts";
import { safeProjectUrl, signatureProject } from "../src/signatures.ts";
import { buildWorld, interaction, type Runtime } from "../src/engine.ts";
import { rules } from "../src/rules.ts";

const data = JSON.parse(
  readFileSync(new URL("../src/data/runtime.json", import.meta.url), "utf8"),
) as Runtime;
const signatures = Object.entries(data.modedex.modemon).filter(
  ([, s]) => s.stage === 3,
);

test("US display rounding handles short feet, exact quarter-mile transition, longer miles and invalid input", () => {
  for (const [meters, expected] of [
    [0, "0 ft"],
    [0.01, "1 ft"],
    [1, "3 ft"],
    [30.48, "100 ft"],
    [75, "250 ft"],
    [381, "1,250 ft"],
    [1609.344 / 4 - 1e-8, "1,320 ft"],
    [1609.344 / 4, "0.25 mi"],
    [804.672, "0.5 mi"],
    [1250, "0.78 mi"],
    [1609.344, "1 mi"],
    [1609.344 * 1.26, "1.3 mi"],
  ] as const)
    assert.equal(approximateDistance(meters), expected);
  for (const invalid of [NaN, Infinity, -Infinity, -1])
    assert.equal(approximateDistance(invalid), "distance unavailable");
});

test("rounded 250ft instruction does not change the 75m gate, metric accuracy or density rules", () => {
  const spawn = buildWorld(data, "2026-10-17")[0];
  const fix = (meters: number) => ({
    lat: spawn.poi.lat + ((meters / 6371008.8) * 180) / Math.PI,
    lon: spawn.poi.lon,
    accuracy: 0,
    timestamp: 100000,
  });
  assert.equal(interaction(spawn, fix(74.99), 100000).allowed, true);
  const gate = interaction(spawn, fix(75.01), 100000);
  assert.equal(gate.allowed, false);
  assert.match(proximityCopy("real", fix(75.01), gate), /roughly 250 ft/);
  assert.equal(rules.interactionMeters, 75);
  assert.equal(rules.maximumAccuracyMeters, 50);
  assert.equal(rules.densityRadiusMeters, 804.672);
});

test("all twelve Signature introductions name existing canonical project, use-case, scope and exact safe URL", () => {
  const before = JSON.stringify(data);
  assert.equal(signatures.length, 12);
  for (const [, species] of signatures) {
    const project = signatureProject(species)!;
    assert.ok(project.introduction);
    assert.ok(project.source);
    assert.equal(project.review, null);
    assert.equal(project.href, project.source.source_url);
    for (const text of [
      species.name,
      project.source.anchor_name,
      project.source.verified_use,
      project.source.source_title,
    ])
      assert.ok(project.introduction.includes(text));
  }
  assert.equal(signatureProject(data.modedex.modemon.detector_base), null);
  assert.equal(JSON.stringify(data), before);
  assert.ok(
    buildWorld(data, "2026-10-17").every(
      (s) => data.modedex.modemon[s.speciesId].stage < 3,
    ),
  );
});

test("missing and unsafe provenance links never become anchors or guessed replacements", () => {
  for (const url of [
    null,
    undefined,
    "",
    "javascript:alert(1)",
    "data:text/html,unsafe",
    "http://example.com",
    "/relative",
    "//example.com",
    "https://user:password@example.com",
    "https://localhost",
    "https://example.local",
    "https://127.0.0.1",
    "https://example.com\n",
    "https://example.com\\evil",
  ]) {
    assert.equal(safeProjectUrl(url), null);
    const species = {
      ...signatures[0][1],
      signature: { ...(signatures[0][1].signature as object), source_url: url },
    };
    const project = signatureProject(species)!;
    assert.equal(project.href, null);
    assert.match(project.review!, /review/);
  }
  const missing = signatureProject({ ...signatures[0][1], signature: null })!;
  assert.equal(missing.introduction, null);
  assert.match(missing.review!, /No project has been inferred/);
});

test("standalone Signature detail renders accessible canonical links and safe missing/unsafe-source states", async () => {
  const vite = await createServer({
    configFile: false,
    root: fileURLToPath(new URL("..", import.meta.url)),
    server: { middlewareMode: true, hmr: false, ws: false },
    oxc: { jsx: { runtime: "automatic" } },
  });
  try {
    const { default: DexEntry } = await vite.ssrLoadModule("/src/DexEntry.tsx");
    for (const [, species] of signatures) {
      const html = renderToStaticMarkup(
        createElement(DexEntry, { species, habitatTitle: (s: string) => s }),
      );
      assert.match(html, /Learn about the real project/);
      assert.match(html, /target="_blank"/);
      assert.match(html, /rel="noopener noreferrer"/);
      assert.match(html, /not a claim that this system runs at your location/);
      assert.match(html, /Representative techniques \(not deployment claims\)/);
    }
    for (const signature of [
      null,
      {
        ...(signatures[0][1].signature as object),
        source_url: "javascript:alert(1)",
      },
    ]) {
      const html = renderToStaticMarkup(
        createElement(DexEntry, {
          species: { ...signatures[0][1], signature },
          habitatTitle: (s: string) => s,
        }),
      );
      assert.doesNotMatch(html, /<a\s|href=|javascript:/);
      assert.match(html, /role="alert"/);
    }
  } finally {
    await vite.close();
  }
});
