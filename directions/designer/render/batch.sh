#!/bin/sh
# Runs a list of renders under one hold of the shared lock: each line of the list file is the
# argument string for one Blender run, script first (lens_scene.py or meadow.py).
. /tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad/dir-designer/env.sh
cd "$(dirname "$0")"
flock "$L" sh -c '
while read -r script args; do
  [ -z "$script" ] && continue
  s=$(date +%s)
  nice -n 5 "$B" -b -P "$script" -- $args 2>&1 | grep -E "RENDER|Error|rror" | sed "s#^#$script $args: #"
  echo "  wall $(( $(date +%s) - s ))s"
done < "$1"
' sh "$1"
