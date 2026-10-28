# The Antimony world on the web (first cut)

`index.html` is the living scene from the Unreal world: concept 14, "the print in the field". It is built on the blue
field page (`../../w11-blue-field`): the still, then the seamless 10 s loop drawn through its depth map so the view
breathes and answers the pointer or the phone's tilt, fine grain, sound on request, and the print in the world as the
thing to open (it opens the note with the hero line: "Large things, made with intention, for the people who make the
work.").

## Made from

- `../world/scripts/build_world.py` with the look in `../world/scripts/concepts.py` (concept 14), rendered headless on
  the GPU with `../world/run_final.sh 14`: a 3840 x 2160 still (Lumen, 64 temporal x 2 spatial samples), a 1080 x 2340
  phone still, the two 10 s loops (1920 and 720 wide) and the disparity passes (2/d, sRGB-encoded).
- `build_web.py --concept 14` turns those into `assets/` and writes the print's place in each frame into `index.html`
  (projected through the scene's own camera; the parallax pivot is read from the depth map at the print).
- The full 4K still is in `../world/renders/`.

| Asset | Size | Budget (SITE.md) |
| --- | --- | --- |
| `still.avif` / `still.webp` (2560 wide) | 221 KB / 367 KB | under 500 KB |
| `loop.mp4` / `loop.webm` (1920 wide, 10 s) | about 1.2 MB each | under 8 MB |

## What moves

Every motion is in the materials and repeats exactly every 10 s, so the loop has no seam: each flower's glow swells on
its own phase. The camera is still; the page adds the slow breathing and the pointer parallax from the depth map.

## Not yet

- The opening from `../../blend-c` (the line typed, the characters gathering into the Break) before the scene: the owner
  wants the site to lean on it. That is HTML and WebGL work and needs no GPU.
- The poster display with a grass or paper feel (the owner's note); the note sheet here is the blue field's paper.
- The other worlds (the coast, the starlit field), the walk-in splat of the hero and "chip the stone".
- The phone frame is weaker than the wide one (too much empty sky and bare ground below); worth a recompose.
- The concept frames, for choosing, are in `../world/previews/concepts/index.html`.
