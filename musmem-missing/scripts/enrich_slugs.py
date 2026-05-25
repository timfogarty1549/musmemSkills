#!/usr/bin/env python3
"""
Enrich npcnol_slugs.json with a sample athlete: first #1 placer in the first
non-excluded division on each contest page.
Uses cache at ~/workspace/musmem/.page_cache/{year}_{slug}.html.
Fetches missing pages and writes them to cache.
Saves progress after each year so the script is safe to interrupt.
"""

import json
import os
import re
import subprocess
import time
from html.parser import HTMLParser

SLUGS_FILE  = os.path.expanduser(
    "~/workspace/skills/musmemSkills/musmem-missing/data/npcnol_slugs.json")
CACHE_DIR   = os.path.expanduser("~/workspace/musmem/.page_cache")
UA          = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
               "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Division titles that mean we skip the whole section
SKIP_DIV_WORDS = [
    "bikini", "wellness", "fitness", "novice", "beginner",
    "true novice", "first timer", "fit model", "armed forces",
    "first responder", "natural",   # skip natural divisions
]

def cache_path(year, slug):
    return os.path.join(CACHE_DIR, f"{year}_{slug}.html")

def fetch_page(year, slug, href):
    """Fetch from web and cache. Returns HTML string or None on error."""
    url = href if href.startswith("http") else \
          f"https://contests.npcnewsonline.com/contests/{year}/{slug}"
    path = cache_path(year, slug)
    result = subprocess.run(
        ["curl", "-s", "--compressed", "-A", UA, url],
        capture_output=True, timeout=30
    )
    if result.returncode != 0 or not result.stdout:
        return None
    html = result.stdout.decode("utf-8", errors="replace")
    if "<html" not in html.lower():
        return None
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return html

def get_html(year, slug, href):
    """Return cached HTML or fetch it. Returns (html, was_cached)."""
    path = cache_path(year, slug)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(), True
    html = fetch_page(year, slug, href)
    return html, False

# ── HTML parser: extract first #1 placer per non-excluded division ────────────
class SampleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = None          # (division_name, athlete_name)
        self._cur_div  = None       # current division title
        self._in_h2    = False
        self._h2_class = False
        self._h2_buf   = []
        self._in_a     = False
        self._a_person = False
        self._a_buf    = []
        self._span_buf = []
        self._in_span  = False
        self._span_depth = 0

    def handle_starttag(self, tag, attrs):
        if self.result:
            return
        ad = dict(attrs)
        if tag == "h2" and "division-title" in ad.get("class", ""):
            self._in_h2 = True
            self._h2_buf = []
        elif tag == "a" and ad.get("data-person") == "yes":
            parent = ad.get("data-parent", "")
            if "overall-winner" in parent:
                return          # skip overall winner entries
            self._in_a = True
            self._a_person = True
            self._a_buf = []
            self._span_buf = []
            self._in_span = False
        elif tag == "span" and self._in_a:
            self._in_span = True
            self._span_depth += 1

    def handle_endtag(self, tag):
        if self.result:
            return
        if tag == "h2" and self._in_h2:
            self._in_h2 = False
            title = "".join(self._h2_buf).strip()
            low = title.lower()
            if any(w in low for w in SKIP_DIV_WORDS):
                self._cur_div = None
            else:
                self._cur_div = title
        elif tag == "span" and self._in_a:
            self._span_depth -= 1
            if self._span_depth < 0:
                self._span_depth = 0
            self._in_span = False
        elif tag == "a" and self._in_a:
            self._in_a = False
            self._a_person = False
            placing_text = "".join(self._span_buf).strip()
            if placing_text == "1" and self._cur_div:
                # full <a> text minus the span content → athlete name
                full = "".join(self._a_buf).strip()
                # remove the placing number from the start
                name = re.sub(r"^\s*1\s*", "", full).strip()
                if name:
                    self.result = (self._cur_div, name)

    def handle_data(self, data):
        if self.result:
            return
        if self._in_h2:
            self._h2_buf.append(data)
        if self._in_a:
            self._a_buf.append(data)
            if self._in_span:
                self._span_buf.append(data)

    def handle_charref(self, name):
        c = chr(int(name[1:], 16) if name.startswith("x") else int(name))
        self.handle_data(c)

def extract_sample(html):
    """Return (division_title, athlete_name) or None."""
    p = SampleParser()
    p.feed(html)
    return p.result

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    with open(SLUGS_FILE) as f:
        slugs = json.load(f)

    years = sorted(slugs.keys(), key=int)
    total = sum(len(v) for v in slugs.values())
    done  = sum(1 for v in slugs.values() for e in v if "sample" in e)
    print(f"Entries: {total}  Already enriched: {done}  Remaining: {total - done}")

    fetched = cached = errors = enriched = 0

    for year_str in years:
        entries = slugs[year_str]
        year    = int(year_str)
        changed = False

        for entry in entries:
            if "sample" in entry:
                continue

            slug = entry["slug"]
            href = entry.get("href", "")
            html, was_cached = get_html(year, slug, href)

            if not html:
                entry["sample"] = None
                errors += 1
                changed = True
                print(f"  ERROR {year} {slug}")
                continue

            if was_cached:
                cached += 1
            else:
                fetched += 1
                time.sleep(0.3)     # gentle rate limit for fresh fetches

            sample = extract_sample(html)
            if sample:
                entry["sample"] = {"division": sample[0], "athlete": sample[1]}
                enriched += 1
            else:
                entry["sample"] = None

            changed = True

        # Save after each year
        if changed:
            with open(SLUGS_FILE, "w") as f:
                json.dump(slugs, f, indent=2)

    print(f"\nDone. Enriched: {enriched}  Cached hits: {cached}  "
          f"Fetched: {fetched}  Errors: {errors}")

if __name__ == "__main__":
    main()
