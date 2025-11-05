#!/usr/bin/env python3
"""
Sync poems from a published Google Doc (Publish to the web -> link) into poems.json.

Usage (in GitHub Actions):
  export PUBLISHED_DOC_URL="https://docs.google.com/document/d/e/.../pub"
  python scripts/sync_poems.py

It writes/updates ./poems.json at the repo root.
"""
import os
import re
import sys
import json
import requests
from bs4 import BeautifulSoup

PUBLISHED_DOC_URL = os.environ.get("PUBLISHED_DOC_URL", "").strip()

if not PUBLISHED_DOC_URL:
    print("ERROR: PUBLISHED_DOC_URL is not set. Please set it to the 'Publish to the web' URL of the Google Doc.", file=sys.stderr)
    sys.exit(1)

# Categories we recognize (in both languages for robustness)
CATEGORY_TITLES = [
    ("Стихи / Poems", {"ru": "Стихи", "en": "Poems"}),
    ("Переводы / Translations", {"ru": "Переводы", "en": "Translations"}),
    ("Шутки в сторону / Not serious", {"ru": "Шутки в сторону", "en": "Not serious"}),
]

CATEGORY_LABELS = [c[0] for c in CATEGORY_TITLES]

def is_year_line(s: str) -> bool:
    s = s.strip()
    return bool(re.fullmatch(r"(19|20)\d{2}", s))

def clean_text(s: str) -> str:
    """Collapse 3+ newlines, but preserve single/double newlines (stanzas)."""
    s = s.rstrip()
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s

def fetch_html(url: str) -> str:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text

def extract_lines_from_html(html: str):
    """Extract lines while preserving line breaks within paragraphs."""
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.find_all(["h1", "h2", "h3", "p", "li", "div"])
    lines = []
    for b in blocks:
        # preserve <br> and soft breaks
        t = b.get_text(separator="\n", strip=True)
        if not t:
            continue
        # split into physical lines
        for line in t.split("\n"):
            line = line.strip()
            if line:
                lines.append(line)
    # remove Google header noise if present
    lines = [l for l in lines if not l.lower().startswith("published using google docs")]
    return lines

def looks_like_category(line: str) -> str:
    t = line.strip()
    for label, langs in CATEGORY_TITLES:
        if t == label or any(k.lower() in t.lower() for k in langs.values()):
            return label
    return ""

def parse_poems(lines):
    """
    Heuristic parser:
      - Track current_category
      - A poem starts when we see a non-category/non-year line and no current_title
      - Collect body lines until a year line appears, which closes the poem
    """
    current_category = None
    current_title = None
    current_body = []
    current_year = None

    poems = []

    def flush_poem():
        nonlocal current_title, current_body, current_year, current_category
        if current_title and (current_body or current_year):
            poem = {
                "category": current_category or CATEGORY_TITLES[0][0],
                "title": current_title.strip(),
                "body": clean_text("\n".join(current_body).strip()),
            }
            if current_year:
                poem["year"] = current_year
            poems.append(poem)
        current_title = None
        current_body = []
        current_year = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        cat = looks_like_category(line)
        if cat:
            flush_poem()
            current_category = cat
            continue

        if is_year_line(line):
            current_year = line
            flush_poem()
            continue

        if current_title is None:
            # ignore pure separator lines
            if set(line) <= set("-—–_•* "):
                continue
            current_title = line
            continue

        current_body.append(line)

    flush_poem()
    return poems

def main():
    html = fetch_html(PUBLISHED_DOC_URL)
    lines = extract_lines_from_html(html)
    poems = parse_poems(lines)

    # Sort poems within each category by year (desc) then title
    def sort_key(p):
        try:
            y = int(p.get("year", "0"))
        except ValueError:
            y = 0
        return (-y, p["title"].lower())

    out_by_cat = {label: [] for label, _ in CATEGORY_TITLES}
    for p in poems:
        out_by_cat.setdefault(p["category"], []).append(p)

    for k in out_by_cat:
        out_by_cat[k].sort(key=sort_key)

    # Flatten
    flattened = [p for cat in CATEGORY_LABELS for p in out_by_cat.get(cat, [])]

    out_path = os.path.join(os.getcwd(), "poems.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(flattened, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path} with {len(flattened)} poems.")

if __name__ == "__main__":
    main()
