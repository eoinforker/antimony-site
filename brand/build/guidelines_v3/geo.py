"""The Break and the Antimony wordmarks as SVG, drawn from break-geometry.json and the wordmark masters.

Everything here returns SVG strings. Every id inside an SVG carries a unique suffix so that many marks can share one page."""
import itertools, json, math, os, re
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
G = json.load(open(os.path.join(SRC, "break-geometry.json")))
P = G["params"]

# ---------- palette ----------
CREAM, STONE, INK, SKY, PRU, COB, WASHI = "#EEEAE0", "#141311", "#0B0C0C", "#94E6FF", "#1F3F7A", "#2448FF", "#F3ECDD"
LIGHT = (CREAM, WASHI)

_uid = itertools.count(1)
def uid(p="a"): return f"{p}{next(_uid)}"

def pts(d):
    """M/L polygon path to a list of points."""
    nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", d)]
    return list(zip(nums[0::2], nums[1::2]))

def fmt(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s

def poly_d(ps, close=True):
    return "M" + "L".join(f"{fmt(x)} {fmt(y)}" for x, y in ps) + ("Z" if close else "")

# ---------- the tile, with its corners as true arcs ----------
R = 22.0
CORNERS = [(R, R), (100 - R, R), (100 - R, 100 - R), (R, 100 - R)]
def tile_poly(n=96):
    out = []
    for (cx, cy), a0 in zip([(100 - R, R), (100 - R, 100 - R), (R, 100 - R), (R, R)], [-90, 0, 90, 180]):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            out.append((cx + R * math.cos(a), cy + R * math.sin(a)))
    return Polygon(out)

def ring_d(coords):
    """A ring from shapely as a path, with every run of points on a corner circle written back as one arc."""
    cs = list(coords)[:-1]
    def corner(p):
        for i, (cx, cy) in enumerate(CORNERS):
            if abs(math.hypot(p[0] - cx, p[1] - cy) - R) < 1e-3 and (p[0] - cx) * (1 if cx > 50 else -1) >= -1e-6 and (p[1] - cy) * (1 if cy > 50 else -1) >= -1e-6:
                return i
        return None
    # start at a point that is not inside an arc run
    n = len(cs); start = 0
    for i in range(n):
        if corner(cs[i]) is None: start = i; break
    cs = cs[start:] + cs[:start]
    tags = [corner(p) for p in cs]
    # shapely orientation: work out sweep from signed area
    area = sum(cs[i][0] * cs[(i + 1) % n][1] - cs[(i + 1) % n][0] * cs[i][1] for i in range(n))
    sweep = 1 if area > 0 else 0
    d = f"M{fmt(cs[0][0])} {fmt(cs[0][1])}"
    i = 1
    while i < n:
        t = tags[i]
        if t is None:
            d += f"L{fmt(cs[i][0])} {fmt(cs[i][1])}"; i += 1; continue
        j = i
        while j + 1 < n and tags[j + 1] == t: j += 1
        d += f"L{fmt(cs[i][0])} {fmt(cs[i][1])}"
        if j > i: d += f"A22 22 0 0 {sweep} {fmt(cs[j][0])} {fmt(cs[j][1])}"
        i = j + 1
    return d + "Z"

def parts(small=False):
    g = G["small"] if small else G
    seam, cav = Polygon(pts(g["seam"])), Polygon(pts(g["cav"]))
    cut = unary_union([seam, cav])
    stone = tile_poly().difference(cut)
    halves = sorted(list(stone.geoms), key=lambda h: h.centroid.x)
    halves_d = [ring_d(h.exterior.coords) for h in halves]
    return {
        "halves": halves_d,                       # left, right
        "stone": "".join(halves_d),
        "gem": g["gem"], "facet": g["facet"], "seam": g["seam"], "cav": g["cav"],
        "axis": "M58.6 21.5L41.4 81.5",
        "halves_poly": halves,
    }
Q, QS = parts(), parts(True)
def _seam_pieces():
    seam, cav = Polygon(pts(G["seam"])), Polygon(pts(G["cav"]))
    pcs = tile_poly().intersection(seam).difference(cav)
    return [poly_d([(round(x, 2), round(y, 2)) for x, y in list(p.exterior.coords)[:-1]]) for p in pcs.geoms]
SEAM_PIECES = _seam_pieces()

def _svg(vb, body, w=None, h=None, style="", label="Antimony", extra=""):
    size = (f' width="{w}"' if w else "") + (f' height="{h}"' if h else "")
    st = f' style="{style}"' if style else ""
    lab = f' role="img" aria-label="{label}"' if label else ' aria-hidden="true"'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}"{size}{st}{lab}{extra}>{body}</svg>'

# ---------- the mark ----------
def mark_body(stone=STONE, crystal=SKY, facet=True, rim=None, small=False, light=False, ox=0, oy=0, k=1.0):
    """The Break in a 100 unit box. rim: a colour for the light along the stone's cut edges (on dark grounds).
    light: the crystal holds the water light (gradient) instead of flat sky."""
    q = QS if small else Q
    t = f' transform="translate({fmt(ox)} {fmt(oy)}) scale({k})"' if (ox or oy or k != 1) else ""
    out = f"<g{t}>"
    out += f'<path d="{q["stone"]}" fill="{stone}"/>'
    if rim:
        c = uid("c")
        out += (f'<clipPath id="{c}"><path d="{q["stone"]}"/></clipPath>'
                f'<path d="{q["stone"]}" fill="none" stroke="{rim}" stroke-opacity=".42" stroke-width="{2.2 if small else 1.2}" stroke-linejoin="round" clip-path="url(#{c})"/>')
    if light:
        gid = uid("w")
        out += (f'<linearGradient id="{gid}" x1="0" y1="21.5" x2="0" y2="81.5" gradientUnits="userSpaceOnUse">'
                '<stop offset="0" stop-color="#E4F8FF"/><stop offset=".3" stop-color="#BDF0FF"/><stop offset=".32" stop-color="#9DE8FF"/>'
                '<stop offset=".7" stop-color="#5FA6E8"/><stop offset="1" stop-color="#3F7FD0"/></linearGradient>'
                f'<path d="{q["gem"]}" fill="url(#{gid})"/>')
    else:
        out += f'<path d="{q["gem"]}" fill="{crystal}"/>'
    if facet:
        out += f'<path d="{q["facet"]}" fill="#fff" fill-opacity="{.22 if light else .28}"/>'
    return out + "</g>"

def mark(stone=STONE, crystal=SKY, facet=True, rim=None, small=False, light=False, ground=None, w=None, h=None, style="", label="The Antimony mark"):
    bg = f'<rect x="-30" y="-30" width="160" height="160" fill="{ground}"/>' if ground else ""
    return _svg("0 0 100 100", bg + mark_body(stone, crystal, facet, rim, small, light), w, h, style, label)

def mark_one(colour, small=False, **kw):
    """One colour: stone and crystal in the same ink; the cavity keeps them apart."""
    return mark(colour, colour, facet=False, small=small, **kw)

# ---------- the line mark ----------
def line_body(colour=CREAM, sw=1.0, nonscaling=False, hi=None, hi_colour=SKY, dim=None, ox=0, oy=0, k=1.0, parts_on=("stone", "gem", "axis")):
    q = Q
    vx = ' vector-effect="non-scaling-stroke"' if nonscaling else ""
    t = f' transform="translate({fmt(ox)} {fmt(oy)}) scale({k})"' if (ox or oy or k != 1) else ""
    a = f'fill="none" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"{vx}'
    out = f'<g{t} {a} stroke="{colour}"' + (f' stroke-opacity="{dim}"' if dim else "") + ">"
    if "stone" in parts_on: out += "".join(f'<path d="{h}"{vx}/>' for h in q["halves"])
    if "gem" in parts_on: out += f'<path d="{q["gem"]}"{vx}/>'
    if "axis" in parts_on: out += f'<path d="{q["axis"]}"{vx}/>'
    out += "</g>"
    return out

def line_mark(colour=CREAM, sw=1.0, ground=None, w=None, h=None, style="", nonscaling=False, label="The Antimony mark, drawn in line", pad=1.5):
    bg = f'<rect x="-30" y="-30" width="160" height="160" fill="{ground}"/>' if ground else ""
    return _svg(f"{-pad} {-pad} {100 + 2 * pad} {100 + 2 * pad}", bg + line_body(colour, sw, nonscaling), w, h, style, label)

# ---------- the five readings ----------
def seam_line():
    t = math.tan(math.radians(16))
    # the seam's centre line, run long, at 16 degrees from upright through the crystal's centre
    cx, cy = 50, 51.5
    return f"M{fmt(cx + (cy + 14) * t)} -14L{fmt(cx - (114 - cy) * t)} 114"

def reading(which, base=CREAM, hi=SKY, sw=1.1, ground=None):
    """One reading of the mark: the whole drawn dim, one part in sky."""
    q = Q
    a = f'fill="none" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"'
    dim = f'<g {a} stroke="{base}" stroke-opacity=".26">' + "".join(f'<path d="{h}"/>' for h in q["halves"]) + f'<path d="{q["gem"]}"/><path d="{q["axis"]}"/></g>'
    if which == "stone":
        top = "".join(f'<path d="{h}"/>' for h in q["halves"])
    elif which == "seam":
        top = "".join(f'<path d="{d}"/>' for d in SEAM_PIECES)
        top += f'<path d="{seam_line()}" stroke-width="{sw * .5}" stroke-dasharray="1.4 1.8"/>'
        top += f'<path d="M68.78 -14V8" stroke-width="{sw * .5}"/><path d="M68.78 -4A10 10 0 0 1 66.02 -4.39" stroke-width="{sw * .5}"/>'
    elif which == "cavity":
        top = f'<path d="{q["cav"]}"/>'
    elif which == "crystal":
        top = f'<path d="{q["gem"]}"/>'
    else:  # light: the lit half, hatched along the axis
        c = uid("f")
        top = f'<path d="{q["facet"]}"/><clipPath id="{c}"><path d="{q["facet"]}"/></clipPath><g clip-path="url(#{c})" stroke-width="{sw * .5}">'
        top += "".join(f'<path d="M{fmt(58.6 + i * 3.2)} 14L{fmt(41.4 + i * 3.2 - 2.3)} 89"/>' for i in range(1, 7)) + "</g>"
    bg = f'<rect x="-30" y="-30" width="160" height="160" fill="{ground}"/>' if ground else ""
    return _svg("-16 -16 132 132", bg + dim + f'<g {a} stroke="{hi}">{top}</g>', label=f"The mark, read as {which}")

# ---------- wordmarks ----------
def _paths(fn):
    s = open(os.path.join(SRC, fn)).read()
    return re.findall(r'<path d="([^"]+)"', s)

CAPS = _paths("antimony-wordmark-caps-ink.svg")       # 8 letters; A carries its counter as a hole
TITLE = _paths("antimony-wordmark-title-ink.svg")     # 8 letters
SERIF = _paths("antimony-wordmark-serif-ink.svg")     # 8 letters, the t to i bar, tittle, facet
CAPS_COUNTER = "M444.5155 -286 336 -563 227.4845 -286 336 -374Z"
TITLE_COUNTER = "M442.9485 -290 336 -563 229.0515 -290 336 -386Z"
TR = 440   # the capitals' extra tracking, per letter, in font units (as on the website)
ADJ = [-130, -30, -55, 5, -15, 0, -35]   # spaced by eye: the crystal A closer to N, the T and I a touch tighter
CAPS_X = [0]
for _a in ADJ: CAPS_X.append(CAPS_X[-1] + TR + _a)
CAPS_W, CAPS_H = 6326 + CAPS_X[-1], 695   # ink extent: x 15 to CAPS_W; cap height 695

def lit_for(ground):
    return PRU if ground in LIGHT or ground is None else SKY

def caps_body(colour=INK, counter=PRU, tracked=True):
    out = ""
    if counter:
        out += f'<path d="{CAPS_COUNTER}" fill="{counter}" stroke="{counter}" stroke-width="14" stroke-linejoin="round"/>'
    out += f'<g fill="{colour}">'
    for i, d in enumerate(CAPS):
        tx = CAPS_X[i] if tracked else 0
        out += f'<path d="{d}"' + (f' transform="translate({tx} 0)"' if tx else "") + "/>"
    return out + "</g>"

def caps(colour=INK, counter=PRU, w=None, h=None, style="", tracked=True):
    width = CAPS_W if tracked else 6326
    return _svg(f"0 -712 {width + 20} 724", caps_body(colour, counter, tracked), w, h, style, "Antimony")

def title_body(colour=INK, counter=PRU):
    out = f'<path d="{TITLE_COUNTER}" fill="{counter}" stroke="{counter}" stroke-width="14" stroke-linejoin="round"/>' if counter else ""
    return out + f'<g fill="{colour}">' + "".join(f'<path d="{d}"/>' for d in TITLE) + "</g>"

def title(colour=INK, counter=PRU, w=None, h=None, style=""):
    return _svg("0 -712 4330 940", title_body(colour, counter), w, h, style, "Antimony")

SERIF_VB = "40 -748 4110 978"
def serif_body(colour=INK, tittle=PRU, heavy=False, facet=True):
    letters = SERIF[:9]
    stroke = f' stroke="{colour}" stroke-width="10" stroke-linejoin="round"' if heavy else ""
    out = f'<g fill="{colour}"{stroke}>' + "".join(f'<path d="{d}"/>' for d in letters) + "</g>"
    out += f'<path d="{SERIF[9]}" fill="{tittle}"/>'
    if facet and tittle != colour:
        out += f'<path d="{SERIF[10]}" fill="#fff" fill-opacity=".28"/>'
    return out

def serif(colour=INK, tittle=PRU, heavy=False, w=None, h=None, style=""):
    return _svg(SERIF_VB, serif_body(colour, tittle, heavy), w, h, style, "antimony")

# ---------- lockups ----------
def mark_for(ground, small=False, light=False):
    """Full colour mark for a ground: dark stone always; on dark grounds its cut edges catch the light."""
    dark = ground not in LIGHT and ground is not None
    return dict(stone=STONE, crystal=SKY, facet=True, rim=CREAM if dark else None, small=small, light=light)

def lockup(ground=CREAM, one=None, w=None, h=None, style="", light=False):
    """Primary lockup: the mark, then the tracked capitals at a fifth of its height, centred on it."""
    ch = 22.0                       # cap height in mark units
    s = ch / CAPS_H
    gap = 34.0
    ww = CAPS_W * s
    W = 100 + gap + ww
    if one:
        m = mark_body(one, one, facet=False) if one in (INK, STONE, PRU) else line_body(one, 1.6)
        wm = caps_body(one, None)
    else:
        m = mark_body(**mark_for(ground, light=light))
        wm = caps_body(INK if ground in LIGHT else CREAM, lit_for(ground))
    body = m + f'<g transform="translate({fmt(100 + gap - 15 * s)} {fmt(50 + ch / 2)}) scale({s:.6f})">{wm}</g>'
    return _svg(f"-1 -1 {fmt(W + 2)} 102", body, w, h, style, "Antimony")

def stacked(ground=CREAM, one=None, w=None, h=None, style="", light=False):
    """Stacked lockup, as on the website: the capitals 1.36 times the mark's width, 0.37 of it below."""
    ww = 136.0; s = ww / CAPS_W; ch = CAPS_H * s; top = 137.0
    if one:
        m = mark_body(one, one, facet=False) if one in (INK, STONE, PRU) else line_body(one, 1.6)
        wm = caps_body(one, None)
    else:
        m = mark_body(**mark_for(ground, light=light))
        wm = caps_body(INK if ground in LIGHT else CREAM, lit_for(ground))
    body = f'<g transform="translate(18 0)">{m}</g><g transform="translate({fmt(-15 * s)} {fmt(top + ch)}) scale({s:.6f})">{wm}</g>'
    return _svg(f"-1 -1 138 {fmt(top + ch + 3)}", body, w, h, style, "Antimony")

if __name__ == "__main__":
    print(Q["halves"][0][:300]); print(len(Q["stone"]))
    print(seam_line())

# ---------- Timeless Serif as outlines, for type inside the SVG masters ----------
_FONTS = {}
def _font(wght):
    if wght not in _FONTS:
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer
        f = TTFont(os.path.join(HERE, "../../../assets/fonts/TimelessSerifVF.woff2"))
        _FONTS[wght] = instancer.instantiateVariableFont(f, {"wght": wght})
    return _FONTS[wght]

def _kern(f, a, b):
    """Pair kerning from GPOS PairPos, format 1 and 2; enough for a short line."""
    try: lookups = f["GPOS"].table.LookupList.Lookup
    except Exception: return 0
    for lk in lookups:
        for st in lk.SubTable:
            if getattr(st, "ExtSubTable", None): st = st.ExtSubTable
            if getattr(st, "LookupType", 0) != 2 and type(st).__name__ != "PairPos": continue
            cov = st.Coverage.glyphs
            if a not in cov: continue
            if st.Format == 1:
                for pvr in st.PairSet[cov.index(a)].PairValueRecord:
                    if pvr.SecondGlyph == b: return getattr(pvr.Value1, "XAdvance", 0) or 0
            elif st.Format == 2:
                c1 = st.ClassDef1.classDefs.get(a, 0); c2 = st.ClassDef2.classDefs.get(b, 0)
                v = st.Class1Record[c1].Class2Record[c2].Value1
                if v is not None: return getattr(v, "XAdvance", 0) or 0
    return 0

def text_path(text, wght=400, size=100.0, x=0.0, y=0.0, track=0.0):
    """The text as one path in Timeless Serif, baseline at y. Returns (d, advance)."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    f = _font(wght); cmap = f.getBestCmap(); gs = f.getGlyphSet(); upm = f["head"].unitsPerEm
    s = size / upm; pen_x = 0.0; d = ""; prev = None
    for ch in text:
        g = cmap.get(ord(ch))
        if g is None: continue
        if prev: pen_x += _kern(f, prev, g)
        sp = SVGPathPen(gs)
        gs[g].draw(TransformPen(sp, (s, 0, 0, -s, x + pen_x * s, y)))
        d += sp.getCommands()
        pen_x += f["hmtx"][g][0] + track / s if s else 0
        prev = g
    return d, pen_x * s

ORBE = json.load(open(os.path.join(SRC, "orbe-trace.json")))
ORBE_BASE, ORBE_XH = 98.4, 66.0    # the wordmark's baseline and x-height, in lockup units (height 100)

def product(ground=CREAM, w=None, h=None, style="", maker="by Antimony"):
    """A product lockup: the product's own lockup, then "by Antimony" in Timeless Serif Light, at the product's x-height."""
    dark = ground not in LIGHT
    fg = CREAM if dark else STONE
    lit = SKY if dark else PRU
    size = ORBE_XH / (500 / 966)        # match x-heights
    gap = 34.0
    d, adv = text_path(maker, 300, size, ORBE["w"] + gap, ORBE_BASE)
    W = ORBE["w"] + gap + adv
    body = f'<path fill-rule="evenodd" fill="{fg}" d="{ORBE["mark"]}{ORBE["word"]}"/><path fill="{lit}" d="{d}"/>'
    return _svg(f"-2 -2 {fmt(W + 4)} 128", body, w, h, style, "Orbe, by Antimony")

# ---------- containers for icons ----------
def square_parts():
    seam, cav = Polygon(pts(G["seam"])), Polygon(pts(G["cav"]))
    st = box(0, 0, 100, 100).difference(unary_union([seam, cav]))
    return "".join(poly_d([(round(x, 2), round(y, 2)) for x, y in list(h.exterior.coords)[:-1]]) for h in st.geoms)
SQUARE = square_parts()

def app_icon(ground=CREAM, w=None, h=None, light=True):
    """For app icons: the stone fills the square, so the platform's own mask rounds it. The cut shows cream."""
    gid = uid("w")
    gem = (f'<linearGradient id="{gid}" x1="0" y1="21.5" x2="0" y2="81.5" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#E4F8FF"/><stop offset=".3" stop-color="#BDF0FF"/>'
           f'<stop offset=".32" stop-color="#9DE8FF"/><stop offset=".7" stop-color="#5FA6E8"/><stop offset="1" stop-color="#3F7FD0"/></linearGradient><path d="{Q["gem"]}" fill="url(#{gid})"/>') if light else f'<path d="{Q["gem"]}" fill="{SKY}"/>'
    body = f'<rect width="100" height="100" fill="{ground}"/><path d="{SQUARE}" fill="{STONE}"/>{gem}<path d="{Q["facet"]}" fill="#fff" fill-opacity="{.22 if light else .28}"/>'
    return _svg("0 0 100 100", body, w, h, "", "Antimony")

def favicon(px=None):
    """For browser tabs: the small drawing below 30 px; the cut filled with cream so it reads on light and dark tabs."""
    q = QS if (px or 99) < 30 else Q
    body = f'<rect width="100" height="100" rx="22" fill="{CREAM}"/><path d="{q["stone"]}" fill="{STONE}"/><path d="{q["gem"]}" fill="{SKY}"/><path d="{q["facet"]}" fill="#fff" fill-opacity=".28"/>'
    return _svg("0 0 100 100", body, px, px, "", "Antimony")
