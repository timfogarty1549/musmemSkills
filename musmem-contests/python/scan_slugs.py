#!/usr/bin/env python3
"""Dry-run scan: fetch all contest pages and collect unknown slugs.
Does NOT write any files. Reports all unknowns grouped by slug+context.
Pages are cached to ~/workspace/musmem/.page_cache/ and reused on subsequent runs.

Usage:
    python3 scan_slugs.py              # all contests
    python3 scan_slugs.py '*2021*'     # glob pattern
    python3 scan_slugs.py --start 50  # skip first N
    python3 scan_slugs.py --no-cache  # force re-fetch (ignore cache)
"""
import sys, os, re, gzip, html as h, urllib.request, glob as glob_module
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fix_subdivisions import slug_to_code, SKIP_SLUG_RE

SRC   = os.path.expanduser('~/workspace/musmem/2-normalize-athletes')
CACHE = os.path.expanduser('~/workspace/musmem/.page_cache')
BASE  = 'https://contests.npcnewsonline.com/contests'
UA    = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

DIV_TITLE_MAP = [
    (r'under.?212|212.?bodybuilding',       'U212', 'male'),
    (r'under.?208|208.?bodybuilding',       'U208', 'male'),
    (r"women.?s.?bodybuilding",             'BB',   'female'),
    (r"men.?s.?bodybuilding|^bodybuilding", 'OP',   'male'),
    (r"men.?s.?classic|classic.?physique",  'CL',   'male'),
    (r"women.?s.?physique",                 'PH',   'female'),
    (r"men.?s.?physique|^physique",         'PH',   'male'),
    (r"figure",                             'FI',   'female'),
]

LISTING_SLUG = {'npc_worldwide': 'npcw', 'ifbb': 'ifbb'}

USE_CACHE = True  # set to False via --no-cache flag


def _cache_path(url):
    path = url.replace('https://contests.npcnewsonline.com/contests/', '')
    safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', path)
    return os.path.join(CACHE, safe + '.html')


def fetch(url):
    """Fetch URL, reading from disk cache if available, writing to cache on miss."""
    os.makedirs(CACHE, exist_ok=True)
    cpath = _cache_path(url)
    if USE_CACHE and os.path.exists(cpath):
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
    try:
        page = fetch(url)
        return page if page.count('data-slug') > 0 else None
    except Exception:
        return None


def clean(raw):
    return h.unescape(re.sub(r'<[^>]+>', '', raw)).strip()


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


def make_url(year, slug, org):
    if org == 'npc_worldwide':
        return f"{BASE}/{year}/npc_worldwide_{slug}"
    elif org == 'ifbb':
        return f"{BASE}/{year}/{slug}"
    raise ValueError(f"Unknown org: {org!r}")


def find_url_from_listing(year, slug, org):
    listing_slug = LISTING_SLUG.get(org)
    if not listing_slug:
        return None
    try:
        page = fetch(f"{BASE}/{year}/{listing_slug}")
    except Exception:
        return None
    all_urls = re.findall(rf'href="({re.escape(BASE)}/{year}/[^"]+)"', page)
    slug_tokens = set(slug.split('_'))
    best_url, best_score = None, 0
    for url in all_urls:
        url_slug = url.split('/')[-1]
        if org == 'npc_worldwide' and url_slug.startswith('npc_worldwide_'):
            url_slug = url_slug[len('npc_worldwide_'):]
        overlap = len(slug_tokens & set(url_slug.split('_')))
        if overlap > best_score:
            best_score, best_url = overlap, url
    return best_url if best_url and best_score >= 2 else None


def parse_filename(fname):
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
    pat = os.path.join(SRC, pattern if pattern else '*.txt')
    files = sorted(glob_module.glob(pat))
    files = [f for f in files
             if '-nac-' not in os.path.basename(f)
             and os.path.basename(f).endswith('.txt')
             and not re.search(r'\.txt-\d+$', os.path.basename(f))]
    contests = {}
    for fpath in files:
        parsed = parse_filename(os.path.basename(fpath))
        if not parsed:
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


def scan_page(page, year, contest_label):
    """Scan all non-skipped slugs and return list of (slug, div_code, contest_label)
    for any that raise ValueError in slug_to_code."""
    unknowns = []
    for div_title, section in iter_sections(page):
        div_code, _ = map_title(div_title)
        if not div_code:
            continue
        for cls_m in re.finditer(
                r'<div class="competitor-class[^"]*" data-slug="([^"]+)">', section):
            slug = cls_m.group(1)
            if re.search(r'^overall', slug, re.I):
                continue
            if slug.lower() == 'open':
                continue
            if SKIP_SLUG_RE.search(slug):
                continue
            try:
                slug_to_code(slug, div_code)
            except ValueError:
                unknowns.append((slug, div_code, contest_label))
    return unknowns


def main():
    global USE_CACHE
    args = sys.argv[1:]
    pattern, start = None, 0
    i = 0
    while i < len(args):
        if args[i] == '--start' and i + 1 < len(args):
            start = int(args[i + 1]); i += 2
        elif args[i] == '--no-cache':
            USE_CACHE = False; i += 1
        else:
            pattern = args[i]; i += 1

    contests = collect_contests(pattern)
    total = len(contests)
    cache_note = '' if USE_CACHE else ' (cache disabled)'
    print(f"Scanning {total} contests (from #{start+1}){cache_note}...\n")

    unknowns = defaultdict(list)
    fetch_errors = []

    for num, contest in enumerate(contests[start:], start=start + 1):
        year, slug, org = contest['year'], contest['slug'], contest['org']
        title = contest['title'] or f"??? - {org}"
        label = f"{title} ({year})"

        print(f"[{num}/{total}] {label}", end=' ... ', flush=True)

        try:
            url = make_url(year, slug, org)
        except ValueError as e:
            print(f"URL ERROR: {e}")
            fetch_errors.append(label)
            continue

        page = try_fetch(url)
        if page is None:
            url2 = find_url_from_listing(year, slug, org)
            if url2:
                page = try_fetch(url2)
        if page is None:
            print("FETCH FAILED")
            fetch_errors.append(label)
            continue

        found = scan_page(page, year, label)
        if found:
            for s, dc, lbl in found:
                unknowns[(s, dc)].append(lbl)
            print(f"{len(found)} unknown(s)")
        else:
            print("OK")

    print(f"\n{'='*60}")
    if unknowns:
        print(f"UNKNOWN SLUGS ({len(unknowns)} distinct):\n")
        for (slug, div_code), labels in sorted(unknowns.items()):
            print(f"  slug={slug!r}  div={div_code}  ({len(labels)} contest(s))")
            for lbl in labels[:3]:
                print(f"    {lbl}")
            if len(labels) > 3:
                print(f"    ... and {len(labels)-3} more")
    else:
        print("No unknown slugs found.")

    if fetch_errors:
        print(f"\nFETCH ERRORS ({len(fetch_errors)}):")
        for e in fetch_errors:
            print(f"  {e}")


if __name__ == '__main__':
    main()
