#!/bin/bash
# Launch verify_and_append.py in a new Terminal window.
# Usage: verify_and_append.sh [filename]   # with or without .out extension
#        verify_and_append.sh              # all pending .out files

SCRIPT=~/workspace/skills/musmemSkills/musmem-contests/python/verify_and_append.py

if [ -n "$1" ]; then
    CMD="python3 $SCRIPT '$1'"
else
    CMD="python3 $SCRIPT"
fi

osascript -e "tell application \"Terminal\" to do script \"$CMD\""
