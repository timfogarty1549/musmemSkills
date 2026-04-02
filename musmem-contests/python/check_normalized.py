#!/usr/bin/env python3
"""Check which files in 1-incoming/ are fully normalized and move them to 2-normalize-athletes/.

A line is normalized if:
  - contains a comma (Last, First format), or
  - starts with @ (East Asian format), or
  - has only one word after the placing number (single name, e.g. "1 Cher")
"""

import json
import shutil
from pathlib import Path

CONFIG = Path.home() / "workspace/skills/musmemSkills/config/paths.json"
data = json.loads(CONFIG.read_text())
INCOMING  = Path(data["incoming_folder"]).expanduser()
NORMALIZE = Path(data["normalize_folder"]).expanduser()

SKIP_PREFIXES = ("y ", "t ", "c ", "y:", "t:", "c:", "----")


def line_is_normalized(line):
    if "," in line or line.startswith("@"):
        return True
    # Strip leading placing number — if only one word remains, it's a single name
    parts = line.split(None, 1)
    if len(parts) < 2:
        return True  # bare number, edge case
    name_part = parts[1].strip()
    return " " not in name_part  # single name, no spaces


def is_normalized(path):
    athlete_lines = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        if any(line.startswith(p) for p in SKIP_PREFIXES):
            continue
        athlete_lines.append(line)
    if not athlete_lines:
        return False
    return all(line_is_normalized(line) for line in athlete_lines)


moved = []
not_normalized = []

for f in sorted(INCOMING.glob("*.txt")):
    if is_normalized(f):
        dest = NORMALIZE / f.name
        shutil.move(str(f), str(dest))
        moved.append(f.name)
    else:
        not_normalized.append(f.name)

if moved:
    print(f"Moved to 2-normalize-athletes/ ({len(moved)} files):")
    for n in moved:
        print(f"  {n}")
else:
    print("No additional files to move.")

print(f"\nLeft in 1-incoming/ ({len(not_normalized)} files, not yet normalized):")
for n in not_normalized:
    print(f"  {n}")
