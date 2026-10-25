"""Writes /home/user/antimony-site/index.html. A dark wall of stone, and the pointer is the light: the grain shows wherever it
falls. The opening is brief: the crack runs out of the crystal, the cavity opens, the print resolves. The stone's surface is
computed once into a texture; each frame only lights it, so it holds sixty frames a second on a phone."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from three import B
HERE = os.path.dirname(os.path.abspath(__file__))
vb, WMB = open(os.path.join(HERE, "../../x/edge/wm.txt")).read().split("\n", 1)
INK, PAPER, SKY = "#0B0C0C", "#EEEAE0", "#94E6FF"

COMMON = r"""
precision highp float;
float h1(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float n2(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  return mix(mix(h1(i), h1(i + vec2(1, 0)), f.x), mix(h1(i + vec2(0, 1)), h1(i + vec2(1, 1)), f.x), f.y); }
"""
# once per size: the grain of the stone, as a normal map (xy) with its height (z)
BAKE = COMMON + r"""
uniform vec2 R; uniform float D;
float fbm(vec2 p) { float v = 0., a = .5; for (int i = 0; i < 5; i++) { v += a * n2(p); p = p * 2.03 + 17.1; a *= .5; } return v; }
float hgt(vec2 p) { return fbm(p * .0055) * 4.2 + fbm(p * .045 + 5.) * 1.5 + n2(p * .16) * .35 + h1(floor(p * .9)) * .22; }
void main() { vec2 p = vec2(gl_FragCoord.x, R.y * D - gl_FragCoord.y) / D;
  float h = hgt(p), hx = hgt(p + vec2(1, 0)), hy = hgt(p + vec2(0, 1));
  vec3 n = normalize(vec3(-(hx - h), -(hy - h), 1.));
  gl_FragColor = vec4(n.xy * .5 + .5, clamp(h / 6., 0., 1.), 1.); }
"""
# every frame: the cuts, worked out exactly, and the light
LIGHT = COMMON + r"""
uniform vec2 R; uniform float D, T, uReach, uFlash, uGlow, uCav, uPrint, uFill;
uniform vec3 L; uniform vec2 C, PAR; uniform float S, Rad; uniform sampler2D N, P;
const float K = 0.28675;
const vec2 DIR = vec2(0.27564, -0.96126), NRM = vec2(0.96126, 0.27564);
vec2 unshear(vec2 p) { vec2 q = p - C; q.x += q.y * K; return q; }
float hexd(vec2 q, float w, float h, float pd) { vec2 a = abs(q); vec2 n = normalize(vec2(pd, w * .5)); return max(a.x - w * .5, dot(a - vec2(0., h * .5), n)); }
float gemD(vec2 p) { return hexd(unshear(p), 38.4 * S, 60. * S, 25.2 * S); }
float cavD(vec2 p) { float m = 6.5 * S * uCav; return hexd(unshear(p), 38.4 * S + m * 2., 60. * S + m * 2.3, 25.2 * S + m * .55); }
float crackD(vec2 p, out float t) { vec2 q = p - C; float al = dot(q, DIR), pr = dot(q, NRM);
  t = abs(al) - 30. * S / 0.96126;
  float w = .55 + (2.4 * S - .55) * exp(-max(t, 0.) / (R.y * .06));
  pr += ((n2(vec2(al * .03, 3.1)) * .65 + n2(vec2(al * .09, 7.3)) * .35) - .5) * 5. * smoothstep(0., 140., t) + (n2(vec2(al * .4, 9.)) - .5) * .7;
  return t > uReach ? 1e4 : abs(pr) - w; }
float cut(vec2 p) { float t; return min(cavD(p), crackD(p, t)); }
void main() {
  vec2 fc = gl_FragCoord.xy, p = vec2(fc.x, R.y * D - fc.y) / D;
  vec4 g = texture2D(N, fc / (R * D));
  vec3 n = normalize(vec3(g.xy * 2. - 1., 1.)); float h = g.z * 6.;
  float t; float cd = crackD(p, t), cv = cavD(p), c0 = min(cd, cv), gd = gemD(p);
  // the cut edges: a bevel, its slope taken from the distance to the cut
  float ex = cut(p + vec2(1, 0)) - c0, ey = cut(p + vec2(0, 1)) - c0, edge = 1. - smoothstep(0., 2.4, abs(c0 - .6));
  n = normalize(mix(n, normalize(vec3(-ex * 3.2, -ey * 3.2, 1.)), edge * step(c0, 4.)));
  float inCut = 1. - smoothstep(-.5, .8, c0); h = mix(h, -14., inCut);
  // the light is where the pointer is, held a little off the wall; and a faint fill from above, so the room is never black
  vec3 lv = L - vec3(p, h); float dl = length(lv); lv /= dl;
  float att = 1. / (1. + dl * dl / (Rad * Rad));
  float dif = max(dot(n, lv), 0.), spec = pow(max(dot(reflect(-lv, n), vec3(0, 0, 1)), 0.), 30.);
  float fill = max(dot(n, normalize(vec3(-.4, -.7, .6))), 0.) * uFill;
  vec3 alb = vec3(.052, .049, .045);
  vec3 col = alb * (.018 + fill * .2 + dif * att * 1.1) + vec3(spec * att * .09 * edge);   // only the cut edges shine
  vec3 sky = vec3(.58, .90, 1.);
  col = mix(col, col * .18 + sky * .006 * (uGlow + uPrint) * exp(-max(gd, 0.) / 30.), inCut);
  col += sky * uFlash * (1. - smoothstep(-.6, .9, cd)) * (.25 + .75 * exp(-max(t, 0.) / (R.y * .5)));
  if (gd < 1.) {
    vec2 q = unshear(p); float a = 1. - smoothstep(-.8, .8, gd), face = q.x > 0. ? 1. : 0.;
    float fil = exp(-abs(dot(p - C, NRM)) / (1.2 + 60. * S * uGlow)) * uGlow;
    vec2 bw = vec2(38.4 * S * 1.35, 60. * S * 1.25);
    vec2 uv = (p - C + vec2(bw.x * .5, bw.y * .55) + PAR) / bw; uv.x += (face - .5) * .006;
    vec3 pr = pow(texture2D(P, clamp(uv, .002, .998)).rgb, vec3(2.2));
    vec3 c = mix(sky * min(.1 * uGlow + fil * .9, .6), pr * (.8 + face * .06), uPrint);
    // each facet is a plane of glass: the light glints on it as it passes
    vec3 fn = normalize(vec3(face > .5 ? .42 : -.42, -.1, 1.));
    float gl = pow(max(dot(reflect(-lv, fn), vec3(0, 0, 1)), 0.), 60.) * att;
    c += vec3(gl * .9 + .03 * att * face);
    c += vec3(.04) * (1. - smoothstep(0., 1.2, abs(gd))) * uPrint;
    col = mix(col, c, a);
  }
  col = pow(max(col, 0.), vec3(1. / 2.2));
  col += (h1(p + fract(T)) - .5) / 255.;
  gl_FragColor = vec4(col, 1.);
}
"""

html = f'''<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#060606"><meta name="description" content="Antimony builds software for the people who make the work. Our first product is Orbe.">
<meta property="og:title" content="Antimony"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<title>Antimony</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
@font-face {{ font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifVF.woff2") format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifItalicVF.woff2") format("woff2"); font-weight: 200 700; font-style: italic; font-display: swap; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ height: 100%; background: #060606; overflow: hidden; }}
body {{ color: {PAPER}; font: 400 15px/1.6 "Timeless Serif", Georgia, serif; -webkit-font-smoothing: antialiased; cursor: crosshair; }}
a {{ color: inherit; text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: .22em; text-decoration-color: rgba(238,234,224,.3); transition: text-decoration-color .2s ease; cursor: pointer; }}
a:hover {{ text-decoration-color: currentColor; }}
:focus-visible {{ outline: 1px solid {SKY}; outline-offset: 4px; }}
::selection {{ background: {SKY}; color: {INK}; }}
#c {{ position: fixed; inset: 0; width: 100%; height: 100%; display: block; touch-action: none; }}
.still {{ position: fixed; inset: 0; background: #0D0D0C url(assets/home-still.webp) 62% 47% / cover no-repeat; display: none; }}
.nogl .still {{ display: block; }} .nogl #c {{ display: none; }}
.wm {{ position: fixed; left: max(40px, env(safe-area-inset-left, 0px)); top: max(36px, env(safe-area-inset-top, 0px)); height: 18px; width: auto; color: {PAPER}; --lit: {SKY}; }}
.col {{ position: fixed; left: max(40px, env(safe-area-inset-left, 0px)); bottom: max(36px, env(safe-area-inset-bottom, 0px)); max-width: 27em; color: rgba(238,234,224,.6); text-wrap: pretty; }}
.col em {{ color: {PAPER}; }}
.cr {{ position: fixed; right: max(40px, env(safe-area-inset-right, 0px)); bottom: max(36px, env(safe-area-inset-bottom, 0px)); font-size: 12.5px; color: rgba(238,234,224,.32); text-align: right; max-width: 22em; }}
.wm, .col, .cr {{ opacity: 0; transition: opacity .9s ease; }} .on .wm, .on .col, .on .cr {{ opacity: 1; }} .on .col {{ transition-delay: .12s; }} .on .cr {{ transition-delay: .24s; }}
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
const still = matchMedia("(prefers-reduced-motion: reduce)").matches, fine = matchMedia("(pointer: fine)").matches, root = document.documentElement, body = document.body;
const FIX = /^#t=/.test(location.hash) ? parseFloat(location.hash.slice(3)) : null;   // a still of any moment, for the kit
let seen = false; try {{ seen = sessionStorage.getItem("antimony-open") === "1"; sessionStorage.setItem("antimony-open", "1"); }} catch (e) {{}}
const c = document.getElementById("c"), gl = c.getContext("webgl", {{ antialias: false, alpha: false }});
const fail = () => {{ root.classList.add("nogl"); body.classList.add("on"); }};
if (!gl) return fail();
const VS = "attribute vec2 a; void main() {{ gl_Position = vec4(a, 0., 1.); }}";
const prog = fs => {{ const p = gl.createProgram(); for (const [t, s] of [[gl.VERTEX_SHADER, VS], [gl.FRAGMENT_SHADER, fs]]) {{ const x = gl.createShader(t); gl.shaderSource(x, s); gl.compileShader(x);
  if (!gl.getShaderParameter(x, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(x)); gl.attachShader(p, x); }} gl.linkProgram(p); return p; }};
let PB, PL; try {{ PB = prog({json.dumps(BAKE)}); PL = prog({json.dumps(LIGHT)}); }} catch (e) {{ console.warn(e); return fail(); }}
gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
const use = p => {{ gl.useProgram(p); const a = gl.getAttribLocation(p, "a"); gl.enableVertexAttribArray(a); gl.vertexAttribPointer(a, 2, gl.FLOAT, false, 0, 0); }};
const loc = (p, ks) => Object.fromEntries(ks.map(k => [k, gl.getUniformLocation(p, k)]));
const UB = loc(PB, ["R", "D"]), U = loc(PL, ["R", "D", "T", "uReach", "uFlash", "uGlow", "uCav", "uPrint", "uFill", "L", "C", "PAR", "S", "Rad", "N", "P"]);
const mk = () => {{ const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t); [gl.TEXTURE_WRAP_S, gl.TEXTURE_WRAP_T].forEach(q => gl.texParameteri(gl.TEXTURE_2D, q, gl.CLAMP_TO_EDGE));
  [gl.TEXTURE_MIN_FILTER, gl.TEXTURE_MAG_FILTER].forEach(q => gl.texParameteri(gl.TEXTURE_2D, q, gl.LINEAR)); return t; }};
const nt = mk(), fb = gl.createFramebuffer(), pt = mk();
gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, 1, 1, 0, gl.RGB, gl.UNSIGNED_BYTE, new Uint8Array([20, 30, 50]));
let dirty = true; const im = new Image(); im.onload = () => {{ gl.bindTexture(gl.TEXTURE_2D, pt); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, im); dirty = true; }};
im.src = "assets/prints/18972.webp";
let W, H, DPR, Cx, Cy, S;
function size() {{
  DPR = Math.min(2, devicePixelRatio || 1); W = innerWidth; H = innerHeight; c.width = Math.round(W * DPR); c.height = Math.round(H * DPR);
  const narrow = W < 700, gh = narrow ? Math.min(H * .34, W * .62) : Math.min(H * .38, W * .3); S = gh / 60; Cx = narrow ? W * .56 : W * .62; Cy = narrow ? H * .36 : H * .47;
  // bake the stone's surface once, at full resolution
  gl.bindTexture(gl.TEXTURE_2D, nt); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, c.width, c.height, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, nt, 0);
  gl.viewport(0, 0, c.width, c.height); use(PB); gl.uniform2f(UB.R, W, H); gl.uniform1f(UB.D, DPR); gl.drawArrays(gl.TRIANGLES, 0, 3);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null); dirty = true;
}}
size(); addEventListener("resize", size);
const cl = v => Math.max(0, Math.min(1, v)), seg = (t, a, b) => cl((t - a) / (b - a)), eo = t => 1 - Math.pow(1 - t, 3), expo = t => t >= 1 ? 1 : 1 - Math.pow(2, -10 * t);
// the light: it rests above the crystal, to the left; the pointer takes it at once. On a phone, a touch moves it, and it drifts home.
let hx = .44, hy = .26, tx = hx, ty = hy, lx = -.1, ly = .55, px = 0, py = 0, qx = 0, qy = 0, active = 0, t0 = performance.now();
const aim = (x, y) => {{ tx = x / W; ty = y / H; qx = -(tx - .5) * 14; qy = -(ty - .5) * 10; active = performance.now(); }};
addEventListener("pointermove", e => aim(e.clientX, e.clientY), {{ passive: true }});
addEventListener("pointerdown", e => aim(e.clientX, e.clientY), {{ passive: true }});
const D0 = seen || still ? -10 : 0;    // a second visit in the same session skips the opening
function frame(now) {{
  const t = FIX !== null ? FIX : (now - t0) / 1000 - D0;
  const glow = eo(seg(t, .1, .4)), reach = expo(seg(t, .3, .75)) * Math.hypot(W, H), flash = seg(t, .3, .34) * (1 - eo(seg(t, .45, 1.6)));
  const cav = eo(seg(t, .6, 1.1)), print = eo(seg(t, .75, 1.5)), fill = eo(seg(t, .5, 1.3));
  // the light swings in from the lower left during the opening, then answers the pointer directly
  const idle = !fine && now - active > 2600;
  if (idle) {{ tx += (hx + Math.sin(now / 4200) * .05 - tx) * .02; ty += (hy + Math.cos(now / 5100) * .03 - ty) * .02; }}
  const k = t < 1.4 ? .09 : .32; lx += (tx - lx) * k; ly += (ty - ly) * k; px += (qx - px) * .2; py += (qy - py) * .2;
  const moving = t < 1.8 || Math.abs(tx - lx) + Math.abs(ty - ly) > 2e-4 || Math.abs(qx - px) + Math.abs(qy - py) > .02 || idle || dirty;
  if (moving) {{ dirty = false;
    gl.viewport(0, 0, c.width, c.height); use(PL);
    gl.uniform2f(U.R, W, H); gl.uniform1f(U.D, DPR); gl.uniform1f(U.T, t); gl.uniform1f(U.uReach, reach); gl.uniform1f(U.uFlash, flash); gl.uniform1f(U.uGlow, glow);
    gl.uniform1f(U.uCav, cav); gl.uniform1f(U.uPrint, print); gl.uniform1f(U.uFill, fill);
    gl.uniform3f(U.L, lx * W, ly * H, Math.min(W, H) * .07); gl.uniform1f(U.Rad, Math.max(W, H) * .26 * (.35 + .65 * fill));
    gl.uniform2f(U.C, Cx, Cy); gl.uniform2f(U.PAR, px, py); gl.uniform1f(U.S, S);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, nt); gl.uniform1i(U.N, 0);
    gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, pt); gl.uniform1i(U.P, 1);
    gl.drawArrays(gl.TRIANGLES, 0, 3); }}
  if (t > .9) body.classList.add("on");
  requestAnimationFrame(frame);
}}
c.addEventListener("webglcontextlost", e => {{ e.preventDefault(); fail(); }});
requestAnimationFrame(frame);
}})();
</script>
</body></html>'''
open(os.path.join(HERE, "../../index.html"), "w").write(html); print(len(html))
