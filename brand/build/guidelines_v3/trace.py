"""Traces the Orbe lockup (src/orbe-lockup.png, dark on cream, 3840 px wide) into an SVG path, so the product
lockups can be drawn as vectors. Marching squares on the luminance at its middle level, then Douglas-Peucker."""
import json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))

def contours(a, iso):
    h, w = a.shape
    b = a < iso
    # cells: corners tl, tr, br, bl
    tl, tr, br, bl = b[:-1, :-1], b[:-1, 1:], b[1:, 1:], b[1:, :-1]
    code = tl.astype(np.uint8) * 8 + tr * 4 + br * 2 + bl * 1
    ys, xs = np.nonzero((code > 0) & (code < 15))
    def ip(p0, p1, v0, v1):
        t = (iso - v0) / (v1 - v0) if v1 != v0 else .5
        return (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)
    seg = {}
    def add(e0, e1):
        seg.setdefault(e0, []).append(e1); seg.setdefault(e1, []).append(e0)
    pos = {}
    for y, x in zip(ys.tolist(), xs.tolist()):
        c = int(code[y, x])
        # edges: T (top), R, B, L as keys
        T, Rr, B, L = ("h", y, x), ("v", y, x + 1), ("h", y + 1, x), ("v", y, x)
        def P(e):
            if e in pos: return
            k, yy, xx = e
            if k == "h": pos[e] = ip((xx, yy), (xx + 1, yy), a[yy, xx], a[yy, xx + 1])
            else: pos[e] = ip((xx, yy), (xx, yy + 1), a[yy, xx], a[yy + 1, xx])
        table = {1: [(L, B)], 2: [(B, Rr)], 3: [(L, Rr)], 4: [(T, Rr)], 6: [(T, B)], 7: [(L, T)], 8: [(L, T)], 9: [(T, B)],
                 11: [(T, Rr)], 12: [(L, Rr)], 13: [(B, Rr)], 14: [(L, B)]}
        if c in (5, 10):
            centre = (a[y, x] + a[y, x + 1] + a[y + 1, x + 1] + a[y + 1, x]) / 4 < iso
            if c == 5: pairs = [(L, T), (B, Rr)] if centre else [(L, B), (T, Rr)]
            else: pairs = [(T, Rr), (L, B)] if centre else [(L, T), (B, Rr)]
        else:
            pairs = table[c]
        for e0, e1 in pairs:
            P(e0); P(e1); add(e0, e1)
    loops, seen = [], set()
    for start in list(seg):
        if start in seen: continue
        loop = [start]; seen.add(start); prev, cur = None, start
        while True:
            nxt = [n for n in seg[cur] if n != prev and n not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]; seen.add(cur); loop.append(cur)
        if len(loop) > 8: loops.append([pos[e] for e in loop])
    return loops

def dp(ps, eps):
    ps = np.asarray(ps)
    if len(ps) < 3: return ps.tolist()
    keep = np.zeros(len(ps), bool); keep[0] = keep[-1] = True
    stack = [(0, len(ps) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1: continue
        a, b = ps[i], ps[j]; d = b - a; n = np.hypot(*d) or 1
        seg = ps[i + 1:j]
        dist = np.abs(d[0] * (seg[:, 1] - a[1]) - d[1] * (seg[:, 0] - a[0])) / n
        k = int(np.argmax(dist))
        if dist[k] > eps:
            m = i + 1 + k; keep[m] = True; stack += [(i, m), (m, j)]
    return ps[keep].tolist()

def main():
    im = Image.open(os.path.join(HERE, "src/orbe-lockup.png")).convert("L")
    a = np.asarray(im, dtype=np.float32)
    # a light blur so the iso line is smooth
    k = np.array([1, 4, 6, 4, 1], np.float32); k /= k.sum()
    a = np.apply_along_axis(lambda r: np.convolve(r, k, "same"), 1, a)
    a = np.apply_along_axis(lambda c: np.convolve(c, k, "same"), 0, a)
    lo, hi = np.percentile(a, 1), np.percentile(a, 99)
    loops = [[(float(x), float(y)) for x, y in l] for l in contours(a, float((lo + hi) / 2))]
    xs = [p[0] for l in loops for p in l]; ys = [p[1] for l in loops for p in l]
    x0, x1, y0, y1 = float(min(xs)), float(max(xs)), float(min(ys)), float(max(ys))
    # split into the mark (left of the gap) and the wordmark
    mark, word = [], []
    for l in loops:
        cx = sum(p[0] for p in l) / len(l)
        (mark if cx < 640 else word).append(l)
    def path(ls, ox, oy, s):
        out = ""
        for l in ls:
            m = len(l) // 2
            q = dp(l[:m + 1], .45)[:-1] + dp(l[m:] + [l[0]], .45)[:-1]
            out += "M" + "L".join(f"{(x - ox) * s:.2f} {(y - oy) * s:.2f}" for x, y in q) + "Z"
        return out
    # units: the lockup's height becomes 100
    s = 100 / (y1 - y0)
    mx1 = max(p[0] for l in mark for p in l); wx0 = min(p[0] for l in word for p in l)
    mys = [p[1] for l in mark for p in l]
    res = {"mark": path(mark, x0, y0, s), "word": path(word, x0, y0, s), "w": round((x1 - x0) * s, 2), "h": 100,
           "mark_w": round((mx1 - x0) * s, 2), "word_x": round((wx0 - x0) * s, 2),
           "mark_top": round((min(mys) - y0) * s, 2), "mark_bot": round((max(mys) - y0) * s, 2)}
    # the wordmark's baseline: the bottom of the O, r, b
    json.dump(res, open(os.path.join(HERE, "src/orbe-trace.json"), "w"))
    print({k: v for k, v in res.items() if k not in ("mark", "word")}, len(res["mark"]), len(res["word"]), len(loops))

if __name__ == "__main__":
    main()
