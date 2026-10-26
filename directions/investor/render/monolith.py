# Investor hero, path traced: the Break as a stone monolith standing in a still lake at first light.
# The sun rises directly behind the crystal, so the first light of the day comes through the break.
#
# Run headless with Blender 4.5 LTS:
#   blender -b -P monolith.py -- --pass scene --out <dir> --res 25 --samples 32
#   blender -b -P monolith.py -- --pass mist  --out <dir> --res 50 --samples 64
# The scene pass writes beauty.exr (denoised), sun.exr (the sun's light group, denoised),
# crystal.exr and water.exr (anti-aliased masks). The mist pass writes mist.exr: the low mist
# on the water alone, everything else a holdout, so the loop can drift it over the still.
#
# World, in metres: the camera stands at the origin, 1.7 m above the water, looking along +Y.
# The water is the plane Z = 0. The monolith stands 450 m out; its tile is 60 m square, 14 m deep.

import bpy, math, sys, os, time
import numpy as np
from mathutils import Vector

def arg(name, default):
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return a[a.index(name) + 1] if name in a else default

PASS = arg('--pass', 'scene')
OUT = arg('--out', '/tmp/inv')
RES = int(arg('--res', '25'))
SAMPLES = int(arg('--samples', '32'))
TL = float(arg('--tl', '0'))
SUNAT = arg('--sun', 'side')           # side, crystal, seam
SUN_AZ = float(arg('--az', '112'))      # degrees from straight ahead, negative is left (behind the camera past 90)
SUN_EL = float(arg('--el', '3.0'))
FIGURE = arg('--figure', '1') == '1'
W0, H0 = 2560, 1440

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
    def abs(s, x): return s.m('ABSOLUTE', x)
    def max(s, a, b): return s.m('MAXIMUM', a, b)
    def min(s, a, b): return s.m('MINIMUM', a, b)
    def pow(s, a, b): return s.m('POWER', a, b)
    def exp(s, x): return s.m('EXPONENT', x)
    def sin(s, x): return s.m('SINE', x)
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
    def vm(s, op, a, b=None, sc=None):
        n = s.new('ShaderNodeVectorMath', operation=op)
        s.put(n.inputs[0], a)
        if b is not None: s.put(n.inputs[1], b)
        if sc is not None: s.put(n.inputs[3], sc)
        sc_out = op in ('LENGTH', 'DOT_PRODUCT', 'DISTANCE')
        return (S if sc_out else V)(s, n.outputs[1] if sc_out else n.outputs[0])
    def scale(s, v, f): return s.vm('SCALE', v, sc=f)
    def mix(s, a, b, f):
        n = s.new('ShaderNodeMix', data_type='RGBA')
        s.put(n.inputs[0], f); s.put(n.inputs[6], a); s.put(n.inputs[7], b)
        return V(s, n.outputs[2])
    def cmul(s, a, f):
        n = s.new('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
        s.put(n.inputs[0], 1.0); s.put(n.inputs[6], a); s.put(n.inputs[7], f)
        return V(s, n.outputs[2])
    def noise(s, vec, scale=1.0, detail=2.0, rough=0.5, dist=0.0, lac=2.0):
        n = s.new('ShaderNodeTexNoise', noise_dimensions='3D')
        s.put(n.inputs['Vector'], vec); s.put(n.inputs['Scale'], scale)
        s.put(n.inputs['Detail'], detail); s.put(n.inputs['Roughness'], rough)
        s.put(n.inputs['Distortion'], dist); s.put(n.inputs['Lacunarity'], lac)
        return S(s, n.outputs['Fac']), V(s, n.outputs['Color'])
    def voronoi(s, vec, scale=1.0):
        n = s.new('ShaderNodeTexVoronoi'); s.put(n.inputs['Vector'], vec); s.put(n.inputs['Scale'], scale)
        return S(s, n.outputs['Distance']), V(s, n.outputs['Color'])
    def bump(s, h, strength=1.0, dist=1.0, normal=None):
        n = s.new('ShaderNodeBump'); s.put(n.inputs['Strength'], strength); s.put(n.inputs['Distance'], dist); s.put(n.inputs['Height'], h)
        if normal is not None: s.put(n.inputs['Normal'], normal)
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

def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)

# ---------------------------------------------------------------- the place
CAM = Vector((0.0, 0.0, 1.7))
YM, XM, ZB, SCL, DEPTH = 680.0, 76.0, -0.3, 0.6, 12.0     # monolith: distance, offset, base, metres per unit, depth

def tile_to_world(u, v):
    return XM + (u - 50.0) * SCL, ZB + (100.0 - v) * SCL

if SUNAT == 'side':
    az, el = math.radians(SUN_AZ), math.radians(SUN_EL)
    TARGET = CAM + Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))) * 1000.0
elif SUNAT == 'crystal':
    TARGET = Vector((XM, YM, ZB + (100 - 51.5) * SCL))
else:   # the upper seam, just above the crystal
    x, z = tile_to_world(60.5, 16.0); TARGET = Vector((x, YM, z))
TO_SUN = (TARGET - CAM).normalized()
TO_SUN = Vector((TO_SUN.x, TO_SUN.y, TO_SUN.z + 0.0012)).normalized()

def parse_path(d):
    import re
    nums = [float(x) for x in re.findall(r'-?\d+\.?\d*', d)]
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]

GEO = {
    'cav': "M60.75 14.02L78.19 42.8L73.21 60.2L39.25 88.97L21.81 60.2L26.79 42.8Z",
    'gem': "M58.6 21.5L70.58 46.7L67.82 56.3L41.4 81.5L29.42 56.3L32.18 46.7Z",
    'seam': "M67.46 -12L68.96 -12L62.35 21.5L45.15 81.5L33.4 112L31.9 112L37.65 81.5L54.85 21.5Z",
}

def prism(name, poly_uv, y0, y1, mats=None):
    """Extrude a tile space polygon (u right, v down) between depths y0 and y1."""
    vs, fs = [], []
    n = len(poly_uv)
    for (u, v) in poly_uv:
        x, z = tile_to_world(u, v); vs.append((x, y0, z))
    for (u, v) in poly_uv:
        x, z = tile_to_world(u, v); vs.append((x, y1, z))
    # orientation: make the front cap face -Y
    area = sum(poly_uv[i][0] * poly_uv[(i + 1) % n][1] - poly_uv[(i + 1) % n][0] * poly_uv[i][1] for i in range(n))
    idx = list(range(n))
    if area < 0: idx = idx[::-1]
    fs.append(tuple(idx)); fs.append(tuple(n + i for i in idx[::-1]))
    for k in range(n):
        a, b = idx[k], idx[(k + 1) % n]
        fs.append((a, n + a, n + b, b))
    me = bpy.data.meshes.new(name); me.from_pydata(vs, [], fs); me.validate(); me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    # fix normals outward
    import bmesh
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return ob

def rounded_square(r=22.0, seg=18):
    pts = []
    for cx, cy, a0 in ((100 - r, r, -90), (100 - r, 100 - r, 0), (r, 100 - r, 90), (r, r, 180)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def stone_mat():
    m, g = material('stone')
    tc = g.new('ShaderNodeTexCoord'); P = V(g, tc.outputs['Object'])
    px, py, pz = g.sep(P)
    # basalt: dark, fine grained, with a faint bedding, broad weathered relief and rain streaks
    n1, _ = g.noise(P, 0.045, 8.0, 0.62, dist=0.5)
    n2, _ = g.noise(P, 2.2, 5.0, 0.62)
    relief, _ = g.noise(P, 0.18, 6.0, 0.58, dist=0.3)
    vd, _ = g.voronoi(P, 0.55)
    grain, _ = g.voronoi(P, 9.0)
    strata = g.sin(pz * 1.1 + n1 * 7.0) * 0.5 + 0.5
    streak, _ = g.noise(g.comb(px * 0.9, py * 0.9, pz * 0.12), 1.0, 7.0, 0.6)
    sk = g.sm(0.52, 0.76, streak)
    base = g.mix((0.028, 0.030, 0.034), (0.068, 0.070, 0.075), g.sm(0.32, 0.70, n1))
    base = g.mix(base, (0.13, 0.13, 0.135), g.sm(0.2, 0.0, grain) * 0.3)
    k = strata * 0.18 + 0.86
    base = g.cmul(base, g.comb(k, k, k))
    base = g.mix(base, (0.022, 0.023, 0.026), sk * 0.25)
    wl = g.sm(2.4, 0.3, pz + n2 * 0.9)                     # the wet foot where the lake laps it
    base = g.mix(base, (0.007, 0.008, 0.010), wl * 0.85)
    rough = 0.46 + n2 * 0.24 - wl * 0.34 - sk * 0.12
    spall = g.sm(0.0, 0.35, vd)
    h = relief * 1.0 + spall * 0.25 + n2 * 0.12 + streak * 0.08 + grain * 0.03
    nrm = g.bump(h, 0.55, 0.12)
    sh = g.principled(Base_Color=base, Roughness=rough, Normal=nrm, Specular_IOR_Level=0.5)
    g.out(sh)
    return m

def crystal_mat():
    """Glass that holds light: deep cobalt at the foot, sky at the crown, the right facet lit as in the mark."""
    m, g = material('crystal')
    sky = srgb('#94E6FF')
    tc = g.new('ShaderNodeTexCoord'); P = V(g, tc.outputs['Object'])
    gp = g.new('ShaderNodeNewGeometry'); N = V(g, gp.outputs['Normal'])
    px, py, pz = g.sep(P)
    n1, _ = g.noise(P, 0.18, 3.0, 0.5)
    hgt = g.sm(ZB + 14.0, ZB + 48.0, pz + n1 * 6.0)
    col = g.mix((0.015, 0.10, 0.48), (0.16, 0.55, 0.85), hgt)
    ecs = g.mix((0.05, 0.30, 0.85), sky, hgt)
    # the facet facing right and up catches more, as the white facet does in the drawn mark
    lit = g.max(g.vm('DOT_PRODUCT', N, (0.62, -0.55, 0.2)), 0.0)
    ecol = g.mix(ecs, (0.62, 0.92, 1.0), lit * 0.35)
    glass = g.principled(Base_Color=col, Roughness=0.04, IOR=1.55, Transmission_Weight=1.0,
                         Emission_Color=ecol, Emission_Strength=float(arg('--cem', '1.0')))
    g.out(glass)
    return m

def water_mat():
    m, g = material('water')
    tc = g.new('ShaderNodeTexCoord'); P = V(g, tc.outputs['Object'])
    px, py, pz = g.sep(P)
    # long, low swell and a few cat's paws of wind: mirror between them
    sw = g.comb(px * 0.05, py * 0.22, 0.0)
    sv, _ = g.noise(sw, 1.0, 3.0, 0.5)
    fine = g.comb(px * 0.9, py * 2.6, 0.0)
    fv, _ = g.noise(fine, 1.0, 4.0, 0.55)
    paws, _ = g.noise(g.comb(px * 0.004, py * 0.012, 3.0), 1.0, 3.0, 0.6)
    pw = g.sm(0.56, 0.68, paws)
    h = sv * 0.6 + fv * (0.12 + pw * 0.5)
    nrm = g.bump(h, 0.045, 0.05)
    sh = g.principled(Base_Color=(0.004, 0.007, 0.011), Roughness=0.015 + pw * 0.07, IOR=1.333,
                      Specular_IOR_Level=0.5, Normal=nrm)
    g.out(sh)
    return m

def ridge_mat(name, col, near, far, k=0.9):
    """Distant land, lost into the morning air: it fades to the very sky behind it."""
    m, g = material(name)
    cd = g.new('ShaderNodeCameraData')
    d = S(g, cd.outputs['View Distance'])
    f = g.sm(near, far, d)
    sh = g.principled(Base_Color=col, Roughness=0.9)
    em = g.new('ShaderNodeEmission')
    gp = g.new('ShaderNodeNewGeometry')
    D = g.vm('NORMALIZE', g.scale(V(g, gp.outputs['Incoming']), -1.0))
    g.put(em.inputs['Color'], sky_color(g, D, clouds=False)); g.put(em.inputs['Strength'], k)
    mx = g.new('ShaderNodeMixShader'); g.put(mx.inputs[0], f)
    g.nt.links.new(sh, mx.inputs[1]); g.nt.links.new(em.outputs[0], mx.inputs[2])
    g.out(mx.outputs[0])
    return m

def ridge(name, dist, x0, x1, hmin, hmax, seed, mat, step=8.0, oct=5):
    rng = np.random.default_rng(seed)
    xs = np.arange(x0, x1 + step, step)
    h = np.zeros_like(xs)
    amp, fr = 1.0, 1.0 / 1600.0
    for o in range(oct):
        ph = rng.uniform(0, 1000)
        k = np.interp((xs * fr + ph) % 64.0, np.arange(65), rng.uniform(-1, 1, 65))
        h += amp * k; amp *= 0.5; fr *= 2.1
    h = (h - h.min()) / (h.max() - h.min())
    h = hmin + (hmax - hmin) * h ** 1.4
    vs, fs = [], []
    n = len(xs)
    for i, x in enumerate(xs):
        y = dist + 0.00004 * x * x
        vs.append((x, y, -2.0)); vs.append((x, y, h[i]))
    for i in range(n - 1):
        fs.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    me = bpy.data.meshes.new(name); me.from_pydata(vs, [], fs); me.update()
    ob = bpy.data.objects.new(name, me); SC.collection.objects.link(ob)
    me.materials.append(mat)
    return ob

def figure(mat):
    """A small person in a long coat, side on, walking the shallows at the water's edge."""
    import bmesh
    obs = []
    X0, Y0 = 9.5, 250.0
    def ell(name, c, r, seg=14):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, location=c)
        ob = bpy.context.active_object; ob.scale = r; ob.name = name; obs.append(ob)
        ob.data.materials.append(mat)
        return ob
    # coat as a tapered loft
    rings = [(0.42, 0.24, 0.17), (0.7, 0.22, 0.15), (0.95, 0.2, 0.135), (1.12, 0.19, 0.125), (1.30, 0.2, 0.135), (1.44, 0.21, 0.13), (1.52, 0.15, 0.1), (1.56, 0.07, 0.065)]
    vs, fs = [], []
    nseg = 20
    for (z, rx, ry) in rings:
        for k in range(nseg):
            a = 2 * math.pi * k / nseg
            vs.append((X0 + ry * math.cos(a), Y0 + rx * math.sin(a) * 0.9, z))
    for j in range(len(rings) - 1):
        for k in range(nseg):
            a, b = j * nseg + k, j * nseg + (k + 1) % nseg
            fs.append((a, b, b + nseg, a + nseg))
    fs.append(tuple(range(nseg))[::-1]); fs.append(tuple(range((len(rings) - 1) * nseg, len(rings) * nseg)))
    me = bpy.data.meshes.new('coat'); me.from_pydata(vs, [], fs); me.update()
    ob = bpy.data.objects.new('coat', me); SC.collection.objects.link(ob); ob.data.materials.append(mat); obs.append(ob)
    # legs mid stride, head, arms
    for s, lean in ((-1, 0.14), (1, -0.12)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.055, depth=0.5, location=(X0 + lean, Y0 + s * 0.08, 0.2), rotation=(0, math.atan(lean / 0.45) * 1.6, 0))
        lg = bpy.context.active_object; lg.data.materials.append(mat); obs.append(lg)
    ell('head', (X0 + 0.01, Y0, 1.68), (0.085, 0.08, 0.105))
    for s, sw in ((-1, -0.06), (1, 0.07)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.045, depth=0.62, location=(X0 + sw, Y0 + s * 0.22, 1.12), rotation=(0, sw * 2.0, 0))
        a = bpy.context.active_object; a.data.materials.append(mat); obs.append(a)
    # a low spit of wet shingle in the shallows, so the figure stands on something
    sm, sg = material('shingle')
    tc = sg.new('ShaderNodeTexCoord'); P = V(sg, tc.outputs['Object'])
    nn, _ = sg.noise(P, 1.5, 4.0, 0.6)
    sg.out(sg.principled(Base_Color=sg.mix((0.012, 0.012, 0.013), (0.03, 0.03, 0.032), nn), Roughness=0.25 + nn * 0.3,
                         Normal=sg.bump(nn, 0.4, 0.05)))
    vs, fs = [(X0 + 2.0, Y0 + 1.0, 0.0)], []
    n = 48
    for k in range(n):
        a = 2 * math.pi * k / n
        r = 1.0 + 0.18 * math.sin(3 * a + 1.0) + 0.1 * math.sin(7 * a)
        vs.append((X0 + 2.0 + math.cos(a) * 26.0 * r, Y0 + 1.0 + math.sin(a) * 4.5 * r, -0.06))
    for k in range(n):
        fs.append((0, 1 + k, 1 + (k + 1) % n))
    vs[0] = (vs[0][0], vs[0][1], 0.05)
    me = bpy.data.meshes.new('spit'); me.from_pydata(vs, [], fs); me.update()
    ob = bpy.data.objects.new('spit', me); SC.collection.objects.link(ob); me.materials.append(sm)
    for p_ in me.polygons: p_.use_smooth = True
    for o in obs:
        o.select_set(False)
    return obs

def sky_color(g, D, clouds=True):
    dx, dy, dz = g.sep(D)
    e = g.max(dz, -0.05)
    cs = g.vm('DOT_PRODUCT', D, tuple(TO_SUN))
    csp = g.max(cs, 0.0)
    sh_ = Vector((TO_SUN.x, TO_SUN.y, 0.0)).normalized()
    hb = g.vm('DOT_PRODUCT', g.vm('NORMALIZE', g.comb(dx, dy, 0.0)), tuple(sh_))
    hbp = g.max(hb * 0.5 + 0.5, 0.0)        # 1 towards the sun's bearing, 0 away from it
    hor = (0.62, 0.68, 0.78)
    low = (0.20, 0.33, 0.62)
    mid = (0.040, 0.105, 0.36)
    zen = (0.010, 0.026, 0.10)
    c = g.mix(hor, low, g.sm(0.0, 0.08, e))
    c = g.mix(c, mid, g.sm(0.06, 0.32, e))
    c = g.mix(c, zen, g.sm(0.28, 0.9, e))
    side = g.pow(hbp, 3.0) * 1.0 + 0.27
    c = g.cmul(c, g.comb(side, side, side))
    if clouds:
        pz = e + 0.035
        u = dx / pz; v = dy / pz
        cv = g.comb(u * 0.16, v * 0.22, 0.0)
        cn, _ = g.noise(cv, 1.0, 8.0, 0.56, dist=0.7)
        cvs = g.comb(u * 0.16 + sh_.x * 0.03, v * 0.22 + sh_.y * 0.03, 0.0)
        cn2, _ = g.noise(cvs, 1.0, 8.0, 0.56, dist=0.7)
        band = g.sm(0.008, 0.03, e) * (1.0 - g.sm(0.075, 0.17, e))
        cover, _ = g.noise(g.comb(u * 0.06, v * 0.06, 2.0), 1.0, 2.0, 0.5)
        thr = 0.44 + (0.5 - cover) * 0.3
        dens = g.sm(thr, thr + 0.16, cn) * band
        lit = g.sm(-0.03, 0.09, cn - cn2)
        sunny = g.pow(hbp, 2.0) * 0.6 + 0.4
        cl_lit = g.mix((0.30, 0.38, 0.60), (1.45, 1.40, 1.34), sunny)
        cl_sh = g.mix((0.035, 0.06, 0.16), (0.16, 0.21, 0.36), sunny)
        clc = g.mix(cl_sh, cl_lit, lit)
        # thin wisps high up
        ci, _ = g.noise(g.comb(u * 0.05, v * 0.9, 5.0), 1.0, 5.0, 0.6, dist=0.4)
        cid = g.sm(0.62, 0.8, ci) * g.sm(0.03, 0.1, e) * (1.0 - g.sm(0.14, 0.26, e)) * 0.16
        c = g.mix(c, g.mix((0.5, 0.58, 0.72), (1.0, 0.99, 0.97), sunny), cid)
        c = g.mix(c, clc, dens * 0.95)
    glow = g.pow(csp, 16.0) * 0.9 + g.exp(g.abs(e) * -30.0) * g.pow(hbp, 5.0) * 0.9 + g.exp(g.abs(e) * -9.0) * g.pow(hbp, 3.0) * 0.18
    core = g.pow(csp, 9000.0) * 50.0
    add = glow + core
    addc = g.cmul(g.comb(add, add, add), (1.0, 0.97, 0.93))
    adn = g.new('ShaderNodeMix', data_type='RGBA', blend_type='ADD'); g.put(adn.inputs[0], 1.0)
    g.put(adn.inputs[6], c); g.put(adn.inputs[7], addc)
    return V(g, adn.outputs[2])

def sky_world():
    wm = bpy.data.worlds.new('w'); SC.world = wm; wm.use_nodes = True
    nt = wm.node_tree; nt.nodes.clear(); g = G(nt)
    bg = g.new('ShaderNodeBackground'); o = g.new('ShaderNodeOutputWorld'); nt.links.new(bg.outputs[0], o.inputs[0])
    tc = g.new('ShaderNodeTexCoord'); D = g.vm('NORMALIZE', V(g, tc.outputs['Generated']))
    g.put(bg.inputs[0], sky_color(g, D)); bg.inputs[1].default_value = 1.0
    wm.lightgroup = 'sky'
    return wm

def mist_mat(density):
    m, g = material('mist')
    vol = g.new('ShaderNodeVolumePrincipled')
    vol.inputs['Anisotropy'].default_value = float(arg('--aniso', '0.45'))
    vol.inputs['Color'].default_value = (0.90, 0.94, 1.0, 1)
    gp = g.new('ShaderNodeNewGeometry'); P = V(g, gp.outputs['Position'])   # world metres
    px, py, pz = g.sep(P)
    n1, _ = g.noise(g.comb(px * 0.006, py * 0.012, pz * 0.08), 1.0, 4.0, 0.55, dist=0.3)
    lay = g.exp(pz * (-1.0 / float(arg('--mh', '8.0'))))
    air = g.exp(pz * (-1.0 / 30.0)) * float(arg('--air', '0.025'))
    far = g.sm(380.0, 820.0, py)          # mist gathers far out on the lake, the near water stays clear
    dens = (lay * (0.15 + 1.6 * g.sm(0.40, 0.72, n1)) * far + air) * density
    lp = g.new('ShaderNodeLightPath'); cam = S(g, lp.outputs['Is Camera Ray'])
    g.put(vol.inputs['Density'], dens * cam)
    g.out(None, vol.outputs[0])
    return m

YAW = math.radians(float(arg('--yaw', '-14')))
def yaw(ob):
    from mathutils import Matrix
    c = Vector((XM, YM, 0.0))
    ob.data.transform(Matrix.Translation(c) @ Matrix.Rotation(YAW, 4, 'Z') @ Matrix.Translation(-c))

def main():
    t0 = time.time()
    m_stone = stone_mat(); m_cry = crystal_mat(); m_water = water_mat()
    m_r1 = ridge_mat('ridge_near', (0.02, 0.024, 0.03), 400.0, 9000.0, 0.85)
    m_r2 = ridge_mat('ridge_far', (0.012, 0.018, 0.03), 1500.0, 14000.0, 0.95)
    m_r3 = ridge_mat('ridge_farthest', (0.02, 0.03, 0.05), 1500.0, 9000.0, 0.99)
    m_fig = bpy.data.materials.new('figure'); m_fig.use_nodes = True
    m_fig.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.012, 0.013, 0.016, 1)
    m_fig.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.8

    # the monolith: the tile with the seam and the cavity cut through it
    y0, y1 = YM - DEPTH / 2, YM + DEPTH / 2
    tile = prism('monolith', rounded_square(), y0, y1)
    cut_seam = prism('cut_seam', parse_path(GEO['seam']), y0 - 5, y1 + 5)
    cut_cav = prism('cut_cav', parse_path(GEO['cav']), y0 - 5, y1 + 5)
    for c in (cut_seam, cut_cav):
        md = tile.modifiers.new('b_' + c.name, 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = c
    bv = tile.modifiers.new('bevel', 'BEVEL'); bv.width = 0.22; bv.segments = 3; bv.limit_method = 'ANGLE'; bv.angle_limit = math.radians(40)
    bpy.context.view_layer.objects.active = tile
    for md in list(tile.modifiers): bpy.ops.object.modifier_apply(modifier=md.name)
    for c in (cut_seam, cut_cav): bpy.data.objects.remove(c)
    tile.data.materials.append(m_stone)
    yaw(tile)
    for p in tile.data.polygons: p.use_smooth = False

    # the crystal: the gem hexagon with a ridge along the facet line, front and back
    gem = parse_path(GEO['gem'])
    gd = DEPTH * 0.55
    gy0, gy1 = YM - gd / 2, YM + gd / 2
    ridge_out = 2.6
    vs = []
    for (u, v) in gem:
        x, z = tile_to_world(u, v); vs.append((x, gy0, z))
    for (u, v) in gem:
        x, z = tile_to_world(u, v); vs.append((x, gy1, z))
    # ridge points: gem vertices 0 and 3 pushed out front and back
    for k in (0, 3):
        x, _, z = vs[k]; vs[k] = (x, gy0 - ridge_out, z)
        x, _, z = vs[6 + k]; vs[6 + k] = (x, gy1 + ridge_out, z)
    fs = [(0, 1, 2, 3), (3, 4, 5, 0), (9, 8, 7, 6), (6, 11, 10, 9)]
    for k in range(6):
        a, b = k, (k + 1) % 6
        fs.append((a, 6 + a, 6 + b, b))
    me = bpy.data.meshes.new('crystal'); me.from_pydata(vs, [], fs); me.update()
    import bmesh
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    cry = bpy.data.objects.new('crystal', me); SC.collection.objects.link(cry)
    me.materials.append(m_cry); cry.pass_index = 1
    bvc = cry.modifiers.new('bevel', 'BEVEL'); bvc.width = 0.12; bvc.segments = 2
    cry.lightgroup = 'sky'
    yaw(cry)

    # the lake
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 4000, 0)); wa = bpy.context.active_object
    wa.scale = (16000, 8000, 1); wa.name = 'water'; wa.data.materials.append(m_water); wa.pass_index = 2

    # the far shore and the hills behind it, lost into the air
    ridge('shore', 1500, -3500, 3500, 2.0, 16.0, 3, m_r1, step=6.0, oct=6)
    ridge('hills', 3200, -6000, 6000, 20.0, 150.0, 5, m_r2, step=12.0)
    ridge('far', 6200, -9000, 9000, 60.0, 420.0, 11, m_r3, step=20.0)
    if FIGURE: figure(m_fig)

    sky_world()
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = float(arg('--sunE', '13.0')); sun.angle = math.radians(0.55); sun.color = (1.0, 0.97, 0.93)
    so = bpy.data.objects.new('sun', sun); SC.collection.objects.link(so)
    so.rotation_euler = (-TO_SUN).to_track_quat('-Z', 'Y').to_euler()
    so.lightgroup = 'sun'

    vl = bpy.context.view_layer
    vl.lightgroups.add(name='sun'); vl.lightgroups.add(name='sky')
    vl.use_pass_object_index = True
    vl.cycles.denoising_store_passes = True

    # the mist, only for the mist pass
    mist_ob = None
    if PASS == 'mist':
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1600, 25)); mist_ob = bpy.context.active_object
        mist_ob.scale = (5200, 3180, 50); mist_ob.name = 'mist'
        mist_ob.data.materials.append(mist_mat(float(arg('--mistd', '0.004'))))
        for ob in SC.collection.objects:
            if ob is not mist_ob and ob.type == 'MESH': ob.is_holdout = True

    # camera: eye height at the water's edge, level, the horizon lowered by lens shift
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); SC.collection.objects.link(cam); SC.camera = cam
    cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.lens = 50.0; cd.shift_y = float(arg('--shift', '0.05'))
    cd.clip_start = 0.5; cd.clip_end = 20000
    cam.location = CAM; cam.rotation_euler = (math.radians(90), 0, 0)

    r = SC.render; r.engine = 'CYCLES'; r.resolution_x, r.resolution_y = W0, H0; r.resolution_percentage = RES
    r.threads_mode = 'FIXED'; r.threads = 4
    c = SC.cycles; c.device = 'CPU'; c.samples = SAMPLES; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.01
    c.adaptive_min_samples = min(32, SAMPLES); c.time_limit = TL
    c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'; c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; c.denoising_prefilter = 'ACCURATE'
    c.max_bounces = 10; c.diffuse_bounces = 3; c.glossy_bounces = 4; c.transmission_bounces = 8; c.volume_bounces = 0; c.transparent_max_bounces = 8
    c.sample_clamp_indirect = 6.0; c.blur_glossy = 0.6; c.caustics_refractive = False; c.caustics_reflective = False
    c.volume_step_rate = 1.0; c.volume_max_steps = 160
    c.use_light_tree = True
    vs_ = SC.view_settings; vs_.view_transform = 'AgX'; vs_.look = 'AgX - Base Contrast'; vs_.exposure = 0.0
    r.film_transparent = PASS == 'mist'

    os.makedirs(OUT, exist_ok=True)
    SC.use_nodes = True; ct = SC.node_tree; ct.nodes.clear()
    rl = ct.nodes.new('CompositorNodeRLayers')
    co = ct.nodes.new('CompositorNodeComposite'); ct.links.new(rl.outputs['Image'], co.inputs['Image'])
    fo = ct.nodes.new('CompositorNodeOutputFile'); fo.base_path = OUT
    fo.format.file_format = 'OPEN_EXR'; fo.format.color_depth = '32'; fo.format.exr_codec = 'ZIP'; fo.format.color_mode = 'RGBA'
    fo.file_slots.clear()
    def slot(name, sock):
        fo.file_slots.new(name); ct.links.new(sock, fo.inputs[name])
    if PASS == 'scene':
        slot('beauty', rl.outputs['Image'])
        dn = ct.nodes.new('CompositorNodeDenoise')
        ct.links.new(rl.outputs['Combined_sun'], dn.inputs['Image'])
        ct.links.new(rl.outputs['Denoising Normal'], dn.inputs['Normal'])
        ct.links.new(rl.outputs['Denoising Albedo'], dn.inputs['Albedo'])
        slot('sun', dn.outputs[0])
        for nm, idx in (('crystal', 1), ('water', 2)):
            idm = ct.nodes.new('CompositorNodeIDMask'); idm.index = idx; idm.use_antialiasing = True
            ct.links.new(rl.outputs['IndexOB'], idm.inputs[0]); slot(nm, idm.outputs[0])
    else:
        slot('mist', rl.outputs['Image'])
    r.filepath = os.path.join(OUT, 'preview_' + PASS + '.png')
    r.image_settings.file_format = 'PNG'
    print('BUILD %.1fs' % (time.time() - t0)); sys.stdout.flush()
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    print('RENDER %s %.1fs' % (PASS, time.time() - t1)); sys.stdout.flush()

main()
