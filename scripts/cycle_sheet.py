"""Consecutive frames of a video (e.g. one bob cycle), cropped and zoomed, in a grid: the way to check a joint (neck,
jaw, collar) on every frame, in-betweens included.

usage: python cycle_sheet.py <video.mp4> <out.png> --start <frame index (0-based)> [--count 24] [--crop x0,y0,x1,y1]
                             [--zoom 0.5] [--cols 8]
"""
import argparse

import cv2
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--count", type=int, default=24)
    ap.add_argument("--crop", default=None)
    ap.add_argument("--zoom", type=float, default=0.5)
    ap.add_argument("--cols", type=int, default=8)
    a = ap.parse_args()
    cap = cv2.VideoCapture(a.video)
    cap.set(cv2.CAP_PROP_POS_FRAMES, a.start)
    crop = [int(v) for v in a.crop.split(",")] if a.crop else None
    tiles = []
    for k in range(a.count):
        ok, im = cap.read()
        if not ok:
            break
        if crop:
            im = im[crop[1]:crop[3], crop[0]:crop[2]]
        im = cv2.resize(im, None, fx=a.zoom, fy=a.zoom, interpolation=cv2.INTER_AREA if a.zoom < 1 else cv2.INTER_CUBIC)
        cv2.putText(im, "+%d" % k, (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        tiles.append(cv2.copyMakeBorder(im, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
    while len(tiles) % a.cols:
        tiles.append(np.full_like(tiles[0], 255))
    cv2.imwrite(a.out, np.vstack([np.hstack(tiles[i:i + a.cols]) for i in range(0, len(tiles), a.cols)]))
    print("wrote", a.out, "(%d frames from %d)" % (a.count, a.start))


if __name__ == "__main__":
    main()
