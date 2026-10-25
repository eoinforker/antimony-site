"""Writes ../finalists/index.html: seven finalists from the four directions chosen (9, 13, 24, 48, 62), each in the same places."""
import math, os, sys, itertools
sys.path.insert(0, os.path.dirname(__file__))
from kit import WM, WM_Y0, WM_Y1
from crystal_geometry import pieces as crystal_pieces, HEX
INK, PAPER, COBALT, SKY = "#0B0D0C", "#F4F3EE", "#2448FF", "#94E6FF"
uid = itertools.count()
f = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")
def P(*pts): return "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"
def mir(half): return list(half) + [(100 - x, y) for x, y in reversed(half)]
def chan(a, b, w, ext=0):
    (x1, y1), (x2, y2) = a, b; dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy); ux, uy = dx / L, dy / L; nx, ny = -uy * w / 2, ux * w / 2
    x1, y1, x2, y2 = x1 - ux * ext, y1 - uy * ext, x2 + ux * ext, y2 + uy * ext
    return P((x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny))
WOLF = P(*mir([(50, 30), (60, 26), (74, 2), (86, 30), (99, 50), (86, 58), (70, 76), (58, 94), (50, 98)]))
EYES = P((31, 46), (45, 53), (43, 58), (29, 51)) + P((69, 46), (55, 53), (57, 58), (71, 51))
BLOCK = "M2.6 0H97.4Q100 0 100 2.6V97.4Q100 100 97.4 100H2.6Q0 100 0 97.4V2.6Q0 0 2.6 0Z"
ORBE = "M38 0H98.6Q100 0 100 1.4V98.6Q100 100 98.6 100H1.4Q0 100 0 98.6V38Z"
CP = crystal_pieces(); cpoly = lambda k: P(*CP[k])
# each finalist: (shape, cuts, accent path or None)
FIN = [
 ("wolf", "The Wolf", "Direction 9", WOLF, EYES, EYES,
  "Alchemists called antimony the wolf of metals: it devoured the dross in molten gold until only the gold was left. Front on, drawn so it can only be a wolf: tall ears set wide, a ruff at the cheeks, a long muzzle. A wolf's eyes are gold, so here the eyes carry the only colour.",
  "Fierce by nature. Kept from menace by its proportions: an upright head, open eyes, no teeth."),
 ("wolfa", "The Wolf A", "Directions 9 and 24", WOLF, chan((50, 37), (33.2, 84), 7) + chan((50, 37), (66.8, 84), 7) + chan((39, 66), (61, 66), 6), None,
  "The same wolf with an A struck down its face: the legs are the brow and the line of the muzzle, the bar sits under the eyes. The name and the myth in one strike.",
  "Busier than the others below 24 px; it needs its own small drawing."),
 ("ears", "The Ears", "Direction 13", P((4, 98), (31, 2), (47, 98)) + P((96, 98), (69, 2), (53, 98)), "", None,
  "The wolf reduced to its ears: two blades, their inner edges steeper than their outer, standing apart. Two that make one shape: an A without its bar, a crown of two, never alone.",
  "The most minimal of the six, and the most open to other readings: two peaks, two spikes."),
 ("punch", "The Punch", "Directions 24 and 48", ORBE, chan((56, -2), (28, 104), 10) + chan((56, -2), (84, 104), 10) + chan((38, 66), (74, 66), 9), None,
  "An A struck right through a block of metal, cut from the same stock as Orbe: the same 45 degree corner, the same radii. The parent and the product are visibly one family.",
  "Binds Antimony's shape to Orbe's; strong as a pair, plainer alone."),
 ("punchg", "The Punch, gold", "Directions 24 and 48", BLOCK, chan((50, -2), (24, 104), 11) + chan((50, -2), (76, 104), 11), P((50, 24), (63.6, 58), (36.4, 58)),
  "A square block struck through by the A's legs from top to foot. The counter between them, what the strike leaves, is the gold: refined, and the only colour.",
  "The most direct; close to the confident block marks you named."),
 ("crystal", "The Crystal A", "Direction 62", P(*HEX), None, None,
  "A hexagon, the shape of antimony's crystal, struck through with the triangle already inside it. The counter is the gold. The full study is on its own page.",
  "A hexagon with a triangle can recall a twenty sided die; the bar settles it as an A."),
]
def render(key, fill=INK, accent=COBALT, style="", pad=2):
    i = next(uid)
    _, _, _, shape, cuts, acc, _, _ = next(x for x in FIN if x[0] == key)
    if key == "crystal":
        body = "".join(f'<path d="{cpoly(k)}" fill="{accent if k == "counter" else fill}" stroke="{accent if k == "counter" else fill}" stroke-width=".8" stroke-linejoin="round"/>' for k in ("wing_l", "wing_r", "foot", "counter"))
        return f'<svg viewBox="{-pad} {-pad} {100 + 2*pad} {100 + 2*pad}" style="{style}" aria-hidden="true">{body}</svg>'
    m = (f'<defs><mask id="f{i}" maskUnits="userSpaceOnUse" x="-10" y="-10" width="120" height="120"><rect x="-10" y="-10" width="120" height="120" fill="#fff"/><path d="{cuts}" fill="#000"/></mask></defs>' if cuts else "")
    a = f'<path d="{acc}" fill="{accent}"/>' if acc else ""
    return (f'<svg viewBox="{-pad} {-pad} {100 + 2*pad} {100 + 2*pad}" style="{style}" aria-hidden="true">{m}<path d="{shape}" fill="{fill}"{f" mask=\"url(#f{i})\"" if cuts else ""} stroke="{fill}" stroke-width=".8" stroke-linejoin="round"/>{a}</svg>')
def wordmark(fill=INK, style=""):
    return f'<svg viewBox="-10 {WM_Y0} {WM["w"] + 20} {WM_Y1 - WM_Y0}" style="{style}" role="img" aria-label="Antimony"><path d="{WM["letters"]}" fill="{fill}"/><path d="{WM["dot"]}" fill="{fill}"/></svg>'
def av(key, size=48, pad=8): return f'<span class="av" style="width:{size}px;height:{size}px;padding:{pad}px">{render(key, PAPER, SKY, "width:100%;height:100%")}</span>'
def row(key, name): return f'<div class="row">{av(key)}<div><b>{name}</b><span>Software Development</span></div></div>'
secs = ""
for key, name, tag, shape, cuts, acc, story, risk in FIN:
    link = '<p><a href="https://claude.ai/artifact/4thud9JNDU8JhHWeBZLsG7">The Crystal A, taken all the way</a></p>' if key == "crystal" else ""
    secs += f'''
<section class="fin" id="{key}">
  <div class="big">{render(key, style="width:100%;height:auto")}</div>
  <div class="txt">
    <span class="eyebrow">{tag}</span><h2>{name}</h2><p>{story}</p><p class="risk">{risk}</p>{link}
    <div class="ctx">
      <span class="tile ink">{render(key, PAPER, SKY, "width:100%;height:100%")}</span>
      <span class="tile cob">{render(key, PAPER, INK, "width:100%;height:100%")}</span>
      <span class="sizes">{"".join(f'<i style="width:{s}px;height:{s}px">{render(key, style="width:100%;height:100%", pad=1)}</i>' for s in (16, 24, 32))}</span>
    </div>
    <div class="lock">{render(key, style="height:54px;width:54px")}{wordmark(INK, "height:40px;width:auto")}</div>
  </div>
</section>'''
lineup = "".join(row(k, n) for k, n, *_ in FIN)
dark = "".join(f'<span class="dk">{render(k, PAPER, SKY, "width:100%;height:100%")}</span>' for k, *_ in FIN)
html = f'''<title>Antimony Finalists</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* Seven finalists, each given exactly the same treatment so they can be judged against each other and against the marks we admire. */
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-400.woff2) format("woff2"); font-weight: 400; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-500.woff2) format("woff2"); font-weight: 500; font-display: swap; }}
@font-face {{ font-family: "Commit Mono"; src: url(fonts/CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
:root {{ --ink: {INK}; --paper: {PAPER}; --cobalt: {COBALT}; --sky: {SKY}; --rule: rgba(11,13,12,.13); --dim: #5C6461;
  --serif: "Timeless Serif", "Iowan Old Style", Georgia, serif; --sans: "Timeless Sans", "Helvetica Neue", Arial, sans-serif; --mono: "Commit Mono", ui-monospace, Menlo, monospace; color-scheme: light; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: var(--paper); color: var(--ink); }}
body {{ font: 400 16px/1.55 var(--sans); -webkit-font-smoothing: antialiased; }}
.band {{ padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 60px; border-bottom: 1px solid var(--rule); }}
.band.ink {{ background: var(--ink); color: var(--paper); --rule: rgba(244,243,238,.14); --dim: #8A9592; }}
.in {{ max-width: 1120px; margin-inline: auto; display: grid; gap: 28px; }}
.eyebrow {{ font: 500 11.5px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--dim); }}
h1 {{ font: 400 clamp(40px, 6vw, 76px)/1 var(--serif); letter-spacing: -.02em; text-wrap: balance; max-width: 15em; }}
h2 {{ font: 400 clamp(30px, 3.8vw, 44px)/1.04 var(--serif); letter-spacing: -.012em; }}
p {{ max-width: 36em; }} .dim {{ color: var(--dim); }} a {{ color: var(--cobalt); }}
.lede {{ font: 400 clamp(18px, 1.9vw, 21px)/1.5 var(--serif); max-width: 34em; }}
.fin {{ display: grid; grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr); gap: 44px; align-items: start; padding-block: 44px; border-top: 1px solid var(--rule); }}
.big {{ background: #FBFAF6; border: 1px solid var(--rule); aspect-ratio: 1; max-width: 100%; display: grid; place-items: center; padding: 18%; }}
.txt {{ display: grid; gap: 14px; align-content: start; min-width: 0; }}
.risk {{ font-size: 14.5px; color: var(--dim); border-left: 2px solid var(--rule); padding-left: 12px; }}
.ctx {{ display: flex; gap: 12px; align-items: end; flex-wrap: wrap; padding-top: 6px; }}
.tile {{ width: 112px; height: 112px; display: block; padding: 24px; }} .tile.ink {{ background: var(--ink); }} .tile.cob {{ background: var(--cobalt); }}
.sizes {{ display: flex; gap: 14px; align-items: end; padding: 12px 14px; border: 1px solid var(--rule); height: 112px; }} .sizes i {{ display: block; }}
.lock {{ display: flex; gap: 16px; align-items: center; padding: 22px; border: 1px solid var(--rule); background: #FBFAF6; flex-wrap: wrap; }}
.lock svg {{ display: block; max-width: 100%; }}
.av {{ display: block; flex: none; border-radius: 4px; background: var(--ink); }}
.list {{ background: #fff; border: 1px solid var(--rule); border-radius: 10px; padding: 4px 16px; color: #191919; max-width: 520px; }}
.row {{ display: flex; gap: 12px; align-items: center; padding: 11px 0; border-bottom: 1px solid rgba(11,13,12,.08); }} .row:last-child {{ border-bottom: 0; }}
.row b {{ display: block; font: 500 15px/1.25 var(--sans); }} .row span {{ font-size: 12.5px; color: #666; }}
.line {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 14px; }}
.dk {{ aspect-ratio: 1; max-width: 100%; display: block; padding: 22%; border: 1px solid var(--rule); }}
.two {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 36px; align-items: start; }}
@media (max-width: 860px) {{ .fin, .two {{ grid-template-columns: 1fr; gap: 24px; }} .line {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }} .band {{ padding-block: 44px; }} .tile, .sizes {{ width: 96px; height: 96px; padding: 20px; }} .sizes {{ width: auto; }} }}
</style>

<section class="band"><div class="in">
  <span class="eyebrow">Antimony, the mark, finalists</span>
  <h1>Six finalists from the four directions you chose.</h1>
  <p class="lede">The wolf (9), the ears (13), the struck block (24 and 48) and the hexagon (62). Each is drawn to exact geometry and shown in exactly the same places, so they can be judged against each other and against the marks you named: solid, few parts, confident in a square.</p>
</div></section>

<section class="band ink"><div class="in">
  <span class="eyebrow">Side by side</span>
  <h2>As avatars, at the same size, on ink.</h2>
  <div class="line">{dark}</div>
  <div class="two"><div class="list">{lineup}</div><p class="dim">In a list at real size, which is where most people will meet the mark first. Look for the one you can still see when you look away.</p></div>
</div></section>

<section class="band"><div class="in">{secs}</div></section>
'''
open("../finalists/index.html", "w").write(html); print(len(html))
