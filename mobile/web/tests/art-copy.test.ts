import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import ts from "typescript";

const source = (file: string) => readFileSync(new URL(`../src/${file}`, import.meta.url), "utf8");
const baseline = JSON.parse(readFileSync(new URL("./fixtures/issue23-copy-baseline.json", import.meta.url), "utf8")) as {
  jsx: Record<string, string[]>; hashes: Record<string, string>;
};
function jsxText(text: string) {
  const file = ts.createSourceFile("component.tsx", text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const values: string[] = [];
  function visit(node: ts.Node) {
    if (ts.isJsxText(node)) {
      const value = node.getText(file).replace(/\s+/g, " ").trim();
      if (value) values.push(value);
    }
    ts.forEachChild(node, visit);
  }
  visit(file);
  return values;
}

test("issue 23 preserves approved UI, Modedex and quiz wording outside explicit availability exceptions", () => {
  for (const [file, expected] of Object.entries(baseline.hashes))
    assert.equal(createHash("sha256").update(source(file)).digest("hex"), expected, file);
  assert.deepEqual(jsxText(source("DexEntry.tsx")), baseline.jsx["DexEntry.tsx"]);
  const normalize = (values: string[]) => values.filter((value) =>
    !["?", "Artwork unavailable", "Modémon GO", "Official access notice"].includes(value)
    && !value.startsWith("Prototype limitations:")
    && !value.startsWith("Durham Station Signatures use an alternative"));
  assert.deepEqual(normalize(jsxText(source("Game.tsx"))), normalize(baseline.jsx["Game.tsx"]));
  assert.match(source("Game.tsx"), /Browser progress is not\s+synchronized across devices/);
  const moved = jsxText(source("Art.tsx"));
  for (const value of ["?", "Artwork unavailable", "Modémon GO"]) assert.ok(moved.includes(value));
});
