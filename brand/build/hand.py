"""Eight marks drawn with the brush: the crystal by hand, and seven new marks from the world of Nurture."""
import math, os, sys, itertools
sys.path.insert(0, os.path.dirname(__file__))
from brush import stroke, dab, scribble, GRAIN
from kit import WM, WM_Y0, WM_Y1
INK, SUN, PRUSSIAN, WASHI, SKY, FIELD, PINE, DAWN = "#1A1D1C", "#F4C84A", "#1F3F7A", "#F3ECDD", "#9CCBEA", "#8DBF6A", "#2F5D50", "#F2B6A0"
uid = itertools.count()
def svg(parts, ink=INK, gold=SUN, grain=True, style="", vb="0 0 100 100"):
    i = next(uid); fid = f"g{i}"
    body = "".join(f'<path d="{d}" fill="{gold if role == "gold" else ink if role == "ink" else role}"/>' for role, d in parts)
    flt = GRAIN.format(id=fid, seed=i % 7 + 2) if grain else ""
    return f'<svg viewBox="{vb}" style="{style}" aria-hidden="true"><defs>{flt}</defs><g{f" filter=\"url(#{fid})\"" if grain else ""}>{body}</g></svg>'
M = {}
# 1 The crystal, by hand: the same idea, drawn in seven strokes and a dab of gold
M["crystal"] = ("The crystal, by hand", "The mark we had, drawn rather than built: six strokes for the hexagon's walls, the A left as paper, the gold coloured in.", [
    ("ink", stroke([(48, 6), (12, 27), (10, 62)], 13, 11, taper=(.1, .3))), ("ink", stroke([(53, 6), (88, 26), (90, 63)], 13, 12, taper=(.1, .3))),
    ("ink", stroke([(16, 76), (50, 95), (84, 76)], 15, 13, taper=(.15, .15))), ("ink", stroke([(27, 66), (73, 66)], 10, 14)),
    ("gold", scribble(41, 34, 59, 54, 9, 4.2, 15, lean=0)), ("ink", stroke([(50, 14), (31, 57), (69, 57), (50, 14)], 2.6, 16, wobble=.6, press=.15))])
# 2 The mountain: an A is a mountain. One stroke up and over, the sun coming up behind it
M["mountain"] = ("The mountain", "An A is a mountain. One stroke up and over, the way a child draws Fuji, and the sun coming up behind the peak: what is left at the end of the climb.", [
    ("gold", dab(66, 34, 15, 21)), ("ink", stroke([(8, 90), (30, 52), (48, 18), (56, 30), (70, 54), (92, 90)], 12, 22, taper=(.08, .12), wobble=1.2)),
    ("ink", stroke([(30, 66), (70, 66)], 7, 23, taper=(.2, .3)))])
# 3 The window: nature seen through a window
M["window"] = ("The window", "A window drawn freehand, a hill line and a low sun inside it. The work is the room; the window is what it is for.", [
    ("ink", stroke([(14, 12), (86, 11), (88, 88), (13, 89), (14, 12)], 9, 31, taper=(.04, .04), wobble=1)),
    ("gold", dab(38, 48, 10, 32)), ("ink", stroke([(18, 70), (36, 60), (54, 66), (70, 54), (84, 60)], 6, 33, taper=(.15, .2)))])
# 4 The A, coloured in: a free A in one stroke, its counter scribbled in gold, a little outside the lines
M["scribble"] = ("The A, coloured in", "A free A drawn in one stroke, and the space inside it coloured in by hand in gold, a little outside the lines.", [
    ("gold", scribble(36, 36, 62, 60, 10, 5, 41, lean=-.4)),
    ("ink", stroke([(14, 94), (40, 30), (50, 8), (62, 32), (88, 94)], 11, 42, taper=(.06, .1), wobble=1.1)), ("ink", stroke([(27, 66), (74, 63)], 8, 43))])
# 5 The road: a road winding up into the hills, as in every print of the Tokaido
M["road"] = ("The road", "A road winding up into the hills, as in every print of the Tokaido. Fifty three stations; the work is a long way, walked together.", [
    ("gold", dab(72, 22, 9, 51)), ("ink", stroke([(10, 32), (30, 22), (52, 30), (76, 44), (94, 40)], 6, 52, taper=(.2, .2))),
    ("ink", stroke([(34, 96), (44, 80), (58, 70), (52, 58), (60, 48)], 15, 53, taper=(.02, .5), wobble=1))])
# 6 The sprout: nurture, literally. Two leaves from a line of earth
M["sprout"] = ("The sprout", "Nurture, literally: a seed that has come up. Two leaves from one stem, a line of earth beneath.", [
    ("ink", stroke([(14, 86), (50, 84), (86, 87)], 7, 61, taper=(.2, .2))), ("ink", stroke([(50, 84), (50, 60), (52, 42)], 7, 62, taper=(.02, .3))),
    ("gold", stroke([(51, 46), (36, 34), (22, 34), (32, 46), (51, 46)], 7.5, 63, taper=(.05, .05), wobble=.6)),
    ("ink", stroke([(52, 40), (66, 22), (82, 18), (76, 34), (52, 40)], 7.5, 64, taper=(.05, .05), wobble=.6))])
# 7 Two: two marks side by side, never alone; one in ink, one in gold
M["two"] = ("Two", "Antimony is almost never found alone. Two strokes standing side by side, one ink, one gold: you and us.", [
    ("ink", stroke([(34, 90), (38, 52), (36, 14)], 16, 71, taper=(.12, .3), wobble=1.3)), ("gold", stroke([(62, 90), (66, 54), (64, 22)], 16, 72, taper=(.12, .3), wobble=1.3))])
# 8 The pencil A: the A drawn with the pencil of an old paint program, pixel by pixel, the gold filled with the bucket
def pixel_a():
    rows = ["......#.......", ".....###......", ".....#o#......", "....##o##.....", "....#ooo#.....", "...##ooo##....", "...#ooooo#....", "..#########...", "..##.....##...", ".##.......##..", ".#.........#..", "##.........##."]
    out = []; s = 100 / 14
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            if c != ".": out.append(("gold" if c == "o" else "ink", f"M{i * s + 1:.1f} {j * s + 7:.1f}h{s:.2f}v{s:.2f}h-{s:.2f}Z"))
    return out
M["pencil"] = ("The pencil A", "The A drawn with the pencil of an old paint program, one pixel at a time, and its counter filled with the bucket.", pixel_a())
def wordmark(fill=INK, dot=SUN, style=""):
    return f'<svg viewBox="-10 {WM_Y0} {WM["w"] + 20} {WM_Y1 - WM_Y0}" style="{style}" role="img" aria-label="Antimony"><path d="{WM["letters"]}" fill="{fill}"/><path d="{WM["dot"]}" fill="{dot}"/></svg>'
cards = ""
for k, (name, text, parts) in M.items():
    grain = k != "pencil"
    cards += f'''<article class="card">
  <div class="big">{svg(parts, grain=grain, style="width:100%;height:100%")}</div>
  <div class="row"><span class="t ink">{svg(parts, WASHI, SUN, grain, "width:100%;height:100%")}</span><span class="t sky">{svg(parts, PRUSSIAN, WASHI, grain, "width:100%;height:100%")}</span>
  <span class="sz">{"".join(f'<i style="width:{s}px;height:{s}px">{svg(parts, grain=False, style="width:100%;height:100%")}</i>' for s in (16, 24, 32))}</span></div>
  <div class="lock">{svg(parts, grain=grain, style="width:44px;height:44px;flex:none")}{wordmark(INK, SUN, "height:30px;width:auto")}</div>
  <h2>{name}</h2><p>{text}</p></article>'''
html = f'''<title>Antimony, By Hand</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* Eight marks drawn with a brush on washi, each shown large, reversed, on sky, small, and with the name. */
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifItalicVF.woff2) format("woff2"); font-weight: 200 700; font-style: italic; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-400.woff2) format("woff2"); font-weight: 400; font-display: swap; }}
:root {{ --ink: {INK}; --washi: {WASHI}; --prussian: {PRUSSIAN}; --sky: {SKY}; --rule: rgba(31,63,122,.16); --dim: #5E6A73; color-scheme: light; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: var(--washi); color: var(--ink); }}
body {{ font: 400 15.5px/1.55 "Timeless Sans", "Helvetica Neue", Arial, sans-serif; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 56px 80px; }}
.in {{ max-width: 1160px; margin-inline: auto; display: grid; gap: 40px; }}
h1 {{ font: 400 clamp(42px, 6.6vw, 88px)/.98 "Timeless Serif", Georgia, serif; letter-spacing: -.02em; color: var(--prussian); max-width: 13em; text-wrap: balance; }}
.lede {{ font: 400 clamp(18px, 1.9vw, 22px)/1.5 "Timeless Serif", Georgia, serif; max-width: 34em; }}
.grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 40px 22px; }}
.card {{ display: grid; gap: 10px; align-content: start; min-width: 0; }}
.big {{ aspect-ratio: 1; max-width: 100%; padding: 14%; background: #F8F3E7; border: 1px solid var(--rule); }}
.big svg, .t svg {{ display: block; }}
.row {{ display: grid; grid-template-columns: 1fr 1fr 1.25fr; gap: 6px; }}
.t {{ aspect-ratio: 1; max-width: 100%; padding: 18%; display: block; }} .t.ink {{ background: var(--ink); }} .t.sky {{ background: var(--sky); }}
.sz {{ display: flex; gap: 6px; align-items: end; justify-content: center; padding: 8px 4px; border: 1px solid var(--rule); }} .sz i {{ display: block; flex: none; }}
.lock {{ display: flex; gap: 10px; align-items: center; padding: 12px; border: 1px solid var(--rule); background: #F8F3E7; overflow: hidden; }}
.lock svg {{ display: block; max-width: 100%; }}
h2 {{ font: 400 24px/1.15 "Timeless Serif", Georgia, serif; color: var(--prussian); margin-top: 4px; }}
.card p {{ font-size: 14.5px; color: var(--dim); }}
.end {{ border-top: 1px solid var(--rule); padding-top: 28px; display: grid; gap: 14px; }}
.end p {{ max-width: 40em; }}
@media (max-width: 980px) {{ .grid {{ grid-template-columns: 1fr 1fr; }} }}
@media (max-width: 520px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
<div class="in">
  <h1>Eight marks, drawn by hand.</h1>
  <p class="lede">One is the crystal, redrawn with a brush to see whether the hand alone was what was missing. The other seven are new, from the world of Nurture: things made, things grown, things seen through a window. Each is shown large, reversed, on sky, small, and with the name.</p>
  <div class="grid">{cards}</div>
  <div class="end"><p>These are drawn with a brush I wrote, so each stroke tapers, swells and wanders like ink; it is close to a hand, not a hand. Whichever one you choose, the final mark should be drawn by a person, with a real brush or pencil, and scanned. I can then build everything around that scan.</p></div>
</div>
'''
open("../hand/index.html", "w").write(html); print(len(html))
