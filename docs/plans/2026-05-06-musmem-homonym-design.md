# MuscleMemory Homonym Detection — Design

## Purpose

Identify athlete names in contest data files that likely represent two different people — a common problem when the same name was used by a competitor in the 1980s and again by an unrelated competitor decades later.

## Input

- Prompt for one or more semicolon-delimited `.dat` files.
- Paths may be absolute, `~`-relative, or bare filenames resolved under `~/workspace/musmem/data`.
- All files are merged into one dataset; source file is not tracked.

## Data Format

Each row: `name; year; contest; division_code-placing; [country];`

- Col 1: athlete name (Last, First)
- Col 2: year (integer)
- Col 4: division code + placing — code is everything before the final `-N` suffix (e.g. `LH` from `LH-3`)

## Detection Logic

Group records by exact name. For each name with 2+ records:

**Pattern A — Large year gap**
Flag if the year span contains a gap of 10+ consecutive years with no appearances.

**Pattern B — 80s athlete in modern era without 60+ category**
Flag if any appearances are before 1995 AND any are after 2010, and the post-2010 appearances are not in a 60+ or older masters category (M6*, 6H, 6l, 6M, 6L, 6t, 6m, 6s, m6, 65, M7*, 7H, 7M, 7L, M8, M9, GM, UM).

**Pattern C — Category profile consistent across gap**
If both the early cluster and late cluster are open/non-masters, this strengthens the suspicion. If the athlete competed exclusively in masters categories throughout all appearances, the flag is lower confidence.

An athlete triggering multiple patterns is higher confidence.

## Report Format

One line per flagged name, sorted highest confidence first:

```
Smith, John; 1984–1991, 2022–2024
Jones, Bob; 1988–1990, 2019–2023
```

Year ranges represent contiguous clusters of appearances separated by the detected gap.

Summary line at the end:

```
68 names flagged
```

Lower-confidence cases (gap present but masters-only throughout) appear in a separate section at the bottom.

## Implementation

- Single Python script prompted by the skill
- No external dependencies beyond stdlib
- Follow project convention: write script to `/tmp/` before running via Bash tool
