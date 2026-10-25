"""The Prism family. Stibnite grows as long prisms with pointed tips, the shape of a Final Fantasy crystal; seen front on,
the tip of a prism is an A. Every mark here is drawn on one grid: a 100 unit square, the prism 40 wide, its tip 22 tall."""
import math, itertools
INK, GOLD = "#0B0D0C", "#2448FF"
uid = itertools.count()
f = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")
def P(*pts, close=True): return "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + ("Z" if close else "")
# the prism, front on: tip, shoulders, body, foot
def prism(cx=50, top=4, w=36, tip=24, foot=12, bottom=96):
    h = w / 2
    T = (cx, top); SL = (cx - h, top + tip); SR = (cx + h, top + tip)
    BL = (cx - h, bottom - foot); BR = (cx + h, bottom - foot); B = (cx, bottom)
    return dict(T=T, SL=SL, SR=SR, BL=BL, BR=BR, B=B, cx=cx)
G = prism()
def svg(body, style="", vb="0 0 100 100", defs=""): return f'<svg viewBox="{vb}" style="{style}" aria-hidden="true"><defs>{defs}</defs>{body}</svg>'
def lines(paths, sw, color, cap="butt", join="miter"):
    return "".join(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="{cap}" stroke-linejoin="{join}" stroke-miterlimit="12"/>' for d in paths)
M = {}
# 1 THE PRISM: planes. The left face in ink, the right face open, the tip's two facets meeting in an A, the bar the shoulder line.
def m_prism(ink=INK, gold=GOLD, gap=3.2):
    g = G; c = g["cx"]
    left = P(g["T"], (c - gap / 2, g["T"][1] + gap * 1.9), (c - gap / 2, g["B"][1] - gap * 1.9), g["B"], g["BL"], g["SL"])
    right_tip = P((c + gap / 2, g["T"][1] + gap * 1.9), g["T"], g["SR"], (g["SR"][0], g["SR"][1] - 0), (c + gap / 2, g["SR"][1] - 0))
    # the right face, below the shoulder line, in gold: the light side of the crystal
    right = P((c + gap / 2, g["SR"][1] + gap), (g["SR"][0], g["SR"][1] + gap), g["BR"], g["B"], (c + gap / 2, g["B"][1] - gap * 1.9))
    tipR = P((c + gap / 2, g["T"][1] + gap * 1.9), g["T"], g["SR"], (c + gap / 2, g["SR"][1]))
    return svg(f'<path d="{left}" fill="{ink}"/><path d="{tipR}" fill="{ink}"/><path d="{right}" fill="{gold}"/>')
M["prism"] = ("The Prism", "A crystal of stibnite, front on. Its left face and its tip in ink; the light face in the gold. The tip is the A; the line where it meets the body is the bar.", m_prism)
# 2 THE LINE: Perplexity's discipline. One weight; the axis runs the full height; the A is the tip; the bar runs out past the faces.
def m_line(ink=INK, gold=GOLD, sw=6.2):
    g = G; c = g["cx"]
    outline = P(g["T"], g["SR"], g["BR"], g["B"], g["BL"], g["SL"])
    return svg(lines([outline], sw, ink) + lines([f"M{c} {g['T'][1]}V{g['B'][1]}", f"M{g['SL'][0] - 10} {g['SL'][1]}H{g['SR'][0] + 10}"], sw, ink)
               + f'<path d="{P((c, g["T"][1] + 9), (g["SR"][0] - 5.2, g["SR"][1] - 3.1), (c, g["SR"][1] - 3.1))}" fill="{gold}"/>')
M["line"] = ("The Line", "One line weight, built on its axis, the way Perplexity's mark is. The tip is an A, the bar runs out past the crystal, and one facet of the tip holds the gold.", m_line)
# 3 THE SPRAY: three prisms from one seed, the middle tallest. Stibnite grows in sprays; Arasaka's tree is three on stems.
def m_spray(ink=INK, gold=GOLD, ring=False):
    out = ""
    for ang, L, w, col in [(-28, 74, 17, ink), (28, 74, 17, ink), (0, 92, 21, gold)]:
        a = math.radians(ang); ox, oy = 50, 97
        dx, dy = math.sin(a), -math.cos(a); nx, ny = -dy, dx
        tip = w * .62; base = 10
        pts = [(ox + dx * base - nx * w * .18, oy + dy * base - ny * w * .18), (ox + dx * (L - tip) - nx * w / 2, oy + dy * (L - tip) - ny * w / 2), (ox + dx * L, oy + dy * L),
               (ox + dx * (L - tip) + nx * w / 2, oy + dy * (L - tip) + ny * w / 2), (ox + dx * base + nx * w * .18, oy + dy * base + ny * w * .18)]
        out += f'<path d="{P(*pts)}" fill="{col}"/>'
        # a facet line down each crystal's axis, knocked out
        out += f'<path d="M{f(ox + dx * (base + 4))} {f(oy + dy * (base + 4))}L{f(ox + dx * (L - 2))} {f(oy + dy * (L - 2))}" stroke="var(--knock, #F4F3EE)" stroke-width="1.6"/>'
    if ring: out = f'<circle cx="50" cy="52" r="47" fill="none" stroke="{ink}" stroke-width="5.5"/>' + out.replace("97", "97")
    return svg(out)
M["spray"] = ("The Spray", "Stibnite grows in sprays from a single seed. Three crystals, the middle one tallest and in the gold: one thing that only exists with the others.", m_spray)
# 4 THE CREST: the prism with two sweeping wings of fine line, as Final Fantasy crowns its crystals
def m_crest(ink=INK, gold=GOLD):
    g = prism(w=26, tip=17, foot=9, top=8, bottom=92); c = 50
    crystal = f'<path d="{P(g["T"], g["SR"], g["BR"], g["B"], g["BL"], g["SL"])}" fill="{ink}"/><path d="{P(g["T"], g["SR"], (c, g["SR"][1]))}" fill="{gold}"/>'
    crystal += lines([f"M{c} {g['SR'][1]}V{g['B'][1] - 3}"], 1.4, "var(--knock, #F4F3EE)")
    wings = lines([f"M{c - 16} 86C{c - 40} 78 {c - 46} 52 {c - 30} 30C{c - 24} 22 {c - 20} 26 {c - 22} 34",
                   f"M{c + 16} 86C{c + 40} 78 {c + 46} 52 {c + 30} 30C{c + 24} 22 {c + 20} 26 {c + 22} 34"], 3.4, ink, "round", "round")
    wings += lines([f"M{c - 22} 72C{c - 32} 64 {c - 33} 50 {c - 26} 42", f"M{c + 22} 72C{c + 32} 64 {c + 33} 50 {c + 26} 42"], 2.2, ink, "round")
    return svg(wings + crystal)
M["crest"] = ("The Crest", "The crystal crowned with two sweeping wings of fine line, the way Final Fantasy dresses its crystals. Ceremonial, for seals and the moments that matter.", m_crest)
# 5 THE PAIR: two prisms leaning into each other until their tips touch: an A made of two crystals, never alone
def m_pair(ink=INK, gold=GOLD):
    out = ""
    for s, col in [(-1, ink), (1, gold)]:
        a = math.radians(20 * s); bx = 50 + s * 31; by = 96
        dx, dy = -math.sin(a) * -1 * -1, -math.cos(a); dx = -s * math.sin(math.radians(20)); L = 90; w = 19; tip = 13
        nx, ny = -dy, dx
        pts = [(bx - nx * w / 2, by - ny * w / 2), (bx + dx * (L - tip) - nx * w / 2, by + dy * (L - tip) - ny * w / 2), (bx + dx * L, by + dy * L),
               (bx + dx * (L - tip) + nx * w / 2, by + dy * (L - tip) + ny * w / 2), (bx + nx * w / 2, by + ny * w / 2)]
        out += f'<path d="{P(*pts)}" fill="{col}"/>'
    out += f'<path d="M24 66H76" stroke="var(--knock, #F4F3EE)" stroke-width="4"/>'
    return svg(out)
M["pair"] = ("The Pair", "Two crystals leaning in until their tips touch: an A made of two, one ink and one gold. Antimony is almost never found alone.", m_pair)
# 6 THE ORBIT: the prism with a fine ring around it, passing behind at the top and in front at the foot
def m_orbit(ink=INK, gold=GOLD):
    g = prism(w=30, tip=20, foot=10, top=6, bottom=94); c = 50
    crystal = f'<path d="{P(g["T"], g["SR"], g["BR"], g["B"], g["BL"], g["SL"])}" fill="{ink}"/><path d="{P(g["T"], g["SR"], (c, g["SR"][1]))}" fill="{gold}"/>'
    back = f'<path d="M6 54A44 15 -14 0 1 94 46" fill="none" stroke="{ink}" stroke-width="3.2"/>'
    front = f'<path d="M94 46A44 15 -14 0 1 6 54" fill="none" stroke="var(--knock, #F4F3EE)" stroke-width="8"/><path d="M94 46A44 15 -14 0 1 6 54" fill="none" stroke="{ink}" stroke-width="3.2"/>'
    return svg(back + crystal + front)
M["orbit"] = ("The Orbit", "The crystal with a fine ring around it, behind at the top and in front at the foot: a world of its own, the way Porter Robinson's marks hold a small universe.", m_orbit)
