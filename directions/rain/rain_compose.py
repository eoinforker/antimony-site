# Rain: composes the final still and the seamless loop from the light-group EXR of rain_scene.py.
# Runs inside Blender's Python for its numpy, OpenImageIO and OpenColorIO (so the view transform is Blender's own AgX):
#   blender -b --factory-startup -P rain_compose.py -- --exr passes_0001.exr --mode still --out still.png
#   blender -b --factory-startup -P rain_compose.py -- --exr passes_0001.exr --mode loop --out frames/f_%04d.png --res 1920
#   blender -b --factory-startup -P rain_compose.py -- --exr passes_0001.exr --mode spill --out spill.png --res 1920
# Light adds linearly, so everything is built in scene-linear light and taken through AgX once, at the end.
# The loop is 6 s at 24 fps; every motion repeats on a period that divides it, so the last frame runs into the first.
import sys, os, math
import numpy as np
import OpenImageIO as oiio
import PyOpenColorIO as ocio

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    k = '--' + name
    return type(default)(argv[argv.index(k) + 1]) if k in argv else default
EXR = arg('exr', ''); MODE = arg('mode', 'still'); OUT = arg('out', 'out.png'); RES = arg('res', 0)
EXPO = arg('exposure', 0.25); FPS = 24; T = arg('seconds', 6.0); NF = int(FPS * T)
F0, F1 = arg('f0', 0), arg('f1', NF)
rng = np.random.default_rng(5)

# ---------------------------------------------------------------- load
inp = oiio.ImageInput.open(EXR); spec = inp.spec(); names = list(spec.channelnames)
px = inp.read_image(0, 0, 0, len(names), 'float'); inp.close()
px = np.asarray(px, np.float32).reshape(spec.height, spec.width, len(names))
def ch(n): return px[:, :, names.index(n)]
def rgb(g): return np.stack([ch(g + '.R'), ch(g + '.G'), ch(g + '.B')], -1)
SRC_W = spec.width
P = {g: rgb(g) for g in ('sky', 'poster', 'warm')}
D = {n: ch(n + '.V') for n in ('Mist', 'Depth', 'plant', 'rill', 'face', 'glass')}
del px

def resize(a, w, h):
    sh = a.shape; c = 1 if a.ndim == 2 else sh[2]
    b = oiio.ImageBuf(oiio.ImageSpec(sh[1], sh[0], c, 'float')); b.set_pixels(oiio.ROI(), np.ascontiguousarray(a.reshape(sh[0], sh[1], c)))
    r = oiio.ImageBufAlgo.resize(b, roi=oiio.ROI(0, w, 0, h, 0, 1, 0, c))
    o = np.asarray(r.get_pixels(oiio.FLOAT)).reshape(h, w, c)
    return o[:, :, 0] if a.ndim == 2 else o
if RES and RES != SRC_W:
    w = RES; h = int(round(spec.height * RES / SRC_W))
    P = {k: resize(v, w, h) for k, v in P.items()}; D = {k: resize(v, w, h) for k, v in D.items()}
H, W = P['sky'].shape[:2]
FLN = arg('lens', 27.0) / 36.0          # focal length over the (horizontal) sensor width, as in rain_scene.py --lens
S = W * FLN / (2560.0 * 0.75)           # pixels per metre relative to the 2560 landscape render (the phone frame is closer)
AREA = W * H / (2560.0 * 1440.0)        # rain and rings are counted per frame area

# ---------------------------------------------------------------- the camera, as in rain_scene.py (for drips and the chain)
CX, CY, CZ, FL, SHIFT = 0.0, -7.4, 1.55, FLN, arg('shift', 0.03)
SREF = max(W, H)                       # Blender's lens shift is in units of the longer side
def proj(x, y, z):
    d = y - CY
    return np.array([W * (0.5 + (x - CX) / d * FL), H / 2 - ((z - CZ) / d * FL * W - SHIFT * SREF)]), W * FL / d   # pixel, px per metre

# ---------------------------------------------------------------- helpers
def box1(a, r, axis):
    if r < 1: return a
    c = np.cumsum(a, axis=axis, dtype=np.float32)
    pad = [(0, 0)] * a.ndim; pad[axis] = (r + 1, r)
    c = np.pad(c, pad, mode='edge')
    sl_hi = [slice(None)] * a.ndim; sl_lo = [slice(None)] * a.ndim
    n = a.shape[axis]
    sl_hi[axis] = slice(2 * r + 1, 2 * r + 1 + n); sl_lo[axis] = slice(0, n)
    return (c[tuple(sl_hi)] - c[tuple(sl_lo)]) / (2 * r + 1)
def blur(a, r):
    for _ in range(3):
        a = box1(box1(a, r, 0), r, 1)
    return a
def down(a, k):
    h, w = a.shape[0] // k * k, a.shape[1] // k * k
    a = a[:h, :w]
    return a.reshape(h // k, k, w // k, k, *a.shape[2:]).mean(axis=(1, 3))
def up(a, h, w):
    return resize(a, w, h)
def sample(img, x, y):
    # bilinear lookup of img at float pixel coords x, y (arrays)
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = x.astype(np.int32); y0 = y.astype(np.int32); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    a = img[y0, x0]; b = img[y0, x0 + 1]; c = img[y0 + 1, x0]; d = img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
def splat(acc, xs, ys, cols):
    # additive bilinear splats of colours at float pixel coords
    ok = (xs >= 0) & (xs < W - 1) & (ys >= 0) & (ys < H - 1)
    xs, ys, cols = xs[ok], ys[ok], cols[ok]
    x0 = xs.astype(np.int64); y0 = ys.astype(np.int64); fx = (xs - x0)[:, None]; fy = (ys - y0)[:, None]
    flat = acc.reshape(-1, 3)
    for dx, dy, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        np.add.at(flat, (y0 + dy) * W + (x0 + dx), cols * wgt)

# ---------------------------------------------------------------- view transform: Blender's AgX, Base Contrast
cfg = ocio.GetCurrentConfig()
dvt = ocio.DisplayViewTransform(src='Linear Rec.709', display='sRGB', view='AgX')
vp = ocio.LegacyViewingPipeline(); vp.setDisplayViewTransform(dvt)
vp.setLooksOverrideEnabled(True); vp.setLooksOverride('AgX - Base Contrast')
CPU = vp.getProcessor(cfg).getDefaultCPUProcessor()
def view(lin):
    a = np.ascontiguousarray(np.clip(lin * (2 ** EXPO), 0, 1e4).astype(np.float32))
    CPU.applyRGB(a); return np.clip(a, 0, 1)

# ---------------------------------------------------------------- static parts
FOG = np.array([float(v) for v in arg('fog-col', '0.30,0.38,0.52').split(',')], np.float32); FOG = np.where(FOG > 0.04045, ((FOG + 0.055) / 1.055) ** 2.4, FOG / 12.92) * arg('fog-l', 0.1)
fogk = (1 - (1 - np.clip(D['Mist'], 0, 1)) ** arg('fog-g', 1.0))[..., None] * arg('fogk', 0.82)
if arg('fog-depth', 0.0) > 0:
    # aerial perspective from depth (for --vista renders): nothing nearer than --fog-near, then an exponential
    # fall into the rain haze, so the far towers emerge from it rather than stand in front of it
    # the EXR's half floats leave stray depth samples; a 5 by 5 median removes them before they can fog a pixel
    zd = np.clip(np.nan_to_num(D['Depth'], posinf=1e9), 0, 1e9); zp = np.pad(zd, 2, mode='edge')
    zd = np.median(np.stack([zp[j:j + zd.shape[0], i:i + zd.shape[1]] for j in range(5) for i in range(5)]), 0)
    fogk = (1 - np.exp(-np.clip(zd - arg('fog-near', 150.0), 0, 1e9) / arg('fog-depth', 0.0)))[..., None] * arg('fogk', 0.82)    # 0 with --vista renders: the scene's own air does it
PL = arg('poster-k', 1.0)
SKYT = np.array([float(v) for v in arg('sky-tint', '1,1,1').split(',')], np.float32)
KW = arg('kw', 1.0)
# the far warm light (terrace windows, lane lamps) held in the mist: a wide soft bloom of the warm group, beyond the wall
far = np.clip((D['Depth'] - 15.0) / 6.0, 0, 1)[..., None]
FARG = arg('far-glow', 0.0)
if FARG > 0:
    fw = P['warm'] * far
    FARL = (up(blur(down(fw, 8), 6), H, W) * 0.6 + up(blur(down(fw, 16), 5), H, W) * 0.4) * FARG * np.array([1.0, 0.82, 0.62], np.float32)
else:
    FARL = 0.0
def light(kw=1.0, kp=PL):
    L = P['sky'] * SKYT + P['poster'] * kp + P['warm'] * kw * KW
    return L * (1 - fogk) + FOG * fogk + FARL
plant = np.clip(D['plant'], 0, 1)
plantb = blur(plant, max(1, int(4 * S)))
water = np.clip(D['rill'], 0, 1); water = np.maximum(water, (D['rill'] > 1.5).astype(np.float32))
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
# a smooth random phase field, so leaves answer the wind at their own moment
ph1 = blur(rng.uniform(0, 1, (H // 8 + 1, W // 8 + 1)).astype(np.float32), 3); ph1 = (ph1 - ph1.min()) / (np.ptp(ph1) + 1e-6)
ph1 = up(ph1, H, W) * 2 * np.pi * 2.0
ph2 = blur(rng.uniform(0, 1, (H // 16 + 1, W // 16 + 1)).astype(np.float32), 2); ph2 = (ph2 - ph2.min()) / (np.ptp(ph2) + 1e-6)
ph2 = up(ph2, H, W) * 2 * np.pi * 3.0
sway_amp = (1.0 + 1.2 * np.clip(1 - yy / (H * 0.55), 0, 1)) * S * arg('sway', 1.0) * plantb
# where the light is, for lighting the rain: a broad blur of the lit frame
def lightfield(L):
    l = down(L, 8); l = blur(l, 3)
    return up(l, H, W)

# ---------------------------------------------------------------- rain, drips, rings: all periodic on T
class Streaks:
    def __init__(self, n, lmin, lmax, wt, cycles, depth_k):
        self.x = rng.uniform(-0.1 * W, 1.05 * W, n); self.y0 = rng.uniform(0, 1, n)
        self.L = rng.uniform(lmin, lmax, n) * S; self.wt = wt * rng.uniform(0.5, 1.0, n)
        self.cyc = rng.integers(cycles[0], cycles[1] + 1, n); self.k = depth_k
    def draw(self, acc, t, Lf):
        span = H + self.L * 2
        yc = ((self.y0 + self.cyc * t / T) % 1.0) * span - self.L
        K = max(8, int(self.L.max() / 0.9))
        u = np.linspace(-0.5, 0.5, K)[None, :]
        ys = yc[:, None] + u * self.L[:, None]; xs = self.x[:, None] + ys * 0.07
        prof = np.sin((u + 0.5) * np.pi) ** 1.5
        c = sample(Lf, np.clip(xs[:, K // 2], 0, W - 2), np.clip(ys[:, K // 2], 0, H - 2))
        col = (c * self.k + 0.0015)[:, None, :] * (self.wt[:, None] * prof)[..., None] * (self.L[:, None, None] / K) * 0.06
        splat(acc, xs.ravel(), ys.ravel(), col.reshape(-1, 3))
RAIN = [Streaks(int(arg('near', 90) * AREA), 90, 150, 1.0, (9, 12), 1.0), Streaks(int(arg('mid', 420) * AREA), 40, 70, 0.8, (6, 8), 0.8),
        Streaks(int(arg('far', 1100) * AREA), 14, 26, 0.6, (4, 5), 0.6)]

# drips: from the canopy edge, the coping, the tree; each falls on its own period
DRIPS = []
# every drip period divides the loop, so the last frame runs into the first (6 s: 1.5, 2, 3, 6; 8 s: 1, 2, 4, 8)
PERIODS = [T / 4, T / 3, T / 2, T] if abs(T - 6.0) < 1e-6 else [T / 8, T / 4, T / 2, T]
def add_drip(x, y, z, zg, period, phase):
    p0, k = proj(x, y, z); p1, _ = proj(x, y, zg)
    DRIPS.append((p0, p1[1], k, period, phase))
for i in range(9):
    add_drip(rng.uniform(1.7, 4.8), -0.74, 2.76, 0.0, float(rng.choice(PERIODS[:3])), rng.uniform(0, 1))
for i in range(10):
    x = rng.uniform(-4.5, 1.3)
    if -1.05 < x < 1.05: continue
    add_drip(x, -0.07, 3.38, 0.17, float(rng.choice(PERIODS[1:])), rng.uniform(0, 1))
# tree drips: emitters on bright-edged leaves in the upper left
cand = np.argwhere((plant[: int(H * 0.45), : int(W * 0.35)] > 0.9))
for i in range(min(10, len(cand))):
    yx = cand[rng.integers(len(cand))]
    DRIPS.append((np.array([yx[1], yx[0]], np.float32), H * 0.98, W * FL / 5.0, float(rng.choice(PERIODS[:3])), rng.uniform(0, 1)))
def draw_drips(acc, t, Lf):
    for p0, yground, k, per, ph in DRIPS:
        a = ((t / per + ph) % 1.0) * per
        hang = 0.45
        if a < hang:                                       # the drop gathers on the edge
            c = sample(Lf, np.array([p0[0]]), np.array([p0[1] + 2]))[0] * (a / hang) * 0.5 + 0.002
            splat(acc, np.array([p0[0]]), np.array([p0[1] + 2 * S]), (c * 3.0)[None, :]); continue
        tf = a - hang; g = 9.8 * k; y = p0[1] + 0.5 * g * tf * tf; v = g * tf
        if y > yground: continue
        L = max(3 * S, v / 48.0); K = max(6, int(L / 0.8)); ys = y - np.linspace(0, L, K); xs = np.full(K, p0[0])
        c = sample(Lf, xs[:1], np.clip(ys[:1], 0, H - 2))[0]
        splat(acc, xs, ys, np.tile((c * 1.1 + 0.002) * 1.4 / K * (L / S) * 0.25, (K, 1)))
# the rain chain: water running down it, a quick bright thread
CH0, kc = proj(1.80, -0.58, 2.70); CH1, _ = proj(1.80, -0.58, 0.14)
CHD = [(rng.uniform(0, 1), rng.integers(3, 6), rng.uniform(-1, 1)) for _ in range(26)]
def draw_chain(acc, t, Lf):
    for ph, cyc, ox in CHD:
        f = (ph + cyc * t / T) % 1.0; y = CH0[1] + f * (CH1[1] - CH0[1]); x = CH0[0] + ox * 2.2 * S + math.sin(y * 0.35) * 1.2 * S
        K = 6; ys = y - np.linspace(0, 9 * S, K); xs = np.full(K, x)
        c = sample(Lf, xs[:1], ys[:1])[0]
        splat(acc, xs, ys, np.tile((c * 1.6 + 0.003) / K * 2.0, (K, 1)))
# rings in the puddles and the rill
wy, wx = np.nonzero(water[int(H * 0.72):, :] > 0.6); wy = wy + int(H * 0.72)
RINGS = []
for i in range(int(arg('rings', 70) * max(AREA, 0.5))):
    j = rng.integers(len(wy)) if len(wy) else 0
    if not len(wy): break
    y, x = float(wy[j]), float(wx[j]); d = max(1.0, float(D['Depth'][int(y), int(x)]))
    k = W * FL / d; fl = min(0.6, CZ / d)
    RINGS.append((x, y, k, fl, rng.uniform(0, T), rng.uniform(0.55, 0.8)))
def rings(t):
    dx = np.zeros((H, W), np.float32); dy = np.zeros((H, W), np.float32); hl = np.zeros((H, W), np.float32)
    for x, y, k, fl, s0, life in RINGS:
        a = ((t - s0) % T)
        if a > life: continue
        u = a / life; R = (0.02 + 0.13 * u) * k; amp = (1 - u) ** 2 * 1.4 * S
        rx = R + 6 * S; ry = rx * fl + 2
        x0, x1 = int(max(0, x - rx - 2)), int(min(W, x + rx + 3)); y0, y1 = int(max(0, y - ry - 2)), int(min(H, y + ry + 3))
        if x1 <= x0 or y1 <= y0: continue
        gx = xx[y0:y1, x0:x1] - x; gy = (yy[y0:y1, x0:x1] - y) / max(fl, 0.05)
        r = np.sqrt(gx * gx + gy * gy) + 1e-3; band = np.exp(-((r - R) / (2.2 * S)) ** 2)
        wv = np.sin((r - R) / (2.0 * S) * np.pi) * band * amp
        dx[y0:y1, x0:x1] += gx / r * wv; dy[y0:y1, x0:x1] += gy / r * wv * fl
        hl[y0:y1, x0:x1] += band * (1 - u) * 0.6
    return dx, dy, hl

# drops on the lightbox glass: a few run down it in short starts, each leaving a faint wet trail; seen against the
# lit print they are slightly darker at the rim with a bright point where they catch the light
GLASS = []
if arg('corners', ''):
    import json
    cj = json.load(open(arg('corners', '')))
    k_ = W / cj['res'][0]
    fx0, fy0 = cj['tl'][0] * k_, cj['tl'][1] * k_; fx1, fy1 = cj['br'][0] * k_, cj['br'][1] * k_
    for i in range(int(arg('glass-drops', 14))):
        GLASS.append((rng.uniform(fx0 + 6 * S, fx1 - 6 * S), fy0, fy1, int(rng.integers(1, 3)), rng.uniform(0, 1), rng.uniform(0.6, 1.0) * S))
def glass_drops(L, t):
    for x, y0, y1, cyc, ph, sz in GLASS:
        f = (ph + cyc * t / T) % 1.0
        f = f + 0.02 * np.sin(2 * np.pi * f * 7)                   # stop and start, as a real drop does
        y = y0 + (y1 - y0) * (0.05 + 0.9 * f); r = arg('drop-r', 4.5) * sz
        xa, xb = int(max(0, x - 3 * r)), int(min(W, x + 3 * r + 1)); ya, yb = int(max(0, y0 + (y1 - y0) * 0.05)), int(min(H, y + 3 * r + 1))
        if xb <= xa or yb <= ya: continue
        gx = xx[ya:yb, xa:xb] - x; gy = yy[ya:yb, xa:xb] - y
        trail = np.exp(-(gx / (0.6 * r)) ** 2) * (gy < 0) * np.exp(gy / (80 * S)) * 0.08
        d = np.sqrt(gx * gx + gy * gy) / r
        rim = np.exp(-((d - 0.85) / 0.25) ** 2) * 0.22; core = np.exp(-((gx + 0.3 * r) ** 2 + (gy + 0.35 * r) ** 2) / (0.12 * r * r)) * 0.5
        L[ya:yb, xa:xb] *= (1 - trail - rim)[..., None]
        L[ya:yb, xa:xb] += core[..., None] * 1.5
    return L

# ---------------------------------------------------------------- finishing: bloom with a warm halation, aberration, vignette, grain
vig = 1 - 0.28 * np.clip(((xx / W - 0.5) ** 2 * 1.3 * min(1.0, W / H) + (yy / H - 0.5) ** 2 * 1.0) * 2.4 - 0.15, 0, 1) ** 1.3
def bloom(L):
    hi = np.maximum(L - arg('bloom-th', 0.6), 0)
    b = np.zeros_like(L); h = hi
    for i, wgt in enumerate((0.5, 0.35, 0.25, 0.18)):
        h = down(h, 2) if i else down(h, 4)
        b += up(blur(h, 2), H, W) * wgt
    hal = b * np.array([1.25, 0.95, 0.75], np.float32)
    return L + hal * arg('bloom', 0.07)
LIFT = np.array([float(v) for v in arg('lift', '0,0,0').split(',')], np.float32)
SAT = arg('sat', 1.0); HW = arg('hi-warm', 0.0)
def grade(img):
    # gentle: blacks lifted towards deep blue, warmth in the highlights, a little more colour
    y = (img * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    img = y + (img - y) * SAT
    img = img + (img ** 3) * np.array([1.0, 0.45, -0.5], np.float32) * HW
    img = LIFT + (1 - LIFT) * np.clip(img, 0, 1)
    return img
# the crystal in the poster's mark, held to sky (#94E6FF) with its lit facet: AgX rightly desaturates a bright
# emitter, so the crystal is laid in after the grade, exactly on the print's geometry mapped through the face corners
GEM = None
if arg('gem', '') and arg('corners', ''):
    import json
    mk = json.load(open(arg('gem', ''))); cj2 = json.load(open(arg('corners', ''))); k2 = W / cj2['res'][0]
    tl, tr, bl = np.array(cj2['tl']) * k2, np.array(cj2['tr']) * k2, np.array(cj2['bl']) * k2
    def to_frame(p): return tl + (tr - tl) * p[0] / mk['print'][0] + (bl - tl) * p[1] / mk['print'][1]
    def mask(pts, ss=6):
        # a convex polygon, anti-aliased: half-plane tests on a supersampled grid over its box
        q = np.array([to_frame(p) for p in pts], np.float64)
        if np.cross(q[1] - q[0], q[2] - q[1]) < 0: q = q[::-1]
        x0_, y0_ = int(np.floor(q[:, 0].min())) - 1, int(np.floor(q[:, 1].min())) - 1
        x1_, y1_ = int(np.ceil(q[:, 0].max())) + 2, int(np.ceil(q[:, 1].max())) + 2
        sy, sx = np.mgrid[y0_:y1_:1.0 / ss, x0_:x1_:1.0 / ss]; sx = sx + 0.5 / ss; sy = sy + 0.5 / ss
        inside = np.ones(sx.shape, bool)
        for i in range(len(q)):
            a_, b_ = q[i], q[(i + 1) % len(q)]
            inside &= (b_[0] - a_[0]) * (sy - a_[1]) - (b_[1] - a_[1]) * (sx - a_[0]) >= 0
        cov = inside.reshape(y1_ - y0_, ss, x1_ - x0_, ss).mean(axis=(1, 3)).astype(np.float32)
        m = np.zeros((H, W), np.float32); m[y0_:y1_, x0_:x1_] = cov
        return m
    gm_ = mask(mk['gem']); fc_ = mask(mk['gem'][:4])
    GEM = (gm_[..., None], fc_[..., None])
SKYC = np.array([0x94, 0xE6, 0xFF], np.float32) / 255
def finish(img, t=0.0, grain=0.0):
    out = grade(img) * vig[..., None]
    if GEM is not None:
        g_, f_ = GEM; out = out * (1 - g_) + SKYC * g_; out = out * (1 - f_ * 0.28) + f_ * 0.28
    ca = arg('ca', 0.6) * S                                  # lateral colour fringe, growing to the corners
    rx = (xx - W / 2) / (W / 2); ry_ = (yy - H / 2) / (W / 2)
    out[..., 0] = sample(out[..., :1], xx + rx * ca, yy + ry_ * ca)[..., 0]
    out[..., 2] = sample(out[..., 2:3], xx - rx * ca, yy - ry_ * ca)[..., 0]
    if grain:
        g = rng.normal(0, grain, (H, W)).astype(np.float32); g = (g + blur(g, 1) * 0.5)
        out = out + g[..., None] * (0.35 + 0.65 * (1 - out))
    return np.clip(out, 0, 1)

def frame(t, rain=True, kp=PL, warm_breath=True):
    kw = 1.0 + (0.05 * math.sin(2 * math.pi * t / T) if warm_breath else 0.0)
    L = light(kw, kp)
    if rain:
        # leaves in the wind: a small displacement, weighted by the foliage mask
        dx = sway_amp * (np.sin(2 * np.pi * t / T * 2 + ph1) * 0.65 + np.sin(2 * np.pi * t / T * 3 + ph2) * 0.35)
        dy = dx * 0.25 + sway_amp * 0.3 * np.sin(2 * np.pi * t / T * 3 + ph1 * 0.7)
        rdx, rdy, hl = rings(t)
        L = sample(L, xx - dx - rdx, yy - dy - rdy)
        Lf = lightfield(L)
        L = L + Lf * hl[..., None] * 0.25
        acc = np.zeros_like(L)
        for r in RAIN: r.draw(acc, t, Lf)
        draw_drips(acc, t, Lf); draw_chain(acc, t, Lf)
        L = L + acc * arg('rain', 10.0)
        if GLASS: L = glass_drops(L, t)
    return bloom(L)

def save(path, img, bits=8):
    o = (img * 255 + rng.uniform(-0.5, 0.5, img.shape) if bits == 8 else img * 65535).round()
    o = np.clip(o, 0, 255 if bits == 8 else 65535).astype(np.uint8 if bits == 8 else np.uint16)
    out = oiio.ImageOutput.create(path); sp = oiio.ImageSpec(W, H, 3, oiio.UINT8 if bits == 8 else oiio.UINT16)
    if path.lower().endswith('.jpg'): sp.attribute('Compression', 'jpeg:95')    # loop frames: small on disk, encoded straight after
    out.open(path, sp); out.write_image(o); out.close()

if MODE == 'still':
    save(OUT, finish(view(frame(arg('t', 1.3), rain=arg('rain-on', 1) == 1)), grain=arg('grain', 0.012)))
elif MODE == 'spill':
    # the poster's own light, as it shows on screen: (all lights) minus (all but the poster), in display terms
    on = finish(view(frame(0.0, rain=False))); off = finish(view(frame(0.0, rain=False, kp=0.0)))
    save(OUT, np.clip(on - off, 0, 1))
    save(OUT.replace('.png', '_off.png'), off)
elif MODE == 'aux':
    # for the page's breathing layer: R disparity about the wall (128 = the wall, brighter is nearer),
    # G the wet paving where a touch can ring the water. Run at full resolution (no --res): depth is clamped
    # before any filtering, so the sky's huge values never bleed into the wall.
    piv = -CY
    z = np.clip(D['Depth'], 0.5, 1000.0)
    dsp = np.clip(piv / z - 1.0, -1, 1)
    k = int(arg('aux-k', 4)); dsp = down(dsp, k)
    pd_ = np.pad(dsp, 2, mode='edge')
    dsp = np.median(np.stack([pd_[j:j + dsp.shape[0], i:i + dsp.shape[1]] for j in range(5) for i in range(5)]), 0)
    gnd = ((z < piv - 0.05) & (yy > H * arg('gnd-y', 0.81)) & (blur(plant, 3) < 0.05)).astype(np.float32)
    gnd = blur(down(gnd, k), 2)
    h_, w_ = dsp.shape
    o = np.stack([dsp * 0.5 + 0.5, gnd[:h_, :w_], np.zeros_like(dsp)], -1)
    H, W = h_, w_
    save(OUT, np.clip(o, 0, 1))
elif MODE == 'loop':
    import time
    for f in range(F0, F1):
        t0 = time.time()
        save(OUT % (f + 1), finish(view(frame(f / FPS))))
        print('frame', f + 1, round(time.time() - t0, 2), flush=True)
