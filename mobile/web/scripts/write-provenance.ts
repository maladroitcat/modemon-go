import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, writeFileSync } from "node:fs";

const git = (...args: string[]) => execFileSync("git", args, { encoding: "utf8" }).trim();
const sha = (bytes: Buffer) => createHash("sha256").update(bytes).digest("hex");
const assets = new URL("../dist/assets/", import.meta.url);
const art = JSON.parse(readFileSync(new URL("../src/data/art.json", import.meta.url), "utf8"));
const provenance = {
  application_repository: "https://github.com/maladroitcat/modemon-go",
  application_branch: git("rev-parse", "--abbrev-ref", "HEAD"),
  application_commit: git("rev-parse", "HEAD"),
  build_command: "npm run build:playable",
  learning_overlay_sha256: sha(readFileSync(new URL("../src/data/learning.json", import.meta.url))),
  optimized_creature_count: Object.keys(art.creatures).length,
  logo_present: !!art.logo,
  assets: Object.fromEntries(readdirSync(assets).sort().map((name) =>
    [`/assets/${name}`, sha(readFileSync(new URL(name, assets)))])),
};
writeFileSync(new URL("../dist/deployment-provenance.json", import.meta.url), JSON.stringify(provenance, null, 2) + "\n");
console.log(`Production provenance: ${provenance.application_branch}@${provenance.application_commit}`);
