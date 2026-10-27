# The cobalt print for the hero lightbox: the Blue Field at night, misted, with the Break mark drawn from its
# exact geometry, the ANTIMONY wordmark (from its own outlines) and "SOFTWARE, MADE ON PURPOSE." at the foot.
#
#   python3 -I hero_print.py --out print.png [--still ../w11-blue-field/assets/still.webp] [--w 1400]
#
# Writes print.png (2 by 3, the 1.16 by 1.74 sheet) and print.json: the crystal and the whole mark as boxes in
# the sheet's own 0 to 1 coordinates (u right, v down), and gem.png, the crystal's mask, for the colour hold.

import json, os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
SCR = '/tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad'
argv = sys.argv[1:]
def arg(k, d):
    return argv[argv.index(k) + 1] if k in argv else d

OUT = arg('--out', os.path.join(HERE, 'print.png'))
STILL = arg('--still', os.path.join(ROOT, 'w11-blue-field', 'assets', 'still.webp'))
FONT = arg('--font', os.path.join(ROOT, 'poster', 'assets', 'fonts', 'TimelessSerifVF.woff2'))
WORD = arg('--wordmark', os.path.join(SCR, 'refs-founder', 'wordmarks', 'antimony-wordmark-caps-ink.svg'))
W = int(arg('--w', '1400')); H = W * 3 // 2

SEAM = "M67.46 -12L68.96 -12L62.35 21.5L45.15 81.5L33.4 112L31.9 112L37.65 81.5L54.85 21.5Z"
CAV = "M60.75 14.02L78.19 42.8L73.21 60.2L39.25 88.97L21.81 60.2L26.79 42.8Z"
GEM = "M58.6 21.5L70.58 46.7L67.82 56.3L41.4 81.5L29.42 56.3L32.18 46.7Z"
FACET = "M58.6 21.5L70.58 46.7L67.82 56.3L41.4 81.5Z"
SKY = np.array([0x94, 0xE6, 0xFF]) / 255.0
INK = np.array([0x0B, 0x0C, 0x0C]) / 255.0
PAPER = np.array([0xEE, 0xEA, 0xE0]) / 255.0

def poly(d):
    v = list(map(float, d.replace('M', ' ').replace('L', ' ').replace('Z', ' ').split()))
    return np.array(v).reshape(-1, 2)

def lin(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def srgb(c): c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)

def mask_polys(polys, size, ss=4):
    """even-odd fill of several polygons (lists of (x, y) in pixels) at ss times supersampling"""
    w, h = size; acc = np.zeros((h * ss, w * ss), bool)
    for p in polys:
        im = Image.new('1', (w * ss, h * ss), 0)
        ImageDraw.Draw(im).polygon([(x * ss, y * ss) for x, y in p], fill=1)
        acc ^= np.array(im)
    return acc.reshape(h, ss, w, ss).mean((1, 3))

def svg_subpaths(path_d, steps=10):
    """absolute M L H V Q Z only, as the wordmark uses; returns a list of polygons"""
    toks = re.findall(r'[MLHVQZ]|-?\d*\.?\d+(?:e-?\d+)?', path_d)
    out, cur, i, cmd, p = [], [], 0, None, (0.0, 0.0)
    def num():
        nonlocal i; i += 1; return float(toks[i - 1])
    while i < len(toks):
        t = toks[i]
        if t in 'MLHVQZ': cmd = t; i += 1
        if cmd == 'Z':
            if cur: out.append(cur)
            cur = []; continue
        if cmd == 'M':
            if cur: out.append(cur)
            p = (num(), num()); cur = [p]; cmd = 'L'
        elif cmd == 'L': p = (num(), num()); cur.append(p)
        elif cmd == 'H': p = (num(), p[1]); cur.append(p)
        elif cmd == 'V': p = (p[0], num()); cur.append(p)
        elif cmd == 'Q':
            c = (num(), num()); e = (num(), num())
            for k in range(1, steps + 1):
                s = k / steps
                cur.append(((1 - s) ** 2 * p[0] + 2 * (1 - s) * s * c[0] + s * s * e[0], (1 - s) ** 2 * p[1] + 2 * (1 - s) * s * c[1] + s * s * e[1]))
            p = e
    if cur: out.append(cur)
    return out

# ---------------------------------------------------------------- the image: the Blue Field, misted
src = Image.open(STILL).convert('RGB')
sw, sh = src.size
cw = int(sh * 2 / 3); cx0 = int(sw * 0.52)
crop = src.crop((cx0, 0, cx0 + cw, sh)).resize((W, H), Image.LANCZOS)
a = lin(np.asarray(crop, np.float32) / 255.0)
yy = (np.arange(H) / H)[:, None, None]
# mist: the upper two thirds settle into a soft pale cobalt haze, so the spires stand as ghosts behind the mark
mist_col = lin(np.array([0.70, 0.79, 0.93]))
fog = np.clip(1.0 - (yy - 0.42) / 0.30, 0, 1) ** 1.2 * 0.78 + 0.08
a = a * (1 - fog) + mist_col * fog
# a breath of deeper cobalt at the very top, and the field kept rich at the foot
top = np.clip(1 - yy / 0.22, 0, 1) ** 2
a = a * (1 - 0.35 * top) + lin(np.array([0.36, 0.48, 0.80])) * 0.35 * top
lum = (a * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True)
cob = lin(np.array([0x24, 0x48, 0xFF]) / 255.0)
a = a * 0.86 + lum * (cob / cob.mean()) * 0.14 * 0.6 + lum * 0.14 * 0.4
img = srgb(a)

# ---------------------------------------------------------------- the Break mark, exact geometry
MS = W * 0.30; mx0 = (W - MS) / 2; my0 = H * 0.215
def tp(P): return [(mx0 + x * MS / 100.0, my0 + y * MS / 100.0) for x, y in P]
bw, bh = int(MS) + 8, int(MS) + 8; ox, oy = int(mx0) - 4, int(my0) - 4
ss = 6
ys = oy + (np.arange(bh * ss) + 0.5) / ss; xs = ox + (np.arange(bw * ss) + 0.5) / ss
X, Y = np.meshgrid(xs, ys); ux, uy = (X - mx0) / MS * 100, (Y - my0) / MS * 100
qx, qy = np.abs(ux - 50) - 28, np.abs(uy - 50) - 28
sd = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - 22
def pin(px, py, P):
    ins = np.zeros(px.shape, bool); n = len(P)
    for i in range(n):
        x1, y1 = P[i]; x2, y2 = P[(i + 1) % n]
        ins ^= ((y1 > py) != (y2 > py)) & (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-12) + x1)
    return ins
stone = (sd < 0) & ~pin(ux, uy, poly(SEAM)) & ~pin(ux, uy, poly(CAV))
gem = pin(ux, uy, poly(GEM)); fac = pin(ux, uy, poly(FACET))
def down(m): return m.astype(np.float32).reshape(bh, ss, bw, ss).mean((1, 3))[..., None]
st, gm, fc = down(stone), down(gem), down(fac)
reg = img[oy:oy + bh, ox:ox + bw]
stone_c = np.array([0x10, 0x13, 0x1A]) / 255.0
reg = reg * (1 - st) + stone_c * st
gem_c = SKY * (1 - 0.0 * fc) + (1 - SKY) * 0.22 * fc      # the lit facet a touch paler, the crystal held to sky
reg = reg * (1 - gm) + gem_c * gm
img[oy:oy + bh, ox:ox + bw] = reg
gem_full = np.zeros((H, W), np.float32); gem_full[oy:oy + bh, ox:ox + bw] = gm[..., 0]

# ---------------------------------------------------------------- the wordmark, from its own outlines
svg = open(WORD).read()
vb = list(map(float, re.search(r'viewBox="([^"]+)"', svg).group(1).split()))
polys = []
for d in re.findall(r'<path d="([^"]+)"', svg): polys += svg_subpaths(d)
ww = W * 0.40; sc = ww / vb[2]; wy = H * 0.565
wx0 = (W - ww) / 2
pp = [[(wx0 + (x - vb[0]) * sc, wy + (y - vb[1]) * sc) for x, y in p] for p in polys]
wm = mask_polys(pp, (W, H), 4)[..., None]
img = img * (1 - wm) + INK * 1.6 * wm

# ---------------------------------------------------------------- the line at the foot
font = ImageFont.truetype(FONT, int(W * 0.024))
try: font.set_variation_by_name('Text Regular')
except Exception: pass
line = 'SOFTWARE, MADE ON PURPOSE.'
track = W * 0.024 * 0.32
widths = [font.getlength(ch) for ch in line]
tw = sum(widths) + track * (len(line) - 1)
lay = Image.new('L', (W * 2, H * 2), 0); dr = ImageDraw.Draw(lay)
f2 = ImageFont.truetype(FONT, int(W * 0.024) * 2)
try: f2.set_variation_by_name('Text Regular')
except Exception: pass
x = (W - tw); yb = H * 0.905 * 2
for ch, w_ in zip(line, widths):
    dr.text((x, yb), ch, font=f2, fill=255, anchor='ls'); x += (w_ + track) * 2
tm = np.asarray(lay.resize((W, H), Image.LANCZOS), np.float32)[..., None] / 255.0
img = img * (1 - tm) + PAPER * tm

out = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
out.save(OUT)
Image.fromarray((gem_full * 255).astype(np.uint8)).save(os.path.join(os.path.dirname(OUT), 'gem.png'))
gy, gx = np.nonzero(gem_full > 0.5)
info = {'w': W, 'h': H,
        'mark': [mx0 / W, my0 / H, (mx0 + MS) / W, (my0 + MS) / H],
        'gem': [gx.min() / W, gy.min() / H, (gx.max() + 1) / W, (gy.max() + 1) / H]}
json.dump(info, open(os.path.splitext(OUT)[0] + '.json', 'w'), indent=1)
print('PRINT', OUT, info)
