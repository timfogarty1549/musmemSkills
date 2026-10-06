"""
Scrape the full video list (id + title) from the GMV Bodybuilding YouTube
channel using yt-dlp, and cache it to gmv_videos_raw.json.

Requires yt-dlp on PATH (brew install yt-dlp).

Usage: python3 fetch_channel_videos.py
"""
import json
import os
import subprocess
import sys

CHANNEL_URL = "https://www.youtube.com/@gmvbodybuilding/videos"
SKILL_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
RAW_FILE = os.path.join(SKILL_DATA_DIR, "gmv_videos_raw.json")


def main():
    try:
        proc = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--dump-json", "--playlist-items", "1:9999", CHANNEL_URL],
            capture_output=True, text=True, timeout=300,
        )
    except FileNotFoundError:
        print("ERROR: yt-dlp not found. Install with: brew install yt-dlp", file=sys.stderr)
        sys.exit(1)

    if proc.returncode != 0:
        print("ERROR: yt-dlp failed:", file=sys.stderr)
        print(proc.stderr[-3000:], file=sys.stderr)
        sys.exit(1)

    videos = []
    seen_ids = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        vid = entry.get("id")
        title = entry.get("title", "")
        if not vid or vid in seen_ids:
            continue
        seen_ids.add(vid)
        videos.append({"id": vid, "title": title})

    videos.sort(key=lambda v: v["id"])

    os.makedirs(SKILL_DATA_DIR, exist_ok=True)
    with open(RAW_FILE, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Fetched {len(videos)} videos from channel.")
    print(f"Wrote {RAW_FILE}")


if __name__ == "__main__":
    main()
