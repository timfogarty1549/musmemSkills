# Olympia vs. Olympia Masters — DB Reconciliation Plan

## Background

MuscleMemory has two contest titles:
- `Olympia - IFBB`
- `Olympia - Masters - IFBB`

Recent Masters Olympia results (2023, 2025) were saved under `Olympia - IFBB` instead
of `Olympia - Masters - IFBB`. This plan documents the actual event history (verified
against npcnewsonline.com/ifbbpro.com-adjacent sources: BarBend, Generation Iron,
FitnessVolt, Wikipedia) and lays out the DB changes needed to make the two titles
correctly reflect "same festival weekend" vs. "separate event."

**Rule applied:** Masters held same weekend/city as Mr. Olympia → same contest
(`Olympia - IFBB`). Masters held on a different weekend or in a different city →
separate contest (`Olympia - Masters - IFBB`).

## Verified year-by-year history

| Year | Masters Olympia location/date | Mr. Olympia location/date | Same weekend? | Currently in DB as | Correct? |
|---|---|---|---|---|---|
| 1994 | Atlanta, GA — Sept 10 | Atlanta, GA — Sept 10 | **Yes** | `Olympia - Masters - IFBB` (separate) | ❌ should be merged |
| 1995 | Atlanta, GA — Sept 10 | Atlanta, GA — Sept 10 | **Yes** | separate | ❌ should be merged |
| 1996 | Chicago, IL — Sept 20 | Chicago, IL — Sept 21 (Arie Crown Theater) | **Yes** | separate | ❌ should be merged |
| 1997 | Long Beach, CA — Sept 20 | Long Beach, CA — Sept 20 (Terrace Theater) | **Yes** | separate | ❌ should be merged |
| 1998 | not held | — | — | (no entry) | — |
| 1999 | Las Vegas, NV — Mandalay Bay | Las Vegas, NV — Mandalay Bay Arena, Oct 23 | **Yes** (same venue) | separate | ❌ should be merged |
| 2000 | Roanoke, VA (first true standalone) | Las Vegas, NV | No | separate | ✅ correct |
| 2001 | Roanoke, VA | Las Vegas, NV | No | separate | ✅ correct |
| 2002 | Lynchburg, VA | Las Vegas, NV | No | separate | ✅ correct |
| 2003 | Charlotte, NC | Las Vegas, NV | No | separate | ✅ correct |
| 2004–2011 | not held (hiatus) | — | — | (no entries) | — |
| 2012 | Miami, FL | Las Vegas, NV (Sept 27–30) | No | separate | ✅ correct |
| 2013–2022 | not held | — | — | (no entries — confirmed, no Masters placing codes present under `Olympia - IFBB` for these years) | — |
| 2023 | **Cluj-Napoca, Romania — Aug 26–27** | Orlando, FL — Nov 2–5 | **No** | merged into `Olympia - IFBB` | ❌ should be split out |
| 2024 | not held (IFBB ran "Masters World Championships" in Pittsburgh instead — a different contest, not Masters Olympia) | Las Vegas, NV | — | (no Masters data present — confirmed) | — |
| 2025 | **Tokyo, Japan — Aug 9–10** | Las Vegas, NV — Oct 9–12 | **No** | merged into `Olympia - IFBB` | ❌ should be split out |

## What's confirmed in the DB right now

- `Olympia - Masters - IFBB` has years: 1994–1997, 1999–2003, 2012. Nothing after 2012.
- `Olympia - IFBB` 2023 and 2025 contain Masters-division placing codes (`M4`, `M212`,
  `c4`, `P4`, `F4` — all confirmed Masters-only codes per divisions-reference.md)
  mixed in with the regular Open/212/Classic/Physique/Figure/Wellness placings.
  No other recent year (2013–2022, 2024) has any Masters codes under `Olympia - IFBB`.
- The 2023 and 2025 rosters cover all ~10 Masters divisions (men's Open/212/Classic
  Physique/Physique, women's Bodybuilding/Physique/Figure), matching reporting that
  "all 10 divisions" competed at both the Cluj and Tokyo shows.

## Proposed changes

### 1. Split 2023 and 2025 out of `Olympia - IFBB` into `Olympia - Masters - IFBB`

For each of 2023 and 2025:
- Move every result whose placing code starts with `M4`, `M212`, `c4`, `P4`, or `F4`
  from the `Olympia - IFBB` contest/year record to a new `Olympia - Masters - IFBB`
  contest/year record.
- Leave the non-Masters placings (`OP`, `U212`, `CL`, `PH`, `FI`, `BB`, `WC`) in
  `Olympia - IFBB` untouched.
- Add location data to `contest_locations.json` for `Olympia - Masters - IFBB`:
  - 2023: Aug 26–27, 2023 — BT Arena, Cluj-Napoca, Romania
  - 2025: Aug 9–10, 2025 — Tokyo, Japan (venue TBD)

### 2. Merge 1994, 1995, 1996, 1997, 1999 from `Olympia - Masters - IFBB` into `Olympia - IFBB`

For each of those five years:
- Move every result currently under `Olympia - Masters - IFBB` for that year into the
  matching `Olympia - IFBB` year record, preserving placing codes as-is (they already
  use the Masters-specific prefixes, e.g. `M6`, `M4`, `M5`, so no collision with the
  main-card codes for those years).
- After the move, `Olympia - Masters - IFBB` should have no entries for 1994–1997 or
  1999.
- This is the larger, more disruptive change — it rewrites contest attribution for
  decades-old placings. **Confirm before executing** — may be worth doing separately
  from the 2023/2025 fix, or not at all if there's a reason the DB has kept them apart
  historically (e.g. a source-material or scoring distinction not captured by "same
  weekend").

### 3. Leave untouched

2000–2003 and 2012 are already correctly separate — no action.

## Open items / things to verify before executing

- Exact 2025 Masters Olympia venue name (city/dates confirmed: Tokyo, Aug 9–10, 2025).
- Whether any consumers (e.g. UI, exported flat files) hardcode assumptions about
  which years exist under which contest title.
- Confirm on npcnewsonline.com/ifbbpro.com directly (per user instruction these are
  the definitive sources) rather than relying solely on secondary sites — the above
  was built from BarBend/GenerationIron/FitnessVolt/Wikipedia since those already had
  clear date/city detail matching what's needed.

## Not yet done

This is a plan only — no database writes have been made. Awaiting explicit
go-ahead on scope (just the 2023/2025 split, or also the 1994–1999 merge) before
executing.
