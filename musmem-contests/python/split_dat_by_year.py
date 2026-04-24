#!/usr/bin/env python3
"""Split bb_male.dat or bb_female.dat into year-range chunks.

Output files: {base}-1.dat (pre-1980), -2 (1980-1999), -3 (2000-2009), -4 (2010-2019), -5 (2020+)
"""

import sys
import os

def year_to_suffix(year):
    if year < 1980:
        return 1
    elif year <= 1999:
        return 2
    elif year <= 2009:
        return 3
    elif year <= 2019:
        return 4
    else:
        return 5

def split_dat(input_path):
    base, ext = os.path.splitext(input_path)
    buckets = {1: [], 2: [], 3: [], 4: [], 5: []}
    skipped = []

    with open(input_path, encoding='utf-8') as f:
        for lineno, line in enumerate(f, 1):
            stripped = line.rstrip('\n')
            parts = stripped.split(';')
            if len(parts) < 2:
                skipped.append((lineno, stripped))
                continue
            try:
                year = int(parts[1].strip())
            except ValueError:
                skipped.append((lineno, stripped))
                continue
            buckets[year_to_suffix(year)].append(stripped)

    for n, lines in sorted(buckets.items()):
        if not lines:
            continue
        out_path = f"{base}-{n}{ext}"
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        print(f"Wrote {len(lines):6d} lines → {out_path}")

    total_written = sum(len(lines) for lines in buckets.values())
    total_original = sum(len(lines) for lines in buckets.values()) + len(skipped)
    print(f"\nVerification: {total_written} lines written", end="")
    if skipped:
        print(f" + {len(skipped)} skipped = {total_original} total")
        print(f"Original file: {total_original} lines — ", end="")
    else:
        # recount from original file
        with open(input_path, encoding='utf-8') as f:
            orig_count = sum(1 for _ in f)
        print(f" / {orig_count} original — ", end="")
        if total_written == orig_count:
            print("OK")
        else:
            print(f"MISMATCH ({orig_count - total_written} unaccounted)")

    if skipped:
        print(f"\nSkipped {len(skipped)} unparseable lines:")
        for lineno, line in skipped[:10]:
            print(f"  line {lineno}: {line!r}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 split_dat_by_year.py <bb_male.dat|bb_female.dat>")
        sys.exit(1)
    split_dat(sys.argv[1])
