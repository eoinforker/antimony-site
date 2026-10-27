# Dawn over the Plate: stills and the seamless loop, composed from one Cycles render and its data passes.
# No per-frame renders: the flowers move by a small warp weighted by the plant pass (stronger when near),
# the mist in the air breathes, and a few motes drift in the low sun. The mark is held perfectly still.
# The grade (halation, vignette, grain) is laid over everything.
#
# Run: python3 dawn_compose.py --beauty beauty.png --passes passes.png --out <assets dir> --shots <shots dir> [--frames 144]
import argparse, os, subprocess, sys
import numpy as np
from PIL import Image, ImageFilter

ap = argparse.ArgumentParser()
ap.add_argument('--beauty', required=True); ap.add_argument('--passes', required=True)
ap.add_argument('--out', required=True); ap.add_argument('--shots', required=True)
ap.add_argument('--frames', type=int, default=144); ap.add_argument('--fps', type=int, default=24)
ap.add_argument('--loop-w', type=int, default=1920); ap.add_argument('--crf', type=int, default=24)
ap.add_argument('--vp9-crf', type=int, default=36); ap.add_argument('--still-only', action='store_true')
ap.add_argument('--tone', type=float, default=0.0)
A = ap.parse_args()
os.makedirs(A.out, exist_ok=True); os.makedirs(A.shots, exist_ok=True)

def read16(path):
    # 16-bit PNG through ffmpeg, so no precision is lost on the way in
    w, h = Image.open(path).size
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb48le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint16).reshape(h, w, 3).astype(np.float32) / 65535.0

def resize(a, w, h):
    return np.stack([np.asarray(Image.fromarray(a[..., c]).resize((w, h), Image.LANCZOS)) for c in range(a.shape[2])], -1)

def blur(ch, r, lo=0.0, hi=1.0):
    # PIL blurs 8-bit planes only: map the range in and out (enough for soft glows and grain)
    u = Image.fromarray((np.clip((ch - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
    return np.asarray(u).astype(np.float32) / 255 * (hi - lo) + lo

BEAUTY = read16(A.beauty); PASS = read16(A.passes)
# the passes PNG carries the sRGB curve (its 'Standard' view): undo it so depth is in metres and the tags are their values
PASS = np.where(PASS > 0.04045, ((PASS + 0.055) / 1.055) ** 2.4, PASS / 12.92).astype(np.float32)
H0, W0, _ = BEAUTY.shape

def grade_static(a):
    """Halation and vignette: computed once per size (the picture barely moves)."""
    h, w, _ = a.shape
    lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    hi = np.clip((lum - 0.72) / 0.28, 0, 1)
    hal = (0.55 * blur(hi, w * 0.012) + 0.45 * blur(hi, w * 0.04))[..., None] * np.array([1.0, 0.42, 0.30], np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 * 0.85 + ((yy - h / 2) / (h / 2)) ** 2 * 0.6)
    vig = (1 - 0.32 * np.clip(d - 0.35, 0, 1) ** 1.6)[..., None]
    return hal, vig

def finish(a, hal, vig, rng, grain=0.075):
    a = a + 0.22 * hal * (1 - a)
    if A.tone > 0:
        # one palette: the shadows lean rose, the light leans gold
        l_ = np.clip(a @ np.array([0.2126, 0.7152, 0.0722], np.float32), 0, 1)[..., None]
        a = a + A.tone * ((1 - l_) ** 2 * np.array([0.035, 0.0, 0.02], np.float32) + l_ ** 2 * np.array([0.03, 0.012, -0.03], np.float32))
    a = a * vig
    lum = np.clip(a @ np.array([0.2126, 0.7152, 0.0722], np.float32), 0, 1)
    g = rng.normal(0, 1, lum.shape).astype(np.float32)
    g = blur(g, 0.6, -3.0, 3.0)
    a = a + (grain * 0.25 * g * (0.35 + 0.65 * 4 * lum * (1 - lum)))[..., None]
    return np.clip(a, 0, 1)

def to8(a): return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)

# where the mark is: the phone crop is centred on it and the warp never touches it
mk = PASS[..., 1] > 0.9          # the stone only (the note is tagged 0.45, its rock 0.3)
ys, xs = np.nonzero(mk)
mark_cx = float(xs.mean()) / W0 if len(xs) else 0.6
mark_box = (xs.min() / W0, ys.min() / H0, xs.max() / W0, ys.max() / H0) if len(xs) else None
print('mark centre x', round(mark_cx, 3), 'box', mark_box)

def phone_crop(a):
    h, w, _ = a.shape
    cw = int(round(h * 9 / 16)) // 2 * 2
    x0 = int(np.clip(mark_cx * w - cw * 0.5, 0, w - cw))
    return a[:, x0:x0 + cw]

def save_stills(a, name):
    im = Image.fromarray(to8(a))
    im.save(os.path.join(A.out, name + '.webp'), quality=86, method=6)
    im.save(os.path.join(A.out, name + '.avif'), quality=62)

rng = np.random.default_rng(5)
hal, vig = grade_static(BEAUTY)
still = finish(BEAUTY, hal, vig, rng)
Image.fromarray(to8(still)).save(os.path.join(A.shots, 'render-still.png'))
s2560 = Image.fromarray(to8(still))
save_stills(np.asarray(s2560.resize((2560, 1440), Image.LANCZOS)).astype(np.float32) / 255, 'dawn-still')
ph = phone_crop(still)
Image.fromarray(to8(ph)).save(os.path.join(A.shots, 'render-still-phone.png'))
save_stills(ph, 'dawn-still-phone')
print('stills written')
if A.still_only: sys.exit(0)

# ---------------------------------------------------------------- the loop
W = A.loop_w; H = int(round(W * 9 / 16)) // 2 * 2
src = resize(BEAUTY, W, H); ps = resize(PASS, W, H)
plant = blur(ps[..., 0], 1.0); mark = blur((ps[..., 1] > 0.2).astype(np.float32), 6) > 0.02
# the note's lifted leaf: it lifts and settles in the air, more towards its free edge
notem = ((ps[..., 1] > 0.38) & (ps[..., 1] < 0.6)).astype(np.float32)
if notem.any():
    nys = np.nonzero(notem.any(1))[0]; ny0, ny1 = nys.min(), nys.max()
    yy_ = np.arange(H, dtype=np.float32)[:, None]
    flut = blur(notem, 1.0) * np.clip((ny1 - yy_) / max(1, ny1 - ny0), 0, 1) ** 1.5 * (W / 1920)
else:
    flut = None
depth = np.maximum(ps[..., 2] * 400.0, 0.5)
amp = np.clip(9.0 / depth, 0.2, 4.0) * (W / 1920) * plant
amp[mark] = 0
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
hal_l, vig_l = grade_static(src)
# mist: a soft field that drifts by exactly one tile per loop, weighted to the far air
far = np.clip((depth - 60) / 300, 0, 1) * (1 - plant)
far[mark] = 0
def tile_noise(seed, tw, th):
    r = np.random.default_rng(seed)
    n = np.zeros((th, tw), np.float32)
    for k in range(6):
        fx, fy = r.integers(1, 4), r.integers(1, 3)
        ph = r.uniform(0, 6.283)
        u = np.arange(tw, dtype=np.float32)[None, :] / tw; v = np.arange(th, dtype=np.float32)[:, None] / th
        n += np.sin(2 * np.pi * (fx * u + fy * v) + ph) / (k + 1)
    return n / 2.5
TN = tile_noise(9, W, H)
# motes: small seeds of light drifting on closed paths, brighter on the sun's side
rm = np.random.default_rng(21); NM = 46
mx0 = rm.uniform(0.05, 0.95, NM) * W; my0 = rm.uniform(0.25, 0.72, NM) * H
mrx = rm.uniform(6, 26, NM) * W / 1920; mry = rm.uniform(4, 16, NM) * W / 1920
mk_ = rm.integers(1, 3, NM); mph = rm.uniform(0, 6.283, NM)
msz = rm.uniform(0.7, 1.8, NM) * W / 1920; mbr = rm.uniform(0.12, 0.35, NM)
sun_side = np.clip(1.2 - mx0 / W, 0.3, 1.0)

def frame(t):
    ph = 2 * np.pi * t / A.frames
    wave = 0.62 * np.sin(ph - xx / W * 9.0 + yy / H * 2.0) + 0.38 * np.sin(2 * ph - xx / W * 17.0 + 1.3)
    dx = amp * wave; dy = 0.25 * amp * np.sin(ph * 1 - xx / W * 11.0 + 0.7)
    if flut is not None:
        g_ = 0.6 + 0.4 * np.sin(ph * 2 + 0.4)
        dy = dy + flut * 1.6 * g_ * np.sin(ph * 3 + 1.1); dx = dx + flut * 0.7 * np.sin(ph * 2 + 2.0)
    sx = np.clip(xx - dx, 0, W - 1.001); sy = np.clip(yy - dy, 0, H - 1.001)
    x0 = sx.astype(np.int32); y0 = sy.astype(np.int32); fx = (sx - x0)[..., None]; fy = (sy - y0)[..., None]
    a = (src[y0, x0] * (1 - fx) * (1 - fy) + src[y0, x0 + 1] * fx * (1 - fy)
         + src[y0 + 1, x0] * (1 - fx) * fy + src[y0 + 1, x0 + 1] * fx * fy)
    shift = int(round(W * t / A.frames))
    n = np.roll(TN, shift, axis=1)
    a = a * (1 + 0.035 * n * far)[..., None]
    # motes
    px = mx0 + mrx * np.cos(mk_ * ph + mph); py = my0 + mry * np.sin(mk_ * ph + mph * 1.3) - 6 * np.sin(ph + mph)
    add = np.zeros((H, W), np.float32)
    for i in range(NM):
        r = int(msz[i] * 3) + 2; cx, cy = int(px[i]), int(py[i])
        if r < cx < W - r and r < cy < H - r and not mark[cy, cx]:
            gy, gx = np.mgrid[-r:r + 1, -r:r + 1]
            add[cy - r:cy + r + 1, cx - r:cx + r + 1] += mbr[i] * sun_side[i] * (0.6 + 0.4 * np.sin(ph * mk_[i] + mph[i])) * np.exp(-(gx ** 2 + gy ** 2) / (2 * msz[i] ** 2))
    a = a + add[..., None] * np.array([1.0, 0.9, 0.8], np.float32) * (1 - a)
    return finish(a, hal_l, vig_l, np.random.default_rng(1000 + t), grain=0.04)

def enc(path, args, w, h):
    return subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(A.fps), '-i', '-'] + args + [path], stdin=subprocess.PIPE)
pw = int(round(H * 9 / 16)) // 2 * 2
x0p = int(np.clip(mark_cx * W - pw * 0.5, 0, W - pw))
outs = [
    (enc(os.path.join(A.out, 'dawn-loop.mp4'), ['-c:v', 'libx264', '-preset', 'slow', '-crf', str(A.crf), '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an'], W, H), None),
    (enc(os.path.join(A.out, 'dawn-loop.webm'), ['-c:v', 'libvpx-vp9', '-crf', str(A.vp9_crf), '-b:v', '0', '-row-mt', '1', '-pix_fmt', 'yuv420p', '-an'], W, H), None),
    (enc(os.path.join(A.out, 'dawn-loop-phone.mp4'), ['-c:v', 'libx264', '-preset', 'slow', '-crf', str(A.crf), '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an'], pw, H), x0p),
    (enc(os.path.join(A.out, 'dawn-loop-phone.webm'), ['-c:v', 'libvpx-vp9', '-crf', str(A.vp9_crf), '-b:v', '0', '-row-mt', '1', '-pix_fmt', 'yuv420p', '-an'], pw, H), x0p),
]
for t in range(A.frames):
    f8 = to8(frame(t))
    for p, xo in outs:
        p.stdin.write((f8 if xo is None else np.ascontiguousarray(f8[:, xo:xo + pw])).tobytes())
    if t % 24 == 0: print('frame', t, flush=True)
for p, _ in outs:
    p.stdin.close(); p.wait()
for f in ('dawn-loop.mp4', 'dawn-loop.webm', 'dawn-loop-phone.mp4', 'dawn-loop-phone.webm'):
    print(f, round(os.path.getsize(os.path.join(A.out, f)) / 1e6, 2), 'MB')
