import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { learningFor, safeLearningUrl } from "../src/learning.ts";
import type { Runtime } from "../src/engine.ts";

const read = (path: string) => JSON.parse(readFileSync(new URL(path, import.meta.url), "utf8"));
const runtime = read("../src/data/runtime.json") as Runtime;
const overlay = read("../src/data/learning.json");
const ordinary = Object.entries(runtime.modedex.modemon).filter(([, s]) => s.stage < 3);
if (overlay.version !== 1 || ordinary.length !== 39 ||
  Object.keys(overlay.species).sort().join() !== ordinary.map(([id]) => id).sort().join())
  throw Error("Learning overlay must cover exactly 39 non-Signatures");
for (const [id, species] of Object.entries(runtime.modedex.modemon)) {
  const links = learningFor(id, species);
  if (species.stage === 3 ? links.length !== 0 : links.length < 1 || links.length > 2)
    throw Error(`Invalid learning-link coverage: ${id}`);
  for (const link of links)
    if (!safeLearningUrl(link.url) || ![link.title, link.source, link.scope_note].every((s) => typeof s === "string" && s.trim()))
      throw Error(`Unsafe or incomplete learning link: ${id}`);
}
for (const [path, digest] of Object.entries(overlay.source_hashes)) {
  const current = createHash("sha256").update(readFileSync(fileURLToPath(new URL("../../../" + path, import.meta.url)))).digest("hex");
  if (current !== digest) throw Error(`Stale learning overlay; rebuild after changing ${path}`);
}
console.log("Learning links: 35 workbook entries + 4 approved outside readings; 12 Signatures excluded from supplementary links.");
