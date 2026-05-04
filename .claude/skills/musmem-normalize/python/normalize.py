#!/usr/bin/env python3
"""
normalize.py — interactive loop for reviewing name variant groups.

Usage: python3 normalize.py
"""

import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fetch_group as fg
import check_collision as col_check
import apply_corrections as ac

DEFAULTS = {
    'file1': '~/workspace/musmem/data/bb_male.dat',
    'file2': '~/workspace/musmem/data/prelim/covid-male.dat',
    'tsv':   '~/workspace/musmem/data/prelim/bb2010-covid-male-variant-groups.tsv',
}

WIDE  = '═' * 58
THIN  = '─' * 58


def prompt_paths():
    paths = {}
    for key, label in [('file1', 'File 1'), ('file2', 'File 2'), ('tsv', 'TSV   ')]:
        default = DEFAULTS[key]
        raw = input(f'{label} [{default}]: ').strip()
        paths[key] = os.path.expanduser(raw if raw else default)
    return paths['file1'], paths['file2'], paths['tsv']


# ── display helpers ────────────────────────────────────────────────────────────

def _parse_years(records):
    years = []
    for r in records:
        parts = r['line'].split(';')
        if len(parts) >= 2:
            try:
                years.append(int(parts[1].strip()))
            except ValueError:
                pass
    if not years:
        return ''
    lo, hi = min(years), max(years)
    return str(lo) if lo == hi else f'{lo}–{hi}'


def _parse_orgs(records):
    seen, result = set(), []
    for r in records:
        parts = r['line'].split(';')
        if len(parts) >= 3 and ' - ' in parts[2]:
            org = parts[2].rsplit(' - ', 1)[1].strip()
            if org and org not in seen:
                seen.add(org)
                result.append(org)
    return ', '.join(result)


def _parse_divisions(records):
    seen, result = set(), []
    for r in records:
        parts = r['line'].split(';')
        if len(parts) >= 4:
            dp = parts[3].strip()
            div = dp.split('-')[0].strip() if '-' in dp else dp
            if div and div not in seen:
                seen.add(div)
                result.append(div)
    return ', '.join(result)


def _parse_countries(records):
    seen, result = set(), []
    for r in records:
        for m in re.finditer(r'c=([A-Z]{2})', r['line']):
            c = m.group(1)
            if c not in seen:
                seen.add(c)
                result.append(c)
    return ', '.join(result)


def _fmt_counts(f1, f2):
    parts = []
    if f1:
        parts.append(f'f1:{f1}')
    if f2:
        parts.append(f'f2:{f2}')
    return '[' + ', '.join(parts) + ']'


def display_group(data):
    gid      = data['group_id']
    variants = data['variants']
    pending  = data['pending_remaining']
    total    = sum(v['count_file1'] + v['count_file2'] for v in variants)
    n        = len(variants)

    print()
    print(WIDE)
    print(f'Group {gid}  ({n} variant{"s" if n != 1 else ""}, {total} record{"s" if total != 1 else ""})   [{pending} pending]')
    print(WIDE)

    rows = []
    max_cnt = 0
    for v in variants:
        counts = _fmt_counts(v['count_file1'], v['count_file2'])
        rows.append((
            v['label'], v['name'], counts,
            _parse_years(v['records']),
            _parse_orgs(v['records']),
            _parse_divisions(v['records']),
            _parse_countries(v['records']),
        ))
        max_cnt = max(max_cnt, len(counts))

    for label, name, counts, years, orgs, divs, ctrs in rows:
        line = f'{label}  {name:<35} {counts:<{max_cnt}}'
        for val in (years, orgs, divs, ctrs):
            if val:
                line += f'  {val}'
        print(line)

    print(THIN)


# ── data loading ───────────────────────────────────────────────────────────────

def load_group(tsv, file1, file2):
    """Return group data dict, or None if no pending groups remain."""
    rows = fg.load_tsv(tsv)
    gid, group_rows = fg.find_next_group(rows)
    if gid is None:
        return None

    pending = fg.count_pending(rows)
    names   = sorted(set(r['name'] for r in group_rows))
    f1_recs = fg.fetch_records(file1, names)
    f2_recs = fg.fetch_records(file2, names)

    variants = []
    for i, name in enumerate(names):
        label   = chr(ord('a') + i)
        records = (
            [{'file': 'file1', 'line': ln} for ln in f1_recs[name]] +
            [{'file': 'file2', 'line': ln} for ln in f2_recs[name]]
        )
        variants.append({
            'label':      label,
            'name':       name,
            'count_file1': len(f1_recs[name]),
            'count_file2': len(f2_recs[name]),
            'records':    records,
        })

    return {'group_id': gid, 'pending_remaining': pending, 'variants': variants}


def count_queued(tsv):
    return len(ac.get_queued_groups(ac.load_tsv(tsv)))


# ── decision recording ─────────────────────────────────────────────────────────

def record_decision(tsv, group_id, expression):
    with open(tsv, encoding='utf-8') as f:
        lines = f.read().splitlines(keepends=True)
    out = [lines[0]]
    for line in lines[1:]:
        cols = line.rstrip('\n').split('\t')
        while len(cols) < 6:
            cols.append('')
        if cols[0].strip() and int(cols[0]) == group_id:
            cols[4] = expression
        out.append('\t'.join(cols) + '\n')
    with open(tsv, 'w', encoding='utf-8') as f:
        f.writelines(out)


# ── collision check ────────────────────────────────────────────────────────────

def _collisions_in_expr(expr, file1, file2):
    result = []
    for name in re.findall(r'"([^"]+)"', expr):
        found = []
        if col_check.name_exists_in_file(file1, name):
            found.append('file1')
        if col_check.name_exists_in_file(file2, name):
            found.append('file2')
        if found:
            result.append((name, found))
    return result


def resolve_expression(expr, file1, file2):
    """Return the final expression, or None if the user aborts."""
    while True:
        collisions = _collisions_in_expr(expr, file1, file2)
        if not collisions:
            return expr
        for name, files in collisions:
            print(f"WARNING: '{name}' already exists in {', '.join(files)}")
        resp = input('Proceed anyway? (yes / enter new expression): ').strip()
        if resp.lower() == 'yes':
            return expr
        if resp:
            expr = resp
        else:
            return None  # user entered nothing — abort


# ── apply corrections ──────────────────────────────────────────────────────────

def run_apply(tsv, file1, file2):
    rows   = ac.load_tsv(tsv)
    queued = ac.get_queued_groups(rows)

    if not queued:
        print("No queued corrections to apply.")
        return

    rename_map = ac.build_rename_map(queued)
    print(f"\nRename map ({len(rename_map)} entries):")
    for src, tgt in sorted(rename_map.items()):
        print(f"  '{src}' → '{tgt}'")

    file1_names = ac.find_names_in_file(file1)
    file2_names = ac.find_names_in_file(file2)
    src_names   = {gid: set(r['name'] for r in grows) for gid, grows in queued.items()}
    warnings    = ac.check_collisions(rename_map, src_names, file1_names, file2_names)
    if warnings:
        print("\nWARNINGS:")
        for w in warnings:
            print(w)

    epoch = int(time.time())
    for path in (file1, file2):
        backup = f'{path}.{epoch}'
        shutil.copy2(path, backup)
        print(f"Backup: {backup}")

    f1 = ac.apply_to_file(file1, rename_map, dry_run=False)
    f2 = ac.apply_to_file(file2, rename_map, dry_run=False)
    print(f"\nApplied: {f1} lines changed in file1, {f2} in file2")

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    ac.stamp_applied(tsv, set(queued.keys()), ts)
    print(f"Stamped {len(queued)} groups as applied at {ts}")


# ── main loop ──────────────────────────────────────────────────────────────────

PROMPT = 'Expression (skip / defer / process / quit / expand <label>): '


def main():
    file1, file2, tsv = prompt_paths()

    while True:
        data = load_group(tsv, file1, file2)

        if data is None:
            queued = count_queued(tsv)
            print()
            print(f'No more pending groups. {queued} queued correction(s) not yet applied.')
            print("Enter 'process' to apply queued corrections, or 'quit' to stop.")
            while True:
                cmd = input('> ').strip().lower()
                if cmd == 'process':
                    run_apply(tsv, file1, file2)
                    break
                elif cmd in ('quit', 'exit'):
                    return
                else:
                    print("  Enter 'process' or 'quit'.")
            continue

        display_group(data)

        while True:
            raw = input(PROMPT).strip()
            if not raw:
                continue
            lo = raw.lower()

            if lo == 'skip':
                record_decision(tsv, data['group_id'], 'skip')
                break

            elif lo == 'defer':
                record_decision(tsv, data['group_id'], 'defer')
                break

            elif lo in ('quit', 'exit'):
                queued = count_queued(tsv)
                print(f'{queued} queued correction(s) not yet applied.')
                return

            elif lo == 'process':
                run_apply(tsv, file1, file2)
                break

            elif lo.startswith('expand '):
                label = raw[7:].strip()
                for v in data['variants']:
                    if v['label'] == label:
                        print()
                        for r in v['records']:
                            print(f'  [{r["file"]}] {r["line"]}')
                        break
                else:
                    print(f'  Unknown label: {label!r}')
                display_group(data)

            else:
                expr = resolve_expression(raw, file1, file2)
                if expr is not None:
                    record_decision(tsv, data['group_id'], expr)
                    break


if __name__ == '__main__':
    main()
