#!/usr/bin/env python3
import glob
import json
import os

data_dir = os.path.expanduser('~/workspace/musmem/data/social-media')
files = sorted(glob.glob(os.path.join(data_dir, 'approved-*-*.json')))

for filepath in files:
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)
    data.sort(key=lambda e: e.get('name', '').lower())
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('[\n')
        for i, entry in enumerate(data):
            comma = ',' if i < len(data) - 1 else ''
            f.write(f'    {json.dumps(entry, ensure_ascii=False)}{comma}\n')
        f.write(']\n')
    print(f"Sorted {os.path.basename(filepath)} ({len(data)} entries)")
