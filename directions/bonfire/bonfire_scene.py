# Bonfire: the Break as a carved stone on a high grassy crest at night, over a plain of campfires.
# Blender 4.5 LTS, Cycles CPU. Poly Haven and ambientCG CC0 assets (see credits in the report).
#
# Run:  blender -b -P bonfire_scene.py -- --ph <assets/polyhaven> --acg <assets/ambientcg> --out <file.png>
#   --res 1600x900  --samples 256  --time 420 (seconds; 0 means no limit)
#   --sky-rot 60,0,70  (the night sky's rotation, degrees XYZ)
import bpy, bmesh, math, json, os, re, sys, time
import numpy as np
from mathutils import Vector, Matrix, Euler

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    k = '--' + name
    return type(default)(argv[argv.index(k) + 1]) if k in argv else default

PH = arg('ph', '')
ACG = arg('acg', '')
OUT = arg('out', '/tmp/bonfire.png')
RES = arg('res', '480x270')
SAMPLES = arg('samples', 24)
TIME = arg('time', 0.0)
EXPO = arg('exposure', 0.0)
D = arg('density', 1.0)
GEO = json.load(open(arg('geometry', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'break-geometry.json'))))
rng = np.random.default_rng(arg('seed', 11))

def srgb2lin(c): return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92
def blackbody(k):
    # a close fit to the blackbody locus (Tanner Helland), returned in linear RGB, normalised
    t = k / 100.0
    r = 255.0 if t <= 66 else 329.698727446 * (t - 60) ** -0.1332047592
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * (t - 60) ** -0.0755148492
    b = 255.0 if t >= 66 else (0.0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    c = [srgb2lin(min(max(v, 0), 255) / 255) for v in (r, g, b)]
    m = max(c); return tuple(v / m for v in c)

# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
W, H = (int(v) for v in RES.split('x'))
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.resolution_percentage = 100
sc.render.engine = 'CYCLES'
cy = sc.cycles
cy.device = 'CPU'; cy.samples = SAMPLES
cy.use_adaptive_sampling = True; cy.adaptive_threshold = arg('adaptive', 0.03)
cy.time_limit = TIME
cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'; cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
cy.max_bounces = 8; cy.diffuse_bounces = 2; cy.glossy_bounces = 2
cy.transmission_bounces = 8; cy.transparent_max_bounces = 24; cy.volume_bounces = 0
cy.caustics_reflective = False; cy.caustics_refractive = False
cy.blur_glossy = 1.0; cy.use_light_tree = True
cy.sample_clamp_indirect = 4.0
sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'None'
sc.view_settings.exposure = EXPO
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_depth = '16'; sc.render.image_settings.color_mode = 'RGB'

# ---------------------------------------------------------------- node helpers
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
def math_(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: link(nt, v, n.inputs[i])
    return n.outputs[0]
def mrange(nt, v, a, b, c=0.0, d=1.0, interp='LINEAR'):
    n = nt.nodes.new('ShaderNodeMapRange'); n.interpolation_type = interp
    n.inputs['From Min'].default_value = a; n.inputs['From Max'].default_value = b
    n.inputs['To Min'].default_value = c; n.inputs['To Max'].default_value = d
    link(nt, v, n.inputs['Value']); return n.outputs['Result']
def camera_only(ob):
    ob.visible_diffuse = False; ob.visible_glossy = False; ob.visible_transmission = False
    ob.visible_volume_scatter = False; ob.visible_shadow = False

# ---------------------------------------------------------------- terrain: a high grassy crest falling to a vast plain
HT = arg('hill', 120.0)        # the crest stands this high over the plain (metres)
CREST = arg('crest', 14.0)    # distance from the camera to the crest line
RISE = arg('rise', -2.0)      # the ground rises this much from the camera to the crest
LDROP = arg('drop', 380.0)    # the hillside runs down over this distance
def smooth(t): t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)
def height(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    yc = CREST + 0.0028 * x ** 2 - 0.02 * x
    up = np.clip((y + 6) / (yc + 6), 0, 1) ** 1.4
    t = (y - yc) / LDROP
    z = HT + RISE * up - (HT + RISE) * smooth(t)
    # small humps and hollows on the hill
    z += (0.10 * np.sin(x * 0.9 + 1.3) * np.sin(y * 0.7) + 0.06 * np.sin(x * 2.3 + y * 1.7)) * (1 - smooth(t * 3))
    z += (1.8 * np.sin(x * 0.031 + 0.4) + 1.2 * np.sin(y * 0.022 - x * 0.012)) * smooth((t - 0.15) * 2)
    # the plain: long, low swells
    pl = smooth((t - 0.8) * 4)
    z += pl * (2.5 * np.sin(x / 260 + 1) * np.sin(y / 410) + 1.4 * np.sin((x + y) / 170) + 0.6 * np.sin(x / 47 - y / 61))
    # far hills at the edge of the plain, for one more layer of depth
    z += arg('ridge', 0.0) * smooth((y - 7500) / 4500) * (0.55 + 0.3 * np.sin(x / 1300 + 0.6) + 0.15 * np.sin(x / 430 + 2))
    return z

AZ = math.radians(58)
NR, NA = arg('rings', 440), arg('segs', 380)
r_ = 0.25 * (16000 / 0.25) ** (np.arange(NR) / (NR - 1))
a_ = np.linspace(-AZ, AZ, NA)
RR, AA = np.meshgrid(r_, a_, indexing='ij')
GX = RR * np.sin(AA); GY = RR * np.cos(AA); GZ = height(GX, GY)
me = bpy.data.meshes.new('terrain')
verts = np.stack([GX, GY, GZ], -1).reshape(-1, 3).astype(np.float32)
ii, jj = np.meshgrid(np.arange(NR - 1), np.arange(NA - 1), indexing='ij')
v0 = (ii * NA + jj).ravel()
quads = np.stack([v0, v0 + 1, v0 + NA + 1, v0 + NA], 1)
me.vertices.add(len(verts)); me.vertices.foreach_set('co', verts.ravel())
me.loops.add(quads.size); me.loops.foreach_set('vertex_index', quads.ravel().astype(np.int32))
me.polygons.add(len(quads)); me.polygons.foreach_set('loop_start', np.arange(0, quads.size, 4, dtype=np.int32))
me.update(calc_edges=True)
me.polygons.foreach_set('use_smooth', np.ones(len(quads), bool))
terrain = bpy.data.objects.new('terrain', me); sc.collection.objects.link(terrain)

# ground material: two scans blended by noise in world space, faded into the night haze by distance
HAZE = tuple(arg('haze-k', 2.4) * v for v in (0.0060, 0.0098, 0.0185))
m_g, nt = mat('ground')
gpos = node(nt, 'ShaderNodeNewGeometry', (-1500, 0))
mpp = node(nt, 'ShaderNodeMapping', (-1300, 0)); mpp.inputs['Scale'].default_value = (0.45, 0.45, 0.45)
link(nt, gpos.outputs['Position'], mpp.inputs['Vector'])
gn_ = node(nt, 'ShaderNodeTexNoise', (-1100, 600)); gn_.inputs['Scale'].default_value = 0.08; gn_.inputs['Detail'].default_value = 4
link(nt, gpos.outputs['Position'], gn_.inputs['Vector'])
gnr = mrange(nt, gn_.outputs['Fac'], 0.42, 0.58)
def gtex(path, nc):
    t = node(nt, 'ShaderNodeTexImage'); t.image = img(path, nc); link(nt, mpp.outputs['Vector'], t.inputs['Vector']); return t.outputs['Color']
def gmix(a, b):
    mx_ = node(nt, 'ShaderNodeMix'); mx_.data_type = 'RGBA'
    link(nt, gnr, mx_.inputs['Factor']); link(nt, a, mx_.inputs['A']); link(nt, b, mx_.inputs['B']); return mx_.outputs['Result']
sg = os.path.join(PH, 'sparse_grass'); g2 = os.path.join(ACG, 'Ground037')
gcol = gmix(gtex(os.path.join(sg, 'sparse_grass_diff_2k.jpg'), False), gtex(os.path.join(g2, 'Ground037_2K-JPG_Color.jpg'), False))
grou = gmix(gtex(os.path.join(sg, 'sparse_grass_rough_2k.jpg'), True), gtex(os.path.join(g2, 'Ground037_2K-JPG_Roughness.jpg'), True))
gnor = gmix(gtex(os.path.join(sg, 'sparse_grass_nor_gl_2k.jpg'), True), gtex(os.path.join(g2, 'Ground037_2K-JPG_NormalGL.jpg'), True))
hsv = node(nt, 'ShaderNodeHueSaturation'); hsv.inputs['Saturation'].default_value = 0.8; hsv.inputs['Value'].default_value = 0.8
link(nt, gcol, hsv.inputs['Color'])
nmg = node(nt, 'ShaderNodeNormalMap'); link(nt, gnor, nmg.inputs['Color'])
bg_ = node(nt, 'ShaderNodeBsdfPrincipled', (-100, 0))
# far off, the scans hand over to their own average colour so the plain never shimmers with tiling
lpf = node(nt, 'ShaderNodeLightPath')
farf = mrange(nt, lpf.outputs['Ray Length'], 120.0, 700.0)
gfar = node(nt, 'ShaderNodeMix'); gfar.data_type = 'RGBA'; link(nt, farf, gfar.inputs['Factor'])
link(nt, hsv.outputs['Color'], gfar.inputs['A']); gfar.inputs['B'].default_value = (0.03, 0.029, 0.024, 1)
link(nt, gfar.outputs['Result'], bg_.inputs['Base Color']); link(nt, grou, bg_.inputs['Roughness'])
link(nt, nmg.outputs['Normal'], bg_.inputs['Normal'])
lp = node(nt, 'ShaderNodeLightPath', (-400, 500))
LF, FMAX = arg('fog-l', 4200.0), arg('fog-max', 1.0)
e1 = math_(nt, 'DIVIDE', lp.outputs['Ray Length'], -LF); e2 = math_(nt, 'EXPONENT', e1)
fogf = math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, e2), FMAX)
fogf = math_(nt, 'MULTIPLY', fogf, lp.outputs['Is Camera Ray'])
hz = node(nt, 'ShaderNodeEmission'); hz.inputs['Color'].default_value = tuple(arg('hor-k', 1.6) * v for v in HAZE) + (1,)   # far off, the plain melts into the horizon's own colour; hz.inputs['Strength'].default_value = 1.0
mx = node(nt, 'ShaderNodeMixShader', (200, 0))
link(nt, fogf, mx.inputs['Fac']); link(nt, bg_.outputs['BSDF'], mx.inputs[1]); link(nt, hz.outputs['Emission'], mx.inputs[2])
o = node(nt, 'ShaderNodeOutputMaterial', (400, 0)); link(nt, mx.outputs['Shader'], o.inputs['Surface'])
me.materials.append(m_g)

# ---------------------------------------------------------------- the night sky: a real HDRI, rotated, cleaned, with fine stars over it
HDRI = arg('hdri', os.path.join(PH, 'rogland_clear_night', 'rogland_clear_night_4k.hdr'))   # pass the starless version made by starless.py
ROT = [math.radians(float(v)) for v in arg('sky-rot', '45,0,270').split(',')]
wld = bpy.data.worlds.new('sky'); sc.world = wld; wld.use_nodes = True
wn = wld.node_tree; wn.nodes.clear()
tc = node(wn, 'ShaderNodeTexCoord', (-1400, 0))
mp = node(wn, 'ShaderNodeMapping', (-1200, 0)); mp.vector_type = 'POINT'
mp.inputs['Rotation'].default_value = ROT
link(wn, tc.outputs['Generated'], mp.inputs['Vector'])
env = node(wn, 'ShaderNodeTexEnvironment', (-1000, 0)); env.image = img(HDRI)
# starless.py writes its HDR through Blender's sRGB encode, so it is read back as sRGB to stay linear
if 'starless' in os.path.basename(HDRI): env.image.colorspace_settings.name = 'sRGB'
link(wn, mp.outputs['Vector'], env.inputs['Vector'])
# lift off the airglow so the night is clean, then cool it
FLOOR, GAIN = arg('sky-floor', 0.14), arg('sky-gain', 0.2)
sub = node(wn, 'ShaderNodeVectorMath', operation='SUBTRACT'); sub.inputs[1].default_value = (FLOOR,) * 3
link(wn, env.outputs['Color'], sub.inputs[0])
mxv = node(wn, 'ShaderNodeVectorMath', operation='MAXIMUM'); mxv.inputs[1].default_value = (0, 0, 0)
link(wn, sub.outputs['Vector'], mxv.inputs[0])
tnt = node(wn, 'ShaderNodeVectorMath', operation='MULTIPLY'); tnt.inputs[1].default_value = (GAIN * 0.82, GAIN * 0.92, GAIN * 1.12)
link(wn, mxv.outputs['Vector'], tnt.inputs[0])
# sky gradient: a deep blue zenith lifting to a hazy band at the horizon
dz = node(wn, 'ShaderNodeSeparateXYZ'); link(wn, tc.outputs['Generated'], dz.inputs['Vector'])
zc = math_(wn, 'MAXIMUM', dz.outputs['Z'], 0.0)
band = math_(wn, 'EXPONENT', math_(wn, 'DIVIDE', zc, -arg('band', 0.12)))
grad = node(wn, 'ShaderNodeMix'); grad.data_type = 'RGBA'
link(wn, band, grad.inputs['Factor'])
grad.inputs['A'].default_value = tuple(arg('zen-k', 1.0) * v for v in (0.0016, 0.0030, 0.0072)) + (1,)
grad.inputs['B'].default_value = tuple(arg('hor-k', 1.6) * v for v in HAZE) + (1,)   # the horizon glows a little brighter than the far plain
addc = node(wn, 'ShaderNodeVectorMath', operation='ADD')
link(wn, tnt.outputs['Vector'], addc.inputs[0]); link(wn, grad.outputs['Result'], addc.inputs[1])
# fine stars for camera rays, drawn crisp over the starless HDRI: in a few Voronoi cells a point of light,
# more of them where the Milky Way is bright
lpw = node(wn, 'ShaderNodeLightPath')
lum = node(wn, 'ShaderNodeRGBToBW'); link(wn, tnt.outputs['Vector'], lum.inputs['Color'])
def starfield(scale, radius, gain, pw, base_p):
    vo = node(wn, 'ShaderNodeTexVoronoi'); vo.voronoi_dimensions = '3D'; vo.feature = 'F1'
    vo.inputs['Scale'].default_value = scale; vo.inputs['Randomness'].default_value = 1.0
    link(wn, mp.outputs['Vector'], vo.inputs['Vector'])
    sep = node(wn, 'ShaderNodeSeparateColor'); link(wn, vo.outputs['Color'], sep.inputs['Color'])
    pt = mrange(wn, vo.outputs['Distance'], 0.0, radius, 1.0, 0.0, 'SMOOTHSTEP')
    br = math_(wn, 'POWER', sep.outputs['Red'], pw)
    prob = math_(wn, 'ADD', base_p, math_(wn, 'MULTIPLY', lum.outputs['Val'], arg('mw-stars', 40.0)), clamp=True)
    keep = math_(wn, 'LESS_THAN', sep.outputs['Blue'], prob)
    st = math_(wn, 'MULTIPLY', math_(wn, 'MULTIPLY', math_(wn, 'MULTIPLY', pt, br), keep), gain)
    return st, sep
s1, sep = starfield(arg('star-scale', 420.0), arg('star-r', 0.14), arg('stars', 5.0), 7.0, 0.35)
s2, _ = starfield(arg('star-scale', 420.0) * 2.3, arg('star-r', 0.14) * 1.2, arg('stars', 5.0) * 0.12, 3.0, 0.25)
st = math_(wn, 'ADD', s1, s2)
st = math_(wn, 'MULTIPLY', st, lpw.outputs['Is Camera Ray'])
st = math_(wn, 'MULTIPLY', st, mrange(wn, dz.outputs['Z'], 0.0, 0.1))
stc = node(wn, 'ShaderNodeMix'); stc.data_type = 'RGBA'; link(wn, sep.outputs['Green'], stc.inputs['Factor'])
stc.inputs['A'].default_value = (1.0, 0.86, 0.72, 1); stc.inputs['B'].default_value = (0.75, 0.86, 1.0, 1)
stv = node(wn, 'ShaderNodeVectorMath', operation='SCALE'); link(wn, stc.outputs['Result'], stv.inputs[0]); link(wn, st, stv.inputs['Scale'])
add2 = node(wn, 'ShaderNodeVectorMath', operation='ADD'); link(wn, addc.outputs['Vector'], add2.inputs[0]); link(wn, stv.outputs['Vector'], add2.inputs[1])
# below the horizon the sky only lights the scene: a dark ground
hor = mrange(wn, dz.outputs['Z'], -0.02, 0.0)
fin = node(wn, 'ShaderNodeMix'); fin.data_type = 'RGBA'; link(wn, hor, fin.inputs['Factor'])
# the thin strip past the end of the plain takes the horizon's haze
fin.inputs['A'].default_value = tuple(arg('hor-k', 1.6) * v for v in HAZE) + (1,); link(wn, add2.outputs['Vector'], fin.inputs['B'])
bg = node(wn, 'ShaderNodeBackground'); bg.inputs['Strength'].default_value = 1.0
link(wn, fin.outputs['Result'], bg.inputs['Color'])
wo = node(wn, 'ShaderNodeOutputWorld'); link(wn, bg.outputs['Background'], wo.inputs['Surface'])
wld.cycles.sampling_method = 'MANUAL'; wld.cycles.sample_map_resolution = 1024

# ---------------------------------------------------------------- camera
EYE = arg('eye', 1.6)
CAM_Z = float(height(0, 0)) + EYE
LENS = arg('lens', 28.0)
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam_d.lens = LENS; cam_d.sensor_width = 36; cam_d.sensor_fit = 'HORIZONTAL'
cam.location = (0, 0, CAM_Z)
cam.rotation_euler = (math.pi / 2 + math.radians(arg('pitch', 0.0)), 0, math.radians(arg('cam-yaw', 0.0)))
cam_d.clip_start = 0.05; cam_d.clip_end = 30000
CAM = np.array([0.0, 0.0, CAM_Z])

# ---------------------------------------------------------------- the Break: exact geometry from break-geometry.json
S = arg('size', 2.6) / 100     # 100 units = 2.6 m: a standing stone on the crest
T = arg('thick', 0.55)
MARK_X, MARK_Y = arg('mx', 2.4), arg('my', CREST + 0.6)
MARK_YAW = math.radians(arg('yaw', -10.0))
MARK_Z0 = float(height(MARK_X, MARK_Y)) - arg('sink', 0.1)

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
def prism(name, pts2d, y0, y1):
    bm = bmesh.new()
    front = [bm.verts.new((x, y0, z)) for x, z in pts2d]; back = [bm.verts.new((x, y1, z)) for x, z in pts2d]
    bm.faces.new(front[::-1]); bm.faces.new(back)
    n = len(pts2d)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((front[i], front[j], back[j], back[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); return ob

tile = prism('stone', [to_xz(p) for p in rrect()], -T / 2, T / 2)
cut_seam = prism('cut_seam', [to_xz(p) for p in svg_poly(GEO['seam'])], -T, T)
cut_cav = prism('cut_cav', [to_xz(p) for p in svg_poly(GEO['cav'])], -T, T)
bv = tile.modifiers.new('arris', 'BEVEL'); bv.width = arg('bevel', 0.022); bv.segments = 4; bv.limit_method = 'ANGLE'
bv.angle_limit = math.radians(35)
for c in (cut_seam, cut_cav):
    md = tile.modifiers.new('cut', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = c
    c.hide_render = True; c.hide_viewport = True
gem = [to_xz(p) for p in svg_poly(GEO['gem'])]
cxz = to_xz((50, 51.5))
ZE, ZR = 0.045, T / 2 - 0.014
bm = bmesh.new()
fr = [bm.verts.new((x, -ZE, z)) for x, z in gem]; bk = [bm.verts.new((x, ZE, z)) for x, z in gem]
af = bm.verts.new((cxz[0], -ZR, cxz[1])); ab = bm.verts.new((cxz[0], ZR, cxz[1]))
for i in range(len(gem)):
    j = (i + 1) % len(gem)
    bm.faces.new((fr[i], fr[j], af)); bm.faces.new((bk[j], bk[i], ab)); bm.faces.new((fr[j], fr[i], bk[i], bk[j]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new('crystal'); bm.to_mesh(me); bm.free()
crystal = bpy.data.objects.new('crystal', me); sc.collection.objects.link(crystal)
bvc = crystal.modifiers.new('arris', 'BEVEL'); bvc.width = 0.003; bvc.segments = 2; bvc.limit_method = 'ANGLE'
mark = bpy.data.objects.new('mark', None); sc.collection.objects.link(mark)
mark.location = (MARK_X, MARK_Y, MARK_Z0); mark.rotation_euler = (0, 0, MARK_YAW)
for o_ in (tile, crystal, cut_seam, cut_cav): o_.parent = mark

# stone: two scanned rocks blended by noise, honed and dark; lichen-grey weathering low on the faces
m_st, nt = mat('stone')
tco = node(nt, 'ShaderNodeTexCoord', (-1200, 0))
mpp = node(nt, 'ShaderNodeMapping', (-1000, 0)); mpp.inputs['Scale'].default_value = (0.7, 0.7, 0.7)
link(nt, tco.outputs['Object'], mpp.inputs['Vector'])
def boxtex(path, nc):
    t = node(nt, 'ShaderNodeTexImage'); t.image = img(path, nc); t.projection = 'BOX'; t.projection_blend = 0.25
    link(nt, mpp.outputs['Vector'], t.inputs['Vector']); return t.outputs['Color']
rk = os.path.join(PH, 'seaside_rock'); ak = os.path.join(ACG, 'Rock041')
nz = node(nt, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.4; nz.inputs['Detail'].default_value = 3
link(nt, tco.outputs['Object'], nz.inputs['Vector'])
nzr = mrange(nt, nz.outputs['Fac'], 0.42, 0.62)
def mixc(a, b):
    mx_ = node(nt, 'ShaderNodeMix'); mx_.data_type = 'RGBA'
    link(nt, nzr, mx_.inputs['Factor']); link(nt, a, mx_.inputs['A']); link(nt, b, mx_.inputs['B']); return mx_.outputs['Result']
td = mixc(boxtex(os.path.join(ak, 'Rock041_2K-JPG_Color.jpg'), False), boxtex(os.path.join(rk, 'seaside_rock_diff_2k.jpg'), False))
tr = mixc(boxtex(os.path.join(ak, 'Rock041_2K-JPG_Roughness.jpg'), True), boxtex(os.path.join(rk, 'seaside_rock_rough_2k.jpg'), True))
tn = mixc(boxtex(os.path.join(ak, 'Rock041_2K-JPG_NormalGL.jpg'), True), boxtex(os.path.join(rk, 'seaside_rock_nor_gl_2k.jpg'), True))
hs = node(nt, 'ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = 0.15
hs.inputs['Value'].default_value = arg('st-val', 0.5); link(nt, td, hs.inputs['Color'])
rr = mrange(nt, tr, 0.0, 1.0, 0.3, 0.55)
nm = node(nt, 'ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.7; link(nt, tn, nm.inputs['Color'])
bvn = node(nt, 'ShaderNodeBevel'); bvn.samples = 6; bvn.inputs['Radius'].default_value = 0.005
link(nt, nm.outputs['Normal'], bvn.inputs['Normal'])
bsdf = node(nt, 'ShaderNodeBsdfPrincipled'); bsdf.inputs['Specular IOR Level'].default_value = 0.55
link(nt, hs.outputs['Color'], bsdf.inputs['Base Color']); link(nt, rr, bsdf.inputs['Roughness'])
link(nt, bvn.outputs['Normal'], bsdf.inputs['Normal'])
out = node(nt, 'ShaderNodeOutputMaterial'); link(nt, bsdf.outputs['BSDF'], out.inputs['Surface'])
tile.data.materials.append(m_st)
m_in = m_st.copy(); m_in.name = 'stone_cut'
for n_ in m_in.node_tree.nodes:
    if n_.bl_idname == 'ShaderNodeHueSaturation': n_.inputs['Value'].default_value = arg('cut-val', 0.12)
dg = bpy.context.evaluated_depsgraph_get()
me_cut = bpy.data.meshes.new_from_object(tile.evaluated_get(dg))
tile.modifiers.clear(); tile.data = me_cut
me_cut.materials.clear(); me_cut.materials.append(m_st); me_cut.materials.append(m_in)
HX = 50 * S; RC = 22 * S; ZC = 50 * S
def rr_sdf(x, z):
    qx = abs(x) - (HX - RC); qz = abs(z - ZC) - (HX - RC)
    return math.hypot(max(qx, 0), max(qz, 0)) + min(max(qx, qz), 0) - RC
for f in me_cut.polygons:
    c_ = f.center
    f.material_index = 1 if (abs(f.normal.y) < 0.6 and rr_sdf(c_.x, c_.z) < -0.012) else 0
tile.modifiers.new('wn', 'WEIGHTED_NORMAL')

# crystal: clear sky glass over a translucent core, held to sky #94E6FF
SKY = [srgb2lin(v / 255) for v in (0x94, 0xE6, 0xFF)]
m_cr, nt = mat('crystal')
b = node(nt, 'ShaderNodeBsdfPrincipled')
b.inputs['Base Color'].default_value = (*[v ** 1.4 for v in SKY], 1)
b.inputs['Subsurface Weight'].default_value = 1.0; b.inputs['Subsurface Radius'].default_value = (0.35, 0.8, 1.0)
b.inputs['Subsurface Scale'].default_value = 0.12
b.inputs['Transmission Weight'].default_value = 0.96; b.inputs['Roughness'].default_value = 0.04
b.inputs['IOR'].default_value = 1.52
b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.02
emc = node(nt, 'ShaderNodeEmission'); emc.inputs['Color'].default_value = (*SKY, 1)
emc.inputs['Strength'].default_value = arg('cr-glow', 0.04)
ad = node(nt, 'ShaderNodeAddShader'); link(nt, b.outputs['BSDF'], ad.inputs[0]); link(nt, emc.outputs['Emission'], ad.inputs[1])
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, ad.outputs['Shader'], o.inputs['Surface'])
crystal.data.materials.append(m_cr)

# ---------------------------------------------------------------- the campfires on the plain
def wedge_ok(x, y, margin=6):
    az = np.degrees(np.arctan2(x, y))
    return np.abs(az) < (math.degrees(math.atan(18 / LENS)) + margin)
NCAMP = arg('camps', 34)
fx, fy = [], []
for k in range(NCAMP):
    r = 520 * (7500 / 520) ** rng.uniform(0, 1) ** 0.85
    az = rng.uniform(-1, 1) * math.radians(36)
    cx_, cy_ = r * math.sin(az), r * math.cos(az)
    n = int(rng.integers(6, 26)); sd = rng.uniform(40, 160) * (r / 2000) ** 0.3
    # a camp: fires in loose rows and knots
    ang = rng.uniform(0, math.pi)
    u = rng.normal(0, sd * 1.6, n); v = rng.normal(0, sd * 0.6, n)
    fx += list(cx_ + u * math.cos(ang) - v * math.sin(ang)); fy += list(cy_ + u * math.sin(ang) + v * math.cos(ang))
nl = arg('loners', 140)
r = 380 * (8500 / 380) ** rng.uniform(0, 1, nl); az = rng.uniform(-1, 1, nl) * math.radians(38)
fx += list(r * np.sin(az)); fy += list(r * np.cos(az))
fx = np.array(fx); fy = np.array(fy)
keep = wedge_ok(fx, fy) & (fy > CREST + 0.75 * LDROP)
fx, fy = fx[keep], fy[keep]
fz = height(fx, fy)
NF = len(fx); print('FIRES', NF)
dist = np.sqrt(fx ** 2 + fy ** 2 + (fz - CAM_Z) ** 2)
kk = np.maximum(1.0, dist / arg('k-dist', 650.0))       # far fires are drawn a touch larger so they never vanish
frnd = rng.uniform(0, 1, NF)

FIRE = blackbody(arg('fire-k', 1850))
PF = arg('fire-w', 45000.0)
for i in range(NF):
    ld = bpy.data.lights.new(f'fire{i}', 'POINT')
    ld.energy = PF * (0.55 + 0.9 * frnd[i]) * (1 + dist[i] / 3000)
    ld.color = FIRE; ld.shadow_soft_size = 0.35
    lo = bpy.data.objects.new(f'fire{i}', ld); sc.collection.objects.link(lo)
    lo.location = (fx[i], fy[i], fz[i] + 0.7)
    lo.visible_camera = False

# billboards that face the camera: flames (bright, small) and smoke (tall, faint, leaning in the breeze)
def billboards(name, w, h, z0, lean, nseg, attrs):
    m = len(fx)
    to_c = np.stack([CAM[0] - fx, CAM[1] - fy], 1); to_c /= np.linalg.norm(to_c, axis=1, keepdims=True)
    rt = np.stack([to_c[:, 1], -to_c[:, 0], np.zeros(m)], 1)     # right, as seen from the camera
    vs, uvs = [], []
    for s_ in range(nseg + 1):
        v = s_ / nseg
        for u in (0.0, 1.0):
            off = (u - 0.5) * w[:, None] * rt + (lean[:, None] * (v ** 1.7) * h[:, None]) * rt
            p = np.stack([fx, fy, fz + z0], 1) + off + np.array([0, 0, 1.0]) * (v * h)[:, None]
            vs.append(p); uvs.append((u, v))
    V = np.stack(vs, 1).reshape(-1, 3)            # per billboard: (nseg+1)*2 verts
    nv = (nseg + 1) * 2
    faces, fuv = [], []
    for s_ in range(nseg):
        a0, a1, b0, b1 = 2 * s_, 2 * s_ + 1, 2 * s_ + 2, 2 * s_ + 3
        faces.append((a0, a1, b1, b0)); fuv.append((uvs[a0], uvs[a1], uvs[b1], uvs[b0]))
    F = (np.arange(m)[:, None, None] * nv + np.array(faces)[None]).reshape(-1, 4)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V)); me.vertices.foreach_set('co', V.astype(np.float32).ravel())
    me.loops.add(F.size); me.loops.foreach_set('vertex_index', F.ravel().astype(np.int32))
    me.polygons.add(len(F)); me.polygons.foreach_set('loop_start', np.arange(0, F.size, 4, dtype=np.int32))
    me.update(calc_edges=True)
    uvl = me.uv_layers.new(name='UVMap')
    UV = np.tile(np.array(fuv, np.float32).reshape(-1, 2), (m, 1))
    uvl.data.foreach_set('uv', UV.ravel())
    for an, vals in attrs.items():
        at = me.attributes.new(an, 'FLOAT', 'CORNER')
        at.data.foreach_set('value', np.repeat(vals.astype(np.float32), nseg * 4))
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); camera_only(ob)
    return ob

ext = np.exp(-dist / arg('fire-ext', 9000.0))          # the night air dims the far fires a little
# flames
m_fl, nt = mat('flame')
uv = node(nt, 'ShaderNodeUVMap'); uv.uv_map = 'UVMap'
sx = node(nt, 'ShaderNodeSeparateXYZ'); link(nt, uv.outputs['UV'], sx.inputs['Vector'])
at_e = node(nt, 'ShaderNodeAttribute'); at_e.attribute_name = 'ext'; at_e.attribute_type = 'GEOMETRY'
at_r = node(nt, 'ShaderNodeAttribute'); at_r.attribute_name = 'rnd'
xu = math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', sx.outputs['X'], 0.5), 0.2)
yv = math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', sx.outputs['Y'], 0.28), 0.26)
core = math_(nt, 'EXPONENT', math_(nt, 'MULTIPLY', math_(nt, 'ADD', math_(nt, 'MULTIPLY', xu, xu), math_(nt, 'MULTIPLY', yv, yv)), -1.0))
fcol = node(nt, 'ShaderNodeMix'); fcol.data_type = 'RGBA'; link(nt, core, fcol.inputs['Factor'])
fcol.inputs['A'].default_value = (*blackbody(1500), 1); fcol.inputs['B'].default_value = (*blackbody(2400), 1)
em = node(nt, 'ShaderNodeEmission'); link(nt, fcol.outputs['Result'], em.inputs['Color'])
estr = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', core, arg('flame', 90.0)), at_e.outputs['Fac'])
estr = math_(nt, 'MULTIPLY', estr, math_(nt, 'ADD', 0.6, math_(nt, 'MULTIPLY', at_r.outputs['Fac'], 0.8)))
link(nt, estr, em.inputs['Strength'])
tp = node(nt, 'ShaderNodeBsdfTransparent')
ms = node(nt, 'ShaderNodeMixShader'); link(nt, math_(nt, 'MULTIPLY', core, 2.5, clamp=True), ms.inputs['Fac'])
link(nt, tp.outputs['BSDF'], ms.inputs[1]); link(nt, em.outputs['Emission'], ms.inputs[2])
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, ms.outputs['Shader'], o.inputs['Surface'])
fl = billboards('flames', 1.1 * kk, 1.5 * kk, -0.1, np.zeros(NF), 1, {'ext': ext, 'rnd': frnd})
fl.data.materials.append(m_fl)

# smoke: warm where the fire lights it, fading to a cool grey as it rises into the starlight
near = dist < arg('smoke-dist', 5000.0)
m_sm, nt = mat('smoke')
uv = node(nt, 'ShaderNodeUVMap'); uv.uv_map = 'UVMap'
sx = node(nt, 'ShaderNodeSeparateXYZ'); link(nt, uv.outputs['UV'], sx.inputs['Vector'])
at_e = node(nt, 'ShaderNodeAttribute'); at_e.attribute_name = 'ext'
at_r = node(nt, 'ShaderNodeAttribute'); at_r.attribute_name = 'rnd'
nvec = node(nt, 'ShaderNodeCombineXYZ')
link(nt, math_(nt, 'MULTIPLY', sx.outputs['X'], 1.6), nvec.inputs['X'])
link(nt, math_(nt, 'MULTIPLY', sx.outputs['Y'], 3.0), nvec.inputs['Y'])
n1 = node(nt, 'ShaderNodeTexNoise'); n1.noise_dimensions = '4D'; n1.inputs['Scale'].default_value = 1.4; n1.inputs['Detail'].default_value = 6
n1.inputs['Roughness'].default_value = 0.6
link(nt, nvec.outputs['Vector'], n1.inputs['Vector']); link(nt, math_(nt, 'MULTIPLY', at_r.outputs['Fac'], 40.0), n1.inputs['W'])
vv = sx.outputs['Y']
xo = math_(nt, 'ADD', math_(nt, 'SUBTRACT', sx.outputs['X'], 0.5), math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', n1.outputs['Fac'], 0.5), math_(nt, 'MULTIPLY', vv, 0.5)))
wdt = math_(nt, 'ADD', 0.05, math_(nt, 'MULTIPLY', vv, 0.24))
q = math_(nt, 'DIVIDE', xo, wdt)
g = math_(nt, 'EXPONENT', math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', q, q), -1.0))
fade = math_(nt, 'MULTIPLY', mrange(nt, vv, 0.0, 0.1), math_(nt, 'POWER', math_(nt, 'SUBTRACT', 1.0, vv), 1.8))
dens = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', g, fade), mrange(nt, n1.outputs['Fac'], 0.3, 0.72))
alpha = math_(nt, 'MULTIPLY', dens, arg('smoke-a', 0.45), clamp=True)
scol = node(nt, 'ShaderNodeMix'); scol.data_type = 'RGBA'; link(nt, mrange(nt, vv, 0.0, 0.2, 0.0, 1.0, 'SMOOTHSTEP'), scol.inputs['Factor'])   # warm only where the fire lights it
SW = arg('smoke-warm', 2.0)
scol.inputs['A'].default_value = tuple(SW * c for c in blackbody(1700)) + (1,)
scol.inputs['B'].default_value = (0.010, 0.014, 0.022, 1)
sem = node(nt, 'ShaderNodeEmission'); link(nt, scol.outputs['Result'], sem.inputs['Color'])
link(nt, at_e.outputs['Fac'], sem.inputs['Strength'])
tp = node(nt, 'ShaderNodeBsdfTransparent')
ms = node(nt, 'ShaderNodeMixShader'); link(nt, alpha, ms.inputs['Fac'])
link(nt, tp.outputs['BSDF'], ms.inputs[1]); link(nt, sem.outputs['Emission'], ms.inputs[2])
o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, ms.outputs['Shader'], o.inputs['Surface'])
_all = (fx, fy, fz)
fx, fy, fz = fx[near], fy[near], fz[near]
kn = kk[near]; NS = len(fx)
lean = rng.uniform(0.15, 0.45, NS) * arg('wind', 1.0)       # the breeze from the left bends every column the same way
smk = billboards('smoke', 5.0 * np.sqrt(kn) * rng.uniform(0.8, 1.3, NS), 24.0 * np.sqrt(kn) * rng.uniform(0.7, 1.4, NS), 0.3 * kn, lean, 6,
                 {'ext': ext[near] * (0.6 + 0.6 * frnd[near]), 'rnd': frnd[near]})
smk.data.materials.append(m_sm)
fx, fy, fz = _all

# ---------------------------------------------------------------- grass on the crest
atlas_dir = os.path.join(PH, 'grass_medium_01')
A_DIFF = img(os.path.join(atlas_dir, 'textures', 'grass_medium_01_diff_2k.jpg'))
A_ALPHA = img(os.path.join(atlas_dir, 'textures', 'grass_medium_01_alpha_2k.png'), True)
def grass_material(name, use_alpha, uv_tint=(1, 1, 1), trans=0.45, dry=0.0):
    m, nt = mat(name)
    uv = node(nt, 'ShaderNodeUVMap'); uv.uv_map = 'UVMap'
    t = node(nt, 'ShaderNodeTexImage'); t.image = A_DIFF; link(nt, uv.outputs['UV'], t.inputs['Vector'])
    oi = node(nt, 'ShaderNodeObjectInfo')
    hs = node(nt, 'ShaderNodeHueSaturation')
    link(nt, mrange(nt, oi.outputs['Random'], 0, 1, 0.47, 0.53), hs.inputs['Hue'])
    hs.inputs['Saturation'].default_value = 0.7; hs.inputs['Value'].default_value = 0.9
    link(nt, t.outputs['Color'], hs.inputs['Color'])
    drym = node(nt, 'ShaderNodeMix'); drym.data_type = 'RGBA'
    link(nt, math_(nt, 'MULTIPLY', math_(nt, 'GREATER_THAN', oi.outputs['Random'], 1 - dry), 0.75), drym.inputs['Factor'])
    link(nt, hs.outputs['Color'], drym.inputs['A']); drym.inputs['B'].default_value = (0.42, 0.36, 0.2, 1)
    tint = node(nt, 'ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs['Factor'].default_value = 1.0
    link(nt, drym.outputs['Result'], tint.inputs['A']); tint.inputs['B'].default_value = (*uv_tint, 1)
    p = node(nt, 'ShaderNodeBsdfPrincipled'); link(nt, tint.outputs['Result'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.4; p.inputs['Specular IOR Level'].default_value = 0.5
    tb = node(nt, 'ShaderNodeMix'); tb.data_type = 'RGBA'; tb.blend_type = 'MULTIPLY'; tb.inputs['Factor'].default_value = 1.0
    link(nt, tint.outputs['Result'], tb.inputs['A']); tb.inputs['B'].default_value = (1.35, 1.5, 0.7, 1)
    tl = node(nt, 'ShaderNodeBsdfTranslucent'); link(nt, tb.outputs['Result'], tl.inputs['Color'])
    ms = node(nt, 'ShaderNodeMixShader'); ms.inputs['Fac'].default_value = trans
    link(nt, p.outputs['BSDF'], ms.inputs[1]); link(nt, tl.outputs['BSDF'], ms.inputs[2]); sh = ms.outputs['Shader']
    if use_alpha:
        ta = node(nt, 'ShaderNodeTexImage'); ta.image = A_ALPHA; link(nt, uv.outputs['UV'], ta.inputs['Vector'])
        tp = node(nt, 'ShaderNodeBsdfTransparent'); ma = node(nt, 'ShaderNodeMixShader')
        link(nt, ta.outputs['Color'], ma.inputs['Fac']); link(nt, tp.outputs['BSDF'], ma.inputs[1]); link(nt, sh, ma.inputs[2]); sh = ma.outputs['Shader']
    o = node(nt, 'ShaderNodeOutputMaterial'); link(nt, sh, o.inputs['Surface'])
    return m
M_BLADE = grass_material('blade', False, (0.8, 0.95, 0.75), 0.5, dry=0.25)
M_HEAD = grass_material('seedhead', True, (1.05, 1.0, 0.9), 0.6, dry=0.6)
COLS = [1612, 1664, 1710]; AY0, AY1 = 380, 1150
HEADS = [(1740, 1840, 20, 330), (1890, 2000, 30, 500), (1920, 2040, 460, 1140), (1395, 1445, 590, 1100)]
def blade_points(L, tilt, az, droop):
    pts = []; N = 7
    d = Vector((math.sin(tilt) * math.cos(az), math.sin(tilt) * math.sin(az), math.cos(tilt)))
    p = Vector((0, 0, 0)); step = L / N
    for i in range(N + 1):
        pts.append(p.copy())
        d = (d + Vector((math.cos(az), math.sin(az), 0)) * droop * (i / N) * 0.6 - Vector((0, 0, droop * (i / N) ** 2 * 0.5))).normalized()
        p = p + d * step
    return pts
WIND_AZ = math.radians(arg('wind-az', 0.0))   # the breeze comes from the left: blades lean to the right
def build_clump(name, nblades, hmin, hmax, heads=0, spread=0.07):
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
    for k in range(nblades):
        L = rng.uniform(hmin, hmax)
        az = WIND_AZ + rng.normal(0, 0.9) if rng.uniform() < 0.6 else rng.uniform(0, 2 * math.pi)
        tilt = rng.uniform(0.05, 0.45); droop = rng.uniform(0.05, 0.6) * (L / hmax)
        base = Vector((rng.normal(0, spread), rng.normal(0, spread), 0))
        pts = blade_points(L, tilt, az, droop)
        w0 = rng.uniform(0.004, 0.0085)
        side = Vector((-math.sin(az + rng.uniform(-0.6, 0.6)), math.cos(az + rng.uniform(-0.6, 0.6)), 0)).normalized()
        col = COLS[rng.integers(len(COLS))] + rng.uniform(-2, 2)
        u0, u1 = (col - 2.5) / 2048, (col + 2.5) / 2048
        vb = 1 - AY1 / 2048; vt = 1 - AY0 / 2048; v_start = rng.uniform(vb, vb + 0.15)
        N = len(pts) - 1; left, right = [], []
        for i, pnt in enumerate(pts):
            t = i / N; w = w0 * (1 - t ** 1.6) + 0.0004; tw = side * w
            left.append((bm.verts.new(base + pnt - tw), t)); right.append((bm.verts.new(base + pnt + tw), t))
        for i in range(N):
            f = bm.faces.new((left[i][0], right[i][0], right[i + 1][0], left[i + 1][0]))
            for lp_, (vx, isr, t) in zip(f.loops, ((0, False, left[i][1]), (0, True, right[i][1]), (0, True, right[i + 1][1]), (0, False, left[i + 1][1]))):
                lp_[uvl].uv = (u1 if isr else u0, v_start + (vt - v_start) * t)
        if k < heads:
            hx0, hx1, hy0, hy1 = HEADS[rng.integers(len(HEADS))]
            top = base + pts[-1]; hh = rng.uniform(0.12, 0.2); hw = hh * (hx1 - hx0) / (hy1 - hy0)
            sd = Vector((math.cos(rng.uniform(0, math.pi)), math.sin(rng.uniform(0, math.pi)), 0))
            up = (pts[-1] - pts[-2]).normalized()
            q_ = [top - sd * hw / 2, top + sd * hw / 2, top + sd * hw / 2 + up * hh, top - sd * hw / 2 + up * hh]
            f = bm.faces.new([bm.verts.new(v) for v in q_]); f.material_index = 1
            for lp_, uvv in zip(f.loops, [(hx0 / 2048, 1 - hy1 / 2048), (hx1 / 2048, 1 - hy1 / 2048), (hx1 / 2048, 1 - hy0 / 2048), (hx0 / 2048, 1 - hy0 / 2048)]):
                lp_[uvl].uv = uvv
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(M_BLADE); me.materials.append(M_HEAD)
    for p_ in me.polygons: p_.use_smooth = True
    return bpy.data.objects.new(name, me)
lib = bpy.data.collections.new('grass_lib'); sc.collection.children.link(lib)
variants = []
for i in range(8):
    tall = i < 5
    ob = build_clump(f'clump{i}', 18 if tall else 26, 0.3 if tall else 0.16, arg('grass-h', 0.62) if tall else 0.36, heads=(4 if tall else 0), spread=0.06 if tall else 0.08)
    lib.objects.link(ob); variants.append(ob)
with bpy.data.libraries.load(os.path.join(atlas_dir, 'grass_medium_01_2k.blend'), link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.endswith('_LOD1') and any(s in n for s in ('large', 'mid', 'tall'))]
M_PH = grass_material('ph_grass', True, (0.95, 1.0, 0.9), 0.45, dry=0.25)
for ob in dst.objects:
    me = ob.data; ob.location = (0, 0, 0); ob.rotation_euler = (0, 0, 0)
    me.materials.clear(); me.materials.append(M_PH)
    if me.uv_layers and me.uv_layers[0].name != 'UVMap': me.uv_layers[0].name = 'UVMap'
    lib.objects.link(ob); variants.append(ob)
NV_TALL = 8; nvar_all = len(variants)

HALF = math.atan(18 / LENS) + math.radians(10)
def outside_mark(x, y):
    c, s_ = math.cos(-MARK_YAW), math.sin(-MARK_YAW)
    lx = (x - MARK_X) * c - (y - MARK_Y) * s_; ly = (x - MARK_X) * s_ + (y - MARK_Y) * c
    return ~((np.abs(lx) < 50 * S + 0.04) & (np.abs(ly) < T / 2 + 0.04))
_ph = rng.uniform(0, 6.28, (2, 4)); _fq = rng.uniform(0.15, 0.6, (2, 4, 2))
def patch(x, y, k):
    v = sum(np.sin(x * _fq[k, i, 0] + y * _fq[k, i, 1] + _ph[k, i]) for i in range(4)) / 4
    return np.clip(0.5 + 0.9 * v, 0, 1)
def scatter(name, n, rmin, rmax, dens, scale_rng, pick):
    th = rng.uniform(-HALF, HALF, n); r = np.sqrt(rng.uniform(rmin ** 2, rmax ** 2, n))
    keep = rng.uniform(0, 1, n) < dens(r); th, r = th[keep], r[keep]
    x = r * np.sin(th); y = r * np.cos(th)
    ok = outside_mark(x, y) & (rng.uniform(0, 1, len(x)) < 0.5 + 0.5 * patch(x, y, 1))
    x, y = x[ok], y[ok]; m = len(x)
    verts = np.stack([x, y, height(x, y) - 0.02], 1).astype(np.float32)
    me = bpy.data.meshes.new(name); me.vertices.add(m); me.vertices.foreach_set('co', verts.ravel())
    rot = np.zeros((m, 3), np.float32); rot[:, 2] = rng.uniform(0, 2 * math.pi, m)
    rot[:, 0] = rng.normal(0, 0.05, m); rot[:, 1] = rng.normal(0, 0.05, m) + 0.06
    dm = np.hypot(x - MARK_X, y - MARK_Y)
    nearm = 0.35 + 0.65 * np.clip((dm - 0.5) / 3.0, 0, 1)   # kept low around the stone so the whole mark reads
    lane = (np.abs(x - MARK_X) < 1.6 + 0.15 * (MARK_Y - y)) & (y < MARK_Y) & (y > MARK_Y - 6)
    nearm = np.where(lane, nearm * (0.35 + 0.65 * np.clip((MARK_Y - y - 1.0) / 5.0, 0, 1)), nearm)
    sc_ = (rng.uniform(*scale_rng, m) * nearm * (0.7 + 0.55 * patch(x, y, 0))).astype(np.float32)
    scl = np.stack([sc_, sc_, sc_ * rng.uniform(0.85, 1.25, m)], 1).astype(np.float32)
    pk = pick(m).astype(np.int32)
    for an, data, tp in (('rot', rot, 'FLOAT_VECTOR'), ('scl', scl, 'FLOAT_VECTOR'), ('pick', pk, 'INT')):
        at = me.attributes.new(an, tp, 'POINT'); at.data.foreach_set('vector' if tp == 'FLOAT_VECTOR' else 'value', data.ravel())
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    ng = bpy.data.node_groups.new(name + '_gn', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    gi = ng.nodes.new('NodeGroupInput'); go = ng.nodes.new('NodeGroupOutput')
    m2p = ng.nodes.new('GeometryNodeMeshToPoints')
    ci = ng.nodes.new('GeometryNodeCollectionInfo'); ci.inputs['Collection'].default_value = lib
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
    md = ob.modifiers.new('scatter', 'NODES'); md.node_group = ng
    print(name, m, 'instances'); return ob
def pick_mix(m):
    return np.where(rng.uniform(0, 1, m) < 0.55, rng.integers(0, NV_TALL, m), rng.integers(NV_TALL, nvar_all, m))
scatter('crest', int(70000 * D), 1.0, CREST + 2.5, lambda r: np.clip(1.15 - r / 40, 0.35, 1), (0.9, 1.4), pick_mix)
scatter('crest_ph', int(26000 * D), 1.0, CREST + 3.5, lambda r: np.ones_like(r), (1.0, 1.5), lambda m: rng.integers(NV_TALL, nvar_all, m))
lib.hide_render = True

# ---------------------------------------------------------------- light: starlight fill from behind the camera, a breath of firelight from the plain
def area(name, loc, target, size, power, col):
    ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'DISK'; ld.size = size; ld.energy = power; ld.color = col
    ob = bpy.data.objects.new(name, ld); sc.collection.objects.link(ob); ob.location = loc
    d = Vector(target) - Vector(loc); ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    ob.visible_camera = False; return ob
mk = Vector((MARK_X, MARK_Y, MARK_Z0 + 50 * S))
area('starfill', (mk.x - 26, mk.y - 30, mk.z + 24), mk, 12.0, arg('fill', 7000.0), (0.55, 0.7, 1.0))
area('firerim', (mk.x + 5, mk.y + 26, mk.z - 7), mk, 14.0, arg('rim', 500.0), blackbody(1900))

# ---------------------------------------------------------------- camera focus
cam_d.dof.use_dof = True
cam_d.dof.focus_distance = float(np.hypot(MARK_X, MARK_Y)) - 0.2
cam_d.dof.aperture_fstop = arg('fstop', 2.8); cam_d.dof.aperture_blades = 7

# ---------------------------------------------------------------- compositor: halation on the fires, a wide warm breath of light over the camp
sc.use_nodes = True
ct = sc.node_tree; ct.nodes.clear()
rl = ct.nodes.new('CompositorNodeRLayers'); comp = ct.nodes.new('CompositorNodeComposite')
g1 = ct.nodes.new('CompositorNodeGlare'); g1.glare_type = 'FOG_GLOW'; g1.quality = 'HIGH'
g1.inputs['Threshold'].default_value = arg('g1-th', 0.6); g1.inputs['Strength'].default_value = arg('g1', 0.5)
g1.inputs['Size'].default_value = 0.6
g2 = ct.nodes.new('CompositorNodeGlare'); g2.glare_type = 'BLOOM'; g2.quality = 'HIGH'
g2.inputs['Threshold'].default_value = arg('g2-th', 0.3); g2.inputs['Smoothness'].default_value = 1.0
g2.inputs['Strength'].default_value = arg('g2', 0.75); g2.inputs['Size'].default_value = 1.0
g2.inputs['Tint'].default_value = (1.0, 0.75, 0.55, 1)
ct.links.new(rl.outputs['Image'], g1.inputs['Image']); ct.links.new(g1.outputs['Image'], g2.inputs['Image'])
# a soft vignette, as a lens gives
em_ = ct.nodes.new('CompositorNodeEllipseMask'); em_.inputs['Size'].default_value = (1.25, 1.35)
bl_ = ct.nodes.new('CompositorNodeBlur'); bl_.filter_type = 'GAUSS'; bl_.use_relative = True
bl_.factor_x = 30; bl_.factor_y = 30
ct.links.new(em_.outputs['Mask'], bl_.inputs['Image'])
vg = ct.nodes.new('CompositorNodeMapRange'); vg.inputs['To Min'].default_value = arg('vignette', 0.62); vg.inputs['To Max'].default_value = 1.0
ct.links.new(bl_.outputs['Image'], vg.inputs['Value'])
mul = ct.nodes.new('CompositorNodeMixRGB'); mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 1.0
ct.links.new(g2.outputs['Image'], mul.inputs[1]); ct.links.new(vg.outputs['Value'], mul.inputs[2])
ct.links.new(mul.outputs['Image'], comp.inputs['Image'])

bpy.context.view_layer.update()
from bpy_extras.object_utils import world_to_camera_view
def proj(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return round(v.x * W, 1), round((1 - v.y) * H, 1)
info = {'stone_top': proj((MARK_X, MARK_Y, MARK_Z0 + 100 * S)), 'stone_base': proj((MARK_X, MARK_Y, MARK_Z0)),
        'crystal': proj(tuple(mark.matrix_world @ Vector((cxz[0], 0, cxz[1])))), 'horizon': proj((0, 20000, CAM_Z)),
        'crest': proj((0, CREST, float(height(0, CREST)))), 'fires': NF, 'smoke': NS}
print('INFO', json.dumps(info))
if arg('sky-only', 0):
    for o_ in sc.objects:
        if o_.type != 'CAMERA': o_.hide_render = True
if '--dry' in argv:
    print('DRY_OK'); sys.exit(0)
t0 = time.time()
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('RENDER_SECONDS', round(time.time() - t0, 1))
