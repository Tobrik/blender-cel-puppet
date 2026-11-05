# The pipeline, phase by phase

Read the phase you're in. Every phase ends with a check you can see. File names refer to `scripts/` (reusable tools) and
`examples/kaguya-fukkireta/` (the full working project these notes come from: Kaguya doing the Fukkireta head-bob).

Contents: A. Reference analysis · B. The art · C. The rig (math) · D. The Blender build · E. Render · F. Review

---

## A. Reference analysis: measure everything

Goal: a `timeline.json` that says, for every frame of the reference, which pose and which mouth is on screen. With that
file the rest is mechanical. Guessed motion is what made the early versions look like "a repeating gif".

1. **Probe:** `ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames,duration,start_time
   -of compact reference.mp4`. Note the fps, the frame count, and the audio duration (it can be longer than the video).
   Compare the streams' `start_time`: in the Fukkireta upload the video starts 1/30 s after the audio, so the sound strip
   goes at frame 0 and reference frame k is scene frame k + 1.
2. **Drawing rate:** `python scripts/drawing_rate.py reference.mp4 --crop <the character's box>`. Anime is rarely on
   ones: Fukkireta is held 2-2-2-3-3 (12.5 drawings/s, 24 frames per 10-drawing cycle). Crop out subtitles / overlays,
   or they show up as fake drawing changes.
3. **Track features on every frame:** something rigid on the head (both irises: centre, size, the eye line's angle) and
   something on the body (a tie, a collar point). `examples/.../analysis/track.py` finds the irises as saturated blobs by
   HSV and pairs them; adapt its thresholds to the reference's character. Eye separation shrinking = the head turning.
4. **Find the cycle:** group the drawings (first frame of each hold) into poses. Dances / bobs repeat a fixed cycle;
   `faces.py` assigns every drawing to the nearest of the cycle's poses (seeded from the first cycle), so skipped or
   doubled drawings (Fukkireta skips one at 60.9 s) come out right. Store per pose: eye midpoint x/y, angle, separation,
   body x/y ("canon").
5. **Symmetrise:** a left/right bob has pose p and p + n/2 as mirror images. Average them (x mirrored, y shared, angle
   negated): real references are a few px lopsided, and the user *will* notice a lean that's bigger on one side.
6. **Mouths:** crop the mouth (aligned to the eyes) per drawing and classify (closed / small / O / A / E / grin). A
   nearest-template classifier on the crops is enough; check a contact sheet of each class.
7. **Blinks, extras:** check the eye crops for closed eyes. Leave out the uploader's overlays (karaoke subtitles,
   watermark mascots); they're not part of the animation.
8. **Background:** sample its colour, measure the pattern's grid and the scroll speed (track one motif over 100 frames).

`timeline.json` format used by the example rig:
```json
{"fps": 30, "frames": 2703, "mouths": ["CLOSED", "TINY", "O", "A", "E", "GRIN"],
 "canon": [[x, y, angle_deg, eye_sep, tie_x, tie_y], ...],             // one per cycle pose
 "drawings": [{"start": 0, "hold": 2, "pose": 0, "mouth": "CLOSED"}, ...]}
```

## B. The art: one still → clean cel layers

The character comes from one still image (the user's drawing, a screenshot, an AI image). Best case: front-facing,
upright, bust crop, neck visible, nothing cut off. A tilted or turned head works (the example's was tilted 18.6° and
turned), but every degree of tilt you undo shows up later at the neck, so ask for a straighter image if one is possible.

1. **Upscale first** (if the source is soft or JPEG-noisy, which shows as "pixely" once it's on screen at full size):
   `python scripts/upscale.py art.png art_2x.png RealESRGAN_x4plus_anime_6B.pth 2 4`. CPU, tiled, ~75 s. The anime
   6B model keeps the shapes and cleans the lines and flats. Cut everything at 2x and keep textures at 2x.
2. **Decide the layers**, back to front. The example's: `ribbon_L, ribbon_R, body (only what's behind the neck: the V
   opening), neck, body_front (lapels / dress, in FRONT of the neck), head (+ hanging locks), mouth`. A part in front of
   a joint hides the joint's seam (the lapels hide where the neck goes into the collar).
3. **Cut on traced outlines, not by colour.** Colour masks put pieces of other parts' lines on the wrong layer (collar
   lines riding on a lock = "hooks"). Trace the outline row by row on the 2x art: print the dark runs (`L < 0.15`) per
   row/column in a window, read the line's edges off the numbers, and write the polygon a fraction of a px outside the
   line. `parts.py` has all of it: `JAW`, `LOCK_L/R`, `NECK`, `COLLAR_TOP`, `VLINE_L/R`... with comments.
4. **Paint in everything that can be uncovered:** the neck under the jaw (with its outline: `NECK_LINE_L/R` drawn only
   where hidden), the collar's back and the lapels under the hair, ribbon stripes under the hair (`dir_fill` along the
   measured stripe direction). Shapes that get revealed have to look intended: a collar pocket is a wedge into the V,
   not a round bubble.
5. **Edges:** un-mix anti-aliased edges against what's behind them (`matte()` / `unmix()`), so no white fringe rides
   along. Give cut edges through ink the polygon's own anti-aliased coverage (`poly_cover`).
6. **Junction ink:** where two parts' lines meet, the art often has an ink pool. If the parts move apart, the pool
   becomes a spike. Cut the moving part along its own line's edge and repaint the pool as the other part.
7. **Checks** (`parts.py` prints both): the round trip (all layers stacked over white vs the art: mean error ~0.002,
   only the deliberate repaints differ) and "foreground px in no layer" (should be a few hundred stray px at most).
   Look at each layer alone over a loud colour (`preview_*.png`).
8. **Mouth sprites:** the closed mouth cut from the art, the others drawn as vector shapes in the character's palette,
   turned to the drawing's head tilt (`mouths.py`).
9. **Pack** (`pack.py`): crop each layer to its content (+4 px), record the boxes in `parts.json`, and **bleed** colours
   into transparent texels (or filtering pulls in black: dark seams).

## C. The rig (pure numpy, before Blender)

Write the rig as plain functions on vertex arrays (reference px), so the same code builds Blender's shape keys and runs
in `scripts/rigsim.py`.

- **Scale:** K = the character's eye separation / the reference character's. Head motion = the reference's eye motion
  × K; body sway = the reference's body feature × K.
- **Stand up straight first** (if the art is tilted): rotate the head by −tilt around **the top of the neck** (the neck's
  centre at the jaw line), not the chin; a chin pivot leaves the head off-centre on the neck and every lean to one side
  looks bigger.
- **Pose:** head = rotate by the pose's roll around the eyes + move by the eye displacement. Any rigid motion is a
  rotation about *some* point; print where the head's jaw goes relative to the collar for every pose before you trust it.
- **Turn (yaw):** slide features on an ellipsoid head model (`yaw_dx`); the silhouette stays. Note it slides the jaw
  too (the example's jaw corner moves up to 45 px at 14°); anything attached to the jaw (shadow, neck outline junction)
  must cope.
- **Body follow:** if the reference's head slides far more than its body (Teto's neck is hidden by hair), give the
  shoulders a share of the head's slide (`BODY_FOLLOW` 0.45), or a visible neck has to shear too much.
- **Neck bend:** blend head transform → body transform *linearly* along the neck's whole visible length, ending exactly
  at the joints with the collar (`NECK_BEND`). A short smoothstep fade is a kink ("the neck dislocates").
- **Hanging parts** (locks, ribbons, tails): rotate around their root by a damped spring driven by the root's
  acceleration; weights ramp down the strand; below the jaw the whole strand swings (no bent tips).
- **Frame poses / smoothness:** the reference's drawings are keys; to make it smoother, put a pose on every frame:
  a periodic monotone cubic (PCHIP) through the cycle's keys at their own frames (each drawing still lands on its frame,
  no overshoot, flat at the turning points). Irregular drawings get their own in-betweens; mouths stay per drawing.
- **Cast shading follows its caster:** the shadow under the chin is painted on the neck but cast by the head. Bake the
  neck's shading per frame pose (`neck_shade.py`: texel → neck bend → screen → inverse head transform → in shadow above
  the drawing's shadow edge) into an atlas.

Try variants with `rigsim.py` (`--set NAME=VALUE`) on every frame pose, zoomed on the joints, before touching Blender.

## D. The Blender build (through the MCP)

`kaguya_v4.py` (`build()`, `still()`, `save()`, `render_cmd()`) is the template. What it does:
- Own scene, orthographic camera at 1 reference px = 1 output px, frame centred on the eyes (`SCREEN_EYE`).
- Each layer a grid mesh (cell 10–28 px) with its texture; unlit material (emission + transparent mix, alpha BLENDED),
  texture lookup "Closest" on 2x textures (the 16 AA samples filter it: sharper than Linear).
- One shape key per frame pose, driven by a controller's `pose` property (`"1.0 if pose == k else 0.0"`, a simple
  expression, so no Python driver/auto-run needed); the property keyed per frame with CONSTANT interpolation.
- Mouth: one object, 6 textures switched by its own keyed `mouth` property (Attribute node, OBJECT type).
- Neck atlas: one texture of per-pose tiles; shader math on the UVs picks the tile from the object's keyed `pose`.
- Background: a textured plane, tile repeated, scroll by drivers on a Mapping node.
- Sound strip at frame 0, FFmpeg H.264 (CRF 14, preset BEST) + AAC.
Verify after build: count drawings not on their pose (0), controller value vs the timeline on every frame (0
mismatches), then `still()` a few frames at 100 % and compare with rigsim's render of the same pose.

## E. Render

Save, then render in a separate background Blender so the UI stays free and only one render runs:
`"<blender.exe>" -b project.blend -S "<scene>" -a > render.log 2>&1` (run it in the background and wait for the
notification). The example: 2724 frames at 1440×1080 in ~4.5 min on EEVEE. Write every version to a new file name.
Check with ffprobe: frame count, duration, audio length, bitrate.

## F. Review (before telling the user it's done)

1. `scripts/review_sheet.py reference.mp4 render.mp4 review.png`: 30 moments side by side. Same pose, same mouth?
2. `scripts/cycle_sheet.py render.mp4 neck.png --start <a cycle's first frame> --crop <the joint> --zoom 0.5`:
   every frame of one cycle, in-betweens included, on each joint (both sides of the neck, the jaw corners, where hair
   meets the collar).
3. A before/after of whatever the user complained about, at their zoom, at the same frames
   (`compare.py` or a small crop script). Show it to them with the result.
