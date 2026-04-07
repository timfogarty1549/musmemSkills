import csv
import re
import unicodedata
from collections import defaultdict

TSV_PATH = "/Users/timfogarty/workspace/musmem/working_data/raw_to_canonical.tsv"


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def clean_token(token: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]", "", token).lower()


def norm_tokens(name: str) -> list[str]:
    cleaned = strip_accents(name).replace("@", "").replace(",", " ")
    return [clean_token(tok) for tok in cleaned.split() if clean_token(tok)]


def style(name: str) -> str:
    if name.startswith("@"):
        return "east"
    if "," in name:
        return "west"
    return "plain"


def main() -> None:
    with open(TSV_PATH, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    canon_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        canon_counts[row["canonical"]] += 1

    by_key: dict[tuple[str, ...], list[tuple[str, list[str]]]] = defaultdict(list)
    for canonical in sorted(canon_counts):
        tokens = norm_tokens(canonical)
        if len(tokens) >= 2:
            by_key[tuple(sorted(tokens))].append((canonical, tokens))

    hits = []
    for key, values in by_key.items():
        if len(values) < 2:
            continue
        ordered = sorted(c for c, _ in values)
        total = sum(canon_counts[c] for c in ordered)
        hits.append((total, key, ordered))

    for total, key, values in sorted(hits, key=lambda x: (-x[0], x[1])):
        print(f"## total={total} key={' '.join(key)}")
        for value in values:
            print(f"{canon_counts[value]}\t{style(value)}\t{value}")
        print()


if __name__ == "__main__":
    main()
