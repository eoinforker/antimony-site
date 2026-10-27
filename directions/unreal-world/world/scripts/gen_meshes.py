"""Generate the hero's own meshes as OBJ: the terrain and the giant crystal with the Break inside.

  python3 gen_meshes.py <out_dir>

Coordinates are written in Unreal's frame (X forward, Y right, Z up) in centimetres; build_world.py checks the
imported bounds, so an axis swap on import shows up at once.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from terrain import height  # noqa: E402

M = 100.0  # metres to centimetres

# The crystal: the mark's hexagon (viewBox 0-100) turned into a hexagonal bipyramid.
CRYSTAL_UNIT_M = 20.0           # one mark unit; the crystal is 90 units tall = 1.8 km
CRYSTAL_CENTRE_M = (3200.0, 0.0, 1100.0)
BREAK_STROKE = 2.2              # line thickness in mark units (the print uses 5.2; thinner reads better at scale)


class Obj:
    def __init__(self):
        self.v, self.vn, self.f = [], [], []

    def vert(self, p):
        self.v.append(p)
        return len(self.v)

    def tri(self, a, b, c, n=None):
        if n is None:
            u = [b[i] - a[i] for i in range(3)]
            w = [c[i] - a[i] for i in range(3)]
            n = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
        length = math.sqrt(sum(x * x for x in n)) or 1.0
        self.vn.append(tuple(x / length for x in n))
        ni = len(self.vn)
        ia, ib, ic = self.vert(a), self.vert(b), self.vert(c)
        self.f.append(((ia, ni), (ib, ni), (ic, ni)))

    def write(self, path, name):
        with open(path, "w") as fh:
            fh.write(f"o {name}\n")
            fh.writelines(f"v {x:.2f} {y:.2f} {z:.2f}\n" for x, y, z in self.v)
            fh.writelines(f"vn {x:.5f} {y:.5f} {z:.5f}\n" for x, y, z in self.vn)
            fh.writelines("f " + " ".join(f"{v}//{n}" for v, n in face) + "\n" for face in self.f)


def grid(obj, x0, x1, y0, y1, step, skip=None):
    """Heightfield grid with smooth shared normals (one vertex per sample)."""
    nx, ny = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
    idx = {}
    for i in range(nx):
        for j in range(ny):
            x, y = x0 + i * step, y0 + j * step
            e = step * 0.5
            dx = (height(x + e, y) - height(x - e, y)) / (2 * e)
            dy = (height(x, y + e) - height(x, y - e)) / (2 * e)
            obj.v.append((x * M, y * M, height(x, y) * M))
            obj.vn.append((-dx, -dy, 1.0))
            idx[i, j] = len(obj.v)
    for i in range(nx - 1):
        for j in range(ny - 1):
            x, y = x0 + (i + 0.5) * step, y0 + (j + 0.5) * step
            if skip and skip(x, y):
                continue
            a, b, c, d = idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1]
            # Counter-clockwise seen from above (+Z), so the faces point up.
            obj.f.append(((a, a), (b, b), (c, c)))
            obj.f.append(((a, a), (c, c), (d, d)))


def crystal():
    """Hexagonal bipyramid: apexes at mark y=5 and 95, shoulders at 29 and 71, half-width 28."""
    cx, cy, cz = (c * M for c in CRYSTAL_CENTRE_M)
    u = CRYSTAL_UNIT_M * M
    ring = lambda z: [(cx + 28 * u * math.cos(math.radians(30 + 60 * k)),
                       cy + 28 * u * math.sin(math.radians(30 + 60 * k)), cz + z * u) for k in range(6)]
    top, bot = (cx, cy, cz + 45 * u), (cx, cy, cz - 45 * u)
    up, lo = ring(21), ring(-21)
    obj = Obj()
    for k in range(6):
        k2 = (k + 1) % 6
        obj.tri(top, up[k], up[k2])
        obj.tri(up[k], lo[k], lo[k2])
        obj.tri(up[k], lo[k2], up[k2])
        obj.tri(bot, lo[k2], lo[k])
    return obj


def break_mark():
    """The Break as light inside the crystal: the A, the chevron and the stem, in the plane facing the camera."""
    cx, cy, cz = (c * M for c in CRYSTAL_CENTRE_M)
    u = CRYSTAL_UNIT_M * M
    to3 = lambda mx, my: (cx, cy + (mx - 50) * u, cz + (50 - my) * u)
    lines = [((22, 71), (50, 15)), ((50, 15), (78, 71)), ((22, 71), (50, 58)), ((50, 58), (78, 71)), ((50, 3), (50, 15))]
    h = BREAK_STROKE * u / 2
    obj = Obj()
    for a, b in lines:
        p, q = to3(*a), to3(*b)
        d = [q[i] - p[i] for i in range(3)]
        length = math.sqrt(sum(x * x for x in d))
        d = [x / length for x in d]
        side = (0.0, -d[2], d[1])            # in the Y-Z plane, perpendicular to the stroke
        depth = (1.0, 0.0, 0.0)
        # Extend each stroke by half its width so the joints meet cleanly.
        p = [p[i] - d[i] * h for i in range(3)]
        q = [q[i] + d[i] * h for i in range(3)]
        corners = []
        for end in (p, q):
            for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                corners.append(tuple(end[i] + s * h * side[i] + t * h * depth[i] for i in range(3)))
        quads = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (3, 2, 1, 0), (4, 5, 6, 7)]
        for a_, b_, c_, d_ in quads:
            A, B, C, D = (corners[i] for i in (a_, b_, c_, d_))
            obj.tri(A, B, C)
            obj.tri(A, C, D)
    return obj


def main(out):
    os.makedirs(out, exist_ok=True)
    near = Obj()
    grid(near, -40, 200, -160, 160, 1.0)
    near.write(os.path.join(out, "SM_TerrainNear.obj"), "SM_TerrainNear")
    far = Obj()
    grid(far, -400, 7000, -5000, 5000, 25.0, skip=lambda x, y: x < 190 and abs(y) < 150)
    far.write(os.path.join(out, "SM_TerrainFar.obj"), "SM_TerrainFar")
    crystal().write(os.path.join(out, "SM_Crystal.obj"), "SM_Crystal")
    break_mark().write(os.path.join(out, "SM_Break.obj"), "SM_Break")
    print("wrote", sorted(os.listdir(out)))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "gen")
