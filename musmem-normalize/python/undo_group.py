#!/usr/bin/env python3
"""
undo_group.py — reverts one group's decision (skip / defer / rename) back to
pending in the TSV.

Only allowed when the group has not yet been applied to the .dat file(s)
(column 4, 'applied', is blank for all its rows). A group that was already
applied must be fixed manually — this script refuses rather than guessing
which .dat lines to revert.

Usage:
    python3 undo_group.py --tsv PATH --group-id N
"""
import argparse


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--tsv', required=True)
    p.add_argument('--group-id', type=int, required=True)
    return p.parse_args()


def load_lines(tsv):
    with open(tsv, encoding='utf-8') as f:
        return f.read().splitlines(keepends=True)


def undo_group(tsv, group_id):
    """Clears the expression column for group_id, if safe to do so.

    Returns (status, detail):
      'not_found'       — no rows for this group_id; detail is None
      'already_pending' — expression already blank for all rows; detail is None
      'applied'         — group was already applied; detail is the applied timestamp
      'reverted'        — expression cleared; detail is the sorted set of prior values
    """
    lines = load_lines(tsv)
    out = []
    header_done = False
    group_rows = []
    row_indices = []

    for line in lines:
        if not header_done:
            out.append(line)
            if not line.startswith('#'):
                header_done = True
            continue
        cols = line.rstrip('\n').split('\t')
        while len(cols) < 4:
            cols.append('')
        if cols[0].strip() and int(cols[0]) == group_id:
            group_rows.append(cols)
            row_indices.append(len(out))
        out.append('\t'.join(cols) + '\n')

    if not group_rows:
        return 'not_found', None

    applied_ts = next((cols[3].strip() for cols in group_rows if cols[3].strip()), None)
    if applied_ts:
        return 'applied', applied_ts

    prev = sorted({cols[2].strip() for cols in group_rows if cols[2].strip()})
    if not prev:
        return 'already_pending', None

    for idx, cols in zip(row_indices, group_rows):
        cols[2] = ''
        out[idx] = '\t'.join(cols) + '\n'

    with open(tsv, 'w', encoding='utf-8') as f:
        f.writelines(out)

    return 'reverted', prev


def main():
    args = parse_args()
    status, detail = undo_group(args.tsv, args.group_id)
    if status == 'not_found':
        print(f"Group {args.group_id} not found in {args.tsv}.")
    elif status == 'already_pending':
        print(f"Group {args.group_id} has no decision recorded; already pending.")
    elif status == 'applied':
        print(
            f"Group {args.group_id} was already applied at {detail} — "
            "cannot undo automatically. Fix the .dat file(s) manually if needed."
        )
    elif status == 'reverted':
        print(f"Group {args.group_id} reverted to pending (was: {', '.join(detail or [])}).")


if __name__ == '__main__':
    main()
