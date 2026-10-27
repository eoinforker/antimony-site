# Poster 1 hero: GPU handoff (11 Starlit coast, 03b Starlit field)

The quick first frames are in `first-frames/` (`11-starlit-coast.png`, `03b-starlit-field.png`), rendered on the
CPU at 960x540 with 32 samples. The same script renders the finals on a GPU unchanged; only the options differ.

## Files to upload

From this folder (`directions/render-poster/`):

- `poster_hero.py` (the scene, one setting per `--setting`)
- `hero_post.py` (the finish: crystal hold, grade, halation, chromatic aberration, vignette, grain, downsample)
- `assets/hero-print.png`, `assets/hero-print.json`, `assets/gem.png` (the cobalt print, its mark box, the crystal mask)
- `hero_print.py` only if the print is to be remade (it needs `../w11-blue-field/assets/still.webp`, the Timeless
  Serif font in `../poster/assets/fonts/` and the wordmark SVG)

From the shared asset cache (`S = /tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad`), keep the
same folder layout under one `assets` folder on the GPU machine:

| Path under `S/assets/` | Used by | Size |
| --- | --- | --- |
| `nasa_svs/starmap_2020_8k_gal.exr` | 11, 03b (the sky) | 161 MB |
| `polyhaven/flower_heliophila/` (blend and textures) | 11, 03b | |
| `polyhaven/periwinkle_plant/` | 11, 03b | |
| `polyhaven/fir_tree_01_lod2/` (blend and textures, including the trunk maps) | 11, 03b | |
| `polyhaven/coastal_cliff_01/`, `polyhaven/coastal_cliff_02/` | 11, 03b | |
| `polyhaven/rock_face_01/` | 11 | |
| `ambientcg/Ground037/` | 11 | |

A fresh copy of any Poly Haven item can come from `https://api.polyhaven.com/files/<asset>` (blend at 1k or 2k).
The star map is at `https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/starmap_2020_8k_gal.exr` (public domain).
Licences are listed in `credits.txt`.

## Final renders

Point the script at the uploaded assets with `--ph`, `--acg` and `--starmap`. Blender 4.5 LTS. With `A` as the
uploaded assets folder:

```
blender -b --factory-startup -P poster_hero.py -- --setting 11 --device OPTIX \
  --res 2560x1440 --samples 1024 --noise 0.01 --time 0 --vstep 1 \
  --ph A/polyhaven --acg A/ambientcg --starmap A/nasa_svs/starmap_2020_8k_gal.exr \
  --print assets/hero-print.png --bloom 0.5 --bloom-th 2.0 --print-e 2.0 \
  --stars 50 --sx -10 --sy -35 --sz 95 --petal-glow 14 --drops 800 \
  --out out/r11.png --data out/d11.png

blender -b --factory-startup -P poster_hero.py -- --setting 3b --device OPTIX \
  --res 2560x1440 --samples 1024 --noise 0.01 --time 0 --vstep 1 \
  --ph A/polyhaven --acg A/ambientcg --starmap A/nasa_svs/starmap_2020_8k_gal.exr \
  --print assets/hero-print.png --bloom 0.5 --bloom-th 2.0 --print-e 2.0 \
  --stars 40 --sx -10 --sy -35 --sz 75 --petal-glow 14 --drops 800 \
  --out out/r3b.png --data out/d3b.png
```

- `--device` takes CPU, OPTIX, CUDA, HIP or METAL. `--time 0` means no cap; set seconds to cap.
- Each render writes the beauty, `<out>.json` (the print's four corners, the mark's box and the crystal's box in
  pixels, and the camera), and the data pass: `d*.png` (16 bit, linear) and `d*.npz` (the same, exact). The data
  pass holds R depth / 100 m, G standing water, and B the object (0.25 print, 0.5 glass, 0.75 lightbox case).
- Add `--dry` to build and print the corners without rendering.

## Post (the finish, then 1920x1080)

```
python3 -I hero_post.py out/r11.png out/r11.png.json first-frames/11-starlit-coast-full.png \
  --w 1920 --sat 1.15 --lift 0.5 --halation 1.6
python3 -I hero_post.py out/r3b.png out/r3b.png.json first-frames/03b-starlit-field-full.png \
  --w 1920 --sat 1.3 --lift 0.5 --halation 1.6
```

It downsamples to 1920 wide and holds the crystal on the print to #94E6FF, mapped through the print's corners. It
then applies the grade, halation, slight chromatic aberration, vignette and fine grain. It writes `<out>.json` with the
corners at the output size.

## Remaining fixes

### 11 Starlit coast

- **Milky Way:** make it stronger and placed as a clear diagonal over the frame. Tune `--stars` (50 to 80) and the
  rotation `--sx/--sy/--sz`. Thin the `high_air` haze in `s_coast` further if it veils the sky.
- **Horizon glow and god rays:** add a real luminous glow on the horizon with god rays. Raise `horizon_light` and
  `mist_glow` in `s_coast`, set the source lower and just behind a stack so its shadows cut shafts through
  `sea_mist`, and add a thin denser bank at sea level for the rays to show in.
- **Flowers:** they still band at mid-distance. Use more and stronger drifts (in `drift_field`, larger
  `drift_scale` contrast, fewer plants between drifts) and keep the near bokeh flowers.
- **Sea stacks:** the near right stack is a little heavy. Consider moving it further back or scaling it down.
- **Debris:** for FF7 Remake level detail near the box, call `debris(rect, z=...)` on the slope in front of it.

### 03b Starlit field

- **Stars:** they are too dense and even. Raise the gamma in `world_stars` (1.6 to about 2.0) and lower `--stars`
  so the faint field drops away and the Milky Way and a few bright stars remain.
- **Horizon glow and god rays:** add a horizon glow and god rays through the mist banks between the spires. Raise
  the `rays` sun, set it lower and behind a spire, and add a denser low bank.
- **Flowers:** use stronger drifts rather than an even carpet.
- **Spires:** the near spires could be a little broader at the foot.

### Both

- **Glow balance:** check that the print stays the brightest value after the post. If the flowers' glow competes,
  lower `--petal-glow`.
- **Displacement and debris:** on the GPU, micro-displacement (`wet_slabs(..., disp=...)`, `micro()`) and hand-placed
  debris can be afforded near the lens.
