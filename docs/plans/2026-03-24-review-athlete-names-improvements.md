# Design: review_athlete_names.py Improvements

Date: 2026-03-24

## Problem

With 2000+ contests and 100k+ athlete names waiting to merge, the current
`review_athlete_names.py` workflow is too slow:

1. **Too much noise** — soundex matches on compound last names (especially
   Arabic "Al " prefixes and Spanish compound surnames) produce obvious false
   positives that require no judgment but still take time to skip.
2. **No action path** — the script only prints variations; fixing them requires
   manually editing `review-athlete-names.dat` outside the tool.

## Goals

- Reduce soundex false positives to only plausible same-person candidates.
- Allow the user to accept/reject each match interactively and write corrections
  back to `review-athlete-names.dat` in a single session.

## Change 1: Soundex post-filter (word-level edit distance)

After soundex finds a candidate, apply an additional filter before accepting it:

**Rule:** At least one word pair — one word from each last name, both of length
≥ 3 — must have Levenshtein edit distance ≤ 2.

This handles two cases that soundex gets wrong:

| False positive | Why it fires today | Why filter drops it |
|---|---|---|
| `Al Kindy` / `Al Saif` | "Al " prefix dominates soundex | only shared word is `al` (len 2) |
| `Alamo Serrano` / `Almaguer` | coincidental soundex collision | no word pair within edit distance 2 |

Cases that should still pass through:

| True positive | Why filter keeps it |
|---|---|
| `Ortiz Guzman` / `Ortiz` | `ortiz`/`ortiz` — edit distance 0 |
| `Pastor Cueto` / `Pastor` | `pastor`/`pastor` — edit distance 0 |
| `Alvarado` / `Lvarado` | `alvarado`/`lvarado` — edit distance 1 |

Note: subset/diacritic/wordorder matches are unaffected — filter only applies
to soundex-tagged candidates.

## Change 2: Interactive review mode (`--interactive` / `-i`)

When `--interactive` is passed, after displaying each variation the script
prompts for a single-keypress decision.

### Single candidate

```
VARIATION  Ortiz Guzman, Jose
          soundex : Ortiz, Jose  (1 contests, 2011, LW)

  [M] use Master spelling  →  "Ortiz, Jose"
  [I] Incoming is canonical (flag master for update later)
  [N] Not the same athlete
  [S] Skip
```

### Multiple candidates

```
VARIATION  Alberto Cancel, Miguel
  1) soundex: Albarado Rodriguez, Miguel  (1 contests, 2012, 5L)
  2) soundex: Alvarado Rodriguez, Miguel  (1 contests, 2013, 5L)

  [1][2] select candidate, then [M]/[I]/[N]  —  [S] Skip
```

### Decision outcomes

| Key | Meaning | Action |
|---|---|---|
| M | Same person — master spelling is canonical | Queue: replace incoming name in `review-athlete-names.dat` |
| I | Same person — incoming spelling is canonical | Append to `master-corrections.txt` for later manual review |
| N | Different athletes | No change |
| S | Skip / undecided | No change |

### Write-back

At the end of the session, all `M` decisions are applied to
`review-athlete-names.dat` in a single atomic pass (read → substitute → write).
No partial writes mid-session.

`master-corrections.txt` (for `I` decisions) is appended to, not overwritten,
so multiple sessions accumulate.

## Out of scope (future UI)

- Showing full contest history per athlete during review
- Side-by-side contest comparison
- Geography / placing context

These are deferred until contest volume drops to 2–3 per week and a proper
web UI can be built.
