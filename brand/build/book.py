"""Writes ../index.html, the brand book. Images point at ../exports."""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from kit import *
A = G["atoms"]; R = G["R"]; W = G["W"]; D = G["D"]
P = json.load(open("pixels.json"))

def construction():
    """the emblem on its lattice, with the three numbers that make it"""
    grid = ""
    for v in (50 - D, 50, 50 + D): grid += f'<line x1="{v}" y1="-4" x2="{v}" y2="104" class="g"/>'
    for v in (A["apex"][1], A["nucleus"][1], A["leg_l"][1]): grid += f'<line x1="-4" y1="{v}" x2="104" y2="{v}" class="g"/>'
    ax, ay = A["right"]
    dims = (f'<line x1="50" y1="-1" x2="{50+D}" y2="-1" class="d"/><text x="{50+D/2}" y="-3">D</text>'
            f'<line x1="{ax}" y1="{ay}" x2="{ax+R}" y2="{ay}" class="d k"/><text x="{ax+R+1.5}" y="{ay+1.1}" class="k" text-anchor="start">R</text>'
            f'<line x1="{50+D/2}" y1="{ay-W/2}" x2="{50+D/2}" y2="{ay+W/2}" class="d k"/><text x="{50+D/2}" y="{ay+W/2+4.6}" class="k">W</text>')
    return (f'<svg viewBox="-8 -10 120 114" class="cons" role="img" aria-label="Construction of the Bond">'
            f'<g opacity=".16">{bond_paths("var(--ink)", "var(--ink)")}</g>{grid}'
            f'<g fill="none" stroke="var(--cobalt)" stroke-width=".35">' + "".join(f'<path d="M{x} {y-R}L{x+R} {y}L{x} {y+R}L{x-R} {y}Z"/>' for x, y in A.values()) + f'</g>{dims}</svg>')

def pixel_svg(rows):
    n = len(rows); cells = ""
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch != ".": cells += f'<rect x="{i}" y="{j}" width="1" height="1" fill="{"var(--ink)" if ch == "1" else "var(--cobalt)"}"/>'
    lines = "".join(f'<line x1="{k}" y1="0" x2="{k}" y2="{n}"/><line x1="0" y1="{k}" x2="{n}" y2="{k}"/>' for k in range(n + 1))
    return f'<svg viewBox="0 0 {n} {n}" class="px" aria-hidden="true">{cells}<g stroke="var(--rule)" stroke-width="{0.6/n*16/16*1.2:.3f}">{lines}</g></svg>'

def swatch(name, hexv, role, fg):
    return f'<div class="sw" style="background:{hexv};color:{fg}"><b>{name}</b><span>{hexv}</span><span>{role}</span></div>'

FILES = [("svg/", "Masters: the Bond, the Seal, the wordmark and both lockups, each in colour, reversed and one colour"),
         ("logo/", "The same as PNG at 1024 to 2400 px, on paper, ink and cobalt"),
         ("social/", "Avatars, LinkedIn company cover and personal banner, X header, Open Graph card, a square post"),
         ("motion/", "The sting as MP4, square and 16 by 9, 6 seconds"),
         ("icons/", "favicon.svg, favicon.ico with hand drawn 16 and 32 px, and app icons at 180, 192 and 512"),
         ("print/", "Business card, front and back, PDF at 85 by 55 mm with 3 mm bleed"),
         ("deck/", "Title slide, 1920 by 1080")]

html = f'''<title>Antimony Identity</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* A brand book in two grounds: paper for the rules, ink for the work in use. One column of evidence, the emblem first. */
@font-face {{ font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-400.woff2) format("woff2"); font-weight: 400; font-display: swap; }}
@font-face {{ font-family: "Timeless Sans"; src: url(fonts/timeless-sans-500.woff2) format("woff2"); font-weight: 500; font-display: swap; }}
@font-face {{ font-family: "Commit Mono"; src: url(fonts/CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }}
:root {{ --ink: {INK}; --paper: {PAPER}; --cobalt: {COBALT}; --sky: {SKY}; --rule: rgba(11,13,12,.13); --dim: #5C6461; --dim-d: #8A9592; --rule-d: rgba(244,243,238,.14);
  --serif: "Timeless Serif", "Iowan Old Style", Georgia, serif; --sans: "Timeless Sans", "Helvetica Neue", Arial, sans-serif; --mono: "Commit Mono", ui-monospace, Menlo, monospace; color-scheme: light; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: var(--paper); color: var(--ink); }}
body {{ font: 400 16px/1.55 var(--sans); -webkit-font-smoothing: antialiased; }}
.band {{ padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 72px; }}
.band.ink {{ background: var(--ink); color: var(--paper); --rule: var(--rule-d); --dim: var(--dim-d); }}
.in {{ max-width: 1120px; margin-inline: auto; display: grid; gap: 28px; }}
.eyebrow {{ font: 500 11.5px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--dim); }}
h1 {{ font: 400 clamp(44px, 7vw, 92px)/.98 var(--serif); letter-spacing: -.02em; text-wrap: balance; }}
h2 {{ font: 400 clamp(30px, 4vw, 46px)/1.04 var(--serif); letter-spacing: -.012em; text-wrap: balance; max-width: 18em; }}
h3 {{ font: 500 15px/1.3 var(--sans); }}
p {{ max-width: 38em; }}
.lede {{ font: 400 clamp(19px, 2vw, 23px)/1.45 var(--serif); max-width: 32em; }}
.dim {{ color: var(--dim); }}
.two {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 40px; align-items: start; }}
.three {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
.hero {{ display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 48px; align-items: center; }}
.hero .em {{ width: min(100%, 440px); justify-self: center; }}
.tile {{ border: 1px solid var(--rule); display: grid; place-items: center; aspect-ratio: 1; max-width: 100%; }}
.tile.ink {{ background: var(--ink); border-color: var(--ink); }} .tile.cob {{ background: var(--cobalt); border-color: var(--cobalt); }}
.tile svg {{ width: 56%; height: auto; }}
.tile.wide {{ aspect-ratio: 2.2; }} .tile.wide svg {{ width: 70%; }}
.cap {{ display: grid; gap: 8px; }}
.cap figcaption {{ font-size: 14px; color: var(--dim); }}
.cons {{ width: 100%; height: auto; font: 500 3.2px var(--mono); }}
.cons .g {{ stroke: var(--rule); stroke-width: .3; stroke-dasharray: 1 1; }}
.cons .d {{ stroke: var(--ink); stroke-width: .35; }} .cons .d.k {{ stroke: var(--cobalt); }}
.cons text {{ fill: var(--ink); text-anchor: middle; }} .cons text.k {{ fill: var(--cobalt); }}
.nums {{ display: grid; gap: 14px; }}
.nums div {{ display: grid; grid-template-columns: 4.6em 1fr; gap: 12px; border-top: 1px solid var(--rule); padding-top: 12px; }}
.nums b {{ font: 500 15px var(--mono); color: var(--cobalt); }}
.sizes {{ display: flex; flex-wrap: wrap; align-items: end; gap: 28px; }}
.sizes span {{ display: grid; gap: 8px; justify-items: center; font: 400 11px var(--mono); color: var(--dim); }}
.px {{ width: 100%; max-width: 260px; height: auto; image-rendering: pixelated; border: 1px solid var(--rule); }}
.real img {{ image-rendering: pixelated; display: block; }}
.sw {{ min-height: 168px; padding: 16px; display: grid; align-content: end; gap: 3px; border: 1px solid var(--rule); }}
.sw b {{ font: 400 26px/1.1 var(--serif); }} .sw span {{ font: 400 12px var(--mono); opacity: .8; }}
.type {{ display: grid; gap: 22px; }}
.type div {{ border-top: 1px solid var(--rule); padding-top: 16px; display: grid; grid-template-columns: 12em minmax(0, 1fr); gap: 20px; align-items: baseline; }}
.t1 {{ font: 400 clamp(30px, 4vw, 52px)/1.05 var(--serif); letter-spacing: -.012em; }}
.t2 {{ font: 400 18px/1.5 var(--sans); }} .t3 {{ font: 400 14px/1.5 var(--mono); }}
video, .shot {{ width: 100%; height: auto; display: block; max-width: 100%; }}
.shot {{ border: 1px solid var(--rule); }}
.profile {{ border: 1px solid var(--rule); background: #121615; overflow: hidden; border-radius: 10px; }}
.profile .ban {{ width: 100%; display: block; aspect-ratio: 1128 / 191; object-fit: cover; }}
.profile .body {{ padding: 0 22px 22px; display: grid; gap: 4px; position: relative; }}
.profile .av {{ width: 104px; height: 104px; margin-top: -52px; border-radius: 8px; border: 4px solid #121615; display: block; }}
.profile b {{ font: 500 22px var(--sans); color: var(--paper); margin-top: 8px; }} .profile span {{ color: var(--dim); font-size: 15px; }}
.dont {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }}
.dont figure {{ display: grid; gap: 8px; }} .dont .tile svg {{ width: 50%; }}
.files {{ display: grid; gap: 0; }}
.files div {{ display: grid; grid-template-columns: 8em minmax(0, 1fr); gap: 16px; border-top: 1px solid var(--rule); padding: 12px 0; }}
.files code {{ font: 500 14px var(--mono); }}
.check li {{ margin-bottom: 8px; }} .check {{ padding-left: 1.1em; max-width: 40em; }}
@media (max-width: 820px) {{ .two, .hero {{ grid-template-columns: 1fr; }} .three {{ grid-template-columns: 1fr 1fr; }} .dont {{ grid-template-columns: 1fr 1fr; }} .type div {{ grid-template-columns: 1fr; gap: 6px; }} .band {{ padding-block: 52px; }} }}
@media (prefers-reduced-motion: reduce) {{ video {{ display: none; }} }}
</style>

<section class="band ink"><div class="in hero">
  <div style="display:grid;gap:22px">
    <span class="eyebrow">Antimony identity, version one</span>
    <h1>The Bond.</h1>
    <p class="lede">Antimony holds five electrons in its outer shell. Drawn as a molecule, five atoms are bound to one nucleus. Read one way it is an A. Read another, it is a person standing, arms open: the people who make the work. No atom in it stands alone.</p>
  </div>
  <div class="em">{bond_svg(PAPER, SKY)}</div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">Construction</span>
  <h2>Three numbers make it, on a lattice of squares turned 45 degrees.</h2>
  <div class="two">
    {construction()}
    <div class="nums">
      <div><b>D {D:g}</b><span>The lattice step between atom centres, on a 100 unit square. Every atom sits on it.</span></div>
      <div><b>R {R:g}</b><span>Each atom, centre to tip. At this size neighbouring tips almost touch, so the bonds read as short and strong rather than as limbs.</span></div>
      <div><b>W {W:g}</b><span>The bond, a third of an atom across. Heavy enough to stand beside thick, solid marks; light enough that the diamonds stay the subject.</span></div>
      <div><b>0</b><span>Free angles. Every edge runs at 45 or 90 degrees, so the emblem can be rebuilt from this page with a ruler.</span></div>
    </div>
  </div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">Forms</span>
  <h2>One emblem, one seal, one wordmark, two lockups.</h2>
  <div class="three">
    <figure class="cap"><div class="tile">{bond_svg(INK, COBALT)}</div><figcaption>The Bond. The default, anywhere the name is already present.</figcaption></figure>
    <figure class="cap"><div class="tile ink">{seal_svg(PAPER, SKY).replace("<svg", '<svg style="width:70%"')}</div><figcaption>The Seal. For avatars, stamps and anywhere the emblem stands alone on a busy ground.</figcaption></figure>
    <figure class="cap"><div class="tile cob">{bond_svg(PAPER, SKY)}</div><figcaption>On cobalt the nucleus turns sky. It is always the only colour in the emblem.</figcaption></figure>
  </div>
  <div class="two">
    <figure class="cap"><div class="tile wide">{lockup_svg(INK, COBALT)}</div><figcaption>The lockup. The emblem is one and a half cap heights tall, centred on the cap height, one atom from the name.</figcaption></figure>
    <figure class="cap"><div class="tile wide">{lockup_svg(INK, COBALT, stacked=True).replace("<svg", '<svg style="width:46%"')}</div><figcaption>Stacked, for square and tall spaces.</figcaption></figure>
  </div>
  <figure class="cap"><div class="tile wide" style="aspect-ratio:3.2">{wordmark_svg(INK, COBALT, style="width:66%")}</div><figcaption>The wordmark: Timeless Serif at 420, kerned as the font intends and tracked in, with the dot of the i replaced by an atom.</figcaption></figure>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">Small sizes</span>
  <h2>Drawn by hand at 16 and 32 pixels, not shrunk.</h2>
  <p class="dim">Each atom is placed on a pixel centre so it lands as a clean stepped diamond. These are the files in the favicon.</p>
  <div class="two"><div class="sizes">
    <span>{pixel_svg(P["16"])}16 px, drawn</span><span>{pixel_svg(P["32"])}32 px, drawn</span>
  </div>
  <div class="sizes real">
    <span><img src="exports/icons/favicon-16.png" width="16" height="16" alt="">16</span>
    <span><img src="exports/icons/favicon-32.png" width="32" height="32" alt="">32</span>
    <span style="width:48px">{bond_svg(INK, COBALT)}48</span>
    <span style="width:96px">{bond_svg(INK, COBALT)}96</span>
  </div></div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">Colour</span>
  <h2>Ink and paper carry everything. Colour is kept for the nucleus.</h2>
  <div class="three" style="grid-template-columns:repeat(4,minmax(0,1fr))">
    {swatch("Ink", INK, "Grounds, text, atoms", PAPER)}{swatch("Paper", PAPER, "Grounds, text, atoms", INK)}{swatch("Cobalt", COBALT, "The nucleus on paper; links", PAPER)}{swatch("Sky", SKY, "The nucleus on ink and cobalt", INK)}
  </div>
  <p class="dim">Cobalt on paper, sky on ink. Never a second accent, never a gradient on the emblem, never purple, teal or amber.</p>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">Type</span>
  <h2>Three faces, each with one job.</h2>
  <div class="type">
    <div><span class="eyebrow">Timeless Serif</span><span class="t1">Software for the people who make the work.</span></div>
    <div><span class="eyebrow">Timeless Sans</span><span class="t2">Body text, interfaces and anything read at length. Set at 16 to 19 px with generous leading.</span></div>
    <div><span class="eyebrow">Commit Mono</span><span class="t3">LABELS, FIGURES AND CODE. 51 SB 121.760</span></div>
  </div>
</div></section>

<section class="band ink"><div class="in">
  <span class="eyebrow">Motion</span>
  <h2>The nucleus first, then the bonds, then the atoms. Then you see it was never alone.</h2>
  <video src="exports/motion/bond-sting-1920x1080.mp4" autoplay muted loop playsinline aria-label="The Antimony sting"></video>
  <p class="dim">Six seconds. The Bond builds from its nucleus, the camera pulls back to show a lattice of Bonds, the lattice falls away and the name arrives. Square and 16 by 9 versions are in the kit; the website's opening uses the same sequence.</p>
</div></section>

<section class="band ink"><div class="in">
  <span class="eyebrow">In use</span>
  <h2>Where most people will meet it first.</h2>
  <div class="profile"><img class="ban" src="exports/social/linkedin-company-cover.png" alt="Company cover"><div class="body"><img class="av" src="exports/social/avatar-ink.png" alt=""><b>Antimony</b><span>Software for the people who make the work.</span></div></div>
  <div class="two">
    <figure class="cap"><img class="shot" src="exports/social/linkedin-personal-banner.png" alt="Personal banner"><figcaption>Personal banner, 1584 by 396. The left stays clear for the profile photo.</figcaption></figure>
    <figure class="cap"><img class="shot" src="exports/social/og-image.png" alt="Link card"><figcaption>The card every antimony.inc link unfurls into.</figcaption></figure>
    <figure class="cap"><img class="shot" src="exports/deck/title.png" alt="Deck title slide"><figcaption>Deck title.</figcaption></figure>
    <figure class="cap"><img class="shot" src="exports/social/post-square.png" alt="Square post"><figcaption>A square post: one Bond lit in a lattice.</figcaption></figure>
    <figure class="cap"><img class="shot" src="exports/print/card-front.png" alt="Card front"><figcaption>Card front, 85 by 55 mm.</figcaption></figure>
    <figure class="cap"><img class="shot" src="exports/print/card-back.png" alt="Card back"><figcaption>Card back.</figcaption></figure>
  </div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">Don't</span>
  <h2>Four ways to break it.</h2>
  <div class="dont">
    <figure class="cap"><div class="tile">{bond_svg(INK, COBALT).replace("<svg", '<svg style="transform:rotate(15deg)"')}</div><figcaption>Rotate it. It stands on its lattice.</figcaption></figure>
    <figure class="cap"><div class="tile">{bond_svg(COBALT, INK)}</div><figcaption>Swap the colours. Only the nucleus is coloured.</figcaption></figure>
    <figure class="cap"><div class="tile"><svg viewBox="0 0 100 100" style="width:50%"><path d="{G["bond"]["ink"]}" fill="none" stroke="{INK}" stroke-width="2"/><path d="{G["bond"]["nuc"]}" fill="none" stroke="{COBALT}" stroke-width="2"/></svg></div><figcaption>Outline it. The atoms are solid.</figcaption></figure>
    <figure class="cap"><div class="tile">{bond_svg(INK, COBALT).replace("<svg", '<svg style="transform:scaleX(1.3)"')}</div><figcaption>Stretch it.</figcaption></figure>
  </div>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">The standard</span>
  <h2>What it has to clear, and does.</h2>
  <ul class="check">
    <li>Reads in one colour, with no help from cobalt.</li>
    <li>Reads at 16 px in a browser tab, drawn for that size.</li>
    <li>Stands as an emblem on its own, like the marks we hold ourselves against, and is built from a true fact about the element rather than a picture of a crystal.</li>
    <li>Can be rebuilt from three numbers.</li>
    <li>Moves with a meaning: it builds from the nucleus, and is shown as one of many.</li>
  </ul>
</div></section>

<section class="band"><div class="in">
  <span class="eyebrow">The kit</span>
  <h2>Every file, ready to post.</h2>
  <div class="files">{"".join(f"<div><code>{a}</code><span>{b}</span></div>" for a, b in FILES)}</div>
</div></section>
'''
open("../index.html", "w").write(html); print(len(html))
