# npcnewsonline.com Contest Extraction — Collaborator Guide (Phase 1 & 2)

This document gives Claude everything needed to find bodybuilding contests on
npcnewsonline.com that are missing from the MuscleMemory database, and to
extract their results into import-ready flat files. It is self-contained —
no access to any other repo, script, or file is required.

The work happens in two phases:

- **Phase 1 — Discovery:** figure out which contest pages need to be looked
  at, fetch them, and save them locally. No data extraction happens yet.
- **Phase 2 — Extract:** read the saved pages and turn them into flat text
  files (one per contest/gender) in a specific format.

Do not skip ahead to importing, normalizing names, or anything past Phase 2
— stop after Phase 2 and hand the output back.

## Working directory

Create these folders in your working directory (adjust the base path as you
like, just be consistent):

```
mkdir -p ./musmem-work/.page_cache
mkdir -p ./musmem-work/1-incoming
```

- `.page_cache/` — raw HTML of every contest page you fetch (Phase 1 output)
- `1-incoming/` — the flat text files you write per contest (Phase 2 output)

Files are never deleted — if a page is already in `.page_cache/`, don't
re-fetch it; if a flat file already exists, you're re-doing that contest.

## Python scripting rule

Never run `python3 -c "..."` or a `python3 - <<EOF` heredoc for anything
beyond a trivial one-liner. For any real script (HTML parsing, curl output
processing, etc.), write it to a file first (e.g. `/tmp/script.py`) and then
run `python3 /tmp/script.py`. This avoids shell-escaping bugs with quotes
and newlines in HTML content.

---

## Phase 1: Discovery

**Goal:** identify which contest pages need to be fetched, then fetch and
cache them. Do not extract any results yet — output is just cached HTML
pages.

This phase is triggered one of two ways — confirm which one applies before
starting:

- **"Check npcnewsonline for {ORG} contests in {year(s)} not already in the
  database"** — target contests are ones that appear on the listing page but
  are absent from the MuscleMemory DB.
- **"Check npcnewsonline for {ORG} contests in {year(s)} for missing
  divisions"** — target contests are ones already in the DB for those years;
  you're fetching their pages so a later pass can compare DB divisions
  against what's actually on the page.

### Step 1 — Fetch the MuscleMemory DB for the target year(s)

```
GET https://musclememory.net/api/contests/{year}
```

Returns JSON with `data.contests` — an array of strings like
`"Arnold Classic - IFBB"`. Call once per year if checking multiple years.

**Important — User-Agent required.** musclememory.net blocks requests
without a browser-like User-Agent and silently returns fake/empty HTML
instead of an error. Always fetch it via curl (not WebFetch — WebFetch can't
set custom headers) with:

```bash
curl -s -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://musclememory.net/api/contests/2025"
```

Other useful endpoints (base URL `https://musclememory.net`), all need the
same User-Agent:

| Endpoint | Purpose |
|---|---|
| `GET /api/contests/{year}` | All contests in DB for a year (`0` = all years) |
| `GET /api/org?name={ORG}` | All contests for a specific org |
| `GET /api/contest/years?name={name}` | Years a given contest appears in the DB |
| `GET /api/contest?name={name}&year={year}` | Full results for a specific contest+year |

### Step 2 — Scrape the listing page and identify target contests

Listing pages are lightweight — no need to cache these, just read them.

| Org | MuscleMemory suffix | Listing URL |
|---|---|---|
| IFBB | `- IFBB` | `https://contests.npcnewsonline.com/contests/{year}/ifbb` |
| NPC | `- NPC` | `https://contests.npcnewsonline.com/contests/{year}/npc` |
| NPC Worldwide | `- NPC Worldwide` | `https://contests.npcnewsonline.com/contests/{year}/npcw` |
| CPA | `- CPA` | `https://contests.npcnewsonline.com/contests/{year}/cpa` |

**Do not use URLs with query-parameter tracking strings** (anything after a
`?`) — they cause errors. Only use the clean URLs above and the individual
contest URLs derived from listing-page links.

**Name normalization — npcnewsonline.com prefixes the org, MuscleMemory
suffixes it.** Strip the leading org prefix (and the space after it), then
append ` - {ORG}`:

| npcnewsonline.com | MuscleMemory format |
|---|---|
| `IFBB Arnold Classic` | `Arnold Classic - IFBB` |
| `NPC Ace of Stage Championships` | `Ace of Stage Championships - NPC` |
| `NPC Worldwide Cancun Naturals` | `Cancun Naturals - NPC Worldwide` |
| `CPA Alberta Open` | `Alberta Open - CPA` |

Compare the normalized listing-page names against the DB list from Step 1:

- **Missing-contests mode:** names on the listing page but not in the DB
  for that year → these are your targets.
- **Missing-divisions mode:** names already in the DB for that year → use
  the listing page only to get each one's individual page URL.

### Step 3 — Fetch individual contest pages into the cache

Individual contest page URL pattern:

```
https://contests.npcnewsonline.com/contests/{year}/{contest_slug}
```

The slug comes straight from the listing-page link (e.g. `ifbb_arnold_classic`).

**For small/medium pages**, WebFetch is fine. **For large contests** (NPC
Nationals, Olympia, or anything with many divisions), **do not use
WebFetch** — it truncates at roughly 50KB of visible content, which
silently cuts off later divisions (and the model may hallucinate to fill
the gap). Instead:

```bash
curl -s --compressed \
  -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://contests.npcnewsonline.com/contests/{year}/{contest_slug}" \
  -o ./musmem-work/.page_cache/{year}_{contest_slug}.html
```

Signs a page was truncated by WebFetch: results end mid-division, or later
divisions show names that look copy-pasted from an earlier division.

If a page is already saved in `.page_cache/`, skip re-fetching it.

### Step 4 — Report

List which contests' pages were newly fetched vs. already cached, and note
any fetch failures. Stop here — do not extract yet.

---

## Phase 2: Extract

**Goal:** read pages from `.page_cache/` and write flat files to
`1-incoming/`. No HTTP requests in this phase — if a needed page isn't
cached, report it and stop (go run Phase 1 first, don't fetch ad hoc).

### Step 1 — Parse the page structure

npcnewsonline.com pages use `data-slug` attributes on the HTML elements that
mark each division and sub-class. Each numbered placing sits inside an
anchor with `data-person="yes"`.

- Names are in **First Last** order — never rewrite them to Last-First and
  never set an `l 1` flag.
- No country information is available on npcnewsonline result pages.

### Step 2 — Clean every extracted athlete name

Apply these steps, in order, to every name pulled off the page:

1. **Strip HTML tags and unescape entities** (`&amp;` → `&`, `&#039;` → `'`, etc.) — unescaped entities will break the flat-file format later.
2. **Repair mojibake UTF-8** — if a name has obviously garbled characters from cp1252 bytes being misread as Unicode, try re-encoding as latin-1 and decoding as UTF-8. If that fails (e.g. it's a non-Latin script), leave the name as-is.
3. **Normalize curly quotes** — `'`/`'` → `'`, `"`/`"` → `"`.
4. **Strip periods** — remove all `.` (e.g. `Jr.` → `Jr`, `D.J.` → `DJ`).
5. **Normalize em-dash spacing** — ` - ` (space-hyphen-space) → `-`.
6. **Strip a trailing "â"** — this is a known stray OCR/encoding artifact from the site; remove it if present at the end of a name.
7. **Remove spaces around apostrophes** — `O ' Brien` → `O'Brien`.
8. **NFC-normalize Unicode** — compose decomposed diacritics into single characters (e.g. combining tilde + n → ñ).
9. **Per-word normalization** (apply to each whitespace-separated word):
   - Title-case it.
   - Capitalize the letter right after an apostrophe (`O'brien` → `O'Brien`).
   - For words starting with `Mc`, capitalize the 3rd letter (`Mcmillan` → `McMillan`).
   - A non-trailing `II` → `Il` (in the middle of a name, `II` is almost always an OCR misread of the name "Il").
   - A two-letter word where both letters are consonants → split into two initials with a space, e.g. `DJ` → `D J`. **Exceptions — do not split:** `Jr`, `Sr`, `St` (the "Saint" particle), `Ng` (a real surname), and any such word ending in `y` (`Ly`, `Ty`, `Dy` are short Vietnamese/Filipino/Cambodian given names, not initials).
   - A trailing word that is exactly `II`, `III`, or `IV` (any case) → uppercase it as a Roman numeral. Don't touch higher values like `VI`/`XI` — those are valid Chinese given names, not suffixes.
   - If the first word is `Dr` (any case), delete it — honorifics aren't recorded.
10. **Collapse whitespace** — multiple spaces → one, trim leading/trailing.
11. **Flag non-Latin scripts** — if a name contains Cyrillic, Arabic, or CJK characters, print a warning but don't modify it.

### Step 3 — Map each division/class to a MuscleMemory division code

Source of truth is the table below (npcnewsonline.com's own coding scheme).
**If you hit a sub-class slug that isn't in this table and isn't in the
exclusion list below, stop immediately and report it** — division name,
contest, and the unrecognized slug — rather than guessing or defaulting to
a generic/outer code. The person you report to will decide whether it's a
new code or should be added to the exclusion list.

**Excluded divisions — skip entirely, write nothing:**
- Bikini (all age groups)
- Wellness (all age groups)
- Fitness (all age groups)
- Novice / Beginner / True Novice / First Timer (all variants)
- Challenger (synonymous with Novice)
- Pairs/Team categories (Mixed-Pairs, Fit-Pairs, Duo, Couple — anywhere a
  single placing represents two or more athletes; the database can't
  represent a multi-athlete entry)

**Explicitly excluded slugs (skip, write nothing):**
- `overall-winner*`, `earned*`, `comparison` — structural markers, not athletes (overall winners are handled separately, see below)
- `novice`, `novice-*`, `*-novice`, `true-novice*`, `beginner`, `beginner-*`, `begginer*`
- `first-timer*`, `first-timers*`
- `regional`, `regional-*`, `*-regional`
- `natural`, `natural-*`
- `local`, `local-*`
- `star-category`, `armed-forces`, `military`, `first-responder`, `hero`, `heroes`, `uniform`, `battle-for-the-belt` — specialty/tribute divisions, excluded even if athletes are placed
- `guest-poser` — non-competitive single entrant, no placing
- `mr-*` — historical title slugs (e.g. `mr-universe`)
- Digit-only slugs (e.g. `1`, `2`) — data errors on the source page
- Geographic "local residents" sub-competitions scoped to a state/county/hometown (e.g. slugs referencing a specific place name or "hometown" rather than a competitive tier) — these run alongside the real open classes but there's no MuscleMemory code for a residents-only bracket. If you find a new one of these (real placings, doesn't match any division vocabulary, clearly a place-name/residency concept), you may exclude it directly without stopping to ask — just note it in your report.

**Important:** one npcnewsonline page can carry an occupation/tribute tag on
a name (e.g. `Gil Devera (Deputy Sheriff)`) even though that athlete's
actual placing is real and not part of the excluded `hero`/`military` slug
— strip the trailing parenthetical/dashed tag as part of name cleaning, but
keep the placing.

**Special slug-mapping rules:**

- **`open`** — in **Men's Bodybuilding**: if the page also has an Under 212/208/202 section → `open` maps to `OP`; if it's the only class on the page → `open` maps to `BB`. In **all other divisions** (CL, PH, FI, Women's Bodybuilding) → `open` maps to that division's own outer code as-is.
- **`pro-qualifier-*` prefix** — strip it, then map the remainder normally (e.g. `pro-qualifier-heavyweight` → treat as `heavyweight`).
- **Bare letter slugs `a`–`h`** — shorthand for `class-a` through `class-h`.
- **`senior`** → `MA` (same as bare `masters` in Bodybuilding).
- **`grandmasters`** → the division's 50+ code: `OP`/`BB` → `M5`, `FI` → `F5`, `PH` → `P5`, `CL` → `c5`.
- **`unique` / `Única` / bare `class`** → the division's outer code (alternate names for the open class).
- **`adaptive` / `special`** → `Hs` (Physically Challenged Standing).
- **`wheelchair` / `wheel-chair`** → `WC`.

**Single primary sub-division → collapse to outer code:** if a major
division (OP, BB, CL, PH, FI) has exactly one height/weight sub-class (not
counting masters/junior/teen sections), replace that sub-class code with the
division's own outer code. E.g. Women's Bodybuilding with only `class-b`
present → write `c BB`, not `c Bb`.

**Overall winners:** on npcnewsonline.com, overall winners appear as a
`data-person="yes"` link right after a `data-slug="overall-winner-*"`
element, with no placing number in its `<span>`. Write these directly into
the Phase 2 file (don't defer them) as:

```
c OP
0 Name Here
```

using the division's outer code (`OP`, `BB`, `CL`, `PH`, `FI`, etc.).
**Only write a `0` overall line when the page has an explicit
overall/combined section for that division** — never infer one from who won
the largest/last class. And never a country code on a `0` line (moot here
since npcnewsonline has no country data anyway).

**No overall entry when the division only has one class:** if a division
already collapsed to the bare outer code (per the single-primary-sub-division
rule above), skip any accompanying "Overall" `0` line for that division —
it would be redundant with placing `1` already sitting under the bare code.

**Did-not-place ties → placing 98:** if the highest placing number repeats
(several athletes all shown as the same final number, e.g. all tied at
"16th"), replace every one of those tied entries with `98`. But if a
division has clean, unique placings 1 through N with no repeats, the last
one is a real placing — leave it alone even if N happens to be a round
number.

**Disqualified (doping) → placing 99.**

**Did Not Compete (DNC) → omit entirely** — don't write a line for them at
all.

### Division code reference (npcnewsonline.com)

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

**Bodybuilding height classes** (some NPC Worldwide/European contests use
height instead of weight for Men's Bodybuilding — slugs `class-a`
through `class-g`):

| Slug | Code | Slug | Code |
|---|---|---|---|
| `class-a` | `Ba` | `class-e` | `Be` |
| `class-b` | `Bb` | `class-f` | `Bf` |
| `class-c` | `Bc` | `class-g` | `Bg` |
| `class-d` | `Bd` | `class-h`+ | **stop — unmapped, report it** |

Note: `class-a/b/c/d` under Classic Physique or Men's Physique map instead
to `Ca/Cb/Cc/Cd` and `Pa/Pb/Pc/Pd` respectively (different letter pools).

**Masters Bodybuilding height classes** (`masters-class-a/b/c/d`, no age
number given):

| Slug | Code |
|---|---|
| `masters-class-a` | `MAa` |
| `masters-class-b` | `MAb` |
| `masters-class-c` | `MAc` |
| `masters-class-d` | `MAd` |

**Bare `masters` slug** (no age number) → the Masters Open for that division:

| Division | Code |
|---|---|
| Bodybuilding (OP/BB) | `MA` |
| Classic Physique (CL) | `mc` |
| Men's/Women's Physique (PH) | `MP` |
| Figure (FI) | `FM` |

**Masters Physique class letters** (no age, by class letter):

| Slug (in PH) | Code | Slug (in OP/BB) | Code |
|---|---|---|---|
| `masters-class-a` | `MPa` | `masters-class-a` | `MAa` |
| `masters-class-b` | `MPb` | `masters-class-b` | `MAb` |
| `masters-class-c` | `MPc` | `masters-class-c` | `MAc` |
| `masters-class-d` | `MPd` | `masters-class-d` | `MAd` |

**Kilogram weight classes** (some international/European NPC Worldwide
contests):

| Slug | Code | Slug | Code |
|---|---|---|---|
| `55kg` | `55kg` | `85kg` | `85kg` |
| `60kg` | `60kg` | `90kg` | `90kg` |
| `65kg` | `65kg` | `95kg` | `95kg` |
| `70kg` | `70kg` | `100kg` | `100kg` |
| `75kg` | `75kg` | `over-100kg` | `o100kg` |
| `80kg` | `80kg` | | |

Range slugs take the upper value (`90-95kg` → `95kg`, `95-100kg` → `100kg`,
`over-102kg` → `HW`). Descriptor slugs: `under-85kg` → `LW`, `over-85kg` →
`MW`, `lightweight-up-to-75kg` → `LW`, etc.

**Classic Physique height sub-classes** (some European contests):

| Slug | Code |
|---|---|
| `a-under175cm` | `Ca` |
| `b-over175cm` | `Cb` |

**`junior` and `teen` slugs — division-dependent:**

| Division | `junior` → | `teen`/`teenage`/`teenager` → |
|---|---|---|
| Bodybuilding (OP/BB) | `JR` | `TE` |
| Classic Physique (CL) | `CJ` | `ct` |
| Men's/Women's Physique (PH) | `PJ` | `PT` |
| Figure (FI) | `FJ` | `FT` |

**Junior weight sub-classes:**

| Slug | Code | Slug | Code |
|---|---|---|---|
| `junior-heavyweight` | `JH` | `junior-lightweight` | `JL` |
| `junior-light-heavyweight` | `Jl` | `junior-bantamweight` | `JB` |
| `junior-middleweight` | `JM` | `junior-flyweight` | `JF` |
| `junior-welterweight` | `JW` | `junior-light-flyweight` | `Jf` |
| `junior-tall` | `Jt` | `junior-medium` | `Jm` |
| `junior-short` | `Js` | | |

**Junior class letters** (`junior-class-a`..`d`, also `junior-a`..`d`):

| Division | -a | -b | -c | -d |
|---|---|---|---|---|
| Classic Physique | `CJa` | `CJb` | `CJc` | `CJd` |
| Men's Physique | `PJa` | `PJb` | `PJc` | `PJd` |
| Figure | `FJa` | `FJb` | `FJc` | `FJd` |

**Masters age codes by division:**

| Age | OP/BB | Classic (CL) | Physique (PH) | Figure (FI) |
|---|---|---|---|---|
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

**Masters age + class/weight combos** — combine the base age code with the
class letter or weight suffix: `masters-40-class-a` in PH → `P4` + `a` =
`P4a`; `masters-35-class-b` in CL → `c3` + `b` = `c3b`;
`masters-45-heavyweight` in OP → `45` + `H` = `45H`;
`masters-40-tall` in OP → `4` + `t` = `4t`. A bare letter suffix works the
same as `class-X` (`masters-40-a` = `masters-40-class-a`).

### Step 4 — Write the flat file

One contest (and gender) per file. Format:

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

Rules:
- `y {year}` — sets the year (once, at the top).
- `t {Contest Name - ORG}` — the MuscleMemory-format title (see normalization above).
- `c {code}` — starts a division block, using a code from the reference above.
- `----` — separator between division blocks.
- Competitor line: `{placing} {First Last}` — no prefix character, no country (npcnewsonline has none).
- Leave the `l` flag unset entirely (don't write `l 1`) — default is first-last order, which matches this source.

**Male/female split — write separate files.** If a contest has both male
and female divisions, write two files, because division codes overlap
between genders (both Men's and Women's Physique use `Pa`–`Ph`, for
example) and would collide in one file.

- Male divisions: Bodybuilding weight/height classes, Men's Physique, Classic Physique
- Female divisions: Figure, Women's Bodybuilding, Women's Physique
- Excluded from both: Bikini, Wellness, Fitness, Fit Model

**Filename format:** `{year}_{contest_name}-{org}-{gender}.txt`, where
`{gender}` is `male` or `female` — always include it, even for a
single-gender contest. `{contest_name}` is lowercase, spaces→underscores,
no special characters, and does not include the org.

Examples:

| Contest | Filename |
|---|---|
| Arnold Classic - IFBB (2025, male) | `2025_arnold_classic-ifbb-male.txt` |
| Arnold Classic - IFBB (2025, female) | `2025_arnold_classic-ifbb-female.txt` |
| Cancun Naturals - NPC Worldwide (2025, male) | `2025_cancun_naturals-npc_worldwide-male.txt` |

**Before writing, validate: a division code must not appear in two separate
`c` blocks in the same file.** If it does, one of those blocks was mapped
too coarsely (needs its own letter/age/weight code) or the two blocks are
really the same class and should be merged — fix this before writing, don't
write duplicate blocks.

### Step 5 — Report

List every file written and the total competitor count per file. Note any
slugs you had to stop on, any non-Latin names flagged for review, and any
pages that were missing from the cache.

---

## Common mistakes to avoid

| Mistake | Fix |
|---|---|
| Using a tracking/query-param URL from npcnewsonline.com | Always use the clean URL patterns above |
| Comparing contest names without stripping the org prefix first | Normalize before comparing to the DB list |
| Assuming a contest is new without checking the DB | Always query `/api/contests/{year}` first |
| Writing names in Last, First order | npcnewsonline.com is First Last — don't reorder, don't set `l 1` |
| Fetching musclememory.net without a browser User-Agent | It silently returns fake HTML for bot UAs — always set the UA shown above |
| Using WebFetch on a large contest page | It truncates ~50KB in — use curl + a saved-to-file script instead |
| Mixing male and female divisions in one file | Always split into separate `-male.txt` / `-female.txt` files |
| Leaving raw HTML entities (`&#039;`, `&amp;`) in a name | Decode them during name cleaning |
| Writing a `0` overall line when there's no explicit overall section on the page | Only write `0` lines when the page has an actual combined/overall round |
| Defaulting an unrecognized slug to a generic code just to keep moving | Stop and report it instead — silent defaults produce wrong division codes |
