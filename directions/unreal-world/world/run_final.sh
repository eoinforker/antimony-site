#!/bin/bash
# Take one concept to final (run as the 'ue' user): build, then the 4K still, the phone still, the two 10 s loops and
# the two depth passes, back to back. Then ../web/build_web.py makes the web assets (run that as root after).
#   ./run_final.sh 1
set -uo pipefail
UE=${UE:-/workspace/UE}
DIR=$(cd "$(dirname "$0")" && pwd)
BIN="$UE/Engine/Binaries/Linux"
PROJ="$DIR/AntimonyWorld.uproject"
COMMON=(-RenderOffscreen -unattended -nosplash -nop4 -nosound -stdout -FullStdOutLogOutput)
n=${1:-1}; mkdir -p "$DIR/logs"
python3 -I "$DIR/scripts/gen_meshes.py" "$DIR/gen" >/dev/null
rm -rf "$DIR/Saved/MovieRenders"
CONCEPT=$n "$BIN/UnrealEditor-Cmd" "$PROJ" -ExecutePythonScript="$DIR/scripts/build_world.py" "${COMMON[@]}" > "$DIR/logs/final_build_$n.log" 2>&1
grep -q ANTIMONY_BUILD_OK "$DIR/logs/final_build_$n.log" || { echo "FINAL BUILD FAILED"; exit 1; }
for job in "HeroSeq Final" "PhoneSeq PhoneFinal" "HeroSeq Depth" "PhoneSeq PhoneDepth" "HeroLoop Loop" "PhoneLoopSeq PhoneLoop"; do
  set -- $job
  w=1920; h=1080; case $2 in Phone*) w=720; h=1560;; esac
  "$BIN/UnrealEditor" "$PROJ" /Game/Hero/Hero -game -LevelSequence=/Game/Hero/$1 -MoviePipelineConfig=/Game/Hero/$2 \
    -vulkan -windowed -resx=$w -resy=$h -NoLoadingScreen "${COMMON[@]}" > "$DIR/logs/final_$2.log" 2>&1
  echo "FINAL $2 $(grep -c 'Movie Pipeline completed' "$DIR/logs/final_$2.log") $(find "$DIR/Saved/MovieRenders" -name '*.png' | wc -l) files"
done
echo FINAL_DONE
