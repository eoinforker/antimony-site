# How the reference sites are built

Taken apart on 25 October 2026 by loading each site in a browser and recording every request, every script, every font, every canvas context and every WebGL shader the page compiled. Facts below are what the pages loaded; where something is an inference it says so.

## The summary

None of the sites that feel alive are built from a template or a big animation framework. Each one has **one purpose-built renderer** for its signature moment, plus **licensed or custom typefaces**, plus **real media** (video, hand-drawn art, data). Everything around that one moment is plain and fast.

Our earlier pages were 2D canvas sketches with a free font. That is why they read as lame next to these.

## Site by site

| Site | Stack | Signature technique | Type |
| --- | --- | --- | --- |
| terminal.cyberspace.online | Vite, raw WebGL2, a PWA (Workbox), WebAssembly builds of `vim` and `cowsay` | A physically modelled CRT: text is drawn to an 8-bit texture, then six shader passes model the electron beam (Gaussian spot plus a "peaking" unsharp mask), scanlines whose width grows with brightness, phosphor persistence (each frame keeps the decayed previous frame), a thresholded bloom, barrel distortion, an aperture grille, beam misconvergence, a rolling shutter bar, flicker and integer-hash noise. The shader comments cite the real analogue circuitry. | Pixel font baked into the texture |
| cyberspace.online | Nuxt (Vue), Three.js (`LineMaterial`), Firestore, Iconify, Cloudflare Turnstile | A wireframe globe drawn from the `world-atlas` 110m country file with Three.js fat lines; everything else is plain monospace, keyboard-driven and themeable (Dark, Light, LCD, C64, VT320, Matrix, Poetry, Brutalist, Grid, Crypt, Bubblegum, Tops) | JetBrains Mono only |
| theghostintheshell-anime.jp | Astro islands, GSAP, Three.js `ShaderMaterial` (22 shaders), body-scroll-lock | A loading screen with a "GradationDance" shader gradient, a "PixelAnimation" shader that builds images out of pixels, mask-reveal text. Each effect is its own small Astro component | Noto Sans JP, Roboto |
| floor796.com | Hand-written JavaScript, 2D canvas, a pool of Web Workers, a Brotli decoder compiled to WebAssembly, a `matrix.json` tile index | One giant hand-drawn animated scene, streamed in tiles: workers fetch Brotli-compressed frame data and decode it off the main thread, so the page can hold an enormous animated world | Undertale fonts |
| fal.ai | Webflow, GSAP 3.15 with ScrollTrigger, jQuery, `smooothy` (slider), their own scripts hosted on GitHub Pages (`angle-marks.js`, `text-selection-v2.js`) | A seamless parallax video loop as the hero, art "selection" frames and angle marks drawn by script, scroll-driven GSAP. The art is the content; the code is small | Focal (licensed, variable) and Hal Timezone |
| fal.ai/worlds | The same, plus `worlds-v1.js`: a custom WebGL2 renderer | 2D "wire" drawings are rasterised into a texture by an antialiased line shader, then a fragment shader with about 60 uniforms (shells, cells, quantisation steps, light angle, rim, palette, an image "plate" infused into the surface) turns them into a 3D generative world | Focal |
| anysphere.inc | Next.js; 11 requests in total; no images, no canvas | Restraint. One paragraph, one mark | JJannon (a revival of the 17th-century Jannon serif), roman and italic |
| cursor.com | Next.js (Turbopack), a WebGL context, an MP4 of the logo | Real product UI shown inside commissioned painting; a logo animation rendered to video rather than in code | Custom; KaTeX for maths in docs |
| joinodin.com | Next.js, Sanity CMS, Mux streaming video (HLS), a WebM loading animation | The product shown as real cards over moving art, all streamed video | Three custom faces (primary, secondary, a variable accent) |
| sequoiacap.com | Framer, Lottie via `dotlottie-web` (WebAssembly), MP4s | Animated illustrations as Lottie, a hand-drawn circle, editorial layout | Rosart (roman and italic), Unica77, Pitch Sans, Fragment Mono |
| initialized.com | Next.js, Sentry | Every menu item has its own rollover video (`ideas`, `ripple`, `bubbles`, `people`); handwriting over black and white texture | Akzidenz-Grotesk Pro |
| thebrowser.company | Next.js, a 2D canvas | A drawn emblem, italic serif, small monospace capitals | Ivar Text, ABC Diatype Mono, Permanent Marker for handwriting |
| anthropic.com | Next.js (Turbopack), 2D canvas | Commissioned editorial illustration on every card | Anthropic Sans, Serif and Mono (their own) |
| recent.design | Vite, StyleX | A curation grid of looping MP4 thumbnails | Inter, Departure Mono |
| perplexity.ai | Vite, Rolldown, their own component system | The product is the page | Their own |

## What this means for Antimony

1. **One real renderer, not five sketches.** Pick the signature moment and build it properly in WebGL: a physically based glass crystal (refraction, dispersion, reflections) with a real post-processing chain (bloom, grain, vignette, a touch of chromatic aberration), the way the CRT terminal treats its screen as physics rather than decoration.
2. **Type that is ours.** Every reference pays for or commissions type. Eoin owns Timeless; the wordmark is custom lettering. A licensed serif in the spirit of JJannon or Rosart for long text is the next purchase.
3. **Real media.** fal, Odin, Initialized and Sequoia all lean on video and drawn art. Antimony needs recorded loops of the crystal (rendered from the WebGL scene), real Orbe screen recordings, and eventually commissioned art.
4. **Plain around the moment.** Anysphere loads 11 files. Everything that is not the signature moment should be text on a calm page.
5. **Tools we would use** (all free): Three.js for the 3D, its `EffectComposer` for post-processing, GSAP with ScrollTrigger for scroll choreography (the same version fal ships), Lenis for smooth scrolling, and later Rive or Lottie for small animated marks.
