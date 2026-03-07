---
name: musmem-social
description: Use when looking up or validating social media handles for bodybuilding athletes in a given contest and year, to populate social_media.json.
---

# MuscleMemory Social Media Lookup

Fetches athletes from a contest, checks `social_media.json` for existing entries, and searches the web to find missing handles for the specified platform.

## Quick Reference

| Config | Key |
|--------|-----|
| `config/paths.json` | `social_media` — path to JSON file |
| `config/apis.json` | `endpoints.contest_event`, `musclememory_net`, `user_agent_api` |

**Platform abbreviations:**

| Platform | Key |
|----------|-----|
| instagram | `ig` |
| facebook | `fb` |
| twitter | `tw` |

## Input

- Contest name + year — e.g., `"Olympia - IFBB, 2020"`
- Platform — e.g., `instagram`
- Optional flag: `--validate` — validate existing handles instead of (or in addition to) finding new ones

---

## Mode 1: Lookup (default)

### Step 1 — Fetch contest athletes

```
GET {musclememory_net}{endpoints.contest_event}
→ /api/contest?name={contest}&year={year}
User-Agent: {user_agent_api}
```

Response: `data.results[]` — each entry has `completeName` (`Last, First`) and `gender` (`"male"` or `"female"`).

**Deduplicate** by `completeName` before proceeding.

### Step 2 — Load social_media.json

Path: `config/paths.json` → `social_media`

```json
{
  "male":   { "Last, First": { "ig": "handle", "fb": "handle", "tw": "handle" } },
  "female": { "Last, First": { "ig": "handle" } }
}
```

For each athlete, check `data[gender][completeName][platform_key]`. If the key exists → **skip** (even if `--validate` is not set — lookup mode only finds missing entries).

### Step 3 — Search for handle

For each athlete missing the platform key, search the web:

**Query:** `"{displayName}" bodybuilder instagram` (or relevant platform name; use First Last order)

A result is sufficient if it returns an Instagram page clearly belonging to this athlete. Signs it's the right person:
- Bio or posts reference bodybuilding / competing / IFBB / NPC
- Name matches (allowing for common abbreviations or nicknames)
- Contest history aligns with what's in MuscleMemory

**Do not add if:**
- No Instagram page found in results
- Page found but identity is unclear (generic name, no bodybuilding content)
- Multiple plausible accounts with no clear match

Extract the handle from the URL or page (`instagram.com/{handle}`) — store without `@`.

### Step 4 — Write results

Write directly to `data[gender][completeName]`, adding only the new platform key. Do not overwrite existing keys for other platforms.

Save `social_media.json` after each new entry.

```python
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

### Step 5 — Report

| Category | What to show |
|----------|-------------|
| Already in file | Count only |
| Added | `Last, First → @handle` |
| Searched, not found | Names only |

---

## Mode 2: Validate (`--validate`)

Checks existing handles for the specified platform. Can be run alone or after a lookup pass.

### Step 1 — Collect handles to validate

Gather all athletes in `data["male"]` and `data["female"]` who have the platform key — regardless of which contest was specified. (Validation is global, not contest-scoped.)

### Step 2 — Check each handle

For each handle, fetch the platform profile page and check two things:

**Existence:** Does the account still exist?
- Account not found / page 404 / "user not found" → flag as **dead**

**Identity:** Does the account still belong to this athlete?
- Bio or recent posts reference bodybuilding / competing / their name
- If account exists but shows no bodybuilding content or a different identity → flag as **suspect**

### Step 3 — Report and prompt

Do not automatically remove or modify any entries. Present findings to the user:

```
Dead handles (account gone):
  Doe, John — ig: johndoe_bb

Suspect handles (identity unclear):
  Smith, Jane — ig: janesmith — bio: "🌸 lifestyle blogger"

Ask: Remove dead handles? Review suspects individually?
```

Only modify `social_media.json` after explicit user confirmation.

---

## File Format

- JSON, UTF-8
- Keys: `completeName` from API (`Last, First` format)
- Handle values: username only, no `@` prefix, no full URL
- Omit platform key entirely if not found — do not store `null`

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Adding `"ig": null` for not-found athletes | Omit the key entirely — absence means not yet found or not found |
| Overwriting existing platform keys during lookup | Only add missing keys — never overwrite |
| Storing full URL instead of handle | Extract handle only: `instagram.com/{handle}` → store `{handle}` |
| Searching `Last, First` on the web | Use `displayName` (First Last) for web searches |
| Auto-removing dead/suspect handles | Always report and confirm with user before modifying existing entries |
| Validating only contest athletes | Validation is global — check all entries in the file, not just the specified contest |
