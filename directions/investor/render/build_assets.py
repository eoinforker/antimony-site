# Build the web assets from the composed frames.
#   python3 build_assets.py <frames dir (f_0001.png ...)> <masks dir> <site assets dir> [nframes]
# Writes: hero/still-2560|1920.(avif|webp), hero/still-portrait.(avif|webp), hero/loop(-portrait).(mp4|webm)
# (encoded by ffmpeg from the same frames), hero/crystal(-portrait).png masks and frame.json.
import sys, os, json, base64, io, subprocess
import numpy as np
from PIL import Image

FR, MK, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
NF = int(sys.argv[4]) if len(sys.argv) > 4 else 0
LOOP = sys.argv[5] if len(sys.argv) > 5 else FR
HERO = os.path.join(OUT, 'hero'); os.makedirs(HERO, exist_ok=True)

f1 = Image.open(os.path.join(FR, 'f_0001.png')).convert('RGB')
W, H = f1.size
cr = np.load(os.path.join(MK, 'crystal.npy'))
mh, mw = cr.shape
ys, xs = np.where(cr > 0.02)
# the crystal box in frame fractions, with a little room
pad = 0.15
x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
bw, bh = x1 - x0, y1 - y0
x0 = max(0, int(x0 - bw * pad)); x1 = min(mw, int(x1 + bw * pad)); y0 = max(0, int(y0 - bh * pad)); y1 = min(mh, int(y1 + bh * pad))
cbox = [x0 / mw, y0 / mh, (x1 - x0) / mw, (y1 - y0) / mh]
cx = (xs.mean()) / mw

# portrait crop: 9 by 16, centred on the stone's axis
pw = int(round(H * 9 / 16)); pw -= pw % 2
px0 = int(round(cx * W - pw / 2)); px0 = max(0, min(W - pw, px0))
pfx = px0 / W

def save_still(im, name, q_avif=66, q_webp=82):
    im.save(os.path.join(HERO, name + '.avif'), quality=q_avif, speed=2)
    im.save(os.path.join(HERO, name + '.webp'), quality=q_webp, method=6)

save_still(f1, 'still-2560') if W >= 2560 else None
save_still(f1.resize((1920, 1080), Image.LANCZOS) if W != 1920 else f1, 'still-1920')
pim = f1.crop((px0, 0, px0 + pw, H))
save_still(pim, 'still-portrait')

def ph(im, w):
    h = max(1, round(w * im.size[1] / im.size[0]))
    b = io.BytesIO(); im.resize((w, h), Image.LANCZOS).save(b, 'WEBP', quality=40)
    return 'data:image/webp;base64,' + base64.b64encode(b.getvalue()).decode()

def mask_png(box, name):
    a = cr[int(box[1] * mh):int((box[1] + box[3]) * mh), int(box[0] * mw):int((box[0] + box[2]) * mw)]
    a = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    rgba = np.dstack([np.full_like(a, 255)] * 3 + [a])
    Image.fromarray(rgba, 'RGBA').save(os.path.join(HERO, name), optimize=True)

mask_png(cbox, 'crystal.png')
pbox = [(cbox[0] - pfx) * W / pw, cbox[1], cbox[2] * W / pw, cbox[3]]
frame = {
    'landscape': {'w': W, 'h': H, 'crystal': [round(v, 5) for v in cbox], 'mask': 'assets/hero/crystal.png', 'video': 'assets/hero/loop', 'ph': ph(f1, 32)},
    'portrait': {'w': pw, 'h': H, 'crystal': [round(v, 5) for v in pbox], 'mask': 'assets/hero/crystal.png', 'video': 'assets/hero/loop-portrait', 'ph': ph(pim, 16)},
    'crop_x': px0, 'crop_w': pw,
}
json.dump(frame, open(os.path.join(HERO, 'frame.json'), 'w'))
print(json.dumps({k: v for k, v in frame.items() if k in ('crop_x', 'crop_w')}), cbox)

if NF:
    pat = os.path.join(LOOP, 'f_%04d.png')
    lw, lh = Image.open(os.path.join(LOOP, 'f_0001.png')).size
    k = lw / W; lpw = int(round(pw * k)); lpw -= lpw % 2; lpx = int(round(px0 * k))
    def run(a): print(' '.join(a)); subprocess.run(a, check=True)
    common = ['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '24', '-i', pat, '-frames:v', str(NF)]
    vf_l = 'scale=1920:1080:flags=lanczos' if lw != 1920 else 'null'
    vf_p = 'crop=%d:%d:%d:0,scale=720:1280:flags=lanczos' % (lpw, lh, lpx)
    for vf, nm in ((vf_l, 'loop'), (vf_p, 'loop-portrait')):
        run(common + ['-vf', vf + ',format=yuv420p', '-c:v', 'libx264', '-preset', 'veryslow', '-crf', '21', '-tune', 'film', '-movflags', '+faststart', '-an', os.path.join(HERO, nm + '.mp4')])
        run(common + ['-vf', vf + ',format=yuv420p', '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '34', '-row-mt', '1', '-deadline', 'good', '-cpu-used', '2', '-an', os.path.join(HERO, nm + '.webm')])
