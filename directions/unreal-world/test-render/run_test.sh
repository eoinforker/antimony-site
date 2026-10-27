#!/bin/bash
# Headless GPU test: build the test level, then render one frame offscreen on Vulkan with Movie Render Queue,
# once with the deferred renderer (Lumen) and once with the path tracer.
# Unreal refuses to run as root: run as the 'ue' user, which owns only this project folder (git stays root's).
set -euo pipefail
UE=${UE:-/workspace/UE}
DIR=$(cd "$(dirname "$0")" && pwd)
PROJ="$DIR/TestRender.uproject"
BIN="$UE/Engine/Binaries/Linux"
COMMON=(-RenderOffscreen -unattended -nosplash -nop4 -nosound -stdout -FullStdOutLogOutput)

rm -rf "$DIR/Content" "$DIR/Saved/MovieRenders"  # the build makes every asset fresh
"$BIN/UnrealEditor-Cmd" "$PROJ" -ExecutePythonScript="$DIR/build_test.py" "${COMMON[@]}" 2>&1 | tee "$DIR/build.log"
grep -q ANTIMONY_TEST_BUILD_OK "$DIR/build.log"

render() {  # $1 preset asset, $2 log name
  "$BIN/UnrealEditor" "$PROJ" /Game/TestMap -game -LevelSequence=/Game/TestSeq -MoviePipelineConfig="$1" \
    -vulkan -windowed -resx=1920 -resy=1080 -NoLoadingScreen "${COMMON[@]}" 2>&1 | tee "$DIR/$2"
}
render /Game/TestPreset render.log
render /Game/TestPresetPT render_pt.log || echo "PATH TRACER RENDER FAILED"
ls -la "$DIR/Saved/MovieRenders/"
