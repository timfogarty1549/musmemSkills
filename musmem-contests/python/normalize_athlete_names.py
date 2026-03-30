#!/usr/bin/env python3
"""
Normalize athlete names in MusMem contest flat files.

Rules:
- preserve all non-athlete lines and original order
- western-style names -> "n Last, First"
- East Asian names -> "@n Family Given"
- preserve already-normalized "n Last, First" and "@n Family Given" lines
- write sibling "-1" copies by default

Examples:
    python3 normalize_athlete_names.py ~/workspace/musmem/1-incoming/*10x*.txt
    python3 normalize_athlete_names.py --in-place ~/workspace/musmem/1-incoming/2024_amateur_olympia_korea-npc_worldwide-male.txt
    python3 normalize_athlete_names.py --src-root ~/workspace/musmem/1-incoming --dst-root ~/workspace/musmem/2-normalize-athletes ~/workspace/musmem/1-incoming/*.txt
"""

from __future__ import annotations

import argparse
import glob
import re
from pathlib import Path


ATHLETE_RE = re.compile(r"^(\d+)\s+(.+)$")
AT_EAST_ASIAN_RE = re.compile(r"^@(\d+)\s+(.+)$")
ALREADY_WESTERN_RE = re.compile(r"^(\d+)\s+[^,]+,\s+.+$")

SURNAME_PARTICLES = {
    "al", "bin", "bint", "da", "de", "del", "della", "der", "di", "do",
    "dos", "du", "el", "la", "le", "o", "van", "von", "vander",
}

EAST_ASIAN_SURNAMES = {
    "ahn", "an", "bae", "bai", "bang", "byun", "cha", "chan", "chang",
    "chen", "cheng", "chiou", "cho", "choi", "chua", "chung", "eom", "fu",
    "gao", "gim", "han", "ham", "heo", "ho", "hong", "huh", "hur", "hwang",
    "jeon", "jeong", "ji", "jin", "jung", "kang", "kim", "kook", "kwon",
    "lee", "leung", "li", "lin", "liu", "moon", "mou", "ng", "oh", "park",
    "seo", "seon", "shi", "shim", "shin", "song", "son", "su", "suo", "tan",
    "wang", "wen", "woo", "wu", "xie", "yang", "yeon", "yoon", "you", "yu",
    "yuan", "yun", "zhang", "zheng", "zhou", "zhu",
}

WESTERN_GIVEN_BLOCK = {
    "adrian", "cameron", "daniel", "danny", "david", "eric", "greg",
    "james", "jordan", "louis", "matthew", "nicholas", "paola", "philip",
    "victor",
}


def token_norm(token: str) -> str:
    return re.sub(r"[^A-Za-z]", "", token).lower()


def is_athlete_line(line: str) -> re.Match[str] | None:
    return ATHLETE_RE.match(line)


def is_already_normalized(line: str) -> bool:
    return bool(AT_EAST_ASIAN_RE.match(line) or ALREADY_WESTERN_RE.match(line))


def western_format(name: str) -> str:
    tokens = name.split()
    if len(tokens) <= 1:
        return name
    if len(tokens) == 2:
        return f"{tokens[1]}, {tokens[0]}"

    surname_start = len(tokens) - 1
    while surname_start - 1 >= 1 and token_norm(tokens[surname_start - 1]) in SURNAME_PARTICLES:
        surname_start -= 1

    if surname_start == len(tokens) - 1 and len(tokens) >= 3:
        prev = token_norm(tokens[-2])
        last = token_norm(tokens[-1])
        if last.startswith("van") or prev in {"van", "de", "du", "dos", "del", "da"}:
            surname_start = len(tokens) - 2

    surname = " ".join(tokens[surname_start:])
    given = " ".join(tokens[:surname_start])
    return f"{surname}, {given}"


def east_asian_format(name: str, file_name: str) -> str | None:
    tokens = name.split()
    if len(tokens) < 2:
        return None

    first = token_norm(tokens[0])
    last = token_norm(tokens[-1])

    # Korea-specific files are strong candidates for East Asian normalization,
    # but still avoid blindly converting clearly western-leading names.
    if "korea" in file_name.lower():
        if first in WESTERN_GIVEN_BLOCK:
            return None
        if first in EAST_ASIAN_SURNAMES:
            return name
        if last in EAST_ASIAN_SURNAMES:
            return f"{tokens[-1]} {' '.join(tokens[:-1])}"

    # Outside Korea files, only convert when the pattern is especially strong.
    if last in EAST_ASIAN_SURNAMES and first not in WESTERN_GIVEN_BLOCK and len(tokens) <= 3:
        return f"{tokens[-1]} {' '.join(tokens[:-1])}"

    return None


def normalize_line(line: str, file_name: str) -> str:
    if is_already_normalized(line):
        return line

    match = is_athlete_line(line)
    if not match:
        return line

    rank, name = match.groups()
    east = east_asian_format(name, file_name)
    if east:
        return f"@{rank} {east}"
    return f"{rank} {western_format(name)}"


def choose_output_path(
    path: Path,
    *,
    in_place: bool,
    src_root: Path | None,
    dst_root: Path | None,
) -> Path:
    if in_place:
        return path
    if src_root is not None and dst_root is not None:
        rel = path.relative_to(src_root)
        return dst_root / rel
    return path.with_name(path.name + "-1")


def normalize_file(
    path: Path,
    *,
    in_place: bool,
    src_root: Path | None,
    dst_root: Path | None,
) -> Path:
    lines = path.read_text(errors="replace").splitlines()
    out_lines = [normalize_line(line, path.name) for line in lines]
    out_path = choose_output_path(path, in_place=in_place, src_root=src_root, dst_root=dst_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out_lines) + "\n")
    return out_path


def expand_inputs(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matches = sorted(Path(p) for p in glob.glob(str(Path(pattern).expanduser())))
        if matches:
            paths.extend(matches)
        else:
            candidate = Path(pattern).expanduser()
            if candidate.exists():
                paths.append(candidate)
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        if path not in seen and path.is_file():
            seen.add(path)
            unique.append(path)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Input files or glob patterns")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Rewrite the source file instead of writing a sibling -1 copy",
    )
    parser.add_argument(
        "--src-root",
        type=Path,
        help="Source root used to preserve relative paths when writing to --dst-root",
    )
    parser.add_argument(
        "--dst-root",
        type=Path,
        help="Write normalized files under this root instead of creating sibling -1 copies",
    )
    args = parser.parse_args()

    files = expand_inputs(args.paths)
    if not files:
        parser.error("no input files matched")

    src_root = args.src_root.expanduser().resolve() if args.src_root else None
    dst_root = args.dst_root.expanduser().resolve() if args.dst_root else None
    if dst_root is not None and src_root is None:
        parser.error("--dst-root requires --src-root")

    for path in files:
        out_path = normalize_file(
            path,
            in_place=args.in_place,
            src_root=src_root,
            dst_root=dst_root,
        )
        print(out_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
