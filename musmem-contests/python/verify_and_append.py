#!/usr/bin/env python3
"""
verify_and_append.py — Verify new athlete names against master files, resolve
conflicts interactively, then append corrected .out files to the master.

Usage:
    python3 verify_and_append.py                              # all pending .out files
    python3 verify_and_append.py 2025_arnold_classic-ifbb-male  # specific file

Keys (no RETURN needed):
    1-N  Match to candidate N (corrects spelling in .out to master spelling)
    N    New athlete — assign next [n] suffix
    D    Details — list all master records for a candidate
    S    Skip — keep name as-is
    9    Back to previous conflict
    0    Done for now (prompt to append, stop this file)
    X    Exit all (prompt to append current file, stop remaining)
    Y/N  Confirm or skip append to master
"""

import json
import os
import re
import sys
import termios
import tty
from dataclasses import dataclass, field
from pathlib import Path

def _load_paths():
    config = Path(__file__).parents[2] / "config/paths.json"
    data = json.loads(config.read_text())
    return {k: Path(v).expanduser() for k, v in data.items()}

_PATHS = _load_paths()

FORMATTED_DIR  = _PATHS["formatted_folder"]
COMPLETED_DIR  = _PATHS["completed_folder"]
MASTER = {
    "male":   _PATHS["master_male"],
    "female": _PATHS["master_female"],
}
CYAN  = "\033[96m"
BOLD  = "\033[1m"
RESET = "\033[0m"


def strip_disambig(name: str) -> str:
    """Remove [n] suffix: 'Smith, John [2]' -> 'Smith, John'."""
    return re.sub(r'\s*\[\d+\]$', '', name).strip()


def base_name_of(name: str) -> str:
    return strip_disambig(name)


def get_next_disambig(base: str, all_master_names: set) -> str:
    """Return next available [n] for base name. Plain name counts as slot 1."""
    n = 2
    while f"{base} [{n}]" in all_master_names:
        n += 1
    return f"{base} [{n}]"


@dataclass
class AthleteEntry:
    full_name: str
    count: int = 0
    y0: int = 9999
    y1: int = 0
    divisions: list = field(default_factory=list)


def build_athlete_index(lines: list) -> dict:
    """
    Returns dict: base_name -> list[AthleteEntry] (one per [n] variant).
    Parses lines of format: Last, First [n]; year; contest; div-placing; ...
    """
    entries = {}  # full_name -> AthleteEntry

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
    index = {}
    for full_name, entry in entries.items():
        base = base_name_of(full_name)
        if base not in index:
            index[base] = []
        index[base].append(entry)

    return index


def all_master_names(index: dict) -> set:
    """Flat set of all full names (including [n] variants) from index."""
    return {e.full_name for entries in index.values() for e in entries}


def soundex(name: str) -> str:
    """Classic Soundex algorithm."""
    name = name.upper()
    if not name:
        return ""
    table = str.maketrans("BFPVCGJKQSXZDTLMNR", "111122222222334556")
    keep = name[0]
    coded = name[1:].translate(table)
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
    """Return (last, first) from 'Last, First' or (name, '') if no comma."""
    base = base_name_of(name)
    if ", " in base:
        last, first = base.split(", ", 1)
        return last.strip(), first.strip()
    return base.strip(), ""


def word_key(name: str) -> str:
    """Sorted words of name — detects first/last swap."""
    base = base_name_of(name)
    words = re.sub(r"[^a-z ]", "", base.lower()).split()
    return "".join(sorted(words))


def find_candidates(new_name: str, index: dict) -> list:
    """
    Return list of AthleteEntry objects from index similar to new_name.
    Checks: soundex last (same first), soundex first (same last),
            edit distance <=2 on last (same first), word-order match.
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
        if not hit and new_last and ex_last and new_last.lower() == ex_last.lower():
            if new_first and ex_first and soundex(new_first) == soundex(ex_first):
                hit = True
        # edit distance <= 2 on last name (same first)
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


def parse_out_new_athletes(out_lines: list, master_names: set) -> set:
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


def apply_name_corrections(out_lines: list, corrections: dict) -> list:
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


def append_master(master_path: Path, new_lines: list) -> None:
    """Append new_lines to end of master_path."""
    with open(master_path, "a") as f:
        f.writelines(new_lines)


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
    divs = "/".join(entry.divisions[:4])
    year_range = f"{entry.y0}" if entry.y0 == entry.y1 else f"{entry.y0}\u2013{entry.y1}"
    return f"  {number}. {entry.full_name:<30} \u2014 {entry.count} contest{'s' if entry.count != 1 else ''}, {year_range}, {divs}"


def show_detail(entry: AthleteEntry, master_lines: list) -> None:
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


def contest_precheck(out_lines: list, master_lines: list, filename: str) -> None:
    """Extract year+contest from .out file and report if already in master."""
    year, contest = "", ""
    for line in out_lines:
        parts = line.strip().split("; ")
        if len(parts) >= 3:
            year, contest = parts[1].strip(), parts[2].strip()
            break
    if not contest:
        return
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}{BOLD}{filename}{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")
    incoming = sum(1 for l in out_lines if l.strip())
    if master_lines:
        existing = sum(
            1 for l in master_lines
            if len(l.strip().split("; ")) >= 3
            and l.strip().split("; ")[1].strip() == year
            and l.strip().split("; ")[2].strip() == contest
        )
        if existing:
            print(f"  WARNING: {contest} {year} already has {existing} records in master.")
        else:
            print(f"  {contest} {year} — not found in master.")
    print(f"  Incoming records: {incoming}")


def _prompt_and_append(out_path: Path, out_lines: list, corrections: dict,
                       master_path: Path) -> bool:
    """Apply corrections, prompt Y/N, append if confirmed. Returns True if appended."""
    final = {k: v for k, v in corrections.items() if v is not None}
    corrected = apply_name_corrections(out_lines, final)
    if corrections:
        resolved = sum(1 for v in corrections.values() if v is not None)
        skipped  = sum(1 for v in corrections.values() if v is None)
        print(f"\n  Resolved: {resolved}  Skipped (kept as-is): {skipped}")
    print(f"\nAppend {out_path.name} to {master_path.name}? (Y/N) ", end="", flush=True)
    while True:
        ch = getch().upper()
        if ch == "Y":
            print(ch)
            COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
            append_master(master_path, corrected)
            out_path.rename(COMPLETED_DIR / out_path.name)
            print(f"  Appended \u2192 {master_path.name}\n")
            return True
        elif ch == "N":
            print(ch)
            print(f"  Skipped \u2014 {out_path.name} left in formatted/\n")
            return False
        elif ch == "\x03":
            print("\nAborted.")
            return False


def process_file(out_path: Path) -> bool:
    """Returns True to continue to next file, False to stop all."""
    gender = get_gender(out_path.name)
    if gender not in MASTER:
        print(f"Cannot determine gender from filename: {out_path.name}")
        return True

    master_path = MASTER[gender]
    master_lines = master_path.read_text().splitlines(keepends=True) if master_path.exists() else []
    out_lines = out_path.read_text().splitlines(keepends=True)

    contest_precheck(out_lines, master_lines, out_path.name)

    index = build_athlete_index(master_lines)
    names = all_master_names(index)
    new_athletes = parse_out_new_athletes(out_lines, names)

    if not new_athletes:
        print(f"  No new athletes.")
        _prompt_and_append(out_path, out_lines, {}, master_path)
        return True

    conflicts = []
    for new_name in sorted(new_athletes):
        candidates = find_candidates(new_name, index)
        if candidates:
            conflicts.append((new_name, candidates))

    if not conflicts:
        print(f"  No name conflicts found.")
        _prompt_and_append(out_path, out_lines, {}, master_path)
        return True

    print(f"  {len(conflicts)} conflict(s) to resolve.")

    corrections = {}
    i = 0

    while i < len(conflicts):
        new_name, candidates = conflicts[i]

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

        next_n = get_next_disambig(base_name_of(new_name), names)
        print(f"  N  New athlete \u2192 {next_n}")
        print(f"  D  Details (then enter number)")
        print(f"  S  Skip (keep name as-is)")
        if i > 0:
            print(f"  9  Back")
        print(f"  0  Done for now (prompt to append, move to next file)")
        print(f"  X  Exit all (prompt to append, stop)")
        print("Choice: ", end="", flush=True)

        while True:
            ch = getch().upper()

            if ch.isdigit() and ch not in ("0", "9"):
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
                corrections[new_name] = None
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
                _prompt_and_append(out_path, out_lines, corrections, master_path)
                return True

            elif ch == "X":
                print(ch)
                _prompt_and_append(out_path, out_lines, corrections, master_path)
                return False

            elif ch == "\x03":
                print("\nAborted.")
                return False

    _prompt_and_append(out_path, out_lines, corrections, master_path)
    return True


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
