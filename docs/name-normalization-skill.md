# Name Normalization Skill

Use this when converting athlete-entry text files into normalized name formats.

## Goal

Transform athlete lines while preserving all non-athlete lines and the original line order.

Athlete lines look like:

```text
1 Anna Vitkalova
2 Shu Xiaofan
```

Non-athlete lines look like:

```text
y 2021
t Event Name
c Fb
----
```

## Output Rules

### 1. Preserve file structure

- Keep every line in the same order.
- Keep non-athlete lines unchanged.
- Only transform athlete-entry lines.

### 2. Western-style names

Convert athlete lines to:

```text
n Last, First
```

Examples:

```text
2 Anna Vitkalova -> 2 Vitkalova, Anna
1 Bodnaryuk Kristina Andreevna -> 1 Bodnaryuk, Kristina Andreevna
3 Irene Donet Garcia -> 3 Donet Garcia, Irene
```

Guideline:

- Determine the most likely family name rather than blindly trusting source order.
- NPC/IFBB-style source files often westernize or inconsistently order names.
- For Spanish and similar naming conventions, preserve multi-part surnames when likely.
- For Arabic, Portuguese, and similar names, keep surname particles attached when they most likely belong with the surname.

### 3. East Asian names

For Chinese, Korean, and similar East Asian names, do not convert to `Last, First`.

Instead, normalize them into:

```text
@n Family Given
```

Examples:

```text
5 Shu Xiaofan -> @5 Shu Xiaofan
3 Xinkai Zhou -> @3 Zhou Xinkai
7 Zi Bin Chua -> @7 Chua Zi Bin
3 Boyang Chen -> @3 Chen Boyang
2 Han Ming Tan -> @2 Tan Han Ming
```

Important:

- The `@` prefix marks that the line is using East Asian family-name-first order.
- Do not simply preserve source order.
- Infer the most likely family name first, then rewrite as `@n Family Given`.
- East Asian surname alone is not enough. First decide which token is the family name, then decide whether the output should be East Asian `@n Family Given` or western `n Last, First`.

### 4. How to infer East Asian family names

Use cultural likelihood, not just token position.

Heuristics:

- Chinese and Korean family names are very often one syllable / one token.
- Given names may be one token or two syllables merged into one word.
- Romanized Cantonese, Chinese diaspora, Singaporean, and Malaysian Chinese names may appear in westernized order in the source.
- A western given name with an East Asian surname does not automatically mean East Asian ordering.
- In Korea-specific files, East Asian ordering is especially likely, but still infer the family name rather than blindly trusting token order.

Examples:

```text
David Cai -> 3 Cai, David
Xinkai Zhou -> @3 Zhou Xinkai
Boyang Chen -> @3 Chen Boyang
Siu Nam Chan -> @3 Chan Siu Nam
Han Ming Tan -> @2 Tan Han Ming
```

### 5. Source skepticism

- Assume the source ordering may be wrong.
- Infer the most likely family name from naming convention, language, and cultural usage.
- NPC/IFBB source files are especially unreliable for name order and may westernize names inconsistently.
- Separate these two questions:
  - Which part is the family name?
  - Should the output be western `Last, First` or East Asian `@Family Given`?

### 6. Ambiguity rule

When uncertain:

- Make the best-supported guess.
- Do not invent missing name parts.
- Prefer preserving the original tokens while reordering only when the family-name inference is reasonably strong.
- If a line is malformed or duplicated, preserve the text as much as possible.

## Processing Workflow

1. Read the file.
2. Keep all non-athlete lines unchanged.
3. For each athlete line:
   - identify the rank number
   - determine the most likely family name
   - if the athlete is most likely using East Asian naming convention, write `@n Family Given`
   - otherwise write `n Last, First`
4. Preserve original file order.
5. If writing a derived copy, write it beside the original and append `-1` to the full filename.

## Examples

Input:

```text
y 2024
t Example Show
c Fa
1 Anna Vitkalova
2 Xinkai Zhou
3 David Cai
----
```

Output:

```text
y 2024
t Example Show
c Fa
1 Vitkalova, Anna
@2 Zhou Xinkai
3 Cai, David
----
```

## Default Assumptions

- Western and European names: use `n Last, First`
- Russian names with patronymics: `n Surname, Given Patronymic`
- Spanish names: preserve likely two-part surnames
- East Asian names: `@n Family Given`
- Western given name + East Asian surname alone is not enough for `@`
- Korean and Chinese given names may appear as one merged romanized word

## Ranking Notes

- Preserve ranking numbers exactly as they appear in the source unless the user explicitly asks for rank correction.
- `98` is valid and usually means unplaced / unranked.
- Ties are valid.
- Sequences like `1, 2, 3, 4, 4, 6, 7, 98, 98` are normal and must not be treated as errors.

## Filename Convention

If creating normalized copies rather than replacing originals:

```text
original.txt -> original.txt-1
```

## Final Check

Before finishing:

- confirm that non-athlete lines are unchanged
- confirm athlete lines were transformed consistently
- confirm East Asian `@` lines are normalized into likely family-name-first order
- confirm westernized East Asian diaspora names are not incorrectly left in source order

## Iterative Cleanup Workflow

Use this when the files have already been normalized once and you are doing cross-file cleanup so the same athlete appears under one canonical name everywhere.

Goal:

- unify each athlete's full contest history under one canonical name
- prefer cross-file consistency over preserving a mistaken source ordering
- use cultural naming judgment to decide which form is most likely correct

Workflow:

1. Scan the current live files for inconsistent name clusters.
2. Group likely duplicates by token overlap, reversed order, punctuation drift, casing drift, and surname-particle drift.
3. Propose only a reasonably safe batch of changes.
4. Get approval on the proposed batch when the cleanup is judgment-heavy.
5. Apply the approved mappings across all live normalized files.
6. Verify that the old forms are gone from the live files.
7. Repeat from the current live scan.

Important:

- Trust the current live scan over memory.
- If a conflict appears again in the live scan, it is still unresolved, even if you thought it was fixed earlier.
- Do not say a cluster is already handled if the current files still contain both forms.

Canonical output rules for iterative cleanup:

- East Asian names should converge on `@n Family Given`.
- Western and non-East-Asian names should converge on `n Last, First`.
- If the same athlete appears in multiple orders, choose one canonical form and use it everywhere.
- For database/history purposes, consistency across all appearances matters more than preserving every source file's exact order.

Common signals:

- `Kim`, `Lee`, and `Park` are very often Korean family names.
- Other common East Asian surnames such as `Choi`, `Jung`, `Kang`, `Seo`, `Ahn`, `Yoon`, `Chen`, `Wang`, `Liu`, `Yang`, `Zhou`, `Chan`, `Chua`, `Tan`, `Leung`, and `Ng` should be treated with similar suspicion when order varies.
- Particles such as `Al`, `De`, `Da`, `Di`, `Du`, `Van`, and `Von` often belong with the family name.
- When the user has a style preference for capitalization of particles, apply it consistently across all files.

Current working helper:

- iterative cleanup in this project has been using `/Users/timfogarty/workspace/node/musmem/tmp_apply_agreed_name_fixes.py`
- that helper should be treated as disposable working state, not the source of truth
- the durable source of truth is this skill plus the user's explicit approvals on canonical forms
