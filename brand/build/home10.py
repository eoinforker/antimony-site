"""Writes /home/user/antimony-site/index.html.
The opening is the mark: on black, the tile is drawn, the seam strikes through it, light breaks out in pixels, the crystal
lights and a print resolves in it. Scrolling splits the whole screen along the seam, and the two halves of black slide away
to leave paper, the brief, and the mark small above it. Then the work, in a row you scroll through. Then the imprint."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from three import break_parts, CONT
HERE = os.path.dirname(os.path.abspath(__file__))
Q = break_parts()
vb, WMB = open(os.path.join(HERE, "../../x/edge/wm.txt")).read().split("\n", 1)
INK, STONE, PAPER, SKY, PRU = "#0B0C0C", "#141311", "#EEEAE0", "#94E6FF", "#1F3F7A"
PRINT = "19006"     # Hiroshige, Satta Peak in Suruga Province, 1852

def mark(cls, i):
    """the tile with its seam and cavity cut, a solid tile over it for the moment before the strike, and its outline"""
    return f'''<svg class="{cls}" viewBox="0 0 100 100" aria-hidden="true"><defs>
<clipPath id="t{i}">{CONT["tile"]}</clipPath>
<mask id="m{i}"><rect width="100" height="100" fill="#fff"/><path d="{Q["seam"]}" fill="#000"/><path d="{Q["cav"]}" fill="#000"/></mask>
<filter id="g{i}" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="1.6" numOctaves="2" seed="3"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .06 0"/></filter>
<linearGradient id="f{i}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1E1D1B"/><stop offset=".6" stop-color="{STONE}"/><stop offset="1" stop-color="#0E0E0D"/></linearGradient></defs>
<g clip-path="url(#t{i})"><g mask="url(#m{i})"><rect width="100" height="100" fill="url(#f{i})"/><rect width="100" height="100" filter="url(#g{i})"/></g>
<rect class="solid" width="100" height="100" fill="url(#f{i})"/></g>
<rect class="line" x=".3" y=".3" width="99.4" height="99.4" rx="21.7" fill="none" stroke="{PAPER}" stroke-opacity=".5" stroke-width=".35" pathLength="1"/></svg>'''

gem = f'''<svg class="gem" viewBox="0 0 100 100" aria-hidden="true"><defs><clipPath id="gc"><path d="{Q["gem"]}"/></clipPath></defs>
<g clip-path="url(#gc)"><rect class="glow" width="100" height="100" fill="{SKY}"/>
<g class="art"><image href="assets/prints/{PRINT}.webp" x="14" y="14" width="80" height="70" preserveAspectRatio="xMidYMid slice"/></g>
<path d="{Q["facet"]}" fill="#fff" fill-opacity=".12"/></g></svg>'''

seal = f'''<svg viewBox="0 0 100 100" aria-hidden="true"><defs><clipPath id="sc">{CONT["tile"]}</clipPath><clipPath id="sg"><path d="{Q["gem"]}"/></clipPath>
<mask id="sm"><rect width="100" height="100" fill="#fff"/><path d="{Q["seam"]}" fill="#000"/><path d="{Q["cav"]}" fill="#000"/></mask></defs>
<g clip-path="url(#sc)"><rect class="sstone" width="100" height="100" fill="{STONE}" mask="url(#sm)"/>
<g class="sgem" clip-path="url(#sg)"><image href="assets/prints/{PRINT}.webp" x="14" y="14" width="80" height="70" preserveAspectRatio="xMidYMid slice"/><path d="{Q["facet"]}" fill="#fff" fill-opacity=".12"/></g></g></svg>'''

WORK = [
    dict(n="01", name="Orbe", tag="Live", tone="sky", href="https://eoinforker.github.io/orbe-site/", more="See the demo", link="https://eoinforker.github.io/orbe-site/demo/",
         line="Brands are getting agents; creators get Orbe. It negotiates every sponsorship inside the creator's rules and holds the brand's money until delivery is proven.",
         badge="assets/work/orbe.svg", art='<img src="assets/work/orbe-console.webp" alt="The Orbe console" loading="lazy">'),
    dict(n="02", name="immiscible", tag="Alpha", tone="paper", href="https://immiscible.ai", more="immiscible.ai", link="https://immiscible.ai",
         line="Rules, approvals and a signed record for what AI agents spend and do.",
         badge="assets/work/immiscible.svg", art='<div class="field dark"><img class="icon" src="assets/work/immiscible.svg" alt="The immiscible mark" loading="lazy"></div>'),
    dict(n="03", name="Idyll", tag="Soon", tone="rose", href="https://idyll.day", more="idyll.day", link="https://idyll.day",
         line="Social without the scroll.",
         badge="assets/work/idyll.svg", art='<div class="field print"><img class="icon" src="assets/work/idyll.svg" alt="The Idyll mark" loading="lazy"></div>'),
]
cards = "".join(f'''<article class="card">
  <div class="art">{w["art"]}<img class="badge" src="{w["badge"]}" alt=""></div>
  <div class="meta"><h3><a href="{w["href"]}">{w["name"]}</a></h3><span class="tag {w["tone"]}">{w["tag"]}</span></div>
  <p>{w["line"]}</p><a class="more" href="{w["link"]}">{w["more"]}</a><span class="no">{w["n"]}</span>
</article>''' for w in WORK)

CSS = r"""
@font-face { font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifVF.woff2") format("woff2"); font-weight: 200 700; font-display: swap; }
@font-face { font-family: "Timeless Serif"; src: url("assets/fonts/TimelessSerifItalicVF.woff2") format("woff2"); font-weight: 200 700; font-style: italic; font-display: swap; }
:root { --ink: %INK%; --paper: %PAPER%; --sky: %SKY%; --pru: %PRU%; --text: #26292A; --dim: #6E6B63; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html { background: var(--ink); }
body { background: var(--paper); color: var(--text); font: 400 18px/1.55 "Timeless Serif", Georgia, serif; -webkit-font-smoothing: antialiased; }
a { color: inherit; text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: .2em; text-decoration-color: color-mix(in srgb, currentColor 35%, transparent); transition: text-decoration-color .2s ease; }
a:hover { text-decoration-color: currentColor; }
:focus-visible { outline: 1px solid var(--pru); outline-offset: 4px; }
::selection { background: var(--sky); color: var(--ink); }

/* the stage: pinned while the black splits away */
.stage { height: 230vh; position: relative; }
.pin { position: sticky; top: 0; height: 100vh; height: 100svh; overflow: hidden; }
.brief { position: absolute; inset: 0; display: grid; place-content: center; padding: 0 24px; }
.brief .in { width: min(620px, 100%); }
.seal { width: 64px; height: 64px; margin-bottom: 40px; }
.seal svg { width: 100%; height: 100%; display: block; }
.brief p { font-size: clamp(19px, 1.6vw, 22px); line-height: 1.5; text-wrap: pretty; }
.brief p + p { margin-top: 1em; } .brief em { font-style: italic; }
.half { position: absolute; inset: 0; background: var(--ink); will-change: transform; }
.big { position: absolute; display: block; }
.big .solid { opacity: 1; } .big .line { stroke-dasharray: 1; stroke-dashoffset: 1; }
.gem { position: absolute; display: block; will-change: transform; visibility: hidden; }
.gem .glow { opacity: 0; } .gem .art { opacity: 0; }
.flash { position: absolute; height: 2px; background: var(--sky); box-shadow: 0 0 18px 2px rgba(148,230,255,.6); opacity: 0; transform-origin: 50% 50%; pointer-events: none; }
#px { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; image-rendering: pixelated; }
.wm { position: absolute; left: max(32px, env(safe-area-inset-left, 0px)); top: max(30px, env(safe-area-inset-top, 0px)); height: 20px; width: auto; color: var(--paper); --lit: var(--sky); opacity: 0; transition: opacity .8s ease, color .3s ease; z-index: 5; }
.wm.on { opacity: 1; } .wm.dark { color: var(--text); --lit: var(--pru); }

/* the work: a row of plates that the scroll carries sideways */
.work { position: relative; }
.work .pin2 { position: sticky; top: 0; height: 100vh; height: 100svh; overflow: hidden; display: grid; grid-template-rows: auto 1fr; padding-top: 12vh; }
.work header { padding: 0 max(32px, 6vw); display: flex; justify-content: space-between; align-items: end; gap: 24px; }
.work h2 { font-weight: 400; font-size: clamp(44px, 6vw, 92px); line-height: .95; letter-spacing: -.03em; }
.work header p { max-width: 21em; color: var(--dim); font-size: 16px; }
.track { display: flex; gap: 22px; padding: 6vh max(32px, 6vw) 0; will-change: transform; align-items: start; }
.card { flex: none; width: min(560px, 82vw); position: relative; border: 1px solid rgba(38,41,42,.14); background: #F6F3EB; }
.card .art { position: relative; aspect-ratio: 16 / 10; overflow: hidden; border-bottom: 1px solid rgba(38,41,42,.14); }
.card .art > img:not(.badge) { width: 100%; height: 100%; object-fit: cover; object-position: 0 0; display: block; transition: transform 1.2s cubic-bezier(.2,.7,.2,1); }
.card:hover .art > img:not(.badge), .card:hover .icon { transform: scale(1.025); }
.field { position: absolute; inset: 0; display: grid; place-items: center; }
.field.dark { background: #0B0D15; } .field.print { background: url(assets/prints/81248.webp) 60% 40% / cover; }
.icon { width: 30%; height: auto; display: block; border-radius: 22%; transition: transform 1.2s cubic-bezier(.2,.7,.2,1); }
.badge { position: absolute; left: 14px; top: 14px; width: 30px; height: 30px; border-radius: 7px; box-shadow: 0 0 0 3px #F6F3EB; }
.card .meta { display: flex; justify-content: space-between; align-items: baseline; gap: 16px; padding: 22px 24px 0; }
.card h3 { font-weight: 400; font-size: 40px; line-height: 1; letter-spacing: -.02em; }
.card h3 a { text-decoration: none; }
.tag { font-size: 14px; padding: 3px 10px; border-radius: 3px; white-space: nowrap; }
.tag.sky { background: #CFF1FC; color: #134E66; } .tag.paper { background: #E7E2D6; color: #4A463E; } .tag.rose { background: #F7DCE6; color: #7A2348; }
.card p { padding: 14px 24px 0; font-size: 16.5px; line-height: 1.5; color: #45464A; max-width: 30em; min-height: 5.6em; }
.card .more { display: inline-block; margin: 14px 24px 22px; font-size: 15px; }
.card .no { position: absolute; right: 18px; top: 14px; font-size: 13px; color: rgba(255,255,255,.8); mix-blend-mode: difference; }
/* the row ends with a hairline of dots, the way an unfinished line is drawn */
.track .end { flex: none; width: min(380px, 70vw); align-self: stretch; border: 1px dashed rgba(38,41,42,.28); display: grid; place-items: center; color: var(--dim); font-size: 16px; text-align: center; padding: 24px; min-height: 360px; }

/* the imprint */
footer { background: var(--ink); color: rgba(238,234,224,.62); position: relative; padding: 120px max(32px, 6vw) max(40px, env(safe-area-inset-bottom, 0px)); font-size: 15px; }
footer .edge { position: absolute; left: 0; right: 0; top: -23px; height: 24px; display: block; width: 100%; }
footer .row { display: grid; grid-template-columns: 1.4fr 1fr 1fr 1fr; gap: 32px; align-items: start; }
footer svg.fwm { height: 26px; width: auto; color: var(--paper); --lit: var(--sky); display: block; margin-bottom: 18px; }
footer h4 { font-weight: 400; font-size: 13px; color: rgba(238,234,224,.38); margin-bottom: 10px; }
footer ul { list-style: none; display: grid; gap: 6px; }
footer .base { margin-top: 90px; padding-top: 22px; border-top: 1px solid rgba(238,234,224,.12); display: flex; justify-content: space-between; gap: 24px; font-size: 13px; color: rgba(238,234,224,.38); flex-wrap: wrap; }
@media (max-width: 760px) {
  .work header { flex-direction: column; align-items: start; } .work .pin2 { padding-top: 9vh; }
  footer .row { grid-template-columns: 1fr 1fr; } footer .row > :first-child { grid-column: 1 / -1; }
  .seal { width: 56px; height: 56px; margin-bottom: 30px; }
}
@media (prefers-reduced-motion: reduce) { .card .art > img:not(.badge), .icon { transition: none; } }
"""
for k, v in {"%INK%": INK, "%PAPER%": PAPER, "%SKY%": SKY, "%PRU%": PRU}.items(): CSS = CSS.replace(k, v)

JS = r"""
(() => { "use strict";
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const pin = $(".pin"), L = $(".half.l"), R = $(".half.r"), gem = $(".gem"), flash = $(".flash"), wm = $(".wm"), brief = $(".brief .in"), sealEl = $(".seal");
const bigs = $$(".big"), sstone = $(".sstone"), sgem = $(".sgem"), cvs = $("#px"), cx = cvs.getContext("2d");
const S16 = Math.sin(16 * Math.PI / 180), C16 = Math.cos(16 * Math.PI / 180), D = [S16, -C16], N = [C16, S16];
const cl = v => Math.max(0, Math.min(1, v)), seg = (t, a, b) => cl((t - a) / (b - a)), eo = t => 1 - Math.pow(1 - t, 3), eio = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
let W, H, M, box;     // M: the mark's centre on screen (the seam's centre), box: the big mark
function layout() {
  W = innerWidth; H = innerHeight; const s = Math.min(H * .5, W * .66); box = { x: W / 2 - s / 2, y: H * .48 - s / 2, s };
  M = [box.x + .5 * s, box.y + .515 * s];
  for (const b of bigs) Object.assign(b.style, { left: box.x + "px", top: box.y + "px", width: s + "px", height: s + "px" });
  // each half of the black is everything on one side of the seam, carried through the whole screen
  const far = Math.hypot(W, H) * 2, a = [M[0] - D[0] * far, M[1] - D[1] * far], b = [M[0] + D[0] * far, M[1] + D[1] * far];
  const o = sg => [-sg * N[0] * .8, -sg * N[1] * .8], poly = sg => [a, b, [b[0] + sg * N[0] * far, b[1] + sg * N[1] * far], [a[0] + sg * N[0] * far, a[1] + sg * N[1] * far]].map(p => `${(p[0] + o(sg)[0]).toFixed(1)}px ${(p[1] + o(sg)[1]).toFixed(1)}px`).join(",");
  L.style.clipPath = `polygon(${poly(-1)})`; R.style.clipPath = `polygon(${poly(1)})`;
  const len = Math.hypot(W, H) * 1.2; Object.assign(flash.style, { width: len + "px", left: M[0] - len / 2 + "px", top: M[1] - 1 + "px", transform: `rotate(${-74}deg)` });
  const d = Math.min(2, devicePixelRatio || 1); cvs.width = Math.round(W / 3); cvs.height = Math.round(H / 3); cvs.style.width = W + "px"; cvs.style.height = H + "px";
}
// light breaking out of the crack, in pixels
const bits = [];
function burst(n, spread) { for (let i = 0; i < n; i++) { const along = (Math.random() - .5) * spread, side = Math.random() < .5 ? -1 : 1;
  const x = M[0] + D[0] * along, y = M[1] + D[1] * along, v = 40 + Math.random() * 260;
  bits.push({ x, y, vx: side * N[0] * v + (Math.random() - .5) * 40, vy: side * N[1] * v + (Math.random() - .5) * 40, life: .5 + Math.random() * 1.1, age: 0, sz: Math.random() < .2 ? 2 : 1, c: Math.random() < .78 ? "#94E6FF" : "#EEEAE0" }); } }
let t0 = performance.now(), last = t0, struck = false, P = 0;
function intro(t) {
  const line = eo(seg(t, .05, .6)), fill = eo(seg(t, .45, .75)), strike = t >= .78;
  for (const b of bigs) { b.querySelector(".line").style.strokeDashoffset = 1 - line; b.querySelector(".line").style.opacity = 1 - seg(t, .8, 1.3);
    b.querySelector(".solid").style.opacity = strike ? 0 : 1; b.style.opacity = .25 + .75 * fill; }
  if (strike && !struck) { struck = true; gem.style.visibility = "visible"; if (!still) burst(260, box.s * 1.1); }
  flash.style.opacity = t < .78 ? 0 : 1 - eo(seg(t, .78, 1.25));
  // the halves are knocked apart by the strike and settle back
  const knock = t < .78 ? 0 : Math.sin(seg(t, .78, 1.4) * Math.PI) * (1 - seg(t, .78, 1.4)) * 7;
  gem.querySelector(".glow").style.opacity = seg(t, .8, .9) * (1 - seg(t, 1.25, 2.0) * .85);
  gem.querySelector(".art").style.opacity = eo(seg(t, 1.1, 2.0));
  if (t > 1.4) wm.classList.add("on");
  return knock;
}
function frame(now) {
  const t = still ? 9 : (now - t0) / 1000, dt = Math.min(.05, (now - last) / 1000); last = now;
  const knock = intro(t);
  // the split, tied straight to the scroll
  const st = $(".stage"), range = st.offsetHeight - H; P = cl(scrollY / (range * .82));
  const k = eio(P), gap = k * Math.hypot(W, H) * .62 + knock, sl = k * H * .25;
  L.style.transform = `translate(${(-N[0] * gap - D[0] * sl).toFixed(2)}px, ${(-N[1] * gap - D[1] * sl).toFixed(2)}px)`;
  R.style.transform = `translate(${(N[0] * gap + D[0] * sl).toFixed(2)}px, ${(N[1] * gap + D[1] * sl).toFixed(2)}px)`;
  // the crystal leaves the stone and becomes the seal above the brief
  const r = sealEl.getBoundingClientRect(), pr = pin.getBoundingClientRect(), g = eio(seg(P, .15, .95));
  const gs = box.s + (r.width - box.s) * g, gx = box.x + (r.left - pr.left - box.x) * g, gy = box.y + (r.top - pr.top - box.y) * g;
  Object.assign(gem.style, { left: gx + "px", top: gy + "px", width: gs + "px", height: gs + "px", opacity: P > .97 ? 0 : 1 });
  sgem.style.opacity = P > .97 ? 1 : 0; sstone.style.opacity = eo(seg(P, .7, .97));
  brief.style.opacity = eo(seg(P, .4, .85)); brief.style.transform = `translateY(${(1 - eo(seg(P, .4, .85))) * 12}px)`;
  wm.classList.toggle("dark", P > .55);
  // pixels
  cx.clearRect(0, 0, cvs.width, cvs.height);
  for (let i = bits.length - 1; i >= 0; i--) { const b = bits[i]; b.age += dt; if (b.age > b.life) { bits.splice(i, 1); continue; }
    b.vx *= .965; b.vy = b.vy * .965 + 30 * dt; b.x += b.vx * dt; b.y += b.vy * dt;
    cx.globalAlpha = (1 - b.age / b.life) * (1 - P); cx.fillStyle = b.c; cx.fillRect(Math.round(b.x / 3), Math.round(b.y / 3), b.sz, b.sz); }
  cx.globalAlpha = 1;
  work();
  requestAnimationFrame(frame);
}
// hovering the crack lets a little light out
addEventListener("pointermove", e => { if (still || P > .05 || !struck) return; const q = [e.clientX - M[0], e.clientY - M[1]];
  if (Math.abs(q[0] * N[0] + q[1] * N[1]) < 16 && Math.random() < .5) { const along = q[0] * D[0] + q[1] * D[1]; const n0 = bits.length; burst(2, 0);
    for (let i = n0; i < bits.length; i++) { bits[i].x = M[0] + D[0] * along; bits[i].y = M[1] + D[1] * along; bits[i].life *= .6; } } }, { passive: true });
// the work: vertical scroll carried sideways
const ws = $(".work"), tr = $(".track");
function sizeWork() { const extra = Math.max(0, tr.scrollWidth - innerWidth); ws.style.height = (innerHeight + extra * 1.1) + "px"; }
function work() { const r = ws.getBoundingClientRect(), extra = Math.max(0, tr.scrollWidth - innerWidth), p = cl(-r.top / Math.max(1, ws.offsetHeight - innerHeight));
  tr.style.transform = `translateX(${(-extra * p).toFixed(1)}px)`; }
addEventListener("resize", () => { layout(); sizeWork(); });
layout(); sizeWork(); requestAnimationFrame(frame);
})();
"""

edge = "".join(f'<rect x="{x}" y="{y}" width="{w}" height="{w}" fill="{INK}"/>' for x, y, w in
               [(0, 12, 12), (12, 18, 6), (30, 12, 6), (48, 6, 6), (60, 18, 6), (84, 12, 6), (102, 18, 6), (1830, 12, 6), (1848, 6, 6), (1866, 18, 6), (1878, 12, 12), (1896, 0, 24)])
html = f'''<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="{INK}"><meta name="description" content="Antimony builds software for the people who make the work. Our first product is Orbe.">
<meta property="og:title" content="Antimony"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<title>Antimony</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>{CSS}</style></head>
<body>
<section class="stage" aria-label="Antimony">
  <div class="pin">
    <div class="brief"><div class="in"><div class="seal">{seal}</div>
      <p><em>Antimony</em> builds software for the people who make the work. Our first product is <a href="https://eoinforker.github.io/orbe-site/">Orbe</a>, the creator&#39;s side of every sponsorship deal.</p>
      <p>We sit on their side of the table, and we mean to stay there for a long time.</p></div></div>
    <div class="half l">{mark("big", "l")}</div>
    <div class="half r">{mark("big", "r")}</div>
    <div class="flash"></div>
    {gem}
    <canvas id="px" aria-hidden="true"></canvas>
    <svg class="wm" viewBox="{vb}" role="img" aria-label="Antimony">{WMB}</svg>
  </div>
</section>
<section class="work" aria-labelledby="wk">
  <div class="pin2">
    <header><h2 id="wk">The work</h2><p>What we have made, and what we are making.</p></header>
    <div class="track">{cards}<div class="end">More, slowly.</div></div>
  </div>
</section>
<footer>
  <svg class="edge" viewBox="0 0 1920 24" preserveAspectRatio="none" aria-hidden="true">{edge}</svg>
  <div class="row">
    <div><svg class="fwm" viewBox="{vb}" role="img" aria-label="Antimony">{WMB}</svg><p>Software for the people who make the work.<br>London.</p></div>
    <div><h4>Work</h4><ul><li><a href="https://eoinforker.github.io/orbe-site/">Orbe</a></li><li><a href="https://immiscible.ai">immiscible</a></li><li><a href="https://idyll.day">Idyll</a></li></ul></div>
    <div><h4>Elsewhere</h4><ul><li><a href="https://github.com/eoinforker">GitHub</a></li></ul></div>
    <div><h4>Prints</h4><ul><li>Utagawa Hiroshige, <i>Satta Peak in Suruga Province</i>, 1852</li><li>Katsushika Hokusai, <i>Mount Fuji with Cherry Trees in Bloom</i>, about 1801 to 1805</li><li>Art Institute of Chicago, CC0</li></ul></div>
  </div>
  <div class="base"><span>Imprint: Antimony, London.</span><span>Set in Timeless Serif.</span></div>
</footer>
<script>{JS}</script>
</body></html>'''
open(os.path.join(HERE, "../../index.html"), "w").write(html); print(len(html))
