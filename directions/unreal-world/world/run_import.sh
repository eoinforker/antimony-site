#!/bin/bash
# Import the Fab assets into the project (run as the 'ue' user). Safe to rerun: done folders are skipped.
set -euo pipefail
UE=${UE:-/workspace/UE}
DIR=$(cd "$(dirname "$0")" && pwd)
"$UE/Engine/Binaries/Linux/UnrealEditor-Cmd" "$DIR/AntimonyWorld.uproject" -ExecutePythonScript="$DIR/scripts/import_assets.py" \
  -RenderOffscreen -unattended -nosplash -nop4 -nosound -stdout -FullStdOutLogOutput 2>&1 | tee "$DIR/import.log"
