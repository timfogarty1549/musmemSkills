---
name: musmem-normalize
description: Use when resolving bodybuilding athlete name variant groups — correcting spelling errors, typos, and formatting mismatches between bb_male.dat and covid-male.dat.
---

# MuscleMemory Name Normalization

Interactive Python tool for reviewing candidate name variant groups and deciding how to reconcile them across two dat files.

## Setup (start of every session)

Run via the shell alias (defined in `~/.bash_profile`):

```bash
musmemNormalize
```

Or directly:

```bash
python3 ~/workspace/skills/musmemSkills/musmem-normalize/python/normalize.py
```

When invoking via Claude's Bash tool, copy to `/tmp/` first (required by permission rules):

```bash
cp ~/workspace/skills/musmemSkills/musmem-normalize/python/*.py /tmp/
python3 /tmp/normalize.py
```

The script prompts for the TSV on startup. If the TSV was produced by `musmem-extract-distinct-athletes`, the source `.dat` file paths are embedded in the TSV and loaded automatically — no further input needed:

```
TSV files in ~/workspace/musmem/distinct/:
  1. bb_male-covid_male-variant-groups.tsv
TSV    (~/workspace/musmem/distinct/): 1
Source files: ~/workspace/musmem/data/bb_male.dat, ~/workspace/musmem/data/covid-male.dat
```

For TSVs that predate this feature (no embedded source paths), the script falls back to prompting for file paths manually.

After confirming paths, the script enters the interactive loop automatically.

## What the Script Does

For each pending group, it displays:

```
══════════════════════════════════════════════════════════
Group 42  (3 variants, 7 records)   [156 pending]
══════════════════════════════════════════════════════════
a  Jones, John                      [f1:3, f2:1]   2011–2014  NPC  BB, MP  US
b  Jones, John Jr.                  [f2:2]         2012       NPC  BB
c  Jones, Johnny                    [f1:1]         2013       NPC  BB      CA
──────────────────────────────────────────────────────────
Expression (skip / defer / process / quit / expand <label>):
```

| Input | Action |
|-------|--------|
| `skip` | Record `skip`, move to next group |
| `defer` | Record `defer`, move to next group |
| `expand <label>` | Print full records for that variant; re-display group |
| `process` | Apply all queued corrections, then move to next group |
| `quit` | Stop; print count of queued-but-not-applied corrections |
| Any expression | Collision-check quoted targets, record, move to next group |

When no more pending groups remain, the script prompts for `process` or `quit`.

## Expression Language

Variants are labeled `a`, `b`, `c`… in alphabetical order by name.

| Expression | Meaning |
|---|---|
| `a=b` | Rename all records with `a`'s name to `b`'s name |
| `b=a` | Rename all records with `b`'s name to `a`'s name |
| `a="New Name, Corrected"` | Rename all records with `a`'s name to the quoted literal |
| `[a,b]=c` | Rename all `a` and `b` records to `c`'s name |
| `[a,b]="New Name"` | Rename all `a` and `b` records to the quoted literal |
| `[a,b]=c, d="Other"` | Multiple renames for one group (comma-separated) |

Variants not mentioned in an expression are left untouched.

## TSV Column Reference

| Col | Name | Notes |
|-----|------|-------|
| 1 | `group_id` | Integer group identifier |
| 2 | `name` | A name variant in this group |
| 3 | `expression` | Per-row decision: blank = pending; `defer` = revisit later; `skip` = no change (whole group); `-` = no rename for this row; any other value = rename this row's name to that value |
| 4 | `applied` | ISO timestamp when corrections were written; blank if not yet applied |

## Session Resumption

Groups with `expression = skip` or a correction expression (and `applied` set) are not shown again.
Groups with `expression = defer` or blank `expression` are shown in future sessions.
