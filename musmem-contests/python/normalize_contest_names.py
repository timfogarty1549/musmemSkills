#!/usr/bin/env python3
"""
normalize_contest_names.py — Rename contest flat files to use canonical
MuscleMemory contest titles, based on contest-title-normalization-audit.md.

Operates on files in 1-incoming/. Updates the filename and 't' line in-place.
Files are never deleted unless a rename succeeds.

Usage:
    python3 normalize_contest_names.py --all
    python3 normalize_contest_names.py 2022_arnold_amateur-ifbb-male.txt
    python3 normalize_contest_names.py '*10x*'    # quote pattern to prevent shell expansion

For each matched file with a non-canonical title, shows the proposed change
and prompts Y/N/A(yes-all)/X(exit) before applying.
"""

import argparse
import json
import os
import re
import sys
import termios
import tty
from pathlib import Path


AUDIT_FILE  = Path(__file__).parents[1] / "contest-title-normalization-audit.md"
CONFIG_FILE = Path(__file__).parents[2] / "config/paths.json"

CYAN   = "\033[96m"
BOLD   = "\033[1m"
YELLOW = "\033[93m"
RESET  = "\033[0m"


def load_incoming_dir():
    data = json.loads(CONFIG_FILE.read_text())
    return Path(data["incoming_folder"]).expanduser()


def load_mapping():
    """Parse audit file → {source_title: canonical_title}."""
    mapping = {}
    canonical = None
    for line in AUDIT_FILE.read_text().splitlines():
        if line.startswith("## "):
            canonical = line[3:].strip()
        elif line.startswith("- ") and canonical:
            rest = line[2:].strip()
            m = re.match(r"^\d{4}\s+-\s+(.+)$", rest)
            if m:
                source = m.group(1).strip()
                if source != canonical:
                    mapping[source] = canonical
    return mapping


def title_to_slug(title):
    """'Contest Name - ORG' → (contest_slug, org_slug)."""
    parts = title.rsplit(" - ", 1)
    contest = parts[0].strip()
    org     = parts[1].strip() if len(parts) == 2 else ""
    contest_slug = re.sub(r"[^a-z0-9 ]", "", contest.lower()).replace(" ", "_")
    org_slug     = re.sub(r"[^a-z0-9 ]", "", org.lower()).replace(" ", "_")
    return contest_slug, org_slug


def extract_gender(filename):
    if "-male" in filename:
        return "male"
    if "-female" in filename:
        return "female"
    return ""


def extract_year(lines):
    for line in lines:
        if line.startswith("y "):
            return line[2:].strip()
    return ""


def extract_title(lines):
    for line in lines:
        if line.startswith("t "):
            return line[2:].strip()
    return ""


def canonical_filename(canonical_title, year, gender):
    contest_slug, org_slug = title_to_slug(canonical_title)
    if org_slug:
        return f"{year}_{contest_slug}-{org_slug}-{gender}.txt"
    return f"{year}_{contest_slug}-{gender}.txt"


def getch():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return os.read(fd, 1).decode()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def apply_change(path, lines, canonical, new_filename):
    new_lines = []
    for line in lines:
        if line.startswith("t "):
            new_lines.append(f"t {canonical}\n")
        else:
            new_lines.append(line)
    dest = path.parent / new_filename if new_filename else path
    dest.write_text("".join(new_lines))
    if new_filename and dest != path:
        path.unlink()
        print(f"  Applied: {path.name} → {dest.name}")
    else:
        print(f"  Applied: updated t line in {path.name}")


def main():
    parser = argparse.ArgumentParser(
        description="Normalize contest titles in 1-incoming/ flat files."
    )
    parser.add_argument("--all", action="store_true", help="Process all files")
    parser.add_argument("files", nargs="*", help="Filenames or glob patterns")
    args = parser.parse_args()

    incoming = load_incoming_dir()
    mapping  = load_mapping()

    # Collect candidate paths
    if args.all:
        candidates = sorted(incoming.glob("*.txt"))
    elif args.files:
        candidates = []
        for pat in args.files:
            if not pat.endswith(".txt"):
                pat += ".txt"
            matched = sorted(incoming.glob(pat))
            if not matched:
                p = incoming / pat
                if p.exists():
                    matched = [p]
                else:
                    print(f"No files matching: {pat}")
            candidates.extend(matched)
    else:
        parser.print_help()
        sys.exit(1)

    if not candidates:
        print("No matching files found.")
        sys.exit(0)

    # Filter to files that actually need a title change
    work = []
    for path in candidates:
        lines = path.read_text().splitlines(keepends=True)
        title = extract_title(lines)
        canonical = mapping.get(title)
        if canonical:
            work.append((path, lines, title, canonical))

    if not work:
        print(f"No title changes needed in {len(candidates)} file(s).")
        return

    print(f"Found {len(work)} file(s) with titles to normalize.\n")

    yes_all = False
    for path, lines, current_title, canonical in work:
        year   = extract_year(lines)
        gender = extract_gender(path.name)
        new_fn = canonical_filename(canonical, year, gender) if year and gender else None

        print(f"{CYAN}{BOLD}{path.name}{RESET}")
        print(f"  title:  {YELLOW}{current_title}{RESET}")
        print(f"  → canonical: {BOLD}{canonical}{RESET}")
        if new_fn and new_fn != path.name:
            print(f"  → filename:  {BOLD}{new_fn}{RESET}")

        if yes_all:
            apply_change(path, lines, canonical, new_fn)
            continue

        print("  Apply? [y]es / [n]o / [a]ll / [x]exit  ", end="", flush=True)
        ch = getch().lower()
        print(ch)

        if ch == "x":
            print("Exiting.")
            break
        elif ch == "a":
            yes_all = True
            apply_change(path, lines, canonical, new_fn)
        elif ch == "y":
            apply_change(path, lines, canonical, new_fn)
        else:
            print("  Skipped.")
        print()


if __name__ == "__main__":
    main()
