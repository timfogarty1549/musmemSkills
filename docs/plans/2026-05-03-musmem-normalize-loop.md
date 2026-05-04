# musmem-normalize: Python Interactive Loop

**Date:** 2026-05-03

## Goal

Replace Claude's managed session loop with a standalone Python script (`normalize.py`) so the tool runs without Claude involvement after startup.

## Architecture

`normalize.py` lives in `.claude/skills/musmem-normalize/python/` alongside the four existing scripts. It imports them as modules — no logic duplication. The existing scripts remain standalone-runnable.

SKILL.md is simplified: instead of a multi-step Claude loop, it says copy `normalize.py` to `/tmp/` and run it.

## Startup

Interactive file-path prompts with defaults, Enter to confirm:

```
File 1 [~/workspace/musmem/data/bb_male.dat]:
File 2 [~/workspace/musmem/data/prelim/covid-male.dat]:
TSV    [~/workspace/musmem/data/prelim/bb2010-covid-male-variant-groups.tsv]:
```

Then immediately fetch and display the first pending group.

## Display Format

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

Record field parsing:
- **year**: field index 1
- **org**: last word after ` - ` in field index 2
- **division**: part before `-` in field index 3
- **countries**: all `c=XX` patterns anywhere in the record

## Input Handling

| Input | Action |
|---|---|
| `skip` | Record, fetch next |
| `defer` | Record, fetch next |
| `expand <label>` | Print full records, re-prompt (no advance) |
| `process` | Run apply_corrections, print rename map + counts, continue |
| `quit` | Stop, print queued-but-not-applied count |
| expression | Collision-check quoted targets, then record, fetch next |

Collision flow: warn + `Proceed anyway? (yes / new expression):` — loops until resolved.

When no pending groups remain: print notice and wait for `process` or `quit`.
