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

# ================================================================ World 8: Rooftop Garden
# A planted rooftop at blue hour in light rain, high above a vast city of towers lost in mist with countless small
# lights and a far elevated line; deep blue sky with a warm band at the horizon. The stone stands in the planting at
# the parapet. The towers are plain masses in haze: the sky, the wet roof and the planting carry the frame.
setup(expo=arg('expo', -0.4), look='AgX - Base Contrast', bounces=(6, 2, 3), clamp=6.0)
HERO = arg('hero', 'stone')
R = random.Random(23)
SKYF = os.path.join(PH, 'qwantani_dusk_2_puresky', 'qwantani_dusk_2_puresky_2k.hdr')
FWD = Vector((-0.25, 1.0, 0.0)).normalized()     # the warm glow sits just left of the view
world_hdri(SKYF, strength=arg('sky', 0.4), tint=(0.5, 0.66, 1.0), rot_z=hdri_rot_for(SKYF, FWD, band=(0.5, 0.56)) + arg('sky-rot', 0.0))
CITY_Z = -300.0

# ---- the roof: wet paving with puddles holding the sky; a raised bed along the parapet
M_ROOF = acg('roof', 'PavingStones128', scale=0.75, val=0.42, sat=0.4, rough=(0.25, 0.7), wet=0.85, wet_scale=0.45, puddles=0.8, stain=0.4,
             tint=(0.85, 0.9, 1.0))
M_PAR = acg('parapet', 'Concrete044B', scale=0.6, val=0.3, sat=0.3, rough=(0.3, 0.8), wet=0.6, wet_scale=0.5, stain=0.5, tint=(0.85, 0.9, 1.0))
M_SOIL = acg('soil', 'Ground037', scale=0.8, val=0.35, sat=0.6, rough=(0.3, 0.8), wet=0.8)
bm = bmesh.new(); box(bm, (0, 2.0, -0.1), (30, 14, 0.2)); add_mesh('roof', bm, M_ROOF)
PY = 5.4                                                 # parapet line
bm = bmesh.new(); box(bm, (0, PY + 0.15, 0.45), (30, 0.3, 0.9)); box(bm, (0, PY + 0.15, 0.92), (30, 0.4, 0.06))
par = add_mesh('parapet', bm, M_PAR); bevel(par, 0.015, 2)
bm = bmesh.new(); box(bm, (0, PY - 0.95, 0.22), (30, 1.9, 0.44)); bed = add_mesh('bed_wall', bm, M_PAR); bevel(bed, 0.012, 2)
bm = bmesh.new(); box(bm, (0, PY - 0.95, 0.42), (29.8, 1.75, 0.06)); add_mesh('soil', bm, M_SOIL)
# the building falls away below the parapet (seen only at the edges)
bm = bmesh.new(); box(bm, (0, PY + 8, CITY_Z / 2), (30, 16, -CITY_Z)); add_mesh('building', bm, M_PAR)

# ---- planting (scanned): grasses, ferns, shrubs, periwinkle and small blue flowers, dense, with variation
grass = ph('grass_medium_01', [f'grass_medium_01_{c}_LOD1' for c in 'abcdef'] + [f'grass_medium_01_tiny_{c}_LOD1' for c in 'abc'])
fern = ph('fern_02', ['fern_02_a', 'fern_02_b', 'fern_02_c', 'fern_02_d'])
shr = ph('shrub_04', ['shrub_04_a_LOD1', 'shrub_04_b_LOD1', 'shrub_04_c_LOD1', 'shrub_04_d_LOD1'])
peri = ph('periwinkle_plant', [f'periwinkle_plant_0{i}_LOD2' for i in range(1, 7)])
heli = ph('flower_heliophila', ['flower_heliophila_small_LOD1', 'flower_heliophila_medium_LOD1', 'flower_heliophila_large_LOD1'])
for d in (grass, fern, shr, peri, heli):
    for o in d.values(): tint_mats(o, val=0.8, sat=0.85)
print('plants', len(grass), len(fern), len(shr), len(peri), len(heli))
SX, SY = arg('sx', 1.35), PY - 0.9                    # the stone's place in the bed
def bed_scatter(srcs, n, smin, smax, xr=(-9, 9), keep=0.5):
    srcs = list(srcs.values())
    if not srcs: return
    for _ in range(n):
        x = R.uniform(*xr); y = R.uniform(PY - 1.8, PY - 0.12)
        if math.hypot((x - SX) * 1.0, (y - SY) * 1.6) < keep: continue
        inst(R.choice(srcs), (x, y, 0.44), R.uniform(0, 6.28), R.uniform(smin, smax))
bed_scatter(grass, 260, 0.6, 1.1, keep=0.62)
bed_scatter(fern, 40, 0.5, 0.85, keep=0.75)
bed_scatter(shr, 22, 0.35, 0.6, xr=(-9, -1.5)); bed_scatter(shr, 10, 0.35, 0.55, xr=(3.0, 9))
bed_scatter(peri, 70, 0.9, 1.4, keep=0.55)
bed_scatter(heli, 120, 0.8, 1.2, keep=0.6)
# a few pots on the roof in the foreground, and moss in the paving joints where the roof stays wet
pot = ph('planter_pot_clay', ['planter_pot_clay'])['planter_pot_clay']; tint_mats(pot, val=0.7, sat=0.7)
for (x, y, s, kind) in ((-2.6, 2.4, 1.2, 'fern'), (-3.3, 3.2, 0.95, 'shr'), (3.4, 2.9, 1.1, 'fern')):
    rz = R.uniform(0, 6.28); inst(pot, (x, y, 0), rz, s)
    src = R.choice(list(fern.values()) if kind == 'fern' else list(shr.values()))
    inst(src, (x, y, 0.36 * s), rz, (0.6 if kind == 'fern' else 0.4) * s)

# ---- a warm practical: one old lamp on the parapet to the left, its light on the wet leaves
lan = ph('Lantern_01', ['Lantern_01', 'Lantern_01_glass'])
for o in lan.values(): inst(o, (-2.3, PY + 0.12, 0.95), 0.4, 1.2)
point((-2.3, PY + 0.12, 0.95 + 0.22), arg('lamp', 22.0), (1.0, 0.56, 0.3), radius=0.05)
M_FLAME = emit_mat('lamp_core', (1.0, 0.55, 0.28), 30.0)
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=0.025)
bmesh.ops.translate(bm, vec=Vector((-2.3, PY + 0.12, 0.95 + 0.2)), verts=bm.verts); add_mesh('lamp_core', bm, M_FLAME).visible_shadow = False

# ---- the city below: plain towers in mist, countless small windows lit
def window_mat(name, warm=True):
    m, nt = mat(name)
    tc = node(nt, 'ShaderNodeTexCoord', (-1400, 0)); sp = node(nt, 'ShaderNodeSeparateXYZ', (-1200, 0))
    link(nt, tc.outputs['Object'], sp.inputs['Vector'])
    hx = node(nt, 'ShaderNodeMath', (-1000, 100), operation='ADD'); link(nt, sp.outputs['X'], hx.inputs[0]); link(nt, sp.outputs['Y'], hx.inputs[1])
    cx = node(nt, 'ShaderNodeMath', (-850, 100), operation='DIVIDE'); cx.inputs[1].default_value = 3.2; link(nt, hx.outputs['Value'], cx.inputs[0])
    cz = node(nt, 'ShaderNodeMath', (-850, -100), operation='DIVIDE'); cz.inputs[1].default_value = 3.6; link(nt, sp.outputs['Z'], cz.inputs[0])
    cc = node(nt, 'ShaderNodeCombineXYZ', (-650, 0)); link(nt, cx.outputs['Value'], cc.inputs['X']); link(nt, cz.outputs['Value'], cc.inputs['Y'])
    oi = node(nt, 'ShaderNodeObjectInfo', (-850, -300)); link(nt, oi.outputs['Random'], cc.inputs['Z'])
    fl = node(nt, 'ShaderNodeVectorMath', (-500, 0), operation='FLOOR'); link(nt, cc.outputs['Vector'], fl.inputs[0])
    wn = node(nt, 'ShaderNodeTexWhiteNoise', (-350, 0)); wn.noise_dimensions = '3D'; link(nt, fl.outputs['Vector'], wn.inputs['Vector'])
    on = node(nt, 'ShaderNodeMath', (-150, 0), operation='GREATER_THAN'); on.inputs[1].default_value = 0.86
    link(nt, wn.outputs['Value'], on.inputs[0])
    fr = node(nt, 'ShaderNodeVectorMath', (-500, -200), operation='FRACTION'); link(nt, cc.outputs['Vector'], fr.inputs[0])
    fs = node(nt, 'ShaderNodeSeparateXYZ', (-350, -200)); link(nt, fr.outputs['Vector'], fs.inputs['Vector'])
    mx = node(nt, 'ShaderNodeMath', (-200, -150), operation='LESS_THAN'); mx.inputs[1].default_value = 0.62; link(nt, fs.outputs['X'], mx.inputs[0])
    mz = node(nt, 'ShaderNodeMath', (-200, -300), operation='LESS_THAN'); mz.inputs[1].default_value = 0.5; link(nt, fs.outputs['Y'], mz.inputs[0])
    m1 = node(nt, 'ShaderNodeMath', (0, -200), operation='MULTIPLY'); link(nt, mx.outputs['Value'], m1.inputs[0]); link(nt, mz.outputs['Value'], m1.inputs[1])
    m2 = node(nt, 'ShaderNodeMath', (150, -100), operation='MULTIPLY'); link(nt, m1.outputs['Value'], m2.inputs[0]); link(nt, on.outputs['Value'], m2.inputs[1])
    cr = node(nt, 'ShaderNodeValToRGB', (150, -400)); link(nt, wn.outputs['Color'], cr.inputs['Fac'])
    cr.color_ramp.elements[0].color = ((1.0, 0.5, 0.24, 1) if warm else (0.5, 0.75, 1.0, 1))
    cr.color_ramp.elements[1].color = ((1.0, 0.72, 0.5, 1) if warm else (0.85, 0.92, 1.0, 1))
    st = node(nt, 'ShaderNodeMath', (300, -100), operation='MULTIPLY'); st.inputs[1].default_value = arg('win', 3.5)
    link(nt, m2.outputs['Value'], st.inputs[0])
    e = node(nt, 'ShaderNodeEmission', (450, -200)); link(nt, cr.outputs['Color'], e.inputs['Color']); link(nt, st.outputs['Value'], e.inputs['Strength'])
    b = node(nt, 'ShaderNodeBsdfPrincipled', (450, 100)); b.inputs['Base Color'].default_value = (0.03, 0.035, 0.045, 1)
    b.inputs['Roughness'].default_value = 0.35
    ad = node(nt, 'ShaderNodeAddShader', (650, 0)); link(nt, b.outputs['BSDF'], ad.inputs[0]); link(nt, e.outputs['Emission'], ad.inputs[1])
    out(nt, ad.outputs['Shader'], (850, 0)); return m
M_TW = window_mat('tower_warm', True); M_TC = window_mat('tower_cool', False)
city = bpy.data.collections.new('city'); sc.collection.children.link(city)
n_t = 0
for i in range(int(arg('towers', 420))):
    d = 380 + 2800 * R.random() ** 1.4
    ang = math.radians(R.uniform(-62, 62)) + math.atan2(FWD.x, FWD.y) * 0.3
    x, y = d * math.sin(ang), d * math.cos(ang) + PY
    hgt = min(420, 40 + R.lognormvariate(4.3, 0.55)) * (1.25 if abs(ang) < 0.3 else 1.0)
    w_, dpt = R.uniform(18, 45), R.uniform(18, 45)
    bm = bmesh.new(); box(bm, (0, 0, hgt / 2), (w_, dpt, hgt))
    if R.random() < 0.45:   # a setback crown
        h2 = hgt * R.uniform(0.12, 0.35); box(bm, (0, 0, hgt + h2 / 2), (w_ * 0.6, dpt * 0.6, h2))
    me = bpy.data.meshes.new('tower'); bm.to_mesh(me); bm.free(); me.materials.append(M_TW if R.random() < 0.8 else M_TC)
    o = bpy.data.objects.new('tower', me); o.location = (x, y, CITY_Z); o.rotation_euler = (0, 0, R.uniform(-0.3, 0.3))
    city.objects.link(o); n_t += 1
# the far elevated line: a long slender deck on piers, a string of small lights along it
M_LINE = acg('line', 'Concrete031', scale=0.05, val=0.2, sat=0.2)
bm = bmesh.new()
for k in range(80):
    t = k / 79; p = Vector((-1800 + 3600 * t, 900 + 260 * math.sin(t * 2.4), CITY_Z + 140))
    q = Vector((-1800 + 3600 * (t + 1 / 79), 900 + 260 * math.sin((t + 1 / 79) * 2.4), CITY_Z + 140))
    c = (p + q) / 2; dv = q - p
    box(bm, tuple(c), (dv.length + 0.5, 7, 3.5), Matrix.Rotation(math.atan2(dv.y, dv.x), 3, 'Z'))
    if k % 2 == 0: box(bm, (p.x, p.y, CITY_Z + 70), (5, 5, 140))
add_mesh('line', bm, M_LINE)
M_LL = emit_mat('line_lights', (1.0, 0.82, 0.62), 30.0)
bm = bmesh.new()
for k in range(240):
    t = k / 239; x = -1800 + 3600 * t; y = 900 + 260 * math.sin(t * 2.4)
    bmesh.ops.translate(bm, vec=Vector((x, y - 4, CITY_Z + 142.6)), verts=bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.1)['verts'])
add_mesh('line_lights', bm, M_LL).visible_shadow = False

# ---- air: deep aerial haze over the city, a low mist among the towers, a light veil over the roof
volume_box('haze', (0, 1900, CITY_Z + 350), (7600, 3800, 800), arg('haze', 0.0014), (0.62, 0.72, 1.0), 0.3, noise=(CITY_Z, CITY_Z + 600))
volume_box('lowmist', (0, 1900, CITY_Z + 60), (7600, 3800, 120), arg('mist', 0.004), (0.85, 0.85, 0.95), 0.3, noise=(CITY_Z, CITY_Z + 120))
volume_box('veil', (0, 3, 2), (30, 12, 6), arg('veil', 0.006), (0.8, 0.85, 1.0), 0.4)

# ---- the hero
if HERO == 'stone':
    build_stone((SX, SY, 0.44), yaw=math.radians(-12), S=0.0135, T=0.36, sink=0.04, wet=0.8, val=0.34, glow=0.6, moss=0.12)
else:
    # a slim lightbox on a short wall of the stair head, at the parapet among the planting, turned towards the view
    bm = bmesh.new(); box(bm, (2.6, PY - 0.5, 1.4), (2.6, 0.5, 2.8)); wl = add_mesh('stairhead', bm, M_PAR); bevel(wl, 0.015, 2)
    CORNERS = build_lightbox((2.3, PY - 0.78, 1.55), math.radians(-14), w=0.95, h=1.48, strength=arg('lb', 3.2), spill=60.0)

cam = camera((-0.35, -2.2, 2.7), (0.3, 60.0, 2.7 - 60 * 0.12), lens=arg('lens', 30.0), fstop=4.0,
             focus=(Vector((SX, SY, 1.0)) - Vector((-0.35, -2.2, 2.7))).length, shift=(0, 0.12))
render()
FINAL = os.path.join(HERE, 'first-frame-draft.png' if HERO == 'stone' else 'first-frame-poster.png')
if HERO != 'stone': export_corners(CORNERS, FINAL.replace('.png', '-corners.json'))
grade(OUT, FINAL, bloom=0.22, halation=0.14, grain=0.03, vignette=0.34, lift=(0.012, 0.014, 0.024), thresh=0.6,
      rain=arg('rain', 1200), rain_angle=0.1, rain_gain=0.18)
