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

- Divisions in `<h2>` tags (e.g., `Men's Physique Masters`, `Classic Physique II`, `Men Body III`)
- Athletes in `<ol>` ordered lists — `<li>` position = placing
- Country codes in `<span class="badge">GER</span>` (3-letter IOC-style codes)
- "Out of Top 10:" entries in `<p><em>Out of Top 10:</em> Name (COUNTRY), ...</p>` — these are unplaced (placing 98)
- "DNF:" entries in `<p><em>DNF:</em> Name (COUNTRY), ...</p>` — skip these
- Overall winners in a `<ul>` under an "Overall Winners" `<h2>`, formatted as `<li><strong>Division Overall</strong>: Name <span class="badge">COUNTRY</span></li>`
- Sections wrapped in `<section id="...">` tags
- Names are in First Last order — do NOT set `l 1`
- Country information IS available (unlike npcnewsonline.com)

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

Overall winners appear in a `<ul>` under the "Overall Winners" `<h2>`:

| Overall category | Code | Gender |
|------------------|------|--------|
| Bodybuilding Overall / Men Body Overall | `OP` | male |
| Classic Physique Overall | `CL` | male |
| Figure Overall | `FI` | female |
| Bikini Shape Overall | — | excluded |
| Best Präsentation | — | skip (non-standard) |

Written as placing `0`: `c OP` + `0 Name (COUNTRY)`.

### Out of Top N / DNF

- `Out of Top 10:` (or similar) entries → placing 98, with country in parentheses
- Inline `– DNF` within "Out of" entries → skip that athlete
- Standalone `DNF:` entries → skip entirely

### Known data issues

- **Universe 2023** page is a duplicate of Universe 2022 data (identical athletes, different publication date). Skip until NAC corrects it.

### Male/female split files

Same rules as npcnewsonline.com — separate `-male.txt` and `-female.txt` files.

**Male divisions:** Men Body I/II/III, Men's Physique (I/II), Classic Physique I/II, Juniors, Masters I/II/III, Classic Physique Masters, Men's Physique Masters
**Female divisions:** Ms./Miss Figure, Ms./Miss Physique, Miss Figure Masters, Ms. Figure Over 40
**Excluded from both:** Bikini Shape (all variants), Bikini Wellness

---

<!-- Add future sources here in the same format -->
