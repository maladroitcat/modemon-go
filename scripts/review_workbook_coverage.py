#!/usr/bin/env python3
"""Index every discovered workbook lesson; cache article text only outside Git."""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.audit_workbook_lessons import DOMAINS, ROOT, discover, fetch

# Broad search leads, not automatic relevance decisions. A mention is not a lesson.
TERMS = (
    "anomaly", "outlier", "autoencoder", "isolation forest", "one-class", "survival",
    "sensor", "time series", "monitoring", "network", "intrusion", "classification",
    "recommendation", "personalization", "learner", "adaptive", "ranking", "curation",
    "ocr", "optical character", "handwriting", "transcription", "document",
    "named entity", "entity recognition", "information extraction", "relation extraction",
    "clinical", "medical", "layout", "vision-language", "multimodal", "token classification",
    "topic model", "text mining", "text representation", "embedding", "structured",
    "prompt", "in-context", "language model", "retrieval", "catalog", "provenance",
    "schedule", "scheduling", "routing", "vehicle", "constraint", "integer programming",
    "linear programming", "optimization", "optimisation", "heuristic", "reinforcement",
    "agent", "dialogue", "conversation", "intent", "traffic", "decision support",
)


def scan(cache_dir, refresh=False):
    if cache_dir.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Keep cached article bodies outside the repository")
    cache_dir.mkdir(parents=True, exist_ok=True)
    toc = discover()
    urls = sorted({url for unit in toc.values() for url, _ in unit["lessons"]})
    pages = {}
    for index, url in enumerate(urls, 1):
        cache = cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        if cache.exists() and not refresh:
            item = json.loads(cache.read_text(encoding="utf-8"))
            if item["url"] != url:
                raise ValueError("Cache identity mismatch")
        else:
            for attempt in range(3):
                try:
                    time.sleep(.4 + attempt)
                    response, page, text = fetch(url)
                    title = next((heading for tag, heading in page.headings if tag == "h1"), "")
                    if response.status_code != 200 or not title or len(text) < 200:
                        raise ValueError(f"Missing article content: {url}")
                    item = {"url": url, "final_url": response.url, "http_status": response.status_code,
                            "article_title": title, "headings": page.headings, "text": text,
                            "verified_at_utc": datetime.now(timezone.utc).isoformat()}
                    cache.write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")
                    break
                except Exception:
                    if attempt == 2:
                        raise
        text = item["text"]
        record = {key: value for key, value in item.items() if key != "text"}
        record.update(main_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                      text_characters=len(text),
                      term_occurrences={term: text.casefold().count(term) for term in TERMS
                                        if term in text.casefold()})
        pages[url] = record
        if index % 25 == 0 or index == len(urls):
            print(f"Indexed {index}/{len(urls)} lesson bodies", flush=True)
    research = ROOT / "data/research"
    (research / "workbook_toc_inventory.json").write_text(json.dumps(toc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = {"scope": "All unique lesson URLs discovered from every unit linked on all three workbook homepages",
              "method": "Full main-body indexing, broad topic-term search, then human relevance review; term hits alone do not approve a match",
              "domains": sorted(DOMAINS), "unit_count": len(toc), "lesson_count": len(urls),
              "failed_urls": [], "pages": pages}
    (research / "workbook_full_review.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    result = scan(args.cache_dir, args.refresh)
    print(f'Exhaustive discovered coverage: {result["unit_count"]} units, {result["lesson_count"]} lesson bodies; no article bodies committed.')
