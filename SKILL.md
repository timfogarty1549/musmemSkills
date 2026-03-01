---
name: musmem-contests
description: Use when checking bodybuilding contest websites for new results not yet in the MuscleMemory database, or when generating flat files of contest results for import into musclememory.net.
---

# MuscleMemory Contest Checker

Checks bodybuilding org websites for contests missing from the MuscleMemory database and generates flat files for import via `format.php`.

## Quick Reference

| Phase | What Claude does |
|-------|-----------------|
| 1 — Discovery | Fetch DB + scrape org site → report missing contests |
| 2 — Results | Scrape individual contest pages → write flat file |
| 3 — Format | Run flat files through format.php → write `.out` files |
| 4 — Review | Interactively resolve `<<<<` flagged names in `.out` files |

---

## Phase 1: Discovery

### 1. Fetch the MuscleMemory DB for the target year(s)

```
GET https://musclememory.net/api/contests/{year}
```

Returns `data.contests` — an array of strings in `"Contest Name - ORG"` format.

If checking multiple years, call once per year.

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

**One file per contest.** Save each to `~/workspace/musmem/incoming/`.

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

**Create the directory if it doesn't exist:** `mkdir -p ~/workspace/musmem/incoming`

Report to the user: list of files written and total competitors captured per file.

---

## Phase 3: Format

Run the flat files through `format.php` to produce import-ready `.out` files.

### Run the formatter

```bash
# Format all unprocessed files (no .out yet in formatted/)
~/workspace/skills/musmemContests/php/run_format.sh

# Format a specific file (with or without .txt extension)
~/workspace/skills/musmemContests/php/run_format.sh 2025_olympia-ifbb-male

# Reprocess all files, overwriting existing .out files
~/workspace/skills/musmemContests/php/run_format.sh --force

# Reprocess a specific file, overwriting its .out
~/workspace/skills/musmemContests/php/run_format.sh --force 2025_olympia-ifbb-male
```

Input: `~/workspace/musmem/incoming/*.txt`
Output: `~/workspace/musmem/formatted/*.out`

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

## Phase 4: Review Flagged Names

Interactively resolve all `<<<<` lines in `.out` files. Run the script via Claude (opens a Terminal window) or directly in your terminal.

### Run the script

Claude launches it with:
```bash
~/workspace/skills/musmemContests/python/review_flags.sh 2025_olympia-ifbb-male
~/workspace/skills/musmemContests/python/review_flags.sh   # all files with <<<< lines
```

Or run directly:
```bash
python3 ~/workspace/skills/musmemContests/python/review_flags.py 2025_olympia-ifbb-male
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
| No User-Agent in scripts | When fetching via curl/script use `MuscleMemoryBot/1.0 (+https://musclememory.net/bot)` — WebFetch does not support custom headers |
| Using WebFetch on large contest pages | WebFetch truncates at ~50KB — later divisions get silently cut off or hallucinated. Use curl + Python for large contests (NPC Nationals, Olympia, etc.) — see sources-reference.md |
| Mixing male and female divisions in one file | Contests with both genders need `-male.txt` and `-female.txt` files — same division codes would collide in a single file |
| Using divisions.php as code reference | Source of truth is now `en.json` DIVISIONS — `PRh` is Pro HeavyWeight (not `Ph`, which is Physique H) |
| Prefixing Olympia with "Mr" | Contest title is `Olympia - IFBB`, not `Mr Olympia - IFBB`. "Mr {name}" applies only to selected AAU titles and selected pre-1980 IFBB titles. |
| HTML entities in names | npcnewsonline.com sometimes includes raw HTML entities (e.g., `&#039;` for `'`, `&amp;` for `&`). Decode them when writing the flat file or format.php will error on the line. |
