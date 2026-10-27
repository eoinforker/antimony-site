"""The hero terrain as a height function, shared by the mesh generator and the scatter in the editor.

Units are metres. The camera stands near the origin looking down +X, up a slope of flowers to a crest; past the
crest the ground falls into a misty valley and rises again to far ridges under the crystal. Pure Python, so it
runs both outside Unreal (gen_meshes.py) and inside it (build_world.py).
"""
import math

CREST_X = 42.0     # the near crest the flowers climb to
CREST_H = 7.0
VALLEY_H = -35.0   # the misty valley floor past the crest
RIDGE_X = 900.0    # where the far ground starts to rise toward the crystal


def _smooth(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def _noise(x, y, scale, seed):
    """Cheap smooth noise: a few rotated sine waves. Good enough for rolling ground."""
    s = 0.0
    for i, (a, f) in enumerate([(1.0, 1.0), (0.5, 2.03), (0.25, 4.11), (0.125, 8.37)]):
        ang = seed * 1.7 + i * 2.1
        u = (x * math.cos(ang) + y * math.sin(ang)) / scale * f
        v = (-x * math.sin(ang) + y * math.cos(ang)) / scale * f
        s += a * math.sin(u + seed + i) * math.cos(v * 0.83 + seed * 2 + i)
    return s / 1.875


def height(x, y):
    # The near slope: rises from the camera to the crest, rolling side to side.
    near = CREST_H * _smooth(-10.0, CREST_X, x) + 1.6 * _noise(x, y, 22.0, 1.0) + 0.5 * _noise(x, y, 6.0, 4.0)
    # Past the crest: down into the valley, then up toward the far ridges.
    fall = _smooth(CREST_X + 8.0, CREST_X + 140.0, x)
    far = VALLEY_H + 80.0 * _smooth(RIDGE_X * 0.4, RIDGE_X * 1.6, x) + 18.0 * _noise(x, y, 160.0, 7.0)
    # Banks either side of the near slope frame the view (rock on the right, firs on the left).
    bank = 5.0 * _smooth(28.0, 70.0, abs(y)) * (1.0 - fall)
    return near * (1.0 - fall) + far * fall + bank


def normal(x, y, e=0.25):
    dx = (height(x + e, y) - height(x - e, y)) / (2 * e)
    dy = (height(x, y + e) - height(x, y - e)) / (2 * e)
    n = (-dx, -dy, 1.0)
    length = math.sqrt(sum(c * c for c in n))
    return tuple(c / length for c in n)
