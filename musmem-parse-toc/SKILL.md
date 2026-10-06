---
name: musmem-parse-toc
description: Extract MuscleMemory magazine table-of-contents TSV rows from OCR-backed magazine PDFs, especially IronMan PDFs, while applying MuscleMemory TOC formatting rules and rejecting unreliable OCR output instead of writing gibberish.
---

# MuscleMemory TOC Parsing

Use this skill when extracting or validating table-of-contents data from MuscleMemory magazine PDFs.

## Output Format

Write tab-separated values with exactly 10 columns, A through J:

1. Magazine title, for IronMan use `IronMan`
2. Year
3. Month number
4. Volume
5. Issue
6. Article title
7. Authors
8. Article page
9. Empty column
10. Article page repeated from column H

Do not write a header row. Do not CSV-escape or otherwise escape characters. Output literal tab-separated text.

## Normalization Rules

- Article titles should be AP/Chicago-style title case.
- Remove `By` from author fields.
- Multiple authors should be comma separated.
- Do not treat commas inside a single author name, suffix, or credential as author separators.
- Remove periods from author names.
- Keep author suffixes and credentials such as `Jr`, `Sr`, `PhD`, `MD`, `RPT`, `BA`, `MA`, `DC`, and `DO`, but remove commas before them.
- Normalize credential casing; for example, `Phd` and `PhD` should output as `PhD`.
- Replace `and` and `&` between author names with a comma separator.
- Example: `John Smith, MD, Tom Jones, Jr` becomes `John Smith MD, Tom Jones Jr`.
- Example: `John Smith and Tom Jones` becomes `John Smith, Tom Jones`.
- Preserve literal quote characters, apostrophes, and other article-title or byline punctuation unless a specific cleanup rule says otherwise.

## Safety Rules

- Prefer dry runs before writing TSVs.
- Never batch-write files whose OCR quality has not been checked.
- If OCR is character-fragmented, vertically interleaved, or produces suspicious rows, do not write a TSV.
- Reject output with too few TOC rows, page numbers over 250, page zero, titles full of separated single letters, or obvious masthead/subscription text.
- Existing hand-curated TSV files should be left untouched unless the user explicitly asks to overwrite them.
- For IronMan, write trusted TSVs under `/Users/timfogarty/workspace/musmem/data/toc/im/`.

## Script

Use the bundled script for the current word-based extractor:

```bash
python3 ~/workspace/skills/musmemSkills/musmem-parse-toc/python/extract_ironman_toc.py --one /path/to/im4406.pdf --dry-run
```

To write a single reviewed file:

```bash
python3 ~/workspace/skills/musmemSkills/musmem-parse-toc/python/extract_ironman_toc.py --one /path/to/im4406.pdf --overwrite
```

For batch attempts, run a dry-run or quality scan first. Only write files that match a known-good layout/OCR pattern.

## Known Findings

- `im4406.pdf`, page 10, is a known-good example for the current word-based extractor.
- Many IronMan PDFs from the 1970s and early 1980s have visually readable TOC pages but broken OCR word grouping. They require a character-position parser or manual review.
- Examples of problematic files include `im4004.pdf`, `im4202.pdf`, and `im4504.pdf`: visible TOCs are readable, but current word extraction yields OCR artifacts.

## Recommended Workflow

1. Locate the TOC page by searching early pages for `CONTENTS`.
2. Render the candidate TOC page for visual verification when layout matters.
3. Inspect OCR quality:
   - healthy word OCR resembles normal words and lines;
   - broken OCR has a high fraction of one-character "words" or interleaved vertical text.
4. Run the extractor with `--dry-run`.
5. Compare several rows against the rendered page.
6. Write only one reviewed TSV at a time until the extractor is proven for that layout family.
7. Keep a reject/review list for files that fail OCR quality checks.
