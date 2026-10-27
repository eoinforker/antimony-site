# stone.py: the shared Antimony stone, for every world.
# Blender 4.5 LTS, Cycles. No add-ons, no dependencies beyond Blender's own Python (numpy, mathutils).
#
# The Break mark carved as an old, purposeful monolith: the exact Break geometry (break-geometry.json:
# the tile rx 22 on 100, the seam at 16 degrees, the hexagonal cavity, the gem) given real thickness,
# honed basalt faces from scanned stone, softened and chipped arrises, faint drove marks and erosion,
# lichen and moss rising from the base, optional rain darkening and wet sheen, darker unpolished cut
# faces in the seam and cavity, and the crystal as true sky glass (#94E6FF held by absorption).
#
# Use from another Blender script:
#   import sys; sys.path.insert(0, '/home/user/antimony-site/directions/stone')
#   import stone
#   parts = stone.build_stone(coll, scale_m=2.2, location=(0, 0, 0), rotation=(0, 0, 0.1),
#                             wetness=0.0, moss=0.5, cache_dir=stone.DEFAULT_CACHE)
#   gnd = stone.make_ground(coll, parts, radius=40)                      # optional soil and grass blend
#   stone.scatter_grass(coll, parts, radius=25, count=30000, ground=gnd) # optional Poly Haven grass
#   stone.mark_caustic_lights([sun_object])                              # let the sun make caustics
#
# Space and units
#   Built at true size in metres. Local axes: X across the mark, Z up, the front face looks down -Y
#   (so a camera on the -Y side sees the mark the right way round). `location` is the point on the
#   ground under the centre of the stone's base; the tile is sunk `sink` below it.
#
# build_stone(collection, scale_m, location, rotation, wetness=0.0, moss=0.5, cache_dir=DEFAULT_CACHE, **opts)
#   collection   bpy collection the objects go into.
#   scale_m      side of the Break tile in metres (its full height, before sinking). About 2 for a
#                meadow, 20 for a landmark.
#   location     (x, y, z) ground point under the stone.
#   rotation     (rx, ry, rz) Euler radians for the whole stone (a slight lean of 1 or 2 degrees on
#                rx or ry reads as age; rz turns it to the view).
#   wetness      0 dry to 1 soaked: darkens the stone (more in streaks and on upward faces and the
#                porous cut faces), lowers roughness, adds a thin clear water coat and beads.
#   moss         0 to 1: moss and lichen creeping up from the base, masked by height above the ground,
#                ambient occlusion and noise. 0 gives clean stone. Kept off the upper faces so the
#                mark stays clean.
#   cache_dir    the shared asset cache (ambientcg/<id>/ and polyhaven/<asset>/). Uses ambientCG
#                Rock041 (honed faces), Rock035 (cut faces and chips), Moss002 (moss); Ground037 and
#                Grass004 for the ground helper; Poly Haven grass_medium_01 for the grass helper.
#   Options (all keyword):
#     thickness=0.26      depth of the stone as a fraction of scale_m.
#     sink=0.035          how far the tile goes into the ground, fraction of scale_m.
#     bevel=0.009         radius of the softened arris, fraction of scale_m.
#     chips=1.0           strength of chipped edges (0 none). Chips are cut into the real geometry.
#     erosion=1.0         gentle waviness of the faces and weathering at the foot (geometry), and pits.
#     tool_marks=1.0      faint drove (chisel) lines running at the seam's 16 degrees on the faces.
#     lichen=None         lichen amount; defaults to 0.6 x moss.
#     stone_value=1.0     brightness of the basalt (1 is about 6 percent albedo).
#     veins=0.0           faint pale quartz veins (0 none, 1 visible).
#     glow=0.15           inner glow of the crystal (0 none; 1 strong, for night).
#     inner_facets=True   a faint internal fracture plane along the crystal's long axis.
#     caustics=True       crystal is an MNEE caustic caster, the stone a receiver (also call
#                         mark_caustic_lights on your sun or lamps).
#     detail=380          mesh resolution: voxels across the tile (about 5 mm at 2 m).
#     seed=7              varies the chips, erosion and growth.
#     geometry=None       path to break-geometry.json (defaults to the copy beside this file).
#     name='antimony'     prefix for object names.
#     Opt-in (defaults leave the stone exactly as before):
#     growth=True         False keeps the mark clean: no moss or lichen on the stone at all (growth only
#                         on the ground around it, which the scene owns).
#     carve=0.0           hand tooling on the faces, 0 none, 1 clear: patches of parallel chisel strokes
#                         at varied angles, a smooth drafted margin along every arris, point (pick) marks
#                         on the seam and cavity walls, worn faint in places.
#     chip_size=1.0       scale of the edge chips (2 gives larger, rarer spalls).
#     chip_dots=1.0       the small round bites along the arrises (0 leaves only the larger faceted spalls).
#     damp_foot=0.0       damp wicked up from the ground: a darker, slightly glossier band at the foot
#                         with a ragged, tongued upper edge (0 none, 1 about a tenth of the stone's height).
#     crystal_depth=0.0   more depth in the glass (0 as before, 1 full): a second, weak absorption that
#                         leans long paths toward cobalt (thick parts read deeper, thin edges stay sky),
#                         the inner glow lowered so it does not fill the gem evenly, and a finer polish
#                         so catches of light are crisp.
#     crystal_bevel=1.0   width of the polished arrises on the crystal, as a multiple of the usual
#                         (larger catches light along the edges as a fine line).
#     inner_faces=0       extra faint internal fracture planes at varied angles inside the crystal (they
#                         use the veil's material and go in the returned 'inner' object).
#   Returns a dict: {'root': empty parent, 'stone': mesh object, 'crystal': mesh object,
#                    'veil': internal facet object or None, 'info': dict of measures (scale, T, sink,
#                    footprint half sizes, matrix)}.
#
# make_ground(collection, parts, radius=30.0, mound=0.012, wetness=None, cache_dir=None, res=None)
#   A ground disc that rises a little against the stone (soil settled against it over centuries),
#   blending mossy soil at the foot (Ground037) into turf (Grass004) further out, with moss where
#   the two meet. wetness defaults to the stone's. Returns the ground object (z of its surface at a
#   point is given by ground_height(parts, x, y)).
#
# scatter_grass(collection, parts, radius=20.0, count=20000, ground=None, cache_dir=None,
#               front_clear=True, seed=3, scale=1.0, inner=None)
#   Poly Haven grass_medium_01 clumps scattered by geometry nodes, dense at the stone's sides and
#   back, hugging the foot, kept short in front so the whole mark stays visible.
#
# mark_caustic_lights(lights)  sets is_caustics_light on the given light objects.
# sky_linear()                  #94E6FF in linear RGB.
#
# Notes
#   - No em or en dashes; British English. CC0 assets only (ambientCG and Poly Haven).
#   - The mesh is boolean cut, bevelled, voxel remeshed and then displaced in Python, so chips are in
#     the silhouette, not only in the shading. It is about 0.5 M faces; build time 20 to 60 s.
#   - The stone keeps per-vertex attributes 'edge' (arris wear), 'chip' (fresh fracture) and 'cut'
#     (seam and cavity walls) that the material reads; other scenes can read them too.
#   - Detail is scale-aware, so the stone holds from about 1 m to 300 m. Fine detail is sized in real
#     metres (scan grain 1.2 m tiles, pits 2 to 3 cm, lichen rosettes 6 cm, drove lines 4 mm to 2.5 cm,
#     arris wear 5 cm, rain beads 7 mm, fine streaks 12 cm), so at landmark size it falls below a pixel
#     the way real grain does. Form-scale weathering is sized to the stone (macro tone, patches,
#     colonies, damp band, long rain stains, a second landmark-sized reading of the scan) and above
#     about 6 m (full at 40 m) shallow hollows and vertical runnels are added. Every cell pattern is
#     domain-warped, sized per cell and gated at random, so nothing reads as a regular grid of dots.
#   - Render settings it relies on: Cycles, caustics on (scene.cycles.caustics_refractive) for light
#     through the crystal; transmission bounces of 8 or more; volume bounces 0 is fine.
import bpy, bmesh, math, json, os, re
import numpy as np
from mathutils import Vector, Matrix, Euler, noise

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CACHE = '/tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad/assets'
SKY_HEX = '94E6FF'


# ------------------------------------------------------------------ small helpers
def _s2l(c):
    return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92


def sky_linear():
    return tuple(_s2l(int(SKY_HEX[i:i + 2], 16) / 255) for i in (0, 2, 4))


def _poly(d):
    nums = [float(v) for v in re.findall(r'-?\d+\.?\d*', d)]
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]


def _rrect(rx=22.0, n=28):
    pts = []
    for cx, cy, a0 in ((100 - rx, rx, -90), (100 - rx, 100 - rx, 0), (rx, 100 - rx, 90), (rx, rx, 180)):
        for i in range(n + 1):
            t = math.radians(a0 + 90 * i / n)
            pts.append((cx + rx * math.cos(t), cy + rx * math.sin(t)))
    return pts


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _seg_dist(px, py, poly):
    """distance from points to the closed polygon's edges (numpy, SVG units)"""
    d = np.full(px.shape, 1e9)
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]; bx, by = poly[(i + 1) % n]
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy
        t = np.clip(((px - ax) * vx + (py - ay) * vy) / L2, 0, 1)
        d = np.minimum(d, np.hypot(px - ax - t * vx, py - ay - t * vy))
    return d


def _rrect_sdf(px, py, rx=22.0):
    qx = np.abs(px - 50) - (50 - rx); qy = np.abs(py - 50) - (50 - rx)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - rx


class _NT:
    """terse node building"""
    def __init__(self, mat):
        self.nt = mat.node_tree; self.nt.nodes.clear()

    def n(self, t, loc=(0, 0), **kw):
        nd = self.nt.nodes.new(t); nd.location = loc
        for k, v in kw.items():
            setattr(nd, k, v)
        return nd

    def l(self, a, b):
        self.nt.links.new(a, b)

    def math(self, op, a, b=None, loc=(0, 0), clamp=False):
        m = self.n('ShaderNodeMath', loc, operation=op); m.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                self.l(v, m.inputs[i])
        return m.outputs[0]

    def mix(self, fac, a, b, blend='MIX', loc=(0, 0)):
        m = self.n('ShaderNodeMix', loc); m.data_type = 'RGBA'; m.blend_type = blend; m.clamp_result = False
        for sock, v in ((m.inputs['Factor'], fac), (m.inputs[6], a), (m.inputs[7], b)):
            if isinstance(v, (int, float)):
                sock.default_value = v
            elif isinstance(v, tuple):
                sock.default_value = (*v, 1) if len(v) == 3 else v
            else:
                self.l(v, sock)
        return m.outputs[2]

    def mixf(self, fac, a, b, loc=(0, 0)):
        m = self.n('ShaderNodeMix', loc); m.data_type = 'FLOAT'
        for sock, v in ((m.inputs['Factor'], fac), (m.inputs[2], a), (m.inputs[3], b)):
            if isinstance(v, (int, float)):
                sock.default_value = v
            else:
                self.l(v, sock)
        return m.outputs[0]

    def ramp(self, x, a, b, lo=0.0, hi=1.0, loc=(0, 0)):
        m = self.n('ShaderNodeMapRange', loc); m.interpolation_type = 'SMOOTHSTEP'
        m.inputs['From Min'].default_value = a; m.inputs['From Max'].default_value = b
        m.inputs['To Min'].default_value = lo; m.inputs['To Max'].default_value = hi
        self.l(x, m.inputs['Value'])
        return m.outputs['Result']

    def attr(self, name, loc=(0, 0)):
        a = self.n('ShaderNodeAttribute', loc); a.attribute_type = 'GEOMETRY'; a.attribute_name = name
        return a.outputs['Fac']


def _img(path, noncolor=False):
    key = os.path.abspath(path)
    for im in bpy.data.images:
        if im.filepath and os.path.abspath(bpy.path.abspath(im.filepath)) == key:
            return im
    im = bpy.data.images.load(path, check_existing=True)
    if noncolor:
        im.colorspace_settings.name = 'Non-Color'
    return im


def _acg(cache, aid, kind):
    return os.path.join(cache, 'ambientcg', aid, f'{aid}_2K-JPG_{kind}.jpg')


def _bake(ob):
    """apply every modifier of ob (evaluated mesh replaces data)"""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear(); ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return me


def _prism(name, pts, y0, y1, coll):
    bm = bmesh.new()
    f = [bm.verts.new((x, y0, z)) for x, z in pts]
    b = [bm.verts.new((x, y1, z)) for x, z in pts]
    bm.faces.new(f[::-1]); bm.faces.new(b)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((f[i], f[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    return ob


# ------------------------------------------------------------------ the stone
def build_stone(collection, scale_m=2.0, location=(0, 0, 0), rotation=(0, 0, 0), wetness=0.0, moss=0.5,
                cache_dir=DEFAULT_CACHE, thickness=0.26, sink=0.035, bevel=0.009, chips=1.0, erosion=1.0,
                tool_marks=1.0, lichen=None, stone_value=1.0, veins=0.0, glow=0.15, inner_facets=True, caustics=True,
                detail=380, seed=7, geometry=None, name='antimony', growth=True, carve=0.0, damp_foot=0.0,
                chip_size=1.0, chip_dots=1.0, crystal_depth=0.0, inner_faces=0, crystal_bevel=1.0):
    geo = json.load(open(geometry or os.path.join(HERE, 'break-geometry.json')))
    if lichen is None:
        lichen = 0.6 * moss
    if not growth:
        moss, lichen = 0.0, 0.0
    S = scale_m / 100.0                      # metres per SVG unit
    T = thickness * scale_m
    SK = sink * scale_m

    def xz(p):                               # SVG (x right, y down) to local (x, z up), base on the ground
        return ((p[0] - 50) * S, (100 - p[1]) * S - SK)

    scn = bpy.context.scene
    tmp = bpy.data.collections.new(name + '_build'); scn.collection.children.link(tmp)

    # 1. the tile, cut by the seam and the cavity (exact boolean)
    tile = _prism(name + '_stone', [xz(p) for p in _rrect()], -T / 2, T / 2, tmp)
    seam_pts = _poly(geo['seam']); cav_pts = _poly(geo['cav']); gem_pts = _poly(geo['gem'])
    cutters = [_prism(name + '_cut_seam', [xz(p) for p in seam_pts], -T, T, tmp),
               _prism(name + '_cut_cav', [xz(p) for p in cav_pts], -T, T, tmp)]
    for c in cutters:
        md = tile.modifiers.new('cut', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = c
    _bake(tile)
    for c in cutters:
        bpy.data.meshes.remove(c.data)

    # 2. a softened arris everywhere, then 3. an even voxel skin so it can be chipped
    bv = tile.modifiers.new('arris', 'BEVEL'); bv.width = bevel * scale_m; bv.segments = 3
    bv.limit_method = 'ANGLE'; bv.angle_limit = math.radians(30); bv.use_clamp_overlap = True
    _bake(tile)
    rm = tile.modifiers.new('skin', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = scale_m / detail
    rm.adaptivity = 0.0; rm.use_smooth_shade = True
    me = _bake(tile)

    # 4. weathering in the geometry: chips at the arrises, faint waviness, a worn foot
    N = len(me.vertices)
    co = np.empty(N * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(N, 3).astype(np.float64)
    nr = np.empty(N * 3, np.float32); me.vertex_normals.foreach_get('vector', nr); nr = nr.reshape(N, 3)
    u = co[:, 0] / S + 50; v = 100 - (co[:, 2] + SK) / S          # back to SVG units
    d_t = np.abs(_rrect_sdf(u, v)) * S
    d_s = _seg_dist(u, v, seam_pts) * S
    d_c = _seg_dist(u, v, cav_pts) * S
    dy = T / 2 - np.abs(co[:, 1])
    d2 = np.minimum(np.minimum(d_t, d_s), d_c)
    de = np.minimum.reduce([np.maximum(d2, dy), np.maximum(d_t, d_s), np.maximum(d_t, d_c), np.maximum(d_s, d_c)])
    BV = bevel * scale_m
    edge = (1 - _smooth(0.0, 2.6 * BV, de)) ** 1.3
    cut = (1 - _smooth(0.4 * BV, 1.6 * BV, np.minimum(d_s, d_c))) * _smooth(0.5 * BV, 1.6 * BV, dy) \
        * _smooth(0.5 * BV, 1.5 * BV, d_t)
    rng = np.random.default_rng(seed)
    off = Vector(rng.uniform(-50, 50, 3))
    fchip = 1.0 / (0.045 * scale_m * chip_size); fsm = 1.0 / (0.012 * scale_m * chip_size); fer = 1.0 / (0.16 * scale_m)
    chip = np.zeros(N); disp = np.zeros(N)
    zrel = (co[:, 2] + SK) / scale_m                            # 0 at the tile's foot, 1 at its top
    for i in range(N):
        p = Vector(co[i]) + off
        er = noise.fractal(p * fer, 1.0, 2.0, 4)
        foot = 1.0 + 2.0 * max(0.0, 0.18 - zrel[i]) / 0.18
        top = 1.0 + max(0.0, float(nr[i, 2]))
        disp[i] = erosion * 0.0011 * scale_m * er * foot * top
        e = edge[i]
        if e > 0.02 and chips > 0:
            n1 = noise.fractal(p * fchip, 0.8, 2.1, 4)
            n2 = noise.cell(p * fsm)
            c = max(0.0, min(1.0, (n1 - 0.26) / 0.18))
            c = max(c, (1.0 if n2 > 0.88 else 0.0) * chip_dots) * e
            # a fracture is faceted: quantise the depth a little
            depth = math.floor((0.55 + 0.45 * noise.cell(p * fchip * 2.0)) * 4) / 4
            chip[i] = c
            disp[i] -= chips * 0.009 * scale_m * c * (0.5 + 0.5 * depth)
    co += nr * disp[:, None]
    me.vertices.foreach_set('co', co.astype(np.float32).ravel())
    for an, data in (('edge', edge), ('chip', np.clip(chip, 0, 1)), ('cut', cut)):
        at = me.attributes.new(an, 'FLOAT', 'POINT'); at.data.foreach_set('value', data.astype(np.float32))
    me.update()
    for p_ in me.polygons:
        p_.use_smooth = True

    # 5. the crystal: the gem hexagon as a cut stone, a girdle, a crown ring and an apex on each face
    cx, cz = xz((50, 51.5))
    gem = [xz(p) for p in gem_pts]
    yg, yr, ya, k = 0.10 * T, 0.30 * T, 0.40 * T, 0.52
    bm = bmesh.new()
    gf = [bm.verts.new((x, -yg, z)) for x, z in gem]; gb = [bm.verts.new((x, yg, z)) for x, z in gem]
    rf = [bm.verts.new((cx + (x - cx) * k, -yr, cz + (z - cz) * k)) for x, z in gem]
    rb = [bm.verts.new((cx + (x - cx) * k, yr, cz + (z - cz) * k)) for x, z in gem]
    af = bm.verts.new((cx, -ya, cz)); ab = bm.verts.new((cx, ya, cz))
    n = len(gem)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((gf[i], gf[j], gb[j], gb[i]))
        bm.faces.new((gf[j], gf[i], rf[i], rf[j])); bm.faces.new((rf[j], rf[i], af))
        bm.faces.new((gb[i], gb[j], rb[j], rb[i])); bm.faces.new((rb[i], rb[j], ab))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cme = bpy.data.meshes.new(name + '_crystal'); bm.to_mesh(cme); bm.free()
    crystal = bpy.data.objects.new(name + '_crystal', cme); tmp.objects.link(crystal)
    bvc = crystal.modifiers.new('arris', 'BEVEL'); bvc.width = 0.0012 * scale_m * crystal_bevel; bvc.segments = 2 if crystal_bevel == 1.0 else 3
    bvc.limit_method = 'ANGLE'; bvc.angle_limit = math.radians(20)
    _bake(crystal)
    veil = None
    if inner_facets:
        # a faint internal fracture along the crystal's long axis (the line of the seam)
        top, bot = xz(gem_pts[0]), xz(gem_pts[3])
        vm = bpy.data.meshes.new(name + '_veil')
        vm.from_pydata([(top[0] * 0.9 + cx * 0.1, 0, top[1] * 0.9 + cz * 0.1), (cx, -0.30 * T, cz),
                        (bot[0] * 0.9 + cx * 0.1, 0, bot[1] * 0.9 + cz * 0.1), (cx + 0.02 * scale_m, 0.26 * T, cz)],
                       [], [(0, 1, 2, 3)])
        veil = bpy.data.objects.new(name + '_veil', vm); tmp.objects.link(veil)
        veil.visible_shadow = False
    inner = None
    if inner_faces > 0:
        # small fracture planes inside the gem, each at its own angle and tilt, slightly irregular
        rs = np.random.default_rng(seed + 31)
        R = 0.5 * max(math.dist(gem[i], gem[j]) for i in range(len(gem)) for j in range(len(gem)))
        iv, ifc = [], []
        for _ in range(int(inner_faces)):
            a = rs.uniform(0, math.pi); b = rs.uniform(0.35, 1.2) * rs.choice((-1, 1))
            u = Vector((math.cos(a), 0, math.sin(a))); w = Vector((-math.sin(a), 0, math.cos(a)))
            v = (w * math.cos(b) + Vector((0, 1, 0)) * math.sin(b)).normalized()
            c = Vector((cx, 0, cz)) + w * rs.uniform(-0.25, 0.25) * R + u * rs.uniform(-0.2, 0.2) * R
            lh = rs.uniform(0.25, 0.5) * R; wh = min(rs.uniform(0.12, 0.25) * R, 0.06 * T / max(abs(math.sin(b)), 0.2))
            k0 = len(iv)
            for su, sv in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
                iv.append(tuple(c + u * su * lh * rs.uniform(0.7, 1.0) + v * sv * wh * rs.uniform(0.6, 1.0)))
            ifc.append((k0, k0 + 1, k0 + 2, k0 + 3))
        im_ = bpy.data.meshes.new(name + '_inner'); im_.from_pydata(iv, [], ifc)
        inner = bpy.data.objects.new(name + '_inner', im_); tmp.objects.link(inner)
        inner.visible_shadow = False

    # 6. materials
    tile.data.materials.append(_stone_material(name, scale_m, T, SK, cache_dir, wetness, moss, lichen,
                                               tool_marks, erosion, stone_value, seed, veins, growth, carve, damp_foot))
    crystal.data.materials.append(_crystal_material(name, T, glow, crystal_depth))
    if veil:
        veil.data.materials.append(_veil_material(name))
    if inner:
        inner.data.materials.append(veil.data.materials[0] if veil else _veil_material(name))

    # 7. parent, place, hand over
    root = bpy.data.objects.new(name, None); root.empty_display_size = scale_m * 0.6
    collection.objects.link(root)
    for ob in (tile, crystal, veil, inner):
        if ob is None:
            continue
        tmp.objects.unlink(ob); collection.objects.link(ob); ob.parent = root
    root.location = location; root.rotation_euler = Euler(rotation)
    bpy.data.collections.remove(tmp)
    if caustics:
        crystal.cycles.is_caustics_caster = True
        tile.cycles.is_caustics_receiver = True
    bpy.context.view_layer.update()
    info = {'scale': scale_m, 'T': T, 'sink': SK, 'half_w': 50 * S, 'half_t': T / 2, 'wetness': wetness,
            'moss': moss, 'cache_dir': cache_dir, 'matrix': root.matrix_world.copy(),
            'crystal_centre': root.matrix_world @ Vector((cx, 0, cz)), 'faces': len(me.polygons)}
    return {'root': root, 'stone': tile, 'crystal': crystal, 'veil': veil, 'inner': inner, 'info': info}


def _stone_material(name, scale_m, T, SK, cache, wet, moss, lichen, tool_marks, erosion, value, seed, veins=0.0,
                    growth=True, carve=0.0, damp_foot=0.0):
    m = bpy.data.materials.new(name + '_stone'); m.use_nodes = True
    g = _NT(m); L = g.l
    tc = g.n('ShaderNodeTexCoord', (-2600, 0))
    geo = g.n('ShaderNodeNewGeometry', (-2600, -400))
    pos = tc.outputs['Object']
    # normal in object space, for masks that care which way a face looks
    vt = g.n('ShaderNodeVectorTransform', (-2400, -500)); vt.vector_type = 'NORMAL'
    vt.convert_from = 'WORLD'; vt.convert_to = 'OBJECT'; L(geo.outputs['Normal'], vt.inputs['Vector'])
    sep = g.n('ShaderNodeSeparateXYZ', (-2200, -500)); L(vt.outputs['Vector'], sep.inputs['Vector'])
    psep = g.n('ShaderNodeSeparateXYZ', (-2400, 300)); L(pos, psep.inputs['Vector'])
    face_y = g.ramp(g.math('ABSOLUTE', sep.outputs['Y']), 0.6, 0.9)          # 1 on front and back faces
    up = g.ramp(sep.outputs['Z'], 0.2, 0.8)                                   # upward-facing
    # height above the ground in metres (the tile's foot sits SK below z = 0)
    hz = psep.outputs['Z']

    def box(path, nc, scale_tex, rot=0.0, loc=(0, 0)):
        mp = g.n('ShaderNodeMapping', (loc[0] - 200, loc[1]))
        mp.inputs['Scale'].default_value = (1 / scale_tex,) * 3
        mp.inputs['Rotation'].default_value = (rot * 0.7, rot, rot * 1.3)
        mp.inputs['Location'].default_value = (seed * 0.37, seed * 0.11, seed * 0.23)
        L(pos, mp.inputs['Vector'])
        t = g.n('ShaderNodeTexImage', loc); t.image = _img(path, nc); t.projection = 'BOX'; t.projection_blend = 0.3
        L(mp.outputs['Vector'], t.inputs['Vector'])
        return t.outputs['Color']

    def warped(cell_m, amt=0.8):
        # domain warp by a noise of about three cells, so no cell pattern stays regular
        n = g.n('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 1.0 / (cell_m * 3.0)
        n.inputs['Detail'].default_value = 3; L(pos, n.inputs['Vector'])
        sub = g.n('ShaderNodeVectorMath', operation='SUBTRACT'); L(n.outputs['Color'], sub.inputs[0])
        sub.inputs[1].default_value = (0.5, 0.5, 0.5)
        sc_ = g.n('ShaderNodeVectorMath', operation='SCALE'); L(sub.outputs[0], sc_.inputs[0])
        sc_.inputs['Scale'].default_value = cell_m * amt * 2.0
        ad = g.n('ShaderNodeVectorMath', operation='ADD'); L(pos, ad.inputs[0]); L(sc_.outputs[0], ad.inputs[1])
        return ad.outputs[0]

    def cells(cell_m, amt=0.8):
        v = g.n('ShaderNodeTexVoronoi'); v.inputs['Scale'].default_value = 1.0 / cell_m
        v.inputs['Randomness'].default_value = 1.0; L(warped(cell_m, amt), v.inputs['Vector'])
        return v.outputs['Distance'], v.outputs['Color']

    def noise_m(size_m, detail=4.0, rough=0.55):
        n = g.n('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 1.0 / size_m
        n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough; L(pos, n.inputs['Vector'])
        return n.outputs['Fac']

    def scale_w(a, b):
        # weight of landmark-only weathering: 0 below a metres, 1 above b metres
        return float(min(1.0, max(0.0, (scale_m - a) / (b - a))))

    W_BIG = scale_w(6.0, 40.0)
    edge = g.attr('edge', (-2200, -900)); chip = g.attr('chip', (-2200, -1000)); cut = g.attr('cut', (-2200, -1100))
    tsc = 1.2                                         # metres per tile of the scanned stone: true grain size
    tsm = max(3.7, scale_m * 0.3)                     # a second, landmark-sized reading of the scan for macro form
    # macro breakup so the two samples of the scan never tile
    nz = g.n('ShaderNodeTexNoise', (-2200, 700)); nz.inputs['Scale'].default_value = 1.2 / scale_m * 3
    nz.inputs['Detail'].default_value = 4; L(pos, nz.inputs['Vector'])
    bk = g.ramp(nz.outputs['Fac'], 0.42, 0.6)
    a_c = box(_acg(cache, 'Rock041', 'Color'), False, tsc, 0.0, (-1900, 900))
    b_c = box(_acg(cache, 'Rock041', 'Color'), False, tsc * 1.73, 0.9, (-1900, 650))
    a_r = box(_acg(cache, 'Rock041', 'Roughness'), True, tsc, 0.0, (-1900, 400))
    b_r = box(_acg(cache, 'Rock041', 'Roughness'), True, tsc * 1.73, 0.9, (-1900, 150))
    a_n = box(_acg(cache, 'Rock041', 'NormalGL'), True, tsc, 0.0, (-1900, -100))
    b_n = box(_acg(cache, 'Rock041', 'NormalGL'), True, tsc * 1.73, 0.9, (-1900, -350))
    hon_c = g.mix(bk, a_c, b_c, loc=(-1600, 800)); hon_r = g.mix(bk, a_r, b_r, loc=(-1600, 300))
    hon_n = g.mix(bk, a_n, b_n, loc=(-1600, -200))
    c_c = box(_acg(cache, 'Rock035', 'Color'), False, tsc * 0.8, 0.4, (-1900, -650))
    c_r = box(_acg(cache, 'Rock035', 'Roughness'), True, tsc * 0.8, 0.4, (-1900, -900))
    c_n = box(_acg(cache, 'Rock035', 'NormalGL'), True, tsc * 0.8, 0.4, (-1900, -1150))
    # honed basalt: desaturated, cool, about 8 percent albedo, with slow cloudy variation
    hs = g.n('ShaderNodeHueSaturation', (-1400, 800)); hs.inputs['Saturation'].default_value = 0.12
    hs.inputs['Value'].default_value = 1.0; L(hon_c, hs.inputs['Color'])
    macro = g.n('ShaderNodeTexNoise', (-1400, 1100)); macro.inputs['Scale'].default_value = 2.0 / scale_m
    macro.inputs['Detail'].default_value = 6; macro.inputs['Roughness'].default_value = 0.6; L(pos, macro.inputs['Vector'])
    mv = g.ramp(macro.outputs['Fac'], 0.3, 0.7, 0.72, 1.25, (-1250, 1100))
    mac_c = box(_acg(cache, 'Rock041', 'Color'), False, tsm, 1.7, (-1900, 1150))
    mac_l = g.n('ShaderNodeRGBToBW', (-1600, 1150)); L(mac_c, mac_l.inputs['Color'])
    mac = g.ramp(mac_l.outputs['Val'], 0.1, 0.5, 1.0 - 0.3 * W_BIG, 1.0 + 0.3 * W_BIG)
    lvl = g.math('MULTIPLY', g.math('MULTIPLY', mv, mac), 0.27 * value, (-1100, 1000))
    honest = g.mix(1.0, hs.outputs['Color'], lvl, 'MULTIPLY', (-950, 800))
    honest = g.mix(1.0, honest, (0.8, 0.9, 1.06), 'MULTIPLY', (-800, 800))
    # faint quartz veins, very sparse
    wv = g.n('ShaderNodeTexWave', (-1400, 1350)); wv.wave_type = 'BANDS'; wv.bands_direction = 'DIAGONAL'
    wv.inputs['Scale'].default_value = 0.35 / scale_m * 3; wv.inputs['Distortion'].default_value = 9.0
    wv.inputs['Detail'].default_value = 6; wv.inputs['Detail Scale'].default_value = 1.6; L(pos, wv.inputs['Vector'])
    vein = g.ramp(wv.outputs['Fac'], 0.988, 0.999, 0.0, 0.3 * veins, (-1250, 1350))
    honest = g.mix(vein, honest, (0.13, 0.135, 0.14), loc=(-350, 900))
    # cut faces: layered slate, darker and rough, not polished
    chs = g.n('ShaderNodeHueSaturation', (-1400, -650)); chs.inputs['Saturation'].default_value = 0.35
    chs.inputs['Value'].default_value = 0.42; L(c_c, chs.inputs['Color'])
    cutc = g.mix(1.0, chs.outputs['Color'], (0.8, 0.86, 0.95), 'MULTIPLY', (-1200, -650))
    # fresh fractures in chips: a paler, granular grey
    chipc = g.mix(1.0, chs.outputs['Color'], (2.2, 2.25, 2.3), 'MULTIPLY', (-1200, -800))
    # arris wear: a lighter, rougher rim where hands and weather have rubbed it
    enz = g.math('ADD', g.math('MULTIPLY', noise_m(0.05, 8), 0.5), g.math('MULTIPLY', noise_m(0.07 * scale_m, 6), 0.5))
    ewear = g.math('MULTIPLY', edge, g.ramp(enz, 0.38, 0.62, 0.35, 1.0), (-1200, -1400), clamp=True)
    col = g.mix(g.math('MULTIPLY', ewear, 0.55), honest, g.mix(1.0, honest, (1.9, 1.9, 1.9), 'MULTIPLY'), loc=(-200, 700))
    col = g.mix(cut, col, cutc, loc=(-50, 700))
    col = g.mix(chip, col, chipc, loc=(100, 700))

    # roughness: honed faces 0.32 to 0.5, cut faces 0.85, chips 0.9, wear rougher
    hr = g.ramp(g.mix(bk, a_r, b_r), 0.0, 1.0, 0.30, 0.52, (-1100, 300))
    rough = g.mixf(ewear, hr, 0.62, (-200, 300))
    rough = g.mixf(cut, rough, g.ramp(c_r, 0, 1, 0.72, 0.95), (-50, 300))
    rough = g.mixf(chip, rough, 0.9, (100, 300))

    # ambient occlusion: grime in the seam and cavity, at the foot
    ao = g.n('ShaderNodeAmbientOcclusion', (-1400, -1700)); ao.samples = 8; ao.inputs['Distance'].default_value = 0.12 * scale_m
    occ = g.math('SUBTRACT', 1.0, ao.outputs['AO'], (-1200, -1700), clamp=True)
    col = g.mix(g.math('MULTIPLY', occ, 0.45), col, g.mix(1.0, col, (0.55, 0.57, 0.55), 'MULTIPLY'), loc=(250, 700))

    # rain streaks running down the faces from the top edges (stretched noise), faint even when dry
    st = g.n('ShaderNodeMapping', (-1600, -1950)); st.inputs['Scale'].default_value = (14 / scale_m, 14 / scale_m, 0.6 / scale_m)
    L(pos, st.inputs['Vector'])
    stn = g.n('ShaderNodeTexNoise', (-1400, -1950)); stn.inputs['Scale'].default_value = 1.0
    stn.inputs['Detail'].default_value = 3; L(st.outputs['Vector'], stn.inputs['Vector'])
    stf = g.n('ShaderNodeMapping'); stf.inputs['Scale'].default_value = (1 / 0.12, 1 / 0.12, 1 / 2.5); L(pos, stf.inputs['Vector'])
    stfn = g.n('ShaderNodeTexNoise'); stfn.inputs['Scale'].default_value = 1.0; stfn.inputs['Detail'].default_value = 4
    L(stf.outputs['Vector'], stfn.inputs['Vector'])
    streak = g.math('MAXIMUM', g.ramp(stn.outputs['Fac'], 0.5, 0.68), g.ramp(stfn.outputs['Fac'], 0.55, 0.72, 0.0, 0.7))
    streak = g.math('MULTIPLY', streak, face_y, (-1200, -1950))
    col = g.mix(g.math('MULTIPLY', streak, 0.22), col, g.mix(1.0, col, (0.7, 0.72, 0.74), 'MULTIPLY'), loc=(400, 700))

    # patina: a damp band wicked up from the ground, and a paler weathered skin high up where sun and rain work it
    pn = g.n('ShaderNodeTexNoise', (-1400, -2100)); pn.inputs['Scale'].default_value = 5.0 / scale_m
    pn.inputs['Detail'].default_value = 5; L(pos, pn.inputs['Vector'])
    damp = g.math('MULTIPLY', g.ramp(g.math('ADD', hz, g.math('MULTIPLY', pn.outputs['Fac'], 0.08 * scale_m)), 0.06 * scale_m, 0.16 * scale_m, 1.0, 0.0), 0.35)
    col = g.mix(damp, col, g.mix(1.0, col, (0.62, 0.64, 0.62), 'MULTIPLY'), loc=(450, 700))
    pale = g.math('MULTIPLY', g.ramp(hz, 0.45 * scale_m, 1.0 * scale_m, 0.0, 1.0), g.ramp(pn.outputs['Fac'], 0.4, 0.65, 0.2, 0.55))
    col = g.mix(pale, col, g.mix(1.0, col, (1.22, 1.2, 1.17), 'MULTIPLY'), loc=(480, 700))
    # moss from the base: height, occlusion and noise; lichen in pale rosettes a little higher
    mn = g.n('ShaderNodeTexNoise', (-1400, -2250)); mn.inputs['Scale'].default_value = 3.5 / scale_m * 2
    mn.inputs['Detail'].default_value = 7; mn.inputs['Roughness'].default_value = 0.65; L(pos, mn.inputs['Vector'])
    mh = (0.04 + 0.10 * moss) * scale_m
    hmask = g.ramp(g.math('ADD', hz, g.math('MULTIPLY', g.math('SUBTRACT', mn.outputs['Fac'], 0.5), mh * 1.6)),
                   mh * 0.2, mh, 1.0, 0.0, (-1100, -2250))
    mos = g.math('MULTIPLY', g.math('ADD', hmask, g.math('MULTIPLY', occ, 0.6 * min(1, moss * 2))), moss * 1.6, clamp=True)
    mos = g.math('MULTIPLY', mos, g.math('SUBTRACT', 1.0, g.math('MULTIPLY', face_y, 0.25)), clamp=True)
    mos = g.ramp(g.math('MULTIPLY', mos, g.ramp(mn.outputs['Fac'], 0.35, 0.6, 0.4, 1.0)), 0.35, 0.75, loc=(-800, -2250))
    mos = g.ramp(g.math('ADD', mos, g.math('MULTIPLY', g.math('SUBTRACT', noise_m(0.08, 6), 0.5), 0.6)), 0.1, 0.9)
    if not growth:
        mos = 0.0
    m_c = box(_acg(cache, 'Moss002', 'Color'), False, 0.45, 0.2, (-1900, -2500))
    m_n = box(_acg(cache, 'Moss002', 'NormalGL'), True, 0.45, 0.2, (-1900, -2750))
    mhs = g.n('ShaderNodeHueSaturation', (-1600, -2500)); mhs.inputs['Saturation'].default_value = 0.85
    mhs.inputs['Value'].default_value = 0.8; mhs.inputs['Hue'].default_value = 0.505; L(m_c, mhs.inputs['Color'])
    col = g.mix(mos, col, mhs.outputs['Color'], loc=(550, 700))
    rough = g.mixf(mos, rough, 0.75, (250, 300))
    # crusts, not dots: strongly warped cells, each its own radius, a ragged noise edge, most cells empty
    l_d, l_c = cells(0.05, 1.8)
    l_r = g.ramp(l_c, 0.0, 1.0, 0.3, 0.6)
    l_e = g.math('MULTIPLY', g.math('SUBTRACT', noise_m(0.012, 6, 0.7), 0.5), 1.1)
    ls = g.math('MULTIPLY', g.ramp(g.math('ADD', g.math('DIVIDE', l_d, l_r), l_e), 1.0, 0.75), g.ramp(l_c, 0.55, 0.7), clamp=True)
    colony = g.ramp(g.math('ADD', noise_m(0.18 * scale_m, 5), g.math('MULTIPLY', noise_m(0.4, 3), 0.15)), 0.55, 0.72)
    ls = g.math('ADD', g.math('MULTIPLY', ls, colony), g.math('MULTIPLY', colony, 0.35 * W_BIG), clamp=True)
    lh = g.ramp(hz, 0.05 * scale_m, (0.25 + 0.3 * lichen) * scale_m, 1.0, 0.0)
    lmask = g.math('MULTIPLY', g.math('MULTIPLY', ls, lh), min(1.0, lichen * 1.6), (-1100, -3000), clamp=True)
    lmask = g.math('MULTIPLY', lmask, g.math('SUBTRACT', 1.0, cut), clamp=True)
    lcol = g.mix(g.ramp(mn.outputs['Fac'], 0.3, 0.7), (0.17, 0.19, 0.16), (0.26, 0.28, 0.24), loc=(-900, -3100))
    col = g.mix(g.math('MULTIPLY', lmask, 0.6), col, lcol, loc=(700, 700))
    rough = g.mixf(lmask, rough, 0.85, (400, 300))

    # wetness: darker, glossier, a clear water coat and beads; upward faces and streaks first
    wmask = None
    if wet > 0:
        wl = g.math('ADD', g.math('MULTIPLY', streak, 0.5), g.math('MULTIPLY', up, 0.6))
        wmask = g.math('MULTIPLY', g.math('ADD', wl, 0.55), wet, (500, -2000), clamp=True)
        dk = g.mix(1.0, col, (0.34, 0.36, 0.39), 'MULTIPLY')
        dk = g.mix(cut, dk, g.mix(1.0, dk, (0.75, 0.75, 0.75), 'MULTIPLY'))
        col = g.mix(wmask, col, dk, loc=(850, 700))
        rough = g.mixf(g.math('MULTIPLY', wmask, 0.85), rough, 0.16, (550, 300))
    if not growth:
        lmask = 0.0
    if damp_foot > 0:
        # damp wicked up from the ground: a ragged upper edge with a few tongues where water runs back down
        dn = g.math('MULTIPLY', g.math('SUBTRACT', noise_m(0.05 * scale_m, 5, 0.6), 0.5), 0.07 * scale_m)
        tm_ = g.n('ShaderNodeMapping'); tm_.inputs['Scale'].default_value = (1 / (0.03 * scale_m), 1 / (0.03 * scale_m), 1 / (0.25 * scale_m))
        L(pos, tm_.inputs['Vector'])
        tn_ = g.n('ShaderNodeTexNoise'); tn_.inputs['Scale'].default_value = 1.0; tn_.inputs['Detail'].default_value = 3
        L(tm_.outputs['Vector'], tn_.inputs['Vector'])
        tongue = g.math('MULTIPLY', g.ramp(tn_.outputs['Fac'], 0.55, 0.75), 0.06 * scale_m)
        hd = g.math('SUBTRACT', g.math('SUBTRACT', hz, dn), tongue)
        top_ = 0.1 * scale_m * damp_foot
        dmp = g.ramp(hd, top_ * 0.55, top_, 1.0, 0.0)
        # the tide line: a faint paler rim where salts dry out at the top of the damp
        rim = g.math('MULTIPLY', g.ramp(hd, top_ * 0.9, top_, 0.0, 1.0), g.ramp(hd, top_, top_ * 1.12, 1.0, 0.0))
        col = g.mix(g.math('MULTIPLY', rim, 0.18), col, g.mix(1.0, col, (1.35, 1.35, 1.33), 'MULTIPLY'))
        col = g.mix(dmp, col, g.mix(1.0, col, (0.5, 0.52, 0.53), 'MULTIPLY'))
        rough = g.mixf(g.math('MULTIPLY', dmp, 0.6), rough, 0.28)
    carve_h = None
    if carve > 0:
        # hand tooling: patches (about 45 cm) each worked with broad, shallow chisel scoops at its own angle,
        # each about 4.5 cm wide and 12 to 22 cm long, of varied depth; it shows only where light rakes across
        cp = g.n('ShaderNodeSeparateXYZ'); L(pos, cp.inputs['Vector'])
        uu = g.math('ADD', cp.outputs['X'], cp.outputs['Y']); vv = cp.outputs['Z']
        cxy = g.n('ShaderNodeCombineXYZ'); L(uu, cxy.inputs['X']); L(vv, cxy.inputs['Y'])
        vo = g.n('ShaderNodeTexVoronoi'); vo.voronoi_dimensions = '2D'; vo.inputs['Scale'].default_value = 1.0 / 0.45
        vo.inputs['Randomness'].default_value = 0.9; L(cxy.outputs['Vector'], vo.inputs['Vector'])
        sp_ = g.n('ShaderNodeSeparateColor'); L(vo.outputs['Color'], sp_.inputs['Color'])
        ang = g.math('ADD', g.math('MULTIPLY', g.math('SUBTRACT', sp_.outputs['Red'], 0.5), math.radians(75)), math.radians(16))
        ca, sa = g.math('COSINE', ang), g.math('SINE', ang)
        s_ = g.math('ADD', g.math('MULTIPLY', uu, ca), g.math('MULTIPLY', vv, sa))
        t_ = g.math('SUBTRACT', g.math('MULTIPLY', vv, ca), g.math('MULTIPLY', uu, sa))
        pitch = 0.045
        sk = g.math('DIVIDE', s_, pitch); k_ = g.math('FLOOR', sk); f_ = g.math('SUBTRACT', sk, k_)
        prof = g.ramp(g.math('ABSOLUTE', g.math('SUBTRACT', g.math('MULTIPLY', f_, 2.0), 1.0)), 0.0, 1.0)
        def white(a, b, c):
            cc_ = g.n('ShaderNodeCombineXYZ')
            for i_, v_ in enumerate((a, b, c)):
                if isinstance(v_, (int, float)): cc_.inputs[i_].default_value = v_
                else: L(v_, cc_.inputs[i_])
            w_ = g.n('ShaderNodeTexWhiteNoise'); w_.noise_dimensions = '3D'; L(cc_.outputs['Vector'], w_.inputs['Vector'])
            return w_.outputs['Value']
        seg_len = g.math('ADD', 0.12, g.math('MULTIPLY', white(k_, sp_.outputs['Green'], 3.1), 0.10))
        tk = g.math('ADD', g.math('DIVIDE', t_, seg_len), white(k_, sp_.outputs['Red'], 1.7))
        sg = g.math('FLOOR', tk); gf = g.math('SUBTRACT', tk, sg)
        endf = g.math('MULTIPLY', g.ramp(gf, 0.0, 0.35), g.ramp(gf, 1.0, 0.65))
        dep = g.ramp(white(k_, sg, sp_.outputs['Blue']), 0.2, 1.0, 0.0, 1.0)
        strokes = g.math('MULTIPLY', g.math('MULTIPLY', prof, dep), endf)
        # worn faint in places, gone in the drafted margin along every arris and on the cut walls
        worn = g.ramp(noise_m(0.35, 4), 0.3, 0.62, 0.25, 1.0)
        margin = g.ramp(edge, 0.03, 0.2, 1.0, 0.0)
        mk = g.math('MULTIPLY', g.math('MULTIPLY', worn, margin), g.math('SUBTRACT', 1.0, g.math('MAXIMUM', cut, chip)), clamp=True)
        tool = g.math('MULTIPLY', strokes, mk)
        # point (pick) marks on the seam and cavity walls: small irregular pits
        q_d, q_c = cells(0.011, 0.9)
        picks = g.math('MULTIPLY', g.ramp(g.math('DIVIDE', q_d, g.ramp(q_c, 0, 1, 0.25, 0.5)), 1.0, 0.0), g.ramp(q_c, 0.3, 0.5), clamp=True)
        picks = g.math('MULTIPLY', picks, cut)
        carve_h = g.math('SUBTRACT', g.math('MULTIPLY', tool, -1.0), g.math('MULTIPLY', picks, 0.8))
        # dust and grime lodge in the scoops; the ridges stay a touch paler
        col = g.mix(g.math('MULTIPLY', tool, min(0.3, 0.12 * carve)), col, g.mix(1.0, col, (0.8, 0.81, 0.82), 'MULTIPLY'))
        rough = g.mixf(g.math('MULTIPLY', tool, 0.25), rough, 0.6)
    bsdf = g.n('ShaderNodeBsdfPrincipled', (1200, 300))
    L(col, bsdf.inputs['Base Color']); L(rough, bsdf.inputs['Roughness'])
    bsdf.inputs['Specular IOR Level'].default_value = 0.5
    if wmask is not None:
        L(g.math('MULTIPLY', wmask, 0.65), bsdf.inputs['Coat Weight'])
        bsdf.inputs['Coat Roughness'].default_value = 0.04; bsdf.inputs['Coat IOR'].default_value = 1.33

    # normals: scanned stone (gentle on honed faces, strong on cuts), drove marks, pits, moss, beads
    nm_h = g.n('ShaderNodeNormalMap', (-600, -100)); nm_h.inputs['Strength'].default_value = 0.45; L(hon_n, nm_h.inputs['Color'])
    nm_c = g.n('ShaderNodeNormalMap', (-600, -300)); nm_c.inputs['Strength'].default_value = 1.2; L(c_n, nm_c.inputs['Color'])
    nm_m = g.n('ShaderNodeNormalMap', (-600, -500)); nm_m.inputs['Strength'].default_value = 1.0; L(m_n, nm_m.inputs['Color'])
    nb = g.n('ShaderNodeMix', (-400, -200)); nb.data_type = 'VECTOR'
    L(g.math('MAXIMUM', cut, chip), nb.inputs['Factor']); L(nm_h.outputs['Normal'], nb.inputs[4]); L(nm_c.outputs['Normal'], nb.inputs[5])
    nb2 = g.n('ShaderNodeMix', (-250, -300)); nb2.data_type = 'VECTOR'
    if growth:
        L(mos, nb2.inputs['Factor'])
    else:
        nb2.inputs['Factor'].default_value = 0.0
    L(nb.outputs[1], nb2.inputs[4]); L(nm_m.outputs['Normal'], nb2.inputs[5])
    # drove marks: fine parallel grooves at the seam's 16 degrees, worn away in patches
    a16 = math.radians(16)
    dm = g.n('ShaderNodeMapping', (-1600, -3400)); dm.inputs['Rotation'].default_value = (0, a16, 0)
    L(pos, dm.inputs['Vector'])
    dw = g.n('ShaderNodeTexWave', (-1400, -3400)); dw.wave_type = 'BANDS'; dw.bands_direction = 'X'
    dw.wave_profile = 'SAW'; dw.inputs['Scale'].default_value = 1.0 / min(0.025, max(0.004, 0.0045 * scale_m))
    dw.inputs['Distortion'].default_value = 1.2; dw.inputs['Detail'].default_value = 2
    dw.inputs['Detail Scale'].default_value = 0.6
    L(dm.outputs['Vector'], dw.inputs['Vector'])
    dpn = g.n('ShaderNodeTexNoise', (-1400, -3600)); dpn.inputs['Scale'].default_value = 3.0 / scale_m * 2; L(pos, dpn.inputs['Vector'])
    dpatch = g.math('MULTIPLY', g.ramp(dpn.outputs['Fac'], 0.45, 0.62), face_y, clamp=True)
    drove = g.math('MULTIPLY', g.math('MULTIPLY', dw.outputs['Fac'], dpatch), tool_marks * (1 - 0.6 * min(1, wet)))
    # pitting: small solution pits (2 to 3 cm, real size), clustered in patches, each its own size, many cells empty
    p_d, p_c = cells(0.028, 0.9)
    p_r = g.ramp(p_c, 0.0, 1.0, 0.12, 0.35)
    pits = g.math('MULTIPLY', g.ramp(g.math('DIVIDE', p_d, p_r), 1.0, 0.0), g.ramp(p_c, 0.55, 0.7), clamp=True)
    ppatch = g.ramp(g.math('ADD', noise_m(0.12 * scale_m, 4), g.math('MULTIPLY', noise_m(0.3, 3), 0.2)), 0.52, 0.7)
    pits = g.math('MULTIPLY', pits, g.math('MULTIPLY', ppatch, erosion * 0.8))
    h = g.math('SUBTRACT', g.math('MULTIPLY', drove, 0.35), pits, (-1100, -3700))
    h = g.math('ADD', h, g.math('MULTIPLY', lmask, 0.4))
    if wet > 0:
        b_d, b_c = cells(0.007, 0.6)
        beads = g.math('MULTIPLY', g.ramp(g.math('DIVIDE', b_d, g.ramp(b_c, 0, 1, 0.2, 0.4)), 1.0, 0.0),
                       g.math('MULTIPLY', wmask, g.ramp(b_c, 0.55, 0.8)))
        h = g.math('ADD', h, g.math('MULTIPLY', beads, 0.8))
    # coarse weathering, sized to the stone: shallow hollows (irregular cells) and, on landmarks, vertical runnels
    hc = g.math('MULTIPLY', g.math('SUBTRACT', noise_m(0.05 * scale_m, 6, 0.6), 0.5), 0.4 * erosion)
    if W_BIG > 0:
        h_d, h_c = cells(0.01 * scale_m, 1.0)
        hol = g.math('MULTIPLY', g.ramp(g.math('DIVIDE', h_d, g.ramp(h_c, 0, 1, 0.2, 0.45)), 1.0, 0.0), g.ramp(h_c, 0.6, 0.75))
        hol = g.math('MULTIPLY', hol, g.ramp(noise_m(0.2 * scale_m, 3), 0.48, 0.66))
        rm_ = g.n('ShaderNodeMapping'); rm_.inputs['Scale'].default_value = (1 / (0.012 * scale_m), 1 / (0.012 * scale_m), 1 / (0.3 * scale_m))
        L(pos, rm_.inputs['Vector'])
        rn_ = g.n('ShaderNodeTexNoise'); rn_.inputs['Scale'].default_value = 1.0; rn_.inputs['Detail'].default_value = 4
        L(rm_.outputs['Vector'], rn_.inputs['Vector'])
        runnel = g.math('MULTIPLY', g.ramp(rn_.outputs['Fac'], 0.55, 0.75), face_y)
        hc = g.math('SUBTRACT', hc, g.math('MULTIPLY', g.math('ADD', hol, g.math('MULTIPLY', runnel, 0.6)), W_BIG * erosion))
        col = g.mix(g.math('MULTIPLY', runnel, 0.25 * W_BIG), col, g.mix(1.0, col, (0.72, 0.74, 0.76), 'MULTIPLY'))
        L(col, bsdf.inputs['Base Color'])
    bmc = g.n('ShaderNodeBump'); bmc.inputs['Strength'].default_value = 0.3
    bmc.inputs['Distance'].default_value = 0.002 * scale_m
    L(hc, bmc.inputs['Height']); L(nb2.outputs[1], bmc.inputs['Normal'])
    bmp = g.n('ShaderNodeBump', (-50, -400)); bmp.inputs['Strength'].default_value = 0.35
    bmp.inputs['Distance'].default_value = 0.003                  # fine detail is real size
    L(h, bmp.inputs['Height']); L(bmc.outputs['Normal'], bmp.inputs['Normal'])
    L(bmp.outputs['Normal'], bsdf.inputs['Normal'])
    if carve_h is not None:
        bct = g.n('ShaderNodeBump'); bct.inputs['Strength'].default_value = min(1.0, 0.5 * carve)
        bct.inputs['Distance'].default_value = 0.003 * carve
        L(carve_h, bct.inputs['Height']); L(bmp.outputs['Normal'], bct.inputs['Normal'])
        L(bct.outputs['Normal'], bsdf.inputs['Normal'])
    if wmask is not None:
        L(bmp.outputs['Normal'] if carve_h is None else bct.outputs['Normal'], bsdf.inputs['Coat Normal'])
    out = g.n('ShaderNodeOutputMaterial', (1500, 300)); L(bsdf.outputs['BSDF'], out.inputs['Surface'])
    m['antimony_masks'] = 'edge chip cut'
    return m


def _crystal_material(name, T, glow, depth=0.0):
    m = bpy.data.materials.new(name + '_crystal'); m.use_nodes = True
    g = _NT(m); L = g.l
    sky = sky_linear()
    b = g.n('ShaderNodeBsdfPrincipled', (0, 200))
    b.inputs['Base Color'].default_value = (1, 1, 1, 1)
    b.inputs['Transmission Weight'].default_value = 1.0
    b.inputs['IOR'].default_value = 1.544                     # quartz
    # a whisper of polish wear so highlights are not CG perfect
    tc = g.n('ShaderNodeTexCoord', (-800, 0))
    nz = g.n('ShaderNodeTexNoise', (-600, 0)); nz.inputs['Scale'].default_value = 6.0 / T; nz.inputs['Detail'].default_value = 5
    L(tc.outputs['Object'], nz.inputs['Vector'])
    L(g.ramp(nz.outputs['Fac'], 0.45, 0.75, 0.0, 0.035 * (1 - 0.7 * depth)), b.inputs['Roughness'])
    o = g.n('ShaderNodeOutputMaterial', (600, 0)); L(b.outputs['BSDF'], o.inputs['Surface'])
    # the colour is held by absorption: light crossing the crystal once lands on #94E6FF
    d = 0.8 * T                                                # a typical path through it
    D = 2.0 / d
    col = [max(0.0, 1 + math.log(max(c, 1e-4)) / (D * d)) for c in sky]
    va = g.n('ShaderNodeVolumeAbsorption', (0, -250)); va.inputs['Color'].default_value = (*col, 1)
    va.inputs['Density'].default_value = D
    vol = va.outputs['Volume']
    if depth > 0:
        # long paths lean toward cobalt: a weak second absorption that takes red first, then green
        vb = g.n('ShaderNodeVolumeAbsorption', (0, -350)); vb.inputs['Color'].default_value = (0.30, 0.55, 1.0, 1)
        vb.inputs['Density'].default_value = D * 0.45 * depth
        ab_ = g.n('ShaderNodeAddShader', (150, -300)); L(vol, ab_.inputs[0]); L(vb.outputs['Volume'], ab_.inputs[1])
        vol = ab_.outputs['Shader']
        glow = glow * (1 - 0.55 * depth)
    if glow > 0:
        ve = g.n('ShaderNodeEmission', (0, -450)); ve.inputs['Color'].default_value = (*sky, 1)
        ve.inputs['Strength'].default_value = glow * 2.5 / d
        ad = g.n('ShaderNodeAddShader', (250, -300)); L(vol, ad.inputs[0]); L(ve.outputs['Emission'], ad.inputs[1])
        vol = ad.outputs['Shader']
    L(vol, o.inputs['Volume'])
    try:
        m.cycles.homogeneous_volume = True
    except Exception:
        pass
    try:
        m.cycles.volume_sampling = 'EQUIANGULAR' if glow > 0 else 'DISTANCE'
    except Exception:
        pass
    return m


def _veil_material(name):
    m = bpy.data.materials.new(name + '_veil'); m.use_nodes = True
    g = _NT(m); L = g.l
    tr = g.n('ShaderNodeBsdfTransparent', (0, 100))
    gl = g.n('ShaderNodeBsdfGlossy', (0, -100)); gl.inputs['Roughness'].default_value = 0.12
    gl.inputs['Color'].default_value = (*[0.6 + 0.4 * c for c in sky_linear()], 1)
    fr = g.n('ShaderNodeLayerWeight', (-200, 0)); fr.inputs['Blend'].default_value = 0.35
    f = g.math('MULTIPLY', fr.outputs['Fresnel'], 0.35)
    ms = g.n('ShaderNodeMixShader', (200, 0)); L(f, ms.inputs['Fac'])
    L(tr.outputs['BSDF'], ms.inputs[1]); L(gl.outputs['BSDF'], ms.inputs[2])
    o = g.n('ShaderNodeOutputMaterial', (400, 0)); L(ms.outputs['Shader'], o.inputs['Surface'])
    return m


def mark_caustic_lights(lights):
    for l in lights:
        l.data.cycles.is_caustics_light = True


# ------------------------------------------------------------------ the ground it sits in
def _local(parts, x, y):
    M = parts['info']['matrix'].inverted()
    return M @ Vector((x, y, parts['info']['matrix'].translation.z))


def _footprint_dist(parts, X, Y):
    """distance (m) on the ground from the stone's footprint rectangle, numpy arrays of world x, y"""
    inf = parts['info']; M = inf['matrix']
    c = M.translation; yaw = M.to_euler().z
    ca, sa = math.cos(-yaw), math.sin(-yaw)
    lx = (X - c.x) * ca - (Y - c.y) * sa; ly = (X - c.x) * sa + (Y - c.y) * ca
    qx = np.abs(lx) - inf['half_w'] * 0.92; qy = np.abs(ly) - inf['half_t']
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0), lx, ly


def ground_height(parts, X, Y, mound=0.012):
    inf = parts['info']; s = inf['scale']
    d, lx, ly = _footprint_dist(parts, np.asarray(X, float), np.asarray(Y, float))
    w = 0.10 * s
    rise = mound * s * np.exp(-(np.maximum(d, 0) / w) ** 2)
    return inf['matrix'].translation.z + rise


def make_ground(collection, parts, radius=30.0, mound=0.012, wetness=None, cache_dir=None, res=None, name='ground'):
    inf = parts['info']; s = inf['scale']; cache = cache_dir or inf['cache_dir']
    wet = inf['wetness'] if wetness is None else wetness
    c = inf['matrix'].translation
    # a polar-ish grid: fine near the stone, coarse far away
    nr = res or 140; na = 160
    rr = np.concatenate([[0], (np.linspace(0, 1, nr) ** 2.2) * radius + 1e-3])
    verts = [(c.x, c.y, 0.0)]
    for r in rr[1:]:
        for j in range(na):
            a = 2 * math.pi * j / na
            verts.append((c.x + r * math.cos(a), c.y + r * math.sin(a), 0.0))
    V = np.array(verts)
    V[:, 2] = ground_height(parts, V[:, 0], V[:, 1], mound)
    # a little natural unevenness that dies away at the stone
    d, _, _ = _footprint_dist(parts, V[:, 0], V[:, 1])
    rnd = np.array([noise.fractal(Vector((x * 0.6 / s, y * 0.6 / s, 0.3)), 1.0, 2.0, 3) for x, y in V[:, :2]])
    V[:, 2] += rnd * 0.012 * s * np.clip(d / (0.4 * s), 0, 1)
    faces = []
    for j in range(na):
        faces.append((0, 1 + j, 1 + (j + 1) % na))
    for i in range(1, len(rr) - 1):
        b0 = 1 + (i - 1) * na; b1 = 1 + i * na
        for j in range(na):
            k = (j + 1) % na
            faces.append((b0 + j, b1 + j, b1 + k, b0 + k))
    me = bpy.data.meshes.new(name); me.from_pydata(V.tolist(), [], faces)
    for p in me.polygons:
        p.use_smooth = True
    at = me.attributes.new('stone_d', 'FLOAT', 'POINT'); at.data.foreach_set('value', d.astype(np.float32))
    ob = bpy.data.objects.new(name, me); collection.objects.link(ob)
    ob.cycles.is_caustics_receiver = True
    ob.data.materials.append(_ground_material(name, s, cache, wet))
    return ob


def _ground_material(name, s, cache, wet):
    m = bpy.data.materials.new(name + '_soil'); m.use_nodes = True
    g = _NT(m); L = g.l
    geo = g.n('ShaderNodeNewGeometry', (-1800, 0)); pos = geo.outputs['Position']

    def tex(aid, kind, nc, sc_, loc):
        mp = g.n('ShaderNodeMapping', (loc[0] - 200, loc[1])); mp.inputs['Scale'].default_value = (1 / sc_,) * 3
        L(pos, mp.inputs['Vector'])
        t = g.n('ShaderNodeTexImage', loc); t.image = _img(_acg(cache, aid, kind), nc); t.projection = 'BOX'
        L(mp.outputs['Vector'], t.inputs['Vector'])
        return t.outputs['Color']
    sd = g.attr('stone_d', (-1600, 400))
    nz = g.n('ShaderNodeTexNoise', (-1600, 600)); nz.inputs['Scale'].default_value = 1.5 / max(1, s / 3); nz.inputs['Detail'].default_value = 6
    L(pos, nz.inputs['Vector'])
    dd = g.math('ADD', sd, g.math('MULTIPLY', g.math('SUBTRACT', nz.outputs['Fac'], 0.5), 0.25 * s))
    soil = g.ramp(dd, 0.02 * s, 0.22 * s, 1.0, 0.0, (-1300, 400))
    s_c = tex('Ground037', 'Color', False, 1.4, (-1300, 100)); s_n = tex('Ground037', 'NormalGL', True, 1.4, (-1300, -150))
    g_c = tex('Grass004', 'Color', False, 1.8, (-1300, -400)); g_n = tex('Grass004', 'NormalGL', True, 1.8, (-1300, -650))
    s_r = tex('Ground037', 'Roughness', True, 1.4, (-1300, -900))
    gcol = g.mix(1.0, g_c, (0.85, 0.9, 0.7), 'MULTIPLY')
    col = g.mix(soil, gcol, s_c, loc=(-900, 200))
    col = g.mix(1.0, col, (0.85, 0.85, 0.85), 'MULTIPLY')
    rough = g.mixf(soil, 0.8, g.ramp(s_r, 0, 1, 0.6, 0.95))
    if wet > 0:
        col = g.mix(wet * 0.9, col, g.mix(1.0, col, (0.5, 0.52, 0.5), 'MULTIPLY'))
        rough = g.mixf(wet * 0.7, rough, 0.22)
    nm = g.n('ShaderNodeMix', (-700, -300)); nm.data_type = 'VECTOR'; L(soil, nm.inputs['Factor'])
    L(g_n, nm.inputs[4]); L(s_n, nm.inputs[5])
    nmap = g.n('ShaderNodeNormalMap', (-500, -300)); nmap.inputs['Strength'].default_value = 0.8; L(nm.outputs[1], nmap.inputs['Color'])
    b = g.n('ShaderNodeBsdfPrincipled', (0, 0)); L(col, b.inputs['Base Color']); L(rough, b.inputs['Roughness'])
    L(nmap.outputs['Normal'], b.inputs['Normal'])
    o = g.n('ShaderNodeOutputMaterial', (300, 0)); L(b.outputs['BSDF'], o.inputs['Surface'])
    return m


def _grass_material(cache, wet=0.0):
    m = bpy.data.materials.get('antimony_grass')
    if m:
        return m
    m = bpy.data.materials.new('antimony_grass'); m.use_nodes = True
    g = _NT(m); L = g.l
    tdir = os.path.join(cache, 'polyhaven', 'grass_medium_01', 'textures')
    uv = g.n('ShaderNodeUVMap', (-1200, 0)); uv.uv_map = 'UVMap'
    t = g.n('ShaderNodeTexImage', (-1000, 100)); t.image = _img(os.path.join(tdir, 'grass_medium_01_diff_2k.jpg'))
    L(uv.outputs['UV'], t.inputs['Vector'])
    td = g.n('ShaderNodeTexImage', (-1000, -150)); td.image = _img(os.path.join(tdir, 'grass_medium_01_dry_diff_2k.png'))
    L(uv.outputs['UV'], td.inputs['Vector'])
    ta = g.n('ShaderNodeTexImage', (-1000, -400)); ta.image = _img(os.path.join(tdir, 'grass_medium_01_alpha_2k.png'), True)
    L(uv.outputs['UV'], ta.inputs['Vector'])
    oi = g.n('ShaderNodeObjectInfo', (-1200, -600))
    dry = g.ramp(oi.outputs['Random'], 0.78, 0.92)
    col = g.mix(dry, t.outputs['Color'], td.outputs['Color'])
    hs = g.n('ShaderNodeHueSaturation', (-600, 100)); L(col, hs.inputs['Color'])
    L(g.ramp(oi.outputs['Random'], 0, 1, 0.48, 0.52), hs.inputs['Hue'])
    hs.inputs['Value'].default_value = 0.95 if wet <= 0 else 0.8
    p = g.n('ShaderNodeBsdfPrincipled', (-200, 200)); L(hs.outputs['Color'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.45 - 0.25 * wet
    tb = g.mix(1.0, hs.outputs['Color'], (1.3, 1.5, 0.7), 'MULTIPLY')
    tl = g.n('ShaderNodeBsdfTranslucent', (-200, -100)); L(tb, tl.inputs['Color'])
    ms = g.n('ShaderNodeMixShader', (50, 0)); ms.inputs['Fac'].default_value = 0.4
    L(p.outputs['BSDF'], ms.inputs[1]); L(tl.outputs['BSDF'], ms.inputs[2])
    tp = g.n('ShaderNodeBsdfTransparent', (50, -250))
    ma = g.n('ShaderNodeMixShader', (250, 0)); L(ta.outputs['Color'], ma.inputs['Fac'])
    L(tp.outputs['BSDF'], ma.inputs[1]); L(ms.outputs['Shader'], ma.inputs[2])
    o = g.n('ShaderNodeOutputMaterial', (450, 0)); L(ma.outputs['Shader'], o.inputs['Surface'])
    return m


def scatter_grass(collection, parts, radius=20.0, count=20000, ground=None, cache_dir=None, front_clear=True,
                  seed=3, scale=1.0, inner=None, mound=0.012, wedge=None, name='grass'):
    inf = parts['info']; s = inf['scale']; cache = cache_dir or inf['cache_dir']
    lib = bpy.data.collections.get('antimony_grass_lib')
    if lib is None:
        lib = bpy.data.collections.new('antimony_grass_lib'); bpy.context.scene.collection.children.link(lib)
        path = os.path.join(cache, 'polyhaven', 'grass_medium_01', 'grass_medium_01_2k.blend')
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.objects = sorted(n for n in src.objects if n.endswith('_LOD1'))
        gm = _grass_material(cache, inf['wetness'])
        for ob in dst.objects:
            ob.location = (0, 0, 0); ob.rotation_euler = (0, 0, 0)
            ob.data.materials.clear(); ob.data.materials.append(gm)
            if ob.data.uv_layers and ob.data.uv_layers[0].name != 'UVMap':
                ob.data.uv_layers[0].name = 'UVMap'
            lib.objects.link(ob)
        lib.hide_render = True
        bpy.context.view_layer.layer_collection.children[lib.name].exclude = False
    kids = sorted(lib.objects, key=lambda o: o.name)
    names = [o.name for o in kids]
    tall = np.array([('tall' in n or 'mid' in n) for n in names])
    rng = np.random.default_rng(seed)
    c = inf['matrix'].translation
    r0 = inner if inner is not None else 0.0
    a = rng.uniform(0, 2 * math.pi, count); r = np.sqrt(rng.uniform(r0 ** 2, radius ** 2, count))
    X = c.x + r * np.cos(a); Y = c.y + r * np.sin(a)
    if wedge:
        # most of the clumps in the camera's view: (cam x, cam y, yaw of the view, half angle)
        wx, wy, wyaw, wha = wedge
        nw = int(count * 0.8)
        aa = wyaw + rng.uniform(-wha, wha, nw)
        rr = radius * rng.uniform(0, 1, nw) ** 0.75 + 0.5
        X[:nw] = wx + rr * np.cos(aa); Y[:nw] = wy + rr * np.sin(aa)
    # crowd some toward the stone: a sixth of the clumps within a tile width of its foot
    nn = count // 6
    an = rng.uniform(0, 2 * math.pi, nn); rn = np.sqrt(rng.uniform(0, (0.9 * s) ** 2, nn)) + inf['half_t'] * 0.5
    X[-nn:] = c.x + rn * np.cos(an); Y[-nn:] = c.y + rn * np.sin(an)
    d, lx, ly = _footprint_dist(parts, X, Y)
    keep = d > 0.01 * s
    X, Y, d, lx, ly = X[keep], Y[keep], d[keep], lx[keep], ly[keep]
    m = len(X)
    pick = rng.integers(0, len(kids), m)
    sc_ = rng.uniform(0.8, 1.3, m) * scale
    if wedge:
        # far clumps larger, so the field fills to the haze without millions of them
        sc_ *= 1.0 + np.clip((np.hypot(X - wedge[0], Y - wedge[1]) - 6.0) / 12.0, 0, 1.6)
    if front_clear:
        # in front of the mark (local -Y) keep only the short clumps, small, so the whole mark shows
        front = (ly < 0) & (np.abs(lx) < inf['half_w'] * 1.15 - ly * 0.12) & (-ly < 2.5 * s)
        short_ids = np.where(~tall)[0]
        pick[front] = rng.choice(short_ids, front.sum())
        sc_[front] *= np.clip(0.35 + 0.65 * (-ly[front]) / (2.5 * s), 0.35, 1.0)
    # hug the foot: a little smaller right against the stone, as if trodden and sheltered
    sc_ *= np.clip(0.55 + d / (0.25 * s), 0.55, 1.0)
    Z = ground_height(parts, X, Y, mound) - 0.01
    me = bpy.data.meshes.new(name); me.vertices.add(m)
    me.vertices.foreach_set('co', np.stack([X, Y, Z], 1).astype(np.float32).ravel())
    rot = np.zeros((m, 3), np.float32); rot[:, 2] = rng.uniform(0, 2 * math.pi, m)
    rot[:, 0] = rng.normal(0, 0.05, m); rot[:, 1] = rng.normal(0, 0.05, m)
    scl = np.stack([sc_, sc_, sc_ * rng.uniform(0.85, 1.25, m)], 1).astype(np.float32)
    for an, data, tp in (('rot', rot, 'FLOAT_VECTOR'), ('scl', scl, 'FLOAT_VECTOR'), ('pick', pick.astype(np.int32), 'INT')):
        at = me.attributes.new(an, tp, 'POINT')
        at.data.foreach_set('vector' if tp == 'FLOAT_VECTOR' else 'value', data.ravel())
    ob = bpy.data.objects.new(name, me); collection.objects.link(ob)
    ng = bpy.data.node_groups.new(name + '_gn', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    gi = ng.nodes.new('NodeGroupInput'); go = ng.nodes.new('NodeGroupOutput')
    m2p = ng.nodes.new('GeometryNodeMeshToPoints')
    ci = ng.nodes.new('GeometryNodeCollectionInfo'); ci.inputs['Collection'].default_value = lib
    ci.inputs['Separate Children'].default_value = True; ci.inputs['Reset Children'].default_value = True
    iop = ng.nodes.new('GeometryNodeInstanceOnPoints'); iop.inputs['Pick Instance'].default_value = True
    Lk = ng.links
    na = {}
    for an, dt in (('rot', 'FLOAT_VECTOR'), ('scl', 'FLOAT_VECTOR'), ('pick', 'INT')):
        x = ng.nodes.new('GeometryNodeInputNamedAttribute'); x.data_type = dt; x.inputs['Name'].default_value = an; na[an] = x
    Lk.new(gi.outputs[0], m2p.inputs['Mesh']); Lk.new(m2p.outputs['Points'], iop.inputs['Points'])
    Lk.new(ci.outputs[0], iop.inputs['Instance'])
    Lk.new(na['pick'].outputs['Attribute'], iop.inputs['Instance Index'])
    Lk.new(na['rot'].outputs['Attribute'], iop.inputs['Rotation'])
    Lk.new(na['scl'].outputs['Attribute'], iop.inputs['Scale'])
    Lk.new(iop.outputs['Instances'], go.inputs[0])
    md = ob.modifiers.new('scatter', 'NODES'); md.node_group = ng
    return ob
