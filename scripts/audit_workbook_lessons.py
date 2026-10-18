#!/usr/bin/env python3
"""Research-only HTTP/lesson-content audit; never imports or edits gameplay data."""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests

ROOT = Path(__file__).resolve().parents[1]
DOMAINS = {"explainableaiworkbook.com", "datascienceworkbook.com", "deeplearningworkbook.com"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.in_main = 0
        self.heading = None
        self.heading_parts = []
        self.headings = []
        self.parts = []
        self.anchor = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self.skip += 1
        if tag == "main":
            self.in_main += 1
        if tag in ("h1", "h2", "h3") and not self.skip:
            self.heading = tag
            self.heading_parts = []
        if tag == "a" and not self.skip:
            self.anchor = [attrs.get("href", ""), []]

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        if tag == "main":
            self.in_main = max(0, self.in_main - 1)
        if tag == self.heading:
            self.headings.append((tag, " ".join(" ".join(self.heading_parts).split())))
            self.heading = None
        if tag == "a" and self.anchor:
            self.links.append((self.anchor[0], " ".join(" ".join(self.anchor[1]).split())))
            self.anchor = None

    def handle_data(self, data):
        if self.skip:
            return
        if self.in_main:
            self.parts.append(data)
        if self.heading:
            self.heading_parts.append(data)
        if self.anchor:
            self.anchor[1].append(data)


def fetch(url):
    if urlsplit(url).hostname not in DOMAINS or urlsplit(url).scheme != "https":
        raise ValueError(f"Outside approved workbook domains: {url}")
    response = requests.get(url, timeout=40, headers={"User-Agent": "ModemonGO-WorkbookResearch/1.0 (+https://github.com/maladroitcat/modemon-go/issues/26)"})
    response.raise_for_status()
    if urlsplit(response.url).hostname not in DOMAINS:
        raise ValueError("Redirect left authorized sites")
    page = Page()
    page.feed(response.text)
    text = " ".join(" ".join(page.parts).split())
    return response, page, text


def discover():
    results = {}
    for domain in sorted(DOMAINS):
        home = f"https://{domain}/"
        _, page, _ = fetch(home)
        units = sorted({urljoin(home, href) for href, _ in page.links
                        if urlsplit(urljoin(home, href)).hostname == domain
                        and len(urlsplit(urljoin(home, href)).path.strip("/").split("/")) == 1
                        and urlsplit(urljoin(home, href)).path not in ("", "/")})
        for url in units:
            time.sleep(.4)
            _, unit, _ = fetch(url)
            results[url] = {"headings": unit.headings,
                            "lessons": sorted(set((urljoin(url, href), label) for href, label in unit.links
                                                  if urlsplit(urljoin(url, href)).hostname == domain
                                                  and len(urlsplit(urljoin(url, href)).path.strip("/").split("/")) >= 3))}
    return results


def verify(catalog):
    results = {}
    tocs = {}
    for key, lesson in sorted(catalog.items()):
        toc_url = lesson["toc_url"]
        if toc_url not in tocs:
            time.sleep(.4)
            _, toc, _ = fetch(toc_url)
            tocs[toc_url] = {urljoin(toc_url, href): label for href, label in toc.links}
        if lesson["url"] not in tocs[toc_url]:
            raise ValueError(f"Lesson not linked from its live TOC: {key}")
        time.sleep(.4)
        response, page, text = fetch(lesson["url"])
        title = next((heading for tag, heading in page.headings if tag == "h1"), "")
        terms = {term: term.casefold() in text.casefold() for term in lesson["verification_terms"]}
        if not title or title != lesson["article_title"] or not all(terms.values()) or len(text) < 300:
            raise ValueError(f"Lesson content mismatch: {key}; title={title!r}; terms={terms}")
        results[key] = dict(url=lesson["url"], final_url=response.url, http_status=response.status_code,
                            toc_url=toc_url, toc_link_label=tocs[toc_url][lesson["url"]],
                            article_title=title, verification_terms_found=terms,
                            main_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                            verified_at_utc=datetime.now(timezone.utc).isoformat())
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.discover:
        result = discover()
    else:
        import yaml
        data = yaml.safe_load((ROOT / "data/config/modedex_learning_links.yaml").read_text(encoding="utf-8"))
        result = verify(data["lessons"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Audited {len(result)} workbook {'unit TOCs' if args.discover else 'lesson pages'} -> {args.output}")
