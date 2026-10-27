# Poster 1, hero: the slim glass lightbox with the cobalt print, in seven settings, path traced.
#
#   blender -b --factory-startup -P poster_hero.py -- --setting 1 --out raw.png [options]
#
# Settings: 1 mist (the monumental wall, heavy low mist), 2 flowers (the wall, pale blue flowers in the cracks),
# 3 blue field, 4 ruins, 7 undercity, 8 pond courtyard, 9 moon forest.
# Options: --res 1920x1080, --samples 256, --time <seconds cap>, --device CPU | OPTIX | CUDA | HIP | METAL,
#          --print <png> (made by hero_print.py), --ph and --acg (the Poly Haven and ambientCG caches),
#          --data <png> (a linear data pass: R depth / 100 m, G standing water, B object: 1 print, 2 glass,
#          3 lightbox case; also written exactly as .npz), --lite 1 (quick drafts: fewer plants and drops).
# Writes <out> and <out>.json: the print's four corners and the mark's box in pixels, the camera, the setting.
# The poster is never touched by growth: every plant is tested in the lens's view against the box's outline.
# Poster 1 itself (poster.py) is unchanged.

import bpy, bmesh, math, sys, os, json, time
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = '/tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad'
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d):
    if k not in argv: return d
    v = argv[argv.index(k) + 1]
    return type(d)(v) if not isinstance(d, str) else v

SET = str(arg('--setting', '1'))
RES = arg('--res', '960x540'); W, H = (int(v) for v in RES.split('x'))
SAMPLES = arg('--samples', 64); TCAP = arg('--time', 0.0)
DEVICE = arg('--device', 'CPU').upper()
OUT = os.path.abspath(arg('--out', os.path.join(HERE, 'hero-%s.png' % SET)))
DATA = arg('--data', '')
PRINT = arg('--print', os.path.join(HERE, 'assets', 'hero-print.png'))
PH = arg('--ph', os.path.join(SCR, 'assets', 'polyhaven')); ACG = arg('--acg', os.path.join(SCR, 'assets', 'ambientcg'))
LITE = arg('--lite', 0)
FULL = arg('--full', 0)            # the hero finish: micro-displacement, hand-placed debris, layered air
EXPO = arg('--exposure', 0.0)
rng = np.random.default_rng(7 + sum(ord(c) * (i + 1) for i, c in enumerate(SET)))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
vl = sc.view_layers[0]
_a = vl.aovs.add(); _a.name = 'wt'; _a.type = 'VALUE'

# ---------------------------------------------------------------- node helpers
def node(nt, t, **kw):
    n = nt.nodes.new(t)
    for k, v in kw.items():
        if k in n.inputs.keys(): n.inputs[k].default_value = v
        else: setattr(n, k, v)
    return n
def link(nt, a, b): nt.links.new(a, b)
def put(nt, sock, v):
    if isinstance(v, bpy.types.NodeSocket): link(nt, v, sock)
    elif isinstance(v, (tuple, list)):
        dv = sock.default_value; v = tuple(v) + (1.0,) * (len(dv) - len(v)); sock.default_value = v[:len(dv)]
    else: sock.default_value = v
def M(nt, op, a, b=None, clamp=False):
    n = node(nt, 'ShaderNodeMath', operation=op, use_clamp=clamp)
    put(nt, n.inputs[0], a)
    if b is not None: put(nt, n.inputs[1], b)
    return n.outputs[0]
def mr(nt, s, a, b, c=0.0, d=1.0, smooth=False):
    n = node(nt, 'ShaderNodeMapRange', clamp=True)
    if smooth: n.interpolation_type = 'SMOOTHSTEP'
    put(nt, n.inputs['Value'], s); n.inputs['From Min'].default_value = a; n.inputs['From Max'].default_value = b
    n.inputs['To Min'].default_value = c; n.inputs['To Max'].default_value = d
    return n.outputs['Result']
def mix(nt, f, a, b, blend='MIX'):
    n = node(nt, 'ShaderNodeMix', data_type='RGBA', blend_type=blend, clamp_result=True)
    put(nt, n.inputs[0], f); put(nt, n.inputs[6], a); put(nt, n.inputs[7], b)
    return n.outputs[2]
def sep(nt, v):
    n = node(nt, 'ShaderNodeSeparateXYZ'); put(nt, n.inputs[0], v); return n.outputs[0], n.outputs[1], n.outputs[2]
def comb(nt, x, y, z):
    n = node(nt, 'ShaderNodeCombineXYZ')
    for i, v in enumerate((x, y, z)): put(nt, n.inputs[i], v)
    return n.outputs[0]
def noise(nt, vec, scale, detail=3.0, rough=0.55):
    n = node(nt, 'ShaderNodeTexNoise'); put(nt, n.inputs['Vector'], vec)
    n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough
    return n.outputs['Fac']
def pos(nt): return node(nt, 'ShaderNodeNewGeometry').outputs['Position']
def newmat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; m.node_tree.nodes.clear(); return m, m.node_tree
def out(nt, surf=None, vol=None):
    o = node(nt, 'ShaderNodeOutputMaterial')
    if surf is not None: link(nt, surf, o.inputs['Surface'])
    if vol is not None: link(nt, vol, o.inputs['Volume'])
def aov(nt, val):
    n = node(nt, 'ShaderNodeOutputAOV'); n.aov_name = 'wt'; put(nt, n.inputs['Value'], val)
def link_obj(ob, coll=None): (coll or sc.collection).objects.link(ob); return ob

def mesh_obj(name, verts, faces, mats=(), uvs=None, smooth=False):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    if uvs is not None:
        lay = me.uv_layers.new(name='UVMap'); vi = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', vi)
        lay.data.foreach_set('uv', np.asarray(uvs, np.float32)[vi].ravel())
    me.polygons.foreach_set('use_smooth', np.full(len(me.polygons), smooth)); me.update()
    for m in mats: me.materials.append(m)
    return link_obj(bpy.data.objects.new(name, me))

def box(name, x0, x1, y0, y1, z0, z1, mat=None, bevel=0.0):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = mesh_obj(name, v, f, [mat] if mat else [])
    if bevel > 0:
        b = ob.modifiers.new('bev', 'BEVEL'); b.width = bevel; b.segments = 2
    return ob

def tex(nt, path, vec, noncolor=False):
    im = bpy.data.images.load(path, check_existing=True)
    if noncolor: im.colorspace_settings.name = 'Non-Color'
    t = node(nt, 'ShaderNodeTexImage', image=im, interpolation='Linear'); put(nt, t.inputs[0], vec)
    return t.outputs['Color']

def find(folder, key):
    for f in sorted(os.listdir(folder)):
        if key.lower() in f.lower() and f.lower().endswith(('.jpg', '.png', '.exr')): return os.path.join(folder, f)
    return None

def scanned(name, folder, uvfun, size, rot=0.0, tint=(1, 1, 1), value=1.0, wet=None, rough_mul=1.0, bump=0.6,
            extra=None, disp=0.0):
    """A scanned PBR set at true scale in metres; two samplings mixed by noise to break the tiling.
    uvfun(nt) gives a 2D coordinate in metres. wet(nt) gives a 0..1 wetness (darker, glossier, coated)."""
    m, nt = newmat(name)
    col_p = find(folder, '_Color') or find(folder, '_diff'); rgh_p = find(folder, '_Roughness') or find(folder, '_rough')
    nrm_p = find(folder, '_NormalGL') or find(folder, 'nor_gl'); dsp_p = find(folder, '_Displacement') or find(folder, '_disp')
    base = uvfun(nt)
    def coord(off, ang):
        mp = node(nt, 'ShaderNodeMapping'); put(nt, mp.inputs['Vector'], base)
        mp.inputs['Rotation'].default_value = (0, 0, rot + ang); mp.inputs['Location'].default_value = (off, off * 0.7, 0)
        mp.inputs['Scale'].default_value = (1 / size, 1 / size, 1)
        return mp.outputs[0]
    c1, c2 = coord(0.0, 0.0), coord(0.37, 0.0)
    f = mr(nt, noise(nt, base, 0.35, 2.0), 0.42, 0.58, smooth=True)
    col = mix(nt, f, tex(nt, col_p, c1), tex(nt, col_p, c2))
    col = mix(nt, 1.0, col, (tint[0] * value, tint[1] * value, tint[2] * value), 'MULTIPLY')
    rg = M(nt, 'MULTIPLY', mix(nt, f, tex(nt, rgh_p, c1, True), tex(nt, rgh_p, c2, True)), rough_mul) if rgh_p else 0.7
    if isinstance(rg, bpy.types.NodeSocket): rg = sep(nt, rg)[0]
    nm = None
    if nrm_p:
        nmap = node(nt, 'ShaderNodeNormalMap'); nmap.inputs['Strength'].default_value = 1.0
        put(nt, nmap.inputs['Color'], mix(nt, f, tex(nt, nrm_p, c1, True), tex(nt, nrm_p, c2, True))); nm = nmap.outputs[0]
    if dsp_p:
        h = sep(nt, mix(nt, f, tex(nt, dsp_p, c1, True), tex(nt, dsp_p, c2, True)))[0]
        if extra is not None: h = M(nt, 'ADD', h, extra(nt))
        bp = node(nt, 'ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; bp.inputs['Distance'].default_value = 0.02
        put(nt, bp.inputs['Height'], h)
        if disp > 0:
            dn = node(nt, 'ShaderNodeDisplacement'); dn.inputs['Scale'].default_value = disp; dn.inputs['Midlevel'].default_value = 0.5
            put(nt, dn.inputs['Height'], h); DISP.append((m, dn.outputs[0]))
        if nm is not None: link(nt, nm, bp.inputs['Normal'])
        nm = bp.outputs[0]
    bsdf = node(nt, 'ShaderNodeBsdfPrincipled')
    if wet is not None:
        w = wet(nt)
        col = mix(nt, M(nt, 'MULTIPLY', w, 0.55), col, (0, 0, 0))
        put(nt, bsdf.inputs['Roughness'], M(nt, 'ADD', M(nt, 'MULTIPLY', rg, M(nt, 'SUBTRACT', 1.0, w)), M(nt, 'MULTIPLY', w, 0.03)))
        put(nt, bsdf.inputs['Coat Weight'], M(nt, 'MULTIPLY', w, 0.9)); bsdf.inputs['Coat Roughness'].default_value = 0.03
        aov(nt, mr(nt, w, 0.85, 0.95))
    else:
        put(nt, bsdf.inputs['Roughness'], rg)
    put(nt, bsdf.inputs['Base Color'], col)
    if nm is not None: link(nt, nm, bsdf.inputs['Normal'])
    bsdf.inputs['Specular IOR Level'].default_value = 0.5
    o_ = node(nt, 'ShaderNodeOutputMaterial'); link(nt, bsdf.outputs[0], o_.inputs['Surface'])
    for (mm, dsock) in DISP:
        if mm is m: link(nt, dsock, o_.inputs['Displacement']); m.displacement_method = 'BOTH'
    return m

DISP = []
def micro(ob, rate=1.0):
    """true micro-displacement: adaptive subdivision diced to about a pixel near the lens"""
    sc.cycles.feature_set = 'EXPERIMENTAL'; sc.cycles.dicing_rate = rate; sc.cycles.offscreen_dicing_scale = 8.0
    md = ob.modifiers.new('sub', 'SUBSURF'); md.subdivision_type = 'SIMPLE'
    try: ob.cycles.use_adaptive_subdivision = True
    except Exception: md.render_levels = 6

def uv_wall(nt):   # a wall in the XZ plane: u along the wall, v up it
    x, y, z = sep(nt, pos(nt)); return comb(nt, x, z, 0.0)
def uv_floor(nt):
    x, y, z = sep(nt, pos(nt)); return comb(nt, x, y, 0.0)

def plain(name, col, rough, metal=0.0, coat=0.0):
    m, nt = newmat(name); b = node(nt, 'ShaderNodeBsdfPrincipled')
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal; b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.05
    out(nt, b.outputs[0]); return m

def anodised():
    """dark anodised aluminium: brushed grain along the rails, a thin wet coat"""
    if 'anodised' in bpy.data.materials: return bpy.data.materials['anodised']
    m, nt = newmat('anodised'); b = node(nt, 'ShaderNodeBsdfPrincipled')
    x, y, z = sep(nt, pos(nt))
    grain = noise(nt, comb(nt, M(nt, 'MULTIPLY', x, 3.0), M(nt, 'MULTIPLY', y, 400.0), M(nt, 'MULTIPLY', z, 400.0)), 1.0, 2.0, 0.5)
    b.inputs['Base Color'].default_value = (0.022, 0.025, 0.03, 1); b.inputs['Metallic'].default_value = 0.9
    put(nt, b.inputs['Roughness'], M(nt, 'ADD', 0.2, M(nt, 'MULTIPLY', grain, 0.14)))
    b.inputs['Anisotropic'].default_value = 0.6
    b.inputs['Coat Weight'].default_value = 0.5; b.inputs['Coat Roughness'].default_value = 0.04
    bp = node(nt, 'ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.08; bp.inputs['Distance'].default_value = 0.0005
    put(nt, bp.inputs['Height'], grain); link(nt, bp.outputs[0], b.inputs['Normal'])
    out(nt, b.outputs[0]); return m

def water_mat(name='water'):
    m, nt = newmat(name); b = node(nt, 'ShaderNodeBsdfPrincipled')
    b.inputs['Roughness'].default_value = 0.0; b.inputs['Transmission Weight'].default_value = 1.0; b.inputs['IOR'].default_value = 1.33
    out(nt, b.outputs[0]); return m

# ---------------------------------------------------------------- the lightbox
PW, PH_ = 1.16, 1.74
print_info = json.load(open(os.path.splitext(PRINT)[0] + '.json')) if os.path.exists(os.path.splitext(PRINT)[0] + '.json') else \
    {'mark': [0.35, 0.215, 0.65, 0.415]}
GLOW = (0.50, 0.66, 1.0)
E_PRINT = arg('--print-e', 1.15)
GLOW_K = arg('--glow', 1.0)

def lightbox(cx, cy, z0, stand=False, glow=60.0, beam=0.10):
    """the print's face at y = cy, its foot at z0; on a wall (case into the wall behind) or freestanding on two legs.
    Returns the print object (for its corners) and the area light."""
    FW, D = 0.045, (0.075 if not stand else 0.14)
    x0, x1, z1 = cx - PW / 2, cx + PW / 2, z0 + PH_
    yf = cy - 0.012                       # glass a little in front of the print
    m_case = anodised()
    parts = [box('case_t', x0 - FW, x1 + FW, yf - 0.01, cy + D, z1, z1 + FW, m_case, 0.004),
             box('case_b', x0 - FW, x1 + FW, yf - 0.01, cy + D, z0 - FW, z0, m_case, 0.004),
             box('case_l', x0 - FW, x0, yf - 0.01, cy + D, z0, z1, m_case, 0.004),
             box('case_r', x1, x1 + FW, yf - 0.01, cy + D, z0, z1, m_case, 0.004),
             box('case_back', x0, x1, cy + D - 0.01, cy + D, z0, z1, m_case)]
    if stand:
        for lx in (x0 + 0.12, x1 - 0.12):
            parts.append(box('leg', lx - 0.02, lx + 0.02, cy + D * 0.3, cy + D * 0.7, -0.05, z0 - FW, m_case, 0.003))
            parts.append(box('foot', lx - 0.05, lx + 0.05, cy - 0.16, cy + D + 0.16, -0.02, 0.02, m_case, 0.004))
    # a thin rubber seal round the print, two fixing bolts on the top rail, the feed cable at the foot
    m_seal = plain('rubber', (0.008, 0.008, 0.009), 0.55)
    sw = 0.006
    parts += [box('seal_t', x0, x1, yf + 0.001, cy, z1 - sw, z1, m_seal), box('seal_b', x0, x1, yf + 0.001, cy, z0, z0 + sw, m_seal),
              box('seal_l', x0, x0 + sw, yf + 0.001, cy, z0, z1, m_seal), box('seal_r', x1 - sw, x1, yf + 0.001, cy, z0, z1, m_seal)]
    m_bolt = plain('bolt', (0.25, 0.26, 0.28), 0.3, metal=1.0)
    for bx_ in (x0 + 0.12, x1 - 0.12):
        bm_ = bmesh.new(); bmesh.ops.create_cone(bm_, cap_ends=True, segments=16, radius1=0.0065, radius2=0.0065, depth=0.004)
        me_ = bpy.data.meshes.new('bolt'); bm_.to_mesh(me_); bm_.free(); me_.materials.append(m_bolt)
        bo = link_obj(bpy.data.objects.new('bolt', me_)); bo.location = (bx_, yf - 0.012, z1 + FW / 2); bo.rotation_euler = (math.radians(90), 0, 0)
        parts.append(bo)
    cb = bpy.data.curves.new('feed', 'CURVE'); cb.dimensions = '3D'; cb.bevel_depth = 0.0045; cb.bevel_resolution = 2
    sp = cb.splines.new('BEZIER')
    if stand:
        pts = [(x1 - 0.12, cy + D * 0.5, 0.06), (x1 - 0.05, cy + 0.5, 0.005), (x1 + 0.6, cy + 2.0, 0.005), (x1 + 2.5, cy + 4.5, 0.005)]
    else:
        pts = [(x1 - 0.1, cy + D * 0.5, z0 - FW), (x1 - 0.02, cy + D * 0.6, 0.08), (x1 + 0.4, -0.008, 0.008), (x1 + 6.0, -0.008, 0.008)]
    sp.bezier_points.add(len(pts) - 1)
    for i, pt in enumerate(pts):
        bp_ = sp.bezier_points[i]; bp_.co = pt; bp_.handle_left_type = bp_.handle_right_type = 'AUTO'
    cbo = link_obj(bpy.data.objects.new('feed', cb)); cb.materials.append(plain('cable', (0.01, 0.01, 0.011), 0.35, coat=0.6))
    parts.append(cbo)
    for p in parts: p.pass_index = 3
    # the print: emission from the image, seen by the lens and in reflections; the area light does the lighting
    img = bpy.data.images.load(PRINT, check_existing=True)
    m, nt = newmat('print')
    t = node(nt, 'ShaderNodeTexImage', image=img, interpolation='Cubic', extension='EXTEND')
    put(nt, t.inputs[0], node(nt, 'ShaderNodeTexCoord').outputs['UV'])
    e = node(nt, 'ShaderNodeEmission'); link(nt, t.outputs[0], e.inputs['Color'])
    u_, v_, _ = sep(nt, node(nt, 'ShaderNodeTexCoord').outputs['UV'])
    edge = M(nt, 'MINIMUM', M(nt, 'MULTIPLY', M(nt, 'MINIMUM', u_, M(nt, 'SUBTRACT', 1.0, u_)), PW), M(nt, 'MULTIPLY', M(nt, 'MINIMUM', v_, M(nt, 'SUBTRACT', 1.0, v_)), PH_))
    put(nt, e.inputs['Strength'], M(nt, 'MULTIPLY', mr(nt, edge, 0.0, 0.07, 0.82, 1.0, smooth=True), E_PRINT))   # the light falls off at the edges
    out(nt, e.outputs[0])
    m.cycles.emission_sampling = 'NONE'
    pr = mesh_obj('print', [(x0, cy, z0), (x1, cy, z0), (x1, cy, z1), (x0, cy, z1)], [(0, 1, 2, 3)], [m],
                  uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    pr.visible_diffuse = False; pr.visible_shadow = False; pr.visible_volume_scatter = False; pr.pass_index = 1
    # wet glass: a clear sheet, drops and short runs
    gm, gnt = newmat('glass')
    tr = node(gnt, 'ShaderNodeBsdfTransparent'); gl = node(gnt, 'ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.01
    fr = node(gnt, 'ShaderNodeFresnel'); fr.inputs['IOR'].default_value = 1.52
    mx = node(gnt, 'ShaderNodeMixShader'); link(gnt, fr.outputs[0], mx.inputs[0]); link(gnt, tr.outputs[0], mx.inputs[1]); link(gnt, gl.outputs[0], mx.inputs[2])
    out(gnt, mx.outputs[0])
    g = mesh_obj('glass', [(x0, yf, z0), (x1, yf, z0), (x1, yf, z1), (x0, yf, z1)], [(0, 1, 2, 3)], [gm]); g.pass_index = 2
    g.visible_shadow = False
    wm = water_mat('drops')
    V, F = [], []
    nd = 90 if LITE else arg('--drops', 380)
    for _ in range(nd):
        x = rng.uniform(x0 + 0.01, x1 - 0.01); z = rng.uniform(z0 + 0.01, z1 - 0.01)
        r = rng.uniform(0.0016, 0.0045) * (1.0 if rng.random() < 0.88 else 1.7)
        run = rng.random() < 0.12
        n = 8; o = len(V)
        L = rng.uniform(0.03, 0.14) if run else 0.0
        for k in range(n):
            a = 2 * math.pi * k / n
            V.append((x + r * math.cos(a), yf - 0.0005, z + r * 1.1 * math.sin(a) - (L if math.sin(a) > 0 else 0) * 0))
        V.append((x, yf - r * 0.35, z)); c = len(V) - 1
        for k in range(n): F.append((o + k, o + (k + 1) % n, c))
        if run:
            # a short run above the drop: the trail it left, thinning upwards
            o2 = len(V); w0 = r * 0.55
            V += [(x - w0, yf - 0.0004, z), (x + w0, yf - 0.0004, z), (x + 0.0004, yf - 0.0003, z + L), (x - 0.0004, yf - 0.0003, z + L)]
            F.append((o2, o2 + 1, o2 + 2, o2 + 3))
    dr = mesh_obj('glass_drops', V, F, [wm], smooth=True); dr.pass_index = 2; dr.visible_shadow = False
    # the light the print gives: an area light on its face, with a little spread forward
    la = bpy.data.lights.new('print_light', 'AREA'); la.shape = 'RECTANGLE'; la.size = PW; la.size_y = PH_
    la.energy = glow * GLOW_K; la.color = GLOW; la.spread = math.radians(150)
    lo = link_obj(bpy.data.objects.new('print_light', la)); lo.location = (cx, yf - 0.02, z0 + PH_ / 2)
    lo.rotation_euler = (math.radians(-90), 0, 0)     # facing -Y, out towards the lens
    # the light pouring out into the air: denser air only in front of the print, thinning with distance
    if beam > 0:
        bx = box('beam_air', cx - 2.2, cx + 2.2, cy - 3.2, yf - 0.03, -0.4, z1 + 1.6)
        bm, bnt = newmat('beam_air'); pv = node(bnt, 'ShaderNodeVolumePrincipled')
        pv.inputs['Color'].default_value = (0.9, 0.94, 1.0, 1); pv.inputs['Anisotropy'].default_value = 0.45
        x, y, z = sep(bnt, pos(bnt))
        d = M(bnt, 'ADD', M(bnt, 'ABSOLUTE', M(bnt, 'SUBTRACT', y, cy)), M(bnt, 'MULTIPLY', M(bnt, 'ABSOLUTE', M(bnt, 'SUBTRACT', x, cx)), 0.5))
        fall = M(bnt, 'EXPONENT', M(bnt, 'MULTIPLY', d, -1.1))
        var = mr(bnt, noise(bnt, comb(bnt, M(bnt, 'MULTIPLY', x, 0.8), y, M(bnt, 'MULTIPLY', z, 0.5)), 0.9, 3.0), 0.3, 0.75, 0.35, 1.25)
        put(bnt, pv.inputs['Density'], M(bnt, 'MULTIPLY', M(bnt, 'MULTIPLY', fall, var), beam))
        out(bnt, None, pv.outputs['Volume']); bx.data.materials.append(bm)
        bx.visible_shadow = False
    return pr, lo, (x0 - FW, x1 + FW, z0 - FW, z1 + FW, cy)

# ---------------------------------------------------------------- air
def ground_mist(x0, x1, y0, y1, dens, height, top=None, col=(0.62, 0.74, 1.0), aniso=0.3, drift=1.0):
    top = top or height * 4
    bx = box('ground_mist', x0, x1, y0, y1, -0.35, top)
    m, nt = newmat('ground_mist'); pv = node(nt, 'ShaderNodeVolumePrincipled')
    pv.inputs['Color'].default_value = (*col, 1); pv.inputs['Anisotropy'].default_value = aniso
    P = pos(nt); x, y, z = sep(nt, P)
    hf = M(nt, 'EXPONENT', M(nt, 'MULTIPLY', M(nt, 'MAXIMUM', z, 0.0), -1.0 / height))
    stretched = comb(nt, M(nt, 'MULTIPLY', x, 0.35 * drift), y, M(nt, 'MULTIPLY', z, 1.6))
    n = mr(nt, noise(nt, stretched, 0.55, 3.0, 0.55), 0.3, 0.75, 0.15, 1.0)
    put(nt, pv.inputs['Density'], M(nt, 'MULTIPLY', M(nt, 'MULTIPLY', hf, n), dens))
    out(nt, None, pv.outputs['Volume']); bx.data.materials.append(m)
    bx.visible_shadow = False
    return bx

def haze(name, x0, x1, y0, y1, z0, z1, dens, col=(0.8, 0.88, 1.0), aniso=0.2, zfall=0.0):
    bx = box(name, x0, x1, y0, y1, z0, z1)
    m, nt = newmat(name); pv = node(nt, 'ShaderNodeVolumePrincipled')
    pv.inputs['Color'].default_value = (*col, 1); pv.inputs['Anisotropy'].default_value = aniso
    if zfall > 0:
        x, y, z = sep(nt, pos(nt))
        put(nt, pv.inputs['Density'], M(nt, 'MULTIPLY', M(nt, 'EXPONENT', M(nt, 'MULTIPLY', M(nt, 'MAXIMUM', z, 0.0), -1.0 / zfall)), dens))
    else:
        pv.inputs['Density'].default_value = dens
    out(nt, None, pv.outputs['Volume']); bx.data.materials.append(m)
    bx.visible_shadow = False
    return bx

def rain(n, x0, x1, y0, y1, z0, z1, cam_loc, length=(0.12, 0.26), slant=0.02, alpha=0.45):
    """streaks as thin strips turned to the lens; they catch the print's light where they cross it"""
    m, nt = newmat('rain')
    tr = node(nt, 'ShaderNodeBsdfTransparent'); tl = node(nt, 'ShaderNodeBsdfTranslucent'); tl.inputs[0].default_value = (0.9, 0.95, 1.0, 1)
    gl = node(nt, 'ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.2
    m1 = node(nt, 'ShaderNodeMixShader'); m1.inputs[0].default_value = 0.35; link(nt, tl.outputs[0], m1.inputs[1]); link(nt, gl.outputs[0], m1.inputs[2])
    m2 = node(nt, 'ShaderNodeMixShader'); m2.inputs[0].default_value = alpha; link(nt, tr.outputs[0], m2.inputs[1]); link(nt, m1.outputs[0], m2.inputs[2])
    out(nt, m2.outputs[0])
    P = np.stack([rng.uniform(x0, x1, n), rng.uniform(y0, y1, n), rng.uniform(z0, z1, n)], 1)
    L = rng.uniform(*length, n); wd = rng.uniform(0.0007, 0.0014, n) * (1 + np.linalg.norm(P - np.array(cam_loc), axis=1) * 0.06)
    up = np.stack([np.full(n, slant), np.zeros(n), np.ones(n)], 1); up /= np.linalg.norm(up, axis=1)[:, None]
    to = np.array(cam_loc)[None] - P; side = np.cross(up, to); side /= np.linalg.norm(side, axis=1)[:, None]
    a = P - side * wd[:, None]; b = P + side * wd[:, None]; c = b + up * L[:, None]; d = a + up * L[:, None]
    V = np.concatenate([a, b, c, d]); idx = np.arange(n)
    F = np.stack([idx, idx + n, idx + 2 * n, idx + 3 * n], 1)
    ob = mesh_obj('rain', V, F, [m]); ob.visible_shadow = False
    return ob

# ---------------------------------------------------------------- scans
def load_objs(blend, names):
    with bpy.data.libraries.load(blend, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if (names is None or n in names)]
    base = os.path.dirname(blend)
    for im in bpy.data.images:
        if im.filepath and not os.path.exists(bpy.path.abspath(im.filepath)):
            cand = os.path.join(base, 'textures', os.path.basename(im.filepath))
            if os.path.exists(cand): im.filepath = cand
    res = []
    for o in dst.objects:
        if o is None: continue
        o.location = (0, 0, 0); o.rotation_euler = (0, 0, 0); o.scale = (1, 1, 1); o.parent = None
        res.append(o)
    return sorted(res, key=lambda o: o.name)

def libcoll(name, objs):
    c = bpy.data.collections.new(name); sc.collection.children.link(c)
    for o in objs:
        for uc in list(o.users_collection): uc.objects.unlink(o)
        c.objects.link(o)
    c.hide_render = True
    return c

def recolour(m, mode, glow=0.0):
    """petals only. 'blue': white petals and the scan's mauve petals to a clean pale blue; 'white': to a cool white.
    Leaves and stems are pulled cool and dark so the palette holds. Works on a Principled Base Color or on the
    Poly Haven group's Diffuse and Translucency inputs."""
    nt = m.node_tree
    targets = []
    for n in nt.nodes:
        if n.bl_idname == 'ShaderNodeBsdfPrincipled' and n.inputs['Base Color'].is_linked: targets.append(n.inputs['Base Color'])
        if n.bl_idname == 'ShaderNodeGroup':
            for i in n.inputs:
                if i.is_linked and i.name in ('Diffuse', 'Translucency', 'Base Color', 'Albedo', 'Color'): targets.append(i)
    tint = (0.86, 0.92, 1.0) if mode == 'white' else (0.55, 0.78, 1.0)
    for sock in targets:
        src = sock.links[0].from_socket
        hsv = node(nt, 'ShaderNodeSeparateColor', mode='HSV'); link(nt, src, hsv.inputs['Color'])
        white = M(nt, 'MULTIPLY', mr(nt, hsv.outputs['Blue'], 0.5, 0.72), mr(nt, hsv.outputs['Green'], 0.35, 0.15))
        mauve = M(nt, 'MULTIPLY', M(nt, 'MULTIPLY', mr(nt, hsv.outputs['Red'], 0.72, 0.8), mr(nt, hsv.outputs['Red'], 0.97, 0.92)),
                  mr(nt, hsv.outputs['Green'], 0.2, 0.35))
        petal = M(nt, 'MAXIMUM', white, mauve)
        cc = node(nt, 'ShaderNodeCombineColor', mode='RGB')
        lum = M(nt, 'MINIMUM', M(nt, 'ADD', M(nt, 'MULTIPLY', hsv.outputs['Blue'], 0.5), 0.55), 1.0)
        for i, k in enumerate(tint): link(nt, M(nt, 'MULTIPLY', lum, k), cc.inputs[i])
        leaf = mix(nt, 1.0, src, (0.32, 0.46, 0.72), 'MULTIPLY')
        link(nt, mix(nt, petal, leaf, cc.outputs[0]), sock)
        if glow > 0 and sock.name in ('Diffuse', 'Base Color', 'Albedo', 'Color'):
            # a soft light from within the petals only (the founder's luminous flowers): added to the surface
            mo = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial' and n.inputs['Surface'].is_linked)
            surf = mo.inputs['Surface'].links[0].from_socket
            em = node(nt, 'ShaderNodeEmission'); link(nt, cc.outputs[0], em.inputs['Color'])
            put(nt, em.inputs['Strength'], M(nt, 'MULTIPLY', M(nt, 'POWER', petal, 1.5), glow))
            ad = node(nt, 'ShaderNodeAddShader'); link(nt, surf, ad.inputs[0]); link(nt, em.outputs[0], ad.inputs[1])
            link(nt, ad.outputs[0], mo.inputs['Surface'])
            m.cycles.emission_sampling = 'NONE'

def instances(name, coll, P, R, Sc, pick):
    m = len(P)
    if m == 0: return None
    me = bpy.data.meshes.new(name); me.vertices.add(m); me.vertices.foreach_set('co', np.asarray(P, np.float32).ravel())
    for an, data, tp in (('rot', np.asarray(R, np.float32), 'FLOAT_VECTOR'), ('scl', np.asarray(Sc, np.float32), 'FLOAT_VECTOR'),
                         ('pick', np.asarray(pick, np.int32), 'INT')):
        at = me.attributes.new(an, tp, 'POINT'); at.data.foreach_set('vector' if tp == 'FLOAT_VECTOR' else 'value', data.ravel())
    ob = link_obj(bpy.data.objects.new(name, me))
    ng = bpy.data.node_groups.new(name + '_gn', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    gi = ng.nodes.new('NodeGroupInput'); go = ng.nodes.new('NodeGroupOutput')
    m2p = ng.nodes.new('GeometryNodeMeshToPoints')
    ci = ng.nodes.new('GeometryNodeCollectionInfo'); ci.inputs['Collection'].default_value = coll
    ci.inputs['Separate Children'].default_value = True; ci.inputs['Reset Children'].default_value = True
    iop = ng.nodes.new('GeometryNodeInstanceOnPoints'); iop.inputs['Pick Instance'].default_value = True
    na = {}
    for an, dt in (('rot', 'FLOAT_VECTOR'), ('scl', 'FLOAT_VECTOR'), ('pick', 'INT')):
        nn = ng.nodes.new('GeometryNodeInputNamedAttribute'); nn.data_type = dt; nn.inputs['Name'].default_value = an; na[an] = nn
    L = ng.links
    L.new(gi.outputs[0], m2p.inputs['Mesh']); L.new(m2p.outputs['Points'], iop.inputs['Points'])
    L.new(ci.outputs[0], iop.inputs['Instance']); L.new(na['pick'].outputs['Attribute'], iop.inputs['Instance Index'])
    L.new(na['rot'].outputs['Attribute'], iop.inputs['Rotation']); L.new(na['scl'].outputs['Attribute'], iop.inputs['Scale'])
    L.new(iop.outputs['Instances'], go.inputs[0])
    ob.modifiers.new('scatter', 'NODES').node_group = ng
    print(name, m, 'instances')
    return ob

def flowers(kind='blue', glow=0.0):
    """Poly Haven heliophila (three sizes) and periwinkle, recoloured; returns the library and its index ranges"""
    helio = load_objs(os.path.join(PH, 'flower_heliophila', 'flower_heliophila_2k.blend'),
                      ['flower_heliophila_small_LOD2', 'flower_heliophila_medium_LOD2', 'flower_heliophila_large_LOD2'])
    for mm in {o.data.materials[0] for o in helio}: recolour(mm, kind, glow)
    peri = load_objs(os.path.join(PH, 'periwinkle_plant', 'periwinkle_plant_1k.blend'),
                     ['periwinkle_plant_0%d_LOD3' % i for i in range(1, 6)])
    if peri: recolour(peri[0].data.materials[0], 'blue', glow * 0.6)
    return libcoll('flower_lib_' + kind, helio + peri), len(helio), len(peri)

# ---------------------------------------------------------------- camera and the poster's keep-out
CAM = None
def camera(loc, yaw=0.0, pitch=0.0, lens=28.0, shift_y=0.0, fstop=4.0, focus=None, clip=4000.0):
    global CAM
    cd = bpy.data.cameras.new('cam'); cam = link_obj(bpy.data.objects.new('cam', cd)); sc.camera = cam
    cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.lens = lens; cd.shift_y = shift_y
    cd.clip_start = 0.05; cd.clip_end = clip
    cam.location = loc; cam.rotation_euler = (math.radians(90 + pitch), 0, math.radians(yaw))
    cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
    cd.dof.focus_distance = focus if focus else 6.0
    CAM = cam
    return cam

def project(P):
    from bpy_extras.object_utils import world_to_camera_view
    bpy.context.view_layer.update()
    return np.array([tuple(world_to_camera_view(sc, CAM, Vector(p))) for p in P])

def keep_clear(P, hgt, rect, margin=0.02):
    """drop any plant whose top or base would stand in front of the lightbox in the lens's view"""
    x0, x1, z0, z1, cy = rect
    q = np.array([[x0, cy, z0], [x1, cy, z1]]); qq = project(q)
    u0, u1 = sorted(qq[:, 0]); v0, v1 = sorted(qq[:, 1])
    tops = P + np.stack([np.zeros(len(P)), np.zeros(len(P)), hgt], 1)
    a, b = project(P), project(tops)
    def inside(p): return (p[:, 0] > u0 - margin) & (p[:, 0] < u1 + margin) & (p[:, 1] > v0 - margin * 1.6) & (p[:, 1] < v1 + margin)
    seg = np.zeros(len(P), bool)
    for t in np.linspace(0, 1, 5): seg |= inside(a * (1 - t) + b * t)
    return ~(seg & (P[:, 1] < cy + 0.2))

# ---------------------------------------------------------------- world
def world(hdr=None, strength=0.05, tint=(0.35, 0.5, 1.0), rot=0.0, flat=(0.004, 0.006, 0.014)):
    wm = bpy.data.worlds.new('w'); sc.world = wm; wm.use_nodes = True; nt = wm.node_tree; nt.nodes.clear()
    bg = node(nt, 'ShaderNodeBackground'); o = node(nt, 'ShaderNodeOutputWorld'); link(nt, bg.outputs[0], o.inputs['Surface'])
    if hdr:
        et = node(nt, 'ShaderNodeTexEnvironment', image=bpy.data.images.load(hdr))
        mp = node(nt, 'ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, rot)
        link(nt, node(nt, 'ShaderNodeTexCoord').outputs['Generated'], mp.inputs[0]); link(nt, mp.outputs[0], et.inputs[0])
        # cooled to cobalt: keep the HDRI's light and shape, take its colour from the night
        bw = node(nt, 'ShaderNodeRGBToBW'); link(nt, et.outputs[0], bw.inputs[0])
        c = mix(nt, 0.95, et.outputs[0], comb(nt, M(nt, 'MULTIPLY', bw.outputs[0], tint[0]), M(nt, 'MULTIPLY', bw.outputs[0], tint[1]), M(nt, 'MULTIPLY', bw.outputs[0], tint[2])))
        link(nt, c, bg.inputs['Color'])
    else:
        bg.inputs['Color'].default_value = (*flat, 1)
    bg.inputs['Strength'].default_value = strength

def sun(name, direction, energy, col, angle=1.0, receivers=None):
    l = bpy.data.lights.new(name, 'SUN'); l.energy = energy; l.color = col; l.angle = math.radians(angle)
    o = link_obj(bpy.data.objects.new(name, l))
    o.rotation_euler = Vector(direction).normalized().to_track_quat('-Z', 'Y').to_euler()
    if receivers: only_light(o, receivers)
    return o

def area(name, loc, target, energy, col, size=4.0, receivers=None, visible=False):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.color = col; l.size = size
    o = link_obj(bpy.data.objects.new(name, l)); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    o.visible_camera = visible; o.visible_glossy = visible
    if receivers: only_light(o, receivers)
    return o

def only_light(light_ob, objs):
    """light linking: this light falls only on these objects"""
    c = bpy.data.collections.new(light_ob.name + '_rx')
    for ob in objs: c.objects.link(ob)
    light_ob.light_linking.receiver_collection = c

# ---------------------------------------------------------------- shared ground pieces
def wet_slabs(name, x0, x1, y0, y1, slab=(0.9, 0.6), puddle=0.55, flood=0.0, z=0.0, disp=0.0):
    """big precast slabs, wet, with water standing where they have settled; scanned concrete surface"""
    def wetf(nt):
        x, y, zz = sep(nt, pos(nt)); yy = M(nt, 'MULTIPLY', y, -1.0)
        row = M(nt, 'FLOOR', M(nt, 'DIVIDE', yy, slab[1]))
        off = M(nt, 'MULTIPLY', M(nt, 'SUBTRACT', row, M(nt, 'MULTIPLY', M(nt, 'FLOOR', M(nt, 'MULTIPLY', row, 0.5)), 2.0)), slab[0] / 2)
        cu = M(nt, 'DIVIDE', M(nt, 'ADD', x, off), slab[0]); fu = M(nt, 'FRACT', cu); fv = M(nt, 'FRACT', M(nt, 'DIVIDE', yy, slab[1]))
        j = M(nt, 'MINIMUM', M(nt, 'MULTIPLY', M(nt, 'MINIMUM', fu, M(nt, 'SUBTRACT', 1.0, fu)), slab[0]),
              M(nt, 'MULTIPLY', M(nt, 'MINIMUM', fv, M(nt, 'SUBTRACT', 1.0, fv)), slab[1]))
        joint = mr(nt, j, 0.008, 0.002)
        pn = noise(nt, comb(nt, M(nt, 'MULTIPLY', x, 0.6), M(nt, 'MULTIPLY', y, 0.9), 0.0), 1.0, 4.0, 0.55)
        lvl = M(nt, 'ADD', M(nt, 'ADD', pn, M(nt, 'MULTIPLY', joint, 0.1)), flood)
        return M(nt, 'ADD', M(nt, 'MULTIPLY', mr(nt, lvl, puddle - 0.2, puddle - 0.02), 0.6), mr(nt, lvl, puddle, puddle + 0.04), clamp=True)
    def joints(nt):
        x, y, zz = sep(nt, pos(nt)); yy = M(nt, 'MULTIPLY', y, -1.0)
        row = M(nt, 'FLOOR', M(nt, 'DIVIDE', yy, slab[1]))
        off = M(nt, 'MULTIPLY', M(nt, 'SUBTRACT', row, M(nt, 'MULTIPLY', M(nt, 'FLOOR', M(nt, 'MULTIPLY', row, 0.5)), 2.0)), slab[0] / 2)
        fu = M(nt, 'FRACT', M(nt, 'DIVIDE', M(nt, 'ADD', x, off), slab[0])); fv = M(nt, 'FRACT', M(nt, 'DIVIDE', yy, slab[1]))
        j = M(nt, 'MINIMUM', M(nt, 'MULTIPLY', M(nt, 'MINIMUM', fu, M(nt, 'SUBTRACT', 1.0, fu)), slab[0]),
              M(nt, 'MULTIPLY', M(nt, 'MINIMUM', fv, M(nt, 'SUBTRACT', 1.0, fv)), slab[1]))
        return M(nt, 'MULTIPLY', mr(nt, j, 0.008, 0.002), -0.6)
    m = scanned(name, os.path.join(ACG, 'Concrete017'), uv_floor, 2.2, tint=(0.62, 0.68, 0.8), value=0.45, wet=wetf, extra=joints, disp=disp)
    ob = mesh_obj(name, [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], [(0, 1, 2, 3)], [m])
    if disp > 0: micro(ob, arg('--dice', 1.0))
    return ob

def board_wall_mat(name, panel=(2.4, 1.2), value=0.42):
    """board-marked precast concrete: the ambientCG scan (boards turned to run level) with the panel joints,
    tie holes and the runs below them, damp rising from the foot, rain darkening it all"""
    def ties(nt):
        x, y, z = sep(nt, pos(nt))
        px = M(nt, 'SUBTRACT', x, M(nt, 'MULTIPLY', M(nt, 'FLOOR', M(nt, 'DIVIDE', x, panel[0])), panel[0]))
        pz = M(nt, 'SUBTRACT', z, M(nt, 'MULTIPLY', M(nt, 'FLOOR', M(nt, 'DIVIDE', z, panel[1])), panel[1]))
        j = M(nt, 'MINIMUM', M(nt, 'MINIMUM', px, M(nt, 'SUBTRACT', panel[0], px)), M(nt, 'MINIMUM', pz, M(nt, 'SUBTRACT', panel[1], pz)))
        joint = mr(nt, j, 0.012, 0.003)
        hx = M(nt, 'ADD', M(nt, 'MULTIPLY', M(nt, 'FLOOR', M(nt, 'DIVIDE', px, panel[0] / 4)), panel[0] / 4), panel[0] / 8)
        hz = M(nt, 'ADD', M(nt, 'MULTIPLY', M(nt, 'FLOOR', M(nt, 'DIVIDE', pz, panel[1] / 2)), panel[1] / 2), panel[1] / 4)
        d = node(nt, 'ShaderNodeVectorMath', operation='LENGTH'); put(nt, d.inputs[0], comb(nt, M(nt, 'SUBTRACT', px, hx), M(nt, 'SUBTRACT', pz, hz), 0.0))
        hole = mr(nt, d.outputs['Value'], 0.016, 0.011)
        return M(nt, 'ADD', M(nt, 'MULTIPLY', joint, -0.9), M(nt, 'MULTIPLY', hole, -1.2))
    def wetf(nt):
        x, y, z = sep(nt, pos(nt))
        streak = mr(nt, noise(nt, comb(nt, M(nt, 'MULTIPLY', x, 6.0), M(nt, 'MULTIPLY', z, 0.25), 0.0), 1.0, 3.0), 0.45, 0.7)
        damp = mr(nt, z, 0.55, 0.15)
        return M(nt, 'ADD', M(nt, 'ADD', 0.35, M(nt, 'MULTIPLY', streak, 0.4)), M(nt, 'MULTIPLY', damp, 0.45), clamp=True)
    return scanned(name, os.path.join(ACG, 'Concrete027'), uv_wall, 1.25, rot=math.radians(90), tint=(0.78, 0.84, 0.98),
                   value=value, wet=wetf, extra=ties, bump=0.8)

# ---------------------------------------------------------------- the settings
CAMLOC = None
INFO = {}

def s_wall(mist_heavy):
    global CAMLOC
    wall_m = board_wall_mat('wall')
    # the wall: monumental, rising far out of frame; its edges just beyond the frame open onto misty space
    WX = 4.3
    wall = mesh_obj('wall', [(-WX, 0, 0), (WX, 0, 0), (WX, 0, 40), (-WX, 0, 40)], [(0, 3, 2, 1)], [wall_m])
    for sx in (-1, 1):
        mesh_obj('wall_end', [(sx * WX, 0, 0), (sx * WX, 2.5, 0), (sx * WX, 2.5, 40), (sx * WX, 0, 40)], [(0, 1, 2, 3)], [wall_m])
    wet_slabs('slabs', -30, 30, -14, 0.0, disp=0.006 if FULL else 0.0)
    wet_slabs('slabs_far', -60, 60, 0.0, 120.0, puddle=0.6)
    pr, lo, rect = lightbox(0.0, -0.075, 0.17, stand=False, glow=34.0, beam=0.07 if mist_heavy else 0.05)
    CAMLOC = (0.0, -6.9, 0.52)
    camera(CAMLOC, 0, 0, 28.0, shift_y=0.088, fstop=5.6, focus=6.8)
    # far masses beyond the wall's edges, standing in aerial haze
    fac = scanned('far_concrete', os.path.join(ACG, 'Concrete027'), uv_wall, 3.0, rot=math.radians(90), tint=(0.7, 0.78, 0.95), value=0.3)
    for (x, y, w, h) in ((-16, 26, 9, 70), (17, 34, 11, 90), (-30, 60, 14, 120), (32, 70, 16, 110)):
        box('far', x - w / 2, x + w / 2, y, y + w, 0, h, fac)
    haze('aerial', -80, 80, 0.5, 140, -0.4, 140, 0.012, (0.72, 0.82, 1.0), 0.25)
    world(os.path.join(PH, 'rogland_clear_night', 'rogland_clear_night_4k.hdr'), 0.12, (0.30, 0.45, 1.0), rot=1.2)
    moon = sun('moon', (0.2, -0.85, -0.45) if FULL else (0.25, 0.9, -0.55), 2.5 if FULL else 3.0, (0.5, 0.64, 1.0), 2.0,
               receivers=[o for o in bpy.data.objects if o.name.startswith(('far', 'aerial', 'slabs_far'))])
    # the faint cobalt fill from off frame, high on the left, raking the wall's boards
    area('cobalt_fill', (-6.5, -2.2, 0.2), (0, 0, 1.4), 2600.0, (0.16, 0.30, 1.0), 2.5, receivers=[wall])
    area('cobalt_floor', (5, -9, 6), (0, -2, 0), 1500.0, (0.2, 0.36, 1.0), 6.0, receivers=[o for o in bpy.data.objects if o.name == 'slabs'])
    if mist_heavy and FULL:
        ground_mist(-40, 40, -12, 60, 1.1, 0.26, 1.8, drift=1.0)
        # the wall rising into darkness and mist: air that thickens with height, lit only faintly from above
        hm = box('high_mist', -9, 9, -7, -0.05, 1.8, 16)
        m_, nt_ = newmat('high_mist'); pv_ = node(nt_, 'ShaderNodeVolumePrincipled')
        pv_.inputs['Color'].default_value = (0.55, 0.66, 1.0, 1); pv_.inputs['Anisotropy'].default_value = 0.3
        hx, hy, hz = sep(nt_, pos(nt_))
        dvar = mr(nt_, noise(nt_, comb(nt_, M(nt_, 'MULTIPLY', hx, 0.3), hy, M(nt_, 'MULTIPLY', hz, 0.6)), 0.5, 3.0), 0.3, 0.75, 0.5, 1.3)
        put(nt_, pv_.inputs['Density'], M(nt_, 'MULTIPLY', M(nt_, 'MULTIPLY', mr(nt_, hz, 2.4, 7.0, 0.0, 1.0, smooth=True), dvar), 0.11))
        out(nt_, None, pv_.outputs['Volume']); hm.data.materials.append(m_); hm.visible_shadow = False
        sun('mist_moon', (0.1, 0.3, -0.95), 0.25, (0.45, 0.6, 1.0), 3.0, receivers=[hm])
        # rain: fewer, finer streaks at many depths, bright only where they cross the print's light
        rain(520, -3.2, 3.2, -6.0, -0.25, -0.1, 4.2, CAMLOC, (0.08, 0.22), alpha=0.3)
        rain(380, -1.4, 1.4, -2.6, -0.15, 0.0, 2.6, CAMLOC, (0.06, 0.16), alpha=0.3)
        rain(500, -40, 40, 1.0, 30, 0, 14, CAMLOC, (0.3, 0.6), alpha=0.3)
        debris(rect)
    elif mist_heavy:
        ground_mist(-40, 40, -12, 60, 1.3, 0.24, 1.8, drift=1.0)
        rain(2600 if not LITE else 1600, -5, 5, -6.2, -0.2, -0.1, 4.6, CAMLOC)
        rain(1400, -40, 40, 1.0, 30, 0, 14, CAMLOC, (0.3, 0.6))
    else:
        ground_mist(-40, 40, -12, 60, 0.16, 0.25, 1.4, drift=1.0)
        rain(1000 if not LITE else 700, -5, 5, -6.2, -0.2, -0.1, 4.6, CAMLOC)
        lib, nh, npw = flowers('blue')
        # along the wall's foot and in the slab joints, never before the box
        n = 1500 if not LITE else 900
        x = rng.uniform(-5.4, 5.4, n); y = -np.abs(rng.normal(0, 0.12, n)) - 0.02
        k = rng.uniform(0, 1, n)
        jx = np.round(rng.uniform(-5, 5, n) / 0.9) * 0.9 + rng.normal(0, 0.012, n)
        jy = -(np.round(rng.uniform(0.3, 4.2, n) / 0.6) * 0.6) + rng.normal(0, 0.01, n)
        jx2 = rng.uniform(-5, 5, n);
        sel = k < 0.55
        X = np.where(sel, x, np.where(k < 0.8, jx, jx2)); Y = np.where(sel, y, jy)
        Y = np.where((k >= 0.55) & (k < 0.8), -np.abs(rng.uniform(0.3, 4.2, n)), Y)
        dens = np.where(sel, 0.55, 0.3 * np.exp(-np.abs(X) / 3.0) + 0.12)
        keep = rng.uniform(0, 1, n) < dens
        X, Y = X[keep], Y[keep]
        clear = (np.abs(X) < 0.8) & (Y > -6.0)
        X, Y = X[~clear], Y[~clear]
        pick = np.where(rng.uniform(0, 1, len(X)) < 0.45, nh - 1 - rng.integers(0, 2, len(X)) * (Y > -0.3), nh + rng.integers(0, npw, len(X)))
        s = rng.uniform(0.5, 0.85, len(X)) * np.where(pick >= nh, 1.2, 1.0) * np.where(Y < -0.4, 0.7, 1.0)
        hgt = np.where(pick < nh, 0.32, 0.25) * s
        P = np.stack([X, Y, np.zeros(len(X))], 1)
        ok = keep_clear(P, hgt, rect)
        P, pick, s = P[ok], pick[ok], s[ok]
        R = np.stack([rng.normal(0, 0.08, len(P)), rng.normal(0, 0.08, len(P)), rng.uniform(0, 6.28, len(P))], 1)
        fl = instances('flowers', lib, P, R, np.stack([s, s, s], 1), pick)
        area('print_spill', (0, -1.0, 1.0), (0, -0.2, 0), 70.0, GLOW, 1.6, receivers=[fl])
        area('cobalt_low', (-6, -3, 0.4), (0, -0.3, 0.1), 500.0, (0.2, 0.36, 1.0), 2.0, receivers=[fl])
    return pr, rect

def debris(rect, x0=-2.2, x1=2.2, y0=-3.2, y1=-0.15, n_leaves=26, n_stones=40, z=0.0):
    """wet fallen leaves and grit placed near the print's light, thinning away from it, kept off the reflection's core"""
    leaves = load_objs(os.path.join(PH, 'tree_small_02', 'tree_small_02_1k.blend'),
                       ['tree_small_02_leaves_a_LOD1', 'tree_small_02_leaves_b_LOD1', 'tree_small_02_leaves_c_LOD1'])
    with bpy.data.libraries.load(os.path.join(PH, 'rock_moss_set_01', 'rock_moss_set_01_1k.blend'), link=False) as (src, dst):
        rn = list(src.objects)
    rocks = [o for o in load_objs(os.path.join(PH, 'rock_moss_set_01', 'rock_moss_set_01_1k.blend'), rn) if o.type == 'MESH']
    for o in rocks:
        k = 1.0 / max(o.dimensions); o.data.transform(Matrix.Diagonal((k, k, k, 1.0)))     # unit size, scaled per stone below
    for o in leaves:
        for mm in o.data.materials:
            if mm: recolour(mm, 'white')
    lib = libcoll('debris_lib', leaves + rocks); nr = len(rocks)      # instance order follows the names: rocks, then leaves
    def place(n, spread):
        r_ = np.abs(rng.normal(0, spread, n)); a_ = rng.uniform(0, math.pi, n)
        X = np.cos(a_) * r_ * 1.4; Y = -0.2 - np.sin(a_) * r_
        keep = (X > x0) & (X < x1) & (Y > y0) & (Y < y1) & ~((np.abs(X) < 0.35) & (Y < -0.5))
        return X[keep], Y[keep]
    X, Y = place(n_leaves * 2, 1.2); X, Y = X[:n_leaves], Y[:n_leaves]
    P = np.stack([X, Y, np.full(len(X), z + 0.004)], 1)
    R = np.stack([rng.normal(0, 0.15, len(X)), rng.normal(0, 0.15, len(X)), rng.uniform(0, 6.28, len(X))], 1)
    sl = rng.uniform(0.6, 1.0, len(X))
    Xs, Ys = place(n_stones * 2, 1.0); Xs, Ys = Xs[:n_stones], Ys[:n_stones]
    Ps = np.stack([Xs, Ys, np.full(len(Xs), z + 0.003)], 1)
    Rs = rng.uniform(0, 6.28, (len(Xs), 3)); ss = rng.uniform(0.012, 0.045, len(Xs))
    PP = np.concatenate([P, Ps]); RR = np.concatenate([R, Rs]); SS = np.concatenate([np.stack([sl, sl, sl], 1), np.stack([ss, ss, ss * 0.6], 1)])
    pick = np.concatenate([nr + rng.integers(0, len(leaves), len(X)), rng.integers(0, max(1, nr), len(Xs))])
    ok = keep_clear(PP, np.full(len(PP), 0.02), rect)
    return instances('debris', lib, PP[ok], RR[ok], SS[ok], pick[ok])

def s_field():
    global CAMLOC
    lib, nh, npw = flowers('blue')
    m_soil, snt = newmat('soil'); b = node(snt, 'ShaderNodeBsdfPrincipled'); b.inputs['Base Color'].default_value = (0.01, 0.014, 0.02, 1)
    b.inputs['Roughness'].default_value = 0.35; out(snt, b.outputs[0])
    mesh_obj('ground', [(-400, -40, 0), (400, -40, 0), (400, 900, 0), (-400, 900, 0)], [(0, 1, 2, 3)], [m_soil])
    pr, lo, rect = lightbox(0.0, 0.0, 0.30, stand=True, glow=38.0, beam=0.10)
    CAMLOC = (0.0, -12.0, 1.0)
    camera(CAMLOC, 0, 0, 35.0, shift_y=0.06, fstop=4.0, focus=12.0)
    # the field: dense near the box and the lens, thinning into the mist
    n = 30000 if not LITE else 12000
    X = rng.uniform(-40, 40, n) * rng.uniform(0.2, 1.0, n); Y = rng.uniform(-12, 60, n)
    X = X * (1 + np.maximum(Y, 0) / 14)
    pick = np.where(rng.uniform(0, 1, n) < 0.75, rng.integers(1, 3, n), nh + rng.integers(0, npw, n))
    s = rng.uniform(0.7, 1.2, n)
    hgt = np.where(pick < nh, 0.38, 0.3) * s
    P = np.stack([X, Y, np.zeros(n)], 1)
    ok = keep_clear(P, hgt, rect) & ~((np.abs(X) < 0.9) & (np.abs(Y) < 0.4))
    P, pick, s = P[ok], pick[ok], s[ok]
    R = np.stack([rng.normal(0, 0.06, len(P)), rng.normal(0, 0.06, len(P)), rng.uniform(0, 6.28, len(P))], 1)
    instances('field', lib, P, R, np.stack([s, s, s], 1), pick)
    # rock spires: the Poly Haven sea cliff scans stood on end, far off in layered mist
    tapered = {}
    def needle(me):
        # the scan stood on end and drawn to a point: local +X is the foot once turned, so it narrows towards -X
        if me.name in tapered: return tapered[me.name]
        nm = me.copy(); co = np.empty(len(nm.vertices) * 3, np.float32); nm.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        x0, x1 = co[:, 0].min(), co[:, 0].max(); t = (x1 - co[:, 0]) / (x1 - x0)
        k = (1.0 - 0.94 * t) ** 1.15
        cy_, cz_ = co[:, 1].mean(), co[:, 2].mean()
        co[:, 1] = cy_ + (co[:, 1] - cy_) * k; co[:, 2] = cz_ + (co[:, 2] - cz_) * k
        nm.vertices.foreach_set('co', co.ravel()); nm.update(); tapered[me.name] = nm
        return nm
    cliffs = load_objs(os.path.join(PH, 'coastal_cliff_02', 'coastal_cliff_02_1k.blend'), ['coastal_cliff_02_LOD2'])
    cliffs += load_objs(os.path.join(PH, 'coastal_cliff_01', 'coastal_cliff_01_1k.blend'), ['coastal_cliff_01_LOD2'])
    sp = []
    spires = ((0, -70, 230, 90, 0.3), (1, 85, 300, 130, 1.9), (0, -170, 420, 150, 2.6), (1, 190, 480, 170, 0.8), (0, 30, 600, 110, 1.2), (1, -30, 380, 60, 2.2))
    if FULL:   # more depths: a nearer pair, the main ranks, and the faintest far off
        spires = ((1, -46, 140, 48, 0.9), (0, 58, 170, 62, 2.0)) + spires + ((1, -260, 720, 190, 0.4), (0, 240, 820, 210, 1.7))
    for (src, x, y, h, rz) in spires:
        o = cliffs[src].copy(); link_obj(o); o.rotation_euler = (0, math.radians(90), rz)
        o.data = needle(cliffs[src].data)
        d = cliffs[src].dimensions; h *= 1.7; o.scale = (h / d.x, 0.54 * h / d.x, 0.54 * h / d.x)
        o.location = (x, y, 0); sp.append(o)
    for c_ in cliffs: bpy.data.objects.remove(c_)
    if not FULL:
        world(os.path.join(PH, 'qwantani_night_puresky', 'qwantani_night_puresky_4k.hdr'), 0.18, (0.32, 0.48, 1.0), rot=2.0)
        sun('moon_rim', (-0.4, 0.9, -0.35), 1.8, (0.6, 0.72, 1.0), 1.5, receivers=sp)
        sun('moon_back', (0.3, -0.8, -0.5), 0.35, (0.55, 0.7, 1.0), 1.5, receivers=[o for o in bpy.data.objects if o.name == 'field'])
        ground_mist(-400, 400, -12, 700, 0.12, 0.6, 5.0, drift=0.6)
        air = haze('aerial', -800, 800, 20, 900, -0.4, 260, 0.010, (0.62, 0.76, 1.0), 0.5, zfall=70.0)
        sun('mist_glow', (0.1, -1.0, -0.3), 0.3, (0.4, 0.58, 1.0), 4.0, receivers=[air])
        rain(1500 if not LITE else 900, -6, 6, -10.5, 6, 0, 5, CAMLOC, (0.18, 0.32))
        area('cobalt_fill', (8, -8, 7), (0, 2, 0.5), 300.0, (0.16, 0.3, 1.0), 6.0)
        return pr, rect
    # ---- the full frame. Idea: one cool light kept in a field at night, the land going on for ever behind it.
    # firs from the moon forest: a few stands at the field's edges and in the middle distance, never before the box
    firs = load_objs(os.path.join(PH, 'fir_tree_01_lod2', 'fir_tree_01_lod2.blend'), ['fir_tree_01_a_LOD2', 'fir_tree_01_b_LOD2', 'fir_tree_01_c_LOD2'])
    for o in firs:
        for mm in o.data.materials:
            if mm and 'twig' in mm.name: recolour(mm, 'white')
    lf = libcoll('fir_lib', firs)
    fp = []
    for (cx_, cy_, nn, sp_) in ((-17, 26, 5, 4.0), (-24, 40, 4, 5.0), (19, 34, 5, 4.5), (27, 52, 4, 5.0), (-62, 95, 7, 8.0), (70, 120, 6, 8.0), (-14, 150, 3, 6.0)):
        for k in range(nn):
            fp.append((cx_ + rng.normal(0, sp_), cy_ + rng.normal(0, sp_ * 0.8), 0.0))
    FP = np.array(fp); nf = len(FP); fs = rng.uniform(1.0, 1.5, nf)
    fob = instances('firs', lf, FP, np.stack([np.zeros(nf), np.zeros(nf), rng.uniform(0, 6.28, nf)], 1), np.stack([fs, fs, fs], 1), rng.integers(0, len(firs), nf))
    world_clouds(os.path.join(PH, 'kloppenheim_07_puresky', 'kloppenheim_07_puresky_2k.hdr'), -82.6, 0.2)
    moon = sun('moon', (-0.55, -0.6, -0.55), 0.5, (0.55, 0.68, 1.0), 0.6)
    sun('moon_rim', (-0.4, 0.9, -0.35), 1.6, (0.6, 0.72, 1.0), 1.5, receivers=sp + [fob])
    # the air in layers: thin banks at several depths, each lit from behind so it glows a little, the sky clear above
    banks = []
    for (ya, yb, top, dens) in ((25, 70, 14, 0.010), (110, 190, 30, 0.006), (260, 420, 55, 0.004), (560, 900, 90, 0.003)):
        banks.append(haze('bank', -900, 900, ya, yb, -0.4, top, dens, (0.6, 0.74, 1.0), 0.55, zfall=top * 0.45))
    sun('mist_glow', (0.1, -1.0, -0.25), 0.45, (0.4, 0.58, 1.0), 4.0, receivers=banks)
    ground_mist(-400, 400, -12, 700, 0.05, 0.5, 4.0, drift=0.6)
    rain(700, -5, 5, -10.5, 4, 0, 5, CAMLOC, (0.08, 0.2), alpha=0.32)
    # the print's light falling on the flowers in front of it: petals catch it
    field = bpy.data.objects['field']
    area('print_spill', (0, -1.6, 1.4), (0, -2.5, 0), 120.0, GLOW, 1.4, receivers=[field])
    area('cobalt_fill', (8, -8, 7), (0, 2, 0.5), 260.0, (0.16, 0.3, 1.0), 6.0, receivers=[field])
    return pr, rect

STARMAP = arg('--starmap', os.path.join(SCR, 'assets', 'nasa_svs', 'starmap_2020_8k_gal.exr'))
def world_stars(rot=(-20.0, 55.0, 90.0), k=60.0, gamma=1.6, horizon=(0.07, 0.07, 0.2), hz_h=0.14, glow=(0.26, 0.2, 0.55), glow_h=0.06):
    """the real sky: NASA SVS Deep Star Maps 2020 (public domain), galactic map turned so the Milky Way rises across
    the frame; toned to the cobalt palette (the core's warmth kept only as a trace); the horizon sinks into mist"""
    wm = bpy.data.worlds.new('w'); sc.world = wm; wm.use_nodes = True; nt = wm.node_tree; nt.nodes.clear()
    tc = node(nt, 'ShaderNodeTexCoord'); mp = node(nt, 'ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = tuple(math.radians(a) for a in rot)
    link(nt, tc.outputs['Generated'], mp.inputs[0])
    et = node(nt, 'ShaderNodeTexEnvironment', image=bpy.data.images.load(STARMAP)); link(nt, mp.outputs[0], et.inputs['Vector'])
    bw = node(nt, 'ShaderNodeRGBToBW'); link(nt, et.outputs[0], bw.inputs[0])
    v = M(nt, 'POWER', M(nt, 'MULTIPLY', bw.outputs[0], k), gamma)
    cob = comb(nt, M(nt, 'MULTIPLY', v, 0.36), M(nt, 'MULTIPLY', v, 0.5), M(nt, 'MULTIPLY', v, 1.0))
    raw = mix(nt, 1.0, et.outputs[0], (k * 0.9, k * 0.9, k * 0.9), 'MULTIPLY')
    col = mix(nt, 0.9, raw, cob)
    z = sep(nt, tc.outputs['Generated'])[2]
    # deep cobalt overhead, a luminous violet-lilac glow low on the horizon
    zen = M(nt, 'MAXIMUM', z, 0.0)
    base = comb(nt, M(nt, 'ADD', 0.008, M(nt, 'MULTIPLY', M(nt, 'EXPONENT', M(nt, 'DIVIDE', zen, -glow_h)), glow[0])),
                M(nt, 'ADD', 0.014, M(nt, 'MULTIPLY', M(nt, 'EXPONENT', M(nt, 'DIVIDE', zen, -glow_h)), glow[1])),
                M(nt, 'ADD', 0.05, M(nt, 'MULTIPLY', M(nt, 'EXPONENT', M(nt, 'DIVIDE', zen, -glow_h)), glow[2])))
    col = node(nt, 'ShaderNodeVectorMath', operation='ADD'); put(nt, col.inputs[0], mix(nt, 0.9, raw, cob)); put(nt, col.inputs[1], base); col = col.outputs[0]
    c = mix(nt, mr(nt, z, hz_h * 0.25, 0.0, smooth=True), col, horizon)
    bg = node(nt, 'ShaderNodeBackground'); link(nt, c, bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0
    # the camera sees the sky at full strength; the land gets only a little of its light
    lp = node(nt, 'ShaderNodeLightPath'); bg2 = node(nt, 'ShaderNodeBackground'); link(nt, c, bg2.inputs['Color']); bg2.inputs['Strength'].default_value = 0.35
    ms = node(nt, 'ShaderNodeMixShader'); link(nt, lp.outputs['Is Camera Ray'], ms.inputs[0]); link(nt, bg2.outputs[0], ms.inputs[1]); link(nt, bg.outputs[0], ms.inputs[2])
    o = node(nt, 'ShaderNodeOutputWorld'); link(nt, ms.outputs[0], o.inputs['Surface'])

def world_clouds(hdr, rot_deg, k=0.17):
    """the scanned moonlit cloud deck, normalised by its median, cooled to cobalt; the horizon sinks into the mist colour"""
    wm = bpy.data.worlds.new('w'); sc.world = wm; wm.use_nodes = True; nt = wm.node_tree; nt.nodes.clear()
    tc = node(nt, 'ShaderNodeTexCoord'); mp = node(nt, 'ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, math.radians(rot_deg))
    im = bpy.data.images.load(hdr); et = node(nt, 'ShaderNodeTexEnvironment', image=im)
    link(nt, tc.outputs['Generated'], mp.inputs[0]); link(nt, mp.outputs[0], et.inputs['Vector'])
    w_, h_ = im.size; px_ = np.empty(w_ * h_ * 4, np.float32); im.pixels.foreach_get(px_)
    px_ = px_.reshape(h_, w_, 4)[h_ // 2 + h_ // 40:, :, :3]
    med = float(np.median((px_ * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(2))); del px_
    bw = node(nt, 'ShaderNodeRGBToBW'); link(nt, et.outputs[0], bw.inputs[0])
    cl = M(nt, 'MULTIPLY', M(nt, 'MINIMUM', M(nt, 'POWER', M(nt, 'DIVIDE', bw.outputs[0], med), 2.2), 9.0), k)
    col = comb(nt, M(nt, 'MULTIPLY', cl, 0.42), M(nt, 'MULTIPLY', cl, 0.58), M(nt, 'MULTIPLY', cl, 1.0))
    z = sep(nt, tc.outputs['Generated'])[2]
    hz = mr(nt, z, 0.16, 0.0)
    c = mix(nt, hz, col, (0.05, 0.09, 0.19))
    bg = node(nt, 'ShaderNodeBackground'); link(nt, c, bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0
    o = node(nt, 'ShaderNodeOutputWorld'); link(nt, bg.outputs[0], o.inputs['Surface'])

def s_ruins():
    global CAMLOC
    lib, nh, npw = flowers('white')
    m_soil, snt = newmat('soil'); b = node(snt, 'ShaderNodeBsdfPrincipled'); b.inputs['Base Color'].default_value = (0.012, 0.015, 0.02, 1)
    b.inputs['Roughness'].default_value = 0.5; out(snt, b.outputs[0])
    mesh_obj('ground', [(-300, -40, 0), (300, -40, 0), (300, 600, 0), (-300, 600, 0)], [(0, 1, 2, 3)], [m_soil])
    stone = scanned('ashlar', os.path.join(PH, 'large_sandstone_blocks', 'textures'), uv_wall, 2.4, tint=(0.62, 0.7, 0.85), value=0.55)
    # an arcade of round arches behind the box, one larger arch framing it; two arches broken down
    Y0, T = 3.2, 0.9
    def arch(cx, span, h_spring, name, broken=0.0):
        r = span / 2; pw = 0.7
        box(name + '_pl', cx - r - pw, cx - r, Y0, Y0 + T, 0, h_spring, stone, 0.02)
        box(name + '_pr', cx + r, cx + r + pw, Y0, Y0 + T, 0, h_spring * (1.0 - broken * 0.6), stone, 0.02)
        n = 18; V, F = [], []
        kmax = int(n * (1.0 - broken))
        for k in range(kmax + 1):
            a = math.pi - math.pi * k / n
            for rr in (r, r + pw):
                for yy in (Y0, Y0 + T):
                    V.append((cx + rr * math.cos(a), yy, h_spring + rr * math.sin(a)))
        for k in range(kmax):
            o = k * 4; p = o + 4
            F += [(o, p, p + 2, o + 2), (o + 1, o + 3, p + 3, p + 1), (o, o + 1, p + 1, p), (o + 2, p + 2, p + 3, o + 3)]
        if F: mesh_obj(name + '_ring', V, F, [stone])
    arch(0.0, 3.4, 3.2, 'a0')
    arch(-4.6, 2.6, 2.6, 'a1'); arch(4.6, 2.6, 2.6, 'a2', broken=0.45)
    arch(-8.6, 2.6, 2.6, 'a3', broken=0.7); arch(8.6, 2.6, 2.6, 'a4')
    box('fallen', 3.0, 4.2, 1.6, 2.3, 0, 0.55, stone, 0.03)
    pr, lo, rect = lightbox(0.0, 0.6, 0.30, stand=True, glow=36.0, beam=0.09)
    CAMLOC = (0.0, -11.0, 1.1)
    camera(CAMLOC, 0, 0, 32.0, shift_y=0.07, fstop=4.0, focus=11.6)
    n = 26000 if not LITE else 10000
    X = rng.uniform(-14, 14, n); Y = rng.uniform(-10.5, 12, n)
    near = (Y > -1.5) & (Y < 1.6) & (np.abs(X) < 1.2)
    pick = np.where(rng.uniform(0, 1, n) < 0.85, rng.integers(1, 3, n), nh + rng.integers(0, npw, n))
    s = rng.uniform(0.6, 1.1, n); hgt = 0.38 * s
    P = np.stack([X, Y, np.zeros(n)], 1)
    ok = keep_clear(P, hgt, rect) & ~near & (rng.uniform(0, 1, n) < np.clip(1.0 - np.abs(X) / 16, 0.2, 1))
    P, pick, s = P[ok], pick[ok], s[ok]
    R = np.stack([rng.normal(0, 0.06, len(P)), rng.normal(0, 0.06, len(P)), rng.uniform(0, 6.28, len(P))], 1)
    instances('field', lib, P, R, np.stack([s, s, s], 1), pick)
    world(os.path.join(PH, 'qwantani_night_puresky', 'qwantani_night_puresky_4k.hdr'), 0.14, (0.3, 0.45, 1.0), rot=0.6)
    sun('moon', (0.45, 0.6, -0.55), 2.4, (0.55, 0.68, 1.0), 1.2)
    sun('moon_rim', (-0.3, -0.85, -0.45), 1.2, (0.6, 0.74, 1.0), 1.0,
        receivers=[o for o in bpy.data.objects if o.name.startswith(('a0', 'a1', 'a2', 'a3', 'a4', 'fallen', 'field'))])
    ground_mist(-200, 200, -12, 300, 0.2, 0.45, 3.0)
    haze('aerial', -300, 300, 6, 500, -0.4, 120, 0.006, (0.72, 0.82, 1.0), 0.3, zfall=30.0)
    return pr, rect

def s_undercity():
    global CAMLOC
    wall_m = board_wall_mat('tunnel', panel=(3.0, 1.5), value=0.36)
    D0, D1, HT, HW = -12.0, 8.0, 6.5, 9.0
    OW, OH = 4.6, 5.2               # the opening, half width and height
    mesh_obj('ceiling', [(-HW, D0, HT), (HW, D0, HT), (HW, D1, HT), (-HW, D1, HT)], [(0, 3, 2, 1)], [wall_m])
    for sx in (-1, 1):
        mesh_obj('side', [(sx * HW, D0, 0), (sx * HW, D1, 0), (sx * HW, D1, HT), (sx * HW, D0, HT)], [(0, 1, 2, 3)], [wall_m])
    # the end wall with its great opening
    V = [(-HW, D1, 0), (-OW, D1, 0), (-OW, D1, OH), (OW, D1, OH), (OW, D1, 0), (HW, D1, 0), (HW, D1, HT), (-HW, D1, HT)]
    mesh_obj('end', V, [(0, 1, 2, 7), (2, 3, 6, 7), (3, 4, 5, 6)], [wall_m])
    box('reveal_l', -OW - 0.01, -OW, D1, D1 + 1.2, 0, OH, wall_m); box('reveal_r', OW, OW + 0.01, D1, D1 + 1.2, 0, OH, wall_m)
    box('lintel', -OW, OW, D1, D1 + 1.2, OH, OH + 0.01, wall_m)
    wet_slabs('floor', -HW, HW, D0, D1 + 1.2, slab=(1.5, 1.5), puddle=0.5, flood=0.08)
    wet_slabs('outside', -200, 200, D1 + 1.2, 400, slab=(1.5, 1.5), puddle=0.45, flood=0.15)
    pr, lo, rect = lightbox(0.0, -0.5, 0.30, stand=True, glow=34.0, beam=0.12)
    CAMLOC = (0.0, -9.5, 1.25)
    camera(CAMLOC, 0, 0, 24.0, shift_y=0.04, fstop=5.6, focus=12.5)
    # beyond: the city as dim cobalt masses in mist, a few distant lit faces
    far = plain('far', (0.05, 0.06, 0.08), 0.8)
    em, ent = newmat('far_light'); e = node(ent, 'ShaderNodeEmission'); e.inputs['Color'].default_value = (0.35, 0.5, 1.0, 1)
    e.inputs['Strength'].default_value = 1.2; out(ent, e.outputs[0])
    for (x, y, w, h) in ((-22, 40, 12, 60), (18, 55, 14, 80), (-5, 95, 20, 120), (40, 110, 18, 90), (-50, 120, 22, 100)):
        box('tower', x - w / 2, x + w / 2, y, y + w, 0, h, far)
        box('tower_lit', x - w / 2 + 1, x + w / 2 - 1, y - 0.05, y, h * 0.3, h * 0.33, em)
    haze('outside_air', -200, 200, D1 + 0.2, 300, -0.4, 160, 0.03, (0.75, 0.85, 1.0), 0.35, zfall=25.0)
    world(None, 1.0, flat=(0.02, 0.035, 0.11))
    sun('sky_light', (0.2, -0.4, -0.9), 0.6, (0.45, 0.6, 1.0), 8.0,
        receivers=[o for o in bpy.data.objects if o.name.startswith(('outside', 'tower'))])
    # the rain curtain at the opening: dense, long, lit from beyond
    rain(4500 if not LITE else 2500, -OW - 1, OW + 1, D1 + 0.3, D1 + 6, 0, OH + 1, CAMLOC, (0.3, 0.6))
    area('opening_spill', (0, D1 + 4, 3), (0, 0, 0.5), 600.0, (0.25, 0.42, 1.0), 8.0)
    area('tunnel_bounce', (0, D1 - 1.0, 0.4), (0, D0, HT * 0.7), 1400.0, (0.2, 0.36, 1.0), 6.0,
         receivers=[o for o in bpy.data.objects if o.name.startswith(('ceiling', 'side', 'end'))])
    ground_mist(-HW, HW, D0, D1 + 30, 0.10, 0.35, 2.0)
    return pr, rect

def s_pond():
    global CAMLOC
    wall_m = board_wall_mat('court_wall', panel=(2.4, 1.2), value=0.4)
    BY, HW = 3.0, 4.6
    mesh_obj('back', [(-HW, BY, -1), (HW, BY, -1), (HW, BY, 6), (-HW, BY, 6)], [(0, 3, 2, 1)], [wall_m])
    for sx in (-1, 1):
        mesh_obj('side', [(sx * HW, -9, -1), (sx * HW, BY, -1), (sx * HW, BY, 6), (sx * HW, -9, 6)], [(0, 1, 2, 3)], [wall_m])
    # the pond: a sunk basin of dark still water, the coping round it, paving all round
    PX, PY0, PY1 = 3.2, -4.2, 2.4
    for (a0, a1, b0, b1) in ((-HW, HW, -12, PY0 - 0.3), (-HW, HW, PY1 + 0.3, BY), (-HW, -PX - 0.3, PY0 - 0.3, PY1 + 0.3), (PX + 0.3, HW, PY0 - 0.3, PY1 + 0.3)):
        wet_slabs('paving', a0, a1, b0, b1, slab=(0.9, 0.9), puddle=0.6, z=0.12)
    cope = scanned('coping', os.path.join(ACG, 'Concrete017'), uv_floor, 1.5, tint=(0.62, 0.68, 0.8), value=0.4)
    box('cope_f', -PX - 0.3, PX + 0.3, PY0 - 0.3, PY0, 0, 0.16, cope, 0.02)
    box('cope_b', -PX - 0.3, PX + 0.3, PY1, PY1 + 0.3, 0, 0.16, cope, 0.02)
    box('cope_l', -PX - 0.3, -PX, PY0, PY1, 0, 0.16, cope, 0.02); box('cope_r', PX, PX + 0.3, PY0, PY1, 0, 0.16, cope, 0.02)
    wm, wnt = newmat('pond')
    b = node(wnt, 'ShaderNodeBsdfPrincipled'); b.inputs['Base Color'].default_value = (0.004, 0.006, 0.01, 1)
    b.inputs['Roughness'].default_value = 0.02; b.inputs['IOR'].default_value = 1.33; b.inputs['Specular IOR Level'].default_value = 0.6
    x, y, z = sep(wnt, pos(wnt))
    h = 0.0
    for scl, amp in ((5.0, 1.0), (9.0, 0.6)):
        v = node(wnt, 'ShaderNodeTexVoronoi'); v.inputs['Scale'].default_value = scl; put(wnt, v.inputs['Vector'], comb(wnt, x, y, 0.0))
        ph = sep(wnt, v.outputs['Color'])[0]
        rr = M(wnt, 'MULTIPLY', M(wnt, 'SUBTRACT', M(wnt, 'DIVIDE', v.outputs['Distance'], scl), M(wnt, 'MULTIPLY', ph, 0.1)), 240.0)
        ring = M(wnt, 'MULTIPLY', M(wnt, 'SINE', M(wnt, 'MULTIPLY', rr, 2.6)), M(wnt, 'EXPONENT', M(wnt, 'MULTIPLY', M(wnt, 'MULTIPLY', rr, rr), -0.5)))
        h = M(wnt, 'ADD', h, M(wnt, 'MULTIPLY', M(wnt, 'MULTIPLY', ring, M(wnt, 'SUBTRACT', 1.0, ph)), 0.0004 * amp))
    bp = node(wnt, 'ShaderNodeBump'); put(wnt, bp.inputs['Height'], h); link(wnt, bp.outputs[0], b.inputs['Normal'])
    out(wnt, b.outputs[0]); aov(wnt, 1.0)
    mesh_obj('pond', [(-PX, PY0, 0.06), (PX, PY0, 0.06), (PX, PY1, 0.06), (-PX, PY1, 0.06)], [(0, 1, 2, 3)], [wm])
    pr, lo, rect = lightbox(0.0, BY - 0.075, 0.75, stand=False, glow=34.0, beam=0.10)
    CAMLOC = (0.0, -8.2, 1.45)
    camera(CAMLOC, 0, -2.0, 30.0, shift_y=0.06, fstop=5.6, focus=12.5)
    # the overhanging tree at the top left, its scanned leaves fallen and floating on the pond
    tree = load_objs(os.path.join(PH, 'tree_small_02', 'tree_small_02_1k.blend'), ['tree_small_02_LOD1'])
    if tree:
        t = tree[0]; link_obj(t) if not t.users_collection else None
        t.location = (-4.0, 1.2, 0.12); t.scale = (1.35, 1.35, 1.35); t.rotation_euler = (0, 0, 2.3)
        for mm in t.data.materials:
            if mm and 'leaves' in mm.name: recolour(mm, 'white')     # the leaves pulled cool, held in the night's palette
    leaves = load_objs(os.path.join(PH, 'tree_small_02', 'tree_small_02_1k.blend'),
                       ['tree_small_02_leaves_a_LOD1', 'tree_small_02_leaves_b_LOD1', 'tree_small_02_leaves_c_LOD1'])
    if leaves:
        lc = libcoll('leaf_lib', leaves); n = 70
        X = rng.uniform(-PX + 0.2, PX - 0.2, n) * rng.uniform(0.4, 1.0, n) - 0.8; Y = rng.uniform(PY0 + 0.3, PY1 - 0.3, n)
        P = np.stack([X, Y, np.full(n, 0.062)], 1)
        ok = keep_clear(P, np.full(n, 0.02), rect)
        R = np.stack([np.zeros(n), np.zeros(n), rng.uniform(0, 6.28, n)], 1)
        s = rng.uniform(0.8, 1.2, n)
        instances('floating_leaves', lc, P[ok], R[ok], np.stack([s, s, s], 1)[ok], rng.integers(0, len(leaves), n)[ok])
    lib, nh, npw = flowers('blue')
    n = 900
    X = np.concatenate([rng.uniform(-HW, -PX - 0.3, n // 2), rng.uniform(PX + 0.3, HW, n // 2)]); Y = rng.uniform(-6, BY - 0.05, n)
    P = np.stack([X, Y, np.full(n, 0.12)], 1); pick = nh + rng.integers(0, npw, n); s = rng.uniform(0.7, 1.2, n)
    ok = keep_clear(P, 0.3 * s, rect)
    R = np.stack([rng.normal(0, 0.06, n), rng.normal(0, 0.06, n), rng.uniform(0, 6.28, n)], 1)
    instances('edge_flowers', lib, P[ok], R[ok], np.stack([s, s, s], 1)[ok], pick[ok])
    world(os.path.join(PH, 'rogland_clear_night', 'rogland_clear_night_4k.hdr'), 0.12, (0.3, 0.45, 1.0), rot=0.4)
    area('cobalt_fill', (3.5, -2, 5.5), (-2, 3, 1.5), 2600.0, (0.16, 0.3, 1.0), 4.0,
         receivers=[o for o in bpy.data.objects if o.name.startswith(('back', 'side', 'tree'))])
    rain(1400 if not LITE else 900, -HW, HW, -7, BY - 0.2, 0.1, 6, CAMLOC)
    ground_mist(-HW, HW, -9, BY, 0.10, 0.3, 1.5)
    return pr, rect

def s_forest():
    global CAMLOC
    m_soil = scanned('forest_floor', os.path.join(ACG, 'Ground037'), uv_floor, 2.0, tint=(0.45, 0.55, 0.85), value=0.35)
    mesh_obj('ground', [(-200, -30, 0), (200, -30, 0), (200, 300, 0), (-200, 300, 0)], [(0, 1, 2, 3)], [m_soil])
    firs = load_objs(os.path.join(PH, 'fir_tree_01_lod2', 'fir_tree_01_lod2.blend'), ['fir_tree_01_a_LOD2', 'fir_tree_01_b_LOD2', 'fir_tree_01_c_LOD2'])
    for o in firs:
        for mm in o.data.materials:
            if mm and 'twig' in mm.name: recolour(mm, 'blue')
    lc = libcoll('fir_lib', firs)
    pr, lo, rect = lightbox(0.0, 0.0, 0.30, stand=True, glow=36.0, beam=0.10)
    CAMLOC = (0.0, -10.5, 1.15)
    camera(CAMLOC, 0, 0, 30.0, shift_y=0.10, fstop=4.0, focus=10.5)
    # tall trunks in ranks: a clear lane to the box, symmetry kept loosely
    pts = []
    for row, (y, spread) in enumerate(((2.5, 3.6), (6, 4.5), (11, 5.5), (17, 7), (25, 9), (36, 12), (50, 15))):
        for side in (-1, 1):
            for k in range(2 + row):
                x = side * (spread + k * rng.uniform(2.5, 4.5) + rng.normal(0, 0.6))
                pts.append((x, y + rng.normal(0, 1.5), 0))
    for k in range(10):
        pts.append((rng.uniform(-6, 6), rng.uniform(30, 70), 0))
    P = np.array(pts); n = len(P)
    s = rng.uniform(1.1, 1.5, n)
    R = np.stack([np.zeros(n), np.zeros(n), rng.uniform(0, 6.28, n)], 1)
    instances('firs', lc, P, R, np.stack([s, s, s], 1), rng.integers(0, len(firs), n))
    lib, nh, npw = flowers('blue')
    m = 2500
    X = rng.uniform(-12, 12, m); Y = rng.uniform(-9, 20, m)
    P2 = np.stack([X, Y, np.zeros(m)], 1); pick = nh + rng.integers(0, npw, m); s2 = rng.uniform(0.7, 1.3, m)
    ok = keep_clear(P2, 0.3 * s2, rect) & (rng.uniform(0, 1, m) < 0.6)
    R2 = np.stack([rng.normal(0, 0.06, m), rng.normal(0, 0.06, m), rng.uniform(0, 6.28, m)], 1)
    instances('floor_plants', lib, P2[ok], R2[ok], np.stack([s2, s2, s2], 1)[ok], pick[ok])
    world(os.path.join(PH, 'qwantani_night_puresky', 'qwantani_night_puresky_4k.hdr'), 0.10, (0.3, 0.45, 1.0))
    # the moon high behind and to the right; shafts through the canopy in the air
    sun('moon', (-0.3, -0.75, -0.6), 2.6, (0.42, 0.58, 1.0), 0.5)
    haze('forest_air', -60, 60, -8, 90, -0.4, 40, 0.026, (0.6, 0.72, 1.0), 0.75, zfall=16.0)
    ground_mist(-60, 60, -10, 90, 0.18, 0.4, 2.0)
    return pr, rect

def s_undergreen():
    """Idea: beneath the plate, nature has quietly taken the city back, and one cool light still burns there."""
    global CAMLOC
    ZP = 22.0                                       # the underside of the plate
    conc = board_wall_mat('plate', panel=(6.0, 3.0), value=0.32)
    def mossy(nt):
        # moss settles on every upward face and creeps down the sides
        n_ = node(nt, 'ShaderNodeNewGeometry'); x, y, z = sep(nt, n_.outputs['Normal'])
        return mr(nt, z, 0.3, 0.8)
    col_m = scanned('column', os.path.join(ACG, 'Concrete027'), uv_wall, 2.0, rot=math.radians(90), tint=(0.7, 0.8, 0.75), value=0.3)
    moss_m = scanned('moss', os.path.join(ACG, 'Moss002'), uv_floor, 1.2, tint=(0.55, 0.85, 0.5), value=0.6)
    # the plate: slabs with two gaps where the sky comes through, girders beneath it
    for (x0, x1, y0, y1) in ((-120, 120, -30, 26), (-120, 4, 26, 42), (16, 120, 26, 42), (-120, 120, 42, 60),
                             (-120, -24, 60, 74), (-12, 120, 60, 74), (-120, 120, 74, 220)):
        box('plate', x0, x1, y0, y1, ZP, ZP + 4, conc)
    for gx in np.arange(-60, 61, 7.5):
        box('girder', gx - 0.45, gx + 0.45, -30, 220, ZP - 1.8, ZP, col_m)
    for gy in np.arange(-6, 200, 16):
        box('beam', -120, 120, gy - 0.5, gy + 0.5, ZP - 1.2, ZP, col_m)
    # supports: great columns rising out of the overgrowth into the haze
    cols = []
    for (x, y, w) in ((-7.5, 9, 2.6), (7.5, 9, 2.6), (-15, 30, 3.2), (15, 30, 3.2), (-9, 52, 3.6), (22.5, 56, 3.6), (-30, 75, 4), (0, 95, 4), (30, 110, 4)):
        cols.append(box('column', x - w / 2, x + w / 2, y - w / 2, y + w / 2, -0.5, ZP - 1.8, col_m, 0.05))
    # ground: moss and loam, a wet path of slabs to the box and on into the green
    gm = scanned('loam', os.path.join(ACG, 'Ground037'), uv_floor, 2.5, tint=(0.45, 0.62, 0.5), value=0.22)
    mesh_obj('ground', [(-200, -30, -0.02), (200, -30, -0.02), (200, 300, -0.02), (-200, 300, -0.02)], [(0, 1, 2, 3)], [gm])
    wet_slabs('path', -1.6, 1.6, -14, 40, slab=(1.6, 0.8), puddle=0.48, flood=0.06, z=0.0)
    pr, lo, rect = lightbox(0.0, 0.0, 0.30, stand=True, glow=40.0, beam=0.12)
    CAMLOC = (0.0, -9.0, 1.35)
    camera(CAMLOC, 0, 0, 20.0, shift_y=0.10, fstop=4.0, focus=9.0, clip=1500)
    # the overgrowth, all scanned: ferns, calathea's broad leaves, pachira canopies, shrubs, moss
    fern = load_objs(os.path.join(PH, 'fern_02', 'fern_02_1k.blend'), ['fern_02_a', 'fern_02_b', 'fern_02_c', 'fern_02_d'])
    cal = load_objs(os.path.join(PH, 'calathea_orbifolia_01', 'calathea_orbifolia_01_1k.blend'), ['calathea_orbifolia_01_%s' % k for k in 'abc'])
    pac = load_objs(os.path.join(PH, 'pachira_aquatica_01', 'pachira_aquatica_01_1k.blend'),
                    ['pachira_aquatica_01_leaves_%s' % k for k in 'acd'])
    shr = load_objs(os.path.join(PH, 'shrub_02', 'shrub_02_1k.blend'), ['shrub_02_%s_LOD1' % k for k in 'bcd'])
    # instance order follows the names: calathea, fern, pachira, shrub
    lib = cal + fern + pac + shr
    L_ = libcoll('jungle_lib', lib)
    iC, iF, iP, iS = 0, len(cal), len(cal) + len(fern), len(cal) + len(fern) + len(pac)
    n = 9000 if not LITE else 4000
    X = rng.normal(0, 1, n) * 12; Y = rng.uniform(-9, 70, n)
    X = np.where(np.abs(X) < 2.2, np.sign(X + 1e-6) * (2.2 + rng.uniform(0, 1.5, n)), X)
    u = rng.uniform(0, 1, n)
    pick = np.where(u < 0.45, rng.integers(iF, iP, n), np.where(u < 0.65, rng.integers(iC, iF, n),
           np.where(u < 0.85, rng.integers(iP, iP + 3, n), rng.integers(iS, len(lib), n))))
    s = rng.uniform(0.6, 1.4, n) * np.where((pick >= iP) & (pick < iS), np.where(Y < 12, 0.8, rng.uniform(1.4, 3.6, n)), 1.0) * (1 + np.clip(Y, 0, 60) / 120)
    s = s * np.where(np.abs(X) < 3.2, 0.7, 1.0)
    P = np.stack([X, Y, np.zeros(n)], 1)
    ok = keep_clear(P, 1.2 * s, rect, margin=0.03)
    P, pick, s = P[ok], pick[ok], s[ok]
    R = np.stack([rng.normal(0, 0.05, len(P)), rng.normal(0, 0.05, len(P)), rng.uniform(0, 6.28, len(P))], 1)
    jungle = instances('jungle', L_, P, R, np.stack([s, s, s], 1), pick)
    # creepers hanging from the girders and the columns' heads: scanned leaves strung down a stem
    vine_pts, vine_rot, vine_s, vine_pick = [], [], [], []
    cu = bpy.data.curves.new('creepers', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.012; cu.bevel_resolution = 1
    for k in range(150):
        gx = rng.choice(np.arange(-30, 31, 7.5)) + rng.normal(0, 1.2); gy = rng.uniform(2, 60)
        if abs(gx) < 4 and gy < 20: continue
        top = ZP - 1.8; Lh = rng.uniform(4, 14) * (0.6 + 0.4 * rng.random())
        sp = cu.splines.new('POLY'); m_ = int(Lh / 0.4) + 1; sp.points.add(m_ - 1)
        sway = rng.normal(0, 0.15)
        for i in range(m_):
            z = top - i * 0.4; x = gx + sway * math.sin(i * 0.3)
            sp.points[i].co = (x, gy, z, 1)
            if rng.random() < 0.8:
                vine_pts.append((x + rng.normal(0, 0.05), gy + rng.normal(0, 0.05), z)); vine_rot.append((math.pi + rng.normal(0, 0.4), rng.normal(0, 0.4), rng.uniform(0, 6.28)))
                sc_ = rng.uniform(0.8, 1.4); vine_s.append((sc_, sc_, sc_)); vine_pick.append(rng.integers(iC, iF))
    vo = link_obj(bpy.data.objects.new('creepers', cu)); cu.materials.append(plain('stem', (0.015, 0.022, 0.014), 0.6))
    vp = np.array(vine_pts); okv = keep_clear(vp, np.full(len(vp), 0.3), rect)
    vines = instances('creeper_leaves', L_, vp[okv], np.array(vine_rot)[okv], np.array(vine_s)[okv], np.array(vine_pick)[okv])
    # water falling in threads from the plate, and a fine drizzle
    for (x, y) in ((-5.0, 14.0), (5.5, 22.0), (-12.0, 34.0), (10.0, 34.0), (3.0, 48.0)):
        rain(500, x - 0.25, x + 0.25, y - 0.25, y + 0.25, 0, ZP - 2, CAMLOC, (0.6, 1.4), slant=0.0)
    rain(900 if not LITE else 500, -6, 6, -7, 8, 0, 8, CAMLOC, (0.15, 0.3))
    # light: the sky through the gaps (shafts in humid air), green light filtering down, cobalt in the shadows
    world(None, 1.0, flat=(0.02, 0.05, 0.035))
    sun('sky_through', (0.12, -0.32, -0.94), 9.0, (0.86, 1.0, 0.9), 1.5)
    canopy = area('green_down', (0, 30, ZP - 3), (0, 30, 0), 90000.0, (0.58, 0.92, 0.66), 40.0,
                  receivers=[jungle] + cols)
    area('plate_bounce', (0, 40, 1.0), (0, 40, ZP), 60000.0, (0.4, 0.62, 0.5), 60.0,
         receivers=[o for o in bpy.data.objects if o.name.startswith(('plate', 'girder', 'beam'))] + [vines, vo])
    area('cobalt_shadow', (-6, -6, 2.0), (0, 6, 0.5), 900.0, (0.16, 0.3, 1.0), 4.0, receivers=[jungle, vo] + cols)
    haze('humid_air', -120, 120, -12, 220, -0.4, ZP - 0.2, 0.014, (0.78, 0.95, 0.82), 0.6, zfall=40.0)
    ground_mist(-60, 60, -10, 120, 0.12, 0.5, 2.5, col=(0.7, 0.9, 0.78))
    return pr, rect

def spires_from_scans(spec):
    """Poly Haven sea cliff scans stood on end and drawn to a point (local +X is the foot once turned)"""
    cliffs = load_objs(os.path.join(PH, 'coastal_cliff_02', 'coastal_cliff_02_1k.blend'), ['coastal_cliff_02_LOD2'])
    cliffs += load_objs(os.path.join(PH, 'coastal_cliff_01', 'coastal_cliff_01_1k.blend'), ['coastal_cliff_01_LOD2'])
    tapered, out_ = {}, []
    def needle(me, sharp):
        key = (me.name, sharp)
        if key in tapered: return tapered[key]
        nm = me.copy(); co = np.empty(len(nm.vertices) * 3, np.float32); nm.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        x0, x1 = co[:, 0].min(), co[:, 0].max(); t = (x1 - co[:, 0]) / (x1 - x0)
        kk = (1.0 - sharp * t) ** 1.15
        cy_, cz_ = co[:, 1].mean(), co[:, 2].mean()
        co[:, 1] = cy_ + (co[:, 1] - cy_) * kk; co[:, 2] = cz_ + (co[:, 2] - cz_) * kk
        nm.vertices.foreach_set('co', co.ravel()); nm.update(); tapered[key] = nm
        return nm
    for (src, x, y, z, h, rz, sharp, thick) in spec:
        o = cliffs[src].copy(); link_obj(o); o.rotation_euler = (0, math.radians(90), rz)
        o.data = needle(cliffs[src].data, sharp)
        d = cliffs[src].dimensions; h *= 1.7; o.scale = (h / d.x, thick * h / d.x, thick * h / d.x)
        o.location = (x, y, z); out_.append(o)
    for c_ in cliffs: bpy.data.objects.remove(c_)
    return out_

def firs_lib():
    firs = load_objs(os.path.join(PH, 'fir_tree_01_lod2', 'fir_tree_01_lod2.blend'), ['fir_tree_01_a_LOD2', 'fir_tree_01_b_LOD2', 'fir_tree_01_c_LOD2'])
    for o in firs:
        for mm in o.data.materials:
            if mm and 'twig' in mm.name: recolour(mm, 'white')
    return libcoll('fir_lib', firs), len(firs)

def drift_field(lib, nh, npw, n, x0, x1, y0, y1, rect, z_of=None, clear=None, scale=1.0, drift_scale=0.12):
    """flowers in drifts: dense where a slow noise says so, thin between; heliophila mostly, a little periwinkle"""
    X = rng.uniform(x0, x1, n); Y = rng.uniform(y0, y1, n)
    f = (np.sin(X * drift_scale + 1.3) * np.cos(Y * drift_scale * 1.3 + 0.4) + np.sin((X + Y) * drift_scale * 0.6)) * 0.5
    keep = rng.uniform(0, 1, n) < np.clip(0.35 + f * 0.9, 0.08, 1.0)
    if clear is not None: keep &= ~clear(X, Y)
    X, Y = X[keep], Y[keep]; m = len(X)
    pick = np.where(rng.uniform(0, 1, m) < 0.82, rng.integers(1, nh, m), nh + rng.integers(0, npw, m))
    s = rng.uniform(0.7, 1.25, m) * scale
    Z = z_of(X, Y) if z_of else np.zeros(m)
    P = np.stack([X, Y, Z], 1)
    ok = keep_clear(P, 0.38 * s, rect)
    P, pick, s = P[ok], pick[ok], s[ok]
    R = np.stack([rng.normal(0, 0.06, len(P)), rng.normal(0, 0.06, len(P)), rng.uniform(0, 6.28, len(P))], 1)
    return instances('field', lib, P, R, np.stack([s, s, s], 1), pick)

def s_coast():
    """Idea: one cool light kept on a headland at the edge of the world, under the whole sky."""
    global CAMLOC
    lib, nh, npw = flowers('white', glow=arg('--petal-glow', 2.2))
    # the headland: a meadow sloping gently down towards the sea, rounding over into the cliff
    EDGE, SEA = 22.0, -24.0
    def hz(X, Y): return -0.075 * (Y + 14.0) - np.maximum(0.0, Y - EDGE) ** 2 * 0.08 - 0.03 * np.sin(X * 0.3)
    nx, ny = 160, 140
    xs = np.linspace(-110, 110, nx); ys = np.linspace(-30, 48, ny)
    GX, GY = np.meshgrid(xs, ys); GZ = hz(GX, GY)
    V = np.stack([GX.ravel(), GY.ravel(), GZ.ravel()], 1)
    F = [(j_ * nx + i_, j_ * nx + i_ + 1, (j_ + 1) * nx + i_ + 1, (j_ + 1) * nx + i_) for j_ in range(ny - 1) for i_ in range(nx - 1)]
    soil = scanned('turf', os.path.join(ACG, 'Ground037'), uv_floor, 2.0, tint=(0.35, 0.45, 0.7), value=0.1)
    mesh_obj('headland', V, F, [soil])
    # the sea: mirror-calm, a long slow swell, catching the sky and the glow
    m_sea, snt = newmat('sea'); b = node(snt, 'ShaderNodeBsdfPrincipled'); b.inputs['Base Color'].default_value = (0.003, 0.005, 0.01, 1)
    b.inputs['Roughness'].default_value = 0.015; b.inputs['Specular IOR Level'].default_value = 0.6
    x_, y_, _ = sep(snt, pos(snt))
    bp = node(snt, 'ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.12; bp.inputs['Distance'].default_value = 0.5
    put(snt, bp.inputs['Height'], noise(snt, comb(snt, M(snt, 'MULTIPLY', x_, 0.02), M(snt, 'MULTIPLY', y_, 0.12), 0.0), 3.0, 4.0, 0.5))
    link(snt, bp.outputs[0], b.inputs['Normal']); out(snt, b.outputs[0]); aov(snt, 1.0)
    mesh_obj('sea', [(-4000, 20, SEA), (4000, 20, SEA), (4000, 5000, SEA), (-4000, 5000, SEA)], [(0, 1, 2, 3)], [m_sea])
    BOXY = 2.0
    pr, lo, rect = lightbox(0.0, BOXY, float(hz(np.array([0.0]), np.array([BOXY]))[0]) + 0.30, stand=True, glow=44.0, beam=0.07)
    for o_ in bpy.data.objects:      # the stand's legs and feet down to the sloping ground
        pass
    CAMLOC = (0.0, -15.5, float(hz(np.array([0.0]), np.array([-15.5]))[0]) + 1.05)
    camera(CAMLOC, 0, -1.5, 30.0, shift_y=arg('--shift', 0.02), fstop=arg('--fstop', 4.0), focus=17.5, clip=8000)
    drift_field(lib, nh, npw, 70000 if not LITE else 24000, -30, 30, -13.5, EDGE + 3, rect, z_of=hz,
                clear=lambda X, Y: ((np.abs(X) < 0.9) & (Y > BOXY - 0.6) & (Y < BOXY + 0.5)),
                drift_scale=0.2, scale=0.8)
    # a few large flowers right before the lens, soft and glowing
    NF = np.array([(-1.3, -13.4), (-0.85, -13.1), (1.15, -13.3), (1.6, -12.9), (-1.9, -12.8)])
    NP = np.stack([NF[:, 0], NF[:, 1], hz(NF[:, 0], NF[:, 1])], 1)
    instances('near_flowers', lib, NP, np.stack([rng.normal(0, 0.1, 5), rng.normal(0, 0.1, 5), rng.uniform(0, 6.28, 5)], 1),
              np.full((5, 3), 2.3), np.array([1, 2, 1, 2, 1]))
    # sea stacks: scanned cliff and rock, broken and varied, at several depths; one carries firs
    stacks = spires_from_scans(((1, 40, 1100, SEA, 95, 1.7, 0.78, 1.0), (0, 330, 900, SEA, 110, 0.3, 0.8, 1.0)))
    rf = load_objs(os.path.join(PH, 'rock_face_01', 'rock_face_01_1k.blend'), ['rock_face_01'])
    if rf:
        r_ = rf[0]; link_obj(r_); r_.scale = (9.0, 9.0, 11.0); r_.rotation_euler = (0, 0, 0.7); r_.location = (-190, 430, SEA - 2)
        # more stacks from the same scan, turned and stretched differently so no two read alike
        for (x, y, sxy, sz_, rz, tilt) in ((140, 470, 7.0, 17.0, 2.1, 0.03), (230, 680, 9.0, 21.0, 4.0, -0.04), (-70, 800, 8.0, 15.0, 1.1, 0.03), (150, 250, 4.0, 8.0, 5.3, 0.0)):
            c_ = r_.copy(); link_obj(c_); c_.scale = (sxy, sxy * 0.8, sz_); c_.rotation_euler = (tilt, 0, rz); c_.location = (x, y, SEA - 3); stacks.append(c_)
        bpy.context.view_layer.update()
        top = max((r_.matrix_world @ v.co).z for v in r_.data.vertices)
        flib, nfl = firs_lib()
        TP = np.array([(-190 + rng.uniform(-18, 18), 430 + rng.uniform(-12, 12), top - rng.uniform(1.0, 6.0)) for _ in range(14)])
        fs = rng.uniform(1.0, 1.6, len(TP))
        instances('stack_firs', flib, TP, np.stack([np.zeros(len(TP)), np.zeros(len(TP)), rng.uniform(0, 6.28, len(TP))], 1),
                  np.stack([fs, fs, fs], 1), rng.integers(0, nfl, len(TP)))
        stacks.append(r_)
    else:
        flib, nfl = firs_lib()
    # two firs on the headland, well to the sides, framing
    HF = np.array([(-19.0, 10.0), (-24.0, 15.0), (22.0, 13.0)]); HZ = hz(HF[:, 0], HF[:, 1])
    hs = np.array([0.95, 1.2, 1.05])
    instances('headland_firs', flib, np.stack([HF[:, 0], HF[:, 1], HZ], 1), np.stack([np.zeros(3), np.zeros(3), rng.uniform(0, 6.28, 3)], 1),
              np.stack([hs, hs, hs], 1), np.array([0, 1, 2]))
    world_stars(rot=(arg('--sx', -18.0), arg('--sy', 52.0), arg('--sz', 90.0)), k=arg('--stars', 60.0),
                glow=(0.3, 0.3, 0.85), glow_h=0.05)
    # the light low on the horizon behind the stacks: rays through the mist on the water, rims on the rock
    moon = sun('horizon_light', (-0.32, -0.94, -0.1), 1.6, (0.55, 0.62, 1.0), 0.8,
               receivers=stacks + [o for o in bpy.data.objects if o.name in ('sea', 'stack_firs')])
    banks = [haze('sea_mist', -4000, 4000, 40, 5000, SEA - 1, SEA + 22, 0.012, (0.62, 0.7, 1.0), 0.65, zfall=8.0),
             haze('high_air', -4000, 4000, 80, 5000, SEA + 18, 200, 0.0006, (0.6, 0.66, 1.0), 0.7)]
    sun('mist_glow', (-0.3, -0.95, -0.08), 0.55, (0.48, 0.55, 1.0), 4.0, receivers=banks)
    ground_mist(-80, 80, -16, EDGE + 6, 0.04, 0.4, 2.5)
    field = bpy.data.objects['field']
    area('print_spill', (0, BOXY - 1.6, 1.4 + hz(np.array([0.0]), np.array([BOXY]))[0]), (0, BOXY - 2.5, -0.3), 110.0, GLOW, 1.4, receivers=[field])
    return pr, rect

def s_starfield():
    """Idea: a field of quiet light under the whole sky, and one made light among it."""
    global CAMLOC
    lib, nh, npw = flowers('white', glow=arg('--petal-glow', 2.2))
    m_soil, snt = newmat('soil'); b = node(snt, 'ShaderNodeBsdfPrincipled'); b.inputs['Base Color'].default_value = (0.008, 0.011, 0.02, 1)
    b.inputs['Roughness'].default_value = 0.4; out(snt, b.outputs[0])
    mesh_obj('ground', [(-900, -40, 0), (900, -40, 0), (900, 1500, 0), (-900, 1500, 0)], [(0, 1, 2, 3)], [m_soil])
    pr, lo, rect = lightbox(0.0, 0.0, 0.30, stand=True, glow=44.0, beam=0.08)
    CAMLOC = (0.0, -12.0, 0.9)
    camera(CAMLOC, 0, 0, 32.0, shift_y=0.12, fstop=arg('--fstop', 11.0), focus=13.0, clip=6000)
    drift_field(lib, nh, npw, 40000 if not LITE else 15000, -45, 45, -11.5, 70, rect,
                clear=lambda X, Y: (np.abs(X) < 0.9) & (Y > -0.6) & (Y < 0.5), drift_scale=0.16)
    sp = spires_from_scans(((1, -46, 140, 0, 48, 0.9, 0.86, 0.85), (0, 58, 170, 0, 62, 2.0, 0.86, 0.85), (0, -70, 230, 0, 90, 0.3, 0.86, 0.85),
                            (1, 85, 300, 0, 130, 1.9, 0.86, 0.85), (0, -170, 420, 0, 150, 2.6, 0.86, 0.85), (1, 190, 480, 0, 170, 0.8, 0.86, 0.85),
                            (0, 30, 600, 0, 110, 1.2, 0.86, 0.85), (1, -260, 720, 0, 190, 0.4, 0.86, 0.85)))
    flib, nfl = firs_lib()
    fp = []
    for (cx_, cy_, nn, sp_) in ((-34, 70, 4, 5.0), (-48, 90, 5, 6.0), (40, 85, 4, 5.0), (58, 110, 5, 7.0), (-95, 170, 8, 10.0), (110, 200, 7, 10.0), (-20, 260, 5, 9.0)):
        for k in range(nn): fp.append((cx_ + rng.normal(0, sp_), cy_ + rng.normal(0, sp_ * 0.8), 0.0))
    FP = np.array(fp); nf = len(FP); fs = rng.uniform(1.0, 1.5, nf)
    fob = instances('firs', flib, FP, np.stack([np.zeros(nf), np.zeros(nf), rng.uniform(0, 6.28, nf)], 1), np.stack([fs, fs, fs], 1), rng.integers(0, nfl, nf))
    world_stars(rot=(arg('--sx', -18.0), arg('--sy', 52.0), arg('--sz', 90.0)), k=arg('--stars', 60.0))
    # the moon high behind, its rays through the banks between the spires
    sun('moon_rim', (-0.35, 0.9, -0.3), 1.2, (0.6, 0.72, 1.0), 1.5, receivers=sp + [fob])
    banks = []
    for (ya, yb, top, dens) in ((25, 70, 14, 0.010), (110, 190, 30, 0.006), (260, 420, 55, 0.005), (560, 900, 90, 0.004)):
        banks.append(haze('bank', -900, 900, ya, yb, -0.4, top, dens, (0.6, 0.74, 1.0), 0.6, zfall=top * 0.45))
    sun('rays', (0.25, -0.9, -0.36), 1.1, (0.45, 0.6, 1.0), 0.8, receivers=banks)
    ground_mist(-400, 400, -12, 700, 0.05, 0.5, 4.0, drift=0.6)
    rain(500, -5, 5, -10.5, 4, 0, 5, CAMLOC, (0.08, 0.2), alpha=0.32)
    field = bpy.data.objects['field']
    area('print_spill', (0, -1.6, 1.4), (0, -2.5, 0), 110.0, GLOW, 1.4, receivers=[field])
    return pr, rect

BUILD = {'1': lambda: s_wall(True), '2': lambda: s_wall(False), '3': s_field, '4': s_ruins, '7': s_undercity, '7b': s_undergreen, '3b': s_starfield, '11': s_coast,
         '8': s_pond, '9': s_forest}
NAMES = {'1': 'mist', '2': 'flowers', '3': 'blue-field', '4': 'ruins', '7': 'undercity', '7b': 'undercity-green', '3b': 'starlit-field', '11': 'starlit-coast', '8': 'pond-courtyard',
         '9': 'moon-forest'}

# ---------------------------------------------------------------- render
t0 = time.time()
pr, rect = BUILD[SET]()
r = sc.render; r.engine = 'CYCLES'; r.resolution_x, r.resolution_y = W, H; r.resolution_percentage = 100
cy = sc.cycles
if DEVICE == 'CPU':
    cy.device = 'CPU'; r.threads_mode = 'FIXED'; r.threads = 4
else:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = DEVICE; prefs.get_devices()
    for d in prefs.devices: d.use = d.type != 'CPU'
    cy.device = 'GPU'
cy.samples = SAMPLES; cy.use_adaptive_sampling = True; cy.adaptive_threshold = arg('--noise', 0.03); cy.time_limit = TCAP
cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'; cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
cy.max_bounces = 6; cy.diffuse_bounces = 2; cy.glossy_bounces = 2; cy.transmission_bounces = 6; cy.volume_bounces = 0
cy.transparent_max_bounces = 16; cy.caustics_reflective = False; cy.caustics_refractive = False
cy.blur_glossy = 1.0; cy.sample_clamp_indirect = 6.0; cy.use_light_tree = True
cy.volume_step_rate = arg('--vstep', 4.0); cy.volume_max_steps = 256
vs = sc.view_settings; vs.view_transform = 'AgX'; vs.look = 'AgX - Medium High Contrast'; vs.exposure = EXPO
r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGB'; r.image_settings.color_depth = '8'
sc.use_nodes = True; ct = sc.node_tree; ct.nodes.clear()
rl = ct.nodes.new('CompositorNodeRLayers')
gl = ct.nodes.new('CompositorNodeGlare'); gl.glare_type = 'BLOOM'; gl.quality = 'HIGH'
for k, v in (('Threshold', arg('--bloom-th', 1.2)), ('Smoothness', 0.7), ('Strength', arg('--bloom', 0.28)), ('Size', 0.8)):
    try: gl.inputs[k].default_value = v
    except Exception: pass
ct.links.new(rl.outputs['Image'], gl.inputs['Image'])
cmp = ct.nodes.new('CompositorNodeComposite'); ct.links.new(gl.outputs['Image'], cmp.inputs['Image'])
if DATA:
    vl.use_pass_z = True; vl.use_pass_object_index = True
    fo = ct.nodes.new('CompositorNodeOutputFile'); fo.base_path = os.path.dirname(os.path.abspath(DATA))
    fo.format.file_format = 'PNG'; fo.format.color_depth = '16'; fo.format.color_mode = 'RGB'
    fo.format.color_management = 'OVERRIDE'; fo.format.view_settings.view_transform = 'Raw'
    fo.file_slots.clear(); fo.file_slots.new('data')
    cc = ct.nodes.new('CompositorNodeCombineColor'); cc.mode = 'RGB'
    def cmr(sock, hi):
        n_ = ct.nodes.new('CompositorNodeMapRange'); n_.use_clamp = True
        n_.inputs['From Min'].default_value = 0; n_.inputs['From Max'].default_value = hi
        n_.inputs['To Min'].default_value = 0; n_.inputs['To Max'].default_value = 1
        ct.links.new(sock, n_.inputs['Value']); return n_.outputs['Value']
    ct.links.new(cmr(rl.outputs['Depth'], 100.0), cc.inputs['Red'])
    ct.links.new(cmr(rl.outputs['wt'], 1.0), cc.inputs['Green'])
    ct.links.new(cmr(rl.outputs['IndexOB'], 4.0), cc.inputs['Blue'])
    ct.links.new(cc.outputs['Image'], fo.inputs[0])

# the print's corners and the mark's box, in pixels (x right, y down)
bpy.context.view_layer.update()
from bpy_extras.object_utils import world_to_camera_view
def px(p):
    q = world_to_camera_view(sc, CAM, Vector(p)); return [round(q.x * W, 2), round((1 - q.y) * H, 2)]
vs_ = [pr.matrix_world @ v.co for v in pr.data.vertices]          # bl, br, tr, tl
corners = {'top_left': px(vs_[3]), 'top_right': px(vs_[2]), 'bottom_right': px(vs_[1]), 'bottom_left': px(vs_[0])}
mk = print_info['mark']
def uvw(u, v):    # sheet coordinates (v down) to world
    return vs_[3] + (vs_[2] - vs_[3]) * u + (vs_[0] - vs_[3]) * v
mpts = [px(uvw(u, v)) for u, v in ((mk[0], mk[1]), (mk[2], mk[1]), (mk[2], mk[3]), (mk[0], mk[3]))]
INFO = {'setting': SET, 'name': NAMES[SET], 'w': W, 'h': H, 'corners': corners,
        'mark_box': [min(p[0] for p in mpts), min(p[1] for p in mpts), max(p[0] for p in mpts), max(p[1] for p in mpts)],
        'print_json': os.path.splitext(PRINT)[0] + '.json', 'lens': CAM.data.lens, 'shift_y': CAM.data.shift_y,
        'cam_matrix': [list(rw) for rw in CAM.matrix_world], 'samples': SAMPLES}
if 'gem' in print_info:
    gk = print_info['gem']; gp = [px(uvw(u, v)) for u, v in ((gk[0], gk[1]), (gk[2], gk[3]))]
    INFO['gem_box'] = [gp[0][0], gp[0][1], gp[1][0], gp[1][1]]
json.dump(INFO, open(OUT + '.json', 'w'), indent=1)
print('CORNERS', corners, 'MARK', INFO['mark_box'])
print('BUILD %.1fs' % (time.time() - t0)); sys.stdout.flush()
if '--dry' in argv: sys.exit(0)
t1 = time.time(); r.filepath = OUT
bpy.ops.render.render(write_still=True)
print('RENDER_SECONDS %.1f' % (time.time() - t1))
if DATA:
    cand = os.path.join(os.path.dirname(os.path.abspath(DATA)), 'data0001.png')
    if os.path.exists(cand): os.replace(cand, DATA)
    vi = bpy.data.images.load(DATA); vi.colorspace_settings.name = 'Non-Color'
    a_ = np.empty(vi.size[0] * vi.size[1] * 4, np.float32); vi.pixels.foreach_get(a_)
    a_ = a_.reshape(vi.size[1], vi.size[0], 4)[::-1, :, :3]
    np.savez_compressed(os.path.splitext(DATA)[0] + '.npz', data=a_.astype(np.float16))
