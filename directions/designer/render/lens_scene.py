# Lens: a close-up of the Break, the Antimony mark, cut as a real object. Dark honed stone, the seam
# cut right through it, the sky crystal set in the cavity as true glass. The stone stands on a wet
# parapet in the rain at night; the city is far behind and below, out of focus.
# Through the crystal (and the hairline of the seam) the page shows a sunlit meadow, live in WebGL.
#
# The meadow is not in these renders. Instead the openings are backed by a plane that records,
# per pixel, what reaches it through the glass, so the browser can put the meadow there in place:
#   --pass beauty  the night scene; the openings read black (camera and glass see nothing behind)
#   --pass thru    how much light gets through to the backplane (white backplane, everything else black)
#   --pass uv      where it lands: the direction of the ray leaving the stone, as camera tangents
#   --pass spill   the meadow's daylight let out: light behind the stone and inside the crystal only
# Light adds linearly, so beauty + thru x meadow + k x spill is the frame, at any k.
#
# blender -b -P lens_scene.py -- --frame desktop|phone --pass beauty --out f.exr [--res 33] [--samples 64] [--tl 600]

import bpy, bmesh, math, random, sys, os, time, json
import numpy as np
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from helpers import S, V, G, material, MB

def arg(name, default):
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return a[a.index(name) + 1] if name in a else default

FRAME = arg('--frame', 'desktop')
PASS = arg('--pass', 'beauty')
OUT = arg('--out', os.path.join(HERE, '%s_%s.exr' % (FRAME, PASS)))
RES = int(arg('--res', '100'))
SAMPLES = int(arg('--samples', '256'))
TL = float(arg('--tl', '0'))
HAZE = arg('--haze', '1') == '1'
rng = random.Random(5)

bpy.ops.wm.read_factory_settings(use_empty=True)
SC = bpy.context.scene

# ---------------------------------------------------------------- the mark, in metres
U = 0.002                    # 100 mark units = 20 cm
DEPTH = 0.04                 # stone thickness
YAW = math.radians(-9.0)     # the stone is turned a little, so its right side shows
GEO = json.load(open(os.path.join(HERE, '..', 'assets', 'break-geometry.json')))

def parse(d):
    pts = []
    for seg in d.replace('M', ' ').replace('Z', '').split('L'):
        x, y = seg.split(); pts.append((float(x), float(y)))
    return pts

def mk(p):  # mark units (y down) to local stone XZ
    return ((p[0] - 50.0) * U, (50.0 - p[1]) * U)

def rounded_rect(half, r, n=24):
    pts = []
    for cx, cz, a0 in ((half - r, half - r, 0), (-half + r, half - r, 90), (-half + r, -half + r, 180), (half - r, -half + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90.0 * k / n); pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts

def prism(name, poly, y0, y1):
    """Extrude an XZ polygon from y0 to y1 (Z offset: the stone stands on Z = 0)."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, y0, z + 0.1)) for x, z in poly]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]: v.co.y = y1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); SC.collection.objects.link(ob); return ob

def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev); old = ob.data
    ob.modifiers.clear(); ob.data = me; bpy.data.meshes.remove(old)

# ---------------------------------------------------------------- materials
def light_path(g):
    n = g.new('ShaderNodeLightPath'); return n

def stone_mat(name, wet_bias=0.0, ledge=False):
    m, g = material(name); nt = m.node_tree
    tc = g.new('ShaderNodeTexCoord'); P = V(g, tc.outputs['Object'])
    px, py, pz = g.sep(P)
    # crystalline grain: half millimetre cells, a few light feldspar flecks, faint mottling
    vd, vc = g.voronoi(P, 1900.0)
    cw, _, _ = g.sep(vc)
    fleck = g.sm(0.955, 0.985, cw)
    mot, _ = g.noise(P, 18.0, detail=6.0, rough=0.62)
    mot2, _ = g.noise(P, 140.0, detail=3.0, rough=0.5)
    base = g.mix((0.0105, 0.0112, 0.0128), (0.0215, 0.022, 0.0235), g.sm(0.3, 0.75, mot * 0.75 + mot2 * 0.25))
    alb = g.mix(base, (0.075, 0.078, 0.085), fleck * 0.85)
    # rain: running wet tracks on the face, a fully wet ledge with standing water
    if ledge:
        pud, _ = g.noise(g.scale(P, 1.0), 2.2, detail=4.0, rough=0.55)
        wet = g.sm(0.36, 0.42, pud + wet_bias)
        rough_dry = 0.34
    else:
        # after rain the whole face is wet; a few drier patches show the honed grain
        dn, _ = g.noise(P, 7.0, detail=4.0, rough=0.55)
        st = g.comb(px * 60.0, pz * 4.0, py * 60.0)
        sn, _ = g.noise(st, 1.0, detail=3.0, rough=0.5)
        wet = 1.0 - g.sm(0.56, 0.68, dn + (sn - 0.5) * 0.12 + wet_bias)
        rough_dry = 0.3
    rvar, _ = g.noise(P, 300.0, detail=2.0)
    rough = g.m('ADD', rough_dry, (rvar - 0.5) * 0.08)
    rough = rough * (1.0 - wet) + wet * (0.02 if ledge else 0.075)
    alb = g.mix(alb, g.mix(alb, (0.0, 0.0, 0.0), 0.35), wet)
    # micro relief: honing, fine grit, tiny pits; the water fills it in where it is wet
    gr, _ = g.noise(P, 5200.0, detail=2.0, rough=0.5)
    pit = 1.0 - g.sm(0.0, 0.07, vd)
    pd, _ = g.voronoi(P, 520.0)
    pits = 1.0 - g.sm(0.012, 0.05, pd)
    hw = g.new('ShaderNodeTexWave', wave_type='RINGS', rings_direction='SPHERICAL')
    g.put(hw.inputs['Vector'], P); g.put(hw.inputs['Scale'], 260.0); g.put(hw.inputs['Distortion'], 18.0); g.put(hw.inputs['Detail'], 3.0)
    hon = S(g, hw.outputs['Fac'])
    h = gr * 0.5 + pit * 0.25 - pits * 1.2 + hon * 0.12
    h = h * (1.0 - wet * 0.85)
    nrm = g.bump(h, strength=0.12, dist=0.00025)
    sh = g.principled(Base_Color=alb, Roughness=rough, Normal=nrm, IOR=1.55)
    if PASS in ('thru', 'uv'):
        # black, but still a mirror, so the meadow shows in wet reflections of the openings
        sh = g.principled(Base_Color=(0, 0, 0), Roughness=rough, Normal=nrm, IOR=1.55)
    g.out(sh)
    return m

def glass_mat():
    m, g = material('crystal')
    if PASS == 'uv':
        sh = g.new('ShaderNodeBsdfGlass'); sh.inputs['IOR'].default_value = 1.544; sh.inputs['Roughness'].default_value = 0.0
        sh.inputs['Color'].default_value = (1, 1, 1, 1)
        g.out(sh.outputs[0]); return m
    sh = g.principled(Base_Color=(1.0, 1.0, 1.0), Transmission_Weight=1.0, Roughness=0.0, IOR=1.544)
    va = g.new('ShaderNodeVolumeAbsorption'); va.inputs['Color'].default_value = (0.58, 0.9, 1.0, 1); va.inputs['Density'].default_value = 9.0
    if PASS == 'spill':
        em = g.new('ShaderNodeEmission'); em.inputs['Color'].default_value = DAY + (1,); em.inputs['Strength'].default_value = 34.0
        add = g.new('ShaderNodeAddShader'); g.nt.links.new(sh, add.inputs[0]); g.nt.links.new(em.outputs[0], add.inputs[1]); sh = add.outputs[0]
    g.out(sh, va.outputs[0])
    return m

def water_mat():
    m, g = material('water')
    if PASS in ('thru', 'uv'):
        sh = g.new('ShaderNodeBsdfGlass'); sh.inputs['IOR'].default_value = 1.333; sh.inputs['Roughness'].default_value = 0.0
        g.out(sh.outputs[0]); return m
    g.out(g.principled(Base_Color=(1, 1, 1), Transmission_Weight=1.0, Roughness=0.0, IOR=1.333))
    return m

def black_mat(name):
    m, g = material(name)
    g.out(g.principled(Base_Color=(0, 0, 0), Roughness=1.0, Specular_IOR_Level=0.0))
    return m

def back_mat():
    """The plane behind the openings, seen only through them."""
    m, g = material('backplane')
    em = g.new('ShaderNodeEmission')
    if PASS == 'thru':
        em.inputs['Color'].default_value = (1, 1, 1, 1); em.inputs['Strength'].default_value = 1.0
    elif PASS == 'uv':
        geo = g.new('ShaderNodeNewGeometry')
        vt = g.new('ShaderNodeVectorTransform', vector_type='VECTOR', convert_from='WORLD', convert_to='CAMERA')
        g.put(vt.inputs[0], V(g, geo.outputs['Incoming']))
        ix, iy, iz = g.sep(V(g, vt.outputs[0]))
        # the ray travels along d = -Incoming; the camera looks down -Z, so the tangents are d.x / -d.z = -I.x / I.z
        tx = (ix / iz) * -1.0; ty = (iy / iz) * -1.0
        col = g.comb(0.5 + tx * 1.2, 0.5 + ty * 1.2, 1.0)
        g.put(em.inputs['Color'], col); em.inputs['Strength'].default_value = 1.0
    else:
        em.inputs['Strength'].default_value = 0.0
    g.out(em.outputs[0])
    return m

def city_mat():
    m, g = material('city_windows')
    if PASS != 'beauty':
        g.out(None); return m
    c, f = g.attr('col')
    em = g.new('ShaderNodeEmission'); g.put(em.inputs['Color'], c); g.put(em.inputs['Strength'], f * 0 + 1.0)
    g.out(em.outputs[0])
    return m

def city_body_mat():
    m, g = material('city_body')
    g.out(g.principled(Base_Color=(0.004, 0.0045, 0.006), Roughness=0.6))
    return m

DAY = (1.0, 0.965, 0.9)

# ---------------------------------------------------------------- build
def build():
    m_stone = stone_mat('stone')
    m_ledge = stone_mat('ledge', ledge=True)
    m_glass = glass_mat(); m_water = water_mat(); m_back = back_mat()
    pivot = bpy.data.objects.new('pivot', None); SC.collection.objects.link(pivot)
    pivot.location = (0, DEPTH * 0.5, 0); pivot.rotation_euler = (0, 0, YAW)
    def parent(ob):
        ob.parent = pivot; ob.matrix_parent_inverse = Matrix.Translation((0, -DEPTH * 0.5, 0))
    # the stone: the tile, the seam and the cavity cut right through it
    tile = prism('stone', rounded_rect(0.1, 0.044), 0.0, DEPTH)
    # the seam goes right through; the cavity is a seat 7 mm deep; the crystal sits in a hole its own shape
    gem = [mk(p) for p in parse(GEO['gem'])]
    gx = sum(p[0] for p in gem) / 6; gz = sum(p[1] for p in gem) / 6
    hole = [(gx + (x - gx) * 1.012, gz + (z - gz) * 1.006) for x, z in gem]
    for nm, poly, y0, y1 in (('cut_seam', [mk(p) for p in parse(GEO['seam'])], -0.01, DEPTH + 0.01),
                             ('cut_cav', [mk(p) for p in parse(GEO['cav'])], -0.01, 0.005),
                             ('cut_hole', hole, -0.01, DEPTH + 0.01)):
        cut = prism(nm, poly, y0, y1)
        bo = tile.modifiers.new(nm, 'BOOLEAN'); bo.operation = 'DIFFERENCE'; bo.solver = 'EXACT'; bo.object = cut
        apply_mods(tile); bpy.data.objects.remove(cut)
    bv = tile.modifiers.new('bevel', 'BEVEL'); bv.width = 0.0007; bv.segments = 3; bv.limit_method = 'ANGLE'; bv.angle_limit = math.radians(40)
    bv.harden_normals = False
    apply_mods(tile)
    tile.data.materials.append(m_stone)
    for p in tile.data.polygons: p.use_smooth = False
    parent(tile)
    # the backplane, just behind the stone and inside its outline, so only the openings see it
    bp = prism('backplane', rounded_rect(0.0985, 0.0425), DEPTH + 0.0006, DEPTH + 0.0007)
    bp.data.materials.append(m_back); parent(bp)
    bp.visible_diffuse = False; bp.visible_shadow = False; bp.visible_volume_scatter = False
    # the crystal
    cr = build_crystal(); cr.data.materials.append(m_glass); parent(cr)
    if PASS == 'spill': cr.visible_camera = False
    # rain beads on the face
    build_beads(m_water, parent)
    # the parapet it stands on, and its far edge
    led = MB(); led.box(-2.5, 2.5, -2.0, 0.42, -0.25, 0.0, 0)
    lo = led.build('ledge', [m_ledge]); bvl = lo.modifiers.new('b', 'BEVEL'); bvl.width = 0.004; bvl.segments = 3; apply_mods(lo)
    build_city()
    return pivot, tile, cr

def build_crystal():
    P = {k: np.array(mk(p)) for k, p in zip('ABCDEF', parse(GEO['gem']))}
    A, D = P['A'], P['D']
    L = np.linalg.norm(D - A); ax = (D - A) / L; nl = np.array([-ax[1], ax[0]])
    if np.dot(P['B'] - A, nl) < 0: nl = -nl            # nl points to the B C side
    tB = np.dot(P['B'] - A, ax) / L; tC = np.dot(P['C'] - A, ax) / L
    tF = np.dot(P['F'] - A, ax) / L; tE = np.dot(P['E'] - A, ax) / L
    wR = np.dot(P['B'] - A, nl); wL = -np.dot(P['F'] - A, nl)
    def wid(t, t1, t2, w):
        if t < t1: return w * t / t1
        if t > t2: return w * (1 - t) / (1 - t2)
        return w
    ts = sorted(set([round(x, 5) for x in list(np.linspace(0, 1, 121)) + [tB, tC, tF, tE]]))
    NS = 36
    Y0 = 0.0075; HB = 0.003               # a thin crystal set flush in its seat: a faceted lens 1.3 cm deep
    K = math.tan(math.radians(5.0)); BUL = 0.003
    verts = []; idx = {}
    def add(key, co): idx[key] = len(verts); verts.append(co)
    for side, sg in (('f', -1), ('b', 1)):
        for i, t in enumerate(ts):
            for j in range(-NS, NS + 1):
                s = j / NS
                w = wid(t, tB, tC, wR) if s >= 0 else wid(t, tF, tE, wL)
                lat = s * w
                q = A + ax * (t * L) + nl * lat
                h = K * (w - abs(lat))
                h += BUL * (1 - (2 * abs(s) - 1) ** 2) * math.sin(math.pi * t) ** 0.6 * (w / max(wR, wL))
                kk = 0.92 if side == 'b' else 1.0
                y = Y0 + sg * (HB + h * kk)
                add((side, i, j), (q[0], y, q[1] + 0.1))
    faces = []
    nt = len(ts)
    for side in ('f', 'b'):
        for i in range(nt - 1):
            for j in range(-NS, NS):
                a, b, c, d = idx[(side, i, j)], idx[(side, i, j + 1)], idx[(side, i + 1, j + 1)], idx[(side, i + 1, j)]
                faces.append((a, b, c, d) if side == 'b' else (a, d, c, b))
    # the girdle band joins the front and back outlines
    for j in (-NS, NS):
        for i in range(nt - 1):
            a, b, c, d = idx[('f', i, j)], idx[('f', i + 1, j)], idx[('b', i + 1, j)], idx[('b', i, j)]
            faces.append((a, b, c, d) if j == NS else (d, c, b, a))
    bm = bmesh.new()
    bv = [bm.verts.new(v) for v in verts]
    for f in faces:
        try: bm.faces.new([bv[k] for k in f])
        except ValueError: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-8)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('crystal'); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    try: me.set_sharp_from_angle(angle=math.radians(7.0))
    except Exception as e: print('sharp', e)
    ob = bpy.data.objects.new('crystal', me); SC.collection.objects.link(ob)
    return ob

def inside_any(x, z, polys):
    for poly in polys:
        n = len(poly); c = False
        for i in range(n):
            x1, z1 = poly[i]; x2, z2 = poly[(i + 1) % n]
            if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1: c = not c
        if c: return True
    return False

def build_beads(m_water, parent):
    keep = [[mk(p) for p in parse(GEO['cav'])], [mk(p) for p in parse(GEO['seam'])]]
    grow = []
    for poly in keep:   # a margin around the openings
        cx = sum(p[0] for p in poly) / len(poly); cz = sum(p[1] for p in poly) / len(poly)
        grow.append([(cx + (x - cx) * 1.12, cz + (z - cz) * 1.04) for x, z in poly])
    mb = MB(); n = 0; tries = 0
    while n < 70 and tries < 4000:
        tries += 1
        x = rng.uniform(-0.092, 0.092); z = rng.uniform(-0.092, 0.092)
        if abs(x) > 0.056 and abs(z) > 0.056 and math.hypot(abs(x) - 0.056, abs(z) - 0.056) > 0.040: continue
        if inside_any(x, z, grow): continue
        # more small ones, a few large; larger ones sit lower on the face (they gather as they run)
        r = 0.00035 + 0.0016 * rng.random() ** 3.2
        if z > 0.03 and r > 0.0011: continue
        sph_v, sph_f = [], []
        nu, nv = 14, 7
        for iv in range(nv + 1):
            ph = (math.pi / 2) * iv / nv
            for iu in range(nu):
                th = 2 * math.pi * iu / nu
                rr = r * math.cos(ph); hh = r * 0.62 * math.sin(ph)
                sag = 0.18 * r * (1 - math.sin(ph))
                sph_v.append((x + rr * math.cos(th), -hh, z + 0.1 + rr * math.sin(th) - sag * (math.sin(th) < 0)))
        for iv in range(nv):
            for iu in range(nu):
                a = iv * nu + iu; b = iv * nu + (iu + 1) % nu
                sph_f.append((a, b, b + nu, a + nu))
        base = list(range(nu))[::-1]
        mb.add(sph_v, sph_f + [tuple(base)], 0); n += 1
    ob = mb.build('beads', [m_water], smooth=True)
    parent(ob)

def build_city():
    # far towers beyond the parapet: dark faces and sparse lit windows (cool whites, the odd pale blue)
    m_w = city_mat(); m_b = city_body_mat()
    win = MB(); body = MB()
    crng = random.Random(21)
    for k in range(46):
        y = crng.uniform(70, 320); x = crng.uniform(-0.6, 0.6) * y
        w = crng.uniform(10, 30); top = crng.uniform(-6, 30) + y * 0.07
        body.box(x - w / 2, x + w / 2, y, y + w, -60, top, 0)
        fl = 3.3; nx = int(w / 1.6)
        for fz in np.arange(top - 2.5, -40, -fl):
            for ix in range(nx):
                if crng.random() > (0.06 if fz / y < 0.02 else 0.04): continue
                cx = x - w / 2 + (ix + 0.5) * w / nx
                if abs(cx / y) < 0.16 and fz / y > 0.03: continue   # keep the air above the stone clear
                cool = crng.random()
                col = (0.75, 0.85, 1.0) if cool < 0.55 else ((0.95, 0.95, 0.92) if cool < 0.9 else (0.3, 0.45, 1.0))
                e = (0.6 + 9.0 * crng.random() ** 3.0) * (120.0 / y) ** 0.5
                c4 = (col[0] * e, col[1] * e, col[2] * e, 1.0)
                win.add([(cx - 0.4, y - 0.05, fz), (cx + 0.4, y - 0.05, fz), (cx + 0.4, y - 0.05, fz + 0.7), (cx - 0.4, y - 0.05, fz + 0.7)],
                        [(0, 1, 2, 3)], 0, col=[c4] * 4)
    body.build('towers', [m_b])
    win.build('windows', [m_w], col=True)
    # behind the camera: the street the stone looks out on, for its reflections: two lit facades and a lamp
    rf = MB(); rrng = random.Random(4)
    for (az0, dist, w, h, z0, cols, rows, p) in ((-0.5, 22.0, 9.0, 12.0, -1.0, 7, 8, 0.32), (0.42, 30.0, 14.0, 18.0, 1.0, 10, 10, 0.2)):
        cx0 = math.sin(az0) * dist; cy0 = -math.cos(az0) * dist; tx, ty = math.cos(az0), math.sin(az0)
        for i in range(cols):
            for j in range(rows):
                if rrng.random() > p: continue
                u = (i + 0.5) / cols - 0.5; zc = z0 + (j + 0.3) * h / rows
                cx = cx0 + tx * u * w; cy = cy0 + ty * u * w
                col = (0.78, 0.86, 1.0) if rrng.random() < 0.6 else (0.96, 0.95, 0.9)
                e = rrng.uniform(6.0, 24.0); c4 = (col[0] * e, col[1] * e, col[2] * e, 1.0)
                ww, hh = 0.45 * w / cols, 0.55 * h / rows
                rf.add([(cx - tx * ww, cy - ty * ww, zc), (cx + tx * ww, cy + ty * ww, zc), (cx + tx * ww, cy + ty * ww, zc + hh), (cx - tx * ww, cy - ty * ww, zc + hh)],
                       [(0, 1, 2, 3)], 0, col=[c4] * 4)
    for (cx, cy, cz, ww, hh, e) in ((-3.0, -24.0, 0.0, 7.0, 3.2, 1.2), (6.0, -30.0, 4.0, 4.0, 9.0, 0.8)):
        c4 = (0.8 * e, 0.88 * e, 1.0 * e, 1.0)
        rf.add([(cx - ww / 2, cy, cz), (cx + ww / 2, cy, cz), (cx + ww / 2, cy, cz + hh), (cx - ww / 2, cy, cz + hh)], [(0, 1, 2, 3)], 0, col=[c4] * 4)
    rf.build('street_windows', [m_w], col=True)

def lights():
    on = PASS == 'beauty'
    # a cool street lamp up to the left, in front: the key
    def area(name, loc, size, energy, col, target, shape='DISK', sy=None, vis_cam=False, vis_trans=True):
        l = bpy.data.lights.new(name, 'AREA'); l.shape = shape; l.size = size
        if sy: l.size_y = sy
        l.energy = energy; l.color = col
        o = bpy.data.objects.new(name, l); SC.collection.objects.link(o); o.location = loc
        o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        o.visible_camera = vis_cam; o.visible_transmission = vis_trans
        return o
    if on:
        area('lamp', (1.1, 1.3, 1.5), 0.25, 150.0, (0.84, 0.9, 1.0), (0.0, 0.02, 0.12))
        area('key', (1.5, -1.2, 1.4), 0.6, 2.0, (0.8, 0.88, 1.0), (0.0, 0.0, 0.1))
        area('rim', (-0.9, 1.1, 0.45), 0.5, 60.0, (0.16, 0.26, 1.0), (-0.05, 0.02, 0.1), shape='RECTANGLE', sy=0.12)
        area('fill', (0.6, -2.5, 0.25), 1.6, 9.0, (0.55, 0.65, 1.0), (0.0, 0.0, 0.1))
    # the meadow's daylight behind the stone: a whisper at rest, the full sun when let through
    e = 1.4 if on else (60.0 if PASS == 'spill' else 0.0)
    if e > 0:
        cen = Vector((0.0, 0.0, 0.1))
        rot = Matrix.Rotation(YAW, 4, 'Z')
        loc = cen + rot @ Vector((0.0, DEPTH * 0.5 + 0.012, 0.0)) + Vector((0, DEPTH * 0.5, 0))
        o = area('daylight', tuple(loc), 0.16, e, DAY, tuple(loc + rot @ Vector((0, -1, 0.0))), shape='RECTANGLE', sy=0.17, vis_trans=False)
        o.data.cycles.cast_shadow = True

def world():
    wm = bpy.data.worlds.new('w'); SC.world = wm; wm.use_nodes = True; nt = wm.node_tree; nt.nodes.clear(); g = G(nt)
    bg = g.new('ShaderNodeBackground'); o = g.new('ShaderNodeOutputWorld'); nt.links.new(bg.outputs[0], o.inputs[0])
    if PASS == 'beauty':
        gp = g.new('ShaderNodeNewGeometry'); _, _, iz = g.sep(g.scale(V(g, gp.outputs['Incoming']), -1.0))
        sky = g.mix((0.010, 0.013, 0.024), (0.0015, 0.002, 0.005), g.sm(-0.05, 0.5, iz))
        g.put(bg.inputs[0], sky); bg.inputs[1].default_value = 1.0
    else:
        bg.inputs[0].default_value = (0, 0, 0, 1); bg.inputs[1].default_value = 0.0

def haze():
    # rain mist: a breath of it in front of the stone, more between the stone and the city.
    # It scatters camera rays only: seen, never bounced through.
    def box(name, y0, y1, dens):
        m, g = material(name)
        lp = g.new('ShaderNodeLightPath')
        sc = g.new('ShaderNodeVolumeScatter'); sc.inputs['Anisotropy'].default_value = 0.6
        g.put(sc.inputs['Density'], S(g, lp.outputs['Is Camera Ray']) * dens)
        g.out(None, sc.outputs[0])
        mb = MB(); mb.box(-1.6, 1.6, y0, y1, -0.01, 1.2, 0); mb.build(name, [m])
    if PASS == 'spill':
        box('mist_front', -0.45, -0.002, 0.012)
    else:
        box('mist_front', -0.9, -0.002, 0.002)
        box('mist_far', 0.3, 6.0, 0.008)

def camera():
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); SC.collection.objects.link(cam); SC.camera = cam
    cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24.0; cd.lens = 85.0
    r = SC.render
    if FRAME == 'desktop':
        r.resolution_x, r.resolution_y = 1920, 1200
        d = 1.04; zc = 0.112; tgt = 0.112
        cd.shift_y = 0.0; cd.shift_x = 0.0
    else:
        r.resolution_x, r.resolution_y = 1000, 2160
        cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 12.2
        d = 1.62; zc = 0.125; tgt = 0.125
        cd.shift_y = -0.17
    cam.location = (0.0, -d, zc)
    cam.rotation_euler = (math.radians(90) - math.atan2(zc - tgt, d), 0, 0)
    cd.clip_start = 0.05; cd.clip_end = 400
    cd.dof.use_dof = True; cd.dof.focus_distance = d - 0.004; cd.dof.aperture_fstop = 5.6 if FRAME == 'desktop' else 10.0
    cd.dof.aperture_blades = 0
    return cam, cd

def main():
    t0 = time.time()
    build(); lights(); world()
    if HAZE and PASS in ('beauty', 'spill'): haze()
    cam, cd = camera()
    r = SC.render; r.engine = 'CYCLES'; r.resolution_percentage = RES
    r.threads_mode = 'FIXED'; r.threads = 4
    c = SC.cycles; c.device = 'CPU'; c.samples = SAMPLES; c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.01; c.adaptive_min_samples = 32
    if TL > 0: c.time_limit = TL
    data = PASS in ('uv',)
    c.use_denoising = not data
    c.denoiser = 'OPENIMAGEDENOISE'; c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; c.denoising_prefilter = 'ACCURATE'
    c.max_bounces = 16; c.diffuse_bounces = 3; c.glossy_bounces = 6; c.transmission_bounces = 14; c.volume_bounces = 0; c.transparent_max_bounces = 8
    c.sample_clamp_indirect = 10.0 if PASS != 'uv' else 0.0
    c.blur_glossy = 0.4 if PASS != 'uv' else 0.0
    c.caustics_refractive = PASS == 'spill'; c.caustics_reflective = False
    c.use_light_tree = True
    c.filter_width = 1.5 if not data else 1.0
    c.seed = 3
    if data:
        c.adaptive_threshold = 0.004
    vs = SC.view_settings; vs.view_transform = 'Standard' if PASS != 'beauty' else 'AgX'; vs.look = 'None'
    r.image_settings.file_format = 'OPEN_EXR'; r.image_settings.color_depth = '32'; r.image_settings.exr_codec = 'ZIP'
    r.image_settings.color_mode = 'RGBA'
    SC.use_nodes = False
    # camera intrinsics for the browser: the straight-through tangent of every pixel
    W, H = r.resolution_x, r.resolution_y
    if cd.sensor_fit == 'VERTICAL':
        th = cd.sensor_height / 2 / cd.lens; tw = th * W / H
    else:
        tw = cd.sensor_width / 2 / cd.lens; th = tw * H / W
    big = max(W, H)
    meta = {'frame': FRAME, 'w': W, 'h': H, 'tan_w': tw, 'tan_h': th,
            'shift_x': cd.shift_x * 2 * (tw if W >= H else th) , 'shift_y': cd.shift_y * 2 * (tw if W >= H else th),
            'pitch': cam.rotation_euler[0] - math.radians(90)}
    json.dump(meta, open(OUT.replace('.exr', '.json'), 'w'), indent=1)
    print('BUILD %.1fs' % (time.time() - t0)); sys.stdout.flush()
    t1 = time.time()
    r.filepath = OUT; bpy.ops.render.render(write_still=True)
    print('RENDER %.1fs' % (time.time() - t1))

main()
