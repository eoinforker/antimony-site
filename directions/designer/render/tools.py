# Small helpers: read EXR through ffmpeg, the AgX approximation the page uses, blur, save.
import subprocess, json, numpy as np
from PIL import Image

def load_exr(path):
    info = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                           '-of', 'json', path], capture_output=True, text=True).stdout
    s = json.loads(info)['streams'][0]; w, h = s['width'], s['height']
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-apply_trc', 'linear', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'gbrapf32le', '-'],
                         capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.float32)[:w * h * 4].reshape(4, h, w)
    g, b, r, al = a
    return np.stack([r, g, b, al], -1).copy()

C_IN = np.array([[0.842479062253094, 0.0423282422610123, 0.0423756549057051],
                 [0.0784335999999992, 0.878468636469772, 0.0784336],
                 [0.0792237451477643, 0.0791661274605434, 0.879142973793104]])
C_OUT = np.array([[1.19687900512017, -0.0528968517574562, -0.0529716355144438],
                  [-0.0980208811401368, 1.15190312990417, -0.0980434501171241],
                  [-0.0990297440797205, -0.0989611768448433, 1.15107367264116]])

def agx(lin, exposure=0.0):
    v = np.maximum(lin[..., :3] * (2.0 ** exposure), 1e-10) @ C_IN
    lo, hi = -12.47393, 4.026069
    v = (np.clip(np.log2(v), lo, hi) - lo) / (hi - lo)
    x2 = v * v; x4 = x2 * x2
    v = 15.5 * x4 * x2 - 40.14 * x4 * v + 31.96 * x4 - 6.868 * x2 * v + 0.4298 * x2 + 0.1191 * v - 0.00232
    v = v @ C_OUT
    return np.clip(v, 0, 1)

def save(img01, path, q=None):
    im = Image.fromarray((np.clip(img01, 0, 1) * 255 + 0.5).astype(np.uint8))
    if q is None: im.save(path)
    else: im.save(path, quality=q, method=6)

def blur(x, rad):
    for _ in range(3):
        for ax in (0, 1):
            pad = [(0, 0)] * x.ndim; pad[ax] = (rad + 1, rad)
            c = np.cumsum(np.pad(x, pad, mode='edge'), axis=ax); n = x.shape[ax]
            x = (np.take(c, np.arange(2 * rad + 1, 2 * rad + 1 + n), axis=ax) - np.take(c, np.arange(n), axis=ax)) / (2 * rad + 1)
    return x

if __name__ == '__main__':
    import sys
    a = load_exr(sys.argv[1]); ex = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    print('max', a[..., :3].max(), 'mean', a[..., :3].mean())
    save(agx(a, ex), sys.argv[2])
