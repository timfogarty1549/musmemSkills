"""
resolve_gender.py

For each entry in athletes_localized.json["unknown"], search the MuscleMemory API
to determine gender. Moves entries to "male" or "female" if exactly 1 result is
found; leaves in "unknown" otherwise. Saves after every move.
"""

import json, os, time, urllib.request, urllib.parse

PATHS_FILE = os.path.join(os.path.dirname(__file__), '../../config/paths.json')
APIS_FILE  = os.path.join(os.path.dirname(__file__), '../../config/apis.json')

def load_json(path):
    with open(os.path.expanduser(path), encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(os.path.expanduser(path), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def search(athlete, gender, base_url, ua):
    encoded = urllib.parse.quote(athlete)
    url = f"{base_url}/api/search?offset=0&limit=2&match={encoded}&gender={gender}"
    req = urllib.request.Request(url, headers={'User-Agent': ua})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def main():
    paths = load_json(PATHS_FILE)
    apis  = load_json(APIS_FILE)

    localized_path = paths['athletes_localized']
    base_url       = apis['musclememory_org']
    ua             = apis['user_agent_api']

    data = load_json(localized_path)

    unknown = data.get('unknown', {})
    if not unknown:
        print("No entries in 'unknown'. Nothing to do.")
        return

    total    = len(unknown)
    moved    = {'male': 0, 'female': 0}
    left     = 0
    errors   = []

    # Work on a copy of keys so we can modify dict while iterating
    names = list(unknown.keys())
    print(f"Processing {total} unknown entries...\n")

    for i, name in enumerate(names, 1):
        value = unknown[name]
        result_gender = None

        try:
            # Try male first
            resp = search(name, 'male', base_url, ua)
            count = resp.get('data', {}).get('count', 0)
            if count == 1:
                result_gender = 'male'
            else:
                # Try female
                resp = search(name, 'female', base_url, ua)
                count = resp.get('data', {}).get('count', 0)
                if count == 1:
                    result_gender = 'female'

        except Exception as e:
            errors.append(f"  {name}: {e}")
            print(f"[{i}/{total}] ERROR {name}: {e}")
            time.sleep(0.5)
            continue

        if result_gender:
            data[result_gender][name] = value
            del data['unknown'][name]
            moved[result_gender] += 1
            print(f"[{i}/{total}] → {result_gender:6s}  {name}")
            # Save after every move so progress is not lost on interruption
            save_json(localized_path, data)
        else:
            left += 1
            print(f"[{i}/{total}]   unknown  {name}")

        time.sleep(0.2)  # be polite to the API

    print(f"\nDone.")
    print(f"  Moved to male:   {moved['male']}")
    print(f"  Moved to female: {moved['female']}")
    print(f"  Still unknown:   {left}")
    if errors:
        print(f"  Errors ({len(errors)}):")
        for e in errors:
            print(e)

if __name__ == '__main__':
    main()
