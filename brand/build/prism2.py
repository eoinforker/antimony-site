"""The Prism family, refined. A hexagonal prism seen front on shows three faces: a narrow left face, a broad front face
and a narrow right face, in widths of 1 : 2 : 1. Its tip is three facets meeting at a point. Facets are separated by a
hairline gap of the ground, as cut stone is. The bar is a gap cut across all three faces where the tip meets the body."""
import math, itertools
INK, GOLD, KNOCK = "#0B0D0C", "#2448FF", "#F4F3EE"
f = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")
def P(pts): return "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"
def rot(pts, a, o):
    c, s = math.cos(a), math.sin(a); return [(o[0] + (x - o[0]) * c - (y - o[1]) * s, o[1] + (x - o[0]) * s + (y - o[1]) * c) for x, y in pts]
def crystal(cx=50, top=3, bottom=97, w=34, tip=26, foot=10, gap=2.4, bar=True, lean=0, scale=1.0, origin=None):
    """faces: [(name, polygon)] for one prism. names: tl, tf, tr (tip facets), bl, bf, br (body faces), fl, ff, fr (foot)"""
    q = w / 4; xs = [cx - 2 * q, cx - q, cx + q, cx + 2 * q]          # face edges: 1 : 2 : 1
    ys = top + tip; yb = bottom - foot; g = gap / 2
    T = (cx, top); B = (cx, bottom)
    F = []
    # tip facets: each a triangle from the apex to its face's top edge, with gaps along the ridges
    F.append(("tl", [(T[0] - g * .6, T[1] + g * 2.2), (xs[1] - g, ys - (g if bar else 0)), (xs[0], ys - (g if bar else 0))]))
    F.append(("tf", [(T[0], T[1] + g * 2.6), (xs[2] - g, ys - (g if bar else 0)), (xs[1] + g, ys - (g if bar else 0))]))
    F.append(("tr", [(T[0] + g * .6, T[1] + g * 2.2), (xs[3], ys - (g if bar else 0)), (xs[2] + g, ys - (g if bar else 0))]))
    y0 = ys + (g if bar else 0)
    F.append(("bl", [(xs[0], y0), (xs[1] - g, y0), (xs[1] - g, yb), (xs[0], yb)]))
    F.append(("bf", [(xs[1] + g, y0), (xs[2] - g, y0), (xs[2] - g, yb), (xs[1] + g, yb)]))
    F.append(("br", [(xs[2] + g, y0), (xs[3], y0), (xs[3], yb), (xs[2] + g, yb)]))
    F.append(("fl", [(xs[0], yb + g), (xs[1] - g, yb + g), (B[0] - g * .6, B[1] - g * 2.2)]))
    F.append(("ff", [(xs[1] + g, yb + g), (xs[2] - g, yb + g), (B[0], B[1] - g * 2.6)]))
    F.append(("fr", [(xs[2] + g, yb + g), (xs[3], yb + g), (B[0] + g * .6, B[1] - g * 2.2)]))
    if scale != 1 or lean:
        o = origin or (cx, bottom)
        F = [(n, rot([(o[0] + (x - o[0]) * scale, o[1] + (y - o[1]) * scale) for x, y in pts], lean, o)) for n, pts in F]
    return F
def svg(faces, colours, style="", vb="0 0 100 100", extra="", knock=None, front=()):
    """knock: draw a ground coloured outline under the faces whose names start with any of `front`, so they sit in front"""
    body = ""
    for n, pts in faces:
        if knock and any(n.startswith(p) for p in front):
            body += f'<path d="{P(pts)}" fill="{knock}" stroke="{knock}" stroke-width="3.2" stroke-linejoin="round"/>'
        body += f'<path d="{P(pts)}" fill="{colours.get(n, colours["*"])}"/>'

    return f'<svg viewBox="{vb}" style="{style}" aria-hidden="true">{extra}{body}</svg>'
# shading schemes: where the light falls. The gold is always the facet that catches the light.
def light(ink=INK, gold=GOLD, mid=None):
    mid = mid or ink
    return {"*": ink, "tr": gold, "br": gold, "fr": ink, "tf": mid, "bf": mid}
M = {}
def prism_mark(ink=INK, gold=GOLD, knock=KNOCK, style=""):
    return svg(crystal(), {"*": ink, "tf": gold}, style)
M["prism_tip"] = ("The Prism, lit tip", "A stibnite crystal front on, three faces wide. The light catches one facet of the tip: the gold.", lambda ink=INK, gold=GOLD, style="": svg(crystal(), {"*": ink, "tf": gold}, style))
M["prism_face"] = ("The Prism, lit face", "The same crystal with its right side in the light, tip to foot.", lambda ink=INK, gold=GOLD, style="": svg(crystal(), {"*": ink, "tr": gold, "br": gold, "fr": gold}, style))
M["prism_lean"] = ("The Prism, floating", "Leaning twelve degrees, as a crystal hangs in the air in Final Fantasy, with two small shards beneath it.", lambda ink=INK, gold=GOLD, style="": svg(
    crystal(top=5, bottom=95, w=32, tip=24, foot=10, lean=math.radians(12), origin=(50, 50)), {"*": ink, "tf": gold}, style))
def spray(ink=INK, gold=GOLD, ring=False, style=""):
    faces = []
    for ang, s, col in [(-24, .74, "a"), (24, .74, "b"), (0, 1.0, "c")]:
        fs = crystal(top=4, bottom=96, w=24, tip=19, foot=0.01, gap=1.9, scale=s, lean=math.radians(ang), origin=(50, 97))
        faces += [((col + n), pts) for n, pts in fs if not n.startswith("f")]
    cols = {"*": ink, "ctf": gold}
    extra = f'<circle cx="50" cy="52" r="46" fill="none" stroke="{ink}" stroke-width="5"/>' if ring else ""
    if ring:
        faces = [(n, [(50 + (x - 50) * .72, 52 + (y - 52) * .72 + 2) for x, y in pts]) for n, pts in faces]
    return svg(faces, cols, style, extra=extra, knock=KNOCK, front=("c",))
M["spray"] = ("The Spray", "Three crystals from one seed, the way stibnite grows: the middle tallest, its tip lit.", lambda ink=INK, gold=GOLD, style="": spray(ink, gold, False, style))
M["spray_ring"] = ("The Spray, sealed", "The spray inside a ring: an emblem, for seals, uniforms and the side of a building.", lambda ink=INK, gold=GOLD, style="": spray(ink, gold, True, style))
def pair(ink=INK, gold=GOLD, style=""):
    a = math.radians(19)
    L = crystal(cx=50, top=3, bottom=98, w=20, tip=15, foot=0.01, gap=1.8, lean=-a, origin=(50, 3))
    R = crystal(cx=50, top=3, bottom=98, w=20, tip=15, foot=0.01, gap=1.8, lean=a, origin=(50, 3))
    faces = [("L" + n, p) for n, p in L if not n.startswith("f")] + [("R" + n, p) for n, p in R if not n.startswith("f")]
    # where the two cross at the tip, the right crystal passes in front: drop the left one's tip facets
    faces = [x for x in faces if x[0] not in ("Ltr", "Ltf", "Rtl")]
    cols = {"*": ink, "Rtl": gold, "Rtf": gold, "Rtr": gold, "Rbl": gold, "Rbf": gold, "Rbr": gold}
    return svg(faces, cols, style, knock=KNOCK, front=("R",))
M["pair"] = ("The Pair", "Two crystals leaning in until their tips meet: an A of two, one ink and one gold. Never alone.", lambda ink=INK, gold=GOLD, style="": pair(ink, gold, style))
