import overlay from "./data/learning.json" with { type: "json" };
import type { Species } from "./engine.ts";

export type LearningLink = Readonly<{
  title: string;
  source: string;
  url: string;
  kind: "workbook" | "external";
  scope_note: string;
}>;
type Entry = Readonly<{ primary: LearningLink; secondary: LearningLink | null }>;
const entries = overlay.species as Readonly<Record<string, Entry>>;
const approvedUrls = new Set(Object.values(entries).flatMap((e) =>
  [e.primary.url, ...(e.secondary ? [e.secondary.url] : [])]));
const hosts = new Set([
  "explainableaiworkbook.com", "datascienceworkbook.com", "deeplearningworkbook.com",
  "news.mit.edu", "www.ibm.com", "blog.optibus.com",
]);

export function safeLearningUrl(value: unknown): string | null {
  if (typeof value !== "string" || /[\u0000-\u0020\u007f\\]/.test(value) || !approvedUrls.has(value)) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && hosts.has(url.hostname) && !url.username &&
      !url.password && !url.port && !url.search && !url.hash ? value : null;
  } catch {
    return null;
  }
}

export function learningFor(id: string | undefined, species: Pick<Species, "stage">): readonly LearningLink[] {
  if (!id || species.stage === 3 || !Object.hasOwn(entries, id)) return [];
  const entry = entries[id];
  return [entry.primary, ...(entry.secondary ? [entry.secondary] : [])]
    .filter((link) => safeLearningUrl(link.url));
}
