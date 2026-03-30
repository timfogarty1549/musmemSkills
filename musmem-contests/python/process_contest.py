#!/usr/bin/env python3
"""
Process a single npcnewsonline.com contest HTML file into flat file(s) for format.php.
Usage: python3 process_contest.py <slug> <"Display Name">
HTML is read from /tmp/contest.html (pre-downloaded by curl).
Org is inferred from the display name prefix (IFBB, NPC, NPC Worldwide, CPA).
"""
import html as htmllib
import os
import re
import sys

YEAR = int(os.environ.get('CONTEST_YEAR', 2024))
OUTPUT_DIR = os.path.expanduser('~/workspace/musmem/1-incoming')

ORG_PREFIXES = [
    ('NPC Worldwide ', 'NPC Worldwide'),
    ('IFBB ', 'IFBB'),
    ('NPC ', 'NPC'),
    ('CPA ', 'CPA'),
]

SKIP_HEADINGS = {
    'BIKINI', "WOMEN'S BIKINI", 'WELLNESS', "WOMEN'S WELLNESS",
    'FITNESS', "WOMEN'S FITNESS", 'FIT MODEL', "WOMEN'S FIT MODEL",
}

# Maps npcnewsonline.com URL slugs to neutral age/category identifiers.
# These are lookup keys only — not division codes.
SLUG_MAP = {
    'open':       'open',
    'overall':    'overall',
    'under-212':  'u212',
    'under-208':  'u208',
    'masters-35': 'age35',
    'masters-40': 'age40',
    'masters-45': 'age45',
    'masters-50': 'age50',
    'masters-55': 'age55',
    'masters-60': 'age60',
    'masters-65': 'age65',
    'masters-70': 'age70',
    'masters-80': 'age80',
    'masters-90': 'age90',
    'teen':       'teen',
    'junior':     'junior',
    'wheelchair': 'wheelchair',
}


def detect_org(display_name):
    for prefix, org in ORG_PREFIXES:
        if display_name.startswith(prefix):
            return org
    return 'IFBB'


def classify(heading, sub_slug):
    """Return (code, gender) or ('', 'skip') or ('', 'unknown')."""
    h = heading.upper().strip()
    s = sub_slug.lower().strip()
    suffix = SLUG_MAP.get(s)

    # Skip categories
    if h in SKIP_HEADINGS or 'BIKINI' in h or 'WELLNESS' in h or 'FIT MODEL' in h:
        return ('', 'skip')
    if 'FITNESS' in h and 'CLASSIC' not in h:
        return ('', 'skip')

    if suffix is None:
        return ('', 'unknown')

    # 212 / 208 as standalone division headings
    if h in ('212', 'UNDER 212', '212 BODYBUILDING', 'UNDER-212'):
        return ('U212', 'male')
    if h in ('208', 'UNDER 208', '208 BODYBUILDING'):
        return ('U208', 'male')

    # BODYBUILDING (male)
    if h in ("MEN'S BODYBUILDING", 'BODYBUILDING', 'OPEN BODYBUILDING', 'MEN BODYBUILDING'):
        codes = {
            'open': 'OP', 'u212': 'U212', 'u208': 'U208',
            'age35': 'M3', 'age40': 'M4', 'age45': '45',
            'age50': 'M5', 'age55': '55', 'age60': 'M6',
            'age65': 'm6', 'age70': 'M7', 'age80': 'M8', 'age90': 'M8',
            'teen': 'TE', 'junior': 'JR', 'wheelchair': 'WC', 'overall': 'OV',
        }
        code = codes.get(suffix)
        return (code, 'male') if code else ('', 'unknown')

    # CLASSIC PHYSIQUE (male)
    if h in ("MEN'S CLASSIC PHYSIQUE", 'CLASSIC PHYSIQUE', 'CLASSIC'):
        codes = {
            'open': 'CL', 'age35': 'c3', 'age40': 'c4', 'age45': 'c45',
            'age50': 'c5', 'age55': 'c55', 'age60': 'c6',
            'teen': 'ct', 'junior': 'CJ', 'overall': 'OV',
        }
        code = codes.get(suffix)
        return (code, 'male') if code else ('', 'unknown')

    # MEN'S PHYSIQUE (male)
    if h in ("MEN'S PHYSIQUE", 'PHYSIQUE', 'OPEN PHYSIQUE', 'MEN PHYSIQUE'):
        codes = {
            'open': 'PH', 'age35': 'P35', 'age40': 'P4', 'age45': 'P45',
            'age50': 'P5', 'age55': 'P55', 'age60': 'P6', 'age70': 'P7',
            'teen': 'PT', 'junior': 'PJ', 'overall': 'OV',
        }
        code = codes.get(suffix)
        return (code, 'male') if code else ('', 'unknown')

    # WHEELCHAIR (male)
    if 'WHEELCHAIR' in h:
        return ('WC', 'male')

    # WOMEN'S BODYBUILDING (female)
    if h in ("WOMEN'S BODYBUILDING", 'WOMEN BODYBUILDING', 'WOMENS BODYBUILDING'):
        codes = {
            'open': 'BB', 'age40': 'M4', 'age45': '45', 'age50': 'M5',
            'age55': '55', 'age60': 'M6', 'age65': 'm6',
            'age70': 'M7', 'age80': 'M8', 'overall': 'OV',
        }
        code = codes.get(suffix)
        return (code, 'female') if code else ('', 'unknown')

    # FIGURE (female)
    if h in ('FIGURE', "WOMEN'S FIGURE", 'WOMEN FIGURE'):
        codes = {
            'open': 'FI', 'age35': 'f3', 'age40': 'F4', 'age45': 'f4',
            'age50': 'F5', 'age55': 'f5', 'age60': 'F6',
            'teen': 'FT', 'junior': 'FJ', 'overall': 'OV',
        }
        code = codes.get(suffix)
        return (code, 'female') if code else ('', 'unknown')

    # WOMEN'S PHYSIQUE (female)
    if h in ("WOMEN'S PHYSIQUE", 'WOMENS PHYSIQUE', 'WOMEN PHYSIQUE'):
        codes = {
            'open': 'PH', 'age35': 'P35', 'age40': 'P4', 'age45': 'P45',
            'age50': 'P5', 'age55': 'P55', 'age60': 'P6', 'age70': 'P7',
            'overall': 'OV',
        }
        code = codes.get(suffix)
        return (code, 'female') if code else ('', 'unknown')

    # Overall
    if h == 'OVERALL':
        return ('OV', 'male')
    if h in ("WOMEN'S OVERALL", 'WOMENS OVERALL'):
        return ('OV', 'female')

    return ('', 'unknown')


def apply_tied_last(entries):
    if not entries:
        return entries
    max_place = max(p for p, _ in entries)
    if [p for p, _ in entries].count(max_place) > 1:
        return [(98 if p == max_place else p, n) for p, n in entries]
    return entries


def normalize_title(display_name, org):
    name = htmllib.unescape(display_name).strip()
    prefix = org + ' '
    if name.startswith(prefix):
        name = name[len(prefix):]
    if name == 'Mr Olympia':
        name = 'Olympia'
    name = re.sub(r'  +', ' ', name)
    return f'{name} - {org}'


def title_to_filebase(title, org):
    name = title.replace(f' - {org}', '').strip().lower()
    name = re.sub(r'[\s]+', '_', name)
    name = re.sub(r'[^\w]', '', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name


def parse_html(content):
    """Return list of (heading, sub_slug, [(placing, name)])."""
    h2_pat = re.compile(r'<h2[^>]*division-title[^>]*>(.*?)</h2>', re.DOTALL)
    h2_matches = list(h2_pat.finditer(content))
    results = []

    for i, h2 in enumerate(h2_matches):
        heading = htmllib.unescape(re.sub(r'<[^>]+>', '', h2.group(1)).strip())
        start = h2.end()
        end = h2_matches[i+1].start() if i+1 < len(h2_matches) else len(content)
        section = content[start:end]

        slug_matches = list(re.finditer(r'data-slug="([^"]+)"', section))
        if not slug_matches:
            continue

        for sm in slug_matches:
            sub_slug = sm.group(1)
            pat = re.compile(
                r'data-parent="' + re.escape(sub_slug) + r'"[^>]*>\s*<span>\s*(\d+)\s*</span>\s*([^<]+)',
                re.DOTALL
            )
            competitors = []
            for m in pat.finditer(section):
                placing = int(m.group(1))
                name = htmllib.unescape(m.group(2).strip())
                competitors.append((placing, name))
            if competitors:
                competitors = apply_tied_last(competitors)
                results.append((heading, sub_slug, competitors))

    return results


def write_file(filepath, title, divs):
    lines = [f'y {YEAR}', f't {title}']
    for i, (code, competitors) in enumerate(divs):
        if i > 0:
            lines.append('----')
        lines.append(f'c {code}')
        for placing, name in competitors:
            lines.append(f'{placing} {name}')
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <slug> <display_name>", file=sys.stderr)
        sys.exit(1)

    slug = sys.argv[1]
    display_name = sys.argv[2]

    org = detect_org(display_name)
    org_slug = org.lower().replace(' ', '_')

    with open('/tmp/contest.html', encoding='utf-8', errors='replace') as f:
        content = f.read()

    title = normalize_title(display_name, org)
    filebase = title_to_filebase(title, org)
    parsed = parse_html(content)

    if not parsed:
        print(f"  {title}: NO DIVISIONS FOUND")
        return

    male_divs, female_divs = [], []
    unknown_divs, skipped = [], []

    for heading, sub_slug, comps in parsed:
        code, gender = classify(heading, sub_slug)
        if gender == 'skip':
            skipped.append(f'{heading}/{sub_slug}')
        elif not code or gender == 'unknown':
            unknown_divs.append((heading, sub_slug, len(comps)))
        elif gender == 'male':
            male_divs.append((code, comps))
        elif gender == 'female':
            female_divs.append((code, comps))

    for h, s, n in unknown_divs:
        print(f"  UNKNOWN: {title} — {h}/{s} ({n} athletes)")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if male_divs:
        fname = f'{YEAR}_{filebase}-{org_slug}-male.txt'
        write_file(os.path.join(OUTPUT_DIR, fname), title, male_divs)
        total = sum(len(c) for _, c in male_divs)
        print(f"  MALE:   {fname} ({len(male_divs)} div{'s' if len(male_divs) != 1 else ''}, {total} entries)")

    if female_divs:
        fname = f'{YEAR}_{filebase}-{org_slug}-female.txt'
        write_file(os.path.join(OUTPUT_DIR, fname), title, female_divs)
        total = sum(len(c) for _, c in female_divs)
        print(f"  FEMALE: {fname} ({len(female_divs)} div{'s' if len(female_divs) != 1 else ''}, {total} entries)")

    if not male_divs and not female_divs:
        print(f"  {title}: no output written (skipped: {skipped}, unknown: {[(h,s) for h,s,_ in unknown_divs]})")


if __name__ == '__main__':
    main()
