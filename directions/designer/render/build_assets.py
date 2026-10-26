# Turn the linear EXR passes into the page's textures, and compose the still the page shows
# before WebGL is ready (and instead of it, when there is none).
#   python3 build_assets.py <scratch dir> <frame: desktop|phone> [--meadow]
# Encoding: light is stored as e = log2(1 + 256 x) / 13 in 8 bits (the page decodes it), so the dark
# stone keeps its gradations and the highlights keep their headroom. The ray tangents are 12 bits
# each, packed into an RGB PNG, read with nearest sampling and interpolated by hand on the page.
import sys, os, json, numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools import load_exr, agx, blur, save

SRC = sys.argv[1]; FRAME = sys.argv[2]
SITE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets'))
TW, TY0, TY1 = 0.62, -0.30, 0.54
EXPO = -1.45            # the house exposure for the AgX view (the page uses the same)
HORIZON = 0.07          # the meadow lookup offset in ty
REST_SPILL = 0.06        # the crystal lights its own seat a little, even at rest
MGAIN = 1.0             # the other world's exposure, relative to the night

def enc(x): return np.log2(1.0 + 256.0 * np.maximum(x, 0)) / 13.0
def dec(e): return (np.exp2(e * 13.0) - 1.0) / 256.0
def q8(x): return (np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8)

def sample(img, u, v):
    """bilinear sample, u v in 0..1, v down"""
    h, w = img.shape[:2]
    x = np.clip(u * w - 0.5, 0, w - 1.001); y = np.clip(v * h - 0.5, 0, h - 1.001)
    x0 = x.astype(int); y0 = y.astype(int); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    a = img[y0, x0]; b = img[y0, x0 + 1]; c = img[y0 + 1, x0]; d = img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

def meadow_at(sky, grass, tx, ty):
    u = (tx + TW) / (2 * TW); v = 1.0 - (ty + HORIZON - TY0) / (TY1 - TY0)
    s = sample(sky, u, v); g = sample(grass, u, v)
    return s * (1 - g[..., 3:4]) + g[..., :3]

def main():
    out = os.path.join(SITE, FRAME); os.makedirs(out, exist_ok=True)
    md = os.path.join(SITE, 'meadow'); os.makedirs(md, exist_ok=True)
    sky = load_exr(os.path.join(SRC, 'meadow_sky.exr'))[..., :3]
    gr = load_exr(os.path.join(SRC, 'meadow_grass.exr'))
    grass = np.concatenate([gr[..., :3], np.clip(gr[..., 3:4], 0, 1)], -1)
    if '--meadow' in sys.argv:
        Image.fromarray(q8(enc(sky))).save(os.path.join(md, 'sky.webp'), quality=88, method=6)
        a = np.maximum(grass[..., 3:4], 1e-4)
        straight = np.where(grass[..., 3:4] > 0.002, grass[..., :3] / a, 0)
        Image.fromarray(np.concatenate([q8(enc(straight)), q8(grass[..., 3:4])], -1), 'RGBA').save(os.path.join(md, 'grass.webp'), quality=90, method=6)
    meta = json.load(open(os.path.join(SRC, '%s_uv.json' % FRAME)))
    B = load_exr(os.path.join(SRC, '%s_beauty.exr' % FRAME))[..., :3]
    T = load_exr(os.path.join(SRC, '%s_thru.exr' % FRAME))[..., :3]
    Uv = load_exr(os.path.join(SRC, '%s_uv.exr' % FRAME))
    Sp = load_exr(os.path.join(SRC, '%s_spill.exr' % FRAME))[..., :3]
    h, w = B.shape[:2]
    if Sp.shape[:2] != (h, w):   # drafts only: a spill pass from another resolution
        yy, xx = np.meshgrid((np.arange(h) + 0.5) / h, (np.arange(w) + 0.5) / w, indexing='ij'); Sp = sample(Sp, xx, yy)
    # straight-through tangents of each pixel (camera space, y up)
    xs = (np.arange(w) + 0.5) / w; ys = (np.arange(h) + 0.5) / h
    sx = (xs * 2 - 1) * meta['tan_w'] + meta['shift_x']
    sy = (1 - ys * 2) * meta['tan_h'] + meta['shift_y']
    SX, SY = np.meshgrid(sx, sy)
    wgt = Uv[..., 2]
    ok = wgt > 0.02
    tx = np.where(ok, ((Uv[..., 0] / np.maximum(wgt, 1e-6)) - 0.5) / 1.2, SX)
    ty = np.where(ok, ((Uv[..., 1] / np.maximum(wgt, 1e-6)) - 0.5) / 1.2, SY)
    # spread valid tangents a few pixels into the invalid ones, so the hand-made bilinear never mixes in junk
    for _ in range(3):
        m = ok.astype(np.float32)
        bx = blur(tx * m, 1); by = blur(ty * m, 1); bm = blur(m, 1)
        fill = (~ok) & (bm > 0.05)
        tx = np.where(fill, bx / np.maximum(bm, 1e-6), tx); ty = np.where(fill, by / np.maximum(bm, 1e-6), ty)
        ok = ok | fill
    T = T * (wgt[..., None] > 0.0)
    if FRAME == 'phone':
        # the phone frame sees far more of the wet parapet, where the crystal's reflection blurs into a large
        # bright shape; hold it down to a glint so the stone stays the subject
        yy = (np.arange(h) + 0.5) / h
        T = T * (1.0 - 0.8 * np.clip((yy - 0.69) / 0.05, 0, 1))[:, None, None]
        dm = (1.0 - 0.85 * np.clip((yy - 0.69) / 0.05, 0, 1))[:, None, None]
        floor = np.minimum(B, 0.01)
        B = floor + (B - floor) * dm
        Sp = Sp * dm * dm
    qx = np.clip(np.round((tx + 0.8) / 1.6 * 4095), 0, 4095).astype(np.int32)
    qy = np.clip(np.round((ty + 0.8) / 1.6 * 4095), 0, 4095).astype(np.int32)
    pk = np.stack([qx >> 4, qy >> 4, ((qx & 15) << 4) | (qy & 15)], -1).astype(np.uint8)
    Image.fromarray(pk).save(os.path.join(out, 'ray.png'), optimize=True)
    # the let-out daylight carries a little of the meadow's colour
    M0 = meadow_at(sky, grass, tx, ty)
    mcol = M0[T.mean(-1) > 0.3].mean(0) if (T.mean(-1) > 0.3).any() else np.ones(3)
    Sp = Sp * (0.6 + 0.4 * mcol / mcol.mean())
    Image.fromarray(q8(enc(B))).save(os.path.join(out, 'base.webp'), quality=97, method=6)
    Image.fromarray(q8(enc(Sp))).save(os.path.join(out, 'spill.webp'), quality=88, method=6)
    Image.fromarray(q8(np.sqrt(np.clip(T, 0, 1)))).save(os.path.join(out, 'thru.webp'), quality=92, method=6)
    # a soft halo of the openings, for the daylight's bloom on the page
    lum = T.mean(-1)
    small = lum.reshape(h // 4, 4, w // 4, 4).mean((1, 3)) if h % 4 == 0 and w % 4 == 0 else lum[::4, ::4]
    gl = blur(small, 6) * 0.5 + blur(small, 22) * 0.35 + blur(small, 60) * 0.15
    gl = gl / max(gl.max(), 1e-6)
    Image.fromarray(q8(np.sqrt(gl))).save(os.path.join(out, 'glow.png'))
    # the still: rest state with the meadow in place, through the same view as the page
    M = meadow_at(sky, grass, tx, ty)
    lin = B + T * M * MGAIN + Sp * REST_SPILL
    g3 = np.repeat(np.repeat(gl, 4, 0), 4, 1)[:h, :w][..., None]
    mlum = M[ok].mean() if ok.any() else 0.3
    lin = lin + g3 * mlum * MGAIN * 0.035
    img = agx(lin, EXPO)
    save(img, os.path.join(out, 'rest.webp'), q=95)
    save(img, os.path.join(SRC, '%s_rest.png' % FRAME))
    # the spilled state, for the record
    lin2 = B + T * M * MGAIN * 1.9 + Sp * 1.0 + g3 * mlum * MGAIN * 0.55
    save(agx(lin2, EXPO), os.path.join(SRC, '%s_spill_preview.png' % FRAME))
    meta.update({'expo': EXPO, 'tw': TW, 'ty0': TY0, 'ty1': TY1, 'horizon': HORIZON, 'mgain': MGAIN, 'rest_spill': REST_SPILL, 'mlum': float(mlum)})
    json.dump(meta, open(os.path.join(out, 'meta.json'), 'w'), indent=1)
    print('ok', FRAME, w, h, 'mlum', mlum)

main()
