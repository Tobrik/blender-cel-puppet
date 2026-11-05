# Kaguya × Fukkireta v4: goal & progress

**Whoever picks this up (a resumed session or the timer): read this file first, then continue from the first unchecked box.**
Update the boxes and the log as you go. The user's ask (2026-11-05): *"recreate the same as in the fukkireta reference, with kaguya,
the same clip + music, right now it is just repeating gif and is really pixelized, use blender mcp for creating it, and dont stop
until you get the perfect result"*.

## The goal
One video, `animation/kaguya/kaguya_fukkireta_v4.mp4`: Kaguya doing the Fukkireta head-bob for the **whole song**, built in Blender
(through the Blender MCP), with the **reference's own music** and timing.

Reference: `reference/fukkireta.mp4` (90.8 s, 960×720, 30 fps, AAC).

## Constraints
- **Go easy on the GPU and RAM** (the user runs another service alongside): modest texture sizes, no GPU upscalers (no Real-ESRGAN),
  low render samples, one render at a time, no giant data kept in Blender. Heavy image work goes in plain Python, in small batches

## Done means (acceptance)
1. [x] **Length and audio:** same length as the reference (90.8 s), and the reference's audio track, in sync
2. [x] **The bob matches:** the head's tilt, sway and dip follow the reference frame by frame (measured from the reference, not guessed), including the still start and end
3. [x] **Lip-sync:** the mouth opens and closes when Teto's does (closed smile / small open / wide open / grin), measured from the reference
4. [x] **Blinks** where the reference blinks (it never blinks)
5. [x] **Crisp:** rendered at full resolution (1440×1080, 4:3 like the reference), the art used 1:1, no pixel specks, no jaggies, no tearing or shards when she leans
6. [x] **Looks like Kaguya, posed like Teto:** upright, facing front, head filling the frame, bust crop, the body nearly still, hair and ribbon trailing the head
7. [x] **Background:** the reference's flat salmon pink with the big soft white outline motifs (scrolling like the reference)
8. [x] **Same animation rate as the reference** (held drawings, measured)
9. [x] **Reviewed:** the final MP4 compared side by side with the reference (contact sheets at the same timestamps), with no obvious fault left

## Plan (tick as done)
- [x] A. Analyse the reference → `v4/analysis/` (`track.py`, `faces.py`, `timeline.json`, `bg_plate.png`)
- [x] B. Art → `v4/parts.py` (cut into layers) + `v4/mouths.py` (lip-sync mouths) → `v4/parts/*.png`
- [x] C. Rig in Blender → `v4/kaguya_v4.py` (`build()` in the open Blender through the MCP; scene "Kaguya Fukkireta v4",
      saved as `v4/kaguya_v4.blend`). Verified: pose + mouth match `timeline.json` on all 2703 frames
- [x] D. Background (scrolling baguette tile, `parts/tex/bg_tile.png`)
- [x] E. Render 1440×1080 at 30 fps with the reference audio → `animation/kaguya/kaguya_fukkireta_v4.mp4`
      (background render: `blender -b v4/kaguya_v4.blend -S "Kaguya Fukkireta v4" -a`, ~0.13 s/frame, ~6 min, log in `v4/checks/render.log`)
- [x] F. Review against the reference (`v4/analysis/review.py`, `compare.py`), fixed, passes
- [x] G. Tell the user, delete the timer (CronDelete), update `animation/fukkireta-notes.md`

**Status: v4.3 done (2026-11-05), output `animation/kaguya/kaguya_fukkireta_v4_3.mp4` (earlier: `_v4_2`, `_v4_1`, `_v4`).** If the user asks for changes, edit the scripts, run parts.py → mouths.py → pack.py → neck_shade.py (plain Python),
then `build()` + `save()` in Blender through the MCP, and the background render command above.

## v4.3: the chin's shadow follows the head + a clean jaw corner (started 2026-11-05)
The user on v4.2 (five close-ups of the chin and neck): *"sent you some screenshots with problems you need to work on them"*.
Found: (1) the shadow under the chin is painted on the neck for the drawing's tilted head (a diagonal band); once she's
stood up / tilted / turned it stayed put, so one side of the neck was lit right up to the jaw; (2) a black spike at the right
jaw corner: the drawing's ink pool where the jaw line meets the neck's outline rode on the head, and the head's turn
(`yaw_dx`) slides the jaw corner up to ~45 px off the neck in the left leans; (3) small steps / specks in the neck's right
outline where the painted part met the art's line and where the collar line joins it.

Done means:
1. [x] **Shadow follows the head:** `neck_shade.py` re-shades the neck for each of the 30 frame poses (texel → the neck's
   bend → the screen → back through the head's transform, with its turn → in shadow above `SHADOW_EDGE`, the drawing's
   shadow edge), one tile each in `parts/tex/neck_atlas.png` (3228x3780); the neck's material picks the tile by its
   keyed `pose` property. Away from the lines the skin is re-flattened to the lit tone (no ghost of the old edge). The
   neck layer reaches down into the V to y 960 (with the body), so the shadow (lowest at y 940) never meets its edge
2. [x] **Jaw corner:** the head is cut along the jaw line's own lower edge (`JAW`), the ink pool (`JAW_POOL`) is neck
   skin + the neck's outline running on up under the jaw: no spike, whatever the head does
3. [x] **Neck's right outline:** re-measured (`NECK_LINE_R`), repainted as one line from under the jaw to the collar's curl
   (`JOINT_R`), overlapping the art's line at both ends; the collar line's joint is no longer notched out of the neck
4. [x] **Rendered + reviewed:** `kaguya_fukkireta_v4_3.mp4` (2724 frames, 90.8 s, 8 Mbps + AAC, log
   `v4/checks/render_v43.log`); the neck on all 24 cycle frames from the MP4, review sheet vs the reference
   (`v4/checks/review_v43.png`: poses + mouths match), before/after `v4/checks/before_after_v43.png`

## v4.1: crisp art + a clean neck (started 2026-11-05)
The user on the v4 render: *"the picture itself is really pixely right now, and there is the problem with the neck ... work with it
untill you wont get the perfect result, mainly on the left side"*. Found: the source art (982x1412, soft, JPEG-like noise) shown
1:1 and H.264 at ~3 Mbps; on the left of the neck a pink hole, collar-line "hooks" riding on the lock, a grey smear, a broken
neck outline; on the right, torn lock edges and ribbon cut lines.

Done means:
1. [x] **Clean art:** `v4/art/reference_2x.png` = reference.png through Real-ESRGAN x4plus anime 6B on the CPU (`v4/upscale.py`,
   4 threads, ~75 s), Lanczos to 2x. Layers cut at 2x (`parts.py`, S = 2), textures 2x
2. [x] **Locks cut on their traced outlines** (LOCK_L / LOCK_R measured row by row on the 2x art): no collar line, ribbon stripe
   or neck line moves with the hair; lock tips sharp, no torn edges
3. [x] **Neck:** own outline on both sides (visible + painted under the jaw / hair), its base moves with the body
   (NECK_FADE 780-832) so it never slides off the V-line; no hole, no smear, no light slivers in any pose. The lapels and the
   dress are a separate layer in front of the neck (`body_front`), so the neck slides under the V edges instead of over them
4. [x] **Under the locks:** collar back grey, the lapel's shadow band, the white lapel and the collar lines painted in cleanly;
   ribbons' stripes continued under the hair (directional fill), clean hidden edges
5. [x] **Render/encode:** sharp at 1440x1080 (texture lookup "Closest" on 2x textures + 16 AA samples: sharper than
   Linear), H.264 CRF 14 preset BEST, no blocking → `animation/kaguya/kaguya_fukkireta_v4_1.mp4`
6. [x] **Reviewed:** all 10 poses zoomed on both sides of the neck (stills and the MP4), review sheet vs the reference (30
   moments), before/after crops at 1:1 (`v4/checks/before_after_neck.png`)

## v4.2: a connected neck + smoother motion (started 2026-11-05)
The user on v4.1 (two left-lean screenshots): *"it feels like the neck dislocates and leans a little bit more left than to
right, and can you make it a little smoother, good work with pixealation tho"*. Found: Teto's head slides 55-150 px
sideways while her body barely moves (her neck is hidden under her hair). Kaguya's neck shows for only ~50-80 px, and v4.1 bent it
in 52 px (NECK_FADE 780-832, a smoothstep): a sideways jog in the right outline just under the jaw. On the right leans
the jaw covers that spot, so only the left leans showed it. Also, she was stood up around the chin, which left the head
6.5 px left of the neck at rest (left leans slid 44-62 px vs 31-49 to the right).

Done means:
1. [x] **Head centred on the neck:** stood up around the top of the neck (`NECK_TOP` 511,785), not the chin
2. [x] **Shoulders follow the head a little:** `BODY_FOLLOW` 0.45 of the head's slide at the top of the neck, on top of
   Teto's tie sway (body ±45 px instead of ±26), so the neck shears half as much
3. [x] **The neck bends evenly:** `NECK_BEND` linear from the head at y 740 to the body where it meets the collar (800 on
   the left, 848 on the right): straight outlines, the collar joints stay put
4. [x] **Left collar pocket:** the neck's hidden outline under the thin strand runs into the V edge at a point
   (`NECK_LINE_L`, `NECK`, `COLLAR_BACK` in parts.py), so the collar's back shows as a wedge, not a grey "bubble"
5. [x] **Smoother:** a pose on every frame at 30 fps: each drawing's pose on its own reference frame, in-betweens
   between them (periodic monotone cubic through the 10 poses, `frame_poses()`), springs run per frame; 30 shape keys
   (24 cycle frames + 6 for the 3 irregular drawings); mouths still switch per drawing
6. [x] **Rendered + reviewed:** `animation/kaguya/kaguya_fukkireta_v4_2.mp4` (2724 frames, 90.8 s, H.264 8 Mbps + AAC,
   4.5 min, log `v4/checks/render_v42.log`); neck both sides on all 24 cycle frames from the MP4, review sheet vs the
   reference (`v4/checks/review_v42.png`, 30 moments: poses + mouths match), before/after `v4/checks/before_after_v42.png`

Checked on the way with `scratchpad/art/rigsim.py` (the rig's own vertex positions rasterized in plain Python, matches
Blender within ~2/255) and Blender stills. The v4.1 scripts and parts are in `v4/old_v41/`.

## What the analysis found (the facts the rig is built on)
- 2703 video frames at 30 fps (90.1 s), audio 90.8 s. Drawings change on a 2-2-2-3-3 frame rhythm (12.5 drawings/s)
- **The bob is a fixed 10-drawing cycle** (24 frames = 0.8 s = 2 beats at 150 BPM), repeated for the whole song, from frame 0.
  One drawing is skipped at 60.9 s (the cycle shifts by one there); `timeline.json` has the right pose for every drawing
- Per half-cycle the head **snaps** to one side on the beat (tilt ±17.3°, turn ~19°, eyes 115 px sideways + 45 px down,
  in Teto px), then settles back over 4 drawings and snaps to the other side. The tie (body) sways ±20 px with it
- **Mouths:** 6 types (CLOSED 259, TINY 147, O 153, A 240, E 122, GRIN 198 drawings), classified per drawing
- **No blinks** anywhere in the clip (every eye crop is open)
- **Background:** flat #FEC1BC pink, soft white baguette outlines on a ~280×285 px grid (tilted ~30°), scrolling
  down-right at (0.254, 0.182) px per frame (ref px). I keep the baguettes (it's "the same clip"); hearts would be a one-line swap
- Kaguya's reference: iris centres (494.0, 482.4) and (742.2, 566.1) → eye-line tilt 18.6°, eye distance 262 px
  (Teto's is 200.4 → scale K = 1.307). Her face is turned a little to the viewer's right in the drawing

## How v4 is built
- `parts.py`: reference.png → RGBA layers (ribbon_L, ribbon_R, body, neck, head, mouth_closed), every hidden area painted in,
  soft edges un-mixed against white (no fringes). Lock tips are cut out of the collar with hand-traced collar lines
- `mouths.py`: TINY / O / A / E / GRIN drawn as vector shapes (Kaguya's palette), turned to the head's tilt
- `kaguya_v4.py` (Blender): textured grid meshes, one shape key per cycle pose (head straightened upright, tilt/turn/sway
  from Teto, lock + ribbon follow-through), mouths switched per drawing, scrolling background, the reference audio, MP4 out

## Log
- 2026-11-05: started v4. Read the v1–v3.2 notes. The full reference clip is new; it has lip-sync, blinks and karaoke subtitles (the uploader's overlay, not part of the animation, so they're left out)
- 2026-11-05: analysis done (A), layers + mouths done (B). The user asked to go easy on GPU/RAM (noted above)
- 2026-11-05: rig built (C, D). Fixed on the way: keys must be CONSTANT (set on the F-curves; the preference doesn't
  apply to custom-property keys in 5.2), the right lock / ribbons mustn't undo the stand-up rotation (only the left
  lock), the jaw cut is measured (not guessed), every seam pixel belongs to some layer (round-trip test in parts.py:
  mean error 0.0012), edges un-mixed on the outline's outside only. Sound strip starts at frame 0 (the reference's
  video starts 1/30 s after its audio). First full render started
- 2026-11-05: final render (2724 frames, 90.8 s, H.264 + AAC; audio/video offset identical to the reference, measured by
  cross-correlation). Extra fixes before it: texture colors bled into transparent pixels (a dark seam across the neck),
  hair edges keep the line color (light specks), painted-in areas softened (streaks), ribbons swing less and their hidden
  part has an outline. Review sheet (30 moments) and a full cycle at full size: matches, no faults. Known tiny leftover:
  a slightly hooked right-lock tip on one drawing. Timer deleted
- 2026-11-05 (v4.1): The user: still pixely, and the neck is wrong, mainly on the left. Upscaled the art (CPU, Real-ESRGAN anime),
  re-cut everything at 2x on traced outlines (row-by-row measurements of the 2x art), new `body_front` layer, neck with its own
  outline + base moving with the body, jaw cut re-measured at the right corner (the jaw's dark wedge goes to y 795), locks
  swing as a whole below the jaw (no bent tips), lapel shadow band painted with a soft edge. Old v4.0 scripts + parts in
  `v4/old/`. Checked every pose on stills, both neck sides. Timer c3141bee set. Full render started
- 2026-11-05 (v4.1): rendered `kaguya_fukkireta_v4_1.mp4` (2724 frames, 90.8 s, H.264 6.2 Mbps + AAC, 4.5 min, log
  `v4/checks/render_v41.log`). Review sheet + neck-cycle sheets from the MP4: matches, no faults. **v4.1 done**, timer deleted
- 2026-11-05 (v4.2): The user: the neck "dislocates and leans a little more left than right", "make it a little smoother".
  Head stood up around the neck top, shoulders follow 45 % of the head's slide, neck bent linearly to the collar joints,
  the left collar pocket repainted as a wedge, a pose on every frame (in-betweens). Tried 8 neck rigs in `rigsim.py`
  first. Rendered `kaguya_fukkireta_v4_2.mp4`, reviewed: **v4.2 done**
- 2026-11-05 (v4.3): The user's chin/neck close-ups: the chin's shadow didn't follow the head, a black spike at the right jaw
  corner. Shadow baked per frame pose (`neck_shade.py`, neck atlas), jaw-corner ink pool repainted as neck, the neck's
  right outline repainted as one line. Rendered `kaguya_fukkireta_v4_3.mp4`, reviewed: **v4.3 done**
