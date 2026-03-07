# Article Scraping — Session Notes

## Goal

Read all 423 article XML files in `~/workspace/node/musmem/data/mm_articles/*/`
to extract contest date, venue, and location from magazine articles, and write results
to `~/workspace/musmem/data/contest_locations.json`.

## Source Files

All files are XML (despite the `.txt` extension the user may reference — actual extension is `.xml`).

```
~/workspace/node/musmem/data/mm_articles/
  im/      IronMan                          (79 files)
  sh/      Strength & Health               (118 files)
  mb/      Muscle Builder                   (82 files)
  md/      Muscular Development             (76 files)
  ma/      Mr. America Magazine              (8 files)
  ma2/     Mr. America Magazine (vol 2)      (1 file)
  mp/      Muscle Power                     (26 files)
  mp2/     Muscle Power (vol 2)              (4 files)
  mti/     Muscle Training Illustrated       (2 files)
  yp/      Your Physique                    (27 files)
```

## XML Structure

Each file follows this pattern:

```xml
<article>
  <title>IronMan, Vol 7, No 1, Page 14</title>
  <date>est. Fall 1946</date>         <!-- publication date of the magazine, NOT the contest -->
  <body>
    <h1>Contest title or article headline</h1>
    <h4>Subheading or intro...</h4>
    <p>Article body text...</p>
    <a href="/event?name=Mr%20America%20-%20AAU&amp;year=1946">...</a>
  </body>
</article>
```

**Important:** The `<date>` field is the magazine publication date, not the contest date.
Contest date must be extracted from the article body text.

**MuscleMemory event links:** 37 of 423 files already contain `<a href="/event?name=...&year=...">` links.
When present, these give the exact MuscleMemory contest name and year — use them directly.

## Output File

`~/workspace/musmem/data/contest_locations.json`

Format:
```json
[
  {
    "contest": "Mr. America - AAU",
    "years": {
      "1946": { "date": "May 30-31, 1946", "venue": "Hollywood Legion Stadium", "location": "Hollywood, California, USA" }
    }
  }
]
```

Contest name format: as used in the MuscleMemory database (e.g. `"Mr. America - AAU"`).

## JSON Rules

- **Omit blank fields.** Only include `date`, `venue`, and `location` if a value was
  actually extracted. Do not write keys with empty or null values.
- **Never overwrite existing entries.** If a contest+year combination already exists
  in contest_locations.json, do not update it. However, if the newly extracted data
  differs from what's stored, print a warning, e.g.:
  `CONFLICT: "Mr. America - AAU" 1946 — stored: {...}, extracted: {...}`

## Scripts

`musmem-locations/python/prescreeen_articles.py`
- Scans all XML files in `~/workspace/node/musmem/data/mm_articles/*/`
- Identifies likely contest articles using keyword matching (contest, championship,
  Mr. America, Mr. Universe, Mr. World, Nationals, Olympia, etc.)
- Also flags files containing `/event?name=` links (reliable anchors)
- Outputs a manifest to `/tmp/article_manifest.tsv`:
  `filepath\thas_event_link\theadline\tpub_date`
- Run once at the start of a scraping campaign; reuse across sessions

`musmem-locations/python/merge_locations.py`
- Same script as used for scorecard scraping (shared)
- Merges extracted contest data into contest_locations.json
- Appends/merges — never overwrites the file
- Skips contest+year entries that already exist with data
- Logs CONFLICT to console if extracted data differs from stored data

## Workflow (per session)

### Session limit: process at most 50 candidate articles per session, then stop and ask the user to restart.

### Phase 0 — One-time pre-screen (first session only)

1. Write and run `prescreen_articles.py` to scan all 423 files
2. Save manifest to `/tmp/article_manifest.tsv`
3. Report: total files, how many are likely contest articles, how many have event links

### Phase 1 — Process candidates

Work through the manifest sequentially. For each candidate article:

1. Read the XML file
2. Determine: **Is this article a report of a specific bodybuilding contest?**
   - Yes if: it reports results, describes the event as it happened, names a contest and year
   - No if: it's a training article, product ad, interview, general history piece, or preview
3. If **No** — skip, note as "not a contest report"
4. If **Yes** — extract:
   - **Contest name** — match to MuscleMemory name (see Contest Name Matching below)
   - **Year** — the year the contest took place (may differ from publication date)
   - **Date** — specific date(s) of the contest (e.g., "May 30-31, 1946")
   - **Venue** — building or arena name (e.g., "Hollywood Legion Stadium")
   - **Location** — city, state/province, country (always include country)
5. Check `contest_locations.json` for an existing entry
6. If entry exists and has data — note any conflicts, do not overwrite
7. If entry is missing or fields are empty — record for writing

### Phase 2 — Write results

After processing a batch:

1. Edit `new_entries` in `merge_locations.py` with all found results
2. Run `python3 musmem-locations/python/merge_locations.py`
3. Report: found / skipped (not a contest report) / conflict / written counts

## Contest Name Matching

**Priority 1 — Event link in the XML:**
If the article contains `<a href="/event?name=CONTEST_NAME&year=YEAR">`, use that
contest name and year directly — it has already been mapped.

**Priority 2 — Known contest name table:**
Common article names → MuscleMemory names:

| Article mentions | MuscleMemory name |
|-----------------|-------------------|
| Mr. America | Mr. America - AAU (pre-1980) or check org |
| Mr. Universe (NABBA) | Mr. Universe - NABBA |
| Mr. Universe (IFBB) | Mr. Universe - IFBB |
| Mr. World | Mr. World - IFBB or check org |
| Mr. Olympia | Olympia - IFBB |
| Nationals | Nationals - NPC (post-1982) or Nationals - AAU (pre-1982) |
| Sr. Nationals / Senior Nationals | Same as Nationals |
| Jr. Nationals / Junior Nationals | Junior Nationals - NPC |

**Priority 3 — MuscleMemory API lookup:**
```
GET https://musclememory.net/api/org?name={ORG}
```
Use browser User-Agent (see SKILL.md). Search the returned list for the closest match.

**When uncertain:** Record the raw contest name from the article and flag for review.
Do not guess. If you cannot confidently match, skip and note "name unresolved".

## Extracting Date, Venue, Location from Prose

Contest articles from the 1940s–1980s describe events in narrative form. Look for:

- **Date:** "held on May 30th and 31st", "the June 14th contest", "Saturday, October 5"
  — combine with year from context to form a full date string (e.g., "May 30-31, 1946")
- **Venue:** "at the Hollywood Legion Stadium", "in the Victoria Palace Theatre",
  "held at Madison Square Garden" — take the proper name of the building
- **Location:** city and state/country mentioned in the article or inferable from the venue
  — always write as "City, State, USA" or "City, Country" (include country)

If the article gives the year but not month/day, record only what is certain (e.g., date: "1946").

## Progress

- Pre-screen: COMPLETE — 382 candidate articles from 423 total (manifest at `/tmp/article_manifest.tsv`)
- Files processed: 50 / 382 candidates (sessions 1-2)

### Session 1 (files 1-24) — im/im* early volumes
- Mr America - AAU: 1945 (confirmed existing), 1946 (date pre-existing; added venue+location), 1947, 1948, 1951, 1952, 1953, 1955
- Mr Universe - NABBA: 1952, 1954, 1955
- Skipped (not contest reports): winner profiles, training articles, editorials
- Notes: 3 unidentified pro shows (1949 — Shrine, Embassy, Civic Auditoriums, Los Angeles) not matched to any MuscleMemory contest; skipped

### Session 2 (files 25-50) — im/im* mid volumes
- Mr America - AAU: 1957, 1958, 1959, 1961, 1962, 1964
- Mr Universe - NABBA: 1956, 1957, 1958, 1959, 1960, 1961, 1962, 1964 (no 1963 article found)
- Universe - Pro - NABBA: 1957, 1958, 1959, 1960, 1961, 1962, 1964 (new contest; no 1963 article found)
- Junior Mr America - AAU: 1963 (new contest)
- Mr America - IFBB: 1964 (new contest)
- Universe - IFBB: 1964 (new contest)
- Skipped (not contest reports): 7 files (editorials, winner profiles, letters to editor)
- Notes: "Bert Goodrich Mr. U.S.A. 1956" (Shrine Auditorium, Los Angeles) — Mr USA - AAU starts 1964 in DB; left unmatched

### Conflicts detected
- **Mr America - AAU 1954**: stored date "June 26-27, 1954" vs. article evidence "June 25-26, 1954"
  (venue/location match: Greek Theatre, Los Angeles — date discrepancy needs resolution)

## To Resume

Next session: **files 51–100** from the manifest (`filepaths[50:100]` in 0-indexed terms).
Use the same pattern as `/tmp/list_batch.py` — write a script to `/tmp/`, run it to list the next batch,
then read and process each file sequentially.
