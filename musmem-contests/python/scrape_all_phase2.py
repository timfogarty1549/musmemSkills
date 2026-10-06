#!/usr/bin/env python3
"""Bulk Phase 2 re-scraper.

For each contest in 2-normalize-athletes/ (excluding NAC), fetch fresh results
from npcnewsonline.com and write updated flat files to 1-incoming/.

Usage:
    python3 ~/workspace/skills/musmemSkills/musmem-contests/python/scrape_all_phase2.py
    python3 ~/workspace/skills/musmemSkills/musmem-contests/python/scrape_all_phase2.py '*2019*'
    python3 ~/workspace/skills/musmemSkills/musmem-contests/python/scrape_all_phase2.py --start 50

Stops immediately and exits non-zero on any unknown slug.
"""
import sys, os, re, gzip, html as h, unicodedata, urllib.request, urllib.error, glob as glob_module

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fix_subdivisions import slug_to_code, overall_slug_to_code, SKIP_SLUG_RE

SRC   = os.path.expanduser('~/workspace/musmem/2-normalize-athletes')
OUT   = os.path.expanduser('~/workspace/musmem/1-incoming')
CACHE = os.path.expanduser('~/workspace/musmem/.page_cache')
BASE  = 'https://contests.npcnewsonline.com/contests'
UA    = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# ── Division title → (code, gender) ──────────────────────────────────────────
DIV_TITLE_MAP = [
    (r'under.?212|212.?bodybuilding|^212$',  'U212', 'male'),
    (r'under.?208|208.?bodybuilding|^208$',  'U208', 'male'),
    (r"women.?s.?bodybuilding",             'BB',   'female'),
    (r"men.?s.?bodybuilding|^bodybuilding", 'OP',   'male'),
    (r"men.?s.?classic|classic.?physique",  'CL',   'male'),
    (r"women.?s.?physique",                 'PH',   'female'),
    (r"men.?s.?physique|^physique",         'PH',   'male'),
    (r"figure",                             'FI',   'female'),
    (r"wheelchair",                          'WC',   'male'),
]

# H2 section titles that are globally excluded — silently skip even if they have athletes.
# Everything else that doesn't match DIV_TITLE_MAP triggers a sanity warning.
_EXCLUDED_TITLE_RE = re.compile(
    r'bikini|wellness|fitness|fit.model', re.IGNORECASE
)

# Outer code for overall winner lines
OUTER_CODE = {
    'OP': 'OP', 'BB': 'BB', 'CL': 'CL', 'PH': 'PH',
    'FI': 'FI', 'U212': 'U212', 'U208': 'U208', 'WC': 'WC',
}

# Regex matching primary (non-masters, non-junior, non-teen) sub-division codes.
# If exactly one primary sub-div exists in a major category, collapse to outer code.
PRIMARY_SUB_RE = {
    'OP': re.compile(r'^(B[a-g]|SW|HW|LH|LW|MW|WW|BW|ULW)$'),
    'BB': re.compile(r'^(B[a-g]|SW|HW|LH|LW|MW|WW|BW|ULW)$'),
    'PH': re.compile(r'^P[a-h]$'),
    'CL': re.compile(r'^C[a-h]$'),
    'FI': re.compile(r'^F[a-h]$'),
}

# Listing page slug for each org (used as URL fallback)
LISTING_SLUG = {
    'npc_worldwide': 'npcw',
    'ifbb':          'ifbb',
}


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _cache_path(url):
    """Derive a cache file path from a URL."""
    # Use the URL path (strip leading slash, replace / with __)
    path = url.replace('https://contests.npcnewsonline.com/contests/', '')
    safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', path)
    return os.path.join(CACHE, safe + '.html')


def fetch(url):
    """Fetch URL, reading from disk cache if available, writing to cache on miss."""
    os.makedirs(CACHE, exist_ok=True)
    cpath = _cache_path(url)
    if os.path.exists(cpath):
        with open(cpath, encoding='utf-8') as f:
            return f.read()
    req = urllib.request.Request(
        url, headers={'User-Agent': UA, 'Accept-Encoding': 'gzip, deflate'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
        enc = resp.headers.get('Content-Encoding', '')
    page = (gzip.decompress(raw) if enc == 'gzip' else raw).decode('utf-8', errors='replace')
    with open(cpath, 'w', encoding='utf-8') as f:
        f.write(page)
    return page


def try_fetch(url):
    """Fetch url; return page or None on error / no contest content."""
    try:
        page = fetch(url)
        return page if page.count('data-slug') > 0 else None
    except Exception:
        return None


# ── HTML helpers ──────────────────────────────────────────────────────────────

# Consonants for initial-pair detection (all letters except vowels a e i o u)
_CONSONANTS = set('bcdfghjklmnpqrstvwxyz')
# Two-letter tokens to keep as-is rather than splitting into initials.
# 'st' = "Saint" name particle (e.g. "St Rose", "St Louis", "St Fleur" --
# common Haitian/French-Caribbean surnames) -- confirmed via 2025 Southern
# States Championships, where "Dontaevous St Rose" was mangled into
# "Dontaevous S T Rose".
# 'ng' = a common Cantonese/Vietnamese surname on its own (e.g. "Xavier Ng")
# -- confirmed via 2019 West Coast Classic.
# Two-consonant tokens ENDING IN 'y' (Ly, Ty, Dy, ...) are excluded from the
# initials-split below via a separate check, not listed individually here --
# they're short Vietnamese/Filipino/Cambodian given names or surnames
# ("Peter Ly", "Ty White", "Michael Dy", "Benghap Ty" all confirmed against
# raw source). Genuine two-letter initials-as-name (JC Harden, Bj Carswell,
# JT Tunks, TJ Walter, Pj Newcomb -- all confirmed against raw source too)
# never end in 'y', so this split is safe.
_INIT_EXCEPTIONS = {'jr', 'sr', 'st', 'ng'}
# Tokens at the end of a name that are Roman numerals → uppercase
_ROMAN_TRAIL = {'ii', 'iii', 'iv'}


def _cap_part(p):
    """Capitalize one non-hyphenated part of a token, applying apostrophe and Mc rules."""
    if "'" in p:
        p = "'".join(s.capitalize() for s in p.split("'"))
    else:
        p = p.capitalize()
    # Mc fix: Mcalister → McAlister, Mcdonald → McDonald
    if len(p) > 2 and p[:2].lower() == 'mc':
        p = p[:2] + p[2].upper() + p[3:]
    return p


def _fix_tokens(name):
    """Per-token normalization applied after basic cleaning:
    - Title-case each token (per-hyphen-part for hyphenated tokens)
    - Capitalize letter after apostrophe: O'brien → O'Brien
    - Mc fix: Mcalister → McAlister, Mcdonald → McDonald
    - Capitalize letter after hyphen: Smith-jones → Smith-Jones
    - Non-trailing 'ii' → 'Il' (name, not Roman numeral)
    - Two-consonant token → split into initials: 'DJ' → 'D J' (except Jr, Sr)
    - Trailing Roman numeral (ii/iii/iv) → uppercase: II / III / IV
    """
    tokens = name.split()
    if not tokens:
        return name
    result = []
    for i, tok in enumerate(tokens):
        tok_low = tok.lower()
        is_last = (i == len(tokens) - 1)

        # Trailing Roman numeral → uppercase
        if is_last and tok_low in _ROMAN_TRAIL:
            result.append(tok.upper())
            continue

        # Title case with apostrophe, Mc, and hyphen handling
        if '-' in tok:
            tok = '-'.join(_cap_part(part) for part in tok.split('-'))
        else:
            tok = _cap_part(tok)

        # Non-trailing 'ii' → 'Il'
        if tok_low == 'ii':
            tok = 'Il'
        # Two-consonant token → initials (e.g. 'DJ' → 'D J'). Tokens ending in
        # 'y' are excluded -- see _INIT_EXCEPTIONS comment above.
        elif (len(tok_low) == 2
              and tok_low not in _INIT_EXCEPTIONS
              and not tok_low.endswith('y')
              and all(c in _CONSONANTS for c in tok_low)):
            tok = tok_low[0].upper() + ' ' + tok_low[1].upper()

        result.append(tok)
    return ' '.join(result)

# cp1252 characters in the 0x80-0x9F range that don't exist in Latin-1.
# Translating them back to their Latin-1 control-char equivalents (same byte value)
# lets us then encode the whole string as Latin-1 and decode as UTF-8 to repair mojibake.
_CP1252_TO_LAT1 = str.maketrans({
    '\u20ac': '\x80', '\u201a': '\x82', '\u0192': '\x83', '\u201e': '\x84',
    '\u2026': '\x85', '\u2020': '\x86', '\u2021': '\x87', '\u02c6': '\x88',
    '\u2030': '\x89', '\u0160': '\x8a', '\u2039': '\x8b', '\u0152': '\x8c',
    '\u017d': '\x8e', '\u2018': '\x91', '\u2019': '\x92', '\u201c': '\x93',
    '\u201d': '\x94', '\u2022': '\x95', '\u2013': '\x96', '\u2014': '\x97',
    '\u02dc': '\x98', '\u2122': '\x99', '\u0161': '\x9a', '\u203a': '\x9b',
    '\u0153': '\x9c', '\u017e': '\x9e', '\u0178': '\x9f',
})


def clean(raw):
    return h.unescape(re.sub(r'<[^>]+>', '', raw)).strip()


_NON_LATIN_RE = re.compile(
    r'[\u0400-\u04FF'   # Cyrillic
    r'\u0600-\u06FF'    # Arabic
    r'\u4E00-\u9FFF'    # CJK Unified Ideographs
    r'\u3040-\u309F'    # Hiragana
    r'\u30A0-\u30FF]'   # Katakana
)

# npcnewsonline's "Hero" tribute program appends a military/first-responder
# occupation tag to an athlete's displayed name across ALL of their entries
# for the show, not just the Hero round itself (confirmed via 2024 Golden
# State Championships: "Gil Devera (Deputy Sheriff)" appears on his real
# Classic Physique overall/masters/class-A placings, not just the excluded
# 'heroes' slug). The placing is real; only the tag needs stripping.
# Keyword-anchored so it can't collide with the DB's numeric "(2)"/"(3)"
# duplicate-name suffix convention (bare-number parens never match this).
_OCCUPATION_KEYWORDS = (
    r'army|navy|marine|air force|coast guard|national guard|space force'
    r'|sheriff|deputy|police|officer|detective|corrections'
    r'|infantry|special\s*forces|speical\s*forces|veteran|retired'
    r'|firefighter|fire fighter|paramedic|\bemt\b'
)
_TRAILING_OCC_RE = re.compile(
    r'\s*\([^)]*(?:' + _OCCUPATION_KEYWORDS + r')[^)]*\)\s*$'
    r'|\s*--\s*(?:' + _OCCUPATION_KEYWORDS + r')[^-]*$',
    re.IGNORECASE
)


def clean_name(raw, _warn=True):
    """Strip HTML/entities from an athlete name, then apply Phase 2 name rules.
    Names are NOT reordered (no Last, First conversion).
    """
    name = h.unescape(re.sub(r'<[^>]+>', '', raw)).strip()

    # Strip npcnewsonline "Hero" tribute occupation tags (see _TRAILING_OCC_RE)
    name = _TRAILING_OCC_RE.sub('', name).strip()

    # Mojibake repair: cp1252/Latin-1 bytes misread as UTF-8.
    # Step 1: normalize cp1252 special chars (œ, Œ, ‚, etc.) to their
    #         Latin-1 control-char equivalents (same underlying byte value).
    # Step 2: encode as Latin-1 → decode as UTF-8.
    # Handles Latin diacritics ("Ã±" → "ñ") and Cyrillic/Turkish mojibake.
    # Fails safely for already-correct text: "José" (é→UnicodeDecodeError),
    # Cyrillic/CJK (UnicodeEncodeError if chars outside Latin-1+cp1252 range).
    try:
        name = name.translate(_CP1252_TO_LAT1).encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    # Normalize curly quotes/apostrophes to plain equivalents
    name = name.replace('\u2019', "'").replace('\u2018', "'")
    name = name.replace('\u201c', '"').replace('\u201d', '"')

    # Strip periods
    name = name.replace('.', '')

    # Normalize em-dash spacing: ' - ' → '-'
    name = name.replace(' - ', '-')

    # Remove trailing â: stray artifact from NPC website
    if name.endswith('\u00e2'):
        name = name[:-1]

    # Remove spaces around apostrophe: "O ' Brien" → "O'Brien"
    name = name.replace(" ' ", "'")

    # Compose decomposed diacritics: n + U+0303 → ñ, etc.
    name = unicodedata.normalize('NFC', name)

    # Per-token: title case, apostrophe caps, initials, II→Il, trailing Roman
    name = _fix_tokens(name)

    # Collapse any double spaces introduced by stripping or initial expansion
    name = re.sub(r'  +', ' ', name).strip()

    # Warn on non-Latin scripts (Cyrillic, Arabic, CJK)
    if _warn and _NON_LATIN_RE.search(name):
        print(f'  WARNING: non-Latin script in name: {name!r}')

    return name


def map_title(title):
    t = title.lower()
    for pattern, code, gender in DIV_TITLE_MAP:
        if re.search(pattern, t):
            return code, gender
    return None, None


def iter_sections(page):
    for td_m in re.finditer(
            r'<td class="[^"]*-td">(.*?)(?=<td class="|</tr\s*>)',
            page, re.DOTALL):
        section = td_m.group(1)
        title_m = re.search(r'<h2 class="division-title">(.*?)</h2>', section, re.DOTALL)
        if title_m:
            yield clean(title_m.group(1)), section


def extract_athletes(cls_html):
    """Extract (placing, name) pairs. Overall winner spans are empty → placing 0.

    Anchors whose class includes "comparison" are npcnewsonline's placeholder
    links to an "Overall Comparisons" photo round (e.g. class="comparison
    28539 open"), not real athletes -- confirmed via 2020 Southern States
    Championships, where these produced fake "0 Men's Physique Overall
    Comparisons" entries. Skip them entirely.
    """
    athletes = []
    for a_m in re.finditer(r'<a([^>]*data-person="yes"[^>]*)>(.*?)</a>', cls_html, re.DOTALL):
        tag_attrs = a_m.group(1)
        if re.search(r'\bclass="[^"]*\bcomparison\b', tag_attrs):
            continue
        inner = a_m.group(2)
        span_m = re.search(r'<span>\s*(\d*)\s*</span>', inner)
        placing = int(span_m.group(1)) if (span_m and span_m.group(1).strip()) else 0
        name_raw = re.sub(r'<span>[^<]*</span>', '', inner)
        name = clean_name(name_raw)
        if name:
            athletes.append((placing, name))
    return athletes


def apply_98(athletes):
    """Replace tied last placings with 98."""
    if not athletes:
        return athletes
    placed = [p for p, _ in athletes if p != 0]
    if not placed:
        return athletes
    max_p = max(placed)
    if placed.count(max_p) > 1:
        athletes = [(98 if p == max_p else p, n) for p, n in athletes]
    return athletes


# ── URL helpers ───────────────────────────────────────────────────────────────

def make_url(year, slug, org):
    """Derive direct contest URL from slug and org."""
    if org == 'npc_worldwide':
        return f"{BASE}/{year}/npc_worldwide_{slug}"
    elif org == 'ifbb':
        return f"{BASE}/{year}/ifbb_{slug}"
    else:
        raise ValueError(f"Unknown org: {org!r}")


def find_url_from_listing(year, slug, org):
    """Search listing page for URL matching slug. Returns best-match URL or None."""
    listing_slug = LISTING_SLUG.get(org)
    if not listing_slug:
        return None
    listing_url = f"{BASE}/{year}/{listing_slug}"
    try:
        page = fetch(listing_url)
    except Exception as e:
        print(f"    listing fetch failed: {e}")
        return None

    all_urls = re.findall(
        rf'href="({re.escape(BASE)}/{year}/[^"]+)"', page)

    slug_tokens = set(slug.split('_'))
    best_url, best_score = None, 0
    for url in all_urls:
        url_slug = url.split('/')[-1]
        # Strip org prefix for fair comparison
        if org == 'npc_worldwide' and url_slug.startswith('npc_worldwide_'):
            url_slug = url_slug[len('npc_worldwide_'):]
        url_tokens = set(url_slug.split('_'))
        overlap = len(slug_tokens & url_tokens)
        if overlap > best_score:
            best_score = overlap
            best_url = url

    # Require at least 2 matching tokens (avoids spurious matches on short slugs)
    return best_url if best_url and best_score >= 2 else None


# ── Contest parsing ───────────────────────────────────────────────────────────

def _check_no_placings(athletes, slug, div_title):
    """Print a warning if athletes are listed but none have a placing number (registrations only)."""
    if athletes and all(p == 0 for p, _ in athletes):
        print(f"  NOTE: '{div_title}' slug='{slug}' — athletes registered but no placings posted (skipping)")

def page_has_under_division(page):
    """Return True if the page has an Under 212, 208, or 202 bodybuilding section."""
    for title, _ in iter_sections(page):
        if re.search(r'under.?2(?:02|08|12)|^2(?:02|08|12)$', title, re.I):
            return True
    return False


def _warn_unrecognized_section(div_title, section):
    """Warn if an unrecognized h2 section contains placed athletes in non-skip slugs."""
    slugs_with_athletes = []
    for m in re.finditer(
            r'<div class="competitor-class[^"]*" data-slug="([^"]+)">'
            r'(.*?)(?=<div class="competitor-class|$)',
            section, re.DOTALL):
        slug     = m.group(1)
        cls_html = m.group(2)
        if re.search(r'^overall', slug, re.I):
            continue
        if slug.lower() != 'open' and SKIP_SLUG_RE.search(slug):
            continue
        athletes = extract_athletes(cls_html)
        placed   = [a for a in athletes if a[0] != 0]
        if placed:
            slugs_with_athletes.append((slug, len(placed)))
    if slugs_with_athletes:
        print(f"  SANITY: unrecognized section '{div_title}' — athletes not captured:")
        for slug, count in slugs_with_athletes:
            print(f"    {count} athlete(s) under slug '{slug}'")


def _add_section(div_sections, code, athletes, front=False):
    """Append athletes under `code` to div_sections, merging into an existing
    block with the same code instead of creating a second 'c CODE' header.

    Confirmed necessary via 2023 Florida State Championships: Women's
    Bodybuilding had both an 'overall-winner' slug (placing 0) and a separate
    bare 'open' slug (real placings), both mapping to code 'BB' — previously
    written as two separate 'c BB' blocks in the same file, violating the
    "one block per code" rule.

    `front` controls where a brand-new block is inserted into div_sections
    (True = index 0, matching the old insert(0, ...) used for the primary
    overall winner; False = end, matching plain .append() used elsewhere).
    When merging into an already-existing block, placing-0 (overall) athletes
    are always prepended so they stay first within the block, regardless of
    `front` — matching file convention (overall line before class placings).
    """
    is_overall = bool(athletes) and athletes[0][0] == 0
    for existing_code, existing_athletes in div_sections:
        if existing_code == code:
            if is_overall:
                existing_athletes[0:0] = athletes
            else:
                existing_athletes.extend(athletes)
            return
    if front:
        div_sections.insert(0, (code, list(athletes)))
    else:
        div_sections.append((code, list(athletes)))


def parse_contest(page, contest_label):
    """
    Parse a contest page. Returns (male_sections, female_sections).
    Raises ValueError on unknown slug (caller should stop and report).
    Each element is a list of (code, [(placing, name), ...]).
    """
    male_sections   = []
    female_sections = []

    # Pre-scan: is there an Under 212/208/202 section? Determines how 'open' maps for OP.
    has_under = page_has_under_division(page)

    for div_title, section in iter_sections(page):
        div_code, gender = map_title(div_title)
        if not div_code:
            # Silently skip known excluded divisions.
            # For anything else, warn if athletes are present in non-skip slugs.
            if not _EXCLUDED_TITLE_RE.search(div_title):
                _warn_unrecognized_section(div_title, section)
            continue

        outer_code = OUTER_CODE[div_code]
        div_sections = []  # (code, athletes) for this division

        cls_blocks = list(re.finditer(
            r'<div class="competitor-class[^"]*" data-slug="([^"]+)">'
            r'(.*?)(?=<div class="competitor-class|$)',
            section, re.DOTALL))

        page_placed = 0   # athletes on page in non-skip, non-overall slugs

        for cls_m in cls_blocks:
            slug     = cls_m.group(1)
            cls_html = cls_m.group(2)

            # Overall winner
            if re.search(r'^overall', slug, re.I):
                athletes = extract_athletes(cls_html)
                if athletes:
                    # Insert overall at front, placing=0
                    _add_section(div_sections, outer_code, [(0, n) for _, n in athletes], front=True)
                continue

            # 'open' slug — maps to outer code; for OP use OP only if Under 212/208 present
            if slug.lower() == 'open':
                if div_code == 'OP':
                    code = 'OP' if has_under else 'BB'
                else:
                    code = outer_code  # PH, CL, FI, BB
                raw_athletes = extract_athletes(cls_html)
                _check_no_placings(raw_athletes, slug, div_title)
                athletes = apply_98([(p, n) for p, n in raw_athletes if p != 0])
                page_placed += len(athletes)
                if athletes:
                    _add_section(div_sections, code, athletes)
                continue

            # Sub-group overall rounds on pro-qualifier pages carry an
            # '-earned-pro-card' suffix (e.g. 'masters-40-overall-winner-earned-pro-card'),
            # which SKIP_SLUG_RE's 'earned' would otherwise swallow. Route them
            # to the sub-group overall handling below before the skip check.
            # Confirmed via 2026 Canadian Natural Pro Qualifier - CPA.
            base_slug = re.sub(r'-earned-pro-card$', '', slug.lower())
            if base_slug != slug.lower() and base_slug.endswith(('-overall', '-overall-winner')):
                code = overall_slug_to_code(slug, div_code)  # raises ValueError on unknown
                athletes = extract_athletes(cls_html)
                if athletes:
                    _add_section(div_sections, code, [(0, n) for _, n in athletes])
                continue

            # Skip excluded categories (novice, beginner, comparison, regional, etc.)
            if SKIP_SLUG_RE.search(slug):
                continue

            # Sub-group overall rounds (teen-overall, masters-overall,
            # masters-over-N-overall, and the '-overall-winner' variant used
            # on some page templates, e.g. masters-overall-winner) — compare
            # winners of several sub-classes within one tier against each
            # other, distinct from the division's main 'overall-winner' slug
            # handled above. Previously these were silently absorbed by
            # SKIP_SLUG_RE's unanchored 'overall' match and dropped entirely;
            # now routed to their own placing-0 entry.
            if slug.lower().endswith(('-overall', '-overall-winner')):
                code = overall_slug_to_code(slug, div_code)  # raises ValueError on unknown
                athletes = extract_athletes(cls_html)
                if athletes:
                    _add_section(div_sections, code, [(0, n) for _, n in athletes])
                continue

            # Map slug → code (raises ValueError on unknown)
            code = slug_to_code(slug, div_code)

            raw_athletes = extract_athletes(cls_html)
            _check_no_placings(raw_athletes, slug, div_title)
            athletes = apply_98([(p, n) for p, n in raw_athletes if p != 0])
            page_placed += len(athletes)
            if athletes:
                _add_section(div_sections, code, athletes)

        # Sanity check: athletes captured should equal athletes on page
        extracted_placed = sum(
            sum(1 for p, _ in athletes if p != 0)
            for _, athletes in div_sections
        )
        if extracted_placed != page_placed:
            print(f"  SANITY: '{div_title}' — {page_placed} placed on page, "
                  f"{extracted_placed} extracted")

        # Collapse single primary sub-division to outer code
        primary_re = PRIMARY_SUB_RE.get(div_code)
        if primary_re:
            primary_idx = [i for i, (code, _) in enumerate(div_sections)
                           if primary_re.match(code)]
            if len(primary_idx) == 1:
                idx = primary_idx[0]
                old_code = div_sections[idx][0]
                outer_existing = [i for i, (code, _) in enumerate(div_sections)
                                  if code == outer_code]
                if outer_existing and all(p == 0 for p, _ in div_sections[outer_existing[0]][1]):
                    # The outer block is only an overall (0) over a single class —
                    # nothing was compared, so collapse the class to the outer code
                    # and drop the overall (a code can't hold both 0 and 1).
                    # Confirmed via 2023/2024 Atlanta Classic - NPC (Figure).
                    dropped = [n for _, n in div_sections[outer_existing[0]][1]]
                    print(f"  FLAG: only one primary sub-div ({old_code}) in '{div_title}' "
                          f"— collapsing to {outer_code}, dropping overall {dropped}")
                    div_sections[idx] = (outer_code, div_sections[idx][1])
                    del div_sections[outer_existing[0]]
                elif outer_existing:
                    print(f"  FLAG: single primary sub-div ({old_code}) in '{div_title}' "
                          f"but outer {outer_code} already present — leaving as-is")
                else:
                    print(f"  FLAG: only one primary sub-div ({old_code}) in '{div_title}' "
                          f"— collapsing to {outer_code}")
                    div_sections[idx] = (outer_code, div_sections[idx][1])

        # A code can never hold both an overall (0) and real placings (1, 2, ...).
        # An overall belongs to the parent of the sub-codes it compares (e.g.
        # M4-0 over 4H/4M/4L; MA-0 over M4/M5); if the same code also has real
        # placings, there was nothing to compare, so drop the 0 line. Rule
        # confirmed by user 2026-10-04.
        for i, (code, athletes) in enumerate(div_sections):
            if any(p == 0 for p, _ in athletes) and any(p != 0 for p, _ in athletes):
                dropped = [n for p, n in athletes if p == 0]
                print(f"  FLAG: '{div_title}' code {code} has both 0 and real placings "
                      f"— dropping overall {dropped}")
                div_sections[i] = (code, [(p, n) for p, n in athletes if p != 0])

        # A placing-0 "overall winner" only means something when there are
        # other sub-divisions being compared against it. If the outer code
        # ends up as the *only* section for this division, with nothing but
        # that single placing-0 entry, the entrant isn't really an "overall"
        # winner in the comparison sense — they're just the sole competitor,
        # so they get a real placing of 1 instead. Confirmed via 2021 Georgia
        # State Championships (as "Georgia Bodybuilding Championships"),
        # where every weight/class sub-division had registrants but no
        # placings posted, leaving only the bare overall-winner slug.
        if (len(div_sections) == 1 and div_sections[0][0] == outer_code
                and len(div_sections[0][1]) == 1 and div_sections[0][1][0][0] == 0):
            name = div_sections[0][1][0][1]
            div_sections[0] = (outer_code, [(1, name)])

        if gender == 'male':
            male_sections.extend(div_sections)
        else:
            female_sections.extend(div_sections)

    return male_sections, female_sections


def write_file(fname, year, title, sections):
    """Write flat file to OUT directory. Returns athlete count."""
    path = os.path.join(OUT, fname)
    with open(path, 'w') as f:
        f.write(f'y {year}\n')
        f.write(f't {title}\n')
        for i, (code, athletes) in enumerate(sections):
            if i > 0:
                f.write('----\n')
            f.write(f'c {code}\n')
            for placing, name in athletes:
                f.write(f'{placing} {name}\n')
    return sum(len(a) for _, a in sections)


# ── File collection ───────────────────────────────────────────────────────────

def parse_filename(fname):
    """Parse '{year}_{slug}-{org}-{gender}.txt' → (year, slug, org, gender)."""
    base = fname.replace('.txt', '')
    m = re.match(r'^(\d{4})_(.+)-([^-]+(?:_[^-]+)*)-(male|female)$', base)
    if not m:
        return None
    return int(m.group(1)), m.group(2), m.group(3), m.group(4)


def read_title(fpath):
    with open(fpath) as f:
        for line in f:
            if line.startswith('t '):
                return line[2:].strip()
    return None


def collect_contests(pattern=None):
    """Collect contests grouped by (year, slug, org) excluding NAC."""
    if pattern:
        files = sorted(glob_module.glob(os.path.join(SRC, pattern)))
    else:
        files = sorted(glob_module.glob(os.path.join(SRC, '*.txt')))

    # Exclude NAC, exclude .BAK and .txt-1 files
    files = [f for f in files
             if '-nac-' not in os.path.basename(f)
             and os.path.basename(f).endswith('.txt')
             and not re.search(r'\.txt-\d+$', os.path.basename(f))]

    contests = {}
    for fpath in files:
        fname  = os.path.basename(fpath)
        parsed = parse_filename(fname)
        if not parsed:
            print(f"  WARNING: cannot parse filename: {fname}", file=sys.stderr)
            continue
        year, slug, org, gender = parsed
        key = (year, slug, org)
        if key not in contests:
            contests[key] = {'year': year, 'slug': slug, 'org': org,
                             'male': None, 'female': None, 'title': None}
        contests[key][gender] = fpath
        if contests[key]['title'] is None:
            contests[key]['title'] = read_title(fpath)

    return sorted(contests.values(), key=lambda c: (c['year'], c['slug']))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    pattern = None
    start   = 0
    i = 0
    while i < len(args):
        if args[i] == '--start' and i + 1 < len(args):
            start = int(args[i + 1])
            i += 2
        else:
            pattern = args[i]
            i += 1

    os.makedirs(OUT, exist_ok=True)
    contests = collect_contests(pattern)
    total    = len(contests)
    print(f"Contests found: {total}  (processing from #{start + 1})")

    ok = err = 0
    for num, contest in enumerate(contests[start:], start=start + 1):
        year  = contest['year']
        slug  = contest['slug']
        org   = contest['org']
        title = contest['title'] or f"??? - {org.upper().replace('_', ' ')}"

        print(f"\n[{num}/{total}] {title} ({year})")

        # Derive URL and fetch
        try:
            url = make_url(year, slug, org)
        except ValueError as e:
            print(f"  ERROR: {e}")
            err += 1
            continue

        print(f"  {url}", end=' ... ', flush=True)
        page = try_fetch(url)

        if page is None:
            print(f"FAILED — trying listing page")
            url = find_url_from_listing(year, slug, org)
            if url:
                print(f"  Found: {url}", end=' ... ', flush=True)
                page = try_fetch(url)

        if page is None:
            print(f"FAILED")
            print(f"  ERROR: cannot fetch page for {slug}")
            err += 1
            continue

        print(f"OK ({page.count('data-slug')} slugs)")

        # Parse
        contest_label = f"{title} ({year})"
        try:
            male_sections, female_sections = parse_contest(page, contest_label)
        except ValueError as e:
            print(f"\n  UNKNOWN SLUG — stopping: {e}")
            print(f"  Contest: {contest_label}")
            print(f"  URL:     {url}")
            sys.exit(1)

        # Write
        base = f"{year}_{slug}-{org}"
        wrote_any = False

        if contest['male'] is not None:
            if male_sections:
                n = write_file(f"{base}-male.txt", year, title, male_sections)
                print(f"  male:   {len(male_sections)} sections, {n} athletes")
                wrote_any = True
            else:
                print(f"  male:   WARNING — no sections found on page")

        if contest['female'] is not None:
            if female_sections:
                n = write_file(f"{base}-female.txt", year, title, female_sections)
                print(f"  female: {len(female_sections)} sections, {n} athletes")
                wrote_any = True
            else:
                print(f"  female: WARNING — no sections found on page")

        if wrote_any:
            ok += 1
        else:
            err += 1

    print(f"\n{'='*60}")
    print(f"Done — written: {ok}, errors/skipped: {err}")
    if err:
        sys.exit(1)


if __name__ == '__main__':
    main()
