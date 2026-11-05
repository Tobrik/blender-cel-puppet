# Blender + MCP notes

Tested on Blender 5.2 with the Blender MCP add-on (tools: `get_addon_status`, `get_scene_info`, `execute_blender_code`,
`look`). The functions named here are in `examples/kaguya-fukkireta/kaguya_v4.py`; copy them rather than rewriting.

## Driving Blender through the MCP

- Start with `get_addon_status` and `get_scene_info`. Build in **its own scene** (`clear_scene()` removes only that
  scene and its data), so the user's other work in the open file is untouched.
- Each `execute_blender_code` call runs in a fresh namespace. Pattern for every call:
  ```python
  PROJECT = r"C:/path/to/project"
  exec(open(PROJECT + "/kaguya_v4.py", encoding="utf-8").read())
  sc = build(); print(save())          # or: still(917, PROJECT + "/checks/f917.png", percent=100)
  ```
- Print what you need to know (counts, mismatches, file paths); keep calls small. Use `look` (small `max_size`) or
  render a still and read the PNG to see results.
- Read enum identifiers instead of hardcoding them; set `scene.render.engine` in a `try/except TypeError`
  (`BLENDER_EEVEE` vs `BLENDER_EEVEE_NEXT` across versions); look shader nodes up by type, not name.

## Building blocks (in the example)

| Function | What it does / gotcha |
|---|---|
| `grid(box, cell)` | a layer's quad grid over its texture box (reference px), UVs 0..1 over the box |
| `make_mesh_object` | mesh at depth y (further = drawn first); camera looks along +y, orthographic, `ortho_scale = RES[0] / PX` |
| `emission_material` | unlit: Emission + Transparent mixed by the texture's alpha, `surface_render_method = "BLENDED"`; several images → picked by an object property (Attribute node, OBJECT) through COMPARE + Mix nodes |
| `atlas_material` | one atlas of per-pose tiles; MULTIPLY_ADD / FLOOR math on the UVs picks the tile from the object's `pose` property (one texture sampler, no 30-image shader) |
| `add_pose_keys` | one shape key per frame pose, each driven by `"1.0 if pose == k else 0.0"` from the controller (check `drv.is_simple_expression`) |
| `keyframes` | keys a custom property per frame / per drawing and sets **CONSTANT** on the keyframe points (custom-property keys come in LINEAR) |
| `fcurves_of` | F-curves of an ID under layered actions (slot → channelbag), with the old `action.fcurves` fallback |
| `image` | `bpy.data.images.load(check_existing=True)` + `reload()` (else an edited PNG keeps its old pixels), alpha STRAIGHT |
| `add_background` | textured plane; Mapping node location driven by `frame * speed` (simple expressions) to scroll |
| `setup_render` | EEVEE, Standard view transform, 16 render samples, no shadows/AO/bloom, `filter_size` 1.0 |
| `setup_output` | FFmpeg MPEG-4 / H.264, `constant_rate_factor = "CUSTOM"`, `custom_constant_rate_factor = 14`, preset BEST, AAC 192k |
| `add_audio` | the reference's audio as a sound strip (`strips` in 5.x, `sequences` before), at the frame that matches the video |
| `still` | renders one frame to PNG (optionally only some layers, `only=[...]`), then restores the video output |

Texture lookup: "Closest" on 2x textures with 16 jittered AA samples was visibly sharper than "Linear" in the example;
compare both on a zoomed still for new art.

## Rendering

- Save first (`save()` writes a copy of the open file), then render in the background so the UI stays free:
  `"<binary_path>" -b "<project>/kaguya_v4.blend" -S "<scene name>" -a > checks/render.log 2>&1`
  (`render_cmd()` prints it). Run it as a background shell command and wait for it to finish; don't poll in a loop.
- One render at a time. ~0.1 s per 1440×1080 frame for this kind of scene on EEVEE.
- Check the result: `ffprobe -v error -show_entries stream=codec_name,width,height,nb_frames,duration,bit_rate -of
  compact out.mp4`. Frame count = scene frames; audio duration = the reference's.

## Memory / GPU budget (when the user needs their machine)

Textures: crop layers to their content, 2x is enough (the example's biggest is the head at 1640×2018); the neck atlas
of 30 tiles is ~50 MB in RAM. Heavy image work (upscaling, cutting, baking) runs in plain Python on the CPU, in small
tiles, with a few threads. Don't keep big arrays alive inside Blender.
