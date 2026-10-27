# Antimony world in Unreal Engine 5: plan

Goal: environments at the level of Elden Ring and FF7 Remake on ultra, made into immersive web scenes for Antimony.
Antimony is a systems company and lab for software products. The world should feel magical and be built with a
craft that designers and creative VCs respect. It is our own world, not a copy of any one game frame.

## The world (from the references in `../render-poster/REFS.md`)

- **One enormous luminous form** fills the sky: our own shape (the crystal or the Break mark grown to the scale of
  a mountain, half transparent, with light breaking through it), not a tree copied from a game.
- **Light through mist:** a low source behind that form throws god rays through layered haze. Each plane back is
  paler: a dark foreground, mid-tone middle ground, near-white distance.
- **Electric flower fields:** glowing blue-white flowers in drifts and clumps across rolling slopes, the nearest huge
  and soft before the lens.
- **Layered silhouettes:** firs on ridges, cliffs into the haze, one domed ruin, a great rock in the foreground.
- **The poster:** the cobalt print in its lightbox, the one made thing in the world, lit from within.
- **One warm accent** at most (embers in a crack, a lit doorway).

## Machine

- Vast, RTX 5090 class, **at least 250 GB disk**, the Vulkan driver present (`vulkaninfo` works).
- Unreal Engine 5.6+ Linux binary from unrealengine.com/linux. The owner signs in, accepts the licence and copies the
  signed download link; the box fetches it with `wget`. Credentials never leave the owner's browser.
- Claude Code runs on the box via `claude remote-control` from the repo folder, so it can drive the engine directly.
- Headless: `UnrealEditor-Cmd <project> -ExecutePythonScript=<script> -RenderOffscreen -unattended`.

## Build

1. Project from the blank template, Python scripting and Movie Render Queue enabled.
2. Assets from Fab (Megascans, free in Unreal): cliffs and rock faces, conifers, ground and grass, small flowers
   recoloured to the electric blue with emissive petals. List kept in `assets.md` with licences.
3. Scene built by a Python script (`build_world.py`) so it is versioned and repeatable: terrain, PCG scatter for
   the flower drifts and firs, the luminous form, Volumetric Clouds, Exponential Height Fog with volumetric fog,
   the god-ray light, the poster lightbox with the print as an emissive texture.
4. Renders with Movie Render Queue: the path tracer for the stills, high-quality Lumen for the loops.

## Web delivery (Unreal itself does not run in the visitor's browser)

| Layer | What | Budget |
| --- | --- | --- |
| Living scenes | Still (WebP/AVIF) + seamless 8-12 s loop (MP4/WebM) + depth map; mouse and tilt parallax in WebGL; scene-to-scene moves | Still under 500 KB, loop under 8 MB per scene |
| Walk-in hero | 3D Gaussian splat trained on the GPU from ~300 path-traced views of the hero scene; viewed in the browser with a WebGL splat renderer; a few metres of free movement | 20-60 MB, loaded only on request |
| Chip the stone | WebGL stone in the page; each chip reveals a product or a line | Small, part of the page |
| Lines | Short poster lines in the Antimony voice, approved by the owner | Text |

## Order

1. Machine and engine up; a test render proves the GPU and headless rendering work.
2. Blockout of the hero scene; previews at 1920x1080 for review against the references.
3. Hero still to final; then its loop; then the splat.
4. Two to four more scenes in the same world.
5. Web: living scenes, then the walk-in hero, the stone and the lines.
