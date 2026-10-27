# ---------------------------------------------------------------- shared kit (Antimony first-frame drafts, worlds 7 to 10)
# Blender 4.5 LTS, Cycles CPU. Scanned CC0 materials from ambientCG and Poly Haven, read from the shared asset cache.
# The Break is built from the exact geometry in break-geometry.json: the rounded tile (rx 22 on 100), the seam at 16
# degrees cut right through, the cavity, and the sky crystal (#94E6FF) set into it.
import bpy, bmesh, math, json, os, re, sys, random
import numpy as np
from mathutils import Vector, Matrix, Euler

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    k = '--' + name
    return type(default)(argv[argv.index(k) + 1]) if k in argv else default

SCR = '/tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad'
ACG = os.path.join(SCR, 'assets', 'ambientcg')
PH = os.path.join(SCR, 'assets', 'polyhaven')
GEO = json.load(open(arg('geometry', os.path.join(SCR, 'break-geometry.json'))))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = arg('out', os.path.join(HERE, 'render.png'))
RES = arg('res', '1600x900')
SAMPLES = arg('samples', 160)
TLIM = arg('time', 330.0)
rng = random.Random(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def setup(expo=0.0, look='AgX - Base Contrast', bounces=(6, 3, 3), clamp=8.0):
    W, H = (int(v) for v in RES.split('x'))
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    cy.device = 'CPU'; cy.samples = SAMPLES; cy.time_limit = TLIM
    cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.025
    cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'; cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces = bounces
    cy.transmission_bounces = 6; cy.transparent_max_bounces = 16; cy.volume_bounces = 0
    cy.caustics_reflective = False; cy.caustics_refractive = False
    cy.sample_clamp_indirect = clamp; cy.use_light_tree = True
    cy.volume_step_rate = 4.0; cy.volume_max_steps = 256
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = look
    sc.view_settings.exposure = expo
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '16'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.filepath = OUT

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
def hexlin(h): return tuple(srgb2lin(int(h[i:i + 2], 16) / 255) for i in (1, 3, 5))
def link_ob(ob, coll=None): (coll or sc.collection).objects.link(ob); return ob
def out(nt, sh, loc=(600, 0), vol=None):
    o = node(nt, 'ShaderNodeOutputMaterial', loc)
    if sh is not None: link(nt, sh, o.inputs['Surface'])
    if vol is not None: link(nt, vol, o.inputs['Volume'])
    return o

def emit_mat(name, col, strength):
    m, nt = mat(name)
    e = node(nt, 'ShaderNodeEmission', Color=(*col, 1), Strength=strength)
    out(nt, e.outputs['Emission']); return m

# ---------------------------------------------------------------- world
def world_hdri(path, strength=1.0, rot_z=0.0, tint=None):
    w = bpy.data.worlds.new('sky'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    tc = node(nt, 'ShaderNodeTexCoord', (-900, 0)); mp = node(nt, 'ShaderNodeMapping', (-700, 0))
    mp.inputs['Rotation'].default_value = (0, 0, rot_z)
    env = node(nt, 'ShaderNodeTexEnvironment', (-500, 0)); env.image = img(path)
    link(nt, tc.outputs['Generated'], mp.inputs['Vector']); link(nt, mp.outputs['Vector'], env.inputs['Vector'])
    c = env.outputs['Color']
    if tint is not None:
        mx = node(nt, 'ShaderNodeMix', (-300, 0)); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
        mx.inputs['Factor'].default_value = 1.0; mx.inputs['B'].default_value = (*tint, 1)
        link(nt, c, mx.inputs['A']); c = mx.outputs['Result']
    bg = node(nt, 'ShaderNodeBackground', (-100, 0)); bg.inputs['Strength'].default_value = strength
    link(nt, c, bg.inputs['Color'])
    o = node(nt, 'ShaderNodeOutputWorld', (150, 0)); link(nt, bg.outputs['Background'], o.inputs['Surface'])
    w.cycles.sampling_method = 'MANUAL'; w.cycles.sample_map_resolution = 1024
    return w

def world_color(col, strength=1.0):
    w = bpy.data.worlds.new('sky'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    bg = node(nt, 'ShaderNodeBackground', Color=(*col, 1), Strength=strength)
    o = node(nt, 'ShaderNodeOutputWorld', (200, 0)); link(nt, bg.outputs['Background'], o.inputs['Surface'])
    return w

def sun(direction_to_sun, energy, col, angle=1.0):
    d = bpy.data.lights.new('sun', 'SUN'); d.energy = energy; d.color = col; d.angle = math.radians(angle)
    o = link_ob(bpy.data.objects.new('sun', d))
    o.rotation_euler = (-Vector(direction_to_sun).normalized()).to_track_quat('-Z', 'Y').to_euler()
    return o

def point(loc, energy, col, radius=0.05, name='pt'):
    d = bpy.data.lights.new(name, 'POINT'); d.energy = energy; d.color = col; d.shadow_soft_size = radius
    o = link_ob(bpy.data.objects.new(name, d)); o.location = loc; return o

def area(loc, rot, energy, col, size=1.0, name='area', shape='SQUARE', size_y=None):
    d = bpy.data.lights.new(name, 'AREA'); d.energy = energy; d.color = col; d.size = size; d.shape = shape
    if size_y is not None: d.size_y = size_y
    o = link_ob(bpy.data.objects.new(name, d)); o.location = loc; o.rotation_euler = rot; return o

def camera(loc, look_at, lens=35, fstop=None, focus=None, shift=(0, 0)):
    cd = bpy.data.cameras.new('cam'); cd.lens = lens; cd.sensor_width = 36
    cd.shift_x, cd.shift_y = shift; cd.clip_end = 20000
    c = link_ob(bpy.data.objects.new('cam', cd)); c.location = loc
    c.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if fstop:
        cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
        cd.dof.focus_distance = focus if focus else (Vector(look_at) - Vector(loc)).length
    sc.camera = c; return c

# ---------------------------------------------------------------- volumes
def volume_box(name, c, s, dens, col=(1, 1, 1), aniso=0.6, emis=None, shadow=True, noise=None):
    bm = bmesh.new(); r = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ Matrix.Diagonal((*s, 1)), verts=r['verts'])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    m, nt = mat(name)
    pv = node(nt, 'ShaderNodeVolumePrincipled', (0, 0))
    pv.inputs['Density'].default_value = dens; pv.inputs['Color'].default_value = (*col, 1)
    pv.inputs['Anisotropy'].default_value = aniso
    if noise:   # height falloff (and optional soft breakup) so mist hugs the water or the ground
        z0, z1 = noise
        tc = node(nt, 'ShaderNodeTexCoord', (-900, 0)); sp = node(nt, 'ShaderNodeSeparateXYZ', (-700, 0))
        link(nt, tc.outputs['Object'], sp.inputs['Vector'])
        mr = node(nt, 'ShaderNodeMapRange', (-500, 0)); mr.inputs['From Min'].default_value = z0
        mr.inputs['From Max'].default_value = z1; mr.inputs['To Min'].default_value = 1.0
        mr.inputs['To Max'].default_value = 0.0; mr.interpolation_type = 'SMOOTHSTEP'
        link(nt, sp.outputs['Z'], mr.inputs['Value'])
        ml = node(nt, 'ShaderNodeMath', (-300, 0), operation='MULTIPLY'); ml.inputs[1].default_value = dens
        link(nt, mr.outputs['Result'], ml.inputs[0]); link(nt, ml.outputs['Value'], pv.inputs['Density'])
    if emis:
        pv.inputs['Emission Color'].default_value = (*emis[0], 1); pv.inputs['Emission Strength'].default_value = emis[1]
    out(nt, None, vol=pv.outputs['Volume'])
    ob = link_ob(bpy.data.objects.new(name, me)); me.materials.append(m)
    ob.visible_shadow = shadow
    return ob

# ---------------------------------------------------------------- scanned PBR (ambientCG)
def acg(name, aid, scale=1.0, val=1.0, sat=1.0, hue=0.5, rough=(0.0, 1.0), nstr=1.0, wet=0.0, wet_scale=0.25,
        puddles=0.0, tint=None, proj='BOX', stain=0.0, coord='Object'):
    """A scanned material, box projected in metres. wet darkens and lowers roughness; puddles add mirror patches."""
    base = os.path.join(ACG, aid, f'{aid}_2K-JPG_')
    m, nt = mat(name)
    tco = node(nt, 'ShaderNodeTexCoord', (-1600, 0))
    mpp = node(nt, 'ShaderNodeMapping', (-1400, 0)); mpp.inputs['Scale'].default_value = (scale,) * 3
    link(nt, tco.outputs[coord], mpp.inputs['Vector'])
    def bt(sfx, nc, loc):
        t = node(nt, 'ShaderNodeTexImage', loc); t.image = img(base + sfx + '.jpg', nc)
        if proj == 'BOX': t.projection = 'BOX'; t.projection_blend = 0.3
        link(nt, mpp.outputs['Vector'], t.inputs['Vector']); return t
    td, tr, tn = bt('Color', False, (-1100, 300)), bt('Roughness', True, (-1100, 0)), bt('NormalGL', True, (-1100, -300))
    hs = node(nt, 'ShaderNodeHueSaturation', (-800, 300)); hs.inputs['Saturation'].default_value = sat
    hs.inputs['Value'].default_value = val; hs.inputs['Hue'].default_value = hue
    link(nt, td.outputs['Color'], hs.inputs['Color']); col = hs.outputs['Color']
    if tint is not None:
        mm = node(nt, 'ShaderNodeMix', (-650, 300)); mm.data_type = 'RGBA'; mm.blend_type = 'MULTIPLY'
        mm.inputs['Factor'].default_value = 1; mm.inputs['B'].default_value = (*tint, 1)
        link(nt, col, mm.inputs['A']); col = mm.outputs['Result']
    if stain > 0:
        nz = node(nt, 'ShaderNodeTexNoise', (-1100, 650)); nz.inputs['Scale'].default_value = 0.08; nz.inputs['Detail'].default_value = 6
        link(nt, tco.outputs['Object'], nz.inputs['Vector'])
        mr = node(nt, 'ShaderNodeMapRange', (-800, 650)); mr.inputs['To Min'].default_value = 1 - stain; mr.inputs['To Max'].default_value = 1 + stain * 0.3
        link(nt, nz.outputs['Fac'], mr.inputs['Value'])
        mm = node(nt, 'ShaderNodeMix', (-500, 400)); mm.data_type = 'RGBA'; mm.blend_type = 'MULTIPLY'; mm.inputs['Factor'].default_value = 1
        link(nt, col, mm.inputs['A']); link(nt, mr.outputs['Result'], mm.inputs['B']); col = mm.outputs['Result']
    rr = node(nt, 'ShaderNodeMapRange', (-800, 0)); rr.inputs['To Min'].default_value = rough[0]; rr.inputs['To Max'].default_value = rough[1]
    link(nt, tr.outputs['Color'], rr.inputs['Value']); rgh = rr.outputs['Result']
    nm = node(nt, 'ShaderNodeNormalMap', (-800, -300)); nm.inputs['Strength'].default_value = nstr
    link(nt, tn.outputs['Color'], nm.inputs['Color']); nrm = nm.outputs['Normal']
    if wet > 0 or puddles > 0:
        # wetness mask: broad noise; puddles: its low points become standing water (dark, mirror smooth, flat normal)
        wn = node(nt, 'ShaderNodeTexNoise', (-1100, -650)); wn.inputs['Scale'].default_value = wet_scale; wn.inputs['Detail'].default_value = 4
        wn.inputs['Roughness'].default_value = 0.6
        link(nt, tco.outputs['Object'], wn.inputs['Vector'])
        pm = node(nt, 'ShaderNodeMapRange', (-800, -650)); pm.inputs['From Min'].default_value = 0.6 - puddles * 0.16
        pm.inputs['From Max'].default_value = 0.63 - puddles * 0.16; pm.inputs['To Min'].default_value = 0.0; pm.inputs['To Max'].default_value = 1.0
        link(nt, wn.outputs['Fac'], pm.inputs['Value'])
        pdl = pm.outputs['Result'] if puddles > 0 else None
        # wet everywhere: darker colour, lower roughness
        dk = node(nt, 'ShaderNodeMix', (-400, 300)); dk.data_type = 'RGBA'; dk.blend_type = 'MULTIPLY'
        dk.inputs['Factor'].default_value = wet; dk.inputs['B'].default_value = (0.45, 0.45, 0.47, 1)
        link(nt, col, dk.inputs['A']); col = dk.outputs['Result']
        wr = node(nt, 'ShaderNodeMath', (-400, 0), operation='MULTIPLY'); wr.inputs[1].default_value = 1 - 0.75 * wet
        link(nt, rgh, wr.inputs[0]); rgh = wr.outputs['Value']
        if pdl is not None:
            pc = node(nt, 'ShaderNodeMix', (-250, 300)); pc.data_type = 'RGBA'
            link(nt, pdl, pc.inputs['Factor']); link(nt, col, pc.inputs['A']); pc.inputs['B'].default_value = (0.012, 0.013, 0.015, 1)
            col = pc.outputs['Result']
            pr = node(nt, 'ShaderNodeMix', (-250, 0)); pr.data_type = 'FLOAT'
            link(nt, pdl, pr.inputs['Factor']); link(nt, rgh, pr.inputs['A']); pr.inputs['B'].default_value = 0.04
            rgh = pr.outputs['Result']
            gn = node(nt, 'ShaderNodeNewGeometry', (-450, -500))
            pn = node(nt, 'ShaderNodeMix', (-250, -300)); pn.data_type = 'VECTOR'
            link(nt, pdl, pn.inputs['Factor']); link(nt, nrm, pn.inputs[4]); link(nt, gn.outputs['Normal'], pn.inputs[5])
            nrm = pn.outputs[1]
    b = node(nt, 'ShaderNodeBsdfPrincipled', (0, 0))
    link(nt, col, b.inputs['Base Color']); link(nt, rgh, b.inputs['Roughness']); link(nt, nrm, b.inputs['Normal'])
    out(nt, b.outputs['BSDF'])
    return m

# ---------------------------------------------------------------- mesh helpers
def add_mesh(name, bm, m=None, smooth=False):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if m: me.materials.append(m)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return link_ob(bpy.data.objects.new(name, me))
def box(bm, c, s, rot=None):
    r = bmesh.ops.create_cube(bm, size=1.0)
    M = Matrix.Translation(Vector(c)) @ (rot.to_4x4() if rot else Matrix.Identity(4)) @ Matrix.Diagonal((*s, 1))
    bmesh.ops.transform(bm, matrix=M, verts=r['verts']); return r
def bevel(ob, w=0.02, seg=2, ang=40):
    b = ob.modifiers.new('bevel', 'BEVEL'); b.width = w; b.segments = seg; b.limit_method = 'ANGLE'; b.angle_limit = math.radians(ang)
    return b
def plane(name, c, s, m, rot=(0, 0, 0)):
    bm = bmesh.new(); r = bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((s[0], s[1], 1, 1)), verts=r['verts'])
    return add_mesh(name, bm, m)

# ---------------------------------------------------------------- scanned models (Poly Haven)
_libs = {}
def ph(asset, names, res=None):
    """Append objects from a cached Poly Haven blend; returns {name: object}, kept out of the render as sources."""
    f = [x for x in os.listdir(os.path.join(PH, asset)) if x.endswith('.blend')][0]
    path = os.path.join(PH, asset, f)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names]
    srcc = bpy.data.collections.get('sources') or bpy.data.collections.new('sources')
    if 'sources' not in sc.collection.children: sc.collection.children.link(srcc)
    res = {}
    for o in dst.objects:
        if o is None: continue
        srcc.objects.link(o); o.hide_render = True; o.location = (0, 0, 0); res[o.name] = o
    return res

def inst(src, loc, rot_z=0.0, scale=1.0, tilt=(0, 0), coll=None):
    o = bpy.data.objects.new(src.name + '_i', src.data)
    o.location = loc; o.rotation_euler = (tilt[0], tilt[1], rot_z); o.scale = (scale,) * 3
    link_ob(o, coll); return o

def tint_mats(obj, val=1.0, sat=1.0, hue=0.5, tag='t'):
    """Copy an object's materials once and route base colour through a hue and value tweak (colour harmony)."""
    for i, slot in enumerate(obj.material_slots):
        m = slot.material
        if m is None or m.get('tinted'): continue
        nt = m.node_tree
        for b in [n for n in nt.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled']:
            s = b.inputs['Base Color']
            if s.is_linked:
                l = s.links[0]; fr = l.from_socket
                hs = nt.nodes.new('ShaderNodeHueSaturation'); hs.inputs['Value'].default_value = val
                hs.inputs['Saturation'].default_value = sat; hs.inputs['Hue'].default_value = hue
                nt.links.remove(l); nt.links.new(fr, hs.inputs['Color']); nt.links.new(hs.outputs['Color'], s)
        m['tinted'] = True

# ---------------------------------------------------------------- the stone: the Break, exact geometry
def build_stone(loc, yaw=0.0, S=0.017, T=0.42, sink=0.06, wet=0.0, val=0.34, glow=1.2, moss=0.12, tilt=0.0):
    """S: metres per SVG unit (the tile is 100 units). Base sits sink metres into the ground at loc."""
    def svg_poly(d):
        nums = [float(v) for v in re.findall(r'-?\d+\.?\d*', d)]
        return [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
    def to_xz(p): return ((p[0] - 50) * S, (100 - p[1]) * S)
    def rrect(rx=22, n=16):
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
    bv = tile.modifiers.new('arris', 'BEVEL'); bv.width = 0.014 * S / 0.017; bv.segments = 4; bv.limit_method = 'ANGLE'
    bv.angle_limit = math.radians(35)
    tile.modifiers.new('wn', 'WEIGHTED_NORMAL')
    gem = [to_xz(p) for p in svg_poly(GEO['gem'])]; cxz = to_xz((50, 51.5))
    ZE, ZR = T / 2 - 0.09 * T / 0.5, T / 2 - 0.012
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
    mark.location = (loc[0], loc[1], loc[2] - sink); mark.rotation_euler = (tilt, 0, yaw)
    for o_ in (tile, crystal, cut_seam, cut_cav): o_.parent = mark

    # honed scanned stone (ambientCG Rock041), weathered edges by pointiness, rain darkening, faint moss at the foot
    base = os.path.join(ACG, 'Rock041', 'Rock041_2K-JPG_')
    m, nt = mat('stone')
    tco = node(nt, 'ShaderNodeTexCoord', (-1500, 0))
    mpp = node(nt, 'ShaderNodeMapping', (-1300, 0)); mpp.inputs['Scale'].default_value = (0.55,) * 3
    link(nt, tco.outputs['Object'], mpp.inputs['Vector'])
    def st(sfx, nc, loc_):
        t = node(nt, 'ShaderNodeTexImage', loc_); t.image = img(base + sfx + '.jpg', nc); t.projection = 'BOX'; t.projection_blend = 0.25
        link(nt, mpp.outputs['Vector'], t.inputs['Vector']); return t
    td, tr, tn = st('Color', False, (-1000, 300)), st('Roughness', True, (-1000, 0)), st('NormalGL', True, (-1000, -300))
    hs = node(nt, 'ShaderNodeHueSaturation', (-700, 300)); hs.inputs['Saturation'].default_value = 0.12
    hs.inputs['Value'].default_value = val * (1 - 0.4 * wet); link(nt, td.outputs['Color'], hs.inputs['Color'])
    col = hs.outputs['Color']
    # pale worn arrises (convex edges catch light and wear lighter)
    gm = node(nt, 'ShaderNodeNewGeometry', (-1000, 650))
    pe = node(nt, 'ShaderNodeMapRange', (-700, 650)); pe.inputs['From Min'].default_value = 0.52; pe.inputs['From Max'].default_value = 0.62
    pe.inputs['To Max'].default_value = 0.35
    link(nt, gm.outputs['Pointiness'], pe.inputs['Value'])
    lm = node(nt, 'ShaderNodeMix', (-450, 400)); lm.data_type = 'RGBA'; lm.blend_type = 'SCREEN'
    link(nt, pe.outputs['Result'], lm.inputs['Factor']); link(nt, col, lm.inputs['A']); lm.inputs['B'].default_value = (0.32, 0.32, 0.31, 1)
    col = lm.outputs['Result']
    # moss at the foot: object height, broken by noise
    sp = node(nt, 'ShaderNodeSeparateXYZ', (-1300, 900)); link(nt, tco.outputs['Object'], sp.inputs['Vector'])
    nz = node(nt, 'ShaderNodeTexNoise', (-1300, 1150)); nz.inputs['Scale'].default_value = 9; nz.inputs['Detail'].default_value = 8
    link(nt, tco.outputs['Object'], nz.inputs['Vector'])
    hz = node(nt, 'ShaderNodeMath', (-1050, 900), operation='MULTIPLY_ADD')
    link(nt, nz.outputs['Fac'], hz.inputs[0]); hz.inputs[1].default_value = 0.22 * S / 0.017; link(nt, sp.outputs['Z'], hz.inputs[2])
    mh = node(nt, 'ShaderNodeMapRange', (-850, 900)); mh.inputs['From Min'].default_value = moss * S / 0.017 + 0.1 * S / 0.017
    mh.inputs['From Max'].default_value = moss * 0.4 * S / 0.017 + 0.1 * S / 0.017
    link(nt, hz.outputs['Value'], mh.inputs['Value'])
    mt = node(nt, 'ShaderNodeTexImage', (-1000, 1300)); mt.image = img(os.path.join(ACG, 'Moss002', 'Moss002_2K-JPG_Color.jpg'))
    mt.projection = 'BOX'; mt.projection_blend = 0.3; link(nt, mpp.outputs['Vector'], mt.inputs['Vector'])
    mhs = node(nt, 'ShaderNodeHueSaturation', (-750, 1300)); mhs.inputs['Value'].default_value = 0.45; mhs.inputs['Saturation'].default_value = 0.8
    link(nt, mt.outputs['Color'], mhs.inputs['Color'])
    mmx = node(nt, 'ShaderNodeMix', (-300, 500)); mmx.data_type = 'RGBA'
    link(nt, mh.outputs['Result'], mmx.inputs['Factor']); link(nt, col, mmx.inputs['A']); link(nt, mhs.outputs['Color'], mmx.inputs['B'])
    col = mmx.outputs['Result']
    rr = node(nt, 'ShaderNodeMapRange', (-700, 0)); rr.inputs['To Min'].default_value = 0.3 - 0.2 * wet; rr.inputs['To Max'].default_value = 0.55 - 0.3 * wet
    link(nt, tr.outputs['Color'], rr.inputs['Value'])
    nm = node(nt, 'ShaderNodeNormalMap', (-700, -300)); nm.inputs['Strength'].default_value = 0.55
    link(nt, tn.outputs['Color'], nm.inputs['Color'])
    b = node(nt, 'ShaderNodeBsdfPrincipled', (0, 0)); b.inputs['Specular IOR Level'].default_value = 0.55
    link(nt, col, b.inputs['Base Color']); link(nt, rr.outputs['Result'], b.inputs['Roughness']); link(nt, nm.outputs['Normal'], b.inputs['Normal'])
    if wet > 0:
        b.inputs['Coat Weight'].default_value = 0.35 * wet; b.inputs['Coat Roughness'].default_value = 0.08
    out(nt, b.outputs['BSDF'])
    tile.data.materials.append(m)
    m_in = m.copy(); m_in.name = 'stone_cut'
    for n_ in m_in.node_tree.nodes:
        if n_.bl_idname == 'ShaderNodeHueSaturation' and n_.inputs['Saturation'].default_value < 0.5: n_.inputs['Value'].default_value = val * 0.42
    for c in (cut_seam, cut_cav): c.data.materials.append(m_in)

    SKY = hexlin('#94E6FF')
    m_cr, nt = mat('crystal')
    b = node(nt, 'ShaderNodeBsdfPrincipled', (0, 0))
    b.inputs['Base Color'].default_value = (*[v ** 1.5 for v in SKY], 1)
    b.inputs['Subsurface Weight'].default_value = 1.0; b.inputs['Subsurface Radius'].default_value = (0.35, 0.8, 1.0)
    b.inputs['Subsurface Scale'].default_value = 0.1
    b.inputs['Transmission Weight'].default_value = 0.85; b.inputs['Roughness'].default_value = 0.1; b.inputs['IOR'].default_value = 1.52
    b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.02
    # inner light: brighter towards the facet centre, so the glass has depth and a core
    emc = node(nt, 'ShaderNodeEmission', (0, -300)); emc.inputs['Color'].default_value = (*SKY, 1)
    lw = node(nt, 'ShaderNodeLayerWeight', (-400, -400)); lw.inputs['Blend'].default_value = 0.45
    mr = node(nt, 'ShaderNodeMapRange', (-200, -400)); mr.inputs['To Min'].default_value = glow * 1.25; mr.inputs['To Max'].default_value = glow * 0.55
    link(nt, lw.outputs['Facing'], mr.inputs['Value']); link(nt, mr.outputs['Result'], emc.inputs['Strength'])
    ad = node(nt, 'ShaderNodeAddShader', (200, 0)); link(nt, b.outputs['BSDF'], ad.inputs[0]); link(nt, emc.outputs['Emission'], ad.inputs[1])
    out(nt, ad.outputs['Shader'])
    crystal.data.materials.append(m_cr)
    return mark, tile, crystal

def render():
    import time
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print('RENDER_SECONDS', round(time.time() - t, 1), OUT)

# ---------------------------------------------------------------- light grade: bloom, halation, grain, vignette
def _gblur(a, sigma):
    """Gaussian blur of an (h, w) or (h, w, c) array by FFT, padded to avoid wrap-around."""
    h, w = a.shape[:2]; p = int(sigma * 3) + 2
    pad = [(p, p), (p, p)] + ([(0, 0)] if a.ndim == 3 else [])
    b = np.pad(a, pad, mode='edge'); H, W = b.shape[:2]
    fy = np.fft.fftfreq(H)[:, None]; fx = np.fft.rfftfreq(W)[None, :]
    g = np.exp(-2 * (math.pi * sigma) ** 2 * (fx ** 2 + fy ** 2))
    if a.ndim == 3: g = g[..., None]
    r = np.fft.irfft2(np.fft.rfft2(b, axes=(0, 1)) * g, s=(H, W), axes=(0, 1))
    return r[p:p + h, p:p + w].astype(np.float32)

def grade(src, dst, bloom=0.18, halation=0.16, grain=0.035, vignette=0.32, lift=(0.012, 0.013, 0.02), thresh=0.62, seed=3, rain=0, rain_angle=0.08, rain_gain=0.5):
    im = bpy.data.images.load(src); im.colorspace_settings.name = 'Non-Color'; w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3]   # display referred, 0..1
    a = np.clip(a, 0, 1)
    lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    hi = np.clip((lum - thresh) / (1 - thresh), 0, 1)[..., None] * a
    bl = 0.5 * _gblur(hi, w * 0.004) + 0.3 * _gblur(hi, w * 0.015) + 0.2 * _gblur(hi, w * 0.05)
    a = a + bloom * bl * (1 - a) * 2.0
    hal = _gblur(np.clip((lum - 0.7) / 0.3, 0, 1), w * 0.006)[..., None] * np.array([1.0, 0.35, 0.22], np.float32)
    a = a + halation * hal * (1 - a)
    if rain:   # fine rain: thin streaks that only show where there is light behind or around them
        rg = np.random.default_rng(seed + 1); acc = np.zeros((h, w), np.float32)
        for _ in range(rain):
            near = rg.random() ** 2.2
            L = (10 + 55 * near) * w / 1600; x0 = rg.uniform(-0.1 * w, 1.1 * w); y0 = rg.uniform(-L, h)
            n = int(L * 1.5) + 2; t = np.linspace(0, 1, n)
            xs = (x0 + rain_angle * L * t).astype(int); ys = (y0 + L * t).astype(int)
            ok = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
            np.add.at(acc, (ys[ok], xs[ok]), (0.25 + 0.75 * near) * np.sin(np.pi * t[ok]) ** 0.7)
        acc = _gblur(acc, 0.7 * w / 1600)
        glow = _gblur(a, w * 0.02)   # each drop takes the colour of the light around it
        a = a + rain_gain * acc[..., None] * (0.03 + 1.8 * glow ** 1.25)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 * 0.8 + ((yy - h / 2) / (h / 2)) ** 2 * 0.65)
    a = a * (1 - vignette * np.clip(d - 0.3, 0, 1) ** 1.7)[..., None]
    a = np.array(lift, np.float32) + a * (1 - np.array(lift, np.float32))
    g = np.random.default_rng(seed).normal(0, 1, (h, w)).astype(np.float32)
    g = _gblur(g, 0.55) * 1.6
    l2 = np.clip(a @ np.array([0.2126, 0.7152, 0.0722], np.float32), 0, 1)
    a = a + (grain * g * (0.4 + 2.4 * l2 * (1 - l2)))[..., None]
    a = np.clip(a, 0, 1)
    o = bpy.data.images.new('graded', w, h, alpha=False, float_buffer=True); o.colorspace_settings.name = 'Non-Color'
    o.pixels[:] = np.concatenate([a[::-1], np.ones((h, w, 1), np.float32)], -1).ravel()
    o.filepath_raw = dst; o.file_format = 'PNG'; o.save()
    print('GRADED', dst)

# ---------------------------------------------------------------- the lightbox poster (alternate hero): slim dark frame, emissive face, wet glass
POSTER_SRC = '/home/user/antimony-site/directions/grow/shots/rest-desktop.png'
def build_lightbox(center, yaw, w=1.0, h=1.56, strength=3.0, spill=60.0, spill_col=(1.0, 0.86, 0.72), crop_aspect=None):
    """Faces along -Y rotated by yaw (radians, about Z). Returns the four face corners in world space
    (top left, top right, bottom right, bottom left, as seen from the front)."""
    rot = Matrix.Rotation(yaw, 4, 'Z'); C = Vector(center)
    def W_(x, y, z): return C + (rot @ Vector((x, y, z)))
    fd = 0.06   # frame depth
    # frame: four dark bars and a back
    M_FR = acg('lb_frame', 'Concrete031', scale=3, val=0.05, sat=0.0, rough=(0.25, 0.4), wet=0.6, wet_scale=3)
    bm = bmesh.new(); t = 0.035
    for (cx, cz, sx, sz) in ((0, h / 2 + t / 2, w + 2 * t, t), (0, -h / 2 - t / 2, w + 2 * t, t), (-w / 2 - t / 2, 0, t, h), (w / 2 + t / 2, 0, t, h)):
        box(bm, (cx, 0, cz), (sx, fd, sz))
    box(bm, (0, fd / 2 + 0.01, 0), (w + 2 * t, 0.02, h + 2 * t))
    fr = add_mesh('lb_frame', bm, M_FR); bevel(fr, 0.004, 2)
    fr.matrix_world = Matrix.Translation(C) @ rot
    # face: the poster image, cropped to the face's aspect from the centre of the source
    im = img(POSTER_SRC); iw, ih = im.size; asp = w / h
    cw = min(1.0, ih * asp / iw); u0, u1 = 0.5 - cw / 2, 0.5 + cw / 2
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
    vs = [bm.verts.new(p) for p in ((-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2))]
    f = bm.faces.new(vs)
    for lp, uv in zip(f.loops, ((u0, 0), (u1, 0), (u1, 1), (u0, 1))): lp[uvl].uv = uv
    if f.normal.y > 0: f.normal_flip()
    m, nt = mat('lb_face')
    tx = node(nt, 'ShaderNodeTexImage', (-400, 0)); tx.image = im; tx.extension = 'EXTEND'
    e = node(nt, 'ShaderNodeEmission', (0, 0)); e.inputs['Strength'].default_value = strength
    link(nt, tx.outputs['Color'], e.inputs['Color']); out(nt, e.outputs['Emission'])
    face = add_mesh('lb_face', bm, m); face.matrix_world = Matrix.Translation(C) @ rot
    # wet glass a little in front: clear, with rain beads and runs as a bump
    bm = bmesh.new(); box(bm, (0, -0.012, 0), (w + 0.01, 0.004, h + 0.01))
    m, nt = mat('lb_glass')
    tc = node(nt, 'ShaderNodeTexCoord', (-900, 0))
    vo = node(nt, 'ShaderNodeTexVoronoi', (-700, 0)); vo.inputs['Scale'].default_value = 55; vo.feature = 'F1'
    link(nt, tc.outputs['Object'], vo.inputs['Vector'])
    mr = node(nt, 'ShaderNodeMapRange', (-500, 0)); mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 0.22
    mr.inputs['To Min'].default_value = 1.0; mr.inputs['To Max'].default_value = 0.0
    link(nt, vo.outputs['Distance'], mr.inputs['Value'])
    nz = node(nt, 'ShaderNodeTexNoise', (-700, -250)); nz.inputs['Scale'].default_value = 6
    link(nt, tc.outputs['Object'], nz.inputs['Vector'])
    gt = node(nt, 'ShaderNodeMath', (-350, -150), operation='GREATER_THAN'); gt.inputs[1].default_value = 0.55
    link(nt, nz.outputs['Fac'], gt.inputs[0])
    mu = node(nt, 'ShaderNodeMath', (-200, 0), operation='MULTIPLY'); link(nt, mr.outputs['Result'], mu.inputs[0]); link(nt, gt.outputs['Value'], mu.inputs[1])
    bp = node(nt, 'ShaderNodeBump', (0, -200)); bp.inputs['Strength'].default_value = 0.6; bp.inputs['Distance'].default_value = 0.002
    link(nt, mu.outputs['Value'], bp.inputs['Height'])
    b = node(nt, 'ShaderNodeBsdfPrincipled', (200, 0)); b.inputs['Transmission Weight'].default_value = 1.0
    b.inputs['Roughness'].default_value = 0.03; b.inputs['IOR'].default_value = 1.45
    link(nt, bp.outputs['Normal'], b.inputs['Normal']); out(nt, b.outputs['BSDF'], (450, 0))
    gl = add_mesh('lb_glass', bm, m); gl.matrix_world = Matrix.Translation(C) @ rot; gl.visible_shadow = False
    # the light it throws (a dimmer cheat, as in the Platform notes: brighter on the scene than it reads to camera)
    a = area(tuple(W_(0, -0.03, 0)), (rot @ Matrix.Rotation(-math.pi / 2, 4, 'X')).to_euler(), spill, spill_col, size=w, size_y=h, shape='RECTANGLE', name='lb_spill')
    a.visible_camera = False; a.visible_glossy = False
    return [W_(-w / 2, -0.012, h / 2), W_(w / 2, -0.012, h / 2), W_(w / 2, -0.012, -h / 2), W_(-w / 2, -0.012, -h / 2)]

def export_corners(corners, path):
    from bpy_extras.object_utils import world_to_camera_view
    W, H = sc.render.resolution_x, sc.render.resolution_y; pts = []
    for c in corners:
        v = world_to_camera_view(sc, sc.camera, c); pts.append([round(v.x * W, 1), round((1 - v.y) * H, 1)])
    json.dump({'image': os.path.basename(path).replace('-corners.json', '.png'), 'width': W, 'height': H,
               'order': 'top-left, top-right, bottom-right, bottom-left (pixels, origin top left)', 'corners': pts},
              open(path, 'w'), indent=1)
    print('CORNERS', pts)

def hdri_rot_for(path, target_dir, band=(0.47, 0.53)):
    """Mapping rotation that turns the brightest part of the HDRI horizon band (or the sun) towards target_dir."""
    im = img(path); w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[..., :3].sum(-1)
    r0, r1 = int(band[0] * h), int(band[1] * h)
    col = a[r0:r1].mean(0); col = np.convolve(col, np.ones(31) / 31, mode='same')
    u = (np.argmax(col) + 0.5) / w
    phi_h = (0.5 - u) * 2 * math.pi
    phi_t = math.atan2(target_dir[1], target_dir[0])
    return phi_h - phi_t

# ================================================================ World 7: Lantern Canopy
# A narrow undercity lane at night, stone steps rising under a canopy of paper lanterns and fine string lights
# at many depths; soft rain; wet stone and puddles holding every light; plants in pots; haze. The stone at the
# top of the steps. The walls stay simple and dark: the light and the wet carry the frame.
setup(expo=arg('expo', -0.3), look='AgX - Punchy', bounces=(6, 2, 3), clamp=6.0)
world_color((0.002, 0.0045, 0.014), 1.0)
HERO = arg('hero', 'stone')
R = random.Random(17)
WARM = (1.0, 0.34, 0.1); PEACH = (1.0, 0.26, 0.09); ROSE = (1.0, 0.11, 0.06); PALE = (1.0, 0.56, 0.3)

HW = 1.75                               # half width of the lane
RISE, GO, NST, Y0 = 0.16, 0.33, 15, 2.6  # steps
ZTOP = RISE * NST; YTOP = Y0 + GO * NST

# ---- stone: wet paving on the steps and the landing; puddles at the foot and on the landing
M_STEP = acg('steps', 'PavingStones128', scale=0.9, val=0.55, sat=0.6, rough=(0.25, 0.7), nstr=0.9, wet=0.7, wet_scale=0.6, stain=0.35)
M_FLOOR = acg('floor', 'PavingStones128', scale=0.9, val=0.5, sat=0.6, rough=(0.25, 0.7), nstr=0.9, wet=0.85, wet_scale=0.32,
              puddles=0.7, stain=0.35)
M_WALL = acg('wall', 'Concrete044B', scale=0.35, val=0.07, sat=0.15, rough=(0.35, 0.8), nstr=1.0, wet=0.6, wet_scale=0.4, stain=0.5,
             tint=(0.55, 0.68, 1.0))
bm = bmesh.new()
for i in range(NST):
    box(bm, (0, Y0 + GO * i + GO * 4, RISE * (i + 1) / 2 - 0.0), (2 * HW + 0.2, GO * 8 if i == 0 else GO * 8, RISE * (i + 1)))
st = add_mesh('steps', bm, M_STEP); bevel(st, 0.012, 2)
# the foot of the lane and the landing (flat, wet, puddled)
bm = bmesh.new(); box(bm, (0, -2.0, -0.05), (2 * HW + 0.4, 9.2, 0.1)); add_mesh('foot', bm, M_FLOOR)
bm = bmesh.new(); box(bm, (0, YTOP + 20, ZTOP - 0.05), (2 * HW + 0.4, 40, 0.1)); add_mesh('landing', bm, M_FLOOR)

# ---- the walls: tall, simple, in shadow; a few deep bays and two warm doorways
DOORS = ((-1, 4.1, 0.64 + 1.05, 0.9, 2.1), (1, 11.5, ZTOP + 1.1, 1.0, 2.2), (-1, 17.0, ZTOP + 3.9, 0.7, 0.9))
bm = bmesh.new()
for sx in (-1, 1):
    box(bm, (sx * (HW + 0.6), 18, 9), (1.2, 50, 22))
    y = -2.0
    while y < 40:
        d = R.uniform(1.6, 4.5); depth = R.choice((0.0, 0.18, 0.35))
        if any(s_ == sx and y - 0.8 < yd < y + d + 0.8 for s_, yd, *_ in DOORS): depth = 0.0
        if depth: box(bm, (sx * (HW - depth / 2 + 0.0), y + d / 2, 9), (depth, d - 0.25, 22))
        y += d
box(bm, (0, 44, 9), (6, 1, 22))    # the lane turns away beyond the haze
walls = add_mesh('walls', bm, M_WALL)
# warm doorways: recessed, the light spills on the wet steps
M_DOOR = emit_mat('door', (1.0, 0.36, 0.12), 0.35)
for (sx, y, z, w_, h_) in DOORS:
    plane('door', (sx * (HW - 0.005), y, z), (w_, h_), M_DOOR, rot=(math.pi / 2, 0, math.pi / 2))
    area((sx * (HW - 0.15), y, z), (0, sx * math.pi / 2, 0), 25 * w_ * h_, (1.0, 0.5, 0.26), size=w_, size_y=h_, shape='RECTANGLE')

# ---- the canopy: strings of paper lanterns and fine bulbs at many depths
def wire_curve(name, pts, rad, m):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = rad; cu.bevel_resolution = 1
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (*p, 1)
    ob = link_ob(bpy.data.objects.new(name, cu)); cu.materials.append(m); return ob
M_WIRE = acg('wire', 'Concrete031', scale=2, val=0.08, sat=0.0, rough=(0.4, 0.6))

def paper_mat(name, col, strength):
    m, nt = mat(name)
    oi = node(nt, 'ShaderNodeObjectInfo', (-800, 0))
    mr = node(nt, 'ShaderNodeMapRange', (-600, 0)); mr.inputs['To Min'].default_value = strength * 0.55; mr.inputs['To Max'].default_value = strength * 1.25
    link(nt, oi.outputs['Random'], mr.inputs['Value'])
    # brighter through the middle of the paper, darker at the ribs and the caps
    tc = node(nt, 'ShaderNodeTexCoord', (-1000, -300)); sp_ = node(nt, 'ShaderNodeSeparateXYZ', (-800, -300))
    link(nt, tc.outputs['Generated'], sp_.inputs['Vector'])
    rib = node(nt, 'ShaderNodeMath', (-600, -300), operation='SINE'); m1 = node(nt, 'ShaderNodeMath', (-700, -300), operation='MULTIPLY')
    m1.inputs[1].default_value = 60.0; link(nt, sp_.outputs['Z'], m1.inputs[0]); link(nt, m1.outputs['Value'], rib.inputs[0])
    rb = node(nt, 'ShaderNodeMapRange', (-450, -300)); rb.inputs['From Min'].default_value = -1; rb.inputs['To Min'].default_value = 0.7
    link(nt, rib.outputs['Value'], rb.inputs['Value'])
    vz = node(nt, 'ShaderNodeMapRange', (-450, -500)); vz.inputs['From Min'].default_value = 0.0; vz.inputs['From Max'].default_value = 0.5
    vz.inputs['To Min'].default_value = 0.25; link(nt, sp_.outputs['Z'], vz.inputs['Value'])
    vz2 = node(nt, 'ShaderNodeMapRange', (-450, -700)); vz2.inputs['From Min'].default_value = 1.0; vz2.inputs['From Max'].default_value = 0.5
    vz2.inputs['To Min'].default_value = 0.25; link(nt, sp_.outputs['Z'], vz2.inputs['Value'])
    mm = node(nt, 'ShaderNodeMath', (-250, -400), operation='MULTIPLY'); link(nt, rb.outputs['Result'], mm.inputs[0]); link(nt, vz.outputs['Result'], mm.inputs[1])
    mm2 = node(nt, 'ShaderNodeMath', (-150, -400), operation='MULTIPLY'); link(nt, mm.outputs['Value'], mm2.inputs[0]); link(nt, vz2.outputs['Result'], mm2.inputs[1])
    mm3 = node(nt, 'ShaderNodeMath', (-50, -200), operation='MULTIPLY'); link(nt, mm2.outputs['Value'], mm3.inputs[0]); link(nt, mr.outputs['Result'], mm3.inputs[1])
    e = node(nt, 'ShaderNodeEmission', (100, 0)); e.inputs['Color'].default_value = (*col, 1); link(nt, mm3.outputs['Value'], e.inputs['Strength'])
    t = node(nt, 'ShaderNodeBsdfDiffuse', (100, -200)); t.inputs['Color'].default_value = (0.0, 0.0, 0.0, 1)
    ad = node(nt, 'ShaderNodeAddShader', (300, 0)); link(nt, e.outputs['Emission'], ad.inputs[0]); link(nt, t.outputs['BSDF'], ad.inputs[1])
    out(nt, ad.outputs['Shader']); return m
LMATS = [(paper_mat('paper_warm', WARM, 4.5), 0.45), (paper_mat('paper_peach', PEACH, 4.5), 0.25),
         (paper_mat('paper_pale', PALE, 3.6), 0.18), (paper_mat('paper_rose', ROSE, 5.0), 0.12)]
def pick_lm():
    r = R.random()
    for m, p in LMATS:
        if r < p: return m
        r -= p
    return LMATS[0][0]
M_BULB = emit_mat('bulb', (1.0, 0.76, 0.55), 18.0)
M_CAP = acg('cap', 'Concrete031', scale=4, val=0.06, sat=0.0, rough=(0.3, 0.5))

# lantern meshes (shared data: an ellipsoid paper body, a dark cap and foot)
def lantern_mesh(name, r, hz):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=r)
    bmesh.ops.scale(bm, vec=(1, 1, hz), verts=bm.verts)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    return me
L_SHAPES = [lantern_mesh('lan_a', 1.0, 1.25), lantern_mesh('lan_b', 1.0, 0.85), lantern_mesh('lan_c', 1.0, 1.6)]
canopy = bpy.data.collections.new('canopy'); sc.collection.children.link(canopy)
lights_at = []
nl = 0
for k in range(int(arg('strings', 70))):
    yA = R.uniform(1.5, 30.0) if R.random() < 0.65 else R.uniform(1.5, 10.0); yB = yA + R.uniform(-4.0, 4.0)
    zA = ZTOP * min(1, max(0, (yA - Y0) / (YTOP - Y0))) + R.uniform(3.2, 7.0)
    zB = ZTOP * min(1, max(0, (yB - Y0) / (YTOP - Y0))) + R.uniform(3.2, 7.0)
    A_ = Vector((-HW, yA, zA)); B_ = Vector((HW, yB, zB))
    if R.random() < 0.3:
        sx_ = R.choice((-1, 1)); A_, B_ = Vector((sx_ * HW, yA, zA)), Vector((-sx_ * HW, yA + R.uniform(5, 12), zA + R.uniform(-0.5, 1.5)))
    sag = R.uniform(0.3, 1.1)
    pts = []
    for i in range(25):
        t = i / 24; p = A_.lerp(B_, t); p.z -= sag * 4 * t * (1 - t); pts.append(tuple(p))
    wire_curve('wire', pts, 0.006, M_WIRE)
    L = (B_ - A_).length; n = max(3, int(L / R.uniform(0.45, 0.85)))
    fine = R.random() < 0.4
    for i in range(1, n):
        t = i / n; p = A_.lerp(B_, t); p.z -= sag * 4 * t * (1 - t)
        if fine:
            bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=0.018)
            bmesh.ops.translate(bm, vec=p + Vector((0, 0, -0.03)), verts=bm.verts)
            o = add_mesh('bulb', bm, M_BULB); o.visible_shadow = False; canopy.objects.link(o); sc.collection.objects.unlink(o)
            continue
        r = R.uniform(0.075, 0.13) * (1.4 if R.random() < 0.08 else 1.0); drop = R.uniform(0.08, 0.35)
        c = p + Vector((0, 0, -drop - r))
        o = bpy.data.objects.new('lantern', R.choice(L_SHAPES))
        o.location = c; o.scale = (r, r, r); o.rotation_euler = (R.uniform(-0.06, 0.06), R.uniform(-0.06, 0.06), R.uniform(0, 6.28))
        canopy.objects.link(o); o.visible_shadow = False
        if not o.data.materials: o.data.materials.append(LMATS[0][0])
        o.material_slots[0].link = 'OBJECT'; o.material_slots[0].material = pick_lm()
        nl += 1
        if nl % 9 == 0: lights_at.append(c.copy())
        # cord to the wire
        wire_curve('cord', [tuple(p), tuple(c + Vector((0, 0, r * 1.1)))], 0.003, M_WIRE)
# low eaves: a string along each wall at head height, lanterns close over the steps, the doorways and the pots
for sx in (-1, 1):
    y = R.uniform(-0.5, 0.5)
    pts = []
    while y < YTOP + 14:
        zf = 0.0 if y < Y0 else (ZTOP if y > YTOP else RISE * math.ceil((y - Y0) / GO))
        pts.append((sx * (HW - 0.32), y, zf + 2.45 + 0.12 * math.sin(y * 1.7)))
        if R.random() < 0.8:
            r = R.uniform(0.08, 0.12); c = Vector(pts[-1]) + Vector((0, 0, -0.18 - r))
            o = bpy.data.objects.new('lantern', R.choice(L_SHAPES)); o.location = c; o.scale = (r, r, r)
            canopy.objects.link(o); o.visible_shadow = False
            if not o.data.materials: o.data.materials.append(LMATS[0][0])
            o.material_slots[0].link = 'OBJECT'; o.material_slots[0].material = pick_lm(); nl += 1
            wire_curve('cord', [pts[-1], tuple(c + Vector((0, 0, r * 1.1)))], 0.003, M_WIRE)
            if nl % 3 == 0: point(tuple(c), 2.5, (1.0, 0.45, 0.2), radius=0.1)
        y += R.uniform(0.7, 1.1)
    wire_curve('eave', pts, 0.006, M_WIRE)
print('lanterns', nl, 'lights', len(lights_at))
for c in lights_at:
    point(tuple(c), R.uniform(3, 5), (1.0, 0.45, 0.2), radius=0.18)

# ---- plants in pots on the step ends and the landing (scanned)
pp = ph('potted_plant_01', ['potted_plant_01_stem', 'potted_plant_01_pot', 'potted_plant_01_pebbles', 'potted_plant_01_leaves'])
pot = ph('planter_pot_clay', ['planter_pot_clay'])['planter_pot_clay']
fern = ph('fern_02', ['fern_02_a', 'fern_02_b', 'fern_02_c'])
shr = ph('shrub_04', ['shrub_04_a_LOD1', 'shrub_04_b_LOD1', 'shrub_04_c_LOD1'])
for o in list(pp.values()) + [pot] + list(fern.values()) + list(shr.values()): tint_mats(o, val=0.75, sat=0.85)
def potted(x, y, z, s=1.0, kind=0):
    rz = R.uniform(0, 6.28)
    if kind == 0:
        for o in pp.values(): inst(o, (x, y, z), rz, s * R.uniform(0.9, 1.15))
    else:
        inst(pot, (x, y, z), rz, s * R.uniform(0.8, 1.1))
        plant = R.choice(list(fern.values()) if kind == 1 else list(shr.values()))
        inst(plant, (x, y, z + 0.32 * s), rz, s * (0.55 if kind == 1 else 0.35) * R.uniform(0.85, 1.2))
for i in range(0, NST, 2):
    for sx in (-1, 1):
        if R.random() < 0.55:
            potted(sx * (HW - R.uniform(0.25, 0.4)), Y0 + GO * i + GO * 0.5, RISE * (i + 1), R.uniform(0.7, 1.0), R.choice((0, 1, 2)))
for (x, y) in ((-1.3, -0.3), (-1.4, 0.6), (1.35, 0.1), (1.25, 1.4), (-1.3, YTOP + 1.0), (1.3, YTOP + 0.8), (-1.35, YTOP + 3.2),
               (1.4, YTOP + 4.5), (-1.3, YTOP + 6.0)):
    z = 0.0 if y < Y0 else ZTOP
    potted(x, y, z, R.uniform(0.85, 1.25), R.choice((0, 1, 1, 2)))

# ---- the stone at the top of the steps, a little in from the edge, warm light behind it
if HERO == 'stone':
    mark, tile, crystal = build_stone((0.05, YTOP + 1.6, ZTOP), yaw=math.radians(-4), S=0.02, T=0.48, sink=0.05, wet=0.7, val=0.46, glow=1.1, moss=0.1)
    point((0.6, YTOP - 0.6, ZTOP + 1.8), 22, (0.7, 0.85, 1.0), radius=0.6)    # cool key on its face
    point((0.0, YTOP + 3.2, ZTOP + 1.2), 40, (1.0, 0.5, 0.24), radius=0.8)    # warm glow behind: a rim    # soft cool fill so its front reads
else:
    # the lightbox set into a wall across the top of the steps; the lane turns away to the right beyond it
    bm = bmesh.new(); box(bm, (-0.45, YTOP + 3.0, 9), (2 * HW + 0.4 - 0.9, 0.8, 22)); box(bm, (1.2, YTOP + 8.0, 9), (2.0, 0.8, 22))
    add_mesh('endwall', bm, M_WALL)
    CORNERS = build_lightbox((-0.3, YTOP + 2.58, ZTOP + 1.45), 0.0, w=1.15, h=1.8, strength=arg('lb', 3.5), spill=90.0, spill_col=(1.0, 0.88, 0.74))

# ---- cool night sky light from far above the lane: warm against cool on the wet walls and steps
area((0, 14, 26), (0, 0, 0), arg('skyfill', 7000.0), (0.32, 0.5, 1.0), size=3.4, size_y=40, shape='RECTANGLE', name='skyfill')
# ---- haze: lit by the lanterns; thicker in the distance
volume_box('haze', (0, 18, 8), (2 * HW + 1, 50, 18), arg('haze', 0.007), (0.9, 0.92, 1.0), 0.5)

cam = camera((0.3, -2.4, 0.62), (0.3, 30.0, 0.62 + 30 * 0.035), lens=arg('lens', 28.0), fstop=2.8, focus=(Vector((0.05, YTOP + 1.6, ZTOP + 0.8)) - Vector((0.3, -2.4, 0.62))).length, shift=(-0.01, 0.24))
render()
FINAL = os.path.join(HERE, 'first-frame-draft.png' if HERO == 'stone' else 'first-frame-poster.png')
if HERO != 'stone': export_corners(CORNERS, FINAL.replace('.png', '-corners.json'))
grade(OUT, FINAL, bloom=0.4, halation=0.22, grain=0.03, vignette=0.38,
      lift=(0.01, 0.012, 0.022), thresh=0.45, rain=arg('rain', 2200), rain_angle=0.06, rain_gain=0.5)
