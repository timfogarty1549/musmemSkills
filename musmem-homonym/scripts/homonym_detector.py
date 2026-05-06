from collections import defaultdict
from pathlib import Path

DEFAULT_DATA_DIR = Path.home() / "workspace" / "musmem" / "data"

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
    Returns (high, medium, low).
    Each item is (name, clusters) where clusters is a list of year lists.

    High  — Scenario 2: 50+ codes in early clusters, open codes in late cluster (age reversal)
    Medium — Scenario 1: gap ≥ 10y, late cluster is 20+ years after first appearance, late has open codes
    Low   — unused; kept for interface compatibility
    """
    by_name = defaultdict(list)
    for name, year, code in records:
        by_name[name].append((year, code))

    high = []
    medium = []

    for name, appearances in by_name.items():
        years_sorted = sorted(set(y for y, _ in appearances))
        if len(years_sorted) < 2:
            continue
        if not find_gaps(years_sorted):
            continue

        clusters = cluster_years(years_sorted)
        if len(clusters) < 2:
            continue

        year_to_codes = defaultdict(set)
        for y, code in appearances:
            year_to_codes[y].add(code)

        def cluster_codes(cluster):
            codes = set()
            for y in cluster:
                codes |= year_to_codes[y]
            return codes

        late_codes = cluster_codes(clusters[-1])

        pre_last_codes = set()
        for c in clusters[:-1]:
            pre_last_codes |= cluster_codes(c)

        first_year = years_sorted[0]
        late_has_open = any(is_open(c) for c in late_codes)

        # Scenario 2: 50+ division in any early cluster, then open division later — age reversal
        scenario2 = any(is_fifty_plus(c) for c in pre_last_codes) and late_has_open

        # Scenario 1: late cluster is 20+ years after first appearance, and contains open divisions
        scenario1 = (max(clusters[-1]) - first_year >= 20) and late_has_open

        if scenario2:
            high.append((name, clusters))
        elif scenario1:
            medium.append((name, clusters))

    return high, medium, []


def format_clusters(clusters):
    parts = []
    for c in clusters:
        if len(c) == 1:
            parts.append(str(c[0]))
        else:
            parts.append(f"{min(c)}–{max(c)}")
    return ", ".join(parts)


def print_report(high, medium, low, min_confidence):
    if min_confidence == "high":
        names = high
    elif min_confidence == "medium":
        names = high + medium
    else:
        names = high + medium + low

    for name, clusters in sorted(names, key=lambda x: x[0]):
        print(f"{name}; {format_clusters(clusters)}")

    print(f"\n{len(names)} names flagged")


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
    """Returns list of (name, year, division_code) tuples."""
    records = []
    for path in paths:
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
                div_placing = cols[3]
                # "LH-3" → "LH", "c4a-2" → "c4a", "M6-1" → "M6"
                code = div_placing.rsplit("-", 1)[0] if "-" in div_placing else div_placing
                if name and code:
                    records.append((name, year, code))
                else:
                    skipped.append(line)
        if skipped:
            print(f"  Warning: {len(skipped)} unparseable line(s) in {path.name}:")
            for bad in skipped:
                print(f"    {bad}")
    return records


if __name__ == "__main__":
    paths = collect_files()
    records = parse_files(paths)
    high, medium, low = analyze(records)
    while True:
        level = input("Minimum confidence level [high/medium/low]: ").strip().lower()
        if level in ("high", "medium", "low"):
            break
        print("  Enter high, medium, or low.")
    print()
    print_report(high, medium, low, level)
