"""Render a puppet rig's frame poses in plain Python (no Blender, no GPU), to compare rig variants on every frame.

The rig is the same Python file Blender exec()s (see examples/kaguya-fukkireta/kaguya_v4.py). Imported here with a stub
`bpy`, it has to provide:
  LAYERS              [(name, grid_cell_px, depth), ...], back to front
  RES, CAM            output resolution; the camera centre in reference px (output px = reference px - CAM + RES / 2)
  grid(box, cell)     -> (P, uv, faces): a layer's rest vertices (reference px), UVs, quads
  load_timeline(); frame_poses(tl) -> (poses, specs, per_frame); swings_for(poses, specs) -> {part: value per pose}
  pose_points(name, P, [pose], {part: [value]}) -> [Q]: the posed vertices (reference px)
  CYCLE (optional)    how many frame poses one cycle has (for "all")
Textures: <project>/parts/tex/<layer>.png (2x reference px), boxes in parts/tex/parts.json. If parts/tex/neck_atlas.png
(+ .json) exists, the neck takes its per-pose tile from it (see the example's neck_shade.py).

usage: python rigsim.py <project_dir> <out.png> <pose indices: 0,4,9 | all> <crop x0,y0,x1,y1 in output px>
                        [--zoom 1] [--cols 8] [--layers head,neck] [--rig kaguya_v4.py] [--set NAME=VALUE ...]
  --set overrides a rig constant before posing (a Python literal), e.g.  --set BODY_FOLLOW=0.3
        --set "NECK_BEND={'top': 740.0, 'L': 800.0, 'R': 848.0, 'x': (420.0, 560.0)}"
        (only constants read at call time; ones that other module-level constants are computed from need a re-import)
Rendered at 2x and averaged down (like the render's AA samples). Matches EEVEE within a few levels of 255.
"""
import argparse
import ast
import importlib.util
import json
import os
import sys
import types

import cv2
import numpy as np
from PIL import Image

PINK = np.array([254, 193, 188], np.float32) / 255      # background colour of the sheet (no background layer here)
SS = 2


def load_rig(path):
    sys.modules.setdefault("bpy", types.ModuleType("bpy"))
    spec = importlib.util.spec_from_file_location("puppet_rig", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def raster(P, Q, faces, box, texture, crop, off, out):
    """One layer: rest vertices P, posed vertices Q (reference px), quads; composited into `out` (SS x the crop)."""
    x0, y0 = crop[:2]
    h, w = out.shape[:2]
    O = (Q + off - [x0, y0]) * SS
    ids = np.full((h, w), -1, np.float32)
    tris = np.array([t for f in faces for t in ((f[0], f[1], f[2]), (f[0], f[2], f[3]))])
    A = np.zeros((len(tris), 2, 3))
    for k, t in enumerate(tris):
        o = O[list(t)]
        if o[:, 0].max() < 0 or o[:, 1].max() < 0 or o[:, 0].min() > w or o[:, 1].min() > h:
            continue
        M = np.vstack([o.T, np.ones(3)])
        if abs(np.linalg.det(M)) < 1e-9:
            continue
        A[k] = P[list(t)].T @ np.linalg.inv(M)
        cv2.fillPoly(ids, [np.round((o - 0.5) * 16).astype(np.int32)], float(k), lineType=cv2.LINE_8, shift=4)
    yy, xx = np.nonzero(ids >= 0)
    if not len(yy):
        return
    k = ids[yy, xx].astype(int)
    px, py = xx + 0.5, yy + 0.5
    rx = A[k, 0, 0] * px + A[k, 0, 1] * py + A[k, 0, 2]
    ry = A[k, 1, 0] * px + A[k, 1, 1] * py + A[k, 1, 2]
    mx = ((rx - box[0]) * 2 - 0.5).astype(np.float32)
    my = ((ry - box[1]) * 2 - 0.5).astype(np.float32)
    n = len(mx)
    m = -(-n // 1024) * 1024                         # (cv2.remap wants maps under 32767 px a side)
    s = cv2.remap(texture, np.pad(mx, (0, m - n)).reshape(-1, 1024), np.pad(my, (0, m - n)).reshape(-1, 1024),
                  cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0).reshape(-1, 4)[:n]
    a = s[:, 3:4]
    out[yy, xx] = s[:, :3] * a + out[yy, xx] * (1 - a)


class Sim:
    def __init__(self, project, rig_file):
        self.rig = load_rig(os.path.join(project, rig_file))
        self.tex_dir = os.path.join(project, "parts", "tex")
        self.boxes = json.load(open(os.path.join(self.tex_dir, "parts.json")))
        self._tex = {}
        self.atlas = None
        ap = os.path.join(self.tex_dir, "neck_atlas.png")
        if os.path.exists(ap):
            self.atlas_info = json.load(open(os.path.join(self.tex_dir, "neck_atlas.json")))
            self.atlas = np.asarray(Image.open(ap)).astype(np.float32) / 255

    def setup(self):
        rig = self.rig
        self.off = np.array([rig.RES[0] / 2, rig.RES[1] / 2]) - rig.CAM
        self.grids = {}
        for name, cell, _ in rig.LAYERS:
            P, _, faces = rig.grid(self.boxes[name], cell)
            self.grids[name] = (P, faces, name)
        if "mouth_closed" in self.boxes:
            P, _, faces = rig.grid(self.boxes["mouth_closed"], 10)
            self.grids["mouth"] = (P, faces, "mouth_closed")
        tl = rig.load_timeline()
        self.poses, self.specs, _ = rig.frame_poses(tl)
        self.swings = rig.swings_for(self.poses, self.specs)

    def tex(self, name, i):
        if name == "neck" and self.atlas is not None:
            inf = self.atlas_info
            r, c = divmod(i, inf["cols"])
            m = inf["margin"]
            TW, TH = inf["tile_w"] + 2 * m, inf["tile_h"] + 2 * m
            return np.ascontiguousarray(self.atlas[r * TH + m:r * TH + m + inf["tile_h"],
                                                   c * TW + m:c * TW + m + inf["tile_w"]])
        if name not in self._tex:
            self._tex[name] = np.asarray(Image.open(os.path.join(self.tex_dir, name + ".png")).convert("RGBA")
                                         ).astype(np.float32) / 255
        return self._tex[name]

    def render(self, i, crop, layers=None):
        x0, y0, x1, y1 = crop
        out = np.ones(((y1 - y0) * SS, (x1 - x0) * SS, 3), np.float32) * PINK
        for name, (P, faces, tname) in self.grids.items():
            if layers and name not in layers:
                continue
            Q = self.rig.pose_points(name, P, [self.poses[i]], {k: [v[i]] for k, v in self.swings.items()})[0]
            raster(P, Q, faces, self.boxes[tname], self.tex(tname if name != "neck" else "neck", i), crop, self.off, out)
        return cv2.resize(out, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)

    def label(self, i):
        s = self.specs[i]
        if isinstance(s, tuple) and len(s) == 4:
            p, q, k, h = s
            return "#%d p%d%s" % (i, p, "" if k == 0 else " +%d/%d" % (k, h))
        return "#%d" % i


def sheet(tiles, cols, path, labels):
    tl = []
    for t, lab in zip(tiles, labels):
        t = t.copy()
        cv2.putText(t, lab, (5, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        tl.append(cv2.copyMakeBorder(t, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
    while len(tl) % cols:
        tl.append(np.full_like(tl[0], 255))
    cv2.imwrite(path, np.vstack([np.hstack(tl[i:i + cols]) for i in range(0, len(tl), cols)]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("out")
    ap.add_argument("poses")
    ap.add_argument("crop")
    ap.add_argument("--zoom", type=float, default=1.0)
    ap.add_argument("--cols", type=int, default=8)
    ap.add_argument("--layers", default=None)
    ap.add_argument("--rig", default="kaguya_v4.py")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE")
    a = ap.parse_args()
    sim = Sim(a.project, a.rig)
    for kv in a.set:
        k, v = kv.split("=", 1)
        val = ast.literal_eval(v)
        if isinstance(getattr(sim.rig, k, None), np.ndarray):
            val = np.array(val, float)
        setattr(sim.rig, k, val)
    sim.setup()
    n = getattr(sim.rig, "CYCLE", len(sim.poses))
    idx = list(range(n)) if a.poses == "all" else [int(v) for v in a.poses.split(",")]
    crop = tuple(int(v) for v in a.crop.split(","))
    layers = a.layers.split(",") if a.layers else None
    tiles = []
    for i in idx:
        im = (np.clip(sim.render(i, crop, layers), 0, 1) * 255).round().astype(np.uint8)[..., ::-1]
        if a.zoom != 1:
            im = cv2.resize(im, None, fx=a.zoom, fy=a.zoom,
                            interpolation=cv2.INTER_AREA if a.zoom < 1 else cv2.INTER_CUBIC)
        tiles.append(im)
    sheet(tiles, min(a.cols, len(tiles)), a.out, [sim.label(i) for i in idx])
    print("wrote", a.out, "(%d poses)" % len(idx))


if __name__ == "__main__":
    main()
