# Antimony: what the Unreal world uses

Everything below is already in this repo. Paths are from the repo root.

## Who we are

Antimony is a systems company and lab for software products, building to be a goliath. The world should feel
magical and be made with the craft that designers and creative VCs respect. First product: **Orbe**, which
"negotiates every sponsorship inside the creator's rules and holds the brand's money until delivery is proven".

## The print (the poster in the world)

- `directions/render-poster/assets/hero-print.png`: the cobalt print that goes in the lightbox. Its mark box is
  in `hero-print.json`, and the crystal mask is in `gem.png`.
- `directions/render-poster/hero_print.py`: remakes the print. It needs `directions/w11-blue-field/assets/still.webp`,
  the wordmark SVG and Timeless Serif.
- The crystal on the print is held to Sky `#94E6FF` in the finish (`hero_post.py`). It should be the brightest
  value in any frame.
- The lightbox: a slim dark anodised case, 1.16 by 1.74 m, on two legs. Its exact build is `lightbox()` in
  `directions/render-poster/poster_hero.py`.

## Identity

- The mark (the Break): `assets/antimony-mark-ink.svg`, `assets/antimony-mark-paper.svg`. All variants are in
  `brand/kit-v3/svg/mark/`, and outlines in `brand/kit-v3/svg/line-mark/`.
- Wordmark and lockups: `assets/antimony-wordmark-*.svg`, `assets/antimony-lockup-horizontal-*.svg`,
  `brand/kit-v3/svg/wordmark/`, `brand/kit-v3/svg/lockup/`.
- Orbe: `assets/orbe-mark.png`, `assets/orbe-mark-on-sky.svg`, `assets/orbe-card.png`, `brand/kit-v3/svg/product/`.
- Rules: `brand/kit-v3/README.txt` and the guidelines site `brand/guidelines/index.html`. Nothing may grow on or
  out of the mark. Keep clear space of 22 units of the mark's 100.

## The giant luminous form (our own, in place of the game's tree)

- The crystal: `assets/crystal-ink.png`, `assets/crystal-paper.png`, `brand/crystals/`, `brand/compare/img/crystal*.webp`.
- The stone: `brand/kit-v3/textures/stone-panel.jpg`, `brand/kit-v3/posters/antimony-poster-stone.png`. The live
  stone on the site is in `directions/final/index.html`.

## Colour

From `brand/kit-v3/colours/antimony-colours.json`:

| Name | Hex | Use in the world |
| --- | --- | --- |
| Cobalt | `#2448FF` | The print; the flowers' deepest glow |
| Sky | `#94E6FF` | The crystal; the brightest light |
| Prussian | `#1F3F7A` | Night shadows, deep mist |
| Ink | `#0B0C0C` | Silhouettes |
| Stone | `#141311` | Rock, ruins |
| Cream | `#EEEAE0` | The pale distance, the haze at its brightest |

Sky tones 100 to 900 (`#E9FAFF` to `#15223A`) step the mist from near-white to night.

## Type

- Timeless Serif: `directions/poster/assets/fonts/TimelessSerifVF.woff2`. It is **licensed to Antimony**, so use it
  in renders and the site, but never ship the font file anywhere public beyond what the licence allows.
- Commit Mono, Newsreader and Schibsted Grotesk are in `assets/fonts/` (SIL Open Font License).

## Earlier worlds to borrow from

- The blue field, with its still, loop and depth map in `directions/w11-blue-field/assets/`. The site already plays it.
- The Blender hero scenes (flowers, mist, glow) are in `directions/render-poster/`. Their first GPU renders are in
  `directions/render-poster/gpu-renders/`.
- The references are in `directions/unreal-world/refs/`.

## Still to come from the owner

- Two references not uploaded yet: the ruins by still water and the cliff over a sea of mist.
- The poster lines. Drafts will be written for approval; there's no final copy yet.
