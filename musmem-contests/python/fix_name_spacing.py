#!/usr/bin/env python3
"""
fix_name_spacing.py

Reads a semicolon-delimited .dat file and corrects spacing in athlete last names.
A space is inserted before any capital letter that is not at the start of a word,
unless the preceding character is an apostrophe or dash.

Exceptions (no space inserted):
  - Capital letter at the start of a word (preceded by space or start of string)
  - Capital letter preceded by ' (e.g. O'Brien)
  - Capital letter preceded by - (e.g. Smith-Jones)
  - Capital letter that follows "Mc" or "Mac" at the start of a word

Year cutoff:
  Names are only fixed if the athlete's first appearance year in the file is >= cutoff.
  Default cutoff is 1995. Pass a second argument to override.

Usage:
  python3 fix_name_spacing.py <filename> [cutoff_year]

Output:
  <filename>-new  (input file is never modified)
"""

import sys
import os


def fix_last_name_spacing(s):
    """Add spaces before internal capital letters in a name segment."""
    result = []
    for i, char in enumerate(s):
        if char.isupper() and i > 0 and s[i - 1] != ' ':
            prev = s[i - 1]
            if prev in ("'", '-'):
                # Apostrophe or dash — leave as-is (e.g. O'Brien, Smith-Jones)
                result.append(char)
            else:
                # Find the start of the current word
                word_start = 0
                for j in range(i - 1, -1, -1):
                    if s[j] == ' ':
                        word_start = j + 1
                        break
                word_fragment = s[word_start:i]
                if word_fragment in ('Mc', 'Mac'):
                    # McDonald / MacGregor — leave as-is
                    result.append(char)
                else:
                    result.append(' ')
                    result.append(char)
        else:
            result.append(char)
    return ''.join(result)


def process_name_field(field):
    """
    Fix spacing in the name field (everything before the first semicolon).
    For Western names ("Last, First"), only the last name (before the comma) is fixed.
    For Asian/Hungarian names (no comma), the entire field is fixed.
    """
    comma_pos = field.find(',')
    if comma_pos == -1:
        return fix_last_name_spacing(field)
    else:
        last_name = field[:comma_pos]
        rest = field[comma_pos:]
        return fix_last_name_spacing(last_name) + rest


def process_file(input_path, cutoff_year):
    output_path = input_path + '-new'

    current_name = None
    current_first_year = None

    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', encoding='utf-8') as outfile:

        for line in infile:
            # Preserve blank lines
            if not line.strip():
                outfile.write(line)
                continue

            semi_pos = line.find(';')
            if semi_pos == -1:
                # No semicolon — write unchanged
                outfile.write(line)
                continue

            name_field = line[:semi_pos]
            rest_of_line = line[semi_pos:]

            # Extract year from second column (first field after the name semicolon)
            parts = rest_of_line.split(';')
            year = None
            if len(parts) >= 2:
                try:
                    year = int(parts[1].strip())
                except ValueError:
                    pass

            # Track the current athlete by raw name; reset first year on name change
            raw_name = name_field.strip()
            if raw_name != current_name:
                current_name = raw_name
                current_first_year = year

            # Only fix if first-seen year meets the cutoff
            if current_first_year is not None and current_first_year >= cutoff_year:
                fixed_name = process_name_field(name_field)
            else:
                fixed_name = name_field

            outfile.write(fixed_name + rest_of_line)

    print(f"Done. Output written to: {output_path}")


if __name__ == '__main__':
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(f"Usage: python3 {os.path.basename(sys.argv[0])} <filename> [cutoff_year]")
        sys.exit(1)

    input_path = sys.argv[1]
    if not os.path.isfile(input_path):
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    cutoff_year = 1995
    if len(sys.argv) == 3:
        try:
            cutoff_year = int(sys.argv[2])
        except ValueError:
            print(f"Error: cutoff_year must be an integer")
            sys.exit(1)

    process_file(input_path, cutoff_year)
