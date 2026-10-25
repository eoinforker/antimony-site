"""Writes one HTML page per export into pages/, and pages/manifest.json for render.js."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from kit import *
os.makedirs("pages", exist_ok=True)
MAN = []
def add(name, w, h, html, scale=1, pdf=None):
    open(f"pages/{name}.html", "w").write(html); MAN.append({"name": name, "w": w, "h": h, "scale": scale, "pdf": pdf})
def centre(inner, w, h, bg, pad="0"):
    return page(w, h, f'<div style="position:absolute;inset:0;display:grid;place-items:center;padding:{pad}">{inner}</div>', bg)
SERIF = "'Timeless Serif', Georgia, serif"; SANS = "'Timeless Sans', Arial, sans-serif"; MONO = "'Commit Mono', monospace"

# Logos, as PNG at large sizes (the SVGs are written separately)
for g, gname in [(PAPER, "paper"), (INK, "ink")]:
    fg = INK if g == PAPER else PAPER
    add(f"logo/bond-on-{gname}", 1024, 1024, centre(bond_svg(fg, nucleus_for(g), style="width:72%"), 1024, 1024, g))
    add(f"logo/seal-on-{gname}", 1024, 1024, centre(seal_svg(fg, nucleus_for(g)).replace("<svg", '<svg style="width:84%"'), 1024, 1024, g))
    add(f"logo/lockup-on-{gname}", 2400, 800, centre(lockup_svg(fg, nucleus_for(g), style="width:80%;height:auto"), 2400, 800, g))
    add(f"logo/stacked-on-{gname}", 1600, 1600, centre(lockup_svg(fg, nucleus_for(g), stacked=True, style="width:62%;height:auto"), 1600, 1600, g))
add("logo/bond-on-cobalt", 1024, 1024, centre(bond_svg(PAPER, SKY, style="width:72%"), 1024, 1024, COBALT))

# Avatars: LinkedIn and X crop company logos to a square and people to a circle, so the emblem sits inside the circle's safe area
add("social/avatar-ink", 800, 800, centre(bond_svg(PAPER, SKY, style="width:58%"), 800, 800, INK))
add("social/avatar-paper", 800, 800, centre(bond_svg(INK, COBALT, style="width:58%"), 800, 800, PAPER))
add("social/avatar-cobalt", 800, 800, centre(bond_svg(PAPER, INK, style="width:58%"), 800, 800, COBALT))

# LinkedIn company cover, 1128 by 191 (shown at 2x). The logo overlaps the bottom left on desktop, so the left third stays quiet.
def cover(w, h, scale, unit, lit, line=None):
    t = f'<div style="position:absolute;right:{int(w*0.045)}px;bottom:{int(h*0.2)}px;text-align:right;font:400 {int(h*0.13)}px/1.25 {SERIF};color:{PAPER}">{line}</div>' if line else ""
    fade = f'<div style="position:absolute;inset:0;background:linear-gradient(90deg,{INK} 0%,{INK} 30%,rgba(11,13,12,0) 62%)"></div>'
    return page(w, h, lattice_svg(w, h, unit, LINE_D) + fade + lattice_svg(w, h, unit, LINE_D, lit=lit, nuc=SKY, lit_tone=PAPER, only=lit) + t, INK)
add("social/linkedin-company-cover", 1128, 191, cover(1128, 191, 2, 60, (14, 1)), scale=2)
add("social/linkedin-personal-banner", 1584, 396, cover(1584, 396, 2, 92, (5, 2), "Software for the people<br>who make the work."), scale=2)
add("social/x-header", 1500, 500, cover(1500, 500, 2, 100, (4, 2), "Software for the people<br>who make the work."), scale=2)

# Open Graph: the card a link unfurls into on LinkedIn, X, Slack and iMessage
og = page(1200, 630, lattice_svg(1200, 630, 120, LINE_L, lit=None, nuc=LINE_L) +
    f'<div style="position:absolute;inset:0;background:radial-gradient(60% 70% at 50% 50%,{PAPER} 40%,rgba(244,243,238,0) 100%)"></div>'
    f'<div style="position:absolute;inset:0;display:grid;place-items:center">{lockup_svg(INK, COBALT, style="width:620px;height:auto")}</div>', PAPER)
add("social/og-image", 1200, 630, og, scale=2)

# A square post: the emblem alone, the first thing the account says
add("social/post-square", 1080, 1080, page(1080, 1080, lattice_svg(1080, 1080, 150, LINE_D, lit=(3, 4), nuc=SKY, lit_tone=PAPER, ox=-28, oy=-60), INK))

# Deck title, 1920 by 1080
deck = page(1920, 1080,
    f'<div style="position:absolute;left:120px;top:110px">{lockup_svg(PAPER, SKY, style="height:58px;width:auto")}</div>'
    f'<div style="position:absolute;left:120px;bottom:120px;font:400 92px/1.04 {SERIF};color:{PAPER};letter-spacing:-.015em;max-width:15em">Software for the people<br>who make the work.</div>'
    f'<div style="position:absolute;right:120px;bottom:128px;font:400 22px {MONO};color:#7C8885;letter-spacing:.04em">2026</div>', INK)
add("deck/title", 1920, 1080, deck)

# Business card, 85 by 55 mm plus 3 mm bleed, drawn at 1 mm = 12 px; also printed to PDF at true size
MM = 12; CW, CH = (85 + 6) * MM, (55 + 6) * MM
front = page(CW, CH, f'<div style="position:absolute;inset:0;display:grid;place-items:center">{bond_svg(PAPER, SKY, style=f"width:{22*MM}px")}</div>', INK)
back = page(CW, CH,
    f'<div style="position:absolute;left:{9*MM}px;top:{9*MM}px">{wordmark_svg(INK, COBALT, style=f"height:{5.2*MM}px;width:auto")}</div>'
    f'<div style="position:absolute;left:{9*MM}px;bottom:{9*MM}px;font:400 {2.9*MM}px/1.45 {SANS};color:{INK}">Name Surname<br><span style="color:#5C6461">name@antimony.inc</span></div>'
    f'<div style="position:absolute;right:{9*MM}px;bottom:{9*MM}px;width:{7*MM}px">{bond_svg(INK, COBALT)}</div>', PAPER)
add("print/card-front", CW, CH, front, scale=2, pdf=[91, 61]); add("print/card-back", CW, CH, back, scale=2, pdf=[91, 61])

# Favicons and app icons: drawn large and reduced by the browser, plus the emblem on its own square for app icons
for s in (16, 32, 48, 180, 192, 512):
    pad = {16: "0", 32: "0", 48: "2px"}.get(s, f"{int(s*0.16)}px")
    bg = PAPER if s <= 48 else INK
    fg, nc = (INK, COBALT) if bg == PAPER else (PAPER, SKY)
    add(f"icons/icon-{s}", s, s, page(s, s, f'<div style="position:absolute;inset:0;padding:{pad}">{bond_svg(fg, nc, style="width:100%;height:100%")}</div>', bg), scale=1)

json.dump(MAN, open("pages/manifest.json", "w"))
print(len(MAN), "pages")
