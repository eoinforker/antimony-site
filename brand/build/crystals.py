"""Writes ../crystals/index.html: every crystal finalist, back, in the world of Arasaka and Ghost in the Shell."""
import os, sys, itertools
sys.path.insert(0, os.path.dirname(__file__))
import finalists2 as F
from kit import WM, WM_Y0, WM_Y1
RED, BLACK, BONE, STEEL = "#E0262D", "#0A0A0B", "#ECE7DC", "#8A9296"
uid = itertools.count()
P = F.P
ORIG = {"body": [(50, 5), (78, 29), (78, 71), (50, 95), (22, 71), (22, 29)], "cuts": [[(22, 71), (50, 15), (78, 71)], [(50, 3), (50, 15)], [(22, 71), (50, 58), (78, 71)]],
        "facets": [[(50, 5), (78, 29), (78, 71), (50, 15)], [(78, 71), (50, 95), (50, 58)]]}
def orig(fill, accent, style=""):
    i = next(uid); cuts = "".join(f'<polyline points="{" ".join(f"{x},{y}" for x, y in c)}"/>' for c in ORIG["cuts"])
    return (f'<svg viewBox="0 0 100 100" style="{style}" aria-hidden="true"><defs><mask id="o{i}"><rect x="-10" y="-10" width="120" height="120" fill="#fff"/>'
            f'<g fill="none" stroke="#000" stroke-width="5.6" stroke-miterlimit="8">{cuts}</g></mask></defs><g mask="url(#o{i})"><path d="{P(*ORIG["body"])}" fill="{fill}"/>'
            + "".join(f'<path d="{P(*f)}" fill="{accent}"/>' for f in ORIG["facets"]) + '</g></svg>')
def crystal(key, fill, accent, style=""):
    if key == "original": return orig(fill, accent, style)
    return F.render(key, fill, accent, style)
MARKS = [("crystal", "The Crystal A", "The hexagon struck through with its own triangle; the counter is the gold."),
         ("crystal_heavy", "The Crystal A, heavy", "Wider strikes: a stamp, louder at small sizes."),
         ("crystal_closed", "The Crystal, closed", "The top corner kept whole, the legs leaving through the foot."),
         ("crystal_flat", "The Crystal, flat", "Turned to sit flat, like an ingot seen end on."),
         ("original", "The first crystal", "The faceted crystal from the opening you loved, its A and reflected bar cut through it.")]
def distress(i, amt=.86):
    return (f'<filter id="d{i}" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="{i}" result="n"/>'
            f'<feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -9 {amt * 9:.2f}" result="m"/>'
            f'<feTurbulence type="fractalNoise" baseFrequency=".02" numOctaves="2" seed="{i + 3}" result="b"/><feColorMatrix in="b" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -3 2.4" result="bm"/>'
            f'<feComposite in="m" in2="bm" operator="arithmetic" k1="0" k2="1" k3="1" k4="-.6" result="mm"/><feComposite in="SourceGraphic" in2="mm" operator="in"/></filter>')
def emblem(key, fg=RED, bg=BLACK, accent=None, ring=True, rough=True, style=""):
    """the Arasaka treatment: the crystal inside a ring, the name in tracked capitals beneath, printed a little worn"""
    i = next(uid); inner = crystal(key, fg, accent or fg)
    inner = inner.replace('<svg ', f'<svg x="25" y="22" width="50" height="50" ', 1)
    ringsvg = f'<circle cx="50" cy="47" r="36" fill="none" stroke="{fg}" stroke-width="5"/>' if ring else ""
    name = f'<text x="50" y="98" text-anchor="middle" fill="{fg}" style="font: 700 9.2px \'Commit Mono\', monospace; letter-spacing: 3.1px">ANTIMONY</text>'
    return (f'<svg viewBox="0 0 100 104" style="{style}" aria-hidden="true"><defs>{distress(i) if rough else ""}</defs>'
            f'<g{f" filter=\"url(#d{i})\"" if rough else ""}>{ringsvg}{inner}{name}</g></svg>')
def ghost(key, fg=BONE, accent=RED, style=""):
    """the Ghost in the Shell lockup: wide spaced capitals with the crystal standing between ANTI and MONY"""
    m = crystal(key, fg, accent).replace('<svg ', '<svg x="186" y="2" width="44" height="44" ', 1)
    t = lambda x, s, a: f'<text x="{x}" y="34" text-anchor="{a}" fill="{fg}" style="font: 400 26px \'Timeless Serif\', Georgia, serif; letter-spacing: 13px">{s}</text>'
    return f'<svg viewBox="0 0 416 48" style="{style}" aria-hidden="true">{t(172, "ANTI", "end")}{m}{t(248, "MONY", "start")}</svg>'
rows = ""
for key, name, text in MARKS:
    rows += f'''<section class="row">
  <div class="hero">{emblem(key, style="width:100%;height:100%")}</div>
  <div class="side">
    <h2>{name}</h2><p>{text}</p>
    <div class="trio"><span class="t red">{emblem(key, BLACK, RED, BLACK, style="width:100%;height:100%")}</span><span class="t bone">{emblem(key, BLACK, BONE, RED, style="width:100%;height:100%")}</span><span class="t blk">{crystal(key, BONE, RED, "width:100%;height:100%")}</span></div>
    <div class="lock">{ghost(key, style="width:100%;height:auto")}</div>
    <div class="sz">{"".join(f'<i style="width:{s}px;height:{s}px">{crystal(key, RED, BLACK, "width:100%;height:100%")}</i>' for s in (16, 24, 32, 48))}</div>
  </div></section>'''
html = f'''<title>Antimony Crystals</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* Every crystal finalist, in one world: black, signal red, bone, a worn print, the ring of a corporate emblem. */
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Commit Mono"; src: url(fonts/CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
:root {{ --bg: {BLACK}; --fg: {BONE}; --red: {RED}; --dim: #8E8B84; --rule: rgba(236,231,220,.13); color-scheme: dark; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: var(--bg); color: var(--fg); }}
body {{ font: 400 15px/1.55 "Commit Mono", ui-monospace, monospace; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 48px 80px; }}
.in {{ max-width: 1160px; margin-inline: auto; display: grid; gap: 0; }}
.head {{ display: grid; gap: 16px; padding-bottom: 40px; border-bottom: 1px solid var(--rule); }}
.k {{ font: 500 11.5px/1 "Commit Mono", monospace; letter-spacing: .14em; text-transform: uppercase; color: var(--red); }}
h1 {{ font: 400 clamp(40px, 6.4vw, 84px)/1 "Timeless Serif", Georgia, serif; letter-spacing: -.02em; max-width: 14em; text-wrap: balance; }}
.head p {{ max-width: 44em; color: #C9C4B9; }}
.row {{ display: grid; grid-template-columns: minmax(0, .95fr) minmax(0, 1.05fr); gap: 44px; align-items: center; padding-block: 48px; border-bottom: 1px solid var(--rule); }}
.hero {{ aspect-ratio: 100 / 104; max-width: 100%; width: min(100%, 440px); justify-self: center; }}
.hero svg, .t svg {{ display: block; }}
.side {{ display: grid; gap: 16px; min-width: 0; }}
h2 {{ font: 400 clamp(28px, 3.4vw, 40px)/1.05 "Timeless Serif", Georgia, serif; }}
.side p {{ color: #C9C4B9; max-width: 34em; }}
.trio {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
.t {{ aspect-ratio: 1; max-width: 100%; display: block; padding: 14%; }} .t.red {{ background: var(--red); }} .t.bone {{ background: var(--fg); }} .t.blk {{ background: #161617; padding: 24%; }}
.lock {{ padding: 26px 22px; background: #121213; border: 1px solid var(--rule); }} .lock svg {{ display: block; max-width: 100%; }}
.sz {{ display: flex; gap: 16px; align-items: end; padding: 14px; border: 1px solid var(--rule); }} .sz i {{ display: block; flex: none; }}
.foot {{ padding-top: 32px; display: grid; gap: 12px; }} .foot p {{ max-width: 44em; color: #C9C4B9; }}
@media (max-width: 860px) {{ .row {{ grid-template-columns: 1fr; gap: 24px; padding-block: 36px; }} }}
</style>
<div class="in">
  <div class="head"><span class="k">Antimony / crystals</span><h1>The crystals, back.</h1>
  <p>All five: the four hex finalists and the first faceted crystal from the opening. Each in the world of Arasaka and Ghost in the Shell: the crystal inside a ring with the name in tracked capitals beneath, printed in signal red on black and a little worn. Each is also shown on red and on bone, as the bare crystal, in the wide spaced ANTI / MONY lockup, and from 16 to 48 pixels.</p></div>
  {rows}
  <div class="foot"><span class="k">Your call</span><p>Pick the crystal, and whether it lives inside the ring or stands alone. Then I take that one, and only that one, all the way: standards, kit and site in this world.</p></div>
</div>
'''
open("../crystals/index.html", "w").write(html); print(len(html))
