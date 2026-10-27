# Crystal Isle: grade the rendered still and compose the seamless loop from passes.
#
#   python3 isle_compose.py --still beauty.png --masks masks.png --out <folder>
#
# Inputs, both from crystal_isle.py at the same camera: the AgX still, and a mask render
# (R: the crystal and its reflection, G: the reeds, B: the water). Everything here works on
# display pixels: a gentle grade (violet shadows, a darker lower frame, a soft vignette), then
# a 6 s loop at 24 fps (144 frames) built from that one still:
#   - the crystal's light breathes (by about 7 percent, through a soft blur of its mask)
#   - the water shimmers: reflections waver a pixel or two, more near the camera
#   - the reeds sway a little
#   - the mist breathes: two soft noise fields crossfade, lifting the haze near the water
#   - fine film grain, new on every frame
# Every motion has a period that divides 144 frames, so the last frame runs into the first.
# Writes: render-still.png (graded, full size), isle-still(.webp/.avif), isle-still-phone(.webp/.avif),
# isle-loop(.mp4/.webm) and isle-loop-phone(.mp4/.webm).

import sys, os, subprocess, math
import numpy as np
from PIL import Image, ImageFilter

def arg(name, default=None):
    a = sys.argv
    return a[a.index(name) + 1] if name in a else default

STILL, MASKS, OUT = arg('--still'), arg('--masks'), arg('--out', '.')
FR, NF = 24, 144
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(5)

def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

SUN = (0.651, 0.517)                   # where the low sun sits, behind the island (from the camera and sun angles)
SKYC = np.array([0.580, 0.902, 1.0], np.float32)   # #94E6FF

def grade(img, mask_r, mask_soft):
    """A violet and gold dawn: gradient-mapped split tone, a gold bloom about the hidden sun that
    lights only the haze, a deeper violet zenith, the crystal lifted as the one cool jewel, a
    darker lower frame and a soft vignette."""
    H, W, _ = img.shape
    y = np.linspace(0, 1, H)[:, None, None]; x = np.linspace(0, 1, W)[None, :, None]
    lum = (img * np.array([.2126, .7152, .0722], np.float32)).sum(-1, keepdims=True)
    keep = mask_r[..., None]
    # contrast: an S about the mids, so the island sinks to a soft dark silhouette
    lc = lum + (smooth(0.0, 1.0, lum) - lum) * 0.65
    lc = np.clip(lc * 1.04 - 0.02, 0, 1)
    # the gradient map: deep violet, rose, warm gold
    sh, md, hi = np.array([.16, .09, .25]), np.array([.66, .46, .68]), np.array([1.0, .86, .66])
    t1 = smooth(0.0, 0.5, lc); t2 = smooth(0.45, 1.0, lc)
    gm = sh + (md - sh) * t1; gm = gm + (hi - gm) * t2
    ratio = lc / np.maximum(lum, 1e-3)
    img2 = np.clip(img * ratio, 0, 1) * 0.42 + gm * 0.58
    # the sun's gold: a broad bloom on the bright haze only, and a warm band along the horizon
    d = np.sqrt(((x - SUN[0]) * 1.6) ** 2 + ((y - SUN[1]) * 0.9) ** 2)
    glow = np.exp(-(d / 0.26) ** 2) * 0.55 + np.exp(-(d / 0.75) ** 2) * 0.22
    glow = glow * smooth(0.25, 0.75, lum)
    gold = np.array([1.0, .74, .44], np.float32)
    img2 = 1 - (1 - img2) * (1 - gold * glow)
    # a deeper violet towards the zenith
    img2 = img2 * (1 - (1 - np.array([.80, .72, .98])) * smooth(0.35, 0.0, y))
    # the crystal: held to sky blue, lifted, with a soft blue glow about it
    lifted = np.clip(SKYC * (0.55 + 0.75 * lum), 0, 1)
    img2 = img2 * (1 - keep) + (img * 0.25 + lifted * 0.75) * keep
    img2 = 1 - (1 - img2) * (1 - SKYC * mask_soft[..., None] * 0.28)
    # a darker lower frame, and a soft vignette
    low = 1 - 0.32 * smooth(0.62, 1.0, y)
    r = np.sqrt(((x - 0.5) * 1.7) ** 2 + ((y - 0.45) * 1.6) ** 2)
    vig = 1 - 0.26 * smooth(0.55, 1.25, r)
    return np.clip(img2 * low * vig, 0, 1)

def load(path, size=None):
    im = Image.open(path).convert('RGB')
    if size: im = im.resize(size, Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255.0

full = load(STILL); H0, W0, _ = full.shape
mk = load(MASKS, (W0, H0))
# the paper boat: rendered alone with the scene's camera and light (paper_boat.py); set on the water
# here with its reflection, before the grade, so the grade binds it into the frame
BOAT = arg('--boat')
boat_mask = np.zeros((H0, W0), np.float32)
boat_only = np.zeros((H0, W0), np.float32)
if BOAT:
    bt = np.asarray(Image.open(BOAT).convert('RGBA').resize((W0, H0))).astype(np.float32) / 255
    rgb, al = bt[..., :3], bt[..., 3]
    lum_b = (rgb * np.array([.2126, .7152, .0722])).sum(-1)
    a = al * smooth(0.05, 0.14, lum_b)            # the paper only (the shadow catcher's shadow is dropped: still water barely shows it)
    ys, xs = np.where(a > 0.5)
    yw = int(ys.max()) - 1                         # the waterline
    # the reflection: the boat mirrored about the waterline, a touch shorter, darker and softer
    ref = np.zeros_like(rgb); ra = np.zeros_like(a)
    for y in range(yw, min(H0, yw + (yw - ys.min()) + 4)):
        src = yw - int((y - yw) / 0.92)
        if src < 0: break
        ref[y] = rgb[src]; ra[y] = a[src]
    ref_im = Image.fromarray((np.clip(ref, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    ref = np.asarray(ref_im).astype(np.float32) / 255
    ra = np.asarray(Image.fromarray((ra * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255
    full = full * (1 - ra[..., None] * 0.55) + ref * 0.75 * ra[..., None] * 0.55
    # a faint soft line where the paper meets the water
    yy_ = np.arange(H0)[:, None]; xx_ = np.arange(W0)[None, :]
    cx = (xs.min() + xs.max()) / 2; hw = (xs.max() - xs.min()) / 2
    contact = np.exp(-((yy_ - yw) / 2.0) ** 2) * np.exp(-((xx_ - cx) / (hw * 0.9)) ** 4) * 0.25
    full = full * (1 - contact[..., None])
    full = full * (1 - a[..., None]) + rgb * a[..., None]
    boat_mask = np.clip(a + ra, 0, 1); boat_only = a
    print('BOATPX', int(xs.min()), int(ys.min()), int(xs.max()), int(yw))
# the crystal mask, slightly grown and softened, for the grade and the breathing light
mr_img = Image.fromarray((mk[..., 0] * 255).astype(np.uint8))
mask_r_full = np.asarray(mr_img.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2))).astype(np.float32) / 255
# soften the meeting of water and sky: a narrow vertical blur about the horizon, so no line survives
wm_full = mk[..., 2] > 0.35
rows_f = np.where(wm_full.mean(1) > 0.3)[0]
if len(rows_f):
    yh_f = int(rows_f.min()); band_h = max(8, H0 // 60)
    blur = np.asarray(Image.fromarray((full * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(0)).resize((W0, H0 // band_h), Image.BOX).resize((W0, H0), Image.BICUBIC)).astype(np.float32) / 255
    yy0 = np.arange(H0, dtype=np.float32)[:, None, None]
    wgt = np.exp(-((yy0 - yh_f) / (band_h * 1.2)) ** 2) * (1 - mask_r_full[..., None])
    full = full * (1 - wgt) + blur * wgt
mask_soft_full = np.asarray(mr_img.filter(ImageFilter.GaussianBlur(H0 / 30))).astype(np.float32) / 255
mask_soft_full = np.clip(mask_soft_full * 2.0, 0, 1)
graded = grade(full, mask_r_full, mask_soft_full)
g8 = (graded * 255 + 0.5).astype(np.uint8)
Image.fromarray(g8).save(os.path.join(OUT, 'render-still.png'))

# phone crop: a tall slice centred on the mark (the mark is at the frame's centre)
PH_AR = 390 / 844
pw = int(round(H0 * PH_AR)) // 2 * 2; px0 = (W0 - pw) // 2
def still_out(arr, name, w=None):
    im = Image.fromarray(arr)
    if w: im = im.resize((w, int(round(im.height * w / im.width)) // 2 * 2), Image.LANCZOS)
    im.save(os.path.join(OUT, name + '.webp'), quality=82, method=6)
    tmp = os.path.join(OUT, name + '.tmp.png'); im.save(tmp)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', tmp, '-c:v', 'libaom-av1', '-still-picture', '1',
                    '-crf', '30', '-cpu-used', '6', '-pix_fmt', 'yuv420p', os.path.join(OUT, name + '.avif')], check=True)
    os.remove(tmp)
still_out(g8, 'isle-still', 2560)
still_out(g8[:, px0:px0 + pw], 'isle-still-phone')
Image.fromarray(g8[:, px0:px0 + pw]).save(os.path.join(OUT, 'render-still-phone.png'))

# ---------------------------------------------------------------- the loop
W, H = 2560, 1440                     # composed at full size; the wide video is scaled to 1920 by ffmpeg
base = load(os.path.join(OUT, 'render-still.png'), (W, H))
m = load(MASKS, (W, H))
crys = np.asarray(Image.fromarray((m[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(32))).astype(np.float32) / 255
crys = np.clip(crys * 1.6, 0, 1)
reed = np.asarray(Image.fromarray((m[..., 1] * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32) / 255
water = m[..., 2] > 0.35
boat_px = np.asarray(Image.fromarray((np.clip(boat_only, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).resize((W, H))) > 40
rows = np.where(water.mean(1) > 0.3)[0]
yh = int(rows.min()) if len(rows) else int(H * 0.72)               # the horizon: where the water begins
print('horizon row', yh)

def field(seed):
    """Soft noise, a few octaves, made from blurred random values."""
    r = np.random.default_rng(seed)
    acc = np.zeros((H, W), np.float32)
    for s, a in [(160, 1.0), (60, 0.5), (24, 0.25)]:
        small = r.random((H // s + 3, W // s + 3)).astype(np.float32)
        im = Image.fromarray((small * 255).astype(np.uint8)).resize((W + 3 * s, H + 3 * s), Image.BICUBIC)
        acc += a * (np.asarray(im).astype(np.float32)[:H, :W] / 255 - 0.5)
    return acc
n1, n2 = field(11), field(12)
yy = np.arange(H, dtype=np.float32)[:, None]
band = np.exp(-((yy - yh) / (H * 0.12)) ** 2)                      # the mist sits low, about the waterline
haze_w = band * (1 - crys) * (1 - reed)
haze_col = np.array([0.92, 0.78, 0.94], np.float32)

xs = np.arange(W, dtype=np.float32)[None, :]
depth = np.clip((yy - yh) / max(1, H - yh), 0, 1)                   # 0 at the horizon, 1 at the frame foot

def frame(i):
    t = i / NF
    out = base.copy()
    # water: reflections waver; periods of 1, 2 and 3 cycles per loop
    amp = 0.5 + 3.0 * depth ** 0.8
    dx = amp * (0.6 * np.sin(2 * np.pi * (t * 2) + yy * 0.33) + 0.4 * np.sin(2 * np.pi * (t * 3) + yy * 0.071 + xs * 0.004))
    dy = 0.5 * depth * np.sin(2 * np.pi * t + yy * 0.21 + xs * 0.002)
    sx = np.clip(xs + dx, 0, W - 1.001); sy = np.clip(yy + dy, 0, H - 1.001)
    # reeds: a small sway (two cycles per loop), only on the grass
    sway = 1.6 * np.sin(2 * np.pi * (t * 2) + xs * 0.013) * reed
    sx = np.where(reed > 0.02, np.clip(xs + sway + 0 * yy, 0, W - 1.001), sx)
    use = (water | (reed > 0.02)) & ~boat_px
    x0 = np.floor(sx).astype(np.int32); fx = (sx - x0)[..., None]
    y0 = np.floor(sy).astype(np.int32); fy = (sy - y0)[..., None]
    y0 = np.broadcast_to(y0, (H, W)); x0 = np.broadcast_to(x0, (H, W))
    fy = np.broadcast_to(fy, (H, W, 1)); fx = np.broadcast_to(fx, (H, W, 1))
    a = base[y0, x0]; b = base[y0, x0 + 1]; c = base[y0 + 1, x0]; d = base[y0 + 1, x0 + 1]
    warped = (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
    out = np.where(use[..., None], warped, out)
    # the crystal's light breathes (one cycle per loop)
    br = 1 + 0.075 * (0.5 - 0.5 * np.cos(2 * np.pi * t))
    out = out * (1 + (br - 1) * crys[..., None])
    # the mist breathes: two fields crossfade over the loop
    w1 = np.cos(np.pi * t) ** 2
    mist = np.clip((n1 * w1 + n2 * (1 - w1)) * 1.6 + 0.5, 0, 1) * haze_w * 0.07
    out = out + (haze_col - out) * mist[..., None]
    # grain
    g = rng.normal(0, 0.011, (H, W, 1)).astype(np.float32)
    out = out + g * (0.6 + 0.4 * out)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)

ppw = int(round(H * PH_AR)) // 2 * 2; ppx = (W - ppw) // 2
def enc(path, w, h, codec, scale=None):
    vf = ['-vf', f'scale={scale}:-2:flags=lanczos'] if scale else []
    if codec == 'h264':
        a = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '21', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-tune', 'grain']
    else:
        a = ['-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '31', '-row-mt', '1', '-pix_fmt', 'yuv420p', '-deadline', 'good', '-cpu-used', '2']
    return subprocess.Popen(['nice', '-n', '10', 'ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                             '-s', f'{w}x{h}', '-r', str(FR), '-i', '-', '-an'] + vf + a + [path], stdin=subprocess.PIPE)
encs = [(enc(os.path.join(OUT, 'isle-loop.mp4'), W, H, 'h264', 1920), False),
        (enc(os.path.join(OUT, 'isle-loop.webm'), W, H, 'vp9', 1920), False),
        (enc(os.path.join(OUT, 'isle-loop-phone.mp4'), ppw, H, 'h264'), True),
        (enc(os.path.join(OUT, 'isle-loop-phone.webm'), ppw, H, 'vp9'), True)]
for i in range(NF):
    f = frame(i)
    fp = np.ascontiguousarray(f[:, ppx:ppx + ppw])
    for p, phone in encs: p.stdin.write((fp if phone else f).tobytes())
    if i % 24 == 0: print('frame', i, flush=True)
for p, _ in encs: p.stdin.close(); p.wait()
print('done')
