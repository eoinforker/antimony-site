"""Writes /home/user/antimony-site/index.html: the Antimony website.
The opening from Section 9 (bands lift, the mark builds in pixels, flies home); the page after Pebblebed (paper, mono and
serif, plain words); the crystal as a window onto the prints (Nurture), the light coloured in by hand; the giant wordmark foot."""
import json, os, re, sys, random, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from three import break_parts, brk, CONT
from kit import WM, WM_Y0, WM_Y1
INK, PAPER, SKY, WASHI, PRUSSIAN = "#141311", "#EEEAE0", "#94E6FF", "#F3ECDD", "#1F3F7A"
Q = break_parts()
PRINTS = ["assets/prints/19006.webp", "assets/prints/24800.webp", "assets/prints/3652.webp", "assets/prints/18972.webp", "assets/prints/87008.webp"]
GEMMASK = "data:image/svg+xml," + urllib.parse.quote(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="{Q["gem"]}"/></svg>')
def stone(stone_col=INK, ground="none", style="", cls="", id_=""):
    """the Break with its crystal left open, for windows: stone, crack and cavity only"""
    return (f'<svg {f"id={chr(34)}{id_}{chr(34)} " if id_ else ""}class="{cls}" viewBox="0 0 100 100" style="{style}" aria-hidden="true"><defs><clipPath id="sc{cls}{id_}">{CONT["tile"]}</clipPath>'
            f'<mask id="sm{cls}{id_}"><rect width="100" height="100" fill="#fff"/><path d="{Q["seam"]}" fill="#000"/><path d="{Q["cav"]}" fill="#000"/></mask></defs>'
            f'<g clip-path="url(#sc{cls}{id_})">{"" if ground == "none" else f"<rect width={chr(34)}100{chr(34)} height={chr(34)}100{chr(34)} fill={chr(34)}{ground}{chr(34)}/>"}'
            f'<rect width="100" height="100" fill="{stone_col}" mask="url(#sm{cls}{id_})"/></g></svg>')
def wordmark(fill=INK, style=""):
    return f'<svg viewBox="-10 {WM_Y0} {WM["w"] + 20} {WM_Y1 - WM_Y0}" style="{style}" role="img" aria-label="Antimony"><path d="{WM["letters"]}" fill="{fill}"/><path d="{WM["dot"]}" fill="{fill}"/></svg>'
rng = random.Random(51)
NOISE = "".join(rng.choice("··:▪ ▫⁘·▴ ") for _ in range(1100))
COPY = [
 "Creators do the work. Then they do the work around the work: the briefs, the contracts, the invoices, the chasing. We build software that takes the second part away.",
 'Our first product is <a href="https://eoinforker.github.io/orbe-site/">Orbe</a>, the creator\'s side of every sponsorship deal. It holds the money until the work is delivered.',
 "Antimony is a metal. It was used to refine gold: melted with it, it took up everything that was not gold. Alchemists called it the wolf of metals. We liked that."]
MD = """# Antimony

Software for the people who make the work.

Creators do the work. Then they do the work around the work: the briefs, the contracts, the invoices, the chasing. We build software that takes the second part away.

Our first product is Orbe (https://eoinforker.github.io/orbe-site/), the creator's side of every sponsorship deal. It holds the money until the work is delivered.

Antimony is a metal. It was used to refine gold: melted with it, it took up everything that was not gold. Alchemists called it the wolf of metals. We liked that.

## The mark

A stone split open, and a crystal grown in the break.

## Facts

- Element: 51, Sb, from the Latin stibium
- Found as: stibnite, long grey prisms that grow in the cracks of rock
- Used for: refining gold
- Rarely: found alone
- We make: Orbe, and what comes after it
"""
html = f'''<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="{PAPER}"><meta name="description" content="Antimony makes software for the people who make the work. Our first product is Orbe.">
<meta property="og:title" content="Antimony"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<title>Antimony</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* Paper, a mono for structure and a serif for the voice (Pebblebed); the opening from Section 9; the crystal as a window (Nurture). */
@font-face {{ font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifVF.woff2") format("woff2"); font-weight: 200 700; font-display: block; }}
@font-face {{ font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifItalicVF.woff2") format("woff2"); font-weight: 200 700; font-style: italic; font-display: swap; }}
@font-face {{ font-family: "Commit Mono"; src: url("assets/fonts/CommitMono-Latin-VF.woff2") format("woff2"); font-weight: 200 700; font-display: block; }}
:root {{ --paper: {PAPER}; --ink: {INK}; --dim: #6C6A64; --sky: {SKY}; --prussian: {PRUSSIAN}; --rule: rgba(20,19,17,.12); --gut: max(16px, env(safe-area-inset-left, 0px)); --gutr: max(16px, env(safe-area-inset-right, 0px)); color-scheme: light; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ background: var(--paper); color: var(--ink); }}
body {{ font: 400 13.5px/1.62 "Commit Mono", ui-monospace, Menlo, monospace; -webkit-font-smoothing: antialiased; }}
a {{ color: var(--prussian); text-decoration: none; }} a:hover {{ text-decoration: underline; text-underline-offset: 3px; }}
:focus-visible {{ outline: 1px solid var(--prussian); outline-offset: 3px; }}
::selection {{ background: var(--sky); color: var(--ink); }}
.wrap {{ padding-left: var(--gut); padding-right: var(--gutr); }}
/* the opening */
#intro {{ position: fixed; inset: 0; z-index: 20; background: var(--ink); transition: background-color .8s cubic-bezier(.4,0,.2,1), opacity .6s ease; }}
#intro.paper {{ background: transparent; }} #intro.gone {{ opacity: 0; pointer-events: none; }}
#intro canvas {{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; }}
.bands {{ position: fixed; inset: 0; z-index: 21; display: grid; grid-template-columns: repeat(6, 1fr); pointer-events: none; }}
.bands i {{ background: linear-gradient(180deg, var(--ink), #2448FF 40%, var(--sky) 62%, var(--paper) 80%, var(--ink)); background-size: 100% 300%; animation: band 1.4s cubic-bezier(.6,0,.2,1) forwards; }}
.bands i:nth-child(2) {{ animation-delay: .05s }} .bands i:nth-child(3) {{ animation-delay: .1s }} .bands i:nth-child(4) {{ animation-delay: .15s }} .bands i:nth-child(5) {{ animation-delay: .2s }} .bands i:nth-child(6) {{ animation-delay: .25s }}
@keyframes band {{ 0% {{ background-position: 0 0 }} 70% {{ background-position: 0 100%; transform: none }} 100% {{ background-position: 0 100%; transform: translateY(-101%) }} }}
main, header, footer {{ transition: opacity .9s ease .1s; }}
body.opening main, body.opening footer, body.opening header .copy {{ opacity: 0; }}
/* the page */
header {{ display: flex; justify-content: space-between; align-items: start; gap: 20px; padding-block: calc(22px + env(safe-area-inset-top, 0px)) 0; }}
.brand {{ display: grid; gap: 4px; }} .brand h1 {{ font: 400 clamp(22px, 2.2vw, 28px)/1.1 "Timeless Serif", Georgia, serif; letter-spacing: -.01em; }}
.brand span {{ color: var(--dim); }}
.right {{ display: grid; justify-items: end; gap: 16px; }}
#logo {{ width: 30px; height: 30px; display: block; cursor: pointer; }}
nav {{ display: grid; gap: 2px; text-transform: uppercase; letter-spacing: .04em; font-size: 12px; justify-items: end; }} nav a {{ color: var(--ink); }} nav span {{ color: var(--dim); }}
.cols {{ display: grid; grid-template-columns: repeat(3, minmax(0, 18em)); gap: 32px; padding-block: 72px 40px; padding-left: clamp(0px, 4vw, 60px); }}
.cols p {{ max-width: 34ch; }}
.ask {{ font: 400 clamp(20px, 1.9vw, 24px)/1.4 "Timeless Serif", Georgia, serif; padding-left: clamp(0px, 4vw, 60px); padding-bottom: 72px; max-width: 40em; }}
.stage {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 48px; align-items: center; background: {WASHI}; border-radius: 14px; padding: clamp(24px, 5vw, 72px); margin-inline: var(--gut) var(--gutr); }}
.win {{ position: relative; aspect-ratio: 1; width: min(100%, 520px); max-width: 100%; justify-self: center; cursor: pointer; }}
.win > * {{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; }}
.win .gl, .win .pencil {{ -webkit-mask: url("{GEMMASK}") center / 100% 100% no-repeat; mask: url("{GEMMASK}") center / 100% 100% no-repeat; }}
.win .pencil {{ image-rendering: pixelated; pointer-events: none; }}
.stage h2 {{ font: 400 clamp(30px, 4vw, 56px)/1.02 "Timeless Serif", Georgia, serif; letter-spacing: -.018em; color: var(--ink); text-wrap: balance; }}
.stage h2 em {{ font-style: normal; color: var(--prussian); }}
.stage p {{ margin-top: 18px; color: #4A4741; max-width: 36ch; }}
.cap {{ color: var(--dim); padding: 10px var(--gutr) 0 calc(var(--gut) + 4px); }}
.two {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 40px; padding-block: 80px 24px; padding-left: clamp(0px, 4vw, 60px); max-width: 1100px; }}
.two h3 {{ font: 400 26px/1.1 "Timeless Serif", Georgia, serif; margin-bottom: 14px; }}
.facts {{ display: grid; grid-template-columns: 9em minmax(0, 1fr); }}
.facts span {{ padding: 9px 0; border-top: 1px solid var(--rule); }} .facts span:nth-child(odd) {{ color: var(--dim); text-transform: uppercase; font-size: 11.5px; letter-spacing: .05em; padding-top: 11px; }}
.orbe {{ display: flex; gap: 18px; align-items: start; }} .orbe img {{ width: 64px; height: 64px; display: block; flex: none; }}
footer {{ padding-block: 80px 24px; }}
.big {{ display: block; width: 100%; height: auto; }}
.noise {{ color: #ABA9A1; font-size: 11px; line-height: 1.15; letter-spacing: .1em; overflow: hidden; height: 3.5em; word-break: break-all; margin-top: 28px; }}
.fine {{ display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-top: 14px; color: var(--dim); font-size: 12px; }}
.fine button {{ font: inherit; color: var(--prussian); background: none; border: 0; cursor: pointer; text-transform: uppercase; letter-spacing: .05em; }}
.fine button[aria-pressed="true"] {{ color: var(--ink); text-decoration: underline; }}
#md {{ white-space: pre-wrap; font: 400 14px/1.65 "Commit Mono", monospace; max-width: 72ch; padding-block: 48px; }}
body.md main {{ display: none; }} body:not(.md) #md {{ display: none; }}
@media (max-width: 820px) {{ .cols {{ grid-template-columns: 1fr; gap: 18px; padding-block: 44px 28px; }} .stage, .two {{ grid-template-columns: 1fr; gap: 32px; }} .facts {{ grid-template-columns: 7.5em minmax(0, 1fr); }} }}
@media (prefers-reduced-motion: reduce) {{ #intro, .bands {{ display: none; }} body.opening main, body.opening footer, body.opening header .copy {{ opacity: 1; }} }}
</style></head>
<body class="opening">
<div class="bands" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i></div>
<div id="intro" aria-hidden="true"><canvas id="px"></canvas></div>
<div class="wrap"><header>
  <div class="brand copy"><h1>Antimony.</h1><span>Software for the people who make the work.</span></div>
  <div class="right"><button id="replay" aria-label="Antimony. Play the opening again" style="all:unset;cursor:pointer">{brk(style="width:30px;height:30px;display:block").replace("<svg ", "<svg id=\"logo\" ", 1)}</button>
  <nav aria-label="Main" class="copy"><a href="https://eoinforker.github.io/orbe-site/">Orbe</a><a href="#about">About</a><span>Letters, soon</span></nav></div>
</header></div>
<main>
  <div class="wrap"><div class="cols">{"".join(f"<p>{c}</p>" for c in COPY)}</div>
  <p class="ask">What is left, once the work around the work is gone, is yours.</p></div>
  <section class="stage" aria-label="The mark">
    <div class="win" id="win" title="Tap to colour the light in"><canvas class="gl" aria-hidden="true"></canvas><canvas class="pencil" width="220" height="220" aria-hidden="true"></canvas>{stone(INK, style="")}</div>
    <div><h2>A stone, split open. A crystal grown in <em>the break</em>.</h2><p>Look through it and the world is still there: the light, the road, the work. Antimony grows in the cracks of rock, under pressure; what is left is the part of value.</p></div>
  </section>
  <p class="cap">Through the crystal: Hokusai and Hiroshige, from the Art Institute of Chicago, in the public domain. Tap it to colour the light in.</p>
  <div class="wrap"><div class="two" id="about">
    <div><h3>Facts</h3><div class="facts">
      <span>Element</span><span>51, Sb, from the Latin stibium</span>
      <span>Found as</span><span>Stibnite, long grey prisms that grow in the cracks of rock</span>
      <span>Used for</span><span>Refining gold</span>
      <span>Rarely</span><span>Found alone</span>
      <span>We make</span><span><a href="https://eoinforker.github.io/orbe-site/">Orbe</a>, and what comes after it</span></div></div>
    <div><h3>Our first product</h3><div class="orbe"><img src="assets/orbe-mark.png" alt="The Orbe mark"><p>Orbe is the creator's side of every sponsorship deal: the brief, the contract and the payment in one place, and the money held until the work is delivered. <a href="https://eoinforker.github.io/orbe-site/">Visit Orbe</a></p></div></div>
  </div></div>
</main>
<div class="wrap" id="md" aria-label="This page as Markdown">{MD}</div>
<div class="wrap"><footer>
  {wordmark(INK).replace("<svg ", "<svg class=\"big\" ", 1)}
  <div class="noise" aria-hidden="true">{NOISE}</div>
  <div class="fine"><span>© 2026 Antimony</span><span><button type="button" id="b-render" aria-pressed="true">Render</button> / <button type="button" id="b-md" aria-pressed="false">Markdown</button></span></div>
</footer></div>
<script>
(() => {{ "use strict";
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
const Q = {json.dumps({k: Q[k] for k in ("seam", "cav", "gem", "facet")})}, SKY = "{SKY}", INK = "{INK}", PAPER = "#F3F0E8", PRINTS = {json.dumps(PRINTS)};
/* ---------- the opening: the mark builds in pixels on ink, then flies home to the logo ---------- */
const intro = document.getElementById("intro"), c = document.getElementById("px"), x = c.getContext("2d"), logo = document.getElementById("logo");
function sample(n) {{
  const S = 400, o = document.createElement("canvas"); o.width = o.height = S; const g = o.getContext("2d"), k = S / 100;
  g.scale(k, k); const rr = new Path2D(); rr.roundRect ? rr.roundRect(0, 0, 100, 100, 22) : rr.rect(0, 0, 100, 100);
  g.fillStyle = "#fff"; g.fill(rr); g.globalCompositeOperation = "destination-out"; g.fill(new Path2D(Q.seam)); g.fill(new Path2D(Q.cav));
  g.globalCompositeOperation = "source-over"; g.fillStyle = "#f00"; g.fill(new Path2D(Q.gem)); g.fillStyle = "rgba(0,0,255,1)"; g.fill(new Path2D(Q.facet));
  const d = g.getImageData(0, 0, S, S).data, out = [];
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {{
    const px = Math.floor((i + .5) / n * S), py = Math.floor((j + .5) / n * S), q = (py * S + px) * 4;
    if (d[q + 3] < 128) continue; const kind = d[q] > 200 && d[q + 1] > 200 ? 0 : d[q] > 200 ? 1 : 2;   // 0 stone, 1 crystal, 2 lit facet
    out.push({{ i, j, u: (i + .5) / n, v: (j + .5) / n, kind }});
  }}
  return out;
}}
const rgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)), mix = (a, b, t) => {{ const A = rgb(a), B = rgb(b); return `rgb(${{A.map((v, i) => Math.round(v + (B[i] - v) * t)).join(",")}})`; }};
const COL = [[PAPER, INK], [SKY, SKY], ["#C3F1FF", "#B5EEFF"]];
let W, H, cells = [], T0, big, home, running = false;
const BUILD = 1.25, HOLD = 2.4, FLY = 1.5, cl = v => Math.max(0, Math.min(1, v)), ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
function layout() {{
  const d = Math.min(2, devicePixelRatio || 1); W = innerWidth; H = innerHeight; c.width = W * d; c.height = H * d; x.setTransform(d, 0, 0, d, 0, 0);
  const s = Math.min(W * .62, H * .56), n = W < 600 ? 40 : 56; big = {{ s, n, ox: W / 2 - s / 2, oy: H * .46 - s / 2 }};
  const r = logo.getBoundingClientRect(); home = {{ s: r.width, ox: r.left, oy: r.top }};
  cells = sample(n).map(p => ({{ ...p, d: Math.random() * .8 + p.v * .6, w: Math.random() * .35 }}));
}}
function frame() {{
  const t = (performance.now() - T0) / 1000, f = cl((t - BUILD - HOLD) / FLY);
  x.clearRect(0, 0, W, H); const cs = big.s / big.n;
  for (const p of cells) {{
    const a = cl((t - BUILD - p.d) / .25); if (a <= 0) continue;
    const e = ease(cl((f - p.w * .5) / (1 - p.w * .5 + 1e-6)));
    const bx = big.ox + p.u * big.s, by = big.oy + p.v * big.s, hx = home.ox + p.u * home.s, hy = home.oy + p.v * home.s;
    const X = bx + (hx - bx) * e, Y = by + (hy - by) * e - Math.sin(e * Math.PI) * 26 * (1 - p.w), sz = (cs - 1) + ((home.s / big.n) - (cs - 1)) * e;
    x.globalAlpha = 1 - cl((f - .88) / .12);
    x.fillStyle = a < 1 ? SKY : mix(COL[p.kind][0], COL[p.kind][1], cl((f - .55) / .35));
    x.fillRect(X - sz * a / 2, Y - sz * a / 2, sz * a, sz * a);
  }}
  x.globalAlpha = 1;
  logo.style.opacity = cl((f - .82) / .18);
  if (f > .45) intro.classList.add("paper");
  if (t > BUILD + HOLD + FLY * .7) document.body.classList.remove("opening");
  if (t < BUILD + HOLD + FLY + .2) requestAnimationFrame(frame); else {{ intro.classList.add("gone"); running = false; }}
}}
function play() {{ if (running) return; running = true; intro.classList.remove("gone", "paper"); document.body.classList.add("opening"); logo.style.opacity = 0; scrollTo(0, 0); layout(); T0 = performance.now(); requestAnimationFrame(frame); }}
document.getElementById("replay").addEventListener("click", play);
addEventListener("resize", () => running && layout());
if (still) {{ intro.classList.add("gone"); document.body.classList.remove("opening"); }}
else (document.fonts ? document.fonts.load('400 20px "Timeless Serif"') : Promise.resolve()).catch(() => {{}}).finally(play);
/* ---------- the window: prints bloom into each other like ink into washi ---------- */
const box = document.getElementById("win"), gc = box.querySelector(".gl"), gl = gc.getContext("webgl", {{ antialias: false }});
if (gl) {{
  const vs = "attribute vec2 p; varying vec2 uv; void main() {{ uv = vec2(p.x * .5 + .5, .5 - p.y * .5); gl_Position = vec4(p, 0., 1.); }}";
  const fs = `precision highp float; varying vec2 uv; uniform sampler2D A, B; uniform float t, seed; uniform vec2 o, ca, cb;
  float h(vec2 p) {{ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }}
  float n(vec2 p) {{ vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f); return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }}
  float fbm(vec2 p) {{ float v = 0., a = .5; for (int i = 0; i < 5; i++) {{ v += a * n(p); p = p * 2.07 + 3.1; a *= .5; }} return v; }}
  vec2 fit(vec2 u, vec2 c) {{ return (u - .5) * c + .5; }}
  void main() {{ vec2 q = (uv - .5) * vec2(.62, .64) + vec2(.5, .515); float r = length(uv - o), g = t * 1.15;
    float e = r + (fbm(uv * 3.5 + seed) - .5) * .42 * (.25 + t) + (fbm(uv * 22. + seed * 1.7) - .5) * .045;
    float m = 1. - smoothstep(g - .005, g + .005, e), rim = exp(-pow((e - g) / .007, 2.)) * (1. - smoothstep(.8, 1., t)) * step(.001, t);
    vec3 a = texture2D(A, fit(q, ca)).rgb, b = texture2D(B, fit(q, cb)).rgb;
    gl_FragColor = vec4(mix(mix(a, b, m), vec3(.12, .25, .48), rim * .7), 1.); }}`;
  const sh = (ty, s) => {{ const q = gl.createShader(ty); gl.shaderSource(q, s); gl.compileShader(q); return q; }};
  const pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(pr); gl.useProgram(pr);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const L = gl.getAttribLocation(pr, "p"); gl.enableVertexAttribArray(L); gl.vertexAttribPointer(L, 2, gl.FLOAT, false, 0, 0);
  const U = k => gl.getUniformLocation(pr, k), tex = [], asp = []; let cur = 0, nxt = 1, t = 0, busy = false, ready = false, seed = 0, o = [.5, .5];
  const load = i => new Promise(res => {{ const im = new Image(); im.onload = () => {{ const tx = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tx); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, im);
    [gl.TEXTURE_MIN_FILTER, gl.TEXTURE_MAG_FILTER].forEach(q => gl.texParameteri(gl.TEXTURE_2D, q, gl.LINEAR)); [gl.TEXTURE_WRAP_S, gl.TEXTURE_WRAP_T].forEach(q => gl.texParameteri(gl.TEXTURE_2D, q, gl.CLAMP_TO_EDGE)); tex[i] = tx; asp[i] = im.width / im.height; res(); }}; im.src = PRINTS[i]; }});
  const cover = ia => {{ const a = .62 / .64; return ia > a ? [a / ia, 1] : [1, ia / a]; }};
  const size = () => {{ const r = box.getBoundingClientRect(), d = Math.min(2, devicePixelRatio || 1); gc.width = r.width * d; gc.height = r.height * d; gl.viewport(0, 0, gc.width, gc.height); }};
  const draw = () => {{ gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex[cur]); gl.uniform1i(U("A"), 0); gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, tex[nxt]); gl.uniform1i(U("B"), 1);
    gl.uniform1f(U("t"), t); gl.uniform1f(U("seed"), seed); gl.uniform2f(U("o"), o[0], o[1]); gl.uniform2fv(U("ca"), cover(asp[cur])); gl.uniform2fv(U("cb"), cover(asp[nxt])); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4); }};
  const go = () => {{ if (busy || !ready) return; busy = true; seed = Math.random() * 40; o = [.38 + Math.random() * .24, .38 + Math.random() * .24]; const s0 = performance.now(), dur = still ? 1 : 2800;
    (function step(now) {{ const k = Math.min(1, (now - s0) / dur); t = 1 - Math.pow(1 - k, 1.7); draw(); if (k < 1) requestAnimationFrame(step); else {{ cur = nxt; nxt = (nxt + 1) % PRINTS.length; t = 0; draw(); busy = false; }} }})(s0); }};
  new ResizeObserver(() => {{ size(); if (ready) draw(); }}).observe(box);
  Promise.all(PRINTS.map((_, i) => load(i))).then(() => {{ ready = true; size(); draw(); if (!still) setInterval(go, 7000); }});
}}
/* ---------- the pencil: the light coloured in by hand, once, a little outside the lines ---------- */
const pc = box.querySelector(".pencil"), px = pc.getContext("2d"), N = pc.width;
const GEM = (Q.gem.match(/-?\\d+\\.?\\d*/g) || []).map(Number).reduce((a, v, i) => (i % 2 ? a[a.length - 1].push(v * N / 100) : a.push([v * N / 100]), a), []);
const top_ = Math.min(...GEM.map(p => p[1])), bot = Math.max(...GEM.map(p => p[1]));
const span = y => {{ const xs = []; for (let i = 0; i < GEM.length; i++) {{ const [a, b] = GEM[i], [c2, d] = GEM[(i + 1) % GEM.length]; if ((b <= y) !== (d <= y)) xs.push(a + (c2 - a) * (y - b) / (d - b)); }} xs.sort((p, q) => p - q); return xs.length > 1 ? [xs[0], xs[xs.length - 1]] : null; }};
const seg = (x0, y0, x1, y1) => {{ x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1); let dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1, e = dx + dy; px.fillStyle = SKY;
  for (;;) {{ px.fillRect(x0, y0, 1, 1); if (x0 === x1 && y0 === y1) break; const e2 = 2 * e; if (e2 >= dy) {{ e += dy; x0 += sx; }} if (e2 <= dx) {{ e += dx; y0 += sy; }} }} }};
let job = 0;
function colourIn(delay) {{
  const me = ++job; px.clearRect(0, 0, N, N); pc.style.transition = "none"; pc.style.opacity = 1; const S = []; let y = top_ + 1, l = true;
  while (y < bot - 1) {{ const y2 = y + .7 + Math.random() * .9, s = span(y), s2 = span(Math.min(y2, bot - 1)); if (s && s2) S.push(l ? [s[0] - 1 + Math.random() * 1.4, y, s2[1] + 1 - Math.random() * 1.4, y2] : [s[1] + 1 - Math.random() * 1.4, y, s2[0] - 1 + Math.random() * 1.4, y2]); l = !l; y = y2; }}
  let i = 0; const tick = () => {{ if (me !== job) return; for (let n = 0; n < 3 && i < S.length; n++, i++) seg(...S[i]); if (i < S.length) setTimeout(tick, 28);
    else setTimeout(() => {{ if (me === job) {{ pc.style.transition = "opacity 1.4s ease"; pc.style.opacity = 0; }} }}, 1500); }};
  setTimeout(tick, delay);
}}
box.addEventListener("click", () => colourIn(0));
if (!still) colourIn((BUILD + HOLD + FLY + .8) * 1000);
/* ---------- render or markdown ---------- */
const rb = document.getElementById("b-render"), mb = document.getElementById("b-md");
const set = md => {{ document.body.classList.toggle("md", md); rb.setAttribute("aria-pressed", !md); mb.setAttribute("aria-pressed", md); }};
rb.addEventListener("click", () => set(false)); mb.addEventListener("click", () => set(true));
}})();
</script>
</body></html>'''
open("/home/user/antimony-site/index.html", "w").write(html); print(len(html))
