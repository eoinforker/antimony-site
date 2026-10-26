# The hero slot: dropping in the meadow render

The page has a second view, "outside". The visitor presses **Look outside** (bottom left; Escape or **Come back in** returns). The stone, wordmark and line fade, then the paper rises like a blind and shows the hero render behind it, full bleed. The daylight on the paper at rest is meant to be the light from this same scene, so the two views belong together.

Right now the slot shows a stand-in: `assets/hero/meadow.webp`, a 1440 by 900 WebP made from `../grow/shots/rest-desktop.png`. **Replace it.** The stand-in has Grow's own wordmark, line and grass at the seam baked in. The real render must not have any of those: no type, and nothing growing on or out of the mark.

## What to deliver (from `directions/hero-meadow/`)

| File | Use | Spec |
| --- | --- | --- |
| `meadow.webp` | The still. Also the poster and fallback for the loop | 2560 by 1600 (16:10), WebP quality about 80, aim under 450 KB |
| `meadow.mp4` | The seamless loop for Safari and iOS | H.264, `yuv420p`, no audio track, `-movflags +faststart`, 1920 by 1200, 8 to 12 s, under 8 MB |
| `meadow.webm` | The same loop for Chrome and Firefox | VP9, no audio, same size and length, under 8 MB |
| `meadow-portrait.webp` (optional) | Still for phones held upright | 1290 by 2796 or similar 9:19.5, same scene recomposed |
| `meadow-portrait.mp4` / `.webm` (optional) | Loop for phones held upright | 1080 by 2340, same specs as above |

The loop's first and last frames must match exactly. The page loops with the browser's own `loop`, so any jump at the seam will show.

Example encodes from a frame sequence or a master file:

```sh
ffmpeg -i master.mov -an -c:v libx264 -crf 22 -preset slow -pix_fmt yuv420p -movflags +faststart -vf scale=1920:1200 meadow.mp4
ffmpeg -i master.mov -an -c:v libvpx-vp9 -crf 34 -b:v 0 -row-mt 1 -vf scale=1920:1200 meadow.webm
```

## How to drop them in

1. Copy the files into `directions/final/assets/hero/`, overwriting `meadow.webp`.
2. In `directions/final/index.html`, find the block marked `Outside: the slot for the hero render` (the `<div class="hero" id="hero">`). Fill in its attributes:

   ```html
   <div class="hero" id="hero" role="img" aria-hidden="true"
     data-still="assets/hero/meadow.webp"
     data-mp4="assets/hero/meadow.mp4"
     data-webm="assets/hero/meadow.webm"
     data-still-portrait="assets/hero/meadow-portrait.webp"
     data-mp4-portrait="assets/hero/meadow-portrait.mp4"
     data-webm-portrait="assets/hero/meadow-portrait.webm"
     data-pos="50% 55%"
     data-alt="A sunlit meadow under a wide sky, with the Antimony stone at rest in the grass"></div>
   ```

   - Leave any attribute empty (`""`) if that file does not exist; the page then uses the still alone, or the landscape files on phones.
   - `data-pos` is the focal point used when the frame is cropped to fit the screen (CSS `object-position`). Set it to where the stone sits in the frame, so it stays in view on narrow screens.
   - `data-alt` is what screen readers hear in the outside view. Describe the real render plainly.
3. Nothing else changes. No code edits are needed.

## How it behaves

- **Nothing loads until it is wanted.** The still starts loading when the visitor points at, focuses or touches **Look outside**; the loop only then too. The first visit's payload stays at the page and its two fonts.
- The blind waits until the still has decoded (at most 2.5 s), so it never rises onto a blank frame. The loop fades in over the still once it is actually playing.
- **Reduced motion:** the still only, no loop, and the blind becomes a cut.
- The loop pauses 1.7 s after the visitor comes back in. The live stone stops drawing while the visitor is outside, to save power.
- With sound on, the room tone opens up (a wider, airier filter) while outside.

## How to check it

Serve `directions/` (for example `python3 -m http.server 8845` from `/home/user/antimony-site`) and open
`http://localhost:8845/directions/final/index.html?rest`, then press **Look outside**. Check at 1440 by 900 and at 390 by 844, and with the system set to reduce motion.
