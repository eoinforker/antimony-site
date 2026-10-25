"""A brush. A stroke is a few control points and a weight; it comes out as one filled outline that tapers at both
ends, swells with pressure, wanders a little off its line and never repeats exactly. Seeded, so a drawing is the same
drawing every time it is rendered."""
import math, random
f = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")
def catmull(pts, n=18):
    if len(pts) < 3:
        (x0, y0), (x1, y1) = pts; return [(x0 + (x1 - x0) * t / (n * 2), y0 + (y1 - y0) * t / (n * 2)) for t in range(n * 2 + 1)]
    P = [pts[0]] + pts + [pts[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n; t2, t3 = t * t, t * t * t
            out.append(tuple(.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(pts[-1]); return out
def smooth_noise(rng, n, scale):
    """a slow wander: a few random values, eased between"""
    knots = [rng.uniform(-1, 1) for _ in range(max(3, n // 9 + 2))]
    out = []
    for i in range(n):
        u = i / max(1, n - 1) * (len(knots) - 1); k = int(u); t = u - k; t = t * t * (3 - 2 * t)
        out.append((knots[k] * (1 - t) + knots[min(k + 1, len(knots) - 1)] * t) * scale)
    return out
def stroke(pts, w, seed=1, taper=(.18, .28), wobble=.9, press=.28, end_blob=0.0):
    rng = random.Random(seed)
    jit = [(x + rng.uniform(-.6, .6) * wobble, y + rng.uniform(-.6, .6) * wobble) for x, y in pts]
    path = catmull(jit); n = len(path)
    off = smooth_noise(rng, n, wobble * .9); pr = smooth_noise(rng, n, press)
    L, R = [], []
    for i in range(n):
        a = path[max(0, i - 1)]; b = path[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]; d = math.hypot(dx, dy) or 1; nx, ny = -dy / d, dx / d
        t = i / (n - 1)
        prof = min(1, t / taper[0]) if t < taper[0] else (min(1, (1 - t) / taper[1]) if t > 1 - taper[1] else 1)
        prof = math.sin(prof * math.pi / 2) ** .8
        hw = w / 2 * max(.06, prof * (1 + pr[i])) + end_blob * w * max(0, t - .9) * 3
        cx, cy = path[i][0] + nx * off[i], path[i][1] + ny * off[i]
        L.append((cx + nx * hw, cy + ny * hw)); R.append((cx - nx * hw, cy - ny * hw))
    pts = L + R[::-1]
    return "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"
def dab(cx, cy, r, seed=1, sides=14, rough=.16):
    rng = random.Random(seed); pts = []
    for k in range(sides):
        a = 2 * math.pi * k / sides; rr = r * (1 + rng.uniform(-rough, rough))
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    pts = catmull(pts + pts[:3], 4)[: sides * 4]
    return "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"
def scribble(x0, y0, x1, y1, rows, w, seed=1, lean=0):
    """a hand colouring in a rectangle: back and forth, a little outside the lines"""
    rng = random.Random(seed); pts = []
    for r in range(rows):
        y = y0 + (y1 - y0) * r / max(1, rows - 1)
        a = x0 + rng.uniform(-2, 1.5); b = x1 + rng.uniform(-1.5, 2)
        pts += [(a + lean * r, y), (b + lean * r, y + (y1 - y0) / rows * .5)] if r % 2 == 0 else [(b + lean * r, y), (a + lean * r, y + (y1 - y0) / rows * .5)]
    return stroke(pts, w, seed, taper=(.05, .08), wobble=.5, press=.2)
# the grain of a dry brush on washi, applied as a filter on the whole drawing
GRAIN = ('<filter id="{id}" x="-5%" y="-5%" width="110%" height="110%">'
         '<feTurbulence type="fractalNoise" baseFrequency=".75" numOctaves="2" seed="{seed}" result="g"/>'
         '<feColorMatrix in="g" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -1.1 1.62" result="m"/>'
         '<feComposite in="SourceGraphic" in2="m" operator="in" result="dry"/>'
         '<feTurbulence type="fractalNoise" baseFrequency=".035" numOctaves="2" seed="{seed}" result="w"/>'
         '<feDisplacementMap in="dry" in2="w" scale="1.1" xChannelSelector="R" yChannelSelector="G"/></filter>')
