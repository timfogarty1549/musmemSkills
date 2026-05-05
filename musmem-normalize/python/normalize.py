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

ROOT     = os.path.expanduser('~/workspace/musmem/data')
TSV_ROOT = os.path.expanduser('~/workspace/musmem/distinct')

FILE_DEFAULTS = [
    'bb_male.dat',
]

WIDE = '═' * 58
THIN = '─' * 58


def resolve_path(raw, root=None):
    if raw.startswith('/') or raw.startswith('~'):
        return os.path.expanduser(raw)
    return os.path.join(root or ROOT, raw)


def prompt_paths():
    files = []
    for i, default in enumerate(FILE_DEFAULTS, 1):
        full_default = resolve_path(default)
        raw = input(f'File {i} [{full_default}]: ').strip()
        files.append(resolve_path(raw) if raw else full_default)

    n = len(FILE_DEFAULTS) + 1
    while True:
        raw = input(f'File {n} (blank to finish): ').strip()
        if not raw:
            break
        files.append(resolve_path(raw))
        n += 1

    tsv_files = sorted(
        f for f in os.listdir(TSV_ROOT) if f.endswith('.tsv')
    ) if os.path.isdir(TSV_ROOT) else []

    if tsv_files:
        print(f'TSV files in {TSV_ROOT}/:')
        for i, name in enumerate(tsv_files, 1):
            print(f'  {i}. {name}')

    while True:
        raw = input(f'TSV    ({TSV_ROOT}/): ').strip()
        if not raw:
            continue
        if tsv_files and raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(tsv_files):
                tsv = os.path.join(TSV_ROOT, tsv_files[idx])
                break
            print(f'  Enter a number between 1 and {len(tsv_files)}.')
        else:
            tsv = resolve_path(raw, TSV_ROOT)
            break

    return files, tsv


# ── expression parsing ─────────────────────────────────────────────────────────

def _split_expressions(expr):
    parts, current, depth, in_quote = [], [], 0, False
    for ch in expr:
        if ch == '"':
            in_quote = not in_quote
        elif ch == '[' and not in_quote:
            depth += 1
        elif ch == ']' and not in_quote:
            depth -= 1
        elif ch == ',' and depth == 0 and not in_quote:
            parts.append(''.join(current).strip())
            current = []
            continue
        current.append(ch)
    if current:
        parts.append(''.join(current).strip())
    return [p for p in parts if p]


def _resolve_target(raw, label_map):
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    return label_map.get(raw)


def _parse_renames(expr, label_map):
    renames = {}
    for part in _split_expressions(expr):
        m = re.match(r'^\[([^\]]+)\]\s*=\s*(.+)$', part)
        if m:
            labels = [l.strip() for l in m.group(1).split(',')]
            target = _resolve_target(m.group(2), label_map)
            if target:
                for lbl in labels:
                    if lbl in label_map:
                        renames[label_map[lbl]] = target
            continue
        m2 = re.match(r'^([a-z])\s*=\s*(.+)$', part)
        if m2:
            target = _resolve_target(m2.group(2), label_map)
            if target and m2.group(1) in label_map:
                renames[label_map[m2.group(1)]] = target
    return renames


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


FILE_COLORS = [
    '\033[32m',   # f1: green
    '\033[33m',   # f2: yellow
    '\033[35m',   # f3: magenta
    '\033[36m',   # f4: cyan
    '\033[34m',   # f5+: blue
]
RESET = '\033[0m'


def expand_group(data):
    all_records = []
    for v in data['variants']:
        for r in v['records']:
            all_records.append((r['file'], r['line']))
    def _sort_key(rec):
        parts = rec[1].split(';')
        year    = parts[1].strip() if len(parts) > 1 else ''
        contest = parts[2].strip() if len(parts) > 2 else ''
        return (year, contest)

    all_records.sort(key=_sort_key)

    print()
    for file_tag, line in all_records:
        fi = int(file_tag[1:]) - 1  # 'f1' -> 0, 'f2' -> 1, etc.
        color = FILE_COLORS[min(fi, len(FILE_COLORS) - 1)]
        print(f'{color}[{file_tag}] {line}{RESET}')
    print()


def _fmt_counts(counts):
    parts = [f'f{i+1}:{n}' for i, n in enumerate(counts) if n > 0]
    return '[' + ', '.join(parts) + ']'


def display_group(data):
    gid      = data['group_id']
    variants = data['variants']
    pending  = data['pending_remaining']
    total    = sum(sum(v['counts']) for v in variants)
    n        = len(variants)

    print()
    print(WIDE)
    print(f'Group {gid}  ({n} variant{"s" if n != 1 else ""}, {total} record{"s" if total != 1 else ""})   [{pending} pending]')
    print(WIDE)

    rows, max_cnt = [], 0
    for v in variants:
        counts = _fmt_counts(v['counts'])
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

def load_group(tsv, files):
    rows = fg.load_tsv(tsv)
    gid, group_rows = fg.find_next_group(rows)
    if gid is None:
        return None

    pending = fg.count_pending(rows)
    names   = sorted(set(r['name'] for r in group_rows))
    recs_per_file = [fg.fetch_records(f, names) for f in files]

    variants = []
    for i, name in enumerate(names):
        label   = chr(ord('a') + i)
        records = []
        counts  = []
        for fi, recs in enumerate(recs_per_file):
            file_records = recs[name]
            records += [{'file': f'f{fi+1}', 'line': ln} for ln in file_records]
            counts.append(len(file_records))
        variants.append({
            'label':   label,
            'name':    name,
            'counts':  counts,
            'records': records,
        })

    return {'group_id': gid, 'pending_remaining': pending, 'variants': variants}


def count_queued(tsv):
    return len(ac.get_queued_groups(ac.load_tsv(tsv)))


# ── decision recording ─────────────────────────────────────────────────────────

def record_decision(tsv, group_id, rename_dict_or_special, all_names):
    with open(tsv, encoding='utf-8') as f:
        lines = f.read().splitlines(keepends=True)

    out = [lines[0]]
    for line in lines[1:]:
        cols = line.rstrip('\n').split('\t')
        while len(cols) < 6:
            cols.append('')
        if cols[0].strip() and int(cols[0]) == group_id:
            name = cols[1]
            if isinstance(rename_dict_or_special, str):
                cols[4] = rename_dict_or_special
            elif name in rename_dict_or_special:
                cols[4] = rename_dict_or_special[name]
            else:
                cols[4] = '-'
        out.append('\t'.join(cols) + '\n')

    with open(tsv, 'w', encoding='utf-8') as f:
        f.writelines(out)


# ── collision check ────────────────────────────────────────────────────────────

def _collisions_in_expr(expr, files):
    result = []
    for name in re.findall(r'"([^"]+)"', expr):
        found = [f'f{i+1}' for i, f in enumerate(files)
                 if col_check.name_exists_in_file(f, name)]
        if found:
            result.append((name, found))
    return result


def resolve_expression(expr, files):
    while True:
        collisions = _collisions_in_expr(expr, files)
        if not collisions:
            return expr
        for name, found in collisions:
            print(f"WARNING: '{name}' already exists in {', '.join(found)}")
        resp = input('Proceed anyway? (yes / enter new expression): ').strip()
        if resp.lower() == 'yes':
            return expr
        if resp:
            expr = resp
        else:
            return None


# ── apply corrections ──────────────────────────────────────────────────────────

def run_apply(tsv, files):
    rows   = ac.load_tsv(tsv)
    queued = ac.get_queued_groups(rows)

    if not queued:
        print("No queued corrections to apply.")
        return

    rename_map = ac.build_rename_map(queued)
    print(f"\nRename map ({len(rename_map)} entries):")
    for src, tgt in sorted(rename_map.items()):
        print(f"  '{src}' → '{tgt}'")

    file_names_list = [ac.find_names_in_file(f) for f in files]
    src_names = {gid: set(r['name'] for r in grows) for gid, grows in queued.items()}
    warnings  = ac.check_collisions(rename_map, src_names, file_names_list)
    if warnings:
        print("\nWARNINGS:")
        for w in warnings:
            print(w)

    epoch = int(time.time())
    for path in files:
        backup = f'{path}.{epoch}'
        shutil.copy2(path, backup)
        print(f"Backup: {backup}")

    changed = []
    for i, path in enumerate(files):
        n = ac.apply_to_file(path, rename_map, dry_run=False)
        changed.append(f'f{i+1}: {n}')
    print(f"\nApplied: {', '.join(changed)} lines changed")

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    ac.stamp_applied(tsv, set(queued.keys()), ts)
    print(f"Stamped {len(queued)} groups as applied at {ts}")


# ── main loop ──────────────────────────────────────────────────────────────────

PROMPT = 'Expression (s)kip / defer / process / (q)uit / (e)xpand: '


def main():
    files, tsv = prompt_paths()

    while True:
        data = load_group(tsv, files)

        if data is None:
            queued = count_queued(tsv)
            print()
            print(f'No more pending groups. {queued} queued correction(s) not yet applied.')
            print("Enter 'process' to apply queued corrections, or 'quit' to stop.")
            while True:
                cmd = input('> ').strip().lower()
                if cmd == 'process':
                    run_apply(tsv, files)
                    break
                elif cmd in ('quit', 'exit'):
                    return
                else:
                    print("  Enter 'process' or 'quit'.")
            continue

        display_group(data)
        all_names = [v['name'] for v in data['variants']]
        label_map = {v['label']: v['name'] for v in data['variants']}

        while True:
            raw = input(PROMPT).strip()
            if not raw:
                continue
            lo = raw.lower()

            if lo in ('skip', 's'):
                record_decision(tsv, data['group_id'], 'skip', all_names)
                break

            elif lo == 'defer':
                record_decision(tsv, data['group_id'], 'defer', all_names)
                break

            elif lo in ('quit', 'exit', 'q'):
                queued = count_queued(tsv)
                print(f'{queued} queued correction(s) not yet applied.')
                return

            elif lo == 'process':
                run_apply(tsv, files)
                break

            elif lo in ('expand', 'e'):
                expand_group(data)
                display_group(data)

            else:
                expr = resolve_expression(raw, files)
                if expr is None:
                    continue
                rename_dict = _parse_renames(expr, label_map)
                if not rename_dict:
                    print('  Could not parse expression. Try again.')
                    continue
                record_decision(tsv, data['group_id'], rename_dict, all_names)
                break


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        sys.exit(0)
