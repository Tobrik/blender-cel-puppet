"""Find the reference's drawing rate: which frames are new drawings and how long each is held ("on twos", 2-2-2-3-3...).

usage: python drawing_rate.py <reference.mp4> [--crop x0,y0,x1,y1] [--thresh 1.0] [--out diffs.npy]
Crop to the character (leave out subtitles / overlays that change on their own). Prints the hold lengths of the first
drawings and their histogram; a repeating pattern there is the animation's rhythm.
"""
import argparse
from collections import Counter

import cv2
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--crop", default=None, help="x0,y0,x1,y1 (px) of the region that holds the animation")
    ap.add_argument("--thresh", type=float, default=1.0, help="mean abs grey change that counts as a new drawing")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    crop = [int(v) for v in a.crop.split(",")] if a.crop else None
    prev, d = None, []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if crop:
            f = f[crop[1]:crop[3], crop[0]:crop[2]]
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
        d.append(0.0 if prev is None else float(np.abs(g - prev).mean()))
        prev = g
    d = np.array(d)
    if a.out:
        np.save(a.out, d)
    new = np.nonzero(d > a.thresh)[0]
    holds = np.diff(np.concatenate([[0], new])).tolist()
    print("%d frames at %.3f fps, %d drawing changes (%.2f drawings/s)" % (len(d), fps, len(new), len(new) / len(d) * fps))
    print("first holds:", holds[:40])
    print("hold histogram:", sorted(Counter(holds).items()))


if __name__ == "__main__":
    main()
