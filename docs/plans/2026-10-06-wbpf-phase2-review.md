# WBPF / ABBF — Phase 2 review (overnight run 2026-10-06)

Phase 2 extracted WBPF/ABBF results into flat files in `~/workspace/musmem/1-incoming/` (names `{year}_{contest}-{org}-{gender}.txt`). Nothing past Phase 2 has been run.

**How to change anything:** all decisions live in `~/workspace/musmem/working_data/wbpf/`:
- `gen.py`: category → code rules (`classify` / `assign_codes`), event titles (`EVENTS`), overall winners.
- `patches.json`: per-row source fixes, each with a reason.
- `raw/*.json`: parsed source rows. Parsers: `parse_text.py`, `parse_rankfirst.py`, `parse_placing.py`, `parse_columns.py`, `manual_raw.py`; run all text ones with `batch_text.sh`.
- Regenerate: `python3 gen.py` (all events) or `python3 gen.py world-2023`, then `python3 gen_review.py` to refresh this doc.

## Questions for you (standing decisions that affect many files)

1. **DECIDED 2026-10-06:** Sports Physique (men's & women's) → `PH` family; Model Physique → excluded; Women's Muscular Physique (Europeans only) → Women's Bodybuilding `BB`. ~~Sports Physique, no DB precedent.~~ WBPF's board-shorts physique category, every year from 2015 on. Left out of every file. Proposal: men → `PH` / `Pa`…`Pd` by height in the male file; women → ? (women's model physique already uses `Pa`… in the female file, per the 2016 DB precedent).
2. **Women's Model Physique.** Mapped to `Pa`/`Pb`/`Pc`… by height, following the DB's ABBF 2016 entry (2012 left it out). Masters ("Ladies … over 35") → `MP`; 30–40 / over 40 → `P3` / `P4`; junior → `PJ`. Confirm or redirect.
3. **Excluded per precedent / skill rules:** Men's & Women's **Fitness Physique** (not in the DB's 2016 entry), **One-Piece Swimsuit / Swimsuit Physique / Wellness** (treated like bikini), **Mixed Pairs**, team results.
4. **Men's bodybuilding weight classes use the named codes the DB already uses for WBPF/ABBF:** 55 `LF`, 60 `FW`, 65 `BW`, 70 `LW`, 75 `WW`, 80 `LM`, 85 `MW`, 90 `LH`, 100 `HW`, over 100 `SW`, and over 90 → `o90kg`. **DECIDED 2026-10-06:** regional top classes "over 75/80/85/90 kg" → `o75kg`/`o80kg`/`o85kg`/`o90kg` (user added o75kg/o85kg to en.json).
5. **Masters BB:** 40–49 → `4L`/`4H` (up to / over 80 kg) or `M4`; 50–59/60 → `5L`/`5H` or `M5`; over 60 → `M6`; over 45 → `45`; no age → `MA`. Women's "Ladies BB over 30" → `MA` (female file). **Athletic physique:** 1 class → `AP`, 2 → `As`/`At`, 3+ → `A1`…`A5` by height (DB precedent 2011/2012/2016); masters athletic → `APM` (`APM3`/`APM4`/`APM5` when the label gives 30/40/50+; user decision 2026-10-06, `am` being phased out). **DECIDED:** Worlds 2018/2019 split → 30–40 `APM3`, over 40 `APM4`. Junior athletic → `JA`; teen classes excluded (decided; only Asian 2023 Women's Teenager Athletic).
6. **Overall winners** are written as `c OP` / `0 Name` (current skill rule). The DB's existing 2009–2014 WBPF/ABBF rows use a bare `0`, so check consistency when importing.
7. **New contest titles (provisional, change in `gen.py` EVENTS):** `South East Asian Championships - WBPF`, `South Asian Championships - WBPF`. The source documents carry SEABPF/SABPF/WBPF branding, not ABBF, so per your rule I used WBPF. Asian stays `Asian Championships - ABBF`; Europe `European Championships - WBPF`; Worlds `World Championships - WBPF` (Mr Universe = its `OP-0`).
8. **Name order:** files use `l 0` (first-last) except European 2022 (`l 1`; EBPF lists `SURNAME Given`). Many Asian sources print family name first (Vietnamese/Chinese/Korean), which Phase 3 normalization will need to handle. A few names arrive already comma-formatted from the source ("Png Kim Tian, Madeleine", "Sun, Shu-Ting", "Teo Wee Beng, Dennis") and were left as-is; Phase 3 treats a comma as already normalized.

- **Name truncation (fixed 2026-10-06):** some PDFs cut long names at the column width, sometimes gluing the country on ("…Binti MohMALAYSIA"). Country detection fixed; 8 mid-word truncations expanded via `patches.json` `_all`. Still truncated, left as printed: "Ameer Mohamed Mohsen Mohamed A/Al" (BH; probably "…Alarab") and "Jayawardhene Thenura Laksen Jose/Josep" (LK; probably "…Joseph").

- **Honorifics & abbreviations (2026-10-06):** removed anywhere in a name: Bruneian *Ak* (Awangku), *Pg* (Pengiran), *Hj*/*Haji* (also inside "Bin Haji X"); leading Mr/Ms/Dr/Col/Ing/Dipl were already stripped. Kept as name parts: Tun, Wan, Raja, Sri, Shree, Syed/Sayed. The skill's `clean_name()` splits two-consonant tokens into initials; `gen.py` `KEEP_PAIRS` undoes that for Md (Mohammad), Mg (Burmese Maung), Th (Thokchom), Kc (Nepali surname), Pd (Prasad). These could also be added to the shared `clean_name()` exception list (Jr/Sr/St/Ng) for future extractions.

## Not extracted / put aside

- **Asian 2017:** source labels two Women's BB classes "up to 52 kg"; the second (p28) was assumed to be over 52 kg (`patches.json`). **South Asian 2014:** first two classes labeled only "Up to 70kg / Above 70kg"; **decided:** juniors → `JL`/`JH`.
- **Asian 2013:** **extracted (partial)** after the user removed the bad DB rows. Day One + Day Three score sheets (10 classes, top 5) + Mr Asia Ghasempur; Day Two never archived. Junior 60/70 kg → `JF`/`JL`; athletic 170/175/+175 pinned to `A3`/`A4`/`A5` (160/165 presumably on lost Day Two). → `manual/asian-2013.txt`
- **Extracted visually from images (spot-check welcome):** Asian 2018 (52nd, Pune; scanned score sheets, full placings) → `manual/asian-2018.txt`; European 2024 (13th, Budapest; top-5 cards) → `manual/european-2024.txt`; World 2022 (top-5 class images, replacing the top-3 report text; 65/70 kg images 404 so those stay top 3) → `manual/world-2022m.txt`.
  - European 2024: the cards print most names SURNAME-first. I wrote First Last, flipping where the given name was clear; "Dali Radu" was left as printed. Pages 12 and 13 are both labeled "Men's BB up to 75 kg"; **decided:** p13 = up to 80 kg (`LM`). Kristián Tóth shows Hungary on one card and Slovakia on another.
  - Asian 2018: "Women's **Ladies** Athletic Physique Open" is mapped to masters `am` ("Ladies" = 35+ elsewhere in WBPF), but its roster overlaps the open women's classes, so it may just be an overall/open class.
- **Asian 2026 (58th, Bangkok):** found on the live abbf.asia only (not yet on wbpsf.org). One class is printed just as "Men's Athletic" (after "up to 182 cm"), assumed over 182 cm (`patches.json`). The overall boxes were jumbled in the text and matched by trunk number.
- **World 2019:** the 60 kg class isn't in the report's text layer (probably an image page).
- **World 2024:** results/report text has only the top 3 per class.
- **Asian 2010 (44th, Tehran):** abbf.asia hub has photos only, no results found. **Asian 2014 / World 2014 (in DB):** day results found (World 2014 `12012015-4/5/6.pdf`, Asian 2014 `29092014.pdf` not archived); kept for a missing-divisions pass.
- **SEA 2014 (12th, Singapore):** photo captions with spaces stripped. Needs a visual pass. Overall = Vachara Sasrisank (Thailand).
- **Central Asian 2015 (1st, Almaty):** **extracted** as `Central Asian Championships - WBPF` with the only two known results (OP-0 Volynkin, Women's AP-1 Nurbekova). The IFBB Kazakhstan "Central Asian Championship 2026" (Oral) is a different federation's event; ignored for now (user decision).
- **South Asian 2011 (8th), 2012 (9th):** 2012 results PDF (`10112012c.pdf`) not yet fetched from Wayback; 2012 Mr South Asia = Sangram Chougule.
- **SEA Games 2013 (Yangon) & 2022 (Hanoi):** **extracted** as new `South East Asian Games - WBPF` (user decision; DB's IFBB-era SEA Games stay `South East Asian Games - IFBB`). 2013: 5 classes top 5 (text); 2022: 7 BB classes + Men's Athletic Open + Women's BB, top 3 (images). **Asian Beach Games:** skipped (user decision).
- **Other WBPF results seen (not extracted):** Austrian Championships/Cup, Kriko Cup, Maldives International 2023, Pacific Games 2023 (image report), Mr & Ms Global, King of Kings, Transylvania Cup, Night of Champions (Tashkent).


## Per-event results

| Event | Files (competitors / divisions) | Open items |
|---|---|---|
| world-2016 | `2016_world_championships-wbpf-male.txt` (106/21)<br>`2016_world_championships-wbpf-female.txt` (23/5) | 0 |
| asian-2013 | `2013_asian_championships-abbf-male.txt` (50/10) | 0 |
| asian-2015 | `2015_asian_championships-abbf-male.txt` (58/19)<br>`2015_asian_championships-abbf-female.txt` (15/5) | 0 |
| asian-2017 | `2017_asian_championships-abbf-male.txt` (61/20)<br>`2017_asian_championships-abbf-female.txt` (12/4) | 0 |
| world-2018 | `2018_world_championships-wbpf-male.txt` (255/26)<br>`2018_world_championships-wbpf-female.txt` (74/10) | 1 |
| world-2019 | `2019_world_championships-wbpf-male.txt` (154/25)<br>`2019_world_championships-wbpf-female.txt` (44/9) | 0 |
| world-2021 | `2021_world_championships-wbpf-male.txt` (213/23)<br>`2021_world_championships-wbpf-female.txt` (21/6) | 0 |
| world-2022 | `2022_world_championships-wbpf-male.txt` (238/23)<br>`2022_world_championships-wbpf-female.txt` (26/5) | 0 |
| world-2023 | `2023_world_championships-wbpf-male.txt` (186/26)<br>`2023_world_championships-wbpf-female.txt` (51/8) | 0 |
| world-2024 | `2024_world_championships-wbpf-male.txt` (170/26)<br>`2024_world_championships-wbpf-female.txt` (48/8) | 0 |
| world-2025 | `2025_world_championships-wbpf-male.txt` (159/22)<br>`2025_world_championships-wbpf-female.txt` (29/7) | 0 |
| asian-2018 | `2018_asian_championships-abbf-male.txt` (210/26)<br>`2018_asian_championships-abbf-female.txt` (31/7) | 0 |
| asian-2019 | `2019_asian_championships-abbf-male.txt` (192/26)<br>`2019_asian_championships-abbf-female.txt` (23/7) | 0 |
| asian-2022 | `2022_asian_championships-abbf-male.txt` (82/27)<br>`2022_asian_championships-abbf-female.txt` (21/7) | 0 |
| asian-2023 | `2023_asian_championships-abbf-male.txt` (174/24)<br>`2023_asian_championships-abbf-female.txt` (33/6) | 0 |
| asian-2024 | `2024_asian_championships-abbf-male.txt` (130/26)<br>`2024_asian_championships-abbf-female.txt` (27/6) | 0 |
| asian-2025 | `2025_asian_championships-abbf-male.txt` (208/26)<br>`2025_asian_championships-abbf-female.txt` (38/7) | 0 |
| asian-2026 | `2026_asian_championships-abbf-male.txt` (167/26)<br>`2026_asian_championships-abbf-female.txt` (41/6) | 0 |
| centralasian-2015 | `2015_central_asian_championships-wbpf-male.txt` (1/0)<br>`2015_central_asian_championships-wbpf-female.txt` (1/1) | 0 |
| seagames-2013 | `2013_south_east_asian_games-wbpf-male.txt` (24/5) | 0 |
| seagames-2022 | `2022_south_east_asian_games-wbpf-male.txt` (24/8)<br>`2022_south_east_asian_games-wbpf-female.txt` (3/1) | 0 |
| european-2022 | `2022_european_championships-wbpf-male.txt` (29/14)<br>`2022_european_championships-wbpf-female.txt` (8/4) | 0 |
| european-2024 | `2024_european_championships-wbpf-male.txt` (60/16)<br>`2024_european_championships-wbpf-female.txt` (21/7) | 0 |
| sea-2014 | `2014_south_east_asian_championships-wbpf-male.txt` (38/9)<br>`2014_south_east_asian_championships-wbpf-female.txt` (11/3) | 1 |
| sea-2019 | `2019_south_east_asian_championships-wbpf-male.txt` (80/14)<br>`2019_south_east_asian_championships-wbpf-female.txt` (9/2) | 0 |
| sea-2023 | `2023_south_east_asian_championships-wbpf-male.txt` (62/14)<br>`2023_south_east_asian_championships-wbpf-female.txt` (8/2) | 0 |
| sea-2024 | `2024_south_east_asian_championships-wbpf-male.txt` (76/15)<br>`2024_south_east_asian_championships-wbpf-female.txt` (4/1) | 0 |
| sea-2025 | `2025_south_east_asian_championships-wbpf-male.txt` (66/13) | 0 |
| sea-2026 | `2026_south_east_asian_championships-wbpf-male.txt` (79/14)<br>`2026_south_east_asian_championships-wbpf-female.txt` (9/2) | 0 |
| southasian-2010 | `2010_south_asian_championships-wbpf-male.txt` (29/9) | 2 |
| southasian-2011 | `2011_south_asian_championships-wbpf-male.txt` (37/9) | 0 |
| southasian-2012 | `2012_south_asian_championships-wbpf-male.txt` (2/1) | 0 |
| southasian-2014 | `2014_south_asian_championships-wbpf-male.txt` (43/11) | 0 |
| sea-2012 | `2012_south_east_asian_championships-wbpf-male.txt` (8/8) | 0 |
| southasian-2019 | `2019_south_asian_championships-wbpf-male.txt` (55/14)<br>`2019_south_asian_championships-wbpf-female.txt` (3/1) | 1 |
| southasian-2023 | `2023_south_asian_championships-wbpf-male.txt` (75/17) | 0 |
| southasian-2024 | `2024_south_asian_championships-wbpf-male.txt` (64/19) | 0 |
| southasian-2025 | `2025_south_asian_championships-wbpf-male.txt` (46/13)<br>`2025_south_asian_championships-wbpf-female.txt` (3/1) | 0 |
| southasian-2026 | `2026_south_asian_championships-wbpf-male.txt` (86/15)<br>`2026_south_asian_championships-wbpf-female.txt` (6/1) | 0 |

## Categories left out pending your decision (by reason)


## Per-event notes (overall, gaps, patches, mapped-with-note)

**world-2016**

- [patched] name wrapped over two lines in source (1 rows)
- [patched] name wrapped over two lines in source (1 rows)
- [patched] name wrapped over two lines in source (1 rows)
- [patched] column bleed (2 rows)
- [patched] class split across page break (places 1-2 on p4, 3-4 on p5) (2 rows)
- [patched] "South Korea" wrapped in source; number, "South" and scores bled into name (1 rows)
- [patched] "South Korea" wrapped in source; number, "South" and scores bled into name (1 rows)
- [overall] OP-0 Mahdi Sabzevari  (trunk None; source name "Mahdi Sabzevari")

**asian-2013**

- [mapped-with-note] Men's Junior Bodybuilding 60 kg -> JF  — pinned in CODE_OVERRIDES
- [mapped-with-note] Men's Junior Bodybuilding 70 kg -> JL  — pinned in CODE_OVERRIDES
- [mapped-with-note] Men's Athletic Physique 170 cm+3 kg -> A3  — pinned in CODE_OVERRIDES
- [mapped-with-note] Men's Athletic Physique 175 cm+4 kg -> A4  — pinned in CODE_OVERRIDES
- [mapped-with-note] Men's Athletic Physique over 175 cm+5 kg -> A5  — pinned in CODE_OVERRIDES
- [overall] OP-0 Mohamadreza Ghasempur  (trunk 109; source name "Mohamadreza Ghasempur")

**asian-2015**

- [patched] country split and glued into name in source (1 rows)
- [mapped-with-note] Men's Master Bodybuilding - Open -> MA  — masters, no age given
- [overall] OP-0 Saeed Khanchsaz  (trunk None; source name "Saeed Khanchsaz")

**asian-2017**

- [patched] source labels two different classes 'up to 52 kg' (p9 and p28); p28 assumed to be over 52 kg — confirmed by user 2026-10-06 (3 rows)
- [overall] OP-0 B D Lucion Anton Pushparaj  (trunk None; source name "B D Lucion Anton Pushparaj")

**world-2018**

- [mapped-with-note] Women's Ladies Bodybuilding over 30yrs -> MA  — women's bodybuilding masters (over 30/35)
- [mapped-with-note] Women's Ladies Sports Physique 30yrs and over -> MP  — masters sports physique
- [mapped-with-note] Women's Ladies Athletic Physique 30- 40 yrs -> APM3  — masters athletic physique 30+
- [mapped-with-note] Women's Ladies Athletic Physique over 40 yrs -> APM4  — masters athletic physique 40+
- [overall] OP-0 B D Lucion Anton Pushparaj  (trunk 195; source name "B.D. Lucion Anton Pushparaj")
- [gaps] Pb Men's Sports Physique up to 175 cm: places [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 14]

**world-2019**

- [mapped-with-note] WOMEN'S LADIES Bodybuilding AGE OVER 30YRS -> MA  — women's bodybuilding masters (over 30/35)
- [mapped-with-note] WOMEN'S LADIES ATHLETIC PHYSIQUE 30-40 YRS -> APM3  — masters athletic physique 30+
- [mapped-with-note] WOMEN'S LADIES ATHLETIC PHYSIQUE OVER 40YRS -> APM4  — masters athletic physique 40+
- [mapped-with-note] WOMEN'S LADIES SPORTS PHYSIQUE AGE 30YRS AND ABOVE -> MP  — masters sports physique
- [overall] OP-0 Kongarampilly Natesan Chitharesh  (trunk 89; source name "KONGARAMPILLY NATESAN CHITHARESH")

**world-2021**

- [mapped-with-note] WOMEN'S LADIES SPORTS PHYSIQUE 30-40 YRS -> MP  — masters sports physique
- [mapped-with-note] WOMEN'S LADIES Bodybuilding OVER 30 YRS -> MA  — women's bodybuilding masters (over 30/35)
- [mapped-with-note] WOMENS LADIES ATHLETIC PHYSIQUE AGE 30-40 YRS - OPEN CATEGORY -> APM3  — masters athletic physique 30+
- [overall] OP-0 Reza Nouriara  (trunk 130; source name "REZA NOURIARA")

**world-2022**

- [overall] OP-0 Karthikeswar R  (trunk 106; source name "Karthikeswar R")

**world-2023**

- [patched] name truncated at source column width (1 rows): Muhamad Shaiful Hisyam Bin Abd Aziz
- [mapped-with-note] Women's Ladies Sports Physique over 35 yrs -> MP  — masters sports physique
- [mapped-with-note] Women's Ladies Athletic Physique over 35 yrs -> APM  — masters athletic physique (no age code, e.g. over 35)
- [overall] OP-0 Sarvanan Mani  (trunk 183; source name "Sarvanan Mani")

**world-2024**

- [mapped-with-note] Women's Ladies Sports Physique over 35 yrs -> MP  — masters sports physique
- [mapped-with-note] Women's Ladies Athletic Physique over 35 yrs -> APM  — masters athletic physique (no age code, e.g. over 35)
- [overall] OP-0 Saravanan Mani  (trunk 98; source name "SARAVANAN MANI")

**world-2025**

- [patched] name truncated at source column width (1 rows): Erne Marina Ainalisa Binti Mohd Noer
- [mapped-with-note] Women's Ladies Sports Physique over 35 yrs -> MP  — masters sports physique
- [mapped-with-note] Women's Athletic Physique up to 165 cm -> AP  — single height class collapsed to outer code
- [mapped-with-note] Women's Ladies Athletic Physique over 35 yrs -> APM  — masters athletic physique (no age code, e.g. over 35)
- [overall] OP-0 Saravanan Mani  (trunk 74; source name "SARAVANAN MANI")

**asian-2018**

- [mapped-with-note] Men's Para Bodybuilding -> HC  — para bodybuilding -> HC (physically challenged)
- [mapped-with-note] Women's Ladies Athletic Physique Open -> APM  — masters athletic physique (no age code, e.g. over 35)
- [mapped-with-note] Women's Ladies Sports Physique Open -> MP  — masters sports physique
- [overall] OP-0 Sunit Jadhav  (trunk 81; source name "Sunit Jadhav")

**asian-2019**

- [patched] name wrapped onto its own line and was absorbed into the class label (1 rows)
- [patched] name wrapped onto its own line and was absorbed into the class label (1 rows)
- [patched] strip absorbed name from class label (8 rows)
- [patched] strip absorbed name from class label (4 rows)
- [patched] name truncated at source column width (1 rows): Mohd Syarul Azman Mahen Bin Abdullah
- [mapped-with-note] Men's Para Bodybuilding -> HC  — para bodybuilding -> HC (physically challenged)
- [mapped-with-note] WOMEN'S LADIES Bodybuilding AGE OVER 30 YRS -> MA  — women's bodybuilding masters (over 30/35)
- [mapped-with-note] WOMEN'S ATHLETIC PHYSIQUE UP TO 165 CM -> AP  — single height class collapsed to outer code
- [mapped-with-note] Women's Ladies Athletic Physique over 30yrs -> APM3  — masters athletic physique 30+
- [overall] OP-0 Chitharesh Kongarampilly Natesan  (trunk 83; source name "Chitharesh Kongarampilly Natesan")

**asian-2022**

- [mapped-with-note] 15TH - 21ST JULY 2022 THE REPUBLIC OF THE MALDIVES ABBF EXECUTIVE COUNCIL MEETING ABBF ANNUAL CONGRESS :Organiser: Bodybuilding ASSOCIATION OF MALDIVES :Supported by: MINISTRY OF YOUTH, SPORTS AND COMMUNITY EMPOWERMENT REPUBLIC OF REPUBLIC OF MALDIVES :In collaboration with: MALDIVES OLYMPIC COMMITTEE 15TH - 21ST JULY 2022 THE REPUBLIC OF THE MALDIVES PARA Bodybuilding -> HC  — para bodybuilding -> HC (physically challenged)
- [mapped-with-note] LADIES WOMEN'S Bodybuilding OVER 30 YRS. - ONE OPEN CATEGORY -> MA  — women's bodybuilding masters (over 30/35)
- [mapped-with-note] LADIES WOMEN'S SPORT PHYSIQUE OVER 30 YRS. ONE OPEN CATEGORY -> MP  — masters sports physique
- [mapped-with-note] SENIOR WOMEN'S ATHLETIC PHYSIQUE UP TO 165 CM ONE OPEN CATEGORY -> AP  — single height class collapsed to outer code
- [mapped-with-note] LADIES WOMEN'S ATHLETIC PHYSIQUE OVER 40 YRS. ONE OPEN CATEGORY -> APM4  — masters athletic physique 40+
- [overall] OP-0 Yatinder Singh  (trunk 87; source name "YATINDER SINGH")

**asian-2023**

- [overall] OP-0 Saravanan Mani  (trunk 79; source name "Saravanan Mani")

**asian-2024**

- [patched] name truncated at source column width (1 rows): Siti Hadjar Binti Mansor Awang Hitam
- [mapped-with-note] Women's Ladies Sports Physique over 35 yrs -> MP  — masters sports physique
- [overall] OP-0 Ganzorig Enkhtuvshin  (trunk 62; source name "GANZORIG ENKHTUVSHIN")

**asian-2025**

- [mapped-with-note] WOMEN'S LADIES SPORTS PHYSIQUE OVER 35 YRS -> MP  — masters sports physique
- [mapped-with-note] WOMEN'S LADIES ATHLETIC PHYSIQUE OVER 35 YRS -> APM  — masters athletic physique (no age code, e.g. over 35)
- [overall] OP-0 Arshan Khan  (trunk 109; source name "Arshan Khan")

**asian-2026**

- [patched] source cell reads only 'Men's Athletic' (p4); follows 'up to 182 cm' so assumed over 182 cm — confirmed by user 2026-10-06 (3 rows)
- [mapped-with-note] Women's Ladies Sports Physique over 35 yrs -> MP  — masters sports physique
- [mapped-with-note] Women's Ladies Athletic Physique over 35 yrs -> APM  — masters athletic physique (no age code, e.g. over 35)
- [mapped-with-note] Women's Athletic Physique up to 165 cm -> AP  — single height class collapsed to outer code
- [overall] OP-0 Rishkanta Singh Laitonjam  (trunk 95; source name "Rishkanta Singh Laitonjam")
- [overall] PH-0 Bilal Ahmed  (from ranked "Men's Sports Physique Overall")
- [overall] AP-0 Abdul Aziz Bin Ahmad  (from ranked "Men's Athletic Physique Overall")

**centralasian-2015**

- [overall] OP-0 Mikhail Volynkin  (trunk None; source name "Mikhail Volynkin")

**european-2022**

- [overall] OP-0 Gojković Nebojša  (from ranked "Men's Bodybuilding Overall")
- [name-order] source lists SURNAME first (e.g. "VARGA Ildiko") -> wrote l 1
- [name-order] source lists SURNAME first (e.g. "VARGA Ildiko") -> wrote l 1

**european-2024**

- [mapped-with-note] Men's Gentleman Sports Physique over 35 yrs -> MP  — masters sports physique
- [mapped-with-note] Men's Athletic Physique over 40 yrs -> APM4  — masters athletic physique 40+
- [mapped-with-note] Women's Lady Athletic Physique over 40 yrs -> APM4  — masters athletic physique 40+
- [mapped-with-note] Women's Lady Sports Physique 30-40 yrs -> P3  — masters model physique 30-40
- [mapped-with-note] Women's Lady Sports Physique over 40 yrs -> P4  — masters model physique 40+
- [overall] PH-0 Bence Kalmár  (from ranked "Men's Sports Physique Overall")
- [overall] AP-0 Balázs Andrasek  (from ranked "Men's Athletic Physique Overall")
- [overall] OP-0 József Móker  (from ranked "Men's Bodybuilding Overall")
- [overall] DROPPED AP-0 Olha Lytvynenko — AP already has placings (single class), nothing to compare
- [overall] PH-0 Dalma Kovács  (from ranked "Women's Sports Physique Overall")

**sea-2014**

- [mapped-with-note] Men's Bodybuilding over 85 kg -> o85kg  — top class over 85 kg -> o85kg
- [overall] OP-0 Vachara Sasrisank  (trunk None; source name "Vachara Sasrisank")
- [gaps] At Men's Athletic Physique above 170 cm: places [1, 2, 3, 5]

**sea-2019**

- [patched] name truncated at source column width (1 rows): Zmarul Al Adam Pulutan Abdullah
- [patched] name truncated at source column width (1 rows): Muammar Gaddafi Bin Muhamad
- [patched] name truncated at source column width (1 rows): Thepphorn Phuangthapthim
- [mapped-with-note] Men's Bodybuilding over 80 kg -> o80kg  — top class over 80 kg -> o80kg
- [overall] OP-0 Zorizal Bin Johari  (trunk 34; source name "Zorizal Bin Haji Johari")

**sea-2023**

- [mapped-with-note] MEN'S Bodybuilding OVER 80KG -> o80kg  — top class over 80 kg -> o80kg
- [overall] OP-0 Nguyen Minh My  (trunk 38; source name "Nguyen Minh My")

**sea-2024**

- [patched] name truncated at source column width (1 rows): Siti Hadjar Binti Mansor Awang Hitam
- [mapped-with-note] Men's Bodybuilding over 75 kg -> o75kg  — top class over 75 kg -> o75kg

**sea-2025**

- [mapped-with-note] MEN'S Bodybuilding OVER 80KG -> o80kg  — top class over 80 kg -> o80kg
- [overall] OP-0 Chan Myae Tun  (trunk 62; source name "Chan Myae Tun")

**sea-2026**

- [patched] name truncated at source column width (1 rows): Mohd Adzrul Ridzuwan Bin Adzahar
- [mapped-with-note] MEN'S Bodybuilding OVER 80 KG -> o80kg  — top class over 80 kg -> o80kg
- [overall] OP-0 Chan Myae Tun  (trunk 62; source name "CHAN MYAE TUN")

**southasian-2010**

- [mapped-with-note] Men's Bodybuilding over 90 kg -> o90kg  — top class over 90 kg -> o90kg
- [gaps] LF Men's Bodybuilding 55 kg: places [1, 2, 3, 3]
- [gaps] WW Men's Bodybuilding 75 kg: places [1, 2, 3, 3]
- [ties] LF: joint place 3 kept (source awarded two bronzes)
- [ties] WW: joint place 3 kept (source awarded two bronzes)

**southasian-2011**

- [patched] source label is only the weight (4 rows)
- [patched] source label is only the weight (3 rows)
- [patched] source label is only the weight (5 rows)
- [patched] source label is only the weight (5 rows)
- [patched] source label is only the weight (4 rows)
- [patched] source label is only the weight (5 rows)
- [patched] source label is only the weight (3 rows)
- [patched] source label is only the weight (3 rows)
- [patched] source label is only the weight (4 rows)
- [patched] team table misread as athletes (3 rows)
- [patched] name glued in source (1 rows)
- [mapped-with-note] Men's Bodybuilding over 90 kg -> o90kg  — top class over 90 kg -> o90kg
- [overall] OP-0 Boby Singh  (trunk 32; source name "Boby Singh")

**southasian-2012**

- [overall] OP-0 Sangram Chougule  (trunk None; source name "Sangram Chougule")

**southasian-2014**

- [patched] source label lacks gender word (3 rows)
- [patched] source label lacks gender word (4 rows)
- [patched] source label lacks gender word (5 rows)
- [patched] source label lacks gender word (4 rows)
- [patched] source label lacks gender word (4 rows)
- [patched] source label lacks gender word (4 rows)
- [patched] source label lacks gender word (5 rows)
- [patched] source label lacks gender word (4 rows)
- [patched] source label lacks gender word (3 rows)
- [patched] source labels only "Weight Up to 70kg" (listed before seniors); user decision 2026-10-06: junior -> JL (4 rows)
- [patched] source labels only "Weight Above 70kg"; user decision 2026-10-06: junior -> JH (3 rows)
- [mapped-with-note] Men's Bodybuilding over 90 kg -> o90kg  — top class over 90 kg -> o90kg

**southasian-2019**

- [mapped-with-note] SENIOR MEN'S Bodybuilding OVER 90 KG -> o90kg  — top class over 90 kg -> o90kg
- [overall] OP-0 Ravinder Kumar Malik  (trunk None; source name "Ravinder Kumar Malik")
- [gaps] Pa MEN'S SPORTS PHYSIQUE UPTO 170 CM: places [1, 2, 4, 5]

**southasian-2023**

- [mapped-with-note] SENIOR MEN'S Bodybuilding OVER 90 KG -> o90kg  — top class over 90 kg -> o90kg
- [overall] OP-0 Sarvanan Mani  (trunk 91; source name "SARVANAN MANI")

**southasian-2024**

- [mapped-with-note] SENIOR MEN'S Bodybuilding Over 90 Kg. -> o90kg  — top class over 90 kg -> o90kg

**southasian-2025**

- [mapped-with-note] MEN'S Bodybuilding OVER 85 KG -> o85kg  — top class over 85 kg -> o85kg
- [overall] OP-0 Naveen Rojh  (trunk None; source name "Naveen Rojh")

**southasian-2026**

- [mapped-with-note] SENIOR MEN'S Bodybuilding OVER 85 KG -> o85kg  — top class over 85 kg -> o85kg
- [overall] OP-0 Rahul Singh Chauhan  (trunk None; source name "Rahul Singh Chauhan")

