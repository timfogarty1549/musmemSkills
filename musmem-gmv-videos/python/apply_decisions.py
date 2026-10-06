"""
Apply a batch of match/skip decisions (made by Claude after reviewing
gmv_videos_suggestions.json) to gmv_videos.json and gmv_videos_skipped.json,
and remove the processed ids from gmv_videos_pending.json.

Input: a JSON file (path given as argv[1]) containing a list of decisions:

[
  {"action": "match", "id": "dr3mOe57-KU",
   "title": "2000 IFBB Toronto Pro International from GMV Bodybuilding",
   "contest": "Toronto Pro - IFBB", "year": "2000"},
  {"action": "skip", "id": "xxxxxxxxxxx",
   "title": "Muscletime Titans Vol. 9 - Gary Strydom - Ageless",
   "reason": "highlight reel, not tied to a specific contest"}
]

Usage: python3 apply_decisions.py /tmp/decisions.json
"""
import json
import os
import sys

SKILL_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MUSMEM_DATA_DIR = os.path.expanduser("~/workspace/musmem/data")

SKIPPED_FILE = os.path.join(SKILL_DATA_DIR, "gmv_videos_skipped.json")
PENDING_FILE = os.path.join(SKILL_DATA_DIR, "gmv_videos_pending.json")
OUTPUT_FILE = os.path.join(MUSMEM_DATA_DIR, "gmv_videos.json")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 apply_decisions.py <decisions.json>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        decisions = json.load(f)

    output_data = load_json(OUTPUT_FILE, [])
    skipped = load_json(SKIPPED_FILE, [])
    pending = load_json(PENDING_FILE, [])

    by_contest = {entry["contest"]: entry for entry in output_data}
    skipped_ids = {s["id"] for s in skipped}

    matched_count = 0
    dup_count = 0
    skip_count = 0
    processed_ids = set()

    for d in decisions:
        vid = d["id"]
        processed_ids.add(vid)

        if d["action"] == "match":
            contest, year = d["contest"], str(d["year"])
            entry = by_contest.setdefault(contest, {"contest": contest, "years": {}})
            year_videos = entry["years"].setdefault(year, [])
            if any(v["id"] == vid for v in year_videos):
                dup_count += 1
                continue
            year_videos.append({"id": vid, "title": d["title"]})
            matched_count += 1

        elif d["action"] == "skip":
            if vid not in skipped_ids:
                skipped.append({"id": vid, "title": d["title"], "reason": d.get("reason", "")})
                skipped_ids.add(vid)
            skip_count += 1

        else:
            print(f"WARNING: unknown action {d['action']!r} for id {vid}", file=sys.stderr)

    output_data = []
    for contest in sorted(by_contest.keys()):
        entry = by_contest[contest]
        years_sorted = {}
        for year in sorted(entry["years"].keys(), key=int):
            years_sorted[year] = entry["years"][year]
        output_data.append({"contest": contest, "years": years_sorted})

    pending = [p for p in pending if p["id"] not in processed_ids]

    os.makedirs(SKILL_DATA_DIR, exist_ok=True)
    os.makedirs(MUSMEM_DATA_DIR, exist_ok=True)
    save_json(OUTPUT_FILE, output_data)
    save_json(SKIPPED_FILE, skipped)
    save_json(PENDING_FILE, pending)

    print(f"Matched : {matched_count} (skipped {dup_count} already-present duplicates)")
    print(f"Skipped : {skip_count}")
    print(f"Remaining pending: {len(pending)}")
    print(f"Wrote {OUTPUT_FILE}, {SKIPPED_FILE}, {PENDING_FILE}")


if __name__ == "__main__":
    main()
