# Dawn over the Plate: first-frame draft.
# A hillside of flowers at sunrise; the old plate, its pillars and a dead reactor stack stand dark
# and quiet beyond a dry moat; the Break stands small and clean in the field.
# Blender 4.5 LTS, Cycles CPU. Poly Haven CC0 assets: pink_sunrise (HDRI), concrete_wall_008,
# rusty_metal_02, seaside_rock (textures), grass_medium_01 (scanned grass clumps).
#
# Run:  blender -b -P dawn_scene.py -- --assets <dir> --out <file> [--res 1600x900 --samples 32 --time 450]
import bpy, bmesh, math, json, os, re, sys, time
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    k = '--' + name
    return type(default)(argv[argv.index(k) + 1]) if k in argv else default

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = arg('assets', '')
OUT = arg('out', os.path.join(HERE, 'draft.png'))
RES = arg('res', '640x360')
SAMPLES = arg('samples', 32)
TIME = arg('time', 0.0)
EXPO = arg('exposure', -0.7)
DENS = arg('density', 1.0)
GEO = json.load(open(arg('geometry', '/tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad/break-geometry.json')))
rng = np.random.default_rng(11)

# ------------------------------------------------------------------ render settings
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
W, H = (int(v) for v in RES.split('x'))
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
sc.render.engine = 'CYCLES'
cy = sc.cycles
cy.device = 'CPU'; cy.samples = SAMPLES; cy.time_limit = TIME
cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.03
cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'; cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
cy.max_bounces = 6; cy.diffuse_bounces = 2; cy.glossy_bounces = 2
cy.transmission_bounces = 6; cy.transparent_max_bounces = 12; cy.volume_bounces = 0
cy.caustics_reflective = False; cy.caustics_refractive = False
cy.use_light_tree = True
sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = arg('look', 'AgX - Base Contrast')
sc.view_settings.exposure = EXPO
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '16'
sc.render.image_settings.color_mode = 'RGB'

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
def srgb2lin(c): return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92
def link_ob(ob, coll=None): (coll or sc.collection).objects.link(ob); return ob

# ------------------------------------------------------------------ sun and sky
# the camera looks down +Y; the sun sits a little right of the view, just over the horizon
SUN_AZ = math.radians(arg('sun-az', -21.5))    # right of +Y (negative: left), just past the first pillar
SUN_EL = math.radians(arg('sun-el', 5.0))
sun_vec = Vector((math.sin(SUN_AZ) * math.cos(SUN_EL), math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)))

wld = bpy.data.worlds.new('sky'); sc.world = wld; wld.use_nodes = True
wn = wld.node_tree; wn.nodes.clear()
tc = node(wn, 'ShaderNodeTexCoord', (-800, 0)); mp = node(wn, 'ShaderNodeMapping', (-600, 0))
# pink_sunrise: the glow sits at u = 0.6 of the panorama; turn it onto the sun's azimuth
HDRI_U = arg('hdri-u', 0.6)
phi_h = (0.5 - HDRI_U) * 2 * math.pi                 # Blender equirect: u = 0.5 - atan2(y, x) / 2pi
phi_s = math.atan2(sun_vec.y, sun_vec.x)
mp.inputs['Rotation'].default_value = (0, 0, phi_h - phi_s)
env = node(wn, 'ShaderNodeTexEnvironment', (-400, 0)); env.image = img(os.path.join(ASSETS, arg('hdri', 'pink_sunrise_8k.exr')))
bg = node(wn, 'ShaderNodeBackground', (-150, 0)); bg.inputs['Strength'].default_value = arg('sky', 0.5)
wo = node(wn, 'ShaderNodeOutputWorld', (100, 0))
link(wn, tc.outputs['Generated'], mp.inputs['Vector']); link(wn, mp.outputs['Vector'], env.inputs['Vector'])
link(wn, env.outputs['Color'], bg.inputs['Color']); link(wn, bg.outputs['Background'], wo.inputs['Surface'])
wld.cycles.sampling_method = 'MANUAL'; wld.cycles.sample_map_resolution = 2048
# the haze is lit by the sun alone, so light has shape: shafts in the air, shadowed air behind every pillar
try: wld.cycles_visibility.scatter = False
except Exception as e: print('world scatter', e)

sd = bpy.data.lights.new('sun', 'SUN'); sd.energy = arg('sun', 8.0); sd.angle = math.radians(0.8)
sd.color = (1.0, 0.70, 0.52)
sun = link_ob(bpy.data.objects.new('sun', sd))
sun.rotation_euler = (-sun_vec).to_track_quat('-Z', 'Y').to_euler()

bpy.ops.mesh.primitive_uv_sphere_add(radius=8000 * math.tan(math.radians(0.3)), location=sun_vec * 8000, segments=32, ring_count=16)
disc = bpy.context.object; disc.name = 'sun_disc'
m_d, nt = mat('sun_disc')
ed = node(nt, 'ShaderNodeEmission', (0, 0)); ed.inputs['Color'].default_value = (1.0, 0.78, 0.6, 1); ed.inputs['Strength'].default_value = arg('disc', 60.0)
o = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, ed.outputs['Emission'], o.inputs['Surface'])
disc.data.materials.append(m_d)
for v in ('visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter', 'visible_shadow'): setattr(disc, v, False)

# ------------------------------------------------------------------ ground: a hillside falling to the field, the dry moat, the rise to the plate
MOAT0, MOAT1, MOAT_D = 150.0, 185.0, 10.0
MX, MY = arg('mx', 1.6), arg('my', 17.0)
def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def ground_h(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    h = 4.6 * (1 - smooth(6, 45, y))                                     # the crest we stand on
    h += 0.35 * np.sin(x * 0.11 + 1.3) * np.sin(y * 0.07) * smooth(10, 40, y)
    h += 1.8 * np.sin(x * 0.012 + 0.4) * np.cos(y * 0.009) * smooth(60, 160, y)
    h += arg('rise', 0.6) * np.exp(-((x - MX) ** 2 + (y - MY) ** 2) / (2 * 2.6 ** 2))   # the low rise the stone stands on
    h += 9.0 * smooth(MOAT1 + 20, 650, y)                                # the field climbs to the old structures
    inm = (y > MOAT0 + 1.2) & (y < MOAT1 - 1.2)
    return np.where(inm, -MOAT_D, h)

rows = np.concatenate([np.geomspace(1.0, 3000.0, 520), [MOAT0, MOAT0 + 1.2, MOAT1 - 1.2, MOAT1]])
rows = np.unique(np.round(rows, 3))
NC = 360
bm = bmesh.new(); grid = []
for y in rows:
    hw = 1.25 * y + 30
    xs = np.linspace(-hw, hw, NC)
    zs = ground_h(xs, np.full(NC, y))
    grid.append([bm.verts.new((float(x), float(y), float(z))) for x, z in zip(xs, zs)])
for j in range(len(rows) - 1):
    for i in range(NC - 1):
        bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
me = bpy.data.meshes.new('ground'); bm.to_mesh(me); bm.free()
for p_ in me.polygons: p_.use_smooth = True
gnd = link_ob(bpy.data.objects.new('ground', me))

# field: green turf with a carpet of yellow, white and sky-blue flowers in drifts, read as colour at distance
m_g, nt = mat('field')
tco = node(nt, 'ShaderNodeTexCoord', (-1400, 0))
vor = node(nt, 'ShaderNodeTexVoronoi', (-1100, 200)); vor.inputs['Scale'].default_value = 9.0
link(nt, tco.outputs['Object'], vor.inputs['Vector'])
drift = node(nt, 'ShaderNodeTexNoise', (-1100, -200)); drift.inputs['Scale'].default_value = 0.012
drift.inputs['Detail'].default_value = 3
link(nt, tco.outputs['Object'], drift.inputs['Vector'])
sep = node(nt, 'ShaderNodeSeparateColor', (-900, 200)); link(nt, vor.outputs['Color'], sep.inputs['Color'])
cr = node(nt, 'ShaderNodeValToRGB', (-650, 200))     # per-cell colour pick
els = cr.color_ramp.elements; cr.color_ramp.interpolation = 'CONSTANT'
els[0].position = 0.0; els[0].color = (0.035, 0.07, 0.018, 1)              # turf
els[1].position = 0.12; els[1].color = (0.92, 0.6, 0.02, 1)               # yellow
e = els.new(0.5); e.color = (0.12, 0.42, 1.0, 1)                          # sky blue
e = els.new(0.84); e.color = (0.80, 0.80, 0.76, 1)                          # white
e = els.new(0.9); e.color = (0.035, 0.07, 0.018, 1)
# drifts: shift the pick so some ground runs to blue, some to yellow
mix = node(nt, 'ShaderNodeMath', (-800, 50), operation='MULTIPLY_ADD')
dm = node(nt, 'ShaderNodeMapRange', (-900, -200)); dm.inputs['From Min'].default_value = 0.35; dm.inputs['From Max'].default_value = 0.65
dm.inputs['To Min'].default_value = -0.3; dm.inputs['To Max'].default_value = 0.22
link(nt, drift.outputs['Fac'], dm.inputs['Value'])
link(nt, sep.outputs['Red'], mix.inputs[0]); mix.inputs[1].default_value = 1.0; link(nt, dm.outputs['Result'], mix.inputs[2])
link(nt, mix.outputs['Value'], cr.inputs['Fac'])
pb = node(nt, 'ShaderNodeBsdfPrincipled', (-200, 100)); pb.inputs['Roughness'].default_value = 0.8
# up close the ground is a real scan (Poly Haven sparse_grass); with distance it hands over to the flower carpet's colour
GT = arg('ground-tex', '/tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad/hm/ph/dl/sparse_grass')
gmp = node(nt, 'ShaderNodeMapping', (-1100, -500)); gmp.inputs['Scale'].default_value = (0.5, 0.5, 0.5)
link(nt, tco.outputs['Object'], gmp.inputs['Vector'])
gtx = node(nt, 'ShaderNodeTexImage', (-900, -500)); gtx.image = img(os.path.join(GT, 'sparse_grass_diff_2k.jpg'))
link(nt, gmp.outputs['Vector'], gtx.inputs['Vector'])
gnx = node(nt, 'ShaderNodeTexImage', (-900, -800)); gnx.image = img(os.path.join(GT, 'sparse_grass_nor_gl_2k.jpg'), True)
link(nt, gmp.outputs['Vector'], gnx.inputs['Vector'])
gnm = node(nt, 'ShaderNodeNormalMap', (-500, -800)); link(nt, gnx.outputs['Color'], gnm.inputs['Color']); link(nt, gnm.outputs['Normal'], pb.inputs['Normal'])
camd = node(nt, 'ShaderNodeCameraData', (-900, -1000))
dfa = node(nt, 'ShaderNodeMapRange', (-600, -1000)); dfa.inputs['From Min'].default_value = 35; dfa.inputs['From Max'].default_value = 110
link(nt, camd.outputs['View Distance'], dfa.inputs['Value'])
gmix = node(nt, 'ShaderNodeMix', (-400, 100)); gmix.data_type = 'RGBA'
link(nt, dfa.outputs['Result'], gmix.inputs['Factor']); link(nt, gtx.outputs['Color'], gmix.inputs['A']); link(nt, cr.outputs['Color'], gmix.inputs['B'])
link(nt, gmix.outputs['Result'], pb.inputs['Base Color'])
tl = node(nt, 'ShaderNodeBsdfTranslucent', (-200, -150)); link(nt, gmix.outputs['Result'], tl.inputs['Color'])
ms = node(nt, 'ShaderNodeMixShader', (50, 0)); ms.inputs['Fac'].default_value = 0.25
link(nt, pb.outputs['BSDF'], ms.inputs[1]); link(nt, tl.outputs['BSDF'], ms.inputs[2])
o = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, ms.outputs['Shader'], o.inputs['Surface'])
gnd.data.materials.append(m_g)

# ------------------------------------------------------------------ concrete and iron (scanned)
TEX = os.path.join(ASSETS, 'tex')
def scanned(name, base, scale, val=0.5, sat=0.5, rough=(0.6, 0.95), nstr=0.8, stain=True):
    m, nt = mat(name)
    tco = node(nt, 'ShaderNodeTexCoord', (-1400, 0))
    mpp = node(nt, 'ShaderNodeMapping', (-1200, 0)); mpp.inputs['Scale'].default_value = (scale,) * 3
    link(nt, tco.outputs['Object'], mpp.inputs['Vector'])
    def bt(sfx, nc, loc):
        t = node(nt, 'ShaderNodeTexImage', loc); t.image = img(os.path.join(TEX, f'{base}_{sfx}_2k.jpg'), nc)
        t.projection = 'BOX'; t.projection_blend = 0.3; link(nt, mpp.outputs['Vector'], t.inputs['Vector']); return t
    td, tr, tn = bt('diff', False, (-900, 300)), bt('rough', True, (-900, 0)), bt('nor_gl', True, (-900, -300))
    hs = node(nt, 'ShaderNodeHueSaturation', (-600, 300)); hs.inputs['Saturation'].default_value = sat
    hs.inputs['Value'].default_value = val; link(nt, td.outputs['Color'], hs.inputs['Color'])
    col = hs.outputs['Color']
    if stain:   # big soft water stains so vast faces do not tile
        nz = node(nt, 'ShaderNodeTexNoise', (-900, 600)); nz.inputs['Scale'].default_value = 0.02; nz.inputs['Detail'].default_value = 6
        link(nt, tco.outputs['Object'], nz.inputs['Vector'])
        mr = node(nt, 'ShaderNodeMapRange', (-600, 600)); mr.inputs['To Min'].default_value = 0.45; mr.inputs['To Max'].default_value = 1.15
        link(nt, nz.outputs['Fac'], mr.inputs['Value'])
        mm = node(nt, 'ShaderNodeMix', (-400, 300)); mm.data_type = 'RGBA'; mm.blend_type = 'MULTIPLY'; mm.inputs['Factor'].default_value = 1
        link(nt, col, mm.inputs['A']); link(nt, mr.outputs['Result'], mm.inputs['B']); col = mm.outputs['Result']
    rr = node(nt, 'ShaderNodeMapRange', (-600, 0)); rr.inputs['To Min'].default_value = rough[0]; rr.inputs['To Max'].default_value = rough[1]
    link(nt, tr.outputs['Color'], rr.inputs['Value'])
    nm = node(nt, 'ShaderNodeNormalMap', (-600, -300)); nm.inputs['Strength'].default_value = nstr
    link(nt, tn.outputs['Color'], nm.inputs['Color'])
    b = node(nt, 'ShaderNodeBsdfPrincipled', (-100, 0))
    link(nt, col, b.inputs['Base Color']); link(nt, rr.outputs['Result'], b.inputs['Roughness']); link(nt, nm.outputs['Normal'], b.inputs['Normal'])
    o = node(nt, 'ShaderNodeOutputMaterial', (200, 0)); link(nt, b.outputs['BSDF'], o.inputs['Surface'])
    return m
M_CON = scanned('concrete', 'concrete_wall_008', 0.12, val=arg('con-val', 0.05), sat=0.35)
M_LIP = scanned('lip', 'concrete_wall_008', 0.25, val=0.7, sat=0.3)
M_IRON = scanned('iron', 'rusty_metal_02', 0.15, val=0.28, sat=0.25, rough=(0.5, 0.9), stain=False)

def add_mesh(name, bm, m):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(m)
    return link_ob(bpy.data.objects.new(name, me))
def box(bm, c, s, rot=None):
    r = bmesh.ops.create_cube(bm, size=1.0)
    M = Matrix.Translation(Vector(c)) @ (rot.to_4x4() if rot else Matrix.Identity(4)) @ Matrix.Diagonal((*s, 1))
    bmesh.ops.transform(bm, matrix=M, verts=r['verts'])
def cyl(bm, c, r1, r2, h, n=48):
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=n, radius1=r1, radius2=r2, depth=h)
    bmesh.ops.translate(bm, vec=Vector((c[0], c[1], c[2] + h / 2)), verts=res['verts'])
def prism_z(bm, pts, z0, z1):
    vs0 = [bm.verts.new((x, y, z0)) for x, y in pts]; vs1 = [bm.verts.new((x, y, z1)) for x, y in pts]
    bm.faces.new(vs0[::-1]); bm.faces.new(vs1)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((vs0[i], vs0[j], vs1[j], vs1[i]))

# ------------------------------------------------------------------ the plate: the old order, broken off at its right-hand end
PY0, PB, PT = 330.0, 205.0, 233.0          # front edge distance, underside, top
PY1 = 1150.0                                 # the plate's far edge: sky shows beneath it
def x_edge(y): return -150 - (y - PY0) * 0.36
edge = []
for k, y in enumerate(np.arange(PY0, PY1, 38.0)):
    edge.append((x_edge(y) + rng.uniform(-18, 18) * (0.3 if k == 0 else 1), y))
pts = [(-3200, PY0)] + edge + [(edge[-1][0], PY1), (-3200, PY1)]
bm = bmesh.new(); prism_z(bm, pts, PB, PT)
# underside: a grid of deep beams, the way a plate is carried
for y in np.arange(PY0 + 6, PY1 - 10, 46.0):
    xe = x_edge(y) - 22
    box(bm, ((xe - 3200) / 2, y, PB - 4.5), (xe + 3200, 3.5, 9))
# front fascia: deep vertical fins give the edge its scale
for x in np.arange(-3150, x_edge(PY0) - 30, 14.0):
    box(bm, (x, PY0 - 1.2, (PB + PT) / 2 - 2), (1.4, 2.4, PT - PB + 6))
box(bm, ((x_edge(PY0) - 3200) / 2, PY0 - 2.5, PT + 2.5), (x_edge(PY0) + 3200, 5, 5))
plate = add_mesh('plate', bm, M_CON)
# what hangs from the break: torn beams and one slab still hinged to the edge
bm = bmesh.new()
for (x, y) in edge[:12:3]:
    for _ in range(2):
        L = rng.uniform(18, 45); a = math.radians(rng.uniform(55, 85)); az = rng.uniform(-0.3, 0.6)
        d = Vector((math.cos(az) * math.cos(a), math.sin(az) * math.cos(a) * 0.4, -math.sin(a)))
        rot = d.to_track_quat('X', 'Z').to_matrix()
        box(bm, Vector((x - 6, y, PB + 4)) + d * (L / 2), (L, rng.uniform(1.6, 3.2), rng.uniform(1.6, 3.2)), rot)
add_mesh('torn', bm, M_IRON)

# pillars: a colonnade under the plate, standing in the flowers
bm = bmesh.new()
for (x, y) in ((-200, 395), (-520, 395), (-390, 820), (-720, 820)):
    gz = float(ground_h(x, y)) - 2
    cyl(bm, (x, y, gz), 21, 19, PB - gz - 14, 64)
    cyl(bm, (x, y, PB - 14), 19, 30, 14, 64)                  # capital flaring into the plate
    cyl(bm, (x, y, gz), 24, 24, 9, 64)                         # plinth
    for hz in (0.35, 0.62):
        cyl(bm, (x, y, gz + (PB - gz) * hz), 21.8, 21.8, 2.2, 64)
add_mesh('pillars', bm, M_CON)

# the dead reactor stacks: tall, tapered, ringed with empty gantries, cold
bm = bmesh.new()
for (x, y, hh, r0, r1) in ((235, 1000, 300, 46, 31), (560, 1900, 235, 40, 28)):
    gz = float(ground_h(x, y)) - 2
    cyl(bm, (x, y, gz), r0, r1, hh, 72)
    cyl(bm, (x, y, gz + hh), r1 + 2.5, r1 + 2.5, 5, 72)      # lip
    for f in (0.42, 0.7):
        rr = r0 + (r1 - r0) * f
        cyl(bm, (x, y, gz + hh * f), rr + 5, rr + 5, 1.6, 72)  # gantry deck
        cyl(bm, (x, y, gz + hh * f + 3.2), rr + 5.2, rr + 5.2, 0.5, 72)   # rail
    box(bm, (x - r0 * 0.75, y - r0 * 0.6, gz + hh * 0.5), (4, 4, hh))       # service spine
    cyl(bm, (x, y, gz), r0 + 18, r0 + 12, 14, 72)               # foundation drum
add_mesh('stacks', bm, M_CON)

# the far ruins of the old city on the horizon: simple masses, lost in the haze
bm = bmesh.new()
for x in np.arange(-6000, 4200, 160.0):
    w = rng.uniform(90, 260); hh = rng.uniform(25, 115) * (0.6 + 0.4 * math.sin(x * 0.0011 + 1.0) ** 2)
    yy = rng.uniform(2700, 3400)
    box(bm, (x, yy, hh / 2 - 5), (w, rng.uniform(80, 200), hh + 10))
add_mesh('far', bm, M_CON)

# the dry moat: concrete walls and a cracked bed, flowers spilling over its lip
bm = bmesh.new()
for yw, sgn in ((MOAT0 + 0.6, 1), (MOAT1 - 0.6, -1)):
    box(bm, (0, yw, -MOAT_D / 2 + 0.3), (5000, 1.6, MOAT_D + 1.4))
for x in np.arange(-2400, 2400, 26.0):                         # buttresses on the far wall, lit by the low sun
    box(bm, (x, MOAT1 - 2.2, -MOAT_D / 2), (2.0, 3.0, MOAT_D))
box(bm, (0, (MOAT0 + MOAT1) / 2, -MOAT_D - 0.5), (5000, MOAT1 - MOAT0, 1.0))
add_mesh('moat', bm, M_CON)
# the lip: pale coping stones on both edges that catch the low sun
bm = bmesh.new()
for yw in (MOAT0 + 0.2, MOAT1 - 0.2):
    for x in np.arange(-2500, 2500, 6.0):
        box(bm, (x + 3, yw, float(ground_h(x, yw - 3 if yw < 170 else yw + 3)) + 0.25), (5.9, 2.2, 0.9))
add_mesh('lip', bm, M_LIP)

# ------------------------------------------------------------------ haze: aerial depth and a low mist in the moat
def volume_box(name, c, s, dens, col, aniso):
    bm = bmesh.new(); box(bm, c, s)
    m, nt = mat(name)
    pv = node(nt, 'ShaderNodeVolumePrincipled', (0, 0))
    pv.inputs['Density'].default_value = dens; pv.inputs['Color'].default_value = (*col, 1)
    pv.inputs['Anisotropy'].default_value = aniso
    o = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, pv.outputs['Volume'], o.inputs['Volume'])
    ob = add_mesh(name, bm, m)
    ob.visible_shadow = True
    return ob
volume_box('haze', (0, 1700, 140), (12000, 3600, 320), arg('haze', 0.00011), (1.0, 0.86, 0.82), 0.75)
volume_box('mist', (0, (MOAT0 + MOAT1) / 2, -4.5), (9000, MOAT1 - MOAT0 - 2, 12), arg('mist', 0.008), (1.0, 0.9, 0.9), 0.6)
volume_box('shafts', (-420, 760, 110), (900, 900, 230), arg('shafts', 0.0005), (1.0, 0.86, 0.8), 0.8)
volume_box('lowmist', (0, 800, 0), (9000, 1300, 6), arg('lowmist', 0.0004), (1.0, 0.9, 0.9), 0.6)

# ------------------------------------------------------------------ the Break: exact geometry, dark honed stone, sky crystal
S, T = 0.019, 0.5
MZ = float(ground_h(MX, MY)) - 0.06
def svg_poly(d):
    nums = [float(v) for v in re.findall(r'-?\d+\.?\d*', d)]
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
def to_xz(p): return ((p[0] - 50) * S, (100 - p[1]) * S)
def rrect(rx=22, n=14):
    pts = []
    for cx, cy_, a0 in ((100 - rx, rx, -90), (100 - rx, 100 - rx, 0), (rx, 100 - rx, 90), (rx, rx, 180)):
        for i in range(n + 1):
            t = math.radians(a0 + 90 * i / n); pts.append((cx + rx * math.cos(t), cy_ + rx * math.sin(t)))
    return pts
def prism_y(name, pts2d, y0, y1):
    bm = bmesh.new()
    f = [bm.verts.new((x, y0, z)) for x, z in pts2d]; b = [bm.verts.new((x, y1, z)) for x, z in pts2d]
    bm.faces.new(f[::-1]); bm.faces.new(b)
    for i in range(len(pts2d)):
        j = (i + 1) % len(pts2d); bm.faces.new((f[i], f[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return link_ob(bpy.data.objects.new(name, me))
tile = prism_y('stone', [to_xz(p) for p in rrect()], -T / 2, T / 2)
cut_seam = prism_y('cut_seam', [to_xz(p) for p in svg_poly(GEO['seam'])], -T, T)
cut_cav = prism_y('cut_cav', [to_xz(p) for p in svg_poly(GEO['cav'])], -T, T)
for c in (cut_seam, cut_cav):
    md = tile.modifiers.new('cut', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = c
    md.material_mode = 'TRANSFER'; c.hide_render = True; c.hide_viewport = True
bv = tile.modifiers.new('arris', 'BEVEL'); bv.width = 0.016; bv.segments = 4; bv.limit_method = 'ANGLE'
bv.angle_limit = math.radians(35)
tile.modifiers.new('wn', 'WEIGHTED_NORMAL')
gem = [to_xz(p) for p in svg_poly(GEO['gem'])]; cxz = to_xz((50, 51.5))
ZE, ZR = T / 2 - 0.1, T / 2 - 0.012
bm = bmesh.new()
fr = [bm.verts.new((x, -ZE, z)) for x, z in gem]; bk = [bm.verts.new((x, ZE, z)) for x, z in gem]
af = bm.verts.new((cxz[0], -ZR, cxz[1])); ab = bm.verts.new((cxz[0], ZR, cxz[1]))
for i in range(len(gem)):
    j = (i + 1) % len(gem)
    bm.faces.new((fr[i], fr[j], af)); bm.faces.new((bk[j], bk[i], ab)); bm.faces.new((fr[j], fr[i], bk[i], bk[j]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new('crystal'); bm.to_mesh(me); bm.free()
crystal = link_ob(bpy.data.objects.new('crystal', me))
mark = link_ob(bpy.data.objects.new('mark', None))
mark.location = (MX, MY, MZ); mark.rotation_euler = (0, 0, math.radians(arg('yaw', -5.4)))
for o_ in (tile, crystal, cut_seam, cut_cav): o_.parent = mark

ST = os.path.join(TEX, 'seaside_rock')
m_st, nt = mat('stone')
tco = node(nt, 'ShaderNodeTexCoord', (-1200, 0))
mpp = node(nt, 'ShaderNodeMapping', (-1000, 0)); mpp.inputs['Scale'].default_value = (0.9, 0.9, 0.9)
link(nt, tco.outputs['Object'], mpp.inputs['Vector'])
def stex(f, nc, loc):
    t = node(nt, 'ShaderNodeTexImage', loc); t.image = img(os.path.join(ST, f), nc); t.projection = 'BOX'; t.projection_blend = 0.25
    link(nt, mpp.outputs['Vector'], t.inputs['Vector']); return t
td = stex('seaside_rock_diff_2k.jpg', False, (-700, 200)); tr = stex('seaside_rock_rough_2k.jpg', True, (-700, -100))
tn = stex('seaside_rock_nor_gl_2k.jpg', True, (-700, -400))
hsv = node(nt, 'ShaderNodeHueSaturation', (-400, 200)); hsv.inputs['Saturation'].default_value = 0.1
hsv.inputs['Value'].default_value = arg('st-val', 0.36); link(nt, td.outputs['Color'], hsv.inputs['Color'])
rr = node(nt, 'ShaderNodeMapRange', (-400, -100)); rr.inputs['To Min'].default_value = 0.26; rr.inputs['To Max'].default_value = 0.46
link(nt, tr.outputs['Color'], rr.inputs['Value'])
nm = node(nt, 'ShaderNodeNormalMap', (-400, -400)); nm.inputs['Strength'].default_value = 0.5; link(nt, tn.outputs['Color'], nm.inputs['Color'])
b = node(nt, 'ShaderNodeBsdfPrincipled', (0, 0)); b.inputs['Specular IOR Level'].default_value = 0.55
link(nt, hsv.outputs['Color'], b.inputs['Base Color']); link(nt, rr.outputs['Result'], b.inputs['Roughness']); link(nt, nm.outputs['Normal'], b.inputs['Normal'])
o = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, b.outputs['BSDF'], o.inputs['Surface'])
tile.data.materials.append(m_st)
m_in = m_st.copy(); m_in.name = 'stone_cut'
for n_ in m_in.node_tree.nodes:
    if n_.bl_idname == 'ShaderNodeHueSaturation': n_.inputs['Value'].default_value = 0.14
    if n_.bl_idname == 'ShaderNodeMapRange': n_.inputs['To Min'].default_value = 0.6; n_.inputs['To Max'].default_value = 0.8
for c in (cut_seam, cut_cav): c.data.materials.append(m_in)

SKY = [srgb2lin(v / 255) for v in (0x94, 0xE6, 0xFF)]
m_cr, nt = mat('crystal')
b = node(nt, 'ShaderNodeBsdfPrincipled', (0, 0))
b.inputs['Base Color'].default_value = (*[v ** 1.6 for v in SKY], 1)
b.inputs['Subsurface Weight'].default_value = 1.0; b.inputs['Subsurface Radius'].default_value = (0.35, 0.8, 1.0)
b.inputs['Subsurface Scale'].default_value = 0.12
b.inputs['Transmission Weight'].default_value = 0.9; b.inputs['Roughness'].default_value = 0.12; b.inputs['IOR'].default_value = 1.52
b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.02
# caustics are off on CPU, so the sunrise poured through the crystal is put back as a faint glow of its own colour
emc = node(nt, 'ShaderNodeEmission', (0, -300)); emc.inputs['Color'].default_value = (*SKY, 1)
emc.inputs['Strength'].default_value = arg('cr-glow', 1.4)
ad = node(nt, 'ShaderNodeAddShader', (200, 0)); link(nt, b.outputs['BSDF'], ad.inputs[0]); link(nt, emc.outputs['Emission'], ad.inputs[1])
o = node(nt, 'ShaderNodeOutputMaterial', (400, 0)); link(nt, ad.outputs['Shader'], o.inputs['Surface'])
crystal.data.materials.append(m_cr)

# ------------------------------------------------------------------ flowers and grass
def blade_points(L, tilt, az, droop):
    pts = []; N = 6
    d = Vector((math.sin(tilt) * math.cos(az), math.sin(tilt) * math.sin(az), math.cos(tilt)))
    p = Vector((0, 0, 0))
    for i in range(N + 1):
        pts.append(p.copy())
        d = (d + Vector((math.cos(az), math.sin(az), 0)) * droop * (i / N) * 0.6).normalized()
        p = p + d * (L / N)
    return pts
def petal_mat(name, col, tcol, mixf=0.5, rough=0.45):
    m, nt = mat(name)
    p = node(nt, 'ShaderNodeBsdfPrincipled', (0, 200)); p.inputs['Base Color'].default_value = (*col, 1)
    p.inputs['Roughness'].default_value = rough; p.inputs['Specular IOR Level'].default_value = 0.5
    t = node(nt, 'ShaderNodeBsdfTranslucent', (0, -100)); t.inputs['Color'].default_value = (*tcol, 1)
    m_ = node(nt, 'ShaderNodeMixShader', (250, 0)); m_.inputs['Fac'].default_value = mixf
    link(nt, p.outputs['BSDF'], m_.inputs[1]); link(nt, t.outputs['BSDF'], m_.inputs[2])
    o = node(nt, 'ShaderNodeOutputMaterial', (500, 0)); link(nt, m_.outputs['Shader'], o.inputs['Surface'])
    return m
M_STEM = petal_mat('stem', (0.05, 0.13, 0.025), (0.2, 0.42, 0.05), 0.4, 0.5)
M_YEL = petal_mat('yellow', (0.82, 0.58, 0.035), (1.0, 0.78, 0.12), 0.45, 0.3)
M_BLU = petal_mat('blue', (0.36, 0.66, 1.0), (0.55, 0.86, 1.0), 0.5)
M_WHT = petal_mat('white', (0.86, 0.85, 0.82), (1.0, 0.96, 0.9), 0.45)
M_EYE = petal_mat('eye', (0.62, 0.5, 0.06), (0.7, 0.55, 0.1), 0.1, 0.7)

def flower(name, h, npet, R, wv, pmat, disc_r, cup):
    bm = bmesh.new()
    pts = blade_points(h, rng.uniform(0.02, 0.2), rng.uniform(0, 6.28), 0.06)
    ring = []
    for pnt in pts:
        ring.append([bm.verts.new(pnt + Vector((0.0018 * math.cos(a), 0.0018 * math.sin(a), 0))) for a in (0, 2.1, 4.2)])
    for i in range(len(ring) - 1):
        for j in range(3):
            bm.faces.new((ring[i][j], ring[i][(j + 1) % 3], ring[i + 1][(j + 1) % 3], ring[i + 1][j]))
    # two leaves low on the stem
    for k in range(2):
        a = rng.uniform(0, 6.28); base = pts[1 + k]
        lv = [Vector((0, 0, 0)), Vector((0.03 * math.cos(a) - 0.006 * math.sin(a), 0.03 * math.sin(a) + 0.006 * math.cos(a), 0.02)),
              Vector((0.06 * math.cos(a), 0.06 * math.sin(a), 0.015)), Vector((0.03 * math.cos(a) + 0.006 * math.sin(a), 0.03 * math.sin(a) - 0.006 * math.cos(a), 0.02))]
        bm.faces.new([bm.verts.new(base + v) for v in lv])
    top = pts[-1]; rot = Vector((rng.normal(0, 0.3), rng.normal(0, 0.3), 1)).normalized().to_track_quat('Z', 'Y')
    for k in range(npet):
        a = 2 * math.pi * k / npet + rng.normal(0, 0.06)
        loc = [Vector((0.002, -wv * 0.4, 0)), Vector((R * 0.6, -wv, cup * 0.5)), Vector((R, -wv * 0.6, cup)), Vector((R + 0.001, 0, cup)),
               Vector((R, wv * 0.6, cup)), Vector((R * 0.6, wv, cup * 0.5)), Vector((0.002, wv * 0.4, 0))]
        rz = Matrix.Rotation(a, 3, 'Z')
        f = bm.faces.new([bm.verts.new(top + rot @ (rz @ v)) for v in loc]); f.material_index = 1
    f = bm.faces.new([bm.verts.new(top + rot @ Vector((disc_r * math.cos(a), disc_r * math.sin(a), 0.002)))
                      for a in np.linspace(0, 2 * math.pi, 10, endpoint=False)]); f.material_index = 2
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for mm in (M_STEM, pmat, M_EYE): me.materials.append(mm)
    return bpy.data.objects.new(name, me)

PH = arg('ph', '/tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad/assets/polyhaven')
def ph_objects(asset, names):
    with bpy.data.libraries.load(os.path.join(PH, asset, asset + '_2k.blend'), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names]
    out = []
    for ob in dst.objects:
        ob.location = (0, 0, 0); ob.rotation_euler = (0, 0, 0); ob.parent = None
        for md in list(ob.modifiers): ob.modifiers.remove(md)
        out.append(ob)
    return out
# real scanned flowers (Poly Haven): lesser celandine and empodium for the yellow, heliophila for the sky blue,
# dandelion clocks for the white
flib = bpy.data.collections.new('flower_lib'); sc.collection.children.link(flib)
WHT = ph_objects('flower_heliophila', ['flower_heliophila_small_LOD3'])
EMP = ph_objects('flower_empodium', [f'flower_empodium_{c}_LOD1' for c in 'abd'])
# heliophila is a dense cushion of small scanned flowers with white petals. Copies of it are tinted, petals only
# (the pale, unsaturated pixels), to buttercup yellow for the front and a true sky blue for the band behind
def tinted(ob, rgb, tag_):
    col = [srgb2lin(v / 255) for v in rgb]
    b_ = ob.copy(); b_.data = ob.data.copy(); b_.name = ob.name + '_' + tag_
    m = ob.data.materials[0].copy(); m.name = 'heliophila_' + tag_; b_.data.materials[0] = m
    nt = m.node_tree
    for l in list(nt.links):
        if l.to_node.bl_idname == 'ShaderNodeGroup' and l.to_socket.name in ('Diffuse', 'Translucency'):
            src = l.from_socket; dst = l.to_socket
            hsv = nt.nodes.new('ShaderNodeSeparateColor'); hsv.mode = 'HSV'; link(nt, src, hsv.inputs['Color'])
            mv = nt.nodes.new('ShaderNodeMapRange'); mv.inputs['From Min'].default_value = 0.3; mv.inputs['From Max'].default_value = 0.5
            link(nt, hsv.outputs['Blue'], mv.inputs['Value'])
            ms_ = nt.nodes.new('ShaderNodeMapRange'); ms_.inputs['From Min'].default_value = 0.45; ms_.inputs['From Max'].default_value = 0.2
            link(nt, hsv.outputs['Green'], ms_.inputs['Value'])
            mk = nt.nodes.new('ShaderNodeMath'); mk.operation = 'MULTIPLY'; link(nt, mv.outputs['Result'], mk.inputs[0]); link(nt, ms_.outputs['Result'], mk.inputs[1])
            mx_ = nt.nodes.new('ShaderNodeMix'); mx_.data_type = 'RGBA'
            link(nt, mk.outputs['Value'], mx_.inputs['Factor']); link(nt, src, mx_.inputs['A']); mx_.inputs['B'].default_value = (*col, 1)
            nt.links.remove(l); link(nt, mx_.outputs['Result'], dst)
    return b_
YEL = [tinted(o, (0xF2, 0xC4, 0x1A), 'yellow') for o in WHT] * 2 + EMP
BLU = [tinted(o, (0x4F, 0xAE, 0xFF), 'sky') for o in WHT]
for ob in list(dict.fromkeys(YEL)) + BLU + WHT: flib.objects.link(ob)
YEL = list(dict.fromkeys(YEL))
NY, NB, NW = len(YEL), len(BLU), len(WHT)
print('flower lib', NY, NB, NW)

# scanned grass clumps (Poly Haven grass_medium_01)
glib = bpy.data.collections.new('grass_lib'); sc.collection.children.link(glib)
gdir = os.path.join(ASSETS, 'grass_medium_01')
A_DIFF = img(os.path.join(gdir, 'textures', 'grass_medium_01_diff_2k.jpg'))
A_ALPHA = img(os.path.join(gdir, 'textures', 'grass_medium_01_alpha_2k.png'), True)
m_gr, nt = mat('ph_grass')
uv = node(nt, 'ShaderNodeUVMap', (-1000, 0)); uv.uv_map = 'UVMap'
t = node(nt, 'ShaderNodeTexImage', (-800, 100)); t.image = A_DIFF; link(nt, uv.outputs['UV'], t.inputs['Vector'])
ta = node(nt, 'ShaderNodeTexImage', (-800, -300)); ta.image = A_ALPHA; link(nt, uv.outputs['UV'], ta.inputs['Vector'])
hs = node(nt, 'ShaderNodeHueSaturation', (-500, 100)); hs.inputs['Value'].default_value = 0.85; hs.inputs['Saturation'].default_value = 1.05
link(nt, t.outputs['Color'], hs.inputs['Color'])
p = node(nt, 'ShaderNodeBsdfPrincipled', (-200, 200)); p.inputs['Roughness'].default_value = 0.45; link(nt, hs.outputs['Color'], p.inputs['Base Color'])
tb = node(nt, 'ShaderNodeMix', (-300, -100)); tb.data_type = 'RGBA'; tb.blend_type = 'MULTIPLY'; tb.inputs['Factor'].default_value = 1
link(nt, hs.outputs['Color'], tb.inputs['A']); tb.inputs['B'].default_value = (1.4, 1.6, 0.6, 1)
tl = node(nt, 'ShaderNodeBsdfTranslucent', (-100, -100)); link(nt, tb.outputs['Result'], tl.inputs['Color'])
m1 = node(nt, 'ShaderNodeMixShader', (100, 0)); m1.inputs['Fac'].default_value = 0.45
link(nt, p.outputs['BSDF'], m1.inputs[1]); link(nt, tl.outputs['BSDF'], m1.inputs[2])
tp = node(nt, 'ShaderNodeBsdfTransparent', (100, -300))
m2 = node(nt, 'ShaderNodeMixShader', (300, 0)); link(nt, ta.outputs['Color'], m2.inputs['Fac'])
link(nt, tp.outputs['BSDF'], m2.inputs[1]); link(nt, m1.outputs['Shader'], m2.inputs[2])
o = node(nt, 'ShaderNodeOutputMaterial', (500, 0)); link(nt, m2.outputs['Shader'], o.inputs['Surface'])
with bpy.data.libraries.load(os.path.join(gdir, 'grass_medium_01_2k.blend'), link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.endswith('_LOD1')]
for ob in ph_objects('grass_medium_02', [f'grass_medium_02_{c}' for c in 'bcde']):
    glib.objects.link(ob)
for ob in dst.objects:
    me = ob.data; me.materials.clear(); me.materials.append(m_gr)
    if me.uv_layers and me.uv_layers[0].name != 'UVMap': me.uv_layers[0].name = 'UVMap'
    ob.location = (0, 0, 0); ob.rotation_euler = (0, 0, 0); glib.objects.link(ob)
NG = len(glib.objects)

# ------------------------------------------------------------------ camera: on the hillside, a little above the flowers
CAM_Z = float(ground_h(0, 0)) + arg('eye', 1.0)
cam_d = bpy.data.cameras.new('cam'); cam = link_ob(bpy.data.objects.new('cam', cam_d)); sc.camera = cam
cam_d.lens = arg('lens', 24.0); cam_d.sensor_width = 36; cam_d.sensor_fit = 'HORIZONTAL'
cam.location = (0, 0, CAM_Z)
cam.rotation_euler = (math.pi / 2 + math.radians(arg('pitch', 3.5)), 0, math.radians(arg('cam-yaw', 10.0)))
cam_d.dof.use_dof = True; cam_d.dof.focus_distance = math.hypot(MX, MY); cam_d.dof.aperture_fstop = arg('fstop', 4.0)
cam_d.clip_start = 0.05; cam_d.clip_end = 12000
HALF = math.atan(18 / cam_d.lens) + math.radians(6)

def scatter(name, coll, n, rmin, rmax, keep, pick, scl_fn, clump=True):
    th = rng.uniform(-HALF, HALF, n) - cam.rotation_euler.z; r = np.sqrt(rng.uniform(rmin ** 2, rmax ** 2, n))
    xx = r * np.sin(th); yy = r * np.cos(th)
    patch = 0.5 + 0.5 * np.sin(xx * 0.9 + 2.0 * np.sin(yy * 0.6)) * np.sin(yy * 0.75 + 1.5 * np.sin(xx * 0.5))
    patch = np.clip(0.25 + patch, 0, 1) if clump else 1.0
    k = rng.uniform(0, 1, n) < keep(r) * patch; th, r = th[k], r[k]
    x = r * np.sin(th); y = r * np.cos(th)
    c, s_ = math.cos(-mark.rotation_euler.z), math.sin(-mark.rotation_euler.z)
    lx = (x - MX) * c - (y - MY) * s_; ly = (x - MX) * s_ + (y - MY) * c
    ok = ~((np.abs(lx) < 1.08) & (np.abs(ly) < 0.42))          # never on the stone
    x, y, r = x[ok], y[ok], r[ok]; m = len(x)
    v = np.zeros((m, 3), np.float32); v[:, 0] = x; v[:, 1] = y; v[:, 2] = ground_h(x, y) - 0.01
    me = bpy.data.meshes.new(name); me.vertices.add(m); me.vertices.foreach_set('co', v.ravel())
    rot = np.zeros((m, 3), np.float32); rot[:, 2] = rng.uniform(0, 6.283, m)
    rot[:, 0] = rng.normal(0, 0.05, m); rot[:, 1] = rng.normal(0, 0.05, m)
    s1 = scl_fn(r, m).astype(np.float32)
    dmk = np.hypot(x - MX, y - MY)
    lat = np.abs(x - MX * y / MY)
    s1 *= np.where(dmk < 3.0, 0.35 + 0.65 * np.clip((dmk - 1.3) / 1.7, 0, 1), 1.0)
    s1 *= np.where((y < MY) & (y > 4) & (lat < 2.2), 0.45 + 0.55 * np.clip((lat - 1.0) / 1.2, 0, 1), 1.0)
    s1 = s1.astype(np.float32)
    scl = np.stack([s1, s1, s1 * rng.uniform(0.85, 1.2, m)], 1).astype(np.float32)
    pk = pick(m, x, y).astype(np.int32)
    pass
    for an, data, tp in (('rot', rot, 'FLOAT_VECTOR'), ('scl', scl, 'FLOAT_VECTOR'), ('pick', pk, 'INT')):
        at = me.attributes.new(an, tp, 'POINT'); at.data.foreach_set('vector' if tp == 'FLOAT_VECTOR' else 'value', data.ravel())
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
    md = ob.modifiers.new('scatter', 'NODES'); md.node_group = ng
    print(name, m, 'instances'); return ob

def fpick(m, x, y):
    # drifts: buttercup yellow in front, a true sky-blue band behind and round the stone, white sprinkled through
    r = np.hypot(x, y)
    band = smooth(13, 19, r) * (1 - smooth(38, 50, r)) * (0.8 + 0.2 * np.sin(x * 0.4 + 1.0))
    band = np.maximum(band, 0.85 * (1 - smooth(1.2, 3.5, np.hypot(x - MX, y - MY))))
    u = rng.uniform(0, 1, m); pb = 0.04 + 0.86 * band
    return np.where(u < pb, NY + rng.integers(0, NB, m), np.where(u < pb + 0.06, NY + NB + rng.integers(0, NW, m), np.where(rng.uniform(0, 1, m) < 0.7, 0, rng.integers(1, NY, m))))
scatter('flowers', flib, int(1400000 * DENS), 0.7, 70, lambda r: np.clip((6 / r) ** 1.15, 0.02, 1.0), fpick,
        lambda r, m: rng.uniform(0.8, 1.15, m) * (1 + r / 60))
scatter('grass', glib, int(500000 * DENS), 0.7, 50, lambda r: np.clip((5 / r) ** 1.3, 0.02, 1.0),
        lambda m, x, y: rng.integers(0, NG, m), lambda r, m: rng.uniform(0.5, 0.85, m) * (1 + r / 60), clump=False)
flib.hide_render = True; glib.hide_render = True

# ------------------------------------------------------------------ data passes for the loop: plants, the mark, depth
vl = sc.view_layers[0]
for nm_ in ('gm', 'mk'):
    av = vl.aovs.add(); av.name = nm_; av.type = 'VALUE'
vl.use_pass_z = True
def tag(m, name):
    nt = m.node_tree
    o = nt.nodes.new('ShaderNodeOutputAOV'); o.aov_name = name; o.inputs['Value'].default_value = 1.0
plant_mats = set()
for c in (flib, glib):
    for ob in c.objects:
        for m in ob.data.materials:
            if m: plant_mats.add(m)
for m in plant_mats: tag(m, 'gm')
for m in (m_st, m_in, m_cr): tag(m, 'mk')
PASSES = arg('passes', '')

# ------------------------------------------------------------------ compositor: soft bloom
sc.use_nodes = True
ct = sc.node_tree; ct.nodes.clear()
rl = ct.nodes.new('CompositorNodeRLayers'); comp = ct.nodes.new('CompositorNodeComposite')
gl = ct.nodes.new('CompositorNodeGlare'); gl.glare_type = 'BLOOM'; gl.quality = 'HIGH'
gl.inputs['Threshold'].default_value = 1.0; gl.inputs['Smoothness'].default_value = 0.6
gl.inputs['Strength'].default_value = arg('bloom', 0.25); gl.inputs['Size'].default_value = 0.85
gl.inputs['Tint'].default_value = (1.0, 0.86, 0.85, 1)
ct.links.new(rl.outputs['Image'], gl.inputs['Image']); ct.links.new(gl.outputs['Image'], comp.inputs['Image'])
if PASSES:
    # one 16-bit PNG, stored linear: R plants, G the mark, B depth / 400 m
    fo = ct.nodes.new('CompositorNodeOutputFile'); fo.base_path = os.path.dirname(PASSES)
    fo.format.file_format = 'PNG'; fo.format.color_depth = '16'; fo.format.color_mode = 'RGB'
    fo.format.color_management = 'OVERRIDE'; fo.format.view_settings.view_transform = 'Standard'
    fo.format.view_settings.look = 'None'; fo.format.view_settings.exposure = 0; fo.format.view_settings.gamma = 1
    fo.file_slots.clear(); fo.file_slots.new('passes')
    cc = ct.nodes.new('CompositorNodeCombineColor'); cc.mode = 'RGB'
    def clamp01(sock, scale=1.0):
        n1 = ct.nodes.new('CompositorNodeMath'); n1.operation = 'MULTIPLY'; n1.inputs[1].default_value = scale; ct.links.new(sock, n1.inputs[0])
        n2 = ct.nodes.new('CompositorNodeMath'); n2.operation = 'MINIMUM'; n2.inputs[1].default_value = 1.0; ct.links.new(n1.outputs[0], n2.inputs[0])
        return n2.outputs[0]
    ct.links.new(clamp01(rl.outputs['gm']), cc.inputs['Red']); ct.links.new(clamp01(rl.outputs['mk']), cc.inputs['Green'])
    ct.links.new(clamp01(rl.outputs['Depth'], 1 / 400.0), cc.inputs['Blue'])
    ct.links.new(cc.outputs['Image'], fo.inputs[0])
    sc.frame_current = 1

if '--dry' in argv:
    exec(open(arg('chk', '/dev/null')).read()); print('DRY_OK'); sys.exit(0)
t0 = time.time()
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('RENDER_SECONDS', round(time.time() - t0, 1))
if PASSES:
    cand = os.path.join(os.path.dirname(PASSES), 'passes0001.png')
    if os.path.exists(cand): os.replace(cand, PASSES)
