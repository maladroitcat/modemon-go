import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";
import { fileURLToPath } from "node:url";
import type { Runtime } from "../src/engine.ts";

const data = JSON.parse(readFileSync(new URL("../src/data/runtime.json", import.meta.url), "utf8")) as Runtime;
const escaped = (text: string) => renderToStaticMarkup(createElement("span", null, text)).replace(/^<span>|<\/span>$/g, "");
test("all trading cards preserve complete canonical educational fields; examples stay outside encounters", async () => {
  const vite = await createServer({ configFile: false, root: fileURLToPath(new URL("..", import.meta.url)),
    server: { middlewareMode: true, hmr: false, ws: false }, oxc: { jsx: { runtime: "automatic" } } });
  try {
    const { default: DexEntry } = await vite.ssrLoadModule("/src/DexEntry.tsx");
    for (const [id, s] of Object.entries(data.modedex.modemon)) {
      const props = { species: s, habitatTitle: (id: string) => id, modemonId: id,
        familyName: data.modedex.families![s.family_id].name };
      const html = renderToStaticMarkup(createElement(DexEntry, { ...props, showExamples: true, mastery: new Set(["expert"]) }));
      for (const text of [s.name, s.role, s.dex_entry, s.input_data, s.output_data,
        ...s.habitats, ...s.ai_tasks, ...s.models_algorithms, ...s.biases_limitations, ...s.explainability])
        assert.ok(html.includes(escaped(text)), `${id}: missing ${text}`);
      for (const heading of ["Ability / Job", "How It Works", "Weaknesses / Limitations", "Explainability", "AI in the Wild", "Further Learning"])
        assert.ok(html.includes(heading), `${id}: ${heading}`);
      assert.ok(html.includes("Expert Badge: earned"));
      assert.ok(html.includes("Beginner Badge: locked"));
      assert.ok(html.includes("Intermediate Badge: locked"));
      const encounter = renderToStaticMarkup(createElement(DexEntry, props));
      assert.ok(!encounter.includes("AI in the Wild"));
      assert.ok(!encounter.includes("Quiz mastery badges"));
      if (s.stage === 3) {
        const source = s.signature as { source_url: string; source_title: string; verified_use: string; documented_technology: string[] };
        for (const text of [source.source_url, source.source_title, source.verified_use, ...source.documented_technology])
          assert.ok(html.includes(escaped(text)), `${id}: source provenance`);
      }
    }
  } finally { await vite.close(); }
});
