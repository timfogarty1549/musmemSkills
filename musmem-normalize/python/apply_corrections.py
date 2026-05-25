#!/usr/bin/env python3
"""
apply_corrections.py — applies all queued name corrections to dat files.

TSV column 5 now stores the canonical target name per row (not an expression string):
  blank or '-' → no rename for this row
  'skip'       → group was skipped, no changes
  'defer'      → group deferred, not applied
  any other    → rename this row's name (col 2) to this value

Usage:
    python3 apply_corrections.py --tsv PATH --file1 PATH --file2 PATH [--dry-run]
"""
import argparse, shutil, time
from datetime import datetime, timezone

SPECIAL = {'', '-', 'skip', 'defer'}

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--tsv', required=True)
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--dry-run', action='store_true')
    return p.parse_args()

def load_tsv(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        lines = f.read().splitlines()
    for line in lines[1:]:
        if not line.strip():
            continue
        cols = line.split('\t')
        while len(cols) < 4:
            cols.append('')
        rows.append({
            'group_id':   int(cols[0]),
            'name':       cols[1],
            'expression': cols[2].strip(),
            'applied':    cols[3].strip(),
        })
    return rows

def get_queued_groups(rows):
    """Groups where any row has a canonical rename target in col 5, not yet applied."""
    groups = {}
    order = []
    for row in rows:
        gid = row['group_id']
        if gid not in groups:
            groups[gid] = []
            order.append(gid)
        groups[gid].append(row)

    result = {}
    for gid in order:
        group_rows = groups[gid]
        has_rename = any(r['expression'] not in SPECIAL for r in group_rows)
        not_applied = all(not r['applied'] for r in group_rows)
        if has_rename and not_applied:
            result[gid] = group_rows
    return result

def build_rename_map(queued_groups):
    """Returns dict: source_name -> canonical_name, read directly from col 5."""
    rename_map = {}
    for gid, group_rows in queued_groups.items():
        for row in group_rows:
            if row['expression'] not in SPECIAL:
                rename_map[row['name']] = row['expression']
    return rename_map

def find_names_in_file(dat_path):
    names = set()
    with open(dat_path, encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if stripped and ';' in stripped:
                names.add(stripped.split(';')[0].strip())
    return names

def check_collisions(rename_map, source_names_per_group, file_names_list):
    """Warn when a target is a new name (not a group variant) and already exists in a file.
    file_names_list: list of name sets, one per file."""
    all_group_names = set()
    for names in source_names_per_group.values():
        all_group_names.update(names)

    warnings = []
    for src, tgt in rename_map.items():
        if tgt in all_group_names:
            continue
        for i, name_set in enumerate(file_names_list):
            if tgt in name_set:
                warnings.append(
                    f"  COLLISION in f{i+1}: '{src}' → '{tgt}' "
                    f"(target already exists — records will merge with an unrelated athlete)"
                )
    return warnings

def apply_to_file(dat_path, rename_map, dry_run):
    with open(dat_path, encoding='utf-8') as f:
        lines = f.readlines()

    changed = 0
    out_lines = []
    for line in lines:
        parts = line.rstrip('\n').split(';')
        if len(parts) >= 2:
            first_field = parts[0].strip()
            if first_field in rename_map:
                parts[0] = rename_map[first_field]
                out_lines.append(';'.join(parts) + '\n')
                changed += 1
                continue
        out_lines.append(line)

    if not dry_run:
        with open(dat_path, 'w', encoding='utf-8') as f:
            f.writelines(out_lines)

    return changed

def stamp_applied(tsv_path, group_ids, timestamp):
    with open(tsv_path, encoding='utf-8') as f:
        lines = f.read().splitlines(keepends=True)

    out_lines = [lines[0]]
    for line in lines[1:]:
        cols = line.rstrip('\n').split('\t')
        while len(cols) < 4:
            cols.append('')
        if int(cols[0]) in group_ids:
            cols[3] = timestamp
        out_lines.append('\t'.join(cols) + '\n')

    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

def main():
    args = parse_args()
    rows = load_tsv(args.tsv)
    queued = get_queued_groups(rows)

    if not queued:
        print("No queued corrections to apply.")
        return

    rename_map = build_rename_map(queued)
    print(f"Rename map ({len(rename_map)} entries):")
    for src, tgt in sorted(rename_map.items()):
        print(f"  '{src}' → '{tgt}'")

    file_names_list = [find_names_in_file(f) for f in args.files]

    source_names_per_group = {gid: set(r['name'] for r in rows) for gid, rows in queued.items()}
    collisions = check_collisions(rename_map, source_names_per_group, file_names_list)
    if collisions:
        print("\nWARNINGS — target name already exists in file (will merge with an unrelated athlete):")
        for w in collisions:
            print(w)

    if args.dry_run:
        print("\n[DRY RUN — no files written]")
        return

    epoch = int(time.time())
    for path in args.files:
        backup = f"{path}.{epoch}"
        shutil.copy2(path, backup)
        print(f"Backup: {backup}")

    changed = []
    for i, path in enumerate(args.files):
        n = apply_to_file(path, rename_map, dry_run=False)
        changed.append(f'f{i+1}: {n}')
    print(f"\nApplied: {', '.join(changed)} lines changed")

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    stamp_applied(args.tsv, set(queued.keys()), ts)
    print(f"Stamped {len(queued)} groups as applied at {ts}")

if __name__ == '__main__':
    main()
