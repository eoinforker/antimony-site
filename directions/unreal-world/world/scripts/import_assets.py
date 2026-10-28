"""Import every Fab asset under FAB_SRC into /Game/Fab/<folder>, meshes with Nanite on.

Run headless (as the 'ue' user):
  UnrealEditor-Cmd AntimonyWorld.uproject -ExecutePythonScript=scripts/import_assets.py -RenderOffscreen -unattended
Reruns skip folders that already have assets. Writes Saved/import_report.json with each mesh's size in metres,
which the blockout uses for scale.
"""
import json
import os
import re

import unreal

FAB_SRC = os.environ.get("FAB_SRC", "/workspace/fab/src")
MESH_EXT = (".fbx", ".obj", ".glb", ".gltf")
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def mesh_files(folder):
    out = []
    for root, _, files in os.walk(folder):
        for f in sorted(files):
            if f.lower().endswith(MESH_EXT):
                out.append(os.path.join(root, f))
    # Keep the highest detail only: drop LOD1 and coarser where a folder carries them.
    return [p for p in out if not re.search(r"_lod[1-9]", os.path.basename(p).lower())]


def import_folder(name, files):
    dest = f"/Game/Fab/{name}"
    tasks = []
    for path in files:
        t = unreal.AssetImportTask()
        t.filename = path
        t.destination_path = dest
        t.automated = True
        t.replace_existing = True
        t.save = False
        tasks.append(t)
    tools.import_asset_tasks(tasks)
    meshes = []
    for p in eal.list_assets(dest, recursive=True, include_folder=False):
        a = eal.load_asset(p)
        if isinstance(a, unreal.StaticMesh):
            ns = a.get_editor_property("nanite_settings")
            ns.enabled = True
            a.set_editor_property("nanite_settings", ns)
            b = a.get_bounding_box()
            size = b.max - b.min
            meshes.append({"asset": p.split(".")[0], "size_m": [round(size.x / 100, 3), round(size.y / 100, 3), round(size.z / 100, 3)],
                           "tris_lod0": a.get_num_triangles(0)})
    eal.save_directory(dest, only_if_is_dirty=False, recursive=True)
    return meshes


report_path = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "import_report.json")
report = json.load(open(report_path)) if os.path.exists(report_path) else {}

for name in sorted(os.listdir(FAB_SRC)):
    folder = os.path.join(FAB_SRC, name)
    if not os.path.isdir(folder) or (name in report and (report[name].get("meshes") or report[name].get("skip"))):
        continue
    files = mesh_files(folder)
    if not files:
        report[name] = {"meshes": [], "note": "no mesh files (surface or atlas: textures only)"}
        continue
    unreal.log(f"ANTIMONY_IMPORT start {name}: {len(files)} file(s)")
    try:
        report[name] = {"files": [os.path.relpath(f, folder) for f in files], "meshes": import_folder(name, files)}
        unreal.log(f"ANTIMONY_IMPORT done {name}: {len(report[name]['meshes'])} mesh(es)")
    except Exception as e:  # keep going; the report says what failed
        report[name] = {"meshes": [], "error": str(e)}
        unreal.log_error(f"ANTIMONY_IMPORT failed {name}: {e}")
    json.dump(report, open(report_path, "w"), indent=1)

unreal.log("ANTIMONY_IMPORT_ALL_DONE")
