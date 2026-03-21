#!/bin/bash
# run_format.sh — Process flat files through format.php
#
# Usage:
#   ./run_format.sh                         # format all unprocessed files
#   ./run_format.sh 2025_olympia-ifbb-male  # format one file (with or without .txt)
#   ./run_format.sh --force                 # reprocess all files, overwriting existing .out
#   ./run_format.sh --force 2025_olympia-ifbb-male  # reprocess one file

INCOMING=~/workspace/musmem/incoming
FORMATTED=~/workspace/musmem/formatted
FORMAT_PHP=~/workspace/skills/musmemSkills/musmem-contests/php/format.php

mkdir -p "$FORMATTED"

# Parse --force flag
FORCE=0
if [ "$1" = "--force" ]; then
    FORCE=1
    shift
fi

TOTAL_ATHLETES=0

process() {
    local f="$1"
    local base=$(basename "$f" .txt)
    local out="$FORMATTED/$base.out"
    echo "Processing $base..."
    local output
    output=$(php "$FORMAT_PHP" "$f" "$out" 2>&1)
    echo "$output" | grep -v '^ATHLETES_COUNT='
    local count
    count=$(echo "$output" | grep '^ATHLETES_COUNT=' | cut -d= -f2)
    count=${count:-0}
    TOTAL_ATHLETES=$((TOTAL_ATHLETES + count))
    # echo "  → $count athletes"
}

if [ -n "$1" ]; then
    # Single file mode — accept name with or without .txt
    base="${1%.txt}"
    f="$INCOMING/$base.txt"
    if [ ! -f "$f" ]; then
        echo "File not found: $f"
        exit 1
    fi
    process "$f"
    echo "Total: $TOTAL_ATHLETES athletes"
else
    # Batch mode
    count=0
    for f in "$INCOMING"/*.txt; do
        [ -e "$f" ] || continue
        base=$(basename "$f" .txt)
        if [ "$FORCE" -eq 1 ] || [ ! -f "$FORMATTED/$base.out" ]; then
            process "$f"
            count=$((count + 1))
        fi
    done
    if [ "$count" -eq 0 ]; then
        echo "No unprocessed files found."
    else
        echo "Done. $count file(s) written to $FORMATTED ($TOTAL_ATHLETES total athletes)"
    fi
fi
