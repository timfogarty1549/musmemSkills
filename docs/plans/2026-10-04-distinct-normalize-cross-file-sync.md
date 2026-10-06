# Distinct/Normalize: keeping name decisions in sync across .dat files

**Status:** Tabled 2026-10-04. Revisit if cross-file drift becomes a bigger problem.

**Skills involved:** `musmem-extract-distinct-athletes`, `musmem-normalize`

## The problem

Workflow in practice: run distinct on a **single** file (e.g. `prelim/prelim-male.dat`),
review the ~650 groups with normalize, and apply the renames to that file only. Other files
(e.g. `bb_male.dat`) can still hold the old spellings, so the files drift apart.

Running distinct on several files with "Restrict output to groups containing a name from
source(s)" doesn't help, because it misses groups that sit entirely inside the focus file (see below).

### Findings from the prelim-male run (2026-10-04)

- `prelim_male-variant-groups.tsv` has 666 groups: 550 skip and 116 applied (120 renamed rows).
- Initially only 9 of the old names were still present in `bb_male.dat`. After manual edits, 6
  remained. In 5 of those, prelim-male had been changed **back** to the bb_male spelling,
  because the bb value was judged more likely. Those files already agree, so the TSV's decision
  is stale for those groups rather than pending. Only `Mabry, Monty` → `Marby, Monty` still
  differed between the two files.
- Conclusion: the drift is small, so the decisions can be carried over by hand for now.
- Some decisions shouldn't be carried over blindly, because they were made looking only at
  prelim records:
  - `Castillo, Francisco` → `Castillo, Francisco (1)` is a disambiguation, and bb's record may be the other person.
  - `Mabry, Monty` (15 bb records) → `Marby, Monty`: check which spelling is right before applying.

## How to compare a TSV's changes to a .dat file that wasn't in the distinct run

Script: `/tmp/tsv_vs_dat.py`. It lives in /tmp, so recreate it from the copy below if it's gone.

```bash
python3 /tmp/tsv_vs_dat.py ~/workspace/musmem/distinct/prelim_male-variant-groups.tsv ~/workspace/musmem/data/bb_male.dat
```

It also reads the TSV's own `# source:` file(s) in their **current** state, because the TSV
doesn't record manual edits made after `applied`. It reports:

1. **Need review:** the source file uses the new name, but the target still has the old one.
   Record counts are shown for the old and new names. "target already exists → merge" means
   applying it would combine two names that both exist in the target.
2. **In sync:** the source file was later edited back to the old name (the new name is gone and
   the old one is present again), so both files agree. No action needed.
3. **Skipped groups:** groups with 2+ names in the target. In the TSV's source file these were
   judged to be different people. This is useful context but needs no action.

To fix the hits, edit by hand, or apply a single rename with sed/Python. If there are many, use the
"propagate" approach below.

```python
#!/usr/bin/env python3
"""Compare applied renames in a normalize TSV against a .dat file not in the TSV's sources.

Usage: python3 /tmp/tsv_vs_dat.py <tsv> <target.dat>
"""
import os
import sys
from collections import Counter, defaultdict

SPECIAL = {'', '-', 'skip', 'defer'}


def names(path):
    c = Counter()
    for line in open(path, encoding='utf-8'):
        p = line.split(';')
        if len(p) >= 2 and p[0].strip():
            c[p[0].strip()] += 1
    return c


tsv, target = (os.path.expanduser(a) for a in sys.argv[1:3])
dat = names(target)
src_paths = []
groups = defaultdict(list)
for line in open(tsv, encoding='utf-8'):
    if line.startswith('# source: '):
        src_paths.append(line[len('# source: '):].strip())
        continue
    if line.startswith('#') or line.startswith('group_id'):
        continue
    c = line.rstrip('\n').split('\t') + ['', '', '']
    groups[int(c[0])].append(c[:4])

# Current state of the TSV's own source file(s): a later manual edit may have reverted a rename there.
src = Counter()
for p in src_paths:
    if os.path.isfile(p):
        src.update(names(p))

renames = [(gid, r[1], r[2]) for gid, rows in groups.items() for r in rows if r[2] not in SPECIAL]
hits = [(gid, s, t) for gid, s, t in renames if s in dat]
pending = [h for h in hits if not (src[h[1]] and not src[h[2]])]
reverted = [h for h in hits if src[h[1]] and not src[h[2]]]

print(f'{len(renames)} renames in TSV; {len(hits)} old names still present in {target}')
print(f'Source file(s): {", ".join(src_paths)}\n')
print(f'{len(pending)} need review (source uses the new name, target still has the old one):')
for gid, s, t in pending:
    flag = '  (target already exists -> merge)' if t in dat else ''
    print(f'  group {gid:>4}  {s!r} [{dat[s]}]  ->  {t!r} [{dat[t]}]{flag}')
print(f'\n{len(reverted)} in sync (source was later edited back to the old name; files agree):')
for gid, s, t in reverted:
    print(f'  group {gid:>4}  {s!r}  (TSV said -> {t!r})')

skips = [(gid, [r[1] for r in rows if r[1] in dat]) for gid, rows in groups.items() if rows[0][2] == 'skip']
skips = [(gid, ns) for gid, ns in skips if len(ns) >= 2]
print(f'\n{len(skips)} skipped groups have 2+ names in the target (judged different people in the TSV source):')
for gid, ns in skips:
    print(f'  group {gid:>4}  ' + ' | '.join(ns))
```

TSV format reminder: `group_id`, `name`, `expression`, `applied`. A rename row has the new name in
`expression` and a timestamp in `applied`. `-` means "no rename for this row". `skip` and `defer`
apply to the whole group.

## Root cause: why focus-file restriction misses groups inside that file

In `extract_distinct_athletes.py` `write_outputs()`, two filters run in this order:

1. When there are 2+ sources, keep only groups whose names span **at least 2 sources**.
2. Then keep only groups containing a name from the focus label(s).

Filter 1 drops every group whose variants all come from the focus file (e.g.
`Achmell, David` / `Schmell, David`, both only in prelim) before filter 2 runs.

## Proposed fixes (not implemented)

### Short term: "propagate" script

Input: an applied TSV and a target .dat. Output: a **new review TSV** for normalize.

- **Which groups:** only groups where a renamed-away name is still present in the target.
- **Group contents:** the old names found in the target plus the new name. Each group starts as pending.
- **`# source:` lines:** both the target file and the original source, so normalize shows records
  from both side by side. Renames are no-ops on the original file because those names are already gone.
- **Hint column:** an optional 5th column holding the original decision, with a small normalize
  display change to print "prelim chose: X". `record_decision` already keeps columns past 4.

Limitation: this only carries over existing decisions. It won't find target-file names that are
variants of a new name but weren't in the original group.

### Long term: "primary source" mode in distinct

- Build candidate pairs from all files, but keep a pair only if **at least one of its two names
  appears in the primary file**.
- Group the connected names and **drop** the "span 2+ sources" rule for this mode.
- Write `# source:` lines for every file. Normalize already handles any number of files, so each
  decision is written to all of them at once and the files can't drift apart.

### Companion: known-different pairs file

Build a persistent list of name pairs judged different from `skip` decisions, and have distinct
read it to suppress those groups. Otherwise a re-run in primary-source mode would bring back
everything already skipped (550 groups for prelim-male).
