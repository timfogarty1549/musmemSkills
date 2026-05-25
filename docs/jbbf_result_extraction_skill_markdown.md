# JBBF Japanese Nationals Result Extraction Skill

Goal: Collect and normalize JBBF Japanese Nationals bodybuilding contest results from 2013 onward for import into musclememory.org.

## Contest Target

Use the contest title:

```text
t Japan Nationals - JBBF
```

The target event is usually listed in Japanese as:

- 日本ボディビル選手権大会
- 日本男子ボディビル選手権
- 日本女子ボディビル選手権
- 日本ジュニアボディビル選手権
- 日本マスターズボディビル選手権

JBBF may not call it “Japan Nationals” in English. Treat “日本選手権” / “日本ボディビル選手権” as the relevant national championship.

## Source Priority

Prefer sources in this order:

1. Official JBBF PDFs hosted on jbbf.jp
2. Official or archived JBBF result indexes, especially:
   - bodybuilding-fitness.jp/Result/Japan.html
3. bodybuilding-report.jp result pages
4. Other sources only for verification, not primary import

Useful search patterns:

```text
site:jbbf.jp 日本選手権 filetype:pdf
site:jbbf.jp 日本男子ボディビル選手権 結果 pdf
site:jbbf.jp 日本ボディビル選手権大会 結果
site:bodybuilding-report.jp zennihon nihondanshi
```

Typical JBBF PDF URL pattern:

```text
https://www.jbbf.jp/Taikai/YYYY_Taikai/YYMMDD_Nihon/YYYY_Nihon_Result.pdf
```

Examples:

```text
https://www.jbbf.jp/Taikai/2014_Taikai/141005_Nihon/2014_Nihon_Result.pdf
https://www.jbbf.jp/Taikai/2015_Taikai/151012_Nihon/2015_Nihon_Result.pdf
https://www.jbbf.jp/Taikai/2016_Taikai/161002_Nihon/2016_Nihon_Result.pdf
```

## Output Format

Use this plain text format:

```text
y {year}
t Japan Nationals - JBBF

c {English class or division}
1 {name}
2 {name}
3 {name}

c {next English class or division}
1 {name}
2 {name}
```

Do not use MuscleMemory internal class codes. Use readable English descriptions only.

Examples:

```text
c Men Bodybuilding Open
c Women Bodybuilding Open
c Junior Bodybuilding Open
c Masters Bodybuilding 40+
c Men Bodybuilding -75kg
c Men Physique -176cm
c Women Bodyfitness +163cm
c Classic Physique Open
```

## Name Handling

Japanese-language result sheets normally list names in family-name-first order.

Preserve East Asian name order.

Do not add commas.

Example:

```text
鈴木 雅
```

becomes:

```text
Suzuki Masashi
```

not:

```text
Masashi Suzuki
Suzuki, Masashi
```

For Japanese names, transliterate to Latin characters while preserving the original order.

When uncertain about a reading, do not guess silently. Mark it for review or verify from another source.

## Extraction Rules

Include every category and every placing available from the source, not just finalists or winners.

Use official placing order from the PDF/table.

Do not fabricate missing lower placings.

Do not extrapolate categories from other years.

If OCR is uncertain, exclude the row or mark it clearly for review rather than importing questionable data.

## Translation Rules

Translate class names into English.

Common terms:

```text
男子 = Men
女子 = Women
ボディビル = Bodybuilding
ジュニア = Junior
マスターズ = Masters
メンズフィジーク = Men Physique
クラシックフィジーク = Classic Physique
ボディフィットネス = Bodyfitness
フィットネス = Fitness
級 = Class
以下 = and under / -
超 = over / +
```

Normalize weight and height classes as:

```text
-70kg
+85kg
-172cm
+176cm
```

## Quality Rule

This data is for a permanent contest database. Accuracy is more important than speed.

Only output import-ready blocks when the source has been directly checked.
