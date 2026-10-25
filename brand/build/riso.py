"""The archive treatment. Every plate is printed as if on a two-drum risograph: an ink drum for the line and a cobalt drum
for the tone, on paper, with the drums a hair out of register and the grain of a real print.

    python3 riso.py            # every source plate, every variant, into ../art/riso
Variants: two (ink and cobalt on paper), ink (ink on paper), cobalt (cobalt on paper), night (paper and sky on ink).
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ART = os.path.join(HERE, "..", "art")
hexrgb = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32) / 255
INK, PAPER, COBALT, SKY = map(hexrgb, ("#0B0D0C", "#F4F3EE", "#2448FF", "#94E6FF"))
def smooth(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def darkness(im, long=1600):
    g = im.convert("L"); g.thumbnail((long, long), Image.LANCZOS)
    a = np.asarray(g, dtype=np.float32) / 255
    lo, hi = np.percentile(a, 3), np.percentile(a, 88)            # the old paper becomes our paper; its ink, our ink
    d = 1 - np.clip((a - lo) / (hi - lo + 1e-6), 0, 1)
    return trim(d)
def trim(d, t=.55):
    """cut away the dark margins of the scan (the book's edge, the photographer's card) so only the plate remains"""
    rows = d.mean(1); cols = d.mean(0)
    def edge(v):
        a, b = 0, len(v) - 1
        while a < len(v) // 4 and v[a] > t: a += 1
        while b > len(v) * 3 // 4 and v[b] > t: b -= 1
        return a, b
    (r0, r1), (c0, c1) = edge(rows), edge(cols)
    pad = 6
    return d[min(r0 + pad, r1):r1 - pad, min(c0 + pad, c1):c1 - pad]
def grain(shape, seed, scale=1.0):
    r = np.random.default_rng(seed)
    n = r.random(shape, dtype=np.float32)
    coarse = np.asarray(Image.fromarray((r.random((shape[0] // 3 + 1, shape[1] // 3 + 1)) * 255).astype(np.uint8)).resize((shape[1], shape[0]), Image.BILINEAR), dtype=np.float32) / 255
    return (n * .55 + coarse * .45) * scale
def drum(density, seed, amount=.38):
    """a drum lays ink stochastically: denser where the plate is darker, with the speckle of a stencil print"""
    g = grain(density.shape, seed)
    return np.clip(density * (1 + amount) - g * amount, 0, 1)
def shift(a, dx, dy): return np.roll(np.roll(a, dy, 0), dx, 1)
def lay(base, colour, a):  # subtractive: each drum multiplies the paper beneath it
    return base * (1 - a[..., None] + a[..., None] * (colour / np.maximum(base, 1e-3)).clip(0, 1.2))
def render(d, variant, seed=51):
    H, W = d.shape
    line = smooth(.42, .82, d)              # the engraved line: only the darkest marks
    tone = smooth(.30, .72, d) * .55        # the tone: dense hatching only, kept light
    if variant == "night":
        base = np.ones((H, W, 3), np.float32) * INK
        t = drum(tone, seed + 1, .5)[..., None] * .35
        out = base * (1 - t) + COBALT * t
        a = drum(line, seed)[..., None]; out = out * (1 - a) + PAPER * a
        return out
    base = np.ones((H, W, 3), np.float32) * PAPER
    if variant in ("two", "cobalt"):
        plate = tone if variant == "two" else smooth(.3, .78, d)
        base = lay(base, COBALT, shift(drum(plate, seed + 1) * (.85 if variant == "two" else .95), 2, 1))
    if variant in ("two", "ink"):
        base = lay(base, INK, drum(line if variant == "two" else np.maximum(line, tone * .5), seed))
    # paper tooth: a faint unevenness so the ground never reads as a flat screen colour
    tooth = (grain((H, W), seed + 9) - .5) * .025
    return np.clip(base + tooth[..., None], 0, 1)
def save(a, path, q=82): Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(path, "WEBP", quality=q, method=6)
if __name__ == "__main__":
    src = json.load(open(os.path.join(ART, "sources.json")))
    only = set(sys.argv[1:]); variants = ("two", "ink", "cobalt", "night")
    for s in src:
        if only and s["id"] not in only: continue
        d = darkness(Image.open(os.path.join(ART, "source", s["id"] + ".jpg")))
        for v in variants: save(render(d, v), os.path.join(ART, "riso", f"{s['id']}-{v}.webp"))
        print(s["id"])
