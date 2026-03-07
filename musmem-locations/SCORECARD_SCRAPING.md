# Scorecard Scraping — Session Notes

## Goal

Scrape all 79 pages of https://npcnewsonline.com/category/contest-scorecards/page/{n}/
to extract contest date, venue, and location from scorecard images, and write results
to ~/workspace/musmem/data/contest_locations.json.

## Output File

`~/workspace/musmem/data/contest_locations.json`

Format:
```json
[
  {
    "contest": "Atlantic Coast Pro - IFBB",
    "years": {
      "2025": { "date": "March 15, 2025", "venue": "Some Arena", "location": "City, State, USA" }
    }
  }
]
```

Contest name format: `"Contest Name - ORG"` — strip the leading org prefix from the scorecard
(e.g. "2025 IFBB PRO LEAGUE ATLANTIC COAST PRO" → `"Atlantic Coast Pro - IFBB"`).

## JSON Rules

- **Omit blank fields.** Only include `date`, `venue`, and `location` if a value was
  actually extracted. Do not write keys with empty or null values.
- **Never overwrite existing entries.** If a contest+year combination already exists
  in contest_locations.json, do not update it. However, if the newly extracted data
  differs from what's stored, print a warning to the console, e.g.:
  `CONFLICT: "IFBB Atlantic Coast Pro" 2025 — stored: {...}, extracted: {...}`

## Scripts

`musmem-locations/python/fetch_scorecards.py`
- Takes a page number as argument
- Fetches the listing page, finds all "Official Score Cards" posts
- Downloads **img1 only** per post to /tmp/scorecards/ (tries img2/img3 only if img1 is corrupt)
- Validates PNG magic bytes before saving — skips HTML error responses
- Outputs a tab-separated manifest to stdout: `title\tpost_url\timg1_path`
- About 14 contests per listing page

`musmem-locations/python/fetch_img2.py`
- Takes a post URL as argument
- Downloads img2 for that specific post to /tmp/scorecards/<slug>-img2.png
- Use on demand when img1 does not contain date/location
- Prints the local path on success, nothing on failure

`musmem-locations/python/group_scorecards.py`
- Groups downloaded PNGs in /tmp/scorecards/ by contest slug
- Prints each contest with its images in order (img1, img2, img3, then base)
- Run after fetch to get a clear processing order before reading images

`musmem-locations/python/merge_locations.py`
- Merges extracted contest data into contest_locations.json
- **Appends/merges — never overwrites the file**
- Skips contest+year entries that already exist with data
- Logs CONFLICT to console if extracted data differs from stored data
- Edit the `new_entries` list at the top before each run

## Workflow (per run)

### Session limit: process at most 8 pages per session, then stop and ask the user to restart.

Loop pages n = 2 to 79:

1. Run `python3 musmem-locations/python/fetch_scorecards.py <n>` — downloads img1 only to /tmp/scorecards/
2. For each contest on the page (use the manifest: `title\tpost_url\timg1_path`):
   a. Open img1 — attempt to extract date and location from scorecard header
   b. If found — record result, move to next contest
   c. If not found — run `python3 musmem-locations/python/fetch_img2.py <post_url>` to get img2, then open it
   d. If still not found — record as not found, move on (do not try img3)
3. Edit `new_entries` in `merge_locations.py` with all found results, then run it
   — it merges into contest_locations.json without overwriting existing data
4. Report page summary (found / not found counts)
5. Delete all files in /tmp/scorecards/ before fetching the next page
6. Automatically continue to page n+1 (no pause between pages)
7. After 8 pages — stop and tell the user to start a new session to continue
8. After page 79 — final report

## Progress

- Page 1: COMPLETE — 12 found, 2 not found
  - Found: All South Pro Championships, Chattanooga Night of Champions, East Coast Pro,
    Hurricane Pro, Idaho Cup Natural Pro, MuscleContest Iron Games Pro, Kansas City Pro,
    MuscleContest Philippines Pro, Oklahoma Grand Prix Pro, Romania Muscle Fest Pro,
    Texas State Pro, Ultimate Grand Prix Masters Pro
  - Not found: Atlantic Coast Pro, Tsunami Nutrition France Natural Pro
    (both lost their header page — img1 was a corrupt HTML response)
- Page 2: COMPLETE
- Page 3: COMPLETE
- Page 4: COMPLETE — 4 found, 1 not found
  - Found: USA Championships - NPC (July 25-26), Gomeisa Ultimate Battle Pro - IFBB (July 20, Medellin Colombia),
    Teen Collegiate & Masters National Championships - NPC (July 16-17), Zhanna Rotar Classic Pro - IFBB (July 12, Las Vegas NV)
  - Not found: Republic of Texas Pro - IFBB (img1 corrupt, no header in img2/img3)
- Page 5: COMPLETE — 9 found, 1 not found
  - Found: Universe - NPC (July 3-4), Dubai Pro - IFBB (June 21, Dubai UAE),
    South Florida Classic Pro - IFBB (June 21, Boca Raton FL), Junior Nationals - NPC (June 20),
    Empro Classic Pro - IFBB (June 15, Alicante Spain), China DMS Pro - IFBB (June 15, Ningjin China),
    Nevada State Pro - IFBB (June 14, Las Vegas NV), Toronto Pro Supershow - IFBB (June 8, Toronto Canada),
    DC Natural Pro - IFBB (June 8, Manassas VA)
  - Not found: World Classic Pro - IFBB (no header in any image)
- Page 6: COMPLETE — 13 found, 0 not found
  - Found: Spanish Masters Pro - IFBB (June 8, Madrid), Adela Garcia Pro - IFBB (June 7, Austin TX),
    Oklahoma Pro - IFBB (June 7, Tulsa OK), DC Pro - IFBB (June 7, Manassas VA),
    Mile High Pro - IFBB (June 7, Denver CO), Southern California Championships Pro - IFBB (June 7, San Diego CA),
    Omaha Pro - IFBB (June 7, Omaha NE), Thailand Pro - IFBB (June 7, Pattaya Thailand),
    Legion Sports Fest Pro - IFBB (May 31, Reno NV), Miami Pro - IFBB (May 24, Miami FL),
    California State Pro - IFBB (May 24, Anaheim CA), New York Pro Championships - IFBB (May 17, Teaneck NJ),
    Pittsburgh Natural Pro Qualifier - NPC Worldwide (May 10)
- Page 7: COMPLETE — 12 found, 0 not found
  - Found: Pittsburgh Power & Fitness Pro - IFBB (May 10, Pittsburgh PA), Los Angeles Grand Prix Pro - IFBB (Apr 26, Anaheim CA),
    GRL PWR Pro - IFBB (Apr 26, Orlando FL), Huanji China Pro - IFBB (Apr 20, Shanghai),
    St. Louis Pro - IFBB (Apr 19, St. Louis MO), 1 Bro Pro Show - IFBB (Apr 19, Maidenhead UK),
    FIBO Pro Championships - IFBB (Apr 12, Cologne Germany), Charlotte Cup Pro - IFBB (Apr 12, Charlotte NC),
    Detroit Pro - IFBB (Mar 29, Dearborn MI), Sampson Showdown Pro - IFBB (Mar 29, Las Vegas NV),
    San Diego Pro - IFBB (Mar 8, San Diego CA), Arnold Classic - IFBB (Feb 28-Mar 1, Columbus OH)
- Page 8: COMPLETE — 9 found, 0 not found (2024 contests)
  - Found: Bharat Pro Show - IFBB (Dec 20, Mumbai), Japan Pro - IFBB (Nov 24, Tokyo),
    Kansas City Pro - IFBB (Nov 23, Kansas City MO), EVLS Prague Pro - IFBB (Nov 16, Prague),
    Ben Weider Natural Pro - IFBB (Nov 15, Alexandria VA), Atlantic Coast Pro - IFBB (Nov 16, Ft. Lauderdale FL),
    Texas State Pro - IFBB (Nov 9, San Marcos TX), Olympia - IFBB (Oct 11-12, Las Vegas NV),
    Legion Pro - IFBB (Sep 28-29, Reno NV) [date corrected on page 9]
- Page 9: COMPLETE — 12 found, 0 not found (2024 contests)
  - Found: Legion Pro - IFBB date corrected to Sep 28-29, Daytona Pro - IFBB (Sep 28, Daytona Beach FL),
    Titans Grand Prix Pro - IFBB (Sep 21, Anaheim CA), Turkiye Pro - IFBB (Sep 19, Izmir Turkey),
    Europa Pro - IFBB (Sep 14, London UK), Battle of the Bodies Pro - IFBB (Sep 14, Ft. Lauderdale FL),
    San Antonio Pro - IFBB (Sep 14, San Antonio TX), Pro Muscle Pro - IFBB (Sep 8, Milan Italy),
    Florida Pro - IFBB (Sep 7, Sarasota FL), Heart of Texas Pro - IFBB (Sep 7, Dallas TX),
    RGV Classic Pro - IFBB (Aug 31, McAllen TX), Masters World Championships - IFBB (Sep 1, Pittsburgh PA)
- Page 10: COMPLETE — 6 found, 1 not found (2024 contests)
  - Found: Arizona Pro - IFBB (Aug 24, Phoenix AZ), Rising Phoenix Pro - IFBB (Aug 24, Phoenix AZ),
    World Klash Pro - IFBB (Aug 24, Charleston SC), Tupelo Pro - IFBB (Aug 16, Tupelo MS),
    Florida State Pro - IFBB (Aug 10, Orlando FL), Pacific USA Pro - IFBB (Aug 10, San Diego CA)
  - Not found: Nashville Fit Pro - IFBB (no header in any image)
- Page 27: COMPLETE — 7 found, 3 not found (2022 contests)
  - Found: Nevada State Pro (Oct 1, Las Vegas NV), Ben Weider Natural Pro (Sep 30, Alexandria VA),
    Battle of the Bodies Pro (Sep 17, Ft. Lauderdale FL), Yamamoto Cup Pro (Sep 11, Padua Italy),
    Sasquatch Pro (Sep 10, Federal Way WA), Heart of Texas Pro (Sep 10, Dallas TX),
    Savannah Pro (Sep 10, Savannah GA)
  - Not found: Minneapolis Pro (not in DB), Arnold Classic UK (not in DB), San Antonio Pro (already stored)

- Page 28: COMPLETE — 3 found, 3 not found (2022 contests)
  - Found: Nashville FitShow Pro (Aug 20, Nashville TN), USA Championships (Jul 29, date only),
    Masters World Championships (Jul 23-24, Pittsburgh PA)
  - Not found: Tokyo Pro (not in DB), Sin City Pro (not in DB), Carolina Excalibur Pro (not in DB)

- Page 29: COMPLETE — 6 found, 1 not found (2022 contests)
  - Found: Vancouver Pro (Jul 17, Vancouver Canada), Zhanna Rotar Classic Pro (Jul 16, Anaheim CA),
    Lenda Murray Atlanta Pro (Jul 16, Atlanta GA), Mr. Big Evolution Portugal Pro (Jul 10, Estoril Portugal),
    Republic of Texas Pro (Jul 9, Austin TX), Orlando Pro (Jul 2, Orlando FL)
  - Not found: Governors Cup Pro (not in DB)

- Page 30: PARTIAL — 3 found from PNG posts; 7 JPG posts unprocessed (script bug, needs re-run)
  - Found: MuscleContest Rio de Janeiro Pro (Jun 24, Rio de Janeiro Brazil),
    Dallas Pro (Jun 18, Dallas TX), Patriots Challenge Pro (Jun 18, Las Vegas NV)
  - Unprocessed JPGs: Sheru Classic Italian, Puerto Rico Pro, Omaha Pro, Southern California Pro,
    DC Pro, Northern California Pro, Mile High Pro (7 posts)
  - Truly no images: none (all had JPGs)

- Page 31: PARTIAL — 1 found from PNG posts; 9 JPG posts unprocessed (script bug, needs re-run)
  - Found: Indy Pro (May 14, Indianapolis IN)
  - Unprocessed JPGs: Toronto Pro, Miami Muscle Beach, Mid-USA, California State, Palmetto Classic,
    Optimum Classic, Pittsburgh Championships, Florida Grand Prix, GRL PWR Pro (9 posts)

- Page 32: PARTIAL — 5 found from PNG posts; 4 JPG posts unprocessed (script bug, needs re-run)
  - Found: Wasatch Warrior Pro (Apr 15, Salt Lake City UT), Charlotte Cup Pro (Apr 15-16, Charlotte NC),
    St. Louis Pro (Apr 16, St. Louis MO), MuscleContest Campinas Pro (Mar 19, Campinas Brazil),
    Boston Pro (Mar 12, Boston MA)
  - Unprocessed JPGs: Warrior Classic Pro, Fitworld Pro, MuscleContest Rio Pro, Caribbean Grand Prix Bermuda (4 posts)
  - Not in DB: Fitmuscle Pro, Golden State Pro

- Page 33: PARTIAL — 3 found from PNG posts; 8 JPG posts unprocessed (script bug, needs re-run)
  - Found: Arnold Classic (Mar 5 2022, Columbus OH), Vancouver Pro (Dec 22 2021, Vancouver Canada),
    New Zealand Pro (Dec 18 2021, Auckland New Zealand)
  - Unprocessed JPGs: 8 posts (2021 contests)

- Page 34: PARTIAL — 1 found from PNG posts; 13 JPG posts unprocessed (script bug, needs re-run)
  - Found: Sacramento Pro (Nov 6 2021, Sacramento CA)
  - Unprocessed JPGs: Atlantic Coast Pro, Ben Weider Natural Pro, Japan Pro, Romania Muscle Fest,
    Texas States, Iron Games, EVLS Prague, KO Egypt, MuscleContest Nacional, Legion Sports Fest,
    Poland Pro Supershow, Hurricane Pro, San Antonio Classic Pro (13 posts)

- Page 11: COMPLETE — 10 found, 0 not found (2024 contests)
  - Found: Tampa Pro - IFBB (Aug 1, Tampa FL), Dubai Pro - IFBB (Jul 28, Dubai UAE),
    USA Championships - NPC (Jul 26-27), Colombia Pro - IFBB (Jul 18, Medellin Colombia),
    Teen Collegiate & Masters National Championships - NPC (Jul 17-18),
    Patriots Challenge Pro - IFBB (Jul 20, Las Vegas NV), Vancouver Pro - IFBB (Jul 13, Abbotsford BC Canada),
    Lenda Murray Atlanta Pro - IFBB (Jul 13, Atlanta GA), Zhanna Rotar Los Angeles Pro - IFBB (Jul 13, Anaheim CA),
    Republic of Texas Pro - IFBB (Jul 13, Austin TX)

## Crash History

- Session crashed with: `API Error: 400 {"type":"error","error":{"type":"invalid_request_error","message":"Could not process image"}}`
- Happened while reading one of the page 1 scorecard images
- Cause: server returned an HTML error page for some image URLs; file was saved with a `.png`
  extension but contained `<!DOCTYPE html>` — Claude's image reader rejected it
- Fix: `fetch_scorecards.py` now validates the PNG magic bytes (`\x89PNG`) before saving;
  non-PNG responses are logged and skipped

- Page 12: COMPLETE — 8 found, 1 not found (2024 contests)
  - Found: Huanji China Pro - IFBB (Jul 7, Sanya China), Indy Pro - IFBB (Jun 29, Carmel IN),
    Kazakhstan Pro - IFBB (Jun 29, Almaty Kazakhstan), Mr. Big Evolution Portugal Pro - IFBB (Jul 7, Estoril Portugal),
    MuscleContest Ireland Pro - IFBB (Jun 30, Limerick Ireland), Orlando Pro - IFBB (Jul 6, Orlando FL),
    Tanji Johnson Pro - IFBB (Jun 22, Tacoma WA), World Classic Pro - IFBB (Jun 22, Chattanooga TN)
  - Not found: St Pete Pro - IFBB (no header in any image)
  - Skipped: Lenda Murray Atlanta Pro - IFBB 2024 (already saved from page 11)

- Page 13: COMPLETE — 13 found, 0 not found (2024 contests)
  - Found: South Florida Pro - IFBB (Jun 22, Boca Raton FL), Empro Pro - IFBB (Jun 16, Alicante Spain),
    Dallas Pro - IFBB (Jun 15, Dallas TX), Southern California Championships Pro - IFBB (Jun 15, San Diego CA),
    Toronto Pro Supershow - IFBB (Jun 9, Toronto Canada), Oklahoma Pro - IFBB (Jun 8, Tulsa OK),
    Omaha Pro - IFBB (Jun 8, Omaha NE), DC Pro - IFBB (Jun 8, Alexandria VA),
    Adela Garcia Pro - IFBB (Jun 8, Bastrop TX), Mile High Pro - IFBB (Jun 8, Denver CO),
    Mid-USA Pro - IFBB (Jun 2, Albuquerque NM), Miami Muscle Beach Pro - IFBB (Jun 1, Miami FL),
    Nevada State Pro - IFBB (Jun 1, Las Vegas NV)

- Page 14: COMPLETE — 12 found, 0 not found (2024 contests; Junior USA Day One/Two = one entry)
  - Found: German Classic Pro - IFBB (May 25, St. Leon-Rot Germany), Optimum Classic Pro - IFBB (May 25, Shreveport LA),
    California State Pro - IFBB (May 25, Anaheim CA), Klash Series Southern USA Pro - IFBB (May 25, Orlando FL),
    Mexico Pro - IFBB (May 18, Guadalajara Mexico), New York Pro Championships - IFBB (May 18, Teaneck NJ),
    Junior USA Championships - NPC (May 17, date only), Pittsburgh Pro - IFBB (May 10, Pittsburgh PA),
    Hungary Kokeny Pro - IFBB (May 11, Budapest Hungary), AGP Bikini Pro - IFBB (May 4, Paju City South Korea),
    AGP Pro - IFBB (Apr 28, Gyeonggi South Korea), Dragon Physique DMS Pro - IFBB (Apr 28, Changsha China)

- Page 15: COMPLETE — 13 found, 0 not found (2024 contests; Charlotte Cup Sat/Sun = one entry)
  - Found: Los Angeles Grand Prix Pro - IFBB (Apr 27, Anaheim CA), St. Louis Pro - IFBB (Apr 27, St. Louis MO),
    Klash Series GRL PWR Pro - IFBB (Apr 27, Orlando FL), Emerald Cup Pro - IFBB (Apr 26, Bellevue WA),
    Vancouver Island Showdown Pro - IFBB (Apr 20, Victoria BC), Wasatch Warrior Pro - IFBB (Apr 20, Salt Lake City UT),
    Detroit Pro - IFBB (Apr 13, Dearborn MI), Tri-City Pro - IFBB (Apr 13, Columbus GA),
    Fitworld Pro - IFBB (Apr 13, Los Angeles CA), Charlotte Cup Pro - IFBB (Apr 6, Charlotte NC),
    Arnold Brazil Pro - IFBB (Apr 5, Sao Paulo Brazil), 1 Bro Pro Show - IFBB (Apr 6, London UK),
    Triple O Dynasty Pro - IFBB (Apr 6, Mesa AZ)

- Page 16: COMPLETE — 8 found, 0 not found (mix of 2024 and 2023 contests)
  - Found: Taiwan Pro - IFBB (Apr 4 2024, Kaohsiung Taiwan), Houston Tournament of Champions Pro - IFBB (Mar 30 2024, The Woodlands TX),
    Klash Series Championships Pro - IFBB (Mar 30 2024, Orlando FL), San Diego Pro - IFBB (Mar 30 2024, San Diego CA),
    Sampson Showdown Pro - IFBB (Mar 23 2024, Las Vegas NV), MuscleContest Campinas Pro - IFBB (Mar 16 2024, Campinas Brazil),
    National Championships - NPC (Dec 9 2023, date only), Pharlabs Battle of Bogota Pro - IFBB (Nov 18-19 2023, Bogota Colombia)

- Page 17: COMPLETE — 9 found, 0 not found (2023 contests)
  - Found: Shawn Ray Hawaiian Classic Pro - IFBB (Nov 18, Honolulu HI), Sheru Classic India Pro - IFBB (Nov 17-19, Mumbai India),
    Romania Muscle Fest Pro - IFBB (Nov 11, Bucharest Romania), Korea Pro - IFBB (Nov 11, South Korea),
    Caribbean Grand Prix Masters Pro - IFBB (Nov 11, Nassau Bahamas), Texas State Pro - IFBB (Nov 11, San Marcos TX),
    Hurricane Pro - IFBB (Oct 21, St. Petersburg FL), Chattanooga Night of Champions Pro - IFBB (Oct 21, Chattanooga TN),
    British Championships Pro - IFBB (Oct 14, Manchester UK)

- Page 18: COMPLETE — 14 found, 0 not found (2023 contests)
  - Found: Daytona Pro - IFBB (Sep 29, Daytona Beach FL), Heart of Texas Pro - IFBB (Sep 9, Dallas TX),
    Battle of the Bodies Pro - IFBB (Sep 16, Ft. Lauderdale FL), Legion Masters Pro - IFBB (Oct 7, Reno NV),
    Legion Pro - IFBB (Oct 8, Reno NV), Masters World Championships - IFBB (Sep 3, Pittsburgh PA),
    Mr. & Ms. Lions Classic Grand Battle Pro - IFBB (Oct 14, Guadalajara Mexico),
    San Antonio Pro - IFBB (Sep 23, San Antonio TX), Sasquatch Pro - IFBB (Sep 9, Federal Way WA),
    Sheru Classic France Pro - IFBB (Sep 28-29, France), Southern Muscle Showdown Pro - IFBB (Oct 7, Dalton GA),
    Ultimate Grand Prix Masters Pro - IFBB (Oct 14, Boca Raton FL),
    Van City Showdown Pro - IFBB (Sep 30, Burnaby BC Canada), MuscleContest Vietnam Pro - IFBB (Oct 13, Vietnam)

## To Resume

Pages 1-29 are fully complete. Pages 30-34 need re-run with JPG-fixed script, then continue from page 35.
Re-run pages 30, 31, 32, 33, 34 first, then resume page 35. This session may process up to 8 pages total.
