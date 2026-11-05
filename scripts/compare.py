"""Side by side at chosen frames: reference (top row) vs render (bottom row).

usage: python compare.py <reference.mp4> <render: .mp4, or a folder of frame_%04d.png> <out.png> <frame> [<frame> ...]
Frame numbers are scene frames (1-based, as Blender counts); the reference is read at frame - 1.
"""
import os
import sys

import cv2
import numpy as np


def grab(src, frames):
    out = {}
    if os.path.isdir(src):
        for f in frames:
            out[f] = cv2.imread(os.path.join(src, "frame_%04d.png" % f))
        return out
    cap = cv2.VideoCapture(src)
    want = sorted(set(frames))
    i, k = 0, 0
    while k < len(want):
        ok, img = cap.read()
        if not ok:
            break
        i += 1                      # 1-based
        if i == want[k]:
            out[i] = img
            k += 1
    return out


def main(ref, ours, outp, frames):
    frames = [int(f) for f in frames]
    R = grab(ref, frames)
    O = grab(ours, frames)
    w, h = 384, 288
    top, bot = [], []
    for f in frames:
        a = cv2.resize(R[f], (w, h), interpolation=cv2.INTER_AREA) if R.get(f) is not None else np.zeros((h, w, 3), np.uint8)
        b = cv2.resize(O[f], (w, h), interpolation=cv2.INTER_AREA) if O.get(f) is not None else np.zeros((h, w, 3), np.uint8)
        cv2.putText(a, "ref %d" % f, (6, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
        cv2.putText(b, "ours %d" % f, (6, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
        top.append(a)
        bot.append(b)
    cv2.imwrite(outp, np.vstack([np.hstack(top), np.hstack(bot)]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
