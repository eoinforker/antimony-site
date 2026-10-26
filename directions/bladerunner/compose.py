# Builds the loop and the stills from the linear passes that scene.py renders.
#   blender -b -P compose.py -- --src <folder with full.exr nohaze.exr flick.exr sw_####.exr> --out <folder>
# Light adds, so the loop is exact sums of passes:
#   nohaze + min(h, 0) + drift(x, y, t) * max(h, 0), h = full - nohaze: the haze's glow, drifting
#   + (v(t) - 1) * flick                           the failing practicals
#   + sweep(t)                                     the searchlight, rendered frame by frame on its own
# then a soft bloom, the AgX view (through OpenColorIO, as Blender itself shows it) and out to ffmpeg.

import bpy, sys, os, math, random, subprocess, time
import numpy as np
import PyOpenColorIO as OCIO

def arg(name, default):
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return a[a.index(name) + 1] if name in a else default

SRC = arg('--src', '.')
OUT = arg('--out', '.')
FPS = 24
NFR = int(arg('--frames', '480'))          # 20 s
SW0 = int(arg('--sw0', '265'))             # the searchlight's first frame in the loop
NSW = int(arg('--nsw', '108'))
EXPO = float(arg('--exposure', '0.0'))
SWG = float(arg('--swgain', '1.0'))      # the searchlight's level, set in the grade (light adds, so this is exact)
ONLY = arg('--only', '')                   # 'stills' to skip the video
W = int(arg('--w', '0'))

def load(path, size=None):
    im = bpy.data.images.load(path)
    if size and tuple(im.size) != size: im.scale(*size)
    w, h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3].copy()
    bpy.data.images.remove(im)
    return a

full = load(os.path.join(SRC, 'full.exr'))
H_, W_ = full.shape[:2]
nohaze = load(os.path.join(SRC, 'nohaze.exr'), (W_, H_)) if os.path.exists(os.path.join(SRC, 'nohaze.exr')) else full.copy()
flick = load(os.path.join(SRC, 'flick.exr'), (W_, H_)) if os.path.exists(os.path.join(SRC, 'flick.exr')) else np.zeros_like(full)
haze = full - nohaze
# the haze's glow drifts; the light it swallows stays as rendered, so thick patches never punch holes
haze_pos = np.maximum(haze, 0.0); base = nohaze + np.minimum(haze, 0.0)
del full
print('passes', W_, H_); sys.stdout.flush()

cfg = OCIO.Config.CreateFromFile(os.path.join(os.path.dirname(bpy.app.binary_path), '4.5', 'datafiles', 'colormanagement', 'config.ocio'))
proc = cfg.getProcessor('Linear Rec.709', 'AgX Base sRGB').getDefaultCPUProcessor()

# a periodic noise field (filtered white noise, periodic by construction), for the haze drift
def pnoise(nx, ny, beta, seed):
    r = np.random.default_rng(seed)
    f = np.fft.fft2(r.standard_normal((ny, nx)))
    kx = np.fft.fftfreq(nx)[None, :]; ky = np.fft.fftfreq(ny)[:, None]
    k = np.sqrt(kx * kx + ky * ky); k[0, 0] = 1
    f *= k ** -beta; f[0, 0] = 0
    a = np.real(np.fft.ifft2(f)); a /= a.std()
    return a.astype(np.float32)

N1 = pnoise(256, 160, 1.6, 3); N2 = pnoise(256, 160, 1.4, 8)
gx = (np.arange(W_) + 0.5) / W_; gy = (np.arange(H_) + 0.5) / H_
def sample(F, sx, sy, ox, oy):
    ny, nx = F.shape
    x = gx * sx * nx + ox; y = gy * sy * ny + oy
    x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64); fx = (x - x0)[None, :]; fy = (y - y0)[:, None]
    x0 %= nx; y0 %= ny; x1 = (x0 + 1) % nx; y1 = (y0 + 1) % ny
    a = F[y0][:, x0]; b = F[y0][:, x1]; c = F[y1][:, x0]; d = F[y1][:, x1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

def drift(f):
    # the smoke moves slowly left, one whole field width per loop for the broad layer, two for the fine
    t = (f % NFR) / NFR
    a = sample(N1, 0.55, 0.55, -t * 256.0, 0.0)
    b = sample(N2, 1.4, 1.4, -t * 512.0, t * 0.0)
    return np.clip(1.0 + 0.24 * a + 0.12 * b, 0.55, 1.5)[..., None]

def flick_v(f):
    # the failing ad walls: mostly steady, two stutters and one long brown out each loop
    rs = random.Random(f % NFR)
    g = f % NFR
    v = 1.0
    if 60 <= g < 66: v = [0.2, 0.9, 0.1, 0.8, 0.95, 1.0][g - 60]
    if 330 <= g < 352: v = 0.25 + 0.6 * abs(math.sin((g - 330) * 0.9)) * (0.5 if g < 344 else 1.0)
    if g in (421, 423): v = 0.45
    return v * (0.97 + 0.03 * rs.random())

def blur(x, rad):
    for _ in range(3):
        for ax in (0, 1):
            pad = [(0, 0)] * 3; pad[ax] = (rad + 1, rad)
            c = np.cumsum(np.pad(x, pad, mode='edge'), axis=ax); n = x.shape[ax]
            x = (np.take(c, np.arange(2 * rad + 1, 2 * rad + 1 + n), axis=ax) - np.take(c, np.arange(n), axis=ax)) / (2 * rad + 1)
    return x

ys, xs = np.mgrid[0:H_, 0:W_].astype(np.float32)
vig = (1.0 - 0.28 * (((xs / W_ - 0.52) * 1.25) ** 2 + ((ys / H_ - 0.48) * 1.5) ** 2))[..., None].clip(0.6, 1.0)

def finish(lin):
    lin = np.maximum(lin, 0.0) * (2.0 ** EXPO)
    lum = lin.mean(-1, keepdims=True)
    hi = np.maximum(lin - 0.8, 0.0) * np.clip((lum - 0.8) * 3, 0, 1)
    small = hi[::4, ::4]
    bl = blur(small, 5) * 0.55 + blur(small, 20) * 0.45
    bl = np.repeat(np.repeat(bl, 4, 0), 4, 1)[:H_, :W_]
    lin = (lin + bl * 0.3) * vig
    px = np.ascontiguousarray(lin, dtype=np.float32)
    proc.applyRGB(px)
    return (np.clip(px, 0, 1) * 255.0 + 0.5).astype(np.uint8)

sweep_cache = {}
def sweep(f):
    k = f - SW0 + 1
    if k < 1 or k > NSW: return None
    p = os.path.join(SRC, 'sw_%04d.exr' % k)
    if os.path.exists(p): return load(p, (W_, H_))
    # rendered on alternate frames: the frame between is the mean of its neighbours (light adds)
    pa, pb = os.path.join(SRC, 'sw_%04d.exr' % (k - 1)), os.path.join(SRC, 'sw_%04d.exr' % (k + 1))
    if os.path.exists(pa) and os.path.exists(pb): return 0.5 * (load(pa, (W_, H_)) + load(pb, (W_, H_)))
    return None

def frame_lin(f, with_sweep=True):
    lin = base + haze_pos * drift(f) + (flick_v(f) - 1.0) * flick
    if with_sweep:
        s = sweep(f)
        if s is not None:
            # the lamp is shut off over the last frames rendered (see notes: the sweep was cut short)
            k = f - SW0 + 1; x = min(1.0, max(0.0, (k - 46) / 13.0)); lin = lin + s * SWG * (1 - x * x * (3 - 2 * x))
    return lin

def save(rgb, path):
    # a plain 8 bit PNG, written directly
    import zlib, struct
    h, w = rgb.shape[:2]
    raw = b''.join(b'\x00' + rgb[y].tobytes() for y in range(h))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))

os.makedirs(OUT, exist_ok=True)
save(finish(frame_lin(1, False)), os.path.join(OUT, 'still.png'))
mid = SW0 + int(NSW * float(arg('--mid', '0.5')))
if os.path.exists(os.path.join(SRC, 'sw_%04d.exr' % (mid - SW0 + 1))):
    save(finish(frame_lin(mid)), os.path.join(OUT, 'moment.png'))
print('stills done'); sys.stdout.flush()
if ONLY == 'stills': sys.exit(0)

cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W_, H_), '-r', str(FPS), '-i', '-',
       '-vf', 'scale=out_color_matrix=bt709:out_range=tv', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
       '-c:v', 'libx264', '-preset', 'slow', '-crf', arg('--crf', '21'), '-tune', 'film', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', os.path.join(OUT, 'loop.mp4'),
       '-vf', 'scale=out_color_matrix=bt709:out_range=tv', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
       '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', arg('--vpcrf', '36'), '-row-mt', '1', '-cpu-used', '4', '-pix_fmt', 'yuv420p', os.path.join(OUT, 'loop.webm')]
ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
t0 = time.time()
for f in range(1, NFR + 1):
    ff.stdin.write(finish(frame_lin(f)).tobytes())
    if f % 24 == 0: print('frame', f, '%.0fs' % (time.time() - t0)); sys.stdout.flush()
ff.stdin.close(); ff.wait()
print('encoded', time.time() - t0)
