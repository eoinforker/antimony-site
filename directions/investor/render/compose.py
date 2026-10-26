# Compose the investor hero from its linear passes, in Blender's own AgX view.
#   blender -b -P compose.py -- --src <dir with beauty/sun/water/crystal exr> --mist <mist exr> --out <png or pattern with ####>
#       [--frames 1-192] [--exposure -0.6] [--still 1]
# A frame is: the lake (beauty) with its reflections shimmering slightly, the sun's light breathing
# (beauty plus a small swing of the sun's own light group), then the mist laid over it with a slow
# drifting density, then a soft bloom. Every motion is periodic in the loop length, so the last frame
# runs straight into the first. Frame 1 is the still.

import bpy, sys, os, math, glob, time
import numpy as np

def arg(name, default):
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return a[a.index(name) + 1] if name in a else default

SRC = arg('--src', '.'); MIST = arg('--mist', ''); OUT = arg('--out', 'out.png')
FR = arg('--frames', '1-1'); EXPO = float(arg('--exposure', '0.0'))
NF = int(arg('--nf', '192'))
BREATH = float(arg('--breath', '0.09')); DRIFT = float(arg('--drift', '1.0'))
MISTK = float(arg('--mistk', '1.0'))
SC = bpy.context.scene

def load(pth):
    im = bpy.data.images.load(pth); w, h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]   # top row first
    bpy.data.images.remove(im); return a

def find(name):
    g = sorted(glob.glob(os.path.join(SRC, name + '*.exr')))
    return g[0] if g else None

def blur(x, rad):
    for _ in range(3):
        for ax in (0, 1):
            pad = [(0, 0)] * x.ndim; pad[ax] = (rad + 1, rad)
            c = np.cumsum(np.pad(x, pad, mode='edge'), axis=ax); n = x.shape[ax]
            x = (np.take(c, np.arange(2 * rad + 1, 2 * rad + 1 + n), axis=ax) - np.take(c, np.arange(n), axis=ax)) / (2 * rad + 1)
    return x

TW = int(arg('--width', '0'))
def resize(m, H, W):
    mh, mw = m.shape[:2]
    if (mh, mw) == (H, W): return m
    if mh > H:   # shrink: box average after a light blur keeps it clean
        k = mh / H
        r = max(1, int(k / 2))
        m = blur(m if m.ndim == 3 else m[..., None], r)
        if m.shape[-1] == 1 and m.ndim == 3: m = m[..., 0]
    ys = np.linspace(0, mh - 1, H); xs = np.linspace(0, mw - 1, W)
    y0 = np.floor(ys).astype(int); x0 = np.floor(xs).astype(int)
    y1 = np.minimum(y0 + 1, mh - 1); x1 = np.minimum(x0 + 1, mw - 1)
    ex = (lambda a: a[:, None, None]) if m.ndim == 3 else (lambda a: a[:, None])
    fy = ex(ys - y0); fx = (xs - x0)[None, :, None] if m.ndim == 3 else (xs - x0)[None, :]
    return ((m[y0][:, x0] * (1 - fx) + m[y0][:, x1] * fx) * (1 - fy) + (m[y1][:, x0] * (1 - fx) + m[y1][:, x1] * fx) * fy).astype(np.float32)

CROP = arg('--crop', '')       # x0,w in full resolution pixels: the portrait loop is composed from the full render
def cropx(m):
    if not CROP: return m
    x0, w = map(int, CROP.split(','))
    if m.shape[1] != FULLW:      # a pass rendered smaller (the mist): scale the window
        k = m.shape[1] / FULLW; return m[:, int(x0 * k):int(x0 * k) + max(1, int(round(w * k)))]
    return m[:, x0:x0 + w]
_l = load
FULLW = None
def load(pth):
    a = _l(pth)
    return cropx(a) if FULLW else a
beauty = _l(find('beauty'))[..., :3]
FULLW = beauty.shape[1]
beauty = cropx(beauty)
H, W = beauty.shape[:2]
if TW and TW != W:
    H, W = int(round(H * TW / W)), TW
    beauty = resize(beauty, H, W)
sun = resize(load(find('sun'))[..., :3], H, W) if find('sun') else np.zeros_like(beauty)
water = resize(load(find('water'))[..., 0], H, W) if find('water') else np.zeros((H, W), np.float32)
mist = None
if MIST and os.path.exists(MIST):
    m = load(MIST)
    m = resize(m, H, W)
    mist = m.astype(np.float32) * MISTK

if arg('--masks', ''):
    cr = load(find('crystal'))[..., 0] if find('crystal') else np.zeros((H, W), np.float32)
    np.save(arg('--masks', '') + '/crystal.npy', cr.astype(np.float32))
    np.save(arg('--masks', '') + '/water.npy', water.astype(np.float32))

# a power window on the crystal, as a colourist would: hold its colour on the brand's sky (#94E6FF)
CG = float(arg('--crygrade', '0.0'))
if CG > 0 and find('crystal'):
    cm = resize(load(find('crystal'))[..., 0], H, W)
    # its reflection: the mask mirrored about the waterline, then only where there is water
    wr0 = np.where(water.mean(1) > 0.5)[0]; hz0 = int(wr0[0]) if len(wr0) else H
    ref = np.zeros_like(cm); rows = np.arange(hz0, H); src = 2 * hz0 - 1 - rows
    ok_ = src >= 0; ref[rows[ok_]] = cm[src[ok_]]
    cm = np.clip(cm + ref * water, 0, 1)[..., None]
    skyl = np.array([0.296, 0.791, 1.0], np.float32)
    def grade(x):
        lum = (x * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
        tgt = lum / 0.7134 * skyl * float(arg('--crylev', '0.85'))
        return x * (1 - cm * CG) + tgt * cm * CG
    beauty = grade(beauty); sun = grade(sun)

# horizon row: the first water row from the top
wr = np.where(water.mean(1) > 0.5)[0]
HZ = int(wr[0]) if len(wr) else int(H * 0.66)

# periodic value noise on a ring, so drift loops exactly
rng = np.random.default_rng(5)
def pnoise2(u, v, period, seed):
    """Smooth 2D noise, periodic in u with the given integer period."""
    r = np.random.default_rng(seed)
    grid = r.uniform(0, 1, (64, period)).astype(np.float32)
    ui = np.floor(u).astype(int); vi = np.floor(v).astype(int)
    fu = u - ui; fv = v - vi
    fu = fu * fu * (3 - 2 * fu); fv = fv * fv * (3 - 2 * fv)
    a = grid[vi % 64, ui % period]; b = grid[vi % 64, (ui + 1) % period]
    c = grid[(vi + 1) % 64, ui % period]; d = grid[(vi + 1) % 64, (ui + 1) % period]
    return (a * (1 - fu) + b * fu) * (1 - fv) + (c * (1 - fu) + d * fu) * fv

# ground coordinates of each pixel below the horizon (for the mist drift and the water shimmer)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
below = np.maximum(yy - HZ + 1.5, H * 0.012)   # far water is clamped, so the drift never turns to stripes at the horizon
dist = (H * 0.5) / below                  # proportional to distance on the water
CX0 = int(CROP.split(',')[0]) if CROP else 0
gx = (xx + CX0 - FULLW * 0.5) / FULLW * dist   # across, in the full frame's terms
gz = dist                                 # away
# above the horizon the mist rises in front of the far shore and the stone: carry on upwards in the volume
gz = np.where(yy < HZ, gz + (HZ - yy) / H * 70.0, gz)

out_img = bpy.data.images.new('frame', W, H, float_buffer=True, alpha=False)
vs = SC.view_settings; vs.view_transform = 'AgX'; vs.look = 'AgX - Base Contrast'; vs.exposure = 0.0
st = SC.render.image_settings; st.file_format = 'PNG'; st.color_mode = 'RGB'; st.color_depth = '16' if arg('--d16', '0') == '1' else '8'

a, b = map(int, FR.split('-'))
for f in range(a, b + 1):
    t = (f - 1) / NF                       # 0 to 1 over the loop
    ph = 2 * math.pi * t
    # light breathing: a slow swell of the sun, two cycles with a little asymmetry
    br = BREATH * (0.65 * math.sin(ph) + 0.35 * math.sin(2 * ph + 0.7))
    lin = beauty + sun * br
    # water: reflections shimmer by a pixel or so, more near, less far
    if True:
        amp = np.clip(1.6 / dist, 0.0, 2.2) * water
        # the noise is walked round a small circle, so it returns to where it began
        n = pnoise2(gx * 6.0 + 1.4 * math.cos(ph) + 4096, gz * 9.0 + 1.4 * math.sin(ph) + 64, 4096, 2) - 0.5
        n2 = pnoise2(gx * 13.0 + 2.2 * math.cos(2 * ph) + 8192, gz * 23.0 + 2.2 * math.sin(2 * ph) + 71, 8192, 3) - 0.5
        dx = (n * 1.6 + n2 * 0.8) * amp
        dy = (n2 * 0.9) * amp * 0.6
        sx = np.clip(xx + dx, 0, W - 1); sy = np.clip(yy + dy, HZ, H - 1)
        x0 = np.floor(sx).astype(int); y0 = np.floor(sy).astype(int)
        x1 = np.minimum(x0 + 1, W - 1); y1 = np.minimum(y0 + 1, H - 1)
        fx = (sx - x0)[..., None]; fy = (sy - y0)[..., None]
        sh = (lin[y0, x0] * (1 - fx) + lin[y0, x1] * fx) * (1 - fy) + (lin[y1, x0] * (1 - fx) + lin[y1, x1] * fx) * fy
        wm = water[..., None]
        lin = lin * (1 - wm) + sh * wm
    if mist is not None:
        # the mist drifts: its lit shape stays where the light puts it, its density moves through
        # two drifting layers, each fading in and out on its own half of the cycle (a flow map, as water
        # shaders do), so the drift reads as steady and still lands exactly where it began
        dn = 0.0
        for li, off in enumerate((0.0, 0.5)):
            p_ = (t * 2.0 + off) % 1.0
            w_ = 1.0 - abs(2.0 * p_ - 1.0)
            u = gx * 0.9 + DRIFT * p_ * 1.4 + li * 17.0
            n_ = pnoise2(u + 640, gz * 0.35 + li * 9, 4096, 9 + li) * 0.6 + pnoise2(u * 2.0 + 1280.5, gz * 0.8 + 3 + li * 5, 4096, 20 + li) * 0.4
            dn = dn + w_ * n_
        dn = dn.astype(np.float32)
        k = (0.72 + 0.56 * dn)[..., None]
        k = np.where((yy < HZ - 2)[..., None], 0.85 + 0.15 * k, k)
        mb = 1.0 + br * 0.6
        ma = np.clip(mist[..., 3:4] * k, 0, 1)
        lin = lin * (1 - ma) + mist[..., :3] * k * mb
    lin = lin * (2.0 ** EXPO)
    lum = lin.mean(-1, keepdims=True)
    hi = np.maximum(lin - 1.0, 0.0) * np.clip((lum - 1.0) * 3, 0, 1)
    small = hi[::4, ::4]
    bl = blur(small, max(2, W // 640)) * 0.6 + blur(small, max(4, W // 160)) * 0.4
    bl = np.repeat(np.repeat(bl, 4, 0), 4, 1)[:H, :W]
    lin = lin + bl * 0.3
    px = np.ascontiguousarray(np.concatenate([lin.astype(np.float32), np.ones((H, W, 1), np.float32)], -1)[::-1])
    out_img.pixels.foreach_set(px.ravel())
    out_img.save_render(OUT.replace('####', '%04d' % f), scene=SC)
    print('composed', f); sys.stdout.flush()
