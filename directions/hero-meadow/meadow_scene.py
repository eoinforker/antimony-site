# Hero Meadow: the Break as a carved stone in a sunlit meadow.
# Blender 4.5 LTS, Cycles CPU. Poly Haven CC0 assets (see credits.txt).
#
# Run:  blender -b -P meadow_scene.py -- --assets <dir> --out <file> [options]
#   --res 640x360  --samples 32  --time 0 (seconds; 0 means no limit)
#   --hdri drackenstein_quarry_4k.hdr  --sun-u 0.6  --sun-az 24
#   --crop phone  (renders the 9:16 portrait framing)
#   --passes <file.exr>  (also writes depth and the grass AOVs for the loop)
import bpy, bmesh, math, json, os, re, sys, random
import numpy as np
from mathutils import Vector, Matrix, Euler

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    k = '--' + name
    return type(default)(argv[argv.index(k) + 1]) if k in argv else default

ASSETS = arg('assets', '')
OUT = arg('out', '/tmp/meadow.png')
RES = arg('res', '640x360')
SAMPLES = arg('samples', 32)
TIME = arg('time', 0.0)
HDRI = arg('hdri', 'drackenstein_quarry_4k.hdr')
SUN_U = arg('sun-u', 0.6)
SUN_AZ = arg('sun-az', 24.0)      # degrees left of the view axis
CROP = arg('crop', 'desktop')
PASSES = arg('passes', '')
DENSITY = arg('density', 1.0)
EXPO = arg('exposure', 0.0)
VARIANT = arg('variant', 'day')     # day, or night (blue hour, soft rain, luminous flowers)
NIGHT = VARIANT == 'night'
GEO = json.load(open(arg('geometry', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'break-geometry.json'))))

random.seed(7); rng = np.random.default_rng(7)

# ---------------------------------------------------------------- scene
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
cy.adaptive_threshold = 0.02
cy.time_limit = TIME
cy.use_denoising = True
cy.denoiser = 'OPENIMAGEDENOISE'
cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
cy.max_bounces = 8; cy.diffuse_bounces = 3; cy.glossy_bounces = 3
cy.transmission_bounces = 8; cy.transparent_max_bounces = 16; cy.volume_bounces = 0
cy.caustics_reflective = False; cy.caustics_refractive = False
cy.blur_glossy = 1.0
cy.use_light_tree = True
sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'None'
sc.view_settings.exposure = EXPO
sc.render.film_transparent = False
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_depth = '16'
sc.render.image_settings.color_mode = 'RGB'

# ---------------------------------------------------------------- materials helpers
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

def aov(nt, name, socket_or_value, loc=(600, -300)):
    o = node(nt, 'ShaderNodeOutputAOV', loc); o.aov_name = name
    if isinstance(socket_or_value, (int, float)): o.inputs['Value'].default_value = socket_or_value
    else: link(nt, socket_or_value, o.inputs['Value'])

vl = sc.view_layers[0]
for nm in ('hf', 'gm', 'st', 'cr', 'ld'):
    a = vl.aovs.add(); a.name = nm; a.type = 'VALUE'
vl.use_pass_z = True

# ---------------------------------------------------------------- world: the real sky
def sun_dir_from_u(u):
    return (0.5 - u) * 2 * math.pi          # Blender equirect: u = 0.5 - atan2(y, x) / 2pi
wld = bpy.data.worlds.new('sky'); sc.world = wld; wld.use_nodes = True
wn = wld.node_tree; wn.nodes.clear()
tc = node(wn, 'ShaderNodeTexCoord', (-800, 0))
mp = node(wn, 'ShaderNodeMapping', (-600, 0))
ang_src = sun_dir_from_u(SUN_U)
a = math.radians(SUN_AZ)
ang_dst = math.atan2(math.cos(a), -math.sin(a))      # target: behind the stone, to the left
mp.inputs['Rotation'].default_value = (0, 0, ang_src - ang_dst)
env = node(wn, 'ShaderNodeTexEnvironment', (-400, 0)); env.image = img(os.path.join(ASSETS, HDRI))
bg = node(wn, 'ShaderNodeBackground', (-150, 0)); bg.inputs['Strength'].default_value = 1.0
wo = node(wn, 'ShaderNodeOutputWorld', (100, 0))
link(wn, tc.outputs['Generated'], mp.inputs['Vector']); link(wn, mp.outputs['Vector'], env.inputs['Vector'])
if NIGHT:
    # the same sky after dusk: its clouds kept as structure, the light gone to a deep blue
    bw = node(wn, 'ShaderNodeRGBToBW', (-250, 200)); link(wn, env.outputs['Color'], bw.inputs['Color'])
    cl_ = node(wn, 'ShaderNodeMath', (-150, 200), operation='MINIMUM'); cl_.inputs[1].default_value = 1.6
    link(wn, bw.outputs['Val'], cl_.inputs[0])
    tnt = node(wn, 'ShaderNodeMix', (-50, 200)); tnt.data_type = 'RGBA'; tnt.blend_type = 'MULTIPLY'; tnt.inputs['Factor'].default_value = 1
    link(wn, cl_.outputs['Value'], tnt.inputs['A']); tnt.inputs['B'].default_value = (0.026, 0.044, 0.095, 1)
    link(wn, tnt.outputs['Result'], bg.inputs['Color'])
else:
    SKY8 = arg('sky', '')
    if SKY8:
        # the camera sees the 8k sky (sharp clouds); everything else is lit by the 4k
        env8 = node(wn, 'ShaderNodeTexEnvironment', (-400, -300)); env8.image = img(SKY8)
        link(wn, mp.outputs['Vector'], env8.inputs['Vector'])
        lpw = node(wn, 'ShaderNodeLightPath', (-400, 300))
        mxw = node(wn, 'ShaderNodeMix', (-250, 0)); mxw.data_type = 'RGBA'
        link(wn, lpw.outputs['Is Camera Ray'], mxw.inputs['Factor']); link(wn, env.outputs['Color'], mxw.inputs['A']); link(wn, env8.outputs['Color'], mxw.inputs['B'])
        link(wn, mxw.outputs['Result'], bg.inputs['Color'])
    else:
        link(wn, env.outputs['Color'], bg.inputs['Color'])
link(wn, bg.outputs['Background'], wo.inputs['Surface'])
bg.inputs['Strength'].default_value = arg('sky-str', 1.0)
SUN_STR = arg('sun-str', 0.0)
SUN_OB = None
if SUN_STR > 0 and not NIGHT:
    # the low sun itself: the puresky's sun is softened by haze, so a matched lamp gives the raking light
    el = math.radians(arg('sun-el', 4.6))
    dsun = Vector((-math.sin(a) * math.cos(el), math.cos(a) * math.cos(el), math.sin(el)))
    sl = bpy.data.lights.new('sun', 'SUN'); sl.energy = SUN_STR; sl.angle = math.radians(0.6)
    sl.color = (1.0, 0.72, 0.46)
    so = bpy.data.objects.new('sun', sl); sc.collection.objects.link(so)
    so.rotation_euler = dsun.to_track_quat('Z', 'Y').to_euler()
    SUN_OB = so
wld.cycles.sampling_method = 'MANUAL'; wld.cycles.sample_map_resolution = 2048

# ---------------------------------------------------------------- the Break: geometry from break-geometry.json
S = arg('stone-m', 1.9) / 100     # 100 units = 1.9 m by default: a carved stone you could walk up to
T = arg('thick', 0.5)   # slab thickness: a real block of stone
MARK_X, MARK_Y = arg('mx', 1.05), arg('my', 13.0)
MARK_YAW = math.radians(arg('yaw', -14.0))
MOUND_H, MOUND_R = arg('mound', 0.35), 3.6
FIELD = arg('field', 1)
def _sm(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def ground_h(x, y):
    h = MOUND_H * np.exp(-((x - MARK_X) ** 2 + (y - MARK_Y) ** 2) / (2 * MOUND_R ** 2))
    if FIELD:
        # beyond the stone the field falls into a shallow dip and rises to a far ridge, gently rolling
        h = h - 2.4 * _sm(18, 115, y) + 6.0 * _sm(150, 330, y)
        h = h + _sm(22, 70, y) * (0.9 * np.sin(x / 47 + y / 63 + 0.7) + 0.5 * np.sin(x / 23 - y / 41 + 2.1) + 0.25 * np.sin(x / 11 + y / 17))
    return h
MARK_Z0 = float(ground_h(MARK_X, MARK_Y)) - arg('sink', 0.03)

def svg_poly(d):
    nums = [float(v) for v in re.findall(r'-?\d+\.?\d*', d)]
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]

def to_xz(p):        # SVG (x right, y down) to object space (x right, z up), centred
    return ((p[0] - 50) * S, (100 - p[1]) * S)

def rrect(rx=22, n=14):
    pts = []
    for cx, cy_, a0 in ((100 - rx, rx, -90), (100 - rx, 100 - rx, 0), (rx, 100 - rx, 90), (rx, rx, 180)):
        for i in range(n + 1):
            t = math.radians(a0 + 90 * i / n)
            pts.append((cx + rx * math.cos(t), cy_ + rx * math.sin(t)))
    return pts

def prism(name, pts2d, y0, y1):
    bm = bmesh.new()
    front = [bm.verts.new((x, y0, z)) for x, z in pts2d]
    back = [bm.verts.new((x, y1, z)) for x, z in pts2d]
    bm.faces.new(front[::-1] if True else front)
    bm.faces.new(back)
    n = len(pts2d)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], front[j], back[j], back[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    return ob

tile = prism('stone', [to_xz(p) for p in rrect()], -T / 2, T / 2)
cut_seam = prism('cut_seam', [to_xz(p) for p in svg_poly(GEO['seam'])], -T, T)
cut_cav = prism('cut_cav', [to_xz(p) for p in svg_poly(GEO['cav'])], -T, T)
# the outer arris is rounded first (18 mm, honed); the cut edges stay crisp, softened in the shader
bv = tile.modifiers.new('arris', 'BEVEL'); bv.width = arg('bevel', 0.018); bv.segments = 4; bv.limit_method = 'ANGLE'
bv.angle_limit = math.radians(35); bv.harden_normals = False
for c in (cut_seam, cut_cav):
    md = tile.modifiers.new('cut', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = c
    md.material_mode = 'TRANSFER'
    c.hide_render = True; c.hide_viewport = True

# the crystal: the gem hexagon cut as a low six-facet pyramid on each face, apex on the crystal's centre
gem = [to_xz(p) for p in svg_poly(GEO['gem'])]
cxz = to_xz((50, 51.5))
ZE, ZR = 0.04, T / 2 - 0.012     # a thin girdle rising to an apex flush with the faces of the stone
bm = bmesh.new()
fr = [bm.verts.new((x, -ZE, z)) for x, z in gem]
bk = [bm.verts.new((x, ZE, z)) for x, z in gem]
af = bm.verts.new((cxz[0], -ZR, cxz[1])); ab = bm.verts.new((cxz[0], ZR, cxz[1]))
n = len(gem)
for i in range(n):
    j = (i + 1) % n
    bm.faces.new((fr[i], fr[j], af)); bm.faces.new((bk[j], bk[i], ab))
    bm.faces.new((fr[j], fr[i], bk[i], bk[j]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new('crystal'); bm.to_mesh(me); bm.free()
crystal = bpy.data.objects.new('crystal', me); sc.collection.objects.link(crystal)
bvc = crystal.modifiers.new('arris', 'BEVEL'); bvc.width = 0.0025; bvc.segments = 2; bvc.limit_method = 'ANGLE'

mark = bpy.data.objects.new('mark', None); sc.collection.objects.link(mark)
mark.location = (MARK_X, MARK_Y, MARK_Z0); mark.rotation_euler = (0, 0, MARK_YAW)
for o in (tile, crystal, cut_seam, cut_cav): o.parent = mark
if arg('no-crystal', 0): crystal.hide_render = True
Z_OFF = 0.0
STONE = arg('stone', '')
if STONE:
    # the shared stone (directions/stone/stone.py): the same exact geometry, carved as an old monolith
    sys.path.insert(0, os.path.dirname(STONE)); import stone as stone_mod
    for o in (tile, crystal):
        o.hide_render = True; o.hide_viewport = True      # the simple stone stays built but unseen
    parts = stone_mod.build_stone(sc.collection, scale_m=100 * S, location=(MARK_X, MARK_Y, float(ground_h(np.array(MARK_X), np.array(MARK_Y)))),
                                  rotation=(0.012, -0.006, MARK_YAW), wetness=0.0, moss=arg('moss', 0.35), glow=0.15,
                                  thickness=T / (100 * S), detail=arg('detail', 380),
                                  **({'growth': False, 'carve': arg('carve', 0.0), 'chip_size': arg('chip-size', 1.0),
                                      'damp_foot': arg('damp-foot', 0.0), 'stone_value': arg('stone-value', 1.0)}
                                     if arg('clean-mark', 0) else {}))
    mark = parts['root']; Z_OFF = parts['info']['sink']
    # the grade reads these: stone and crystal held still in the loop, the crystal's colour held to sky
    def tag(ob, cr):
        if ob is None: return
        for ms_ in ob.material_slots:
            mt = ms_.material
            if mt is None or not mt.use_nodes: continue
            nt_ = mt.node_tree
            if any(n_.bl_idname == 'ShaderNodeOutputAOV' for n_ in nt_.nodes): continue
            aov(nt_, 'st', 1.0)
            if cr: aov(nt_, 'cr', 1.0, (600, -500))
    tag(parts['stone'], False); tag(parts['crystal'], True); tag(parts.get('veil'), True)
    BOUNCE = arg('bounce', 0.0)
    if BOUNCE > 0:
        # the warm bounce: low sun on the meadow in front throws a little warm light back up onto the honed
        # face, as a reflector would on set; linked to the stone alone, so the grass keeps its own light
        bl_ = bpy.data.lights.new('bounce', 'AREA'); bl_.shape = 'RECTANGLE'; bl_.size = 4.0; bl_.size_y = 1.5
        bl_.energy = BOUNCE; bl_.color = (1.0, 0.78, 0.55)
        bo_ = bpy.data.objects.new('bounce', bl_); sc.collection.objects.link(bo_)
        tgt = Vector((MARK_X, MARK_Y, float(ground_h(np.array(MARK_X), np.array(MARK_Y))) + 0.9))
        bo_.location = Vector((MARK_X - 2.2, MARK_Y - 4.5, tgt.z - 0.75))
        bo_.rotation_euler = (tgt - bo_.location).to_track_quat('-Z', 'Y').to_euler()
        rc_ = bpy.data.collections.new('bounce_receivers')
        for ob_ in (parts['stone'], parts['crystal']):
            if ob_ is not None: rc_.objects.link(ob_)
        bo_.light_linking.receiver_collection = rc_
    if SUN_OB is not None:
        cy.caustics_refractive = True
        stone_mod.mark_caustic_lights([SUN_OB])

# ---------------------------------------------------------------- the paper: a letter tucked into the seam (by night, low, by the crystal)
PAPER = arg('paper', 1)
paper_ob = None
PAPER_FOOT = None
if PAPER:
    m_pp, nt = mat('paper')
    pb = node(nt, 'ShaderNodeBsdfPrincipled', (0, 200)); pb.inputs['Base Color'].default_value = (0.84, 0.81, 0.74, 1)
    pb.inputs['Roughness'].default_value = 0.85; pb.inputs['Specular IOR Level'].default_value = 0.3
    ptl = node(nt, 'ShaderNodeBsdfTranslucent', (0, -100)); ptl.inputs['Color'].default_value = (0.95, 0.9, 0.8, 1)
    pms = node(nt, 'ShaderNodeMixShader', (250, 0)); pms.inputs['Fac'].default_value = 0.22
    link(nt, pb.outputs['BSDF'], pms.inputs[1]); link(nt, ptl.outputs['BSDF'], pms.inputs[2])
    psh = pms.outputs['Shader']
    if NIGHT:
        # faintly lit from within by the crystal's light, as paper glows by a lamp
        pe = node(nt, 'ShaderNodeEmission', (250, -250)); pe.inputs['Color'].default_value = (0.55, 0.85, 1.0, 1); pe.inputs['Strength'].default_value = 0.12
        pad_ = node(nt, 'ShaderNodeAddShader', (400, 0)); link(nt, psh, pad_.inputs[0]); link(nt, pe.outputs['Emission'], pad_.inputs[1]); psh = pad_.outputs['Shader']
    po = node(nt, 'ShaderNodeOutputMaterial', (600, 0)); link(nt, psh, po.inputs['Surface'])
    aov(nt, 'st', 1.0)
    # a folded letter, 12 by 9 cm showing: its left edge slid into the seam, the rest lying on the face,
    # its free edge lifting a little; turned to follow the seam
    sy = 14.0 if not NIGHT else 90.0
    tsl = math.tan(math.radians(16))
    # the seam's right edge at that height (break-geometry: the seam leans 16 degrees from vertical)
    right_edge = 64.6 - (sy - 12) * tsl if not NIGHT else 42.3 - (sy - 88) * tsl
    PWd, PHd, NU, NV = 0.18, 0.13, 12, 8
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
    grid = []
    for j in range(NV + 1):
        row = []
        for i in range(NU + 1):
            u, v = i / NU, j / NV
            x = -0.025 + u * (PWd + 0.025)            # the first 2.5 cm sits inside the seam
            y = -T / 2 - 0.0025
            if x < 0: y = -T / 2 + (-x) * 1.4          # turning into the slot
            y -= (max(u - 0.55, 0) / 0.45) ** 2 * 0.018  # the free edge lifts
            y -= 0.0025 * math.exp(-((v - 0.5) / 0.06) ** 2)  # the fold
            z = (v - 0.5) * PHd
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(NV):
        for i in range(NU):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('paper'); bm.to_mesh(me); bm.free()
    for p_ in me.polygons: p_.use_smooth = True
    paper_ob = bpy.data.objects.new('paper', me); sc.collection.objects.link(paper_ob); me.materials.append(m_pp)
    sol = paper_ob.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.0006
    paper_ob.parent = mark
    paper_ob.location = ((right_edge - 50) * S, 0, (100 - sy) * S - Z_OFF)
    paper_ob.rotation_euler = (0, math.radians(16), 0)
    if arg('paper-at', 'seam') == 'foot':
        # not in the seam (it read as a sticker): a folded sheet resting in the short grass at the stone's foot,
        # its two leaves opened into a low tent, in the low sun
        me.clear_geometry()
        PW, PL, NU, NV = arg('paper-w', 0.24), arg('paper-l', 0.17), 16, 12              # 24 by 17 cm folded sheet; the fold runs across its middle
        bm = bmesh.new(); grid = []
        for j in range(NV + 1):
            row = []
            for i in range(NU + 1):
                u, v = i / NU, j / NV
                x = (u - 0.5) * PW; y = (v - 0.5) * PL
                z = 0.028 * (1 - abs(2 * v - 1)) ** 0.9 + 0.006 * (abs(2 * u - 1)) ** 3 + 0.004 * math.sin(u * 5.0 + v * 2.0)
                row.append(bm.verts.new((x, y, z)))
            grid.append(row)
        for j in range(NV):
            for i in range(NU):
                bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
        for p_ in me.polygons: p_.use_smooth = True
        paper_ob.parent = None
        fx_, fy_ = MARK_X + arg('paper-dx', -0.95), MARK_Y - arg('paper-dy', 0.9)
        paper_ob.location = (fx_, fy_, float(ground_h(np.array(fx_), np.array(fy_))) + arg('paper-lift', 0.07))
        paper_ob.rotation_euler = (math.radians(arg('paper-tilt', 22.0)), math.radians(4), math.radians(arg('paper-rot', 28.0)))
        PAPER_FOOT = (fx_, fy_)

# stone: scanned seaside rock, darkened and honed (fine grain, soft sheen)
m_st, nt = mat('stone')
tco = node(nt, 'ShaderNodeTexCoord', (-1200, 0))
mpp = node(nt, 'ShaderNodeMapping', (-1000, 0)); mpp.inputs['Scale'].default_value = (0.9, 0.9, 0.9)
link(nt, tco.outputs['Object'], mpp.inputs['Vector'])
def boxtex(path, nc, loc):
    t = node(nt, 'ShaderNodeTexImage', loc); t.image = img(path, nc); t.projection = 'BOX'; t.projection_blend = 0.25
    link(nt, mpp.outputs['Vector'], t.inputs['Vector']); return t
ACG = arg('acg', '')
rk = os.path.join(ASSETS, 'seaside_rock'); ak = os.path.join(ACG, 'Rock041')
# two scanned stones (ambientCG Rock041, Poly Haven seaside_rock) blended by a soft noise so nothing tiles
nz = node(nt, 'ShaderNodeTexNoise', (-1000, 500)); nz.inputs['Scale'].default_value = 1.6; nz.inputs['Detail'].default_value = 3
link(nt, tco.outputs['Object'], nz.inputs['Vector'])
nzr = node(nt, 'ShaderNodeMapRange', (-850, 500)); nzr.inputs['From Min'].default_value = 0.42; nzr.inputs['From Max'].default_value = 0.62
link(nt, nz.outputs['Fac'], nzr.inputs['Value'])
def mixc(a, b, loc):
    mx_ = node(nt, 'ShaderNodeMix', loc); mx_.data_type = 'RGBA'
    link(nt, nzr.outputs['Result'], mx_.inputs['Factor']); link(nt, a, mx_.inputs['A']); link(nt, b, mx_.inputs['B'])
    return mx_.outputs['Result']
a_d = boxtex(os.path.join(ak, 'Rock041_2K-JPG_Color.jpg'), False, (-900, 250))
a_r = boxtex(os.path.join(ak, 'Rock041_2K-JPG_Roughness.jpg'), True, (-900, -50))
a_n = boxtex(os.path.join(ak, 'Rock041_2K-JPG_NormalGL.jpg'), True, (-900, -350))
b_d = boxtex(os.path.join(rk, 'seaside_rock_diff_2k.jpg'), False, (-700, 200))
b_r = boxtex(os.path.join(rk, 'seaside_rock_rough_2k.jpg'), True, (-700, -100))
b_n = boxtex(os.path.join(rk, 'seaside_rock_nor_gl_2k.jpg'), True, (-700, -400))
class _T:
    def __init__(s_, o): s_.outputs = {'Color': o}
td = _T(mixc(a_d.outputs['Color'], b_d.outputs['Color'], (-550, 250)))
tr = _T(mixc(a_r.outputs['Color'], b_r.outputs['Color'], (-550, -50)))
tn = _T(mixc(a_n.outputs['Color'], b_n.outputs['Color'], (-550, -350)))
hsv = node(nt, 'ShaderNodeHueSaturation', (-400, 200)); hsv.inputs['Saturation'].default_value = 0.12
hsv.inputs['Value'].default_value = arg('st-val', 0.45)
link(nt, td.outputs['Color'], hsv.inputs['Color'])
rr = node(nt, 'ShaderNodeMapRange', (-400, -100)); rr.inputs['To Min'].default_value = 0.28; rr.inputs['To Max'].default_value = 0.5
link(nt, tr.outputs['Color'], rr.inputs['Value'])
nm = node(nt, 'ShaderNodeNormalMap', (-400, -400)); nm.inputs['Strength'].default_value = 0.6
link(nt, tn.outputs['Color'], nm.inputs['Color'])
bsdf = node(nt, 'ShaderNodeBsdfPrincipled', (0, 0))
bsdf.inputs['Specular IOR Level'].default_value = 0.55
link(nt, hsv.outputs['Color'], bsdf.inputs['Base Color']); link(nt, rr.outputs['Result'], bsdf.inputs['Roughness'])
bvn = node(nt, 'ShaderNodeBevel', (-200, -400)); bvn.samples = 6; bvn.inputs['Radius'].default_value = 0.004
link(nt, nm.outputs['Normal'], bvn.inputs['Normal'])
link(nt, bvn.outputs['Normal'], bsdf.inputs['Normal'])
out = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, bsdf.outputs['BSDF'], out.inputs['Surface'])
aov(nt, 'st', 1.0)
tile.data.materials.append(m_st)
# the cut faces: the same stone, darker and unpolished, so the break reads as a cut and the crystal as seated
m_in = m_st.copy(); m_in.name = 'stone_cut'
for n_ in m_in.node_tree.nodes:
    if n_.bl_idname == 'ShaderNodeHueSaturation': n_.inputs['Value'].default_value = arg('cut-val', 0.07)
    if n_.bl_idname == 'ShaderNodeMapRange': n_.inputs['To Min'].default_value = 0.6; n_.inputs['To Max'].default_value = 0.8
# bake the cuts and give every face inside the outline (the walls of the seam and the cavity) the cut stone
dg = bpy.context.evaluated_depsgraph_get()
me_cut = bpy.data.meshes.new_from_object(tile.evaluated_get(dg))
tile.modifiers.clear(); old_me = tile.data; tile.data = me_cut
me_cut.materials.clear(); me_cut.materials.append(m_st); me_cut.materials.append(m_in)
HX = 50 * S; RC = 22 * S; ZC = 50 * S
def rr_sdf(x, z):
    qx = abs(x) - (HX - RC); qz = abs(z - ZC) - (HX - RC)
    return math.hypot(max(qx, 0), max(qz, 0)) + min(max(qx, qz), 0) - RC
for f in me_cut.polygons:
    c_ = f.center
    f.material_index = 1 if (abs(f.normal.y) < 0.6 and rr_sdf(c_.x, c_.z) < -0.012) else 0
tile.modifiers.new('wn', 'WEIGHTED_NORMAL')

# crystal: true glass, tinted so that light through both faces lands on sky #94E6FF
def srgb2lin(c): return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92
SKY = [srgb2lin(v / 255) for v in (0x94, 0xE6, 0xFF)]
m_cr, nt = mat('crystal')
# a sky crystal: clear glass skin over a translucent core, so it holds its own colour and glows when backlit
b = node(nt, 'ShaderNodeBsdfPrincipled', (0, 0))
b.inputs['Base Color'].default_value = (*[v ** 1.6 for v in SKY], 1)
b.inputs['Subsurface Weight'].default_value = 1.0
b.inputs['Subsurface Radius'].default_value = (0.35, 0.8, 1.0)
b.inputs['Subsurface Scale'].default_value = 0.12
b.inputs['Transmission Weight'].default_value = arg('cr-glass', 0.97)
b.inputs['Roughness'].default_value = arg('cr-rough', 0.05)
b.inputs['IOR'].default_value = 1.52
b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.02
# one cheat, as on a film set: refractive caustics are off (too noisy on CPU), so the low sun that would
# pour through the crystal is put back as a faint glow of its own colour
emc = node(nt, 'ShaderNodeEmission', (0, -300)); emc.inputs['Color'].default_value = (*SKY, 1)
emc.inputs['Strength'].default_value = arg('cr-glow', 0.7 if NIGHT else 0.2)
ad = node(nt, 'ShaderNodeAddShader', (200, 0)); link(nt, b.outputs['BSDF'], ad.inputs[0]); link(nt, emc.outputs['Emission'], ad.inputs[1])
o = node(nt, 'ShaderNodeOutputMaterial', (400, 0)); link(nt, ad.outputs['Shader'], o.inputs['Surface'])
aov(nt, 'st', 1.0); aov(nt, 'cr', 1.0, (600, -500))
crystal.data.materials.append(m_cr)

# ---------------------------------------------------------------- ground
# the field as a height field out to 600 m (the rise round the stone has its own finer mesh below)
_gx, _gy = np.meshgrid(np.linspace(-520, 520, 209), np.linspace(-40, 640, 273))
_gz = ground_h(_gx, _gy) - 0.004
bm = bmesh.new()
_vv = [[bm.verts.new((float(_gx[j, i]), float(_gy[j, i]), float(_gz[j, i]))) for i in range(_gx.shape[1])] for j in range(_gx.shape[0])]
for j in range(_gx.shape[0] - 1):
    for i in range(_gx.shape[1] - 1):
        bm.faces.new((_vv[j][i], _vv[j][i + 1], _vv[j + 1][i + 1], _vv[j + 1][i]))
_me = bpy.data.meshes.new('ground'); bm.to_mesh(_me); bm.free()
for p_ in _me.polygons: p_.use_smooth = True
gnd = bpy.data.objects.new('ground', _me); sc.collection.objects.link(gnd)
m_g, nt = mat('ground')
tco = node(nt, 'ShaderNodeTexCoord', (-1200, 0))
mpp = node(nt, 'ShaderNodeMapping', (-1000, 0)); mpp.inputs['Scale'].default_value = (0.55, 0.55, 0.55)
link(nt, tco.outputs['Object'], mpp.inputs['Vector'])
gpath = os.path.join(ACG, 'Grass004'); g2 = os.path.join(ACG, 'Ground037')
# world position, so the plane and the rise share one scale (metres); two scans blended by noise
gpos = node(nt, 'ShaderNodeNewGeometry', (-1400, 0))
mpp2 = node(nt, 'ShaderNodeMapping', (-1200, 0)); mpp2.inputs['Scale'].default_value = (0.5, 0.5, 0.5)
link(nt, gpos.outputs['Position'], mpp2.inputs['Vector'])
gn_ = node(nt, 'ShaderNodeTexNoise', (-1000, 600)); gn_.inputs['Scale'].default_value = 0.35; gn_.inputs['Detail'].default_value = 3
link(nt, gpos.outputs['Position'], gn_.inputs['Vector'])
gnr = node(nt, 'ShaderNodeMapRange', (-850, 600)); gnr.inputs['From Min'].default_value = 0.62; gnr.inputs['From Max'].default_value = 0.8
link(nt, gn_.outputs['Fac'], gnr.inputs['Value'])
def gtex(path, nc, loc):
    t = node(nt, 'ShaderNodeTexImage', loc); t.image = img(path, nc); link(nt, mpp2.outputs['Vector'], t.inputs['Vector']); return t
def gmix(a, b, loc):
    mx_ = node(nt, 'ShaderNodeMix', loc); mx_.data_type = 'RGBA'
    link(nt, gnr.outputs['Result'], mx_.inputs['Factor']); link(nt, a.outputs['Color'], mx_.inputs['A']); link(nt, b.outputs['Color'], mx_.inputs['B'])
    return mx_.outputs['Result']
gcol = gmix(gtex(os.path.join(gpath, 'Grass004_2K-JPG_Color.jpg'), False, (-700, 300)), gtex(os.path.join(g2, 'Ground037_2K-JPG_Color.jpg'), False, (-700, 100)), (-450, 200))
grou = gmix(gtex(os.path.join(gpath, 'Grass004_2K-JPG_Roughness.jpg'), True, (-700, -100)), gtex(os.path.join(g2, 'Ground037_2K-JPG_Roughness.jpg'), True, (-700, -250)), (-450, -150))
gnor = gmix(gtex(os.path.join(gpath, 'Grass004_2K-JPG_NormalGL.jpg'), True, (-700, -400)), gtex(os.path.join(g2, 'Ground037_2K-JPG_NormalGL.jpg'), True, (-700, -550)), (-450, -450))
nmg = node(nt, 'ShaderNodeNormalMap', (-300, -400)); link(nt, gnor, nmg.inputs['Color'])
bg_ = node(nt, 'ShaderNodeBsdfPrincipled', (-100, 0))
link(nt, gcol, bg_.inputs['Base Color']); bg_.inputs['Roughness'].default_value = 0.95
bg_.inputs['Specular IOR Level'].default_value = 0.12   # turf is matt: no sheen of sky at grazing angles
link(nt, nmg.outputs['Normal'], bg_.inputs['Normal'])
# far ground hands over to the photographed meadow: camera rays beyond ~40 m see the HDRI itself
lp = node(nt, 'ShaderNodeLightPath', (-400, 500))
geo = node(nt, 'ShaderNodeNewGeometry', (-900, 500))
ce = node(nt, 'ShaderNodeTexEnvironment', (-400, 300)); ce.image = env.image
mpw = node(nt, 'ShaderNodeMapping', (-600, 300)); mpw.inputs['Rotation'].default_value = mp.inputs['Rotation'].default_value
neg = node(nt, 'ShaderNodeVectorMath', (-750, 300), operation='SCALE'); neg.inputs['Scale'].default_value = -1
link(nt, geo.outputs['Incoming'], neg.inputs[0]); link(nt, neg.outputs['Vector'], mpw.inputs['Vector'])
link(nt, mpw.outputs['Vector'], ce.inputs['Vector'])
em = node(nt, 'ShaderNodeEmission', (-100, 300)); link(nt, ce.outputs['Color'], em.inputs['Color'])
if NIGHT: em.inputs['Strength'].default_value = 0.03
dist = node(nt, 'ShaderNodeMapRange', (-200, 600)); dist.inputs['From Min'].default_value = 1e6; dist.inputs['From Max'].default_value = 2e6
link(nt, lp.outputs['Ray Length'], dist.inputs['Value'])
fac = node(nt, 'ShaderNodeMath', (0, 600), operation='MULTIPLY')
link(nt, dist.outputs['Result'], fac.inputs[0]); link(nt, lp.outputs['Is Camera Ray'], fac.inputs[1])
mx = node(nt, 'ShaderNodeMixShader', (200, 0))
link(nt, fac.outputs['Value'], mx.inputs['Fac']); link(nt, bg_.outputs['BSDF'], mx.inputs[1]); link(nt, em.outputs['Emission'], mx.inputs[2])
o = node(nt, 'ShaderNodeOutputMaterial', (400, 0)); link(nt, mx.outputs['Shader'], o.inputs['Surface'])
gnd.data.materials.append(m_g)
# the stone stands on a low rise in the meadow
gx, gy = np.meshgrid(np.linspace(-9, 9, 73), np.linspace(-9, 9, 73))
gx = gx + MARK_X; gy = gy + MARK_Y
gz = ground_h(gx, gy)
bm = bmesh.new()
vv = [[bm.verts.new((float(gx[j, i]), float(gy[j, i]), float(gz[j, i]))) for i in range(73)] for j in range(73)]
for j in range(72):
    for i in range(72):
        bm.faces.new((vv[j][i], vv[j][i + 1], vv[j + 1][i + 1], vv[j + 1][i]))
me = bpy.data.meshes.new('mound'); bm.to_mesh(me); bm.free()
for p_ in me.polygons: p_.use_smooth = True
mound = bpy.data.objects.new('mound', me); sc.collection.objects.link(mound); me.materials.append(m_g)

# ---------------------------------------------------------------- grass
atlas_dir = os.path.join(ASSETS, 'grass_medium_01')
A_DIFF = img(os.path.join(atlas_dir, 'textures', 'grass_medium_01_diff_2k.jpg'))
A_ALPHA = img(os.path.join(atlas_dir, 'textures', 'grass_medium_01_alpha_2k.png'), True)

def grass_material(name, use_alpha, uv_tint=(1, 1, 1), trans=0.45, dry=0.0):
    m, nt = mat(name)
    uv = node(nt, 'ShaderNodeUVMap', (-1200, 0)); uv.uv_map = 'UVMap'
    t = node(nt, 'ShaderNodeTexImage', (-1000, 100)); t.image = A_DIFF
    link(nt, uv.outputs['UV'], t.inputs['Vector'])
    oi = node(nt, 'ShaderNodeObjectInfo', (-1200, -300))
    # per-instance variation: a little hue drift and some dry straw stems among the green
    hs = node(nt, 'ShaderNodeHueSaturation', (-750, 100))
    hj = node(nt, 'ShaderNodeMapRange', (-950, -250)); hj.inputs['To Min'].default_value = 0.47; hj.inputs['To Max'].default_value = 0.53
    link(nt, oi.outputs['Random'], hj.inputs['Value']); link(nt, hj.outputs['Result'], hs.inputs['Hue'])
    hs.inputs['Saturation'].default_value = 1.05; hs.inputs['Value'].default_value = 1.15
    link(nt, t.outputs['Color'], hs.inputs['Color'])
    drym = node(nt, 'ShaderNodeMix', (-550, 100)); drym.data_type = 'RGBA'; drym.blend_type = 'MIX'
    drythr = node(nt, 'ShaderNodeMath', (-750, -250), operation='GREATER_THAN'); drythr.inputs[1].default_value = 1 - dry
    link(nt, oi.outputs['Random'], drythr.inputs[0])
    dfac = node(nt, 'ShaderNodeMath', (-650, -250), operation='MULTIPLY'); dfac.inputs[1].default_value = 0.75
    link(nt, drythr.outputs['Value'], dfac.inputs[0])
    link(nt, dfac.outputs['Value'], drym.inputs['Factor'])
    link(nt, hs.outputs['Color'], drym.inputs['A']); drym.inputs['B'].default_value = (0.42, 0.36, 0.17, 1)
    tint = node(nt, 'ShaderNodeMix', (-350, 100)); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'
    tint.inputs['Factor'].default_value = 1.0; link(nt, drym.outputs['Result'], tint.inputs['A'])
    tint.inputs['B'].default_value = (*uv_tint, 1)
    p = node(nt, 'ShaderNodeBsdfPrincipled', (0, 200))
    link(nt, tint.outputs['Result'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.42; p.inputs['Specular IOR Level'].default_value = 0.45
    # light through the blade: brighter and yellower than the reflected colour
    tb = node(nt, 'ShaderNodeMix', (-150, -200)); tb.data_type = 'RGBA'; tb.blend_type = 'MULTIPLY'
    tb.inputs['Factor'].default_value = 1.0; link(nt, tint.outputs['Result'], tb.inputs['A'])
    tb.inputs['B'].default_value = (1.35, 1.6, 0.6, 1)
    tl = node(nt, 'ShaderNodeBsdfTranslucent', (0, -200)); link(nt, tb.outputs['Result'], tl.inputs['Color'])
    ms = node(nt, 'ShaderNodeMixShader', (250, 0)); ms.inputs['Fac'].default_value = trans
    link(nt, p.outputs['BSDF'], ms.inputs[1]); link(nt, tl.outputs['BSDF'], ms.inputs[2])
    sh = ms.outputs['Shader']
    if use_alpha:
        ta = node(nt, 'ShaderNodeTexImage', (-1000, -500)); ta.image = A_ALPHA
        link(nt, uv.outputs['UV'], ta.inputs['Vector'])
        tp = node(nt, 'ShaderNodeBsdfTransparent', (250, -300))
        ma = node(nt, 'ShaderNodeMixShader', (450, 0))
        link(nt, ta.outputs['Color'], ma.inputs['Fac']); link(nt, tp.outputs['BSDF'], ma.inputs[1]); link(nt, sh, ma.inputs[2])
        sh = ma.outputs['Shader']
    o = node(nt, 'ShaderNodeOutputMaterial', (700, 0)); link(nt, sh, o.inputs['Surface'])
    at = node(nt, 'ShaderNodeAttribute', (300, -500)); at.attribute_name = 'hf'
    aov(nt, 'hf', at.outputs['Fac'], (600, -400)); aov(nt, 'gm', 1.0, (600, -600))
    return m

M_BLADE = grass_material('blade', False, (0.85, 1.05, 0.7), 0.5, dry=0.12)
M_HEAD = grass_material('seedhead', True, (1.1, 1.05, 0.9), 0.6, dry=0.5)

COLS = [1612, 1664, 1710]
AY0, AY1 = 380, 1150
HEADS = [(1740, 1840, 20, 330), (1890, 2000, 30, 500), (1920, 2040, 460, 1140), (1395, 1445, 590, 1100)]

def blade_points(L, tilt, az, droop, rng_):
    pts = []; N = 7
    d = Vector((math.sin(tilt) * math.cos(az), math.sin(tilt) * math.sin(az), math.cos(tilt)))
    p = Vector((0, 0, 0)); step = L / N
    for i in range(N + 1):
        pts.append(p.copy())
        d = (d + Vector((math.cos(az), math.sin(az), 0)) * droop * (i / N) * 0.6 - Vector((0, 0, droop * (i / N) ** 2 * 0.5))).normalized()
        p = p + d * step
    return pts

def build_clump(name, nblades, hmin, hmax, heads=0, spread=0.07):
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); hfl = bm.verts.layers.float.new('hf')
    faces_head = []
    for k in range(nblades):
        L = rng.uniform(hmin, hmax); az = rng.uniform(0, 2 * math.pi)
        tilt = rng.uniform(0.04, 0.42); droop = rng.uniform(0.05, 0.6) * (L / hmax)
        base = Vector((rng.normal(0, spread), rng.normal(0, spread), 0))
        pts = blade_points(L, tilt, az, droop, rng)
        w0 = rng.uniform(0.004, 0.0085)
        side = Vector((-math.sin(az + rng.uniform(-0.6, 0.6)), math.cos(az + rng.uniform(-0.6, 0.6)), 0)).normalized()
        col = COLS[rng.integers(len(COLS))] + rng.uniform(-2, 2)
        u0, u1 = (col - 2.5) / 2048, (col + 2.5) / 2048
        vb = 1 - AY1 / 2048; vt = 1 - AY0 / 2048
        v_start = rng.uniform(vb, vb + 0.15)
        N = len(pts) - 1
        left, right = [], []
        for i, pnt in enumerate(pts):
            t = i / N
            w = w0 * (1 - t ** 1.6) + 0.0004
            tw = side * w
            a_ = bm.verts.new(base + pnt - tw); b_ = bm.verts.new(base + pnt + tw)
            a_[hfl] = t; b_[hfl] = t
            left.append((a_, t)); right.append((b_, t))
        for i in range(N):
            f = bm.faces.new((left[i][0], right[i][0], right[i + 1][0], left[i + 1][0]))
            for lp_ in f.loops:
                t = lp_.vert[hfl]; isr = lp_.vert in (right[i][0], right[i + 1][0])
                lp_[uvl].uv = (u1 if isr else u0, v_start + (vt - v_start) * t)
        if k < heads:
            # a seed head card at the top of this stem
            hx0, hx1, hy0, hy1 = HEADS[rng.integers(len(HEADS))]
            top = base + pts[-1]
            hh = rng.uniform(0.12, 0.2); hw = hh * (hx1 - hx0) / (hy1 - hy0)
            sd = Vector((math.cos(rng.uniform(0, math.pi)), math.sin(rng.uniform(0, math.pi)), 0))
            up = (pts[-1] - pts[-2]).normalized()
            q = [top - sd * hw / 2, top + sd * hw / 2, top + sd * hw / 2 + up * hh, top - sd * hw / 2 + up * hh]
            vs = [bm.verts.new(v) for v in q]
            for v in vs[:2]: v[hfl] = 1.0
            for v in vs[2:]: v[hfl] = 1.15
            f = bm.faces.new(vs); f.material_index = 1
            uvs = [(hx0 / 2048, 1 - hy1 / 2048), (hx1 / 2048, 1 - hy1 / 2048), (hx1 / 2048, 1 - hy0 / 2048), (hx0 / 2048, 1 - hy0 / 2048)]
            for lp_, uvv in zip(f.loops, uvs): lp_[uvl].uv = uvv
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    # bmesh float layer to a mesh attribute named hf
    me.materials.append(M_BLADE); me.materials.append(M_HEAD)
    for p_ in me.polygons: p_.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    return ob

lib = bpy.data.collections.new('grass_lib'); sc.collection.children.link(lib)
lib.hide_render = False
variants = []
for i in range(8):
    tall = i < 5
    ob = build_clump(f'clump{i}', 18 if tall else 26, 0.45 if tall else 0.25, 1.05 if tall else 0.6,
                     heads=(3 if tall else 0), spread=0.06 if tall else 0.08)
    lib.objects.link(ob); variants.append(ob)

# Poly Haven grass_medium_01 clumps as the lower layer
with bpy.data.libraries.load(os.path.join(atlas_dir, 'grass_medium_01_2k.blend'), link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.endswith('_LOD1') and any(s in n for s in ('large', 'mid', 'tall'))]
for ob in dst.objects:
    me = ob.data
    zs = [v.co.z for v in me.vertices]; zmax = max(zs) or 1
    at = me.attributes.new('hf', 'FLOAT', 'POINT')
    at.data.foreach_set('value', [max(0.0, z / zmax) for z in zs])
    ob.location = (0, 0, 0); ob.rotation_euler = (0, 0, 0)
    me.materials.clear(); me.materials.append(M_BLADE_PH := bpy.data.materials.get('ph_grass') or grass_material('ph_grass', True, (1.0, 1.0, 0.9), 0.45, dry=0.15))
    # Poly Haven clumps carry their own UVs into the same atlas
    if me.uv_layers and me.uv_layers[0].name != 'UVMap': me.uv_layers[0].name = 'UVMap'
    lib.objects.link(ob); variants.append(ob)
NV_TALL = 8

# daisies: thin stems with a white ray flower, slightly translucent
m_pet, nt = mat('petal')
p = node(nt, 'ShaderNodeBsdfPrincipled', (0, 200)); p.inputs['Base Color'].default_value = (0.85, 0.84, 0.8, 1); p.inputs['Roughness'].default_value = 0.5
tl = node(nt, 'ShaderNodeBsdfTranslucent', (0, -100)); tl.inputs['Color'].default_value = (1.0, 0.95, 0.85, 1)
ms = node(nt, 'ShaderNodeMixShader', (250, 0)); ms.inputs['Fac'].default_value = 0.4
link(nt, p.outputs['BSDF'], ms.inputs[1]); link(nt, tl.outputs['BSDF'], ms.inputs[2])
o = node(nt, 'ShaderNodeOutputMaterial', (500, 0)); link(nt, ms.outputs['Shader'], o.inputs['Surface'])
aov(nt, 'hf', 1.0); aov(nt, 'gm', 1.0, (600, -600))
m_disc, nt = mat('disc')
p = node(nt, 'ShaderNodeBsdfPrincipled', (0, 0)); p.inputs['Base Color'].default_value = (0.75, 0.48, 0.03, 1); p.inputs['Roughness'].default_value = 0.7
o = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, p.outputs['BSDF'], o.inputs['Surface'])
aov(nt, 'hf', 1.0); aov(nt, 'gm', 1.0, (600, -600))

def flower(name, h, npet, R, wv, pmat, dmat, disc_r, cup=0.0):
    bm = bmesh.new(); hfl = bm.verts.layers.float.new('hf'); uvl = bm.loops.layers.uv.new('UVMap')
    pts = blade_points(h, rng.uniform(0.02, 0.15), rng.uniform(0, 6.28), 0.05, rng)
    ring = []
    for i, pnt in enumerate(pts):
        t = i / (len(pts) - 1); r = 0.0016
        vs = [bm.verts.new(pnt + Vector((r * math.cos(a), r * math.sin(a), 0))) for a in (0, 2.1, 4.2)]
        for v in vs: v[hfl] = t
        ring.append(vs)
    for i in range(len(ring) - 1):
        for j in range(3):
            bm.faces.new((ring[i][j], ring[i][(j + 1) % 3], ring[i + 1][(j + 1) % 3], ring[i + 1][j]))
    top = pts[-1]; tiltv = Vector((rng.normal(0, 0.25), rng.normal(0, 0.25), 1)).normalized()
    rot = tiltv.to_track_quat('Z', 'Y')
    for k in range(npet):
        a = 2 * math.pi * k / npet + rng.normal(0, 0.05)
        loc = [Vector((0.002, -wv * 0.4, 0)), Vector((R * 0.6, -wv, cup * 0.5)), Vector((R, -wv * 0.6, cup)), Vector((R + 0.001, 0, cup)),
               Vector((R, wv * 0.6, cup)), Vector((R * 0.6, wv, cup * 0.5)), Vector((0.002, wv * 0.4, 0))]
        rz = Matrix.Rotation(a, 3, 'Z')
        vs = [bm.verts.new(top + rot @ (rz @ v)) for v in loc]
        for v in vs: v[hfl] = 1.0
        f = bm.faces.new(vs); f.material_index = 1
    disc = [bm.verts.new(top + rot @ Vector((disc_r * math.cos(a), disc_r * math.sin(a), 0.002))) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)]
    for v in disc: v[hfl] = 1.0
    f = bm.faces.new(disc); f.material_index = 2
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(M_BLADE); me.materials.append(pmat); me.materials.append(dmat)
    return bpy.data.objects.new(name, me)

def petal_mat(name, col, tcol, mix=0.45, glow=None):
    m, nt = mat(name)
    p = node(nt, 'ShaderNodeBsdfPrincipled', (0, 200)); p.inputs['Base Color'].default_value = (*col, 1); p.inputs['Roughness'].default_value = 0.45
    p.inputs['Specular IOR Level'].default_value = 0.5
    tl = node(nt, 'ShaderNodeBsdfTranslucent', (0, -100)); tl.inputs['Color'].default_value = (*tcol, 1)
    ms = node(nt, 'ShaderNodeMixShader', (250, 0)); ms.inputs['Fac'].default_value = mix
    link(nt, p.outputs['BSDF'], ms.inputs[1]); link(nt, tl.outputs['BSDF'], ms.inputs[2])
    sh = ms.outputs['Shader']
    if glow:
        e_ = node(nt, 'ShaderNodeEmission', (250, -250)); e_.inputs['Color'].default_value = (*glow[0], 1); e_.inputs['Strength'].default_value = glow[1]
        ad_ = node(nt, 'ShaderNodeAddShader', (400, 0)); link(nt, sh, ad_.inputs[0]); link(nt, e_.outputs['Emission'], ad_.inputs[1]); sh = ad_.outputs['Shader']
    o = node(nt, 'ShaderNodeOutputMaterial', (600, 0)); link(nt, sh, o.inputs['Surface'])
    aov(nt, 'hf', 1.0); aov(nt, 'gm', 1.0, (600, -600))
    return m
# yellow buttercups and a pale sky-blue flower (a flax-like five-petal), with the odd white daisy
m_yel = petal_mat('yellow', (0.85, 0.62, 0.02), (1.0, 0.75, 0.08))
m_blu = petal_mat('paleblue', (0.42, 0.66, 0.95), (0.55, 0.8, 1.0), glow=((0.09, 0.42, 1.0), arg('flower-glow', 2.2)) if NIGHT else None)
if NIGHT:
    m_pet = petal_mat('whiteglow', (0.85, 0.9, 0.95), (0.9, 0.95, 1.0), glow=((0.55, 0.8, 1.0), arg('flower-glow', 2.2) * 0.45))
m_eye = petal_mat('eye', (0.6, 0.55, 0.12), (0.6, 0.55, 0.12), 0.1)

flib = bpy.data.collections.new('flower_lib'); sc.collection.children.link(flib)
for i in range(4):
    flib.objects.link(flower(f'butter{i}', rng.uniform(0.5, 0.85), 5, rng.uniform(0.022, 0.028), 0.013, m_yel, m_eye, 0.003, cup=0.004))
for i in range(4):
    flib.objects.link(flower(f'flax{i}', rng.uniform(0.5, 0.9), 5, rng.uniform(0.017, 0.021), 0.01, m_blu, m_eye, 0.002, cup=0.002))
for i in range(2):
    flib.objects.link(flower(f'daisy{i}', rng.uniform(0.55, 0.85), 18, rng.uniform(0.018, 0.022), 0.0035, m_pet, m_disc, 0.0055, cup=-0.002))

# ---------------------------------------------------------------- night: far spires of rock standing in the mist, for scale
if NIGHT and arg('spires', 0):
    m_sp, nt = mat('spire')
    bp = node(nt, 'ShaderNodeBsdfPrincipled', (0, 0)); bp.inputs['Base Color'].default_value = (0.16, 0.17, 0.19, 1); bp.inputs['Roughness'].default_value = 0.9
    o = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, bp.outputs['BSDF'], o.inputs['Surface'])
    for k, (sx, sy, sh_, sr) in enumerate(((-62, 320, 95, 13), (-22, 420, 50, 9), (96, 360, 62, 10))):
        bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=sr, radius2=sr * 0.12, depth=sh_, location=(sx, sy, sh_ / 2 - 3))
        sp = bpy.context.object; sp.rotation_euler = (rng.normal(0, 0.06), rng.normal(0, 0.06), rng.uniform(0, 6))
        sp.data.materials.append(m_sp)
        sb = sp.modifiers.new('sub', 'SUBSURF'); sb.levels = 4; sb.render_levels = 4; sb.subdivision_type = 'SIMPLE'
        tx = bpy.data.textures.new(f'rock{k}', 'CLOUDS'); tx.noise_scale = 0.35; tx.noise_depth = 4
        dsp = sp.modifiers.new('disp', 'DISPLACE'); dsp.texture = tx; dsp.texture_coords = 'LOCAL'; dsp.strength = sr * 0.5; dsp.mid_level = 0.5

# ---------------------------------------------------------------- behind the stone: a hedgerow of scanned trees on the far ridge, a lone tree, distant hills
PH = arg('ph', '')
TREES = arg('trees', 1) and PH and not NIGHT
def ph_object(name, pick):
    path = os.path.join(PH, name, name + '_1k.blend')
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if pick(n)]
    coll = bpy.data.collections.new('lib_' + name)
    for ob in dst.objects:
        ob.location = (0, 0, 0); coll.objects.link(ob)
    return coll
def place(coll, loc, rotz, scale):
    e = bpy.data.objects.new('i_' + coll.name, None); e.instance_type = 'COLLECTION'; e.instance_collection = coll
    e.location = loc; e.rotation_euler = (0, 0, rotz); e.scale = (scale, scale, scale * rng.uniform(0.9, 1.15))
    sc.collection.objects.link(e); return e
if TREES:
    t_lib = [ph_object(n, lambda k: k.endswith('geometry_nodes')) for n in ('island_tree_01', 'island_tree_02', 'tree_small_02')]
    s_lib = [ph_object('shrub_01', lambda k: k.endswith('_LOD1'))]
    # the hedgerow: trees in loose groups with gaps, shrubs between, along a curve on the ridge
    xh = -260.0
    while xh < 280:
        yh = 285 + 35 * math.sin(xh / 95) + rng.normal(0, 6)
        zh = float(ground_h(np.array(xh), np.array(yh)))
        if rng.uniform() < 0.8:
            k = rng.integers(3); sc_ = (rng.uniform(2.0, 2.9) if k < 2 else rng.uniform(1.7, 2.3)) * arg('tree-scale', 1.0)
            place(t_lib[k], (xh, yh, zh - 0.3), rng.uniform(0, 6.28), sc_)
        for _ in range(rng.integers(3, 7)):
            xs = xh + rng.uniform(-6, 6); ys = yh + rng.uniform(-4, 4)
            place(s_lib[0], (xs, ys, float(ground_h(np.array(xs), np.array(ys))) - 0.3), rng.uniform(0, 6.28), rng.uniform(11, 19))
        xh += rng.uniform(4, 9) if rng.uniform() < 0.88 else rng.uniform(20, 35)
    # one lone tree in the field, left of the stone, for depth
    for (lx, ly, ls) in ():
        place(t_lib[0], (lx, ly, float(ground_h(np.array(lx), np.array(ly))) - 0.3), 1.3, ls)
    # distant hills, low and soft, kilometres off (the grade gives them their air)
    m_h, nt = mat('hills')
    hb = node(nt, 'ShaderNodeBsdfPrincipled', (0, 0)); hb.inputs['Base Color'].default_value = (0.05, 0.075, 0.035, 1); hb.inputs['Roughness'].default_value = 0.95
    o = node(nt, 'ShaderNodeOutputMaterial', (300, 0)); link(nt, hb.outputs['BSDF'], o.inputs['Surface'])
    angs = np.linspace(-1.25, 1.25, 241); rads = np.linspace(900, 3600, 41)
    bm = bmesh.new(); rows = []
    for r_ in rads:
        row = []
        for a_ in angs:
            x_ = r_ * math.sin(a_); y_ = r_ * math.cos(a_)
            h_ = (40 + 38 * math.sin(a_ * 5.1 + 0.4) + 22 * math.sin(a_ * 11.3 + 1.7) + 9 * math.sin(a_ * 27 + 0.3)) * float(_sm(900, 1700, r_)) * (0.55 + 0.45 * math.sin(r_ / 700 + a_ * 3))
            row.append(bm.verts.new((x_, y_, max(h_, 0) - 1.5)))
        rows.append(row)
    for j in range(len(rads) - 1):
        for i in range(len(angs) - 1):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    me = bpy.data.meshes.new('hills'); bm.to_mesh(me); bm.free()
    for p_ in me.polygons: p_.use_smooth = True
    hills = bpy.data.objects.new('hills', me); sc.collection.objects.link(hills); me.materials.append(m_h)

# ---------------------------------------------------------------- the far edge: a great escarpment, kilometres off, from scans
# Poly Haven coastal_cliff_01 and 02 (scanned cliff bands, 92 m and 41 m long) scaled up as a matte painter would,
# set end to end along a gentle arc so they read as one long gritstone edge standing over the land in haze.
ESC_D = arg('escarp', 0.0)
if ESC_D > 0 and PH and not NIGHT:
    ESC_H = arg('escarp-h', 480.0); A0, A1 = arg('escarp-a0', -6.0), arg('escarp-a1', 32.0)
    TURN = math.radians(arg('escarp-turn', 18.0))
    # the air's colour: the sky with its clouds smoothed away (a 64 by 32 copy), so the haze carries the
    # warm-to-cool sweep of the horizon but never paints a cloud onto the rock
    AIR_IMG = env.image.copy(); AIR_IMG.name = 'air'; AIR_IMG.scale(64, 32)
    def air(nt, mist=None):
        # aerial perspective, as the air does it: with distance the rock gives way to the colour of the sky a
        # little above it in the same direction (the sky the camera sees, so it matches the clouds behind)
        out_ = [n_ for n_ in nt.nodes if n_.bl_idname == 'ShaderNodeOutputMaterial'][0]
        # at kilometres the scan's colour blotches read as cloud: calm it towards one even dark rock, so the
        # edge stands as a solid layer and its scanned form carries it
        for pb_ in [n_ for n_ in nt.nodes if n_.bl_idname == 'ShaderNodeBsdfPrincipled']:
            bc_ = pb_.inputs['Base Color']
            if bc_.links:
                s0_ = bc_.links[0].from_socket
                mc_ = node(nt, 'ShaderNodeMix', (pb_.location.x - 200, pb_.location.y + 200)); mc_.data_type = 'RGBA'
                mc_.inputs['Factor'].default_value = arg('esc-calm', 0.7); mc_.inputs['B'].default_value = (0.085, 0.085, 0.075, 1)
                link(nt, s0_, mc_.inputs['A']); link(nt, mc_.outputs['Result'], bc_)
        src_ = out_.inputs['Surface'].links[0].from_socket
        g_ = node(nt, 'ShaderNodeNewGeometry', (-600, 900))
        ng_ = node(nt, 'ShaderNodeVectorMath', (-450, 900), operation='SCALE'); ng_.inputs['Scale'].default_value = -1
        link(nt, g_.outputs['Incoming'], ng_.inputs[0])
        up_ = node(nt, 'ShaderNodeVectorMath', (-300, 900), operation='ADD'); up_.inputs[1].default_value = (0, 0, arg('air-lift', 0.035))
        link(nt, ng_.outputs['Vector'], up_.inputs[0])
        mpa = node(nt, 'ShaderNodeMapping', (-150, 900)); mpa.inputs['Rotation'].default_value = mp.inputs['Rotation'].default_value
        link(nt, up_.outputs['Vector'], mpa.inputs['Vector'])
        ea = node(nt, 'ShaderNodeTexEnvironment', (0, 900)); ea.image = AIR_IMG; link(nt, mpa.outputs['Vector'], ea.inputs['Vector'])
        ea.interpolation = 'Cubic'
        em_ = node(nt, 'ShaderNodeEmission', (200, 900)); link(nt, ea.outputs['Color'], em_.inputs['Color'])
        cd_ = node(nt, 'ShaderNodeCameraData', (-300, 1150))
        fd_ = node(nt, 'ShaderNodeMath', (-100, 1150), operation='MULTIPLY'); fd_.inputs[1].default_value = -1.0 / arg('air-k', 6000.0)
        link(nt, cd_.outputs['View Distance'], fd_.inputs[0])
        ex_ = node(nt, 'ShaderNodeMath', (50, 1150), operation='EXPONENT'); link(nt, fd_.outputs['Value'], ex_.inputs[0])
        iv_ = node(nt, 'ShaderNodeMath', (200, 1150), operation='SUBTRACT'); iv_.inputs[0].default_value = 1.0; link(nt, ex_.outputs['Value'], iv_.inputs[1])
        cap_ = node(nt, 'ShaderNodeMath', (300, 1150), operation='MULTIPLY'); cap_.inputs[1].default_value = arg('air-max', 0.5)
        link(nt, iv_.outputs['Value'], cap_.inputs[0])
        # the base sinks into a low haze: more air in the lowest part of the edge
        gz_ = node(nt, 'ShaderNodeSeparateXYZ', (-300, 1350)); link(nt, g_.outputs['Position'], gz_.inputs['Vector'])
        lm_ = node(nt, 'ShaderNodeMapRange', (-100, 1350)); lm_.interpolation_type = 'SMOOTHSTEP'
        lm_.inputs['From Min'].default_value = arg('mist-h', 160.0); lm_.inputs['From Max'].default_value = -20.0
        lm_.inputs['To Min'].default_value = 0.0; lm_.inputs['To Max'].default_value = arg('mist', 0.45) if mist is None else mist
        link(nt, gz_.outputs['Z'], lm_.inputs['Value'])
        ad2 = node(nt, 'ShaderNodeMath', (450, 1150), operation='ADD'); ad2.use_clamp = True
        link(nt, cap_.outputs['Value'], ad2.inputs[0]); link(nt, lm_.outputs['Result'], ad2.inputs[1])
        mxa = node(nt, 'ShaderNodeMixShader', (400, 900)); link(nt, ad2.outputs['Value'], mxa.inputs['Fac'])
        link(nt, src_, mxa.inputs[1]); link(nt, em_.outputs['Emission'], mxa.inputs[2])
        link(nt, mxa.outputs['Shader'], out_.inputs['Surface'])
    libs = []
    for nm_, lod_ in (('coastal_cliff_01', '_LOD1'), ('coastal_cliff_02', '_LOD2')):
        path = os.path.join(PH, nm_, nm_ + '_1k.blend')
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n.endswith(lod_)]
        ob = dst.objects[0]
        bb = [Vector(c) for c in ob.bound_box]
        cx0 = (min(v.x for v in bb) + max(v.x for v in bb)) / 2; cy0 = (min(v.y for v in bb) + max(v.y for v in bb)) / 2
        me = ob.data
        me.transform(Matrix.Translation((-cx0, -cy0, -min(v.z for v in bb))))   # base centre at the origin
        for ms_ in me.materials:
            if ms_ is not None and ms_.use_nodes and not any(n_.bl_idname == 'ShaderNodeOutputAOV' for n_ in ms_.node_tree.nodes):
                aov(ms_.node_tree, 'ld', 1.0)
                air(ms_.node_tree)
        coll = bpy.data.collections.new('lib_' + nm_); coll.objects.link(ob)
        libs.append((coll, ob.dimensions.x, ob.dimensions.z))
    def edge_line(rn_, an_, rf_, af_, H_, taper_end=0.0):
        # one edge from (r, angle) near to far, angles in degrees right of the view; taper_end > 0 lets the
        # last part of it break down and sink into the land instead of ending in a cut
        an_, af_ = math.radians(an_), math.radians(af_)
        P0 = Vector((rn_ * math.sin(an_), rn_ * math.cos(an_), 0)); P1 = Vector((rf_ * math.sin(af_), rf_ * math.cos(af_), 0))
        dl = (P1 - P0); Ltot = dl.length; dl.normalize()
        nrm = Vector((-dl.y, dl.x, 0))
        if nrm.dot(-P0) < 0: nrm = -nrm                        # the face looks back towards the camera side
        # turned a little towards the sun, so its upper ledges and top edge catch a rim of light
        a_s = math.radians(SUN_AZ); sh_ = Vector((-math.sin(a_s), math.cos(a_s), 0))
        tsign = 1.0 if nrm.cross(sh_).z > 0 else -1.0
        tt = -0.08 * Ltot
        while tt < Ltot * 1.05:
            k = 0 if rng.uniform() < 0.8 else 1
            coll, Lx, Hz = libs[k]
            f = H_ / Hz * rng.uniform(0.85, 1.1) * (0.8 if k else 1.0)
            span = Lx * f * 0.72
            c_ = P0 + dl * (tt + span / 2) + nrm * rng.normal(0, 0.03 * span)
            e = bpy.data.objects.new('i_' + coll.name, None); e.instance_type = 'COLLECTION'; e.instance_collection = coll
            # local -Y (the scan's face) turned onto the normal, then towards the light
            e.rotation_euler = (0, 0, math.atan2(nrm.x, -nrm.y) + tsign * TURN + rng.normal(0, 0.06))
            flip = -1 if rng.uniform() < 0.5 else 1
            e.scale = (f * flip, f, f)
            tp = (tt + span / 2) / Ltot
            sink_ = rng.uniform(0.2, 0.35) + (taper_end * max(0.0, (tp - (1 - taper_end))) / max(taper_end, 1e-6) * 0.7 if taper_end > 0 else 0)
            e.location = (c_.x, c_.y, -Hz * f * sink_)
            sc.collection.objects.link(e)
            tt += span
    if TREES and arg('hills-air', 1):
        # the nearer hills take the same air and land mask, so they read as a darker layer in front of the edge
        # (left to the grade they washed out to a pale wedge with a hard edge)
        aov(m_h.node_tree, 'ld', 1.0); air(m_h.node_tree, mist=arg('hills-mist', 0.15))
    if arg('escarp-line', 1):
        edge_line(arg('esc-near-r', 3600.0), arg('esc-near-a', 30.0), arg('esc-far-r', 15000.0), arg('esc-far-a', -14.0), ESC_H)
        if arg('spur', 0):
            # a nearer, lower spur in front of the edge on the right: darker, less air, so the land layers
            edge_line(arg('spur-near-r', 2100.0), arg('spur-near-a', 26.0), arg('spur-far-r', 4200.0), arg('spur-far-a', 8.0),
                      arg('spur-h', 260.0), taper_end=0.45)
    ang = math.radians(A0)
    while ang < math.radians(A1) and not arg('escarp-line', 1):
        k = 0 if rng.uniform() < 0.75 else 1
        coll, Lx, Hz = libs[k]
        # the edge rises out of the land, stands, and breaks down again: a height envelope across its length
        tpos = (ang - math.radians(A0)) / max(1e-6, math.radians(A1 - A0))
        envh = 0.3 + 0.7 * math.sin(math.pi * min(1.0, max(0.0, tpos * 1.25 - 0.05))) ** 0.6
        f = ESC_H / Hz * envh * rng.uniform(0.82, 1.12) * (0.8 if k else 1.0)
        span = Lx * max(f, ESC_H / Hz * 0.6) * 0.7
        r_ = ESC_D * (1 + 0.04 * math.sin(ang * 9))
        mid = ang + span / 2 / r_
        px, py = r_ * math.sin(mid), r_ * math.cos(mid)
        e = bpy.data.objects.new('i_' + coll.name, None); e.instance_type = 'COLLECTION'; e.instance_collection = coll
        # face the camera (the scan's face looks down -Y), turned a little towards the light
        e.rotation_euler = (0, 0, math.atan2(-px, py) + TURN + rng.normal(0, 0.05))
        flip = -1 if rng.uniform() < 0.5 else 1
        e.scale = (f * flip, f, f)
        e.location = (px, py, -Hz * f * rng.uniform(0.12, 0.38))
        sc.collection.objects.link(e)
        ang += span / r_
    # the land runs on under the edge: the far hills carried out past it
    if TREES:
        angs = np.linspace(-1.25, 1.25, 181); rads = np.linspace(3400, (arg('esc-far-r', 15000.0) if arg('escarp-line', 1) else ESC_D) * 1.15, 40)
        bm = bmesh.new(); rows = []
        for r_ in rads:
            row = []
            for a_ in angs:
                x_ = r_ * math.sin(a_); y_ = r_ * math.cos(a_)
                h_ = (45 + 30 * math.sin(a_ * 7.1 + 0.4) + 16 * math.sin(a_ * 17.3 + 1.7)) * (0.6 + 0.4 * math.sin(r_ / 900 + a_ * 4))
                row.append(bm.verts.new((x_, y_, max(h_, 0) - 2)))
            rows.append(row)
        for j in range(len(rads) - 1):
            for i in range(len(angs) - 1):
                bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
        me = bpy.data.meshes.new('farland'); bm.to_mesh(me); bm.free()
        for p_ in me.polygons: p_.use_smooth = True
        fl = bpy.data.objects.new('farland', me); sc.collection.objects.link(fl); me.materials.append(m_h)

# ---------------------------------------------------------------- cloud shadows on the land
# A gobo high over the land, invisible to everything but shadow rays, and even then it only stops rays
# that travel within a degree or two of the sun: so it lays the shadows of passing cumulus on the land
# from the low sun without dimming the sky light. Its pattern is placed on the ground (each gobo point
# is the ground point it shades plus the climb to the sun), kept clear over the stone and the near field.
CLOUDS = arg('clouds', 0.0)
if CLOUDS > 0 and SUN_OB is not None:
    HC = 450.0
    el = math.radians(arg('sun-el', 4.6))
    dsun = (SUN_OB.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    off = dsun * (HC / dsun.z)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(off.x, off.y + 4000, HC))
    gb = bpy.context.object; gb.name = 'cloud_gobo'; gb.scale = (40000, 40000, 1)
    for v_ in ('visible_camera', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter'):
        setattr(gb, v_, False)
    gb.visible_shadow = True
    m_gb, nt = mat('gobo')
    geo_ = node(nt, 'ShaderNodeNewGeometry', (-1400, 0))
    gp = node(nt, 'ShaderNodeVectorMath', (-1200, 0), operation='SUBTRACT'); gp.inputs[1].default_value = tuple(off)
    link(nt, geo_.outputs['Position'], gp.inputs[0])
    sep = node(nt, 'ShaderNodeSeparateXYZ', (-1000, -300)); link(nt, gp.outputs['Vector'], sep.inputs['Vector'])
    gsc = node(nt, 'ShaderNodeVectorMath', (-1000, 0), operation='MULTIPLY')
    gsc.inputs[1].default_value = (1 / arg('cloud-size', 260.0), 1 / (arg('cloud-size', 260.0) * 1.6), 0)
    link(nt, gp.outputs['Vector'], gsc.inputs[0])
    gofs = node(nt, 'ShaderNodeVectorMath', (-850, 0), operation='ADD'); gofs.inputs[1].default_value = (arg('cloud-seed', 3.0), 1.7, 0.5)
    link(nt, gsc.outputs['Vector'], gofs.inputs[0])
    nz_ = node(nt, 'ShaderNodeTexNoise', (-700, 0)); nz_.noise_dimensions = '3D'
    nz_.inputs['Scale'].default_value = 1.0; nz_.inputs['Detail'].default_value = 4; nz_.inputs['Roughness'].default_value = 0.55
    link(nt, gofs.outputs['Vector'], nz_.inputs['Vector'])
    cv = node(nt, 'ShaderNodeMapRange', (-500, 0)); cv.interpolation_type = 'SMOOTHSTEP'
    cv.inputs['From Min'].default_value = arg('cloud-lo', 0.47); cv.inputs['From Max'].default_value = arg('cloud-lo', 0.47) + 0.09
    link(nt, nz_.outputs['Fac'], cv.inputs['Value'])
    # kept clear: the stone and the meadow round it (out to the dip)
    dst_ = node(nt, 'ShaderNodeVectorMath', (-800, -500), operation='DISTANCE'); dst_.inputs[1].default_value = (MARK_X, MARK_Y, 0)
    cmb = node(nt, 'ShaderNodeCombineXYZ', (-900, -500)); link(nt, sep.outputs['X'], cmb.inputs['X']); link(nt, sep.outputs['Y'], cmb.inputs['Y'])
    link(nt, cmb.outputs['Vector'], dst_.inputs[0])
    clr = node(nt, 'ShaderNodeMapRange', (-600, -500)); clr.interpolation_type = 'SMOOTHSTEP'
    clr.inputs['From Min'].default_value = arg('cloud-clear', 55.0); clr.inputs['From Max'].default_value = arg('cloud-clear', 55.0) * 1.8
    link(nt, dst_.outputs['Value'], clr.inputs['Value'])
    op_ = node(nt, 'ShaderNodeMath', (-300, 0), operation='MULTIPLY'); link(nt, cv.outputs['Result'], op_.inputs[0]); link(nt, clr.outputs['Result'], op_.inputs[1])
    # only rays on their way to the sun
    dd_ = node(nt, 'ShaderNodeVectorMath', (-800, 400), operation='DOT_PRODUCT'); dd_.inputs[1].default_value = tuple(-dsun)
    link(nt, geo_.outputs['Incoming'], dd_.inputs[0])
    dm_ = node(nt, 'ShaderNodeMapRange', (-600, 400)); dm_.interpolation_type = 'SMOOTHSTEP'
    dm_.inputs['From Min'].default_value = math.cos(math.radians(3.0)); dm_.inputs['From Max'].default_value = math.cos(math.radians(1.2))
    link(nt, dd_.outputs['Value'], dm_.inputs['Value'])
    op2 = node(nt, 'ShaderNodeMath', (-150, 0), operation='MULTIPLY'); link(nt, op_.outputs['Value'], op2.inputs[0]); link(nt, dm_.outputs['Result'], op2.inputs[1])
    op3 = node(nt, 'ShaderNodeMath', (0, 0), operation='MULTIPLY'); op3.inputs[1].default_value = CLOUDS; link(nt, op2.outputs['Value'], op3.inputs[0])
    tr_ = node(nt, 'ShaderNodeBsdfTransparent', (0, 200)); hb_ = node(nt, 'ShaderNodeBsdfDiffuse', (0, -200)); hb_.inputs['Color'].default_value = (0, 0, 0, 1)
    mx_ = node(nt, 'ShaderNodeMixShader', (200, 0)); link(nt, op3.outputs['Value'], mx_.inputs['Fac'])
    link(nt, tr_.outputs['BSDF'], mx_.inputs[1]); link(nt, hb_.outputs['BSDF'], mx_.inputs[2])
    o_ = node(nt, 'ShaderNodeOutputMaterial', (400, 0)); link(nt, mx_.outputs['Shader'], o_.inputs['Surface'])
    gb.data.materials.append(m_gb)

# ---------------------------------------------------------------- camera
CAM_H = arg('cam-h', 1.0)
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam_d.lens = arg('lens', 50.0); cam_d.sensor_width = 36; cam_d.sensor_fit = 'HORIZONTAL'
pitch = math.radians(arg('pitch', 2.0)); yaw = 0.0
if CROP == 'phone':
    # portrait framing from the same spot: turn towards the stone, a longer view up into the sky
    cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.lens = 50
    yaw = -math.atan2(MARK_X - 0.05, MARK_Y); pitch = math.radians(6.5)
cam.location = (0, 0, CAM_H)
cam.rotation_euler = (math.pi / 2 + pitch, 0, yaw)
cam_d.dof.use_dof = True
cam_d.dof.focus_distance = math.hypot(MARK_X, MARK_Y) - 0.15
cam_d.dof.aperture_fstop = arg('fstop', 2.2)
cam_d.dof.aperture_blades = 7; cam_d.dof.aperture_rotation = math.radians(10)
cam_d.clip_start = 0.05; cam_d.clip_end = 2000 if ESC_D <= 0 else 30000

# ---------------------------------------------------------------- scatter (numpy) and instance with geometry nodes
cam_fwd = Vector((math.sin(-yaw) * -1, math.cos(yaw), 0)) if False else (cam.matrix_world.to_3x3() @ Vector((0, 0, -1)))
half = math.atan(18 / cam_d.lens) + math.radians(12) if CROP != 'phone' else math.radians(28)
base_yaw = math.atan2(cam_fwd.x, cam_fwd.y)

def sample(n_target, rmin, rmax, dens):
    # area-uniform samples in a wedge around the view, thinned by a density profile dens(r) in [0, 1]
    th = rng.uniform(-half, half, n_target)
    r = np.sqrt(rng.uniform(rmin ** 2, rmax ** 2, n_target))
    keep = rng.uniform(0, 1, n_target) < dens(r)
    th, r = th[keep], r[keep]
    x = r * np.sin(base_yaw + th); y = r * np.cos(base_yaw + th)
    return x, y

def outside_mark(x, y):
    # never on the stone: drop points inside its footprint (plus a hand's width)
    c, s_ = math.cos(-MARK_YAW), math.sin(-MARK_YAW)
    lx = (x - MARK_X) * c - (y - MARK_Y) * s_; ly = (x - MARK_X) * s_ + (y - MARK_Y) * c
    keep = ~((np.abs(lx) < 50 * S + 0.03) & (np.abs(ly) < T / 2 + 0.03))
    if PAPER_FOOT is not None:
        # a little clearing where the sheet rests, so it lies on the short grass and is never buried
        keep &= np.hypot(x - PAPER_FOOT[0], y - PAPER_FOOT[1]) > arg('paper-clear', 0.32)
    return keep

FRONT_THIN = arg('front-thin', 0.7)
WIND = arg('wind', 0.0)            # radians of lean at the crest of a gust (0 is still air)
WIND_AZ = arg('wind-az', -50.0)    # direction the wind blows towards, degrees from +x
_ph = rng.uniform(0, 6.28, (2, 4)); _fq = rng.uniform(0.12, 0.45, (2, 4, 2))
def patch(x, y, k):
    # a soft 0..1 field of clumps and thinner ground, a few metres across
    v = sum(np.sin(x * _fq[k, i, 0] + y * _fq[k, i, 1] + _ph[k, i]) for i in range(4)) / 4
    return np.clip(0.5 + 0.9 * v, 0, 1)
NEAR_MIN = arg('near-min', 0.7)
def scatter(name, coll, n, rmin, rmax, dens, nvar, scale_rng, seed_off=0, pick_bias=None, around=None):
    if around:
        cx_, cy_, r0_, r1_ = around
        a_ = rng.uniform(0, 2 * math.pi, n); rr_ = np.sqrt(rng.uniform(r0_ ** 2, r1_ ** 2, n))
        x, y = cx_ + rr_ * np.cos(a_), cy_ + rr_ * np.sin(a_)
    else:
        x, y = sample(n, rmin, rmax, dens)
    ok = outside_mark(x, y)
    front = (np.abs(x - MARK_X) < 1.2 + 0.12 * (MARK_Y - y)) & (y < MARK_Y) & (y > MARK_Y - 7.0)
    if not around: ok &= ~(front & (rng.uniform(0, 1, len(x)) < FRONT_THIN))
    ok &= rng.uniform(0, 1, len(x)) < 0.45 + 0.55 * patch(x, y, 1)
    x, y = x[ok], y[ok]
    m = len(x)
    verts = np.zeros((m, 3), np.float32); verts[:, 0] = x; verts[:, 1] = y; verts[:, 2] = ground_h(x, y) - 0.01
    me = bpy.data.meshes.new(name); me.vertices.add(m); me.vertices.foreach_set('co', verts.ravel())
    rot = np.zeros((m, 3), np.float32); rot[:, 2] = rng.uniform(0, 2 * math.pi, m)
    rot[:, 0] = rng.normal(0, 0.04, m); rot[:, 1] = rng.normal(0, 0.04, m)
    if WIND > 0:
        # wind made visible: every clump leans the same way, more in broad travelling bands (gusts
        # rolling through the field), composed after the clump's own random heading
        wa = math.radians(WIND_AZ)
        u_ = (x * math.cos(wa) + y * math.sin(wa))
        band = 0.5 + 0.5 * np.sin(u_ / 7.5 + 0.8 * np.sin(x / 19.0 - y / 23.0)) * np.sin(u_ / 3.1 + 1.7)
        th = (WIND * (0.3 + 0.7 * band) * rng.uniform(0.7, 1.3, m)).astype(np.float64)
        cz, sz = np.cos(rot[:, 2]), np.sin(rot[:, 2]); cy_, sy_ = np.cos(rot[:, 1]), np.sin(rot[:, 1]); cx_, sx_ = np.cos(rot[:, 0]), np.sin(rot[:, 0])
        E = np.empty((m, 3, 3))
        E[:, 0, 0] = cz * cy_; E[:, 0, 1] = cz * sy_ * sx_ - sz * cx_; E[:, 0, 2] = cz * sy_ * cx_ + sz * sx_
        E[:, 1, 0] = sz * cy_; E[:, 1, 1] = sz * sy_ * sx_ + cz * cx_; E[:, 1, 2] = sz * sy_ * cx_ - cz * sx_
        E[:, 2, 0] = -sy_; E[:, 2, 1] = cy_ * sx_; E[:, 2, 2] = cy_ * cx_
        k_ = np.array([-math.sin(wa), math.cos(wa), 0.0])          # lean axis: up crossed with the wind
        K = np.array([[0, -k_[2], k_[1]], [k_[2], 0, -k_[0]], [-k_[1], k_[0], 0]])
        Lr = np.eye(3)[None] + np.sin(th)[:, None, None] * K[None] + (1 - np.cos(th))[:, None, None] * (K @ K)[None]
        M_ = Lr @ E
        rot[:, 1] = -np.arcsin(np.clip(M_[:, 2, 0], -1, 1)); rot[:, 0] = np.arctan2(M_[:, 2, 1], M_[:, 2, 2]); rot[:, 2] = np.arctan2(M_[:, 1, 0], M_[:, 0, 0])
    dm = np.hypot(x - MARK_X, y - MARK_Y)
    fr_ = (np.abs(x - MARK_X) < 1.2 + 0.12 * (MARK_Y - y)) & (y < MARK_Y) & (y > MARK_Y - 7.0)
    near = NEAR_MIN + (1 - NEAR_MIN) * np.clip((dm - 1.2) / 3.0, 0, 1)
    # a trodden way up to the stone: short in front of it, full height at its sides and back
    lane = np.where(fr_, (0.45 if around else 0.22) + (0.55 if around else 0.78) * np.clip((MARK_Y - y - 0.6) / 5.0, 0, 1), 1.0)
    sc_ = (rng.uniform(*scale_rng, m) * near * lane * (0.7 + 0.55 * patch(x, y, 0))).astype(np.float32)
    scl = np.stack([sc_, sc_, sc_ * rng.uniform(0.85, 1.2, m)], 1).astype(np.float32)
    pick = (pick_bias(m) if pick_bias else rng.integers(0, nvar, m)).astype(np.int32)
    for an, data, tp in (('rot', rot, 'FLOAT_VECTOR'), ('scl', scl, 'FLOAT_VECTOR'), ('pick', pick, 'INT')):
        at = me.attributes.new(an, tp, 'POINT')
        at.data.foreach_set('vector' if tp == 'FLOAT_VECTOR' else 'value', data.ravel())
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
    L.new(gi.outputs[0], m2p.inputs['Mesh']); L.new(m2p.outputs['Points'], iop.inputs['Points'])
    L.new(ci.outputs[0], iop.inputs['Instance'])
    L.new(na['pick'].outputs['Attribute'], iop.inputs['Instance Index'])
    L.new(na['rot'].outputs['Attribute'], iop.inputs['Rotation'])
    L.new(na['scl'].outputs['Attribute'], iop.inputs['Scale'])
    L.new(iop.outputs['Instances'], go.inputs[0])
    md = ob.modifiers.new('scatter', 'NODES'); md.node_group = ng
    print(name, m, 'instances')
    return ob

D = DENSITY
# children are picked in name order: butter0 to 3 (yellow), daisy0 to 1 (white), flax0 to 3 (pale blue)
FLOWER_P = ([0, 0, 0, 0, .05, .05, .225, .225, .225, .225] if NIGHT else [.14, .14, .14, .14, .06, .06, .08, .08, .08, .08])
nvar_all = len(variants)
def pick_mix(m):
    tall = rng.integers(0, NV_TALL, m); ph = rng.integers(NV_TALL, nvar_all, m)
    return np.where(rng.uniform(0, 1, m) < 0.55, tall, ph)
def dens_near(r): return np.clip(1.0 - (r - 14) / 40, 0.25, 1.0)
scatter('meadow', lib, int(60000 * D), 1.2, 60, dens_near, nvar_all, (0.9, 1.35), pick_bias=pick_mix)
scatter('meadow_far', lib, int(70000 * D), 55, 190, lambda r: np.clip(1.1 - (r - 55) / 160, 0.15, 1), nvar_all, (2.0, 3.0), pick_bias=lambda m: rng.integers(NV_TALL, nvar_all, m))
scatter('meadow_ph', lib, int(30000 * D), 1.2, 30, lambda r: np.ones_like(r), nvar_all, (1.6, 2.3),
        pick_bias=lambda m: rng.integers(NV_TALL, nvar_all, m))
scatter('turf', lib, int(22000 * D), 0.0, 60, lambda r: np.ones_like(r), nvar_all, (1.1, 1.6),
        pick_bias=lambda m: rng.integers(NV_TALL, nvar_all, m), around=(MARK_X, MARK_Y, 0.35, 4.0))
scatter('flowers', flib, int((26000 if NIGHT else 16000) * D), 1.2, 45, (lambda r: np.clip(1.5 - r / 9, 0.1, 1)) if NIGHT else (lambda r: np.clip(1.2 - r / 45, 0.2, 1)), 10, (0.55, 1.35) if NIGHT else (0.9, 1.3),
        pick_bias=lambda m: rng.choice(10, m, p=FLOWER_P))
for c in (lib, flib):
    c.hide_render = True        # the library objects themselves are not rendered at the origin

# ---------------------------------------------------------------- compositor: a soft bloom in linear light; data passes for the loop
BLOOM = arg('bloom', 0.22)
sc.use_nodes = True
ct = sc.node_tree; ct.nodes.clear()
rl = ct.nodes.new('CompositorNodeRLayers')
comp = ct.nodes.new('CompositorNodeComposite')
gl = ct.nodes.new('CompositorNodeGlare'); gl.glare_type = 'BLOOM'; gl.quality = 'HIGH'
gl.inputs['Threshold'].default_value = 0.9; gl.inputs['Smoothness'].default_value = 0.6
gl.inputs['Strength'].default_value = BLOOM; gl.inputs['Size'].default_value = 0.85
gl.inputs['Tint'].default_value = (1.0, 0.86, 0.7, 1)
src_img = rl.outputs['Image']
if NIGHT:
    fz = ct.nodes.new('CompositorNodeMapRange'); fz.use_clamp = True
    fz.inputs['From Min'].default_value = 4; fz.inputs['From Max'].default_value = 300
    fz.inputs['To Min'].default_value = 0; fz.inputs['To Max'].default_value = arg('fog', 0.74)
    ct.links.new(rl.outputs['Depth'], fz.inputs['Value'])
    fm = ct.nodes.new('CompositorNodeMixRGB'); fm.blend_type = 'MIX'
    fm.inputs[2].default_value = (0.010, 0.020, 0.042, 1)
    ct.links.new(fz.outputs['Value'], fm.inputs[0]); ct.links.new(rl.outputs['Image'], fm.inputs[1])
    src_img = fm.outputs['Image']
    gl.inputs['Threshold'].default_value = 0.25; gl.inputs['Strength'].default_value = arg('bloom', 0.6)
    gl.inputs['Size'].default_value = 0.9; gl.inputs['Tint'].default_value = (0.8, 0.92, 1.0, 1)
ct.links.new(src_img, gl.inputs['Image']); ct.links.new(gl.outputs['Image'], comp.inputs['Image'])
if PASSES:
    # one 16-bit PNG of data, stored with the Standard view so it inverts exactly:
    # R depth / 80 m, G blade height fraction / 1.2, B 1.0 crystal, 0.75 stone, 0.5 grass and flowers, 0 sky
    fo = ct.nodes.new('CompositorNodeOutputFile')
    fo.base_path = os.path.dirname(PASSES); fo.format.file_format = 'PNG'
    fo.format.color_depth = '16'; fo.format.color_mode = 'RGB'
    fo.format.color_management = 'OVERRIDE'; fo.format.view_settings.view_transform = 'Standard'
    fo.format.view_settings.look = 'None'; fo.format.view_settings.exposure = 0; fo.format.view_settings.gamma = 1
    fo.file_slots.clear(); fo.file_slots.new('data')
    cc = ct.nodes.new('CompositorNodeCombineColor'); cc.mode = 'RGB'
    def cl(sock):
        n_ = ct.nodes.new('CompositorNodeMath'); n_.operation = 'MINIMUM'; n_.inputs[1].default_value = 1.0
        ct.links.new(sock, n_.inputs[0]); return n_.outputs[0]
    def mr(sock, hi):
        n_ = ct.nodes.new('CompositorNodeMapRange'); n_.use_clamp = True
        n_.inputs['From Min'].default_value = 0; n_.inputs['From Max'].default_value = hi
        n_.inputs['To Min'].default_value = 0; n_.inputs['To Max'].default_value = 1
        ct.links.new(sock, n_.inputs['Value']); return n_.outputs['Value']
    # depth, log encoded (R = ln(1 + d) / ln(4001)) so the grade can reach the distant hills
    a1 = ct.nodes.new('CompositorNodeMath'); a1.operation = 'ADD'; a1.inputs[1].default_value = 1.0
    ct.links.new(rl.outputs['Depth'], a1.inputs[0])
    lg = ct.nodes.new('CompositorNodeMath'); lg.operation = 'LOGARITHM'; lg.inputs[1].default_value = 4001.0
    ct.links.new(a1.outputs[0], lg.inputs[0])
    ct.links.new(mr(lg.outputs[0], 1.0), cc.inputs['Red'])
    ct.links.new(mr(rl.outputs['hf'], 1.2), cc.inputs['Green'])
    half_ = ct.nodes.new('CompositorNodeMath'); half_.operation = 'MULTIPLY'; half_.inputs[1].default_value = 0.5
    ct.links.new(cl(rl.outputs['gm']), half_.inputs[0])
    q3 = ct.nodes.new('CompositorNodeMath'); q3.operation = 'MULTIPLY'; q3.inputs[1].default_value = 0.75
    ct.links.new(cl(rl.outputs['st']), q3.inputs[0])
    mxm = ct.nodes.new('CompositorNodeMath'); mxm.operation = 'MAXIMUM'
    ct.links.new(half_.outputs[0], mxm.inputs[0]); ct.links.new(q3.outputs[0], mxm.inputs[1])
    mx2 = ct.nodes.new('CompositorNodeMath'); mx2.operation = 'MAXIMUM'
    ct.links.new(mxm.outputs[0], mx2.inputs[0]); ct.links.new(cl(rl.outputs['cr']), mx2.inputs[1])
    q4 = ct.nodes.new('CompositorNodeMath'); q4.operation = 'MULTIPLY'; q4.inputs[1].default_value = 0.25
    ct.links.new(cl(rl.outputs['ld']), q4.inputs[0])
    mx3 = ct.nodes.new('CompositorNodeMath'); mx3.operation = 'MAXIMUM'
    ct.links.new(mx2.outputs[0], mx3.inputs[0]); ct.links.new(q4.outputs[0], mx3.inputs[1])
    ct.links.new(mx3.outputs[0], cc.inputs['Blue'])
    ct.links.new(cc.outputs['Image'], fo.inputs[0])
    sc.frame_current = 1

BORDER = arg('border', '')
if BORDER:
    x0, y0, x1, y1 = (float(v) for v in BORDER.split(','))
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_min_y, sc.render.border_max_x, sc.render.border_max_y = x0, y0, x1, y1
if paper_ob is not None:
    # where the paper lands in the frame, for the page's hotspot
    from bpy_extras.object_utils import world_to_camera_view
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); pe_ = paper_ob.evaluated_get(dg)
    pts = [world_to_camera_view(sc, cam, pe_.matrix_world @ v.co) for v in pe_.data.vertices]
    xs = [p_.x * W for p_ in pts]; ys = [(1 - p_.y) * H for p_ in pts]
    json.dump({'w': W, 'h': H, 'x0': min(xs), 'y0': min(ys), 'x1': max(xs), 'y1': max(ys)}, open(OUT + '.paper.json', 'w'))
    print('PAPER', min(xs), min(ys), max(xs), max(ys))
import time
if '--dry' in argv and '--probe' in argv:
    from bpy_extras.object_utils import world_to_camera_view
    dg_ = bpy.context.evaluated_depsgraph_get(); fr_ = cam.data.view_frame(scene=sc)
    for (u_, v_) in ((0.05, 0.5), (0.6, 0.5), (0.6, 0.8), (0.9, 0.3), (0.3, 0.3)):
        pt = fr_[2] + (fr_[1] - fr_[2]) * u_ + (fr_[3] - fr_[2]) * v_   # frame corners: 0 tr, 1 br, 2 bl, 3 tl
        d_ = (cam.matrix_world.to_3x3() @ pt).normalized()
        hit = sc.ray_cast(dg_, cam.matrix_world.translation, d_)
        print('PROBE', u_, v_, hit[0], tuple(round(c, 1) for c in hit[1]) if hit[0] else '', hit[4].name if hit[0] else '')
if '--dry' in argv:
    for o_ in sc.objects:
        if o_.name.startswith('i_lib_coastal') or o_.name.startswith('coastal') or o_.name in ('cloud_gobo', 'farland'): print('DRYOBJ', o_.name, tuple(round(v) for v in o_.location), tuple(round(v, 1) for v in o_.scale), o_.users_collection[0].name)
    print('DRY_OK'); sys.exit(0)
t0 = time.time()
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('RENDER_SECONDS', round(time.time() - t0, 1))
if PASSES:
    # the file output node names the file <base>/<frame>.exr; move it to the requested name
    cand = os.path.join(os.path.dirname(PASSES), 'data0001.png')
    if os.path.exists(cand): os.replace(cand, PASSES)
