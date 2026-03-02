---
name: musmem-locations
description: Use when searching for the date, venue, or location of historic or modern bodybuilding contests to populate contest_locations.json.
---

# MuscleMemory Contest Location Finder

Searches the web for contest dates, venues, and locations, then writes results to `~/workspace/musmem/contest_locations.json`.

## Input Modes

- `"Nationals - NPC, 1995"` → research that specific year (always, even if data exists)
- `"Nationals - NPC, 1982-2025"` → research that year range
- `"Nationals - NPC"` → query API for all years in DB, research only years with no existing data

## MuscleMemory API

```
GET https://musclememory.net/api/contests                          # all contests across all orgs
GET https://musclememory.net/api/contests/{year}                   # all contests across all orgs for a year
GET https://musclememory.net/api/org?name={ORG}                    # all contest names for one org (use to find exact contest name)
GET https://musclememory.net/api/contest/years?name={contest}      # all years DB has results for a specific contest
```

Use browser User-Agent for all musclememory.net API calls (server blocks bots):
```
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
```

## JSON Schema

File: `~/workspace/musmem/contest_locations.json`

```json
[
  {
    "contest": "Contest Name - ORG",
    "years": {
      "1940": {
        "date": "May 25, 1940",
        "venue": "Madison Square Garden",
        "location": "New York, New York, USA"
      },
      "1947": { "date": "", "venue": "", "location": "" }
    }
  }
]
```

- `date` — free text, can be a range (e.g., `"June 1-2, 1946"`), empty string if unknown
- `venue` — building/arena name, empty string if unknown
- `location` — `"City, State, Country"` format, empty string if unknown
- Write valid JSON after every update

## Workflow

### Step 1 — Resolve contest name

If the user gave the exact contest name (e.g., `"Nationals - NPC"`), use it directly.

If the name is ambiguous or the org is given instead:
- `GET /api/org?name={ORG}` → pick the matching contest name from the list

### Step 2 — Determine target years

**Specific year given** (e.g., `"Nationals - NPC, 1995"`):
- That single year is the only target. Proceed regardless of existing JSON data.

**Year range given** (e.g., `"1982-2025"` or `"1982 to present"`):
- `GET /api/contest/years?name={contest}` → get years in DB
- Filter to the requested range
- Skip any year that already has ANY field filled in the JSON
- Remaining years are the targets

**No year given:**
- `GET /api/contest/years?name={contest}` → get all years in DB
- Skip any year that already has ANY field filled in the JSON
- Remaining years (all fields empty, or year not yet in JSON) are the targets

### Step 3 — Research each target year

Process sequentially — one year at a time. Use Search Tiers below.

### Step 4 — Write results

**Specific year was given AND data already exists in JSON:**
- If found data differs from existing: present both versions, ask for confirmation before updating
- If found data matches existing: report "no change"
- If fields were empty: write directly

**All other cases:**
- Write found data directly to JSON after each year (don't batch at the end)
- If the year doesn't exist in JSON yet, create the entry

### Step 5 — Report

After all targets: list what was found, what was skipped (had existing data), and what remains empty (not found after exhausting all search tiers).

## Search Tiers

**Tier 1 — Org website (modern contests):**
- For IFBB/NPC/NPC Worldwide/CPA: check `npcnewsonline.com` contest listing or result page — often includes date and venue
- If not found: search for promoter's event page: `"[Contest Name] [year] [org]" schedule OR results`

**Tier 2 — General web search:**
- `"[Contest Name] [year]" bodybuilding date location`
- `"[Contest Name] [year]" bodybuilding "[org]"`
- For historical contests (pre-1980): also try Wikipedia and history sites like sandowplus.co.uk

**Tier 3 — Declare unknown:**
- After 2–3 failed searches across both tiers, leave fields empty and note "not found" in report

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Searching year-by-year via API | Use `/api/contest/years` to get all years at once |
| Overwriting existing data without confirmation | Only overwrite when user gave a specific year AND confirmed |
| Invalid JSON | Validate structure before writing — array at top level, no trailing commas |
| Stopping after one failed search | Try all tiers before declaring unknown |
| Processing entries in parallel | One year at a time — no parallel agents |
| Writing location as "City, State" | Always include country: `"City, State, USA"` |
