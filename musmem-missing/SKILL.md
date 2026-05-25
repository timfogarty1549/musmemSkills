---
name: musmem-missing
description: Use when identifying IFBB pro contests missing from the MuscleMemory HTML tracker by comparing against npcnewsonline.com, or when updating the tracker with red-M missing markers and P* Men's Physique opportunity flags.
---

# musmem-missing

Identifies IFBB pro contests missing from the MuscleMemory HTML tracker by comparing against npcnewsonline.com, then updates the tracker with red-M missing markers and P* Men's Physique opportunity flags.

## Quick Reference

| Phase | What Claude does | Reads from | Writes to |
|-------|------------------|------------|-----------|
| 1 — Gap Analysis | Scrape npcnewsonline IFBB listing pages → compare to HTML tracker → save slug map | npcnewsonline, HTML tracker, `docs/contest-name-mapping.md` | `data/npcnol_slugs.json` |
| 2 — Mapping Review | User reviews gap list; updates `docs/contest-name-mapping.md`; Claude re-runs Phase 1 if needed | — | `docs/contest-name-mapping.md` |
| 3 — HTML Updates | Add missing contest rows + mark red M cells for known missing data | `data/npcnol_slugs.json`, HTML tracker | HTML tracker |
| 4 — Men's Physique Audit | Check existing data rows lacking P → fetch npcnewsonline page → add P* if found | `data/npcnol_slugs.json`, HTML tracker | HTML tracker, `.page_cache/` |

**Do not auto-advance phases.** Complete the requested phase, report, and stop.

---

## Key Files

| File | Role |
|------|------|
| `~/workspace/musmem/working-docs/ifbb-pro-contests-years-since-2012.html` | Source of truth for collected data; target of all HTML edits |
| `~/workspace/skills/musmemSkills/docs/contest-name-mapping.md` | npcnewsonline → MuscleMemory name overrides (edit in Phase 2) |
| `data/npcnol_slugs.json` | Slug map: `{year: [{normalized, raw, slug, href}, ...]}` — written by Phase 1, read by Phase 4 |
| `scripts/gap_analysis.py` | Phase 1 script |
| `~/workspace/musmem/.page_cache/` | Individual contest page cache (shared with musmem-contests skill) |

---

## HTML Tracker Structure

Each data row:
```html
<tr>
  <td class="contest">Contest Name - IFBB</td>
  <td class="">          <!-- empty year cell (2012) -->
  <td class="mark">B, C, P, F</td>  <!-- year with data -->
  ...15 year columns total...
</tr>
```

Year columns: index 1 = 2012, index 2 = 2013, … index 15 = 2026.

Division codes used in cells: **B** (Bodybuilding), **U** (Under 212/208), **C** (Classic Physique), **Cw** (Women's Classic), **P** (Men's Physique), **Pw** (Women's Physique), **F** (Figure), **O** (Other)

### CSS classes to add (if not already present)

```css
.missing { background: #fff0f0; color: #cc0000; font-weight: bold; }
.potential { color: #1a7a1a; font-style: italic; }
```

### Notation

- **Red M** (`<td class="missing">M</td>`): npcnewsonline has results for that year but we have collected nothing
- **P\*** (`<span class="potential">P*</span>` appended to cell text): npcnewsonline had Men's Physique but it's not in our DB

---

## Phase 1 — Gap Analysis

**Trigger:** "Find missing contests" / "compare HTML tracker to npcnewsonline" / "run gap analysis"

**Script:** `python3 ~/workspace/skills/musmemSkills/musmem-missing/scripts/gap_analysis.py`

The script:
1. Parses the HTML tracker → extracts all contest names and year/division data
2. Loads `docs/contest-name-mapping.md` → builds override dict
3. For each year 2012–2026, fetches `https://contests.npcnewsonline.com/contests/{year}/ifbb` via curl with browser UA
4. Extracts contest links (href pattern `/contests/{year}/ifbb_`), strips "IFBB " prefix, appends " - IFBB", applies mapping
5. Filters out names containing "amateur" or "pro qualifier"
6. Compares normalized names against HTML tracker contest names (exact match)
7. Saves slug map to `data/npcnol_slugs.json`
8. Reports gap list (on npcnewsonline but not in HTML) and reverse list (in HTML but not on npcnewsonline)

**UA for curl:** `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36`

**Stop and report after Phase 1.** The gap list typically contains:
- **Bikini/Wellness/Figure-only contests** — ignore (names with "Bikini", "Wellness", "Figure", "GRL PWR", Korea Figure, etc.)
- **Division-specific shows** — Men's Physique-only or Classic-only: decide whether to include
- **Name mapping gaps** — contests in HTML under a slightly different name → add to `docs/contest-name-mapping.md`
- **Genuinely missing contests** — add as new rows in Phase 3

---

## Phase 2 — Mapping Review (user decision)

User reviews gap list and decides:
- Which names need new entries in `docs/contest-name-mapping.md`
- Which are genuinely new contests to add to the HTML tracker
- Which to ignore (Bikini/Wellness-only, Natural-only, Masters-only, etc.)

If `contest-name-mapping.md` is updated: re-run the gap_analysis.py script to regenerate the gap list with new mappings applied. The script re-fetches nothing (listing pages are not cached) but will use the updated mapping.

**Claude proceeds to Phase 3 only on explicit user instruction.**

---

## Phase 3 — HTML Updates

**Trigger:** User says "proceed to Phase 3" / "update the HTML"

Write `/tmp/update_html.py`:

1. Parse HTML tracker → get all contest rows and year cells
2. Add CSS `.missing` and `.potential` rules to `<style>` block if absent
3. Load `data/npcnol_slugs.json` → build `{(contest_name, year): True}` map of known npcnewsonline entries
4. **New rows:** For each distinct name in the slug map not in HTML tracker → insert `<tr>` alphabetically; mark each year this contest appeared with `<td class="missing">M</td>`
5. **Existing empty cells:** For each existing row, for each empty year cell where npcnewsonline has that contest → change to `<td class="missing">M</td>`
6. Write updated HTML

Report: N new rows added, M red-M cells marked.

**Stop and wait for user instruction before Phase 4.**

---

## Phase 4 — Men's Physique Audit

**Trigger:** User says "proceed to Phase 4" / "check Men's Physique"

Write `/tmp/ph_audit.py`:

1. Parse updated HTML tracker → find all `class="mark"` cells where text does NOT contain `P`
2. Cross-reference with `data/npcnol_slugs.json` → only check contest+year combos that have a known slug
3. For each candidate:
   - Cache path: `~/workspace/musmem/.page_cache/{year}_{slug}.html`
   - If cached: read from disk
   - If not cached: fetch via curl with browser UA → save to cache
   - Parse HTML for Men's Physique division (look for PH-related `data-slug` or "Men's Physique" in division headers, excluding Women's Physique)
4. For confirmed Men's Physique present: append `, <span class="potential">P*</span>` to the cell's content
5. Write updated HTML

Report: list of contest+year where P* added; pages newly cached vs. already cached.

**Stop and report.**

---

## Running Scripts

All scripts follow the project rule: write to `/tmp/script.py`, run with `python3 /tmp/script.py`. The scripts in `scripts/` are source-controlled originals — copy to `/tmp/` before running if modifications are needed, or run directly:

```bash
python3 ~/workspace/skills/musmemSkills/musmem-missing/scripts/gap_analysis.py
```

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Fetching listing pages without `--compressed` | npcnewsonline serves gzip — always use `curl -s --compressed` |
| Running gap analysis without checking if `data/npcnol_slugs.json` is fresh | If mapping.md changed, re-run Phase 1 to regenerate slug map |
| Adding Bikini/Wellness-only contests to HTML tracker | Filter by name: skip anything with "Bikini", "Wellness" in title unless user explicitly says to include |
| Missing the double-space in some npcnewsonline names | e.g., "Colombia  Pro" has two spaces — normalize to one space before matching |
