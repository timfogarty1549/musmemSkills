#!/usr/bin/env python3
"""
Phase 1: Gap Analysis
Fetches npcnewsonline IFBB listing pages for 2012-2026, compares to HTML tracker.
Outputs: gap report + /tmp/npcnol_slugs.json
"""

import json
import os
import re
import subprocess
from html.parser import HTMLParser

# ── Config ────────────────────────────────────────────────────────────────────
HTML_FILE   = os.path.expanduser(
    "~/workspace/musmem/working-docs/ifbb-pro-contests-years-since-2012.html")
MAPPING_FILE = os.path.expanduser(
    "~/workspace/skills/musmemSkills/docs/contest-name-mapping.md")
SLUGS_OUT   = os.path.expanduser(
    "~/workspace/skills/musmemSkills/musmem-missing/data/npcnol_slugs.json")
YEARS       = list(range(2012, 2027))
UA          = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
               "AppleWebKit/537.36 (KHTML, like Gecko) "
               "Chrome/120.0.0.0 Safari/537.36")
SKIP_WORDS  = ["amateur", "pro qualifier"]

# ── HTML tracker parser ───────────────────────────────────────────────────────
class TrackerParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.contests = {}   # {name: {year: divisions_str or None}}
        self._in_tbody = False
        self._in_row = False
        self._cells = []
        self._cell_text = []
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == 'tbody':
            self._in_tbody = True
        elif tag == 'tr' and self._in_tbody:
            self._in_row = True
            self._cells = []
        elif tag in ('td', 'th') and self._in_row:
            self._in_cell = True
            self._cell_text = []

    def handle_endtag(self, tag):
        if tag == 'tbody':
            self._in_tbody = False
        elif tag == 'tr' and self._in_row:
            self._in_row = False
            if self._cells and self._cells[0]:
                name = self._cells[0]
                years_data = {}
                for i, div_text in enumerate(self._cells[1:]):
                    year = 2012 + i
                    years_data[year] = div_text if div_text.strip() else None
                self.contests[name] = years_data
        elif tag in ('td', 'th') and self._in_cell:
            self._in_cell = False
            text = ''.join(self._cell_text).strip()
            self._cells.append(text)

    def handle_data(self, data):
        if self._in_cell:
            self._cell_text.append(data)

    def handle_entityref(self, name):
        import html as h
        if self._in_cell:
            self._cell_text.append(h.unescape('&' + name + ';'))

    def handle_charref(self, name):
        if self._in_cell:
            if name.startswith('x'):
                c = chr(int(name[1:], 16))
            else:
                c = chr(int(name))
            self._cell_text.append(c)

def parse_html_tracker(path):
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()
    p = TrackerParser()
    p.feed(html)
    return p.contests

# ── Mapping loader ────────────────────────────────────────────────────────────
def load_mapping(path):
    """Return (alias_dict, ignore_set).
    alias_dict: {npcnol_name: musmem_name} for entries with a non-empty musmem name.
    ignore_set: set of npcnol_names whose type column is 'ignore'.
    """
    alias = {}
    ignore = set()
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('|'):
                continue
            # Split on | and strip each cell — preserve empty cells so column
            # positions stay fixed even when musclememory name is blank.
            cols = [c.strip() for c in line.split('|')]
            # cols[0] is empty (before first |), cols[-1] is empty (after last |)
            # actual columns are cols[1], cols[2], cols[3]
            if len(cols) < 3:
                continue
            npcnol = cols[1]
            musmem = cols[2] if len(cols) > 2 else ''
            typ    = cols[3] if len(cols) > 3 else ''
            if not npcnol or npcnol in ('npcnewsonline name', '---'):
                continue
            if typ == 'ignore':
                ignore.add(npcnol)
            elif musmem and musmem != npcnol:
                alias[npcnol] = musmem
    return alias, ignore

# ── Listing page fetcher ──────────────────────────────────────────────────────
class ListingParser(HTMLParser):
    def __init__(self, year):
        super().__init__()
        self.year = year
        self.contests = []   # [(raw_name, slug)]
        self._href = None
        self._capture = False
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            ad = dict(attrs)
            href = ad.get('href', '')
            # Match individual contest pages for this year
            pattern = f'/contests/{self.year}/ifbb_'
            if pattern in href:
                self._href = href
                self._capture = True
                self._text = []

    def handle_endtag(self, tag):
        if tag == 'a' and self._capture:
            raw = ''.join(self._text).strip()
            if raw and self._href:
                slug = self._href.rstrip('/').split('/')[-1]
                self.contests.append((raw, slug, self._href))
            self._capture = False
            self._href = None
            self._text = []

    def handle_data(self, data):
        if self._capture:
            self._text.append(data)

    def handle_entityref(self, name):
        import html as h
        if self._capture:
            self._text.append(h.unescape('&' + name + ';'))

    def handle_charref(self, name):
        if self._capture:
            if name.startswith('x'):
                c = chr(int(name[1:], 16))
            else:
                c = chr(int(name))
            self._text.append(c)

def normalize_name(raw, alias, ignore):
    """Strip 'IFBB ' prefix, append ' - IFBB', apply alias overrides.
    Returns None if the stripped name is in the ignore set.
    """
    name = raw
    if name.upper().startswith("IFBB "):
        name = name[5:]
    name = ' '.join(name.split()) + " - IFBB"  # collapse double spaces too
    if name in ignore:
        return None
    return alias.get(name, name)

def should_skip(raw_name):
    low = raw_name.lower()
    return any(w in low for w in SKIP_WORDS)

def fetch_listing(year):
    url = f"https://contests.npcnewsonline.com/contests/{year}/ifbb"
    result = subprocess.run(
        ["curl", "-s", "--compressed", "-A", UA, url],
        capture_output=True
    )
    if result.returncode != 0:
        print(f"  ERROR fetching {year}: {result.stderr.decode()[:200]}")
        return []
    html = result.stdout.decode('utf-8', errors='replace')
    p = ListingParser(year)
    p.feed(html)
    # Deduplicate by slug (some pages list duplicates)
    seen = set()
    unique = []
    for raw, slug, href in p.contests:
        if slug not in seen:
            seen.add(slug)
            unique.append((raw, slug, href))
    return unique

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("Loading HTML tracker...")
    contests_in_html = parse_html_tracker(HTML_FILE)
    all_html_names = set(contests_in_html.keys())
    print(f"  {len(all_html_names)} contests in HTML tracker")

    print("Loading contest name mapping...")
    alias, ignore = load_mapping(MAPPING_FILE)
    print(f"  {len(alias)} alias entries, {len(ignore)} ignored")

    # Fetch all listing pages
    npcnol = {}   # {year: [{normalized, raw, slug, href}, ...]}
    print("\nFetching npcnewsonline listing pages...")
    for year in YEARS:
        raw_list = fetch_listing(year)
        entries = []
        skipped = 0
        for raw, slug, href in raw_list:
            if should_skip(raw):
                skipped += 1
                continue
            norm = normalize_name(raw, alias, ignore)
            if norm is None:  # type=ignore in mapping
                skipped += 1
                continue
            entries.append({
                "normalized": norm,
                "raw": raw,
                "slug": slug,
                "href": href
            })
        npcnol[year] = entries
        print(f"  {year}: {len(entries)} IFBB contests ({skipped} skipped)")

    # Save slug map for Phase 4
    with open(SLUGS_OUT, 'w') as f:
        json.dump(npcnol, f, indent=2)
    print(f"\nSlug map saved to {SLUGS_OUT}")

    # Gap analysis
    gaps = []   # [{year, raw, normalized, slug}]
    no_match_names = set()

    for year in YEARS:
        for entry in npcnol[year]:
            norm = entry["normalized"]
            if norm not in all_html_names:
                gaps.append({
                    "year": year,
                    "raw": entry["raw"],
                    "normalized": norm,
                    "slug": entry["slug"]
                })
                no_match_names.add(norm)

    # Report
    print("\n" + "="*70)
    print("CONTESTS ON NPCNEWSONLINE NOT FOUND IN HTML TRACKER")
    print("="*70)

    by_year = {}
    for g in gaps:
        by_year.setdefault(g["year"], []).append(g)

    for year in YEARS:
        items = by_year.get(year, [])
        if items:
            print(f"\n{year}:")
            for g in items:
                print(f'  {g["raw"]!r}')
                print(f'    → normalized: {g["normalized"]!r}  (slug: {g["slug"]})')

    print("\n" + "="*70)
    print(f"TOTAL: {len(gaps)} contest-years unmatched across {len(no_match_names)} distinct names")
    print("="*70)
    print("\nDISTINCT UNMATCHED NAMES (for mapping review):")
    for name in sorted(no_match_names):
        print(f"  {name}")

    # Also check HTML contests not on npcnewsonline (for reference)
    npcnol_names_by_year = {}
    for year in YEARS:
        npcnol_names_by_year[year] = {e["normalized"] for e in npcnol[year]}

    html_not_on_npcnol = []
    for name, year_data in contests_in_html.items():
        for year, divs in year_data.items():
            if divs:  # has data in HTML
                if year in npcnol_names_by_year and name not in npcnol_names_by_year[year]:
                    html_not_on_npcnol.append((name, year))

    if html_not_on_npcnol:
        print(f"\n[Reference] {len(html_not_on_npcnol)} HTML cells with data where contest not found on npcnewsonline that year:")
        for name, year in sorted(html_not_on_npcnol)[:30]:
            print(f"  {year}: {name}")
        if len(html_not_on_npcnol) > 30:
            print(f"  ... and {len(html_not_on_npcnol)-30} more")

if __name__ == "__main__":
    main()
