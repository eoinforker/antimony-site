"""Three ways to make an exact mark lovable without changing a single line of it.
print_photo: a photograph printed in one ink on paper with heavy grain (Greatest Hits, Ricochet)
paint:       the mark painted in gouache on a painted block (Pinegrove)
thermal:     the mark glowing like a heat camera (WIRED)"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
from mark import PC
hexrgb = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255
def noise(shape, seed, blur=0):
    r = np.random.default_rng(seed); n = r.random(shape, dtype=np.float32)
    if blur: n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur)), np.float32) / 255
    return n
def streaks(shape, seed, angle=0, length=40):
    """paint drag: short smears of noise along one direction, in patches, the way a brush loads and runs dry"""
    H, W = shape; S = int(max(H, W) * 1.5)
    r = np.random.default_rng(seed)
    n = r.random((S // length + 1, S // 3 + 1)).astype(np.float32)              # long in one axis, short in the other
    im = Image.fromarray((n * 255).astype(np.uint8)).resize((S, S), Image.BICUBIC)
    patch = Image.fromarray((r.random((8, 8)) * 255).astype(np.uint8)).resize((S, S), Image.BICUBIC)
    a = (np.asarray(im, np.float32) / 255 - .5) * (np.asarray(patch, np.float32) / 255 + .3)
    im = Image.fromarray(((a - a.min()) / (np.ptp(a) + 1e-6) * 255).astype(np.uint8)).rotate(angle + 90, resample=Image.BILINEAR)
    o = (S - H) // 2, (S - W) // 2; a = np.asarray(im, np.float32)[o[0]:o[0] + H, o[1]:o[1] + W] / 255
    return (a - a.mean()) / (a.std() + 1e-6)
def mark_mask(size, pad=.14, pieces=("wing_l", "wing_r", "foot"), extra=None):
    S = size * 4; im = Image.new("L", (S, S), 0); d = ImageDraw.Draw(im); k = S * (1 - 2 * pad) / 100; o = S * pad
    for p in pieces: d.polygon([(o + x * k, o + y * k) for x, y in PC[p]], fill=255)
    return np.asarray(im.resize((size, size), Image.LANCZOS), np.float32) / 255
def rough(mask, seed, amount=2.5, scale=5):
    """push an edge about by low frequency noise, as a brush edge wanders"""
    H, W = mask.shape; nx = (noise((H, W), seed, scale) - .5) * amount * 2; ny = (noise((H, W), seed + 1, scale) - .5) * amount * 2
    yy, xx = np.mgrid[0:H, 0:W]; xs = np.clip(xx + nx * 6, 0, W - 1).astype(int); ys = np.clip(yy + ny * 6, 0, H - 1).astype(int)
    return mask[ys, xs]
def paint(size, ground="#F2C230", block="#1C2A5E", ink="#E4483B", gold="#F2C230", seed=51):
    H = W = size; out = np.ones((H, W, 3), np.float32) * hexrgb(ground)
    # the ground: thin yellow paint over paper, uneven, with drag marks
    out *= (1 + streaks((H, W), seed, 4, 60)[..., None] * .025 + (noise((H, W), seed + 2, 1.2)[..., None] - .5) * .05)
    # the block: a painted square, its edges loose, its body streaked, paper showing through in places
    bm = np.zeros((H, W), np.float32); m = int(size * .12); bm[m:H - m, m:W - m] = 1
    bm = rough(np.asarray(Image.fromarray((bm * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255, seed + 3, 1.4, 6)
    dry = np.clip((noise((H, W), seed + 4, 1.0) - .86) * 8, 0, 1) * np.clip(streaks((H, W), seed + 5, 88, 30) * .5 + .5, 0, 1)
    bcol = hexrgb(block) * (1 + streaks((H, W), seed + 6, 90, 50)[..., None] * .07)
    a = np.clip(bm - dry * .8, 0, 1)[..., None]; out = out * (1 - a) + bcol * a
    # the mark: painted in ink with a finer brush, the gold counter in the ground colour, both a little loose but exact in shape
    mm = rough(mark_mask(size, .26), seed + 7, .9, 3); gm = rough(mark_mask(size, .26, ("counter",)), seed + 8, .9, 3)
    tex = 1 + streaks((H, W), seed + 9, 0, 24)[..., None] * .06
    for msk, col in ((mm, ink), (gm, gold)):
        a = np.clip(msk * (1 - np.clip((noise((H, W), seed + 10, .8) - .93) * 10, 0, 1) * .7), 0, 1)[..., None]
        out = out * (1 - a) + hexrgb(col) * tex * a
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
def print_photo(src, size, ink="#1F3F7A", paper="#E9E4D6", seed=51, contrast=1.35, gamma=.9):
    im = Image.open(src).convert("L"); w, h = im.size; s = min(w, h); im = im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2)).resize((size, size), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255
    a = np.clip((a - .5) * contrast + .5, 0, 1) ** gamma
    g = (noise(a.shape, seed) - .5) * .42 + (noise(a.shape, seed + 1, 1.5) - .5) * .25       # film grain, coarse and fine
    t = np.clip(a + g * (1 - np.abs(a - .5) * .9), 0, 1)
    t = np.where(noise(a.shape, seed + 2) < t, 1.0, 0.0) * .55 + t * .45                        # half stochastic screen, half tone: like a cheap print
    out = hexrgb(ink) * (1 - t[..., None]) + hexrgb(paper) * t[..., None]
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
def thermal(size, seed=51):
    H = W = size; m = mark_mask(size, .2); g = mark_mask(size, .2, ("counter",))
    heat = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(size * .03)), np.float32) / 255
    heat = np.clip(heat * 1.25, 0, 1) * .85 + m * .15
    cold = np.asarray(Image.fromarray((g * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(size * .018)), np.float32) / 255
    # a heat camera's ramp: black, red, orange, yellow; the counter burns white hot inside a ring of blue
    def ramp(t):
        stops = [(0, (0.03, 0.03, 0.04)), (.35, (.55, .08, .05)), (.6, (.93, .30, .12)), (.82, (.98, .62, .25)), (1, (1, .9, .55))]
        out = np.zeros(t.shape + (3,), np.float32)
        for (a0, c0), (a1, c1) in zip(stops, stops[1:]):
            k = np.clip((t - a0) / (a1 - a0), 0, 1)[..., None]; sel = ((t >= a0) & (t <= a1))[..., None]
            out = np.where(sel, np.array(c0) * (1 - k) + np.array(c1) * k, out)
        return out
    out = ramp(np.clip(heat + (noise((H, W), seed, 2) - .5) * .06, 0, 1))
    ring = np.clip(cold * 1.6, 0, 1)[..., None]; core = np.clip((cold - .55) * 4, 0, 1)[..., None]
    out = out * (1 - ring * .85) + np.array([.3, .55, 1.]) * ring * .85
    out = out * (1 - core) + np.array([1, 1, 1.]) * core
    out = np.clip(out + (noise((H, W), seed + 3) - .5)[..., None] * .16, 0, 1)
    return Image.fromarray((out * 255).astype(np.uint8))
if __name__ == "__main__":
    O = "../balance/img/"; os.makedirs(O, exist_ok=True)
    paint(1400).save(O + "paint.webp", quality=88)
    paint(1400, ground="#F3ECDD", block="#1F3F7A", ink="#F3ECDD", gold="#F4C84A", seed=7).save(O + "paint-washi.webp", quality=88)
    thermal(1400).save(O + "thermal.webp", quality=88)
    print_photo("/tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad/stib/stibnite.png", 1400).save(O + "stibnite.webp", quality=88)
    print("ok")
def worn(size, seed=11):
    """the mark struck in dull metal on worn paper: grey, a soft sheen across it, the paper's grain through both"""
    H = W = size; base = np.ones((H, W, 3), np.float32) * hexrgb("#E6E4DE")
    fib = noise((H, W), seed, .7) - .5; blot = noise((H, W), seed + 1, size * .05) - .5
    base *= (1 + fib[..., None] * .06 + blot[..., None] * .07)
    m = mark_mask(size, .24); g = mark_mask(size, .24, ("counter",))
    yy, xx = np.mgrid[0:H, 0:W] / size
    sheen = .42 + .2 * np.sin((xx * .8 + yy * 1.4) * math.pi) + (noise((H, W), seed + 2, 3) - .5) * .08
    metal = np.stack([sheen * .86, sheen * .93, sheen], -1)
    edge = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.5)), np.float32) / 255
    rim = np.clip(m - edge, 0, 1)[..., None] * .5
    a = np.clip(m * (1 - np.clip((noise((H, W), seed + 3, .6) - .9) * 6, 0, .5)), 0, 1)[..., None]
    out = base * (1 - a) + (metal - rim * .3) * a
    ga = g[..., None]; out = out * (1 - ga) + (hexrgb("#E1B450") * (.9 + (noise((H, W), seed + 4, 1) - .5)[..., None] * .2)) * ga
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
if __name__ == "__main__":
    worn(1400).save("../balance/img/worn.webp", quality=88); print("worn")
