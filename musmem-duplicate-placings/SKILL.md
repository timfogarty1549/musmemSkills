---
name: musmem-duplicate-placings
description: Use when a contest may have been entered into more than one data file (e.g. a missed division was patched by re-adding the whole contest to a prelim file), producing the same division/placement slot in two files under athlete names that may not yet be normalized.
---

# musmem-duplicate-placings

Scans a user-specified set of bodybuilding data files and identifies contests where the same (division, placement) slot appears in more than one file — a sign the contest was fully or partially re-entered rather than merged.

## Quick Reference

| Step | Action |
|------|--------|
| 1 | Run the detection script |
| 2 | Enter file names one at a time when prompted; blank line ends the list |
| 3 | Review flagged contests and their overlapping division/placement slots |
| 4 | Spot-check each pair in the raw data files |
| 5 | Report findings to user; stop |

**Do not auto-advance.** Run the script, report, and stop.

---

## Key Files

| File | Role |
|------|------|
| `~/workspace/musmem/data/` | Default folder — entered file names are resolved relative to this unless absolute |
| `scripts/find_duplicate_placings.py` | Detection script — prompts for file names interactively |

File names change over time — confirm current file names with the user or by listing the data directory before running.

---

## Data Format

Each line: `Name; Year; Contest Name; DivisionCode-Placement; [optional fields]`

- `MW-5` → division MW, placement 5
- `98` (bare number, no hyphen) → division OPEN (older pro records), placement 98
- Placements `98` (competed, no rank) and `0` (special) are **excluded from the overlap check** — they don't represent a unique-holder slot, so seeing them in multiple files is normal. They still count toward each file's total record count.

---

## Detection Algorithm

For each `(year, contest name)` present in **2 or more** of the input files:

1. Build the set of `(division, placement)` slots each file holds for that contest (skipping placements 98 and 0).
2. Any slot held by more than one file is a **duplicate placing**.
3. If any duplicate placings exist, flag the contest and report:
   - Total record count per file for that contest
   - Every overlapping `(division, placement)` slot, with the athlete name recorded in each file

Matching is on **exact contest name + division + placement only** — not on athlete name. This is deliberate: one file may already be normalized (e.g. `bb_male.dat`) while another may not be (e.g. a freshly-scraped `prelim-*.dat`), so the same person can appear as `J. Smith` in one file and `John Smith` in another. The script surfaces both spellings side by side so a human can confirm it's the same slot.

---

## Running the Script

```bash
python3 ~/workspace/skills/musmemSkills/musmem-duplicate-placings/scripts/find_duplicate_placings.py
```

The script prompts for file names one at a time (relative to `~/workspace/musmem/data/`, or an absolute path). A blank line ends the list. It does not run as a single non-interactive shell call — pipe the file names in via stdin, e.g.:

```bash
printf 'bb_male.dat\nprelim/prelim-male.dat\n\n' | python3 ~/workspace/skills/musmemSkills/musmem-duplicate-placings/scripts/find_duplicate_placings.py
```

Confirm the current file names with the user before running — do not guess, since names change over time.

Output format:
```
2018: 'Contest X'
      bb_male.dat: 40 records
      prelim-male.dat: 52 records
      Overlapping division/placement slots (3):
        LW-1: bb_male.dat='John Smith' vs prelim-male.dat='J. SMITH'
        LW-2: bb_male.dat='Mike Jones' vs prelim-male.dat='MIKE JONES'
        MW-1: bb_male.dat='Bob Lee' vs prelim-male.dat='ROBERT LEE'
```

The record-count difference (52 vs 40) plus the fact that only 3 of the divisions overlap tells you the extra records in `prelim-male.dat` are the genuinely-missing division(s) — those are fine to keep. The overlapping slots are the actual duplicates to remove (typically from whichever file is unnormalized/newer).

---

## Interpreting Results

- **A contest flagged with overlaps** almost always means the same contest data exists in two places for at least some divisions. Confirm by grepping the contest name in both files and comparing full rosters.
- **A contest present in 2+ files with NO overlap** is not flagged — that's the normal, healthy case of one file supplying a division the other was missing.
- Once confirmed, the usual fix is to delete the duplicated (division, placement) rows from the un-normalized file and keep only the genuinely new division(s), then run the normalization script on what remains before merging.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Matching on athlete name | Don't — one side may be unnormalized. Match on (division, placement) only |
| Flagging placements 98/0 as duplicates | Script already excludes them from the overlap check |
| Assuming any multi-file contest is a duplicate | Only flagged if actual (division, placement) slots overlap — supplementing a missing division is normal and won't be flagged |
| Assuming fixed file names | Names change over time — ask the user or list the data directory to confirm current names before entering them |
