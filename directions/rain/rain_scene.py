# Rain: a pale stone garden wall in a green city at blue hour, gentle rain, a lightbox set into the wall.
# Blender 4.5 LTS, Cycles CPU. Poly Haven CC0 assets (see credits.txt).
#
# Run:  blender -b -P rain_scene.py -- --assets <dir> --poster <png> --out <file> [options]
#   --res 640x360  --samples 32  --time 0 (seconds, 0 = no limit)
#   --exr <file.exr>   also writes a multilayer EXR with the light groups and the data passes for the loop
#   --corners <file.json>  writes where the lightbox face lands on the frame
import bpy, bmesh, math, json, os, sys, random, time
import numpy as np
from mathutils import Vector, Matrix, Euler

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    k = '--' + name
    return type(default)(argv[argv.index(k) + 1]) if k in argv else default

ASSETS = arg('assets', '')
POSTER = arg('poster', '')
OUT = arg('out', '/tmp/rain.png')
RES = arg('res', '640x360')
SAMPLES = arg('samples', 32)
TIME = arg('time', 0.0)
EXR = arg('exr', '')
CORNERS = arg('corners', '')
EXPO = arg('exposure', 0.0)
SKY = arg('sky', 0.5)
P_STR = arg('poster-str', 5.0)
W_STR = arg('warm-str', 6.0)

rng = np.random.default_rng(11); random.seed(11)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
W, H = (int(v) for v in RES.split('x'))
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.resolution_percentage = 100
sc.render.engine = 'CYCLES'
cy = sc.cycles
cy.device = 'CPU'; cy.samples = SAMPLES
cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.02
cy.time_limit = TIME
cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'; cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
cy.max_bounces = 8; cy.diffuse_bounces = 3; cy.glossy_bounces = 3
cy.transmission_bounces = 6; cy.transparent_max_bounces = 24; cy.volume_bounces = 0
cy.caustics_reflective = False; cy.caustics_refractive = False
cy.blur_glossy = 1.0; cy.use_light_tree = True
cy.sample_clamp_indirect = 8.0
sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Base Contrast'
sc.view_settings.exposure = EXPO
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '16'
sc.render.image_settings.color_mode = 'RGB'

vl = sc.view_layers[0]
vl.use_pass_mist = True; vl.use_pass_z = True
for nm in ('plant', 'wet', 'rill', 'face', 'glass'):
    a = vl.aovs.add(); a.name = nm; a.type = 'VALUE'
for g in ('sky', 'poster', 'warm'):
    vl.lightgroups.add(name=g)
sc.world = bpy.data.worlds.new('world')
mi = sc.world.mist_settings; mi.start = 6; mi.depth = 70; mi.falloff = 'QUADRATIC'

# ---------------------------------------------------------------- helpers
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
def aov(nt, name, val):
    o = node(nt, 'ShaderNodeOutputAOV', (900, -400 - 120 * len([n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputAOV'])))
    o.aov_name = name
    if isinstance(val, (int, float)): o.inputs['Value'].default_value = val
    else: link(nt, val, o.inputs['Value'])
def srgb(c): return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)
def box(name, x0, x1, y0, y1, z0, z1, m=None):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    ob.scale = (x1 - x0, y1 - y0, z1 - z0); ob.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    if m: me.materials.append(m)
    bv = ob.modifiers.new('bevel', 'BEVEL'); bv.width = 0.006; bv.segments = 2; bv.use_clamp_overlap = True
    return ob
def plane(name, x0, x1, z0, z1, y, m=None, facing=-1):
    # a vertical rectangle in the x/z plane at depth y, its normal towards -y
    me = bpy.data.meshes.new(name)
    v = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
    me.from_pydata(v, [], [(0, 1, 2, 3)]); me.update()
    uv = me.uv_layers.new(name='UVMap')
    for i, l in enumerate(me.loops): uv.data[i].uv = [(0, 0), (1, 0), (1, 1), (0, 1)][l.vertex_index]
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    if m: me.materials.append(m)
    return ob

ACG = arg('acg', '')
def pbr(name, folder, scale, tint=(1, 1, 1), val=1.0, sat=1.0, rough=(0.0, 1.0), nstr=1.0, wet=None, coords='Object', plant=0.0, extra=None, acg=None):
    """A scanned material, box-mapped in metres. wet: (amount node builder) darkens and glosses it."""
    m, nt = mat(name)
    tc = node(nt, 'ShaderNodeTexCoord', (-1400, 0))
    mp = node(nt, 'ShaderNodeMapping', (-1200, 0)); mp.inputs['Scale'].default_value = (scale, scale, scale)
    link(nt, tc.outputs[coords], mp.inputs['Vector'])
    base = os.path.join(ASSETS, folder, folder) if not acg else os.path.join(ACG, acg, acg + '_2K-JPG')
    sx = ('_diff_2k.jpg', '_rough_2k.jpg', '_nor_gl_2k.jpg', '_disp_2k.jpg') if not acg else ('_Color.jpg', '_Roughness.jpg', '_NormalGL.jpg', '_Displacement.jpg')
    def t(suffix, nc, loc):
        n = node(nt, 'ShaderNodeTexImage', loc); n.image = img(base + suffix, nc); n.projection = 'BOX'; n.projection_blend = 0.2
        link(nt, mp.outputs['Vector'], n.inputs['Vector']); return n
    td = t(sx[0], False, (-900, 300)); tr = t(sx[1], True, (-900, 0)); tn = t(sx[2], True, (-900, -300))
    th = t(sx[3], True, (-900, -600)); nt['height'] = th.name
    hs = node(nt, 'ShaderNodeHueSaturation', (-600, 300)); hs.inputs['Saturation'].default_value = sat; hs.inputs['Value'].default_value = val
    link(nt, td.outputs['Color'], hs.inputs['Color'])
    ti = node(nt, 'ShaderNodeMix', (-450, 300)); ti.data_type = 'RGBA'; ti.blend_type = 'MULTIPLY'; ti.inputs['Factor'].default_value = 1
    link(nt, hs.outputs['Color'], ti.inputs['A']); ti.inputs['B'].default_value = (*tint, 1)
    rr = node(nt, 'ShaderNodeMapRange', (-600, 0)); rr.inputs['To Min'].default_value = rough[0]; rr.inputs['To Max'].default_value = rough[1]
    link(nt, tr.outputs['Color'], rr.inputs['Value'])
    nm = node(nt, 'ShaderNodeNormalMap', (-600, -300)); nm.inputs['Strength'].default_value = nstr
    link(nt, tn.outputs['Color'], nm.inputs['Color'])
    b = node(nt, 'ShaderNodeBsdfPrincipled', (0, 0))
    col, ro = ti.outputs['Result'], rr.outputs['Result']
    if wet is not None:
        w = wet(nt, tc, th.outputs['Color'])        # 0 dry .. 1 soaked
        dk = node(nt, 'ShaderNodeMix', (-250, 300)); dk.data_type = 'RGBA'; dk.blend_type = 'MULTIPLY'
        link(nt, w, dk.inputs['Factor']); link(nt, col, dk.inputs['A']); dk.inputs['B'].default_value = (0.74, 0.74, 0.75, 1)
        col = dk.outputs['Result']
        wr = node(nt, 'ShaderNodeMix', (-250, 0)); wr.data_type = 'FLOAT'
        link(nt, w, wr.inputs['Factor']); link(nt, ro, wr.inputs['A']); wr.inputs['B'].default_value = 0.12
        ro = wr.outputs['Result']
        aov(nt, 'wet', w)
    link(nt, col, b.inputs['Base Color']); link(nt, ro, b.inputs['Roughness']); link(nt, nm.outputs['Normal'], b.inputs['Normal'])
    o = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, b.outputs['BSDF'], o.inputs['Surface'])
    aov(nt, 'plant', plant)
    if extra: extra(nt, b, tc, th.outputs['Color'])
    return m

def noise_mask(nt, tc, scale, lo, hi, coords='Object', detail=4.0, w=None):
    n = node(nt, 'ShaderNodeTexNoise', (-1100, -700)); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
    if w is not None:
        mp = node(nt, 'ShaderNodeMapping', (-1250, -700)); mp.inputs['Scale'].default_value = w
        link(nt, tc.outputs[coords], mp.inputs['Vector']); link(nt, mp.outputs['Vector'], n.inputs['Vector'])
    else: link(nt, tc.outputs[coords], n.inputs['Vector'])
    r = node(nt, 'ShaderNodeMapRange', (-900, -700)); r.inputs['From Min'].default_value = lo; r.inputs['From Max'].default_value = hi
    link(nt, n.outputs['Fac'], r.inputs['Value']); return r.outputs['Result']

def fix_paths(folder):
    for im in bpy.data.images:
        if im.filepath.startswith('//'):
            p = os.path.join(ASSETS, folder, im.filepath[2:])
            if os.path.exists(p): im.filepath = p
def load(folder, names):
    with bpy.data.libraries.load(os.path.join(ASSETS, folder, folder + '_2k.blend'), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names]
    fix_paths(folder)
    return {o.name: o for o in dst.objects if o}


# ---------------------------------------------------------------- world: blue hour, overcast, in fog
wn = sc.world.node_tree if sc.world.use_nodes else None
sc.world.use_nodes = True; wn = sc.world.node_tree; wn.nodes.clear()
tc = node(wn, 'ShaderNodeTexCoord', (-900, 0)); mpw = node(wn, 'ShaderNodeMapping', (-700, 0))
mpw.inputs['Rotation'].default_value = (0, 0, math.radians(arg('sky-rot', 200.0)))
link(wn, tc.outputs['Generated'], mpw.inputs['Vector'])
env = node(wn, 'ShaderNodeTexEnvironment', (-500, 0)); env.image = img(os.path.join(ASSETS, 'beach_parking_4k.hdr'))
link(wn, mpw.outputs['Vector'], env.inputs['Vector'])
# cool it towards blue hour: less green-grey, a deeper blue above
tint = node(wn, 'ShaderNodeMix', (-250, 0)); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs['Factor'].default_value = 1
link(wn, env.outputs['Color'], tint.inputs['A']); tint.inputs['B'].default_value = (0.62, 0.78, 1.25, 1)
bg = node(wn, 'ShaderNodeBackground', (0, 0)); bg.inputs['Strength'].default_value = SKY
link(wn, tint.outputs['Result'], bg.inputs['Color'])
wo = node(wn, 'ShaderNodeOutputWorld', (200, 0)); link(wn, bg.outputs['Background'], wo.inputs['Surface'])
sc.world.lightgroup = 'sky'
sc.world.cycles.sampling_method = 'MANUAL'; sc.world.cycles.sample_map_resolution = 1024

# ---------------------------------------------------------------- layout (metres). The wall face is the plane y = 0, facing -y.
WALL_X0, WALL_X1, WALL_H = -8.0, 1.45, 3.4
PW, PH = 1.74, 2.61                     # the lightbox face: a large format sheet, half again a six sheet
PX, PZ0 = 0.0, 0.5                      # face centre x, foot height
CAFE_X0 = WALL_X1
WIN = (1.95, 4.45, 0.52, 2.55)          # cafe window x0, x1, z0, z1
CAN = (1.62, 4.85, 2.78, 0.72)          # canopy x0, x1, z, depth
CHAIN = (1.80, -0.58)                   # rain chain x, y
RILL = (-0.86, -0.70)                   # rill y range

def wall_wet(nt, tc, hgt=None):
    # wet everywhere a little, soaked low down (splash-back), in runs under the coping and in streaks
    z = node(nt, 'ShaderNodeSeparateXYZ', (-1250, -950)); link(nt, tc.outputs['Object'], z.inputs['Vector'])
    low = node(nt, 'ShaderNodeMapRange', (-1050, -950)); low.inputs['From Min'].default_value = 0.7; low.inputs['From Max'].default_value = 0.15
    link(nt, z.outputs['Z'], low.inputs['Value'])
    streak = noise_mask(nt, tc, 3.0, 0.5, 0.75, w=(9.0, 9.0, 0.25))
    top = node(nt, 'ShaderNodeMapRange', (-1050, -1100)); top.inputs['From Min'].default_value = WALL_H - 0.6; top.inputs['From Max'].default_value = WALL_H - 0.05
    link(nt, z.outputs['Z'], top.inputs['Value'])
    m1 = node(nt, 'ShaderNodeMath', (-800, -950), operation='MAXIMUM'); link(nt, low.outputs['Result'], m1.inputs[0]); link(nt, streak, m1.inputs[1])
    m2 = node(nt, 'ShaderNodeMath', (-650, -950), operation='MAXIMUM'); link(nt, m1.outputs[0], m2.inputs[0])
    tp = node(nt, 'ShaderNodeMath', (-800, -1100), operation='MULTIPLY'); link(nt, top.outputs['Result'], tp.inputs[0]); link(nt, streak, tp.inputs[1])
    link(nt, tp.outputs[0], m2.inputs[1])
    f = node(nt, 'ShaderNodeMapRange', (-500, -950)); f.inputs['To Min'].default_value = 0.35; f.inputs['To Max'].default_value = 0.95
    link(nt, m2.outputs[0], f.inputs['Value']); return f.outputs['Result']

M_STONE = pbr('sandstone', 'large_sandstone_blocks', 0.62, tint=(1.0, 0.98, 0.95), val=1.15, sat=0.6, rough=(0.5, 0.92), nstr=0.8, wet=wall_wet, acg='Bricks084')
def low(nt, tc, hgt, a, b):
    n = noise_mask(nt, tc, 0.35, 0.3, 0.7, w=(1.0, 1.6, 1.0), detail=3.0)
    m = node(nt, 'ShaderNodeMath', (-700, -800), operation='MULTIPLY_ADD'); link(nt, hgt, m.inputs[0]); m.inputs[1].default_value = -0.6; link(nt, n, m.inputs[2])
    r = node(nt, 'ShaderNodeMapRange', (-550, -800)); r.inputs['From Min'].default_value = a; r.inputs['From Max'].default_value = b
    link(nt, m.outputs[0], r.inputs['Value']); return r.outputs['Result']
def ground_wet(nt, tc, hgt):
    p = low(nt, tc, hgt, 0.0, 0.35)
    f = node(nt, 'ShaderNodeMapRange', (-500, -950)); f.inputs['To Min'].default_value = 0.55; f.inputs['To Max'].default_value = 1.0
    link(nt, p, f.inputs['Value']); return f.outputs['Result']
def puddles(nt, b, tc, hgt):
    # standing water: a mirror in the joints and where the slabs dip, the rest wet stone
    p = low(nt, tc, hgt, 0.3 - arg('pud', 0.0), 0.36 - arg('pud', 0.0))
    w = node(nt, 'ShaderNodeBsdfPrincipled', (0, -400)); w.inputs['Base Color'].default_value = (0.02, 0.022, 0.025, 1)
    w.inputs['Roughness'].default_value = 0.02; w.inputs['IOR'].default_value = 1.33
    ms = node(nt, 'ShaderNodeMixShader', (250, -200)); link(nt, p, ms.inputs['Fac'])
    out = [n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial'][0]
    link(nt, b.outputs['BSDF'], ms.inputs[1]); link(nt, w.outputs['BSDF'], ms.inputs[2]); link(nt, ms.outputs['Shader'], out.inputs['Surface'])
    aov(nt, 'rill', p)
M_GROUND = pbr('paving', 'granite_tile', 0.5, tint=(1.0, 0.97, 0.93), val=0.62, sat=0.8, rough=(0.3, 0.8), nstr=1.2, wet=ground_wet, extra=puddles, acg='PavingStones128')
M_TIMBER = pbr('larch', 'wood_planks_grey', 0.5, tint=(1.0, 0.98, 0.95), val=1.05, sat=0.7, rough=(0.45, 0.85), nstr=1.0,
               wet=lambda nt, tc, h: noise_mask(nt, tc, 2.0, 0.3, 0.8, w=(4.0, 4.0, 0.3)))

def simple(name, col, rough, metal=0.0, spec=0.5, plant=0.0):
    m, nt = mat(name); b = node(nt, 'ShaderNodeBsdfPrincipled')
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    b.inputs['Specular IOR Level'].default_value = spec
    o = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, b.outputs['BSDF'], o.inputs['Surface']); aov(nt, 'plant', plant)
    return m
M_BRONZE = simple('bronze', (0.12, 0.085, 0.06), 0.32, metal=1.0)
M_FRAME = simple('frame', (0.035, 0.037, 0.04), 0.28, metal=0.6)
M_SOIL = simple('soil', (0.02, 0.016, 0.012), 0.6)

# ---------------------------------------------------------------- the wall, its coping, the planting bed, the rill
wall = box('wall', WALL_X0, WALL_X1, 0.0, 0.45, 0.0, WALL_H, M_STONE)
cop = box('coping', WALL_X0, WALL_X1 + 0.02, -0.06, 0.5, WALL_H, WALL_H + 0.1, M_STONE)
# the lightbox is set into the wall: a recess, a slim dark bronze frame, the face
rec = box('recess_cut', PX - PW / 2 - 0.05, PX + PW / 2 + 0.05, -0.1, 0.06, PZ0 - 0.05, PZ0 + PH + 0.05)
md = wall.modifiers.new('cut', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = rec; rec.hide_render = True; rec.hide_viewport = True
FW = 0.03
for nm_, a in (('fl', (PX - PW / 2 - FW - 0.02, PX - PW / 2, 0.0, 0.05, PZ0 - FW, PZ0 + PH + FW)),
               ('fr', (PX + PW / 2, PX + PW / 2 + FW + 0.02, 0.0, 0.05, PZ0 - FW, PZ0 + PH + FW)),
               ('fb', (PX - PW / 2 - FW - 0.02, PX + PW / 2 + FW + 0.02, 0.0, 0.05, PZ0 - FW - 0.02, PZ0)),
               ('ft', (PX - PW / 2 - FW - 0.02, PX + PW / 2 + FW + 0.02, 0.0, 0.05, PZ0 + PH, PZ0 + PH + FW + 0.02))):
    box(nm_, *a[:2], a[2] - 0.035, a[3], *a[4:], M_FRAME)
box('lb_back', PX - PW / 2 - 0.05, PX + PW / 2 + 0.05, 0.05, 0.08, PZ0 - 0.05, PZ0 + PH + 0.05, M_FRAME)

m_face, nt = mat('poster_face')
uvn = node(nt, 'ShaderNodeTexCoord', (-800, 0))
ti = node(nt, 'ShaderNodeTexImage', (-600, 0)); ti.image = img(POSTER); ti.extension = 'EXTEND'
link(nt, uvn.outputs['UV'], ti.inputs['Vector'])
em = node(nt, 'ShaderNodeEmission', (-300, 0)); em.inputs['Strength'].default_value = P_STR
link(nt, ti.outputs['Color'], em.inputs['Color'])
# a sheet of glass over the print: the box glows, and the street reflects in it a little
gl_ = node(nt, 'ShaderNodeBsdfGlossy', (-300, -200)); gl_.inputs['Roughness'].default_value = 0.03; gl_.inputs['Color'].default_value = (0.05, 0.05, 0.05, 1)
ad = node(nt, 'ShaderNodeAddShader', (0, 0)); link(nt, em.outputs['Emission'], ad.inputs[0]); link(nt, gl_.outputs['BSDF'], ad.inputs[1])
o = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, ad.outputs['Shader'], o.inputs['Surface'])
aov(nt, 'face', 1.0); aov(nt, 'plant', 0.0)
FACE_Y = -0.012
face = plane('poster_face', PX - PW / 2, PX + PW / 2, PZ0, PZ0 + PH, FACE_Y, m_face)
face.lightgroup = 'poster'

# a handbill tucked under the frame's right rail: thin card, rain spotted, its free edge curling off the stone
PAPER = arg('paper', '')
RAIL_X = PX + PW / 2 + 0.05                  # the rail's outer edge
CW, CH, CANG = 0.24, 0.33, math.radians(arg('paper-ang', -7.0))
CX0, CZ0 = RAIL_X - 0.012, arg('paper-z', 0.66)   # the card's top left corner, tucked under the rail
def card_pt(u, v):
    # u across from the tucked edge, v down from the top; in the wall plane, turned a little about its corner
    lx, lz = u * CW, -v * CH
    x = CX0 + lx * math.cos(CANG) - lz * math.sin(CANG); z = CZ0 + CH + lx * math.sin(CANG) + lz * math.cos(CANG)
    d = max(0.0, x - RAIL_X) / (CW - 0.012)
    y = -0.0025 - 0.008 * d - arg('curl', 0.055) * d * d - 0.022 * d * v * v
    return (x, y, z)
if PAPER:
    m_pap, nt = mat('handbill')
    tcp = node(nt, 'ShaderNodeTexCoord', (-1200, 0))
    tip = node(nt, 'ShaderNodeTexImage', (-900, 200)); tip.image = img(PAPER); tip.extension = 'EXTEND'
    link(nt, tcp.outputs['UV'], tip.inputs['Vector'])
    # rain spots: round cells soaked darker and glossier, and the foot wicking water up from where it drips
    vo = node(nt, 'ShaderNodeTexVoronoi', (-900, -200)); vo.inputs['Scale'].default_value = 8.0; vo.voronoi_dimensions = '2D'
    link(nt, tcp.outputs['UV'], vo.inputs['Vector'])
    rr = node(nt, 'ShaderNodeMath', (-700, -350), operation='MULTIPLY_ADD'); rr.inputs[1].default_value = 0.26; rr.inputs[2].default_value = 0.06
    sepc = node(nt, 'ShaderNodeSeparateColor', (-700, -500)); link(nt, vo.outputs['Color'], sepc.inputs['Color'])
    keep = node(nt, 'ShaderNodeMath', (-550, -500), operation='GREATER_THAN'); keep.inputs[1].default_value = 0.55; link(nt, sepc.outputs['Green'], keep.inputs[0])
    link(nt, sepc.outputs['Red'], rr.inputs[0])
    sp = node(nt, 'ShaderNodeMath', (-550, -250), operation='LESS_THAN'); link(nt, vo.outputs['Distance'], sp.inputs[0]); link(nt, rr.outputs[0], sp.inputs[1])
    spm = node(nt, 'ShaderNodeMath', (-400, -300), operation='MULTIPLY'); link(nt, sp.outputs[0], spm.inputs[0]); link(nt, keep.outputs[0], spm.inputs[1])
    sepuv = node(nt, 'ShaderNodeSeparateXYZ', (-900, -650)); link(nt, tcp.outputs['UV'], sepuv.inputs['Vector'])
    foot = node(nt, 'ShaderNodeMapRange', (-700, -650)); foot.inputs['From Min'].default_value = 0.16; foot.inputs['From Max'].default_value = 0.0
    link(nt, sepuv.outputs['Y'], foot.inputs['Value'])
    wetp = node(nt, 'ShaderNodeMath', (-250, -400), operation='MAXIMUM'); link(nt, spm.outputs[0], wetp.inputs[0]); link(nt, foot.outputs['Result'], wetp.inputs[1])
    wk = node(nt, 'ShaderNodeMath', (-120, -400), operation='MULTIPLY'); wk.inputs[1].default_value = 0.85; link(nt, wetp.outputs[0], wk.inputs[0])
    dk = node(nt, 'ShaderNodeMix', (-250, 150)); dk.data_type = 'RGBA'; dk.blend_type = 'MULTIPLY'; link(nt, wk.outputs[0], dk.inputs['Factor'])
    link(nt, tip.outputs['Color'], dk.inputs['A']); dk.inputs['B'].default_value = (0.56, 0.58, 0.62, 1)
    ro = node(nt, 'ShaderNodeMapRange', (-80, -200)); ro.inputs['To Min'].default_value = 0.62; ro.inputs['To Max'].default_value = 0.12
    link(nt, wk.outputs[0], ro.inputs['Value'])
    # cockle: the card is not flat where it got wet
    cn = node(nt, 'ShaderNodeTexNoise', (-500, -800)); cn.inputs['Scale'].default_value = 7.0; cn.inputs['Detail'].default_value = 3
    link(nt, tcp.outputs['UV'], cn.inputs['Vector'])
    bpp = node(nt, 'ShaderNodeBump', (-150, -700)); bpp.inputs['Strength'].default_value = 0.12; bpp.inputs['Distance'].default_value = 0.002
    link(nt, cn.outputs['Fac'], bpp.inputs['Height'])
    bp = node(nt, 'ShaderNodeBsdfPrincipled', (100, 0)); link(nt, dk.outputs['Result'], bp.inputs['Base Color'])
    link(nt, ro.outputs['Result'], bp.inputs['Roughness']); link(nt, bpp.outputs['Normal'], bp.inputs['Normal'])
    bp.inputs['Specular IOR Level'].default_value = 0.4
    tl = node(nt, 'ShaderNodeBsdfTranslucent', (100, -300)); link(nt, dk.outputs['Result'], tl.inputs['Color'])
    mxp = node(nt, 'ShaderNodeMixShader', (350, 0)); mxp.inputs['Fac'].default_value = 0.12
    link(nt, bp.outputs['BSDF'], mxp.inputs[1]); link(nt, tl.outputs['BSDF'], mxp.inputs[2])
    o = node(nt, 'ShaderNodeOutputMaterial', (550, 0)); link(nt, mxp.outputs['Shader'], o.inputs['Surface'])
    aov(nt, 'plant', 0.0)
    NU, NV = 24, 32
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UV')
    vs_ = [[bm.verts.new(card_pt(i / NU, j / NV)) for i in range(NU + 1)] for j in range(NV + 1)]
    for j in range(NV):
        for i in range(NU):
            f = bm.faces.new((vs_[j][i], vs_[j + 1][i], vs_[j + 1][i + 1], vs_[j][i + 1]))
            for lp, (a, b) in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))):
                lp[uvl].uv = (a / NU, 1 - b / NV)
    me = bpy.data.meshes.new('handbill'); bm.to_mesh(me); bm.free()
    for p_ in me.polygons: p_.use_smooth = True
    hb = bpy.data.objects.new('handbill', me); sc.collection.objects.link(hb); me.materials.append(m_pap)
    # a little thickness, so its edge catches the light
    so = hb.modifiers.new('thick', 'SOLIDIFY'); so.thickness = 0.0007; so.offset = 1.0

# planting bed along the wall foot (stone kerb), and the rill: a narrow open runnel in the paving
BED_Y = -0.56
box('kerb', WALL_X0, CHAIN[0] + 0.25, BED_Y - 0.08, BED_Y, 0.0, 0.17, M_STONE)
box('bed_soil', WALL_X0, CHAIN[0] + 0.25, BED_Y, 0.0, 0.0, 0.13, M_SOIL)
for nm_, y0, y1 in (('rill_l', RILL[0] - 0.05, RILL[0]), ('rill_r', RILL[1], RILL[1] + 0.05)):
    box(nm_, WALL_X0, CHAIN[0] + 0.12, y0, y1, -0.02, 0.012, M_STONE)
box('rill_bed', WALL_X0, CHAIN[0] + 0.12, RILL[0], RILL[1], -0.07, -0.05, M_SOIL)
m_water, nt = mat('water')
tcw = node(nt, 'ShaderNodeTexCoord', (-900, 0))
nw = node(nt, 'ShaderNodeTexNoise', (-700, 0)); nw.inputs['Scale'].default_value = 14; nw.inputs['Detail'].default_value = 6
mpn = node(nt, 'ShaderNodeMapping', (-850, 0)); mpn.inputs['Scale'].default_value = (0.35, 2.0, 1.0)
link(nt, tcw.outputs['Object'], mpn.inputs['Vector']); link(nt, mpn.outputs['Vector'], nw.inputs['Vector'])
bmp = node(nt, 'ShaderNodeBump', (-450, 0)); bmp.inputs['Strength'].default_value = 0.25; bmp.inputs['Distance'].default_value = 0.01
link(nt, nw.outputs['Fac'], bmp.inputs['Height'])
bw = node(nt, 'ShaderNodeBsdfPrincipled', (-200, 0)); bw.inputs['Base Color'].default_value = (0.01, 0.012, 0.014, 1)
bw.inputs['Roughness'].default_value = 0.02; bw.inputs['IOR'].default_value = 1.33
link(nt, bmp.outputs['Normal'], bw.inputs['Normal'])
o = node(nt, 'ShaderNodeOutputMaterial', (200, 0)); link(nt, bw.outputs['BSDF'], o.inputs['Surface'])
aov(nt, 'rill', 2.0); aov(nt, 'plant', 0.0)
box('rill_water', WALL_X0, CHAIN[0] + 0.12, RILL[0], RILL[1], -0.04, -0.012, m_water)
# the basin under the chain
basin = box('basin', CHAIN[0] - 0.2, CHAIN[0] + 0.2, CHAIN[1] - 0.24, CHAIN[1] + 0.2, 0.0, 0.12, M_STONE)
box('basin_water', CHAIN[0] - 0.16, CHAIN[0] + 0.16, CHAIN[1] - 0.2, CHAIN[1] + 0.16, 0.0, 0.105, m_water)

# ---------------------------------------------------------------- the pavement
gnd = box('ground', -40, 40, -40, 0.0, -0.2, 0.0, M_GROUND)

# ---------------------------------------------------------------- the cafe: larch cladding, a steamed window, a canopy
cafe = box('cafe', CAFE_X0, 9.0, 0.0, 0.5, 0.0, 14.0, M_TIMBER)
wc = box('win_cut', WIN[0], WIN[1], -0.1, 0.7, WIN[2], WIN[3])
md = cafe.modifiers.new('cut', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = wc; wc.hide_render = True; wc.hide_viewport = True
WIN2 = (2.2, 3.75, 3.45, 5.1)
wc2 = box('win2_cut', WIN2[0], WIN2[1], -0.1, 0.2, WIN2[2], WIN2[3])
md = cafe.modifiers.new('cut2', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = wc2; wc2.hide_render = True; wc2.hide_viewport = True

def window_mat(name, strength, seed, upper=False):
    """Warm interior behind steamed glass: a soft room, two pendant lamps, plant shapes; the street reflected on top."""
    m, nt = mat(name)
    tcw = node(nt, 'ShaderNodeTexCoord', (-1400, 0))
    sep = node(nt, 'ShaderNodeSeparateXYZ', (-1200, 0)); link(nt, tcw.outputs['UV'], sep.inputs['Vector'])
    # room light: brighter towards the top, a little warmer low down
    grad = node(nt, 'ShaderNodeMapRange', (-1000, 200)); grad.inputs['To Min'].default_value = 0.45; grad.inputs['To Max'].default_value = 1.0
    link(nt, sep.outputs['Y'], grad.inputs['Value'])
    # pendant lamps: soft blobs
    lamps = None
    for i, (lx, ly) in enumerate(((0.28, 0.78), (0.7, 0.8)) if not upper else ((0.5, 0.75),)):
        d = node(nt, 'ShaderNodeVectorMath', (-1000, -100 - 150 * i), operation='DISTANCE'); link(nt, tcw.outputs['UV'], d.inputs[0])
        d.inputs[1].default_value = (lx, ly, 0)
        f = node(nt, 'ShaderNodeMath', (-850, -100 - 150 * i), operation='MULTIPLY'); f.inputs[1].default_value = -7.0; link(nt, d.outputs['Value'], f.inputs[0])
        e = node(nt, 'ShaderNodeMath', (-700, -100 - 150 * i), operation='EXPONENT'); link(nt, f.outputs[0], e.inputs[0])
        if lamps is None: lamps = e.outputs[0]
        else:
            a = node(nt, 'ShaderNodeMath', (-550, -100), operation='ADD'); link(nt, lamps, a.inputs[0]); link(nt, e.outputs[0], a.inputs[1]); lamps = a.outputs[0]
    # silhouettes: leaves and the backs of chairs, soft, low in the frame
    nn = node(nt, 'ShaderNodeTexNoise', (-1000, -500)); nn.inputs['Scale'].default_value = 3.5; nn.inputs['Detail'].default_value = 3
    nn.noise_dimensions = '4D'; nn.inputs['W'].default_value = seed
    link(nt, tcw.outputs['UV'], nn.inputs['Vector'])
    lowm = node(nt, 'ShaderNodeMapRange', (-850, -650)); lowm.inputs['From Min'].default_value = 0.65; lowm.inputs['From Max'].default_value = 0.2
    link(nt, sep.outputs['Y'], lowm.inputs['Value'])
    sil = node(nt, 'ShaderNodeMapRange', (-850, -500)); sil.inputs['From Min'].default_value = 0.5; sil.inputs['From Max'].default_value = 0.62
    link(nt, nn.outputs['Fac'], sil.inputs['Value'])
    sl = node(nt, 'ShaderNodeMath', (-700, -500), operation='MULTIPLY'); link(nt, sil.outputs['Result'], sl.inputs[0]); link(nt, lowm.outputs['Result'], sl.inputs[1])
    dim = node(nt, 'ShaderNodeMapRange', (-550, -500)); dim.inputs['To Min'].default_value = 1.0; dim.inputs['To Max'].default_value = 0.1
    link(nt, sl.outputs[0], dim.inputs['Value'])
    tot = node(nt, 'ShaderNodeMath', (-450, 100), operation='MULTIPLY'); link(nt, grad.outputs['Result'], tot.inputs[0]); link(nt, dim.outputs['Result'], tot.inputs[1])
    tot2 = node(nt, 'ShaderNodeMath', (-300, 100), operation='MULTIPLY_ADD'); link(nt, lamps, tot2.inputs[0]); tot2.inputs[1].default_value = 0.7; link(nt, tot.outputs[0], tot2.inputs[2])
    em = node(nt, 'ShaderNodeEmission', (-100, 200)); em.inputs['Color'].default_value = (*srgb((1.0, 0.74, 0.45)), 1)
    st = node(nt, 'ShaderNodeMath', (-200, 0), operation='MULTIPLY'); st.inputs[1].default_value = strength; link(nt, tot2.outputs[0], st.inputs[0])
    link(nt, st.outputs[0], em.inputs['Strength'])
    # steamed glass: a dull reflection, cleared where drops have run
    cn = node(nt, 'ShaderNodeTexNoise', (-700, -900)); cn.inputs['Scale'].default_value = 18; cn.inputs['Detail'].default_value = 2
    mpc = node(nt, 'ShaderNodeMapping', (-850, -900)); mpc.inputs['Scale'].default_value = (6.0, 0.25, 1.0); link(nt, tcw.outputs['UV'], mpc.inputs['Vector'])
    link(nt, mpc.outputs['Vector'], cn.inputs['Vector'])
    cr = node(nt, 'ShaderNodeMapRange', (-500, -900)); cr.inputs['From Min'].default_value = 0.55; cr.inputs['From Max'].default_value = 0.7
    cr.inputs['To Min'].default_value = 0.22; cr.inputs['To Max'].default_value = 0.03; link(nt, cn.outputs['Fac'], cr.inputs['Value'])
    g = node(nt, 'ShaderNodeBsdfGlossy', (-100, -300)); g.inputs['Color'].default_value = (0.06, 0.06, 0.06, 1); link(nt, cr.outputs['Result'], g.inputs['Roughness'])
    ad = node(nt, 'ShaderNodeAddShader', (150, 0)); link(nt, em.outputs['Emission'], ad.inputs[0]); link(nt, g.outputs['BSDF'], ad.inputs[1])
    o = node(nt, 'ShaderNodeOutputMaterial', (400, 0)); link(nt, ad.outputs['Shader'], o.inputs['Surface'])
    aov(nt, 'glass', 1.0); aov(nt, 'plant', 0.0)
    return m
def steam_glass():
    m, nt = mat('steam_glass')
    tcw = node(nt, 'ShaderNodeTexCoord', (-1200, 0))
    cn = node(nt, 'ShaderNodeTexNoise', (-900, 0)); cn.inputs['Scale'].default_value = 14; cn.inputs['Detail'].default_value = 3
    mpc = node(nt, 'ShaderNodeMapping', (-1050, 0)); mpc.inputs['Scale'].default_value = (5.0, 0.2, 1.0); link(nt, tcw.outputs['UV'], mpc.inputs['Vector'])
    link(nt, mpc.outputs['Vector'], cn.inputs['Vector'])
    sep = node(nt, 'ShaderNodeSeparateXYZ', (-1050, -250)); link(nt, tcw.outputs['UV'], sep.inputs['Vector'])
    # steam thickest low and at the edges; clear runs where drops have slid down
    cr = node(nt, 'ShaderNodeMapRange', (-700, 0)); cr.inputs['From Min'].default_value = 0.56; cr.inputs['From Max'].default_value = 0.66
    cr.inputs['To Min'].default_value = arg('steam', 0.22); cr.inputs['To Max'].default_value = 0.025; link(nt, cn.outputs['Fac'], cr.inputs['Value'])
    lo_ = node(nt, 'ShaderNodeMapRange', (-700, -250)); lo_.inputs['From Min'].default_value = 0.0; lo_.inputs['From Max'].default_value = 0.5
    lo_.inputs['To Min'].default_value = 0.12; lo_.inputs['To Max'].default_value = 0.0; link(nt, sep.outputs['Y'], lo_.inputs['Value'])
    ad = node(nt, 'ShaderNodeMath', (-500, 0), operation='ADD'); link(nt, cr.outputs['Result'], ad.inputs[0]); link(nt, lo_.outputs['Result'], ad.inputs[1])
    b = node(nt, 'ShaderNodeBsdfPrincipled', (-200, 0)); b.inputs['Transmission Weight'].default_value = 1.0; b.inputs['IOR'].default_value = 1.45
    b.inputs['Base Color'].default_value = (0.92, 0.93, 0.92, 1); link(nt, ad.outputs[0], b.inputs['Roughness'])
    o = node(nt, 'ShaderNodeOutputMaterial', (200, 0)); link(nt, b.outputs['BSDF'], o.inputs['Surface'])
    aov(nt, 'glass', 1.0); aov(nt, 'plant', 0.0)
    return m
win = plane('cafe_window', WIN[0], WIN[1], WIN[2], WIN[3], 0.06, steam_glass())
# the room: warm plaster, a counter with shelves of jars, a table, plants, three pendant lamps
RY = 3.2
M_PLASTER = simple('plaster', srgb((0.78, 0.66, 0.52)), 0.8)
M_OAK = simple('oak', srgb((0.42, 0.28, 0.17)), 0.45)
M_JAR = simple('jar', srgb((0.85, 0.82, 0.74)), 0.25)
box('room_back', WIN[0] - 1.5, WIN[1] + 1.5, RY, RY + 0.1, 0.0, 3.2, M_PLASTER)
box('room_floor', WIN[0] - 1.5, WIN[1] + 1.5, 0.2, RY, -0.05, 0.0, M_OAK)
box('room_ceil', WIN[0] - 1.5, WIN[1] + 1.5, 0.2, RY, 3.0, 3.1, M_PLASTER)
for i, z in enumerate((1.25, 1.75, 2.25)):
    box('shelf', WIN[0] + 0.3, WIN[1] - 0.2, RY - 0.3, RY, z, z + 0.04, M_OAK)
    xj = WIN[0] + 0.35
    while xj < WIN[1] - 0.3:
        hj = rng.uniform(0.12, 0.3); box('jar', xj, xj + rng.uniform(0.07, 0.14), RY - 0.25, RY - 0.12, z + 0.04, z + 0.04 + hj, M_JAR if rng.uniform() < 0.7 else M_OAK)
        xj += rng.uniform(0.14, 0.3)
box('counter', WIN[0] - 0.2, WIN[1] + 0.4, RY - 1.1, RY - 0.5, 0.0, 1.0, M_OAK)
TX = (WIN[0] + WIN[1]) / 2 + 0.35
box('table', TX - 0.45, TX + 0.45, 0.7, 1.3, 0.72, 0.76, M_OAK)
box('table_leg', TX - 0.04, TX + 0.04, 0.96, 1.04, 0.0, 0.72, M_FRAME)
for cx_ in (TX - 0.75, TX + 0.75):
    box('chair_seat', cx_ - 0.2, cx_ + 0.2, 0.8, 1.2, 0.44, 0.48, M_OAK); box('chair_back', cx_ - 0.2, cx_ + 0.2, 1.17, 1.21, 0.48, 0.9, M_OAK)
pots = load('potted_plant_01', ['potted_plant_01_leaves', 'potted_plant_01_pot', 'potted_plant_01_stem'])
pots.update(load('potted_plant_02', ['potted_plant_02_leaves', 'potted_plant_02_pot', 'potted_plant_02_dirt']))
for k_, o_ in pots.items():
    sc.collection.objects.link(o_)
    if k_.startswith('potted_plant_01'): o_.location = (WIN[0] + 0.45, 0.9, 0.0); o_.scale = (1.6, 1.6, 1.6)
    else: o_.location = (WIN[1] - 0.35, 1.6, o_.location.z * 1.3 + 1.0); o_.scale = (1.3, 1.3, 1.3)
box('plant_stand', WIN[1] - 0.6, WIN[1] - 0.1, 1.35, 1.85, 0.0, 1.0, M_OAK)
M_BULB, nt = mat('bulb'); e_ = node(nt, 'ShaderNodeEmission'); e_.inputs['Color'].default_value = (*srgb((1.0, 0.78, 0.5)), 1); e_.inputs['Strength'].default_value = 30
o = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, e_.outputs['Emission'], o.inputs['Surface']); aov(nt, 'plant', 0.0)
for lx_ in (WIN[0] + 0.5, TX, WIN[1] + 0.1):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(lx_, 1.0 if lx_ == TX else 1.8, 2.15), segments=12, ring_count=8)
    b_ = bpy.context.object; b_.data.materials.append(M_BULB); b_.lightgroup = 'warm'
    box('flex', lx_ - 0.004, lx_ + 0.004, (1.0 if lx_ == TX else 1.8) - 0.004, (1.0 if lx_ == TX else 1.8) + 0.004, 2.2, 3.0, M_FRAME)
    pl = bpy.data.lights.new('pend', 'POINT'); pl.energy = arg('pend-w', 60.0); pl.color = srgb((1.0, 0.74, 0.46)); pl.shadow_soft_size = 0.08
    lo_ = bpy.data.objects.new('pend', pl); sc.collection.objects.link(lo_); lo_.location = (lx_, 1.0 if lx_ == TX else 1.8, 2.05); lo_.lightgroup = 'warm'
lw_in = bpy.data.lights.new('room_fill', 'AREA'); lw_in.size = 3.0; lw_in.energy = arg('room-w', 120.0); lw_in.color = srgb((1.0, 0.76, 0.5))
lo_ = bpy.data.objects.new('room_fill', lw_in); sc.collection.objects.link(lo_); lo_.location = (TX, 1.5, 2.95); lo_.lightgroup = 'warm'
win2 = plane('upper_window', WIN2[0], WIN2[1], WIN2[2], WIN2[3], 0.14, window_mat('upper_glass', W_STR * 0.45, 7.0, True)); win2.lightgroup = 'warm'
# window frames: larch, darker with rain
M_DARKWOOD = simple('darkwood', (0.05, 0.045, 0.04), 0.4)
for (x0, x1, z0, z1, y) in ((WIN[0], WIN[1], WIN[2] - 0.06, WIN[2], 0.0), (WIN[0], WIN[1], WIN[3], WIN[3] + 0.05, 0.0),
                           (WIN[0] - 0.05, WIN[0], WIN[2], WIN[3], 0.0), (WIN[1], WIN[1] + 0.05, WIN[2], WIN[3], 0.0),
                           ((WIN[0] + WIN[1]) / 2 - 0.025, (WIN[0] + WIN[1]) / 2 + 0.025, WIN[2], WIN[3], 0.08),
                           (WIN2[0], WIN2[1], WIN2[2] - 0.05, WIN2[2], 0.0), (WIN2[0] - 0.04, WIN2[0], WIN2[2], WIN2[3], 0.0),
                           (WIN2[1], WIN2[1] + 0.04, WIN2[2], WIN2[3], 0.0), (WIN2[0], WIN2[1], WIN2[3], WIN2[3] + 0.04, 0.0)):
    box('wf', x0, x1, y - 0.06, y + 0.12, z0, z1, M_DARKWOOD)
box('sill', WIN[0] - 0.08, WIN[1] + 0.08, -0.16, 0.12, WIN[2] - 0.1, WIN[2] - 0.04, M_STONE)
# canopy: a thin larch roof on bronze brackets, with a planter of ferns on it
can = box('canopy', CAN[0], CAN[1], -CAN[3], 0.0, CAN[2], CAN[2] + 0.07, M_DARKWOOD)
box('canopy_edge', CAN[0], CAN[1], -CAN[3] - 0.02, -CAN[3] + 0.02, CAN[2] - 0.02, CAN[2] + 0.12, M_BRONZE)
for bx in (CAN[0] + 0.15, CAN[1] - 0.15):
    box('bracket', bx - 0.015, bx + 0.015, -CAN[3] + 0.05, 0.0, CAN[2] - 0.35, CAN[2], M_BRONZE)

# rain chain: alternating links from the canopy corner down into the basin
CH_TOP, CH_BOT = CAN[2] - 0.02, 0.11
nl = int((CH_TOP - CH_BOT) / 0.052)
bpy.ops.mesh.primitive_torus_add(major_radius=0.034, minor_radius=0.008, major_segments=16, minor_segments=6)
link0 = bpy.context.object; link0.name = 'chain_link'; link0.data.materials.append(M_BRONZE)
link0.rotation_euler = (math.pi / 2, 0, 0); bpy.ops.object.transform_apply(rotation=True)
for i in range(nl):
    ob = link0.copy(); ob.data = link0.data; sc.collection.objects.link(ob)
    ob.location = (CHAIN[0], CHAIN[1], CH_TOP - 0.03 - i * 0.052)
    ob.rotation_euler = (0, 0, (math.pi / 2) * (i % 2) + 0.1 * math.sin(i))
    ob.scale = (1, 1, 1.25)
bpy.data.objects.remove(link0)

# ---------------------------------------------------------------- assets: plants, the tree, the bench
def wetten(m, plant=1.0):
    # rain on foliage: a glossier leaf, and an AOV so the loop knows what may sway
    if not m or not m.use_nodes: return
    nt = m.node_tree
    for n in nt.nodes:
        if n.bl_idname == 'ShaderNodeBsdfPrincipled':
            r = n.inputs['Roughness']
            if r.is_linked:
                mm = node(nt, 'ShaderNodeMath', (n.location.x - 200, n.location.y - 300), operation='MULTIPLY'); mm.inputs[1].default_value = 0.55
                link(nt, r.links[0].from_socket, mm.inputs[0]); link(nt, mm.outputs[0], r)
            else: r.default_value *= 0.55
            n.inputs['Coat Weight'].default_value = 0.35; n.inputs['Coat Roughness'].default_value = 0.08
    if not any(n.bl_idname == 'ShaderNodeOutputAOV' and n.aov_name == 'plant' for n in nt.nodes): aov(nt, 'plant', plant)

ferns = load('fern_02', ['fern_02_a', 'fern_02_b', 'fern_02_c', 'fern_02_d'])
shrubs = load('shrub_04', ['shrub_04_a_LOD1', 'shrub_04_b_LOD1', 'shrub_04_c_LOD1', 'shrub_04_d_LOD1'])
tree = load('tree_small_02', ['tree_small_02_LOD1', 'tree_small_02_leaves_a_LOD1', 'tree_small_02_leaves_b_LOD1', 'tree_small_02_leaves_c_LOD1'])
bench = load('modular_street_seating', ['legs_double', 'legs_single', 'seat', 'seat_back', 'back_support_l', 'back_support_r', 'crossbar', 'suspended_support_01', 'arm_rest_01'])
for d in (ferns, shrubs, tree, bench):
    for o in d.values():
        for s in o.material_slots: wetten(s.material, 0.0 if d is bench else 1.0)

peri = load('periwinkle_plant', ['periwinkle_plant_01_LOD1', 'periwinkle_plant_02_LOD1'])
cel = load('celandine_01', ['celandine_01_a_LOD0', 'celandine_01_b_LOD0', 'celandine_01_c_LOD1', 'celandine_01_d_LOD1'])
whites = load('shrub_01', ['shrub_01_a_LOD1', 'shrub_01_b_LOD1', 'shrub_01_c_LOD1', 'shrub_01_d_LOD1'])
for d in (peri, cel, whites):
    for o in d.values():
        for sl in o.material_slots: wetten(sl.material)
def pale_blue(m):
    # the periwinkle's pink petals turned to a pale sky blue; its leaves left alone
    nt = m.node_tree
    for n in nt.nodes:
        if n.bl_idname != 'ShaderNodeBsdfPrincipled' or not n.inputs['Base Color'].is_linked: continue
        src = n.inputs['Base Color'].links[0].from_socket
        sh = node(nt, 'ShaderNodeSeparateColor', (n.location.x - 600, n.location.y + 300)); sh.mode = 'HSV'; link(nt, src, sh.inputs['Color'])
        h1 = node(nt, 'ShaderNodeMath', (n.location.x - 450, n.location.y + 400), operation='GREATER_THAN'); h1.inputs[1].default_value = 0.7; link(nt, sh.outputs['Red'], h1.inputs[0])
        s1 = node(nt, 'ShaderNodeMath', (n.location.x - 450, n.location.y + 250), operation='GREATER_THAN'); s1.inputs[1].default_value = 0.12; link(nt, sh.outputs['Green'], s1.inputs[0])
        mk = node(nt, 'ShaderNodeMath', (n.location.x - 300, n.location.y + 300), operation='MULTIPLY'); link(nt, h1.outputs[0], mk.inputs[0]); link(nt, s1.outputs[0], mk.inputs[1])
        mx = node(nt, 'ShaderNodeMix', (n.location.x - 150, n.location.y + 300)); mx.data_type = 'RGBA'; link(nt, mk.outputs[0], mx.inputs['Factor'])
        link(nt, src, mx.inputs['A']); mx.inputs['B'].default_value = (*srgb((0.55, 0.78, 1.0)), 1)
        link(nt, mx.outputs['Result'], n.inputs['Base Color'])
for o in peri.values():
    for sl in o.material_slots: pale_blue(sl.material)
lib = bpy.data.collections.new('lib'); sc.collection.children.link(lib); lib.hide_render = True
def to_lib(objs):
    for o in objs:
        o.location = (0, 0, 0); o.rotation_euler = (0, 0, 0); lib.objects.link(o)
    return list(objs)
FERNS = to_lib(ferns.values()); SHRUBS = to_lib(shrubs.values())
FLOWERS = to_lib(list(peri.values()) + list(cel.values()) + list(whites.values()))
LEAVES = to_lib([tree[k] for k in ('tree_small_02_leaves_a_LOD1', 'tree_small_02_leaves_b_LOD1', 'tree_small_02_leaves_c_LOD1')])

def instance(name, objs, pts, rots, scls, picks):
    """Instance library objects on points through geometry nodes (cheap for thousands)."""
    coll = bpy.data.collections.new(name + '_c'); sc.collection.children.link(coll); coll.hide_render = True
    for o in objs: coll.objects.link(o)
    m = len(pts)
    me = bpy.data.meshes.new(name); me.vertices.add(m); me.vertices.foreach_set('co', np.asarray(pts, np.float32).ravel())
    for an, data, tp in (('rot', rots, 'FLOAT_VECTOR'), ('scl', scls, 'FLOAT_VECTOR'), ('pick', picks, 'INT')):
        at = me.attributes.new(an, tp, 'POINT')
        at.data.foreach_set('vector' if tp == 'FLOAT_VECTOR' else 'value', np.asarray(data, np.float32 if tp != 'INT' else np.int32).ravel())
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
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
    L.new(gi.outputs[0], m2p.inputs['Mesh']); L.new(m2p.outputs['Points'], iop.inputs['Points']); L.new(ci.outputs[0], iop.inputs['Instance'])
    L.new(na['pick'].outputs['Attribute'], iop.inputs['Instance Index']); L.new(na['rot'].outputs['Attribute'], iop.inputs['Rotation'])
    L.new(na['scl'].outputs['Attribute'], iop.inputs['Scale']); L.new(iop.outputs['Instances'], go.inputs[0])
    ob.modifiers.new('inst', 'NODES').node_group = ng
    return ob

TREE_P = (arg('tree-x', -3.25), arg('tree-y', -2.5))
# moss: cushions along the kerb, the coping, the basin and the paving joints at the wall foot
mo = load('moss_01', ['moss_01_%s_LOD1' % c for c in 'abcdefghij'])
for o in mo.values():
    for sl in o.material_slots: wetten(sl.material, 0.0)
MOSS = to_lib(mo.values())
pts, rots, scls, picks = [], [], [], []
def moss_line(x0, x1, y0, y1, z, n, smin=2.0, smax=4.5):
    for i in range(n):
        pts.append((rng.uniform(x0, x1), rng.uniform(y0, y1), z)); rots.append((0, 0, rng.uniform(0, 6.28)))
        s_ = rng.uniform(smin, smax); scls.append((s_, s_, s_ * 0.6)); picks.append(int(rng.integers(0, len(MOSS))))
moss_line(WALL_X0, CHAIN[0] + 0.25, BED_Y - 0.08, BED_Y - 0.03, 0.17, 1600)
moss_line(WALL_X0, WALL_X1, -0.06, 0.0, WALL_H + 0.1, 1400)
moss_line(WALL_X0, CHAIN[0] + 0.1, RILL[0] - 0.06, RILL[0] - 0.04, 0.012, 900, 1.5, 3.0)
moss_line(WALL_X0, CHAIN[0] + 0.1, RILL[1] + 0.04, RILL[1] + 0.06, 0.012, 900, 1.5, 3.0)
moss_line(CHAIN[0] - 0.2, CHAIN[0] + 0.2, CHAIN[1] - 0.24, CHAIN[1] - 0.2, 0.12, 120)
instance('moss', MOSS, pts, rots, scls, picks)
# the planting bed: ferns, with small leafy plants between, kept below the lightbox
PXL, PXR = PX - PW / 2 - 0.08, PX + PW / 2 + 0.08
pts, rots, scls, picks = [], [], [], []
x = WALL_X0 + 0.2
while x < CHAIN[0] + 0.1:
    under = PXL - 0.25 < x < PXR + 0.25
    if under: x += rng.uniform(0.32, 0.55); continue
    s = rng.uniform(0.75, 1.15)
    pts.append((x, rng.uniform(BED_Y + 0.12, -0.2), 0.12)); rots.append((rng.normal(0, 0.05), rng.normal(0, 0.05), rng.uniform(0, 6.28)))
    scls.append((s, s, s * (0.9 if under else 1.1))); picks.append(int(rng.integers(0, 4)))
    x += rng.uniform(0.32, 0.55)
instance('bed_ferns', FERNS, pts, rots, scls, picks)
pts, rots, scls, picks = [], [], [], []
for i in range(140):
    x = rng.uniform(WALL_X0 + 0.1, CHAIN[0] + 0.15)
    pts.append((x, rng.uniform(BED_Y + 0.02, -0.05), 0.12)); rots.append((0, 0, rng.uniform(0, 6.28)))
    s = rng.uniform(1.0, 1.9) if not (PXL - 0.25 < x < PXR + 0.25) else rng.uniform(0.8, 1.15); scls.append((s, s, s)); picks.append(int(rng.integers(0, 4)))
# small plants in the paving joints and at the foot of the cafe
for i in range(0):
    x = rng.uniform(-6, 6); y = rng.uniform(-3.5, -1.0)
    pts.append((x, y, 0.0)); rots.append((0, 0, rng.uniform(0, 6.28))); s = rng.uniform(0.35, 0.7); scls.append((s, s, s)); picks.append(int(rng.integers(0, 4)))
instance('bed_shrubs', SHRUBS, pts, rots, scls, picks)
# flowers along the front of the bed: pale blue periwinkle, white, and a little yellow celandine
pts, rots, scls, picks = [], [], [], []
for i in range(420):
    x = rng.uniform(WALL_X0 + 0.1, CHAIN[0] + 0.15)
    k = int(rng.choice([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], p=[.05, .05, .04, .04, .17, .17, .12, .12, .12, .12]))
    if PXL - 0.25 < x < PXR + 0.25: k = int(rng.integers(0, 4))    # only low celandine under the box (instances sort by name: celandine 0 to 3, periwinkle 4 and 5, white 6 to 9)
    pts.append((x, rng.uniform(BED_Y + 0.02, BED_Y + 0.2), 0.12)); rots.append((rng.normal(0, 0.08), rng.normal(0, 0.08), rng.uniform(0, 6.28)))
    sc_ = rng.uniform(1.2, 1.6) * (1.5 if k < 4 else 1.0) * (0.8 if PXL - 0.25 < x < PXR + 0.25 else 1.0); scls.append((sc_, sc_, sc_)); picks.append(k)
# and a drift of them at the tree's foot
for i in range(60):
    k = int(rng.choice([4, 5, 6, 7, 8, 9, 0, 1]))
    pts.append((TREE_P[0] + rng.uniform(-0.65, 0.65), TREE_P[1] + rng.uniform(-0.65, 0.65), 0.02)); rots.append((0, 0, rng.uniform(0, 6.28)))
    sc_ = rng.uniform(1.0, 1.5); scls.append((sc_, sc_, sc_)); picks.append(k)
instance('bed_flowers', FLOWERS, pts, rots, scls, picks)

# the climber: leafy sprigs laid flat against the stone, falling from the coping in curtains (never on the lightbox)
def curtain(x0, x1, top, depth_fn, n, y=-0.03):
    P, R, Sc, Pk = [], [], [], []
    for i in range(n):
        x = rng.uniform(x0, x1); hang = depth_fn(x)
        z = top - abs(rng.normal(0, 1)) * hang * 0.55
        if PXL - 0.12 < x < PXR + 0.12 and z < PZ0 + PH + 0.1: continue
        if z < 0.2: continue
        P.append((x, y - rng.uniform(0, 0.06), z))
        # leaf cards face the camera, hanging down
        R.append((math.pi / 2 + rng.normal(0, 0.35), rng.normal(0, 0.4), rng.uniform(-0.6, 0.6) + math.pi))
        s = rng.uniform(0.7, 1.15); Sc.append((s, s, s)); Pk.append(int(rng.integers(0, 3)))
    return P, R, Sc, Pk
def hang_l(x): return 0.35 + 1.2 * max(0.0, math.sin((x + 8.0) * 0.55)) * (1.0 if x < -1.2 else 0.25)
P1 = curtain(WALL_X0, -1.0, WALL_H + 0.08, hang_l, 650)
P2 = curtain(PXR + 0.2, WALL_X1, WALL_H + 0.08, lambda x: 0.6, 120)
# along the coping top, spilling over
P3 = ([], [], [], [])
for i in range(700):
    x = rng.uniform(WALL_X0, WALL_X1); P3[0].append((x, rng.uniform(-0.1, 0.45), WALL_H + 0.1 + rng.uniform(0, 0.05)))
    P3[1].append((rng.normal(0, 0.5), rng.normal(0, 0.5), rng.uniform(0, 6.28))); s = rng.uniform(0.9, 1.4); P3[2].append((s, s, s)); P3[3].append(int(rng.integers(0, 3)))
# climbing the cafe corner and over the canopy
P4 = curtain(CAFE_X0 + 0.02, CAFE_X0 + 0.5, 6.0, lambda x: 4.0, 420, y=-0.02)
allp = [sum((p[k] for p in (P1, P2, P3, P4)), []) for k in range(4)]
instance('climber', LEAVES, *allp)
# ferns in the canopy planter
pts = [(rng.uniform(CAN[0] + 0.2, CAN[1] - 0.2), -rng.uniform(0.1, CAN[3] - 0.1), CAN[2] + 0.08) for _ in range(9)]
instance('canopy_ferns', FERNS, pts, [(0, 0, rng.uniform(0, 6.28)) for _ in pts], [(0.8, 0.8, 1.0)] * len(pts), [int(rng.integers(0, 4)) for _ in pts])

# the tree, in its own bed, front left
TREE = (arg('tree-x', -3.25), arg('tree-y', -2.5))
tr = tree['tree_small_02_LOD1']; tr.location = (TREE[0], TREE[1], 0.12); tr.rotation_euler = (0, 0, math.radians(arg('tree-rot', 120.0)))
s = arg('tree-s', 1.15); tr.scale = (s, s, s); sc.collection.objects.link(tr)
box('tree_soil', TREE[0] - 0.68, TREE[0] + 0.68, TREE[1] - 0.68, TREE[1] + 0.68, 0.0, 0.02, M_SOIL)
pts = [(TREE[0] + rng.uniform(-0.6, 0.6), TREE[1] + rng.uniform(-0.6, 0.6), 0.02) for _ in range(5)]
instance('tree_ferns', FERNS, pts, [(0, 0, rng.uniform(0, 6.28)) for _ in pts], [(0.9, 0.9, 1.0)] * len(pts), [int(rng.integers(0, 4)) for _ in pts])
# behind the wall: the garden's trees, rising above the coping
pts, rots, scls = [], [], []
for x in (-6.8, -2.6, 0.9):
    pts.append((x, rng.uniform(2.5, 4.5), 0.0)); rots.append((0, 0, rng.uniform(0, 6.28))); s = rng.uniform(1.25, 1.55); scls.append((s, s, s))
tcoll = bpy.data.collections.new('trees_c'); sc.collection.children.link(tcoll); tcoll.hide_render = True
for p, r, s_ in zip(pts, rots, scls):
    ob = bpy.data.objects.new('gtree', tr.data); sc.collection.objects.link(ob); ob.location = p; ob.rotation_euler = r; ob.scale = s_

# the bench, against the planting bed, left of the box
broot = bpy.data.objects.new('bench', None); sc.collection.objects.link(broot)
for o in bench.values():
    sc.collection.objects.link(o); o.parent = broot
broot.location = (arg('bench-x', -1.75), -1.0, 0.0); broot.rotation_euler = (0, 0, math.radians(arg('bench-rot', 0.0)))

# ---------------------------------------------------------------- beyond: planted terraces stepping back into the mist
def facade_mat(name, seed, lit=0.4):
    m, nt = mat(name)
    tg = node(nt, 'ShaderNodeNewGeometry', (-1600, 0))
    sep = node(nt, 'ShaderNodeSeparateXYZ', (-1450, 0)); link(nt, tg.outputs['Position'], sep.inputs['Vector'])
    u = node(nt, 'ShaderNodeMath', (-1300, 100), operation='ADD'); link(nt, sep.outputs['X'], u.inputs[0]); link(nt, sep.outputs['Y'], u.inputs[1])
    cu = node(nt, 'ShaderNodeMath', (-1150, 100), operation='DIVIDE'); cu.inputs[1].default_value = 2.6; link(nt, u.outputs[0], cu.inputs[0])
    cv = node(nt, 'ShaderNodeMath', (-1150, -50), operation='DIVIDE'); cv.inputs[1].default_value = 3.1; link(nt, sep.outputs['Z'], cv.inputs[0])
    fu = node(nt, 'ShaderNodeMath', (-1000, 100), operation='FRACT'); link(nt, cu.outputs[0], fu.inputs[0])
    fv = node(nt, 'ShaderNodeMath', (-1000, -50), operation='FRACT'); link(nt, cv.outputs[0], fv.inputs[0])
    flu = node(nt, 'ShaderNodeMath', (-1000, 250), operation='FLOOR'); link(nt, cu.outputs[0], flu.inputs[0])
    flv = node(nt, 'ShaderNodeMath', (-1000, -200), operation='FLOOR'); link(nt, cv.outputs[0], flv.inputs[0])
    cmb = node(nt, 'ShaderNodeCombineXYZ', (-850, 250)); link(nt, flu.outputs[0], cmb.inputs['X']); link(nt, flv.outputs[0], cmb.inputs['Y']); cmb.inputs['Z'].default_value = seed
    wn_ = node(nt, 'ShaderNodeTexWhiteNoise', (-700, 250)); wn_.noise_dimensions = '3D'; link(nt, cmb.outputs[0], wn_.inputs['Vector'])
    # the window opening
    wu = node(nt, 'ShaderNodeMath', (-850, 100), operation='COMPARE'); wu.inputs[1].default_value = 0.5; wu.inputs[2].default_value = 0.27; link(nt, fu.outputs[0], wu.inputs[0])
    wv = node(nt, 'ShaderNodeMath', (-850, -50), operation='COMPARE'); wv.inputs[1].default_value = 0.55; wv.inputs[2].default_value = 0.28; link(nt, fv.outputs[0], wv.inputs[0])
    inw = node(nt, 'ShaderNodeMath', (-700, 0), operation='MULTIPLY'); link(nt, wu.outputs[0], inw.inputs[0]); link(nt, wv.outputs[0], inw.inputs[1])
    on = node(nt, 'ShaderNodeMath', (-550, 250), operation='LESS_THAN'); on.inputs[1].default_value = lit; link(nt, wn_.outputs['Value'], on.inputs[0])
    lv = node(nt, 'ShaderNodeMath', (-550, 100), operation='MULTIPLY'); link(nt, on.outputs[0], lv.inputs[0]); link(nt, inw.outputs[0], lv.inputs[1])
    br = node(nt, 'ShaderNodeMapRange', (-550, 400)); br.inputs['To Min'].default_value = 0.4; br.inputs['To Max'].default_value = 1.3
    link(nt, wn_.outputs['Color'], br.inputs['Value'])
    ls = node(nt, 'ShaderNodeMath', (-400, 100), operation='MULTIPLY'); link(nt, lv.outputs[0], ls.inputs[0]); link(nt, br.outputs['Result'], ls.inputs[1])
    est = node(nt, 'ShaderNodeMath', (-250, 100), operation='MULTIPLY'); est.inputs[1].default_value = W_STR * 0.9 * arg('fac-k', 1.0); link(nt, ls.outputs[0], est.inputs[0])
    em = node(nt, 'ShaderNodeEmission', (-100, 250)); em.inputs['Color'].default_value = (*srgb((1.0, 0.72, 0.46)), 1); link(nt, est.outputs[0], em.inputs['Strength'])
    # planted facade: green hangs over pale render in bands, thicker on the terraces
    gn = node(nt, 'ShaderNodeTexNoise', (-850, -400)); gn.inputs['Scale'].default_value = 0.6; gn.inputs['Detail'].default_value = 5; gn.noise_dimensions = '4D'; gn.inputs['W'].default_value = seed
    link(nt, tg.outputs['Position'], gn.inputs['Vector'])
    gm = node(nt, 'ShaderNodeMapRange', (-700, -400)); gm.inputs['From Min'].default_value = 0.48; gm.inputs['From Max'].default_value = 0.6; link(nt, gn.outputs['Fac'], gm.inputs['Value'])
    gmx = node(nt, 'ShaderNodeMath', (-550, -400), operation='MULTIPLY'); link(nt, gm.outputs['Result'], gmx.inputs[0])
    nwin = node(nt, 'ShaderNodeMath', (-700, -550), operation='SUBTRACT'); nwin.inputs[0].default_value = 1.0; link(nt, inw.outputs[0], nwin.inputs[1])
    link(nt, nwin.outputs[0], gmx.inputs[1])
    col = node(nt, 'ShaderNodeMix', (-350, -200)); col.data_type = 'RGBA'; link(nt, gmx.outputs[0], col.inputs['Factor'])
    col.inputs['A'].default_value = (0.55, 0.55, 0.53, 1); col.inputs['B'].default_value = (0.05, 0.09, 0.035, 1)
    col2 = node(nt, 'ShaderNodeMix', (-200, -200)); col2.data_type = 'RGBA'; link(nt, inw.outputs[0], col2.inputs['Factor'])
    link(nt, col.outputs['Result'], col2.inputs['A']); col2.inputs['B'].default_value = (0.02, 0.02, 0.025, 1)
    b = node(nt, 'ShaderNodeBsdfPrincipled', (0, -200)); link(nt, col2.outputs['Result'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.55
    ad = node(nt, 'ShaderNodeAddShader', (200, 0)); link(nt, em.outputs['Emission'], ad.inputs[0]); link(nt, b.outputs['BSDF'], ad.inputs[1])
    o = node(nt, 'ShaderNodeOutputMaterial', (400, 0)); link(nt, ad.outputs['Shader'], o.inputs['Surface'])
    aov(nt, 'plant', 0.0)
    return m
FAC = [facade_mat('facade%d' % i, float(i) * 3.7, lit=0.38 + 0.08 * i + arg('lit-k', 0.0)) for i in range(3)]
M_SLAB = simple('slab', (0.5, 0.5, 0.49), 0.6)
terr_green = []
for row, (y0, hmin, hmax, xs) in enumerate(((16.0, 8.0, 13.0, (-34, 30)), (30.0, 14.0, 22.0, (-50, 50)), (52.0, 22.0, 34.0, (-80, 80)))):
    x = xs[0]
    while x < xs[1]:
        w_ = rng.uniform(8, 15); h_ = rng.uniform(hmin, hmax)
        if row == 0 and -4.0 < x + w_ / 2 < 3.0: h_ *= 0.55      # a lower block in the middle opens a slice of sky
        steps = int(rng.integers(2, 4)); z = 0.0; yb = y0 + rng.uniform(-2, 2)
        for k in range(steps):
            hz = h_ / steps
            box('bld', x, x + w_, yb + k * 2.2, yb + 9, z, z + hz, FAC[row]).lightgroup = 'warm'
            # a terrace edge planted along its length
            box('terrace', x, x + w_, yb + k * 2.2 - 0.6, yb + k * 2.2 + 0.4, z + hz - 0.15, z + hz, M_SLAB)
            terr_green.append((x, x + w_, yb + k * 2.2 - 0.3, z + hz))
            z += hz
        x += w_ + rng.uniform(1.5, 5.0)
# greenery on the terraces: ferns scaled up into shrubs and hanging plants
pts, rots, scls, picks = [], [], [], []
for (x0, x1, y, z) in terr_green:
    n = int((x1 - x0) * 1.3)
    for i in range(n):
        pts.append((rng.uniform(x0, x1), y + rng.uniform(-0.2, 0.3), z)); rots.append((0, 0, rng.uniform(0, 6.28)))
        s = rng.uniform(1.8, 3.2); scls.append((s, s, s)); picks.append(int(rng.integers(0, 4)))
instance('terrace_green', FERNS, pts, rots, scls, picks)
# street lamps along the lane beyond the wall: warm, low, soft in the mist
M_LAMP, nt = mat('lamp'); e_ = node(nt, 'ShaderNodeEmission'); e_.inputs['Color'].default_value = (*srgb((1.0, 0.78, 0.55)), 1); e_.inputs['Strength'].default_value = 40
o = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, e_.outputs['Emission'], o.inputs['Surface']); aov(nt, 'plant', 0.0)
for lx in (-22, -11, 0.5, 12, 24):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(lx, 11.0, 4.2), segments=12, ring_count=8)
    lo = bpy.context.object; lo.data.materials.append(M_LAMP); lo.lightgroup = 'warm'
    box('post', lx - 0.03, lx + 0.03, 10.97, 11.03, 0.0, 4.1, M_FRAME)
    if arg('lamp-w', 0.0) > 0:
        # each lamp lights the mist around it, a soft warm halo in the lane
        lpl = bpy.data.lights.new('lane', 'POINT'); lpl.energy = arg('lamp-w', 0.0); lpl.color = srgb((1.0, 0.74, 0.5)); lpl.shadow_soft_size = 0.3
        lpo = bpy.data.objects.new('lane', lpl); sc.collection.objects.link(lpo); lpo.location = (lx, 10.8, 4.0); lpo.lightgroup = 'warm'

# ---------------------------------------------------------------- lights
M_BOL, nt = mat('bollard_glow'); e_ = node(nt, 'ShaderNodeEmission'); e_.inputs['Color'].default_value = (*srgb((1.0, 0.8, 0.56)), 1); e_.inputs['Strength'].default_value = arg('bollard', 25.0)
o = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, e_.outputs['Emission'], o.inputs['Surface']); aov(nt, 'plant', 0.0)
for bx in (-3.0, 1.15):
    box('bollard', bx - 0.06, bx + 0.06, -0.32, -0.2, 0.0, 0.66, M_BRONZE)
    g_ = box('bollard_lens', bx - 0.045, bx + 0.045, -0.325, -0.31, 0.48, 0.6, M_BOL); g_.lightgroup = 'warm'
    pl = bpy.data.lights.new('bollard', 'SPOT'); pl.energy = arg('bollard-w', 9.0); pl.color = srgb((1.0, 0.78, 0.52)); pl.spot_size = math.radians(150); pl.spot_blend = 0.8; pl.shadow_soft_size = 0.04
    lo = bpy.data.objects.new('bollard', pl); sc.collection.objects.link(lo); lo.location = (bx, -0.36, 0.54); lo.rotation_euler = (math.radians(-55), 0, 0); lo.lightgroup = 'warm'
# the cafe throws its light out onto the paving through the glass (a soft panel just inside)
lw = bpy.data.lights.new('cafe_spill', 'AREA'); lw.shape = 'RECTANGLE'; lw.size = WIN[1] - WIN[0]; lw.size_y = WIN[3] - WIN[2]
lw.energy = arg('cafe-w', 220.0); lw.color = srgb((1.0, 0.72, 0.48)); lw.spread = math.radians(140)
lo = bpy.data.objects.new('cafe_spill', lw); sc.collection.objects.link(lo)
lo.location = ((WIN[0] + WIN[1]) / 2, -0.03, (WIN[2] + WIN[3]) / 2); lo.rotation_euler = (math.radians(90), 0, 0); lo.lightgroup = 'warm'
lo.visible_camera = False; lo.visible_glossy = False; lo.visible_transmission = False

M_HAZE, nt = mat('haze')
vs = node(nt, 'ShaderNodeVolumeScatter', (0, 0)); vs.inputs['Anisotropy'].default_value = 0.55; vs.inputs['Color'].default_value = (0.9, 0.93, 1.0, 1)
lp = node(nt, 'ShaderNodeLightPath', (-400, 0)); dn = node(nt, 'ShaderNodeMath', (-200, 0), operation='MULTIPLY'); dn.inputs[1].default_value = arg('haze', 0.006)
link(nt, lp.outputs['Is Camera Ray'], dn.inputs[0]); link(nt, dn.outputs[0], vs.inputs['Density'])
o = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, vs.outputs['Volume'], o.inputs['Volume'])
if arg('haze', 0.006) > 0:
    hz = box('haze', -12, 12, -7.2, 9.0, -0.3, 9.0, M_HAZE); hz.visible_shadow = False
cy.volume_step_rate = arg('vstep', 4.0); cy.volume_max_steps = 256
# ---------------------------------------------------------------- camera: eye height, square on, verticals straight
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam_d.sensor_fit = 'HORIZONTAL'; cam_d.sensor_width = 36; cam_d.lens = arg('lens', 27.0)
CAM = (arg('cam-x', 0.1), -arg('dist', 7.4), arg('cam-h', 1.55))
cam.location = CAM; cam.rotation_euler = (math.pi / 2, 0, 0)
cam_d.shift_y = arg('shift', 0.06); cam_d.shift_x = arg('shift-x', 0.0)
cam_d.clip_start = 0.05; cam_d.clip_end = 400
cam_d.dof.use_dof = True; cam_d.dof.focus_distance = -CAM[1] - 0.02; cam_d.dof.aperture_fstop = arg('fstop', 4.0)

# ---------------------------------------------------------------- compositor: mist, bloom; light groups and data to EXR
sc.use_nodes = True; ct = sc.node_tree; ct.nodes.clear()
rl = ct.nodes.new('CompositorNodeRLayers'); comp = ct.nodes.new('CompositorNodeComposite')
FOG = srgb((0.30, 0.38, 0.52)); FOG = tuple(v * arg('fog-l', 0.10) for v in FOG)
def fogged(sock):
    mr = ct.nodes.new('CompositorNodeMapRange'); mr.inputs['From Min'].default_value = 0; mr.inputs['From Max'].default_value = 1
    mr.inputs['To Min'].default_value = 0; mr.inputs['To Max'].default_value = arg('fog', 0.82); mr.use_clamp = True
    ct.links.new(rl.outputs['Mist'], mr.inputs['Value'])
    mx = ct.nodes.new('CompositorNodeMixRGB'); ct.links.new(mr.outputs['Value'], mx.inputs['Fac'])
    ct.links.new(sock, mx.inputs[1]); mx.inputs[2].default_value = (*FOG, 1); return mx.outputs['Image']
gl = ct.nodes.new('CompositorNodeGlare'); gl.glare_type = 'BLOOM'; gl.quality = 'HIGH'
gl.inputs['Threshold'].default_value = 0.8; gl.inputs['Smoothness'].default_value = 0.6
gl.inputs['Strength'].default_value = arg('bloom', 0.35); gl.inputs['Size'].default_value = 0.8
ct.links.new(fogged(rl.outputs['Image']), gl.inputs['Image']); ct.links.new(gl.outputs['Image'], comp.inputs['Image'])
if EXR:
    vl.use_pass_diffuse_color = True
    fo = ct.nodes.new('CompositorNodeOutputFile'); fo.base_path = EXR; fo.format.file_format = 'OPEN_EXR_MULTILAYER'
    fo.format.color_depth = '16'; fo.format.exr_codec = 'DWAA'
    fo.file_slots.clear()
    def den(sock):
        d = ct.nodes.new('CompositorNodeDenoise'); d.prefilter = 'ACCURATE'
        ct.links.new(sock, d.inputs['Image'])
        ct.links.new(rl.outputs['Denoising Normal'], d.inputs['Normal']); ct.links.new(rl.outputs['Denoising Albedo'], d.inputs['Albedo'])
        return d.outputs['Image']
    vl.cycles.denoising_store_passes = True
    for g in ('sky', 'poster', 'warm'):
        fo.file_slots.new(g); ct.links.new(den(rl.outputs['Combined_' + g]), fo.inputs[g])
    for nm_ in ('Mist', 'Depth', 'plant', 'wet', 'rill', 'face', 'glass'):
        fo.file_slots.new(nm_); ct.links.new(rl.outputs[nm_], fo.inputs[nm_])

# ---------------------------------------------------------------- where the face lands on the frame
def corners():
    from bpy_extras.object_utils import world_to_camera_view
    bpy.context.view_layer.update()
    out = {}
    for k, (x, z) in (('tl', (PX - PW / 2, PZ0 + PH)), ('tr', (PX + PW / 2, PZ0 + PH)), ('br', (PX + PW / 2, PZ0)), ('bl', (PX - PW / 2, PZ0))):
        v = world_to_camera_view(sc, cam, Vector((x, FACE_Y, z)))
        out[k] = [v.x * W, (1 - v.y) * H]
    if PAPER:
        # the handbill's outline where it shows (beyond the rail), for the page's button and hint
        ring = [(i / 12, 0.0) for i in range(13)] + [(1.0, j / 12) for j in range(1, 13)] + [(1 - i / 12, 1.0) for i in range(1, 13)] + [(0.0, 1 - j / 12) for j in range(1, 12)]
        pts = []
        for u, v in ring:
            q = card_pt(u, v); q = (max(q[0], RAIL_X), q[1], q[2])
            c_ = world_to_camera_view(sc, cam, Vector(q)); pts.append([round(c_.x * W, 1), round((1 - c_.y) * H, 1)])
        out['paper'] = pts
    out['res'] = [W, H]
    return out
if CORNERS:
    json.dump(corners(), open(CORNERS, 'w'), indent=1)
if '--dry' in argv:
    print('DRY_OK', corners()); sys.exit(0)
if arg('border', ''):
    b_ = [float(v) for v in arg('border', '').split(',')]
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_max_x, sc.render.border_min_y, sc.render.border_max_y = b_
t0 = time.time()
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('RENDER_SECONDS', round(time.time() - t0, 1))
