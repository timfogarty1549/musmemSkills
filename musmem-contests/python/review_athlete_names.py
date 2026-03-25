#!/usr/bin/env python3
"""
review_athlete_names.py — Compare names in review-athlete-names.dat against bb_male.dat
(or bb_female.dat with --female).

Input:  ~/workspace/musmem/working_data/review-athlete-names.dat
        Two columns separated by ':'. The second column is the name to check.

Output: Lines where the name has a variation (non-exact match) in the master.
        Exact matches and not-found names produce no output.

Usage:
    python3 review_athlete_names.py             # compare against bb_male.dat
    python3 review_athlete_names.py --female    # compare against bb_female.dat
"""

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


def _load_paths():
    config = Path(__file__).parents[2] / "config/paths.json"
    data = json.loads(config.read_text())
    return {k: Path(v).expanduser() for k, v in data.items()}


_PATHS = _load_paths()

INPUT_FILE = Path("~/workspace/musmem/working_data/review-athlete-names.dat").expanduser()

CYAN   = "\033[96m"
YELLOW = "\033[93m"
RESET  = "\033[0m"


# ---------------------------------------------------------------------------
# Special character code mapping
# ---------------------------------------------------------------------------

_SPECIAL_CODES: dict = {
    "a''": "a'",
    "O''": "Ó", "o''": "ó",
    "D---": "Đ", "d---": "đ",
    "C--": "Ç", "c--": "ç",
    "D--": "Ð", "d--": "ð",
    "S--": "Ş", "s--": "ş",
    "A:": "Ä",  "a:": "ä",
    "A`": "À",  "a`": "à",
    "A'": "Á",  "a'": "á",
    "A^": "Â",  "a^": "â",
    "a~": "ã",
    "A@": "Å",  "a@": "å",
    "A*": "Ă",  "a*": "ă",
    "a_": "ā",  "A_": "Ā",
    "C^": "Č",  "c^": "č",
    "C'": "Ć",  "c'": "ć",
    "E:": "Ë",  "e:": "ë",
    "E`": "È",  "e`": "è",
    "E'": "É",  "e'": "é",
    "e^": "ě",
    "E.": "Ė",  "e.": "ė",
    "e_": "ē",  "E_": "Ē",
    "g^": "ģ",
    "I`": "Ì",  "i`": "ì",
    "I'": "Í",  "i'": "í",
    "I.": "İ",
    "i_": "ī",  "I_": "Ī",
    "L/": "Ł",  "l/": "ł",
    "N~": "Ñ",  "n~": "ñ",
    "n'": "Ņ",
    "N^": "Ň",  "n^": "ň",
    "O`": "Ò",  "o`": "ò",
    "o^": "ô",
    "O~": "Õ",  "o~": "õ",
    "O:": "Ö",  "o:": "ö",
    "O/": "Ø",  "o/": "ø",
    "r^": "ř",
    "S'": "Ś",  "s'": "ś",
    "S^": "Š",  "s^": "š",
    "s*": "ß",
    "U^": "Û",  "u^": "û",
    "U:": "Ü",  "u:": "ü",
    "u@": "ů",
    "U_": "Ū",  "u_": "ū",
    "U'": "Ú",  "u'": "ú",
    "y:": "ÿ",  "Y:": "Ÿ",
    "Y'": "Ý",  "y'": "ý",
    "Z^": "Ž",  "z^": "ž",
}

_SPECIAL_CODE_RE = re.compile(
    "|".join(re.escape(k) for k in sorted(_SPECIAL_CODES, key=len, reverse=True))
)


def expand_special_codes(s: str) -> str:
    return _SPECIAL_CODE_RE.sub(lambda m: _SPECIAL_CODES[m.group(0)], s)


def strip_to_ascii(s: str) -> str:
    s = expand_special_codes(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


# ---------------------------------------------------------------------------
# Name utilities
# ---------------------------------------------------------------------------

def strip_disambig(name: str) -> str:
    return re.sub(r"\s*\[\d+\]$", "", name).strip()


def base_name_of(name: str) -> str:
    return strip_disambig(name)


def strip_generational_suffix(first: str) -> str:
    return re.sub(r"\s+(Jr\.?|Sr\.?|II|III|IV)\s*$", "", first, flags=re.IGNORECASE).strip()


def name_parts(name: str):
    base = base_name_of(name)
    if ", " in base:
        last, first = base.split(", ", 1)
        return last.strip(), first.strip()
    return base.strip(), ""


def word_key(name: str) -> str:
    s = strip_to_ascii(base_name_of(name))
    words = re.sub(r"[^a-z ]", "", s).split()
    return "".join(sorted(words))


def soundex(name: str) -> str:
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


def last_names_word_close(last1: str, last2: str, min_len: int = 3, max_dist: int = 2) -> bool:
    """Return True if any word pair (one from each last name, both len >= min_len)
    has Levenshtein distance <= max_dist."""
    words1 = [w for w in re.sub(r"[^a-z ]", "", strip_to_ascii(last1)).split() if len(w) >= min_len]
    words2 = [w for w in re.sub(r"[^a-z ]", "", strip_to_ascii(last2)).split() if len(w) >= min_len]
    for w1 in words1:
        for w2 in words2:
            if levenshtein(w1, w2) <= max_dist:
                return True
    return False


# ---------------------------------------------------------------------------
# Master index
# ---------------------------------------------------------------------------

@dataclass
class AthleteEntry:
    full_name: str
    count: int = 0
    y0: int = 9999
    y1: int = 0
    divisions: list = field(default_factory=list)


@dataclass
class MasterIndex:
    # base_name -> list[AthleteEntry]
    by_base: dict

    # Precomputed lookup tables for fast matching
    by_ascii_norm: dict      # ascii-normalized base -> list[str base_name]  (step 2)
    by_nospace:    dict      # no-space ascii -> list[str base_name]          (step 4)
    by_word_key:   dict      # sorted-word key -> list[str base_name]         (step 5/6)
    by_last_ascii: dict      # ascii last name -> list[str base_name]         (step 3 filter)
    by_soundex_last: dict    # (first_lower, soundex_last) -> list[str base_name]
    by_soundex_first: dict   # (last_lower, soundex_first) -> list[str base_name]


def build_master_index(lines: list, since_year: int = 0) -> MasterIndex:
    entries: dict = {}  # full_name -> AthleteEntry

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
        if since_year and year < since_year:
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

    # Group by base name
    by_base: dict = {}
    for full_name, entry in entries.items():
        base = base_name_of(full_name)
        if base not in by_base:
            by_base[base] = []
        by_base[base].append(entry)

    # Precompute lookup tables
    by_ascii_norm:    dict = defaultdict(list)
    by_nospace:       dict = defaultdict(list)
    by_word_key:      dict = defaultdict(list)
    by_last_ascii:    dict = defaultdict(list)
    by_soundex_last:  dict = defaultdict(list)
    by_soundex_first: dict = defaultdict(list)

    for base in by_base:
        norm = strip_to_ascii(base)
        by_ascii_norm[norm].append(base)

        nospace = re.sub(r"[^a-z]", "", norm)
        if nospace:
            by_nospace[nospace].append(base)

        wk = word_key(base)
        if wk:
            by_word_key[wk].append(base)

        last_a, first_a = name_parts(base)
        last_ascii = strip_to_ascii(last_a)
        if last_ascii:
            by_last_ascii[last_ascii].append(base)

        # Soundex tables
        if last_a and first_a:
            sdx_last  = soundex(last_a)
            sdx_first = soundex(first_a)
            by_soundex_last[(first_a.lower(), sdx_last)].append(base)
            by_soundex_first[(last_a.lower(), sdx_first)].append(base)

    return MasterIndex(
        by_base=by_base,
        by_ascii_norm=dict(by_ascii_norm),
        by_nospace=dict(by_nospace),
        by_word_key=dict(by_word_key),
        by_last_ascii=dict(by_last_ascii),
        by_soundex_last=dict(by_soundex_last),
        by_soundex_first=dict(by_soundex_first),
    )


# ---------------------------------------------------------------------------
# Candidate matching
# ---------------------------------------------------------------------------

@dataclass
class CandidateMatch:
    entry: AthleteEntry
    match_types: list


def find_all_candidates(name: str, idx: MasterIndex) -> list:
    found: dict = {}  # full_name -> CandidateMatch

    def add_base(base_key: str, strategy: str):
        for entry in idx.by_base.get(base_key, []):
            if entry.full_name in found:
                if strategy not in found[entry.full_name].match_types:
                    found[entry.full_name].match_types.append(strategy)
            else:
                found[entry.full_name] = CandidateMatch(entry=entry, match_types=[strategy])

    base = base_name_of(name)
    last, first = name_parts(name)
    first_no_gen = strip_generational_suffix(first)

    # Step 1: Exact base-name match (including [n] variants, generational suffixes)
    add_base(base, "exact")

    if first_no_gen != first:
        no_gen_base = f"{last}, {first_no_gen}" if first_no_gen else last
        add_base(no_gen_base, "exact")
    else:
        for suffix in ("Jr", "Sr", "II", "III", "IV"):
            with_gen = f"{last}, {first} {suffix}" if first else f"{last}, {suffix}"
            add_base(with_gen, "exact")

    # Step 2: Diacritic normalization — O(1) via precomputed table
    norm_incoming = strip_to_ascii(name)
    for candidate_base in idx.by_ascii_norm.get(norm_incoming, []):
        if candidate_base != base:
            add_base(candidate_base, "diacritic")

    # Step 3: Name part subset/superset — O(same-last-name only)
    incoming_words = set(re.sub(r"[^a-z ]", "", norm_incoming.replace(",", "")).split())
    last_ascii = strip_to_ascii(last)
    for candidate_base in idx.by_last_ascii.get(last_ascii, []):
        if candidate_base == base:
            continue
        norm_key = strip_to_ascii(candidate_base)
        master_words = set(re.sub(r"[^a-z ]", "", norm_key.replace(",", "")).split())
        if incoming_words == master_words:
            continue
        if len(incoming_words & master_words) < 2:
            continue
        if incoming_words.issubset(master_words) or master_words.issubset(incoming_words):
            add_base(candidate_base, "subset")

    # Step 4: Space normalization — O(1) via precomputed table
    nospace_incoming = re.sub(r"[^a-z]", "", norm_incoming)
    if nospace_incoming:
        for candidate_base in idx.by_nospace.get(nospace_incoming, []):
            if candidate_base != base:
                add_base(candidate_base, "space")

    # Step 5: Eastern format (no comma in incoming)
    if "," not in name:
        words = name.split()
        if len(words) >= 2:
            eastern_base = f"{words[-1]}, {' '.join(words[:-1])}"
            norm_eastern = strip_to_ascii(eastern_base)
            for candidate_base in idx.by_ascii_norm.get(norm_eastern, []):
                add_base(candidate_base, "eastern")

    # Step 6: Word order permutations — O(1) via precomputed table
    wk = word_key(name)
    if wk:
        for candidate_base in idx.by_word_key.get(wk, []):
            if candidate_base != base:
                add_base(candidate_base, "wordorder")

    # Steps 7–8: Soundex and edit distance (only when nothing found above)
    if not found:
        # Soundex on last name (same first)
        if first and last:
            sdx_last = soundex(last)
            for candidate_base in idx.by_soundex_last.get((first.lower(), sdx_last), []):
                if candidate_base != base:
                    ex_last, _ = name_parts(candidate_base)
                    if last_names_word_close(last, ex_last):
                        add_base(candidate_base, "soundex")

        # Soundex on first name (same last)
        if first and last:
            sdx_first = soundex(first)
            for candidate_base in idx.by_soundex_first.get((last.lower(), sdx_first), []):
                if candidate_base != base:
                    ex_last, _ = name_parts(candidate_base)
                    if last_names_word_close(last, ex_last):
                        add_base(candidate_base, "soundex")

        # Edit distance <= 2 on last name (same first) — still O(same-first candidates)
        if first and last:
            for candidate_base in idx.by_soundex_last.get((first.lower(), soundex(last)), []):
                pass  # already handled above via soundex
            # Full edit-distance pass against same-first-name entries only
            # (use last-ascii index to limit scope)
            for candidate_base in list(idx.by_base.keys()):
                ex_last, ex_first = name_parts(candidate_base)
                if ex_first and ex_first.lower() == first.lower():
                    if ex_last and levenshtein(last.lower(), ex_last.lower()) <= 2:
                        if candidate_base != base:
                            if last_names_word_close(last, ex_last):
                                add_base(candidate_base, "soundex")

    return list(found.values())


def is_exact_only(candidates: list) -> bool:
    return all(c.match_types == ["exact"] for c in candidates)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def format_entry(entry: AthleteEntry) -> str:
    yr = f"{entry.y0}–{entry.y1}" if entry.y0 != entry.y1 else str(entry.y0)
    divs = "/".join(entry.divisions[:4])
    return f"{entry.full_name}  ({entry.count} contests, {yr}, {divs})"


def main():
    parser = argparse.ArgumentParser(description="Check athlete names against master dat file.")
    parser.add_argument("--female", action="store_true", help="Compare against bb_female.dat instead of bb_male.dat")
    parser.add_argument("--since", type=int, default=2010, metavar="YEAR", help="Ignore master records before this year (default: 2010)")
    args = parser.parse_args()

    master_file = _PATHS["master_female"] if args.female else _PATHS["master_male"]
    gender_label = "female" if args.female else "male"

    if not INPUT_FILE.exists():
        print(f"Input file not found: {INPUT_FILE}", file=sys.stderr)
        sys.exit(1)

    master_lines = master_file.read_text(encoding="utf-8", errors="replace").splitlines()
    idx = build_master_index(master_lines, since_year=args.since)
    print(f"Loaded {sum(len(v) for v in idx.by_base.values())} {gender_label} athletes from master (since {args.since}).", file=sys.stderr)

    input_lines = INPUT_FILE.read_text(encoding="utf-8", errors="replace").splitlines()

    variation_count = 0

    for lineno, raw in enumerate(input_lines, 1):
        raw = raw.strip()
        if not raw:
            continue
        if ":" not in raw:
            print(f"Line {lineno}: malformed (no colon): {raw!r}", file=sys.stderr)
            continue

        col1, col2 = raw.split(":", 1)
        name = col2.strip()
        if not name:
            continue

        candidates = find_all_candidates(name, idx)

        if not candidates:
            pass  # not found — no output
        elif is_exact_only(candidates):
            pass  # exact match — no output
        else:
            variation_count += 1
            exact_cands = [c for c in candidates if c.match_types == ["exact"]]
            var_cands   = [c for c in candidates if c.match_types != ["exact"]]

            print(f"{CYAN}VARIATION{RESET}  {name}")
            for c in exact_cands:
                print(f"          exact   : {format_entry(c.entry)}")
            for c in var_cands:
                tags = "+".join(c.match_types)
                print(f"          {tags:<8}: {format_entry(c.entry)}")

    print(file=sys.stderr)
    print(f"Done. {variation_count} variations found.", file=sys.stderr)


if __name__ == "__main__":
    main()
