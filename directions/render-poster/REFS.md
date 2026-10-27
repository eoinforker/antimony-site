# Poster 1 hero: reference brief

The bar is FF7 Remake and Elden Ring at ultra quality: dense, hand-placed detail near the lens, deep atmospheric
perspective, and light you can see in the air. Five reference frames (Elden Ring and Shadow of the Erdtree) were
shared on 27 Oct 2026. What they have in common, and what it means for 11 Starlit coast and 03b Starlit field:

| In the refs | For our frames |
| --- | --- |
| A bright, misty night: the sky is lavender to periwinkle, not black. Mist fills every valley and lifts the far planes almost to white. | Raise `horizon_light` and `mist_glow`. The horizon band should read as luminous haze, and distance should step back in clear, paler layers. |
| God rays fan from a low source behind a silhouette (tree, spire, cliff) and cut through the haze. | Put the `rays` sun low and just behind a stack or spire. Add a thin dense bank at sea or field level for the shafts to show in. |
| The Milky Way is a clear diagonal band of dust and colour (violet and magenta in the ruins frame). The rest of the sky holds only a few bright stars. | Gamma about 2.0 in `world_stars`, lower `--stars` and turn the band diagonal with `--sx/--sy/--sz`. The faint field should drop away. |
| The glowing blue-white flowers grow in drifts and clumps with dark gaps between them. Near the lens they are large, bokeh-soft and almost blown out. | Stronger `drift_field` contrast, fewer plants between drifts, and keep the near bokeh flowers. Flowers glow, but the print stays the brightest value. |
| Silhouettes are layered: conifers on clifftops, a lone gnarled tree, standing stones, ruined arches. | Firs on the stack tops, one sculptural dead tree, and a tilted standing stone in the foreground (03b). |
| There are one or two warm accents in a cool frame: a lit doorway, a golden tree, embers. | Keep the frame cool overall, with one small warm accent at most so it doesn't compete with the cobalt print. |
| Near-field detail: moss, wet stone, debris, puddle reflections. | On the GPU, use `micro()` displacement, `debris(rect, ...)` near the box and wet slabs that catch the sky. |

Render settings for this level: 3840x2160 internal, 2048 samples, noise 0.005, finished at 3840 and supersampled to
1920 (see `gpu/run.sh`).
