#!/bin/bash
# Launch append_to_master.py in a new Terminal window.
# Usage: append_to_master.sh [filename]   # with or without .out extension
#        append_to_master.sh              # all files in completed/

SCRIPT=~/workspace/skills/musmemSkills/musmem-contests/python/append_to_master.py

if [ -n "$1" ]; then
    CMD="python3 $SCRIPT '$1'"
else
    CMD="python3 $SCRIPT"
fi

osascript -e "tell application \"Terminal\" to do script \"$CMD\""
