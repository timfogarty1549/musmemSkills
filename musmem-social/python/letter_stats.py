"""
letter_stats.py — show per-letter progress for a dat-file sweep

Usage:
    python3 letter_stats.py [dat_basename] [gender]

Defaults:
    dat_basename = covid-male
    gender       = male

Reads:
    ~/workspace/musmem/data/prelim/{dat_basename}.dat
    ~/workspace/musmem/working_data/searched-ig-{gender}.txt
    ~/workspace/musmem/data/social-media/{dat_basename}-{letter}-section-{gender}.json

Prints a table: letter | dat names | searched | found | % found
"""

import json, re, os, sys, unicodedata

DAT_BASENAME = sys.argv[1] if len(sys.argv) > 1 else "covid-male"
GENDER = sys.argv[2] if len(sys.argv) > 2 else "male"

DAT = os.path.expanduser(f"~/workspace/musmem/data/prelim/{DAT_BASENAME}.dat")
SEARCHED_FILE = os.path.expanduser(f"~/workspace/musmem/working_data/searched-ig-{GENDER}.txt")
SOCIAL_DIR = os.path.expanduser("~/workspace/musmem/data/social-media")


def strip_codes(name):
    s = re.sub(r'\s*\(\d+\)', '', name)
    s = re.sub(r"[^a-zA-Z,\s\-]", " ", s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = unicodedata.normalize('NFD', s)
    return s.encode('ascii', 'ignore').decode('ascii').lower()


# Count distinct dat names per letter
dat_by_letter = {}
seen_keys = set()
with open(DAT, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split(';')
        if not parts:
            continue
        name = parts[0].strip()
        if not name:
            continue
        k = strip_codes(name)
        if not k or not k[0].isalpha():
            continue
        if k in seen_keys:
            continue
        seen_keys.add(k)
        letter = k[0]
        dat_by_letter[letter] = dat_by_letter.get(letter, 0) + 1

# Count searched names per letter
searched_by_letter = {}
with open(SEARCHED_FILE, encoding='utf-8') as f:
    for line in f:
        name = line.strip()
        if not name:
            continue
        k = strip_codes(name)
        if not k or not k[0].isalpha():
            continue
        letter = k[0]
        searched_by_letter[letter] = searched_by_letter.get(letter, 0) + 1

# Count found handles per letter
found_by_letter = {}
for letter in 'abcdefghijklmnopqrstuvwxyz':
    path = os.path.join(SOCIAL_DIR, f"{DAT_BASENAME}-{letter}-section-{GENDER}.json")
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            records = json.load(f)
        found_by_letter[letter] = len(records)
    else:
        found_by_letter[letter] = 0

# Print table
letters = sorted(dat_by_letter.keys())
print(f"{'Letter':<8} {'Dat names':>10} {'Searched':>10} {'Found':>7} {'% found':>8}")
print("-" * 50)
total_dat = total_searched = total_found = 0
for letter in letters:
    dat_n = dat_by_letter.get(letter, 0)
    srch_n = searched_by_letter.get(letter, 0)
    fnd_n = found_by_letter.get(letter, 0)
    pct = f"{100 * fnd_n / dat_n:.1f}%" if dat_n else "-"
    print(f"{letter.upper():<8} {dat_n:>10} {srch_n:>10} {fnd_n:>7} {pct:>8}")
    total_dat += dat_n
    total_searched += srch_n
    total_found += fnd_n

print("-" * 50)
total_pct = f"{100 * total_found / total_dat:.1f}%" if total_dat else "-"
print(f"{'TOTAL':<8} {total_dat:>10} {total_searched:>10} {total_found:>7} {total_pct:>8}")
