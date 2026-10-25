"""Writes /home/user/antimony-site/index.html. The whole screen is a terminal. The Break is drawn in it in characters; a slow
scroll opens the stone along its seam, carries you into the crystal, lets a print bloom inside it, then wipes the page to paper
at the seam's angle, where the mark closes small at the foot and two paragraphs are typed."""
import json, os, sys, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from three import break_parts, CONT
Q = break_parts()
HERE = os.path.dirname(os.path.abspath(__file__))
vb, WMB = open(os.path.join(HERE, "../../x/edge/wm.txt")).read().split("\n", 1)
INK, PAPER, SKY, PRU = "#0B0C0C", "#EEEAE0", "#94E6FF", "#1F3F7A"
GEMMASK = "data:image/svg+xml," + urllib.parse.quote(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="{Q["gem"]}"/></svg>')
stone = (f'<svg id="stone" viewBox="0 0 100 100" aria-hidden="true"><defs><clipPath id="sc">{CONT["tile"]}</clipPath><mask id="sm"><rect width="100" height="100" fill="#fff"/>'
         f'<path d="{Q["seam"]}" fill="#000"/><path d="{Q["cav"]}" fill="#000"/></mask></defs><g clip-path="url(#sc)"><rect width="100" height="100" fill="#141311" mask="url(#sm)"/></g></svg>')
WORDS = "ANTIMONY SOFTWARE FOR THE PEOPLE WHO MAKE THE WORK ORBE THE BRIEF THE CONTRACT PAID ON TIME STIBIUM 51 SB WHAT IS LEFT IS YOURS "
BOOT = ["antimony", "sb 51  stibium  121.760", "splitting stone", "growing crystal", "ready"]

CSS = r"""
@font-face { font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifVF.woff2") format("woff2"); font-weight: 200 700; font-display: block; }
@font-face { font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifItalicVF.woff2") format("woff2"); font-weight: 200 700; font-style: italic; font-display: block; }
@font-face { font-family: "Commit Mono"; src: url("assets/fonts/CommitMono-Latin-VF.woff2") format("woff2"); font-weight: 200 700; font-display: block; }
:root { --paper: %PAPER%; --ink: %INK%; --sky: %SKY%; --pru: %PRU%; --hud: #8C918E; --hudb: #E7E2D6; color-scheme: dark; }
body.paper { --hud: #77746C; --hudb: #26292A; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html { background: var(--ink); }
body { background: var(--ink); color: #26292A; font: 400 19px/1.55 "Timeless Serif", Georgia, serif; -webkit-font-smoothing: antialiased; height: 620vh; }
a { color: inherit; text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: .18em; text-decoration-color: rgba(38,41,42,.35); } a:hover { text-decoration-color: currentColor; }
:focus-visible { outline: 1px solid var(--pru); outline-offset: 3px; }
::selection { background: var(--sky); color: var(--ink); }
#c { position: fixed; inset: 0; width: 100%; height: 100%; display: block; }
.hud { position: fixed; inset: 0; pointer-events: none; font: 400 11px/1.7 "Commit Mono", monospace; letter-spacing: .06em; color: var(--hud); transition: color .5s ease; }
.hud > * { position: absolute; }
.hud b { font-weight: 400; color: var(--hudb); transition: color .5s ease; }
.hud i { font-style: normal; color: var(--sky); }
body.paper .hud i { color: var(--pru); }
.tl { left: max(20px, env(safe-area-inset-left, 0px)); top: calc(18px + env(safe-area-inset-top, 0px)); }
.wm { display: block; height: 19px; width: auto; color: var(--hudb); --lit: var(--sky); transition: color .5s ease; margin-bottom: 14px; }
body.paper .wm { --lit: #2E8FC4; }
.boot { white-space: pre; transition: opacity .6s ease; }
.tr { right: max(20px, env(safe-area-inset-right, 0px)); top: calc(20px + env(safe-area-inset-top, 0px)); text-align: right; white-space: pre; }
.bl { left: max(20px, env(safe-area-inset-left, 0px)); bottom: calc(18px + env(safe-area-inset-bottom, 0px)); white-space: pre; transition: opacity .5s ease; }
.br { right: max(20px, env(safe-area-inset-right, 0px)); bottom: calc(18px + env(safe-area-inset-bottom, 0px)); text-align: right; white-space: pre; transition: opacity .5s ease; }
.bar { display: block; width: 168px; height: 1px; background: currentColor; opacity: .35; margin-top: 8px; position: relative; }
.bar s { position: absolute; left: 0; top: -1px; height: 3px; width: 0; background: var(--sky); text-decoration: none; }
body.paper .bar s { background: var(--pru); }
.hint { left: 50%; bottom: calc(22px + env(safe-area-inset-bottom, 0px)); transform: translateX(-50%); text-transform: uppercase; letter-spacing: .16em; transition: opacity .5s ease; }
.hint::after { content: ""; display: block; width: 1px; height: 22px; margin: 8px auto 0; background: currentColor; animation: fall 2.2s ease-in-out infinite; transform-origin: top; }
@keyframes fall { 0% { transform: scaleY(0); } 50% { transform: scaleY(1); } 100% { transform: scaleY(1); opacity: 0; } }
main { position: fixed; left: 0; right: 0; top: 0; max-width: 640px; margin: 0 auto; padding: 18vh max(24px, env(safe-area-inset-right, 0px)) 0 max(24px, env(safe-area-inset-left, 0px)); opacity: 0; pointer-events: none; }
main.on { pointer-events: auto; }
.prompt { font: 400 12px "Commit Mono", monospace; color: #6C6A64; letter-spacing: .02em; margin-bottom: 1.6em; }
.prompt i { font-style: normal; color: var(--pru); }
main p { text-wrap: pretty; min-height: 1.55em; } main p + p { margin-top: 1.4em; } main em { font-style: italic; }
.cur { display: inline-block; width: .5em; height: 1.05em; background: var(--sky); vertical-align: -.16em; margin-left: .06em; animation: blink 1.06s steps(1) infinite; }
@keyframes blink { 50% { opacity: 0; } }
.foot { position: fixed; left: 50%; bottom: calc(64px + env(safe-area-inset-bottom, 0px)); width: 92px; height: 92px; transform: translateX(-50%); opacity: 0; }
.foot.on { pointer-events: auto; }
#top { all: unset; display: block; width: 100%; height: 100%; cursor: pointer; border-radius: 22%; }
#top:focus-visible { outline: 1px solid var(--pru); outline-offset: 4px; }
.win, .win > * { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
.win .img, .win .pencil { -webkit-mask: url("%GEMMASK%") center / 100% 100% no-repeat; mask: url("%GEMMASK%") center / 100% 100% no-repeat; }
.win .img { background: url(assets/prints/19006.webp) 48% 40% / 260% auto no-repeat; animation: drift 24s ease-in-out infinite alternate; }
@keyframes drift { to { background-position: 56% 52%; } }
.win .pencil { image-rendering: pixelated; pointer-events: none; }
@media (max-width: 600px) { body { font-size: 17.5px; } main { padding-top: 15vh; } .foot { width: 76px; height: 76px; } .tr .x { display: none; } .bar { width: 120px; } .br { display: none; } }
@media (prefers-reduced-motion: reduce) { .win .img, .cur, .hint::after { animation: none; } }
"""

JS = r"""
(() => { "use strict";
const Q = %Q%, WORDS = "%WORDS%", BOOT = %BOOT%;
const GLYPH = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/<>[]{}=+*#%&$:";
const RAMP = " .·:;-=+*x#%@";
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = id => document.getElementById(id);
const c = $("c"), x = c.getContext("2d"), main = $("m"), foot = $("foot"), boot = $("boot"), hint = $("hint");
const lerp = (a, b, t) => a + (b - a) * t, cl = v => v < 0 ? 0 : v > 1 ? 1 : v;
const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2, seg = (p, a, b) => cl((p - a) / (b - a));
const S16 = Math.sin(16 * Math.PI / 180), C16 = Math.cos(16 * Math.PI / 180);
// the seam runs from the bottom left to the top right, 16 degrees off the vertical; N points from the left half to the right
const SD = [S16, -C16], N = [C16, S16], CX = 50, CY = 51.5;

// bitmaps of the parts, sampled in mark units (0 to 100)
const R = 320, K = R / 100;
function bitmap(draw) { const o = document.createElement("canvas"); o.width = o.height = R; const g = o.getContext("2d"); g.scale(K, K); g.fillStyle = "#fff"; draw(g); const d = g.getImageData(0, 0, R, R).data, a = new Uint8Array(R * R); for (let i = 0; i < a.length; i++) a[i] = d[i * 4 + 3] > 127; return a; }
const tile = new Path2D(); tile.roundRect ? tile.roundRect(0, 0, 100, 100, 22) : tile.rect(0, 0, 100, 100);
const STONE = bitmap(g => { g.fill(tile); g.globalCompositeOperation = "destination-out"; g.fill(new Path2D(Q.seam)); g.fill(new Path2D(Q.cav)); });
const GEM = bitmap(g => g.fill(new Path2D(Q.gem))), FACET = bitmap(g => g.fill(new Path2D(Q.facet)));
const at = (A, u, v) => u >= 0 && v >= 0 && u < 100 && v < 100 ? A[((v * K) | 0) * R + ((u * K) | 0)] : 0;
// the print that blooms in the crystal; sampled for brightness once it loads
let PR = null, PC = null, PW = 0, PH = 0;
const im = new Image(); im.onload = () => { try { PW = 220; PH = Math.round(220 * im.height / im.width); const o = document.createElement("canvas"); o.width = PW; o.height = PH; const g = o.getContext("2d"); g.drawImage(im, 0, 0, PW, PH); const d = g.getImageData(0, 0, PW, PH).data; PR = new Float32Array(PW * PH); PC = new Array(PW * PH); let lo = 1, hi = 0;
    for (let i = 0; i < PR.length; i++) { PR[i] = (d[i * 4] * .3 + d[i * 4 + 1] * .55 + d[i * 4 + 2] * .15) / 255; lo = Math.min(lo, PR[i]); hi = Math.max(hi, PR[i]); }
    // stretch the brightness, and keep the print's own colour, lifted so it glows on black
    for (let i = 0; i < PR.length; i++) { PR[i] = Math.pow(cl((PR[i] - lo) / (hi - lo)), 1.25); const q = [0, 1, 2].map(k => Math.min(255, (Math.round((d[i * 4 + k] * 1.45 + 18) / 16) * 16) | 0)); PC[i] = `rgb(${q})`; } } catch (e) { PR = null; } };
im.src = "assets/prints/19006.webp";
// a little value noise for the grain of the stone
const hsh = (i, j) => { const s = Math.sin(i * 127.1 + j * 311.7) * 43758.5453; return s - Math.floor(s); };
const noise = (u, v) => { const i = Math.floor(u), j = Math.floor(v), f = u - i, g = v - j, a = hsh(i, j), b = hsh(i + 1, j), c2 = hsh(i, j + 1), d = hsh(i + 1, j + 1), su = f * f * (3 - 2 * f), sv = g * g * (3 - 2 * g); return lerp(lerp(a, b, su), lerp(c2, d, su), sv); };

// colour tables, built once so the frame loop never parses a colour
const tab = (a, b, n = 24) => Array.from({ length: n }, (_, i) => { const t = i / (n - 1); return `rgb(${[0, 1, 2].map(k => Math.round(lerp(a[k], b[k], t))).join(",")})`; });
const INKC = [11, 12, 12], PAPERC = [238, 234, 224];
const T_STONE = tab([26, 28, 28], [214, 209, 197]), T_SKY = tab([18, 52, 74], [205, 246, 255]), T_INKON = tab([226, 222, 212], [40, 42, 42]), T_PRU = tab([214, 222, 236], [31, 63, 122]);
const pick = (T, v) => T[(cl(v) * (T.length - 1)) | 0];

let W, H, fs, cw, ch, cols, rows, mark, cells, T0 = 0, mx = -1e9, my = -1e9, P = 0, Pd = 0, rings = [];
function layout() {
  const d = Math.min(2, devicePixelRatio || 1); W = innerWidth; H = innerHeight; c.width = W * d; c.height = H * d; x.setTransform(d, 0, 0, d, 0, 0);
  fs = W < 600 ? 8.5 : W < 1100 ? 10 : 11; cw = fs * .6; ch = fs * 1.18;
  x.font = `500 ${fs}px "Commit Mono", monospace`; x.textBaseline = "middle"; x.textAlign = "center";
  cols = Math.ceil(W / cw); rows = Math.ceil(H / ch);
  const s = Math.min(H * .64, W * .8); mark = { s, ox: W / 2 - s / 2, oy: H * .48 - s / 2 };
  cells = new Array(cols * rows);
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
    const X = (i + .5) * cw, Y = (j + .5) * ch;
    cells[j * cols + i] = { X, Y, n: hsh(i * .37, j * .91) * 99, d: Math.hypot(X - W / 2, Y - H * .48) / Math.max(W, H) * 1.6 + hsh(i, j) * .45, w: (j * cols + i) % WORDS.length };
  }
}
let stage = -1;
const STAGES = ["01  stone", "02  break", "03  light", "04  paper"];
function hudStage(k, p) {
  if (k !== stage) { stage = k; $("st").innerHTML = STAGES.map((s, i) => i === k ? `<b>${s}</b>` : s).join("\n"); }
  $("bs").style.width = (p * 100).toFixed(1) + "%";
}
function frame(now) {
  const t = still ? 99 : (now - T0) / 1000, built = t - 1.2;
  const max = document.documentElement.scrollHeight - innerHeight;
  P = max > 0 ? cl(scrollY / max) : 0; Pd += (P - Pd) * (still ? 1 : .085); if (Math.abs(P - Pd) < 1e-4) Pd = P;
  const p = Pd;
  // the timeline
  const kOpen = ease(seg(p, .06, .34)), kPush = ease(seg(p, .22, .58)), kPrint = ease(seg(p, .36, .56)), kWipe = seg(p, .58, .78), kClose = ease(seg(p, .78, .88)), kText = seg(p, .84, .9);
  const s = mark.s, gap = kOpen * .62 * 100, slide = kOpen * 22, gs = 1 + kOpen * .22, rot = -kOpen * 12 * Math.PI / 180;
  const Z = 1 + Math.pow(kPush, 2.2) * (Math.max(W, H) / s * 3.6), gx = mark.ox + CX / 100 * s, gy = mark.oy + CY / 100 * s;
  const fx = lerp(gx, W / 2, kPush), fy = lerp(gy, H / 2, kPush);
  const cr = Math.cos(rot), sr = Math.sin(rot);
  // the paper wipe, along the seam's angle
  const qmin = -H * S16 - 80, qmax = W * C16 + H * S16 + 80, qw = lerp(qmin, qmax, ease(kWipe));
  const fade = 1 - kClose;
  x.fillStyle = "rgb(11,12,12)"; x.fillRect(0, 0, W, H);
  if (kWipe > 0) { x.fillStyle = `rgb(${PAPERC})`; x.beginPath(); const L = 4000; const ax = qw * C16, ay = qw * S16; x.moveTo(ax - SD[0] * L, ay - SD[1] * L); x.lineTo(ax + SD[0] * L, ay + SD[1] * L); x.lineTo(ax + SD[0] * L - N[0] * L, ay + SD[1] * L - N[1] * L); x.lineTo(ax - SD[0] * L - N[0] * L, ay - SD[1] * L - N[1] * L); x.closePath(); x.fill(); }
  document.body.classList.toggle("paper", kWipe > .5);
  const near2 = 110 * 110, rr = rings.map(r => ({ x: r.x, y: r.y, R: (t - r.t) * 820 })).filter(r => r.R < Math.max(W, H) * 1.3);
  rings = rings.filter(r => (t - r.t) * 820 < Math.max(W, H) * 1.3);
  let lastF = "";
  for (let k = 0; k < cells.length; k++) {
    const cc = cells[k], a = built - cc.d; if (a < 0) continue;
    const X = cc.X, Y = cc.Y, q = X * C16 + Y * S16, onPaper = q < qw;
    const edge = Math.abs(q - qw) < ch * 1.6 && kWipe > 0 && kWipe < 1;
    // screen to mark units, through the camera
    const wx = (X - fx) / Z + gx, wy = (Y - fy) / Z + gy, mu = (wx - mark.ox) / s * 100, mv = (wy - mark.oy) / s * 100;
    let chr = "", T = null, v = 0, tint = null;
    // the crystal, grown and turned about its centre
    let du = (mu - CX) / gs, dv = (mv - CY) / gs; const gu = CX + du * cr + dv * sr, gv = CY - du * sr + dv * cr;
    if (at(GEM, gu, gv)) {
      if (kPrint > 0 && PR && hsh(cc.n, 3) < kPrint * 1.15) {
        // the print, laid over the whole screen and seen through the crystal
        const ia = PW / PH, sa = W / H, dw = sa > ia ? W : H * ia, dh = sa > ia ? W / ia : H;
        const pu = cl((X - (W - dw) / 2) / dw), pv = cl((Y - (H - dh) / 2) / dh), pi = ((pv * (PH - 1)) | 0) * PW + ((pu * (PW - 1)) | 0), L2 = PR[pi];
        // on black the bright parts of the print are dense; on paper the dark parts are, as ink would be
        if (onPaper) { chr = RAMP[1 + ((1 - L2) * (RAMP.length - 2)) | 0]; T = T_PRU; v = (1 - L2) * .75; }
        else { chr = RAMP[1 + (L2 * (RAMP.length - 2)) | 0]; T = null; tint = PC[pi]; }
      } else {
        const fc = at(FACET, gu, gv), glint = Math.exp(-Math.pow(((gu * C16 + gv * S16) - (t * 18 % 140) + 20) / 6, 2));
        chr = WORDS[cc.w]; if (chr === " ") chr = "·"; T = onPaper ? T_INKON : T_SKY; v = (fc ? .95 : .72) + glint * .4 + (noise(gu * .3, gv * .3 + t * .4) - .5) * .2;
        if (onPaper) v = .55 + v * .3;
      }
    } else {
      // the two halves of the stone, parted along the seam
      const lu = mu + N[0] * gap / 2 + SD[0] * slide, lv = mv + N[1] * gap / 2 + SD[1] * slide;
      const ru = mu - N[0] * gap / 2 - SD[0] * slide, rv = mv - N[1] * gap / 2 - SD[1] * slide;
      const side = (u, w) => (u - CX) * N[0] + (w - CY) * N[1];
      let su = -1, sv = -1;
      if (side(lu, lv) < 0 && at(STONE, lu, lv)) { su = lu; sv = lv; } else if (side(ru, rv) >= 0 && at(STONE, ru, rv)) { su = ru; sv = rv; }
      if (su >= 0) {
        const grain = noise(su * .16, sv * .16) * .55 + noise(su * .5, sv * .5) * .25, strata = Math.sin((su * N[0] + sv * N[1]) * .55 + grain * 4) * .5 + .5;
        v = .08 + grain * .42 + strata * .14 + (1 - (su + sv) / 200) * .16;
        chr = RAMP[1 + (cl(v) * (RAMP.length - 2)) | 0];
        // the cut edges catch the light, so the silhouette stays sharp
        const e = cw / s / Z * 100 * .9;
        if (!at(STONE, su + e, sv) || !at(STONE, su - e, sv) || !at(STONE, su, sv + e * 1.9) || !at(STONE, su, sv - e * 1.9)) { v = .92; chr = "#"; }
        v *= 1 - kPush * .8;  // the stone falls away as you go in T = onPaper ? T_INKON : T_STONE; if (onPaper) v = .2 + v * .4;
      } else if (!onPaper && (k % 7 === 0) && ((k / cols) | 0) % 2 === 0) {
        // the terminal ground
        chr = Math.sin(t * .6 + cc.n) > .97 ? GLYPH[((cc.n * 13) | 0) % GLYPH.length] : "·"; T = T_STONE; v = .14 * (1 - kWipe);
      }
    }
    if (!chr) { if (!edge) continue; chr = GLYPH[((t * 24 + cc.n * 7) | 0) % GLYPH.length]; T = T_SKY; v = .9; }
    // arrival, the pointer, the rings and the wipe's edge all scramble
    let hot = a < .45;
    const dx = X - mx, dy = Y - my;
    if (dx * dx + dy * dy < near2 && p < .3 && Math.sin(t * 20 + cc.n) > -.2) hot = true;
    for (const r of rr) { const dd = Math.hypot(X - r.x, Y - r.y) - r.R; if (dd > -26 && dd < 4) hot = true; }
    if (edge) hot = true;
    if (hot) { chr = GLYPH[((t * 30 + cc.n * 7) | 0) % GLYPH.length]; T = onPaper ? T_PRU : T_SKY; v = Math.max(v, .85); tint = null; }
    if (still && hot) continue;
    if (!T && !tint) continue;
    const f = tint || pick(T, v * (onPaper ? fade : 1));
    if (onPaper && fade < .02) continue;
    if (f !== lastF) { x.fillStyle = f; lastF = f; }
    x.fillText(chr, X, Y);
  }
  // the hud
  hudStage(p < .2 ? 0 : p < .4 ? 1 : p < .62 ? 2 : 3, p);
  hint.style.opacity = p < .02 && built > 1 ? 1 : 0;
  boot.style.opacity = 1 - seg(p, 0, .05);
  $("bl").style.opacity = $("br").style.opacity = 1 - kText;
  foot.style.opacity = kClose; foot.style.transform = `translateX(-50%) scale(${lerp(1.35, 1, kClose)})`; foot.classList.toggle("on", kClose > .5);
  main.style.opacity = kText; main.style.transform = `translateY(${(1 - kText) * 14}px)`; main.classList.toggle("on", kText > .5);
  if (kText > .3 && !typed) { typed = true; type(); colourIn(700); }
  if (p < .5 && typed) typed = false;
  requestAnimationFrame(frame);
}
// the boot lines, the clock and the pointer readout
(function bootType() {
  let lines = [], i = 0;
  const step = () => { if (i >= BOOT.length) { boot.innerHTML = lines.join("\n"); return; } lines.push(BOOT[i] === "ready" ? "<i>ready</i>" : BOOT[i]); boot.innerHTML = lines.join("\n") + "\n<i>_</i>"; i++; setTimeout(step, still ? 0 : 240); };
  step();
})();
const clock = () => { const d = new Date(), f = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/London", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }); $("clk").textContent = f.format(d); };
clock(); setInterval(clock, 1000);
addEventListener("pointermove", e => { mx = e.clientX; my = e.clientY; if (mark) $("xy").textContent = `x ${((mx - mark.ox) / mark.s).toFixed(3)}  y ${((my - mark.oy) / mark.s).toFixed(3)}`; });
addEventListener("pointerleave", () => { mx = my = -1e9; });
addEventListener("pointerdown", e => { if (Pd < .58 && !still) rings.push({ x: e.clientX, y: e.clientY, t: (performance.now() - T0) / 1000 }); });
addEventListener("resize", layout);
// typing the two paragraphs
let typed = false, tjob = 0;
function type() {
  const me = ++tjob, ps = [$("p1"), $("p2")]; ps.forEach(p => p.innerHTML = "");
  const run = k => { if (me !== tjob || k >= ps.length) return; const p = ps[k], tmp = document.createElement("div"); tmp.innerHTML = p.dataset.html; const full = tmp.textContent; let i = 0;
    const tick = () => { if (me !== tjob) return; i = Math.min(full.length, i + (still ? full.length : 2)); const clone = tmp.cloneNode(true); let left = i;
      const walk = n => { for (const ch of [...n.childNodes]) { if (ch.nodeType === 3) { if (left <= 0) ch.remove(); else { if (ch.length > left) ch.textContent = ch.textContent.slice(0, left); left -= ch.length; } } else { walk(ch); if (!ch.textContent.length) ch.remove(); } } };
      walk(clone); p.innerHTML = clone.innerHTML + '<span class="cur"></span>';
      if (i < full.length) setTimeout(tick, 18 + Math.random() * 26); else if (k < ps.length - 1) { p.innerHTML = clone.innerHTML; setTimeout(() => run(k + 1), 360); } };
    tick(); };
  run(0);
}
// the pencil, colouring the light in once
const pc = foot.querySelector(".pencil"), px = pc.getContext("2d"), NP = pc.width;
const GP = (Q.gem.match(/-?\d+\.?\d*/g) || []).map(Number).reduce((a, v, i) => (i % 2 ? a[a.length - 1].push(v * NP / 100) : a.push([v * NP / 100]), a), []);
const tp = Math.min(...GP.map(p => p[1])), bt = Math.max(...GP.map(p => p[1]));
const span = y => { const xs = []; for (let i = 0; i < GP.length; i++) { const [a, b] = GP[i], [c2, d] = GP[(i + 1) % GP.length]; if ((b <= y) !== (d <= y)) xs.push(a + (c2 - a) * (y - b) / (d - b)); } xs.sort((p, q) => p - q); return xs.length > 1 ? [xs[0], xs[xs.length - 1]] : null; };
const line = (x0, y0, x1, y1) => { x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1); let dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1, e = dx + dy; px.fillStyle = "%SKY%";
  for (;;) { px.fillRect(x0, y0, 1, 1); if (x0 === x1 && y0 === y1) break; const e2 = 2 * e; if (e2 >= dy) { e += dy; x0 += sx; } if (e2 <= dx) { e += dx; y0 += sy; } } };
let job = 0;
function colourIn(delay) {
  if (still) return; const me = ++job; px.clearRect(0, 0, NP, NP); pc.style.transition = "none"; pc.style.opacity = 1; const S = []; let y = tp + 1, l = true;
  while (y < bt - 1) { const y2 = y + .7 + Math.random() * .9, s = span(y), s2 = span(Math.min(y2, bt - 1)); if (s && s2) S.push(l ? [s[0] - 1 + Math.random() * 1.4, y, s2[1] + 1 - Math.random() * 1.4, y2] : [s[1] + 1 - Math.random() * 1.4, y, s2[0] - 1 + Math.random() * 1.4, y2]); l = !l; y = y2; }
  let i = 0; const tick = () => { if (me !== job) return; for (let n = 0; n < 3 && i < S.length; n++, i++) line(...S[i]); if (i < S.length) setTimeout(tick, 26); else setTimeout(() => { if (me === job) { pc.style.transition = "opacity 1.4s ease"; pc.style.opacity = 0; } }, 1400); };
  setTimeout(tick, delay);
}
$("top").addEventListener("click", () => scrollTo({ top: 0, behavior: still ? "auto" : "smooth" }));
(document.fonts ? document.fonts.load('500 12px "Commit Mono"') : Promise.resolve()).catch(() => {}).finally(() => { layout(); T0 = performance.now(); requestAnimationFrame(frame); if (still) scrollTo(0, document.body.scrollHeight); });
})();
"""

for k, v in {"%PAPER%": PAPER, "%INK%": INK, "%SKY%": SKY, "%PRU%": PRU, "%GEMMASK%": GEMMASK}.items(): CSS = CSS.replace(k, v)
JS = JS.replace("%Q%", json.dumps({k: Q[k] for k in ("seam", "cav", "gem", "facet")})).replace("%WORDS%", WORDS).replace("%BOOT%", json.dumps(BOOT)).replace("%SKY%", SKY)

html = f'''<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="{INK}"><meta name="description" content="Antimony builds software for the people who make the work. Our first product is Orbe.">
<meta property="og:title" content="Antimony"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<title>Antimony</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>{CSS}</style></head>
<body>
<canvas id="c" aria-label="The Antimony mark, a stone split open with a crystal grown in the break, drawn in characters"></canvas>
<div class="hud" aria-hidden="true">
  <div class="tl"><svg class="wm" viewBox="{vb}">{WMB}</svg><div class="boot" id="boot"></div></div>
  <div class="tr"><b>london</b>  <span id="clk">00:00:00</span>\n<span class="x">51.5074 n  0.1278 w</span></div>
  <div class="bl" id="bl"><span id="st"></span><span class="bar"><s id="bs"></s></span></div>
  <div class="br" id="br"><span id="xy">x 0.000  y 0.000</span>\n<i>■</i> tap to ring the stone</div>
  <div class="hint" id="hint">Scroll</div>
</div>
<main id="m">
  <div class="prompt" aria-hidden="true"><i>&gt;</i> antimony, london</div>
  <p id="p1" data-html="<em>Antimony</em> builds software for the people who make the work. Our first product is <a href=&quot;https://eoinforker.github.io/orbe-site/&quot;>Orbe</a>, the creator&#39;s side of every sponsorship deal."></p>
  <p id="p2" data-html="We sit on their side of the table, and we mean to stay there for a long time."></p>
  <noscript><p><em>Antimony</em> builds software for the people who make the work. Our first product is <a href="https://eoinforker.github.io/orbe-site/">Orbe</a>, the creator's side of every sponsorship deal.</p><p>We sit on their side of the table, and we mean to stay there for a long time.</p></noscript>
</main>
<div class="foot" id="foot"><button id="top" aria-label="Antimony. Back to the top"><span class="win"><span class="img"></span><canvas class="pencil" width="220" height="220"></canvas>{stone}</span></button></div>
<script>{JS}</script>
</body></html>'''
open(os.path.join(HERE, "../../index.html"), "w").write(html); print(len(html))
