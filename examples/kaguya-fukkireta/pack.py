"""Kaguya v4: crop the layers to their content (small textures, little RAM) and draw the background tile.

Writes parts/tex/<layer>.png (2x, like the layers) and parts/tex/parts.json ({layer: [x0, y0, x1, y1] in reference px}), plus
parts/tex/bg_tile.png: one cell of the reference's background (flat pink, a soft white baguette outline).

usage: python pack.py      (after parts.py and mouths.py)
"""
import json
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(HERE, "parts")
TEX = os.path.join(PARTS, "tex")
LAYERS = ["ribbon_L", "ribbon_R", "body", "neck", "body_front", "head"]
MOUTHS = ["mouth_tiny", "mouth_o", "mouth_a", "mouth_e", "mouth_grin"]   # + mouth_closed, put in the same 2x box
MOUTH_CENTER, MOUTH_HALF, MOUTH_SCALE = (577, 677), 80, 2
S = 2                           # layer px per reference px (parts.py)

# background, in output pixels (1440x1080 frame = 1.5x the reference video's 960x720)
BG_PINK = (254, 193, 188)
CELL = (418, 428)               # one lattice cell (278 x 285 reference-video px, x1.5)
BREAD_LEN, BREAD_W = 300, 76    # the baguette (outline), x1.5
BREAD_ANGLE = 32                # degrees, rising to the right
TILE_SCALE = 2                  # the tile texture is drawn at 2x for crisp edges


def bleed(rgba, r=8):
    """Copy the nearest visible color into the fully transparent pixels (alpha stays 0), so texture filtering at an
    edge never mixes in black."""
    a = rgba[..., 3]
    known = a > 0
    if known.all() or not known.any():
        return rgba
    _, lab = cv2.distanceTransformWithLabels((~known).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    order = np.nonzero(known.ravel())[0]
    idx = np.zeros(lab.max() + 1, np.int64)
    idx[lab.ravel()[order]] = order
    flat = rgba.reshape(-1, 4)
    out = rgba.copy()
    sel = ~known
    out[sel, :3] = flat[idx[lab[sel]], :3]
    return out


def save_tex(rgba, path):
    Image.fromarray(bleed(rgba), "RGBA").save(path)


def crop_layers():
    os.makedirs(TEX, exist_ok=True)
    boxes = {}
    for name in LAYERS:
        im = np.array(Image.open(os.path.join(PARTS, name + ".png")))
        ys, xs = np.nonzero(im[..., 3] > 0)
        h0, w0 = im.shape[0] // S, im.shape[1] // S                    # box in reference px, crop at 2x
        x0, y0 = max(0, xs.min() // S - 4), max(0, ys.min() // S - 4)
        x1, y1 = min(w0, xs.max() // S + 5), min(h0, ys.max() // S + 5)
        save_tex(im[y0 * S:y1 * S, x0 * S:x1 * S], os.path.join(TEX, name + ".png"))
        boxes[name] = [int(x0), int(y0), int(x1), int(y1)]
    cx, cy = MOUTH_CENTER
    mbox = [cx - MOUTH_HALF, cy - MOUTH_HALF, cx + MOUTH_HALF, cy + MOUTH_HALF]
    for name in MOUTHS:
        im = np.array(Image.open(os.path.join(PARTS, name + ".png")))
        save_tex(im, os.path.join(TEX, name + ".png"))
        boxes[name] = mbox
    # the closed mouth (cut from the 2x art): the same box, already at the mouths' 2x
    assert MOUTH_SCALE == S
    full = np.array(Image.open(os.path.join(PARTS, "mouth_closed.png")))
    save_tex(full[mbox[1] * S:mbox[3] * S, mbox[0] * S:mbox[2] * S], os.path.join(TEX, "mouth_closed.png"))
    boxes["mouth_closed"] = mbox
    json.dump(boxes, open(os.path.join(TEX, "parts.json"), "w"), indent=1)
    return boxes


def bread_outline(draw, cx, cy, s):
    """A baguette: a long rounded loaf with diagonal score marks, as an outline."""
    L, Wd = BREAD_LEN * s / 2, BREAD_W * s / 2
    a = math.radians(-BREAD_ANGLE)
    ca, sa = math.cos(a), math.sin(a)

    def P(x, y):
        return (cx + x * ca - y * sa, cy + x * sa + y * ca)
    # the loaf: a capsule that tapers a little toward the ends
    pts = []
    for t in np.linspace(0, 2 * math.pi, 120, endpoint=False):
        x = L * math.cos(t)
        y = Wd * math.sin(t) * (1 - 0.18 * abs(math.cos(t)) ** 3)
        pts.append(P(x, y))
    draw.line(pts + [pts[0]], fill=255, width=int(7 * s), joint="curve")
    # score marks: short slanted cuts along the top
    for k in range(5):
        x = -L * 0.62 + k * L * 0.31
        draw.line([P(x - 0.10 * L, -Wd * 0.05), P(x + 0.06 * L, -Wd * 0.72)], fill=255, width=int(6 * s))


def bg_tile():
    s = TILE_SCALE
    w, h = CELL[0] * s, CELL[1] * s
    # draw on a 3x3 block of cells so the glow wraps across the tile edges, keep the centre cell
    big = Image.new("L", (3 * w, 3 * h), 0)
    d = ImageDraw.Draw(big)
    for i in range(3):
        for j in range(3):
            bread_outline(d, w * i + w * 0.5, h * j + h * 0.5, s)
    glow = big.filter(ImageFilter.GaussianBlur(5 * s))
    core = big.filter(ImageFilter.GaussianBlur(1.2 * s))
    m = np.maximum(np.array(core, np.float32) / 255 * 0.85, np.array(glow, np.float32) / 255 * 0.9)
    m = np.clip(m, 0, 1)[h:2 * h, w:2 * w]
    pink = np.array(BG_PINK, np.float32) / 255
    white = np.array([1.0, 0.985, 0.98], np.float32)
    img = pink * (1 - m[..., None]) + white * m[..., None]
    Image.fromarray((img * 255).round().astype(np.uint8)).save(os.path.join(TEX, "bg_tile.png"))


if __name__ == "__main__":
    boxes = crop_layers()
    bg_tile()
    for k, v in boxes.items():
        print(k, v)
