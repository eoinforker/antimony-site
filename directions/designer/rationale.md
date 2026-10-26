# Lens

## The idea

The Break is a stone with a crystal grown in its seam. This page takes that literally and then asks one more thing of it: if the crystal is real glass, what do you see through it?

The whole page is a single close-up of the mark made as an object: dark honed stone, wet from the rain, the seam cut right through it, the crystal set in the cavity as clear glass. It stands on a parapet at night with the city far behind it, out of focus. Its face holds the reflections of the street. Through the crystal, and only through the crystal, there is somewhere else: a meadow in full sun under a big sky, with the wind moving through it. The seam, which cuts all the way through, lets a hairline of the same daylight show.

Move the pointer and the stone tilts a fraction; the meadow inside swings and bends the way a view through cut glass does, facet by facet, with a trace of colour fringing at the edges. Click the crystal and the light gets out: the daylight pours through the crystal and the seam, across the face of the stone and into the rain, then settles back. The sound follows the same line: rain outside, wind and something warm inside, crossfading as you move towards the crystal, and one clear glass tone when the light is let through. It is muted until you ask for it.

The type is one line: the wordmark and "Software for the people who make the work". Orbe, immiscible and Idyll are three small links in the corner.

## Why it should hold up

- **It comes from the mark and nowhere else.** The stone, the seam at 16 degrees and the crystal are the logo's exact geometry, built in three dimensions. Nothing is borrowed from another brand, and the page could not belong to another company.
- **One idea, carried all the way.** The mark is not decoration on a backdrop; it is the subject, the light source and the interface. Looking, tilting and clicking all happen to the crystal itself.
- **The metaphor is earned, not stated.** A hard, dark, closed object that, looked at properly, holds a whole bright world: that is what good software is to the people who use it, and it is the brief's rain that clears to sun. The page never says so.
- **Physics, not effects.** The stone, glass and water are path traced in Cycles. The view through the crystal is not a picture pasted in: every pixel stores the direction a ray leaves the glass, measured from the real geometry, so the live meadow bends exactly as that crystal bends light. Light is added in linear space and passed through one view transform, so the daylight on the stone, in the seam and on the wet parapet comes from the same numbers.
- **Restraint.** One frame, one interaction, one line of type. No scroll, no counters, no interface furniture.

## How it is made

- `render/lens_scene.py`: the stone scene in Blender (Cycles, CPU). Four passes from one fixed camera: the night beauty, how much light passes through the openings, where each ray lands, and the daylight let out.
- `render/meadow.py`: the meadow, rendered once as a sky layer and a grass layer, so the wind can move the grass on the page.
- `render/build_assets.py`: turns the linear passes into the page's textures and composes the still that shows before WebGL is ready.
- `index.html`: the live layer (WebGL), the sound (Web Audio, all synthesised on the page) and the type.
