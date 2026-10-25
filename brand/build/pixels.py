"""Pixel drawings of the Bond for 16 and 32 px, sampled at pixel centres with the atoms' centres placed on pixel centres,
so every diamond is a clean stepped diamond rather than a blur. Writes ../exports/icons/favicon-16.png and -32.png and pixels.json."""
import json
from PIL import Image
G = json.load(open("geo.json")); A = G["atoms"]; R = G["R"]; W = G["W"]
INK, COB, PAPER = (11, 13, 12), (36, 72, 255), (244, 243, 238)
def inside(u, v):
    for k, (x, y) in A.items():
        if abs(u - x) + abs(v - y) <= R: return 2 if k == "nucleus" else 1
    for a, b in G["bonds"]:
        (x1, y1), (x2, y2) = A[a], A[b]
        if x1 == x2 and abs(u - x1) <= W / 2 and min(y1, y2) <= v <= max(y1, y2): return 1
        if y1 == y2 and abs(v - y1) <= W / 2 and min(x1, x2) <= u <= max(x1, x2): return 1
    return 0
def draw(n, s):
    # s: pixels per 100 units; place the nucleus centre on a pixel centre in the middle of the grid
    cx, cy = n / 2 - 0.5 + 0.5, n / 2 - 0.5 + 0.5 - 0.5 * 0          # pixel centre nearest the middle
    ox = (n // 2 + 0.5) - A["nucleus"][0] * s / 100
    oy = (n // 2 + 0.5) - A["nucleus"][1] * s / 100 - (0 if n == 16 else 0)
    grid = []
    for j in range(n):
        row = ""
        for i in range(n):
            u = (i + 0.5 - ox) * 100 / s; v = (j + 0.5 - oy) * 100 / s
            row += ".12"[inside(u, v)]
        grid.append(row)
    return grid
out = {"16": draw(16, 16 * 100 / 100 * 0.968), "32": draw(32, 32 * 0.968)}
for n, g in out.items():
    im = Image.new("RGBA", (int(n), int(n)), PAPER + (255,))
    for j, row in enumerate(g):
        for i, c in enumerate(row):
            if c != ".": im.putpixel((i, j), (INK if c == "1" else COB) + (255,))
    im.save(f"../exports/icons/favicon-{n}.png")
    print("\n".join(g)); print()
json.dump(out, open("pixels.json", "w"))
