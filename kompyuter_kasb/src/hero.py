# The programmer hero, flat silhouette style.
# All geometry is in "reference units": the pixel grid of the attached 1080x1920 reference image.
# turn=0 reproduces the reference side view exactly (polygons traced from it);
# turn=1 is the matching front view; values between give the 3/4 view by morphing.
import math
import skia
from common import *

C = dict(body="#3F7B61", shade="#2F634D", light="#4C8A6E", ikat_l="#6FA586", ikat_g="#C7A548",
         trim="#BE8642", sash="#B4473B", cream="#E8E1D3", hat="#1D2427", skin="#EBC8A2",
         skin_sh="#D8B089", hair="#2E231D", eye="#191614", boot="#33241E", boot2="#291D18",
         laptop="#3A474C", laptop_d="#2B3539", glow="#E7A05C")

ROOT = (520.0, 1699.0)          # ground point between the feet
HEIGHT = 1451.0                 # hat top (248) .. sole (1699)

# ---------------------------------------------------------------- body (coat)
COAT_P = [(463, 500), (540, 499), (587, 517), (614, 537), (646, 648), (650, 859), (652, 916), (658, 1101),
          (685, 1419), (565, 1436), (436, 1436), (354, 1419), (369, 1293), (385, 1090), (392, 947),
          (394, 917), (395, 859), (392, 723), (396, 598), (417, 523)]
_WF = [(495, 40), (505, 60), (517, 112), (523, 117), (537, 128), (600, 131), (648, 132), (723, 131), (859, 130),
       (916, 131), (947, 133), (1090, 139), (1101, 140), (1293, 152), (1419, 164), (1436, 164)]


def wf(y):
    for (y0, w0), (y1, w1) in zip(_WF, _WF[1:]):
        if y <= y1:
            return w0 + (w1 - w0) * (y - y0) / (y1 - y0)
    return _WF[-1][1]


def _front_of(pts_left_right):
    out = []
    for (x, y), side in pts_left_right:
        out.append((520 + side * wf(y), y))
    return out


COAT_F = [(480, 500), (560, 500)] + _front_of([((0, y), 1) for _, y in COAT_P[2:9]]) + [(580, 1436), (460, 1436)] + \
    _front_of([((0, y), -1) for _, y in COAT_P[11:]])
BACK_P = [(416, 524), (467, 524), (447, 600), (448, 860), (445, 917), (437, 1076), (428, 1197), (419, 1307), (405, 1426),
          (354, 1419), (369, 1293), (385, 1090), (392, 947), (394, 917), (395, 859), (392, 723), (396, 598)]
BACK_F = [(520 - wf(524), 524)] + [(520 - wf(y) + (30 if y > 530 else 22), y) for _, y in BACK_P[1:9]] + \
    [(520 - wf(y), y) for _, y in BACK_P[9:]]
# front edge trim band: edge "b" (outer in side view) and "a" (inner)
T1B_P = [(587, 519), (614, 537), (646, 648), (650, 859), (652, 916), (658, 1101), (685, 1419)]
T1A_P = [(584, 532), (603, 546), (633, 650), (635, 859), (637, 917), (643, 1095), (671, 1420)]
T1B_F = [(559, 503), (552, 537), (528, 648), (527, 859), (527, 916), (527, 1101), (527, 1426)]
T1A_F = [(546, 503), (539, 546), (515, 650), (514, 859), (514, 917), (514, 1095), (514, 1428)]
T2B_F = [(481, 503), (488, 537), (512, 648)]
T2A_F = [(494, 503), (501, 546), (525, 650)]
COLLAR_P = [(536, 489), (558, 489), (587, 508), (589, 519), (584, 532), (579, 550), (577, 535), (571, 521), (558, 507), (539, 499)]
COLLAR_F = [(488, 492), (552, 492), (560, 500), (547, 505), (533, 580), (520, 640), (507, 580), (493, 505), (480, 500), (484, 494)]
NECK_P = [(508, 466), (538, 466), (538, 503), (508, 503)]
NECK_F = [(505, 466), (535, 466), (535, 503), (505, 503)]
SASH_P = [(383, 860), (656, 860), (656, 915), (383, 915)]
SASH_F = [(384, 860), (656, 860), (656, 915), (384, 915)]
SASHEND_P = [(382, 910), (403, 915), (371, 1003), (352, 992)]
SASHEND_F = [(452, 912), (472, 914), (462, 1001), (440, 996)]
HEM_P = [(348, 1428), (438, 1444), (565, 1443.5), (671, 1429), (685, 1428)]
HEM_F = [(356, 1428), (452, 1444), (588, 1444), (675, 1430), (684, 1428)]
HEM_W = 15.5

# ---------------------------------------------------------------- legs
NLEG_P = [(494, 1290), (568, 1290), (567, 1643), (585, 1661), (616, 1677), (619, 1699), (491, 1699), (495, 1640)]
NLEG_F = [(447, 1290), (517, 1290), (518, 1643), (522, 1665), (526, 1684), (526, 1699), (438, 1699), (443, 1640)]
FLEG_P = [(x - 23, y) for x, y in NLEG_P]
FLEG_F = [(x + 76, y) for x, y in NLEG_F]

# ---------------------------------------------------------------- head
HEAD_C_P = (548.0, 420.0)
HEAD_P = [(492, 356), (596, 358), (606, 381), (608, 398), (610, 420), (603, 443), (588, 468), (569, 483), (557, 488),
          (535, 490), (511, 479), (491, 457), (488, 420), (488, 390)]
NOSE_P = [(608, 398), (625, 428), (604, 447)]
HAIR_P = [(448, 379), (461, 356), (502, 355), (507, 386), (498, 441), (475, 467), (450, 436)]
HAT_P = [(455, 261), (529, 248), (599, 260), (615, 294), (618, 342), (620, 355), (436, 355), (437, 342), (440, 295)]
RIM_P = [(436, 343), (558, 342), (621, 343), (625, 350), (621, 354), (543, 351), (435, 353), (432, 347)]
HAT_CX = 528.0
PEPPERS = [(468, 306), (516, 298), (564, 298)]          # pepper-pod motif centres (side view)
HAND_P = [(552, 1105), (538, 1111), (529, 1123), (526, 1136), (529, 1148), (538, 1160), (552, 1166), (567, 1166),
          (581, 1160), (590, 1148), (593, 1134), (589, 1121), (581, 1111), (567, 1105)]
HAND_C = (559.5, 1135.5)


def _head_front():
    out = []
    cx, cy = HEAD_C_P
    for x, y in HEAD_P:
        a = math.atan2(y - cy, x - cx)
        out.append((520 + 61 * math.cos(a), 421 + 69 * math.sin(a)))
    return out


HEAD_F = _head_front()

# ---------------------------------------------------------------- arm
SH_P = (528.0, 548.0)            # shoulder pivot (centre of the round sleeve top), side view
L_UP = 330.9
R_TOP, HW_EL, HW_CUFF = 49.0, 45.5, 44.0
A1_REST, A2_REST = -4.24, 12.21  # degrees from "straight down", positive = towards facing direction
SLEEVE_IKAT = [("up", 0.0, 166.4, "l"), ("fo", 0.0, 70.5, "g"), ("fo", 0.0, 144.3, "l")]


class Arm:
    def __init__(self, a1=A1_REST, a2=A2_REST, hand="fist", open=1.0, k=1.0, k1=1.0):
        self.a1, self.a2, self.hand, self.open, self.k, self.k1 = a1, a2, hand, open, k, k1

    def lerp(self, o, t):
        h = self.hand if t < 0.5 else o.hand
        return Arm(lerp(self.a1, o.a1, t), lerp(self.a2, o.a2, t), h, lerp(self.open, o.open, t), lerp(self.k, o.k, t),
                   lerp(self.k1, o.k1, t))


REST = Arm()
HOLD = Arm(-12, 88, "hold")


class Pose:
    def __init__(self, turn=0.0, head_turn=None, walk=0.0, walk_amp=0.0, arm=None, farm=None, laptop=False,
                 tilt=0.0, far_front=False, sway=0.0, bob=True):
        self.turn = turn
        self.head_turn = turn if head_turn is None else head_turn
        self.walk, self.walk_amp = walk, walk_amp
        self.arm = arm or REST
        self.farm = farm
        self.laptop = laptop
        self.tilt = tilt
        self.far_front = far_front
        self.sway = sway
        self.bob = bob


def _dirs(a_deg):
    a = math.radians(a_deg)
    d = (math.sin(a), math.cos(a))
    n = (math.cos(a), -math.sin(a))
    return d, n


def _pt(o, d, n, v, u):
    return (o[0] + d[0] * v + n[0] * u, o[1] + d[1] * v + n[1] * u)


def _diamond(cx, cy, hw, hh, ang=0.0):
    pts = [(0, -hh), (hw, 0), (0, hh), (-hw, 0)]
    if ang:
        pts = [rot(x, y, ang) for x, y in pts]
    return poly([(cx + x, cy + y) for x, y in pts])


def arm_paths(P, arm):
    """sleeve (union path), elbow point, forearm frame"""
    d1, n1 = _dirs(arm.a1)
    L1 = L_UP * arm.k1
    E = (P[0] + d1[0] * L1, P[1] + d1[1] * L1)
    d2, n2 = _dirs(arm.a2)
    k = arm.k
    up = poly([_pt(P, d1, n1, 0, -R_TOP), _pt(P, d1, n1, 0, R_TOP), _pt(P, d1, n1, L1, HW_EL), _pt(P, d1, n1, L1, -HW_EL)])
    fo = poly([_pt(E, d2, n2, 0, -HW_EL), _pt(E, d2, n2, 0, HW_EL), _pt(E, d2, n2, 215 * k, HW_CUFF), _pt(E, d2, n2, 215 * k, -HW_CUFF)])
    sleeve = union(circle(P[0], P[1], R_TOP), up, circle(E[0], E[1], HW_EL), fo)
    return sleeve, E, d1, n1, d2, n2


def draw_hand(c, E, d2, n2, arm, skin, flip_thumb=1.0):
    k = arm.k
    vh = 263.4 * k
    a2 = math.radians(arm.a2)
    if arm.hand in ("fist", "hold"):
        ang = -(a2 - math.radians(A2_REST))
        hc = _pt(E, d2, n2, vh, 0.4)
        pts = [rot(x - HAND_C[0], y - HAND_C[1], ang) for x, y in HAND_P]
        c.drawPath(poly([(hc[0] + x, hc[1] + y) for x, y in pts]), paint(skin))
        return
    o = clamp01(arm.open)
    # open palm / pointing hand, drawn in the forearm frame (v along the forearm, u across)
    pc = _pt(E, d2, n2, vh, 0)
    ang = math.atan2(d2[1], d2[0]) - math.pi / 2
    c.save()
    c.translate(pc[0], pc[1])
    c.rotate(math.degrees(ang))
    p = paint(skin)
    if arm.hand == "palm":
        c.drawPath(rrect(-31, -30, 31, 30, 22), p)
        L = 22 + 34 * o
        for i, u in enumerate((-22.5, -7.5, 7.5, 22.5)):
            spread = (i - 1.5) * 0.07 * o
            c.save(); c.rotate(math.degrees(spread))
            ln = L * (0.86 if i in (0, 3) else 1.0)
            c.drawPath(rrect(u - 7.2, 10, u + 7.2, 22 + ln, 7.2), p)
            c.restore()
        c.save(); c.translate(26 * flip_thumb, 0); c.rotate(-(35 + 25 * o) * flip_thumb)
        c.drawPath(rrect(-8, 0, 8, 26 + 20 * o, 8), p)
        c.restore()
    elif arm.hand == "pointat":   # fist with the index finger aimed out of the screen, at the viewer
        c.rotate(-math.degrees(ang))                                # draw upright, independent of the forearm
        c.scale(1.4 + 0.4 * o, 1.4 + 0.4 * o)                       # "open" doubles as the poke towards the camera
        c.drawPath(oval(0, 0, 31, 29), p)
        for fx in (-17, -3, 11):                                    # curled finger knuckles
            c.drawPath(oval(fx, 17, 8.0, 9.0), paint(C["skin_sh"]))
            c.drawPath(oval(fx, 15.5, 7.6, 8.0), p)
        c.drawPath(oval(-25, -6, 9, 14), p)                          # thumb
        # index finger aimed straight at the camera: only its rounded tip shows, in front of the fist
        c.drawPath(oval(7, -3, 15.5, 15), paint(C["skin_sh"]))
        c.drawPath(oval(5, -6, 14, 13.5), p)
    else:  # point
        c.drawPath(oval(0, 0, 33, 30), p)
        c.drawPath(rrect(-4 - 8, 12, -4 + 8, 30 + 50 * o, 8), p)
    c.restore()


def draw_arm(c, P, arm, sleeve_col, ikat=True, cuff=True):
    sleeve, E, d1, n1, d2, n2 = arm_paths(P, arm)
    c.drawPath(sleeve, paint(sleeve_col))
    if ikat:
        c.save(); c.clipPath(sleeve, doAntiAlias=True)
        for part, u, v, kind in SLEEVE_IKAT:
            if part == "up":
                q = _pt(P, d1, n1, v * arm.k1, u); ang = -math.radians(arm.a1)
            else:
                q = _pt(E, d2, n2, v * arm.k, u); ang = -math.radians(arm.a2)
            c.drawPath(_diamond(q[0], q[1], 11.5, 18, ang), paint(C["ikat_l"] if kind == "l" else C["ikat_g"]))
        c.restore()
    if cuff:
        k = arm.k
        a = math.degrees(math.atan2(d2[1], d2[0])) - 90
        cc = _pt(E, d2, n2, 218 * k, 0)
        c.save(); c.translate(cc[0], cc[1]); c.rotate(a)
        c.drawPath(rrect(-45, 163 * k - 218 * k, 45, 273 * k - 218 * k + (1 - k) * 40, 45), paint(C["trim"]))
        c.restore()
    return E, d2, n2


def _boot(c, pts, colr, pivot, ang, lift):
    """leg swings about the hip; the foot stays (almost) flat on the ground"""
    if ang or lift:
        out = []
        ank = (sum(x for x, y in pts) / len(pts), 1640.0)
        ax, ay = rot(ank[0] - pivot[0], ank[1] - pivot[1], ang)
        ank2 = (pivot[0] + ax, pivot[1] + ay)
        for x, y in pts:
            if y >= 1639:            # foot: carried by the ankle, mostly un-rotated
                fx, fy = rot(x - ank[0], y - ank[1], ang * 0.15)
                out.append((ank2[0] + fx, ank2[1] + fy - lift))
            else:
                rx, ry = rot(x - pivot[0], y - pivot[1], ang)
                out.append((pivot[0] + rx, pivot[1] + ry - lift))
        pts = out
    c.drawPath(poly(pts), paint(colr))


def draw_hero(c, x, y, scale, facing=1, pose=None):
    """draw the hero with feet centre at screen (x, y); scale = screen px per reference unit"""
    pose = pose or Pose()
    t = clamp01(pose.turn)
    c.save()
    c.translate(x, y)
    c.scale(scale * facing, scale)
    # walk cycle
    ph, A = pose.walk, pose.walk_amp
    leg_a = math.radians(13) * A * math.sin(ph)
    bob = (410 * (1 - math.cos(leg_a))) if pose.bob else 0.0
    c.translate(-ROOT[0], -ROOT[1] + bob * 0.6)
    sway = pose.sway + 7 * A * math.sin(2 * ph + 0.6)

    def hem_sway(pts):
        return [(px + sway * clamp01((py - 1250) / 190.0), py) for px, py in pts]

    # ------------------------------------------------------------- far arm (behind body)
    Pf = (lerp(SH_P[0] - 6, 660, t), SH_P[1])
    if pose.farm is not None and not pose.far_front:
        draw_arm(c, Pf, pose.farm, mix(C["body"], C["light"], t), ikat=t > 0.3)
        E, d2, n2 = arm_paths(Pf, pose.farm)[1], *_dirs(pose.farm.a2)
        draw_hand(c, E, d2, n2, pose.farm, C["skin"], flip_thumb=1.0)
    # ------------------------------------------------------------- legs
    lift_n = 22 * A * max(0.0, math.cos(ph)) if A else 0.0
    lift_f = 22 * A * max(0.0, -math.cos(ph)) if A else 0.0
    _boot(c, lerp_pts(FLEG_P, FLEG_F, t), mix(C["boot2"], "#30221C", t), (lerp(508, 558, t), 1290), -leg_a, lift_f + bob * 0.6)
    _boot(c, lerp_pts(NLEG_P, NLEG_F, t), C["boot"], (lerp(531, 482, t), 1290), leg_a, lift_n + bob * 0.6)
    # ------------------------------------------------------------- neck + coat
    c.drawPath(poly(lerp_pts(NECK_P, NECK_F, t)), paint(C["skin_sh"]))
    coat_pts = hem_sway(lerp_pts(COAT_P, COAT_F, t))
    coat = poly(coat_pts)
    c.drawPath(coat, paint(C["body"]))
    c.drawPath(poly(hem_sway(lerp_pts(BACK_P, BACK_F, t))), paint(C["shade"]))
    # ikat diamonds: screen-space grid scrolled with the turn, kept inside the panels
    t1a = hem_sway(lerp_pts(T1A_P, T1A_F, t)); t1b = hem_sway(lerp_pts(T1B_P, T1B_F, t))
    left = coat_pts[11:] + coat_pts[:1]          # left silhouette bottom->top
    right = coat_pts[1:9]

    def x_at(chain, yy):
        ch = sorted(chain, key=lambda p: p[1])
        if yy <= ch[0][1]: return ch[0][0]
        for (xa, ya), (xb, yb) in zip(ch, ch[1:]):
            if ya <= yy <= yb:
                return xa + (xb - xa) * (yy - ya) / max(1e-6, yb - ya)
        return ch[-1][0]

    ox = -192.0 * t
    c.save(); c.clipPath(coat, doAntiAlias=True)
    pg, pl = paint(C["ikat_g"]), paint(C["ikat_l"])
    for col_i in range(-6, 12):
        gx = 436 + 46 * col_i + ox
        gold = (col_i % 2 == 0)
        y0 = 548 if gold else 580
        for row in range(-1, 15):
            gy = y0 + 64 * row
            top, bot = gy - 16, gy + 16
            if top < 528 or bot > 1436 or (bot > 858 and top < 917): continue   # none under / touching the sash
            l = max(x_at(left, top), x_at(left, bot)) + 11.4
            ra = min(x_at(t1a, top), x_at(t1a, bot)) - 3.4
            rb = max(x_at(t1b, top), x_at(t1b, bot)) + 2.5
            rr = min(x_at(right, top), x_at(right, bot)) - 12
            ok = (gx - 10 >= l and gx + 10 <= ra) or (gx - 10 >= rb and gx + 10 <= rr)
            if ok:
                c.drawPath(_diamond(gx + sway * clamp01((gy - 1250) / 190.0), gy, 10, 16), pg if gold else pl)
    c.restore()
    # trims, collar, sash
    c.drawPath(poly(lerp_pts(COLLAR_P, COLLAR_F, t)), paint(C["cream"]))
    if t > 0.02:
        b2 = lerp_pts(T1B_P[:3], T2B_F, t); a2 = lerp_pts(T1A_P[:3], T2A_F, t)
        c.drawPath(poly(b2 + a2[::-1]), paint(C["trim"]))
    c.drawPath(poly(t1b + t1a[::-1]), paint(C["trim"]))
    hem = smooth_path(hem_sway(lerp_pts(HEM_P, HEM_F, t)), close=False, tension=0.0)
    c.drawPath(hem, paint(C["trim"], style="stroke", width=HEM_W, cap="round", join="round"))
    c.drawPath(poly(lerp_pts(SASH_P, SASH_F, t)), paint(C["sash"]))
    se = lerp_pts(SASHEND_P, SASHEND_F, t)
    if A:
        sw = 0.06 * A * math.sin(ph * 2 + 1.0)
        piv = ((se[0][0] + se[1][0]) / 2, (se[0][1] + se[1][1]) / 2)
        se = se[:2] + [(piv[0] + rot(px - piv[0], py - piv[1], sw)[0], piv[1] + rot(px - piv[0], py - piv[1], sw)[1]) for px, py in se[2:]]
    c.drawPath(poly(se), paint(C["sash"]))
    # ------------------------------------------------------------- far arm in front (front-view poses)
    if pose.farm is not None and pose.far_front:
        E, d2, n2 = draw_arm(c, Pf, pose.farm, C["light"])
        draw_hand(c, E, d2, n2, pose.farm, C["skin"], flip_thumb=1.0)
    # ------------------------------------------------------------- laptop (under the near arm)
    Pn = (lerp(SH_P[0], 380, t), SH_P[1])
    if pose.laptop:
        lw = 280 * (1 - 0.5 * t); cx = lerp(578, 420, t)
        c.save(); c.translate(cx, 734); c.rotate(-4 + 6 * t)
        c.drawPath(rrect(-lw / 2, -94, lw / 2, 94, 10), paint(C["laptop"]))
        c.drawPath(rrect(-lw / 2, 70, lw / 2, 94, 8), paint(C["laptop_d"]))
        gp = paint(C["glow"], a=150); gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 7))
        c.drawPath(rrect(-lw / 2 + 4, 62, lw / 2 - 4, 72, 5), gp)
        c.drawPath(rrect(-lw / 2 + 4, 64, lw / 2 - 4, 70, 3), paint(C["glow"]))
        c.restore()
    # ------------------------------------------------------------- near arm
    arm = pose.arm
    if A and arm.hand == "fist" and abs(arm.a1 - A1_REST) < 1e-6:
        sw = -9.0 * A * math.sin(ph)
        arm = Arm(arm.a1 + sw, arm.a2 + sw * 1.25, arm.hand, arm.open, arm.k)
    E, d2, n2 = draw_arm(c, Pn, arm, C["light"])
    draw_hand(c, E, d2, n2, arm, C["skin"], flip_thumb=-1.0)
    # ------------------------------------------------------------- head
    draw_head(c, clamp01(pose.head_turn), pose.tilt)
    c.restore()


def draw_head(c, th, tilt):
    e = th
    hc = lerp(HEAD_C_P[0], 520, e)
    c.save()
    if tilt:
        c.rotate(-tilt, 530, 486)
    # ears that sit at the silhouette (front-ish views) are drawn first
    head = lerp_pts(HEAD_P, HEAD_F, e)
    hp = poly(head)
    c.drawPath(hp, paint(C["skin"]))
    # nose: shrinks and fades towards the front view
    nk = math.cos(e * math.pi / 2)
    if nk > 0.05:
        nb = 60 * nk
        nose = [(hc + (x - HEAD_C_P[0]) * (nb / 60.0) if i != 1 else hc + nb + 17 * nk, y) for i, (x, y) in enumerate(NOSE_P)]
        nose[0] = (hc + 60 * nk, 398); nose[2] = (hc + 56 * nk, 447)
        np_ = paint(C["skin"]); np_.setAlphaf(clamp01(nk * 1.6))
        c.drawPath(poly(nose), np_)
    # ears
    ex_near = lerp(515.5 - HEAD_C_P[0], -60, e)
    c.drawPath(oval(hc + ex_near, 411.5, 12.5 * (1 - 0.35 * e), 18.5), paint(C["skin_sh"]))
    if e > 0.6:
        k = seg(e, 0.6, 1.0)
        c.drawPath(oval(hc + lerp(48, 60, k), 411.5, 8.1 * k + 0.1, 18.5), paint(C["skin_sh"]))
    # hair at the nape: rotates away behind the head
    if e < 0.62:
        ca = math.cos(e * math.pi / 2)
        bnd = hc + 60 * math.cos(math.radians(133) + e * math.pi / 2)
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(-5000, -5000, bnd, 5000), doAntiAlias=True)
        c.drawPath(poly([(hc + (x - HEAD_C_P[0]) * ca, y) for x, y in HAIR_P]), paint(C["hair"]))
        c.restore()
    # eyes
    ep = paint(C["eye"])
    near = lerp(575.5 - HEAD_C_P[0], -27, e)
    c.drawPath(oval(hc + near, 391.5, 7.6 * (1 - 0.25 * (1 - abs(2 * e - 1)) * 0), 8.2), ep)
    if e > 0.3:
        k = seg(e, 0.3, 1.0)
        c.drawPath(oval(hc + lerp(58, 27, smooth(k)), 391.5, 7.6 * min(1, k * 3), 8.2), ep)
    # doppi
    hx = hc + lerp(HAT_CX - HEAD_C_P[0], 0, e)
    dx = hx - HAT_CX
    c.drawPath(poly([(x + dx, y) for x, y in HAT_P]), paint(C["hat"]))
    c.drawPath(poly([(x + dx, y) for x, y in RIM_P]), paint(C["cream"]))
    fronts = [-48, 0, 48]
    for (px, py), fx in zip(PEPPERS, fronts):
        ox = lerp(px - HAT_CX, fx, e)
        cx = hx + ox
        cy = lerp(py, 300, e)
        c.save(); c.translate(cx, cy); c.rotate(-27)
        pc = paint(C["cream"])
        c.drawPath(oval(0, 1.5, 6.8, 12.8), pc)
        c.restore()
        c.drawPath(circle(cx + 4.2, cy - 13.5, 3.6), pc)
    c.restore()
