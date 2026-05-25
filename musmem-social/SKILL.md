---
name: musmem-social
description: Use when looking up social media handles for bodybuilding athletes from .dat files, verifying them, or merging prelim into approved files.
---

# MuscleMemory Social Media Lookup

Five-phase pipeline for finding and vetting social media handles for bodybuilding athletes.

## Quick Reference

Read paths from `~/workspace/skills/musmemSkills/config/paths.json`:
- `social_media` — folder for all JSON output files
- `working_data` — folder for state/progress files

**Platform abbreviations:**

| Platform | Key |
|----------|-----|
| instagram | `ig` |
| facebook | `fb` |
| twitter | `tw` |

**Output files:**

```
{social_media}/
  approved-{letter}-{gender}.json     ← vetted handles
  prelim-{letter}-{gender}.json       ← found this session, awaiting review
  completed/
    prelim-{letter}-{gender}-{YYYYMMDD-HHMMSS}.json  ← merged prelim files
{working_data}/
  athlete-list-{platform}-{gender}.txt   ← Phase 1 output (persists across sessions)
  progress-{platform}-{gender}.json      ← Phase 2 resume state
  searched-{platform}-{gender}.txt       ← every athlete searched (found or not)
```

**Scripts (in `musmem-social/`):**

| Script | Phase | Usage |
|--------|-------|-------|
| `open_tabs.sh` | 3 | `open_tabs.sh LETTER GENDER PLATFORM [--dry-run]` |
| `python/merge_prelim.py` | 4 | `python3 merge_prelim.py LETTER GENDER` |
| `python/find_conflicts.py` | 5 | `python3 find_conflicts.py [--platform PLATFORM]` |
| `python/sort_approved.py` | utility | `python3 sort_approved.py` — sorts all approved JSON files by name in place |

---

## Data Format

All JSON files are arrays of records, one object per line:

```json
[
    { "name": "Last, First", "ig": "handle" },
    { "name": "Banya, Parnelli", "fb": "patbanya1", "ig": "patbanya", "tw": "patbanya" }
]
```

| Field | Notes |
|-------|-------|
| `name` | `Last, First` coded form as in dat file |
| `ig` / `fb` / `tw` | Handle only — no `@`, no URL |

Omit platform keys that are not known. Never store `null`.

---

## Name Normalization

Used for comparisons and search queries — not for storing names.

```python
import re

def strip_codes(name):
    s = re.sub(r'\s*\(\d+\)', '', name)        # remove (1), (2) disambiguators
    s = re.sub(r"[^a-zA-Z,\s\-]", " ", s)      # keep only letters, comma, hyphens, spaces
    s = re.sub(r'\s+', ' ', s).strip()
    return s.lower()
```

Store names in the **coded form as-is from the dat file** (e.g., `Rodri'guez, Pablo`). Use normalized form only for deduplication, comparisons, and web search queries.

---

## Dat file format

Semicolon-delimited, 5 columns:

```
Last, First; Year; Contest Name; Division; !country
```

---

## Phase 1 — Build athlete list

### Input

- One or more `.dat` files (relative to `~/workspace/musmem/data/`, e.g. `prelim/covid-male.dat`)
- Gender: `male` | `female`
- Platform: `instagram` | `twitter` | `facebook`
- Optional filters (any combination):
  - `--min-year YYYY` — only athletes with at least one record in that year or later (column 2)
  - `--max-year YYYY` — only athletes with at least one record in that year or earlier (column 2)
  - `--contest SUBSTRING` — only rows where column 3 contains this substring (case-insensitive)
  - `--keyword SUBSTRING` — only rows containing this substring anywhere in the record (case-insensitive)

### Process

Write a Python script to `/tmp/build_athlete_list.py` and run it:

1. Read all specified dat files (semicolon-delimited; strip whitespace around fields)
2. For each row, apply all specified filters
3. Extract column 1 (coded name)
4. Deduplicate by `strip_codes()` key — on collision keep the first occurrence's coded form
5. Sort by `strip_codes()` key (so `č` sorts with `c`, not after `z`)
6. Write to `{working_data}/athlete-list-{platform}-{gender}.txt`, one name per line

### Report

Print: total distinct athletes, filters applied, and first 5 / last 5 names.

**Stop after Phase 1. Do not proceed to Phase 2 without explicit instruction.**

---

## Phase 2 — Search for social media

### Session start protocol

**Always do this before any searching — do not skip.**

1. Read `{working_data}/athlete-list-{platform}-{gender}.txt` → full list of names
2. Read `{working_data}/progress-{platform}-{gender}.json` if it exists → `last_name_processed`
3. Read `{working_data}/searched-{platform}-{gender}.txt` if it exists → build set of normalized names already searched
4. Determine start point:
   - Progress file exists → find `last_name_processed` in the sorted list; start from the **next** name (forward only — never go back to fill gaps)
   - No progress file → start from beginning
5. Report: `"Resuming from [name]. [N] already searched. Next: [first unsearched name]."`

### For each athlete

**Step 1 — Check existing handles**

- `letter` = first letter of athlete's last name (by `strip_codes`), lowercased
- Load `{social_media}/approved-{letter}-{gender}.json` if it exists
- Load `{social_media}/prelim-{letter}-{gender}.json` if it exists
- Compare by normalized name; if either file contains the platform key for this athlete → **skip** (already known)

**Step 2 — Search**

If not already known:
- Normalize name, convert to First Last order: `Rodri'guez, Pablo` → `Pablo Rodriguez`
- Query: `IFBB bodybuilder {First Last} {platform_name}` (use "instagram", not "ig")
- Accept if the result clearly belongs to this athlete: bio/posts reference bodybuilding/IFBB/NPC, name matches, no ambiguity
- Do not add if: no page found, identity unclear, or multiple plausible accounts

**Step 3 — Write to prelim**

If found: load `{social_media}/prelim-{letter}-{gender}.json` (empty list if not exists), append the new record, write back using this helper:

```python
def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        f.write("[\n")
        for i, rec in enumerate(data):
            comma = "," if i < len(data) - 1 else ""
            f.write(f"    {json.dumps(rec, ensure_ascii=False)}{comma}\n")
        f.write("]\n")
```

**Step 4 — Update state**

After every athlete (found, not found, or skipped): append coded name to `{working_data}/searched-{platform}-{gender}.txt`.

After every ~10 searches: update `{working_data}/progress-{platform}-{gender}.json`:

```json
{
  "platform": "ig",
  "gender": "male",
  "last_name_processed": "Czyz, Jan",
  "total_athletes": 8459,
  "searched_this_run": 2341,
  "last_updated": "2026-05-23"
}
```

### Report (end of session)

| Category | What to show |
|----------|-------------|
| Already known | Count only |
| Found | `Last, First → @handle` |
| Searched, not found | Names only |

**Stop after Phase 2. Do not proceed to Phase 3 without explicit instruction.**

---

## Phase 3 — Verify handles

The user runs `open_tabs.sh` manually to open prelim handles in the browser for review.

```
musmem-social/open_tabs.sh LETTER GENDER PLATFORM [--dry-run]
```

Reads `{social_media}/prelim-{letter}-{gender}.json`, opens each handle for the given platform in Google Chrome (pauses every 50, sleeps 1 s between each).

After reviewing in the browser, the user removes false positives from the prelim file manually.

---

## Phase 4 — Merge prelim into approved

The user runs `merge_prelim.py` manually.

```
python3 musmem-social/python/merge_prelim.py LETTER GENDER
```

For each record in prelim:
- Athlete not in approved → add to approved
- Athlete in approved, platform key absent → add the key
- Athlete in approved, platform key **conflicts** → print both values, prompt user to choose

After merging: writes updated approved file, moves prelim to:
`{social_media}/completed/prelim-{letter}-{gender}-{YYYYMMDD-HHMMSS}.json`

---

## Phase 5 — Find conflicts

The user runs `find_conflicts.py` manually.

```
python3 musmem-social/python/find_conflicts.py [--platform PLATFORM]
```

Reads all `approved-{letter}-{gender}.json` files. Reports any handle value that appears under more than one athlete name for the same platform.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Storing `"ig": null` | Omit the key entirely |
| Searching "Last, First" on the web | Normalize to First Last before querying |
| Going back to fill alphabetical gaps | Resume forward from `last_name_processed` only |
| Auto-advancing to the next phase | Stop after each phase and wait for explicit instruction |
| Adding date suffix to active prelim files | Only files moved to `completed/` get a timestamp suffix |
| Hardcoding social-media path | Always read `social_media` from `config/paths.json` |
| Re-searching a name already in the searched log | Normalize both sides with `strip_codes()` before comparing |
