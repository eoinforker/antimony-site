"""Writes ../../x/quiet/index.html: Antimony, quaint and brief. The mark drawn faintly in our words; a lantern where you look."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from three import break_parts, brk
Q = break_parts()
PAPER, INK, SKY, PRU, DIM = "#F4F2EC", "#1A1917", "#8FDFFA", "#1F3F7A", "#8A877F"
vb, WMB = open("../../x/edge/wm.txt").read().split("\n", 1)
def wordmark(style=""): return f'<svg viewBox="{vb}" style="{style}" role="img" aria-label="Antimony">{WMB}</svg>'
WORDS = "antimony software for the people who make the work orbe the brief the contract paid on time never alone stibium fifty one refine the gold the break makers yours what is left "
html = f'''<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Antimony</title><meta name="claude:viewport-fit-sides" content="cover"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<meta name="description" content="Antimony builds software for the people who make the work. Our first product is Orbe.">
<style>
/* Quaint and brief, after Anysphere: one narrow column of serif on paper, and one quiet, curious thing to look at. */
@font-face {{ font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifVF.woff2") format("woff2"); font-weight: 200 700; font-display: block; }}
@font-face {{ font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifItalicVF.woff2") format("woff2"); font-weight: 200 700; font-style: italic; font-display: swap; }}
@font-face {{ font-family: "Commit Mono"; src: url("assets/fonts/CommitMono-Latin-VF.woff2") format("woff2"); font-weight: 200 700; font-display: block; }}
:root {{ --paper: {PAPER}; --ink: {INK}; --dim: {DIM}; --lit: {SKY}; --pru: {PRU}; color-scheme: light; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ background: var(--paper); color: var(--ink); }}
body {{ font: 400 18px/1.55 "Timeless Serif", Georgia, serif; -webkit-font-smoothing: antialiased; padding-left: max(20px, env(safe-area-inset-left, 0px)); padding-right: max(20px, env(safe-area-inset-right, 0px)); }}
a {{ color: inherit; text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: .18em; text-decoration-color: rgba(26,25,23,.35); }} a:hover {{ text-decoration-color: var(--ink); }}
:focus-visible {{ outline: 1px solid var(--pru); outline-offset: 3px; }}
::selection {{ background: var(--lit); }}
.col {{ max-width: 34rem; margin-inline: auto; padding-block: calc(56px + env(safe-area-inset-top, 0px)) 56px; display: grid; gap: 1.3em; }}
.wm {{ width: 132px; height: auto; display: block; color: var(--ink); margin-bottom: 2.2em; }}
.win {{ position: relative; aspect-ratio: 1; width: 100%; max-width: 100%; margin: .6em 0 1em; cursor: crosshair; touch-action: pan-y; }}
.win canvas {{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; }}
.hint {{ font: 400 11.5px "Commit Mono", monospace; color: var(--dim); letter-spacing: .02em; margin-top: -1.4em; }}
p {{ text-wrap: pretty; }}
.links {{ display: flex; gap: 1.4em; flex-wrap: wrap; font-size: 16px; margin-top: .6em; }} .links span {{ color: var(--dim); }}
footer {{ font: 400 11.5px "Commit Mono", monospace; color: var(--dim); margin-top: 3.2em; display: flex; justify-content: space-between; gap: 12px; }}
@media (max-width: 520px) {{ body {{ font-size: 17px; }} }}
</style></head><body>
<main class="col">
  {wordmark().replace("<svg ", "<svg class=\"wm\" ", 1)}
  <p>Antimony builds software for the people who make the work.</p>
  <div class="win" id="win"><canvas id="c" aria-label="The Antimony mark, drawn faintly in our own words. Move over it to look closer."></canvas></div>
  <p class="hint">Look closer.</p>
  <p>Creators do the work, and then the work around the work: the briefs, the contracts, the chasing. We take the second part away, so what is left is theirs.</p>
  <p>Our first product is <a href="https://eoinforker.github.io/orbe-site/">Orbe</a>, the creator's side of every sponsorship deal. There will be others.</p>
  <p>The name is a metal that was used to refine gold. It is almost never found alone. We intend to be around for a long time.</p>
  <div class="links"><a href="https://eoinforker.github.io/orbe-site/">Orbe</a><span>Letters, soon</span></div>
  <footer><span>Antimony, London</span><span>© 2026</span></footer>
</main>
<script>
(() => {{ "use strict";
const Q = {json.dumps({k: Q[k] for k in ("seam", "cav", "gem")})}, WORDS = "{WORDS}";
const INK = [26, 25, 23], PAPER = [244, 242, 236], SKYC = [143, 223, 250], still = matchMedia("(prefers-reduced-motion: reduce)").matches;
const box = document.getElementById("win"), c = document.getElementById("c"), x = c.getContext("2d");
let W, cw, ch, cells = [], lx = .5, ly = .5, tx = .5, ty = .5, touched = false, T0 = performance.now();
function layout() {{
  const d = Math.min(2, devicePixelRatio || 1); W = box.getBoundingClientRect().width; c.width = W * d; c.height = W * d; x.setTransform(d, 0, 0, d, 0, 0);
  const fs = Math.max(7, W / 70); cw = fs * .6; ch = fs * 1.05; x.font = `400 ${{fs}}px "Commit Mono", monospace`; x.textBaseline = "top";
  const S = 400, o = document.createElement("canvas"); o.width = o.height = S; const g = o.getContext("2d"), k = S / 100; g.scale(k, k);
  const rr = new Path2D(); rr.roundRect ? rr.roundRect(0, 0, 100, 100, 22) : rr.rect(0, 0, 100, 100);
  g.fillStyle = "#fff"; g.fill(rr); g.globalCompositeOperation = "destination-out"; g.fill(new Path2D(Q.seam)); g.fill(new Path2D(Q.cav));
  g.globalCompositeOperation = "source-over"; g.fillStyle = "#f00"; g.fill(new Path2D(Q.gem));
  const D = g.getImageData(0, 0, S, S).data, cols = Math.floor(W / cw), rows = Math.floor(W / ch); cells = []; let wi = 0;
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {{
    const u = (i + .5) / cols, v = (j + .5) / rows, q = (Math.floor(v * S) * S + Math.floor(u * S)) * 4;
    const kind = D[q + 3] > 128 ? (D[q + 1] > 200 ? 1 : 2) : 0, chr = WORDS[wi++ % WORDS.length];
    if (chr !== " ") cells.push({{ x: i * cw, y: j * ch, u, v, kind, chr }});
  }}
}}
const CRY = PAPER.map((v, i) => Math.round(v + (INK[i] - v) * .2));
const mix = (a, b, t) => `rgb(${{a.map((v, i) => Math.round(v + (b[i] - v) * t)).join(",")}})`;
function frame(now) {{
  const t = (now - T0) / 1000;
  if (!touched && !still) {{ tx = .5 + Math.sin(t * .23) * .28; ty = .5 + Math.sin(t * .17 + 1) * .26; }}   // left alone, the light wanders slowly
  lx += (tx - lx) * .08; ly += (ty - ly) * .08;
  x.clearRect(0, 0, W, W);
  for (const p of cells) {{
    const dl = Math.hypot(p.u - lx, p.v - ly), light = Math.max(0, 1 - dl / .26) ** 1.6;   // the lantern
    let col;
    if (p.kind === 0) col = mix(PAPER, INK, .045 + light * .1);
    else if (p.kind === 1) col = mix(PAPER, INK, .5 + light * .48);
    else col = mix(CRY, [64, 170, 220], .55 + light * .45);
    x.fillStyle = col; x.fillText(p.chr, p.x, p.y);
  }}
  requestAnimationFrame(frame);
}}
box.addEventListener("pointermove", e => {{ const r = box.getBoundingClientRect(); tx = (e.clientX - r.left) / r.width; ty = (e.clientY - r.top) / r.height; touched = true; }});
box.addEventListener("pointerleave", () => {{ touched = false; }});
new ResizeObserver(layout).observe(box);
(document.fonts ? document.fonts.load('400 12px "Commit Mono"') : Promise.resolve()).catch(() => {{}}).finally(() => {{ layout(); requestAnimationFrame(frame); }});
}})();
</script></body></html>'''
open("../../x/quiet/index.html", "w").write(html); print(len(html))
