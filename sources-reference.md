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

<!-- Add future sources here in the same format -->
