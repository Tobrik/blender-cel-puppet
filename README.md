# blender-cel-puppet

A Claude skill that recreates a 2D anime reference clip with a different character from a single still image. Think
a head-bob or dance meme like Kasane Teto's **"Fukkireta"**, a lip-synced bust shot, or a loop. Claude builds it as a
cel-puppet rig in **Blender through the Blender MCP**, with the reference's own audio and timing.

Give it a reference video and one picture of your character, and it:

1. **measures the reference** frame by frame: drawing rate, head tilt / slide / dip / turn, body sway, mouth shapes,
   background scroll, audio offset → `timeline.json`
2. **cuts the picture into clean cel layers** (head, hair locks, neck, body, ribbons, mouths). Cuts follow traced
   outlines, everything motion can uncover is painted in, edges are un-mixed, and an optional CPU anime upscale cleans
   up the art first
3. **rigs them** with the reference's measured motion: the head stood up straight and posed, the neck bending to the
   collar, the hair and ribbons trailing on springs, in-betweens on every frame, and shading that follows the head
4. **builds and renders** the scene in Blender (shape keys, a keyed controller, the audio strip, H.264 + AAC)
5. **reviews** the result side by side with the reference and frame by frame at the joints

It was distilled from a real project, Kaguya Shinomiya doing the full 90.8 s Fukkireta clip, and carries the fixes from
every round of feedback on it: "it's pixelated", "the neck dislocates", "make it smoother", "the shadow's wrong", "a
black spike at the jaw". See `references/lessons.md`.

## Install

Clone into your Claude skills folder:

```bash
git clone https://github.com/<you>/blender-cel-puppet ~/.claude/skills/blender-cel-puppet
```

(or into a project's `.claude/skills/`). Then just ask, e.g.:

- "make my OC (oc.png) do the fukkireta head bob, here's the video: fukkireta.mp4, use blender mcp"
- "recreate this dance clip with my character, same music and timing"
- "the animation looks pixely and the neck looks broken when she leans left"

## Requirements

- Blender 4.4+ (tested on 5.2) with a Blender MCP add-on/server that can run Python in Blender (`execute_blender_code`)
- Python 3 with `numpy`, `opencv-python`, `pillow`; `torch` (CPU build is fine) for the optional upscaler
- `ffmpeg` / `ffprobe`
- Optional: the Real-ESRGAN anime model `RealESRGAN_x4plus_anime_6B.pth` (17 MB) from the
  [Real-ESRGAN releases](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.2.4)

Everything heavy (upscaling, cutting, baking, rig checks) runs in plain Python on the CPU; Blender only builds the scene
and renders once, in the background.

## Layout

```
SKILL.md                     the skill: workflow, principles, where to look
references/
  pipeline.md                the six phases in detail
  lessons.md                 symptom → cause → fix (what users notice, Blender bugs)
  blender.md                 MCP call pattern, building blocks, rendering
  goal-template.md           GOAL.md for long multi-session jobs
scripts/
  upscale.py                 CPU anime upscaler (Real-ESRGAN anime 6B, tiled)
  drawing_rate.py            held-frame rhythm of the reference
  rigsim.py                  plain-Python render of the rig on any frame pose (+ constant overrides)
  review_sheet.py            reference vs render across the whole clip
  cycle_sheet.py             consecutive frames zoomed on a joint
  compare.py                 chosen frames side by side
examples/kaguya-fukkireta/   the complete working project (analysis, layers, mouths, bake, Blender rig, GOAL/NOTES)
```

## Notes

- The reference video, its music and the character art aren't included. Use material you have the right to use, and
  keep it out of the repo (see `.gitignore`).
- The example's layer polygons are traced on one specific image. For a new character they get re-measured; the method,
  helpers and rig carry over.
