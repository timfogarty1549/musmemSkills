"""
Unicode lookup for a specific contest + year.
Follows the musmem-unicode skill workflow.
"""
import json, os, urllib.request, urllib.parse

SKILLS_DIR = os.path.expanduser('~/workspace/skills/musmemSkills')
PATHS_FILE = os.path.join(SKILLS_DIR, 'config/paths.json')
APIS_FILE  = os.path.join(SKILLS_DIR, 'config/apis.json')

def load_json(path):
    with open(os.path.expanduser(path), encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(os.path.expanduser(path), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch(url, ua):
    req = urllib.request.Request(url, headers={'User-Agent': ua})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

paths = load_json(PATHS_FILE)
apis  = load_json(APIS_FILE)
base  = apis['musclememory_net']
ua    = apis['user_agent_api']

contest = 'Korean Classic Pro - IFBB'
year    = 2020

# Step 1 — fetch athletes
url = base + '/api/contest?name=' + urllib.parse.quote(contest) + '&year=' + str(year)
print(f"Fetching: {url}\n")
data = fetch(url, ua)

results = data.get('data', {}).get('results', [])

# Deduplicate by completeName, keep gender
seen = {}
for r in results:
    name = r['completeName']
    if name not in seen:
        seen[name] = r['gender']

print(f"Athletes: {len(seen)}")

# Step 2 — check athletes_localized.json
localized = load_json(paths['athletes_localized'])

already   = []
unmatched = []  # (name, gender)

for name, gender in seen.items():
    if name in localized.get(gender, {}) or name in localized.get('unknown', {}):
        already.append(name)
    else:
        unmatched.append((name, gender))

print(f"Already in file: {len(already)}")
for n in already:
    print(f"  {n}")

print(f"\nTo search: {len(unmatched)}")
for n, g in unmatched:
    print(f"  [{g}] {n}")
