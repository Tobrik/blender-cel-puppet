"""Kaguya v4.2: the shadow under her chin follows her head.

The neck's shading in the art is the shadow her (tilted) head casts: a band under the jaw. Painted onto the neck layer
it stayed put while the head was stood up straight, tilted, turned and slid, so in most poses one side of the neck was
lit right up to the jaw. Here the neck texture is re-shaded for every frame pose of the rig: each texel goes through
the neck's bend to the screen, back through the head's own transform (with its turn) into the drawing, and is in shadow
where the drawing's head casts it (above SHADOW_EDGE). The neck's outline and shape are untouched.

Writes parts/tex/neck_atlas.png (one tile per frame pose, in the rig's order, `COLS` per row) and neck_atlas.json.
usage: python neck_shade.py        (after parts.py, mouths.py and pack.py; plain Python, uses kaguya_v4.py's rig)
"""
import importlib.util
import json
import os
import sys
import types

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "parts", "tex")
S = 2
COLS, MARGIN = 6, 8                     # atlas: tiles per row, transparent margin around each tile (2x px)

# the two skin tones of the neck (sampled on the art)
LIGHT = np.array([0.984, 0.910, 0.847], np.float32)
SHADE = np.array([0.741, 0.616, 0.553], np.float32)
K = SHADE / LIGHT                       # shadow = light * K (per channel); lines stay dark under it
# the shadow's lower edge in the drawing (reference px), measured where the lit skin starts; extended past both ends
SHADOW_EDGE = [(380, 762), (400, 783), (410, 793), (420, 807.5), (430, 820), (440, 831.5), (450, 842), (470, 861.5),
               (490, 878), (500, 884.5), (510, 890), (520, 894.5), (540, 900), (550, 899.5), (580, 892.5),
               (590, 889.5), (600, 885.5), (610, 881), (630, 872), (660, 859)]
EDGE_SOFT = 0.7                         # its anti-aliasing (reference px)


def load_rig():
    sys.modules.setdefault("bpy", types.ModuleType("bpy"))
    spec = importlib.util.spec_from_file_location("kaguya_v4_rig", os.path.join(HERE, "kaguya_v4.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def shadow_in_art(Q):
    """1 where the drawing's head shades the neck (above the edge), 0 where it's lit; anti-aliased."""
    ex, ey = np.array(SHADOW_EDGE, float).T
    yb = np.interp(Q[:, 0], ex, ey, left=np.nan, right=np.nan)
    lo = Q[:, 0] < ex[0]
    hi = Q[:, 0] > ex[-1]
    yb[lo] = ey[0] + (Q[lo, 0] - ex[0]) * (ey[1] - ey[0]) / (ex[1] - ex[0])
    yb[hi] = ey[-1] + (Q[hi, 0] - ex[-1]) * (ey[-1] - ey[-2]) / (ex[-1] - ex[-2])
    return np.clip((yb - Q[:, 1]) / EDGE_SOFT + 0.5, 0, 1)


def unshade(rgba):
    """The neck without its painted shadow: s = how much of the shadow each texel has (skin: from its color; lines
    and edges: their nearest skin's), base = color / K^s."""
    c = np.clip(rgba[..., :3], 1e-3, 1)
    s3 = np.log(c / LIGHT) / np.log(K)
    s = np.clip(s3.mean(-1), 0, 1)
    model = LIGHT * K ** s[..., None]
    lum = c @ np.array([0.299, 0.587, 0.114], np.float32)
    skin = (rgba[..., 3] > 0.5) & (lum > 0.45) & (np.abs(c - model).max(-1) < 0.07)
    _, lab = cv2.distanceTransformWithLabels((~skin).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    order = np.nonzero(skin.ravel())[0]
    idx = np.zeros(lab.max() + 1, np.int64)
    idx[lab.ravel()[order]] = order
    s_all = s.ravel()[idx[lab.ravel()]].reshape(s.shape)
    s_all[skin] = s[skin]
    base = np.clip(rgba[..., :3] / K ** s_all[..., None], 0, 1)
    # the skin is flat cel color: away from the lines it's the lit tone exactly (no ghost of the old shadow's edge, whose
    # anti-aliasing / the upscaler's light fringe doesn't un-shade cleanly)
    near_line = cv2.dilate((lum < 0.35).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))) > 0
    base[~near_line] = LIGHT
    return base, s_all


def head_inverse(rig, S_, ps, iters=8):
    """Points of the drawing that the head (with its turn) puts at screen points S_ (reference px)."""
    # the head without its turn is a rotation + shift: invert that exactly, then correct for the turn
    a = -rig.TILT + ps["roll"]
    Q = rig.rot(rig.rot(S_ - ps["dE"] - rig.E_UP, -ps["roll"]) + rig.E_UP, rig.TILT, rig.NECK_TOP)
    for _ in range(iters):
        err = S_ - rig.head_T(Q, ps, warp=True)
        Q = Q + rig.rot(err, -a)
    return Q


def bleed(rgba):
    a = rgba[..., 3]
    known = a > 0
    _, lab = cv2.distanceTransformWithLabels((~known).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    order = np.nonzero(known.ravel())[0]
    idx = np.zeros(lab.max() + 1, np.int64)
    idx[lab.ravel()[order]] = order
    out = rgba.copy()
    flat = rgba.reshape(-1, 4)
    out[~known, :3] = flat[idx[lab[~known]], :3]
    return out


def main():
    rig = load_rig()
    boxes = json.load(open(os.path.join(TEX, "parts.json")))
    x0, y0, x1, y1 = boxes["neck"]
    rgba = np.asarray(Image.open(os.path.join(TEX, "neck.png"))).astype(np.float32) / 255
    th, tw = rgba.shape[:2]
    assert (tw, th) == ((x1 - x0) * S, (y1 - y0) * S), (tw, th, boxes["neck"])
    base, s_art = unshade(rgba)
    # every texel's place in the drawing (Blender's UV convention: texel j covers [x0 + j/S, x0 + (j+1)/S])
    jj, ii = np.meshgrid(np.arange(tw), np.arange(th))
    P = np.stack([x0 + (jj.ravel() + 0.5) / S, y0 + (ii.ravel() + 0.5) / S], 1)

    tl = rig.load_timeline()
    pose_list, specs, _ = rig.frame_poses(tl)
    swings = rig.swings_for(pose_list, specs)
    n = len(pose_list)
    rows = -(-n // COLS)
    TW, TH = tw + 2 * MARGIN, th + 2 * MARGIN
    atlas = np.zeros((rows * TH, COLS * TW, 4), np.float32)
    alpha = rgba[..., 3]
    for i, ps in enumerate(pose_list):
        Sx = rig.pose_points("neck", P, [ps], {k: [v[i]] for k, v in swings.items()})[0]
        Q = head_inverse(rig, Sx, ps)
        m = shadow_in_art(Q).reshape(th, tw)
        tile = np.zeros((TH, TW, 4), np.float32)
        tile[MARGIN:MARGIN + th, MARGIN:MARGIN + tw, :3] = base * K ** m[..., None]
        tile[MARGIN:MARGIN + th, MARGIN:MARGIN + tw, 3] = alpha
        r, c = divmod(i, COLS)
        atlas[r * TH:(r + 1) * TH, c * TW:(c + 1) * TW] = bleed(tile)
        if i == 0:
            chk = np.abs(rgba[..., :3] - tile[MARGIN:MARGIN + th, MARGIN:MARGIN + tw, :3]).max(-1)[alpha > 0.5]
            print("frame pose 0 vs the art's own shading: %.0f%% of texels change by > 0.1" % (100 * (chk > 0.1).mean()))
    Image.fromarray((np.clip(atlas, 0, 1) * 255).round().astype(np.uint8), "RGBA").save(os.path.join(TEX, "neck_atlas.png"))
    info = dict(cols=COLS, rows=rows, count=n, margin=MARGIN, tile_w=tw, tile_h=th, width=COLS * TW, height=rows * TH)
    json.dump(info, open(os.path.join(TEX, "neck_atlas.json"), "w"), indent=1)
    print("neck atlas: %d tiles, %dx%d px" % (n, info["width"], info["height"]))


if __name__ == "__main__":
    main()
