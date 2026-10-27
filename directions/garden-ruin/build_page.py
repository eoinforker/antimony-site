# Builds index.html from page.src.html: the wordmark, and the layout measured from the render
# (frame size, the letter and the stone as fractions of each framing, the depth pivot at the stone).
#   python3 -I build_page.py <render.json> <wordmark.svg>
import sys, os, json
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
info = json.load(open(sys.argv[1]))
wm = open(sys.argv[2]).read().strip()
W, H = info['w'], info['h']

def phone_box():
    cw = int(round(H * 9 / 16))
    # the stone whole and the letter beside it, centred together; if both cannot fit, the stone stays whole
    L_, S_ = info['letter'], info['stone']
    a = min(L_[0], S_[0]) * W; b = max(L_[2], S_[2]) * W
    x0 = (a + b) / 2 - cw / 2
    x0 = min(x0, S_[0] * W - 0.04 * cw)
    x0 = max(x0, S_[2] * W + 0.04 * cw - cw)
    x0 = int(np.clip(x0, 0, W - cw))
    return x0, cw

def pivot(path, st):
    d = np.asarray(Image.open(path).convert('RGB'), np.float32)[..., 0] / 255.0
    h, w = d.shape
    x0, y0, x1, y1 = int(st[0] * w), int(st[1] * h), int(st[2] * w), int(st[3] * h)
    return float(np.median(d[y0:y1, x0:x1]))

x0, cw = phone_box()
def to_phone(b):
    return [(b[0] * W - x0) / cw, b[1], (b[2] * W - x0) / cw, b[3]]

A = os.path.join(HERE, 'assets')
L = {'desk': {'w': 1920, 'h': 1080, 'fx': 0.56, 'letter': info['letter'], 'stone': info['stone'],
              'pivot': round(pivot(os.path.join(A, 'garden-depth.webp'), info['stone']), 4)},
     'phone': {'w': 1080, 'h': 1920, 'fx': 0.5, 'letter': to_phone(info['letter']), 'stone': to_phone(info['stone']),
               'pivot': round(pivot(os.path.join(A, 'garden-depth-phone.webp'), to_phone(info['stone'])), 4)}}
for k in L:
    for kk in ('letter', 'stone'): L[k][kk] = [round(v, 4) for v in L[k][kk]]
src = open(os.path.join(HERE, 'page.src.html')).read()
src = src.replace('@@WORDMARK@@', '  ' + wm).replace('@@LAYOUT@@', json.dumps(L))
open(os.path.join(HERE, 'index.html'), 'w').write(src)
print(json.dumps(L))
