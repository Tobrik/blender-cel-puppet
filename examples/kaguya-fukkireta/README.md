# Example: Kaguya × Fukkireta (the project this skill came from)

Kaguya Shinomiya doing Kasane Teto's "Fukkireta" head-bob for the whole 90.8 s song, 1440×1080, 30 fps, with the
reference's audio. Version 4.3: crisp upscaled art, measured motion, in-betweens on every frame, the neck bending to
the collar joints, the chin's shadow following the head. `GOAL.md` and `NOTES.md` keep every round of feedback and
what was done about it. Read them to see why each rule in `parts.py` / `kaguya_v4.py` exists.

**Not included:** the reference video and its audio, the character image and everything cut from it (`art/`,
`parts/`), the upscaler model, the renders. Bring your own; don't commit them.

## Files, in run order

| Step | File | In → out |
|---|---|---|
| A1 | `analysis/track.py` | `reference.mp4` → `analysis/track.npz` (both irises + the tie on every frame, frame diffs). Its iris colour thresholds and screen regions are for Teto |
| A2 | `analysis/faces.py` | + `track.npz` → `faces.npz`: drawings (first frame + hold), which of the 10 cycle poses each is (seeded from the first cycle: `SEED_X`, `SEED_A`), mouth / eye crops |
| A3 | `analysis/make_timeline.py` | `faces.npz` → mouth clusters → (you name them) → `analysis/timeline.json` (included, as a format example) |
| B1 | `../../scripts/upscale.py` | `art/reference.png` → `art/reference_2x.png` (CPU, ~75 s) |
| B2 | `parts.py` | `art/reference_2x.png` → `parts/*.png` (2x layers: ribbons, body, neck, body_front, head, closed mouth) + previews + the round-trip check. **All the polygons are traced on this one image**: re-measure for new art (print dark runs row by row, see `references/pipeline.md` §B) |
| B3 | `mouths.py` | → `parts/mouth_*.png` (TINY, O, A, E, GRIN drawn as vector shapes, turned to the drawing's tilt) |
| B4 | `pack.py` | `parts/*.png` → `parts/tex/*.png` (cropped, colour-bled) + `parts.json` (boxes) + `bg_tile.png` |
| B5 | `neck_shade.py` | → `parts/tex/neck_atlas.png` (+ `.json`): the neck's shading for every frame pose (needs the rig) |
| D | `kaguya_v4.py` | in Blender: `PROJECT = r"..."; exec(open(PROJECT + "/kaguya_v4.py").read()); build(); save()` |
| E | background render | `"<blender>" -b kaguya_v4.blend -S "Kaguya Fukkireta v4" -a` |

Also expected in the folder: `fukkireta_audio.m4a` (the reference's audio: `ffmpeg -i reference.mp4 -vn -c:a copy
fukkireta_audio.m4a`), `checks/` (stills, logs), `render/` (output).

## What's specific to this art / this reference

- `parts.py`: every coordinate constant (`JAW`, `JAW_POOL`, `LOCK_L/R`, `NECK`, `NECK_LINE_L/R`, `JOINT_R`, `COLLAR_*`,
  `VLINE_*`, `V_OPEN`, ribbons, `BG_SEEDS`, `MOUTH_BOX`) and the sampled colours.
- `mouths.py`: the mouth centre, tilt and palette.
- `neck_shade.py`: the two skin tones and `SHADOW_EDGE`.
- `kaguya_v4.py`: `EYE_L/R` (the drawing's iris centres), `NECK_TOP`, `TETO_*` (the reference's rest pose / eye
  distance), `SCREEN_EYE`, the lock / ribbon roots and spring settings, `NECK_BEND`, `BODY_FOLLOW`, `YAW_*`, `HEAD_R*`,
  the background cell / scroll, `FRAMES`, `HOLDS`.

The rest is general: the helpers at the top of `parts.py` (masks, anti-aliased coverage, un-mixing, fills, line
drawing, round trip), the rig maths, frame poses and springs, and the Blender build.
