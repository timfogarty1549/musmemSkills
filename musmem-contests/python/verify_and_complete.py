#!/usr/bin/env python3
"""
verify_and_complete.py — Verify new athlete names against master files, resolve
conflicts interactively, then write the corrected .out file to completed/.

Usage:
    python3 verify_and_complete.py                              # all pending .out files
    python3 verify_and_complete.py 2025_arnold_classic-ifbb-male  # specific file
    python3 verify_and_complete.py --max-gap 10 2025_arnold_classic-ifbb-male

Keys (no RETURN needed):
    1-N  Match to candidate N (corrects spelling in .out to master spelling)
    N    New athlete — assign next [n] suffix
    D    Details — list all master records for a candidate
    S    Skip — keep name as-is
    9    Back to previous conflict
    0    Done for now (prompt to write, stop this file)
    X    Exit all (prompt to write, stop remaining)
    Y/N  Confirm or skip writing to completed/
"""

import argparse
import json
import os
import re
import sys
import termios
import tty
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


def _load_paths():
    config = Path(__file__).parents[2] / "config/paths.json"
    data = json.loads(config.read_text())
    return {k: Path(v).expanduser() for k, v in data.items()}

_PATHS = _load_paths()

FORMATTED_DIR  = _PATHS["reviewed_folder"]
COMPLETED_DIR  = _PATHS["completed_folder"]
MASTER = {
    "male":   _PATHS["master_male"],
    "female": _PATHS["master_female"],
}
CYAN  = "\033[96m"
BOLD  = "\033[1m"
YELLOW = "\033[93m"
RESET = "\033[0m"


# ---------------------------------------------------------------------------
# Special character code mapping (from SpecialChars.ts replaceUtf)
# Keys are ordered longest-first to prevent partial matches during replacement.
# ---------------------------------------------------------------------------

_SPECIAL_CODES: dict = {
    "a''": "a'",
    "O''": "Ó",
    "o''": "ó",
    "D---": "Đ",
    "d---": "đ",
    "C--": "Ç",
    "c--": "ç",
    "D--": "Ð",
    "d--": "ð",
    "S--": "Ş",
    "s--": "ş",
    "A:": "Ä",
    "a:": "ä",
    "A`": "À",
    "a`": "à",
    "A'": "Á",
    "a'": "á",
    "A^": "Â",
    "a^": "â",
    "a~": "ã",
    "A@": "Å",
    "a@": "å",
    "A*": "Ă",
    "a*": "ă",
    "a_": "ā",
    "A_": "Ā",
    "C^": "Č",
    "c^": "č",
    "C'": "Ć",
    "c'": "ć",
    "E:": "Ë",
    "e:": "ë",
    "E`": "È",
    "e`": "è",
    "E'": "É",
    "e'": "é",
    "e^": "ě",
    "E.": "Ė",
    "e.": "ė",
    "e_": "ē",
    "E_": "Ē",
    "g^": "ģ",
    "I`": "Ì",
    "i`": "ì",
    "I'": "Í",
    "i'": "í",
    "I.": "İ",
    "i_": "ī",
    "I_": "Ī",
    "L/": "Ł",
    "l/": "ł",
    "N~": "Ñ",
    "n~": "ñ",
    "n'": "Ņ",
    "N^": "Ň",
    "n^": "ň",
    "O`": "Ò",
    "o`": "ò",
    "o^": "ô",
    "O~": "Õ",
    "o~": "õ",
    "O:": "Ö",
    "o:": "ö",
    "O/": "Ø",
    "o/": "ø",
    "r^": "ř",
    "S'": "Ś",
    "s'": "ś",
    "S^": "Š",
    "s^": "š",
    "s*": "ß",
    "U^": "Û",
    "u^": "û",
    "U:": "Ü",
    "u:": "ü",
    "u@": "ů",
    "U_": "Ū",
    "u_": "ū",
    "U'": "Ú",
    "u'": "ú",
    "y:": "ÿ",
    "Y:": "Ÿ",
    "Y'": "Ý",
    "y'": "ý",
    "Z^": "Ž",
    "z^": "ž",
}

_SPECIAL_CODE_RE = re.compile(
    "|".join(re.escape(k) for k in sorted(_SPECIAL_CODES, key=len, reverse=True))
)


def expand_special_codes(s: str) -> str:
    """Expand internal special char codes to unicode: 'n~' -> 'ñ'."""
    return _SPECIAL_CODE_RE.sub(lambda m: _SPECIAL_CODES[m.group(0)], s)


def strip_to_ascii(s: str) -> str:
    """
    Normalize a name to plain lowercase ASCII for comparison.
    Handles both unicode diacritics and internal special codes (n~, etc.).
    'Pen~a' -> 'pena', 'Peña' -> 'pena', 'Pena' -> 'pena'
    """
    s = expand_special_codes(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


# ---------------------------------------------------------------------------
# Name utility functions
# ---------------------------------------------------------------------------

def strip_disambig(name: str) -> str:
    """Remove [n] suffix: 'Smith, John [2]' -> 'Smith, John'."""
    return re.sub(r"\s*\[\d+\]$", "", name).strip()


def base_name_of(name: str) -> str:
    return strip_disambig(name)


def strip_generational_suffix(first: str) -> str:
    """Remove Jr/Sr/II/III/IV from end of first name portion."""
    return re.sub(r"\s+(Jr\.?|Sr\.?|II|III|IV)\s*$", "", first, flags=re.IGNORECASE).strip()


def get_next_disambig(base: str, all_names: set) -> str:
    """Return next available [n] for base name. Plain name counts as slot 1."""
    n = 2
    while f"{base} [{n}]" in all_names:
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
    entries = {}

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
        div_placing = parts[3]
        div = div_placing.split("-")[0] if "-" in div_placing else div_placing

        if full_name not in entries:
            entries[full_name] = AthleteEntry(full_name=full_name)
        e = entries[full_name]
        e.count += 1
        e.y0 = min(e.y0, year)
        e.y1 = max(e.y1, year)
        if div not in e.divisions:
            e.divisions.append(div)

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


def name_parts(name: str):
    """Return (last, first) from 'Last, First' or (name, '') if no comma."""
    base = base_name_of(name)
    if ", " in base:
        last, first = base.split(", ", 1)
        return last.strip(), first.strip()
    return base.strip(), ""


def word_key(name: str) -> str:
    """Sorted ASCII words of name — detects first/last swap and word-order variants."""
    s = strip_to_ascii(base_name_of(name))
    words = re.sub(r"[^a-z ]", "", s).split()
    return "".join(sorted(words))


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
            prev = ""
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
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]


def get_incoming_year(out_lines: list) -> int:
    """Extract contest year from first data line of .out file."""
    for line in out_lines:
        parts = line.strip().split("; ")
        if len(parts) >= 2:
            try:
                return int(parts[1].strip())
            except ValueError:
                pass
    return 0


# ---------------------------------------------------------------------------
# Candidate matching
# ---------------------------------------------------------------------------

@dataclass
class CandidateMatch:
    entry: AthleteEntry
    match_types: list      # strategies that found this match, e.g. ['exact', 'diacritic']
    temporal_gap: int      # incoming_year - entry.y1 (positive = years since last seen)


def _temporal_gap(entry: AthleteEntry, incoming_year: int) -> int:
    if not incoming_year or entry.y1 == 0:
        return 0
    return incoming_year - entry.y1


def find_all_candidates(name: str, index: dict, incoming_year: int, max_gap: int) -> list:
    """
    Find all master candidates for a given incoming name using a six-step pipeline
    followed by soundex and edit-distance fallbacks.

    Returns list[CandidateMatch], deduplicated by entry.full_name.
    Auto-accept is appropriate only when is_auto_accept() returns True.
    """
    found: dict = {}  # full_name -> CandidateMatch

    def add(entry: AthleteEntry, strategy: str):
        gap = _temporal_gap(entry, incoming_year)
        if entry.full_name in found:
            if strategy not in found[entry.full_name].match_types:
                found[entry.full_name].match_types.append(strategy)
        else:
            found[entry.full_name] = CandidateMatch(entry=entry, match_types=[strategy], temporal_gap=gap)

    base = base_name_of(name)
    last, first = name_parts(name)
    first_no_gen = strip_generational_suffix(first)

    # ------------------------------------------------------------------
    # Step 1: Exact base-name match
    # Catches: exact spelling, [n] variants (all grouped under same base),
    # and generational suffix variants (Jr, Sr, II, III, IV).
    # ------------------------------------------------------------------
    if base in index:
        for entry in index[base]:
            add(entry, "exact")

    # Incoming has generational suffix → also check master without it
    if first_no_gen != first:
        no_gen_base = f"{last}, {first_no_gen}" if first_no_gen else last
        if no_gen_base in index:
            for entry in index[no_gen_base]:
                add(entry, "exact")

    # Incoming lacks generational suffix → also check master with Jr/Sr/II/III/IV
    else:
        for suffix in ("Jr", "Sr", "II", "III", "IV"):
            with_gen = f"{last}, {first} {suffix}" if first else f"{last}, {suffix}"
            if with_gen in index:
                for entry in index[with_gen]:
                    add(entry, "exact")

    # ------------------------------------------------------------------
    # Step 2: Diacritic normalization
    # Normalizes both special codes (n~) and unicode (ñ) to plain ASCII.
    # Catches: Pena ↔ Pen~a ↔ Peña
    # ------------------------------------------------------------------
    norm_incoming = strip_to_ascii(name)
    for base_key, entries in index.items():
        if base_key == base:
            continue  # already handled in step 1
        if strip_to_ascii(base_key) == norm_incoming:
            for entry in entries:
                add(entry, "diacritic")

    # ------------------------------------------------------------------
    # Step 3: Name part subset/superset
    # Catches: Lisa Smith ↔ Lisa Marie Smith, partial Latin surnames.
    # Requires last name to match (normalized). Minimum 2 words in common.
    # ------------------------------------------------------------------
    incoming_words = set(re.sub(r"[^a-z ]", "", norm_incoming.replace(",", "")).split())
    for base_key, entries in index.items():
        if base_key == base:
            continue
        norm_key = strip_to_ascii(base_key)
        master_words = set(re.sub(r"[^a-z ]", "", norm_key.replace(",", "")).split())
        if incoming_words == master_words:
            continue  # identical — already caught or will be caught by diacritic step
        if len(incoming_words & master_words) < 2:
            continue
        m_last, _ = name_parts(base_key)
        if strip_to_ascii(last) != strip_to_ascii(m_last):
            continue
        if incoming_words.issubset(master_words) or master_words.issubset(incoming_words):
            for entry in entries:
                add(entry, "subset")

    # ------------------------------------------------------------------
    # Step 4: Space normalization
    # Catches: Shu Xiao Fan ↔ Shu Xiaofan ↔ ShuXiaofan
    # ------------------------------------------------------------------
    nospace_incoming = re.sub(r"[^a-z]", "", norm_incoming)
    for base_key, entries in index.items():
        if base_key == base:
            continue
        nospace_key = re.sub(r"[^a-z]", "", strip_to_ascii(base_key))
        if nospace_key == nospace_incoming and nospace_incoming:
            for entry in entries:
                add(entry, "space")

    # ------------------------------------------------------------------
    # Step 5: Eastern format
    # Catches: "Shu, Xiaofan" ↔ "Shu Xiaofan" (last name = first word,
    # no comma). Tries treating incoming as "Firstname Lastname" and
    # converting to "Lastname, Firstname".
    # ------------------------------------------------------------------
    if "," not in name:
        words = name.split()
        if len(words) >= 2:
            eastern_base = f"{words[-1]}, {' '.join(words[:-1])}"
            norm_eastern = strip_to_ascii(eastern_base)
            for base_key, entries in index.items():
                if strip_to_ascii(base_key) == norm_eastern:
                    for entry in entries:
                        add(entry, "eastern")

    # ------------------------------------------------------------------
    # Step 6: Word order permutations
    # Catches: Xiao Fan Shu ↔ Shu Xiao Fan ↔ Fan Shu Xiao, etc.
    # Uses normalized sorted-word key.
    # ------------------------------------------------------------------
    wkey = word_key(name)
    for base_key, entries in index.items():
        if base_key == base:
            continue
        if word_key(base_key) == wkey and wkey:
            for entry in entries:
                add(entry, "wordorder")

    # ------------------------------------------------------------------
    # Steps 7–8: Soundex and edit distance fallbacks
    # Only applied when no match found via steps 1–6.
    # ------------------------------------------------------------------
    if not found:
        new_last, new_first = last, first
        for base_key, entries in index.items():
            ex_last, ex_first = name_parts(base_key)

            hit = False
            # Soundex on last name (same first)
            if new_first and ex_first and new_first.lower() == ex_first.lower():
                if soundex(new_last) == soundex(ex_last):
                    hit = True
            # Soundex on first name (same last)
            if not hit and new_last and ex_last and new_last.lower() == ex_last.lower():
                if new_first and ex_first and soundex(new_first) == soundex(ex_first):
                    hit = True
            # Edit distance <= 2 on last name (same first)
            if not hit and new_first and ex_first and new_first.lower() == ex_first.lower():
                if new_last and ex_last and levenshtein(new_last.lower(), ex_last.lower()) <= 2:
                    hit = True

            if hit:
                for entry in entries:
                    add(entry, "soundex")

    return list(found.values())


def is_auto_accept(candidates: list, incoming_year: int, max_gap: int) -> bool:
    """
    True only when there is exactly one candidate, it was found via exact match
    only, and the temporal gap is within the acceptable threshold.
    """
    if len(candidates) != 1:
        return False
    c = candidates[0]
    if c.match_types != ["exact"]:
        return False
    gap = _temporal_gap(c.entry, incoming_year)
    return gap <= max_gap


# ---------------------------------------------------------------------------
# Utility functions (I/O, display)
# ---------------------------------------------------------------------------

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


def format_candidate_summary(match: CandidateMatch, number: int, incoming_year: int, max_gap: int) -> str:
    entry = match.entry
    divs = "/".join(entry.divisions[:4])
    year_range = f"{entry.y0}" if entry.y0 == entry.y1 else f"{entry.y0}\u2013{entry.y1}"
    base = f"  {number}. {entry.full_name:<30} \u2014 {entry.count} contest{'s' if entry.count != 1 else ''}, {year_range}, {divs}"

    tags = []
    gap = _temporal_gap(entry, incoming_year)
    if gap > max_gap:
        tags.append(f"{YELLOW}\u26a0 {gap}yr gap{RESET}")
    non_exact = [t for t in match.match_types if t != "exact"]
    if non_exact:
        tags.append(f"({', '.join(non_exact)})")

    return base + ("  " + "  ".join(tags) if tags else "")


def show_detail(entry: AthleteEntry, master_lines: list) -> None:
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
            print(f"  {contest} {year} \u2014 not found in master.")
    print(f"  Incoming records: {incoming}")


def _prompt_and_complete(out_path: Path, out_lines: list, corrections: dict) -> bool:
    """Apply corrections, prompt Y/N, write corrected file to completed/. Returns True if written."""
    final = {k: v for k, v in corrections.items() if v is not None}
    corrected = apply_name_corrections(out_lines, final)
    if corrections:
        resolved = sum(1 for v in corrections.values() if v is not None)
        skipped  = sum(1 for v in corrections.values() if v is None)
        print(f"\n  Resolved: {resolved}  Skipped (kept as-is): {skipped}")
    print(f"\nWrite corrected file to completed/? (Y/N) ", end="", flush=True)
    while True:
        ch = getch().upper()
        if ch == "Y":
            print(ch)
            COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
            dest = COMPLETED_DIR / out_path.name
            dest.write_text("".join(corrected))
            out_path.unlink()
            print(f"  Written \u2192 5-completed/{out_path.name}\n")
            return True
        elif ch == "N":
            print(ch)
            print(f"  Skipped \u2014 {out_path.name} left in 4-reviewed/\n")
            return False
        elif ch == "\x03":
            print("\nAborted.")
            return False


# ---------------------------------------------------------------------------
# Main per-file processing
# ---------------------------------------------------------------------------

def process_file(out_path: Path, max_gap: int = 8) -> bool:
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
    incoming_year = get_incoming_year(out_lines)

    # Collect unique names from .out in order of first appearance
    unique_names = []
    seen_names: set = set()
    for line in out_lines:
        name = line.strip().split("; ", 1)[0]
        if name and name not in seen_names:
            seen_names.add(name)
            unique_names.append(name)

    # Build conflict list — names requiring user input
    conflicts = []
    for name in sorted(unique_names):
        candidates = find_all_candidates(name, index, incoming_year, max_gap)
        if not candidates:
            continue  # truly new athlete — no action needed
        if is_auto_accept(candidates, incoming_year, max_gap):
            continue  # single unambiguous exact match within gap — silent accept
        conflicts.append((name, candidates))

    if not conflicts:
        print(f"  No conflicts requiring review.")
        _prompt_and_complete(out_path, out_lines, {})
        return True

    print(f"  {len(conflicts)} conflict(s) to resolve.")

    # Build flat set of all master names for [n] assignment
    names = all_master_names(index)

    corrections = {}
    i = 0

    while i < len(conflicts):
        name, candidates = conflicts[i]

        example = ""
        for line in out_lines:
            if line.split("; ", 1)[0] == name:
                parts = line.strip().split("; ")
                if len(parts) >= 4:
                    example = f"{parts[2]}, {parts[1]}, {parts[3]}"
                break

        print(f"\n[{i+1}/{len(conflicts)}] {BOLD}{name}{RESET}  ({example})")
        if name in corrections:
            val = corrections[name]
            print(f"  (previous decision: {val if val else 'skip'})")

        for j, match in enumerate(candidates, 1):
            print(format_candidate_summary(match, j, incoming_year, max_gap))

        next_n = get_next_disambig(base_name_of(name), names)
        print(f"  N  New athlete \u2192 {next_n}")
        print(f"  D  Details (then enter number)")
        print(f"  S  Skip (keep name as-is)")
        if i > 0:
            print(f"  9  Back")
        print(f"  0  Done for now (prompt to write, move to next file)")
        print(f"  X  Exit all (prompt to write, stop)")
        print("Choice: ", end="", flush=True)

        while True:
            ch = getch().upper()

            if ch.isdigit() and ch not in ("0", "9"):
                idx_pick = int(ch) - 1
                if 0 <= idx_pick < len(candidates):
                    print(ch)
                    corrections[name] = candidates[idx_pick].entry.full_name
                    i += 1
                    break

            elif ch == "N":
                print(ch)
                corrections[name] = next_n
                i += 1
                break

            elif ch == "D":
                print(ch)
                print("  Which candidate? ", end="", flush=True)
                num_ch = getch()
                print(num_ch)
                idx_pick = int(num_ch) - 1 if num_ch.isdigit() else -1
                if 0 <= idx_pick < len(candidates):
                    show_detail(candidates[idx_pick].entry, master_lines)
                else:
                    print("  (invalid)")
                print("Choice: ", end="", flush=True)

            elif ch == "S":
                print(ch)
                corrections[name] = None
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
                _prompt_and_complete(out_path, out_lines, corrections)
                return True

            elif ch == "X":
                print(ch)
                _prompt_and_complete(out_path, out_lines, corrections)
                return False

            elif ch == "\x03":
                print("\nAborted.")
                return False

    _prompt_and_complete(out_path, out_lines, corrections)
    return True


def main():
    parser = argparse.ArgumentParser(description="Verify athlete names and write corrected .out to completed/")
    parser.add_argument("file", nargs="?", help="Specific .out file to process (with or without extension)")
    parser.add_argument("--max-gap", type=int, default=8,
                        help="Max acceptable year gap for auto-accepting exact matches (default: 8)")
    args = parser.parse_args()

    if args.file:
        name = args.file if args.file.endswith(".out") else args.file + ".out"
        out_path = FORMATTED_DIR / name
        if not out_path.exists():
            print(f"File not found: {out_path}")
            sys.exit(1)
        process_file(out_path, max_gap=args.max_gap)
    else:
        for f in sorted(FORMATTED_DIR.glob("*.out")):
            if not process_file(f, max_gap=args.max_gap):
                return


if __name__ == "__main__":
    main()
