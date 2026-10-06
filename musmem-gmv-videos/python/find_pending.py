"""
Diff the raw channel video list against videos already recorded in
gmv_videos.json (matched) and gmv_videos_skipped.json (deliberately
not matched), producing the list of videos that still need review.

Usage: python3 find_pending.py
"""
import json
import os

SKILL_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MUSMEM_DATA_DIR = os.path.expanduser("~/workspace/musmem/data")

RAW_FILE = os.path.join(SKILL_DATA_DIR, "gmv_videos_raw.json")
SKIPPED_FILE = os.path.join(SKILL_DATA_DIR, "gmv_videos_skipped.json")
PENDING_FILE = os.path.join(SKILL_DATA_DIR, "gmv_videos_pending.json")
OUTPUT_FILE = os.path.join(MUSMEM_DATA_DIR, "gmv_videos.json")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def known_matched_ids(output_data):
    ids = set()
    for entry in output_data:
        for year_videos in entry.get("years", {}).values():
            for v in year_videos:
                ids.add(v["id"])
    return ids


def main():
    raw = load_json(RAW_FILE, [])
    if not raw:
        print(f"No raw videos found at {RAW_FILE} — run fetch_channel_videos.py first.")
        return

    output_data = load_json(OUTPUT_FILE, [])
    skipped = load_json(SKIPPED_FILE, [])

    matched_ids = known_matched_ids(output_data)
    skipped_ids = {s["id"] for s in skipped}

    pending = [v for v in raw if v["id"] not in matched_ids and v["id"] not in skipped_ids]

    os.makedirs(SKILL_DATA_DIR, exist_ok=True)
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(pending, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Raw videos       : {len(raw)}")
    print(f"Already matched  : {len(matched_ids)}")
    print(f"Already skipped  : {len(skipped_ids)}")
    print(f"Pending review   : {len(pending)}")
    print(f"Wrote {PENDING_FILE}")


if __name__ == "__main__":
    main()
