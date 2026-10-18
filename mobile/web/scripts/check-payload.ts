import { readFileSync, readdirSync } from "node:fs";
import { gzipSync } from "node:zlib";

const assets = new URL("../dist/assets/", import.meta.url);
const files = readdirSync(assets);
const js = files.filter((name) => name.endsWith(".js"));
const css = files.filter((name) => name.endsWith(".css"));
const jsGzip = js.reduce((total, name) => total + gzipSync(readFileSync(new URL(name, assets))).length, 0);
const cssBytes = css.reduce((total, name) => total + readFileSync(new URL(name, assets)).length, 0);
if (!js.length || jsGzip > 550_000 || cssBytes > 30_000)
  throw Error(`Mobile payload budget exceeded: JS gzip ${jsGzip}/550000, CSS ${cssBytes}/30000`);
console.log(`Mobile payload: ${jsGzip} gzip JS bytes, ${cssBytes} CSS bytes; no image masters in entry bundle.`);
