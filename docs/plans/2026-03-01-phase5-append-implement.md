# Phase 5 Append & Verify Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create `append_and_verify.py` (+ shell wrapper) that verifies new athlete names against master files, resolves conflicts interactively, then appends to the master.

**Architecture:** Single Python script modeled on `review_flags.py`. Reads master as read-only reference, parses `.out` file, runs similarity checks on new athlete names, collects conflicts, iterates interactively (single-keypress), holds all corrections in memory, then appends corrected content to master and sorts — touching the master only once at the end.

**Tech Stack:** Python 3 stdlib only (termios, tty, difflib, re, pathlib). No external packages. Shell wrapper uses osascript like `review_flags.sh`.

---

## Master file record format

```
Last, First; year; Contest Name - ORG; division-placing; c=XX;
Last, First [2]; year; Contest Name - ORG; division-placing;
```

Fields separated by `; `. First field is athlete name (may include `[n]` disambiguation suffix).

## .out file record format (same as master, no [n] suffixes on new data)

```
Smith, John; 2025; Arnold Classic - IFBB; OP-3;
```

---

## Task 1: Shell wrapper

**Files:**
- Create: `.claude/skills/musmem-contests/python/append_and_verify.sh`

**Step 1: Write the shell wrapper**

```bash
#!/bin/bash
# Launch append_and_verify.py in a new Terminal window.
# Usage: append_and_verify.sh [filename]   # with or without .out extension
#        append_and_verify.sh              # all pending .out files

SCRIPT=~/workspace/skills/musmemContests/python/append_and_verify.py

if [ -n "$1" ]; then
    CMD="python3 $SCRIPT '$1'"
else
    CMD="python3 $SCRIPT"
fi

osascript -e "tell application \"Terminal\" to do script \"$CMD\""
```

**Step 2: Make it executable**

```bash
chmod +x ~/.../append_and_verify.sh
```

**Step 3: Commit**

```bash
git add .claude/skills/musmem-contests/python/append_and_verify.sh
git commit -m "feat: add append_and_verify shell wrapper"
```

---

## Task 2: Core data structures and parsing

**Files:**
- Create: `.claude/skills/musmem-contests/python/append_and_verify.py`
- Create: `.claude/skills/musmem-contests/python/test_append_and_verify.py`

The script needs these constants at the top:

```python
FORMATTED_DIR = Path.home() / "workspace/musmem/formatted"
APPENDED_DIR  = Path.home() / "workspace/musmem/appended"
MASTER = {
    "male":   Path.home() / "workspace/musmem/bb_male.dat",
    "female": Path.home() / "workspace/musmem/bb_female.dat",
}
CYAN  = "\033[96m"
BOLD  = "\033[1m"
RESET = "\033[0m"
```

**Step 1: Write failing tests for name parsing utilities**

```python
# test_append_and_verify.py
from append_and_verify import strip_disambig, base_name_of, get_next_disambig

def test_strip_disambig_plain():
    assert strip_disambig("Smith, John") == "Smith, John"

def test_strip_disambig_numbered():
    assert strip_disambig("Smith, John [2]") == "Smith, John"
    assert strip_disambig("Smith, John [12]") == "Smith, John"

def test_base_name_of():
    assert base_name_of("Smith, John") == "Smith, John"
    assert base_name_of("Smith, John [3]") == "Smith, John"

def test_get_next_disambig_none_exist():
    # base name not in master at all — new person, no [n] needed (keep as plain)
    assert get_next_disambig("Jones, Bob", set()) == "Jones, Bob [2]"

def test_get_next_disambig_plain_exists():
    # "Jones, Bob" exists (no [n]), next is [2]
    assert get_next_disambig("Jones, Bob", {"Jones, Bob"}) == "Jones, Bob [2]"

def test_get_next_disambig_gap():
    # "Jones, Bob" and "Jones, Bob [2]" exist, next is [3]
    existing = {"Jones, Bob", "Jones, Bob [2]"}
    assert get_next_disambig("Jones, Bob", existing) == "Jones, Bob [3]"
```

**Step 2: Run tests to verify they fail**

```bash
cd ~/.../python && python3 -m pytest test_append_and_verify.py::test_strip_disambig_plain -v
```

Expected: ImportError or NameError — function not defined yet.

**Step 3: Implement the functions**

```python
import re

def strip_disambig(name: str) -> str:
    """Remove [n] suffix: 'Smith, John [2]' -> 'Smith, John'."""
    return re.sub(r'\s*\[\d+\]$', '', name).strip()

def base_name_of(name: str) -> str:
    return strip_disambig(name)

def get_next_disambig(base: str, all_master_names: set) -> str:
    """Return next available [n] for base name. Plain name counts as slot 1."""
    n = 1
    if base in all_master_names:
        n = 2
    while f"{base} [{n}]" in all_master_names:
        n += 1
    return f"{base} [{n}]"
```

**Step 4: Run tests to verify they pass**

```bash
python3 -m pytest test_append_and_verify.py -k "disambig or base_name" -v
```

Expected: all PASS.

**Step 5: Commit**

```bash
git add .claude/skills/musmem-contests/python/append_and_verify.py \
        .claude/skills/musmem-contests/python/test_append_and_verify.py
git commit -m "feat: name disambiguation utilities with tests"
```

---

## Task 3: Athlete index from master file

**Step 1: Write failing tests**

```python
# add to test_append_and_verify.py
from append_and_verify import build_athlete_index, AthleteEntry

SAMPLE_MASTER = [
    "Smith, John; 2015; Arnold Classic - IFBB; OP-1;\n",
    "Smith, John; 2016; Tampa Pro - IFBB; OP-2;\n",
    "Smith, John [2]; 2021; Arnold Classic - IFBB; PH-3;\n",
    "Jones, Bob; 2020; Olympia - IFBB; CL-5;\n",
]

def test_build_athlete_index_keys():
    idx = build_athlete_index(SAMPLE_MASTER)
    assert "Smith, John" in idx
    assert "Jones, Bob" in idx

def test_build_athlete_index_variants():
    idx = build_athlete_index(SAMPLE_MASTER)
    # Smith, John has two variants
    assert len(idx["Smith, John"]) == 2

def test_build_athlete_index_summary():
    idx = build_athlete_index(SAMPLE_MASTER)
    entry = idx["Smith, John"][0]  # first variant: plain "Smith, John"
    assert entry.full_name == "Smith, John"
    assert entry.count == 2
    assert entry.y0 == 2015
    assert entry.y1 == 2016
    assert "OP" in entry.divisions

def test_build_athlete_index_all_names():
    idx = build_athlete_index(SAMPLE_MASTER)
    all_names = {e.full_name for entries in idx.values() for e in entries}
    assert "Smith, John" in all_names
    assert "Smith, John [2]" in all_names
```

**Step 2: Run to verify they fail**

```bash
python3 -m pytest test_append_and_verify.py -k "athlete_index" -v
```

**Step 3: Implement**

```python
from dataclasses import dataclass, field

@dataclass
class AthleteEntry:
    full_name: str
    count: int = 0
    y0: int = 9999
    y1: int = 0
    divisions: list = field(default_factory=list)

def build_athlete_index(lines: list[str]) -> dict:
    """
    Returns dict: base_name -> list[AthleteEntry] (one per [n] variant).
    Parses lines of format: Last, First [n]; year; contest; div-placing; ...
    """
    entries: dict[str, AthleteEntry] = {}  # full_name -> AthleteEntry

    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split("; ", 4)
        if len(parts) < 4:
            continue
        full_name = parts[0]
        try:
            year = int(parts[1])
        except ValueError:
            continue
        div_placing = parts[3]  # e.g. "OP-3"
        div = div_placing.split("-")[0] if "-" in div_placing else div_placing

        if full_name not in entries:
            entries[full_name] = AthleteEntry(full_name=full_name)
        e = entries[full_name]
        e.count += 1
        e.y0 = min(e.y0, year)
        e.y1 = max(e.y1, year)
        if div not in e.divisions:
            e.divisions.append(div)

    # Group by base name
    index: dict[str, list[AthleteEntry]] = {}
    for full_name, entry in entries.items():
        base = base_name_of(full_name)
        if base not in index:
            index[base] = []
        index[base].append(entry)

    return index


def all_master_names(index: dict) -> set:
    """Flat set of all full names (including [n] variants) from index."""
    return {e.full_name for entries in index.values() for e in entries}
```

**Step 4: Run tests**

```bash
python3 -m pytest test_append_and_verify.py -k "athlete_index" -v
```

Expected: all PASS.

**Step 5: Commit**

```bash
git add .claude/skills/musmem-contests/python/append_and_verify.py \
        .claude/skills/musmem-contests/python/test_append_and_verify.py
git commit -m "feat: athlete index builder with tests"
```

---

## Task 4: Similarity detection

**Step 1: Write failing tests**

```python
# add to test_append_and_verify.py
from append_and_verify import soundex, find_candidates

def test_soundex_basic():
    assert soundex("Smith") == soundex("Smithe")
    assert soundex("John") != soundex("Smith")

def test_soundex_same():
    assert soundex("Smith") == soundex("Smith")

def test_find_candidates_soundex_last():
    idx = build_athlete_index([
        "Smith, John; 2020; Test - IFBB; OP-1;\n",
    ])
    candidates = find_candidates("Smithe, John", idx)
    assert any(c.full_name == "Smith, John" for c in candidates)

def test_find_candidates_edit_distance():
    idx = build_athlete_index([
        "Lunsford, Derek; 2020; Test - IFBB; OP-1;\n",
    ])
    # one letter off
    candidates = find_candidates("Lundsford, Derek", idx)
    assert any(c.full_name == "Lunsford, Derek" for c in candidates)

def test_find_candidates_word_order():
    idx = build_athlete_index([
        "Smith, John; 2020; Test - IFBB; OP-1;\n",
    ])
    # first/last swapped
    candidates = find_candidates("John, Smith", idx)
    assert any(c.full_name == "Smith, John" for c in candidates)

def test_find_candidates_no_false_positives():
    idx = build_athlete_index([
        "Jones, Alice; 2020; Test - IFBB; FI-1;\n",
    ])
    candidates = find_candidates("Smith, John", idx)
    assert candidates == []
```

**Step 2: Run to verify they fail**

```bash
python3 -m pytest test_append_and_verify.py -k "soundex or find_candidates" -v
```

**Step 3: Implement**

```python
def soundex(name: str) -> str:
    """Classic Soundex algorithm."""
    name = name.upper()
    if not name:
        return ""
    table = str.maketrans("BFPVCGJKQSXZDTLMNR", "111122222222334556")
    keep = name[0]
    coded = name[1:].translate(table)
    # remove non-coded chars (vowels etc become empty after translate — they aren't in table)
    # actually translate only maps chars in table; others pass through unchanged
    # We want to remove anything not in 1-6
    result = keep
    prev = ""
    for ch in coded:
        if ch in "123456" and ch != prev:
            result += ch
            prev = ch
        elif ch not in "123456":
            prev = ""  # vowel breaks adjacency
    return (result + "000")[:4]


def levenshtein(a: str, b: str) -> int:
    """Edit distance between two strings."""
    if len(a) < len(b):
        return levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1,
                            prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]


def name_parts(name: str):
    """Return (last, first) from 'Last, First' or ('', name) if no comma."""
    base = base_name_of(name)
    if ", " in base:
        last, first = base.split(", ", 1)
        return last.strip(), first.strip()
    return base.strip(), ""


def word_key(name: str) -> str:
    """Sorted lowercase letters of all name words — detects first/last swap."""
    base = base_name_of(name)
    words = re.sub(r"[^a-z ]", "", base.lower()).split()
    return "".join(sorted(words))


def find_candidates(new_name: str, index: dict) -> list:
    """
    Return list of AthleteEntry objects from index that are similar to new_name.
    Checks: soundex last, soundex first, edit distance on last, word-order.
    """
    new_last, new_first = name_parts(new_name)
    new_wkey = word_key(new_name)
    matched = set()
    results = []

    for base, entries in index.items():
        ex_last, ex_first = name_parts(base)

        hit = False
        # soundex on last name (same first)
        if new_first and ex_first and new_first.lower() == ex_first.lower():
            if soundex(new_last) == soundex(ex_last):
                hit = True
        # soundex on first name (same last)
        if new_last and ex_last and new_last.lower() == ex_last.lower():
            if new_first and ex_first and soundex(new_first) == soundex(ex_first):
                hit = True
        # edit distance ≤ 2 on last name (same first)
        if not hit and new_first and ex_first and new_first.lower() == ex_first.lower():
            if new_last and ex_last and levenshtein(new_last.lower(), ex_last.lower()) <= 2:
                hit = True
        # word-order match (first/last swap)
        if not hit and new_wkey and word_key(base) == new_wkey:
            hit = True

        if hit:
            for entry in entries:
                if entry.full_name not in matched:
                    matched.add(entry.full_name)
                    results.append(entry)

    return results
```

**Step 4: Run tests**

```bash
python3 -m pytest test_append_and_verify.py -k "soundex or find_candidates" -v
```

Expected: all PASS.

**Step 5: Commit**

```bash
git add .claude/skills/musmem-contests/python/append_and_verify.py \
        .claude/skills/musmem-contests/python/test_append_and_verify.py
git commit -m "feat: similarity detection (soundex, edit distance, word order) with tests"
```

---

## Task 5: .out file parsing and correction application

**Step 1: Write failing tests**

```python
# add to test_append_and_verify.py
from append_and_verify import parse_out_new_athletes, apply_name_corrections

SAMPLE_OUT = [
    "Smithe, John; 2025; Arnold Classic - IFBB; OP-3;\n",
    "Dauda, Samson; 2025; Arnold Classic - IFBB; OP-2;\n",
    "Smithe, John; 2025; Arnold Classic - IFBB; OV-1;\n",  # same athlete, second line
]

SAMPLE_MASTER_LINES = [
    "Dauda, Samson; 2024; Tampa Pro - IFBB; OP-1;\n",
]

def test_parse_out_new_athletes():
    idx = build_athlete_index(SAMPLE_MASTER_LINES)
    master_names = all_master_names(idx)
    new_athletes = parse_out_new_athletes(SAMPLE_OUT, master_names)
    # Smithe, John is new; Dauda, Samson already in master
    assert "Smithe, John" in new_athletes
    assert "Dauda, Samson" not in new_athletes

def test_apply_name_corrections_renames_all():
    corrections = {"Smithe, John": "Smith, John"}
    result = apply_name_corrections(SAMPLE_OUT, corrections)
    assert result[0].startswith("Smith, John;")
    assert result[2].startswith("Smith, John;")  # both occurrences renamed

def test_apply_name_corrections_no_change():
    corrections = {}
    result = apply_name_corrections(SAMPLE_OUT, corrections)
    assert result == SAMPLE_OUT
```

**Step 2: Run to verify they fail**

```bash
python3 -m pytest test_append_and_verify.py -k "parse_out or apply_name" -v
```

**Step 3: Implement**

```python
def parse_out_new_athletes(out_lines: list[str], master_names: set) -> set:
    """Return set of athlete names in out_lines not already in master_names."""
    new = set()
    for line in out_lines:
        line = line.strip()
        if not line:
            continue
        name = line.split("; ", 1)[0]
        if name and name not in master_names:
            new.add(name)
    return new


def apply_name_corrections(out_lines: list[str], corrections: dict) -> list[str]:
    """
    Return new list of lines with athlete names replaced per corrections dict.
    corrections: {old_name: new_name}
    """
    result = []
    for line in out_lines:
        stripped = line.rstrip("\n")
        parts = stripped.split("; ", 1)
        if len(parts) >= 1 and parts[0] in corrections:
            new_name = corrections[parts[0]]
            if len(parts) == 2:
                stripped = f"{new_name}; {parts[1]}"
            else:
                stripped = new_name
        result.append(stripped + "\n")
    return result
```

**Step 4: Run tests**

```bash
python3 -m pytest test_append_and_verify.py -k "parse_out or apply_name" -v
```

Expected: all PASS.

**Step 5: Commit**

```bash
git add .claude/skills/musmem-contests/python/append_and_verify.py \
        .claude/skills/musmem-contests/python/test_append_and_verify.py
git commit -m "feat: .out parsing and correction application with tests"
```

---

## Task 6: Append, sort, and move

**Step 1: Write failing tests**

```python
# add to test_append_and_verify.py
import tempfile, os
from pathlib import Path
from append_and_verify import append_sort_master

def test_append_sort_master():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.dat', delete=False) as mf:
        mf.write("Smith, John; 2020; Test - IFBB; OP-2;\n")
        mf.write("Adams, Carl; 2020; Test - IFBB; OP-1;\n")
        master_path = Path(mf.name)

    new_lines = ["Jones, Bob; 2025; Arnold Classic - IFBB; OP-3;\n"]
    append_sort_master(master_path, new_lines)

    result = master_path.read_text().splitlines()
    # Should be sorted: Adams, Jones, Smith
    assert result[0].startswith("Adams, Carl")
    assert result[1].startswith("Jones, Bob")
    assert result[2].startswith("Smith, John")
    master_path.unlink()
```

**Step 2: Run to verify it fails**

```bash
python3 -m pytest test_append_and_verify.py::test_append_sort_master -v
```

**Step 3: Implement**

```python
def append_sort_master(master_path: Path, new_lines: list[str]) -> None:
    """Append new_lines to master_path, then sort in place."""
    existing = master_path.read_text().splitlines(keepends=True) if master_path.exists() else []
    combined = existing + new_lines
    combined.sort(key=lambda l: l.lower())
    master_path.write_text("".join(combined))
```

**Step 4: Run tests**

```bash
python3 -m pytest test_append_and_verify.py::test_append_sort_master -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add .claude/skills/musmem-contests/python/append_and_verify.py \
        .claude/skills/musmem-contests/python/test_append_and_verify.py
git commit -m "feat: append and sort master with tests"
```

---

## Task 7: Interactive UI and main entry point

No tests for the UI (interactive terminal). Implement it following the `review_flags.py` pattern exactly.

**Step 1: Add getch, get_gender, format_candidate_summary, detail_view**

```python
import os, sys, termios, tty

def getch():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return os.read(fd, 1).decode()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def get_gender(filename: str) -> str:
    if "-male" in filename:
        return "male"
    elif "-female" in filename:
        return "female"
    return ""


def format_candidate_summary(entry: AthleteEntry, number: int) -> str:
    divs = "/".join(entry.divisions[:4])  # cap at 4 for readability
    year_range = f"{entry.y0}" if entry.y0 == entry.y1 else f"{entry.y0}–{entry.y1}"
    return f"  {number}. {entry.full_name:<30} — {entry.count} contest{'s' if entry.count != 1 else ''}, {year_range}, {divs}"


def show_detail(entry: AthleteEntry, master_lines: list[str]) -> None:
    """Print all master records for this athlete."""
    print(f"\n  Records for {entry.full_name}:")
    count = 0
    for line in master_lines:
        if line.split("; ", 1)[0] == entry.full_name:
            print(f"    {line.rstrip()}")
            count += 1
    if count == 0:
        print("    (none found)")
    print()
```

**Step 2: Implement process_file()**

```python
def process_file(out_path: Path) -> bool:
    """
    Returns True to continue to next file, False to stop all.
    """
    gender = get_gender(out_path.name)
    if gender not in MASTER:
        print(f"Cannot determine gender from filename: {out_path.name}")
        return True

    master_path = MASTER[gender]
    master_lines = master_path.read_text().splitlines(keepends=True) if master_path.exists() else []

    out_lines = out_path.read_text().splitlines(keepends=True)

    index = build_athlete_index(master_lines)
    names = all_master_names(index)

    new_athletes = parse_out_new_athletes(out_lines, names)

    if not new_athletes:
        print(f"  No new athletes in {out_path.name} — appending directly.")
        APPENDED_DIR.mkdir(parents=True, exist_ok=True)
        append_sort_master(master_path, out_lines)
        out_path.rename(APPENDED_DIR / out_path.name)
        return True

    # Build conflicts: list of (new_name, [AthleteEntry, ...])
    conflicts = []
    for new_name in sorted(new_athletes):
        candidates = find_candidates(new_name, index)
        if candidates:
            conflicts.append((new_name, candidates))

    if not conflicts:
        print(f"  No similar names found in {out_path.name} — appending directly.")
        APPENDED_DIR.mkdir(parents=True, exist_ok=True)
        append_sort_master(master_path, out_lines)
        out_path.rename(APPENDED_DIR / out_path.name)
        return True

    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}{BOLD}{out_path.name}  ({len(conflicts)} conflicts){RESET}")
    print(f"{CYAN}{'='*60}{RESET}")

    # corrections: new_name -> resolved_name (None = skip/keep as-is)
    corrections = {}
    i = 0

    while i < len(conflicts):
        new_name, candidates = conflicts[i]

        # Find one contest example for this athlete from the .out file
        example = ""
        for line in out_lines:
            if line.split("; ", 1)[0] == new_name:
                parts = line.strip().split("; ")
                if len(parts) >= 4:
                    example = f"{parts[2]}, {parts[1]}, {parts[3]}"
                break

        print(f"\n[{i+1}/{len(conflicts)}] NEW: {BOLD}{new_name}{RESET}  ({example})")
        if new_name in corrections:
            val = corrections[new_name]
            print(f"  (previous decision: {val if val else 'skip'})")

        for j, entry in enumerate(candidates, 1):
            print(format_candidate_summary(entry, j))

        # Compute next [n] for display
        next_n = get_next_disambig(base_name_of(new_name), names)
        print(f"  N  New athlete → {next_n}")
        print(f"  D  Details (then enter number)")
        print(f"  S  Skip (keep name as-is)")
        if i > 0:
            print(f"  9  Back")
        print(f"  0  Done for now")
        print(f"  X  Exit all")
        print("Choice: ", end="", flush=True)

        while True:
            ch = getch().upper()

            if ch.isdigit() and ch != "0" and ch != "9":
                idx_pick = int(ch) - 1
                if 0 <= idx_pick < len(candidates):
                    print(ch)
                    corrections[new_name] = candidates[idx_pick].full_name
                    i += 1
                    break

            elif ch == "N":
                print(ch)
                corrections[new_name] = next_n
                i += 1
                break

            elif ch == "D":
                print(ch)
                print("  Which candidate? ", end="", flush=True)
                num_ch = getch()
                print(num_ch)
                idx_pick = int(num_ch) - 1 if num_ch.isdigit() else -1
                if 0 <= idx_pick < len(candidates):
                    show_detail(candidates[idx_pick], master_lines)
                else:
                    print("  (invalid)")
                print("Choice: ", end="", flush=True)

            elif ch == "S":
                print(ch)
                corrections[new_name] = None  # keep as-is
                i += 1
                break

            elif ch == "9" and i > 0:
                print(ch)
                prev_name = conflicts[i - 1][0]
                corrections.pop(prev_name, None)
                i -= 1
                break

            elif ch == "0":
                print(ch)
                _finish_file(out_path, out_lines, corrections, master_path)
                return True  # continue to next file but stop this one

            elif ch == "X":
                print(ch)
                _finish_file(out_path, out_lines, corrections, master_path)
                return False

            elif ch == "\x03":
                print("\nAborted.")
                return False

    _finish_file(out_path, out_lines, corrections, master_path)
    return True


def _finish_file(out_path, out_lines, corrections, master_path):
    # Build final corrections (skip None entries — keep name as-is)
    final = {k: v for k, v in corrections.items() if v is not None}
    corrected = apply_name_corrections(out_lines, final)
    APPENDED_DIR.mkdir(parents=True, exist_ok=True)
    append_sort_master(master_path, corrected)
    out_path.rename(APPENDED_DIR / out_path.name)
    resolved = sum(1 for v in corrections.values() if v is not None)
    skipped = sum(1 for v in corrections.values() if v is None)
    print(f"\nResolved: {resolved}  Skipped (kept as-is): {skipped}")
    print(f"Appended: {out_path.name} → {master_path.name}\n")
```

**Step 3: Add main()**

```python
def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        name = arg if arg.endswith(".out") else arg + ".out"
        out_path = FORMATTED_DIR / name
        if not out_path.exists():
            print(f"File not found: {out_path}")
            sys.exit(1)
        process_file(out_path)
    else:
        for f in sorted(FORMATTED_DIR.glob("*.out")):
            if not process_file(f):
                return


if __name__ == "__main__":
    main()
```

**Step 4: Run all tests to confirm nothing broken**

```bash
python3 -m pytest .claude/skills/musmem-contests/python/test_append_and_verify.py -v
```

Expected: all PASS.

**Step 5: Commit**

```bash
git add .claude/skills/musmem-contests/python/append_and_verify.py
git commit -m "feat: interactive UI and main entry point for append_and_verify"
```

---

## Task 8: Add append_and_verify.sh to SKILL.md run_format section and update settings

**Step 1: Add to settings.local.json**

Add to the `allow` array in `.claude/settings.local.json`:

```json
"Bash(~/workspace/skills/musmemContests/python/append_and_verify.sh*)"
```

**Step 2: Run the full test suite one final time**

```bash
python3 -m pytest .claude/skills/musmem-contests/python/test_append_and_verify.py -v
```

**Step 3: Commit settings**

```bash
git add .claude/settings.local.json
git commit -m "chore: allow append_and_verify.sh in settings"
```

---

## Notes for implementer

- The `.sh` script path uses `musmemContests` (the symlink path), not `musmemSkills/.claude/skills/musmem-contests` — follow the same pattern as `review_flags.sh`.
- Master files may not exist yet (first run) — `append_sort_master` handles this gracefully.
- `APPENDED_DIR` must be created with `mkdir -p` before moving files.
- The `[n]` suffix uses square brackets literally: `Smith, John [2]` — space before bracket.
- `get_next_disambig` with a base name not in master at all returns `base [2]` — this is correct because pressing `N` means "new different person" implying the incoming plain name is being kept but the conflict exists, so we'd only call this when there IS a match. If no match exists, the name passes through unchanged.

Wait — re-read: `get_next_disambig` should only be called when the base name already exists in master. The `N` option says "new athlete — use next [n]". So if master has `Smith, John`, pressing `N` gives `Smith, John [2]`. If master has `Smith, John` and `Smith, John [2]`, pressing `N` gives `Smith, John [3]`. The function is correct as written.
