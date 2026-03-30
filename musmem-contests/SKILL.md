---
name: musmem-contests
description: Use when checking bodybuilding contest websites for new results not yet in the MuscleMemory database, or when generating flat files of contest results for import into musclememory.net.
---

# MuscleMemory Contest Checker

Checks bodybuilding org websites for contests missing from the MuscleMemory database and generates flat files for import via `format.php`.

## Quick Reference

| Phase | What Claude does | Reads from | Writes to |
|-------|------------------|------------|-----------|
| 1 — Discovery | Fetch DB + scrape org site → report missing contests | — | — |
| 2 — Results | Scrape individual contest pages → write flat file | — | `1-incoming/` |
| 2a — Normalize Contest Names | Rename files + `t` lines to canonical MuscleMemory titles | `1-incoming/` | `1-incoming/` (in-place) |
| 3 — Normalize Athletes | Normalize athlete names (Last, First / East Asian format) | `1-incoming/` | `2-normalize-athletes/` |
| 4 — Format | Run flat files through format.php → write `.out` files | `2-normalize-athletes/` | `3-formatted/` |
| 5 — Review | Interactively resolve `<<<<` flagged names in `.out` files | `3-formatted/` | `4-reviewed/` |
| 6 — Complete | Verify athlete names against master, write corrected `.out` | `4-reviewed/` | `5-completed/` |
| 7 — Append | Append files to gender staging `.dat` files | `5-completed/` | `6-appended/` |

**`0-later/`** — holding area for files that can't be processed yet (missing data, illegible scans, etc.)

**Files are never deleted or moved from a source folder.** Each step reads from N-1 and writes to N.

---

## Phase 1: Discovery

> **Python scripting rule:** Never use `python3 -c "..."` or `python3 - <<'PYEOF'` heredocs. Always write scripts to `/tmp/script.py` using the Write tool, then run `python3 /tmp/script.py`. This applies to all curl-piped processing and any other Python work in this phase.

### 1. Fetch the MuscleMemory DB for the target year(s)

```
GET https://musclememory.net/api/contests/{year}
```

Returns `data.contests` — an array of strings in `"Contest Name - ORG"` format.

If checking multiple years, call once per year.

**User-Agent for musclememory.net API calls:** The server blocks bot user agents and returns fake HTML. Use a browser UA:
```
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
```

### 2. Scrape listing pages

See `sources-reference.md` for each source's listing URLs, org slugs, User-Agent, and name normalization rules.

### 3. Normalize names to MuscleMemory format

Each source has its own normalization rule — see `sources-reference.md`. For npcnewsonline.com: strip the leading org prefix, append ` - {ORG}` (e.g., `IFBB Arnold Classic` → `Arnold Classic - IFBB`).

### 4. Compare and report

Find contest names (normalized) that appear on npcnewsonline.com but **not** in the DB for that year. Present as a numbered list grouped by org:

```
Missing from MuscleMemory (2025):

IFBB (3 missing):
  1. Arnold Classic Europe - IFBB
  2. Tampa Pro - IFBB
  3. Toronto Pro - IFBB

NPC (12 missing):
  ...
```

Ask the user: "Which contests should I fetch full results for?"

---

## Phase 2: Results

### 1. Fetch individual contest pages

See `sources-reference.md` for each source's individual contest URL pattern and User-Agent.

### 2. Extract results

Each page shows divisions with numbered placings. See `sources-reference.md` for source-specific notes (name order, country availability, etc.).

### 3. Write the flat file

Output format for `format.php` — one contest per file:

```
y 2025
t Arnold Classic - IFBB
c OP
1 Derek Lunsford
2 Samson Dauda
3 Andrew Jacked
----
c CL
1 Ramon Rocha Queiroz
2 Mike Sommerfeld
98 Some Athlete
98 Another Athlete
```

**Format rules:**
- `y {year}` — set year
- `t {Contest Name - ORG}` — set contest title (MuscleMemory format)
- `c {code}` — division code from `en.json` DIVISIONS (see `divisions-reference.md`)
- `----` — separator between divisions
- Competitor lines: `{placing} {First Last}` (no prefix character)
- Names are "First Last" order (npcnewsonline.com format) — do NOT set `l 1`
- Leave `l` flag unset (defaults to `l 0` = first-last order)

**Excluded divisions — skip entirely, do not write:**
- Bikini (all age groups)
- Wellness (all age groups)
- Fitness (all age groups)
- Novice (all categories)

**Did not place → placing 98:**
When the highest placing number repeats within a division (e.g., multiple athletes all listed as 16th), replace ALL of those tied entries with placing `98`.

```
# Example: 15 placed athletes, then many tied at 16 → all become 98
15 Rubiel Mosquera
98 Akim Williams
98 Brett Wilkin
98 Chenglong Shen
```

**Division codes** — full reference: `divisions-reference.md` in this skill's directory.

Division codes are universal — not specific to any org. All codes may appear across IFBB, NPC, CPA, and other orgs. When a division name is unfamiliar, read `divisions-reference.md` rather than inventing a code.

Source of truth for all codes: `~/workspace/angular/musmem-ui/src/assets/i18n/en.json` → `DIVISIONS`.

Common mappings for npcnewsonline.com:

| Division | Code | Division | Code |
|----------|------|----------|------|
| Bodybuilding Open | `OP` | Classic Physique Open | `CL` |
| Women's Bodybuilding Open | `BB` | Classic Masters 40+ | `c4` |
| Under 212 | `U212` | Classic Masters 45+ | `c45` |
| Under 208 | `U208` | Classic Masters 50+ | `c5` |
| Masters 40+ | `M4` | Classic Masters 55+ | `c55` |
| Masters 45+ | `45` | Classic Masters 60+ | `c6` |
| Masters 50+ | `M5` | Physique Open | `PH` |
| Masters 55+ | `55` | Masters Physique 40+ | `P4` |
| Masters 60+ | `M6` | Masters Physique 45+ | `P45` |
| Overall | `OV` | Masters Physique 50+ | `P5` |
| Teen | `TE` | Masters Physique 55+ | `P55` |
| Junior | `JR` | Masters Physique 60+ | `P6` |
| Wheelchair | `WC` | Figure Open | `FI` |
| | | Figure 40+ | `F4` |
| | | Figure 45+ | `f4` |
| | | Figure 50+ | `F5` |
| | | Figure 55+ | `f5` |
| | | Figure 60+ | `F6` |

**One file per contest.** Save each to `~/workspace/musmem/1-incoming/`.

**Male/female split:** When a contest has both male and female divisions, write two separate files — one per gender. Division codes are the same across genders; separate files prevent collisions (e.g., both Men's and Women's Physique use `Pa`–`Ph`).

- Male divisions: Bodybuilding weight classes, Men's Physique, Classic Physique
- Female divisions: Figure, Women's Bodybuilding, Women's Physique
- Excluded from both: Bikini, Wellness, Fitness, Fit Model

**Filename format:** `{year}_{contest_name}-{org}-{gender}.txt` where gender is `male` or `female`

- Always include the gender suffix — even if a contest is single-gender
- Use the contest name part only (no org in the name portion)
- Lowercase, spaces replaced with underscores, remove special characters

Examples:
| Contest | Filename |
|---------|----------|
| Arnold Classic - IFBB (2025, male) | `2025_arnold_classic-ifbb-male.txt` |
| Arnold Classic - IFBB (2025, female) | `2025_arnold_classic-ifbb-female.txt` |
| NPC Nationals 2025 (male) | `2025_national_championships-npc-male.txt` |
| NPC Nationals 2025 (female) | `2025_national_championships-npc-female.txt` |
| Cancun Naturals - NPC Worldwide (2025, male) | `2025_cancun_naturals-npc_worldwide-male.txt` |

**Create the directory if it doesn't exist:** `mkdir -p ~/workspace/musmem/1-incoming`

Report to the user: list of files written and total competitors captured per file.

---

## Phase 2a: Normalize Contest Names

Rename flat files in `1-incoming/` so that the filename and `t` line use the canonical MuscleMemory contest title. The mapping is defined in `contest-title-normalization-audit.md`.

### Run the script

```bash
# Normalize all files
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/normalize_contest_names.py --all

# Normalize specific files (with or without .txt)
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/normalize_contest_names.py 2022_arnold_amateur-ifbb-male.txt

# Glob pattern (quote to prevent shell expansion)
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/normalize_contest_names.py '*arnold*'
```

For each file that needs a title change, shows the current title, the canonical title, and the new filename. Prompts `[y]es / [n]o / [a]ll / [x]exit` before applying.

### What it changes

- The `t` line in the file is updated to the canonical title
- The filename is renamed to match (e.g. `2022_arnold_amateur-ifbb-male.txt` → `2022_arnold_amateur-npc_worldwide-male.txt`)
- Files already using the canonical title are skipped silently

The mapping is sourced from `contest-title-normalization-audit.md` — entries of the form `- YEAR - Source Title` under a `## Canonical Title` heading.

---

## Phase 3: Normalize Athletes

Normalize athlete names in flat files so that `format.php` can split them correctly.

### Run the script

```bash
# All files (writes sibling "-1" copies by default — review before using --src-root/--dst-root)
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/normalize_athlete_names.py \
  --src-root ~/workspace/musmem/1-incoming \
  --dst-root ~/workspace/musmem/2-normalize-athletes \
  ~/workspace/musmem/1-incoming/*.txt

# Specific files
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/normalize_athlete_names.py \
  --src-root ~/workspace/musmem/1-incoming \
  --dst-root ~/workspace/musmem/2-normalize-athletes \
  ~/workspace/musmem/1-incoming/2025_olympia-ifbb-male.txt
```

Input: `~/workspace/musmem/1-incoming/*.txt`
Output: `~/workspace/musmem/2-normalize-athletes/*.txt`

### What it does

- Western names: `1 First Last` → `n Last, First` (where `n` is the placing number)
- East Asian names: `1 Family Given` → `@n Family Given`
- Preserves all non-athlete lines (`y`, `t`, `c`, `----`) unchanged
- Already-normalized lines (e.g. `1 Last, First`) are preserved as-is

See `name-normalization-skill.md` for full rules on East Asian name detection and ambiguous cases.

---

## Phase 4: Format

Run the normalized flat files through `format.php` to produce import-ready `.out` files.

### Run the formatter

```bash
# Format all unprocessed files (no .out yet in 3-formatted/)
~/workspace/skills/musmemSkills/musmem-contests/php/run_format.sh

# Format a specific file (with or without .txt extension)
~/workspace/skills/musmemSkills/musmem-contests/php/run_format.sh 2025_olympia-ifbb-male

# Reprocess all files, overwriting existing .out files
~/workspace/skills/musmemSkills/musmem-contests/php/run_format.sh --force

# Reprocess a specific file, overwriting its .out
~/workspace/skills/musmemSkills/musmem-contests/php/run_format.sh --force 2025_olympia-ifbb-male
```

Input: `~/workspace/musmem/2-normalize-athletes/*.txt`
Output: `~/workspace/musmem/3-formatted/*.out`

### What format.php does

- Parses `y`, `t`, `c`, `l`, `----` control lines
- Converts competitor lines to: `Last, First; year; Contest Name - ORG; division-placing; c=XX;`
- Normalizes name casing (title case, handles O'/Mc/hyphen prefixes)
- Detects and converts country codes if present in source data (npcnewsonline.com has none)
- Flags 3+ word names with `<<<<` for manual review
- Warns on upper-case `C` (should be lowercase `c`)
- Transliterates common accented characters (ñ→n~, á→a, etc.)

### Output format (one line per competitor)

```
Lunsford, Derek; 2025; Olympia - IFBB; OP-1;
Dauda, Samson; 2025; Olympia - IFBB; OP-2;
```

### Review the output

Check stdout for:
- `<<<<` — 3+ word names that may be split incorrectly (Last vs First ambiguous)
- `===> POSSIBLE ERROR` — uppercase `C` used instead of `c`
- `******* ` — unrecognized country code

---

## Phase 5: Review Flagged Names

Interactively resolve all `<<<<` lines in `.out` files. Reads from `3-formatted/`, writes resolved files to `4-reviewed/`. Run the script via Claude (opens a Terminal window) or directly in your terminal.

### Run the script

Claude launches it with:
```bash
~/workspace/skills/musmemSkills/musmem-contests/python/review_flags.sh 2025_olympia-ifbb-male
~/workspace/skills/musmemSkills/musmem-contests/python/review_flags.sh   # all files with <<<< lines
```

Or run directly:
```bash
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/review_flags.py 2025_olympia-ifbb-male
```

### Keys (single keypress — no RETURN)

| Key | Action |
|-----|--------|
| `1` | Accept as-is |
| `2` | Re-split (alternative comma position) |
| `3` | Asianize (remove comma, keep word order) |
| `4` | DB lookup — searches MuscleMemory, then pick a result by number |
| `5` | Enter manually (type + RETURN) |
| `6` | Skip (leave `<<<<` for now) |
| `9` | Back to previous entry |
| `0` | Done for now (write file, stop this file) |
| `x` | Exit all (write file, stop all remaining files) |

### How it works

- Collects all `<<<<` lines upfront, iterates one at a time
- All decisions held in memory — file only written when done, `0`, or `x` pressed
- **Re-split:** shifts the comma one word position (e.g. `B C, A` → `C, A B`)
- **Asianize:** removes the comma, keeping word order as-is (e.g. `C, A B` → `C A B`)
- **DB lookup:** searches full name first; if no match, tries each word individually
- **Back:** removes previous decision so it can be changed
- **Done for now (`0`):** writes resolved decisions for this file, leaves remaining `<<<<` intact, continues to next file
- **Exit all (`x`):** writes resolved decisions for this file, stops processing all remaining files
- Gender inferred from filename (`-male` / `-female`)

---

## Phase 6: Complete

Verify new athlete names against the master files, resolve conflicts interactively, then write the corrected `.out` file to `5-completed/`. **Does not modify the master.**

### Run the script

```bash
# Process all pending .out files
~/workspace/skills/musmemSkills/musmem-contests/python/verify_and_complete.sh

# Process a specific file (with or without .out extension)
~/workspace/skills/musmemSkills/musmem-contests/python/verify_and_complete.sh 2025_arnold_classic-ifbb-male
```

Input: `~/workspace/musmem/4-reviewed/*.out`
Master files: read-only reference for conflict detection
After completion: corrected file written to `~/workspace/musmem/5-completed/`

Gender inferred from filename (`-male` / `-female`).

### Per-file workflow

1. Read master as read-only reference
2. For each unique name in the `.out` file, run the candidate-matching pipeline (see below)
3. **Auto-accept** names with exactly one exact match and temporal gap ≤ `--max-gap` — no user input
4. Iterate remaining conflicts interactively — corrections held in memory
5. On approval: apply corrections → write corrected file to `5-completed/`

If no conflicts require review, prompts to write immediately.

### Candidate-matching pipeline

Strategies are run in order. All matches across all strategies are collected, deduplicated, and presented together.

| Step | Strategy | Examples caught |
|------|----------|-----------------|
| 1 | **Exact + variants** | `Smith, John` → also finds `Smith, John [2]`, `Smith, John Jr`, `Smith, John III` |
| 2 | **Diacritic normalization** | `Pena` ↔ `Pen~a` ↔ `Peña`; uses internal special-char codes — see `special-chars-reference.md` |
| 3 | **Name part subset/superset** | `Smith, Lisa` ↔ `Smith, Lisa Marie`; partial Latin surnames |
| 4 | **Space normalization** | `Shu Xiao Fan` ↔ `Shu Xiaofan` ↔ `ShuXiaofan` |
| 5 | **Eastern format** | `Xiaofan Shu` (no comma) ↔ `Shu, Xiaofan` |
| 6 | **Word order permutations** | `Xiao Fan Shu` ↔ `Shu Xiao Fan` ↔ `Fan Shu Xiao` |
| 7–8 | **Soundex / edit distance** | `Smithe` ↔ `Smith`; fallback only when steps 1–6 find nothing |

**Auto-accept rule:** Only when there is exactly one candidate, found via exact match only, with temporal gap ≤ `--max-gap`. Any other match type (diacritic, subset, space, etc.) always requires confirmation — even with one candidate.

**Temporal gap warning:** If an exact match is found but the athlete's last master appearance is more than `--max-gap` years before the incoming contest year, a ⚠ year-gap warning is shown and confirmation is required. Default `--max-gap` is 8 years.

```bash
# Override gap threshold
python3 verify_and_complete.py --max-gap 12 2025_arnold_classic-ifbb-male
```

### Keys (single keypress — no RETURN)

| Key | Action |
|-----|--------|
| `1`–`N` | Match to candidate N (corrects spelling in `.out` to master spelling) |
| `N` | New athlete — assign next `[n]` suffix |
| `D` | Details — prompts for a number, then lists all master records for that candidate |
| `S` | Skip — leave name as-is, move to next conflict |
| `9` | Back to previous conflict |
| `0` | Done for now — prompt to write, stop this file |
| `X` | Exit all — prompt to write, stop all remaining files |

### Candidate summary format

```
[2/5] Smith, John  (Arnold Classic - IFBB, 2025, OP-3)
  1. Smith, John              — 18 contests, 2008–2019, OP/CL
  2. Smith, John [2]          — 4 contests, 2021–2024, PH
  3. Smithe, John             — 1 contest, 2023, M4   (soundex)
  N  New athlete → Smith, John [3]
  D  Details (then enter number)
  S  Skip (keep name as-is)
  9  Back
  0  Done for now
  X  Exit all
```

Candidates found via non-exact strategies show a tag: `(diacritic)`, `(subset)`, `(space)`, `(eastern)`, `(wordorder)`, `(soundex)`. Temporal gap warnings show as `⚠ 47yr gap`.

### Name disambiguation (`[n]` notation)

Incoming `.out` files use plain names (no `[n]`). The master may have multiple athletes with the same base name: `Smith, John`, `Smith, John [2]`, `Smith, John [3]`, etc. All variants are presented as candidates. Selecting `N` assigns the next available number to every occurrence in the `.out` file.

---

## Phase 7: Append

Append corrected `.out` files from `5-completed/` to gender-specific staging `.dat` files in `6-appended/`. Files in `5-completed/` are never moved or deleted.

### Run the script

```bash
# Process all files in 5-completed/
~/workspace/skills/musmemSkills/musmem-contests/python/append_to_master.sh

# Process a specific file (with or without .out extension)
~/workspace/skills/musmemSkills/musmem-contests/python/append_to_master.sh 2025_arnold_classic-ifbb-male
```

Input: `~/workspace/musmem/5-completed/*.out`
Output: `~/workspace/musmem/6-appended/append-male.dat` or `append-female.dat`

Gender inferred from filename (`-male` / `-female`).

### Per-file workflow

For each file, shows:
- Contest name, year, and whether it already exists in the staging `.dat` (duplicate warning)
- Number of records to append

Prompts Y/N/X before appending. On Y: appends records to `append-{gender}.dat`.

### Keys (single keypress — no RETURN)

| Key | Action |
|-----|--------|
| `Y` | Append to `6-appended/append-{gender}.dat` |
| `N` | Skip — leave file in `5-completed/` |
| `X` | Exit — stop processing remaining files |

---

## MuscleMemory API Reference

| Endpoint | Purpose |
|----------|---------|
| `GET /api/contests/{year}` | All contests in DB for a year (use `0` for all years) |
| `GET /api/org?name={ORG}` | All contests for a specific org |
| `GET /api/contest/years?name={name}` | Years a contest appears in the DB |
| `GET /api/contest?name={name}&year={year}` | Full results for a specific contest+year |

Base URL: `https://musclememory.net`

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using query-param tracking URLs from npcnewsonline.com | Use the clean URLs in sources-reference.md — tracking params cause errors |
| Comparing names without normalizing org prefix | Always strip "IFBB "/"NPC "/"NPC Worldwide "/"CPA " prefix before comparing |
| Assuming contest is new without checking DB | Always query the API first |
| Writing names in Last, First order | npcnewsonline.com uses First Last — do not set `l 1` |
| Wrong User-Agent for musclememory.net | The API blocks bot UAs and returns fake HTML — use a browser UA (e.g. `Mozilla/5.0 ... Chrome/120.0.0.0 Safari/537.36`) for all musclememory.net API calls |
| No User-Agent when scraping external sites | When fetching npcnewsonline.com etc. via curl/script use `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36` — WebFetch does not support custom headers |
| Using WebFetch on large contest pages | WebFetch truncates at ~50KB — later divisions get silently cut off or hallucinated. Use curl + Python for large contests (NPC Nationals, Olympia, etc.) — see sources-reference.md |
| Mixing male and female divisions in one file | Contests with both genders need `-male.txt` and `-female.txt` files — same division codes would collide in a single file |
| Using divisions.php as code reference | Source of truth is now `en.json` DIVISIONS — `PRh` is Pro HeavyWeight (not `Ph`, which is Physique H) |
| Prefixing Olympia with "Mr" | Contest title is `Olympia - IFBB`, not `Mr Olympia - IFBB`. "Mr {name}" applies only to selected AAU titles and selected pre-1980 IFBB titles. |
| HTML entities in names | npcnewsonline.com sometimes includes raw HTML entities (e.g., `&#039;` for `'`, `&amp;` for `&`). Decode them when writing the flat file or format.php will error on the line. |
