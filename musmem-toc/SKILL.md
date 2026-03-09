---
name: musmem-toc
description: Use when extracting table of contents from bodybuilding magazine PDFs to populate toc .dat files, or when tracing article page ranges through PDFs to add a range column.
---

# MuscleMemory Magazine TOC

Extracts table-of-contents data from scanned magazine PDFs and writes to `~/workspace/musmem/toc/{mag}.dat`.

Two phases — run one at a time per user instruction.

## File Locations

| Resource | Path |
|----------|------|
| TOC data files | `~/workspace/musmem/toc/{mag}.dat` |
| PDF files | `~/workspace/s3/musmem/magPdfs/{mag}/` |
| Phase 1 script | `musmem-toc/python/extract_toc.py` |
| Phase 2 script | `musmem-toc/python/trace_ranges.py` |

## PDF Naming Convention (per magazine)

| Code | Name | PDF naming | Example |
|------|------|-----------|---------|
| `im` | IronMan | `im{VV}{NN}.pdf` — volume + issue | `im1801.pdf` = Vol 18, Issue 1 |
| `sh` | Strength & Health | `sh{YY}{MM}.pdf` — year + month | `sh6001.pdf` = 1960 January |

More magazines may be added; verify the naming convention per magazine when first encountered.

**Always derive year and month from the magazine cover (page 1), not the filename.**
For combined-month issues (e.g., "June-July"), use the month stated on the cover.

## .dat Format

Tab-delimited, 8 columns (9th added by Phase 1 for TOC rows; Phase 2 fills it for all article rows):
```
Magazine Name  Year  Month  Volume  Issue  Article Title  Author(s)  Mag Page  [PDF Pages]
```
- Month may be negative when indeterminate (e.g., `-8` = "8th issue that year, month unknown")
- **Col 8** = printed magazine page number where the article starts (from the TOC)
- **Col 9** = PDF page range — the PDF pages that contain the article, used to deliver just those pages to the reader. Format: `"6"` (single page) or `"23-25,34-35,50"` (multi-page with gaps). Numbers are PDF page numbers, which usually equal the printed page numbers.
- The `Table of Contents` row gets col 9 from Phase 1 (the PDF page where the TOC was found); all other rows get col 9 from Phase 2

## OCR Quality Warning

These PDFs are scanned magazines with varying text-layer quality:
- **Some issues**: clean, readable text → good extraction results
- **Many older issues**: OCR artifacts (split words, merged words, characters stored at scattered y-positions) → titles will be garbled and need manual cleanup
- **Script behavior when OCR is poor**: uses y-position word clustering to reconstruct lines; still extracts entries and page numbers, but both may contain errors
- **Page number errors under poor OCR**: entries flagged as "new" may actually exist in the .dat under a different page — verify before appending to the real file

> **Python scripting rule:** Never use `python3 -c` or heredocs. Copy scripts from the skill's `python/` directory to `/tmp/`, then run from there.

---

## Phase 1: TOC Extraction

**Input:** magazine code + issue identifier + year + month + volume + issue

### Safety Rule
**Always test against a temp copy of the .dat file first:**
```bash
cp ~/workspace/musmem/toc/{mag}.dat /tmp/{mag}_test.dat
```
Verify output looks correct before running against the real file.

### Setup (first time per session)
```bash
pip3 install pdfplumber --break-system-packages
```

### Workflow

1. Look at the cover page of the PDF (page 1) to determine year and month
2. Get volume and issue from the magazine masthead (usually page 2-3)
3. Test against temp copy first:
   ```bash
   cp ~/workspace/musmem/toc/{mag}.dat /tmp/{mag}_test.dat
   cp {skill_dir}/python/extract_toc.py /tmp/extract_toc.py
   python3 /tmp/extract_toc.py {pdf} /tmp/{mag}_test.dat {mag_name} {year} {month} {volume} {issue}
   ```
4. Review output:
   - **Cover date**: script shows detected cover date — verify it matches what you provided
   - **Existing match**: matched by volume+issue or year+month
   - **Title notes**: pages already present but with different titles — useful for spotting hand-entry errors or OCR differences
   - **Author discrepancies**: same page, different author — note for manual review
   - **TOC location row**: a `Table of Contents` row records where the TOC was found; col 8 is the printed magazine page (0 if not determinable), col 9 is the PDF page
   - **Entries to append**: new articles not yet in .dat; if OCR quality is "poor", cross-check page numbers against the .dat before accepting
5. If output looks good, run against the real .dat file

### TOC Detection
Script scans first 40 pages. A page qualifies as a TOC page only if it:
1. Contains a TOC keyword: `CONTENTS`, `TABLE OF CONTENTS`, `IN THIS ISSUE`, `THIS MONTH`
2. Has ≥3 lines ending in a number (confirming article → page number format)

### When TOC Not Found
If the script says "No TOC pages detected":
- The magazine may not have a formal table of contents
- TOC may appear after page 40 (rare)
- The TOC text layer may be too fragmented for detection (e.g., multi-column layout in early issues)

In these cases, manual entry or a different extraction approach is needed.

---

## Phase 2: Article Range Tracing

**Input:** magazine code + vol/issue or year/month, optionally a specific article title

### Safety Rule
**Always test against a temp copy of the .dat file first:**
```bash
cp ~/workspace/musmem/toc/{mag}.dat /tmp/{mag}_test.dat
```

### Workflow

1. Copy and run:
   ```bash
   cp {skill_dir}/python/trace_ranges.py /tmp/trace_ranges.py
   python3 /tmp/trace_ranges.py {pdf} /tmp/{mag}_test.dat {mag_name} {year} {month}
   ```

2. Script pre-scans all PDF pages for two kinds of continuation markers (OCR-tolerant regex — matches "Continucd", "Continues", etc.):
   - **"Continued ON page X"** (forward): article section ends here, resumes at X
   - **"Continued FROM page Y"** (backward): this page is a continuation of Y — catches articles where the outgoing marker on Y was garbled by OCR
   - Pre-scan summary is printed; use it to verify expected markers were found

3. For each article, builds the page range:
   - **Main body**: walks consecutive pages from col 8, stopping when a "Continued ON" marker is found (destination queued) or the next article's start page is reached
   - **Jump destinations**: walks consecutive pages from the target with tighter stop conditions:
     - Stops before a page whose "from" references all point to *other* articles
     - Stops before an empty-reference page that immediately follows a page explicitly referencing this article (end-of-continuation signal)
   - A page shared between two articles (e.g., two articles in different columns) will appear in both ranges — correct behavior
   - Skips `Table of Contents` rows (already have col 9 from Phase 1)
   - Skips rows that already have col 9

4. Review output — watch for:
   - **Continuation jumps**: non-consecutive ranges like `20-21,43` — verify the jump page is plausible
   - **Large ranges at end of issue**: when a page gap has no article entries, the preceding article gets those pages (often correct, e.g., a multi-page "Readers Roundup")
   - **Skipped entries**: page out of PDF range (bad data in col 8)
   - **Pre-existing col 9 with bad value**: entries that already have col 9 are skipped even if wrong — fix manually first

5. If output looks good, run against the real .dat file

### Known Limitation: Undetected Markers
When OCR is too poor to read continuation markers, articles that jump to non-consecutive pages show only their main consecutive section. The pre-scan summary lists all markers found — if an expected continuation isn't listed, the OCR on that page is too fragmented. Correct col 9 manually in that case.

---

## Magazine Code → Name Mapping

| Code | Name |
|------|------|
| `im` | `IronMan` |
| `sh` | `Strength & Health` |
| `mb` | `Muscle Builder` |
| `md` | `Muscular Development` |
| `mp` | `Muscle Power` |
| `yp` | `Your Physique` |
| `ma` | `Mr America` |
| `mti` | `Muscle Training Illustrated` |

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Running against real .dat without testing | Always test on `/tmp/{mag}_test.dat` first |
| Using filename to determine year/month | Look at the cover page; filename convention varies per magazine |
| Assuming combined-month issues use the first month | Use whatever month the cover shows |
| Expecting clean titles from old scanned PDFs | OCR artifacts are normal; review title notes and clean up manually |
| Blindly appending "new" entries when OCR is poor | Poor OCR can misread page numbers; verify "new" entries against the .dat before running on the real file |
| Using `python3 -c` or heredoc | Copy script to `/tmp/`, run `python3 /tmp/script.py` |
| Processing multiple issues in parallel | One issue at a time |
| Running Phase 2 when col 9 already has a bad value | Phase 2 skips rows that already have col 9 — fix bad values manually first |
| Missing continuation jumps in Phase 2 output | Check the pre-scan summary — if the marker isn't listed, OCR is too poor to read it; correct col 9 manually |
