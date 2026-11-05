"""Track Teto in the reference, every frame: both irises (head position, roll, turn) and the tie (body sway).

usage: python track.py <reference.mp4> <out.npz>
Saves per frame: eyeL, eyeR (x, y, w, h of the iris blobs; L = viewer's left), tie (x, y), diff (change vs the previous frame).
"""
import sys

import cv2
import numpy as np


def irises(f):
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV).astype(np.int16)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = (((h >= 155) | (h <= 4)) & (s > 140) & (v < 185) & (v > 40)).astype(np.uint8)
    m[:150] = 0
    m[560:] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    cands = []
    for i in range(1, n):
        x, y, w, hh, a = st[i]
        if 40 <= w <= 85 and 50 <= hh <= 100 and a > 0.55 * w * hh and 0.5 < w / hh < 1.2:
            cands.append((a, cen[i][0], cen[i][1], w, hh))
    best = None
    # the pair: about level, 120-260 px apart
    for i in range(len(cands)):
        for j in range(len(cands)):
            a, b = cands[i], cands[j]
            dx, dy = b[1] - a[1], b[2] - a[2]
            if 100 < dx < 280 and abs(dy) < 0.6 * dx:
                score = a[0] + b[0]
                if best is None or score > best[0]:
                    best = (score, a, b)
    if best is None:
        return None
    return [best[1][1:], best[2][1:]]


def tie(f):
    """The tie's top: the dark-red/crimson vertical strip at the collar's center."""
    reg = f[600:720]
    hsv = cv2.cvtColor(reg, cv2.COLOR_BGR2HSV).astype(np.int16)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = ((h >= 160) | (h <= 6)) & (s > 120) & (v > 90) & (v < 230)
    ys, xs = np.nonzero(m)
    if len(xs) < 50:
        return (np.nan, np.nan)
    return (float(np.median(xs)), float(ys.min() + 600))


def main(src, out):
    cap = cv2.VideoCapture(src)
    E, T, D = [], [], []
    prev = None
    while True:
        ok, f = cap.read()
        if not ok:
            break
        e = irises(f)
        E.append(np.array(e).ravel() if e else np.full(8, np.nan))
        T.append(tie(f))
        g = cv2.cvtColor(f[150:560, 120:900], cv2.COLOR_BGR2GRAY).astype(np.float32)
        D.append(0.0 if prev is None else float(np.abs(g - prev).mean()))
        prev = g
    E = np.array(E)
    np.savez(out, eyeL=E[:, :4], eyeR=E[:, 4:], tie=np.array(T), diff=np.array(D))
    print(len(E), "frames; eyes missing in", int(np.isnan(E[:, 0]).sum()))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
