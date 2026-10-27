# The Garden in the Ruin: a vast old stone hall, its roof broken open; one shaft of warm daylight
# falls through dust onto flowers growing through the cracked floor, where the Antimony stone stands.
# Blender 4.5 LTS, Cycles CPU. Every surface and plant from CC0 scans (Poly Haven, ambientCG; see credits.txt).
#
# Run:  blender -b -P garden_scene.py -- --ph <assets/polyhaven> --acg <assets/ambientcg> --out <file.png>
#   --res 1600x900  --samples 256  --time 420 (seconds; 0 means no limit)
import bpy, bmesh, math, json, os, re, sys, time
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    k = '--' + name
    return type(default)(argv[argv.index(k) + 1]) if k in argv else default

PH = arg('ph', '')
ACG = arg('acg', '')
OUT = arg('out', '/tmp/garden.png')
RES = arg('res', '640x360')
SAMPLES = arg('samples', 32)
TIME = arg('time', 0.0)
EXPO = arg('exposure', 0.55)
DENS = arg('density', 1.0)
HERE = os.path.dirname(os.path.abspath(__file__))
GEO = json.load(open(arg('geometry', os.path.join(HERE, 'break-geometry.json'))))
rng = np.random.default_rng(11)

# ---------------------------------------------------------------- scene and render
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
W, H = (int(v) for v in RES.split('x'))
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.resolution_percentage = 100
sc.render.engine = 'CYCLES'
cy = sc.cycles
cy.device = 'CPU'
cy.samples = SAMPLES
cy.use_adaptive_sampling = True
cy.adaptive_threshold = arg('noise', 0.03)
cy.time_limit = TIME
cy.use_denoising = True
cy.denoiser = 'OPENIMAGEDENOISE'
cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
cy.max_bounces = 8; cy.diffuse_bounces = 3; cy.glossy_bounces = 2
cy.transmission_bounces = 6; cy.transparent_max_bounces = 12; cy.volume_bounces = 0
cy.caustics_reflective = False; cy.caustics_refractive = False
cy.blur_glossy = 1.0
cy.sample_clamp_indirect = 6.0
cy.use_light_tree = True
cy.volume_step_rate = 4.0
sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = arg('look', 'AgX - Medium High Contrast')
sc.view_settings.exposure = EXPO
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_depth = '8'
sc.render.image_settings.color_mode = 'RGB'
vl = sc.view_layers[0]
_a = vl.aovs.add(); _a.name = 'wt'; _a.type = 'VALUE'

# ---------------------------------------------------------------- helpers
def mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    return m, nt

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

def math_n(nt, op, a, b=None, loc=(0, 0)):
    n_ = node(nt, 'ShaderNodeMath', loc, operation=op)
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n_.inputs[i].default_value = v
        else: link(nt, v, n_.inputs[i])
    return n_.outputs[0]

def maprange(nt, sock, a, b, c=0.0, d=1.0, loc=(0, 0)):
    n_ = node(nt, 'ShaderNodeMapRange', loc); n_.clamp = True
    n_.inputs['From Min'].default_value = a; n_.inputs['From Max'].default_value = b
    n_.inputs['To Min'].default_value = c; n_.inputs['To Max'].default_value = d
    link(nt, sock, n_.inputs['Value']); return n_.outputs['Result']

def mixrgb(nt, fac, a, b, blend='MIX', loc=(0, 0)):
    m_ = node(nt, 'ShaderNodeMix', loc); m_.data_type = 'RGBA'; m_.blend_type = blend; m_.clamp_result = True
    sid = lambda col, ident: next(x for x in col if x.identifier == ident)
    for sock, v in ((sid(m_.inputs, 'Factor_Float'), fac), (sid(m_.inputs, 'A_Color'), a), (sid(m_.inputs, 'B_Color'), b)):
        if isinstance(v, (int, float)): sock.default_value = v
        elif isinstance(v, tuple): sock.default_value = v
        else: link(nt, v, sock)
    return sid(m_.outputs, 'Result_Color')

def link_obj(ob, coll=None):
    (coll or sc.collection).objects.link(ob); return ob

def box(name, x0, x1, y0, y1, z0, z1, m=None, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 if v.co.x < 0 else x1
        v.co.y = y0 if v.co.y < 0 else y1
        v.co.z = z0 if v.co.z < 0 else z1
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = link_obj(bpy.data.objects.new(name, me))
    if m: me.materials.append(m)
    if bevel:
        b = ob.modifiers.new('bv', 'BEVEL'); b.width = bevel; b.segments = 3; b.limit_method = 'ANGLE'
    return ob

def cyl(name, r, z0, z1, x=0, y=0, n=48, axis='Z', m=None, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=n, radius1=r, radius2=r, depth=z1 - z0)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = len(p.vertices) == 4
    ob = link_obj(bpy.data.objects.new(name, me))
    if axis == 'Z': ob.location = (x, y, (z0 + z1) / 2)
    if m: me.materials.append(m)
    if bevel:
        b = ob.modifiers.new('bv', 'BEVEL'); b.width = bevel; b.segments = 3; b.limit_method = 'ANGLE'; b.angle_limit = math.radians(50)
    return ob

def cut(target, cutters):
    coll = bpy.data.collections.new(target.name + '_cut')
    for c in cutters:
        coll.objects.link(c); c.hide_render = True; c.display_type = 'WIRE'
    md = target.modifiers.new('cut', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'
    md.operand_type = 'COLLECTION'; md.collection = coll
    target.modifiers.move(len(target.modifiers) - 1, 0)
    return md

def srgb2lin(c): return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92
SKY = [srgb2lin(v / 255) for v in (0x94, 0xE6, 0xFF)]

# ---------------------------------------------------------------- the light: real sky, a warm low-afternoon sun
wld = bpy.data.worlds.new('sky'); sc.world = wld; wld.use_nodes = True
wn = wld.node_tree; wn.nodes.clear()
tc = node(wn, 'ShaderNodeTexCoord', (-800, 0)); mp = node(wn, 'ShaderNodeMapping', (-600, 0))
mp.inputs['Rotation'].default_value = (0, 0, math.radians(arg('sky-rot', 140.0)))
env = node(wn, 'ShaderNodeTexEnvironment', (-400, 0))
env.image = img(os.path.join(PH, 'kloppenheim_06_puresky', 'kloppenheim_06_puresky_2k.hdr'))
bg = node(wn, 'ShaderNodeBackground', (-150, 0)); bg.inputs['Strength'].default_value = arg('sky', 0.65)
link(wn, tc.outputs['Generated'], mp.inputs['Vector']); link(wn, mp.outputs['Vector'], env.inputs['Vector'])
link(wn, env.outputs['Color'], bg.inputs['Color'])
wo = node(wn, 'ShaderNodeOutputWorld', (100, 0)); link(wn, bg.outputs['Background'], wo.inputs['Surface'])
wld.cycles.sampling_method = 'MANUAL'; wld.cycles.sample_map_resolution = 1024

# sun travels down steeply, a little to the right and away from the camera, so it lights the stone's face from above
SUN_D = Vector((arg('sun-x', 0.2), arg('sun-y', 0.2), -0.94)).normalized()
sun_d = bpy.data.lights.new('sun', 'SUN'); sun_d.energy = arg('sun', 28.0); sun_d.angle = math.radians(arg('sun-angle', 0.9))
sun_d.color = (1.0, 0.80, 0.58)
sun = link_obj(bpy.data.objects.new('sun', sun_d))
sun.rotation_euler = SUN_D.to_track_quat('-Z', 'Y').to_euler()

# ---------------------------------------------------------------- the stone: geometry from break-geometry.json
S = arg('scale', 0.026)        # 100 units = 2.6 m: a monolith you stand beside
T = arg('thick', 0.55)
MARK_X, MARK_Y = arg('mx', 2.6), arg('my', 10.5)
BLOCK = (arg('bx', 0.55), arg('by', 9.3))
MARK_YAW = math.radians(arg('yaw', -14.0))

# the shared stone (directions/stone/stone.py): exact Break geometry, honed scanned basalt, softened and
# chipped arrises, faint drove marks, lichen at the foot, the crystal as true sky glass
sys.path.insert(0, arg('stone-dir', os.path.join(os.path.dirname(HERE), 'stone')))
import stone
# hand-carved and old: chipped, worn arrises, chisel tooling in patches with a drafted margin, pick marks in the
# seam, damp wicked up at the foot. Nothing grows on the mark (growth=False): growth stays on the ground around it.
STONE = stone.build_stone(sc.collection, scale_m=S * 100, location=(MARK_X, MARK_Y, 0.0),
                          rotation=(0.01, -0.006, MARK_YAW), wetness=0.0, moss=0.0, growth=False,
                          cache_dir=os.path.dirname(PH.rstrip('/')), stone_value=arg('st-val', 0.68),
                          glow=arg('cr-glow', 0.0), caustics=bool(arg('caustics', 0)), detail=arg('detail', 340),
                          chips=arg('chips', 1.6), chip_size=arg('chip-size', 1.9), chip_dots=0.0,
                          bevel=arg('st-bevel', 0.012), erosion=arg('erosion', 1.4),
                          tool_marks=arg('tool', 0.3), carve=arg('carve', 0.8), damp_foot=arg('damp', 1.0))
T = STONE['info']['T']
crystal = STONE['crystal']
# the crystal as real, clear glass with only a faint body tint: its sky colour comes from the light it transmits
# (held by absorption), never from a glow of its own
cm_ = crystal.active_material; cnt = cm_.node_tree
cb_ = next(n_ for n_ in cnt.nodes if n_.bl_idname == 'ShaderNodeBsdfPrincipled')
cout = next(n_ for n_ in cnt.nodes if n_.bl_idname == 'ShaderNodeOutputMaterial')
body = node(cnt, 'ShaderNodeBsdfPrincipled', (0, 600))
# pre-balanced against the warm sun, so the lit crystal lands on #94E6FF and never drifts to teal
body.inputs['Base Color'].default_value = (arg('cb-r', 0.16), arg('cb-g', 0.55), 1.0, 1); body.inputs['Roughness'].default_value = 0.25
body.inputs['Subsurface Weight'].default_value = 1.0; body.inputs['Subsurface Radius'].default_value = (0.03, 0.06, 0.09)
body.inputs['Coat Weight'].default_value = 1.0; body.inputs['Coat Roughness'].default_value = 0.02
cmix = node(cnt, 'ShaderNodeMixShader', (350, 300)); cmix.inputs['Fac'].default_value = arg('cr-body', 0.14)
for n_ in cnt.nodes:                      # denser sky absorption, so what the glass transmits lands nearer #94E6FF
    if n_.bl_idname == 'ShaderNodeVolumeAbsorption':
        n_.inputs['Density'].default_value *= arg('cr-abs', 2.1)
link(cnt, cb_.outputs['BSDF'], cmix.inputs[1]); link(cnt, body.outputs['BSDF'], cmix.inputs[2])
link(cnt, cmix.outputs['Shader'], cout.inputs['Surface'])

# what the crystal refracts: through the cavity it would see the stone's own shadowed bed, so, as in any gem
# photograph, a soft card stands behind it, seen only through the glass (invisible to the lens, lights nothing)
if arg('cr-card', 1):
    nb_ = (STONE['root'].matrix_world.to_3x3() @ Vector((0, 1, 0))).normalized()
    cc0 = Vector(STONE['info']['crystal_centre'])
    bpy.ops.mesh.primitive_plane_add(size=1); card = bpy.context.object; card.name = 'crystal_card'
    card.scale = (1.8, 1.8, 1); card.location = cc0 + nb_ * arg('card-d', 0.9)
    card.rotation_euler = (-nb_).to_track_quat('Z', 'Y').to_euler()
    mcd, ntc = mat('crystal_card')
    tcc = node(ntc, 'ShaderNodeTexCoord', (-800, 0))
    nzc = node(ntc, 'ShaderNodeTexNoise', (-600, 0)); nzc.inputs['Scale'].default_value = 2.2; nzc.inputs['Detail'].default_value = 3
    link(ntc, tcc.outputs['Object'], nzc.inputs['Vector'])
    gr_ = node(ntc, 'ShaderNodeSeparateXYZ', (-600, -200)); link(ntc, tcc.outputs['Object'], gr_.inputs['Vector'])
    # brighter high up (the sky's side), with soft broken variation so the facets differ
    sv = math_n(ntc, 'MULTIPLY', maprange(ntc, gr_.outputs['Y'], -0.5, 0.5, 0.35, 1.0), maprange(ntc, nzc.outputs['Fac'], 0.3, 0.7, 0.45, 1.1))
    emc = node(ntc, 'ShaderNodeEmission', (-100, 0)); emc.inputs['Color'].default_value = (1.0, 0.98, 0.95, 1)
    link(ntc, math_n(ntc, 'MULTIPLY', sv, arg('card', 1.9)), emc.inputs['Strength'])
    oc_ = node(ntc, 'ShaderNodeOutputMaterial', (200, 0)); link(ntc, emc.outputs['Emission'], oc_.inputs['Surface'])
    card.data.materials.append(mcd)
    card.visible_camera = False; card.visible_diffuse = False; card.visible_glossy = False
    card.visible_shadow = False; card.visible_volume_scatter = False; card.visible_transmission = True

# ---------------------------------------------------------------- the floor plan: masks for the garden bed and the water
# one map over the hall floor (x -12..12, y -12..42): R garden bed, G still water
FX0, FX1, FY0, FY1 = -12.0, 12.0, -12.0, 42.0
MW, MH = 480, 1080
gx = np.linspace(FX0, FX1, MW); gy = np.linspace(FY0, FY1, MH)
XX, YY = np.meshgrid(gx, gy)
def fbm(x, y, seed, oct_=5, f0=0.35):
    r_ = np.random.default_rng(seed); v = np.zeros_like(x); amp = 1.0; f = f0; tot = 0
    for _ in range(oct_):
        for _k in range(3):
            a = r_.uniform(0, math.pi); ph = r_.uniform(0, 6.28)
            v += amp * np.sin((x * math.cos(a) + y * math.sin(a)) * f + ph)
            tot += amp
        amp *= 0.55; f *= 2.1
    return v / tot * 2.2
BED_C = (MARK_X - 0.3, MARK_Y + 0.3)
POOL = (MARK_X - arg('pool-dx', 1.0), MARK_Y - arg('pool-dy', 0.45))   # where the shaft lands
def bed_field(x, y):
    d = np.hypot((x - BED_C[0]) / 1.0, (y - BED_C[1]) / 0.8)
    return 3.4 - d + 0.9 * fbm(x, y, 3)          # > 0 inside the bed
def water_field(x, y):
    d = np.hypot((x - 0.9) / 1.5, (y - 6.4) / 0.75)
    return 2.5 - d + 0.6 * fbm(x, y, 5)
BED = np.clip(bed_field(XX, YY) / 0.25, 0, 1)
WAT = np.clip(water_field(XX, YY) / 0.12, 0, 1) * (1 - BED)
mimg = bpy.data.images.new('floormask', MW, MH, alpha=False, float_buffer=True)
mimg.colorspace_settings.name = 'Non-Color'
px = np.ones((MH, MW, 4), np.float32); px[..., 0] = BED; px[..., 1] = WAT; px[..., 2] = 0
mimg.pixels.foreach_set(px.ravel())

def floor_uv(nt):
    # world xy to the mask's 0..1 space
    gm = node(nt, 'ShaderNodeNewGeometry', (-1600, -900))
    mpx = node(nt, 'ShaderNodeMapping', (-1400, -900))
    mpx.inputs['Location'].default_value = (-FX0 / (FX1 - FX0), -FY0 / (FY1 - FY0), 0)
    mpx.inputs['Scale'].default_value = (1 / (FX1 - FX0), 1 / (FY1 - FY0), 1)
    link(nt, gm.outputs['Position'], mpx.inputs['Vector'])
    t = node(nt, 'ShaderNodeTexImage', (-1200, -900)); t.image = mimg; t.extension = 'EXTEND'; t.interpolation = 'Cubic'
    link(nt, mpx.outputs['Vector'], t.inputs['Vector'])
    sp = node(nt, 'ShaderNodeSeparateColor', (-1000, -900)); link(nt, t.outputs['Color'], sp.inputs['Color'])
    return sp

# ---------------------------------------------------------------- architecture stone: scanned ashlar, cooled; moss on ledges, damp streaks
def arch_mat(name, tex_dir, prefix, size=3.0, val=0.75, sat=0.35, moss=0.6, streak=0.5, coords='Object'):
    m, nt = mat(name)
    tco = node(nt, 'ShaderNodeTexCoord', (-1600, 0))
    mpp = node(nt, 'ShaderNodeMapping', (-1400, 0)); s_ = 1.0 / size
    mpp.inputs['Scale'].default_value = (s_, s_, s_)
    link(nt, tco.outputs[coords], mpp.inputs['Vector'])
    def bt(suffix, nc, loc):
        t = node(nt, 'ShaderNodeTexImage', loc); t.image = img(os.path.join(tex_dir, prefix + suffix), nc)
        t.projection = 'BOX'; t.projection_blend = 0.15
        link(nt, mpp.outputs['Vector'], t.inputs['Vector']); return t.outputs['Color']
    col = bt('_diff_2k.jpg', False, (-1100, 400)); rgh = bt('_rough_2k.jpg', True, (-1100, 100))
    hgt = bt('_disp_2k.jpg', True, (-1100, -200)); ao = bt('_ao_2k.jpg', True, (-1100, -500))
    hsv = node(nt, 'ShaderNodeHueSaturation', (-800, 400)); hsv.inputs['Saturation'].default_value = sat
    hsv.inputs['Value'].default_value = val; link(nt, col, hsv.inputs['Color'])
    # a cool grey tint so the stone sits in the hall's blue shadow and warms only where the sun lands
    c1 = mixrgb(nt, 0.35, hsv.outputs['Color'], (0.30, 0.32, 0.35, 1), 'MULTIPLY')
    c1 = mixrgb(nt, 1.0, hsv.outputs['Color'], c1)
    gpos = node(nt, 'ShaderNodeNewGeometry', (-1400, -900))
    # damp streaks running down the faces
    sm = node(nt, 'ShaderNodeMapping', (-1200, -1100)); sm.inputs['Scale'].default_value = (2.2, 2.2, 0.18)
    link(nt, gpos.outputs['Position'], sm.inputs['Vector'])
    nzs = node(nt, 'ShaderNodeTexNoise', (-1000, -1100)); nzs.inputs['Scale'].default_value = 1.3; nzs.inputs['Detail'].default_value = 5
    link(nt, sm.outputs['Vector'], nzs.inputs['Vector'])
    stk = math_n(nt, 'MULTIPLY', maprange(nt, nzs.outputs['Fac'], 0.5, 0.75), streak)
    c2 = mixrgb(nt, stk, c1, (0.05, 0.055, 0.05, 1), 'MULTIPLY')
    c2 = mixrgb(nt, math_n(nt, 'MULTIPLY', stk, 0.6), c1, c2)
    # moss: on upward faces, in the crevices (low AO) and near the floor, broken up by noise
    sepn = node(nt, 'ShaderNodeSeparateXYZ', (-1200, -1400)); link(nt, gpos.outputs['Normal'], sepn.inputs['Vector'])
    sepp = node(nt, 'ShaderNodeSeparateXYZ', (-1200, -1600)); link(nt, gpos.outputs['Position'], sepp.inputs['Vector'])
    up = maprange(nt, sepn.outputs['Z'], 0.35, 0.8)
    low = maprange(nt, sepp.outputs['Z'], 1.4, 0.0)
    crev = maprange(nt, ao, 0.75, 0.35)
    nzm = node(nt, 'ShaderNodeTexNoise', (-1000, -1500)); nzm.inputs['Scale'].default_value = 0.9; nzm.inputs['Detail'].default_value = 8
    nzm.inputs['Roughness'].default_value = 0.65
    link(nt, gpos.outputs['Position'], nzm.inputs['Vector'])
    brk = maprange(nt, nzm.outputs['Fac'], 0.45, 0.62)
    mm = math_n(nt, 'MAXIMUM', math_n(nt, 'MAXIMUM', up, low), math_n(nt, 'MULTIPLY', crev, 0.7))
    mm = math_n(nt, 'MULTIPLY', math_n(nt, 'MULTIPLY', mm, brk), moss)
    mt = os.path.join(ACG, 'Moss002', 'Moss002_2K-JPG_Color.jpg')
    tm = node(nt, 'ShaderNodeTexImage', (-1100, -1800)); tm.image = img(mt); tm.projection = 'BOX'; tm.projection_blend = 0.3
    mpm = node(nt, 'ShaderNodeMapping', (-1300, -1800)); mpm.inputs['Scale'].default_value = (0.8, 0.8, 0.8)
    link(nt, tco.outputs[coords], mpm.inputs['Vector']); link(nt, mpm.outputs['Vector'], tm.inputs['Vector'])
    mhs = node(nt, 'ShaderNodeHueSaturation', (-800, -1800)); mhs.inputs['Value'].default_value = 0.7; mhs.inputs['Saturation'].default_value = 0.85
    link(nt, tm.outputs['Color'], mhs.inputs['Color'])
    c3 = mixrgb(nt, mm, c2, mhs.outputs['Color'])
    rr = maprange(nt, rgh, 0.0, 1.0, 0.55, 0.95)
    rr = math_n(nt, 'MAXIMUM', rr, math_n(nt, 'MULTIPLY', mm, 0.95))
    bmp = node(nt, 'ShaderNodeBump', (-300, -400)); bmp.inputs['Strength'].default_value = 0.6; bmp.inputs['Distance'].default_value = 0.03
    link(nt, hgt, bmp.inputs['Height'])
    bvn = node(nt, 'ShaderNodeBevel', (-100, -400)); bvn.samples = 4; bvn.inputs['Radius'].default_value = 0.03
    link(nt, bmp.outputs['Normal'], bvn.inputs['Normal'])
    bsd = node(nt, 'ShaderNodeBsdfPrincipled', (200, 0)); bsd.inputs['Specular IOR Level'].default_value = 0.35
    link(nt, c3, bsd.inputs['Base Color']); link(nt, rr, bsd.inputs['Roughness']); link(nt, bvn.outputs['Normal'], bsd.inputs['Normal'])
    o = node(nt, 'ShaderNodeOutputMaterial', (500, 0)); link(nt, bsd.outputs['BSDF'], o.inputs['Surface'])
    return m

d_blk = os.path.join(PH, 'large_sandstone_blocks', 'textures')
d_pl = os.path.join(PH, 'worn_mossy_plasterwall', 'textures')
M_ASHLAR = arch_mat('ashlar', d_blk, 'large_sandstone_blocks', 3.0, arg('wall-val', 1.2), 0.3, 0.55, coords='Generated' if False else 'Object')
M_PLASTER = arch_mat('plaster', d_pl, 'worn_mossy_plasterwall', 1.8, arg('plaster-val', 0.55), 0.3, 0.35, 0.7)
M_COLUMN = arch_mat('column', d_blk, 'large_sandstone_blocks', 2.4, arg('wall-val', 1.2) * 1.05, 0.25, 0.7)

# ---------------------------------------------------------------- the hall: kept simple and big
NAVE = 5.5                 # column lines at x = +-5.5
COL_Y = [-10, -4, 2, 8, 14, 20, 26, 32, 38]
Z_CAP = 9.8; Z_ROOF = 22.0; Z_AISLE = 12.0
cols_objs = []
for side in (-1, 1):
    x = side * NAVE
    for y in COL_Y:
        parts = [box(f'plinth_{side}_{y}', x - 0.95, x + 0.95, y - 0.95, y + 0.95, 0, 0.38, M_COLUMN, 0.035),
                 cyl(f'torus_{side}_{y}', 0.92, 0.38, 0.6, x, y, 48, m=M_COLUMN, bevel=0.06),
                 cyl(f'shaft_{side}_{y}', 0.74, 0.6, 9.2, x, y, 64, m=M_COLUMN, bevel=0.03),
                 cyl(f'neck_{side}_{y}', 0.9, 9.2, 9.42, x, y, 48, m=M_COLUMN, bevel=0.06),
                 box(f'abacus_{side}_{y}', x - 1.0, x + 1.0, y - 1.0, y + 1.0, 9.42, Z_CAP, M_COLUMN, 0.035)]
        cols_objs.append(parts)

# the arcades: a wall over the columns with round arches between them, and arched clerestory windows above
mids = [(a + b) / 2 for a, b in zip(COL_Y[:-1], COL_Y[1:])]
for side in (-1, 1):
    x = side * NAVE
    wall = box(f'arcade_{side}', x - 0.7, x + 0.7, -12, 41, Z_CAP, Z_ROOF, M_ASHLAR)
    cutters = []
    for ym in mids:
        c = cyl('arch', 2.05, -1.5, 1.5, n=64); c.rotation_euler = (0, math.pi / 2, 0); c.location = (x, ym, Z_CAP)
        cutters.append(c)
        if side < 0: continue      # the sun side is blind, so the only sun in the hall is the shaft
        cutters.append(box('cl', x - 1.5, x + 1.5, ym - 0.85, ym + 0.85, 13.6, 17.4))
        c2 = cyl('cla', 0.85, -1.5, 1.5, n=40); c2.rotation_euler = (0, math.pi / 2, 0); c2.location = (x, ym, 17.4)
        cutters.append(c2)
    cut(wall, cutters)
    # the aisle: an outer wall with tall arched windows, under a lower roof
    xo = side * 12.0
    ow = box(f'outer_{side}', min(xo, xo + side * 1.2), max(xo, xo + side * 1.2), -12, 41, 0, Z_AISLE + 0.8, M_ASHLAR)
    oc = []
    for ym in mids:
        oc.append(box('w', xo - 2, xo + 2, ym - 1.05, ym + 1.05, 2.4, 8.2))
        c3 = cyl('wa', 1.05, -2, 2, n=48); c3.rotation_euler = (0, math.pi / 2, 0); c3.location = (xo, ym, 8.2); oc.append(c3)
    cut(ow, oc)
    box(f'aisleroof_{side}', min(side * 6.2, xo), max(side * 6.2, xo), -12, 41, Z_AISLE, Z_AISLE + 0.8, M_PLASTER)

# the far wall with one great arched window; a plain wall behind the camera
far = box('far', -13.2, 13.2, 41, 42.4, 0, Z_ROOF + 1.2, M_ASHLAR)
FWW = arg('far-win', 2.2)
FWS = arg('far-sill', 0.45)      # the great window has lost its sill and glazing: an open arch into the next hall
fc = [box('fw', -FWW, FWW, 40, 43.4, FWS, 13.5)]
c4 = cyl('fwa', FWW, -1.5, 1.5, n=64); c4.rotation_euler = (math.pi / 2, 0, 0); c4.location = (0, 41.7, 13.5); fc.append(c4)
# a smaller window high in each aisle bay of the far wall
for xs in (-9.0, 9.0):
    fc.append(box('fs', xs - 1.0, xs + 1.0, 40, 43.4, 3.0, 8.5))
    c5 = cyl('fsa', 1.0, -1.5, 1.5, n=40); c5.rotation_euler = (math.pi / 2, 0, 0); c5.location = (xs, 41.7, 8.5); fc.append(c5)
cut(far, fc)
# mullions in the great window
# a fallen mullion lies across the threshold
mb_ = box('mullion_fallen', -0.1, 0.1, -2.6, 2.6, -0.1, 0.1, M_ASHLAR, 0.02)
mb_.location = (0.9, 43.6, 0.12); mb_.rotation_euler = (0.0, 0.0, 1.2)
box('back', -13.2, 13.2, -13.4, -12.0, 0, Z_ROOF + 1.2, M_ASHLAR)

# ---------------------------------------------------------------- beyond the far window: a second hall, roofless and sunlit,
# its arcade broken down towards a far gable with a great open arch; past it, ridges (scanned cliffs) in layered haze
SH = arg('hall2', 1)
if SH:
    rs_ = np.random.default_rng(21)
    X2 = 2.7
    Y2 = [47.0, 53.0, 59.0, 65.0, 71.0, 77.0, 83.0, 89.0]
    for side in (-1, 1):
        for i, y in enumerate(Y2):
            full = (i < 4) if side < 0 else (i < 2)
            ztop = 8.0 if full else float(rs_.uniform(2.5, 6.5))
            if not full and rs_.uniform() < 0.25: continue          # a few have fallen entirely
            x = side * X2
            box(f'p2_{side}_{i}', x - 0.62, x + 0.62, y - 0.62, y + 0.62, 0, 0.3, M_COLUMN, 0.03)
            sh_ = cyl(f's2_{side}_{i}', 0.48, 0.3, ztop, x, y, 40, m=M_COLUMN, bevel=0.02)
            if full:
                box(f'a2_{side}_{i}', x - 0.66, x + 0.66, y - 0.66, y + 0.66, ztop, ztop + 0.45, M_COLUMN, 0.03)
            else:
                sh_.rotation_euler = (float(rs_.normal(0, 0.03)), float(rs_.normal(0, 0.03)), 0)
        # the arcade wall stands over the first bays only, its top broken
        if side > 0: continue
        nb_ = 2
        w2 = box(f'arc2_{side}', side * X2 - 0.5, side * X2 + 0.5, Y2[0] - 0.7, Y2[nb_] + 0.7, 8.45, 13.6, M_ASHLAR)
        cs_ = []
        for a_, b_ in zip(Y2[:nb_], Y2[1:nb_ + 1]):
            c_ = cyl('arch2', 2.45, -1.5, 1.5, n=56); c_.rotation_euler = (0, math.pi / 2, 0); c_.location = (side * X2, (a_ + b_) / 2, 8.45)
            cs_.append(c_)
        # a stepped break where the courses have fallen away
        for k_ in range(3):
            cs_.append(box('brk2', side * X2 - 1, side * X2 + 1, Y2[nb_] + 0.7 - 1.3 * (k_ + 1), Y2[nb_] + 1.0, 13.6 - 1.4 * (k_ + 1), 14.0))
        cut(w2, cs_)
    # the far gable: a great arch open to the country beyond, its top broken
    g2 = box('gable2', -12, 12, 95.0, 96.6, 0, 17.0, M_ASHLAR)
    ga = cyl('g2a', 3.4, -2, 2, n=64); ga.rotation_euler = (math.pi / 2, 0, 0); ga.location = (0.4, 95.8, 9.0)
    gb = box('g2b', -3.0, 3.8, 94, 97.6, 0, 9.0)
    # its top fallen in steps, lower to the right
    brk_ = [box('g2t', x0_, 13, 94, 97.6, z0_, 18) for x0_, z0_ in ((-1.5, 15.2), (3.5, 13.4), (7.5, 11.0))]
    brk_ += [box('g2t', -13, x1_, 94, 97.6, z0_, 18) for x1_, z0_ in ((-6.0, 16.0), (-9.5, 14.6))]
    cut(g2, [ga, gb] + brk_)
    # floor of the second hall (unseen but it bounces the sun up into the haze and the arcade)
    box('floor2', -14, 14, 42.4, 97, -0.2, 0.0, M_ASHLAR)
    # its air: thicker than the nave's and lit by the open sky, so it falls back in layers
    def _hz(name, x0, x1, y0, y1, z0, z1, dens, col, aniso=0.3):
        ob_ = box(name, x0, x1, y0, y1, z0, z1)
        m_, nt_ = mat(name)
        pv_ = node(nt_, 'ShaderNodeVolumePrincipled', (0, 0)); pv_.inputs['Density'].default_value = dens
        pv_.inputs['Anisotropy'].default_value = aniso; pv_.inputs['Color'].default_value = (*col, 1)
        o_ = node(nt_, 'ShaderNodeOutputMaterial', (300, 0)); link(nt_, pv_.outputs['Volume'], o_.inputs['Volume'])
        link(nt_, node(nt_, 'ShaderNodeBsdfTransparent', (0, 200)).outputs['BSDF'], o_.inputs['Surface'])
        ob_.data.materials.append(m_); return ob_
    _hz('haze_hall2', -12, 12, 42.4, 95.0, -0.2, 26.0, arg('haze2', 0.0015), (0.93, 0.96, 1.0))


# the nave roof (plaster vault soffit), broken open where the sun comes in
roof = box('roof', -NAVE - 0.7, NAVE + 0.7, -12, 41, Z_ROOF, Z_ROOF + 1.2, M_PLASTER)
t_hit = (Z_ROOF + 0.6) / -SUN_D.z
HOLE = (POOL[0] + SUN_D.x * -t_hit, POOL[1] + SUN_D.y * -t_hit)
def ragged(name, cx_, cy_, r, z0, z1, rough=0.35, seed=1):
    r_ = np.random.default_rng(seed)
    bm = bmesh.new(); n = 40
    ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
    rad = r * (1 + rough * (0.6 * np.sin(ang * 3 + r_.uniform(0, 6)) + 0.4 * np.sin(ang * 7 + r_.uniform(0, 6)) + 0.5 * r_.uniform(-1, 1, n)))
    lo = [bm.verts.new((cx_ + rd * math.cos(a), cy_ + rd * math.sin(a), z0)) for a, rd in zip(ang, rad)]
    hi = [bm.verts.new((cx_ + rd * 1.15 * math.cos(a), cy_ + rd * 1.15 * math.sin(a), z1)) for a, rd in zip(ang, rad)]
    bm.faces.new(lo[::-1]); bm.faces.new(hi)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return link_obj(bpy.data.objects.new(name, me))
cut(roof, [ragged('hole', HOLE[0], HOLE[1], arg('hole', 1.7), Z_ROOF - 1, Z_ROOF + 2.5, 0.25, 4),
           ragged('hole2', arg('far-break-x', 1.5), arg('far-break-y', 36.0), arg('far-break', 2.4), Z_ROOF - 1, Z_ROOF + 2.5, 0.45, 9)])
# broken roof slabs hang from the far break's edge
for i, (hx, hy, rx_, ry_) in enumerate(((-1.6, 33.4, 0.5, -0.3), (4.2, 34.6, -0.4, 0.6))):
    hb = box(f'hang{i}', -0.9, 0.9, -0.5, 0.5, -0.25, 0.25, M_PLASTER, 0.03)
    hb.location = (hx, hy, Z_ROOF - 0.3); hb.rotation_euler = (rx_, ry_, 0.3 * i)

# the floor: scanned flagstones (Poly Haven large_floor_tiles_02, 1 m slabs), the garden bed where they have gone,
# and a shallow sheet of still water
bpy.ops.mesh.primitive_plane_add(size=1); flo = bpy.context.object; flo.name = 'floor'
flo.scale = (FX1 - FX0, FY1 - FY0, 1); flo.location = ((FX0 + FX1) / 2, (FY0 + FY1) / 2, 0)
bpy.ops.object.transform_apply(scale=True)
m_f, nt = mat('floor')
gm = node(nt, 'ShaderNodeNewGeometry', (-1800, 0))
mpf = node(nt, 'ShaderNodeMapping', (-1600, 0)); mpf.inputs['Scale'].default_value = (1 / 3, 1 / 3, 1)
link(nt, gm.outputs['Position'], mpf.inputs['Vector'])
fd = os.path.join(PH, 'large_floor_tiles_02', 'textures', 'large_floor_tiles_02')
def ft(suffix, nc, loc, vec=None):
    t = node(nt, 'ShaderNodeTexImage', loc); t.image = img(fd + suffix, nc)
    link(nt, vec or mpf.outputs['Vector'], t.inputs['Vector']); return t.outputs['Color']
f_col = ft('_diff_2k.jpg', False, (-1300, 500)); f_rgh = ft('_rough_2k.jpg', True, (-1300, 200))
f_dsp = ft('_disp_2k.jpg', True, (-1300, -100)); f_ao = ft('_ao_2k.jpg', True, (-1300, -400))
msk = floor_uv(nt)
# variation: big soft patches of dirt and wear so the 3 m repeat never shows
nzf = node(nt, 'ShaderNodeTexNoise', (-1300, 800)); nzf.inputs['Scale'].default_value = 0.12; nzf.inputs['Detail'].default_value = 6
link(nt, gm.outputs['Position'], nzf.inputs['Vector'])
vfac = maprange(nt, nzf.outputs['Fac'], 0.35, 0.7, 0.55, 1.0)
fcol = mixrgb(nt, 1.0, f_col, (0.86, 0.88, 0.92, 1), 'MULTIPLY')
fcol = mixrgb(nt, maprange(nt, vfac, 0.55, 1.0, 1.0, 0.0), fcol, (0.12, 0.12, 0.11, 1), 'MULTIPLY')
# moss in the joints (low AO), stronger near the garden and the water
near_g = maprange(nt, math_n(nt, 'ADD', msk.outputs['Red'], math_n(nt, 'MULTIPLY', msk.outputs['Green'], 0.6)), 0.0, 0.05, 0.25, 1.0)
blur_bed = node(nt, 'ShaderNodeTexNoise', (-1300, 1000)); blur_bed.inputs['Scale'].default_value = 0.6; blur_bed.inputs['Detail'].default_value = 7
link(nt, gm.outputs['Position'], blur_bed.inputs['Vector'])
joint = maprange(nt, f_ao, 0.82, 0.55)
mossj = math_n(nt, 'MULTIPLY', joint, math_n(nt, 'MULTIPLY', maprange(nt, blur_bed.outputs['Fac'], 0.4, 0.6), near_g))
tmo = node(nt, 'ShaderNodeTexImage', (-1300, -800)); tmo.image = img(os.path.join(ACG, 'Moss002', 'Moss002_2K-JPG_Color.jpg'))
mpm = node(nt, 'ShaderNodeMapping', (-1500, -800)); mpm.inputs['Scale'].default_value = (0.9, 0.9, 1)
link(nt, gm.outputs['Position'], mpm.inputs['Vector']); link(nt, mpm.outputs['Vector'], tmo.inputs['Vector'])
fcol = mixrgb(nt, mossj, fcol, tmo.outputs['Color'])
# the garden bed: dark loam and moss (ambientCG Ground037, Moss002)
gd = os.path.join(ACG, 'Ground037', 'Ground037_2K-JPG_')
mpg = node(nt, 'ShaderNodeMapping', (-1600, -1200)); mpg.inputs['Scale'].default_value = (0.6, 0.6, 1)
link(nt, gm.outputs['Position'], mpg.inputs['Vector'])
g_col = ft('', False, (-1300, -1200), mpg.outputs['Vector']) if False else None
tg = node(nt, 'ShaderNodeTexImage', (-1300, -1200)); tg.image = img(gd + 'Color.jpg'); link(nt, mpg.outputs['Vector'], tg.inputs['Vector'])
tgd = node(nt, 'ShaderNodeTexImage', (-1300, -1500)); tgd.image = img(gd + 'Displacement.jpg', True); link(nt, mpg.outputs['Vector'], tgd.inputs['Vector'])
gcol = mixrgb(nt, maprange(nt, blur_bed.outputs['Fac'], 0.4, 0.65, 0.2, 0.75), tg.outputs['Color'], tmo.outputs['Color'])
gcol = mixrgb(nt, 1.0, gcol, (0.55, 0.55, 0.5, 1), 'MULTIPLY')
# the bed's edge breaks along the flagstone joints
edge = math_n(nt, 'ADD', msk.outputs['Red'], math_n(nt, 'MULTIPLY', math_n(nt, 'SUBTRACT', joint, 0.5), 0.5))
bedm = maprange(nt, edge, 0.45, 0.6)
col_out = mixrgb(nt, bedm, fcol, gcol)
# water: the stone beneath darkens and goes glassy; the edge creeps along the joints first
wedge = math_n(nt, 'ADD', msk.outputs['Green'], math_n(nt, 'MULTIPLY', joint, 0.35))
watm = maprange(nt, wedge, 0.5, 0.62)
col_out = mixrgb(nt, math_n(nt, 'MULTIPLY', watm, 0.75), col_out, (0.02, 0.025, 0.03, 1))
rgh_out = maprange(nt, f_rgh, 0.0, 1.0, 0.45, 0.85)
rgh_out = math_n(nt, 'MAXIMUM', rgh_out, math_n(nt, 'MULTIPLY', bedm, 0.95))
mixr = node(nt, 'ShaderNodeMix', (-200, -300)); mixr.data_type = 'FLOAT'
link(nt, watm, mixr.inputs['Factor']); link(nt, rgh_out, mixr.inputs['A']); mixr.inputs['B'].default_value = 0.015
hgt = math_n(nt, 'ADD', math_n(nt, 'MULTIPLY', f_dsp, math_n(nt, 'SUBTRACT', 1.0, bedm)), math_n(nt, 'MULTIPLY', tgd.outputs['Color'], bedm))
hgt = math_n(nt, 'MULTIPLY', hgt, math_n(nt, 'SUBTRACT', 1.0, watm))
fb = node(nt, 'ShaderNodeBump', (-200, -600)); fb.inputs['Strength'].default_value = 0.7; fb.inputs['Distance'].default_value = 0.02
link(nt, hgt, fb.inputs['Height'])
bsd = node(nt, 'ShaderNodeBsdfPrincipled', (200, 0)); bsd.inputs['Specular IOR Level'].default_value = 0.5
link(nt, col_out, bsd.inputs['Base Color']); link(nt, mixr.outputs['Result'], bsd.inputs['Roughness']); link(nt, fb.outputs['Normal'], bsd.inputs['Normal'])
o = node(nt, 'ShaderNodeOutputMaterial', (500, 0)); link(nt, bsd.outputs['BSDF'], o.inputs['Surface'])
if arg('dbg-floor', 0):
    em_ = node(nt, 'ShaderNodeEmission', (300, 300)); link(nt, {'1': col_out, '2': f_col, '3': fcol, '4': gcol}[str(arg('dbg-floor', 0))], em_.inputs['Color']); link(nt, em_.outputs['Emission'], o.inputs['Surface'])
ao_w = node(nt, 'ShaderNodeOutputAOV', (500, -400)); ao_w.aov_name = 'wt'; link(nt, watm, ao_w.inputs['Value'])
flo.data.materials.append(m_f)

def bed_at(x, y): return bed_field(x, y) > 0.1
def water_at(x, y): return (water_field(x, y) > -0.1) & ~bed_at(x, y)

# ---------------------------------------------------------------- air: a faint haze in the hall so the shaft has shape
hz = box('haze', -12, 12, -12, 41, -0.5, Z_ROOF)
m_h, nt = mat('haze')
pv = node(nt, 'ShaderNodeVolumePrincipled', (0, 0)); pv.inputs['Density'].default_value = arg('haze', 0.006)
pv.inputs['Anisotropy'].default_value = arg('aniso', 0.35); pv.inputs['Color'].default_value = (0.95, 0.96, 1.0, 1)
o = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, pv.outputs['Volume'], o.inputs['Volume'])
link(nt, node(nt, 'ShaderNodeBsdfTransparent', (0, 200)).outputs['BSDF'], o.inputs['Surface'])
hz.data.materials.append(m_h)
hz.visible_shadow = True
def haze_obj(name, ob, dens, aniso=0.35, col=(0.95, 0.96, 1.0)):
    m_, nt_ = mat(name)
    pv_ = node(nt_, 'ShaderNodeVolumePrincipled', (0, 0)); pv_.inputs['Density'].default_value = dens
    pv_.inputs['Anisotropy'].default_value = aniso; pv_.inputs['Color'].default_value = (*col, 1)
    o_ = node(nt_, 'ShaderNodeOutputMaterial', (300, 0)); link(nt_, pv_.outputs['Volume'], o_.inputs['Volume'])
    link(nt_, node(nt_, 'ShaderNodeBsdfTransparent', (0, 200)).outputs['BSDF'], o_.inputs['Surface'])
    ob.data.materials.append(m_)
# air thickens with distance (aerial depth towards the far window)
haze_obj('haze_far', box('haze_far', -12, 12, 20, 41, -0.5, Z_ROOF), arg('haze-far', 0.009), 0.2, (0.9, 0.95, 1.0))
# dust hangs in the sunbeam: a column of denser air along the shaft (the light itself draws its edge)
bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=2.4, radius2=2.4, depth=30)
me_ = bpy.data.meshes.new('shaftair'); bm.to_mesh(me_); bm.free()
sa = link_obj(bpy.data.objects.new('shaftair', me_))
sa.location = Vector((POOL[0], POOL[1], 0)) - SUN_D * 12
sa.rotation_euler = (-SUN_D).to_track_quat('Z', 'Y').to_euler()
haze_obj('haze_shaft', sa, arg('haze-shaft', 0.04), arg('aniso', 0.35), (1.0, 0.97, 0.92))
# the dust thins low down, so the beam does not veil the far arch where the line of sight crosses it
_ms = sa.data.materials[0]; _nt = _ms.node_tree
_pv = next(n_ for n_ in _nt.nodes if n_.bl_idname == 'ShaderNodeVolumePrincipled')
_gp = node(_nt, 'ShaderNodeNewGeometry', (-600, 0)); _sz = node(_nt, 'ShaderNodeSeparateXYZ', (-400, 0))
link(_nt, _gp.outputs['Position'], _sz.inputs['Vector'])
link(_nt, math_n(_nt, 'MULTIPLY', maprange(_nt, _sz.outputs['Z'], arg('shaft-fade0', 2.0), arg('shaft-fade1', 6.5), 0.15, 1.0), arg('haze-shaft', 0.04)), _pv.inputs['Density'])

# ---------------------------------------------------------------- instancing (geometry nodes from a point cloud)
def instances(name, coll, P, R, Sc, pick):
    m = len(P)
    me = bpy.data.meshes.new(name); me.vertices.add(m); me.vertices.foreach_set('co', np.asarray(P, np.float32).ravel())
    for an, data, tp in (('rot', np.asarray(R, np.float32), 'FLOAT_VECTOR'), ('scl', np.asarray(Sc, np.float32), 'FLOAT_VECTOR'),
                         ('pick', np.asarray(pick, np.int32), 'INT')):
        at = me.attributes.new(an, tp, 'POINT')
        at.data.foreach_set('vector' if tp == 'FLOAT_VECTOR' else 'value', data.ravel())
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
    L.new(ci.outputs[0], iop.inputs['Instance'])
    L.new(na['pick'].outputs['Attribute'], iop.inputs['Instance Index'])
    L.new(na['rot'].outputs['Attribute'], iop.inputs['Rotation'])
    L.new(na['scl'].outputs['Attribute'], iop.inputs['Scale'])
    L.new(iop.outputs['Instances'], go.inputs[0])
    md = ob.modifiers.new('scatter', 'NODES'); md.node_group = ng
    print(name, m, 'instances')
    return ob

def load_objs(blend, names):
    with bpy.data.libraries.load(blend, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names]
    base = os.path.dirname(blend)
    for im in bpy.data.images:
        if im.filepath and not os.path.exists(bpy.path.abspath(im.filepath)):
            cand = os.path.join(base, 'textures', os.path.basename(im.filepath))
            if os.path.exists(cand): im.filepath = cand
    out = []
    for o in dst.objects:
        o.location = (0, 0, 0); o.rotation_euler = (0, 0, 0); o.scale = (1, 1, 1); o.parent = None
        out.append(o)
    return sorted(out, key=lambda o: o.name)

def libcoll(name, objs):
    c = bpy.data.collections.new(name); sc.collection.children.link(c)
    for o in objs: c.objects.link(o)
    c.hide_render = True
    return c

def base_color_link(m):
    nt = m.node_tree
    for n_ in nt.nodes:
        if n_.bl_idname == 'ShaderNodeBsdfPrincipled' and n_.inputs['Base Color'].is_linked:
            return nt, n_, n_.inputs['Base Color'].links[0].from_socket
    return nt, None, None

def recolour(m, mode):
    # petals only: 'blue' turns white petals a pale sky blue; 'periwinkle' turns the scan's pink petals blue
    nt, bsdf, src = base_color_link(m)
    if bsdf is None: return
    hsv = node(nt, 'ShaderNodeSeparateColor', (-400, 600)); hsv.mode = 'HSV'; link(nt, src, hsv.inputs['Color'])
    if mode == 'blue':
        f = math_n(nt, 'MULTIPLY', maprange(nt, hsv.outputs['Blue'], 0.55, 0.75), maprange(nt, hsv.outputs['Green'], 0.3, 0.15))
        tint = (0.30, 0.66, 1.0, 1)
        newc = mixrgb(nt, f, src, mixrgb(nt, 1.0, src, tint, 'MULTIPLY'))
    else:
        hue = hsv.outputs['Red']
        f = math_n(nt, 'MULTIPLY', maprange(nt, hue, 0.78, 0.86), maprange(nt, hsv.outputs['Green'], 0.2, 0.4))
        cc = node(nt, 'ShaderNodeCombineColor', (-200, 700)); cc.mode = 'HSV'
        cc.inputs['Red'].default_value = 0.6; link(nt, math_n(nt, 'MULTIPLY', hsv.outputs['Green'], 0.55), cc.inputs['Green'])
        link(nt, math_n(nt, 'MINIMUM', math_n(nt, 'MULTIPLY', hsv.outputs['Blue'], 1.15), 1.0), cc.inputs['Blue'])
        newc = mixrgb(nt, f, src, cc.outputs['Color'])
    link(nt, newc, bsdf.inputs['Base Color'])

# ---------------------------------------------------------------- plants, all scanned (Poly Haven)
helio = load_objs(os.path.join(PH, 'flower_heliophila', 'flower_heliophila_2k.blend'),
                  ['flower_heliophila_small_LOD1', 'flower_heliophila_medium_LOD1', 'flower_heliophila_large_LOD2'])
for m_ in {o.data.materials[0] for o in helio}: recolour(m_, 'periwinkle')     # the scan's mauve tips go blue, never pink
helio_blue = []
for o in helio:
    ob = o.copy(); ob.data = o.data.copy(); ob.name = o.name + '_blue'
    mb = o.data.materials[0].copy(); mb.name = 'helio_blue'; recolour(mb, 'blue'); ob.data.materials[0] = mb
    helio_blue.append(ob)
peri = load_objs(os.path.join(PH, 'periwinkle_plant', 'periwinkle_plant_1k.blend'),
                 [f'periwinkle_plant_0{i}_LOD2' for i in range(1, 6)])
if peri: recolour(peri[0].data.materials[0], 'periwinkle')
cel = load_objs(os.path.join(PH, 'celandine_01', 'celandine_01_2k.blend'), [f'celandine_01_{k}_LOD1' for k in 'abcde'])
grass = load_objs(os.path.join(PH, 'grass_medium_01', 'grass_medium_01_2k.blend'),
                  [f'grass_medium_01_{k}_LOD1' for k in ('small_a', 'small_b', 'mid_a', 'mid_b', 'mid_c', 'tiny_a', 'tiny_e', 'tall_a', 'tall_b')])
fern = load_objs(os.path.join(PH, 'fern_02', 'fern_02_1k.blend'), ['fern_02_a', 'fern_02_b', 'fern_02_c', 'fern_02_d'])
rocks = load_objs(os.path.join(PH, 'rock_moss_set_01', 'rock_moss_set_01_1k.blend'), None) if False else []
with bpy.data.libraries.load(os.path.join(PH, 'rock_moss_set_01', 'rock_moss_set_01_1k.blend'), link=False) as (src, dst):
    rnames = list(src.objects)
rocks = load_objs(os.path.join(PH, 'rock_moss_set_01', 'rock_moss_set_01_1k.blend'), rnames)
rocks = [o for o in rocks if o.type == 'MESH']
for o in rocks: print('rock', o.name, tuple(round(v, 2) for v in o.dimensions))

# one library, in order: helio white (3), helio blue (3), periwinkle (5), celandine (5), grass (9)
garden = helio + helio_blue + peri + cel + grass
L_G = libcoll('garden_lib', garden)
iH, iB = 0, len(helio)
iP = iB + len(helio_blue); iC = iP + len(peri); iGr = iC + len(cel); nG = len(garden)
L_F = libcoll('fern_lib', fern)
L_R = libcoll('rock_lib', rocks)

c_m, s_m = math.cos(-MARK_YAW), math.sin(-MARK_YAW)
def off_mark(x, y, pad=0.12):
    lx = (x - MARK_X) * c_m - (y - MARK_Y) * s_m; ly = (x - MARK_X) * s_m + (y - MARK_Y) * c_m
    return ~((np.abs(lx) < 50 * S + pad) & (np.abs(ly) < T / 2 + pad))

# the letter leans against the front of the block, facing the lens
LB_N = Vector((math.sin(0.42), -math.cos(0.42), 0))
LETTER_BASE = Vector((BLOCK[0], BLOCK[1], 0)) + LB_N * arg('letter-off', 0.64)
def off_letter(x, y):
    # clear around the letter and in a narrowing lane from it towards the camera, so nothing hides it
    vx, vy = 0.3 - LETTER_BASE.x, 1.8 - LETTER_BASE.y; L_ = math.hypot(vx, vy); vx /= L_; vy /= L_
    dx, dy = x - LETTER_BASE.x, y - LETTER_BASE.y
    along = dx * vx + dy * vy; perp = np.abs(dx * vy - dy * vx)
    return ~(((along > -0.25) & (along < 2.6) & (perp < 0.3 + 0.03 * np.maximum(along, 0))) | (np.hypot(dx, dy) < 0.35))

def plant_points(n, x0, x1, y0, y1, keep):
    x = rng.uniform(x0, x1, n); y = rng.uniform(y0, y1, n)
    k = keep(x, y) & off_mark(x, y) & off_letter(x, y)
    return x[k], y[k]

P, R, Sc, K = [], [], [], []
def add(x, y, pick, smin, smax, z=0.0):
    m = len(x)
    if not m: return
    s = rng.uniform(smin, smax, m)
    P.append(np.stack([x, y, np.full(m, z) + rng.uniform(-0.01, 0.0, m)], 1))
    R.append(np.stack([rng.normal(0, 0.05, m), rng.normal(0, 0.05, m), rng.uniform(0, 6.283, m)], 1))
    Sc.append(np.stack([s, s, s * rng.uniform(0.9, 1.2, m)], 1)); K.append(pick)

# the bed: dense, mostly white and pale blue, a little yellow; thinner towards its edge and in front of the stone
bed_in = lambda x, y: bed_field(x, y) > 0.0
x, y = plant_points(int(34000 * DENS), BED_C[0] - 6, BED_C[0] + 6, BED_C[1] - 6, BED_C[1] + 6, bed_in)
depth = np.clip(bed_field(x, y) / 1.6, 0, 1)
front = (y < MARK_Y - 0.2) & (np.abs(x - MARK_X) < 1.35 + 0.1 * (MARK_Y - y))
blockz = np.hypot(x - BLOCK[0], y - BLOCK[1]) < 0.75
keep = (rng.uniform(0, 1, len(x)) < (0.35 + 0.65 * depth) * np.where(front, 0.85, 1.0)) & ~blockz & off_letter(x, y)
x, y = x[keep], y[keep]
u = rng.uniform(0, 1, len(x))
grass_k = u < 0.3
g_pick = rng.integers(iGr, nG, grass_k.sum())
gx_, gy_ = x[grass_k], y[grass_k]
g_front = (gy_ < MARK_Y) & (np.abs(gx_ - MARK_X) < 1.35 + 0.1 * (MARK_Y - gy_))
add(gx_[~g_front], gy_[~g_front], g_pick[~g_front], 1.0, 1.6)
add(gx_[g_front], gy_[g_front], iGr + 7 + rng.integers(0, 2, g_front.sum()), 0.5, 0.9)   # tiny tufts only
fx, fy = x[~grass_k], y[~grass_k]
v = rng.uniform(0, 1, len(fx))
pk = np.where(v < 0.36, rng.integers(iH, iH + 2, len(fx)),
     np.where(v < 0.62, rng.integers(iB, iB + 2, len(fx)),
     np.where(v < 0.82, rng.integers(iB, iB + 2, len(fx)), rng.integers(iC, iGr, len(fx)))))
sc_lo = np.where(pk >= iP, 1.3, 0.75); sc_hi = np.where(pk >= iP, 2.0, 1.15)
s = rng.uniform(0, 1, len(fx)) * (sc_hi - sc_lo) + sc_lo
# low in front of the stone, so the whole mark reads
infront = (fy < MARK_Y) & (np.abs(fx - MARK_X) < 1.35 + 0.1 * (MARK_Y - fy))
s = np.where(infront, s * 0.3, s)
m = len(fx)
P.append(np.stack([fx, fy, rng.uniform(-0.01, 0.0, m)], 1))
R.append(np.stack([rng.normal(0, 0.06, m), rng.normal(0, 0.06, m), rng.uniform(0, 6.283, m)], 1))
Sc.append(np.stack([s, s, s * rng.uniform(0.9, 1.25, m)], 1)); K.append(pk)
# a few large clumps deep in the bed
x, y = plant_points(int(160 * DENS), BED_C[0] - 5, BED_C[0] + 5, BED_C[1] - 5, BED_C[1] + 5, lambda x, y: bed_field(x, y) > 0.9)
x, y = x[~((y < MARK_Y) & (np.abs(x - MARK_X) < 1.7))], y[~((y < MARK_Y) & (np.abs(x - MARK_X) < 1.7))]
add(x, y, np.where(rng.uniform(0, 1, len(x)) < 0.55, iH + 2, iB + 2), 0.5, 0.8)
# flowers and grass in the cracks of the floor around the bed and along the water's edge
x, y = plant_points(int(9000 * DENS), -9, 10, -4, 24, lambda x, y: (bed_field(x, y) < 0) & (water_field(x, y) < -0.25))
near = np.clip(1.0 - (-bed_field(x, y)) / 4.0, 0, 1) ** 2
on_joint = (np.abs(x - np.round(x)) < 0.05) | (np.abs(y - np.round(y)) < 0.05)
keep = (rng.uniform(0, 1, len(x)) < near * 0.9) & on_joint
x, y = x[keep], y[keep]
v = rng.uniform(0, 1, len(x))
pk = np.where(v < 0.65, rng.integers(iGr, nG, len(x)), np.where(v < 0.85, rng.integers(iH, iH + 2, len(x)),
     np.where(v < 0.93, rng.integers(iB, iB + 2, len(x)), rng.integers(iC, iGr, len(x)))))
add(x, y, pk, 0.6, 1.1)
# the near-left corner: a small drift of flowers at the water's edge, out of focus, for depth
DRIFT = (arg('drift-x', -1.7), arg('drift-y', 5.3))
x, y = plant_points(int(2600 * DENS), DRIFT[0] - 2.5, DRIFT[0] + 2.5, DRIFT[1] - 2.0, DRIFT[1] + 2.0,
                    lambda x, y: (water_field(x, y) < -0.1) & (np.hypot((x - DRIFT[0]) / 1.4, y - DRIFT[1]) < 1.0 + 0.35 * fbm(x, y, 9)))
v = rng.uniform(0, 1, len(x))
pk = np.where(v < 0.3, rng.integers(iGr, nG, len(x)), np.where(v < 0.55, rng.integers(iH, iH + 2, len(x)),
     np.where(v < 0.8, rng.integers(iB, iB + 2, len(x)), np.where(v < 0.92, rng.integers(iB, iB + 2, len(x)), rng.integers(iC, iGr, len(x))))))
add(x, y, pk, 1.0, 1.5)
instances('garden', L_G, np.concatenate(P), np.concatenate(R), np.concatenate(Sc), np.concatenate(K))

# ferns at the feet of the columns and the walls, in the shade
FP, FR, FS, FK = [], [], [], []
for side in (-1, 1):
    for yc in COL_Y:
        if yc < -5 or yc > 33: continue
        nf = rng.integers(2, 5)
        a = rng.uniform(0, 2 * math.pi, nf)
        rr_ = rng.uniform(1.05, 1.5, nf)
        for k in range(nf):
            FP.append((side * NAVE + rr_[k] * math.cos(a[k]), yc + rr_[k] * math.sin(a[k]), 0))
            FR.append((rng.normal(0, 0.08), rng.normal(0, 0.08), rng.uniform(0, 6.28)))
            s = rng.uniform(0.8, 1.3); FS.append((s, s, s)); FK.append(rng.integers(0, len(fern)))
    for k in range(10):
        yy = rng.uniform(-4, 36); FP.append((side * 11.3, yy, 0)); FR.append((0, 0, rng.uniform(0, 6.28)))
        s = rng.uniform(0.9, 1.5); FS.append((s, s, s)); FK.append(rng.integers(0, len(fern)))
# ferns in the near-left drift
for k in range(4):
    FP.append((DRIFT[0] - 0.9 + rng.normal(0, 0.4), DRIFT[1] + 0.4 + rng.normal(0, 0.3), 0)); FR.append((0, 0, rng.uniform(0, 6.28)))
    s = rng.uniform(0.9, 1.3); FS.append((s, s, s)); FK.append(rng.integers(0, len(fern)))
instances('ferns', L_F, FP, FR, FS, FK)

# ---------------------------------------------------------------- fallen stone: roof blocks from the break, a column drum, scanned rubble
def block(name, size, loc, rot, mtl=M_ASHLAR, bev=0.05):
    sx, sy, sz = size
    ob = box(name, -sx / 2, sx / 2, -sy / 2, sy / 2, -sz / 2, sz / 2, mtl, bev)
    ob.location = loc; ob.rotation_euler = rot
    return ob
fall = [((1.4, 0.9, 0.7), (-1.6, 12.6, 0.22), (0.12, -0.25, 0.5)),
        ((1.1, 0.8, 0.6), (5.0, 12.8, 0.2), (0.3, 0.1, 1.1)),
        ((1.6, 1.0, 0.8), (-8.5, 15.0, 0.3), (0.05, 0.2, 0.8)),
        ((0.8, 0.6, 0.45), (4.2, 15.5, 0.15), (0.2, -0.3, 2.0))]
for i, (sz, lc, rt) in enumerate(fall):
    block(f'fallen{i}', sz, lc, rt)
# the block in the light, where the letter rests
pb_ = block('letterblock', (0.95, 0.7, 0.62), (BLOCK[0], BLOCK[1], 0.24), (0.04, -0.03, 0.42))
drum = cyl('drum', 0.74, -0.6, 0.6, n=64, m=M_COLUMN, bevel=0.04)
drum.rotation_euler = (math.pi / 2, 0, 0.6); drum.location = (-8.2, 9.0, 0.68)
drum2 = cyl('drum2', 0.74, -0.55, 0.55, n=64, m=M_COLUMN, bevel=0.04)
drum2.rotation_euler = (math.pi / 2 + 0.1, 0, 2.1); drum2.location = (8.6, 22.0, 0.66)
if rocks:
    RP, RR, RS, RK = [], [], [], []
    for (sz, lc, rt) in fall:
        for k in range(5):
            a = rng.uniform(0, 6.28); d_ = rng.uniform(0.6, 1.3)
            RP.append((lc[0] + d_ * math.cos(a), lc[1] + d_ * math.sin(a), 0)); RR.append((rng.uniform(0, 6), rng.uniform(0, 6), rng.uniform(0, 6)))
            s = rng.uniform(0.07, 0.2); RS.append((s, s, s)); RK.append(rng.integers(0, len(rocks)))
    instances('rubble', L_R, RP, RR, RS, RK)

# ---------------------------------------------------------------- ivy: scanned leaves (ambientCG LeafSet017) climbing columns and hanging from the arcade
iv_dir = os.path.join(ACG, 'LeafSet017', 'LeafSet017_2K-JPG_')
m_iv, nt = mat('ivy')
uvn = node(nt, 'ShaderNodeUVMap', (-900, 0))
ti = node(nt, 'ShaderNodeTexImage', (-700, 200)); ti.image = img(iv_dir + 'Color.jpg'); link(nt, uvn.outputs['UV'], ti.inputs['Vector'])
to_ = node(nt, 'ShaderNodeTexImage', (-700, -100)); to_.image = img(iv_dir + 'Opacity.jpg', True); link(nt, uvn.outputs['UV'], to_.inputs['Vector'])
tr_ = node(nt, 'ShaderNodeTexImage', (-700, -400)); tr_.image = img(iv_dir + 'Roughness.jpg', True); link(nt, uvn.outputs['UV'], tr_.inputs['Vector'])
tn_ = node(nt, 'ShaderNodeTexImage', (-700, -700)); tn_.image = img(iv_dir + 'NormalGL.jpg', True); link(nt, uvn.outputs['UV'], tn_.inputs['Vector'])
ivh = node(nt, 'ShaderNodeHueSaturation', (-400, 200)); ivh.inputs['Value'].default_value = 0.55; ivh.inputs['Saturation'].default_value = 0.9
link(nt, ti.outputs['Color'], ivh.inputs['Color'])
nmi = node(nt, 'ShaderNodeNormalMap', (-400, -700)); link(nt, tn_.outputs['Color'], nmi.inputs['Color']); nmi.inputs['Strength'].default_value = 0.6
pb = node(nt, 'ShaderNodeBsdfPrincipled', (-100, 200))
link(nt, ivh.outputs['Color'], pb.inputs['Base Color']); link(nt, tr_.outputs['Color'], pb.inputs['Roughness']); link(nt, nmi.outputs['Normal'], pb.inputs['Normal'])
pb.inputs['Specular IOR Level'].default_value = 0.6
tl = node(nt, 'ShaderNodeBsdfTranslucent', (-100, -200)); link(nt, ivh.outputs['Color'], tl.inputs['Color'])
ms = node(nt, 'ShaderNodeMixShader', (150, 0)); ms.inputs['Fac'].default_value = 0.3
link(nt, pb.outputs['BSDF'], ms.inputs[1]); link(nt, tl.outputs['BSDF'], ms.inputs[2])
trn = node(nt, 'ShaderNodeBsdfTransparent', (150, -250))
ma = node(nt, 'ShaderNodeMixShader', (350, 0)); link(nt, to_.outputs['Color'], ma.inputs['Fac'])
link(nt, trn.outputs['BSDF'], ma.inputs[1]); link(nt, ms.outputs['Shader'], ma.inputs[2])
o = node(nt, 'ShaderNodeOutputMaterial', (550, 0)); link(nt, ma.outputs['Shader'], o.inputs['Surface'])
CELLS = [(0.03, 0.44, 0.67, 0.985), (0.58, 0.92, 0.67, 0.985), (0.03, 0.44, 0.32, 0.635),
         (0.58, 0.92, 0.32, 0.635), (0.03, 0.44, 0.01, 0.31), (0.58, 0.92, 0.01, 0.31)]
leaves = []
for i, (u0, u1, v0, v1) in enumerate(CELLS):
    w_ = (u1 - u0) / (v1 - v0)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
    vs = [bm.verts.new(p) for p in ((-w_ / 2, 0, 0), (w_ / 2, 0, 0), (w_ / 2, 1, 0), (-w_ / 2, 1, 0))]
    f = bm.faces.new(vs)
    for lp, uv in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))): lp[uvl].uv = uv
    me = bpy.data.meshes.new(f'leaf{i}'); bm.to_mesh(me); bm.free(); me.materials.append(m_iv)
    leaves.append(bpy.data.objects.new(f'leaf{i}', me))
L_IV = libcoll('ivy_lib', leaves)

UP = Vector((0, 0, 1))
def leaf_frame(n_out):
    z = (n_out + UP * 0.35 + Vector(rng.normal(0, 0.35, 3))).normalized()
    tip = (UP * 0.4 - n_out * 0.2 + Vector(rng.normal(0, 0.6, 3)))
    yv = (tip - z * tip.dot(z)).normalized()
    xv = yv.cross(z)
    return Matrix((xv, yv, z)).transposed().to_euler()
IP, IR, IS, IK = [], [], [], []
def ivy_leaf(p, n_out, smin=0.07, smax=0.12):
    d_ = rng.uniform(0.01, 0.09)
    IP.append(tuple(p + n_out * d_)); IR.append(tuple(leaf_frame(n_out)))
    s = rng.uniform(smin, smax); IS.append((s, s, s)); IK.append(rng.integers(0, 6))
# columns: the ivy climbs from the floor in tongues on some, hangs from the capitals on others
CAM = Vector((0.3, 1.8, 0.95))
for (side, yc, mode, amt) in ((-1, 2, 'climb', 1.0), (-1, 14, 'hang', 1.0), (1, 8, 'climb', 0.8), (1, 20, 'hang', 0.9), (-1, 26, 'climb', 0.7)):
    cx_, cy_ = side * NAVE, yc
    ph = rng.uniform(0, 6.28, 3)
    nl = int(9000 * amt * DENS)
    th = rng.uniform(0, 2 * math.pi, nl); z = rng.uniform(0.5, 9.3, nl)
    reach = 2.5 + 3.5 * (0.5 + 0.5 * np.sin(th * 2 + ph[0])) * (0.6 + 0.4 * np.sin(th * 5 + ph[1])) * amt
    ok = (z < 0.6 + reach) if mode == 'climb' else (z > 9.3 - reach)
    # thinner at the tongue's end
    edge = np.abs(z - (0.6 + reach)) if mode == 'climb' else np.abs(z - (9.3 - reach))
    ok &= rng.uniform(0, 1, nl) < np.clip(edge / 1.2, 0.15, 1.0)
    for t_, z_ in zip(th[ok], z[ok]):
        n_out = Vector((math.cos(t_), math.sin(t_), 0))
        p = Vector((cx_, cy_, z_)) + n_out * 0.74
        if (CAM - p).normalized().dot(n_out) < -0.25: continue
        ivy_leaf(p, n_out)
# the arcade walls: curtains of ivy falling from the clerestory sills over the arches
for side in (-1, 1):
    xf = side * (NAVE - 0.7)
    n_out = Vector((-side, 0, 0))
    for ym in mids:
        if ym < -2 or ym > 30 or rng.uniform() < 0.35: continue
        nl = int(5000 * DENS)
        yy = rng.uniform(ym - 3, ym + 3, nl); zz = rng.uniform(Z_CAP, 13.6, nl)
        hang = 13.6 - (1.0 + 2.6 * (0.5 + 0.5 * np.sin(yy * 1.7 + rng.uniform(0, 6))))
        ok = zz > hang
        arch_r = np.hypot(yy - ym, zz - Z_CAP)
        ok &= arch_r > 2.05
        for y_, z_ in zip(yy[ok], zz[ok]):
            ivy_leaf(Vector((xf, y_, z_)), n_out)
instances('ivy', L_IV, IP, IR, IS, IK)

# ---------------------------------------------------------------- dust: motes adrift in the shaft
nm_ = int(arg('motes', 0))
m_dust, nt = mat('dust')
dd = node(nt, 'ShaderNodeBsdfPrincipled', (0, 0)); dd.inputs['Base Color'].default_value = (1, 0.95, 0.85, 1); dd.inputs['Roughness'].default_value = 0.6
tld = node(nt, 'ShaderNodeBsdfTranslucent', (0, -200)); tld.inputs['Color'].default_value = (1, 0.9, 0.75, 1)
msd = node(nt, 'ShaderNodeMixShader', (200, 0)); msd.inputs['Fac'].default_value = 0.6
link(nt, dd.outputs['BSDF'], msd.inputs[1]); link(nt, tld.outputs['BSDF'], msd.inputs[2])
o = node(nt, 'ShaderNodeOutputMaterial', (400, 0)); link(nt, msd.outputs['Shader'], o.inputs['Surface'])
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
me = bpy.data.meshes.new('mote'); bm.to_mesh(me); bm.free(); me.materials.append(m_dust)
mote = bpy.data.objects.new('mote', me)
L_D = libcoll('dust_lib', [mote])
tt = rng.uniform(0.3, 18.0, nm_)
rad = 1.7 * np.sqrt(rng.uniform(0, 1, nm_)); aa = rng.uniform(0, 6.28, nm_)
foot = np.array([MARK_X - 0.2, MARK_Y + 0.3, 0.0])
axd = -np.array(SUN_D)
pts = foot + tt[:, None] * axd + np.stack([rad * np.cos(aa), rad * np.sin(aa), np.zeros(nm_)], 1)
s = rng.uniform(0.004, 0.009, nm_)
if nm_: instances('dust', L_D, pts, np.zeros((nm_, 3)), np.stack([s, s, s], 1), np.zeros(nm_, int))

# ---------------------------------------------------------------- camera
cam_d = bpy.data.cameras.new('cam'); cam = link_obj(bpy.data.objects.new('cam', cam_d)); sc.camera = cam
cam_d.lens = arg('lens', 22.0); cam_d.sensor_width = 36; cam_d.sensor_fit = 'HORIZONTAL'
cam.location = (arg('cx', 0.3), arg('cy', 1.8), arg('cz', 0.95))
pitch = math.radians(arg('pitch', 9.0)); yaw = math.radians(arg('cam-yaw', -10.0))
cam.rotation_euler = (math.pi / 2 + pitch, 0, yaw)
cam_d.dof.use_dof = True
cam_d.dof.focus_distance = (Vector((MARK_X, MARK_Y, 1.3)) - cam.location).length
cam_d.dof.aperture_fstop = arg('fstop', 3.2)
cam_d.dof.aperture_blades = 7
cam_d.clip_start = 0.05; cam_d.clip_end = 400
cam_d.shift_y = arg('shift', 0.0)

# portals at the openings so the sky's light finds its way in
def portal(loc, rot, sx, sy):
    l_ = bpy.data.lights.new('portal', 'AREA'); l_.shape = 'RECTANGLE'; l_.size = sx; l_.size_y = sy
    l_.cycles.is_portal = True
    ob = link_obj(bpy.data.objects.new('portal', l_)); ob.location = loc; ob.rotation_euler = rot
for ym in mids:
    for side in (-1, 1):
        portal((side * 11.9, ym, 6.5), (0, side * math.pi / 2, 0), 7.5, 2.1)
        if side > 0: portal((side * NAVE, ym, 16.0), (0, side * math.pi / 2, 0), 5.2, 1.7)
portal((0, 40.9, (FWS + 15.7) / 2), (-math.pi / 2, 0, 0), 2 * FWW, 15.7 - FWS)
portal((1.5, 36.0, Z_ROOF - 0.05), (0, 0, 0), 9.0, 9.0)
portal((HOLE[0], HOLE[1], Z_ROOF - 0.05), (0, 0, 0), 5.5, 5.5)

# ---------------------------------------------------------------- the far country: scanned cliffs as ridges, in aerial haze
if SH:
    # the haze colour is the sky's own, read from the HDRI just above the horizon
    px_ = np.empty(len(env.image.pixels), np.float32); env.image.pixels.foreach_get(px_)
    iw_, ih_ = env.image.size; px_ = px_.reshape(ih_, iw_, 4)
    HAZE = px_[int(ih_ * 0.52):int(ih_ * 0.56), :, :3].reshape(-1, 3).mean(0) * arg('sky', 0.65) * arg('haze-sky', 0.8)
    HAZE = HAZE * np.array([0.86, 0.96, 1.12])        # distance cools it a little, as air does
    print('HAZE', HAZE)
    def aerial(m_, L_):
        # mix towards the sky's horizon colour with distance from the lens: 1 - exp(-d / L)
        nt_ = m_.node_tree
        out_ = next(n_ for n_ in nt_.nodes if n_.bl_idname == 'ShaderNodeOutputMaterial' and n_.is_active_output)
        src_ = out_.inputs['Surface'].links[0].from_socket
        cd_ = node(nt_, 'ShaderNodeCameraData', (0, -600))
        f_ = math_n(nt_, 'SUBTRACT', 1.0, math_n(nt_, 'EXPONENT', math_n(nt_, 'DIVIDE', math_n(nt_, 'MULTIPLY', cd_.outputs['View Distance'], -1.0), L_)))
        em_ = node(nt_, 'ShaderNodeEmission', (0, -800)); em_.inputs['Color'].default_value = (*[float(v) for v in HAZE], 1)
        mx_ = node(nt_, 'ShaderNodeMixShader', (300, -600)); link(nt_, f_, mx_.inputs['Fac'])
        link(nt_, src_, mx_.inputs[1]); link(nt_, em_.outputs['Emission'], mx_.inputs[2])
        link(nt_, mx_.outputs['Shader'], out_.inputs['Surface'])
        # a step darker and cooler than the sunlit scan, so each ridge holds against the sky
        pb_ = next((n_ for n_ in nt_.nodes if n_.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
        if pb_ is not None and pb_.inputs['Base Color'].is_linked:
            sc_ = pb_.inputs['Base Color'].links[0].from_socket
            link(nt_, mixrgb(nt_, 1.0, sc_, (0.25, 0.29, 0.37, 1), 'MULTIPLY'), pb_.inputs['Base Color'])
    cl_ = load_objs(os.path.join(PH, 'coastal_cliff_01', 'coastal_cliff_01_1k.blend'), ['coastal_cliff_01_LOD3'])
    if cl_:
        base_ = cl_[0]; aerial(base_.data.materials[0], arg('aerial', 4200.0))
        # three low ridges, one behind another, each further and paler
        for i, (loc_, rz_, s_, sz_) in enumerate((((-40, 430, -24), 0.05, 8.0, 5.0),
                                                 ((180, 760, -34), -0.3, 14.0, 7.5),
                                                 ((-380, 1100, -46), 0.25, 20.0, 10.0))):
            o_ = base_ if i == 0 else base_.copy()
            sc.collection.objects.link(o_)
            o_.location = loc_; o_.rotation_euler = (0, 0, rz_); o_.scale = (s_, s_, sz_ * arg('cliff-z', 1.0))
            o_.visible_shadow = False
            bpy.context.view_layer.update()
            bb_ = [o_.matrix_world @ Vector(c) for c in o_.bound_box]
            print('CLIFF', i, [round(min(v[k] for v in bb_)) for k in range(3)], [round(max(v[k] for v in bb_)) for k in range(3)])

# ---------------------------------------------------------------- fill: what the bright pool and the sky would give back
def fill_light(name, loc, aim, size, power, col, spot=False):
    l_ = bpy.data.lights.new(name, 'AREA'); l_.shape = 'RECTANGLE'; l_.size, l_.size_y = size
    l_.energy = power; l_.color = col
    ob = link_obj(bpy.data.objects.new(name, l_)); ob.location = loc
    ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    ob.visible_camera = False; ob.visible_glossy = False; ob.visible_transmission = False
    return ob
# warm bounce off the sunlit flowers onto the stone's face (a film-set bounce card), so the seam reads top to bottom
fill_light('bounce', (MARK_X - 0.9, MARK_Y - 3.2, 0.35), (MARK_X, MARK_Y, 1.3), (2.6, 0.8), arg('bounce', 80.0), (1.0, 0.88, 0.76))
# cool skylight from the breaks, high in the nave, so the columns, arches and ivy read in the blue shadow
fill_light('skyfill', (0.0, 14.0, Z_ROOF - 1.0), (0.0, 14.0, 0.0), (10.0, 30.0), arg('skyfill', 1100.0), (0.62, 0.74, 1.0))

# ---------------------------------------------------------------- the letter: folded in half, resting on the block in the light
m_pp, nt = mat('paper')
pd_ = os.path.join(ACG, 'Paper002', 'Paper002_2K-JPG_')
uvp = node(nt, 'ShaderNodeUVMap', (-900, 0))
tpc = node(nt, 'ShaderNodeTexImage', (-700, 200)); tpc.image = img(pd_ + 'Color.jpg'); link(nt, uvp.outputs['UV'], tpc.inputs['Vector'])
tpn = node(nt, 'ShaderNodeTexImage', (-700, -200)); tpn.image = img(pd_ + 'NormalGL.jpg', True); link(nt, uvp.outputs['UV'], tpn.inputs['Vector'])
pcol = mixrgb(nt, 0.55, tpc.outputs['Color'], (0.64, 0.59, 0.50, 1))     # warm paper, a touch below white
pcol = mixrgb(nt, 1.0, pcol, (0.7, 0.7, 0.7, 1), 'MULTIPLY')
nmp = node(nt, 'ShaderNodeNormalMap', (-400, -200)); nmp.inputs['Strength'].default_value = 0.5; link(nt, tpn.outputs['Color'], nmp.inputs['Color'])
pbp = node(nt, 'ShaderNodeBsdfPrincipled', (0, 200)); pbp.inputs['Roughness'].default_value = 0.85
link(nt, pcol, pbp.inputs['Base Color']); link(nt, nmp.outputs['Normal'], pbp.inputs['Normal'])
tlp = node(nt, 'ShaderNodeBsdfTranslucent', (0, -100)); tlp.inputs['Color'].default_value = (0.95, 0.88, 0.76, 1)
mpp_ = node(nt, 'ShaderNodeMixShader', (250, 0)); mpp_.inputs['Fac'].default_value = 0.2
link(nt, pbp.outputs['BSDF'], mpp_.inputs[1]); link(nt, tlp.outputs['BSDF'], mpp_.inputs[2])
op_ = node(nt, 'ShaderNodeOutputMaterial', (500, 0)); link(nt, mpp_.outputs['Shader'], op_.inputs['Surface'])
PW, PH_, NU, NV = arg('letter-w', 0.29), arg('letter-h', 0.41), 16, 24   # a writing sheet, folded once across
bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
grid = []
bow = arg('bow', 0.09)                    # the crease stands forward: the fold has not quite let go
for j in range(NV + 1):
    row = []
    v = j / NV
    for i in range(NU + 1):
        u = i / NU
        x = (u - 0.5) * PW
        y = v * PH_
        z = bow * (1 - abs(2 * v - 1)) ** 0.8                          # local z: out of the sheet, towards the lens
        z += 0.012 * max(0, (v - 0.82) / 0.18) ** 2 * (0.4 + 0.6 * abs(2 * u - 1))   # the top edge curls a little
        z += 0.006 * max(0, (0.12 - v) / 0.12) ** 2 * max(0, (u - 0.75) / 0.25)       # a lifted bottom corner
        row.append(bm.verts.new((x, y, z)))
    grid.append(row)
for j in range(NV):
    for i in range(NU):
        f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
        for lp, (uu, vv) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
            lp[uvl].uv = (uu / NU * 0.5, vv / NV * 0.7)
me = bpy.data.meshes.new('letter'); bm.to_mesh(me); bm.free()
for p_ in me.polygons: p_.use_smooth = True
letter = link_obj(bpy.data.objects.new('letter', me)); me.materials.append(m_pp)
letter.modifiers.new('sol', 'SOLIDIFY').thickness = 0.0006
# stand it up, leaning back against the block, turned towards the lens with a little give
lean = math.radians(arg('lean', 34.0))
yaw_l = math.radians(arg('letter-rot', 38.0))       # turned so the sun rakes across the fold
Rl = Matrix.Rotation(yaw_l, 4, 'Z') @ Matrix(((1, 0, 0, 0), (0, math.sin(lean), -math.cos(lean), 0), (0, math.cos(lean), math.sin(lean), 0), (0, 0, 0, 1)))
letter.matrix_world = Matrix.Translation(LETTER_BASE + Vector((0, 0, -0.004))) @ Rl
letter.pass_index = 3
for ob_ in (STONE['stone'],): ob_.pass_index = 1
for ob_ in (STONE['crystal'], STONE.get('veil')):
    if ob_ is not None: ob_.pass_index = 2

# ---------------------------------------------------------------- light through the crystal
# The sun crosses the hall away from the lens, so light refracted straight through the crystal lands behind the stone,
# out of view. What a cut crystal also throws is light that enters its front, reflects inside and leaves forward:
# a soft dapple of sky blue on the ground at the stone's foot. Projected by a small spot just in front of the crystal.
if arg('fake-caustic', 0):     # cut after review: at the foot it read as a glow, not as light
    Mst = STONE['root'].matrix_world
    nf = (Mst.to_3x3() @ Vector((0, -1, 0))).normalized()
    cc_ = Vector(STONE['info']['crystal_centre'])
    lp_ = cc_ + nf * (T / 2 + 0.14)
    tgt = Vector((cc_.x, cc_.y, 0.0)) + nf * arg('caustic-d', 1.1) + Vector((-0.15, 0, 0))
    kd = bpy.data.lights.new('caustic', 'SPOT'); kd.energy = arg('caustic', 1600.0); kd.color = (1, 1, 1)
    kd.spot_size = math.radians(arg('caustic-cone', 44.0)); kd.spot_blend = 0.9; kd.shadow_soft_size = 0.02
    kd.use_nodes = True; kn = kd.node_tree; kn.nodes.clear()
    ktc = node(kn, 'ShaderNodeTexCoord', (-1000, 0)); ksp = node(kn, 'ShaderNodeSeparateXYZ', (-800, 0))
    link(kn, ktc.outputs['Normal'], ksp.inputs['Vector'])
    kz = math_n(kn, 'MAXIMUM', math_n(kn, 'MULTIPLY', ksp.outputs['Z'], -1.0), 0.05)
    kc = node(kn, 'ShaderNodeCombineXYZ', (-500, 0))
    link(kn, math_n(kn, 'DIVIDE', ksp.outputs['X'], kz), kc.inputs['X']); link(kn, math_n(kn, 'DIVIDE', ksp.outputs['Y'], kz), kc.inputs['Y'])
    def cvor(scale, rot, loc):
        mp_ = node(kn, 'ShaderNodeMapping', (loc, 200)); mp_.inputs['Rotation'].default_value = (0, 0, rot)
        mp_.inputs['Location'].default_value = (rot * 3.1, rot * 1.7, 0)
        link(kn, kc.outputs['Vector'], mp_.inputs['Vector'])
        v_ = node(kn, 'ShaderNodeTexVoronoi', (loc + 200, 200)); v_.voronoi_dimensions = '2D'; v_.feature = 'DISTANCE_TO_EDGE'
        v_.inputs['Scale'].default_value = scale; v_.inputs['Randomness'].default_value = 0.85
        link(kn, mp_.outputs['Vector'], v_.inputs['Vector'])
        return maprange(kn, v_.outputs['Distance'], 0.0, 0.16, 1.0, 0.0)
    veins = math_n(kn, 'ADD', math_n(kn, 'MULTIPLY', cvor(5.0, 0.4, -400), 0.7), math_n(kn, 'MULTIPLY', cvor(8.0, 1.3, -400), 0.45))
    veins = math_n(kn, 'ADD', math_n(kn, 'POWER', veins, 2.2), 0.06)
    kem = node(kn, 'ShaderNodeEmission', (0, 0)); kem.inputs['Color'].default_value = (*SKY, 1)
    link(kn, veins, kem.inputs['Strength'])
    ko = node(kn, 'ShaderNodeOutputLight', (200, 0)); link(kn, kem.outputs['Emission'], ko.inputs['Surface'])
    kob = link_obj(bpy.data.objects.new('caustic', kd)); kob.location = lp_
    kob.rotation_euler = (tgt - lp_).to_track_quat('-Z', 'Y').to_euler()
    kob.visible_camera = False; kob.visible_glossy = False; kob.visible_transmission = False
    # light linking: it falls on the ground and flowers only, never on the stone or the crystal that throw it
    kx = bpy.data.collections.new('caustic_excl')
    for o_ in (STONE['stone'], STONE['crystal'], STONE.get('veil')):
        if o_ is not None: kx.objects.link(o_)
    kob.light_linking.receiver_collection = kx
    for co_ in kx.collection_objects:
        co_.light_linking.link_state = 'EXCLUDE'
    print('CAUSTIC at', tuple(round(v, 2) for v in lp_), 'to', tuple(round(v, 2) for v in tgt))
if arg('caustics', 0):
    # MNEE shadow caustics: the sun is a caustic light, the crystal a caster, the stone, floor and flowers receivers
    stone.mark_caustic_lights([sun])
    for n_ in ('floor', 'garden', 'letterblock'):
        o_ = bpy.data.objects.get(n_)
        if o_: o_.cycles.is_caustics_receiver = True

# ---------------------------------------------------------------- compositor: soft bloom, a breath of halation, vignette
sc.use_nodes = True
ct = sc.node_tree; ct.nodes.clear()
rl = ct.nodes.new('CompositorNodeRLayers')
gl = ct.nodes.new('CompositorNodeGlare'); gl.glare_type = 'BLOOM'; gl.quality = 'HIGH'
gl.inputs['Threshold'].default_value = arg('bloom-th', 1.0); gl.inputs['Smoothness'].default_value = 0.7
gl.inputs['Strength'].default_value = arg('bloom', 0.35); gl.inputs['Size'].default_value = 0.9
gl.inputs['Tint'].default_value = (1.0, 0.85, 0.7, 1)
ct.links.new(rl.outputs['Image'], gl.inputs['Image'])
ld = ct.nodes.new('CompositorNodeLensdist'); ld.inputs['Distortion'].default_value = 0.0; ld.inputs['Dispersion'].default_value = 0.012
ct.links.new(gl.outputs['Image'], ld.inputs['Image'])
el = ct.nodes.new('CompositorNodeEllipseMask'); el.width = 1.25; el.height = 1.35
bl = ct.nodes.new('CompositorNodeBlur'); bl.filter_type = 'GAUSS'; bl.size_x = int(W * 0.2); bl.size_y = int(H * 0.2)
ct.links.new(el.outputs['Mask'], bl.inputs['Image'])
vg = ct.nodes.new('CompositorNodeMapRange'); vg.inputs['From Min'].default_value = 0; vg.inputs['From Max'].default_value = 1
vg.inputs['To Min'].default_value = arg('vig', 0.62); vg.inputs['To Max'].default_value = 1.0
ct.links.new(bl.outputs['Image'], vg.inputs['Value'])
mx = ct.nodes.new('CompositorNodeMixRGB'); mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1
ct.links.new(ld.outputs['Image'], mx.inputs[1]); ct.links.new(vg.outputs['Value'], mx.inputs[2])
comp = ct.nodes.new('CompositorNodeComposite'); ct.links.new(mx.outputs['Image'], comp.inputs['Image'])
PASSES = arg('passes', '')
if PASSES:
    # one 16-bit PNG of data, Standard view so it inverts exactly: R depth / 60 m, G still water, B object (1 stone,
    # 2 crystal, 3 letter) / 4
    vl.use_pass_z = True; vl.use_pass_object_index = True
    fo = ct.nodes.new('CompositorNodeOutputFile')
    fo.base_path = os.path.dirname(PASSES); fo.format.file_format = 'PNG'
    fo.format.color_depth = '16'; fo.format.color_mode = 'RGB'
    # Raw, so the values are written linear (Standard would put them through the sRGB curve)
    fo.format.color_management = 'OVERRIDE'; fo.format.view_settings.view_transform = 'Raw'
    fo.format.view_settings.look = 'None'; fo.format.view_settings.exposure = 0; fo.format.view_settings.gamma = 1
    fo.file_slots.clear(); fo.file_slots.new('data')
    cc = ct.nodes.new('CompositorNodeCombineColor'); cc.mode = 'RGB'
    def mr(sock, hi):
        n_ = ct.nodes.new('CompositorNodeMapRange'); n_.use_clamp = True
        n_.inputs['From Min'].default_value = 0; n_.inputs['From Max'].default_value = hi
        n_.inputs['To Min'].default_value = 0; n_.inputs['To Max'].default_value = 1
        ct.links.new(sock, n_.inputs['Value']); return n_.outputs['Value']
    ct.links.new(mr(rl.outputs['Depth'], 60.0), cc.inputs['Red'])
    ct.links.new(mr(rl.outputs['wt'], 1.0), cc.inputs['Green'])
    ct.links.new(mr(rl.outputs['IndexOB'], 4.0), cc.inputs['Blue'])
    ct.links.new(cc.outputs['Image'], fo.inputs[0])
    sc.frame_current = 1
# the camera, the beam and the letter, for the page and the loop
from bpy_extras.object_utils import world_to_camera_view
bpy.context.view_layer.update()
def frame_box(ob):
    dg_ = bpy.context.evaluated_depsgraph_get(); e_ = ob.evaluated_get(dg_)
    pts_ = [world_to_camera_view(sc, cam, e_.matrix_world @ v.co) for v in e_.data.vertices]
    return [min(p.x for p in pts_), 1 - max(p.y for p in pts_), max(p.x for p in pts_), 1 - min(p.y for p in pts_)]
info = {'w': W, 'h': H, 'lens': cam_d.lens, 'sensor': cam_d.sensor_width,
        'cam_matrix': [list(r) for r in cam.matrix_world], 'beam_foot': [POOL[0], POOL[1], 0.0],
        'beam_dir': list(-SUN_D), 'beam_r': arg('hole', 2.0) * 0.95, 'letter': frame_box(letter),
        'stone': frame_box(STONE['stone'])}
json.dump(info, open(OUT + '.json', 'w'), indent=1)
print('LETTER', info['letter'], 'STONE', info['stone'])

if arg('border', ''):
    b_ = [float(v) for v in arg('border', '').split(',')]
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_max_x = b_[0], b_[2]
    sc.render.border_min_y, sc.render.border_max_y = 1 - b_[3], 1 - b_[1]
if '--dry' in argv:
    print('DRY_OK'); sys.exit(0)

t0 = time.time()
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('RENDER_SECONDS', round(time.time() - t0, 1))
if PASSES:
    cand = os.path.join(os.path.dirname(PASSES), 'data0001.png')
    if os.path.exists(cand): os.replace(cand, PASSES)
    try:
        # read the 16-bit PNG back as plain numbers and keep it exact as data.npz (float16), which numpy reads directly
        vi = bpy.data.images.load(PASSES); vi.colorspace_settings.name = 'Non-Color'; vw_, vh_ = vi.size
        a_ = np.empty(vw_ * vh_ * 4, np.float32); vi.pixels.foreach_get(a_)
        a_ = a_.reshape(vh_, vw_, 4)[::-1, :, :3]
        np.savez_compressed(os.path.splitext(PASSES)[0] + '.npz', data=a_.astype(np.float16))
        print('DATA_NPZ', a_.shape, [float(a_[..., k].max()) for k in range(3)])
    except Exception as e_:
        print('DATA_NPZ failed', e_)
