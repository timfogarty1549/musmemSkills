#!/usr/bin/env python3
"""
parse_contest.py — Extract bodybuilding contest results from a saved npcnewsonline.com HTML page.

NOTE: This script is specific to npcnewsonline.com. It depends on these site-specific
HTML patterns:
  - <h2 class="division-title"> — division section headers
  - data-slug="..." divs — class/sub-division identifiers
  - data-person="yes" anchors with <span> N </span> Name — competitor rows

If parsing a different source, the regex patterns will need to be adapted.

Usage:
    curl -s --compressed \
      -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
      "https://contests.npcnewsonline.com/contests/{year}/{slug}" \
      > /tmp/contest.html

    python3 parse_contest.py /tmp/contest.html

Prints all divisions and competitors to stdout in flat-file format.
Claude then filters by gender and writes the appropriate files.
"""

import html
import re
import sys

def parse_contest(html_path):
    with open(html_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Find all h2.division-title positions and labels
    h2_pattern = re.compile(r'<h2[^>]*division-title[^>]*>(.*?)</h2>', re.DOTALL)
    h2_matches = list(h2_pattern.finditer(content))

    if not h2_matches:
        print("No division titles found. Check that the HTML was saved correctly.", file=sys.stderr)
        sys.exit(1)

    for i, h2 in enumerate(h2_matches):
        division_title = re.sub(r'<[^>]+>', '', h2.group(1)).strip()

        # Section body: from end of this h2 to start of next h2 (or end of content)
        start = h2.end()
        end = h2_matches[i + 1].start() if i + 1 < len(h2_matches) else len(content)
        section_body = content[start:end]

        # Find all classes (sub-divisions) within this section via data-slug divs
        class_pattern = re.compile(r'data-slug="([^"]+)"', re.DOTALL)
        class_slugs = class_pattern.findall(section_body)

        # Find competitor blocks: data-person="yes" anchors containing <span> placing </span> Name
        competitor_pattern = re.compile(
            r'data-person="yes"[^>]*>\s*<span>\s*(\d+)\s*</span>\s*([^<]+)',
            re.DOTALL
        )
        competitors = competitor_pattern.findall(section_body)

        print(f"\n=== {division_title} ===")
        if class_slugs:
            print(f"(slugs: {', '.join(class_slugs)})")

        for placing, name in competitors:
            print(f"{placing} {html.unescape(name.strip())}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <saved_html_file>", file=sys.stderr)
        sys.exit(1)
    parse_contest(sys.argv[1])
