"""Export each top-level object (with its children) of a .blend to its own FBX, for assets that come only as .blend.

  blender -b --factory-startup --disable-autoexec <file.blend> -P blend_to_fbx.py -- <out_dir>
"""
import os
import sys

import bpy

out = sys.argv[sys.argv.index("--") + 1]
os.makedirs(out, exist_ok=True)
# Packed textures go next to the FBX files so the importer finds them.
tex = os.path.join(out, "textures")
os.makedirs(tex, exist_ok=True)
for img in bpy.data.images:
    if img.packed_file:
        img.filepath_raw = os.path.join(tex, bpy.path.clean_name(img.name).replace("_png", "") + ".png")
        img.save()
roots = [o for o in bpy.context.scene.objects if o.parent is None and o.type in {"MESH", "EMPTY"}]
for root in roots:
    bpy.ops.object.select_all(action="DESELECT")
    stack = [root]
    while stack:
        o = stack.pop()
        # Highest detail only: skip the coarser LODs that sit under the same root.
        if not any(f"_LOD{i}" in o.name for i in (1, 2, 3, 4)):
            o.select_set(True)
        stack.extend(o.children)
    if not any(o.type == "MESH" for o in bpy.context.selected_objects):
        continue
    loc = root.location.copy()
    root.location = (0, 0, 0)  # each tree at the origin, so it scatters from its own base
    name = "".join(c if c.isalnum() or c in "-_" else "_" for c in root.name)
    bpy.ops.export_scene.fbx(filepath=os.path.join(out, f"{name}.fbx"), use_selection=True, object_types={"MESH", "EMPTY"},
                             apply_scale_options="FBX_SCALE_UNITS", path_mode="ABSOLUTE", embed_textures=False, mesh_smooth_type="FACE")
    root.location = loc
    print("exported", name)
