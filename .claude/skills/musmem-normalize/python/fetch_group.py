#!/usr/bin/env python3
"""
fetch_group.py — reads next pending group and its records from both dat files.

Usage:
    python3 fetch_group.py --tsv PATH --file1 PATH --file2 PATH [--group-id N]

Output: JSON to stdout, or 'null' if no pending groups remain.
"""
import argparse, json, sys

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--tsv', required=True)
    p.add_argument('--file1', required=True)
    p.add_argument('--file2', required=True)
    p.add_argument('--group-id', type=int, default=None)
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

def group_is_pending(group_rows):
    expr = group_rows[0]['expression']
    return expr == '' or expr == 'defer'

def find_next_group(rows, target_id=None):
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
    names = sorted(set(r['name'] for r in group_rows))

    file1_records = fetch_records(args.file1, names)
    file2_records = fetch_records(args.file2, names)

    variants = []
    for i, name in enumerate(names):
        label = chr(ord('a') + i)
        records = (
            [{'file': 'file1', 'line': ln} for ln in file1_records[name]] +
            [{'file': 'file2', 'line': ln} for ln in file2_records[name]]
        )
        variants.append({
            'label': label,
            'name': name,
            'count_file1': len(file1_records[name]),
            'count_file2': len(file2_records[name]),
            'records': records,
        })

    print(json.dumps({
        'group_id': gid,
        'pending_remaining': pending_remaining,
        'variants': variants,
    }, ensure_ascii=False))

if __name__ == '__main__':
    main()
