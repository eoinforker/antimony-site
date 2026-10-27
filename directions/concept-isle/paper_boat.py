# Crystal Isle: the paper boat, rendered alone with the scene's own camera and light, on a
# transparent film, so isle_compose.py can set it on the water (with its reflection) exactly
# where it floats: about 58 m out, just left of the mark's reflection, near the rocks and grass.
#
#   flock <lock> nice -n 5 blender -b -P paper_boat.py -- --out boat.png --w 2560 --h 1440 --samples 160
# Prints the boat's bounding box in image pixels (for the page's button).

import bpy, bmesh, math, sys
from mathutils import Vector

def arg(name, default):
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return a[a.index(name) + 1] if name in a else default

OUT = arg('--out', 'boat.png'); W, H = int(arg('--w', '2560')), int(arg('--h', '1440'))
SAMPLES = int(arg('--samples', '160'))
bpy.ops.wm.read_factory_settings(use_empty=True)
SC = bpy.context.scene

BOAT = Vector((-8.0, -258.0, 0.0))
L, BEAM, HULL, PEAK = 2.0, 0.72, 0.42, 0.95       # a large paper boat: 2 m long

# ---------------------------------------------------------------- the boat: the classic fold
bm = bmesh.new()
def v(x, y, z): return bm.verts.new((x, y, z))
k0, k1 = v(-L * 0.36, 0, 0.0), v(L * 0.36, 0, 0.0)                 # the keel
r = [v(-L / 2, -BEAM / 2, HULL), v(L / 2, -BEAM / 2, HULL), v(L / 2, BEAM / 2, HULL), v(-L / 2, BEAM / 2, HULL)]
bm.faces.new([k0, k1, r[1], r[0]])                                  # near side
bm.faces.new([k1, k0, r[3], r[2]])                                  # far side
bm.faces.new([k0, r[0], r[3]])                                      # stern
bm.faces.new([k1, r[2], r[1]])                                      # bow
# the sail: the folded peak, two thin leaves rising from the middle of the rim
for s in (-1, 1):
    a, b, c = v(-L * 0.30, s * 0.035, HULL), v(L * 0.30, s * 0.035, HULL), v(0.0, s * 0.012, HULL + PEAK)
    bm.faces.new([a, b, c])
    # the pockets either side of the sail
    d, e = v(-L * 0.30, s * BEAM / 2 * 0.95, HULL), v(L * 0.30, s * BEAM / 2 * 0.95, HULL)
    f = v(0.0, s * BEAM * 0.18, HULL + PEAK * 0.42)
    bm.faces.new([d, e, f])
me = bpy.data.meshes.new('boat'); bm.to_mesh(me); bm.free()
boat = bpy.data.objects.new('boat', me); SC.collection.objects.link(boat)
boat.location = BOAT + Vector((0, 0, -0.05)); boat.rotation_euler = (math.radians(3), math.radians(-2), math.radians(28))
sol = boat.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.004
bv = boat.modifiers.new('bev', 'BEVEL'); bv.width = 0.006; bv.segments = 2

m = bpy.data.materials.new('paper'); m.use_nodes = True
N, Lk = m.node_tree.nodes, m.node_tree.links
bs = N['Principled BSDF']
bs.inputs['Base Color'].default_value = (0.86, 0.82, 0.74, 1)
bs.inputs['Roughness'].default_value = 0.62
bs.inputs['Subsurface Weight'].default_value = 0.25
tr = N.new('ShaderNodeBsdfTranslucent'); tr.inputs['Color'].default_value = (1.0, 0.86, 0.72, 1)
mx = N.new('ShaderNodeMixShader'); mx.inputs[0].default_value = 0.35
Lk.new(bs.outputs[0], mx.inputs[1]); Lk.new(tr.outputs[0], mx.inputs[2])
nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 60; nz.inputs['Detail'].default_value = 8
bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.08
Lk.new(nz.outputs['Fac'], bump.inputs['Height']); Lk.new(bump.outputs[0], bs.inputs['Normal'])
Lk.new(mx.outputs[0], N['Material Output'].inputs['Surface'])
me.materials.append(m)

# ---------------------------------------------------------------- the scene's light
sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 22.0; sun.angle = math.radians(1.0); sun.color = (1.0, 0.70, 0.62)
so = bpy.data.objects.new('sun', sun); SC.collection.objects.link(so)
el, az = math.radians(2.6), math.radians(11.0)
to_sun = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
so.rotation_euler = to_sun.to_track_quat('Z', 'Y').to_euler()
# the crystal's light, far off over the island
pl = bpy.data.lights.new('crystal', 'POINT'); pl.energy = 9.0e4; pl.color = (0.30, 0.74, 1.0); pl.shadow_soft_size = 3
po = bpy.data.objects.new('crystal', pl); SC.collection.objects.link(po); po.location = (0, 2, 93)
world = bpy.data.worlds.new('w'); SC.world = world; world.use_nodes = True
WN, WL = world.node_tree.nodes, world.node_tree.links
tc = WN.new('ShaderNodeTexCoord'); sp = WN.new('ShaderNodeSeparateXYZ'); WL.new(tc.outputs['Generated'], sp.inputs[0])
gr = WN.new('ShaderNodeValToRGB')
gr.color_ramp.elements[0].position = 0.0; gr.color_ramp.elements[0].color = (0.95, 0.56, 0.80, 1)
gr.color_ramp.elements[1].position = 0.55; gr.color_ramp.elements[1].color = (0.13, 0.09, 0.27, 1)
WL.new(sp.outputs['Z'], gr.inputs[0]); WL.new(gr.outputs[0], WN['Background'].inputs['Color'])
WN['Background'].inputs['Strength'].default_value = 0.55
# the water under it, as a shadow catcher (the reflection is laid in by the composer)
bpy.ops.mesh.primitive_plane_add(size=40, location=BOAT)
wp = bpy.context.active_object; wp.is_shadow_catcher = True

# ---------------------------------------------------------------- camera: exactly the scene's
cam = bpy.data.cameras.new('cam'); cam.lens = 28; cam.sensor_width = 36
cam.dof.use_dof = True; cam.dof.focus_distance = 326; cam.dof.aperture_fstop = 8.0
co = bpy.data.objects.new('cam', cam); SC.collection.objects.link(co); SC.camera = co
co.location = (0, -320, 6.0)
tgt = Vector((0, 0, 6.0 + 326 * math.tan(math.radians(3.3))))
co.rotation_euler = (tgt - co.location).to_track_quat('-Z', 'Y').to_euler()

# the boat's box on screen, then render only that region
from bpy_extras.object_utils import world_to_camera_view
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get(); ev = boat.evaluated_get(dg)
pts = [world_to_camera_view(SC, co, ev.matrix_world @ vv.co) for vv in ev.data.vertices]
x0, x1 = min(p.x for p in pts), max(p.x for p in pts); y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
print('BOATBOX', round(x0 * W), round((1 - y1) * H), round(x1 * W), round((1 - y0) * H))
pad = 0.02
SC.render.use_border = True; SC.render.use_crop_to_border = False
SC.render.border_min_x, SC.render.border_max_x = max(0, x0 - pad), min(1, x1 + pad)
SC.render.border_min_y, SC.render.border_max_y = max(0, y0 - pad * 2), min(1, y1 + pad)

SC.render.engine = 'CYCLES'; c = SC.cycles
c.device = 'CPU'; c.samples = SAMPLES; c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'
c.max_bounces = 6
SC.render.film_transparent = True
SC.render.threads_mode = 'FIXED'; SC.render.threads = 4
SC.render.resolution_x, SC.render.resolution_y = W, H; SC.render.resolution_percentage = 100
SC.render.image_settings.file_format = 'PNG'; SC.render.image_settings.color_mode = 'RGBA'
vs = SC.view_settings; vs.view_transform = 'AgX'; vs.look = 'AgX - Base Contrast'; vs.exposure = -0.5
SC.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('wrote', OUT)
