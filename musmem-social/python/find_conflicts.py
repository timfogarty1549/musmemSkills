#!/usr/bin/env python3
import sys
import json
import os
import glob
from collections import defaultdict


PLATFORM_KEYS = ["ig", "fb", "tw"]
PLATFORM_ALIASES = {"instagram": "ig", "facebook": "fb", "twitter": "tw", "ig": "ig", "fb": "fb", "tw": "tw"}
PLATFORM_URL = {
    "ig": "https://www.instagram.com/{}",
    "fb": "https://www.facebook.com/{}",
    "tw": "https://x.com/{}",
}


def get_config():
    config_dir = os.path.expanduser("~/workspace/skills/musmemSkills/config")
    with open(f"{config_dir}/paths.json") as f:
        paths = json.load(f)
    return {
        "social_media": os.path.expanduser(paths["social_media"]),
    }


def main():
    filter_platform = None
    if "--platform" in sys.argv:
        idx = sys.argv.index("--platform")
        if idx + 1 >= len(sys.argv):
            print("--platform requires a value (ig, fb, tw, instagram, facebook, twitter)", file=sys.stderr)
            sys.exit(2)
        arg = sys.argv[idx + 1]
        if arg not in PLATFORM_ALIASES:
            print(f"Unknown platform: {arg}", file=sys.stderr)
            sys.exit(2)
        filter_platform = PLATFORM_ALIASES[arg]

    config = get_config()
    social_media = config["social_media"]
    keys_to_check = [filter_platform] if filter_platform else PLATFORM_KEYS

    # handle -> platform_key -> [(athlete_name, filename)]
    handle_map = defaultdict(lambda: defaultdict(list))

    files = sorted(glob.glob(os.path.join(social_media, "approved-*-*.json")))
    if not files:
        print(f"No approved files found in {social_media}")
        sys.exit(0)

    for filepath in files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, encoding="utf-8") as f:
                records = json.load(f)
        except Exception as e:
            print(f"Warning: could not read {filepath}: {e}", file=sys.stderr)
            continue

        for rec in records:
            name = rec.get("name", "?")
            for key in keys_to_check:
                handle = rec.get(key)
                if handle:
                    handle_map[handle][key].append((name, filename))

    conflicts = [
        (key, handle, entries)
        for handle, platforms in handle_map.items()
        for key, entries in platforms.items()
        if len(entries) > 1
    ]

    if not conflicts:
        print("No conflicts found.")
        return

    conflicts.sort(key=lambda x: (x[0], x[1]))
    print(f"Found {len(conflicts)} conflict(s):\n")
    for key, handle, entries in conflicts:
        url = PLATFORM_URL.get(key, "{}").format(handle)
        print(f"  {url}")
        for name, filename in entries:
            print(f"    {name}  ({filename})")
        print()


if __name__ == "__main__":
    main()
