"""
Find contests entered twice under different names by comparing athlete results.
"""
import sys
from collections import defaultdict

DATA_FILES = [
    '/Users/timfogarty/workspace/musmem/data/bb_male.dat',
    '/Users/timfogarty/workspace/musmem/data/bb_female.dat',
    '/Users/timfogarty/workspace/musmem/data/prelim/covid-male.dat',
    '/Users/timfogarty/workspace/musmem/data/prelim/covid-female.dat',
    '/Users/timfogarty/workspace/musmem/data/prelim/gap-male.dat',
    '/Users/timfogarty/workspace/musmem/data/prelim/gap-female.dat',
]

SKIP_PLACEMENTS = {98, 0}


def parse_record(line):
    line = line.strip()
    if not line:
        return None
    parts = [p.strip() for p in line.split(';')]
    if len(parts) < 4:
        return None
    name, year, contest, div_place = parts[0], parts[1], parts[2], parts[3]
    if not div_place:
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


def load_contests():
    # contests[(year, contest)][division][placement] = [name, ...]
    contests = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    total = 0
    for path in DATA_FILES:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                rec = parse_record(line)
                if rec is None:
                    continue
                name, year, contest, division, placement = rec
                if placement in SKIP_PLACEMENTS:
                    continue
                contests[(year, contest)][division][placement].append(name)
                total += 1
    print(f"Loaded {total:,} athlete-contest records", file=sys.stderr)
    return contests


def check_pair(a_divs, b_divs):
    """
    Return (method, match_count) if duplicate, else None.

    Method 1: shared named divisions >= 4, compare 1st-place athletes.
    Method 2: shared named divisions < 4, compare top-4 athletes in a single division.
    """
    a_named = {d for d in a_divs if d != 'OPEN'}
    b_named = {d for d in b_divs if d != 'OPEN'}
    shared_named = a_named & b_named

    if len(shared_named) >= 4:
        # Stage 1: find divisions where 1st place matches (need >= 4)
        match1 = [d for d in shared_named
                  if set(a_divs[d].get(1, [])) & set(b_divs[d].get(1, []))]
        if len(match1) >= 4:
            # Stage 2: of those, find where 2nd place also matches (need >= 2)
            match2 = [d for d in match1
                      if set(a_divs[d].get(2, [])) & set(b_divs[d].get(2, []))]
            if len(match2) >= 2:
                # Stage 3: of those, find where 3rd place also matches (need >= 2)
                match3 = [d for d in match2
                          if set(a_divs[d].get(3, [])) & set(b_divs[d].get(3, []))]
                if len(match3) >= 2:
                    return 'method1', len(match1)
    else:
        # Method 2: check if top-4 athletes match in any shared division
        # Include OPEN if present in both
        shared_divs = shared_named | (set(a_divs.keys()) & set(b_divs.keys()) & {'OPEN'})
        for div in shared_divs:
            a_places = sorted(a_divs[div].keys())
            b_places = sorted(b_divs[div].keys())
            # Stage 1: top-4 placements must exist and match in both contests
            a_top4 = a_places[:4]
            b_top4 = b_places[:4]
            if len(a_top4) < 4 or len(b_top4) < 4:
                continue
            if a_top4 != b_top4:
                continue
            if not all(
                set(a_divs[div][p]) & set(b_divs[div][p])
                for p in a_top4
            ):
                continue
            # Stage 2: of places 5-8, require >= 2 to match (if either contest
            # has athletes there; skip check only if both fields end at place 4)
            places_5_8 = [p for p in sorted(set(a_places) | set(b_places))
                          if p not in a_top4 and p <= 8]
            if places_5_8:
                deeper_matches = sum(
                    1 for p in places_5_8
                    if p in a_divs[div] and p in b_divs[div]
                    and set(a_divs[div][p]) & set(b_divs[div][p])
                )
                if deeper_matches < 2:
                    continue
            return f'method2({div})', 4

    return None


def main():
    contests = load_contests()

    # Group contest names by year
    by_year = defaultdict(list)
    for year, contest in contests:
        by_year[year].append(contest)

    duplicates = []
    for year in sorted(by_year):
        names = sorted(by_year[year])
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = names[i], names[j]
                result = check_pair(contests[(year, a)], contests[(year, b)])
                if result:
                    method, count = result
                    duplicates.append((year, a, b, method, count))

    if duplicates:
        print(f"\n{'='*70}")
        print(f"CANDIDATE DUPLICATE CONTESTS ({len(duplicates)} pairs)")
        print(f"{'='*70}")
        for year, a, b, method, count in duplicates:
            print(f"{year}: '{a}'")
            print(f"      '{b}'")
            print(f"      [{method}, {count} matching athletes]")
            print()
    else:
        print("\nNo duplicate contest candidates found.")

    print(f"Total pairs found: {len(duplicates)}")


if __name__ == '__main__':
    main()
