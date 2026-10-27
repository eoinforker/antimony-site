# The finish for poster_hero.py renders: the crystal held to sky blue #94E6FF (mapped from the print through the
# print's four corners), a breath of halation on the print and highlights, slight chromatic aberration at the
# edges, a gentle vignette, fine grain, and an optional nearest-neighbour upscale (the quick first frames).
#
#   python3 -I hero_post.py raw.png raw.png.json out.png [--up 4] [--grain 0.012] [--hold 0.85]

import json, os, sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
def arg(k, d):
    return type(d)(a[a.index(k) + 1]) if k in a else d
RAW, JS, OUT = a[0], a[1], a[2]
UP = arg('--up', 1); GRAIN = arg('--grain', 0.012); HOLD = arg('--hold', 0.85); SEED = arg('--seed', 3)
info = json.load(open(JS))
img = np.asarray(Image.open(RAW).convert('RGB'), np.float32) / 255.0
Hh, Ww = img.shape[:2]

def homography(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u]); A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.array(A)); h = vt[-1].reshape(3, 3); return h / h[2, 2]

# ---------------------------------------------------------------- the crystal held to sky
gem_p = os.path.join(os.path.dirname(info.get('print_json', os.path.join(HERE, 'assets', 'hero-print.json'))), 'gem.png')
if HOLD > 0 and os.path.exists(gem_p):
    c = info['corners']
    dst = [c['top_left'], c['top_right'], c['bottom_right'], c['bottom_left']]
    Hm = homography(dst, [(0, 0), (1, 0), (1, 1), (0, 1)])          # pixel to sheet
    gem = np.asarray(Image.open(gem_p).convert('L'), np.float32) / 255.0; gh, gw = gem.shape
    ss = 3
    ys, xs = np.mgrid[0:Hh * ss, 0:Ww * ss]; xs = (xs + 0.5) / ss; ys = (ys + 0.5) / ss
    q = Hm @ np.stack([xs.ravel(), ys.ravel(), np.ones(xs.size)])
    u, v = q[0] / q[2], q[1] / q[2]
    inside = (u >= 0) & (u < 1) & (v >= 0) & (v < 1)
    m = np.zeros(u.size, np.float32)
    m[inside] = gem[(v[inside] * gh).astype(int), (u[inside] * gw).astype(int)]
    m = m.reshape(Hh, ss, Ww, ss).mean((1, 3))[..., None]
    sky = np.array([0x94, 0xE6, 0xFF]) / 255.0
    lum = (img * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True)
    ref = np.median(lum[m[..., 0] > 0.6]) if (m > 0.6).any() else 0.7
    held = np.clip(sky * (0.85 + 0.15 * lum / max(ref, 1e-3)), 0, 1)
    img = img * (1 - m * HOLD) + held * m * HOLD

# ---------------------------------------------------------------- halation, chromatic aberration, vignette, grain
lum = (img * [0.2126, 0.7152, 0.0722]).sum(-1)
hi = np.clip((lum - 0.72) / 0.28, 0, 1)[..., None] * img
r = max(2, int(Ww * 0.012))
glow = np.asarray(Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0
img = 1 - (1 - img) * (1 - glow * np.array([0.30, 0.42, 0.62]))
yy, xx = np.mgrid[0:Hh, 0:Ww]; cx, cy = (Ww - 1) / 2, (Hh - 1) / 2
dx, dy = (xx - cx) / cx, (yy - cy) / cy; rr = np.sqrt(dx * dx + dy * dy)
k = 0.0016 * Ww
def shift(ch, s):
    sx = np.clip(np.rint(xx + dx * s * rr), 0, Ww - 1).astype(int); sy = np.clip(np.rint(yy + dy * s * rr * cy / cx), 0, Hh - 1).astype(int)
    return ch[sy, sx]
img = np.stack([shift(img[..., 0], k), img[..., 1], shift(img[..., 2], -k)], -1)
vig = 1 - 0.32 * np.clip(rr / 1.35, 0, 1) ** 2.2
img = img * vig[..., None]
g = np.random.default_rng(SEED).normal(0, GRAIN, (Hh, Ww, 1))
img = np.clip(img + g * (0.4 + 0.6 * np.sqrt(np.clip(img, 0, 1))), 0, 1)
out = Image.fromarray((img * 255 + 0.5).astype(np.uint8))
if UP > 1: out = out.resize((Ww * UP, Hh * UP), Image.NEAREST)
out.save(OUT)
print('POST', OUT, out.size)
