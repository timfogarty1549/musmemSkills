# 2026 IFBB Contests — npcnewsonline.com vs. MuscleMemory DB

## Purpose

Tracks the 2026 IFBB contest listing on npcnewsonline.com against the local
MuscleMemory database, so a future session can:

1. **Check for new contests** — re-fetch the listing page, diff against the
   "Slug" column below, and add any new rows (with a best-guess "Probable DB
   Match" and "Status").
2. **Fetch pages for contests not yet retrieved** — when requested, fetch the
   individual contest result pages for rows with a blank Status and store
   them in this skill's page cache at `~/workspace/musmem/.page_cache/`
   (see Phase 1 of the `musmem-contests` skill for caching mechanics). If a
   fetched page turns out to contain only excluded divisions, update its
   Status to 🚫 (with the reason, e.g. "Wellness only") so it isn't
   re-fetched in future sessions.

## Source URLs

- **Listing page:** https://contests.npcnewsonline.com/contests/2026/ifbb
- **Individual contest page pattern:** `https://contests.npcnewsonline.com/contests/2026/{slug}`
- **DB contests for 2026:** `http://localhost:3000/api/contests/2026`
- **All historical IFBB contests in DB:** `http://localhost:3000/api/org?name=IFBB&from=2010`
- **IFBB contests already collected for 2026:** `http://localhost:3000/api/org?name=IFBB&year=2026` — use this to confirm
  that every contest already inserted for 2026 has a corresponding row in the
  table below (with "In DB?" = `Yes`). If this endpoint returns a contest name
  that doesn't match any row's "Probable DB Match", flag it as a discrepancy
  (see Notes).

User-Agent for npcnewsonline.com fetches: `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36`

## How "Probable DB Match" was determined

- Exact match against `/api/org?name=IFBB&year=2026` → Status = ✅
- Otherwise, exact or near match against the full historical list from
  `/api/org?name=IFBB&from=2010` → name shown, Status = blank (To Fetch; means
  the contest exists in the DB under this name for other years, but the 2026
  result has not been added yet)
- No match found → "Probable DB Match" = `(new — no match)`, Status = blank
  (To Fetch), unless the page has been checked and contains only excluded
  divisions, in which case Status = 🚫

## Contest Table

Status values:
- **✅ (Fetched)** — 2026 result already in the DB (confirmed via `/api/org?name=IFBB&year=2026`)
- **(blank) (To Fetch)** — not yet retrieved; candidate for caching/extraction
- **phase 1** — page cached in `~/workspace/musmem/.page_cache/` (as `2026_{slug}.html`) and confirmed to contain at least one covered division; ready for Phase 2 (Extract)
- **phase 2** — flat file(s) written to `~/workspace/musmem/1-incoming/` (as `2026_{contest}-ifbb-{gender}.txt`); extraction complete, ready for Phase 3 (Normalize)
- **🚫 (Excluded)** — page checked, contains only excluded divisions (Bikini, Wellness, Fitness, Novice, etc. — see `musmem-contests` SKILL.md exclusion list); do not fetch (or re-fetch). Reason noted in parentheses.

| Listing Name | Slug | Probable DB Match | Status |
|---|---|---|---|
| AGP Korea Natural Pro Show | `ifbb_agp_korea_natural_pro_show` | Asian Grand Prix Korea Natural Pro - IFBB | phase 2 |
| AGP Korea Pro Show | `ifbb_agp_korea_pro_show` | Asian Grand Prix Korea Pro - IFBB | phase 2 |
| Arnold Classic | `ifbb_arnold_classic` | Arnold Classic - IFBB | ✅ |
| Arnold Classic UK | `ifbb_arnold_classic_uk` | Arnold Classic UK - IFBB | ✅ |
| Battle of the Bodies Pro | `ifbb_battle_of_the_bodies_pro` | Battle of the Bodies Pro Florida - IFBB | ✅ |
| Benelux Netherlands Pro | `ifbb_benelux_netherlands_pro` | Benelux Pro - IFBB | ✅ |
| California Night of Champions Pro | `ifbb_california_night_of_champions_pro` | California Night of Champions - IFBB | 🚫 (Fit Model only) |
| California State Pro | `ifbb_california_state_pro` | California State Pro - IFBB | phase 2 |
| Charlotte Cup Pro | `ifbb_charlotte_cup_pro` | Charlotte Pro - IFBB | ✅ |
| DC Natural Pro | `ifbb_dc_natural_pro` | DC Natural Pro - IFBB | phase 2 |
| DC Pro | `ifbb_dc_pro` | DC Pro - IFBB | phase 2 |
| Detroit Pro | `ifbb_detroit_pro` | Detroit Pro - IFBB | ✅ |
| Emerald Cup Masters Pro | `ifbb_emerald_cup_masters_pro` | Emerald Cup Pro - IFBB | ✅ |
| Emerald Cup Natural Pro | `ifbb_emerald_cup_natural_pro` | Emerald Cup Natural Pro - IFBB | ✅ |
| Everest Poland Pro Muscle Games | `ifbb_everest_poland_pro_muscle_games` | Poland Pro - IFBB | phase 2 |
| FIBO Pro Championships | `ifbb_fibo_pro_championships` | Germany FIBO Pro - IFBB | ✅ |
| Fitworld Pro | `ifbb_fitworld_pro` | Anaheim FitWorld Pro - IFBB | ✅ |
| Florida Grand Prix Masters Pro | `ifbb_florida_grand_prix_masters_pro` | Florida Grand Prix Pro - IFBB | ✅ |
| GRL PWR Championships Pro | `ifbb_grl_pwr_championships_pro` |  | 🚫 (Bikini/Women's Wellness/Fit Model only) |
| Huanji Shanghai China Pro | `ifbb_huanji_shanghai_china_pro` | Shanghai China Pro - IFBB | ✅ |
| Kansas City Natural Pro | `ifbb_kansas_city_natural_pro` |  | 🚫 (Bikini only) |
| Kim Jun Ho Classic | `ifbb_kim_jun_ho_classic` | Kim Junho Korea Pro - IFBB | phase 2 |
| Las Vegas Natural Pro | `ifbb_las_vegas_natural_pro` | Las Vegas Natural Pro - IFBB | phase 2 |
| Legion Sports Fest Pro | `ifbb_legion_sports_fest_pro` | Legion Sports Fest Pro - IFBB | phase 2 |
| Los Angeles Grand Prix Pro | `ifbb_los_angeles_grand_prix_pro` | Los Angeles Grand Prix Pro - IFBB | ✅ |
| Marrakech Pro | `ifbb_marrakech_pro` | Marrakech Morocco Pro - IFBB | phase 2 |
| Memphis Pro | `ifbb_memphis_pro` | Memphis Pro - IFBB | phase 2 |
| Miami Pro | `ifbb_miami_pro` | Miami Pro - IFBB | phase 2 |
| Musclecontest Bullman Pro | `ifbb_musclecontest_bullman_pro` | Ireland Bullman Pro - IFBB | phase 2 |
| Musclecontest Japan Pro | `ifbb_musclecontest_japan_pro` | Japan Pro - IFBB | ✅ |
| Natural Strength Showdown Pro | `ifbb_natural_strength_showdown_pro` | (new — no match) | 🚫 (Bikini only) |
| New York Pro | `ifbb_new_york_pro` | New York Pro Championships - IFBB | ✅ |
| Oksana Grishina Pro | `ifbb_oksana_grishina_pro` | Oksana Grishina Moscow Pro - IFBB | ✅ |
| Omaha Pro | `ifbb_omaha_pro` | Omaha Pro - IFBB | phase 2 |
| Optimum Classic Pro | `ifbb_optimum_classic_pro` | Optimum Classic Pro - IFBB | phase 2 |
| Pittsburgh Pro | `ifbb_pittsburgh_pro` | Pittsburgh Pro - IFBB | phase 2 |
| Puerto Rico Pro | `ifbb_puerto_rico_pro` | Puerto Rico Pro Championships - IFBB | ✅ |
| Sampson Showdown Pro | `ifbb_sampson_showdown_pro` |  | 🚫 (Wellness only) |
| San Diego Pro | `ifbb_san_diego_pro` | San Diego Pro - IFBB | 🚫 (Bikini only) |
| Southern USA Pro | `ifbb_southern_usa_pro` | Southern USA Pro - IFBB | phase 2 |
| St. Louis Pro | `ifbb_st_louis_pro` | St Louis Pro - IFBB | ✅ |
| Taiwan Pro | `ifbb_taiwan_pro` | Taiwan Pro - IFBB | ✅ |
| Top Tan Spain Pro | `ifbb_top_tan_spain_pro` | Spain Top Tan Pro - IFBB | ✅ |
| Tri-City Pro | `ifbb_tricity_pro` | Tri-City Georgia Pro - IFBB | ✅ |
| Triple O Dynasty Pro | `ifbb_triple_o_dynasty_pro` | Triple O Dynasty Arizona Pro - IFBB | ✅ |
| Tsunami Nutrition Showdown Pro | `ifbb_tsunami_nutrition_showdown_pro` | France Tsunami Showdown Pro - IFBB | phase 2 |
| Utah Cup Pro | `ifbb_utah_cup_pro` | Utah Cup Pro - IFBB | ✅ |
| Wasatch Warrior Pro | `ifbb_wasatch_warrior_pro` | Wasatch Warrior Pro - IFBB | ✅ |
| Zhanna Rotar Classic Pro | `ifbb_zhanna_rotar_classic_pro` | Zhanna Rotar Classic Pro - IFBB | phase 2 |

## Notes


- ✅ reflects whether the **2026** result has been retrieved/inserted, not
  whether the contest name exists historically. Most blank (To Fetch) rows
  already exist in the DB under prior years.

