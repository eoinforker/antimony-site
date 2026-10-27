"""Build the hero scene (the field under the crystal) from scratch, headless and repeatable.

Run as the 'ue' user, after import_assets.py and gen_meshes.py:
  UnrealEditor-Cmd AntimonyWorld.uproject -ExecutePythonScript=scripts/build_world.py -RenderOffscreen -unattended
Writes /Game/Hero/Hero (the level), /Game/Hero/HeroSeq (one-frame sequence with the camera) and the render presets
/Game/Hero/Preview (Lumen, 1920x1080) and /Game/Hero/Final (path tracer).

The palette is the brand's (BRAND.md): Cobalt #2448FF, Sky #94E6FF, Prussian #1F3F7A, Ink #0B0C0C, Stone #141311,
Cream #EEEAE0. Everything tunable sits in the constants below.
"""
import json
import math
import os
import random
import sys

import unreal

PROJECT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
sys.path.insert(0, os.path.join(PROJECT, "scripts"))
from terrain import height, normal, CREST_X  # noqa: E402

GEN = os.path.join(PROJECT, "gen")
PRINT_PNG = os.path.abspath(os.path.join(PROJECT, "../../render-poster/assets/hero-print.png"))
REPORT = json.load(open(os.path.join(PROJECT, "Saved/import_report.json")))
RNG = random.Random(11)

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def srgb(hexstr, scale=1.0):
    """Brand hex to a linear colour (the material and light inputs are linear)."""
    c = [int(hexstr[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return unreal.LinearColor(lin[0] * scale, lin[1] * scale, lin[2] * scale, 1.0)


COBALT, SKY, PRUSSIAN, INK, STONE, CREAM = "#2448FF", "#94E6FF", "#1F3F7A", "#0B0C0C", "#141311", "#EEEAE0"

# ---- the look (tune here) ----
CAMERA = dict(x=-2.0, y=1.5, eye=1.25, pitch=11.0, yaw=-2.0, focal=19.0, fstop=4.0, focus_m=9.0)
LIGHT = dict(pitch=-7.0, yaw=180.0, lux=6.0, colour="#DCEBFF", shafts=True, scatter=4.0)
FOG = dict(density=0.035, falloff=0.06, colour="#9FB8E8", inscatter="#CFE0FF", vol_extinction=1.2,
           vol_albedo="#E6F0FF", start_m=6.0)
EXPOSURE_EV = 1.0           # manual exposure, EV100
FLOWER_GLOW = 9.0           # emissive strength of the petals
CRYSTAL_GLOW = 2.5
BREAK_GLOW = 60.0
PRINT_GLOW = 6.0


# ------------------------------------------------------------------------------------------------------------------
# assets

def fresh(path):
    if eal.does_directory_exist(path):
        eal.delete_directory(path)
    eal.make_directory(path)


def import_file(path, dest, name=None):
    t = unreal.AssetImportTask()
    t.filename, t.destination_path, t.automated, t.replace_existing, t.save = path, dest, True, True, False
    if name:
        t.destination_name = name
    tools.import_asset_tasks([t])
    return [eal.load_asset(p) for p in t.imported_object_paths]


def meshes(folder, contains=""):
    out = [m["asset"] for m in REPORT.get(folder, {}).get("meshes", []) if contains.lower() in m["asset"].lower()]
    if not out:
        unreal.log_warning(f"ANTIMONY no meshes for {folder} {contains!r}")
    return [eal.load_asset(p) for p in out]


def material(name, build):
    m = tools.create_asset(name, "/Game/Hero/Mat", unreal.Material, unreal.MaterialFactoryNew())
    build(m)
    mel.recompile_material(m)
    return m


def param(m, cls, name, x, y, value=None):
    n = mel.create_material_expression(m, cls, x, y)
    n.set_editor_property("parameter_name", name)
    if value is not None:
        n.set_editor_property("default_value", value)
    return n


def build_glow(m):
    """Emissive surface (petals, the Break): colour x strength, a dark base so it reads as light not paint."""
    m.set_editor_property("two_sided", True)
    col = param(m, unreal.MaterialExpressionVectorParameter, "Colour", -600, 0, srgb(SKY))
    k = param(m, unreal.MaterialExpressionScalarParameter, "Strength", -600, 200, 10.0)
    mul = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -300, 100)
    mel.connect_material_expressions(col, "", mul, "A")
    mel.connect_material_expressions(k, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    base = param(m, unreal.MaterialExpressionVectorParameter, "Base", -600, -200, srgb(INK))
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)


def build_lit(m):
    """Plain lit surface for the blockout (ground, rock, trees until their own textures go on)."""
    m.set_editor_property("two_sided", True)
    base = param(m, unreal.MaterialExpressionVectorParameter, "Base", -600, 0, srgb(STONE))
    rough = param(m, unreal.MaterialExpressionScalarParameter, "Roughness", -600, 200, 0.85)
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)


def build_crystal(m):
    """The giant crystal: a luminous translucent body; the light it holds comes from the Break inside."""
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("two_sided", True)
    col = param(m, unreal.MaterialExpressionVectorParameter, "Colour", -700, 0, srgb(SKY))
    k = param(m, unreal.MaterialExpressionScalarParameter, "Strength", -700, 200, 2.0)
    op = param(m, unreal.MaterialExpressionScalarParameter, "Opacity", -700, 400, 0.22)
    # Facets catch more light at grazing angles: brighten by Fresnel so the edges read.
    fres = mel.create_material_expression(m, unreal.MaterialExpressionFresnel, -700, 600)
    one = mel.create_material_expression(m, unreal.MaterialExpressionAdd, -450, 500)
    mel.connect_material_expressions(fres, "", one, "A")
    one.set_editor_property("const_b", 0.35)
    mul = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -450, 100)
    mel.connect_material_expressions(col, "", mul, "A")
    mel.connect_material_expressions(k, "", mul, "B")
    mul2 = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -200, 200)
    mel.connect_material_expressions(mul, "", mul2, "A")
    mel.connect_material_expressions(one, "", mul2, "B")
    mel.connect_material_property(mul2, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    opm = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -200, 450)
    mel.connect_material_expressions(op, "", opm, "A")
    mel.connect_material_expressions(one, "", opm, "B")
    mel.connect_material_property(opm, "", unreal.MaterialProperty.MP_OPACITY)


def build_print(m):
    """The cobalt print, lit from within: the image as emission."""
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    tex = mel.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, 0)
    tex.set_editor_property("parameter_name", "Print")
    tex.set_editor_property("texture", eal.load_asset("/Game/Hero/Tex/T_HeroPrint"))
    k = param(m, unreal.MaterialExpressionScalarParameter, "Strength", -600, 300, 6.0)
    mul = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -300, 100)
    mel.connect_material_expressions(tex, "RGB", mul, "A")
    mel.connect_material_expressions(k, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)


def instance(parent, name, scalars=None, vectors=None):
    mi = tools.create_asset(name, "/Game/Hero/Mat", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, parent)
    for k, v in (scalars or {}).items():
        mel.set_material_instance_scalar_parameter_value(mi, k, v)
    for k, v in (vectors or {}).items():
        mel.set_material_instance_vector_parameter_value(mi, k, v)
    return mi


# ------------------------------------------------------------------------------------------------------------------
# placing things

def ground(x, y):
    return height(x, y) * 100.0


def place(mesh, x, y, z=None, yaw=0.0, scale=1.0, mats=None, sink=0.0, label=None, tilt=None):
    """Put a mesh on the ground at (x, y) metres; z in metres overrides the terrain height."""
    zz = (ground(x, y) if z is None else z * 100.0) - sink * 100.0
    rot = unreal.Rotator(0, 0, yaw) if tilt is None else unreal.Rotator(tilt[0], tilt[1], yaw)
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x * 100, y * 100, zz), rot)
    a.static_mesh_component.set_static_mesh(mesh)
    a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    if mats:
        for i in range(mesh.get_num_sections(0)):
            a.static_mesh_component.set_material(i, mats if isinstance(mats, unreal.MaterialInterface) else mats[i % len(mats)])
    if label:
        a.set_actor_label(label)
    return a


def instanced(label, parts, points, mats_for):
    """One actor per asset, with a hierarchical instanced component per part (bush = flowers + leaves + bark)."""
    host = eas.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0))
    host.set_actor_label(label)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    root = sds.k2_gather_subobject_data_for_instance(host)[0]
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    xforms = []
    for x, y, yaw, s, sink in points:
        xforms.append(unreal.Transform(unreal.Vector(x * 100, y * 100, ground(x, y) - sink * 100),
                                       unreal.Rotator(0, 0, yaw), unreal.Vector(s, s, s)))
    for part in parts:
        params = unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.HierarchicalInstancedStaticMeshComponent,
                                              blueprint_context=None)
        handle, fail = sds.add_new_subobject(params)
        comp = lib.get_object(lib.get_data(handle))
        comp.set_static_mesh(part)
        mat = mats_for(part)
        if mat:
            for i in range(part.get_num_sections(0)):
                comp.set_material(i, mat)
        comp.set_editor_property("cast_shadow", True)
        comp.add_instances(xforms, False, True)
    return host


def scatter(n, region, density, scale=(0.8, 1.3), sink=0.02, min_gap=0.0):
    """Points over a region (x0, x1, y0, y1) in metres, kept where density(x, y) beats a random draw."""
    x0, x1, y0, y1 = region
    pts, tries = [], 0
    while len(pts) < n and tries < n * 40:
        tries += 1
        x, y = RNG.uniform(x0, x1), RNG.uniform(y0, y1)
        if RNG.random() > density(x, y):
            continue
        pts.append((x, y, RNG.uniform(0, 360), RNG.uniform(*scale), sink))
    return pts


def drifts(x, y):
    """Where the flowers grow: drifts and clumps running up the slope, densest in the middle distance, thin at the crest
    and on the banks, with dark gaps between so the glow has shape."""
    if x < -6 or x > CREST_X + 30:
        return 0.0
    d = 0.5 + 0.5 * math.sin(x * 0.21 + y * 0.09) * math.cos(y * 0.17 - x * 0.05)
    d += 0.35 * math.sin(x * 0.63 + 1.3) * math.sin(y * 0.51 + 0.4)
    d = max(0.0, min(1.0, (d - 0.25) * 1.6))
    bank = max(0.0, 1.0 - max(0.0, abs(y) - 22.0) / 30.0)
    return d * bank


# ------------------------------------------------------------------------------------------------------------------

def main():
    for p in ("/Game/Hero", "/Game/Gen"):
        fresh(p)
    les.new_level("/Game/Hero/Hero")

    # Generated meshes and the print texture.
    gen = {}
    for name in ("SM_TerrainNear", "SM_TerrainFar", "SM_Crystal", "SM_Break"):
        objs = [o for o in import_file(os.path.join(GEN, name + ".obj"), "/Game/Gen", name) if isinstance(o, unreal.StaticMesh)]
        gen[name] = objs[0]
        b = objs[0].get_bounding_box()
        unreal.log(f"ANTIMONY gen {name} min={b.min} max={b.max}")
    for name in ("SM_TerrainNear", "SM_TerrainFar"):
        ns = gen[name].get_editor_property("nanite_settings")
        ns.enabled = True
        gen[name].set_editor_property("nanite_settings", ns)
    eal.make_directory("/Game/Hero/Tex")
    import_file(PRINT_PNG, "/Game/Hero/Tex", "T_HeroPrint")

    # Materials.
    m_glow, m_lit = material("M_Glow", build_glow), material("M_Lit", build_lit)
    m_crystal, m_print = material("M_Crystal", build_crystal), material("M_Print", build_print)
    mi = {
        "petal": instance(m_glow, "MI_Petal", {"Strength": FLOWER_GLOW}, {"Colour": srgb(SKY), "Base": srgb(COBALT, 0.2)}),
        "petal_deep": instance(m_glow, "MI_PetalDeep", {"Strength": FLOWER_GLOW * 0.8}, {"Colour": srgb(COBALT), "Base": srgb(COBALT, 0.2)}),
        "break": instance(m_glow, "MI_Break", {"Strength": BREAK_GLOW}, {"Colour": srgb(SKY)}),
        "crystal": instance(m_crystal, "MI_Crystal", {"Strength": CRYSTAL_GLOW}),
        "print": instance(m_print, "MI_Print", {"Strength": PRINT_GLOW}),
        "ground": instance(m_lit, "MI_Ground", {"Roughness": 0.9}, {"Base": srgb(PRUSSIAN, 0.18)}),
        "rock": instance(m_lit, "MI_Rock", {"Roughness": 0.8}, {"Base": srgb(STONE, 1.6)}),
        "leaf": instance(m_lit, "MI_Leaf", {"Roughness": 0.7}, {"Base": srgb(PRUSSIAN, 0.35)}),
        "fir": instance(m_lit, "MI_Fir", {"Roughness": 0.9}, {"Base": srgb(INK, 1.0)}),
        "case": instance(m_lit, "MI_Case", {"Roughness": 0.35}, {"Base": srgb(INK, 1.0)}),
    }

    # Terrain, the crystal and the Break.
    place(gen["SM_TerrainNear"], 0, 0, z=0, mats=mi["ground"], label="TerrainNear")
    place(gen["SM_TerrainFar"], 0, 0, z=0, mats=mi["ground"], label="TerrainFar")
    place(gen["SM_Crystal"], 0, 0, z=0, mats=mi["crystal"], label="Crystal")
    place(gen["SM_Break"], 0, 0, z=0, mats=mi["break"], label="Break")

    # The great rock on the right, close to the lens, and stones in the grass.
    rock = meshes("nordic_beach_rock_formation_vd4iecjva_raw")
    if rock:
        place(rock[0], 9.0, 10.5, yaw=200, scale=3.4, mats=mi["rock"], sink=0.6, label="GreatRock")
    for i, (folder, x, y, s, yaw) in enumerate([("nordic_forest_ledge_rock_large_xfpjeie_raw", 26, -14, 1.6, 40),
                                                ("nordic_forest_ledge_rock_large_xfpkee1_raw", 34, 18, 1.4, 130),
                                                ("mossy_rocks_tjmudcfda_raw", 6, -3.5, 2.0, 10)]):
        for m in meshes(folder)[:1]:
            place(m, x, y, yaw=yaw, scale=s, mats=mi["rock"], sink=0.2, label=f"Stone{i}")

    # Cliffs into the haze: the middle ground either side of the valley.
    cliffs = meshes("massive_nordic_coastal_cliff_vdssailfa_raw") + meshes("nordic_forest_cliff_large_xibsff1_raw")
    for i, (x, y, s, yaw) in enumerate([(320, -260, 9.0, 70), (520, 330, 11.0, 250), (900, -520, 14.0, 95), (1300, 640, 16.0, 260)]):
        if cliffs:
            place(cliffs[i % len(cliffs)], x, y, yaw=yaw, scale=s, mats=mi["rock"], sink=4.0, label=f"Cliff{i}")

    # The domed ruin on the right bank, past the great rock.
    ruin = meshes("saepinum-mausoleum-caius-italy") or meshes("mausoleum-of-james-and-carre-mcdonald")
    if ruin:
        place(ruin[0], 58, 30, yaw=235, scale=1.0, mats=mi["rock"], sink=0.3, label="Ruin")

    # Firs: on the left bank near, then thinning onto the ridges.
    fir = meshes("fir-tree-inside-circle-of-flowers")
    if fir:
        near_firs = [(RNG.uniform(10, 70), RNG.uniform(-75, -30), RNG.uniform(0, 360), RNG.uniform(0.8, 1.4), 0.1) for _ in range(28)]
        far_firs = [(RNG.uniform(120, 700), RNG.uniform(-450, 450), RNG.uniform(0, 360), RNG.uniform(0.9, 1.6), 0.2) for _ in range(260)]
        instanced("FirsNear", fir, near_firs, lambda p: mi["fir"])
        instanced("FirsFar", fir, far_firs, lambda p: mi["fir"])

    # Flowers: the glowing drifts. Bush parts named Flower/petal glow; leaves and bark stay dark.
    def flower_mat(part, deep=False):
        n = part.get_name().lower()
        if any(k in n for k in ("bark", "leaf", "stem", "branch", "gullash")):
            return mi["leaf"]
        return mi["petal_deep"] if deep else mi["petal"]

    region = (-6, CREST_X + 30, -48, 48)
    for folder, n, scale, deep in [("dwarf-snowflake-mock-orange-flowers-summer", 2600, (0.25, 0.55), False),
                                   ("dwarf-snowflake-mock-orange-flowers-spring", 1600, (0.25, 0.5), True),
                                   ("kalmia_latifolia_galaxy_gltf", 1400, (0.3, 0.6), False),
                                   ("daisy_pink_flower_bush_gltf", 1200, (0.35, 0.7), True)]:
        parts = meshes(folder)
        if parts:
            instanced(f"Flowers_{folder[:20]}", parts, scatter(n, region, drifts, scale), lambda p, d=deep: flower_mat(p, d))
    # A few huge soft flowers right before the lens.
    big = meshes("dwarf-snowflake-mock-orange-flowers-summer")
    if big:
        instanced("FlowersLens", big, [(RNG.uniform(-1.2, 2.5), RNG.uniform(-2.2, 2.2), RNG.uniform(0, 360), RNG.uniform(0.7, 1.0), 0.05)
                                       for _ in range(7)], lambda p: flower_mat(p))

    # The poster: the cobalt print in its slim lightbox, standing in the flowers left of centre.
    lightbox(x=16.0, y=-4.5, yaw=-30.0, mi=mi)  # yaw -16 would face the lens square on

    sky_and_light()
    seq = camera_and_sequence()
    presets()
    les.save_current_level()
    eal.save_directory("/Game/Hero", only_if_is_dirty=False, recursive=True)
    eal.save_directory("/Game/Gen", only_if_is_dirty=False, recursive=True)
    unreal.log("ANTIMONY_BUILD_OK")


def lightbox(x, y, yaw, mi):
    """Slim dark case 1.16 x 1.74 m on two legs; the print as emission on its face, which looks down -X at yaw 0."""
    cube = eal.load_asset("/Engine/BasicShapes/Cube")
    plane = eal.load_asset("/Engine/BasicShapes/Plane")
    W, H, D, F, foot = 1.16, 1.74, 0.14, 0.045, 0.45
    z0 = height(x, y) + foot
    host = eas.spawn_actor_from_class(unreal.Actor, unreal.Vector(x * 100, y * 100, z0 * 100), unreal.Rotator(0, 0, yaw))
    host.set_actor_label("Lightbox")

    def box(name, cx, cy, cz, sx, sy, sz, mat):  # local metres: x depth (toward the back), y across, z up from the case foot
        a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0))
        a.static_mesh_component.set_static_mesh(cube)
        a.static_mesh_component.set_material(0, mat)
        a.set_actor_label(f"Lightbox_{name}")
        a.attach_to_actor(host, "", unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE,
                          unreal.AttachmentRule.KEEP_RELATIVE, False)
        a.set_actor_relative_location(unreal.Vector(cx * 100, cy * 100, cz * 100), False, False)
        a.set_actor_relative_scale3d(unreal.Vector(sx, sy, sz))  # the engine cube is 1 m
        return a

    box("back", D / 2, 0, H / 2, D, W + 2 * F, H + 2 * F, mi["case"])
    for side in (-1, 1):
        box(f"leg{side}", D / 2, side * (W / 2 - 0.12), -foot / 2, 0.04, 0.04, foot, mi["case"])
        box(f"foot{side}", D / 2, side * (W / 2 - 0.12), -foot + 0.02, D + 0.32, 0.1, 0.04, mi["case"])
    face = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0))
    face.static_mesh_component.set_static_mesh(plane)
    face.static_mesh_component.set_material(0, mi["print"])
    face.set_actor_label("Lightbox_print")
    face.attach_to_actor(host, "", unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE,
                         unreal.AttachmentRule.KEEP_RELATIVE, False)
    # The engine plane is 1 m, facing +Z; stand it up facing -X (out of the case front).
    face.set_actor_relative_location(unreal.Vector(-0.005 * 100, 0, H / 2 * 100), False, False)
    face.set_actor_relative_rotation(unreal.Rotator(0, 90, 0), False, False)  # (roll, pitch, yaw): +Z normal to -X
    face.set_actor_relative_scale3d(unreal.Vector(H, W, 1))


def sky_and_light():
    sun = eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 50000),
                                     unreal.Rotator(0, LIGHT["pitch"], LIGHT["yaw"]))
    sun.set_actor_label("BackLight")
    lc = sun.light_component
    lc.set_intensity(LIGHT["lux"])
    lc.set_light_color(srgb(LIGHT["colour"]))
    lc.set_atmosphere_sun_light(True)
    lc.set_editor_property("volumetric_scattering_intensity", LIGHT["scatter"])
    lc.set_editor_property("enable_light_shaft_bloom", LIGHT["shafts"])
    lc.set_editor_property("enable_light_shaft_occlusion", True)
    lc.set_editor_property("bloom_scale", 0.4)
    lc.set_editor_property("bloom_threshold", 2.0)
    lc.set_editor_property("source_angle", 2.0)

    eas.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0)).set_actor_label("Sky")
    sky = eas.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 500))
    sky.set_actor_label("SkyLight")
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property("real_time_capture", True)
    sky.light_component.set_intensity(1.4)

    fog = eas.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0))
    fog.set_actor_label("Mist")
    fc = fog.component
    fc.set_editor_property("fog_density", FOG["density"])
    fc.set_editor_property("fog_height_falloff", FOG["falloff"])
    fc.set_editor_property("fog_inscattering_luminance", srgb(FOG["inscatter"], 0.6))
    fc.set_editor_property("directional_inscattering_luminance", srgb(FOG["inscatter"], 1.4))
    fc.set_editor_property("start_distance", FOG["start_m"] * 100)
    fc.set_editor_property("enable_volumetric_fog", True)
    fc.set_editor_property("volumetric_fog_extinction_scale", FOG["vol_extinction"])
    fc.set_editor_property("volumetric_fog_albedo", unreal.Color(230, 240, 255, 255))
    fc.set_editor_property("volumetric_fog_distance", 600000.0)

    clouds = eas.spawn_actor_from_class(unreal.VolumetricCloud, unreal.Vector(0, 0, 0))
    clouds.set_actor_label("Clouds")

    ppv = eas.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
    ppv.set_actor_label("Grade")
    ppv.set_editor_property("unbound", True)
    s = ppv.settings
    for k, v in [("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                 ("override_auto_exposure_apply_physical_camera_exposure", True), ("auto_exposure_apply_physical_camera_exposure", False),
                 ("override_auto_exposure_bias", True), ("auto_exposure_bias", EXPOSURE_EV),
                 ("override_bloom_intensity", True), ("bloom_intensity", 1.2),
                 ("override_bloom_threshold", True), ("bloom_threshold", 1.0),
                 ("override_vignette_intensity", True), ("vignette_intensity", 0.45),
                 ("override_white_temp", True), ("white_temp", 7200.0),
                 ("override_film_toe", True), ("film_toe", 0.6)]:
        s.set_editor_property(k, v)
    ppv.set_editor_property("settings", s)


def camera_and_sequence():
    c = CAMERA
    loc = unreal.Vector(c["x"] * 100, c["y"] * 100, ground(c["x"], c["y"]) + c["eye"] * 100)
    cam = eas.spawn_actor_from_class(unreal.CineCameraActor, loc, unreal.Rotator(0, c["pitch"], c["yaw"]))
    cc = cam.get_cine_camera_component()
    fb = cc.get_editor_property("filmback")
    fb.sensor_width, fb.sensor_height = 36.0, 20.25
    cc.set_editor_property("filmback", fb)
    cc.set_editor_property("current_focal_length", c["focal"])
    cc.set_editor_property("current_aperture", c["fstop"])
    fs = cc.get_editor_property("focus_settings")
    fs.focus_method = unreal.CameraFocusMethod.MANUAL
    fs.manual_focus_distance = c["focus_m"] * 100
    cc.set_editor_property("focus_settings", fs)

    seq = tools.create_asset("HeroSeq", "/Game/Hero", unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    seq.set_display_rate(unreal.FrameRate(24, 1))
    seq.set_playback_start(0)
    seq.set_playback_end(1)
    binding = seq.add_spawnable_from_instance(cam)
    eas.destroy_actor(cam)
    cut = seq.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    cut.set_range(0, 1)
    cut.set_camera_binding_id(seq.get_binding_id(binding))
    return seq


def presets():
    out_dir = unreal.DirectoryPath(os.path.join(PROJECT, "Saved/MovieRenders"))
    for name, pass_cls, spatial, temporal, warm in [("Preview", unreal.MoviePipelineDeferredPassBase, 1, 16, 64),
                                                    ("Final", unreal.MoviePipelineDeferredPass_PathTracer, 1024, 1, 8)]:
        p = tools.create_asset(name, "/Game/Hero", unreal.MoviePipelinePrimaryConfig, None)
        p.find_or_add_setting_by_class(pass_cls)
        p.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
        o = p.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
        o.output_resolution = unreal.IntPoint(1920, 1080)
        o.output_directory = out_dir
        o.file_name_format = "hero_" + name.lower() + "_{frame_number}"
        aa = p.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
        aa.override_anti_aliasing = True
        aa.spatial_sample_count, aa.temporal_sample_count = spatial, temporal
        aa.engine_warm_up_count, aa.render_warm_up_count = warm, warm
        # Lumen at its best for the preview: these mirror the cinematic scalability.
        gs = p.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting)
        gs.cinematic_quality_settings = True
        gs.shadow_distance_scale = 2
        cv = p.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
        for k, v in [("r.VolumetricFog.GridPixelSize", 4), ("r.VolumetricFog.GridSizeZ", 256),
                     ("r.Lumen.ScreenProbeGather.DownsampleFactor", 8), ("r.Nanite.MaxPixelsPerEdge", 0.5)]:
            cv.add_or_update_console_variable(k, v)


main()
