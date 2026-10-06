#!/usr/bin/env python3
"""IFBB contest-report coverage audit vs MuscleMemory.

Scrapes https://ifbb.com/contest-report-{year}/ for every year in range,
compares the contest names found there against the local MuscleMemory
instance (musclememory.net API, self-hosted on localhost:3000), and writes
a markdown coverage table.

Recurring regional/world championships get renamed on ifbb.com almost every
year (ordinals, federation acronyms like "AFBF", "& Annual Congress", etc.),
so this script clusters those by *region* (continent/direction words) rather
than literal text, then rolls all known name variants into one row per
MuscleMemory canonical contest. One-off branded events (Arnold Classic X,
Diamond Cup Y, Mr Universe Z...) are matched by strict text-similarity
instead, since two different countries' Diamond Cups are genuinely
different contests.

"Fit Model", "Children", and "Fitness Challenge" sub-events are never
tracked by MuscleMemory and are excluded from matching, even when they
appear as one part of a compound "X Championships & Y Fit Model Cup" title
- the valid part still matches on its own. "Cup" is treated as a different
event format from "Championships" and the two are never matched to each
other.

Usage:
    python3 ifbb_coverage_report.py
    python3 ifbb_coverage_report.py --start-year 2013 --end-year 2026
    python3 ifbb_coverage_report.py --out ~/Desktop/ifbb-amateur.md

Run this every few months to refresh the report; each run re-fetches both
ifbb.com and MuscleMemory live, so no manual cache maintenance is needed.
"""
import argparse
import difflib
import gzip
import html
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime

BROWSER_UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
              'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
BOT_UA = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'

MM_BASE = 'http://localhost:3000'
DEFAULT_OUT = '/Users/timfogarty/workspace/skills/musmemSkills/ifbb-amateur.md'


# ============================================================================
# Fetching
# ============================================================================

def fetch_url(url, ua=BROWSER_UA, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': ua, 'Accept-Encoding': 'gzip, deflate'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        enc = resp.headers.get('Content-Encoding', '')
    return (gzip.decompress(raw) if enc == 'gzip' else raw).decode('utf-8', errors='replace')


def fetch_ifbb_year_page(year):
    """Fetch ifbb.com's contest-report page for a year. Returns None if the
    page doesn't exist (e.g. 2017, which ifbb.com never published)."""
    url = f'https://ifbb.com/contest-report-{year}/'
    try:
        return fetch_url(url, ua=BROWSER_UA)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            try:
                return fetch_url(url, ua=BOT_UA)
            except urllib.error.HTTPError:
                return None
        raise


def fetch_mm_contests(year):
    """Fetch all MuscleMemory contest titles for a year, filtered to org=IFBB."""
    url = f'{MM_BASE}/api/contests/{year}'
    try:
        page = fetch_url(url, ua=BROWSER_UA, timeout=15)
    except Exception as e:
        print(f'  WARNING: could not fetch MuscleMemory data for {year}: {e}', file=sys.stderr)
        return []
    import json
    data = json.loads(page)
    contests = data.get('data', {}).get('contests', [])
    return [c[:-len(' - IFBB')] for c in contests if c.endswith(' - IFBB')]


# ============================================================================
# Parsing ifbb.com's flip-box contest listing
# ============================================================================

FLIPBOX_RE = re.compile(
    r'elementor-flip-box__front.*?elementor-flip-box__layer__title">\s*(.*?)\s*</h3>'
    r'.*?elementor-flip-box__back.*?elementor-flip-box__layer__inner">(.*?)</div>\s*</div>\s*</div>\s*</div>',
    re.DOTALL
)
DOWNLOAD_RE = re.compile(r'href="([^"]+\.pdf)"', re.IGNORECASE)


def parse_ifbb_page(page_html):
    """Return list of {"title": str, "has_pdf": bool} for one year's page."""
    contests = []
    for m in FLIPBOX_RE.finditer(page_html):
        title_raw, back_raw = m.group(1), m.group(2)
        title = html.unescape(re.sub(r'<[^>]+>', '', title_raw)).strip()
        title = re.sub(r'\s+', ' ', title)
        if not title:
            continue
        has_pdf = bool(DOWNLOAD_RE.search(back_raw))
        contests.append({'title': title, 'has_pdf': has_pdf})
    return contests


# ============================================================================
# Name normalization
# ============================================================================

ORDINAL_RE = re.compile(r'^\d+(st|nd|rd|th)\s+', re.IGNORECASE)
YEAR_PREFIX_RE = re.compile(r'^(19|20)\d{2}\s+')
NONALNUM_RE = re.compile(r'[^a-z0-9 ]+')

TYPO_FIXES = [
    (r'\bmeditteranean\b', 'mediterranean'),
    (r'\bchallengue\b', 'challenge'),
    (r'\bchampionshp\b', 'championships'),
    (r'\bidiamond\b', 'diamond'),
    (r'\bfitnessresult\b', 'fitness result'),
    (r'\bhercules\b', 'herkules'),
    (r'\bbrazils\b', 'brazil'),
    (r'\beastern\b', 'east'),
    (r'\bwestern\b', 'west'),
    (r'\bnorthern\b', 'north'),
    (r'\bsouthern\b', 'south'),
    # "America" (no trailing n) must alias to "american" so it's
    # recognized as the same continent word - otherwise a title like
    # "Arnold Amateur South America" has no detectable continent marker
    # and slips past the continent-conflict veto entirely
    (r'\bamerica\b', 'american'),
]


def normalize(title):
    t = title.lower()
    t = t.replace('&', ' and ')
    t = t.replace('’', "'").replace('´', "'")
    t = ORDINAL_RE.sub('', t)
    t = YEAR_PREFIX_RE.sub('', t)
    t = t.replace('ifbb', ' ')
    t = NONALNUM_RE.sub(' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    for pat, repl in TYPO_FIXES:
        t = re.sub(pat, repl, t)
    t = re.sub(r'\band annual congress\b', '', t).strip()
    t = re.sub(r'\bafbf\b', '', t).strip()
    t = re.sub(r'\bcacbbff\b', '', t).strip()
    t = re.sub(r'\s+', ' ', t).strip()
    return t


STOPWORDS = {
    'the', 'of', 'and', 'cup', 'world', 'grand', 'prix',
    'championships', 'championship', 'international', 'open',
    'ifbb', 'for', 'all', 'national', 'federations', 'in',
    'annual', 'congress',
    # frequently-recurring franchise/brand words - carry no
    # location-distinguishing signal on their own (e.g. "Arnold Classic
    # Columbus" vs "Arnold Classic Asia" both share these two words but
    # are different events)
    'arnold', 'classic', 'olympia', 'mister', 'muscle', 'show',
    'beach', 'diamond',
    # "amateur" is a near-universal qualifier tier, not a distinguishing
    # word - "Arnold Amateur" and "Mr. Olympia Amateur England" share only
    # this word and are otherwise unrelated events
    'amateur',
}

# Distinct franchise/brand identifiers - "Arnold Amateur South America" and
# a plain "South American Championship" share only generic continent words
# and are different events; "Mr. Olympia Amateur X" is a different
# franchise from "Arnold X" even when both are held in the same country.
# These are stripped from STOPWORDS' jaccard scoring (so e.g. "Arnold
# Classic Brazil" vs "Arnold Classic Brasil" is judged on the location
# alone) but must match exactly between the two sides, or not appear on
# either side, before that scoring is even attempted.
BRAND_IDENTITY_WORDS = {'arnold', 'olympia', 'diamond', 'universe', 'universo'}

DIRECTIONS = {'north', 'south', 'east', 'west', 'central'}
CONTINENTS = {'asian', 'american', 'african', 'european', 'oceania'}
REGION_KEY_WORDS = DIRECTIONS | CONTINENTS | {
    'world', 'balkan', 'mediterranean', 'nordic', 'baltic', 'arab',
    'caribbean', 'latin', 'pacific',
}

# "Congress" removed as a marker on its own - a title that's only about a
# congress (administrative meeting), not a competition, shouldn't count.
CHAMPIONSHIP_MARKER_RE = re.compile(r'championship|tournament')
LEADING_ORDINAL_RE = re.compile(r'^\d+(st|nd|rd|th)\s+', re.IGNORECASE)

# Categories MuscleMemory does not track as a contest identity - "Fit Model"
# and "Children" events never match anything; "Fitness Challenge" likewise.
EXCLUDE_TERMS_RE = re.compile(r'fit model|fitmodel|childre?n|fitness challenge')

# Multi-sport games/expos/festivals shouldn't be swept into the championship
# family just because they share a region word and an ordinal number
# (e.g. "4th Asian Beach Games" is not the "Asian Championships").
ALTERNATE_EVENT_WORDS = {'games', 'expo', 'festival'}

SEGMENT_SPLIT_RE = re.compile(r'\s*&\s*|\s*/\s*')


def significant_tokens(norm):
    return set(w for w in norm.split() if w not in STOPWORDS and len(w) > 2)


def region_sig(norm):
    return frozenset(set(norm.split()) & REGION_KEY_WORDS)


def is_cup_format(norm):
    """'Cup' is a different event format from 'Championships' - a title
    whose only format word is Cup should never match a Championships entry."""
    tokens = norm.split()
    return 'cup' in tokens and not CHAMPIONSHIP_MARKER_RE.search(norm)


def is_alt_event_format(norm):
    """'Games'/'Expo'/'Festival' (multi-sport games, trade expos...) are a
    different event format from 'Championships' - "5th Asian Beach Games"
    should never match "Asian Amateur Championships" just because both
    mention "Asian"."""
    tokens = set(norm.split())
    return bool(tokens & ALTERNATE_EVENT_WORDS) and not CHAMPIONSHIP_MARKER_RE.search(norm)


def is_pro_arnold_classic(norm):
    """"Arnold Classic X" is MuscleMemory's IFBB Pro League canonical name,
    distinct from "Arnold Amateur X". ifbb.com's contest-report page only
    covers the amateur federation (confirmed by opening the actual PDF
    behind ifbb.com's "Arnold Classic Brasil" 2013 link, which is titled
    "Arnold Amateur" inside) - the amateur IFBB no longer talks to the Pro
    League orgs, so "Arnold Classic X" must never be a valid match target
    here, regardless of what ifbb.com's own link text says."""
    tokens = set(norm.split())
    return 'arnold' in tokens and 'classic' in tokens


def split_segments(raw_title):
    return [s.strip() for s in SEGMENT_SPLIT_RE.split(raw_title) if s.strip()]


def find_valid_champ_segment(raw_title):
    """Return the normalized text of the first segment of raw_title that is
    a real, MM-trackable regional/world championship (not Fit Model,
    Children, Fitness Challenge, or a bare Cup), or None. Compound titles
    like "World Junior Championships & Women Fit Model World Cup" match on
    their valid segment even though another segment is excluded."""
    segments = split_segments(raw_title) or [raw_title]
    full_has_ordinal = bool(LEADING_ORDINAL_RE.match(raw_title.strip().lower()))
    for i, seg in enumerate(segments):
        norm_seg = normalize(seg)
        if not norm_seg:
            continue
        if EXCLUDE_TERMS_RE.search(norm_seg):
            continue
        if is_cup_format(norm_seg):
            continue
        has_marker = bool(CHAMPIONSHIP_MARKER_RE.search(norm_seg))
        tokens = set(norm_seg.split())
        if not has_marker and (tokens & ALTERNATE_EVENT_WORDS):
            continue
        has_ordinal = has_marker or (i == 0 and full_has_ordinal)
        if has_ordinal and region_sig(norm_seg):
            return norm_seg
    return None


def region_compatible(a, b):
    if not a or not b:
        return False
    if not (a & b):
        return False
    a_dirs, b_dirs = a & DIRECTIONS, b & DIRECTIONS
    if a_dirs and b_dirs and not (a_dirs & b_dirs):
        return False
    a_cont, b_cont = a & CONTINENTS, b & CONTINENTS
    if a_cont and b_cont and not (a_cont & b_cont):
        return False
    return True


# ============================================================================
# Matching
# ============================================================================

def rank_region_candidates(ifbb_sig, mm_entries):
    """mm_entries: list of {"norm":..., "title":...} for one year."""
    candidates = []
    for e in mm_entries:
        # ifbb.com's contest-report page is elite/amateur only - IFBB Pro
        # League city shows ("X Pro", "X Pro Championships"...) are never
        # a valid match, even if the region words happen to line up
        if 'pro' in e['norm'].split():
            continue
        if EXCLUDE_TERMS_RE.search(e['norm']) or is_cup_format(e['norm']):
            continue
        # A generic continental/world championship should never resolve to
        # a branded show like "Arnold Amateur South America" just because
        # both happen to mention the same continent
        if set(e['norm'].split()) & BRAND_IDENTITY_WORDS:
            continue
        cand_sig = region_sig(e['norm'])
        if not region_compatible(ifbb_sig, cand_sig):
            continue
        sym_diff = len(ifbb_sig ^ cand_sig)
        has_amateur = 'amateur' in e['norm'].split()
        candidates.append((sym_diff, 0 if has_amateur else 1, e['title']))
    candidates.sort()
    if not candidates:
        return None
    return candidates[0][2], candidates[0][0]  # title, sym_diff


def match_brand(norm, mm_entries):
    if not mm_entries:
        return None
    if EXCLUDE_TERMS_RE.search(norm):
        return None
    ifbb_is_cup = is_cup_format(norm)
    ifbb_is_alt = is_alt_event_format(norm)
    ifbb_has_champ = bool(CHAMPIONSHIP_MARKER_RE.search(norm))
    ifbb_brand = set(norm.split()) & BRAND_IDENTITY_WORDS
    sig = significant_tokens(norm)
    sig_dirs = sig & DIRECTIONS
    sig_cont = sig & CONTINENTS
    best, best_score = None, 0.0
    for e in mm_entries:
        if EXCLUDE_TERMS_RE.search(e['norm']):
            continue
        # ifbb.com's contest-report page is elite/amateur only - IFBB Pro
        # League city shows ("Miami Pro", "Dubai Pro"...) are never a valid
        # match here either, same reasoning as the region-family matcher
        if 'pro' in e['norm'].split():
            continue
        # "Arnold Classic X" is the Pro League show, not the amateur one -
        # never a valid match even when ifbb.com's own link text says
        # "Classic" (it doesn't - the PDF behind it says "Amateur")
        if is_pro_arnold_classic(e['norm']):
            continue
        # A different (or missing) franchise identifier is a hard mismatch -
        # "Arnold Amateur South America" is not "South American Championship"
        cand_brand = set(e['norm'].split()) & BRAND_IDENTITY_WORDS
        if ifbb_brand != cand_brand:
            ratio_check = difflib.SequenceMatcher(None, norm, e['norm']).ratio()
            if ratio_check < 0.95:
                continue
        # Cup is a different event format from Championships - never match
        # a bare "X Cup" to an "X Championships" (or vice versa)
        cand_is_cup = is_cup_format(e['norm'])
        cand_has_champ = bool(CHAMPIONSHIP_MARKER_RE.search(e['norm']))
        if ifbb_is_cup and cand_has_champ and not cand_is_cup:
            continue
        if cand_is_cup and ifbb_has_champ and not ifbb_is_cup:
            continue
        # Same idea for "Games"/"Expo"/"Festival" vs "Championships"
        cand_is_alt = is_alt_event_format(e['norm'])
        if ifbb_is_alt and cand_has_champ and not cand_is_alt:
            continue
        if cand_is_alt and ifbb_has_champ and not ifbb_is_alt:
            continue
        ratio = difflib.SequenceMatcher(None, norm, e['norm']).ratio()
        e_sig = significant_tokens(e['norm'])
        e_dirs = e_sig & DIRECTIONS
        e_cont = e_sig & CONTINENTS
        if sig_dirs and e_dirs and not (sig_dirs & e_dirs) and ratio < 0.95:
            continue
        if sig_cont and e_cont and not (sig_cont & e_cont) and ratio < 0.95:
            continue
        inter = sig & e_sig
        if not inter and ratio < 0.95:
            continue
        union = sig | e_sig
        jaccard = len(inter) / len(union) if union else 0.0
        if jaccard < 0.5 and ratio < 0.8:
            continue
        score = max(ratio, jaccard)
        if score > best_score:
            best_score, best = score, e
    if best is not None and best_score >= 0.5:
        return best['title'], best_score
    return None


STATUS_PRIORITY = {'check': 3, 'maybe': 2, 'x': 1, 'listed_no_pdf': 0}


def build_rows(years):
    print('Fetching ifbb.com contest-report pages...')
    ifbb_by_year = {}
    for year in years:
        page = fetch_ifbb_year_page(year)
        if page is None:
            print(f'  {year}: no report page on ifbb.com (skipped)')
            ifbb_by_year[year] = {}
            continue
        contests = parse_ifbb_page(page)
        seen = {}
        for c in contests:
            norm = normalize(c['title'])
            if not norm:
                continue
            if norm not in seen:
                seen[norm] = {'title': c['title'], 'has_pdf': c['has_pdf']}
            else:
                seen[norm]['has_pdf'] = seen[norm]['has_pdf'] or c['has_pdf']
        ifbb_by_year[year] = seen
        print(f'  {year}: {len(seen)} contests, {sum(1 for v in seen.values() if v["has_pdf"])} with a PDF report')

    print('Fetching MuscleMemory (org=IFBB) contest lists...')
    mm_by_year = {}
    for year in years:
        names = fetch_mm_contests(year)
        mm_by_year[year] = [{'norm': normalize(n), 'title': n} for n in names]
        print(f'  {year}: {len(names)} IFBB-org contests in MuscleMemory')

    # ---- Assign each (year, ifbb entry) to a region- or brand-family
    # cluster identity, then resolve it against MuscleMemory individually.
    # Rows are grouped by the *actual* MM title matched in each year, not
    # by cluster identity - MuscleMemory sometimes renames its own
    # canonical title for the same recurring contest over time (e.g.
    # "Central American and Caribbean Championships" through 2023 became
    # "Central American Amateur Championships" from 2025), and collapsing
    # those years under one cluster's "most common" label would hide the
    # rename instead of surfacing it as its own row.
    entries = []
    for year in years:
        for norm, info in ifbb_by_year[year].items():
            champ_seg = find_valid_champ_segment(info['title'])
            key = ('region', region_sig(champ_seg)) if champ_seg else ('brand', norm)
            entries.append({'year': year, 'title': info['title'], 'has_pdf': info['has_pdf'], 'key': key})

    for e in entries:
        if not e['has_pdf']:
            e['status'], e['mm_title'] = 'listed_no_pdf', None
            continue
        if e['key'][0] == 'region':
            result = rank_region_candidates(e['key'][1], mm_by_year.get(e['year'], []))
            if result:
                mm_title, sym_diff = result
                e['status'] = 'check' if sym_diff == 0 else 'maybe'
                e['mm_title'] = mm_title
            else:
                e['status'], e['mm_title'] = 'x', None
        else:
            m = match_brand(e['key'][1], mm_by_year.get(e['year'], []))
            if m:
                title, score = m
                e['status'] = 'check' if score >= 0.7 else 'maybe'
                e['mm_title'] = title
            else:
                e['status'], e['mm_title'] = 'x', None

    # A cluster's "dominant" MM title (its most frequent match, if any) is
    # where x/listed_no_pdf years for that same cluster get attached, so a
    # single missing/undated year doesn't spawn its own orphan row.
    cluster_entries = {}
    for e in entries:
        cluster_entries.setdefault(e['key'], []).append(e)
    dominant_title = {}
    for key, elist in cluster_entries.items():
        counts = Counter(e['mm_title'] for e in elist if e['mm_title'])
        dominant_title[key] = counts.most_common(1)[0][0] if counts else None

    row_map = {}
    for e in entries:
        if e['mm_title']:
            row_key = ('title', e['mm_title'])
        elif dominant_title[e['key']]:
            row_key = ('title', dominant_title[e['key']])
        else:
            row_key = ('cluster', e['key'])
        row = row_map.setdefault(row_key, {
            'canonical': e['mm_title'] or dominant_title[e['key']],
            'variants': [],
            'status': {},
        })
        if e['title'] not in row['variants']:
            row['variants'].append(e['title'])
        prev = row['status'].get(e['year'])
        if prev is None or STATUS_PRIORITY[e['status']] > STATUS_PRIORITY[prev]:
            row['status'][e['year']] = e['status']

    return list(row_map.values())


# ============================================================================
# Markdown rendering
# ============================================================================

SYMBOLS = {'check': '✅', 'maybe': '❓', 'x': '❌', 'listed_no_pdf': '➖', None: ''}
NO_MATCH = '*(no MuscleMemory match)*'
FONT = 'font-size:0.75em'


def render_markdown(rows, years):
    def sort_key(r):
        canon = r['canonical'] or '￿' + (r['variants'][0] if r['variants'] else '')
        return YEAR_PREFIX_RE.sub('', canon).lower()

    rows_sorted = sorted(rows, key=sort_key)

    lines = []
    lines.append('# Amateur IFBB Contest Report Coverage vs MuscleMemory')
    lines.append('')
    lines.append(
        f'Source: [ifbb.com/contest-report-{{year}}](https://ifbb.com/contest-report-{years[-1]}/) '
        f'({years[0]}–{years[-1]}). Compared against the local MuscleMemory instance '
        f'(`localhost:3000`), org = IFBB. Generated {datetime.now().strftime("%Y-%m-%d")}.'
    )
    lines.append('')
    lines.append(
        'Rows are grouped by **canonical MuscleMemory contest name** — recurring regional/world '
        'championships get renamed on ifbb.com almost every year (ordinals, federation acronyms, '
        '"& Annual Congress", etc.), so all known name variants for a contest are listed in the '
        'second column and rolled up into one row. "Fit Model", "Children", and "Fitness Challenge" '
        'sub-events are excluded from matching (MuscleMemory does not track them), and "Cup" is '
        'treated as a different event format from "Championships".'
    )
    lines.append('')
    lines.append('**Legend**')
    lines.append('')
    lines.append('| Symbol | Meaning |')
    lines.append('|---|---|')
    lines.append(f"| {SYMBOLS['check']} | ifbb.com has a contest report (PDF) **and** MuscleMemory has matching data |")
    lines.append(f"| {SYMBOLS['maybe']} | ifbb.com has a contest report; matched to the *closest available* MuscleMemory contest, but not an exact regional match — verify manually |")
    lines.append(f"| {SYMBOLS['x']} | ifbb.com has a contest report but **no matching data found** in MuscleMemory |")
    lines.append(f"| {SYMBOLS['listed_no_pdf']} | Contest listed on ifbb.com for that year but **no PDF report** was published |")
    lines.append('| _(blank)_ | Contest not listed on ifbb.com for that year |')
    lines.append('')

    header = '| MuscleMemory Canonical Name | ifbb.com Name Variants |' + ''.join(f' {y} |' for y in years)
    sep = '|---|---|' + '---|' * len(years)
    lines.append(header)
    lines.append(sep)

    for r in rows_sorted:
        canon = r['canonical'] or NO_MATCH
        canon = YEAR_PREFIX_RE.sub('', canon)
        canon_cell = f'<span style="{FONT}">{canon}</span>'
        variants_text = '; '.join(r['variants']).replace('|', '\\|')
        variants_cell = f'<span style="{FONT}">{variants_text}</span>'
        cells = [SYMBOLS.get(r['status'].get(y), '') for y in years]
        lines.append(f'| {canon_cell} | {variants_cell} |' + ''.join(f' {c} |' for c in cells))

    return '\n'.join(lines) + '\n'


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--start-year', type=int, default=2013)
    parser.add_argument('--end-year', type=int, default=None,
                         help='Defaults to next calendar year, so future runs auto-extend.')
    parser.add_argument('--out', default=DEFAULT_OUT)
    args = parser.parse_args()

    end_year = args.end_year or (datetime.now().year + 1)
    years = [str(y) for y in range(args.start_year, end_year + 1)]

    rows = build_rows(years)
    md = render_markdown(rows, years)

    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(md)

    counts = Counter()
    for r in rows:
        counts.update(r['status'].values())
    print()
    print(f'Wrote {len(rows)} rows to {args.out}')
    print(f"  check={counts['check']} maybe={counts['maybe']} x={counts['x']} listed_no_pdf={counts['listed_no_pdf']}")


if __name__ == '__main__':
    main()
