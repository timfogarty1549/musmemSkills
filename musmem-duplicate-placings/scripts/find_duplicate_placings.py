"""
Find duplicate athlete placings for the same contest split across multiple data files.

Trigger scenario: a contest is entered into one file, then later re-entered
(fully or partially) into another file to add a division that was missed the
first time. If the re-entry included divisions that were already present,
those division/placement slots now exist in both files -- a duplicate. Athlete
names may not match exactly between the two entries because one file may not
yet have been run through the normalization script; matching is done on
(division, placement) alone, not on name.
"""
import os
import sys
from collections import defaultdict

DEFAULT_DIR = '/Users/timfogarty/workspace/musmem/data/'

SKIP_PLACEMENTS = {98, 0}


def prompt_for_files():
    print(f"Default folder: {DEFAULT_DIR}", file=sys.stderr)
    print("Enter data file names one at a time (relative to the default folder,", file=sys.stderr)
    print("or an absolute path). Blank line ends the list.", file=sys.stderr)
    paths = []
    while True:
        entry = input("File: ").strip()
        if not entry:
            break
        path = entry if os.path.isabs(entry) else os.path.join(DEFAULT_DIR, entry)
        paths.append(path)
    return paths


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


def load_records(data_files):
    """
    records[(year, contest)][path] = list of (division, placement, name)
    """
    records = defaultdict(lambda: defaultdict(list))
    total = 0
    for path in data_files:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                rec = parse_record(line)
                if rec is None:
                    continue
                name, year, contest, division, placement = rec
                records[(year, contest)][path].append((division, placement, name))
                total += 1
    print(f"Loaded {total:,} athlete-contest records", file=sys.stderr)
    return records


def find_duplicate_placings(records):
    """
    For each (year, contest) present in 2+ files, find (division, placement)
    slots that appear in more than one file. Placements 98 and 0 are excluded
    from the overlap check (they're not unique-holder slots) but still count
    toward each file's total record count.

    Returns a list of (year, contest, counts, overlaps):
      counts  = {path: total record count in that file for this contest}
      overlaps = {(division, placement): {path: [names]}}
    """
    results = []
    for (year, contest), by_file in records.items():
        files_present = [p for p, entries in by_file.items() if entries]
        if len(files_present) < 2:
            continue

        slot_map = defaultdict(lambda: defaultdict(list))
        for path, entries in by_file.items():
            for division, placement, name in entries:
                if placement in SKIP_PLACEMENTS:
                    continue
                slot_map[(division, placement)][path].append(name)

        overlaps = {
            slot: file_names
            for slot, file_names in slot_map.items()
            if len(file_names) > 1
        }
        if overlaps:
            counts = {path: len(entries) for path, entries in by_file.items()}
            results.append((year, contest, counts, overlaps))

    results.sort(key=lambda r: (r[0], r[1]))
    return results


def main():
    data_files = prompt_for_files()
    if not data_files:
        print("No files entered. Exiting.", file=sys.stderr)
        return
    records = load_records(data_files)
    results = find_duplicate_placings(records)

    if results:
        print(f"\n{'='*70}")
        print(f"CONTESTS WITH DUPLICATE PLACINGS ACROSS FILES ({len(results)})")
        print(f"{'='*70}")
        for year, contest, counts, overlaps in results:
            print(f"{year}: '{contest}'")
            for path, count in counts.items():
                print(f"      {os.path.basename(path)}: {count} records")
            print(f"      Overlapping division/placement slots ({len(overlaps)}):")
            for (division, placement), file_names in sorted(overlaps.items()):
                pieces = [
                    f"{os.path.basename(p)}='{'/'.join(names)}'"
                    for p, names in file_names.items()
                ]
                print(f"        {division}-{placement}: " + " vs ".join(pieces))
            print()
    else:
        print("\nNo duplicate placings found.")

    print(f"Total contests flagged: {len(results)}")


if __name__ == '__main__':
    main()
