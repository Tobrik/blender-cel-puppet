---
name: blender-cel-puppet
description: Recreate a 2D anime reference clip (a head-bob or dance meme like Kasane Teto's "Fukkireta", a loop, a lip-synced bust shot) with a different character from a single still image, as a cel-puppet rig built in Blender through the Blender MCP, with the reference's own audio and timing. It measures the motion from the reference frame by frame, cuts the still into clean layers with painted-in hidden parts, rigs them, renders an MP4 and reviews it side by side against the reference. Use this whenever someone wants their character / OC / waifu / screenshot to "do the Fukkireta", copy a meme animation or dance from a video, animate an anime still to a song, or turn a reference clip into the same clip with a new character in Blender. Also use it for follow-ups on such an animation, like "it's pixelated", "the neck looks dislocated", "make it smoother", "the shadow is wrong", or "fix the hair".
compatibility: Blender 4.4+ (tested on 5.2) with the Blender MCP add-on; Python 3 with numpy, opencv-python, pillow (and torch CPU for the optional upscaler); ffmpeg/ffprobe.
---

# Cel puppet from a reference clip

You take two inputs, **a reference video** (the motion, the timing, the music) and **one still of the character**,
and produce the reference clip with that character: same length, the reference's audio, the same moves on the same
frames. The character is a set of cel layers (head, hair locks, neck, body, ribbons, mouths) on textured meshes in
Blender, posed by shape keys, so the art stays exactly the user's art and nothing gets redrawn.

The method in one line: **measure everything from the reference, cut the art like an animator would, check every
joint on every frame, then render.** Most of the hard-won detail is in `references/lessons.md`. When the user reports a
problem, look it up there first.

## What's in this skill

- `references/pipeline.md`: the six phases in detail (analysis, art, rig, Blender build, render, review). Read the
  section for the phase you're in.
- `references/lessons.md`: what the user said, what caused it, and the fix, plus Blender pipeline bugs. Read it before
  you rig, and whenever the user complains about something.
- `references/blender.md`: MCP call pattern, the building blocks (materials, shape-key drivers, CONSTANT keys,
  atlas, audio, output), rendering in the background.
- `references/goal-template.md`: a GOAL.md for long, multi-session jobs.
- `scripts/`: reusable tools. `upscale.py` (CPU anime upscaler), `drawing_rate.py` (held frames), `rigsim.py`
  (plain-Python render of the rig on any frame pose, with constant overrides), `review_sheet.py` (reference vs render
  across the clip), `cycle_sheet.py` (consecutive frames zoomed on a joint), `compare.py` (chosen frames).
- `examples/kaguya-fukkireta/`: the complete working project this skill was distilled from (Kaguya doing the Fukkireta
  head-bob for the whole 90.8 s song). It has analysis, layer cutting, mouths, packing, shading bake and the Blender rig,
  and its `GOAL.md` and `NOTES.md` record every round of feedback. Copy it as the starting point for a new project. The
  coordinates in `parts.py` are traced on that one image and have to be re-measured for new art. The structure, helpers
  and rig carry over.

## Before you start

1. **Gather:** the reference video (with audio), the character still (best: front-facing, upright, bust, neck visible;
   ask for a straighter one if the head is strongly tilted or turned, because every degree you undo shows at the neck),
   and a working Blender MCP connection (`get_addon_status`).
2. **Ask about the machine** if it's unclear: if they run other GPU or RAM work, keep image work on the CPU in plain
   Python, keep textures small, and render once, in the background.
3. **For long jobs** (the full clip easily takes hours), write a `GOAL.md` from `references/goal-template.md`, with the
   user's words, the acceptance list and the plan. If they want it to keep going unattended, offer a check-in timer.
   Update the boxes and the log as you go.
4. Start a project folder (copy `examples/kaguya-fukkireta/` and rename): `analysis/`, `art/`, `parts/`, `checks/`,
   scripts at the top. Never commit the reference video, its audio or the user's art to a public repo.

## The workflow

**A. Analyse the reference** (`pipeline.md` §A). Get the fps, the frame count and the audio offset; work out the drawing
rate (`drawing_rate.py`); track the head (both irises) and the body on every frame; split the drawings into the
cycle's poses; symmetrise left and right; classify the mouths; note blinks and the background's scroll. The output is
`timeline.json`, with a pose and a mouth for every drawing. Everything later reads this file, so check it with a contact
sheet.

**B. Cut the art** (`pipeline.md` §B). Upscale it if it's soft (`upscale.py`, CPU). Choose the layers and their order.
Cut on outlines traced row by row on the 2x art, never by colour. Paint in whatever motion can uncover. Un-mix the soft
edges. Run the round-trip test (the stacked layers should give back the art), draw the mouth sprites, then pack the
textures (crop and bleed).

**C. Rig in numpy** (`pipeline.md` §C):
- Scale the reference's measured motion by the eye-separation ratio.
- Stand the head up around the top of the neck.
- Turn the head with the ellipsoid warp.
- Let the shoulders follow a share of the head's slide.
- Bend the neck linearly between the jaw and the collar joints.
- Give the hanging parts springs.
- Put in-betweens on every frame with the drawings on their own frames.
- Bake shading cast by the head so it follows the head.

Check variants with `rigsim.py` on every frame pose, zoomed on the joints, before going to Blender. It costs seconds
and no GPU.

**D. Build in Blender** (`blender.md`, the example's `kaguya_v4.py`). In its own scene: a grid mesh per layer, a shape
key per frame pose driven by a keyed controller (CONSTANT keys), the mouth switched per drawing, the background
scrolling, the audio strip, the H.264 output. Verify that every drawing is on its pose and the controller matches the
timeline on every frame (0 mismatches). Compare a few Blender stills with rigsim's renders.

**E. Render** in a background Blender process, one render at a time, to a **new file name per version**. Check the file
with ffprobe.

**F. Review before saying it's done:**
- `review_sheet.py`: about 30 moments side by side with the reference. Poses and mouths should match.
- `cycle_sheet.py`: every frame of one cycle, zoomed on each joint, both sides.
- A before/after crop of whatever the user complained about.

## Principles (why the steps are what they are)

- **Measure, don't guess.** Motion invented by eye looks like "a repeating gif". Numbers taken from the reference
  look like the reference. When a joint looks wrong, print how far each part moves per pose, and check left against
  right.
- **The user looks at the joints.** Neck, jaw corners, where hair meets the collar, hair tips, and whether left and
  right leans match. Check those yourself on every frame, not only the key poses.
- **Every pixel belongs to exactly one part.** Line pixels go to the part whose line it is, junction ink to the part
  it stays with, a cast shadow to the part that casts it. Most artefacts are a pixel on the wrong layer.
- **Hidden areas will show.** Motion uncovers what the drawing hides. Paint it so it looks intended (a collar
  pocket is a wedge), and draw the hidden outlines too.
- **Spread deformation, pin joints.** Bend a neck over its whole length, ending exactly where it meets the collar. A
  short fade reads as a dislocation.
- **Keep the timing, smooth on top.** Keep the reference's drawings on their exact frames. In-betweens make it
  smoother without moving the beat.
- **Simulate before rendering. Render once, in the background.** Plain-Python checks are fast, repeatable and free
  on the GPU.

## Talking to the user

- Explain causes in their words. For example: "the shadow under her chin was painted for the tilted drawing, so it
  stayed put while her head moved". Say what changed in what they'll see, and point them to the before/after image.
- Give every render a new file name (`_v2`, `_v3`, ...), so a player's cache can't show them the old file.
- Mention trade-offs you made, such as "the shoulders now sway a bit more than the reference's". Name the one setting
  that changes it.
