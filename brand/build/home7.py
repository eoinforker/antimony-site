"""Writes /home/user/antimony-site/index.html. The screen is the stone. A crack runs through it at sixteen degrees and opens
into the crystal's cavity, the way it does in the mark; through the crystal there is a print. The type is a colophon."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from three import B
HERE = os.path.dirname(os.path.abspath(__file__))
vb, WMB = open(os.path.join(HERE, "../../x/edge/wm.txt")).read().split("\n", 1)
INK, PAPER, SKY = "#0B0C0C", "#EEEAE0", "#94E6FF"
GEOM = {k: B[k] for k in ("ang", "gw", "gh", "pd", "mar")}

html = f'''<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#121211"><meta name="description" content="Antimony builds software for the people who make the work. Our first product is Orbe.">
<meta property="og:title" content="Antimony"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<title>Antimony</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
@font-face {{ font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifVF.woff2") format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifItalicVF.woff2") format("woff2"); font-weight: 200 700; font-style: italic; font-display: swap; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ height: 100%; background: #121211; overflow: hidden; }}
body {{ color: {PAPER}; font: 400 15px/1.6 "Timeless Serif", Georgia, serif; -webkit-font-smoothing: antialiased; }}
a {{ color: inherit; text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: .22em; text-decoration-color: rgba(238,234,224,.3); transition: text-decoration-color .3s ease; }}
a:hover {{ text-decoration-color: currentColor; }}
:focus-visible {{ outline: 1px solid {SKY}; outline-offset: 4px; }}
::selection {{ background: {SKY}; color: {INK}; }}
#wall {{ position: fixed; inset: 0; width: 100%; height: 100%; display: block; }}
.wm {{ position: fixed; left: max(40px, env(safe-area-inset-left, 0px)); top: max(36px, env(safe-area-inset-top, 0px)); height: 18px; width: auto; color: {PAPER}; --lit: {SKY}; opacity: .92; }}
.col {{ position: fixed; left: max(40px, env(safe-area-inset-left, 0px)); bottom: max(36px, env(safe-area-inset-bottom, 0px)); max-width: 27em; color: rgba(238,234,224,.62); text-wrap: pretty; }}
.col em {{ color: {PAPER}; }}
.cr {{ position: fixed; right: max(40px, env(safe-area-inset-right, 0px)); bottom: max(36px, env(safe-area-inset-bottom, 0px)); font-size: 12.5px; color: rgba(238,234,224,.34); text-align: right; max-width: 22em; }}
.col, .cr, .wm {{ opacity: 0; transition: opacity 1.6s ease; }} .on .col, .on .cr {{ opacity: 1; }} .on .wm {{ opacity: .92; }}
@media (max-width: 700px) {{ .wm {{ left: 24px; top: max(28px, env(safe-area-inset-top, 0px)); }} .col {{ left: 24px; right: 24px; bottom: max(28px, env(safe-area-inset-bottom, 0px)); font-size: 15.5px; }} .cr {{ display: none; }} }}
</style></head>
<body>
<svg id="wall" aria-label="A wall of dark stone with a crack through it at sixteen degrees, opening into a crystal; through the crystal, a print of the moon"></svg>
<svg class="wm" viewBox="{vb}" role="img" aria-label="Antimony">{WMB}</svg>
<p class="col"><em>Antimony</em> builds software for the people who make the work. Our first product is <a href="https://eoinforker.github.io/orbe-site/">Orbe</a>, the creator&#39;s side of every sponsorship deal. We sit on their side of the table, and we mean to stay there for a long time.</p>
<p class="cr">Through the crystal: Utagawa Hiroshige, <i>Autumn Moon over Ishiyama Temple</i>, 1857. Art Institute of Chicago.</p>
<script>
(() => {{ "use strict";
const G = {json.dumps(GEOM)}, NS = "http://www.w3.org/2000/svg", svg = document.getElementById("wall");
const still = matchMedia("(prefers-reduced-motion: reduce)").matches, fine = matchMedia("(pointer: fine)").matches;
const k = Math.tan(G.ang * Math.PI / 180), d = [Math.sin(G.ang * Math.PI / 180), -Math.cos(G.ang * Math.PI / 180)];
const el = (n, a, p = svg) => {{ const e = document.createElementNS(NS, n); for (const q in a) e.setAttribute(q, a[q]); p.appendChild(e); return e; }};
const P = pts => "M" + pts.map(p => p[0].toFixed(1) + " " + p[1].toFixed(1)).join("L") + "Z";
// the crystal and its cavity, as in the mark: a hexagon sheared to the seam's angle
const hex = (cx, cy, w, h, pd) => [[cx, cy - h / 2], [cx + w / 2, cy - h / 2 + pd], [cx + w / 2, cy + h / 2 - pd], [cx, cy + h / 2], [cx - w / 2, cy + h / 2 - pd], [cx - w / 2, cy - h / 2 + pd]];
const shear = (pts, cy) => pts.map(([x, y]) => [x + (cy - y) * k, y]);
let W, H, t0 = performance.now(), crack, light, print, img, rim, ox = 0, oy = 0, tx = 0, ty = 0, done = still;
function build() {{
  W = innerWidth; H = innerHeight; svg.setAttribute("viewBox", `0 0 ${{W}} ${{H}}`); svg.innerHTML = "";
  const narrow = W < 700, gh = narrow ? Math.min(H * .34, W * .62) : Math.min(H * .38, W * .3), s = gh / G.gh;
  const cx = narrow ? W * .56 : W * .62, cy = narrow ? H * .36 : H * .47;
  const gem = shear(hex(cx, cy, G.gw * s, G.gh * s, G.pd * s), cy), cav = shear(hex(cx, cy, (G.gw + G.mar * 2) * s, (G.gh + G.mar * 2.3) * s, (G.pd + G.mar * .55) * s), cy);
  const defs = el("defs", {{}});
  // stone: a slow fall of light from the upper left, and a fine grain
  const lg = el("radialGradient", {{ id: "fall", cx: "18%", cy: "8%", r: "115%" }}, defs);
  el("stop", {{ offset: "0", "stop-color": "#1D1C1A" }}, lg); el("stop", {{ offset: ".55", "stop-color": "#131312" }}, lg); el("stop", {{ offset: "1", "stop-color": "#0C0C0B" }}, lg);
  const f = el("filter", {{ id: "grain", x: "0", y: "0", width: "100%", height: "100%" }}, defs);
  el("feTurbulence", {{ type: "fractalNoise", baseFrequency: ".85", numOctaves: "3", seed: "9" }}, f);
  el("feColorMatrix", {{ values: "0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .06 0" }}, f);
  const gc = el("clipPath", {{ id: "gem" }}, defs); el("path", {{ d: P(gem) }}, gc);
  el("rect", {{ width: W, height: H, fill: "url(#fall)" }}); el("rect", {{ width: W, height: H, filter: "url(#grain)" }});
  // the crack: hairline at the edges of the screen, widening to the cavity, like the seam in the mark
  const L = Math.hypot(W, H), top = gem[0], bot = gem[3], w0 = s * 2.4, w1 = .55;
  crack = {{ top, bot, w0, w1, L }};
  light = el("path", {{ fill: "#070808" }});
  el("path", {{ d: P(cav), fill: "#070808" }});
  // where the light from the upper left catches the far edge of each cut
  rim = el("path", {{ fill: "none", stroke: "rgba(238,234,224,.10)", "stroke-width": "1", d: "M" + [cav[1], cav[2], cav[3]].map(p => p.join(" ")).join("L") }});
  const g = el("g", {{ "clip-path": "url(#gem)" }});
  print = el("g", {{}}, g);
  const bw = (Math.max(...gem.map(p => p[0])) - Math.min(...gem.map(p => p[0]))) * 1.35, bh = gh * 1.25;
  img = el("image", {{ href: "assets/prints/18972.webp", x: cx - bw / 2, y: cy - bh * .55, width: bw, height: bh, preserveAspectRatio: "xMidYMin slice", opacity: still ? 1 : 0 }}, print);
  el("path", {{ d: P([gem[0], gem[1], gem[2], gem[3]]), fill: "#fff", "fill-opacity": ".06" }}, g);
  el("path", {{ d: P(gem), fill: "none", stroke: "rgba(255,255,255,.14)", "stroke-width": ".8" }}, g);
  draw(done ? 1 : 0);
}}
// the crack grows out of the crystal, up and down, the first time the page opens
function draw(e) {{
  const {{ top, bot, w0, w1, L }} = crack, n = [Math.cos(16 * Math.PI / 180), Math.sin(16 * Math.PI / 180)];
  // half widths along the crack, from the cavity outwards: it narrows fast, then runs on as a hairline
  const prof = [[0, w0], [.05, w0 * .62], [.16, w0 * .3], [.34, w0 * .14], [1, w1]], reach = e * L * .75;
  const side = (p, dir, sgn) => prof.filter(([f]) => f * L * .75 <= reach + 1e-6).concat(reach < L * .75 ? [[reach / (L * .75), null]] : [])
    .map(([f, w], i, A) => {{ if (w === null) {{ const [f0, w0_] = A[i - 1], nx = prof.find(q => q[0] > f0), t = nx ? (f - f0) / (nx[0] - f0) : 0; w = w0_ + ((nx ? nx[1] : w1) - w0_) * t; }}
      const q = [p[0] + dir[0] * f * L * .75, p[1] + dir[1] * f * L * .75]; return [q[0] + sgn * n[0] * w, q[1] + sgn * n[1] * w]; }});
  const up = [d[0], d[1]], dn = [-d[0], -d[1]];
  const tl = side(top, up, -1), tr = side(top, up, 1), bl = side(bot, dn, -1), br = side(bot, dn, 1);
  light.setAttribute("d", P([...tl.slice().reverse(), ...bl, ...br.slice().reverse(), ...tr]));
}}
const ease = t => 1 - Math.pow(1 - t, 3);
function tick(now) {{
  const t = (now - t0) / 1000;
  if (!done) {{ const e = ease(Math.min(1, Math.max(0, (t - .3) / 1.8))); draw(e); img.setAttribute("opacity", ease(Math.min(1, Math.max(0, (t - 1.4) / 1.6)))); if (t > 3.2) done = true; }}
  ox += (tx - ox) * .05; oy += (ty - oy) * .05; print.setAttribute("transform", `translate(${{ox.toFixed(2)}} ${{oy.toFixed(2)}})`);
  requestAnimationFrame(tick);
}}
if (fine && !still) addEventListener("pointermove", e => {{ tx = -(e.clientX / innerWidth - .5) * 10; ty = -(e.clientY / innerHeight - .5) * 8; }});
addEventListener("resize", build);
build(); requestAnimationFrame(tick);
setTimeout(() => document.body.classList.add("on"), still ? 0 : 1500);
}})();
</script>
</body></html>'''
open(os.path.join(HERE, "../../index.html"), "w").write(html); print(len(html))
