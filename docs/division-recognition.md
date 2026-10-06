# Division Recognition (source-agnostic)

npcnewsonline.com results are structured HTML with explicit `data-slug` attributes — division and class identity is deterministic (see `sources-reference.md`). Most other sources are not structured this way: PDFs (federation-published results, scanned or exported), and any HTML site without slug-like markup. This document is the source-agnostic method for recognizing division and class identity from free-form text, so the same discipline applies regardless of which site or file format the results come from.

Division codes themselves are universal (see `divisions-reference.md`) — this doc is only about mapping a source's own wording onto those codes.

## Step 1 — Identify the base division

A division/class header is free text, e.g. `Women's Bodyfitness up to 163 cm`, `Master Men's Classic Bodybuilding 40-44 Years, Open`, `Junior Women's Physique 16-23 Years, OVERALL`. Match the header against a **base division keyword table**. Keep this table growing as new sources are processed — federations use inconsistent names for the same category:

| Header contains | Base division |
|---|---|
| Bodybuilding (unqualified) | `OP` (male) / `BB` (female) |
| **Classic Physique** (as a qualifier — "Men's Classic Physique") | `CL` |
| **Classic Bodybuilding** (as a qualifier, no "Games" prefix — "Men's Classic Bodybuilding") — a *separate* IFBB amateur category from Classic Physique, confirmed via the 2022 European Amateur Championships (distinct roster, distinct height-class thresholds) | `CB` (dedicated code family — `CBa`-`CBe` classes, `CBJ` junior, `CB4`/`CB45`/`CB5` masters age brackets, `CBM` masters overall, `CB` open overall) |
| **"Games" prefix on any division name** (e.g. "Games Classic Bodybuilding") | excluded — do not write (confirmed via 2022 European Amateur Championships) |
| Physique, Men's/Women's Physique | `PH` |
| **Muscular Physique** (e.g. "Muscular Men's Physique Open") — a separate category from standard Physique | `MUP` |
| Figure, **Bodyfitness**, Body Fitness | `FI` |
| Wheelchair, Wheel-chair | `WC` |
| Physically Challenged / Adaptive / Special (standing) | `Hs` |
| Bikini, Bikini Shape, Bikini Fitness, Wellness, Fitness (unqualified — not "Men's/Women's Physique"), Fit Model, **Fit Body** | excluded — do not write (Fit Body confirmed via 2019 INBF Hercules — same competitors doing double/triple duty across Figure-family divisions same day, a toned-but-not-muscular judged category rather than a separate tracked discipline) |
| **Debut** (Bodybuilding/Bikini/Classic Physique/Men's Physique) — WNBF/INBF terminology | excluded — do not write (same entry-level-competitor concept as Novice/Beginner/First Timer, confirmed via 2025 WNBF Hercules Pro Am) |
| **Acrobatic Fitness, Artistic Fitness** — gymnastics-style fitness disciplines distinct from unqualified Fitness/Wellness | excluded — do not write (confirmed via 2023 IFBB European Amateur Championships; no DB code exists for these) |
| **"Classic Figure" + age number** (WNBF/INBF terminology) | Masters Figure at that age — maps to the division's age code same as bare "Master's Figure {age}" (e.g. `Classic Figure 50+` → `F5`), but only when its roster contains at least one competitor not already in the bare Master's Figure list for that page (i.e. it adds real information). Confirmed via 2018 Naturalmania Nationals (Jamil Miller not elsewhere on the page) — per user decision. |
| **Bare "Classic Figure"** (no age number) | A distinct division with no MuscleMemory code — excluded, do not write. (Earlier reasoning that a subset roster with matching relative order to Master's Figure implied it was a non-informative duplicate was wrong — a smaller field getting its own real placing is legitimate data, not proof of duplication. The actual reason to exclude it is simply that no code exists for it, same as Bikini/Wellness/Fitness.) Confirmed via 2019 Naturalmania Nationals — per user decision. |

`Bodyfitness` = `FI` is confirmed IFBB/EBFF (European federation) terminology. When a new source uses a division name not in this table, add it here once confirmed rather than guessing inline — this table is the shared memory across all future PDF/HTML extractions.

## Step 2 — Identify qualifiers on the header

Strip the base division keyword and look at what's left:

- **Age qualifiers** — `Junior` (+ age range), `Master`/`Masters` (+ age number or range) → resolve via the existing Junior/Masters code tables in `SKILL.md` Phase 2 (e.g. `f3`/`F4`/`f4` for Figure 35+/40+/45+, `P35` for Physique 35+). Match the *nearest* age bracket in the table to the source's stated range — e.g. a source bracket of `35-39 Years` maps to the `35+` row, `40-44 Years` maps to `40+`, etc. If a source's age bracket doesn't cleanly correspond to any table row, stop and report rather than guessing.
- **Two identically-labeled age brackets with no distinguishing qualifier** (e.g. two separate "Men's Bodybuilding | Masters 40+" lists on the same page, with different rosters) — do not resolve this with a heuristic (roster size, list order, or anything else) and do not generalize a fix from a single instance. One occurrence was resolved by asking the user directly, who judged from the specific page that the smaller group was mislabeled and was really Masters 50+ (2018 INBF World Championships, worldnaturalbb.com/results-2018-inbf-wnbf-worlds/) — that was a per-page call, not a rule. When this pattern recurs, stop, note the conflict, and give the source URL so it can be reviewed fresh each time.
- **Age + kg-weight qualifiers on Bodybuilding (OP/BB)** — some sources split a masters bodybuilding bracket into kg-based weight classes (e.g. "Master Men's Bodybuilding 40-44 Years, up to 80 kg / up to 90 kg / over 90 kg") rather than the descriptive names the existing Masters weight-code table uses (Light/Middle/Heavy, etc). Confirmed mapping (2022 European Amateur Championships): sort the kg classes ascending and assign them to the age bracket's Light/Middle/Heavy codes in order — e.g. three classes at 40-44 → `4L`, `4M`, `4H`; three classes at 45-49 → `45L`, `45M`, `45H`. If a bracket has only two kg classes, use the lightest and heaviest of the age bracket's weight codes (skip Middle) — e.g. two classes at 50-54 → `5L`, `5H`. If a bracket has a number of kg classes that doesn't map cleanly onto the available Light/Middle/Heavy (etc) codes for that age, stop and report rather than guessing.
- **Size qualifiers** — `Class A/B/...`, `up to X cm`, `X kg`, `Heavyweight/Middleweight/Lightweight`, etc. → first check whether an existing named table already covers this exact pattern (npcnewsonline's Ba-Bg height classes, the kg weight-class table, etc.). If not, use Step 3 below.
- **`OVERALL` / `Combined` / `Overall Winner`** → this header represents a division-level combined result, not another class. See Step 4.
- **`Open`** with no other qualifier → the division's base open class.

## Step 3 — Lettering un-tabled size classes

Some sources split a division into height/weight classes that don't match any pre-existing named table (e.g. a federation's own Figure height bands: `up to 158 cm`, `up to 163 cm`, `up to 168 cm`, `over 168 cm`). These still need letter codes — every division that takes classes has a reserved letter pool in `divisions-reference.md` (`Ba`–`Bg` for OP/BB, `Ca`–`Ch` for CL, `Pa`–`Ph` for PH, `Fa`–`Fh` for FI). Do not invent new codes outside these pools.

**Assign letters in ascending order of the class's numeric threshold** (cm, kg, lb — whatever unit the source uses), smallest first: `Xa` = smallest/lightest class, ascending from there. This is the same convention already used for `Pa`–`Pf` (Men's Physique height classes) and `Ba`–`Bg` (Bodybuilding height classes) — extend it to any division, including Figure, when a source presents un-tabled classes.

If the source's classes have no extractable numeric threshold and there's no other way to establish size order (e.g. bare "Class A"/"Class B" labels that don't match the npcnewsonline `class-a`/`class-b` convention, or ordering is genuinely ambiguous), **stop and report** — do not guess an order.

Apply the existing "single primary sub-division → collapse to outer code" rule (SKILL.md Phase 2) exactly as before — if a division turns out to have only one class after exclusions, write the bare division code instead of a letter code.

## Step 4 — Overall / combined entries

- Only write a `0 {Name}` overall entry when the source contains an **explicit combined/overall section for that division** — a heading containing "Overall", "Combined", "Overall Winner", or equivalent. **Never synthesize one from the winner of a class** (e.g. the winner of the tallest/heaviest class is not automatically the division overall winner — federations often don't crown one at all for a given division, or the actual comparison hasn't happened).
- `0 {Name}` lines never include a country code, even when the source provides one and even though placed-competitor lines do include it. This applies to every source (npcnewsonline, PDFs, NAC, etc.) — write `0 {Name}`, not `0 {Name} (CCC)`.

## Step 5 — Multi-person entries (pairs, teams)

Some sources include paired or team events (`Mixed-Pairs`, `Fit-Pairs`, couples/duo categories) where a single placing corresponds to two or more athletes competing together. **Exclude these divisions entirely** — the database has no way to represent a multi-athlete entry. Detect via:
- Division/class name containing "Pair(s)", "Team", "Duo", "Couple", or similar, or
- A placing line that visibly contains two distinct person names with no other separator (a strong sign an earlier pass mis-parsed a paired entry as one competitor).

## Step 6 — Unknown pattern → stop and report

If a division header or size/age qualifier doesn't match anything in Steps 1–3, and isn't in the exclusion list, **stop immediately and report it** with its context (division name, source file/page) — exactly the same discipline as npcnewsonline's "unknown sub-class slug" rule. Never fall back to a generic/outer code to keep moving — that silent-default behavior is what caused every division-code error found in the 2022 European Amateur Championships (female) extraction: unmapped Figure height/age classes were all dumped into the bare `FI`/`FM` codes instead of stopping for a mapping decision.

## Step 7 — Validate: one block per division

After mapping every division/class in the source, check the result: **for a given year, contest, and gender, a division code should appear only once.** If the same code ends up attached to two separate class lists in the same file, that's a signal something upstream was mapped too coarsely (a class that needed its own letter/age code got collapsed to the bare division code) — or, less commonly, that two blocks which are really the same class got split. Either way, resolve it before writing the file; don't write two `c {code}` blocks for the same code in one file. This is the cheapest catch-all check — a repeated code in the output is essentially never correct, regardless of source.

## Step 8 — Validate: placing values are plausible

For sources where each competitor's data is a fixed sequence of fields per row (name, bib/registration number, place, born year, bodyweight, round scores, country — typical of PDF-tabulated results), a placing value far larger than that division's roster size (and not 98/99) is almost never a real placing — it's the signature of a **bib number getting captured as the placing** because a wrapped (multi-line) athlete name shifted every field after it down by one line. The parser reads the "No" (bib) field as if it were "Place", and the athlete's true placing is dropped entirely.

Before writing the file, check each division/class: does the max placing roughly match the number of listed competitors (accounting for 98 ties)? A class of 5 with placings `1, 2, 3, 5, 238` is the tell — the `238` is a bib number, not a placing, and someone's real placing (here, `4`) is missing from the file. Re-check the source at that spot for a name that spans two lines and re-derive the correct placing rather than writing the bogus number. Confirmed via the 2018 Asian Amateur Championships (IFBB) AFBF-template PDF, where wrapped Gulf/Mongolian names caused this in 11 separate classes (`100kg`, `4L`, `60kg`, `65kg` ×2, `75kg`, `80kg`, `CBc`, `CBe`, `PJ` ×3, `Pd`, `Pe`) — every flagged athlete's bib number had been written as their placing, and their real placing never appeared. See `sources-reference.md`'s PDF section for the specific field layout and a parsing technique that avoids this.

## Applying this to a specific source

Per-source notes (URLs, fetch mechanics, User-Agent, confirmed terminology) still belong in `sources-reference.md`. This doc is the shared reasoning process; a source's entry in `sources-reference.md` should stay short and only capture what's genuinely specific to that source (how to fetch it, any confirmed base-division synonyms worth adding to Step 1's table, known data issues) rather than restating the recognition algorithm.
