# The world inside the crystal: a sunlit meadow under a huge sky, after rain.
# Rendered once as two layers so the page can move them separately:
#   --layer sky    the sky and its clouds (wind drifts them)
#   --layer grass  the grass with alpha (wind bends it)
# The camera is a pinhole whose image is linear in view tangent, so the page can look it up by the
# direction a ray leaves the stone: tx in [-0.62, 0.62], ty in [-0.30, 0.54].
#
# blender -b -P meadow.py -- --layer sky --out sky.exr [--res 50] [--samples 64]

import bpy, bmesh, math, random, sys, os, time
import numpy as np
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from helpers import S, V, G, material, MB

def arg(name, default):
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return a[a.index(name) + 1] if name in a else default

LAYER = arg('--layer', 'sky')
OUT = arg('--out', os.path.join(HERE, 'meadow_%s.exr' % LAYER))
RES = int(arg('--res', '100'))
SAMPLES = int(arg('--samples', '96'))
TL = float(arg('--tl', '0'))
NBLADES = int(arg('--blades', '260000'))
TW, TY0, TY1 = 0.62, -0.30, 0.54
CAM_H = 1.05

bpy.ops.wm.read_factory_settings(use_empty=True)
SC = bpy.context.scene
SUN_EL, SUN_AZ = math.radians(34.0), math.radians(72.0)    # high to the right: the clouds take form, the grass is side lit

def sun_dir():
    return Vector((math.sin(SUN_AZ) * math.cos(SUN_EL), math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)))

def world():
    wm = bpy.data.worlds.new('w'); SC.world = wm; wm.use_nodes = True; nt = wm.node_tree; nt.nodes.clear(); g = G(nt)
    # a painted sky, not a measured one: deep blue overhead, pale and clean at the horizon, a lift towards the sun
    tc = g.new('ShaderNodeTexCoord'); D = g.vm('NORMALIZE', V(g, tc.outputs['Generated']))
    dx, dy, dz = g.sep(D)
    sd = sun_dir()
    sdot = g.vm('DOT_PRODUCT', D, (sd.x, sd.y, sd.z))
    up = g.pow(g.sm(0.0, 0.42, dz), 0.55)
    sky = g.mix((0.45, 0.62, 0.92), (0.035, 0.13, 0.55), up)
    sky = g.mix(sky, (1.0, 0.98, 0.94), g.pow(g.max(sdot, 0.0), 6.0) * 0.35)
    sky = g.mix(sky, (0.16, 0.2, 0.12), g.sm(0.0, -0.02, dz))
    bg = g.new('ShaderNodeBackground'); bg.inputs[1].default_value = 1.0
    g.put(bg.inputs[0], sky)
    o = g.new('ShaderNodeOutputWorld'); nt.links.new(bg.outputs[0], o.inputs[0])
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 4.2; sun.angle = math.radians(1.2); sun.color = (1.0, 0.96, 0.9)
    so = bpy.data.objects.new('sun', sun); SC.collection.objects.link(so)
    so.rotation_euler = (-sun_dir()).to_track_quat('-Z', 'Y').to_euler()

def clouds():
    # cumulus: each cloud is a cluster of overlapping soft volumes (Cycles sums them), eroded by one
    # world-space noise so the cluster reads as a single body, with a flat base where it condenses
    m, g = material('cloud')
    tc = g.new('ShaderNodeTexCoord'); P = V(g, tc.outputs['Object'])
    gp = g.new('ShaderNodeNewGeometry'); Wp = V(g, gp.outputs['Position'])
    wx, wy, wz = g.sep(Wp)
    r = g.vm('LENGTH', P)
    n1, _ = g.noise(g.scale(Wp, 1.0 / 700.0), 1.0, detail=7.0, rough=0.58, dist=0.2)
    n2, _ = g.noise(g.scale(Wp, 1.0 / 90.0), 1.0, detail=4.0, rough=0.55)
    soft = 1.0 - g.sm(0.3, 1.0, r + (n1 - 0.5) * 1.1 + (n2 - 0.5) * 0.65)
    at = g.attr('base')[1]
    base = g.sm(0.0, 1.0, (wz - at) / 60.0)
    dens = g.sm(0.04, 0.6, soft) * base * 0.035
    pv = g.new('ShaderNodeVolumePrincipled'); pv.inputs['Color'].default_value = (1, 1, 1, 1)
    pv.inputs['Anisotropy'].default_value = 0.35
    g.put(pv.inputs['Density'], dens)
    g.out(None, pv.outputs[0])
    rng = random.Random(9)
    specs = [  # x, y (distance), base z, size, towering: a great heap off to the left, a few small ones, open blue between
        (-3400, 6200, 700, 1500, 1.9), (-5600, 7400, 760, 1000, 1.0), (4200, 6800, 900, 800, 0.9),
        (5600, 8200, 760, 600, 0.6), (900, 11000, 650, 380, 0.4), (-1500, 12000, 640, 360, 0.4),
        (2400, 3600, 2300, 520, 0.5), (-1200, 3300, 2700, 420, 0.4),
    ]
    for i, (x, y, z, s, tower) in enumerate(specs):
        nsub = int(8 + tower * 8)
        for k in range(nsub):
            sub = s * rng.uniform(0.3, 0.62)
            ox = rng.uniform(-1.15, 1.15) * s * (1.0 - 0.25 * k / nsub); oy = rng.uniform(-0.5, 0.5) * s
            oz = sub * 0.55 + abs(rng.gauss(0, 0.55)) * s * tower * (1.0 - abs(ox) / (1.35 * s))
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0)
            ob = bpy.context.active_object; ob.name = 'cloud%d_%d' % (i, k)
            ob.location = (x + ox, y + oy, z + oz); ob.scale = (sub * 1.15, sub, sub * 0.92)
            ob['base'] = float(z)
            ob.data.materials.append(m)
    # the attribute node reads the object property 'base'
    for n in m.node_tree.nodes:
        if n.bl_idname == 'ShaderNodeAttribute': n.attribute_type = 'OBJECT'

def terrain(x, y):
    near = np.clip((y - 50.0) / 250.0, 0, 1) ** 2
    far = np.clip((y - 380.0) / 320.0, 0, 1)
    return (near * (4.0 * np.sin(x / 110.0 + 0.6) + 2.2 * np.sin(x / 47.0 + 2.1) + 3.0)
            + far * (14.0 + 9.0 * np.sin(x / 160.0 + 1.3) + 4.0 * np.sin(x / 61.0)))

def grass():
    m, g = material('grass')
    c, f = g.attr('gcol')
    tc = g.new('ShaderNodeTexCoord')
    # tips paler and glowing where the sun comes through
    vtx, _ = g.attr('h')
    tip = S(g, vtx.k)
    col = g.mix(c, (0.42, 0.52, 0.16), tip * tip * 0.5)
    dif = g.new('ShaderNodeBsdfDiffuse'); g.put(dif.inputs['Color'], col)
    tr = g.new('ShaderNodeBsdfTranslucent'); g.put(tr.inputs['Color'], g.mix(col, (0.55, 0.75, 0.18), 0.35))
    gl = g.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.35; gl.inputs['Color'].default_value = (0.6, 0.65, 0.7, 1)
    mx = g.new('ShaderNodeMixShader'); mx.inputs[0].default_value = 0.42
    g.nt.links.new(dif.outputs[0], mx.inputs[1]); g.nt.links.new(tr.outputs[0], mx.inputs[2])
    mx2 = g.new('ShaderNodeMixShader'); mx2.inputs[0].default_value = 0.08
    g.nt.links.new(mx.outputs[0], mx2.inputs[1]); g.nt.links.new(gl.outputs[0], mx2.inputs[2])
    cam = g.new('ShaderNodeCameraData')
    fog = 1.0 - g.exp(S(g, cam.outputs['View Z Depth']) * (-1.0 / 520.0))
    hz = g.new('ShaderNodeEmission'); hz.inputs['Color'].default_value = (0.62, 0.74, 0.92, 1); hz.inputs['Strength'].default_value = 1.15
    mx3 = g.new('ShaderNodeMixShader'); g.put(mx3.inputs[0], fog * 0.85)
    g.nt.links.new(mx2.outputs[0], mx3.inputs[1]); g.nt.links.new(hz.outputs[0], mx3.inputs[2])
    g.out(mx3.outputs[0])
    rng = np.random.default_rng(3)
    # place blades inside the view: dense near, thinning to the far field
    N = NBLADES
    u = rng.random(N)
    dist = 1.1 * (700.0 / 1.1) ** (u ** 1.3)
    tx = rng.uniform(-TW * 1.08, TW * 1.08, N)
    X = tx * dist; Y = dist
    hgt = rng.uniform(0.35, 0.85, N) * (1.0 + 0.25 * np.sin(X * 0.21) * np.cos(Y * 0.17))
    wid = rng.uniform(0.004, 0.009, N) * (1 + dist * 0.025)
    # a few tall stems close by, rising past the eye into the sky, soft in the foreground
    NF = 420
    fd = rng.uniform(1.4, 7.0, NF); ftx = rng.uniform(-TW * 1.05, TW * 1.05, NF)
    X = np.concatenate([X, ftx * fd]); Y = np.concatenate([Y, fd]); dist = np.concatenate([dist, fd])
    hgt = np.concatenate([hgt, rng.uniform(0.9, 1.45, NF)]); wid = np.concatenate([wid, rng.uniform(0.0025, 0.005, NF)])
    N = N + NF
    flower = rng.random(N) < 0.03
    ZB = terrain(X, Y)
    lean_a = rng.uniform(0, 2 * np.pi, N); lean = rng.uniform(0.05, 0.4, N)
    # a light prevailing wind leans the field to the right
    lx = np.cos(lean_a) * lean + 0.22; ly = np.sin(lean_a) * lean
    rot = rng.uniform(0, np.pi, N)
    NSEG = 5
    verts = np.zeros((N, NSEG * 2 + 1, 3), np.float32)
    hh = np.zeros((N, NSEG * 2 + 1), np.float32)
    for k in range(NSEG + 1):
        s = k / NSEG
        bend = s * s
        cx = X + lx * hgt * bend; cy = Y + ly * hgt * bend; cz = ZB + hgt * s * (1 - 0.18 * lean * bend)
        w = wid * (1 - s) if k < NSEG else 0
        dx = np.cos(rot) * w * 0.5; dy = np.sin(rot) * w * 0.5
        if k < NSEG:
            verts[:, 2 * k] = np.stack([cx - dx, cy - dy, cz], -1); verts[:, 2 * k + 1] = np.stack([cx + dx, cy + dy, cz], -1)
            hh[:, 2 * k] = s; hh[:, 2 * k + 1] = s
        else:
            verts[:, 2 * k] = np.stack([cx, cy, cz], -1); hh[:, 2 * k] = 1.0
    nv = NSEG * 2 + 1
    faces = []
    for k in range(NSEG - 1):
        faces.append((2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2))
    faces_tri = [(2 * (NSEG - 1), 2 * (NSEG - 1) + 1, 2 * NSEG)]
    me = bpy.data.meshes.new('grass')
    allv = verts.reshape(-1, 3)
    me.vertices.add(len(allv)); me.vertices.foreach_set('co', allv.ravel())
    nq = len(faces); nf = nq + 1
    loops = []
    for b in range(1):
        pass
    base = (np.arange(N) * nv)[:, None]
    q = (np.array(faces)[None, :, :] + base[:, :, None]).reshape(-1, 4)
    t = (np.array(faces_tri)[None, :, :] + base[:, :, None]).reshape(-1, 3)
    me.loops.add(q.size + t.size)
    me.loops.foreach_set('vertex_index', np.concatenate([q.ravel(), t.ravel()]).astype(np.int32))
    npoly = len(q) + len(t)
    me.polygons.add(npoly)
    starts = np.concatenate([np.arange(len(q)) * 4, q.size + np.arange(len(t)) * 3]).astype(np.int32)
    sizes = np.concatenate([np.full(len(q), 4), np.full(len(t), 3)]).astype(np.int32)
    me.polygons.foreach_set('loop_start', starts)
    me.update(calc_edges=True)
    me.polygons.foreach_set('use_smooth', np.ones(npoly, bool))
    # per blade colour: fresh greens, a few paler seed heads; per vertex height along the blade
    gc = np.array([[0.07, 0.24, 0.03], [0.13, 0.33, 0.04], [0.2, 0.38, 0.06], [0.1, 0.27, 0.05], [0.32, 0.38, 0.12]])
    pick = rng.choice(len(gc), N, p=[0.25, 0.3, 0.2, 0.17, 0.08])
    bc = gc[pick] * rng.uniform(0.8, 1.15, (N, 1))
    bc[flower] = np.array([0.78, 0.78, 0.66]) * rng.uniform(0.85, 1.1, (int(flower.sum()), 1))
    patch = 0.5 + 0.5 * np.sin(X * 0.09 + np.sin(Y * 0.05) * 2.0) * np.cos(Y * 0.07 + X * 0.02)
    bc = bc * (0.8 + 0.4 * patch[:, None]) + np.array([0.05, 0.03, 0.0]) * (patch[:, None] ** 3)
    col = np.repeat(bc, nv, 0); col = np.concatenate([col, np.ones((len(col), 1))], 1).astype(np.float32)
    a = me.color_attributes.new('gcol', 'FLOAT_COLOR', 'POINT'); a.data.foreach_set('color', col.ravel())
    hcol = np.repeat(hh.reshape(-1, 1), 4, 1).astype(np.float32); hcol[:, 3] = 1
    a2 = me.color_attributes.new('h', 'FLOAT_COLOR', 'POINT'); a2.data.foreach_set('color', hcol.ravel())
    me.materials.append(m)
    ob = bpy.data.objects.new('grass', me); SC.collection.objects.link(ob)
    # the ground under it
    mg, gg = material('ground')
    gsh = gg.principled(Base_Color=(0.07, 0.17, 0.035), Roughness=0.8)
    camd = gg.new('ShaderNodeCameraData')
    fog = 1.0 - gg.exp(S(gg, camd.outputs['View Z Depth']) * (-1.0 / 520.0))
    hz = gg.new('ShaderNodeEmission'); hz.inputs['Color'].default_value = (0.62, 0.74, 0.92, 1); hz.inputs['Strength'].default_value = 1.15
    mx = gg.new('ShaderNodeMixShader'); gg.put(mx.inputs[0], fog * 0.85)
    gg.nt.links.new(gsh, mx.inputs[1]); gg.nt.links.new(hz.outputs[0], mx.inputs[2]); gg.out(mx.outputs[0])
    gm = MB(); nd, nt_ = 160, 120
    ds = 0.6 * (1400.0 / 0.6) ** (np.arange(nd) / (nd - 1)); ts = np.linspace(-0.8, 0.8, nt_)
    vv = [(t * d, d, float(terrain(np.array(t * d), np.array(d)))) for d in ds for t in ts]
    ff = [(i * nt_ + j, i * nt_ + j + 1, (i + 1) * nt_ + j + 1, (i + 1) * nt_ + j) for i in range(nd - 1) for j in range(nt_ - 1)]
    gm.add(vv, ff, 0); gm.build('ground', [mg], smooth=True)

def camera():
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); SC.collection.objects.link(cam); SC.camera = cam
    W, H = 2048, int(round(2048 * (TY1 - TY0) / (2 * TW)))
    SC.render.resolution_x, SC.render.resolution_y = W, H
    cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.lens = 18.0 / TW
    cd.shift_y = ((TY1 + TY0) / 2) / (2 * TW)
    cam.location = (0, 0, CAM_H); cam.rotation_euler = (math.radians(90), 0, 0)
    cd.clip_start = 0.05; cd.clip_end = 20000
    cd.dof.use_dof = True; cd.dof.focus_distance = 14.0; cd.dof.aperture_fstop = 7.0

def main():
    t0 = time.time()
    world(); camera()
    if LAYER == 'sky':
        clouds()
    else:
        grass()
        SC.render.film_transparent = True
    r = SC.render; r.engine = 'CYCLES'; r.resolution_percentage = RES
    r.threads_mode = 'FIXED'; r.threads = 4
    c = SC.cycles; c.device = 'CPU'; c.samples = SAMPLES; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.015
    if TL > 0: c.time_limit = TL
    c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'; c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    c.max_bounces = 12; c.diffuse_bounces = 3; c.glossy_bounces = 2; c.transmission_bounces = 4; c.volume_bounces = 8
    c.transparent_max_bounces = 16; c.volume_step_rate = 2.0; c.volume_max_steps = 512
    c.sample_clamp_indirect = 6.0; c.use_light_tree = True
    r.image_settings.file_format = 'OPEN_EXR'; r.image_settings.color_depth = '32'; r.image_settings.exr_codec = 'ZIP'
    r.image_settings.color_mode = 'RGBA'
    print('BUILD %.1fs' % (time.time() - t0)); sys.stdout.flush()
    t1 = time.time(); r.filepath = OUT; bpy.ops.render.render(write_still=True)
    print('RENDER %.1fs' % (time.time() - t1))

main()
