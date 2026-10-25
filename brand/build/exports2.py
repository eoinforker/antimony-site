"""Every export of the Crystal A identity: one HTML page each into pages2/, listed in pages2/manifest.json for render.js."""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from mark import *
from kit import page
os.makedirs("pages2", exist_ok=True)
ART = "file:///home/user/antimony-site/brand/art/riso/"
MAN = []
def add(name, w, h, html, scale=1, pdf=None):
    os.makedirs(os.path.dirname(f"pages2/{name}.html"), exist_ok=True)
    open(f"pages2/{name}.html", "w").write(html); MAN.append({"name": name, "w": w, "h": h, "scale": scale, "pdf": pdf})
SERIF = "'Timeless Serif', Georgia, serif"; SANS = "'Timeless Sans', Arial, sans-serif"; MONO = "'Commit Mono', monospace"
def centre(inner, w, h, bg): return page(w, h, f'<div style="position:absolute;inset:0;display:grid;place-items:center">{inner}</div>', bg)
def window(plate, size, x=0, y=0, fill=None):
    """the mark as a window: the four pieces cut from an archive plate"""
    clip = "".join(f'<path d="{poly(PC[k])}"/>' for k in ("wing_l", "wing_r", "foot"))
    return (f'<svg width="{size}" height="{size}" viewBox="-1 -1 102 102" style="position:absolute;left:{x}px;top:{y}px" aria-hidden="true"><defs><clipPath id="w">{clip}</clipPath></defs>'
            f'<image href="{ART}{plate}.webp" x="-1" y="-1" width="102" height="102" preserveAspectRatio="xMidYMid slice" clip-path="url(#w)"/>'
            + "".join(f'<path d="{poly(PC[k])}" fill="none" stroke="{INK}" stroke-width=".45" stroke-linejoin="round"/>' for k in ("wing_l", "wing_r", "foot")) +
            f'<path d="{poly(PC["counter"])}" fill="{COBALT}"/></svg>')
# logos
for g, gn in [(PAPER, "paper"), (INK, "ink"), (COBALT, "cobalt")]:
    fg = INK if g == PAPER else PAPER
    add(f"logo/mark-on-{gn}", 1024, 1024, centre(mark(fg, gold_for(g), "width:66%"), 1024, 1024, g))
    if g != COBALT:
        add(f"logo/lockup-on-{gn}", 2400, 760, centre(lockup(fg, gold_for(g), "width:80%;height:auto"), 2400, 760, g))
        add(f"logo/stacked-on-{gn}", 1600, 1600, centre(stacked(fg, gold_for(g), "width:58%;height:auto"), 1600, 1600, g))
        add(f"logo/wordmark-on-{gn}", 2400, 700, centre(wordmark(fg, gold_for(g), "width:76%;height:auto"), 2400, 700, g))
# app icons: the mark on ink with room to breathe inside platform masks
for s in (180, 192, 512, 1024):
    add(f"icons/app-{s}", s, s, centre(mark(PAPER, SKY, f"width:{int(s * .62)}px"), s, s, INK))
# avatars: filling the square, safe inside a circle crop
add("social/avatar-ink", 800, 800, centre(mark(PAPER, SKY, "width:64%"), 800, 800, INK))
add("social/avatar-paper", 800, 800, centre(mark(INK, COBALT, "width:64%"), 800, 800, PAPER))
# covers: the lattice, quiet on the left where the profile photo and logo sit, one counter lit
def cover(w, h, size, lit, line=None, scale=2):
    lat = lattice(int(w / (size * .866)) + 3, int(h / (size * .75)) + 3, size, lit=lit, fill="#161D1B", gold=SKY, lit_fill=PAPER, ox=-size * .3, oy=-size * .1, w_=w, h_=h)
    fade = f'<div style="position:absolute;inset:0;background:linear-gradient(90deg,{INK} 0%,{INK} 28%,rgba(11,13,12,.55) 52%,rgba(11,13,12,0) 74%)"></div>'
    t = (f'<div style="position:absolute;right:{int(w * .045)}px;bottom:{int(h * .2)}px;text-align:right;font:400 {int(h * .12)}px/1.22 {SERIF};color:{PAPER};letter-spacing:-.01em">{line}</div>' if line else "")
    top = lattice(int(w / (size * .866)) + 3, int(h / (size * .75)) + 3, size, lit=lit, fill="#161D1B", gold=SKY, ox=-size * .3, oy=-size * .1, w_=w, h_=h, lit_fill=PAPER, only=True)
    return page(w, h, f'<div style="position:absolute;inset:0">{lat}</div>{fade}<div style="position:absolute;inset:0">{top}</div>{t}', INK)
add("social/linkedin-company-cover", 1128, 191, cover(1128, 191, 86, (9, 1)), 2)
add("social/linkedin-personal-banner", 1584, 396, cover(1584, 396, 132, (9, 1), "Software for the people<br>who make the work."), 2)
add("social/x-header", 1500, 500, cover(1500, 500, 150, (8, 1), "Software for the people<br>who make the work."), 2)
# the link card
og = page(1200, 630, f'<div style="position:absolute;inset:0;opacity:.07">{lattice(16, 10, 120, fill=INK, ox=-30, oy=-30, w_=1200, h_=630)}</div>'
          f'<div style="position:absolute;inset:0;background:radial-gradient(56% 62% at 50% 50%,{PAPER} 45%,rgba(244,243,238,0) 100%)"></div>'
          f'<div style="position:absolute;inset:0;display:grid;place-items:center">{lockup(INK, COBALT, "width:640px;height:auto")}</div>', PAPER)
add("social/og-image", 1200, 630, og, 2)
# posts: the mark struck large; the mark as a window onto the archive
add("social/post-mark", 1080, 1080, centre(mark(PAPER, SKY, "width:56%"), 1080, 1080, INK))
add("social/post-archive", 1080, 1350, page(1080, 1350, window("V0025578-two", 820, 130, 150) +
    f'<div style="position:absolute;left:130px;right:130px;bottom:110px;display:flex;justify-content:space-between;align-items:end;font:400 30px/1.3 {SERIF};color:{INK}"><span>The laboratory, 1763.<br><span style="color:#5C6461">From the archive.</span></span>{wordmark(INK, COBALT, "height:38px;width:auto")}</div>', PAPER))
# the deck
add("deck/01-title", 1920, 1080, page(1920, 1080,
    f'<div style="position:absolute;left:120px;top:110px">{lockup(PAPER, SKY, "height:62px;width:auto")}</div>'
    f'<div style="position:absolute;left:120px;bottom:120px;font:400 104px/1.02 {SERIF};color:{PAPER};letter-spacing:-.02em">Software for the people<br>who make the work.</div>'
    f'<div style="position:absolute;right:-120px;top:120px;opacity:.9">{mark("#161D1B", "#161D1B", "width:760px")}</div>', INK))
add("deck/02-content", 1920, 1080, page(1920, 1080, window("V0039777EL-ink", 720, 1080, 180) +
    f'<div style="position:absolute;left:120px;top:110px;font:500 22px {MONO};letter-spacing:.06em;color:#5C6461">01  WHY WE EXIST</div>'
    f'<div style="position:absolute;left:120px;top:300px;width:820px;font:400 72px/1.06 {SERIF};color:{INK};letter-spacing:-.015em">Antimony refined gold by taking away everything that was not gold.</div>'
    f'<div style="position:absolute;left:120px;top:640px;width:760px;font:400 28px/1.5 {SANS};color:#353937">We build software that takes the work around the work off the people who make it, so what is left is theirs.</div>'
    f'<div style="position:absolute;left:120px;bottom:100px">{wordmark(INK, COBALT, "height:34px;width:auto")}</div>', PAPER))
add("deck/03-close", 1920, 1080, centre(stacked(PAPER, SKY, "width:520px;height:auto"), 1920, 1080, INK))
# print: card (85 x 55 mm, 3 mm bleed), letterhead (A4)
MM = 12; CW, CH = 91 * MM, 61 * MM
add("print/card-front", CW, CH, centre(mark(PAPER, SKY, f"width:{24 * MM}px"), CW, CH, INK), 2, [91, 61])
add("print/card-back", CW, CH, page(CW, CH,
    f'<div style="position:absolute;left:{9*MM}px;top:{9*MM}px">{wordmark(INK, COBALT, f"height:{5*MM}px;width:auto")}</div>'
    f'<div style="position:absolute;left:{9*MM}px;bottom:{9*MM}px;font:400 {2.9*MM}px/1.45 {SANS};color:{INK}">Name Surname<br><span style="color:#5C6461">name@antimony.inc</span></div>'
    f'<div style="position:absolute;right:{9*MM}px;bottom:{9*MM}px">{mark(INK, COBALT, f"width:{8*MM}px")}</div>', PAPER), 2, [91, 61])
AW, AH = 210 * 4, 297 * 4
add("print/letterhead", AW, AH, page(AW, AH,
    f'<div style="position:absolute;left:{20*4}px;top:{18*4}px">{lockup(INK, COBALT, f"height:{9*4}px;width:auto")}</div>'
    f'<div style="position:absolute;left:{20*4}px;bottom:{14*4}px;right:{20*4}px;display:flex;justify-content:space-between;font:400 {2.6*4}px/1.5 {SANS};color:#5C6461"><span>Antimony</span><span>antimony.inc</span></div>'
    f'<div style="position:absolute;right:{20*4}px;top:{18*4}px;font:400 {2.6*4}px/1.5 {MONO};color:#5C6461;text-align:right">51 Sb</div>', PAPER), 2, [210, 297])
json.dump(MAN, open("pages2/manifest.json", "w")); print(len(MAN), "pages")
