"""Kaguya x Fukkireta v4: the Blender build (run inside Blender).

    PROJECT = r"C:/path/to/this/folder"
    exec(open(PROJECT + "/kaguya_v4.py", encoding="utf-8").read()); build(); save()

(through the Blender MCP: every call starts with a fresh namespace, so set PROJECT and exec again in each call), then
still(frame) for a check frame, and the background render (render_cmd()). Imported from plain Python with a stub `bpy`
(neck_shade.py, rigsim.py), the rig part (everything above "Blender") works without Blender.

What it builds, in its own scene "Kaguya Fukkireta v4":
- Kaguya as cel-puppet layers (parts/tex/*.png at 2x, cut from the upscaled art by parts.py) on textured grid meshes.
- One shape key per bob-cycle pose (10). Each pose: the head stood up straight, then tilted / turned / moved the way Teto's
  head is in that drawing of the reference (analysis/timeline.json, scaled to Kaguya), the body swaying with it, the neck
  bending between them, and the hanging locks + ribbon tails trailing behind (a damped spring, run over the cycle).
- A controller ("KF4 Control") with an animated "pose" property, one value per frame: every drawing of the reference lands
  on its own pose exactly on the reference's frame (2-2-2-3-3 holds, 12.5 drawings/s), and the frames between show
  in-betweens (a monotone cubic through the 10 poses), so the bob moves on every frame at 30 fps. The shape keys (one per
  frame of the 24-frame cycle, plus a few for the reference's 3 irregular drawings) follow through drivers.
- One mouth object whose "mouth" property picks one of 6 mouth textures, again per drawing (the reference's lip-sync).
- The background: flat pink, soft white baguette outlines, scrolling diagonally like the reference.
- The reference's own audio in the sequencer, and an H.264 + AAC MP4 as output.
"""
import json
import math
import os

import bpy
import numpy as np

# this project's folder: PROJECT when exec()'d in Blender (no __file__ there), else this file's folder
V4 = globals().get("PROJECT") or (os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else None)
assert V4, 'set PROJECT = r"<this folder>" before exec()-ing kaguya_v4.py in Blender'
V4 = V4.replace("\\", "/")
TEX = V4 + "/parts/tex"
TIMELINE = V4 + "/analysis/timeline.json"
AUDIO = V4 + "/fukkireta_audio.m4a"       # the reference's own audio track: ffmpeg -i reference.mp4 -vn -c:a copy fukkireta_audio.m4a
VIDEO = V4 + "/render/kaguya_fukkireta.mp4"   # (give every version its own name: players cache the old file)
BLEND = V4 + "/kaguya_v4.blend"
SCENE = "Kaguya Fukkireta v4"
RES, FPS = (1440, 1080), 30
FRAMES = 2724                       # 90.8 s, the reference's length (its audio)
PX = 1000.0                         # reference px per Blender unit

# ---------- Kaguya's reference (reference px, y down) ----------
EYE_L, EYE_R = np.array([494.0, 482.4]), np.array([742.2, 566.1])
E0 = (EYE_L + EYE_R) / 2
TILT = math.atan2(EYE_R[1] - EYE_L[1], EYE_R[0] - EYE_L[0])     # the drawing's head tilt (clockwise on screen)
SEP = float(np.hypot(*(EYE_R - EYE_L)))
# she's stood up straight around the top of her neck (its centre at the jaw), so at rest the head sits centred on the neck
# (around the chin, as in v4.1, it sat 6.5 px left of it: every lean to the left looked bigger than one to the right)
NECK_TOP = np.array([511.0, 785.0])

# ---------- Teto (reference video px) -> Kaguya ----------
TETO_SEP = 200.4
K = SEP / TETO_SEP                                                # Kaguya px per Teto px
TETO_REST = np.array([523.5, 297.0])                              # eye midpoint, upright (the cycle's centre, top)
TETO_TIE_X = 521.4
SCREEN_EYE = np.array([785.3, 445.5])                             # where her (upright) eyes sit in the 1440x1080 frame

# ---------- the rig's feel ----------
YAW_GAIN, YAW_BASE = 0.55, math.radians(-3.0)                     # head turn: a share of Teto's, and a small correction
HEAD_RX, HEAD_RY, HEAD_CY = 280.0, 400.0, -30.0                   # the head as an ellipsoid for the turn (local px)
# The neck bends evenly along its whole visible length: with the head down to y TOP, with the body from where it meets
# the collar (y L on the left, R on the right, blended between x0 and x1), linearly in between. The joints with the
# collar stay put, the outlines stay straight, and the lean is spread over ~110 px (v4.1 squeezed it into 52, a kink
# that looked like a dislocated neck).
# (on the left the bend ends at 800, above the collar's back: that grey pocket between the lapel and the neck keeps its
#  drawn wedge shape, instead of being squeezed into a grey "leaf" when the head leans left)
NECK_BEND = dict(top=740.0, L=800.0, R=848.0, x=(420.0, 560.0))
# Teto's head slides far more than her body (her neck is hidden under her hair); Kaguya's shoulders follow a share of the
# head's slide (at the top of the neck) on top of Teto's tie sway, so her neck doesn't have to shear as much.
BODY_FOLLOW = 0.45
# Hanging parts: `straight` = how much of the stand-up rotation they undo (the left lock hangs plumb in the tilted
# drawing, so standing her up would swing it inward; the right lock and the ribbons hang right once she's upright),
# `roll` = how much of each pose's tilt they undo (they keep hanging down while the head tilts).
LOCKS = {   # root (reference px), the weight ramp along the lock
    "L": dict(root=(365.0, 600.0), y=(640.0, 960.0), straight=0.6, roll=0.5),
    "R": dict(root=(880.0, 560.0), y=(560.0, 960.0), straight=0.0, roll=0.5),
}
RIBBONS = {"ribbon_L": dict(root=(305.0, 470.0), straight=0.0, roll=0.3),
           "ribbon_R": dict(root=(800.0, 650.0), straight=0.0, roll=0.3)}
SPRING = dict(T=18.0, zeta=0.32, gain=0.55, L=330.0, max=math.radians(22))
SPRING_RIB = dict(T=22.0, zeta=0.28, gain=0.30, L=260.0, max=math.radians(10))

# ---------- background (output px) ----------
CELL = (418.0, 428.0)
SCROLL = (0.254 * 1.5, 0.182 * 1.5)                               # px per frame, right and down

TEX_FILTER = "Closest"              # texture lookup: 2x textures, 16 jittered samples per px do the filtering (sharpest)
FILTER_SIZE = 1.0                   # render pixel filter (px)
SAMPLES = 16                        # EEVEE render samples
CRF = 14                            # H.264 quality (lower = better; ~3 Mbps at 20, this is well above)

LAYERS = [  # name, grid cell (px), depth (further = drawn first)
    ("ribbon_L", 16, 0.07), ("ribbon_R", 16, 0.06), ("body", 28, 0.05), ("neck", 10, 0.04), ("body_front", 28, 0.035),
    ("head", 12, 0.03),
]
MOUTHS = ["closed", "tiny", "o", "a", "e", "grin"]                # the timeline's CLOSED, TINY, O, A, E, GRIN


# ======================================================================================================================
# the rig (pure numpy, reference px)
# ======================================================================================================================

def rot(P, a, c=(0.0, 0.0)):
    """Rotate points P (N x 2, y down) by a (radians, + = clockwise on screen) around c."""
    c = np.asarray(c, float)
    ca, sa = math.cos(a), math.sin(a)
    Q = P - c
    return np.stack([Q[:, 0] * ca - Q[:, 1] * sa, Q[:, 0] * sa + Q[:, 1] * ca], 1) + c


def smoothstep(a, b, v):
    t = np.clip((np.asarray(v, float) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


E_UP = rot(E0[None], -TILT, NECK_TOP)[0]                          # her eye midpoint once she stands straight
CAM = E_UP + (np.array([RES[0] / 2, RES[1] / 2]) - SCREEN_EYE)     # the frame's centre, in reference px


def load_timeline():
    tl = json.load(open(TIMELINE, encoding="utf-8"))
    return tl


def poses(tl):
    """The 10 cycle poses (Kaguya units), symmetrised (pose p and p+5 are mirror images in Teto's cycle)."""
    C = np.array(tl["canon"])            # x, y, angle, sep, tie_x, tie_y
    out = []
    for p in range(10):
        q = (p + 5) % 10
        sgn = 1.0 if C[p, 2] > 0 else -1.0
        dx = 0.5 * ((C[p, 0] - TETO_REST[0]) - (C[q, 0] - TETO_REST[0]))
        dy = 0.5 * ((C[p, 1] - TETO_REST[1]) + (C[q, 1] - TETO_REST[1]))
        roll = 0.5 * (C[p, 2] - C[q, 2])
        yaw = 0.5 * (math.degrees(math.acos(min(1.0, C[p, 3] / C[:, 3].max())))
                     + math.degrees(math.acos(min(1.0, C[q, 3] / C[:, 3].max()))))
        body = 0.5 * ((C[p, 4] - TETO_TIE_X) - (C[q, 4] - TETO_TIE_X))
        out.append(dict(dE=np.array([dx * K, dy * K]), roll=math.radians(roll),
                        yaw=YAW_BASE + YAW_GAIN * math.radians(yaw) * sgn, body=np.array([body * K, 0.0])))
    return out


# ---------- the motion between the drawings (in-betweens on every frame, 30 fps) ----------
HOLDS = [2, 2, 2, 3, 3, 2, 2, 2, 3, 3]                            # frames each of the cycle's 10 drawings lasts
CYCLE = int(sum(HOLDS))                                           # 24 frames
CYCLE_START = [int(v) for v in np.concatenate([[0], np.cumsum(HOLDS)[:-1]])]   # the cycle frame each drawing lands on


def _vec(ps):
    return np.array([ps["dE"][0], ps["dE"][1], ps["roll"], ps["yaw"], ps["body"][0]], float)


def _pose(v):
    return dict(dE=np.array([v[0], v[1]]), roll=float(v[2]), yaw=float(v[3]), body=np.array([v[4], 0.0]))


def key_slopes(keys):
    """Each key pose's parameters and their slopes (per frame) for a periodic monotone cubic through the 10 keys at
    their cycle frames: smooth, no overshoot, and flat at the turning points (the head eases into each lean)."""
    V = np.array([_vec(k) for k in keys])
    n = len(V)
    d = np.array([(CYCLE_START[(i + 1) % n] - CYCLE_START[i]) % CYCLE for i in range(n)], float)
    sec = (np.roll(V, -1, 0) - V) / d[:, None]                   # key i -> i + 1
    m = np.zeros_like(V)
    for i in range(n):
        d0, d1 = d[i - 1], d[i]
        w1, w2 = 2 * d1 + d0, d1 + 2 * d0
        for j in range(V.shape[1]):
            s0, s1 = sec[i - 1, j], sec[i, j]
            if s0 * s1 > 0:
                m[i, j] = (w1 + w2) / (w1 / s0 + w2 / s1)
    return V, m


def between(V, m, p, q, f, dur):
    """The pose a fraction f of the way from key p to key q, `dur` frames apart (cubic Hermite)."""
    h00, h10 = 2 * f ** 3 - 3 * f ** 2 + 1, f ** 3 - 2 * f ** 2 + f
    h01, h11 = -2 * f ** 3 + 3 * f ** 2, f ** 3 - f ** 2
    return h00 * V[p] + h10 * dur * m[p] + h01 * V[q] + h11 * dur * m[q]


def follow(ps):
    """The shoulders take BODY_FOLLOW of the head's slide (measured at the top of the neck) on top of the tie's sway."""
    rel = head_T(NECK_TOP[None], ps, warp=False)[0, 0] - NECK_TOP[0] - ps["body"][0]
    ps["body"] = ps["body"] + np.array([BODY_FOLLOW * rel, 0.0])
    return ps


def spec_of(p, q, k, h):
    """Which in-between frame k of h, from drawing p to the next drawing q, is: (p, q, k, h) normalised so that every
    regular one is one of the cycle's 24 and every key frame (k = 0) is the key pose itself."""
    if k == 0 or q == p or (q == (p + 1) % 10 and h == HOLDS[p]):
        return (p, (p + 1) % 10, k if (q == (p + 1) % 10 and h == HOLDS[p]) else 0, HOLDS[p])
    return (p, q, k, h)


def frame_poses(tl):
    """Every distinct frame pose of the clip: the cycle's 24 (key drawings on their own frames, in-betweens on the
    others) in cycle order, then the few the irregular drawings need. -> (poses, specs, the clip's spec per drawing frame)"""
    keys = poses(tl)
    V, m = key_slopes(keys)
    specs = [(p, (p + 1) % 10, k, HOLDS[p]) for p in range(10) for k in range(HOLDS[p])]
    draw = tl["drawings"]
    per_frame = []                                               # (reference frame, spec)
    for i, d in enumerate(draw):
        p = d["pose"]
        if i + 1 < len(draw):
            q, h = draw[i + 1]["pose"], draw[i + 1]["start"] - d["start"]
        else:
            q, h = p, FRAMES - d["start"]
        for k in range(h):
            s = spec_of(p, q, k, h)
            if s not in specs:
                specs.append(s)
            per_frame.append((d["start"] + k, s))
    out = []
    for p, q, k, h in specs:
        out.append(follow(_pose(between(V, m, p, q, k / h, h))))
    return out, specs, per_frame


def yaw_dx(L, psi):
    """Horizontal shift of head-local points for a turn by psi: the head as an ellipsoid (features slide, the silhouette
    stays put)."""
    v = (L[:, 1] - HEAD_CY) / HEAD_RY
    r = HEAD_RX * np.sqrt(np.clip(1 - v * v, 0, 1))
    u = L[:, 0]
    rs = np.maximum(r, 1e-6)
    t = np.clip(u / rs, -1, 1)
    inside = r * np.sin(np.arcsin(t) + psi) - np.clip(u, -r, r)
    return np.where(r > 1e-6, inside, 0.0)


def head_T(P, ps, warp=True):
    Q = rot(P, -TILT, NECK_TOP)
    L = Q - E_UP
    if warp:
        L = L.copy()
        L[:, 0] += yaw_dx(L, ps["yaw"])
    return rot(L, ps["roll"]) + E_UP + ps["dE"]


def hang_angle(part, ps):
    """The extra rotation that keeps a hanging part hanging down (rad, + = clockwise)."""
    return part["straight"] * TILT - part["roll"] * ps["roll"]


def body_T(P, ps):
    return P + ps["body"]


def lock_weight(P, side):
    """How much of a lock's swing each head vertex takes: down the lock, and (near the jaw) only on the lock's side so
    the face doesn't bend. Below the jaw there is only hair, so there the whole strand swings (no bent tips)."""
    x, y = P[:, 0], P[:, 1]
    lk = LOCKS[side]
    wy = smoothstep(lk["y"][0], lk["y"][1], y)
    if side == "L":
        below = smoothstep(770, 830, y)
        wx_jaw = 1 - smoothstep(400, 440, x)
        wx_low = 1 - smoothstep(470, 520, x)
    else:
        below = smoothstep(790, 840, y)
        xth = 830 - (y - 600) * 0.33
        wx_jaw = smoothstep(xth - 30, xth + 10, x)
        wx_low = smoothstep(640, 680, x)
    return wy * (wx_jaw * (1 - below) + wx_low * below)


def spring_cycle(xs, T, zeta, gain, L, max, cycles=8):
    """Damped-spring follow-through over the periodic cycle: the angle (rad, + = tip to the left) on each of its frames.
    xs: the hanging part's root x on each of the cycle's 24 frames (the smooth motion)."""
    k = (2 * math.pi / T) ** 2
    c = 2 * zeta * math.sqrt(k)
    x = np.tile(np.asarray(xs, float), cycles)
    phi, om, out = 0.0, 0.0, []
    for t in range(2, len(x)):
        a = x[t] - 2 * x[t - 1] + x[t - 2]
        om += -k * phi - c * om + gain * a / L
        phi += om
        out.append(phi)
    out = np.array([0, 0] + out)
    return np.clip(out[-len(xs):], -max, max)                    # the last cycle (settled)


def pose_points(name, P, pose_list, swings):
    """Every vertex P (reference px) of layer `name`, for each pose -> list of (N x 2) arrays."""
    res = []
    for p, ps in enumerate(pose_list):
        if name in ("body", "body_front"):          # (the front body: the lapels / dress, in front of the neck)
            Q = body_T(P, ps)
        elif name == "neck":
            nb = NECK_BEND
            bottom = np.interp(P[:, 0], nb["x"], [nb["L"], nb["R"]])
            t = np.clip((P[:, 1] - nb["top"]) / (bottom - nb["top"]), 0, 1)[:, None]
            Q = (1 - t) * head_T(P, ps, warp=False) + t * body_T(P, ps)
        elif name.startswith("ribbon"):
            rb = RIBBONS[name]
            root = np.array(rb["root"])
            Q = head_T(P, ps, warp=False)
            R = head_T(root[None], ps, warp=False)[0]
            ang = hang_angle(rb, ps) + swings[name][p]
            ramp = smoothstep(root[1] - 30, root[1] + 120, P[:, 1])
            Q = _rot_each(Q, ang * ramp, R)
        elif name in ("head", "mouth"):
            Q = head_T(P, ps, warp=True)
            if name == "head":
                for side in ("L", "R"):
                    h = lock_weight(P, side)
                    sel = h > 1e-4
                    if not sel.any():
                        continue
                    root = np.array(LOCKS[side]["root"])
                    R = head_T(root[None], ps, warp=True)[0]
                    ang = (hang_angle(LOCKS[side], ps) + swings["lock_" + side][p]) * h[sel]
                    Q[sel] = _rot_each(Q[sel], ang, R)
        else:
            raise ValueError(name)
        res.append(Q)
    return res


def _rot_each(Q, angs, c):
    ca, sa = np.cos(angs), np.sin(angs)
    d = Q - c
    return np.stack([d[:, 0] * ca - d[:, 1] * sa, d[:, 0] * sa + d[:, 1] * ca], 1) + c


def swings_for(pose_list, specs):
    """Root x of each hanging part on each of the cycle's frames, then its spring follow-through; the extra frame poses
    (irregular drawings) take the swing at their place in the cycle. -> {part: angle per frame pose}"""
    cyc = pose_list[:CYCLE]
    t = []
    for p, q, k, h in specs:
        span = (CYCLE_START[q] - CYCLE_START[p]) % CYCLE
        t.append(CYCLE_START[p] + k / h * span)
    out = {}
    parts = [("lock_" + s, np.array(LOCKS[s]["root"]), True, SPRING) for s in ("L", "R")]
    parts += [(n, np.array(rb["root"]), False, SPRING_RIB) for n, rb in RIBBONS.items()]
    for name, root, warp, sp in parts:
        xs = [head_T(root[None], ps, warp=warp)[0, 0] for ps in cyc]
        a = spring_cycle(xs, **sp)
        out[name] = np.interp(t, np.arange(CYCLE + 1), np.append(a, a[0]))
    return out


# ======================================================================================================================
# Blender
# ======================================================================================================================

def to_world(Q):
    """Reference px -> Blender (x, z) around the frame's centre."""
    return np.stack([(Q[:, 0] - CAM[0]) / PX, -(Q[:, 1] - CAM[1]) / PX], 1)


def grid(box, cell):
    x0, y0, x1, y1 = box
    nx = max(2, int(math.ceil((x1 - x0) / cell)) + 1)
    ny = max(2, int(math.ceil((y1 - y0) / cell)) + 1)
    xs, ys = np.linspace(x0, x1, nx), np.linspace(y0, y1, ny)
    X, Y = np.meshgrid(xs, ys)
    P = np.stack([X.ravel(), Y.ravel()], 1)
    uv = np.stack([(P[:, 0] - x0) / (x1 - x0), 1 - (P[:, 1] - y0) / (y1 - y0)], 1)
    faces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + nx, a + nx + 1, a + 1))
    return P, uv, faces


def enum_items(rna, prop):
    return [i.identifier for i in rna.bl_rna.properties[prop].enum_items]


def image(path):
    img = bpy.data.images.load(path, check_existing=True)
    img.reload()                                   # (the file may have changed since it was first loaded)
    img.alpha_mode = "STRAIGHT"
    return img


def emission_material(name, images, index_prop=None):
    """Unlit (exact color) material with alpha. Several images: the object's `index_prop` picks one."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    texs = []
    for k, img in enumerate(images):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = img
        t.interpolation = TEX_FILTER
        t.extension = "CLIP"
        t.location = (-700, -260 * k)
        texs.append(t)
    if len(texs) == 1:
        col, alpha = texs[0].outputs["Color"], texs[0].outputs["Alpha"]
    else:
        attr = nt.nodes.new("ShaderNodeAttribute")
        attr.attribute_type = "OBJECT"
        attr.attribute_name = index_prop
        col, alpha = texs[0].outputs["Color"], texs[0].outputs["Alpha"]
        for k in range(1, len(texs)):
            cmp_ = nt.nodes.new("ShaderNodeMath")
            cmp_.operation = "COMPARE"
            nt.links.new(attr.outputs["Fac"], cmp_.inputs[0])
            cmp_.inputs[1].default_value = float(k)
            cmp_.inputs[2].default_value = 0.5
            mc = nt.nodes.new("ShaderNodeMix")
            mc.data_type = "RGBA"
            nt.links.new(cmp_.outputs[0], mc.inputs["Factor"])
            nt.links.new(col, mc.inputs[6])
            nt.links.new(texs[k].outputs["Color"], mc.inputs[7])
            ma = nt.nodes.new("ShaderNodeMix")
            ma.data_type = "FLOAT"
            nt.links.new(cmp_.outputs[0], ma.inputs["Factor"])
            nt.links.new(alpha, ma.inputs[2])
            nt.links.new(texs[k].outputs["Alpha"], ma.inputs[3])
            col, alpha = mc.outputs[2], ma.outputs[0]
    nt.links.new(col, emit.inputs["Color"])
    emit.inputs["Strength"].default_value = 1.0
    nt.links.new(alpha, mix.inputs["Fac"])
    nt.links.new(transp.outputs[0], mix.inputs[1])
    nt.links.new(emit.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    if "surface_render_method" in mat.bl_rna.properties:
        mat.surface_render_method = "BLENDED"
    elif "blend_method" in mat.bl_rna.properties:
        mat.blend_method = "BLEND"
    return mat


def atlas_material(name, img, info, index_prop="pose"):
    """Unlit material whose texture is one tile of an atlas, picked by the object's `index_prop` (the neck: its shading
    baked per frame pose by neck_shade.py, so the shadow under the chin follows the head)."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_type, attr.attribute_name = "OBJECT", index_prop
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image, tex.interpolation, tex.extension = img, TEX_FILTER, "CLIP"

    def madd(a, b, c):                                   # a * b + c (each a socket or a number)
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = "MULTIPLY_ADD"
        for k, v in enumerate((a, b, c)):
            if isinstance(v, (int, float)):
                n.inputs[k].default_value = float(v)
            else:
                nt.links.new(v, n.inputs[k])
        return n.outputs[0]

    cols, m = info["cols"], info["margin"]
    tw, th, W, H = info["tile_w"], info["tile_h"], info["width"], info["height"]
    TW, TH = tw + 2 * m, th + 2 * m
    fl = nt.nodes.new("ShaderNodeMath")
    fl.operation = "FLOOR"
    nt.links.new(madd(attr.outputs["Fac"], 1.0 / cols, 0.5 / cols), fl.inputs[0])
    row = fl.outputs[0]
    col = madd(row, -float(cols), attr.outputs["Fac"])
    nt.links.new(tc.outputs["UV"], sep.inputs[0])
    # U = (col * TW + m + u * tw) / W ;  V = 1 - (row * TH + m + (1 - v) * th) / H   (tiles laid out from the top)
    nt.links.new(madd(sep.outputs[0], tw / W, madd(col, TW / W, m / W)), comb.inputs[0])
    nt.links.new(madd(sep.outputs[1], th / H, madd(row, -TH / H, 1 - (m + th) / H)), comb.inputs[1])
    nt.links.new(comb.outputs[0], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
    emit.inputs["Strength"].default_value = 1.0
    nt.links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(transp.outputs[0], mix.inputs[1])
    nt.links.new(emit.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    if "surface_render_method" in mat.bl_rna.properties:
        mat.surface_render_method = "BLENDED"
    elif "blend_method" in mat.bl_rna.properties:
        mat.blend_method = "BLEND"
    return mat


def make_mesh_object(sc, name, P, uv, faces, depth, mat):
    me = bpy.data.meshes.new(name)
    W = to_world(P)
    verts = [(float(x), 0.0, float(z)) for x, z in W]
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name="UVMap")
    loop_uv = np.array([uv[v] for f in faces for v in f], np.float32)
    uvl.data.foreach_set("uv", loop_uv.ravel())
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location = (0.0, depth, 0.0)
    sc.collection.objects.link(ob)
    return ob


def add_pose_keys(ob, pose_coords, ctrl):
    ob.shape_key_add(name="Basis", from_mix=False)
    for p, Q in enumerate(pose_coords):
        kb = ob.shape_key_add(name="pose%d" % p, from_mix=False)
        W = to_world(Q)
        co = np.zeros((len(W), 3), np.float32)
        co[:, 0], co[:, 2] = W[:, 0], W[:, 1]
        kb.data.foreach_set("co", co.ravel())
        kb.slider_min, kb.slider_max = 0.0, 1.0
        fc = kb.driver_add("value")
        drv = fc.driver
        drv.type = "SCRIPTED"
        var = drv.variables.new()
        var.name, var.type = "pose", "SINGLE_PROP"
        var.targets[0].id_type = "OBJECT"
        var.targets[0].id = ctrl
        var.targets[0].data_path = '["pose"]'
        drv.expression = "1.0 if pose == %d else 0.0" % p
        if not drv.is_simple_expression:
            print("warning: driver isn't a simple expression:", drv.expression)


def fcurves_of(owner):
    """The F-curves animating an ID (layered actions in Blender 4.4+, plain ones before)."""
    ad = owner.animation_data
    if ad is None or ad.action is None:
        return []
    act = ad.action
    slot = getattr(ad, "action_slot", None)
    if slot is not None:
        try:
            from bpy_extras import anim_utils
            cb = anim_utils.action_get_channelbag_for_slot(act, slot)
            if cb is not None:
                return list(cb.fcurves)
        except Exception:
            pass
    return list(getattr(act, "fcurves", []))


def keyframes(owner, prop, frames, values):
    """Constant (held) keys on a custom property, one per drawing."""
    last = None
    for f, v in zip(frames, values):
        if v == last:
            continue
        owner[prop] = v
        owner.keyframe_insert('["%s"]' % prop, frame=f)
        last = v
    for fc in fcurves_of(owner):
        if fc.data_path == '["%s"]' % prop:
            for k in fc.keyframe_points:
                k.interpolation = "CONSTANT"
            fc.update()


def clear_scene():
    old = bpy.data.scenes.get(SCENE)
    if old:
        datas = [ob.data for ob in old.objects if ob.data is not None]
        for ob in list(old.objects):
            bpy.data.objects.remove(ob)
        for data in datas:
            if data.users == 0:
                if isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
                elif isinstance(data, bpy.types.Camera):
                    bpy.data.cameras.remove(data)
        bpy.data.scenes.remove(old)


def setup_render(sc):
    r = sc.render
    try:
        r.engine = "BLENDER_EEVEE"
    except TypeError:
        r.engine = "BLENDER_EEVEE_NEXT"
    r.resolution_x, r.resolution_y, r.resolution_percentage = RES[0], RES[1], 100
    r.fps, r.fps_base = FPS, 1.0
    sc.frame_start, sc.frame_end = 1, FRAMES
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure, sc.view_settings.gamma = 0.0, 1.0
    r.film_transparent = False
    if hasattr(r, "filter_size"):
        r.filter_size = FILTER_SIZE
    ee = sc.eevee
    if hasattr(ee, "taa_render_samples"):
        ee.taa_render_samples = SAMPLES
    if hasattr(ee, "taa_samples"):
        ee.taa_samples = 8
    for flag in ("use_shadows", "use_raytracing", "use_gtao", "use_bloom", "use_ssr", "use_volumetric_shadows"):
        if hasattr(ee, flag):
            try:
                setattr(ee, flag, False)
            except Exception:
                pass


def setup_output(sc, path=VIDEO):
    r = sc.render
    ims = r.image_settings
    if "media_type" in ims.bl_rna.properties:
        ims.media_type = "VIDEO"
    ims.file_format = "FFMPEG"
    ff = r.ffmpeg
    ff.format = "MPEG4"
    ff.codec = "H264"
    ff.constant_rate_factor = "CUSTOM"
    ff.custom_constant_rate_factor = CRF
    ff.ffmpeg_preset = "BEST"
    ff.gopsize = 30
    ff.audio_codec = "AAC"
    ff.audio_bitrate = 192
    ff.audio_channels = "STEREO"
    ff.audio_mixrate = 44100
    r.filepath = os.path.abspath(path).replace("\\", "/")
    r.use_file_extension = False


def add_audio(sc):
    se = sc.sequence_editor_create()
    strips = getattr(se, "strips", None)
    if strips is None:
        strips = se.sequences
    for st in list(strips):
        strips.remove(st)
    # the reference's video starts 1/30 s after its audio (its frame 0 is shown at t = 0.033 s): reference frame k is
    # our frame k + 1, so the sound starts at frame 0
    strips.new_sound(name="Fukkireta", filepath=AUDIO, channel=1, frame_start=0)


def add_background(sc):
    img = image(TEX + "/bg_tile.png")
    img.alpha_mode = "NONE"
    mat = bpy.data.materials.get("KF4 bg") or bpy.data.materials.new("KF4 bg")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image, tx.interpolation, tx.extension = img, "Linear", "REPEAT"
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tx.inputs["Vector"])
    nt.links.new(tx.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs[0], out.inputs["Surface"])
    # object coords are Blender units (1 unit = PX output px): one cell per texture repeat
    mp.inputs["Scale"].default_value = (PX / CELL[0], PX / CELL[1], 1.0)
    # scroll: right and down by SCROLL px per frame
    for axis, expr in ((0, "-frame * %f" % (SCROLL[0] / CELL[0])), (1, "frame * %f" % (SCROLL[1] / CELL[1]))):
        fc = mp.inputs["Location"].driver_add("default_value", axis)
        fc.driver.type = "SCRIPTED"
        fc.driver.expression = expr
    me = bpy.data.meshes.new("KF4 bg")
    w, h = RES[0] / PX / 2 + 0.05, RES[1] / PX / 2 + 0.05
    me.from_pydata([(-w, -h, 0), (w, -h, 0), (w, h, 0), (-w, h, 0)], [], [(0, 1, 2, 3)])
    me.materials.append(mat)
    ob = bpy.data.objects.new("KF4 bg", me)
    ob.rotation_euler = (math.pi / 2, 0, 0)
    ob.location = (0, 1.0, 0)
    sc.collection.objects.link(ob)
    return ob


def build(frames=FRAMES):
    tl = load_timeline()
    pose_list, specs, per_frame = frame_poses(tl)
    swings = swings_for(pose_list, specs)
    boxes = json.load(open(TEX + "/parts.json"))

    clear_scene()
    sc = bpy.data.scenes.new(SCENE)
    for win in bpy.context.window_manager.windows:
        win.scene = sc
    setup_render(sc)
    sc.frame_end = frames

    cam_data = bpy.data.cameras.new("KF4 Cam")
    cam_data.type, cam_data.ortho_scale = "ORTHO", RES[0] / PX
    cam_data.clip_start, cam_data.clip_end = 0.1, 100
    cam = bpy.data.objects.new("KF4 Cam", cam_data)
    cam.location, cam.rotation_euler = (0, -10, 0), (math.pi / 2, 0, 0)
    sc.collection.objects.link(cam)
    sc.camera = cam

    ctrl = bpy.data.objects.new("KF4 Control", None)
    sc.collection.objects.link(ctrl)
    ctrl["pose"] = 0

    add_background(sc)
    atlas = json.load(open(TEX + "/neck_atlas.json"))
    assert atlas["count"] == len(pose_list), "neck_atlas.png is out of date: run neck_shade.py"
    objs = {}
    for name, cell, depth in LAYERS:
        P, uv, faces = grid(boxes[name], cell)
        if name == "neck":                       # its shading per frame pose (the shadow under the chin follows the head)
            mat = atlas_material("KF4 " + name, image(TEX + "/neck_atlas.png"), atlas)
        else:
            mat = emission_material("KF4 " + name, [image(TEX + "/%s.png" % name)])
        ob = make_mesh_object(sc, "KF4 " + name, P, uv, faces, depth, mat)
        add_pose_keys(ob, pose_points(name, P, pose_list, swings), ctrl)
        objs[name] = ob
    objs["neck"]["pose"] = 0
    # the mouth: one quad grid, 6 textures picked by its "mouth" property
    P, uv, faces = grid(boxes["mouth_closed"], 10)
    mat = emission_material("KF4 mouth", [image(TEX + "/mouth_%s.png" % m) for m in MOUTHS], index_prop="mouth")
    mouth = make_mesh_object(sc, "KF4 mouth", P, uv, faces, 0.02, mat)
    mouth["mouth"] = 0
    add_pose_keys(mouth, pose_points("mouth", P, pose_list, swings), ctrl)

    # the timeline: the pose on every frame (each drawing's own pose on its first frame, in-betweens after it), the
    # mouth per drawing
    names = tl["mouths"]
    draw = [d for d in tl["drawings"] if d["start"] < frames]
    starts = [d["start"] + 1 for d in draw]          # reference frame 0 = scene frame 1
    fr = [(f + 1, specs.index(s)) for f, s in per_frame if f + 1 <= frames]
    keyframes(ctrl, "pose", [f for f, _ in fr], [i for _, i in fr])
    keyframes(objs["neck"], "pose", [f for f, _ in fr], [i for _, i in fr])     # (picks the neck's shading tile)
    keyframes(mouth, "mouth", starts, [names.index(d["mouth"]) for d in draw])

    add_audio(sc)
    setup_output(sc)
    sc.frame_set(1)
    # every drawing's first frame shows exactly that drawing's pose
    at = dict(per_frame)
    bad = [d["start"] for d in draw if at[d["start"]][0] != d["pose"] or at[d["start"]][2] != 0]
    print("built: %d drawings, %d frame poses (%d extra), drawings not on their pose: %d"
          % (len(draw), len(pose_list), len(pose_list) - CYCLE, len(bad)))
    print("roll per cycle frame (deg):", np.round([math.degrees(p["roll"]) for p in pose_list[:CYCLE]], 1).tolist())
    print("swings (deg):", {k: np.round(np.degrees(v[:CYCLE]), 1).tolist() for k, v in swings.items()})
    return sc


def still(frame, path=None, percent=50, only=None):
    """Render one frame (to a PNG) for checking. only: render just these layers (e.g. ["body"]) over the background."""
    sc = bpy.data.scenes[SCENE]
    hidden = []
    if only:
        keep = {"KF4 " + n for n in only} | {"KF4 bg"}
        for ob in sc.objects:
            if ob.type == "MESH" and ob.name not in keep and not ob.hide_render:
                ob.hide_render = True
                hidden.append(ob)
    try:
        return _still(sc, frame, path, percent)
    finally:
        for ob in hidden:
            ob.hide_render = False


def _still(sc, frame, path, percent):
    sc.frame_set(frame)
    r = sc.render
    old = (r.image_settings.file_format, r.filepath, r.resolution_percentage,
           getattr(r.image_settings, "media_type", None))
    if "media_type" in r.image_settings.bl_rna.properties:
        r.image_settings.media_type = "IMAGE"
    r.image_settings.file_format = "PNG"
    r.resolution_percentage = percent
    path = path or (V4 + "/checks/frame_%04d.png" % frame)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r.filepath = path
    bpy.ops.render.render(write_still=True, scene=sc.name)
    r.resolution_percentage = old[2]
    setup_output(sc)
    return path


def save():
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, copy=True)
    return BLEND


def render_cmd():
    """The command line for a background render (doesn't tie up the open Blender)."""
    exe = bpy.app.binary_path
    return '"%s" -b "%s" -S "%s" -a' % (exe, BLEND, SCENE)
