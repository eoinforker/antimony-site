"""The chapters of the Antimony brand guidelines."""
import json, math, os
import geo as g
import gsite as S
from gsite import section, sub, pan, fig, intro, toc, pill, chapter_head, esc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "../../guidelines"))
KITZIP = "downloads/antimony-kit-v3.zip"

def zip_mb():
    p = os.path.join(OUT, KITZIP)
    return f"{os.path.getsize(p) / 1e6:.0f} MB" if os.path.exists(p) else ""

# ---------- colour arithmetic ----------
def rgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
def lum(h):
    c = [v / 255 for v in rgb(h)]
    c = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]
def ratio(a, b):
    x, y = sorted((lum(a), lum(b)), reverse=True); return (x + .05) / (y + .05)
def grade(r): return "AAA" if r >= 7 else "AA" if r >= 4.5 else "AA large" if r >= 3 else "not for text"

def _lin(v): v /= 255; return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
def _gam(v): v = max(0, min(1, v)); return 255 * (12.92 * v if v <= .0031308 else 1.055 * v ** (1 / 2.4) - .055)
def oklab(h):
    r, g_, b = (_lin(v) for v in rgb(h))
    l = (.4122214708 * r + .5363325363 * g_ + .0514459929 * b) ** (1 / 3); m = (.2119034982 * r + .6806995451 * g_ + .1073969566 * b) ** (1 / 3)
    s = (.0883024619 * r + .2817188376 * g_ + .6299787005 * b) ** (1 / 3)
    return (.2104542553 * l + .793617785 * m - .0040720468 * s, 1.9779984951 * l - 2.428592205 * m + .4505937099 * s, .0259040371 * l + .7827717662 * m - .808675766 * s)
def from_oklab(L, a, b):
    l = (L + .3963377774 * a + .2158037573 * b) ** 3; m = (L - .1055613458 * a - .0638541728 * b) ** 3; s = (L - .0894841775 * a - 1.291485548 * b) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + .2309699292 * s; g_ = -1.2684380046 * l + 2.6097574011 * m - .3413193965 * s; bb = -.0041960863 * l - .7034186147 * m + 1.707614701 * s
    return "#" + "".join(f"{round(_gam(v)):02X}" for v in (r, g_, bb))
def mix_ok(a, b, t):
    A, B = oklab(a), oklab(b); return from_oklab(*(A[i] + (B[i] - A[i]) * t for i in range(3)))

# sky runs from near white, through the crystal's light, down to Prussian, the way the water in the crystal deepens
SKY_RAMP = [("Sky 100", mix_ok("#FFFFFF", g.SKY, .22)), ("Sky 200", mix_ok("#FFFFFF", g.SKY, .55)), ("Sky 300", g.SKY),
            ("Sky 400", mix_ok(g.SKY, g.PRU, .22)), ("Sky 500", mix_ok(g.SKY, g.PRU, .42)), ("Sky 600", mix_ok(g.SKY, g.PRU, .62)),
            ("Sky 700", mix_ok(g.SKY, g.PRU, .82)), ("Sky 800", g.PRU), ("Sky 900", mix_ok(g.PRU, g.INK, .55))]
STONE_RAMP = [(f"Stone {n}", mix_ok(g.CREAM, g.STONE, t)) for n, t in ((100, .1), (200, .24), (300, .38), (400, .52), (500, .64), (600, .75), (700, .85), (800, .93))] + [("Stone 900", g.STONE)]

# ---------- small drawings ----------
def tagline(cls="mono"): return f'<span class="{cls}">Software for the people who make the work</span>'

def huge_line(colour, style, sw=1.1, op=1):
    return f'<div style="position:absolute;{style};opacity:{op}">{g.line_mark(colour, sw, nonscaling=True, style="width:100%;height:100%;overflow:visible", label="")}</div>'

def w(svg, width):  # an svg at a share of its panel's width
    return f'<div class="art" style="width:{width}">{svg}</div>'

# =====================================================================================
def cover():
    b = ('<header class="head cover"><img src="img/tex/stipple-panel.png" alt="" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.6">'
         + huge_line(g.SKY, "right:-14vw;top:-8vw;width:min(78vw,1180px);aspect-ratio:1", 1.1, .9)
         + '<div class="wrap"><div class="g12 bar"><a class="home" href="index.html" aria-label="Antimony brand guidelines">'
         + g.caps(g.CREAM, g.SKY, style="width:100%;height:auto") + '</a><span class="title">Brand guidelines</span></div>'
         + '<h1 class="big">Brand<br>Guidelines</h1></div></header>')
    b += ('<section class="wrap"><div class="g12 intro"><p class="st" style="grid-column:1/7">A stone split open, with a crystal of light grown in the break. Everything here is drawn from that one idea.</p>'
          '<div style="grid-column:7/11;display:grid;gap:1em;font-size:16px;line-height:1.46;padding-top:6px">'
          '<p>Antimony makes software for the people who make the work. These pages show how the company looks, moves and speaks, so that anyone who builds with the brand can make something we would recognise as ours.</p>'
          '<p>They are written as reasons, not only rules. Where a page gives a number, use it. Where it gives a reason, use your judgement. When in doubt, take something away.</p></div></div></section>')
    rows = [("logo", "Logo", "The Break, its readings, lockups, wordmarks and construction."), ("type", "Typography", "Timeless Serif, the drawn wordmarks, and Commit Mono for callouts."),
            ("colour", "Colour", "Cream, stone, ink and one light: sky. Prussian, cobalt and washi."), ("motion", "Motion", "The opening, beat by beat; the water and the chipped stone."),
            ("art", "Art direction", "Grain, halftone, stippled light, the character field, hairlines."), ("use", "Brand in use", "Social, posters, print, slides and email, at true size."),
            ("downloads", "Downloads", "The kit: masters, exports, icons, social images and posters.")]
    b += ('<section class="wrap sec" id="contents" style="padding-top:150px"><div class="g12"><h2 class="lab">Contents</h2></div><ol class="contents">'
          + "".join(f'<li><a href="{s}.html"><span class="n">{i + 1:02d}</span><span class="t">{t}</span><span class="d">{d}</span></a></li>' for i, (s, t, d) in enumerate(rows))
          + '</ol></section>')
    css = ('<style>.contents{list-style:none;margin-top:28px}.contents a{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));column-gap:var(--gap);align-items:baseline;text-decoration:none;'
           'border-top:1px solid var(--hair);padding:12px 0 16px}.contents li:last-child a{border-bottom:1px solid var(--hair)}'
           '.contents .n{grid-column:1/3;font:400 clamp(44px,6.4vw,96px)/1 var(--serif);letter-spacing:-.03em}.contents .t{grid-column:3/9;font:400 clamp(44px,6.4vw,96px)/1 var(--serif);letter-spacing:-.035em}'
           '.contents .d{grid-column:9/13;font-size:15px;color:var(--dim);align-self:center}.contents a:hover .t{color:var(--pru)}'
           '@media(max-width:760px){.contents a{grid-template-columns:3.2em minmax(0,1fr);row-gap:6px}.contents .n,.contents .t{font-size:40px}.contents .n{grid-column:1/2!important}.contents .t{grid-column:2/3!important}.contents .d{grid-column:2/3!important;font-size:14px}}</style>')
    return S.page("index", "Antimony brand guidelines", "How Antimony looks, moves and speaks.", css + b)

# =====================================================================================
def readings_panel():
    names = [("stone", "Stone"), ("seam", "Seam, 16°"), ("cavity", "Cavity"), ("crystal", "Crystal"), ("light", "Light")]
    cells = ""
    for i, (k, n) in enumerate(names):
        cells += (f'<div style="display:grid;justify-items:center;gap:26px;min-width:0"><div style="width:100%;max-width:190px">{g.reading(k)}</div>'
                  f'<span class="mono" style="font-size:10.5px;opacity:.85">{n}</span></div>')
        if i < 4: cells += '<span aria-hidden="true" style="font:300 18px var(--mono);opacity:.5;align-self:center;margin-top:-40px">+</span>'
    return pan(f'<div class="rd" style="display:grid;grid-template-columns:1fr auto 1fr auto 1fr auto 1fr auto 1fr;gap:2.4%;width:88%;align-items:start">{cells}</div>', "i", "wide rdp",
               label="The mark read five ways: stone, seam, cavity, crystal and light, each drawn in sky over the whole")

def construction():
    """The Break with its true measurements, read from break-geometry.json."""
    P = g.P; t = math.tan(math.radians(16))
    lab = lambda x, y, s, a="start", c=g.PRU: f'<text x="{x}" y="{y}" text-anchor="{a}" fill="{c}">{s}</text>'
    ln = lambda d, c=g.INK, sw=.22, da="": f'<path d="{d}" stroke="{c}" stroke-width="{sw}" fill="none"{f" stroke-dasharray={chr(34)}{da}{chr(34)}" if da else ""}/>'
    q = g.Q
    out = '<svg viewBox="-64 -14 250 126" role="img" aria-label="Construction of the Break, with its measurements" style="width:100%;height:auto;font:400 2.5px var(--mono);letter-spacing:.04em">'
    out += f'<g opacity=".1">{g.mark_body()}</g>'
    out += ln("M0 22A22 22 0 0 1 22 0H78A22 22 0 0 1 100 22V78A22 22 0 0 1 78 100H22A22 22 0 0 1 0 78Z", g.INK, .25)
    out += "".join(ln(h, g.INK, .3) for h in q["halves"]) + ln(q["gem"], g.PRU, .4) + ln(q["cav"], g.INK, .22, ".8 .7")
    out += ln(g.seam_line(), g.PRU, .2, "1.6 1") + ln("M68.78 -14V112", g.INK, .14, ".5 .7") + ln("M68.78 -4A10 10 0 0 1 66.02 -4.39", g.PRU, .25) + lab(70, -6.4, "16°")
    out += ln("M-6 51.5H106", g.INK, .14, ".5 .7") + ln("M50 47V56M45.5 51.5H54.5", g.PRU, .25) + lab(54.5, 55.6, "50, 51.5")
    # tile width, radius
    out += ln("M0 -9H100M0 -10.5V-7.5M100 -10.5V-7.5", g.INK, .22) + lab(50, -10.6, "100", "middle", g.INK)
    out += ln("M-7 0V22M-8.5 0H-5.5M-8.5 22H-5.5", g.INK, .22) + lab(-9.5, 12, "r 22", "end", g.INK)
    # crystal height and shoulders
    out += ln("M112 21.5V81.5M110.5 21.5H113.5M110.5 81.5H113.5", g.INK, .22) + ln("M58.6 21.5H112M41.4 81.5H112", g.INK, .12, ".4 .6") + lab(115, 52.5, "crystal 60 tall", "start", g.INK)
    out += ln("M122 21.5V46.7M120.5 46.7H123.5M120.5 21.5H123.5", g.PRU, .22) + ln("M70.58 46.7H122", g.PRU, .12, ".4 .6") + lab(125, 35, "shoulder 25.2")
    out += ln("M32.18 44.3H70.58M32.18 43V45.6M70.58 43V45.6", g.PRU, .22) + lab(51.4, 42.6, "38.4", "middle")
    # seam and cavity callouts
    out += ln("M54.85 21.5H62.35", g.PRU, .3) + ln("M58.6 21.5L58.6 9L84 9", g.PRU, .14) + lab(85, 9.8, "seam 7.5 beside the crystal")
    out += ln("M62.94 0H66.59", g.INK, .3) + ln("M64.8 0V-3.4H84", g.INK, .14) + lab(85, -2.6, "3.65 where it leaves the stone", "start", g.INK)
    out += ln("M58.6 21.5V14.02", g.INK, .3) + ln("M78.19 42.8L90 66H112", g.INK, .14) + lab(115, 68.2, "cavity: 7.5 clear at the points,", "start", g.INK) + lab(115, 71.6, "4.3 at its narrowest", "start", g.INK)
    out += ln("M62 60L74 92H112", g.PRU, .14) + lab(115, 93.2, "facet: the right half, white at 28%")
    out += lab(-52, 92, "points move by", "start", g.INK) + lab(-52, 95.4, "(51.5 minus y) × tan 16°", "start", g.INK) + lab(-52, 98.8, "in x", "start", g.INK)
    return out + "</svg>"

def clearspace():
    s = 22
    out = f'<svg viewBox="-36 -36 {423.5 + 72} 174" role="img" aria-label="Clear space around the primary lockup" style="width:100%;height:auto;font:400 6px var(--mono)">'
    out += f'<rect x="-22" y="-22" width="{423.5 + 44}" height="144" fill="none" stroke="{g.PRU}" stroke-width=".6" stroke-dasharray="3 2"/>'
    out += f'<g>{g.lockup(g.CREAM).replace("<svg ", "<svg x=\"0\" y=\"-1\" width=\"425.5\" height=\"102\" ", 1)}</g>'
    for x, y in ((-22, 39), (423.5, 39), (39, -22), (39, 100)):
        out += f'<rect x="{x}" y="{y}" width="22" height="22" fill="{g.SKY}" fill-opacity=".55"/><text x="{x + 11}" y="{y + 13.2}" text-anchor="middle" fill="{g.PRU}">22</text>'
    return out + "</svg>"

def min_sizes():
    items = [(f'<div style="width:16px">{g.mark(small=True)}</div>', "16 px", "Symbol, smallest. Below 30 px use the small drawing."),
             (f'<div style="width:32px">{g.mark(small=False)}</div>', "32 px", "Symbol, the drawing as standard from here."),
             (f'<div style="width:180px">{g.lockup(g.CREAM)}</div>', "180 px", "Primary lockup, smallest. 40 mm in print."),
             (f'<div style="width:120px">{g.stacked(g.CREAM)}</div>', "120 px", "Stacked lockup, smallest. 26 mm in print."),
             (f'<div style="width:120px">{g.caps(g.INK, g.PRU)}</div>', "120 px", "Capitals alone. 25 mm in print."),
             (f'<div style="width:72px">{g.serif(g.INK, g.PRU, heavy=True)}</div>', "72 px", "Lower case. Below 96 px use the heavy drawing.")]
    cells = "".join(f'<div style="display:grid;grid-template-rows:120px auto auto;gap:6px;min-width:0"><div style="display:flex;align-items:flex-end">{a}</div>'
                    f'<b class="mono" style="font-size:10.5px;color:var(--pru)">{b}</b><span style="font-size:13.5px;color:var(--dim)">{c}</span></div>' for a, b, c in items)
    return f'<div class="pan c" style="aspect-ratio:auto;padding:36px 4%"><div class="ms" style="display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:28px;width:100%">{cells}</div></div>'

def dont_list():
    st = "width:100%;height:100%"
    def tile(svg, kind="c"): return pan(f'<div class="art" style="width:42%">{svg}</div>', kind, "sq")
    D = [
        (tile(g.mark(g.CREAM, g.SKY, facet=True), "i"), "Don't set a pale tile on black.", "The stone is always dark. On dark grounds use the full colour mark, whose cut edges catch the light, or the line mark."),
        (tile(g.mark(style="transform:rotate(-24deg)")), "Don't rotate it.", "The seam is always sixteen degrees from upright, leaning the same way."),
        (tile(g.mark(style="transform:scaleX(1.34)")), "Don't stretch it.", "The mark is a square. Scale it only as a whole."),
        (tile(g.mark(crystal="#E3A33B")), "Don't recolour the crystal.", "The crystal holds sky, or the moving water on screen, and nothing else."),
        (tile(g.mark(stone=g.COB)), "Don't colour the stone.", "Stone is dark. A bright stone reads as a button, not a mineral."),
        (tile(g._svg("0 0 100 100", f'<rect width="100" height="100" rx="22" fill="{g.STONE}"/><path d="{g.Q["cav"]}" fill="{g.CREAM}"/><path d="{g.Q["gem"]}" fill="{g.SKY}"/><path d="{g.Q["facet"]}" fill="#fff" fill-opacity=".28"/>')),
         "Don't close the seam.", "Without the break there is no crystal. The seam always runs edge to edge."),
        (tile(g.line_mark(g.INK, 5.2)), "Don't make the lines heavy.", "The line mark has one hairline weight. If it starts to look like the solid mark, use the solid mark."),
        (pan(f'<div class="art" style="width:74%;position:relative">{g.lockup(g.CREAM)}<span style="position:absolute;left:31.5%;top:-30%;font:600 15px/1 var(--serif);white-space:nowrap">Now in beta</span><span style="position:absolute;left:2%;top:100%;margin-top:4px;font:400 9px var(--mono);letter-spacing:.1em">SOFTWARE FOR THE PEOPLE</span></div>', "c", "sq"),
         "Don't crowd it.", "Keep 22 units clear on every side. Nothing enters that space: not type, not other marks, not the edge of the page."),
    ]
    return '<div class="r4">' + "".join(fig(p, t, d) for p, t, d in D) + "</div>"

def logo():
    secs = [("about", "About the mark"), ("primary", "Primary lockup"), ("stacked", "Stacked lockup"), ("symbol", "Symbol"), ("wordmarks", "Wordmarks"),
            ("full-colour", "Full colour"), ("one-colour", "One colour"), ("line", "Line mark"), ("element", "Mark as a design element"), ("construction", "Construction"),
            ("space", "Clear space and size"), ("products", "Product lockups"), ("dont", "What not to do")]
    b = chapter_head("logo", "Logo") + toc("Logo", secs)
    b += intro("Our mark is a dark stone split by a seam, with a crystal grown in the break. It appears everywhere, from a browser tab to the side of a poster, so every point in it is measured.",
               pill(KITZIP, "Download all logo files"))
    b += section("about", "About the mark",
        "<p>Antimony is element 51. Its ore, stibnite, grows in long grey crystals, and for centuries it was used to refine gold. Our mark is a piece of that stone, split open.</p>",
        "<p>It reads five ways, and each reading is a part of the drawing: the stone, the seam at sixteen degrees, the cavity cut around the crystal, the crystal, and the light it holds.</p>",
        readings_panel() + '<div class="r5">' + "".join(f'<figure><figcaption><b>{a}</b>{b_}</figcaption></figure>' for a, b_ in [
            ("The stone", "A tile of dark stone, 100 units square with corners of 22. It is the container, and it is always dark."),
            ("The seam, 16°", "The break runs at sixteen degrees from upright, the way a cleaved mineral parts. Everything in the mark leans with it."),
            ("The cavity", "The stone is cut back around the crystal so the two never touch. On paper the cavity shows the ground."),
            ("The crystal", "A six sided prism, 60 units tall, sheared to the seam's angle. It is the only colour in the mark."),
            ("The light", "The crystal's right half catches the light, white at 28 per cent. On screen the crystal holds moving water.")]) + "</div>")
    b += section("primary", "Primary lockup",
        "<p>The mark beside the capitals. Use it wherever Antimony is introduced: the website, a letterhead, the first slide, the end of a film.</p>",
        "<p>The capitals stand at 0.22 of the mark's height, centred on it, with 0.34 of the mark between them. Use light colours on dark grounds and dark on light, always.</p>",
        '<div class="r2">' + pan(w(g.lockup(g.CREAM), "64%"), "c") + pan(w(g.lockup(g.INK), "64%"), "i") + "</div>")
    b += section("stacked", "Stacked lockup",
        "<p>The mark above the capitals, as the website opens. It can stand in for the primary lockup on almost anything: a poster, a card, a cover.</p>",
        "<p>Whenever you use it, centre it on the page or the panel. The capitals run 1.36 times the mark's width, 0.37 of the mark below it.</p>",
        '<div class="r2">' + pan(w(g.stacked(g.CREAM), "24%"), "c") + pan(w(g.stacked(g.INK), "24%"), "i") + "</div>")
    b += section("symbol", "Symbol",
        "<p>The mark can stand alone wherever the name is already present or there is no room for it: avatars, app icons, favicons, the foot of a page.</p>",
        "<p>We also use the symbol as a design element, drawn in line, huge and thin. See the mark as a design element, below.</p>",
        '<div class="r4">' + pan(w(g.mark(), "40%"), "c", "sq") + pan(w(g.mark(light=True), "40%"), "w", "sq", tag_r="with light")
        + pan(w(g.mark(**g.mark_for(g.INK)), "40%"), "i", "sq") + pan(w(g.mark(**g.mark_for(g.PRU)), "40%"), "p", "sq") + "</div>")
    wm_rows = [("Capitals, primary", "Timeless Serif capitals, tracked wide and spaced by eye: the A sits closer to the N, the T and I a touch tighter. The A is cut as a crystal; its counter is filled with Prussian on paper and sky on dark grounds.",
                g.caps(g.INK, g.PRU), g.caps(g.CREAM, g.SKY), "58%"),
               ("Lower case", "Drawn from Timeless Serif. Three changes make it ours: the tittle of the i is a small crystal, the t joins the i, and the tail of the y is cut on the crystal's angle. For footers, documents and wherever the name is said rather than announced.",
                g.serif(g.INK, g.PRU), g.serif(g.CREAM, g.SKY), "46%"),
               ("Heavy", "The lower case thickened by ten units of its 1000. For small sizes, low resolution screens and print below 8 mm high, where the regular drawing would thin out.",
                g.serif(g.INK, g.PRU, heavy=True), g.serif(g.CREAM, g.SKY, heavy=True), "46%"),
               ("Title case", "Antimony with the crystal A, for places that read as a sentence: a book spine, a sign off, a title page.",
                g.title(g.INK, g.PRU), g.title(g.CREAM, g.SKY), "46%")]
    b += section("wordmarks", "Wordmarks",
        "<p>Four wordmarks, each drawn, never typed. The capitals are the primary wordmark. The others are for places where the capitals would be too quiet or too formal.</p>",
        "<p>Use a wordmark alone where the symbol already appears, or where the full lockup would repeat itself: the foot of a document, the last slide, a footer.</p>",
        "".join(sub(n, f"<p>{d}</p>", '<div class="r2">' + pan(w(a, ws), "c", "slim") + pan(w(c, ws), "i", "slim") + "</div>") for n, d, a, c, ws in wm_rows))
    b += section("full-colour", "Full colour",
        "<p>Dark stone and a sky crystal. This is the mark we reach for first, on our own channels and wherever colour is possible.</p>",
        "<p>The stone keeps its colour on every ground. On ink and Prussian its cut edges carry a hairline of light, so it never sinks into the ground. On screen, at large sizes, the crystal may hold the moving water, as on the website.</p>",
        '<div class="r2">' + "".join(pan(w(g.lockup(gc), "62%"), k, tag=n) for n, gc, k in (("cream", g.CREAM, "c"), ("ink", g.INK, "i"), ("Prussian", g.PRU, "p"), ("washi", g.WASHI, "w"))) + "</div>")
    b += section("one-colour", "One colour",
        "<p>For one ink: a single colour print, engraving, embossing, a stamp. On light grounds the stone and the crystal take the same ink, and the cavity keeps them apart.</p>",
        "<p>On dark grounds, the one colour version is the line mark. A solid pale tile on a dark ground is never used.</p>",
        '<div class="r2">' + pan(w(g.lockup(one=g.INK), "62%"), "c", tag="ink on cream") + pan(w(g.lockup(one=g.PRU), "62%"), "w", tag="Prussian on washi")
        + pan(w(g.lockup(one=g.CREAM), "62%"), "i", tag="cream line on ink") + pan(w(g.lockup(one=g.CREAM), "62%"), "p", tag="cream line on Prussian") + "</div>")
    b += section("line", "Line mark",
        "<p>The Break drawn in outline: one hairline weight, rounded joins, and nothing filled, so whatever lies behind it shows through.</p>",
        "<p>Draw it in cream on ink or in ink on cream. At small sizes the line is one unit of the mark's 100; drawn large, it stays a single hairline.</p>",
        '<div class="r2">' + pan(w(g.line_mark(g.CREAM, 1.0), "34%"), "i") + pan(w(g.line_mark(g.INK, 1.0), "34%"), "c") + "</div>")
    b += section("element", "Mark as a design element",
        "<p>The line mark can be drawn huge and thin, running off the edges, over our water light, stone, characters or paper. It adds depth without adding things.</p>",
        "<p>Keep the line a hairline and the layout quiet. Use it once per layout, and use the wordmark, not the symbol, anywhere else on the same page.</p>",
        '<div class="r3">'
        + pan('<img class="fill" src="img/tex/light-panel.jpg" alt="">' + huge_line("#FFFFFF", "left:-34%;top:6%;width:168%;aspect-ratio:1", 1.1, .95)
              + f'<div style="position:absolute;left:7%;bottom:6%;width:46%">{g.serif(g.CREAM, g.SKY)}</div>', "k", "tall")
        + pan(huge_line(g.PRU, "left:12%;top:34%;width:130%;aspect-ratio:1", 1.1, .9)
              + f'<div style="position:absolute;left:7%;top:5%;right:7%">{g.serif(g.INK, g.PRU)}</div><div style="position:absolute;left:7%;right:7%;top:25%;border-top:1px solid var(--ink)"></div>', "c", "tall")
        + pan('<img class="fill" src="img/tex/chars-panel.png" alt="" style="opacity:.5">' + huge_line(g.SKY, "left:-50%;top:12%;width:200%;aspect-ratio:1", 1.1, .95)
              + f'<div style="position:absolute;left:7%;top:6%;right:7%">{g.caps(g.CREAM, g.SKY)}</div>', "i", "tall")
        + "</div>")
    b += section("construction", "Construction",
        "<p>Every point is found from a handful of numbers on a square of 100 units. Nothing is placed by eye. The masters in the kit are drawn from these numbers, and so is the website.</p>",
        "<p>Below 30 pixels the mark changes, not just shrinks: the seam widens to 10 and the cavity to 9.2 at the points, so the break still reads at a glance.</p>",
        pan(f'<div class="art" style="width:90%">{construction()}</div>', "c cons", style="aspect-ratio:16/9")
        + '<div class="facts">' + "".join(f"<div><b>{a}</b><span>{c}</span></div>" for a, c in [
            ("100, r 22", "The tile, and the radius of its corners."),
            ("16°", "The seam's angle from upright. The crystal is sheared to the same angle: each point moves by (51.5 minus y) times tan 16° in x."),
            ("50, 51.5", "The crystal's centre, 1.5 below the middle, so it sits rather than floats."),
            ("60 × 38.4", "The crystal: 60 tall, 38.4 across at the shoulders, which are 25.2 from each point."),
            ("7.5 to 3.65", "The seam: 7.5 wide beside the crystal, thinning to 3.65 where it leaves the stone, and on to a fifth of 7.5 beyond the edge."),
            ("7.5 and 4.3", "The cavity: the crystal grown outward, 7.5 clear at its points and 4.3 at its narrowest."),
            ("28%", "The facet, the crystal's right half, lit with white at 28 per cent."),
            ("10, 9.2", "The small drawing, for 16 to 30 pixels: seam 10 wide beside the crystal, cavity 9.2 clear at the points.")]) + "</div>")
    b += section("space", "Clear space and size",
        "<p>Keep 22 units clear on every side, the radius of the tile's corner: a little over a fifth of the mark. Nothing enters it. The same measure holds for the symbol, the lockups and the wordmarks.</p>",
        "<p>The smallest sizes, shown below at their true size on screen. Smaller than this, the seam closes up and the capitals blur.</p>",
        pan(f'<div class="art" style="width:72%">{clearspace()}</div>', "c", style="aspect-ratio:auto;padding:5% 0") + min_sizes())
    b += section("products", "Product lockups",
        "<p>Each product keeps its own mark and its own name. Where its maker needs naming, the product lockup adds <i>by Antimony</i> in Timeless Serif Light, at the product's x-height.</p>",
        "<p>The suffix is Prussian on paper and sky on dark grounds. It says who makes the product, and nothing more. Never join our mark to another company's, and never use a lockup to suggest a partnership.</p>",
        '<div class="r2">' + pan(w(g.product(g.CREAM), "66%"), "c") + pan(w(g.product(g.INK), "66%"), "i") + "</div>")
    b += section("dont", "What not to do",
        "<p>Beyond the usual rules for any mark (do not warp it, do not add shadows or glows), eight that belong to this one, each drawn as it would go wrong.</p>", "",
        dont_list())
    return S.page("logo", "Logo, Antimony brand guidelines", "The Break: readings, lockups, wordmarks, colour versions, construction and clear space.", b)

# =====================================================================================
AZ = "ABCDEFGHIJKLMNOPQRSTUVWXYZ<br>abcdefghijklmnopqrstuvwxyz<br>0123456789<br>&amp;!?@£€%()[]*+=/"

def annotated_wordmark():
    t = math.tan(math.radians(16))
    lab = lambda x, y, s, a="start": f'<text x="{x}" y="{y}" text-anchor="{a}">{s}</text>'
    out = ('<svg viewBox="-300 -1150 4700 1720" role="img" aria-label="The lower case wordmark, with its three drawn changes marked" style="width:100%;height:auto">'
           f'<g stroke="{g.PRU}" stroke-width="3" fill="none" opacity=".55"><path d="M-240 0H4380" stroke-dasharray="14 12"/><path d="M-240 -500H4380" stroke-dasharray="14 12"/></g>'
           f'<g font-family="Commit Mono, monospace" font-size="54" letter-spacing="5" fill="{g.PRU}">{lab(-240, -520, "X HEIGHT 500")}{lab(-240, -20, "BASELINE")}</g>'
           + g.serif_body(g.INK, g.PRU)
           + f'<g stroke="{g.PRU}" stroke-width="4" fill="none"><path d="M1547 -770V-950"/><path d="M1382 -500V-950"/><path d="M3812 232V390"/>'
           f'<path d="M{3812 - 200 * t:.0f} {232 - 200} L{3812 + 120 * t:.0f} {232 + 120}" stroke-dasharray="12 10"/></g>'
           f'<g font-family="Commit Mono, monospace" font-size="58" letter-spacing="6" fill="{g.PRU}">'
           + lab(1580, -990, "THE TITTLE IS A CRYSTAL") + lab(1350, -990, "THE T JOINS THE I", "end") + lab(3780, 470, "THE TAIL IS CUT AT 16°", "end") + "</g></svg>")
    return out

def type_rules():
    bal = (pan('<div style="position:absolute;inset:0;padding:7% 7%;display:grid;align-content:space-between">'
               f'<div style="width:22%">{g.caps(g.CREAM, g.SKY)}</div><p style="font:400 clamp(22px,2.9vw,46px)/1.02 var(--serif);letter-spacing:-.03em;max-width:12em">Software for the people who make the work.</p></div>', "i")
           + pan('<div style="position:absolute;inset:0;padding:7% 7%;display:grid;align-content:space-between">'
                 f'<div style="width:62%">{g.caps(g.INK, g.PRU)}</div><p style="font:400 clamp(16px,1.9vw,30px)/1.06 var(--serif);letter-spacing:-.02em;max-width:12em">Software for the people who make the work.</p></div>', "c"))
    cols = "".join(f'<span style="border-left:1px solid rgba(31,63,122,.16);height:100%"></span>' for _ in range(12))
    grid_bg = f'<div style="position:absolute;inset:0 6%;display:grid;grid-template-columns:repeat(12,1fr);pointer-events:none">{cols}</div>'
    use = pan(grid_bg + '<div style="position:absolute;inset:9% 6%;display:grid;grid-template-columns:repeat(12,1fr);align-content:space-between">'
              '<p style="grid-column:1/8;font:400 clamp(20px,2.5vw,40px)/1.02 var(--serif);letter-spacing:-.03em">Software for the people who make the work.</p>'
              '<p style="grid-column:7/12;font-size:clamp(11px,.9vw,13px);line-height:1.45">Every block starts on a column. The headline takes seven, the text takes five, and the two share one column where they meet.</p></div>', "c", "wide gridp")
    brk = pan(grid_bg + '<div style="position:absolute;inset:9% 6%;display:grid;grid-template-columns:repeat(12,1fr);align-content:space-between">'
              '<p style="grid-column:1/13;font:400 clamp(20px,2.5vw,40px)/1.02 var(--serif);letter-spacing:-.03em">Software for the people<br><span style="padding-left:41.6%">who make the work.</span></p>'
              '<p style="grid-column:1/6;font-size:clamp(11px,.9vw,13px);line-height:1.45">The second line of the headline steps over five columns. One break like this per layout is enough.</p></div>', "c", "wide gridp")
    return bal, use, brk

SCALE = [("Display", 200, ".86", -.038, 400, "Brand"), ("Headline", 96, ".98", -.03, 400, "The people who make"), ("Title", 56, "1.04", -.022, 400, "A crystal grown in the break"),
         ("Statement", 40, "1.13", -.016, 500, "Every point in it is measured."), ("Lede", 24, "1.32", -.01, 500, "Software for the people who make the work."),
         ("Body", 16, "1.46", 0, 500, "Antimony makes software for the people who make the work."), ("Small", 14, "1.42", 0, 500, "Captions, notes and the fine print."),
         ("Callout", 11, "1.5", .1, 400, "#94E6FF  16°  1584 × 396")]

def typography():
    secs = [("serif", "Timeless Serif"), ("weights", "Weights and italic"), ("drawn", "The drawn wordmark"), ("mono", "Commit Mono, for callouts"), ("scale", "Scale"),
            ("balance", "Balance against the wordmark"), ("grid", "Use the grid"), ("break", "Break the grid, once")]
    b = chapter_head("type", "Typography") + toc("Typography", secs)
    b += intro("One serif does nearly all the work. We set it large and with confidence, and keep it quiet at small sizes. A monospace appears only for the small things a machine would say.",
               pill("fonts/CommitMono-Latin-VF.woff2", "Download Commit Mono"))
    b += section("serif", "Timeless Serif",
        "<p>Our typeface for headlines, text and everything said with conviction. It is a variable font, from 200 to 700, with an italic.</p>",
        "<p>Timeless Serif is licensed to Antimony. Ask for the files and the terms of the licence rather than finding them elsewhere. Our wordmarks are drawn from it.</p>",
        '<div class="spec" style="font:400 clamp(34px,5.9vw,88px)/1.08 var(--serif);letter-spacing:-.02em;overflow-wrap:anywhere"><p style="margin-bottom:.12em">Timeless Serif Variable</p>'
        f'<p style="font-weight:400">{AZ}</p></div>')
    wcells = "".join(f'<div style="display:grid;gap:10px;justify-items:start;min-width:0"><span style="font:{wt} clamp(46px,7vw,112px)/1 var(--serif);letter-spacing:-.03em">Aa</span><span class="mono" style="font-size:10.5px;color:var(--pru)">{wt}</span></div>' for wt in (200, 300, 400, 500, 600, 700))
    b += section("weights", "Weights and italic",
        "<p>Headlines at 400, with tight spacing. Text at 500, which holds up better on screen. 600 for the labels in a list or a table. The lighter weights are for very large display and the suffix of a product lockup.</p>",
        "<p>The italic is for names of things and for the odd emphasis. Never set whole paragraphs in it.</p>",
        pan(f'<div class="wts" style="display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:3%;width:86%">{wcells}</div>', "c", "slim", style="aspect-ratio:auto;padding:6% 0")
        + pan('<p style="font:italic 400 clamp(30px,4.4vw,72px)/1.05 var(--serif);letter-spacing:-.025em;width:86%">Orbe, by Antimony. <span style="font-style:normal">A crystal grown in the break.</span></p>', "w", "slim"))
    b += section("drawn", "The drawn wordmark",
        "<p>The wordmarks are drawn from Timeless Serif, but they are not typed in it. Never set the name in the font and call it the logo: use the files in the kit.</p>",
        "<p>In the lower case wordmark three things are changed by hand. Each comes from the mark: a crystal for the tittle, a join where the stone would be one piece, a cut at the seam's angle.</p>",
        pan(f'<div class="art" style="width:84%">{annotated_wordmark()}</div>', "c", "anno"))
    b += section("mono", "Commit Mono, for callouts",
        "<p>Commit Mono is for small callouts only: a colour value, a measurement, a file name, a size, the typed line that opens the website. Never for headlines or paragraphs.</p>",
        "<p>Set it small, 10 to 13 pixels, in capitals tracked by a tenth of an em, or in lower case for code. It is open source, under the SIL Open Font License, and in the kit.</p>",
        '<div class="r2">' + pan('<div style="width:84%;display:grid;gap:16px"><p style="font:400 clamp(26px,3.2vw,50px)/1.05 var(--mono);letter-spacing:-.01em">Commit Mono</p>'
                                 '<p style="font:400 clamp(11px,1.2vw,17px)/1.6 var(--mono)">ABCDEFGHIJKLMNOPQRSTUVWXYZ<br>abcdefghijklmnopqrstuvwxyz<br>0123456789 #°×:/.</p></div>', "c")
        + pan('<div style="width:84%;display:grid;gap:22px">'
              + "".join(f'<div style="display:flex;justify-content:space-between;gap:16px;border-top:1px solid rgba(238,234,224,.22);padding-top:10px"><span class="mono" style="color:var(--sky)">{a}</span><span style="font-size:14px;opacity:.8">{c}</span></div>' for a, c in [
                  ("#94E6FF", "a colour value"), ("16°", "a measurement"), ("1584 × 396", "a size"), ("<span style='text-transform:none'>antimony-mark.svg</span>", "a file name")]) + "</div>", "i") + "</div>")
    rows = "".join(f'<tr><th style="font-weight:600;white-space:nowrap">{n}</th><td class="n">{s} px</td><td class="n">{l}</td><td class="n">{wt}</td>'
                   f'<td><div style="font:{wt} {min(s, 120)}px/{l} {"var(--mono)" if n == "Callout" else "var(--serif)"};letter-spacing:{ls}em;{"text-transform:uppercase;" if n == "Callout" else ""}white-space:nowrap;overflow:hidden;text-overflow:clip;max-width:62vw">{x}</div></td></tr>'
                   for n, s, l, ls, wt, x in SCALE)
    b += section("scale", "Scale",
        "<p>Eight steps, in pixels on screen. Each step is roughly one and a half times the one below. In print, divide by 1.33 for points.</p>",
        "<p>On a phone, the display and headline steps drop to about half; everything from the statement down stays close to its size.</p>",
        f'<div class="scroll"><table class="tab scale"><thead><tr><th>Step</th><th>Size</th><th>Leading</th><th>Weight</th><th>Sample</th></tr></thead><tbody>{rows}</tbody></table></div>')
    bal, use, brk = type_rules()
    b += section("balance", "Balance against the wordmark",
        "<p>Set the main headline clearly larger or clearly smaller than the wordmark beside it, never the same. The most important thing on the page is the largest; everything else takes less attention.</p>",
        "<p>Left, the headline leads and the capitals sign it. Right, the capitals lead a cover, and the line beneath is quieter.</p>",
        f'<div class="r2">{bal}</div>')
    b += section("grid", "Use the grid",
        "<p>Everything sits on the document's grid. That does not mean everything is ranged left: it means every block starts and ends on a column, so the page has a reason.</p>",
        "<p>Our pages use twelve columns with a 20 pixel gutter, and a 40 pixel margin on a laptop, 20 on a phone. Labels take three columns; text takes three or six.</p>", use)
    b += section("break", "Break the grid, once",
        "<p>Our grid is there to be broken, a little. Step one line of a headline over a few columns, or let one word sit where it is not expected.</p>",
        "<p>Once per layout is enough. A second break is just a mess.</p>", brk)
    return S.page("type", "Typography, Antimony brand guidelines", "Timeless Serif, the drawn wordmarks, Commit Mono for callouts, the scale and the rules.", b)

# =====================================================================================
CORE = [("Cream", g.CREAM, "Our paper. The ground of every page we write on.", g.INK), ("Stone", g.STONE, "The stone of the mark. Dark, always.", g.CREAM),
        ("Ink", g.INK, "The night side: chapter heads, the opening, slides.", g.CREAM), ("Sky", g.SKY, "The light. The crystal, and one lit thing per layout.", g.INK)]
SECOND = [("Prussian", g.PRU, "Sky's partner on paper: small things that must be read.", g.CREAM), ("Cobalt", g.COB, "Loud and rare. One moment at a time.", g.CREAM),
          ("Washi", g.WASHI, "A warmer paper, for print and long reading.", g.INK)]

def swatch(n, h, note, fg, shape="tall"):
    rc, ri = ratio(h, g.CREAM), ratio(h, g.INK)
    r, gg, bb = rgb(h)
    lines = (f'<span>HEX {h}</span><span>RGB {r} {gg} {bb}</span>'
             + (f'<span>with cream {rc:.2f} : 1</span>' if h != g.CREAM else "") + (f'<span>with ink {ri:.2f} : 1</span>' if h != g.INK else ""))
    border = "box-shadow:inset 0 0 0 1px rgba(11,12,12,.14);" if h in (g.CREAM, g.WASHI) else ""
    return (f'<figure><div class="pan {shape}" style="background:{h};color:{fg};{border}place-items:end start">'
            f'<div style="padding:7%;display:grid;gap:3px"><b style="font:400 clamp(24px,2.4vw,38px)/1.05 var(--serif);letter-spacing:-.02em;margin-bottom:10px">{n}</b>'
            f'<span class="mono" style="display:grid;gap:2px;font-size:10.5px;letter-spacing:.06em">{lines}</span></div></div><figcaption>{note}</figcaption></figure>')

def ramp(rows):
    cells = ""
    for n, h in rows:
        fg = g.INK if ratio(h, g.INK) >= ratio(h, g.CREAM) else g.CREAM
        best = max(ratio(h, g.INK), ratio(h, g.CREAM))
        cells += (f'<div style="background:{h};color:{fg};aspect-ratio:3/4;display:grid;align-content:end;padding:12px;gap:2px;min-width:0">'
                  f'<b style="font:600 14px/1.2 var(--serif)">{n}</b><span class="mono" style="font-size:9.5px;letter-spacing:.04em">{h}</span>'
                  f'<span class="mono" style="font-size:9.5px;letter-spacing:.04em;opacity:.8">{"ink" if fg == g.INK else "cream"} {best:.1f}</span></div>')
    return f'<div class="ramp" style="display:grid;grid-template-columns:repeat(9,minmax(0,1fr));box-shadow:inset 0 0 0 1px rgba(11,12,12,.1)">{cells}</div>'

COMBOS = [("Cream", g.CREAM, "Ink", g.INK), ("Cream", g.CREAM, "Prussian", g.PRU), ("Ink", g.INK, "Cream", g.CREAM), ("Ink", g.INK, "Sky", g.SKY),
          ("Prussian", g.PRU, "Cream", g.CREAM), ("Prussian", g.PRU, "Sky", g.SKY), ("Washi", g.WASHI, "Prussian", g.PRU), ("Washi", g.WASHI, "Stone", g.STONE),
          ("Sky", g.SKY, "Ink", g.INK), ("Sky", g.SKY, "Prussian", g.PRU), ("Stone", g.STONE, "Cream", g.CREAM), ("Cobalt", g.COB, "Cream", g.CREAM)]

def colour():
    secs = [("core", "Core colours"), ("second", "Supporting colours"), ("sky", "Sky tones"), ("stone", "Stone tones"), ("combinations", "Combinations"), ("contrast", "Contrast"), ("proportion", "Proportion"), ("using", "Using colour")]
    b = chapter_head("colour", "Colour") + toc("Colour", secs)
    b += intro("Cream, stone and ink carry nearly everything. Then one light: sky, the colour of the crystal. Prussian, cobalt and washi support it, and each is used with restraint.",
               pill("downloads/antimony-colours.json", "Download swatches"))
    b += section("core", "Core colours",
        "<p>The four we reach for first, in every execution. Cream is the ground, stone the mark, ink the night side, and sky the light.</p>",
        "<p>Contrast ratios are measured with the WCAG 2 formula against cream and against ink. Screen values; for print, match each to a drawdown on the stock rather than converting by formula.</p>",
        '<div class="r4">' + "".join(swatch(*c) for c in CORE) + "</div>")
    b += section("second", "Supporting colours",
        "<p>Prussian is sky's partner on paper: sky is a colour you can see but not read on cream, so small things that must be read take Prussian.</p>",
        "<p>Cobalt is loud, kept for a single moment. Washi is a warmer paper for print. None of them should ever outweigh the core.</p>",
        '<div class="r3">' + "".join(swatch(*c, shape="") for c in SECOND) + "</div>")
    b += section("sky", "Sky tones",
        "<p>Sky deepens the way the water in the crystal does: from near white, through the crystal's light, down to Prussian at 800. Sky 300 is the core sky.</p>",
        "<p>Use the tones for depth inside a single piece: a chart, a gradient of light, a set of states. Each tile shows the text colour it takes and its contrast.</p>",
        ramp(SKY_RAMP))
    b += section("stone", "Stone tones",
        "<p>The stone runs from cream to stone in nine steps, mixed evenly in the OKLab colour space so each step looks the same distance from the next.</p>",
        "<p>Use them for rules, quiet text, disabled states and the grey of a table. They stay warm without turning brown.</p>",
        ramp(STONE_RAMP))
    cells = "".join(f'<figure><div class="pan sq" style="background:{bh};{"box-shadow:inset 0 0 0 1px rgba(11,12,12,.12);" if bh in (g.CREAM, g.WASHI) else ""}"><div style="width:42%;aspect-ratio:1;background:{fh}"></div></div>'
                    f'<figcaption><b>{fn} on {bn}</b>{ratio(bh, fh):.2f} : 1, {grade(ratio(bh, fh))}</figcaption></figure>' for bn, bh, fn, fh in COMBOS)
    b += section("combinations", "Combinations",
        "<p>These are the pairs we use. Each is a ground and the colour set on it. Pick from these before inventing a new one.</p>",
        "<p>Sky on cream and cream on sky are missing on purpose: they do not have the contrast to carry anything.</p>",
        f'<div class="r4 combos ccombo" style="grid-template-columns:repeat(6,minmax(0,1fr))">{cells}</div>')
    pairs = [(g.CREAM, g.INK), (g.CREAM, g.STONE), (g.CREAM, g.PRU), (g.CREAM, g.COB), (g.CREAM, g.SKY), (g.WASHI, g.PRU), (g.WASHI, g.INK), (g.INK, g.CREAM), (g.INK, g.SKY),
             (g.INK, g.PRU), (g.PRU, g.CREAM), (g.PRU, g.SKY), (g.SKY, g.INK), (g.SKY, g.PRU), (g.COB, g.CREAM), (g.COB, g.SKY)]
    NM = {h: n for n, h, *_ in CORE + SECOND}
    rows = "".join(f'<tr><td>{NM[a]}</td><td><span style="display:inline-block;width:12px;height:12px;background:{c};box-shadow:inset 0 0 0 1px rgba(11,12,12,.25);vertical-align:-1px;margin-right:8px"></span>{NM[c]}</td>'
                   f'<td class="n">{ratio(a, c):.2f} : 1</td><td>{grade(ratio(a, c))}</td><td style="color:var(--dim)">{use_for(ratio(a, c))}</td></tr>' for a, c in pairs)
    b += section("contrast", "Contrast",
        "<p>Every pairing, measured. Text below 4.5 to 1 is never used for reading; between 3 and 4.5 it is for large type and for marks only.</p>", "",
        f'<div class="scroll"><table class="tab"><thead><tr><th>Ground</th><th>Colour</th><th>Ratio</th><th>WCAG 2</th><th>Use</th></tr></thead><tbody>{rows}</tbody></table></div>')
    PROP = [("Cream", g.CREAM, 46), ("Ink", g.INK, 30), ("Stone", g.STONE, 10), ("Prussian", g.PRU, 6), ("Washi", g.WASHI, 4), ("Sky", g.SKY, 3), ("Cobalt", g.COB, 1)]
    bar = "".join(f'<div style="flex:{v};background:{h};min-width:0;{"box-shadow:inset 0 0 0 1px rgba(11,12,12,.12);" if h in (g.CREAM, g.WASHI) else ""}"></div>' for n, h, v in PROP)
    keys = "".join(f'<span><b style="font-weight:600;color:var(--fg)">{n}</b> {v}%</span>' for n, h, v in PROP)
    b += section("proportion", "Proportion",
        "<p>Across a body of work, roughly this much of each. The light is rare on purpose: when sky appears, it should be the thing you look at.</p>", "",
        f'<div style="display:flex;height:120px">{bar}</div><div style="display:flex;flex-wrap:wrap;gap:6px 24px;font-size:14px;color:var(--dim)">{keys}</div>')
    b += section("using", "Using colour", "", "",
        '<div class="facts">' + "".join(f"<div><b>{a}</b><span>{c}</span></div>" for a, c in [
            ("Start with the core", "Cream, stone and ink first. Most layouts need nothing else but the crystal."),
            ("One light", "Sky is the only bright colour. Light one thing per layout: the crystal, a link, a figure. If two things are lit, neither is."),
            ("Prussian for small things", "On paper, anything small in our blue is Prussian: the tittle, the counter of the A, a link, a note."),
            ("Cobalt, rarely", "For one loud moment, such as a single slide or a sticker. Never as a ground for long text."),
            ("Never", "No muddy browns, no amber, no teal, no purple gradients, no glows. No gradient that is not the light in the crystal.")]) + "</div>")
    return S.page("colour", "Colour, Antimony brand guidelines", "Cream, stone, ink, sky, Prussian, cobalt and washi, with true contrast ratios, tonal ramps and combinations.", b)

def use_for(r): return "any text" if r >= 7 else "body text" if r >= 4.5 else "large type and marks" if r >= 3 else "never for text"

# =====================================================================================
def bez(x1, y1, x2, y2):
    def f(x):
        t = x
        for _ in range(12):
            cx = 3 * x1 * t * (1 - t) ** 2 + 3 * x2 * t * t * (1 - t) + t ** 3 - x
            d = 3 * x1 * (1 - t) ** 2 + 6 * (x2 - x1) * t * (1 - t) + 3 * (1 - x2) * t * t
            if abs(cx) < 1e-7: break
            t = min(1, max(0, t - cx / (d or 1e-6)))
        return 3 * y1 * t * (1 - t) ** 2 + 3 * y2 * t * t * (1 - t) + t ** 3
    return f

def curve(c, name, kind="c"):
    f = bez(*c); pts = " ".join(f"{i:.1f},{100 - f(i / 100) * 100:.2f}" for i in range(0, 101, 2))
    col = g.PRU if kind == "c" else g.SKY
    base = "rgba(11,12,12,.18)" if kind == "c" else "rgba(238,234,224,.2)"
    svg = (f'<svg viewBox="-8 -8 116 116" style="width:62%;height:auto;overflow:visible" aria-hidden="true"><path d="M0 0V100H100" fill="none" stroke="{base}" stroke-width=".6"/>'
           f'<path d="M0 100L{c[0] * 100} {100 - c[1] * 100}M100 0L{c[2] * 100} {100 - c[3] * 100}" stroke="{base}" stroke-width=".5" stroke-dasharray="1.5 1.5"/>'
           f'<circle cx="{c[0] * 100}" cy="{100 - c[1] * 100}" r="1.6" fill="{col}"/><circle cx="{c[2] * 100}" cy="{100 - c[3] * 100}" r="1.6" fill="{col}"/>'
           f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.4" stroke-linejoin="round"/></svg>')
    return pan(svg + f'<span class="tag">{name}</span><span class="tag r">{", ".join(f"{v:g}" for v in c)}</span>', kind, "sq")

def timeline_svg(T):
    end = T["end"]; X = lambda t: t / end * 1000
    beats = [("Typed line", 0, T["fade1"]), ("Characters gather", T["g0"], T["land"]), ("Cells", T["sn0"], T["e0"] + T["ed"]), ("Held apart", T["e0"] + T["ed"], T["j0"]),
             ("Join", T["j0"], T["j1"]), ("Cream", T["d0"], T["d1"])]
    out = '<svg viewBox="-10 -34 1030 120" role="img" aria-label="The opening as a timeline, from 0 to 7.3 seconds" style="width:100%;height:auto;font:400 10px var(--mono);letter-spacing:.06em">'
    out += f'<path d="M0 40H1000" stroke="rgba(238,234,224,.35)" stroke-width="1"/>'
    for s in range(0, 8):
        out += f'<path d="M{X(s):.1f} 36V44" stroke="rgba(238,234,224,.5)"/><text x="{X(s):.1f}" y="62" fill="rgba(238,234,224,.6)" text-anchor="middle">{s} S</text>'
    for i, (n, a, b_) in enumerate(beats):
        y = 10 if i % 2 == 0 else -12
        out += f'<rect x="{X(a):.1f}" y="{y + 16}" width="{max(3, X(b_) - X(a)):.1f}" height="4" fill="{g.SKY if n in ("Join",) else "rgba(238,234,224,.85)"}"/>'
        out += f'<text x="{X(a):.1f}" y="{y + 10}" fill="#EEEAE0">{n.upper()}</text>'
    out += f'<path d="M{X(end):.1f} 30V50" stroke="{g.SKY}"/><text x="{X(end):.1f}" y="80" text-anchor="end" fill="{g.SKY}">{end:.2f} S, AT REST</text>'
    return out + "</svg>"

def motion():
    T = json.load(open(os.path.join(HERE, "src/motion/timeline.json")))
    secs = [("opening", "The opening"), ("storyboard", "Storyboard"), ("water", "The water"), ("chip", "The chipped stone"), ("timing", "Timing and easing"), ("rules", "Rules")]
    b = chapter_head("motion", "Motion") + toc("Motion", secs)
    b += intro("The website opens on black, in five beats, one idea each. It takes a little over seven seconds, and any touch, key or scroll skips straight to the end.",
               pill("#storyboard", "See the storyboard", download=False))
    b += section("opening", "The opening",
        "<p>A short line is typed, the line fades, and the characters of the mark's own drawing gather from a wall of text into the Break, held apart along the seam. The halves join with a hairline of light, and cream floods out from the seam.</p>",
        f"<p>A second visit in the same session skips the opening, and so does reduced motion, which shows the page at rest. Every beat starts, holds and leaves on its own; nothing overlaps that does not need to.</p>",
        pan(f'<div class="art" style="width:92%;min-width:640px">{timeline_svg(T)}</div>', "i", "slim tl"))
    beats = [("typed", f'0.35 to {T["typed"]:.2f} s', "The line, typed", "Nineteen characters in Commit Mono at 70 ms each, an even pace. The label is sky; the rest is cream."),
             ("wall", f'{T["g0"]:.2f} s', "The characters", "A field of text set from the mark's own source: its paths, its angle, its colours."),
             ("gather", f'{T["g0"]:.2f} to {T["land"]:.2f} s', "They gather", "The field flows in towards the mark, and its characters travel to their places in it."),
             ("cells", f'{T["sn0"]:.2f} s', "Characters to mosaic", "Each character snaps to a square cell on the same grid, and each cell gives way to the exact mark."),
             ("split", f'{T["e0"] + T["ed"]:.2f} s', "The split", "The two halves held apart along the seam, the crystal broken with them. The longest hold."),
             ("join", f'{T["j0"]:.2f} to {T["j1"]:.2f} s', "The join", "The halves close along the seam, heavy at the start and with a long, firm finish. No overshoot."),
             ("flare", f'{T["j1"]:.2f} s', "The light", "As they lock, a hairline of light runs down the seam, and the water in the crystal settles."),
             ("ground", f'{T["d0"]:.2f} to {T["d1"]:.2f} s', "Cream", "Paper floods out from the seam in an ordered dissolve, cell by cell, and the wordmark is there beneath it."),
             ("rest", f'{T["end"]:.2f} s', "At rest", "The page as it stays: the mark, the capitals, and one line at the foot.")]
    b += section("storyboard", "Storyboard",
        "<p>Every frame here is taken from the website itself, at the moment given. The first is cropped to the top of the screen, where the line is typed.</p>", "",
        '<div class="r3">' + "".join(fig(f'<div class="pan i" style="aspect-ratio:16/10"><img class="fill" src="img/motion/beat-{k}.jpg" alt="{esc(n)}" loading="lazy"><span class="tag t" style="opacity:.8">{i + 1:02d}</span><span class="tag t r" style="opacity:.8">{tm}</span></div>', n, d)
                                    for i, (k, tm, n, d) in enumerate(beats)) + "</div>")
    wf = [("water-0", "Still", "At rest the surface tilts very slightly, once every nine seconds or so."), ("water-1", "80 ms", "The pointer sweeps across: the water takes its speed and tips."),
          ("water-2", "320 ms", "It runs up the far wall of the crystal and a ripple crosses the surface."), ("water-3", "800 ms", "It swings back, less each time."),
          ("water-4", "3.2 s", "Settled. On a phone, a tap tips it, and tilting the phone moves it too.")]
    b += section("water", "The water",
        "<p>The crystal holds water and light. When the pointer moves over or near it, the water takes up the movement and sloshes with real inertia, then settles slowly.</p>",
        "<p>It is two damped springs: the tilt of the surface at 0.8 cycles a second with a damping ratio of 0.09, and its level at 1.2 cycles with 0.12. The nearer the pointer, the more it moves.</p>",
        '<div class="r5">' + "".join(fig(f'<div class="pan c sq"><img class="fill" src="img/motion/{k}.jpg" alt=""></div>', n, d) for k, n, d in wf) + "</div>")
    cf = [("chip-0", "Over the stone", "A fine fracture runs from the seam towards the pointer, and the cursor becomes a hairline cross."),
          ("chip-1", "A tap", "A six sided shard chips out of the stone, with a few dark fragments, and leaves a hole lit at its edge."),
          ("chip-3up", "Three shards", "Each shard turns over to show one thing made here, in grey, with its name beneath. Colour returns on hover."),
          ("chip-heal", "Healed", "Tap anywhere else or press Escape: the shards fly home and the stone heals along each break with a line of light.")]
    b += section("chip", "The chipped stone",
        "<p>The stone can be chipped. Up to three shards come away, each turning to show one of the things Antimony makes, and each a link to it. It is the only place the website names them.</p>",
        "<p>With a keyboard, the mark takes focus; Enter chips the next shard and Escape heals the stone. Under reduced motion every move is instant.</p>",
        '<div class="r4">' + "".join(fig(f'<div class="pan c sq"><img class="fill" src="img/motion/{k}.jpg" alt="" style="object-fit:cover;transform:scale(1.22)"></div>', n, d) for k, n, d in cf) + "</div>")
    TIM = [("Typed line", "70 ms a character", "linear steps", "The opening's first line; it holds 0.36 s and fades over 0.6 s."),
           ("Characters gather", "1.22 s", "cubic-bezier(.55, 0, .2, 1)", "The wall flows into the mark."),
           ("Snap to cells", "0.58 s, then 0.2 s", "per cell, at random", "Characters to squares, squares to the exact mark."),
           ("Join", "1.15 s", "cubic-bezier(.64, 0, .28, 1)", "Heavy to start, a long firm finish, no overshoot."),
           ("Cream", "0.95 s", "cubic-bezier(.42, 0, .22, 1)", "The ground floods out from the seam."),
           ("Page fade", "0.8 s", "cubic-bezier(.25, .6, .3, 1)", "On a second visit, or when the opening is skipped."),
           ("Shard turns", "1.5 s", "cubic-bezier(.2, .7, .18, 1)", "Out, over and into its place; the name follows after 1.15 s."),
           ("Shards return", "0.95 s, 110 ms apart", "cubic-bezier(.55, 0, .25, 1)", "Home, then the healing light fades over 1.7 s."),
           ("Water", "0.8 Hz and 1.2 Hz", "damped springs, 0.09 and 0.12", "The tilt and the level of the surface.")]
    rows = "".join(f'<tr><th style="font-weight:600">{a}</th><td class="n">{b_}</td><td class="n">{c}</td><td>{d}</td></tr>' for a, b_, c, d in TIM)
    b += section("timing", "Timing and easing",
        "<p>Every number here is read from the website's code. Movements ease out; nothing shorter than 0.6 s unless it is a deliberate cut, like the typed characters or the cells.</p>",
        "<p>The curves, drawn: each starts slowly enough to feel like weight, and none of them passes its end.</p>",
        '<div class="r4">' + curve((.55, 0, .2, 1), "Gather", "i") + curve((.64, 0, .28, 1), "Join", "i") + curve((.42, 0, .22, 1), "Cream", "i") + curve((.2, .7, .18, 1), "Shard", "i") + "</div>"
        + f'<div class="scroll"><table class="tab"><thead><tr><th>Move</th><th>Duration</th><th>Easing</th><th>For</th></tr></thead><tbody>{rows}</tbody></table></div>')
    b += section("rules", "Rules", "", "",
        '<div class="facts">' + "".join(f"<div><b>{a}</b><span>{c}</span></div>" for a, c in [
            ("One beat at a time", "One idea moves at once. When two things move together, one of them is in the way."),
            ("Weight", "Stone is heavy: it starts slowly and stops firmly, and it never bounces. Only water moves on after it is touched."),
            ("Always skippable", "Any touch, key or scroll ends an opening. A second visit skips it. Reduced motion shows the end."),
            ("Instant to the hand", "Anything that answers the pointer answers on the same frame. Nothing waits for an animation to finish."),
            ("No tricks", "No blinking cursors, no scroll hints, no counters, no glow. If a movement has no meaning in the mark, cut it.")]) + "</div>")
    return S.page("motion", "Motion, Antimony brand guidelines", "The opening as a storyboard, the water and the chipped stone, timings, easing and rules.", b)

# =====================================================================================
def ornament(fg, sky=g.SKY, op=.55):
    """Hairline construction as ornament: long lines through the mark, the seam run on, arcs, and one point of light."""
    t = math.tan(math.radians(16)); cx, cy = 800, 450; s = 1.1
    L = lambda d, sw=1, o=op, da="": f'<path d="{d}" fill="none" stroke="{fg}" stroke-opacity="{o}" stroke-width="{sw}" vector-effect="non-scaling-stroke"{f" stroke-dasharray={chr(34)}{da}{chr(34)}" if da else ""}/>'
    sx = lambda y: cx + (cy + 1.5 * s - y) * t
    out = f'<svg viewBox="0 0 1600 900" style="width:100%;height:100%" aria-hidden="true">'
    out += L(f"M0 {cy}H1600") + L(f"M{cx} 0V900", 1, op * .8) + L(f"M{sx(0):.1f} 0L{sx(900):.1f} 900", 1, op)
    out += L(f"M{cx - 330} {cy}A330 330 0 0 1 {cx + 330} {cy}", 1, op * .7) + L(f"M{cx + 210} {cy}A210 210 0 0 1 {cx} {cy + 210}", 1, op * .7)
    out += L(f"M{cx - 520} {cy}A520 520 0 0 0 {cx} {cy + 520}", 1, op * .45, "2 6")
    out += f'<circle cx="{cx}" cy="{cy}" r="104" fill="none" stroke="{fg}" stroke-opacity="{op * .7}" vector-effect="non-scaling-stroke"/>'
    for k in range(-7, 8):
        if k: out += L(f"M{cx + k * 100} {cy - 5}V{cy + 5}", 1, op * .8)
    # a point of light on the vertical
    out += f'<path d="M{cx} {cy - 262}l5 9-5 9-5-9z" fill="{sky}"/>' + L(f"M{cx - 14} {cy - 253}H{cx + 14}", 1, .9)
    out += f'<g transform="translate({cx - 50 * s} {cy - 51.5 * s}) scale({s})">{g.mark_body(**g.mark_for(g.INK if fg == g.CREAM else g.CREAM))}</g>'
    return out + "</svg>"

def art():
    secs = [("textures", "Textures"), ("light", "Water light"), ("ornament", "Hairline construction"), ("rules", "Rules")]
    b = chapter_head("art", "Art direction") + toc("Art direction", secs)
    b += intro("We draw our own pictures, and we draw them from the mark: its grain, its light, its geometry, its source. Nothing is photographed, borrowed or generated.",
               pill(KITZIP, "Download textures"))
    tx = [('<div style="position:absolute;inset:0;background:url(img/tex/grain-cream.png) 0 0/512px 512px;image-rendering:pixelated"></div>', "c", "Paper grain", "Fine and even: dark and light points on cream, baked once. It sits over every light layout, as on the website. Shown here at twice its size."),
          ('<img class="fill" src="img/tex/halftone-panel.png" alt="" loading="lazy">', "c", "Halftone", "The water light as a dot screen in Prussian on cream, the screen turned to the seam's sixteen degrees."),
          ('<img class="fill" src="img/tex/halftone-ink-panel.png" alt="" loading="lazy">', "i", "Halftone on ink", "The same screen in sky on ink. The dots grow where the light is."),
          ('<img class="fill" src="img/tex/stipple-panel.png" alt="" loading="lazy">', "i", "Stippled light", "Points of light on ink, gathered where the light is strong and thinning into the dark, like an engraving."),
          ('<img class="fill" src="img/tex/chars-panel.png" alt="" loading="lazy">', "i", "The character field", "Rows of the mark's own source, set in Commit Mono: its paths, its angle, its colours. It is the wall the website opens on."),
          ('<img class="fill" src="img/tex/stone-panel.jpg" alt="" loading="lazy">', "s", "Stone", "Dark stone, a little lighter where the light falls, with a fine tooth. The back of a card, a slide.")]
    b += section("textures", "Textures",
        "<p>Nothing we make is flat. Every ground carries a texture, and every texture is procedural: drawn by code, baked once, and cheap to show.</p>",
        "<p>One texture per layout. Pick it for the ground you need, not for decoration, and keep it quiet enough that the mark or the words lead.</p>",
        '<div class="r3">' + "".join(fig(pan(c, k, "sq"), n, d) for c, k, n, d in tx) + "</div>")
    b += section("light", "Water light",
        "<p>The light in the crystal, opened out: deep blue below, sky through the middle, pale at the top, with slow caustics and a stippled grain. It is the closest we come to a picture.</p>",
        "<p>Use it full bleed, under the line mark or a single line of type. Never put it inside a frame, and never put a photograph in its place.</p>",
        pan('<img class="fill" src="img/tex/light-panel.jpg" alt="" loading="lazy">', "k", "wide"))
    b += section("ornament", "Hairline construction",
        "<p>The mark's own construction, drawn as ornament: a long horizontal through its centre, a vertical, the seam run on at sixteen degrees, a few arcs, and one small point of light.</p>",
        "<p>Hairlines only, at about half strength. Use it on a cover, a title slide or the back of something, never behind text, and always with the mark at the crossing.</p>",
        '<div class="r2">' + pan(ornament(g.CREAM), "i") + pan(ornament(g.INK, g.PRU, .42), "c") + "</div>")
    b += section("rules", "Rules", "", "",
        '<div class="facts">' + "".join(f"<div><b>{a}</b><span>{c}</span></div>" for a, c in [
            ("No stock photos", "Not of people, offices, laptops or hands. If a layout seems to need a photograph, it needs fewer things."),
            ("No prints, no borrowed art", "We do not use other people's pictures, old or new, however fine. Everything here is drawn by us, from the mark."),
            ("No generated images", "No pictures made by image models, and nothing that imitates them."),
            ("Light, not glow", "The only light is the crystal's: sky, deepening to blue. No neon, no bloom, no gradients for their own sake."),
            ("One texture", "One texture per layout, one line mark per layout. The page stays nearly empty.")]) + "</div>")
    return S.page("art", "Art direction, Antimony brand guidelines", "Textures, water light and hairline construction.", b)

# =====================================================================================
def use():
    sz = json.load(open(os.path.join(HERE, "jobs/mock-sizes.json")))
    def m(name, title, kit):
        W, Hh = sz[name]
        return S.mock(f"mockups/{name}.html", round(W), round(Hh), title, [(f"img/use/antimony-{name}.png", "PNG"), (f"mockups/{name}.html", "HTML")])
    secs = [("social", "Social"), ("posters", "Posters"), ("print", "Print"), ("deck", "Presentations"), ("email", "Email")]
    b = chapter_head("use", "Brand in use") + toc("Brand in use", secs)
    b += intro("Where people meet Antimony first. Each piece here is drawn in HTML at the size the platform or the printer asks for, and exported as a PNG in the kit.", pill(KITZIP, "Download all"))
    b += section("social", "Social",
        "<p>The LinkedIn banner is 1584 by 396 and the avatar 400 square; the X header 1500 by 500; the link card, shown when our address is shared, 1200 by 630.</p>",
        "<p>Platforms crop banners on phones and lay the avatar over the lower left, so the banner keeps its words to the middle and right. The avatar is the mark alone, with the water in the crystal.</p>",
        m("linkedin-banner", "LinkedIn banner", "social") + m("x-header", "X header", "social")
        + '<div class="r2" style="grid-template-columns:1fr 2fr;align-items:start">' + m("linkedin-avatar", "Avatar", "social") + m("link-card", "Link card", "social") + "</div>")
    b += section("posters", "Posters",
        "<p>Three posters in the A series proportion, exported at 2400 by 3394 for A2 and smaller. The line mark is drawn huge and thin over the water light, paper and the character field.</p>",
        "<p>Each carries the wordmark large at the top or the foot, and a few plain lines in columns. No photographs: the texture is the picture.</p>",
        '<div class="r3">' + m("poster-light", "Poster, light", "posters") + m("poster-paper", "Poster, paper", "posters") + m("poster-stone", "Poster, characters", "posters") + "</div>")
    b += section("print", "Print",
        "<p>The card is 85 by 55 mm, the letterhead A4. Both are exported as PDF at true size and as PNG at 300 dpi. The front of the card carries the name and role; the back carries the mark on stone.</p>",
        "<p>Name in Timeless Serif 600 at 9.6 pt, role at 7.6 pt. Add a contact line beneath the role in the same size only once the company's address is confirmed. The letter is set in Timeless Serif at 10.5 pt.</p>",
        '<div class="r2">' + m("card-front", "Business card, front", "print") + m("card-back", "Business card, back", "print") + "</div>"
        + '<div class="r2" style="align-items:start">' + m("letterhead", "Letterhead", "print")
        + '<div class="facts" style="align-self:start">' + "".join(f"<div><b>{a}</b><span>{c}</span></div>" for a, c in [
            ("Lockup", "Primary, 46 mm wide, 20 mm from the left and 18 mm from the top."),
            ("Text", "120 mm measure, 70 mm from the top; Timeless Serif 10.5 on 15.75 pt."),
            ("Foot", "A hairline 16 mm from the bottom, with the name and the line, in Commit Mono at 6.4 pt."),
            ("Paper", "Cream stock, matched to a drawdown. No grain is printed: the paper brings its own.")]) + "</div></div>")
    b += section("deck", "Presentations",
        "<p>The title slide, at 1920 by 1080: ink with stippled light, the capitals at the top, one line in Timeless Serif at 112 pixels, and the line mark running off the right edge.</p>",
        "<p>Every slide after it is cream. Keep one idea to a slide, and let the last slide carry the wordmark alone.</p>", m("deck-title", "Deck title slide", "deck"))
    b += section("email", "Email",
        "<p>Mail clients cannot load our fonts, so the signature is set in Georgia, with the lockup as a small image. Name, role, the lockup and the line: nothing else.</p>",
        "<p>No banners, no quotations, no social icons, no legal paragraphs unless they are required. The HTML and the image are in the kit.</p>",
        f'<div style="max-width:600px">{m("email-signature", "Email signature", "email")}</div>')
    return S.page("use", "Brand in use, Antimony brand guidelines", "Social images, posters, business card, letterhead, a title slide and an email signature, drawn at true size.", b)

# =====================================================================================
def downloads(counts):
    secs = [("kit", "The kit"), ("folders", "What is in it"), ("choosing", "Choosing a file"), ("fonts", "Fonts")]
    b = chapter_head("downloads", "Downloads") + toc("Downloads", secs)
    b += intro("Everything on these pages, as files. Masters in SVG, exports in PNG at 1x and 2x, icons, social images, posters and print.", pill(KITZIP, f"Download the kit, {zip_mb()}"))
    F = [("svg/mark", "The Break in full colour for cream, ink, Prussian and washi; with light; the small drawing for 16 to 30 px; one colour."),
         ("svg/line-mark", "The line mark in ink, cream, Prussian and sky, and a hairline version that keeps one pixel at any size."),
         ("svg/wordmark", "Capitals, lower case, heavy and title case, for each ground and in one colour."),
         ("svg/lockup", "Primary and stacked lockups, for each ground and in one colour."),
         ("svg/product", "Orbe, by Antimony, for cream and ink."),
         ("png", "Every master above, at 1x and 2x, on a transparent ground."),
         ("icons", "favicon.ico and favicon.svg; 16, 32 and 48 px; Apple touch icon; 192, 512 and 1024 px; maskable icon; web manifest."),
         ("social", "LinkedIn banner and avatar, X header, link card, at 1x and 2x."),
         ("posters", "Light, paper and characters, at 2400 by 3394."),
         ("print", "Card front and back, letterhead: PDF at true size, PNG at 300 dpi."),
         ("deck", "The title slide at 1920 by 1080, and 2x."),
         ("email", "The signature as HTML and as a picture, and its lockup image."),
         ("textures", "Paper grain, water light, stippled light, halftone, the character field, stone."),
         ("colours", "Every colour and tone as JSON, with its contrast against cream and ink."), ("fonts", "Commit Mono, with its licence.")]
    b += section("kit", "The kit",
        f"<p>One archive, <span class=mono style='font-size:12px'>antimony-kit-v3.zip</span>, {zip_mb()}. Unzip it and start with the SVG masters: they are exact, and they scale.</p>",
        "<p>The PNG files are drawn from the same masters by the same engine as these pages. Use them where SVG is not accepted.</p>",
        f'<div>{pill(KITZIP, "Download the kit")}</div>')
    b += section("folders", "What is in it", "", "",
        '<div class="facts">' + "".join(f'<div><b>{a}/</b><span>{c} <span style="color:var(--dim)">{counts.get(a, "")}</span></span></div>' for a, c in F) + "</div>")
    b += section("choosing", "Choosing a file",
        "<p>Each file says which ground it is drawn for: for-cream, for-ink, for-prussian, for-washi. The stone is always dark; on ink and Prussian its edges carry a hairline of light.</p>",
        "<p>For one colour on a dark ground, use the line mark. Never place a pale tile on a dark ground, and never recolour a file by hand: if the version you need is missing, ask for it.</p>")
    b += section("fonts", "Fonts",
        "<p>Commit Mono is in the kit under the SIL Open Font License. Timeless Serif is licensed to Antimony and is not in the kit.</p>",
        "<p>You do not need either font to use the logos: every wordmark and lockup is drawn as outlines.</p>")
    return S.page("downloads", "Downloads, Antimony brand guidelines", "The Antimony brand kit: masters, exports, icons, social images, posters and print.", b)

# =====================================================================================
def build():
    os.makedirs(os.path.join(OUT, "downloads"), exist_ok=True)
    cols = {n: {"hex": h, "rgb": list(rgb(h)), "contrast_with_cream": round(ratio(h, g.CREAM), 2), "contrast_with_ink": round(ratio(h, g.INK), 2)} for n, h, *_ in CORE + SECOND}
    cols["tones"] = {n: h for n, h in SKY_RAMP + STONE_RAMP}
    json.dump(cols, open(os.path.join(OUT, "downloads/antimony-colours.json"), "w"), indent=1)
    kit = os.path.normpath(os.path.join(OUT, "../kit-v3"))
    os.makedirs(os.path.join(kit, "colours"), exist_ok=True)
    json.dump(cols, open(os.path.join(kit, "colours/antimony-colours.json"), "w"), indent=1)
    counts = {}
    for a in ("svg/mark", "svg/line-mark", "svg/wordmark", "svg/lockup", "svg/product", "png", "icons", "social", "posters", "print", "deck", "email", "textures", "colours", "fonts"):
        n = sum(len(f) for _, _, f in os.walk(os.path.join(kit, a)))
        counts[a] = f"{n} files." if n != 1 else "1 file."
    pages = {"index": cover(), "logo": logo(), "type": typography(), "colour": colour(), "motion": motion(), "art": art(), "use": use(), "downloads": downloads(counts)}
    for k, v in pages.items():
        open(os.path.join(OUT, f"{k}.html"), "w").write(v)
        print(k, len(v))
