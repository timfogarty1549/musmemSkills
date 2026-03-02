#!/usr/bin/env python3
"""
review_flags.py — Interactively resolve <<<<-flagged lines in .out files.

Usage:
    python3 review_flags.py                           # all .out files with <<<< lines
    python3 review_flags.py 2025_olympia-ifbb-male    # specific file (with or without .out)

Keys (no RETURN needed):
    1  Accept as-is
    2  Re-split (alternative comma position)
    3  Asianize (restore original word order, no comma)
    4  DB lookup
    5  Enter manually (requires typing + RETURN)
    6  Skip (leave <<<< for now)
    9  Back to previous
    0  Done for now (write resolved, leave rest)
    x  Exit (write resolved, skip remaining files)
"""

import json
import os
import sys
import termios
import tty
import urllib.parse
import urllib.request
from pathlib import Path

FORMATTED_DIR = Path.home() / "workspace/musmem/formatted"
SEARCH_URL = "https://musclememory.org/api/search"

CYAN  = "\033[96m"
BOLD  = "\033[1m"
RESET = "\033[0m"


def getch():
    """Read a single character without requiring RETURN."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return os.read(fd, 1).decode()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def get_gender(filename):
    if "-male" in filename:
        return "male"
    elif "-female" in filename:
        return "female"
    return ""


def parse_line(line):
    """Strip <<<< and split into (name, rest). rest includes trailing semicolon."""
    line = line.rstrip()
    if line.endswith(" <<<<"):
        line = line[:-5].rstrip()
    parts = line.split("; ")
    return parts[0], "; ".join(parts[1:])


def original_order(name):
    """Convert 'Last, First' → 'First Last'."""
    if ", " in name:
        last, first = name.split(", ", 1)
        return f"{first} {last}"
    return name


def resplit(name):
    """Return alternative comma position, or None if not applicable."""
    words = original_order(name).split()
    if len(words) < 3:
        return None
    if ", " in name:
        first_count = len(name.split(", ", 1)[1].split())
    else:
        first_count = 0
    total = len(words)
    new_first = first_count + 1 if first_count < total - 1 else first_count - 1
    if new_first <= 0 or new_first >= total:
        return None
    return f"{' '.join(words[new_first:])}, {' '.join(words[:new_first])}"


def asianize(name):
    return name.replace(", ", " ")


def db_search(query, gender):
    params = urllib.parse.urlencode({
        "offset": 0, "limit": 20,
        "match": query, "gender": gender, "searchType": "anywhere"
    })
    try:
        with urllib.request.urlopen(f"{SEARCH_URL}?{params}", timeout=5) as r:
            data = json.loads(r.read())
            return [e["completeName"] for e in data.get("data", {}).get("names", [])]
    except Exception as e:
        print(f"\n  [DB error: {e}]")
        return []


def db_lookup(name, gender):
    orig = original_order(name)
    results = db_search(orig, gender)
    if not results:
        seen = set()
        for word in orig.split():
            if len(word) > 2:
                for r in db_search(word, gender):
                    if r not in seen:
                        seen.add(r)
                        results.append(r)
    return results


def collect_flagged(filepath):
    flagged = []
    with open(filepath) as f:
        for i, line in enumerate(f):
            if line.rstrip().endswith("<<<<"):
                flagged.append((i, line.rstrip()))
    return flagged


def apply_decisions(filepath, decisions):
    """Write resolved decisions to file. Skipped (None) lines keep their <<<<."""
    with open(filepath) as f:
        lines = f.readlines()
    for line_num, new_name in decisions.items():
        if new_name is None:
            continue
        name, rest = parse_line(lines[line_num])
        lines[line_num] = f"{new_name}; {rest}\n"
    with open(filepath, "w") as f:
        f.writelines(lines)


def review_file(filepath):
    gender = get_gender(filepath.name)
    flagged = collect_flagged(filepath)
    total = len(flagged)

    if total == 0:
        print(f"No <<<< lines in {filepath.name}")
        return

    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}{BOLD}{filepath.name}  ({total} flagged){RESET}")
    print(f"{CYAN}{'='*60}{RESET}")

    decisions = {}  # line_num -> new_name | None (skip)
    i = 0

    while i < total:
        line_num, line = flagged[i]
        name, rest = parse_line(line)
        alt = resplit(name)
        prev = decisions.get(line_num)

        print(f"\n[{i+1}/{total}] {name}; {rest}")
        if prev is not None:
            print(f"  (previous: {prev})")
        elif prev is None and line_num in decisions:
            print(f"  (previous: skip)")

        print(f"  1) Accept:   {name}")
        print(f"  2) Re-split: {alt}" if alt else "  2) Re-split: (n/a)")
        print(f"  3) Asianize: {asianize(name)}")
        print(f"  4) DB lookup")
        print(f"  5) Enter manually")
        print(f"  6) Skip")
        if i > 0:
            print(f"  9) Back")
        print(f"  0) Done for now")
        print(f"  x) Exit all")
        print("Choice: ", end="", flush=True)

        while True:
            ch = getch()

            if ch == "1":
                print(ch)
                decisions[line_num] = name
                i += 1
                break

            elif ch == "2" and alt:
                print(ch)
                decisions[line_num] = alt
                i += 1
                break

            elif ch == "3":
                print(ch)
                decisions[line_num] = asianize(name)
                i += 1
                break

            elif ch == "4":
                print(ch)
                print(f"  Searching '{original_order(name)}'...")
                matches = db_lookup(name, gender)
                if matches:
                    print("  DB matches:")
                    for j, m in enumerate(matches[:9], 1):
                        print(f"    {j}) {m}")
                    print("  Pick number or any other key to cancel: ", end="", flush=True)
                    pick = getch()
                    idx = ord(pick) - ord("1")
                    if 0 <= idx < len(matches[:9]):
                        print(pick)
                        decisions[line_num] = matches[idx]
                        i += 1
                        break
                    else:
                        print("  (cancelled)")
                else:
                    print("  No matches found.")
                print("Choice: ", end="", flush=True)

            elif ch == "5":
                print(ch)
                new_name = input("  Enter name: ").strip()
                if new_name:
                    decisions[line_num] = new_name
                    i += 1
                    break
                print("Choice: ", end="", flush=True)

            elif ch == "6":
                print(ch)
                decisions[line_num] = None
                i += 1
                break

            elif ch == "9" and i > 0:
                print(ch)
                prev_line_num = flagged[i - 1][0]
                prev_val = decisions.pop(prev_line_num, "(none)")
                print(f"  (going back — was: {prev_val})")
                i -= 1
                break

            elif ch == "0":
                print(ch)
                _finish(filepath, decisions, flagged)
                return True

            elif ch in ("x", "X"):
                print(ch)
                _finish(filepath, decisions, flagged)
                return False

            elif ch == "\x03":  # Ctrl+C
                print("\nAborted.")
                return False

    _finish(filepath, decisions, flagged)
    return True


def _finish(filepath, decisions, flagged):
    resolved = sum(1 for v in decisions.values() if v is not None)
    skipped = sum(1 for v in decisions.values() if v is None)
    remaining = len(flagged) - len(decisions)
    apply_decisions(filepath, decisions)
    print(f"\nResolved: {resolved}  Skipped: {skipped}  <<<< remaining: {skipped + remaining}")
    print(f"Written:  {filepath.name}\n")


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        name = arg if arg.endswith(".out") else arg + ".out"
        filepath = FORMATTED_DIR / name
        if not filepath.exists():
            print(f"File not found: {filepath}")
            sys.exit(1)
        review_file(filepath)
    else:
        for f in sorted(FORMATTED_DIR.glob("*.out")):
            with open(f) as fh:
                if any("<<<<" in line for line in fh):
                    if not review_file(f):
                        return


if __name__ == "__main__":
    main()
