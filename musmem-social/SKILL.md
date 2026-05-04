---
name: musmem-social
description: Use when looking up or validating social media handles for bodybuilding athletes in a given contest and year, to populate the social-media folder.
---

# MuscleMemory Social Media Lookup

Fetches athletes from a contest, checks the social-media folder for existing entries, and searches the web to find missing handles for the specified platform.

## Quick Reference

| Config | Key |
|--------|-----|
| `config/paths.json` | `social_media` — path to the social-media **folder** |
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

## Data Format

The social-media folder contains multiple JSON files. Each file name ends in `-male.json` or `-female.json`. Each file is a JSON array of records:

```json
[
  { "name": "Last, First", "ig": "handle" },
  { "name": "Banya, Parnelli", "fb": "patbanya1", "ig": "patbanya", "tw": "patbanya" }
]
```

| Field | Notes |
|-------|-------|
| `name` | `Last, First` format — matches `completeName` from API |
| `ig` | Instagram handle, no `@`, no URL |
| `fb` | Facebook handle |
| `tw` | Twitter/X handle |

Omit platform keys that are not known — do not store `null`.

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

### Step 2 — Load existing social media data

Path: `config/paths.json` → `social_media` (a folder)

1. List all `*-male.json` and `*-female.json` files in the folder, sorted alphabetically.
2. For each file, parse as a JSON array and merge records into an in-memory map keyed by `name`, split by gender (inferred from filename suffix).
3. On conflict (same name and same platform key in two files): last file wins (alphabetical order).

For each contest athlete, check `mergedMap[gender][completeName][platform_key]`. If the key exists → **skip** (even without `--validate`).

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

Write newly found handles to a **new file** in the social-media folder. Name it after the contest and year:

```
{social_media}/{contest-slug}-{year}-{gender}.json
```

Example: `~/workspace/musmem/data/social-media/2020-olympia-male.json`

The file contains only the handles found in this session as a JSON array. Do not append to existing files.

```python
with open(path, 'w', encoding='utf-8') as f:
    json.dump(records, f, ensure_ascii=False, indent=2)
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

Load and merge all files in the folder (as in Step 2 above). Gather all athletes in the merged male and female maps who have the platform key — regardless of which contest was specified. (Validation is global, not contest-scoped.)

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

Only modify files after explicit user confirmation. Write corrections to a new file named after the session (e.g., `corrections-YYYY-MM-DD-{gender}.json`) rather than editing existing files.

---

## File Format Rules

- JSON array, UTF-8
- Keys: `name` in `Last, First` format (matches `completeName` from API)
- Handle values: username only, no `@` prefix, no full URL
- Omit platform key entirely if not found — do not store `null`
- One file per session/batch — do not append to existing files

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Adding `"ig": null` for not-found athletes | Omit the key entirely |
| Editing an existing file instead of creating a new one | Always write a new file per session |
| Overwriting existing platform keys during lookup | New file only contains newly found handles — merging happens at read time |
| Storing full URL instead of handle | Extract handle only: `instagram.com/{handle}` → store `{handle}` |
| Searching `Last, First` on the web | Use `displayName` (First Last) for web searches |
| Auto-removing dead/suspect handles | Always report and confirm with user before modifying |
| Validating only contest athletes | Validation is global — check all entries across all files, not just the specified contest |
| Reading only one file | Always load and merge ALL files in the folder before checking for existing entries |
