"""Writes /home/user/antimony-site/index.html. The screen is a wall of stone, lit in real time. It opens in the dark: a thread of
light at the crystal, the crack running out to the edges of the screen, a raking light crossing the stone, the cavity opening,
and the print resolving inside the crystal. Afterwards the light follows the pointer. The type is a colophon."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from three import B
HERE = os.path.dirname(os.path.abspath(__file__))
vb, WMB = open(os.path.join(HERE, "../../x/edge/wm.txt")).read().split("\n", 1)
INK, PAPER, SKY = "#0B0C0C", "#EEEAE0", "#94E6FF"
GEOM = {k: B[k] for k in ("ang", "gw", "gh", "pd", "mar")}

FRAG = r"""
precision highp float;
uniform vec2 R; uniform float D, T, uLight, uReach, uFlash, uGlow, uCav, uSheen, uPrint, uNarrow;
uniform vec3 L; uniform vec2 C, PAR; uniform float S, PA; uniform sampler2D P;
const float K = 0.28675;                       // tan 16
const vec2 DIR = vec2(0.27564, -0.96126), NRM = vec2(0.96126, 0.27564);
float h1(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float n2(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  return mix(mix(h1(i), h1(i + vec2(1, 0)), f.x), mix(h1(i + vec2(0, 1)), h1(i + vec2(1, 1)), f.x), f.y); }
float fbm(vec2 p) { float v = 0., a = .5; for (int i = 0; i < 4; i++) { v += a * n2(p); p = p * 2.03 + 17.1; a *= .5; } return v; }
// the crystal and the cavity: a hexagon, sheared to the seam's angle, as in the mark
vec2 unshear(vec2 p) { vec2 q = p - C; q.x += q.y * K; return q; }
float hexd(vec2 q, float w, float h, float pd) { vec2 a = abs(q); vec2 n = normalize(vec2(pd, w * .5));
  return max(a.x - w * .5, dot(a - vec2(0., h * .5), n)); }
float gemD(vec2 p) { return hexd(unshear(p), 38.4 * S, 60. * S, 25.2 * S); }
float cavD(vec2 p) { float m = 6.5 * S * uCav; return hexd(unshear(p), 38.4 * S + m * 2., 60. * S + m * 2.3, 25.2 * S + m * .55); }
// the crack: along the crystal's axis, out of its two points; wide at the cavity, then a hairline, with a little tremor
float crackD(vec2 p, out float t) {
  vec2 q = p - C; float al = dot(q, DIR), pr = dot(q, NRM);
  t = abs(al) - 30. * S / 0.96126;
  float w = .5 + (2.4 * S - .5) * exp(-max(t, 0.) / (R.y * .06));
  pr += ((n2(vec2(al * .03, 3.1)) * .65 + n2(vec2(al * .09, 7.3)) * .35) - .5) * 5. * smoothstep(0., 140., t) + (n2(vec2(al * .4, 9.)) - .5) * .7;
  float d = abs(pr) - w;
  return t > uReach ? 1e4 : d; }
float cutD(vec2 p) { float t; return min(cavD(p), crackD(p, t)); }
float height(vec2 p) {
  float s = fbm(p * .0055) * 3.2 + n2(p * .04 + 5.) * 1.1 + n2(p * .11) * .5 + h1(floor(p * .9)) * .22;
  float e = smoothstep(-1.6, 1.1, cutD(p));
  return mix(-16., s, e); }
void main() {
  vec2 p = vec2(gl_FragCoord.x, R.y * D - gl_FragCoord.y) / D;
  float h = height(p), hx = height(p + vec2(1, 0)), hy = height(p + vec2(0, 1));
  vec3 n = normalize(vec3(-(hx - h), -(hy - h), 1.));
  vec3 lv = L - vec3(p, h); float dl = length(lv); lv /= dl;
  float att = 1. / (1. + dl * dl / (R.x * R.x * 1.7));
  float dif = max(dot(n, lv), 0.), spec = pow(max(dot(reflect(-lv, n), vec3(0, 0, 1)), 0.), 24.) * .25;
  vec3 alb = vec3(.060, .057, .052);
  vec3 col = alb * (.06 * uLight + .8 * dif * att * uLight) + vec3(spec * att * uLight * .12);
  float t; float cd = crackD(p, t), cv = cavD(p), gd = gemD(p);
  vec3 sky = vec3(.58, .90, 1.);
  // in the cut: the dark of the recess, a little of the crystal's light, and, when the crack is new, light leaking through it
  float inCut = 1. - smoothstep(-.5, .8, min(cd, cv));
  float near = exp(-max(gd, 0.) / (40. * S * .25 + 20.));
  col = mix(col, col * .2 + sky * .012 * near * (uGlow * .6 + uPrint * .4), inCut);
  col += sky * uFlash * (1. - smoothstep(-.6, .9, cd)) * (.25 + .75 * exp(-max(t, 0.) / (R.y * .5)));
  // the crystal: first a filament of light along its ridge, filling it; then the print, a little refracted at each facet
  if (gd < 1.) {
    vec2 q = unshear(p); float a = 1. - smoothstep(-.8, .8, gd);
    float fil = exp(-abs(dot(p - C, NRM)) / (1.2 + 60. * S * uGlow)) * uGlow;
    float face = q.x > 0. ? 1. : 0.;
    vec2 bw = vec2(38.4 * S * 1.35, 60. * S * 1.25);
    vec2 uv = (p - C + vec2(bw.x * .5, bw.y * .55) + PAR) / bw; uv.x = (uv.x - .5) * PA + .5; uv.x += (face - .5) * .006;
    vec3 pr = pow(texture2D(P, clamp(uv, .002, .998)).rgb, vec3(2.2));   // the print is stored in sRGB; light it in linear
    vec3 g = mix(sky * min(.12 * uGlow + fil * .9, .62), pr * (.92 + face * .08), uPrint);
    float sh = exp(-pow((dot(p - C, NRM) - mix(-40. * S, 40. * S, uSheen)) / (3. * S), 2.)) * sin(uSheen * 3.14159);
    g += vec3(sh * .55);
    g += vec3(.05) * (1. - smoothstep(0., 1.2, abs(gd))) * uPrint;
    col = mix(col, g, a);
  }
  col = pow(max(col, 0.), vec3(1. / 2.2));
  col += (h1(p + fract(T)) - .5) / 255.;      // a whisper of dither so the dark never bands
  gl_FragColor = vec4(col, 1.);
}
"""

html = f'''<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0B0B0A"><meta name="description" content="Antimony builds software for the people who make the work. Our first product is Orbe.">
<meta property="og:title" content="Antimony"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<title>Antimony</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
@font-face {{ font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifVF.woff2") format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifItalicVF.woff2") format("woff2"); font-weight: 200 700; font-style: italic; font-display: swap; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ height: 100%; background: #000; overflow: hidden; }}
body {{ color: {PAPER}; font: 400 15px/1.6 "Timeless Serif", Georgia, serif; -webkit-font-smoothing: antialiased; }}
a {{ color: inherit; text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: .22em; text-decoration-color: rgba(238,234,224,.3); transition: text-decoration-color .3s ease; }}
a:hover {{ text-decoration-color: currentColor; }}
:focus-visible {{ outline: 1px solid {SKY}; outline-offset: 4px; }}
::selection {{ background: {SKY}; color: {INK}; }}
#c {{ position: fixed; inset: 0; width: 100%; height: 100%; display: block; }}
.still {{ position: fixed; inset: 0; background: #121211 url(assets/home-still.webp) 62% 47% / cover no-repeat; display: none; }}
.nogl .still {{ display: block; }} .nogl #c {{ display: none; }}
.wm {{ position: fixed; left: max(40px, env(safe-area-inset-left, 0px)); top: max(36px, env(safe-area-inset-top, 0px)); height: 18px; width: auto; color: {PAPER}; --lit: {SKY}; }}
.col {{ position: fixed; left: max(40px, env(safe-area-inset-left, 0px)); bottom: max(36px, env(safe-area-inset-bottom, 0px)); max-width: 27em; color: rgba(238,234,224,.62); text-wrap: pretty; }}
.col em {{ color: {PAPER}; }}
.cr {{ position: fixed; right: max(40px, env(safe-area-inset-right, 0px)); bottom: max(36px, env(safe-area-inset-bottom, 0px)); font-size: 12.5px; color: rgba(238,234,224,.34); text-align: right; max-width: 22em; }}
.wm, .col, .cr {{ opacity: 0; transform: translateY(4px); transition: opacity 1.8s ease, transform 1.8s cubic-bezier(.2,.7,.2,1); }}
.on .wm, .on .col, .on .cr {{ opacity: 1; transform: none; }} .on .col {{ transition-delay: .25s; }} .on .cr {{ transition-delay: .5s; }}
@media (max-width: 700px) {{ .wm {{ left: 24px; top: max(28px, env(safe-area-inset-top, 0px)); }} .col {{ left: 24px; right: 24px; bottom: max(28px, env(safe-area-inset-bottom, 0px)); font-size: 15.5px; }} .cr {{ display: none; }} .still {{ background-position: 56% 36%; }} }}
</style></head>
<body>
<canvas id="c" aria-label="A wall of dark stone. A crack runs through it at sixteen degrees and opens into a crystal; through the crystal, a print of the moon"></canvas>
<div class="still" aria-hidden="true"></div>
<svg class="wm" viewBox="{vb}" role="img" aria-label="Antimony">{WMB}</svg>
<p class="col"><em>Antimony</em> builds software for the people who make the work. Our first product is <a href="https://eoinforker.github.io/orbe-site/">Orbe</a>, the creator&#39;s side of every sponsorship deal. We sit on their side of the table, and we mean to stay there for a long time.</p>
<p class="cr">Through the crystal: Utagawa Hiroshige, <i>Autumn Moon over Ishiyama Temple</i>, 1857. Art Institute of Chicago.</p>
<script>
(() => {{ "use strict";
const still = matchMedia("(prefers-reduced-motion: reduce)").matches, fine = matchMedia("(pointer: fine)").matches, root = document.documentElement;
const c = document.getElementById("c"), gl = c.getContext("webgl", {{ antialias: false, alpha: false, preserveDrawingBuffer: false }});
const fail = () => {{ root.classList.add("nogl"); document.body.classList.add("on"); }};
if (!gl) return fail();
const FS = {json.dumps(FRAG)}, VS = "attribute vec2 a; void main() {{ gl_Position = vec4(a, 0., 1.); }}";
const sh = (t, s) => {{ const x = gl.createShader(t); gl.shaderSource(x, s); gl.compileShader(x); if (!gl.getShaderParameter(x, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(x)); return x; }};
let pr; try {{ pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(pr); gl.useProgram(pr); }} catch (e) {{ console.warn(e); return fail(); }}
gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
const al = gl.getAttribLocation(pr, "a"); gl.enableVertexAttribArray(al); gl.vertexAttribPointer(al, 2, gl.FLOAT, false, 0, 0);
const U = {{}}; ["R", "D", "T", "uLight", "uReach", "uFlash", "uGlow", "uCav", "uSheen", "uPrint", "uNarrow", "L", "C", "PAR", "S", "PA", "P"].forEach(k => U[k] = gl.getUniformLocation(pr, k));
// the print, as a texture
const tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex);
gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, 1, 1, 0, gl.RGB, gl.UNSIGNED_BYTE, new Uint8Array([20, 30, 50]));
[gl.TEXTURE_WRAP_S, gl.TEXTURE_WRAP_T].forEach(q => gl.texParameteri(gl.TEXTURE_2D, q, gl.CLAMP_TO_EDGE)); [gl.TEXTURE_MIN_FILTER, gl.TEXTURE_MAG_FILTER].forEach(q => gl.texParameteri(gl.TEXTURE_2D, q, gl.LINEAR));
let PA = 1, dirty = true; const im = new Image(); im.onload = () => {{ gl.bindTexture(gl.TEXTURE_2D, tex); gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, im); PA = 1; dirty = true; }};
im.src = "assets/prints/18972.webp";
let W, H, DPR, Cx, Cy, S, narrow;
function size() {{ DPR = Math.min(fine ? 1 : 1.25, devicePixelRatio || 1); W = innerWidth; H = innerHeight; c.width = Math.round(W * DPR); c.height = Math.round(H * DPR); gl.viewport(0, 0, c.width, c.height);
  narrow = W < 700; const gh = narrow ? Math.min(H * .34, W * .62) : Math.min(H * .38, W * .3); S = gh / 60; Cx = narrow ? W * .56 : W * .62; Cy = narrow ? H * .36 : H * .47; }}
size(); addEventListener("resize", () => {{ size(); dirty = true; }});
// the opening, in seconds
const cl = v => Math.max(0, Math.min(1, v)), seg = (t, a, b) => cl((t - a) / (b - a)), eo = t => 1 - Math.pow(1 - t, 3), expo = t => t >= 1 ? 1 : 1 - Math.pow(2, -10 * t), io = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const FIX = /^#t=/.test(location.hash) ? parseFloat(location.hash.slice(3)) : null;   // a still of any moment, for the kit
let mx = .3, my = .2, lx = -.25, ly = .1, lz = 260, t0 = performance.now(), shown = false, px = 0, py = 0, qx = 0, qy = 0;
if (fine && !still) addEventListener("pointermove", e => {{ mx = e.clientX / W; my = e.clientY / H; qx = -(e.clientX / W - .5) * 12; qy = -(e.clientY / H - .5) * 9; }});
function frame(now) {{
  const t = still ? 99 : FIX !== null ? FIX : (now - t0) / 1000;
  const glow = eo(seg(t, .5, 1.1)), reach = expo(seg(t, 1.0, 1.75)) * Math.hypot(W, H), flash = seg(t, 1.0, 1.08) * (1 - eo(seg(t, 1.2, 3.0)));
  const light = io(seg(t, 1.5, 3.4)), cav = io(seg(t, 1.8, 2.8)), sheen = seg(t, 2.5, 3.3), print = io(seg(t, 2.4, 3.9));
  // a raking light crosses the stone, then comes to rest above and to the left, and leans towards the pointer
  const sweep = io(seg(t, 1.5, 3.6)), rx = .22 + (mx - .3) * .45, ry = .12 + (my - .2) * .35;
  const tx = sweep < 1 ? -.3 + (rx + .3) * sweep : rx, ty = sweep < 1 ? .5 + (ry - .5) * sweep : ry, tz = 70 + 190 * sweep;
  const k = sweep < 1 || FIX !== null ? 1 : .03; lx += (tx - lx) * k; ly += (ty - ly) * k; lz += (tz - lz) * k;
  px += (qx - px) * .05; py += (qy - py) * .05;
  gl.uniform2f(U.R, W, H); gl.uniform1f(U.D, DPR); gl.uniform1f(U.T, t); gl.uniform1f(U.uLight, light); gl.uniform1f(U.uReach, reach); gl.uniform1f(U.uFlash, flash);
  gl.uniform1f(U.uGlow, glow); gl.uniform1f(U.uCav, cav); gl.uniform1f(U.uSheen, sheen); gl.uniform1f(U.uPrint, print); gl.uniform1f(U.uNarrow, narrow ? 1 : 0);
  gl.uniform3f(U.L, lx * W, ly * H, lz); gl.uniform2f(U.C, Cx, Cy); gl.uniform2f(U.PAR, px, py); gl.uniform1f(U.S, S); gl.uniform1f(U.PA, PA); gl.uniform1i(U.P, 0);
  const moving = t < 4.6 || Math.abs(tx - lx) + Math.abs(ty - ly) > 1e-4 || Math.abs(qx - px) + Math.abs(qy - py) > .01 || dirty;
  if (moving) {{ dirty = false; gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex); gl.drawArrays(gl.TRIANGLES, 0, 3); }}
  if (!shown && t > 4.1) {{ shown = true; document.body.classList.add("on"); }}
  requestAnimationFrame(frame);
}}
c.addEventListener("webglcontextlost", e => {{ e.preventDefault(); fail(); }});
requestAnimationFrame(frame);
}})();
</script>
</body></html>'''
open(os.path.join(HERE, "../../index.html"), "w").write(html); print(len(html))
