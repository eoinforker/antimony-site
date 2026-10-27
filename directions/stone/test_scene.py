# Test stills for stone.py (three framings, no turntable).
# Run under the shared lock:
#   flock <scratchpad>/blender.lock nice -n 5 blender -b -P test_scene.py -- --variant a --out test-a.png
#   --variant a  golden-hour meadow close-up (Poly Haven qwantani_sunset_puresky, grass_medium_01)
#   --variant b  overcast, wet (kloofendal_overcast_puresky), the stone soaked and darkened
#   --variant c  monumental, 20 m, seen from below in haze (industrial_sunset_02_puresky)
#   --res 1280x800  --samples 128  --time 300 (seconds of sampling at most)  --dry 1 (build only)
import bpy, sys, os, math, time
import numpy as np
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stone

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d):
    k = '--' + k
    return type(d)(argv[argv.index(k) + 1]) if k in argv else d

V = arg('variant', 'a'); OUT = arg('out', os.path.join(HERE, f'test-{V}.png'))
W, H = (int(x) for x in arg('res', '1280x800').split('x'))
SAMPLES = arg('samples', 128); TLIM = arg('time', 300.0)
CACHE = stone.DEFAULT_CACHE
PH = os.path.join(CACHE, 'polyhaven')
DETAIL = arg('detail', 380)
GRASS = arg('grass', 1.0)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = W, H; sc.render.resolution_percentage = 100
sc.render.engine = 'CYCLES'
cy = sc.cycles
cy.device = 'CPU'; cy.samples = SAMPLES; cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.02
cy.time_limit = TLIM; cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
cy.max_bounces = 10; cy.diffuse_bounces = 2; cy.glossy_bounces = 4; cy.transmission_bounces = 10
cy.transparent_max_bounces = 12; cy.volume_bounces = 0
cy.caustics_refractive = True; cy.caustics_reflective = True; cy.blur_glossy = 0.5
cy.use_light_tree = True
sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
sc.view_settings.view_transform = 'AgX'
try:
    sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass
sc.render.film_transparent = False
coll = sc.collection

# ---------------------------------------------------------------- per variant
if V == 'a':
    HDR = os.path.join(PH, 'qwantani_sunset_puresky', 'qwantani_sunset_puresky_2k.hdr')
    P = dict(scale_m=2.2, location=(0, 0, 0), rotation=(0.012, -0.008, -0.15), wetness=0.0, moss=0.55, glow=0.12)
    SUN = Vector((-0.92, -0.33, 0.14)).normalized(); SUN_STR = 8.0; SUN_COL = (1.0, 0.6, 0.32)
    CAM = (1.3, -8.4, 1.15); TGT = (0.1, 0.0, 1.12); LENS = 50; FSTOP = 2.8
    WORLD_STR = 0.6; EXPO = 0.2; MIST = (8, 260, 0.35, (1.0, 0.8, 0.62))
    GR = dict(radius=40, count=int(60000 * GRASS))
elif V == 'b':
    HDR = os.path.join(PH, 'kloofendal_overcast_puresky', 'kloofendal_overcast_puresky_2k.hdr')
    P = dict(scale_m=2.2, location=(0, 0, 0), rotation=(-0.01, 0.012, 0.26), wetness=1.0, moss=0.8, glow=0.25)
    SUN = Vector((-0.4, 0.5, 0.75)).normalized(); SUN_STR = 0.0; SUN_COL = (0.9, 0.95, 1.0)
    CAM = (-2.2, -7.9, 0.95); TGT = (-0.1, 0.0, 1.1); LENS = 50; FSTOP = 3.5
    WORLD_STR = 1.1; EXPO = 0.2; MIST = (6, 160, 0.45, (0.62, 0.68, 0.74))
    GR = dict(radius=40, count=int(60000 * GRASS))
else:
    HDR = os.path.join(PH, 'industrial_sunset_02_puresky', 'industrial_sunset_02_puresky_2k.hdr')
    P = dict(scale_m=20.0, location=(0, 0, 0), rotation=(0.02, 0.0, -0.12), wetness=0.0, moss=0.45, glow=0.2)
    SUN = Vector((-0.12, 0.96, 0.25)).normalized(); SUN_STR = 6.0; SUN_COL = (1.0, 0.78, 0.55)
    CAM = (7.0, -38.0, 0.7); TGT = (0.0, 0.0, 12.0); LENS = 24; FSTOP = 8.0
    WORLD_STR = 0.8; EXPO = -0.2; MIST = (30, 900, 0.12, (0.86, 0.88, 0.92))
    GR = dict(radius=140, count=int(60000 * GRASS), scale=1.5, front_clear=False)

SCALE = arg('scale', 0.0)
if SCALE > 0:
    # try another size with the same framing: camera, target and grass scale with it
    k = SCALE / P['scale_m']; P['scale_m'] = SCALE
    CAM = tuple(c * k for c in CAM); TGT = tuple(c * k for c in TGT)
    MIST = (MIST[0] * k, MIST[1] * k, MIST[2], MIST[3])
t0 = time.time()
parts = stone.build_stone(coll, cache_dir=CACHE, detail=DETAIL, **P)
print('STONE_BUILD', round(time.time() - t0, 1), 's', parts['info']['faces'], 'faces')
gnd = stone.make_ground(coll, parts, radius=(600 if V == 'c' else 300))
if GRASS > 0:
    cyaw = math.atan2(TGT[1] - CAM[1], TGT[0] - CAM[0])
    stone.scatter_grass(coll, parts, ground=gnd, wedge=(CAM[0], CAM[1], cyaw, math.radians(48 if V == 'c' else 26)), **GR)
print('SCENE_BUILD', round(time.time() - t0, 1), 's')

# ---------------------------------------------------------------- world: the HDRI turned so its sun agrees with ours, sun disc clamped
img = bpy.data.images.load(HDR)
w_, h_ = img.size
px = np.empty(w_ * h_ * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(h_, w_, 4)
lum = px[..., :3] @ np.array([0.2126, 0.7152, 0.0722], np.float32)
r_, c_ = np.unravel_index(np.argmax(lum[h_ // 2:]), lum[h_ // 2:].shape); r_ += h_ // 2
u = (c_ + 0.5) / w_
az0 = (0.5 - u) * 2 * math.pi          # Cycles equirect: u = 0.5 - atan2(y, x) / 2 pi
cap = float(np.percentile(lum[h_ // 2:], 99.5)) * 1.5
az_want = math.atan2(SUN.y, SUN.x)
wr = az0 - az_want                       # the mapping turns the lookup, so the sky turns the other way
wd = bpy.data.worlds.new('w'); sc.world = wd; wd.use_nodes = True
nt = wd.node_tree; nt.nodes.clear()
tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, wr)
env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = img
mn = nt.nodes.new('ShaderNodeVectorMath'); mn.operation = 'MINIMUM'; mn.inputs[1].default_value = (cap, cap, cap)
bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = arg("wstr", WORLD_STR)
wo = nt.nodes.new('ShaderNodeOutputWorld')
L = nt.links.new
L(tc.outputs['Generated'], mp.inputs['Vector']); L(mp.outputs['Vector'], env.inputs['Vector'])
L(env.outputs['Color'], mn.inputs[0]); L(mn.outputs['Vector'], bg.inputs['Color']); L(bg.outputs['Background'], wo.inputs['Surface'])
print('HDRI sun az', round(math.degrees(az0)), 'elev row', r_, 'cap', round(cap, 2))

sun = None
if SUN_STR > 0:
    ld = bpy.data.lights.new('sun', 'SUN'); ld.energy = SUN_STR; ld.color = SUN_COL; ld.angle = math.radians(0.6)
    sun = bpy.data.objects.new('sun', ld); coll.objects.link(sun)
    sun.rotation_euler = SUN.to_track_quat('Z', 'Y').to_euler()
    stone.mark_caustic_lights([sun])

if V == 'c':
    # haze with shape: a large homogeneous volume around the scene
    bpy.ops.mesh.primitive_cube_add(size=1); hz = bpy.context.object; hz.name = 'haze'
    hz.scale = (700, 700, 160); hz.location = (0, 120, 70)
    hm = bpy.data.materials.new('haze'); hm.use_nodes = True; hnt = hm.node_tree; hnt.nodes.clear()
    pv = hnt.nodes.new('ShaderNodeVolumePrincipled'); pv.inputs['Density'].default_value = arg('haze', 0.0035)
    pv.inputs['Color'].default_value = (0.88, 0.93, 1.0, 1); pv.inputs['Anisotropy'].default_value = 0.55
    ho = hnt.nodes.new('ShaderNodeOutputMaterial'); hnt.links.new(pv.outputs['Volume'], ho.inputs['Volume'])
    hz.data.materials.append(hm); hz.visible_shadow = False
    hm.cycles.homogeneous_volume = True
    cy.volume_bounces = 0

# ---------------------------------------------------------------- camera
cd = bpy.data.cameras.new('cam'); cd.lens = LENS; cd.sensor_width = 36
cam = bpy.data.objects.new('cam', cd); coll.objects.link(cam); sc.camera = cam
cam.location = CAM
cam.rotation_euler = (Vector(TGT) - Vector(CAM)).to_track_quat('-Z', 'Y').to_euler()
cd.dof.use_dof = True; cd.dof.aperture_fstop = FSTOP
cd.dof.focus_distance = (Vector(TGT) - Vector(CAM)).length
cd.clip_end = 3000
sc.view_settings.exposure = EXPO

# ---------------------------------------------------------------- compositor: aerial haze from the mist pass, soft bloom, a gentle vignette
vl = sc.view_layers[0]; vl.use_pass_mist = True
wd.mist_settings.start = MIST[0]; wd.mist_settings.depth = MIST[1]; wd.mist_settings.falloff = 'QUADRATIC'
sc.use_nodes = True; ct = sc.node_tree; ct.nodes.clear()
rl = ct.nodes.new('CompositorNodeRLayers'); comp = ct.nodes.new('CompositorNodeComposite')
mm = ct.nodes.new('CompositorNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = MIST[2]
ct.links.new(rl.outputs['Mist'], mm.inputs[0])
mx = ct.nodes.new('CompositorNodeMixRGB'); mx.inputs[2].default_value = (*MIST[3], 1)
ct.links.new(mm.outputs[0], mx.inputs[0]); ct.links.new(rl.outputs['Image'], mx.inputs[1])
gl = ct.nodes.new('CompositorNodeGlare'); gl.glare_type = 'BLOOM'; gl.quality = 'HIGH'
gl.inputs['Threshold'].default_value = 1.0; gl.inputs['Strength'].default_value = 0.18; gl.inputs['Size'].default_value = 0.8
ct.links.new(mx.outputs[0], gl.inputs['Image'])
ld_ = ct.nodes.new('CompositorNodeLensdist'); ld_.inputs['Dispersion'].default_value = 0.008
ct.links.new(gl.outputs['Image'], ld_.inputs['Image'])
el = ct.nodes.new('CompositorNodeEllipseMask'); el.width = 1.25; el.height = 1.25
bl = ct.nodes.new('CompositorNodeBlur'); bl.size_x = bl.size_y = int(W * 0.25); bl.filter_type = 'GAUSS'
ct.links.new(el.outputs['Mask'], bl.inputs['Image'])
vm = ct.nodes.new('CompositorNodeMapRange'); vm.inputs['To Min'].default_value = 0.78; vm.inputs['To Max'].default_value = 1.0
ct.links.new(bl.outputs['Image'], vm.inputs['Value'])
vv = ct.nodes.new('CompositorNodeMixRGB'); vv.blend_type = 'MULTIPLY'; vv.inputs[0].default_value = 1.0
ct.links.new(ld_.outputs['Image'], vv.inputs[1]); ct.links.new(vm.outputs['Value'], vv.inputs[2])
GRADE = {'a': ((1.0, 0.97, 0.92), (1.06, 1.0, 0.9)), 'b': ((0.98, 1.0, 1.03), (1.0, 1.0, 1.02)),
         'c': ((1.0, 0.96, 0.9), (1.05, 0.99, 0.9))}[V]
cb = ct.nodes.new('CompositorNodeColorBalance'); cb.correction_method = 'LIFT_GAMMA_GAIN'
cb.lift = GRADE[0]; cb.gain = GRADE[1]
ct.links.new(vv.outputs[0], cb.inputs['Image']); ct.links.new(cb.outputs['Image'], comp.inputs['Image'])

BORDER = arg('border', '')
if BORDER:
    x0, y0, x1, y1 = (float(v) for v in BORDER.split(','))
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_min_y, sc.render.border_max_x, sc.render.border_max_y = x0, y0, x1, y1
if arg('dry', 0):
    print('DRY_OK'); sys.exit(0)
sc.render.filepath = OUT
t1 = time.time()
bpy.ops.render.render(write_still=True)
print('RENDER_SECONDS', round(time.time() - t1, 1), 'TOTAL', round(time.time() - t0, 1))
