#!/usr/bin/env python3
"""Find flat files in 1-incoming/ that contain non-Latin athlete names."""
import os, re, unicodedata, glob

INCOMING = os.path.expanduser('~/workspace/musmem/1-incoming')

def is_nonlatin(name):
    """True if name contains characters outside Latin/Latin-Extended/Common ranges."""
    for c in name:
        cp = ord(c)
        # Skip ASCII, Latin-1 Supplement, Latin Extended A/B, IPA, spacing modifiers,
        # combining diacritical marks (already NFC-normalized away normally)
        if cp <= 0x02FF:
            continue
        if 0x0300 <= cp <= 0x036F:  # combining diacriticals
            continue
        # Anything else is non-Latin
        cat = unicodedata.category(c)
        if cat in ('Zs', 'Pd', 'Po'):  # spaces, dashes, punctuation — skip
            continue
        return True
    return False

def script_hint(name):
    """Return a short label for the dominant non-Latin script."""
    for c in name:
        cp = ord(c)
        if 0x0400 <= cp <= 0x04FF:
            return 'Cyrillic'
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            return 'CJK'
        if 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF:
            return 'Korean'
        if 0x3040 <= cp <= 0x30FF:
            return 'Japanese'
        if 0x0600 <= cp <= 0x06FF:
            return 'Arabic'
        if cp > 0x02FF:
            return f'U+{cp:04X}'
    return '?'

files = sorted(glob.glob(os.path.join(INCOMING, '*.txt')))
results = {}  # script → [(file, name), ...]

for fpath in files:
    fname = os.path.basename(fpath)
    with open(fpath, encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^(\d+|98|0)\s+(.+)$', line.rstrip())
            if not m:
                continue
            name = m.group(2)
            if is_nonlatin(name):
                script = script_hint(name)
                results.setdefault(script, []).append((fname, name))

for script, entries in sorted(results.items()):
    print(f"\n{script} ({len(entries)} names in {len(set(f for f,_ in entries))} files):")
    shown_files = set()
    for fname, name in entries[:20]:
        if fname not in shown_files:
            print(f"  {fname}")
            shown_files.add(fname)
        print(f"    {name}")
    if len(entries) > 20:
        print(f"  ... and {len(entries)-20} more")
