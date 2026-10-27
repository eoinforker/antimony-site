#!/usr/bin/env bash
# Poster 1 hero finals on a GPU box (Vast, RTX 5090). Run from the folder holding poster_hero.py, hero_post.py
# and assets/ (the print). Fetches Blender 4.5 LTS and the CC0 / public-domain assets itself, then renders
# 11 Starlit coast and 03b Starlit field at 3840x2160 and finishes them at 3840 and 1920 wide.
#   bash gpu/run.sh            everything
#   ONLY=11 bash gpu/run.sh    one setting
#   DRY=1 bash gpu/run.sh      build the scenes and print the corners, no render
set -euo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd); cd "$HERE"
W=${W:-/workspace/poster}; A=$W/assets; B=$W/blender; OUT=$HERE/out; mkdir -p "$A" "$OUT"
RES=${RES:-3840x2160}; SAMPLES=${SAMPLES:-2048}; NOISE=${NOISE:-0.005}; PH_RES=${PH_RES:-2k}

# ---- Blender 4.5 LTS
if [ ! -x "$B/blender" ]; then
  v=$(curl -fsSL https://download.blender.org/release/Blender4.5/ | grep -o 'blender-4\.5\.[0-9]*-linux-x64\.tar\.xz' | sort -V | tail -1)
  echo "fetching $v"; mkdir -p "$B"
  curl -fsSL "https://download.blender.org/release/Blender4.5/$v" | tar -xJ -C "$B" --strip-components=1
fi
apt-get install -y -qq libxi6 libxkbcommon0 libsm6 libxrender1 libxxf86vm1 libgl1 >/dev/null 2>&1 || true
python3 -m pip install -q numpy pillow >/dev/null 2>&1 || true

# ---- assets (Poly Haven blends with their textures, saved under the names poster_hero.py expects)
python3 - "$A" "$PH_RES" <<'PY'
import json, os, sys, urllib.request
A, res = sys.argv[1], sys.argv[2]
def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0: return
    os.makedirs(os.path.dirname(path), exist_ok=True); print('  ', os.path.relpath(path, A))
    urllib.request.urlretrieve(url, path + '.part'); os.replace(path + '.part', path)
# asset id -> (folder, blend filename the scene loads)
want = {'flower_heliophila': ('flower_heliophila', 'flower_heliophila_2k.blend'),
        'periwinkle_plant': ('periwinkle_plant', 'periwinkle_plant_1k.blend'),
        'fir_tree_01': ('fir_tree_01_lod2', 'fir_tree_01_lod2.blend'),
        'coastal_cliff_01': ('coastal_cliff_01', 'coastal_cliff_01_1k.blend'),
        'coastal_cliff_02': ('coastal_cliff_02', 'coastal_cliff_02_1k.blend'),
        'rock_face_01': ('rock_face_01', 'rock_face_01_1k.blend')}
for aid, (folder, name) in want.items():
    files = json.load(urllib.request.urlopen('https://api.polyhaven.com/files/' + aid))['blend']
    b = files.get(res, files.get('2k', files['1k']))['blend']
    d = os.path.join(A, 'polyhaven', folder)
    get(b['url'], os.path.join(d, name))
    for rel, f in b.get('include', {}).items(): get(f['url'], os.path.join(d, rel))
get('https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/starmap_2020_8k_gal.exr',
    os.path.join(A, 'nasa_svs', 'starmap_2020_8k_gal.exr'))
g = os.path.join(A, 'ambientcg', 'Ground037')
if not os.path.isdir(g) or not os.listdir(g):
    import io, zipfile
    req = urllib.request.Request('https://ambientcg.com/get?file=Ground037_4K-JPG.zip', headers={'User-Agent': 'curl/8'})
    zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(req).read())).extractall(g); print('   ambientcg/Ground037')
PY

nvidia-smi --query-gpu=name,memory.used,utilization.gpu --format=csv,noheader || true

# ---- render and finish
common=(--device OPTIX --res "$RES" --samples "$SAMPLES" --noise "$NOISE" --time 0 --vstep 1
        --ph "$A/polyhaven" --acg "$A/ambientcg" --starmap "$A/nasa_svs/starmap_2020_8k_gal.exr"
        --print assets/hero-print.png --bloom 0.5 --bloom-th 2.0 --print-e 2.0 --petal-glow 14 --drops 800)
declare -A EXTRA=([11]="--stars 50 --sx -10 --sy -35 --sz 95" [3b]="--stars 40 --sx -10 --sy -35 --sz 75")
declare -A NAME=([11]=11-starlit-coast [3b]=03b-starlit-field)
declare -A POST=([11]="--sat 1.15 --lift 0.5 --halation 1.6" [3b]="--sat 1.3 --lift 0.5 --halation 1.6")
for s in ${ONLY:-11 3b}; do
  log=$OUT/r$s.log; echo "== $s -> $log"
  "$B/blender" -b --factory-startup -P poster_hero.py -- --setting "$s" "${common[@]}" ${EXTRA[$s]} \
    ${DRY:+--dry} --out "$OUT/r$s.png" --data "$OUT/d$s.png" 2>&1 | tee "$log" | grep -E "Error|Traceback|corners|Time|saved|^\[" || true
  [ -n "${DRY:-}" ] && continue
  for w in 3840 1920; do
    python3 -I hero_post.py "$OUT/r$s.png" "$OUT/r$s.png.json" "$OUT/${NAME[$s]}-$w.png" --w $w ${POST[$s]}
  done
done
ls -la "$OUT"
