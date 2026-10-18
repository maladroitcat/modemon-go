import type { Species } from "./engine.ts";

type Signature = {
  anchor_name: string;
  anchor_scope: string;
  verified_use: string;
  source_title: string;
  source_organization: string;
  source_url: string;
  documented_technology: string[];
};
const scopes: Record<string, string> = {
  research_project: "research project",
  institution: "institution-level example",
  library_system: "library-system example",
  agency_system: "transit-system example",
  agency_service: "service example",
  city_system: "city-system example",
};
export function safeProjectUrl(value: unknown): string | null {
  if (typeof value !== "string" || !value || /[\u0000-\u0020\\]/.test(value))
    return null;
  try {
    const url = new URL(value);
    if (
      url.protocol !== "https:" ||
      url.username ||
      url.password ||
      url.port ||
      !url.hostname.includes(".") ||
      url.hostname.endsWith(".local") ||
      url.hostname === "127.0.0.1" ||
      url.hostname === "0.0.0.0"
    )
      return null;
    return value;
  } catch {
    return null;
  }
}
export function signatureProject(species: Species) {
  if (species.stage !== 3) return null;
  const raw = species.signature;
  if (!raw || typeof raw !== "object")
    return {
      introduction: null,
      source: null,
      href: null,
      review:
        "Signature inspiration needs source review. No project has been inferred.",
    };
  const s = raw as Signature;
  const required = [
    s.anchor_name,
    s.anchor_scope,
    s.verified_use,
    s.source_title,
    s.source_organization,
  ];
  if (
    required.some((v) => typeof v !== "string" || !v.trim()) ||
    !Array.isArray(s.documented_technology) ||
    s.documented_technology.some((v) => typeof v !== "string" || !v.trim())
  )
    return {
      introduction: null,
      source: null,
      href: null,
      review:
        "Signature inspiration needs source review. Required provenance is missing.",
    };
  const href = safeProjectUrl(s.source_url);
  return {
    introduction: `${species.name}'s real-world inspiration is ${s.anchor_name}'s documented ${scopes[s.anchor_scope] ?? "example"}: ${s.verified_use}. Recorded evidence: “${s.source_title}”.`,
    source: s,
    href,
    review: href
      ? null
      : "The recorded project link is missing or unsafe. Source review is needed; no replacement link has been guessed.",
  };
}
