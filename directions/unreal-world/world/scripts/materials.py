"""Master materials and texture handling for the hero, used by build_world.py.

Two masters:
  M_Foliage  masked, two-sided. The asset's own albedo (and its alpha, or a separate opacity map) and normal,
             tinted toward the night; whatever is bright in the albedo (petals) glows, so leaves stay dark and
             flowers light up, from one rule.
  M_Surface  opaque. Albedo, normal, tint, roughness and tiling, for scanned rock and the ground.
Textures from the Fab folders are imported once into /Game/FabTex/<folder>/ and kept between builds.
"""
import os
import re

import unreal

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
FAB_SRC = os.environ.get("FAB_SRC", "/workspace/fab/src")
MAT_DIR = "/Game/Hero/Mat"

KINDS = {  # file-name patterns for each map, first match wins; billboards, previews and LOD bakes are skipped
    "albedo": r"(basecolou?r|albedo|diffuse|_col(or)?(_full)?\b|_color)",
    "normal": r"normal",
    "opacity": r"(opacity|alpha|_mask)",
    "roughness": r"roughness",
}
SKIP = r"(billboard|preview|thumb|_lod[1-9]|gloss|cavity|bump|displacement|specular)"


# ---------------------------------------------------------------- textures

def find_maps(folder):
    """The maps in a Fab folder, by kind. Prefers the largest file of each kind (the raw scans' 8K)."""
    found = {}
    root = os.path.join(FAB_SRC, folder)
    files = []
    for d, _, fs in os.walk(root):
        files += [os.path.join(d, f) for f in fs if f.lower().endswith((".jpg", ".jpeg", ".png", ".tga", ".tif", ".tiff", ".exr"))]
    for kind, pat in KINDS.items():
        hits = [f for f in files if re.search(pat, os.path.basename(f).lower()) and not re.search(SKIP, os.path.basename(f).lower())]
        if kind == "albedo":
            hits = [f for f in hits if not re.search(KINDS["normal"] + "|" + KINDS["opacity"], os.path.basename(f).lower())]
        if hits:
            found[kind] = max(hits, key=os.path.getsize)
    return found


def texture(path, folder, kind):
    """Import a map once, capped at 4K, with the right colour space and compression for its kind."""
    dest = f"/Game/FabTex/{re.sub(r'[^A-Za-z0-9_]', '_', folder)[:48]}"
    name = "T_" + re.sub(r"[^A-Za-z0-9_]", "_", os.path.splitext(os.path.basename(path))[0])[:60]
    asset_path = f"{dest}/{name}"
    if eal.does_asset_exist(asset_path):
        return eal.load_asset(asset_path)
    t = unreal.AssetImportTask()
    t.filename, t.destination_path, t.destination_name = path, dest, name
    t.automated, t.replace_existing, t.save = True, True, False
    tools.import_asset_tasks([t])
    tex = eal.load_asset(asset_path)
    if not tex:
        unreal.log_warning(f"ANTIMONY texture import failed {path}")
        return None
    tex.set_editor_property("max_texture_size", 4096)
    if kind == "normal":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property("srgb", False)
    else:
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
        tex.set_editor_property("srgb", kind in ("albedo", "opacity"))
    eal.save_loaded_asset(tex)
    return tex


# ---------------------------------------------------------------- masters

def _tex_param(m, name, x, y, default, normal=False):
    n = mel.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, x, y)
    n.set_editor_property("parameter_name", name)
    n.set_editor_property("texture", eal.load_asset(default))
    if normal:
        n.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    return n


def _scalar(m, name, x, y, v):
    n = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, x, y)
    n.set_editor_property("parameter_name", name)
    n.set_editor_property("default_value", v)
    return n


def _vector(m, name, x, y, v):
    n = mel.create_material_expression(m, unreal.MaterialExpressionVectorParameter, x, y)
    n.set_editor_property("parameter_name", name)
    n.set_editor_property("default_value", v)
    return n


def _op(m, cls, a, b, x, y, a_out="", b_out=""):
    n = mel.create_material_expression(m, cls, x, y)
    mel.connect_material_expressions(a, a_out, n, "A")
    mel.connect_material_expressions(b, b_out, n, "B")
    return n


WHITE = "/Engine/EngineResources/WhiteSquareTexture"
DEFAULT_NORMAL = "/Engine/EngineMaterials/DefaultNormal"


def _create(name):
    path = f"{MAT_DIR}/{name}"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    return tools.create_asset(name, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())


def build_foliage():
    m = _create("M_Foliage")
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    m.set_editor_property("two_sided", True)
    m.set_editor_property("opacity_mask_clip_value", 0.4)
    alb = _tex_param(m, "Albedo", -1400, -200, WHITE)
    opa = _tex_param(m, "Opacity", -1400, 200, WHITE)
    nrm = _tex_param(m, "Normal", -1400, 600, DEFAULT_NORMAL, normal=True)
    tint = _vector(m, "Tint", -1100, -400, unreal.LinearColor(0.35, 0.45, 0.7, 1))
    base = _op(m, unreal.MaterialExpressionMultiply, alb, tint, -800, -300, "RGB")
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = _scalar(m, "Roughness", -800, -100, 0.7)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(nrm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    # Opacity: the albedo's alpha, or a separate map (AlphaFromAlbedo picks).
    afa = _scalar(m, "AlphaFromAlbedo", -1100, 300, 1.0)
    lerp = mel.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -800, 250)
    mel.connect_material_expressions(opa, "R", lerp, "A")
    mel.connect_material_expressions(alb, "A", lerp, "B")
    mel.connect_material_expressions(afa, "", lerp, "Alpha")
    mel.connect_material_property(lerp, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    # Glow: the bright parts of the albedo (petals), by luminance.
    w = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -1100, 0)
    w.set_editor_property("constant", unreal.LinearColor(0.3, 0.59, 0.11, 1))
    lum = _op(m, unreal.MaterialExpressionDotProduct, alb, w, -800, 0, "RGB")
    ss = mel.create_material_expression(m, unreal.MaterialExpressionSmoothStep, -550, 0)
    mel.connect_material_expressions(_scalar(m, "GlowLo", -800, 100, 0.45), "", ss, "Min")
    mel.connect_material_expressions(_scalar(m, "GlowHi", -800, 180, 0.8), "", ss, "Max")
    mel.connect_material_expressions(lum, "", ss, "Value")
    col = _op(m, unreal.MaterialExpressionMultiply, _vector(m, "GlowColour", -800, 400, unreal.LinearColor(0.3, 0.8, 1.0, 1)),
              _scalar(m, "Glow", -800, 500, 0.0), -550, 400)
    em = _op(m, unreal.MaterialExpressionMultiply, ss, col, -300, 200)
    mel.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(m)
    return m


def build_surface():
    m = _create("M_Surface")
    m.set_editor_property("two_sided", True)
    uv = mel.create_material_expression(m, unreal.MaterialExpressionTextureCoordinate, -1700, 0)
    tiled = _op(m, unreal.MaterialExpressionMultiply, uv, _scalar(m, "Tiling", -1700, 150, 1.0), -1500, 50)
    alb = _tex_param(m, "Albedo", -1200, -200, WHITE)
    nrm = _tex_param(m, "Normal", -1200, 300, DEFAULT_NORMAL, normal=True)
    mel.connect_material_expressions(tiled, "", alb, "UVs")
    mel.connect_material_expressions(tiled, "", nrm, "UVs")
    tint = _vector(m, "Tint", -900, -400, unreal.LinearColor(0.4, 0.45, 0.6, 1))
    base = _op(m, unreal.MaterialExpressionMultiply, alb, tint, -600, -300, "RGB")
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    # Flatten the normal a little at distance-scale tiling so far ground does not shimmer.
    k = _scalar(m, "NormalStrength", -900, 450, 1.0)
    flat = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -900, 550)
    flat.set_editor_property("constant", unreal.LinearColor(0, 0, 1, 1))
    nl = mel.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -600, 400)
    mel.connect_material_expressions(flat, "", nl, "A")
    mel.connect_material_expressions(nrm, "RGB", nl, "B")
    mel.connect_material_expressions(k, "", nl, "Alpha")
    mel.connect_material_property(nl, "", unreal.MaterialProperty.MP_NORMAL)
    mel.connect_material_property(_scalar(m, "Roughness", -600, 0, 0.85), "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(m)
    return m


def instance(parent, name, scalars=None, vectors=None, textures=None):
    path = f"{MAT_DIR}/{name}"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    mi = tools.create_asset(name, MAT_DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, parent)
    for k, v in (scalars or {}).items():
        mel.set_material_instance_scalar_parameter_value(mi, k, v)
    for k, v in (vectors or {}).items():
        mel.set_material_instance_vector_parameter_value(mi, k, v)
    for k, v in (textures or {}).items():
        if v:
            mel.set_material_instance_texture_parameter_value(mi, k, v)
    return mi


# ---------------------------------------------------------------- per-asset materials

def gltf_maps(mat):
    """Albedo (with alpha) and normal from a glTF material instance made by Interchange."""
    if not isinstance(mat, unreal.MaterialInstance):
        return None, None
    get = lambda n: mel.get_material_instance_texture_parameter_value(mat, n)
    return get("BaseColorTexture"), get("NormalTexture")


_cache = {}


def foliage_for(mesh, folder, foliage, look):
    """One M_Foliage instance per source material of the mesh (cached), with the asset's own maps.
    look: dict of Tint, Glow, GlowColour, GlowLo, GlowHi, Roughness."""
    mats = []
    for i in range(mesh.get_num_sections(0)):
        src = mesh.get_material(i)
        key = (folder, src.get_name() if src else "none", tuple(sorted((k, str(v)) for k, v in look.items())))
        if key not in _cache:
            alb, nrm = gltf_maps(src)
            opacity, afa = None, 1.0
            if alb is None:  # an FBX scan: its maps sit in the folder
                maps = find_maps(folder)
                alb = texture(maps["albedo"], folder, "albedo") if "albedo" in maps else None
                nrm = texture(maps["normal"], folder, "normal") if "normal" in maps else None
                if "opacity" in maps:
                    opacity, afa = texture(maps["opacity"], folder, "opacity"), 0.0
            name = re.sub(r"[^A-Za-z0-9_]", "_", f"MI_F_{folder[:24]}_{src.get_name() if src else i}_{len(_cache)}")[:80]
            scal = {k: v for k, v in look.items() if not isinstance(v, unreal.LinearColor)}
            scal["AlphaFromAlbedo"] = afa
            _cache[key] = instance(foliage, name, scal, {k: v for k, v in look.items() if isinstance(v, unreal.LinearColor)},
                                   {"Albedo": alb, "Normal": nrm, "Opacity": opacity})
        mats.append(_cache[key])
    return mats


def surface_for(folder, surface, name, tint, tiling=1.0, roughness=0.85, normal_strength=1.0):
    maps = find_maps(folder)
    if "albedo" not in maps:
        unreal.log_warning(f"ANTIMONY no albedo in {folder}")
    return instance(surface, name, {"Tiling": tiling, "Roughness": roughness, "NormalStrength": normal_strength}, {"Tint": tint},
                    {"Albedo": texture(maps["albedo"], folder, "albedo") if "albedo" in maps else None,
                     "Normal": texture(maps["normal"], folder, "normal") if "normal" in maps else None})
