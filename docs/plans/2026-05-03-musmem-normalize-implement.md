# musmem-normalize Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the `musmem-normalize` skill — an interactive conversational loop for resolving bodybuilding athlete name variants across bb_male.dat and covid-male.dat.

**Architecture:** A SKILL.md file (conversational loop instructions for Claude) plus three Python helper scripts for file I/O. Claude manages the loop; Python handles reading/writing large dat files and the TSV. Labels (a, b, c…) are assigned alphabetically by name within each group — consistently between fetch and apply.

**Tech Stack:** Python 3, standard library only (csv, json, re, datetime). No external dependencies.

---

## Task 1: Create skill directory structure

**Files:**
- Create: `.claude/skills/musmem-normalize/` (directory)
- Create: `.claude/skills/musmem-normalize/python/` (directory)

**Step 1: Verify parent directory exists**

```bash
ls /Users/timfogarty/workspace/skills/musmemSkills/.claude/skills/
```
Expected: shows existing skill directories (musmem-contests, musmem-social, etc.)

**Step 2: Create directories**

```bash
mkdir -p /Users/timfogarty/workspace/skills/musmemSkills/.claude/skills/musmem-normalize/python
```

---

## Task 2: Write fetch_group.py

**Files:**
- Create: `.claude/skills/musmem-normalize/python/fetch_group.py`

This script reads the TSV, finds the next pending group (expression blank or `defer`), fetches matching records from both dat files, and outputs JSON for Claude to format and display.

**Step 1: Write the script**

```python
#!/usr/bin/env python3
"""
fetch_group.py — reads next pending group and its records from both dat files.

Usage:
    python3 fetch_group.py --tsv PATH --bb-male PATH --covid-male PATH [--group-id N]

Output: JSON to stdout.
  {
    "group_id": 14,
    "pending_remaining": 42,
    "variants": [
      {
        "label": "a",
        "name": "Adams, Brian",
        "count_bb_male": 1,
        "count_covid_male": 0,
        "records": [
          {"file": "bb_male", "line": "Adams, Brian; 2010; New York Metro Championships - NPC; 3L-1;"}
        ]
      }
    ]
  }
  null  — if no pending groups remain
"""
import argparse, json, sys, csv

FINALS = {'skip'}  # expressions that permanently close a group; anything else (incl. defer) is re-presentable

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--tsv', required=True)
    p.add_argument('--bb-male', required=True)
    p.add_argument('--covid-male', required=True)
    p.add_argument('--group-id', type=int, default=None)
    return p.parse_args()

def load_tsv(path):
    """Returns list of dicts with keys: group_id, name, count_bb_male, count_covid_male, expression, applied"""
    rows = []
    with open(path, encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        header = next(reader)
        for row in reader:
            # Pad to 6 columns
            while len(row) < 6:
                row.append('')
            rows.append({
                'group_id': int(row[0]),
                'name': row[1],
                'count_bb_male': int(row[2]) if row[2].strip().isdigit() else 0,
                'count_covid_male': int(row[3]) if row[3].strip().isdigit() else 0,
                'expression': row[4].strip(),
                'applied': row[5].strip(),
            })
    return rows

def group_is_pending(rows_for_group):
    """A group is pending if its expression is blank or 'defer'."""
    expr = rows_for_group[0]['expression']
    return expr == '' or expr == 'defer'

def find_next_group(rows, target_id=None):
    """Returns (group_id, group_rows) for the next pending group, or (None, None)."""
    groups = {}
    order = []
    for row in rows:
        gid = row['group_id']
        if gid not in groups:
            groups[gid] = []
            order.append(gid)
        groups[gid].append(row)
    
    if target_id is not None:
        g = groups.get(target_id)
        if g and group_is_pending(g):
            return target_id, g
        return None, None
    
    for gid in order:
        if group_is_pending(groups[gid]):
            return gid, groups[gid]
    return None, None

def count_pending(rows):
    groups = {}
    for row in rows:
        gid = row['group_id']
        if gid not in groups:
            groups[gid] = []
        groups[gid].append(row)
    return sum(1 for g in groups.values() if group_is_pending(g))

def fetch_records(dat_path, names):
    """Returns dict: name -> list of raw line strings (stripped)."""
    name_set = set(names)
    result = {n: [] for n in name_set}
    with open(dat_path, encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            first_field = stripped.split(';')[0].strip()
            if first_field in name_set:
                result[first_field].append(stripped)
    return result

def main():
    args = parse_args()
    rows = load_tsv(args.tsv)
    
    gid, group_rows = find_next_group(rows, args.group_id)
    if gid is None:
        print('null')
        return
    
    pending_remaining = count_pending(rows)
    names = sorted(set(r['name'] for r in group_rows))  # alphabetical = label order
    
    bb_records = fetch_records(args.bb_male, names)
    covid_records = fetch_records(args.covid_male, names)
    
    variants = []
    for i, name in enumerate(names):
        label = chr(ord('a') + i)
        row = next(r for r in group_rows if r['name'] == name)
        records = (
            [{'file': 'bb_male', 'line': ln} for ln in bb_records[name]] +
            [{'file': 'covid_male', 'line': ln} for ln in covid_records[name]]
        )
        variants.append({
            'label': label,
            'name': name,
            'count_bb_male': row['count_bb_male'],
            'count_covid_male': row['count_covid_male'],
            'records': records,
        })
    
    print(json.dumps({
        'group_id': gid,
        'pending_remaining': pending_remaining,
        'variants': variants,
    }, ensure_ascii=False))

if __name__ == '__main__':
    main()
```

**Step 2: Smoke-test manually**

Copy to `/tmp/fetch_group.py`, run against the real files:

```bash
python3 /tmp/fetch_group.py \
  --tsv ~/workspace/musmem/data/prelim/bb2010-covid-male-variant-groups.tsv \
  --bb-male ~/workspace/musmem/data/bb_male.dat \
  --covid-male ~/workspace/musmem/data/prelim/covid-male.dat
```

Expected: JSON output with the first pending group's variants and records.

---

## Task 3: Write record_decision.py

**Files:**
- Create: `.claude/skills/musmem-normalize/python/record_decision.py`

Writes an expression to column 5 of all TSV rows matching a given group_id.

```python
#!/usr/bin/env python3
"""
record_decision.py — writes expression to TSV for all rows in a group.

Usage:
    python3 record_decision.py --tsv PATH --group-id N --expression TEXT
"""
import argparse, csv, sys

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--tsv', required=True)
    p.add_argument('--group-id', type=int, required=True)
    p.add_argument('--expression', required=True)
    return p.parse_args()

def main():
    args = parse_args()
    
    with open(args.tsv, encoding='utf-8') as f:
        content = f.read()
    
    lines = content.splitlines(keepends=True)
    header = lines[0]
    data_lines = lines[1:]
    
    updated = 0
    out_lines = [header]
    for line in data_lines:
        cols = line.rstrip('\n').split('\t')
        while len(cols) < 6:
            cols.append('')
        if int(cols[0]) == args.group_id:
            cols[4] = args.expression
            updated += 1
        out_lines.append('\t'.join(cols) + '\n')
    
    with open(args.tsv, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)
    
    print(f"Updated {updated} rows for group {args.group_id}")

if __name__ == '__main__':
    main()
```

---

## Task 4: Write apply_corrections.py

**Files:**
- Create: `.claude/skills/musmem-normalize/python/apply_corrections.py`

Reads all queued expressions from the TSV, parses them into a rename map, checks for collisions, applies to both dat files, stamps the `applied` timestamp.

Key logic:
- Labels (a, b, c…) are resolved by sorting variant names alphabetically within the group
- `a=b` → rename a's name to b's name
- `[a,b]=c` → rename a and b to c's name
- `a="New Name"` → rename a to literal "New Name"
- Multiple expressions separated by commas
- Only groups where `expression` is set AND `applied` is blank AND expression is not `skip`/`defer`

```python
#!/usr/bin/env python3
"""
apply_corrections.py — applies all queued name corrections to dat files.

Usage:
    python3 apply_corrections.py --tsv PATH --bb-male PATH --covid-male PATH [--dry-run]

Prints collision warnings to stdout. On --dry-run, shows what would change without writing.
"""
import argparse, csv, re
from datetime import datetime, timezone

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--tsv', required=True)
    p.add_argument('--bb-male', required=True)
    p.add_argument('--covid-male', required=True)
    p.add_argument('--dry-run', action='store_true')
    return p.parse_args()

def load_tsv(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        lines = f.read().splitlines()
    header = lines[0]
    for line in lines[1:]:
        if not line.strip():
            continue
        cols = line.split('\t')
        while len(cols) < 6:
            cols.append('')
        rows.append({
            'group_id': int(cols[0]),
            'name': cols[1],
            'expression': cols[4].strip(),
            'applied': cols[5].strip(),
        })
    return rows, header, lines

def get_queued_groups(rows):
    """Groups where expression is set, not skip/defer, and applied is blank."""
    groups = {}
    for row in rows:
        gid = row['group_id']
        if gid not in groups:
            groups[gid] = []
        groups[gid].append(row)
    
    result = {}
    for gid, group_rows in groups.items():
        expr = group_rows[0]['expression']
        applied = group_rows[0]['applied']
        if expr and expr not in ('skip', 'defer') and not applied:
            result[gid] = group_rows
    return result

def resolve_labels(group_rows):
    """Returns dict: label -> name, sorted alphabetically."""
    names = sorted(set(r['name'] for r in group_rows))
    return {chr(ord('a') + i): name for i, name in enumerate(names)}

def parse_expression(expr, label_map):
    """
    Parses an expression string into a list of (source_names, canonical_name) tuples.
    source_names is a list of actual name strings.
    canonical_name is an actual name string.
    """
    renames = []
    # Split on top-level commas (not inside brackets or quotes)
    parts = split_expressions(expr)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Match: [a,b,c]="Name" or [a,b,c]=d or a="Name" or a=b
        m = re.match(r'^\[([^\]]+)\]\s*=\s*(.+)$', part)
        if m:
            labels = [l.strip() for l in m.group(1).split(',')]
            sources = [label_map[l] for l in labels if l in label_map]
            target = parse_target(m.group(2).strip(), label_map)
            renames.append((sources, target))
        else:
            m2 = re.match(r'^([a-z])\s*=\s*(.+)$', part)
            if m2:
                lbl = m2.group(1)
                sources = [label_map[lbl]] if lbl in label_map else []
                target = parse_target(m2.group(2).strip(), label_map)
                renames.append((sources, target))
    return renames

def split_expressions(expr):
    """Split on commas that are not inside [] or quotes."""
    parts = []
    depth = 0
    in_quote = False
    current = []
    for ch in expr:
        if ch == '"':
            in_quote = not in_quote
        elif ch == '[' and not in_quote:
            depth += 1
        elif ch == ']' and not in_quote:
            depth -= 1
        elif ch == ',' and depth == 0 and not in_quote:
            parts.append(''.join(current))
            current = []
            continue
        current.append(ch)
    if current:
        parts.append(''.join(current))
    return parts

def parse_target(raw, label_map):
    """Returns the canonical name string from a target token."""
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw in label_map:
        return label_map[raw]
    return raw  # fallback: treat as literal

def build_rename_map(queued_groups):
    """Returns dict: source_name -> canonical_name across all queued groups."""
    rename_map = {}
    for gid, group_rows in queued_groups.items():
        label_map = resolve_labels(group_rows)
        expr = group_rows[0]['expression']
        renames = parse_expression(expr, label_map)
        for sources, target in renames:
            for src in sources:
                rename_map[src] = target
    return rename_map

def find_names_in_file(dat_path):
    """Returns set of all distinct name fields in the dat file."""
    names = set()
    with open(dat_path, encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                names.add(stripped.split(';')[0].strip())
    return names

def check_collisions(rename_map, bb_names, covid_names):
    """Returns list of collision warning strings."""
    warnings = []
    for src, tgt in rename_map.items():
        for file_label, name_set in [('bb_male', bb_names), ('covid_male', covid_names)]:
            if src in name_set and tgt in name_set:
                warnings.append(f"COLLISION in {file_label}: '{src}' → '{tgt}' (target already exists)")
    return warnings

def apply_to_file(dat_path, rename_map, dry_run):
    """Applies rename_map to dat file. Returns count of changed lines."""
    with open(dat_path, encoding='utf-8') as f:
        lines = f.readlines()
    
    changed = 0
    out_lines = []
    for line in lines:
        stripped = line.rstrip('\n')
        if ';' in stripped:
            first_field = stripped.split(';')[0].strip()
            if first_field in rename_map:
                new_name = rename_map[first_field]
                new_line = stripped.replace(first_field, new_name, 1) + '\n'
                out_lines.append(new_line)
                changed += 1
                continue
        out_lines.append(line)
    
    if not dry_run:
        with open(dat_path, 'w', encoding='utf-8') as f:
            f.writelines(out_lines)
    
    return changed

def stamp_applied(tsv_path, group_ids, timestamp):
    """Stamps applied timestamp on all rows in the given group_ids."""
    with open(tsv_path, encoding='utf-8') as f:
        lines = f.read().splitlines(keepends=True)
    
    header = lines[0]
    out_lines = [header]
    for line in lines[1:]:
        cols = line.rstrip('\n').split('\t')
        while len(cols) < 6:
            cols.append('')
        if int(cols[0]) in group_ids:
            cols[5] = timestamp
        out_lines.append('\t'.join(cols) + '\n')
    
    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

def main():
    args = parse_args()
    rows, header, raw_lines = load_tsv(args.tsv)
    queued = get_queued_groups(rows)
    
    if not queued:
        print("No queued corrections to apply.")
        return
    
    rename_map = build_rename_map(queued)
    print(f"Rename map ({len(rename_map)} entries):")
    for src, tgt in sorted(rename_map.items()):
        print(f"  '{src}' → '{tgt}'")
    
    bb_names = find_names_in_file(args.bb_male)
    covid_names = find_names_in_file(args.covid_male)
    
    collisions = check_collisions(rename_map, bb_names, covid_names)
    if collisions:
        print("\nWARNINGS (collisions — target name already exists in file):")
        for w in collisions:
            print(f"  {w}")
        print("\nCollisions will merge records. Proceeding anyway (no data is lost).")
    
    if args.dry_run:
        print("\n[DRY RUN — no files written]")
        return
    
    bb_changed = apply_to_file(args.bb_male, rename_map, dry_run=False)
    covid_changed = apply_to_file(args.covid_male, rename_map, dry_run=False)
    print(f"\nApplied: {bb_changed} lines changed in bb_male.dat, {covid_changed} in covid-male.dat")
    
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    stamp_applied(args.tsv, set(queued.keys()), ts)
    print(f"Stamped {len(queued)} groups as applied at {ts}")

if __name__ == '__main__':
    main()
```

---

## Task 5: Write SKILL.md

**Files:**
- Create: `.claude/skills/musmem-normalize/SKILL.md`

The skill file defines the conversational loop, how to invoke the Python scripts, and the display format Claude must render.

Key points for the SKILL.md:
- Default file paths hardcoded (with override option)
- Copy Python scripts from skill directory to `/tmp/` before first run
- Session loop: fetch → display → wait → record → repeat
- Display format: compact summary with year range, orgs, divisions
- `expand <label>` shows full records for that variant
- `process` runs apply_corrections.py; `exit` quits
- After `process`, continue loop (don't exit)

---

## Task 6: Smoke-test the full loop

**Step 1:** Invoke the skill from Claude Code with default paths.

**Step 2:** Verify:
- First pending group displays correctly with compact summary
- `expand a` shows full records and re-prompts
- Entering `defer` loops to next group and marks TSV correctly
- Entering `skip` loops to next group and marks TSV correctly
- Entering a simple expression (e.g. `a=b`) records it and loops
- `process` runs apply_corrections.py and continues
- `exit` quits cleanly

**Step 3:** Check the TSV to confirm columns 5 and 6 are written correctly.
