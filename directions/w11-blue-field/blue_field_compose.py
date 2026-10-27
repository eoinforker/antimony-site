# The Blue Field: the loop, the stills and the depth map for the page, built from one render and its data pass.
# Run with the system Python (numpy, Pillow) and ffmpeg; no Blender needed:
#   python3 blue_field_compose.py --work <scratch folder with base.png, data.png, frame.json> --out <this folder>
# Writes assets/loop.mp4, assets/loop.webm (8 s, 24 fps, seamless), assets/still.webp|avif (desktop),
# assets/still-phone.webp|avif (a portrait crop centred on the stone), assets/depth.png, assets/frame.json,
# and shots/render-still.png, shots/render-still-phone.png.
#
# The loop (every motion repeats a whole number of times in 8 s, so the last frame runs into the first):
#   - blooms sway: a smooth displacement from travelling waves, weighted by the plant mask and by nearness;
#     the stone, the crystal and the paper hold perfectly still
#   - the petals' glow breathes slowly, each patch on its own phase
#   - motes of sky light drift on small closed paths, hidden behind anything nearer than they are
#   - fine rain in two layers, brighter where the light is
#   - the crystal's light swells a little
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
        # the crystal held to sky #94E6FF: its light and shade kept, its colour pulled onto the brand's sky
        lumF = s.F @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        held = np.clip(lumF[..., None] / float(SKY @ np.array([0.2126, 0.7152, 0.0722], np.float32)) * SKY, 0, 1)
        s.F = s.F * (1 - 0.8 * s.crystal[..., None]) + held * (0.8 * s.crystal[..., None])
        pl = blur(s.plant[..., None], 3 * k)[..., 0]
        near = np.clip(blur(s.disp[..., None], 4 * k)[..., 0] / 0.5, 0, 1)
        s.sway_w = pl * (0.25 + 0.75 * near) * (1 - s.still)
        yy, xx = np.mgrid[0:s.h, 0:s.w].astype(np.float32); s.xx, s.yy = xx, yy
        lum = s.F @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        blue = np.clip((s.F[..., 2] - s.F[..., 0]) * 3, 0, 1)
        s.petal = np.clip((lum - 0.22) * 3.5, 0, 1) * blue * pl
        s.phase = smooth_noise(s.h, s.w, int(60 * k), 3)
        s.ph2 = smooth_noise(s.h, s.w, int(140 * k), 4)
        s.light = blur(lum[::4, ::4, None], 10 * k)[..., 0].repeat(4, 0).repeat(4, 1)[:s.h, :s.w]
        s.motes = make_motes(s); s.rain = make_rain(s)

def make_motes(s):
    n = 110; k = s.k
    m = dict(x=rng.uniform(0, s.w, n), y=rng.uniform(0.08, 0.92, n) * s.h, d=rng.uniform(0, 1, n) ** 2.2)
    m['d'] = 0.02 + 0.9 * m['d']                       # their disparity: most far, a few close to the lens
    m['r'] = (1.2 + 13 * m['d'] ** 1.6) * k          # radius: near ones are soft discs of light
    m['a'] = (0.9 + 0.7 * rng.random(n)) * (1.0 - 0.5 * m['d'])
    m['ax'] = (8 + 40 * m['d']) * k * rng.uniform(0.5, 1, n); m['ay'] = (6 + 30 * m['d']) * k * rng.uniform(0.5, 1, n)
    m['k1'] = rng.integers(1, 3, n); m['k2'] = rng.integers(1, 3, n); m['k3'] = rng.integers(1, 4, n)
    m['p1'], m['p2'], m['p3'] = rng.uniform(0, 2 * np.pi, (3, n))
    m['col'] = np.where(rng.random(n)[:, None] < 0.8, np.array([0.25, 0.68, 1.0]), np.array([0.6, 0.9, 1.0])).astype(np.float32)
    return m

def make_rain(s):
    layers = []
    for count, (l0, l1), amp, scroll, seed in ((int(2600 * s.k ** 2), (16, 34), 0.45, 4, 1), (int(900 * s.k ** 2), (55, 110), 0.8, 9, 2)):
        g = np.random.default_rng(seed); tex = np.zeros((s.h, s.w), np.float32)
        xs = g.uniform(0, s.w, count); ys = g.uniform(0, s.h, count); ls = g.uniform(l0, l1, count) * s.k
        for t in np.linspace(0, 1, int(l1 * s.k)):
            xi = (xs + t * ls * 0.10).astype(int) % s.w; yi = (ys + t * ls).astype(int) % s.h
            ok = t * l1 * s.k <= ls
            np.add.at(tex, (yi[ok], xi[ok]), np.sin(np.pi * t) * g.uniform(0.4, 1.0, ok.sum()))
        tex = blur(tex[..., None], 1)[..., 0]
        layers.append((tex, amp, scroll))
    return layers

def frame(s, t, rain=True, motes=True):
    TW = 2 * np.pi
    xx, yy = s.xx, s.yy; k = s.k
    # sway: travelling waves across the field
    wv = (0.6 * np.sin(TW * (xx / (420 * k) - t) + s.ph2 * 2.0) + 0.4 * np.sin(TW * (xx / (170 * k) + yy / (300 * k) - 2 * t)))
    dx = 5.5 * k * s.sway_w * wv; dy = 1.4 * k * s.sway_w * np.sin(TW * (xx / (260 * k) - t) + 1.3)
    F = sample(s.F, xx - dx, yy - dy)
    # the petals breathe
    F = F * (1 + (0.11 * s.petal * np.sin(TW * (t * 2 + s.phase)))[..., None])
    # the crystal's light swells a little; the whole light by about two percent
    F = F + (0.035 * (0.5 + 0.5 * np.sin(TW * t)) * s.crystal)[..., None] * SKY
    F = F * (1 + 0.018 * np.sin(TW * t + 0.6))
    add = np.zeros_like(F)
    if motes:
        m = s.motes
        for i in range(len(m['x'])):
            x = (m['x'][i] + m['ax'][i] * np.sin(TW * m['k1'][i] * t + m['p1'][i])) % s.w
            y = m['y'][i] + m['ay'][i] * np.sin(TW * m['k2'][i] * t + m['p2'][i])
            xi, yi = int(x), int(np.clip(y, 0, s.h - 1))
            if s.disp[yi, xi] > m['d'][i] + 0.01: continue        # something nearer stands in front
            r = m['r'][i]; R = int(r * 3 + 2)
            R = int(R * 1.8)
            x0, x1, y0, y1 = max(0, xi - R), min(s.w, xi + R + 1), max(0, yi - R), min(s.h, yi + R + 1)
            if x0 >= x1 or y0 >= y1: continue
            gx = xx[y0:y1, x0:x1] - x; gy = yy[y0:y1, x0:x1] - y
            d2 = (gx * gx + gy * gy) / (r * r)
            spr = (np.exp(-d2 * 1.6) + 0.22 * np.exp(-d2 * 0.18)) if m['d'][i] < 0.35 else np.clip(1.15 - d2 ** 3, 0, 1) * 0.45 + np.exp(-d2 * 2) * 0.25 + 0.12 * np.exp(-d2 * 0.3)
            tw = 0.7 + 0.3 * np.sin(TW * m['k3'][i] * t + m['p3'][i])
            add[y0:y1, x0:x1] += (spr * m['a'][i] * tw)[..., None] * m['col'][i]
    if rain:
        for tex, amp, scroll in s.rain:
            off = int(round(t * scroll * s.h)) % s.h
            r_ = np.roll(tex, off, axis=0)
            add += (r_ * amp * 0.07 * (0.3 + 2.2 * s.light))[..., None] * np.array([0.72, 0.86, 1.0], np.float32)
    F = 1 - (1 - np.clip(F, 0, 1)) * (1 - np.clip(add, 0, 1))      # screen: light adds without clipping hard
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
