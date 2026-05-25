# IFBB World Amateur Championships PDF Parsing Rules

Use these rules when extracting IFBB World Amateur Championships results PDFs into MuscleMemory `.dat` prelim files.

## PDF Extraction Tooling

- Use PyMuPDF for PDF text extraction.
- In Python, import it as `fitz`.
- The package used successfully in this workflow was PyMuPDF `1.27.2.3`.

## Output Files

- Write men to `data/prelim/YYYY-wac-male.dat`.
- Write women to `data/prelim/YYYY-wac-female.dat`.
- Men and women use the same division-code namespace; the file split is by sex, not by code family.

## Output Line Format

Use exactly:

```text
{family}, {given}; YYYY; World Amateur Championships - IFBB; {division-code}-{place}; c={country-code};
```

If the source country is blank or an IFBB flag entry, omit the country field:

```text
{family}, {given}; YYYY; World Amateur Championships - IFBB; {division-code}-{place};
```

Use single spaces only. Do not emit double spaces anywhere in output lines.

## Placings

- Do not include athletes whose place column is blank.
- Do not include athletes whose place is `DNC`.
- Record `DQ` or `DQ*` as place `99`.
- Strip asterisks from numeric places, for example `10*` becomes `10`.
- Avoid treating birth years as places. A numeric place should be one or two digits, unless explicitly handling `DQ` or `DNC`.
- For `OVERALL` sections, write only the 1st-place athlete to the output file, and record the placing as `0`.
- Do not include country fields on `OVERALL` lines, even when the source row has a country.

## Countries

- Use two-character internet / top-level-domain style country codes, uppercase, matching existing `.dat` conventions.
- Examples: `Korea` / `South Korea` -> `KO`, `Chinese Taipei` -> `TW`, `USA` -> `US`, `UAE` -> `AE`, `United Kingdom` -> `UK`.
- For `IFBB Flag`, `IFBB Flag C`, `IFBB Flag (B)`, or similar IFBB-flag country values, omit `c=`.
- Preserve rows with IFBB flag country values if they have a valid place.

## Names

- Source rows are generally `given family`; output as `family, given`.
- Join wrapped name lines before splitting names.
- For Chinese athletes, treat the first token as family name unless a known exception is identified.
- Preserve hyphens and apostrophe-free spelling as extracted unless there is a clear correction from context.
- Keep family-name particles with the family name when obvious, such as `Al`, `De`, `Del`, `El`, `Van`, `Von`, `Da`, `Dos`, `Di`, and `La`.

## Section Selection Workflow

1. Extract bold section headers from the PDF.
2. Present them as a numbered list.
3. Let the user remove unwanted sections.
4. Map the remaining sections to division codes using `docs/divisions-reference.md` and the rules below.
5. Parse only the selected sections into prelim files.

## Division Mapping Rules

- Overall rows use the parent division code, not `OV`.
- Overall rows should include only the winner, with place `0`.
  - `Men's Physique OVERALL` -> `PH`
  - `Men's Classic Bodybuilding OVERALL` -> `CB`
  - `Men's Bodybuilding OVERALL` -> `BB`
  - `Master Men's Bodybuilding OVERALL` -> `MA`
  - `Men's Classic Physique OVERALL` -> `CL`
  - `Master Men's Classic Physique OVERALL` -> `mc`
  - `Women's Bodyfitness OVERALL` -> `FI`
  - Junior rows are when age is under 24
  - Teen rows are when age is under 20
  - In the 2025 and 2021 WAC sessions, `Junior ... 15-23`, `16-23`, `16-20`, and `21-23` bodybuilding rows were mapped to `TE` when requested.
- Height-based classes map shortest to `a`, next to `b`, then `c`, etc.
  - Example: Physique height classes -> `Pa`, `Pb`, `Pc`, etc.
  - Example: Classic Bodybuilding height classes -> `CBa`, `CBb`, `CBc`, etc.
- For plain bodybuilding by height, use height codes if instructed.
  - In the 2025 WAC session: `Up To 170 cm` -> `SH`, `Over 170 cm` -> `TA`.
- Bodyfitness is treated as Figure.
  - `Women's Bodyfitness up to 158 cm` -> `Fa`
  - `Women's Bodyfitness up to 163 cm` -> `Fb`
  - `Women's Bodyfitness up to 168 cm` -> `Fc`
  - `Women's Bodyfitness over 168 cm` -> `Fd`
  - `Master Women's Bodyfitness ...` maps to Figure masters codes.
  - `Junior Women's Bodyfitness ...` maps to Figure teen/junior codes.
- Wheelchair bodybuilding maps to `WC`.
- Muscular Men's Physique Open maps to the parent physique code `MUP`.

## 2025 WAC Division Decisions

The final selected 2025 male section map was:

| Section | Code |
|---|---|
| Men's Classic Bodybuilding Up To 168 cm | `CBa` |
| Men's Classic Bodybuilding Up To 171 cm | `CBb` |
| Men's Classic Bodybuilding Up To 175 cm | `CBc` |
| Men's Classic Bodybuilding Up To 180 cm | `CBd` |
| Men's Classic Bodybuilding Over 180 cm | `CBe` |
| Men's Classic Bodybuilding OVERALL | `CB` |
| Master Men's Bodybuilding 40-49 Years, Open | `M4` |
| Master Men's Bodybuilding 50 Years & Over, Open | `M5` |
| Master Men's Bodybuilding OVERALL | `MA` |
| Junior Men's Bodybuilding 15-23 Years, Open | `TE` |
| Men's Bodybuilding by Height Up To 170 cm | `SH` |
| Men's Bodybuilding by Height Over 170 cm | `TA` |
| Men's Bodybuilding by Height OVERALL | `BB` |
| Wheelchair Men's Bodybuilding Open | `WC` |
| Junior Men's Physique 15-23 Years Up To 174 cm | `PJa` |
| Junior Men's Physique 15-23 Years Over 174 cm | `PJb` |
| Junior Men's Physique 15-23 OVERALL | `PJ` |
| Men's Physique Up To 170 cm | `Pa` |
| Men's Physique Up To 173 cm | `Pb` |
| Men's Physique Up To 176 cm | `Pc` |
| Men's Physique Up To 179 cm | `Pd` |
| Men's Physique Up To 182 cm | `Pe` |
| Men's Physique Over 182 cm | `Pf` |
| Men's Physique OVERALL | `PH` |
| Master Men's Physique 40 Years & Over, Open | `P4` |

## 2021 WAC Division Decisions

The final selected 2021 male section map was:

| Section | Code |
|---|---|
| Men's Classic Bodybuilding up to 168 cm | `CBa` |
| Men's Classic Bodybuilding up to 171 cm | `CBb` |
| Men's Classic Bodybuilding up to 175 cm | `CBc` |
| Men's Classic Bodybuilding up to 180 cm | `CBd` |
| Men's Classic Bodybuilding over 180 cm | `CBe` |
| Men's Classic Bodybuilding OVERALL | `CB` |
| Muscular Men's Physique Open | `MUP` |
| Men's Physique up to 170 cm | `Pa` |
| Men's Physique up to 173 cm | `Pb` |
| Men's Physique up to 176 cm | `Pc` |
| Men's Physique up to 179 cm | `Pd` |
| Men's Physique up to 182 cm | `Pe` |
| Men's Physique over 182 cm | `Pf` |
| Men's Physique OVERALL | `PH` |
| Men's Bodybuilding up to 65 kg | `65kg` |
| Men's Bodybuilding up to 70 kg | `70kg` |
| Men's Bodybuilding up to 75 kg | `75kg` |
| Men's Bodybuilding up to 80 kg | `80kg` |
| Men's Bodybuilding up to 85 kg | `85kg` |
| Men's Bodybuilding up to 90 kg | `90kg` |
| Men's Bodybuilding up to 95 kg | `95kg` |
| Men's Bodybuilding up to 100 kg | `100kg` |
| Men's Bodybuilding over 100 kg | `o100kg` |
| Men's Bodybuilding OVERALL | `BB` |
| Wheelchair Men's Bodybuilding Open | `WC` |
| Men's Classic Physique up to 168 cm | `Ca` |
| Men's Classic Physique up to 171 cm | `Cb` |
| Men's Classic Physique up to 175 cm | `Cc` |
| Men's Classic Physique up to 180 cm | `Cd` |
| Men's Classic Physique over 180 cm | `Ce` |
| Men's Classic Physique OVERALL | `CL` |
| Master Men's Classic Bodybuilding 40-44 Years, Open | `CB4` |
| Master Men's Classic Bodybuilding 45-49 Years, Open | `CB4` |
| Master Men's Classic Bodybuilding 50 Years & over, Open | `CB5` |
| Master Men's Classic Bodybuilding OVERALL | `CBM` |
| Master Men's Bodybuilding 40-44 Years, up to 80 kg | `4L` |
| Master Men's Bodybuilding 40-44 Years, up to 90 kg | `4M` |
| Master Men's Bodybuilding 40-44 Years, over 90 kg | `4H` |
| Master Men's Bodybuilding 45-49 Years, up to 70 kg | `45L` |
| Master Men's Bodybuilding 45-49 Years, up to 80 kg | `45M` |
| Master Men's Bodybuilding 45-49 Years, up to 90 kg | `45l` |
| Master Men's Bodybuilding 45-49 Years, over 90 kg | `45H` |
| Master Men's Bodybuilding 50-54 Years, up to 80 kg | `5L` |
| Master Men's Bodybuilding 50-54 Years, over 80 kg | `5H` |
| Master Men's Bodybuilding 55-59 Years, up to 75 kg | `55L` |
| Master Men's Bodybuilding 55-59 Years, over 75 kg | `55H` |
| Master Men's Bodybuilding 60 Years & over, Open | `M6` |
| Master Men's Bodybuilding OVERALL | `MA` |
| Master Men's Physique 40-44 Years, Open | `P4` |
| Master Men's Physique 45-49 Years, Open | `P45` |
| Master Men's Physique 50 Years & over, Open | `P5` |
| Master Men's Physique OVERALL | `MP` |
| Master Men's Classic Physique 40-44 Years, Open | `c4` |
| Master Men's Classic Physique 45-49 Years, Open | `c45` |
| Master Men's Classic Physique 50 Years & over, Open | `c5` |
| Master Men's Classic Physique OVERALL | `mc` |
| Junior Men's Classic Bodybuilding 16-23 Years, Open | `CBT` |
| Junior Men's Physique 16-20 Years, Open | `PT` |
| Junior Men's Physique 21-23 Years, up to 174 cm | `PJa` |
| Junior Men's Physique 21-23 Years, up to 178 cm | `PJb` |
| Junior Men's Physique 21-23 Years, over 178 cm | `PJc` |
| Junior Men's Physique OVERALL | `PT` |
| Junior Men's Classic Physique 16-23 Years, Open | `ct` |
| Junior Men's Bodybuilding 16-20 Years, open | `TE` |
| Junior Men's Bodybuilding 21-23 Years, open | `TE` |
| Junior Men's Bodybuilding OVERALL | `TE` |

The final selected 2021 female section map was:

| Section | Code |
|---|---|
| Women's Bodyfitness up to 158 cm | `Fa` |
| Women's Bodyfitness up to 163 cm | `Fb` |
| Women's Bodyfitness up to 168 cm | `Fc` |
| Women's Bodyfitness over 168 cm | `Fd` |
| Women's Bodyfitness OVERALL | `FI` |
| Master Women's Bodyfitness 35-39 Years, Open | `f3` |
| Master Women's Bodyfitness 40-44 Years, Open | `F4` |
| Master Women's Bodyfitness 45 Years & over, Open | `f4` |
| Master Women's Bodyfitness OVERALL | `FM` |
| Master Women's Physique 35 Years & over | `P35` |
| Junior Women's Bodyfitness 16-20 Years, Open | `FT` |
| Junior Women's Bodyfitness 21-23 Years, Open | `FJ` |
| Junior Women's Bodyfitness OVERALL | `FJ` |

## Validation Checklist

After writing files, validate:

- line count with `wc -l`
- no `DNC`
- no leaked headers such as `COUNTRY`, `NAME`, `RD1`, `Score`
- no `IFBB Flag` text in output
- no suspicious birth years used as places, such as `-1995`
- no double spaces
- no `c=` country field on overall lines such as `BB-0`, `CB-0`, `FI-0`, `PJ-0`, or similar
- all lines match the `.dat` format
- `DQ` rows, if present, are written as `-99`
