# Symptoms → causes → fixes

Every row was a real complaint or a real bug on the way from a looping GIF to the final clip. When the user describes
a problem in their words ("pixely", "the neck dislocates"), find the row, then confirm the cause on a zoomed frame
before you change anything.

## What the user sees

| The user says / you see | Cause | Fix |
|---|---|---|
| "just a repeating gif" | a short invented loop, no audio | analyse the whole reference clip, build the timeline from it, use its audio |
| "really pixely", soft, blocky | the soft / JPEG-noisy source shown 1:1, H.264 at ~3 Mbps | CPU anime upscale (`upscale.py`), cut at 2x, 2x textures, "Closest" lookup + 16 AA samples, CRF 14 preset BEST (~6–8 Mbps) |
| hard shape edges look traced / jagged | vector-tracing the art | don't trace into strokes; use the (upscaled) pixels as textures on meshes |
| "the neck dislocates" | the head slides further than the body and the neck bends in a short strip under the jaw (a jog in the outline) | bend linearly over the neck's whole visible length to the collar joints (`NECK_BEND`), shoulders follow a share of the head's slide (`BODY_FOLLOW`) |
| "leans more to one side than the other" | stood up around the chin (head off-centre on the neck), lopsided reference poses, the art's own tilt | pivot at the neck top (`NECK_TOP`), symmetrise poses p / p+n/2, check the slide left vs right numerically |
| one side of the neck lit up to the jaw | the chin's cast shadow is painted on the neck for the drawing's head and stays put | bake the neck's shading per frame pose so the shadow follows the head (`neck_shade.py`) |
| black spike / thorn at the jaw corner | the drawing's ink pool where the jaw line meets the neck line rides with the head (the turn slides the jaw off the neck) | cut the head along the jaw line's own lower edge, repaint the pool as neck (`JAW_POOL`) |
| "hooks" / collar lines moving with the hair | locks cut by colour, so other parts' line pixels are on the hair layer | trace the locks' outlines; trim lines only where they show beside a lock; keep other parts' dark pixels (`keep_dark`) |
| grey "bubble" / "leaf" beside the neck when hair swings away | a painted-in hidden region with an unnatural shape gets revealed, or a joint gets squeezed | paint the pocket as a wedge into the V; pin the joint to the body above it |
| a notch / tick / step in an outline | painted line ≠ the art's line where they meet; a joint trimmed out of one layer | re-measure the line on the art, repaint the stretch as one line, overlap the painted line 1.5 px into the art's |
| stray dark specks next to a line | another part's line pixels caught in an edge/ring mask | exclude repainted zones from the ring/edge masks; drop isolated dark pixels |
| white fringe around a moving part | anti-aliased edge pixels mixed with the white background | un-mix edges against what's behind them (`matte`/`unmix`) |
| dark seam across a part | texture filtering pulls in the black of transparent texels | bleed colours into transparent texels when packing |
| pink hole / see-through slit between parts | some foreground pixel belongs to no layer | the "foreground px in no layer" check; dilate covers by 1–2 px under the front part |
| ribbon / tail cut lines, streaks under the hair | hidden part filled with flat or smeared colour | directional fill along the measured stripe direction, then a light soften; draw the hidden part's outline |
| bent / hooked hair tips when swinging | the swing weight varies across the tip | below the jaw, swing the whole strand with one weight |
| the tuft / a part "dislocates" for a few frames | a part split off the head where it should be one piece | keep it on the head layer |
| motion feels choppy | the reference's held drawings (12.5/s) shown as is | in-betweens on every frame (PCHIP through the keys, keys on their frames); springs per frame |
| the user still sees the old problem | their player cached the old file | a new file name for every version (`_v4_1`, `_v4_2`, ...) |

## Blender / pipeline bugs

| Symptom | Cause | Fix |
|---|---|---|
| held frames show in-between poses, wrong mouths | keys on custom properties come in LINEAR (Blender 5.x ignores the preference for them) | set CONSTANT on the F-curves' keyframe points after inserting |
| `action.fcurves` missing (Blender 4.4+) | layered actions / slots | get the channelbag for the slot (`anim_utils.action_get_channelbag_for_slot`), see `fcurves_of()` |
| changed textures don't show up | Blender reuses the loaded image | `img.reload()` after `bpy.data.images.load(check_existing=True)` |
| the MCP call can't find `build` | every MCP call starts with an empty namespace | set `PROJECT`, `exec()` the script again in each call |
| drivers don't run in the background render | Python-expression drivers need auto-run | keep driver expressions "simple" (`drv.is_simple_expression`), or key properties directly |
| audio a frame off | the reference's video starts 1/30 s after its audio | sound strip at frame 0; reference frame k = scene frame k + 1; check by cross-correlating the audio |
| colours darker than the art | view transform / lighting | Standard view transform, emission shaders, film not transparent |
| a still's settings leak into the render | `still()` changes the output format | restore the FFmpeg output settings after each still |
| the GPU / RAM is busy with something else | the user runs other services | upscale on the CPU with a few threads, small textures, render once, in the background, no UI renders in a loop |

## Process lessons

- **Measure, don't guess.** Every number in the rig (tilt, slide, dip, holds, mouths, scroll speed) comes from the
  reference; when a joint looks wrong, print the displacements per pose instead of eyeballing.
- **Look where the user looks.** They zoom into joints (neck, jaw, collar, hair tips) and compare left vs right leans.
  Check both sides on every frame of a cycle, not just the key poses.
- **Simulate before you render.** A plain-Python rasterizer of the rig's own vertices (`rigsim.py`) tests a variant on
  24 frames in seconds, with no GPU and no Blender state to clean up.
- **Fix the cause, not the frame.** A spike on one frame is a joint that separates on every frame; find the rule.
- **One render at a time, in the background,** with a log; check the file with ffprobe before reviewing.
- **Long jobs: a goal file + a timer.** Write the acceptance list and progress to a `GOAL.md` and set a check-in timer,
  so a resumed session (or the timer) continues from the first unchecked box (see `goal-template.md`).
