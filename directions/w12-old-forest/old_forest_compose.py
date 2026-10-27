# The Old Forest: the loop, the stills and the depth map for the page, built from one render and its data pass.
# Run with the system Python (numpy, Pillow) and ffmpeg; no Blender needed:
#   python3 old_forest_compose.py --work <scratch folder with base.png, data.png, frame.json> --out <this folder>
# Writes assets/loop.mp4, assets/loop.webm (8 s, 24 fps, seamless), assets/still.webp|avif (desktop),
# assets/still-phone.webp|avif (a portrait crop centred on the stone), assets/depth.png, assets/frame.json,
# and shots/render-still.png, shots/render-still-phone.png.
#
# The loop (every motion repeats a whole number of times in 8 s, so the last frame runs into the first):
#   - the light shifts: the shafts swell and ebb slowly, a soft travelling change along them
#   - motes of dust turn slowly in the shafts, seen only where the light is
#   - golden leaves fall slowly, turning, hidden behind anything nearer than they are
#   - the ferns stir a little; the high leaves barely
#   - the stone, the crystal and the letter hold perfectly still
import argparse, json, os, subprocess
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('--work', required=True); ap.add_argument('--out', default=os.path.dirname(os.path.abspath(__file__)))
ap.add_argument('--w', type=int, default=1920); ap.add_argument('--secs', type=float, default=8.0); ap.add_argument('--fps', type=int, default=24)
ap.add_argument('--crf264', type=int, default=24); ap.add_argument('--crf9', type=int, default=36)
ap.add_argument('--frames', type=int, default=0, help='only this many frames (testing)')
A = ap.parse_args()
os.makedirs(os.path.join(A.out, 'assets'), exist_ok=True); os.makedirs(os.path.join(A.out, 'shots'), exist_ok=True)
rng = np.random.default_rng(5)
SKY = np.array([0x94, 0xE6, 0xFF], np.float32) / 255

def load_rgb(path, bits16=False):
    w, h = Image.open(path).size
    fmt, dt, mx = ('rgb48le', np.uint16, 65535.0) if bits16 else ('rgb24', np.uint8, 255.0)
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', fmt, '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dt).reshape(h, w, 3).astype(np.float32) / mx

def resize(a, w, h):
    ch = [np.asarray(Image.fromarray(a[..., i]).resize((w, h), Image.BICUBIC if a.shape[1] < w else Image.LANCZOS)) for i in range(a.shape[2])]
    return np.stack(ch, 2)

def blur(a, r):
    r = max(1, int(r))
    for _ in range(3):
        for ax in (0, 1):
            pad = [(r + 1, r) if i == ax else (0, 0) for i in range(a.ndim)]
            c = np.cumsum(np.pad(a, pad, mode='edge'), axis=ax, dtype=np.float32); n = a.shape[ax]
            a = (np.take(c, range(2 * r + 1, 2 * r + 1 + n), axis=ax) - np.take(c, range(0, n), axis=ax)) / (2 * r + 1)
    return a

def smooth_noise(h, w, cell, seed):
    g = np.random.default_rng(seed).random((h // cell + 3, w // cell + 3)).astype(np.float32)
    im = Image.fromarray(g).resize(((w // cell + 3) * cell, (h // cell + 3) * cell), Image.BICUBIC)
    return np.asarray(im)[cell:cell + h, cell:cell + w]

def sample(img, X, Y):
    """bilinear lookup of img at float pixel coordinates"""
    h, w = img.shape[:2]
    X = np.clip(X, 0, w - 1.001); Y = np.clip(Y, 0, h - 1.001)
    x0 = X.astype(np.int32); y0 = Y.astype(np.int32); fx = (X - x0)[..., None]; fy = (Y - y0)[..., None]
    a = img[y0, x0]; b = img[y0, x0 + 1]; c = img[y0 + 1, x0]; d = img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

info = json.load(open(os.path.join(A.work, 'frame.json')))
BASE = load_rgb(os.path.join(A.work, 'base.png'))
DATA = load_rgb(os.path.join(A.work, 'data.png'), bits16=True)
H0, W0 = BASE.shape[:2]

class Layers:
    """everything the frame function needs, at one resolution"""
    def __init__(s, w):
        s.w = w; s.h = int(round(w * H0 / W0)); k = w / 1920.0; s.k = k
        s.F = resize(BASE, s.w, s.h) if w != W0 else BASE.copy()
        D = resize(DATA, s.w, s.h) if w != W0 else DATA
        s.disp = D[..., 0]; s.plant = np.clip(D[..., 1], 0, 1); code = D[..., 2]
        s.still = blur((code > 0.3).astype(np.float32)[..., None], 6 * k)[..., 0]          # stone, crystal, paper: no motion
        s.still = np.clip(s.still * 3, 0, 1)
        s.crystal = blur((code > 0.9).astype(np.float32)[..., None], 3 * k)[..., 0]
        pl = blur(s.plant[..., None], 3 * k)[..., 0]
        near = np.clip(blur(s.disp[..., None], 4 * k)[..., 0] / 0.5, 0, 1)
        s.sway_w = pl * (0.25 + 0.75 * near) * (1 - s.still)
        yy, xx = np.mgrid[0:s.h, 0:s.w].astype(np.float32); s.xx, s.yy = xx, yy
        lum = s.F @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        s.phase = smooth_noise(s.h, s.w, int(60 * k), 3)
        s.ph2 = smooth_noise(s.h, s.w, int(140 * k), 4)
        s.light = blur(lum[::4, ::4, None], 10 * k)[..., 0].repeat(4, 0).repeat(4, 1)[:s.h, :s.w]
        s.shaft = np.clip((blur(lum[..., None], 3 * k)[..., 0] - 0.55) * 2.5, 0, 1) * (1 - s.still)
        s.light2 = np.clip((blur(lum[..., None], 2 * k)[..., 0] - 0.45) * 1.8, 0, 1)
        s.motes = make_motes(s); s.rain = make_rain(s)

def make_motes(s):
    n = 220; k = s.k
    m = dict(x=rng.uniform(0, s.w, n), y=rng.uniform(0.02, 0.85, n) * s.h, d=0.03 + 0.85 * rng.uniform(0, 1, n) ** 2.5)
    m['r'] = (0.9 + 7 * m['d'] ** 1.5) * k
    m['a'] = 0.5 + 0.5 * rng.random(n)
    m['ax'] = (6 + 26 * m['d']) * k * rng.uniform(0.5, 1, n); m['ay'] = (8 + 30 * m['d']) * k * rng.uniform(0.5, 1, n)
    m['k1'] = rng.integers(1, 3, n); m['k2'] = rng.integers(1, 3, n); m['k3'] = rng.integers(1, 4, n)
    m['p1'], m['p2'], m['p3'] = rng.uniform(0, 2 * np.pi, (3, n))
    m['col'] = np.tile(np.array([1.0, 0.93, 0.76], np.float32), (n, 1))
    return m

def make_rain(s):
    """here: the falling leaves (each crosses the frame once a loop, turning as it goes)"""
    n = 16; k = s.k
    L = dict(x=rng.uniform(0.05, 0.95, n) * s.w, ph=rng.uniform(0, 1, n), d=0.05 + 0.6 * rng.uniform(0, 1, n) ** 1.8)
    L['size'] = (5 + 16 * L['d']) * k; L['sw'] = (20 + 60 * L['d']) * k * rng.uniform(0.6, 1, n)
    L['kf'] = rng.integers(1, 4, n); L['ks'] = rng.integers(1, 3, n); L['p'] = rng.uniform(0, 2 * np.pi, n)
    L['col'] = np.array([[0.98, 0.72, 0.28], [0.92, 0.62, 0.20], [1.0, 0.80, 0.40]], np.float32)[rng.integers(0, 3, n)]
    return L

def frame(s, t, rain=True, motes=True):
    TW = 2 * np.pi
    xx, yy = s.xx, s.yy; k = s.k
    wv = (0.6 * np.sin(TW * (xx / (500 * k) - t) + s.ph2 * 2.0) + 0.4 * np.sin(TW * (xx / (190 * k) + yy / (320 * k) - 2 * t)))
    dx = 2.6 * k * s.sway_w * wv; dy = 0.9 * k * s.sway_w * np.sin(TW * (xx / (280 * k) - t) + 1.3)
    F = sample(s.F, xx - dx, yy - dy)
    # the light shifts: shafts swell and ebb, a slow change travelling along them
    F = F * (1 + (s.shaft * (0.075 * np.sin(TW * (t + xx / (1400 * k) - yy / (2600 * k))) + 0.035 * np.sin(TW * 2 * t + s.phase * 3)))[..., None])
    F = F * (1 + 0.02 * np.sin(TW * t + 0.6))
    add = np.zeros_like(F)
    if motes:
        m = s.motes
        for i in range(len(m['x'])):
            x = (m['x'][i] + m['ax'][i] * np.sin(TW * m['k1'][i] * t + m['p1'][i])) % s.w
            y = m['y'][i] + m['ay'][i] * np.sin(TW * m['k2'][i] * t + m['p2'][i])
            xi, yi = int(x), int(np.clip(y, 0, s.h - 1))
            if s.disp[yi, xi] > m['d'][i] + 0.01: continue
            lit = s.light2[yi, xi]
            if lit < 0.02: continue
            r = m['r'][i]; R = int(r * 4 + 2)
            x0, x1, y0, y1 = max(0, xi - R), min(s.w, xi + R + 1), max(0, yi - R), min(s.h, yi + R + 1)
            if x0 >= x1 or y0 >= y1: continue
            gx = xx[y0:y1, x0:x1] - x; gy = yy[y0:y1, x0:x1] - y; d2 = (gx * gx + gy * gy) / (r * r)
            spr = np.exp(-d2 * 1.4) + 0.15 * np.exp(-d2 * 0.25)
            tw = 0.65 + 0.35 * np.sin(TW * m['k3'][i] * t + m['p3'][i])
            add[y0:y1, x0:x1] += (spr * m['a'][i] * tw * lit * 1.6)[..., None] * m['col'][i]
    if rain:
        L = s.rain
        for i in range(len(L['x'])):
            u = (t + L['ph'][i]) % 1.0
            sz = L['size'][i]; y = -2 * sz + u * (s.h + 4 * sz)
            x = L['x'][i] + L['sw'][i] * np.sin(TW * L['ks'][i] * t + L['p'][i])
            xi, yi = int(np.clip(x, 0, s.w - 1)), int(np.clip(y, 0, s.h - 1))
            if 0 <= y < s.h and s.disp[yi, xi] > L['d'][i] + 0.01: continue
            R = int(sz * 1.6 + 2)
            x0, x1, y0, y1 = max(0, int(x) - R), min(s.w, int(x) + R + 1), max(0, int(y) - R), min(s.h, int(y) + R + 1)
            if x0 >= x1 or y0 >= y1: continue
            ang = L['p'][i] + TW * L['kf'][i] * t; flip = 0.25 + 0.75 * abs(np.cos(TW * L['kf'][i] * t + L['p'][i] * 0.7))
            gx = xx[y0:y1, x0:x1] - x; gy = yy[y0:y1, x0:x1] - y
            ca, sa = np.cos(ang), np.sin(ang); u_ = gx * ca + gy * sa; v_ = -gx * sa + gy * ca
            e = (u_ / sz) ** 2 + (v_ / (sz * 0.45 * flip + 0.6)) ** 2
            al = np.clip((1.0 - e) * 2.2, 0, 1) * (0.55 + 0.45 * flip)
            blurk = L['d'][i] > 0.4
            if blurk: al = al * 0.75
            lit = 0.45 + 1.1 * s.light2[min(s.h - 1, max(0, yi)), xi]
            col = np.clip(L['col'][i] * lit, 0, 1)
            F[y0:y1, x0:x1] = F[y0:y1, x0:x1] * (1 - al[..., None]) + col * al[..., None]
    F = 1 - (1 - np.clip(F, 0, 1)) * (1 - np.clip(add, 0, 1))
    return np.clip(F, 0, 1)

def to8(a): return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
def save(a, path, **kw): Image.fromarray(to8(a)).save(path, **kw); print('wrote', path)

# ---------------------------------------------------------------- stills (frame 0) at full size
SL = Layers(W0)
still = frame(SL, 0.0)
save(still, os.path.join(A.out, 'shots', 'render-still.png'))
Image.fromarray(to8(resize(still, 1920, 1080) if W0 > 1920 else still)).save(os.path.join(A.out, 'assets', 'still.webp'), quality=82, method=6)
st = info['stone']; cx = (st[0] + st[2]) / 2 * W0
cw = int(H0 * 9 / 16); x0 = int(np.clip(cx - cw / 2, 0, W0 - cw))
phone = still[:, x0:x0 + cw]
save(phone, os.path.join(A.out, 'shots', 'render-still-phone.png'))
Image.fromarray(to8(resize(phone, 810, 1440) if phone.shape[1] > 810 else phone)).save(os.path.join(A.out, 'assets', 'still-phone.webp'), quality=82, method=6)
for nm in ('still', 'still-phone'):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', os.path.join(A.out, 'assets', nm + '.webp'), '-c:v', 'libaom-av1',
                    '-still-picture', '1', '-crf', '30', '-cpu-used', '6', os.path.join(A.out, 'assets', nm + '.avif')], check=True)
# depth for the breathing layer: disparity, smoothed so the warp never tears
dep = blur(resize(DATA, 960, 540)[..., :1], 3)[..., 0]
Image.fromarray((np.clip(dep, 0, 1) * 255).astype(np.uint8)).save(os.path.join(A.out, 'assets', 'depth.png'))
info['phone_crop_x'] = x0 / W0; info['phone_crop_w'] = cw / W0
json.dump(info, open(os.path.join(A.out, 'assets', 'frame.json'), 'w'), indent=1)
del SL

# ---------------------------------------------------------------- the loop
L = Layers(A.w); n = int(A.secs * A.fps)
if A.frames: n = A.frames
enc = [subprocess.Popen(['nice', '-n', '10', 'ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{L.w}x{L.h}', '-r', str(A.fps), '-i', '-',
                         '-c:v', 'libx264', '-preset', 'slow', '-crf', str(A.crf264), '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an',
                         os.path.join(A.out, 'assets', 'loop.mp4')], stdin=subprocess.PIPE),
       subprocess.Popen(['nice', '-n', '10', 'ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{L.w}x{L.h}', '-r', str(A.fps), '-i', '-',
                         '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', str(A.crf9), '-deadline', 'good', '-cpu-used', '4', '-row-mt', '1', '-pix_fmt', 'yuv420p', '-an',
                         os.path.join(A.out, 'assets', 'loop.webm')], stdin=subprocess.PIPE)]
for i in range(n):
    fr = to8(frame(L, i / n)).tobytes()
    for e in enc: e.stdin.write(fr)
    if i % 24 == 0: print('frame', i, flush=True)
for e in enc: e.stdin.close(); e.wait()
for f in ('loop.mp4', 'loop.webm', 'still.webp', 'still.avif', 'still-phone.webp', 'still-phone.avif', 'depth.png'):
    p = os.path.join(A.out, 'assets', f); print(f, round(os.path.getsize(p) / 1e6, 2), 'MB')
