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
from fix_subdivisions import slug_to_code, SKIP_SLUG_RE

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
]

# Outer code for overall winner lines
OUTER_CODE = {
    'OP': 'OP', 'BB': 'BB', 'CL': 'CL', 'PH': 'PH',
    'FI': 'FI', 'U212': 'U212', 'U208': 'U208',
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

# Roman numeral suffix: II, III, IV, VI, VII, VIII, IX, X, XI, XII etc.
# Only matches at end of string, preceded by whitespace.
_ROMAN_RE = re.compile(
    r'(\s+)(X{0,3}(?:IX|IV|VIII|VII|VI|V|III|II|I))$',
    re.IGNORECASE
)

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


def clean_name(raw):
    """Strip HTML/entities from an athlete name, then apply Phase 2 name rules:
    - Attempt mojibake repair (Latin-1 bytes misread as UTF-8)
    - Strip periods
    - Uppercase trailing Roman numeral suffixes
    Names are NOT reordered (no Last, First conversion).
    """
    name = h.unescape(re.sub(r'<[^>]+>', '', raw)).strip()

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

    # Uppercase trailing Roman numeral (e.g. "John Smith iii" → "John Smith III")
    name = _ROMAN_RE.sub(lambda m: m.group(1) + m.group(2).upper(), name)

    # Compose decomposed diacritics: n + U+0303 → ñ, etc.
    name = unicodedata.normalize('NFC', name)

    # Collapse any double spaces introduced by stripping
    name = re.sub(r'  +', ' ', name).strip()

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
    """Extract (placing, name) pairs. Overall winner spans are empty → placing 0."""
    athletes = []
    for a_m in re.finditer(r'<a[^>]*data-person="yes"[^>]*>(.*?)</a>', cls_html, re.DOTALL):
        inner = a_m.group(1)
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
    """Raise ValueError if athletes are listed but none have a placing number."""
    if athletes and all(p == 0 for p, _ in athletes):
        raise ValueError(
            f"Athletes registered but no placings posted "
            f"(slug='{slug}', division='{div_title}')"
        )

def page_has_under_division(page):
    """Return True if the page has an Under 212, 208, or 202 bodybuilding section."""
    for title, _ in iter_sections(page):
        if re.search(r'under.?2(?:02|08|12)|^2(?:02|08|12)$', title, re.I):
            return True
    return False


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
            continue  # Bikini, Wellness, Fitness, Novice, etc. — skip

        outer_code = OUTER_CODE[div_code]
        div_sections = []  # (code, athletes) for this division

        cls_blocks = list(re.finditer(
            r'<div class="competitor-class[^"]*" data-slug="([^"]+)">'
            r'(.*?)(?=<div class="competitor-class|$)',
            section, re.DOTALL))

        for cls_m in cls_blocks:
            slug     = cls_m.group(1)
            cls_html = cls_m.group(2)

            # Overall winner
            if re.search(r'^overall', slug, re.I):
                athletes = extract_athletes(cls_html)
                if athletes:
                    # Insert overall at front, placing=0
                    div_sections.insert(0, (outer_code, [(0, n) for _, n in athletes]))
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
                if athletes:
                    div_sections.append((code, athletes))
                continue

            # Skip excluded categories (novice, beginner, comparison, regional, etc.)
            if SKIP_SLUG_RE.search(slug):
                continue

            # Map slug → code (raises ValueError on unknown)
            code = slug_to_code(slug, div_code)

            raw_athletes = extract_athletes(cls_html)
            _check_no_placings(raw_athletes, slug, div_title)
            athletes = apply_98([(p, n) for p, n in raw_athletes if p != 0])
            if athletes:
                div_sections.append((code, athletes))

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
                if outer_existing:
                    print(f"  FLAG: single primary sub-div ({old_code}) in '{div_title}' "
                          f"but outer {outer_code} already present — leaving as-is")
                else:
                    print(f"  FLAG: only one primary sub-div ({old_code}) in '{div_title}' "
                          f"— collapsing to {outer_code}")
                    div_sections[idx] = (outer_code, div_sections[idx][1])

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
