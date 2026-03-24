# review_athlete_names.py Improvements — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce soundex false positives via a word-level edit-distance post-filter, then add an interactive mode that lets the user accept/reject each match and writes corrections back to `review-athlete-names.dat`.

**Architecture:** All changes are confined to one file (`review_athlete_names.py`). Task 1 adds a pure helper function and one filter call. Task 2 adds the interactive prompt loop and write-back logic. Tests live in a new `test_review_athlete_names.py` alongside the script.

**Tech Stack:** Python 3 stdlib only — `unicodedata`, `re`, `argparse`, `termios`, `tty`, `pathlib`.

---

## Reference

- Design doc: `docs/plans/2026-03-24-review-athlete-names-improvements.md`
- Script under edit: `musmem-contests/python/review_athlete_names.py`
- Pattern for single-keypress I/O: `musmem-contests/python/review_flags.py` (see `getch()`)
- Input file format: `~/workspace/musmem/working_data/review-athlete-names.dat`
  - Each line: `context_col : Lastname, Firstname`
  - Two columns separated by `: ` (colon + space)
- Master corrections output: `~/workspace/musmem/working_data/master-corrections.txt`

---

## Task 1: Word-level edit-distance filter for soundex candidates

**Files:**
- Modify: `musmem-contests/python/review_athlete_names.py`
- Create: `musmem-contests/python/test_review_athlete_names.py`

### Step 1: Write failing tests

Create `musmem-contests/python/test_review_athlete_names.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from review_athlete_names import last_names_word_close

# --- last_names_word_close ---

def test_exact_shared_word():
    # "Ortiz" appears in both last names
    assert last_names_word_close("Ortiz Guzman", "Ortiz") is True

def test_exact_shared_word_reversed():
    assert last_names_word_close("Ortiz", "Ortiz Guzman") is True

def test_typo_one_char_missing_end():
    assert last_names_word_close("Alvardo", "Alvarado") is True

def test_typo_one_char_missing_start():
    assert last_names_word_close("Lvarado", "Alvarado") is True

def test_al_prefix_different_names():
    # Only shared word is "al" (len 2) — should fail
    assert last_names_word_close("Al Kindy", "Al Saif") is False

def test_al_prefix_different_names_2():
    assert last_names_word_close("Al Sabea", "Al Saif") is False

def test_no_shared_words():
    assert last_names_word_close("Alamo Serrano", "Almaguer") is False

def test_no_shared_words_2():
    assert last_names_word_close("Alberto Cancel", "Albarado Rodriguez") is False

def test_shared_word_min_len_boundary():
    # "van" is len 3 — should count
    assert last_names_word_close("van Berg", "van Berg Jr") is True

def test_both_single_words_close():
    # Single words, edit distance 1
    assert last_names_word_close("Smithe", "Smith") is True

def test_both_single_words_far():
    # Single words, completely different
    assert last_names_word_close("Jones", "Smith") is False
```

### Step 2: Run tests to verify they fail

```bash
cd /Users/timfogarty/workspace/skills/musmemSkills/musmem-contests/python
python3 -m pytest test_review_athlete_names.py -v
```

Expected: ImportError or NameError on `last_names_word_close`.

### Step 3: Implement `last_names_word_close`

Add this function to `review_athlete_names.py` after the existing `levenshtein` function (around line 172):

```python
def last_names_word_close(last1: str, last2: str, min_len: int = 3, max_dist: int = 2) -> bool:
    """Return True if any word pair (one from each last name, both len >= min_len)
    has Levenshtein distance <= max_dist."""
    words1 = [w for w in re.sub(r"[^a-z ]", "", strip_to_ascii(last1)).split() if len(w) >= min_len]
    words2 = [w for w in re.sub(r"[^a-z ]", "", strip_to_ascii(last2)).split() if len(w) >= min_len]
    for w1 in words1:
        for w2 in words2:
            if levenshtein(w1, w2) <= max_dist:
                return True
    return False
```

### Step 4: Apply filter inside `find_all_candidates`

In `find_all_candidates`, the soundex block adds candidates via `add_base(candidate_base, "soundex")`. Wrap those calls with the filter.

Find the two soundex `add_base` calls in the `if not found:` block (around lines 366–376) and the edit-distance scan (around lines 384–389). Add a guard before each `add_base(..., "soundex")` call:

```python
# Soundex on last name (same first)
if first and last:
    sdx_last = soundex(last)
    for candidate_base in idx.by_soundex_last.get((first.lower(), sdx_last), []):
        if candidate_base != base:
            ex_last, _ = name_parts(candidate_base)
            if last_names_word_close(last, ex_last):          # ← add this guard
                add_base(candidate_base, "soundex")

# Soundex on first name (same last)
if first and last:
    sdx_first = soundex(first)
    for candidate_base in idx.by_soundex_first.get((last.lower(), sdx_first), []):
        if candidate_base != base:
            ex_last, _ = name_parts(candidate_base)
            if last_names_word_close(last, ex_last):          # ← add this guard
                add_base(candidate_base, "soundex")

# Edit distance scan
if first and last:
    for candidate_base in list(idx.by_base.keys()):
        ex_last, ex_first = name_parts(candidate_base)
        if ex_first and ex_first.lower() == first.lower():
            if ex_last and levenshtein(last.lower(), ex_last.lower()) <= 2:
                if candidate_base != base:
                    if last_names_word_close(last, ex_last):  # ← add this guard
                        add_base(candidate_base, "soundex")
```

### Step 5: Run tests to verify they pass

```bash
python3 -m pytest test_review_athlete_names.py -v
```

Expected: all 11 tests PASS.

### Step 6: Smoke test against real data

```bash
python3 review_athlete_names.py 2>&1 | head -60
```

Verify that `Al Kindy / Al Saif`, `Al Sabea / Al Saif`, `Alamo Serrano / Almaguer`, and `Alberto Cancel / Albarado Rodriguez` no longer appear. Verify that `Ortiz Guzman / Ortiz` and `Pastor Cueto / Pastor` still appear.

### Step 7: Commit

```bash
git add musmem-contests/python/review_athlete_names.py \
        musmem-contests/python/test_review_athlete_names.py
git commit -m "feat: filter soundex false positives via word-level edit distance"
```

---

## Task 2: Interactive review mode (`--interactive`)

**Files:**
- Modify: `musmem-contests/python/review_athlete_names.py`
- Modify: `musmem-contests/python/test_review_athlete_names.py`

### Step 1: Write failing tests for the write-back logic

The interactive prompting itself cannot be unit-tested (requires a tty), but the write-back function — which applies name substitutions to the lines of `review-athlete-names.dat` — can be. Add to `test_review_athlete_names.py`:

```python
from review_athlete_names import apply_name_corrections

# --- apply_name_corrections ---

def test_apply_corrections_basic():
    lines = [
        "2015_nationals-npc-male:123 : Ortiz Guzman, Jose\n",
        "2015_nationals-npc-male:145 : Smith, John\n",
        "2015_nationals-npc-male:167 : Ortiz Guzman, Jose\n",
    ]
    corrections = {"Ortiz Guzman, Jose": "Ortiz, Jose"}
    result = apply_name_corrections(lines, corrections)
    assert result[0] == "2015_nationals-npc-male:123 : Ortiz, Jose\n"
    assert result[1] == "2015_nationals-npc-male:145 : Smith, John\n"
    assert result[2] == "2015_nationals-npc-male:167 : Ortiz, Jose\n"

def test_apply_corrections_no_match():
    lines = ["2015_nationals-npc-male:123 : Smith, John\n"]
    corrections = {"Jones, Bob": "Jones, Robert"}
    result = apply_name_corrections(lines, corrections)
    assert result == lines

def test_apply_corrections_empty():
    lines = ["2015_nationals-npc-male:123 : Smith, John\n"]
    result = apply_name_corrections(lines, {})
    assert result == lines

def test_apply_corrections_preserves_context_col():
    # The part before ' : ' must be unchanged
    lines = ["abc:99 : Pastor Cueto, German\n"]
    corrections = {"Pastor Cueto, German": "Pastor, German"}
    result = apply_name_corrections(lines, corrections)
    assert result[0].startswith("abc:99 : ")
    assert result[0].endswith("Pastor, German\n")
```

### Step 2: Run new tests to verify they fail

```bash
python3 -m pytest test_review_athlete_names.py -v -k "apply_name"
```

Expected: ImportError on `apply_name_corrections`.

### Step 3: Implement `apply_name_corrections`

Add this function to `review_athlete_names.py` after `format_entry`:

```python
def apply_name_corrections(lines: list, corrections: dict) -> list:
    """Return a new list of lines with incoming names substituted per corrections dict.
    Each line has format:  context_col : Name
    Only the name portion (after last ' : ') is replaced."""
    if not corrections:
        return lines
    result = []
    for line in lines:
        stripped = line.rstrip("\n")
        if " : " in stripped:
            prefix, name = stripped.rsplit(" : ", 1)
            name = name.strip()
            if name in corrections:
                line = prefix + " : " + corrections[name] + "\n"
        result.append(line)
    return result
```

### Step 4: Run tests to verify they pass

```bash
python3 -m pytest test_review_athlete_names.py -v -k "apply_name"
```

Expected: 4 tests PASS.

### Step 5: Add `getch()` and `--interactive` flag

Copy `getch()` from `review_flags.py` into `review_athlete_names.py` (place it near the top, after imports):

```python
def getch() -> str:
    """Read a single character without requiring RETURN."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return os.read(fd, 1).decode()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
```

Add `import os`, `import termios`, `import tty` to the imports block (they are stdlib; check if already present before adding).

In `main()`, add `--interactive` to the argument parser:

```python
parser.add_argument("--interactive", "-i", action="store_true",
                    help="Prompt for each variation; write corrections back to input file")
```

### Step 6: Add interactive prompt logic to `main()`

Replace the variation-output block in `main()` (the `else:` branch inside the name loop) with:

```python
else:
    variation_count += 1
    exact_cands = [c for c in candidates if c.match_types == ["exact"]]
    var_cands   = [c for c in candidates if c.match_types != ["exact"]]

    print(f"{CYAN}VARIATION{RESET}  {name}")
    for c in exact_cands:
        print(f"          exact   : {format_entry(c.entry)}")
    for c in var_cands:
        tags = "+".join(c.match_types)
        print(f"          {tags:<8}: {format_entry(c.entry)}")

    if args.interactive:
        chosen_entry = None

        if len(var_cands) == 1 and not exact_cands:
            chosen_entry = var_cands[0].entry
            print(f"\n  [M] use Master  → \"{chosen_entry.full_name}\"")
            print(f"  [I] Incoming is canonical  (flag master for update)")
            print(f"  [N] Not same athlete")
            print(f"  [S] Skip")
            print(f"  Choice: ", end="", flush=True)
            while True:
                ch = getch().upper()
                if ch in "MINS\x03":
                    print(ch)
                    break
            if ch == "\x03":
                print("\nAborted.")
                break
        else:
            # Multiple candidates: pick one first
            all_cands = exact_cands + var_cands
            for idx_c, c in enumerate(all_cands, 1):
                tags = "exact" if c.match_types == ["exact"] else "+".join(c.match_types)
                print(f"  [{idx_c}] {tags}: {format_entry(c.entry)}")
            valid_digits = [str(i) for i in range(1, len(all_cands) + 1)]
            print(f"  Select candidate ({'/'.join(valid_digits)}) or [N]ot same / [S]kip: ", end="", flush=True)
            while True:
                ch = getch().upper()
                if ch in valid_digits or ch in "NS\x03":
                    print(ch)
                    break
            if ch == "\x03":
                print("\nAborted.")
                break
            if ch in valid_digits:
                chosen_entry = all_cands[int(ch) - 1].entry
                print(f"  [M] use Master  → \"{chosen_entry.full_name}\"")
                print(f"  [I] Incoming is canonical")
                print(f"  [N] Not same athlete")
                print(f"  [S] Skip")
                print(f"  Choice: ", end="", flush=True)
                while True:
                    ch = getch().upper()
                    if ch in "MINS\x03":
                        print(ch)
                        break
                if ch == "\x03":
                    print("\nAborted.")
                    break

        if ch == "M" and chosen_entry:
            pending_corrections[name] = chosen_entry.full_name
            print(f"  → will rename \"{name}\" → \"{chosen_entry.full_name}\"")
        elif ch == "I" and chosen_entry:
            pending_master_flags.append((name, chosen_entry.full_name))
            print(f"  → flagged for master update")
```

At the top of `main()`, before the loop, add:

```python
pending_corrections: dict = {}      # incoming_name -> master_name (M decisions)
pending_master_flags: list = []     # [(incoming, master)] for I decisions
```

### Step 7: Add write-back after the loop

After the name-processing loop in `main()`, add:

```python
if args.interactive and pending_corrections:
    raw_lines = INPUT_FILE.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    updated = apply_name_corrections(raw_lines, pending_corrections)
    INPUT_FILE.write_text("".join(updated), encoding="utf-8")
    print(f"\nWrote {len(pending_corrections)} correction(s) to {INPUT_FILE.name}.")

if args.interactive and pending_master_flags:
    master_corr_file = INPUT_FILE.parent / "master-corrections.txt"
    with open(master_corr_file, "a", encoding="utf-8") as f:
        for incoming, master in pending_master_flags:
            f.write(f"{incoming}  →  {master}\n")
    print(f"Wrote {len(pending_master_flags)} master flag(s) to {master_corr_file.name}.")
```

### Step 8: Run all tests

```bash
python3 -m pytest test_review_athlete_names.py -v
```

Expected: all tests PASS.

### Step 9: Manual smoke test of interactive mode

Run against real data with interactive flag:

```bash
python3 review_athlete_names.py --interactive 2>&1 | head -40
```

Verify:
- A variation is shown
- The prompt appears with M/I/N/S options
- Pressing N moves to the next variation without modifying the file
- Pressing M queues a correction; at session end the file is updated

### Step 10: Commit

```bash
git add musmem-contests/python/review_athlete_names.py \
        musmem-contests/python/test_review_athlete_names.py
git commit -m "feat: add --interactive mode with write-back to review-athlete-names.dat"
```
