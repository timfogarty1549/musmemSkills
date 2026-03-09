#!/usr/bin/env python3
"""
Phase 2: Trace article page ranges through a magazine PDF and write col 9.

Col 8 = printed magazine page number (from the TOC).
Col 9 = PDF page range string — the PDF pages that contain the article,
        used by the website to extract and deliver just those pages.
        Format: "23-25,34-35,50"  (consecutive PDF pages collapsed to N-M)

Algorithm:
  Pre-scan:
    Every page is scanned once for two kinds of continuation markers:
    - "Continued ON  page X" (forward): means the current article section
      ends here and resumes on page X.
    - "Continued FROM page Y" (backward): means the current page is a
      continuation of whatever was on page Y. This catches cases where
      the outgoing marker on page Y was missing or garbled by OCR.
    Word counts are also recorded per page during the pre-scan.

  Per article:
    1. Walk consecutive pages from the article's start page (col 8).
       Stop walking when a "Continued ON" marker is found on a page;
       add the destination to the queue. This prevents runaway ranges
       where ads and other articles' pages would otherwise be included.
    2. Also stop at the next article's start page (from the full .dat).
    3. For each page added to the result, check the from-map: if another
       page says "Continued FROM page P", that page is also part of
       this article — add it to the queue.
    4. Repeat for each queued continuation page.
    5. If --min-words is set, stop the consecutive walk when a page's
       word count is below the threshold (likely a full-page ad).

  Notes:
    - Printed page numbers in continuation markers are treated as PDF
      page numbers (they match in the vast majority of issues).
    - A page may belong to multiple articles (e.g., two articles share
      a page in different columns). Both get the page in their range.
    - OCR tolerance: the regex matches "Continucd", "Continues", etc.

Usage:
    python3 trace_ranges.py <pdf_path> <dat_path> <mag_name> <year> <month> [article_title [min_words]]

    article_title is optional — if provided, only that article is traced.
    min_words is optional — pages with fewer words are treated as ad pages
      and stop the consecutive walk (default: 0 = disabled).
      Useful when OCR-missed markers cause the walk to continue into ads.
      Recommended starting value: 700. Check pre-scan word counts first.
"""

import sys
import re
import os

# OCR-tolerant: matches "Continued", "Continucd", "Continues", etc.
ON_RE = re.compile(
    r'contin[a-z]+\s+on\s+(?:p(?:age|\.)\s*)?(\d+)',
    re.IGNORECASE
)
FROM_RE = re.compile(
    r'contin[a-z]+\s+from\s+(?:p(?:age|\.)\s*)?(\d+)',
    re.IGNORECASE
)


def load_dat(dat_path):
    if not os.path.exists(dat_path):
        return []
    with open(dat_path, 'r', encoding='utf-8', errors='replace') as f:
        return f.readlines()


def build_range_string(pages):
    """Convert list of PDF page numbers into a compact range string.
    e.g. [23, 24, 25, 34, 35, 50] -> '23-25,34-35,50'
    """
    if not pages:
        return ''
    pages = sorted(set(pages))
    ranges = []
    start = pages[0]
    end = pages[0]
    for p in pages[1:]:
        if p == end + 1:
            end = p
        else:
            ranges.append(f"{start}-{end}" if start != end else str(start))
            start = end = p
    ranges.append(f"{start}-{end}" if start != end else str(start))
    return ','.join(ranges)


def prescan_pdf(pdf):
    """
    Scan every page once and build four maps:
      on_map[p]         = dest pages that p sends to via "Continued ON page X"
      from_map[y]       = pages that say "Continued FROM page y" (reverse index)
      page_from_refs[p] = source pages that p itself references via "Continued FROM"
      word_count_map[p] = number of whitespace-delimited words on page p
    Printed in a summary at run time.
    """
    on_map = {}
    from_map = {}
    page_from_refs = {}
    word_count_map = {}
    for i, page in enumerate(pdf.pages):
        pnum = i + 1
        text = page.extract_text() or ''
        word_count_map[pnum] = len(text.split())
        for m in ON_RE.finditer(text):
            dest = int(m.group(1))
            on_map.setdefault(pnum, []).append(dest)
        for m in FROM_RE.finditer(text):
            src = int(m.group(1))
            from_map.setdefault(src, []).append(pnum)
            page_from_refs.setdefault(pnum, []).append(src)
    return on_map, from_map, page_from_refs, word_count_map


def trace_article(start_page, pdf_page_count, all_start_pages, on_map, from_map,
                  page_from_refs, word_count_map=None, min_words=0):
    """
    Return sorted list of PDF page numbers for the article starting at start_page.

    Queue entries are (seg_start, is_jump):
      is_jump=False  main section — walk consecutively, stop only at "Continued ON" or next article
      is_jump=True   jump destination — same walk, but with tighter stop conditions:
                     • stop before a page whose from-refs all point to OTHER articles
                     • stop before an empty-from-refs page if the previous page had our ref

    If min_words > 0: stop (for both section types) before any non-first page whose
    word count is below the threshold — treats low-content pages as likely ads.
    """
    other_starts = sorted(s for s in all_start_pages if s != start_page)

    def next_article_start(after_page):
        for s in other_starts:
            if s > after_page:
                return s
        return pdf_page_count + 1

    visited = set()
    result = []
    queue = [(start_page, False)]

    while queue:
        seg_start, is_jump = queue.pop(0)
        if seg_start in visited:
            continue
        if seg_start < 1 or seg_start > pdf_page_count:
            continue

        next_art = next_article_start(seg_start)
        had_our_marker = False  # did any page in this segment reference our article?

        for p in range(seg_start, next_art):
            if p > pdf_page_count or p in visited:
                break

            # Stop checks for jump segments (not the first page of the segment)
            if is_jump and p != seg_start:
                # Word-count stop: low word count in a continuation section signals an ad page.
                # Only applied to jump destinations (not main article walk), since main sections
                # are bounded by the next article's start page. Not applied to seg_start.
                if min_words > 0 and word_count_map:
                    wc = word_count_map.get(p, 0)
                    if wc < min_words:
                        print(f"    [word-count stop at p.{p}: {wc} words < {min_words}]")
                        break

                from_refs = page_from_refs.get(p, [])
                if from_refs:
                    # Page explicitly continues from somewhere — if none of those
                    # sources are ours, this page belongs to a different article.
                    if not any(ref in visited for ref in from_refs):
                        break
                elif had_our_marker:
                    # Previous page in this segment had our "from" reference,
                    # confirming the last page was our tail. Empty-refs page
                    # after that is likely new territory — stop.
                    break

            visited.add(p)
            result.append(p)

            # Update had_our_marker: did this page reference any of our pages?
            from_refs = page_from_refs.get(p, [])
            if any(ref in visited for ref in from_refs):
                had_our_marker = True

            # Reverse lookup: pages that say "Continued FROM page p"
            for cont_page in from_map.get(p, []):
                if cont_page not in visited:
                    queue.append((cont_page, True))

            # Forward lookup: page p says "Continued ON page X" — stop here
            if p in on_map:
                for dest in on_map[p]:
                    if dest not in visited:
                        queue.append((dest, True))
                break

    return sorted(result)


def main():
    if len(sys.argv) < 6:
        print("Usage: trace_ranges.py <pdf_path> <dat_path> <mag_name> <year> <month> [article_title [min_words]]")
        sys.exit(1)

    pdf_path = os.path.expanduser(sys.argv[1])
    dat_path = os.path.expanduser(sys.argv[2])
    mag_name = sys.argv[3]
    year = int(sys.argv[4])
    month = int(sys.argv[5])
    filter_title = sys.argv[6].lower().strip() if len(sys.argv) > 6 else None
    min_words = int(sys.argv[7]) if len(sys.argv) > 7 else 0

    print(f"\n=== Phase 2: Article Range Tracing ===")
    print(f"PDF:  {pdf_path}")
    print(f"DAT:  {dat_path}")
    print(f"Issue: {mag_name} {year}/{month:02d}")
    if filter_title:
        print(f"Filter: '{filter_title}'")
    if min_words > 0:
        print(f"Min words: {min_words} (pages below this treated as ads)")

    if not os.path.exists(pdf_path):
        print(f"ERROR: PDF not found: {pdf_path}")
        sys.exit(1)

    import pdfplumber

    all_lines = load_dat(dat_path)

    # Collect all article start pages for this issue
    all_start_pages = set()
    target_indices = []

    for i, line in enumerate(all_lines):
        parts = line.rstrip('\n').split('\t')
        if len(parts) < 8:
            continue
        if parts[0].strip() != mag_name:
            continue
        try:
            if int(parts[1]) != year or int(parts[2]) != month:
                continue
        except ValueError:
            continue
        try:
            pg = int(parts[7].strip())
            if pg > 0:
                all_start_pages.add(pg)
        except (ValueError, IndexError):
            pass
        if len(parts) >= 9 and parts[8].strip():
            continue
        title = parts[5].strip()
        if title == 'Table of Contents':
            continue
        if filter_title and filter_title not in title.lower():
            continue
        target_indices.append(i)

    print(f"\nArticle start pages: {sorted(all_start_pages)}")
    print(f"Entries to trace: {len(target_indices)}")
    if not target_indices:
        print("Nothing to do.")
        sys.exit(0)

    traced = 0
    skipped = 0

    with pdfplumber.open(pdf_path) as pdf:
        pdf_page_count = len(pdf.pages)
        print(f"PDF pages: {pdf_page_count}")

        print("\nPre-scanning all pages for continuation markers...")
        on_map, from_map, page_from_refs, word_count_map = prescan_pdf(pdf)

        if on_map:
            print("  Forward (Continued ON):")
            for p in sorted(on_map):
                print(f"    p.{p} → {on_map[p]}")
        if from_map:
            print("  Reverse (Continued FROM):")
            for src in sorted(from_map):
                print(f"    p.{src} ← {from_map[src]}")

        if min_words > 0:
            low_pages = [(p, wc) for p, wc in sorted(word_count_map.items()) if wc < min_words]
            if low_pages:
                print(f"  Low word-count pages (< {min_words}):")
                for p, wc in low_pages:
                    print(f"    p.{p}: {wc} words")

        print()

        for i in target_indices:
            parts = all_lines[i].rstrip('\n').split('\t')
            title = parts[5].strip()
            try:
                start_page = int(parts[7].strip())
            except (ValueError, IndexError):
                print(f"  SKIP (no page number): {title}")
                skipped += 1
                continue

            if start_page < 1 or start_page > pdf_page_count:
                print(f"  SKIP (page {start_page} out of range): {title}")
                skipped += 1
                continue

            pages = trace_article(start_page, pdf_page_count, all_start_pages,
                                  on_map, from_map, page_from_refs,
                                  word_count_map, min_words)
            range_str = build_range_string(pages)
            print(f"  {title!r}  p.{start_page} → {range_str}")

            stripped = all_lines[i].rstrip('\n').rstrip('\t')
            all_lines[i] = stripped + f"\t{range_str}\n"
            traced += 1

    with open(dat_path, 'w', encoding='utf-8') as f:
        f.writelines(all_lines)

    print(f"\nResults: {traced} traced, {skipped} skipped")
    print(f"Updated: {dat_path}")
    print("\n=== Phase 2 Complete ===")


if __name__ == '__main__':
    main()
