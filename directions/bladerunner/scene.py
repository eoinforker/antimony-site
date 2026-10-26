# Blade Runner: a high room at night. Slatted blinds, rain on the glass, a canyon of city light
# below, and across the void the Antimony tower, a vast dark slab whose crown carries the Break.
# Every so often an unseen spinner hangs above the window and its searchlight rakes through the
# blinds and across the floor.
#
# Run headless with Blender 4.5 LTS (always inside the shared render lock):
#   blender -b -P scene.py -- --pass full    --out full.exr    --res 100 --samples 256
#   blender -b -P scene.py -- --pass nohaze  --out nohaze.exr
#   blender -b -P scene.py -- --pass flick   --out flick.exr   (only the flickering practicals)
#   blender -b -P scene.py -- --pass sweep   --out sw_####.exr --frames 1-108 --res 50 --samples 32
# then compose.py builds the loop and the still from those linear passes.
#
# Everything is procedural. The only images are Antimony's own: the meadow poster (a frame of
# directions/poster, exported clean) on a tower screen, and the Break mark, drawn here from its
# exact geometry.
#
# World, in metres: X runs along the window wall, the glass is the plane Y = 0 and the city lies
# out along +Y, Z is up. The room floor is Z = 0, some 260 m above the street (Z = -260).

import bpy, bmesh, math, random, sys, os, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

def arg(name, default):
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return a[a.index(name) + 1] if name in a else default

PASS = arg('--pass', 'full')               # full, nohaze, flick, sweep
OUT = arg('--out', os.path.join(HERE, PASS + '.exr'))
RES = int(arg('--res', '100'))
SAMPLES = int(arg('--samples', '256'))
TL = float(arg('--tl', '1150'))
FRAMES = arg('--frames', '1-108')
POSTER = arg('--poster', os.path.join(HERE, 'assets', 'src', 'poster_tex.png'))
NSW = int(arg('--nsw', '108'))             # frames in the searchlight pass
PNG = arg('--png', '0') == '1'             # quick look drafts straight to AgX PNG
ZG = -260.0
rng = random.Random(11)

bpy.ops.wm.read_factory_settings(use_empty=True)
SC = bpy.context.scene

# ---------------------------------------------------------------- node helpers
class S:
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
    def exp(s, x): return s.m('EXPONENT', x)
    def pow(s, a, b): return s.m('POWER', a, b)
    def clamp(s, x): return s.m('ADD', x, 0.0, clamp=True)
    def sm(s, e0, e1, x):
        n = s.new('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP', clamp=True)
        s.put(n.inputs[0], x); s.put(n.inputs[1], e0); s.put(n.inputs[2], e1)
        s.put(n.inputs[3], 0.0); s.put(n.inputs[4], 1.0)
        return S(s, n.outputs[0])
    def comb(s, x, y, z):
        n = s.new('ShaderNodeCombineXYZ')
        for i, v in enumerate((x, y, z)): s.put(n.inputs[i], v)
        return V(s, n.outputs[0])
    def sep(s, v):
        n = s.new('ShaderNodeSeparateXYZ'); s.put(n.inputs[0], v)
        return S(s, n.outputs[0]), S(s, n.outputs[1]), S(s, n.outputs[2])
    def scale(s, v, f):
        n = s.new('ShaderNodeVectorMath', operation='SCALE'); s.put(n.inputs[0], v); s.put(n.inputs[3], f)
        return V(s, n.outputs[0])
    def mix(s, a, b, f):
        n = s.new('ShaderNodeMix', data_type='RGBA')
        s.put(n.inputs[0], f); s.put(n.inputs[6], a); s.put(n.inputs[7], b)
        return V(s, n.outputs[2])
    def noise(s, vec, scale=1.0, detail=2.0, rough=0.5):
        n = s.new('ShaderNodeTexNoise', noise_dimensions='3D')
        s.put(n.inputs['Vector'], vec); s.put(n.inputs['Scale'], scale)
        s.put(n.inputs['Detail'], detail); s.put(n.inputs['Roughness'], rough)
        return S(s, n.outputs['Fac'])
    def white(s, vec):
        n = s.new('ShaderNodeTexWhiteNoise', noise_dimensions='3D'); s.put(n.inputs['Vector'], vec)
        return S(s, n.outputs['Value']), V(s, n.outputs['Color'])
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
        return n
    def emis(s, col, strength):
        e = s.new('ShaderNodeEmission'); s.put(e.inputs[0], col); s.put(e.inputs[1], strength); return e.outputs[0]
    def add(s, a, b):
        n = s.new('ShaderNodeAddShader'); s.nt.links.new(a, n.inputs[0]); s.nt.links.new(b, n.inputs[1]); return n.outputs[0]
    def mixsh(s, f, a, b):
        n = s.new('ShaderNodeMixShader'); s.put(n.inputs[0], f); s.nt.links.new(a, n.inputs[1]); s.nt.links.new(b, n.inputs[2]); return n.outputs[0]
    def out(s, shader, volume=None):
        o = s.new('ShaderNodeOutputMaterial')
        if shader is not None: s.nt.links.new(shader, o.inputs['Surface'])
        if volume is not None: s.nt.links.new(volume, o.inputs['Volume'])
        return o

def material(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, G(m.node_tree)

def cam_only(g):
    lp = g.new('ShaderNodeLightPath'); return S(g, lp.outputs['Is Camera Ray'])

# which emitters a pass keeps: 'static' (the room and the city), 'flick' (the failing practicals)
def lit(group):
    if PASS in ('full', 'nohaze'): return 1.0
    if PASS == 'flick': return 1.0 if group == 'flick' else 0.0
    return 0.0

# ---------------------------------------------------------------- mesh helpers
class MB:
    def __init__(s): s.v, s.f, s.mi, s.uv, s.col = [], [], [], [], []
    def add(s, verts, faces, mat=0, uvs=None, col=None):
        o = len(s.v); s.v.extend(verts)
        for f in faces: s.f.append([i + o for i in f]); s.mi.append(mat)
        s.uv.extend(uvs if uvs is not None else [(0.0, 0.0)] * len(verts))
        s.col.extend([col or (1, 1, 1, 1)] * len(verts))
    def box(s, x0, x1, y0, y1, z0, z1, mat=0, col=None):
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        s.add(v, f, mat, col=col)
    def quad(s, pts, mat=0, uvs=((0, 0), (1, 0), (1, 1), (0, 1)), col=None):
        s.add(list(pts), [(0, 1, 2, 3)], mat, uvs=list(uvs), col=col)
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

def bevel(ob, w=0.006, seg=2):
    b = ob.modifiers.new('bev', 'BEVEL'); b.width = w; b.segments = seg; b.limit_method = 'ANGLE'
    return ob

def cyl(mb, cx, cy, z0, z1, r0, r1, n=32, mat=0, caps=True):
    v = []
    for z, r in ((z0, r0), (z1, r1)):
        for k in range(n):
            a = 2 * math.pi * k / n; v.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    f = [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
    if caps: f += [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    mb.add(v, f, mat)

def area(name, size, size_y, power, col, loc, rot, spread=None, shape='RECTANGLE'):
    L = bpy.data.lights.new(name, 'AREA'); L.shape = shape; L.size = size; L.size_y = size_y
    L.energy = power; L.color = col
    if spread is not None: L.spread = math.radians(spread)
    o = bpy.data.objects.new(name, L); SC.collection.objects.link(o)
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    o.visible_camera = False; o.visible_glossy = False; o.visible_transmission = False
    return o

def point(name, power, col, loc, radius=0.05):
    L = bpy.data.lights.new(name, 'POINT'); L.energy = power; L.color = col; L.shadow_soft_size = radius
    o = bpy.data.objects.new(name, L); SC.collection.objects.link(o); o.location = loc
    return o

# ---------------------------------------------------------------- the Break, from its exact geometry
def parse_path(d):
    t = d.replace('M', ' ').replace('L', ' ').replace('Z', ' ').split()
    return np.array(list(map(float, t))).reshape(-1, 2)

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

def stone_mask(N=2048):
    ss = 2; n = N * ss
    c = (np.arange(n) + 0.5) / n * 100.0
    X, Y = np.meshgrid(c, c)
    qx, qy = np.abs(X - 50) - 28, np.abs(Y - 50) - 28
    sd = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - 22
    st = (sd < 0) & ~poly_in(X, Y, SEAM) & ~poly_in(X, Y, CAV)
    a = st.astype(np.float32).reshape(N, ss, N, ss).mean((1, 3))
    img = bpy.data.images.new('stone_mask', N, N, alpha=True, float_buffer=False)
    px = np.ones((N, N, 4), np.float32); px[..., 3] = a; px[..., 0] = a; px[..., 1] = a; px[..., 2] = a
    img.pixels.foreach_set(px[::-1].ravel()); img.pack()
    img.colorspace_settings.name = 'Non-Color'
    return img

# ---------------------------------------------------------------- materials: the room
def concrete_mat(name, base=0.2, boards=True, ceiling=False):
    m, g = material(name)
    P, N = g.pos(); x, y, z = g.sep(P)
    n1 = g.noise(P, 0.8, 4.0, 0.62)
    n2 = g.noise(P, 7.0, 3.0, 0.6)
    pits = g.sm(0.72, 0.8, g.noise(P, 38.0, 2.0, 0.5))
    a = base * (0.72 + 0.5 * n1) * (0.9 + 0.2 * n2) * (1.0 - 0.35 * pits)
    h = n2 * 0.0006 - pits * 0.0008
    if boards:
        bz = g.fract((z if not ceiling else x) / 0.24)
        seam = 1.0 - g.sm(0.0, 0.035, g.min(bz, 1.0 - bz))
        _, rc = g.white(g.comb(g.floor((z if not ceiling else x) / 0.24), 3.1, 0.0)); r1, _, _ = g.sep(rc)
        grain = g.noise(g.comb(x * 0.6 if not ceiling else y * 0.6, z * 9.0 if not ceiling else x * 9.0, y * 0.6), 6.0, 2.0, 0.5)
        a = a * (0.9 + 0.2 * r1) * (0.94 + 0.12 * grain) * (1.0 - 0.25 * seam)
        h = h - seam * 0.0012 + grain * 0.0003
    col = g.comb(a * 0.98, a, a * 1.02)
    sh = g.principled(Base_Color=col, Roughness=0.78 - 0.1 * n1, Normal=g.bump(h), Specular_IOR_Level=0.35)
    g.out(sh.outputs[0])
    return m

def floor_mat():
    m, g = material('floor')
    P, N = g.pos(); x, y, z = g.sep(P)
    sx = g.fract(x / 1.2 + 0.5); sy = g.fract(y / 1.2)
    j = g.min(g.min(sx, 1.0 - sx), g.min(sy, 1.0 - sy)) * 1.2
    joint = 1.0 - g.sm(0.0008, 0.0024, j)
    n1 = g.noise(P, 0.9, 4.0, 0.6); n2 = g.noise(P, 14.0, 3.0, 0.6)
    _, cc = g.white(g.comb(g.floor(x / 1.2 + 0.5), g.floor(y / 1.2), 2.0)); c1, _, _ = g.sep(cc)
    a = (0.028 + 0.012 * n1) * (0.85 + 0.3 * c1)
    col = g.mix(g.comb(a, a * 1.02, a * 1.06), (0.008, 0.008, 0.009), joint)
    scuff = g.sm(0.5, 0.7, g.noise(P, 2.2, 5.0, 0.65))
    rough = 0.07 + 0.16 * scuff + 0.05 * n2 + 0.4 * joint
    sh = g.principled(Base_Color=col, Roughness=rough, Normal=g.bump(-joint * 0.001 + n2 * 0.0002), Specular_IOR_Level=0.55)
    g.out(sh.outputs[0])
    return m

def plain(name, col, rough, metal=0.0, sheen=0.0, coat=0.0, spec=0.5, nscale=3.0, var=0.5):
    m, g = material(name)
    P, N = g.pos()
    n1 = g.noise(P, nscale, 4.0, 0.6)
    base = g.scale(col, (1 - var * 0.5) + var * n1)
    sh = g.principled(Base_Color=base, Roughness=rough, Metallic=metal, Sheen_Weight=sheen, Coat_Weight=coat, Specular_IOR_Level=spec)
    g.out(sh.outputs[0])
    return m

def slat_mat():
    m, g = material('slats')
    P, N = g.pos()
    n1 = g.noise(P, 5.0, 3.0, 0.6)
    dust = g.sm(0.45, 0.75, g.noise(P, 1.5, 3.0, 0.6))
    a = 0.42 * (0.85 + 0.2 * n1) * (1.0 - 0.25 * dust)
    sh = g.principled(Base_Color=g.comb(a, a * 0.985, a * 0.955), Roughness=0.36 + 0.2 * dust, Metallic=0.35, Specular_IOR_Level=0.5)
    g.out(sh.outputs[0])
    return m

def glass_mat():
    m, g = material('glass')
    P, N = g.pos()
    smear = g.noise(P, 3.0, 4.0, 0.6)
    tr = g.new('ShaderNodeBsdfTransparent'); g.put(tr.inputs[0], (0.93, 0.95, 0.96))
    gl = g.new('ShaderNodeBsdfGlossy'); g.put(gl.inputs['Roughness'], 0.01 + 0.06 * g.sm(0.55, 0.8, smear))
    fr = g.new('ShaderNodeFresnel'); fr.inputs['IOR'].default_value = 1.52
    k = S(g, fr.outputs[0]) * 0.8
    g.out(g.mixsh(k, tr.outputs[0], gl.outputs[0]))
    return m

def shade_mat():
    # a linen drum shade: the bulb glows through it, warm
    m, g = material('shade')
    P, N = g.pos(); x, y, z = g.sep(P)
    weave = g.noise(P, 90.0, 2.0, 0.5)
    grad = g.sm(0.76, 0.98, z)
    e = g.emis((1.0, 0.56, 0.26), (1.4 + 1.6 * (1.0 - g.abs(grad - 0.5) * 2.0)) * (0.92 + 0.16 * weave) * lit('static'))
    tl = g.new('ShaderNodeBsdfTranslucent'); g.put(tl.inputs[0], (0.85, 0.7, 0.55))
    g.out(g.add(e, tl.outputs[0]))
    return m

# ---------------------------------------------------------------- materials: the city
def city_mat():
    m, g = material('city')
    P, N = g.pos(); x, y, z = g.sep(P); nx, ny, nz = g.sep(N)
    sc, _ = g.attr('col'); seed, kind, dens = g.sep(sc)
    face_y = g.sm(0.5, 0.6, g.abs(ny))
    u = x * face_y + y * (1.0 - face_y)
    fh = 3.3 + kind * 0.6; cw = 1.5 + seed * 0.9
    cu = g.floor(u / cw); cv = g.floor(z / fh)
    fu = g.fract(u / cw); fv = g.fract(z / fh)
    _, rc = g.white(g.comb(cu + seed * 97.0, cv, face_y * 7.0 + seed * 13.0)); r1, r2, r3 = g.sep(rc)
    _, rb = g.white(g.comb(g.floor(cu / 6.0) + seed * 31.0, g.floor(cv / 3.0), seed)); b1, b2, _ = g.sep(rb)
    # windows lit in loose clusters, as offices and flats are
    p_on = dens * (0.35 + 1.3 * b1)
    on = g.m('LESS_THAN', r1, p_on)
    win = g.sm(0.12, 0.18, fu) * (1.0 - g.sm(0.82, 0.88, fu)) * g.sm(0.18, 0.26, fv) * (1.0 - g.sm(0.78, 0.86, fv))
    warm = (1.0, 0.5, 0.2); cool = (0.62, 0.78, 1.0); white = (1.0, 0.82, 0.62)
    wc = g.mix(g.mix(warm, white, g.sm(0.4, 0.6, r2)), cool, g.sm(0.78, 0.86, r2 + 0.3 * b2))
    inten = (0.25 + 1.4 * r3 * r3) * on * win
    # some towers carry continuous floor bands instead of windows, the 2049 way
    band = g.m('GREATER_THAN', kind, 0.82) * (1.0 - g.sm(0.06, 0.1, g.fract(z / (fh * 4.0)))) * g.sm(0.3, 0.6, b2)
    inten = inten + band * 0.7
    roof = g.sm(0.6, 0.7, nz)
    inten = inten * (1.0 - roof) * (1.0 - g.sm(-200.0, -258.0, z) * 0.0)
    e = g.emis(wc, inten * 5.0 * lit('static'))
    fac = g.noise(P, 0.05, 3.0, 0.6)
    a = 0.02 + 0.02 * fac
    sh = g.principled(Base_Color=g.comb(a, a, a * 1.05), Roughness=0.28 + 0.3 * fac, Metallic=0.2, Specular_IOR_Level=0.6)
    g.out(g.add(sh.outputs[0], e))
    m.cycles.emission_sampling = 'NONE'
    return m

def monolith_mat():
    # board marked concrete at the scale of a building: panels, deep joints, rain streaks,
    # and a handful of warm slots where people still work late
    m, g = material('monolith')
    P, N = g.pos(); x, y, z = g.sep(P); nx, ny, nz = g.sep(N)
    face_y = g.sm(0.5, 0.6, g.abs(ny))
    u = x * face_y + y * (1.0 - face_y)
    pu = g.fract(u / 7.2); pv = g.fract(z / 4.8)
    j = g.min(g.min(pu, 1.0 - pu) * 7.2, g.min(pv, 1.0 - pv) * 4.8)
    joint = 1.0 - g.sm(0.05, 0.14, j)
    _, rc = g.white(g.comb(g.floor(u / 7.2), g.floor(z / 4.8), 5.0)); r1, r2, r3 = g.sep(rc)
    streak = g.noise(g.comb(u * 0.35, z * 0.012, 0.0), 1.0, 4.0, 0.6)
    a = 0.022 * (0.8 + 0.35 * r1) * (0.75 + 0.5 * streak) * (1.0 - 0.6 * joint)
    rough = 0.5 - 0.3 * g.sm(0.5, 0.75, streak)
    # slots: thin horizontal openings, very few lit, warm and dim
    slot = g.sm(0.42, 0.46, pv) * (1.0 - g.sm(0.54, 0.58, pv)) * g.m('LESS_THAN', g.fract(z / 38.4), 0.12)
    _, rs = g.white(g.comb(g.floor(u / 7.2), g.floor(z / 38.4), 9.0)); s1, s2, _ = g.sep(rs)
    slit = slot * g.m('LESS_THAN', s1, 0.18) * g.sm(0.1, 0.2, pu) * (1.0 - g.sm(0.8, 0.9, pu)) * face_y
    e = g.emis(g.mix((1.0, 0.52, 0.22), (1.0, 0.7, 0.45), s2), slit * (1.0 + 2.0 * s2) * 1.6 * lit('static'))
    sh = g.principled(Base_Color=g.comb(a, a, a * 1.04), Roughness=rough, Normal=g.bump(-joint * 0.06, 1.0, 1.0), Specular_IOR_Level=0.5)
    g.out(g.add(sh.outputs[0], e))
    m.cycles.emission_sampling = 'NONE'
    return m

def stone_sign_mat(img):
    m, g = material('mark_stone')
    t = g.new('ShaderNodeTexImage', image=img, interpolation='Cubic', extension='CLIP')
    g.put(t.inputs[0], g.uv())
    P, N = g.pos()
    n1 = g.noise(P, 0.25, 4.0, 0.6); n2 = g.noise(P, 3.0, 3.0, 0.6)
    a = 0.07 * (0.85 + 0.3 * n1) * (0.92 + 0.16 * n2)
    sh = g.principled(Base_Color=g.comb(a, a * 0.98, a * 0.96), Roughness=0.2 + 0.12 * n2, Coat_Weight=0.5, Coat_Roughness=0.08, Specular_IOR_Level=0.6, Normal=g.bump(n2 * 0.01))
    tr = g.new('ShaderNodeBsdfTransparent')
    g.out(g.mixsh(S(g, t.outputs['Alpha']), tr.outputs[0], sh.outputs[0]))
    m.blend_method = 'HASHED' if hasattr(m, 'blend_method') else None
    return m

SKY = (0x94 / 255.0, 0xE6 / 255.0, 0xFF / 255.0)
def srgb2lin(c): return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)
SKYL = srgb2lin(SKY)

def gem_mat(name, facet=False, E=1.1):
    # the crystal holds light: deeper at its foot, clearer at its crown, the right facet lifted by white
    m, g = material(name)
    P, N = g.pos(); x, y, z = g.sep(P)
    t = g.sm(MARK['z'] - MARK['s'] * 0.3, MARK['z'] + MARK['s'] * 0.3, z)
    deep = (SKYL[0] * 0.55, SKYL[1] * 0.78, SKYL[2])
    c = g.mix(deep, SKYL, t)
    if facet: c = g.mix(c, (1.0, 1.0, 1.0), 0.28)
    shimmer = g.noise(P, 0.4, 3.0, 0.55)
    g.out(g.emis(c, E * (0.9 + 0.2 * shimmer) * lit('static')))
    return m

def poster_mat(img):
    # a building sized screen: the meadow, ghostly, with the faint pitch of its emitters
    m, g = material('screen')
    t = g.new('ShaderNodeTexImage', image=img, interpolation='Cubic', extension='EXTEND')
    uv = g.uv(); g.put(t.inputs[0], uv)
    u, v, _ = g.sep(uv)
    pitch = 0.9 + 0.1 * g.sm(0.2, 0.5, g.abs(g.fract(v * 420.0) - 0.5) * 2.0)
    edge = g.min(g.min(u, 1.0 - u) * 1.5, g.min(v, 1.0 - v))
    fall = 0.8 + 0.2 * g.sm(0.0, 0.05, edge)
    g.out(g.emis(V(g, t.outputs[0]), 0.6 * pitch * fall * lit('static')))
    m.cycles.emission_sampling = 'NONE'
    return m

def adpanel_mat(name, c0, c1, strength, group):
    # an advertising wall that shows nothing legible: soft fields of colour, slowly banded
    m, g = material(name)
    uv = g.uv(); u, v, _ = g.sep(uv)
    n1 = g.noise(g.comb(u * 2.0, v * 0.6, 0.0), 1.4, 3.0, 0.55)
    c = g.mix(c0, c1, g.sm(0.3, 0.7, n1 + (v - 0.5) * 0.6))
    edge = g.min(g.min(u, 1.0 - u), g.min(v, 1.0 - v))
    fall = g.sm(0.0, 0.04, edge)
    g.out(g.emis(c, strength * (0.75 + 0.5 * n1) * fall * lit(group)))
    m.cycles.emission_sampling = 'NONE'
    return m

def haze_mat(name, inside):
    m, g = material(name)
    vol = g.new('ShaderNodeVolumePrincipled')
    vol.inputs['Anisotropy'].default_value = 0.45 if inside else 0.55
    vol.inputs['Color'].default_value = (0.92, 0.95, 1.0, 1)
    cam = cam_only(g)
    P, _ = g.pos(); x, y, z = g.sep(P)
    if inside:
        n1 = g.noise(P, 0.45, 2.0, 0.5)
        d = 0.024 * (0.55 + 0.9 * g.sm(0.3, 0.7, n1)) * (0.8 + 0.4 * g.sm(0.0, 3.0, z))
    else:
        n1 = g.noise(g.scale(P, 1.0), 0.012, 2.0, 0.5)
        low = g.exp((ZG - z) / 140.0)
        near = g.exp(-g.max(y, 0.0) / 30.0)
        d = (0.0005 + 0.006 * low) * (0.6 + 0.8 * n1)
        if PASS == 'sweep':
            # rain mist close to the glass, which only the searchlight's beam shows up
            d = d + 0.003 * near * g.sm(0.3, 0.7, g.noise(P, 0.08, 2.0, 0.5))
    g.put(vol.inputs['Density'], d * cam)
    g.out(None, vol.outputs[0])
    return m

# ---------------------------------------------------------------- the room
WX0, WX1, WZ0, WZ1 = -3.6, 3.6, 0.22, 3.0     # the glazed opening
MUL = (-1.2, 1.2); MW = 0.22                   # concrete fins between the bays
RX, RY, RZ = 4.6, -8.0, 3.3
BAYS = [(WX0, MUL[0] - MW / 2), (MUL[0] + MW / 2, MUL[1] - MW / 2), (MUL[1] + MW / 2, WX1)]
BLIND_FOOT = [2.3, 1.5, 1.9]                   # where each blind has been let down to

def build_room(m_wall, m_ceil, m_floor, m_frame, m_glass):
    mb = MB()
    T = 0.3
    # floor and ceiling
    mb.box(-RX - T, RX + T, RY, 0.45, -T, 0.0, 1)
    mb.box(-RX - T, RX + T, RY, 0.45, RZ, RZ + T, 2)
    # side walls and the back wall behind the camera
    mb.box(-RX - T, -RX, RY, 0.45, 0.0, RZ, 0)
    mb.box(RX, RX + T, RY, 0.45, 0.0, RZ, 0)
    mb.box(-RX, RX, RY - T, RY, 0.0, RZ, 0)
    # the window wall: piers either side, an upstand below, a deep beam above
    mb.box(-RX, WX0, 0.0, 0.45, 0.0, RZ, 0)
    mb.box(WX1, RX, 0.0, 0.45, 0.0, RZ, 0)
    mb.box(WX0, WX1, 0.0, 0.45, 0.0, WZ0, 0)
    mb.box(WX0, WX1, -0.32, 0.45, WZ1, RZ, 0)
    # fins
    for xm in MUL: mb.box(xm - MW / 2, xm + MW / 2, -0.38, 0.45, WZ0, WZ1, 0)
    room = mb.build('room', [m_wall, m_floor, m_ceil])
    bevel(room, 0.01, 2)
    # frames and glass, set back in the reveal
    fb = MB(); gb = MB()
    for (a, b) in BAYS:
        F = 0.045
        fb.box(a, b, 0.02, 0.09, WZ0, WZ0 + F); fb.box(a, b, 0.02, 0.09, WZ1 - F, WZ1)
        fb.box(a, a + F, 0.02, 0.09, WZ0, WZ1); fb.box(b - F, b, 0.02, 0.09, WZ0, WZ1)
        gb.quad([(a, 0.05, WZ0), (b, 0.05, WZ0), (b, 0.05, WZ1), (a, 0.05, WZ1)])
    bevel(fb.build('frames', [m_frame]), 0.004)
    gl = gb.build('glass', [m_glass], uv=True)
    return room, gl

def build_blinds(m_slat, m_cord, m_rail):
    sb = MB(); cb = MB(); rb = MB()
    W, TH, SP, TILT = 0.034, 0.0018, 0.029, math.radians(38)
    ca, sa = math.cos(TILT), math.sin(TILT)
    for k, (a, b) in enumerate(BAYS):
        a, b = a + 0.03, b - 0.03
        yc = -0.11
        rb.box(a - 0.01, b + 0.01, yc - 0.035, yc + 0.035, WZ1 - 0.07, WZ1 - 0.015)
        z = WZ1 - 0.09
        foot = BLIND_FOOT[k]
        while z > foot:
            # a slat: its room side edge lower, so light from above and outside comes down through
            hw = W / 2
            p = [(yc - hw * ca, z - hw * sa), (yc + hw * ca, z + hw * sa)]
            nrm = (-sa * TH / 2, ca * TH / 2)
            sag = 0.002
            n = 12
            verts = []
            for i in range(n + 1):
                x = a + (b - a) * i / n
                s_ = sag * math.sin(math.pi * i / n)
                for (py, pz) in p:
                    for sg in (-1, 1):
                        verts.append((x, py + nrm[0] * sg, pz + nrm[1] * sg - s_))
            faces = []
            for i in range(n):
                o, q = i * 4, (i + 1) * 4
                faces += [(o + 0, q + 0, q + 2, o + 2), (o + 1, o + 3, q + 3, q + 1), (o + 0, o + 1, q + 1, q + 0), (o + 2, q + 2, q + 3, o + 3)]
            faces += [(0, 2, 3, 1), (n * 4, n * 4 + 1, n * 4 + 3, n * 4 + 2)]
            sb.add(verts, faces, 0)
            z -= SP
        rb.box(a, b, yc - 0.022, yc + 0.022, z - 0.012, z + 0.006)
        # ladder cords and the lift cords
        for xc in (a + (b - a) * 0.17, a + (b - a) * 0.83):
            for dy in (-0.018, 0.018):
                cb.box(xc - 0.0012, xc + 0.0012, yc + dy - 0.0008, yc + dy + 0.0008, z, WZ1 - 0.07)
        if k == 2:
            cb.box(b - 0.06, b - 0.057, yc - 0.03, yc - 0.027, 1.05, WZ1 - 0.07)
            cyl(cb, b - 0.0585, yc - 0.0285, 1.0, 1.06, 0.006, 0.004, 10)
    sb.build('slats', [m_slat], smooth=True)
    cb.build('cords', [m_cord])
    bevel(rb.build('rails', [m_rail]), 0.003)

def build_props(m_wood, m_leather, m_metal, m_shade):
    # a low stone side table with a drum lamp, and one lounge chair turned to the window
    tb = MB()
    tx, ty = -2.75, -1.05
    tb.box(tx - 0.26, tx + 0.26, ty - 0.26, ty + 0.26, 0.0, 0.5)
    t = bevel(tb.build('table', [m_wood]), 0.012, 3)
    lb = MB()
    cyl(lb, tx + 0.02, ty - 0.02, 0.5, 0.515, 0.08, 0.075, 32)
    cyl(lb, tx + 0.02, ty - 0.02, 0.515, 0.8, 0.008, 0.008, 12)
    lb.build('lamp_stem', [m_metal], smooth=True)
    sh = MB(); cyl(sh, tx + 0.02, ty - 0.02, 0.76, 0.98, 0.19, 0.17, 48, caps=False)
    so = sh.build('lamp_shade', [m_shade], smooth=True)
    so.modifiers.new('sol', 'SOLIDIFY').thickness = 0.004
    if lit('static'):
        point('bulb', 32.0, (1.0, 0.6, 0.3), (tx + 0.02, ty - 0.02, 0.86), 0.03)

# ---------------------------------------------------------------- the city
MONO = dict(x0=8.0, x1=102.0, y0=212.0, y1=290.0, top=40.0)
MARK = dict(x=58.0, z=-3.0, s=34.0)
SCREEN = dict(x=-152.0, y=380.0, w=60.0, z0=-64.0)

def tower_ok(x, y, hw, hd):
    # keep the void clear, and keep the monolith and the screen tower free
    if y - hd < 95: return False
    if y < 330 and abs(x - 20) < 330 + (y - 95) * 0.0 and not (y > 200 and x > 160): return False
    if MONO['x0'] - 30 < x + hw and x - hw < MONO['x1'] + 30 and MONO['y0'] - 40 < y + hd and y - hd < MONO['y1'] + 25: return False
    if abs(x - SCREEN['x']) < 40 and y - hd < SCREEN['y'] + 20 and y + hd > SCREEN['y'] - 40: return False
    if y < SCREEN['y'] + 30 and abs((x + math.copysign(hw, SCREEN['x'] - x)) / (y + 6.4) - SCREEN['x'] / (SCREEN['y'] + 6.4)) < (SCREEN['w'] / 2 + 8) / SCREEN['y']: return False
    return True

def build_city(m_city):
    mb = MB()
    count = 0
    for gy in np.arange(120, 2400, 58):
        for gx in np.arange(-2200, 2200, 58):
            x = gx + rng.uniform(-14, 14); y = gy + rng.uniform(-14, 14)
            hw = rng.uniform(11, 23); hd = rng.uniform(11, 23)
            if not tower_ok(x, y, hw, hd): continue
            # most towers stop below us; a few go far above
            # a canyon: low in the middle, walls of towers rising either side, taller with distance
            off = abs(x - (-20.0 + 0.08 * y)) - (70.0 + 0.12 * y)
            h = 150.0 + rng.uniform(-40, 90) + max(0.0, off) * rng.uniform(0.6, 1.5) + y * 0.04
            if rng.random() < 0.05: h += rng.uniform(80, 200)
            h = min(h, 520.0)
            seed = rng.random(); kind = rng.random(); dens = rng.uniform(0.05, 0.32)
            col = (seed, kind, dens, 1.0)
            top = ZG + h
            mb.box(x - hw, x + hw, y - hd, y + hd, ZG, top, 0, col)
            if rng.random() < 0.35:       # a setback crown
                f = rng.uniform(0.55, 0.8)
                mb.box(x - hw * f, x + hw * f, y - hd * f, y + hd * f, top, top + rng.uniform(12, 50), 0, col)
            count += 1
    ob = mb.build('city', [m_city], col=True)
    print('towers', count)
    return ob

def build_monolith(m_mono, m_stone_sign, m_gem, m_facet):
    mb = MB()
    x0, x1, y0, y1, top = MONO['x0'], MONO['x1'], MONO['y0'], MONO['y1'], MONO['top']
    b = 16.0     # it widens toward its foot, a slow batter over three hundred metres
    v = [(x0 - b, y0 - b * 0.6, ZG), (x1 + b, y0 - b * 0.6, ZG), (x1 + b, y1 + b, ZG), (x0 - b, y1 + b, ZG),
         (x0, y0, top), (x1, y0, top), (x1, y1, top), (x0, y1, top)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    mb.add(v, f, 0)
    # a thin parapet line and a recessed crown band, which give the mass its edge against the sky
    mb.box(x0 - 0.6, x1 + 0.6, y0 - 0.6, y1 + 0.6, top - 1.6, top + 1.2, 0)
    ob = mb.build('monolith', [m_mono])
    # the Break, on the crown face: the stone tile as a panel proud of the face, the crystal in its break
    S_ = MARK['s']; cx, cz = MARK['x'], MARK['z']
    # the face is battered; find its Y at the mark's height
    t = (cz - ZG) / (top - ZG); yf = (y0 - b * 0.6) * (1 - t) + y0 * t - 0.5
    def fy(z): tt = (z - ZG) / (top - ZG); return (y0 - b * 0.6) * (1 - tt) + y0 * tt - 0.4
    def mp(px, py, dy=0.0):
        z = cz - (py - 50) / 100 * S_
        return (cx + (px - 50) / 100 * S_, fy(z) - dy, z)
    sb = MB()
    sb.quad([mp(0, 100), mp(100, 100), mp(100, 0), mp(0, 0)])
    sb.build('mark_stone', [m_stone_sign], uv=True)
    gb = MB(); gb.add([mp(px, py, 0.7) for (px, py) in GEM], [tuple(range(len(GEM)))[::-1]], 0)
    gb.build('mark_gem', [m_gem])
    fb = MB(); fb.add([mp(px, py, 0.74) for (px, py) in FACET], [tuple(range(len(FACET)))[::-1]], 0)
    rb = MB(); rb.quad([mp(-1, 101, -0.25), mp(101, 101, -0.25), mp(101, -1, -0.25), mp(-1, -1, -0.25)])
    rb.build('mark_recess', [plain('recess', (0.003, 0.003, 0.004), 0.7)])
    fb.build('mark_facet', [m_facet])
    return ob, yf

def build_screen(img, m_city):
    W = SCREEN['w']; H = W * 1.5; x, y, z0 = SCREEN['x'], SCREEN['y'], SCREEN['z0']
    pm = MB()
    pm.quad([(x - W / 2, y - 0.3, z0), (x + W / 2, y - 0.3, z0), (x + W / 2, y - 0.3, z0 + H), (x - W / 2, y - 0.3, z0 + H)])
    pm.build('screen', [poster_mat(img)], uv=True)
    # the tower that carries it
    tb = MB(); tb.box(x - 24, x + 24, y, y + 40, ZG, z0 + H + 22, 0, (0.4, 0.3, 0.04, 1))
    tb.build('screen_tower', [m_city], col=True)
    return x, y, z0, W, H

ADS = [
    # x, y, z0, w, h, colour a, colour b, strength, group, facing angle
    (-290.0, 430.0, -120.0, 34.0, 52.0, (0.03, 0.09, 1.0), (0.12, 0.2, 0.9), 3.2, 'static'),
    (230.0, 520.0, -150.0, 60.0, 26.0, (1.0, 0.62, 0.3), (1.0, 0.8, 0.55), 2.2, 'flick'),
    (-150.0, 760.0, -60.0, 26.0, 70.0, (0.9, 0.85, 0.8), (0.4, 0.55, 1.0), 1.8, 'static'),
    (420.0, 900.0, -40.0, 40.0, 40.0, (0.05, 0.1, 0.9), (0.6, 0.7, 1.0), 2.4, 'flick'),
]

def build_ads(m_city):
    for i, (x, y, z0, w, h, ca, cb, st, grp) in enumerate(ADS):
        pm = MB(); pm.quad([(x - w / 2, y - 0.3, z0), (x + w / 2, y - 0.3, z0), (x + w / 2, y - 0.3, z0 + h), (x - w / 2, y - 0.3, z0 + h)])
        pm.build('ad%d' % i, [adpanel_mat('ad%d' % i, ca, cb, st, grp)], uv=True)
        tb = MB(); tb.box(x - w / 2 - 6, x + w / 2 + 6, y, y + 36, ZG, z0 + h + rng.uniform(20, 90), 0, (rng.random(), 0.5, 0.12, 1))
        tb.build('ad_tower%d' % i, [m_city], col=True)
        if lit(grp):
            c = tuple(0.5 * (a + b) for a, b in zip(ca, cb))
            area('ad_light%d' % i, w, h, st * w * h * 9.0, c, (x, y - 2.0, z0 + h / 2), (90, 0, 180), spread=150)

# ---------------------------------------------------------------- the searchlight
def sweep_state(f):
    # f runs 1 to NSW: the spinner drifts in from the right, hangs, and slides away left
    s = (f - 1) / max(1, NSW - 1)
    e = s * s * (3 - 2 * s)
    sx = 30.0 - 60.0 * (0.5 * s + 0.5 * e)
    sy = 15.0 + 2.5 * math.sin(math.pi * s)
    sz = 15.5 + 0.8 * math.sin(2 * math.pi * s * 0.7)
    tx = 4.4 - 8.8 * (0.35 * s + 0.65 * e) + 0.25 * math.sin(s * 9.0)
    ty = -2.2 - 0.9 * math.sin(math.pi * s)
    tz = 0.4
    # the lamp opens up and dies away at the ends
    k = min(1.0, s / 0.12, (1 - s) / 0.14)
    k = max(0.0, k) ** 1.5
    return (sx, sy, sz), (tx, ty, tz), k

def build_searchlight():
    L = bpy.data.lights.new('searchlight', 'SPOT')
    L.spot_size = math.radians(16); L.spot_blend = 0.45; L.shadow_soft_size = 0.035
    L.color = (0.86, 0.92, 1.0)
    o = bpy.data.objects.new('searchlight', L); SC.collection.objects.link(o)
    tgt = bpy.data.objects.new('sl_target', None); SC.collection.objects.link(tgt)
    c = o.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    for f in range(1, NSW + 1):
        p, t, k = sweep_state(f)
        o.location = p; tgt.location = t; L.energy = 60000.0 * k
        o.keyframe_insert('location', frame=f); tgt.keyframe_insert('location', frame=f); L.keyframe_insert('energy', frame=f)
    return o

# ---------------------------------------------------------------- assemble
def main():
    t0 = time.time()
    m_wall = concrete_mat('walls', 0.17)
    m_ceil = concrete_mat('ceiling', 0.2, ceiling=True)
    m_floor = floor_mat()
    m_frame = plain('frame', (0.02, 0.021, 0.023), 0.35, metal=0.9)
    m_glass = glass_mat()
    m_slat = slat_mat()
    m_cord = plain('cord', (0.3, 0.29, 0.27), 0.8)
    m_rail = plain('rail', (0.3, 0.3, 0.29), 0.35, metal=0.6)
    m_wood = plain('table_stone', (0.05, 0.048, 0.046), 0.35, coat=0.3, nscale=6)
    m_leather = plain('leather', (0.03, 0.02, 0.016), 0.42, sheen=0.2, coat=0.15, nscale=8)
    m_metal = plain('brass', (0.3, 0.22, 0.12), 0.3, metal=1.0)
    m_shade = shade_mat()
    build_room(m_wall, m_ceil, m_floor, m_frame, m_glass)
    build_blinds(m_slat, m_cord, m_rail)
    build_props(m_wood, m_leather, m_metal, m_shade)
    m_city = city_mat()
    build_city(m_city)
    img = stone_mask()
    ob, yf = build_monolith(monolith_mat(), stone_sign_mat(img), gem_mat('gem'), gem_mat('facet', True))
    pimg = bpy.data.images.load(POSTER)
    sx, sy, sz0, sw, sh = build_screen(pimg, m_city)
    build_ads(m_city)

    st = lit('static')
    if st:
        # the city's glow, coming up out of the canyon: sodium, wide, from far below
        for (x, y, p, c) in ((-320, 560, 1.0, 0), (260, 620, 0.8, 0), (-40, 760, 1.3, 1), (520, 700, 0.9, 0), (-600, 1000, 1.0, 0), (300, 1200, 1.0, 0), (60, 1550, 1.6, 1), (-900, 1600, 1.2, 0)):
            col = (1.0, 0.42, 0.13) if c else (0.22, 0.4, 1.0)
            area('street', 300, 300, 1.4e6 * p, col, (x, y, ZG + 8), (180, 0, 0), spread=170)
        # the night above: a cold, wide fill from the cloud deck
        area('sky_fill', 1800, 1800, 0.7e6, (0.28, 0.4, 1.0), (0, 600, 420), (0, 0, 0), spread=180)
        # the meadow screen throws its light into the rain
        area('screen_light', sw, sh, 1.2e5, (0.72, 0.88, 0.8), (sx, sy - 1.5, sz0 + sh / 2), (90, 0, 180), spread=160)
        # the crystal's light, and a low grazing wash that lifts the stone tile off the tower face
        S_ = MARK['s']
        area('gem_glow', S_ * 0.3, S_ * 0.5, 2.5e3, SKYL, (MARK['x'], yf - 1.0, MARK['z']), (90, 0, 180), spread=170)
        area('stone_front', S_ * 0.8, S_ * 0.8, 5.0e3, (0.72, 0.84, 1.0), (MARK['x'], yf - 22.0, MARK['z'] + 4.0), (90, 0, 0), spread=22)
        area('stone_wash', S_ * 1.1, 1.0, 4.0e3, (0.75, 0.86, 1.0), (MARK['x'], yf - 3.0, MARK['z'] - S_ * 0.58), (165, 0, 0), spread=40)
        # the monolith's foot is washed by the city below: a warm light climbing its face and dying out
        L = bpy.data.lights.new('mono_up', 'SPOT'); L.spot_size = math.radians(24); L.spot_blend = 0.8; L.shadow_soft_size = 6.0
        L.energy = 7.0e5; L.color = (1.0, 0.5, 0.2)
        o = bpy.data.objects.new('mono_up', L); SC.collection.objects.link(o); o.location = (40.0, 140.0, ZG + 20)
        tg = bpy.data.objects.new('mono_tgt', None); SC.collection.objects.link(tg); tg.location = (40.0, 205.0, -40.0)
        c = o.constraints.new('TRACK_TO'); c.target = tg; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
        # the room's light from outside: the cold night through the glass, the warm canyon from below
        area('night_in', 7.4, 2.8, 16.0, (0.42, 0.55, 1.0), (0.0, 2.2, 1.7), (-90, 0, 0), spread=100)
        area('canyon_up', 7.4, 3.0, 22.0, (1.0, 0.62, 0.4), (0.0, 3.2, -2.0), (-125, 0, 0), spread=70)
    if PASS == 'sweep':
        build_searchlight()
    if st:
        # a vast advertising wall off frame, high and to the left, throws its cold light in across the floor
        L = bpy.data.lights.new('ad_spot', 'SPOT'); L.spot_size = math.radians(7.5); L.spot_blend = 0.6; L.shadow_soft_size = 0.4
        L.energy = 5.5e5; L.color = (0.42, 0.58, 1.0)
        o = bpy.data.objects.new('ad_spot', L); SC.collection.objects.link(o); o.location = (-58.0, 70.0, 46.0)
        tg = bpy.data.objects.new('ad_tgt', None); SC.collection.objects.link(tg); tg.location = (-0.2, -2.6, 0.0)
        c = o.constraints.new('TRACK_TO'); c.target = tg; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'

    # haze inside the room and out over the city
    if PASS != 'nohaze':
        hb = MB(); hb.box(-RX + 0.01, RX - 0.01, RY + 0.01, -0.02, 0.01, RZ - 0.01, 0)
        hz = hb.build('haze_in', [haze_mat('haze_in', True)])
        hb = MB()
        if PASS == 'sweep': hb.box(-90, 90, 0.7, 90, -60, 60, 0)        # the beam only lives near the window
        else: hb.box(-2600, 2600, 0.7, 2600, ZG, 520, 0)
        hb.build('haze_out', [haze_mat('haze_out', False)])

    # world: a nearly black night with the faintest cold lift toward the horizon
    wm = bpy.data.worlds.new('w'); SC.world = wm; wm.use_nodes = True; nt = wm.node_tree; nt.nodes.clear(); g = G(nt)
    bg = g.new('ShaderNodeBackground'); o = g.new('ShaderNodeOutputWorld'); nt.links.new(bg.outputs[0], o.inputs[0])
    gp = g.new('ShaderNodeNewGeometry'); _, _, iz = g.sep(g.scale(V(g, gp.outputs['Incoming']), -1.0))
    sky = g.mix((0.010, 0.016, 0.035), (0.0015, 0.0025, 0.007), g.sm(-0.05, 0.5, iz))
    g.put(bg.inputs[0], sky); bg.inputs[1].default_value = 1.0 * st

    # camera: standing well back in the room, level, looking out
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); SC.collection.objects.link(cam); SC.camera = cam
    cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24.0; cd.lens = 12.0 / math.tan(math.radians(25.0)); cd.shift_y = 0.0
    cd.clip_start = 0.1; cd.clip_end = 5000
    cam.location = (0.25, -6.4, 1.38); cam.rotation_euler = (math.radians(90), 0, 0)
    cd.dof.use_dof = True; cd.dof.focus_distance = 40.0; cd.dof.aperture_fstop = 5.6

    r = SC.render; r.engine = 'CYCLES'; r.resolution_x, r.resolution_y = 1920, 1200; r.resolution_percentage = RES
    r.threads_mode = 'FIXED'; r.threads = 4
    c = SC.cycles; c.device = 'CPU'; c.samples = SAMPLES; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.015
    c.adaptive_min_samples = min(32, SAMPLES); c.time_limit = TL
    c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'; c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; c.denoising_prefilter = 'ACCURATE'
    c.max_bounces = 8; c.diffuse_bounces = 3; c.glossy_bounces = 3; c.transmission_bounces = 4; c.volume_bounces = 0; c.transparent_max_bounces = 10
    c.sample_clamp_indirect = 6.0; c.blur_glossy = 0.8; c.caustics_refractive = False; c.caustics_reflective = False
    c.volume_step_rate = 6.0 if PASS != 'sweep' else 8.0; c.volume_max_steps = 192
    c.use_light_tree = True; c.seed = 5
    vs = SC.view_settings; vs.view_transform = 'AgX'; vs.exposure = 0.0
    if PNG:
        r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGB'; r.image_settings.color_depth = '8'
    else:
        r.image_settings.file_format = 'OPEN_EXR'; r.image_settings.color_depth = '32'; r.image_settings.exr_codec = 'ZIP'; r.image_settings.color_mode = 'RGB'
    print('BUILD %.1fs' % (time.time() - t0)); sys.stdout.flush()
    t1 = time.time()
    if PASS == 'sweep':
        a, b = map(int, FRAMES.split('-'))
        ev = int(arg('--every', '1'))
        fl = list(range(a, b + 1, ev))
        if fl[-1] != b: fl.append(b)
        for f in fl:
            if os.path.exists(OUT.replace('####', '%04d' % f)): continue
            SC.frame_set(f)
            r.filepath = OUT.replace('####', '%04d' % f)
            tf = time.time(); bpy.ops.render.render(write_still=True)
            print('frame', f, '%.1fs' % (time.time() - tf)); sys.stdout.flush()
    else:
        if PASS == 'sweep1':
            pass
        r.filepath = OUT; bpy.ops.render.render(write_still=True)
    print('RENDER %.1fs' % (time.time() - t1))

main()
