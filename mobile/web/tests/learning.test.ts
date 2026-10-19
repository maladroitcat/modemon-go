import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";
import { learningFor, safeLearningUrl } from "../src/learning.ts";
import { signatureProject } from "../src/signatures.ts";
import type { Runtime } from "../src/engine.ts";

const data = JSON.parse(readFileSync(new URL("../src/data/runtime.json", import.meta.url), "utf8")) as Runtime;
const overlay = JSON.parse(readFileSync(new URL("../src/data/learning.json", import.meta.url), "utf8"));

test("exactly 39 ID-keyed entries, 35 workbook primaries and four approved external references", () => {
  const ordinary = Object.entries(data.modedex.modemon).filter(([, s]) => s.stage < 3);
  assert.deepEqual(Object.keys(overlay.species).sort(), ordinary.map(([id]) => id).sort());
  assert.equal(ordinary.length, 39);
  assert.equal(ordinary.filter(([id, s]) => learningFor(id, s)[0].kind === "external").length, 4);
  for (const [id, s] of ordinary) assert.ok(learningFor(id, s).length >= 1);
});

test("safe educational URLs require exact approved path, HTTPS and allowed host", () => {
  for (const row of Object.values(overlay.species) as { primary: { url: string } }[])
    assert.equal(safeLearningUrl(row.primary.url), row.primary.url);
  for (const url of [null, "", "javascript:alert(1)", "data:text/html,unsafe", "/relative", "//www.ibm.com/think/x",
    "https://www.ibm.com/think/unapproved", "http://news.mit.edu/2016/x", "https://www.ibm.com.evil.test/think/x",
    "https://user:password@www.ibm.com/think/topics/dispatch-management", "https://localhost/lesson",
    "https://www.ibm.com/think/topics/dispatch-management?next=evil", "https://www.ibm.com/think/topics/dispatch-management#x",
    "https://www.ibm.com/think/topics/dispatch-management\n", "https://www.ibm.com\\evil.test/think/x"])
    assert.equal(safeLearningUrl(url), null);
});

test("no name fallback, prototype keys, unknown IDs or supplementary Signature links", () => {
  const before = JSON.stringify({ data, overlay });
  for (const [id, s] of Object.entries(data.modedex.modemon)) {
    if (s.stage === 3) assert.deepEqual(learningFor(id, s), []);
    else {
      assert.deepEqual(learningFor(s.name, s), []);
      assert.deepEqual(learningFor(undefined, s), []);
      assert.deepEqual(learningFor("__proto__", s), []);
    }
  }
  assert.deepEqual(learningFor("detector_base", { stage: 3 }), []);
  assert.equal(JSON.stringify({ data, overlay }), before);
});

test("all details render accessible approved readings or ONLY canonical Signature project links", async () => {
  const vite = await createServer({ configFile: false, root: fileURLToPath(new URL("..", import.meta.url)),
    server: { middlewareMode: true, hmr: false, ws: false }, oxc: { jsx: { runtime: "automatic" } } });
  try {
    const { default: DexEntry } = await vite.ssrLoadModule("/src/DexEntry.tsx");
    for (const [id, s] of Object.entries(data.modedex.modemon)) {
      const html = renderToStaticMarkup(createElement(DexEntry, { species: s, modemonId: id, habitatTitle: (x: string) => x }));
      const links = learningFor(id, s);
      if (s.stage === 3) {
        assert.doesNotMatch(html, /class="learning-links"/);
        assert.equal((html.match(/<a\s/g) ?? []).length, 1);
        assert.ok(html.includes(signatureProject(s)!.href!.replaceAll("&", "&amp;")));
        assert.match(html, /Learn about the real project/);
      } else {
        assert.match(html, /Learn about this kind of AI/);
        assert.equal((html.match(/<a\s/g) ?? []).length, links.length);
        assert.equal((html.match(/rel="noopener noreferrer"/g) ?? []).length, links.length);
        for (const link of links) {
          assert.ok(html.includes(link.url));
          assert.ok(html.includes(link.title.replaceAll("&", "&amp;")));
        }
        assert.match(html, /aria-label="Read .*opens in a new tab/);
        assert.match(html, /aria-hidden="true"/);
      }
    }
    const html = renderToStaticMarkup(createElement(DexEntry, { species: data.modedex.modemon.detector_base,
      modemonId: "not_a_species", habitatTitle: (x: string) => x }));
    assert.doesNotMatch(html, /class="learning-links"/);
  } finally {
    await vite.close();
  }
});
