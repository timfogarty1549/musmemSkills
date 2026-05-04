#!/usr/bin/env python3
"""
record_decision.py — writes expression to TSV for all rows in a group.

Usage:
    python3 record_decision.py --tsv PATH --group-id N --expression TEXT
"""
import argparse

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--tsv', required=True)
    p.add_argument('--group-id', type=int, required=True)
    p.add_argument('--expression', required=True)
    return p.parse_args()

def main():
    args = parse_args()

    with open(args.tsv, encoding='utf-8') as f:
        lines = f.read().splitlines(keepends=True)

    header = lines[0]
    out_lines = [header]
    updated = 0

    for line in lines[1:]:
        cols = line.rstrip('\n').split('\t')
        while len(cols) < 6:
            cols.append('')
        if int(cols[0]) == args.group_id:
            cols[4] = args.expression
            updated += 1
        out_lines.append('\t'.join(cols) + '\n')

    with open(args.tsv, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

    print(f"Updated {updated} rows for group {args.group_id} with expression: {args.expression!r}")

if __name__ == '__main__':
    main()
