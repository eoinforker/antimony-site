# Platform, path traced: a deep tiled metro vault at night, one lightbox across the tracks
# showing the Grow meadow, one person standing in its light.
#
# Run headless with Blender 4.2 LTS or newer:
#   blender -b -P platform_scene.py -- --variant night --out night.png
#   blender -b -P platform_scene.py -- --variant overgrown --out overgrown.png
#   blender -b -P platform_scene.py -- --variant loop --out frames/f_#### --frames 1-72 --res 67
# Options: --res <percent of 1920x1200>, --samples <max>, --tl <seconds per frame>, --print <png>
#
# Everything is procedural: geometry is generated here, materials are node graphs.
# The only image is the print in the lightbox, made from Antimony's own Grow page
# (directions/grow/shots/rest-desktop.png) with the Break mark redrawn from its exact geometry.
#
# World, in metres: Blender X runs along the platform, the far wall across the tracks is the
# plane Y = 0, the camera stands at Y = -10.5, Z is up. The platform floor is Z = 0, its edge at
# Y = -3, the track bed at Z = -1.05; the vault springs at Z = 3.7 and is a half ellipse with
# semi axes 6 (across) and 2.4 (up), as in the real-time version.

import bpy, bmesh, math, random, sys, os, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))

def arg(name, default):
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return a[a.index(name) + 1] if name in a else default

VARIANT = arg('--variant', 'night')          # night, overgrown, loop
OUT = arg('--out', os.path.join(HERE, VARIANT + '.png'))
RES = int(arg('--res', '100'))
SAMPLES = int(arg('--samples', '1024'))
TL = float(arg('--tl', '1320'))
FRAMES = arg('--frames', '1-72')
PASS = arg('--pass', 'on')            # for the loop: on, off (the failing lamp), anim (drips and rings), compose
PRINT_SRC = arg('--print', os.path.join(ROOT, 'grow', 'shots', 'rest-desktop.png'))
GREEN = VARIANT == 'overgrown'
LOOP = VARIANT == 'loop'
NFR = 72
rng = random.Random(7)
nrng = np.random.default_rng(7)

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

# ---------------------------------------------------------------- the print (Grow meadow, mark redrawn clean)
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

def make_print():
    im = bpy.data.images.load(PRINT_SRC); W, H = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4)[::-1].copy()
    k = W / 1440.0
    s, x0, y0 = 188.5 / 100 * k, 626 * k, 290 * k          # where the mark sits in the Grow shot
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
    stone_c = np.array([0.105, 0.100, 0.094])
    col = col * (1 - st) + stone_c * st
    gy = ((np.arange(hh) + by0 - y0) / s / 100.0)[:, None, None]
    sky = np.array([0x94, 0xE6, 0xFF]) / 255.0
    gem_c = sky * (1.08 - 0.22 * np.clip((gy - 0.2) / 0.6, 0, 1)) + np.array([0.06, 0.02, 0.0]) * (1 - gy)
    col = col * (1 - gm) + np.clip(gem_c, 0, 1) * gm
    col = col * (1 - 0.28 * fc) + 0.28 * fc
    a[by0:by1, bx0:bx1, :3] = col
    # a little extra saturation, which the AgX view gives back as it rolls off the bright print
    lum = (a[..., :3] * np.array([0.3, 0.59, 0.11])).sum(-1, keepdims=True)
    a[..., :3] = np.clip(lum + (a[..., :3] - lum) * 1.18, 0, 1)
    # crop to the lightbox's 16:9 and hand it back
    ch = int(W * 2.8 / 4.98); c0 = int((H - ch) * 0.55)
    a = a[c0:c0 + ch]
    out = bpy.data.images.new('meadow_print', W, ch, alpha=False)
    out.pixels.foreach_set(a[::-1].ravel())
    out.pack()
    bpy.data.images.remove(im)
    return out

# ---------------------------------------------------------------- materials
def tile_mat():
    m, g = material('tiles')
    uvv = g.uv(); u, v, _ = g.sep(uvv); P, N = g.pos()
    Wt, Ht, GW = 0.244, 0.0835, 0.0052
    r = g.floor(v / Ht); off = 0.5 * (r - 2.0 * g.floor(r * 0.5))
    cu = u / Wt + off; c = g.floor(cu); fu = cu - c; fv = v / Ht - r
    d = g.min(g.min(fu, 1.0 - fu) * Wt, g.min(fv, 1.0 - fv) * Ht)
    face = g.sm(GW * 0.5, GW * 0.5 + 0.0012, d)
    bev = g.sm(GW * 0.5, GW * 0.5 + 0.008, d)
    _, rc = g.white(g.comb(c, r, 3.7)); rx, ry, rz = g.sep(rc)
    tilt = ((rx - 0.5) * (fu - 0.5) * Wt + (ry - 0.5) * (fv - 0.5) * Ht) * 0.07
    wav, _ = g.noise(P, 26.0, 2.0, 0.5)
    vault = g.sm(3.6, 3.9, v)
    pit = 1.0 - g.sm(-0.06, -0.02, v)
    hgt = bev * 0.0035 + tilt * face + (wav - 0.5) * 0.00035 * face
    nrm = g.bump(hgt * (1.0 - pit), 1.0, 1.0)
    # albedo: glazed off white, a Prussian band above and below the box, soot and leaks
    soot, _ = g.noise(P, 0.55, 4.0, 0.6)
    leak, _ = g.noise(g.comb(u * 2.6, 0.0, v * 0.22), 1.0, 3.0, 0.55)
    leak = g.sm(0.56, 0.74, leak)
    fine, _ = g.noise(P, 9.0, 3.0, 0.6)
    farwall = 1.0 - vault
    bandm = g.max(g.band(0.5, 2.5, r, 0.01), g.band(38.5, 40.5, r, 0.01)) * farwall
    glaze = g.scale(g.mix((0.60, 0.61, 0.585), (0.52, 0.54, 0.53), rz), 1.0)
    tcol = g.mix(glaze, (0.010, 0.040, 0.165), bandm)
    gr = (0.78 + 0.34 * soot) * (1.0 - 0.45 * leak) * (1.0 - 0.2 * vault)
    gr = gr * (1.0 - 0.3 * (1.0 - g.sm(-0.1, 1.2, v)))
    tcol = g.scale(tcol, gr)
    grout = g.scale((0.06, 0.058, 0.055), 0.5 + 0.7 * fine)
    base = g.mix(grout, tcol, face)
    if GREEN:
        mo, _ = g.noise(P, 1.3, 4.0, 0.6)
        low = 1.0 - g.sm(0.4, 1.4, v)
        mossg = g.clamp(g.sm(0.45, 0.6, mo) * (1.0 - face) * (0.35 + 0.65 * g.max(low, leak)) * farwall * 1.6)
        mossp = g.sm(0.55, 0.66, mo) * g.max(low, leak * 0.8) * farwall
        moss = g.mix((0.035, 0.11, 0.012), (0.09, 0.22, 0.025), fine)
        base = g.mix(base, moss, g.max(mossg, mossp))
    base = g.mix(base, (0.010, 0.010, 0.010), pit)
    rough = 0.32 + 0.4 * (1.0 - face)
    coat = face * (1.0 - pit) * (0.95 - 0.5 * vault * soot)
    sh = g.principled(Base_Color=base, Roughness=g.max(rough, pit * 0.85), Normal=nrm,
                      Coat_Weight=coat, Coat_Roughness=0.025 + 0.12 * soot * vault + 0.06 * leak,
                      Coat_Normal=nrm, Specular_IOR_Level=0.4)
    g.out(sh)
    return m

def floor_mat():
    m, g = material('platform_floor')
    P, N = g.pos(); x, y, z = g.sep(P)
    T = clock(g)
    # concrete slabs with a coping row at the edge
    sx = g.fract(x / 0.9); sy = g.fract((y + 3.33) / 0.9)
    js = g.min(g.min(sx, 1.0 - sx) * 0.9, g.min(sy, 1.0 - sy) * 0.9)
    coping = g.sm(-3.36, -3.34, y)
    cx = g.fract(x / 0.6)
    jc = g.min(cx, 1.0 - cx) * 0.6
    j = g.mix(g.comb(js, js, js), g.comb(jc, jc, jc), coping); j, _, _ = g.sep(j)
    joint = 1.0 - g.sm(0.002, 0.006, j)
    agg, _ = g.noise(P, 60.0, 3.0, 0.7)
    blot, _ = g.noise(P, 1.4, 4.0, 0.6)
    _, slabc = g.white(g.comb(g.floor(x / 0.9), g.floor((y + 3.33) / 0.9), 1.0)); sr, _, _ = g.sep(slabc)
    dry = g.scale(g.mix((0.075, 0.074, 0.072), (0.13, 0.128, 0.122), coping), (0.75 + 0.5 * agg) * (0.85 + 0.3 * sr) * (0.8 + 0.4 * blot))
    dry = g.mix(dry, (0.02, 0.02, 0.02), joint)
    # puddles: shallow water in the low places, more of it in front of the box
    pn, _ = g.noise(g.comb(x * 0.6, y * 0.9, 0.0), 1.0, 4.0, 0.55)
    infront = g.sm(-3.6, -2.6, x) * (1.0 - g.sm(2.0, 3.6, x)) * g.sm(-6.5, -4.6, y)
    thr = 0.56 - 0.12 * infront + (0.04 if GREEN else 0.0)
    pud = g.sm(thr, thr + 0.06, pn + joint * 0.03)
    damp = g.sm(0.35, 0.55, pn)
    base = g.mix(dry, g.scale(dry, 0.55), damp)
    base = g.mix(base, g.scale(dry, 0.25 if not GREEN else 0.35), pud)
    if GREEN:
        mo, _ = g.noise(P, 2.2, 4.0, 0.6)
        mm = g.clamp(joint * g.sm(0.45, 0.6, mo) * 1.5 + g.sm(0.66, 0.72, mo) * coping * 0.8) * (1.0 - pud)
        base = g.mix(base, (0.05, 0.15, 0.02), mm)
    rough = 0.62 - 0.32 * damp
    rough = rough * (1.0 - pud) + 0.015 * pud
    # rings where drips land
    h = (agg - 0.5) * 0.0012 * (1.0 - pud) - joint * 0.002
    rip = None
    for i in range(len(DRIP_SPOTS)):
        cxp, cyp, Pd, ph, zt, zf, tf = drip_info(i)
        if cyp > EDGE_Y: continue
        dd = g.vm('DISTANCE', P, (cxp, cyp, 0.0))
        if LOOP:
            # the ring starts when that drip lands
            age = g.fract(T * (NFR / Pd) - ph - tf / Pd) * (Pd / 24.0)
        else:
            age = 0.15 + ((i * 0.61) % 1.0) * 0.7
        rr = dd - age * 0.32
        ring = g.sin(rr * 150.0) * g.exp(-(rr * rr) * 900.0) * g.exp(-age * 2.4) * g.sm(0.0, 0.01, age * 0.32 - dd + 0.03)
        rip = ring if rip is None else rip + ring
    if not LOOP: h = h + rip * 0.0006 * pud
    nrm = g.bump(h, 1.0, 1.0)
    sh = g.principled(Base_Color=base, Roughness=rough, Normal=nrm, Specular_IOR_Level=0.5)
    g.out(sh)
    return m

def plain(name, col, rough, metal=0.0, bumpscale=0.0, bumpamt=0.0, moss=False, sheen=0.0, coat=0.0, spec=0.5):
    m, g = material(name)
    P, N = g.pos()
    n1, _ = g.noise(P, 3.0, 4.0, 0.6)
    base = g.scale(col, 0.75 + 0.5 * n1)
    nrm = None
    if bumpscale:
        d, _ = g.voronoi(P, bumpscale)
        n2, _ = g.noise(P, bumpscale * 3, 3.0, 0.6)
        nrm = g.bump((1.0 - d) * bumpamt + n2 * bumpamt * 0.3, 1.0, 1.0)
    if moss and GREEN:
        _, _, nz = g.sep(N)
        mo, _ = g.noise(P, 1.6, 4.0, 0.6)
        mm = g.sm(0.4, 0.55, mo) * g.sm(0.2, 0.8, nz)
        base = g.mix(base, g.mix((0.04, 0.13, 0.015), (0.10, 0.25, 0.03), n1), mm)
    kw = dict(Base_Color=base, Roughness=rough, Metallic=metal, Sheen_Weight=sheen, Coat_Weight=coat, Specular_IOR_Level=spec)
    if nrm is not None: kw['Normal'] = nrm
    g.out(g.principled(**kw))
    return m

def rail_mat():
    m, g = material('rail')
    P, N = g.pos(); _, _, nz = g.sep(N); _, _, z = g.sep(P)
    n1, _ = g.noise(g.comb(g.sep(P)[0] * 0.3, 0.0, 0.0), 4.0, 3.0, 0.6)
    top = g.sm(0.8, 0.95, nz) * g.sm(-0.77, -0.765, z)
    base = g.mix((0.05, 0.048, 0.046), (0.55, 0.56, 0.58), top)
    if GREEN: base = g.mix((0.05, 0.048, 0.046), (0.16, 0.16, 0.16), top)
    rough = 0.55 - 0.42 * top * (0.7 + 0.3 * n1)
    g.out(g.principled(Base_Color=base, Metallic=0.4 + 0.6 * top, Roughness=rough))
    return m

def emission(name, col, strength, visible_glow=True):
    m, g = material(name)
    e = g.new('ShaderNodeEmission'); g.put(e.inputs[0], col); g.put(e.inputs[1], strength)
    g.out(e.outputs[0])
    return m, e

def print_mat(img, E):
    m, g = material('print')
    t = g.new('ShaderNodeTexImage', image=img, interpolation='Cubic', extension='EXTEND')
    uv = g.uv(); g.put(t.inputs[0], uv)
    u, v, _ = g.sep(uv)
    # a backlit box is a touch brighter in its middle, a touch softer at its very edge
    edge = g.min(g.min(u, 1.0 - u) * 1.78, g.min(v, 1.0 - v))
    fall = (0.88 + 0.12 * g.sm(0.0, 0.08, edge)) * (1.0 + 0.04 * g.cos((u - 0.5) * 6.283))
    # a practical on a dimmer: the camera and mirror reflections see the print at a printable level,
    # while the light it throws on tiles, floor and figure is a stop brighter (the film trick of gelling a practical)
    lp = g.new('ShaderNodeLightPath')
    k = g.max(S(g, lp.outputs['Is Shadow Ray']), S(g, lp.outputs['Is Diffuse Ray']))
    e = g.new('ShaderNodeEmission'); g.put(e.inputs[0], V(g, t.outputs[0])); g.put(e.inputs[1], fall * (E + (E * LIFT - E) * k))
    g.out(e.outputs[0])
    return m

def glass_sheet():
    m, g = material('box_glass')
    P, N = g.pos()
    sm_, _ = g.noise(P, 4.0, 4.0, 0.6)
    tr = g.new('ShaderNodeBsdfTransparent')
    gl = g.new('ShaderNodeBsdfGlossy'); g.put(gl.inputs['Roughness'], 0.004 + 0.05 * g.sm(0.55, 0.75, sm_))
    fr = g.new('ShaderNodeFresnel'); fr.inputs['IOR'].default_value = 1.52
    mx = g.new('ShaderNodeMixShader')
    g.nt.links.new(fr.outputs[0], mx.inputs[0]); g.nt.links.new(tr.outputs[0], mx.inputs[1]); g.nt.links.new(gl.outputs[0], mx.inputs[2])
    g.out(mx.outputs[0])
    return m

def water_mat():
    m, g = material('drip')
    g.out(g.principled(Base_Color=(1, 1, 1), Roughness=0.0, Transmission_Weight=1.0, IOR=1.33))
    return m

def leaf_mat(name, glossy=0.45, trans=0.35):
    m, g = material(name)
    c, _ = g.attr('col')
    P, N = g.pos()
    n1, _ = g.noise(P, 30.0, 2.0, 0.5)
    base = g.scale(c, 0.85 + 0.3 * n1)
    pr = g.principled(Base_Color=base, Roughness=glossy, Specular_IOR_Level=0.35, Sheen_Weight=0.15)
    tl = g.new('ShaderNodeBsdfTranslucent'); g.put(tl.inputs[0], g.scale(base, 1.3))
    mx = g.new('ShaderNodeMixShader'); mx.inputs[0].default_value = trans
    g.nt.links.new(pr, mx.inputs[1]); g.nt.links.new(tl.outputs[0], mx.inputs[2])
    g.out(mx.outputs[0])
    return m

def beam_mat():
    # dust and pollen thick in the daylight, thinning in slow clouds
    m, g = material('beam_dust')
    vol = g.new('ShaderNodeVolumePrincipled'); vol.inputs['Anisotropy'].default_value = 0.3
    lp = g.new('ShaderNodeLightPath'); cam = S(g, lp.outputs['Is Camera Ray'])
    P, _ = g.pos(); n1, _ = g.noise(P, 0.7, 3.0, 0.55)
    g.put(vol.inputs['Density'], cam * 0.22 * (0.35 + 1.3 * g.sm(0.35, 0.7, n1)))
    g.out(None, vol.outputs[0])
    return m

def haze_mat(density, aniso, drift=False):
    m, g = material('haze')
    vol = g.new('ShaderNodeVolumePrincipled')
    vol.inputs['Anisotropy'].default_value = aniso
    vol.inputs['Color'].default_value = (0.92, 0.95, 1.0, 1)
    lp = g.new('ShaderNodeLightPath')
    cam = S(g, lp.outputs['Is Camera Ray'])
    if drift:
        P, _ = g.pos(); T = clock(g)
        a = T * 6.2832
        off = g.comb(g.cos(a) * 0.9, 0.0, g.sin(a) * 0.9)
        n1, _ = g.noise(g.vm('ADD', P, off), 0.22, 2.0, 0.5)
        dens = density * (0.45 + 1.1 * g.sm(0.3, 0.7, n1))
        g.put(vol.inputs['Density'], dens * cam)
    else:
        # the haze is seen, not bounced through: only camera rays scatter in it, which keeps CPU renders affordable
        g.put(vol.inputs['Density'], cam * density)
    g.out(None, vol.outputs[0])
    return m

# ---------------------------------------------------------------- the station
EDGE_Y, PIT_Z, SPR, VC, VA, VB = -3.0, -1.05, 3.7, -6.0, 6.0, 2.4
XL = 26.0

def profile():
    pts = []                     # (y, z, material) walked so that faces look into the tunnel
    for y in np.linspace(-12, EDGE_Y, 19): pts.append((y, 0.0, 3))
    for z in np.linspace(0.0, PIT_Z, 4)[1:]: pts.append((EDGE_Y, z, 2))
    for y in np.linspace(EDGE_Y, 0.0, 7)[1:]: pts.append((y, PIT_Z, 1))
    for z in np.linspace(PIT_Z, SPR, 39)[1:]: pts.append((0.0, z, 0))
    for i in range(1, 97):
        th = math.pi * i / 96
        pts.append((VC + VA * math.cos(th), SPR + VB * math.sin(th), 0))
    for z in np.linspace(SPR, 0.0, 16)[1:]: pts.append((-12.0, z, 0))
    return pts

CROWN_S = [0.0]
HOLE = dict(x=-3.4, arc=None, rx=1.1, ra=0.85)

def build_station(mats):
    pr = profile()
    # arc length along the profile, zeroed so that on the far wall v equals height
    s = [0.0]
    for i in range(1, len(pr)): s.append(s[-1] + math.hypot(pr[i][0] - pr[i - 1][0], pr[i][1] - pr[i - 1][1]))
    i0 = next(i for i, p in enumerate(pr) if p[0] == 0.0 and abs(p[1] - PIT_Z) < 1e-6)
    s = [v - s[i0] + PIT_Z for v in s]
    # where the overgrown vault has opened: a broken patch near the far side, left of the box
    hy, hz = -1.25, None
    hole_s = None
    CROWN_S[0] = s[min(range(len(pr)), key=lambda i: abs(pr[i][0] - VC) + (0 if pr[i][1] > SPR else 9))]
    if GREEN:
        best = min(range(len(pr)), key=lambda i: abs(pr[i][0] - hy) + (0 if pr[i][1] > SPR else 9))
        hole_s = s[best]; HOLE['arc'] = hole_s; HOLE['pt'] = (pr[best][0], pr[best][1])
    xs = np.arange(-XL, XL + 1e-6, 0.125)
    mb = MB(); nP = len(pr)
    verts, uvs = [], []
    for x in xs:
        for (y, z, _), sv in zip(pr, s):
            verts.append((x, y, z)); uvs.append((x, sv))
    faces, fm = [], []
    for i in range(len(xs) - 1):
        for j in range(nP - 1):
            mat = pr[j + 1][2]
            if GREEN and mat == 0 and s[j] > SPR + 0.2:
                xm = (xs[i] + xs[i + 1]) * 0.5; am = (s[j] + s[j + 1]) * 0.5
                dx, da = (xm - HOLE['x']) / HOLE['rx'], (am - hole_s) / HOLE['ra']
                ang = math.atan2(da, dx)
                rim = 1.0 + 0.16 * math.sin(ang * 3 + 1.3) + 0.09 * math.sin(ang * 7 + 0.4) + 0.05 * math.sin(ang * 13)
                if dx * dx + da * da < rim * rim: continue
                # a newer, long skylight along the crown, glazed open to the sky
                if abs(am - CROWN_S[0]) < 0.6: continue
            a = i * nP + j
            faces.append((a, a + nP, a + nP + 1, a + 1)); fm.append(mat)
    mb.v, mb.uv = verts, uvs; mb.col = [(1, 1, 1, 1)] * len(verts)
    mb.f, mb.mi = faces, fm
    ob = mb.build('station', mats, smooth=True, uv=True)
    if GREEN:
        gb = MB()
        for k, off in enumerate((-0.75, -0.45, -0.15, 0.15, 0.45, 0.75)):
            if k in (2, 4): continue
            j = min(range(len(pr)), key=lambda q: abs(s[q] - (hole_s + off)) + (0 if pr[q][1] > SPR else 99))
            y, z = pr[j][0], pr[j][1]
            xa, xb = HOLE['x'] - 1.35, HOLE['x'] + 1.35
            if k == 3: xb = HOLE['x'] + 0.2
            gb.box(xa, xb, y - 0.02, y + 0.02, z + 0.02, z + 0.07, 0)
        for xx in (HOLE['x'] - 0.7, HOLE['x'] + 0.6):
            for k in range(len(pr) - 1):
                if pr[k][1] > SPR and abs(s[k] - hole_s) < 0.85:
                    y, z = pr[k][0], pr[k][1]; y2, z2 = pr[k + 1][0], pr[k + 1][1]
                    gb.box(xx - 0.02, xx + 0.02, min(y, y2) - 0.02, max(y, y2) + 0.02, min(z, z2) + 0.02, max(z, z2) + 0.08, 0)
        for k in range(int(-XL / 1.5), int(XL / 1.5) + 1):
            gb.box(k * 1.5 - 0.03, k * 1.5 + 0.03, VC - 0.65, VC + 0.65, SPR + VB - 0.02, SPR + VB + 0.06, 0)
        gb.box(-XL, XL, VC - 0.66, VC - 0.6, SPR + VB - 0.04, SPR + VB + 0.06, 0)
        gb.box(-XL, XL, VC + 0.6, VC + 0.66, SPR + VB - 0.04, SPR + VB + 0.06, 0)
        gb.build('grating', [mats[2]])
    sd = ob.modifiers.new('shell', 'SOLIDIFY'); sd.thickness = 0.3; sd.offset = -1.0; sd.use_even_offset = True
    # the two ends of the station, far off in the dark
    for x in (-XL, XL):
        bm = bmesh.new()
        vv = [bm.verts.new((x, y, z)) for (y, z, _) in pr[:-1]]
        bm.faces.new(vv if x > 0 else vv[::-1])
        me = bpy.data.meshes.new('end'); bm.to_mesh(me); bm.free()
        me.materials.append(mats[2]); e = bpy.data.objects.new('end', me); SC.collection.objects.link(e)
    return ob, pr, s

def build_ribs(pr, mat):
    mb = MB()
    arc = [(y, z) for (y, z, m) in pr if m == 0 and z >= SPR - 1e-6 and -12 < y < 0]
    arc = [(0.0, SPR)] + arc + [(-12.0, SPR)]
    for X in (-12.5, -7.5, -2.5, 2.5, 7.5, 12.5):
        if GREEN and abs(X - HOLE['x']) < 1.6: pass
        verts, faces = [], []
        for (y, z) in arc:
            th = math.atan2((z - SPR) / VB, (y - VC) / VA)
            n = np.array([-(math.cos(th)) / VA, -(math.sin(th)) / VB]); n /= np.linalg.norm(n)
            for dx in (-0.13, 0.13):
                for dd in (-0.02, 0.11):
                    verts.append((X + dx, y + n[0] * dd, z + n[1] * dd))
        for i in range(len(arc) - 1):
            a, b = i * 4, (i + 1) * 4
            for (p, q) in ((0, 1), (1, 3), (3, 2), (2, 0)):
                faces.append((a + p, a + q, b + q, b + p))
        mb.add(verts, faces, 0)
    # the cornice above the lamps, all along the far wall
    mb.box(-XL, XL, -0.16, 0.0, 3.62, 3.72, 0)
    mb.box(-XL, XL, -0.10, 0.0, 3.56, 3.62, 0)
    return mb.build('ribs', [mat], smooth=False)

def build_track(m_conc, m_rail, m_ins, m_ballast):
    mb = MB()
    for k in range(int(-XL / 0.7), int(XL / 0.7)):
        x = k * 0.7 + rng.uniform(-0.02, 0.02)
        mb.box(x - 0.13, x + 0.13, -2.75, -0.25, PIT_Z - 0.02, PIT_Z + 0.13, 0)
    rails = MB()
    prof = [(-0.07, 0.0), (0.07, 0.0), (0.07, 0.012), (0.009, 0.03), (0.009, 0.11), (0.036, 0.12), (0.036, 0.16), (-0.036, 0.16), (-0.036, 0.12), (-0.009, 0.11), (-0.009, 0.03), (-0.07, 0.012)]
    def extrude(mbx, prof, yc, zb, mat=0):
        n = len(prof); verts = []
        for x in (-XL, XL):
            for (py, pz) in prof: verts.append((x, yc + py, zb + pz))
        faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        faces.append(tuple(range(n))[::-1]); faces.append(tuple(range(n, 2 * n)))
        mbx.add(verts, faces, mat)
    for yc in (-1.5 - 0.7175, -1.5 + 0.7175): extrude(rails, prof, yc, PIT_Z + 0.13)
    # the conductor rails, on their pots
    cprof = [(-0.04, 0.0), (0.04, 0.0), (0.04, 0.07), (-0.04, 0.07)]
    extrude(rails, cprof, -1.5, PIT_Z + 0.2)
    extrude(rails, cprof, -1.5 - 0.7175 - 0.41, PIT_Z + 0.24)
    ins = MB()
    for k in range(int(-XL / 2.1), int(XL / 2.1)):
        x = k * 2.1 + 0.35
        loft(ins, [(x, -1.5, PIT_Z + 0.12, 0.045, 0.045, 2), (x, -1.5, PIT_Z + 0.2, 0.035, 0.035, 2)], 12)
        loft(ins, [(x, -2.6275, PIT_Z + 0.12, 0.045, 0.045, 2), (x, -2.6275, PIT_Z + 0.24, 0.035, 0.035, 2)], 12)
    mb.build('sleepers', [m_conc])
    rails.build('rails', [m_rail])
    ins.build('pots', [m_ins], smooth=True)

def build_lightbox(img, E, m_frame, m_glass):
    PW, PH, PZc = 4.98, 2.8, 0.35 + 1.4
    x0, x1, z0, z1 = -PW / 2, PW / 2, PZc - PH / 2, PZc + PH / 2
    FW = 0.055
    mb = MB()
    mb.box(x0 - FW, x1 + FW, -0.12, 0.0, z1, z1 + FW, 0)
    mb.box(x0 - FW, x1 + FW, -0.12, 0.0, z0 - FW, z0, 0)
    mb.box(x0 - FW, x0, -0.12, 0.0, z0, z1, 0)
    mb.box(x1, x1 + FW, -0.12, 0.0, z0, z1, 0)
    mb.box(x0, x1, -0.02, 0.0, z0, z1, 0)
    fr = mb.build('frame', [m_frame])
    bev = fr.modifiers.new('bev', 'BEVEL'); bev.width = 0.004; bev.segments = 2
    pm = MB()
    pm.add([(x0, -0.075, z0), (x1, -0.075, z0), (x1, -0.075, z1), (x0, -0.075, z1)], [(0, 1, 2, 3)], 0, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    pm.build('print', [print_mat(img, E)], uv=True)
    gm = MB()
    gm.add([(x0, -0.112, z0), (x1, -0.112, z0), (x1, -0.112, z1), (x0, -0.112, z1)], [(0, 1, 2, 3)], 0)
    gm.build('glass', [m_glass])

def build_lamps(m_house, m_on, m_dim, m_dead):
    hb = MB(); tb_on = MB(); tb_dim = MB(); tb_dead = MB()
    near = MB()
    for X in (-12.0, -7.5, 7.5, 12.0):
        verts = []
        for x in (X - 0.62, X + 0.62):
            for k in range(10):
                a = 2 * math.pi * k / 10; verts.append((x, -11.85 + 0.017 * math.cos(a), 3.45 + 0.017 * math.sin(a)))
        near.add(verts, [(k, (k + 1) % 10, 10 + (k + 1) % 10, 10 + k) for k in range(10)], 0)
    if not GREEN: near.build('tubes_behind', [m_on])
    for X, kind in ((-5.6, 'on'), (-1.7, 'dead'), (1.7, 'dead'), (5.6, 'dim'), (-9.5, 'on'), (9.5, 'on')):
        hb.box(X - 0.68, X + 0.68, -0.16, -0.02, 3.5, 3.56, 0)
        hb.box(X - 0.7, X - 0.66, -0.16, -0.02, 3.44, 3.56, 0); hb.box(X + 0.66, X + 0.7, -0.16, -0.02, 3.44, 3.56, 0)
        t = {'on': tb_on, 'dim': tb_dim, 'dead': tb_dead}[kind if not GREEN else 'dead']
        verts, faces = [], []
        for x in (X - 0.62, X + 0.62):
            for k in range(10):
                a = 2 * math.pi * k / 10; verts.append((x, -0.09 + 0.017 * math.cos(a), 3.475 + 0.017 * math.sin(a)))
        faces = [(k, (k + 1) % 10, 10 + (k + 1) % 10, 10 + k) for k in range(10)] + [tuple(range(10))[::-1], tuple(range(10, 20))]
        t.add(verts, faces, 0)
    hb.build('lamp_housings', [m_house])
    for t, m, nm in ((tb_on, m_on, 'tubes_on'), (tb_dim, m_dim, 'tube_failing'), (tb_dead, m_dead, 'tubes_dead')):
        if t.v: t.build(nm, [m], smooth=True)

def build_figure(mats):
    m_coat, m_trou, m_shoe, m_skin, m_hair = mats
    X0, Y0 = 1.42, -3.42
    coat, trou, shoe, skin, hair = MB(), MB(), MB(), MB(), MB()
    # coat: a long dark wool coat, hem just below the knee, seen from behind
    rings = [(0, 0.0, 0.43, 0.245, 0.17, 2.4), (0, 0.0, 0.47, 0.24, 0.165, 2.4), (0, 0.0, 0.7, 0.225, 0.15, 2.4), (0, 0.0, 0.94, 0.205, 0.135, 2.5),
             (0, 0.0, 1.08, 0.188, 0.125, 2.5), (0, 0.0, 1.26, 0.198, 0.135, 2.6), (0, 0.0, 1.38, 0.212, 0.135, 2.8),
             (0, 0.005, 1.44, 0.218, 0.125, 2.8), (0, 0.005, 1.49, 0.185, 0.11, 2.4), (0, 0.01, 1.535, 0.12, 0.085, 2.2), (0, 0.01, 1.56, 0.075, 0.07, 2.0)]
    loft(coat, rings, 32)
    for sgn in (-1, 1):
        arm = [(sgn * 0.17, 0.0, 1.43, 0.05, 0.06, 2.0), (sgn * 0.205, 0.0, 1.38, 0.06, 0.064, 2.0), (sgn * 0.222, 0.0, 1.28, 0.058, 0.062, 2.0), (sgn * 0.232, 0.01, 1.14, 0.05, 0.055, 2.0),
               (sgn * 0.238, 0.02, 0.96, 0.045, 0.05, 2.0), (sgn * 0.24, 0.025, 0.84, 0.048, 0.052, 2.0), (sgn * 0.24, 0.025, 0.825, 0.03, 0.03, 2.0)]
        loft(coat, arm, 16)
        hand = [(sgn * 0.238, 0.03, 0.84, 0.026, 0.038, 2.0), (sgn * 0.236, 0.035, 0.76, 0.024, 0.042, 2.2), (sgn * 0.232, 0.04, 0.69, 0.018, 0.03, 2.0)]
        loft(skin, hand, 12)
        leg = [(sgn * 0.105, 0.0, 0.075, 0.046, 0.05, 2.0), (sgn * 0.103, 0.0, 0.16, 0.044, 0.05, 2.0), (sgn * 0.1, 0.0, 0.32, 0.055, 0.06, 2.0),
               (sgn * 0.097, 0.0, 0.5, 0.066, 0.07, 2.0), (sgn * 0.095, 0.0, 0.62, 0.075, 0.08, 2.0)]
        loft(trou, leg, 16)
        sh = [(sgn * 0.107, 0.035, 0.0, 0.048, 0.13, 2.6), (sgn * 0.107, 0.035, 0.035, 0.05, 0.13, 2.6), (sgn * 0.106, 0.015, 0.075, 0.045, 0.085, 2.2), (sgn * 0.105, 0.0, 0.1, 0.035, 0.045, 2.0)]
        loft(shoe, sh, 16)
        ellipsoid(skin, sgn * 0.078, 0.012, 1.675, 0.012, 0.028, 0.032, 10, 6)
    loft(skin, [(0, 0.012, 1.5, 0.052, 0.055, 2.0), (0, 0.016, 1.62, 0.05, 0.052, 2.0)], 16)
    ellipsoid(hair, 0, 0.008, 1.672, 0.083, 0.102, 0.114, 24, 14)
    # a turned up collar, which is what makes a coat read as a coat from behind
    loft(coat, [(0, 0.012, 1.5, 0.098, 0.088, 2.2), (0, 0.006, 1.555, 0.088, 0.08, 2.2), (0, 0.0, 1.6, 0.084, 0.078, 2.2)], 24)
    out = []
    for mb, m, nm in ((coat, m_coat, 'coat'), (trou, m_trou, 'trousers'), (shoe, m_shoe, 'shoes'), (skin, m_skin, 'skin'), (hair, m_hair, 'hair')):
        mb.v = [(x + X0, y + Y0, z) for (x, y, z) in mb.v]
        out.append(subsurf(mb.build(nm, [m], smooth=True), 2))
    return out

DRIP_SPOTS = [(-0.9, -2.4), (0.62, -3.9), (2.45, -5.2), (-1.35, -4.6), (-3.2, -1.2), (3.5, -0.9), (-0.4, -3.55), (1.8, -4.1), (-2.2, -2.0), (0.3, -1.6)]
DRIP_PERIODS = [24, 36, 72, 24, 36, 72, 36, 24, 72, 36]

def drip_info(i):
    x, y = DRIP_SPOTS[i]
    P = DRIP_PERIODS[i]; ph = (i * 0.37) % 1.0
    zt = SPR + VB * math.sqrt(max(0.0, 1 - ((y - VC) / VA) ** 2)) - 0.05
    zf = 0.0 if y < EDGE_Y else PIT_Z + 0.15
    tf = math.sqrt(2 * (zt - zf) / 9.81) * 24.0
    return x, y, P, ph, zt, zf, tf

def build_drips(m, still=True):
    obs = []
    for i, (x, y) in enumerate(DRIP_SPOTS):
        mb = MB()
        loft(mb, [(0, 0, -0.04, 0.0006, 0.0006, 2), (0, 0, -0.02, 0.0022, 0.0022, 2), (0, 0, 0.03, 0.0026, 0.0026, 2), (0, 0, 0.055, 0.001, 0.001, 2)], 10)
        ob = mb.build('drip%d' % i, [m], smooth=True)
        _, _, _, _, zt, zf, _ = drip_info(i)
        ob['ztop'], ob['zfloor'] = zt, zf
        ob.location = (x, y, zt)
        if still:
            ob.location = (x, y, rng.uniform(zf + 0.4, min(zt - 0.3, 3.4)))
            ob.scale = (1, 1, 1.6)
        obs.append(ob)
    return obs

def animate_drips(obs):
    for i, ob in enumerate(obs):
        x, y, P, ph, zt, zf, tf = drip_info(i)
        for f in range(1, NFR + 2):
            age = ((f - 1) / P - ph) % 1.0 * P
            if age < tf:
                tt = age / 24.0; z = zt - 0.5 * 9.81 * tt * tt; sc = 1.0
            else:
                z = zt; sc = 0.0
            ob.location = (x, y, z); ob.scale = (sc, sc, sc * (1.0 + 0.8 * min(1, age / tf)))
            ob.keyframe_insert('location', frame=f); ob.keyframe_insert('scale', frame=f)
        for fc in ob.animation_data.action.fcurves:
            for k in fc.keyframe_points: k.interpolation = 'LINEAR'

def flicker_values():
    # a failing tube: mostly a low, steady glow, with stutters and one near blackout, periodic over the loop
    rs = random.Random(3)
    vals = []
    for f in range(NFR):
        v = 1.0
        if 10 <= f < 14: v = [0.15, 0.9, 0.05, 0.7][f - 10]
        if 40 <= f < 47: v = [0.6, 0.02, 0.02, 0.4, 0.05, 0.85, 0.9][f - 40]
        if f in (58, 59): v = 0.35
        vals.append(v * (0.96 + 0.04 * rs.random()))
    return vals

def flicker(node_input, owner_nt, base):
    vals = [base * v for v in flicker_values()]
    vals.append(vals[0])
    dp = node_input.path_from_id('default_value')
    for f, v in enumerate(vals):
        node_input.default_value = v; owner_nt.keyframe_insert(dp, frame=f + 1)
    for fc in owner_nt.animation_data.action.fcurves:
        for k in fc.keyframe_points: k.interpolation = 'CONSTANT'

# ---------------------------------------------------------------- growth for the overgrown future
GCOL = [(0.07, 0.22, 0.025), (0.12, 0.32, 0.04), (0.18, 0.40, 0.06), (0.05, 0.17, 0.02), (0.22, 0.42, 0.08)]

def grass(mb, bases, dirs, heights, widths, lean, cols, segs=5):
    n = len(bases)
    for i in range(n):
        b = bases[i]; d = dirs[i]; h = heights[i]; w = widths[i]; l = lean[i]
        side = np.cross(d, l); ns = np.linalg.norm(side); side = side / ns if ns > 1e-6 else np.array([1.0, 0, 0])
        verts = []
        for k in range(segs + 1):
            t = k / segs
            p = b + d * h * t + l * h * t * t * 0.55 + np.array([0, 0, -1.0]) * h * 0.25 * t ** 3 * np.linalg.norm(l)
            ww = w * (1 - t) ** 0.8 + 0.0004
            verts.append(tuple(p - side * ww)); verts.append(tuple(p + side * ww))
        faces = [(2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2) for k in range(segs)]
        mb.add(verts, faces, 0, col=cols[i])

def tuft(mb, centre, normal, count, hmin, hmax, spread=0.05, cols=None):
    normal = np.array(normal, float); normal /= np.linalg.norm(normal)
    bases, dirs, hs, ws, ln, cs = [], [], [], [], [], []
    for _ in range(count):
        off = nrng.normal(0, spread, 3); off -= normal * off.dot(normal)
        bases.append(np.array(centre) + off)
        d = normal * 1.0 + nrng.normal(0, 0.28, 3) + np.array([0, 0, 0.6 if normal[2] < 0.5 else 0])
        d /= np.linalg.norm(d); dirs.append(d)
        hs.append(rng.uniform(hmin, hmax)); ws.append(rng.uniform(0.0025, 0.006))
        l = nrng.normal(0, 0.6, 3); l[2] = 0; ln.append(l)
        c = rng.choice(cols or GCOL); cs.append((c[0] * rng.uniform(0.8, 1.2), c[1] * rng.uniform(0.85, 1.15), c[2], 1))
    grass(mb, bases, dirs, hs, ws, ln, cs)

def fern(mb, base, size, rot, col=(0.05, 0.2, 0.03), up=(0, 0, 1)):
    nf = rng.randint(8, 13)
    up = np.array(up, float); up /= np.linalg.norm(up)
    tmp = np.array([1.0, 0, 0]) if abs(up[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(up, tmp); e1 /= np.linalg.norm(e1); e2 = np.cross(up, e1)
    for fi in range(nf):
        az = rot + 2 * math.pi * fi / nf + rng.uniform(-0.25, 0.25)
        el = rng.uniform(0.55, 1.15)
        L = size * rng.uniform(0.65, 1.0)
        hd = e1 * math.cos(az) + e2 * math.sin(az)
        pts = []
        for k in range(26):
            t = k / 25
            p = np.array(base) + hd * L * t * math.cos(el * (1 - 0.7 * t)) + up * L * (t * math.sin(el) - 0.55 * t * t * (1.1 - el * 0.5))
            pts.append(p)
        c = (col[0] * rng.uniform(0.8, 1.3), col[1] * rng.uniform(0.85, 1.2), col[2], 1)
        verts, faces = [], []
        for k in range(2, 25):
            t = k / 25
            p = pts[k]; tan = pts[k + 1] - pts[k - 1]; tan /= np.linalg.norm(tan)
            sd = np.cross(tan, up); sd /= max(np.linalg.norm(sd), 1e-6)
            nrm = np.cross(sd, tan)
            pl = L * 0.2 * math.sin(math.pi * min(1, t * 1.05)) ** 0.8 * (1 - 0.35 * t) + 0.006
            for sg in (-1, 1):
                dirp = sd * sg * 0.85 + tan * 0.45 - nrm * 0.15
                dirp /= np.linalg.norm(dirp)
                tip = p + dirp * pl
                wv = tan * pl * 0.17
                o = len(verts)
                verts += [tuple(p), tuple(p + dirp * pl * 0.5 + wv), tuple(tip), tuple(p + dirp * pl * 0.5 - wv)]
                faces.append((o, o + 1, o + 2, o + 3))
        # the stem
        for k in range(25):
            p, q = pts[k], pts[k + 1]
            tan = q - p; sd = np.cross(tan, up); sd /= max(np.linalg.norm(sd), 1e-6); w = 0.0025
            o = len(verts); verts += [tuple(p - sd * w), tuple(p + sd * w), tuple(q + sd * w), tuple(q - sd * w)]
            faces.append((o, o + 1, o + 2, o + 3))
        mb.add(verts, faces, 0, col=c)

IVY_LEAF = [(0.0, 0.0), (0.35, 0.15), (0.5, 0.45), (0.28, 0.55), (0.22, 0.85), (0.0, 1.0), (-0.22, 0.85), (-0.28, 0.55), (-0.5, 0.45), (-0.35, 0.15)]

def ivy_strand(mb, stems, top, length, wall_n=None):
    pts = [np.array(top, float)]
    step = 0.04; n = int(length / step)
    ph = rng.uniform(0, 6.28)
    for k in range(n):
        p = pts[-1] + np.array([0.004 * math.sin(k * 0.25 + ph), 0.003 * math.cos(k * 0.31 + ph), -step])
        pts.append(p)
    stems.append(pts)
    col = rng.choice([(0.04, 0.14, 0.025), (0.06, 0.2, 0.035), (0.09, 0.26, 0.04)])
    for k in range(1, n, 1):
        t = k / n
        s = rng.uniform(0.045, 0.08) * (1.1 - 0.4 * t)
        p = pts[k]
        az = rng.uniform(-math.pi, math.pi) if wall_n is None else math.atan2(wall_n[0], wall_n[1]) + rng.uniform(-1.2, 1.2)
        outv = np.array([math.sin(az), -math.cos(az) if wall_n is None else math.cos(az), 0]) if wall_n is None else np.array([math.sin(az), math.cos(az), 0.0])
        dn = np.array([0, 0, -1.0]) * 0.6 + outv * 0.8; dn /= np.linalg.norm(dn)
        sd = np.cross(dn, np.array([0, 0, 1.0])); sd /= max(np.linalg.norm(sd), 1e-6)
        nrm = np.cross(sd, dn)
        tilt = rng.uniform(-0.6, 0.6)
        ax = dn * math.cos(tilt) + nrm * math.sin(tilt)
        verts = [tuple(p + (sd * lx + ax * ly) * s + nrm * 0.15 * s * ly * ly) for (lx, ly) in IVY_LEAF]
        cv = (col[0] * rng.uniform(0.8, 1.25), col[1] * rng.uniform(0.85, 1.2), col[2], 1)
        mb.add(verts, [tuple(range(len(IVY_LEAF)))], 0, col=cv)

def build_growth(mats):
    m_grass, m_fern, m_ivy, m_pollen, m_flower = mats
    gm, fm, im, flm = MB(), MB(), MB(), MB()
    stems = []
    # the track bed: grass in drifts, deep in the middle, thinner on the sleepers and rails
    for _ in range(3200):
        x = rng.uniform(-9, 9); y = rng.uniform(-2.95, -0.05)
        dens = 0.5 + 0.5 * math.sin(x * 0.7 + 1.3) * math.cos(x * 0.31)
        if rng.random() > 0.35 + 0.65 * dens: continue
        tuft(gm, (x, y, PIT_Z), (0, 0, 1), rng.randint(8, 18), 0.9, 1.75 + 0.15 * dens, 0.07)
    # ferns along the track bed and under the platform edge
    for _ in range(26):
        x = rng.uniform(-10, 10); y = rng.choice([rng.uniform(-2.85, -2.5), rng.uniform(-0.6, -0.15), rng.uniform(-2.4, -0.6)])
        fern(fm, (x, y, PIT_Z + 0.05), rng.uniform(0.8, 1.35), rng.uniform(0, 6.28))
    # the platform's edge and its joints
    for _ in range(70):
        x = rng.uniform(-8, 8)
        tuft(gm, (x, rng.uniform(-3.12, -3.02), 0.0), (0, 0.3, 1), rng.randint(5, 12), 0.06, 0.28, 0.03)
    for _ in range(40):
        x = rng.uniform(-6, 6); y = -3.33 - 0.9 * rng.randint(0, 3) + rng.uniform(-0.01, 0.01)
        tuft(gm, (x, y, 0.0), (0, 0, 1), rng.randint(3, 8), 0.04, 0.14, 0.02)
    for _ in range(14):
        x = rng.uniform(-6, 6)
        fern(fm, (x, -3.05, 0.0), rng.uniform(0.25, 0.4), rng.uniform(0, 6.28), up=(0, -0.8, 1))
    # tile joints on the far wall, clear of the lightbox by a hand's width
    for _ in range(170):
        x = rng.uniform(-9, 9); z = rng.choice([rng.uniform(-0.9, 0.3), rng.uniform(0.0, 3.4), rng.uniform(3.2, 3.55)])
        z = round(z / 0.0835) * 0.0835
        if -2.85 < x < 2.85 and 0.05 < z < 3.5: continue
        if rng.random() < 0.75:
            tuft(gm, (x, -0.003, z), (0, -1, 0.35), rng.randint(3, 9), 0.05, 0.22, 0.02)
        else:
            fern(fm, (x, -0.003, z), rng.uniform(0.12, 0.25), rng.uniform(0, 6.28), up=(0, -1, 0.4))
    # small white and pale sky flowers on the edge and in the track bed
    for _ in range(60):
        x = rng.uniform(-7, 7)
        y, z = (rng.uniform(-3.1, -3.0), 0.0) if rng.random() < 0.4 else (rng.uniform(-2.9, -0.1), PIT_Z)
        h = rng.uniform(0.9, 1.35) if z < 0 else rng.uniform(0.08, 0.2)
        top = np.array([x + rng.uniform(-0.03, 0.03), y + rng.uniform(-0.03, 0.03), z + h])
        tuft(gm, (x, y, z), (0, 0, 1), 1, h * 0.95, h, 0.0)
        c = rng.choice([(0.85, 0.86, 0.8, 1), (0.8, 0.82, 0.78, 1), (0.42, 0.62, 0.85, 1)])
        r = rng.uniform(0.008, 0.014); verts = [tuple(top)]; faces = []
        for k in range(10):
            a = 2 * math.pi * k / 10; rr = r * (1.0 if k % 2 == 0 else 0.55)
            verts.append(tuple(top + np.array([math.cos(a) * rr, math.sin(a) * rr, 0.002])))
        for k in range(10): faces.append((0, 1 + k, 1 + (k + 1) % 10))
        flm.add(verts, faces, 0, col=c)
    # ivy: from the cornice either side of the box, and from the opened vault into the light
    for _ in range(110):
        x = rng.choice([rng.uniform(-9, -2.9), rng.uniform(2.9, 9)])
        ivy_strand(im, stems, (x, -0.17, 3.6), rng.uniform(0.5, 3.0) if abs(x) > 3.2 else rng.uniform(0.3, 1.2), wall_n=(0, -1))
    for _ in range(18):
        x = rng.uniform(-2.8, 2.8)
        ivy_strand(im, stems, (x, -0.17, 3.6), rng.uniform(0.08, 0.25), wall_n=(0, -1))
    hx, (hy, hz) = HOLE['x'], HOLE['pt']
    for _ in range(44):
        a = rng.uniform(0, 2 * math.pi)
        x = hx + math.cos(a) * HOLE['rx'] * 1.05; y = hy + math.sin(a) * 0.9
        y = min(-0.2, max(-3.4, y))
        zt = SPR + VB * math.sqrt(max(0.0, 1 - ((y - VC) / VA) ** 2)) - 0.03
        ivy_strand(im, stems, (x, y, zt), rng.uniform(0.6, 2.6))
    for _ in range(30):
        x = rng.uniform(-10, 10)
        if -3.2 < x < 3.2: continue
        y = rng.uniform(-2.5, -0.5); zt = SPR + VB * math.sqrt(max(0.0, 1 - ((y - VC) / VA) ** 2)) - 0.03
        ivy_strand(im, stems, (x, y, zt), rng.uniform(0.3, 1.6))
    gm.build('grass', [m_grass], smooth=True, col=True)
    fm.build('ferns', [m_fern], smooth=True, col=True)
    im.build('ivy', [m_ivy], smooth=True, col=True)
    flm.build('flowers', [m_flower], col=True)
    cu = bpy.data.curves.new('ivy_stems', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.0025; cu.bevel_resolution = 1
    for pts in stems:
        sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts): sp.points[i].co = (p[0], p[1], p[2], 1)
    co = bpy.data.objects.new('ivy_stems', cu); SC.collection.objects.link(co); cu.materials.append(m_ivy)
    # dust and pollen held in the shaft of daylight
    pm = MB()
    hp = np.array([hx, hy, hz])
    ico_v = [(0, 0, 1), (0.894, 0, 0.447), (0.276, 0.851, 0.447), (-0.724, 0.526, 0.447), (-0.724, -0.526, 0.447), (0.276, -0.851, 0.447),
             (0.724, 0.526, -0.447), (-0.276, 0.851, -0.447), (-0.894, 0, -0.447), (-0.276, -0.851, -0.447), (0.724, -0.526, -0.447), (0, 0, -1)]
    ico_f = [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 5), (0, 5, 1), (1, 6, 2), (2, 7, 3), (3, 8, 4), (4, 9, 5), (5, 10, 1),
             (6, 7, 2), (7, 8, 3), (8, 9, 4), (9, 10, 5), (10, 6, 1), (11, 7, 6), (11, 8, 7), (11, 9, 8), (11, 10, 9), (11, 6, 10)]
    D = SUN_DIR / np.linalg.norm(SUN_DIR)
    for _ in range(2600):
        t = rng.uniform(0.2, 1.0) ** 0.8 * (hz / -D[2])
        p = hp + D * t + np.array([rng.gauss(0, 0.5), rng.gauss(0, 0.35), rng.gauss(0, 0.3)])
        if p[2] < 0.05 or p[1] > -0.1: continue
        r = rng.uniform(0.0012, 0.0032)
        pm.add([tuple(p + np.array(v) * r) for v in ico_v], ico_f, 0)
    pm.build('pollen', [m_pollen], smooth=True)

SUN_DIR = np.array([0.08, -0.12, -1.0])
LIFT = 2.2

# ---------------------------------------------------------------- assemble
def compose():
    # out = off + v(f) (on - off), then the moving water over it, then the house view transform and a soft bloom
    src = arg('--src', HERE)
    def load(pth):
        im = bpy.data.images.load(pth); w, h = im.size
        a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4); bpy.data.images.remove(im); return a
    on = load(os.path.join(src, 'on.exr')); off = load(os.path.join(src, 'off.exr'))
    h, w = on.shape[:2]
    vals = flicker_values()
    vs = SC.view_settings; vs.view_transform = 'AgX'; vs.look = 'AgX - Base Contrast'; vs.exposure = 0.3
    SC.render.image_settings.file_format = 'PNG'; SC.render.image_settings.color_mode = 'RGB'; SC.render.image_settings.color_depth = '8'
    def blur(x, rad):
        # three box passes approximate a gaussian
        for _ in range(3):
            for ax in (0, 1):
                pad = [(0, 0)] * 3; pad[ax] = (rad + 1, rad)
                c = np.cumsum(np.pad(x, pad, mode='edge'), axis=ax); n = x.shape[ax]
                x = (np.take(c, np.arange(2 * rad + 1, 2 * rad + 1 + n), axis=ax) - np.take(c, np.arange(n), axis=ax)) / (2 * rad + 1)
        return x
    out_img = bpy.data.images.new('frame', w, h, float_buffer=True, alpha=False)
    a, b = map(int, FRAMES.split('-'))
    for f in range(a, b + 1):
        lin = off[..., :3] + vals[(f - 1) % NFR] * (on[..., :3] - off[..., :3])
        dp = os.path.join(src, 'anim_%04d.exr' % f)
        if os.path.exists(dp):
            d = load(dp); lin = lin * (1.0 - d[..., 3:4]) + d[..., :3]
        lum = lin.mean(-1, keepdims=True)
        hi = np.maximum(lin - 0.9, 0.0) * np.clip((lum - 0.9) * 4, 0, 1)
        small = hi[::4, ::4]
        bl = blur(small, 6) * 0.6 + blur(small, 18) * 0.4
        bl = np.repeat(np.repeat(bl, 4, 0), 4, 1)[:h, :w]
        lin = lin + bl * 0.22
        px = np.concatenate([lin, np.ones((h, w, 1), np.float32)], -1)
        out_img.pixels.foreach_set(px.ravel())
        out_img.save_render(OUT.replace('####', '%04d' % f), scene=SC)
        print('composed', f); sys.stdout.flush()

def main():
    if PASS == 'compose':
        compose(); return
    t0 = time.time()
    img = make_print()
    m_tile = tile_mat()
    m_ballast = plain('ballast', (0.035, 0.034, 0.033), 0.85, bumpscale=22.0, bumpamt=0.012, moss=True)
    m_edge = plain('edge', (0.03, 0.03, 0.03), 0.8, moss=True)
    m_floor = floor_mat()
    m_iron = plain('iron', (0.018, 0.019, 0.021), 0.45, metal=0.6, moss=True)
    m_conc = plain('sleeper', (0.09, 0.088, 0.085), 0.85, bumpscale=40.0, bumpamt=0.003, moss=True)
    m_ins = plain('pots', (0.5, 0.5, 0.48), 0.25, coat=0.6)
    m_rail = rail_mat()
    m_frame = plain('frame', (0.03, 0.032, 0.036), 0.32, metal=0.9)
    m_glass = glass_sheet()
    E_PRINT = 1.7 if not GREEN else 1.9
    if arg('--dbg', '') == 'tiles': m_tile = plain('t', (0.5, 0.5, 0.5), 0.3)
    if arg('--dbg', '') == 'floor': m_floor = plain('f', (0.05, 0.05, 0.05), 0.1)
    station, pr, s = build_station([m_tile, m_ballast, m_edge, m_floor])
    build_ribs(pr, m_iron)
    build_track(m_conc, m_rail, m_ins, m_ballast)
    build_lightbox(img, E_PRINT, m_frame, m_glass)
    m_on, _ = emission('tube_on', (0.82, 0.9, 1.0), 34.0)
    m_dim, e_dim = emission('tube_failing', (0.78, 0.88, 1.0), 2.6)
    m_dead = plain('tube_dead', (0.5, 0.52, 0.55), 0.2, coat=0.5)
    m_house = plain('housing', (0.05, 0.052, 0.055), 0.4, metal=0.7)
    build_lamps(m_house, m_on, m_dim, m_dead)
    m_coat = plain('coat', (0.016, 0.018, 0.026), 0.75, sheen=0.7, bumpscale=180.0, bumpamt=0.0004)
    m_trou = plain('trousers', (0.012, 0.012, 0.014), 0.7, sheen=0.4)
    m_shoe = plain('shoes', (0.01, 0.01, 0.01), 0.3)
    m_skin = plain('skin', (0.32, 0.2, 0.16), 0.5)
    m_hair = plain('hair', (0.012, 0.011, 0.011), 0.6, sheen=0.15, spec=0.3)
    build_figure([m_coat, m_trou, m_shoe, m_skin, m_hair])
    m_drip = water_mat()
    if not GREEN:
        if not LOOP:
            build_drips(m_drip, still=True)
        elif PASS == 'off':
            e_dim.inputs[1].default_value = 0.0
    # haze in the vault
    if arg('--nohaze', '0') == '0':
      hb = MB(); hb.box(-XL, XL, -12, 0, PIT_Z, SPR + VB + 0.05, 0)
      hz = hb.build('haze', [haze_mat(0.005 if GREEN else 0.017, 0.55 if GREEN else 0.3, drift=False)])
      hz.visible_shadow = True
    # world
    wm = bpy.data.worlds.new('w'); SC.world = wm; wm.use_nodes = True; nt = wm.node_tree; nt.nodes.clear(); g = G(nt)
    bg = g.new('ShaderNodeBackground'); o = g.new('ShaderNodeOutputWorld'); nt.links.new(bg.outputs[0], o.inputs[0])
    if GREEN:
        gp = g.new('ShaderNodeNewGeometry'); _, _, iz = g.sep(g.scale(V(g, gp.outputs['Incoming']), -1.0))
        sky = g.mix((0.62, 0.76, 0.95), (0.16, 0.36, 0.85), g.sm(0.0, 0.9, iz))
        g.put(bg.inputs[0], sky); bg.inputs[1].default_value = 3.6
        sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 14.0; sun.angle = math.radians(0.6); sun.color = (1.0, 0.96, 0.9)
        so = bpy.data.objects.new('sun', sun); SC.collection.objects.link(so)
        D = SUN_DIR / np.linalg.norm(SUN_DIR)
        from mathutils import Vector
        so.rotation_euler = Vector(tuple(D)).to_track_quat('-Z', 'Y').to_euler()
        hx, (hy, hzz) = HOLE['x'], HOLE['pt']
        pl = bpy.data.lights.new('portal', 'AREA'); pl.shape = 'RECTANGLE'; pl.size = 2.8; pl.size_y = 2.4
        try: pl.cycles.is_portal = True
        except Exception: pass
        po = bpy.data.objects.new('portal', pl); SC.collection.objects.link(po)
        po.location = (hx, hy, hzz + 0.35)
        sk = bpy.data.lights.new('skylight_portal', 'AREA'); sk.shape = 'RECTANGLE'; sk.size = 2 * XL; sk.size_y = 1.25
        try: sk.cycles.is_portal = True
        except Exception: pass
        sko = bpy.data.objects.new('skylight_portal', sk); SC.collection.objects.link(sko); sko.location = (0, VC, SPR + VB + 0.08)
        bm_ = MB(); hp = np.array([hx, hy, hzz + 0.6]); Dn = SUN_DIR / np.linalg.norm(SUN_DIR)
        e1 = np.cross(Dn, [1.0, 0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(Dn, e1)
        tmax = (hzz + 0.6 - PIT_Z) / -Dn[2]
        verts = []
        for t in (0.0, tmax):
            for k in range(16):
                a = 2 * math.pi * k / 16; verts.append(tuple(hp + Dn * t + (e1 * math.cos(a) * 1.2 + e2 * math.sin(a) * 0.95) * 1.0))
        faces = [(k, (k + 1) % 16, 16 + (k + 1) % 16, 16 + k) for k in range(16)] + [tuple(range(16))[::-1], tuple(range(16, 32))]
        bm_.add(verts, faces, 0)
        bm_.build('beam_dust', [beam_mat()])
        build_growth([leaf_mat('grass', 0.5, 0.4), leaf_mat('fern', 0.45, 0.4), leaf_mat('ivy', 0.32, 0.25),
                      plain('pollen', (0.9, 0.9, 0.85), 0.6), leaf_mat('flower', 0.5, 0.35)])
    else:
        bg.inputs[0].default_value = (0.002, 0.003, 0.005, 1); bg.inputs[1].default_value = 1.0
    # camera: the real-time framing, eye height, looking across the tracks, a touch of yaw
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); SC.collection.objects.link(cam); SC.camera = cam
    cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24.0; cd.lens = 12.0 / 0.364; cd.shift_y = 0.03 / (2 * 0.364 * 1.6)
    cd.clip_start = 0.1; cd.clip_end = 80
    cam.location = (math.sin(math.radians(1.5)) * 9.5, -9.5, 1.5); cam.rotation_euler = (math.radians(90), 0, math.radians(1.5))
    cd.dof.use_dof = True; cd.dof.focus_distance = 6.1; cd.dof.aperture_fstop = 2.8
    # render
    r = SC.render; r.engine = 'CYCLES'; r.resolution_x, r.resolution_y = 1920, 1200; r.resolution_percentage = RES
    r.threads_mode = 'FIXED'; r.threads = 4
    c = SC.cycles; c.device = 'CPU'; c.samples = SAMPLES; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.012 if not LOOP else 0.03
    c.adaptive_min_samples = 48; c.time_limit = TL
    c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'; c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; c.denoising_prefilter = 'ACCURATE'
    c.max_bounces = 8; c.diffuse_bounces = 3; c.glossy_bounces = 3; c.transmission_bounces = 6; c.volume_bounces = 0; c.transparent_max_bounces = 8
    c.sample_clamp_indirect = 8.0; c.blur_glossy = 0.8; c.caustics_refractive = False
    c.volume_step_rate = 4.0; c.volume_max_steps = 256
    c.use_light_tree = True
    if LOOP: c.seed = 11; c.use_animated_seed = False
    r.use_motion_blur = LOOP; r.motion_blur_shutter = 0.5
    vs = SC.view_settings; vs.view_transform = 'AgX'; vs.look = 'AgX - Base Contrast'; vs.exposure = 0.3 if not GREEN else 0.35
    r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGB'; r.image_settings.color_depth = '8'
    # a gentle bloom, nothing more
    SC.use_nodes = True; ct = SC.node_tree; ct.nodes.clear()
    rl = ct.nodes.new('CompositorNodeRLayers'); gl = ct.nodes.new('CompositorNodeGlare'); co = ct.nodes.new('CompositorNodeComposite')
    gl.glare_type = 'BLOOM'
    for k, v in (('Threshold', 0.9), ('Strength', 0.22), ('Size', 0.6), ('Saturation', 1.0)):
        try: gl.inputs[k].default_value = v
        except Exception: pass
    ct.links.new(rl.outputs['Image'], gl.inputs['Image']); ct.links.new(gl.outputs[0], co.inputs['Image'])
    print('BUILD %.1fs' % (time.time() - t0)); sys.stdout.flush()
    t1 = time.time()
    if LOOP:
        r.resolution_x, r.resolution_y = int(1280 * RES / 67), int(800 * RES / 67); r.resolution_percentage = 100
        # the loop is built from linear passes: the platform with the failing lamp on and off, rendered
        # once each, and the moving water (drips and the rings they leave) rendered every frame on its own
        SC.use_nodes = False
        r.image_settings.file_format = 'OPEN_EXR'; r.image_settings.color_depth = '32'; r.image_settings.exr_codec = 'ZIP'
        r.image_settings.color_mode = 'RGBA'
        r.fps = 24
        if PASS in ('on', 'off'):
            r.filepath = OUT; bpy.ops.render.render(write_still=True)
        else:
            static = bpy.data.collections.new('static'); SC.collection.children.link(static)
            for ob in list(SC.collection.objects):
                static.objects.link(ob); SC.collection.objects.unlink(ob)
            bpy.context.view_layer.layer_collection.children['static'].indirect_only = True
            drips = build_drips(m_drip, still=False); animate_drips(drips)
            m_ring = plain('ripple', (0.0, 0.0, 0.0), 0.02, spec=0.5)
            r.film_transparent = True; r.use_motion_blur = True
            c.adaptive_threshold = 0.02; c.adaptive_min_samples = 16
            a, b = map(int, FRAMES.split('-'))
            ring_ob = None
            for f in range(a, b + 1):
                SC.frame_set(f)
                if ring_ob is not None:
                    me = ring_ob.data; bpy.data.objects.remove(ring_ob); bpy.data.meshes.remove(me); ring_ob = None
                mb = MB()
                for i in range(len(DRIP_SPOTS)):
                    x, y, P, ph, zt, zf, tf = drip_info(i)
                    if y > EDGE_Y: continue
                    age = (((f - 1) / P - ph) % 1.0 * P - tf) / 24.0
                    if age < 0: age += P / 24.0
                    if age > 1.0: continue
                    for kk, (sp_, am) in enumerate(((1.0, 1.0), (0.62, 0.55))):
                        R = 0.008 + 0.17 * age * sp_; A = math.exp(-age * 3.6) * am
                        w = 0.003 + 0.008 * age; hgt = 0.0008 * A
                        if hgt < 0.00008: continue
                        n = 48; verts = []; faces = []
                        prof = [(-w, 0.0), (-w * 0.5, hgt * 0.7), (0.0, hgt), (w * 0.5, hgt * 0.7), (w, 0.0)]
                        for k in range(n):
                            th = 2 * math.pi * k / n
                            for (dr, dz) in prof: verts.append((x + (R + dr) * math.cos(th), y + (R + dr) * math.sin(th), 0.0004 + dz))
                        m5 = len(prof)
                        for k in range(n):
                            for q in range(m5 - 1):
                                a0 = k * m5 + q; b0 = ((k + 1) % n) * m5 + q
                                faces.append((a0, a0 + 1, b0 + 1, b0))
                        mb.add(verts, faces, 0)
                if mb.v:
                    ring_ob = mb.build('ripples', [m_ring], smooth=True)
                r.filepath = OUT.replace('####', '%04d' % f)
                bpy.ops.render.render(write_still=True)
    else:
        r.filepath = OUT; bpy.ops.render.render(write_still=True)
    print('RENDER %.1fs' % (time.time() - t1))

main()
