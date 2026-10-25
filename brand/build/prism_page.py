"""Writes ../prism/index.html: the Prism family, each mark in the worlds of the references."""
import os, sys, itertools, re
sys.path.insert(0, os.path.dirname(__file__))
from prism2 import M, crystal, P, KNOCK
from crystals import distress
from kit import WM, WM_Y0, WM_Y1
uid = itertools.count()
INK, COB, NAVY, SKY, RED, BLACK, BONE, GOLDL = "#0B0D0C", "#2448FF", "#0B1230", "#9BE7FF", "#E0262D", "#0A0A0B", "#ECE7DC", "#D9B46A"
def word(fill, style=""): return f'<svg viewBox="-10 {WM_Y0} {WM["w"] + 20} {WM_Y1 - WM_Y0}" style="{style}" role="img" aria-label="Antimony"><path d="{WM["letters"]}" fill="{fill}"/><path d="{WM["dot"]}" fill="{fill}"/></svg>'
def glow(fn):
    """Final Fantasy: the crystal lit from inside, on midnight, its light spilling into the air"""
    i = next(uid); m = fn(SKY, "#FFFFFF")
    inner = m[m.index(">") + 1:m.rindex("</svg>")]
    return (f'<svg viewBox="-20 -20 140 140" aria-hidden="true"><defs><filter id="gl{i}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6" result="b"/>'
            f'<feColorMatrix in="b" type="matrix" values="0 0 0 0 .45  0 0 0 0 .85  0 0 0 0 1  0 0 0 1.4 0" result="c"/><feMerge><feMergeNode in="c"/><feMergeNode in="c"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
            f'<radialGradient id="rg{i}" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#3A6BD8" stop-opacity=".55"/><stop offset="1" stop-color="{NAVY}" stop-opacity="0"/></radialGradient></defs>'
            f'<rect x="-20" y="-20" width="140" height="140" fill="{NAVY}"/><circle cx="50" cy="50" r="62" fill="url(#rg{i})"/>'
            f'<path d="M50 -20V120" stroke="#9BE7FF" stroke-width=".25" opacity=".45"/><g filter="url(#gl{i})">{inner}</g></svg>')
def seal(fn):
    """Arasaka: the mark in a ring, one ink, printed worn"""
    i = next(uid); m = fn(RED, RED); inner = m[m.index(">") + 1:m.rindex("</svg>")].replace(KNOCK, BLACK)
    return (f'<svg viewBox="0 0 100 108" aria-hidden="true"><defs>{distress(900 + i)}</defs><rect width="100" height="108" fill="{BLACK}"/><g filter="url(#d{900 + i})">'
            f'<circle cx="50" cy="46" r="36" fill="none" stroke="{RED}" stroke-width="4.6"/><g transform="translate(29 25) scale(.42)">{inner}</g>'
            f'<text x="50" y="100" text-anchor="middle" fill="{RED}" style="font: 700 8.6px \'Commit Mono\', monospace; letter-spacing: 3px">ANTIMONY</text></g></svg>')
def fine(fn):
    """Porter Robinson: the facets drawn as fine gold line on midnight, a sparkle where the light catches"""
    m = fn(INK, INK); paths = re.findall(r'<path d="([^"]+)" fill="[^"]+"/>', m)
    lines = "".join(f'<path d="{d}" fill="none" stroke="{GOLDL}" stroke-width=".55" stroke-linejoin="round"/>' for d in paths)
    return (f'<svg viewBox="-20 -20 140 140" aria-hidden="true"><rect x="-20" y="-20" width="140" height="140" fill="{NAVY}"/>'
            f'<path d="M-20 106H120M-6 -20V120" stroke="{GOLDL}" stroke-width=".2" opacity=".6"/>{lines}'
            f'<path d="M57 6l1.2 4 4 1.2-4 1.2-1.2 4-1.2-4-4-1.2 4-1.2z" fill="#fff"/><circle cx="-6" cy="30" r="1" fill="#fff"/>'
            f'<text x="50" y="117" text-anchor="middle" fill="#E9DFC8" style="font: 400 5.4px \'Timeless Serif\', serif; letter-spacing: 2.6px">a n t i m o n y</text></svg>')
ORDER = ["spray", "spray_ring", "prism_tip", "prism_face", "prism_lean", "pair"]
secs = ""
for k in ORDER:
    name, text, fn = M[k]
    secs += f'''<section class="mk"><div class="big">{fn(style="width:100%;height:100%")}</div>
  <div class="side"><h2>{name}</h2><p>{text}</p>
  <div class="worlds"><figure><div class="w">{glow(fn)}</div><figcaption>Lit from inside</figcaption></figure><figure><div class="w">{seal(fn)}</div><figcaption>The seal</figcaption></figure><figure><div class="w">{fine(fn)}</div><figcaption>Fine line, midnight</figcaption></figure></div>
  <div class="foot"><span class="sz">{"".join(f'<i style="width:{s}px;height:{s}px">{fn(style="width:100%;height:100%")}</i>' for s in (16, 24, 32, 48))}</span>
  <span class="lock">{fn(style="width:40px;height:40px;flex:none")}{word(INK, "height:28px;width:auto")}</span></div></div></section>'''
html = f'''<title>Antimony, The Prism</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* One new family, the crystal whose tip is an A, each mark large and then in three worlds: lit like a Final Fantasy crystal, sealed like Arasaka, drawn in fine line like Porter Robinson. */
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-400.woff2) format("woff2"); font-weight: 400; font-display: swap; }}
@font-face {{ font-family: "Commit Mono"; src: url(fonts/CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
:root {{ --paper: #F4F3EE; --ink: {INK}; --dim: #5C6461; --rule: rgba(11,13,12,.13); color-scheme: light; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: var(--paper); color: var(--ink); }}
body {{ font: 400 15.5px/1.55 "Timeless Sans", "Helvetica Neue", Arial, sans-serif; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 52px 80px; }}
.in {{ max-width: 1160px; margin-inline: auto; display: grid; }}
.k {{ font: 500 11.5px/1 "Commit Mono", monospace; letter-spacing: .1em; text-transform: uppercase; color: var(--dim); }}
h1 {{ font: 400 clamp(40px, 6.4vw, 84px)/1 "Timeless Serif", Georgia, serif; letter-spacing: -.02em; max-width: 14em; text-wrap: balance; }}
.head {{ display: grid; gap: 16px; padding-bottom: 36px; border-bottom: 1px solid var(--rule); }}
.lede {{ font: 400 clamp(18px, 1.9vw, 22px)/1.5 "Timeless Serif", Georgia, serif; max-width: 36em; }}
.mk {{ display: grid; grid-template-columns: minmax(0, .8fr) minmax(0, 1.2fr); gap: 40px; align-items: center; padding-block: 44px; border-bottom: 1px solid var(--rule); }}
.big {{ aspect-ratio: 1; max-width: 100%; padding: 12%; background: #FBFAF6; border: 1px solid var(--rule); }}
.big svg, .w svg {{ display: block; width: 100%; height: 100%; }}
.side {{ display: grid; gap: 14px; min-width: 0; }}
h2 {{ font: 400 clamp(28px, 3.2vw, 38px)/1.05 "Timeless Serif", Georgia, serif; }}
.side p {{ color: var(--dim); max-width: 34em; }}
.worlds {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
figure {{ display: grid; gap: 6px; min-width: 0; }} figcaption {{ font-size: 13px; color: var(--dim); }}
.w {{ aspect-ratio: 1; max-width: 100%; overflow: hidden; }}
.foot {{ display: flex; gap: 12px; flex-wrap: wrap; }}
.sz {{ display: flex; gap: 14px; align-items: end; padding: 12px 14px; border: 1px solid var(--rule); }} .sz i {{ display: block; flex: none; }}
.lock {{ display: flex; gap: 12px; align-items: center; padding: 12px 16px; border: 1px solid var(--rule); background: #FBFAF6; flex: 1; min-width: 0; }} .lock svg {{ display: block; max-width: 100%; }}
.end {{ padding-top: 30px; display: grid; gap: 12px; }} .end p {{ max-width: 44em; }}
@media (max-width: 860px) {{ .mk {{ grid-template-columns: 1fr; gap: 22px; }} }}
</style>
<div class="in">
  <div class="head"><span class="k">Antimony, the mark, the prism</span><h1>The crystal whose tip is an A.</h1>
  <p class="lede">Stibnite, antimony's ore, grows as long prisms with pointed tips: the very shape of a Final Fantasy crystal. Seen front on, the tip of a prism is an A. So the mark is a real crystal, cut like a gem: three faces in proportions of one, two and one, hairline gaps where the facets meet, the light catching one facet. Each is shown large, then lit from inside, sealed, and in fine line, then small and with the name.</p></div>
  {secs}
  <div class="end"><span class="k">My read</span><p>The Spray is the strongest new mark I have made for you: three cut crystals from one seed, the middle one lit, readable at 16 pixels, an emblem in a ring and a jewel when lit. The Prism, lit tip, is its simplest member, for app icons and favicons. They are one family: the single crystal and the spray it grows into.</p></div>
</div>
'''
open("../prism/index.html", "w").write(html); print(len(html))
