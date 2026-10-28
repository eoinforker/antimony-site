#!/bin/bash
# Build and render the ten concepts (or those given: ./run_concepts.sh 2 5). Run as the 'ue' user.
# Each: rebuild the level with that concept's look, render the Lumen preview, keep it as previews/concepts/NN-name.webp.
set -uo pipefail
UE=${UE:-/workspace/UE}
DIR=$(cd "$(dirname "$0")" && pwd)
BIN="$UE/Engine/Binaries/Linux"
PROJ="$DIR/AntimonyWorld.uproject"
COMMON=(-RenderOffscreen -unattended -nosplash -nop4 -nosound -stdout -FullStdOutLogOutput)
OUT="$DIR/previews/concepts"; mkdir -p "$OUT" "$DIR/logs"
python3 -I "$DIR/scripts/gen_meshes.py" "$DIR/gen" >/dev/null
for n in ${@:-1 2 3 4 5 6 7 8 9 10}; do
  name=$(cd "$DIR/scripts" && python3 -I -c "import sys; sys.path.insert(0,'.'); import concepts; print(concepts.CONCEPTS[$n][0])")
  CONCEPT=$n "$BIN/UnrealEditor-Cmd" "$PROJ" -ExecutePythonScript="$DIR/scripts/build_world.py" "${COMMON[@]}" > "$DIR/logs/build_$n.log" 2>&1
  if ! grep -q ANTIMONY_BUILD_OK "$DIR/logs/build_$n.log"; then echo "CONCEPT $n BUILD FAILED"; grep "LogPython: Error" "$DIR/logs/build_$n.log" | tail -3; continue; fi
  rm -f "$DIR/Saved/MovieRenders/hero_preview_0000.png"
  "$BIN/UnrealEditor" "$PROJ" /Game/Hero/Hero -game -LevelSequence=/Game/Hero/HeroSeq -MoviePipelineConfig=/Game/Hero/Preview \
    -vulkan -windowed -resx=1920 -resy=1080 -NoLoadingScreen "${COMMON[@]}" > "$DIR/logs/render_$n.log" 2>&1
  f=$(printf "%s/%02d-%s" "$OUT" "$n" "$name")
  if [ -f "$DIR/Saved/MovieRenders/hero_preview_0000.png" ]; then
    cp "$DIR/Saved/MovieRenders/hero_preview_0000.png" "$f.png"
    ffmpeg -loglevel error -y -i "$f.png" -q:v 90 "$f.webp" && rm "$f.png"
    echo "CONCEPT $n OK $f.webp"
  else echo "CONCEPT $n RENDER FAILED"; fi
done
