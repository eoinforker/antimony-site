# Dawn over the Plate: the film grade laid over the Cycles render.
# Halation (red-orange bleed round the brightest light, as on colour negative), a soft vignette and fine grain.
# Run: python3 dawn_post.py <render.png> <out.png>
import sys
import numpy as np
from PIL import Image, ImageFilter

src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGB')
a = np.asarray(im).astype(np.float32) / 255.0
h, w, _ = a.shape

# halation: highlights bleed a warm red into their surroundings
lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
hi = np.clip((lum - 0.72) / 0.28, 0, 1)
hi_img = Image.fromarray((hi * 255).astype(np.uint8))
glow = np.asarray(hi_img.filter(ImageFilter.GaussianBlur(w * 0.012))).astype(np.float32) / 255.0
wide = np.asarray(hi_img.filter(ImageFilter.GaussianBlur(w * 0.04))).astype(np.float32) / 255.0
hal = (0.55 * glow + 0.45 * wide)[..., None] * np.array([1.0, 0.42, 0.30], np.float32)
a = a + 0.22 * hal * (1 - a)

# vignette: a gentle fall-off to the corners
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 * 0.85 + ((yy - h / 2) / (h / 2)) ** 2 * 0.6)
a = a * (1 - 0.32 * np.clip(d - 0.35, 0, 1) ** 1.6)[..., None]

# grain: fine, luminance-weighted, strongest in the mid tones
rng = np.random.default_rng(3)
g = rng.normal(0, 1, (h, w)).astype(np.float32)
g = np.asarray(Image.fromarray(((g * 0.25 + 0.5).clip(0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32) / 255.0 - 0.5
mid = 4 * lum * (1 - lum)
a = a + (0.075 * g * (0.35 + 0.65 * mid))[..., None]

Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).save(dst)
print('graded', dst)
