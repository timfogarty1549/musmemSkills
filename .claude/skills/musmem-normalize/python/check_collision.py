#!/usr/bin/env python3
"""
check_collision.py — checks whether a new target name already exists in file1 or file2.

Called immediately when the user enters an expression containing a quoted (new) target name,
before recording the decision.

Usage:
    python3 check_collision.py --name "New Name" --file1 PATH --file2 PATH

Output: one line per collision found, or nothing if clean.
Exit code 1 if any collision found, 0 if clean.
"""
import argparse, sys

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--name', required=True)
    p.add_argument('--file1', required=True)
    p.add_argument('--file2', required=True)
    return p.parse_args()

def name_exists_in_file(dat_path, name):
    with open(dat_path, encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(';')
            if len(parts) >= 2 and parts[0].strip() == name:
                return True
    return False

def main():
    args = parse_args()
    found = []
    if name_exists_in_file(args.file1, args.name):
        found.append('file1')
    if name_exists_in_file(args.file2, args.name):
        found.append('file2')

    if found:
        print(f"WARNING: '{args.name}' already exists in {', '.join(found)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
