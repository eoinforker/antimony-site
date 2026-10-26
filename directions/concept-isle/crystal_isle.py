# Crystal Isle: first-frame draft.
# Dawn over still water in pink and violet mist; a quiet terraced island with a few
# warm-windowed stone houses and trees in silhouette; at its heart the Antimony crystal
# (the Break mark's gem, exact facet geometry, scaled to architecture) in clear glass tinted
# #94E6FF with light inside, reflected in the water; shafts of light through the mist.
#
# Run headless (Blender 4.5 LTS), always under the shared lock:
#   flock <scratch>/blender.lock nice -n 5 blender -b -P crystal_isle.py -- \
#       --out first-frame-draft.png --w 1600 --h 900 --samples 48 --tl 460
# Options: --w, --h, --samples, --tl (time limit in seconds), --hdri (Poly Haven sky).
#
# World, in metres: Z up, the water is Z = 0, the island centre is the origin, the camera
# stands out on the water to the south (negative Y) looking north into the dawn.

import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix
from mathutils.noise import noise as pnoise

def arg(name, default):
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return a[a.index(name) + 1] if name in a else default

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = arg('--out', os.path.join(HERE, 'first-frame-draft.png'))
W, H = int(arg('--w', '1600')), int(arg('--h', '900'))
SAMPLES = int(arg('--samples', '48'))
TL = float(arg('--tl', '460'))
HDRI = arg('--hdri', '/tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad/assets/polyhaven/kloppenheim_06_puresky/kloppenheim_06_puresky_2k.hdr')
rng = random.Random(11)

bpy.ops.wm.read_factory_settings(use_empty=True)
SC = bpy.context.scene

def hexcol(h, a=1.0):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*lin, a)

SKY = hexcol('#94E6FF')

def link_obj(name, me):
    ob = bpy.data.objects.new(name, me); SC.collection.objects.link(ob); return ob

def mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links

# ---------------------------------------------------------------- the crystal
# The gem hexagon from break-geometry.json (SVG units, y down, 100 to the tile). The seam
# runs from the top vertex to the bottom vertex at 16 degrees; it is the ridge of the two
# front facets (and of the two back facets), so the silhouette from the front is the exact
# mark gem and the facet split is the mark's facet.
GEM = [(58.6, 21.5), (70.58, 46.7), (67.82, 56.3), (41.4, 81.5), (29.42, 56.3), (32.18, 46.7)]
TOP, BOT = Vector(GEM[0]), Vector(GEM[3])
CX, CY = 50.0, 51.5
SCALE = 1.6                  # metres per mark unit: the gem stands about 96 m tall

def ridge_dist(p):
    a, b = TOP, BOT; d = (b - a).normalized(); v = Vector(p) - a
    return abs(d.x * v.y - d.y * v.x)

def gem_mesh(name, scale, slope, rim):
    """Bi-facet slab: depth falls off linearly from the ridge, so each facet is planar."""
    bm = bmesh.new()
    front, back = [], []
    for (x, y) in GEM:
        dz = max(rim, 0.0) + slope * (max(ridge_dist(p) for p in GEM) - ridge_dist((x, y)))
        X, Z = (x - CX) * scale, (CY - y) * scale
        front.append(bm.verts.new((X, -dz * scale, Z)))
        back.append(bm.verts.new((X, dz * scale, Z)))
    bm.faces.new([front[0], front[1], front[2], front[3]])      # right facet (the mark's facet)
    bm.faces.new([front[0], front[3], front[4], front[5]])      # left facet
    bm.faces.new([back[3], back[2], back[1], back[0]])
    bm.faces.new([back[5], back[4], back[3], back[0]])
    n = len(GEM)
    for i in range(n):
        j = (i + 1) % n
        if front[i] is front[j]: continue
        try: bm.faces.new([front[j], front[i], back[i], back[j]])
        except ValueError: pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return link_obj(name, me)

crystal = gem_mesh('crystal', SCALE, 0.38, 0.6)
crystal.location = (0, 6, 70)
crystal.rotation_euler = (0, 0, math.radians(-14))
bev = crystal.modifiers.new('bev', 'BEVEL'); bev.width = 0.6; bev.segments = 3; crystal.visible_shadow = False
m, N, L = mat('crystal_glass')
bs = N['Principled BSDF']
bs.inputs['Base Color'].default_value = SKY
bs.inputs['Transmission Weight'].default_value = 1.0
bs.inputs['Roughness'].default_value = 0.04
bs.inputs['IOR'].default_value = 1.46
bs.inputs['Emission Color'].default_value = SKY
bs.inputs['Emission Strength'].default_value = 0.06
vol = N.new('ShaderNodeVolumePrincipled')
vol.inputs['Color'].default_value = SKY
vol.inputs['Density'].default_value = 0.012; vol.inputs['Absorption Color'].default_value = SKY
vol.inputs['Emission Color'].default_value = SKY
vol.inputs['Emission Strength'].default_value = 0.05
L.new(vol.outputs[0], N['Material Output'].inputs['Volume'])
crystal.data.materials.append(m)

# light inside: a smaller inner gem of pale blue light, the same shape
core = gem_mesh('core', SCALE * 0.42, 0.30, 0.2)
core.location = (0, 6, 70); core.rotation_euler = crystal.rotation_euler
m, N, L = mat('core_light')
N.remove(N['Principled BSDF'])
em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (0.42, 0.85, 1.0, 1)
em.inputs['Strength'].default_value = 2.5
L.new(em.outputs[0], N['Material Output'].inputs['Surface'])
core.data.materials.append(m)
core.visible_shadow = False; core.visible_diffuse = False; core.visible_volume_scatter = False
pl = bpy.data.lights.new("crystal_glow", "POINT"); pl.energy = 2.5e5; pl.color = SKY[:3]
pl.shadow_soft_size = 14
plo = link_obj("crystal_glow", pl); plo.location = (0, 6, 66); plo.visible_glossy = False; plo.visible_camera = False

# ---------------------------------------------------------------- the island (terraced)
R0 = 115.0; HMAX = 40.0; STEP = 4.2
def island_h(x, y):
    a = math.atan2(y, x)
    r = math.hypot(x * 0.85, y * 1.35)
    r *= 1 + 0.18 * pnoise(Vector((math.cos(a) * 1.4, math.sin(a) * 1.4, 0.3))) \
            + 0.06 * pnoise(Vector((x / 18, y / 18, 1.7)))
    t = max(0.0, 1 - (r / R0) ** 2)
    h = HMAX * t ** 2.3 - 1.0
    if h <= 0: return h - 2.0 * (1 - t)
    # terraces: flat garden steps with steep stone retaining edges
    k = h / STEP; f = k - math.floor(k)
    s = f * f * f * (f * (f * 6 - 15) + 10)
    s = min(1.0, max(0.0, (f - 0.78) / 0.22)); s = s * s * (3 - 2 * s)
    return (math.floor(k) + s) * STEP + 0.3 * pnoise(Vector((x / 9, y / 9, 4.1)))

NG = 260; SPAN = 320.0
bm = bmesh.new()
vs = []
for j in range(NG + 1):
    row = []
    for i in range(NG + 1):
        x = -SPAN / 2 + SPAN * i / NG; y = -SPAN / 2 + SPAN * j / NG
        row.append(bm.verts.new((x, y, island_h(x, y))))
    vs.append(row)
for j in range(NG):
    for i in range(NG):
        bm.faces.new([vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]])
me = bpy.data.meshes.new('island'); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
island = link_obj('island', me)

ASSETS = '/tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad/assets'
ACG = ASSETS + '/ambientcg'
PH = ASSETS + '/polyhaven'

def img(N, path, noncolor=False, proj_vec=None):
    t = N.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path)
    if noncolor: t.image.colorspace_settings.name = 'Non-Color'
    t.projection = 'BOX'; t.projection_blend = 0.3
    return t

def scan_set(N, L, name, metres, vec_src):
    """ambientCG PBR set, box projected in object space at a real-world tile size."""
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / metres,) * 3
    L.new(vec_src, mp.inputs[0])
    col = img(N, f'{ACG}/{name}/{name}_2K-JPG_Color.jpg')
    rough = img(N, f'{ACG}/{name}/{name}_2K-JPG_Roughness.jpg', True)
    nrm = img(N, f'{ACG}/{name}/{name}_2K-JPG_NormalGL.jpg', True)
    for t in (col, rough, nrm): L.new(mp.outputs[0], t.inputs[0])
    return col, rough, nrm

# island ground: scanned grass on the terrace flats, scanned rock on the retaining walls
m, N, L = mat('island_ground')
bs = N['Principled BSDF']
tc = N.new('ShaderNodeTexCoord')
g_col, g_r, g_n = scan_set(N, L, 'Grass004', 3.0, tc.outputs['Object'])
r_col, r_r, r_n = scan_set(N, L, 'Rock030', 4.0, tc.outputs['Object'])
geo = N.new('ShaderNodeNewGeometry')
sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'], sep.inputs[0])
brk = N.new('ShaderNodeTexNoise'); brk.inputs['Scale'].default_value = 0.15; brk.inputs['Detail'].default_value = 4
add = N.new('ShaderNodeMath'); add.operation = 'MULTIPLY_ADD'
L.new(brk.outputs['Fac'], add.inputs[0]); add.inputs[1].default_value = 0.25
L.new(sep.outputs['Z'], add.inputs[2])
fac = N.new('ShaderNodeMapRange'); fac.inputs['From Min'].default_value = 0.78; fac.inputs['From Max'].default_value = 0.92
L.new(add.outputs[0], fac.inputs['Value'])
def mixc(a, b, t='RGBA'):
    mx = N.new('ShaderNodeMix'); mx.data_type = t
    L.new(fac.outputs[0], mx.inputs['Factor']); L.new(a, mx.inputs['A']); L.new(b, mx.inputs['B'])
    return mx.outputs['Result']
L.new(mixc(r_col.outputs[0], g_col.outputs[0]), bs.inputs['Base Color'])
mr = N.new('ShaderNodeMix'); mr.data_type = 'FLOAT'; L.new(fac.outputs[0], mr.inputs['Factor'])
L.new(r_r.outputs[0], mr.inputs['A']); L.new(g_r.outputs[0], mr.inputs['B'])
L.new(mr.outputs['Result'], bs.inputs['Roughness'])
nm = N.new('ShaderNodeNormalMap'); L.new(mixc(r_n.outputs[0], g_n.outputs[0]), nm.inputs['Color'])
L.new(nm.outputs[0], bs.inputs['Normal'])
island.data.materials.append(m)

# ---------------------------------------------------------------- houses (few, distant, in silhouette)
def box(name, loc, size, rot=0.0, mtl=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=(0, 0, rot))
    ob = bpy.context.active_object; ob.name = name; ob.scale = size
    bv = ob.modifiers.new('bev', 'BEVEL'); bv.width = 0.08; bv.segments = 2
    if mtl: ob.data.materials.append(mtl)
    return ob

stone, N, L = mat('house_stone')
tc = N.new('ShaderNodeTexCoord')
s_col, s_r, s_n = scan_set(N, L, 'Rock041', 2.5, tc.outputs['Object'])
L.new(s_col.outputs[0], N['Principled BSDF'].inputs['Base Color'])
L.new(s_r.outputs[0], N['Principled BSDF'].inputs['Roughness'])
roofm, N, L = mat('roof')
N['Principled BSDF'].inputs['Base Color'].default_value = (0.08, 0.08, 0.10, 1)
winm, N, L = mat('window_warm')
N.remove(N['Principled BSDF'])
em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (1.0, 0.66, 0.45, 1)
em.inputs['Strength'].default_value = 60.0
L.new(em.outputs[0], N['Material Output'].inputs['Surface'])

def house(x, y, w, d, h, rot):
    z0 = island_h(x, y)
    hs = box('house', (x, y, z0 + h / 2 - 0.5), (1, 1, 1), rot, stone); hs.scale = (w, d, h + 1)
    r = box('roof', (x, y, z0 + h + 0.2), (1, 1, 1), rot, roofm)
    r.rotation_euler = (math.radians(45), 0, rot); r.scale = (w * 1.08, d * 0.72, d * 0.72)
    c, s = math.cos(rot), math.sin(rot)
    nwin = max(1, int(w // 3.2))
    for k in range(nwin):
        if rng.random() < 0.3: continue
        u = (k + 0.5) / nwin * w - w / 2
        px, py = x + c * u + s * (d / 2 + 0.05), y + s * u - c * (d / 2 + 0.05)
        wn = box('win', (px, py, z0 + h * 0.55), (1, 1, 1), rot, winm); wn.scale = (0.9, 0.05, 1.4)

for (x, y, w, d, h, rot) in [(-46, -36, 9, 6, 6, 0.10), (34, -44, 10, 6, 7, -0.15),
                             (-20, -54, 6, 5, 5, 0.05), (54, -20, 7, 6, 5, 0.25)]:
    house(x, y, w, d, h, rot)

# ---------------------------------------------------------------- scanned trees and shore rock (Poly Haven)
def load_obj(blend, name):
    with bpy.data.libraries.load(blend, link=False) as (src, dst):
        dst.objects = [name]
    ob = dst.objects[0]
    return ob

TREES = [load_obj(f'{PH}/island_tree_01/island_tree_01_1k.blend', 'island_tree_01_LOD1'),
         load_obj(f'{PH}/island_tree_02/island_tree_02_1k.blend', 'island_tree_02_LOD1')]

def tree(x, y, sc):
    z = island_h(x, y)
    if z < 0.8: return
    src = rng.choice(TREES)
    ob = bpy.data.objects.new('tree', src.data); SC.collection.objects.link(ob)
    ob.location = (x, y, z - 0.3); ob.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi))
    ob.scale = (sc * rng.uniform(0.85, 1.15), sc * rng.uniform(0.85, 1.15), sc)

placed = 0
while placed < 140:
    a = rng.uniform(0, 2 * math.pi); r = rng.uniform(18, 108)
    x, y = math.cos(a) * r, math.sin(a) * r * 0.72
    if abs(x) < 20 and abs(y - 6) < 20: continue          # keep the crystal's foot clear
    tree(x, y, rng.uniform(2.0, 3.0)); placed += 1

CLIFF = load_obj(f'{PH}/coastal_cliff_01/coastal_cliff_01_1k.blend', 'coastal_cliff_01_LOD2')
def cliff(x, y, rot, sc, z=-2.5):
    ob = bpy.data.objects.new('cliff', CLIFF.data); SC.collection.objects.link(ob)
    ob.location = (x, y, z); ob.rotation_euler = (0, 0, rot); ob.scale = (sc, sc, sc)
# a ring of scanned sea cliff along the island's waterline
for k in range(10):
    a = 2 * math.pi * k / 10 + 0.2
    rx, ry = 128 * math.cos(a), 84 * math.sin(a)
    cliff(rx, ry, a + math.pi / 2, rng.uniform(0.75, 1.0))
# far shores in the mist, from the same scan
pass


# ---------------------------------------------------------------- water
bpy.ops.mesh.primitive_plane_add(size=30000, location=(0, 0, 0))
water = bpy.context.active_object; water.name = 'water'
m, N, L = mat('water')
bs = N['Principled BSDF']
bs.inputs['Base Color'].default_value = (0.02, 0.02, 0.03, 1)
bs.inputs['Roughness'].default_value = 0.03
bs.inputs['IOR'].default_value = 1.33
wn = N.new('ShaderNodeTexNoise'); wn.inputs['Scale'].default_value = 0.6; wn.inputs['Detail'].default_value = 3
mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.08, 2.2, 1.0)
tc = N.new('ShaderNodeTexCoord'); L.new(tc.outputs['Object'], mp.inputs[0]); L.new(mp.outputs[0], wn.inputs['Vector'])
bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.22
L.new(wn.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs[0], bs.inputs['Normal'])
water.data.materials.append(m)

# ---------------------------------------------------------------- fog
# One wide volume whose density falls with height and is broken by slow noise, so the low
# sun behind the island cuts shafts through it. It runs far past the horizon, so the water
# and the mist fade into each other with no seam.
def fog_near():
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 199))
    ob = bpy.context.active_object; ob.name = 'fog_near'; ob.scale = (16000, 16000, 400)
    m, N, L = mat('fog_near'); N.remove(N['Principled BSDF'])
    v = N.new('ShaderNodeVolumePrincipled')
    v.inputs['Color'].default_value = (1.0, 0.74, 0.88, 1); v.inputs['Anisotropy'].default_value = 0.85
    geo = N.new('ShaderNodeNewGeometry')
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Position'], sep.inputs[0])
    hz = N.new('ShaderNodeMath'); hz.operation = 'MULTIPLY'; hz.inputs[1].default_value = -1 / 45.0
    L.new(sep.outputs['Z'], hz.inputs[0])
    ex = N.new('ShaderNodeMath'); ex.operation = 'EXPONENT'; L.new(hz.outputs[0], ex.inputs[0])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1 / 70.0
    nz.inputs['Detail'].default_value = 3; nz.inputs['Roughness'].default_value = 0.55
    L.new(geo.outputs['Position'], nz.inputs['Vector'])
    rm = N.new('ShaderNodeMapRange'); rm.inputs['From Min'].default_value = 0.3; rm.inputs['From Max'].default_value = 0.7
    rm.inputs['To Min'].default_value = 0.25; rm.inputs['To Max'].default_value = 1.6
    L.new(nz.outputs['Fac'], rm.inputs['Value'])
    m1 = N.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; L.new(ex.outputs[0], m1.inputs[0]); L.new(rm.outputs[0], m1.inputs[1])
    m2 = N.new('ShaderNodeMath'); m2.operation = 'MULTIPLY_ADD'; L.new(m1.outputs[0], m2.inputs[0])
    m2.inputs[1].default_value = 0.0034; m2.inputs[2].default_value = 0.0
    L.new(m2.outputs[0], v.inputs['Density'])
    L.new(v.outputs[0], N['Material Output'].inputs['Volume'])
    ob.data.materials.append(m)
fog_near()

def haze_bank():
    # a hollow ring around the near volume would be exact; a slab under it is close enough:
    # it is thin (0.0011) and only 30 m deep, so it barely touches the near fog's light
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 2000, 14))
    ob = bpy.context.active_object; ob.name = 'haze_bank'; ob.scale = (16000, 16000, 30)
    m, N, L = mat('haze_bank'); N.remove(N['Principled BSDF'])
    v = N.new('ShaderNodeVolumePrincipled')
    v.inputs['Color'].default_value = (1.0, 0.76, 0.90, 1); v.inputs['Density'].default_value = 0.0011
    v.inputs['Anisotropy'].default_value = 0.7
    L.new(v.outputs[0], N['Material Output'].inputs['Volume'])
    ob.data.materials.append(m)


# ---------------------------------------------------------------- sun and sky
sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 22.0; sun.angle = math.radians(1.0)
sun.color = (1.0, 0.70, 0.62)
so = link_obj('sun', sun); so.visible_glossy = False
el, az = math.radians(4.5), math.radians(11.0)        # low, behind the island's right shoulder
to_sun = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
so.rotation_euler = to_sun.to_track_quat('Z', 'Y').to_euler()

# Sky: the Poly Haven HDRI, desaturated and pushed well back under a dawn gradient with a
# broad warm glow around the sun, so the sky is luminous and the clouds only whisper.
world = bpy.data.worlds.new('w'); SC.world = world; world.use_nodes = True
WN, WL = world.node_tree.nodes, world.node_tree.links
bg = WN['Background']
wtc = WN.new('ShaderNodeTexCoord')
env = WN.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(HDRI)
wm = WN.new('ShaderNodeMapping'); wm.inputs['Rotation'].default_value = (0, 0, math.radians(200))
WL.new(wtc.outputs['Generated'], wm.inputs[0]); WL.new(wm.outputs[0], env.inputs[0])
sat = WN.new('ShaderNodeHueSaturation'); sat.inputs['Saturation'].default_value = 0.3
WL.new(env.outputs[0], sat.inputs['Color'])
dot = WN.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
dot.inputs[1].default_value = to_sun; WL.new(wtc.outputs['Generated'], dot.inputs[0])
cl = WN.new('ShaderNodeMath'); cl.operation = 'MAXIMUM'; cl.inputs[1].default_value = 0.0; WL.new(dot.outputs['Value'], cl.inputs[0])
pw = WN.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 9.0; WL.new(cl.outputs[0], pw.inputs[0])
sepw = WN.new('ShaderNodeSeparateXYZ'); WL.new(wtc.outputs['Generated'], sepw.inputs[0])
gr = WN.new('ShaderNodeValToRGB')                         # vertical gradient: bright pink horizon to violet zenith
gr.color_ramp.elements[0].position = 0.0; gr.color_ramp.elements[0].color = (1.0, 0.62, 0.72, 1)
gr.color_ramp.elements[1].position = 0.55; gr.color_ramp.elements[1].color = (0.22, 0.17, 0.36, 1)
WL.new(sepw.outputs['Z'], gr.inputs[0])
mixh = WN.new('ShaderNodeMix'); mixh.data_type = 'RGBA'; mixh.blend_type = 'MULTIPLY'
mixh.clamp_result = True; mixh.inputs['Factor'].default_value = 0.35; WL.new(gr.outputs[0], mixh.inputs['A']); WL.new(sat.outputs[0], mixh.inputs['B'])
glow = WN.new('ShaderNodeMix'); glow.data_type = 'RGBA'; glow.blend_type = 'ADD'
WL.new(pw.outputs[0], glow.inputs['Factor']); WL.new(mixh.outputs['Result'], glow.inputs['A'])
glow.inputs['B'].default_value = (1.3, 0.72, 0.55, 1)
WL.new(glow.outputs['Result'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = 0.55

# ---------------------------------------------------------------- foreground: scanned mossy rocks and grass
ROCKS = [load_obj(f'{PH}/rock_moss_set_01/rock_moss_set_01_1k.blend', 'rock_moss_set_01_rock0%d' % i) for i in (1, 2, 4, 5)]
GRASS = [load_obj(f'{PH}/grass_medium_02/grass_medium_02_2k.blend', 'grass_medium_02_%s' % k) for k in 'cde']
def place(src, loc, rot, sc):
    ob = bpy.data.objects.new(src.name, src.data); SC.collection.objects.link(ob)
    ob.location = loc; ob.rotation_euler = (0, 0, rot); ob.scale = sc
    return ob
for (x, y, sc, k) in [(-38, -304, 3.2, 0), (-31, -299, 2.4, 1), (-43, -296, 2.0, 2), (-27, -306, 1.6, 3),
                      (-4, -300, 1.8, 2), (2, -296, 1.3, 0)]:
    r = place(ROCKS[k], (x, y, -1.2 * sc / 2), rng.uniform(0, 6.28), (sc, sc, sc * 0.9))
    for q in range(int(10 * sc)):
        gx, gy = x + rng.uniform(-1.2, 1.2) * sc, y + rng.uniform(-1.0, 1.0) * sc
        gs = rng.uniform(4.0, 7.0)
        place(rng.choice(GRASS), (gx, gy, rng.uniform(0.2, 0.9) * sc), rng.uniform(0, 6.28), (gs, gs, gs * 1.4))

# ---------------------------------------------------------------- camera
cam = bpy.data.cameras.new('cam'); cam.lens = 35; cam.sensor_width = 36
cam.dof.use_dof = True; cam.dof.focus_distance = 330; cam.dof.aperture_fstop = 5.6
co = link_obj('cam', cam); SC.camera = co
co.location = (-24, -330, 3.0)
tgt = Vector((-4, 0, 36))
co.rotation_euler = (tgt - co.location).to_track_quat('-Z', 'Y').to_euler()

# ---------------------------------------------------------------- composite: depth haze, bloom, grade, grain
SC.view_layers[0].use_pass_mist = True
SC.world.mist_settings.start = 60; SC.world.mist_settings.depth = 3000; SC.world.mist_settings.falloff = 'QUADRATIC'
SC.use_nodes = True
T = SC.node_tree; CN = T.nodes; CL = T.links
for n in list(CN): CN.remove(n)
rl = CN.new('CompositorNodeRLayers'); out = CN.new('CompositorNodeComposite')
haze = CN.new('CompositorNodeMixRGB'); haze.blend_type = 'MIX'
haze.inputs[2].default_value = (0.95, 0.70, 0.88, 1)          # the pink dawn haze colour, linear
hz = CN.new('CompositorNodeMath'); hz.operation = 'MULTIPLY'; hz.inputs[1].default_value = 0.12
CL.new(rl.outputs['Mist'], hz.inputs[0]); CL.new(hz.outputs[0], haze.inputs[0])
CL.new(rl.outputs['Image'], haze.inputs[1])
gl = CN.new('CompositorNodeGlare'); gl.glare_type = 'FOG_GLOW'; gl.quality = 'MEDIUM'
try:
    gl.inputs['Threshold'].default_value = 0.8; gl.inputs['Strength'].default_value = 0.35; gl.inputs['Size'].default_value = 0.7
except Exception:
    gl.threshold = 0.8; gl.mix = -0.6; gl.size = 8
CL.new(haze.outputs[0], gl.inputs[0])
lens = CN.new('CompositorNodeLensdist')
try: lens.inputs['Distortion'].default_value = -0.008; lens.inputs['Dispersion'].default_value = 0.012
except Exception: pass
CL.new(gl.outputs[0], lens.inputs[0])
CL.new(lens.outputs[0], out.inputs[0])

# ---------------------------------------------------------------- render
SC.render.engine = 'CYCLES'
c = SC.cycles
c.device = 'CPU'; c.samples = SAMPLES; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.03
c.time_limit = TL; c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'
c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
c.max_bounces = 6; c.diffuse_bounces = 2; c.glossy_bounces = 3; c.transmission_bounces = 6
c.volume_bounces = 1; c.transparent_max_bounces = 8
c.caustics_reflective = False; c.caustics_refractive = False
c.sample_clamp_indirect = 8.0
c.volume_max_steps = 192; c.volume_step_rate = 6.0; c.volume_preview_step_rate = 6.0
SC.render.threads_mode = 'FIXED'; SC.render.threads = 4
SC.render.resolution_x, SC.render.resolution_y = W, H
SC.render.resolution_percentage = 100
SC.render.image_settings.file_format = 'PNG'
vs = SC.view_settings; vs.view_transform = 'AgX'; vs.look = 'AgX - Base Contrast'; vs.exposure = -0.5
SC.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('wrote', OUT)
