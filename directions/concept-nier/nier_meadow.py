# Concept Nier: first-frame draft.
# A quiet city long abandoned and gently reclaimed: tall concrete towers, some leaning or broken,
# hung with ivy and crowned with trees; a wide meadow of tall grass and wildflowers where the streets
# were; bright, soft, slightly washed daylight. The Break stands clean in the meadow, catching the light.
# Feeling only, after the city ruins of NieR: Automata; none of its assets, characters, logos or text.
#
# Blender 4.5 LTS, Cycles CPU. All third-party assets are CC0:
#   Poly Haven: kloppenheim_06_puresky (HDRI); grass_medium_01, grass_medium_02, celandine_01, flower_empodium,
#     flower_heliophila, dandelion_01, shrub_02, tree_small_02, island_tree_01, island_tree_02,
#     rock_moss_set_01 (scanned models)
#   ambientCG: Facade019A (concrete window grid), Concrete044B and Concrete031 (weathered concrete),
#     LeafSet017 (scanned ivy leaves), Moss002, Rock041 and Rock030 (the stone), Ground037, Grass004
# The Break geometry is Antimony's own (break-geometry.json).
#
# Run (always under the shared lock):
#   flock <scratch>/blender.lock nice -n 5 blender -b -P nier_meadow.py -- \
#     --ph <assets/polyhaven> --acg <assets/ambientcg> --out <final.png> [--res 1600x900 --samples 24 --time 420]
#   --dry builds the scene and exits without rendering.
import bpy, bmesh, math, json, os, re, sys, time
import numpy as np
from mathutils import Vector, Matrix, Euler

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    k = '--' + name
    return type(default)(argv[argv.index(k) + 1]) if k in argv else default

HERE = os.path.dirname(os.path.abspath(__file__))
PH = arg('ph', '')
ACG = arg('acg', '')
OUT = arg('out', '/tmp/nier.png')
RAW = arg('raw', OUT.replace('.png', '_raw.png'))
RES = arg('res', '1600x900')
SAMPLES = arg('samples', 24)
TIME = arg('time', 0.0)
DENS = arg('density', 1.0)
EXPO = arg('exposure', 0.15)
GEO = json.load(open(arg('geometry', os.path.join(HERE, 'break-geometry.json'))))
rng = np.random.default_rng(11)

# ------------------------------------------------------------------ scene and render settings
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
W, H = (int(v) for v in RES.split('x'))
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
sc.render.engine = 'CYCLES'
cy = sc.cycles
cy.device = 'CPU'; cy.samples = SAMPLES; cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.03
cy.time_limit = TIME
cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'; cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
cy.max_bounces = 8; cy.diffuse_bounces = 2; cy.glossy_bounces = 2
cy.transmission_bounces = 8; cy.transparent_max_bounces = 24; cy.volume_bounces = 0
cy.caustics_reflective = False; cy.caustics_refractive = False; cy.blur_glossy = 1.0
cy.use_light_tree = True
sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'None'; sc.view_settings.exposure = EXPO
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '16'
sc.render.image_settings.color_mode = 'RGB'
vl = sc.view_layers[0]; vl.use_pass_z = True

# ------------------------------------------------------------------ helpers
def mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); return m, nt
def node(nt, t, loc=(0, 0), **kw):
    n = nt.nodes.new(t); n.location = loc
    for k, v in kw.items():
        if k in n.inputs: n.inputs[k].default_value = v
        else: setattr(n, k, v)
    return n
def link(nt, a, b): nt.links.new(a, b)
def img(path, noncolor=False):
    im = bpy.data.images.load(path, check_existing=True)
    if noncolor: im.colorspace_settings.name = 'Non-Color'
    return im
def link_ob(ob, coll=None): (coll or sc.collection).objects.link(ob); return ob
def srgb2lin(c): return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92
def acg(asset, kind): return os.path.join(ACG, asset, f'{asset}_2K-JPG_{kind}.jpg')
def smooth(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def fbm(x, y, s=1.0, seed=0.0):
    # cheap smooth value field in numpy (sums of rotated sines), 0..1
    v = np.zeros_like(x, dtype=np.float64)
    for i, (f, a) in enumerate(((1.0, 0.5), (2.13, 0.25), (4.37, 0.125), (8.9, 0.0625))):
        th = 0.7 * i + seed
        u = (x * math.cos(th) - y * math.sin(th)) * f * s; w = (x * math.sin(th) + y * math.cos(th)) * f * s
        v += a * np.sin(u + 1.7 * np.sin(w * 0.8 + seed * 3.1) + seed) * np.cos(w * 0.9 - seed)
    return np.clip(0.5 + v, 0, 1)

# ------------------------------------------------------------------ sky: real HDRI, its sun replaced by a matched sun lamp
HDRI = os.path.join(PH, *arg('hdri', 'kloppenheim_06_puresky/kloppenheim_06_puresky_2k.hdr').split('/'))
hdr = img(HDRI)
px = np.array(hdr.pixels[:], dtype=np.float32).reshape(hdr.size[1], hdr.size[0], 4)
small = px[::8, ::8, :3].sum(2)
iy, ix = np.unravel_index(np.argmax(small), small.shape)
su, sv = (ix * 8 + 4) / hdr.size[0], (iy * 8 + 4) / hdr.size[1]
del px, small
src_az = (su - 0.5) * 2 * math.pi          # Blender equirect: u = atan2(y, -x) / 2pi + 0.5
sun_el = (sv - 0.5) * math.pi
SUN_AZ = math.radians(arg('sun-az', 212.0))  # target heading of the sun, measured from +X towards +Y
dst_az = math.atan2(math.sin(SUN_AZ), -math.cos(SUN_AZ))
print('hdri sun u v', round(su, 3), round(sv, 3), 'elev', round(math.degrees(sun_el), 1))
wld = bpy.data.worlds.new('sky'); sc.world = wld; wld.use_nodes = True
wn = wld.node_tree; wn.nodes.clear()
tc = node(wn, 'ShaderNodeTexCoord', (-900, 0)); mp = node(wn, 'ShaderNodeMapping', (-700, 0))
mp.inputs['Rotation'].default_value = (0, 0, dst_az - src_az)
env = node(wn, 'ShaderNodeTexEnvironment', (-500, 0)); env.image = hdr
link(wn, tc.outputs['Generated'], mp.inputs['Vector']); link(wn, mp.outputs['Vector'], env.inputs['Vector'])
# clamp the sun disc out of the sky (the lamp carries it) and wash the sky towards a pale, slightly warm white
clampn = node(wn, 'ShaderNodeMix', (-300, 0)); clampn.data_type = 'RGBA'; clampn.blend_type = 'DARKEN'
clampn.inputs['Factor'].default_value = 1.0; link(wn, env.outputs['Color'], clampn.inputs['A'])
clampn.inputs['B'].default_value = (arg('sky-clamp', 6.0),) * 3 + (1,)
wash = node(wn, 'ShaderNodeMix', (-100, 0)); wash.data_type = 'RGBA'; wash.blend_type = 'MIX'
wash.inputs['Factor'].default_value = arg('sky-wash', 0.16)
link(wn, clampn.outputs['Result'], wash.inputs['A']); wash.inputs['B'].default_value = (1.05, 1.02, 0.98, 1)
bg = node(wn, 'ShaderNodeBackground', (100, 0)); bg.inputs['Strength'].default_value = arg('sky', 1.0)
link(wn, wash.outputs['Result'], bg.inputs['Color'])
wo = node(wn, 'ShaderNodeOutputWorld', (300, 0)); link(wn, bg.outputs['Background'], wo.inputs['Surface'])
wld.cycles.sampling_method = 'MANUAL'; wld.cycles.sample_map_resolution = 1024
SUN_EL = math.radians(arg('sun-el', 36.0))
sdir = Vector((math.cos(SUN_EL) * math.cos(SUN_AZ), math.cos(SUN_EL) * math.sin(SUN_AZ), math.sin(SUN_EL)))
sun_d = bpy.data.lights.new('sun', 'SUN'); sun_d.energy = arg('sun', 5.2); sun_d.angle = math.radians(1.2)
sun_d.color = (1.0, 0.9, 0.76)
sun = link_ob(bpy.data.objects.new('sun', sun_d))
sun.rotation_euler = (-sdir).to_track_quat('-Z', 'Y').to_euler()

# ------------------------------------------------------------------ camera: a real 40 mm lens at eye height in the meadow
cam_d = bpy.data.cameras.new('cam'); cam = link_ob(bpy.data.objects.new('cam', cam_d)); sc.camera = cam
cam_d.lens = arg('lens', 40.0); cam_d.sensor_width = 36; cam_d.sensor_fit = 'HORIZONTAL'
CAM = Vector((0, 0, arg('eye', 1.45)))
cam.location = CAM
cam.rotation_euler = (math.pi / 2 + math.radians(arg('pitch', 5.0)), 0, math.radians(arg('cam-yaw', 0.0)))
cam_d.clip_start = 0.05; cam_d.clip_end = 5000
HALF = math.atan(18 / cam_d.lens) + math.radians(5)

# ------------------------------------------------------------------ the Break: exact geometry, dark honed scanned stone, glass crystal
S = 0.019; T = arg('thick', 0.46)
MX, MY = arg('mx', 2.5), arg('my', 12.5)
MYAW = math.radians(arg('yaw', -16.0))
def svg_poly(d):
    nums = [float(v) for v in re.findall(r'-?\d+\.?\d*', d)]
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
def to_xz(p): return ((p[0] - 50) * S, (100 - p[1]) * S)
def rrect(rx=22, n=14):
    pts = []
    for cx, cz, a0 in ((100 - rx, rx, -90), (100 - rx, 100 - rx, 0), (rx, 100 - rx, 90), (rx, rx, 180)):
        for i in range(n + 1):
            t = math.radians(a0 + 90 * i / n); pts.append((cx + rx * math.cos(t), cz + rx * math.sin(t)))
    return pts
def prism(name, pts2d, y0, y1):
    bm = bmesh.new()
    fr = [bm.verts.new((x, y0, z)) for x, z in pts2d]; bk = [bm.verts.new((x, y1, z)) for x, z in pts2d]
    bm.faces.new(fr[::-1]); bm.faces.new(bk)
    for i in range(len(pts2d)):
        j = (i + 1) % len(pts2d); bm.faces.new((fr[i], fr[j], bk[j], bk[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return link_ob(bpy.data.objects.new(name, me))
tile = prism('stone', [to_xz(p) for p in rrect()], -T / 2, T / 2)
cuts = [prism('cut_seam', [to_xz(p) for p in svg_poly(GEO['seam'])], -T, T),
        prism('cut_cav', [to_xz(p) for p in svg_poly(GEO['cav'])], -T, T)]
bv = tile.modifiers.new('arris', 'BEVEL'); bv.width = 0.016; bv.segments = 4; bv.limit_method = 'ANGLE'
bv.angle_limit = math.radians(35)
for c in cuts:
    md = tile.modifiers.new('cut', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = c
    c.hide_render = True; c.hide_viewport = True
gem = [to_xz(p) for p in svg_poly(GEO['gem'])]; cxz = to_xz((50, 51.5))
ZE, ZR = 0.04, T / 2 - 0.012
bm = bmesh.new()
fr = [bm.verts.new((x, -ZE, z)) for x, z in gem]; bk = [bm.verts.new((x, ZE, z)) for x, z in gem]
af = bm.verts.new((cxz[0], -ZR, cxz[1])); ab = bm.verts.new((cxz[0], ZR, cxz[1]))
for i in range(len(gem)):
    j = (i + 1) % len(gem)
    bm.faces.new((fr[i], fr[j], af)); bm.faces.new((bk[j], bk[i], ab)); bm.faces.new((fr[j], fr[i], bk[i], bk[j]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new('crystal'); bm.to_mesh(me); bm.free()
crystal = link_ob(bpy.data.objects.new('crystal', me))
bvc = crystal.modifiers.new('arris', 'BEVEL'); bvc.width = 0.0025; bvc.segments = 2; bvc.limit_method = 'ANGLE'
mark = link_ob(bpy.data.objects.new('mark', None))
mark.location = (MX, MY, -0.05); mark.rotation_euler = (0, 0, MYAW)
for o in [tile, crystal] + cuts: o.parent = mark

m_st, nt = mat('stone')
tco = node(nt, 'ShaderNodeTexCoord', (-1200, 0))
mpp = node(nt, 'ShaderNodeMapping', (-1000, 0)); mpp.inputs['Scale'].default_value = (0.9,) * 3
link(nt, tco.outputs['Object'], mpp.inputs['Vector'])
nz = node(nt, 'ShaderNodeTexNoise', (-1000, 500)); nz.inputs['Scale'].default_value = 1.6; nz.inputs['Detail'].default_value = 3
link(nt, tco.outputs['Object'], nz.inputs['Vector'])
nzr = node(nt, 'ShaderNodeMapRange', (-850, 500)); nzr.inputs['From Min'].default_value = 0.42; nzr.inputs['From Max'].default_value = 0.62
link(nt, nz.outputs['Fac'], nzr.inputs['Value'])
def boxtex(nt_, path, nc, vec):
    t = node(nt_, 'ShaderNodeTexImage'); t.image = img(path, nc); t.projection = 'BOX'; t.projection_blend = 0.25
    link(nt_, vec, t.inputs['Vector']); return t
def mixc(nt_, fac, a, b):
    m_ = node(nt_, 'ShaderNodeMix'); m_.data_type = 'RGBA'
    link(nt_, fac, m_.inputs['Factor']); link(nt_, a, m_.inputs['A']); link(nt_, b, m_.inputs['B']); return m_.outputs['Result']
V = mpp.outputs['Vector']
cd = mixc(nt, nzr.outputs['Result'], boxtex(nt, acg('Rock041', 'Color'), False, V).outputs['Color'], boxtex(nt, acg('Rock030', 'Color'), False, V).outputs['Color'])
crr = mixc(nt, nzr.outputs['Result'], boxtex(nt, acg('Rock041', 'Roughness'), True, V).outputs['Color'], boxtex(nt, acg('Rock030', 'Roughness'), True, V).outputs['Color'])
cn = mixc(nt, nzr.outputs['Result'], boxtex(nt, acg('Rock041', 'NormalGL'), True, V).outputs['Color'], boxtex(nt, acg('Rock030', 'NormalGL'), True, V).outputs['Color'])
hsv = node(nt, 'ShaderNodeHueSaturation'); hsv.inputs['Saturation'].default_value = 0.1
hsv.inputs['Value'].default_value = arg('st-val', 0.13); link(nt, cd, hsv.inputs['Color'])
rr = node(nt, 'ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.24; rr.inputs['To Max'].default_value = 0.46
link(nt, crr, rr.inputs['Value'])
nm = node(nt, 'ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.55; link(nt, cn, nm.inputs['Color'])
bvn = node(nt, 'ShaderNodeBevel'); bvn.samples = 6; bvn.inputs['Radius'].default_value = 0.004
link(nt, nm.outputs['Normal'], bvn.inputs['Normal'])
bsdf = node(nt, 'ShaderNodeBsdfPrincipled'); bsdf.inputs['Specular IOR Level'].default_value = 0.55
link(nt, hsv.outputs['Color'], bsdf.inputs['Base Color']); link(nt, rr.outputs['Result'], bsdf.inputs['Roughness'])
link(nt, bvn.outputs['Normal'], bsdf.inputs['Normal'])
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, bsdf.outputs['BSDF'], o.inputs['Surface'])
m_in = m_st.copy(); m_in.name = 'stone_cut'
for n_ in m_in.node_tree.nodes:
    if n_.bl_idname == 'ShaderNodeHueSaturation': n_.inputs['Value'].default_value = 0.07
    if n_.bl_idname == 'ShaderNodeMapRange' and n_.inputs['To Min'].default_value == 0.24:
        n_.inputs['To Min'].default_value = 0.6; n_.inputs['To Max'].default_value = 0.8
dg = bpy.context.evaluated_depsgraph_get()
me_cut = bpy.data.meshes.new_from_object(tile.evaluated_get(dg))
tile.modifiers.clear(); tile.data = me_cut
me_cut.materials.clear(); me_cut.materials.append(m_st); me_cut.materials.append(m_in)
HX = 50 * S; RC = 22 * S; ZC = 50 * S
def rr_sdf(x, z):
    qx = abs(x) - (HX - RC); qz = abs(z - ZC) - (HX - RC)
    return math.hypot(max(qx, 0), max(qz, 0)) + min(max(qx, qz), 0) - RC
for f in me_cut.polygons:
    f.material_index = 1 if (abs(f.normal.y) < 0.6 and rr_sdf(f.center.x, f.center.z) < -0.012) else 0
tile.modifiers.new('wn', 'WEIGHTED_NORMAL')

SKY = [srgb2lin(v / 255) for v in (0x94, 0xE6, 0xFF)]
m_cr, nt = mat('crystal')
b = node(nt, 'ShaderNodeBsdfPrincipled')
b.inputs['Base Color'].default_value = (*[v ** 1.6 for v in SKY], 1)
b.inputs['Subsurface Weight'].default_value = 1.0; b.inputs['Subsurface Radius'].default_value = (0.35, 0.8, 1.0)
b.inputs['Subsurface Scale'].default_value = 0.12
b.inputs['Transmission Weight'].default_value = 0.92; b.inputs['Roughness'].default_value = 0.12
b.inputs['IOR'].default_value = 1.52; b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.02
emc = node(nt, 'ShaderNodeEmission'); emc.inputs['Color'].default_value = (*SKY, 1); emc.inputs['Strength'].default_value = arg('cr-glow', 0.25)
ad = node(nt, 'ShaderNodeAddShader'); link(nt, b.outputs['BSDF'], ad.inputs[0]); link(nt, emc.outputs['Emission'], ad.inputs[1])
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, ad.outputs['Shader'], o.inputs['Surface'])
crystal.data.materials.append(m_cr)

# ------------------------------------------------------------------ ground: scanned soil near, scanned turf far
bpy.ops.mesh.primitive_plane_add(size=1); gnd = bpy.context.object; gnd.name = 'ground'
gnd.scale = (3000, 3000, 1); gnd.location = (0, 1200, 0)
m_g, nt = mat('ground')
gp = node(nt, 'ShaderNodeNewGeometry')
def wmap(scale):
    m_ = node(nt, 'ShaderNodeMapping'); m_.inputs['Scale'].default_value = (scale,) * 3
    link(nt, gp.outputs['Position'], m_.inputs['Vector']); return m_.outputs['Vector']
def flat(path, nc, vec):
    t = node(nt, 'ShaderNodeTexImage'); t.image = img(path, nc); link(nt, vec, t.inputs['Vector']); return t.outputs['Color']
v1, v2 = wmap(0.45), wmap(0.08)
lp = node(nt, 'ShaderNodeLightPath')
far = node(nt, 'ShaderNodeMapRange'); far.inputs['From Min'].default_value = 12; far.inputs['From Max'].default_value = 40
cam_dist = node(nt, 'ShaderNodeVectorMath', operation='DISTANCE'); cam_dist.inputs[1].default_value = CAM
link(nt, gp.outputs['Position'], cam_dist.inputs[0]); link(nt, cam_dist.outputs['Value'], far.inputs['Value'])
gc = mixc(nt, far.outputs['Result'], flat(acg('Ground037', 'Color'), False, v1), flat(acg('Grass004', 'Color'), False, v2))
gr = mixc(nt, far.outputs['Result'], flat(acg('Ground037', 'Roughness'), True, v1), flat(acg('Grass004', 'Roughness'), True, v2))
gn_ = mixc(nt, far.outputs['Result'], flat(acg('Ground037', 'NormalGL'), True, v1), flat(acg('Grass004', 'NormalGL'), True, v2))
ghs = node(nt, 'ShaderNodeHueSaturation'); ghs.inputs['Value'].default_value = 0.8; link(nt, gc, ghs.inputs['Color'])
nmg = node(nt, 'ShaderNodeNormalMap'); link(nt, gn_, nmg.inputs['Color'])
bg_ = node(nt, 'ShaderNodeBsdfPrincipled')
link(nt, ghs.outputs['Color'], bg_.inputs['Base Color']); link(nt, gr, bg_.inputs['Roughness']); link(nt, nmg.outputs['Normal'], bg_.inputs['Normal'])
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, bg_.outputs['BSDF'], o.inputs['Surface'])
gnd.data.materials.append(m_g)

# ------------------------------------------------------------------ concrete towers: slabs dressed with scanned facade and concrete
def tower_material(name, val=1.0):
    m, nt_ = mat(name)
    gp_ = node(nt_, 'ShaderNodeTexCoord')
    def mp_(s):
        m2 = node(nt_, 'ShaderNodeMapping'); m2.inputs['Scale'].default_value = (s,) * 3
        link(nt_, gp_.outputs['Object'], m2.inputs['Vector']); return m2.outputs['Vector']
    vf, vc, vm = mp_(1 / 13.0), mp_(1 / 3.0), mp_(1 / 2.0)
    f_col = boxtex(nt_, acg('Facade019A', 'Color'), False, vf); f_rou = boxtex(nt_, acg('Facade019A', 'Roughness'), True, vf)
    f_nor = boxtex(nt_, acg('Facade019A', 'NormalGL'), True, vf)
    c_col = boxtex(nt_, acg('Concrete044B', 'Color'), False, vc); c_nor = boxtex(nt_, acg('Concrete044B', 'NormalGL'), True, vc)
    c2_col = boxtex(nt_, acg('Concrete031', 'Color'), False, mp_(1 / 4.0))
    mo_col = boxtex(nt_, acg('Moss002', 'Color'), False, vm)
    # glazing mask: the blue panes of the scan become empty, dark rooms
    sep = node(nt_, 'ShaderNodeSeparateColor'); link(nt_, f_col.outputs['Color'], sep.inputs['Color'])
    bmr = node(nt_, 'ShaderNodeMath', operation='SUBTRACT'); link(nt_, sep.outputs['Blue'], bmr.inputs[0]); link(nt_, sep.outputs['Red'], bmr.inputs[1])
    win = node(nt_, 'ShaderNodeMapRange'); win.inputs['From Min'].default_value = 0.015; win.inputs['From Max'].default_value = 0.06
    link(nt_, bmr.outputs['Value'], win.inputs['Value'])
    ob_ = node(nt_, 'ShaderNodeObjectInfo')
    # concrete body: the facade frame retextured with two weathered concrete scans, broken up by a large noise
    nzc = node(nt_, 'ShaderNodeTexNoise'); nzc.inputs['Scale'].default_value = 0.05; nzc.inputs['Detail'].default_value = 5
    link(nt_, gp_.outputs['Object'], nzc.inputs['Vector'])
    conc = mixc(nt_, nzc.outputs['Fac'], c_col.outputs['Color'], c2_col.outputs['Color'])
    frame = node(nt_, 'ShaderNodeMix'); frame.data_type = 'RGBA'; frame.blend_type = 'OVERLAY'; frame.inputs['Factor'].default_value = 0.6
    link(nt_, conc, frame.inputs['A']); link(nt_, f_col.outputs['Color'], frame.inputs['B'])
    room = node(nt_, 'ShaderNodeMix'); room.data_type = 'RGBA'
    link(nt_, win.outputs['Result'], room.inputs['Factor']); link(nt_, frame.outputs['Result'], room.inputs['A'])
    room.inputs['B'].default_value = (0.018, 0.019, 0.02, 1)
    # rain streaks running down from every ledge: noise stretched vertically
    st_map = node(nt_, 'ShaderNodeMapping'); st_map.inputs['Scale'].default_value = (0.9, 0.9, 0.035)
    link(nt_, gp_.outputs['Object'], st_map.inputs['Vector'])
    st = node(nt_, 'ShaderNodeTexNoise'); st.inputs['Scale'].default_value = 1.0; st.inputs['Detail'].default_value = 6
    link(nt_, st_map.outputs['Vector'], st.inputs['Vector'])
    stm = node(nt_, 'ShaderNodeMapRange'); stm.inputs['From Min'].default_value = 0.35; stm.inputs['From Max'].default_value = 0.75
    stm.inputs['To Min'].default_value = 1.05; stm.inputs['To Max'].default_value = 0.5
    link(nt_, st.outputs['Fac'], stm.inputs['Value'])
    dark = node(nt_, 'ShaderNodeMix'); dark.data_type = 'RGBA'; dark.blend_type = 'MULTIPLY'; dark.inputs['Factor'].default_value = 1
    link(nt_, room.outputs['Result'], dark.inputs['A']); link(nt_, stm.outputs['Result'], dark.inputs['B'])
    # green creep: moss on every upward face, and greening at the foot of the walls
    gm = node(nt_, 'ShaderNodeNewGeometry')
    nzz = node(nt_, 'ShaderNodeSeparateXYZ'); link(nt_, gm.outputs['Normal'], nzz.inputs['Vector'])
    up = node(nt_, 'ShaderNodeMapRange'); up.inputs['From Min'].default_value = 0.5; up.inputs['From Max'].default_value = 0.8
    link(nt_, nzz.outputs['Z'], up.inputs['Value'])
    pz = node(nt_, 'ShaderNodeSeparateXYZ'); link(nt_, gm.outputs['Position'], pz.inputs['Vector'])
    foot = node(nt_, 'ShaderNodeMapRange'); foot.inputs['From Min'].default_value = 14; foot.inputs['From Max'].default_value = 0
    link(nt_, pz.outputs['Z'], foot.inputs['Value'])
    nzf = node(nt_, 'ShaderNodeTexNoise'); nzf.inputs['Scale'].default_value = 0.12; nzf.inputs['Detail'].default_value = 4
    link(nt_, gm.outputs['Position'], nzf.inputs['Vector'])
    ff = node(nt_, 'ShaderNodeMath', operation='MULTIPLY'); link(nt_, foot.outputs['Result'], ff.inputs[0]); link(nt_, nzf.outputs['Fac'], ff.inputs[1])
    gmax = node(nt_, 'ShaderNodeMath', operation='MAXIMUM'); link(nt_, up.outputs['Result'], gmax.inputs[0]); link(nt_, ff.outputs['Value'], gmax.inputs[1])
    mossy = mixc(nt_, gmax.outputs['Value'], dark.outputs['Result'], mo_col.outputs['Color'])
    hs_ = node(nt_, 'ShaderNodeHueSaturation'); hs_.inputs['Saturation'].default_value = 0.75; hs_.inputs['Value'].default_value = val
    link(nt_, mossy, hs_.inputs['Color'])
    nmix = mixc(nt_, nzc.outputs['Fac'], f_nor.outputs['Color'], c_nor.outputs['Color'])
    nm_ = node(nt_, 'ShaderNodeNormalMap'); nm_.inputs['Strength'].default_value = 0.9; link(nt_, nmix, nm_.inputs['Color'])
    bvl = node(nt_, 'ShaderNodeBevel'); bvl.samples = 4; bvl.inputs['Radius'].default_value = 0.08
    link(nt_, nm_.outputs['Normal'], bvl.inputs['Normal'])
    rgh = node(nt_, 'ShaderNodeMapRange'); rgh.inputs['To Min'].default_value = 0.7; rgh.inputs['To Max'].default_value = 0.95
    link(nt_, f_rou.outputs['Color'], rgh.inputs['Value'])
    p_ = node(nt_, 'ShaderNodeBsdfPrincipled'); p_.inputs['Specular IOR Level'].default_value = 0.35
    link(nt_, hs_.outputs['Color'], p_.inputs['Base Color']); link(nt_, rgh.outputs['Result'], p_.inputs['Roughness'])
    link(nt_, bvl.outputs['Normal'], p_.inputs['Normal'])
    o_ = node(nt_, 'ShaderNodeOutputMaterial'); link(nt_, p_.outputs['BSDF'], o_.inputs['Surface'])
    return m
M_TOWER = tower_material('tower', arg('con-val', 0.95))

# x, y (metres from camera), width, depth, height, yaw, lean about x, lean about y (deg), broken top (dx, dz slope)
TOWERS = [
    (72, 230, 26, 22, 150, 8, -2, -6.5, None),            # near right: leaning towards the gap
    (128, 395, 30, 24, 118, 20, 0, 0, (0.55, 18)),      # far right: top sheared off
    (-36, 560, 26, 26, 165, -6, 0, 2.5, (-0.4, 26)),     # centre left, deep in the haze
    (-104, 300, 24, 26, 104, 14, 0, 4.5, (0.7, 14)),      # left: broken, trees on the break
    (-215, 470, 22, 22, 82, -10, 0, 0, None),            # far left, low
    (24, 760, 30, 30, 150, 4, 0, -3, (0.3, 20)),          # far centre, almost gone in haze
    (210, 640, 26, 26, 125, -12, 0, 0, None),            # far right edge
]
towers = []
for k, (tx, ty, tw, td, th, yaw, lx, ly, brk) in enumerate(TOWERS):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(tw, td, th), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, 0, th / 2 - 6), verts=bm.verts)      # foundations sunk 6 m
    me = bpy.data.meshes.new(f'tower{k}'); bm.to_mesh(me); bm.free()
    ob = link_ob(bpy.data.objects.new(f'tower{k}', me)); me.materials.append(M_TOWER)
    ob.location = (tx, ty, 0)
    ob.rotation_euler = Euler((math.radians(lx), math.radians(ly), math.radians(yaw)), 'XYZ')
    if brk:
        slope, depth = brk
        cutter_me = bpy.data.meshes.new(f'cut{k}'); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(tw * 3, td * 3, 60), verts=bm.verts); bm.to_mesh(cutter_me); bm.free()
        cut = link_ob(bpy.data.objects.new(f'cut{k}', cutter_me))
        cut.parent = ob
        cut.location = (0, 0, th - 6 - depth / 2 + 30)
        cut.rotation_euler = (math.radians(rng.uniform(-6, 6)), math.atan(slope * depth / tw), 0)
        md = ob.modifiers.new('break', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'FAST'; md.object = cut
        cut.hide_render = True; cut.hide_viewport = True
    bvm = ob.modifiers.new('arris', 'BEVEL'); bvm.width = 0.25; bvm.segments = 2; bvm.limit_method = 'ANGLE'
    towers.append((ob, tw, td, th))
bpy.context.view_layer.update()

# low ruins in the meadow (off in this draft: they read as flat bars)
for k, (rx_, ry_, rw, rh, ryaw, rtilt) in enumerate([(-15, 46, 9, 2.6, 18, 4), (24, 64, 14, 3.4, -8, -3), (-40, 92, 18, 5.5, 6, 2),
                                                      (46, 120, 10, 4.0, 30, 0), (-6, 150, 22, 3.0, -4, 0)][:arg('ruins', 0)]):
    bpy.ops.mesh.primitive_cube_add(size=1)
    w_ = bpy.context.object; w_.name = f'ruin{k}'
    w_.scale = (rw, 0.45, rh); w_.location = (rx_, ry_, rh / 2 - 0.5)
    w_.rotation_euler = (math.radians(rtilt), 0, math.radians(ryaw))
    bpy.ops.object.transform_apply(scale=True)
    w_.data.materials.append(M_TOWER)
    b_ = w_.modifiers.new('arris', 'BEVEL'); b_.width = 0.06; b_.segments = 2

# ------------------------------------------------------------------ Poly Haven loaders
def ph_objects(asset, names, res='2k'):
    path = os.path.join(PH, asset, f'{asset}_{res}.blend')
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names]
    out = []
    for ob in dst.objects:
        if ob is None: continue
        ob.location = (0, 0, 0); ob.rotation_euler = (0, 0, 0); ob.parent = None
        for md_ in list(ob.modifiers): ob.modifiers.remove(md_)
        out.append(ob)
    return out
def library(name, obs):
    c = bpy.data.collections.new(name); sc.collection.children.link(c)
    for ob in obs: c.objects.link(ob)
    c.hide_render = True
    return c

def instancer(name, coll, pts, rot, scl, pick):
    m = len(pts)
    me = bpy.data.meshes.new(name); me.vertices.add(m); me.vertices.foreach_set('co', pts.astype(np.float32).ravel())
    for an, data, tp in (('rot', rot, 'FLOAT_VECTOR'), ('scl', scl, 'FLOAT_VECTOR'), ('pick', pick, 'INT')):
        at = me.attributes.new(an, tp, 'POINT')
        at.data.foreach_set('vector' if tp == 'FLOAT_VECTOR' else 'value', data.astype(np.int32 if tp == 'INT' else np.float32).ravel())
    ob = link_ob(bpy.data.objects.new(name, me))
    ng = bpy.data.node_groups.new(name + '_gn', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    gi = ng.nodes.new('NodeGroupInput'); go = ng.nodes.new('NodeGroupOutput')
    m2p = ng.nodes.new('GeometryNodeMeshToPoints')
    ci = ng.nodes.new('GeometryNodeCollectionInfo'); ci.inputs['Collection'].default_value = coll
    ci.inputs['Separate Children'].default_value = True; ci.inputs['Reset Children'].default_value = True
    iop = ng.nodes.new('GeometryNodeInstanceOnPoints'); iop.inputs['Pick Instance'].default_value = True
    L = ng.links
    L.new(gi.outputs[0], m2p.inputs['Mesh']); L.new(m2p.outputs['Points'], iop.inputs['Points']); L.new(ci.outputs[0], iop.inputs['Instance'])
    for an, dt, sock in (('rot', 'FLOAT_VECTOR', 'Rotation'), ('scl', 'FLOAT_VECTOR', 'Scale'), ('pick', 'INT', 'Instance Index')):
        nn = ng.nodes.new('GeometryNodeInputNamedAttribute'); nn.data_type = dt; nn.inputs['Name'].default_value = an
        L.new(nn.outputs['Attribute'], iop.inputs[sock])
    L.new(iop.outputs['Instances'], go.inputs[0])
    md_ = ob.modifiers.new('scatter', 'NODES'); md_.node_group = ng
    print(name, m, 'instances'); return ob

# ------------------------------------------------------------------ ivy: scanned leaves (ambientCG LeafSet017) hung on the towers
LEAF_BOX = [(0.051, 0.016, 0.379, 0.324), (0.621, 0.055, 0.871, 0.316), (0.063, 0.371, 0.406, 0.680),
            (0.625, 0.395, 0.910, 0.637), (0.590, 0.691, 0.898, 0.977), (0.043, 0.695, 0.430, 0.988)]
m_ivy, nt = mat('ivy')
uv = node(nt, 'ShaderNodeUVMap'); uv.uv_map = 'UVMap'
ic = node(nt, 'ShaderNodeTexImage'); ic.image = img(acg('LeafSet017', 'Color')); link(nt, uv.outputs['UV'], ic.inputs['Vector'])
ia = node(nt, 'ShaderNodeTexImage'); ia.image = img(acg('LeafSet017', 'Opacity'), True); link(nt, uv.outputs['UV'], ia.inputs['Vector'])
inn = node(nt, 'ShaderNodeTexImage'); inn.image = img(acg('LeafSet017', 'NormalGL'), True); link(nt, uv.outputs['UV'], inn.inputs['Vector'])
at = node(nt, 'ShaderNodeAttribute'); at.attribute_name = 'lv'; at.attribute_type = 'GEOMETRY'
ihs = node(nt, 'ShaderNodeHueSaturation'); link(nt, ic.outputs['Color'], ihs.inputs['Color'])
hmap = node(nt, 'ShaderNodeMapRange'); hmap.inputs['To Min'].default_value = 0.47; hmap.inputs['To Max'].default_value = 0.53
link(nt, at.outputs['Fac'], hmap.inputs['Value']); link(nt, hmap.outputs['Result'], ihs.inputs['Hue'])
vmap = node(nt, 'ShaderNodeMapRange'); vmap.inputs['To Min'].default_value = 0.45; vmap.inputs['To Max'].default_value = 0.8
link(nt, at.outputs['Fac'], vmap.inputs['Value']); link(nt, vmap.outputs['Result'], ihs.inputs['Value'])
ip = node(nt, 'ShaderNodeBsdfPrincipled'); ip.inputs['Roughness'].default_value = 0.5
link(nt, ihs.outputs['Color'], ip.inputs['Base Color'])
inm = node(nt, 'ShaderNodeNormalMap'); link(nt, inn.outputs['Color'], inm.inputs['Color']); link(nt, inm.outputs['Normal'], ip.inputs['Normal'])
itr = node(nt, 'ShaderNodeBsdfTranslucent'); link(nt, ihs.outputs['Color'], itr.inputs['Color'])
im1 = node(nt, 'ShaderNodeMixShader'); im1.inputs['Fac'].default_value = 0.3
link(nt, ip.outputs['BSDF'], im1.inputs[1]); link(nt, itr.outputs['BSDF'], im1.inputs[2])
itp = node(nt, 'ShaderNodeBsdfTransparent')
im2 = node(nt, 'ShaderNodeMixShader'); link(nt, ia.outputs['Color'], im2.inputs['Fac'])
link(nt, itp.outputs['BSDF'], im2.inputs[1]); link(nt, im1.outputs['Shader'], im2.inputs[2])
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, im2.outputs['Shader'], o.inputs['Surface'])

def ivy_on_tower(ob, tw, td, th, count):
    # points on the four walls in local space; ivy climbs from the foot in uneven curtains and
    # pours down from the broken top and the ledges
    mw = ob.matrix_world
    face = rng.integers(0, 4, count * 3)
    u = rng.uniform(-0.5, 0.5, count * 3)
    z = rng.uniform(-6, th - 6, count * 3)
    width = np.where(face < 2, tw, td)
    s = u * width + face * 97.0
    climb = 5 + 30 * fbm(s, np.zeros_like(s), 0.05, ob.location.x * 0.01) ** 1.4
    hang = 2 + 26 * fbm(s, np.ones_like(s) * 3, 0.07, 1.3 + ob.location.y * 0.01) ** 2.2
    top = th - 6
    p = np.maximum(1 - smooth(climb * 0.75, climb, z), 1 - smooth(hang * 0.7, hang, top - z))
    p = np.maximum(p, 0.5 * (fbm(s, z, 0.12, 2.0) > 0.86))
    keep = rng.uniform(0, 1, len(p)) < p
    face, u, z, width = face[keep][:count], u[keep][:count], z[keep][:count], width[keep][:count]
    n = len(face)
    lx = np.where(face == 0, u * tw, np.where(face == 1, -u * tw, np.where(face == 2, tw / 2, -tw / 2)))
    ly = np.where(face == 0, -td / 2, np.where(face == 1, td / 2, np.where(face == 2, u * td, -u * td)))
    nx = np.select([face == 2, face == 3], [1.0, -1.0], 0.0); ny = np.select([face == 0, face == 1], [-1.0, 1.0], 0.0)
    off = rng.uniform(0.03, 0.35, n)
    P = np.stack([lx + nx * off, ly + ny * off, z], 1)
    return P, np.stack([nx, ny, np.zeros(n)], 1), n

def build_leaves(name, P, N, size, wall_frame):
    # one quad per leaf, lying roughly along the wall, tilted outwards and drooping, from the scanned atlas
    n = len(P)
    side = np.cross(N, np.array([0, 0, 1.0])); side /= np.linalg.norm(side, axis=1, keepdims=True) + 1e-9
    up = np.tile(np.array([0, 0, 1.0]), (n, 1))
    a = rng.uniform(0, 2 * math.pi, n)
    tilt = rng.uniform(0.25, 0.8, n)
    dirv = (np.cos(a)[:, None] * side + np.sin(a)[:, None] * up) * np.cos(tilt)[:, None] + N * np.sin(tilt)[:, None]
    dirv = dirv - up * 0.35; dirv /= np.linalg.norm(dirv, axis=1, keepdims=True)
    perp = np.cross(N, dirv); perp /= np.linalg.norm(perp, axis=1, keepdims=True) + 1e-9
    L = size * rng.uniform(0.7, 1.3, n)
    box = np.array(LEAF_BOX)[rng.integers(0, 6, n)]
    asp = (box[:, 2] - box[:, 0]) / (box[:, 3] - box[:, 1])
    Wd = L * asp
    p0 = P - perp * (Wd / 2)[:, None]; p1 = P + perp * (Wd / 2)[:, None]
    p2 = p1 + dirv * L[:, None]; p3 = p0 + dirv * L[:, None]
    V_ = np.stack([p0, p1, p2, p3], 1).reshape(-1, 3)
    if wall_frame is not None:
        V_ = (np.array(wall_frame)[:3, :3] @ V_.T).T + np.array(wall_frame)[:3, 3]
    me = bpy.data.meshes.new(name)
    me.vertices.add(n * 4); me.vertices.foreach_set('co', V_.astype(np.float32).ravel())
    me.loops.add(n * 4); me.loops.foreach_set('vertex_index', np.arange(n * 4, dtype=np.int32))
    me.polygons.add(n); me.polygons.foreach_set('loop_start', np.arange(0, n * 4, 4, dtype=np.int32))
    me.polygons.foreach_set('loop_total', np.full(n, 4, np.int32))
    me.update(calc_edges=True)
    uvl = me.uv_layers.new(name='UVMap')
    U = np.stack([np.stack([box[:, 0], 1 - box[:, 3]], 1), np.stack([box[:, 2], 1 - box[:, 3]], 1),
                  np.stack([box[:, 2], 1 - box[:, 1]], 1), np.stack([box[:, 0], 1 - box[:, 1]], 1)], 1)
    uvl.data.foreach_set('uv', U.astype(np.float32).ravel())
    lv = me.attributes.new('lv', 'FLOAT', 'FACE'); lv.data.foreach_set('value', rng.uniform(0, 1, n).astype(np.float32))
    me.materials.append(m_ivy)
    ob = link_ob(bpy.data.objects.new(name, me)); print(name, n, 'leaves'); return ob

IVY = arg('ivy', 26000)
dg = bpy.context.evaluated_depsgraph_get()
for k, (ob, tw, td, th) in enumerate(towers):
    dist = ob.location.length
    size = 0.5 * max(1.0, dist / 260)          # leaves grow with distance so the curtains read through the haze
    P, N, n = ivy_on_tower(ob, tw, td, th, int(IVY * DENS * (1.2 if dist < 350 else 0.7)))
    if TOWERS[k][8]:
        # a sheared top: keep only the leaves that still have wall behind them (a short ray cast into the wall)
        mw = ob.matrix_world; R = mw.to_3x3(); ok = np.zeros(n, bool)
        for i in range(n):
            wp = mw @ Vector(P[i]); wn_ = R @ Vector(N[i])
            hit, loc, nor, idx, hob, _ = sc.ray_cast(dg, wp + wn_ * 0.5, -wn_, distance=1.5)
            ok[i] = hit and hob is not None and hob.name == ob.name
        P, N = P[ok], N[ok]
    build_leaves(f'ivy{k}', P, N, size, ob.matrix_world)

# ------------------------------------------------------------------ trees and shrubs: scanned models on the broken tops, ledges and in the meadow
TREES = ph_objects('tree_small_02', ['tree_small_02_LOD1'], '1k') + ph_objects('island_tree_01', ['island_tree_01_LOD1'], '1k') \
    + ph_objects('island_tree_02', ['island_tree_02_LOD1'], '1k')
tlib = library('tree_lib', TREES)
SHRUBS = ph_objects('shrub_02', [f'shrub_02_{c}_LOD1' for c in 'abcd'], '1k')
slib = library('shrub_lib', SHRUBS)
ROCKS = ph_objects('rock_moss_set_01', [f'rock_moss_set_01_rock0{i}' for i in range(1, 7)], '1k')
rlib = library('rock_lib', ROCKS)
dg = bpy.context.evaluated_depsgraph_get()
def surface_points(ob, n, top_only=True):
    # cast rays straight down onto the evaluated tower (its sheared or flat top) to plant trees
    mw = ob.matrix_world; pts = []
    tw, td = ob.dimensions.x, ob.dimensions.y
    for _ in range(n * 4):
        lp_ = Vector((rng.uniform(-0.45, 0.45) * tw, rng.uniform(-0.45, 0.45) * td, 0))
        wp = mw @ lp_; o_ = Vector((wp.x, wp.y, 400))
        hit, loc, nor, idx, hob, _ = sc.ray_cast(dg, o_, Vector((0, 0, -1)))
        if hit and hob is not None and hob.name == ob.name and nor.z > 0.5: pts.append(loc)
        if len(pts) >= n: break
    return pts
tp, tsc, tpk = [], [], []
for ob, tw, td, th in towers:
    for p_ in surface_points(ob, int(rng.integers(3, 7))):
        tp.append(p_); tsc.append(rng.uniform(1.6, 2.8)); tpk.append(rng.integers(0, len(TREES)))
# a few trees and stands in the meadow, at the feet of the towers and by the ruins
for _ in range(arg('meadow-trees', 26)):
    r_ = rng.uniform(55, 420); th_ = rng.uniform(-HALF, HALF)
    x_, y_ = r_ * math.sin(th_), r_ * math.cos(th_)
    if abs(x_ - 0) < 12 and y_ < 120: continue           # keep the gap behind the stone open
    tp.append(Vector((x_, y_, -0.2))); tsc.append(rng.uniform(1.4, 2.6)); tpk.append(rng.integers(0, len(TREES)))
tp = np.array([tuple(v) for v in tp]); n_ = len(tp)
trot = np.zeros((n_, 3)); trot[:, 2] = rng.uniform(0, 6.283, n_); trot[:, 0] = rng.normal(0, 0.05, n_)
tsc = np.array(tsc); instancer('trees', tlib, tp, trot, np.stack([tsc, tsc, tsc * rng.uniform(0.9, 1.15, n_)], 1), np.array(tpk))

# shrubs on ledges and tops, and as hanging masses at the foot of the walls
sp_, ss_ = [], []
for ob, tw, td, th in towers:
    for p_ in surface_points(ob, 18): sp_.append(tuple(p_)); ss_.append(rng.uniform(1.5, 3.0))
    mw = ob.matrix_world
    for _ in range(40):
        f_ = rng.integers(0, 4); u_ = rng.uniform(-0.5, 0.5)
        lp_ = [(u_ * tw, -td / 2 - 0.4), (u_ * tw, td / 2 + 0.4), (tw / 2 + 0.4, u_ * td), (-tw / 2 - 0.4, u_ * td)][f_]
        wp = mw @ Vector((lp_[0], lp_[1], -6)); sp_.append((wp.x, wp.y, -0.3)); ss_.append(rng.uniform(2.0, 4.0))
for _ in range(220):
    r_ = rng.uniform(25, 300); th_ = rng.uniform(-HALF, HALF)
    sp_.append((r_ * math.sin(th_), r_ * math.cos(th_), -0.2)); ss_.append(rng.uniform(1.0, 2.2))
sp_ = np.array(sp_); n_ = len(sp_); ss_ = np.array(ss_)
srot = np.zeros((n_, 3)); srot[:, 2] = rng.uniform(0, 6.283, n_)
instancer('shrubs', slib, sp_, srot, np.stack([ss_] * 3, 1), rng.integers(0, len(SHRUBS), n_))

# rubble in the grass: scanned mossy rocks standing in for fallen concrete, half buried
rp = []
for _ in range(arg('rocks', 40)):
    r_ = rng.uniform(6, 140); th_ = rng.uniform(-HALF, HALF)
    x_, y_ = r_ * math.sin(th_), r_ * math.cos(th_)
    if math.hypot(x_ - MX, y_ - MY) < 3.0: continue
    rp.append((x_, y_, -0.25))
rp = np.array(rp); n_ = len(rp); rs = rng.uniform(0.15, 0.55, n_) * (1 + np.linalg.norm(rp[:, :2], axis=1) / 60)
rrot = np.zeros((n_, 3)); rrot[:, 2] = rng.uniform(0, 6.283, n_)
instancer('rocks', rlib, rp, rrot, np.stack([rs, rs, rs * 0.7], 1), rng.integers(0, len(ROCKS), n_))

# ------------------------------------------------------------------ the meadow: scanned grass and wildflowers, dense, varied
GR = ph_objects('grass_medium_01', [n for n in (f'grass_medium_01_{s}_LOD1' for s in ('large_a', 'large_b', 'large_c', 'mid_a', 'mid_b', 'mid_c', 'tall_a', 'tall_b', 'tall_c', 'tall_d'))])
if not GR:
    with bpy.data.libraries.load(os.path.join(PH, 'grass_medium_01', 'grass_medium_01_2k.blend'), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.endswith('_LOD1')]
    GR = [o_ for o_ in dst.objects if o_]
    for o_ in GR: o_.location = (0, 0, 0); o_.rotation_euler = (0, 0, 0); o_.parent = None
GR += ph_objects('grass_medium_02', [f'grass_medium_02_{c}' for c in 'bcde'])
glib = library('grass_lib', GR)
YEL = ph_objects('celandine_01', [f'celandine_01_{c}_LOD1' for c in 'abcde']) + ph_objects('flower_empodium', [f'flower_empodium_{c}_LOD1' for c in 'abcde'])
BLU = ph_objects('flower_heliophila', ['flower_heliophila_small_LOD3'])
WHT = ph_objects('dandelion_01', ['dandelion_01_a_LOD2', 'dandelion_01_b_LOD2'])
flib = library('flower_lib', YEL + BLU + WHT)
NY, NB, NW = len(YEL), len(BLU), len(WHT)
print('libs grass', len(GR), 'flowers', NY, NB, NW, 'trees', len(TREES))

def field(n, rmin, rmax, keep):
    th = rng.uniform(-HALF, HALF, n); r = np.sqrt(rng.uniform(rmin ** 2, rmax ** 2, n))
    x = r * np.sin(th); y = r * np.cos(th)
    k = rng.uniform(0, 1, n) < keep(r, x, y); x, y, r = x[k], y[k], r[k]
    c, s_ = math.cos(-MYAW), math.sin(-MYAW)
    lx = (x - MX) * c - (y - MY) * s_; ly = (x - MX) * s_ + (y - MY) * c
    ok = ~((np.abs(lx) < 1.06) & (np.abs(ly) < T / 2 + 0.06))         # nothing grows on the mark
    return x[ok], y[ok], r[ok]
def plant(name, coll, x, y, r, scl, pick):
    m = len(x); P = np.stack([x, y, np.full(m, -0.02)], 1)
    rot = np.zeros((m, 3)); rot[:, 2] = rng.uniform(0, 6.283, m); rot[:, 0] = rng.normal(0, 0.06, m); rot[:, 1] = rng.normal(0, 0.06, m)
    return instancer(name, coll, P, rot, np.stack([scl, scl, scl * rng.uniform(0.85, 1.25, m)], 1), pick)
# patches: the old street grid still shows as lower, flowerier strips through the tall grass
def patches(x, y): return fbm(x, y, 0.06, 0.4)
x, y, r = field(int(2600000 * DENS), 1.2, 260, lambda r, x, y: np.clip((10 / r) ** 1.15, 0.02, 1.0))
dm = np.hypot(x - MX, y - MY)
gs = rng.uniform(1.15, 1.85, len(x)) * (1 + r / 70) * (0.55 + 0.45 * smooth(1.2, 4.0, dm)) * (0.75 + 0.5 * patches(x, y))
plant('grass', glib, x, y, r, gs, rng.integers(0, len(GR), len(x)))
x, y, r = field(int(900000 * DENS), 1.2, 220, lambda r, x, y: np.clip((9 / r) ** 1.1, 0.02, 1.0) * (0.35 + 0.65 * patches(x, y)))
u = rng.uniform(0, 1, len(x))
pick = np.where(u < 0.3, NY + NB + rng.integers(0, NW, len(x)), np.where(u < 0.45, NY + rng.integers(0, NB, len(x)), rng.integers(0, NY, len(x))))
fs = rng.uniform(1.0, 1.6, len(x)) * (1 + r / 45)
plant('flowers', flib, x, y, r, fs, pick)

# ------------------------------------------------------------------ haze: an optional thin real volume (--vol 1; off in the draft, too noisy at
# low samples), and aerial perspective by depth in the composite
if arg('vol', 0):
    bpy.ops.mesh.primitive_cube_add(size=1); vb = bpy.context.object; vb.name = 'haze'
    vb.scale = (2400, 2400, 180); vb.location = (0, 1100, 89)
    m_v, nt = mat('haze')
    pv = node(nt, 'ShaderNodeVolumePrincipled'); pv.inputs['Density'].default_value = arg('haze', 0.0011)
    pv.inputs['Color'].default_value = (0.92, 0.95, 1.0, 1); pv.inputs['Anisotropy'].default_value = 0.55
    o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, pv.outputs['Volume'], o.inputs['Volume'])
    vb.data.materials.append(m_v)
    vb.visible_shadow = False

cam_d.dof.use_dof = True
cam_d.dof.focus_distance = math.hypot(MX, MY) - 0.2
cam_d.dof.aperture_fstop = arg('fstop', 4.0); cam_d.dof.aperture_blades = 7

# ------------------------------------------------------------------ compositor: aerial perspective by depth, soft bloom
sc.use_nodes = True
ct = sc.node_tree; ct.nodes.clear()
rl = ct.nodes.new('CompositorNodeRLayers'); comp = ct.nodes.new('CompositorNodeComposite')
fz = ct.nodes.new('CompositorNodeMapRange'); fz.use_clamp = True
fz.inputs['From Min'].default_value = 45; fz.inputs['From Max'].default_value = arg('fog-far', 1400)
fz.inputs['To Min'].default_value = 0; fz.inputs['To Max'].default_value = arg('fog', 0.32)
ct.links.new(rl.outputs['Depth'], fz.inputs['Value'])
skyk = ct.nodes.new('CompositorNodeMath'); skyk.operation = 'LESS_THAN'; skyk.inputs[1].default_value = 4000
ct.links.new(rl.outputs['Depth'], skyk.inputs[0])
fk = ct.nodes.new('CompositorNodeMath'); fk.operation = 'MULTIPLY'
ct.links.new(fz.outputs['Value'], fk.inputs[0]); ct.links.new(skyk.outputs['Value'], fk.inputs[1])
pw = ct.nodes.new('CompositorNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 0.7
ct.links.new(fk.outputs['Value'], pw.inputs[0])
fm = ct.nodes.new('CompositorNodeMixRGB'); fm.blend_type = 'MIX'
hz = arg('haze-level', 1.1)
fm.inputs[2].default_value = (0.86 * hz, 0.89 * hz, 0.93 * hz, 1)
ct.links.new(pw.outputs[0], fm.inputs[0]); ct.links.new(rl.outputs['Image'], fm.inputs[1])
gl = ct.nodes.new('CompositorNodeGlare'); gl.glare_type = 'BLOOM'; gl.quality = 'HIGH'
gl.inputs['Threshold'].default_value = 0.85; gl.inputs['Smoothness'].default_value = 0.7
gl.inputs['Strength'].default_value = arg('bloom', 0.3); gl.inputs['Size'].default_value = 0.9
gl.inputs['Tint'].default_value = (1.0, 0.93, 0.84, 1)
ct.links.new(fm.outputs['Image'], gl.inputs['Image']); ct.links.new(gl.outputs['Image'], comp.inputs['Image'])

if '--dry' in argv:
    print('DRY_OK'); sys.exit(0)
t0 = time.time()
sc.render.filepath = RAW
if '--grade-only' not in argv: bpy.ops.render.render(write_still=True)
print('RENDER_SECONDS', round(time.time() - t0, 1))

# ------------------------------------------------------------------ grade: filmic lift to pale pastel blacks, warm highlights, lens, grain
im = bpy.data.images.load(RAW); im.colorspace_settings.name = 'Non-Color'
a = np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4)[:, :, :3]
lift = np.array([0.075, 0.08, 0.095]) * arg('lift', 0.65)
a = lift + a * (1 - lift)
lum = a @ np.array([0.2126, 0.7152, 0.0722])
a = lum[..., None] + (a - lum[..., None]) * arg('sat', 0.96)
warm = np.array([1.025, 1.0, 0.965]); a = a * (1 + (warm - 1) * smooth(0.45, 1.0, lum)[..., None])
yy, xx = np.mgrid[0:H, 0:W]; cx_, cy_ = (W - 1) / 2, (H - 1) / 2
rr2 = ((xx - cx_) / cx_) ** 2 * 0.8 + ((yy - cy_) / cy_) ** 2 * 0.6
def resample(ch, k):
    sx = cx_ + (xx - cx_) * k; sy = cy_ + (yy - cy_) * k
    x0 = np.clip(sx.astype(int), 0, W - 2); y0 = np.clip(sy.astype(int), 0, H - 2); fx = sx - x0; fy = sy - y0
    return (ch[y0, x0] * (1 - fx) * (1 - fy) + ch[y0, x0 + 1] * fx * (1 - fy) + ch[y0 + 1, x0] * (1 - fx) * fy + ch[y0 + 1, x0 + 1] * fx * fy)
ca = arg('ca', 0.0007)
a[..., 0] = resample(a[..., 0], 1 - ca); a[..., 2] = resample(a[..., 2], 1 + ca)
a *= (1 - 0.14 * np.clip(rr2, 0, 1.4) ** 1.5)[..., None]
g = rng.normal(0, arg('grain', 0.012), (H, W)).astype(np.float32)
a += (g * (0.6 + 0.4 * (1 - lum)))[..., None]
a = np.clip(a, 0, 1)
outim = bpy.data.images.new('graded', W, H, alpha=False, float_buffer=False); outim.colorspace_settings.name = 'Non-Color'
outim.pixels.foreach_set(np.concatenate([a, np.ones((H, W, 1))], 2).astype(np.float32).ravel())
outim.filepath_raw = OUT; outim.file_format = 'PNG'; outim.save()
print('WROTE', OUT)
