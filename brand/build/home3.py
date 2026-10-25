"""Writes /home/user/antimony-site/index.html. A terminal boots; the Break is drawn in live characters; scrolling carries it
down into the mark at the foot while black turns to paper; two paragraphs are typed. The pointer scrambles and lights the characters."""
import json, os, sys, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from three import break_parts, CONT
Q = break_parts()
INK, PAPER, SKY, PRU = "#0B0C0C", "#EEEAE0", "#94E6FF", "#1F3F7A"
GEMMASK = "data:image/svg+xml," + urllib.parse.quote(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="{Q["gem"]}"/></svg>')
stone = (f'<svg id="stone" viewBox="0 0 100 100" aria-hidden="true"><defs><clipPath id="sc">{CONT["tile"]}</clipPath><mask id="sm"><rect width="100" height="100" fill="#fff"/>'
         f'<path d="{Q["seam"]}" fill="#000"/><path d="{Q["cav"]}" fill="#000"/></mask></defs><g clip-path="url(#sc)"><rect width="100" height="100" fill="#141311" mask="url(#sm)"/></g></svg>')
WORDS = "ANTIMONY SOFTWARE FOR THE PEOPLE WHO MAKE THE WORK ORBE THE BRIEF THE CONTRACT PAID ON TIME NEVER ALONE STIBIUM 51 SB REFINE THE GOLD WHAT IS LEFT IS YOURS "
BOOT = ["ANTIMONY", "51 SB  STIBIUM", "SPLITTING STONE", "GROWING CRYSTAL", "READY"]
html = f'''<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="{INK}"><meta name="description" content="Antimony builds software for the people who make the work. Our first product is Orbe.">
<meta property="og:title" content="Antimony"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<title>Antimony</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* A terminal on black that becomes a page on paper. The scroll is the transition. */
@font-face {{ font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifVF.woff2") format("woff2"); font-weight: 200 700; font-display: block; }}
@font-face {{ font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifItalicVF.woff2") format("woff2"); font-weight: 200 700; font-style: italic; font-display: block; }}
@font-face {{ font-family: "Commit Mono"; src: url("assets/fonts/CommitMono-Latin-VF.woff2") format("woff2"); font-weight: 200 700; font-display: block; }}
:root {{ --paper: {PAPER}; --ink: {INK}; --sky: {SKY}; --pru: {PRU}; color-scheme: dark; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ background: var(--ink); }}
body {{ background: var(--ink); color: #26292A; font: 400 19px/1.55 "Timeless Serif", Georgia, serif; -webkit-font-smoothing: antialiased; height: 260vh; }}
a {{ color: inherit; text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: .18em; text-decoration-color: rgba(38,41,42,.35); }} a:hover {{ text-decoration-color: currentColor; }}
:focus-visible {{ outline: 1px solid var(--pru); outline-offset: 3px; }}
::selection {{ background: var(--sky); color: var(--ink); }}
#c {{ position: fixed; inset: 0; width: 100%; height: 100%; display: block; }}
.boot {{ position: fixed; left: max(20px, env(safe-area-inset-left, 0px)); top: calc(20px + env(safe-area-inset-top, 0px)); font: 400 11.5px/1.7 "Commit Mono", monospace; color: #8C918E; letter-spacing: .08em; white-space: pre; pointer-events: none; transition: opacity .6s ease; }}
.boot b {{ font-weight: 400; color: var(--sky); }}
.hint {{ position: fixed; left: 50%; bottom: calc(26px + env(safe-area-inset-bottom, 0px)); transform: translateX(-50%); font: 400 11px "Commit Mono", monospace; letter-spacing: .14em; color: #8C918E; text-transform: uppercase; transition: opacity .5s ease; pointer-events: none; }}
main {{ position: fixed; left: 0; right: 0; top: 0; max-width: 640px; margin: 0 auto; padding: 16vh max(24px, env(safe-area-inset-right, 0px)) 0 max(24px, env(safe-area-inset-left, 0px)); opacity: 0; pointer-events: none; }}
main.on {{ pointer-events: auto; }}
.prompt {{ font: 400 12px "Commit Mono", monospace; color: #6C6A64; letter-spacing: .02em; margin-bottom: 1.6em; }}
main p {{ text-wrap: pretty; min-height: 1.55em; }} main p + p {{ margin-top: 1.4em; }} main em {{ font-style: italic; }}
.cur {{ display: inline-block; width: .5em; height: 1.05em; background: var(--sky); vertical-align: -.16em; margin-left: .06em; animation: blink 1.06s steps(1) infinite; }}
@keyframes blink {{ 50% {{ opacity: 0; }} }}
.foot {{ position: fixed; left: 50%; bottom: calc(36px + env(safe-area-inset-bottom, 0px)); width: 92px; height: 92px; transform: translateX(-50%); opacity: 0; }}
.foot.on {{ pointer-events: auto; }}
#top {{ all: unset; display: block; width: 100%; height: 100%; cursor: pointer; border-radius: 22%; }}
#top:focus-visible {{ outline: 1px solid var(--pru); outline-offset: 4px; }}
.win, .win > * {{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; }}
.win .img, .win .pencil {{ -webkit-mask: url("{GEMMASK}") center / 100% 100% no-repeat; mask: url("{GEMMASK}") center / 100% 100% no-repeat; }}
.win .img {{ background: url(assets/prints/19006.webp) 48% 40% / 260% auto no-repeat; animation: drift 24s ease-in-out infinite alternate; }}
@keyframes drift {{ to {{ background-position: 56% 52%; }} }}
.win .pencil {{ image-rendering: pixelated; pointer-events: none; }}
@media (max-width: 600px) {{ body {{ font-size: 17.5px; }} main {{ padding-top: 12vh; }} .foot {{ width: 76px; height: 76px; }} }}
@media (prefers-reduced-motion: reduce) {{ .win .img {{ animation: none; }} .cur {{ animation: none; }} }}
</style></head>
<body>
<canvas id="c" aria-label="The Antimony mark, a stone split open with a crystal grown in the break, drawn in characters"></canvas>
<div class="boot" id="boot" aria-hidden="true"></div>
<div class="hint" id="hint" aria-hidden="true">Scroll</div>
<main id="m">
  <div class="prompt" aria-hidden="true">antimony, london</div>
  <p id="p1" data-html="<em>Antimony</em> builds software for the people who make the work. Our first product is <a href=&quot;https://eoinforker.github.io/orbe-site/&quot;>Orbe</a>, the creator&#39;s side of every sponsorship deal."></p>
  <p id="p2" data-html="We sit on their side of the table, and we mean to stay there for a long time."></p>
  <noscript><p><em>Antimony</em> builds software for the people who make the work. Our first product is <a href="https://eoinforker.github.io/orbe-site/">Orbe</a>, the creator's side of every sponsorship deal.</p><p>We sit on their side of the table, and we mean to stay there for a long time.</p></noscript>
</main>
<div class="foot" id="foot"><button id="top" aria-label="Antimony. Back to the top"><span class="win"><span class="img"></span><canvas class="pencil" width="220" height="220"></canvas>{stone}</span></button></div>
<script>
(() => {{ "use strict";
const Q = {json.dumps({k: Q[k] for k in ("seam", "cav", "gem", "facet")})}, WORDS = "{WORDS}", BOOT = {json.dumps(BOOT)};
const GLYPH = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/<>[]{{}}=+*#%&$:";
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
const c = document.getElementById("c"), x = c.getContext("2d"), main = document.getElementById("m"), foot = document.getElementById("foot");
const boot = document.getElementById("boot"), hint = document.getElementById("hint");
const INKC = [11, 12, 12], PAPERC = [238, 234, 224], BONE = [236, 231, 220], SKYC = [148, 230, 255], DEEP = [20, 19, 17], GRID = [40, 44, 43];
const lerp = (a, b, t) => a + (b - a) * t, cl = v => Math.max(0, Math.min(1, v)), ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const mixc = (a, b, t) => [0, 1, 2].map(i => Math.round(lerp(a[i], b[i], t)));
const css = a => `rgb(${{a[0]}},${{a[1]}},${{a[2]}})`;
let W, H, fs, cw, ch, cells = [], bg = [], big, home, T0 = performance.now(), mx = -1e9, my = -1e9, P = 0;
function sampler() {{
  const S = 400, o = document.createElement("canvas"); o.width = o.height = S; const g = o.getContext("2d"), k = S / 100; g.scale(k, k);
  const rr = new Path2D(); rr.roundRect ? rr.roundRect(0, 0, 100, 100, 22) : rr.rect(0, 0, 100, 100);
  g.fillStyle = "#fff"; g.fill(rr); g.globalCompositeOperation = "destination-out"; g.fill(new Path2D(Q.seam)); g.fill(new Path2D(Q.cav));
  g.globalCompositeOperation = "source-over"; g.fillStyle = "#f00"; g.fill(new Path2D(Q.gem)); g.fillStyle = "#00f"; g.fill(new Path2D(Q.facet));
  const D = g.getImageData(0, 0, S, S).data;
  return (u, v) => {{ if (u < 0 || v < 0 || u >= 1 || v >= 1) return 0; const q = (Math.floor(v * S) * S + Math.floor(u * S)) * 4; if (D[q + 3] < 128) return 0; return D[q] > 200 && D[q + 1] > 200 ? 1 : D[q] > 200 ? 2 : 3; }};
}}
const kindAt = sampler();
function layout() {{
  const d = Math.min(2, devicePixelRatio || 1); W = innerWidth; H = innerHeight; c.width = W * d; c.height = H * d; x.setTransform(d, 0, 0, d, 0, 0);
  fs = W < 600 ? 9 : 11.5; cw = fs * .6; ch = fs * 1.12; x.font = `500 ${{fs}}px "Commit Mono", monospace`; x.textBaseline = "middle"; x.textAlign = "center";
  const s = Math.min(H * .72, W * .82); big = {{ s, ox: W / 2 - s / 2, oy: H * .47 - s / 2 }};
  const r = foot.getBoundingClientRect(); home = {{ s: r.width, ox: r.left, oy: r.top }};
  cells = []; bg = []; let wi = 0;
  const cols = Math.floor(s / cw), rows = Math.floor(s / ch);
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {{
    const u = (i + .5) / cols, v = (j + .5) / rows, k = kindAt(u, v), chr = WORDS[wi++ % WORDS.length];
    if (k && chr !== " ") cells.push({{ u, v, k, chr, d: .2 + Math.random() * .9 + Math.hypot(u - .5, v - .5) * .9, n: Math.random() * 99, w: Math.random() }});
  }}
  for (let y = ch / 2; y < H; y += ch * 2) for (let X = cw / 2; X < W; X += cw * 6) bg.push({{ x: X, y, n: Math.random() * 99 }});
}}
function frame(now) {{
  const t = still ? 99 : (now - T0) / 1000, built = t - 1.7;
  P = cl(scrollY / (innerHeight * 1.45)); const e = ease(P);
  const ground = mixc(INKC, PAPERC, cl((P - .35) / .45));
  x.fillStyle = css(ground); x.fillRect(0, 0, W, H);
  // the terminal grid, faint, fading as the paper arrives
  const ga = (1 - cl(P / .5)) * cl(t / .6);
  if (ga > 0) {{ x.fillStyle = `rgba(140,150,148,${{.16 * ga}})`; for (const b of bg) x.fillText((Math.sin(t * .7 + b.n) > .6) ? GLYPH[(b.n * 13 | 0) % GLYPH.length] : "·", b.x, b.y); }}
  const s = lerp(big.s, home.s, e), ox = lerp(big.ox, home.ox, e), oy = lerp(big.oy, home.oy, e) - Math.sin(e * Math.PI) * 30;
  const small = cl((P - .82) / .16);                       // the characters hand over to the finished mark
  for (const p of cells) {{
    const a = built - p.d; if (a < 0) continue;
    const X = ox + p.u * s + (1 - e) * 0, Y = oy + p.v * s;
    const near = Math.hypot(X - mx, Y - my) < 90;
    const decoding = a < .5 || (near && P < .3 && Math.sin(t * 22 + p.n) > .1) || (t > 5 && Math.sin(t * 1.1 + p.n * 4.1) > .9994);
    const chr = decoding ? GLYPH[(Math.floor(t * 30 + p.n * 7)) % GLYPH.length] : p.chr;
    let col;
    const paperT = cl((P - .35) / .45);
    if (p.k === 1) col = mixc(BONE, DEEP, paperT);
    else col = p.k === 3 ? mixc([190, 242, 255], [181, 238, 255], paperT) : SKYC;
    if (near && P < .3) col = p.k === 1 ? SKYC : [255, 255, 255];
    if (a < .5) col = SKYC;
    x.globalAlpha = 1 - small;
    x.font = `500 ${{fs * lerp(1, Math.max(.35, home.s / big.s * 1.6), e)}}px "Commit Mono", monospace`;
    x.fillStyle = css(col); x.fillText(chr, X, Y);
  }}
  x.globalAlpha = 1;
  foot.style.opacity = small; foot.classList.toggle("on", small > .5);
  const tx = cl((P - .86) / .1); main.style.opacity = tx; main.style.transform = `translateY(${{(1 - tx) * 14}}px)`; main.classList.toggle("on", tx > .5);
  if (tx > .4 && !typed) {{ typed = true; type(); colourIn(700); }}
  if (P < .2 && typed) {{ typed = false; }}
  hint.style.opacity = P < .05 && built > 1.4 ? 1 : 0;
  boot.style.opacity = 1 - cl(P / .15);
  requestAnimationFrame(frame);
}}
// the terminal boot
(function bootType() {{
  let lines = [], i = 0;
  const step = () => {{ if (i >= BOOT.length) return; lines.push(BOOT[i] === "READY" ? "<b>READY</b>" : BOOT[i]); boot.innerHTML = lines.join("\\n") + "\\n<b>_</b>"; i++; setTimeout(step, still ? 0 : 280); }};
  step();
}})();
// typing the two paragraphs
let typed = false, tjob = 0;
function type() {{
  const me = ++tjob, ps = [document.getElementById("p1"), document.getElementById("p2")]; ps.forEach(p => p.innerHTML = "");
  const run = k => {{ if (me !== tjob || k >= ps.length) return; const p = ps[k], tmp = document.createElement("div"); tmp.innerHTML = p.dataset.html; const full = tmp.textContent; let i = 0;
    const tick = () => {{ if (me !== tjob) return; i = Math.min(full.length, i + (still ? full.length : 2)); const clone = tmp.cloneNode(true); let left = i;
      const walk = n => {{ for (const ch of [...n.childNodes]) {{ if (ch.nodeType === 3) {{ if (left <= 0) ch.remove(); else {{ if (ch.length > left) ch.textContent = ch.textContent.slice(0, left); left -= ch.length; }} }} else {{ walk(ch); if (!ch.textContent.length) ch.remove(); }} }} }};
      walk(clone); p.innerHTML = clone.innerHTML + '<span class="cur"></span>';
      if (i < full.length) setTimeout(tick, 18 + Math.random() * 26); else if (k < ps.length - 1) {{ p.innerHTML = clone.innerHTML; setTimeout(() => run(k + 1), 360); }} }};
    tick(); }};
  run(0);
}}
// the pencil, colouring the light in once
const pc = foot.querySelector(".pencil"), px = pc.getContext("2d"), N = pc.width;
const GEM = (Q.gem.match(/-?\\d+\\.?\\d*/g) || []).map(Number).reduce((a, v, i) => (i % 2 ? a[a.length - 1].push(v * N / 100) : a.push([v * N / 100]), a), []);
const tp = Math.min(...GEM.map(p => p[1])), bt = Math.max(...GEM.map(p => p[1]));
const span = y => {{ const xs = []; for (let i = 0; i < GEM.length; i++) {{ const [a, b] = GEM[i], [c2, d] = GEM[(i + 1) % GEM.length]; if ((b <= y) !== (d <= y)) xs.push(a + (c2 - a) * (y - b) / (d - b)); }} xs.sort((p, q) => p - q); return xs.length > 1 ? [xs[0], xs[xs.length - 1]] : null; }};
const seg = (x0, y0, x1, y1) => {{ x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1); let dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1, e = dx + dy; px.fillStyle = "{SKY}";
  for (;;) {{ px.fillRect(x0, y0, 1, 1); if (x0 === x1 && y0 === y1) break; const e2 = 2 * e; if (e2 >= dy) {{ e += dy; x0 += sx; }} if (e2 <= dx) {{ e += dx; y0 += sy; }} }} }};
let job = 0;
function colourIn(delay) {{
  if (still) return; const me = ++job; px.clearRect(0, 0, N, N); pc.style.transition = "none"; pc.style.opacity = 1; const S = []; let y = tp + 1, l = true;
  while (y < bt - 1) {{ const y2 = y + .7 + Math.random() * .9, s = span(y), s2 = span(Math.min(y2, bt - 1)); if (s && s2) S.push(l ? [s[0] - 1 + Math.random() * 1.4, y, s2[1] + 1 - Math.random() * 1.4, y2] : [s[1] + 1 - Math.random() * 1.4, y, s2[0] - 1 + Math.random() * 1.4, y2]); l = !l; y = y2; }}
  let i = 0; const tick = () => {{ if (me !== job) return; for (let n = 0; n < 3 && i < S.length; n++, i++) seg(...S[i]); if (i < S.length) setTimeout(tick, 26); else setTimeout(() => {{ if (me === job) {{ pc.style.transition = "opacity 1.4s ease"; pc.style.opacity = 0; }} }}, 1400); }};
  setTimeout(tick, delay);
}}
document.getElementById("top").addEventListener("click", () => scrollTo({{ top: 0, behavior: still ? "auto" : "smooth" }}));
addEventListener("pointermove", e => {{ mx = e.clientX; my = e.clientY; }});
addEventListener("pointerleave", () => {{ mx = my = -1e9; }});
addEventListener("resize", layout);
// a nudge if nothing happens: after the build, drift down gently once so the page is never stuck on the hero
(document.fonts ? document.fonts.load('500 12px "Commit Mono"') : Promise.resolve()).catch(() => {{}}).finally(() => {{ layout(); T0 = performance.now(); requestAnimationFrame(frame); if (still) scrollTo(0, document.body.scrollHeight); }});
}})();
</script>
</body></html>'''
open("/home/user/antimony-site/index.html", "w").write(html); print(len(html))
