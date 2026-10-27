# Golden Coast: first-frame draft (Antimony world 13).
# Run headless (Blender 4.5 LTS), always under the shared lock:
#   flock <scratch>/blender.lock nice -n 5 blender -b -P golden_coast.py -- [--res 1600x900 --samples 64 --tl 300]
# Writes first-frame-draft.png beside this script (graded: bloom, halation, vignette, grain).
# Assets: Poly Haven and ambientCG scans (CC0) from the shared cache.

# ================================================================ shared: setup, the stone, scatter, grade
# (the same block opens each world script, so every script stands alone)
import bpy, bmesh, math, json, os, re, sys, random
import numpy as np
from mathutils import Vector, Matrix, Euler

SCR = '/tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad'
ASSETS = SCR + '/assets'; PH = ASSETS + '/polyhaven'; ACG = ASSETS + '/ambientcg'
HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    k = '--' + name
    return type(default)(argv[argv.index(k) + 1]) if k in argv else default

OUT = arg('out', os.path.join(HERE, 'first-frame-draft.png'))
RAW = arg('raw', os.path.join(SCR, 'w11-13', os.path.basename(HERE) + '-raw.png'))
W, H = (int(v) for v in arg('res', '1600x900').split('x'))
SAMPLES = arg('samples', 64)
TL = arg('tl', 330.0)
rng = np.random.default_rng(arg('seed', 11)); random.seed(11)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
SKY = srgb('#94E6FF')

def mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); return m, nt
def node(nt, t, **kw):
    n = nt.nodes.new(t)
    for k, v in kw.items():
        if k in n.inputs: n.inputs[k].default_value = v
        else: setattr(n, k, v)
    return n
def link(nt, a, b): nt.links.new(a, b)
def img(path, nc=False):
    im = bpy.data.images.load(path, check_existing=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    return im
def tex(nt, path, nc, vec, box=True):
    t = node(nt, 'ShaderNodeTexImage'); t.image = img(path, nc)
    if box: t.projection = 'BOX'; t.projection_blend = 0.3
    if vec is not None: link(nt, vec, t.inputs['Vector'])
    return t
def mixc(nt, fac, a, b, kind='RGBA'):
    m = node(nt, 'ShaderNodeMix'); m.data_type = kind
    link(nt, fac, m.inputs['Factor'])
    ia = [s for s in m.inputs if s.name == 'A' and s.enabled][0]; ib = [s for s in m.inputs if s.name == 'B' and s.enabled][0]
    link(nt, a, ia); link(nt, b, ib)
    return [s for s in m.outputs if s.name == 'Result' and s.enabled][0]
def maprange(nt, v, a, b, c=0.0, d=1.0):
    r = node(nt, 'ShaderNodeMapRange'); r.inputs['From Min'].default_value = a; r.inputs['From Max'].default_value = b
    r.inputs['To Min'].default_value = c; r.inputs['To Max'].default_value = d
    link(nt, v, r.inputs['Value']); return r.outputs['Result']
def math_(nt, op, a, b=None):
    m = node(nt, 'ShaderNodeMath'); m.operation = op
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): m.inputs[i].default_value = v
        else: link(nt, v, m.inputs[i])
    return m.outputs[0]

def load_objs(blend, names):
    with bpy.data.libraries.load(blend, link=False) as (src, dst):
        dst.objects = [n for n in names if n in src.objects]
    return [o for o in dst.objects if o is not None]
def place(src, loc, rot=(0, 0, 0), scale=(1, 1, 1), name=None):
    ob = bpy.data.objects.new(name or src.name, src.data); sc.collection.objects.link(ob)
    ob.location = loc; ob.rotation_euler = rot; ob.scale = scale if hasattr(scale, '__len__') else (scale,) * 3
    return ob

# ---------------------------------------------------------------- scatter: points instanced by geometry nodes
def scatter(name, srcs, pts, rots, scls, picks):
    srcs = sorted(srcs, key=lambda o: o.name)     # Collection Info separates children by name
    coll = bpy.data.collections.new(name + '_src')
    for s in srcs: coll.objects.link(s)
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(p) for p in pts], [], [])
    a = me.attributes.new('rot', 'FLOAT_VECTOR', 'POINT'); a.data.foreach_set('vector', np.asarray(rots, np.float32).ravel())
    a = me.attributes.new('scl', 'FLOAT_VECTOR', 'POINT'); a.data.foreach_set('vector', np.asarray(scls, np.float32).ravel())
    a = me.attributes.new('pick', 'INT', 'POINT'); a.data.foreach_set('value', np.asarray(picks, np.int32).ravel())
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    ng = bpy.data.node_groups.new(name + '_gn', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, L = ng.nodes, ng.links
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
    ci = N.new('GeometryNodeCollectionInfo'); ci.transform_space = 'ORIGINAL'
    ci.inputs['Collection'].default_value = coll; ci.inputs['Separate Children'].default_value = True
    ci.inputs['Reset Children'].default_value = True
    iop = N.new('GeometryNodeInstanceOnPoints'); iop.inputs['Pick Instance'].default_value = True
    def attr(nm, dt):
        n = N.new('GeometryNodeInputNamedAttribute'); n.data_type = dt; n.inputs['Name'].default_value = nm
        return n.outputs['Attribute']
    L.new(gi.outputs[0], iop.inputs['Points']); L.new(ci.outputs[0], iop.inputs['Instance'])
    L.new(attr('pick', 'INT'), iop.inputs['Instance Index'])
    L.new(attr('rot', 'FLOAT_VECTOR'), iop.inputs['Rotation'])
    L.new(attr('scl', 'FLOAT_VECTOR'), iop.inputs['Scale'])
    L.new(iop.outputs[0], go.inputs[0])
    md = ob.modifiers.new('gn', 'NODES'); md.node_group = ng
    return ob

# ---------------------------------------------------------------- the stone: the whole Break mark, exact
GEO = json.load(open(SCR + '/break-geometry.json'))
def svg_poly(d):
    nums = [float(v) for v in re.findall(r'-?\d+\.?\d*', d)]
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
def rrect(rx=22, n=14):
    pts = []
    for cx, cy_, a0 in ((100 - rx, rx, -90), (100 - rx, 100 - rx, 0), (rx, 100 - rx, 90), (rx, rx, 180)):
        for i in range(n + 1):
            t = math.radians(a0 + 90 * i / n); pts.append((cx + rx * math.cos(t), cy_ + rx * math.sin(t)))
    return pts

def build_stone(size, thick, loc, yaw=0.0, val=0.30, wet=0.4, moss=0.6, glow=0.6, inner_light=0.0,
                light_col=None):
    """The Break as a carved block: tile rx 22 on 100, seam at 16 degrees cut through, cavity cut
    through, the sky crystal seated in it. size: metres for 100 units. Returns (root, crystal)."""
    S, T = size / 100.0, thick
    def to_xz(p): return ((p[0] - 50) * S, (100 - p[1]) * S)
    def prism(name, pts2d, y0, y1):
        bm = bmesh.new()
        fr = [bm.verts.new((x, y0, z)) for x, z in pts2d]; bk = [bm.verts.new((x, y1, z)) for x, z in pts2d]
        bm.faces.new(fr[::-1]); bm.faces.new(bk)
        for i in range(len(pts2d)):
            j = (i + 1) % len(pts2d); bm.faces.new((fr[i], fr[j], bk[j], bk[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); return ob
    tile = prism('stone', [to_xz(p) for p in rrect()], -T / 2, T / 2)
    cs = prism('cut_seam', [to_xz(p) for p in svg_poly(GEO['seam'])], -T, T)
    cc = prism('cut_cav', [to_xz(p) for p in svg_poly(GEO['cav'])], -T, T)
    bv = tile.modifiers.new('arris', 'BEVEL'); bv.width = 0.012 * size; bv.segments = 4
    bv.limit_method = 'ANGLE'; bv.angle_limit = math.radians(35)
    for c in (cs, cc):
        md = tile.modifiers.new('cut', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = c
    dg = bpy.context.evaluated_depsgraph_get()
    me_cut = bpy.data.meshes.new_from_object(tile.evaluated_get(dg))
    tile.modifiers.clear(); tile.data = me_cut
    for c in (cs, cc): bpy.data.objects.remove(c)
    for p in me_cut.polygons: p.use_smooth = True
    try: me_cut.set_sharp_from_angle(angle=math.radians(40))
    except Exception: pass
    # the stone: two scans (ambientCG Rock041, Rock030) blended by noise, honed, weathered
    m, nt = mat('stone')
    tco = node(nt, 'ShaderNodeTexCoord'); geo = node(nt, 'ShaderNodeNewGeometry')
    mp = node(nt, 'ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.8 / (size / 1.9),) * 3
    link(nt, tco.outputs['Object'], mp.inputs['Vector']); v = mp.outputs['Vector']
    A = ACG + '/Rock041/Rock041_2K-JPG_'; B = ACG + '/Rock030/Rock030_2K-JPG_'
    nz = node(nt, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.4 / (size / 1.9); nz.inputs['Detail'].default_value = 3
    link(nt, tco.outputs['Object'], nz.inputs['Vector']); f = maprange(nt, nz.outputs['Fac'], 0.42, 0.62)
    col = mixc(nt, f, tex(nt, A + 'Color.jpg', False, v).outputs[0], tex(nt, B + 'Color.jpg', False, v).outputs[0])
    rgh = mixc(nt, f, tex(nt, A + 'Roughness.jpg', True, v).outputs[0], tex(nt, B + 'Roughness.jpg', True, v).outputs[0])
    nrm = mixc(nt, f, tex(nt, A + 'NormalGL.jpg', True, v).outputs[0], tex(nt, B + 'NormalGL.jpg', True, v).outputs[0])
    hs = node(nt, 'ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = 0.15; hs.inputs['Value'].default_value = val
    link(nt, col, hs.inputs['Color'])
    # height above the ground in object space (the root sits at the ground)
    sep = node(nt, 'ShaderNodeSeparateXYZ'); link(nt, tco.outputs['Object'], sep.inputs[0])
    zn = math_(nt, 'DIVIDE', sep.outputs['Z'], size)
    # rain darkening: streaks running down from the top, stronger high up
    st = node(nt, 'ShaderNodeTexNoise'); st.inputs['Scale'].default_value = 3.0; st.inputs['Detail'].default_value = 6
    stm = node(nt, 'ShaderNodeMapping'); stm.inputs['Scale'].default_value = (14.0, 14.0, 0.8)
    link(nt, tco.outputs['Object'], stm.inputs['Vector']); link(nt, stm.outputs['Vector'], st.inputs['Vector'])
    wetm = math_(nt, 'MULTIPLY', maprange(nt, st.outputs['Fac'], 0.45, 0.62), maprange(nt, zn, 0.1, 1.0, 0.35, 1.0))
    wetm = math_(nt, 'MULTIPLY', wetm, wet)
    mulw = node(nt, 'ShaderNodeMix'); mulw.data_type = 'RGBA'; mulw.blend_type = 'MULTIPLY'
    link(nt, wetm, mulw.inputs['Factor']); link(nt, hs.outputs['Color'], mulw.inputs[6]); mulw.inputs[7].default_value = (0.45, 0.45, 0.47, 1)
    base = mulw.outputs[2]
    # lichen: faint pale specks, mostly on the lower half
    lv = node(nt, 'ShaderNodeTexVoronoi'); lv.inputs['Scale'].default_value = 9.0 / (size / 1.9)
    link(nt, tco.outputs['Object'], lv.inputs['Vector'])
    ln = node(nt, 'ShaderNodeTexNoise'); ln.inputs['Scale'].default_value = 4.0; link(nt, tco.outputs['Object'], ln.inputs['Vector'])
    lm = math_(nt, 'MULTIPLY', maprange(nt, lv.outputs['Distance'], 0.22, 0.05), maprange(nt, ln.outputs['Fac'], 0.5, 0.7))
    lm = math_(nt, 'MULTIPLY', lm, maprange(nt, zn, 0.7, 0.05, 0.0, 0.55 * moss))
    lich = node(nt, 'ShaderNodeMix'); lich.data_type = 'RGBA'; link(nt, lm, lich.inputs['Factor'])
    link(nt, base, lich.inputs[6]); lich.inputs[7].default_value = (0.30, 0.32, 0.24, 1)
    # moss at the foot: scanned moss, rising unevenly a few centimetres
    M = ACG + '/Moss002/Moss002_2K-JPG_'
    mpm = node(nt, 'ShaderNodeMapping'); mpm.inputs['Scale'].default_value = (2.2,) * 3
    link(nt, tco.outputs['Object'], mpm.inputs['Vector'])
    mc = tex(nt, M + 'Color.jpg', False, mpm.outputs['Vector'])
    mn = node(nt, 'ShaderNodeTexNoise'); mn.inputs['Scale'].default_value = 7.0; mn.inputs['Detail'].default_value = 5
    link(nt, tco.outputs['Object'], mn.inputs['Vector'])
    mh = math_(nt, 'ADD', zn, math_(nt, 'MULTIPLY', mn.outputs['Fac'], -0.10))
    mm = math_(nt, 'MULTIPLY', maprange(nt, mh, 0.03, -0.02), moss)
    mos = node(nt, 'ShaderNodeMix'); mos.data_type = 'RGBA'; link(nt, mm, mos.inputs['Factor'])
    link(nt, lich.outputs[2], mos.inputs[6]); mdim = node(nt, 'ShaderNodeHueSaturation'); mdim.inputs['Value'].default_value = 0.55
    link(nt, mc.outputs[0], mdim.inputs['Color']); link(nt, mdim.outputs[0], mos.inputs[7])
    bsdf = node(nt, 'ShaderNodeBsdfPrincipled'); bsdf.inputs['Specular IOR Level'].default_value = 0.5
    link(nt, mos.outputs[2], bsdf.inputs['Base Color'])
    rr = maprange(nt, rgh, 0.0, 1.0, 0.32, 0.6)
    rr = math_(nt, 'SUBTRACT', rr, math_(nt, 'MULTIPLY', wetm, 0.25))
    rr = math_(nt, 'MAXIMUM', rr, math_(nt, 'MULTIPLY', mm, 0.9))
    link(nt, rr, bsdf.inputs['Roughness'])
    nm = node(nt, 'ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.7; link(nt, nrm, nm.inputs['Color'])
    bvn = node(nt, 'ShaderNodeBevel'); bvn.samples = 6; bvn.inputs['Radius'].default_value = 0.004 * size / 1.9
    link(nt, nm.outputs['Normal'], bvn.inputs['Normal']); link(nt, bvn.outputs['Normal'], bsdf.inputs['Normal'])
    o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, bsdf.outputs['BSDF'], o.inputs['Surface'])
    m_in = m.copy(); m_in.name = 'stone_cut'
    for n_ in m_in.node_tree.nodes:
        if n_.bl_idname == 'ShaderNodeHueSaturation' and abs(n_.inputs['Value'].default_value - val) < 1e-6:
            n_.inputs['Value'].default_value = val * 0.35
    me_cut.materials.append(m); me_cut.materials.append(m_in)
    HX, RC, ZC = 50 * S, 22 * S, 50 * S
    def rr_sdf(x, z):
        qx = abs(x) - (HX - RC); qz = abs(z - ZC) - (HX - RC)
        return math.hypot(max(qx, 0), max(qz, 0)) + min(max(qx, qz), 0) - RC
    for p in me_cut.polygons:
        c_ = p.center
        p.material_index = 1 if (abs(p.normal.y) < 0.6 and rr_sdf(c_.x, c_.z) < -0.01 * size) else 0
    tile.modifiers.new('wn', 'WEIGHTED_NORMAL')
    # the crystal: the gem hexagon as a low six-facet pyramid on each face
    gem = [to_xz(p) for p in svg_poly(GEO['gem'])]; cxz = to_xz((50, 51.5))
    ZE, ZR = 0.02 * size, T / 2 - 0.006 * size
    bm = bmesh.new()
    fr = [bm.verts.new((x, -ZE, z)) for x, z in gem]; bk = [bm.verts.new((x, ZE, z)) for x, z in gem]
    af = bm.verts.new((cxz[0], -ZR, cxz[1])); ab = bm.verts.new((cxz[0], ZR, cxz[1]))
    for i in range(len(gem)):
        j = (i + 1) % len(gem)
        bm.faces.new((fr[i], fr[j], af)); bm.faces.new((bk[j], bk[i], ab)); bm.faces.new((fr[j], fr[i], bk[i], bk[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('crystal'); bm.to_mesh(me); bm.free()
    crystal = bpy.data.objects.new('crystal', me); sc.collection.objects.link(crystal)
    b2 = crystal.modifiers.new('arris', 'BEVEL'); b2.width = 0.0014 * size; b2.segments = 2; b2.limit_method = 'ANGLE'
    crystal.pass_index = 1
    m, nt = mat('crystal')
    b = node(nt, 'ShaderNodeBsdfPrincipled')
    b.inputs['Base Color'].default_value = (*[c ** 1.5 for c in SKY], 1)
    b.inputs['Subsurface Weight'].default_value = 1.0; b.inputs['Subsurface Radius'].default_value = (0.35, 0.8, 1.0)
    b.inputs['Subsurface Scale'].default_value = 0.06 * size
    b.inputs['Transmission Weight'].default_value = 0.95; b.inputs['Roughness'].default_value = 0.05
    b.inputs['IOR'].default_value = 1.52; b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.02
    # internal depth: a Voronoi of light inside the glass, as if facets within catch it
    vo = node(nt, 'ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 14.0 / size
    tc2 = node(nt, 'ShaderNodeTexCoord'); link(nt, tc2.outputs['Object'], vo.inputs['Vector'])
    fres = node(nt, 'ShaderNodeLayerWeight'); fres.inputs['Blend'].default_value = 0.35
    gl = math_(nt, 'ADD', maprange(nt, vo.outputs['Distance'], 0.0, 0.5, 1.0, 0.75), math_(nt, 'MULTIPLY', fres.outputs['Facing'], 0.6))
    em = node(nt, 'ShaderNodeEmission'); em.inputs['Color'].default_value = (*SKY, 1)
    link(nt, math_(nt, 'MULTIPLY', gl, glow), em.inputs['Strength'])
    ad = node(nt, 'ShaderNodeAddShader'); link(nt, b.outputs['BSDF'], ad.inputs[0]); link(nt, em.outputs[0], ad.inputs[1])
    o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, ad.outputs[0], o.inputs['Surface'])
    crystal.data.materials.append(m)
    root = bpy.data.objects.new('mark', None); sc.collection.objects.link(root)
    root.location = loc; root.rotation_euler = (0, 0, yaw)
    tile.parent = root; crystal.parent = root
    if inner_light > 0:
        for side in (-1, 1):
            l = bpy.data.lights.new('crystal_light', 'POINT'); l.energy = inner_light; l.color = light_col or SKY
            l.shadow_soft_size = 0.08 * size
            lo = bpy.data.objects.new('crystal_light', l); sc.collection.objects.link(lo); lo.parent = root
            lo.visible_glossy = False; lo.visible_transmission = False
            lo.location = (cxz[0], side * (T / 2 + 0.05 * size), cxz[1])
    return root, crystal


# ---------------------------------------------------------------- foliage from scans (alpha cards), with optional petal tint
def foliage_mat(name, diff, alpha=None, value=1.0, sat=1.0, tint=(1, 1, 1), trans=0.35, rough=0.6,
                petal=None, hue_jitter=0.0, uvbox=None):
    """diff/alpha: the scan's textures (UV). petal: dict(a=rgb, b=rgb, emit=float, bright=float) tints the
    petals (found in the scan's own colour: pale or yellow, bright) and lets them glow gently; the rest
    of the plant keeps its scanned texture under value/sat/tint."""
    m, nt = mat(name)
    tx = tex(nt, diff, False, None, box=False)
    hs = node(nt, 'ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = sat; hs.inputs['Value'].default_value = value
    link(nt, tx.outputs[0], hs.inputs['Color'])
    tm = node(nt, 'ShaderNodeMix'); tm.data_type = 'RGBA'; tm.blend_type = 'MULTIPLY'; tm.inputs['Factor'].default_value = 1
    link(nt, hs.outputs[0], tm.inputs[6]); tm.inputs[7].default_value = (*tint, 1)
    oi = node(nt, 'ShaderNodeObjectInfo')
    if hue_jitter:
        hj = node(nt, 'ShaderNodeHueSaturation')
        link(nt, maprange(nt, oi.outputs['Random'], 0, 1, 0.5 - hue_jitter, 0.5 + hue_jitter), hj.inputs['Hue'])
        link(nt, maprange(nt, oi.outputs['Random'], 0, 1, 0.8, 1.15), hj.inputs['Value'])
        link(nt, tm.outputs[2], hj.inputs['Color']); col = hj.outputs[0]
    else: col = tm.outputs[2]
    bs = node(nt, 'ShaderNodeBsdfPrincipled'); bs.inputs['Roughness'].default_value = rough
    bs.inputs['Specular IOR Level'].default_value = 0.35
    tl = node(nt, 'ShaderNodeBsdfTranslucent')
    surf_col = col; emit = None
    if petal:
        sh = node(nt, 'ShaderNodeSeparateColor'); sh.mode = 'HSV'; link(nt, tx.outputs[0], sh.inputs[0])
        pale = math_(nt, 'MULTIPLY', maprange(nt, sh.outputs[1], 0.30, 0.14), maprange(nt, sh.outputs[2], 0.42, 0.62))
        yel = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', maprange(nt, sh.outputs[0], 0.20, 0.17), maprange(nt, sh.outputs[0], 0.05, 0.08)),
                    math_(nt, 'MULTIPLY', maprange(nt, sh.outputs[1], 0.40, 0.55), maprange(nt, sh.outputs[2], 0.40, 0.60)))
        pm = math_(nt, 'MINIMUM', math_(nt, 'ADD', pale, yel), 1.0)
        if uvbox:
            uvn = node(nt, 'ShaderNodeUVMap'); su = node(nt, 'ShaderNodeSeparateXYZ'); link(nt, uvn.outputs[0], su.inputs[0])
            inb = math_(nt, 'MULTIPLY', math_(nt, 'LESS_THAN', su.outputs['X'], uvbox[1]), math_(nt, 'LESS_THAN', su.outputs['Y'], uvbox[3]))
            inb = math_(nt, 'MULTIPLY', inb, math_(nt, 'MULTIPLY', math_(nt, 'GREATER_THAN', su.outputs['X'], uvbox[0]), math_(nt, 'GREATER_THAN', su.outputs['Y'], uvbox[2])))
            pm = math_(nt, 'MULTIPLY', pm, inb)
        pc = node(nt, 'ShaderNodeMix'); pc.data_type = 'RGBA'
        link(nt, oi.outputs['Random'], pc.inputs['Factor']); pc.inputs[6].default_value = (*petal['a'], 1); pc.inputs[7].default_value = (*petal['b'], 1)
        # keep the petal's own light and dark (veins, shading) under the new colour
        vv = maprange(nt, sh.outputs[2], 0.3, 1.0, 0.55, 1.0)
        pcv = node(nt, 'ShaderNodeMix'); pcv.data_type = 'RGBA'; pcv.blend_type = 'MULTIPLY'; pcv.inputs['Factor'].default_value = 1
        link(nt, pc.outputs[2], pcv.inputs[6]); vc = node(nt, 'ShaderNodeCombineColor'); link(nt, vv, vc.inputs[0]); link(nt, vv, vc.inputs[1]); link(nt, vv, vc.inputs[2])
        link(nt, vc.outputs[0], pcv.inputs[7])
        surf_col = mixc(nt, pm, col, pcv.outputs[2])
        ie = maprange(nt, oi.outputs['Random'], 0, 1, 0.55, 1.35)
        emit = node(nt, 'ShaderNodeEmission'); link(nt, pcv.outputs[2], emit.inputs['Color'])
        link(nt, math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', pm, ie), petal['emit']), emit.inputs['Strength'])
        trans_f = math_(nt, 'ADD', trans, math_(nt, 'MULTIPLY', pm, 0.25))
    else:
        trans_f = None
    link(nt, surf_col, bs.inputs['Base Color']); link(nt, surf_col, tl.inputs['Color'])
    ms = node(nt, 'ShaderNodeMixShader')
    if trans_f is not None: link(nt, trans_f, ms.inputs[0])
    else: ms.inputs[0].default_value = trans
    link(nt, bs.outputs[0], ms.inputs[1]); link(nt, tl.outputs[0], ms.inputs[2]); sh_out = ms.outputs[0]
    if emit is not None:
        ad = node(nt, 'ShaderNodeAddShader'); link(nt, sh_out, ad.inputs[0]); link(nt, emit.outputs[0], ad.inputs[1]); sh_out = ad.outputs[0]
    if alpha:
        at = tex(nt, alpha, True, None, box=False); tr = node(nt, 'ShaderNodeBsdfTransparent')
        ma = node(nt, 'ShaderNodeMixShader'); link(nt, at.outputs[0], ma.inputs[0])
        link(nt, tr.outputs[0], ma.inputs[1]); link(nt, sh_out, ma.inputs[2]); sh_out = ma.outputs[0]
    o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, sh_out, o.inputs['Surface'])
    return m

def set_mat(objs, m):
    for o in objs:
        o.data.materials.clear(); o.data.materials.append(m)

# ---------------------------------------------------------------- render settings and the grade
def cycles(samples=SAMPLES, tl=TL, exposure=0.0, look='None', volume=False):
    sc.render.engine = 'CYCLES'; c = sc.cycles
    c.device = 'CPU'; c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.03
    c.time_limit = tl; c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'; c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    c.max_bounces = 6; c.diffuse_bounces = 2; c.glossy_bounces = 2; c.transmission_bounces = 6
    c.transparent_max_bounces = 12; c.volume_bounces = 0
    c.caustics_reflective = False; c.caustics_refractive = False; c.sample_clamp_indirect = 6.0
    c.use_light_tree = True; c.blur_glossy = 1.0
    if volume: c.volume_step_rate = 4.0; c.volume_max_steps = 128
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    sc.render.resolution_x, sc.render.resolution_y = W, H; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '16'
    sc.render.image_settings.color_mode = 'RGB'
    vs = sc.view_settings; vs.view_transform = 'AgX'; vs.look = look; vs.exposure = exposure

def mist_comp(col, amount, start, depth, sky_amount=None):
    """depth haze from the mist pass, mixed in linear light before the view transform"""
    sc.view_layers[0].use_pass_mist = True
    sc.world.mist_settings.start = start; sc.world.mist_settings.depth = depth; sc.world.mist_settings.falloff = 'QUADRATIC'
    sc.use_nodes = True; T_ = sc.node_tree
    for n in list(T_.nodes): T_.nodes.remove(n)
    rl = T_.nodes.new('CompositorNodeRLayers'); out = T_.nodes.new('CompositorNodeComposite')
    mx = T_.nodes.new('CompositorNodeMixRGB'); mx.blend_type = 'MIX'; mx.inputs[2].default_value = (*col, 1)
    mm = T_.nodes.new('CompositorNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = amount
    T_.links.new(rl.outputs['Mist'], mm.inputs[0]); fac = mm.outputs[0]
    if sky_amount is not None:      # the open sky takes its own, lighter veil so its clouds survive
        gt = T_.nodes.new('CompositorNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.999
        T_.links.new(rl.outputs['Mist'], gt.inputs[0])
        sub = T_.nodes.new('CompositorNodeMath'); sub.operation = 'MULTIPLY'; sub.inputs[1].default_value = amount - sky_amount
        T_.links.new(gt.outputs[0], sub.inputs[0])
        d = T_.nodes.new('CompositorNodeMath'); d.operation = 'SUBTRACT'; T_.links.new(fac, d.inputs[0]); T_.links.new(sub.outputs[0], d.inputs[1])
        fac = d.outputs[0]
    T_.links.new(fac, mx.inputs[0])
    T_.links.new(rl.outputs['Image'], mx.inputs[1]); T_.links.new(mx.outputs[0], out.inputs[0])

def _blur(a, r):
    """three box passes: near gaussian. a: HxWxC float32"""
    r = max(1, int(r))
    for _ in range(3):
        for ax in (0, 1):
            c = np.cumsum(np.pad(a, [(r + 1, r) if i == ax else (0, 0) for i in range(3)], mode='edge'), axis=ax, dtype=np.float32)
            n = a.shape[ax]
            a = (np.take(c, range(2 * r + 1, 2 * r + 1 + n), axis=ax) - np.take(c, range(0, n), axis=ax)) / (2 * r + 1)
    return a

def grade(raw, out, bloom=0.22, bloom_thr=0.55, halation=0.10, grain=0.018, vignette=0.32, lift=0.012,
          tint=(1.0, 1.0, 1.0), rain=0.0, rain_col=(0.75, 0.88, 1.0)):
    """the light grade, in display space after AgX: bloom, halation, lift, tint, vignette, grain"""
    im = bpy.data.images.load(raw); im.colorspace_settings.name = 'Non-Color'
    w, h = im.size
    a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a); a = a.reshape(h, w, 4)[:, :, :3].copy()
    lum = (a * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(2, keepdims=True)
    hi = np.clip(a - bloom_thr, 0, None) * (1 / (1 - bloom_thr))
    small = hi[::4, ::4]
    bl = 0.5 * _blur(small, w / 400) + 0.35 * _blur(small, w / 120) + 0.15 * _blur(small, w / 40)
    bl = np.repeat(np.repeat(bl, 4, 0), 4, 1)[:h, :w]
    a = a + bloom * bl * (1 - a * 0.5)
    hl = np.clip(lum - 0.7, 0, None) * 3.0
    ha = _blur(hl[::2, ::2], w / 500); ha = np.repeat(np.repeat(ha, 2, 0), 2, 1)[:h, :w]
    a = a + halation * ha * np.array([1.0, 0.32, 0.18], np.float32)
    a = a * np.array(tint, np.float32)
    if rain > 0:
        # fine rain: short, faint, slightly slanted streaks at two depths, brighter over light
        ov = np.zeros((h, w), np.float32)
        for n, ln, wgt in ((int(w * h / 900), (10, 26), 0.5), (int(w * h / 4000), (30, 70), 1.0)):
            xs = rng.uniform(0, w, n); ys = rng.uniform(0, h, n); ls = rng.uniform(*ln, n)
            for t in np.linspace(0, 1, int(ln[1])):
                xi = (xs + t * ls * 0.12).astype(int); yi = (ys + t * ls).astype(int)
                ok = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h) & (t * ln[1] <= ls)
                ov[yi[ok], xi[ok]] += wgt * np.sin(np.pi * t)
        ov = _blur(ov[..., None], 1)[..., 0]
        a = a + rain * ov[..., None] * (0.35 + 1.6 * _blur(lum[::4, ::4], 6).repeat(4, 0).repeat(4, 1)[:h, :w]) * np.array(rain_col, np.float32)
    a = lift + a * (1 - lift)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = ((xx / w - 0.5) * 1.0) ** 2 + ((yy / h - 0.5) * 0.85) ** 2
    a = a * (1 - vignette * np.clip(d / 0.5, 0, 1) ** 1.3)[..., None]
    g = rng.normal(0, 1, (h, w, 1)).astype(np.float32)
    g = 0.6 * g + 0.4 * np.repeat(np.repeat(rng.normal(0, 1, ((h + 1) // 2, (w + 1) // 2, 1)).astype(np.float32), 2, 0), 2, 1)[:h, :w]
    a = a + grain * g * (0.35 + 0.65 * np.sqrt(np.clip(lum, 0, 1)))
    a = np.clip(a, 0, 1)
    o = bpy.data.images.new('graded', w, h, alpha=False)
    o.colorspace_settings.name = 'Non-Color'
    o.pixels.foreach_set(np.concatenate([a, np.ones((h, w, 1), np.float32)], 2).ravel())
    o.filepath_raw = out; o.file_format = 'PNG'; o.save()
    print('graded', out)

def render_and_grade(**kw):
    import time; t0 = time.time()
    sc.render.filepath = RAW
    bpy.ops.render.render(write_still=True)
    print('render seconds', round(time.time() - t0))
    grade(RAW, OUT, **kw)
# ================================================================ end of shared block

# ================================================================ Golden Coast
# Golden hour on a clifftop meadow above a calm, shining sea. The low sun stands over the water to the
# left and lays a path of light across it; along the coast to the right, far off on a headland in the
# haze, an old weathered fortification of concrete (Poly Haven modular_fort_01 pieces, re-surfaced with
# ambientCG Concrete044B); gulls; the stone at the very edge of the cliff, backlit, its crystal catching
# the sun. Metres, Z up; the sea is Z = 0; the camera stands on the clifftop looking north (+Y).

from mathutils.noise import noise as pnoise
TOP = 34.0
STONE_AT = Vector((-1.2, 13.0, 0.0))
def edge(y):
    """the coastline: land lies at x > edge(y). Straight near the camera, a bay, then a headland reaching left"""
    e = -3.2 + 0.03 * y
    e += 34 * math.exp(-((y - 120) / 45) ** 2)
    e -= 48 * math.exp(-((y - 280) / 50) ** 2)
    return e + 1.6 * pnoise(Vector((y / 9, 0.3, 0.5))) + 0.7 * pnoise(Vector((y / 3, 1.3, 0.5)))
def gh(x, y):
    d = x - edge(y)
    top = TOP + 0.9 * pnoise(Vector((x / 16, y / 16, 0.2))) + 0.25 * pnoise(Vector((x / 4, y / 4, 0.9))) + min(max(d, 0), 60) * 0.03
    if d >= 0: return top - 2.2 * math.exp(-d / 0.8)            # the lip rounds over
    return top - 2.2 - (TOP + 6) * min(1.0, (-d / 6.0) ** 0.8)    # the cliff face falls to the sea floor

# ---------------------------------------------------------------- the land (heightfield, scanned rock and grass by slope)
NX, NY = 260, 240
xs = np.concatenate([np.linspace(-80, 30, NX // 2), np.linspace(30.5, 260, NX // 2)])
ys = np.concatenate([np.linspace(-4, 60, NY // 2), np.geomspace(61, 600, NY // 2)])
bm = bmesh.new(); vs = [[bm.verts.new((x, y, gh(x, y))) for x in xs] for y in ys]
for j in range(len(ys) - 1):
    for i in range(len(xs) - 1): bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
me = bpy.data.meshes.new('land'); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
land = bpy.data.objects.new('land', me); sc.collection.objects.link(land)
m, nt = mat('land'); tco = node(nt, 'ShaderNodeTexCoord'); geo = node(nt, 'ShaderNodeNewGeometry')
mp = node(nt, 'ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.25,) * 3; link(nt, tco.outputs['Object'], mp.inputs[0])
R = ACG + '/Rock030/Rock030_2K-JPG_'; G = ACG + '/Grass004/Grass004_2K-JPG_'
sep = node(nt, 'ShaderNodeSeparateXYZ'); link(nt, geo.outputs['Normal'], sep.inputs[0])
nz = node(nt, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.3; link(nt, tco.outputs['Object'], nz.inputs['Vector'])
f = maprange(nt, math_(nt, 'ADD', sep.outputs['Z'], math_(nt, 'MULTIPLY', nz.outputs['Fac'], 0.3)), 0.78, 0.92)
gc = node(nt, 'ShaderNodeHueSaturation'); gc.inputs['Hue'].default_value = 0.47; gc.inputs['Saturation'].default_value = 0.8; gc.inputs['Value'].default_value = 0.85
link(nt, tex(nt, G + 'Color.jpg', False, mp.outputs[0]).outputs[0], gc.inputs['Color'])
rc = node(nt, 'ShaderNodeHueSaturation'); rc.inputs['Saturation'].default_value = 0.7; rc.inputs['Value'].default_value = 0.8
link(nt, tex(nt, R + 'Color.jpg', False, mp.outputs[0]).outputs[0], rc.inputs['Color'])
bs = node(nt, 'ShaderNodeBsdfPrincipled'); link(nt, mixc(nt, f, rc.outputs[0], gc.outputs[0]), bs.inputs['Base Color'])
link(nt, mixc(nt, f, tex(nt, R + 'Roughness.jpg', True, mp.outputs[0]).outputs[0], tex(nt, G + 'Roughness.jpg', True, mp.outputs[0]).outputs[0]), bs.inputs['Roughness'])
nm = node(nt, 'ShaderNodeNormalMap'); link(nt, mixc(nt, f, tex(nt, R + 'NormalGL.jpg', True, mp.outputs[0]).outputs[0], tex(nt, G + 'NormalGL.jpg', True, mp.outputs[0]).outputs[0]), nm.inputs['Color'])
link(nt, nm.outputs[0], bs.inputs['Normal'])
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, bs.outputs[0], o.inputs['Surface']); land.data.materials.append(m)

# scanned sea cliffs set into the faces, so the rock is real where it shows
CL = load_objs(f'{PH}/coastal_cliff_01/coastal_cliff_01_1k.blend', ['coastal_cliff_01_LOD3']) + \
     load_objs(f'{PH}/coastal_cliff_02/coastal_cliff_02_1k.blend', ['coastal_cliff_02_LOD3'])
for (y, k, s, rz) in ((150, 0, 1.0, -0.5), (235, 1, 2.0, 0.7), (300, 0, 1.2, -0.2), (330, 1, 2.0, 0.4)):
    depth = CL[k].dimensions.y * s
    x = edge(y) - depth / 2 - 3
    ob = place(CL[k], (x, y, -1), (0, 0, math.radians(90) + rz), (s, s, (TOP - 6) / CL[k].dimensions.z))
# far islets on the horizon to the left
for (x, y, s, k) in ((-420, 900, 2.5, 1), (-360, 980, 1.6, 0), (-250, 1100, 1.4, 1), (-520, 1200, 2.0, 0)):
    place(CL[k], (x, y, -2), (0, 0, rng.uniform(0, 6.28)), (s, s, s * 1.2))

# ---------------------------------------------------------------- the sea
bpy.ops.mesh.primitive_plane_add(size=20000, location=(0, 0, 0)); sea = bpy.context.object; sea.name = 'sea'
m, nt = mat('sea'); bs = node(nt, 'ShaderNodeBsdfPrincipled')
bs.inputs['Base Color'].default_value = (0.03, 0.05, 0.06, 1); bs.inputs['Roughness'].default_value = 0.06; bs.inputs['IOR'].default_value = 1.33
tco = node(nt, 'ShaderNodeTexCoord')
wv = node(nt, 'ShaderNodeTexNoise'); wv.inputs['Scale'].default_value = 0.5; wv.inputs['Detail'].default_value = 8; wv.inputs['Roughness'].default_value = 0.6
mpw = node(nt, 'ShaderNodeMapping'); mpw.inputs['Scale'].default_value = (0.25, 1.0, 1.0); link(nt, tco.outputs['Object'], mpw.inputs[0]); link(nt, mpw.outputs[0], wv.inputs['Vector'])
bu = node(nt, 'ShaderNodeBump'); bu.inputs['Strength'].default_value = 0.35; link(nt, wv.outputs['Fac'], bu.inputs['Height']); link(nt, bu.outputs[0], bs.inputs['Normal'])
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, bs.outputs[0], o.inputs['Surface']); sea.data.materials.append(m)

# ---------------------------------------------------------------- the old structure on the headland
FORT = load_objs(f'{PH}/modular_fort_01/modular_fort_01_1k.blend',
                 ['modular_fort_01_tower_round', 'modular_fort_01_wall_thick_straight_01', 'modular_fort_01_wall_thick_corner_01'])
FORT = {o.name.replace('modular_fort_01_', ''): o for o in FORT}
cm, nt = mat('weathered_concrete'); tco = node(nt, 'ShaderNodeTexCoord')
mpc = node(nt, 'ShaderNodeMapping'); mpc.inputs['Scale'].default_value = (0.25,) * 3; link(nt, tco.outputs['Object'], mpc.inputs[0])
C = ACG + '/Concrete044B/Concrete044B_2K-JPG_'
if not os.path.exists(C + 'Color.jpg'): C = ACG + '/Concrete031/Concrete031_2K-JPG_'
bsc = node(nt, 'ShaderNodeBsdfPrincipled'); hc = node(nt, 'ShaderNodeHueSaturation'); hc.inputs['Value'].default_value = 0.7
link(nt, tex(nt, C + 'Color.jpg', False, mpc.outputs[0]).outputs[0], hc.inputs['Color']); link(nt, hc.outputs[0], bsc.inputs['Base Color'])
link(nt, tex(nt, C + 'Roughness.jpg', True, mpc.outputs[0]).outputs[0], bsc.inputs['Roughness'])
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, bsc.outputs[0], o.inputs['Surface'])
for o_ in FORT.values(): set_mat([o_], cm)
HX, HY = 22.0, 278.0; HZ = gh(HX, HY)
FS = 1.5         # the kit's thick walls stacked into a blunt, stepped concrete works (no towers: no castle)
for (dx, dy, dz, k, rz, sx, sz) in ((0, 0, 0, 'wall_thick_straight_01', 0.0, 2.2, 2.6), (-16, 4, 0, 'wall_thick_straight_01', math.radians(90), 1.6, 1.8),
                                    (14, -6, 0, 'wall_thick_straight_01', math.radians(90), 2.0, 2.2), (2, 6, 18, 'wall_thick_straight_01', 0.0, 1.5, 1.4),
                                    (-6, 2, 18, 'wall_thick_corner_01', 0.0, 1.4, 1.6), (30, -2, 0, 'wall_thick_corner_01', 0.3, 1.8, 1.5)):
    x, y = HX + dx, HY + dy
    place(FORT[k], (x, y, gh(x, y) - 2 + dz), (0, 0, rz), (FS * sx, FS, FS * sz))

# ---------------------------------------------------------------- the stone, at the cliff's edge
root, crystal = build_stone(2.2, 0.5, (STONE_AT.x, STONE_AT.y, gh(STONE_AT.x, STONE_AT.y) - 0.12), math.radians(arg('yaw', 18.0)),
                            val=0.34, wet=0.2, moss=0.7, glow=arg('glow', 0.3), inner_light=0.0)

# ---------------------------------------------------------------- the clifftop meadow: dry golden grass (scans), backlit
G1 = load_objs(f'{PH}/grass_medium_01/grass_medium_01_2k.blend', [f'grass_medium_01_{k}_LOD1' for k in ('tall_a', 'tall_b', 'tall_c', 'mid_a', 'mid_b', 'large_a')])
G2 = load_objs(f'{PH}/grass_medium_02/grass_medium_02_2k.blend', [f'grass_medium_02_{k}' for k in 'bcde'])
SH = load_objs(f'{PH}/shrub_sorrel_01/shrub_sorrel_01_1k.blend', [f'shrub_sorrel_01_{k}' for k in 'abde'])
gdry = foliage_mat('grass_dry', f'{PH}/grass_medium_01/textures/grass_medium_01_dry_diff_2k.png', f'{PH}/grass_medium_01/textures/grass_medium_01_alpha_2k.png',
                   value=1.0, sat=0.95, tint=(1.0, 0.86, 0.62), trans=0.5, hue_jitter=0.03)
gmix = foliage_mat('grass_mix', f'{PH}/grass_medium_02/textures/grass_medium_02_dry_diff_2k.png', f'{PH}/grass_medium_02/textures/grass_medium_02_alpha_2k.png',
                   value=0.95, sat=0.9, tint=(1.0, 0.9, 0.7), trans=0.5, hue_jitter=0.04)
set_mat(G1, gdry); set_mat(G2, gmix)
srcs = G1 + G2
n = 30000; u = rng.random(n); y = 2.0 + 120 * u ** 2.2; x = rng.uniform(-1, 1, n) * (y * 0.75 + 3)
d = np.array([a - edge(b) for a, b in zip(x, y)])
keep = (d > 0.15) & (np.hypot(x - STONE_AT.x, (y - STONE_AT.y) * 1.3) > 1.0)
x, y = x[keep], y[keep]; k = len(x); z = np.array([gh(a, b) for a, b in zip(x, y)])
s = rng.uniform(0.8, 1.6, k) * np.where(y < 5, 1.2, 1.0) * np.clip(np.hypot(x - STONE_AT.x, y - STONE_AT.y) / 2.0, 0.45, 1.0)
scatter('meadow', srcs, np.stack([x, y, z], 1), np.stack([rng.normal(0, 0.15, k), rng.normal(0, 0.15, k), rng.uniform(0, 6.28, k)], 1),
        np.stack([s, s, s * rng.uniform(1.0, 1.5, k)], 1), rng.integers(0, len(srcs), k))
n = 2500; u = rng.random(n); y = 1 + 50 * u ** 2; x = rng.uniform(-1, 1, n) * (y * 0.7 + 3)
d = np.array([a - edge(b) for a, b in zip(x, y)]); keep = d > 0.3; x, y = x[keep], y[keep]; k = len(x)
z = np.array([gh(a, b) for a, b in zip(x, y)]); s = rng.uniform(5, 9, k)
scatter('sorrel', SH, np.stack([x, y, z], 1), np.stack([np.zeros(k), np.zeros(k), rng.uniform(0, 6.28, k)], 1), np.stack([s, s, s], 1), rng.integers(0, len(SH), k))

# ---------------------------------------------------------------- gulls: small far silhouettes (no scan of a bird in flight exists in the CC0 libraries)
gm, nt = mat('gull'); bsg = node(nt, 'ShaderNodeBsdfPrincipled'); bsg.inputs['Base Color'].default_value = (0.5, 0.48, 0.45, 1)
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, bsg.outputs[0], o.inputs['Surface'])
for (x, y, z, sz, rz) in ((-60, 160, 62, 1.0, 0.3), (-48, 175, 66, 0.9, 0.5), (-75, 210, 58, 0.8, -0.2), (-30, 260, 75, 1.0, 0.1), (-90, 300, 70, 1.0, 0.7)):
    bm = bmesh.new(); w_ = 0.8 * sz
    v0 = bm.verts.new((0, 0, 0)); a1 = bm.verts.new((-w_, -0.12, 0.22)); a2 = bm.verts.new((-2 * w_, -0.05, 0.05)); b1 = bm.verts.new((w_, -0.12, 0.22)); b2 = bm.verts.new((2 * w_, -0.05, 0.05))
    t0 = bm.verts.new((0, 0.35, 0.02))
    bm.faces.new((v0, a1, a2)); bm.faces.new((v0, b2, b1)); bm.faces.new((a1, v0, t0)); bm.faces.new((v0, b1, t0))
    me = bpy.data.meshes.new('gull'); bm.to_mesh(me); bm.free(); me.materials.append(gm)
    g = bpy.data.objects.new('gull', me); sc.collection.objects.link(g); g.location = (x, y, TOP + z - 30); g.rotation_euler = (0.1, 0.0, rz)

# ---------------------------------------------------------------- sun and sky: the HDRI's own sun turned to stand over the sea, left
HDRI = f'{PH}/belfast_sunset_puresky/belfast_sunset_puresky_2k.hdr'
im = img(HDRI); iw, ih = im.size
px = np.empty(iw * ih * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(ih, iw, 4)
lumi = px[:, :, :3].sum(2); vi, ui = np.unravel_index(np.argmax(lumi), lumi.shape)
u_, v_ = (ui + 0.5) / iw, (vi + 0.5) / ih
phi = (u_ - 0.5) * 2 * math.pi; az_h = math.atan2(math.sin(phi), -math.cos(phi)); el_h = (v_ - 0.5) * math.pi
AZ = math.radians(arg('sunaz', 122.0)); EL = math.radians(arg('sunel', 8.0))
to_sun = Vector((math.cos(AZ) * math.cos(EL), math.sin(AZ) * math.cos(EL), math.sin(EL)))
print('hdri sun', math.degrees(az_h), math.degrees(el_h))
wld = bpy.data.worlds.new('sky'); sc.world = wld; wld.use_nodes = True; wn = wld.node_tree; wn.nodes.clear()
tc = node(wn, 'ShaderNodeTexCoord'); mpw = node(wn, 'ShaderNodeMapping'); mpw.inputs['Rotation'].default_value = (0, 0, az_h - AZ)
env = node(wn, 'ShaderNodeTexEnvironment'); env.image = im
link(wn, tc.outputs['Generated'], mpw.inputs[0]); link(wn, mpw.outputs[0], env.inputs['Vector'])
warm = node(wn, 'ShaderNodeMix'); warm.data_type = 'RGBA'; warm.blend_type = 'MULTIPLY'; warm.inputs['Factor'].default_value = 1
link(wn, env.outputs[0], warm.inputs[6]); warm.inputs[7].default_value = (1.0, 0.78, 0.55, 1)
bg = node(wn, 'ShaderNodeBackground'); bg.inputs['Strength'].default_value = arg('sky', 1.4)
link(wn, warm.outputs[2], bg.inputs['Color']); wo = node(wn, 'ShaderNodeOutputWorld'); link(wn, bg.outputs[0], wo.inputs['Surface'])
sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = arg('sun', 7.0); sun.color = (1.0, 0.72, 0.45); sun.angle = math.radians(1.2)
so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so); so.rotation_euler = to_sun.to_track_quat('Z', 'Y').to_euler()

# ---------------------------------------------------------------- camera
cam = bpy.data.cameras.new('cam'); cam.lens = 30; cam.sensor_width = 36
cam.dof.use_dof = True; cam.dof.aperture_fstop = 5.6
co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
CAM_Z = gh(3.0, 0.0) + 1.6
co.location = (3.0, 0.0, CAM_Z)
tgt = Vector((-4.0, 40, CAM_Z + 40 * math.tan(math.radians(arg('pitch', -3.0)))))
co.rotation_euler = (tgt - co.location).to_track_quat('-Z', 'Y').to_euler()
cam.dof.focus_distance = (Vector((STONE_AT.x, STONE_AT.y, CAM_Z)) - co.location).length

cycles(exposure=arg('exposure', 0.2), look='None')
mist_comp((1.0, 0.74, 0.50), arg('mist', 0.55), 40, 900, sky_amount=0.0)
render_and_grade(bloom=0.30, bloom_thr=0.6, halation=0.14, grain=0.016, vignette=0.28, lift=0.02, tint=(1.06, 1.0, 0.90))
