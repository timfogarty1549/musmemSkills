---
name: musmem-social
description: Use when looking up or validating social media handles for bodybuilding athletes in a given contest and year, to populate the social-media folder.
---

# MuscleMemory Social Media Lookup

Fetches athletes from a contest, checks the social-media folder for existing entries, and searches the web to find missing handles for the specified platform.

## Quick Reference

| Config | Key |
|--------|-----|
| `config/paths.json` | `social_media` — path to the social-media **folder** |
| `config/apis.json` | `endpoints.contest_event`, `musclememory_net`, `user_agent_api` |

**Platform abbreviations:**

| Platform | Key |
|----------|-----|
| instagram | `ig` |
| facebook | `fb` |
| twitter | `tw` |

## Input

- Contest name + year — e.g., `"Olympia - IFBB, 2020"`
- Platform — e.g., `instagram`
- Optional flag: `--validate` — validate existing handles instead of (or in addition to) finding new ones

---

## Data Format

The social-media folder contains multiple JSON files. Each file name ends in `-male.json` or `-female.json`. Each file is a JSON array of records:

```json
[
  { "name": "Last, First", "ig": "handle" },
  { "name": "Banya, Parnelli", "fb": "patbanya1", "ig": "patbanya", "tw": "patbanya" }
]
```

| Field | Notes |
|-------|-------|
| `name` | `Last, First` format — matches `completeName` from API |
| `ig` | Instagram handle, no `@`, no URL |
| `fb` | Facebook handle |
| `tw` | Twitter/X handle |

Omit platform keys that are not known — do not store `null`.

---

## Mode 1: Lookup (default)

### Step 1 — Fetch contest athletes

```
GET {musclememory_net}{endpoints.contest_event}
→ /api/contest?name={contest}&year={year}
User-Agent: {user_agent_api}
```

Response: `data.results[]` — each entry has `completeName` (`Last, First`) and `gender` (`"male"` or `"female"`).

**Deduplicate** by `completeName` before proceeding.

### Step 2 — Load existing social media data

Path: `config/paths.json` → `social_media` (a folder)

1. List all `*-male.json` and `*-female.json` files in the folder, sorted alphabetically.
2. For each file, parse as a JSON array and merge records into an in-memory map keyed by `name`, split by gender (inferred from filename suffix).
3. On conflict (same name and same platform key in two files): last file wins (alphabetical order).

For each contest athlete, check `mergedMap[gender][completeName][platform_key]`. If the key exists → **skip** (even without `--validate`).

### Step 3 — Search for handle

For each athlete missing the platform key, search the web:

**Query:** `"{displayName}" bodybuilder instagram` (or relevant platform name; use First Last order)

A result is sufficient if it returns an Instagram page clearly belonging to this athlete. Signs it's the right person:
- Bio or posts reference bodybuilding / competing / IFBB / NPC
- Name matches (allowing for common abbreviations or nicknames)
- Contest history aligns with what's in MuscleMemory

**Do not add if:**
- No Instagram page found in results
- Page found but identity is unclear (generic name, no bodybuilding content)
- Multiple plausible accounts with no clear match

Extract the handle from the URL or page (`instagram.com/{handle}`) — store without `@`.

### Step 4 — Write results

Write newly found handles to a **new file** in the social-media folder. Name it after the contest and year:

```
{social_media}/{contest-slug}-{year}-{gender}.json
```

Example: `~/workspace/musmem/data/social-media/2020-olympia-male.json`

The file contains only the handles found in this session as a JSON array. Do not append to existing files.

```python
with open(path, 'w', encoding='utf-8') as f:
    json.dump(records, f, ensure_ascii=False, indent=2)
```

### Step 5 — Report

| Category | What to show |
|----------|-------------|
| Already in file | Count only |
| Added | `Last, First → @handle` |
| Searched, not found | Names only |

---

## Mode 2: Validate (`--validate`)

Checks existing handles for the specified platform. Can be run alone or after a lookup pass.

### Step 1 — Collect handles to validate

Load and merge all files in the folder (as in Step 2 above). Gather all athletes in the merged male and female maps who have the platform key — regardless of which contest was specified. (Validation is global, not contest-scoped.)

### Step 2 — Check each handle

For each handle, fetch the platform profile page and check two things:

**Existence:** Does the account still exist?
- Account not found / page 404 / "user not found" → flag as **dead**

**Identity:** Does the account still belong to this athlete?
- Bio or recent posts reference bodybuilding / competing / their name
- If account exists but shows no bodybuilding content or a different identity → flag as **suspect**

### Step 3 — Report and prompt

Do not automatically remove or modify any entries. Present findings to the user:

```
Dead handles (account gone):
  Doe, John — ig: johndoe_bb

Suspect handles (identity unclear):
  Smith, Jane — ig: janesmith — bio: "🌸 lifestyle blogger"

Ask: Remove dead handles? Review suspects individually?
```

Only modify files after explicit user confirmation. Write corrections to a new file named after the session (e.g., `corrections-YYYY-MM-DD-{gender}.json`) rather than editing existing files.

---

## Mode 3: Dat-file Sweep

Searches for social media handles for all distinct athletes in a `.dat` file, working alphabetically across multiple sessions.

### Input

- Path to `.dat` file relative to `~/workspace/musmem/data/` — e.g., `prelim/covid-male.dat` or `bb_male.dat`
- Platform
- Gender
- Optional `--min-year` — filter to athletes with at least one result in that year or later

### State files

Two global files in `~/workspace/musmem/working_data/` persist across all sessions and all dat files:

| File | Purpose |
|------|---------|
| `progress-{platform}-{gender}.json` | Current dat file + last name processed — enables instant resume |
| `searched-{platform}-{gender}.txt` | Every athlete ever searched (found or not) — prevents re-searching deleted false matches |

Names in both files use the **coded form exactly as they appear in the dat file** (e.g., `Rodri'guez, Pablo`). See `docs/special-chars-reference.md` for the coding system. Comparisons strip codes to plain ASCII on both sides so `Rodri'guez` matches `Rodriguez` across different dat files.

### Session start protocol

**Do this before any other work — takes seconds, replaces all transcript archaeology.**

1. Read `working_data/progress-{platform}-{gender}.json` if it exists
2. Read `working_data/searched-{platform}-{gender}.txt` if it exists → build set of already-searched names (compare by plain-ASCII-stripped keys)
3. Determine start point:
   - Same dat file as in progress → in the alphabetically-sorted full name list, find `last_name_processed` and start from the name immediately after it. Do **not** go back to fill gaps for names that appear earlier alphabetically but were never searched.
   - Different dat file (or no progress file) → start from beginning of new dat file
4. Report: `"Resuming from [last_name_processed]. [N] names already searched globally. Next: [first unsearched name]."`

### Name extraction

1. Read column 1 (`Last, First`) from every row of the dat file (semicolon-delimited)
2. Deduplicate
3. If `--min-year` given, keep only names that appear with that year or later in the dat file
4. Sort by plain-ASCII-stripped form (so `č` sorts with `c`, not after `z`)
5. Remove names whose plain-ASCII-stripped form is already in the searched log

### Name normalization

Before any comparison, search query, or logging, normalize athlete names using this function:

```python
def strip_codes(name):
    s = re.sub(r'\s*\(\d+\)', '', name)          # remove (1), (2) disambiguators
    s = re.sub(r"[^a-zA-Z,\s\-]", " ", s)         # keep only letters, comma, hyphens, spaces
    s = re.sub(r'\s+', ' ', s).strip()
    return s.lower()
```

Examples:
- `Rodri'guez, Pablo` → `rodriguez, pablo`
- `Min~ana Iban~ez, Ferran` → `minana ibanez, ferran`
- `Smith (2), John` → `smith, john`
- `O'Brien, Sean` → `obrien, sean`

Use normalized form for:
- Deduplication and comparisons against the searched log
- Building web search queries (convert to First Last after normalizing)

Store names in the **coded form as-is from the dat file** in the searched log and output files — normalization is only for comparisons and queries, not for stored values.

### Search loop

For each remaining name in sorted order:

**Web search query:** Normalize to plain ASCII, convert to First Last order.
`Rodri'guez, Pablo` → `Pablo Rodriguez bodybuilder instagram`

Do **not** use Unicode or the coded form for queries — plain ASCII maximises recall.

Accept a result using the same confidence criteria as Mode 1 Step 3.

**After each name searched (found or not):**
- Append the name in coded form (as-is from dat file) to `searched-{platform}-{gender}.txt`

**After each batch of ~10 searches:**
- Update `progress-{platform}-{gender}.json`:

```json
{
  "platform": "ig",
  "gender": "male",
  "current_dat_file": "prelim/covid-male.dat",
  "last_name_processed": "Czyz, Jan",
  "total_in_current_dat": 8459,
  "searched_in_current_dat": 2341,
  "last_updated": "2026-05-13"
}
```

### Output files

Write found handles to `~/workspace/musmem/data/social-media/`, one file per letter:

```
{dat-basename}-{letter}-section-{gender}.json
```

Example: `covid-male-d-section-male.json`

**If the file already exists, append to it** (load existing records, add new ones, write back). Do not create a dated variant or a separate file. Never add a date suffix to the filename.

Standard JSON array format — same schema as all other social-media files. `name` field uses coded form as-is from the dat file.

---

## File Format Rules

- JSON array, UTF-8
- Keys: `name` in `Last, First` format (matches `completeName` from API)
- Handle values: username only, no `@` prefix, no full URL
- Omit platform key entirely if not found — do not store `null`
- One file per session/batch — do not append to existing files

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Adding `"ig": null` for not-found athletes | Omit the key entirely |
| Creating a new dated file (`-2026-05-16.json`) instead of appending | In Mode 3, append to the existing letter file; never add a date suffix |
| Going back to fill A–M gaps instead of resuming forward | Session start means finding `last_name_processed` in the sorted list and starting from the next name — forward only |
| Overwriting existing platform keys during lookup (Mode 1) | New file only contains newly found handles — merging happens at read time |
| Storing full URL instead of handle | Extract handle only: `instagram.com/{handle}` → store `{handle}` |
| Searching `Last, First` on the web | Use `displayName` (First Last) for web searches |
| Auto-removing dead/suspect handles | Always report and confirm with user before modifying |
| Validating only contest athletes | Validation is global — check all entries across all files, not just the specified contest |
| Reading only one file | Always load and merge ALL files in the folder before checking for existing entries |
