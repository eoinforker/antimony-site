"""Writes ../alive/index.html: the same marks, made by hand. Cut from paper with a torn edge, and boiling: redrawn eight
times a second with a slightly different edge, the way hand drawn animation lives."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from mark import PC, poly, mark_paths
INK, PAPER = "#0B0D0C", "#F4F3EE"
AND1, AND2 = "M90 96 L38 44 L52 30 L38 16 L24 30 L36 42", "M36 42 L18 60 L18 78 L34 94 L56 94 L86 64"
def torn(id_, scale=2.2, freq=.055, seed=3):
    # a torn paper edge: turbulence pushes the outline about; three seeds cycle to make the edge boil
    return (f'<filter id="{id_}" x="-10%" y="-10%" width="120%" height="120%">'
            f'<feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="3" seed="{seed}" result="n"><animate attributeName="seed" values="{seed};{seed + 7};{seed + 13};{seed + 21}" dur=".5s" calcMode="discrete" repeatCount="indefinite"/></feTurbulence>'
            f'<feDisplacementMap in="SourceGraphic" in2="n" scale="{scale}" xChannelSelector="R" yChannelSelector="G"/></filter>')
def fibre(id_):
    # the paper's own fibre, laid over the cut piece
    return (f'<filter id="{id_}"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="5" result="g"/>'
            f'<feColorMatrix in="g" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 .22 0" result="ga"/><feComposite in="ga" in2="SourceGraphic" operator="in" result="gr"/>'
            f'<feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="gr"/></feMerge></filter>')
def crystal(fill, gold, k):
    return (f'<svg viewBox="-6 -6 112 112" aria-hidden="true"><defs>{torn("t" + k, 3.2, .045)}{fibre("f" + k)}</defs>'
            f'<g filter="url(#t{k})"><g filter="url(#f{k})">{mark_paths(fill, gold, 0)}</g></g></svg>')
def and_mark(fill, gold, k):
    return (f'<svg viewBox="2 0 96 104" aria-hidden="true"><defs>{torn("t" + k, 3.4, .05, 9)}{fibre("f" + k)}<clipPath id="c{k}"><rect width="100" height="94"/></clipPath></defs>'
            f'<g filter="url(#t{k})"><g filter="url(#f{k})"><g clip-path="url(#c{k})" fill="none" stroke="{fill}" stroke-width="10.5" stroke-linejoin="miter"><path d="{AND1}"/><path d="{AND2}"/></g>'
            f'<path d="M38 23L45 30L38 37L31 30Z" fill="{gold}"/></g></g></svg>')
def still_crystal(fill, gold): return f'<svg viewBox="-6 -6 112 112" aria-hidden="true">{mark_paths(fill, gold, .8)}</svg>'
GROUNDS = [("#F2C230", "#1C2A5E", "#E4483B", "Late afternoon"), ("#F6C9D6", "#1E2B5C", "#FFFFFF", "Dusk"), ("#CFEDE2", "#123B33", "#F2C230", "First light"), (PAPER, INK, "#2448FF", "Paper")]
cards = ""
for i, (g, fg, gold, name) in enumerate(GROUNDS):
    cards += (f'<figure><div class="tile" style="background:{g}">{crystal(fg, gold, f"c{i}")}</div><div class="tile" style="background:{g}">{and_mark(fg, gold, f"a{i}")}</div>'
              f'<figcaption>{name}</figcaption></figure>')
html = f'''<title>Antimony, Alive</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* A test, not a design: does the hand make it feel alive? Same marks, cut from paper with a torn edge, boiling like hand drawn animation, on warm grounds. */
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-400.woff2) format("woff2"); font-weight: 400; font-display: swap; }}
:root {{ --ink: #1C2A5E; --ground: #F2C230; --rule: rgba(28,42,94,.18); color-scheme: light; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: var(--ground); color: var(--ink); }}
body {{ font: 400 16px/1.55 "Timeless Sans", "Helvetica Neue", Arial, sans-serif; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 48px 72px; }}
.in {{ max-width: 1160px; margin-inline: auto; display: grid; gap: 34px; }}
h1 {{ font: 400 clamp(44px, 7vw, 92px)/.98 "Timeless Serif", Georgia, serif; letter-spacing: -.02em; text-transform: lowercase; }}
p {{ max-width: 36em; font: 400 clamp(17px, 1.8vw, 20px)/1.5 "Timeless Serif", Georgia, serif; }}
.vs {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; max-width: 720px; }}
.vs figure, .grid figure {{ display: grid; gap: 10px; margin: 0; }}
.tile {{ aspect-ratio: 1; max-width: 100%; display: grid; place-items: center; padding: 18%; border-radius: 2px; }}
.tile svg {{ width: 100%; height: 100%; display: block; overflow: visible; }}
figcaption {{ font: 400 14px "Timeless Sans", Arial, sans-serif; opacity: .8; }}
.grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }}
.grid figure {{ gap: 8px; }}
@media (max-width: 760px) {{ .grid {{ grid-template-columns: 1fr 1fr; }} }}
@media (prefers-reduced-motion: reduce) {{ animate {{ display: none; }} }}
</style>
<div class="in">
  <h1>hello &amp; welcome.</h1>
  <p>A test of one idea before I redraw anything: that what is missing is the hand. The same marks as before, cut from paper with a torn edge and redrawn eight times a second, the way hand drawn animation boils, on the warm grounds of late afternoon, dusk and first light.</p>
  <div class="vs">
    <figure><div class="tile" style="background:#FBF7EA">{still_crystal("#1C2A5E", "#E4483B")}</div><figcaption>Ruled: what I made.</figcaption></figure>
    <figure><div class="tile" style="background:#FBF7EA">{crystal("#1C2A5E", "#E4483B", "x")}</div><figcaption>By hand: the same drawing, alive.</figcaption></figure>
  </div>
  <div class="grid">{cards}</div>
  <p>If this is closer to the feeling, the next round is drawn by hand from the start rather than filtered, the palette opens to warm light, and the type and words loosen with it.</p>
</div>
'''
open("../alive/index.html", "w").write(html); print(len(html))
