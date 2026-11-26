# Characters. Hero = only coloured element; mother / wife / child = flat dark silhouettes.
# Local units: hero height ~ 101 u (feet to doppi top). skia y-down, facing +x, origin on the ground (or seat).
import math
import skia
from style import *

Hc = HERO

def _T(x, y, s, f):
    return lambda p: (x + p[0] * s * f, y + p[1] * s)

def ik2(a, b, l1, l2, bend=1):
    """2-bone IK: shoulder a -> target b; returns elbow, end"""
    dx, dy = b[0] - a[0], b[1] - a[1]; d = math.hypot(dx, dy)
    d2 = min(d, l1 + l2 - 1e-3)
    ang = math.atan2(dy, dx)
    c = clamp01((l1 * l1 + d2 * d2 - l2 * l2) / (2 * l1 * d2)) if d2 > 1e-6 else 1
    al = math.acos(max(-1, min(1, (l1 * l1 + d2 * d2 - l2 * l2) / (2 * l1 * max(d2, 1e-6)))))
    e = (a[0] + l1 * math.cos(ang - bend * al), a[1] + l1 * math.sin(ang - bend * al))
    end = (a[0] + d2 * math.cos(ang), a[1] + d2 * math.sin(ang))
    return e, end

# ------------------------------------------------------------------ head (pseudo 3D yaw)
def head(cv, c, yaw, tilt=0.0, pivot=None, scale=1.0, nod=0.0):
    """yaw deg: 0 = facing +x, 90 = facing viewer, 180 = facing -x, 270 = back to viewer"""
    th = yaw * D2R; cs, sn = math.cos(th), math.sin(th)
    cv.save()
    if pivot is not None and tilt:
        cv.translate(*pivot); cv.rotate(tilt * (1 if cs >= 0 else -1)); cv.translate(-pivot[0], -pivot[1])
    cx, cy = c
    skull = ell(cx, cy, 6.1, 6.8)
    jaw = ell(cx + 2.0 * cs, cy + 4.3, 4.6, 3.7)
    nose = ell(cx + 6.0 * cs, cy + 1.4, 1.45, 1.2)
    shape = skia.Op(skull, jaw, skia.kUnion_PathOp)
    shape = skia.Op(shape, nose, skia.kUnion_PathOp)
    fill(cv, shape, Hc["skin"])
    # soft shadow under the jaw line toward the neck
    cv.save(); cv.clipPath(shape, doAntiAlias=True)
    fill(cv, ell(cx - 2.2 * cs, cy + 8.9, 5.0, 2.4), Hc["skin_d"], 0.6)
    # hair at the nape
    zb = -sn; v = clamp01((zb + 0.85) / 0.55)
    if v > 0.01:
        xb = -cs
        hr = ell(cx + 4.0 * xb, cy + 1.4, 3.4 + 3.0 * max(0, zb), 5.6)
        fill(cv, hr, Hc["hair"], v)
    cv.restore()
    # eyes (one in profile)
    for ph in (40, -40):
        a = th + ph * D2R; z = math.sin(a)
        if z > 0.12:
            al = clamp01((z - 0.12) / 0.18)
            fill(cv, ell(cx + 4.9 * math.cos(a), cy - 0.4, 0.78 * max(0.45, z), 0.9), Hc["eye"], al)
    # doppi (Chust): black, white rim, white qalampir motifs
    dx = cx - 0.4 * cs
    rim = cy - 3.6; top = cy - 10.4
    dp = smooth([(dx - 6.9, rim + 0.4), (dx - 6.5, top + 2.0), (dx - 5.2, top + 0.2), (dx, top - 0.5),
                 (dx + 5.2, top + 0.2), (dx + 6.5, top + 2.0), (dx + 6.9, rim + 0.4), (dx, rim + 1.0)], k=0.25)
    fill(cv, dp, Hc["doppi"])
    cv.save(); cv.clipPath(dp, doAntiAlias=True)
    cv.drawRect(skia.Rect.MakeLTRB(dx - 8, rim - 0.9, dx + 8, rim + 2), paint(Hc["doppi_w"]))
    for k in range(4):
        a = th + (90 * k) * D2R; z = math.sin(a)
        if z <= 0.05: continue
        px = dx + 6.0 * math.cos(a); py = rim - 3.7
        w = 1.15 * z
        pts = [(0, 2.2), (1.2, 1.3), (1.25, -0.5), (0.55, -1.9), (-0.25, -2.6), (0.05, -1.1), (-0.95, 0.2), (-1.15, 1.5)]
        pep = smooth([(px + qx * w, py + qy) for qx, qy in pts], k=0.4)
        fill(cv, pep, Hc["doppi_w"], clamp01((z - 0.05) / 0.2))
        # little stitched dots around the motif
        for j, (ox, oy) in enumerate(((1.9, -2.2), (-1.9, -2.0), (2.0, 1.9), (-2.0, 2.0))):
            fill(cv, ell(px + ox * w, py + oy * 0.9, 0.32 * max(z, 0.3), 0.32), Hc["doppi_w"], 0.85 * clamp01((z - 0.05) / 0.2))
    cv.restore()
    cv.restore()

# ------------------------------------------------------------------ hands
def hand(cv, w, ang, kind, near=True, s=1.0):
    """w = wrist point, ang = direction (radians, atan2) of forearm"""
    col = Hc["skin"] if near else Hc["skin_d"]
    cv.save(); cv.translate(*w); cv.rotate(ang / D2R)
    if kind == "fist":
        fill(cv, ell(2.3, 0, 2.5, 2.2), col)
    elif kind == "palm":          # open palm, side view, palm up
        p = smooth([(-0.4, -1.2), (3.5, -1.5), (7.6, -1.3), (8.6, -0.6), (8.0, 0.4), (3.5, 0.9), (-0.4, 1.2)], k=0.35)
        fill(cv, p, col)
        fill(cv, ell(2.6, -1.9, 1.6, 0.9), col)  # thumb
    elif kind == "palm_top":      # open palm seen from above (close-up)
        fill(cv, rrect(-0.2, -2.9, 5.4, 2.9, 1.8), col)
        for j, oy in enumerate((-2.2, -0.75, 0.75, 2.2)):
            L = (3.4, 4.0, 3.8, 3.0)[j]
            fill(cv, limb((5.0, oy * 1.05), (5.0 + L, oy * 1.25), 0.78, 0.68), col)
        fill(cv, limb((1.4, -2.6), (4.0, -5.0), 0.95, 0.8), col)
        fill(cv, ell(3.0, 0.2, 2.0, 1.7), Hc["skin_d"], 0.55)
    elif kind == "grip":          # fingers curled around something (sleeve)
        fill(cv, ell(2.4, 0.2, 2.8, 2.0), col)
        fill(cv, ell(4.4, 1.2, 1.3, 1.1), col)
    else:                         # relaxed
        fill(cv, ell(3.1, 0.2, 3.3, 1.9), col)
        fill(cv, ell(1.8, -1.4, 1.5, 0.85), col)
    cv.restore()

# ------------------------------------------------------------------ hero
def _legs_walk(ph, amp):
    out = []
    for p in (ph, ph + math.pi):
        a = 27 * amp * math.sin(p)
        k = 58 * amp * max(0.0, math.cos(p)) ** 2 + 4
        out.append((a, k))
    return out   # near, far

def _arm(cv, S, sh, el, kind, near, tug=(0, 0), hold=None, cuff_col=None):
    sh_r, el_r = sh * D2R, el * D2R
    E = polar(S, 16.0, sh_r)
    Wr = polar(E, 14.2, sh_r + el_r)
    Wr = (Wr[0] + tug[0], Wr[1] + tug[1])
    c = Hc["ch"] if near else Hc["ch_d"]
    fill(cv, limb(S, E, 3.9, 3.4), c)
    fill(cv, limb(E, Wr, 3.4, 3.3), c)
    # gold cuff
    ux, uy = Wr[0] - E[0], Wr[1] - E[1]; L = math.hypot(ux, uy) or 1
    cb = (Wr[0] - ux / L * 1.9, Wr[1] - uy / L * 1.9)
    fill(cv, limb(cb, Wr, 3.35, 3.35), Hc["trim"] if near else mix(Hc["trim"], Hc["ch_d"], 0.35))
    ang = math.atan2(uy, ux)
    hw = (Wr[0] + ux / L * 0.6, Wr[1] + uy / L * 0.6)
    if kind: hand(cv, hw, ang, kind, near)
    return E, Wr, hw, ang

def hero(cv, x, y, s, pose=None, draw=True):
    """pose keys: mode stand|sit, facing, ph, walk, legs, armN, armF, handN, handF, head, tilt, lean, tugF, breath"""
    po = dict(mode="stand", facing=1, ph=0.0, walk=0.0, legs=None, armN=None, armF=None, handN="relax", handF="relax",
              head=0.0, tilt=0.0, lean=0.0, tugF=(0, 0), breath=0.0)
    if pose: po.update(pose)
    f = po["facing"]; T = _T(x, y, s, f)
    sit = po["mode"] == "sit"
    # ---------------- skeleton
    if sit:
        hip = (0.0, -3.0); dy = 45.0
        legs = None
    else:
        legs = po["legs"] or _legs_walk(po["ph"], po["walk"])
        hip0 = (0.0, -48.0)
        pts = []
        for a, k in legs:
            K = polar(hip0, 24.0, a * D2R); A = polar(K, 23.2, (a - k) * D2R); pts.append((K, A))
        low = max(pts[0][1][1], pts[1][1][1])
        bob = -1.6 - low
        hip = (0.0, -48.0 + bob); dy = bob
    lean = po["lean"] * D2R
    def U(p):      # upper body point (standing coords) -> lean about hip
        q = (p[0], p[1] + dy)
        return rot(q, lean, hip)
    br = 1 + 0.012 * po["breath"]
    S_n = U((0.8, -78.6 * br)); S_f = U((-1.4, -78.0 * br))
    walkamp = po["walk"]
    armN = po["armN"] or (-20 * walkamp * math.sin(po["ph"]) + (14 if sit else 3), 18 + (8 * walkamp * max(0, -math.sin(po["ph"]))) + (55 if sit else 0))
    armF = po["armF"] or (20 * walkamp * math.sin(po["ph"]) + (10 if sit else 0), 15 + (48 if sit else 0))
    neck_p = U((0.6, -86.0)); hc = U((1.4, -92.6))
    info = {}
    if draw:
        cv.save(); cv.translate(x, y); cv.scale(s * f, s)
        # ---------------- far arm
        _, _, hwF, _ = _arm(cv, S_f, armF[0] + po["lean"], armF[1], po["handF"], False, po["tugF"])
        # ---------------- legs
        if not sit:
            for idx, (a, k) in reversed(list(enumerate(legs))):
                near = idx == 0
                K = polar(hip, 24.0, a * D2R); A = polar(K, 23.2, (a - k) * D2R)
                tc = Hc["trou"] if near else Hc["trou_d"]; bc = Hc["boot"] if near else Hc["boot_d"]
                fill(cv, limb((hip[0] + (1 if near else -1), hip[1]), K, 4.2, 3.4), tc)
                fill(cv, limb(K, A, 3.4, 2.6), tc)
                # boot shaft + foot (toe forward, slight lift in swing)
                fa = -10 * max(0, math.cos(po["ph"] + (0 if near else math.pi))) * walkamp
                sh_top = polar(A, -8.0, (a - k) * D2R)
                fill(cv, limb(sh_top, A, 3.0, 2.7), bc)
                cv.save(); cv.translate(*A); cv.rotate(fa)
                fill(cv, smooth([(-2.8, -2.4), (2.4, -2.6), (3.6, -1.0), (7.6, -0.4), (8.7, 0.9), (8.1, 1.7), (-2.9, 1.7)], k=0.3), bc)
                cv.restore()
        else:
            fill(cv, smooth([(16, -3.6), (23.5, -3.8), (27.4, -1.8), (27.2, 0.7), (16, 0.7)], k=0.3), Hc["boot"])
        # ---------------- chapan
        if sit:
            hb = hf = None
            body = [U((-4.5, -85.0)), U((-8.6, -81.0)), U((-10.0, -72.0)), U((-9.3, -59.5)),
                    (-10.6, -6.0), (-10.4, 0.7), (19.0, 0.7), (24.0, -2.2), (23.4, -8.2), (15.0, -11.2),
                    U((8.8, -59.5)), U((9.7, -69.0)), U((6.6, -80.5)), U((3.2, -84.6))]
            front = [U((3.2, -84.6)), U((7.4, -78.0)), U((9.7, -69.0)), U((8.8, -59.5)), (15.0, -11.2), (23.4, -8.2), (24.0, -2.2)]
            hem = [(-10.4, 0.7), (19.0, 0.7), (24.0, -2.2)]
            belt_y = U((0, -58.6))[1]
        else:
            Ks = [polar(hip, 24.0, a * D2R) for a, k in legs]
            hf = min(19.0, max(10.5, max(K[0] for K in Ks) + 6.5)); hb = max(-19.0, min(-10.5, min(K[0] for K in Ks) - 6.0))
            hy = hip[1] + 26.0
            body = [U((-4.5, -85.0)), U((-8.6, -81.0)), U((-10.0, -72.0)), U((-9.3, -59.5)), (-10.8, hip[1]),
                    (hb, hy), ((hb + hf) / 2, hy + 0.8), (hf, hy), (10.8, hip[1]), U((8.8, -59.5)), U((9.7, -69.0)),
                    U((6.6, -80.5)), U((3.2, -84.6))]
            front = [U((3.2, -84.6)), U((7.4, -78.0)), U((9.7, -69.0)), U((8.8, -59.5)), (10.8, hip[1]), (hf, hy)]
            hem = [(hb, hy), ((hb + hf) / 2, hy + 0.8), (hf, hy)]
            belt_y = U((0, -58.6))[1]
        bp = smooth(body, k=0.42)
        fill(cv, bp, Hc["ch"])
        cv.save(); cv.clipPath(bp, doAntiAlias=True)
        # satin highlight band
        hl = poly([U((2.6, -82)), U((6.0, -82)), (6.0 if not sit else 12, (hip[1] + 26) if not sit else -9), (2.6 if not sit else 7, (hip[1] + 26) if not sit else -9)])
        fill(cv, hl, Hc["ch_l"])
        # ikat diamonds: vertical columns
        y_top = U((0, -88))[1]; y_bot = 2 if sit else hip[1] + 30
        for ci, cx0 in enumerate([-12.6 + 4.4 * i for i in range(9)]):
            colc = Hc["ikat1"] if ci % 2 == 0 else Hc["ikat2"]
            yy = y_top + (ci % 2) * 2.6
            while yy < y_bot:
                px = cx0 + (yy - y_top) * math.tan(lean) * -1
                d = poly([(px, yy - 1.75), (px + 0.95, yy), (px, yy + 1.75), (px - 0.95, yy)])
                fill(cv, d, colc, 0.9)
                yy += 5.2
            # thin ikat thread line between diamonds
            fill(cv, poly([(cx0 - 0.18, y_top), (cx0 + 0.18, y_top), (cx0 + 0.18, y_bot), (cx0 - 0.18, y_bot)]), colc, 0.35)
        # shadow on the back part
        bx = U((-5.6, -70))[0]
        fill(cv, poly([(bx - 30, y_top - 5), (U((-5.2, -84))[0], y_top - 5), (bx, -55 + dy), (bx - 1.0, y_bot + 5), (bx - 30, y_bot + 5)]), Hc["ch_d"], 0.72)
        # belt
        fill(cv, poly([(-30, belt_y - 2.3), (30, belt_y - 2.3), (30, belt_y + 2.3), (-30, belt_y + 2.3)]), Hc["belt"])
        fill(cv, poly([(-30, belt_y + 1.4), (30, belt_y + 1.4), (30, belt_y + 2.3), (-30, belt_y + 2.3)]), mix(Hc["belt"], (0, 0, 0), 0.2))
        # trims (half of the stroke is clipped away)
        cv.drawPath(smooth(front, closed=False, k=0.4), paint(Hc["trim"], stroke=3.4))
        cv.drawPath(smooth(hem, closed=False, k=0.4), paint(Hc["trim"], stroke=3.8))
        cv.restore()
        # belt knot tail
        kx = U((8.6, -57.5))
        fill(cv, smooth([(kx[0] - 0.8, kx[1] - 0.5), (kx[0] + 1.6, kx[1] - 0.2), (kx[0] + 2.4, kx[1] + 6.0), (kx[0] + 0.4, kx[1] + 6.6), (kx[0] - 0.2, kx[1] + 2.0)], k=0.3), Hc["belt"])
        # neck + collar
        n0 = U((-2.2, -90.0)); n1 = U((3.0, -84.0))
        fill(cv, limb(U((0.4, -89.5)), U((0.6, -84.0)), 2.7, 2.9), Hc["skin"])
        fill(cv, limb(U((-1.3, -89.0)), U((-1.2, -84.2)), 1.2, 1.4), Hc["skin_d"], 0.8)
        fill(cv, poly([U((-2.6, -85.8)), U((3.3, -85.3)), U((5.4, -81.8)), U((3.6, -80.6)), U((0.6, -83.2)), U((-2.2, -83.6))]), Hc["collar"])
        # ---------------- head
        head(cv, hc, po["head"], po["tilt"], pivot=neck_p)
        # ---------------- near arm
        _, _, hwN, angN = _arm(cv, S_n, armN[0] + po["lean"], armN[1], po["handN"], True)
        cv.restore()
        info["hand_n"] = T(hwN); info["hand_f"] = T(hwF); info["hand_n_ang"] = angN
    else:
        info["hand_n"] = T(polar(polar(S_n, 16, (armN[0] + po["lean"]) * D2R), 14.8, (armN[0] + po["lean"] + armN[1]) * D2R))
    info["shoulder_n"] = T(S_n); info["shoulder_f"] = T(S_f); info["head"] = T(hc); info["neck"] = T(neck_p)
    top = T((0, hc[1] - 11.5)); bot = T((0, 1.5))
    xs = [x - 22 * s, x + 30 * s]
    info["bbox"] = (min(xs), top[1], max(xs), bot[1])
    info["T"] = T
    return info

def hero_back_sit(cv, x, y, s, look=0.0, tilt=0.0):
    """hero seen from behind, sitting; look = small head yaw offset (deg)"""
    cv.save(); cv.translate(x, y); cv.scale(s, s)
    for sx in (-1, 1):
        fill(cv, limb((11.0 * sx, -33.0), (14.6 * sx, -17.0), 3.9, 3.4), Hc["ch_d"])
    body = smooth([(-6.0, -39.0), (-11.2, -36.0), (-12.8, -30.0), (-13.8, -14.0), (-16.2, 0.7), (16.2, 0.7),
                   (13.8, -14.0), (12.8, -30.0), (11.2, -36.0), (6.0, -39.0)], k=0.4)
    fill(cv, body, Hc["ch"])
    cv.save(); cv.clipPath(body, doAntiAlias=True)
    fill(cv, poly([(-2.5, -40), (2.5, -40), (3, 2), (-3, 2)]), Hc["ch_l"])
    for ci in range(9):
        cx0 = -15.4 + 3.85 * ci
        colc = Hc["ikat1"] if ci % 2 == 0 else Hc["ikat2"]
        yy = -40 + (ci % 2) * 2.6
        while yy < 2:
            fill(cv, poly([(cx0, yy - 1.75), (cx0 + 0.95, yy), (cx0, yy + 1.75), (cx0 - 0.95, yy)]), colc, 0.9); yy += 5.2
    for sx in (-1, 1):
        fill(cv, poly([(sx * 9.5, -42), (sx * 30, -42), (sx * 30, 3), (sx * 12.5, 3)]), Hc["ch_d"], 0.72)
    fill(cv, poly([(-20, -16.0), (20, -16.0), (20, -11.4), (-20, -11.4)]), Hc["belt"])
    cv.drawPath(poly([(-17, 0.7), (17, 0.7)], closed=False), paint(Hc["trim"], stroke=3.8))
    cv.restore()
    fill(cv, limb((0, -44.0), (0, -38.6), 2.8, 3.0), Hc["skin"])
    fill(cv, poly([(-4.6, -40.0), (4.6, -40.0), (5.2, -37.8), (-5.2, -37.8)]), Hc["collar"])
    head(cv, (0.0, -48.6), 270 + look, tilt, pivot=(0, -42))
    cv.restore()
    return dict(bbox=(x - 17 * s, y - 60 * s, x + 17 * s, y + s))

# ------------------------------------------------------------------ mother (silhouette + muted headscarf)
def _sil_head(cv, c, yaw_side, col, tilt=0.0, pivot=None):
    cv.save()
    if pivot is not None and tilt:
        cv.translate(*pivot); cv.rotate(tilt); cv.translate(-pivot[0], -pivot[1])
    cx, cy = c
    sh = skia.Op(ell(cx, cy, 5.8, 6.4), ell(cx + 1.9, cy + 4.0, 4.3, 3.4), skia.kUnion_PathOp)
    sh = skia.Op(sh, ell(cx + 5.7, cy + 1.3, 1.35, 1.1), skia.kUnion_PathOp)
    fill(cv, sh, col)
    cv.restore()

def mother_arm(cv, x, y, s, facing, target, col):
    """mother's near arm only (drawn after the hero so the hand lies on top)"""
    cv.save(); cv.translate(x, y); cv.scale(s * facing, s)
    S = (0.2, -31.5)
    tl = ((target[0] - x) / (s * facing), (target[1] - y) / s)
    E, Wp = ik2(S, tl, 15.5, 14.5, bend=-1)
    fill(cv, limb(S, E, 3.6, 3.1), col); fill(cv, limb(E, Wp, 3.1, 2.5), col)
    ang = math.atan2(Wp[1] - E[1], Wp[0] - E[0])
    cv.save(); cv.translate(*Wp); cv.rotate(ang / D2R)
    fill(cv, ell(2.4, 0.8, 3.2, 1.7), col)
    for oy in (0.2, 1.4, 2.5): fill(cv, limb((4.4, oy), (6.6, oy + 2.0), 0.75, 0.65), col)
    cv.restore(); cv.restore()

def mother_sit(cv, x, y, s, col, facing=1, tilt=0.0, arm_target=None, arm=None, breath=0.0, scarf=SCARF, scarf_a=1.0, draw_arm=True):
    """sitting side view; arm_target in screen coords (near hand reaches there)"""
    T = _T(x, y, s, facing)
    cv.save(); cv.translate(x, y); cv.scale(s * facing, s)
    body = smooth([(-3.5, -36.5), (-8.8, -33.0), (-11.2, -24.0), (-12.6, -8.0), (-13.0, 0.7), (21.0, 0.7), (24.6, -2.2),
                   (23.0, -8.4), (14.0, -11.0), (8.4, -15.0), (9.0, -25.0), (7.4, -32.0), (3.4, -36.0)], k=0.42)
    fill(cv, body, col)
    c = (1.2, -43.6); piv = (0.6, -37.5)
    fill(cv, limb((0.4, -40.0), (0.8, -35.0), 2.6, 2.8), col)
    _sil_head(cv, c, 1, col, tilt, piv)
    # headscarf: over the head, framing the face, draping down the back
    cv.save()
    cv.translate(*piv); cv.rotate(tilt * 0.8); cv.translate(-piv[0], -piv[1])
    sc = smooth([(c[0] + 5.4, c[1] - 3.8), (c[0] + 2.8, c[1] - 7.9), (c[0] - 2.6, c[1] - 8.2), (c[0] - 6.9, c[1] - 4.4),
                 (c[0] - 8.4, c[1] + 2.8), (c[0] - 9.2, c[1] + 8.5), (-12.0, -27.0), (-12.4, -20.0), (-8.4, -22.5),
                 (-4.6, -31.0), (c[0] - 0.6, c[1] + 7.4), (c[0] + 1.3, c[1] + 3.3), (c[0] + 3.0, c[1] - 0.8)], k=0.4)
    fill(cv, sc, scarf, scarf_a)
    cv.restore()
    info = {}
    S = (0.2, -31.5)
    if not draw_arm:
        pass
    elif arm_target is not None:
        tl = ((arm_target[0] - x) / (s * facing), (arm_target[1] - y) / s)
        E, Wp = ik2(S, tl, 15.5, 14.5, bend=-1)
        fill(cv, limb(S, E, 3.5, 3.0), col); fill(cv, limb(E, Wp, 3.0, 2.5), col)
        ang = math.atan2(Wp[1] - E[1], Wp[0] - E[0])
        cv.save(); cv.translate(*Wp); cv.rotate(ang / D2R)
        fill(cv, ell(2.4, 0.6, 3.1, 1.6), col); fill(cv, ell(4.6, 1.6, 1.8, 1.1), col)
        cv.restore()
    else:
        a0, a1 = arm or (22, 70)
        E = polar(S, 15.5, a0 * D2R); Wp = polar(E, 14.5, (a0 + a1) * D2R)
        fill(cv, limb(S, E, 3.5, 3.0), col); fill(cv, limb(E, Wp, 3.0, 2.5), col)
        fill(cv, ell(Wp[0] + 1.8, Wp[1] + 0.6, 3.0, 1.7), col)
    cv.restore()
    info["bbox"] = (x - 14 * s * (1 if facing > 0 else -1), y - 53 * s, x + 25 * s * facing, y + s)
    info["head"] = T(c)
    return info

def mother_back_sit(cv, x, y, s, col, scarf=SCARF):
    cv.save(); cv.translate(x, y); cv.scale(s, s)
    fill(cv, smooth([(-5.5, -37.0), (-10.5, -34.0), (-12.5, -26.0), (-14.5, -12.0), (-17.0, 0.7), (17.0, 0.7),
                     (14.5, -12.0), (12.5, -26.0), (10.5, -34.0), (5.5, -37.0)], k=0.4), col)
    fill(cv, ell(0, -45.0, 6.2, 6.8), col)
    fill(cv, smooth([(0, -53.3), (6.6, -50.0), (8.4, -42.0), (10.5, -32.0), (12.0, -22.0), (0, -18.5), (-12.0, -22.0),
                     (-10.5, -32.0), (-8.4, -42.0), (-6.6, -50.0)], k=0.4), scarf)
    cv.restore()

def mother_arm_in(cv, sx, sy, target, s, col, scarf=SCARF, show_scarf=0.0):
    """arm entering from the left frame edge: shoulder at (sx,sy) (off-screen), hand grips the sleeve at target"""
    E, Wp = ik2((sx, sy), target, 16.0 * s, 14.5 * s, bend=1)
    if show_scarf > 0:
        fill(cv, smooth([(sx - 40 * s, sy - 46 * s), (sx - 6 * s, sy - 40 * s), (sx + 4 * s, sy - 10 * s), (sx + 2 * s, sy + 30 * s),
                         (sx - 40 * s, sy + 40 * s)], k=0.4), col)
        fill(cv, smooth([(sx - 40 * s, sy - 60 * s), (sx - 9 * s, sy - 52 * s), (sx - 2 * s, sy - 30 * s), (sx - 8 * s, sy - 6 * s),
                         (sx - 40 * s, sy)], k=0.4), scarf, show_scarf)
    fill(cv, limb((sx, sy), E, 5.4 * s, 4.4 * s), col)       # wide dress sleeve
    fill(cv, limb(E, Wp, 4.2 * s, 3.0 * s), col)
    ang = math.atan2(Wp[1] - E[1], Wp[0] - E[0])
    cv.save(); cv.translate(*Wp); cv.rotate(ang / D2R); cv.scale(s, s)
    fill(cv, ell(2.0, 0.2, 3.3, 2.7), col)                     # back of the hand
    for k, oy in enumerate((-1.6, -0.2, 1.2, 2.5)):            # fingers wrapped around the sleeve
        fill(cv, limb((3.6, oy), (6.2, oy + 1.9), 0.95, 0.8), col)
    fill(cv, limb((1.0, -2.0), (3.8, -3.6), 1.0, 0.85), col)   # thumb on top
    cv.restore()
    return E, Wp

# ------------------------------------------------------------------ wife (silhouette, no colour)
def wife(cv, x, y, s, col, facing=1, ph=0.0, walk=0.0, tilt=0.0, arm=(10, 20), arm_target=None, look=0.0):
    T = _T(x, y, s, facing)
    cv.save(); cv.translate(x, y); cv.scale(s * facing, s)
    # feet peeking under the dress
    for k, p in enumerate((ph, ph + math.pi)):
        fx = 9 * walk * math.sin(p)
        lift = 2.5 * walk * max(0, math.cos(p))
        fill(cv, smooth([(fx - 3, -2.5 - lift), (fx + 3.5, -2.6 - lift), (fx + 6.2, -0.6 - lift), (fx + 5.5, 0.8 - lift), (fx - 3, 0.8 - lift)], k=0.3), col)
    sway = 3.0 * walk * math.sin(ph)
    bob = -1.2 * walk * abs(math.cos(ph))
    body = smooth([(-3.8, -82 + bob), (-7.6, -78 + bob), (-8.6, -68 + bob), (-7.0, -57 + bob), (-9.0, -46 + bob),
                   (-13.5 - sway * 0.5, -3), (13.5 + sway, -3), (9.4, -46 + bob), (7.6, -57 + bob), (9.0, -66 + bob),
                   (6.4, -77 + bob), (2.8, -82 + bob)], k=0.42)
    fill(cv, body, col)
    fill(cv, limb((0.2, -88 + bob), (0.4, -81 + bob), 2.4, 2.7), col)
    c = (1.0, -92.0 + bob); piv = (0.4, -86 + bob)
    cv.save(); cv.translate(*piv); cv.rotate(tilt); cv.translate(-piv[0], -piv[1])
    sh = skia.Op(ell(c[0], c[1], 5.7, 6.4), ell(c[0] + 1.9, c[1] + 4.0, 4.2, 3.4), skia.kUnion_PathOp)
    sh = skia.Op(sh, ell(c[0] + 5.6, c[1] + 1.3, 1.3, 1.05), skia.kUnion_PathOp)
    fill(cv, sh, col)
    fill(cv, ell(c[0] - 6.6, c[1] - 2.0, 3.6, 3.4), col)           # hair bun
    fill(cv, smooth([(c[0] - 6, c[1] - 1), (c[0] - 4.5, c[1] + 6), (c[0] - 8.5, c[1] + 16), (c[0] - 9.5, c[1] + 6)], k=0.4), col)
    cv.restore()
    S = (0.6, -77.5 + bob)
    if arm_target is not None:
        tl = ((arm_target[0] - x) / (s * facing), (arm_target[1] - y) / s)
        E, Wp = ik2(S, tl, 15.0, 14.0, bend=-1)
    else:
        E = polar(S, 15.0, arm[0] * D2R); Wp = polar(E, 14.0, (arm[0] + arm[1]) * D2R)
    fill(cv, limb(S, E, 2.9, 2.4), col); fill(cv, limb(E, Wp, 2.4, 2.0), col)
    ang = math.atan2(Wp[1] - E[1], Wp[0] - E[0])
    cv.save(); cv.translate(*Wp); cv.rotate(ang / D2R); fill(cv, ell(2.8, 0.2, 3.0, 1.5), col); cv.restore()
    cv.restore()
    return dict(hand=T(Wp), head=T(c), bbox=(x - 14 * s, y - 100 * s, x + 14 * s, y))

# ------------------------------------------------------------------ child (silhouette)
def child_side(cv, x, y, s, col, facing=1):
    cv.save(); cv.translate(x, y); cv.scale(s * facing, s)
    for fx in (-2.5, 2.5):
        fill(cv, limb((fx, -26), (fx, -2), 3.0, 2.6), col)
        fill(cv, smooth([(fx - 2.5, -3.5), (fx + 3.5, -3.5), (fx + 5.5, -0.6), (fx + 4.8, 0.8), (fx - 2.8, 0.8)], k=0.3), col)
    fill(cv, smooth([(-6.5, -50), (-8.5, -40), (-8.8, -24), (9.0, -24), (8.4, -40), (5.6, -50), (0, -52)], k=0.4), col)
    fill(cv, limb((0, -48), (1.5, -28), 2.6, 2.3), col)
    fill(cv, limb((0, -56), (0.4, -50), 2.6, 2.8), col)
    sh = skia.Op(ell(0.8, -63.5, 7.6, 8.0), ell(5.6, -60.4, 1.4, 1.2), skia.kUnion_PathOp)
    fill(cv, sh, col)
    cv.restore()

def child_front(cv, x, y, s, col, turn=1.0, eye_col=None, eye_a=0.0):
    """child head + shoulders; turn: 0 = side profile, 1 = facing camera"""
    cv.save(); cv.translate(x, y); cv.scale(s, s)
    w = lerp(0.8, 1.0, turn)
    fill(cv, smooth([(-15.5 * w, 2), (-15 * w, -12), (-12 * w, -20.5), (-6, -24.5), (6, -24.5), (12 * w, -20.5), (15 * w, -12), (15.5 * w, 2)], k=0.45), col)
    fill(cv, limb((0, -33), (0, -23), 3.5, 3.9), col)
    off = 2.6 * (1 - turn)
    head_ = ell(off * 0.5, -42.5, lerp(8.4, 9.0, turn), 9.8)
    head_ = skia.Op(head_, ell(off + 8.2 * (1 - turn), -41.0, 1.6, 1.3), skia.kUnion_PathOp)     # nose in profile
    for sx in (-1, 1):                                                                           # ears
        ex = sx * 9.0 * turn + off * 0.5 - (1 - turn) * 2.0
        head_ = skia.Op(head_, ell(ex, -42.0, 2.1, 2.8), skia.kUnion_PathOp)
    fill(cv, head_, col)
    fill(cv, smooth([(-9.0 + off * 0.5, -45), (-8.2, -51), (-3.5, -54.0), (2, -54.4), (6.8, -52.2), (9.0 + off * 0.5, -46.5), (4.5, -50.0), (-1.5, -50.6)], k=0.45), col)
    if eye_col is not None and eye_a > 0:
        for ex in (-3.3, 3.3):
            fill(cv, ell(ex * turn + off * 0.6, -42.8, 0.55, 0.62), eye_col, eye_a * turn)
    cv.restore()

def person_top(cv, x, y, s, col, heading=0.0, a=1.0, child=False):
    """top-down silhouette (head + shoulders + feet hint), heading in degrees"""
    cv.save(); cv.translate(x, y); cv.rotate(heading); cv.scale(s, s)
    sw = 9.5 if not child else 7.0
    fill(cv, ell(0, 0, sw, sw * 0.52), col, a)
    fill(cv, ell(0, 0, sw * 0.5, sw * 0.5), mix(col, (0, 0, 0), 0.25), a)
    cv.restore()
