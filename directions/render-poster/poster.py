# Poster 1, path traced: one wet concrete wall at night, one slim lightbox behind wet glass
# showing the Grow meadow, rain, wet pavement, a cool lamp off frame to the left.
#
# Run headless with Blender 4.2 LTS or newer:
#   blender -b -P poster.py -- --variant night --out night.png
#   blender -b -P poster.py -- --variant overgrown --out overgrown.png
# Options: --res <percent of 1920x1200>, --samples <max>, --tl <seconds>, --print <png>
#
# Everything is procedural. The only image is the print, made from Antimony's own Grow page
# (directions/grow/shots/rest-desktop.png), cropped to a portrait sheet, with the Break mark
# redrawn from its exact geometry so that nothing grows on it.
#
# World, in metres: the wall is the plane Y = 0 facing the camera, the pavement is Z = 0,
# X runs along the wall. The box is 1.16 by 1.74, its foot 0.17 above the pavement, as in the
# real-time version, and the camera matches its framing: straight on, four degrees off axis.

import bpy, bmesh, math, random, sys, os, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))

def arg(name, default):
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return a[a.index(name) + 1] if name in a else default

VARIANT = arg('--variant', 'night')
OUT = arg('--out', os.path.join(HERE, VARIANT + '.png'))
RES = int(arg('--res', '100'))
SAMPLES = int(arg('--samples', '1024'))
TL = float(arg('--tl', '1320'))
PRINT_SRC = arg('--print', os.path.join(ROOT, 'grow', 'shots', 'rest-desktop.png'))
GREEN = VARIANT == 'overgrown'
LOOP = False
NFR = 72
rng = random.Random(11)
nrng = np.random.default_rng(11)

bpy.ops.wm.read_factory_settings(use_empty=True)
SC = bpy.context.scene

# ---------------------------------------------------------------- node helpers
class S:
    """A float socket; arithmetic makes Math nodes."""
    def __init__(s, g, k): s.g, s.k = g, k
    def __add__(s, o): return s.g.m('ADD', s, o)
    def __radd__(s, o): return s.g.m('ADD', o, s)
    def __sub__(s, o): return s.g.m('SUBTRACT', s, o)
    def __rsub__(s, o): return s.g.m('SUBTRACT', o, s)
    def __mul__(s, o): return s.g.m('MULTIPLY', s, o)
    def __rmul__(s, o): return s.g.m('MULTIPLY', o, s)
    def __truediv__(s, o): return s.g.m('DIVIDE', s, o)
    def __rtruediv__(s, o): return s.g.m('DIVIDE', o, s)
    def __neg__(s): return s.g.m('MULTIPLY', s, -1.0)

class V:
    """A vector or colour socket."""
    def __init__(s, g, k): s.g, s.k = g, k

class G:
    def __init__(s, nt): s.nt = nt
    def new(s, t, **kw):
        n = s.nt.nodes.new(t)
        for k, v in kw.items(): setattr(n, k, v)
        return n
    def put(s, inp, val):
        if isinstance(val, (S, V)): s.nt.links.new(val.k, inp)
        elif isinstance(val, bpy.types.NodeSocket): s.nt.links.new(val, inp)
        elif isinstance(val, (tuple, list)):
            dv = inp.default_value
            val = tuple(val) + (1.0,) * (len(dv) - len(val))
            inp.default_value = val[:len(dv)]
        else: inp.default_value = val
    def m(s, op, a, b=None, c=None, clamp=False):
        n = s.new('ShaderNodeMath', operation=op, use_clamp=clamp)
        for i, x in enumerate((a, b, c)):
            if x is not None: s.put(n.inputs[i], x)
        return S(s, n.outputs[0])
    def floor(s, x): return s.m('FLOOR', x)
    def fract(s, x): return s.m('FRACT', x)
    def abs(s, x): return s.m('ABSOLUTE', x)
    def min(s, a, b): return s.m('MINIMUM', a, b)
    def max(s, a, b): return s.m('MAXIMUM', a, b)
    def sin(s, x): return s.m('SINE', x)
    def cos(s, x): return s.m('COSINE', x)
    def exp(s, x): return s.m('EXPONENT', x)
    def pow(s, a, b): return s.m('POWER', a, b)
    def clamp(s, x): return s.m('ADD', x, 0.0, clamp=True)
    def sm(s, e0, e1, x):
        n = s.new('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP', clamp=True)
        s.put(n.inputs[0], x); s.put(n.inputs[1], e0); s.put(n.inputs[2], e1)
        s.put(n.inputs[3], 0.0); s.put(n.inputs[4], 1.0)
        return S(s, n.outputs[0])
    def lin(s, e0, e1, x):
        n = s.new('ShaderNodeMapRange', interpolation_type='LINEAR', clamp=True)
        s.put(n.inputs[0], x); s.put(n.inputs[1], e0); s.put(n.inputs[2], e1)
        s.put(n.inputs[3], 0.0); s.put(n.inputs[4], 1.0)
        return S(s, n.outputs[0])
    def band(s, a, b, x, soft=0.002): return s.sm(a - soft, a, x) * (1.0 - s.sm(b, b + soft, x))
    def comb(s, x, y, z):
        n = s.new('ShaderNodeCombineXYZ')
        for i, v in enumerate((x, y, z)): s.put(n.inputs[i], v)
        return V(s, n.outputs[0])
    def sep(s, v):
        n = s.new('ShaderNodeSeparateXYZ'); s.put(n.inputs[0], v)
        return S(s, n.outputs[0]), S(s, n.outputs[1]), S(s, n.outputs[2])
    def vm(s, op, a, b=None, sc=None):
        n = s.new('ShaderNodeVectorMath', operation=op)
        s.put(n.inputs[0], a)
        if b is not None: s.put(n.inputs[1], b)
        if sc is not None: s.put(n.inputs[3], sc)
        o = n.outputs[1] if op in ('LENGTH', 'DOT_PRODUCT', 'DISTANCE') else n.outputs[0]
        return (S if op in ('LENGTH', 'DOT_PRODUCT', 'DISTANCE') else V)(s, o)
    def scale(s, v, f): return s.vm('SCALE', v, sc=f)
    def mix(s, a, b, f):
        n = s.new('ShaderNodeMix', data_type='RGBA')
        s.put(n.inputs[0], f); s.put(n.inputs[6], a); s.put(n.inputs[7], b)
        return V(s, n.outputs[2])
    def noise(s, vec, scale=1.0, detail=2.0, rough=0.5, w=None, dist=0.0):
        n = s.new('ShaderNodeTexNoise', noise_dimensions='4D' if w is not None else '3D')
        s.put(n.inputs['Vector'], vec); s.put(n.inputs['Scale'], scale)
        s.put(n.inputs['Detail'], detail); s.put(n.inputs['Roughness'], rough)
        s.put(n.inputs['Distortion'], dist)
        if w is not None: s.put(n.inputs['W'], w)
        return S(s, n.outputs['Fac']), V(s, n.outputs['Color'])
    def white(s, vec):
        n = s.new('ShaderNodeTexWhiteNoise', noise_dimensions='3D'); s.put(n.inputs['Vector'], vec)
        return S(s, n.outputs['Value']), V(s, n.outputs['Color'])
    def voronoi(s, vec, scale=1.0, feature='F1'):
        n = s.new('ShaderNodeTexVoronoi', feature=feature); s.put(n.inputs['Vector'], vec); s.put(n.inputs['Scale'], scale)
        return S(s, n.outputs['Distance']), V(s, n.outputs['Color'])
    def pos(s):
        n = s.new('ShaderNodeNewGeometry'); return V(s, n.outputs['Position']), V(s, n.outputs['Normal'])
    def uv(s):
        n = s.new('ShaderNodeTexCoord'); return V(s, n.outputs['UV'])
    def attr(s, name):
        n = s.new('ShaderNodeAttribute', attribute_name=name); return V(s, n.outputs['Color']), S(s, n.outputs['Fac'])
    def bump(s, h, strength=1.0, dist=1.0):
        n = s.new('ShaderNodeBump'); s.put(n.inputs['Strength'], strength); s.put(n.inputs['Distance'], dist); s.put(n.inputs['Height'], h)
        return V(s, n.outputs['Normal'])
    def principled(s, **kw):
        n = s.new('ShaderNodeBsdfPrincipled')
        for k, v in kw.items(): s.put(n.inputs[k.replace('_', ' ')], v)
        return n.outputs[0]
    def out(s, shader, volume=None):
        o = s.new('ShaderNodeOutputMaterial')
        if shader is not None: s.nt.links.new(shader, o.inputs['Surface'])
        if volume is not None: s.nt.links.new(volume, o.inputs['Volume'])
        return o

def material(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, G(m.node_tree)

# a scene-wide clock for the loop: 0 at frame 1, 1 at frame 73
def clock(g):
    n = g.new('ShaderNodeValue'); n.outputs[0].default_value = 0.0
    if LOOP:
        dp = 'nodes["%s"].outputs[0].default_value' % n.name
        n.outputs[0].default_value = 0.0; g.nt.keyframe_insert(dp, frame=1)
        n.outputs[0].default_value = 1.0; g.nt.keyframe_insert(dp, frame=NFR + 1)
        for fc in g.nt.animation_data.action.fcurves:
            for k in fc.keyframe_points: k.interpolation = 'LINEAR'
    return S(g, n.outputs[0])

# ---------------------------------------------------------------- mesh helpers
class MB:
    def __init__(s): s.v, s.f, s.mi, s.uv, s.col = [], [], [], [], []
    def add(s, verts, faces, mat=0, uvs=None, col=None):
        o = len(s.v); s.v.extend(verts)
        for f in faces: s.f.append([i + o for i in f]); s.mi.append(mat)
        s.uv.extend(uvs if uvs is not None else [(0.0, 0.0)] * len(verts))
        s.col.extend([col or (1, 1, 1, 1)] * len(verts) if not (col and isinstance(col[0], (tuple, list))) else col)
    def box(s, x0, x1, y0, y1, z0, z1, mat=0):
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        s.add(v, f, mat)
    def build(s, name, mats, smooth=False, uv=False, col=False):
        me = bpy.data.meshes.new(name)
        me.from_pydata(s.v, [], s.f)
        if uv:
            lay = me.uv_layers.new(name='UVMap'); vi = np.zeros(len(me.loops), dtype=np.int32)
            me.loops.foreach_get('vertex_index', vi)
            lay.data.foreach_set('uv', np.asarray(s.uv, dtype=np.float32)[vi].ravel())
        if col:
            a = me.color_attributes.new('col', 'FLOAT_COLOR', 'POINT')
            a.data.foreach_set('color', np.asarray(s.col, dtype=np.float32).ravel())
        me.polygons.foreach_set('material_index', np.asarray(s.mi, dtype=np.int32))
        me.polygons.foreach_set('use_smooth', np.full(len(s.f), smooth))
        me.update()
        for m in mats: me.materials.append(m)
        ob = bpy.data.objects.new(name, me); SC.collection.objects.link(ob)
        return ob

def superring(cx, cy, cz, rx, ry, p, n):
    out = []
    for k in range(n):
        a = 2 * math.pi * k / n; c, s_ = math.cos(a), math.sin(a)
        out.append((cx + rx * math.copysign(abs(c) ** (2 / p), c), cy + ry * math.copysign(abs(s_) ** (2 / p), s_), cz))
    return out

def loft(mb, rings, n=24, mat=0, caps=True):
    """rings: (cx, cy, z, rx, ry, p) from bottom to top; a closed tube with capped ends."""
    verts, faces = [], []
    for r in rings: verts += superring(*r, n)
    for i in range(len(rings) - 1):
        for k in range(n):
            a, b = i * n + k, i * n + (k + 1) % n
            faces.append((a, b, b + n, a + n))
    if caps:
        c0 = len(verts); verts.append(rings[0][:3]); c1 = len(verts); verts.append(rings[-1][:3])
        top = (len(rings) - 1) * n
        for k in range(n):
            faces.append((c0, (k + 1) % n, k)); faces.append((c1, top + k, top + (k + 1) % n))
    mb.add(verts, faces, mat)

def ellipsoid(mb, cx, cy, cz, rx, ry, rz, n=20, m=12, mat=0):
    rings = []
    for i in range(1, m):
        t = -math.pi / 2 + math.pi * i / m
        rings.append((cx, cy, cz + rz * math.sin(t), max(rx * math.cos(t), 1e-4), max(ry * math.cos(t), 1e-4), 2.0))
    loft(mb, rings, n, mat)

def subsurf(ob, lv=2):
    md = ob.modifiers.new('sub', 'SUBSURF'); md.levels = 1; md.render_levels = lv
    return ob


def parse_path(d):
    t = d.replace('M', ' ').replace('L', ' ').replace('Z', ' ').split()
    v = list(map(float, t)); return np.array(v).reshape(-1, 2)

def poly_in(px, py, poly):
    ins = np.zeros(px.shape, bool); n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        c = ((y1 > py) != (y2 > py)) & (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-12) + x1)
        ins ^= c
    return ins

SEAM = parse_path("M67.46 -12L68.96 -12L62.35 21.5L45.15 81.5L33.4 112L31.9 112L37.65 81.5L54.85 21.5Z")
CAV = parse_path("M60.75 14.02L78.19 42.8L73.21 60.2L39.25 88.97L21.81 60.2L26.79 42.8Z")
GEM = parse_path("M58.6 21.5L70.58 46.7L67.82 56.3L41.4 81.5L29.42 56.3L32.18 46.7Z")
FACET = parse_path("M58.6 21.5L70.58 46.7L67.82 56.3L41.4 81.5Z")

# ---------------------------------------------------------------- the print: Grow, portrait, mark redrawn clean
def make_print():
    im = bpy.data.images.load(PRINT_SRC); W, H = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4)[::-1].copy()
    k = W / 1440.0
    s, x0, y0 = 188.5 / 100 * k, 626 * k, 290 * k
    bx0, bx1, by0, by1 = int(608 * k), int(832 * k), int(272 * k), int(496 * k)
    Lc = a[by0:by1, bx0 - 8:bx0 - 2].mean(1); Rc = a[by0:by1, bx1 + 2:bx1 + 8].mean(1)
    t = np.linspace(0, 1, bx1 - bx0)[None, :, None]
    bg = Lc[:, None] * (1 - t) + Rc[:, None] * t
    ss = 4; hh, ww = by1 - by0, bx1 - bx0
    ys = by0 + (np.arange(hh * ss) + 0.5) / ss; xs = bx0 + (np.arange(ww * ss) + 0.5) / ss
    X, Y = np.meshgrid(xs, ys); ux, uy = (X - x0) / s, (Y - y0) / s
    qx, qy = np.abs(ux - 50) - 28, np.abs(uy - 50) - 28
    sd = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - 22
    stone = (sd < 0) & ~poly_in(ux, uy, SEAM) & ~poly_in(ux, uy, CAV)
    gem = poly_in(ux, uy, GEM); fac = poly_in(ux, uy, FACET)
    def down(m): return m.reshape(hh, ss, ww, ss).mean((1, 3))[..., None]
    st, gm, fc = down(stone.astype(np.float32)), down(gem.astype(np.float32)), down(fac.astype(np.float32))
    col = bg[..., :3].copy()
    col = col * (1 - st) + np.array([0.105, 0.100, 0.094]) * st
    gy = ((np.arange(hh) + by0 - y0) / s / 100.0)[:, None, None]
    sky = np.array([0x94, 0xE6, 0xFF]) / 255.0
    gem_c = sky * (1.08 - 0.22 * np.clip((gy - 0.2) / 0.6, 0, 1)) + np.array([0.06, 0.02, 0.0]) * (1 - gy)
    col = col * (1 - gm) + np.clip(gem_c, 0, 1) * gm
    col = col * (1 - 0.28 * fc) + 0.28 * fc
    a[by0:by1, bx0:bx1, :3] = col
    lum = (a[..., :3] * np.array([0.3, 0.59, 0.11])).sum(-1, keepdims=True)
    a[..., :3] = np.clip(lum + (a[..., :3] - lum) * 1.18, 0, 1)
    # a portrait sheet for a 1.16 by 1.74 box, centred on the mark
    cw = int(H * 1.16 / 1.74); c0 = int(720 * k - cw / 2)
    a = a[:, c0:c0 + cw].copy()
    out = bpy.data.images.new('meadow_print', cw, H, alpha=False)
    out.pixels.foreach_set(a[::-1].ravel())
    out.pack()
    bpy.data.images.remove(im)
    return out

# ---------------------------------------------------------------- materials
def wall_mat():
    """Precast concrete poured against boards: panels, tie holes, runs below them, damp rising from the pavement."""
    m, g = material('wall')
    P, N = g.pos(); x, _, z = g.sep(P)
    cxi = g.floor(x / 1.8); czi = g.floor(z / 0.9)
    px = x - cxi * 1.8; pz = z - czi * 0.9
    j = g.min(g.min(px, 1.8 - px), g.min(pz, 0.9 - pz))
    joint = 1.0 - g.sm(0.002, 0.007, j)
    hx = g.floor(px / 0.6) * 0.6 + 0.3
    hz = 0.225 + 0.45 * g.m('GREATER_THAN', pz, 0.45)
    sx = px - hx; sz = pz - hz
    hd = g.vm('LENGTH', g.comb(sx, sz, 0.0))
    hole = 1.0 - g.sm(0.009, 0.014, hd)
    ring = g.sm(0.012, 0.016, hd) * (1.0 - g.sm(0.016, 0.026, hd))
    _, hk = g.white(g.comb(cxi * 7.0 + hx * 13.0, czi + hz * 5.0, 2.0)); hk, hk2, _ = g.sep(hk)
    below = 1.0 - g.sm(-0.002, 0.002, sz)
    wdt = 0.006 + 0.03 * g.max(-sz, 0.0)
    run = below * g.exp(sz / (0.05 + 0.25 * hk)) * g.exp(-(sx / wdt) * (sx / wdt))
    # the boards: horizontal planks, each with its own tone and a little grain
    bi = g.floor(z / 0.15)
    _, bc = g.white(g.comb(bi, cxi, 4.0)); bt, _, _ = g.sep(bc)
    grain, _ = g.noise(g.comb(x * 1.2, z * 34.0, bi), 1.0, 3.0, 0.6)
    edge = 1.0 - g.sm(0.0, 0.004, g.min(g.fract(z / 0.15) * 0.15, 0.15 - g.fract(z / 0.15) * 0.15))
    _, cc = g.white(g.comb(cxi, czi, 3.1)); cr, _, _ = g.sep(cc)
    f1, _ = g.noise(g.comb(x * 1.1, z * 1.6, 0.0), 1.0, 4.0, 0.55)
    f2, _ = g.noise(P, 13.0, 2.0, 0.5)
    pit, _ = g.noise(P, 95.0, 1.0, 0.5)
    st, _ = g.noise(g.comb(x * 5.5, z * 0.3 + 3.0, 0.0), 1.0, 3.0, 0.5)
    stain = g.sm(0.5, 0.75, st)
    dn, _ = g.noise(g.comb(x * 1.5, 5.0, 0.0), 1.0, 3.0, 0.5)
    dh = 0.26 + 0.34 * dn
    damp = 1.0 - g.sm(dh - 0.07, dh, z)
    a = (0.2 + 0.06 * (cr - 0.5)) * (0.72 + 0.52 * f1) * (0.88 + 0.24 * f2) * (1.0 - 0.3 * g.sm(0.65, 0.8, pit))
    a = a * (0.93 + 0.14 * bt) * (0.95 + 0.1 * grain) * (1.0 - 0.25 * edge)
    a = a * (1.0 - 0.4 * stain) * (1.0 - 0.45 * run) * (1.0 - 0.55 * joint) * (1.0 - 0.35 * damp) + ring * 0.03
    a = a * (1.0 - hole) + 0.012 * hole
    ch, _ = g.noise(g.comb(x * 64.0, z * 1.4, 0.0), 1.0, 2.0, 0.5)
    riv = g.sm(0.66, 0.78, ch) * (0.4 + 0.6 * g.sm(0.3, 0.7, g.noise(g.comb(x * 9.0, z * 0.4, 0.0), 1.0, 2.0, 0.5)[0]))
    if GREEN:
        wet = g.clamp(0.1 + 0.4 * damp + 0.2 * run)
        riv = riv * 0.0
    else:
        wet = g.clamp(0.4 + 0.35 * stain + 0.45 * damp + 0.35 * run + 0.3 * joint + 0.5 * riv)
    alb = g.scale((0.97, 0.98, 1.0), a * (1.0 - 0.45 * wet))
    if GREEN:
        mo, _ = g.noise(P, 6.0, 4.0, 0.6)
        mo2, _ = g.noise(P, 1.2, 3.0, 0.6)
        holem = 1.0 - g.sm(0.012 + 0.012 * mo, 0.03 + 0.02 * mo, hd)
        mossm = g.clamp(holem + joint * g.sm(0.45, 0.6, mo) * (0.4 + damp) + damp * g.sm(0.55, 0.68, mo2) + run * g.sm(0.5, 0.7, mo) * 0.7)
        moss = g.mix((0.035, 0.11, 0.012), (0.10, 0.24, 0.03), mo)
        alb = g.mix(alb, moss, mossm)
        alg = g.sm(0.4, 0.8, run + stain * 0.5) * 0.35
        alb = g.mix(alb, g.scale((0.06, 0.09, 0.04), a * 3.0), alg)
    h = -0.004 * joint - 0.012 * hole + 0.0014 * f2 + 0.0005 * pit + 0.0006 * grain - 0.0008 * edge
    nrm = g.bump(h + riv * 0.0004, 1.0, 1.0)
    sh = g.principled(Base_Color=alb, Roughness=0.75 - 0.35 * wet, Normal=nrm, Coat_Weight=wet * 0.9,
                      Coat_Roughness=0.04 + 0.1 * (1.0 - riv), Coat_Normal=nrm, Specular_IOR_Level=0.45)
    g.out(sh)
    return m

def pavement_mat():
    m, g = material('pavement')
    P, N = g.pos(); x, y, _ = g.sep(P)
    yy = -y
    row = g.floor(yy / 0.6); off = 0.45 * (row - 2.0 * g.floor(row * 0.5))
    cu = (x + off) / 0.9; ci = g.floor(cu)
    fu = cu - ci; fv = yy / 0.6 - row
    j = g.min(g.min(fu, 1.0 - fu) * 0.9, g.min(fv, 1.0 - fv) * 0.6)
    joint = 1.0 - g.sm(0.003, 0.008, j)
    _, sc = g.white(g.comb(ci, row, 9.0)); sr, sr2, _ = g.sep(sc)
    agg, _ = g.noise(P, 70.0, 3.0, 0.7)
    blot, _ = g.noise(P, 1.6, 4.0, 0.6)
    dry = (0.085 + 0.03 * sr) * (0.75 + 0.5 * agg) * (0.8 + 0.4 * blot)
    # water stands where the slabs have settled, deeper near the wall
    pn, _ = g.noise(g.comb(x * 0.7, yy * 1.1, 0.0), 1.0, 4.0, 0.55)
    tilt = (fu - 0.5) * (sr - 0.5) + (fv - 0.5) * (sr2 - 0.5)
    lvl = pn + 0.25 * tilt + 0.08 * joint + 0.12 * (1.0 - g.sm(0.0, 1.2, yy))
    thr = 0.55 if not GREEN else 0.56
    pud = g.sm(thr, thr + 0.05, lvl)
    damp = g.sm(0.3, 0.5, lvl) if not GREEN else g.sm(0.45, 0.6, lvl)
    a = dry * (1.0 - 0.45 * damp) * (1.0 - 0.6 * pud)
    a = a * (1.0 - 0.6 * joint)
    alb = g.comb(a, a * 1.01, a * 1.04)
    if GREEN:
        mo, _ = g.noise(P, 3.0, 4.0, 0.6)
        mm = g.clamp(joint * g.sm(0.4, 0.55, mo) * 1.6) * (1.0 - pud)
        alb = g.mix(alb, (0.05, 0.14, 0.02), mm)
    rough = (0.7 - 0.4 * damp) * (1.0 - pud) + 0.012 * pud
    h = (agg - 0.5) * 0.0015 * (1.0 - pud) - joint * 0.003
    if not GREEN:
        # rain landing: rings in two scales, each cell its own moment
        for sc_, amp in ((7.0, 1.0), (12.0, 0.6)):
            dv, vc = g.voronoi(g.comb(x, yy, 0.0), sc_)
            ph, _, _ = g.sep(vc)
            r0 = ph * 0.11
            rr = (dv / sc_ - r0) * 260.0
            ring = g.sin(rr * 2.6) * g.exp(-(rr * rr) * 0.6) * (1.0 - ph) * (1.0 - ph)
            h = h + ring * 0.00025 * amp * g.max(pud, damp * 0.5)
    nrm = g.bump(h, 1.0, 1.0)
    g.out(g.principled(Base_Color=alb, Roughness=rough, Normal=nrm, Specular_IOR_Level=0.5))
    return m

def plain(name, col, rough, metal=0.0, coat=0.0, spec=0.5, sheen=0.0):
    m, g = material(name)
    P, N = g.pos(); n1, _ = g.noise(P, 3.0, 4.0, 0.6)
    g.out(g.principled(Base_Color=g.scale(col, 0.8 + 0.4 * n1), Roughness=rough, Metallic=metal, Coat_Weight=coat, Specular_IOR_Level=spec, Sheen_Weight=sheen))
    return m

def print_mat(img, E):
    m, g = material('print')
    t = g.new('ShaderNodeTexImage', image=img, interpolation='Cubic', extension='EXTEND')
    uv = g.uv(); g.put(t.inputs[0], uv); u, v, _ = g.sep(uv)
    edge = g.min(g.min(u, 1.0 - u) * 0.667, g.min(v, 1.0 - v))
    fall = (0.88 + 0.12 * g.sm(0.0, 0.06, edge))
    lp = g.new('ShaderNodeLightPath')
    k = g.max(S(g, lp.outputs['Is Shadow Ray']), S(g, lp.outputs['Is Diffuse Ray']))
    e = g.new('ShaderNodeEmission'); g.put(e.inputs[0], V(g, t.outputs[0])); g.put(e.inputs[1], fall * (E + (E * LIFT - E) * k))
    g.out(e.outputs[0])
    return m

def glass_sheet():
    m, g = material('box_glass')
    P, N = g.pos(); sm_, _ = g.noise(P, 6.0, 4.0, 0.6)
    tr = g.new('ShaderNodeBsdfTransparent')
    gl = g.new('ShaderNodeBsdfGlossy'); g.put(gl.inputs['Roughness'], 0.004 + 0.06 * g.sm(0.55, 0.75, sm_))
    fr = g.new('ShaderNodeFresnel'); fr.inputs['IOR'].default_value = 1.52
    mx = g.new('ShaderNodeMixShader')
    g.nt.links.new(fr.outputs[0], mx.inputs[0]); g.nt.links.new(tr.outputs[0], mx.inputs[1]); g.nt.links.new(gl.outputs[0], mx.inputs[2])
    g.out(mx.outputs[0])
    return m

def water_mat(name='water', rough=0.0):
    m, g = material(name)
    g.out(g.principled(Base_Color=(1, 1, 1), Roughness=rough, Transmission_Weight=1.0, IOR=1.33))
    return m

def rain_mat():
    # rain seen against light: it scatters what is behind it forward, so it reads bright, never as dark scratches
    m, g = material('rain')
    tr = g.new('ShaderNodeBsdfTransparent')
    tl = g.new('ShaderNodeBsdfTranslucent'); tl.inputs[0].default_value = (0.9, 0.94, 1.0, 1)
    gl = g.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.15
    m1 = g.new('ShaderNodeMixShader'); m1.inputs[0].default_value = 0.35
    g.nt.links.new(tl.outputs[0], m1.inputs[1]); g.nt.links.new(gl.outputs[0], m1.inputs[2])
    m2 = g.new('ShaderNodeMixShader'); m2.inputs[0].default_value = 0.4
    g.nt.links.new(tr.outputs[0], m2.inputs[1]); g.nt.links.new(m1.outputs[0], m2.inputs[2])
    g.out(m2.outputs[0])
    return m

def leaf_mat(name, glossy=0.45, trans=0.35):
    m, g = material(name)
    c, _ = g.attr('col'); P, N = g.pos(); n1, _ = g.noise(P, 30.0, 2.0, 0.5)
    base = g.scale(c, 0.85 + 0.3 * n1)
    pr = g.principled(Base_Color=base, Roughness=glossy, Specular_IOR_Level=0.35, Sheen_Weight=0.15)
    tl = g.new('ShaderNodeBsdfTranslucent'); g.put(tl.inputs[0], g.scale(base, 1.3))
    mx = g.new('ShaderNodeMixShader'); mx.inputs[0].default_value = trans
    g.nt.links.new(pr, mx.inputs[1]); g.nt.links.new(tl.outputs[0], mx.inputs[2])
    g.out(mx.outputs[0])
    return m

def haze_mat(density, aniso):
    m, g = material('haze')
    vol = g.new('ShaderNodeVolumePrincipled'); vol.inputs['Anisotropy'].default_value = aniso
    vol.inputs['Color'].default_value = (0.92, 0.95, 1.0, 1)
    lp = g.new('ShaderNodeLightPath'); cam = S(g, lp.outputs['Is Camera Ray'])
    g.put(vol.inputs['Density'], cam * density)
    g.out(None, vol.outputs[0])
    return m

# ---------------------------------------------------------------- growth
GCOL = [(0.07, 0.22, 0.025), (0.12, 0.32, 0.04), (0.18, 0.40, 0.06), (0.05, 0.17, 0.02), (0.22, 0.42, 0.08)]

def grass(mb, bases, dirs, heights, widths, lean, cols, segs=5):
    for i in range(len(bases)):
        b = bases[i]; d = dirs[i]; h = heights[i]; w = widths[i]; l = lean[i]
        side = np.cross(d, l); ns = np.linalg.norm(side); side = side / ns if ns > 1e-6 else np.array([1.0, 0, 0])
        verts = []
        for k in range(segs + 1):
            t = k / segs
            p = b + d * h * t + l * h * t * t * 0.55 + np.array([0, 0, -1.0]) * h * 0.25 * t ** 3 * np.linalg.norm(l)
            ww = w * (1 - t) ** 0.8 + 0.0004
            verts.append(tuple(p - side * ww)); verts.append(tuple(p + side * ww))
        mb.add(verts, [(2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2) for k in range(segs)], 0, col=cols[i])

def tuft(mb, centre, normal, count, hmin, hmax, spread=0.05, cols=None):
    normal = np.array(normal, float); normal /= np.linalg.norm(normal)
    bases, dirs, hs, ws, ln, cs = [], [], [], [], [], []
    for _ in range(count):
        off = nrng.normal(0, spread, 3); off -= normal * off.dot(normal)
        bases.append(np.array(centre) + off)
        d = normal + nrng.normal(0, 0.28, 3) + np.array([0, 0, 0.6 if normal[2] < 0.5 else 0])
        d /= np.linalg.norm(d); dirs.append(d)
        hs.append(rng.uniform(hmin, hmax)); ws.append(rng.uniform(0.002, 0.005))
        l = nrng.normal(0, 0.6, 3); l[2] = 0
        if normal[1] < -0.5: l[1] = -abs(l[1]) * 0.5
        ln.append(l)
        c = rng.choice(cols or GCOL); cs.append((c[0] * rng.uniform(0.8, 1.2), c[1] * rng.uniform(0.85, 1.15), c[2], 1))
    grass(mb, bases, dirs, hs, ws, ln, cs)

def fern(mb, base, size, rot, col=(0.05, 0.2, 0.03), up=(0, 0, 1)):
    nf = rng.randint(7, 11)
    up = np.array(up, float); up /= np.linalg.norm(up)
    tmp = np.array([1.0, 0, 0]) if abs(up[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(up, tmp); e1 /= np.linalg.norm(e1); e2 = np.cross(up, e1)
    for fi in range(nf):
        az = rot + 2 * math.pi * fi / nf + rng.uniform(-0.25, 0.25)
        el = rng.uniform(0.55, 1.15); L = size * rng.uniform(0.65, 1.0)
        hd = e1 * math.cos(az) + e2 * math.sin(az)
        pts = [np.array(base) + hd * L * (k / 25) * math.cos(el * (1 - 0.7 * k / 25)) + up * L * ((k / 25) * math.sin(el) - 0.55 * (k / 25) ** 2 * (1.1 - el * 0.5)) for k in range(26)]
        c = (col[0] * rng.uniform(0.8, 1.3), col[1] * rng.uniform(0.85, 1.2), col[2], 1)
        verts, faces = [], []
        for k in range(2, 25):
            t = k / 25; p = pts[k]; tan = pts[k + 1] - pts[k - 1]; tan /= np.linalg.norm(tan)
            sd = np.cross(tan, up); sd /= max(np.linalg.norm(sd), 1e-6); nrm = np.cross(sd, tan)
            pl = L * 0.2 * math.sin(math.pi * min(1, t * 1.05)) ** 0.8 * (1 - 0.35 * t) + 0.006
            for sg in (-1, 1):
                dirp = sd * sg * 0.85 + tan * 0.45 - nrm * 0.15; dirp /= np.linalg.norm(dirp)
                wv = tan * pl * 0.17; o = len(verts)
                verts += [tuple(p), tuple(p + dirp * pl * 0.5 + wv), tuple(p + dirp * pl), tuple(p + dirp * pl * 0.5 - wv)]
                faces.append((o, o + 1, o + 2, o + 3))
        for k in range(25):
            p, q = pts[k], pts[k + 1]; tan = q - p; sd = np.cross(tan, up); sd /= max(np.linalg.norm(sd), 1e-6); w = 0.002
            o = len(verts); verts += [tuple(p - sd * w), tuple(p + sd * w), tuple(q + sd * w), tuple(q - sd * w)]
            faces.append((o, o + 1, o + 2, o + 3))
        mb.add(verts, faces, 0, col=c)

IVY_LEAF = [(0.0, 0.0), (0.35, 0.15), (0.5, 0.45), (0.28, 0.55), (0.22, 0.85), (0.0, 1.0), (-0.22, 0.85), (-0.28, 0.55), (-0.5, 0.45), (-0.35, 0.15)]

def leaf(mb, p, s, up, out, col):
    """an ivy leaf at p, pointing along up, its face toward out"""
    up = np.array(up, float); up /= np.linalg.norm(up); out = np.array(out, float)
    sd = np.cross(up, out); sd /= max(np.linalg.norm(sd), 1e-6); nrm = np.cross(sd, up)
    verts = [tuple(p + (sd * lx + up * ly) * s + nrm * 0.18 * s * ly * ly) for (lx, ly) in IVY_LEAF]
    mb.add(verts, [tuple(range(len(IVY_LEAF)))], 0, col=col)

def climb(mb, stems, start, height, avoid, wall_y=-0.004, drift=0.0, depth=0):
    """ivy climbing the wall from the pavement, held a few millimetres off it; it never crosses the print"""
    p = np.array(start, float); pts = [p.copy()]
    ang = rng.uniform(-0.3, 0.3) + drift if depth == 0 else drift
    col = rng.choice([(0.025, 0.10, 0.018), (0.04, 0.14, 0.025), (0.06, 0.19, 0.03), (0.08, 0.22, 0.04)])
    n = int(height / 0.03)
    for k in range(n):
        ang += rng.uniform(-0.18, 0.18); ang *= 0.97
        q = p + np.array([math.sin(ang) * 0.03, 0.0, math.cos(ang) * 0.03])
        x0, x1, z0, z1 = avoid
        if x0 < q[0] < x1 and z0 < q[2] < z1:
            # run round the frame: turn toward the nearer side
            ang += (-0.6 if q[0] < (x0 + x1) / 2 else 0.6)
            q = p + np.array([math.sin(ang) * 0.03, 0.0, max(0.0, math.cos(ang)) * 0.03])
            if x0 < q[0] < x1 and z0 < q[2] < z1: break
        p = q; p[1] = wall_y; pts.append(p.copy())
        for _l in range(2):
            if rng.random() > 0.8: continue
            s = rng.uniform(0.035, 0.07) * (1.15 - 0.4 * k / max(n, 1))
            sideways = (-1 if _l == 0 else 1) * rng.uniform(0.4, 1.4)
            upv = np.array([math.sin(ang + sideways), 0.0, math.cos(ang + sideways)])
            outv = np.array([rng.uniform(-0.3, 0.3), -1.0, rng.uniform(-0.2, 0.6)])
            lp = p + np.array([math.sin(ang + sideways) * 0.012, -0.004 - rng.uniform(0, 0.03), math.cos(ang + sideways) * 0.012])
            if not (avoid[0] - 0.01 < lp[0] + 0.0 < avoid[1] + 0.01 and avoid[2] - 0.01 < lp[2] < avoid[3] + 0.01) \
                    and not (avoid[0] - 0.01 < lp[0] + upv[0] * s < avoid[1] + 0.01 and avoid[2] - 0.01 < lp[2] + upv[2] * s < avoid[3] + 0.01):
                cv = (col[0] * rng.uniform(0.75, 1.3), col[1] * rng.uniform(0.8, 1.25), col[2], 1)
                leaf(mb, lp, s, upv, outv, cv)
        # side shoots, which is what makes ivy a mass rather than a string
        if depth < 2 and rng.random() < 0.07 and k > 3:
            climb(mb, stems, tuple(p), rng.uniform(0.15, 0.6) * (n - k) * 0.03 + 0.1, avoid, wall_y, ang + rng.choice([-1, 1]) * rng.uniform(0.6, 1.2), depth + 1)
    stems.append(pts)

def flower(mb, top, r, col, n=10):
    verts = [tuple(top)]; faces = []
    for k in range(n):
        a = 2 * math.pi * k / n; rr = r * (1.0 if k % 2 == 0 else 0.5)
        verts.append(tuple(top + np.array([math.cos(a) * rr, math.sin(a) * rr * 0.6, 0.002 + math.sin(a) * rr * 0.5])))
    for k in range(n): faces.append((0, 1 + k, 1 + (k + 1) % n))
    mb.add(verts, faces, 0, col=col)

# ---------------------------------------------------------------- the street
PW, PH, PB, PZo, FW = 1.16, 1.74, 0.17, 0.07, 0.036
PIPE_X = PW / 2 + 0.66

def build(img):
    m_wall = wall_mat(); m_pave = pavement_mat()
    mb = MB(); mb.add([(-9, 0, 0), (9, 0, 0), (9, 0, 3.4), (-9, 0, 3.4)], [(0, 3, 2, 1)], 0)
    wall = mb.build('wall', [m_wall])
    sd = wall.modifiers.new('sub', 'SUBSURF'); sd.subdivision_type = 'SIMPLE'; sd.levels = 0; sd.render_levels = 0
    mb = MB(); mb.add([(-9, 0, 0), (9, 0, 0), (9, -14, 0), (-9, -14, 0)], [(0, 1, 2, 3)], 0)
    mb.build('pavement', [m_pave])
    # the lightbox: a slim dark case, the print, wet glass
    m_frame = plain('frame', (0.025, 0.027, 0.03), 0.3, metal=0.9)
    x0, x1, z0, z1 = -PW / 2, PW / 2, PB, PB + PH
    fb = MB()
    fb.box(x0 - FW, x1 + FW, -PZo, 0.0, z1, z1 + FW); fb.box(x0 - FW, x1 + FW, -PZo, 0.0, z0 - FW, z0)
    fb.box(x0 - FW, x0, -PZo, 0.0, z0, z1); fb.box(x1, x1 + FW, -PZo, 0.0, z0, z1)
    fr = fb.build('frame', [m_frame]); bv = fr.modifiers.new('bev', 'BEVEL'); bv.width = 0.003; bv.segments = 2
    pm = MB(); pm.add([(x0, -0.05, z0), (x1, -0.05, z0), (x1, -0.05, z1), (x0, -0.05, z1)], [(0, 1, 2, 3)], 0, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    pm.build('print', [print_mat(img, E_PRINT)], uv=True)
    gm = MB(); gm.add([(x0, -PZo + 0.004, z0), (x1, -PZo + 0.004, z0), (x1, -PZo + 0.004, z1), (x0, -PZo + 0.004, z1)], [(0, 1, 2, 3)], 0)
    gm.build('glass', [glass_sheet()])
    # drops on the glass, and the few that have run
    m_w = water_mat()
    dm = MB()
    ndrops = 420 if not GREEN else 120
    for _ in range(ndrops):
        x = rng.uniform(x0 + 0.01, x1 - 0.01); z = rng.uniform(z0 + 0.01, z1 - 0.01)
        r = rng.uniform(0.0015, 0.0045) * (1.0 if rng.random() < 0.9 else 1.8)
        if False:
            L = rng.uniform(0.05, 0.25)
            loft(dm, [(x, -PZo, z - L, 0.0008, 0.0006, 2), (x, -PZo, z - L * 0.5, 0.0012, 0.0008, 2), (x, -PZo, z, r, r * 0.45, 2)], 8, caps=True)
        else:
            ellipsoid(dm, x, -PZo + 0.004 - r * 0.28, z, r, r * 0.28, r * 1.05, 10, 6)
    dm.build('glass_drops', [m_w], smooth=True)
    # the downpipe and its brackets, and a cable clipped to the wall
    m_pipe = plain('pipe', (0.03, 0.032, 0.036), 0.35, metal=0.6, coat=0.7 if not GREEN else 0.2)
    pp = MB(); loft(pp, [(PIPE_X, -0.095, -0.01, 0.062, 0.062, 2), (PIPE_X, -0.095, 3.4, 0.062, 0.062, 2)], 24, caps=False)
    for zb in (0.45, 1.55, 2.65):
        loft(pp, [(PIPE_X, -0.095, zb - 0.02, 0.068, 0.068, 2), (PIPE_X, -0.095, zb + 0.02, 0.068, 0.068, 2)], 24)
        pp.box(PIPE_X - 0.012, PIPE_X + 0.012, -0.04, 0.0, zb - 0.02, zb + 0.02)
    loft(pp, [(PIPE_X, -0.095, -0.01, 0.075, 0.075, 2), (PIPE_X, -0.095, 0.04, 0.075, 0.075, 2)], 24)
    pp.build('pipe', [m_pipe], smooth=True)
    cb = bpy.data.curves.new('cable', 'CURVE'); cb.dimensions = '3D'; cb.bevel_depth = 0.0055; cb.bevel_resolution = 2
    sp = cb.splines.new('POLY'); xs = np.arange(-6.0, PIPE_X - 0.06, 0.02); sp.points.add(len(xs) - 1)
    for i, x in enumerate(xs):
        sp.points[i].co = (x, -0.009, 2.24 - 0.012 * math.sin(math.pi * ((x + 6.0) / 0.46 % 1.0)), 1)
    co = bpy.data.objects.new('cable', cb); SC.collection.objects.link(co); cb.materials.append(plain('cable', (0.01, 0.01, 0.011), 0.4, coat=0.5))
    cl = MB()
    for x in np.arange(-6.0, PIPE_X - 0.1, 0.46): cl.box(x - 0.008, x + 0.008, -0.018, 0.0, 2.226, 2.254)
    cl.build('clips', [plain('clip', (0.3, 0.3, 0.3), 0.4)])
    if not GREEN:
        # rain: thin streaks, the length a drop falls in a fiftieth of a second
        rb = MB()
        for _ in range(3200):
            x = rng.uniform(-3.2, 3.2); y = -rng.uniform(0.08, 3.6) ** 1.0; z = rng.uniform(0.0, 3.3)
            L = rng.uniform(0.12, 0.26); r = rng.uniform(0.0006, 0.0012); dx = 0.012
            loft(rb, [(x, y, z, r * 0.3, r * 0.3, 2), (x + dx * 0.5, y, z + L * 0.5, r, r, 2), (x + dx, y, z + L, r * 0.3, r * 0.3, 2)], 6)
        rb.build('rain', [rain_mat()], smooth=True)
        # splashes on the pavement and on the box's top edge
        sb = MB()
        for _ in range(140):
            x = rng.uniform(-2.6, 2.6); y = -rng.uniform(0.05, 2.6)
            for kk in range(rng.randint(3, 6)):
                a = rng.uniform(0, 6.28); d = rng.uniform(0.004, 0.02)
                ellipsoid(sb, x + math.cos(a) * d, y + math.sin(a) * d, rng.uniform(0.004, 0.03), 0.0015, 0.0015, 0.003, 6, 4)
        sb.build('splashes', [m_w], smooth=True)
    else:
        build_growth((x0 - FW, x1 + FW, z0 - FW, z1 + FW))

def build_growth(frame):
    m_grass = leaf_mat('grass', 0.5, 0.4); m_fern = leaf_mat('fern', 0.45, 0.4); m_ivy = leaf_mat('ivy', 0.3, 0.25)
    m_flower = leaf_mat('flower', 0.5, 0.35); m_moss = leaf_mat('moss', 0.8, 0.2)
    gm, fm, im, flm, mm = MB(), MB(), MB(), MB(), MB()
    stems = []
    margin = 0.02
    avoid = (frame[0] - margin, frame[1] + margin, frame[2] - margin, frame[3] + margin)
    # ivy: from the foot of the wall, climbing, parting round the box
    for _ in range(46):
        x = rng.choice([rng.gauss(-1.9, 0.6), rng.gauss(-1.9, 0.6), rng.gauss(2.3, 0.5), rng.uniform(-3.2, 3.4), rng.uniform(-0.9, 0.9)])
        h = rng.uniform(0.4, 3.2) if abs(x) > 0.8 else rng.uniform(0.05, 0.12)
        climb(im, stems, (x, -0.004, 0.0), h, avoid, drift=(-0.25 if x < 0 else 0.25) * rng.random())
    # one long run that comes across the top of the box and hangs a little off its frame
    for k in range(9):
        x = rng.uniform(-1.4, 1.4); z = rng.uniform(2.05, 2.5)
        climb(im, stems, (x, -0.004, z), rng.uniform(0.2, 0.9), avoid, drift=rng.uniform(-1.4, 1.4))
    # tufts in the tie holes and along the wall's foot
    for xi in range(-6, 6):
        for zi in range(0, 4):
            for hx in (0.3, 0.9, 1.5):
                for hz in (0.225, 0.675):
                    x = xi * 1.8 + hx; z = zi * 0.9 + hz
                    if not (-3.3 < x < 3.5 and z < 2.6): continue
                    if frame[0] - 0.08 < x < frame[1] + 0.08 and frame[2] - 0.08 < z < frame[3] + 0.08: continue
                    if abs(x - PIPE_X) < 0.12: continue
                    rv = rng.random()
                    # a cushion of moss in every hole
                    for _ in range(rng.randint(8, 16)):
                        a = rng.uniform(0, 6.28); d = rng.uniform(0, 0.016)
                        ellipsoid(mm, x + math.cos(a) * d, -0.004, z + math.sin(a) * d, rng.uniform(0.004, 0.008), 0.006, rng.uniform(0.004, 0.008), 8, 5)
                    if rv < 0.35:
                        tuft(gm, (x, -0.01, z), (0, -1, 0.5), rng.randint(4, 9), 0.05, 0.18, 0.006)
                    elif rv < 0.5:
                        fern(fm, (x, -0.01, z), rng.uniform(0.1, 0.18), rng.uniform(0, 6.28), up=(0, -1, 0.5))
    for _ in range(90):
        x = rng.uniform(-3.4, 3.6)
        tuft(gm, (x, -rng.uniform(0.01, 0.06), 0.0), (0, -0.25, 1), rng.randint(6, 14), 0.08, 0.42, 0.04)
    for _ in range(9):
        fern(fm, (rng.uniform(-3, 3.2), -0.08, 0.0), rng.uniform(0.25, 0.45), rng.uniform(0, 6.28))
    # the pavement's joints, and wildflowers in its cracks
    for _ in range(160):
        row = rng.randint(0, 5); yy = row * 0.6 + rng.uniform(-0.004, 0.004)
        x = rng.uniform(-3.2, 3.2)
        if rng.random() < 0.5:
            off = 0.45 * (row % 2); x = (round((x + off) / 0.9) * 0.9 - off) + rng.uniform(-0.003, 0.003); yy = row * 0.6 + rng.uniform(0.05, 0.55)
        tuft(gm, (x, -yy, 0.0), (0, 0, 1), rng.randint(3, 9), 0.03, 0.16, 0.012)
    for _ in range(70):
        x = rng.uniform(-3.0, 3.2); yy = rng.choice([rng.uniform(0.02, 0.15), rng.randint(1, 4) * 0.6 + rng.uniform(-0.01, 0.01)])
        h = rng.uniform(0.08, 0.34) if yy < 0.2 else rng.uniform(0.05, 0.16)
        tuft(gm, (x, -yy, 0.0), (0, 0, 1), 1, h * 0.95, h, 0.0)
        top = np.array([x + rng.uniform(-0.02, 0.02), -yy + rng.uniform(-0.02, 0.02), h * 0.97])
        c = rng.choice([(0.86, 0.87, 0.82, 1), (0.82, 0.84, 0.8, 1), (0.48, 0.66, 0.9, 1), (0.36, 0.5, 0.86, 1)])
        flower(flm, top, rng.uniform(0.008, 0.016), c)
    gm.build('grass', [m_grass], smooth=True, col=True)
    fm.build('ferns', [m_fern], smooth=True, col=True)
    im.build('ivy', [m_ivy], smooth=True, col=True)
    flm.build('flowers', [m_flower], col=True)
    mm.col = [(0.07 + 0.05 * rng.random(), 0.2 + 0.08 * rng.random(), 0.03, 1)] * len(mm.v)
    mm.build('moss', [m_moss], smooth=True, col=True)
    cu = bpy.data.curves.new('ivy_stems', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.002; cu.bevel_resolution = 1
    for pts in stems:
        if len(pts) < 2: continue
        sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts): sp.points[i].co = (p[0], p[1], p[2], 1)
    co = bpy.data.objects.new('ivy_stems', cu); SC.collection.objects.link(co); cu.materials.append(m_ivy)

LIFT = 2.0
E_PRINT = 1.5 if not GREEN else 2.4

def main():
    t0 = time.time()
    img = make_print()
    build(img)
    from mathutils import Vector
    wm = bpy.data.worlds.new('w'); SC.world = wm; wm.use_nodes = True; nt = wm.node_tree; nt.nodes.clear(); g = G(nt)
    bg = g.new('ShaderNodeBackground'); o = g.new('ShaderNodeOutputWorld'); nt.links.new(bg.outputs[0], o.inputs[0])
    if GREEN:
        gp = g.new('ShaderNodeNewGeometry'); _, _, iz = g.sep(g.scale(V(g, gp.outputs['Incoming']), -1.0))
        sky = g.mix((0.66, 0.78, 0.95), (0.2, 0.4, 0.86), g.sm(0.0, 0.9, iz))
        sky = g.mix((0.08, 0.09, 0.08), sky, g.sm(-0.15, 0.02, iz))
        g.put(bg.inputs[0], sky); bg.inputs[1].default_value = 1.3
        sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.6; sun.angle = math.radians(4.0); sun.color = (1.0, 0.97, 0.92)
        so = bpy.data.objects.new('sun', sun); SC.collection.objects.link(so)
        so.rotation_euler = Vector((0.55, 0.75, -0.62)).normalized().to_track_quat('-Z', 'Y').to_euler()
    else:
        bg.inputs[0].default_value = (0.0025, 0.0035, 0.007, 1); bg.inputs[1].default_value = 1.0
        # the cool street lamp, high and off frame to the left
        sp = bpy.data.lights.new('lamp', 'SPOT'); sp.energy = 520.0; sp.color = (0.5, 0.63, 1.0); sp.spot_size = math.radians(70); sp.spot_blend = 0.6; sp.shadow_soft_size = 0.12
        so = bpy.data.objects.new('lamp', sp); SC.collection.objects.link(so); so.location = (-2.6, -1.4, 4.0)
        so.rotation_euler = Vector((0.36, 0.48, -0.8)).normalized().to_track_quat('-Z', 'Y').to_euler()
        # a far cobalt glow to the right
        cp = bpy.data.lights.new('cobalt', 'POINT'); cp.energy = 140.0; cp.color = (0.14, 0.28, 1.0); cp.shadow_soft_size = 1.2
        co = bpy.data.objects.new('cobalt', cp); SC.collection.objects.link(co); co.location = (5.4, -3.2, 1.6)
    hb = MB(); hb.box(-6, 6, -5, -0.002, 0.0, 3.4, 0)
    hz = hb.build('haze', [haze_mat(0.012 if GREEN else 0.03, 0.35)])
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); SC.collection.objects.link(cam); SC.camera = cam
    TANY = math.tan(math.radians(19)); yaw = math.radians(4)
    V_ = max(PH / 0.6, PW / (0.8 * 1.6)); D = V_ / (2 * TANY)
    cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24.0; cd.lens = 12.0 / TANY
    cam.location = (math.sin(yaw) * D, -math.cos(yaw) * D, 1.3); cam.rotation_euler = (math.radians(90), 0, yaw)
    cd.shift_y = ((0.3 * V_ - 1.3) / D) / (2 * TANY * 1.6)
    cd.dof.use_dof = True; cd.dof.focus_distance = D; cd.dof.aperture_fstop = 4.0
    r = SC.render; r.engine = 'CYCLES'; r.resolution_x, r.resolution_y = 1920, 1200; r.resolution_percentage = RES
    r.threads_mode = 'FIXED'; r.threads = 4
    c = SC.cycles; c.device = 'CPU'; c.samples = SAMPLES; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.015; c.adaptive_min_samples = 24
    c.time_limit = TL
    c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'; c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; c.denoising_prefilter = 'ACCURATE'
    c.max_bounces = 8; c.diffuse_bounces = 3; c.glossy_bounces = 3; c.transmission_bounces = 8; c.volume_bounces = 0; c.transparent_max_bounces = 10
    c.sample_clamp_indirect = 8.0; c.blur_glossy = 0.8; c.caustics_refractive = False; c.use_light_tree = True
    vs = SC.view_settings; vs.view_transform = 'AgX'; vs.look = 'AgX - Base Contrast'; vs.exposure = 0.0 if not GREEN else 0.0
    r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGB'; r.image_settings.color_depth = '8'
    SC.use_nodes = True; ct = SC.node_tree; ct.nodes.clear()
    rl = ct.nodes.new('CompositorNodeRLayers'); gl = ct.nodes.new('CompositorNodeGlare'); cmp = ct.nodes.new('CompositorNodeComposite')
    gl.glare_type = 'BLOOM'
    for k, v in (('Threshold', 0.9), ('Strength', 0.22), ('Size', 0.6)):
        try: gl.inputs[k].default_value = v
        except Exception: pass
    ct.links.new(rl.outputs['Image'], gl.inputs['Image']); ct.links.new(gl.outputs[0], cmp.inputs['Image'])
    print('BUILD %.1fs' % (time.time() - t0)); sys.stdout.flush()
    t1 = time.time(); r.filepath = OUT; bpy.ops.render.render(write_still=True)
    print('RENDER %.1fs' % (time.time() - t1))

main()
