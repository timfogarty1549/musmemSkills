# Contest Sources Reference

## npcnewsonline.com

Covers IFBB, NPC, NPC Worldwide, and CPA contests.

**User-Agent (scripted/curl fetching only):** `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36`
Claude's built-in WebFetch tool does not support custom headers — this applies only when fetching via curl or a script.

**Important:** Do not use URLs with query-parameter tracking strings — they cause errors. Use the clean URLs below.

### Listing pages (Phase 1 — Discovery)

| Org | MuscleMemory suffix | Listing URL |
|-----|--------------------|-----------------------------|
| IFBB | `- IFBB` | `https://contests.npcnewsonline.com/contests/{year}/ifbb` |
| NPC | `- NPC` | `https://contests.npcnewsonline.com/contests/{year}/npc` |
| NPC Worldwide | `- NPC Worldwide` | `https://contests.npcnewsonline.com/contests/{year}/npcw` |
| CPA | `- CPA` | `https://contests.npcnewsonline.com/contests/{year}/cpa` |

### Individual contest pages (Phase 2 — Results)

```
https://contests.npcnewsonline.com/contests/{year}/{contest_slug}
```

The slug comes from the listing page link (e.g., `ifbb_arnold_classic`).

### Name normalization

npcnewsonline.com prefixes the org. MuscleMemory suffixes it:

| npcnewsonline.com | MuscleMemory format |
|-------------------|---------------------|
| `IFBB Arnold Classic` | `Arnold Classic - IFBB` |
| `NPC Ace of Stage Championships` | `Ace of Stage Championships - NPC` |
| `NPC Worldwide Cancun Naturals` | `Cancun Naturals - NPC Worldwide` |
| `CPA Alberta Open` | `Alberta Open - CPA` |

**Rule:** Strip the leading org prefix (including the space after it), then append ` - {ORG}`.

### Result page structure

- Divisions listed with numbered placings
- Competitor names in First Last order — do NOT set `l 1`
- No country information available on result pages

### Large contest pages — use curl + Python, not WebFetch

WebFetch truncates pages beyond ~50KB of visible content. Large contests (NPC Nationals, Olympia, etc.) exceed this limit — WebFetch will silently cut off later divisions, and the AI may hallucinate data to fill the gap.

**Use this approach for large contests:**

```bash
# Download full page
curl -s --compressed \
  -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://contests.npcnewsonline.com/contests/{year}/{slug}" \
  > /tmp/contest.html
```

Then parse with the saved script (npcnewsonline.com only — depends on site-specific HTML patterns):

```bash
python3 ~/workspace/skills/musmemSkills/musmem-contests/python/parse_npcnewsonline_contest.py /tmp/contest.html
```

The script (`parse_npcnewsonline_contest.py` in this skill's directory):
- Finds division sections by `<h2 class="division-title">` tags — slices body between consecutive h2 positions
- Finds classes via `data-slug="..."` divs within each section body
- Extracts competitors via `<span> N </span> Name` pattern inside `data-person="yes"` anchors
- Prints all divisions to stdout; Claude then filters by gender and writes the flat files

**Signs WebFetch was truncated:** results end mid-division, or data from wrong divisions appears (names copied from earlier divisions).

### Male/female split files

When a contest has both male and female divisions, write separate files:
- `{year}_{contest_name}-{org}-male.txt`
- `{year}_{contest_name}-{org}-female.txt`

Division codes are the same across genders — the file split prevents collisions (e.g., both Men's and Women's Physique use `Pa`–`Ph`).

**Male divisions:** Bodybuilding weight classes, Men's Physique, Classic Physique
**Female divisions:** Figure, Women's Bodybuilding, Women's Physique
**Excluded from both:** Bikini, Wellness, Fitness, Fit Model

---

## PDF sources (any site)

Many federations (especially IFBB Amateur continental/regional championships — European, Asian, Balkan, Central American & Caribbean, Mediterranean, South American, etc.) publish results only as PDFs, cached in `.page_cache/` alongside HTML pages. npcnewsonline.com itself occasionally serves PDF results instead of its usual HTML structure. **PDF layout and wording is not guaranteed to be consistent across sources or even across years of the same contest** — there is no fixed template to hard-code against.

**Do not write a per-site division mapping from scratch.** Use the source-agnostic method in `division-recognition.md` for every PDF (and for any HTML source without npcnewsonline-style slug markup). It defines how to recognize base divisions, age/size qualifiers, letter-class ordering, overall entries, and pairs/team exclusion from free text, and when to stop and report an unrecognized pattern instead of guessing.

**Extracting text:** Use PyMuPDF (`import fitz`) via a script — see the Python scripting rule in Phase 1. `pdftotext`/`pdftoppm` (poppler) are not guaranteed to be installed; `fitz.open(path).get_text()` per page does not require them.

**Confirmed terminology synonyms** (add to `division-recognition.md` Step 1 as new ones are confirmed):

| Source wording | Base division |
|---|---|
| Bodyfitness (EBFF/IFBB European federation PDFs) | `FI` (Figure) |
| Classic Bodybuilding (no "Games" prefix — EBFF/IFBB European federation PDFs) | `CB` — a distinct category from Classic Physique (`CL`), confirmed via 2022 European Amateur Championships: different roster, different height-class thresholds. Don't assume "Classic X" always means Classic Physique. |
| Muscular Physique / "Muscular Men's Physique" (EBFF/IFBB European federation PDFs) | `MUP` — a distinct category from standard Physique (`PH`) |
| "Games" prefix on any division (e.g. "Games Classic Bodybuilding") | excluded — do not write |

**Known structural pitfalls** (found via the 2022 European Amateur Championships review — see Step 5/6 of `division-recognition.md`):
- Paired/team categories (`Mixed-Pairs`, `Fit-Pairs`) can appear directly after a legitimate division's class list with no strong visual separator — don't assume every section following a division header belongs to that division.
- A division's numbered classes and its age-bracketed (Junior/Master) classes are usually printed as separate class lists later in the document, not inline with each other — map each independently rather than assuming they share one code.
- **A single results PDF can contain multiple, differently-named "Classic"-style divisions that share overlapping rosters** (athletes entering more than one category) — don't assume two sections with similar names and shared competitors are the same division mis-printed twice. In the 2022 European Amateur Championships PDF, "Men's Games Classic Bodybuilding", "Men's Classic Bodybuilding", and "Men's Classic Physique" were three separate categories with three separate code families (excluded, `CB`, `CL`).
- Some cached PDF copies of the same contest are incomplete — always check for multiple cached PDFs of one contest (e.g. a "-copia-ok"/"corrected" filename) and prefer the more complete one; diff page counts and spot-check divergent pages before picking one as authoritative.
- **Two cached PDFs for the same year/region can be genuinely different contests, not duplicates or drafts** — check the edition number and title text before assuming. In 2025, the Central American & Caribbean cache held both "52nd CAC" (`Central American and Caribbean Championships - IFBB`) and "XII Campeonato Centroamericano" (`Central American Amateur Championships - IFBB`) — a separate, narrower regional event with its own independent edition count (XII, XIII in 2026), Spanish ordinal placings (`1er./2do./3er.`), and no Caribbean nations in the results. Confirm via edition-number continuity (does "XII" show up again as "XIII" the following year on its own site page?) before merging or discarding either one.
- **AFBF (Asian Federation of Bodybuilding and Fitness) result PDFs — wrapped names shift the field offset and corrupt the placing.** These PDFs (Asian Amateur Championships, West Asian Amateur Championships — cached for 2018–2025) use a fixed per-competitor field sequence extracted by `fitz` as one line per field: `Name → No (bib) → Place → Born → BW/BH → RD1 → RD2 → RD3 → RD4 → Score → Country`. The **name is not always one line** — long names (common for Gulf/Arabic and Mongolian athletes, e.g. "Ahmad Hussain Mohammad" / "Ghuloom Alblooshi") wrap onto a second line. If extraction assumes exactly one name line per competitor, every field after a wrapped name shifts down by one: the bib (`No`) field gets read as `Place`, and the athlete's real placing never appears in the output. Confirmed via the 2018 Asian Amateur Championships, where this happened in 11 classes — see Step 8 of `division-recognition.md` for the general detection check. **To parse this template correctly:** don't count forward from the name assuming it's one line — instead locate the `Country` line (the last line of the block, non-numeric, a nationality) and count backward exactly 9 fields (`Score, RD4, RD3, RD2, RD1, BW/BH, Born, Place, No`); everything before that back to the previous competitor's country line is the name, however many lines it spans.

---

## nac-international.com

Covers NAC (National Amateur Championships) international contests. WordPress-based site with manually entered results.

**User-Agent (scripted/curl fetching only):** `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36`

### Listing page (Phase 1 — Discovery)

| Org | MuscleMemory suffix | Listing URL |
|-----|--------------------|-----------------------------|
| NAC | `- NAC` | `https://www.nac-international.com/results/` |

Single listing page covers all years — no per-year URL needed. Links are organized by year on the page.

### Individual contest pages (Phase 2 — Results)

URLs are WordPress slugs linked from the listing page, e.g.:
```
https://www.nac-international.com/world-championships-2025-in-larvik-norway/
https://www.nac-international.com/ms-mr-universe-2025-in-cuxhaven-germany/
```

No predictable URL pattern — slugs must be scraped from the listing page.

### Name normalization

NAC contest page titles include the year and location. MuscleMemory uses a short canonical name:

| nac-international.com page title | MuscleMemory format |
|----------------------------------|---------------------|
| `World Championships 2025 in Larvik – Norway` | `World Championships - NAC` |
| `Ms. & Mr. Universe 2025 in Cuxhaven – Germany` | `Universe - NAC` |

**Rule:** Extract the contest name (strip year, location, and "Ms. & Mr." prefix), then append ` - NAC`.

### Result page structure

**Site redesign (confirmed 2026-08-25):** NAC redesigned their results pages site-wide, replacing the old semantic `<h2>`/`<ol>` markup with inline-styled `<div>`s. Confirmed via live refetch of the 2023 Universe and 2025/2026 Worlds pages — all now serve the new markup. Any previously-cached NAC page may still hold the old `<h2>`/`<ol>` structure from before the redesign; **re-fetch (don't trust the cache) before extracting** if there's any doubt which structure a cached file has. Current (post-redesign) structure:

- Each division is a `<div id="{slug}" style="...">` block. Its first child `<div>` is the division title (plain text, e.g. `Men's Physique Masters`, `Classic Physique II`, `Men Body III`); the next `<div>` holds one child `<div>` per placing.
- Each placing line: `<div style="padding: 4px 0;">N. Name <span style="...">CCC</span></div>` — `N.` is the placing number, `CCC` the 3-letter IOC-style country code.
- "Out of Top N" trailing line (same division block, after the last placing): `<div style="...font-style: italic;...">Out of Top N: Name (CCC), Name (CCC).</div>` — these are unplaced (placing 98), country in parens.
- "DNF" trailing line, same styling: `<div style="...font-style: italic;...">DNF: Name (CCC).</div>` — skip these entirely.
- Overall winners are a separate `<div id="overall" ...>` block; each row: `<div>› <strong>{Category} Overall:</strong> Name <span style="...">CCC</span></div>`.
- A "Quick Navigation" `<div>` near the top of the page lists every division name/anchor on the page — useful as a completeness cross-check against the divisions actually parsed.
- Bare `<section>` tags exist but are unlabeled theme wrappers — not usable as division boundaries.
- Names are in First Last order — do NOT set `l 1`.
- Country information IS available (unlike npcnewsonline.com).

### NAC division name → MuscleMemory code mapping

NAC uses Roman numerals where I = tallest/heaviest and higher numbers = shorter/lighter (confirmed by 2024 height annotations: Men Body III = −172 cm, Men Body I = +179 cm).

| NAC division name | Code | Notes |
|-------------------|------|-------|
| Men Body III / Men Body III (−172 cm) | `Ba` | Shortest height class |
| Men Body II / Men Body II (172–179 cm) | `Bb` | |
| Men Body I / Men Body I (+179 cm) | `Bc` | Tallest height class |
| Classic Physique II | `Ca` | Shorter classic height class |
| Classic Physique I | `Cb` | Taller classic height class |
| Men's Physique II | `Pa` | Shorter physique class |
| Men's Physique I | `Pb` | Taller physique class |
| Men's Physique | `PH` | Single open class |
| Ms. Physique / Miss Physique | `BB` | Women's Bodybuilding equivalent |
| Ms. Figure / Miss Figure | `FI` | |
| Juniors | `JR` | |
| Masters I / Over 40 / Body Over 40 | `M4` | Universe uses "Body Over X" |
| Masters II / Over 50 / Body Over 50 | `M5` | |
| Masters III / Over 60 / Body Over 60 | `M6` | |
| Masters IV / Over 70 | `M7` | (if present) |
| Classic Physique Masters | `mc` | Masters Classic Open |
| Men's Physique Masters | `MP` | Masters Physique Open |
| Miss Figure Masters / Ms. Figure Over 40 | `FM` | Masters Figure Open |
| Bikini Shape (all variants) | — | Excluded |
| Bikini Wellness | — | Excluded |

### Overall winners

Overall winners appear in the `<div id="overall">` block described above (pre-redesign pages: a `<ul>` under an "Overall Winners" `<h2>`):

| Overall category | Code | Gender |
|------------------|------|--------|
| Bodybuilding Overall / Men Body Overall | `OP` | male |
| Classic Physique Overall | `CL` | male |
| Figure Overall | `FI` | female |
| Bikini Shape Overall | — | excluded |
| Best Präsentation | — | skip (non-standard) |

Written as placing `0`: `c OP` + `0 Name` — no country code on placing-0 lines, even though the source provides one here (see the universal Overall-entry rule in `division-recognition.md` Step 4).

### Out of Top N / DNF

- `Out of Top 10:` (or similar) entries → placing 98, with country in parentheses
- Inline `– DNF` within "Out of" entries → skip that athlete
- Standalone `DNF:` entries → skip entirely

### Known data issues

- None currently open. (Previously: Universe 2023 briefly duplicated Universe 2022 data — confirmed fixed by NAC as of 2026-08-25, alongside the site-wide markup redesign above.)

### Male/female split files

Same rules as npcnewsonline.com — separate `-male.txt` and `-female.txt` files.

**Male divisions:** Men Body I/II/III, Men's Physique (I/II), Classic Physique I/II, Juniors, Masters I/II/III, Classic Physique Masters, Men's Physique Masters
**Female divisions:** Ms./Miss Figure, Ms./Miss Physique, Miss Figure Masters, Ms. Figure Over 40
**Excluded from both:** Bikini Shape (all variants), Bikini Wellness

---

## mrolympiasudamerica.com

Official site for Mr Olympia Amateur South America, an NPC Worldwide-sanctioned event (awards IFBB Pro Cards). Results are published as PDFs, not HTML — follow the `PDF sources (any site)` section above for the general extraction method. This section covers only site-specific navigation and PDF quirks.

**User-Agent (scripted/curl fetching only):** `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36`

### Listing / results pages (Phase 1 — Discovery)

Yearly Spanish-language results pages:
```
https://www.mrolympiasudamerica.com/resultados-{year}/
```
Site history starts at 2021. No single all-years listing page — fetch each year's `resultados-{year}/` page individually.

### Locating the actual PDF

The `resultados-{year}/` page itself has no results — it links out to a PDF via a "Para ver los resultados **ingresar aquí**" link. **There is no fixed PDF URL pattern**: the path includes an upload month subfolder and a filename that both vary year to year, e.g.:
- 2024: `wp-content/uploads/2024/09/2024-NPC-Worldwide-Olympia-Amateur-South-America-Final-Placings-with-Overalls.pdf`
- 2022: `wp-content/uploads/2022/10/Mr-Olympia-Amateur-South-America-2022-Results.pdf`

Always scrape the `resultados-{year}/` page for the actual `href` — do not guess the path.

- **2021 published two separate PDFs** (`Resultados-Sabado.pdf` / `Resultados-Domingo.pdf` — Saturday/Sunday), both linked from `resultados-2021/`. Fetch and merge both.
- Every year's page also links a perennial `invitation-letter-2024.pdf` — unrelated to results, ignore it.

### Contest naming

Site name: "Mr Olympia Amateur South America" / PDF title: "NPC Worldwide Olympia Amateur South America". This is one of NPC Worldwide's "Amateur Olympia {region}" series (same family as `Amateur Olympia China/Italy/Spain/Korea/Portugal/India/Eastern Europe - NPC Worldwide`, already in the DB). Expected canonical MuscleMemory title:
```
Amateur Olympia South America - NPC Worldwide
```
Confirm via `GET /api/contests/{year}` before writing — as of 2024 this title was not yet found in the DB (the South America entry appears to be missing from the "Amateur Olympia" series).

### PDF structure

Text-selectable (not scanned), generated by muscleware.com. Consistent columnar layout per division:

```
Men's Physique - Novice
Placing Competitor #
Name
1
63
Diego Freitas Ferreira
2
67
Alisson Silva
```

- Division header line is always `{Division Name} - {Subclass}`, e.g. `Men's Physique - Open Class A`, `Men's Bodybuilding - Masters 40+`, `Women's Bikini - Open Class G`.
- Each competitor is a 3-line block: **placing**, then **competitor #** (an arbitrary registration number, not a placing), then **name**. **Do not confuse the competitor-# line with a placing value** — a competitor number of `98` appearing as the 2nd line of a block is not a "did not place" marker; only the placing value (1st line) drives the 98-collapse rule.
- No country codes anywhere in the file.
- Names are First Last order — do not set `l 1`.
- `*IFBB PRO*` is appended to names of athletes who already hold (or just earned) pro status — strip this suffix during name cleaning. Some names additionally have bare `*` wrapping (e.g. `* Julio Soares * *IFBB PRO*`) — strip all `*` characters as part of cleaning.
- Subclass wording is plain English (`True Novice`, `Novice`, `Junior`, `Masters {age}+`, `Open Class {A-G}`, `Open {Lightweight/Middleweight/Heavyweight/Super Heavyweight}`) — map via the standard `division-recognition.md` rules; apply the skill's existing True Novice/Novice/Bikini/Wellness/Fitness exclusions as usual.
- No explicit "Overall" section was found in the 2024 PDF despite the filename saying "with-Overalls" — confirm per-file whether an Overall section actually exists before writing any `0` placing (per the universal rule: never infer an overall from a class winner).

---

## musclemania.com

Musclemania's own site stopped publishing structured results after ~2018 — event pages (`musclemania.com/{show}-{year}/`), the photo/media archive, and the Team Championships page carry no per-division placings for any year from 2018 onward (checked through 2026). Overall-winner announcements only appear on Facebook/Instagram, not as structured placings.

**The DB (`Musclemania` org, no `- ORG` suffix in contest titles) caps out at 2017 for every contest variant.** Recoverable post-2017 data exists only via the Wayback Machine, from a `/scores/{year}/{show}/{division}.pdf` results system the live site used through mid-2018 and has since deleted:

```
http://web.archive.org/cdx/search/cdx?url=musclemania.com/scores/&matchType=prefix&collapse=urlkey&limit=5000&output=text
```

Filter rows to `statuscode 200` (or `warc/revisit`, which points to identical content from an earlier 200 capture) — most rows are `301`/`404`, meaning Wayback only crawled the URL after the live PDF was already gone. Fetch a real capture at its exact timestamp:

```
https://web.archive.org/web/{timestamp}/{original_url}
```

(`WebFetch` cannot reach `web.archive.org` — use `curl -L`.) As of this writing, only 2017 and 2018 have any live-captured PDFs; nothing was ever archived under `/scores/2019/` onward, so 2019+ results do not appear to be recoverable from any source.

### Contest naming

DB contest titles have **no org suffix** — `t Musclemania Universe`, not `Musclemania Universe - Musclemania`. Filenames still take an `-musclemania-` org slug per the usual convention (e.g. `2018_universe-musclemania-male.txt`).

Confirm via `GET /api/org?name=Musclemania` (case-sensitive — `MuscleMania` returns 0 results) for the full list of tracked contest names before assuming a show is new; a regional/qualifier-tier show (e.g. "Rocky Mountain", "Antelope Valley") may never have been tracked at all, which is a bigger call (new contest vs. missing division/year) than the usual gap-fill — confirm with the user before adding one.

### PDF structure

Text-selectable, one table per division, columns vary by division type:
- Physique/Model: `PLACE NUMBER NAME [CLUBWEAR/SPORTSWEAR/SWIMSUIT | ...] GRAND TOTAL`
- Bodybuilding/Classic: `PLACE NUMBER NAME [1-5 or 1-8 round scores] TOTAL [1-4 or 1-8 posing-routine scores] TOTAL GRAND TOTAL PLACE NOTES`
- `*OVERALL WINNER` appears as a NOTES annotation on the class winner's row when an explicit overall exists for that show — do not infer one otherwise.
- A competitor's bib `NUMBER` is stable across every division table in the same PDF/show — if a name is truncated or cut off in one table (e.g. a long name clipped by column width), cross-reference the same bib number in another division's table in the same document to recover the full name before writing it.
- Divisions use Musclemania's own vocabulary, not npcnewsonline's: Physique splits by height/weight (`Short`/`Medium`/`Medium Tall`/`Tall`/`X-Tall`, or `Light`/`Heavy`) rather than letter classes — map ascending (shortest/lightest first) to the generic `Pa`–`Pe` codes, regardless of whether the source's own criterion is height or weight (confirmed 2013–2018; extend to `Pf`+ only if a show has more than 5 tiers). When a show has exactly 2–3 tiers, the letters still start at `Pa` (don't skip ahead). `Junior` → `PJ`. `Teen`/`Teenage` → `PT`. Physique Pro → `PP` (not `PR` — `PR` is Bodybuilding Pro in this org's existing DB data); use `PP` even where the source's own "Professional" table isn't height-split. Bodybuilding uses flat weight-class names (`Lightweight`/`Middleweight`/`Heavyweight`) with no letter suffix → `LW`/`MW`/`HW`; `Master`/`Masters` (no age number given) → `MA`. `Model` and `Bikini` divisions are excluded per the standard skill-wide exclusion list. `All Forces`/`All-Forces` (a military-tribute show, not a division) → excluded entirely per the armed-forces/military exclusion, even though it has real placings.
- **Two tables both titled the same class name** (e.g. two "Physique Open" tables, no Short/Tall distinction given) has been seen at least once (Orange County 2015) — treat presentation order as the tiebreak (first table → `Pa`, second → `Pb`) rather than guessing at a height/weight split that isn't labeled.
- **Blank placing rows after the ranked finalists** (a `Placing`/`Rank` column with numbers 1–5 then several rows with no number, still carrying scores) is this org's version of the "didn't final" bucket — treat exactly like the standard 98-rule: those unranked-but-scored rows all become placing `98`. Seen repeatedly (Asia 2015, Universe 2014/2015) once a class has more entrants than finalists called out.
- **An "Overall Champion — {Name}" line below all the sub-class tables** (not a separate scored section, just a caption naming the champion) is a legitimate explicit overall — write it as `c PH` + `0 {Name}`, same as the sub-class-comparison overall pattern elsewhere in this skill. Seen at Asia 2015 and Universe 2014 (the latter as `***Overall Winner` next to the winning row instead of a caption).
- **A `data-slug`-free show name doesn't necessarily mean a new/untracked contest** — confirm via `GET /api/org?name=Musclemania` and `GET /api/contest/years?name=Musclemania+{Name}` before assuming: `14-capital` turned out to already be the long-tracked `Musclemania Nations Capitol` (DB years back to 2001), not a new show. Once identified, `Antelope Valley`, `Lone Star`, `New Mexico`, `Orange County`, `Rocky`/`Rocky Mountain`, `Paris`, and `Central America` were each confirmed genuinely untracked (added as new contests in 2013–2015).

---

## ukbff.co.uk

UK Bodybuilding & Fitness Federation (UKBFF) — IFBB's British national federation. Results are published as **scanned image JPGs embedded in Squarespace blog posts**, not HTML text or PDF — this source needs the same free-text/image-reading approach as `PDF sources (any site)`, but read as images (via the `Read` tool) instead of `fitz` text extraction.

**User-Agent (scripted/curl fetching only):** `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36`

### Listing page (Phase 1 — Discovery)

```
https://www.ukbff.co.uk/show-results
```

Squarespace blog listing, paginated via `?offset={timestamp}` ("Older" link at the bottom). **The archive is short — confirmed exhausted at 17 total posts**, spanning roughly Nov 2017 to Oct 2019 (the site stopped posting show-results after Oct 2019; nothing from 2020 onward exists on this page as of 2026-08-28). Paginate until the "Older" link disappears or an offset repeats already-seen posts, then stop — don't assume more pages exist.

### Individual contest pages (Phase 2 — Results)

No predictable URL pattern — slugs must be scraped from the listing page, e.g.:
```
https://www.ukbff.co.uk/show-results/2019/10/19/ukbff-british-final-2019-results
https://www.ukbff.co.uk/show-results/2018/4/8/ukbff-nationals-2018
```

The HTML page itself carries almost no text (just the title, author, date) — results live entirely in `<img>` tags pointing at `images.squarespace-cdn.com`, one JPG per scanned results page (a typed table, not handwritten — legible). Extract every `src="https://images.squarespace-cdn.com/...jpg"` URL from the cached HTML, download each image into its own subfolder under `.page_cache/`, and read them with the `Read` tool (image mode) — one contest can span 4–21 images. A contest may post its images in two separate batches on the same page (e.g. "British Finals Day 1" / "Day 2") — both batches belong to the same contest/year, treat them as one combined set of pages.

### Contest naming

Only two UKBFF series exist in the DB as tracked amateur contests (confirmed via `GET /api/org?name=IFBB`, 2026-08-28) — other UK-named IFBB entries (`British Grand Prix`, `British Pro Championships`, `UK Bodypower Pro`, `Arnold Classic UK`, `Sheru Classic UK Pro`) are Pro-tier shows, not this federation's amateur results:

| ukbff.co.uk post title | MuscleMemory format |
|-------------------------|----------------------|
| `UKBFF British Final {year}` / `UKBFF British Final {year} Results` | `British Championships - IFBB` |
| `UKBFF Nationals {year}` | `UK Nationals - IFBB` |

Other post titles on this listing (`UKBFF Midlands Championships`, `UKBFF South Coast`, `UKBFF North East/North West/Scottish/Welsh Championships`, `UKBFF Classic`, `Kent Klassic`, `IFBB English Grand Prix`) do not match either tracked series — regional/qualifier-tier UKBFF shows with no corresponding DB contest name. Do not extract these without confirming a new contest with the user first (same as any never-tracked contest — see `musclemania.com` guidance above for the analogous judgment call).

### Result page structure (from image content)

Confirmed via 2018 UK Nationals page 1: typed table per division, columns `PLACE | NR | NAME | TOWN | BORN | BW/HEIGHT | R1(x2) | R2 | Score`, with a `Σ=N` entrant-count line under each table. Division headings are plain English (`JUNIOR BODYBUILDING`, `MASTERS MEN BODYBUILDING`, `WELLNESS`, etc.) — apply `division-recognition.md`'s free-text method, same exclusions as any other source (Bikini/Wellness/Fitness/Novice/etc. excluded as usual). Names are in First-order left-to-right as printed — confirm order per contest before assuming (not yet verified across all pages).

No country codes. `TOWN` column is not a competitor attribute the DB tracks — ignore it.

### Known gaps

As of 2026-08-28, DB coverage for `British Championships - IFBB` runs 1989–2016 (with internal gaps at 1990/1992/1994/1995/1997) and stops entirely after 2016; `UK Nationals - IFBB` only has 2013/2015/2016. This listing page's archive (2017–2019) can fill: **British Final 2017, British Final 2019, Nationals 2018, Nationals 2019** — no British Final 2018 post exists on the blog (not found in the 17-post archive; unconfirmed whether the show wasn't held that year or simply wasn't posted). Years before 2017 or after 2019 are not recoverable from this source at all — the blog doesn't cover them.

---

## aausports.org

AAU (Amateur Athletic Union) "Strength Sports" program — covers Powerlifting, Weightlifting, Feats of Strength (FOS), MAS Wrestling, **and** Bodybuilding under one umbrella. Only the Bodybuilding results are in scope for this skill; the site's listing page is dominated by non-bodybuilding meets that must be skipped. Results are published as PDFs — follow the `PDF sources (any site)` section above for the general extraction method. This section covers site-specific navigation, the Cloudflare block, and how to separate Bodybuilding from the other strength sports.

### Site is Cloudflare-protected — no automated fetch

Confirmed 403 via curl with both a browser UA and the Googlebot UA — the response is a genuine Cloudflare JS-challenge page ("Attention Required! | Cloudflare" / "Sorry, you have been blocked"), not a simple User-Agent check, so there is **no UA-swap workaround**. WebFetch also 403s.

**Listing page:** must be fetched manually. Ask the user to save it from a real browser (File → Save Page As → "Webpage, Complete") into `~/workspace/musmem/.page_cache/`, then read the saved `.html` file directly. A browser save produces a default-named file (e.g. `Strength Sports Results _ AAU.html`) plus an accompanying `..._files/` asset folder — the `_files/` folder can be ignored (only needed for the browser's own rendering, not text extraction); the HTML file itself is fine to read under its default name, no need to rename to the usual URL-derived cache key.

**Individual result PDFs:** hosted off-domain at `image.aausports.org` and `s3(.us-east-1).amazonaws.com` — not confirmed whether these bypass the Cloudflare challenge on the main site. Try a normal curl fetch first; if a PDF also 403s, ask the user to save it manually the same way as the listing page.

### Listing page (Phase 1 — Discovery)

```
https://aausports.org/strength-sports/strength-sports-results
```

Single listing page covering all years — no per-year URL. Links are a flat, reverse-chronological list of PDF result files for every AAU strength-sports discipline mixed together, spanning roughly 2002–2024 in the confirmed 2026-09-10 snapshot.

**Bodybuilding-relevant window confirmed (2026-09-10 snapshot):** Bodybuilding links appear only **2017–2021**; none found for 2022 onward or pre-2017 in that snapshot. Re-check the full list on any refresh in case new events are posted, rather than assuming this window is permanent.

### Identifying bodybuilding-relevant links

Link text (not the URL) names the sport(s) covered by that PDF. Only follow links whose title contains "Bodybuilding" (filenames sometimes abbreviate it as `BB`, e.g. `US-PL-NationalBB-SL-AtlanticCity.pdf` — check filenames too, not just visible link text, since a couple of bodybuilding-bearing files had non-bodybuilding-sounding link text). Many of these titles bundle bodybuilding together with other strength sports in **one shared PDF** — confirmed examples from the 2026-09-10 snapshot:

| Link text | Sports bundled in the one PDF |
|-----------|-------------------------------|
| AAU Universe Powerlifting, Weightlifting & Bodybuilding Championship | PL + WL + BB |
| AAU North American Powerlifting, Weightlifting, FOS & Bodybuilding Championship | PL + WL + FOS + BB |
| AAU International Powerlifting, Weightlifting & Bodybuilding Championship | PL + WL + BB |
| AAU World Powerlifting, Weightlifting & Bodybuilding National Championship | PL + WL + BB |
| AAU North American Powerlifting & Bodybuilding Results | PL + BB |
| 2021 Worlds PL, WL, FOS, Fitness & BB | PL + WL + FOS + Fitness + BB |
| AAU International Bodybuilding & Fitness | BB + Fitness (excluded division) |
| AAU Universe Bodybuilding / AAU World Bodybuilding / AAU National Bodybuilding | Bodybuilding only |
| AAU Natural International Bodybuilding / AAU Natural National Bodybuilding | Bodybuilding only ("Natural" i.e. tested — part of the contest name here, confirm with user whether this is a separate MuscleMemory title or folds into the plain title, first occurrence) |
| AAU North American & USA Masters Bodybuilding | Bodybuilding (Masters) bundled with other North American results in the same document |

For any bundled PDF: locate the Bodybuilding section boundary first (by in-document heading) and parse only within it — do not assume the rest of the document (Powerlifting/Weightlifting/FOS/MAS Wrestling sections) is in scope, and do not let a Powerlifting or Weightlifting class heading get mistaken for a Bodybuilding division.

A few links are shortened via `tinyurl.com` — resolve to the underlying PDF URL (e.g. `curl -sI` to follow the redirect) before caching; the tinyurl redirect page itself isn't the content to cache.

### PDF structure

No fixed template confirmed yet — these are AAU-authored multi-sport meet-report PDFs and format is expected to vary by event/year, same caveat as the general `PDF sources` section. Follow `division-recognition.md`'s free-text method for whatever Bodybuilding section is found. Not yet confirmed as of this writing (establish during first real Phase 2 extraction):

- Column layout / class structure within the Bodybuilding section
- Whether country codes are present (AAU is a US-based org — plausible they're absent, like npcnewsonline.com, but unconfirmed)
- Name order (First Last vs Last, First) — verify per contest before assuming, do not assume it matches npcnewsonline.com
- Whether "Masters" and "Natural" bodybuilding results use their own division codes/contest-title suffix or need a user decision, first occurrence of each

### Contest naming

**No existing AAU contests in the DB overlap this era.** The DB's tracked `- AAU` contests run 1938–1999 (Mr/Ms America, Mr/Ms USA, Universe, and dozens of regional titles — e.g. `Universe - AAU` last appears in 1988) — a decades-long gap before aausports.org's 2017–2021 results begin.

**Per user decision (2026-09-10):** treat every aausports.org bodybuilding contest as a **new** MuscleMemory contest. Naming rule: take the base event name (Universe / World / National / International / North American / Natural International / Natural National), replace the word "Bodybuilding" with "Championships", and append ` - AAU`. Do **not** try to map it onto an old 1938–1999 title, even where the base word matches — e.g. `Universe Championships - AAU` is a new title, not a continuation of the DB's dormant `Universe - AAU` (checked against the DB: closest overlap by name, but still a new title per this decision; the other six have no DB overlap at all, not even a close one).

**Confirmed new contests, with years, from the 16 PDFs fetched and read 2026-09-10** (see list below) — this is the actual title/year list to extract, superseding the speculative per-link-text table above:

| MuscleMemory title | Years confirmed |
|---|---|
| `North American Championships - AAU` | 2017, 2018, 2019 |
| `World Championships - AAU` | 2017, 2018, 2019 |
| `International Championships - AAU` | 2017, 2021 |
| `Universe Championships - AAU` | 2018, 2019, 2021 |
| `National Championships - AAU` | 2019 |
| `Natural International Championships - AAU` | 2018 |
| `Natural National Championships - AAU` | 2018 |

Source PDF → title/year mapping (all cached in `~/workspace/musmem/aau-pdfs/`, manually downloaded by the user since even the off-domain `image.aausports.org`/S3 PDF hosts sit behind the same Cloudflare block as the listing page):

| PDF filename | Title | Year | Notes |
|---|---|---|---|
| `2017VistaJuneResults.pdf` | North American Championships - AAU | 2017 | Year inferred from filename/folder — no explicit year in doc text |
| `2017AAUWorldsFinalResults.pdf` | World Championships - AAU | 2017 | Bundled with PL+WL; year inferred from filename — no explicit year on the BB page itself |
| `2018AAUInternationalDecemberResults.pdf` | International Championships - AAU | 2017 | Bundled with PL+WL; explicit "DEC 16 2017" found in doc. Filed under the site's 2018 folder but event itself was Dec 2017 |
| `2018AAUNORTHAMERICANFINALCompleteResults.pdf` | North American Championships - AAU | 2018 | Bundled with PL/WL/FOS; explicit date/year in doc ("April 7" 2018) |
| `2018AAU-Universe-Results.pdf` | Universe Championships - AAU | 2018 | Bundled with PL+WL; explicit "DEC 16 2018" |
| `2018WorldBodybuildingResults.pdf` | World Championships - AAU | 2018 | Bodybuilding-only; explicit year in doc |
| `AAUInternationalNatural-Results.pdf` | Natural International Championships - AAU | 2018 | Bodybuilding-only; explicit "2018" in doc |
| `AAUNaturalNationals-Results.pdf` | Natural National Championships - AAU | 2018 | Bodybuilding-only. **Tentative year** — no explicit year in doc text, inferred only from site folder placement |
| `19-NorthAmerican-PLBB-Results.pdf` | North American Championships - AAU | 2019 | Bundled with PL; year inferred from `19-` filename prefix — no explicit year in doc |
| `2019-AAUNationalBodybuilding-June29.pdf` | National Championships - AAU | 2019 | Bodybuilding-only. Year inferred from filename |
| `2019-AAUUniverseBodybuilding-Nov2.pdf` | Universe Championships - AAU | 2019 | Bodybuilding-only; explicit "NOV 2 2019" |
| `2019AAUWorldBodybuilding-Sept28.pdf` | World Championships - AAU | 2019 | Bodybuilding-only. Year inferred from filename |
| `International-BB-Fitness-LasVegas.pdf` | International Championships - AAU | 2021 | Uses "CLASSIC BB" abbreviation, not spelled-out "Bodybuilding" — confirm by reading full text, not just a "bodybuild" keyword search, which misses this file. Also has Physique, Figure, Bikini, Fitness, Sports Model, Angel, Classic Swim divisions |
| `UNIVERSE-2021-RESULTS.pdf` | Universe Championships - AAU | 2021 | Classic Physique, Classic Bodybuilding, Fitness, Sports Model, etc. |

**Two of the 16 fetched PDFs contain no bodybuilding data at all** — confirmed by reading full text, not just keyword search — and are excluded entirely:
- `2021-AAUWorlds-September.pdf` — pure powerlifting/weightlifting/FOS
- `US-PL-NationalBB-SL-AtlanticCity.pdf` — pure powerlifting, despite "BB" in the filename

Always confirm via `GET http://localhost:3000/api/org?name=AAU` (see `musclememory-api.md` / SKILL.md Phase 1 Step 1 — use the local server, not musclememory.net/.org directly) before writing a title as new — a title that looks new may already exist under slightly different modern wording not yet seen.

### Male/female split files

Same rule as npcnewsonline.com — separate `-male.txt` and `-female.txt` files when a contest has both genders.

---

## worldnaturalbb.com

WNBF = pro branch, INBF = amateur branch, of the same federation. A combo event posts both sides on one page.

### Page structure — no fixed template

Unlike npcnewsonline.com, this site's HTML structure changes from page to page, sometimes even within the same contest series across consecutive years (e.g. Hercules 2017 vs 2018 vs 2019 vs 2022 each use a different layout). Confirmed variants seen so far:
- `<h1>`/`<h2>WNBF PRO</h2>` + `<h2>INBF AMATEUR</h2>` section markers, each followed by `<p><strong>Division</strong><br>Qualifier</p>` heading paragraphs and either a following `<p>1 Name<br>2 Name</p>` placings paragraph or an `<ol class="wp-block-list"><li>Name</li>...</ol>` (placing = list position).
- No section markers at all — pro and amateur divisions run together in document order, distinguished only by whether the division heading itself says "Pro"/"WNBF Pro".
- Heading and qualifier can appear split across `<strong>Heading</strong><br>Qualifier` (qualifier outside the strong tag) **or** `<strong>Heading<br>Qualifier</strong>` (qualifier inside it) — check both when parsing.
- 2025+ pages use a completely different "Competition Results" custom post type: `result-card` components with a 3-place podium `<ol class="...podium-wrapper">` (placement number and name in separate `<p>` tags) plus a 4th-place-and-beyond `<ol start="4">` with **name only, no placement number** — easy to silently miss if only scraping the podium markup.
- Overall-round markers appear inconsistently: sometimes a separate `*Overall`/`World Champion` list entry immediately after the real winner, sometimes suffixed onto the winner's own name/line (`1 Seung Hyeon Kim *overall winner`). A naive "does this line contain 'overall'" check will wrongly discard the winner's name in the second case — strip the suffix instead of discarding the whole line.

### INBF naming cutover — 2024/2025

Last confirmed "INBF"-branded page: `2024 INBF Gunz Classic Results` (20 mentions). Every page under the 2025+ "Competition Results" post type (~19 checked) has **zero** mentions of "INBF" anywhere, including for events that are clearly amateur-tier (e.g. title is literally "2025 WNBF Amateur World Championships", not "INBF World Championships"). The org folded INBF into WNBF as a labeling distinction ("WNBF Amateur" vs "WNBF Pro") rather than a separately-branded organization, coinciding with the site's template migration. Don't assume a 2025+ page's "INBF"-free wording means the amateur/pro divisions are combined into one title, though — check case by case (see Hercules below).

### Hercules — canonical title split by era

- **2014–2022** (combo pages, INBF-branded): use the existing split — pro side → `Pro Natural Masters - WNBF`, amateur side → `Natural Hercules International - INBF`. Every pro result at Hercules in this era was masters-qualified (no bare/open pro division ever appeared) — confirmed across 2014, 2015, 2017, 2018, 2019, 2022.
- **2024 onward**: per user decision, both sides are now tracked under one unified title, **`Hercules Pro/Am - WNBF`**, because (a) INBF stopped being used as of 2024 and (b) starting 2025 the pro side is no longer exclusively Masters — a bare, non-masters "Pro Men('s) Bodybuilding"/"Pro Women's Bodybuilding"/"Pro Men's Physique" result now sits alongside "Pro Masters...". Use the `P`-prefixed division codes (`PB`, `PP`, `PM`/`PM4`/`PM5`/`PM6`/`PM7`, `PCL`/`PCa`-`PCd`, `PCM` [Pro Classic Physique Masters], `PP`/`PPa`-`PPd`, `PF`/`PFa`/`PFb`, `PFM`, `PMP`) for the pro-side divisions in this unified file, and the ordinary amateur codes (`OP`/`BB`/`M4`/`Fa`/`Fb`/etc.) for the amateur-side divisions — no collision since the two families are disjoint. See `divisions-reference.md`'s "Pro divisions" section.
- The bare non-masters "Pro" result's real nature (genuine second pro contest vs. a qualifier/pro-card-award showcase) is still not fully confirmed — went with treating it as real placings under `PB`/`PP` per the above rather than leaving it out, since a title now exists to hold it.
- No page has ever branded Hercules "International" — that word in the DB title `Natural Hercules International - INBF` is a MuscleMemory naming convention, not something this site uses. Every "International" hit on a Hercules page is the sitewide nav-menu "International Events" link, unrelated to the contest.

### Naturalmania — same era split, canonical title `Naturalmania Pro/Am - WNBF` for 2025+

Same pattern as Hercules, confirmed independently. Every year 2015–2022 titled the page with "Universe" explicitly paired with "Naturalmania" (`RESULTS 2015 INBF Naturalmania and WNBF Pro Universe`, `RESULTS 2016 WNBF Pro Universe and INBF Naturalmania`, `RESULTS: Universe & Naturalmania`, `Pro Universe & Naturalmania`, etc.) — pro side → `Pro Natural Universe - WNBF`, amateur side → `Naturalmania Nationals - INBF`. In 2025 the title becomes "2025 WNBF Naturalmania Nationals Pro Am | New York" — "Universe" is gone entirely, and the page has both a "Pro Masters..." tier and a separate bare "Pro Men's Bodybuilding"/"Pro Figure"/"Pro Classic Physique"/"Pro Men's Physique" tier, exactly like Hercules. Per user decision, 2025 onward uses one unified title, **`Naturalmania Pro/Am - WNBF`**, with the same `P`-prefixed pro codes + ordinary amateur codes convention as `Hercules Pro/Am - WNBF`.

The 2025 Naturalmania page also gave direct confirmation of the pro-card-qualifier theory: two amateur Open-division winners are tagged `*Overall & WNBF Pro Card` / `*WNBF Pro Card` right in their placing line (David Birger, Open Classic Physique Short; Destiny Aghedo, Classic Physique Tall) — i.e. winning the amateur open class earns a pro card, and that person may then also show up in the bare "Pro..." list. This doesn't change the extraction (both tiers are still written, under `P`-codes for pro and ordinary codes for amateur), it just explains why the bare "Pro" tier's roster overlaps with amateur standouts.

### Division-name quirks confirmed on this site

- **Fit Body** (any qualifier) — excluded, no MuscleMemory code. Confirmed via 2019 INBF Hercules: its roster is the same women doing double/triple duty across Figure-family divisions the same day, i.e. a toned-but-not-muscular judged category rather than a separate discipline.
- **Debut** (Bodybuilding/Bikini/Classic Physique/Men's Physique) — excluded, same entry-level concept as Novice/Beginner/First Timer. Confirmed via 2025 WNBF Hercules Pro Am.
- **"Classic Figure" + an age number** (e.g. "Classic Figure 50+") — maps to Masters Figure at that age (`F5`, etc.), same as a bare "Master's Figure {age}" heading, but only when its roster adds at least one competitor not already in the bare Master's Figure list on the same page (confirmed via 2018 Naturalmania Nationals, where "Classic Figure 50+" included Jamil Miller who wasn't in "Master's Figure 40+").
- **Bare "Classic Figure"** (no age number) — excluded; it's a distinct WNBF/INBF division with no MuscleMemory code, not simply a duplicate of Master's Figure. (An earlier theory that a subset roster with matching relative placing order proved it was a non-informative duplicate was wrong and was retracted — a smaller field getting its own real placing is legitimate data. The actual reason to exclude it is just that no code exists.)
- **Two identically-labeled age brackets with no distinguishing qualifier** (e.g. two separate "Men's Bodybuilding | Masters 40+" lists on one page, different rosters) — do not resolve with a heuristic (roster size, list order, etc.) and do not generalize a fix from one instance. Stop, note the conflict, and give the source URL for a fresh per-page judgment call each time. (One occurrence was resolved this way — the smaller list was judged to actually be Masters 50+ — for 2018 INBF World Championships specifically; that was a one-off call, not a standing rule.)
- **"Grandmasters"/"Grand Masters" + an explicit age number** (e.g. "Grand Masters Men's Bodybuilding 50+") — maps directly to that age's code (`M5`, `PM5`, etc.); the "Grand" wording is just this site's flourish, not a distinct bracket.
- Country codes, when present in parens after a name (seen on `Pro Natural International - WNBF` pages), get written as-is per the existing country-code rule.

### Discovery gaps — title/category metadata can miss real content

The listing-page tags and WordPress category taxonomy are **not reliable** for deciding which DB title a page belongs to — several genuine matches were only found by opening the page and reading the actual results:
- 2017 and 2025 Hercules pages both had a real WNBF Pro Masters section that the category/title text gave no hint of (tagged generically, e.g. just "INBF").
- A same-titled event can be a completely different show than it looks — `Natural USA - INBF`'s real match is a literally-named "INBF Natural USA" page, *not* the California/LA "Natural Muscle Mayhem" pages, despite Muscle Mayhem's WNBF pro side genuinely being `Pro Natural USA - WNBF`. Confirmed by roster comparison (Muscle Mayhem scored 3-6% overlap against the DB's existing `Natural USA - INBF` years; the correctly-named page scored 100%).
- Four "Universe & Naturalmania" pages (`results-universe-naturalmania`, `-2`, `-3`, `results-pro-universe-naturalmania-2`) had no year anywhere in the HTML (title, dates, image *filenames*) and completely different rosters from each other. Resolved by looking at the images themselves (not just filenames) — they visibly state 2021, 2018, 2017, and 2022 respectively. Roster-cross-checked the first three against already-extracted years and confirmed they're duplicate postings of events already covered from other pages; the fourth (2022) was genuinely new and closed out the last gap in `Pro Natural Universe - WNBF` / `Naturalmania Nationals - INBF`. Lesson: page text/metadata missing a year doesn't mean the year is unrecoverable — check the images themselves before giving up on dating a page.
- **Always roster-verify a title/page match against an overlapping DB year before trusting it**, the same discipline as any other source — an 80–100% name-overlap score is a real confirmation (the shortfall is normally spelling drift, e.g. `Lytle`/`Lyle`, `Duerr`/`Duer` — not missing people); a single-digit-percent score means the page is the wrong event entirely.

<!-- Add future sources here in the same format -->

## nationalgym.com (NGA)

### Listing page (Phase 1 — Discovery)

`https://www.nationalgym.com/national-gym-past-contest-winners.html` — one page, all years (2009–present), grouped by year. **A browser User-Agent returns 403; use the Googlebot UA** (`Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)`).

- Most entries link straight to a results PDF: `{YYYY}-nga-past-contest-winners/{MMDDYY}-nga-....pdf` (relative to site root; filenames contain spaces/typos, so URL-quote them).
- The year-end nationals (Pro Universe / Amateur Universe / American Natural, plus Florida National through 2014) link to `{YYYY}-nga-nationals-show-results.html` instead (no 2020 edition), which in turn links the PDF(s). 2012–2016 have one PDF per contest; 2017+ is a single combined `...-NGA-Pro-AM-Universe-American-natural-Championships.pdf`. The 2023/2024 pages use `../` relative hrefs — strip them.
- Cache key: `nationalgym_` + path with `/` and spaces → `_`.

### Contest scope

The DB tracks only NGA's national/pro tier (Pro Universe, Universe, American International/Nationals, Pro World, Pro Galaxy, US Natural Championships, Florida Natural, Potomac Cup, etc.). The ~250 local/regional shows on the listing were never tracked — adding any of them is a new-contest decision for the user.

### Site title → DB title (confirmed by user / roster match, 2026-10-01)

| Site title | DB title | Notes |
|---|---|---|
| American International (2010–2012), American National (2013–2014) | `American International - NGA` | Same series; renamed on the site 2013–14 (2012 PDF filename already says "national"). User-confirmed. |
| Pro Universe / "PRO" divisions of the PRO/AM Universe | `Pro Universe - NGA` | |
| Amateur Universe / non-PRO Open+Masters divisions of the PRO/AM Universe | `Universe - NGA` | |
| United States & Pro Galaxy (Bloomfield/East Orange, NJ) | `US Natural Championships - NGA` (amateur) + `Pro Galaxy - NGA` (PRO divisions) | 2016–17 DB rosters match this PDF. |
| Pro World & NJ State Open | `Pro World - NGA` (PRO divisions) | 2017 DB roster matches 9/9. |
| Canadian Championships (Toronto) | `Canadian Championships - NGA` (new, user decision) | Only 2015 on site. PDF has two unlabeled "Men's Bodybuilding – Masters" classes: Avery/Nelson class → `M4`, Jefferson class → `M5` (user decision, 2015 only). |
| North American Championships & Ed Cole Pro Classic (Wilkes-Barre, PA) | `North American Championships - NGA` (new, user decision) — non-PRO divisions | 2017–2019 on site. `PRO` divisions are the Ed Cole Pro Classic — see table below. |
| NGA/FIBBN Italian Championships | `Italian Championships - NGA` (new, user decision) | 2016 Pescara, 2017 Padova. |

### Not tracked *as of 2026-10-01* — revisit when the site posts new years

These are **point-in-time judgments about the years that were posted when reviewed**, not permanent exclusions. Per the per-year rule in the skill (Phase 1 Step 2), on every run check the listing for years **newer than "years reviewed"** or a changed format (e.g. open divisions added, a national-level name, a pro tier that starts feeding a tracked title) and bring those back to the user rather than silently skipping them.

| Site title | Years reviewed | Why not tracked (at that time) |
|---|---|---|
| American Natural (nationals, 2015+) | 2015–2025 | Every year reviewed had only Novice/Debut/Teen/Junior/Collegiate/Kids and beginner-masters classes — no open divisions. A year with open divisions should be re-raised. |
| US Championships / PRO/AM USA (Madison, WI) | 2017–2018 | Different show from the NJ US Natural Championships (0/6 roster overlap with DB 2017). Regional-level when reviewed. |
| Florida Natural State Championships (Ormond Beach) | 2015, 2017 | Different show from DB `Florida Natural - NGA` (0/18 overlap with DB 2015). State-level. |
| NGA/FIBBN North Italy Selection (Torino) | 2018–2019 | Regional qualifier, not the national Italian Championships. |
| Ultimate Fitness Championships + "NGA PRO United States" (Coral Springs, FL); predecessor Florida Ultimate Physique (Lauderhill, FL) | 2018–2019 | Local South Florida PRO/AM (promoter Anthony Boulware); "PRO United States" looked like its pro tier, not a national show or Pro Galaxy successor. |
| Natural Olympian PRO/AM (Rohnert Park / Folsom, CA) | 2017–2019 | Regional NorCal PRO/AM (promoter Johnny Carrero), small fields. |
| Pro tiers attached to amateur shows: Ed Cole Pro Classic (with North American), Dave Spindel Pro Classic (with Potomac Cup), Mid-Atlantic PRO Blowout (with Mt. Rogers), NGA PRO Atlas (with Northwest Natural), Florida PRO (with Florida State) | through 2025 | Not tracked for now (user decision 2026-10-01). When extracting the paired amateur show, leave these `PRO` divisions out but note them in the results summary. |
| All other state/local shows on the listing (~250) | 2009–2026 | Never tracked; not reviewed individually. Any show that later looks national-level is a new-contest decision for the user. |

### Overall winners in NGA PDFs

NGA PDFs mark overall winners with a note under a class winner ("NGA PRO Card & Overall", "Overall 1st", etc.), not a separate overall section.
- Note on an **Open** class winner → `0 {Name}` under the open code (`OP` for Men's BB).
- Note on a **Masters** class winner and **no other overall winner listed** for that division → that athlete won the overall: `0 {Name}` under the open code, not `MA` (user decision 2026-10-01).

### Known data issues / per-contest decisions (user, 2026-10-02)

- 2014 American National PDF lists "Israel Hernandez, Jr." 1st in Women's BB — male athlete, source error. Dropped; Marilyn Hightower renumbered to 1st.
- 2018 Universe "Women's Phys - Masters 39+" → `P4`.
- 2018 United States Championships "Paralympic Physique" → `Hs` (female file).

### Missing divisions

Men's Physique was omitted from the DB for `Pro Universe - NGA` and `Universe - NGA` 2016–2017 although the PDFs have it — add as missing divisions (user decision 2026-10-01).

### Nationals PDF section boundaries (2015+)

The year-end nationals ran three contests the same day: Pro Universe, Amateur Universe, American Natural. 2016 has three PDFs; 2017 has one PDF with section headers; **2018+ has one PDF with no section headers** (the nationals HTML page's three links all point to the same file). Split by content:
- Division prefixed `PRO` → `Pro Universe - NGA`.
- Unprefixed Open/Masters divisions listed before the Novice/Debut block → `Universe - NGA`.
- From the first Novice/Debut division onward (including any Collegiate, Teen, Junior, Kids, Couples, and stray masters classes such as 2025's "Men's BB – Masters 35-39") → American Natural, which is not tracked as of 2026-10-01 (see table above). If a year's American Natural block contains open divisions, stop and raise it instead of skipping.
- Notes like "NGA PRO Card & Overall **Italian**" / "2nd Overall **American**" (2018) are nationality awards within the amateur section, not contest labels.

## wbpsf.org (WBPF / ABBF / EBPF)

World Bodybuilding & Physique Sports Federation, with its continental bodies ABBF (Asia), EBPF (Europe), SEABPF (South-East Asia) and SABPF (South Asia). The site is plain static HTML, but it **can be very slow** (20–30 s per request at times; at other times ~1 s). Use curl with `-m 90`+ and a browser UA. First crawled 2026-10-06; everything is cached under `~/workspace/musmem/.page_cache/wbpf/` (`*.html` pages, `pdf/` PDFs, `img/` result images, `_crawl_state.json` = every linked doc URL, `pdf/_manifest.json` / `img/_manifest.json` = local file → source URL).

### Listing pages (Phase 1 — Discovery)

- `Past%20Event.html` — the real index. One accordion block per event with `Result | Report` links (`href="#"` or no link = nothing posted). Many hrefs use backslashes (`PDF\Result\...pdf`); replace `\` with `/` before fetching.
- `News.html` — news archive by year. 2022+ result posts link per-class JPGs under `images/demo/Big News/{event} Result/...`. Pre-2017 news items link PDFs under `pdf/News/` (day-by-day results for 2013 Worlds, 2013/2014/2016 Asians).
- `Mr%20Universe.html` — Mr Universe overall winner per year, 2009–2025 (no 2020).
- `Event.html` — upcoming events + entry forms (no results).

### Contest naming

| Site title | DB title | Notes |
|---|---|---|
| {N}th WBPF World Bodybuilding & Physique Sports Championships (1st = 2009) | `World Championships - WBPF` | DB has 2009–2014. |
| WBPF Mr Universe (overall winner of the Worlds) | **no separate contest** — the `0` (overall) line of `World Championships - WBPF` (user decision 2026-10-06) | Same event as the Worlds: the men's BB overall. `Mr%20Universe.html` lists the winner per year (2009–2025, no 2020) and is a cross-check for the World `0` line. |
| {N}th Asian Bodybuilding & Physique Sports Championships (ABBF; 47th = 2013) | `Asian Championships - ABBF` | DB has 2009, 2011–2014, 2016. 2025 was held jointly with the 19th SEA Championships ("57th Asian cum 19th South East Asian"), one combined report. |
| {N}th WBPF/EBPF European Championships | `European Championships - WBPF` | DB has 2011–2013. |

### Result formats seen

- **Score-sheet PDFs** ("FINAL PLACES COMBINED SCORE SHEET"): text layer, columns are No. / Competitor / Country / Round 1 / Round 2 / Total / Place, full placings. Used for World 2018, 2023, 2024, 2025 and Asian 2024. Asian 2018 (`52nd Asian Championship.pdf`) is the same sheet but **scanned, with no text layer**.
- **Event-report PDFs**: narrative + one page per class with a text table, with full placings or the top 5/6 (World 2019, 2021, 2022; Asian 2019, 2022, 2023, 2025).
- **Photo-card reports**: European 2024 is 40 image-only pages, each a card for one class with places 1–5 + country.
- **Photo-caption PDFs** (2013–2016): placings embedded in captions ("Salar Madady - 2nd place Silver Medalist (Iran)"), usually top 5.
- Names are mostly upper-case, and order varies (Indian/Thai/Vietnamese names are often given surname-first or as a single token). Treat name order per row, not per file.

### abbf.asia (live) — mirror of wbpsf.org, sometimes ahead

abbf.asia is **live** (checked 2026-10-06). Its current site uses the same layout and file paths as wbpsf.org (`Past%20Events.html`, `PDF/Result/...`); files at the same path are byte-identical. Crawl it too, because it can post results before wbpsf.org links them: the 58th Asian 2026 full result (`PDF/58th-ABBF-2026/58th-ABBF-2026-Full-Result.pdf`, plus per-class images under `images/demo/Big News/58th-ABBF-2026/`) was only on abbf.asia. Cache: `~/workspace/musmem/.page_cache/abbf_live/`.

### ABBF archive — abbf.asia on the Wayback Machine

ABBF's own site was **abbf.asia**; abbf.org was only a parked domain. abbf.asia is well archived (2009–2026, about 685 PDFs). Look up captures with the CDX API (`web.archive.org/cdx/search/cdx?url=abbf.asia&matchType=domain&output=json`) and fetch raw files with the `{timestamp}id_/` form. News items are files named `DDMMYYYY[a-z].pdf/.html`, and a dated `index.html` snapshot maps them to their titles. Known result sets: 2011 (45th, Bangkok) has per-class PDFs `00-01.pdf`…`00-20.pdf`, indexed by `30102011a.html`; 2012 (46th, Guangzhou) has `27092012.pdf`, `28092012.pdf`, `28a/28b/28c092012.pdf`, `30092012.pdf` and `24b092012.pdf` (top 10 + Mr Asia); 2013 (47th, Ho Chi Minh City) Day One is `04092013.pdf`. `results.html` also has SEA Games top-3 results from 1979 on. The Archive often returns "Temporarily Offline"; retry after a pause. Cache: `~/workspace/musmem/.page_cache/abbf_wayback/`.

### ibbf.in (Indian Body Builders Federation) — fuller WBPF/ABBF score sheets

IBBF re-posts WBPF/ABBF result PDFs under `https://ibbf.in/old-website/assets/pdf/` (no directory listing; find names via the Wayback CDX: `url=ibbf.in/old-website/assets/pdf/*`). Some are **fuller** than wbpsf.org's: `13thWBPF-Result.pdf` (World 2022 full score sheet; wbpsf has only top 3 / top-5 images) and `15th-WBBC-2024-Result.pdf` (World 2024 full; wbpsf has top 3). Coverage only goes back to about 2022; the 2012 9th South Asian circular is there but not its results. Cache: `~/workspace/musmem/.page_cache/ibbf/`.
