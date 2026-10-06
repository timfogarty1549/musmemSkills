#!/usr/bin/env python3
"""
Checks MuscleMemory contest results for missing placings within a division's
numeric sequence.

A division's placings should increment by 1 (1, 2, 3, 4, ...). Two
exceptions are not flagged as missing:
  1. Ties: if N athletes tie at a placing, that number repeats N times and
     the next (N-1) placings are skipped (e.g. 1, 2, 3, 3, 5, 6).
  2. Special placing codes 96-99 (DQ, unranked tie / "did not place", etc.)
     are excluded from the sequence check entirely, as is placing 0
     (overall-winner marker, which is not part of a numbered sequence).

A third case is reported separately rather than as a missing-placing gap:
sometimes an athlete's bib number gets entered as their placing by mistake.
A bib number is usually still <= 90, so it survives the filter above, but
it lands far past the next expected placing (e.g. sequence 1, 2, 3 then a
recorded placing of 45). Treating that 45 as real would fill "missing" with
every number from 4 to 44 — noise that drowns out the real, single missing
placing (4). Instead, any value that jumps more than --gap-threshold past
the currently expected placing is pulled out of the sequence and reported
under "Suspicious Placings" instead of being used to compute gaps.

Queries the local MuscleMemory server (localhost:3000) directly — this is a
read-only audit script, no files are written under 1-incoming/ etc.

Persistent tracking:
    Every run's findings are reconciled against a JSON state file (default
    placing_gaps_state_<org>.json next to this script — kept separate per
    org so an NPC run can't mark IFBB-only issues "fixed" and vice versa).
    Each discrepancy is identified by (type, division, gender, explanation):
      - Not seen before -> appended with dateFound/lastChecked = now,
        resolution = "".
      - Seen again with the same explanation -> lastChecked updated. If it
        had been auto-marked "fixed" but reappeared, resolution is reopened
        (reset to "").
      - Present in the state file but not found this run, and still
        unresolved (resolution == "" and lastChecked isn't from this run)
        -> resolution is auto-set to "fixed".
    The state file is meant to be hand-edited too: e.g. set resolution to a
    note like "confirmed in original source" for a discrepancy that isn't a
    data-entry error at all. Manual resolutions are never overwritten by the
    auto-fixed logic above (only the literal "fixed" marker gets reopened).

Usage:
    python3 check_placing_gaps.py                       # IFBB since 2013 (default)
    python3 check_placing_gaps.py --org IFBB --from 2013
    python3 check_placing_gaps.py --org NPC --from 2020 --out /tmp/report.md
    python3 check_placing_gaps.py --report unresolved    # skip fixed/manually-resolved items in the .md
    python3 check_placing_gaps.py --state /tmp/state.json
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

BASE_URL = 'http://localhost:3000'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
# RATE_LIMIT_BYPASS_SECRET from ~/workspace/node/musmem/.env — skips the
# 1000-req/hour long-term limit. The 30-req/10s short-term limit is always
# enforced regardless, so REQUEST_DELAY still throttles every call.
BYPASS_SECRET = '2001 a Space Odyssey'
REQUEST_DELAY = 0.35


def fetch_json(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'X-Rate-Limit-Bypass': BYPASS_SECRET,
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    time.sleep(REQUEST_DELAY)
    return data


def get_contest_names(org, from_year):
    url = f'{BASE_URL}/api/org?name={urllib.parse.quote(org)}&from={from_year}'
    data = fetch_json(url)
    return data['data']['contests']


def get_years(name):
    url = f'{BASE_URL}/api/contest/years?name={urllib.parse.quote(name)}'
    data = fetch_json(url)
    return data['data']['years']


def get_results(name, year):
    url = f'{BASE_URL}/api/contest?name={urllib.parse.quote(name)}&year={year}'
    data = fetch_json(url)
    return data['data']['results']


def analyze_division(placings_sorted, gap_threshold=10):
    """placings_sorted: sorted list (with dups) of ints, already filtered to
    exclude 0 and 96-99. Returns (missing, anomalies, suspicious):
      - missing: sorted list of placement numbers absent from the sequence.
      - anomalies: (value, expected) pairs where a placement appeared below
        the currently expected value — e.g. a tie that wasn't followed by
        the expected skip (1, 2, 2, 3 instead of 1, 2, 2, 4). Reported
        separately since it's a different kind of irregularity than a gap.
      - suspicious: values that jumped more than gap_threshold past the
        currently expected placing — likely a bib number entered as a
        placing rather than a real gap. Excluded from the missing-range
        fill and from advancing the expected sequence, since treating them
        as real would bury the actual gap under a wall of false "missing"
        numbers.
    """
    counts = Counter(placings_sorted)
    missing = []
    anomalies = []
    suspicious = []
    expected = 1
    for v in sorted(counts):
        if v < expected:
            anomalies.append((v, expected))
            continue
        if v - expected >= gap_threshold:
            suspicious.append(v)
            continue
        if v > expected:
            missing.extend(range(expected, v))
        expected = v + counts[v]
    return missing, anomalies, suspicious


def now_iso():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def load_state(path):
    if not path.exists():
        return []
    with open(path) as fh:
        return json.load(fh)


def save_state(path, state):
    state = sorted(state, key=lambda e: (e['year'], e['contest']))
    for entry in state:
        entry['discrepancy'].sort(key=lambda d: (d['type'], d['division'], d['gender'], d['explanation']))
    with open(path, 'w') as fh:
        json.dump(state, fh, indent=2)
        fh.write('\n')


def build_discrepancies(findings):
    """Group findings by (year, contest name) into lists of discrepancy dicts
    with just type/division/gender/explanation — dateFound/lastChecked/
    resolution are filled in by reconcile_state."""
    grouped = {}
    for f in findings:
        entries = grouped.setdefault((f['year'], f['name']), [])
        if f['missing']:
            entries.append({
                'type': 'missing', 'division': f['code'], 'gender': f['gender'],
                'explanation': f"missing {f['missing']} — actual: {f['placings']}",
            })
        if f['anomalies']:
            anomaly_str = ', '.join(f"{v} (expected >= {e})" for v, e in f['anomalies'])
            entries.append({
                'type': 'irregular', 'division': f['code'], 'gender': f['gender'],
                'explanation': f"{anomaly_str} — actual: {f['placings']}",
            })
        if f['suspicious']:
            entries.append({
                'type': 'suspicious', 'division': f['code'], 'gender': f['gender'],
                'explanation': f"suspicious {f['suspicious']} — actual: {f['placings']}",
            })
    return grouped


def reconcile_state(state, current_by_key, run_ts):
    """Mutates state in place (and returns it) per the rules in the module
    docstring's "Persistent tracking" section."""
    state_by_key = {(e['year'], e['contest']): e for e in state}

    for (year, contest), discs in current_by_key.items():
        entry = state_by_key.get((year, contest))
        if entry is None:
            entry = {'year': year, 'contest': contest, 'discrepancy': []}
            state.append(entry)
            state_by_key[(year, contest)] = entry
        existing_by_key = {
            (d['type'], d['division'], d['gender'], d['explanation']): d
            for d in entry['discrepancy']
        }
        for d in discs:
            dk = (d['type'], d['division'], d['gender'], d['explanation'])
            existing = existing_by_key.get(dk)
            if existing is None:
                new_disc = dict(d, dateFound=run_ts, lastChecked=run_ts, resolution='')
                entry['discrepancy'].append(new_disc)
                existing_by_key[dk] = new_disc
            else:
                existing['lastChecked'] = run_ts
                if existing['resolution'] == 'fixed':
                    existing['resolution'] = ''

    # Anything not touched above (lastChecked still isn't this run's
    # timestamp) wasn't found this run. If it was still open, it's fixed.
    for entry in state:
        for d in entry['discrepancy']:
            if d['resolution'] == '' and d['lastChecked'] != run_ts:
                d['resolution'] = 'fixed'

    return state


def build_report_lines(state, run_ts, mode, org, from_year, checked, num_names):
    """mode: 'all' includes every discrepancy found in this run regardless of
    resolution; 'unresolved' additionally drops anything with a non-blank
    resolution (auto-fixed or manually annotated).

    Output is nested contest -> year -> discrepancy."""
    by_contest = {}
    total = 0
    for entry in state:
        kept = [d for d in entry['discrepancy'] if d['lastChecked'] == run_ts
                and (mode != 'unresolved' or d['resolution'] == '')]
        if not kept:
            continue
        kept.sort(key=lambda d: (d['type'], d['division'], d['gender']))
        by_contest.setdefault(entry['contest'], {})[entry['year']] = kept
        total += len(kept)

    def fmt(d):
        body = f"**{d['type']}** [{d['division']}/{d['gender']}]: {d['explanation']}"
        if d['resolution']:
            body = f"~~{body}~~ _(resolution: {d['resolution']})_"
        return f"    - {body}"

    lines = [f"# Missing Placing Report — {org} since {from_year}", ""]
    lines.append(f"Checked {checked} contest-years across {num_names} distinct contests.")
    if mode == 'unresolved':
        lines.append("Showing unresolved discrepancies only (`--report unresolved`).")
    lines.append(f"\n{total} discrepancies across {len(by_contest)} contests.\n")

    for contest in sorted(by_contest, key=str.casefold):
        lines.append(f"- **{contest}**")
        years = by_contest[contest]
        encoded_name = urllib.parse.quote(contest)
        for year in sorted(years):
            prod_url = f'https://musclememory.org/event?name={encoded_name}&year={year}'
            local_url = f'http://localhost:4200/event?name={encoded_name}&year={year}'
            lines.append(f"  - **[{year}]({prod_url})** [🖥️]({local_url})")
            for d in years[year]:
                lines.append(fmt(d))

    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--org', default='IFBB')
    ap.add_argument('--from', dest='from_year', type=int, default=2013)
    ap.add_argument('--out', default=None, help='write markdown report to this file in addition to stdout')
    ap.add_argument('--state', default=None,
                     help='JSON state file tracking discrepancies across runs '
                          '(default: placing_gaps_state_<org>.json next to this script)')
    ap.add_argument('--report', choices=['all', 'unresolved'], default='all',
                     help="markdown report contents: 'all' current findings, or 'unresolved' "
                          "only (excludes anything with a resolution set, e.g. auto-fixed or "
                          "manually confirmed against the original source) (default: all)")
    ap.add_argument('--gap-threshold', type=int, default=10,
                     help='placings this far past the expected value are treated as likely '
                          'bib numbers and reported separately instead of as a gap (default: 10)')
    args = ap.parse_args()

    state_path = Path(args.state) if args.state else (
        Path(__file__).resolve().parent / f'placing_gaps_state_{args.org.lower()}.json'
    )

    print(f"Fetching {args.org} contest list since {args.from_year}...")
    names = get_contest_names(args.org, args.from_year)
    print(f"  {len(names)} distinct contest names")

    print("Resolving contest years...")
    pairs = []
    for i, name in enumerate(names, 1):
        try:
            years = get_years(name)
        except Exception as e:
            print(f"  WARNING: could not fetch years for {name!r}: {e}", file=sys.stderr)
            continue
        pairs.extend((name, y) for y in years if y >= args.from_year)
        if i % 50 == 0:
            print(f"  ...{i}/{len(names)} contest names resolved, {len(pairs)} contest-years so far")

    total_pairs = len(pairs)
    print(f"Checking {total_pairs} contest-year result sets...")

    findings = []
    checked = 0
    for i, (name, year) in enumerate(pairs, 1):
        try:
            results = get_results(name, year)
        except Exception as e:
            print(f"  WARNING: could not fetch results for {name!r} {year}: {e}", file=sys.stderr)
            continue
        checked += 1

        # Group by (gender, code) — the same division code (e.g. PH) is
        # reused independently for Men's and Women's divisions, so results
        # for both genders are interleaved under one code in the API
        # response. Grouping by code alone falsely interleaves two
        # independent 1..N sequences into what looks like a duplicated one.
        by_key = {}
        for r in results:
            placing = r.get('placing', '')
            if '-' not in placing:
                continue
            code, num_str = placing.rsplit('-', 1)
            if not num_str.isdigit():
                continue
            num = int(num_str)
            if num == 0 or 96 <= num <= 99:
                continue
            key = (r.get('gender', ''), code)
            by_key.setdefault(key, []).append(num)

        for (gender, code), nums in by_key.items():
            nums_sorted = sorted(nums)
            missing, anomalies, suspicious = analyze_division(nums_sorted, args.gap_threshold)
            if missing or anomalies or suspicious:
                findings.append({
                    'name': name, 'year': year, 'code': code, 'gender': gender,
                    'placings': nums_sorted, 'missing': missing,
                    'anomalies': anomalies, 'suspicious': suspicious,
                })

        if i % 100 == 0:
            print(f"  ...{i}/{total_pairs} checked, {len(findings)} findings so far")

    print(f"\nDone. {checked}/{total_pairs} contest-years checked. {len(findings)} divisions with issues.")

    run_ts = now_iso()
    state = load_state(state_path)
    current_by_key = build_discrepancies(findings)
    reconcile_state(state, current_by_key, run_ts)
    save_state(state_path, state)

    new_count = sum(1 for e in state for d in e['discrepancy'] if d['dateFound'] == run_ts)
    fixed_now = sum(1 for e in state for d in e['discrepancy']
                     if d['resolution'] == 'fixed' and d['lastChecked'] != run_ts)
    open_count = sum(1 for e in state for d in e['discrepancy'] if d['resolution'] == '')
    print(f"State file: {state_path}")
    print(f"  {new_count} new discrepancies, {fixed_now} auto-marked fixed this run, {open_count} currently open.")

    report = build_report_lines(state, run_ts, args.report, args.org, args.from_year, checked, len(names))
    print('\n' + report)

    if args.out:
        with open(args.out, 'w') as fh:
            fh.write(report + '\n')
        print(f"\nReport written to {args.out}")


if __name__ == '__main__':
    main()
