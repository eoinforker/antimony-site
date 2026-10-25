"""Round four: 64 rough thumbnails, eight territories of eight. Ink on paper, same box, numbered, no stories."""
import math
INK = "#0B0D0C"
f = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")
def P(*pts): return "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"
def R(x, y, w, h): return P((x, y), (x + w, y), (x + w, y + h), (x, y + h))
def Rr(x, y, w, h): return P((x, y + h), (x + w, y + h), (x + w, y), (x, y))           # wound the other way: a hole
def D(cx, cy, r, ry=None): ry = ry or r; return P((cx, cy - ry), (cx + r, cy), (cx, cy + ry), (cx - r, cy))
def Dr(cx, cy, r, ry=None): ry = ry or r; return P((cx, cy - ry), (cx - r, cy), (cx, cy + ry), (cx + r, cy))
def circ(cx, cy, r, rev=False):
    s = 0 if rev else 1
    return f"M{f(cx - r)} {f(cy)}a{f(r)} {f(r)} 0 1 {s} {f(2 * r)} 0a{f(r)} {f(r)} 0 1 {s} {f(-2 * r)} 0Z"
def poly(n, cx, cy, r, rot=0, rev=False):
    pts = [(cx + r * math.cos(math.radians(rot + 360 / n * k)), cy + r * math.sin(math.radians(rot + 360 / n * k))) for k in range(n)]
    return P(*(pts[::-1] if rev else pts))
def bar(x1, y1, x2, y2, w):
    dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy); nx, ny = -dy / L * w / 2, dx / L * w / 2
    return P((x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny))
def ring(cx, cy, r, w): return circ(cx, cy, r) + circ(cx, cy, r - w, True)
def sq_ring(cx, cy, r, w): return R(cx - r, cy - r, 2 * r, 2 * r) + Rr(cx - r + w, cy - r + w, 2 * (r - w), 2 * (r - w))
def dia_ring(cx, cy, r, w): return D(cx, cy, r) + Dr(cx, cy, r - w * 1.414)
def hexring(cx, cy, r, w, rot=-90): return poly(6, cx, cy, r, rot) + poly(6, cx, cy, r - w * 1.155, rot, True)
def S(d, rule="nonzero", extra=""): return f'<svg viewBox="0 0 100 100" aria-hidden="true"><path d="{d}" fill="{INK}" fill-rule="{rule}"/>{extra}</svg>'
def SE(d, extra=""): return S(d, "evenodd", extra)
def stroke(d, w, cap="butt", join="miter"): return f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{w}" stroke-linecap="{cap}" stroke-linejoin="{join}" stroke-miterlimit="10"/>'
def SS(*parts): return f'<svg viewBox="0 0 100 100" aria-hidden="true">{"".join(parts)}</svg>'
def cutmask(body, cut, i):
    return (f'<svg viewBox="0 0 100 100" aria-hidden="true"><defs><mask id="w{i}" maskUnits="userSpaceOnUse" x="-5" y="-5" width="110" height="110"><rect x="-5" y="-5" width="110" height="110" fill="#fff"/>'
            f'<g fill="#000" stroke="#000">{cut}</g></mask></defs><g mask="url(#w{i})"><path d="{body}" fill="{INK}"/></g></svg>')
T = []
def t(name, items): T.append((name, items))

# 1 Refining: everything reduced until only the gold is left
t("Refining", [
 SE(sq_ring(50, 50, 46, 5) + sq_ring(50, 50, 34, 4) + sq_ring(50, 50, 23, 3) + R(42, 42, 16, 16)),
 S(P((8, 10), (92, 10), (58, 56), (58, 74), (42, 74), (42, 56)) + D(50, 88, 8)),
 SE(P((10, 12), (24, 12), (24, 70), (76, 70), (76, 12), (90, 12), (90, 84), (10, 84)) + R(43, 52, 14, 14)),
 S(R(8, 12, 84, 12) + R(22, 32, 56, 12) + R(36, 52, 28, 12) + R(44, 72, 12, 12)),
 S(P((6, 14), (94, 14), (94, 26), (80, 26), (80, 40), (66, 40), (66, 54), (56, 54), (56, 68), (44, 68), (44, 54), (34, 54), (34, 40), (20, 40), (20, 26), (6, 26)) + D(50, 86, 7)),
 SE(R(10, 8, 80, 58) + Rr(46, 8, 8, 40) + D(50, 84, 9)),
 S("".join(bar(x, y, 50, 72, 4) for x, y in [(10, 10), (30, 10), (50, 10), (70, 10), (90, 10)]) + D(50, 78, 12)),
 SE(P((8, 12), (92, 12), (50, 92)) + P((22, 20), (50, 72), (78, 20)) + P((40, 30), (60, 30), (50, 50))),
])
# 2 The wolf of metals: the grey wolf that devours the dross so the king, gold, comes out pure
t("The wolf", [
 S(P((14, 6), (34, 30), (66, 30), (86, 6), (90, 48), (50, 96), (10, 48))),
 SE(P((14, 6), (34, 30), (66, 30), (86, 6), (90, 48), (50, 96), (10, 48)) + Dr(34, 52, 6, 4) + Dr(66, 52, 6, 4)),
 S(P((6, 94), (22, 40), (40, 8), (52, 34), (94, 46), (94, 58), (60, 64), (40, 94))),
 SE(P((50, 18), (96, 50), (50, 82), (4, 50)) + Dr(50, 50, 16)  , ""),
 S(P((8, 90), (30, 10), (46, 60)) + P((54, 60), (70, 10), (92, 90))),
 SE(P((10, 8), (90, 8), (90, 56), (50, 96), (10, 56)) + P((24, 20), (36, 34), (64, 34), (76, 20), (78, 52), (50, 82), (22, 52)).replace("M", "M", 1)),
 S(D(28, 22, 13) + D(72, 22, 13) + D(50, 46, 13) + D(36, 72, 10) + D(64, 72, 10) + D(50, 90, 8)),
 SE(R(6, 6, 88, 88) + Rr(6, 6, 0.01, 0.01) + P((20, 94), (20, 54), (34, 30), (48, 40), (60, 14), (68, 42), (82, 52), (82, 94))),
])
# 3 Metal: ingots, hallmarks, the stamp that proves purity
t("Metal", [
 SE(P((6, 74), (22, 30), (78, 30), (94, 74)) + P((50, 40), (36, 66), (43, 66), (50, 52), (57, 66), (64, 66))),
 SE(R(6, 24, 88, 52) + Rr(12, 30, 76, 40), '<text x="50" y="62" text-anchor="middle" style="font:700 30px Georgia" fill="#0B0D0C">Sb</text>'),
 SE(P((10, 8), (90, 8), (90, 50), (50, 94), (10, 50)) + Dr(50, 44, 18)),
 SE(circ(50, 50, 46) + circ(50, 50, 40, True), '<text x="50" y="62" text-anchor="middle" style="font:700 34px Georgia" fill="#0B0D0C">51</text>'),
 S(P((30, 34), (70, 34), (78, 52), (22, 52)) + P((10, 58), (48, 58), (54, 76), (4, 76)) + P((52, 58), (90, 58), (96, 76), (46, 76))),
 SE(poly(8, 50, 50, 48, 22.5) + poly(8, 50, 50, 40, 22.5, True) + R(28, 46, 44, 8)),
 SE(D(50, 50, 48) + Dr(50, 50, 40) + P((50, 22), (34, 72), (42, 72), (50, 46), (58, 72), (66, 72))),
 SE(R(10, 10, 80, 80) + P((50, 22), (26, 80), (40, 80), (50, 52), (60, 80), (74, 80))),
])
# 4 The library: Borges's hexagonal galleries, shelves without end, books that lean on each other
t("The library", [
 SE(hexring(50, 50, 48, 7) + R(36, 30, 6, 40) + R(47, 26, 6, 48) + R(58, 30, 6, 40)),
 S(R(12, 50, 9, 44) + R(24, 38, 9, 56) + R(36, 24, 9, 70) + R(48, 10, 9, 84) + R(60, 24, 9, 70) + R(72, 38, 9, 56) + R(84, 50, 9, 44)),
 S(P((50, 20), (50, 92), (6, 72), (6, 2)) + P((54, 20), (94, 2), (94, 72), (54, 92))),
 SE(R(4, 4, 92, 92) + Rr(14, 14, 72, 72) + R(22, 22, 56, 56) + Rr(30, 30, 40, 40) + R(38, 38, 24, 24) + Rr(44, 44, 12, 12)),
 SE(P((8, 20), (60, 20), (68, 8), (92, 8), (92, 92), (8, 92)) + Rr(18, 30, 64, 52)),
 S(P((30, 2), (70, 2), (70, 98), (50, 80), (30, 98))),
 SE("".join(poly(6, 50 + 26 * math.cos(math.radians(a)), 50 + 26 * math.sin(math.radians(a)), 14, 0) for a in range(30, 390, 60)) + poly(6, 50, 50, 14, 0)),
 S(R(6, 90, 88, 6) + bar(26, 90, 50, 10, 14) + bar(74, 90, 50, 10, 14)),
])
# 5 Crystal: stibnite's needles, the lattice, antimony's layers
t("Crystal", [
 S(P((50, 2), (62, 16), (62, 98), (38, 98), (38, 16))),
 S(P((50, 2), (58, 12), (58, 98), (42, 98), (42, 12)) + P((22, 20), (30, 26), (40, 98), (28, 98), (18, 28)) + P((78, 20), (82, 28), (72, 98), (60, 98), (70, 26))),
 SE(R(6, 6, 88, 88) + "".join(Rr(10 + i * 21, 10 + j * 21, 17, 17) for i in range(4) for j in range(4) if (i, j) != (2, 1))),
 S(P((32, 6), (94, 6), (70, 34), (8, 34)) + P((6, 39), (66, 39), (66, 94), (6, 94)) + P((71, 37), (94, 10), (94, 64), (71, 92))),
 S("".join(P((4, y), (24, y - 12), (44, y), (64, y - 12), (84, y), (96, y - 7), (96, y + 1), (84, y + 8), (64, y - 4), (44, y + 8), (24, y - 4), (4, y + 8)) for y in (24, 48, 72, 96))),
 S(P((10, 96), (40, 4), (52, 4), (26, 96)) + P((90, 96), (60, 4), (48, 4), (74, 96))),
 SE(P((50, 2), (94, 40), (50, 98), (6, 40)) + P((50, 2), (66, 40), (50, 98), (34, 40))),
 SE(R(4, 4, 92, 92) + Rr(10, 10, 80, 80) + P((50, 18), (62, 30), (62, 82), (38, 82), (38, 30))),
])
# 6 Monograms: A, Sb, 51
t("Monograms", [
 SE(P((36, 6), (64, 6), (96, 94), (66, 94), (60, 76), (40, 76), (34, 94), (4, 94)) + P((50, 30), (56, 58), (44, 58)) + Rr(47, 4, 6, 92)),
 S(P((8, 94), (40, 6), (48, 6), (48, 94)) + P((52, 30), (60, 30), (92, 94), (52, 94))),
 SS(stroke("M74 18 H34 Q20 18 20 32 Q20 46 34 46 H58 Q72 46 72 60 Q72 74 58 74 H18", 10), stroke("M82 8 V92", 10)),
 SS(stroke("M60 14 H22 V46 H44 Q60 46 60 62 Q60 82 40 82 H18", 11), stroke("M80 14 V86", 11)),
 S(P((30, 6), (44, 6), (72, 94), (58, 94)) + P((30, 6), (44, 6), (16, 94), (2, 94)) + R(10, 62, 88, 10)),
 SE(circ(44, 56, 34) + Dr(44, 56, 14) + R(78, 22, 12, 68)),
 S(P((50, 6), (94, 94), (78, 94), (50, 36), (22, 94), (6, 94)) + D(50, 74, 9)),
 SE(R(6, 6, 88, 88) + P((50, 20), (80, 94), (66, 94), (50, 54), (34, 94), (20, 94))),
])
# 7 Fire: the athanor, the furnace that never goes out
t("Fire", [
 SE(P((22, 96), (22, 30), (50, 4), (78, 30), (78, 96)) + P((40, 96), (40, 70), (60, 70), (60, 96))),
 S(P((50, 4), (74, 46), (50, 96), (26, 46)) + P((20, 40), (36, 66), (24, 96), (8, 66)) + P((80, 40), (92, 66), (76, 96), (64, 66))),
 SE(R(8, 8, 84, 84) + "M34 92 V52 A16 16 0 0 1 66 52 V92 Z" + R(44, 72, 12, 12)),
 SS(stroke("M26 94 V54 Q26 44 34 38 Q42 32 42 22 V6", 9), stroke("M50 94 V54 Q50 44 58 38 Q66 32 66 22 V6", 9), stroke("M74 94 V54 Q74 44 82 38", 9)),
 SE(R(30, 4, 40, 92) + Rr(44, 4, 12, 50) + R(10, 70, 80, 26)),
 SE(circ(38, 62, 30) + circ(38, 62, 22, True) + bar(58, 40, 94, 6, 9)),
 S(P((40, 4), (60, 4), (60, 30), (80, 50), (80, 96), (20, 96), (20, 50), (40, 30))),
 S(R(6, 74, 88, 22) + R(18, 50, 64, 18) + R(30, 26, 40, 18) + R(42, 4, 16, 16)),
])
# 8 Emblems: power without menace; enclosed, symmetric, few parts
t("Emblems", [
 SE(ring(50, 50, 47, 7) + P((50, 14), (78, 74), (66, 74), (50, 40), (34, 74), (22, 74))),
 SE(poly(8, 50, 50, 48, 22.5) + poly(8, 50, 50, 41, 22.5, True) + D(50, 50, 20)),
 SE(circ(50, 50, 48) + Rr(18, 18, 64, 64) + R(30, 30, 40, 40) + Dr(50, 50, 12)),
 SE(P((10, 6), (90, 6), (90, 56), (50, 96), (10, 56)) + Rr(22, 20, 56, 8) + Rr(22, 36, 56, 8) + Rr(30, 52, 40, 8)),
 SE(circ(50, 50, 48) + P((50, 4), (22, 96), (30, 96), (50, 30), (70, 96), (78, 96)) + Rr(30, 64, 40, 6)),
 SE(poly(6, 50, 50, 48, -90) + P((50, 20), (76, 76), (64, 76), (50, 46), (36, 76), (24, 76))),
 SE(ring(50, 56, 40, 8) + D(50, 14, 13)),
 S(P((6, 30), (50, 6), (94, 30), (94, 44), (50, 20), (6, 44)) + P((6, 56), (50, 32), (94, 56), (94, 70), (50, 46), (6, 70)) + P((6, 82), (50, 58), (94, 82), (94, 96), (50, 72), (6, 96))),
])
