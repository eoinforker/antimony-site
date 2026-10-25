"""Writes /home/user/antimony-site/index.html. One object on black: the Break as a slab of stone with the crystal set in it,
lit from one side. Scrolling turns it to face you and opens the seam a little; the light spills onto the cut faces; the
brief appears. Everything else is left out."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from shapely.geometry import Polygon, box
from three import break_parts, brk
HERE = os.path.dirname(os.path.abspath(__file__))
Q = break_parts()
vb, WMB = open(os.path.join(HERE, "../../x/edge/wm.txt")).read().split("\n", 1)
INK, PAPER, SKY = "#0B0C0C", "#EEEAE0", "#94E6FF"
BEVEL = .9
pts = lambda d: [(float(a), float(b)) for a, b in re.findall(r"(-?\d+\.?\d*)[ ,](-?\d+\.?\d*)", d)]
# the stone: the tile with the seam and the cavity cut out, which leaves two halves. Shrunk by the bevel, which grows them back.
tile = box(22, 22, 78, 78).buffer(22, resolution=20)
stone = tile.difference(Polygon(pts(Q["seam"]))).difference(Polygon(pts(Q["cav"])))
halves = sorted(stone.geoms, key=lambda g: g.centroid.x)
def ring(g): g = g.buffer(-BEVEL, join_style=2).simplify(.05); c = list(g.exterior.coords)[:-1]; return [[round(x - 50, 3), round(50 - y, 3)] for x, y in c]
GEO = {"L": ring(halves[0]), "R": ring(halves[1]), "gem": [[round(x - 50, 3), round(50 - y, 3)] for x, y in pts(Q["gem"])]}
fallback = brk(stone="#1C1B19", ground="none", style="width:100%;height:100%")

CSS = r"""
@font-face { font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifVF.woff2") format("woff2"); font-weight: 200 700; font-display: swap; }
@font-face { font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifItalicVF.woff2") format("woff2"); font-weight: 200 700; font-style: italic; font-display: swap; }
@font-face { font-family: "Commit Mono"; src: url("assets/fonts/CommitMono-Latin-VF.woff2") format("woff2"); font-weight: 200 700; font-display: swap; }
:root { --ink: %INK%; --paper: %PAPER%; --sky: %SKY%; color-scheme: dark; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: var(--ink); }
body { color: var(--paper); font: 400 18px/1.55 "Timeless Serif", Georgia, serif; -webkit-font-smoothing: antialiased; height: 280vh; }
a { color: inherit; text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: .2em; text-decoration-color: rgba(238,234,224,.35); }
a:hover { text-decoration-color: currentColor; }
:focus-visible { outline: 1px solid var(--sky); outline-offset: 3px; }
::selection { background: var(--sky); color: var(--ink); }
#c, .fallback { position: fixed; inset: 0; width: 100%; height: 100%; display: block; }
.fallback { display: none; place-items: center; } .fallback svg { width: min(36vh, 60vw); height: auto; }
.nogl .fallback { display: grid; } .nogl #c { display: none; }
header { position: fixed; left: 0; right: 0; top: 0; display: flex; justify-content: space-between; align-items: center;
  padding: calc(26px + env(safe-area-inset-top, 0px)) max(28px, env(safe-area-inset-right, 0px)) 0 max(28px, env(safe-area-inset-left, 0px)); pointer-events: none; }
header svg { height: 20px; width: auto; display: block; color: var(--paper); --lit: var(--sky); }
.meta { font: 400 11px "Commit Mono", monospace; letter-spacing: .06em; color: #6F716D; }
main { position: fixed; left: max(28px, env(safe-area-inset-left, 0px)); bottom: calc(32px + env(safe-area-inset-bottom, 0px)); max-width: 30em; font-size: 17px; color: rgba(238,234,224,.82); opacity: 0; pointer-events: none; }
main.on { pointer-events: auto; }
main p + p { margin-top: .9em; } main em { font-style: italic; color: var(--paper); }
.hint { position: fixed; right: max(28px, env(safe-area-inset-right, 0px)); bottom: calc(32px + env(safe-area-inset-bottom, 0px)); font: 400 11px "Commit Mono", monospace; letter-spacing: .06em; color: #6F716D; transition: opacity .8s ease; }
@media (max-width: 600px) { main { right: 24px; font-size: 16px; } .hint { display: none; } }
"""
for k, v in {"%INK%": INK, "%PAPER%": PAPER, "%SKY%": SKY}.items(): CSS = CSS.replace(k, v)

JS = r"""
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
const G = %GEO%, still = matchMedia("(prefers-reduced-motion: reduce)").matches;
const main = document.getElementById("m"), hint = document.getElementById("hint"), c = document.getElementById("c");
let R;
try { R = new THREE.WebGLRenderer({ canvas: c, antialias: true, powerPreference: "high-performance" }); } catch (e) { document.documentElement.classList.add("nogl"); throw e; }
R.setPixelRatio(Math.min(2, devicePixelRatio || 1)); R.toneMapping = THREE.ACESFilmicToneMapping; R.toneMappingExposure = .95; R.shadowMap.enabled = true; R.shadowMap.type = THREE.PCFSoftShadowMap; R.setClearColor(new THREE.Color("#0B0C0C"), 1);
const scene = new THREE.Scene(), pm = new THREE.PMREMGenerator(R);
scene.environment = pm.fromScene(new RoomEnvironment(), .04).texture;
const cam = new THREE.PerspectiveCamera(26, 1, 1, 4000);

// grain for the stone: a little noise in its roughness and its surface, so the light has something to catch
function grain(n = 512) { const cv = document.createElement("canvas"); cv.width = cv.height = n; const g = cv.getContext("2d"), d = g.createImageData(n, n);
  let s = 7; const r = () => (s = (s * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < n * n; i++) { const v = 150 + (r() - .5) * 70 + (r() < .02 ? 40 : 0); d.data[i * 4] = d.data[i * 4 + 1] = d.data[i * 4 + 2] = v; d.data[i * 4 + 3] = 255; }
  g.putImageData(d, 0, 0); g.filter = "blur(.6px)"; g.drawImage(cv, 0, 0);
  const t = new THREE.CanvasTexture(cv); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(.02, .02); return t; }
const gt = grain();
const stoneM = new THREE.MeshStandardMaterial({ color: 0x100f0e, roughness: .62, metalness: .25, roughnessMap: gt, bumpMap: gt, bumpScale: .12, envMapIntensity: .3 });
const D = 22, ext = { depth: D, bevelEnabled: true, bevelThickness: 1.1, bevelSize: %BEVEL%, bevelSegments: 5, curveSegments: 1 };
const half = p => { const s = new THREE.Shape(p.map(([x, y]) => new THREE.Vector2(x, y))); const g = new THREE.ExtrudeGeometry(s, ext); g.translate(0, 0, -D / 2);
  // world-space uvs, so the grain runs across both halves as one stone
  const P = g.attributes.position, uv = new Float32Array(P.count * 2); for (let i = 0; i < P.count; i++) { uv[i * 2] = P.getX(i) + P.getZ(i) * .7; uv[i * 2 + 1] = P.getY(i) + P.getZ(i) * .3; } g.setAttribute("uv", new THREE.BufferAttribute(uv, 2)); return new THREE.Mesh(g, stoneM); };
const L = half(G.L), Rr = half(G.R);
// the crystal: the hexagon as a prism with a roof, its ridge running from point to point, so its two halves are two facets
function crystal(h, depth = 12, roof = 10) {
  const n = h.length, cx = h.reduce((a, p) => a + p[0], 0) / n, cy = h.reduce((a, p) => a + p[1], 0) / n;
  const sh = h.map(([x, y]) => [cx + (x - cx) * .965, cy + (y - cy) * .965]);
  const zf = i => (i === 0 || i === 3) ? depth / 2 + roof : depth / 2, v = [];
  const tri = (a, b, cc) => v.push(...a, ...b, ...cc);
  const F = i => [sh[i][0], sh[i][1], zf(i)], B = i => [sh[i][0], sh[i][1], -depth / 2];
  tri(F(0), F(2), F(1)); tri(F(0), F(3), F(2)); tri(F(0), F(5), F(4)); tri(F(0), F(4), F(3));          // the two facets
  for (let i = 0; i < n; i++) { const j = (i + 1) % n; tri(F(i), F(j), B(j)); tri(F(i), B(j), B(i)); }      // the sides
  tri(B(0), B(1), B(2)); tri(B(0), B(2), B(3)); tri(B(0), B(3), B(4)); tri(B(0), B(4), B(5));            // the back
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.Float32BufferAttribute(v, 3)); g.computeVertexNormals(); return g; }
const gemM = new THREE.MeshPhysicalMaterial({ color: 0x62cdf2, emissive: 0x2aa6d6, emissiveIntensity: .22, roughness: .1, metalness: .05, clearcoat: 1, clearcoatRoughness: .04, ior: 1.6, flatShading: true, envMapIntensity: .9, side: THREE.DoubleSide });
const gem = new THREE.Mesh(crystal(G.gem), gemM);
const mark = new THREE.Group(); mark.add(L, Rr, gem); scene.add(mark);
[L, Rr, gem].forEach(m => { m.castShadow = true; m.receiveShadow = true; });
// it stands on a floor that goes to black, so it is a thing in a room, not a picture of an icon
const ink = new THREE.Color("#0B0C0C"); scene.fog = new THREE.Fog(ink, 300, 640);
const pool = (() => { const cv = document.createElement("canvas"); cv.width = cv.height = 256; const g = cv.getContext("2d"), r = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  r.addColorStop(0, "#fff"); r.addColorStop(.45, "#777"); r.addColorStop(1, "#000"); g.fillStyle = r; g.fillRect(0, 0, 256, 256); return new THREE.CanvasTexture(cv); })();
// the floor is only a pool of light around the stone, fading into the page
const floor = new THREE.Mesh(new THREE.PlaneGeometry(520, 520), new THREE.MeshStandardMaterial({ color: 0x0e0e0d, roughness: .72, metalness: .1, envMapIntensity: 0, alphaMap: pool, transparent: true, depthWrite: false }));
floor.rotation.x = -Math.PI / 2; floor.position.y = -51.2; floor.receiveShadow = true; scene.add(floor);
// light: one key from the upper left, a cool rim from behind, and the crystal's own light, which reaches the cut faces as the seam opens
const key = new THREE.SpotLight(0xfff1e0, 9e4, 0, .34, 1, 1.7); key.position.set(-150, 210, 190); key.castShadow = true; key.shadow.mapSize.set(2048, 2048); key.shadow.radius = 6; key.shadow.bias = -.0004; key.shadow.camera.near = 50; key.shadow.camera.far = 800; scene.add(key); scene.add(key.target);
const rim = new THREE.DirectionalLight(0xe8f4ff, .9); rim.position.set(220, 120, -200); scene.add(rim);
const low = new THREE.DirectionalLight(0x94e6ff, .25); low.position.set(60, -200, 80); scene.add(low);
const glow = new THREE.PointLight(0x94e6ff, 0, 90, 1.6); glow.position.set(0, 0, 6); mark.add(glow);
// the seam, in the drawing's units: its direction, and the normal the halves part along
const S16 = Math.sin(16 * Math.PI / 180), C16 = Math.cos(16 * Math.PI / 180), SD = new THREE.Vector2(S16, C16), NN = new THREE.Vector2(C16, -S16);
let W = 1, H = 1, P = 0, Pd = 0, px = 0, py = 0, tx = 0, ty = 0;
function size() { W = innerWidth; H = innerHeight; R.setSize(W, H, false); cam.aspect = W / H;
  const want = Math.min(.44, (W / H) * .6); cam.position.set(0, 0, (100 / want) / (2 * Math.tan(THREE.MathUtils.degToRad(cam.fov / 2)))); cam.updateProjectionMatrix(); scene.fog.near = cam.position.z * .75; scene.fog.far = cam.position.z * 1.6; }
const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2, cl = v => Math.max(0, Math.min(1, v)), seg = (p, a, b) => cl((p - a) / (b - a));
const z0 = () => cam.position.z;
let Z0 = 0, t0 = performance.now();
function frame(now) {
  const t = (now - t0) / 1000, max = document.documentElement.scrollHeight - innerHeight;
  P = still ? 1 : max > 0 ? cl(scrollY / max) : 0; Pd += (P - Pd) * .06;
  const turn = ease(seg(Pd, 0, .7)), open = ease(seg(Pd, .15, .8)), text = seg(Pd, .62, .9);
  px += (tx - px) * .04; py += (ty - py) * .04;
  const idle = still ? 0 : Math.sin(t * .23) * .5 + .5;
  // from three quarters to face on, as you scroll; the pointer leans it a little
  mark.rotation.y = THREE.MathUtils.degToRad(lerp(-32, -4, turn) + px * 4 + (1 - turn) * idle * 2);
  mark.rotation.x = 0;
  const g = open * 3.2, sl = open * 1.6;
  L.position.set(-g - sl * .4, 0, 0); Rr.position.set(g + sl * .4, 0, 0);
  gem.position.z = open * 3; gem.rotation.z = -open * .03;
  gemM.emissiveIntensity = .2 + open * .2 + (still ? 0 : Math.sin(t * 1.05) * .02); glow.intensity = open * 2600;
  const z = Z0 * lerp(1.08, .9, turn); cam.position.set(px * -6, lerp(34, 14, turn) - py * 4, z); cam.lookAt(0, lerp(-6, 2, turn) + text * 6, 0);
  main.style.opacity = text; main.style.transform = `translateY(${(1 - text) * 10}px)`; main.classList.toggle("on", text > .5);
  hint.style.opacity = Pd < .03 && t > 1.2 ? 1 : 0;
  R.render(scene, cam); requestAnimationFrame(frame);
}
const lerp = (a, b, t) => a + (b - a) * t;
addEventListener("pointermove", e => { tx = e.clientX / innerWidth * 2 - 1; ty = e.clientY / innerHeight * 2 - 1; });
addEventListener("resize", () => { size(); Z0 = z0(); });
size(); Z0 = z0(); requestAnimationFrame(frame);
"""
JS = JS.replace("%GEO%", json.dumps(GEO)).replace("%BEVEL%", str(BEVEL))

html = f'''<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="{INK}"><meta name="description" content="Antimony builds software for the people who make the work. Our first product is Orbe.">
<meta property="og:title" content="Antimony"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<title>Antimony</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>{CSS}</style></head>
<body>
<canvas id="c" aria-label="The Antimony mark: a stone split open, with a crystal set in the break"></canvas>
<div class="fallback" aria-hidden="true">{fallback}</div>
<header><svg viewBox="{vb}" role="img" aria-label="Antimony">{WMB}</svg><span class="meta">london</span></header>
<main id="m">
  <p><em>Antimony</em> builds software for the people who make the work. Our first product is <a href="https://eoinforker.github.io/orbe-site/">Orbe</a>, the creator&#39;s side of every sponsorship deal.</p>
  <p>We sit on their side of the table, and we mean to stay there for a long time.</p>
</main>
<div class="hint" id="hint" aria-hidden="true">scroll</div>
<script>addEventListener("error", e => {{ if (/three|WebGL/i.test(String(e.message) + (e.filename || ""))) document.documentElement.classList.add("nogl"); }}, true);</script>
<script type="importmap">{{ "imports": {{ "three": "https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.js", "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/" }} }}</script>
<script type="module">{JS}</script>
</body></html>'''
open(os.path.join(HERE, "../../index.html"), "w").write(html); print(len(html))
