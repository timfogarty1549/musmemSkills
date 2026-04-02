#!/usr/bin/env python3
"""
Fix missing sub-division c-lines, overall-winner entries, and wrong division
codes in 2-normalize-athletes/ files.

Three types of fixes:
  1. Sub-division insertions: insert 'c {code}' before each placing-1 reset
  2. Code corrections: replace a wrong c-code (e.g. c OP → c BB in female files)
  3. Overall-winner appends: append 'c {outer}\n0 {athlete}' at end of file
     (only when --overall flag is given)

Usage:
    python3 fix_subdivisions.py                     # interactive, all files
    python3 fix_subdivisions.py --auto              # automatic, all files
    python3 fix_subdivisions.py 2022_charlotte*     # specific files (glob)
    python3 fix_subdivisions.py --overall 2023_*    # also add overall-winner entries
    python3 fix_subdivisions.py --auto --overall    # fully automatic with overall check
"""

import os, re, sys, glob, urllib.request, html as html_module

SRC      = os.path.expanduser('~/workspace/musmem/2-normalize-athletes')
BASE_URL = 'https://contests.npcnewsonline.com/contests'
UA       = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# ── Division code tables ────────────────────────────────────────────────────

# Age-group codes per parent division code.
# Key: parent div code → {age: sub-code}
# Covers both 'masters-over-N' (IFBB Pro) and 'masters-N' (NPC Worldwide) slugs.
MASTERS_AGE_CODES = {
    'OP':   {35: 'M3',  40: 'M4',  45: '45',  50: 'M5',  55: '55',  60: 'M6',
             65: 'm6',  70: 'M7',  80: 'M8',  90: 'M9'},
    'BB':   {35: 'M3',  40: 'M4',  45: '45',  50: 'M5',  55: '55',  60: 'M6',
             70: 'M7'},
    'CL':   {35: 'c3',  40: 'c4',  45: 'c45', 50: 'c5',  55: 'c55', 60: 'c6',
             70: 'c7'},
    'PH':   {30: 'P3',  35: 'P35', 40: 'P4',  45: 'P45', 50: 'P5',  55: 'P55',
             60: 'P6',  70: 'P7'},
    'FI':   {35: 'f3',  40: 'F4',  45: 'f4',  50: 'F5',  55: 'f5',  60: 'F6',
             65: 'F65', 70: 'F65'},
    'U212': {40: 'M4',  45: '45',  50: 'M5'},
}

BB_HEIGHT_CODES = {
    'a': 'Ba', 'b': 'Bb', 'c': 'Bc', 'd': 'Bd',
    'e': 'Be', 'f': 'Bf', 'g': 'Bg',
}

# Masters competing in height classes (no age number, just letter suffix)
MASTERS_HEIGHT_CODES = {
    'a': 'MAa', 'b': 'MAb', 'c': 'MAc', 'd': 'MAd',
}

# Junior slug maps to different codes depending on parent division
JUNIOR_CODES = {
    'OP': 'JR', 'BB': 'JR',
    'PH': 'PJ',
    'CL': 'CJ',
    'FI': 'FJ',
}

# Teen slug maps to different codes depending on parent division
TEEN_CODES = {
    'OP': 'TE', 'BB': 'TE',
    'CL': 'ct',
    'PH': 'PT',
    'FI': 'FT',
}

# Open-class letter prefix per division (for class-X slugs)
# e.g. CL+class-a → Ca, PH+class-a → Pa, FI+class-a → Fa
CLASS_LETTER_PREFIX = {
    'CL': 'C',
    'PH': 'P',
    'FI': 'F',
}
CLASS_LETTER_MAX = {
    'CL': 'h',   # Ca–Ch
    'PH': 'h',   # Pa–Ph
    'FI': 'h',   # Fa–Fh
}

# Weight/height suffix map for masters age+sub-class combos
# slug suffix → division-code suffix appended to base age code
WEIGHT_SUFFIX = {
    'super-heavyweight': 'S',
    'heavyweight':       'H',
    'light-heavyweight': 'l',
    'middleweight':      'M',
    'welterweight':      'W',
    'lightweight':       'L',
    'bantamweight':      'B',
    'tall':              't',
    'medium-tall':       '',   # handled separately if needed
    'medium':            'm',
    'short':             's',
}

# For OP/BB masters+weight, age → numeric prefix used in codes (e.g. 35→'3', 45→'45')
OP_AGE_PREFIX = {35: '3', 40: '4', 45: '45', 50: '5', 55: '55', 60: '6', 70: '7'}

# Bare weight/height class slugs for OP/BB open divisions (IFBB amateur style)
# These appear without any age prefix, e.g. just 'super-heavyweight', 'heavyweight', etc.
OPEN_WEIGHT_SLUG_CODES = {
    'super-heavyweight': 'SW',
    'heavyweight':       'HW',
    'light-heavyweight': 'LH',
    'middleweight':      'MW',
    'welterweight':      'WW',
    'lightweight':       'LW',
    'bantamweight':      'BW',
    'ultra-lightweight': 'ULW',
}

# Junior with weight class slug → code (OP/BB context)
JUNIOR_WEIGHT_CODES = {
    'heavyweight':       'JH',
    'light-heavyweight': 'Jl',
    'middleweight':      'JM',
    'welterweight':      'JW',
    'lightweight':       'JL',
    'bantamweight':      'JB',
    'flyweight':         'JF',
    'light-flyweight':   'Jf',
    'tall':              'Jt',
    'medium':            'Jm',
    'short':             'Js',
}

# Junior with class letter: prefix per division (e.g. junior-a in PH → PJa)
JUNIOR_CLASS_PREFIX = {
    'CL': 'CJ',
    'PH': 'PJ',
    'FI': 'FJ',
}

# kg-based weight class slugs → MuscleMemory codes
KG_SLUG_CODES = {
    '55kg':                    '55kg',
    '60kg':                    '60kg',
    '65kg':                    '65kg',
    '70kg':                    '70kg',
    '75kg':                    '75kg',
    '80kg':                    '80kg',
    '85kg':                    '85kg',
    '90kg':                    '90kg',
    '95kg':                    '95kg',
    '100kg':                   '100kg',
    # ranges → upper value
    '65-70kg':                 '70kg',
    '75-80kg':                 '80kg',
    '80-85kg':                 '85kg',
    '85-90kg':                 '90kg',
    '90-95kg':                 '95kg',
    '95-100kg':                '100kg',
    # over 100
    'over-100kg':              'o100kg',
    # Perth-specific plain over/under
    'under-85kg':              'LW',
    'over-85kg':               'MW',
    'over-102kg':              'HW',
    # descriptive variants
    'lightweight-up-to-75kg':  'LW',
    'middleweight-up-to-85kg': 'MW',
    'heavyweight-over-85kg':   'HW',
}


def slug_to_code(slug, div_code):
    """Map a data-slug to a division code given the parent div code.
    Raises ValueError for unrecognized slugs that are not in SKIP_SLUG_RE.
    Handles both 'masters-over-N' (IFBB Pro) and 'masters-N[...]' (NPC Worldwide).
    """
    slug_l = slug.lower()

    # ── Typo normalization ───────────────────────────────────────────────────
    # 'master-N-*' → 'masters-N-*' (missing 's')
    if slug_l.startswith('master-') and not slug_l.startswith('masters-'):
        slug_l = 'masters-' + slug_l[7:]
    # 'clas-X' → 'class-X'
    if slug_l.startswith('clas-') and not slug_l.startswith('class-'):
        slug_l = 'class-' + slug_l[5:]

    # Strip 'pro-qualifier-' prefix — treat like the bare sub-class slug
    if slug_l.startswith('pro-qualifier-'):
        slug_l = slug_l[len('pro-qualifier-'):]

    # Bare letter slug (a/b/c/d/e/f/g/h) — treat as 'class-{letter}'
    if re.match(r'^[a-h]$', slug_l):
        slug_l = f'class-{slug_l}'

    age_map = MASTERS_AGE_CODES.get(div_code, {})

    # ── Open-class letter sub-divisions (class-X) ────────────────────────────
    hm = re.match(r'^class-([a-h])$', slug_l)
    if hm:
        letter = hm.group(1)
        if div_code in ('OP', 'BB'):
            code = BB_HEIGHT_CODES.get(letter)
            if code is None:
                raise ValueError(
                    f"Unknown Bodybuilding height class '{slug}' — "
                    f"only class-a through class-g are mapped"
                )
            return code
        prefix = CLASS_LETTER_PREFIX.get(div_code)
        if prefix:
            max_l = CLASS_LETTER_MAX[div_code]
            if letter > max_l:
                raise ValueError(
                    f"Unknown class letter '{slug}' for division '{div_code}' — "
                    f"only class-a through class-{max_l} are mapped"
                )
            return f'{prefix}{letter}'
        raise ValueError(f"'class-{letter}' slug in unhandled division context '{div_code}'")

    # ── Masters age + class/weight combos ────────────────────────────────────
    # Matches: masters-[over-]N-{suffix}  e.g. masters-over-40-class-a, masters-45-heavyweight
    m = re.match(r'^masters-(?:over-)?(\d+)-(.+)$', slug_l)
    if m:
        age    = int(m.group(1))
        suffix = m.group(2)   # e.g. 'class-a', 'heavyweight', 'tall'
        base   = age_map.get(age)
        if base is None:
            raise ValueError(
                f"Unknown masters age {age} for division '{div_code}' — "
                f"add to MASTERS_AGE_CODES"
            )
        # class-X suffix or bare letter → append letter to base age code
        # e.g. masters-35-class-a or masters-35-a both → P35a
        lm = re.match(r'^(?:class-)?([a-h])$', suffix)
        if lm:
            return f'{base}{lm.group(1)}'
        # weight/height suffix → context-dependent
        wsuffix = WEIGHT_SUFFIX.get(suffix)
        if wsuffix is not None:
            if div_code in ('OP', 'BB'):
                prefix = OP_AGE_PREFIX.get(age)
                if prefix is None:
                    raise ValueError(
                        f"No OP age prefix for age {age} — add to OP_AGE_PREFIX"
                    )
                return f'{prefix}{wsuffix}'
            # For PH/CL/FI, weight suffixes would append to base age code too
            # but these are uncommon — raise error if not yet seen
            raise ValueError(
                f"Masters age+weight combo '{slug}' in division '{div_code}' — "
                f"check en.json for the correct code"
            )
        raise ValueError(
            f"Unknown masters combo suffix '{suffix}' in '{slug}' — "
            f"add to WEIGHT_SUFFIX or handle explicitly"
        )

    # ── Masters no-age combos ────────────────────────────────────────────────
    # masters-class-X (no age number)
    hm2 = re.match(r'^masters-class-([a-d])$', slug_l)
    if hm2:
        letter = hm2.group(1)
        if div_code in ('OP', 'BB'):
            return MASTERS_HEIGHT_CODES[letter]   # MAa–MAd
        if div_code == 'PH':
            return f'MP{letter}'                  # MPa–MPd
        raise ValueError(
            f"'masters-class-{letter}' in unhandled division context '{div_code}'"
        )

    # Bare 'masters' slug (no age, no class) — context-dependent
    if slug_l == 'masters':
        bare_masters = {'OP': 'MA', 'BB': 'MA', 'PH': 'MP', 'CL': 'mc', 'FI': 'FM'}
        code = bare_masters.get(div_code)
        if code:
            return code
        raise ValueError(
            f"'masters' slug in unhandled division context '{div_code}'"
        )

    # ── Age-only masters slugs ────────────────────────────────────────────────
    # NPC Worldwide: masters-N (plain age, no suffix)
    m = re.match(r'^masters-(\d+)$', slug_l)
    if m:
        code = age_map.get(int(m.group(1)))
        if code is None:
            raise ValueError(
                f"Unknown masters age '{slug}' for division '{div_code}'"
            )
        return code
    # IFBB Pro: masters-over-N
    m = re.match(r'^masters-over-(\d+)$', slug_l)
    if m:
        code = age_map.get(int(m.group(1)))
        if code is None:
            raise ValueError(
                f"Unknown masters age '{slug}' for division '{div_code}'"
            )
        return code

    # ── Other categorical sub-divisions ─────────────────────────────────────
    if slug_l in ('wheelchair', 'wheel-chair'):
        return 'WC'

    if slug_l in ('adaptive', 'special'):
        return 'Hs'

    if slug_l == 'senior':
        return 'MA'

    # ── kg-based weight classes ──────────────────────────────────────────────
    if slug_l in KG_SLUG_CODES:
        if div_code in ('OP', 'BB'):
            return KG_SLUG_CODES[slug_l]
        raise ValueError(f"kg slug '{slug}' in unhandled division context '{div_code}'")

    # ── Height sub-classes for Classic Physique ──────────────────────────────
    if slug_l == 'a-under175cm' and div_code == 'CL':
        return 'Ca'
    if slug_l == 'b-over175cm' and div_code == 'CL':
        return 'Cb'

    # ── Outer-code slugs (pro-qualifier bare, unique/única, class bare) ──────
    if slug_l in ('pro-qualifier', 'unique', 'única', 'class'):
        return div_code

    # ── Junior with class letter (junior-a, junior-class-a, etc.) ───────────
    # Matches: junior-[class-]X  e.g. junior-a, junior-b, junior-class-a
    jm = re.match(r'^junior-(?:class-)?([a-h])$', slug_l)
    if jm:
        letter = jm.group(1)
        prefix = JUNIOR_CLASS_PREFIX.get(div_code)
        if prefix:
            return f'{prefix}{letter}'
        raise ValueError(f"junior-class-{letter} slug in unhandled division context '{div_code}'")

    # ── Junior with weight class (junior-heavyweight, etc.) ─────────────────
    jw = re.match(r'^junior-(.+)$', slug_l)
    if jw:
        weight = jw.group(1)
        code = JUNIOR_WEIGHT_CODES.get(weight)
        if code:
            return code
        raise ValueError(f"Unknown junior weight slug '{slug}' — add to JUNIOR_WEIGHT_CODES")

    if slug_l == 'junior':
        code = JUNIOR_CODES.get(div_code)
        if code:
            return code
        raise ValueError(f"'junior' slug in unhandled division context '{div_code}'")

    if slug_l in ('teen', 'teenage', 'teenager'):
        code = TEEN_CODES.get(div_code)
        if code:
            return code
        raise ValueError(f"'{slug_l}' slug in unhandled division context '{div_code}'")

    # ── Bare open weight class slugs (IFBB amateur style) ───────────────────
    # e.g. 'super-heavyweight', 'heavyweight', 'light-heavyweight', etc.
    if slug_l in OPEN_WEIGHT_SLUG_CODES:
        if div_code in ('OP', 'BB'):
            return OPEN_WEIGHT_SLUG_CODES[slug_l]
        raise ValueError(
            f"Weight class slug '{slug}' in unhandled division context '{div_code}'"
        )

    # ── Site-specific miscategorizations ────────────────────────────────────
    # Brazil 2021: Middleweight mis-split into class-a (Light-Middle) / class-b (Middle)
    if slug_l == 'middleweight-class-a' and div_code in ('OP', 'BB'):
        return 'LM'
    if slug_l == 'middleweight-class-b' and div_code in ('OP', 'BB'):
        return 'MW'

    raise ValueError(
        f"Unknown slug '{slug}' in division '{div_code}' — "
        f"add to en.json/divs.php or to SKIP_SLUG_RE"
    )

# Division title → sub-class parent code
DIV_TITLE_MAP = [
    (r"under.?212|212.?bodybuilding",   'U212'),
    (r"under.?208|208.?bodybuilding",   'U208'),
    (r"women.?s.?bodybuilding",         'BB'),
    (r"bodybuilding",                   'OP'),
    (r"classic.?physique",              'CL'),
    (r"physique",                       'PH'),
    (r"figure",                         'FI'),
]

# Division title → outer overall code (same except bodybuilding → BB not OP)
OUTER_CODE_MAP = [
    (r"under.?212|212.?bodybuilding",   'U212'),
    (r"under.?208|208.?bodybuilding",   'U208'),
    (r"bodybuilding",                   'BB'),
    (r"classic.?physique",              'CL'),
    (r"physique",                       'PH'),
    (r"figure",                         'FI'),
]

# Slugs to skip in sub-class reset matching
# (excluded categories + markers that don't represent division boundaries)
SKIP_SLUG_RE = re.compile(
    r'^open$|overall|earned|comparison'
    r'|^novice$|^novice-|true-novice|-novice'
    r'|^beginner$|^beginner|^begginer'
    r'|^first-timer'
    r'|^regional$|^regional-|-regional'
    r'|^natural$|^natural-'
    r'|^local$|^local-'
    r'|^star-category$|^armed-forces$|^first-responder$|^mr-'
    r'|^\d+$',
    re.IGNORECASE
)

# Slugs that signal an overall winner (for overall-winner appending)
OVERALL_SLUG_RE = re.compile(r'overall', re.IGNORECASE)

# Code corrections: (gender, wrong_code, right_code, reason)
# Applied when the page confirms the division is present for that gender.
CODE_CORRECTIONS = [
    ('female', 'OP', 'BB', "Women's Bodybuilding should use BB, not OP"),
]


# ── Helpers ─────────────────────────────────────────────────────────────────

def getch():
    try:
        line = input().strip().lower()
        return line[0] if line else 'n'
    except EOFError:
        return 'q'


def filename_to_url(fname):
    base  = os.path.basename(fname).replace('.txt', '')
    parts = base.split('-')
    if len(parts) < 3:
        return None
    org       = parts[-2]
    year_name = '-'.join(parts[:-2])
    sep       = year_name.index('_')
    year      = year_name[:sep]
    name      = year_name[sep+1:]
    return f"{BASE_URL}/{year}/{org}_{name}"


def get_gender(fname):
    base = os.path.basename(fname)
    if '-male.txt' in base:   return 'male'
    if '-female.txt' in base: return 'female'
    return None


def fetch_page(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            page = resp.read().decode('utf-8', errors='replace')
        if page.count('data-slug') == 0:
            return None  # redirected to homepage — URL is wrong
        return page
    except Exception:
        return None


def clean_title(raw):
    return html_module.unescape(re.sub(r'<[^>]+>', '', raw)).strip().lower()


def title_gender(title_raw):
    """Return 'female', 'male', or None (ambiguous) for a division title."""
    t = clean_title(title_raw)
    if re.search(r'women|female|figure', t):
        return 'female'
    if re.search(r'\bmen\b|classic.?physique|under.?2[01][28]', t):
        return 'male'
    return None


def map_title(title_raw, code_map):
    t = clean_title(title_raw)
    for pattern, code in code_map:
        if re.search(pattern, t):
            return code
    return None


def raw_to_last_first(raw_name):
    """'First Last' → 'Last, First' (last word = last name)."""
    parts = raw_name.strip().split()
    if len(parts) <= 1:
        return raw_name
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


# ── Page parsing ─────────────────────────────────────────────────────────────

def iter_td_sections(page_html):
    """Yield (title_raw, section_html) for each division td on the page."""
    for td_m in re.finditer(
            r'<td class="[^"]*-td">(.*?)(?=<td class="|</tr\s*>)',
            page_html, re.DOTALL):
        section = td_m.group(1)
        title_m = re.search(r'<h2 class="division-title">(.*?)</h2>', section, re.DOTALL)
        if title_m:
            yield title_m.group(1), section


def parse_page_subclasses(page_html, gender=None):
    """
    Returns dict: div_code -> [slug, ...] (non-open/overall/novice slugs only).
    If gender is given, only includes divisions matching that gender.
    """
    result = {}
    for title_raw, section in iter_td_sections(page_html):
        if gender:
            tg = title_gender(title_raw)
            if tg and tg != gender:
                continue
        code = map_title(title_raw, DIV_TITLE_MAP)
        if not code:
            continue
        slugs = [
            m.group(1)
            for m in re.finditer(
                r'<div class="competitor-class[^"]*" data-slug="([^"]+)">', section)
            if not SKIP_SLUG_RE.search(m.group(1))
        ]
        if slugs:
            result.setdefault(code, []).extend(slugs)
    return result


def parse_overall_winners(page_html, gender):
    """
    Returns list of (code, last_first_name) for overall-winner entries
    relevant to this file's gender.
    Handles both division-level overalls (outer_code) and age-group overalls
    (masters-N-overall-winner-* → maps to age-group sub-code).
    """
    results = []
    for title_raw, section in iter_td_sections(page_html):
        tg = title_gender(title_raw)
        if tg and tg != gender:
            continue
        outer_code = map_title(title_raw, OUTER_CODE_MAP)
        if not outer_code:
            continue
        for slug_m in re.finditer(
                r'<div class="competitor-class[^"]*" data-slug="([^"]+)">', section):
            slug = slug_m.group(1)
            if not OVERALL_SLUG_RE.search(slug):
                continue
            # Determine which code this overall belongs to
            code = outer_code  # default: division-level overall
            age_m = re.match(r'^masters-(\d+)-overall', slug, re.IGNORECASE)
            if age_m:
                age = int(age_m.group(1))
                age_code = MASTERS_AGE_CODES.get(outer_code, {}).get(age)
                if not age_code:
                    continue  # age group not mapped for this division, skip
                code = age_code
            athlete_m = re.search(
                r'data-parent="' + re.escape(slug) + r'"[^>]*>.*?<span>[^<]*</span>\s*([^<\n]+)',
                section, re.DOTALL)
            if athlete_m:
                raw = html_module.unescape(athlete_m.group(1)).strip()
                results.append((code, raw_to_last_first(raw)))
    return results


def page_has_women_bb(page_html):
    """Return True if the page has a Women's Bodybuilding division."""
    for title_raw, _ in iter_td_sections(page_html):
        if re.search(r"women.?s.?bodybuilding", clean_title(title_raw)):
            return True
    return False


# ── Code corrections ──────────────────────────────────────────────────────────

def detect_code_corrections(lines, page_html, gender):
    """
    Return list of (old_code, new_code, reason) for c-codes in the file that
    need to be corrected based on gender and page content.
    """
    if not gender:
        return []
    file_codes = {
        m.group(1)
        for line in lines
        for m in [re.match(r'^c (\S+)', line.rstrip())]
        if m
    }
    corrections = []
    for corr_gender, wrong, right, reason in CODE_CORRECTIONS:
        if gender == corr_gender and wrong in file_codes:
            # Confirm the page actually has the right division
            if wrong == 'OP' and right == 'BB' and page_has_women_bb(page_html):
                corrections.append((wrong, right, reason))
    return corrections


def apply_corrections(lines, corrections):
    """Replace 'c OLD' with 'c NEW' throughout the file."""
    lookup = {old: new for old, new, _ in corrections}
    result = []
    for line in lines:
        s = line.rstrip()
        if s.startswith('c '):
            code = s[2:].strip()
            if code in lookup:
                result.append(f'c {lookup[code]}\n')
                continue
        result.append(line)
    return result


# ── Reset detection and sub-division insertion ────────────────────────────────

def find_resets(lines):
    """Return list of (line_index, div_code) where placing resets to 1 after going higher."""
    resets      = []
    current_div = None
    last_placing = 0
    for i, line in enumerate(lines):
        s = line.rstrip()
        if s.startswith('c '):
            current_div  = s[2:].strip()
            last_placing = 0
        elif s == '----':
            last_placing = 0
        else:
            m = re.match(r'^@?(\d+)\s+', s)
            if m:
                p = int(m.group(1))
                if p == 1 and last_placing > 1:
                    resets.append((i, current_div))
                if p != 98:
                    last_placing = p
    return resets


def build_insertions(resets, page_subclasses):
    by_div = {}
    for line_idx, div_code in resets:
        by_div.setdefault(div_code, []).append(line_idx)

    insertions = []
    for div_code, line_indices in by_div.items():
        page_slugs = page_subclasses.get(div_code, [])
        if not page_slugs:
            # No sub-classes on page for this division → resets are out-of-order
            # placings (false positives), not missing sub-class boundaries.
            continue
        for i, line_idx in enumerate(line_indices):
            slug = page_slugs[i] if i < len(page_slugs) else '?'
            if slug == '?':
                new_code = None
            else:
                new_code = slug_to_code(slug, div_code)  # raises ValueError on unknown
            insertions.append((line_idx, new_code, slug, div_code))

    insertions.sort(key=lambda x: x[0])
    return insertions


def apply_insertions(lines, insertions):
    offset = 0
    for line_idx, new_code, slug, div_code in insertions:
        if new_code is None:
            continue
        lines.insert(line_idx + offset, f'c {new_code}\n')
        offset += 1
    return lines


# ── Overall-winner already-present check ──────────────────────────────────────

def overall_already_in_file(lines, outer_code, last_first):
    last_name  = last_first.split(',')[0].strip().lower()
    in_section = False
    for line in lines:
        s = line.rstrip()
        if s == f'c {outer_code}':
            in_section = True
        elif s.startswith('c ') and in_section:
            in_section = False
        elif in_section and re.match(r'^0\s+', s):
            if last_name in s.lower():
                return True
    return False


# ── Main per-file logic ───────────────────────────────────────────────────────

def process_file(fpath, auto=False, check_overall=False, override_url=None):
    fname  = os.path.basename(fpath)
    gender = get_gender(fname)

    with open(fpath) as f:
        lines = f.readlines()

    resets = find_resets(lines)
    if not resets and not check_overall:
        return 'skipped'

    url = override_url or filename_to_url(fname)
    if not url:
        print(f"\n  !! Cannot derive URL for {fname}")
        return 'error'

    print(f"\n{'='*70}")
    print(f"File  : {fname}")
    print(f"URL   : {url}")
    print(f"Fetch...", end='', flush=True)
    page = fetch_page(url)
    if not page:
        print(" FAILED (no data-slug content — URL may be wrong or page unavailable)")
        return 'error'
    print(" OK")

    page_subclasses = parse_page_subclasses(page, gender)
    try:
        insertions = build_insertions(resets, page_subclasses)
    except ValueError as e:
        print(f"\n  !! UNKNOWN SLUG — cannot continue: {e}")
        return 'error'
    corrections = detect_code_corrections(lines, page, gender)

    appends = []
    if check_overall and gender:
        for outer_code, last_first in parse_overall_winners(page, gender):
            if not overall_already_in_file(lines, outer_code, last_first):
                appends.append((outer_code, last_first))

    if not insertions and not corrections and not appends:
        print("  (nothing to change)")
        return 'skipped'

    # ── Display proposals ──
    has_unknown = False

    if corrections:
        print(f"\nCode corrections ({len(corrections)}):")
        for old, new, reason in corrections:
            print(f"  c {old}  →  c {new}   ({reason})")

    if insertions:
        print(f"\nSub-division insertions ({len(insertions)}):")
        for line_idx, new_code, slug, div_code in insertions:
            ctx = lines[line_idx].rstrip() if line_idx < len(lines) else '(EOF)'
            if new_code:
                print(f"  Before line {line_idx+1:4d}  [{div_code}] {slug!r:32s} → c {new_code}")
                print(f"    context: {ctx}")
            else:
                has_unknown = True
                print(f"  Before line {line_idx+1:4d}  [{div_code}] {slug!r:32s} → !! UNKNOWN CODE")
                print(f"    context: {ctx}")

    if appends:
        print(f"\nOverall-winner appends ({len(appends)}):")
        for outer_code, last_first in appends:
            print(f"  c {outer_code}")
            print(f"  0 {last_first}")

    if has_unknown:
        print("\n  WARNING: Unknown codes will be skipped — fix manually afterward.")

    if auto:
        do_apply = True
    else:
        print(f"\n  [y] Apply  [n] Skip  [q] Quit all", end='  ', flush=True)
        ch = getch()
        print(ch)
        if ch.lower() == 'q':
            return 'quit'
        do_apply = (ch.lower() == 'y')

    if do_apply:
        new_lines = apply_corrections(list(lines), corrections)
        new_lines = apply_insertions(new_lines, insertions)
        for outer_code, last_first in appends:
            new_lines.append(f'c {outer_code}\n')
            new_lines.append(f'0 {last_first}\n')
        with open(fpath, 'w') as f:
            f.writelines(new_lines)
        n = (len(corrections) + sum(1 for _, c, _, _ in insertions if c) +
             len(appends) * 2)
        print(f"  → Written ({n} changes)")
        return 'fixed'
    else:
        print("  → Skipped")
        return 'skipped'


# ── Entry point ───────────────────────────────────────────────────────────────

def collect_files(args):
    if not args:
        return sorted(glob.glob(os.path.join(SRC, '*.txt')))
    files = []
    for arg in args:
        matches = (glob.glob(arg) if os.path.isabs(arg)
                   else glob.glob(os.path.join(SRC, arg)) or glob.glob(arg))
        files.extend(matches)
    return sorted(set(files))


def main():
    args          = sys.argv[1:]
    auto          = '--auto'    in args
    check_overall = '--overall' in args
    # --url URL (optional, only used when processing a single file)
    override_url  = None
    new_args = []
    i = 0
    while i < len(args):
        if args[i] == '--url' and i + 1 < len(args):
            override_url = args[i + 1]
            i += 2
        elif args[i].startswith('--'):
            i += 1  # skip other flags
        else:
            new_args.append(args[i])
            i += 1
    args = new_args

    files = collect_files(args)
    if not files:
        print("No files found.")
        sys.exit(1)

    if override_url and len(files) > 1:
        print("Warning: --url only applies to single-file processing; ignoring for batch.")
        override_url = None

    flags = (['AUTO'] if auto else []) + (['+OVERALL'] if check_overall else [])
    print(f"Processing {len(files)} file(s)  [{' '.join(flags) or 'INTERACTIVE'}]")

    counts = {'fixed': 0, 'skipped': 0, 'error': 0}
    for fpath in files:
        url = override_url if (override_url and len(files) == 1) else None
        result = process_file(fpath, auto=auto, check_overall=check_overall, override_url=url)
        if result == 'quit':
            print("\nStopped by user.")
            break
        counts[result] = counts.get(result, 0) + 1

    print(f"\nDone — fixed: {counts['fixed']}, skipped: {counts['skipped']}, "
          f"errors: {counts['error']}")


if __name__ == '__main__':
    main()
