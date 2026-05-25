"""
Detect bodybuilding contest divisions with mislabeled placements.

A mislabeled division occurs when athletes from two different classes are
merged under one division label, producing duplicate placements (two athletes
at 1st, two at 2nd, etc.). This is distinct from a valid tie, where duplicate
placements only appear at the last position (no P+1 exists).

Detection rule: for each (year, contest, division) group, if placement P
appears more than once AND placement P+1 also exists in the group, flag it.
Placements >= 90 are excluded (98=DNP, 99=DQ, other 9x=special).
"""

import sys
import argparse
from collections import defaultdict, Counter
from pathlib import Path

DATA_DIR = Path('/Users/timfogarty/workspace/musmem/data')

CONTEST_FILES = [
    (DATA_DIR / 'bb_male.dat',                       'male',   'main'),
    (DATA_DIR / 'bb_female.dat',                     'female', 'main'),
    (DATA_DIR / 'prelim' / 'covid-male.dat',         'male',   'prelim'),
    (DATA_DIR / 'prelim' / 'covid-female.dat',       'female', 'prelim'),
    (DATA_DIR / 'prelim' / 'gap-male.dat',           'male',   'prelim'),
    (DATA_DIR / 'prelim' / 'gap-female.dat',         'female', 'prelim'),
    (DATA_DIR / 'prelim' / 'npc-male.dat',           'male',   'prelim'),
    (DATA_DIR / 'prelim' / 'npc-female.dat',         'female', 'prelim'),
    (DATA_DIR / 'prelim' / 'legion.dat',             'mixed',  'prelim'),
    (DATA_DIR / 'prelim' / 'legion21.dat',           'mixed',  'prelim'),
    (DATA_DIR / 'prelim' / 'unknown-emerald-male.dat',   'male',   'prelim'),
    (DATA_DIR / 'prelim' / 'unknown-emerald-female.dat', 'female', 'prelim'),
]

SPECIAL_PLACEMENT_THRESHOLD = 90


def parse_record(line):
    """Parse one .dat line. Returns (name, year, contest, division, placement) or None."""
    line = line.strip()
    if not line:
        return None
    parts = [p.strip() for p in line.split(';')]
    if len(parts) < 4 or not parts[3]:
        return None
    name, year, contest, div_place = parts[0], parts[1], parts[2], parts[3]
    if not name or not year or not contest:
        return None

    if '-' in div_place:
        hyphen = div_place.rfind('-')
        division = div_place[:hyphen]
        try:
            placement = int(div_place[hyphen + 1:])
        except ValueError:
            return None
    else:
        division = 'OPEN'
        try:
            placement = int(div_place)
        except ValueError:
            return None

    return name, year, contest, division, placement


def load_groups(path):
    """Load a .dat file and return grouped records.

    Returns dict: (year, contest, division) -> list of (name, placement).
    """
    groups = defaultdict(list)
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            rec = parse_record(line)
            if rec is None:
                continue
            name, year, contest, division, placement = rec
            if placement >= SPECIAL_PLACEMENT_THRESHOLD:
                continue
            groups[(year, contest, division)].append((name, placement))
    return groups


def detect_suspicious(groups):
    """Find groups with mislabeled placements.

    Returns list of dicts with keys: year, contest, division, athletes,
    suspicious_placements, severity.
    """
    results = []
    for (year, contest, division), athletes in groups.items():
        placements = [p for _, p in athletes]
        counts = Counter(placements)
        duplicates = {p for p, c in counts.items() if c > 1}
        # A duplicate at P is only suspicious if P+1 also exists (not a tie)
        suspicious = sorted(p for p in duplicates if (p + 1) in counts)
        if not suspicious:
            continue

        n = len(suspicious)
        if n >= 3:
            severity = 'HIGH'
        elif n == 2:
            severity = 'MED'
        else:
            severity = 'LOW'

        results.append({
            'year': year,
            'contest': contest,
            'division': division,
            'athletes': athletes,
            'suspicious_placements': suspicious,
            'severity': severity,
            'counts': counts,
        })
    return results


def severity_rank(s):
    return {'HIGH': 0, 'MED': 1, 'LOW': 2}[s]


def print_results(all_results, filter_file=None, filter_contest=None, filter_year=None):
    severity_order = {'HIGH': 0, 'MED': 1, 'LOW': 2}
    sorted_results = sorted(
        all_results,
        key=lambda r: (severity_rank(r['severity']), -int(r['year']) if r['year'].isdigit() else 0)
    )

    total = len(sorted_results)
    if total == 0:
        print("No suspicious divisions found.")
        return

    counts_by_severity = Counter(r['severity'] for r in sorted_results)
    print(f"Found {total} suspicious division(s): "
          f"{counts_by_severity.get('HIGH', 0)} HIGH, "
          f"{counts_by_severity.get('MED', 0)} MED, "
          f"{counts_by_severity.get('LOW', 0)} LOW\n")

    for r in sorted_results:
        filename = r['file'].name
        print(f"[{r['severity']}] {r['year']} {r['contest']} | Division: {r['division']} | {filename}")

        # Group athletes by placement for display
        by_place = defaultdict(list)
        for name, p in r['athletes']:
            by_place[p].append(name)

        max_place = max(by_place.keys()) if by_place else 0
        for p in range(1, max_place + 1):
            names = by_place.get(p, [])
            if len(names) == 1:
                continue
            marker = ' *' if p in r['suspicious_placements'] else ''
            if len(names) == 0:
                print(f"  P{p} (×0): [missing]")
            else:
                print(f"  P{p} (×{len(names)}): {'; '.join(names)}{marker}")

        print()


def main():
    parser = argparse.ArgumentParser(description='Detect mislabeled contest divisions in MuscleMemory .dat files')
    parser.add_argument('--file', help='Filter by filename (e.g. bb_male.dat)')
    parser.add_argument('--contest', help='Filter by contest name substring')
    parser.add_argument('--year', help='Filter by year')
    args = parser.parse_args()

    all_results = []
    for path, gender, tier in CONTEST_FILES:
        if not path.exists():
            continue
        if args.file and args.file not in path.name:
            continue
        groups = load_groups(path)
        suspicious = detect_suspicious(groups)
        for r in suspicious:
            if args.contest and args.contest.lower() not in r['contest'].lower():
                continue
            if args.year and r['year'] != args.year:
                continue
            r['file'] = path
            r['gender'] = gender
            all_results.append(r)

    print_results(all_results)


if __name__ == '__main__':
    main()
