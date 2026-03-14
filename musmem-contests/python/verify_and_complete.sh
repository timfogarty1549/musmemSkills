#!/bin/bash
# Launch verify_and_complete.py in a new Terminal window.
# Usage: verify_and_complete.sh [filename]   # with or without .out extension
#        verify_and_complete.sh              # all pending .out files

SCRIPT=~/workspace/skills/musmemSkills/musmem-contests/python/verify_and_complete.py

if [ -n "$1" ]; then
    CMD="python3 $SCRIPT '$1'"
else
    CMD="python3 $SCRIPT"
fi

osascript -e "tell application \"Terminal\" to do script \"$CMD\""
