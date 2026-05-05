#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path


DATA_ROOT = Path("~/workspace/musmem/data").expanduser()
DISTINCT_ROOT = Path("~/workspace/musmem/distinct").expanduser()


NICKNAMES = {
    "alex": {"alexander", "alexandro", "alejandro"},
    "andy": {"andrew", "andrei", "andrey"},
    "anthony": {"tony"},
    "ben": {"benjamin"},
    "bill": {"william", "billy"},
    "bob": {"robert", "bobby"},
    "chris": {"christopher", "christian", "cristian", "cristiano"},
    "dan": {"daniel", "danny"},
    "dave": {"david", "davi"},
    "ed": {"edward", "eduardo"},
    "frank": {"francis", "francesco", "francisco"},
    "fred": {"frederick", "frederico"},
    "gabe": {"gabriel"},
    "greg": {"gregory", "gregorio"},
    "jack": {"john"},
    "jim": {"james", "jimmy"},
    "joe": {"joseph", "joey"},
    "jon": {"jonathan", "john"},
    "josh": {"joshua"},
    "ken": {"kenneth", "kenny"},
    "leo": {"leonardo", "leonard"},
    "matt": {"matthew", "mathew"},
    "mike": {"michael", "mikey"},
    "nick": {"nicholas", "nicolas", "nikolai"},
    "pat": {"patrick"},
    "pete": {"peter"},
    "rob": {"robert", "roberto"},
    "sam": {"samuel"},
    "steve": {"steven", "stephen"},
    "ted": {"edward", "theodore"},
    "tim": {"timothy"},
    "tom": {"thomas", "tommy"},
    "vic": {"victor"},
    "vince": {"vincent", "vincenzo"},
    "zack": {"zachary", "zakari", "zakary"},
}

NICKNAME_EQUIV: dict[str, set[str]] = defaultdict(set)
for short, fulls in NICKNAMES.items():
    for full in fulls:
        NICKNAME_EQUIV[short].add(full)
        NICKNAME_EQUIV[full].add(short)
        for other in fulls:
            if other != full:
                NICKNAME_EQUIV[full].add(other)


@dataclass(frozen=True)
class Source:
    label: str
    path: Path
    min_year: int | None


@dataclass(frozen=True)
class NameRecord:
    original: str
    surname: str
    given: str
    surname_key: str
    given_key: str
    full_key: str
    given_tokens: tuple[str, ...]
    all_tokens: tuple[str, ...]


def prompt(text: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value or (default or "")


def prompt_int(text: str, default: int | None = None) -> int | None:
    default_text = "" if default is None else str(default)
    while True:
        value = prompt(text, default_text).strip()
        if value == "":
            return None
        try:
            return int(value)
        except ValueError:
            print("Please enter a year as digits, or leave blank.")


def safe_label(label: str) -> str:
    label = re.sub(r"[^A-Za-z0-9]+", "_", label.strip()).strip("_").lower()
    return label or "source"


def resolve_data_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return DATA_ROOT / path


def resolve_output_path(value: str) -> Path:
    return Path(value).expanduser()


def strip_accents(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


def clean_text(text: str) -> str:
    text = strip_accents(text).casefold()
    text = text.replace("'", "").replace("`", "").replace("´", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def compact_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", clean_text(text))


def parse_name(name: str) -> NameRecord:
    if "," in name:
        surname, given = name.split(",", 1)
    else:
        parts = name.split()
        surname = parts[-1] if parts else ""
        given = " ".join(parts[:-1])
    surname = surname.strip()
    given = given.strip()
    surname_key = clean_text(surname)
    given_key = clean_text(given)
    return NameRecord(
        original=name,
        surname=surname,
        given=given,
        surname_key=surname_key,
        given_key=given_key,
        full_key=clean_text(f"{surname} {given}"),
        given_tokens=tuple(given_key.split()),
        all_tokens=tuple(clean_text(name).split()),
    )


def damerau_levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev_prev: list[int] | None = None
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            value = min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
            if prev_prev is not None and i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                value = min(value, prev_prev[j - 2] + 1)
            cur.append(value)
        prev_prev, prev = prev, cur
    return prev[-1]


def close_spelling(a: str, b: str) -> bool:
    if a == b or not a or not b:
        return False
    if abs(len(a) - len(b)) > 2:
        return False
    limit = 1 if max(len(a), len(b)) <= 9 else 2
    return damerau_levenshtein(a, b) <= limit


def initials_match(shorter: tuple[str, ...], longer: tuple[str, ...]) -> bool:
    if not shorter or len(shorter) >= len(longer):
        return False
    if len(shorter) == 1 and len(longer) >= 2:
        return shorter[0] == longer[0]
    if len(shorter) + 1 != len(longer):
        return False
    return all(a == b or (len(a) == 1 and b.startswith(a)) for a, b in zip(shorter, longer))


def nickname_match(a_tokens: tuple[str, ...], b_tokens: tuple[str, ...]) -> bool:
    if len(a_tokens) != len(b_tokens) or not a_tokens:
        return False
    diffs = [(a, b) for a, b in zip(a_tokens, b_tokens) if a != b]
    if len(diffs) != 1:
        return False
    a, b = diffs[0]
    return b in NICKNAME_EQUIV.get(a, set()) or a in NICKNAME_EQUIV.get(b, set())


def add_pair(pairs: dict[tuple[str, str], set[str]], left: NameRecord, right: NameRecord, reason: str) -> None:
    if left.original == right.original:
        return
    key = tuple(sorted((left.original, right.original), key=str.casefold))
    pairs[key].add(reason)


def connected_groups(pairs: dict[tuple[str, str], set[str]]) -> list[list[str]]:
    edges: dict[str, set[str]] = defaultdict(set)
    for left, right in pairs:
        edges[left].add(right)
        edges[right].add(left)
    seen: set[str] = set()
    groups: list[list[str]] = []
    for name in sorted(edges, key=str.casefold):
        if name in seen:
            continue
        stack = [name]
        seen.add(name)
        group: list[str] = []
        while stack:
            current = stack.pop()
            group.append(current)
            for nxt in edges[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        if len(group) > 1:
            groups.append(sorted(group, key=str.casefold))
    return groups


def read_counts(source: Source) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for line in source.path.read_text(encoding="utf-8").splitlines():
        parts = [part.strip() for part in line.split(";")]
        if not parts or not parts[0]:
            continue
        if source.min_year is not None:
            if len(parts) < 2:
                continue
            try:
                year = int(parts[1])
            except ValueError:
                continue
            if year < source.min_year:
                continue
        counts[parts[0]] += 1
    return counts


def build_pairs(names: list[str]) -> dict[tuple[str, str], set[str]]:
    records = [parse_name(name) for name in names]
    by_full_compact: dict[str, list[NameRecord]] = defaultdict(list)
    by_surname: dict[str, list[NameRecord]] = defaultdict(list)
    by_given: dict[str, list[NameRecord]] = defaultdict(list)
    by_surname_initial: dict[tuple[str, str], list[NameRecord]] = defaultdict(list)
    by_sorted_tokens: dict[tuple[str, ...], list[NameRecord]] = defaultdict(list)
    by_three_token_combo: dict[tuple[str, ...], list[NameRecord]] = defaultdict(list)

    for record in records:
        by_full_compact[compact_key(record.original)].append(record)
        by_surname[record.surname_key].append(record)
        by_given[record.given_key].append(record)
        by_surname_initial[(record.surname_key[:1], record.given_key[:1])].append(record)
        token_key = tuple(sorted(record.all_tokens))
        if len(token_key) >= 2:
            by_sorted_tokens[token_key].append(record)
        if len(set(record.all_tokens)) >= 3:
            for combo in combinations(sorted(set(record.all_tokens)), 3):
                by_three_token_combo[combo].append(record)

    pairs: dict[tuple[str, str], set[str]] = defaultdict(set)

    for group in by_sorted_tokens.values():
        for i, left in enumerate(group):
            for right in group[i + 1 :]:
                add_pair(pairs, left, right, "same tokens in different order")

    partial_token_pairs: set[tuple[str, str]] = set()
    for bucket in by_three_token_combo.values():
        if len(bucket) < 2 or len(bucket) > 100:
            continue
        for i, left in enumerate(bucket):
            left_tokens = set(left.all_tokens)
            for right in bucket[i + 1 :]:
                right_tokens = set(right.all_tokens)
                if max(len(left_tokens), len(right_tokens)) < 4:
                    continue
                if min(len(left_tokens), len(right_tokens)) < 3:
                    continue
                shared = left_tokens & right_tokens
                if len(shared) < 3:
                    continue
                if not (left_tokens <= right_tokens or right_tokens <= left_tokens):
                    continue
                pair = tuple(sorted((left.original, right.original), key=str.casefold))
                if pair in partial_token_pairs:
                    continue
                partial_token_pairs.add(pair)
                add_pair(pairs, left, right, "three-plus shared tokens")

    for group in by_full_compact.values():
        for i, left in enumerate(group):
            for right in group[i + 1 :]:
                add_pair(pairs, left, right, "punctuation/spacing/accent only")

    for bucket in by_surname.values():
        bucket = sorted(bucket, key=lambda r: r.given_key)
        for i, left in enumerate(bucket):
            for right in bucket[i + 1 :]:
                if left.given_key == right.given_key:
                    continue
                if nickname_match(left.given_tokens, right.given_tokens):
                    add_pair(pairs, left, right, "same surname; common given-name variant")
                elif close_spelling(compact_key(left.given), compact_key(right.given)):
                    add_pair(pairs, left, right, "same surname; given-name typo/transposition")
                elif initials_match(left.given_tokens, right.given_tokens) or initials_match(right.given_tokens, left.given_tokens):
                    add_pair(pairs, left, right, "same surname; initial/expanded given-name")

    for bucket in by_given.values():
        for i, left in enumerate(bucket):
            for right in bucket[i + 1 :]:
                if left.surname_key == right.surname_key:
                    continue
                if close_spelling(compact_key(left.surname), compact_key(right.surname)):
                    add_pair(pairs, left, right, "same given name; surname typo/transposition")

    for bucket in by_surname_initial.values():
        if len(bucket) > 250:
            continue
        for i, left in enumerate(bucket):
            for right in bucket[i + 1 :]:
                if left.surname_key == right.surname_key or left.given_key == right.given_key:
                    continue
                if close_spelling(left.full_key, right.full_key):
                    add_pair(pairs, left, right, "full name typo candidate")

    return pairs


def collect_sources() -> list[Source]:
    while True:
        count_text = prompt("How many source files? Enter 1 or 2", "2")
        if count_text in {"1", "2"}:
            source_count = int(count_text)
            break
        print("Please enter 1 or 2.")

    sources: list[Source] = []
    for idx in range(1, source_count + 1):
        print(f"\nSource {idx}")
        while True:
            path = resolve_data_path(prompt("Input data file path"))
            if path.is_file():
                break
            print(f"File not found: {path}")
        label_default = safe_label(path.stem)
        label = safe_label(prompt("Label for output/count column", label_default))
        min_year = prompt_int("Minimum year from column 2, blank for none")
        sources.append(Source(label=label, path=path, min_year=min_year))
    return sources


def default_groups_out(sources: list[Source]) -> Path:
    if len(sources) == 1:
        return DISTINCT_ROOT / f"{sources[0].label}-variant-groups.tsv"
    return DISTINCT_ROOT / f"{sources[0].label}-{sources[1].label}-variant-groups.tsv"


def write_outputs(sources: list[Source], counts_by_label: dict[str, dict[str, int]], groups_out: Path) -> None:
    all_names = sorted({name for counts in counts_by_label.values() for name in counts}, key=str.casefold)
    pairs = build_pairs(all_names)
    groups = connected_groups(pairs)

    if len(sources) > 1:
        groups = [
            group
            for group in groups
            if sum(any(counts_by_label[source.label].get(name, 0) for name in group) for source in sources) >= 2
        ]

    groups_out.parent.mkdir(parents=True, exist_ok=True)
    with groups_out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["group_id", "name", *[f"count_{source.label}" for source in sources]])
        for idx, group in enumerate(groups, 1):
            for name in group:
                writer.writerow([idx, name, *[counts_by_label[source.label].get(name, 0) for source in sources]])

    print(f"Wrote {len(groups)} candidate groups to {groups_out}")


def main() -> int:
    sources = collect_sources()
    counts_by_label: dict[str, dict[str, int]] = {}

    for source in sources:
        counts = read_counts(source)
        counts_by_label[source.label] = counts
        year_text = f" with year >= {source.min_year}" if source.min_year is not None else ""
        print(f"Read {sum(counts.values())} rows{year_text} from {source.path}")
        print(f"Found {len(counts)} distinct names")

    groups_out = resolve_output_path(prompt("Candidate group TSV output path", str(default_groups_out(sources))))
    write_outputs(sources, counts_by_label, groups_out)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nAborted.")
        raise SystemExit(130)
