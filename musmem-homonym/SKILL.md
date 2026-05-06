---
name: musmem-homonym
description: Use when scanning bodybuilding contest data files for athlete names that likely represent two different people — identified by large year gaps, pre-1995 athletes reappearing post-2010 outside 60+ categories, or open-only category profiles spanning a large gap.
---

# MuscleMemory Homonym Detection

Scans one or more semicolon-delimited `.dat` files for athlete names that likely represent two different people. Input is interactive — the script prompts for file paths at runtime, not as CLI arguments.

## Usage

Copy the script to `/tmp/` first (required by permission rules), then run:

```bash
cp ~/workspace/skills/musmemSkills/musmem-homonym/scripts/homonym_detector.py /tmp/
python3 /tmp/homonym_detector.py
```

The script prompts interactively for one or more file paths. Press Enter on a blank line to finish. Paths may be absolute, `~`-relative, or bare filenames resolved under `~/workspace/musmem/data`. Names with only one appearance are not flagged.

## Detection

Names with a gap ≥ 10 years are flagged and assigned a confidence level:

- **High**: pre-1995 appearance + post-2010 appearance outside 60+ categories (Pattern B), OR gap with no masters codes in the late cluster
- **Medium**: gap where the late cluster contains masters division codes — suggests the athlete aged into masters competition
- **Low**: gap with no open/non-masters codes anywhere — masters-only career throughout

The script prompts for a minimum confidence level. All names at or above that level are shown in a single alphabetically sorted list.

## Report Format

Year ranges use en-dashes. Single years appear without a dash.

```
Smith, John; 1984–1990, 2022–2024
Jones, Bob; 1988–1990, 2019–2023

42 names flagged
```
