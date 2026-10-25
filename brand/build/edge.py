"""Writes ../../x/edge/index.html: Antimony after Arasaka, Edgerunners, First of Kind and Anysphere.
Black and bone, one signal red. The Break drawn in our own words, decoding as it arrives. The customised serif wordmark."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from three import break_parts, brk
Q = break_parts()
BLACK, BONE, RED, DIM = "#0A0A0B", "#ECE7DC", "#E0262D", "#6F6B64"
vb, WMB = open("../../x/edge/wm.txt").read().split("\n", 1)
def wordmark(cls="", style=""): return f'<svg class="{cls}" viewBox="{vb}" style="{style}" role="img" aria-label="Antimony">{WMB}</svg>'
WORDS = "ANTIMONY SOFTWARE FOR THE PEOPLE WHO MAKE THE WORK ORBE BRIEF CONTRACT PAID ON TIME NEVER ALONE STIBIUM 51 SB REFINE GOLD THE BREAK MAKERS YOURS "
html = f'''<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Antimony</title><meta name="claude:viewport-fit-sides" content="cover"><link rel="icon" href="../../assets/favicon.svg" type="image/svg+xml">
<style>
/* Arasaka's corporate black, Edgerunners' signal red and decoding type, First of Kind's word mosaic, Anysphere's restraint. */
@font-face {{ font-family: "Timeless Serif"; src: url("../../assets/fonts/TimelessSerifVF.woff2") format("woff2"); font-weight: 200 700; font-display: block; }}
@font-face {{ font-family: "Commit Mono"; src: url("../../assets/fonts/CommitMono-Latin-VF.woff2") format("woff2"); font-weight: 200 700; font-display: block; }}
:root {{ --bg: {BLACK}; --fg: {BONE}; --red: {RED}; --dim: {DIM}; --rule: rgba(236,231,220,.13); --lit: {RED}; color-scheme: dark; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ background: var(--bg); color: var(--fg); }}
body {{ font: 400 13px/1.6 "Commit Mono", ui-monospace, monospace; -webkit-font-smoothing: antialiased; }}
a {{ color: var(--fg); text-decoration: none; border-bottom: 1px solid var(--red); }} a:hover {{ color: var(--red); }}
:focus-visible {{ outline: 1px solid var(--red); outline-offset: 3px; }}
::selection {{ background: var(--red); color: var(--bg); }}
.g {{ padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }}
.bar {{ position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5; display: flex; justify-content: space-between; align-items: center; gap: 16px; padding-block: 14px; background: rgba(10,10,11,.86); backdrop-filter: blur(8px); border-bottom: 1px solid var(--rule); text-transform: uppercase; letter-spacing: .12em; font-size: 11px; }}
body::before {{ content: ""; position: fixed; inset: 0 0 auto; height: env(safe-area-inset-top, 0px); background: var(--bg); z-index: 10; }}
.bar .l {{ display: flex; align-items: center; gap: 12px; }} .bar svg.m {{ width: 18px; height: 18px; display: block; }} .bar .r {{ display: flex; gap: 22px; color: var(--dim); }} .bar .r a {{ border: 0; color: var(--fg); }}
.red {{ color: var(--red); }}
.hero {{ position: relative; height: min(100svh, 980px); min-height: 560px; }}
#mosaic {{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; }}
.hero .t {{ position: absolute; left: max(16px, env(safe-area-inset-left, 0px)); bottom: 48px; max-width: 30em; display: grid; gap: 12px; }}
.hero .t b {{ font: 400 clamp(30px, 4vw, 56px)/1.04 "Timeless Serif", Georgia, serif; letter-spacing: -.015em; }}
.hero .t span {{ color: var(--dim); text-transform: uppercase; letter-spacing: .12em; font-size: 11px; }}
.hero .corner {{ position: absolute; right: max(16px, env(safe-area-inset-right, 0px)); bottom: 48px; text-align: right; color: var(--dim); text-transform: uppercase; letter-spacing: .12em; font-size: 11px; line-height: 1.9; }}
.grid {{ display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); border-top: 1px solid var(--rule); }}
.cell {{ grid-column: span 4; border-right: 1px solid var(--rule); padding: 22px 22px 40px 0; display: grid; gap: 14px; align-content: start; min-width: 0; }}
.cell:last-child {{ border-right: 0; }} .cell + .cell {{ padding-left: 22px; }}
.cell h3 {{ font: 500 11px "Commit Mono", monospace; letter-spacing: .12em; text-transform: uppercase; color: var(--red); }}
.cell p {{ max-width: 36ch; color: #CFC9BC; }}
.line {{ font: 400 clamp(26px, 3.4vw, 46px)/1.15 "Timeless Serif", Georgia, serif; letter-spacing: -.012em; padding-block: 96px; max-width: 22em; text-wrap: balance; }}
.spec {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); }}
.spec div {{ padding: 18px 18px 22px 0; border-right: 1px solid var(--rule); display: grid; gap: 6px; }} .spec div + div {{ padding-left: 18px; }} .spec div:last-child {{ border-right: 0; }}
.spec b {{ font-weight: 400; color: var(--dim); text-transform: uppercase; letter-spacing: .1em; font-size: 11px; }} .spec span {{ font-size: 15px; }}
.orbe {{ display: grid; grid-template-columns: 120px minmax(0, 1fr); gap: 28px; padding-block: 80px; align-items: center; max-width: 900px; }}
.orbe img {{ width: 120px; height: 120px; display: block; filter: invert(1); }}
.orbe p {{ font: 400 clamp(19px, 2vw, 24px)/1.4 "Timeless Serif", Georgia, serif; }}
footer {{ padding-block: 64px 22px; }}
.big {{ display: block; width: 100%; height: auto; color: var(--fg); }}
.fine {{ display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-top: 22px; color: var(--dim); text-transform: uppercase; letter-spacing: .12em; font-size: 11px; border-top: 1px solid var(--rule); padding-top: 14px; }}
@media (max-width: 820px) {{ .cell {{ grid-column: span 12; border-right: 0; border-bottom: 1px solid var(--rule); padding: 20px 0 28px; }} .cell + .cell {{ padding-left: 0; }} .spec {{ grid-template-columns: 1fr 1fr; }} .spec div:nth-child(2) {{ border-right: 0; }} .spec div:nth-child(3) {{ padding-left: 0; }} .bar .r span {{ display: none; }} .hero .corner {{ display: none; }} .orbe {{ grid-template-columns: 72px minmax(0, 1fr); }} .orbe img {{ width: 72px; height: 72px; }} }}
</style></head><body>
<div class="bar g"><div class="l">{brk(stone=BONE, ground=BLACK, lit=RED, facet=False, style="").replace("<svg ", "<svg class=\"m\" ", 1)}<span>Antimony</span><span class="red" style="margin-left:6px">//</span><span style="color:var(--dim)">Software for the people who make the work</span></div>
  <div class="r"><a href="https://eoinforker.github.io/orbe-site/">Orbe</a><span>Letters soon</span><span>London</span></div></div>
<section class="hero"><canvas id="mosaic" aria-label="The Antimony mark, drawn in our own words"></canvas>
  <div class="t g" style="padding:0"><span>001 / The break</span><b>Take away everything that is not the work.</b></div>
  <div class="corner">51 Sb<br>stibium<br>found in the break</div></section>
<main class="g">
  <div class="grid">
    <div class="cell"><h3>01 / The work</h3><p>Creators do the work. Then they do the work around the work: the briefs, the contracts, the invoices, the chasing. We build software that takes the second part away.</p></div>
    <div class="cell"><h3>02 / Orbe</h3><p>Our first product is <a href="https://eoinforker.github.io/orbe-site/">Orbe</a>, the creator's side of every sponsorship deal. It holds the money until the work is delivered.</p></div>
    <div class="cell"><h3>03 / The name</h3><p>Antimony is a metal. It was used to refine gold: melted with it, it took up everything that was not gold. Alchemists called it the wolf of metals.</p></div>
  </div>
  <p class="line">What is left, once the work around the work is gone, is <span class="red">yours</span>.</p>
  <div class="spec"><div><b>Element</b><span>51, Sb</span></div><div><b>Found as</b><span>Stibnite, in the cracks of rock</span></div><div><b>Used for</b><span>Refining gold</span></div><div><b>Rarely</b><span>Found alone</span></div></div>
  <div class="orbe"><img src="../../assets/orbe-mark.png" alt="The Orbe mark"><p>Orbe is the creator's side of every sponsorship deal: the brief, the contract and the payment in one place. <a href="https://eoinforker.github.io/orbe-site/">Visit Orbe</a></p></div>
</main>
<footer class="g">{wordmark("big")}<div class="fine"><span>© 2026 Antimony</span><span>Made in London</span></div></footer>
<script>
(() => {{ "use strict";
const Q = {json.dumps({k: Q[k] for k in ("seam", "cav", "gem")})}, BONE = "{BONE}", RED = "{RED}", DIM = "#2A2826", DIM2 = "#3A3733";
const WORDS = "{WORDS}", GLYPH = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/\\\\<>[]{{}}=+*#%&$";
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
const c = document.getElementById("mosaic"), x = c.getContext("2d");
let W, H, cw, ch, cols, rows, grid = [], T0 = performance.now(), mx = -1e9, my = -1e9;
function regions(n, m) {{
  const S = 600, o = document.createElement("canvas"); o.width = o.height = S; const g = o.getContext("2d"), k = S / 100; g.scale(k, k);
  const rr = new Path2D(); rr.roundRect ? rr.roundRect(0, 0, 100, 100, 22) : rr.rect(0, 0, 100, 100);
  g.fillStyle = "#fff"; g.fill(rr); g.globalCompositeOperation = "destination-out"; g.fill(new Path2D(Q.seam)); g.fill(new Path2D(Q.cav));
  g.globalCompositeOperation = "source-over"; g.fillStyle = "#f00"; g.fill(new Path2D(Q.gem));
  return (u, v) => {{ if (u < 0 || v < 0 || u >= 1 || v >= 1) return 0; const q = (Math.floor(v * S) * S + Math.floor(u * S)) * 4, d = g.getImageData(0, 0, 1, 1); return 0; }};
}}
function layout() {{
  const d = Math.min(2, devicePixelRatio || 1), r = c.getBoundingClientRect(); W = r.width; H = r.height; c.width = W * d; c.height = H * d; x.setTransform(d, 0, 0, d, 0, 0);
  const fs = W < 600 ? 10 : 12.5; cw = fs * .62; ch = fs * 1.08; cols = Math.ceil(W / cw); rows = Math.ceil(H / ch);
  x.font = `500 ${{fs}}px "Commit Mono", monospace`; x.textBaseline = "top";
  // where the mark sits: a square on the right two thirds, centred vertically
  const s = Math.min(H * .78, W * (W < 700 ? .9 : .5)), ox = W < 700 ? (W - s) / 2 : W * .66 - s / 2, oy = (H - s) / 2 - (W < 700 ? 40 : 0);
  const S = 400, o = document.createElement("canvas"); o.width = o.height = S; const g = o.getContext("2d"), k = S / 100; g.scale(k, k);
  const rr = new Path2D(); rr.roundRect ? rr.roundRect(0, 0, 100, 100, 22) : rr.rect(0, 0, 100, 100);
  g.fillStyle = "#fff"; g.fill(rr); g.globalCompositeOperation = "destination-out"; g.fill(new Path2D(Q.seam)); g.fill(new Path2D(Q.cav));
  g.globalCompositeOperation = "source-over"; g.fillStyle = "#f00"; g.fill(new Path2D(Q.gem));
  const D = g.getImageData(0, 0, S, S).data;
  grid = [];
  let wi = Math.floor(Math.random() * WORDS.length);
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {{
    const px = i * cw + cw / 2, py = j * ch + ch / 2, u = (px - ox) / s, v = (py - oy) / s;
    let kind = 0;
    if (u >= 0 && v >= 0 && u < 1 && v < 1) {{ const q = (Math.floor(v * S) * S + Math.floor(u * S)) * 4; if (D[q + 3] > 128) kind = D[q + 1] > 200 ? 1 : 2; }}
    const chr = WORDS[wi % WORDS.length]; wi++;
    grid.push({{ i, j, chr, kind, d: Math.random() * 1.4 + (kind ? .2 : 1.2) + Math.hypot(u - .5, v - .5) * .6, n: Math.random() * 99 }});
  }}
}}
function frame(now) {{
  const t = still ? 99 : (now - T0) / 1000; x.fillStyle = "{BLACK}"; x.fillRect(0, 0, W, H);
  for (const p of grid) {{
    const a = t - p.d; if (a < 0) continue;
    const px = p.i * cw, py = p.j * ch, near = Math.hypot(px - mx, py - my) < 70;
    let chr = p.chr;
    const decoding = a < .55 || (near && Math.sin(t * 20 + p.n) > .2) || (!still && t > 4 && Math.sin(t * 1.3 + p.n * 4.1) > .9993);
    if (decoding) chr = GLYPH[(Math.floor(t * 30 + p.n * 7)) % GLYPH.length];
    if (chr === " ") continue;
    x.fillStyle = p.kind === 1 ? (decoding ? RED : BONE) : p.kind === 2 ? (decoding ? BONE : RED) : (near ? DIM2 : DIM);
    x.fillText(chr, px, py);
  }}
  requestAnimationFrame(frame);
}}
c.addEventListener("pointermove", e => {{ const r = c.getBoundingClientRect(); mx = e.clientX - r.left; my = e.clientY - r.top; }});
c.addEventListener("pointerleave", () => mx = my = -1e9);
new ResizeObserver(layout).observe(c);
(document.fonts ? document.fonts.load('500 12px "Commit Mono"') : Promise.resolve()).catch(() => {{}}).finally(() => {{ layout(); T0 = performance.now(); requestAnimationFrame(frame); }});
}})();
</script></body></html>'''
open("../../x/edge/index.html", "w").write(html); print(len(html))
