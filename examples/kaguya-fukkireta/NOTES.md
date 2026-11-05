# Fukkireta head-bob: notes 🎵

> Reference: the Kasane Teto "Fukkireta" head-bob (Lamaze-P, Nov 2010; the template that turned into the meme).
> Studied from a 91-frame Tenor GIF on 2026-11-04. Frames 0–23: `reference-frames.jpg`.

## Timing
- **10 fps**, every frame held for 100 ms (no doubles)
- **One full left → right → left cycle = 8 frames (0.8 s)**, so each swing is 4 frames (0.4 s)
- It loops the same cycle the whole time. Variation: **one blink** around frame 56

## The motion
- **The head tilts side to side** (a roll of about ±10–15°), with a small sideways shift and a slight turn of the face toward the lean
- **A small dip in the middle** of each swing, so the path is a "U" instead of a flat line
- **The hair lags (follow-through):** the twin drills swing out to the side, 1–2 frames behind the head, and swing wider than the head. The bangs shift a bit, and the ahoge flicks last
- **The body barely moves:** the shoulders and collar stay almost still, which sells the bob

## The look
- A bust close-up, square 1:1, with the head filling most of the frame and the top slightly cropped
- **The same soft closed-mouth smile** the whole time, eyes open, blushed cheeks
- A flat cel style: one base color plus one shadow tone, thin dark outlines that wobble a little between frames
- **Background:** flat pink with big soft white polka dots, static

## How I'd make it (Blender Grease Pencil)
1. Draw the character in layers: back hair / twintails, face + neck, eyes, bangs, ahoge, body
2. Draw the 4 key poses (left, passing, right, passing), then the in-betweens, for 8 drawings in a loop
3. Hair and the ahoge offset by 1–2 frames for the follow-through
4. Add a blink drawing, swap it in once per loop
5. Render 1:1 at 10 fps → a PNG sequence + an MP4 (Blender has ffmpeg built in)

## The character: Kaguya 🎀 (v1, 2026-11-04)
- **Script:** `kaguya/kaguya_fukkireta.py` (run in Blender: `build()`, then `render()`). It lives in its own Blender scene, "Kaguya Fukkireta"
- **Output:** `kaguya/kaguya_fukkireta.mp4` (12 s, 3 loops, 1080²), `kaguya/kaguya_fukkireta.gif` (40 frames at 10 fps), `kaguya/frames/` (PNGs)
- **Design:** black hair with a blue-ish shine, long sidelocks, the red ribbon peeking out at the back, sharp almond red eyes, blush, the dark Shuchiin dress with a red bow at the collar, and **hearts instead of polka dots** (Love is War)
- **Motion:** ±11° tilt around the chin, a "U" dip, the face turning a bit toward the lean, the sidelocks and ribbon tails trailing ~1.3 frames behind, a slight line wobble, and a blink at frames 26–28
- **Blender 5.2 gotcha:** fills are per stroke (`fill_id` > 0, `hide_stroke`), not the material's "show fill". Also turn off `use_grease_pencil_lights`, or the colors come out dark
- **No music** in the file. Add the song in an editor

## Kaguya v2: closer to the anime (2026-11-04)
- The user liked v1's style (*"lowkey your style is good"*) but wanted it closer to the anime, and generated a reference with **Nano Banana**
- **Script:** `kaguya/kaguya_fukkireta_v2.py` (reuses v1's machinery, replaces only the art). Blender scene "Kaguya Fukkireta v2"
- **Output:** `kaguya/kaguya_fukkireta_v2.mp4`, `kaguya/kaguya_fukkireta_v2.gif`, `kaguya/frames_v2/`
- **What changed:** bangs parted in the middle with the forehead showing, **the striped red ribbon hanging behind the head on both sides** (it swings a beat late), the tied tuft at the back, ears, thin brows, narrow almond eyes, a longer face with a pointed chin, almost no blush, cel shadows under the chin and the bangs, and **the white collar with a V and a red string bow**

## Kaguya v3: traced from the reference + a cel puppet rig (2026-11-04)
- The user on v2: the body stayed still, the shoulders were too broad, it looked like a cartoon, and *"the allignment like you are using shapes again"*. Asked me to *"set a goal"* and keep going until it matches the reference
- **The switch:** no more inventing her from coordinates. `kaguya/reference.png` (the user's Nano Banana image) is traced into strokes, the way animators clean up a key frame
- **Script:** `kaguya/kaguya_fukkireta_v3.py` (trace cache: `trace_cache.npz`). Blender scene "Kaguya Fukkireta v3". 4:5, 1080×1350
- **How:** 15 flat colors from the reference (k-means) → background = white connected to the border → the image cut into parts (body, neck, head, two "hangs" = lock + ribbon tail, the tuft) → each part painted in under the parts that cover it (fill colors spread, lines don't) → marching squares at 2× → ~4,300 even-odd fills per frame plus a back-paint
- **Rig:** the head tilts −18°…+2° around the neck, the neck stretches between head and body, the hangs and the tuft trail ~1 frame, and the body sways ±3° and bounces
- **Output:** `kaguya/kaguya_fukkireta_v3.mp4` (12 s), `kaguya/kaguya_fukkireta_v3.gif` (720×900, 10 fps), `kaguya/frames_v3/`
- **Lessons:** same-color regions across parts (hair = dress black) tear, so split by part *before* tracing. Light anti-aliased edge pixels must travel with their hair. White between strands is background
- **Known leftovers:** tiny scraps around the lock tips, visible only zoomed in. No blink (the trace has open eyes only)

### v3.1: standing straight + an even bob (2026-11-04)
- The user: the tuft *"dislocates"* for ~3 frames, she leans more to the right than the left, and she should *"stand straight"* like in the Fukkireta clip
- **Fixes:** the tuft is now part of the head (no seam). The reference leans **19.5°** (measured on the eye line), so she's straightened fully and bobs **±11° evenly** (8 frames, seamless loop). The camera is zoomed out so the tuft fits. The fill-in under the hair only spreads flat colors (no streaks). The ribbon's dark stripes are part of the ribbon. **Hand-painted patches** (the collar back, the hidden side of the neck) fill only pixels that something covers, so they're invisible at rest
- **Known leftovers:** small white collar shards by the right lock tip on the far-left lean. A **front-facing, upright reference** would remove these and match Fukkireta even closer
- **v3.2 (same day):** the user saw a frame with the old ribbon streaks (QuickTime was still showing the previous file) and *"the pixels"*. Light specks under 8 px² are dropped (dark ones under 3 px², since lines are made of small bits), and dark dots right next to a lock move with it. Output: `kaguya/kaguya_fukkireta_v3_1.mp4` / `.gif` / `frames_v3_1/`
- **v3.2, the anti-pixel pass (2026-11-04):** the user: *"fix the pixelazation so the picture would looke better"*. Done: sub-pixel tracing (each mask softened, then the 0.5 level is traced with interpolation), hair tones read from a smoothed copy of the hair only (speckles → smooth bands), a thin-line detector for light lines (`line_soft`, kept out of the hair and the reds), rings along lines take the area's color, two new iris pinks, and a 2× render scaled down with `sips` (MP4 built in the sequencer). Output: `kaguya/kaguya_fukkireta_v3_2.mp4` / `.gif` / `frames_v3_2/` (the 2× frames are in `frames_v3_2_hi/`, 178 MB, safe to delete)
- **Next time:** the lash lines are still a bit fuzzy, and there are small collar bits on the far-left lean. Best next step: a front-facing reference from Nano Banana

## Kaguya v4: the whole clip, with the music (2026-11-05)
- The user: *"recreate the same as in the fukkireta reference, with kaguya, the same clip + music, right now it is just repeating gif and is really pixelized, use blender mcp"*. Reference: `reference/fukkireta.mp4` (90.8 s, 960×720, 30 fps). Goal + progress: `kaguya/v4/GOAL.md`
- **Output:** `kaguya/kaguya_fukkireta_v4.mp4`: 1440×1080 (4:3 like the reference), 30 fps, 90.8 s, the reference's own AAC audio, rendered by Blender (EEVEE, ~0.13 s a frame, ~6 min)
- **What the full clip taught (it overrides the GIF-based notes above):** the bob is a fixed **10-drawing cycle** of 24 frames, drawings held 2-2-2-3-3 frames (12.5 a second), from frame 0 to the end (one drawing skipped at 60.9 s). Each beat the head **snaps** to a side (tilt ±17°, a ~19° turn, a dip) and settles back over 4 drawings; the body sways ±20 px with it. Six mouth shapes carry the lip-sync. **No blinks.** The background is pink with white baguette outlines, **scrolling** diagonally
- **How:** everything is measured, then copied. `v4/analysis/` tracks Teto's eyes and tie on every frame (`track.py`), works out which cycle pose and which mouth every drawing is (`faces.py` → `timeline.json`). `v4/parts.py` cuts reference.png into cel layers (ribbons, body, neck, head, closed mouth) with real alpha and every hidden area painted in; `v4/mouths.py` draws the other five mouths; `v4/pack.py` crops them and draws the background tile. `v4/kaguya_v4.py` builds the Blender scene: textured grid meshes, 10 pose shape keys (stood upright, then Teto's tilt / turn / sway per pose, the neck bending between head and body, locks and ribbon tails trailing on a damped spring), a controller whose `pose` key changes on exactly the reference's drawing frames, one mouth object with 6 textures switched per drawing, the scrolling background, the audio strip and the MP4 output
- **Not pixels any more:** the textures are used at 1:1 (no upscaling), edges are un-mixed into real alpha (no white fringes), textures have their colors bled into the transparent area (no dark seams), EEVEE 16 samples
- **Gotchas:** keys on custom properties come in LINEAR in Blender 5.2 even with the preference set, so set CONSTANT on the F-curves (otherwise held frames show in-between poses and wrong mouths). The reference's video starts 1/30 s after its audio, so the sound strip starts at frame 0. Each MCP call starts with an empty namespace: `exec` the script again before calling its functions
- **Left out on purpose:** the karaoke subtitles and the little cat in the corner (the uploader's overlay, not the animation)

### v4.1: crisp art + a clean neck (2026-11-05)
- The user on v4: *"the picture itself is really pixely right now, and there is the problem with the neck ... mainly on the left side"*
- **Why it was pixely:** the source art (`reference.png`, 982×1412) is soft with JPEG-like noise, and it was shown 1:1 and encoded at ~3 Mbps.
  Now: `v4/upscale.py` runs Real-ESRGAN x4plus **anime 6B** on the CPU (4 threads, ~75 s, no GPU), Lanczos down to 2×
  → `v4/art/reference_2x.png` (clean lines, flat colors, same shapes). All layers are cut at 2×, textures are 2×, looked up with
  "Closest" (the 16 jittered AA samples do the filtering, sharper than Linear), H.264 CRF 14 / preset BEST
- **Why the neck broke:** the lock layers were cut by color, so collar lines, the V edge and bits of the neck outline rode along
  with the hair (the "hooks"), the neck had no outline of its own on the hidden parts, and its base moved with the head (sliding
  off the V). Now: the locks are traced row by row on the 2× art (`LOCK_L` / `LOCK_R` in `parts.py`), the neck has its own
  outline (visible + painted), its base moves with the body (`NECK_FADE` 780–832), and the lapels/dress are a separate
  `body_front` layer **in front of** the neck, so the neck slides under the V edges. The jaw cut was re-measured at the right
  corner (the jaw's dark wedge reaches y 795). Below the jaw the locks swing as a whole (no bent tips)
- **Checks that caught things:** the round-trip (layers over white vs the art), a layer-move simulator in plain Python
  (shift/rotate the 2× layers like the rig), and Blender stills of all 10 poses with single layers isolated (`still(only=[...])`)
- Output: `kaguya/kaguya_fukkireta_v4_1.mp4`. The v4.0 scripts and parts are kept in `v4/old/`

### v4.2: a connected neck + smoother motion (2026-11-05)
- The user on v4.1: *"it feels like the neck dislocates and leans a little bit more left than to right, and can you make it a
  little smoother, good work with pixealation tho"*
- **Why the neck looked dislocated:** Teto's head *slides* 55–150 px sideways while her body barely moves (her neck is
  under her hair). Kaguya's neck is visible for only ~50–80 px, and v4.1 did the whole shift in 52 px under the jaw, a jog in
  the outline. The right leans hide that spot under the jaw, so only the left leans showed it. On top of that, standing her up around
  the chin left the head 6.5 px left of the neck at rest
- **Fix:** stood up around the top of the neck (`NECK_TOP`); the shoulders take 45 % of the head's slide
  (`BODY_FOLLOW`); the neck bends linearly from y 740 to where it meets the collar (`NECK_BEND`, joints stay put); under
  the thin strand the neck's hidden outline runs into the V edge at a point (no grey "bubble" when the strand swings away)
- **Smoother:** a pose on every frame (30 fps) instead of 12.5 drawings/s: the drawings still land on their own frames,
  in-betweens come from a periodic monotone cubic through the 10 poses (eases into each lean, no overshoot), springs per
  frame. 30 shape keys (24 cycle frames + 6 for the 3 irregular drawings); mouths still per drawing
- **New check tool:** `rigsim.py` (scratchpad) rasterizes the rig's own vertex positions in plain Python, so neck
  variants can be compared on every frame without Blender or the GPU
- Output: `kaguya/kaguya_fukkireta_v4_2.mp4`. The v4.1 scripts and parts are in `v4/old_v41/`

### v4.3: the chin's shadow follows the head (2026-11-05)
- The user sent five close-ups of the chin/neck. Two problems: the neck's shadow (painted for the drawing's tilted head) stayed
  put, so one side of the neck was lit right up to the jaw; and a black spike at the right jaw corner (the drawing's ink
  pool where the jaw line meets the neck outline, riding on the head; the head's turn slides the jaw ~45 px off the neck)
- **Shadow:** `v4/neck_shade.py` bakes the neck's shading per frame pose into `parts/tex/neck_atlas.png`: every texel is
  taken through the neck's bend to the screen and back through the head's own transform (turn included) into the drawing,
  and is in shadow above the drawing's shadow edge. The neck material picks its tile by a keyed `pose` property (shader
  math on the UVs, one texture). Lesson: shading that is *cast* by a part belongs to that part's motion, even when it's
  painted on another layer
- **Jaw corner:** head cut along the jaw line's own lower edge; the ink pool is repainted as neck skin + the neck's outline
  continuing under the jaw. Neck's right outline re-measured and repainted as one line down to the collar's curl
- Output: `kaguya/kaguya_fukkireta_v4_3.mp4`
