---
name: musmem-duplicate-contests
description: Use when searching for contests that were entered twice under different names across bb_*.dat and prelim/*.dat files.
---

# musmem-duplicate-contests

Scans a user-specified set of bodybuilding data files as a single source and identifies contest pairs that likely represent the same physical event entered under different names.

## Quick Reference

| Step | Action |
|------|--------|
| 1 | Run the detection script |
| 2 | Enter file names one at a time when prompted; blank line ends the list |
| 3 | Review candidate pairs reported |
| 4 | Spot-check each pair in the raw data files |
| 5 | Report findings to user; stop |

**Do not auto-advance.** Run the script, report, and stop.

---

## Key Files

| File | Role |
|------|------|
| `~/workspace/musmem/data/` | Default folder — entered file names are resolved relative to this unless absolute |
| `scripts/find_duplicates.py` | Detection script — prompts for file names interactively |

File names change over time (e.g. `prelim-male.dat`, `npc-a-male.dat` have replaced older `covid-male.dat`/`gap-male.dat` naming). The script does not hardcode a file list — confirm current file names with the user or by listing the data directory before running.

---

## Data Format

Each line: `Name; Year; Contest Name; DivisionCode-Placement; [optional fields]`

- `MW-5` → division MW, placement 5
- `98` (bare number, no hyphen) → division OPEN (older pro records), placement 98
- Placements `98` (competed, no rank) and `0` (special) are **excluded** from all matching

---

## Detection Algorithm

Contests are compared **within the same year only**.

**Method 1 — multi-division shows** (≥ 4 shared named divisions), three cascading stages:
1. Find divisions where 1st place matches → need ≥ 4
2. Of those, find where 2nd place also matches → need ≥ 2
3. Of those, find where 3rd place also matches → need ≥ 2
All three stages must pass → DUPLICATE.

**Method 2 — single-division or old pro shows** (< 4 shared named divisions), two cascading stages:
1. Confirm places 1–4 exist in both contests and are held by the same athletes
2. Of places 5–8, require ≥ 2 to also match (if either contest has athletes there; if both fields end at place 4, skip this check)
Both stages must pass → DUPLICATE.

Male and female records are combined — a contest's divisions span both files.

---

## Running the Script

```bash
python3 ~/workspace/skills/musmemSkills/musmem-duplicate-contests/scripts/find_duplicates.py
```

The script prompts for file names one at a time (relative to `~/workspace/musmem/data/`, or an absolute path). A blank line ends the list. It does not run as a single non-interactive shell call — pipe the file names in via stdin, e.g.:

```bash
printf 'bb_male.dat\nprelim/prelim-male.dat\nprelim/npc-a-male.dat\n\n' | python3 ~/workspace/skills/musmemSkills/musmem-duplicate-contests/scripts/find_duplicates.py
```

Confirm the current file names with the user before running — do not guess, since names change over time.

Output format:
```
2019: 'Arnold Classic - IFBB'
      'Arnold Classic Brasil - IFBB'
      [method1, 5 matching athletes]
```

---

## Interpreting Results

Many candidates will be **legitimate false positives**:

- Small regional qualifiers where the same top athletes repeatedly win
- Renamed contests (old name vs. new name in the same year)
- Pro shows where only 1–3 athletes compete across divisions

For each candidate pair: grep both names in the data files and compare the full athlete lists before concluding they are true duplicates.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Comparing across different years | Script already restricts to same year — don't override this |
| Treating placement-98 records as real results | Script already excludes 98 and 0 |
| Concluding duplicate from the script output alone | Always spot-check in the raw files before reporting |
| Assuming fixed file names (e.g. `covid-male.dat`) | Names change over time — ask the user or list the data directory to confirm current names before entering them |
