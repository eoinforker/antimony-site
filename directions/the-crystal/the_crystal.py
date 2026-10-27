# The Crystal: first-frame draft.
# Golden hour over a vast misty valley of forest and old ruins. On a far promontory stands the
# Antimony stone at the scale of a landmark: a weathered monolith of the exact Break geometry (the
# tile with corners of radius 22 on 100, split by the seam at 16 degrees, the sky crystal set in its
# cavity), 300 m tall. Dense fir forest fills the valley and fades into the mist; a ruined gatehouse
# stands at the stone's foot for scale; a broken cloud deck and a ridge of firs towards the sun cut
# the light into shafts. The low sun stands behind and to the left; shafts of light fall through
# the haze past the stone and the ridges; a few birds cross far off.
#
# Run headless (Blender 4.5 LTS), always under the shared lock:
#   flock <scratch>/blender.lock nice -n 5 blender -b -P the_crystal.py -- --out first-frame-draft.png --w 1600 --h 900 --samples 64 --tl 440
#
# The stone comes from the shared module, directions/stone/stone.py (exact Break geometry, scanned
# basalt, softened and chipped arrises, moss at the foot, sky glass crystal).
#
# World, in metres: Z up, the valley floor near Z = 0, the camera on a grassy ridge to the south
# (negative Y) looking north across the valley to the stone.

import bpy, bmesh, math, random, sys, os, json
from mathutils import Vector
from mathutils.noise import noise as pnoise, fractal

def arg(name, default):
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return a[a.index(name) + 1] if name in a else default

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = arg('--out', os.path.join(HERE, 'first-frame-draft.png'))
W, H = int(arg('--w', '1600')), int(arg('--h', '900'))
SAMPLES = int(arg('--samples', '64')); TL = float(arg('--tl', '440'))
SCR = '/tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad'
PH, ACG = SCR + '/assets/polyhaven', SCR + '/assets/ambientcg'
rng = random.Random(4)

bpy.ops.wm.read_factory_settings(use_empty=True)
SC = bpy.context.scene
SC.render.engine = 'CYCLES'

def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple([x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0])
SKY = lin('#94E6FF')

def link_obj(name, data):
    ob = bpy.data.objects.new(name, data); SC.collection.objects.link(ob); return ob

def mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links

def scan(N, L, name, metres, vec, colour_only=False):
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / metres,) * 3
    L.new(vec, mp.inputs[0]); out = []
    for suf, nc in [('Color', False), ('Roughness', True), ('NormalGL', True)]:
        t = N.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(f'{ACG}/{name}/{name}_2K-JPG_{suf}.jpg')
        if nc: t.image.colorspace_settings.name = 'Non-Color'
        t.projection = 'BOX'; t.projection_blend = 0.3; L.new(mp.outputs[0], t.inputs[0]); out.append(t)
    return out

# ---------------------------------------------------------------- terrain
# A grassy ridge under the camera, the long valley of forest and ruins, and the far upland with
# the stone on its promontory, then hills fading into the haze.
CAM_Y = -1458.0
STONE_POS = Vector((260.0, 120.0, 0.0))
def terrain_h(x, y):
    n = fractal(Vector((x / 900, y / 900, 0.4)), 0.6, 2.0, 5) * 55
    if y < -1450:                                   # the near ridge
        t = min(1.0, (-1450 - y) / 50); base = 150 * (t * t * (3 - 2 * t))
    elif y < 0:                                     # the valley
        t = (y + 1450) / 1450; base = 18 * math.sin(t * math.pi) * 0.3
    else:                                           # the upland, rising to far hills
        t = min(1.0, y / 260); base = 120 * (t * t * (3 - 2 * t)) + max(0.0, y - 900) * 0.07
    # the promontory under the stone
    d = math.hypot(x - STONE_POS.x, (y - STONE_POS.y) * 1.3)
    base += 140 * math.exp(-(d / 300) ** 2)
    return base + n * (0.5 if y < -1450 else 1.0)

NG, X0, X1, Y0, Y1 = 300, -3400.0, 3400.0, -1900.0, 3800.0
bm = bmesh.new(); vs = []
for j in range(NG + 1):
    row = []
    for i in range(NG + 1):
        x = X0 + (X1 - X0) * i / NG; y = Y0 + (Y1 - Y0) * (j / NG) ** 1.6   # denser rows near the camera
        row.append(bm.verts.new((x, y, terrain_h(x, y))))
    vs.append(row)
for j in range(NG):
    for i in range(NG):
        bm.faces.new([vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]])
me = bpy.data.meshes.new('terrain'); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
terrain = link_obj('terrain', me)
m, N, L = mat('ground')
tc = N.new('ShaderNodeTexCoord')
g = scan(N, L, 'Grass004', 4.0, tc.outputs['Object']); r = scan(N, L, 'Rock030', 8.0, tc.outputs['Object'])
geo = N.new('ShaderNodeNewGeometry'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'], sep.inputs[0])
fac = N.new('ShaderNodeMapRange'); fac.inputs['From Min'].default_value = 0.72; fac.inputs['From Max'].default_value = 0.9
L.new(sep.outputs['Z'], fac.inputs['Value'])
def mixc(a, b):
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; L.new(fac.outputs[0], mx.inputs['Factor'])
    L.new(a, mx.inputs['A']); L.new(b, mx.inputs['B']); return mx.outputs['Result']
L.new(mixc(r[0].outputs[0], g[0].outputs[0]), N['Principled BSDF'].inputs['Base Color'])
N['Principled BSDF'].inputs['Roughness'].default_value = 0.85
nm = N.new('ShaderNodeNormalMap'); L.new(mixc(r[2].outputs[0], g[2].outputs[0]), nm.inputs['Color']); L.new(nm.outputs[0], N['Principled BSDF'].inputs['Normal'])
terrain.data.materials.append(m)

# ---------------------------------------------------------------- the stone (the shared module)
sys.path.insert(0, '/home/user/antimony-site/directions/stone')
import stone as stonemod
STONE_SIZE = 300.0                                   # the tile is 300 m square: a landmark
ground_z = terrain_h(STONE_POS.x, STONE_POS.y)
parts = stonemod.build_stone(SC.collection, scale_m=STONE_SIZE, location=(STONE_POS.x, STONE_POS.y, ground_z),
                             rotation=(math.radians(1.2), 0, math.radians(-9)), wetness=0.0, moss=0.85,
                             cache_dir=SCR + '/assets', glow=0.5, caustics=False, detail=320, seed=11)
mon = parts['root']; crystal = parts['crystal']; crystal.pass_index = 1
CY = 51.5; S = STONE_SIZE / 100.0
# ---------------------------------------------------------------- forest (Poly Haven scans, scattered densely)
def load_obj(blend, name):
    with bpy.data.libraries.load(blend, link=False) as (src, dst): dst.objects = [name]
    return dst.objects[0]
FIRS = [load_obj(f'{PH}/fir_tree_01_lod2/fir_tree_01_lod2.blend', 'fir_tree_01_%s_LOD2' % k) for k in 'abc']
BROAD = [load_obj(f'{PH}/island_tree_01/island_tree_01_1k.blend', 'island_tree_01_LOD1')]
# the fir scan's trunk textures are left out to save disk: trunks take a plain bark of its own colour map
bark, N, L = mat('fir_bark_plain')
bt = N.new('ShaderNodeTexImage'); bt.image = bpy.data.images.load(f'{PH}/fir_tree_01_lod2/textures/fir_tree_01_bark_diff_1k.png')
L.new(bt.outputs[0], N['Principled BSDF'].inputs['Base Color']); N['Principled BSDF'].inputs['Roughness'].default_value = 0.9
for f in FIRS:
    for i, sl in enumerate(f.data.materials):
        if sl and 'twig' not in sl.name: f.data.materials[i] = bark
placed = 0; tries = 0
while placed < 9000 and tries < 90000:
    tries += 1
    x = rng.uniform(-1500, 1900); y = rng.uniform(-1250, 1400)
    if y < -1250: continue
    dd = math.hypot(x - STONE_POS.x, (y - STONE_POS.y) * 1.3)
    if dd < 230: continue                                                         # the stone's open crown
    if (x + 380) ** 2 / 260 ** 2 + (y + 700) ** 2 / 160 ** 2 < 1: continue        # clearings for the ruins
    if (x - 620) ** 2 / 200 ** 2 + (y + 420) ** 2 / 140 ** 2 < 1: continue
    if (x - 90) ** 2 / 120 ** 2 + (y - 40) ** 2 / 90 ** 2 < 1: continue
    if fractal(Vector((x / 500, y / 500, 2.3)), 0.6, 2.0, 3) < -0.25: continue      # a few glades
    z = terrain_h(x, y)
    ob = link_obj('fir', rng.choice(FIRS).data)
    sc = rng.uniform(1.4, 2.2)
    ob.location = (x, y, z - 0.5); ob.rotation_euler = (0, 0, rng.uniform(0, 6.28)); ob.scale = (sc, sc, sc * rng.uniform(0.9, 1.15))
    placed += 1
# a ridge of tall firs on the promontory's shoulder, between the low sun and the valley haze: the
# sun breaks through their crowns, and the gaps throw shafts down through the air
for k in range(140):
    t = k / 139.0
    x = STONE_POS.x - 520 + 380 * t + rng.uniform(-25, 25); y = STONE_POS.y + 260 + 120 * t + rng.uniform(-30, 30)
    if rng.random() < 0.25: continue
    ob = link_obj('ridge_fir', rng.choice(FIRS).data); sc = rng.uniform(2.0, 2.8)
    ob.location = (x, y, terrain_h(x, y) - 0.5); ob.rotation_euler = (0, 0, rng.uniform(0, 6.28)); ob.scale = (sc, sc, sc * 1.1)
TREES = BROAD
# grass on the near ridge, under the camera
GRASS = [load_obj(f'{PH}/grass_medium_02/grass_medium_02_2k.blend', 'grass_medium_02_%s' % k) for k in 'cde']
ROCKS = [load_obj(f'{PH}/rock_moss_set_01/rock_moss_set_01_1k.blend', 'rock_moss_set_01_rock0%d' % i) for i in (1, 2, 4, 5)]
for k in range(900):
    x = rng.uniform(-9, 11); y = rng.uniform(CAM_Y + 2.5, CAM_Y + 8.5)
    ob = link_obj('grass', rng.choice(GRASS).data); gs = rng.uniform(3.2, 5.0)
    ob.location = (x, y, terrain_h(x, y) - 0.1); ob.rotation_euler = (0, 0, rng.uniform(0, 6.28)); ob.scale = (gs, gs, gs * 1.5)
for (x, y, sc) in [(-5.5, CAM_Y + 7.5, 1.6), (7.0, CAM_Y + 8.0, 2.0)]:
    ob = link_obj('rock', rng.choice(ROCKS).data)
    ob.location = (x, y, terrain_h(x, y) - 0.4 * sc); ob.rotation_euler = (0, 0, rng.uniform(0, 6.28)); ob.scale = (sc, sc, sc)

# ---------------------------------------------------------------- ruins (few, distant, scanned stone, in haze)
ruin_m, N, L = mat('ruin_stone')
tc = N.new('ShaderNodeTexCoord'); rs = scan(N, L, 'Rock041', 6.0, tc.outputs['Object'])
L.new(rs[0].outputs[0], N['Principled BSDF'].inputs['Base Color']); L.new(rs[1].outputs[0], N['Principled BSDF'].inputs['Roughness'])
def block(loc, size, rot=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=(0, 0, rot))
    ob = bpy.context.active_object; ob.scale = size
    b = ob.modifiers.new('b', 'BEVEL'); b.width = 0.4; b.segments = 2
    ob.data.materials.append(ruin_m); return ob
def arcade(cx, cy, n, rot, h, span):
    """A broken arcade: piers of different heights, a few lintels left standing."""
    c, s = math.cos(rot), math.sin(rot)
    for i in range(n):
        u = (i - n / 2) * span; hh = h * rng.uniform(0.35, 1.0) if rng.random() < 0.7 else h
        x, y = cx + c * u, cy + s * u; z = terrain_h(x, y)
        block((x, y, z + hh / 2 - 2), (5, 5, hh + 4), rot)
        if i < n - 1 and hh > h * 0.9 and rng.random() < 0.6:
            block((x + c * span / 2, y + s * span / 2, z + h + 1.5), (span + 5, 5, 4), rot)
arcade(-380, -700, 9, 0.25, 38, 16)
arcade(-300, -760, 5, 1.6, 30, 16)
arcade(620, -420, 7, -0.35, 44, 18)
# a ruined gatehouse and wall at the stone's foot, so its size reads
arcade(STONE_POS.x - 240, STONE_POS.y - 120, 8, 0.2, 46, 18)
block((STONE_POS.x - 330, STONE_POS.y - 140, terrain_h(STONE_POS.x - 330, STONE_POS.y - 140) + 34), (16, 16, 76), 0.2)
for (x, y, hh, w) in [(-120, -980, 70, 12), (900, -150, 90, 16), (-900, 300, 110, 18)]:   # broken towers
    block((x, y, terrain_h(x, y) + hh / 2 - 3), (w, w, hh), rng.uniform(0, 1))

# ---------------------------------------------------------------- birds, far off
bird_m, N, L = mat('bird'); N['Principled BSDF'].inputs['Base Color'].default_value = (0.02, 0.02, 0.025, 1)
def bird(loc, sc, rot, flap):
    bm = bmesh.new()
    a, b, c = bm.verts.new((0, 0, 0)), bm.verts.new((-1, -0.25, flap)), bm.verts.new((1, -0.25, flap))
    d = bm.verts.new((0, -0.45, 0.02))
    bm.faces.new([a, b, d]); bm.faces.new([a, d, c])
    me = bpy.data.meshes.new('bird'); bm.to_mesh(me); bm.free()
    ob = link_obj('bird', me); ob.location = loc; ob.scale = (sc, sc, sc); ob.rotation_euler = (0, 0, rot)
    me.materials.append(bird_m)
to_st = (Vector((STONE_POS.x, STONE_POS.y, 0)) - Vector((0, CAM_Y, 0))); to_st.z = 0; to_st.normalize()
for k in range(9):
    d0 = 520 + rng.uniform(-30, 30)
    base_p = Vector((0, CAM_Y, 0)) + to_st * d0
    bird((base_p.x - 70 + k * 9 + rng.uniform(-4, 4), base_p.y + k * 3, 230 + rng.uniform(-6, 6) - abs(k - 4) * 4), 1.4, 0.4, rng.uniform(-0.35, 0.55))

# ---------------------------------------------------------------- air: valley mist and golden haze
def fog():
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1000, 700))
    ob = bpy.context.active_object; ob.name = 'fog'; ob.scale = (9000, 7000, 1500)
    m, N, L = mat('fog'); N.remove(N['Principled BSDF'])
    v = N.new('ShaderNodeVolumePrincipled'); v.inputs['Color'].default_value = (1.0, 0.90, 0.76, 1); v.inputs['Anisotropy'].default_value = 0.7
    geo = N.new('ShaderNodeNewGeometry'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Position'], sep.inputs[0])
    hz = N.new('ShaderNodeMath'); hz.operation = 'MULTIPLY'; hz.inputs[1].default_value = -1 / 26.0; L.new(sep.outputs['Z'], hz.inputs[0])
    ex = N.new('ShaderNodeMath'); ex.operation = 'EXPONENT'; L.new(hz.outputs[0], ex.inputs[0])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1 / 260.0; nz.inputs['Detail'].default_value = 3
    L.new(geo.outputs['Position'], nz.inputs['Vector'])
    rm = N.new('ShaderNodeMapRange'); rm.inputs['From Min'].default_value = 0.35; rm.inputs['From Max'].default_value = 0.65
    rm.inputs['To Min'].default_value = 0.2; rm.inputs['To Max'].default_value = 1.7; L.new(nz.outputs['Fac'], rm.inputs['Value'])
    m1 = N.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; L.new(ex.outputs[0], m1.inputs[0]); L.new(rm.outputs[0], m1.inputs[1])
    # high haze for aerial depth, thinning upward
    hz2 = N.new('ShaderNodeMath'); hz2.operation = 'MULTIPLY'; hz2.inputs[1].default_value = -1 / 650.0; L.new(sep.outputs['Z'], hz2.inputs[0])
    ex2 = N.new('ShaderNodeMath'); ex2.operation = 'EXPONENT'; L.new(hz2.outputs[0], ex2.inputs[0])
    a1 = N.new('ShaderNodeMath'); a1.operation = 'MULTIPLY'; a1.inputs[1].default_value = 0.0030; L.new(m1.outputs[0], a1.inputs[0])
    a2 = N.new('ShaderNodeMath'); a2.operation = 'MULTIPLY_ADD'; L.new(ex2.outputs[0], a2.inputs[0]); a2.inputs[1].default_value = 0.00013
    L.new(a1.outputs[0], a2.inputs[2]); L.new(a2.outputs[0], v.inputs['Density'])
    L.new(v.outputs[0], N['Material Output'].inputs['Volume']); ob.data.materials.append(m); return ob
FOG = fog()
cl, N, L = mat('cloud_deck'); N.remove(N['Principled BSDF'])
tr = N.new('ShaderNodeBsdfTransparent'); dfs = N.new('ShaderNodeBsdfDiffuse')
cn = N.new('ShaderNodeTexNoise'); cn.inputs['Scale'].default_value = 5.0; cn.inputs['Detail'].default_value = 5; cn.inputs['Roughness'].default_value = 0.6
cr = N.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = 0.46; cr.color_ramp.elements[1].position = 0.52
L.new(cn.outputs['Fac'], cr.inputs[0]); mxs = N.new('ShaderNodeMixShader'); L.new(cr.outputs[0], mxs.inputs[0])
L.new(dfs.outputs[0], mxs.inputs[1]); L.new(tr.outputs[0], mxs.inputs[2]); L.new(mxs.outputs[0], N['Material Output'].inputs['Surface'])
bpy.ops.mesh.primitive_plane_add(size=1, location=(STONE_POS.x - 1100, STONE_POS.y + 1750, 720))
deck = bpy.context.active_object; deck.name = 'cloud_deck'; deck.scale = (4200, 4200, 1)
deck.data.materials.append(cl); deck.visible_camera = False; deck.visible_glossy = False; deck.visible_diffuse = False
if arg('--nofog', '0') == '1': FOG.hide_render = True

# ---------------------------------------------------------------- golden hour light
sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 9.0; sun.angle = math.radians(0.8); sun.color = (1.0, 0.62, 0.32)
so = link_obj('sun', sun); so.visible_glossy = False
el, az = math.radians(11.0), math.radians(-32.0)                 # low, behind the stone and to the left
to_sun = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
so.rotation_euler = to_sun.to_track_quat('Z', 'Y').to_euler()
pl = bpy.data.lights.new('crystal_glow', 'POINT'); pl.energy = 8.0e4; pl.color = (0.3, 0.75, 1.0); pl.shadow_soft_size = 8
plo = link_obj('crystal_glow', pl); plo.parent = mon; plo.location = (0, -0.16 * STONE_SIZE, (100 - CY) * S)
plo.visible_glossy = False; plo.visible_camera = False
rc = bpy.data.collections.new('glow_excludes'); rc.objects.link(FOG)
plo.light_linking.receiver_collection = rc
for it in rc.collection_objects: it.light_linking.link_state = 'EXCLUDE'

world = bpy.data.worlds.new('w'); SC.world = world; world.use_nodes = True
WN, WL = world.node_tree.nodes, world.node_tree.links
wtc = WN.new('ShaderNodeTexCoord')
env = WN.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(f'{PH}/kloppenheim_06_puresky/kloppenheim_06_puresky_2k.hdr')
wm = WN.new('ShaderNodeMapping'); wm.inputs['Rotation'].default_value = (0, 0, math.radians(150))
WL.new(wtc.outputs['Generated'], wm.inputs[0]); WL.new(wm.outputs[0], env.inputs[0])
sat = WN.new('ShaderNodeHueSaturation'); sat.inputs['Saturation'].default_value = 0.5; WL.new(env.outputs[0], sat.inputs['Color'])
sepw = WN.new('ShaderNodeSeparateXYZ'); WL.new(wtc.outputs['Generated'], sepw.inputs[0])
gr = WN.new('ShaderNodeValToRGB')
gr.color_ramp.elements[0].position = 0.0; gr.color_ramp.elements[0].color = (1.0, 0.60, 0.26, 1)
gr.color_ramp.elements[1].position = 0.5; gr.color_ramp.elements[1].color = (0.30, 0.42, 0.66, 1)
WL.new(sepw.outputs['Z'], gr.inputs[0])
mixh = WN.new('ShaderNodeMix'); mixh.data_type = 'RGBA'; mixh.blend_type = 'MULTIPLY'; mixh.clamp_result = True
mixh.inputs['Factor'].default_value = 0.5; WL.new(gr.outputs[0], mixh.inputs['A']); WL.new(sat.outputs[0], mixh.inputs['B'])
dot = WN.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'; dot.inputs[1].default_value = to_sun
WL.new(wtc.outputs['Generated'], dot.inputs[0])
cl = WN.new('ShaderNodeMath'); cl.operation = 'MAXIMUM'; cl.inputs[1].default_value = 0; WL.new(dot.outputs['Value'], cl.inputs[0])
pw = WN.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 14; WL.new(cl.outputs[0], pw.inputs[0])
glow = WN.new('ShaderNodeMix'); glow.data_type = 'RGBA'; glow.blend_type = 'ADD'
WL.new(pw.outputs[0], glow.inputs['Factor']); WL.new(mixh.outputs['Result'], glow.inputs['A']); glow.inputs['B'].default_value = (3.0, 1.9, 0.9, 1)
WL.new(glow.outputs['Result'], WN['Background'].inputs['Color']); WN['Background'].inputs['Strength'].default_value = 0.40

# ---------------------------------------------------------------- camera
cam = bpy.data.cameras.new('cam'); cam.lens = 35; cam.sensor_width = 36; cam.clip_start = 0.5; cam.clip_end = 20000
co = link_obj('cam', cam); SC.camera = co
cz = terrain_h(0, CAM_Y) + 3.0                    # standing at the lip of the ridge
co.location = (0, CAM_Y, cz)
dist = (STONE_POS - Vector((0, CAM_Y, 0))).length
tgt = Vector((STONE_POS.x * 0.62, STONE_POS.y, cz + dist * math.tan(math.radians(3.5))))
co.rotation_euler = (tgt - co.location).to_track_quat('-Z', 'Y').to_euler()
cam.dof.use_dof = True; cam.dof.focus_distance = dist; cam.dof.aperture_fstop = 11

# ---------------------------------------------------------------- composite: crystal held to sky blue, bloom
SC.view_layers[0].use_pass_object_index = True
SC.use_nodes = True
T = SC.node_tree; CN, CL = T.nodes, T.links
for n in list(CN): CN.remove(n)
rl = CN.new('CompositorNodeRLayers'); out = CN.new('CompositorNodeComposite')
idm = CN.new('CompositorNodeIDMask'); idm.index = 1; idm.use_antialiasing = True; CL.new(rl.outputs['IndexOB'], idm.inputs[0])
tint = CN.new('CompositorNodeMixRGB'); tint.blend_type = 'MULTIPLY'; tint.inputs[0].default_value = 1.0
tint.inputs[2].default_value = (0.296 * 0.7, 0.791 * 0.7, 1.0 * 0.7, 1); CL.new(rl.outputs['Image'], tint.inputs[1])
fm = CN.new('CompositorNodeMath'); fm.operation = 'MULTIPLY'; fm.inputs[1].default_value = 0.8; CL.new(idm.outputs[0], fm.inputs[0])
held = CN.new('CompositorNodeMixRGB'); CL.new(fm.outputs[0], held.inputs[0]); CL.new(rl.outputs['Image'], held.inputs[1]); CL.new(tint.outputs[0], held.inputs[2])
gl = CN.new('CompositorNodeGlare'); gl.glare_type = 'FOG_GLOW'; gl.quality = 'MEDIUM'
try: gl.inputs['Threshold'].default_value = 0.9; gl.inputs['Strength'].default_value = 0.3; gl.inputs['Size'].default_value = 0.7
except Exception: pass
CL.new(held.outputs[0], gl.inputs[0]); CL.new(gl.outputs[0], out.inputs[0])

# ---------------------------------------------------------------- render
c = SC.cycles
c.device = 'CPU'; c.samples = SAMPLES; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.04
c.time_limit = TL; c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'; c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
c.max_bounces = 5; c.diffuse_bounces = 2; c.glossy_bounces = 2; c.transmission_bounces = 6; c.volume_bounces = 1
c.transparent_max_bounces = 10; c.caustics_reflective = False; c.caustics_refractive = False; c.sample_clamp_indirect = 6.0
c.volume_max_steps = 160; c.volume_step_rate = 8.0
SC.render.threads_mode = 'FIXED'; SC.render.threads = 4
SC.render.resolution_x, SC.render.resolution_y = W, H; SC.render.resolution_percentage = 100
SC.render.image_settings.file_format = 'PNG'
vs = SC.view_settings; vs.view_transform = 'AgX'; vs.look = 'AgX - Medium High Contrast'; vs.exposure = -0.35
SC.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('wrote', OUT)
