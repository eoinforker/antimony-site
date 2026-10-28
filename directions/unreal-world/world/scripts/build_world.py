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
from gen_meshes import CRYSTAL_CENTRE_M  # noqa: E402
import materials as M  # noqa: E402

GEN = os.path.join(PROJECT, "gen")
PRINT_PNG = os.path.abspath(os.path.join(PROJECT, "../../render-poster/assets/hero-print.png"))
REPORT = json.load(open(os.path.join(PROJECT, "Saved/import_report.json")))
RNG = random.Random(11)
MAP = "/Game/Hero/Hero"

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
import concepts  # noqa: E402
CONCEPT = int(os.environ.get("CONCEPT", "1"))
CONCEPT_NAME, CONCEPT_LINE, LOOK = concepts.look(CONCEPT)
CAMERA, LIGHT, FOG = LOOK["camera"], dict(LOOK["light"], shafts=False), LOOK["fog"]
EXPOSURE_EV = LOOK["exposure"]   # exposure compensation in stops (manual exposure; positive is brighter)
FLOWER_GLOW = LOOK["flower_glow"]  # emissive strength of the petals (only the bright parts of the albedo glow)
CRYSTAL_GLOW = LOOK["crystal_glow"]
BREAK_GLOW = LOOK["break_glow"]
PRINT_GLOW = 2.2
NIGHT_TINT = (0.30, 0.42, 0.75)   # albedo multiplier for plants: green leaves go to deep blue
STONE_TINT = (0.42, 0.47, 0.62)


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
    br = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -150, 150)
    mel.connect_material_expressions(mul, "", br, "A")
    mel.connect_material_expressions(M.breathe(m, 0.3), "", br, "B")
    mel.connect_material_property(br, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
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
    """The giant crystal: a luminous translucent body, brighter at its facets' grazing edges. It casts no shadow
    itself; a hidden, slightly smaller copy does (see main), so the light behind breaks around its edges."""
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("two_sided", True)
    col = param(m, unreal.MaterialExpressionVectorParameter, "Colour", -700, 0, srgb(SKY))
    k = param(m, unreal.MaterialExpressionScalarParameter, "Strength", -700, 200, 2.0)
    op = param(m, unreal.MaterialExpressionScalarParameter, "Opacity", -700, 400, 0.45)
    fres = mel.create_material_expression(m, unreal.MaterialExpressionFresnel, -700, 600)
    fres.set_editor_property("exponent", 2.5)
    one = mel.create_material_expression(m, unreal.MaterialExpressionAdd, -450, 500)
    mel.connect_material_expressions(fres, "", one, "A")
    one.set_editor_property("const_b", 0.25)
    mul = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -450, 100)
    mel.connect_material_expressions(col, "", mul, "A")
    mel.connect_material_expressions(k, "", mul, "B")
    mul2 = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -200, 200)
    mel.connect_material_expressions(mul, "", mul2, "A")
    mel.connect_material_expressions(one, "", mul2, "B")
    br = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -50, 250)
    mel.connect_material_expressions(mul2, "", br, "A")
    mel.connect_material_expressions(M.breathe(m, 0.18), "", br, "B")
    mel.connect_material_property(br, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
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
    # The plane is stood up with a pitch, which turns its UVs a quarter: swap U and V back.
    uv = mel.create_material_expression(m, unreal.MaterialExpressionTextureCoordinate, -1100, 0)
    u = mel.create_material_expression(m, unreal.MaterialExpressionComponentMask, -900, -50)
    u.set_editor_property("r", True); u.set_editor_property("g", False)
    v = mel.create_material_expression(m, unreal.MaterialExpressionComponentMask, -900, 50)
    v.set_editor_property("r", False); v.set_editor_property("g", True)
    mel.connect_material_expressions(uv, "", u, "")
    mel.connect_material_expressions(uv, "", v, "")
    # ...and stands it upside down: flip the vertical (v, 1 - u). Checked against the print: mark above the name.
    fu = mel.create_material_expression(m, unreal.MaterialExpressionOneMinus, -820, 50)
    mel.connect_material_expressions(u, "", fu, "")
    sw = mel.create_material_expression(m, unreal.MaterialExpressionAppendVector, -750, 0)
    mel.connect_material_expressions(v, "", sw, "A")
    mel.connect_material_expressions(fu, "", sw, "B")
    mel.connect_material_expressions(sw, "", tex, "UVs")
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
        comp = lib.get_associated_object(lib.get_data(handle))
        comp.set_static_mesh(part)
        mat = mats_for(part)
        if mat:
            mats = mat if isinstance(mat, list) else [mat] * part.get_num_sections(0)
            for i, m in enumerate(mats):
                comp.set_material(i, m)
        comp.set_editor_property("cast_shadow", True)
        comp.add_instances(xforms, False, True)
    return host


def forest(label, models, points):
    """Spread the points across the tree models, one instanced actor per model, each keeping its own materials."""
    for i, m in enumerate(models):
        share = points[i::len(models)]
        if share:
            instanced(f"{label}_{i}", [m], share, lambda p: None)


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
    if x < -6 or x > CREST_X + 55:
        return 0.0
    d = 0.5 + 0.5 * math.sin(x * 0.21 + y * 0.09) * math.cos(y * 0.17 - x * 0.05)
    d += 0.35 * math.sin(x * 0.63 + 1.3) * math.sin(y * 0.51 + 0.4)
    d = max(0.0, min(1.0, (d - 0.25) * 1.6))
    bank = max(0.0, 1.0 - max(0.0, abs(y) - 22.0) / 30.0)
    return d * bank


# ------------------------------------------------------------------------------------------------------------------

def lc(rgb, k=1.0):
    return unreal.LinearColor(rgb[0] * k, rgb[1] * k, rgb[2] * k, 1.0)


def main():
    # The map is reused, not deleted: deleting a loaded map and making it again leaves the editor in an untitled world.
    if eal.does_asset_exist(MAP):
        les.load_level(MAP)
        for a in eas.get_all_level_actors():
            eas.destroy_actor(a)
    else:
        les.new_level(MAP)
    world = unreal.EditorLevelLibrary.get_editor_world()
    assert world.get_path_name().startswith(MAP), f"editing {world.get_path_name()}, not {MAP}"
    for p in ("/Game/Hero/Mat", "/Game/Hero/Tex", "/Game/Gen"):
        fresh(p)

    # Generated meshes and the print texture.
    gen = {}
    for name in ("SM_TerrainNear", "SM_TerrainFar", "SM_Crystal", "SM_Break", "SM_CrystalEdges"):
        objs = [o for o in import_file(os.path.join(GEN, name + ".obj"), "/Game/Gen", name) if isinstance(o, unreal.StaticMesh)]
        gen[name] = objs[0]
    for name, on in (("SM_TerrainNear", True), ("SM_TerrainFar", True), ("SM_Crystal", False), ("SM_Break", False), ("SM_CrystalEdges", True)):
        ns = gen[name].get_editor_property("nanite_settings")
        ns.enabled = on  # Nanite takes opaque and masked only
        gen[name].set_editor_property("nanite_settings", ns)
    import_file(PRINT_PNG, "/Game/Hero/Tex", "T_HeroPrint")

    # Materials: the glow and crystal family, then the scanned surfaces and the plants (their own maps).
    m_glow, m_crystal, m_print = material("M_Glow", build_glow), material("M_Crystal", build_crystal), material("M_Print", build_print)
    m_lit = material("M_Lit", build_lit)
    foliage, surface = M.build_foliage(), M.build_surface()
    mi = {
        "break": instance(m_glow, "MI_Break", {"Strength": BREAK_GLOW}, {"Colour": srgb(SKY)}),
        "crystal": instance(m_crystal, "MI_Crystal", {"Strength": CRYSTAL_GLOW}),
        "print": instance(m_print, "MI_Print", {"Strength": PRINT_GLOW}),
        "case": instance(m_lit, "MI_Case", {"Roughness": 0.35}, {"Base": srgb(INK, 1.0)}),
        "ground": M.surface_for("mossy_grass_vcjmej0s_8k", surface, "MI_Ground", lc(NIGHT_TINT, 0.45), tiling=5.0, roughness=0.9),
        "ground_far": M.surface_for("forest_floor_sfjmafua_8k", surface, "MI_GroundFar", lc(NIGHT_TINT, 0.4), tiling=0.4,
                                    roughness=0.95, normal_strength=0.3),
    }
    rock_mi = {}

    def rock_mat(folder, tint=STONE_TINT, k=1.0):
        if folder not in rock_mi:
            rock_mi[folder] = M.surface_for(folder, surface, f"MI_Rock_{len(rock_mi)}", lc(tint, k))
        return rock_mi[folder]

    petal = dict(Tint=lc(NIGHT_TINT), Glow=FLOWER_GLOW, GlowColour=srgb(SKY), GlowLo=0.42, GlowHi=0.85, Roughness=0.6)
    petal_deep = dict(petal, GlowColour=srgb(COBALT, 1.6), Glow=FLOWER_GLOW * 1.2)
    dark = dict(Tint=lc(NIGHT_TINT, 1.1), Glow=0.0, Roughness=0.75)

    # Terrain, the crystal and the Break.
    place(gen["SM_TerrainNear"], 0, 0, z=0, mats=mi["ground"], label="TerrainNear")
    place(gen["SM_TerrainFar"], 0, 0, z=0, mats=mi["ground_far"], label="TerrainFar")
    sx, sy, sz = LOOK["crystal_shift"]  # the crystal's meshes are built in place; a concept may move them
    if LOOK["crystal"]:
        crystal_scene(gen, mi, m_lit, sx, sy, sz)


    # The great rock on the right, and stones in the flowers.
    for folder, x, y, yaw, s, sink in [("nordic_beach_rock_formation_vd4iecjva_raw", 14.0, 10.0, 105, 1.7, 0.8),
                                       ("nordic_beach_rock_formation_vflrejtfa_raw", 30.0, -19.0, 20, 1.2, 0.5),
                                       ("nordic_forest_ledge_rock_large_xfpjeie_raw", 9.0, -6.5, 40, 0.9, 0.3),
                                       ("nordic_forest_ledge_rock_large_xfpkee1_raw", 24.0, 5.0, 130, 0.8, 0.3),
                                       ("mossy_rocks_tjmudcfda_raw", 4.5, 2.6, 10, 2.5, 0.05)]:
        for m in meshes(folder)[:1]:
            place(m, x, y, yaw=yaw, scale=s, mats=rock_mat(folder), sink=sink, label=f"Rock_{folder[:18]}")

    # Cliffs into the haze, either side of the valley, stepping back so each is paler.
    slate = sorted(k for k in REPORT if k.startswith("slate_") and REPORT[k].get("meshes"))
    cliff_sets = [(k, 1.0) for k in slate[:4]] + [("massive_nordic_coastal_cliff_vdssailfa_raw", 1.0), ("nordic_forest_cliff_large_xibsff1_raw", 1.4),
                  ("ice_cliff_uhpocesfa_raw", 2.6), ("ice_cliff_uhupbgxfa_raw", 2.4)]
    for i, (x, y, s, yaw) in enumerate([(300, -95, 8.0, 70), (460, 120, 10.0, 250), (820, -280, 13.0, 95), (1150, 360, 15.0, 260),
                                        (1700, -620, 20.0, 80), (2200, 760, 22.0, 240), (380, -180, 6.0, 30), (620, 220, 7.0, 200)]):
        folder, k = cliff_sets[i % len(cliff_sets)]
        for m in meshes(folder)[:1]:
            place(m, x, y, yaw=yaw, scale=s * k, mats=rock_mat(folder, k=0.8), sink=6.0, label=f"Cliff{i}")

    # The domed ruin, mid-right past the great rock (the OBJ scans came in at 1/100 scale).
    ruin = meshes("saepinum-mausoleum-caius-italy")
    if ruin:
        place(ruin[0], 46, 11, yaw=215, scale=100.0, mats=rock_mat("saepinum-mausoleum-caius-italy", k=0.9), sink=0.4, label="Ruin")
    mono = meshes("philopappos-monument-greece")
    if mono:
        place(mono[0], 150, -32, yaw=160, scale=100.0, mats=rock_mat("philopappos-monument-greece", k=0.9), sink=1.0, label="Monument")

    # Firs: on the left bank and behind the ruin, then thinning onto the ridges. Each tree model takes a share.
    tree_folders = ["christmass_trees_pack"]  # Trees60 and the mobile trees lose their leaf alpha on import: blobs
    tree_mats = {}

    def tree_look(part, folder):
        return M.foliage_for(part, folder, foliage, dict(Tint=lc(NIGHT_TINT, 0.55), Glow=0.0, Roughness=0.8))

    big = [(m, "christmass_trees_pack") for m in meshes("christmass_trees_pack") if "large" in m.get_name().lower() or "medium" in m.get_name().lower()]
    all_trees = [(m, f) for f in tree_folders for m in meshes(f)]
    near = [(RNG.uniform(22, 70), RNG.uniform(-40, -11), RNG.uniform(0, 360), RNG.uniform(1.1, 1.8), 0.1) for _ in range(30)]
    near += [(RNG.uniform(55, 110), RNG.uniform(12, 50), RNG.uniform(0, 360), RNG.uniform(1.0, 1.6), 0.1) for _ in range(18)]
    ridge = [(RNG.uniform(140, 1100), RNG.uniform(-700, 700), RNG.uniform(0, 360), RNG.uniform(1.0, 2.0), 0.3) for _ in range(1400)]
    for label, models, pts in (("FirsNear", big or all_trees, near), ("FirsFar", all_trees, ridge)):
        for i, (m, folder) in enumerate(models):
            share = pts[i::len(models)]
            if share:
                instanced(f"{label}_{i}", [m], share, lambda p, f=folder: tree_look(p, f))

    # Ground cover: dark grass everywhere on the near slope, so the glow has a bed.
    region = (-4, CREST_X + 60, -45, 45)
    for folder, n, sc in [("wild_grass_vlkhcbxia_raw", 24000, (0.7, 1.3)), ("kikuyu_grass_wiljearqx_raw", 14000, (0.6, 1.1))]:
        for i, part in enumerate(meshes(folder)):
            pts = scatter(n // 8, region, lambda x, y: 0.9, sc, 0.02)
            instanced(f"Grass_{folder[:10]}_{i}", [part], pts, lambda p, f=folder: M.foliage_for(p, f, foliage, dark))

    # Flowers: the glowing drifts. Small plants, dense; whatever is bright in each albedo glows.
    for folder, n, sc, look, keep in [
            ("violet_wood_sorrel_uchkajuia_raw", 30000, (1.0, 1.8), petal, None),
            ("dwarf-snowflake-mock-orange-flowers-summer", 7000, (0.10, 0.18), petal, ("flower", "leaf")),
            ("dwarf-snowflake-mock-orange-flowers-spring", 5000, (0.10, 0.16), petal_deep, ("flower", "leaf")),
            ("kalmia_latifolia_galaxy_gltf", 5000, (0.09, 0.15), petal, None),
            ("daisy_pink_flower_bush_gltf", 4000, (0.12, 0.2), petal_deep, None)]:
        parts = [p for p in meshes(folder) if not keep or any(k in p.get_name().lower() for k in keep)]
        if not parts:
            continue
        if folder.startswith("violet"):  # separate variations: share the points
            for i, part in enumerate(parts):
                instanced(f"Flowers_sorrel_{i}", [part], scatter(n // len(parts), region, drifts, sc, 0.01),
                          lambda p, f=folder, lk=look: M.foliage_for(p, f, foliage, lk))
        else:  # a bush in parts (flowers, leaves, stems): every part at the same points
            instanced(f"Flowers_{folder[:20]}", parts, scatter(n, region, drifts, sc, 0.02),
                      lambda p, f=folder, lk=look: M.foliage_for(p, f, foliage, lk))
    # A few big soft flowers right before the lens.
    lens = [p for p in meshes("dwarf-snowflake-mock-orange-flowers-summer") if any(k in p.get_name().lower() for k in ("flower", "leaf"))]
    if lens:
        instanced("FlowersLens", lens, [(RNG.uniform(0.3, 2.2), RNG.uniform(-1.6, 1.8), RNG.uniform(0, 360), RNG.uniform(0.22, 0.3), 0.05)
                                        for _ in range(6)], lambda p: M.foliage_for(p, "dwarf-snowflake-mock-orange-flowers-summer", foliage, petal))

    # The poster: the cobalt print in its slim lightbox, standing in the flowers left of centre.
    lightbox(*LOOK["lightbox"], mi=mi)
    if LOOK["stars"]:
        stars()

    sky_and_light()
    camera_and_sequence()
    presets()
    les.save_current_level()
    for p in ("/Game/Hero", "/Game/Gen", "/Game/FabTex"):
        eal.save_directory(p, only_if_is_dirty=False, recursive=True)
    unreal.log("ANTIMONY_BUILD_OK")


def crystal_scene(gen, mi, m_lit, sx, sy, sz):
    """The giant crystal with the Break inside (concepts 1 to 10; dropped after the owner's review on 28 Oct)."""
    crystal = place(gen["SM_Crystal"], sx, sy, z=sz, mats=mi["crystal"], label="Crystal")
    crystal.static_mesh_component.set_editor_property("cast_shadow", False)
    # The gobo: the crystal's edges cast shadow, unseen, so its faces let the light through in shafts.
    edges = place(gen["SM_CrystalEdges"], sx, sy, z=sz, mats=instance(m_lit, "MI_Shade", {}, {"Base": srgb(INK)}), label="CrystalEdges")
    edges.static_mesh_component.set_editor_property("cast_hidden_shadow", True)
    edges.static_mesh_component.set_editor_property("visible", False)
    brk = place(gen["SM_Break"], sx, sy, z=sz, mats=mi["break"], label="Break")
    crystal_cluster(gen["SM_Crystal"], mi["crystal"], (sx, sy, sz))
    brk.static_mesh_component.set_editor_property("cast_shadow", True)   # the Break cuts the light too


def rotate(r, v):
    """Turn a vector by a Rotator, as Unreal's FRotationMatrix does (roll, then pitch, then yaw)."""
    sp, cp = math.sin(math.radians(r.pitch)), math.cos(math.radians(r.pitch))
    sy, cy = math.sin(math.radians(r.yaw)), math.cos(math.radians(r.yaw))
    sr, cr = math.sin(math.radians(r.roll)), math.cos(math.radians(r.roll))
    X = (cp * cy, cp * sy, sp)
    Y = (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)
    Z = (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp)
    return unreal.Vector(*(v.x * X[i] + v.y * Y[i] + v.z * Z[i] for i in range(3)))


def crystal_cluster(mesh, mat, shift):
    """Smaller crystals round the giant's foot, leaning out, so it reads as a formation grown from the land."""
    cx, cy, cz = (CRYSTAL_CENTRE_M[0] + shift[0], CRYSTAL_CENTRE_M[1] + shift[1], CRYSTAL_CENTRE_M[2] + shift[2])
    half_h = 45 * 28.0  # mark units x unit (gen_meshes), metres
    rng = random.Random(5)
    for i in range(9):
        s = rng.uniform(0.12, 0.32)
        ang = rng.uniform(0, 360)
        r = rng.uniform(500, 1100)
        foot = (cx + r * math.cos(math.radians(ang)), cy + r * math.sin(math.radians(ang)))
        rot = unreal.Rotator(rng.uniform(-22, 22), rng.uniform(-22, 22), rng.uniform(0, 360))
        # The mesh is built around the crystal centre C; put s*C (rotated) where this crystal's centre should be.
        centre = unreal.Vector(foot[0] * 100, foot[1] * 100, (height(*foot) + half_h * s * 0.75) * 100)
        moved = rotate(rot, unreal.Vector(CRYSTAL_CENTRE_M[0] * 100 * s, CRYSTAL_CENTRE_M[1] * 100 * s, CRYSTAL_CENTRE_M[2] * 100 * s))
        a = eas.spawn_actor_from_class(unreal.StaticMeshActor, centre - moved, rot)
        a.static_mesh_component.set_static_mesh(mesh)
        a.static_mesh_component.set_material(0, mat)
        a.static_mesh_component.set_editor_property("cast_shadow", False)
        a.set_actor_scale3d(unreal.Vector(s, s, s))
        a.set_actor_label(f"Crystal_small_{i}")


def stars():
    """A night sky: a few thousand tiny additive points far out, untouched by the fog."""
    m = tools.create_asset("M_Star", "/Game/Hero/Mat", unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    for prop in ("use_translucency_vertex_fog", "apply_fogging"):  # stars sit beyond the mist: no fog on them
        try:
            m.set_editor_property(prop, False)
            break
        except Exception:
            pass
    k = param(m, unreal.MaterialExpressionVectorParameter, "Colour", -400, 0, unreal.LinearColor(26, 29, 38, 1))
    mel.connect_material_property(k, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(m)
    sphere = eal.load_asset("/Engine/BasicShapes/Sphere")
    rng = random.Random(3)
    pts = []
    R_M = 9000.0
    for _ in range(9000):
        az, el = rng.uniform(0, 2 * math.pi), math.asin(rng.uniform(0.02, 1.0))
        x, y, z = R_M * math.cos(el) * math.cos(az), R_M * math.cos(el) * math.sin(az), R_M * math.sin(el)
        s = 3.5 * (1.0 + 3.0 * rng.random() ** 8)  # most faint and small, a few bright
        pts.append(unreal.Transform(unreal.Vector(x * 100, y * 100, z * 100), unreal.Rotator(0, 0, 0), unreal.Vector(s, s, s)))
    host = eas.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0))
    host.set_actor_label("Stars")
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    root = sds.k2_gather_subobject_data_for_instance(host)[0]
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handle, _ = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.InstancedStaticMeshComponent,
                                                                   blueprint_context=None))
    comp = lib.get_associated_object(lib.get_data(handle))
    comp.set_static_mesh(sphere)
    comp.set_material(0, m)
    comp.set_editor_property("cast_shadow", False)
    comp.add_instances(pts, False, True)


def lightbox(x, y, yaw, mi):
    """Slim dark case 1.16 x 1.74 m on two legs; the print as emission on its face, which looks down -X at yaw 0.
    Parts are placed in world space (local offsets turned by the yaw), not attached: attaching static parts fails."""
    cube = eal.load_asset("/Engine/BasicShapes/Cube")
    plane = eal.load_asset("/Engine/BasicShapes/Plane")
    W, H, D, foot = 1.16, 1.74, 0.14, 0.45
    z0 = height(x, y) + foot
    c, s_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

    def put(mesh, name, lx, ly, lz, rot, scale, mat):  # local metres: x toward the back, y across, z up from the case foot
        wx, wy = x + lx * c - ly * s_, y + lx * s_ + ly * c
        a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(wx * 100, wy * 100, (z0 + lz) * 100), rot)
        a.static_mesh_component.set_static_mesh(mesh)
        a.static_mesh_component.set_material(0, mat)
        a.set_actor_scale3d(scale)
        a.set_actor_label(f"Lightbox_{name}")
        return a

    box = lambda name, lx, ly, lz, sx, sy, sz, mat: put(cube, name, lx, ly, lz, unreal.Rotator(0, 0, yaw), unreal.Vector(sx, sy, sz), mat)
    box("case", D / 2, 0, H / 2, D, W + 0.09, H + 0.09, mi["case"])  # the engine cube is 1 m, centred
    for side in (-1, 1):
        box(f"leg{side}", D / 2, side * (W / 2 - 0.12), -foot / 2, 0.04, 0.04, foot, mi["case"])
        box(f"foot{side}", D / 2, side * (W / 2 - 0.12), -foot + 0.02, D + 0.32, 0.1, 0.04, mi["case"])
    # The engine plane is 1 m facing +Z; pitch 90 turns its face to -X (out of the case front).
    put(plane, "print", -0.005, 0, H / 2, unreal.Rotator(0, 90, yaw), unreal.Vector(H, W, 1), mi["print"])


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
    lc.set_editor_property("bloom_scale", 0.12)
    lc.set_editor_property("bloom_threshold", 2.0)
    lc.set_editor_property("light_source_angle", 2.0)
    lc.set_editor_property("atmosphere_sun_disk_color_scale", unreal.LinearColor(0, 0, 0, 1))  # the crystal is the light

    atmo = eas.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    atmo.set_actor_label("Sky")
    ac = atmo.get_component_by_class(unreal.SkyAtmosphereComponent)
    ac.set_editor_property("mie_scattering_scale", LOOK["mie"])  # above the default 0.004: a milky, hazy sky
    ac.set_editor_property("mie_anisotropy", 0.85)             # the haze glows most toward the light
    ac.set_editor_property("multi_scattering_factor", 1.6)
    sky = eas.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 500))
    sky.set_actor_label("SkyLight")
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property("real_time_capture", True)
    sky.light_component.set_intensity(LOOK["sky_light"])

    fog = eas.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0))
    fog.set_actor_label("Mist")
    fc = fog.component
    fc.set_editor_property("fog_density", FOG["density"])
    fc.set_editor_property("fog_height_falloff", FOG["falloff"])
    fc.set_editor_property("fog_inscattering_luminance", srgb(FOG["inscatter"], 0.6))
    fc.set_editor_property("directional_inscattering_luminance", srgb(FOG["inscatter"], 0.6))
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
                 ("override_bloom_intensity", True), ("bloom_intensity", 0.45),
                 ("override_bloom_threshold", True), ("bloom_threshold", 1.5),
                 ("override_scene_color_tint", True), ("scene_color_tint", unreal.LinearColor(*LOOK["tint"], 1)),
                 ("override_vignette_intensity", True), ("vignette_intensity", 0.45),
                 ("override_white_temp", True), ("white_temp", LOOK["white_temp"]),
                 ("override_film_toe", True), ("film_toe", 0.6)]:
        s.set_editor_property(k, v)
    ppv.set_editor_property("settings", s)


PHONE = dict(CAMERA, yaw=CAMERA["yaw"] + 3.0, pitch=CAMERA["pitch"] + 2.0, focal=17.0)  # the tall frame for phones (web/build_web.py matches)


def camera(c, sensor):
    loc = unreal.Vector(c["x"] * 100, c["y"] * 100, ground(c["x"], c["y"]) + c["eye"] * 100)
    cam = eas.spawn_actor_from_class(unreal.CineCameraActor, loc, unreal.Rotator(0, c["pitch"], c["yaw"]))
    cc = cam.get_cine_camera_component()
    fb = cc.get_editor_property("filmback")
    fb.sensor_width, fb.sensor_height = sensor
    cc.set_editor_property("filmback", fb)
    cc.set_editor_property("current_focal_length", c["focal"])
    cc.set_editor_property("current_aperture", c["fstop"])
    fs = cc.get_editor_property("focus_settings")
    fs.focus_method = unreal.CameraFocusMethod.MANUAL
    fs.manual_focus_distance = c["focus_m"] * 100
    cc.set_editor_property("focus_settings", fs)
    return cam


def sequence(name, cam_spec, sensor, frames):
    path = f"/Game/Hero/{name}"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    seq = tools.create_asset(name, "/Game/Hero", unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    seq.set_display_rate(unreal.FrameRate(24, 1))
    seq.set_playback_start(0)
    seq.set_playback_end(frames)
    cam = camera(cam_spec, sensor)
    binding = seq.add_spawnable_from_instance(cam)
    eas.destroy_actor(cam)
    cut = seq.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    cut.set_range(0, frames)
    cut.set_camera_binding_id(seq.get_binding_id(binding))
    return seq


def camera_and_sequence():
    loop = int(M.LOOP_S * 24)
    sequence("HeroSeq", CAMERA, (36.0, 20.25), 1)
    sequence("HeroLoop", CAMERA, (36.0, 20.25), loop)
    sequence("PhoneSeq", PHONE, (16.6, 36.0), 1)
    sequence("PhoneLoopSeq", PHONE, (16.6, 36.0), loop)  # not "PhoneLoop": that name is the render preset


def presets():
    """Render presets. Preview: quick Lumen check. Final: Lumen at its highest for the still (2560 wide). Loop: the
    10 s web loop. Depth: the disparity pass for the web parallax. Phone*: the tall frame, same settings."""
    out_dir = unreal.DirectoryPath(os.path.join(PROJECT, "Saved/MovieRenders"))
    depth = M.build_depth()
    for name, res, temporal, spatial, warm, fmt, pp in [
            ("Preview", (1920, 1080), 32, 1, 64, "hero_preview_{frame_number}", False),
            ("Final", (3840, 2160), 64, 2, 96, "hero_final_{frame_number}", False),
            ("Loop", (1920, 1080), 12, 1, 64, "loop/hero_loop_{frame_number}", False),
            ("Depth", (1920, 1080), 8, 1, 32, "hero_depth_{frame_number}", True),
            ("PhoneFinal", (1080, 2340), 64, 2, 96, "phone_final_{frame_number}", False),
            ("PhoneLoop", (720, 1560), 12, 1, 64, "loop_phone/phone_loop_{frame_number}", False),
            ("PhoneDepth", (720, 1560), 8, 1, 32, "phone_depth_{frame_number}", True)]:
        path = f"/Game/Hero/{name}"
        if eal.does_asset_exist(path):
            eal.delete_asset(path)
        p = tools.create_asset(name, "/Game/Hero", unreal.MoviePipelinePrimaryConfig, None)
        dp = p.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
        if pp:  # the disparity as an extra pass beside the beauty
            ppp = unreal.MoviePipelinePostProcessPass()
            ppp.enabled, ppp.material = True, depth
            dp.set_editor_property("additional_post_process_materials", [ppp])
        p.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
        o = p.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
        o.output_resolution = unreal.IntPoint(*res)
        o.output_directory = out_dir
        o.file_name_format = fmt + ("_{render_pass}" if pp else "")
        aa = p.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
        aa.override_anti_aliasing = True
        aa.spatial_sample_count, aa.temporal_sample_count = spatial, temporal
        aa.engine_warm_up_count, aa.render_warm_up_count = warm, warm
        gs = p.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting)
        gs.cinematic_quality_settings = True
        gs.shadow_distance_scale = 2
        cv = p.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
        for k, v in [("r.VolumetricFog.GridPixelSize", 4), ("r.VolumetricFog.GridSizeZ", 256),
                     ("r.Lumen.ScreenProbeGather.DownsampleFactor", 8), ("r.Nanite.MaxPixelsPerEdge", 0.5)]:
            cv.add_or_update_console_variable(k, v)

main()
