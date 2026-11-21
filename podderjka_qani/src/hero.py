# Hero rig for this video. The drawing code, geometry and colours are those of qahramon.py
# (imported unchanged); this copy only adds poses the scenes need:
#   legs=  "sit" / "sit_f" (bench, profile / front), "kneel", or a dict of custom leg chains (hop, jump, dance)
#   hyaw=  head yaw independent of the body (turn only the head to the camera)
#   lhand= shape for the far hand ("open", "flat", "point", ...), eye_k / eye_hl (bigger eyes with a highlight)
import math
from qahramon import (SKIN, SKIN_D, HAIR, CHAPAN, CHAPAN_D, CHAPAN_L, IKAT1, IKAT2, GOLD, BELT, SHIRT, DOPPI, BOOT, CREAM,
                      LEG, P_COAT, F_COAT, P_TRIM, F_TRIM, P_COLLAR, F_COLLAR, P_DOPPI, F_DOPPI, P_BOOT, F_BOOT,
                      _lp, _lv, coat_edge_x, RA, draw_hand, clamp01, lerp, lerpc, rot, ellipse_pts, point_in_poly,
                      dist_to_poly, ease_io)

DEF = dict(yaw=0.0, dir=1, walk=0.0, phase=0.0, rarm=None, rshape="fist", rangle=90.0, head_tilt=0.0, shake=0.0,
           bow=0.0, look=0.0, larm=None, lshape=None, langle=90.0, legs=None, hyaw=None, eye_k=1.0, eye_hl=False,
           flutter=None, lean=0.0, rise=0.0)

def _boot_poly(F, yaw, mirror=False, ang=0.0):
    bt = _lp(P_BOOT, F_BOOT, yaw)
    if mirror: bt = [(-x, y) for x, y in bt]
    if ang: bt = [rot(p, ang, (0, 0)) for p in bt]
    return [(F[0] + x, F[1] + y) for x, y in bt]

def leg_chains(mode, yaw, P):
    """returns (hip_y, chains) ; chain = (hip, knee, foot, boot_angle, far)"""
    if mode == "sit":         # profile on a bench, seat at y=-92
        hs = P.get("seat", 92.0)
        return -hs, [((-2, -hs), (58, -hs - 2), (60, 0), 0.0, True), ((2, -hs), (64, -hs - 1), (68, 0), 0.0, False)]
    if mode == "sit_f":       # facing the camera on a bench; thighs foreshortened. rise: 0 seated -> 1 standing
        r = P.get("rise", 0.0)
        hs = lerp(P.get("seat", 92.0), LEG, r)
        kx, fx = lerp(19, 13, r), lerp(21, 13, r)
        ky = lerp(-hs + 30, -88, r)
        return -hs, [((-13, -hs), (-kx, ky), (-fx, 0), 0.0, False), ((13, -hs), (kx, ky), (fx, 0), 0.0, False)]
    if mode == "kneel":
        return -96.0, [((-3, -96), (6, -10), (-76, -8), 90.0, True), ((3, -96), (14, -10), (-66, -8), 90.0, False)]
    if isinstance(mode, dict):
        return mode["hip_y"], mode["chains"]
    raise ValueError(mode)

def draw_hero(cv, X, Y, s, **kw):
    P = dict(DEF); P.update(kw)
    yaw = clamp01(P["yaw"]); dr = P["dir"]
    yawH = clamp01(P["hyaw"]) if P["hyaw"] is not None else yaw
    legs_mode = P["legs"]
    th = math.radians(20) * P["walk"] * math.sin(P["phase"])
    if legs_mode is None:
        hip_y = -LEG * math.cos(th)
        chains = None
    else:
        hip_y, chains = leg_chains(legs_mode, yaw, P)
    dy = LEG + hip_y                    # body offset (>0 = lower)
    bow = math.radians(P["bow"])
    pivot = (0.0, hip_y)
    lean = P["lean"]

    def bend(p):
        x, y = p[0], p[1] + dy
        h = pivot[1] - y
        if lean and h > 0: x += lean * h / 100.0
        if bow <= 0 or h <= 0: return (x, y)
        a = bow * min(1.0, h / 45.0)
        rx, ry = rot((x, y), math.degrees(a), pivot)
        cx_, cy_ = x + h * math.sin(a) * 0.35, pivot[1] - h * math.cos(a) * 0.97
        return (lerp(rx, cx_, yaw), lerp(ry, cy_, yaw))

    neck = bend((4, -300))
    ht = P["head_tilt"]
    def headp(p):
        q = bend(p)
        return rot(q, ht, neck) if ht else q

    def L(p): return (X + dr * p[0] * s, Y + p[1] * s)
    def Lp(pts): return [L(p) for p in pts]
    def S_(v): return v * s

    front = yaw >= 0.5
    frontH = yawH >= 0.5

    # ---------------- arms geometry
    shR = _lv((2, -288), (-33, -286), yaw)
    shL = _lv((7, -288), (33, -286), yaw)
    if P["larm"] is not None:
        eL0, handL = P["larm"]
    else:
        swl = P["walk"] * 22 * math.sin(P["phase"])
        eL0 = _lv((0 + swl * 0.35, -205), (44, -208), yaw)
        handL = _lv((12 + swl, -144), (46, -140), yaw)
    if P["rarm"] is None:
        sw = P["walk"] * 22 * math.sin(P["phase"] + math.pi)
        rE = _lv((-4 + sw * 0.35, -205), (-44, -208), yaw)
        rT = _lv((10 + sw, -141), (-46, -140), yaw)
    else:
        rE, rT = P["rarm"]
    shR_b, shL_b = bend(shR), bend(shL)
    eR, hR = bend(rE), bend(rT)
    eL, hL = bend(eL0), bend(handL)
    sleeve_far = lerpc(CHAPAN_D, CHAPAN_L, yaw)

    def diamond(c, rx, ry, col, ang=0.0):
        pts = [(c[0], c[1] - ry), (c[0] + rx, c[1]), (c[0], c[1] + ry), (c[0] - rx, c[1])]
        if ang: pts = [rot(p, ang, c) for p in pts]
        cv.poly(Lp(pts), col)

    def sleeve(Sh, E, Hd, col, upper=True, fore=True):
        if upper:
            cv.capsule(L(Sh), L(E), S_(12.5), S_(11.5), col)
        if fore:
            d = (Hd[0] - E[0], Hd[1] - E[1]); n = math.hypot(*d) or 1
            u = (d[0] / n, d[1] / n)
            wr = (Hd[0] - u[0] * 8, Hd[1] - u[1] * 8)
            cv.capsule(L(E), L(wr), S_(11.5), S_(10.8), col)
            c0 = (wr[0] - u[0] * 6, wr[1] - u[1] * 6)
            cv.capsule(L(c0), L(wr), S_(11.2), S_(11.0), GOLD)
            for k in (0.3, 0.62):
                q = (E[0] + (wr[0] - E[0]) * k, E[1] + (wr[1] - E[1]) * k)
                diamond(q, 3.0, 4.6, IKAT2 if k < 0.5 else IKAT1, ang=math.degrees(math.atan2(u[1], u[0])) - 90)
        if upper:
            q = ((Sh[0] + E[0]) / 2, (Sh[1] + E[1]) / 2)
            d = (E[0] - Sh[0], E[1] - Sh[1])
            diamond(q, 3.0, 4.6, IKAT1, ang=math.degrees(math.atan2(d[1], d[0])) - 90)

    def lhand_draw():
        if P["lshape"]:
            draw_hand(cv, Lp, hL, eL, P["lshape"], P["langle"], front, dr)
        else:
            cv.poly(Lp(ellipse_pts(hL[0], hL[1], 8.5, 7.5 if not front else 8.0, 14)), SKIN)

    # ---------------- far arm (profile: behind body)
    if not front:
        sleeve(shL_b, eL, hL, sleeve_far, upper=True, fore=True)
        lhand_draw()

    # ---------------- legs
    if chains is None:
        legs = []
        for k, (hxp, hxf) in enumerate(((-3, 13), (3, -13))):
            ang = th if k == 0 else -th
            hx_ = lerp(hxp, hxf, yaw)
            Hh = (hx_, hip_y)
            F = (hx_ + LEG * math.sin(ang) * (1 - yaw), 0.0)
            legs.append((Hh, F, k))
        for Hh, F, k in sorted(legs, key=lambda q: q[2]):
            col = BOOT if (k == 1 or front) else lerpc(BOOT, (22, 15, 12), 0.35)
            cv.capsule(L(Hh), L((F[0], F[1] - 10)), S_(9.5), S_(9.0), col)
            bt = _lp(P_BOOT, F_BOOT, yaw)
            if front and k == 1: bt = [(-x, y) for x, y in bt]
            cv.poly(Lp([(F[0] + x, F[1] + y) for x, y in bt]), col)
    else:
        for j, (Hh, Kn, F, bang, far) in enumerate(sorted(chains, key=lambda c: not c[4])):
            col = lerpc(BOOT, (22, 15, 12), 0.35) if (far and not front) else BOOT
            cv.capsule(L(Hh), L(Kn), S_(9.5), S_(9.3), col)
            cv.capsule(L(Kn), L(F), S_(9.3), S_(9.0), col)
            cv.poly(Lp(_boot_poly((F[0], F[1]), yaw, mirror=(front and j == 1), ang=bang)), col)

    # ---------------- coat
    flutter = P["walk"] * 3.5 if P["flutter"] is None else P["flutter"]
    coat_src = _lp(P_COAT, F_COAT, yaw)
    coat = []
    if legs_mode == "sit_f":
        r = P["rise"]; cfac = lerp(0.40, 1.0, r); xf = lerp(1.12, 1.0, r)
        def cmp(p):
            x, y = p
            if y > -175: return (x * xf, -175 + (y + 175) * cfac)
            return p
        coat = [bend(cmp(p)) for p in coat_src]
        hem_line = [(x, y - 2) for x, y in coat[7:11]]
        trim_low = None
    elif legs_mode in ("sit", "kneel"):
        # upper coat unchanged, lower coat re-draped over the lap / to the ground
        top = [bend(p) for p in coat_src if p[1] <= -200]
        back = [p for p in coat_src[:9] if p[1] <= -200]
        frontp = [p for p in coat_src[9:] if p[1] <= -200]
        hy = hip_y
        if legs_mode == "sit":
            lap = [(-35, hy - 8), (-33, hy + 10), (48, hy + 13), (58, hy + 15), (62, hy + 36), (82, hy + 36), (80, hy + 8),
                   (74, hy - 15), (36, hy - 17), (33, hy - 30)]
        else:
            lap = [(-36, hy + 8), (-46, hy + 60), (-58, hy + 90), (-24, hy + 92), (20, hy + 92), (34, hy + 70), (38, hy + 10)]
        coat = [bend(p) for p in back] + lap + [bend(p) for p in frontp]
        hem_line = {"sit": [(58, hy + 15), (62, hy + 36), (82, hy + 36)],
                    "kneel": [(-58, hy + 90), (-24, hy + 92), (20, hy + 92), (34, hy + 70)]}[legs_mode]
        trim_low = {"sit": [(33, hy - 30), (36, hy - 17), (74, hy - 15), (80, hy + 8), (82, hy + 36)],
                    "kneel": [(38, hy + 10), (34, hy + 70)]}[legs_mode]
    else:
        for (x, y) in coat_src:
            if y > -150: x += flutter * math.sin(P["phase"] * 2 + 1.0) * ((y + 150) / 85.0)
            coat.append(bend((x, y)))
        hem_line = [(x, y - 2) for x, y in coat[7:11]]
        trim_low = None
    cv.poly(Lp(coat), CHAPAN)
    back_strip = coat[1:8] if legs_mode in (None, "sit_f") or isinstance(legs_mode, dict) else coat[1:len(back) + 2]
    inner = [(x + lerp(13, 10, yaw), y) for x, y in back_strip][::-1]
    cv.poly(Lp(back_strip + inner), CHAPAN_D)
    # ikat diamonds (grid in body coords, kept inside the coat)
    ys0 = -288 + dy
    for ci in range(-4, 14):
        cx0 = -44 + 11.5 * ci
        for ri in range(16):
            y0 = -288 + 16 * ri + (8 if ci % 2 else 0)
            if -214 < y0 < -186: continue
            if legs_mode is None or isinstance(legs_mode, dict):
                if ci < 0 or ci > 8 or ri > 13: continue
                p = bend((cx0 + (flutter * math.sin(P["phase"] * 2 + 1.0) * ((y0 + 150) / 85.0) if y0 > -150 else 0), y0))
            elif legs_mode == "sit_f":
                if ci < 0 or ci > 8 or ri > 13: continue
                p = bend(cmp((cx0, y0)))
            else:
                p = bend((cx0, y0)) if y0 <= -200 else (cx0, y0 + dy)
            if point_in_poly(p[0], p[1], coat) and dist_to_poly(p[0], p[1], coat) > 5.5:
                diamond(p, 2.7, 4.3, IKAT2 if ci % 2 == 0 else IKAT1)
    if legs_mode == "sit_f":
        trim = [bend(cmp(p)) for p in _lp(P_TRIM, F_TRIM, yaw)]
    else:
        trim = [bend(p) for p in _lp(P_TRIM, F_TRIM, yaw)]
    if trim_low is not None:
        trim = [p for p in trim if p[1] <= hip_y - 30] + trim_low
    cv.line(Lp(trim), GOLD, S_(3.6))
    cv.line(Lp(hem_line), GOLD, S_(4.2))
    # belt
    by0, by1 = -210, -196
    bl0 = coat_edge_x(coat, by0 + dy, -1) - 3; br0 = coat_edge_x(coat, by0 + dy, 1) + 3
    bl1 = coat_edge_x(coat, by1 + dy, -1) - 3; br1 = coat_edge_x(coat, by1 + dy, 1) + 3
    cv.poly(Lp([(bl0, by0 + dy), (br0, by0 + dy), (br1, by1 + dy), (bl1, by1 + dy)]), BELT)
    if front:
        kx = 5
        cv.poly(Lp([(kx - 4, by1 + dy - 2), (kx + 4, by1 + dy - 2), (kx + 6, by1 + dy + 16), (kx - 1, by1 + dy + 18)]), BELT)
    else:
        cv.poly(Lp([(bl0 + 2, by0 + dy + 6), (bl0 + 7, by0 + dy + 8), (bl0 - 3, by1 + dy + 22), (bl0 - 8, by1 + dy + 19)]), BELT)

    # ---------------- neck, collar, head
    neck_pts = [headp(p) for p in [(lerp(-3, -6, yawH), -314), (lerp(10, 8, yawH), -314), (lerp(10, 8, yawH), -296), (lerp(-3, -6, yawH), -296)]]
    cv.poly(Lp(neck_pts), SKIN_D)
    cv.poly(Lp([bend(p) for p in _lp(P_COLLAR, F_COLLAR, yaw)]), SHIRT)
    sh = P["shake"]
    hc = headp((lerp(6, 3, yawH) + sh * 2.0, -323))
    face = [headp((lerp(6, 3, yawH) + sh * 2.0 + lerp(16.5, 18, yawH) * math.cos(a), -323 + 20.5 * math.sin(a)))
            for a in [i * 2 * math.pi / 36 for i in range(36)]]
    cv.poly(Lp(face), SKIN)
    ek = P["eye_k"]
    eyes = []
    if not frontH:
        nose = [headp(p) for p in [(20, -329), (26.5, -318), (21, -313)]]
        cv.poly(Lp(nose), SKIN)
        hair = [headp(p) for p in [(-13, -339), (-5, -339), (-3, -329), (-5, -315), (-11, -308), (-17.5, -316), (-18, -330)]]
        cv.poly(Lp(hair), HAIR)
        ear = [headp((-1 + 3.2 * math.cos(a), -322 + 4.8 * math.sin(a))) for a in [i * 2 * math.pi / 12 for i in range(12)]]
        cv.poly(Lp(ear), SKIN_D)
        ey = headp((14 + P["look"] * 1.5, -327))
        cv.poly(Lp(ellipse_pts(ey[0], ey[1], 2.2 * ek, 2.5 * ek, 10)), (25, 22, 20))
        eyes.append((ey, 2.2 * ek))
    else:
        for side in (-1, 1):
            if side < 0: hp_ = [(-19.5, -339), (-11, -339), (-14, -330), (-19, -326)]
            else: hp_ = [(22, -339), (25.5, -339), (24.5, -329), (21, -331)]
            cv.poly(Lp([headp((x + sh * 2.0, y)) for x, y in hp_]), HAIR)
        for ex, r in ((-4.5, 2.1), (9.5, 2.0)):
            ey = headp((ex + sh * 6.0 + P["look"] * 2, -325))
            cv.poly(Lp(ellipse_pts(ey[0], ey[1], r * ek, r * 1.15 * ek, 12)), (25, 22, 20))
            eyes.append((ey, r * ek))
    if P["eye_hl"]:
        for ey, r in eyes:
            cv.poly(Lp(ellipse_pts(ey[0] + r * 0.35 * dr, ey[1] - r * 0.4, r * 0.36, r * 0.36, 8)), CREAM)
    dp = [headp((x + sh * 1.5, y)) for x, y in _lp(P_DOPPI, F_DOPPI, yawH)]
    cv.poly(Lp(dp), DOPPI)
    cv.line(Lp([headp((-20.5 + sh * 1.5, -337.8)), headp((2 + sh * 1.5, -338.3)), headp((25 + sh * 1.5, -337.8))]), SHIRT, S_(2.8))
    for mx_, my_ in ((-12, -348), (0, -350), (12, -350), (22, -348)):
        if mx_ > 20 and not frontH: continue
        c = headp((mx_ + sh * 1.5 + (2 if frontH else -1), my_))
        pts = ellipse_pts(c[0], c[1], 1.9, 4.0, 10, ang=-28 + ht)
        cv.poly(Lp(pts), SHIRT)
        cv.poly(Lp(ellipse_pts(c[0] + 0.9, c[1] - 3.4, 1.0, 1.0, 6)), SHIRT)

    # ---------------- near arms
    if front:
        sleeve(shL_b, eL, hL, CHAPAN_L, upper=True, fore=True)
        lhand_draw()
    sleeve(shR_b, eR, hR, CHAPAN_L, upper=True, fore=True)
    draw_hand(cv, Lp, hR, eR, P["rshape"], P["rangle"], front, dr)
    return dict(head=L(hc), hand=L(hR), lhand=L(hL), neck=L(neck), hip=L((0, hip_y)), top=L(headp((2, -363))),
                elbow=L(eR), lelbow=L(eL), L=L, s=s)
