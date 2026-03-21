import json
import sys
from collections import defaultdict

INPUT_FILE = "/Users/timfogarty/workspace/musmem/data/contest_locations.json"
OUTPUT_FILE = "/Users/timfogarty/workspace/musmem/data/contest_locations.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# Group entries by contest name
grouped = defaultdict(list)
for entry in data:
    grouped[entry["contest"]].append(entry)

duplicates = {name: entries for name, entries in grouped.items() if len(entries) > 1}

if duplicates:
    print("=== DUPLICATE CONTEST NAMES FOUND ===")
    for name, entries in duplicates.items():
        print(f"\n  Contest: {name}  ({len(entries)} entries)")

# Merge all entries per contest name
merged = {}
for name, entries in grouped.items():
    combined_years = {}
    for entry in entries:
        for year, year_data in entry.get("years", {}).items():
            if year in combined_years:
                existing = combined_years[year]
                incoming = year_data
                # Check if they differ in any meaningful way
                if existing != incoming:
                    print(f"\n  DUPLICATE YEAR {year} in '{name}':")
                    print(f"    existing : {json.dumps(existing)}")
                    print(f"    incoming : {json.dumps(incoming)}")
                    # Keep whichever has more populated fields
                    def field_count(d):
                        return sum(1 for v in d.values() if v)
                    if field_count(incoming) > field_count(existing):
                        print(f"    -> keeping incoming (more fields populated)")
                        combined_years[year] = incoming
                    else:
                        print(f"    -> keeping existing (more or equal fields populated)")
                # else identical — silently keep
            else:
                combined_years[year] = year_data
    merged[name] = combined_years

# Build output array: sorted by contest name, years sorted numerically within each entry
output = []
for name in sorted(merged.keys()):
    years_sorted = dict(sorted(merged[name].items(), key=lambda kv: int(kv[0])))
    output.append({"contest": name, "years": years_sorted})

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"\n=== DONE ===")
print(f"  Input entries  : {len(data)}")
print(f"  Output contests: {len(output)}")
if duplicates:
    print(f"  Merged duplicates: {list(duplicates.keys())}")
else:
    print("  No duplicate contest names found.")
