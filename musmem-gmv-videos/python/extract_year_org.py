"""
Extract (year, org) from each pending video's title and write an md table.
Org detection uses the DB's known orgs (from /api/org) plus federations
commonly seen on this channel that MuscleMemory does NOT track (WFF, UKBFF,
BNBF, ANB, EFBB, ICN, NPFC) so those are captured explicitly instead of
silently defaulting. If no org token is found in the title at all, default
to IFBB (most GMV titles with no org prefix are IFBB pro/amateur shows).

Usage: python3 extract_year_org.py
"""
import json
import os
import re
import urllib.request

from ensure_local_server import BASE_URL, ensure_server

SKILL_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PENDING_FILE = os.path.join(SKILL_DATA_DIR, "gmv_videos_pending.json")
TABLE_FILE = os.path.join(SKILL_DATA_DIR, "pending_year_org.md")

# Federations seen in GMV titles that MuscleMemory does not track as a
# distinct org (confirmed absent from /api/contests org list).
UNTRACKED_ORGS = {"WFF", "UKBFF", "BNBF", "ANB", "EFBB", "ICN", "NPFC"}

YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def fetch_db_orgs():
    with urllib.request.urlopen(f"{BASE_URL}/api/contests", timeout=10) as resp:
        data = json.load(resp)
    return {c.rsplit(" - ", 1)[1] for c in data["data"]["contests"] if " - " in c}


def _org_at(text, org):
    """True if `org` (or an org/org compound containing it) sits at the very
    start of `text`."""
    pattern = r"^\s*" + re.escape(org) + r"\b"
    return re.match(pattern, text) is not None


def find_org(title, known_orgs, year_match=None):
    """Find the org token, but ONLY if it sits immediately next to the year
    (right after it, or right before it as a fallback). An org-like word
    appearing elsewhere in the title usually describes something else (e.g.
    "NPC" in "Arnold Amateur NPC Women" names a division's eligibility, not
    the sanctioning body -- treating it as the org sends the search to the
    wrong org's contest list entirely, where the real answer can't exist).
    year_match is a re.Match for YEAR_RE against `title`; if not given it's
    located here.
    """
    if year_match is None:
        year_match = YEAR_RE.search(title)
    if not year_match:
        return None

    after = title[year_match.end():year_match.end() + 20].lstrip(" -:,")
    before = title[max(0, year_match.start() - 20):year_match.start()].rstrip(" -:,")

    # Longest tokens first so "NPC Worldwide" wins over "NPC", etc.
    for org in sorted(known_orgs, key=len, reverse=True):
        if _org_at(after, org):
            combo = re.match(r"^[/-]([A-Z]{2,10})\b", after[len(org):])
            if combo and combo.group(1) in known_orgs:
                return f"{org}/{combo.group(1)}"
            return org
        if before.endswith(org) and re.search(r"(^|[\s/-])" + re.escape(org) + r"$", before):
            combo = re.search(r"([A-Z]{2,10})[/-]$", before[:-len(org)])
            if combo and combo.group(1) in known_orgs and combo.group(1) != org:
                return f"{combo.group(1)}/{org}"
            return org
    return None


def main():
    if not ensure_server():
        print("ERROR: could not reach or start the local musmem server. Aborting.")
        return

    if not os.path.exists(PENDING_FILE):
        print(f"No pending file at {PENDING_FILE} -- run find_pending.py first.")
        return
    with open(PENDING_FILE, encoding="utf-8") as f:
        pending = json.load(f)

    db_orgs = fetch_db_orgs()
    known_orgs = db_orgs | UNTRACKED_ORGS

    rows = []
    for video in pending:
        title = video["title"]
        year_match = YEAR_RE.search(title)
        year = year_match.group(0) if year_match else ""
        org = find_org(title, known_orgs, year_match) or "IFBB"
        rows.append((video["id"], year, org, title))

    os.makedirs(SKILL_DATA_DIR, exist_ok=True)
    with open(TABLE_FILE, "w", encoding="utf-8") as f:
        f.write("| YouTube ID | Year | Org | Title |\n")
        f.write("|---|---|---|---|\n")
        for vid, year, org, title in rows:
            title_escaped = title.replace("|", "\\|")
            f.write(f"| {vid} | {year} | {org} | {title_escaped} |\n")

    no_year = sum(1 for _, y, _, _ in rows if not y)
    print(f"Wrote {len(rows)} rows to {TABLE_FILE}")
    print(f"  no year found: {no_year}")
    from collections import Counter
    org_counts = Counter(o for _, _, o, _ in rows)
    print("  org breakdown:")
    for org, cnt in org_counts.most_common():
        tracked = "tracked" if org.split("/")[0] in db_orgs or org in db_orgs else "NOT TRACKED"
        print(f"    {org:15s} {cnt:4d}  ({tracked})")


if __name__ == "__main__":
    main()
