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
4. Update the Progress section of this file with the page results
5. Report page summary (found / not found counts)
6. Delete all files in /tmp/scorecards/ before fetching the next page
7. Automatically continue to page n+1 (no pause between pages)
8. After 8 pages — stop and tell the user to start a new session to continue
9. After page 79 — final report

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

- Page 30: COMPLETE (re-run) — 7 found, 2 already stored
  - Found: Sheru Classic Italian Pro (Jun 26, Rome Italy), MuscleContest Brazil Pro (Jun 24, Rio de Janeiro Brazil),
    Puerto Rico Pro (Jun 17-19, San Juan Puerto Rico), Omaha Pro (Jun 11, Omaha NE),
    Southern California Championships Pro (Jun 11, San Diego CA), DC Pro (Jun 11, Alexandria VA),
    Northern California Pro (Jun 11, Sacramento CA)
  - Already stored: Dallas Pro, Patriots Challenge Pro
  - Note: Mile High Pro was not on this page (appeared on page 31)

- Page 31: COMPLETE (re-run) — 10 found, 1 already stored
  - Found: Mile High Pro (Jun 11, Denver CO), Clash at the Titanz Pro (Jun 11, Marietta GA),
    Toronto Pro Supershow (Jun 5, Toronto Canada), Miami Muscle Beach Pro (Jun 4, Miami Beach FL),
    Mid-USA Pro (May 28, Albuquerque NM), California State Pro (May 28, San Diego CA),
    Palmetto Classic Pro (May 28, Columbia SC), Optimum Classic Pro (May 21, Shreveport LA),
    Pittsburgh Championships NPC (May 6, Pittsburgh PA), Florida Grand Prix Pro (May 7, Boca Raton FL)
  - Already stored: Indy Pro 2022
  - Note: GRL PWR Pro was not on this page (appeared on page 32)

- Page 32: COMPLETE (re-run) — 7 found, 4 already stored, 1 conflict
  - Found: GRL PWR Pro (Apr 30, Orlando FL), Warrior Classic Pro (Apr 30, Richmond VA),
    Fitmuscle Pro (Apr 23, Guadalajara Mexico), Golden State Pro (Apr 9, Sacramento CA),
    MuscleContest Rio Pro (Mar 26, Rio de Janeiro Brazil), Caribbean Grand Prix Bermuda Pro (Mar 26, Hamilton Bermuda),
    Fitworld Pro (Mar 19, Anaheim CA)
  - Already stored: Wasatch Warrior Pro, Charlotte Cup Pro, St. Louis Pro
  - Conflict: World Klash Pro 2022 has two events (Apr 2 and Nov 5, both Orlando) — stored Nov 5

- Page 33: COMPLETE (re-run) — 5 found, 7 already stored
  - Found: National Championships NPC (Dec 17, 2021), Atlanta All States Pro (Dec 10-11, Atlanta GA),
    Toronto Pro Supershow (Dec 5, Toronto Canada), Battle of Texas Pro (Dec 4, Irving TX),
    Pro Bigman Weekend (Nov 28, Alicante Spain)
  - Already stored: MuscleContest Campinas Pro, Boston Pro, Arnold Classic 2022, Vancouver Pro 2021, New Zealand Pro 2021
  - Note: Atlanta All States Bikini img1 contained Toronto Pro scorecard (wrong image uploaded by site)

- Page 34: COMPLETE (re-run) — 12 found, 1 already stored
  - Found: MuscleContest Brazil Pro (Nov 26-28, Brazil), Shawn Ray Hawaiian Classic Pro (Nov 20, Honolulu HI),
    Atlantic Coast Pro (Nov 20, Ft. Lauderdale FL), Ben Weider Natural Pro (Nov 19, Alexandria VA),
    Romania Muscle Fest Pro (Nov 13-14, Bucharest Romania), Texas State Pro (Nov 13, Austin TX),
    Iron Games Pro (Nov 13, Anaheim CA), EVLS Prague Pro (Nov 6, Prague Czech Republic),
    KO Egypt Pro (Oct 31, Cairo Egypt), MuscleContest Nacional Pro (Oct 30, Campinas Brazil),
    Legion Sports Fest Pro (Oct 24, Reno NV), Poland Pro Supershow (Oct 24, Warsaw Poland)
  - Already stored: Sacramento Pro 2021
  - Note: Japan Pro, Hurricane Pro, San Antonio Classic Pro were not on this page (appeared on pages 35-36)

- Page 35: COMPLETE — 9 found
  - Found: Hurricane Pro (Oct 23, St. Petersburg FL), San Antonio Classic Pro (Oct 23, San Antonio TX),
    FitParade Pro (Oct 16-17, Budapest Hungary), Yamamoto Cup Pro (Oct 17, Rome Italy),
    Monterrey Pro (Oct 16, Monterrey Mexico), Kentucky Muscle Pro (Oct 16, Louisville KY),
    Titans Grand Prix Pro (Oct 16, Los Angeles CA), Amateur Olympia Orlando NPC Worldwide (Oct 5, Orlando FL),
    Arnold Classic United Kingdom (Oct 1-2, Birmingham UK)

- Page 36: COMPLETE — 10 found
  - Found: Minneapolis Pro (Oct 2, Minneapolis MN), Nashville Night of Champions Pro (Oct 2, Chattanooga TN),
    Arnold Classic (Sep 25, Columbus OH), San Antonio Pro (Sep 25, San Antonio TX),
    Champions Classic Pro (Sep 19, Warsaw Poland), Heart of Texas Pro (Sep 18, Dallas TX),
    Monsterzym Pro (Sep 12, Seoul South Korea), Rising Phoenix Pro (Sep 11, Scottsdale AZ),
    Powerhouse Classic Pro (Sep 11, Ypsilanti MI), Lenda Murray Savannah Pro (Sep 4, Savannah GA)

- Page 37: COMPLETE — 8 found
  - Found: Battle of Champions Pro (Aug 29, Warsaw Poland), Tokyo Supershow Pro (Aug 29, Tokyo Japan),
    Nashville FitShow Pro (Aug 21, Nashville TN), Europa Pro (Aug 15, Alicante Spain),
    Tahoe Pro (Aug 15, Stateline NV), Pacific USA Pro (Aug 5, San Diego CA),
    Puerto Vallarta Pro (Jul 31-Aug 1, Puerto Vallarta Mexico), Battle of the Bodies Pro (Jul 31, Ft. Lauderdale FL)

- Page 38: COMPLETE — 3 found, 4 not in DB (2021 contests)
  - Found: Republic of Texas Pro (Jul 17, Austin TX), Patriots Challenge Pro (Jul 10, Las Vegas NV),
    Omaha Pro (Jul 10, Omaha NE)
  - Not in DB: Pittsburgh Pro Masters, Battle in the Desert Pro, Xtreme Fitness and Bodybuilding Pro,
    Lenda Murray Norfolk Pro

- Page 39: COMPLETE — 6 found, 3 not in DB/already stored (2021 contests)
  - Found: Universe NPC (Jul 1-3, date only), Puerto Rico Pro (Jun 26-27, Nassau Bahamas),
    DC Pro (Jun 19, Herndon VA), Northern California Pro (Jun 12, Sacramento CA),
    Clash at the Titanz Pro (Jun 12, Austell GA), Miami Muscle Beach Pro (Jun 5, Miami Beach FL)
  - Not in DB/skip: World Caribbean Championships NPC Worldwide, Europa Dallas Pro (Alicante already stored),
    Europa Orlando Pro (not in 2021 DB)

- Page 40: COMPLETE — 9 found, 2 not in DB (2021 contests)
  - Found: Mile High Pro (Jun 5, Denver CO), California State Pro (May 29, San Diego CA),
    Optimum Classic Pro (May 22, Shreveport LA), New York Pro Championships (May 15, Tampa FL),
    Junior USA Championships NPC (May 13, date only), St. Louis Pro (May 8, St. Louis MO),
    GRL PWR Pro (May 8, Orlando FL), Indy Pro (May 8, Indianapolis IN),
    Pittsburgh Pro (Apr 30-May 1, Pittsburgh PA)
  - Not in DB: Milwaukee Pro, City Limits Pro

- Page 41: COMPLETE — 5 found, 3 not in DB/no data (2021/2020 contests)
  - Found: Wasatch Warrior Pro (Apr 17, Salt Lake City UT), World Klash Pro (Apr 3, Orlando FL),
    USA Championships NPC (Dec 13-14, Phoenix AZ), Battle of Texas Pro (Dec 4-5, Dallas TX),
    Atlantic Coast Pro (Nov 28, Fort Lauderdale FL)
  - Not in DB/no data: Australia Pro 2021, Amateur Olympia Orlando 2020 (no header in any image),
    Masters USA Championships NPC, National Championships NPC 2020 (img illegible)

- Page 42: COMPLETE — 3 found, 4 not in DB/no data (2020 contests)
  - Found: MuscleContest Nacional Pro (Nov 8, Sao Paulo Brazil),
    San Antonio Pro (Nov 7, San Antonio TX), Sacramento Pro (Oct 17, Sacramento CA)
  - Not in DB: British Grand Prix Pro, Upper Midwest Pro, Chicago Pro 2020;
    Teen Collegiate & Masters NPC 2020 (no header in any day image)

- Page 43: COMPLETE — 5 found, 2 not in DB/no data (2020 contests)
  - Found: Minneapolis Pro (Oct 3, Minneapolis MN), Tahoe Pro (Sep 27, Squaw Valley CA),
    California State Pro (Sep 12, Las Vegas NV), New York Pro Championships (Sep 5, Tampa FL),
    Pittsburgh Pro (Sep 2, Pittsburgh PA)
  - Not in DB: Border States Pro; Junior USA 2020 (no date in any image)

- Page 44: COMPLETE — 6 found, 1 not in DB (2020 contests)
  - Found: Pacific USA Pro (Aug 27, San Diego CA), Optimum Classic Pro (Aug 29, Shreveport LA),
    Tampa Pro (Jul 31-Aug 1, Tampa FL), Omaha Pro (Jul 18, Omaha NE),
    Wasatch Warrior Pro (Jul 11, Salt Lake City UT), Northern California Pro (Jul 11, Sacramento CA)
  - Not in DB: Southeast Texas Pro

- Page 45: COMPLETE — 2 found, 2 not in DB (2019 contests)
  - Found: Battle of Texas Pro (Dec 14, Dallas TX), Legion Sports Fest Pro (Nov 10, Long Beach CA)
  - Not in DB: San Marino Pro, Dennis James Classic Pro

- Page 46: COMPLETE (recovery) — 1 found, rest already stored
  - Written: Border States Pro - IFBB (Oct 5, San Diego CA)
  - Not in DB: Iowa Pro
  - All other page 46 contests were already stored from a prior session

- Page 47: COMPLETE — 5 found, 1 not in DB (2019 contests)
  - Found: Ben Weider Natural Pro - IFBB, Hurricane Pro - IFBB, Rising Phoenix Pro - IFBB,
    Arizona Pro - IFBB, Golden State Pro - IFBB
  - Not in DB: Portland Classic Pro

- Page 48: COMPLETE — 6 found, 1 not found (2019 contests)
  - Found: MuscleContest Brazil Pro - IFBB (Aug 3, Sao Paulo Brazil), Tampa Pro - IFBB (Aug 3, Tampa FL),
    USA Championships - NPC (Jul 26-27, date only), Prestige Crystal Cup Pro - IFBB (Jul 27, Boca Raton FL),
    Vancouver Pro - IFBB (Jul 13-14, Vancouver Canada), Lenda Murray Pro - IFBB (Jul 13, Norfolk VA)
  - Not found: Teen Collegiate Masters NPC 2019 (no date/location in any image)

- Page 49: COMPLETE — 6 found, 3 not in DB (2019 contests)
  - Found: San Jose Pro - IFBB, Europa Dallas - IFBB, Omaha Pro - IFBB,
    Miami Muscle Beach Pro - IFBB, Toronto Pro Supershow - IFBB, Mile High Pro - IFBB
  - Not in DB: Battle in the Desert Pro, Greater Gulf Pro, Junior Nationals NPC

- Page 50: COMPLETE — 6 found, 7 skipped (2019 contests)
  - Found: Puerto Rico Pro - IFBB, Optimum Classic Pro - IFBB, New York Pro Championships - IFBB,
    Pittsburgh Pro - IFBB, Pro Bigman Weekend - IFBB, MuscleContest Ireland Pro - IFBB
  - Skipped: not in DB / NPC scorecards with no location / duplicate day entries

- Page 51: COMPLETE — 2 found, 4 not in DB (2019 contests)
  - Found: World Klash Pro - IFBB, Fitworld Pro - IFBB
  - Not in DB: Upper Midwest Classic Pro, Sheru Classic Colombia, Legends Classic Pro, NPC Amateur Arnold

- Page 52: COMPLETE — 5 found, 3 skipped (2018 contests)
  - Found: Iron Games Pro - IFBB, Sacramento Pro - IFBB, Baltimore Pro - IFBB,
    Kentucky Muscle Pro - IFBB, Dominican Republic Pro - IFBB
  - Skipped: NPC Nationals (no scorecard location), Muscle Mulisha (not in DB), Dennis James Classic (not in DB)

- Page 53: COMPLETE — 4 found, 2 skipped (2018 contests)
  - Found: EVLS Prague Pro - IFBB (Sep 29, Prague Czech Republic), Arkansas Pro - IFBB (Sep 22, Little Rock AR),
    Hurricane Pro - IFBB (Sep 22, Tampa FL), Olympia - IFBB (Sep 15, Las Vegas NV)
  - Skipped: EVLS Prague Pro Qualifier (not a tracked contest), Amateur Olympia (no header in img1 or img2)

- Page 54: COMPLETE — 7 found, 2 not in DB (2018 contests)
  - Found: Pittsburgh Pro - IFBB (Aug 29, Pittsburgh PA), Golden State Pro - IFBB (Aug 25, Sacramento CA),
    Pacific USA Pro - IFBB (Aug 18, San Diego CA), MuscleContest Brazil Pro - IFBB (Aug 12, Sao Paulo Brazil),
    San Antonio Pro - IFBB (Aug 11, San Antonio TX), Tampa Pro - IFBB (Aug 3-4, Tampa FL),
    USA Championships - NPC (Jul 27-28, date only)
  - Not in DB: Portland Classic Pro, Battle in the Desert Pro

- Page 55: COMPLETE — 5 found, 4 skipped (2018 contests)
  - Found: Pro Bigman Weekend - IFBB (Jul 21, Benidorm Spain), Lenda Murray Pro - IFBB (Jul 14, Norfolk VA),
    Vancouver Pro - IFBB (Jul 8, Vancouver Canada), Patriots Challenge Pro - IFBB (Jul 7, Las Vegas NV),
    Universe - NPC (Jun 29-30, date only)
  - Skipped: LA Pro 2018 (no matching DB contest), Portugal Pro Qualifier (qualifier),
    Teen Collegiate Masters (no header), Big Man Weekend (used Pro Bigman Weekend name)

- Page 56: COMPLETE — 7 found, 3 not in DB (2018 contests)
  - Found: British Championships Pro - IFBB (Jun 23-24, London England), Junior Nationals - NPC (Jun 15-16, date only),
    Omaha Pro - IFBB (Jun 9, Omaha NE), San Marino Pro - IFBB (Jun 3, Rimini Italy),
    Toronto Pro Supershow - IFBB (Jun 2, Toronto Canada), Northern California Pro - IFBB (Jun 2, Sacramento CA),
    Mile High Pro - IFBB (Jun 2, Denver CO)
  - Not in DB: Mexico Supershow Pro, Greater Gulf Pro, Muscle Mayhem Pro

- Page 57: COMPLETE — 6 found/fixed, 4 not in DB (2018 contests)
  - Found: Miami Muscle Beach Pro - IFBB (Jun 2, Miami FL), California State Pro - IFBB (May 26, Culver City CA),
    New York Pro Championships - IFBB (May 19, White Plains NY), Optimum Classic Pro - IFBB (May 19, Shreveport LA),
    Junior USA Championships - NPC (May 18-19, date only)
  - Fixed: Pittsburgh Pro - IFBB 2018 corrected from Aug 29 (Masters) to May 5 (regular show)
  - Not in DB: Alex Classic Pro, Dennis James Pro, Champions of Power and Grace Pro, Nebraska Pro

- Page 58: COMPLETE — 5 found, 3 not in DB (2018 contests)
  - Found: Europa Pro - IFBB (Apr 14, Orlando FL), Indy Pro - IFBB (Mar 31, Indianapolis IN),
    Fitworld Pro - IFBB (Mar 24, Culver City CA), World Klash Pro - IFBB (Mar 24, Aiken SC),
    Upper Midwest Pro - IFBB (Mar 24, Fargo ND)
  - Not in DB: Salt City Showdown Pro, Governors Cup Pro, City Limits Pro

- Page 59: COMPLETE — 5 found, 7 NPC/amateur/qualifier skipped (2018 contests)
  - Found: Atlantic Coast Pro (Mar 24, Ft. Lauderdale FL), Royal London Pro (Mar 10-11, London England),
    Hawaii Pro (Mar 10, Honolulu HI), Arnold Classic (Mar 3, Columbus OH),
    Sheru Classic Colombia Pro (Feb 18, Medellin Colombia)

- Page 60: COMPLETE — 8 found, 4 NPC skipped (2017-2018 contests)
  - Found: Legends Pro (Feb 10 2018, Las Vegas NV), Tournament of Champions Pro (Dec 2, San Diego CA),
    Ferrigno Legacy Pro (Nov 18, Rancho Mirage CA), Iron Games Pro (Nov 11, Culver City CA),
    Ultimate Warriors Pro (Nov 4, San Diego CA), Sacramento Pro (Oct 28, Sacramento CA),
    Kentucky Muscle Pro (Oct 28, Louisville KY), Mel Chancey Pro (Oct 28, Fort Myers FL)

- Page 61: COMPLETE — 8 found, 1 NPC skipped (2017 contests)
  - Found: Titans Grand Prix Pro (Oct 21, Culver City CA), South Carolina Grand Prix Pro (Oct 21, Charleston SC),
    Central USA Pro (Oct 14, Sioux Falls SD), San Antonio Classic Pro (Oct 7, San Antonio TX),
    EVLS Prague Pro (Sep 30, Prague Czech Republic), Arkansas Pro (Sep 23, Little Rock AR),
    Arnold Classic Europe (Sep 23, Barcelona Spain), Olympia (Sep 16, Las Vegas NV)

- Page 62: COMPLETE — 6 found, 5 NPC/skip (2017 contests)
  - Found: Rising Phoenix Pro (Sep 9, Phoenix AZ), Pittsburgh Pro Masters Championships (Aug 30, Pittsburgh PA),
    Pacific USA Pro (Aug 19, San Diego CA), Golden State Pro (Aug 12, Sacramento CA),
    San Antonio Pro (Aug 12, San Antonio TX), Tampa Pro (Aug 5, Tampa FL)
  - Skipped: NPC Tahoe Show, NPC Muscle Contest Challenge, NPC Victor Martinez's Legends, NPC USA Championships, NPC Teen Collegiate Masters; North American Championships (no header visible)

- Page 63: COMPLETE — 8 found, 2 NPC + 3 posts 404 (2017 contests)
  - Found: Baltimore Pro (Jul 15, Baltimore MD), Lenda Murray Pro (Jul 8, Norfolk VA),
    Patriots Challenge Pro (Jul 1, Las Vegas NV), San Jose Pro (Jul 1, San Jose CA),
    Chicago Pro (Jun 30), Arctic Pro (Jun 24, Anchorage AK),
    Greater Gulf Pro (Jun 24, New Orleans LA), Dexter Jackson Memphis Classic Pro (Jun 24, Memphis TN)

- Page 64: COMPLETE — 8 found, 3 NPC skipped (2017 contests; duplicates collapsed)
  - Found: Miami Muscle Beach Pro (Jun 10, Miami Beach FL), Puerto Rico Pro (Jun 4, date only),
    Northern California Pro (Jun 3, Sacramento CA), California State Pro (May 27, Culver City CA),
    Toronto Pro Supershow (May 28, Toronto Canada), Ostrava Pro (May 27, Ostrava Czech Republic),
    Europa Pro (May 21, Orlando FL), New York Pro Championships (May 20, New York NY)

- Page 65: COMPLETE — 7 found, 4 NPC skipped + 1 wrong img (2017 contests)
  - Found: Optimum Classic Pro (May 20, Shreveport LA), Florida Grand Prix Masters Pro (May 7, West Palm Beach FL),
    California Night of Champions Pro (May 6, San Diego CA), Pittsburgh Pro (May 6, Pittsburgh PA),
    Europa Charlotte Pro (Apr 23, Charlotte NC), St. Louis Pro (Apr 15, St. Louis MO),
    Los Angeles Grand Prix Pro (Apr 8, Culver City CA)
  - Salt City Showdown img1 had wrong scorecard — skipped

- Page 66: COMPLETE — 7 found, 6 NPC skipped (2017 contests)
  - Found: Governors Cup Pro (Apr 1, Sacramento CA), City Limits Pro (Apr 1, Waxahachie TX),
    Karina Nascimento Pro (Mar 25, Fort Lauderdale FL), Fitworld Pro (Mar 11, Culver City CA),
    Orlando Pro (Mar 11, Orlando FL), Arnold Classic (Mar 3, Columbus OH),
    Legends Classic Pro (Feb 11, Las Vegas NV)

- Page 67: COMPLETE — 9 found (2016 contests)
  - Found: San Marino Pro - IFBB (Dec 4, San Marino), Tournament of Champions Pro - IFBB (Dec 3, San Diego CA),
    Iron Games Pro - IFBB (Nov 12, Culver City CA), Florida Victory Pro - IFBB (Nov 5, Boca Raton FL),
    Ultimate Warriors Pro - IFBB (Nov 5, San Diego CA), Sacramento Pro - IFBB (Nov 5, Sacramento CA),
    Moscow Pro - IFBB (Oct 30, Moscow Russia), Ferrigno Legacy Pro - IFBB (Oct 29, Rancho Mirage CA),
    Nationals - NPC (Nov 18-19, date only)
  - Skipped NPC: Excalibur, Eastern USA, New England

- Page 68: COMPLETE — 2 found, 4 not in DB (2016 contests)
  - Found: Titans Grand Prix Pro - IFBB (Oct 15, Culver City CA), Border States Pro - IFBB (Oct 1, San Diego CA)
  - Not in DB: Europa Phoenix Pro, Liquid Sun Rayz Pro, Nordic Pro, Fort Lauderdale Cup Pro

- Page 69: COMPLETE — 8 found, 3 not in DB/no data (2016 contests)
  - Found: Kuwait Pro Championships - IFBB (Sep 29, Kuwait), Asia Grand Prix - IFBB (Sep 25, Seoul Korea),
    Hurricane Pro - IFBB (Sep 24, Tampa FL), Arnold Classic Europe - IFBB (Sep 24, Barcelona Spain),
    Arkansas Pro - IFBB (Sep 24, Little Rock AR), Olympia - IFBB (Sep 17, Las Vegas NV),
    Pacific USA Pro - IFBB (Sep 3, San Diego CA), Pittsburgh Pro Masters Championships - IFBB (Aug 31, Pittsburgh PA)
  - Not in DB/no data: Arizona Pro/Rising Phoenix 2016 (not in DB), North American Championships (no header in scorecard)

- Page 70: COMPLETE — 5 found, 3 not in DB (2016 contests)
  - Found: Arnold Classic Asia - IFBB (Aug 20, Hong Kong), Golden State Pro - IFBB (Aug 13, Sacramento CA),
    San Antonio Pro - IFBB (Aug 13, San Antonio TX), Tampa Pro - IFBB (Aug 6, Tampa FL),
    Prestige Crystal Cup Pro - IFBB (Jul 30, Boca Raton FL)
  - Not in DB: Naples Pro, Coastal USA Pro, Flex Lewis Classic Pro

- Page 71: COMPLETE — 7 found (2016 contests)
  - Found: Europa Charlotte Pro - IFBB (Jul 9, Charlotte NC), San Jose Pro - IFBB (Jul 2, San Jose CA),
    Patriots Challenge Pro - IFBB (Jul 2, Las Vegas NV), Chicago Pro - IFBB (Jul 2, Chicago IL),
    Greater Gulf Pro - IFBB (Jun 25, New Orleans LA), Dexter Jackson Memphis Classic Pro - IFBB (Jun 25, Memphis TN),
    Europa Dallas - IFBB (Jun 18, Dallas TX)

- Page 72: COMPLETE — 6 found, 1 skipped (2016 contests)
  - Found: Arctic Pro - IFBB (Jun 11, Anchorage AK), Toronto Pro Supershow - IFBB (Jun 5, Toronto Canada),
    Northern California Pro - IFBB (Jun 4, Sacramento CA), Mile High Pro - IFBB (Jun 4, Denver CO),
    California Pro - IFBB (May 28, Culver City CA), Arnold Classic South Africa - IFBB (May 28, Johannesburg SA)
  - Skipped: Muscle Mayhem Pro (404 error on post)

- Page 73: COMPLETE — 4 found, 1 not in DB (2016 contests)
  - Found: New York Pro Championships - IFBB (May 21, Teaneck NJ), Florida Grand Prix Pro - IFBB (May 14, West Palm Beach FL),
    California Night of Champions Pro - IFBB (May 7, San Diego CA), Pittsburgh Pro - IFBB (May 7, Pittsburgh PA)
  - Not in DB: Body Power Pro

- Page 74: COMPLETE — 3 found, 3 not in DB (2016 contests)
  - Found: Governors Cup Pro - IFBB (Mar 26, Sacramento CA), St. Louis Pro - IFBB (Mar 26, St. Louis MO),
    Orlando Pro - IFBB (Mar 12, Orlando FL)
  - Not in DB: LA Grand Prix Pro 2016, MuscleContest Pro 2016, Phil Heath Classic Pro

- Page 75: COMPLETE — 3 found, 5 NPC amateur skipped, 1 not in DB (2015-2016 contests)
  - Found: Arnold Classic - IFBB (Mar 4 2016, Columbus OH), Karina Nascimento Pro - IFBB (Feb 20 2016, Palm Beach Gardens FL),
    Ferrigno Legacy Pro - IFBB (Nov 20 2015, Palm Springs CA)
  - Not in DB: Kevin Levrone Classic - IFBB 2016 (Gdansk, Poland)
  - NPC skipped: Gold Coast Muscle Classic, Texas Cup, Excalibur, Tournament of Champions, NPC Ferrigno Legacy, NPC Kentucky Muscle

- Page 76: COMPLETE — 3 found, 5 NPC amateur skipped, 1 not in DB (2015 contests)
  - Found: Iron Games Pro - IFBB (Nov 14, Culver City CA), Kentucky Muscle Pro - IFBB (Nov 14, Louisville KY),
    Sacramento Pro - IFBB (Nov 7, Sacramento CA)
  - Not in DB: Iowa Pro - IFBB 2015 (Council Bluffs, Iowa)
  - NPC skipped: Irongames, Cut Above, Ultimate Warriors, Eastern USA, New York State Grand Prix

- Page 77: COMPLETE — 3 found, 5 NPC amateur skipped, 1 not in DB (2015 contests)
  - Found: Titans Grand Prix Pro - IFBB (Oct 17, Culver City CA), Europa Pro - IFBB (Oct 10, Phoenix AZ),
    Arkansas Pro - IFBB (Oct 10, Little Rock AR)
  - Not in DB: Fort Lauderdale Cup Pro - IFBB 2015 (Fort Lauderdale, FL)
  - NPC skipped: Golds Classic, Formulation 1 Classic, NPC Titans Grand Prix, NPC Fort Lauderdale Cup, Brooklyn Grand Prix

- Page 78: COMPLETE — 4 found, 2 NPC skipped, 4 not in DB (2015 contests)
  - Found: Border States Pro - IFBB (Oct 3, San Diego CA), EVLS Prague Pro - IFBB (Oct 3, Prague Czech Republic),
    Olympia - IFBB (Sep 19, Las Vegas NV), Tahoe Pro - IFBB (Aug 22, Lake Tahoe NV)
  - Not in DB: Southwest Muscle Classic Pro, Naples Pro, Europa Atlantic City Pro, Wings of Strength Texas Pro
  - NPC skipped: NPC Fit World Championships, NPC Southwest Muscle Classic

- Page 79: COMPLETE (FINAL PAGE) — 2 found, 2 NPC skipped, 1 not in DB (2015 contests)
  - Found: Golden State Pro - IFBB (Aug 15, Sacramento CA), Dallas Pro - IFBB (Aug 15, Dallas TX)
  - Not in DB: Coastal USA Pro - IFBB 2015 (Atlanta, GA)
  - NPC skipped: NPC Golden State Championships, NPC Muscle Beach Championships
  - Note: Dallas Pro scorecard header said "2014 IFBB Dallas Pro" but post title and date (Aug 15, 2015) confirm 2015

## To Resume

ALL 79 PAGES COMPLETE. Scorecard scraping is finished.
