"""The seed principle: any plate in the archive can be redrawn out of the mark itself. Each cell of a grid holds one mark,
drawn larger where the plate is darker, so the picture appears from a crystal of small Bonds (or stars).

    python3 mosaic.py <source id> <mark: bond|star> <cols> <out.png> [ground ink|paper]
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from riso import darkness
G = json.load(open(os.path.join(os.path.dirname(__file__), "geo.json")))
INK, PAPER, COBALT, SKY = (11, 13, 12), (244, 243, 238), (36, 72, 255), (148, 230, 255)
def bond_polys(cx, cy, s):
    """the Bond as polygons, centred on (cx, cy), s px across its 100 unit square"""
    k = s / 100; A = G["atoms"]; R = G["R"] * k; W = G["W"] * k / 2
    P = {n: (cx + (x - 50) * k, cy + (y - 50) * k) for n, (x, y) in A.items()}
    out = []
    for a, b in G["bonds"]:
        (x1, y1), (x2, y2) = P[a], P[b]
        out.append(("ink", [(x1 - W, y1), (x1 + W, y1), (x2 + W, y2), (x2 - W, y2)] if x1 == x2 else [(x1, y1 - W), (x2, y2 - W), (x2, y2 + W), (x1, y1 + W)]))
    for n, (x, y) in P.items():
        out.append(("nuc" if n == "nucleus" else "ink", [(x, y - R), (x + R, y), (x, y + R), (x - R, y)]))
    return out
def star_polys(cx, cy, s):
    out = []; L = s * .48; w = s * .07
    for k in range(4):
        a = math.radians(45 * k); dx, dy = math.cos(a) * L, math.sin(a) * L; nx, ny = -math.sin(a) * w, math.cos(a) * w
        out.append(("ink", [(cx - dx + nx, cy - dy + ny), (cx + dx + nx, cy + dy + ny), (cx + dx - nx, cy + dy - ny), (cx - dx - nx, cy - dy - ny)]))
    out.append(("nuc", [(cx - w * 1.2, cy - w * 1.2), (cx + w * 1.2, cy - w * 1.2), (cx + w * 1.2, cy + w * 1.2), (cx - w * 1.2, cy + w * 1.2)]))
    return out
def render(src, mark="bond", cols=64, ground="ink", width=2400, steps=(0, .3, .5, .68, .84, 1.0)):
    d = darkness(Image.open(src), long=1600)
    from PIL import ImageFilter
    d = np.asarray(Image.fromarray((d * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(d.shape[1] / cols * .6)), dtype=np.float32) / 255  # hatching becomes tone
    H, W = d.shape; cell = W / cols; rows = int(H / cell)
    scale = 3; cw = width * scale; ch = int(cw * rows / cols); c = cw / cols
    bg, fg, nc = (INK, SKY, PAPER) if ground == "ink" else (PAPER, INK, COBALT)
    im = Image.new("RGB", (cw, ch), bg); dr = ImageDraw.Draw(im)
    polys = bond_polys if mark == "bond" else star_polys
    V = np.array([[d[int(j * cell):int((j + 1) * cell), int(i * cell):int((i + 1) * cell)].mean() for i in range(cols)] for j in range(rows)])
    if ground == "ink": V = V.max() - V                      # on ink the picture reads as a positive: its light becomes our light
    lo, hi = np.percentile(V, 4), np.percentile(V, 96)       # the hatching of an engraving is even; stretch it until the forms read
    V = np.clip((V - lo) / (hi - lo + 1e-6), 0, 1) ** 1.25
    for j in range(rows):
        for i in range(cols):
            v = V[j, i]
            q = min(steps, key=lambda s: abs(s - v))          # sizes come in six steps, like type sizes, never a smear
            if q <= 0: continue
            s = c * (.32 + .78 * q)
            for kind, p in polys(i * c + c / 2, j * c + c / 2, s):
                dr.polygon(p, fill=(nc if (kind == "nuc" and q >= .84) else fg))
    return im.resize((width, int(width * rows / cols)), Image.LANCZOS)
if __name__ == "__main__":
    sid, mark, cols, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    ground = sys.argv[5] if len(sys.argv) > 5 else "ink"
    render(os.path.join(os.path.dirname(__file__), "..", "art", "source", sid + ".jpg"), mark, cols, ground).save(out)
    print(out)
