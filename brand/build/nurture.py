"""Writes ../nurture/index.html: Antimony after Nurture. Nature seen through a window, coloured in by hand.

The mark is a window: its wings and foot show the prints (Hiroshige and Hokusai, public domain, Art Institute of Chicago);
the counter, the gold, is coloured in live with an aliased pencil, one jagged pixel line at a time, the way the album's
scribbles stand for the mess of making something."""
import json, math, os, sys, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from mark import PC, poly, lockup, mark_paths, WM, DOT
from crystal_geometry import HEX
P = {"Sky": "#9CCBEA", "Prussian": "#1F3F7A", "Field": "#8DBF6A", "Pine": "#2F5D50", "Sun": "#F4C84A", "Dawn": "#F2B6A0", "Washi": "#F3ECDD", "Ink": "#1A1D1C"}
NOTE = {"Sky": "a clear day", "Prussian": "Hiroshige's blue, the pigment that came by ship", "Field": "grass in the sun", "Pine": "the trees on every road",
        "Sun": "the gold, always coloured in by hand", "Dawn": "the pink at the edge of a print's sky", "Washi": "the paper everything is printed on", "Ink": "type, and the line of the pencil"}
SRC = json.load(open("../nurture/prints/sources.json"))
ORDER = [87008, 18307, 24800, 3652, 19006, 18972, 81248, 4368]
win = "".join(f'<path d="{poly(PC[k])}" fill="#000"/>' for k in ("wing_l", "wing_r", "foot"))
MASK = "data:image/svg+xml," + urllib.parse.quote(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1.5 -1.5 103 103">{win}</svg>')
CT = PC["counter"]
def lock_wm(fill, dot, style=""):
    return (f'<svg viewBox="-10 {WM["asc"] - WM["cap"] - 40} {WM["w"] + 20} {WM["cap"] + 300}" style="{style}" role="img" aria-label="Antimony">'
            f'<path d="{WM["letters"]}" fill="{fill}"/><path d="{DOT}" fill="{dot}"/></svg>')
def window_block(cls, plates, delay=0):
    return (f'<div class="win {cls}" data-plates="{",".join(f"img/{p}.webp" for p in plates)}" data-delay="{delay}">'
            f'<canvas class="gl" aria-hidden="true"></canvas><canvas class="pencil" width="206" height="206" aria-hidden="true"></canvas>'
            f'<svg class="edge" viewBox="-1.5 -1.5 103 103" aria-hidden="true">' + "".join(f'<path d="{poly(PC[k])}" fill="none" stroke="{P["Prussian"]}" stroke-width=".5" stroke-linejoin="round"/>' for k in ("wing_l", "wing_r", "foot")) + '</svg></div>')
credits = "".join(f'<li><a href="{s["url"]}">{s["title"].split(",")[0].split("(")[0].strip()}</a>, {s["artist"].split(chr(10))[0].split(" ")[0]} {s["artist"].split(chr(10))[0].split(" ")[1] if len(s["artist"].split(chr(10))[0].split(" ")) > 1 else ""}, {s["date"]}</li>' for s in SRC if s["id"] in ORDER)
html = f'''<title>Antimony, Nurture</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* Warm washi ground, Hiroshige's skies seen through the mark, and one thing always done by hand: the gold, coloured in with a jagged pencil. */
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifItalicVF.woff2) format("woff2"); font-weight: 200 700; font-style: italic; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-400.woff2) format("woff2"); font-weight: 400; font-display: swap; }}
@font-face {{ font-family: "Commit Mono"; src: url(fonts/CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
:root {{ {" ".join(f"--{k.lower()}: {v};" for k, v in P.items())} --rule: rgba(31,63,122,.16); --dim: #5E6A73; color-scheme: light;
  --serif: "Timeless Serif", "Iowan Old Style", Georgia, serif; --sans: "Timeless Sans", "Helvetica Neue", Arial, sans-serif; --mono: "Commit Mono", ui-monospace, Menlo, monospace; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: var(--washi); color: var(--ink); }}
body {{ font: 400 16px/1.6 var(--sans); -webkit-font-smoothing: antialiased; }}
a {{ color: var(--prussian); }}
.band {{ padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 72px; }}
.band + .band {{ border-top: 1px solid var(--rule); }}
.in {{ max-width: 1120px; margin-inline: auto; display: grid; gap: 30px; }}
.eyebrow {{ font: 500 11.5px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--dim); }}
h1 {{ font: 400 clamp(44px, 7.4vw, 104px)/.98 var(--serif); letter-spacing: -.022em; color: var(--prussian); text-wrap: balance; }}
h2 {{ font: 400 clamp(32px, 4.2vw, 52px)/1.04 var(--serif); letter-spacing: -.014em; color: var(--prussian); text-wrap: balance; max-width: 17em; }}
p {{ max-width: 37em; }} .dim {{ color: var(--dim); }}
.lede {{ font: 400 clamp(19px, 2vw, 23px)/1.5 var(--serif); max-width: 32em; }}
.hero {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr); gap: 56px; align-items: center; padding-top: 24px; }}
.top {{ display: flex; justify-content: space-between; align-items: center; }}
.top svg {{ height: 26px; width: auto; display: block; }}
.win {{ position: relative; aspect-ratio: 1; width: 100%; max-width: 100%; cursor: pointer; }}
.win .gl {{ position: absolute; inset: 0; width: 100%; height: 100%; -webkit-mask: url("{MASK}") center / 100% 100% no-repeat; mask: url("{MASK}") center / 100% 100% no-repeat; }}
.win .pencil {{ position: absolute; inset: 0; width: 100%; height: 100%; image-rendering: pixelated; image-rendering: crisp-edges; }}
.win .edge {{ position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }}
.hint {{ font: 500 11px var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--dim); }}
.two {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 40px; align-items: center; }}
.pal {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
.sw {{ min-height: 150px; padding: 14px; display: grid; align-content: end; gap: 2px; border-radius: 2px; }}
.sw b {{ font: 400 24px/1.1 var(--serif); }} .sw span {{ font: 400 12px var(--mono); opacity: .85; }} .sw i {{ font: italic 400 14px/1.3 var(--serif); opacity: .85; }}
.prints {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }}
.prints img {{ width: 100%; aspect-ratio: 4 / 3; object-fit: cover; display: block; border-radius: 2px; max-width: 100%; }}
.credits {{ columns: 2; column-gap: 40px; font-size: 13.5px; color: var(--dim); padding-left: 1.1em; }}
.credits li {{ break-inside: avoid; margin-bottom: 6px; }}
.ban {{ position: relative; aspect-ratio: 1584 / 396; max-width: 100%; overflow: hidden; border-radius: 4px; }}
.ban img {{ width: 100%; height: 100%; object-fit: cover; object-position: 50% 40%; display: block; }}
.ban .lab {{ position: absolute; right: 3.4%; bottom: 10%; background: var(--washi); padding: 2.2% 2.6%; display: grid; gap: 6px; border-radius: 2px; }}
.ban .lab svg {{ height: clamp(16px, 2.6vw, 30px); width: auto; display: block; }}
.ban .lab span {{ font: italic 400 clamp(12px, 1.5vw, 18px)/1.2 var(--serif); color: var(--prussian); }}
.posts {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
.post {{ aspect-ratio: 4 / 5; max-width: 100%; display: grid; place-items: center; padding: 14%; border-radius: 2px; position: relative; }}
.post .cap {{ position: absolute; left: 8%; bottom: 6%; right: 8%; font: italic 400 15px/1.3 var(--serif); color: var(--prussian); }}
.say {{ font: italic 400 clamp(24px, 3.2vw, 40px)/1.3 var(--serif); color: var(--prussian); max-width: 22em; }}
@media (max-width: 860px) {{ .hero, .two {{ grid-template-columns: 1fr; gap: 32px; }} .pal, .prints {{ grid-template-columns: 1fr 1fr; }} .posts {{ grid-template-columns: 1fr; }} .credits {{ columns: 1; }} .band {{ padding-block: 52px; }} }}
</style>

<section class="band"><div class="in">
  <div class="top">{lock_wm(P["Prussian"], P["Sun"])}<span class="hint">Tap a window to colour it in again</span></div>
  <div class="hero">
    <div style="display:grid;gap:26px"><h1>for the people who make the work.</h1>
    <p class="lede">Antimony was used to refine gold: it took away everything that was not gold, and the gold was left. We make software that takes away the work around the work, so what is left is yours.</p></div>
    {window_block("hero", ORDER)}
  </div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">The idea</span>
  <h2>Nature seen through a window. The gold, coloured in by hand.</h2>
  <div class="two">
    <div style="display:grid;gap:16px">
      <p>The mark is a crystal with an A struck through it. Here it is a window: through its pieces you see the roads, bays and mountains of Hiroshige and Hokusai, two hundred years old and as calm as the day they were cut.</p>
      <p>The one piece that is not a window is the gold. It is never printed flat. It is coloured in, live, with a jagged pencil, a little outside the lines, every time. Making things is messy; the mark says so.</p>
    </div>
    {window_block("b", [18972, 81248, 3652], 1)}
  </div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">Colour</span>
  <h2>Taken from the prints, then let out into the light.</h2>
  <div class="pal">{"".join(f'<div class="sw" style="background:{v};color:{"#F3ECDD" if k in ("Prussian", "Pine", "Ink") else "#1A1D1C"}"><b>{k}</b><span>{v}</span><i>{NOTE[k]}</i></div>' for k, v in P.items())}</div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">Out in the world</span>
  <h2>Where people will meet it.</h2>
  <div class="ban"><img src="img/19006.webp" alt="Satta Peak in Suruga Province, Hiroshige, 1852"><div class="lab">{lock_wm(P["Prussian"], P["Sun"])}<span>for the people who make the work.</span></div></div>
  <div class="posts">
    <div class="post" style="background:var(--washi);border:1px solid var(--rule)">{window_block("p1", [24800], 2)}<span class="cap">Ejiri in Suruga, Hokusai, about 1831.</span></div>
    <div class="post" style="background:var(--sky)">{window_block("p2", [3652], 3)}<span class="cap">Togetsu Bridge, Arashiyama.</span></div>
    <div class="post" style="background:var(--prussian)">{window_block("p3", [18972], 4)}<span class="cap" style="color:var(--washi)">Autumn moon, Ishiyama.</span></div>
  </div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">How it sounds</span>
  <p class="say">we make things for people who make things. it is not always easy. we are on your side, and we will be here for a long time.</p>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">The prints</span>
  <div class="prints">{"".join(f'<img src="img/{i}.webp" alt="" loading="lazy">' for i in ORDER)}</div>
  <ol class="credits">{credits}</ol>
  <p class="dim">All from the Art Institute of Chicago, released into the public domain under CC0. Inspired by the visual world of Porter Robinson's Nurture, art directed by Samuel Burgess-Johnson; nothing here is taken from it.</p>
</div></section>

<script>
(() => {{ "use strict";
const CT = {json.dumps(CT)}, PAD = 1.5, SUN = "{P["Sun"]}", INK = "{P["Ink"]}";
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
// the pencil: one pixel wide, no smoothing, like the pencil in an old paint program
function pencil(cv, delay) {{
  const x = cv.getContext("2d"), N = cv.width, k = N / (100 + 2 * PAD);
  const P = ([a, b]) => [Math.round((a + PAD) * k), Math.round((b + PAD) * k)];
  const pts = CT.map(P).sort((p, q) => p[1] - q[1]); const A = pts[0], [C, B] = pts.slice(1).sort((p, q) => p[0] - q[0]);   // apex, then left C and right B
  function line(x0, y0, x1, y1, c) {{ let dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1, e = dx + dy; x.fillStyle = c;
    for (;;) {{ x.fillRect(x0, y0, 1, 1); if (x0 === x1 && y0 === y1) break; const e2 = 2 * e; if (e2 >= dy) {{ e += dy; x0 += sx; }} if (e2 <= dx) {{ e += dx; y0 += sy; }} }} }}
  // zigzags from top to bottom across the counter, a little outside the lines
  function strokes() {{
    const out = [], top = A[1], bot = C[1], over = 1.6;
    let y = top + 2, left = true;
    while (y < bot) {{
      const t = (y - top) / (bot - top), hw = (B[0] - C[0]) / 2 * t, cx = A[0];
      const xa = cx - hw - over + Math.random() * 2, xb = cx + hw + over - Math.random() * 2;
      const y2 = y + .55 + Math.random() * .8;
      out.push(left ? [xa, y, xb, y2] : [xb, y, xa, y2]); left = !left; y = y2;
    }}
    return out.map(s => s.map(Math.round));
  }}
  let job = 0;
  function run() {{
    const me = ++job; x.clearRect(0, 0, N, N);
    const S = strokes(); let i = 0;
    const tick = () => {{ if (me !== job) return;
      for (let n = 0; n < (still ? S.length : 2) && i < S.length; n++, i++) {{ const [a, b, c, d] = S[i]; line(a, b, c, d, SUN); }}
      if (i < S.length) setTimeout(tick, 34);
      else {{ // a last pass of the pencil round the edge, in ink, the way you would finish a drawing
        const ed = [[A, B], [B, C], [C, A]]; ed.forEach(([p, q], j) => setTimeout(() => {{ if (me === job) line(p[0], p[1], q[0], q[1], INK); }}, still ? 0 : 160 + j * 140));
      }} }};
    setTimeout(tick, still ? 0 : 600 + delay * 500);
  }}
  cv.parentElement.addEventListener("click", run); run();
}}
// the window: two prints blooming into each other like ink into washi
function bloom(box, srcs, delay) {{
  const c = box.querySelector(".gl"), gl = c.getContext("webgl", {{ antialias: false }}); if (!gl) return;
  const vs = "attribute vec2 p; varying vec2 uv; void main() {{ uv = vec2(p.x * .5 + .5, .5 - p.y * .5); gl_Position = vec4(p, 0., 1.); }}";
  const fs = `precision highp float; varying vec2 uv; uniform sampler2D A, B; uniform float t, seed; uniform vec2 o, ca, cb;
  float h(vec2 p) {{ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }}
  float n(vec2 p) {{ vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f); return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }}
  float fbm(vec2 p) {{ float v = 0., a = .5; for (int i = 0; i < 5; i++) {{ v += a * n(p); p = p * 2.07 + 3.1; a *= .5; }} return v; }}
  vec2 fit(vec2 u, vec2 c) {{ return (u - .5) * c + .5; }}
  void main() {{ float r = length(uv - o), g = t * 1.15;
    float e = r + (fbm(uv * 3.5 + seed) - .5) * .42 * (.25 + t) + (fbm(uv * 22. + seed * 1.7) - .5) * .045;
    float m = 1. - smoothstep(g - .005, g + .005, e), rim = exp(-pow((e - g) / .007, 2.)) * (1. - smoothstep(.8, 1., t)) * step(.001, t);
    vec3 a = texture2D(A, fit(uv, ca)).rgb, b = texture2D(B, fit(uv, cb)).rgb;
    gl_FragColor = vec4(mix(mix(a, b, m), vec3(.12, .25, .48), rim * .7), 1.); }}`;
  const sh = (ty, s) => {{ const q = gl.createShader(ty); gl.shaderSource(q, s); gl.compileShader(q); return q; }};
  const pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(pr); gl.useProgram(pr);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const L = gl.getAttribLocation(pr, "p"); gl.enableVertexAttribArray(L); gl.vertexAttribPointer(L, 2, gl.FLOAT, false, 0, 0);
  const U = k => gl.getUniformLocation(pr, k), tex = [], asp = []; let cur = 0, nxt = srcs.length > 1 ? 1 : 0, t = 0, busy = false, ready = false, seed = 0, o = [.5, .5];
  const load = i => new Promise(res => {{ const im = new Image(); im.onload = () => {{ const tx = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tx); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, im);
    [gl.TEXTURE_MIN_FILTER, gl.TEXTURE_MAG_FILTER].forEach(q => gl.texParameteri(gl.TEXTURE_2D, q, gl.LINEAR)); [gl.TEXTURE_WRAP_S, gl.TEXTURE_WRAP_T].forEach(q => gl.texParameteri(gl.TEXTURE_2D, q, gl.CLAMP_TO_EDGE)); tex[i] = tx; asp[i] = im.width / im.height; res(); }}; im.src = srcs[i]; }});
  const cover = ia => {{ const a = c.width / c.height; return ia > a ? [a / ia, 1] : [1, ia / a]; }};
  const size = () => {{ const r = box.getBoundingClientRect(), d = Math.min(2, devicePixelRatio || 1); c.width = r.width * d; c.height = r.height * d; gl.viewport(0, 0, c.width, c.height); }};
  const draw = () => {{ gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex[cur]); gl.uniform1i(U("A"), 0); gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, tex[nxt]); gl.uniform1i(U("B"), 1);
    gl.uniform1f(U("t"), t); gl.uniform1f(U("seed"), seed); gl.uniform2f(U("o"), o[0], o[1]); gl.uniform2fv(U("ca"), cover(asp[cur])); gl.uniform2fv(U("cb"), cover(asp[nxt])); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4); }};
  const go = () => {{ if (busy || !ready || srcs.length < 2) return; busy = true; seed = Math.random() * 40; o = [.3 + Math.random() * .4, .3 + Math.random() * .4]; const s0 = performance.now(), dur = still ? 1 : 2800;
    (function step(now) {{ const k = Math.min(1, (now - s0) / dur); t = 1 - Math.pow(1 - k, 1.7); draw(); if (k < 1) requestAnimationFrame(step); else {{ cur = nxt; nxt = (nxt + 1) % srcs.length; t = 0; draw(); busy = false; }} }})(s0); }};
  new ResizeObserver(() => {{ size(); if (ready) draw(); }}).observe(box);
  Promise.all(srcs.map((_, i) => load(i))).then(() => {{ ready = true; size(); draw(); if (srcs.length > 1) setTimeout(() => {{ go(); setInterval(go, 6500); }}, 2500 + delay * 900); }});
}}
document.querySelectorAll(".win").forEach(w => {{ const d = +w.dataset.delay; bloom(w, w.dataset.plates.split(","), d); pencil(w.querySelector(".pencil"), d); }});
}})();
</script>
'''
open("../nurture/index.html", "w").write(html); print(len(html))
