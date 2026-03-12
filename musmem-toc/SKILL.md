---
name: musmem-toc
description: Use when extracting table of contents from bodybuilding magazine PDFs to populate toc .dat files, or when tracing article page ranges through PDFs to add a range column.
---

# MuscleMemory Magazine TOC

Extracts table-of-contents data from scanned magazine PDFs and writes to per-issue `.dat` files under `~/workspace/musmem/toc/{mag}/`.

Two phases — run one at a time per user instruction.

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `https://musclememory.org/api/mags` | List all magazines (title, code, date range, issue/scan counts) |
| `https://musclememory.org/api/mags?title={title}&brief=true` | List all issues for a magazine, with `year`, `month`, `volume`, `issue`, `code`, `own` (copies owned), and `toc` (existing TOC data or null) |

The `code` field in the API matches the magazine code used in filenames (e.g., `"im"` → `im.dat`, `~/workspace/musmem/toc/im/`).

## File Locations

| Resource | Path |
|----------|------|
| Monolithic TOC data file (source of truth) | `~/workspace/musmem/toc/{mag}.dat` |
| Per-issue TOC files (split from monolithic) | `~/workspace/musmem/toc/{mag}/{filename}.dat` |
| PDF files | `~/workspace/s3/musmem/magPdfs/{mag}/` |
| Phase 1 script | `musmem-toc/python/extract_toc.py` |
| Phase 2 script | `musmem-toc/python/trace_ranges.py` |
| Split script | `musmem-toc/python/split_dat.py` |
| Merge script | `musmem-toc/python/merge_dat.py` |
| Status script | `musmem-toc/python/generate_status.py` |
| Status output | `~/workspace/musmem/toc/TOC_STATUS.html` |

## Per-Issue File Naming Convention

Each issue gets its own `.dat` file inside a per-magazine folder. The filename encodes the issue identifier using one of two schemes depending on the magazine:

**Year + month** (`sh`, `mb`, `mma`, `mtis`, `rpj`):
```
{mag}{YYYY}{MM:02d}.dat
```
Examples: `sh193407.dat` (July 1934), `mma199500.dat` (annual, month=00)

**Volume + issue** (all other magazines, when volume > 0):
```
{mag}{VV:02d}{NN:02d}.dat
```
Example: `im0304.dat` (Vol 3, Issue 4)

**3-digit issue** (when volume = 0):
```
{mag}{NNN:03d}.dat
```
Examples: `mti001.dat` (Issue 1), `mmi042.dat` (Issue 42 with vol=0)

Notes:
- `mti` always has vol=0, so always uses 3-digit issue
- `mmi` uses vol+issue normally, but falls back to 3-digit issue when vol=0

## PDF Naming Convention (per magazine)

| Code | Name | PDF naming | Example |
|------|------|-----------|---------|
| `im` | IronMan | `im{VV}{NN}.pdf` — volume + issue | `im1801.pdf` = Vol 18, Issue 1 |
| `sh` | Strength & Health | `sh{YY}{MM}.pdf` — year + month | `sh6001.pdf` = 1960 January |

More magazines may be added; verify the naming convention per magazine when first encountered.

**Always derive year and month from the magazine cover (page 1), not the filename.**
For combined-month issues (e.g., "June-July"), use the month stated on the cover.

## .dat Format

Tab-delimited, 10 columns (col 9 filled by Phase 2; col 10 pre-existing from source data):
```
Magazine Name  Year  Month  Volume  Issue  Article Title  Author(s)  Mag Page  [PDF Pages]  [Text Flag]
     1          2      3      4       5           6           7          8           9            10
```
- Month may be negative when indeterminate (e.g., `-8` = "8th issue that year, month unknown")
- **Col 8** = printed magazine page number where the article starts (from the TOC)
- **Col 9** = PDF page range — the PDF pages that contain the article. Format: `"6"` (single page) or `"23-25,34-35,50"` (multi-page with gaps). Numbers are PDF page numbers, which usually equal the printed page numbers.
- **Col 10** = text file flag: `1` means a full article text file exists on the website (`mm_articles`); empty otherwise
- The `Table of Contents` row gets col 9 from Phase 1 (the PDF page where the TOC was found); all other rows get col 9 from Phase 2
- **Note:** the monolithic `.dat` files (source of truth) have only 9 columns — col 9 holds the text flag and col 10 (PDF range) is absent until Phase 2 runs. The per-issue split files always have 10 columns with col 9 empty and col 10 holding the flag.

## OCR Quality Warning

These PDFs are scanned magazines with varying text-layer quality:
- **Some issues**: clean, readable text → good extraction results
- **Many older issues**: OCR artifacts (split words, merged words, characters stored at scattered y-positions) → titles will be garbled and need manual cleanup
- **Script behavior when OCR is poor**: uses y-position word clustering to reconstruct lines; still extracts entries and page numbers, but both may contain errors
- **Page number errors under poor OCR**: entries flagged as "new" may actually exist in the .dat under a different page — verify before appending to the real file

> **Python scripting rule:** Never use `python3 -c` or heredocs. Copy scripts from the skill's `python/` directory to `/tmp/`, then run from there.

---

## Status Report

`TOC_STATUS.html` summarizes the status of every known issue across all magazines. Regenerate it any time after making changes:

```bash
cp {skill_dir}/python/generate_status.py /tmp/generate_status.py
python3 /tmp/generate_status.py
```

The script fetches live data from the API (`own`, API-side TOC) and combines it with the local per-issue `.dat` files (local TOC, col 9 ranges, col 10 text flag) and the PDF filesystem. Output is written to `~/workspace/musmem/toc/TOC_STATUS.html`.

---

## Splitting the Monolithic .dat

The monolithic `{mag}.dat` files are the source of truth. The per-issue files under `{mag}/` are derived from them and must be regenerated whenever the monolithic changes.

```bash
cp {skill_dir}/python/split_dat.py /tmp/split_dat.py
python3 /tmp/split_dat.py {mag}   # one magazine
python3 /tmp/split_dat.py all     # all magazines
```

The split script:
- Inserts an empty col 9 (PDF range slot) at index 8
- Moves the text-file flag from index 8 to index 9 (col 10)
- Creates `~/workspace/musmem/toc/{mag}/` if needed and writes one file per issue

**Typical workflow:**
- After Phase 1 or Phase 2 updates the monolithic file → re-run `split_dat.py` to sync per-issue files
- After editing per-issue files directly → re-run `merge_dat.py` to sync back to the monolithic
- After either → re-run `generate_status.py` to refresh the HTML

```bash
cp {skill_dir}/python/merge_dat.py /tmp/merge_dat.py
python3 /tmp/merge_dat.py {mag}   # one magazine
python3 /tmp/merge_dat.py all     # all magazines
```

Rows are sorted by year → month → volume → issue → magazine page (numeric where possible; non-numeric pages like `sup-1` sort before page 1).

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
   Optional arguments (positional, in order):
   - `article_title` — trace only the article whose title contains this string (case-insensitive)
   - `min_words` — word-count threshold for ad detection (default: 0 = disabled); see below

2. Script pre-scans all PDF pages for two kinds of continuation markers:
   - **"Continued ON page X"** (forward): article section ends here, resumes at X
   - **"Continued FROM page Y"** (backward): this page is a continuation of Y — catches articles where the outgoing marker on Y was garbled by OCR
   - Pre-scan uses two-pass detection for maximum OCR tolerance:
     - **Pass 1 (spaced):** word-clustered text, regex `cont[ei][a-z]+` — handles "Continucd", "Conteinued" (i/e transposition), etc.
     - **Pass 2 (compact):** each line collapsed to remove spaces, compact regex — catches character-scattered OCR where markers appear as individual letter tokens, e.g. `( C o n t in u e d f r o m p a g e 2 7 )` → detected as "from 27"
   - Pre-scan summary is printed; use it to verify expected markers were found
   - When `min_words` > 0, pre-scan also lists all pages below that word count

3. For each article, builds the page range:
   - **Main body**: walks consecutive pages from col 8, stopping when a "Continued ON" marker is found (destination queued) or the next article's start page is reached
   - **Jump destinations**: walks consecutive pages from the target with tighter stop conditions (not applied to the first page of the segment):
     - Stops before a page whose "from" references all point to *other* articles
     - Stops before an empty-reference page that immediately follows a non-start page that explicitly references this article (end-of-continuation signal)
     - If `min_words` > 0: also stops before a page whose word count is below the threshold (treats it as a full-page ad)
   - A page shared between two articles (e.g., two articles in different columns) will appear in both ranges — correct behavior
   - Skips `Table of Contents` rows (already have col 9 from Phase 1)
   - Skips rows that already have col 9

4. Review output — watch for:
   - **Continuation jumps**: non-consecutive ranges like `20-21,43` — verify the jump page is plausible
   - **Jump range runs too long**: continuation walk has no marker to stop it; check the pre-scan — if no "Continued ON" marker was found for this article, the jump section walked to the next article start or word-count threshold
   - **Jump range cut short**: expected continuation page missing from range — the FROM/ON marker for that page wasn't detected; correct col 9 manually
   - **Skipped entries**: page out of PDF range (bad data in col 8)
   - **Pre-existing col 9 with bad value**: entries that already have col 9 are skipped even if wrong — fix manually first

5. If output looks good, run against the real .dat file

### Ad Detection: `min_words` Option

When articles jump to a continuation section and OCR fails to detect "Continued ON" markers, the walk can run into full-page ads. Use `min_words` to stop early:

```bash
python3 /tmp/trace_ranges.py {pdf} /tmp/{mag}_test.dat {mag_name} {year} {month} "" 700
```

**How it works:** Applied only to continuation jump segments (not the main article section, which is bounded by the next article's start page). When a page inside a jump segment has fewer words than the threshold, the walk stops — treating that page as an ad.

**Choosing a threshold:**
1. Run without `min_words` first; note the "Low word-count pages" list from pre-scan
2. Look at the page numbers — do they align with known ad pages?
3. If a problem article's jump walks into an ad, set `min_words` just above that ad's word count
4. Verify the result doesn't cut off legitimate article content

**Caution:** Photo-heavy article pages can have low word counts. In older magazines, legitimate article pages often fall in the 400–700 word range. Always check the pre-scan low-word-count list and confirm that the pages flagged are actually ads before committing to a threshold. A threshold of 700 may cut off article pages in photo-heavy issues; start lower (e.g., 400–500) if unsure.

### Known Limitation: Undetected Markers
The two-pass prescan recovers many markers that `extract_text()` alone misses. However, some markers remain undetectable:
- **Complete character fragmentation at wrong y-positions**: if individual characters are scattered across different y-buckets, word clustering cannot reconstruct the phrase
- **Marker present but no forward link**: if an article continues to page X but neither "Continued ON X" (on the outgoing page) nor "Continued FROM [source]" (on page X) appears in any readable form, the connection is lost
- **Shared continuation pages**: if two articles share a continuation page (e.g., side-by-side columns), only the article with a detected FROM marker gets that page

When a continuation is missing: the pre-scan summary lists all markers found — if an expected one isn't there, OCR is too fragmented. Correct col 9 manually in that case.

---

## Magazine Code → Name Mapping

| Code | Name | Notes |
|------|------|-------|
| `im` | `IronMan` | |
| `sh` | `Strength & Health` | |
| `mb` | `Muscle Builder` | |
| `md` | `Muscular Development` | |
| `mp` | `Muscle Power` | |
| `mp2` | `Muscle Power` | Issues where the publisher reused volume+issue numbers; stored separately to avoid key collisions |
| `yp` | `Your Physique` | |
| `ma` | `Mr America` | |
| `ma2` | `Mr America` | Issues where the publisher reused volume+issue numbers; stored separately to avoid key collisions |
| `mti` | `Muscle Training Illustrated` | |
| `jma` | `Junior Mr America` | |
| `mmi` | `Muscle Mag International` | |
| `mma` | `Muscle Mag Annual` | |
| `mtis` | `Muscle Training Illustrated Special` | |
| `rpj` | `Reg Park Journal` | |

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Running against real .dat without testing | Always test on `/tmp/{mag}_test.dat` first |
| Using filename to determine year/month | Look at the cover page; IronMan filenames encode volume+issue (not year+month), so `im1801.pdf` = Vol 18 Issue 1, year 1958 |
| Assuming combined-month issues use the first month | Use whatever month the cover shows |
| Expecting clean titles from old scanned PDFs | OCR artifacts are normal; review title notes and clean up manually |
| Blindly appending "new" entries when OCR is poor | Poor OCR can misread page numbers; verify "new" entries against the .dat before running on the real file |
| Using `python3 -c` or heredoc | Copy script to `/tmp/`, run `python3 /tmp/script.py` |
| Processing multiple issues in parallel | One issue at a time |
| Running Phase 2 when col 9 already has a bad value | Phase 2 skips rows that already have col 9 — fix bad values manually first |
| Missing continuation jumps in Phase 2 output | Check the pre-scan summary — if the marker isn't listed, OCR is too poor to read it; correct col 9 manually |
| Jump section runs into ads (no marker to stop) | Use `min_words` (e.g., 700) — check pre-scan word-count list first to find the right threshold |
| `min_words` cutting off article pages | Threshold too high — article photo pages can be low-word; reduce threshold or don't use it |
