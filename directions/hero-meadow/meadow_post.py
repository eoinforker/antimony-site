# Hero Meadow: the photographic finish and the loop, in numpy.
# still: python3 meadow_post.py still <render.png> <out.png> [<data.png>] [--grain 0.012 --crystal 0.45]
# loop : python3 meadow_post.py loop <render.png> <data.png> <frames_dir> [--w 1920 --fps 24 --secs 7]
#
# The render arrives through AgX with a soft bloom (Blender). This adds what a lens and film add:
# halation round the brightest edges, a gentle grade, a vignette and grain. The loop is built from
# the one still and its data pass (depth, blade height, masks): grass sways by a displacement field
# that grows towards the tips and the foreground, the light breathes, and pollen drifts.
# Every motion repeats a whole number of times in the loop, so the last frame runs into the first.
import sys, os, subprocess, math
import numpy as np
from PIL import Image

def read16(path):
    w, h = Image.open(path).size
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb48le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint16).reshape(h, w, 3).astype(np.float32) / 65535.0

def resize(a, w, h):
    a = np.asarray(a, np.float32)
    return np.stack([np.asarray(Image.fromarray(np.ascontiguousarray(a[..., c]), 'F').resize((w, h), Image.BICUBIC))
                     for c in range(a.shape[2])], -1) if a.ndim == 3 else \
        np.asarray(Image.fromarray(np.ascontiguousarray(a), 'F').resize((w, h), Image.BICUBIC))

def box1(a, r, axis):
    if r < 1: return a
    pad = [(0, 0)] * a.ndim; pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode='edge'), axis=axis, dtype=np.float64)
    n = a.shape[axis]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return ((hi - lo) / (2 * r + 1)).astype(np.float32)

def blur(a, sigma):
    # three box passes approximate a gaussian; large sigmas run on a reduced image
    h, w = a.shape[:2]; f = 1
    while sigma / f > 12 and min(h, w) // (f * 2) > 32: f *= 2
    b = resize(a, max(1, w // f), max(1, h // f)) if f > 1 else a
    r = max(1, int(round(sigma / f * 0.85)))
    for _ in range(3):
        b = box1(box1(b, r, 0), r, 1)
    return resize(b, w, h) if f > 1 else b

def lum(a): return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722

def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def lens(img, k=0.012, ca=0.0007):
    # a touch of barrel distortion and lateral colour, as a real lens gives
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx = (xx - w / 2) / (w / 2); ny = (yy - h / 2) / (w / 2)
    r2 = nx * nx + ny * ny
    out = np.empty_like(img)
    for c, f in ((0, 1 + ca), (1, 1.0), (2, 1 - ca)):
        sc = (1 - k * 0.5 + k * r2 * 0.5) * f      # samples slightly outward towards the edge
        out[..., c] = sample_bilinear(img[..., c:c + 1], w / 2 + nx * sc * (w / 2), h / 2 + ny * sc * (w / 2))[..., 0]
    return out

def finish(img, seed=0, grain=0.012, halation=1.0, gain=1.0):
    img = np.asarray(img, np.float32)
    h, w = img.shape[:2]; s = w / 2560
    out = lens(img) * gain
    L = lum(out)
    # halation: warm red bleed round the brightest edges, as in colour negative
    hm = smooth(0.72, 1.0, L)[..., None] * out
    hal = blur(hm, 9 * s) * 0.7 + blur(hm, 30 * s) * 0.3
    out = out + halation * hal * np.array([0.16, 0.06, 0.025], np.float32)
    # grade: a breath of warmth in the highlights, the shadows held a touch cool and lifted
    L = lum(out)[..., None]
    out = out + (1 - L) ** 3 * np.array([0.006, 0.010, 0.022], np.float32)
    out = out * (1 + smooth(0.55, 1.0, L) * np.array([0.02, 0.005, -0.02], np.float32))
    # a soft vignette, as a fast lens gives
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r2 = ((xx - w * 0.52) / (w * 0.62)) ** 2 + ((yy - h * 0.5) / (h * 0.75)) ** 2
    out = out * (1 - 0.14 * np.clip(r2 - 0.35, 0, 1.5)[..., None])
    # grain: fine, slightly soft, strongest in the mid tones
    if grain > 0:
        rng = np.random.default_rng(seed)
        g = rng.normal(0, 1, (h, w)).astype(np.float32)
        g = (g + 0.5 * box1(box1(g, 1, 0), 1, 1) * 3) / 2.0
        L = lum(np.clip(out, 0, 1))
        amp = grain * (0.35 + 1.3 * L * (1 - L) * 2)
        out = out + (g * amp)[..., None] * np.array([1.0, 0.95, 1.05], np.float32)
    return np.clip(out, 0, 1)

def read_data(path, W, H):
    d = resize(read16(path), W, H)
    d = np.where(d <= 0.04045, d / 12.92, ((d + 0.055) / 1.055) ** 2.4)   # stored through the Standard view
    return np.clip(d[..., 0] * 80.0, 0.3, 80.0), np.clip(d[..., 1] * 1.2, 0, 1.2), d[..., 2]

SKY = np.array([0x94, 0xE6, 0xFF], np.float32) / 255

def crystal_true(img, m, k=0.45):
    # a power window on the crystal, as a colourist would: pull its chroma onto sky #94E6FF, keep its light
    cm = smooth(0.85, 0.97, m)
    cm = blur(cm, 0.8 * img.shape[1] / 1920)[..., None]
    L = lum(img)[..., None]
    target = SKY / float(SKY @ np.array([0.2126, 0.7152, 0.0722], np.float32)) * L
    target = np.clip(target, 0, 1)
    tinted = img * (1 - k) + target * k
    return img * (1 - cm) + tinted * cm

def haze(img, depth, m, k=1.0):
    # aerial perspective: distance takes on the warm sky near the sun side
    h, w = img.shape[:2]
    f = (1 - np.exp(-np.maximum(depth - 8, 0) / 90)) * 0.28 * k * (1 - smooth(0.02, 0.2, m) * 0)
    f = np.where(m < 0.02, 0, f)[..., None]
    xx = np.linspace(1, 0, w, dtype=np.float32)[None, :, None]
    col = np.array([1.0, 0.86, 0.78], np.float32) * (0.78 + 0.2 * xx)
    return img * (1 - f) + col * f

def warm_sky(img, m, k=1.0):
    # the grey underside of the cloud band takes on the sun's warmth (peach, never amber)
    sky = (1 - smooth(0.02, 0.2, m))
    sky = blur(sky, 1.5 * img.shape[1] / 1920)
    L = lum(img)
    mx = img.max(-1); mn = img.min(-1); sat = (mx - mn) / (mx + 1e-4)
    w = (sky * smooth(0.2, 0.45, L) * (1 - smooth(0.75, 0.95, L)) * (1 - smooth(0.12, 0.3, sat)) * k)[..., None]
    warm = img * np.array([1.08, 1.0, 0.92], np.float32) + np.array([0.03, 0.02, 0.01], np.float32)
    return img * (1 - w) + warm * w

def motes_and_rain(img, depth, seed=3, motes=160, rain=900, col=(0.58, 0.9, 1.0)):
    # night: soft blue motes of light drifting in the meadow, and fine rain caught in the glow
    h, w = img.shape[:2]; s = w / 1920; rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for i in range(motes):
        cx, cy = rng.uniform(0, w), rng.uniform(0.05 * h, 0.95 * h)
        big = rng.uniform() < 0.18
        r = (rng.uniform(6, 14) if big else rng.uniform(1.2, 3.0)) * s
        R = int(r * 3) + 2
        x0, x1, y0, y1 = int(max(0, cx - R)), int(min(w, cx + R)), int(max(0, cy - R)), int(min(h, cy + R))
        if x1 <= x0 or y1 <= y0: continue
        dd = np.hypot(xx[y0:y1, x0:x1] - cx, yy[y0:y1, x0:x1] - cy)
        spot = np.exp(-(dd / r) ** 2) * (0.25 if big else 1.0) + np.exp(-(dd / (r * 3)) ** 2) * 0.12
        acc[y0:y1, x0:x1] += spot * rng.uniform(0.4, 1.0)
    rn = np.zeros((h, w), np.float32)
    for i in range(rain):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h); L = rng.uniform(18, 45) * s
        n = int(L)
        xs = (cx + np.linspace(0, L * 0.12, n)).astype(int); ys = (cy + np.linspace(0, L, n)).astype(int)
        ok = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
        rn[ys[ok], xs[ok]] += rng.uniform(0.02, 0.06)
    rn = blur(rn, 0.7 * s)
    lit = blur(lum(img), 25 * s)                 # rain shows where there is light behind it
    out = img + acc[..., None] * np.array(col, np.float32) * 0.9 + (rn * (0.4 + 2.5 * lit))[..., None] * np.array([0.8, 0.9, 1.0], np.float32)
    return out

def save8(a, path):
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)

def sample_bilinear(img, x, y):
    h, w = img.shape[:2]
    x = np.clip(x, 0, w - 1.001); y = np.clip(y, 0, h - 1.001)
    x0 = x.astype(np.int32); y0 = y.astype(np.int32); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    a = img[y0, x0]; b = img[y0, x0 + 1]; c = img[y0 + 1, x0]; d = img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

def opt(name, default):
    k = '--' + name
    return type(default)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else default

mode = sys.argv[1]
if mode == 'still':
    img = read16(sys.argv[2])
    if len(sys.argv) > 4 and not sys.argv[4].startswith('--'):
        _, _, m = read_data(sys.argv[4], img.shape[1], img.shape[0])
        img = crystal_true(img, m, opt('crystal', 0.45))
        if '--night' in sys.argv:
            img = motes_and_rain(img, None)
        else:
            dep, _, _ = read_data(sys.argv[4], img.shape[1], img.shape[0])
            img = haze(img, dep, m, opt('haze', 1.0))
            img = warm_sky(img, m, opt('warm', 1.0))
    save8(finish(img, grain=opt('grain', 0.012)), sys.argv[3])

elif mode == 'loop':
    src, data, outdir = sys.argv[2], sys.argv[3], sys.argv[4]
    W = opt('w', 1920); FPS = opt('fps', 24); SECS = opt('secs', 7.0)
    N = int(round(FPS * SECS))
    img = read16(src); H = int(round(img.shape[0] * W / img.shape[1]))
    img = resize(img, W, H)
    depth, hf, m = read_data(data, W, H)
    img = crystal_true(img, m, opt('crystal', 0.45))
    img = haze(img, depth, m, opt('haze', 1.0))
    img = warm_sky(img, m, opt('warm', 1.0))
    grass = smooth(0.3, 0.45, m) * (1 - smooth(0.6, 0.7, m))
    stone = smooth(0.6, 0.72, m)
    s = W / 1920
    # amplitude in pixels: more for the near grass and the tips, little at the stone, nothing on it
    amp = 5.0 * s * np.clip(3.5 / depth, 0.18, 1.6) * np.clip(hf, 0, 1) ** 1.4
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # extend the field a few pixels past the blades so tips can move over sky, then keep the stone still
    wgt = blur(grass, 2.5 * s) + 1e-4
    ampx = blur(amp * grass, 2.5 * s) / wgt
    reach = np.clip(blur(grass, 3 * s) * 1.6, 0, 1) * (1 - np.clip(blur(stone, 1.2 * s) * 1.5, 0, 1))
    ampx = ampx * reach
    TAU = 2 * math.pi
    rng = np.random.default_rng(11)
    # pollen: points of light on closed drifting paths; some near and unfocused, most small
    P = 70
    px0 = rng.uniform(0, W, P); py0 = rng.uniform(0.08 * H, 0.85 * H, P)
    prx = rng.uniform(30, 160, P) * s; pry = rng.uniform(10, 50, P) * s
    pph = rng.uniform(0, TAU, P); pk = rng.choice([1, 1, 1, 2], P)
    psz = np.where(rng.uniform(0, 1, P) < 0.15, rng.uniform(7, 16, P), rng.uniform(1.0, 2.4, P)) * s
    pbr = np.where(psz > 6 * s, rng.uniform(0.04, 0.08, P), rng.uniform(0.25, 0.6, P))
    ptw = rng.integers(1, 4, P)
    sunside = np.clip(1.2 - px0 / W, 0.35, 1.1)
    hi = smooth(0.6, 1.0, lum(img))[..., None] * img
    for f in range(N):
        t = f / N
        ph = TAU * t
        # wind: two travelling gusts and a slow sway, all whole cycles per loop
        wnd = (0.55 * np.sin(TAU * (xx / (700 * s) - yy / (2600 * s)) - ph) +
               0.30 * np.sin(TAU * (xx / (310 * s) + yy / (900 * s)) - 2 * ph + 1.3) +
               0.15 * np.sin(TAU * (xx / (140 * s)) - 3 * ph + 0.4))
        dx = ampx * wnd
        dy = -0.35 * np.abs(dx)
        fr = sample_bilinear(img, xx - dx, yy - dy)
        # light breathing: the sun leans in and eases off a little, more in the highlights
        br = 0.5 + 0.5 * math.sin(ph - 0.6)
        fr = fr * (0.985 + 0.03 * br) + sample_bilinear(hi, xx - dx, yy - dy) * (0.05 * br)
        # pollen
        acc = np.zeros((H, W), np.float32)
        ppx = px0 + prx * np.cos(pk * ph + pph) + 18 * s * np.sin(2 * ph + pph * 2)
        ppy = py0 + pry * np.sin(pk * ph + pph) - 6 * s * np.cos(3 * ph + pph)
        tw = 0.75 + 0.25 * np.sin(ptw * ph + pph * 3)
        for i in range(P):
            r = psz[i]; R = int(r * 2.5) + 2
            cx, cy = ppx[i] % W, ppy[i]
            x0, x1 = int(max(0, cx - R)), int(min(W, cx + R + 1)); y0, y1 = int(max(0, cy - R)), int(min(H, cy + R + 1))
            if x1 <= x0 or y1 <= y0: continue
            gx = xx[y0:y1, x0:x1] - cx; gy = yy[y0:y1, x0:x1] - cy
            dd = np.sqrt(gx * gx + gy * gy)
            if r > 6 * s:   # out-of-focus disc with a soft rim
                spot = smooth(r, r - 1.5 * s, dd) * (0.8 + 0.2 * smooth(r * 0.6, r, dd))
            else:
                spot = np.exp(-(dd / r) ** 2)
            acc[y0:y1, x0:x1] += spot * pbr[i] * tw[i] * sunside[i]
        fr = fr + (acc * (1 - stone * 0.6))[..., None] * np.array([1.0, 0.92, 0.72], np.float32)
        out = finish(fr, seed=1000 + f, grain=opt('grain', 0.008), halation=1.0)
        save8(out, os.path.join(outdir, f'f{f:04d}.png'))
        if f % 24 == 0: print('frame', f, flush=True)
