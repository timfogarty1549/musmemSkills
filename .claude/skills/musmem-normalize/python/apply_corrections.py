#!/usr/bin/env python3
"""
apply_corrections.py — applies all queued name corrections to dat files.

Usage:
    python3 apply_corrections.py --tsv PATH --file1 PATH --file2 PATH [--dry-run]

Prints collision warnings to stdout. On --dry-run, shows what would change without writing.
"""
import argparse, re, shutil, time
from datetime import datetime, timezone

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--tsv', required=True)
    p.add_argument('--file1', required=True)
    p.add_argument('--file2', required=True)
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
        while len(cols) < 6:
            cols.append('')
        rows.append({
            'group_id': int(cols[0]),
            'name': cols[1],
            'expression': cols[4].strip(),
            'applied': cols[5].strip(),
        })
    return rows

def get_queued_groups(rows):
    """Groups where expression is actionable (not skip/defer/blank) and not yet applied."""
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
        expr = group_rows[0]['expression']
        applied = group_rows[0]['applied']
        if expr and expr not in ('skip', 'defer') and not applied:
            result[gid] = group_rows
    return result

def resolve_labels(group_rows):
    """Returns dict: label -> name, labels assigned alphabetically by name."""
    names = sorted(set(r['name'] for r in group_rows))
    return {chr(ord('a') + i): name for i, name in enumerate(names)}

def split_expressions(expr):
    """Split on commas not inside [] or quotes."""
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
    """Returns canonical name string from a target token (quoted literal or label)."""
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw in label_map:
        return label_map[raw]
    return raw

def parse_expression(expr, label_map):
    """Returns list of (source_names, canonical_name) tuples."""
    renames = []
    for part in split_expressions(expr):
        part = part.strip()
        if not part:
            continue
        # [a,b,c]=target
        m = re.match(r'^\[([^\]]+)\]\s*=\s*(.+)$', part)
        if m:
            labels = [l.strip() for l in m.group(1).split(',')]
            sources = [label_map[l] for l in labels if l in label_map]
            target = parse_target(m.group(2), label_map)
            renames.append((sources, target))
            continue
        # a=target
        m2 = re.match(r'^([a-z])\s*=\s*(.+)$', part)
        if m2:
            lbl = m2.group(1)
            if lbl in label_map:
                target = parse_target(m2.group(2), label_map)
                renames.append(([label_map[lbl]], target))
    return renames

def build_rename_map(queued_groups):
    """Returns dict: source_name -> canonical_name."""
    rename_map = {}
    for gid, group_rows in queued_groups.items():
        label_map = resolve_labels(group_rows)
        expr = group_rows[0]['expression']
        for sources, target in parse_expression(expr, label_map):
            for src in sources:
                rename_map[src] = target
    return rename_map

def find_names_in_file(dat_path):
    """Returns set of all distinct name fields in the dat file."""
    names = set()
    with open(dat_path, encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if stripped and ';' in stripped:
                names.add(stripped.split(';')[0].strip())
    return names

def check_collisions(rename_map, source_names_per_group, file1_names, file2_names):
    """
    Warn only when a target is a new name (not a variant from the same group)
    and already exists in one of the files.
    source_names_per_group: dict of gid -> set of all variant names in that group.
    """
    # Build set of all names that are known group variants (safe merge targets)
    all_group_names = set()
    for names in source_names_per_group.values():
        all_group_names.update(names)

    warnings = []
    for src, tgt in rename_map.items():
        if tgt in all_group_names:
            continue  # merging into a known group variant — not a collision
        for label, name_set in [('file1', file1_names), ('file2', file2_names)]:
            if tgt in name_set:
                warnings.append(f"  COLLISION in {label}: '{src}' → '{tgt}' (new target name already exists — records will merge with an unrelated athlete)")
    return warnings

def apply_to_file(dat_path, rename_map, dry_run):
    """Applies rename_map to dat file in place. Returns count of changed lines."""
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
        while len(cols) < 6:
            cols.append('')
        if int(cols[0]) in group_ids:
            cols[5] = timestamp
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

    file1_names = find_names_in_file(args.file1)
    file2_names = find_names_in_file(args.file2)

    source_names_per_group = {gid: set(r['name'] for r in rows) for gid, rows in queued.items()}
    collisions = check_collisions(rename_map, source_names_per_group, file1_names, file2_names)
    if collisions:
        print("\nWARNINGS — new target name already exists in file (will merge with an unrelated athlete):")
        for w in collisions:
            print(w)

    if args.dry_run:
        print("\n[DRY RUN — no files written]")
        return

    epoch = int(time.time())
    for path in [args.file1, args.file2]:
        backup = f"{path}.{epoch}"
        shutil.copy2(path, backup)
        print(f"Backup: {backup}")

    f1_changed = apply_to_file(args.file1, rename_map, dry_run=False)
    f2_changed = apply_to_file(args.file2, rename_map, dry_run=False)
    print(f"\nApplied: {f1_changed} lines changed in file1, {f2_changed} in file2")

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    stamp_applied(args.tsv, set(queued.keys()), ts)
    print(f"Stamped {len(queued)} groups as applied at {ts}")

if __name__ == '__main__':
    main()
