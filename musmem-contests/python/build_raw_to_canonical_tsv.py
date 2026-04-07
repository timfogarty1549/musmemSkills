#!/usr/bin/env python3
"""
build_tsv_v3.py — Build raw→canonical TSV from 2-normalize-athletes.

Strategy:
  For every normalized name in 2-normalize-athletes, find the best-matching
  raw name in the corresponding 1-incoming file (same division + place, highest
  token similarity).  Non-normalized names are skipped entirely.

Output columns: raw, canonical, note
  - Matched pair:  raw_name  canonical_name  (note empty)
  - No match:      ___TBD___  canonical_name  filename

Rows are sorted and deduplicated on (raw, canonical) at the end.
"""
from __future__ import annotations

import csv
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

INCOMING_DIR   = Path("/Users/timfogarty/workspace/musmem/1-incoming")
NORMALIZED_DIR = Path("/Users/timfogarty/workspace/musmem/2-normalize-athletes")
OUTPUT_TSV     = Path("/Users/timfogarty/workspace/musmem/working_data/raw_to_canonical.tsv")
ISSUES_TSV     = Path("/Users/timfogarty/workspace/musmem/working_data/raw_to_canonical_issues.tsv")

TBD = "___TBD___"

# Similarity threshold for matching.
# Unique candidate (only one name at this div+place in incoming): lower bar —
# the div+place constraint already narrows the search strongly.
# Multiple candidates: higher bar to avoid wrong picks.
UNIQUE_SIM_MIN = 0.3
MULTI_SIM_MIN  = 0.5

DIVISION_RE  = re.compile(r"^c\s+(\S+)\s*$")
NORMAL_ENTRY = re.compile(r"^(\d+)\s+(.*\S)\s*$")
EAST_ENTRY   = re.compile(r"^@(\d+)\s+(.*\S)\s*$")


@dataclass
class Row:
    division: str
    place: str
    name: str        # as it appears in the file
    east_asian: bool # True if the line started with @


def parse_file(path: Path) -> list[Row]:
    rows: list[Row] = []
    div = ""
    for line in path.read_text(errors="ignore").splitlines():
        dm = DIVISION_RE.match(line)
        if dm:
            div = dm.group(1)
            continue
        em = EAST_ENTRY.match(line)
        if em:
            rows.append(Row(div, em.group(1), em.group(2), True))
            continue
        nm = NORMAL_ENTRY.match(line)
        if nm:
            rows.append(Row(div, nm.group(1), nm.group(2), False))
    return rows


def is_normalized(row: Row) -> bool:
    """A name is normalized if it's East Asian (@) or Last, First (comma)."""
    if row.east_asian:
        return True
    return "," in row.name


def canonical_name(row: Row) -> str:
    """Canonical form as it should appear in col2 of the TSV."""
    if row.east_asian:
        return "@" + row.name
    return row.name


# ---------------------------------------------------------------------------
# Similarity (token-only, no char fallback — char fallback causes false pairs)
# ---------------------------------------------------------------------------

def normalize_token(t: str) -> str:
    t = unicodedata.normalize("NFKD", t)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", t.lower())


def name_tokens(name: str) -> list[str]:
    """
    Split on whitespace and hyphens, normalize, then expand short all-alpha
    tokens (≤3 chars) into individual characters to handle merged initials
    like 'IB' → ['i','b'], 'TJ' → ['t','j'].
    """
    clean = name.lstrip("@").replace(",", " ")
    expanded: list[str] = []
    for t in re.split(r"[\s\-]+", clean):
        nt = normalize_token(t)
        if not nt:
            continue
        if len(nt) <= 3 and nt.isalpha():
            expanded.extend(list(nt))
        else:
            expanded.append(nt)
    return expanded


def token_similarity(a: str, b: str) -> float:
    ta = Counter(name_tokens(a))
    tb = Counter(name_tokens(b))
    if not ta or not tb:
        return 0.0
    intersection = sum((ta & tb).values())
    union = sum((ta | tb).values())
    return intersection / union


# ---------------------------------------------------------------------------
# Core matching: for each normalized row in norm_file, find best raw in inc_file
# ---------------------------------------------------------------------------

# Divisions treated as interchangeable for matching purposes.
DIV_ALIAS: dict[str, str] = {"BB": "OP"}   # both collapse to "OP"


def index_key(division: str) -> str:
    """Normalise division to a canonical key so aliases share the same bucket."""
    return DIV_ALIAS.get(division, division)


def build_index(rows: list[Row]) -> dict[tuple[str, str], list[Row]]:
    idx: dict[tuple[str, str], list[Row]] = defaultdict(list)
    for r in rows:
        idx[(index_key(r.division), r.place)].append(r)
    return idx


def find_raw(norm_row: Row, inc_index: dict[tuple[str, str], list[Row]]) -> Row | None:
    """
    Find the best-matching raw row for a normalized row.
    Looks in the same (division, place) bucket, picks by token similarity.
    Returns None if no candidate meets the threshold.
    """
    key = (index_key(norm_row.division), norm_row.place)
    candidates = inc_index.get(key, [])

    if not candidates:
        return None

    can_name = canonical_name(norm_row)
    threshold = UNIQUE_SIM_MIN if len(candidates) == 1 else MULTI_SIM_MIN

    best_sim, best_row = 0.0, None
    for cand in candidates:
        sim = token_similarity(cand.name, can_name)
        if sim > best_sim:
            best_sim, best_row = sim, cand

    return best_row if best_sim >= threshold else None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

Triplet = tuple[str, str, str]   # (raw, canonical, note)


def build() -> tuple[list[Triplet], list[str]]:
    triplets: list[Triplet] = []
    issues: list[str] = []
    stats: Counter = Counter()

    for norm_path in sorted(NORMALIZED_DIR.glob("*.txt")):
        inc_path = INCOMING_DIR / norm_path.name
        if not inc_path.exists():
            print(f"ALERT: no matching incoming file for {norm_path.name}", file=sys.stderr)
            stats["missing_incoming"] += 1
            continue

        stats["files"] += 1
        norm_rows = parse_file(norm_path)
        inc_rows  = parse_file(inc_path)
        inc_index = build_index(inc_rows)

        for nr in norm_rows:
            if not is_normalized(nr):
                continue

            stats["normalized_names"] += 1
            canon = canonical_name(nr)
            raw_row = find_raw(nr, inc_index)

            if raw_row is not None:
                triplets.append((raw_row.name, canon, ""))
                stats["matched"] += 1
            else:
                triplets.append((TBD, canon, norm_path.name))
                stats["tbd"] += 1

    return triplets, issues, stats


def write_tsv(path: Path, triplets: list[Triplet]) -> int:
    # Dedup on (raw, canonical) — keep first occurrence when sorted
    seen: set[tuple[str, str]] = set()
    unique: list[Triplet] = []
    for t in sorted(triplets):
        key = (t[0], t[1])
        if key not in seen:
            seen.add(key)
            unique.append(t)

    with path.open("w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["raw", "canonical", "note"])
        w.writerows(unique)

    return len(unique)


def main() -> None:
    triplets, issues, stats = build()
    n = write_tsv(OUTPUT_TSV, triplets)

    tbd_rows = [t for t in triplets if t[0] == TBD]
    # Dedup TBD on canonical for reporting
    tbd_unique_can = sorted({t[1] for t in tbd_rows})

    print(f"files_compared:    {stats['files']}")
    print(f"missing_incoming:  {stats['missing_incoming']}")
    print(f"normalized_names:  {stats['normalized_names']}")
    print(f"matched:           {stats['matched']}")
    print(f"tbd:               {stats['tbd']}")
    print(f"unique_rows_tsv:   {n}")

    at_count     = sum(1 for t in triplets if t[0] != TBD and t[1].startswith("@"))
    comma_count  = sum(1 for t in triplets if t[0] != TBD and "," in t[1])
    print(f"  east_asian (@):  {at_count}")
    print(f"  last_first (,):  {comma_count}")

    if tbd_unique_can:
        print(f"\nTBD names ({len(tbd_unique_can)} unique canonicals):")
        for name in tbd_unique_can[:30]:
            # find a file that reported this TBD
            file_ = next(t[2] for t in tbd_rows if t[1] == name)
            print(f"  {name!r:45s}  [{file_}]")
        if len(tbd_unique_can) > 30:
            print(f"  ... and {len(tbd_unique_can) - 30} more")


if __name__ == "__main__":
    main()
