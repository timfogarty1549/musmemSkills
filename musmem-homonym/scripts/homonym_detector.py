from collections import defaultdict
from pathlib import Path
import sys
import termios
import tty

DEFAULT_DATA_DIR = Path.home() / "workspace" / "musmem" / "data"
NOT_HOMONYMS_PATH = Path.home() / "workspace" / "musmem" / "working_data" / "not-homonyms.dat"

# Codes representing 60+ or older masters categories
SIXTY_PLUS_CODES = {
    "M6", "6H", "6l", "6M", "6L", "6t", "6m", "6s",
    "m6", "65",
    "M7", "7H", "7M", "7L",
    "M8", "M9",
    "GM", "GH", "GL", "Gt", "Gs", "UM",
    "M6212", "M7212",
    "c6", "c6a", "c6b", "c7",
    "P6", "P7",
    "F6", "F6a", "F6b", "f6", "F65",
}

# Codes representing 50+ masters categories (includes all 60+)
FIFTY_PLUS_CODES = SIXTY_PLUS_CODES | {
    "M5", "5S", "5H", "5l", "5M", "5W", "5L", "5B", "5t", "5m", "5s",
    "55", "55L", "55H",
    "M5212",
    "c5", "c5a", "c5b", "c5c", "c5d", "c5s", "c5m", "c5t",
    "c55", "c55a", "c55b",
    "P5", "P5a", "P5b", "P5c", "P5d",
    "P55", "P55a", "P55b",
    "F5", "F5a", "F5b", "F5c", "F5d",
    "f5", "f5a", "f5b",
}

# Codes representing clearly open/non-masters competition
OPEN_CODES = {
    "OP", "OV", "BB", "PBB",
    "SW", "LS", "HW", "LH", "MW", "LM", "WW", "LW", "BW", "FW", "LF",
    "U212", "U208", "U202",
    "XT", "TA", "MT", "ME", "SH", "XS",
    "TE", "TH", "Tl", "TM", "TL", "Tt", "Tm", "Ts", "Ta", "Tb", "Tu",
    "JR", "JH", "Jl", "JM", "JW", "JL", "JB", "JF", "Jf", "Jt", "Jm", "Js", "Ju", "Jy",
    "ED", "EH", "EM", "EL", "EP", "EF",
    "Ba", "Bb", "Bc", "Bd", "Be", "Bf", "Bg",
    "55kg", "60kg", "65kg", "70kg", "75kg", "80kg", "85kg", "90kg",
    "95kg", "100kg", "105kg", "o100kg",
    "CL", "Ca", "Cb", "Cc", "Cd", "Ce", "Cf", "Cg", "Ch",
    "Cs", "cS", "Cm", "cM", "Ct", "cT", "ct",
    "CJ", "CJa", "CJb", "CJc", "CJd",
    "PH", "Pa", "Pb", "Pc", "Pd", "Pe", "Pf", "Pg", "Ph",
    "PT", "PJ", "PJa", "PJb", "PJc", "PJd",
    "FI", "FX", "Ft", "fM", "Fm", "fS", "Fs", "Fx",
    "Fa", "Fb", "Fc", "Fd", "Fe", "Ff", "Fg", "Fh",
    "FT", "FJ", "FJa", "FJb", "FJc", "FJd", "js", "jt",
    "PQ", "PR", "PB", "PRh", "Pmw", "Pl", "Ps", "Pm", "Pt", "PP", "PCL", "PF",
    "AP", "As", "Am", "aM", "At", "A1", "A2", "A3", "A4", "A5", "JA",
    "AM", "C1", "C2", "C3", "C4",
    "HP", "HP3", "HP0s", "HP0t", "HP4s", "HP4t", "HP6t",
    "Ea", "Mi", "So", "Se", "Sw", "dC", "We",
    "PA", "HC", "Hs", "Hw", "WC", "QA",
    "Mu", "Sy",
}


def is_sixty_plus(code):
    return code in SIXTY_PLUS_CODES


def is_fifty_plus(code):
    return code in FIFTY_PLUS_CODES


def is_open(code):
    return code in OPEN_CODES


GAP_THRESHOLD = 10  # consecutive years with no appearances


def find_gaps(years_sorted):
    """Returns True if any consecutive pair of years has a gap >= GAP_THRESHOLD."""
    for i in range(len(years_sorted) - 1):
        if years_sorted[i + 1] - years_sorted[i] >= GAP_THRESHOLD:
            return True
    return False


def cluster_years(years_sorted):
    """Split sorted years into clusters separated by gaps >= GAP_THRESHOLD."""
    if not years_sorted:
        return []
    clusters = []
    current = [years_sorted[0]]
    for y in years_sorted[1:]:
        if y - current[-1] >= GAP_THRESHOLD:
            clusters.append(current)
            current = [y]
        else:
            current.append(y)
    clusters.append(current)
    return clusters


def analyze(records):
    """
    Returns (high, medium).
    Each item is (name, clusters) where clusters is a list of year lists.

    High   — 50+ codes in early clusters, open codes in non-masters contests in late cluster
    Medium — gap ≥ 10y, late cluster 20+ years after first appearance, open in non-masters contest
    """
    by_name = defaultdict(list)
    for name, year, code, contest in records:
        by_name[name].append((year, code, contest))

    high = []
    medium = []

    for name, appearances in by_name.items():
        years_sorted = sorted(set(y for y, _, _ in appearances))
        if len(years_sorted) < 2:
            continue
        if not find_gaps(years_sorted):
            continue

        clusters = cluster_years(years_sorted)
        if len(clusters) < 2:
            continue

        year_to_entries = defaultdict(list)  # year -> [(code, contest), ...]
        for y, code, contest in appearances:
            year_to_entries[y].append((code, contest))

        def cluster_entries(cluster):
            # Returns (year, code, contest) triples
            entries = []
            for y in cluster:
                for code, contest in year_to_entries[y]:
                    entries.append((y, code, contest))
            return entries

        late_entries = cluster_entries(clusters[-1])

        pre_last_codes = set()
        for c in clusters[:-1]:
            for _, code, _ in cluster_entries(c):
                pre_last_codes.add(code)

        first_year = years_sorted[0]

        def has_true_open(entries):
            # Group by (year, contest); an open code only counts if that same
            # contest/year has no non-open code alongside it (i.e. the athlete
            # wasn't also entered in a masters division at the same event).
            by_contest = defaultdict(list)
            for y, code, contest in entries:
                by_contest[(y, contest)].append(code)
            for (_, contest), codes in by_contest.items():
                if "master" in contest.lower():
                    continue
                if any(is_open(c) for c in codes) and all(is_open(c) for c in codes):
                    return True
            return False

        late_has_true_open = has_true_open(late_entries)

        # 50+ division in any early cluster, then open division in a non-masters contest later
        scenario2 = any(is_fifty_plus(c) for c in pre_last_codes) and late_has_true_open

        # Late cluster is 20+ years after first appearance, open in a non-masters contest
        scenario1 = (max(clusters[-1]) - first_year >= 20) and late_has_true_open

        if scenario2:
            high.append((name, clusters))
        elif scenario1:
            medium.append((name, clusters))

    return high, medium


def format_clusters(clusters):
    parts = []
    for c in clusters:
        if len(c) == 1:
            parts.append(str(c[0]))
        else:
            parts.append(f"{min(c)}–{max(c)}")
    return ", ".join(parts)


WIDE = "═" * 60
THIN = "─" * 60

FILE_COLORS = [
    "\033[32m",  # f1: green
    "\033[33m",  # f2: yellow
    "\033[35m",  # f3: magenta
    "\033[36m",  # f4: cyan
    "\033[34m",  # f5+: blue
]
RESET = "\033[0m"


def get_char(prompt):
    """Print prompt, read one character without requiring Enter, echo it."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    sys.stdout.write(ch + "\n")
    sys.stdout.flush()
    return ch


def load_not_homonyms():
    """Return set of athlete names already confirmed as non-homonyms."""
    if not NOT_HOMONYMS_PATH.exists():
        return set()
    names = set()
    with open(NOT_HOMONYMS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                names.add(line.split(";")[0].strip())
    return names


def save_not_homonym(name, clusters, record_count):
    """Append one confirmed non-homonym entry to the exclusion file."""
    NOT_HOMONYMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NOT_HOMONYMS_PATH, "a", encoding="utf-8") as f:
        f.write(f"{name}; {format_clusters(clusters)}; {record_count}\n")


def display_candidate(name, clusters, name_to_lines, confidence, position, total):
    """Print the summary header and all raw records for one candidate."""
    entries = sorted(
        name_to_lines[name],
        key=lambda t: (t[1].split(";")[1].strip() if len(t[1].split(";")) > 1 else "", t[1]),
    )
    record_count = len(entries)
    print()
    print(WIDE)
    print(f"{name}   [{position} / {total}]   {format_clusters(clusters)}   {record_count} records   [{confidence}]")
    print(WIDE)
    for file_idx, line in entries:
        color = FILE_COLORS[min(file_idx, len(FILE_COLORS) - 1)]
        print(f"{color}  {line}{RESET}")
    print(THIN)
    return record_count


def review_loop(high, medium, name_to_lines, min_confidence):
    """Interactively review candidates one at a time."""
    not_homonyms = load_not_homonyms()

    if min_confidence == "high":
        candidates = [("high", name, clusters) for name, clusters in sorted(high)]
    else:
        candidates = (
            [("high", name, clusters) for name, clusters in sorted(high)]
            + [("medium", name, clusters) for name, clusters in sorted(medium)]
        )

    candidates = [
        (conf, name, clusters)
        for conf, name, clusters in candidates
        if name not in not_homonyms
    ]

    total = len(candidates)
    if total == 0:
        print("No candidates to review.")
        return

    excluded = len(not_homonyms)
    suffix = f"  ({excluded} previously confirmed non-homonyms skipped)" if excluded else ""
    print(f"\n{total} candidates to review{suffix}")

    for i, (confidence, name, clusters) in enumerate(candidates, 1):
        record_count = display_candidate(name, clusters, name_to_lines, confidence, i, total)

        while True:
            ch = get_char("(n)ext  (s)ave as non-homonym  (q)uit: ")
            if ch in ("\x03", "\x04"):  # Ctrl-C / Ctrl-D
                print("Exiting.")
                return
            key = ch.strip().lower()
            if key in ("n", " ", ""):
                break
            elif key == "s":
                save_not_homonym(name, clusters, record_count)
                print("  Saved.")
                break
            elif key == "q":
                return
            else:
                print("  n = next, s = save as non-homonym, q = quit")

    print("\nAll candidates reviewed.")


def collect_files():
    """Prompt interactively for .dat file paths; return list of resolved Path objects."""
    print("Enter .dat file paths (blank line to finish).")
    print(f"Relative paths resolve under {DEFAULT_DATA_DIR}")
    print()
    seen = set()
    files = []
    while True:
        raw = input("File: ").strip()
        if not raw:
            if not files:
                print("  No files entered yet — enter at least one, or Ctrl-C to abort.")
                continue
            break
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = DEFAULT_DATA_DIR / p
        if not p.exists():
            print(f"  Not found: {p}")
        elif p in seen:
            print(f"  Already added: {p}")
        else:
            seen.add(p)
            files.append(p)
            print(f"  Added: {p}")
    return files


def parse_files(paths):
    """Returns (records, name_to_lines).
    records: list of (name, year, division_code, contest) tuples
    name_to_lines: dict mapping name to list of (file_index, raw_line) tuples
    """
    records = []
    name_to_lines = defaultdict(list)
    for file_idx, path in enumerate(paths):
        skipped = []
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                cols = [c.strip() for c in line.split(";")]
                if len(cols) < 4:
                    skipped.append(line)
                    continue
                name = cols[0]
                try:
                    year = int(cols[1])
                except ValueError:
                    skipped.append(line)
                    continue
                contest = cols[2]
                div_placing = cols[3]
                # "LH-3" → "LH", "c4a-2" → "c4a", "M6-1" → "M6"
                code = div_placing.rsplit("-", 1)[0] if "-" in div_placing else div_placing
                if name and code:
                    records.append((name, year, code, contest))
                    name_to_lines[name].append((file_idx, line))
                else:
                    skipped.append(line)
        if skipped:
            print(f"  Warning: {len(skipped)} unparseable line(s) in {path.name}:")
            for bad in skipped:
                print(f"    {bad}")
    return records, name_to_lines


if __name__ == "__main__":
    try:
        paths = collect_files()
        records, name_to_lines = parse_files(paths)
        high, medium = analyze(records)
        while True:
            level = input("Minimum confidence level [high/medium]: ").strip().lower()
            if level in ("high", "medium"):
                break
            print("  Enter high or medium.")
        print()
        review_loop(high, medium, name_to_lines, level)
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)
