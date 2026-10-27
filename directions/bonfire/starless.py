# grey opening (min then max filter) removes point stars from the night HDRI, keeping the Milky Way's glow and dust
import bpy, sys, numpy as np
a = sys.argv[sys.argv.index('--') + 1:]
im = bpy.data.images.load(a[0]); w, h = im.size
px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
c = px[:, :, :3]
def filt(x, r, fn):
    out = x.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx == 0 and dy == 0: continue
            sh = np.roll(np.roll(x, dy, 0), dx, 1)
            out = fn(out, sh)
    return out
R = int(a[2]) if len(a) > 2 else 3
o = filt(filt(c, R, np.minimum), R, np.maximum)
# soften the blocky residue a little
o = (o + np.roll(o, 1, 0) + np.roll(o, -1, 0) + np.roll(o, 1, 1) + np.roll(o, -1, 1)) / 5
px[:, :, :3] = o
im2 = bpy.data.images.new('starless', w, h, float_buffer=True); im2.colorspace_settings.name = im.colorspace_settings.name
im2.pixels = px.ravel()
print('pre', np.percentile(o[h//2:].mean(-1), [5, 50, 95])); im2.filepath_raw = a[1]; im2.file_format = 'HDR'; im2.save()
print('saved', a[1])
