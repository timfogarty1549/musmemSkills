#!/usr/bin/env python3
"""
Phase 1: Extract TOC from a magazine PDF and append new entries to .dat file.

Usage:
    python3 extract_toc.py <pdf_path> <dat_path> <mag_name> <year> <month> <volume> <issue>

    year/month: as shown on the magazine cover (use the later month for combined issues)
    volume/issue: as printed in the magazine; use 0 if unknown
"""

import sys
import re
import os

TOC_KEYWORDS = re.compile(
    r'\b(contents|table of contents|in this issue|this month)\b',
    re.IGNORECASE
)
MONTH_NAMES = re.compile(
    r'\b(january|february|march|april|may|june|july|august|september|'
    r'october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b',
    re.IGNORECASE
)
SMALL_WORDS = {
    'a', 'an', 'the', 'and', 'but', 'or', 'nor', 'for', 'so', 'yet',
    'at', 'by', 'in', 'of', 'on', 'to', 'up', 'as', 'it', 'is', 'vs',
    'via', 'with', 'from', 'into', 'than', 'that', 'this',
}


# ── helpers ───────────────────────────────────────────────────────────────────

def to_title_case(text):
    """Convert text (possibly all-caps) to proper title case."""
    words = text.split()
    result = []
    for i, word in enumerate(words):
        if re.match(r'^\d', word):
            result.append(word)
        elif i == 0 or i == len(words) - 1:
            result.append(word.capitalize())
        elif word.lower() in SMALL_WORDS:
            result.append(word.lower())
        else:
            result.append(word.capitalize())
    return ' '.join(result)


def load_dat(dat_path):
    rows = []
    if not os.path.exists(dat_path):
        return rows
    with open(dat_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n')
            if line.strip():
                rows.append(line.split('\t'))
    return rows


def find_issue_entries(existing_rows, mag_name, year, month, volume, issue):
    """
    Return all .dat rows for this issue.
    Matches by volume+issue first; falls back to year+month.
    Returns (rows, match_type).
    """
    vol_str = str(volume)
    iss_str = str(issue)

    if vol_str != '0' and iss_str != '0':
        rows = [r for r in existing_rows
                if len(r) >= 5
                and r[0].strip() == mag_name
                and r[3].strip() == vol_str
                and r[4].strip() == iss_str]
        if rows:
            return rows, 'volume+issue'

    rows = [r for r in existing_rows
            if len(r) >= 3
            and r[0].strip() == mag_name
            and r[1].strip() == str(year)
            and r[2].strip() == str(month)]
    return rows, 'year+month'


def assess_ocr_quality(lines):
    """
    Heuristic: if many "words" in title lines are 1-2 uppercase chars,
    the OCR is likely poor (characters are being split).
    Returns 'poor' or 'good'.
    """
    suspicious = 0
    total = 0
    for line in lines:
        for word in line.split():
            if re.match(r'^[A-Z]{1,2}$', word):
                suspicious += 1
            total += 1
    if total == 0:
        return 'unknown'
    ratio = suspicious / total
    return 'poor' if ratio > 0.10 else 'good'


def extract_cover_date_hint(page):
    """Try to read the cover page text to show the user for date verification."""
    text = page.extract_text() or ''
    # Look for month+year pattern
    m = re.search(
        r'(january|february|march|april|may|june|july|august|september|'
        r'october|november|december)\s+\d{4}',
        text, re.IGNORECASE
    )
    if m:
        return m.group(0)
    # Also check for "Month-Month Year" combined issue
    m2 = re.search(
        r'(january|february|march|april|may|june|july|august|september|'
        r'october|november|december)[- /]+'
        r'(january|february|march|april|may|june|july|august|september|'
        r'october|november|december)\s+\d{4}',
        text, re.IGNORECASE
    )
    if m2:
        return m2.group(0)
    return None


def _crop_lines(page, x0_frac, x1_frac):
    """Extract text lines from a horizontal slice of the page."""
    bbox = page.bbox
    x0 = max(page.width * x0_frac, bbox[0])
    x1 = min(page.width * x1_frac, bbox[2])
    cropped = page.crop((x0, bbox[1], x1, bbox[3]))
    text = cropped.extract_text(x_tolerance=5, y_tolerance=3) or ''
    return text.split('\n')


def _count_number_ending_lines(lines):
    """Count lines that end in a number (TOC pattern: title ... page)."""
    num_end = re.compile(r'\d+\s*$')
    return sum(1 for l in lines if num_end.search(l.strip()) and len(l.strip()) > 5)


def detect_toc_pages(pdf, scan_limit=40):
    """
    A page qualifies as a TOC page only if:
    - it contains a TOC keyword, AND
    - either its left column or right column has ≥3 lines ending in a number
    Returns list of (pdf_page_num, column) where column is 'left' or 'right' or 'full'.
    """
    toc_pages = []
    limit = min(scan_limit, len(pdf.pages))
    for i in range(limit):
        page = pdf.pages[i]
        text = page.extract_text() or ''
        if not TOC_KEYWORDS.search(text):
            continue
        # Check left column (0–42% of width) and right column (42–100%)
        left_lines  = _crop_lines(page, 0.0, 0.42)
        right_lines = _crop_lines(page, 0.42, 1.0)
        full_lines  = text.split('\n')
        left_n  = _count_number_ending_lines(left_lines)
        right_n = _count_number_ending_lines(right_lines)
        full_n  = _count_number_ending_lines(full_lines)
        best_n  = max(left_n, right_n, full_n)
        if best_n >= 3:
            col = 'left' if left_n == best_n else ('right' if right_n == best_n else 'full')
            toc_pages.append((i + 1, col))
            print(f"  [TOC] PDF page {i + 1}: {best_n} number-ending lines in {col} column")
        else:
            print(f"  [skip] PDF page {i + 1}: keyword found but only {best_n} number-ending lines")
    return toc_pages


def extract_toc_column(page, column):
    """
    Extract text lines from the best column for TOC content.
    Uses y-position word clustering for better handling of character-scattered OCR.
    """
    bbox = page.bbox
    if column == 'left':
        x0 = bbox[0]
        x1 = min(page.width * 0.42, bbox[2])
    elif column == 'right':
        x0 = max(page.width * 0.42, bbox[0])
        x1 = bbox[2]
    else:
        x0, x1 = bbox[0], bbox[2]
    cropped = page.crop((x0, bbox[1], x1, bbox[3]))
    return _word_cluster_lines(cropped)


def get_toc_printed_page(page):
    """
    Best-effort: find the printed page number of the TOC page itself.
    Looks for a standalone number in the page header/footer.
    Returns the page number as int, or 0 if not determinable.
    """
    words = page.extract_words(x_tolerance=3, y_tolerance=3)
    if not words:
        return 0

    page_h = page.height
    # Look in top 8% or bottom 8% of page for isolated numbers
    for zone_min, zone_max in [(0, page_h * 0.08), (page_h * 0.92, page_h)]:
        candidates = [w for w in words
                      if zone_min <= w['top'] <= zone_max
                      and re.match(r'^\d{1,3}$', w['text'])]   # 1-3 digits only; excludes years
        if candidates:
            # Take the one with most typical page-number position (near center-x or margins)
            return int(candidates[0]['text'])
    return 0


def _fix_end_number(line):
    """
    Collapse space-separated digits at the END of a line into a proper number.
    e.g. "Some Title 1 9" → "Some Title 19"
         "Some Title 3 1" → "Some Title 31"
    Applied twice to handle 3-digit page numbers ("1 0 2" → "102").
    """
    for _ in range(2):
        line = re.sub(r'(\d) (\d)(\s*)$', lambda m: m.group(1) + m.group(2) + m.group(3), line)
    return line


def _word_cluster_lines(cropped_page, bucket=6):
    """
    Reconstruct text lines from a cropped page by clustering words by y-position.
    Uses extract_words (positional) instead of extract_text, which handles PDFs
    where individual characters are stored at scattered y-coordinates (poor OCR).
    Returns list of line strings, each being words in that y-bucket joined by spaces.
    """
    words = cropped_page.extract_words(x_tolerance=5, y_tolerance=3)
    buckets = {}
    for w in words:
        y = round(w['top'] / bucket) * bucket
        buckets.setdefault(y, []).append(w)
    lines = []
    for y in sorted(buckets):
        ws = sorted(buckets[y], key=lambda w: w['x0'])
        lines.append(' '.join(w['text'] for w in ws))
    return lines


def _collapse_char_spaces(text):
    """
    Merge runs of space-separated single alphabetic characters into words.
    e.g. "H o w G o o d" → "HowGood"  (best-effort for character-spaced OCR)
    Multi-char tokens break the run; punctuation and digits are left as-is.
    """
    tokens = text.split(' ')
    result = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if len(tok) == 1 and tok.isalpha():
            run = tok
            i += 1
            while i < len(tokens) and len(tokens[i]) == 1 and tokens[i].isalpha():
                run += tokens[i]
                i += 1
            result.append(run)
        else:
            result.append(tok)
            i += 1
    return ' '.join(result)


def parse_toc_lines(lines):
    """
    Parse TOC lines into (title, author, page_num) tuples.
    Converts all-caps to title case. Associates "By …" lines with preceding entry.
    Handles two sh-specific quirks:
    - spaced page numbers ("1 9" → "19")
    - page number on a separate line above the title (held as pending_page)
    """
    entries = []
    seen_pages = set()
    pending_page = None   # page number seen on its own line, waiting for a title line

    line_re = re.compile(r'^(.+?)\s+(\d{1,3})\s*$')
    noise_re = re.compile(r'^[\s.\-,;:!?0-9/\']+$')
    by_re = re.compile(r'^[Bb]y\s*(.+)')
    standalone_num_re = re.compile(r'^\d{1,3}$')

    SKIP = {
        'contents', 'table of contents', 'in this issue', 'this month',
        'page', 'staff', 'editorial staff', 'on our cover',
    }
    # Stop parsing TOC when we hit the staff/contributor section
    STOP_MARKERS = re.compile(
        r'\b(strength\s*&\s*health\s*staff|featured\s*contributors?|'
        r'staff\s*photographers?|on\s*the\s*cover)\b',
        re.IGNORECASE
    )

    last_idx = None

    for line in lines:
        line = line.strip()
        if not line or len(line) < 4:
            continue

        # Collapse spaced trailing digits before any parsing ("1 9" → "19")
        line = _fix_end_number(line)

        if noise_re.match(line):
            continue
        # Stop at staff/contributor section — these follow the TOC entries
        if STOP_MARKERS.search(line):
            break
        # Skip "Vol. N Month Year No. N" headers
        if re.match(r'^Vol\.?\s+\d', line, re.IGNORECASE) and MONTH_NAMES.search(line):
            continue

        # Author attribution line
        by_m = by_re.match(line)
        if by_m and last_idx is not None:
            raw = by_m.group(1).strip()
            raw = re.sub(r'[.\s]+$', '', raw)
            raw = re.sub(r'([a-z])([A-Z])', r'\1 \2', raw)   # fix merged words
            author = re.sub(r'\s+', ' ', raw).strip()
            if 2 < len(author) < 60:
                t, _, p = entries[last_idx]
                entries[last_idx] = (t, author, p)
            last_idx = None
            pending_page = None
            continue

        # Standalone page number on its own line — hold it for the next title line
        if standalone_num_re.match(line):
            pending_page = int(line)
            last_idx = None
            continue

        m = line_re.match(line)
        if m:
            raw_title = re.sub(r'[\s.]+$', '', m.group(1)).strip()
            page = int(m.group(2))
            pending_page = None   # explicit page on this line, clear any pending
        elif pending_page is not None:
            # Title line without trailing number; use the pending standalone page
            raw_title = re.sub(r'[\s.]+$', '', line).strip()
            page = pending_page
            pending_page = None
        else:
            last_idx = None
            continue

        if raw_title.lower() in SKIP or len(raw_title) < 3 or page > 500:
            last_idx = None
            continue

        # Filter date fragments (e.g., "Uary, 1960" — month name fragment + year)
        if re.match(r'^[A-Za-z]+,?\s*(19|20)\d{2}$', raw_title.strip()):
            last_idx = None
            continue

        raw_title = _collapse_char_spaces(raw_title)
        title = to_title_case(raw_title)

        # Deduplicate by page number (same page = same article)
        if page not in seen_pages:
            seen_pages.add(page)
            entries.append((title, '', page))
            last_idx = len(entries) - 1
        else:
            last_idx = None

    return entries


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 8:
        print("Usage: extract_toc.py <pdf_path> <dat_path> <mag_name> <year> <month> <volume> <issue>")
        sys.exit(1)

    pdf_path = os.path.expanduser(sys.argv[1])
    dat_path = os.path.expanduser(sys.argv[2])
    mag_name = sys.argv[3]
    year     = int(sys.argv[4])
    month    = int(sys.argv[5])
    volume   = sys.argv[6]
    issue    = sys.argv[7]

    print(f"\n=== Phase 1: TOC Extraction ===")
    print(f"PDF:  {pdf_path}")
    print(f"DAT:  {dat_path}")
    print(f"Issue: {mag_name} {year}/{month:02d}  vol={volume}  issue={issue}")

    if not os.path.exists(pdf_path):
        print(f"ERROR: PDF not found: {pdf_path}")
        sys.exit(1)

    import pdfplumber

    # ── Cover page: show date hint for verification ───────────────────────────
    with pdfplumber.open(pdf_path) as pdf:
        cover_hint = extract_cover_date_hint(pdf.pages[0])
        if cover_hint:
            print(f"\nCover date detected: {cover_hint!r}")
            print(f"  → You provided: month={month}, year={year}  (verify these match)")
        else:
            print(f"\n[Cover] No readable date found on cover page.")

        # ── Load existing entries ─────────────────────────────────────────────
        existing_rows = load_dat(dat_path)
        issue_rows, match_type = find_issue_entries(
            existing_rows, mag_name, year, month, volume, issue
        )
        print(f"\nExisting .dat entries for this issue: {len(issue_rows)} (matched by {match_type})")

        # Build set of already-present page numbers for this issue
        existing_pages = set()
        for r in issue_rows:
            try:
                existing_pages.add(int(r[7].strip()))
            except (IndexError, ValueError):
                pass

        # ── Find TOC pages ────────────────────────────────────────────────────
        print("\nScanning PDF for TOC pages...")
        toc_pdf_pages = detect_toc_pages(pdf)

        if not toc_pdf_pages:
            print("WARNING: No TOC pages detected in first 40 pages.")
            sys.exit(0)

        print(f"TOC found on PDF pages: {toc_pdf_pages}")

        # ── Extract entries from each TOC page ────────────────────────────────
        all_entries = []
        toc_printed_pages = []   # printed magazine page number for each TOC PDF page

        for pdf_pnum, column in toc_pdf_pages:
            page = pdf.pages[pdf_pnum - 1]

            lines = extract_toc_column(page, column)
            entries = parse_toc_lines(lines)

            # Assess OCR quality
            quality = assess_ocr_quality(lines)
            if quality == 'poor':
                print(f"  [page {pdf_pnum}] WARNING: OCR quality appears poor — titles may have artifacts")

            print(f"  [page {pdf_pnum}/{column}] {len(entries)} entries parsed  (OCR: {quality})")
            all_entries.extend(entries)

            # Find printed page number of this TOC page
            pp = get_toc_printed_page(page)
            toc_printed_pages.append((pdf_pnum, pp))

    # ── Deduplicate (keep first occurrence of each page) ──────────────────────
    seen_pages = set()
    unique_entries = []
    for t, a, p in all_entries:
        if p not in seen_pages:
            seen_pages.add(p)
            unique_entries.append((t, a, p))

    print(f"\nTotal unique TOC entries parsed: {len(unique_entries)}")

    # ── Compare with existing ─────────────────────────────────────────────────
    new_entries = []
    already_present = []
    page_discrepancies = []

    for title, author, page in unique_entries:
        if page in existing_pages:
            already_present.append((title, author, page))
            # Check if title differs significantly
            for r in issue_rows:
                try:
                    if int(r[7].strip()) == page:
                        existing_title = r[5].strip()
                        existing_author = r[6].strip() if len(r) > 6 else ''
                        if existing_title.lower() != title.lower():
                            page_discrepancies.append({
                                'page': page,
                                'dat_title': existing_title,
                                'pdf_title': title,
                                'dat_author': existing_author,
                                'pdf_author': author,
                            })
                        break
                except (IndexError, ValueError):
                    pass
        else:
            new_entries.append((title, author, page))

    print(f"  Already in .dat (by page match): {len(already_present)}")
    print(f"  New entries:                      {len(new_entries)}")

    if page_discrepancies:
        print(f"\n=== TITLE NOTES (same page, different title) ===")
        for d in page_discrepancies:
            print(f"  p.{d['page']}: .dat title: {d['dat_title']!r}")
            print(f"         PDF title: {d['pdf_title']!r}")
            if d['dat_author'] != d['pdf_author'] and d['pdf_author']:
                print(f"         .dat author: {d['dat_author']!r}  PDF author: {d['pdf_author']!r}")

    # ── TOC location rows ─────────────────────────────────────────────────────
    # Add one row per TOC PDF page recording where the TOC was found.
    # Col 8 = printed magazine page; col 9 = PDF page number.
    already_has_toc = any(
        r[5].strip() == 'Table of Contents'
        for r in issue_rows
        if len(r) > 5
    )
    toc_rows_to_add = []
    if not already_has_toc:
        for pdf_pnum, printed_pp in toc_printed_pages:
            toc_rows_to_add.append(('Table of Contents', '', printed_pp, pdf_pnum))

    # ── Append to .dat ────────────────────────────────────────────────────────
    if toc_rows_to_add or new_entries:
        print(f"\n=== ENTRIES TO APPEND ({len(toc_rows_to_add) + len(new_entries)}) ===")
        lines_to_append = []
        # TOC location rows include col 9 (PDF page)
        for title, author, mag_page, pdf_page in toc_rows_to_add:
            row = f"{mag_name}\t{year}\t{month}\t{volume}\t{issue}\t{title}\t{author}\t{mag_page}\t{pdf_page}"
            lines_to_append.append(row)
            print(f"  {row}")
        # Regular article rows (col 9 left empty; Phase 2 fills it)
        for title, author, page in new_entries:
            row = f"{mag_name}\t{year}\t{month}\t{volume}\t{issue}\t{title}\t{author}\t{page}"
            lines_to_append.append(row)
            print(f"  {row}")

        with open(dat_path, 'a', encoding='utf-8') as f:
            for line in lines_to_append:
                f.write(line + '\n')

        print(f"\nAppended {len(lines_to_append)} rows to {dat_path}")
    else:
        print("\nNothing new to append.")

    print("\n=== Phase 1 Complete ===")


if __name__ == '__main__':
    main()
