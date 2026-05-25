---
name: musmem-duplicate-contests
description: Use when searching for contests that were entered twice under different names across bb_*.dat and prelim/*.dat files.
---

# musmem-duplicate-contests

Scans all six bodybuilding data files as a single source and identifies contest pairs that likely represent the same physical event entered under different names.

## Quick Reference

| Step | Action |
|------|--------|
| 1 | Run the detection script |
| 2 | Review candidate pairs reported |
| 3 | Spot-check each pair in the raw data files |
| 4 | Report findings to user; stop |

**Do not auto-advance.** Run the script, report, and stop.

---

## Key Files

| File | Role |
|------|------|
| `~/workspace/musmem/data/bb_male.dat` | Primary male results |
| `~/workspace/musmem/data/bb_female.dat` | Primary female results |
| `~/workspace/musmem/data/prelim/covid-male.dat` | COVID-era male results |
| `~/workspace/musmem/data/prelim/covid-female.dat` | COVID-era female results |
| `~/workspace/musmem/data/prelim/gap-male.dat` | Gap-period male results |
| `~/workspace/musmem/data/prelim/gap-female.dat` | Gap-period female results |
| `scripts/find_duplicates.py` | Detection script |

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
| Running script on only one gender file | Always run against all six files via the script — never partial |
