"""Every export of the Break identity, into pages3/ for render.js."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from three import brk, CONT, break_parts
from kit import page, WM, WM_Y0, WM_Y1
INK, PAPER, SKY, COB, WASHI, PRUSSIAN = "#141311", "#EEEAE0", "#94E6FF", "#2448FF", "#F3ECDD", "#1F3F7A"
Q = break_parts(); PR = "file:///home/user/antimony-site/assets/prints/"
os.makedirs("pages3", exist_ok=True); MAN = []
def add(name, w, h, html, scale=1, pdf=None):
    os.makedirs(os.path.dirname(f"pages3/{name}.html"), exist_ok=True); open(f"pages3/{name}.html", "w").write(html); MAN.append(dict(name=name, w=w, h=h, scale=scale, pdf=pdf))
SG = "@font-face { font-family: 'Schibsted Grotesk'; src: url(file:///home/user/antimony-site/assets/fonts/SchibstedGrotesk-VF.woff2); font-weight: 400 900; }"
def P(w, h, body, bg): return page(w, h, body, bg, SG)
def C(inner, w, h, bg): return P(w, h, f'<div style="position:absolute;inset:0;display:grid;place-items:center">{inner}</div>', bg)
GROUND = "#0B0C0C"
VB, WMB = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../x/edge/wm.txt")).read().split("\n", 1)
# the drawn serif wordmark: crystal tittle, t joined to i, y cut at the seam's angle. The tittle is sky on ink and cobalt, Prussian on paper.
def wm(fill, style="", lit=None):
    lit = lit or (PRUSSIAN if fill in (INK, GROUND) else SKY)
    return f'<svg viewBox="{VB}" style="color:{fill};--lit:{lit};{style}">{WMB}</svg>'
def bold(col, px): return f'<span style="font:700 {px}px/1 \'Schibsted Grotesk\',sans-serif;letter-spacing:-.045em;color:{col}">antimony</span>'
def lock(stone, ground, txt, px, serif=False):
    m = brk(stone=stone, ground=ground, style=f"width:{px * 1.15:.0f}px;height:{px * 1.15:.0f}px;display:block;flex:none")
    t = wm(txt, f"height:{px * .62:.0f}px;width:auto")
    return f'<div style="display:flex;align-items:center;gap:{px * .32:.0f}px">{m}{t}</div>'
def window(img, size, stone=INK, ground=WASHI):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 100 100"><defs><clipPath id="c">{CONT["tile"]}</clipPath><clipPath id="g"><path d="{Q["gem"]}"/></clipPath>'
            f'<mask id="m"><rect width="100" height="100" fill="#fff"/><path d="{Q["seam"]}" fill="#000"/><path d="{Q["cav"]}" fill="#000"/></mask></defs>'
            f'<g clip-path="url(#c)"><rect width="100" height="100" fill="{ground}"/><rect width="100" height="100" fill="{stone}" mask="url(#m)"/>'
            f'<image href="{PR}{img}.webp" x="18" y="16" width="64" height="68" preserveAspectRatio="xMidYMid slice" clip-path="url(#g)"/></g></svg>')
# logos
for gn, g, st in [("paper", PAPER, INK), ("ink", GROUND, PAPER), ("cobalt", COB, PAPER)]:
    add(f"logo/mark-on-{gn}", 1024, 1024, C(brk(stone=st, ground=g, style="width:62%;height:62%"), 1024, 1024, g))
    tc = INK if g == PAPER else PAPER
    add(f"logo/lockup-on-{gn}", 2400, 760, C(lock(st, g, tc, 200), 2400, 760, g))
    add(f"logo/wordmark-on-{gn}", 2400, 760, C(wm(tc, "height:150px;width:auto"), 2400, 760, g))
add("logo/mark-round", 1024, 1024, C(brk("round", style="width:62%;height:62%"), 1024, 1024, PAPER))
# icons
for s in (180, 192, 512, 1024): add(f"icons/app-{s}", s, s, P(s, s, brk("square", style="width:100%;height:100%;position:absolute;inset:0"), "transparent"))
for s in (16, 32, 48): add(f"icons/favicon-{s}", s, s, P(s, s, brk(small=s < 30, style="width:100%;height:100%;position:absolute;inset:0"), "#F3F0E8"))
# social
add("social/avatar", 800, 800, C(brk("round", style="width:100%;height:100%"), 800, 800, PAPER))
def cover(w, h, img, line=None, pos="50% 40%"):
    lab = (f'<div style="position:absolute;right:{w * .03:.0f}px;bottom:{h * .12:.0f}px;background:{WASHI};padding:{h * .07:.0f}px {h * .09:.0f}px;border-radius:6px;display:grid;gap:{h * .035:.0f}px">'
           f'{lock(INK, WASHI, PRUSSIAN, h * .1, True)}' + (f'<span style="font:italic 400 {h * .065:.0f}px \'Timeless Serif\',serif;color:{PRUSSIAN}">{line}</span>' if line else "") + '</div>')
    return P(w, h, f'<img src="{PR}{img}.webp" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:{pos}">{lab}', "#1A2A4A")
add("social/linkedin-company-cover", 1128, 191, cover(1128, 191, "87008", None, "50% 45%"), 2)
add("social/linkedin-personal-banner", 1584, 396, cover(1584, 396, "87008", "for the people who make the work."), 2)
add("social/x-header", 1500, 500, cover(1500, 500, "19006", "for the people who make the work."), 2)
add("social/og-image", 1200, 630, C(lock(INK, PAPER, INK, 120), 1200, 630, PAPER), 2)
for n, (img, g, st, cap, cc) in enumerate([("24800", WASHI, INK, "Ejiri in Suruga, Hokusai, about 1831.", PRUSSIAN), ("3652", "#9CCBEA", INK, "Togetsu Bridge, Arashiyama.", PRUSSIAN), ("18972", PRUSSIAN, WASHI, "Autumn moon, Ishiyama.", WASHI)]):
    add(f"social/post-{n + 1}", 1080, 1350, P(1080, 1350, f'<div style="position:absolute;left:170px;top:200px">{window(img, 740, st, g)}</div>'
        f'<div style="position:absolute;left:90px;bottom:80px;font:italic 400 34px \'Timeless Serif\',serif;color:{cc}">{cap}</div>', g))
# deck
add("deck/01-title", 1920, 1080, P(1920, 1080, f'<div style="position:absolute;left:120px;top:110px">{lock(PAPER, GROUND, PAPER, 84)}</div>'
    f'<div style="position:absolute;left:120px;bottom:120px;font:400 104px/1.02 \'Timeless Serif\',serif;color:{PAPER};letter-spacing:-.02em">Software for the people<br>who make the work.</div>', GROUND))
add("deck/02-content", 1920, 1080, P(1920, 1080, f'<div style="position:absolute;right:120px;top:170px">{window("19006", 740)}</div>'
    f'<div style="position:absolute;left:120px;top:110px;font:500 22px \'Commit Mono\',monospace;letter-spacing:.06em;color:#6C6A64">01  WHY WE EXIST</div>'
    f'<div style="position:absolute;left:120px;top:300px;width:820px;font:400 72px/1.06 \'Timeless Serif\',serif;color:{INK};letter-spacing:-.015em">Antimony refined gold by taking away everything that was not gold.</div>'
    f'<div style="position:absolute;left:120px;top:640px;width:760px;font:400 28px/1.5 \'Commit Mono\',monospace;color:#3A3834">We build software that takes the work around the work off the people who make it.</div>', WASHI))
add("deck/03-close", 1920, 1080, C(brk(stone=PAPER, ground=GROUND, style="width:300px;height:300px"), 1920, 1080, GROUND))
# print
MM = 12; CW, CH = 91 * MM, 61 * MM
add("print/card-front", CW, CH, C(brk(stone=PAPER, ground=GROUND, style=f"width:{24 * MM}px;height:{24 * MM}px"), CW, CH, GROUND), 2, [91, 61])
add("print/card-back", CW, CH, P(CW, CH, f'<div style="position:absolute;left:{9 * MM}px;top:{9 * MM}px">{lock(INK, PAPER, INK, 5 * MM, True)}</div>'
    f'<div style="position:absolute;left:{9 * MM}px;bottom:{9 * MM}px;font:400 {2.9 * MM}px/1.45 \'Commit Mono\',monospace;color:{INK}">Name Surname<br><span style="color:#6C6A64">name@antimony.inc</span></div>', PAPER), 2, [91, 61])
AW, AH = 840, 1188
add("print/letterhead", AW, AH, P(AW, AH, f'<div style="position:absolute;left:80px;top:72px">{lock(INK, PAPER, INK, 34, True)}</div>'
    f'<div style="position:absolute;left:80px;right:80px;bottom:56px;display:flex;justify-content:space-between;font:400 11px \'Commit Mono\',monospace;color:#6C6A64"><span>Antimony</span><span>antimony.inc</span></div>', PAPER), 2, [210, 297])
json.dump(MAN, open("pages3/manifest.json", "w")); print(len(MAN))
