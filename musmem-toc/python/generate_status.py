"""
generate_status.py — Generate TOC_STATUS.html with magazine issue status tables.

For each magazine, produces a grid table where:
  Rows = volume (or year for year+month magazines)
  Cols = issue number (or month)

Cell appearance:
  Background #ccddcc = own 1 copy
  Background #ccccdd = own 2+ copies
  No background     = not owned
  ✓  = TOC entered (articles in local .dat or API)
  R  = all article page ranges filled; r = partially filled
  📄 = PDF exists on disk
  📝 = article text file exists on website (col 10 = 1)

Run: python3 generate_status.py
Output: ~/workspace/musmem/toc/TOC_STATUS.html
"""

import os
import json
import urllib.request
import urllib.parse
import re
from html import escape

TOC_DIR  = os.path.expanduser('~/workspace/musmem/toc')
PDF_BASE = os.path.expanduser('~/workspace/s3/musmem/magPdfs')
OUT_FILE = os.path.join(TOC_DIR, 'TOC_STATUS.html')
API_BASE = 'https://musclememory.org/api/mags'

YEAR_MONTH_MAGS = {'sh', 'mb', 'mma', 'mtis', 'rpj'}

MONTH_ABBR = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# (code, api_title or None, display_name)
MAG_LIST = [
    ('im',   'IronMan',                     'IronMan'),
    ('sh',   'Strength & Health',           'Strength &amp; Health'),
    ('mb',   'Muscle Builder',              'Muscle Builder'),
    ('md',   'Muscular Development',        'Muscular Development'),
    ('mp',   'Muscle Power',                'Muscle Power'),
    ('yp',   'Your Physique',               'Your Physique'),
    ('ma',   'Mr America',                  'Mr America'),
    ('jma',  'Junior Mr America',           'Junior Mr America'),
    ('mti',  'Muscle Training Illustrated', 'Muscle Training Illustrated'),
    ('mp2',  None,                          'Muscle Power (reused numbers)'),
    ('ma2',  None,                          'Mr America (reused numbers)'),
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def fetch_api_issues(api_title):
    """Fetch issue list from API. Returns list of issue dicts, or [] on error."""
    url = f'{API_BASE}?title={urllib.parse.quote(api_title)}&brief=true'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        return data.get('data', {}).get('issues', [])
    except Exception as e:
        print(f'  WARNING: API error for {api_title!r}: {e}')
        return []


def load_dat(mag):
    """
    Read per-issue .dat files for mag (from ~/workspace/musmem/toc/{mag}/).
    Returns dict: issue_key -> {rows, ranges_filled, ranges_total, has_text}

    Per-issue file column layout (0-indexed):
      [0] Magazine Name  [1] Year  [2] Month  [3] Volume  [4] Issue
      [5] Title  [6] Author  [7] Mag Page  [8] PDF range  [9] Text-file flag
    """
    per_issue_dir = os.path.join(TOC_DIR, mag)
    if not os.path.isdir(per_issue_dir):
        return {}

    result = {}
    for fname in os.listdir(per_issue_dir):
        if not fname.endswith('.dat'):
            continue
        path = os.path.join(per_issue_dir, fname)
        with open(path, encoding='latin-1') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                cols = line.split('\t')
                if len(cols) < 6:
                    continue
                try:
                    year  = int(cols[1])
                    month = int(cols[2])
                    vol   = int(cols[3])
                    issue = int(cols[4])
                except ValueError:
                    continue

                title      = cols[5].strip()
                pdf_range  = cols[8].strip() if len(cols) > 8 else ''
                text_flag  = cols[9].strip() if len(cols) > 9 else ''

                key = (year, abs(month)) if mag in YEAR_MONTH_MAGS else (vol, issue)
                if key not in result:
                    result[key] = {'rows': 0, 'ranges_filled': 0,
                                   'ranges_total': 0, 'has_text': False}

                result[key]['rows'] += 1
                if text_flag == '1':
                    result[key]['has_text'] = True

                if title.lower() == 'table of contents':
                    continue

                result[key]['ranges_total'] += 1
                if pdf_range:
                    result[key]['ranges_filled'] += 1

    return result


def load_pdf_keys(mag):
    """Scan the PDF directory for mag. Returns set of issue keys with a PDF on disk."""
    pdf_dir = os.path.join(PDF_BASE, mag)
    if not os.path.isdir(pdf_dir):
        return set()

    keys = set()
    for fname in os.listdir(pdf_dir):
        if not fname.lower().endswith('.pdf'):
            continue
        stem = fname[:-4]

        if mag in YEAR_MONTH_MAGS:
            m = re.match(rf'^{re.escape(mag)}(\d{{2}})(\d{{2}})$', stem, re.IGNORECASE)
            if m:
                yy, mm = int(m.group(1)), int(m.group(2))
                year = 1900 + yy if yy >= 30 else 2000 + yy
                keys.add((year, mm))
        else:
            m = re.match(rf'^{re.escape(mag)}(\d{{2}})(\d{{2}})$', stem, re.IGNORECASE)
            if m:
                keys.add((int(m.group(1)), int(m.group(2))))

    return keys


def api_issue_key(iss, mag):
    if mag in YEAR_MONTH_MAGS:
        return (iss['year'], abs(iss['month']))
    else:
        return (iss['volume'], iss['issue'])


# ---------------------------------------------------------------------------
# Cell rendering
# ---------------------------------------------------------------------------

def issue_stem(mag, key, use_ym):
    """Return the file stem for a given issue key (e.g. 'im2401', 'sh4801', 'mti024')."""
    if use_ym:
        year, month = key
        yy = year % 100
        return f'{mag}{yy:02d}{abs(month):02d}'
    elif key[0] == 0:   # vol=0 → 3-digit issue
        return f'{mag}{key[1]:03d}'
    else:
        vol, iss = key
        return f'{mag}{vol:02d}{iss:02d}'


def range_char(dat_info):
    if not dat_info:
        return ''
    total  = dat_info['ranges_total']
    filled = dat_info['ranges_filled']
    if total == 0:
        return ''
    if filled == total:
        return 'R'
    if filled > 0:
        return 'r'
    return ''


def make_cell(own_count, toc, rng, pdf, text_file, stem=''):
    if own_count == 1:
        bg = ' style="background:#ccddcc"'
    elif own_count >= 2:
        bg = ' style="background:#ccccdd"'
    else:
        bg = ' style="background:#fff4ff"'

    title_attr = f' data-tip="{escape(stem)}"' if stem else ''

    parts = []
    if toc:
        parts.append('✓')
    if rng == 'R':
        parts.append('R')
    elif rng == 'r':
        parts.append('<span style="color:#999">r</span>')
    if pdf:
        parts.append('<span class="badge badge-pdf">PDF</span>')
    if text_file:
        parts.append('<span class="badge badge-text">TXT</span>')

    content = ''.join(parts) if parts else '&nbsp;'
    return f'<td{bg}{title_attr}>{content}</td>'


EMPTY_CELL = '<td></td>'


# ---------------------------------------------------------------------------
# Table building
# ---------------------------------------------------------------------------

def build_section_html(mag, api_issues, dat, pdf_keys, display_name):
    use_ym = mag in YEAR_MONTH_MAGS

    own_map     = {}   # key -> int (count)
    api_toc_map = {}   # key -> bool
    all_keys    = set()

    for iss in api_issues:
        try:
            key = api_issue_key(iss, mag)
        except (KeyError, TypeError, ValueError):
            continue
        all_keys.add(key)
        own_map[key]     = iss.get('own', 0)
        toc_val          = iss.get('toc')
        api_toc_map[key] = bool(toc_val)

    all_keys.update(dat.keys())

    lines = [f'<h2>{display_name}</h2>']

    if not all_keys:
        lines.append('<p><em>No data found.</em></p>')
        return '\n'.join(lines)

    lines.append('<table>')

    def cell_for(key):
        if key not in all_keys:
            return EMPTY_CELL
        own   = own_map.get(key, 0)
        toc   = api_toc_map.get(key, False) or (dat.get(key, {}).get('rows', 0) > 0)
        rng   = range_char(dat.get(key))
        pdf   = key in pdf_keys
        txt   = dat.get(key, {}).get('has_text', False)
        stem  = issue_stem(mag, key, use_ym)
        return make_cell(own, toc, rng, pdf, txt, stem)

    if use_ym:
        years  = sorted(set(k[0] for k in all_keys))
        months = list(range(1, 13))
        if any(k[1] == 0 for k in all_keys):
            months = [0] + months

        header_cells = '<th>Year</th>' + ''.join(
            f'<th>{"00" if m == 0 else MONTH_ABBR[m]}</th>' for m in months
        )
        lines.append(f'<tr>{header_cells}</tr>')

        for year in years:
            row = f'<th>{year}</th>'
            for month in months:
                row += cell_for((year, month))
            lines.append(f'<tr>{row}</tr>')

    else:
        vols      = sorted(set(k[0] for k in all_keys))
        max_issue = max(k[1] for k in all_keys)
        issue_nums = list(range(1, max_issue + 1))

        if vols == [0]:
            # 3-digit issue magazines: group into rows of 10
            GROUP  = 10
            starts = list(range(1, max_issue + 1, GROUP))
            offsets = list(range(1, GROUP + 1))

            header_cells = '<th>Issues</th>' + ''.join(f'<th>{o}</th>' for o in offsets)
            lines.append(f'<tr>{header_cells}</tr>')

            for start in starts:
                end = min(start + GROUP - 1, max_issue)
                row = f'<th>{start}–{end}</th>'
                for offset in offsets:
                    row += cell_for((0, start + offset - 1))
                lines.append(f'<tr>{row}</tr>')

        else:
            header_cells = '<th>Vol</th>' + ''.join(f'<th>{i}</th>' for i in issue_nums)
            lines.append(f'<tr>{header_cells}</tr>')

            for vol in vols:
                row = f'<th>{vol}</th>'
                for iss_num in issue_nums:
                    row += cell_for((vol, iss_num))
                lines.append(f'<tr>{row}</tr>')

    lines.append('</table>')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

HTML_HEAD = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>TOC Status</title>
  <style>
    body { font-family: sans-serif; font-size: 13px; margin: 1em auto; max-width: 1400px; padding: 0 2em; }
    h1   { font-size: 1.4em; }
    h2   { font-size: 1.1em; margin-top: 2em; margin-bottom: 0.3em; color: #333; }
    .legend { margin: 0.5em 0 1.5em 0; font-size: 0.9em; }
    .legend span { display: inline-block; padding: 1px 10px; margin-right: 6px;
                   border: 1px solid #bbb; }
    table { border-collapse: collapse; margin-bottom: 0.5em; min-width: 800px; }
    th { background: #ddd; padding: 2px 5px; font-size: 0.8em;
         border: 1px solid #bbb; white-space: nowrap; }
    td { padding: 1px 3px; border: 1px solid #ddd; text-align: center;
         min-width: 2em; font-size: 0.85em; white-space: nowrap; }
    hr { border: none; border-top: 1px solid #ccc; margin: 2em 0 0 0; }
    .badge { display: inline-block; font-size: 0.7em; font-weight: bold;
             padding: 1px 4px; border-radius: 3px; color: #fff;
             vertical-align: middle; margin: 0 1px; }
    .badge-pdf  { background: #336699; }
    .badge-text { background: #4a7a4a; }
    td[data-tip] { position: relative; cursor: pointer; }
    td[data-tip]:hover::after {
      content: attr(data-tip);
      position: absolute;
      bottom: 50%;
      left: 50%;
      background: #222;
      color: #fff;
      padding: 2px 7px;
      border-radius: 3px;
      font-size: 11px;
      white-space: nowrap;
      z-index: 100;
      pointer-events: none;
    }
  </style>
</head>
<body>
<h1>TOC Status</h1>
<div class="legend">
  <span style="background:#ccddcc">own 1 copy</span>
  <span style="background:#ccccdd">own 2+ copies</span>
  <span style="background:#fff4ff">known, not owned</span>
  white = no issue published &nbsp;|&nbsp;
  ✓ TOC entered &nbsp; R ranges filled &nbsp;
  <span class="badge badge-pdf">PDF</span> PDF on disk &nbsp;
  <span class="badge badge-text">TXT</span> article text on website
</div>
<hr>
"""

HTML_FOOT = """\
</body>
</html>
"""


def main():
    sections = []
    for mag, api_title, display_name in MAG_LIST:
        print(f'Processing {mag}: {display_name}')
        api_issues = fetch_api_issues(api_title) if api_title else []
        dat        = load_dat(mag)
        pdf_keys   = load_pdf_keys(mag)
        sections.append(build_section_html(mag, api_issues, dat, pdf_keys, display_name))

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(HTML_HEAD)
        f.write('\n'.join(sections))
        f.write(HTML_FOOT)

    print(f'\nWritten: {OUT_FILE}')


if __name__ == '__main__':
    main()
