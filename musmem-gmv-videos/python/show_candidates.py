"""Ad-hoc helper: print full candidate list for one or more video ids."""
import json
import os
import sys

SKILL_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SUGGESTIONS_FILE = os.path.join(SKILL_DATA_DIR, "gmv_videos_suggestions.json")

with open(SUGGESTIONS_FILE, encoding="utf-8") as f:
    data = {d["id"]: d for d in json.load(f)}

for vid in sys.argv[1:]:
    d = data.get(vid)
    if not d:
        print(f"{vid}: not found")
        continue
    print(f"\n{d['id']} | {d['title']}")
    print(f"  guess: year={d['year_guess']} org={d['org_guess']} base={d['base_guess']!r}")
    for c in d["candidates"]:
        print(f"   {c['score']:.3f}  {c['contest']:45s} year_in_db={c['year_in_db']}  {c['db_years_span']}")
