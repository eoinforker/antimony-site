#!/bin/bash
# Build the hero scene and render it (run as the 'ue' user, after run_import.sh).
#   ./run_hero.sh            build + Lumen preview
#   ./run_hero.sh final      build + Lumen preview + path-traced final
#   SKIP_BUILD=1 ./run_hero.sh [final]   render only
set -euo pipefail
UE=${UE:-/workspace/UE}
DIR=$(cd "$(dirname "$0")" && pwd)
BIN="$UE/Engine/Binaries/Linux"
PROJ="$DIR/AntimonyWorld.uproject"
COMMON=(-RenderOffscreen -unattended -nosplash -nop4 -nosound -stdout -FullStdOutLogOutput)

if [ -z "${SKIP_BUILD:-}" ]; then
  python3 -I "$DIR/scripts/gen_meshes.py" "$DIR/gen"
  "$BIN/UnrealEditor-Cmd" "$PROJ" -ExecutePythonScript="$DIR/scripts/build_world.py" "${COMMON[@]}" 2>&1 | tee "$DIR/build.log"
  grep -q ANTIMONY_BUILD_OK "$DIR/build.log"
fi

render() {  # $1 preset name
  "$BIN/UnrealEditor" "$PROJ" /Game/Hero/Hero -game -LevelSequence=/Game/Hero/HeroSeq -MoviePipelineConfig="/Game/Hero/$1" \
    -vulkan -windowed -resx=1920 -resy=1080 -NoLoadingScreen "${COMMON[@]}" 2>&1 | tee "$DIR/render_$1.log"
}
render Preview
[ "${1:-}" = final ] && render Final
ls -la "$DIR/Saved/MovieRenders/"
