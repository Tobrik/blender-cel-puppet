"""faces.npz (from faces.py) -> timeline.json: cluster the mouth crops, let a human (or you, looking at the sheet) name
the clusters, write the timeline the rig reads.

step 1:  python make_timeline.py faces.npz --k 10 --sheet mouth_clusters.png
         clusters every drawing's mouth crop (k-means on small grey crops), saves faces_clusters.npy next to faces.npz
         and a contact sheet (one row per cluster, up to 12 samples). Look at it.
step 2:  write labels.json naming each cluster, e.g. {"0": "CLOSED", "1": "A", "2": "A", "3": "TINY", ...}
         (several clusters can share a name; the names become the mouth sprites: CLOSED, TINY, O, A, E, GRIN, ...)
step 3:  python make_timeline.py faces.npz --labels labels.json --out timeline.json --audio-seconds 90.8
"""
import argparse
import json
import os

import cv2
import numpy as np


def features(mouths):
    g = np.array([cv2.resize(cv2.cvtColor(m, cv2.COLOR_BGR2GRAY), (32, 28), interpolation=cv2.INTER_AREA)
                  for m in mouths], np.float32) / 255
    g -= g.mean((1, 2), keepdims=True)
    g /= g.std((1, 2), keepdims=True) + 1e-6
    return g.reshape(len(g), -1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("faces")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--labels", default=None)
    ap.add_argument("--out", default="timeline.json")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--audio-seconds", type=float, default=None)
    ap.add_argument("--source", default="reference.mp4")
    a = ap.parse_args()
    d = np.load(a.faces)
    cpath = os.path.splitext(a.faces)[0] + "_clusters.npy"
    if a.labels is None:
        F = features(d["mouth"])
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-3)
        cv2.setRNGSeed(1)
        _, lab, _ = cv2.kmeans(F, a.k, None, crit, 8, cv2.KMEANS_PP_CENTERS)
        lab = lab.ravel()
        np.save(cpath, lab)
        rows = []
        for c in range(a.k):
            idx = np.nonzero(lab == c)[0]
            pick = idx[np.linspace(0, len(idx) - 1, min(12, len(idx))).astype(int)] if len(idx) else []
            tiles = [d["mouth"][i] for i in pick] + [np.zeros_like(d["mouth"][0])] * (12 - len(pick))
            row = np.hstack(tiles)
            cv2.putText(row, "%d (%d)" % (c, len(idx)), (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            rows.append(row)
            print("cluster %d: %d drawings" % (c, len(idx)))
        if a.sheet:
            cv2.imwrite(a.sheet, np.vstack(rows))
            print("contact sheet:", a.sheet)
        return
    lab = np.load(cpath)
    names = json.load(open(a.labels))
    mouth = [names[str(int(c))] for c in lab]
    order = list(dict.fromkeys(["CLOSED"] + sorted(set(mouth))))
    order = [m for m in order if m in set(mouth)]
    tl = dict(source=a.source, fps=a.fps, frames=int(d["start"][-1] + d["hold"][-1]),
              audio_seconds=a.audio_seconds, mouths=order, canon=d["canon"].round(2).tolist(),
              notes="One held drawing per entry. pose = which cycle drawing; canon = per cycle drawing: eye midpoint "
                    "x, y, eye-line angle (deg, + = clockwise), eye distance, body feature x, y (reference px).",
              drawings=[dict(start=int(s), hold=int(h), pose=int(p), mouth=m)
                        for s, h, p, m in zip(d["start"], d["hold"], d["pose"], mouth)])
    json.dump(tl, open(a.out, "w"), indent=0)
    print("timeline:", len(tl["drawings"]), "drawings, mouths", {m: mouth.count(m) for m in order}, "->", a.out)


if __name__ == "__main__":
    main()
