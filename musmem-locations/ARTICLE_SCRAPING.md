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
- Files processed: 382 / 382 candidates (sessions 1-9) — **COMPLETE**

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

### Session 3 (files 51-100) — im/im* late volumes + ma/, ma2/, mb/* early volumes
- Mr America - AAU: 1956, 1961, 1962, 1965, 1966, 1967, 1968 (historical 1939-1944 already in DB)
- Junior Mr America - AAU: 1955, 1965, 1966
- Mr Universe - NABBA: 1956 (date update), 1965, 1966, 1967, 1968
- Universe - Pro - NABBA: 1956, 1965, 1966, 1967, 1968
- Mr America - IFBB: 1962, 1965, 1966, 1967
- Universe - IFBB: 1962, 1965, 1966
- Olympia - IFBB: 1965, 1966, 1967, 1969 (new contest in DB)
- Mr World - IFBB: 1966, 1967 (new contest in DB)
- Skipped: editorials, letters, winner profiles, Mr USA (not in DB), historical exposés
- Notes:
  - 1955 NABBA Mr. Universe: London Palladium (not Victoria Palace Theatre; VPT starts 1961+)
  - 1957 NABBA: London Coliseum (not VPT)
  - 1962 Mr. America AAU venue: Highland Park High School Auditorium, Highland Park, MI
    (DB had "Detroit, MI" — conflict flagged, not overwritten)
  - "Bert Goodrich Mr. U.S.A. 1957" (Shrine Auditorium, LA) — not in DB; skipped

### Session 4 (files 101-150) — mb/* volumes (1960s-1975)
- Mr America - IFBB: 1960, 1963, 1971, 1972, 1973, 1974
- Universe - IFBB: 1960, 1963, 1971, 1972, 1973, 1974
- Mr Universe - NABBA: 1969, 1970
- Universe - Pro - NABBA: 1969, 1970
- Mr World - IFBB: 1970, 1971, 1972, 1973, 1974
- Olympia - IFBB: 1970, 1971, 1973, 1974
- Mr America - AAU: 1975
- Skipped: winner profiles, training articles, editorials, Mr USA (not in DB), AABA contests
- Notes:
  - 1960 IFBB shows: Monument-National, Montreal (event link confirmed)
  - 1963 IFBB shows: Brooklyn Academy of Music (event links confirmed)
  - 1970 Olympia: Town Hall, New York City (no specific date in article)
  - 1971 IFBB Mr. America: Aquarius Theatre, Hollywood (venue history: Earl Carroll's → Moulin Rouge → Hullabaloo → Aquarius)
  - 1971 IFBB Universe + Olympia: Palais de la Mutualité, Paris (pre-judging Sept 24, finals Sept 25)
  - 1971 Mr. World: White Plains County Center, White Plains, NY (Sept 12)
  - 1972 Mr. America + Mr. World: Brooklyn Academy of Music (Sept 16)
  - 1972 Universe: Al-Nasr Cinema, Baghdad, Iraq (Nov 21)
  - 1973 Mr. America + Mr. World + Olympia: Brooklyn Academy of Music (Sept 8)
  - 1973 Universe: Victoria Hall, Geneva, Switzerland (Oct 20)
  - 1974 Mr. America + Mr. World + Olympia: Felt Forum (MSG), New York (Oct 12)
  - 1974 Universe: Teatro Nuovo, Verona, Italy (Oct 3-6)
  - 1975 Mr. America AAU: Culver City Veterans Memorial Auditorium (June 19)
  - mb760143.xml (file 149): AABA show July 19, 1975 (Embassy Auditorium, LA) — distinct from AAU Mr. America; skipped

### Conflicts detected
- **Mr America - AAU 1954**: stored date "June 26-27, 1954" vs. article evidence "June 25-26, 1954"
  (venue/location match: Greek Theatre, Los Angeles — date discrepancy needs resolution)
- **Mr America - AAU 1962**: stored location "Detroit, Michigan, USA" vs. article evidence
  "Highland Park, Michigan, USA" — venue "Highland Park High School Auditorium" and date "June 2-3, 1962"
  were NOT written; needs manual resolution

### Session 5 (files 151-200) — mb/* 1975-1976 + md/* 1964-1972
- Mr Universe - NABBA: 1963 (Victoria Palace Theatre — previously no 1963 article found)
- Universe - Pro - NABBA: 1963 (Victoria Palace Theatre)
- Mr America - AAU: 1969 (DePaul Alumni Hall, Chicago, June 13-15), 1970 (Veterans Memorial Auditorium, Culver City, June 14), 1971 (York, PA, June 12), 1972 (Masonic Temple, Detroit), 1976 (Philadelphia)
- Junior Mr America - AAU: 1970 (Brentwood, NY, May 17), 1971 (Baytown, TX, May 16)
- Mr World - IFBB: 1975 (Felt Forum/MSG, New York, September 27)
- Universe - IFBB: 1975 (University of South Africa, Pretoria, November 7-8)
- Olympia - IFBB: 1975 (University of South Africa, Pretoria, November 7-8), 1976 (Veterans Memorial Auditorium, Columbus, September 18)
- Skipped: historical retrospectives, editorials, winner profiles, Mr. United States (not in DB), FIHC/AAU Mr. World York (not confirmed in DB), "Setting the Record Straight" controversy articles
- Notes:
  - 1969 NABBA Universe: Victoria Palace Theatre, September 20, 1969 — NOT written (1969 already has location "London" from session 4; merge would skip)
  - 1970 AAU Mr. World: Veterans Memorial Hall, Columbus — not matched to confirmed DB contest name; skipped
  - 1971 AAU Mr. World: William Penn High School, York, PA, November 6 — not matched to DB; skipped
  - 1976 IFBB Mr. America: mentioned as October 2, 1976 (from Robby Robinson article) — not yet written, no article found in this batch

### Session 6 (files 201-250) — md/* 1973-1979 + mp/* 1947-1957
- Mr America - AAU: 1949 (Masonic Auditorium, Cleveland, May 21-22), 1973 (Williamsburg, VA), 1974 (York, PA), 1977 (Santa Monica Auditorium, July 16), 1978 (Cincinnati Music Hall, September 2)
- Mr Universe - NABBA + Pro: 1971 (London), 1972 (London), 1977 (London)
- Skipped: 1957 Mr America (Peabody Auditorium, Daytona Beach — existing data already in DB); AAU/FIHC Mr. World 1972+1973 (Zembo Mosque, Harrisburg, PA — not confirmed in DB); WABBA Paris 1977 (not in DB); Mr. USA AAU (not confirmed in DB); training articles, profiles, editorials
- Notes:
  - 1949 AAU Mr. America: entry existed in DB (UPDATED, not ADDED — likely had existing location data that was augmented)
  - 1957 AAU Mr. America: confirmed at Peabody Auditorium, Daytona Beach, FL — but SKIP (existing DB entry has data)
  - 1970 NABBA Universe: confirmed at Ohio State University, Columbus (same as Veterans Memorial Hall story) — existing entry skipped
  - NABBA venues 1971-1972: London, venue not named in articles (likely Victoria Palace Theatre based on pattern)
  - File 229 (1979 Mr. America): "still to be typed in" placeholder — no location data

### Session 7 (files 251-300) — mp2/* + mti/* + sh/* 1936-1950

- Mr America - AAU: 1950 (Academy of Music, Philadelphia, May 12-13)
- Mr Universe - NABBA: 1948 (Scala Theatre, London, August 13), 1950 (Scala Theatre, London, June 24)
- Pro Mr America: 1946 (San Francisco, September 27)
- World-Universe - FICH: 1950 (Paris, October 15)
- Best Developed Athlete in America - IFBB: 1950 (New York City, September 8)
- Junior Mr America - AAU: 1949 (Chattanooga, Tennessee, May 1)
- Mr France: 1948 (Cannes, August 15)
- Mr Europe: 1948 (Cannes, August 16)
- Mr World: 1948 (Cannes, August 16)
- Skipped: editorials, winner profiles, training articles, 1939-1949 Mr. America (already in DB), editorial/challenge letters (mti/mp2 files), 1947 Mr. Universe Philadelphia (no DB match — pre-NABBA show), Most Muscular Physique in America contest 1946 (not in DB), Mr USA contests
- Notes:
  - 1946 AAU Mr. America: S&H article says June 1-2 vs. DB "May 30-31" — date conflict noted; skip (already in DB)
  - 1947 AAU Mr. America: confirmed Lane Tech Auditorium, Chicago, June 28-29 (already in DB)
  - 1948 NABBA Mr. Universe: date confirmed August 13, 1948 (sh481110 confirms this; Scala Theatre, London)
  - 1950 Mr. America: UPDATED (year existed but had no data; now has Academy of Music, Philadelphia, May 12-13)
  - Junior Mr America 1942: Bristol, Connecticut (from sh430918 — not in DB based on sessions 1-6)
  - Junior Mr America 1944: Pittsburgh, Pennsylvania (from sh440716 — not in DB; no venue named)

### Session 8 (files 301-350) — sh/ Strength & Health 1951-1966

- Mr World: 1952 ("the Met", Philadelphia, October 25)
- World-Universe - FICH: 1947 (Philadelphia), 1954 (Roubaix, France, October 16), 1955 (Munich, Germany, October 12-17), 1965 (Tehran, Iran)
- Universe - Pro - NABBA: 1955 (Scala Theatre, London, June 10-11)
- Mr America - AAU: 1960 (Cleveland, Ohio), 1963 (Zembo Mosque, Harrisburg, PA, June 28-29)
- Skipped: most S&H articles — editorials, winner profiles, judging articles, training articles, years already in DB
- Notes:
  - 1951 Mr America: already in DB (Greek Theatre, Griffith Park, LA, June 15-16) — confirmed
  - 1952 AAU Mr Universe: "still to be typed in" — skip
  - 1953 Mr America: already in DB (Murat Theater, Indianapolis) — confirmed
  - 1954 Mr America: date conflict persists (article: June 25-26; DB: June 26-27) — NOT overwritten
  - 1955 NABBA Amateur: DB has "London Palladium" but article sh551030 says "Scala Theatre" — CONFLICT, not overwritten
  - 1961 Mr America: confirmed June 24, Santa Monica — already in DB (Santa Monica Civic Aud.)
  - 1963 Mr America: Zembo Mosque, Harrisburg — NEW (40 contestants, greatest since 1940)
  - 1964 Mr America: already in DB (Chicago, June 13-14) — confirmed
  - 1966 Mr America: venue = York High School Auditorium — location already in DB, not written
  - World-Universe FICH 1947: first FICH physique contest, Philadelphia, Steve Stanko won
  - World-Universe FICH 1955: event link in article confirmed `World-Universe - FICH` name

### Session 9 (files 351-382) — sh/ Strength & Health 1966-1969 + yp/ Your Physique 1942-1952

- Mr America - AAU: 1967 (UPDATED — added venue "Veterans' Memorial Auditorium"; Columbus confirmed), 1968 (UPDATED — added date "June 8, 1968" and venue "William Penn High School Auditorium")
- Mr Universe - NABBA: 1951 (NEW — Scala Theatre, London, September 1, 1951; Reg Park won)
- Skipped: profiles, editorials, winner stories, training articles, years already fully in DB
- Notes:
  - sh/sh670920.xml (1967 Mr America): "Veterans' Memorial Auditorium in Columbus" — added venue (DB had location only)
  - sh/sh680918.xml (1968 Mr America): "William Penn High School Auditorium, Sunday evening, June 8th" — added date+venue; did NOT add location (city unnamed in article, DB has "Columbus, Ohio, USA", William Penn High School is in York, PA — potential conflict avoided)
  - sh/sh681036.xml (1968 Mr America score sheet): no new location data; skip
  - yp/yp160316.xml (1951 Mr Universe): full contest report — Scala Theatre, London, September 1, 1951 — NEW
  - yp/yp16057.xml (1952, Weider personal account of 1951 Universe): confirms London/Reg Park, no new date/venue
  - yp/yp140129.xml (1950 NABBA Universe editorial): no specific date/venue; skip
  - yp/yp140620.xml (1950 FICH World-Universe, Paris): event link confirmed; DB already has complete data
  - 1946, 1947, 1969 Mr America: all fully in DB, confirmed by yp articles; skipped

## Persistent Conflicts (manual resolution required)

- **Mr America - AAU 1954**: stored date "June 26-27, 1954" vs. article evidence "June 25-26, 1954"
- **Mr America - AAU 1962**: stored location "Detroit, Michigan, USA" vs. article evidence "Highland Park, Michigan, USA" (Highland Park High School Auditorium, June 2-3, 1962) — venue and date NOT written
- **Mr Universe - NABBA 1955**: stored venue "London Palladium" vs. article (sh551030) "Scala Theatre" — date June 10-11, 1955 NOT written

## Completion

All 382 candidate articles processed (sessions 1-9). Article scraping campaign complete.
