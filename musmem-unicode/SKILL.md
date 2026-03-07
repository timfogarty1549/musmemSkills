---
name: musmem-unicode
description: Use when looking up native-language names (non-Latin or extended-Latin scripts) for bodybuilding athletes in a given contest and year, to populate athletes_localized.json.
---

# MuscleMemory Unicode — Native Name Lookup

Fetches athletes from a contest, checks `athletes_localized.json` for existing entries, and searches the web to find and add missing native-script names.

## Quick Reference

| Config | Key |
|--------|-----|
| `config/paths.json` | `athletes_localized` — path to JSON file |
| `config/apis.json` | `endpoints.contest_event`, `musclememory_net`, `user_agent_api` |

## Input

Contest name + year — e.g., `"Japan Pro - IFBB, 2019"`

---

## Workflow

### Step 1 — Fetch contest athletes

```
GET {musclememory_net}{endpoints.contest_event}
→ /api/contest?name={contest}&year={year}
User-Agent: {user_agent_api}
```

Response: `data.results[]` — each entry has `completeName` (`Last, First`) and `gender` (`"male"` or `"female"`).

**Deduplicate** by `completeName` before proceeding — athletes appear once per division placing.

### Step 2 — Load athletes_localized.json

Path: `config/paths.json` → `athletes_localized`

```json
{
  "male":    { "Last, First": "native script name" },
  "female":  { "Last, First": "native script name" },
  "unknown": { "Last, First": "native script name" }
}
```

For each athlete, check `data[gender][completeName]` and `data["unknown"][completeName]`. If found in either → **skip**.

### Step 3 — Search for native name

For each unmatched athlete, search the web:

**Query:** `"{displayName}" bodybuilding` (First Last order — more natural for web search)

For Korean athletes also try: `"{displayName}" 보디빌딩`

**Good sources to check (in order):**
- NamuWiki (namu.wiki) — thorough Korean athlete profiles
- Korean news sites (newsfreezone.co.kr, etc.)
- Instagram — many Korean/Japanese pros show native name in bio
- Wikipedia in the athlete's likely native language

Scan results for characters above U+007F. If found:
- Confirm the result refers to this athlete (same sport, same contest if possible)
- Extract the native-script name

**Only add if a source explicitly confirms the native-script name for this specific athlete.** Acceptable sources:
- Instagram profile showing their native-script name in bio or posts
- Native-language article about them as a bodybuilder (Korean news, NamuWiki, Japanese bodybuilding site, etc.)
- Official federation page in the native language

**Do not add if:**
- No confirming source found — even if the romanization is unambiguous, do not infer the native-script name without a source
- No non-ASCII characters found in results
- Match is ambiguous (common name, multiple possible athletes)
- Only minor accented Latin (e.g., a single `é` in an otherwise ASCII name) — use judgment; `Tomáš Bureš` is worth keeping, a stray accent is not

### Step 4 — Write results

Gender is known from the contest API response — write directly to `data[gender]`, **never to `unknown`**.

Save `athletes_localized.json` after each new entry.

```python
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

### Step 5 — Report

| Category | What to show |
|----------|-------------|
| Already in file | Count only |
| Added | `Last, First → native name` |
| Searched, not found | Names only |

---

## File Format

- UTF-8, actual Unicode characters — **never HTML entities**
- Keys: `completeName` from API (`Last, First` format)
- Values: native-script string
- `unknown` section is for legacy entries only; new entries always go to `male` or `female`

## Supporting Scripts

| Script | Purpose |
|--------|---------|
| `python/convert_unicode.py` | One-time: converts legacy `unicode.txt` → `athletes_localized.json` |
| `python/resolve_gender.py` | Resolves `unknown` entries via MuscleMemory search API |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Writing HTML entities (`&#nnnn;`) | Use `ensure_ascii=False` — write actual UTF-8 characters |
| Writing to `unknown` for contest athletes | Gender is known from API — write to `male` or `female` directly |
| Not deduplicating | API returns one row per placing — deduplicate by `completeName` first |
| Searching `Last, First` on the web | Use `displayName` (First Last) for web searches |
| Inferring native name from romanization alone | Always require a confirming source (Instagram, native-language article, federation page) — never infer from romanization rules alone |
| Skipping Korean-language search terms | Adding 보디빌딩 to the query surfaces Korean sources that English-only searches miss |
