"""
split_dat.py — Split a monolithic magazine .dat file into per-issue files.

Usage:
    python3 split_dat.py {mag}           # split one magazine
    python3 split_dat.py all             # split all magazines with a .dat file

Output: ~/workspace/musmem/toc/{mag}/{filename}.dat
  - One file per issue
  - Filename derived from naming convention (see SKILL.md)

Naming convention:
  Year+month mags (sh, mb, mma, mtis, rpj):  {mag}{YYYY}{MM:02d}.dat
  Vol=0 mags (3-digit issue):                 {mag}{NNN:03d}.dat
  All others (vol > 0):                       {mag}{VV:02d}{NN:02d}.dat
"""

import sys
import os
import collections

TOC_DIR = os.path.expanduser('~/workspace/musmem/toc')

# Magazines that use year+month for filenames
YEAR_MONTH_MAGS = {'sh', 'mb', 'mma', 'mtis', 'rpj'}


def issue_filename(mag, year, month, vol, issue):
    """Return the per-issue filename (without directory) for the given issue."""
    if mag in YEAR_MONTH_MAGS:
        return f'{mag}{int(year):04d}{abs(int(month)):02d}.dat'
    elif int(vol) == 0:
        return f'{mag}{int(issue):03d}.dat'
    else:
        return f'{mag}{int(vol):02d}{int(issue):02d}.dat'


def split_mag(mag):
    src = os.path.join(TOC_DIR, f'{mag}.dat')
    if not os.path.exists(src):
        print(f'  SKIP: {src} not found')
        return

    with open(src, encoding='latin-1') as f:
        lines = [l.rstrip('\n') for l in f if l.strip()]

    # Group lines by issue key (preserving order)
    groups = collections.OrderedDict()
    skipped = 0
    for line in lines:
        cols = line.split('\t')
        if len(cols) < 5:
            skipped += 1
            continue
        year, month, vol, issue = cols[1], cols[2], cols[3], cols[4]
        try:
            fname = issue_filename(mag, year, month, vol, issue)
        except (ValueError, TypeError):
            skipped += 1
            continue
        # Reorder columns: insert empty col 9 (PDF range) at index 8,
        # moving the text-file flag from index 8 to index 9 (col 10).
        # Exception: 9-col TOC locator rows have pdf_page at index 8 (not a text flag);
        # those should keep pdf_page at index 8 and get empty text flag appended.
        parts = line.split('\t')
        is_toc_row = (len(parts) > 5 and parts[5].strip() == 'Table of Contents')
        if len(parts) == 8:
            parts += ['', '']          # add empty range + empty flag
        elif len(parts) == 9:
            if is_toc_row:
                parts += ['']          # pdf_page stays at index 8; append empty text flag
            else:
                parts = parts[:8] + ['', parts[8]]  # insert empty range before flag
        # len >= 10: already in new format, leave as-is
        groups.setdefault(fname, []).append('\t'.join(parts))

    out_dir = os.path.join(TOC_DIR, mag)
    os.makedirs(out_dir, exist_ok=True)

    written = 0
    for fname, issue_lines in groups.items():
        out_path = os.path.join(out_dir, fname)
        with open(out_path, 'w', encoding='latin-1') as f:
            f.write('\n'.join(issue_lines) + '\n')
        written += 1

    print(f'  {mag}: {written} issues written to {out_dir}/'
          + (f', {skipped} lines skipped' if skipped else ''))


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 split_dat.py {mag|all}')
        sys.exit(1)

    arg = sys.argv[1]
    if arg == 'all':
        mags = [
            f[:-4] for f in os.listdir(TOC_DIR)
            if f.endswith('.dat') and os.path.isfile(os.path.join(TOC_DIR, f))
        ]
        mags.sort()
    else:
        mags = [arg]

    for mag in mags:
        split_mag(mag)


if __name__ == '__main__':
    main()
