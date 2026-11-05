"""Review sheet: the reference and your render side by side at the same moments, across the whole clip.

usage: python review_sheet.py <reference.mp4> <render.mp4> <out.png> [--every 3] [--offset 0] [--cols 4]
Each tile is [reference | render] at the same frame index (render frame n + offset vs reference frame n), labelled with
the time. Look for: the same pose (tilt / lean / dip), the same mouth, the same background phase, nothing broken.
"""
import argparse

import cv2
import numpy as np


def frames_at(path, idx):
    cap = cv2.VideoCapture(path)
    out, want, i, k = {}, sorted(set(idx)), 0, 0
    while k < len(want):
        ok, f = cap.read()
        if not ok:
            break
        if i == want[k]:
            out[i] = f
            k += 1
        i += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reference")
    ap.add_argument("render")
    ap.add_argument("out")
    ap.add_argument("--every", type=float, default=3.0, help="seconds between moments")
    ap.add_argument("--offset", type=int, default=0, help="render frame = reference frame + offset")
    ap.add_argument("--cols", type=int, default=4)
    a = ap.parse_args()
    cap = cv2.VideoCapture(a.reference)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    idx = [int(round(t * fps)) for t in np.arange(0.5, n / fps - 0.5, a.every)]
    R = frames_at(a.reference, idx)
    V = frames_at(a.render, [i + a.offset for i in idx])
    w, h = 256, 192
    tiles = []
    for i in idx:
        blank = np.zeros((h, w, 3), np.uint8)
        pa = cv2.resize(R[i], (w, h), interpolation=cv2.INTER_AREA) if i in R else blank
        pb = cv2.resize(V[i + a.offset], (w, h), interpolation=cv2.INTER_AREA) if i + a.offset in V else blank
        pair = np.hstack([pa, pb])
        cv2.putText(pair, "%.1fs" % (i / fps), (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        tiles.append(cv2.copyMakeBorder(pair, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
    while len(tiles) % a.cols:
        tiles.append(np.full_like(tiles[0], 255))
    cv2.imwrite(a.out, np.vstack([np.hstack(tiles[r:r + a.cols]) for r in range(0, len(tiles), a.cols)]))
    print("sheet:", len(idx), "moments ->", a.out)


if __name__ == "__main__":
    main()
