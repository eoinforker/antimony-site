"""The Antimony mark, the Crystal A, and everything drawn from it. Every page and export imports from here.

A regular hexagon, pointy top, radius 50. Join its top corner to its two lower side corners: an equilateral triangle, the A
already inside the crystal. The triangle's sides are struck through the hexagon as channels W wide, and the bar is struck
three quarters of the way down the A. Four pieces remain: two wings, the counter, the foot. The counter is the gold.
"""
import json, math, os, re
from crystal_geometry import pieces, HEX, TOP, LL, LR, V
from kit import WM, WM_Y0, WM_Y1
HERE = os.path.dirname(os.path.abspath(__file__))
INK, PAPER, COBALT, SKY = "#0B0D0C", "#F4F3EE", "#2448FF", "#94E6FF"
PC = pieces()
PX = json.load(open(os.path.join(HERE, "crystal_pixels.json")))
ORDER = ("wing_l", "wing_r", "foot", "counter")
f = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")
poly = lambda pts: "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"
def gold_for(ground): return {INK: SKY, COBALT: INK}.get(ground, COBALT)
def mark_paths(fill=INK, gold=COBALT, soft=.8):
    return "".join(f'<path d="{poly(PC[k])}" fill="{gold if k == "counter" else fill}" stroke="{gold if k == "counter" else fill}" stroke-width="{soft}" stroke-linejoin="round"/>' for k in ORDER)
def mark(fill=INK, gold=None, style="", pad=1.5, line=None, cls="", label=True):
    gold = gold or (COBALT if fill == INK else SKY)
    body = ("".join(f'<path d="{poly(PC[k])}" fill="none" stroke="{fill}" stroke-width="{line}" stroke-linejoin="round"/>' for k in ORDER) if line else mark_paths(fill, gold))
    lab = 'role="img" aria-label="Antimony"' if label else 'aria-hidden="true"'
    return f'<svg class="{cls}" viewBox="{-pad} {-pad} {100 + 2 * pad} {100 + 2 * pad}" style="{style}" {lab}>{body}</svg>'
# the wordmark: Timeless Serif, its i dotted with the gold, a small triangle
_n = list(map(float, re.findall(r"-?\d+\.?\d*", WM["dot"])))
_dx, _dy = _n[0::2], _n[1::2]; _cx = (min(_dx) + max(_dx)) / 2; _cy = (min(_dy) + max(_dy)) / 2; _r = (max(_dx) - min(_dx)) / 2 * 1.05
DOT = poly([(_cx, _cy - _r), (_cx + _r * .996, _cy + _r * .575), (_cx - _r * .996, _cy + _r * .575)])
def wordmark(fill=INK, gold=None, style=""):
    gold = gold or fill
    return (f'<svg viewBox="-10 {WM_Y0} {WM["w"] + 20} {WM_Y1 - WM_Y0}" style="{style}" role="img" aria-label="Antimony">'
            f'<path d="{WM["letters"]}" fill="{fill}"/><path d="{DOT}" fill="{gold}"/></svg>')
LOCK_RATIO = 1.42          # the mark's height in cap heights
def lockup(fill=INK, gold=None, style=""):
    gold = gold or (COBALT if fill == INK else SKY)
    cap, base = WM["cap"], WM["asc"]; mh = cap * LOCK_RATIO; s = mh / 100
    ey = base - cap / 2 - mh / 2; gx = 100 * s + cap * .42
    y0 = min(ey, WM_Y0); y1 = max(ey + mh, WM_Y1)
    return (f'<svg viewBox="-6 {y0 - 6:.0f} {gx + WM["w"] + 12:.0f} {y1 - y0 + 12:.0f}" style="{style}" role="img" aria-label="Antimony">'
            f'<g transform="translate(0 {ey:.1f}) scale({s:.4f})">{mark_paths(fill, gold)}</g>'
            f'<g transform="translate({gx:.1f} 0)"><path d="{WM["letters"]}" fill="{fill}"/><path d="{DOT}" fill="{gold}"/></g></svg>')
def stacked(fill=INK, gold=None, style=""):
    gold = gold or (COBALT if fill == INK else SKY)
    cap = WM["cap"]; mh = cap * 2.6; s = mh / 100; ex = WM["w"] / 2 - 50 * s; ey = WM_Y0 - mh - cap * .55
    return (f'<svg viewBox="-10 {ey - 10:.0f} {WM["w"] + 20:.0f} {WM_Y1 - ey + 10:.0f}" style="{style}" role="img" aria-label="Antimony">'
            f'<g transform="translate({ex:.1f} {ey:.1f}) scale({s:.4f})">{mark_paths(fill, gold)}</g><path d="{WM["letters"]}" fill="{fill}"/><path d="{DOT}" fill="{gold}"/></svg>')
def lattice(cols, rows, size, lit=None, fill=INK, gold=COBALT, gap=.955, ox=0, oy=0, svg=True, w_=None, h_=None, lit_fill=None, only=False):
    """pointy topped crystals in rows, each a hair apart; lit = (i, j) of the one whose counter is gold"""
    w = size * math.sqrt(3) / 2; out = []
    for j in range(rows):
        for i in range(cols):
            x = ox + i * w + (j % 2) * w / 2 - w / 2; y = oy + j * size * .75 - size * .25
            on = lit is not None and (i, j) == tuple(lit)
            if only and not on: continue
            out.append(f'<g transform="translate({x + w / 2:.1f} {y + size / 2:.1f}) scale({size / 100 * gap:.4f}) translate(-50 -50)">{mark_paths((lit_fill or fill) if on else fill, gold if on else fill, 0)}</g>')
    W_ = w_ or cols * w - w / 2; H_ = h_ or rows * size * .75 - size * .25
    return f'<svg viewBox="0 0 {W_:.0f} {H_:.0f}" width="{W_:.0f}" height="{H_:.0f}" aria-hidden="true" style="display:block">{"".join(out)}</svg>' if svg else "".join(out)
def pixel_svg(rows, crisp=True, grid=True, size=None):
    n = len(rows)
    cells = "".join(f'<rect x="{i}" y="{j}" width="1" height="1" fill="{INK if c == "1" else COBALT}"/>' for j, r in enumerate(rows) for i, c in enumerate(r) if c != ".")
    g = ("<g stroke='rgba(11,13,12,.12)' stroke-width='" + f"{1.4 / n:.3f}" + "'>" + "".join(f'<line x1="{k}" y1="0" x2="{k}" y2="{n}"/><line x1="0" y1="{k}" x2="{n}" y2="{k}"/>' for k in range(n + 1)) + "</g>") if grid else ""
    sz = f' width="{size}" height="{size}"' if size else ""
    return f'<svg viewBox="0 0 {n} {n}"{sz} shape-rendering="{"crispEdges" if crisp else "auto"}" aria-hidden="true">{cells}{g}</svg>'
