#!/usr/bin/env python3
"""
review_flags.py — Interactively resolve <<<<-flagged lines in .out files.

Usage:
    python3 review_flags.py                           # all .out files with <<<< lines
    python3 review_flags.py 2025_olympia-ifbb-male    # specific file (with or without .out)
    python3 review_flags.py --accept-dict             # auto-apply dict matches, prompt only for unknowns
    python3 review_flags.py --accept-dict 2025_olympia-ifbb-male

Keys (no RETURN needed):
    1  Accept as-is
    2  Re-split (alternative comma position)
    3  Asianize (restore original word order, no comma)
    4  Asianize with dash (restore original word order, no comma, with dash)
    5  Enter manually (requires typing + RETURN)
    6  DB lookup
    7  Previous (cached name from earlier decision)
    8  Skip (leave <<<< for now)
    b  Back to previous
    d  Done for now (write resolved, leave rest)
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

def _load_config():
    base = Path(__file__).parents[2] / "config"
    paths = json.loads((base / "paths.json").read_text())
    apis  = json.loads((base / "apis.json").read_text())
    return (
        {k: Path(v).expanduser() for k, v in paths.items()},
        apis,
    )

_PATHS, _APIS = _load_config()

FORMATTED_DIR    = _PATHS["formatted_folder"]
REVIEWED_DIR     = _PATHS["reviewed_folder"]
WORKING_DATA_DIR = Path.home() / "workspace/musmem/working_data"
NAMES_FILE       = WORKING_DATA_DIR / "review-athlete-names.dat"
SEARCH_URL       = _APIS["musclememory_org"] + _APIS["endpoints"]["search"]

CYAN   = "\033[96m"
BOLD   = "\033[1m"
YELLOW = "\033[93m"
RESET  = "\033[0m"


def getch():
    """Read a single character without requiring RETURN."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return os.read(fd, 1).decode()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def load_name_cache():
    """Load original->chosen name mappings from the dat file."""
    cache = {}
    if not NAMES_FILE.exists():
        return cache
    with open(NAMES_FILE) as f:
        for line in f:
            line = line.strip()
            if ":" in line:
                orig, chosen = line.split(":", 1)
                cache[orig] = chosen
    return cache


def write_name_cache(cache):
    """Rewrite the dat file from the current cache dict."""
    WORKING_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(NAMES_FILE, "w") as f:
        for orig, ch in sorted(cache.items()):
            f.write(f"{orig}:{ch}\n")


def save_name_cache_entry(cache, original, chosen):
    """Update cache dict and rewrite the dat file."""
    cache[original] = chosen
    write_name_cache(cache)


def remove_name_cache_entry(cache, original):
    """Remove an entry from the cache dict and rewrite the dat file."""
    if original in cache:
        del cache[original]
        write_name_cache(cache)


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
        return name
    if ", " in name:
        first_count = len(name.split(", ", 1)[1].split())
    else:
        first_count = 0
    total = len(words)
    new_first = first_count + 1 if first_count < total - 1 else first_count - 1
    if new_first <= 0 or new_first >= total:
        return name
    return f"{' '.join(words[new_first:])}, {' '.join(words[:new_first])}"


def asianize(name):
    return resplit(name).replace(", ", " ")

def asianize_with_dash(name):
    return resplit(name).replace(", ", "~").replace(" ", "-").replace("~", " ")

def db_search(query, gender):
    params = urllib.parse.urlencode({
        "offset": 0, "limit": 20,
        "match": query, "gender": gender, "searchType": "anywhere"
    })
    req = urllib.request.Request(
        f"{SEARCH_URL}?{params}",
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
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
    """Write resolved decisions to REVIEWED_DIR. Skipped (None) lines keep their <<<<."""
    with open(filepath) as f:
        lines = f.readlines()
    for line_num, new_name in decisions.items():
        if new_name is None:
            continue
        name, rest = parse_line(lines[line_num])
        lines[line_num] = f"{new_name}; {rest}\n"
    REVIEWED_DIR.mkdir(parents=True, exist_ok=True)
    dest = REVIEWED_DIR / filepath.name
    with open(dest, "w") as f:
        f.writelines(lines)


def review_file(filepath, name_cache, accept_dict=False):
    gender = get_gender(filepath.name)
    flagged = collect_flagged(filepath)
    total = len(flagged)

    if total == 0:
        print(f"No <<<< lines in {filepath.name}")
        return

    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}{BOLD}{filepath.name}  ({total} flagged){RESET}")
    print(f"{CYAN}{'='*60}{RESET}")

    decisions      = {}  # line_num -> new_name | None (skip)
    new_cache_keys = set()  # names added to cache during this session
    backed         = False
    i = 0

    while i < total:
        line_num, line = flagged[i]
        name, rest = parse_line(line)
        alt     = resplit(name)
        cached  = name_cache.get(name)
        prev    = decisions.get(line_num)

        if accept_dict and cached and not backed:
            decisions[line_num] = cached
            print(f"\n[{i+1}/{total}] {name}; {rest}")
            print(f"  [dict] {YELLOW}{cached}{RESET}")
            i += 1
            continue

        backed = False

        print(f"\n[{i+1}/{total}] {name}; {rest}")
        if line_num in decisions:
            print(f"  (previous: {prev if prev is not None else 'skip'})")

        print(f"  1) Accept:   {name}")
        print(f"  2) Re-split: {alt}" if alt else "  2) Re-split: (n/a)")
        print(f"  3) Asianize: {asianize(name)}")
        print(f"  4) Asianize with dash: {asianize_with_dash(name)}")
        print(f"  5) Enter manually")
        print(f"  6) DB lookup")
        print(f"  7) Previous: {YELLOW}{cached}{RESET}" if cached else "  7) Previous: (none)")
        print(f"  8) Skip")
        if i > 0:
            print(f"  b) Back")
        print(f"  d) Done for now")
        print(f"  x) Exit all")
        print("Choice: ", end="", flush=True)

        while True:
            ch = getch()

            if ch == "1":
                print(ch)
                decisions[line_num] = name
                save_name_cache_entry(name_cache, name, name)
                new_cache_keys.add(name)
                i += 1
                break

            elif ch == "2" and alt:
                print(ch)
                decisions[line_num] = alt
                save_name_cache_entry(name_cache, name, alt)
                new_cache_keys.add(name)
                i += 1
                break

            elif ch == "3":
                print(ch)
                result = asianize(name)
                decisions[line_num] = result
                save_name_cache_entry(name_cache, name, result)
                new_cache_keys.add(name)
                i += 1
                break

            elif ch == "4":
                print(ch)
                result = asianize_with_dash(name)
                decisions[line_num] = result
                save_name_cache_entry(name_cache, name, result)
                new_cache_keys.add(name)
                i += 1
                break

            elif ch == "7" and cached:
                print(ch)
                decisions[line_num] = cached
                i += 1
                break

            elif ch == "5":
                print(ch)
                new_name = input("  Enter name: ").strip()
                if new_name:
                    decisions[line_num] = new_name
                    save_name_cache_entry(name_cache, name, new_name)
                    new_cache_keys.add(name)
                    i += 1
                    break
                print("Choice: ", end="", flush=True)

            elif ch == "6":
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
                        save_name_cache_entry(name_cache, name, matches[idx])
                        new_cache_keys.add(name)
                        i += 1
                        break
                    else:
                        print("  (cancelled)")
                else:
                    print("  No matches found.")
                print("Choice: ", end="", flush=True)

            elif ch == "8" or ch == "s":
                print(ch)
                decisions[line_num] = None
                i += 1
                break

            elif ch in ("b", "B") and i > 0:
                print(ch)
                prev_line_num = flagged[i - 1][0]
                prev_name = parse_line(flagged[i - 1][1])[0]
                prev_val = decisions.pop(prev_line_num, "(none)")
                if prev_name in new_cache_keys:
                    remove_name_cache_entry(name_cache, prev_name)
                    new_cache_keys.discard(prev_name)
                    print(f"  (removed dict entry for '{prev_name}')")
                print(f"  (going back — was: {prev_val})")
                backed = True
                i -= 1
                break

            elif ch in ("d", "D"):
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
    skipped  = sum(1 for v in decisions.values() if v is None)
    remaining = len(flagged) - len(decisions)
    apply_decisions(filepath, decisions)
    print(f"\nResolved: {resolved}  Skipped: {skipped}  <<<< remaining: {skipped + remaining}")
    print(f"Written:  4-reviewed/{filepath.name}\n")


def main():
    name_cache  = load_name_cache()
    args        = sys.argv[1:]
    accept_dict = "--accept-dict" in args
    args        = [a for a in args if a != "--accept-dict"]

    if args:
        arg      = args[0]
        name     = arg if arg.endswith(".out") else arg + ".out"
        filepath = FORMATTED_DIR / name
        if not filepath.exists():
            print(f"File not found: {filepath}")
            sys.exit(1)
        review_file(filepath, name_cache, accept_dict)
    else:
        for f in sorted(FORMATTED_DIR.glob("*.out")):
            with open(f) as fh:
                if any("<<<<" in line for line in fh):
                    if not review_file(f, name_cache, accept_dict):
                        return


if __name__ == "__main__":
    main()
