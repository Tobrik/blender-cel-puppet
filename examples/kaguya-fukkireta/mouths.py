"""Kaguya v4: the lip-sync mouths (TINY, O, A, E, GRIN), drawn as clean vector shapes in Kaguya's palette.

The shapes follow Teto's mouths in the reference (measured per drawing, see analysis/), sized to Kaguya's face. They're
drawn upright around the closed mouth's centre, then turned by the reference's head tilt, so they sit on the face
exactly where the closed mouth was. Rendered at 4x and saved at 2x reference resolution for crisp edges.

usage: python mouths.py      (writes parts/mouth_*.png; run after parts.py)
"""
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "parts")
CENTER = (577.0, 677.0)            # the closed mouth's centre (reference px)
TILT = math.radians(18.4)          # the reference's head tilt (eye line), clockwise on screen
SAVE_SCALE = 2                     # sprites are stored at 2x reference resolution
SS = 4                             # supersampling while drawing
HALF = 80                          # sprite half-size, reference px

INK = (30, 18, 20)
INSIDE = (128, 46, 52)             # the mouth's dark-red inside
TONGUE = (214, 120, 124)
TEETH = (252, 249, 247)
TEETH_SHADE = (222, 214, 214)
LIP = (232, 180, 174)


def curve(f, n=48):
    u = np.linspace(-1, 1, n)
    return u, f(u)


def shape_pts(w, top, bot, n=64):
    """A closed mouth outline: corners at (+-w, 0); `top(u)` and `bot(u)` give y (down) along u in [-1, 1]."""
    u = np.linspace(-1, 1, n)
    upper = [(w * x, top(x)) for x in u]
    lower = [(w * x, bot(x)) for x in u[::-1]]
    return upper + lower


def draw_mouth(kind):
    S = HALF * 2 * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def P(pts, dy=0.0):
        return [((HALF + x) * SS, (HALF + y + dy) * SS) for x, y in pts]

    def poly(pts, fill):
        d.polygon(P(pts), fill=fill)

    def line(pts, width, fill=INK):
        d.line(P(pts), fill=fill, width=int(round(width * SS)), joint="curve")
        for x, y in (pts[0], pts[-1]):           # round caps
            r = width * SS / 2
            cx, cy = (HALF + x) * SS, (HALF + y) * SS
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)

    def clip_fill(outline, inner_pts, fill):
        """Fill inner_pts, clipped to the outline (via a mask)."""
        m = Image.new("L", (S, S), 0)
        ImageDraw.Draw(m).polygon(P(outline), fill=255)
        layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(layer).polygon(P(inner_pts), fill=fill)
        img.paste(layer, (0, 0), Image.composite(layer, Image.new("RGBA", (S, S), (0, 0, 0, 0)), m).split()[3])

    smile = lambda u: 3.0 * (1 - u * u)            # the corners lift a little, like her smile
    if kind == "TINY":
        t = np.linspace(0, 2 * np.pi, 64)
        out = [(10.5 * math.cos(a), 7 + 8.5 * math.sin(a)) for a in t]
        poly(out, INSIDE)
        tongue = [(7 * math.cos(a), 10 + 4.5 * math.sin(a)) for a in t]
        clip_fill(out, tongue, TONGUE)
        line(out + [out[0]], 3.0)
    elif kind == "O":
        t = np.linspace(0, 2 * np.pi, 72)
        out = [(20 * math.sin(a), 20 - 25 * math.cos(a) + 2.5 * math.cos(a) ** 2) for a in t]
        poly(out, INSIDE)
        teeth = [(x, y) for x, y in shape_pts(20, lambda u: -4.5 - 0.0 * u, lambda u: -4.5 + 9 * (1 - u * u))]
        clip_fill(out, teeth, TEETH)
        tongue = [(14 * math.cos(a), 36 + 9 * math.sin(a)) for a in t]
        clip_fill(out, tongue, TONGUE)
        line(out + [out[0]], 3.4)
    elif kind in ("A", "E"):
        w, depth, tooth = (40, 46, 9.5) if kind == "A" else (43, 24, 7.5)
        top = lambda u: -2 - 3.5 * (1 - u * u) + smile(u) * 0.6
        bot = lambda u: -2 + depth * (1 - u * u) ** (0.55 if kind == "A" else 0.8)
        out = shape_pts(w, top, bot)
        poly(out, INSIDE)
        teeth = shape_pts(w, lambda u: top(u) - 3, lambda u: top(u) + tooth * (1 - u ** 4))
        clip_fill(out, teeth, TEETH)
        tongue = shape_pts(w * 0.62, lambda u: depth * (0.55 if kind == "A" else 0.5) - 2 + 6 * u * u,
                           lambda u: depth + 4)
        clip_fill(out, tongue, TONGUE)
        line(out + [out[0]], 3.4)
    elif kind == "GRIN":
        w = 52
        top = lambda u: -4 - 2.5 * (1 - u * u) + 1.0 * u
        bot = lambda u: -4 + 21 * (1 - u * u) ** 0.75 + 1.0 * u
        out = shape_pts(w, top, bot)
        poly(out, TEETH)
        shade = shape_pts(w, lambda u: bot(u) - 6 * (1 - u * u) ** 0.5, lambda u: bot(u) + 2)
        clip_fill(out, shade, TEETH_SHADE)
        gap = [(w * u * 0.86, -4 + 8.5 * (1 - u * u) + 1.0 * u) for u in np.linspace(-1, 1, 40)]
        line(gap, 1.8)
        line(out + [out[0]], 3.4)
    else:
        raise ValueError(kind)
    # a soft pink lower-lip line under the open mouths, like the closed mouth has
    if kind in ("A", "E", "O"):
        pass
    return img


def place(sprite):
    """Turn the upright sprite by the reference's tilt; return the RGBA at SAVE_SCALE plus its box (ref px)."""
    a = np.array(sprite).astype(np.float32) / 255.0
    S = a.shape[0]
    M = cv2.getRotationMatrix2D((S / 2, S / 2), -math.degrees(TILT), 1.0)
    rgb = a[..., :3] * a[..., 3:4]                                   # premultiplied for clean resampling
    rot = cv2.warpAffine(np.dstack([rgb, a[..., 3]]), M, (S, S), flags=cv2.INTER_CUBIC)
    out_px = 2 * HALF * SAVE_SCALE
    small = cv2.resize(rot, (out_px, out_px), interpolation=cv2.INTER_AREA)
    al = np.clip(small[..., 3:4], 0, 1)
    col = np.where(al > 1e-4, small[..., :3] / np.maximum(al, 1e-4), 0)
    rgba = np.dstack([np.clip(col, 0, 1), al])
    box = (CENTER[0] - HALF, CENTER[1] - HALF, CENTER[0] + HALF, CENTER[1] + HALF)
    return rgba, box


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    sheet = []
    for kind in ("TINY", "O", "A", "E", "GRIN"):
        rgba, box = place(draw_mouth(kind))
        Image.fromarray((rgba * 255).round().astype(np.uint8), "RGBA").save(os.path.join(OUT, "mouth_%s.png" % kind.lower()))
        sheet.append(rgba)
    # preview: each mouth on the face
    head = np.array(Image.open(os.path.join(OUT, "head.png"))).astype(np.float32) / 255
    x0, y0 = int(CENTER[0] - HALF), int(CENTER[1] - HALF)
    tiles = []
    for rgba in sheet:
        face = head[y0:y0 + 2 * HALF, x0:x0 + 2 * HALF].copy()
        m = cv2.resize(rgba, (2 * HALF, 2 * HALF), interpolation=cv2.INTER_AREA)
        a = m[..., 3:4]
        face[..., :3] = m[..., :3] * a + face[..., :3] * (1 - a)
        tiles.append(cv2.resize(face, (320, 320), interpolation=cv2.INTER_CUBIC))
    Image.fromarray((np.clip(np.hstack(tiles), 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, "preview_mouths.png"))
    print("mouths written")
