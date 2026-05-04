# musmem-normalize Skill Design

## Purpose

An interactive skill for resolving name variant groups across two bodybuilding dat files — correcting spelling errors, typos, and formatting inconsistencies between incoming data and existing records.

## Files Involved

- `~/workspace/musmem/data/bb_male.dat` — main dataset (~177K lines)
- `~/workspace/musmem/data/prelim/covid-male.dat` — incoming data
- `~/workspace/musmem/data/prelim/bb2010-covid-male-variant-groups.tsv` — candidate groups (output of a prior deduplication script)

## TSV Structure

The variant-groups TSV has 6 columns:

| # | Column | Description |
|---|---|---|
| 1 | `group_id` | Integer group identifier |
| 2 | `name` | A name variant belonging to this group |
| 3 | `count_bb_male` | Occurrences of this variant in bb_male.dat |
| 4 | `count_covid_male` | Occurrences of this variant in covid-male.dat |
| 5 | `expression` | Decision recorded during review (see Expression Language) |
| 6 | `applied` | ISO timestamp when corrections were written to dat files; blank if pending |

## Session Loop

1. Read the TSV and find the first group where all rows have a blank `expression` column (i.e., not yet reviewed)
2. Fetch all matching records from both dat files for every variant in the group
3. Display the group summary (see Display Format)
4. Wait for user input
5. Record the decision in the TSV `expression` column for all rows in the group
6. Loop to the next pending group

The loop continues until the user enters `process` or `exit`.

## Display Format

```
══════════════════════════════════════════════
Group 14  (3 variants, 8 records total)
══════════════════════════════════════════════
a  Adams, Brian     [bb_male: 1]   2010  NPC  3L
b  Adams, Bryan     [bb_male: 2]   2001–2002  NPC  HW, SW
c  Adams, Bryan     [covid:   2]   2021–2022  NPC  SW, LH
──────────────────────────────────────────────
Expression (or skip/defer/process/exit/expand <a|b|c>):
```

Each variant line shows: label, name, source file + count, year range, orgs, divisions.

`expand <label>` dumps full records for that variant before re-prompting.

## Expression Language

Variants are labeled `a`, `b`, `c`... in display order. Unmentioned variants are left untouched.

| Expression | Meaning |
|---|---|
| `a=b` | Rename all `a` records to `b`'s name |
| `b=a` | Rename all `b` records to `a`'s name |
| `a="New Name"` | Rename all `a` records to a new spelling |
| `[a,b]=c` | Rename all `a` and `b` records to `c`'s name |
| `[a,b]="New Name"` | Rename all `a` and `b` records to a new spelling |
| `skip` | Confirmed different athletes — do not show again |
| `defer` | Needs more research — show again next session |
| `expand a` | Show full records for variant `a`, then re-prompt |
| `process` | Write all queued corrections to dat files, continue loop |
| `exit` | Quit without writing |

Multiple expressions for one group can be comma-separated: e.g. `[a,b]=c, d="New Name"` handles a 4-variant group that splits two ways.

## Session Resumption

- Groups with `expression = skip` or a correction expression are not presented again
- Groups with `expression = defer` or blank are presented in future sessions
- The loop always starts from the first non-final pending group

## Applying Corrections (`process`)

When the user enters `process`:

1. Read all rows from the TSV where `expression` is set but `applied` is blank
2. Build a rename map: `{source_name → canonical_name}` resolved from each expression
3. Check for collisions: if a canonical name already exists in the target file alongside the source name, warn the user before writing
4. For each dat file, read into memory, replace matching name fields (exact match on field before first `;`), write back
5. Stamp the `applied` timestamp on all processed TSV rows
6. Continue the session loop

Sorting is handled by external scripts — do not re-sort after writes.

## Skill File

New skill: `.claude/skills/musmem-normalize.md`

The skill is conversational — Claude manages the loop in the conversation. Python scripts handle all file I/O (reading TSV, fetching records, writing corrections). File paths are hardcoded as defaults in the skill with optional overrides.
