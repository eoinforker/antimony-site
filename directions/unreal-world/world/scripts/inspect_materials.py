"""List each plant mesh's material slots: the material, its parent, and its texture/scalar/vector parameters.
Writes Saved/materials_report.json (used to build the plant materials)."""
import json, os
import unreal
eal = unreal.EditorAssetLibrary
PROJECT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
report = json.load(open(os.path.join(PROJECT, "Saved/import_report.json")))
FOLDERS = os.environ.get("FOLDERS", "").split(",")
out = {}
for folder in FOLDERS:
    for m in report.get(folder, {}).get("meshes", []):
        mesh = eal.load_asset(m["asset"])
        slots = []
        for i, sm in enumerate(mesh.get_editor_property("static_materials")):
            mat = sm.get_editor_property("material_interface")
            d = {"slot": str(sm.get_editor_property("material_slot_name")), "material": mat.get_path_name() if mat else None}
            if isinstance(mat, unreal.MaterialInstance):
                d["parent"] = mat.get_editor_property("parent").get_path_name() if mat.get_editor_property("parent") else None
                d["textures"] = {str(p.parameter_info.name): (p.parameter_value.get_path_name() if p.parameter_value else None)
                                 for p in mat.get_editor_property("texture_parameter_values")}
                d["scalars"] = {str(p.parameter_info.name): p.parameter_value for p in mat.get_editor_property("scalar_parameter_values")}
                d["blend"] = str(mat.get_blend_mode()) if hasattr(mat, "get_blend_mode") else ""
            elif isinstance(mat, unreal.Material):
                d["blend"] = str(mat.get_editor_property("blend_mode"))
                d["textures_used"] = [t.get_path_name() for t in unreal.MaterialEditingLibrary.get_used_textures(mat)]
            slots.append(d)
        out[m["asset"]] = {"size_m": m["size_m"], "slots": slots}
json.dump(out, open(os.path.join(PROJECT, "Saved/materials_report.json"), "w"), indent=1)
unreal.log("ANTIMONY_INSPECT_OK")
