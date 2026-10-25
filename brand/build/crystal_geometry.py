"""The Crystal A as four exact pieces: two wings, the counter, and the foot. Clipped half plane by half plane."""
import math, json
R = 50; C = (50, 50); S3 = math.sqrt(3)
def V(k): a = math.radians(-90 + 60 * k); return (C[0] + R * math.cos(a), C[1] + R * math.sin(a))
HEX = [V(k) for k in range(6)]
TOP, LR, LL = V(0), V(2), V(4)
def clip(poly, a, b, c):
    """keep the part of poly where a*x + b*y + c >= 0"""
    out = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        fp, fq = a * p[0] + b * p[1] + c, a * q[0] + b * q[1] + c
        if fp >= 0: out.append(p)
        if (fp >= 0) != (fq >= 0):
            t = fp / (fp - fq); out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out
def side(p, q, offset, ref):
    """the half plane bounded by the line p->q moved by offset towards ref, on ref's side"""
    dx, dy = q[0] - p[0], q[1] - p[1]; L = math.hypot(dx, dy); nx, ny = -dy / L, dx / L
    if nx * (ref[0] - p[0]) + ny * (ref[1] - p[1]) < 0: nx, ny = -nx, -ny     # point the normal at ref
    return nx, ny, -(nx * p[0] + ny * p[1]) - offset
def pieces(W=9.0, bar=.75, Wb=None):
    Wb = Wb or W * .9
    by = TOP[1] + (LL[1] - TOP[1]) * bar
    out_l, out_r, mid = HEX[5], HEX[1], (50, 60)
    wing_l = clip(HEX, *side(TOP, LL, W / 2, out_l))
    wing_r = clip(HEX, *side(TOP, LR, W / 2, out_r))
    inner = clip(clip(HEX, *side(TOP, LL, W / 2, mid)), *side(TOP, LR, W / 2, mid))
    counter = clip(inner, 0, -1, by - Wb / 2)
    foot = clip(inner, 0, 1, -(by + Wb / 2))
    r = lambda pts: [(round(x, 3), round(y, 3)) for x, y in pts]
    return {"wing_l": r(wing_l), "wing_r": r(wing_r), "counter": r(counter), "foot": r(foot), "W": W, "bar_y": round(by, 3)}
if __name__ == "__main__":
    p = pieces(); json.dump(p, open("pieces.json", "w"), indent=1)
    for k, v in p.items(): print(k, v)
