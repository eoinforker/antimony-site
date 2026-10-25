"""Writes ../balance/index.html: one exact mark, eight lovable worlds, laid out as covers."""
import os, sys, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from mark import PC, poly, mark_paths, WM, DOT
NAVY, GOLD, WASHI, INK = "#0E1733", "#D9B46A", "#F3ECDD", "#1A1D1C"
def exact(fill=INK, gold="#2448FF", style=""): return f'<svg viewBox="-1.5 -1.5 103 103" style="{style}" aria-hidden="true">{mark_paths(fill, gold)}</svg>'
def word(fill, dot, style=""):
    return f'<svg viewBox="-10 {WM["asc"] - WM["cap"] - 40} {WM["w"] + 20} {WM["cap"] + 300}" style="{style}" role="img" aria-label="Antimony"><path d="{WM["letters"]}" fill="{fill}"/><path d="{DOT}" fill="{dot}"/></svg>'
win = "".join(f'<path d="{poly(PC[k])}"/>' for k in ("wing_l", "wing_r", "foot"))
def window(img, gold="#F4C84A", line=GOLD):
    return (f'<svg viewBox="-1.5 -1.5 103 103" aria-hidden="true"><defs><clipPath id="cw{abs(hash(img)) % 999}">{win}</clipPath></defs>'
            f'<image href="{img}" x="-1.5" y="-1.5" width="103" height="103" preserveAspectRatio="xMidYMid slice" clip-path="url(#cw{abs(hash(img)) % 999})"/>'
            + "".join(f'<path d="{poly(PC[k])}" fill="none" stroke="{line}" stroke-width=".35"/>' for k in ("wing_l", "wing_r", "foot")) + f'<path d="{poly(PC["counter"])}" fill="{gold}"/></svg>')
FINE = f'''<div class="cv fine"><svg class="rules" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
  <path d="M14 0V100M0 86H100" stroke="{GOLD}" stroke-width=".12" fill="none" opacity=".7"/><path d="M14 4V14M14 33V36" stroke="{GOLD}" stroke-width=".25"/>
  <path d="M86 80V92M80 86H92" stroke="{GOLD}" stroke-width=".12" opacity=".8"/><circle cx="86" cy="86" r="4.5" fill="none" stroke="{GOLD}" stroke-width=".12"/></svg>
  <span class="spark" style="left:14%;top:24%"></span><span class="spark" style="left:14%;top:2%;transform:scale(.6)"></span>
  <div class="frame">{window("img/24800.webp")}</div>
  <span class="vert">for the people who make the work</span>
  <span class="name">a n t i m o n y</span><span class="seal">{exact(GOLD, "#F4C84A", "width:100%;height:100%")}</span></div>'''
COVERS = [
 ("img/stibnite.webp", "The ore", "Antimony's own crystal, stibnite, printed in one blue with heavy grain. The object you want to hold.", "Bob Dylan's Greatest Hits, Ricochet", '<span class="over" style="color:#E9E4D6">{w}</span>'),
 ("img/worn.webp", "Struck", "The mark in dull metal on worn paper, the gold left warm in the middle.", "Starset", ""),
 ("img/thermal.webp", "Warm", "The mark seen by a heat camera: the gold burns brightest.", "Basement, WIRED", ""),
 ("img/paint.webp", "Painted", "Painted in gouache on a painted block, the shapes exact, the paint not.", "Pinegrove", ""),
 (None, "Midnight", "Fine gold lines on midnight, a print in the window, the name set wide and lower case.", "Everything Goes On, Arcane", FINE),
 ("img/paint-washi.webp", "Washi", "The same painting on paper, Prussian and sun.", "Nurture", ""),
]
cards = ""
for img, name, text, learns, extra in COVERS:
    if img:
        over = extra.format(w=word("#E9E4D6", "#E9E4D6", "width:100%;height:auto")) if extra else ""
        body = f'<div class="cv" style="background-image:url({img})">{over}</div>'
    else: body = extra
    cards += f'<figure>{body}<figcaption><b>{name}</b>{text}<i>Learns from {learns}</i></figcaption></figure>'
html = f'''<title>Antimony, The Balance</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* Covers, because the references are covers: one exact mark, each time placed in a world you would want to live in. */
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifItalicVF.woff2) format("woff2"); font-weight: 200 700; font-style: italic; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-400.woff2) format("woff2"); font-weight: 400; font-display: swap; }}
@font-face {{ font-family: "Commit Mono"; src: url(fonts/CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
:root {{ --bg: #15130F; --fg: #EDE6D6; --dim: #A29A89; --rule: rgba(237,230,214,.14); color-scheme: dark; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: var(--bg); color: var(--fg); }}
body {{ font: 400 15.5px/1.55 "Timeless Sans", "Helvetica Neue", Arial, sans-serif; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 56px 80px; }}
.in {{ max-width: 1160px; margin-inline: auto; display: grid; gap: 44px; }}
.eyebrow {{ font: 500 11.5px/1 "Commit Mono", monospace; letter-spacing: .08em; text-transform: uppercase; color: var(--dim); }}
h1 {{ font: 400 clamp(40px, 6.4vw, 84px)/1 "Timeless Serif", Georgia, serif; letter-spacing: -.02em; max-width: 14em; text-wrap: balance; }}
h2 {{ font: 400 clamp(28px, 3.4vw, 40px)/1.08 "Timeless Serif", Georgia, serif; letter-spacing: -.012em; max-width: 20em; text-wrap: balance; }}
.lede {{ font: 400 clamp(18px, 1.9vw, 22px)/1.5 "Timeless Serif", Georgia, serif; max-width: 34em; color: #D8D0BE; }}
.rule {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 0; border: 1px solid var(--rule); }}
.rule div {{ padding: 22px; display: grid; gap: 10px; align-content: start; }} .rule div + div {{ border-left: 1px solid var(--rule); }}
.rule b {{ font: 400 24px "Timeless Serif", Georgia, serif; }}
.rule ul {{ padding-left: 1.1em; color: #CFC7B5; display: grid; gap: 4px; }}
.exact {{ display: grid; place-items: center; background: #F3ECDD; aspect-ratio: 1; max-width: 100%; padding: 26%; }}
.grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 34px 20px; }}
figure {{ display: grid; gap: 12px; align-content: start; min-width: 0; }}
figcaption {{ font-size: 14.5px; color: var(--dim); display: grid; gap: 3px; }}
figcaption b {{ font: 400 22px/1.15 "Timeless Serif", Georgia, serif; color: var(--fg); }}
figcaption i {{ font: 500 11px "Commit Mono", monospace; letter-spacing: .06em; text-transform: uppercase; font-style: normal; color: #7E7768; margin-top: 4px; }}
.cv {{ aspect-ratio: 1; max-width: 100%; background-size: cover; background-position: center; border-radius: 6px; position: relative; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,.35); }}
.over {{ position: absolute; left: 34%; right: 34%; top: 9%; display: block; }}
.fine {{ background: radial-gradient(90% 80% at 30% 30%, #1A2550 0%, {NAVY} 70%); }}
.fine .rules {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
.fine .frame {{ position: absolute; left: 34%; top: 12%; width: 50%; aspect-ratio: 1; }}
.fine .frame svg {{ width: 100%; height: 100%; display: block; }}
.fine .vert {{ position: absolute; right: 4%; top: 12%; writing-mode: vertical-rl; font: 400 clamp(8px, 1vw, 11px) "Timeless Serif", Georgia, serif; letter-spacing: .32em; color: {GOLD}; opacity: .85; }}
.fine .name {{ position: absolute; left: 34%; bottom: 10.5%; font: 400 clamp(11px, 1.5vw, 17px) "Timeless Serif", Georgia, serif; color: #E8DFC9; letter-spacing: .12em; }}
.fine .seal {{ position: absolute; left: calc(86% - 2.4%); top: calc(86% - 2.4%); width: 4.8%; aspect-ratio: 1; display: block; }}
.spark {{ position: absolute; width: 18px; height: 18px; margin: -9px; background: radial-gradient(circle, #fff 0 8%, transparent 9%), linear-gradient(90deg, transparent 47%, #fff 50%, transparent 53%), linear-gradient(0deg, transparent 47%, #fff 50%, transparent 53%);
  -webkit-mask: radial-gradient(circle, #000 20%, transparent 70%); mask: radial-gradient(circle, #000 20%, transparent 70%); }}
.next {{ border-top: 1px solid var(--rule); padding-top: 28px; display: grid; gap: 12px; }} .next p {{ max-width: 42em; color: #CFC7B5; }}
@media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr 1fr; }} .rule {{ grid-template-columns: 1fr; }} .rule div + div {{ border-left: 0; border-top: 1px solid var(--rule); }} }}
@media (max-width: 520px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
<div class="in">
  <span class="eyebrow">Antimony, the balance</span>
  <h1>An exact mark, in a world you would want to live in.</h1>
  <p class="lede">Every reference you sent does the same two things. The sign is exact: Arasaka's tree, the triangle in Ghost in the Shell, Berserk's brand, Starset's A. And it is never seen alone, flat, on white. It is struck into metal, burned into skin, printed with grain, painted on a block, lit like a heat camera. That is where the love lives.</p>
  <div class="rule">
    <div><b>Exact</b><ul><li>One sign, drawn once, never changed.</li><li>Few parts, symmetrical, readable at 16 px.</li><li>Its meaning is true.</li></ul></div>
    <div><b>Lovable</b><ul><li>Always shown in a world: an object, a material, a light.</li><li>Grain, paint, metal, warmth. Never flat, never on white alone.</li><li>A different world for each moment, like a run of records.</li></ul></div>
  </div>
  <h2>Six covers. The mark does not change once.</h2>
  <div class="grid">{cards}</div>
  <div class="next"><span class="eyebrow">What this means</span>
    <p>We stop asking the mark to be lovable by itself. No mark is: Arasaka's tree on white is a clip art tree. The mark is the exact part and stays exact; the system is a set of worlds it lives in, each with its own material, and every launch, letter and product gets a new one, the way a band gets a new cover.</p>
    <p>The mark here is the Crystal A, because your hex picks pointed there. If the exact part is still wrong, these worlds work for any sign: tell me and I will drop another into the same six.</p></div>
</div>
'''
open("../balance/index.html", "w").write(html); print(len(html))
