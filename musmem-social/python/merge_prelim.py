#!/usr/bin/env python3
import sys
import json
import os
import re
import shutil
from datetime import datetime


def get_config():
    config_dir = os.path.expanduser("~/workspace/skills/musmemSkills/config")
    with open(f"{config_dir}/paths.json") as f:
        paths = json.load(f)
    return {
        "social_media": os.path.expanduser(paths["social_media"]),
    }


def strip_codes(name):
    s = re.sub(r'\s*\(\d+\)', '', name)
    s = re.sub(r"[^a-zA-Z,\s\-]", " ", s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s.lower()


def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        f.write("[\n")
        for i, rec in enumerate(data):
            comma = "," if i < len(data) - 1 else ""
            f.write(f"    {json.dumps(rec, ensure_ascii=False)}{comma}\n")
        f.write("]\n")


def main():
    if len(sys.argv) != 3:
        print("Usage: merge_prelim.py LETTER GENDER", file=sys.stderr)
        sys.exit(2)

    letter = sys.argv[1].lower()
    gender = sys.argv[2].lower()

    if not re.match(r'^[a-z]$', letter):
        print(f"Expected a single letter A-Z, got: {sys.argv[1]}", file=sys.stderr)
        sys.exit(2)

    if gender not in ("male", "female"):
        print(f"Expected gender: male or female, got: {sys.argv[2]}", file=sys.stderr)
        sys.exit(2)

    config = get_config()
    social_media = config["social_media"]

    prelim_path = os.path.join(social_media, f"prelim-{letter}-{gender}.json")
    approved_path = os.path.join(social_media, f"approved-{letter}-{gender}.json")

    if not os.path.exists(prelim_path):
        print(f"No prelim file found: {prelim_path}", file=sys.stderr)
        sys.exit(1)

    prelim = load_json(prelim_path)
    approved = load_json(approved_path)

    approved_index = {strip_codes(r["name"]): i for i, r in enumerate(approved)}

    added = 0
    updated = 0
    conflicts_resolved = 0

    for prelim_rec in prelim:
        norm = strip_codes(prelim_rec["name"])
        platform_keys = [k for k in prelim_rec if k != "name"]

        if norm not in approved_index:
            approved.append(dict(prelim_rec))
            approved_index[norm] = len(approved) - 1
            added += 1
        else:
            idx = approved_index[norm]
            approved_rec = approved[idx]

            for key in platform_keys:
                prelim_handle = prelim_rec[key]

                if key not in approved_rec:
                    approved_rec[key] = prelim_handle
                    updated += 1
                elif approved_rec[key] == prelim_handle:
                    pass  # identical, no action needed
                else:
                    print(f"\nConflict for {prelim_rec['name']} ({key}):")
                    print(f"  [1] approved: {approved_rec[key]}")
                    print(f"  [2] prelim:   {prelim_handle}")
                    while True:
                        choice = input("  Keep which? [1/2]: ").strip()
                        if choice == "1":
                            break
                        elif choice == "2":
                            approved_rec[key] = prelim_handle
                            break
                        else:
                            print("  Please enter 1 or 2.")
                    conflicts_resolved += 1

    save_json(approved_path, approved)
    print(f"\nWrote {approved_path}")
    print(f"  Added:              {added} new athletes")
    print(f"  Updated:            {updated} new platform keys")
    print(f"  Conflicts resolved: {conflicts_resolved}")

    completed_dir = os.path.join(social_media, "completed")
    os.makedirs(completed_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    completed_path = os.path.join(completed_dir, f"prelim-{letter}-{gender}-{timestamp}.json")
    shutil.move(prelim_path, completed_path)
    print(f"  Moved prelim to:    {completed_path}")


if __name__ == "__main__":
    main()
