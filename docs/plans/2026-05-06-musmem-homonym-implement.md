# MuscleMemory Homonym Detection — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a skill that reads one or more semicolon-delimited `.dat` files and flags athlete names that likely represent two different people based on year gaps and category patterns.

**Architecture:** A single Python script that parses `.dat` files, groups records by name, detects suspicious patterns (large year gap, pre-1995/post-2010 span without 60+ categories, open-only profile across the gap), and prints a one-line-per-name report to stdout. A `SKILL.md` wraps it for Claude invocation.

**Tech Stack:** Python 3 stdlib only — `pathlib`, `collections`, `sys`.

---

### Task 1: Create the skill folder and SKILL.md

**Files:**
- Create: `musmem-homonym/SKILL.md`

**Step 1: Create the folder and write SKILL.md**

```markdown
---
name: musmem-homonym
description: Use when scanning bodybuilding contest data files for athlete names that likely represent two different people — identified by large year gaps, pre-1995 athletes reappearing post-2010 outside 60+ categories, or open-only category profiles spanning a large gap.
---

# MuscleMemory Homonym Detection

Scans one or more semicolon-delimited `.dat` files for athlete names that likely represent two different people.

## Usage

Copy the script to `/tmp/` first (required by permission rules), then run:

```bash
cp ~/workspace/skills/musmemSkills/musmem-homonym/scripts/homonym_detector.py /tmp/
python3 /tmp/homonym_detector.py
```

The script prompts for one or more file paths. Press Enter on a blank line to finish. Paths may be absolute, `~`-relative, or bare filenames resolved under `~/workspace/musmem/data`.

## Detection

- **Gap ≥ 10 years** with no appearances → flagged
- Flagged as high confidence unless the athlete competed exclusively in masters categories throughout (lower confidence section)
- Pre-1995 appearance + post-2010 appearance outside 60+ categories → always high confidence regardless of category profile

## Report Format

```
Smith, John; 1984–1990, 2022–2024
Jones, Bob; 1988–1990, 2019–2023

42 names flagged

--- Lower confidence (masters throughout) ---
Williams, Mark; 1995–2005, 2020–2023
```
```

**Step 2: Verify the file exists and frontmatter is valid**

Read `musmem-homonym/SKILL.md` and confirm `name:` and `description:` fields are present.

---

### Task 2: Write the script — file collection

**Files:**
- Create: `musmem-homonym/scripts/homonym_detector.py`

**Step 1: Write the file with the collect_files() function and a stub main**

```python
import sys
from pathlib import Path
from collections import defaultdict

DEFAULT_DATA_DIR = Path.home() / "workspace" / "musmem" / "data"


def collect_files():
    print(f"Enter .dat file paths (blank line to finish).")
    print(f"Relative paths resolve under {DEFAULT_DATA_DIR}")
    print()
    files = []
    while True:
        raw = input("File: ").strip()
        if not raw:
            if not files:
                print("No files entered. Exiting.")
                sys.exit(1)
            break
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = DEFAULT_DATA_DIR / p
        if not p.exists():
            print(f"  Not found: {p}")
        else:
            files.append(p)
            print(f"  Added: {p}")
    return files


if __name__ == "__main__":
    paths = collect_files()
    print(f"Collected {len(paths)} file(s)")
```

**Step 2: Copy to /tmp and verify interactively**

```bash
cp ~/workspace/skills/musmemSkills/musmem-homonym/scripts/homonym_detector.py /tmp/homonym_detector.py
python3 /tmp/homonym_detector.py
```

Enter `bb_male.dat` at the prompt. Confirm output: `Added: /Users/timfogarty/workspace/musmem/data/bb_male.dat` and `Collected 1 file(s)`.

---

### Task 3: Add the parser

**Files:**
- Modify: `musmem-homonym/scripts/homonym_detector.py`

**Step 1: Add parse_files() above the `if __name__` block**

```python
def parse_files(paths):
    """Returns list of (name, year, division_code) tuples."""
    records = []
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                cols = [c.strip() for c in line.split(";")]
                if len(cols) < 4:
                    continue
                name = cols[0]
                try:
                    year = int(cols[1])
                except ValueError:
                    continue
                div_placing = cols[3]
                # "LH-3" → "LH", "c4a-2" → "c4a", "M6-1" → "M6"
                code = div_placing.rsplit("-", 1)[0] if "-" in div_placing else div_placing
                if name and year and code:
                    records.append((name, year, code))
    return records
```

**Step 2: Update main to print record count**

```python
if __name__ == "__main__":
    paths = collect_files()
    records = parse_files(paths)
    print(f"Parsed {len(records)} records")
```

**Step 3: Verify against bb_male.dat**

Copy to /tmp and run. Confirm record count is in the tens of thousands (no traceback).

---

### Task 4: Add category classifiers

**Files:**
- Modify: `musmem-homonym/scripts/homonym_detector.py`

**Step 1: Add constants and helper functions after the imports, before collect_files()**

```python
# Codes representing 60+ or older masters categories
SIXTY_PLUS_CODES = {
    "M6", "6H", "6l", "6M", "6L", "6t", "6m", "6s",
    "m6", "65",
    "M7", "7H", "7M", "7L",
    "M8", "M9",
    "GM", "GH", "GL", "Gt", "Gs", "UM",
    "M6212", "M7212",
    "c6", "c6a", "c6b", "c7",
    "P6", "P7",
    "F6", "F6a", "F6b", "f6", "F65",
}

# Codes representing clearly open/non-masters competition
OPEN_CODES = {
    "OP", "OV", "BB", "PBB",
    "SW", "LS", "HW", "LH", "MW", "LM", "WW", "LW", "BW", "FW", "LF",
    "U212", "U208", "U202",
    "XT", "TA", "MT", "ME", "SH", "XS",
    "TE", "TH", "Tl", "TM", "TL", "Tt", "Tm", "Ts", "Ta", "Tb", "Tu",
    "JR", "JH", "Jl", "JM", "JW", "JL", "JB", "JF", "Jf", "Jt", "Jm", "Js", "Ju", "Jy",
    "ED", "EH", "EM", "EL", "EP", "EF",
    "Ba", "Bb", "Bc", "Bd", "Be", "Bf", "Bg",
    "55kg", "60kg", "65kg", "70kg", "75kg", "80kg", "85kg", "90kg",
    "95kg", "100kg", "105kg", "o100kg",
    "CL", "Ca", "Cb", "Cc", "Cd", "Ce", "Cf", "Cg", "Ch",
    "Cs", "cS", "Cm", "cM", "Ct", "cT", "ct",
    "CJ", "CJa", "CJb", "CJc", "CJd",
    "PH", "Pa", "Pb", "Pc", "Pd", "Pe", "Pf", "Pg", "Ph",
    "PT", "PJ", "PJa", "PJb", "PJc", "PJd",
    "FI", "FX", "Ft", "fM", "Fm", "fS", "Fs", "Fx",
    "Fa", "Fb", "Fc", "Fd", "Fe", "Ff", "Fg", "Fh",
    "FT", "FJ", "FJa", "FJb", "FJc", "FJd", "js", "jt",
    "PQ", "PR", "PB", "PRh", "Pmw", "Pl", "Ps", "Pm", "Pt", "PP", "PCL", "PF",
    "AP", "As", "Am", "aM", "At", "A1", "A2", "A3", "A4", "A5", "JA",
    "AM", "C1", "C2", "C3", "C4",
    "HP", "HP3", "HP0s", "HP0t", "HP4s", "HP4t", "HP6t",
    "Ea", "Mi", "So", "Se", "Sw", "dC", "We",
    "PA", "HC", "Hs", "Hw", "WC", "QA",
    "Mu", "Sy",
}


def is_sixty_plus(code):
    return code in SIXTY_PLUS_CODES


def is_open(code):
    return code in OPEN_CODES
```

---

### Task 5: Add gap detection and year clustering

**Files:**
- Modify: `musmem-homonym/scripts/homonym_detector.py`

**Step 1: Add after the category classifier functions**

```python
GAP_THRESHOLD = 10  # consecutive years with no appearances


def find_gaps(years_sorted):
    """Returns True if any consecutive pair of years has a gap >= GAP_THRESHOLD."""
    for i in range(len(years_sorted) - 1):
        if years_sorted[i + 1] - years_sorted[i] >= GAP_THRESHOLD:
            return True
    return False


def cluster_years(years_sorted):
    """Split sorted years into clusters separated by gaps >= GAP_THRESHOLD."""
    if not years_sorted:
        return []
    clusters = []
    current = [years_sorted[0]]
    for y in years_sorted[1:]:
        if y - current[-1] >= GAP_THRESHOLD:
            clusters.append(current)
            current = [y]
        else:
            current.append(y)
    clusters.append(current)
    return clusters
```

---

### Task 6: Add the main analysis function

**Files:**
- Modify: `musmem-homonym/scripts/homonym_detector.py`

**Step 1: Add analyze() after cluster_years()**

```python
def analyze(records):
    """
    Returns (high_confidence, lower_confidence).
    Each item is (name, clusters) where clusters is a list of year lists.
    """
    by_name = defaultdict(list)
    for name, year, code in records:
        by_name[name].append((year, code))

    high = []
    low = []

    for name, appearances in by_name.items():
        years_sorted = sorted(set(y for y, _ in appearances))
        if len(years_sorted) < 2:
            continue
        if not find_gaps(years_sorted):
            continue

        clusters = cluster_years(years_sorted)
        if len(clusters) < 2:
            continue

        year_to_codes = defaultdict(set)
        for y, code in appearances:
            year_to_codes[y].add(code)

        def cluster_codes(cluster):
            codes = set()
            for y in cluster:
                codes |= year_to_codes[y]
            return codes

        early_codes = cluster_codes(clusters[0])
        late_codes = cluster_codes(clusters[-1])
        all_codes = set(code for _, code in appearances)

        # Pre-1995 appearances + post-2010 appearances outside 60+ → always high confidence
        pattern_b = (
            min(clusters[0]) < 1995
            and max(clusters[-1]) > 2010
            and not any(is_sixty_plus(c) for c in late_codes)
        )

        # No open codes anywhere → masters-only profile
        masters_only = not any(is_open(c) for c in all_codes)

        if masters_only and not pattern_b:
            low.append((name, clusters))
        else:
            high.append((name, clusters))

    return high, low
```

---

### Task 7: Add the report printer and wire up main

**Files:**
- Modify: `musmem-homonym/scripts/homonym_detector.py`

**Step 1: Add format_clusters() and print_report() after analyze()**

```python
def format_clusters(clusters):
    parts = []
    for c in clusters:
        if len(c) == 1:
            parts.append(str(c[0]))
        else:
            parts.append(f"{min(c)}–{max(c)}")
    return ", ".join(parts)


def print_report(high, low):
    for name, clusters in sorted(high, key=lambda x: x[0]):
        print(f"{name}; {format_clusters(clusters)}")

    total = len(high) + len(low)
    print(f"\n{total} names flagged")

    if low:
        print("\n--- Lower confidence (masters throughout) ---")
        for name, clusters in sorted(low, key=lambda x: x[0]):
            print(f"{name}; {format_clusters(clusters)}")
```

**Step 2: Replace the stub main with the full entry point**

```python
if __name__ == "__main__":
    paths = collect_files()
    records = parse_files(paths)
    high, low = analyze(records)
    print_report(high, low)
```

---

### Task 8: End-to-end verification

**Step 1: Copy to /tmp and run against bb_male.dat**

```bash
cp ~/workspace/skills/musmemSkills/musmem-homonym/scripts/homonym_detector.py /tmp/homonym_detector.py
python3 /tmp/homonym_detector.py
```

Enter `bb_male.dat` at the prompt.

**Step 2: Confirm output shape**

- Lines follow format: `Last, First; 1984–1991, 2022–2024`
- Summary line `N names flagged` appears
- Optional lower-confidence section appears if any masters-only cases exist
- No Python tracebacks

**Step 3: Spot-check 2–3 flagged names**

Pick a flagged name and search the data file to confirm the year clusters match actual records. Adjust GAP_THRESHOLD or category sets if results look wrong.
