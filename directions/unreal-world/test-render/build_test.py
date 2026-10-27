"""Build a tiny test level, a 1-frame sequence and an MRQ preset, then save them.
Run headless: UnrealEditor-Cmd TestRender.uproject -ExecutePythonScript=build_test.py -unattended"""
import unreal

MAP = "/Game/TestMap"
SEQ = "/Game/TestSeq"
PRESET = "/Game/TestPreset"

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assets = unreal.AssetToolsHelpers.get_asset_tools()

les.new_level(MAP)

def spawn(cls, loc=(0, 0, 0), rot=(0, 0, 0)):
    return eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))

# Ground, a sphere, a cube.
for path, loc, scale in [
    ("/Engine/BasicShapes/Plane", (0, 0, 0), (40, 40, 1)),
    ("/Engine/BasicShapes/Sphere", (0, 0, 100), (2, 2, 2)),
    ("/Engine/BasicShapes/Cube", (250, 150, 75), (1.5, 1.5, 1.5)),
]:
    a = spawn(unreal.StaticMeshActor, loc)
    a.static_mesh_component.set_static_mesh(unreal.load_asset(path))
    a.set_actor_scale3d(unreal.Vector(*scale))

sun = spawn(unreal.DirectionalLight, (0, 0, 500), (0, -20, 40))  # roll, pitch, yaw
sun.light_component.set_intensity(8)
sun.light_component.set_atmosphere_sun_light(True)
spawn(unreal.SkyAtmosphere)
sky = spawn(unreal.SkyLight)
sky.light_component.set_editor_property("real_time_capture", True)
sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
fog = spawn(unreal.ExponentialHeightFog)
fog.component.set_editor_property("enable_volumetric_fog", True)
spawn(unreal.VolumetricCloud)

cam = spawn(unreal.CineCameraActor, (-700, -300, 250), (0, -12, 25))

# One-frame level sequence with the camera bound to a camera cut track.
seq = assets.create_asset("TestSeq", "/Game", unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
seq.set_display_rate(unreal.FrameRate(24, 1))
seq.set_playback_start(0)
seq.set_playback_end(1)
binding = seq.add_possessable(cam)
cut = seq.add_track(unreal.MovieSceneCameraCutTrack).add_section()
cut.set_range(0, 1)
cut.set_camera_binding_id(seq.get_binding_id(binding))

# MRQ preset: deferred render, PNG, 1920x1080, a few temporal samples.
preset = assets.create_asset("TestPreset", "/Game", unreal.MoviePipelinePrimaryConfig, None)
preset.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
preset.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
out = preset.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
out.output_resolution = unreal.IntPoint(1920, 1080)
out.output_directory = unreal.DirectoryPath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir() + "MovieRenders"))
out.file_name_format = "test_{frame_number}"
aa = preset.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
aa.spatial_sample_count = 1
aa.temporal_sample_count = 8
aa.override_anti_aliasing = True
aa.engine_warm_up_count = 32
aa.render_warm_up_count = 32

# Second preset: the path tracer (the final stills depend on it working on Vulkan).
pt = assets.create_asset("TestPresetPT", "/Game", unreal.MoviePipelinePrimaryConfig, None)
pt.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPass_PathTracer)
pt.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
pto = pt.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
pto.output_resolution = unreal.IntPoint(1920, 1080)
pto.output_directory = out.output_directory
pto.file_name_format = "test_pathtraced_{frame_number}"
pta = pt.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
pta.spatial_sample_count = 64  # path tracer samples per pixel
pta.temporal_sample_count = 1
pta.override_anti_aliasing = True

les.save_current_level()
unreal.EditorAssetLibrary.save_loaded_asset(seq)
unreal.EditorAssetLibrary.save_loaded_asset(preset)
unreal.EditorAssetLibrary.save_loaded_asset(pt)
unreal.log("ANTIMONY_TEST_BUILD_OK")
