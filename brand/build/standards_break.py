"""Writes ../standards/: the Antimony standards on the Break, one page per chapter. Every measure is read from three.py, the
same geometry the kit and the website are drawn from."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from three import brk, break_parts, CONT, B
Q = break_parts(); QS = break_parts(small=True)
OUT = os.path.join(HERE, "../standards/")
VB, WMB = open(os.path.join(HERE, "../../x/edge/wm.txt")).read().split("\n", 1)
# the prints' records, with their dashes written out as the house style asks
_clean = lambda v: v.replace("\u2014", ", ").replace("\u2013", " to ") if isinstance(v, str) else v
SRC = {str(s["id"]): {k: _clean(v) for k, v in s.items()} for s in json.load(open(os.path.join(HERE, "../nurture/prints/sources.json")))}
INK, STONE, PAPER, SKY, PRU, COB = "#0B0C0C", "#141311", "#EEEAE0", "#94E6FF", "#1F3F7A", "#2448FF"
CH = [("index", "Introduction"), ("logo", "Logo"), ("type", "Typography"), ("colour", "Colour"), ("art", "Art direction"),
      ("motion", "Motion"), ("voice", "Voice"), ("use", "Brand in use"), ("downloads", "Downloads")]

def wm(fill=INK, lit=None, style="height:22px;width:auto"):
    lit = lit or (PRU if fill in (INK, STONE) else SKY)
    return f'<svg viewBox="{VB}" style="color:{fill};--lit:{lit};{style}" role="img" aria-label="Antimony">{WMB}</svg>'
def lock(stone=STONE, ground=PAPER, txt=INK, h=64):
    return (f'<span style="display:inline-flex;align-items:center;gap:{h * .28:.0f}px">{brk(stone=stone, ground=ground, style=f"width:{h}px;height:{h}px;display:block;flex:none")}'
            f'{wm(txt, style=f"height:{h * .54:.0f}px;width:auto;display:block")}</span>')
def mk(stone=STONE, ground=PAPER, **k): return brk(stone=stone, ground=ground, style="width:100%;height:100%;display:block", **k)

CSS = r"""
@font-face { font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }
@font-face { font-family: "Timeless Serif"; src: url(fonts/TimelessSerifItalicVF.woff2) format("woff2"); font-weight: 200 700; font-style: italic; font-display: swap; }
@font-face { font-family: "Commit Mono"; src: url(fonts/CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }
/* The same two grounds as the website: ink for the terminal and the mark, paper for the rules. Two faces. One light. */
:root { --ink: %INK%; --paper: %PAPER%; --sky: %SKY%; --pru: %PRU%; --rule: rgba(11,12,12,.13); --dim: #66645D; --card: #F6F3EB;
  --serif: "Timeless Serif", "Iowan Old Style", Georgia, serif; --mono: "Commit Mono", ui-monospace, Menlo, monospace; color-scheme: light; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: var(--paper); color: #1B1D1D; }
body { font: 400 18px/1.55 var(--serif); -webkit-font-smoothing: antialiased; }
a { color: inherit; text-decoration-thickness: 1px; text-underline-offset: .18em; }
:focus-visible { outline: 1px solid var(--pru); outline-offset: 3px; }
::selection { background: var(--sky); color: var(--ink); }
body::before { content: ""; position: fixed; inset: 0 0 auto; height: env(safe-area-inset-top, 0px); z-index: 10; background: var(--ink); }
.top { position: sticky; top: env(safe-area-inset-top, 0px); z-index: 9; background: var(--ink); color: #E7E2D6;
  padding: 13px max(18px, env(safe-area-inset-right, 0px)) 13px max(18px, env(safe-area-inset-left, 0px)); display: flex; gap: 24px; align-items: center; font: 400 12px var(--mono); letter-spacing: .04em; }
.top .home { display: flex; align-items: center; gap: 14px; text-decoration: none; flex: none; }
.top .home span { color: #8C918E; }
.top nav { display: flex; gap: 18px; overflow-x: auto; scrollbar-width: none; min-width: 0; margin-left: auto; }
.top nav a { text-decoration: none; color: #8C918E; white-space: nowrap; padding-block: 4px; }
.top nav a i { font-style: normal; color: #4A4F4D; margin-right: 6px; }
.top nav a:hover { color: #E7E2D6; } .top nav a[aria-current] { color: #E7E2D6; } .top nav a[aria-current] i { color: var(--sky); }
.band { padding: 80px max(18px, env(safe-area-inset-right, 0px)) 80px max(18px, env(safe-area-inset-left, 0px)); border-bottom: 1px solid var(--rule); }
.band.ink { background: var(--ink); color: #E7E2D6; --rule: rgba(231,226,214,.13); --dim: #8C918E; --card: #121414; }
.in { max-width: 1160px; margin-inline: auto; display: grid; gap: 28px; }
.eb { font: 400 12px/1 var(--mono); letter-spacing: .04em; color: var(--dim); }
.eb i { font-style: normal; color: var(--pru); margin-right: 8px; } .ink .eb i { color: var(--sky); }
.hero { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 420px); gap: 48px; align-items: center; }
.chapter { font: 400 clamp(60px, 10vw, 148px)/.9 var(--serif); letter-spacing: -.035em; }
h2 { font: 400 clamp(28px, 3.4vw, 42px)/1.06 var(--serif); letter-spacing: -.014em; text-wrap: balance; max-width: 20em; }
h3 { font: 400 22px/1.2 var(--serif); }
p { max-width: 36em; text-wrap: pretty; } .dim { color: var(--dim); }
.lede { font: 400 clamp(20px, 2.1vw, 25px)/1.42 var(--serif); max-width: 32em; }
.toc { display: flex; gap: 8px 22px; flex-wrap: wrap; font: 400 12.5px var(--mono); }
.toc a { text-decoration: none; color: var(--dim); } .toc a:hover { color: #E7E2D6; }
.glyphs { width: 100%; aspect-ratio: 1; display: block; cursor: crosshair; }
.sec { display: grid; grid-template-columns: minmax(0, 14em) minmax(0, 1fr); gap: 40px; align-items: start; }
.sec > .head { display: grid; gap: 10px; position: sticky; top: 80px; }
.sec > .body { display: grid; gap: 22px; min-width: 0; }
.two { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 20px; align-items: start; }
.three { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; align-items: start; }
.four { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; align-items: start; }
figure { display: grid; gap: 10px; min-width: 0; } figcaption { font-size: 15px; line-height: 1.45; color: var(--dim); }
figcaption b { display: block; color: #1B1D1D; font: 400 12px/1.4 var(--mono); letter-spacing: .03em; margin-bottom: 3px; }
.ink figcaption b { color: #E7E2D6; }
.tile { aspect-ratio: 1; max-width: 100%; display: grid; place-items: center; padding: 22%; background: var(--card); border: 1px solid var(--rule); }
.tile > svg, .tile > img { width: 100%; height: 100%; display: block; object-fit: contain; }
.tile.wide { aspect-ratio: 2.4; padding: 0 8%; } .tile.ink { background: var(--ink); border-color: var(--ink); } .tile.cob { background: %COB%; border-color: %COB%; }
.tile.sky { background: var(--sky); border-color: var(--sky); } .tile.pru { background: var(--pru); border-color: var(--pru); }
.shot { width: 100%; height: auto; display: block; border: 1px solid var(--rule); max-width: 100%; }
.nums { display: grid; }
.nums div { display: grid; grid-template-columns: 7em minmax(0, 1fr); gap: 16px; border-top: 1px solid var(--rule); padding: 13px 0; }
.nums b { font: 400 13.5px/1.6 var(--mono); color: var(--pru); } .ink .nums b { color: var(--sky); }
.nums strong { display: block; font-weight: 400; font-size: 19px; }
.cons { width: 100%; height: auto; display: block; background: var(--card); border: 1px solid var(--rule); font: 400 3px var(--mono); }
.dont .tile { position: relative; }
.dont .tile::after { content: ""; position: absolute; inset: 10px; background: linear-gradient(to top right, transparent calc(50% - .6px), #C8472F calc(50% - .6px), #C8472F calc(50% + .6px), transparent calc(50% + .6px)); opacity: .75; pointer-events: none; }
table { width: 100%; border-collapse: collapse; font-size: 15.5px; }
th, td { text-align: left; padding: 11px 12px; border-bottom: 1px solid var(--rule); vertical-align: top; }
thead th { font: 400 12px var(--mono); letter-spacing: .04em; color: var(--dim); }
td.num, th.num { font: 400 13.5px var(--mono); font-variant-numeric: tabular-nums; }
.scroll { overflow-x: auto; }
.sw { display: grid; gap: 3px; padding: 14px; min-height: 170px; align-content: end; border: 1px solid var(--rule); }
.sw b { font: 400 26px/1.1 var(--serif); } .sw span { font: 400 12px/1.5 var(--mono); opacity: .85; }
.prop { display: flex; height: 56px; border: 1px solid var(--rule); }
.contents { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 40px; }
.contents a { display: grid; grid-template-columns: 3em minmax(0, 1fr) auto; gap: 12px; align-items: baseline; padding: 16px 0; border-top: 1px solid var(--rule); text-decoration: none; }
.contents a span { font: 400 12.5px var(--mono); color: var(--dim); } .contents a b { font: 400 28px/1.1 var(--serif); font-weight: 400; } .contents a i { font-style: normal; color: var(--dim); }
.contents a:hover b { color: var(--pru); }
.pn { display: flex; justify-content: space-between; gap: 20px; flex-wrap: wrap; }
.pn a { font: 400 clamp(26px, 3vw, 40px)/1.1 var(--serif); text-decoration: none; } .pn a:hover { color: var(--sky); }
.spec { font-size: clamp(22px, 3vw, 34px); line-height: 1.3; word-break: break-word; }
.do { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); border: 1px solid var(--rule); }
.do div { padding: 16px 18px; display: grid; gap: 6px; } .do div + div { border-left: 1px solid var(--rule); }
.do .k { font: 400 12px var(--mono); color: var(--dim); } .do .yes .k { color: var(--pru); }
.files { display: grid; } .files div { display: grid; grid-template-columns: 10em minmax(0, 1fr); gap: 16px; border-top: 1px solid var(--rule); padding: 13px 0; }
.files code { font: 400 14px var(--mono); }
.profile { background: #fff; border: 1px solid var(--rule); border-radius: 10px; overflow: hidden; color: #191919; font-family: Arial, sans-serif; }
.profile .ban { width: 100%; display: block; aspect-ratio: 1128 / 191; object-fit: cover; }
.profile .pb { padding: 0 20px 20px; } .profile .av { width: 96px; height: 96px; margin-top: -48px; border: 4px solid #fff; border-radius: 50%; display: block; background: #fff; }
.profile b { display: block; font: 700 22px/1.2 Arial, sans-serif; margin-top: 10px; } .profile span { color: #555; font-size: 15px; }
.tab { display: inline-flex; align-items: center; gap: 8px; background: #fff; border: 1px solid var(--rule); border-bottom: 0; border-radius: 8px 8px 0 0; padding: 9px 16px; font: 13px Arial, sans-serif; color: #333; }
.tab img { image-rendering: pixelated; display: block; }
.sig { background: #fff; border: 1px solid var(--rule); padding: 22px; font: 400 14px/1.5 Arial, sans-serif; color: #222; }
.px { image-rendering: pixelated; width: 100%; height: auto; display: block; border: 1px solid var(--rule); }
video { width: 100%; height: auto; display: block; max-width: 100%; }
.split { display: block; width: 100%; height: auto; cursor: ew-resize; touch-action: pan-y; }
@media (prefers-reduced-motion: reduce) { video { display: none; } }
@media (max-width: 900px) { .sec, .hero { grid-template-columns: 1fr; gap: 22px; } .sec > .head { position: static; } .three, .four { grid-template-columns: 1fr 1fr; } .contents { grid-template-columns: 1fr; } .band { padding-block: 56px; } .hero .glyphs { max-width: 360px; } }
@media (max-width: 560px) { .two { grid-template-columns: 1fr; } .top .home span { display: none; } .do { grid-template-columns: 1fr; } .do div + div { border-left: 0; border-top: 1px solid var(--rule); } .nums div { grid-template-columns: 1fr; gap: 2px; } }
"""
for k, v in {"%INK%": INK, "%PAPER%": PAPER, "%SKY%": SKY, "%PRU%": PRU, "%COB%": COB}.items(): CSS = CSS.replace(k, v)

# the mark in characters, on every chapter head: the same drawing as the website's opening, smaller, and the pointer scrambles it
GLYPHS_JS = r"""<script>
(() => { "use strict";
const Q = %Q%, WORDS = "ANTIMONY SOFTWARE FOR THE PEOPLE WHO MAKE THE WORK ORBE THE BRIEF THE CONTRACT PAID ON TIME STIBIUM 51 SB ";
const GL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/<>[]{}=+*#%&$:", RAMP = " .·:;-=+*x#%@", still = matchMedia("(prefers-reduced-motion: reduce)").matches;
const R = 240, K = R / 100;
const bm = f => { const o = document.createElement("canvas"); o.width = o.height = R; const g = o.getContext("2d"); g.scale(K, K); g.fillStyle = "#fff"; f(g); const d = g.getImageData(0, 0, R, R).data, a = new Uint8Array(R * R); for (let i = 0; i < a.length; i++) a[i] = d[i * 4 + 3] > 127; return a; };
const tile = new Path2D(); tile.roundRect ? tile.roundRect(0, 0, 100, 100, 22) : tile.rect(0, 0, 100, 100);
const ST = bm(g => { g.fill(tile); g.globalCompositeOperation = "destination-out"; g.fill(new Path2D(Q.seam)); g.fill(new Path2D(Q.cav)); }), GM = bm(g => g.fill(new Path2D(Q.gem))), FC = bm(g => g.fill(new Path2D(Q.facet)));
const at = (A, u, v) => u >= 0 && v >= 0 && u < 100 && v < 100 ? A[((v * K) | 0) * R + ((u * K) | 0)] : 0;
const h = (i, j) => { const s = Math.sin(i * 127.1 + j * 311.7) * 43758.5453; return s - Math.floor(s); };
document.querySelectorAll("canvas.glyphs").forEach(c => {
  const x = c.getContext("2d"); let W, fs, cw, ch, cells, mx = -1e9, my = -1e9, t0 = performance.now(), live = 0;
  const size = () => { const d = Math.min(2, devicePixelRatio || 1); W = c.getBoundingClientRect().width; c.width = c.height = W * d; x.setTransform(d, 0, 0, d, 0, 0);
    fs = Math.max(7, W / 46); cw = fs * .6; ch = fs * 1.18; x.font = `500 ${fs}px "Commit Mono", monospace`; x.textAlign = "center"; x.textBaseline = "middle"; cells = []; let w = 0;
    for (let j = 0; j < Math.floor(W / ch); j++) for (let i = 0; i < Math.floor(W / cw); i++) { const X = (i + .5) * cw, Y = (j + .5) * ch, u = X / W * 100, v = Y / W * 100;
      const g = at(GM, u, v), s = at(ST, u, v); if (!g && !s) continue; const e = s && (!at(ST, u + 1.6, v) || !at(ST, u - 1.6, v) || !at(ST, u, v + 2.6) || !at(ST, u, v - 2.6));
      const L = .1 + h(i * .2, j * .2) * .35 + (1 - (u + v) / 200) * .18; cells.push({ X, Y, g, f: at(FC, u, v), e, L, n: h(i, j) * 99, d: Math.hypot(u - 50, v - 50) / 70 + h(j, i) * .4, c: WORDS[w++ % WORDS.length] }); } };
  const draw = now => { const t = still ? 9 : (now - t0) / 1000; x.clearRect(0, 0, W, W); let busy = t < 1.6;
    for (const p of cells) { const a = t - p.d; if (a < 0) continue; const near = Math.hypot(p.X - mx, p.Y - my) < W * .12; let chr, col;
      if (p.g) { chr = p.c === " " ? "·" : p.c; col = p.f ? "#CFF4FF" : "#94E6FF"; } else if (p.e) { chr = "#"; col = "#D6D1C5"; } else { chr = RAMP[1 + (p.L * 11) | 0]; col = `rgba(214,209,197,${.25 + p.L})`; }
      if (a < .4 || (near && Math.sin(t * 20 + p.n) > -.2)) { chr = GL[((t * 30 + p.n * 7) | 0) % GL.length]; col = "#94E6FF"; busy = true; }
      x.fillStyle = col; x.fillText(chr, p.X, p.Y); }
    if (busy || live) requestAnimationFrame(draw); else running = false; };
  let running = false; const go = () => { if (!running) { running = true; requestAnimationFrame(draw); } };
  c.addEventListener("pointermove", e => { const r = c.getBoundingClientRect(); mx = e.clientX - r.left; my = e.clientY - r.top; live = 1; go(); });
  c.addEventListener("pointerleave", () => { mx = my = -1e9; live = 0; go(); });
  new ResizeObserver(() => { size(); go(); }).observe(c);
  (document.fonts ? document.fonts.ready : Promise.resolve()).then(() => { size(); t0 = performance.now(); go(); });
});
})();
</script>""".replace("%Q%", json.dumps({k: Q[k] for k in ("seam", "cav", "gem", "facet")}))

HEAD = '<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><link rel="icon" href="img/b-favicon.svg" type="image/svg+xml">'
def nav(slug):
    links = "".join(f'<a href="{s}.html"{" aria-current=\"page\"" if s == slug else ""}><i>{i:02d}</i>{t.lower()}</a>' for i, (s, t) in enumerate(CH))
    return f'<header class="top"><a class="home" href="index.html">{wm("#E7E2D6", SKY, "height:21px;width:auto;display:block")}<span>standards</span></a><nav aria-label="Chapters">{links}</nav></header>'
def prevnext(slug):
    i = [s for s, _ in CH].index(slug); p = CH[i - 1] if i > 0 else None; n = CH[i + 1] if i < len(CH) - 1 else None
    a = f'<a href="{p[0]}.html">&larr; {p[1]}</a>' if p else "<span></span>"; b = f'<a href="{n[0]}.html">{n[1]} &rarr;</a>' if n else ""
    return f'<section class="band ink"><div class="in pn">{a}{b}</div></section>'
def chapter_head(slug, n, lede, sections):
    toc = "".join(f'<a href="#{a}">{b.lower()}</a>' for a, b in sections)
    return (f'<section class="band ink"><div class="in hero"><div style="display:grid;gap:26px"><span class="eb"><i>{n:02d}</i>chapter</span><h1 class="chapter">{dict(CH)[slug]}</h1>'
            f'<p class="lede">{lede}</p><nav class="toc" aria-label="In this chapter">{toc}</nav></div><canvas class="glyphs" aria-hidden="true"></canvas></div></section>')
def sec(id_, title, intro, body, ink=False, n=None):
    return (f'<section class="band{" ink" if ink else ""}" id="{id_}"><div class="in sec"><div class="head"><span class="eb">{f"<i>{n}</i>" if n else ""}{title.lower()}</span></div>'
            f'<div class="body">{intro}{body}</div></div></section>')
def write(slug, title, body, scripts=""):
    html = (f'<!doctype html><html lang="en-GB"><head>{HEAD}<title>{title}</title><meta name="claude:viewport-fit-sides" content="cover"><style>{CSS}</style></head><body>'
            + nav(slug) + body + prevnext(slug) + GLYPHS_JS + scripts + "</body></html>")
    open(OUT + f"{slug}.html", "w").write(html); return len(html)

# ---------- 00 Introduction ----------
PRINCIPLES = [("Grown, not drawn", "The mark is a stone that split and a crystal that grew in the break. We make things the same way: slowly, from what is already there."),
              ("One light", "Sky is the only bright colour. It is the crystal, a cursor, a link. If two things are lit, neither is."),
              ("Quiet and exact", "Say less, and make every number true. A measure that cannot be explained is not finished."),
              ("On their side", "Everything we make is for the people who make the work. It should feel like it was made by one of them."),
              ("Built to last", "Choose what will still look right in fifty years: a serif, paper, ink, plain words, an old print.")]
intro = (f'<section class="band ink"><div class="in hero"><div style="display:grid;gap:26px"><span class="eb"><i>00</i>antimony standards</span><h1 class="chapter">Standards.</h1>'
         f'<p class="lede">How Antimony looks, sounds and moves, and why. Written so that anyone who builds with it, now or in fifty years, can make something we would recognise as ours.</p></div>'
         f'<canvas class="glyphs" aria-hidden="true"></canvas></div></section>'
         + sec("note", "A note", '<p class="lede">Antimony is element 51. Its ore, stibnite, grows in long grey crystals, and for centuries it was used to refine gold: it took up what was not gold and left the gold behind.</p>'
               '<p>Our mark is a stone split open, with a crystal grown in the break. This is a standard, not a template. Learn the reasons and you can make anything; copy the examples and you will make the same thing twice. Where these pages give a number, use it. Where they give a reason, use your judgement.</p>', "")
         + sec("principles", "Five principles", "", '<div class="nums">' + "".join(f'<div><b>{i + 1:02d}</b><span><strong>{a}</strong>{b}</span></div>' for i, (a, b) in enumerate(PRINCIPLES)) + '</div>')
         + f'<section class="band"><div class="in"><span class="eb">contents</span><div class="contents">'
         + "".join(f'<a href="{s}.html"><span>{i:02d}</span><b>{t}</b><i>&rarr;</i></a>' for i, (s, t) in enumerate(CH) if s != "index") + '</div></div></section>')
sizes = {"index": write("index", "Antimony Standards", intro)}

# ---------- 01 Logo ----------
def construction():
    p = B; seam_c = f'M{50 + (51.5 + 12) * .2867:.2f} -12L{50 - (112 - 51.5) * .2867:.2f} 112'
    lab = lambda x, y, t, a="start", c=PRU: f'<text x="{x}" y="{y}" text-anchor="{a}" fill="{c}">{t}</text>'
    return (f'<svg viewBox="-22 -14 144 128" class="cons" role="img" aria-label="Construction of the Break">'
            f'<g opacity=".14">{brk(stone=STONE, ground="none").replace("<svg ", "<svg width=\"100\" height=\"100\" ", 1)}</g>'
            f'<rect width="100" height="100" rx="22" fill="none" stroke="{INK}" stroke-width=".3"/>'
            f'<path d="{Q["cav"]}" fill="none" stroke="{INK}" stroke-width=".3" stroke-dasharray="1 .8"/><path d="{Q["gem"]}" fill="none" stroke="{PRU}" stroke-width=".45"/>'
            f'<path d="{seam_c}" stroke="{PRU}" stroke-width=".3" stroke-dasharray="2 1"/><path d="M50 -12V112" stroke="{INK}" stroke-width=".2" stroke-dasharray=".6 .8"/>'
            f'<path d="M0 51.5H100" stroke="{INK}" stroke-width=".2" stroke-dasharray=".6 .8"/>'
            f'<path d="M50 4A10 10 0 0 1 52.8 4.4" fill="none" stroke="{PRU}" stroke-width=".3"/>' + lab(54, 3.6, "16°") +
            f'<path d="M0 -6H100M0 -7.5V-4.5M100 -7.5V-4.5" stroke="{INK}" stroke-width=".25"/>' + lab(50, -8.5, "100", "middle", INK) +
            f'<path d="M0 22H-3M0 0H-3" stroke="{INK}" stroke-width=".25"/>' + lab(-4, 12.5, "r 22", "end", INK) +
            lab(-4, 52.5, "51.5", "end", INK) + lab(78, 30, "crystal 38.4 × 60") + lab(78, 34.5, "shoulder 25.2") + lab(77, 78, "cavity, 6.5 clear", "start", INK) +
            lab(14, 106, "seam 7.5, thinning to 1.5 at the edge", "start", INK) + '</svg>')
USED = ["19006", "87008", "24800", "3652", "18972", "81248"]
def window(img, stone=STONE, ground=PAPER, pos="xMidYMid slice"):
    i = abs(hash(img + stone)) % 99999
    return (f'<svg viewBox="0 0 100 100" style="width:100%;height:100%;display:block" role="img" aria-label="A print seen through the crystal"><defs><clipPath id="t{i}">{CONT["tile"]}</clipPath><clipPath id="g{i}"><path d="{Q["gem"]}"/></clipPath>'
            f'<mask id="m{i}"><rect width="100" height="100" fill="#fff"/><path d="{Q["seam"]}" fill="#000"/><path d="{Q["cav"]}" fill="#000"/></mask></defs>'
            f'<g clip-path="url(#t{i})"><rect width="100" height="100" fill="{ground}"/><rect width="100" height="100" fill="{stone}" mask="url(#m{i})"/>'
            f'<image href="prints/{img}.webp" x="18" y="16" width="64" height="68" preserveAspectRatio="{pos}" clip-path="url(#g{i})"/></g></svg>')
READ = [("A stone, split", "A tile of dark stone with a seam run through it at sixteen degrees, the angle a cleaved mineral breaks along.", mk()),
        ("The crystal", "Stibnite, antimony's ore, grows in long prisms. Ours sits in the break, tilted with it, one facet catching the light.", mk(ground=PAPER, stone="#D8D3C7")),
        ("The window", "Look through the crystal and there is a picture: the work. On the website it holds a print.", window("19006")),
        ("What is left", "Antimony refined gold by taking away everything else. Cut the stone away and what is left is the light.",
         f'<svg viewBox="0 0 100 100" style="width:100%;height:100%"><path d="{Q["gem"]}" fill="{SKY}"/><path d="{Q["facet"]}" fill="#fff" fill-opacity=".28"/></svg>')]
DONTS = [("Rotate it. The seam is always 16° from upright.", brk(stone=STONE, ground=PAPER, style="width:100%;height:100%;transform:rotate(-16deg)")),
         ("Colour the stone.", brk(stone=COB, ground=PAPER, style="width:100%;height:100%")),
         ("Light the crystal in any colour but sky.", brk(stone=STONE, ground=PAPER, lit="#F0563A", style="width:100%;height:100%")),
         ("Stretch it.", brk(stone=STONE, ground=PAPER, style="width:100%;height:100%;transform:scaleX(1.3)")),
         ("Change its container.", f'<svg viewBox="0 0 100 100" style="width:100%;height:100%"><defs><clipPath id="hx"><path d="M50 0L95 25V75L50 100L5 75V25Z"/></clipPath></defs><g clip-path="url(#hx)">{brk(stone=STONE, ground=PAPER).replace("<svg ", "<svg width=\"100\" height=\"100\" ", 1)}</g></svg>'),
         ("Outline it.", f'<svg viewBox="-2 -2 104 104" style="width:100%;height:100%" fill="none" stroke="{STONE}" stroke-width="1.6"><rect width="100" height="100" rx="22"/><path d="{Q["cav"]}"/><path d="{Q["gem"]}"/></svg>'),
         ("Close the seam.", f'<svg viewBox="0 0 100 100" style="width:100%;height:100%"><rect width="100" height="100" rx="22" fill="{STONE}"/><path d="{Q["gem"]}" fill="{SKY}"/></svg>'),
         ("Crowd it.", f'<svg viewBox="0 0 100 100" style="width:100%;height:100%">{brk(stone=STONE, ground=PAPER).replace("<svg ", "<svg width=\"100\" height=\"100\" ", 1)}<text x="58" y="28" style="font:700 15px Arial" fill="#C8472F">NEW</text></svg>')]
logo = chapter_head("logo", 1, "A stone split open, with a crystal grown in the break. It has to hold at sixteen pixels and on the front of a building, so it is drawn to be exact at both.",
    [("about", "Readings"), ("lockup", "Lockup"), ("symbol", "Symbol"), ("wordmark", "Wordmark"), ("containers", "Containers"), ("construction", "Construction"), ("space", "Clear space and size"),
     ("small", "Small sizes"), ("family", "Our products"), ("others", "Working with others"), ("dont", "What not to do"), ("element", "As a design element")])
logo += sec("about", "Readings", '<p class="lede">Four readings, each true, for anyone who looks for long enough.</p>',
    '<div class="four">' + "".join(f'<figure><div class="tile">{s}</div><figcaption><b>{a}</b>{b}</figcaption></figure>' for a, b, s in READ) + '</div>', n="01")
logo += sec("lockup", "Lockup", '<p>The mark beside the wordmark: the website header, a letterhead, the end of a film. The wordmark stands 0.54 of the mark\'s height, from the top of the t to the tail of the y, centred on it, with 0.28 of the mark between them.</p>',
    f'<div class="two"><figure><div class="tile wide">{lock(STONE, PAPER, INK, 88)}</div><figcaption><b>on paper</b>Stone and sky; the tittle in Prussian.</figcaption></figure>'
    f'<figure><div class="tile wide ink">{lock(PAPER, INK, "#E7E2D6", 88)}</div><figcaption><b>on ink</b>Paper and sky; the tittle in sky.</figcaption></figure>'
    f'<figure><div class="tile wide cob">{lock(PAPER, COB, PAPER, 88)}</div><figcaption><b>on cobalt</b>For a single loud moment.</figcaption></figure>'
    f'<figure><div class="tile wide">{lock(STONE, PAPER, INK, 88).replace(SKY, STONE).replace(PRU, INK)}</div><figcaption><b>one colour</b>For anything printed in one ink.</figcaption></figure></div>', n="02")
logo += sec("symbol", "Symbol", '<p>On its own wherever the name is already present or there is no room for it: avatars, app icons, the favicon, the foot of a page.</p>',
    f'<div class="four"><figure><div class="tile">{mk(STONE, PAPER)}</div><figcaption>On paper</figcaption></figure><figure><div class="tile ink">{mk(PAPER, INK)}</div><figcaption>On ink</figcaption></figure>'
    f'<figure><div class="tile cob">{mk(PAPER, COB)}</div><figcaption>On cobalt</figcaption></figure><figure><div class="tile pru">{mk(PAPER, PRU)}</div><figcaption>On Prussian</figcaption></figure></div>', n="03")
logo += sec("wordmark", "Wordmark", '<p>Drawn from Timeless Serif, in lower case. Three changes make it ours: the tittle of the i is a small crystal, the t is joined to the i, and the tail of the y is cut on the crystal\'s angle. The tittle is sky on ink and cobalt, and Prussian on paper, where sky is too faint at that size.</p>',
    f'<figure><div class="tile wide" style="aspect-ratio:3.2">{wm(INK, style="width:62%;height:auto")}</div></figure><figure><div class="tile wide ink" style="aspect-ratio:3.2">{wm("#E7E2D6", SKY, "width:62%;height:auto")}</div></figure>', n="04")
logo += sec("containers", "Containers", '<p>The stone is a tile with corners of 22 units on a 100 unit square. Two other containers exist, each for one job, and the break is the same in all three.</p>',
    f'<div class="three"><figure><div class="tile">{mk()}</div><figcaption><b>tile</b>Everywhere, unless a platform asks otherwise.</figcaption></figure>'
    f'<figure><div class="tile">{brk("round", stone=STONE, ground=PAPER, style="width:100%;height:100%")}</div><figcaption><b>round</b>Avatars, where the platform crops to a circle.</figcaption></figure>'
    f'<figure><div class="tile">{brk("square", stone=STONE, ground=PAPER, style="width:100%;height:100%")}</div><figcaption><b>square</b>App icons, so the platform\'s own mask does the rounding.</figcaption></figure></div>', n="05")
logo += sec("construction", "Construction", '<p>Every point is found from a handful of numbers on a 100 unit square. Nothing is placed by eye.</p>',
    f'<div class="two">{construction()}<div class="nums">'
    f'<div><b>100, r 22</b><span>The tile, and the radius of its corners.</span></div>'
    f'<div><b>16°</b><span>The angle of the seam from upright. The crystal is sheared to the same angle, so it grows along the break.</span></div>'
    f'<div><b>50, 51.5</b><span>The crystal\'s centre: 1.5 below the middle, so it sits, rather than floats.</span></div>'
    f'<div><b>38.4 × 60</b><span>The crystal: a hexagon 38.4 wide and 60 tall, its shoulders 25.2 from each point.</span></div>'
    f'<div><b>6.5</b><span>Clear stone around the crystal at its sides; 7.5 at its points. The cavity is the crystal, grown by that much.</span></div>'
    f'<div><b>7.5</b><span>The seam\'s width beside the crystal. It thins to a fifth of that, 1.5, where it meets the edge.</span></div>'
    f'<div><b>28%</b><span>The facet, the crystal\'s right half, is lit with white at 28 per cent.</span></div></div></div>', n="06")
logo += sec("space", "Clear space and size", '<p>Keep 22 units, the radius of the tile\'s corner, clear on every side: about a fifth of the mark. Nothing enters it, not type, not other marks, not the edge of the page.</p>',
    f'<div class="two"><svg viewBox="-30 -30 160 160" class="cons" role="img" aria-label="Clear space"><rect x="-22" y="-22" width="144" height="144" fill="none" stroke="{PRU}" stroke-width=".5" stroke-dasharray="2 1.5"/>'
    f'{brk(stone=STONE, ground="none").replace("<svg ", "<svg width=\"100\" height=\"100\" ", 1)}'
    + "".join(f'<text x="{x}" y="{y}" text-anchor="middle" fill="{PRU}" style="font:400 5px var(--mono)">22</text>' for x, y in ((-11, 52), (111, 52), (50, -9), (50, 113))) +
    '</svg><div class="nums"><div><b>22</b><span>Units of clear space, measured on the mark, for the symbol and the lockup.</span></div>'
    '<div><b>16 px</b><span>The smallest symbol on screen, using the version drawn for small sizes.</span></div><div><b>120 px</b><span>The narrowest lockup on screen.</span></div>'
    '<div><b>6 mm</b><span>The smallest symbol in print; 26 mm for the lockup.</span></div></div></div>', n="07")
logo += sec("small", "Small sizes", f'<p>Below 30 pixels the mark changes, not just shrinks: the seam widens to 10, the clear stone to 8, and the seam thins less toward the edge, so the break still reads at a glance. These are the files in the favicon.</p>',
    '<div class="two"><div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;align-items:end">'
    + "".join(f'<figure><img class="px" src="img/b-favicon-{s}.png" alt=""><figcaption><b>{s} px</b></figcaption></figure>' for s in (16, 32, 48)) + '</div>'
    f'<div class="nums"><div><b>16, 32</b><span>Drawn for small sizes.</span></div><div><b>48 and up</b><span>The mark as drawn.</span></div></div></div>'
    f'<figure><div><span class="tab"><img src="img/b-favicon-32.png" width="16" height="16" alt="">Antimony</span><div style="height:90px;background:#fff;border:1px solid var(--rule)"></div></div><figcaption><b>in a browser tab</b></figcaption></figure>', n="08")
logo += sec("family", "Our products", '<p>Each product carries its own mark. Antimony stands beside it as its maker, never inside it.</p>',
    f'<div class="two"><figure><div class="tile wide" style="display:flex;gap:10%;justify-content:center;padding:0">{brk(stone=STONE, ground=PAPER, style="width:26%;height:auto")}<img src="img/orbe-mark.png" alt="The Orbe mark" style="width:26%;height:auto"></div><figcaption><b>antimony and orbe</b>A stone split by a crystal; a block with its orb struck out.</figcaption></figure>'
    f'<figure><div class="tile wide" style="display:flex;gap:16px;align-items:center;justify-content:center;flex-wrap:wrap;padding:0 6%"><img src="img/orbe-lockup.png" alt="The Orbe lockup" style="width:46%;height:auto;min-width:0"><span style="display:flex;align-items:center;gap:8px;font:400 13px var(--mono);color:var(--dim);border-left:1px solid var(--rule);padding-left:16px">by {wm(INK, style="height:14px;width:auto")}</span></div><figcaption><b>the endorsement</b>Where a product needs its maker named: the wordmark, after a hairline.</figcaption></figure></div>', n="09")
logo += sec("others", "Working with others", "<p>When our name appears beside another company's, set the two at equal optical size, a hairline and clear space between them, and only where the relationship is real and agreed in writing. Never place a mark so that it suggests one company endorses or partners with the other. Never join our mark to anyone else's.</p>", "", n="10")
logo += sec("dont", "What not to do", '<p>Beyond the usual rules for any mark (do not warp it, do not add effects), eight that belong to this one.</p>',
    '<div class="four dont">' + "".join(f'<figure><div class="tile">{s}</div><figcaption>{t}</figcaption></figure>' for t, s in DONTS) + '</div>', n="11")
logo += sec("element", "As a design element", '<p>Two uses beyond the logo, and only these two. The window: the crystal holding a picture. The characters: the mark drawn in type on the terminal, as the website opens. Never both in one layout.</p>',
    f'<div class="two"><figure><div class="tile">{window("87008")}</div><figcaption><b>the window</b>A print in the crystal. See Art direction.</figcaption></figure>'
    f'<figure><div class="tile ink" style="padding:8%"><canvas class="glyphs" aria-hidden="true"></canvas></div><figcaption><b>the characters</b>Words in the crystal, grain in the stone, the cut edges lit. Move over it.</figcaption></figure></div>', n="12")
sizes["logo"] = write("logo", "Logo, Antimony Standards", logo)

# ---------- 02 Typography ----------
SCALE = [("Display", 148, "serif", ".9"), ("Headline", 84, "serif", "1.0"), ("Title", 42, "serif", "1.06"), ("Lede", 25, "serif", "1.42"), ("Body", 19, "serif", "1.55"),
         ("Small", 15, "serif", "1.45"), ("Terminal", 12, "mono", "1.7"), ("Label", 11, "mono", "1.4")]
AZ = "ABCDEFGHIJKLMNOPQRSTUVWXYZ<br>abcdefghijklmnopqrstuvwxyz<br>0123456789 &amp; ! ? ( ) £ € %"
typ = chapter_head("type", 2, "Two faces. A serif for what we say, a monospace for what the machine says.", [("faces", "The faces"), ("scale", "Scale"), ("rules", "Using type"), ("languages", "Other languages")])
typ += sec("faces", "The faces", "",
    f'<div class="nums"><div><b>serif</b><span><span style="font:400 54px/1.05 var(--serif);display:block;margin-bottom:10px">Timeless Serif</span>Headlines, body text, the source of the wordmark, and anything said with conviction. Licensed to Antimony. Set it large and let it be quiet; use the italic for names and the odd emphasis.<p class="spec" style="margin-top:14px">{AZ}</p></span></div>'
    f'<div><b>mono</b><span><span style="font:400 38px/1.1 var(--mono);display:block;margin-bottom:10px">Commit Mono</span>The terminal: labels, figures, the boot lines, the characters the mark is drawn in, code. Open source. Lower case, tracked a little.<p class="spec" style="font-family:var(--mono);font-size:clamp(16px,2.1vw,23px);margin-top:14px">{AZ}</p></span></div></div>', n="01")
typ += sec("scale", "Scale", '<p>Eight steps, on screen in pixels. In print, divide by 1.33 for points.</p>',
    '<div class="scroll"><table><thead><tr><th>step</th><th class="num">size</th><th class="num">leading</th><th>sample</th></tr></thead><tbody>' + "".join(
        f'<tr><th style="font-weight:400">{n}</th><td class="num">{s}</td><td class="num">{l}</td><td style="font:400 {min(s, 60)}px/{l} var(--{fam});white-space:nowrap">antimony</td></tr>' for n, s, fam, l in SCALE) + '</tbody></table></div>', n="02")
typ += sec("rules", "Using type", "",
    '<div class="nums"><div><b>case</b><span>Sentence case for prose and headlines. The mono is set in lower case, as a terminal would print it.</span></div>'
    '<div><b>measure</b><span>Body text runs 30 to 36 ems wide. The website\'s brief is 640 pixels across.</span></div>'
    '<div><b>contrast</b><span>Set a headline clearly larger or clearly smaller than the wordmark beside it, never the same.</span></div>'
    '<div><b>figures</b><span>Tables, prices and coordinates in Commit Mono, so columns line up.</span></div>'
    '<div><b>cursor</b><span>When text is typed on, it ends in a sky block cursor, blinking at 1.06 seconds.</span></div>'
    '<div><b>punctuation</b><span>British spelling. Curly quotation marks. No em or en dashes: a colon, a comma or a full stop does the work, and "to" for ranges.</span></div></div>', n="03")
typ += sec("languages", "Other languages", '<p>Timeless covers Latin scripts. For others, use Noto Serif and Noto Sans Mono in the matching script, and Source Han Serif for Chinese, Japanese and Korean, set at the same optical size as the Latin beside them.</p>', "", n="04")
sizes["type"] = write("type", "Typography, Antimony Standards", typ)

# ---------- 03 Colour ----------
def lum(h): c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]; c = [v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4 for v in c]; return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]
def ratio(a, b): x, y = sorted((lum(a), lum(b)), reverse=True); return (x + .05) / (y + .05)
def rgb(h): return ", ".join(str(int(h[i:i + 2], 16)) for i in (1, 3, 5))
CORE = [("Ink", INK, "The ground of the terminal and the night side.", PAPER), ("Stone", STONE, "The stone of the mark on paper.", PAPER), ("Paper", PAPER, "The ground of every page we write on.", INK),
        ("Sky", SKY, "The light: the crystal, the cursor, a lit character.", INK), ("Prussian", PRU, "Sky's partner on paper: links, the tittle, a print in one ink.", PAPER), ("Cobalt", COB, "A loud ground, for one moment at a time.", PAPER)]
col = chapter_head("colour", 3, "Ink and paper carry everything. One light, sky, and its partner on paper, Prussian. The rest is borrowed from the prints.", [("core", "Core colours"), ("light", "The light"), ("contrast", "Contrast"), ("proportion", "Proportion")])
col += sec("core", "Core colours", "",
    '<div class="three">' + "".join(f'<div class="sw" style="background:{h};color:{t}"><b>{n}</b><span>{h}</span><span>RGB {rgb(h)}</span><span>{r}</span></div>' for n, h, r, t in CORE) + '</div>'
    '<p class="dim">Screen values. For print, match each to a drawdown on the stock being used; do not convert by formula.</p>', n="01")
col += sec("light", "The light", '<p>The crystal is always sky. On paper, sky is a colour you see but cannot read, so anything small that has to be read takes Prussian instead: the tittle, a link, a figure.</p>',
    f'<div class="three"><figure><div class="tile">{mk(STONE, PAPER)}</div><figcaption><b>on paper</b>The crystal in sky; it is large enough to see.</figcaption></figure>'
    f'<figure><div class="tile wide" style="aspect-ratio:1;padding:12%">{wm(INK, style="width:100%;height:auto")}</div><figcaption><b>small, on paper</b>The tittle in Prussian.</figcaption></figure>'
    f'<figure><div class="tile ink">{mk(PAPER, INK)}</div><figcaption><b>on ink</b>Sky, everywhere.</figcaption></figure></div>', n="02")
PAIRS = [(INK, PAPER), (INK, SKY), (PAPER, STONE), (PAPER, PRU), (PAPER, COB), (PAPER, SKY), (COB, PAPER), (PRU, PAPER)]
NAME = {h: n for n, h, _, _ in CORE}
def use(r): return "any text" if r >= 7 else "any text, AA" if r >= 4.5 else "large text and marks" if r >= 3 else "never for text"
col += sec("contrast", "Contrast", '<p>Every pairing we use, measured with the WCAG 2 formula.</p>',
    '<div class="scroll"><table><thead><tr><th>ground</th><th>colour</th><th class="num">ratio</th><th>use</th></tr></thead><tbody>' + "".join(
        f'<tr><td>{NAME[g]}</td><td><span style="display:inline-block;width:12px;height:12px;background:{c};border:1px solid var(--rule);vertical-align:-1px;margin-right:8px"></span>{NAME[c]}</td><td class="num">{ratio(g, c):.2f} : 1</td><td>{use(ratio(g, c))}</td></tr>' for g, c in PAIRS)
    + '</tbody></table></div>', n="03")
PROP = [("Ink", INK, 40), ("Paper", PAPER, 44), ("Stone", STONE, 8), ("Prussian", PRU, 4), ("Sky", SKY, 3), ("Cobalt", COB, 1)]
col += sec("proportion", "Proportion", '<p>Across a body of work, roughly this much of each. The light is rare on purpose.</p>',
    '<div class="prop">' + "".join(f'<div style="flex:{v};background:{h};border-right:1px solid var(--rule)" title="{k} {v}%"></div>' for k, h, v in PROP) + '</div>'
    '<div style="display:flex;gap:20px;flex-wrap:wrap;font:400 13px var(--mono);color:var(--dim)">' + "".join(f'<span>{k.lower()} {v}%</span>' for k, _, v in PROP) + '</div>', n="04")
sizes["colour"] = write("colour", "Colour, Antimony Standards", col)

# ---------- 04 Art direction ----------
art = chapter_head("art", 4, "We do not make pictures of the future. We look back two hundred years, to people who made prints of the world with great patience, and let them show through.", [("prints", "The prints"), ("window", "The window"), ("characters", "In characters"), ("rules", "Rules"), ("sources", "Sources")])
art += sec("prints", "The prints", '<p>Japanese woodblock prints by Katsushika Hokusai and Utagawa Hiroshige, from the Art Institute of Chicago, all released under CC0. Mountains, weather, bridges, people on the road. They are what nostalgia looks like without being about us.</p>',
    '<div class="three">' + "".join(f'<figure><img class="shot" src="prints/{k}.webp" alt="{SRC[k]["title"].split(",")[0][:90]}" loading="lazy" style="aspect-ratio:4/3;object-fit:cover"><figcaption><b>{SRC[k]["artist"].split(chr(10))[0].split(" ")[0].lower()} {SRC[k]["artist"].split(chr(10))[0].split(" ")[1].lower()}</b>{SRC[k]["title"].split(" (")[0].split(", from")[0]}, {SRC[k]["date"]}.</figcaption></figure>' for k in USED) + '</div>', n="01")
art += sec("window", "The window", '<p>A print seen through the crystal: the only way a picture and the mark meet. The print drifts slowly behind it, a few per cent over twenty-four seconds, so it feels like looking through glass.</p>',
    '<div class="three">' + "".join(f'<figure><div class="tile{c}" style="padding:12%">{window(k, s, g)}</div><figcaption>{SRC[k]["title"].split(" (")[0].split(", from")[0]}.</figcaption></figure>'
        for k, s, g, c in [("19006", STONE, PAPER, ""), ("87008", STONE, PAPER, ""), ("24800", PAPER, INK, " ink")]) + '</div>', n="02")
art += sec("characters", "In characters", '<p>On ink, a print can be drawn in type: each character\'s density follows the print\'s light, each takes the print\'s own colour. On paper, the same print is drawn in Prussian, dense where the print is dark, as ink would be. This is how the website carries you from the crystal to the page.</p>',
    '<div class="two"><figure><img class="shot" src="img/b-home-light.webp" alt="A print by Hiroshige drawn in characters on ink" loading="lazy"><figcaption><b>on ink</b>In the print\'s own colour.</figcaption></figure>'
    '<figure><img class="shot" src="img/b-home-paper.webp" alt="The same print drawn in Prussian characters on paper" loading="lazy"><figcaption><b>on paper</b>In Prussian, as the paper wipes in at the seam\'s angle.</figcaption></figure></div>', n="03")
art += sec("rules", "Rules", "",
    '<div class="nums"><div><b>credit</b><span>Every print carries its credit: artist, title, date, "Art Institute of Chicago, CC0". In a window too small to caption, credit it where the layout is described.</span></div>'
    '<div><b>whole</b><span>Never recolour a print, never crop out its title cartouche and pass it off as a landscape, never set type over a face.</span></div>'
    '<div><b>truth</b><span>Never make new pictures that imitate these prints and present them as old. If we commission work, it is credited as ours.</span></div>'
    '<div><b>one</b><span>One print per layout. The archive is a source, not a collage.</span></div></div>', n="04")
art += sec("sources", "Sources", f'<p>{len(SRC)} prints, each from the Art Institute of Chicago under CC0.</p>',
    '<div class="scroll"><table><thead><tr><th>artist</th><th>print</th><th class="num">date</th><th class="num">reference</th></tr></thead><tbody>' + "".join(
        f'<tr><td>{s["artist"].split(chr(10))[0].split(" ")[0]} {s["artist"].split(chr(10))[0].split(" ")[1]}</td><td>{s["title"][:110]}</td><td class="num">{s["date"]}</td><td class="num"><a href="{s["url"]}">{s["id"]}</a></td></tr>' for s in SRC.values()) + '</tbody></table></div>', n="05")
sizes["art"] = write("art", "Art direction, Antimony Standards", art)

# ---------- 05 Motion ----------
mot = chapter_head("motion", 5, "Everything moves at the speed of the hand that scrolls it. Nothing plays to you; you play it.", [("break", "The break"), ("film", "The film"), ("pieces", "The pieces"), ("timing", "Timing"), ("rules", "Rules")])
mot += sec("break", "The break", '<p>The website opens on a terminal. The mark is drawn in characters, decoding from the centre out. Then the scroll does the rest, in four stages, each tied to how far you have scrolled, never to a clock.</p>',
    '<div class="two">' + "".join(f'<figure><img class="shot" src="img/b-home-{k}.webp" alt="" loading="lazy"><figcaption><b>{n}</b>{d}</figcaption></figure>' for k, n, d in [
        ("stone", "01 stone", "The Break in characters: words in the crystal, grain in the stone, the cut edges lit."), ("break", "02 break", "The halves part along the seam and slide apart; the crystal grows and turns 12 degrees."),
        ("light", "03 light", "You go into the crystal, and a print blooms in it, a character at a time."), ("end", "04 paper", "Paper wipes across at 16 degrees; the mark closes small at the foot; the brief is typed.")]) + '</div>', n="01")
mot += sec("film", "The film", '<p>The same sequence, recorded at an even scroll. For the start of talks, and posts. Square and 16 by 9 versions are in the kit.</p>',
    '<video src="img/the-break-1920x1080.mp4" autoplay muted loop playsinline aria-label="The break, as a film"></video>', ink=True, n="02")
mot += sec("pieces", "The pieces", "",
    '<div class="nums"><div><b>boot</b><span>Five lines, typed one at a time, ending in "ready" in sky.</span></div>'
    '<div><b>decode</b><span>Each character arrives as random glyphs in sky, then settles into itself. It starts at the centre and spreads.</span></div>'
    '<div><b>scramble</b><span>Near the pointer, characters scramble and light. Tap and a ring runs out from the point, scrambling as it passes.</span></div>'
    '<div><b>wipe</b><span>Paper crosses the screen along the seam\'s angle, with a line of scrambled characters at its edge.</span></div>'
    '<div><b>type</b><span>Prose is typed on with a sky block cursor.</span></div>'
    '<div><b>pencil</b><span>The crystal in the small mark is coloured in once with a pixel pencil, in sky, then the print shows through.</span></div></div>', n="03")
TIM = [("Boot line", "240 ms", "", "One line of the boot."), ("Decode", "450 ms", "", "A character, from glyph to itself."), ("The break", "6.2 screens of scroll", "eased, then smoothed at 8.5% a frame", "From stone to paper."),
       ("Ring", "820 px a second", "linear", "A tap on the stone."), ("Type", "18 to 44 ms", "random, two letters a step", "Per step of typing."), ("Pencil", "26 ms", "", "Three strokes of colouring."),
       ("Interface", "180 to 240 ms", "cubic-bezier(.2, .7, .2, 1)", "Hovers, menus, small changes.")]
mot += sec("timing", "Timing", "", '<div class="scroll"><table><thead><tr><th>move</th><th class="num">duration</th><th class="num">easing</th><th>for</th></tr></thead><tbody>' + "".join(
    f'<tr><th style="font-weight:400">{a}</th><td class="num">{b}</td><td class="num">{c}</td><td>{d}</td></tr>' for a, b, c, d in TIM) + '</tbody></table></div>', n="04")
mot += sec("rules", "Rules", "", '<div class="nums"><div><b>hand</b><span>Long sequences follow the scroll, so they can be slowed, stopped and played back.</span></div><div><b>still</b><span>With reduced motion on, show the final frame and type the text in full.</span></div>'
    '<div><b>no bounce</b><span>Nothing overshoots, wobbles or springs. Stone does not bounce.</span></div><div><b>one light</b><span>Only the thing that is moving is lit.</span></div></div>', n="05")
sizes["motion"] = write("motion", "Motion, Antimony Standards", mot)

# ---------- 06 Voice ----------
VP = [("Revolutionising the creator economy with AI.", "Orbe holds the money until the work is delivered."), ("Seamless, end to end brand partnerships.", "Every deal in one place: the brief, the contract, the payment."),
      ("We're on a mission to empower creators!", "We sit on the creator's side of the table."), ("Leverage our cutting edge platform to unlock value.", "Send a brief. Get paid when the work is done.")]
voice = chapter_head("voice", 6, "Plain, exact and on their side. Brief, the way a good craftsperson talks about their work.", [("principles", "How we write"), ("pairs", "Before and after"), ("words", "Words"), ("names", "Names")])
voice += sec("principles", "How we write", "", '<div class="nums"><div><b>brief</b><span>Say it in fewer words, then stop. Our home page is two paragraphs.</span></div><div><b>plain</b><span>Short sentences, common words. If a word needs explaining, choose another.</span></div>'
    '<div><b>exact</b><span>Say what happens: who pays whom, when, for what. A number beats an adjective.</span></div><div><b>on their side</b><span>Write from the creator\'s side of the screen, about their work, in their terms.</span></div>'
    '<div><b>calm</b><span>No exclamation marks, no hype, no countdowns. Confidence is quiet.</span></div><div><b>british</b><span>British spelling and punctuation; no em or en dashes.</span></div></div>', n="01")
voice += sec("pairs", "Before and after", "", "".join(f'<div class="do"><div><span class="k">not this</span><span>{a}</span></div><div class="yes"><span class="k">this</span><span>{b}</span></div></div>' for a, b in VP), n="02")
voice += sec("words", "Words", "", '<div class="two"><div class="nums"><div><b>use</b><span>work, make, deal, brief, paid, on time, yours, together</span></div></div><div class="nums"><div><b>avoid</b><span>revolutionise, seamless, leverage, unlock, empower, game changing, ecosystem</span></div></div></div>', n="03")
voice += sec("names", "Names", '<p>Antimony is the company. Orbe is our first product. Write "Antimony, makers of Orbe" where both are needed. Describe other companies and their products factually, and never suggest a partnership or endorsement that does not exist in writing.</p>', "", n="04")
sizes["voice"] = write("voice", "Voice, Antimony Standards", voice)

# ---------- 07 Brand in use ----------
use_ = chapter_head("use", 7, "Where people meet Antimony first. Every image here is a file in the kit, at the size the platform asks for.", [("linkedin", "LinkedIn"), ("social", "Social"), ("deck", "Presentations"), ("print", "Print"), ("web", "Web and app"), ("email", "Email")])
use_ += sec("linkedin", "LinkedIn", "", '<div class="profile"><img class="ban" src="img/b-linkedin-cover.webp" alt="Company cover"><div class="pb"><img class="av" src="img/b-avatar.webp" alt="Avatar"><b>Antimony</b><span>Software for the people who make the work.</span></div></div>'
    '<figure><img class="shot" src="img/b-linkedin-banner.webp" alt="Personal banner" loading="lazy"><figcaption><b>personal banner</b>1584 by 396. A print, with the lockup on a paper label at the right, clear of the profile photo.</figcaption></figure>', n="01")
use_ += sec("social", "Social", "", '<div class="three">' + "".join(f'<figure><img class="shot" src="img/b-post-{i}.webp" alt="" loading="lazy"><figcaption><b>post {i}</b>1080 by 1350, the window.</figcaption></figure>' for i in (1, 2, 3)) + '</div>'
    '<div class="two"><figure><img class="shot" src="img/b-x-header.webp" alt="X header" loading="lazy"><figcaption><b>x header</b>1500 by 500.</figcaption></figure><figure><img class="shot" src="img/b-og.webp" alt="" loading="lazy"><figcaption><b>link card</b>1200 by 630.</figcaption></figure></div>', n="02")
use_ += sec("deck", "Presentations", "", '<div class="three">' + "".join(f'<figure><img class="shot" src="img/b-deck-{i}.webp" alt="" loading="lazy"><figcaption><b>{n}</b>{d}</figcaption></figure>' for i, n, d in [(1, "title", "On ink."), (2, "content", "One print, one idea, on paper."), (3, "close", "The mark alone.")]) + '</div>', n="03")
use_ += sec("print", "Print", "", '<div class="three"><figure><img class="shot" src="img/b-card-front.webp" alt="" loading="lazy"><figcaption><b>card, front</b>85 by 55 mm, with bleed.</figcaption></figure><figure><img class="shot" src="img/b-card-back.webp" alt="" loading="lazy"><figcaption><b>card, back</b></figcaption></figure><figure><img class="shot" src="img/b-letterhead.webp" alt="" loading="lazy" style="max-width:260px"><figcaption><b>letterhead</b>A4.</figcaption></figure></div>', n="04")
use_ += sec("web", "Web and app", "", '<div class="two"><figure><img class="shot" src="img/b-home-stone.webp" alt="The website, opening" loading="lazy"><figcaption><b>the website</b>Opens on the terminal. See Motion.</figcaption></figure>'
    '<figure><img class="shot" src="img/b-app-512.webp" alt="" loading="lazy" style="max-width:180px;border-radius:40px"><figcaption><b>app icon</b>The square container, so the platform\'s mask rounds it.</figcaption></figure></div>', n="05")
use_ += sec("email", "Email", "", f'<div class="sig"><b style="font-weight:700">Name Surname</b><br>Antimony, makers of Orbe<br><span style="color:#666">name@antimony.inc</span><div style="margin-top:12px">{lock(STONE, "#fff", INK, 22)}</div></div><p class="dim">Plain text, with the lockup at 22 pixels. No banners, no quotes, no social icons.</p>', n="06")
sizes["use"] = write("use", "Brand in use, Antimony Standards", use_)

# ---------- 08 Downloads ----------
FILES = [("logo/", "The mark, lockup and wordmark on paper, ink and cobalt, and the round mark, as PNG at up to 2400 px."), ("svg/", "The mark as SVG: full colour, reversed, one colour, round and small, and the geometry it is drawn from."),
         ("icons/", "Favicons at 16, 32 and 48, and app icons at 180, 192, 512 and 1024."), ("social/", "Avatar, LinkedIn cover and banner, X header, link card and three posts."),
         ("deck/", "Title, content and closing slides at 1920 by 1080."), ("print/", "Business card front and back, and letterhead, as PDF at true size."),
         ("motion/", "The break, as MP4 at 1920 by 1080 and 1080 square.")]
dl = chapter_head("downloads", 8, "Everything on these pages, as files.", [("kit", "The kit")])
dl += sec("kit", "The kit", '<p>The kit is sent as one archive, <code style="font:400 15px var(--mono)">antimony-break-kit.zip</code>. Ask the brand owner for it. Its folders:</p>', '<div class="files">' + "".join(f'<div><code>{a}</code><span>{b}</span></div>' for a, b in FILES) + '</div>', n="01")
sizes["downloads"] = write("downloads", "Downloads, Antimony Standards", dl)
print(sizes)
