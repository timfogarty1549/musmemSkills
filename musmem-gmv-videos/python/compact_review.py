"""
Ad-hoc helper (not part of the documented workflow): render
gmv_videos_suggestions.json as compact one-line-per-video text so Claude can
scan hundreds of candidates densely instead of paging through full JSON.
"""
import json
import os

SKILL_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SUGGESTIONS_FILE = os.path.join(SKILL_DATA_DIR, "gmv_videos_suggestions.json")
OUT_FILE = os.path.join(SKILL_DATA_DIR, "compact_review.txt")

with open(SUGGESTIONS_FILE, encoding="utf-8") as f:
    data = json.load(f)

lines = []
for d in data:
    tops = d["candidates"][:3]
    if tops:
        parts = [f"{c['score']:.2f} {c['contest']}{'*' if c['year_in_db'] else ''}" for c in tops]
        top_str = " ; ".join(parts)
    else:
        top_str = "NO CANDIDATES"
    lines.append(f"{d['id']} | {d['title']} || {top_str}")

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"Wrote {len(lines)} lines to {OUT_FILE}")
