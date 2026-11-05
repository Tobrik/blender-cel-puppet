"""For every held drawing of the reference: which of the 10 cycle poses it is, plus its mouth and eye crops, aligned to the eyes.

usage: python faces.py <reference.mp4> <track.npz> <out.npz>
Saves: start (first frame of each held drawing), hold (frames), pose (0-9), canon (10 x [x, y, angle, sep, tie_x, tie_y]),
mouth (N x 112 x 128 x 3 crops, BGR), eyes (N x 64 x 256 x 3 crops).
"""
import sys

import cv2
import numpy as np

MOUTH = (128, 112, 0.0, 0.80)  # crop size, and its centre in eye-separation units from the eye midpoint (x, y down)
EYES = (256, 64, 0.0, 0.0)
# the 10 cycle poses as first seen (eye midpoint x, eye-line angle); used to tell which pose a drawing is
SEED_X = np.array([579.2, 565.3, 408.3, 429.6, 446.3, 467.5, 481.4, 639.0, 618.1, 600.7])
SEED_A = np.array([5.1, 2.4, -17.3, -14.0, -6.5, -4.6, -2.2, 17.4, 12.0, 6.9])


def assign_poses(L, R, start):
    """Which cycle pose each drawing is: the nearest seed pose where the eyes were found, else the previous pose + 1.
    (The reference skips a drawing at 60.9 s, so the index mod 10 isn't enough.)"""
    pose = np.full(len(start), -1)
    for k, a in enumerate(start):
        l, r = L[a], R[a]
        if not np.isnan(l[0]):
            x, ang = (l[0] + r[0]) / 2, np.degrees(np.arctan2(r[1] - l[1], r[0] - l[0]))
            pose[k] = int(np.argmin((SEED_X - x) ** 2 + (4 * (SEED_A - ang)) ** 2))
    for k in range(len(pose)):
        if pose[k] < 0:
            pose[k] = (pose[k - 1] + 1) % 10 if k else 0
    return pose


def crop(f, mid, ang, sep, size):
    w, h, cx, cy = size
    s = 200.0 / sep                       # normalise: eye separation = 200 px
    M = cv2.getRotationMatrix2D((float(mid[0]), float(mid[1])), float(ang), s)
    # the crop centre, in the normalised frame, sits at mid + (cx, cy) * 200
    M[:, 2] += np.array([w / 2 - cx * 200, h / 2 - cy * 200]) - np.array(mid)
    return cv2.warpAffine(f, M, (w, h), flags=cv2.INTER_AREA, borderValue=(0, 0, 0))


def main(src, track, out):
    d = np.load(track)
    L, R, T, D = d["eyeL"], d["eyeR"], d["tie"], d["diff"]
    ch = [0] + [i for i in range(1, len(D)) if D[i] > 1.0]
    start = np.array(ch)
    hold = np.diff(np.append(start, len(D)))
    pose = assign_poses(L, R, start)
    canon = np.zeros((10, 6))
    for p in range(10):
        a = start[pose == p]
        l, r = L[a, :2], R[a, :2]
        ok = ~np.isnan(l[:, 0]) & ~np.isnan(r[:, 0])
        mid = np.median((l[ok] + r[ok]) / 2, 0)
        v = np.median(r[ok] - l[ok], 0)
        canon[p] = [mid[0], mid[1], np.degrees(np.arctan2(v[1], v[0])), np.hypot(*v),
                    np.nanmedian(T[a, 0]), np.nanmedian(T[a, 1])]
    cap = cv2.VideoCapture(src)
    mouths, eyes = [], []
    k, i = 0, 0
    while k < len(start):
        ok, f = cap.read()
        if not ok:
            break
        if i == start[k]:
            x, y, ang, sep = canon[pose[k], :4]
            mouths.append(crop(f, (x, y), ang, sep, MOUTH))
            eyes.append(crop(f, (x, y), ang, sep, EYES))
            k += 1
        i += 1
    np.savez_compressed(out, start=start, hold=hold, pose=pose, canon=canon, mouth=np.array(mouths), eyes=np.array(eyes))
    print(len(start), "drawings")
    for p in range(10):
        print("pose %d: x %.1f y %.1f ang %.1f sep %.1f tie %.1f, %.1f" % (p, *canon[p]))


if __name__ == "__main__":
    main(*sys.argv[1:4])
