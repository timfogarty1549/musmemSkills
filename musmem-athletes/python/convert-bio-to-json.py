#!/usr/bin/env python3
"""
Convert a bio .dat file to JSON.
Usage: python convert-bio-to-json.py <input.dat>
Output: <input.json> in the same directory.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def parse_header_line(line: str) -> Optional[Tuple[str, str]]:
    """Parse a comment line '! CODE= label' into (code, label). Returns None if not a header line."""
    if not line.startswith("! ") or "=" not in line:
        return None
    rest = line[2:].strip()
    eq = rest.index("=")
    code = rest[:eq].strip()
    label = rest[eq + 1 :].strip()
    return (code, label) if code and label else None


def build_code_to_label(lines: List[str]) -> Dict[str, str]:
    """Build mapping from short code to long label from header lines."""
    code_to_label = {}
    for line in lines:
        if not line.startswith("!"):
            break
        if line.startswith("!!"):
            continue
        parsed = parse_header_line(line)
        if parsed:
            code, label = parsed
            code_to_label[code] = label
    return code_to_label


def parse_data_line(line: str, code_to_label: Dict[str, str]) -> Optional[dict]:
    """
    Parse a single data line. First segment is athlete name; rest are key=value.
    Returns a dict with 'name' and long-label keys; url is always a list; duplicates are lists.
    """
    line = line.strip()
    if not line or line.startswith("!"):
        return None
    parts = line.split(";")
    name = (parts[0] or "").strip()
    if not name:
        return None

    # Collect all key-value pairs; skip code "1"
    raw: Dict[str, List[str]] = {}
    for part in parts[1:]:
        part = part.strip()
        if "=" not in part:
            continue
        eq_idx = part.index("=")
        code = part[:eq_idx].strip()
        value = part[eq_idx + 1 :].strip()
        if code == "1":
            continue
        if code not in code_to_label:
            continue
        label = code_to_label[code]
        raw.setdefault(label, []).append(value)

    out: dict = {"name": name}
    url_label = code_to_label.get("u", "url")
    for label, values in raw.items():
        if label == url_label:
            out[label] = values
        elif len(values) == 1:
            out[label] = values[0]
        else:
            out[label] = values
    return out


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python convert-bio-to-json.py <input.dat>", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    if input_path.suffix.lower() != ".dat":
        print("Warning: input does not have .dat extension", file=sys.stderr)
    output_path = input_path.with_suffix(".json")

    lines: List[str] = []
    try:
        with open(input_path, "rb") as f:
            for line_no, raw in enumerate(f, start=1):
                try:
                    lines.append(raw.decode("utf-8"))
                except UnicodeDecodeError as e:
                    print(
                        f"UTF-8 decode error on line {line_no} of {input_path}: {e}",
                        file=sys.stderr,
                    )
                    sys.exit(1)
    except OSError as e:
        print(f"Error reading {input_path}: {e}", file=sys.stderr)
        sys.exit(1)

    code_to_label = build_code_to_label(lines)
    athletes = []
    for line in lines:
        if line.startswith("!!"):
            continue
        obj = parse_data_line(line, code_to_label)
        if obj is not None:
            athletes.append(obj)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(athletes, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(athletes)} athletes to {output_path}")


if __name__ == "__main__":
    main()
