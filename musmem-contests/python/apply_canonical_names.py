#!/usr/bin/env python3
"""
Apply raw_to_canonical.tsv to 1-incoming/ files → write 2-normalize-athletes/.

For each file in 1-incoming/:
  - Copy y/t/c/---- and other non-athlete lines verbatim
  - For athlete lines (N name):
      - If placing == 98 AND filename contains 'npc_worldwide': skip
      - Otherwise: look up name in TSV
          - Found, canonical starts with '@': write @N canonical_name
          - Found, canonical normal:           write N  canonical_name
          - Not found:                         write line as-is
"""
import csv, os, re, sys

INCOMING   = os.path.expanduser('~/workspace/musmem/1-incoming')
NORMALIZED = os.path.expanduser('~/workspace/musmem/2-normalize-athletes')
TSV        = os.path.expanduser('~/workspace/musmem/working_data/raw_to_canonical.tsv')

ATHLETE_RE = re.compile(r'^(\d+)\s+(.*\S)\s*$')

# ── Load TSV ──────────────────────────────────────────────────────────────────
lookup = {}
with open(TSV, newline='') as f:
    reader = csv.reader(f, delimiter='\t')
    next(reader)  # skip header
    for row in reader:
        if len(row) >= 2 and row[0] != '___TBD___':
            lookup[row[0]] = row[1]

print(f"Loaded {len(lookup)} TSV entries")

# ── Process files ─────────────────────────────────────────────────────────────
os.makedirs(NORMALIZED, exist_ok=True)

written = skipped_98 = looked_up = not_found = 0
files_written = 0

for fname in sorted(os.listdir(INCOMING)):
    if not fname.endswith('.txt'):
        continue

    is_npc_worldwide = 'npc_worldwide' in fname
    src = os.path.join(INCOMING, fname)
    dst = os.path.join(NORMALIZED, fname)

    out_lines = []
    for raw_line in open(src, errors='ignore'):
        line = raw_line.rstrip('\n')

        m = ATHLETE_RE.match(line)
        if not m:
            # Non-athlete line (y, t, c, ----, blank): copy verbatim
            out_lines.append(line)
            continue

        place = m.group(1)
        name  = m.group(2)

        # Skip placing-98 in NPC Worldwide files
        if place == '98' and is_npc_worldwide:
            skipped_98 += 1
            continue

        canonical = lookup.get(name)
        if canonical is not None:
            looked_up += 1
            if canonical.startswith('@'):
                out_lines.append(f'@{place} {canonical[1:]}')
            else:
                out_lines.append(f'{place} {canonical}')
        else:
            not_found += 1
            out_lines.append(line)

    with open(dst, 'w') as f:
        f.write('\n'.join(out_lines))
        if out_lines:
            f.write('\n')

    written += 1
    files_written += 1

print(f"Files written:     {files_written}")
print(f"TSV lookups hit:   {looked_up}")
print(f"Not in TSV (raw):  {not_found}")
print(f"Skipped (98+npcw): {skipped_98}")
