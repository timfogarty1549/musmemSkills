#!/usr/bin/env python3
"""
prescreen_articles.py

Scans all XML article files in ~/workspace/node/musmem/data/mm_articles/*/
and identifies likely contest articles via keyword matching and event links.

Outputs a TSV manifest to /tmp/article_manifest.tsv with columns:
  filepath  has_event_link  headline  pub_date  match_reason

Run once at the start of a scraping campaign; reuse the manifest across sessions.
"""

import glob
import os
import re
import sys

ARTICLE_DIR = os.path.expanduser("~/workspace/node/musmem/data/mm_articles")
MANIFEST_PATH = "/tmp/article_manifest.tsv"

# Keywords that suggest a contest report (in h1/h2 or article body)
CONTEST_KEYWORDS = [
    r"\bcontest\b",
    r"\bchampionship\b",
    r"\bchampionships\b",
    r"\bnational[s]?\b",
    r"\bolympia\b",
    r"\bmr\.?\s*america\b",
    r"\bmr\.?\s*universe\b",
    r"\bmr\.?\s*world\b",
    r"\bmr\.?\s*olympia\b",
    r"\bmiss\s+olympia\b",
    r"\bms\.?\s*olympia\b",
    r"\bnabba\b",
    r"\bifbb\b",
    r"\bnpc\b",
    r"\baau\b",
    r"\bpro\s+show\b",
    r"\bgrand\s+prix\b",
    r"\bclassic\b",
    r"\bopen\s+(?:contest|championship)\b",
    r"\btitle\s+(?:won|goes|goes to|holder)\b",
    r"\bwinner[s]?\b",
    r"\bplaced?\s+(?:first|second|third|1st|2nd|3rd)\b",
    r"\bjudge[sd]\b",
    r"\bcompetitors?\b",
    r"\bcontestant[s]?\b",
    r"\bscore\s*card\b",
    r"\bresult[s]\b",
    r"\bphysique\s+(?:contest|competition|show)\b",
    r"\bbodybuilding\s+(?:contest|competition|championship)\b",
]

# Compiled once for efficiency
KEYWORD_RE = re.compile(
    "|".join(CONTEST_KEYWORDS),
    re.IGNORECASE,
)

EVENT_LINK_RE = re.compile(r'/event\?name=([^&"]+)(?:&(?:amp;)?year=(\d{4}))?')
H1_RE = re.compile(r'<h1[^>]*>(.*?)</h1>', re.IGNORECASE | re.DOTALL)
TITLE_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)
DATE_RE = re.compile(r'<date[^>]*>(.*?)</date>', re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r'<[^>]+>')


def strip_tags(text):
    return TAG_RE.sub(' ', text).strip()


def extract_headline(content):
    m = H1_RE.search(content)
    if m:
        return strip_tags(m.group(1)).replace('\n', ' ').strip()
    return ""


def find_event_links(content):
    """Return list of (contest_name, year) tuples from <a href="/event?..."> links."""
    results = []
    for m in EVENT_LINK_RE.finditer(content):
        name = m.group(1).replace('%20', ' ').replace('+', ' ')
        year = m.group(2) or ""
        results.append((name, year))
    return results


def prescreen(filepath):
    """
    Returns a dict with screening results, or None if the file cannot be read.
    """
    try:
        with open(filepath, encoding='utf-8', errors='replace') as fh:
            content = fh.read()
    except OSError as e:
        print(f"ERROR reading {filepath}: {e}", file=sys.stderr)
        return None

    title_m = TITLE_RE.search(content)
    date_m = DATE_RE.search(content)
    pub_date = strip_tags(date_m.group(1)) if date_m else ""
    mag_title = strip_tags(title_m.group(1)) if title_m else ""
    headline = extract_headline(content)

    event_links = find_event_links(content)
    has_event_link = len(event_links) > 0

    # Keyword match against the full text (fast — single compiled RE)
    plain_text = strip_tags(content)
    keyword_matches = KEYWORD_RE.findall(plain_text)
    unique_keywords = list({m.lower() for m in keyword_matches})

    # A file is a candidate if it has an event link OR enough keyword hits
    is_candidate = has_event_link or len(keyword_matches) >= 3

    return {
        "filepath": filepath,
        "mag_title": mag_title,
        "pub_date": pub_date,
        "headline": headline,
        "has_event_link": has_event_link,
        "event_links": event_links,
        "keyword_count": len(keyword_matches),
        "unique_keywords": unique_keywords[:8],  # cap for display
        "is_candidate": is_candidate,
    }


def main():
    pattern = os.path.join(ARTICLE_DIR, "*", "*.xml")
    all_files = sorted(glob.glob(pattern))

    if not all_files:
        print(f"No XML files found under {ARTICLE_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {len(all_files)} files...", file=sys.stderr)

    candidates = []
    skipped = []
    errors = []

    for filepath in all_files:
        result = prescreen(filepath)
        if result is None:
            errors.append(filepath)
            continue
        if result["is_candidate"]:
            candidates.append(result)
        else:
            skipped.append(result)

    # Write TSV manifest — candidates only, sorted by filepath
    with open(MANIFEST_PATH, 'w', encoding='utf-8') as out:
        out.write("filepath\thas_event_link\theadline\tpub_date\tkeyword_count\tmatch_reason\n")
        for r in candidates:
            reason_parts = []
            if r["has_event_link"]:
                links_str = "; ".join(f"{name} ({yr})" for name, yr in r["event_links"])
                reason_parts.append(f"event_link: {links_str}")
            if r["keyword_count"] >= 3:
                reason_parts.append(f"keywords({r['keyword_count']}): {', '.join(r['unique_keywords'])}")
            reason = " | ".join(reason_parts)
            headline = r["headline"].replace('\t', ' ')
            out.write(f"{r['filepath']}\t{r['has_event_link']}\t{headline}\t{r['pub_date']}\t{r['keyword_count']}\t{reason}\n")

    # Summary report
    print(f"\n=== Pre-screen Results ===")
    print(f"Total files scanned : {len(all_files)}")
    print(f"Candidate articles  : {len(candidates)}")
    print(f"Skipped (low signal): {len(skipped)}")
    print(f"Read errors         : {len(errors)}")
    print(f"\nManifest written to : {MANIFEST_PATH}")

    # Breakdown by subdir
    print(f"\nCandidates by magazine:")
    by_dir = {}
    for r in candidates:
        subdir = os.path.basename(os.path.dirname(r["filepath"]))
        by_dir.setdefault(subdir, 0)
        by_dir[subdir] += 1
    for subdir, count in sorted(by_dir.items()):
        print(f"  {subdir:8s}  {count}")

    # Files with event links
    linked = [r for r in candidates if r["has_event_link"]]
    print(f"\nFiles with MuscleMemory event links: {len(linked)}")
    for r in linked:
        for name, yr in r["event_links"]:
            print(f"  {os.path.basename(r['filepath'])}: {name} ({yr})")


if __name__ == "__main__":
    main()
