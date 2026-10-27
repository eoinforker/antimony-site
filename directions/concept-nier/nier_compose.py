# Concept Nier: composes the graded still, the phone crop and the seamless loop from the EXR of nier_meadow.py.
# Runs inside Blender's Python for its numpy, OpenImageIO and OpenColorIO (so the view transform is Blender's own AgX):
#   blender -b --factory-startup -P nier_compose.py -- --exr <prefix_>0001.exr --mark <prefix_>mark.json --mode still --out still.png
#   blender -b --factory-startup -P nier_compose.py -- --exr ... --mark ... --mode loop --out frames/f_%04d.png --res 1920
# --phone <path> also writes the 9:16 crop centred on the mark (for the still, or %04d frames for the loop).
# Light adds linearly, so the haze drift, the crystal and the bloom are done in scene-linear light, then AgX once,
# then a gentle display grade (pastel lifted blacks, warm highlights, lens, grain).
# The loop is 6 s at 24 fps; every motion repeats on a period that divides it, so the last frame runs into the first.
# Nothing moves on the mark: the stone and the crystal are masked out of every warp, and no mote crosses them.
import sys, os, math, json
import numpy as np
import OpenImageIO as oiio
import PyOpenColorIO as ocio

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    k = '--' + name
    return type(default)(argv[argv.index(k) + 1]) if k in argv else default
EXR = arg('exr', ''); MODE = arg('mode', 'still'); OUT = arg('out', 'out.png'); RES = arg('res', 0)
PHONE = arg('phone', ''); MARK = json.load(open(arg('mark', '')))
EXPO = arg('exposure', 0.0); FPS = 24; T = arg('seconds', 6.0); NF = int(FPS * T)
F0, F1 = arg('f0', 0), arg('f1', NF)
rng = np.random.default_rng(9)

# ---------------------------------------------------------------- load
inp = oiio.ImageInput.open(EXR); spec = inp.spec(); names = list(spec.channelnames)
px = np.asarray(inp.read_image(0, 0, 0, len(names), 'float'), np.float32).reshape(spec.height, spec.width, len(names)); inp.close()
def ch(n):
    for i, c in enumerate(names):
        if c == n or c.endswith('.' + n) or c.endswith(n): return px[:, :, i]
    raise KeyError(n + ' not in ' + str(names))
Lsrc = np.stack([ch('rgb.R'), ch('rgb.G'), ch('rgb.B')], -1)
D = {'Depth': ch('Depth.V'), 'pl': ch('pl.V'), 'mk': ch('mk.V'), 'cr': ch('cr.V')}
del px
D['Depth'] = np.where(np.isfinite(D['Depth']), D['Depth'], 1e9)
# Cycles writes the depth of the first scatter in the haze, so the raw pass has outliers both ways: a 5 by 5
# median recovers the surfaces (the haze itself is real, in the render; depth here only scales the wind and the drift)
def median5(a):
    st = np.stack([np.roll(np.roll(a, dy, 0), dx, 1) for dy in range(-2, 3) for dx in range(-2, 3)], 0)
    return np.median(st, axis=0).astype(np.float32)
D['Depth'] = median5(np.minimum(D['Depth'], 1e5))

def resize(a, w, h):
    sh = a.shape; c = 1 if a.ndim == 2 else sh[2]
    b = oiio.ImageBuf(oiio.ImageSpec(sh[1], sh[0], c, 'float')); b.set_pixels(oiio.ROI(), np.ascontiguousarray(a.reshape(sh[0], sh[1], c)))
    r = oiio.ImageBufAlgo.resize(b, roi=oiio.ROI(0, w, 0, h, 0, 1, 0, c))
    o = np.asarray(r.get_pixels(oiio.FLOAT)).reshape(h, w, c)
    return o[:, :, 0] if a.ndim == 2 else o
if RES and RES != spec.width:
    w = RES; h = int(round(spec.height * RES / spec.width))
    Lsrc = resize(Lsrc, w, h)
    D = {k: (resize(np.minimum(v, 1e5), w, h) if k == 'Depth' else resize(v, w, h)) for k, v in D.items()}
H, W = Lsrc.shape[:2]
S = W / 2560.0
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

# ---------------------------------------------------------------- helpers (as in Rain)
def box1(a, r, axis):
    if r < 1: return a
    c = np.cumsum(a, axis=axis, dtype=np.float32)
    pad = [(0, 0)] * a.ndim; pad[axis] = (r + 1, r); c = np.pad(c, pad, mode='edge')
    hi = [slice(None)] * a.ndim; lo = [slice(None)] * a.ndim; n = a.shape[axis]
    hi[axis] = slice(2 * r + 1, 2 * r + 1 + n); lo[axis] = slice(0, n)
    return (c[tuple(hi)] - c[tuple(lo)]) / (2 * r + 1)
def blur(a, r):
    for _ in range(3): a = box1(box1(a, r, 0), r, 1)
    return a
def down(a, k):
    h, w = a.shape[0] // k * k, a.shape[1] // k * k
    return a[:h, :w].reshape(h // k, k, w // k, k, *a.shape[2:]).mean(axis=(1, 3))
def up(a, h, w): return resize(a, w, h)
def sample(img, x, y):
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = x.astype(np.int32); y0 = y.astype(np.int32); fx = (x - x0); fy = (y - y0)
    if img.ndim == 3: fx = fx[..., None]; fy = fy[..., None]
    a = img[y0, x0]; b = img[y0, x0 + 1]; c = img[y0 + 1, x0]; d = img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
def smooth(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

# ---------------------------------------------------------------- view transform: Blender's AgX
cfg = ocio.GetCurrentConfig()
dvt = ocio.DisplayViewTransform(src='Linear Rec.709', display='sRGB', view='AgX')
vp = ocio.LegacyViewingPipeline(); vp.setDisplayViewTransform(dvt)
if arg('look', 'base'):
    vp.setLooksOverrideEnabled(True); vp.setLooksOverride({'base': 'AgX - Base Contrast', 'punchy': 'AgX - Punchy'}.get(arg('look', 'base'), arg('look', 'base')))
CPU = vp.getProcessor(cfg).getDefaultCPUProcessor()
def view(lin):
    a = np.ascontiguousarray(np.clip(lin * (2 ** EXPO), 0, 1e4).astype(np.float32)); CPU.applyRGB(a); return np.clip(a, 0, 1)

# ---------------------------------------------------------------- static fields
depth = D['Depth']; sky = depth > 5e3
mk = np.clip(D['mk'], 0, 1); cr = np.clip(D['cr'], 0, 1)
mkd = np.clip(blur(mk, max(1, int(3 * S))) * 4, 0, 1)                   # the mark plus a hair of margin
pl = np.clip(D['pl'], 0, 1) * (1 - mkd)
plb = blur(pl, max(1, int(2 * S)))
# aerial perspective: the haze colour is the sky's own, just above the horizon
band = sky[int(H * 0.45):int(H * 0.62)]
hz = Lsrc[int(H * 0.45):int(H * 0.62)][band].mean(0) if band.any() else np.array([0.8, 0.85, 0.9], np.float32)
HAZE = (hz * arg('haze-level', 0.97)).astype(np.float32)
fog0 = np.where(sky, 0.0, arg('fog', 0.0) * (1 - np.exp(-np.maximum(depth - 40, 0) / arg('fog-k', 520.0)))).astype(np.float32)
# the drift field for the haze: two soft noises that slide through one period each
def noise_field(cell, seed):
    g = np.random.default_rng(seed).uniform(0, 1, (H // cell + 3, W // cell + 3)).astype(np.float32)
    g = blur(g, 1); g = (g - g.min()) / (np.ptp(g) + 1e-6); return up(g, H + 3 * cell, W + 3 * cell)
NZ1 = noise_field(int(160 * S) + 8, 3); NZ2 = noise_field(int(90 * S) + 8, 4)
def drift(t):
    a = 2 * math.pi * t / T
    ox1 = 60 * S * math.cos(a); oy1 = 30 * S * math.sin(a)
    ox2 = -70 * S * math.cos(a + 1.3); oy2 = 20 * S * math.sin(2 * a)
    n1 = NZ1[int(80 * S + oy1 + 40 * S):int(80 * S + oy1 + 40 * S) + H, int(100 * S + ox1 + 80 * S):int(100 * S + ox1 + 80 * S) + W]
    n2 = NZ2[int(40 * S + oy2 + 30 * S):int(40 * S + oy2 + 30 * S) + H, int(60 * S + ox2 + 90 * S):int(60 * S + ox2 + 90 * S) + W]
    return (n1[:H, :W] * 0.6 + n2[:H, :W] * 0.4) - 0.5
# wind in the grass: a gust that travels left to right, nearer blades move further on screen
gst = noise_field(int(120 * S) + 8, 7)[:H, :W] * 2 * math.pi
ph1 = gst + xx / W * 2 * math.pi * 1.5
ph2 = noise_field(int(50 * S) + 8, 8)[:H, :W] * 2 * math.pi * 2
near = np.clip(14.0 / np.maximum(depth, 0.5), 0.15, 5.0)
sway = plb * near * S * arg('sway', 2.2)
# crystal: hold it to sky #94E6FF in linear light, keeping its own light and shade
SKY = np.array([((c / 255 + 0.055) / 1.055) ** 2.4 for c in (0x94, 0xE6, 0xFF)], np.float32)
LUMW = np.array([0.2126, 0.7152, 0.0722], np.float32)
def hold_crystal(L):
    y = (L @ LUMW)[..., None]; tgt = SKY * y / float(SKY @ LUMW)
    k = (cr * arg('crystal-hold', 0.65))[..., None]
    return L * (1 - k) + tgt * k

# seeds in the warm air: dandelion fluff hanging and turning, on closed paths of one period each
MB = (MARK['u0'] * W - 30 * S, MARK['u1'] * W + 30 * S, MARK['v0'] * H - 30 * S, MARK['v1'] * H + 30 * S)
NS = int(arg('seeds', 46))
SX = rng.uniform(0.02, 0.98, NS) * W; SY = rng.uniform(0.25, 0.9, NS) * H
SR = np.where(rng.uniform(0, 1, NS) < 0.15, rng.uniform(7, 14, NS), rng.uniform(1.2, 2.6, NS)) * S * 1.6
SA = rng.uniform(60, 180, NS) * S; SB = rng.uniform(15, 45, NS) * S; SPH = rng.uniform(0, 2 * math.pi, NS)
SK = rng.integers(1, 3, NS)
def seeds(t, L):
    acc = np.zeros((H, W), np.float32)
    a = 2 * math.pi * t / T
    for i in range(NS):
        x = SX[i] + SA[i] * math.sin(a * SK[i] + SPH[i]); y = SY[i] + SB[i] * math.sin(a * SK[i] * 2 + SPH[i] * 1.7) - SB[i] * 0.5
        if MB[0] < x < MB[1] and MB[2] < y < MB[3]: continue
        fade = 0.5 - 0.5 * math.cos(a * SK[i] + SPH[i] * 0.5)           # each seed drifts in and out of the light
        r = SR[i]; x0, x1 = int(max(0, x - 3 * r)), int(min(W, x + 3 * r + 1)); y0, y1 = int(max(0, y - 3 * r)), int(min(H, y + 3 * r + 1))
        if x1 <= x0 or y1 <= y0: continue
        d2 = ((xx[y0:y1, x0:x1] - x) ** 2 + (yy[y0:y1, x0:x1] - y) ** 2) / (r * r)
        prof = np.exp(-d2 * 1.6) if r < 6 * S else np.clip(1.2 - d2 ** 3, 0, 1) * 0.18
        acc[y0:y1, x0:x1] += prof * fade
    return acc[..., None] * np.array([1.0, 0.93, 0.8], np.float32) * arg('seed-k', 0.55)

# ---------------------------------------------------------------- finishing
vig = 1 - 0.18 * np.clip(((xx / W - 0.5) ** 2 * 1.2 + (yy / H - 0.5) ** 2 * 1.0) * 2.4 - 0.12, 0, 1) ** 1.4
def bloom(L):
    hi = np.maximum(L - arg('bloom-th', 0.9), 0); b = np.zeros_like(L); h = hi
    for i, wgt in enumerate((0.5, 0.35, 0.25, 0.18)):
        h = down(h, 2) if i else down(h, 4); b += up(blur(h, 2), H, W) * wgt
    return L + b * np.array([1.2, 1.0, 0.82], np.float32) * arg('bloom', 0.09)
def grade(img, grain=0.0):
    lift = np.array([float(v) for v in arg('lift-col', '0.06,0.066,0.08').split(',')], np.float32) * arg('lift', 1.0)        # pale pastel blacks
    out = lift + img * (1 - lift)
    lum = (out @ LUMW)[..., None]
    out = lum + (out - lum) * arg('sat', 1.0)
    out = out * (1 + (np.array([1.03, 1.0, 0.955], np.float32) - 1) * arg('warm', 1.0) * smooth(0.5, 1.0, lum))   # warm highlights
    out = out * vig[..., None]
    ca = arg('ca', 0.7) * S
    rx = (xx - W / 2) / (W / 2); ry = (yy - H / 2) / (W / 2)
    out[..., 0] = sample(out[..., 0], xx + rx * ca, yy + ry * ca)
    out[..., 2] = sample(out[..., 2], xx - rx * ca, yy - ry * ca)
    if grain:
        g = rng.normal(0, grain, (H, W)).astype(np.float32); g = g + blur(g, 1) * 0.5
        out = out + g[..., None] * (0.4 + 0.6 * (1 - out))
    return np.clip(out, 0, 1)

def frame(t, motion=True):
    L = Lsrc
    f = fog0
    if motion:
        dx = sway * (np.sin(2 * math.pi * t / T * 2 + ph1) * 0.7 + np.sin(2 * math.pi * t / T * 3 + ph2) * 0.3)
        dy = sway * 0.25 * np.sin(2 * math.pi * t / T * 3 + ph1 * 0.7)
        Lw = sample(L, xx - dx, yy - dy)
        took_mark = sample(mkd, xx - dx, yy - dy) > 0.02
        L = np.where((took_mark | (mkd > 0.02))[..., None], L, Lw)
        f = np.clip(f + arg('drift', 1.0) * 0.07 * (drift(t) + 0.5) * smooth(80, 400, depth) * (1 - mkd), 0, 0.95)
    L = L * (1 - f[..., None]) + HAZE * f[..., None]
    L = hold_crystal(L)
    if motion or arg('seeds-still', 1): L = L + seeds(t, L)
    return bloom(L)

def save(path, img):
    o = np.clip((img * 255 + rng.uniform(-0.5, 0.5, img.shape)).round(), 0, 255).astype(np.uint8)
    h, w = o.shape[:2]
    out = oiio.ImageOutput.create(path); out.open(path, oiio.ImageSpec(w, h, 3, oiio.UINT8)); out.write_image(o); out.close()
def phone_crop(img):
    cw = int(round(H * 9 / 16)) // 2 * 2
    cx = (MARK['u0'] + MARK['u1']) / 2 * W
    x0 = int(np.clip(cx - cw / 2, 0, W - cw))
    return img[:, x0:x0 + cw]

if MODE == 'still':
    img = grade(view(frame(0.0, motion=False)), grain=arg('grain', 0.011))
    save(OUT, img)
    if PHONE: save(PHONE, phone_crop(img))
    print('WROTE', OUT)
elif MODE == 'loop':
    import time
    for f_ in range(F0, F1):
        t0 = time.time()
        img = grade(view(frame(f_ / FPS)), grain=arg('grain', 0.009))
        save(OUT % (f_ + 1), img)
        if PHONE: save(PHONE % (f_ + 1), phone_crop(img))
        print('frame', f_ + 1, round(time.time() - t0, 2), flush=True)
