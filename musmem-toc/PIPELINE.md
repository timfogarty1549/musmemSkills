# Magazine Scanning & Article Serving Pipeline

## Goal

Scan ~2000 bodybuilding magazines, upload PDFs to S3, extract table-of-contents data, and serve per-article sub-PDFs on demand via musclememory.org.

---

## Hardware

- **CZUR scanner** — overhead book scanner; non-destructive; good for bound/fragile issues
- **HP LaserJet MFP 3101sdw** — flatbed/ADF; faster for bulk scanning if destructive cutting is acceptable
- **Hybrid option** — scan individual JPEGs with the HP ADF, drop them into the CZUR software folder, let CZUR/ABBYY FineReader handle deskewing and OCR → searchable PDF

The Internet Archive PDF (sh3709) is lower resolution but looks cleaner than CZUR output — professional scanning workflow + calibrated optics matters more than raw resolution.

---

## Scanning Decision

| Option | Pro | Con |
|--------|-----|-----|
| CZUR overhead | Non-destructive | Slower; some geometric distortion |
| HP ADF (destructive) | Fast throughput | Destroys binding; irreplaceable issues gone |
| HP ADF → CZUR software | Fast scanning + ABBYY OCR | Must test quality; CZUR license may limit external files |

**Recommendation:** Test the HP → CZUR folder workflow on one full issue before committing. For rare issues, use CZUR overhead.

---

## Storage

- Master PDFs stored on S3: `s3://musmem/magPdfs/{mag}/{filename}.pdf`
- Filename convention derives from `getMagIssue()` in the musmem backend:
  - Year/month mags (`sh`, `mb`, `mma`, `mtis`, `rpj`): `{code}{YY}{MM}.pdf` → e.g. `sh8901.pdf`
  - Volume/issue mags: `{code}{VV}{II}.pdf` → e.g. `fl0201.pdf`
  - Issue-only mags (vol=0): `{code}{NNN}.pdf` → e.g. `mti001.pdf`

---

## TOC Data Pipeline

```
Phase 1: extract_toc.py
  PDF → dat col 8 (printed start page from TOC)

Phase 2: trace_ranges.py
  PDF + col 8 → dat col 9 (PDF page range, e.g. "24-26,42,45-48")

split_dat.py
  Monolithic {mag}.dat → per-issue {mag}/{filename}.dat

generate_status.py
  → TOC_STATUS.html (tracks coverage across all issues)
```

Article page ranges are **non-contiguous**: e.g. `"24-26,42,45-48"` means an article that starts on page 24, runs to 26, then jumps to pages 42 and 45–48 (intervening pages are ads).

---

## Article Serving Pipeline

```
User clicks article on musclememory.org
  ↓
musmem backend looks up article → {magazineFilename, pageRange}
  ↓
musmem-mag-parser POST /api/parse
  ↓
Fetch full PDF from S3
  ↓
Parse page range "24-26,42,45-48" → [24,25,26,42,45,46,47,48]
  ↓
Extract those pages using pdf-lib
  ↓
Return sub-PDF to client
```

The mag-parser is a separate Express/TypeScript service (`~/workspace/node/musmem-mag-parser`) that may be merged into the main musmem backend later.

---

## Gaps to Close

### 1. `TableOfContents` interface needs page range

Current (`~/workspace/node/musmem/src/interfaces/table-of-contents.ts`):
```typescript
export interface TableOfContents {
  title: string;
  page: number;       // col 8: printed start page
  author?: string[];
}
```

Needs:
```typescript
  pageRange?: string; // col 9: PDF page range e.g. "24-26,42,45-48"
```

### 2. `ArticleInfoService` needs real data

Current state: stub data in `~/workspace/node/musmem-mag-parser/src/ArticleInfo.ts`.

Needs to be wired to real article data from the musmem backend or shared dat files. The `magazineFilename` is derivable from the magazine `code` via `getMagIssue()`.

### 3. Page range parsing utility

The string `"24-26,42,45-48"` must be parsed into `number[]` when serving a request:

```typescript
function parsePageRange(range: string): number[] {
  return range.split(',').flatMap(segment => {
    const [start, end] = segment.trim().split('-').map(Number);
    if (end === undefined) return [start];
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  });
}
```

---

## Repositories

| Repo | Path | Purpose |
|------|------|---------|
| Main backend | `~/workspace/node/musmem` | API, data loading, TOC search |
| Magazine parser | `~/workspace/node/musmem-mag-parser` | S3 fetch + page extraction |
| Frontend | `~/workspace/angular/musmem-ui` | Angular UI |
| Skills | `~/workspace/skills/musmemSkills` | TOC extraction scripts |
| S3 mirror | `~/workspace/s3/musmem/magPdfs/` | Local PDF copies |
