"""Writes ../three/index.html: the three marks Eoin chose (the Break, the Seal, the Line), finished to an institutional
standard and tested where institutions show their marks."""
import math, os, sys, itertools, re
sys.path.insert(0, os.path.dirname(__file__))
from crystals import emblem, crystal as crystal_svg
INK, PAPER, SKY, COB, RED, BLACK, BONE = "#141311", "#F3F0E8", "#94E6FF", "#2448FF", "#E0262D", "#0A0A0B", "#ECE7DC"
uid = itertools.count()
f = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")
def poly(pts): return "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"
# ---------- the Break: a stone split at 16 degrees, a crystal grown in the break (the tile, refined) ----------
B = dict(ang=16, cy=51.5, gw=38.4, gh=60, pd=25.2, seam=7.5, mar=6.5, taper=.2)
def gem(cx, cy, w, h, pd): return [(cx, cy - h / 2), (cx + w / 2, cy - h / 2 + pd), (cx + w / 2, cy + h / 2 - pd), (cx, cy + h / 2), (cx - w / 2, cy + h / 2 - pd), (cx - w / 2, cy - h / 2 + pd)]
def break_parts(p=B, small=False):
    p = dict(p)
    if small: p.update(seam=p["seam"] + 2.5, mar=p["mar"] + 1.5, taper=.35)
    k = math.tan(math.radians(p["ang"])); cx, cy = 50, p["cy"]
    sk = lambda pts: [(x + (cy - y) * k, y) for x, y in pts]
    gw, gh, pd, s, m, t = p["gw"], p["gh"], p["pd"], p["seam"], p["mar"], p["taper"]
    cav = sk(gem(cx, cy, gw + m * 2, gh + m * 2.3, pd + m * .55))
    g = sk(gem(cx, cy, gw, gh, pd))
    seam = sk([(cx - s / 2 * t, -12), (cx + s / 2 * t, -12), (cx + s / 2, cy - gh / 2), (cx + s / 2, cy + gh / 2), (cx + s / 2 * t, 112), (cx - s / 2 * t, 112), (cx - s / 2, cy + gh / 2), (cx - s / 2, cy - gh / 2)])
    facet = sk([(cx, cy - gh / 2), (cx + gw / 2, cy - gh / 2 + pd), (cx + gw / 2, cy + gh / 2 - pd), (cx, cy + gh / 2)])
    return dict(cav=poly(cav), gem=poly(g), seam=poly(seam), facet=poly(facet))
CONT = {"tile": '<rect width="100" height="100" rx="22"/>', "round": '<circle cx="50" cy="50" r="50"/>',
        "orbe": '<path d="M36 0H95Q100 0 100 5V95Q100 100 95 100H5Q0 100 0 95V36Z"/>', "square": '<rect width="100" height="100" rx="3"/>'}
def brk(container="tile", stone=INK, ground=PAPER, lit=SKY, facet=True, small=False, style="", one=False):
    i = next(uid); q = break_parts(small=small)
    inner = (f'<rect width="100" height="100" fill="{ground}"/><rect width="100" height="100" fill="{stone}" mask="url(#bm{i})"/>'
             + (f'<path d="{q["gem"]}" fill="{lit}"/>' + (f'<path d="{q["facet"]}" fill="#fff" fill-opacity=".28"/>' if facet else "") if not one else
                f'<path d="{q["gem"]}" fill="{stone}"/><path d="{q["facet"]}" fill="{ground}" fill-opacity=".16"/>'))
    if ground == "none":
        inner = f'<rect width="100" height="100" fill="{stone}" mask="url(#bm{i})"/>' + (f'<path d="{q["gem"]}" fill="{lit}"/>' if not one else f'<path d="{q["gem"]}" fill="{stone}"/>')
        if facet and not one: inner += f'<path d="{q["facet"]}" fill="#fff" fill-opacity=".28"/>'
    return (f'<svg viewBox="0 0 100 100" style="{style}" aria-hidden="true"><defs><clipPath id="bc{i}">{CONT[container]}</clipPath>'
            f'<mask id="bm{i}"><rect width="100" height="100" fill="#fff"/><path d="{q["seam"]}" fill="#000"/><path d="{q["cav"]}" fill="#000"/></mask></defs>'
            f'<g clip-path="url(#bc{i})">{inner}</g></svg>')
# ---------- the Line: two crystals in one line weight, and the crystal A (monoline) ----------
def hexa(cx, cy, w, h, pd): return [(cx, cy - h / 2), (cx + w / 2, cy - h / 2 + pd), (cx + w / 2, cy + h / 2 - pd), (cx, cy + h / 2), (cx - w / 2, cy + h / 2 - pd), (cx - w / 2, cy - h / 2 + pd), (cx, cy - h / 2)]
def pl(pts): return f'<polyline points="{" ".join(f"{x:.2f},{y:.2f}" for x, y in pts)}"/>'
LINES = {"two": [hexa(38, 50, 40, 80, 20), hexa(62, 50, 40, 80, 20), [(50, 4), (50, 96)]],
         "crystalA": [hexa(50, 50, 66, 84, 26), [(17, 66), (50, 8), (83, 66)], [(33.5, 37), (66.5, 37)], [(50, 8), (50, 92)]]}
def line(key, col=INK, sw=4.4, style="", bg="none", lit=None):
    lt = ""
    if lit and key == "two":   # the lens where the two crystals overlap, in the light
        lt = f'<path d="{poly([(50, 18), (58, 34), (58, 66), (50, 82), (42, 66), (42, 34)])}" fill="{lit}"/>'
    if lit and key == "crystalA":
        lt = f'<path d="{poly([(50, 18), (61.5, 37), (38.5, 37)])}" fill="{lit}"/>'
    return (f'<svg viewBox="-4 -4 108 108" style="{style}{";background:" + bg if bg != "none" else ""}" aria-hidden="true">{lt}<g fill="none" stroke="{col}" stroke-width="{sw}" stroke-linecap="square" stroke-linejoin="miter" stroke-miterlimit="10">'
            + "".join(pl(s) for s in LINES[key]) + '</g></svg>')
def seal(fg=RED, bg=BLACK, accent=None, rough=True, style=""): return emblem("crystal", fg, bg, accent, True, rough, style)
# ---------- tests where institutions show their marks ----------
def emboss(svg_inner_mask, base="#1A1A1C", light="#D9D3C4", id_=None, w=100, h=100):
    """a mark pressed into a material: the shape raised by a specular light from the upper left"""
    i = id_ or next(uid)
    return (f'<filter id="em{i}" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur in="SourceAlpha" stdDeviation="1.1" result="b"/>'
            f'<feSpecularLighting in="b" surfaceScale="3.5" specularConstant=".9" specularExponent="22" lighting-color="{light}" result="s"><feDistantLight azimuth="225" elevation="42"/></feSpecularLighting>'
            f'<feComposite in="s" in2="SourceAlpha" operator="in" result="sc"/><feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="sc"/></feMerge></filter>'), f"em{i}"
def card(mark_paths_svg, label):
    flt, fid = emboss(None)
    return (f'<div class="card"><svg viewBox="0 0 856 540" aria-hidden="true"><defs>{flt}<linearGradient id="cg{fid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#232325"/><stop offset="1" stop-color="#0E0E10"/></linearGradient></defs>'
            f'<rect width="856" height="540" rx="38" fill="url(#cg{fid})"/><g transform="translate(64 60) scale(1.3)" filter="url(#{fid})">{mark_paths_svg}</g>'
            f'<text x="64" y="470" fill="#8F8B82" style="font: 500 30px \'Commit Mono\', monospace; letter-spacing: 6px">ANTIMONY</text>'
            f'<rect x="690" y="232" width="102" height="78" rx="12" fill="#C9B27A" opacity=".85"/></svg><span>{label}</span></div>')
def plaque(mark_svg_inner, label):
    flt, fid = emboss(None, light="#FFFFFF")
    return (f'<div class="plaque"><svg viewBox="0 0 600 380" aria-hidden="true"><defs>{flt}<filter id="st{fid}"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="3" seed="4"/><feColorMatrix values="0 0 0 0 .55  0 0 0 0 .54  0 0 0 0 .52  0 0 0 .35 0"/></filter></defs>'
            f'<rect width="600" height="380" fill="#B9B6AE"/><rect width="600" height="380" filter="url(#st{fid})"/>'
            f'<g transform="translate(230 70) scale(1.4)" filter="url(#{fid})">{mark_svg_inner}</g>'
            f'<text x="300" y="320" text-anchor="middle" fill="#7C7972" style="font: 400 34px \'Timeless Serif\', serif; letter-spacing: 14px">ANTIMONY</text></svg><span>{label}</span></div>')
def inner(svg):
    """place a whole mark inside another drawing at 100 by 100 units, whatever its own size rules say"""
    vb = re.search(r'viewBox="([^"]+)"', svg).group(1)
    body = svg[svg.index(">") + 1:svg.rindex("</svg>")]
    return f'<svg x="0" y="0" width="100" height="100" viewBox="{vb}" overflow="visible">{body}</svg>'

WORD = lambda col: f'<span class="wm" style="color:{col}">antimony</span>'
def lock(m, col=INK): return f'<div class="lk">{m}{WORD(col)}</div>'
ORBE = '<img src="orbe-mark.png" alt="The Orbe mark" class="orbe">'
# ---------- the page ----------
def section(n, title, idea, built, risks, score, marks, tests):
    return f'''<section class="band" id="{n}"><div class="in">
  <div class="top"><span class="k">0{n}</span><h2>{title}</h2><p class="idea">{idea}</p></div>
  <div class="hero">{marks}</div>
  <div class="tests">{tests}</div>
  <div class="facts"><div><b>Built</b><p>{built}</p></div><div><b>Could be mistaken for</b><p>{risks}</p></div><div><b>Honest score</b><p>{score}</p></div></div>
</div></section>'''
b_small = "".join(f'<i style="width:{s}px;height:{s}px">{brk(small=s < 30, style="width:100%;height:100%")}</i>' for s in (16, 24, 32, 48))
S1 = section(1, "The Break", "A stone split at sixteen degrees, the seam tapering like a real crack, and a crystal grown in the break. Antimony is what forms where the rock gives way: value found in the break, under pressure.",
    "A square stone with 22 unit corners on a 100 unit grid. The seam runs at 16 degrees and tapers to a point at both edges. The crystal is a long hexagon 38.4 by 60, its shoulders 25.2 down, its right half lit. Below 32 pixels the seam opens by 2.5 units and the cavity by 1.5 so the break still reads.",
    "Deutsche Bank's slash in a square (the closest risk, and the reason it reads as an institution). A lightning bolt, if the crystal is lost. Not a flame, a pin or a drop.",
    "8 out of 10. The only one that already reads as a company worth billions at app icon size. It needs a second, quieter form for print and buildings, shown in the one colour and Orbe cut versions.",
    f'<figure class="m">{brk(style="width:100%;height:100%")}<figcaption>The tile</figcaption></figure>'
    f'<figure class="m">{brk("round", style="width:100%;height:100%")}<figcaption>The round stone</figcaption></figure>'
    f'<figure class="m">{brk("orbe", style="width:100%;height:100%")}<figcaption>Cut from Orbe\'s block</figcaption></figure>'
    f'<figure class="m dk">{brk(stone=PAPER, ground=INK, one=True, style="width:100%;height:100%")}<figcaption>One colour</figcaption></figure>',
    card(inner(brk("square", stone="#2B2B2E", ground="none", lit="#3A3A3E", facet=False)), "Pressed into a metal card") +
    plaque(inner(brk("tile", stone="#A9A69E", ground="none", lit="#A9A69E", facet=False)), "Cut into stone") +
    f'<div class="pair"><div class="row">{brk(style="width:64px;height:64px")}{ORBE}</div>{lock(brk(style="width:44px;height:44px"))}<div class="sz">{b_small}</div><span>Beside Orbe, with the name, and at 16 to 48 pixels</span></div>')
s_small = "".join(f'<i style="width:{s}px;height:{s}px">{seal(rough=False, style="width:100%;height:100%")}</i>' for s in (16, 24, 32, 48))
S2 = section(2, "The Seal", "The crystal with the A struck through it, inside a ring: the emblem of a house, made to be stamped, sewn, engraved and worn. Arasaka and Ghost in the Shell, on our side of the table.",
    "A regular hexagon of radius 50, its own triangle struck through as an A with strikes 9 units wide and the bar three quarters down, set inside a ring of 5 units at 72 per cent. Name in tracked capitals beneath for ceremonial use only.",
    "The anarchy sign, an A in a circle. This is a real risk and the main reason it should be a seal for ceremonies rather than the everyday mark. Also a twenty sided die without the ring.",
    "7 out of 10 as a primary mark, 9 as a seal. It has the most presence of the three, and the most risk.",
    f'<figure class="m dk">{seal(style="width:100%;height:100%")}<figcaption>Red on black, worn</figcaption></figure>'
    f'<figure class="m">{seal(INK, PAPER, rough=False, style="width:100%;height:100%")}<figcaption>Ink on paper</figcaption></figure>'
    f'<figure class="m cb">{seal(BONE, COB, rough=False, style="width:100%;height:100%")}<figcaption>On cobalt</figcaption></figure>'
    f'<figure class="m dk">{crystal_svg("crystal", BONE, RED, "width:100%;height:100%")}<figcaption>The crystal alone</figcaption></figure>',
    card(inner(seal("#2B2B2E", "none", rough=False)), "Pressed into a metal card") +
    plaque(inner(seal("#A9A69E", "none", rough=False)), "Cut into stone") +
    f'<div class="pair"><div class="row">{seal(INK, PAPER, rough=False, style="width:64px;height:68px")}{ORBE}</div>{lock(crystal_svg("crystal", INK, COB, "width:44px;height:44px"))}<div class="sz">{s_small}</div><span>Beside Orbe, with the name, and at 16 to 48 pixels</span></div>')
l_small = "".join(f'<i style="width:{s}px;height:{s}px">{line("two", sw=4.4 * (1.8 if s < 30 else 1), lit=SKY, style="width:100%;height:100%")}</i>' for s in (16, 24, 32, 48))
S3 = section(3, "The Line", "Two crystals drawn in one line weight, overlapping on a single axis: two that make one, never alone. The overlap, the lens they share, is lit. Perplexity's discipline, applied to a crystal.",
    "Two hexagons 40 by 80, shoulders 20 down, their centres 24 apart, on one vertical axis that runs the full height. One stroke weight of 4.4 units; 8 units below 32 pixels. The shared lens is filled in sky.",
    "A gemstone or jewellery brand. Two overlapping shapes can recall a wedding ring motif. Nothing in technology owns it.",
    "7 out of 10. The most elegant and the most Perplexity, and the least likely to make you feel something at 16 pixels. Best as the line drawing of the system: diagrams, packaging, fine print.",
    f'<figure class="m">{line("two", lit=SKY, style="width:100%;height:100%")}<figcaption>Two crystals</figcaption></figure>'
    f'<figure class="m dk">{line("two", PAPER, lit=SKY, style="width:100%;height:100%")}<figcaption>On ink</figcaption></figure>'
    f'<figure class="m">{line("crystalA", lit=COB, style="width:100%;height:100%")}<figcaption>The crystal A</figcaption></figure>'
    f'<figure class="m cb">{line("crystalA", PAPER, lit=INK, style="width:100%;height:100%")}<figcaption>On cobalt</figcaption></figure>',
    card(inner(line("two", "#3A3A3E", sw=4.4)), "Pressed into a metal card") +
    plaque(inner(line("two", "#A9A69E", sw=4.4)), "Cut into stone") +
    f'<div class="pair"><div class="row">{line("two", lit=SKY, style="width:64px;height:64px")}{ORBE}</div>{lock(line("two", lit=SKY, style="width:44px;height:44px"))}<div class="sz">{l_small}</div><span>Beside Orbe, with the name, and at 16 to 48 pixels</span></div>')
html = f'''<title>Antimony, The Three</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* The three marks Eoin chose, finished and tested where institutions show their marks: a metal card, stone, an app icon, beside Orbe. */
@font-face {{ font-family: "Schibsted Grotesk"; src: url(sg.woff2) format("woff2"); font-weight: 400 900; font-display: swap; }}
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Commit Mono"; src: url(fonts/CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
:root {{ --paper: #E9E5DB; --card: {PAPER}; --ink: {INK}; --dim: #6A6760; --rule: rgba(20,19,17,.12); color-scheme: light; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: var(--paper); color: var(--ink); }}
body {{ font: 400 15.5px/1.55 "Schibsted Grotesk", "Helvetica Neue", Arial, sans-serif; -webkit-font-smoothing: antialiased; }}
.band {{ padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 64px; border-bottom: 1px solid var(--rule); }}
.in {{ max-width: 1180px; margin-inline: auto; display: grid; gap: 28px; }}
.k {{ font: 500 12px "Commit Mono", monospace; letter-spacing: .08em; color: var(--dim); }}
h1 {{ font: 700 clamp(40px, 6vw, 80px)/.98 "Schibsted Grotesk", sans-serif; letter-spacing: -.035em; max-width: 14em; text-wrap: balance; }}
h2 {{ font: 700 clamp(34px, 4.4vw, 56px)/1 "Schibsted Grotesk", sans-serif; letter-spacing: -.03em; }}
.lede, .idea {{ font-size: clamp(17px, 1.7vw, 20px); line-height: 1.5; max-width: 40em; color: #34322E; }}
.top {{ display: grid; gap: 10px; }}
.hero {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }}
.m {{ display: grid; gap: 8px; margin: 0; }} .m > svg {{ display: block; aspect-ratio: 1; width: 100%; height: auto; padding: 16%; background: var(--card); border-radius: 14px; }}
.m.dk > svg {{ background: #121212; }} .m.cb > svg {{ background: #2448FF; }}
figcaption {{ font: 500 12px "Commit Mono", monospace; color: var(--dim); }}
.tests {{ display: grid; grid-template-columns: 1.15fr 1fr 1fr; gap: 14px; align-items: start; }}
.card, .plaque, .pair {{ display: grid; gap: 8px; min-width: 0; }}
.card > svg, .plaque > svg {{ width: 100%; height: auto; display: block; border-radius: 14px; }}
.card span, .plaque span, .pair > span {{ font: 500 12px "Commit Mono", monospace; color: var(--dim); }}
.pair {{ background: var(--card); border-radius: 14px; padding: 18px; gap: 16px; align-content: start; }}
.pair .row {{ display: flex; gap: 18px; align-items: center; }} .orbe {{ width: 64px; height: 64px; display: block; }}
.lk {{ display: flex; gap: 12px; align-items: center; }} .lk svg {{ flex: none; display: block; }}
.wm {{ font: 700 40px/1 "Schibsted Grotesk", sans-serif; letter-spacing: -.045em; }}
.sz {{ display: flex; gap: 14px; align-items: end; }} .sz i {{ display: block; flex: none; }}
.facts {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0; border-top: 1px solid var(--rule); }}
.facts div {{ padding: 16px 18px 0 0; display: grid; gap: 6px; align-content: start; }} .facts b {{ font: 500 12px "Commit Mono", monospace; letter-spacing: .06em; text-transform: uppercase; color: var(--dim); }}
.facts p {{ font-size: 14.5px; color: #34322E; }}
.verdict {{ display: grid; gap: 14px; }} .verdict p {{ max-width: 46em; font-size: 17px; }}
@media (max-width: 900px) {{ .hero {{ grid-template-columns: 1fr 1fr; }} .tests, .facts {{ grid-template-columns: 1fr; }} .facts div {{ padding-right: 0; }} .band {{ padding-block: 48px; }} }}
</style>
<section class="band"><div class="in">
  <span class="k">Antimony, the mark, the three you chose</span>
  <h1>The Break, the Seal and the Line, finished.</h1>
  <p class="lede">These are the three you picked out as better than anything since: the tile with the crystal grown in the break, the crystal A in its ring, and the two crystals in one line. Nothing new has been added. Each is finished and tested where wealth and institutions show their marks: pressed into a metal card, cut into stone, as an app icon, beside Orbe, with the name and at 16 pixels. Each has an honest score and an honest list of what it could be mistaken for.</p>
</div></section>
{S1}{S2}{S3}
<section class="band"><div class="in verdict">
  <span class="k">My recommendation</span>
  <h2>One family, three jobs.</h2>
  <p>The Break is the mark: the app icon, the avatar, the product, the thing people will know us by. It is the only one of the three that already reads as a company of real scale at 16 pixels, and it pairs with Orbe because both are solid blocks with something cut from them.</p>
  <p>The Seal is the house emblem: for the letters, the certificates, the side of a building, a ring. Kept for ceremony, its risk of reading as the anarchy sign stays small.</p>
  <p>The Line is the drawing: the fine line version of the crystal for diagrams, packaging and the moments that should be quiet.</p>
  <p>If you agree, I take the Break alone to the level of Perplexity's guidelines next, with the Seal and the Line as its named family members, and drop everything else.</p>
</div></section>
'''
open("../three/index.html", "w").write(html); print(len(html))
