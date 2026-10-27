# The Crystal: grade the rendered still and compose the seamless loop from passes.
#
#   python3 crystal_compose.py --still beauty.png --masks masks.png --letter letter.png --info letterinfo.json --out assets --shots shots
#
# Inputs, all from the_crystal.py at the same camera: the AgX still, a mask render (R the crystal,
# G the near grass, B distance from the camera: 0 near, 1 at 3 km and the sky) and the frame info
# (where the stone, the crystal and the letter land, in pixels). Everything works on display pixels:
# a gentle golden grade, then a 6 s loop at 24 fps (144 frames) built from the one still:
#   - mist drifts through the valley: two soft noise layers sway slowly at different speeds,
#     weighted to the middle distance (the forest in the valley), never over the stone
#   - the light breathes: the sun's side of the sky swells and settles, and the crystal glows a
#     little brighter and back
#   - a small flock of birds wheels near the stone, far off (their size tells the stone's scale)
#   - the grass on the near lip sways in the wind
#   - fine grain, new on every frame
# Every motion has a period that divides 144 frames, so the last frame runs into the first.
# Writes: shots/render-still.png and render-still-phone.png, assets/crystal-still(.webp/.avif),
# crystal-still-phone(.webp/.avif), crystal-loop(.mp4/.webm), crystal-loop-phone(.mp4/.webm),
# and assets/frame.json (the letter's box and the phone crop, for the page).

import sys, os, subprocess, math, json
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

def arg(name, default=None):
    a = sys.argv
    return a[a.index(name) + 1] if name in a else default

STILL, MASKS, INFO = arg('--still'), arg('--masks'), arg('--info')
OUT, SHOTS = arg('--out', 'assets'), arg('--shots', 'shots')
FR, NF = 24, 144
os.makedirs(OUT, exist_ok=True); os.makedirs(SHOTS, exist_ok=True)
rng = np.random.default_rng(5)
info = json.load(open(INFO))

def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def load(path, size=None):
    im = Image.open(path)
    if im.mode in ('I;16', 'I'): im = im.point(lambda v: v / 256).convert('L')
    im = im.convert('RGB')
    if size and im.size != size: im = im.resize(size, Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255.0

full = load(STILL); H0, W0, _ = full.shape
mk = load(MASKS, (W0, H0))
k = W0 / info['w']                                        # the info may come from a smaller render
SB = [v * k for v in info['stone']]; LB = [v * k for v in info['letter']]
SUN = (0.10, 0.30)
# the letter: its own object pass (same camera, same light, held out by the grass in front,
# its shadow caught on the ground), laid in before the grade so the grade binds it in
LETTER = arg('--letter')
if LETTER:
    lt = np.asarray(Image.open(LETTER).convert('RGBA').resize((W0, H0))).astype(np.float32) / 255
    al = np.where(lt[..., 3] > 0.08, lt[..., 3], 0.0)[..., None]                 # drop the faint haze of the empty border
    # the pass is lit only by sun and sky (no haze), so its paper reads cold: keep its folds and
    # shading, and set its colour from the light around it, warm cotton catching the low sun
    lum = (lt[..., :3] * np.array([.2126, .7152, .0722], np.float32)).sum(-1, keepdims=True)
    ys_, xs_ = np.where(al[..., 0] > 0.5)
    lo_, hi_ = np.percentile(lum[ys_, xs_], 5), np.percentile(lum[ys_, xs_], 95)
    shade = np.clip((lum - lo_) / max(1e-3, hi_ - lo_), 0, 1)
    paper = np.array([0.66, 0.55, 0.41], np.float32) * (0.70 + 0.42 * shade)
    # sit it in the evening air: a little of the haze colour over it, and a softened edge
    paper = paper * 0.85 + np.array([0.62, 0.50, 0.36], np.float32) * 0.15
    al = np.asarray(Image.fromarray((al[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32)[..., None] / 255
    # a soft contact shadow under its lower edge, in the grass
    yb = int(ys_.max()); xc = (xs_.min() + xs_.max()) / 2; hw = (xs_.max() - xs_.min()) / 2
    yy_ = np.arange(H0)[:, None]; xx_ = np.arange(W0)[None, :]
    cs = np.exp(-((yy_ - yb - 2) / 6.0) ** 2) * np.exp(-((xx_ - xc) / (hw * 1.1)) ** 4) * 0.45
    full = full * (1 - cs[..., None] * (1 - al))
    full = full * (1 - al) + paper * al                                        # where the sun's glow sits, behind the left ridge

def grade(img, crys):
    """Gold against dark: an S about the mids, a warm gradient map, the crystal kept sky blue, a soft vignette."""
    H, W, _ = img.shape
    y = np.linspace(0, 1, H)[:, None, None]; x = np.linspace(0, 1, W)[None, :, None]
    lum = (img * np.array([.2126, .7152, .0722], np.float32)).sum(-1, keepdims=True)
    lc = np.clip(lum + (smooth(0.06, 0.95, lum) - lum) * 0.55, 0, 1)
    b = np.clip(img * lc / np.maximum(lum, 1e-3), 0, 1)
    sh, md, hi = np.array([.09, .075, .10]), np.array([.60, .40, .22]), np.array([1.0, .88, .62])
    gm = sh + (md - sh) * smooth(0.0, 0.5, lc); gm = gm + (hi - gm) * smooth(0.45, 1.0, lc)
    b = b * 0.7 + gm * 0.3
    keep = crys[..., None]
    b = b * (1 - keep) + img * keep
    r = np.sqrt(((x - 0.5) * 1.6) ** 2 + ((y - 0.45) * 1.5) ** 2)
    return np.clip(b * (1 - 0.24 * smooth(0.55, 1.25, r)), 0, 1)

cr_img = Image.fromarray((mk[..., 0] * 255).astype(np.uint8))
crys_full = np.asarray(cr_img.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32) / 255
graded = grade(full, crys_full)
g8 = (graded * 255 + 0.5).astype(np.uint8)
Image.fromarray(g8).save(os.path.join(SHOTS, 'render-still.png'))

# phone crop: a tall slice centred on the stone
PH_AR = 390 / 844
pw = int(round(H0 * PH_AR)) // 2 * 2
scx = (SB[0] + SB[2]) / 2
px0 = int(min(max(0, scx - pw / 2), W0 - pw))
def still_out(arr, name, w=None):
    im = Image.fromarray(arr)
    if w and im.width != w: im = im.resize((w, int(round(im.height * w / im.width)) // 2 * 2), Image.LANCZOS)
    im.save(os.path.join(OUT, name + '.webp'), quality=84, method=6)
    tmp = os.path.join(OUT, name + '.tmp.png'); im.save(tmp)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', tmp, '-c:v', 'libaom-av1', '-still-picture', '1',
                    '-crf', '28', '-cpu-used', '6', '-pix_fmt', 'yuv420p', os.path.join(OUT, name + '.avif')], check=True)
    os.remove(tmp)
still_out(g8, 'crystal-still', 2560)
still_out(g8[:, px0:px0 + pw], 'crystal-still-phone')
Image.fromarray(g8[:, px0:px0 + pw]).save(os.path.join(SHOTS, 'render-still-phone.png'))
json.dump({'w': W0, 'h': H0, 'letter': LB, 'stone': SB, 'phone_x0': px0, 'phone_w': pw},
          open(os.path.join(OUT, 'frame.json'), 'w'))
print('phone crop', px0, pw, 'letter', LB)

# ---------------------------------------------------------------- the loop
W, H = W0, H0
base = graded.astype(np.float32)
crys = np.clip(np.asarray(cr_img.filter(ImageFilter.GaussianBlur(28))).astype(np.float32) / 255 * 1.8, 0, 1)
grass = np.asarray(Image.fromarray((mk[..., 1] * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32) / 255
dist = mk[..., 2]
if LETTER:                                                    # the letter does not sway with the grass behind it
    keep_l = np.asarray(Image.fromarray((al[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))).astype(np.float32) / 255
    grass = grass * (1 - keep_l)
yy = np.arange(H, dtype=np.float32)[:, None]; xs = np.arange(W, dtype=np.float32)[None, :]
# where the mist lives: the valley in the middle distance, never the sky, the stone or the lip
valley = smooth(0.18, 0.32, dist) * (1 - smooth(0.80, 0.96, dist))
sx0, sy0, sx1, sy1 = SB
stone_box = (smooth(sx0 - 60, sx0 + 20, xs) * (1 - smooth(sx1 - 20, sx1 + 60, xs)) * (1 - smooth(sy1 - 10, sy1 + 40, yy)))
mist_w = np.clip(valley * (1 - stone_box) * (1 - grass), 0, 1)
mist_w = np.asarray(Image.fromarray((mist_w * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(12))).astype(np.float32) / 255

def field(seed, scales):
    r = np.random.default_rng(seed); acc = np.zeros((H, 2 * W), np.float32)
    for s, a in scales:
        small = r.random((H // s + 3, (2 * W) // s + 3)).astype(np.float32)
        im = Image.fromarray((small * 255).astype(np.uint8)).resize(((2 * W) + 3 * s, H + 3 * s), Image.BICUBIC)
        acc += a * (np.asarray(im).astype(np.float32)[:H, :2 * W] / 255 - 0.5)
    return acc
# wide, soft layers, stretched along the valley
f1 = field(21, [(220, 1.0), (90, 0.45)]); f2 = field(22, [(160, 1.0), (60, 0.4)])
mist_col = np.array([1.0, 0.86, 0.66], np.float32)
y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
sun_glow = np.exp(-(((x - SUN[0]) * 1.4) ** 2 + ((y - SUN[1]) * 1.1) ** 2) / 0.12)

# birds: seven, wheeling about a point left of the stone at about two thirds of its height
BC = (sx0 - (sx1 - sx0) * 0.55, sy0 + (sy1 - sy0) * 0.30)
BR = ((sx1 - sx0) * 0.42, (sy1 - sy0) * 0.10)
BS = max(4.0, (sx1 - sx0) / 46)                                       # half wingspan in pixels
birds = [(2 * math.pi * j / 7 + rng.uniform(-0.25, 0.25), rng.uniform(0.85, 1.12), rng.uniform(0, 2 * math.pi)) for j in range(7)]
def draw_birds(i):
    ss = 4; pad = int(BR[0] + BS * 4)
    ox, oy = int(BC[0] - pad), int(BC[1] - BR[1] - BS * 4)
    w_, h_ = int(2 * pad), int(2 * BR[1] + BS * 8)
    layer = Image.new('L', (w_ * ss, h_ * ss), 0); dr = ImageDraw.Draw(layer)
    t = i / NF
    for (ph, rad, fp) in birds:
        a = 2 * math.pi * t + ph                                         # one circuit per loop
        cx = BC[0] + BR[0] * rad * math.cos(a) - ox; cy = BC[1] + BR[1] * rad * math.sin(a) - oy
        flap = math.sin(2 * math.pi * t * 12 + fp)                       # twelve wingbeats per loop
        s = BS * (0.9 + 0.2 * math.sin(a))                              # a touch nearer at the front of the circle
        tip = -0.65 * flap * s; d = 1 if math.sin(a) > 0 else -1
        pts = [(cx - s, cy + tip), (cx - 0.35 * s, cy - 0.12 * s), (cx, cy + 0.12 * s), (cx + 0.35 * s, cy - 0.12 * s), (cx + s, cy + tip),
               (cx + 0.35 * s, cy + 0.10 * s), (cx, cy + 0.32 * s), (cx - 0.35 * s, cy + 0.10 * s)]
        dr.polygon([(px * ss, py * ss) for px, py in pts], fill=255)
    layer = layer.resize((w_, h_), Image.LANCZOS)
    return np.asarray(layer).astype(np.float32) / 255 * 0.85, ox, oy

def frame(i):
    t = i / NF
    out = base.copy()
    # the grass on the lip sways (two cycles per loop, with a slower gust)
    if grass.max() > 0:
        sway = (1.4 * np.sin(2 * np.pi * (t * 2) + xs * 0.011) + 0.8 * np.sin(2 * np.pi * t + xs * 0.003)) * grass
        sx = np.clip(xs + sway, 0, W - 1.001) + 0 * yy
        x0 = np.floor(sx).astype(np.int32); fx = (sx - x0)[..., None]
        yi = np.broadcast_to(np.arange(H)[:, None], (H, W))
        warped = base[yi, x0] * (1 - fx) + base[yi, x0 + 1] * fx
        out = np.where((grass > 0.02)[..., None], warped, out)
    # the mist drifts: two layers sway along the valley at different speeds (one and two cycles)
    o1 = W // 2 + int(90 * math.sin(2 * math.pi * t)); o2 = W // 2 - int(140 * math.sin(2 * math.pi * 2 * t + 1.0))
    m = 0.6 * f1[:, o1:o1 + W] + 0.4 * f2[:, o2:o2 + W]
    mist = np.clip(m * 1.8 + 0.5, 0, 1) * mist_w * 0.16
    out = out + (mist_col - out) * mist[..., None]
    # the light breathes: the sun's side swells and settles; the crystal glows and settles
    br = 0.5 - 0.5 * math.cos(2 * math.pi * t)
    out = 1 - (1 - out) * (1 - np.array([1.0, .80, .52], np.float32) * (sun_glow * 0.10 * br)[..., None])
    out = out * (1 + 0.08 * br * crys[..., None])
    # the birds
    bl, ox, oy = draw_birds(i)
    hh, ww = bl.shape
    sub = out[oy:oy + hh, ox:ox + ww]
    sub[:] = sub * (1 - bl[..., None]) + (sub * 0.32) * bl[..., None]
    # grain
    g = rng.normal(0, 0.010, (H, W, 1)).astype(np.float32)
    out = out + g * (0.6 + 0.4 * out)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)

def enc(path, w, h, codec, scale=None):
    vf = ['-vf', f'scale={scale}:-2:flags=lanczos'] if scale else []
    if codec == 'h264':
        a = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '22', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-tune', 'grain']
    else:
        a = ['-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '32', '-row-mt', '1', '-pix_fmt', 'yuv420p', '-deadline', 'good', '-cpu-used', '2']
    return subprocess.Popen(['nice', '-n', '10', 'ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                             '-s', f'{w}x{h}', '-r', str(FR), '-i', '-', '-an'] + vf + a + [path], stdin=subprocess.PIPE)
encs = [(enc(os.path.join(OUT, 'crystal-loop.mp4'), W, H, 'h264', 1920), False),
        (enc(os.path.join(OUT, 'crystal-loop.webm'), W, H, 'vp9', 1920), False),
        (enc(os.path.join(OUT, 'crystal-loop-phone.mp4'), pw, H, 'h264', 620), True),
        (enc(os.path.join(OUT, 'crystal-loop-phone.webm'), pw, H, 'vp9', 620), True)]
for i in range(NF):
    f = frame(i)
    fp = np.ascontiguousarray(f[:, px0:px0 + pw])
    for p, phone in encs: p.stdin.write((fp if phone else f).tobytes())
    if i % 24 == 0: print('frame', i, flush=True)
for p, _ in encs: p.stdin.close(); p.wait()
print('done')
