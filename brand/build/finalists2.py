"""Writes ../finalists/index.html again: the wolves gone; the Punch, the Crystal and the Ears, each in refined variants."""
import math, os, sys, itertools
sys.path.insert(0, os.path.dirname(__file__))
from kit import WM, WM_Y0, WM_Y1
from crystal_geometry import clip, side
INK, PAPER, COBALT, SKY = "#0B0D0C", "#F4F3EE", "#2448FF", "#94E6FF"
uid = itertools.count()
f = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")
def P(*pts): return "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"
S3 = math.sqrt(3); T30 = math.tan(math.radians(30))

def struck_pieces(outline, legs, W, bar_y=None, Wb=None, mid=(50, 70)):
    """Cut an outline (a convex polygon) by an A: two legs (each a pair of points on the centre line) and an optional bar.
    Returns the pieces, and which one is the counter (the piece between the legs, above the bar)."""
    (a1, b1), (a2, b2) = legs
    Wb = Wb or W * .9
    outL = (min(p[0] for p in outline) - 1, mid[1]); outR = (max(p[0] for p in outline) + 1, mid[1])
    wl = clip(outline, *side(a1, b1, W / 2, outL)); wr = clip(outline, *side(a2, b2, W / 2, outR))
    inner = clip(clip(outline, *side(a1, b1, W / 2, mid)), *side(a2, b2, W / 2, mid))
    if bar_y is None: return {"wing_l": wl, "wing_r": wr, "counter": inner}
    counter = clip(inner, 0, -1, bar_y - Wb / 2); foot = clip(inner, 0, 1, -(bar_y + Wb / 2))
    return {"wing_l": wl, "wing_r": wr, "counter": counter, "foot": foot}
def rounded_square(r=2.6, n=4):
    pts = []
    for cx, cy, a0 in [(100 - r, r, -90), (100 - r, 100 - r, 0), (r, 100 - r, 90), (r, r, 180)]:
        for k in range(n + 1): a = math.radians(a0 + 90 * k / n); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts
SQ = rounded_square()
ORBE = [(38, 0), (98.6, 0), (100, 1.4), (100, 98.6), (98.6, 100), (1.4, 100), (0, 98.6), (0, 38)]
def hexagon(rot=-90, R=50): return [(50 + R * math.cos(math.radians(rot + 60 * k)), 50 + R * math.sin(math.radians(rot + 60 * k))) for k in range(6)]
HEXP, HEXF = hexagon(), hexagon(0)
def drop(top, half_angle, length=140): return (top, (top[0] - length * math.sin(math.radians(half_angle)), top[1] + length * math.cos(math.radians(half_angle))))
def mirror_leg(leg): (a, b) = leg; return ((100 - a[0], a[1]), (100 - b[0], b[1]))
V = {}
# THE PUNCH
legl = ((50, -3), (24, 103)); V["punch_gold"] = ("The Punch, gold", struck_pieces(SQ, (legl, mirror_leg(legl)), 11), "A square block struck by the A's legs from top to foot; what the strike leaves between them is the gold.")
legl = drop((50, -6), 30); V["punch_60"] = ("The Punch, 60 degrees", struck_pieces(SQ, (legl, mirror_leg(legl)), 10, bar_y=70), "The legs at 60 degrees, the angle of an equilateral triangle, so the A inside the block is the same A as the crystal's.")
legl = ((50, -3), (24, 103)); V["punch_bar"] = ("The Punch, barred", struck_pieces(SQ, (legl, mirror_leg(legl)), 11, bar_y=66), "The full A: the bar struck as well, so the gold is a triangle above it.")
legl = ((56, -3), (30, 103)); V["punch_orbe"] = ("The Punch, Orbe's stock", struck_pieces(ORBE, (legl, ((56, -3), (82, 103))), 11, mid=(56, 70)), "Cut from Orbe's block, its 45 degree corner kept: parent and product from one piece of metal.")
# THE CRYSTAL
top = (50, 0)
V["crystal"] = ("The Crystal A", struck_pieces(HEXP, ((top, (50 - 50 * S3 / 2, 75)), (top, (50 + 50 * S3 / 2, 75))), 9, bar_y=56.25, mid=(50, 60)), "The hexagon struck through with the triangle already inside it.")
V["crystal_heavy"] = ("The Crystal A, heavy", struck_pieces(HEXP, ((top, (50 - 50 * S3 / 2, 75)), (top, (50 + 50 * S3 / 2, 75))), 12, bar_y=56.25, mid=(50, 60)), "The same with wider strikes: louder at small sizes, more like a stamp.")
legl = drop((50, 14), 30); V["crystal_closed"] = ("The Crystal, closed", struck_pieces(HEXP, (legl, mirror_leg(legl)), 9, bar_y=62, mid=(50, 64)), "The A starts inside the crystal, so the top corner stays whole and the legs leave through the foot; no die.")
legl = drop((50, -2), 30); V["crystal_flat"] = ("The Crystal, flat", struck_pieces(HEXF, (legl, mirror_leg(legl)), 9, bar_y=62, mid=(50, 64)), "The hexagon turned to sit flat, like a nut or an ingot seen end on; the A struck through its top edge.")
# THE EARS
V["ears"] = ("The Ears", {"wing_l": [(4, 98), (31, 2), (47, 98)], "wing_r": [(96, 98), (69, 2), (53, 98)]}, "Two blades standing apart: an A without its bar, two that make one shape.")
V["ears_bar"] = ("The Ears, joined", {"wing_l": [(4, 98), (31, 2), (47, 98)], "wing_r": [(96, 98), (69, 2), (53, 98)], "counter": [(38.5, 68), (61.5, 68), (61.5, 76), (38.5, 76)]}, "The same blades held by a bar of gold between them.")
GROUPS = [("The Punch", "Directions 24 and 48", ["punch_gold", "punch_60", "punch_bar", "punch_orbe"]),
          ("The Crystal", "Direction 62", ["crystal", "crystal_heavy", "crystal_closed", "crystal_flat"]),
          ("The Ears", "Direction 13", ["ears", "ears_bar"])]
def render(key, fill=INK, accent=COBALT, style="", pad=2):
    pcs = V[key][1]
    body = "".join(f'<path d="{P(*pts)}" fill="{accent if k == "counter" else fill}" stroke="{accent if k == "counter" else fill}" stroke-width=".7" stroke-linejoin="round"/>' for k, pts in pcs.items() if pts)
    return f'<svg viewBox="{-pad} {-pad} {100 + 2*pad} {100 + 2*pad}" style="{style}" aria-hidden="true">{body}</svg>'
def wordmark(style=""): return f'<svg viewBox="-10 {WM_Y0} {WM["w"] + 20} {WM_Y1 - WM_Y0}" style="{style}" role="img" aria-label="Antimony"><path d="{WM["letters"]}" fill="{INK}"/><path d="{WM["dot"]}" fill="{INK}"/></svg>'
def av(key): return f'<span class="av">{render(key, PAPER, SKY, "width:100%;height:100%")}</span>'
rows = "".join(f'<div class="row">{av(k)}<div><b>{V[k][0]}</b><span>Software Development</span></div></div>' for _, _, ks in GROUPS for k in ks)
dark = "".join(f'<span class="dk">{render(k, PAPER, SKY, "width:100%;height:100%")}</span>' for _, _, ks in GROUPS for k in ks)
secs = ""
for name, tag, ks in GROUPS:
    cards = ""
    for k in ks:
        cards += f'''<figure class="card"><div class="big">{render(k, style="width:100%;height:auto")}</div>
          <div class="ctx"><span class="t ink">{render(k, PAPER, SKY, "width:100%;height:100%")}</span><span class="t cob">{render(k, PAPER, INK, "width:100%;height:100%")}</span>
          <span class="sz">{"".join(f'<i style="width:{s}px;height:{s}px">{render(k, style="width:100%;height:100%", pad=1)}</i>' for s in (16, 24, 32))}</span></div>
          <div class="lock">{render(k, style="height:40px;width:40px")}{wordmark("height:30px;width:auto")}</div>
          <figcaption><b>{V[k][0]}</b>{V[k][2]}</figcaption></figure>'''
    secs += f'<section class="band"><div class="in"><span class="eyebrow">{tag}</span><h2>{name}</h2><div class="cards">{cards}</div></div></section>'
html = f'''<title>Antimony Finalists</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* The struck mark in three families, each variant given the same treatment: large, on ink, on cobalt, small, and with the name. */
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-400.woff2) format("woff2"); font-weight: 400; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-500.woff2) format("woff2"); font-weight: 500; font-display: swap; }}
@font-face {{ font-family: "Commit Mono"; src: url(fonts/CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
:root {{ --ink: {INK}; --paper: {PAPER}; --cobalt: {COBALT}; --sky: {SKY}; --rule: rgba(11,13,12,.13); --dim: #5C6461;
  --serif: "Timeless Serif", "Iowan Old Style", Georgia, serif; --sans: "Timeless Sans", "Helvetica Neue", Arial, sans-serif; --mono: "Commit Mono", ui-monospace, Menlo, monospace; color-scheme: light; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: var(--paper); color: var(--ink); }}
body {{ font: 400 16px/1.55 var(--sans); -webkit-font-smoothing: antialiased; }}
.band {{ padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 56px; border-bottom: 1px solid var(--rule); }}
.band.ink {{ background: var(--ink); color: var(--paper); --rule: rgba(244,243,238,.14); --dim: #8A9592; }}
.in {{ max-width: 1160px; margin-inline: auto; display: grid; gap: 26px; }}
.eyebrow {{ font: 500 11.5px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--dim); }}
h1 {{ font: 400 clamp(38px, 5.6vw, 70px)/1 var(--serif); letter-spacing: -.02em; text-wrap: balance; max-width: 16em; }}
h2 {{ font: 400 clamp(30px, 3.8vw, 44px)/1.04 var(--serif); letter-spacing: -.012em; }}
p {{ max-width: 36em; }} .dim {{ color: var(--dim); }}
.lede {{ font: 400 clamp(18px, 1.9vw, 21px)/1.5 var(--serif); max-width: 34em; }}
.cards {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 18px; align-items: start; }}
.card {{ display: grid; gap: 10px; min-width: 0; }}
.big {{ background: #FBFAF6; border: 1px solid var(--rule); aspect-ratio: 1; max-width: 100%; display: grid; place-items: center; padding: 18%; }}
.ctx {{ display: grid; grid-template-columns: 1fr 1fr 1.25fr; gap: 6px; }}
.t {{ aspect-ratio: 1; max-width: 100%; display: block; padding: 22%; }} .t.ink {{ background: var(--ink); }} .t.cob {{ background: var(--cobalt); }}
.sz {{ display: flex; gap: 6px; align-items: end; justify-content: center; padding: 8px 6px; border: 1px solid var(--rule); }} .sz i {{ display: block; flex: none; }}
.lock {{ display: flex; gap: 10px; align-items: center; padding: 14px; border: 1px solid var(--rule); background: #FBFAF6; overflow: hidden; }}
.lock svg {{ display: block; flex: none; max-width: 100%; }}
figcaption {{ font-size: 14px; color: var(--dim); }} figcaption b {{ display: block; color: var(--ink); font: 500 15px var(--sans); margin-bottom: 3px; }}
.line {{ display: grid; grid-template-columns: repeat(10, minmax(0, 1fr)); gap: 10px; }}
.dk {{ aspect-ratio: 1; max-width: 100%; display: block; padding: 22%; border: 1px solid var(--rule); }}
.two {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 36px; align-items: start; }}
.av {{ width: 48px; height: 48px; padding: 8px; display: block; flex: none; border-radius: 4px; background: var(--ink); }}
.list {{ background: #fff; border: 1px solid var(--rule); border-radius: 10px; padding: 4px 16px; color: #191919; }}
.row {{ display: flex; gap: 12px; align-items: center; padding: 10px 0; border-bottom: 1px solid rgba(11,13,12,.08); }} .row:last-child {{ border-bottom: 0; }}
.row b {{ display: block; font: 500 15px/1.25 var(--sans); }} .row span {{ font-size: 12.5px; color: #666; }}
@media (max-width: 960px) {{ .cards {{ grid-template-columns: 1fr 1fr; }} .line {{ grid-template-columns: repeat(5, minmax(0, 1fr)); }} .two {{ grid-template-columns: 1fr; }} }}
@media (max-width: 520px) {{ .cards {{ grid-template-columns: 1fr; }} .band {{ padding-block: 42px; }} }}
</style>
<section class="band"><div class="in">
  <span class="eyebrow">Antimony, the mark, finalists</span>
  <h1>The struck A, in three families.</h1>
  <p class="lede">The wolves are gone. What is left is the idea your picks shared: a solid piece of metal with the A struck through it, and the gold left where the strike was. Ten variants across the Punch, the Crystal and the Ears, each in the same places.</p>
</div></section>
<section class="band ink"><div class="in">
  <span class="eyebrow">Side by side</span>
  <h2>All ten, as avatars, on ink.</h2>
  <div class="line">{dark}</div>
  <div class="two"><div class="list">{rows}</div><p class="dim">At real size in a list. Look for the one you can still see when you look away, then tell me its name.</p></div>
</div></section>
{secs}
'''
open("../finalists/index.html", "w").write(html); print(len(html))
