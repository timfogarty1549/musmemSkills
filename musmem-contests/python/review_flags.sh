#!/bin/bash
# Launch review_flags.py in a new Terminal window.
# Usage: review_flags.sh [filename]   # with or without .out extension
#        review_flags.sh              # all .out files with <<<< lines

SCRIPT=~/workspace/skills/musmemSkills/musmem-contests/python/review_flags.py

if [ -n "$1" ]; then
    CMD="python3 $SCRIPT '$1'"
else
    CMD="python3 $SCRIPT"
fi

osascript -e "tell application \"Terminal\" to do script \"$CMD\""
