# The Old Forest (Antimony world 12): the scene, its graded still and the data pass for the loop.
# Run headless (Blender 4.5 LTS), always under the shared lock:
#   flock <scratch>/blender.lock nice -n 5 blender -b -P old_forest.py -- --res 2560x1440 --samples 256 --tl 960 \
#       --work <scratch folder> --out <graded still>
# Then: python3 old_forest_compose.py (the loop, stills and depth for the page). See notes.txt.
# Assets: Poly Haven and ambientCG scans (CC0) from the shared cache; the stone from ../stone/stone.py.

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
WORK = arg('work', os.path.join(SCR, 'w11-13', 'work-' + os.path.basename(HERE))); os.makedirs(WORK, exist_ok=True)
RAW = arg('raw', os.path.join(WORK, 'raw.png'))
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

# ---------------------------------------------------------------- the stone: the shared module (exact Break geometry, carved from scans)
sys.path.insert(0, '/home/user/antimony-site/directions/stone')
import stone as STONE

# ---------------------------------------------------------------- foliage from scans (alpha cards), with optional petal tint
def foliage_mat(name, diff, alpha=None, value=1.0, sat=1.0, tint=(1, 1, 1), trans=0.35, rough=0.6,
                petal=None, hue_jitter=0.0, uvbox=None):
    """diff/alpha: the scan's textures (UV). petal: dict(a=rgb, b=rgb, emit=float, bright=float) tints the
    petals (found in the scan's own colour: pale or yellow, bright) and lets them glow gently; the rest
    of the plant keeps its scanned texture under value/sat/tint."""
    m, nt = mat(name); m['alpha'] = alpha or ''
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

# ---------------------------------------------------------------- finishing: data pass, frame positions, paper
from bpy_extras.object_utils import world_to_camera_view
def frame_rect(obj_or_pts):
    """bounding rectangle in the frame (fractions, top-left origin) of an object's evaluated vertices or of points"""
    if hasattr(obj_or_pts, 'evaluated_get'):
        dg = bpy.context.evaluated_depsgraph_get(); ev = obj_or_pts.evaluated_get(dg)
        me_ = ev.to_mesh(); pts = [ev.matrix_world @ v.co for v in me_.vertices]; ev.to_mesh_clear()
    else: pts = obj_or_pts
    xs_, ys_ = [], []
    for p in pts:
        c = world_to_camera_view(sc, sc.camera, Vector(p)); xs_.append(c.x); ys_.append(1 - c.y)
    return [min(xs_), min(ys_), max(xs_), max(ys_)]

def screen_xy(pts):
    """frame fractions (x right, y down) and camera depth for an array of world points"""
    out = []
    for p in pts:
        c = world_to_camera_view(sc, sc.camera, Vector(p)); out.append((c.x, 1 - c.y, c.z))
    return np.array(out)

def make_paper(name, size=(0.21, 0.297), fold=0.35, curl=0.012, glow=0.0, glow_col=(0.5, 0.85, 1.0)):
    """a sheet folded once across its length, half-open, edges lifting; ambientCG Paper002"""
    W_, H_ = size; NU, NV = 16, 10
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); grid = []
    for j in range(NV + 1):
        row = []
        for i in range(NU + 1):
            u, v = i / NU, j / NV
            x = (u - 0.5) * W_; yv = (v - 0.5) * H_ / 2          # folded: half the height shows
            a = abs(u - 0.5) * 2
            z = math.sin(fold) * abs(x) * 0.6 + curl * (a ** 2) + 0.004 * math.sin(v * 9.0 + u * 3.0)
            row.append(bm.verts.new((x * math.cos(fold * 0.6), yv, z)))
        grid.append(row)
    for j in range(NV):
        for i in range(NU):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for k, (ii, jj) in enumerate(((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                f.loops[k][uvl].uv = (ii / NU, jj / NV)
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free()
    for p in me_.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me_); sc.collection.objects.link(ob)
    sol = ob.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.0004
    m, nt = mat(name)
    P = ACG + '/Paper002/Paper002_2K-JPG_'
    tc_ = node(nt, 'ShaderNodeTexCoord'); mp_ = node(nt, 'ShaderNodeMapping'); mp_.inputs['Scale'].default_value = (0.5, 0.5, 0.5)
    link(nt, tc_.outputs['UV'], mp_.inputs[0])
    col = tex(nt, P + 'Color.jpg', False, mp_.outputs[0], box=False)
    hs_ = node(nt, 'ShaderNodeHueSaturation'); hs_.inputs['Saturation'].default_value = 0.4; hs_.inputs['Value'].default_value = 1.15
    link(nt, col.outputs[0], hs_.inputs['Color'])
    bs_ = node(nt, 'ShaderNodeBsdfPrincipled'); link(nt, hs_.outputs[0], bs_.inputs['Base Color']); bs_.inputs['Roughness'].default_value = 0.85
    nm_ = node(nt, 'ShaderNodeNormalMap'); nm_.inputs['Strength'].default_value = 0.4
    link(nt, tex(nt, P + 'NormalGL.jpg', True, mp_.outputs[0], box=False).outputs[0], nm_.inputs['Color']); link(nt, nm_.outputs[0], bs_.inputs['Normal'])
    tl_ = node(nt, 'ShaderNodeBsdfTranslucent'); link(nt, hs_.outputs[0], tl_.inputs['Color'])
    ms_ = node(nt, 'ShaderNodeMixShader'); ms_.inputs[0].default_value = 0.25
    link(nt, bs_.outputs[0], ms_.inputs[1]); link(nt, tl_.outputs[0], ms_.inputs[2]); sh = ms_.outputs[0]
    if glow > 0:
        e_ = node(nt, 'ShaderNodeEmission'); e_.inputs['Color'].default_value = (*glow_col, 1); e_.inputs['Strength'].default_value = glow
        ad_ = node(nt, 'ShaderNodeAddShader'); link(nt, sh, ad_.inputs[0]); link(nt, e_.outputs[0], ad_.inputs[1]); sh = ad_.outputs[0]
    o_ = node(nt, 'ShaderNodeOutputMaterial'); link(nt, sh, o_.inputs['Surface'])
    me_.materials.append(m)
    return ob

def data_pass(path, codes, hide=(), disp_k=2.0, samples=16):
    """R: disparity (disp_k / distance, clamped), G and B: per-material codes {material name: (g, b)}.
    Raw view transform, so the values land in the PNG as written."""
    dmap = {}
    for m in list(bpy.data.materials):
        if m.name.startswith('D_'): continue
        g, b = codes.get(m.name, (0.0, 0.0))
        d, nt = mat('D_' + m.name)
        cd = node(nt, 'ShaderNodeCameraData')
        dv = math_(nt, 'MINIMUM', math_(nt, 'DIVIDE', disp_k, math_(nt, 'MAXIMUM', cd.outputs['View Distance'], 0.01)), 1.0)
        cc_ = node(nt, 'ShaderNodeCombineColor'); link(nt, dv, cc_.inputs[0]); cc_.inputs[1].default_value = g; cc_.inputs[2].default_value = b
        e_ = node(nt, 'ShaderNodeEmission'); link(nt, cc_.outputs[0], e_.inputs['Color']); sh = e_.outputs[0]
        if m.get('alpha'):
            at = tex(nt, m['alpha'], True, None, box=False); tr_ = node(nt, 'ShaderNodeBsdfTransparent')
            ma = node(nt, 'ShaderNodeMixShader'); link(nt, at.outputs[0], ma.inputs[0]); link(nt, tr_.outputs[0], ma.inputs[1]); link(nt, sh, ma.inputs[2]); sh = ma.outputs[0]
        o_ = node(nt, 'ShaderNodeOutputMaterial'); link(nt, sh, o_.inputs['Surface'])
        dmap[m.name] = d
    for me_ in bpy.data.meshes:
        for i, mm in enumerate(me_.materials):
            if mm and mm.name in dmap: me_.materials[i] = dmap[mm.name]
    for ob in bpy.data.objects:
        for sl in ob.material_slots:
            if sl.link == 'OBJECT' and sl.material and sl.material.name in dmap: sl.material = dmap[sl.material.name]
        if ob.name in hide or ob.type == 'LIGHT': ob.hide_render = True
    w_ = bpy.data.worlds.new('black'); sc.world = w_; w_.use_nodes = True; w_.node_tree.nodes['Background'].inputs[1].default_value = 0
    sc.use_nodes = False; c = sc.cycles
    c.samples = samples; c.use_denoising = False; c.use_adaptive_sampling = False; c.time_limit = 0
    c.max_bounces = 0; c.transparent_max_bounces = 16
    vs = sc.view_settings
    try: vs.view_transform = 'Raw'
    except Exception: vs.view_transform = 'Standard'
    vs.look = 'None'; vs.exposure = 0.0
    sc.render.filepath = path; bpy.ops.render.render(write_still=True); print('data', path, vs.view_transform)

# ================================================================ The Old Forest
# Morning in a towering old forest: cream mist, several distinct god rays slanting down through gaps in the
# canopy, golden leaves catching the light, one great trunk (Poly Haven jacaranda_tree, scaled to an
# ancient giant, its leaves turned gold); the stone (shared stone module) among scanned roots
# (root_cluster_01) in a clear pool of light, a letter tucked among the roots at its foot.
# Metres, Z up; the camera stands on the forest floor at the origin looking north (+Y), into the light.
#
# Outputs (in WORK): raw.png, base.png (graded, no grain: the loop's source), data.png (R disparity 2/d,
# G ferns 1 / leaves 0.5, B stone 0.5 / crystal 1 / paper 0.75) and frame.json.
from mathutils.noise import noise as pnoise
STONE_AT = Vector((-0.9, 9.0, 0.0))
to_sun = Vector((arg('sx', -0.62), arg('sy', 0.48), arg('sz', 0.62))).normalized()
TRUNK_AT = Vector((7.0, 18.5, 0.0))
def gh(x, y):
    return 0.45 * pnoise(Vector((x / 14, y / 14, 0.7))) + 0.12 * pnoise(Vector((x / 3, y / 3, 1.9))) \
           + 0.6 * math.exp(-((x - TRUNK_AT.x) ** 2 + (y - TRUNK_AT.y) ** 2) / 18) \
           - 0.45 * math.exp(-((x - STONE_AT.x) ** 2 + (y - STONE_AT.y) ** 2) / 30)

# ---------------------------------------------------------------- camera
cam = bpy.data.cameras.new('cam'); cam.lens = 26; cam.sensor_width = 36
cam.dof.use_dof = True; cam.dof.aperture_fstop = 4.0
co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
CAM_Z = gh(0.6, 0) + 1.55
co.location = (0.6, 0.0, CAM_Z)
tgt = Vector((0.2, 30, CAM_Z + 30 * math.tan(math.radians(arg('pitch', 5.0)))))
co.rotation_euler = (tgt - co.location).to_track_quat('-Z', 'Y').to_euler()
cam.dof.focus_distance = (Vector((STONE_AT.x, STONE_AT.y, 1.0)) - co.location).length
sc.render.resolution_x, sc.render.resolution_y = W, H
bpy.context.view_layer.update()


# ---------------------------------------------------------------- forest floor
NG = 180; xs = np.linspace(-90, 90, NG + 1); ys = np.concatenate([np.linspace(-5, 40, NG // 2 + 1), np.geomspace(41, 220, NG // 2)])
bm = bmesh.new(); vs = [[bm.verts.new((x, y, gh(x, y))) for x in xs] for y in ys]
for j in range(len(ys) - 1):
    for i in range(NG): bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
me = bpy.data.meshes.new('floor'); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
floor = bpy.data.objects.new('floor', me); sc.collection.objects.link(floor)
m, nt = mat('floor'); tco = node(nt, 'ShaderNodeTexCoord')
mp = node(nt, 'ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.5,) * 3; link(nt, tco.outputs['Object'], mp.inputs[0])
G = ACG + '/Ground037/Ground037_2K-JPG_'; M = ACG + '/Moss002/Moss002_2K-JPG_'
nz = node(nt, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.25; nz.inputs['Detail'].default_value = 4
link(nt, tco.outputs['Object'], nz.inputs['Vector']); f = maprange(nt, nz.outputs['Fac'], 0.42, 0.58)
c = mixc(nt, f, tex(nt, G + 'Color.jpg', False, mp.outputs[0]).outputs[0], tex(nt, M + 'Color.jpg', False, mp.outputs[0]).outputs[0])
hs = node(nt, 'ShaderNodeHueSaturation'); hs.inputs['Value'].default_value = 0.9; hs.inputs['Saturation'].default_value = 0.85; link(nt, c, hs.inputs['Color'])
bs = node(nt, 'ShaderNodeBsdfPrincipled'); link(nt, hs.outputs[0], bs.inputs['Base Color'])
link(nt, mixc(nt, f, tex(nt, G + 'Roughness.jpg', True, mp.outputs[0]).outputs[0], tex(nt, M + 'Roughness.jpg', True, mp.outputs[0]).outputs[0]), bs.inputs['Roughness'])
nm = node(nt, 'ShaderNodeNormalMap'); link(nt, mixc(nt, f, tex(nt, G + 'NormalGL.jpg', True, mp.outputs[0]).outputs[0], tex(nt, M + 'NormalGL.jpg', True, mp.outputs[0]).outputs[0]), nm.inputs['Color'])
link(nt, nm.outputs[0], bs.inputs['Normal'])
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, bs.outputs[0], o.inputs['Surface'])
floor.data.materials.append(m)

# ---------------------------------------------------------------- the stone, among roots
SZ = gh(STONE_AT.x, STONE_AT.y)
parts = STONE.build_stone(sc.collection, scale_m=1.9, location=(STONE_AT.x, STONE_AT.y, SZ),
                          rotation=(-0.012, 0.010, math.atan2(0.6 - STONE_AT.x, STONE_AT.y) + math.radians(arg('yaw', 0.0))),
                          wetness=0.15, moss=0.9, cache_dir=STONE.DEFAULT_CACHE, glow=arg('glow', 0.12), caustics=False, detail=arg('detail', 380))
STONE_MATS = {m_.name for m_ in parts['stone'].data.materials if m_}
CRYSTAL_MATS = {m_.name for m_ in parts['crystal'].data.materials if m_}
if parts.get('veil'): CRYSTAL_MATS |= {m_.name for m_ in parts['veil'].data.materials if m_}
STONE_DEPTH = (STONE_AT - co.location).length
ROOTS = load_objs(f'{PH}/root_cluster_01/root_cluster_01_1k.blend', ['root_cluster_01'])[0]
for (dx, dy, rz, s) in ((-1.45, 0.55, 0.4, 0.42), (1.35, 0.75, 2.6, 0.36), (0.1, 1.1, 4.4, 0.5)):
    x, y = STONE_AT.x + dx, STONE_AT.y + dy
    place(ROOTS, (x, y, gh(x, y) - 0.25), (0, 0, rz), s)

# the letter: an unfolded sheet tucked among the roots at the stone's right foot, one edge lifting
paper = make_paper('paper', size=(0.21, 0.30), fold=0.06, curl=0.02, glow=0.0)
PX_, PY_ = STONE_AT.x + 0.95, STONE_AT.y - 0.55
paper.location = (PX_, PY_, gh(PX_, PY_) + 0.03); paper.rotation_euler = (math.radians(14), math.radians(-8), math.radians(-28))

# ---------------------------------------------------------------- the great tree: its leaves turned gold
JAC = load_objs(f'{PH}/jacaranda_tree/jacaranda_tree_1k.blend', ['jacaranda_tree_LOD1'])[0]
JT = f'{PH}/jacaranda_tree/textures/jacaranda_tree_'
gold = foliage_mat('gold_leaves', JT + 'leaves_diff_1k.png', JT + 'leaves_alpha_1k.png', value=1.7, sat=1.0,
                   tint=(1.0, 0.58, 0.16), trans=0.62, hue_jitter=0.03)
for i, sl in enumerate(JAC.data.materials):
    if sl and 'leaves' in sl.name: JAC.data.materials[i] = gold
great = place(JAC, (TRUNK_AT.x, TRUNK_AT.y, gh(TRUNK_AT.x, TRUNK_AT.y) - 0.6), (0, 0, math.radians(arg('trot', 200.0))), arg('tscale', 2.0))
great.visible_shadow = False
for (dx, dy, rz, s) in ((-2.6, -1.0, 0.3, 1.3), (2.2, -1.4, 1.9, 1.2), (-0.8, 2.0, 3.5, 1.4)):
    x, y = TRUNK_AT.x + dx, TRUNK_AT.y + dy
    place(ROOTS, (x, y, gh(x, y) - 0.4), (0, 0, rz), s)

# ---------------------------------------------------------------- the forest beyond: scanned trees, scaled tall, fading into the mist
IT = load_objs(f'{PH}/island_tree_01/island_tree_01_1k.blend', ['island_tree_01_LOD1']) + \
     load_objs(f'{PH}/island_tree_02/island_tree_02_1k.blend', ['island_tree_02_LOD1'])
for t, nm_ in zip(IT, ('island_tree_01', 'island_tree_02')):
    lm = foliage_mat(nm_ + '_gold', f'{PH}/{nm_}/textures/{nm_}_leaves_diff_1k.png', f'{PH}/{nm_}/textures/{nm_}_leaves_alpha_1k.png',
                     value=1.5, sat=1.0, tint=(1.0, 0.64, 0.2), trans=0.6, hue_jitter=0.05)
    for i, sl in enumerate(t.data.materials):
        if sl and sl.name.endswith('_leaves'): t.data.materials[i] = lm
n = 0; P, R, S_, K = [], [], [], []
while n < 300:
    y = 14 + 240 * rng.random() ** 1.2; x = rng.uniform(-1, 1) * (y * 0.8 + 10)
    if math.hypot(x - STONE_AT.x, y - STONE_AT.y) < 9 or math.hypot(x - TRUNK_AT.x, y - TRUNK_AT.y) < 12: continue
    if abs(x - STONE_AT.x) < 6 and y < 30: continue          # keep the view of the stone open
    hx, hy = to_sun.x, to_sun.y; hn = math.hypot(hx, hy); hx, hy = hx / hn, hy / hn
    along = (x - STONE_AT.x) * hx + (y - STONE_AT.y) * hy; across = abs(-(x - STONE_AT.x) * hy + (y - STONE_AT.y) * hx)
    if 0 < along < 45 and across < 9: continue               # and the sun's path down to it
    s = rng.uniform(3.5, 6.0)
    P.append((x, y, gh(x, y) - 0.5)); R.append((0, 0, rng.uniform(0, 6.283))); S_.append((s, s, s * rng.uniform(1.4, 1.9))); K.append(rng.integers(0, 2)); n += 1
# a few nearer trees whose golden crowns stand in the upper frame, where the shafts catch them
for (x, y, sc_) in ((-11, 22, 2.4), (-17, 30, 2.8), (13, 26, 2.3), (21, 34, 2.9), (-6, 38, 2.6), (6, 44, 3.0), (-24, 46, 3.2)):
    P.append((x, y, gh(x, y) - 0.4)); R.append((0, 0, rng.uniform(0, 6.283))); S_.append((sc_, sc_, sc_ * 1.5)); K.append(rng.integers(0, 2))
forest = scatter('forest', IT, np.array(P), np.array(R), np.array(S_), np.array(K))
# the canopy flag alone shapes the light (a film-set cheat): the trees cast no shadow of their own, so the
# shafts fall cleanly through the flag's gaps and catch trunks and crowns wherever they pass
forest.visible_shadow = False

# ferns and mossy stones on the floor
FERN = load_objs(f'{PH}/fern_02/fern_02_1k.blend', [f'fern_02_{k}' for k in 'abcd'])
for o in FERN:
    for i, sl in enumerate(o.data.materials):
        if sl: o.data.materials[i] = foliage_mat('fern', f'{PH}/fern_02/textures/fern_02_diff_1k.jpg', f'{PH}/fern_02/textures/fern_02_alpha_1k.png',
                                                  value=0.9, sat=0.9, tint=(0.95, 0.9, 0.6), trans=0.45)
        break
u = rng.random(2600); y = 1.5 + 60 * u ** 1.8; x = rng.uniform(-1, 1, 2600) * (y * 0.75 + 3)
keep = (np.hypot(x - STONE_AT.x, (y - STONE_AT.y) * 1.3) > 2.4) & ~((np.abs(x - STONE_AT.x) < 2.0) & (y < STONE_AT.y)) & (np.hypot(x - PX_, y - PY_) > 0.8)
x, y = x[keep], y[keep]; k = len(x)
z = np.array([gh(a, b) for a, b in zip(x, y)]); s = rng.uniform(0.9, 1.8, k)
scatter('ferns', FERN, np.stack([x, y, z], 1), np.stack([rng.normal(0, 0.1, k), rng.normal(0, 0.1, k), rng.uniform(0, 6.28, k)], 1), np.stack([s, s, s], 1), rng.integers(0, 4, k))
ROCK = load_objs(f'{PH}/rock_moss_set_01/rock_moss_set_01_1k.blend', [f'rock_moss_set_01_rock0{i}' for i in (1, 2, 3, 4)])
for (x, y, s, kk) in ((-4.5, 6.5, 0.6, 0), (2.4, 5.2, 0.4, 1), (-7.5, 13, 0.9, 2), (6.5, 9, 0.7, 3), (-2.2, 3.4, 0.25, 1)):
    place(ROCK[kk], (x, y, gh(x, y) - 0.15 * s), (0, 0, rng.uniform(0, 6.28)), s)

# ---------------------------------------------------------------- light: a low morning sun behind, a canopy that cuts it into shafts

sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = arg('sun', 30.0); sun.color = (1.0, 0.76, 0.46); sun.angle = math.radians(0.8)
so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so); so.rotation_euler = to_sun.to_track_quat('Z', 'Y').to_euler()
# the canopy flag: a sheet high above, opaque except for ragged gaps (one open over the stone); seen only by shadow rays
CZ = 34.0
hole = STONE_AT + to_sun * ((CZ - 1.0) / to_sun.z)
# the canopy is a flag (a film-set cheat): an opaque sheet high above with real holes cut where the shafts
# should fall, chosen so each shaft crosses the view; one opens over the stone. Seen only by shadow rays.
k_ = (CZ - 0.0) / to_sun.z
targets = [(STONE_AT.x, STONE_AT.y, 2.6)]
grng = np.random.default_rng(31)
for (tx, ty) in ((-9, 16), (-4, 24), (3, 14), (8, 30), (-14, 34), (14, 22), (-2, 42), (20, 46), (-20, 52), (6, 58), (-8, 70), (24, 64)):
    targets.append((tx + grng.uniform(-2, 2), ty + grng.uniform(-2, 2), grng.uniform(1.0, 2.0)))
holes = [(x + to_sun.x * k_, y + to_sun.y * k_, r) for (x, y, r) in targets]
hx0 = min(h[0] for h in holes) - 8; hx1 = max(h[0] for h in holes) + 8; hy0 = min(h[1] for h in holes) - 8; hy1 = max(h[1] for h in holes) + 8
CELL = 0.5
bm = bmesh.new()
nx_, ny_ = int((hx1 - hx0) / CELL), int((hy1 - hy0) / CELL)
for j in range(ny_):
    for i in range(nx_):
        cx_, cy_ = hx0 + (i + .5) * CELL, hy0 + (j + .5) * CELL
        cut = False
        for (hx, hy, hr) in holes:
            d_ = math.hypot(cx_ - hx, cy_ - hy); ang = math.atan2(cy_ - hy, cx_ - hx)
            if d_ < hr * (1 + 0.25 * math.sin(ang * 3 + hx) + 0.15 * math.sin(ang * 7 + hy)): cut = True; break
        if cut: continue
        x0_, y0_ = hx0 + i * CELL, hy0 + j * CELL
        vv = [bm.verts.new((x0_, y0_, CZ)), bm.verts.new((x0_ + CELL, y0_, CZ)), bm.verts.new((x0_ + CELL, y0_ + CELL, CZ)), bm.verts.new((x0_, y0_ + CELL, CZ))]
        bm.faces.new(vv)
BIG = 900
for (x0_, y0_, x1_, y1_) in ((-BIG, -BIG, hx0, BIG), (hx1, -BIG, BIG, BIG), (hx0, -BIG, hx1, hy0), (hx0, hy1, hx1, BIG)):
    bm.faces.new([bm.verts.new((x0_, y0_, CZ)), bm.verts.new((x1_, y0_, CZ)), bm.verts.new((x1_, y1_, CZ)), bm.verts.new((x0_, y1_, CZ))])
me = bpy.data.meshes.new('canopy_flag'); bm.to_mesh(me); bm.free()
flag = bpy.data.objects.new('canopy_flag', me); sc.collection.objects.link(flag)
m, nt = mat('flag'); df = node(nt, 'ShaderNodeBsdfDiffuse'); df.inputs['Color'].default_value = (0.02, 0.02, 0.015, 1)
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, df.outputs[0], o.inputs['Surface']); flag.data.materials.append(m)
flag.visible_camera = False; flag.visible_diffuse = False; flag.visible_glossy = False; flag.visible_transmission = False
print('FLAG faces', len(me.polygons), 'holes', len(holes))

# morning mist: one homogeneous volume, forward scattering, so the shafts have shape
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 130, 15)); fog = bpy.context.object; fog.name = 'mist'; fog.scale = (400, 290, 33)
m, nt = mat('mist'); v = node(nt, 'ShaderNodeVolumePrincipled'); v.inputs['Color'].default_value = (1.0, 0.94, 0.82, 1)
v.inputs['Density'].default_value = arg('fog', 0.012); v.inputs['Anisotropy'].default_value = 0.62
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, v.outputs[0], o.inputs['Volume']); fog.data.materials.append(m)

# sky: soft, pale, seen only in gaps
wld = bpy.data.worlds.new('sky'); sc.world = wld; wld.use_nodes = True
wld.node_tree.nodes['Background'].inputs['Color'].default_value = (0.95, 0.88, 0.74, 1)
wld.node_tree.nodes['Background'].inputs['Strength'].default_value = arg('sky', 0.12)

# ---------------------------------------------------------------- frame positions for the page
bpy.context.view_layer.update()
info = {'w': W, 'h': H, 'paper': frame_rect(paper), 'stone': frame_rect(parts['stone']), 'crystal': frame_rect(parts['crystal']),
        'stone_disp': 2.0 / STONE_DEPTH}
json.dump(info, open(os.path.join(WORK, 'frame.json'), 'w'), indent=1); print('FRAME', info)
if arg('dry', 0): raise SystemExit

cycles(samples=SAMPLES, tl=TL, exposure=arg('exposure', 0.7), look='None', volume=True)
sc.cycles.volume_bounces = 0; sc.cycles.transmission_bounces = 10
mist_comp((0.95, 0.88, 0.72), arg('mist', 0.38), 12, 150, sky_amount=0.6)
sc.world.mist_settings.falloff = 'LINEAR'
import time; t0 = time.time()
sc.render.filepath = RAW; bpy.ops.render.render(write_still=True); print('render seconds', round(time.time() - t0))
GK = dict(bloom=0.30, bloom_thr=0.62, halation=0.12, vignette=0.26, lift=0.025, tint=(1.04, 1.0, 0.92))
grade(RAW, os.path.join(WORK, 'base.png'), grain=0.0, **GK)
grade(RAW, OUT, grain=0.016, **GK)
codes = {'fern': (1.0, 0.0), 'gold_leaves': (0.5, 0.0), 'island_tree_01_gold': (0.5, 0.0), 'island_tree_02_gold': (0.5, 0.0)}
codes.update({m_: (0.0, 0.5) for m_ in STONE_MATS}); codes.update({m_: (0.0, 1.0) for m_ in CRYSTAL_MATS}); codes['paper'] = (0.0, 0.75)
data_pass(os.path.join(WORK, 'data.png'), codes, hide=('mist', 'canopy_flag'))
