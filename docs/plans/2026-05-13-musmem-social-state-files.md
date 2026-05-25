# Plan: Persistent State for musmem-social Dat-file Sweeps

## Context

The musmem-social skill currently handles contest-based lookups (Mode 1) and handle validation (Mode 2). A third use pattern has emerged: sweeping through all distinct athletes in a `.dat` file alphabetically to find their social media handles. This sweep is token-intensive and always runs out before completing, requiring multiple sessions.

Two problems:
1. **Resume overhead** — every new session reconstructs state from scratch (reads old transcript, runs scripts to count coverage), spending many tokens before doing any actual search work.
2. **False-match re-search** — user reviews JSON output and deletes false matches. The deleted athlete has no "already searched" marker, so a future session re-finds and re-writes the same bad profile.

## Solution: Two State Files

Both files live in `~/workspace/musmem/working_data/` and are **global per gender + platform** — not tied to any specific dat file. The same athlete can appear in multiple dat files (bb_male.dat, covid-male.dat, gap-male.dat); these files ensure they are only ever searched once.

### 1. Progress file — `progress-{platform}-{gender}.json`

Tracks which dat file is currently being swept and where we are in it. Updated after every batch.

```json
{
  "platform": "ig",
  "gender": "male",
  "current_dat_file": "prelim/covid-male.dat",
  "last_name_processed": "Czyz, Jan",
  "total_in_current_dat": 8459,
  "searched_in_current_dat": 2341,
  "last_updated": "2026-05-08"
}
```

**Purpose:** On resume, read this first. If the same dat file is specified → jump past `last_name_processed`. If a different dat file → start from the beginning of that file (but still skip names in the searched log).

### 2. Searched log — `searched-{platform}-{gender}.txt`

One `Last, First` name per line — every athlete ever searched on that platform for that gender, across all dat files, whether found or not. Appended after each name is searched.

```
Abbas, Anwar
Abbott, Justin
Abba, Hugo
...
```

**Purpose:** Even after the user deletes a false match from a JSON file, the athlete's name stays in this file. Future sessions skip them regardless of which dat file they appear in. The user can manually remove a name to allow re-searching.

## Skill Changes — `musmem-social/SKILL.md`

Add **Mode 3: Dat-file Sweep** section.

### Input
- Path to `.dat` file (e.g., `prelim/covid-male.dat` or `bb_male.dat`)
- Platform
- Gender
- Optional `--min-year` to filter dat entries by year

### Session Start Protocol
1. Read `working_data/progress-{platform}-{gender}.json` if it exists
2. Read `working_data/searched-{platform}-{gender}.txt` if it exists → build set of already-searched names
3. Determine start point:
   - Same dat file as progress → resume from name after `last_name_processed`
   - Different dat file (or no progress file) → start from beginning of new dat file
4. Report: `"Resuming from [last_name_processed] in [dat_file]. [N] names already searched globally. Next: [first unsearched name]."`

### Name extraction
- Read distinct `Last, First` values from column 1 of the dat file (semicolon-delimited)
- Filter by `--min-year` if provided
- Sort alphabetically
- Remove any names already in the searched log (see Diacritic handling below)

### Diacritic handling
Dat files use ASCII-safe codes for diacritics (e.g., `Rodri'guez`, `S^tefan`). See `docs/special-chars-reference.md` for the full mapping.

| Context | Form to use | Rationale |
|---------|-------------|-----------|
| Searched log (storage) | Coded — as-is from dat file | Consistent with source data |
| JSON `name` field (storage) | Coded — as-is from dat file | Consistent with source data |
| Web search query | Strip codes to plain ASCII (`Rodriguez`, `Stefan`) | Unicode form misses too many results; plain ASCII maximises recall |
| Searched log lookup (comparison) | Strip codes to plain ASCII on both sides | Allows `Rodri'guez` from one file to match `Rodriguez` from another |
| Alphabetical sort | Strip codes to plain ASCII | Correct sort order without Unicode collation complexity |

### Search loop
- After each name searched (found **or** not): append name to searched log
- After each batch of ~10 searches: update progress file
- Output JSON files go in `~/workspace/musmem/data/social-media/`, named after the dat file being swept: `{dat-basename}-{letter}-section-{gender}.json`

## Retroactive State for Current In-Progress Sweep

A sweep of `prelim/covid-male.dat` (instagram, male) completed A–C sections with 207 found names. Retroactively bootstrap state:

1. Extract all names with first letter ≤ C from `covid-male.dat`, sorted → last one is `last_name_processed`
2. Collect all `name` values from the three existing JSON files → write to `searched-ig-male.txt`
3. Write `progress-ig-male.json` pointing to `prelim/covid-male.dat` with that last name

Note: Names searched but not found in A–C are absent from the searched log (history lost), but `last_name_processed` prevents re-searching them since they fall before the resume point.

## Files

| Action | File |
|--------|------|
| Edit | `musmemSkills/.claude/skills/musmem-social/SKILL.md` |
| Create | `~/workspace/musmem/working_data/progress-ig-male.json` |
| Create | `~/workspace/musmem/working_data/searched-ig-male.txt` |

## Verification

Start a new session and invoke musmem-social on `prelim/covid-male.dat`, platform `ig`, gender `male`. The session should:
1. Read both state files immediately
2. Report the resume point and globally-searched count — without reading any transcript or running discovery scripts
3. Begin searching from the first D name in covid-male.dat
