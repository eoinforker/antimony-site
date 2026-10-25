"""The Antimony identity, drawn once. Every export reads geo.json, which this script writes.

The Bond: antimony holds five electrons in its outer shell. Drawn as a molecule, five atoms are bound to a nucleus:
one above, one each side, and two that hang from the sides. Read one way it is an A; another, a person standing.
Atoms are squares turned 45 degrees (diamonds), set on a lattice of D units, each R units from centre to tip,
joined by bonds W units wide. The nucleus is cobalt; everything else is ink.
"""
import json, math
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import RecordingPen

D, R, W = 31.0, 15.5, 10.0
CY = 47.5                                   # centres the emblem's height in a 100 unit square
f2 = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")

ATOMS = {"apex": (50, CY - D), "left": (50 - D, CY), "nucleus": (50, CY), "right": (50 + D, CY),
         "leg_l": (50 - D, CY + D), "leg_r": (50 + D, CY + D)}
BONDS = [("nucleus", "apex"), ("nucleus", "left"), ("nucleus", "right"), ("left", "leg_l"), ("right", "leg_r")]

def diamond(x, y, r): return f"M{f2(x)} {f2(y - r)}L{f2(x + r)} {f2(y)}L{f2(x)} {f2(y + r)}L{f2(x - r)} {f2(y)}Z"
def bar(a, b, w):
    (x1, y1), (x2, y2) = a, b
    if x1 == x2: return f"M{f2(x1 - w/2)} {f2(min(y1, y2))}H{f2(x1 + w/2)}V{f2(max(y1, y2))}H{f2(x1 - w/2)}Z"
    return f"M{f2(min(x1, x2))} {f2(y1 - w/2)}H{f2(max(x1, x2))}V{f2(y1 + w/2)}H{f2(min(x1, x2))}Z"

def bond_mark(atoms=ATOMS, r=R, w=W):
    ink = "".join(bar(atoms[a], atoms[b], w) for a, b in BONDS)
    ink += "".join(diamond(*atoms[k], r) for k in atoms if k != "nucleus")
    return {"ink": ink, "nuc": diamond(*atoms["nucleus"], r)}

def lattice(cols, rows, step, ox=0, oy=0):
    """the emblem repeated as a crystal: every molecule shares the lattice, offset by half a step each row"""
    out = []
    for j in range(rows):
        for i in range(cols):
            out.append((ox + i * step * 3 + (j % 2) * step * 1.5, oy + j * step * 2.2))
    return out

# The Seal: the Bond inside a ring, for avatars and anywhere the emblem has to stand alone.
def seal():
    s = 0.6; t = lambda p: (50 + (p[0] - 50) * s, 50 + (p[1] - CY) * s)
    m = bond_mark({k: t(v) for k, v in ATOMS.items()}, R * s, W * s)
    return {"ring": {"cx": 50, "cy": 50, "r": 45.5, "w": 7}, **m}

# The wordmark: Timeless Serif at 420, kerned as the font intends (measured in Chromium), tracked in 14 units,
# the dot of the i replaced by an atom: a diamond, in cobalt where colour is allowed.
KERN = [0, 734.984375, 1310.984375, 1668.984375, 1956.984375, 2810.984375, 3372.984375, 3948.984375]
def wordmark():
    f = TTFont("ts-420-0.ttf"); gs = f.getGlyphSet(); upm = f["head"].unitsPerEm
    cap, xh = f["OS/2"].sCapHeight, f["OS/2"].sxHeight
    names = ["A", "n", "t", "dotlessi", "m", "o", "n", "y"]; track = -14; asc = 930
    d = ""; dot = None
    for i, (g, x) in enumerate(zip(names, KERN)):
        x = x * upm / 966 + track * i
        pen = SVGPathPen(gs); gs[g].draw(TransformPen(pen, (1, 0, 0, -1, x, asc))); d += pen.getCommands()
        if g == "dotlessi":
            rp = RecordingPen(); gs["i"].draw(rp); contours, cur = [], []
            for op, args in rp.value:
                if op == "moveTo": cur = [args[0]]
                elif op == "lineTo": cur.append(args[0])
                elif op in ("qCurveTo", "curveTo"): cur += list(args)
                elif op in ("closePath", "endPath"): contours.append(cur)
            dotc = [c for c in contours if min(p[1] for p in c) > xh][0]
            xs = [p[0] for p in dotc]; ys = [p[1] for p in dotc]
            r = (max(xs) - min(xs)) * 0.66
            dot = diamond(x + (min(xs) + max(xs)) / 2, asc - (min(ys) + max(ys)) / 2 - 8, r)
    end = KERN[-1] * upm / 966 + track * 7 + f["hmtx"]["y"][0]
    return {"letters": d, "dot": dot, "w": round(end, 1), "asc": asc, "cap": cap, "xh": xh, "desc": 240}

out = {"D": D, "R": R, "W": W, "CY": CY, "atoms": ATOMS, "bonds": BONDS,
       "bond": bond_mark(), "seal": seal(), "wordmark": wordmark()}
json.dump(out, open("geo.json", "w"), indent=0)
print("ok", {k: len(json.dumps(v)) for k, v in out.items()})
