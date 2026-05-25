---
name: musmem-mislabeled-divisions
description: Use when searching for contests where athletes were assigned to the wrong division class — e.g., Light-heavyweight results filed under Lightweight — producing duplicate placements across bb_*.dat and prelim/*.dat files.
---

# musmem-mislabeled-divisions

Scans all bodybuilding contest data files for divisions where multiple athletes share the same placement AND the next placement is also filled — the signature of two classes merged under one division label.

## Quick Reference

| Step | Action |
|------|--------|
| 1 | Run the detection script |
| 2 | Review flagged divisions by severity (HIGH first) |
| 3 | Spot-check each flag in the raw .dat file |
| 4 | Report findings to user; stop |

**Do not auto-advance.** Run the script, report, and stop.

---

## Key Files

| File | Role |
|------|------|
| `~/workspace/musmem/data/bb_male.dat` | Primary male results |
| `~/workspace/musmem/data/bb_female.dat` | Primary female results |
| `~/workspace/musmem/data/prelim/covid-*.dat` | COVID-era results |
| `~/workspace/musmem/data/prelim/gap-*.dat` | Gap-period results |
| `~/workspace/musmem/data/prelim/npc-*.dat` | NPC prelim results |
| `~/workspace/musmem/data/prelim/legion*.dat` | Legion Athletics results |
| `~/workspace/musmem/data/prelim/unknown-emerald-*.dat` | Unknown Emerald results |
| `scripts/detect_mislabeled.py` | Detection script |

---

## Detection Rule

For each `(year, contest, division)` group within a single file:

1. Collect all placements, **excluding placements ≥ 90** (98 = DNP, 99 = DQ, other 9x = special)
2. If placement `P` appears more than once **and** `P+1` also exists → **suspicious**

Valid tie: two athletes at P5 with no P6 → not flagged.  
Mislabeled: two athletes at P5 with someone at P6 → flagged.

Male and female files are processed separately and never compared against each other.

---

## Severity

| Level | Condition |
|-------|-----------|
| HIGH | 3+ distinct duplicate placements (likely entire class mislabeled) |
| MED | 2 distinct duplicate placements |
| LOW | 1 duplicate placement with next placement filled (possibly one athlete mislabeled) |

Asterisk (`*`) marks the suspicious placements in output.

---

## Running the Script

```bash
python3 ~/workspace/skills/musmemSkills/musmem-mislabeled-divisions/scripts/detect_mislabeled.py
```

Optional filters:

```bash
# Narrow by file
python3 ~/workspace/skills/musmemSkills/musmem-mislabeled-divisions/scripts/detect_mislabeled.py --file bb_male.dat

# Narrow by year
python3 ~/workspace/skills/musmemSkills/musmem-mislabeled-divisions/scripts/detect_mislabeled.py --year 2019

# Narrow by contest name substring
python3 ~/workspace/skills/musmemSkills/musmem-mislabeled-divisions/scripts/detect_mislabeled.py --contest "Arnold"
```

---

## Interpreting Results

HIGH flags are most likely genuine data errors. LOW flags are often valid ties at non-final positions or data entry quirks — always spot-check before concluding.

Common legitimate causes for LOW flags:
- Judges awarded identical points to two athletes at a non-last position (unusual but possible)
- One athlete's division code was mistyped (e.g., `LH` vs `LH2`)

For each flag: grep both athlete names in the raw .dat file and compare the full placement sequence.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Treating all LOW flags as errors | Always spot-check; valid near-ties at non-last positions do occur |
| Ignoring the `*` markers | Only starred placements are suspicious; unstarred duplicates are valid ties |
| Running on only one file | The script automatically scans all contest files |
| Comparing male and female results | Each file is processed independently; no cross-gender comparison occurs |
