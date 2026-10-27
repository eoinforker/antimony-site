# The Blue Field at first light (Antimony world 11, dawn variant): the night version (blue_field.py) relit
# as dawn. The same field, needles, ranges, stone, crystal and letter; the sky is a scanned sunrise turned so
# its sun stands between the needles, just clearing the far ranges, graded to clear cobalt above and a band
# of gold to peach low down; the cloud deck lit from beneath; the low sun rims the needles, backlights the
# mist and the flowers (dew on them catches it) and edges the stone, whose face rests in cool skylight;
# the crystal is glass, with a warm glint on one arris. No stars, no motes, no rain.
# Run headless (Blender 4.5 LTS), always under the shared lock:
#   flock <scratch>/blender.lock nice -n 5 blender -b -P blue_field.py -- --res 2560x1440 --samples 256 --tl 3300 \
#       --vstep 6 --data 1 --work <scratch folder> --out <graded still>
#   flock <scratch>/blender.lock nice -n 5 blender -b -P blue_field.py -- --phone 1 --res 1080x2340 --samples 224 \
#       --tl 2700 --vstep 6 --data 1 --work <another scratch folder> --out <graded still>
# Then: python3 blue_field_compose.py --work <wide folder> --work-phone <phone folder> (loops, stills, depth). See notes.txt.
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
def foliage_mat(name, diff, alpha=None, value=1.0, sat=1.0, tint=(1, 1, 1), trans=0.35, rough=arg('frough', 0.4),
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
    bs.inputs['Specular IOR Level'].default_value = 0.5      # wet with dew: the low sun catches it
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

# ================================================================ The Blue Field
# Night, fine rain. A vast field of scanned flowers (Poly Haven heliophila, empodium, celandine), their
# petals tinted to a true sky blue and white-blue, translucent and glowing gently, larger and denser near
# the camera, their light pooling on the scanned grass; the field thins into low mist over softly rolling
# ground. Far off, tall needles of scanned sea cliff (Poly Haven coastal_cliff_01 and _02, stood on end and
# tapered to a point) in layers of mist. The stone (shared stone module) stands dark and wet in a small
# clearing, its crystal glowing gently; at its foot a folded paper catches the crystal's light.
# Metres, Z up; the camera stands low in the field at the origin looking north (+Y).
#
# Outputs (in WORK, the scratch folder): raw.png (the render), base.png (graded, no grain or rain: the
# loop's source), data.png (R disparity 2/d, G plants, B stone 0.5 / crystal 1 / paper 0.75) and
# frame.json (paper, stone and crystal positions in the frame).

from mathutils.noise import noise as pnoise
STONE_AT = Vector((-1.35, 10.5, 0.0))
HILLS = arg('hills', 1)
SCALE_M = 2.1

def gh(x, y):
    d = math.hypot(x - STONE_AT.x, y - STONE_AT.y)
    near = (0.35 * pnoise(Vector((x / 22, y / 22, 0.3))) + 0.08 * pnoise(Vector((x / 5, y / 5, 1.1)))) * min(1.0, d / 4.0)
    t = min(1.0, max(0.0, (y - 50) / 150)); t = t * t * (3 - 2 * t)
    roll = t * (11.0 * pnoise(Vector((x / 130, y / 110, 3.3))) + 4.0 * pnoise(Vector((x / 45, y / 45, 5.1))) + 4.0 + 0.004 * max(y - 120, 0) ** 1.2)
    if HILLS:
        u = min(1.0, max(0.0, (y - 280) / 260)); u = u * u * (3 - 2 * u)
        ridge = max(0.0, pnoise(Vector((x / 210, y / 150, 7.7))) + 0.25) * 34.0 + abs(pnoise(Vector((x / 55, y / 48, 9.1)))) * 14.0 \
            + abs(pnoise(Vector((x / 17, y / 17, 4.4)))) * 3.0
        roll += u * ridge
        # far ranges, lost in the mist, so the horizon is a soft skyline and not a level band
        m_ = min(1.0, max(0.0, (y - 900) / 900)); m_ = m_ * m_ * (3 - 2 * m_)
        roll += m_ * max(0.0, 110 + 120 * pnoise(Vector((x / 420, y / 380, 12.5))) + 25 * pnoise(Vector((x / 90, y / 90, 13.7))))
    return near + roll + 0.06

# ---------------------------------------------------------------- camera first (the scatter keeps the mark clear in its view)
cam = bpy.data.cameras.new('cam'); cam.lens = 32; cam.sensor_width = 36; cam.clip_end = 8000.0   # past the far ranges
cam.dof.use_dof = True; cam.dof.aperture_fstop = 2.8
co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
CAM_Z = gh(0.4, 0.0) + arg('camh', 1.45)
co.location = (0.4, 0.0, CAM_Z)
# the wide frame looks due north, 2.6 degrees up; the tall phone frame turns onto the stone and looks a
# little higher, so the needles rise over it (--phone 1 with --res 1080x2340)
PHONE = arg('phone', 0)
if PHONE:
    _yaw = math.atan2(STONE_AT.x - 0.4, STONE_AT.y) + math.radians(arg('yawoff', 2.0)); _pit = math.radians(arg('pitch', 5.0))
else:
    _yaw = 0.0; _pit = math.radians(2.6)
tgt = co.location + Vector((math.sin(_yaw) * math.cos(_pit), math.cos(_yaw) * math.cos(_pit), math.sin(_pit))) * 30
co.rotation_euler = (tgt - co.location).to_track_quat('-Z', 'Y').to_euler()
cam.dof.focus_distance = (STONE_AT - co.location).length
sc.render.resolution_x, sc.render.resolution_y = W, H
bpy.context.view_layer.update()

# ---------------------------------------------------------------- ground
NG, X0, X1, Y0, Y1 = 240, -900.0, 900.0, -6.0, 3000.0
_xo = np.geomspace(126, 2600, 60)
xs = np.concatenate([-_xo[::-1], np.linspace(-120, 120, 181), _xo]); NG = len(xs) - 1; ys = np.concatenate([np.linspace(Y0, 40, NG // 2 + 1), np.geomspace(41, Y1, NG // 2)])
bm = bmesh.new(); vs = [[bm.verts.new((x, y, gh(x, y))) for x in xs] for y in ys]
for j in range(len(ys) - 1):
    for i in range(NG): bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
me = bpy.data.meshes.new('ground'); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
ground = bpy.data.objects.new('ground', me); sc.collection.objects.link(ground)
m, nt = mat('ground'); tco = node(nt, 'ShaderNodeTexCoord')
mp = node(nt, 'ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.45,) * 3; link(nt, tco.outputs['Object'], mp.inputs[0])
G = ACG + '/Grass004/Grass004_2K-JPG_'; D = ACG + '/Ground037/Ground037_2K-JPG_'
nz = node(nt, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.2; link(nt, tco.outputs['Object'], nz.inputs['Vector'])
f = maprange(nt, nz.outputs['Fac'], 0.4, 0.6)
# turf, not bare soil, close around the stone: the soil blend fades out within about 4 m of it
_dv = node(nt, 'ShaderNodeVectorMath'); _dv.operation = 'DISTANCE'; link(nt, tco.outputs['Object'], _dv.inputs[0])
_dv.inputs[1].default_value = (STONE_AT.x, STONE_AT.y, 0.0)
f = math_(nt, 'MULTIPLY', f, maprange(nt, _dv.outputs['Value'], 1.5, 4.0))
c = mixc(nt, f, tex(nt, G + 'Color.jpg', False, mp.outputs[0]).outputs[0], tex(nt, D + 'Color.jpg', False, mp.outputs[0]).outputs[0])
hs = node(nt, 'ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = 0.5; link(nt, c, hs.inputs['Color'])
link(nt, maprange(nt, _dv.outputs['Value'], 0.6, 3.5, 0.13, 0.35), hs.inputs['Value'])          # dark, wet turf at the foot
bs = node(nt, 'ShaderNodeBsdfPrincipled'); link(nt, hs.outputs[0], bs.inputs['Base Color'])
link(nt, maprange(nt, _dv.outputs['Value'], 0.6, 3.5, 0.22, 0.45), bs.inputs['Roughness'])
nm = node(nt, 'ShaderNodeNormalMap'); link(nt, tex(nt, G + 'NormalGL.jpg', True, mp.outputs[0]).outputs[0], nm.inputs['Color']); link(nt, nm.outputs[0], bs.inputs['Normal'])
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, bs.outputs[0], o.inputs['Surface'])
ground.data.materials.append(m)

# ---------------------------------------------------------------- the stone (shared module), square to the camera so the seam reads through
SZ = gh(STONE_AT.x, STONE_AT.y)
parts = STONE.build_stone(sc.collection, scale_m=SCALE_M, location=(STONE_AT.x, STONE_AT.y, SZ),
                          rotation=(0.010, -0.006, math.atan2(0.4 - STONE_AT.x, STONE_AT.y) + math.radians(arg('yaw', 0.0))), wetness=arg('wet', 0.45), moss=0.0, growth=False,
                          stone_value=arg('sval', 2.2), carve=arg('carve', 0.55), damp_foot=0.45, chip_dots=0.0,
                          crystal_depth=arg('cdepth', 0.5), inner_faces=arg('ifaces', 5), crystal_bevel=arg('cbevel', 3.0),
                          cache_dir=STONE.DEFAULT_CACHE, glow=arg('glow', 0.08), caustics=False, detail=arg('detail', 380))
STONE_MATS = {m_.name for m_ in parts['stone'].data.materials if m_}
CRYSTAL_MATS = {m_.name for m_ in parts['crystal'].data.materials if m_}
if parts.get('veil'): CRYSTAL_MATS |= {m_.name for m_ in parts['veil'].data.materials if m_}
CRY_C = Vector((STONE_AT.x, STONE_AT.y, SZ + SCALE_M * (100 - 51.5) / 100 - parts['info'].get('sink', 0.0)))
# the crystal's light on the flowers and paper in front (a cheat: the glass's own glow made clean)
cl_ = bpy.data.lights.new('crystal_light', 'POINT'); cl_.energy = arg('cl', 3.0); cl_.color = (0.48, 0.84, 1.0); cl_.shadow_soft_size = 0.45
clo = bpy.data.objects.new('crystal_light', cl_); sc.collection.objects.link(clo)
clo.location = CRY_C + Vector((0.0, -0.42, 0.05)); clo.visible_glossy = False; clo.visible_transmission = False

# a soft light low behind the stone on the flowers there, so the seam and the outline read against them
bl_ = bpy.data.lights.new('behind', 'AREA'); bl_.energy = arg('bl', 0.0); bl_.color = (0.40, 0.72, 1.0); bl_.size = 2.5
blo = bpy.data.objects.new('behind', bl_); sc.collection.objects.link(blo)
blo.location = (STONE_AT.x, STONE_AT.y + 1.6, SZ + 1.5); blo.rotation_euler = (math.radians(-12), 0, 0)
blo.visible_camera = False; blo.visible_glossy = False

# ---------------------------------------------------------------- the paper: folded, at the stone's foot, by the crystal's light
def make_letter(name, size=(0.23, 0.30), lift=55.0, glow=0.0):
    """a sheet folded once across its length and left half open: the near half lies on the turf, the far
    half stands up toward the camera with a soft round crease, a slight bow and lifting corners.
    The whole unfolded sheet carries the UVs (ambientCG Paper002 through make_paper's material)."""
    ob = make_paper(name, size=size, glow=glow)               # for its material; the mesh is replaced
    W_, H_ = size; H2 = H_ / 2; th = math.radians(lift); rr = 0.008
    NU, NV = 22, 30; bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); grid = []
    for j in range(NV + 1):
        v = j / NV; t = (v - 0.5) * H_                         # along the sheet; the crease at t = 0
        row = []
        for i in range(NU + 1):
            u = i / NU; x = (u - 0.5) * W_; a = abs(u - 0.5) * 2
            if t <= 0:                                          # the near half on the ground, edges lifting a little
                y, z = t, 0.003 + 0.010 * a ** 2 + 0.008 * (-t / H2) ** 2 * a
            else:                                               # the far half, rounding off the crease, standing up
                ang = th * min(1.0, t / (rr * th + 1e-6)) if t < rr * th else th
                if t < rr * th: y, z = rr * math.sin(ang), rr * (1 - math.cos(ang))
                else:
                    t2 = t - rr * th; y0, z0 = rr * math.sin(th), rr * (1 - math.cos(th))
                    y, z = y0 + t2 * math.cos(th), z0 + t2 * math.sin(th)
                y += 0.012 * a ** 2 * (t / H2)                  # a slight bow across the standing half
                z += 0.002 * math.sin(u * 7.0)
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(NV):
        for i in range(NU):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for k, (ii, jj) in enumerate(((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                f.loops[k][uvl].uv = (ii / NU, jj / NV)
    me_ = ob.data; bm.to_mesh(me_); bm.free()
    for p in me_.polygons: p.use_smooth = True
    return ob

paper = make_letter('paper', glow=arg('pglow', 0.0))
PX_, PY_ = STONE_AT.x + arg('paperdx', 0.05), STONE_AT.y - arg('paperdy', 1.6)
paper.location = (PX_, PY_, gh(PX_, PY_))
paper.rotation_euler = (0.0, 0.0, math.radians(-10))

# ---------------------------------------------------------------- flowers and grass (scans)
HEL = load_objs(f'{PH}/flower_heliophila/flower_heliophila_2k.blend',
                [f'flower_heliophila_{s}_LOD{l}' for s in ('small', 'medium', 'large') for l in (1, 3)])
EMP = load_objs(f'{PH}/flower_empodium/flower_empodium_2k.blend', [f'flower_empodium_{k}_LOD1' for k in 'abcd'])
CEL = load_objs(f'{PH}/celandine_01/celandine_01_2k.blend', [f'celandine_01_{k}_LOD1' for k in 'abcd'])
GRS = load_objs(f'{PH}/grass_medium_01/grass_medium_01_2k.blend',
                [f'grass_medium_01_{k}_LOD1' for k in ('tall_a', 'tall_b', 'tall_c', 'mid_a', 'mid_b', 'large_a')])
BLUE = (0.10, 0.50, 1.0); PALE = (0.36, 0.78, 1.0)
pet = dict(a=BLUE, b=PALE, emit=arg('emit', 0.9))
leaf = dict(value=0.2, sat=0.5, tint=(0.42, 0.62, 1.0), trans=0.42)
def tx_(a, n): return f'{PH}/{a}/textures/{a}_{n}_2k.' + ('png' if n in ('alpha', 'translucency') else 'jpg')
set_mat(HEL, foliage_mat('heliophila', tx_('flower_heliophila', 'diff'), tx_('flower_heliophila', 'alpha'),
                         petal=dict(a=(0.03, 0.22, 1.0), b=(0.10, 0.45, 1.0), emit=arg('hemit', 0.3)), uvbox=(0.0, 0.56, 0.0, 0.26), **leaf))
set_mat(EMP, foliage_mat('empodium', tx_('flower_empodium', 'diff'), tx_('flower_empodium', 'alpha'), petal=pet, **leaf))
set_mat(CEL, foliage_mat('celandine', tx_('celandine_01', 'diff'), tx_('celandine_01', 'alpha'), petal=pet, **leaf))
set_mat(GRS, foliage_mat('grass', tx_('grass_medium_01', 'diff'), tx_('grass_medium_01', 'alpha'), value=0.5, sat=0.6,
                         tint=(0.45, 0.7, 1.0), trans=0.4, hue_jitter=0.02))
PLANT_MATS = {'heliophila', 'empodium', 'celandine', 'grass'}

# the mark's rectangle in the frame, with a margin: nothing may stand in front of it
MARK = frame_rect(parts['stone']); MX0, MY0, MX1, MY1 = MARK[0] - 0.012, MARK[1] - 0.02, MARK[2] + 0.012, MARK[3] + 0.004
STONE_DEPTH = (STONE_AT - co.location).length
bpy.context.view_layer.update()
_pr = frame_rect(paper); print('PAPER top', _pr[1], 'MARK bottom', MARK[3], 'paper px', (_pr[2] - _pr[0]) * W, (_pr[3] - _pr[1]) * H); PRX0, PRY0, PRX1, PRY1 = _pr[0] - 0.01, _pr[1] - 0.01, _pr[2] + 0.01, _pr[3] + 0.01
PAPER_DEPTH = (paper.location - co.location).length
SENS_W = 0.036 * min(1.0, W / H); SENS_H = SENS_W * H / W; F_ = cam.lens / 1000
def clear_of_mark(p, h):
    """keep points whose plant (height h) would not cover the mark from this camera: its spread (about
    half its height, for plants nearer than the stone) and the lens's blur at its distance are counted,
    so no petal and no soft edge of an out-of-focus bloom reaches the mark"""
    tops = p.copy(); tops[:, 2] += h
    a = screen_xy(p); b = screen_xy(tops)
    x = a[:, 0]; ytop = b[:, 1]; d = np.maximum(a[:, 2], 0.05); s_ = cam.dof.focus_distance
    near_ = np.clip((STONE_DEPTH - d) / 3.0, 0, 1)
    spread = np.minimum(0.3 * np.asarray(h), 0.18) * near_ * F_ / d                 # sideways, on the sensor, metres
    coc = F_ * F_ / (cam.dof.aperture_fstop * (s_ - F_)) * np.abs(d - s_) / d       # blur diameter, metres
    rx = (spread + coc) / SENS_W + 0.003 * near_; ry = coc / SENS_H + 0.002 * near_
    inside = (x + rx > MX0) & (x - rx < MX1) & (ytop - ry < MY1) & (a[:, 1] + ry > MY0)
    in_front = a[:, 2] < STONE_DEPTH + 0.6
    on_paper = (x > PRX0) & (x < PRX1) & (ytop < PRY1) & (a[:, 1] > PRY0) & (a[:, 2] < PAPER_DEPTH + 0.3)
    return ~(inside & in_front) & ~on_paper

TANH = math.tan(math.radians(33))
def field_pts(n, ymin, ymax, power):
    u = rng.random(n); y = ymin + (ymax - ymin) * u ** power
    x = (rng.random(n) * 2 - 1) * (y * TANH + 2.0)
    keep = (np.hypot(x - STONE_AT.x, (y - STONE_AT.y) * 1.4) > 0.8) | (y > STONE_AT.y + 0.42)   # flowers right up behind it
    keep &= np.hypot(x - PX_, y - PY_) > 0.40                                                # the paper lies in a little clearing
    x, y = x[keep], y[keep]
    z = np.array([gh(a, b) for a, b in zip(x, y)])
    return np.stack([x, y, z], 1)
def clump_patches(p, strength=0.9, fade=None):
    nzv = np.array([pnoise(Vector((a / 7.0, b / 7.0, 2.2))) for a, b, _ in p])
    keep = rng.random(len(p)) < (1 - strength) + strength * np.clip(nzv * 1.6 + 0.55, 0, 1)
    if fade:                                                  # the field thins into the mist
        keep &= rng.random(len(p)) < np.clip(1.0 - (p[:, 1] - fade[0]) / (fade[1] - fade[0]), 0.08, 1.0)
    return p[keep]
def rots(n, tilt=0.12): return np.stack([rng.normal(0, tilt, n), rng.normal(0, tilt, n), rng.uniform(0, 6.283, n)], 1)

def scatter_clear(name, srcs, p, s, zs, tilt, hmax):
    k = len(p); sc_ = np.stack([s, s, s * zs], 1)
    ok = clear_of_mark(p, hmax * s * zs)
    p, sc_ = p[ok], sc_[ok]; k = len(p)
    return scatter(name, srcs, p, rots(k, tilt), sc_, rng.integers(0, len(srcs), k))

hel_sorted = sorted(HEL, key=lambda o: o.name)
for nm_, lod, n, y0, y1, pw, fade in (('hel_near', 'LOD1', 5500, 1.2, 30, 2.2, None), ('hel_far', 'LOD3', 26000, 26, 480, 1.9, (120, 470))):
    srcs = [o for o in hel_sorted if o.name.endswith(lod)]
    p = clump_patches(field_pts(n, y0, y1, pw), fade=fade); k = len(p)
    s = rng.uniform(0.7, 1.35, k) * np.where(p[:, 1] < 6, 1.25, 1.0) * np.clip(np.hypot(p[:, 0] - STONE_AT.x, p[:, 1] - STONE_AT.y) / 2.2, 0.45, 1.0)
    scatter_clear(nm_, srcs, p, s, rng.uniform(0.9, 1.5, k), 0.12, 0.4)
srcs = sorted(EMP + CEL, key=lambda o: o.name)
p = clump_patches(field_pts(16000, 1.0, 60, 2.2), 0.7); k = len(p)
s = rng.uniform(1.0, 2.0, k) * np.clip(np.hypot(p[:, 0] - STONE_AT.x, p[:, 1] - STONE_AT.y) / 2.2, 0.5, 1.0)
scatter_clear('stars', srcs, p, s, np.full(k, 1.3), 0.2, 0.3)
p = field_pts(700, 0.9, 4.5, 1.6); k = len(p)
scatter_clear('stars_near', srcs, p, rng.uniform(2.4, 4.0, k), np.full(k, 1.2), 0.25, 0.3)
srcs = sorted(GRS, key=lambda o: o.name)
p = field_pts(24000, 1.6, 80, 2.0); k = len(p)
s = rng.uniform(0.8, 1.5, k) * np.clip(np.hypot(p[:, 0] - STONE_AT.x, p[:, 1] - STONE_AT.y) / 2.0, 0.5, 1.0)
scatter_clear('grass', srcs, p, s, rng.uniform(1.0, 1.5, k), 0.15, 0.33)
# low turf in the clearing at the stone's foot, so it stands in the field and not on a bare pad
# (each tuft is kept only if it stays below the mark's lower edge in the camera's view)
n_ = 6000; cx_ = STONE_AT.x + rng.uniform(-1.9, 1.9, n_); cy_ = STONE_AT.y + rng.uniform(-2.6, -0.30, n_)
p = np.stack([cx_, cy_, np.array([gh(a, b) for a, b in zip(cx_, cy_)])], 1)
p = p[np.hypot(p[:, 0] - PX_, p[:, 1] - PY_) > 0.22]; k = len(p)
scatter_clear('turf', srcs, p, rng.uniform(0.16, 0.42, k), rng.uniform(0.5, 0.9, k), 0.25, 0.33)
# and a close, cropped sward right up to the stone's foot, low enough to stay under the mark's edge
n_ = 9000; cx_ = STONE_AT.x + rng.uniform(-1.6, 1.6, n_); cy_ = STONE_AT.y + rng.uniform(-1.5, -0.30, n_)
p = np.stack([cx_, cy_, np.array([gh(a, b) for a, b in zip(cx_, cy_)])], 1)
p = p[np.hypot(p[:, 0] - PX_, (p[:, 1] - PY_) * 1.3) > 0.2]; k = len(p)
scatter_clear('sward', srcs, p, rng.uniform(0.07, 0.16, k), rng.uniform(0.5, 0.8, k), 0.3, 0.33)

for i in range(arg('pools', 0)):
    y = 1.5 + 22 * rng.random() ** 1.6; x = (rng.random() * 2 - 1) * (y * TANH + 1)
    if math.hypot(x - STONE_AT.x, y - STONE_AT.y) < 1.2: continue
    l = bpy.data.lights.new('pool', 'POINT'); l.energy = rng.uniform(0.5, 1.4); l.color = (0.35, 0.72, 1.0); l.shadow_soft_size = 0.35
    lo = bpy.data.objects.new('pool', l); sc.collection.objects.link(lo); lo.location = (x, y, gh(x, y) + 0.22)
    lo.visible_camera = False

# ---------------------------------------------------------------- needles: scanned sea cliff stood on end and tapered to a point
SP = load_objs(f'{PH}/coastal_cliff_01/coastal_cliff_01_1k.blend', ['coastal_cliff_01_LOD2']) + \
     load_objs(f'{PH}/coastal_cliff_02/coastal_cliff_02_1k.blend', ['coastal_cliff_02_LOD3'])
# clusters, as rock needles stand in nature: one great group right of the stone, a lesser group far left,
# a few faint ones deep in the mist
NEEDLES = ((40, 230, 135, 0, 1.2, -0.05, 0.95), (58, 236, 92, 1, 1.9, 0.10, 0.9), (26, 244, 70, 1, 2.4, 0.16, 0.85),
           (66, 252, 55, 1, 4.4, 0.20, 0.8), (49, 222, 48, 1, 0.7, -0.14, 0.8),
           (-70, 330, 105, 0, 2.0, 0.06, 0.95), (-88, 340, 70, 1, 0.9, -0.10, 0.85), (-55, 345, 52, 1, 3.6, 0.14, 0.8),
           (150, 520, 120, 0, 3.3, -0.05, 0.9), (-190, 560, 100, 0, 1.4, 0.07, 0.9), (0, 640, 90, 1, 0.3, 0.03, 0.85))
for idx, (x, y, hgt, k, rz, lean, slim) in enumerate(NEEDLES):
    src = SP[k]; bb = [Vector(c) for c in src.bound_box]
    xmin = min(v.x for v in bb); xmax = max(v.x for v in bb); L_ = xmax - xmin
    s_ = (hgt * 1.25) / L_
    me2 = src.data.copy(); ob = bpy.data.objects.new(f'needle{idx}', me2); sc.collection.objects.link(ob)
    # taper the scan to a point in Python (local -X is up once stood on end), with a slight bend
    co_ = np.empty(len(me2.vertices) * 3, np.float32); me2.vertices.foreach_get('co', co_); co_ = co_.reshape(-1, 3)
    cy_, cz_ = float(np.median(co_[:, 1])), float(np.median(co_[:, 2]))
    t_ = np.clip((co_[:, 0] - xmin) / L_, 0, 1)                     # 0 at the tip, 1 at the base
    sp = 0.03 + 2.1 * t_ ** 0.75
    bend = (rng.uniform(-1, 1) * 0.08 * L_) * (1 - t_) ** 2
    co_[:, 1] = cy_ + (co_[:, 1] - cy_) * sp + bend; co_[:, 2] = cz_ + (co_[:, 2] - cz_) * sp
    co_[:, 0] -= (xmin + xmax) / 2
    me2.vertices.foreach_set('co', co_.ravel()); me2.update()
    ob.rotation_euler = (lean, math.radians(90), rz); ob.scale = (s_, s_ * slim, s_ * slim)
    ob.location = (x, y, 0)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg)
    zmin = min((ev.matrix_world @ Vector(c)).z for c in ev.bound_box)
    ob.location.z += gh(x, y) - zmin - 0.2 * hgt                # a fifth of it under the field

for m_ in {sl.material for o_ in SP for sl in o_.material_slots if sl.material}:
    for n_ in m_.node_tree.nodes:
        if n_.type == 'NORMAL_MAP': n_.inputs['Strength'].default_value = 1.8
        if n_.type == 'BSDF_PRINCIPLED':
            src_ = n_.inputs['Base Color'].links[0].from_socket if n_.inputs['Base Color'].links else None
            if src_ is not None:
                hs_ = m_.node_tree.nodes.new('ShaderNodeHueSaturation'); hs_.inputs['Saturation'].default_value = 0.35
                hs_.inputs['Value'].default_value = arg('rockv', 1.4)
                m_.node_tree.links.new(src_, hs_.inputs['Color']); m_.node_tree.links.new(hs_.outputs[0], n_.inputs['Base Color'])

# ---------------------------------------------------------------- low mist lying over the far field, so the needles stand in layers
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1520, 40)); fog = bpy.context.object; fog.name = 'lowmist'; fog.scale = (4000, 2960, 100)
m, nt = mat('lowmist'); v_ = node(nt, 'ShaderNodeVolumePrincipled'); v_.inputs['Color'].default_value = (0.86, 0.89, 0.96, 1)
v_.inputs['Anisotropy'].default_value = arg('aniso', 0.7)
gq = node(nt, 'ShaderNodeNewGeometry'); sq = node(nt, 'ShaderNodeSeparateXYZ'); link(nt, gq.outputs['Position'], sq.inputs[0])
low_ = math_(nt, 'MULTIPLY', math_(nt, 'EXPONENT', math_(nt, 'DIVIDE', sq.outputs['Z'], -9.0)), arg('fogd', 0.009))
# banks: broad, flat-bottomed sheets of mist between the layers of needles (noise stretched sideways)
mpb = node(nt, 'ShaderNodeMapping'); mpb.inputs['Scale'].default_value = (1 / 260, 1 / 90, 1 / 26); link(nt, gq.outputs['Position'], mpb.inputs[0])
nzb = node(nt, 'ShaderNodeTexNoise'); nzb.inputs['Scale'].default_value = 1.0; nzb.inputs['Detail'].default_value = 3.0
link(nt, mpb.outputs[0], nzb.inputs['Vector'])
bank = maprange(nt, nzb.outputs['Fac'], 0.47, 0.62)
band = math_(nt, 'MULTIPLY', maprange(nt, sq.outputs['Z'], 4.0, 18.0), maprange(nt, sq.outputs['Z'], 30.0, 75.0, 1.0, 0.0))
far_ = maprange(nt, sq.outputs['Y'], 150.0, 260.0)
bank = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', bank, band), math_(nt, 'MULTIPLY', far_, arg('bankd', 0.03)))
# and mist gathered around the needles' feet and the far ridges, so nothing stands on a hard edge
base_ = math_(nt, 'MULTIPLY', math_(nt, 'EXPONENT', math_(nt, 'DIVIDE', sq.outputs['Z'], -arg('baseh', 20.0))),
              math_(nt, 'MULTIPLY', maprange(nt, sq.outputs['Y'], 140.0, 230.0), arg('based', 0.006)))
# thinning beyond about 1.5 km, so the far ranges stand as a soft skyline instead of a lit band of mist
thin_ = maprange(nt, sq.outputs['Y'], 1100.0, 2000.0, 1.0, 0.12)
link(nt, math_(nt, 'MULTIPLY', math_(nt, 'ADD', math_(nt, 'ADD', low_, bank), base_), thin_), v_.inputs['Density'])
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, v_.outputs[0], o.inputs['Volume']); fog.data.materials.append(m)

# ---------------------------------------------------------------- night sky, fading to the mist's colour at the horizon; moonlight
MISTC = (0.40, 0.40, 0.47)                 # the haze at first light: pale, a little cool
wld = bpy.data.worlds.new('sky'); sc.world = wld; wld.use_nodes = True; wn = wld.node_tree; wn.nodes.clear()
# the scanned sky at sunrise (belfast_sunset_puresky: a broken cloud deck lit from the horizon), turned so its
# sun stands between the needles and tipped a few degrees so it just clears the far ranges; graded so the top
# of the frame is clear deep cobalt and the low sky a band of gold to peach. No stars.
_us, _vs = 0.6045, 0.4893                    # where the scan's sun is (u, and v from the top)
_azm = (0.5 - _us) * 2 * math.pi; _elm = (0.5 - _vs) * math.pi
M_SUN = Vector((math.cos(_elm) * math.cos(_azm), math.cos(_elm) * math.sin(_azm), math.sin(_elm)))
_sa, _se = math.radians(arg('sunaz', 88.0)), math.radians(arg('sunel', 4.5))
SUN_DIR = Vector((math.cos(_se) * math.cos(_sa), math.cos(_se) * math.sin(_sa), math.sin(_se)))
_q = SUN_DIR.rotation_difference(M_SUN)       # the turn that brings the frame's sun onto the scan's
tc = node(wn, 'ShaderNodeTexCoord'); mpw = node(wn, 'ShaderNodeMapping'); mpw.inputs['Rotation'].default_value = _q.to_euler('XYZ')
env = node(wn, 'ShaderNodeTexEnvironment'); env.image = img(f'{PH}/belfast_sunset_puresky/belfast_sunset_puresky_2k.hdr')
link(wn, tc.outputs['Generated'], mpw.inputs[0]); link(wn, mpw.outputs[0], env.inputs['Vector'])
sepz = node(wn, 'ShaderNodeSeparateXYZ'); link(wn, tc.outputs['Generated'], sepz.inputs[0])
sat_ = node(wn, 'ShaderNodeHueSaturation'); sat_.inputs['Saturation'].default_value = 1.08; link(wn, env.outputs[0], sat_.inputs['Color'])
up_ = maprange(wn, sepz.outputs['Z'], 0.03, 0.55)                       # 0 at the horizon, 1 high overhead
tint_ = node(wn, 'ShaderNodeMix'); tint_.data_type = 'RGBA'; link(wn, up_, tint_.inputs['Factor'])
tint_.inputs[6].default_value = (1.14, 0.97, 0.82, 1); tint_.inputs[7].default_value = (0.52, 0.70, 1.22, 1)
tm_ = node(wn, 'ShaderNodeMix'); tm_.data_type = 'RGBA'; tm_.blend_type = 'MULTIPLY'; tm_.inputs['Factor'].default_value = 1
link(wn, sat_.outputs[0], tm_.inputs[6]); link(wn, tint_.outputs[2], tm_.inputs[7])
sk = node(wn, 'ShaderNodeVectorMath'); sk.operation = 'SCALE'; link(wn, tm_.outputs[2], sk.inputs[0]); sk.inputs['Scale'].default_value = arg('sky', 1.0)
hz = maprange(wn, sepz.outputs['Z'], 0.0, -0.05)                        # below the horizon only: haze
hzm = node(wn, 'ShaderNodeMix'); hzm.data_type = 'RGBA'; link(wn, hz, hzm.inputs['Factor'])
link(wn, sk.outputs[0], hzm.inputs[6]); hzm.inputs[7].default_value = (*MISTC, 1)
bg = node(wn, 'ShaderNodeBackground'); bg.inputs['Strength'].default_value = 1.0
link(wn, hzm.outputs[2], bg.inputs['Color']); wo = node(wn, 'ShaderNodeOutputWorld'); link(wn, bg.outputs[0], wo.inputs['Surface'])
# the low sun itself, gold, from behind the needles: it rims their sun edges, backlights the flowers and
# the mist, and edges the stone; the stone's face stays in the cool light of the sky
MOON_DIR = SUN_DIR                           # (the crystal's catch below looks for this direction)
print('SUN_DIR', SUN_DIR, 'mapping', tuple(_q.to_euler('XYZ')))
moon = bpy.data.lights.new('sun', 'SUN'); moon.energy = arg('sun', 5.0); moon.color = (1.0, 0.76, 0.52); moon.angle = math.radians(0.6)
mo = bpy.data.objects.new('sun', moon); sc.collection.objects.link(mo)
mo.rotation_euler = SUN_DIR.to_track_quat('Z', 'Y').to_euler()
# the crystal's catch of the moon: a small source along the mirror direction of the facet that best faces
# between the moon and the lens, seen by the crystal alone and only in its reflections
_dg = bpy.context.evaluated_depsgraph_get(); _ce = parts['crystal'].evaluated_get(_dg); _cm = _ce.to_mesh(); _M = _ce.matrix_world
_best = None
for f_ in _cm.polygons:
    c_ = _M @ f_.center; n_ = (_M.to_3x3() @ f_.normal).normalized(); V_ = (co.location - c_).normalized()
    if n_.dot(V_) < 0.15: continue
    _el = [(_M @ _cm.vertices[f_.vertices[(i + 1) % len(f_.vertices)]].co - _M @ _cm.vertices[f_.vertices[i]].co).length for i in range(len(f_.vertices))]
    if max(_el) < 6 * max(min(_el), 1e-5) or max(_el) < 0.04: continue          # only the long, narrow strips of the arrises
    L_ = (2 * n_.dot(V_) * n_ - V_).normalized(); sc_ = L_.dot(MOON_DIR) + 0.3 * L_.z
    if _best is None or sc_ > _best[0]: _best = (sc_, c_.copy(), L_.copy())
_ce.to_mesh_clear()
if _best and arg('catch', 160.0) > 0:
    kl = bpy.data.lights.new('catch', 'AREA'); kl.energy = arg('catch', 160.0); kl.color = (1.0, 0.80, 0.56); kl.shape = 'DISK'; kl.size = 0.06          # small: the arris draws it out into a line
    klo = bpy.data.objects.new('catch', kl); sc.collection.objects.link(klo); klo.location = _best[1] + _best[2] * 3.0
    klo.rotation_euler = (-_best[2]).to_track_quat('-Z', 'Y').to_euler()
    klo.visible_diffuse = False; klo.visible_camera = False
    _cc = bpy.data.collections.new('crystal_rx'); _cc.objects.link(parts['crystal']); klo.light_linking.receiver_collection = _cc
    klo.light_linking.blocker_collection = _cc                 # the stone around it casts no shadow from this one
    print('CATCH', _best[0], tuple(_best[2]))

# the sky's light on the stone's face, as a film crew would give it: a broad soft source above and to
# the left of the camera, linked to the stone alone so the field keeps its own light
fl_ = bpy.data.lights.new('face_fill', 'AREA'); fl_.energy = arg('fill', 85.0); fl_.color = (0.62, 0.74, 1.0)
fl_.shape = 'DISK'; fl_.size = 5.0
flo = bpy.data.objects.new('face_fill', fl_); sc.collection.objects.link(flo)
flo.location = STONE_AT + Vector((-3.5, -7.0, 5.5)); flo.rotation_euler = (STONE_AT + Vector((0, 0, 1.0)) - flo.location).to_track_quat('-Z', 'Y').to_euler()
flo.visible_camera = False; flo.visible_glossy = False
_lk = bpy.data.collections.new('face_fill_receivers'); _lk.objects.link(parts['stone'])
flo.light_linking.receiver_collection = _lk
lf_ = bpy.data.lights.new('left_fill', 'AREA'); lf_.energy = arg('lfill', 35.0); lf_.color = (0.58, 0.70, 1.0); lf_.shape = 'DISK'; lf_.size = 4.0
lfo = bpy.data.objects.new('left_fill', lf_); sc.collection.objects.link(lfo)
lfo.location = STONE_AT + Vector((-6.0, -4.5, 2.2)); lfo.rotation_euler = (STONE_AT + Vector((0, 0, 1.0)) - lfo.location).to_track_quat('-Z', 'Y').to_euler()
lfo.visible_camera = False; lfo.visible_glossy = False; lfo.light_linking.receiver_collection = _lk

# ---------------------------------------------------------------- frame positions for the page
bpy.context.view_layer.update()
info = {'w': W, 'h': H, 'paper': frame_rect(paper), 'stone': frame_rect(parts['stone']), 'crystal': frame_rect(parts['crystal']),
        'stone_disp': 2.0 / STONE_DEPTH}
json.dump(info, open(os.path.join(WORK, 'frame.json'), 'w'), indent=1); print('FRAME', info)

cycles(samples=SAMPLES, tl=TL, exposure=arg('exposure', 0.0), look='None', volume=True)
sc.cycles.volume_step_rate = arg('vstep', 4.0)
sc.cycles.transmission_bounces = 10
if arg('dry', 0): raise SystemExit
if arg('border', ''):                       # render only a region (fractions x0,y0,x1,y1 from the bottom left), for checks
    _b = [float(v) for v in arg('border', '').split(',')]
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_min_y, sc.render.border_max_x, sc.render.border_max_y = _b
mist_comp(MISTC, arg('mist', 0.25), 18, 620, sky_amount=0.0)
sc.world.mist_settings.falloff = 'LINEAR'
import time; t0 = time.time()
sc.render.filepath = RAW; bpy.ops.render.render(write_still=True); print('render seconds', round(time.time() - t0))
# no rain (the sky has cleared; the stone is still wet), no motes. base.png (no grain) feeds the loop
grade(RAW, os.path.join(WORK, 'base.png'), bloom=0.24, bloom_thr=0.5, halation=0.05, grain=0.0, vignette=0.34, lift=0.016, tint=(0.97, 1.0, 1.03), rain=0.0)
grade(RAW, OUT, bloom=0.24, bloom_thr=0.5, halation=0.05, grain=0.016, vignette=0.34, lift=0.016, tint=(0.97, 1.0, 1.03), rain=0.0)
if not arg('data', 0): raise SystemExit
codes = {m_: (1.0, 0.0) for m_ in PLANT_MATS}
codes.update({m_: (0.0, 0.5) for m_ in STONE_MATS}); codes.update({m_: (0.0, 1.0) for m_ in CRYSTAL_MATS}); codes['paper'] = (0.0, 0.75)
data_pass(os.path.join(WORK, 'data.png'), codes, hide=('lowmist',))
