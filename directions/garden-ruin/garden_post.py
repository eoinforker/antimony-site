# The Garden in the Ruin: stills, the depth map and the seamless loop, from one render and its data pass.
# Plain numpy and Pillow, run with python3 -I.
#
#   still : python3 -I garden_post.py still  <render.png> <render.json> <outdir> [--data <data.png> --hold 0.2]
#           (--hold k: a light hold of the crystal towards sky #94E6FF, 0 to 1; off by default)
#   loop  : python3 -I garden_post.py loop   <render.png> <data.npz> <render.json> <frames_dir> [--w 1920] [--crop phone]
#   depth : python3 -I garden_post.py depth  <data.npz> <out.webp> [--w 1280] [--crop phone]   (lossless WebP)
#
# The data pass (data.npz, linear float16): R depth / 60 m, G still water, B object index / 4 (1 stone, 2 crystal,
# 3 letter). Earlier renders wrote it as a PNG through the sRGB curve; it is now saved linear and exact.
# The loop (8 s, 24 fps, 192 frames) is built from the one still:
#   - motes: dust drifting in the sunbeam, each on its own closed path (whole cycles per loop), lit by the beam,
#     hidden behind anything nearer than it, soft with the lens's depth of field
#   - the light breathes: the shaft and its pool swell and settle by a few percent
#   - the water: a slow shimmer, and two drips from the broken roof setting rings spreading across it
#   - a very few petals falling slowly through the shaft, turning as they fall, lit only inside the beam
# The stone and the crystal never move. Every motion repeats a whole number of times in 8 s.
import sys, os, json, math
import numpy as np
from PIL import Image

def opt(name, default):
    k = '--' + name
    return type(default)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else default

def read_rgb(path):
    return np.asarray(Image.open(path).convert('RGB'), np.float32) / 255.0

def read_data(path):
    # the data pass, linear: R depth / 60 m, G still water, B object index / 4. The render saves it exactly as
    # data.npz (float16); a PNG beside it is the same data written linear (Raw), 8 bits once PIL has read it.
    if path.endswith('.npz'):
        return np.load(path)['data'].astype(np.float32)
    return read16(path)

def read16(path):
    im = Image.open(path)
    a = np.asarray(im)
    if a.dtype != np.uint16:
        a = np.asarray(im.convert('RGB'), np.float32) / 255.0
        return a
    return a.astype(np.float32) / 65535.0

def resize(a, w, h, resample=Image.LANCZOS):
    if a.shape[1] == w and a.shape[0] == h: return a
    chans = [np.asarray(Image.fromarray(a[..., c].astype(np.float32), 'F').resize((w, h), resample)) for c in range(a.shape[2])]
    return np.stack(chans, -1)

def save8(a, path, q=None):
    im = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))
    if q: im.save(path, quality=q)
    elif path.endswith('.webp'): im.save(path, lossless=True, quality=100, method=6)    # depth maps stay exact
    else: im.save(path)

def crop_box(W, H, info, mode):
    if mode != 'phone': return 0, 0, W, H
    cw = int(round(H * 9 / 16))
    # the stone whole and the letter beside it, centred together; if both cannot fit, the stone stays whole
    L_, S_ = info['letter'], info['stone']
    a = min(L_[0], S_[0]) * W; b = max(L_[2], S_[2]) * W
    x0 = (a + b) / 2 - cw / 2
    x0 = min(x0, S_[0] * W - 0.04 * cw)
    x0 = max(x0, S_[2] * W + 0.04 * cw - cw)
    x0 = int(np.clip(x0, 0, W - cw))
    return x0, 0, x0 + cw, H

def sample_bilinear(img, x, y):
    h, w = img.shape[:2]
    x = np.clip(x, 0, w - 1.001); y = np.clip(y, 0, h - 1.001)
    x0 = x.astype(np.int32); y0 = y.astype(np.int32); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    a = img[y0, x0]; b = img[y0, x0 + 1]; c = img[y0 + 1, x0]; d = img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

def _box(a, r, axis):
    if r < 1: return a
    c = np.cumsum(np.pad(a, [(r + 1, r) if i == axis else (0, 0) for i in range(a.ndim)], mode='edge'), axis=axis, dtype=np.float64)
    hi = np.take(c, np.arange(2 * r + 1, c.shape[axis]), axis=axis); lo = np.take(c, np.arange(0, c.shape[axis] - 2 * r - 1), axis=axis)
    return ((hi - lo) / (2 * r + 1)).astype(np.float32)

def blur(a, s):
    # a Gaussian, near enough: three box passes each way
    if s <= 0: return a
    r = max(1, int(round(s * 0.93)))
    for _ in range(3):
        a = _box(_box(a, r, 0), r, 1)
    return a

# ---------------------------------------------------------------- camera geometry (from the render's json)
def camera(info, W, H, box):
    M = np.array(info['cam_matrix'], np.float64)
    R = M[:3, :3]; C = M[:3, 3]
    fpx = info['lens'] / info['sensor'] * info['w']        # focal length in render pixels
    scale = W / (box[2] - box[0])                           # render px to output px (the crop is in render px)
    return R, C, fpx, scale

def rays(info, W, H, box):
    R, C, fpx, scale = camera(info, W, H, box)
    xs = (np.arange(W) + 0.5) / scale + box[0]; ys = (np.arange(H) + 0.5) / scale + box[1]
    X, Y = np.meshgrid(xs - info['w'] / 2, info['h'] / 2 - ys)
    d = np.stack([X, Y, -np.full_like(X, fpx)], -1) @ R.T
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    return C, d

def beam_mask(info, W, H, box, depth_m):
    # how much of each pixel's view ray passes through the sunbeam before it meets a surface
    C, d = rays(info, W, H, box)
    P0 = np.array(info['beam_foot']); u = np.array(info['beam_dir']); u /= np.linalg.norm(u)
    w0 = C - P0
    b = d @ u; dd = d @ w0; e = float(w0 @ u)
    den = np.maximum(1 - b * b, 1e-6)
    tr = (b * e - dd) / den                                 # along the view ray
    tb = (e - b * dd) / den                                 # along the beam
    dist = np.linalg.norm((C + d * tr[..., None]) - (P0 + u * tb[..., None]), axis=-1)
    r = info['beam_r']
    m = np.clip((r - dist) / (0.55 * r), 0, 1) ** 1.5
    m *= (tr > 0) * np.clip((depth_m - tr) / 1.0 + 0.5, 0, 1) * (tb > -0.2)
    return m

def project(info, W, H, box, P):
    R, C, fpx, scale = camera(info, W, H, box)
    q = (P - C) @ R                                         # camera space (x right, y up, -z forward)
    z = -q[:, 2]
    x = (q[:, 0] / z * fpx + info['w'] / 2 - box[0]) * scale
    y = (info['h'] / 2 - q[:, 1] / z * fpx - box[1]) * scale
    return x, y, z, fpx * scale

# ---------------------------------------------------------------- the grade: cool shade, warm light, lifted blacks
def petals_blue(img):
    # warm sun on the pale blue petals reads lilac; hold them to a pale sky blue (flowers only: magenta hues)
    mx = img.max(-1); mn = img.min(-1); c = mx - mn
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    h = np.where(mx == r, ((g - b) / np.maximum(c, 1e-5)) % 6, np.where(mx == g, (b - r) / np.maximum(c, 1e-5) + 2, (r - g) / np.maximum(c, 1e-5) + 4)) / 6
    sat = c / np.maximum(mx, 1e-5)
    m = np.clip((h - 0.72) / 0.06, 0, 1) * np.clip((0.99 - h) / 0.04, 0, 1) * np.clip((sat - 0.12) / 0.15, 0, 1)
    l = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    blue = l[..., None] * np.array([0.80, 1.02, 1.32], np.float32)
    return img * (1 - m[..., None]) + np.clip(blue, 0, 1) * m[..., None]

def grade(img):
    img = petals_blue(img)
    l = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    sh = np.clip(1 - l / 0.35, 0, 1)[..., None] ** 1.5           # shadows
    hi = np.clip((l - 0.45) / 0.5, 0, 1)[..., None]                # highlights
    out = img * (1 - 0.10 * sh) + sh * np.array([0.004, 0.010, 0.024], np.float32)   # blue-black, gently lifted
    out = out * (1 + hi * np.array([0.025, 0.0, -0.035], np.float32))
    lift = np.array([0.022, 0.026, 0.034], np.float32)
    out = lift + out * (1 - lift)
    return np.clip(out, 0, 1)

def obj_index(data):
    return data[..., 2] * 4

def hold_marks(img, data, k=0.0):
    # a light hold of the crystal towards sky #94E6FF (its facets keep their light and dark); k 0 is off.
    # The stone is left exactly as rendered.
    idx = obj_index(data)
    lw = np.array([0.2126, 0.7152, 0.0722], np.float32)
    l = img @ lw
    # the index pass is speckled through glass: close the mask first, then soften its edge
    cm = blur((blur((np.abs(idx - 2) < 0.4).astype(np.float32), 3.0) > 0.35).astype(np.float32), 1.2)
    if cm.max() > 0:
        # read the facets' light from a smoothed luminance, so render grain is not lifted into sparkle
        ls = blur(l * cm, 2.5) / np.maximum(blur(cm, 2.5), 1e-3)
        ref = np.percentile(ls[cm > 0.5], 85)
        t = ls / max(ref, 1e-4)
        sky = np.array([0x94, 0xE6, 0xFF], np.float32) / 255
        held = sky[None, None, :] * (0.25 + 0.75 * np.clip(t, 0, 1)[..., None])
        held = held + np.clip(t - 1, 0, 0.6)[..., None] * (1 - sky)      # the brightest glints go towards white
        a_ = k * cm[..., None]
        img = img * (1 - a_) + np.clip(held, 0, 1) * a_
    return img

# ---------------------------------------------------------------- modes
mode = sys.argv[1]

if mode == 'still':
    src, js, outdir = sys.argv[2:5]
    info = json.load(open(js))
    os.makedirs(outdir, exist_ok=True)
    g_ = grade(read_rgb(src))
    if opt('data', '') and opt('hold', 0.0) > 0:
        d_ = read_data(opt('data', ''))
        g_ = hold_marks(g_, d_ if d_.shape[:2] == g_.shape[:2] else resize(d_, g_.shape[1], g_.shape[0], Image.NEAREST), opt('hold', 0.0))
    img = Image.fromarray((np.clip(g_, 0, 1) * 255 + 0.5).astype(np.uint8))
    img.save(os.path.join(outdir, 'garden-still.png'))
    os.makedirs(outdir, exist_ok=True)
    W, H = img.size
    img.save(os.path.join(outdir, 'garden-still.webp'), quality=86, method=6)
    img.save(os.path.join(outdir, 'garden-still.avif'), quality=62)
    b = crop_box(W, H, info, 'phone')
    ph = img.crop(b).resize((1080, 1920), Image.LANCZOS)
    ph.save(os.path.join(outdir, 'garden-still-phone.webp'), quality=86, method=6)
    ph.save(os.path.join(outdir, 'garden-still-phone.avif'), quality=62)
    ph.save(os.path.join(outdir, 'garden-still-phone.png'))
    print('phone crop', b)

elif mode == 'depth':
    datap, out = sys.argv[2:4]
    data = read_data(datap)
    Hs, Ws = data.shape[:2]
    info = json.load(open(opt('json', '')))
    box = crop_box(Ws, Hs, info, opt('crop', 'desktop'))
    data = data[box[1]:box[3], box[0]:box[2]]
    w = opt('w', 1280); h = int(round(w * data.shape[0] / data.shape[1]))
    depth = np.maximum(data[..., 0] * 60.0, 0.3)
    depth = np.where(data[..., 0] >= 0.999, 60.0, depth)
    disp = np.clip((1.0 / depth - 1 / 60.0) / (1 / 3.0 - 1 / 60.0), 0, 1) ** 0.6
    disp = blur(disp, 1.5)
    wat = blur(data[..., 1], 1.0)
    out_a = np.stack([disp, wat, data[..., 2]], -1)
    save8(resize(out_a, w, h, Image.BILINEAR), out)

elif mode == 'loop':
    src, datap, js, fdir = sys.argv[2:6]
    info = json.load(open(js))
    os.makedirs(fdir, exist_ok=True)
    base = grade(read_rgb(src)); data = read_data(datap)
    Hr, Wr = base.shape[:2]
    if data.shape[:2] != (Hr, Wr): data = resize(data, Wr, Hr, Image.NEAREST)
    box = crop_box(Wr, Hr, info, opt('crop', 'desktop'))
    base = base[box[1]:box[3], box[0]:box[2]]; data = data[box[1]:box[3], box[0]:box[2]]
    W = opt('w', 1920); H = int(round(W * base.shape[0] / base.shape[1]))
    base = resize(base, W, H); data = resize(data, W, H, Image.BILINEAR)
    depth = np.where(data[..., 0] >= 0.999, 200.0, data[..., 0] * 60.0)
    water = np.clip(data[..., 1], 0, 1)
    obj = data[..., 2] * 4
    still = (np.abs(obj - 1) < 0.3) | (np.abs(obj - 2) < 0.3)
    FPS = opt('fps', 24); SECS = opt('secs', 8); N = FPS * SECS
    beam = beam_mask(info, W, H, box, depth)
    # the pool: lit floor and flowers at the beam's foot (bright pixels near the foot)
    lum = base @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    beam_glow = blur(beam, 6)
    pool = np.clip((lum - 0.25) / 0.5, 0, 1) * np.clip(beam_glow * 2, 0, 1)
    breathe_w = np.clip(0.55 * beam_glow + 0.6 * pool, 0, 1)[..., None]
    warm = np.array([1.0, 0.86, 0.66], np.float32)
    # water: screen-space shimmer, smaller with distance; two drips from the roof make rings
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    k_d = np.clip(8.0 / np.maximum(depth, 1.0), 0.15, 1.5)
    wm = blur(water, 1.0)
    drips = [(0.30, 0.86, 0.0, 1), (0.47, 0.80, 0.5, 2)]    # (x, y frame fraction, phase, rings per loop)
    sx = W / 1920.0
    # motes: points in the beam (world space), each drifting on a small closed loop
    rng = np.random.default_rng(5)
    NM = opt('motes', 240)
    P0 = np.array(info['beam_foot']); u = np.array(info['beam_dir']); u /= np.linalg.norm(u)
    a1 = np.cross(u, [0, 0, 1.0]); a1 /= np.linalg.norm(a1); a2 = np.cross(u, a1)
    tt = rng.uniform(0.15, 9.0, NM); rr = info['beam_r'] * np.sqrt(rng.uniform(0, 1, NM)) * 0.95
    th = rng.uniform(0, 2 * np.pi, NM)
    centre = P0 + tt[:, None] * u + (rr * np.cos(th))[:, None] * a1 + (rr * np.sin(th))[:, None] * a2
    amp = rng.uniform(0.05, 0.22, (NM, 3)); cyc = rng.integers(1, 3, (NM, 3)); ph = rng.uniform(0, 2 * np.pi, (NM, 3))
    tw_c = rng.integers(1, 4, NM); tw_p = rng.uniform(0, 2 * np.pi, NM)
    size_w = rng.uniform(0.0012, 0.003, NM)                 # metres
    focus = np.linalg.norm(np.array(info['beam_foot']) - camera(info, W, H, box)[1])
    # petals: each falls once per loop from high in the shaft to the flowers, swaying, fading in high and out low
    NP = opt('petals', 6)
    prng = np.random.default_rng(17)
    p_ph = (np.arange(NP) + prng.uniform(0.1, 0.9, NP)) / NP          # staggered so one is always on its way
    p_r = info['beam_r'] * 0.75 * np.sqrt(prng.uniform(0.05, 1, NP)); p_th = prng.uniform(0, 2 * np.pi, NP)
    p_top = prng.uniform(4.5, 7.0, NP); p_sw = prng.uniform(0.12, 0.3, NP); p_sp = prng.integers(2, 5, NP)
    p_len = prng.uniform(0.016, 0.024, NP)
    for f in range(N):
        t = f / N
        img = base.copy()
        # breathing light (one slow swell per loop), warm in the beam
        g = 0.045 * math.sin(2 * math.pi * t) + 0.015 * math.sin(2 * math.pi * 2 * t + 1.3)
        img = img * (1 + g * breathe_w * warm)
        # water
        if wm.max() > 0:
            dx = 1.1 * sx * k_d * (np.sin(xx * 0.021 / sx / k_d + 2 * np.pi * t * 2) * 0.6 + np.sin(yy * 0.047 / sx / k_d - 2 * np.pi * t * 3) * 0.4)
            dy = 0.9 * sx * k_d * np.sin(yy * 0.033 / sx / k_d + xx * 0.007 / sx + 2 * np.pi * t)
            for (dxp, dyp, dph, n_) in drips:
                tl = (t * n_ + dph) % 1.0
                cx, cy = dxp * W, dyp * H
                r_ = tl * 160 * sx
                dist = np.hypot((xx - cx), (yy - cy) * 3.2)       # flattened by perspective
                ring = np.exp(-((dist - r_) / (10 * sx)) ** 2) * (1 - tl) ** 1.5
                ang_x = (xx - cx) / np.maximum(dist, 1); ang_y = (yy - cy) * 3.2 / np.maximum(dist, 1)
                dx += 4.0 * sx * ring * np.sin((dist - r_) * 0.35 / sx) * ang_x
                dy += 2.0 * sx * ring * np.sin((dist - r_) * 0.35 / sx) * ang_y
            ww = wm * (~still)
            sel = ww > 0.01
            if sel.any():
                ys_, xs_ = np.nonzero(sel)
                warped = sample_bilinear(img, xs_ + dx[sel], ys_ + dy[sel])
                a_ = ww[sel][:, None]
                img[ys_, xs_] = img[ys_, xs_] * (1 - a_) + warped * a_
        # motes
        Pm = centre + amp * np.sin(2 * np.pi * cyc * t + ph)
        px, py, pz, fpx = project(info, W, H, box, Pm)
        tw = 0.6 + 0.4 * np.sin(2 * np.pi * tw_c * t + tw_p) ** 2
        for i in range(NM):
            if pz[i] <= 0.3: continue
            x, y = px[i], py[i]
            if not (2 <= x < W - 2 and 2 <= y < H - 2): continue
            if depth[int(y), int(x)] < pz[i] - 0.05: continue
            bl = beam[int(y), int(x)] if True else 1
            coc = abs(pz[i] - focus) / pz[i] * fpx * 0.022 + 0.6 * sx     # blur radius in px (f/3.2-ish)
            rad = max(size_w[i] * fpx / pz[i], 0.5 * sx) + coc
            inten = 0.6 * tw[i] * (0.4 + 0.6 * bl) * min(1.0, (1.2 * sx / rad) ** 1.2) * 1.6
            R_ = int(math.ceil(rad * 2.2)) + 1
            x0, x1 = int(x) - R_, int(x) + R_ + 1; y0, y1 = int(y) - R_, int(y) + R_ + 1
            if x0 < 0 or y0 < 0 or x1 > W or y1 > H: continue
            gy, gx = np.mgrid[y0:y1, x0:x1]
            k = np.exp(-(((gx - x) ** 2 + (gy - y) ** 2) / (rad * rad)))
            img[y0:y1, x0:x1] += (k * inten)[..., None] * np.array([1.0, 0.9, 0.74], np.float32) * (1 - img[y0:y1, x0:x1]) * 0.9
        # petals
        for i in range(NP):
            ft = (t + p_ph[i]) % 1.0
            z = p_top[i] * (1 - ft) + 0.25 * ft
            alpha = min(1.0, ft / 0.12) * min(1.0, (1 - ft) / 0.1)
            if alpha <= 0: continue
            sway = p_sw[i] * math.sin(2 * math.pi * (2 * t + p_ph[i] * 3))
            on_axis = P0 + u * (z / u[2])
            ang = p_th[i] + 0.6 * math.sin(2 * math.pi * (t + p_ph[i]))
            Pp = on_axis + (p_r[i] * math.cos(ang) + sway) * a1 + p_r[i] * math.sin(ang) * a2
            px_, py_, pz_, fpx_ = project(info, W, H, box, Pp[None, :])
            x, y, zc = px_[0], py_[0], pz_[0]
            if zc <= 0.3 or not (4 <= x < W - 4 and 4 <= y < H - 4): continue
            if depth[int(y), int(x)] < zc - 0.05: continue
            dist_ax = np.linalg.norm(np.cross(Pp - P0, u))
            lit = 1.0 if dist_ax < info['beam_r'] * 0.9 else 0.3
            spin = 2 * math.pi * p_sp[i] * t + p_ph[i] * 7
            flick = 0.45 + 0.55 * abs(math.cos(spin))                      # a turning petal catches the sun
            L_ = max(p_len[i] * fpx_ / zc, 1.2 * sx); Wd = max(L_ * 0.45 * (0.35 + 0.65 * abs(math.sin(spin))), 0.7 * sx)
            th_ = spin * 0.5
            R_ = int(math.ceil(L_ * 1.6)) + 2
            x0, x1 = int(x) - R_, int(x) + R_ + 1; y0, y1 = int(y) - R_, int(y) + R_ + 1
            if x0 < 0 or y0 < 0 or x1 > W or y1 > H: continue
            gy, gx = np.mgrid[y0:y1, x0:x1]
            dx_, dy_ = gx - x, gy - y
            ca, sa = math.cos(th_), math.sin(th_)
            q = ((dx_ * ca + dy_ * sa) / (L_ * 0.5)) ** 2 + ((-dx_ * sa + dy_ * ca) / (Wd * 0.5)) ** 2
            k = np.exp(-q * 1.6) * alpha * lit * flick * 0.85
            img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - k[..., None]) + k[..., None] * np.array([0.98, 0.95, 0.9], np.float32)
        save8(img, os.path.join(fdir, f'f_{f:04d}.jpg'), q=95)
        if f % 24 == 0: print('frame', f, flush=True)
