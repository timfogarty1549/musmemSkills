---
name: musmem-gmv-videos
description: Use when linking MuscleMemory contests to archival footage on the GMV Bodybuilding YouTube channel (youtube.com/@gmvbodybuilding), or refreshing gmv_videos.json with videos uploaded since the last run.
---

# GMV Bodybuilding Video Linker

Scrapes the video list from `youtube.com/@gmvbodybuilding/videos` and matches each
video to a MuscleMemory contest name + year, writing results to
`~/workspace/musmem/data/gmv_videos.json` — the **only** file this skill writes
outside its own folder. Every intermediate/cache file lives in this skill's own
`data/` directory instead. Designed to be re-run every few weeks to pick up
newly uploaded videos — later runs only process videos not already matched or
skipped.

**Requires yt-dlp:** `brew install yt-dlp` (one-time setup, if not already installed).

**Matching uses the local musmem node server, not musclememory.net.** The public
musclememory.net API now rejects unsigned requests
(`{"success":false,"error":"Invalid or missing request signature"}` on a plain GET).
The local dev server at `~/workspace/node/musmem` serves the same data (it reads
the same dat files) and does **not** require a signature when called as
`localhost:3000` — `suggest_match.py` calls `ensure_local_server.py` automatically,
which starts the server (`npm run dev` in that directory) if it isn't already
running on port 3000, and waits for it to come up before continuing.

## Workflow

### Step 1 — Fetch the channel's video list

```
python3 python/fetch_channel_videos.py
```

Runs yt-dlp against the channel in flat-playlist mode (no video downloads, just id+title). Overwrites `data/gmv_videos_raw.json` with the full current list (~750+ videos as of 2026; takes 1-2 minutes).

### Step 2 — Find videos not yet processed

```
python3 python/find_pending.py
```

Diffs the raw list against ids already present in `~/workspace/musmem/data/gmv_videos.json` (matched) and `data/gmv_videos_skipped.json` (deliberately not matched). Writes the remainder to `data/gmv_videos_pending.json`. On the very first run this is the full ~750 videos; on later runs it should be a small handful of new uploads.

### Step 3 — Generate match candidates

```
python3 python/suggest_match.py
```

Ensures the local server is running (starts it if not), then fetches the full contest list from `http://localhost:3000/api/contests`. For each pending video, parses the title (leading year, org token, remaining show name), then scores every known contest base-name using weighted token overlap plus a substring-containment bonus (plain character-similarity badly over-ranks generic words like "Pro" or "International", so this is not a simple fuzzy-match — see the module docstring). Year spans for the top candidates come from `/api/contest/years`. Writes `data/gmv_videos_suggestions.json`: each entry has the parsed guesses and up to 8 ranked candidate contests with their DB year spans.

**This is a hint file, not an answer key.** Scores are informational; always read the actual video title before deciding. A `year_in_db: false` does NOT mean don't match — it usually just means MuscleMemory has no results entered for that contest/year yet. Match on contest identity, not on whether the year already has data (e.g. `dr3mOe57-KU`, "2000 IFBB Toronto Pro International", correctly matches `Toronto Pro - IFBB` for year 2000 even though the DB's earliest Toronto Pro year on file might differ).

### Step 4 — Review and apply decisions

Read `gmv_videos_pending.json` and `gmv_videos_suggestions.json` together. For each video, decide:

- **Match** — the video documents a specific MuscleMemory contest/year. Use the top-scoring candidate if it's clearly right; otherwise use judgment (web search for the contest name/org if the local candidates all look wrong) to find the correct canonical `Contest Name - ORG` string. Contest name format matches the rest of MuscleMemory: no leading org prefix, org appended after ` - ` (same convention as musmem-contests and contest_locations.json).
- **Skip** — the video isn't tied to a single contest result (highlight reels, athlete interviews/profiles, "Muscletime" compilation videos, training footage), or documents a federation/contest MuscleMemory doesn't track (e.g. UKBFF, BNBF, ANB, EFBB, ICN are common on this channel but absent from the local server's contest list — confirm absence before skipping for this reason, a federation may simply be under a name you haven't tried).

Process sequentially, all pending videos in one autonomous pass — no need to ask before each decision. Batch the results into a single JSON file, e.g. `/tmp/gmv_decisions.json`:

```json
[
  {"action": "match", "id": "dr3mOe57-KU",
   "title": "2000 IFBB Toronto Pro International from GMV Bodybuilding",
   "contest": "Toronto Pro - IFBB", "year": "2000"},
  {"action": "skip", "id": "xxxxxxxxxxx",
   "title": "Muscletime Titans Vol. 9 - Gary Strydom - Ageless",
   "reason": "highlight reel, not tied to a specific contest"}
]
```

Then apply it:

```
python3 python/apply_decisions.py /tmp/gmv_decisions.json
```

This merges matches into `~/workspace/musmem/data/gmv_videos.json` (deduping by video id), appends skips to `data/gmv_videos_skipped.json`, and removes processed ids from `data/gmv_videos_pending.json`. Safe to call multiple times with smaller batches if reviewing in chunks.

### Step 5 — Report

Summarize: videos fetched, newly matched (with contest names), newly skipped (with reasons), and any left pending (e.g. ambiguous titles needing the user's input).

## JSON Schema

File: `~/workspace/musmem/data/gmv_videos.json`

```json
[
  {
    "contest": "Toronto Pro - IFBB",
    "years": {
      "2000": [
        { "id": "dr3mOe57-KU", "title": "2000 IFBB Toronto Pro International from GMV Bodybuilding" }
      ]
    }
  }
]
```

- A contest/year can have multiple videos (e.g. separate prejudging/finals uploads) — `years[year]` is always an array.
- `id` is the YouTube video id (`https://www.youtube.com/watch?v={id}`).
- `title` is the video's exact YouTube title at scrape time.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Trusting the top suggestion score blindly | Always read the actual title — the suggester is a fuzzy hint, not ground truth |
| Refusing to match because the year isn't in `db_years_span` | Match on contest identity; the year comes from the video, not from existing DB coverage |
| Re-running `fetch_channel_videos.py` and reprocessing everything each time | `find_pending.py` is what limits work to new videos — always run it before `suggest_match.py` |
| Skipping a UK-federation video without checking | Some (UKBFF, BNBF, etc.) really aren't tracked in MuscleMemory, but verify against the local server's contest list rather than assuming |
| Calling musclememory.net API endpoints for contest names | They require a signed request now and will fail; `suggest_match.py` uses the local server on port 3000 instead, which doesn't need one |
| Writing `years` as an object instead of an array | Format differs from `contest_locations.json` — a contest/year here holds a list of video objects |
| Writing any file other than `gmv_videos.json` into `~/workspace/musmem/data/` | All caches (`gmv_videos_raw.json`, `_pending.json`, `_suggestions.json`, `_skipped.json`) belong in this skill's own `data/` folder |
