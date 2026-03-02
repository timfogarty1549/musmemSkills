# Phase 5 — Append & Verify Design

**Date:** 2026-03-01
**Status:** Approved

## Overview

After Phase 4 (review flagged names), Phase 5 appends formatted `.out` files to the master flat files (`bb_male.dat` / `bb_female.dat`), verifying each new athlete name against existing master records before committing the append. The master files are the source of truth — the live site loads them into memory.

---

## Script & Invocation

Two files mirroring Phase 4:
- `~/workspace/skills/musmemSkills/musmem-contests/python/verify_and_append.py` — main logic
- `~/workspace/skills/musmemSkills/musmem-contests/python/verify_and_append.sh` — shell wrapper

```bash
# Process all pending .out files
~/workspace/skills/musmemSkills/musmem-contests/python/verify_and_append.sh

# Process a specific file (with or without .out extension)
~/workspace/skills/musmemSkills/musmem-contests/python/verify_and_append.sh 2025_arnold_classic-ifbb-male
```

Gender inferred from filename: `-male` → `bb_male.dat`, `-female` → `bb_female.dat`.

**Pending** = `.out` files in `~/workspace/musmem/formatted/` not yet appended.
After successful append, file is moved to `~/workspace/musmem/appended/`.

---

## Per-File Workflow

1. Read master file into memory (read-only reference)
2. Parse the `.out` file — extract unique athlete names not already in master → "new athletes"
3. For each new athlete, run similarity checks against master (see below)
4. Collect all conflicts upfront, then iterate interactively
5. All corrections held in memory — no files touched yet
6. When done (all conflicts resolved, or `0`/`X` pressed):
   - Apply name corrections to `.out` lines in memory
   - Append corrected content to master
   - Sort master in place
   - Move `.out` to `~/workspace/musmem/appended/`

If **no conflicts** exist, file is appended automatically — no interaction needed.

---

## Similarity Detection

For each new athlete name, strip any `[n]` suffix from master names before comparing.

| Check | Catches |
|-------|---------|
| Soundex on last name, exact first | `Smith` vs `Smithe` |
| Soundex on first name, exact last | `John` vs `Jon` |
| Anagram of full name | letter transpositions |
| Sorted words match | first/last swap |
| Edit distance ≤ 2 on last name | single typos soundex misses |

All matches shown regardless of year range (career spans vary widely).

New athletes with no similar names in master pass through silently.

---

## Name Disambiguation (`[n]` Notation)

Incoming `.out` files use plain names (no `[n]`). The master may contain:
- `Smith, John` — first athlete with this name
- `Smith, John [2]`, `Smith, John [3]` — subsequent distinct athletes

When a conflict is found, all master variants of the base name are presented as candidates.

---

## Interactive Interface

Single-keypress. For each conflict:

```
NEW: Smithe, John  (Arnold Classic - IFBB 2025, OP-3)

Candidates in master:
  1. Smith, John       — 18 contests, 2008–2019, OP/CL
  2. Smith, John [2]   — 4 contests, 2021–2024, PH
  3. Smith, John [3]   — 1 contest, 2023, M4
  N  New athlete → Smith, John [4]
  D  Details (then enter number)
  S  Skip (leave as-is for now)
  9  Back to previous
  0  Done for now (append what's resolved, stop this file)
  X  Exit all
```

**1–N (number):** Corrects every occurrence of the new name in the `.out` file to the chosen master spelling. If `N`, assigns next available `[n]` suffix to every occurrence.

**D:** Prompts `Which candidate? >`, then prints all master records for that candidate, then redisplays the menu.

**S:** Leaves name unchanged, moves to next conflict.

**9:** Removes previous decision, steps back.

**0:** Applies resolved corrections, appends file to master, sorts, moves file. Stops processing remaining files.

**X:** Same as `0` but stops all remaining files.

---

## Candidate Summary Format

```
  2. Smith, John [2]   — 4 contests, 2021–2024, PH
```

Fields: master name, contest count, year range, division codes (deduplicated).

Detail view (`D` + number): all raw master records for that candidate, one per line.

---

## Master File Only Changes Once Per File

The master is not touched during the interactive session. It is appended, sorted, and the `.out` moved only after the user approves the full file.
