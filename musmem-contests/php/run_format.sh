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

process() {
    local f="$1"
    local base=$(basename "$f" .txt)
    local out="$FORMATTED/$base.out"
    echo "Processing $base..."
    php "$FORMAT_PHP" "$f" "$out"
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
        echo "Done. $count file(s) written to $FORMATTED"
    fi
fi
