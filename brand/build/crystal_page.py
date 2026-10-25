"""Writes ../crystal/index.html: the Crystal A, taken all the way."""
import json, math, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from crystal_geometry import pieces, HEX, TOP, LL, LR, V
from kit import WM, WM_Y0, WM_Y1
INK, PAPER, COBALT, SKY, MIST = "#0B0D0C", "#F4F3EE", "#2448FF", "#94E6FF", "#D9DBD5"
PC = pieces(); PX = json.load(open("crystal_pixels.json"))
f = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")
poly = lambda pts: "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"
def mark(fill=INK, counter=None, style="", line=None, soft=.8, pad=1.5, cls=""):
    counter = counter or fill
    if line:
        body = "".join(f'<path d="{poly(PC[k])}" fill="none" stroke="{fill}" stroke-width="{line}" stroke-linejoin="round"/>' for k in ("wing_l", "wing_r", "counter", "foot"))
    else:
        body = "".join(f'<path class="{k}" d="{poly(PC[k])}" fill="{counter if k == "counter" else fill}" stroke="{counter if k == "counter" else fill}" stroke-width="{soft}" stroke-linejoin="round"/>' for k in ("wing_l", "wing_r", "foot", "counter"))
    return f'<svg class="{cls}" viewBox="{-pad} {-pad} {100 + 2*pad} {100 + 2*pad}" style="{style}" aria-hidden="true">{body}</svg>'
# the wordmark, its i dot now the counter: a small cobalt triangle
nums = list(map(float, re.findall(r"-?\d+\.?\d*", WM["dot"])))
dx, dy = nums[0::2], nums[1::2]; dcx = (min(dx) + max(dx)) / 2; dcy = (min(dy) + max(dy)) / 2; dr = (max(dx) - min(dx)) / 2 * 1.05
DOT = poly([(dcx, dcy - dr), (dcx + dr * .866 * 1.15, dcy + dr * .5 * 1.15), (dcx - dr * .866 * 1.15, dcy + dr * .5 * 1.15)])
def wordmark(fill=INK, dot=COBALT, style=""):
    return f'<svg viewBox="-10 {WM_Y0} {WM["w"] + 20} {WM_Y1 - WM_Y0}" style="{style}" role="img" aria-label="Antimony"><path d="{WM["letters"]}" fill="{fill}"/><path d="{DOT}" fill="{dot}"/></svg>'
def lockup(fill=INK, counter=COBALT, style=""):
    cap, base = WM["cap"], WM["asc"]; mh = cap * 1.42; s = mh / 100
    ex = 0; ey = base - cap / 2 - mh / 2; gx = 100 * s + cap * .42
    y0 = min(ey, WM_Y0); y1 = max(ey + mh, WM_Y1)
    m = "".join(f'<path d="{poly(PC[k])}" fill="{counter if k == "counter" else fill}" stroke="{counter if k == "counter" else fill}" stroke-width=".8" stroke-linejoin="round"/>' for k in ("wing_l", "wing_r", "foot", "counter"))
    return (f'<svg viewBox="-6 {y0 - 6:.0f} {gx + WM["w"] + 12:.0f} {y1 - y0 + 12:.0f}" style="{style}" role="img" aria-label="Antimony">'
            f'<g transform="translate({ex} {ey:.1f}) scale({s:.4f})">{m}</g><g transform="translate({gx:.1f} 0)"><path d="{WM["letters"]}" fill="{fill}"/><path d="{DOT}" fill="{counter}"/></g></svg>')
def stacked(fill=INK, counter=COBALT, style=""):
    cap = WM["cap"]; mh = cap * 2.6; s = mh / 100; ex = WM["w"] / 2 - 50 * s; ey = WM_Y0 - mh - cap * .55
    m = "".join(f'<path d="{poly(PC[k])}" fill="{counter if k == "counter" else fill}" stroke="{counter if k == "counter" else fill}" stroke-width=".8" stroke-linejoin="round"/>' for k in ("wing_l", "wing_r", "foot", "counter"))
    return (f'<svg viewBox="-10 {ey - 10:.0f} {WM["w"] + 20:.0f} {WM_Y1 - ey + 10:.0f}" style="{style}" role="img" aria-label="Antimony">'
            f'<g transform="translate({ex:.1f} {ey:.1f}) scale({s:.4f})">{m}</g><path d="{WM["letters"]}" fill="{fill}"/><path d="{DOT}" fill="{counter}"/></svg>')
def construction():
    hexo = poly(HEX); tri = poly([TOP, LR, LL]); by = PC["bar_y"]
    return (f'<svg viewBox="-14 -12 128 126" class="cons" role="img" aria-label="Construction of the mark">'
            f'<circle cx="50" cy="50" r="50" class="g"/><path d="{hexo}" class="g2"/><path d="{tri}" class="k"/>'
            f'<g opacity=".14">{mark(INK, INK, pad=0)[mark(INK, INK, pad=0).index(">") + 1:-6]}</g>'
            f'<line x1="50" y1="50" x2="{V(1)[0]:.2f}" y2="{V(1)[1]:.2f}" class="d"/><text x="74" y="34">R</text>'
            f'<line x1="-6" y1="{TOP[1]}" x2="-6" y2="{LL[1]}" class="d"/><line x1="-8" y1="{by}" x2="-4" y2="{by}" class="d"/><text x="-9" y="{by + 1.2}" text-anchor="end">¾</text>'
            f'<line x1="{(TOP[0] + LL[0]) / 2 - 3.9:.2f}" y1="{(TOP[1] + LL[1]) / 2 - 2.25:.2f}" x2="{(TOP[0] + LL[0]) / 2 + 3.9:.2f}" y2="{(TOP[1] + LL[1]) / 2 + 2.25:.2f}" class="d k2"/><text x="{(TOP[0] + LL[0]) / 2 - 9:.2f}" y="{(TOP[1] + LL[1]) / 2 + 1:.2f}" class="t2">W</text>'
            f'<text x="50" y="112" text-anchor="middle" class="t3">60°</text></svg>')
def pixels(rows):
    n = len(rows); cells = "".join(f'<rect x="{i}" y="{j}" width="1" height="1" fill="{INK if c == "1" else COBALT}"/>' for j, r in enumerate(rows) for i, c in enumerate(r) if c != ".")
    grid = "".join(f'<line x1="{k}" y1="0" x2="{k}" y2="{n}"/><line x1="0" y1="{k}" x2="{n}" y2="{k}"/>' for k in range(n + 1))
    return f'<svg viewBox="0 0 {n} {n}" class="px" aria-hidden="true">{cells}<g stroke="rgba(11,13,12,.12)" stroke-width="{1.4/n:.3f}">{grid}</g></svg>'
def pixel_img(rows, scale=1):
    n = len(rows); cells = "".join(f'<rect x="{i}" y="{j}" width="1" height="1" fill="{INK if c == "1" else COBALT}"/>' for j, r in enumerate(rows) for i, c in enumerate(r) if c != ".")
    return f'<svg viewBox="0 0 {n} {n}" width="{n*scale}" height="{n*scale}" shape-rendering="crispEdges" aria-hidden="true">{cells}</svg>'
def lattice(cols=7, rows=4, size=100, lit=(3, 1), fill=INK, ground=None):
    """pointy topped hexagons in rows; the struck lines run on from one crystal into the next"""
    w = size * math.sqrt(3) / 2; out = []
    for j in range(rows):
        for i in range(cols):
            x = i * w + (j % 2) * w / 2 - w / 2; y = j * size * .75 - size * .25
            on = (i, j) == lit
            k = .955; cx_, cy_ = x + w / 2, y + size / 2
            out.append(f'<g transform="translate({cx_:.1f} {cy_:.1f}) scale({size / 100 * k:.4f}) translate(-50 -50)">{mark(fill, COBALT if on else fill, pad=0, soft=0)[mark(fill, pad=0).index(">") + 1:-6]}</g>')
    W_ = cols * w - w / 2; H_ = rows * size * .75 - size * .25
    return f'<svg viewBox="0 0 {W_:.0f} {H_:.0f}" class="lat" aria-hidden="true">{"".join(out)}</svg>'
def strike():
    """the motion: a solid crystal, struck three times; the counter is what is left, and it turns to gold"""
    hexo = poly(HEX); by = PC["bar_y"]; W = PC["W"]
    t = (by - TOP[1]) / (LL[1] - TOP[1]); xl = TOP[0] + (LL[0] - TOP[0]) * t
    def seg(a, b, cls): 
        L = math.hypot(b[0] - a[0], b[1] - a[1]); return f'<path class="cut {cls}" d="M{f(a[0])} {f(a[1])}L{f(b[0])} {f(b[1])}" stroke-dasharray="{L:.1f}" stroke-dashoffset="{L:.1f}" style="--L:{L:.1f}"/>'
    ext = lambda p, q, e: (p[0] - (q[0] - p[0]) / math.hypot(q[0] - p[0], q[1] - p[1]) * e, p[1] - (q[1] - p[1]) / math.hypot(q[0] - p[0], q[1] - p[1]) * e)
    return (f'<svg viewBox="-2 -2 104 104" class="strike" role="img" aria-label="The mark, struck"><path d="{hexo}" fill="{PAPER}"/>'
            f'<g fill="none" stroke="{INK}" stroke-width="{W}" stroke-linecap="butt">{seg(ext(TOP, LL, 6), ext(LL, TOP, 6), "c1")}{seg(ext(TOP, LR, 6), ext(LR, TOP, 6), "c2")}{seg((xl, by), (100 - xl, by), "c3")}</g>'
            f'<path class="gold" d="{poly(PC["counter"])}" fill="{SKY}" stroke="{SKY}" stroke-width=".8" stroke-linejoin="round"/></svg>')
def reading(svg, title, text): return f'<figure class="read"><div class="rt">{svg}</div><figcaption><b>{title}</b>{text}</figcaption></figure>'
R1 = mark(INK, INK)
R2 = f'<svg viewBox="-2 -2 104 104" aria-hidden="true"><path d="{poly(HEX)}" fill="none" stroke="{INK}" stroke-width="2.4"/><path d="{poly([TOP, LR, LL])}" fill="none" stroke="{COBALT}" stroke-width="2.4"/><circle cx="50" cy="50" r="2.6" fill="{INK}"/></svg>'
R3 = lattice(4, 3, 100, lit=None)
R4 = mark(INK, INK) .replace("</svg>", f'<path d="M36 1 L46 -3 M64 1 L54 -3" stroke="{COBALT}" stroke-width="2" fill="none"/><path d="M50 104 L50 112" stroke="{COBALT}" stroke-width="2"/></svg>').replace('viewBox="-1.5 -1.5 103 103"', 'viewBox="-6 -8 112 124"')
R5 = mark(MIST, COBALT)
def row(av, name): return f'<div class="row">{av}<div><b>{name}</b><span>Software Development</span></div></div>'
GHOST = '<div class="row ghost"><span class="av"></span><div><b></b><span></span></div></div>'
AV = f'<span class="av" style="background:{INK};padding:7px">{mark(PAPER, SKY, style="width:100%;height:100%")}</span>'
TESTS = [("Drawn from memory after one look", "A hexagon, an A struck through it."), ("Reads in one colour", "Yes: the counter is colour only when colour is there."),
         ("Reads at 16 px", "Yes, drawn by hand for that size."), ("Every meaning is true", "Five readings, each a fact about antimony or the name."),
         ("Power without menace", "Solid and struck like metal; open at the top, never a fortress."), ("Nobody else's", "One risk: a hexagon with a triangle can recall a twenty sided die. The bar settles it as an A."),
         ("Could be tattooed", "Four shapes, or one fine line around each.")]
html = f'''<title>The Crystal A</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* One mark, taken all the way: idea, construction, readings, versions, small sizes, lockups, family, system, motion, use. */
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-400.woff2) format("woff2"); font-weight: 400; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-500.woff2) format("woff2"); font-weight: 500; font-display: swap; }}
@font-face {{ font-family: "Commit Mono"; src: url(fonts/CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
:root {{ --ink: {INK}; --paper: {PAPER}; --cobalt: {COBALT}; --sky: {SKY}; --rule: rgba(11,13,12,.13); --dim: #5C6461;
  --serif: "Timeless Serif", "Iowan Old Style", Georgia, serif; --sans: "Timeless Sans", "Helvetica Neue", Arial, sans-serif; --mono: "Commit Mono", ui-monospace, Menlo, monospace; color-scheme: light; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: var(--paper); color: var(--ink); }}
body {{ font: 400 16px/1.55 var(--sans); -webkit-font-smoothing: antialiased; }}
.band {{ padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 72px; border-bottom: 1px solid var(--rule); }}
.band.ink {{ background: var(--ink); color: var(--paper); --rule: rgba(244,243,238,.14); --dim: #8A9592; }}
.in {{ max-width: 1120px; margin-inline: auto; display: grid; gap: 30px; }}
.eyebrow {{ font: 500 11.5px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--dim); }}
h1 {{ font: 400 clamp(46px, 7vw, 96px)/.96 var(--serif); letter-spacing: -.025em; }}
h2 {{ font: 400 clamp(30px, 4vw, 48px)/1.04 var(--serif); letter-spacing: -.014em; text-wrap: balance; max-width: 18em; }}
p {{ max-width: 38em; }} .dim {{ color: var(--dim); }}
.lede {{ font: 400 clamp(19px, 2vw, 23px)/1.45 var(--serif); max-width: 32em; }}
.hero {{ display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr); gap: 56px; align-items: center; }}
.hero .m {{ width: min(100%, 420px); justify-self: center; }} .hero .m svg {{ width: 100%; height: auto; display: block; }}
.two {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 36px; align-items: center; }}
.three {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; align-items: start; }}
.five {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 18px; align-items: start; }}
figure {{ display: grid; gap: 10px; min-width: 0; }} figcaption {{ font-size: 14px; color: var(--dim); }}
.cons {{ width: 100%; height: auto; font: 500 4.2px var(--mono); }}
.cons .g {{ fill: none; stroke: var(--rule); stroke-width: .35; stroke-dasharray: 1.2 1.2; }} .cons .g2 {{ fill: none; stroke: var(--ink); stroke-width: .35; }}
.cons .k {{ fill: none; stroke: var(--cobalt); stroke-width: .5; }} .cons .d {{ stroke: var(--ink); stroke-width: .4; }} .cons .k2 {{ stroke: var(--cobalt); }}
.cons text {{ fill: var(--ink); }} .cons .t2 {{ fill: var(--cobalt); }} .cons .t3 {{ fill: var(--dim); }}
.nums {{ display: grid; gap: 12px; }}
.nums div {{ display: grid; grid-template-columns: 4.2em minmax(0, 1fr); gap: 12px; border-top: 1px solid var(--rule); padding-top: 12px; }}
.nums b {{ font: 500 15px var(--mono); color: var(--cobalt); }}
.read {{ align-content: start; }} .rt {{ aspect-ratio: 1; max-width: 100%; display: grid; place-items: center; padding: 18%; border: 1px solid var(--rule); }}
.rt svg {{ width: 100%; height: 100%; display: block; }}
.read b {{ display: block; color: var(--ink); font: 500 15px/1.3 var(--sans); margin-bottom: 4px; }}
.tile {{ aspect-ratio: 1; max-width: 100%; display: grid; place-items: center; padding: 22%; border: 1px solid var(--rule); }}
.tile svg {{ width: 100%; height: 100%; display: block; }}
.tile.ink {{ background: var(--ink); border-color: var(--ink); }} .tile.cob {{ background: var(--cobalt); border-color: var(--cobalt); }}
.tile.skin {{ background: radial-gradient(120% 90% at 40% 30%, #E7B998 0%, #D59F7E 60%, #C48C6C 100%); border: 0; }}
.tile.skin svg {{ filter: blur(.3px); opacity: .9; }}
.tile.stamp {{ background: #EDE8DC; }}
.px {{ width: 100%; max-width: 240px; height: auto; border: 1px solid var(--rule); image-rendering: pixelated; }}
.real {{ display: flex; gap: 22px; align-items: end; flex-wrap: wrap; }} .real span {{ display: grid; gap: 8px; justify-items: center; font: 400 11px var(--mono); color: var(--dim); }}
.lock {{ padding: 40px 30px; border: 1px solid var(--rule); background: #FBFAF6; display: grid; place-items: center; }}
.lock svg {{ width: 100%; max-width: 520px; height: auto; display: block; }}
.lock.st svg {{ max-width: 260px; }}
.fam {{ display: flex; gap: 40px; align-items: center; justify-content: center; padding: 44px 20px; border: 1px solid var(--rule); background: #FBFAF6; flex-wrap: wrap; }}
.fam > * {{ width: 128px; height: 128px; display: block; }}
.lat {{ width: 100%; height: auto; display: block; }}
.av {{ width: 48px; height: 48px; display: block; flex: none; border-radius: 4px; background: #DCDDD7; }}
.list {{ background: #fff; border: 1px solid var(--rule); border-radius: 10px; padding: 4px 16px; color: #191919; }}
.row {{ display: flex; gap: 12px; align-items: center; padding: 12px 0; border-bottom: 1px solid rgba(11,13,12,.08); }} .row:last-child {{ border-bottom: 0; }}
.row b {{ display: block; font: 500 15px/1.25 var(--sans); }} .row span {{ font-size: 12.5px; color: #666; }}
.row.ghost b {{ width: 120px; height: 10px; background: #E3E3DF; border-radius: 3px; margin-bottom: 7px; }} .row.ghost span {{ display: block; width: 70px; height: 8px; background: #EDEDEA; border-radius: 3px; }}
.page {{ background: #fff; border: 1px solid var(--rule); border-radius: 10px; overflow: hidden; color: #191919; }}
.page .ban {{ aspect-ratio: 1128 / 191; background: var(--ink); overflow: hidden; display: grid; align-items: center; }}
.page .ban svg {{ width: 140%; margin-left: -6%; opacity: 1; }}
.page .body {{ padding: 0 20px 20px; }}
.page .big {{ width: 96px; height: 96px; margin-top: -48px; border: 4px solid #fff; border-radius: 6px; background: var(--ink); padding: 14px; display: block; }}
.page .big svg {{ width: 100%; height: 100%; display: block; }}
.page b {{ display: block; font: 500 24px/1.2 var(--sans); margin-top: 10px; }} .page span {{ color: #555; font-size: 15px; }}
.strike {{ width: min(100%, 360px); height: auto; display: block; justify-self: center; cursor: pointer; }}
.strike .cut {{ animation: cut .55s cubic-bezier(.7,0,.2,1) forwards; }}
.strike .c1 {{ animation-delay: .5s; }} .strike .c2 {{ animation-delay: 1.05s; }} .strike .c3 {{ animation-delay: 1.6s; }}
.strike .gold {{ opacity: 0; animation: gold .7s ease 2.3s forwards; }}
@keyframes cut {{ to {{ stroke-dashoffset: 0; }} }} @keyframes gold {{ to {{ opacity: 1; }} }}
@media (prefers-reduced-motion: reduce) {{ .strike .cut {{ animation: none; stroke-dashoffset: 0; }} .strike .gold {{ animation: none; opacity: 1; }} }}
table {{ width: 100%; border-collapse: collapse; font-size: 15px; }} th, td {{ text-align: left; padding: 11px 12px; border-bottom: 1px solid var(--rule); vertical-align: top; }} th {{ font-weight: 500; width: 34%; }}
.alts {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
@media (max-width: 860px) {{ .hero, .two {{ grid-template-columns: 1fr; gap: 28px; }} .three {{ grid-template-columns: 1fr 1fr; }} .five {{ grid-template-columns: 1fr 1fr; }} .band {{ padding-block: 52px; }} .fam > * {{ width: 96px; height: 96px; }} }}
</style>

<section class="band ink"><div class="in hero">
  <div style="display:grid;gap:22px"><span class="eyebrow">Antimony, the mark</span><h1>The Crystal A.</h1>
  <p class="lede">A hexagon, the shape of antimony's crystal. Inside every hexagon there is already a triangle: join its alternate corners. We strike that triangle through the metal as an A. What is left in the middle, once everything else has been cut away, is the gold.</p></div>
  <div class="m">{mark(PAPER, SKY)}</div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">Construction</span>
  <h2>A hexagon, the triangle already inside it, and three numbers.</h2>
  <div class="two">{construction()}
    <div class="nums">
      <div><b>R 50</b><span>The hexagon's radius. Every point of the mark sits on it or is found from it.</span></div>
      <div><b>60°</b><span>The A's legs run from the top corner to the two lower side corners: an equilateral triangle, every angle 60 degrees. Nothing is drawn by eye.</span></div>
      <div><b>W 9</b><span>Each strike is 9 units wide, just under a fifth of the radius: wide enough to read at 16 pixels, narrow enough that the metal stays the subject.</span></div>
      <div><b>¾</b><span>The bar is struck three quarters of the way down the A, so the counter above it holds nine sixteenths of the triangle.</span></div>
      <div><b>4</b><span>Four pieces result: two wings, the counter and the foot. Three triangles and a pentagon.</span></div>
    </div>
  </div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">Five readings, all true</span>
  <h2>What it says, to anyone who looks for long enough.</h2>
  <div class="five">
    {reading(R1, "An A, struck", "Struck through solid metal like a hallmark: the stamp that says a metal has been tested and is true.")}
    {reading(R2, "The crystal", "Antimony crystallises in the trigonal system. Its symmetry is exactly this: a triangle inside a hexagon.")}
    {reading(R3, "The library", "Borges's Library of Babel is made of hexagonal galleries. Tile the mark and its strikes run on from room to room.")}
    {reading(R4, "The wolf", "Alchemists called antimony the wolf of metals. Struck through the top corner, the crystal keeps two ears; its lower point is the muzzle.")}
    {reading(R5, "The gold", "Antimony refined gold by consuming everything else. The counter is what is left, and it is the only colour.")}
  </div>
</div></section>

<section class="band ink"><div class="in">
  <span class="eyebrow">Motion</span>
  <h2>Struck three times. What is left turns to gold.</h2>
  <div class="two"><div id="strikebox">{strike()}</div><p class="dim">The mark is never drawn on; it is cut out. A solid crystal, the two legs struck, then the bar, then the counter lights. Every reveal, loader and transition in the system is a strike. Tap the mark to strike it again.</p></div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">Versions</span>
  <h2>One mark, every surface.</h2>
  <div class="three">
    <figure><div class="tile">{mark(INK, COBALT)}</div><figcaption>Primary: ink, the gold in cobalt.</figcaption></figure>
    <figure><div class="tile ink">{mark(PAPER, SKY)}</div><figcaption>Reversed: paper, the gold in sky.</figcaption></figure>
    <figure><div class="tile cob">{mark(PAPER, INK)}</div><figcaption>On cobalt: paper, the gold in ink.</figcaption></figure>
    <figure><div class="tile">{mark(INK, INK)}</div><figcaption>One colour. The counter needs no colour to read.</figcaption></figure>
    <figure><div class="tile stamp">{mark("#8E8A7E", "#8E8A7E", style="filter:drop-shadow(0 1px 0 rgba(255,255,255,.7)) drop-shadow(0 -1px 0 rgba(0,0,0,.18))")}</div><figcaption>Blind stamped, for paper and leather.</figcaption></figure>
    <figure><div class="tile skin">{mark("#23282A", line=1.4)}</div><figcaption>Fine line: four shapes, one outline each.</figcaption></figure>
  </div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">Small sizes</span>
  <h2>Drawn by hand at 16 and 32 pixels.</h2>
  <div class="two"><div class="real" style="gap:28px">{pixels(PX["16"])}{pixels(PX["32"])}</div>
    <div class="real"><span>{pixel_img(PX["16"])}16</span><span>{pixel_img(PX["32"])}32</span><span>{mark(INK, COBALT, style="width:48px;height:48px")}48</span><span>{mark(INK, COBALT, style="width:96px;height:96px")}96</span></div></div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">Lockups</span>
  <h2>With the wordmark, whose i is dotted with the gold.</h2>
  <div class="two"><figure><div class="lock">{lockup()}</div><figcaption>Horizontal. The mark stands 1.42 cap heights, centred on the cap height.</figcaption></figure>
  <figure><div class="lock st">{stacked()}</div><figcaption>Stacked.</figcaption></figure></div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">The family</span>
  <h2>Two pieces of the same metal, each struck with its own sign.</h2>
  <div class="fam">{mark(INK, COBALT)}<img src="orbe-mark.png" alt="The Orbe mark"></div>
  <p class="dim">Orbe is a block with its orb struck out; Antimony is a crystal with its A struck through. Solid, few parts, cut rather than drawn. Every product after Orbe follows the rule: one block of metal, one strike.</p>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">The system</span>
  <h2>Tiled, the strikes run on from crystal to crystal: the library.</h2>
  {lattice(8, 4, 100)}
  <p class="dim">Because the legs run corner to corner, a tiling of marks joins its strikes into one continuous lattice of triangles. It is the pattern for covers, packaging, the website's ground and the motion grid. One counter is lit; it is always the gold.</p>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">In use</span>
  <h2>Where people will meet it first.</h2>
  <div class="two">
    <figure><div class="list">{row(AV, "Antimony")}{GHOST}{GHOST}</div><figcaption>In a list, at real size.</figcaption></figure>
    <figure><div class="page"><div class="ban">{lattice(12, 2, 100, lit=(7, 0), fill="#1B2321")}</div><div class="body"><span class="big">{mark(PAPER, SKY)}</span><b>Antimony</b><span>Software for the people who make the work.</span></div></div><figcaption>A company page, the lattice as its cover.</figcaption></figure>
  </div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">The tests</span>
  <h2>How it does.</h2>
  <table><tbody>{"".join(f"<tr><th>{a}</th><td>{b}</td></tr>" for a, b in TESTS)}</tbody></table>
</div></section>

<script>
document.getElementById("strikebox").addEventListener("click", e => {{ const s = e.currentTarget.querySelector("svg"), c = s.cloneNode(true); s.replaceWith(c); }});
</script>
'''
open("../crystal/index.html", "w").write(html); print(len(html))
