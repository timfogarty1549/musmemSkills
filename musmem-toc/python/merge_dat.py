"""
merge_dat.py — Merge per-issue .dat files back into a monolithic .dat file.

Usage:
    python3 merge_dat.py {mag}    # merge one magazine
    python3 merge_dat.py all      # merge all magazines that have a per-issue folder

Reads:  ~/workspace/musmem/toc/{mag}/*.dat
Writes: ~/workspace/musmem/toc/{mag}.dat  (sorted alphanumerically by issue then page)

Sort order: year → month (numeric) → volume → issue → magazine page (numeric where possible)
"""

import sys
import os

TOC_DIR = os.path.expanduser('~/workspace/musmem/toc')


def page_sort_key(page_str):
    """
    Convert a magazine page string to a sortable value.
    Numeric pages sort numerically; non-numeric (e.g. 'sup-1') sort before page 1.
    """
    try:
        return (1, int(page_str.strip()))
    except (ValueError, AttributeError):
        return (0, page_str.strip())


def line_sort_key(line):
    """Return a sort tuple for a .dat line."""
    parts = line.rstrip('\n').split('\t')
    try:
        year  = int(parts[1])
        month = abs(int(parts[2]))
        vol   = int(parts[3])
        issue = int(parts[4])
    except (IndexError, ValueError):
        return (0, 0, 0, 0, (1, 0))
    page = parts[7] if len(parts) > 7 else ''
    return (year, month, vol, issue, page_sort_key(page))


def merge_mag(mag):
    src_dir = os.path.join(TOC_DIR, mag)
    if not os.path.isdir(src_dir):
        print(f'  SKIP: {src_dir}/ not found')
        return

    lines = []
    for fname in sorted(os.listdir(src_dir)):
        if not fname.endswith('.dat'):
            continue
        with open(os.path.join(src_dir, fname), encoding='latin-1') as f:
            for line in f:
                if line.strip():
                    lines.append(line if line.endswith('\n') else line + '\n')

    if not lines:
        print(f'  SKIP: no lines found in {src_dir}/')
        return

    lines.sort(key=line_sort_key)

    out_path = os.path.join(TOC_DIR, f'{mag}.dat')
    with open(out_path, 'w', encoding='latin-1') as f:
        f.writelines(lines)

    print(f'  {mag}: {len(lines)} rows written to {out_path}')


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 merge_dat.py {mag|all}')
        sys.exit(1)

    arg = sys.argv[1]
    if arg == 'all':
        mags = sorted(
            d for d in os.listdir(TOC_DIR)
            if os.path.isdir(os.path.join(TOC_DIR, d)) and not d.startswith('.')
        )
    else:
        mags = [arg]

    for mag in mags:
        merge_mag(mag)


if __name__ == '__main__':
    main()
