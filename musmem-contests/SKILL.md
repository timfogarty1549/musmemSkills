---
name: musmem-contests
description: Use when checking bodybuilding contest websites for new results not yet in the MuscleMemory database, or when generating flat files of contest results for import into musclememory.net.
---

# MuscleMemory Contest Checker

Checks bodybuilding org websites for contests missing from the MuscleMemory database and generates flat files for import via `format.php`.

## Quick Reference

| Phase | What Claude does | Reads from | Writes to |
|-------|------------------|------------|-----------|
| 1 — Discovery | Fetch DB + scrape listing → identify target contests → fetch individual pages | — | `.page_cache/` |
| 2 — Extract | Read cached pages → parse results → write flat files | `.page_cache/` | `1-incoming/` |
| 3 — Normalize Athletes | Normalize athlete names (Last, First / East Asian format) | `1-incoming/` | `2-normalize-athletes/` |
| 4 — Normalize Contest Names | Rename files + `t` lines to canonical MuscleMemory titles | `2-normalize-athletes/` | `2-normalize-athletes/` (in-place) |
| 5 — Format | Run flat files through format.php → write `.out` files | `2-normalize-athletes/` | `3-formatted/` |
| 6 — Review | Interactively resolve `<<<<` flagged names in `.out` files | `3-formatted/` | `4-reviewed/` |
| 7 — Complete | Verify athlete names against master, write corrected `.out` | `4-reviewed/` | `5-completed/` |
| 8 — Append | Append files to gender staging `.dat` files | `5-completed/` | `6-appended/` |

**`0-later/`** — holding area for files that can't be processed yet (missing data, illegible scans, etc.)

**Files are never deleted or moved from a source folder.** Each step reads from N-1 and writes to N.

---

## Phase 1: Discovery

> **Python scripting rule:** Never use `python3 -c "..."` or `python3 - <<'PYEOF'` heredocs. Always write scripts to `/tmp/script.py` using the Write tool, then run `python3 /tmp/script.py`. This applies to all curl-piped processing and any other Python work in this phase.

**Goal:** Identify which contest pages need to be fetched, then fetch and cache them. No extraction happens in this phase — output is pages in `.page_cache/` only.

**This phase is triggered in two ways:**
- *"Check website X for ORG contests for years Y1–Y2 that are not already in the MuscleMemory database"* — target contests are those on the listing page but absent from the DB.
- *"Check website X for ORG contests for years Y1–Y2 for missing divisions"* — target contests are those already in the DB for those years; their pages are cached so Extract can compare DB divisions against what's on the page.

### 1. Fetch the MuscleMemory DB for the target year(s)

**Use the local node server, not musclememory.net/.org directly.** The public API now requires a signed request and returns `{"success":false,"error":"Invalid or missing request signature"}` for any unsigned call — the old browser-UA workaround no longer works. The local server (`~/workspace/node/musmem`) serves the same endpoints on `localhost:3000` with no signature required.

Before any API call, check that the local server is up (`curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/contests/2025` → `200`). If nothing is running on port 3000, stop and ask the user to start the local musmem server — do not start it yourself, and never fall back to musclememory.org/.net.

```
GET http://localhost:3000/api/contests/{year}
```

Returns `data.contests` — an array of strings in `"Contest Name - ORG"` format.

If checking multiple years, call once per year.

### 2. Scrape listing pages and identify target contests

Listing pages are lightweight and do not need to be cached, but **always re-fetch the listing fresh for this check** — never diff against a previously-saved listing snapshot or infer "already handled" from whether a contest's individual page happens to already exist in `.page_cache/`. A cached individual page only means it was fetched at some point, not that it was checked against the DB or extracted — pages fetched in an earlier, incomplete pass will sit in the cache indefinitely otherwise and silently fall out of consideration. Every run compares the full current listing against the DB directly.

See `sources-reference.md` for each source's listing URLs, org slugs, User-Agent, and name normalization rules.

Each source has its own normalization rule — see `sources-reference.md`. For npcnewsonline.com: strip the leading org prefix, append ` - {ORG}` (e.g., `IFBB Arnold Classic` → `Arnold Classic - IFBB`).

**Before concluding a contest is "missing," reconcile its name against the mapping doc — never rely on a naive normalized-string comparison alone.** npcnewsonline's title and the MuscleMemory DB's canonical title frequently differ (sponsor names added/dropped, word order swapped, "Championships" added/dropped, entirely different brand name for the same event) — a plain string-equality check against the DB produces both false "missing" reports (the contest is already tracked under different wording) and false negatives (a reworded 2026 entry silently shadows a real gap).

- **`../docs/contest-name-mapping.md`** — npcnewsonline title → MuscleMemory title, for IFBB pro shows.
- **`../docs/npc-contest-name-mapping.md`** — same, for NPC amateur shows.

For each contest on the listing:
1. Look up its exact npcnewsonline title (with org prefix, e.g. `Chicago Pro - IFBB`) in the relevant mapping doc.
2. If found with `type: ignore` → already reviewed and deliberately excluded (e.g. lower-tier/duplicate show). Not missing, no further action.

   **Excluded-only is a per-year judgment, not a per-contest one.** A contest/year is skipped when *that year's* event has no division we track (Bikini-only, Fit Model-only, Wellness-only, etc.). If an earlier year was Bikini-only but this year adds e.g. Men's Physique, this year gets added for the tracked divisions only. So a newly-seen show that is currently excluded-only should get a real target title in the mapping doc (not `type: ignore`) — it will then surface each year as "missing" and the Step 3 division check will mark it excluded-only until a tracked division appears. Reserve `ignore` for rows that should never be tracked regardless of divisions (duplicates, split-out bikini-only listings of a show tracked elsewhere, etc.). Confirmed by user 2026-09-29.
3. If found with a real target title → check that title against the DB for the target year(s) (`GET /api/contest/years?name=...`, not just the flat `/api/contests/{year}` list, since the exact string must match). Present in DB → not missing. Absent → genuinely missing this year, proceed to fetch its page.
4. If not found in the mapping doc at all → don't assume it's new. Cross-check the full org listing (`GET /api/org?name={ORG}`) for a reworded match before concluding it's untracked. Once resolved (whichever direction), **add the new row to the mapping doc** so the next run doesn't redo this work — do not leave a name unresolved and unrecorded.
5. If genuinely no match exists anywhere → treat as a never-tracked contest, same judgment call as any new-contest decision elsewhere in this skill (confirm with the user before adding, per the `musclemania.com`/`ukbff.co.uk` precedent in `sources-reference.md`) rather than silently marking it new or ignore in the mapping doc.

- **Missing contests trigger:** contests resolved as genuinely missing per the above, for the target year(s).
- **Missing divisions trigger:** find contests in the DB for those years (listing page used only to get their individual page URLs).

### 3. Fetch individual contest pages → store in `.page_cache/`

For each target contest, fetch its individual results page and store it in the local page cache. See `sources-reference.md` for individual contest URL patterns.

**Cache location:** `~/workspace/musmem/.page_cache/`  
If a page is already cached, check its fetch date — results pages get updated as results are posted, so a cache older than a few weeks should be re-fetched rather than trusted as-is for a missing-contest check (extraction from a fresh cache is still fine to skip re-fetching, per Phase 2).

**After fetching, check whether the page actually has a trackable division before reporting it as actionable.** A contest can be genuinely missing from the DB and still have nothing to extract yet — e.g. its results page currently shows only Bikini/Wellness/Fitness/Fit Model (all excluded categories), because the real divisions' results haven't been posted yet or the show only ran excluded categories this cycle. Scan for `<h2 class="division-title">` sections and note which ones fall outside the standard exclusion list (Bikini, Wellness, Fitness, Fit Model, Novice, etc.). A contest with no non-excluded division yet should still be cached, but flagged as "excluded-only — nothing to extract" rather than listed alongside contests ready for Phase 2.

### 4. Report

List the contests whose pages were cached (newly fetched vs. already cached), note any fetch failures, and separate "trackable now" contests from "excluded-only, nothing to extract yet" ones (see division check above).

---

## Phase 2: Extract

**Goal:** Parse contest pages from `.page_cache/` and write flat files to `1-incoming/`. No HTTP requests — all pages must already be cached by Phase 1.

This is where most of the interactive work happens: slug mappings, division structure, and name cleaning require iteration. Because extraction reads from cache, fixes can be applied and re-run without re-hitting the web.

### 1. Read pages from cache

Pages are read from `~/workspace/musmem/.page_cache/`. If a page is missing from cache, report it and stop — do not fetch it. Run Phase 1 first to populate the cache.

### 2. Extract results

Each page shows divisions with numbered placings. See `sources-reference.md` for source-specific notes (name order, country availability, etc.).

**PDF sources and any non-slug-structured HTML:** The division/class mapping rules in this section (steps below) describe npcnewsonline.com's `data-slug`-driven structure specifically. For PDFs or any other source without that structure — see `../docs/division-recognition.md` for the source-agnostic method (base division keywords, age/size qualifier resolution, letter-class ordering, overall-entry rules, pairs/team exclusion, and the same "stop and report" discipline for unrecognized patterns). Division *codes* are identical either way — only how you identify which code applies differs by source.

**Name cleaning rules** (applied to every athlete name extracted from HTML):

1. **Strip HTML and unescape entities** — remove all tags, unescape `&amp;` etc.
2. **Repair mojibake UTF-8** — cp1252 bytes misread as Unicode → translate via `_CP1252_TO_LAT1` table, then encode as latin-1 and decode as UTF-8. On failure (non-Latin script), keep original.
3. **Normalize curly quotes/apostrophes** — `'` / `'` → `'`; `"` / `"` → `"`
4. **Strip periods** — remove all `.` characters (e.g. `Jr.` → `Jr`, `D.J.` → `DJ`)
5. **Normalize em-dash spacing** — ` - ` (space-hyphen-space) → `-`
6. **Strip trailing â** — a name ending with `â` is a stray artifact from the NPC website; remove it
7. **Remove spaces around apostrophe** — `" ' "` → `"'"` (e.g. `O ' Brien` → `O'Brien`)
8. **NFC normalization** — compose decomposed diacritics (NFD n + U+0303 → ñ)
9. **Per-token normalization** (applied to each whitespace-separated token):
   - Title-case each token
   - Capitalize the letter after `'` — e.g. `O'brien` → `O'Brien`
   - Capitalize the letter at index 2 for tokens starting with `Mc` — e.g. `Mcmillan` → `McMillan`, `Mcdonald` → `McDonald`
   - Non-trailing `II` → `Il` (middle-name position is more likely an OCR error for the name "Il")
   - Two-letter token where both letters are consonants → split into initials — e.g. `DJ` → `D J` (exceptions: `Jr`, `Sr`, `St` — Saint particle; `Ng` — surname; and any such token ending in `y`, e.g. `Ly`/`Ty`/`Dy` — short Vietnamese/Filipino/Cambodian names, confirmed via "Peter Ly", "Ty White", "Michael Dy", "Benghap Ty". Genuine initials-as-name like `JC`/`Bj`/`JT`/`TJ`/`Pj` never end in `y`, so this split stays safe for those.)
   - Trailing token that is `II`, `III`, or `IV` (case-insensitive) → uppercase Roman numeral; higher values not uppercased (`Xi`, `Vi`, etc. are valid Chinese given names)
   - First token `Dr` (case-insensitive) → remove it (honorifics are not recorded in the database)
10. **Collapse whitespace** — multiple spaces → single space, strip leading/trailing
11. **Report non-Latin scripts** — if the name contains Cyrillic, Arabic, or CJK characters, print a warning (do not modify the name)

These rules are implemented in `clean_name()` in `scrape_all_phase2.py`.

### 3. Write the flat file

Output format for `format.php` — one contest per file:

```
y 2025
t Arnold Classic - IFBB
c OP
1 Derek Lunsford
2 Samson Dauda
3 Andrew Jacked
----
c CL
1 Ramon Rocha Queiroz
2 Mike Sommerfeld
98 Some Athlete
98 Another Athlete
```

**Format rules:**
- `y {year}` — set year
- `t {Contest Name - ORG}` — set contest title (MuscleMemory format)
- `c {code}` — division code from `en.json` DIVISIONS (see `../docs/divisions-reference.md`)
- `----` — separator between divisions
- Competitor lines: `{placing} {First Last}` (no prefix character)
- Names are "First Last" order (npcnewsonline.com format) — do NOT set `l 1`
- Leave `l` flag unset (defaults to `l 0` = first-last order)

**Excluded divisions — skip entirely, do not write:**
- Bikini (all age groups)
- Wellness (all age groups)
- Fitness (all age groups)
- Novice (all categories)
- Beginner (all categories)
- True Novice (all categories)
- First Timer (all categories)
- Challenger (all categories) — synonymous with Novice (confirmed via 2021 South American Amateur Championships, which uses "Challenger" for its entry-level/novice bracket)
- Pairs/Team categories (Mixed-Pairs, Fit-Pairs, Duo, Couple, or any category where a single placing represents two or more athletes) — the database has no way to represent a multi-athlete entry. See `../docs/division-recognition.md` Step 5.

**Unknown sub-class slug → stop and report an error:**
When processing a division that has sub-classes (multiple `data-slug` entries), every sub-class slug must map to a known division code or be explicitly in the exclusion list. If a slug is encountered that is neither mappable nor excluded, **stop immediately and report the unknown slug with its division context** — e.g. `"masters-class-a" in MEN'S BODYBUILDING — unknown slug, cannot continue`. The user will then decide whether to add a new code to en.json/divs.php or add the slug to the exclusion list. Never silently skip or fall back to the parent code.

This same discipline applies to PDF and other non-slug sources — an unrecognized division name or class qualifier must stop extraction and get reported, never silently default to a generic/outer code. See `../docs/division-recognition.md` Step 6. (Silently defaulting unmapped classes to a bare division code is exactly what produced the division-code errors in the 2022 European Amateur Championships female-file extraction.)

**Standing exception — geographic/local-residents sub-competitions:** some contests run a real, separately-judged "residents only" sub-competition alongside the main open classes, scoped to a state, county, or "hometown" — confirmed via `colorado-*` (Colorado State - NPC: parallel weight classes + overall, overlapping-but-not-identical roster vs the main open classes) and `etowah-county`/`hometown` (Alabama State Championships - NPC: real 1-6 entrant classes reused across Men's and Women's Bodybuilding). These are never a MuscleMemory-tracked category (no "state/county residents" code exists) and the user has confirmed this call once — **do not stop and ask again for this specific pattern.** When an unknown slug (a) has real placings (not a stray glitch — verify via a quick roster check, same as any unknown slug), (b) doesn't match any standard division vocabulary (weight/age/class-letter/kg), and (c) clearly references a place name, "hometown", or residency concept rather than a competitive tier, add it straight to the exclusion list (`SKIP_SLUG_RE` in `fix_subdivisions.py`) with a comment documenting the contest/year it was confirmed against, and continue extraction — note it in the results summary instead of blocking on it. Every other "stop and report" situation (new age brackets, new class letters, structurally ambiguous slugs) still requires stopping and asking as normal.

**Explicitly excluded slugs** (skip, write nothing):
- `overall-winner*`, `earned*`, `comparison` — structural markers (overall winner extracted separately)
- `novice`, `novice-*`, `*-novice`, `true-novice*`, `beginner`, `beginner-*`, `begginer*` (typo variant) — excluded beginner/novice categories
- `first-timer*`, `first-timers*` — excluded categories
- `regional`, `regional-*`, `*-regional` — regional-tier slugs (only pro-qualifier tier is included)
- `natural`, `natural-*` — natural/tested division variants (not tracked)
- `local`, `local-*` — local-level subdivisions
- `star-category`, `armed-forces`, `military`, `first-responder`, `hero`, `heroes`, `uniform`, `battle-for-the-belt` — specialty/tribute divisions not tracked, even when placed athletes are present (`military` confirmed via 2021 Missouri State Championships, same category as armed-forces) (confirmed via 2025 Emerald Cup Open — `hero` has real 1st–4th placings, excluded anyway for consistency with armed-forces/first-responder; `uniform` confirmed via 2014 Alabama State Championships — a "Best Uniform" style award equivalent to armed-forces/police/fire tribute categories; `battle-for-the-belt` confirmed via 2021 Georgia State Championships — a novelty title-match format, no placings posted anyway that year)
- `guest-poser` — non-competitive single entrant, no placing number
- `mr-*` — historical title slugs (e.g. `mr-universe`)
- Digit-only slugs (e.g. `1`, `2`) — data errors on source page
- `colorado-*` (Colorado State - NPC), `etowah-county`/`mr-etowah-county`/`ms-etowah-county`/`hometown`/`mr-northeast-alabama`/`ms-northeast-alabama` (Alabama State Championships - NPC), `georgia-state`/`georgia-state-*` (Georgia State Championships - NPC, 2020 only) — real, multi-entrant geographic-residents-only sub-competitions running alongside the main open classes; excluded as untracked categories per user decision (no MuscleMemory code exists for a "state/county/region/hometown residents" bracket). See the standing exception above — new slugs matching this same pattern get added here directly, no need to stop and ask again. **Blanket-exclude by prefix, even when a bare (non-prefixed) sibling slug is missing for a given class that year** — confirmed via Georgia State Championships 2020: a missing bare sibling just means nobody entered the regular open division for that weight class that year, not that the `georgia-state-*` entrants should be promoted into it. Don't try to be clever and map an unpaired `georgia-state-X` to the plain `X` code.

**`open` slug — context-dependent mapping:**
The slug `open` is handled before the exclusion list:
- In **Men's Bodybuilding (OP)**: if the page also has an Under 212/208/202 section → use `OP`; otherwise (only one class) → use `BB`
- In all other divisions (CL, PH, FI, BB) → use the outer code as-is

**`pro-qualifier-*` prefix — strip and treat as bare slug:**
Strip the `pro-qualifier-` prefix, then map the remainder normally:
- `pro-qualifier-heavyweight` → `heavyweight` → weight code lookup
- `pro-qualifier-class-a` → `class-a` → maps normally
- `pro-qualifier` bare → maps to outer code

**Bare letter slugs `a`–`h` — treat as `class-a` through `class-h`:**
Single-letter slugs are shorthand for class slugs (e.g. bare `a` = `class-a`).

**`senior` → `MA`:** The slug `senior` maps to Masters Bodybuilding Open (`MA`), same as bare `masters` in Bodybuilding.

**`grandmasters` — division's 50+ code:** Confirmed via 2018 Michigan State Championships as a distinct, higher age bracket from the bare `masters` slug — both appear as separate sub-divisions on the same page in Men's Bodybuilding, Figure, Men's Physique, and Men's Classic Physique, with no age number given. Maps to the division's 50+ code per user decision: `OP`/`BB` → `M5`, `FI` → `F5`, `PH` → `P5`, `CL` → `c5`. Stop and ask before extending to a division not yet confirmed.

**`unique` / `Única` / `class` bare → outer code:** These appear on some pages as an alternative name for the open class.

**`adaptive` / `special` → `Hs` (Physically Challenged Standing).**

**`wheelchair` / `wheel-chair` → `WC` (Wheelchair).**

**Single primary sub-division → collapse to outer code:**
If a major division (OP, BB, CL, PH, FI) has exactly one "primary" sub-division — meaning one height/weight class sub-division, excluding masters, junior, and teen — replace that sub-division code with the outer division code and print a flag.

- Primary sub-division codes: `Ba`–`Bg` (OP/BB height), `SW`/`HW`/`LH`/`MW`/`WW`/`BW`/`LW`/`ULW` (OP/BB weight), `Pa`–`Ph` (PH), `Ca`–`Ch` (CL), `Fa`–`Fh` (FI), `CBa`–`CBf` (CB — Classic Bodybuilding, confirmed via 2023 IFBB North American Championships), `MUPa`–`MUPd` (MUP — Muscular Physique)
- Example: Women's Bodybuilding with only `class-b` → write `c BB` not `c Bb`
- Example: Physique with only `class-c` (but also masters/junior sections) → write `c PH` not `c Pc`
- If an overall winner entry already occupies the outer code, flag it and leave both as-is.

**Overall winners — extract in Phase 2, not deferred:**
Overall winner entries must be written directly into the Phase 2 flat file. Do not defer them to a separate fix_subdivisions pass.

On npcnewsonline.com, overall winners appear as `<a data-parent="overall-winner-*" data-person="yes">` links immediately after the `<div data-slug="overall-winner-*">` element. They have an empty `<span>` (no placing number). Write them as `c {parent-code}` + `0 {Name}`:

```
c OP
0 M Sarhan
```

The parent code is the division's outer code: `OP` for Men's Bodybuilding, `BB` for Women's Bodybuilding, `CL` for Classic Physique, `PH` for Men's Physique, `FI` for Figure, etc.

**Country code on placed-competitor lines, when the source provides one:** Write `{placing} {First Last} ({CountryName})` — the country name in parens at the end of the line, title-cased and matching format.php's `$countryCode` table where possible (e.g. `Mexico` not `México`, `Brasil` or `Brazil` both work). format.php's `extractCountry()` parses the parenthetical, converts known names to 2-letter codes, and flags unrecognized ones with `*******` for review — so it's fine to write the country name exactly as extracted even if it's not a perfect table match; unmatched ones surface in Phase 5 review rather than blocking extraction. This applies to any source that provides a country per competitor (PDFs, NAC, etc.) — npcnewsonline.com has none, so this only applies to PDF/NAC-style sources. Confirmed via 2023 IFBB North American Championships (initially missed, then corrected).

**No country code on `0` (overall) lines:** Write `0 {Name}` only — never `0 {Name} (CCC)` — even on sources (PDFs, NAC, etc.) that do provide a country for the overall winner and where placed-competitor lines in the same file do include it. This applies universally, regardless of source.

**Only write an overall entry when the source has an explicit overall/combined section for that division.** Never infer one from the winner of a class (e.g. the winner of the largest/final class in a division is not automatically its overall winner) — many divisions don't have a combined overall at all. See `../docs/division-recognition.md` Step 4.

**No overall entry when the division has no subdivisions to compare:** If a division's only class already collapsed to the bare outer code (see "Single primary sub-division" above), an "Overall" section for that same division adds no new information — its winner is already placing `1` in the bare-code block. Skip the `0` line entirely in this case; do not write a second block under the same code. Only write the `0` overall line when the division actually has 2+ sub-codes (letter classes, weight classes, age brackets) being compared. Confirmed via 2023 IFBB North American Championships ("Overall Women's Bodyfitness" dropped — Bodyfitness had only one bare-`FI` class that year).

**Overall rounds in scored competitions (IFBB Amateur, etc.):** When a contest has a separate Overall round with full judged placings (e.g. Men's Physique Overall, Classic Bodybuilding Overall), only the **1st place finisher** is recorded. Write as `c {parent-code}` + `0 {Name}`. Height/weight/height-class codes (Pa, Pb, Ca, Cb, 70kg, etc.) roll up to the top-level division code for the overall entry:
- Men's Physique Overall → `c PH` + `0 {name}`
- Classic Physique/Bodybuilding Overall → `c CL` + `0 {name}`
- Figure Overall → `c FI` + `0 {name}`
- Men's/Women's Bodybuilding Overall → `c OP` / `c BB` + `0 {name}`

**Masters-specific overall rounds** (e.g. "Overall Master Men's Bodybuilding", comparing only the masters age-bracket winners against each other, separate from the plain "Overall Men's Bodybuilding") roll up to the masters-tier parent code, not the general open code:
- Overall Master Men's/Women's Bodybuilding → `c MA` + `0 {name}`
- Overall Master Men's Physique → `c MP` + `0 {name}`
- Overall Master Classic Physique → `c mc` + `0 {name}`
- Overall Master Classic Bodybuilding → `c CBM` + `0 {name}`
- Overall Master Figure/Bodyfitness → `c FM` + `0 {name}`

Confirmed via 2023 IFBB North American Championships and 2023 IFBB European Amateur Championships.

**General rule — an overall (`0`) belongs to the parent of the sub-codes it compares.** Include a sub-group overall whenever the source has one and the subdivisions under it exist. It rolls up exactly one level:
- `4H-1`, `4M-1`, `4L-1` (masters 40 weight classes) → masters-40 overall is `M4-0`
- `M4-0` or `M4-1` plus `M5-0` or `M5-1` (multiple masters age brackets) → masters overall is `MA-0`
- Same pattern in every division: `P4a`/`P4b` → `P4-0`; `c4a`/`c4b` → `c4-0`; `F4a`/`F4b` → `F4-0`

**A code can never have both a `0` and a `1`** (or any real placing). If the overall's parent code also has real placings, there was nothing to compare, so drop the `0` line. `parse_contest()` enforces this and prints a `FLAG` when it drops one. Rule stated by user 2026-10-04.

On npcnewsonline these slugs look like `masters-40-overall`, `masters-40-overall-winner`, or, on pro-qualifier pages, `masters-40-overall-winner-earned-pro-card`. The last form was previously swallowed by the `earned` skip pattern; it's now routed to the overall handling. Confirmed via 2026 Canadian Natural Pro Qualifier - CPA.

**Cross-bracket "Junior section" overalls — skip entirely:** Some IFBB sources label a combined Teen(16-20)+Junior(21-23) age-bracket section "Junior" throughout, including its overall round (e.g. "Junior Men's Physique OVERALL" comparing the Teen winner against the Junior winner(s)). Since Teen and Junior are separate code families with no shared parent code, do not write a `0` line for these — skip the overall round entirely rather than guessing a parent code. Confirmed via 2023 IFBB European Amateur Championships (Junior Men's/Women's Physique, Bodybuilding, Classic Physique, and Bodyfitness overalls all skipped for this reason).

**`junior` and `teen` slugs — context-dependent codes:**

| Division | `junior` → | `teen` / `teenage` / `teenager` → |
|----------|-----------|----------------------------------|
| Bodybuilding (OP/BB) | `JR` | `TE` |
| Classic Physique (CL) | `CJ` | `ct` |
| Men's/Women's Physique (PH) | `PJ` | `PT` |
| Figure (FI) | `FJ` | `FT` |

**Bare `collegiate` slug** → `ED` in Bodybuilding (OP/BB), `EP` in Physique, `EC` in Classic Physique, `EF` in Figure (`COLLEGIATE_CODES` in `fix_subdivisions.py`; `EC` was added 2026-10-04, confirmed via 2025/2026 Atlanta Classic - NPC). This applies when a collegiate class sits inside an open show. On the combined "Teen Collegiate & Masters Nationals" page the collegiate classes instead go to their own contest, `Collegiate Nationals - NPC`, with the prefix stripped (plain `CL`/`Ca`/`OP`…), matching how 2019 was stored.

**IFBB "Junior section" age brackets — 16-20 = Teen, 21-23 = Junior:** Some IFBB sources (e.g. European federation results) present Teen and Junior as two age brackets under one umbrella heading ("Junior Men's Physique 16-20 Years", "...21-23 Years") rather than as separately-labeled Teen/Junior divisions. Map by age, not by the umbrella heading: **16-20 Years → Teen codes** (`TE`/`PT`/`CBT`/`ct`/`FT`), **21-23 Years → Junior codes** (`JR`/`PJ`/`CBJ`/`CJ`/`FJ`). Where the 21-23 bracket further splits by height/weight, use that division's existing Junior letter-class slots (e.g. `PJa`/`PJb`). Confirmed via 2023 IFBB European Amateur Championships. See also "Cross-bracket 'Junior section' overalls" below for how the combined overall round is handled.

**Junior weight sub-classes** — `junior-{weight}` slugs:

| Slug | Code | | Slug | Code |
|------|------|-|------|------|
| `junior-heavyweight` | `JH` | | `junior-lightweight` | `JL` |
| `junior-light-heavyweight` | `Jl` | | `junior-bantamweight` | `JB` |
| `junior-middleweight` | `JM` | | `junior-flyweight` | `JF` |
| `junior-welterweight` | `JW` | | `junior-light-flyweight` | `Jf` |
| `junior-tall` | `Jt` | | `junior-medium` | `Jm` |
| | | | `junior-short` | `Js` |

**Junior class letters** — `junior-class-a` through `junior-class-d` (also `junior-a` through `junior-d`):

| Division | `-class-a` | `-class-b` | `-class-c` | `-class-d` |
|----------|-----------|-----------|-----------|-----------|
| Classic Physique (CL) | `CJa` | `CJb` | `CJc` | `CJd` |
| Men's Physique (PH) | `PJa` | `PJb` | `PJc` | `PJd` |
| Figure (FI) | `FJa` | `FJb` | `FJc` | `FJd` |

**Masters age codes** — base code by division and age:

| Age | OP / BB | Classic (CL) | Physique (PH) | Figure (FI) |
|-----|---------|--------------|---------------|-------------|
| 30+ | — | — | `P3` | — |
| 35+ | `M3` | `c3` | `P35` | `f3` |
| 40+ | `M4` | `c4` | `P4` | `F4` |
| 45+ | `45` | `c45` | `P45` | `f4` |
| 50+ | `M5` | `c5` | `P5` | `F5` |
| 55+ | `55` | `c55` | `P55` | `f5` |
| 60+ | `M6` | `c6` | `P6` | `F6` |
| 65+ | `m6` | — | — | `F65` |
| 70+ | `M7` | `c7` | `P7` | `F65` |
| 80+ | `M8` | — | — | — |
| 90+ | `M9` | — | — | — |

**Masters age + class/weight combos** — valid and common. The code is derived by combining the base age code with the class letter or weight suffix:

- `masters-[over-]40-class-a` in PH → base `P4` + letter `a` = `P4a`
- `masters-[over-]35-class-b` in CL → base `c3` + letter `b` = `c3b`
- `masters-[over-]40-class-c` in FI → base `F4` + letter `c` = `F4c`
- `masters-[over-]45-heavyweight` in OP → age prefix `45` + `H` = `45H`
- `masters-[over-]40-tall` in OP → age prefix `4` + `t` = `4t`
- Bare letter suffix works same as `class-X`: `masters-40-a` in CL = `masters-40-class-a` → `c4a`

**Did not place → placing 98:**
When the highest placing number repeats within a division (e.g., multiple athletes all listed as 16th), replace ALL of those tied entries with placing `98`.

```
# Example: 15 placed athletes, then many tied at 16 → all become 98
15 Rubiel Mosquera
98 Akim Williams
98 Brett Wilkin
98 Chenglong Shen
```

**Do not convert a genuine last-place finish to 98.** The 98 rule only applies when the *same* highest placing number repeats (a true tie/uncalled-out bucket). If a division has N competitors with sequential unique placings 1–N (including when N happens to be a round number like 15 or 16), the last one is a real placing — leave it as-is. Confirmed via 2018 Arnold Classic South America, where several classes coincidentally end at a unique, non-repeated 16th place.

**Disqualified (doping) → placing 99:** When a source marks an entrant `DQ*`/"Disqualified due to Anti-Doping Rules violation" (their numeric placing has been struck, sometimes with a note like "Initially in 2nd place"), write them at placing `99` rather than their original pre-DQ rank or omitting them. Confirmed via 2023 IFBB European Amateur Championships.

**Did Not Compete (DNC) → exclude entirely:** An entrant marked `DNC` registered but never competed — there is no performance to record. Unlike an unranked-but-competed entrant (→ 98) or a disqualified one (→ 99), omit DNC entries from the flat file entirely. Confirmed via 2018 Central American and Caribbean Championships.

**Division codes** — full reference: `../docs/divisions-reference.md`.

Division codes are universal — not specific to any org. All codes may appear across IFBB, NPC, CPA, and other orgs. When a division name is unfamiliar, read `../docs/divisions-reference.md` rather than inventing a code.

Source of truth for all codes: `~/workspace/angular/musmem-ui/src/assets/i18n/en.json` → `DIVISIONS`.

Common mappings for npcnewsonline.com:

**Bodybuilding height classes** — Some NPC Worldwide amateur contests (especially European regionals) use height classes instead of weight classes for Men's Bodybuilding. On npcnewsonline.com, these appear as slugs `class-a` through `class-g` under the Men's Bodybuilding division. Map them as:

| Slug | Code | | Slug | Code |
|------|------|-|------|------|
| `class-a` | `Ba` | | `class-e` | `Be` |
| `class-b` | `Bb` | | `class-f` | `Bf` |
| `class-c` | `Bc` | | `class-g` | `Bg` |
| `class-d` | `Bd` | | `class-h`+ | **error — stop and report** |

Note: `class-a/b/c/d` in Classic Physique and Men's Physique map to `Ca/Cb/Cc/Cd` and `Pa/Pb/Pc/Pd` respectively — those are different from Bodybuilding height classes.

**Masters Bodybuilding height classes** — `masters-class-a/b/c/d` slugs (masters competing in height classes, without an age number) map to:

| Slug | Code |
|------|------|
| `masters-class-a` | `MAa` |
| `masters-class-b` | `MAb` |
| `masters-class-c` | `MAc` |
| `masters-class-d` | `MAd` |

**Bare `masters` slug** (no age number) — maps to the Masters Open for that division:

| Division | `masters` slug → |
|----------|-----------------|
| Bodybuilding (OP / BB) | `MA` |
| Classic Physique (CL) | `mc` |
| Men's / Women's Physique (PH) | `MP` |
| Figure (FI) | `FM` |

**Masters Physique class letters** (no age, by class):

| Slug | Code | | Slug | Code |
|------|------|-|------|------|
| `masters-class-a` in PH | `MPa` | | `masters-class-a` in OP/BB | `MAa` |
| `masters-class-b` in PH | `MPb` | | `masters-class-b` in OP/BB | `MAb` |
| `masters-class-c` in PH | `MPc` | | `masters-class-c` in OP/BB | `MAc` |
| `masters-class-d` in PH | `MPd` | | `masters-class-d` in OP/BB | `MAd` |

**Kilogram weight classes** — appear in some international and European NPC Worldwide contests:

| Slug | Code | | Slug | Code |
|------|------|-|------|------|
| `55kg` | `55kg` | | `85kg` | `85kg` |
| `60kg` | `60kg` | | `90kg` | `90kg` |
| `65kg` | `65kg` | | `95kg` | `95kg` |
| `70kg` | `70kg` | | `100kg` | `100kg` |
| `75kg` | `75kg` | | `over-100kg` | `o100kg` |
| `80kg` | `80kg` | | | |

Range slugs take the upper value: `90-95kg` → `95kg`, `95-100kg` → `100kg`, `over-102kg` → `HW`.
Descriptor slugs: `under-85kg` → `LW`, `over-85kg` → `MW`, `lightweight-up-to-75kg` → `LW`, etc.

**Classic Physique height sub-classes** (some European contests):

| Slug | Code |
|------|------|
| `a-under175cm` | `Ca` |
| `b-over175cm` | `Cb` |

| Division | Code | Division | Code |
|----------|------|----------|------|
| Bodybuilding Open | `OP` | Classic Physique Open | `CL` |
| Women's Bodybuilding Open | `BB` | Classic Masters 40+ | `c4` |
| Under 212 | `U212` | Classic Masters 45+ | `c45` |
| Under 208 | `U208` | Classic Masters 50+ | `c5` |
| Masters 40+ | `M4` | Classic Masters 55+ | `c55` |
| Masters 45+ | `45` | Classic Masters 60+ | `c6` |
| Masters 50+ | `M5` | Classic Masters 70+ | `c7` |
| Masters 55+ | `55` | Physique Open | `PH` |
| Masters 60+ | `M6` | Masters Physique 40+ | `P4` |
| Masters 65+ | `m6` | Masters Physique 45+ | `P45` |
| Masters 70+ | `M7` | Masters Physique 50+ | `P5` |
| Masters 80+ | `M8` | Masters Physique 55+ | `P55` |
| Masters 90+ | `M9` | Masters Physique 60+ | `P6` |
| Masters Open (BB) | `MA` | Masters Physique 70+ | `P7` |
| Overall | `OV` | Masters Physique Open | `MP` |
| Teen | `TE` | Figure Open | `FI` |
| Bodybuilding Junior | `JR` | Figure 40+ | `F4` |
| Physique Junior | `PJ` | Figure 45+ | `f4` |
| Classic Physique Junior | `CJ` | Figure 50+ | `F5` |
| Figure Junior | `FJ` | Figure 55+ | `f5` |
| Wheelchair | `WC` | Figure 60+ | `F6` |
| Phys. Challenged Standing | `Hs` | Figure 65+ / 70+ | `F65` |
| Phys. Challenged | `HC` | Masters Figure Open | `FM` |
| Junior Heavyweight | `JH` | Classic Masters Open | `mc` |
| Junior Light-Heavyweight | `Jl` | Kg classes | `55kg`–`100kg`, `o100kg` |

**One file per contest.** Save each to `~/workspace/musmem/1-incoming/`.

**Male/female split:** When a contest has both male and female divisions, write two separate files — one per gender. Division codes are the same across genders; separate files prevent collisions (e.g., both Men's and Women's Physique use `Pa`–`Ph`).

- Male divisions: Bodybuilding weight classes, Men's Physique, Classic Physique
- Female divisions: Figure, Women's Bodybuilding, Women's Physique
- Excluded from both: Bikini, Wellness, Fitness, Fit Model

**Filename format:** `{year}_{contest_name}-{org}-{gender}.txt` where gender is `male` or `female`

- Always include the gender suffix — even if a contest is single-gender
- Use the contest name part only (no org in the name portion)
- Lowercase, spaces replaced with underscores, remove special characters

Examples:
| Contest | Filename |
|---------|----------|
| Arnold Classic - IFBB (2025, male) | `2025_arnold_classic-ifbb-male.txt` |
| Arnold Classic - IFBB (2025, female) | `2025_arnold_classic-ifbb-female.txt` |
| NPC Nationals 2025 (male) | `2025_national_championships-npc-male.txt` |
| NPC Nationals 2025 (female) | `2025_national_championships-npc-female.txt` |
| Cancun Naturals - NPC Worldwide (2025, male) | `2025_cancun_naturals-npc_worldwide-male.txt` |

**Create the directory if it doesn't exist:** `mkdir -p ~/workspace/musmem/1-incoming`

**Validate before writing — a division code must appear in at most one `c` block per file.** Within a single year/contest/gender file, every `c {code}` block should be unique. If the same code shows up in two separate blocks, that is not a legitimate situation — it means at least one of those blocks was mapped to the wrong (too-generic) code and should instead have its own distinct letter/age/weight code, or the two blocks actually belong to the same class and should be merged into one. Before writing the file, scan all `c` lines and flag any repeated code with both blocks' context; resolve the mapping (per `../docs/division-recognition.md`) rather than writing duplicate blocks. This check would have caught the 2022 European Amateur Championships (female) errors, where six separate Figure classes were all written as `c FI`.

Report to the user: list of files written and total competitors captured per file.

### Bulk Extract script

To re-extract all contests that already have files in `2-normalize-athletes/` (e.g. after slug mapping updates), use:

```bash
# All contests (reads 2-normalize-athletes/ to find slugs/orgs)
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/scrape_all_phase2.py

# Glob filter (quote to prevent shell expansion)
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/scrape_all_phase2.py '*2019*'

# Resume from offset N (skip first N contests)
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/scrape_all_phase2.py --start 50
```

- Excludes NAC contests automatically
- Stops with exit code 1 on any unknown slug — fix `fix_subdivisions.py` and restart with `--start N`
- Only writes gender files that already exist in `2-normalize-athletes/` (male and/or female)
- Prints `FLAG` lines when single primary sub-divisions are collapsed to outer code

### Page cache

All HTTP fetches go through a local disk cache at `~/workspace/musmem/.page_cache/`. The workflow is two logical steps:

1. **Fetch** — each contest page URL is checked against the cache. On a miss, the page is fetched from the web and written to disk. On a hit, the cached file is read directly — no HTTP request is made.
2. **Extract** — athlete placings are parsed from the cached HTML and written to `1-incoming/`.

This means re-running the scraper (e.g. after fixing a slug mapping) replays extraction against already-cached pages, without re-hitting the web.

**Cache location:** `~/workspace/musmem/.page_cache/`  
**Cache key:** derived from the URL path (slashes replaced with `_`, `.html` extension)  
**To force a re-fetch:** delete the relevant `.html` file(s) from `.page_cache/`, or delete the whole directory.

The `scan_slugs.py` diagnostic script also uses this cache. Pass `--no-cache` to force fresh fetches:
```bash
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/scan_slugs.py --no-cache
```

### Diagnostic scripts

**Scan for unknown slugs** (before running the full scraper):
```bash
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/scan_slugs.py
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/scan_slugs.py --no-cache  # force re-fetch
```
Reports unknown slugs grouped by contest. Zero unknowns = safe to run the full scraper.

**Find non-Latin athlete names** (after Phase 2 scrape, to spot encoding issues):
```bash
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/find_nonlatin.py
```
Scans `1-incoming/` and groups names by script (Cyrillic, CJK, Arabic, etc.). Latin diacritics are excluded.

---

## Phase 3: Normalize Athletes

Convert raw scraped names in `1-incoming/` to canonical `Last, First` or `@n Family Given` form, writing results to `2-normalize-athletes/`.

Canonical forms and normalization rules are documented in `~/workspace/musmem/working-docs/normalization_playbook.md`.

### Step 1 — Apply TSV (auto-replay known corrections)

```bash
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/apply_canonical_names.py
```

Reads `~/workspace/musmem/working_data/raw_to_canonical.tsv` and applies all known `raw → canonical` mappings to every file in `1-incoming/`, writing results to `2-normalize-athletes/`. Names not found in the TSV are written as-is (still raw).

- TSV has ~5,200 entries covering the bulk of previously seen names
- NPC Worldwide placing-98 lines are skipped (not written to output)
- Run this first — it handles the majority of names automatically

### Step 2 — Agent bulk normalization (remaining unnormalized names)

For names not covered by the TSV, use an interactive agent session:

1. Identify unnormalized names remaining in `2-normalize-athletes/` (lines without a comma and without `@`)
2. Find structural patterns (e.g. all `a b c d` four-token names, names with particles like `Van`/`De`/`Bin`, Arabic blocks, East Asian names)
3. For each pattern, propose canonical forms following `normalization_playbook.md`
4. Review proposed batch in chat, approve, then apply directly to `2-normalize-athletes/` files

After agent work, rebuild the TSV to absorb new corrections:

```bash
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/build_raw_to_canonical_tsv.py
```

This re-derives `raw_to_canonical.tsv` by comparing `1-incoming/` against the updated `2-normalize-athletes/`. Future runs of Step 1 will automatically apply the new corrections.

### What "normalized" means

A name line is considered normalized if:
- it contains a comma: `1 Smith, John`
- or it starts with `@`: `@2 Kim Sungyeob`

Non-athlete lines (`y`, `t`, `c`, `----`) are always passed through unchanged.

### Note on `normalize_athlete_names.py`

This script (algorithmic heuristics only, no TSV) is superseded by the two-step workflow above. It may still be useful for a quick pass on 1–2 new contests where no TSV entries exist yet, but should not be used for bulk processing.

---

## Phase 4: Normalize Contest Names

Rename flat files in `2-normalize-athletes/` so that the filename and `t` line use the canonical MuscleMemory contest title. The mapping is defined in `../docs/contest-title-normalization-audit.md`.

### Run the script

```bash
# Normalize all files (interactive — prompts per file)
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/normalize_contest_names.py --all

# Normalize all files non-interactively (accept all)
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/normalize_contest_names.py --all --yes

# Normalize specific files (with or without .txt)
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/normalize_contest_names.py 2022_arnold_amateur-ifbb-male.txt

# Glob pattern (quote to prevent shell expansion)
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/normalize_contest_names.py '*arnold*'
```

For each file that needs a title change, shows the current title, the canonical title, and the new filename. Prompts `[y]es / [n]o / [a]ll / [x]exit` before applying. Use `--yes` for non-interactive batch normalization.

### What it changes

- The `t` line in the file is updated to the canonical title
- The filename is renamed to match (e.g. `2022_arnold_amateur-ifbb-male.txt` → `2022_arnold_amateur-npc_worldwide-male.txt`)
- Files already using the canonical title are skipped silently

The mapping is sourced from `../docs/contest-title-normalization-audit.md` — entries of the form `- YEAR - Source Title` under a `## Canonical Title` heading.

---

## Phase 5: Format

Run the normalized flat files through `format.php` to produce import-ready `.out` files.

### Run the formatter

```bash
# Format all unprocessed files (no .out yet in 3-formatted/)
~/workspace/skills/musmemSkills/musmem-contests/php/run_format.sh

# Format a specific file (with or without .txt extension)
~/workspace/skills/musmemSkills/musmem-contests/php/run_format.sh 2025_olympia-ifbb-male

# Reprocess all files, overwriting existing .out files
~/workspace/skills/musmemSkills/musmem-contests/php/run_format.sh --force

# Reprocess a specific file, overwriting its .out
~/workspace/skills/musmemSkills/musmem-contests/php/run_format.sh --force 2025_olympia-ifbb-male
```

Input: `~/workspace/musmem/2-normalize-athletes/*.txt`
Output: `~/workspace/musmem/3-formatted/*.out`

### What format.php does

- Parses `y`, `t`, `c`, `l`, `----` control lines
- Converts competitor lines to: `Last, First; year; Contest Name - ORG; division-placing; c=XX;`
- Normalizes name casing (title case, handles O'/Mc/hyphen prefixes)
- Detects and converts country codes if present in source data (npcnewsonline.com has none)
- Flags 3+ word names with `<<<<` for manual review
- Warns on upper-case `C` (should be lowercase `c`)
- Transliterates common accented characters (ñ→n~, á→a, etc.)

### Output format (one line per competitor)

```
Lunsford, Derek; 2025; Olympia - IFBB; OP-1;
Dauda, Samson; 2025; Olympia - IFBB; OP-2;
```

### Review the output

Check stdout for:
- `<<<<` — 3+ word names that may be split incorrectly (Last vs First ambiguous)
- `===> POSSIBLE ERROR` — uppercase `C` used instead of `c`
- `******* ` — unrecognized country code

---

## Phase 6: Review Flagged Names

Interactively resolve all `<<<<` lines in `.out` files. Reads from `3-formatted/`, writes resolved files to `4-reviewed/`. Run the script via Claude (opens a Terminal window) or directly in your terminal.

> **TODO:** `review_flags.py` currently uses `~/workspace/musmem/working_data/review-athlete-names.dat` as its `--accept-dict` persistence file (colon-delimited `original:chosen`). This should be modified to use `~/workspace/musmem/working_data/raw_to_canonical.tsv` instead — the same TSV used in Phase 3 — so that name decisions are shared across both phases and the TSV remains the single source of truth for all raw→canonical mappings.

### Run the script

Claude launches it with:
```bash
~/workspace/skills/musmemSkills/musmem-contests/python/review_flags.sh 2025_olympia-ifbb-male
~/workspace/skills/musmemSkills/musmem-contests/python/review_flags.sh   # all files with <<<< lines
```

Or run directly:
```bash
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/review_flags.py 2025_olympia-ifbb-male
```

### Keys (single keypress — no RETURN)

| Key | Action |
|-----|--------|
| `1` | Accept as-is |
| `2` | Re-split (alternative comma position) |
| `3` | Asianize (remove comma, keep word order) |
| `4` | DB lookup — searches MuscleMemory, then pick a result by number |
| `5` | Enter manually (type + RETURN) |
| `6` | Skip (leave `<<<<` for now) |
| `9` | Back to previous entry |
| `0` | Done for now (write file, stop this file) |
| `x` | Exit all (write file, stop all remaining files) |

### How it works

- Collects all `<<<<` lines upfront, iterates one at a time
- All decisions held in memory — file only written when done, `0`, or `x` pressed
- **Re-split:** shifts the comma one word position (e.g. `B C, A` → `C, A B`)
- **Asianize:** removes the comma, keeping word order as-is (e.g. `C, A B` → `C A B`)
- **DB lookup:** searches full name first; if no match, tries each word individually
- **Back:** removes previous decision so it can be changed
- **Done for now (`0`):** writes resolved decisions for this file, leaves remaining `<<<<` intact, continues to next file
- **Exit all (`x`):** writes resolved decisions for this file, stops processing all remaining files
- Gender inferred from filename (`-male` / `-female`)

---

## Phase 7: Complete

Verify new athlete names against the master files, resolve conflicts interactively, then write the corrected `.out` file to `5-completed/`. **Does not modify the master.**

### Run the script

```bash
# Process all pending .out files
~/workspace/skills/musmemSkills/musmem-contests/python/verify_and_complete.sh

# Process a specific file (with or without .out extension)
~/workspace/skills/musmemSkills/musmem-contests/python/verify_and_complete.sh 2025_arnold_classic-ifbb-male
```

Input: `~/workspace/musmem/4-reviewed/*.out`
Master files: read-only reference for conflict detection
After completion: corrected file written to `~/workspace/musmem/5-completed/`

Gender inferred from filename (`-male` / `-female`).

### Per-file workflow

1. Read master as read-only reference
2. For each unique name in the `.out` file, run the candidate-matching pipeline (see below)
3. **Auto-accept** names with exactly one exact match and temporal gap ≤ `--max-gap` — no user input
4. Iterate remaining conflicts interactively — corrections held in memory
5. On approval: apply corrections → write corrected file to `5-completed/`

If no conflicts require review, prompts to write immediately.

### Candidate-matching pipeline

Strategies are run in order. All matches across all strategies are collected, deduplicated, and presented together.

| Step | Strategy | Examples caught |
|------|----------|-----------------|
| 1 | **Exact + variants** | `Smith, John` → also finds `Smith, John [2]`, `Smith, John Jr`, `Smith, John III` |
| 2 | **Diacritic normalization** | `Pena` ↔ `Pen~a` ↔ `Peña`; uses internal special-char codes — see `../docs/special-chars-reference.md` |
| 3 | **Name part subset/superset** | `Smith, Lisa` ↔ `Smith, Lisa Marie`; partial Latin surnames |
| 4 | **Space normalization** | `Shu Xiao Fan` ↔ `Shu Xiaofan` ↔ `ShuXiaofan` |
| 5 | **Eastern format** | `Xiaofan Shu` (no comma) ↔ `Shu, Xiaofan` |
| 6 | **Word order permutations** | `Xiao Fan Shu` ↔ `Shu Xiao Fan` ↔ `Fan Shu Xiao` |
| 7–8 | **Soundex / edit distance** | `Smithe` ↔ `Smith`; fallback only when steps 1–6 find nothing |

**Auto-accept rule:** Only when there is exactly one candidate, found via exact match only, with temporal gap ≤ `--max-gap`. Any other match type (diacritic, subset, space, etc.) always requires confirmation — even with one candidate.

**Temporal gap warning:** If an exact match is found but the athlete's last master appearance is more than `--max-gap` years before the incoming contest year, a ⚠ year-gap warning is shown and confirmation is required. Default `--max-gap` is 8 years.

```bash
# Override gap threshold
python3 verify_and_complete.py --max-gap 12 2025_arnold_classic-ifbb-male
```

### Keys (single keypress — no RETURN)

| Key | Action |
|-----|--------|
| `1`–`N` | Match to candidate N (corrects spelling in `.out` to master spelling) |
| `N` | New athlete — assign next `[n]` suffix |
| `D` | Details — prompts for a number, then lists all master records for that candidate |
| `S` | Skip — leave name as-is, move to next conflict |
| `9` | Back to previous conflict |
| `0` | Done for now — prompt to write, stop this file |
| `X` | Exit all — prompt to write, stop all remaining files |

### Candidate summary format

```
[2/5] Smith, John  (Arnold Classic - IFBB, 2025, OP-3)
  1. Smith, John              — 18 contests, 2008–2019, OP/CL
  2. Smith, John [2]          — 4 contests, 2021–2024, PH
  3. Smithe, John             — 1 contest, 2023, M4   (soundex)
  N  New athlete → Smith, John [3]
  D  Details (then enter number)
  S  Skip (keep name as-is)
  9  Back
  0  Done for now
  X  Exit all
```

Candidates found via non-exact strategies show a tag: `(diacritic)`, `(subset)`, `(space)`, `(eastern)`, `(wordorder)`, `(soundex)`. Temporal gap warnings show as `⚠ 47yr gap`.

### Name disambiguation (`[n]` notation)

Incoming `.out` files use plain names (no `[n]`). The master may have multiple athletes with the same base name: `Smith, John`, `Smith, John [2]`, `Smith, John [3]`, etc. All variants are presented as candidates. Selecting `N` assigns the next available number to every occurrence in the `.out` file.

---

## Phase 8: Append

Append corrected `.out` files from `5-completed/` to gender-specific staging `.dat` files in `6-appended/`. Files in `5-completed/` are never moved or deleted.

### Run the script

```bash
# Process all files in 5-completed/
~/workspace/skills/musmemSkills/musmem-contests/python/append_to_master.sh

# Process a specific file (with or without .out extension)
~/workspace/skills/musmemSkills/musmem-contests/python/append_to_master.sh 2025_arnold_classic-ifbb-male
```

Input: `~/workspace/musmem/5-completed/*.out`
Output: `~/workspace/musmem/6-appended/append-male.dat` or `append-female.dat`

Gender inferred from filename (`-male` / `-female`).

### Per-file workflow

For each file, shows:
- Contest name, year, and whether it already exists in the staging `.dat` (duplicate warning)
- Number of records to append

Prompts Y/N/X before appending. On Y: appends records to `append-{gender}.dat`.

### Keys (single keypress — no RETURN)

| Key | Action |
|-----|--------|
| `Y` | Append to `6-appended/append-{gender}.dat` |
| `N` | Skip — leave file in `5-completed/` |
| `X` | Exit — stop processing remaining files |

---

## MuscleMemory API Reference

| Endpoint | Purpose |
|----------|---------|
| `GET /api/contests/{year}` | All contests in DB for a year (use `0` for all years) |
| `GET /api/org?name={ORG}` | All contests for a specific org |
| `GET /api/contest/years?name={name}` | Years a contest appears in the DB |
| `GET /api/contest?name={name}&year={year}` | Full results for a specific contest+year |

Base URL: `http://localhost:3000` (confirm the local server is running first — see Phase 1 Step 1; if not, ask the user to start it. Do not call `musclememory.net`/`.org` directly; it requires a signed request and will 403.)

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using query-param tracking URLs from npcnewsonline.com | Use the clean URLs in sources-reference.md — tracking params cause errors |
| Comparing names without normalizing org prefix | Always strip "IFBB "/"NPC "/"NPC Worldwide "/"CPA " prefix before comparing |
| Assuming contest is new without checking DB | Always query the API first |
| Writing names in Last, First order | npcnewsonline.com uses First Last — do not set `l 1` |
| Calling musclememory.net/.org directly for API endpoints | It requires a signed request and 403s (`Invalid or missing request signature`) on any unsigned call. Use the local server on `localhost:3000` instead (if port 3000 isn't up, ask the user to start the local musmem server) — no signature needed |
| No User-Agent when scraping external sites | When fetching npcnewsonline.com etc. via curl/script use `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36` — WebFetch does not support custom headers |
| Using WebFetch on large contest pages | WebFetch truncates at ~50KB — later divisions get silently cut off or hallucinated. Use curl + Python for large contests (NPC Nationals, Olympia, etc.) — see sources-reference.md |
| Mixing male and female divisions in one file | Contests with both genders need `-male.txt` and `-female.txt` files — same division codes would collide in a single file |
| Using divisions.php as code reference | Source of truth is now `en.json` DIVISIONS — `PRh` is Pro HeavyWeight (not `Ph`, which is Physique H) |
| Prefixing Olympia with "Mr" | Contest title is `Olympia - IFBB`, not `Mr Olympia - IFBB`. "Mr {name}" applies only to selected AAU titles and selected pre-1980 IFBB titles. |
| HTML entities in names | npcnewsonline.com sometimes includes raw HTML entities (e.g., `&#039;` for `'`, `&amp;` for `&`). Decode them when writing the flat file or format.php will error on the line. |
| Defaulting un-mapped PDF division/class names to a bare/generic code (e.g. `FI` for every Figure sub-class) | PDFs have no `data-slug` structure — division and class identity must be recognized from free text using `../docs/division-recognition.md`. An unrecognized division or class name must stop extraction and get reported, never silently collapse to the outer code. |
| Writing a `0 {Name}` overall entry for a class winner when the source has no explicit overall/combined section for that division | Only write placing `0` when an explicit "Overall"/"Combined" section exists in the source — never infer one from a class winner |
| Including a country code on a `0` (overall) line | `0 {Name}` lines never include a country code, on any source, even when placed-competitor lines in the same file do |
| Writing a Pairs/Team event (Mixed-Pairs, Fit-Pairs, Duo) as a normal division | These represent 2+ athletes per placing — exclude entirely, the DB has no multi-athlete entry support |
| Same division code (`c` block) appearing twice in one year/contest/gender file | Not legitimate — indicates a class was mapped too coarsely and needs its own letter/age code, or two blocks should be merged. Scan for duplicate `c` codes before writing the file. |
| Writing a placing-0 entry named "{Division} Overall Comparisons" | This is npcnewsonline's placeholder link to a photo-comparison round, not an athlete — it reuses the `data-parent="overall-winner"` markup with an empty placing but its anchor has `class="comparison ..."`. Confirmed via 2020 Southern States Championships. `extract_athletes()` in `scrape_all_phase2.py` now filters any anchor whose class contains `comparison`. |
| Trusting a name with a parenthetical/dashed occupation tag, e.g. "Gil Devera (Deputy Sheriff)" or "Luc-Julien Bongiovanni -- Infantry" | npcnewsonline's "Hero" tribute program appends a military/first-responder tag to an athlete's name across *all* their entries for the show, not just the excluded `hero`/`heroes` slug — the placing itself is real and must be kept. Confirmed via 2024 Golden State Championships (Gil Devera legitimately won CL overall + c3 + c4 + Ca that year). `clean_name()` now strips trailing occupation tags via `_TRAILING_OCC_RE` — keyword-anchored so it never touches the DB's numeric `(2)`/`(3)` duplicate-name suffix convention. |
