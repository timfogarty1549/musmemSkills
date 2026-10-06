#!/usr/bin/env python3
"""Extract IronMan table-of-contents TSVs from OCR-backed PDFs."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber


MAGAZINE_TITLE = "IronMan"
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
LOWERCASE_TITLE_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "but",
    "by",
    "for",
    "from",
    "in",
    "into",
    "nor",
    "of",
    "on",
    "onto",
    "or",
    "over",
    "per",
    "the",
    "to",
    "up",
    "via",
    "with",
    "within",
}
AUTHOR_SUFFIXES_AND_CREDENTIALS = {
    "jr",
    "sr",
    "ii",
    "iii",
    "iv",
    "phd",
    "md",
    "rpt",
    "ba",
    "ma",
    "dc",
    "do",
}
AUTHOR_TOKEN_CASING = {
    "phd": "PhD",
}
@dataclass
class TocRecord:
    title: str
    authors: str
    page: int


@dataclass
class IssueMetadata:
    year: int
    month: int
    volume: int
    issue: int


def title_case(text: str) -> str:
    text = normalize_text(text)
    words = re.split(r"(\s+)", text.lower())
    cased_words = []
    word_index = 0
    word_count = len([w for w in words if not w.isspace() and w])

    for word in words:
        if not word or word.isspace():
            cased_words.append(word)
            continue

        is_first = word_index == 0
        is_last = word_index == word_count - 1
        prev = "".join(cased_words).rstrip()
        force_cap = is_first or is_last or prev.endswith(("-", ":", "?", "!"))
        cased_words.append(title_case_word(word, force_cap))
        word_index += 1

    return "".join(cased_words)


def title_case_word(word: str, force_cap: bool) -> str:
    if re.fullmatch(r"\d+[a-z]{0,2}", word):
        return word.upper()
    if word.upper() in {"AAU", "IFBB", "NPC", "USA", "YMCA"}:
        return word.upper()
    if not force_cap and word in LOWERCASE_TITLE_WORDS:
        return word

    parts = re.split(r"([-/\"])", word)
    out = []
    for part in parts:
        if part in {"-", "/", "'", '"'} or not part:
            out.append(part)
        elif part in LOWERCASE_TITLE_WORDS and out and not force_cap:
            out.append(part)
        else:
            out.append(part[:1].upper() + part[1:])
    return "".join(out)


def normalize_text(text: str) -> str:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": " - ",
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_title(raw_title: str) -> str:
    title = normalize_text(raw_title)
    title = re.sub(r"[.,;:·\s]+$", "", title)
    title = re.sub(r"\.{2,}", "", title)
    title = fix_common_ocr_title_spacing(title)
    return title_case(title)


def fix_common_ocr_title_spacing(title: str) -> str:
    fixes = {
        r"\bHE\s+L\s+P\s+F\s+O\s+R\s+T\s+H\s+E\s+O\s+L\s+DER\b": "HELP FOR THE OLDER",
    }
    for pattern, replacement in fixes.items():
        title = re.sub(pattern, replacement, title, flags=re.IGNORECASE)
    return title


def clean_authors(raw_author: str) -> str:
    author = normalize_text(raw_author)
    as_told_by = re.match(r"^As\s+Told\s+By\s+(.+?)\s+to\s+(.+)$", author, flags=re.IGNORECASE)
    if as_told_by:
        return ", ".join(clean_author_name(part) for part in as_told_by.groups())
    as_told_to = re.match(r"^As\s+Told\s+To\s+(.+?)\s+By\s+(.+)$", author, flags=re.IGNORECASE)
    if as_told_to:
        return ", ".join(clean_author_name(part) for part in as_told_to.groups())

    author = re.sub(r"^(By|BY)\s+", "", author)
    author = re.sub(r"^(As\s+Told\s+(By|To))\s+", "", author, flags=re.IGNORECASE)
    author = re.sub(r"\b(By|BY)\b", "", author)
    author = re.sub(r"\s+", " ", author).strip(" ,.;")
    if not author:
        return ""

    author = re.sub(r"\s+(?:and|&)\s+", ", ", author)
    return ", ".join(split_and_clean_author_list(author))


def split_and_clean_author_list(author: str) -> list[str]:
    authors = []
    current = ""
    for part in [p.strip() for p in author.split(",") if p.strip()]:
        clean_part = clean_author_name(part)
        if not clean_part:
            continue
        if current and is_suffix_or_credential(clean_part):
            current = f"{current} {clean_part}"
        else:
            if current:
                authors.append(current)
            current = clean_part
    if current:
        authors.append(current)
    return authors


def is_suffix_or_credential(value: str) -> bool:
    return value.lower() in AUTHOR_SUFFIXES_AND_CREDENTIALS


def clean_author_name(name: str) -> str:
    name = normalize_text(name)
    name = name.replace(",", "")
    name = name.replace(".", "")
    tokens = [t.strip(" ,;") for t in name.split() if t.strip(" ,;")]
    tokens = [AUTHOR_TOKEN_CASING.get(token.lower(), token) for token in tokens]
    return " ".join(tokens)


def find_toc_page(pdf: pdfplumber.PDF, max_pages: int = 16) -> int | None:
    for idx, page in enumerate(pdf.pages[:max_pages]):
        text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
        if re.search(r"\bCONTENTS\b", text, re.IGNORECASE):
            return idx
    return None


def load_magazine_metadata(path: Path) -> dict[tuple[int, int], IssueMetadata]:
    metadata: dict[tuple[int, int], IssueMetadata] = {}
    if not path.exists():
        return metadata

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = [part.strip() for part in line.split(";")]
        if len(parts) < 6 or parts[0] != MAGAZINE_TITLE or parts[5] != "im":
            continue
        try:
            year = int(parts[1])
            month = int(parts[2])
            volume = int(parts[3])
            issue = int(parts[4])
        except ValueError:
            continue
        metadata[(volume, issue)] = IssueMetadata(year=year, month=month, volume=volume, issue=issue)
    return metadata


def parse_issue_metadata(
    pdf_name: str,
    page_text: str,
    metadata_by_issue: dict[tuple[int, int], IssueMetadata],
) -> IssueMetadata:
    match = re.match(r"im(\d{2})(\d{2})", pdf_name.lower())
    if not match:
        raise ValueError(f"Cannot parse volume/issue from {pdf_name}")
    volume = int(match.group(1))
    issue = int(match.group(2))
    known_metadata = metadata_by_issue.get((volume, issue))
    if known_metadata and known_metadata.year and known_metadata.month:
        return known_metadata

    year_match = re.search(r"\b(19|20)\d{2}\b", page_text)
    if not year_match and not known_metadata:
        raise ValueError(f"Cannot parse year from {pdf_name}")
    year = int(year_match.group(0)) if year_match else known_metadata.year

    month = 0
    for month_name, month_number in MONTHS.items():
        if re.search(rf"\b{month_name}\b", page_text, re.IGNORECASE):
            month = month_number
            break
    if not month and known_metadata:
        month = known_metadata.month
    if not month:
        raise ValueError(f"Cannot parse month from {pdf_name}")

    return IssueMetadata(year=year, month=month, volume=volume, issue=issue)


def page_lines(page: pdfplumber.page.Page) -> list[tuple[float, str]]:
    words = page.extract_words(
        x_tolerance=2,
        y_tolerance=3,
        keep_blank_chars=False,
        use_text_flow=False,
    )
    left_limit = page.width * 0.56
    kept = [
        w
        for w in words
        if page.width * 0.04 <= w["x0"] <= left_limit
        and page.height * 0.08 <= w["top"] <= page.height * 0.96
    ]
    lines: list[dict[str, object]] = []
    for word in sorted(kept, key=lambda item: (item["top"], item["x0"])):
        if not lines or abs(float(lines[-1]["top"]) - word["top"]) > 3.2:
            lines.append({"top": word["top"], "words": [word]})
        else:
            line_words = lines[-1]["words"]
            assert isinstance(line_words, list)
            line_words.append(word)

    result = []
    for line in lines:
        line_words = sorted(line["words"], key=lambda item: item["x0"])
        text = " ".join(word["text"] for word in line_words)
        result.append((float(line["top"]), normalize_text(text)))
    return result


def extract_records(page: pdfplumber.page.Page) -> list[TocRecord]:
    records: list[TocRecord] = []
    pending: TocRecord | None = None
    title_without_page: str | None = None

    for _, text in page_lines(page):
        if not text or re.search(r"\bCONTENTS\b", text, re.IGNORECASE) or text.startswith("zwM"):
            continue

        if re.fullmatch(r"\.?\d{1,3}", text) and title_without_page:
            page_number = int(text.lstrip("."))
            if page_number > 250:
                title_without_page = None
                continue
            pending = TocRecord(clean_title(title_without_page), "", page_number)
            records.append(pending)
            title_without_page = None
            continue

        if is_author_line(text):
            if pending:
                pending.authors = clean_authors(text)
                pending = None
            continue

        page_match = re.search(r"(?:[.,;:\s·]*)(\d{1,3})\s*$", text)
        if page_match:
            page_number = int(page_match.group(1))
            if page_number > 250:
                continue
            title = text[: page_match.start()].strip()
            if title:
                pending = TocRecord(clean_title(title), "", page_number)
                records.append(pending)
                title_without_page = None
            continue

        if looks_like_title(text):
            title_without_page = text

    return records


def is_author_line(text: str) -> bool:
    return bool(
        re.match(r"^(By|BY)\s+", text)
        or re.match(r"^As\s+Told\s+(By|To)\s+", text, re.IGNORECASE)
    )


def looks_like_title(text: str) -> bool:
    if len(text) < 3:
        return False
    if re.search(r"\b(STAFF|SUBSCRIPTION|PHOTOGRAPHERS|BACK ISSUES)\b", text):
        return False
    letters = re.sub(r"[^A-Za-z]", "", text)
    return bool(letters) and sum(ch.isupper() for ch in letters) >= max(3, len(letters) // 2)


def rows_for_pdf(
    pdf_path: Path,
    metadata_by_issue: dict[tuple[int, int], IssueMetadata],
) -> list[list[object]]:
    with pdfplumber.open(str(pdf_path)) as pdf:
        page_index = find_toc_page(pdf)
        if page_index is None:
            raise ValueError("No CONTENTS page found")
        page = pdf.pages[page_index]
        page_text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
        metadata = parse_issue_metadata(pdf_path.name, page_text, metadata_by_issue)
        records = extract_records(page)
        if len(records) < 5:
            raise ValueError(f"Too few TOC records found ({len(records)})")

    return [
        [
            MAGAZINE_TITLE,
            metadata.year,
            metadata.month,
            metadata.volume,
            metadata.issue,
            record.title,
            record.authors,
            record.page,
            "",
            record.page,
        ]
        for record in records
    ]


def write_tsv(path: Path, rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write("\t".join(str(field) for field in row) + "\n")


def iter_pdf_paths(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.rglob("*.pdf") if re.match(r"im\d{4}\.pdf$", path.name.lower()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("/Volumes/ASM225/musmemMags/Ironman"))
    parser.add_argument("--output-dir", type=Path, default=Path("/Users/timfogarty/workspace/musmem/data/toc/im"))
    parser.add_argument("--mags-file", type=Path, default=Path("/Users/timfogarty/workspace/musmem/data/mags.dat"))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--one", type=Path, help="Extract a single PDF instead of scanning the input directory.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    metadata_by_issue = load_magazine_metadata(args.mags_file)
    pdf_paths = [args.one] if args.one else iter_pdf_paths(args.input_dir)
    written = skipped = failed = 0

    for pdf_path in pdf_paths:
        output_path = args.output_dir / f"{pdf_path.stem}.tsv"
        if output_path.exists() and not args.overwrite:
            skipped += 1
            continue
        try:
            rows = rows_for_pdf(pdf_path, metadata_by_issue)
            if args.dry_run:
                for row in rows:
                    print("\t".join(str(field) for field in row))
            else:
                write_tsv(output_path, rows)
            written += 1
            print(f"ok {pdf_path.name}: {len(rows)} rows -> {output_path}")
        except Exception as exc:
            failed += 1
            print(f"fail {pdf_path.name}: {exc}")

    print(f"summary written={written} skipped={skipped} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
