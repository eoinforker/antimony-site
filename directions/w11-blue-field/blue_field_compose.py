# The Blue Field: the loops, the stills and the depth maps for the page, built from two renders (the wide
# frame and the tall phone frame) and their data passes.
# Run with the system Python (numpy, Pillow) and ffmpeg; no Blender needed:
#   python3 blue_field_compose.py --work <wide render folder> --work-phone <phone render folder> --out <this folder>
# Each folder holds base.png (graded, no grain), data.png (16 bit: R disparity 2/d, G plants, B stone 0.5,
# crystal 1, paper 0.75) and frame.json, as blue_field.py writes them.
# Writes assets/loop.mp4|webm (1920x1080) and assets/loop-phone.mp4|webm (720x1560), 8 s at 24 fps, seamless;
# assets/still.webp|avif and assets/still-phone.webp|avif; assets/depth.png and assets/depth-phone.png;
# assets/frame.json (both frames); shots/render-still.png and shots/render-still-phone.png.
#
# Motion, restrained (every motion repeats a whole number of times in 8 s, so the last frame runs into the first):
#   - a breath of wind through the flowers: a slow travelling sway, stronger near the lens;
#     the stone, the crystal and the paper hold perfectly still, and the crystal's light is steady
#   - mist drifting through the needles: soft banks of the scene's own mist colour sliding slowly sideways
#     over the far field, thicker low down
#   - slow cloud: the sky slides a few pixels over the loop, on a plate filled in behind the needles
# One grade over everything (stills and loops alike): a gentle curve, blacks lifted toward night blue.
import argparse, json, os, subprocess
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('--work', required=True); ap.add_argument('--work-phone', required=True)
ap.add_argument('--out', default=os.path.dirname(os.path.abspath(__file__)))
ap.add_argument('--secs', type=float, default=8.0); ap.add_argument('--fps', type=int, default=24)
ap.add_argument('--crf264', type=int, default=20); ap.add_argument('--crf9', type=int, default=31)
ap.add_argument('--frames', type=int, default=0, help='only this many frames (testing)')
ap.add_argument('--x264', default='', help='extra x264 parameters (testing)')
ap.add_argument('--only', default='', help='wide or phone (testing)')
A = ap.parse_args()
os.makedirs(os.path.join(A.out, 'assets'), exist_ok=True); os.makedirs(os.path.join(A.out, 'shots'), exist_ok=True)
SKY = np.array([0x94, 0xE6, 0xFF], np.float32) / 255
LUMW = np.array([0.2126, 0.7152, 0.0722], np.float32)
TW = 2 * np.pi

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

def noise2(h, w, cx, cy, seed):
    """smooth value noise with cells cx by cy pixels"""
    g = np.random.default_rng(seed)
    nx = w // cx + 3; ny = h // cy + 3
    grid = g.random((ny, nx)).astype(np.float32)
    return np.asarray(Image.fromarray(grid).resize((nx * cx, ny * cy), Image.BICUBIC))[:h, :w]

def banks(h, P, k, seed):
    """soft banks of mist, wide and low, tiling exactly across a period of P pixels: a sum of waves whose
    sideways frequencies are whole numbers of cycles per period"""
    g = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:P].astype(np.float32)
    f = np.zeros((h, P), np.float32)
    for i in range(40):
        m = int(g.integers(1, 7)); sy = g.uniform(0.09, 0.24); sw_ = g.uniform(0.1, 0.5)
        shear = 0.25 * np.cos(TW * (yy / (h * sw_) + g.uniform(0, 1)))                 # bends each band a little
        f += (1.0 / m ** 0.7) * np.cos(TW * (m * xx / P + shear + g.uniform(0, 1))) * (0.5 + 0.5 * np.cos(TW * (yy / (h * sy) + g.uniform(0, 1))))
    f = (f - f.mean()) / (f.std() + 1e-6)
    return f

def sample(img, X, Y):
    """bilinear lookup of img at float pixel coordinates"""
    h, w = img.shape[:2]
    X = np.clip(X, 0, w - 1.001); Y = np.clip(Y, 0, h - 1.001)
    x0 = X.astype(np.int32); y0 = Y.astype(np.int32); fx = (X - x0)[..., None]; fy = (Y - y0)[..., None]
    a = img[y0, x0]; b = img[y0, x0 + 1]; c = img[y0 + 1, x0]; d = img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

def look(F):
    """the one grade: a gentle curve, blacks lifted toward night blue, a breath less saturation"""
    lum = (F @ LUMW)[..., None]
    F = lum + (F - lum) * 0.94
    F = np.clip(F, 0, 1); F = F + 0.10 * (F - F * F) * (F - 0.35) * 2.2           # soft S around the mids
    lift = np.array([0.010, 0.016, 0.034], np.float32)
    return np.clip(lift + F * (1 - lift), 0, 1)

class Layers:
    """everything the frame function needs, at one size"""
    def __init__(s, base, data, w, h):
        s.w, s.h = w, h; k = w / 1920.0 if w > h else w / 720.0; s.k = k
        H0, W0 = base.shape[:2]
        s.F = resize(base, w, h) if (w, h) != (W0, H0) else base.copy()
        D = resize(data, w, h) if (w, h) != (W0, H0) else data
        s.disp = D[..., 0]; s.plant = np.clip(D[..., 1], 0, 1); code = D[..., 2]
        s.still = np.clip(blur((code > 0.3).astype(np.float32)[..., None], 6 * k)[..., 0] * 3, 0, 1)   # stone, crystal, paper
        s.crystal = blur((code > 0.9).astype(np.float32)[..., None], 3 * k)[..., 0]
        # the crystal held to sky #94E6FF: its light and shade kept, its colour pulled onto the brand's sky
        lumF = s.F @ LUMW
        held = np.clip(lumF[..., None] / float(SKY @ LUMW) * SKY, 0, 1)
        s.F = s.F * (1 - 0.8 * s.crystal[..., None]) + held * (0.8 * s.crystal[..., None])
        pl = blur(s.plant[..., None], 3 * k)[..., 0]
        near = np.clip(blur(s.disp[..., None], 4 * k)[..., 0] / 0.5, 0, 1)
        s.sway_w = pl * (0.2 + 0.8 * near) * (1 - s.still)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); s.xx, s.yy = xx, yy
        s.ph = noise2(h, w, int(150 * k), int(150 * k), 4)
        # the sky (nothing hit) and the far field and needles (beyond about 60 m)
        sky = ((s.disp < 1e-4) & (s.plant < 0.01) & (code < 0.1)).astype(np.float32)
        s.sky = blur(sky[..., None], 1.5 * k)[..., 0]
        far = np.clip((0.035 - s.disp) / 0.02, 0, 1) * (1 - sky)
        s.far = blur(far[..., None], 3 * k)[..., 0]
        # a sky plate: the sky with the needles and hills filled in from round about, for the cloud to slide over
        m = sky[..., None]; num = blur(s.F * m, 40 * k); den = blur(m, 40 * k)
        s.plate = s.F * m + np.where(den > 1e-3, num / np.maximum(den, 1e-3), s.F) * (1 - m)
        # mist banks: long soft shapes, wider than tall, tiling sideways so they can drift for ever
        s.mist_w = int(w * 1.5)
        s.mist = np.clip(0.5 + 0.26 * banks(h, s.mist_w, k, 11), 0, 1) ** 1.4
        s.mist = blur(np.concatenate([s.mist[:, -40:], s.mist, s.mist[:, :40]], 1)[..., None], 5 * k)[..., 0][:, 40:40 + s.mist_w]   # soft, still tiling
        # where mist may lie: the far field, thickest low over the ground, up the needles' lower parts
        hz = np.argmax(s.sky.mean(1) < 0.5) if (s.sky.mean(1) < 0.5).any() else h // 2
        yfac = np.clip((s.yy - (hz - 0.30 * h)) / (0.30 * h), 0, 1) * np.clip(((hz + 0.18 * h) - s.yy) / (0.10 * h), 0, 1)
        s.mist_where = np.clip(s.far + 0.5 * s.sky, 0, 1) * yfac * (1 - s.still)
        mc = s.F[np.clip(hz, 0, h - 1) - int(0.02 * h), :, :].mean(0)                 # the mist's own colour, near the horizon
        s.mist_col = np.clip(mc * 1.18, 0, 1)

def frame(s, t):
    xx, yy, k = s.xx, s.yy, s.k
    # a breath of wind through the flowers
    wv = 0.6 * np.sin(TW * (xx / (520 * k) - t) + s.ph * 2.0) + 0.4 * np.sin(TW * (xx / (210 * k) + yy / (340 * k) - 2 * t))
    dx = 3.6 * k * s.sway_w * wv; dy = 0.9 * k * s.sway_w * np.sin(TW * (xx / (300 * k) - t) + 1.3)
    F = sample(s.F, xx - dx, yy - dy)
    # slow cloud: the sky slides; two passes cross-faded so the loop closes
    v = 14 * k
    c1 = sample(s.plate, xx - v * t, yy); c2 = sample(s.plate, xx - v * (t - 1), yy)
    C = c1 * (1 - t) + c2 * t
    F = F * (1 - s.sky[..., None]) + C * s.sky[..., None]
    # mist drifting through the needles, the same way
    vm = 60 * k
    def mistat(off):
        X = (xx + off) % s.mist_w
        x0 = X.astype(np.int32); fx = X - x0
        return s.mist[yy.astype(np.int32), x0] * (1 - fx) + s.mist[yy.astype(np.int32), (x0 + 1) % s.mist_w] * fx
    M = mistat(-vm * t) * (1 - t) + mistat(-vm * (t - 1)) * t
    a = (0.34 * M * s.mist_where)[..., None]
    F = F * (1 - a) + s.mist_col * a
    return look(np.clip(F, 0, 1))

def to8(a): return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
def save(a, path, **kw): Image.fromarray(to8(a)).save(path, **kw); print('wrote', path)
def avif(src, dst):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', src, '-c:v', 'libaom-av1', '-still-picture', '1', '-crf', '30', '-cpu-used', '6', dst], check=True)

def encode(L, name):
    n = A.frames or int(A.secs * A.fps)
    common = ['nice', '-n', '10', 'ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{L.w}x{L.h}', '-r', str(A.fps), '-i', '-']
    enc = [subprocess.Popen(common + ['-c:v', 'libx264', '-preset', 'slow', '-crf', str(A.crf264)] + (['-x264-params', A.x264] if A.x264 else []) + [ '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an',
                                      os.path.join(A.out, 'assets', name + '.mp4')], stdin=subprocess.PIPE),
           subprocess.Popen(common + ['-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', str(A.crf9), '-deadline', 'good', '-cpu-used', '4', '-row-mt', '1',
                                      '-pix_fmt', 'yuv420p', '-an', os.path.join(A.out, 'assets', name + '.webm')], stdin=subprocess.PIPE)]
    for i in range(n):
        fr = to8(frame(L, i / n)).tobytes()
        for e in enc: e.stdin.write(fr)
        if i % 24 == 0: print(name, 'frame', i, flush=True)
    for e in enc: e.stdin.close(); e.wait()

out_info = {}
try:                                       # keep the other frame's entry when only one is rebuilt
    _old = json.load(open(os.path.join(A.out, 'assets', 'frame.json')))
    out_info = {k: v for k, v in _old.items() if k in ('wide', 'phone')}
except Exception:
    pass
for key, work, still_name, loop_name, depth_name, lw, lh, sw in (
        ('wide', A.work, 'still', 'loop', 'depth', 1920, 1080, 1920),
        ('phone', A.work_phone, 'still-phone', 'loop-phone', 'depth-phone', 720, 1560, 1080)):
    if A.only and A.only != key: continue
    info = json.load(open(os.path.join(work, 'frame.json')))
    base = load_rgb(os.path.join(work, 'base.png')); data = load_rgb(os.path.join(work, 'data.png'), bits16=True)
    H0, W0 = base.shape[:2]
    # the still: frame 0 at full size
    SL = Layers(base, data, W0, H0); still = frame(SL, 0.0); del SL
    save(still, os.path.join(A.out, 'shots', 'render-still.png' if key == 'wide' else 'render-still-phone.png'))
    sh = int(round(sw * H0 / W0))
    Image.fromarray(to8(resize(still, sw, sh) if W0 > sw else still)).save(os.path.join(A.out, 'assets', still_name + '.webp'), quality=82, method=6)
    avif(os.path.join(A.out, 'assets', still_name + '.webp'), os.path.join(A.out, 'assets', still_name + '.avif'))
    # depth for the breathing layer: disparity, smoothed so the warp never tears
    dw = 960 if key == 'wide' else 480
    dep = blur(resize(data, dw, int(round(dw * H0 / W0)))[..., :1], 3)[..., 0]
    Image.fromarray((np.clip(dep, 0, 1) * 255).astype(np.uint8)).save(os.path.join(A.out, 'assets', depth_name + '.png'))
    out_info[key] = info
    # the loop
    L = Layers(base, data, lw, lh); encode(L, loop_name); del L
json.dump(out_info, open(os.path.join(A.out, 'assets', 'frame.json'), 'w'), indent=1)
for f in sorted(os.listdir(os.path.join(A.out, 'assets'))):
    p = os.path.join(A.out, 'assets', f)
    if os.path.isfile(p): print(f, round(os.path.getsize(p) / 1e6, 2), 'MB')
