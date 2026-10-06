# NPC Contest Name Mapping

Maps npcnewsonline.com contest titles for NPC-sanctioned amateur shows to their
corresponding canonical MuscleMemory database contest name. Names frequently
differ between the two sites — sponsor names get added/dropped (e.g. "Bev
Francis"), "State"/"Championships" gets added or dropped, or the show is
tracked in MuscleMemory under a completely different brand name for the same
event.

This is the NPC (amateur) counterpart to `contest-name-mapping.md`, which
covers IFBB Pro shows.

Status column:
- `confirmed` — verified match between the two names
- `new` — no corresponding contest exists in MuscleMemory yet; name shown is
  the canonical name to use when adding it (org-suffix convention: strip the
  leading "NPC " from the npcnewsonline title, append " - NPC")

| npcnewsonline name | musclememory name | status |
|---|---|---|
| NPC Bev Francis Atlantic States Championships | Atlantic States Championships - NPC | confirmed |
| NPC California Night of Champions | California Night of Champions - NPC | new |
| NPC California State Championships | California Championships - NPC | confirmed |
| NPC Contra Costa Championships | Contra Costa (CA) Championships - NPC | confirmed |
| NPC Emerald Cup Open | Emerald Cup - NPC | confirmed |
| NPC Golden State Championships | Golden State Championships - NPC | confirmed |
| NPC Governors Cup | California Governor's Cup - NPC | confirmed |
| NPC Los Angeles Grand Prix | Titans Grand Prix (Los Angeles) - NPC | confirmed |
| NPC Michigan State Championships | Michigan State Championships - NPC | confirmed (2026 roster 39/39; was mis-recorded as "Michigan Championships - NPC", which does not exist in the DB) |
| NPC Natural Steve Stone Metropolitan Championships | New York Metro Championships - NPC | confirmed |
| NPC New York Amateur | New York Amateur Grand Prix - NPC | confirmed |
| NPC Northern California Championships | Northern California - NPC | confirmed |
| NPC Pacific Coast Championship | Pacific Coast Championships - NPC | new |
| NPC Palmetto Classic | Palmetto Cup - NPC | confirmed |
| NPC San Jose Championships | San Jose Championships - NPC | confirmed |
| NPC San Diego Championships | San Diego Championships - NPC | confirmed |
| NPC Southern California Championships | Southern California Championships - NPC | confirmed |
| NPC Southern States Championships | Southern States - NPC | confirmed |
| NPC Southern USA | Southern USA - NPC | confirmed |
| NPC West Coast Classic | West Coast Classic - NPC | confirmed |
| NPC Wheelchair Nationals | Wheelchair Nationals - NPC | confirmed |
| NPC Universe | Team Universe Championships - NPC | confirmed |
| NPC All South Muscle Championship | All South Muscle Championships - NPC | confirmed (2025 roster 50/51) |
| NPC Pacific USA | Pacific USA Championships - NPC | confirmed (2017 roster 48/50) |
| NPC Los Angeles Championships | Los Angeles Championships - NPC | confirmed (2017 roster 78/81) |
| NPC Midwest Championships | Midwest Championships (STL) - NPC | confirmed (2017 roster 74/81). NOT "Midwest Championships - NPC" (2000-2009, older show) |
| NPC Tournament of Champions | Tournament of Champions - NPC | confirmed (2017 roster 33/35) |
| NPC Teen Collegiate & Masters National Championships | Teen Nationals - NPC / Collegiate Nationals - NPC / Masters Nationals - NPC | confirmed (2019 page holds all three: 17/17, 5/5, 485/514) — one page, three DB titles |
| NPC Fitworld | Fit World Championships (California) - NPC | confirmed (2019 roster 21/24) |
| NPC Gold Coast Muscle Classic | Gold Coast Muscle Classic (California) - NPC | confirmed (2019 roster 11/12) |
| NPC Legends Classic | Legends Classic (Las Vegas) - NPC | confirmed (2021 roster 4/4) |
| NPC SC Excalibur | Excalibur (South Carolina) - NPC | likely — slug chain npc_excalibur_championships (2016, roster 42/45) → npc_south_carolina_excalibur (2018-22) → npc_sc_excalibur (2023+) |
| NPC Musclecontest Challenge FitExpo LA | Muscle Contest (So Cal) - NPC | likely — npc_muscle_contest_challenge (2017 roster 22/23, 2018 22/25) became FitExpo LA in 2023; the Anaheim edition is a separate show |
| NPC Empire Classic | Empire Classic (WA) - NPC | confirmed (2026 roster 56/57) |
| NPC Garden State Championships | Garden State (NJ) Championships - NPC | confirmed (2026 roster 64/67) |
| NPC USA Bodybuilding Championships | USA Championships - NPC | confirmed (2026 roster 256/260) |
| NPC Washington State Open | Washington State Championships - NPC | confirmed (2026 roster 42/43) |
| NPC Amateur Olympia Las Vegas | Amateur Olympia Las Vegas - NPC Worldwide | confirmed by user 2026-10-04 (2022 roster 247/268). Listed under NPC (not NPCW) on npcnewsonline from 2024 on; keep the NPC Worldwide DB title |
| NPC Atlanta Classic | Atlanta Classic - NPC | new — added by user 2026-10-04 as its own contest, separate from "Atlanta Championships - NPC" (1988-2012) |
| NPC Mid-USA Championships | Mid USA - NPC | confirmed by user 2026-10-04 — reuse the DB title (DB years end 2003) |
| NPC South Central USA | South Central USA - NPC | confirmed by user 2026-10-04 — reuse the DB title (DB has 1983 only) |

Checked 2026-10-04 and found to be **different** contests despite similar names
(roster overlap near zero) — don't re-pair them:
- NPC Charlotte Cup ≠ Europa Charlotte - NPC (2017: 5/62)
- NPC Phoenix Natural Noble Warrior ≠ Phoenix Championships - NPC (2024: 0/51)
- NPC Iowa State Championships ≠ Midwest Championships (Iowa) - NPC (that DB title is npcnewsonline's "NPC Midwest Open Championships", 2013: 36/38)
- NPC Alabama Open Championships ≠ Alabama State Championships - NPC (Alabama State has its own slug, npc_alabama_state_championships)
- NPC Natural Mid-Atlantic Cup (new slug 2025) — not linked to Mid Atlantic Natural (NJ) - NPC, which was "NPC Mid Atlantic Natural Classic" (last seen 2018)

## NPC Worldwide

Same convention, org suffix ` - NPC Worldwide`. npcnewsonline lists these under
`/contests/{year}/npcw`. Note npcnewsonline writes "Olympia Amateur {Region}"
from 2026 on (2025 and earlier, and some 2026 entries, use "Amateur Olympia
{Region}"); the DB title is always "Amateur Olympia {Region}".

| npcnewsonline name | musclememory name | status |
|---|---|---|
| NPC Worldwide Amateur Olympia Spain | Amateur Olympia Spain - NPC Worldwide | confirmed |
| NPC Worldwide Olympia Amateur China | Amateur Olympia China - NPC Worldwide | confirmed |
| NPC Worldwide Olympia Amateur Eastern Europe | Amateur Olympia Eastern Europe - NPC Worldwide | confirmed |
| NPC Worldwide Olympia Amateur Portugal | Amateur Olympia Portugal - NPC Worldwide | confirmed |
| NPC Worldwide European Championships Pro Qualifier | European Championships - NPC Worldwide | confirmed |
| NPC Worldwide Arnold Amateur | Arnold Amateur - NPC Worldwide | confirmed |

## CPA

Org suffix ` - CPA`; npcnewsonline lists these under `/contests/{year}/cpa`.
As of 2026-10-04 the DB tracks only the two national pro qualifiers. The ~40
other CPA shows on the listing (provincial/regional) are untracked: a new-contest
decision for the user, not reviewed here.

| npcnewsonline name | musclememory name | status |
|---|---|---|
| CPA Canadian National Pro Qualifier | Canadian National Pro Qualifier - CPA | confirmed |
| CPA Natural Canada Pro Qualifier | Canadian Natural Pro Qualifier - CPA | confirmed (2025 roster: 181/187 DB names on page) |
