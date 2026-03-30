#!/usr/bin/env python3
"""
append_to_master.py — Append completed .out files to the gender-specific
staging .dat files in 6-appended/.

Reads from: 5-completed/
Writes to:  6-appended/append-male.dat  or  6-appended/append-female.dat

Files in 5-completed/ are never moved or deleted.

Usage:
    python3 append_to_master.py                              # all files in 5-completed/
    python3 append_to_master.py 2025_arnold_classic-ifbb-male  # specific file

Keys (no RETURN needed):
    Y    Append this file to 6-appended/append-{gender}.dat
    N    Skip this file (leave in 5-completed/)
    X    Exit (stop processing remaining files)
"""

import json
import os
import sys
import termios
import tty
from pathlib import Path


def _load_paths():
    config = Path(__file__).parents[2] / "config/paths.json"
    data = json.loads(config.read_text())
    return {k: Path(v).expanduser() for k, v in data.items()}

_PATHS = _load_paths()

COMPLETED_DIR = _PATHS["completed_folder"]
APPENDED_DIR  = _PATHS["appended_folder"]
APPEND_DAT = {
    "male":   APPENDED_DIR / "append-male.dat",
    "female": APPENDED_DIR / "append-female.dat",
}
CYAN  = "\033[96m"
BOLD  = "\033[1m"
RESET = "\033[0m"


def get_gender(filename: str) -> str:
    if "-male" in filename:
        return "male"
    elif "-female" in filename:
        return "female"
    return ""


def getch():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return os.read(fd, 1).decode()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def process_file(out_path: Path) -> bool:
    """Returns True to continue to next file, False to stop all."""
    gender = get_gender(out_path.name)
    if gender not in APPEND_DAT:
        print(f"Cannot determine gender from filename: {out_path.name}")
        return True

    dest_dat = APPEND_DAT[gender]
    existing_lines = dest_dat.read_text().splitlines(keepends=True) if dest_dat.exists() else []
    out_lines = out_path.read_text().splitlines(keepends=True)

    # Extract year and contest name from first data line
    year, contest = "", ""
    for line in out_lines:
        parts = line.strip().split("; ")
        if len(parts) >= 3:
            year, contest = parts[1].strip(), parts[2].strip()
            break

    record_count = sum(1 for l in out_lines if l.strip())

    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}{BOLD}{out_path.name}{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")

    if contest:
        existing = sum(
            1 for l in existing_lines
            if len(l.strip().split("; ")) >= 3
            and l.strip().split("; ")[1].strip() == year
            and l.strip().split("; ")[2].strip() == contest
        ) if existing_lines else 0
        if existing:
            print(f"  WARNING: {contest} {year} already has {existing} records in {dest_dat.name}.")
        else:
            print(f"  {contest} {year} \u2014 not found in {dest_dat.name}.")

    print(f"  Records to append: {record_count}")
    print(f"\nAppend to {dest_dat.name}? (Y/N/X) ", end="", flush=True)

    while True:
        ch = getch().upper()
        if ch == "Y":
            print(ch)
            APPENDED_DIR.mkdir(parents=True, exist_ok=True)
            with open(dest_dat, "a") as f:
                f.writelines(out_lines)
            print(f"  Appended \u2192 {dest_dat.name}\n")
            return True
        elif ch == "N":
            print(ch)
            print(f"  Skipped \u2014 {out_path.name} left in 5-completed/\n")
            return True
        elif ch == "X":
            print(ch)
            print("  Exiting.\n")
            return False
        elif ch == "\x03":
            print("\nAborted.")
            return False


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        name = arg if arg.endswith(".out") else arg + ".out"
        out_path = COMPLETED_DIR / name
        if not out_path.exists():
            print(f"File not found: {out_path}")
            sys.exit(1)
        process_file(out_path)
    else:
        for f in sorted(COMPLETED_DIR.glob("*.out")):
            if not process_file(f):
                return


if __name__ == "__main__":
    main()
