---
name: musmem-extract-distinct-athletes
description: Extract athlete names from semicolon-delimited MusMem contest result files and create candidate variant groups for cleanup. Use when working with files like covid-male.dat or bb_male.dat where column 1 is athlete name and column 2 is year, especially to compare one or two files, apply optional year filters, count appearances, and generate TSV review groups for likely same-person name variants.
metadata:
  short-description: Extract and compare MusMem athlete names
---

# MusMem Extract Distinct Athletes

Use this skill for repeatable name-cleanup passes over MusMem semicolon-delimited result files.

## Workflow

1. Run the bundled script:

```bash
python3 /Users/timfogarty/workspace/skills/musmemSkills/musmem-extract-distinct-athletes/scripts/extract_distinct_athletes.py
```

The alias `musmemDistinct` has been added to `.bash_profile` for this command.

2. Answer prompts for one or two input files.
   - `Input data file path` means the MusMem `.dat` file to process.
   - Input files must be semicolon-delimited.
   - Input file paths may be absolute, `~`-relative, or relative to `/Users/timfogarty/workspace/musmem/data`.
   - Column 1 is the athlete name.
   - Column 2 is the contest year when using a minimum-year filter.

3. For each source, the script tracks distinct names and occurrence counts in memory.

4. The script writes a candidate-group TSV. Columns are:
   - `group_id`
   - `name`
   - one count column per source, named `count_<label>`

The default folder for candidate-group TSV files is `/Users/timfogarty/workspace/musmem/distinct`.

## Defaults

For the common current task, use:

- Source 1 file: `bb_male.dat`
- Source 1 label: `bb_male`
- Source 1 minimum year: `2010`
- Source 2 file: `prelim/covid-male.dat`
- Source 2 label: `covid_male`
- Source 2 minimum year: blank
- Candidate group output: `/Users/timfogarty/workspace/musmem/distinct/bb_male-covid_male-variant-groups.tsv`

## Review Guidance

The grouping is intentionally a candidate generator, not an automatic canonicalization step. Review before applying corrections. It catches punctuation/accent variants, close spelling edits, adjacent transpositions, common nickname/full-name variants, and initial/expanded-name cases when surnames match.

## Variant Group Logic

The script builds candidate pairs first, then turns connected pairs into `group_id` groups.

Name normalization for matching:

- Removes accents/diacritics.
- Case-folds names.
- Ignores apostrophes and similar quote marks.
- Treats non-alphanumeric punctuation and spacing as separators.

Candidate pair rules:

- **Punctuation/spacing/accent only**: names with the same compact normalized form are paired.
- **Same tokens in different order**: names with the same full normalized token set, regardless of comma placement or token order, are paired. This catches cases like `a, b` and `b, a`, and requires all three tokens to match for cases like `a b, c` and `c a, b`.
- **Three-plus shared tokens**: when one name has four or more unique tokens and the other name's three-or-more unique tokens are contained within it, the names are paired. This catches cases like a dropped surname/given-name token while avoiding broad partial-overlap matches.
- **Same surname; given-name variant**: pairs names with the same normalized surname when the given name is a known nickname/full-name variant, such as `Tim`/`Timothy`.
- **Same surname; given-name typo/transposition**: pairs names with the same normalized surname when the compact given names are within a small Damerau-Levenshtein edit distance.
- **Same surname; initial/expanded given-name**: pairs names with the same normalized surname when one given-name form appears to be an initial or shorter expansion of the other.
- **Same given name; surname typo/transposition**: pairs names with the same normalized given name when the compact surnames are within a small Damerau-Levenshtein edit distance.
- **Full name typo candidate**: pairs names in the same surname/given initial bucket when the full normalized name is within a small edit distance.

For two-source comparisons, the final TSV only includes groups that contain at least one name from each source. For one-source runs, all generated candidate groups are written.
