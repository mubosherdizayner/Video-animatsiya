# The hero (traced from the reference image, same shapes and colors) as a posable rig, plus the friend
# (same proportions, muted dusty-blue chapan) and plain silhouette people.
# All geometry is in the reference image's pixel space; the rig's origin is the ground point (520, 1700).
import math
import skia
from gfx import *

GROUND = (520.0, 1700.0)
HEIGHT = 1452.0                       # doppi top (248) to boot sole (1700)
SHOULDER = (527.0, 548.0)
L_UP, L_FORE, HAND_OFF = 333.0, 205.0, 56.0
REST_ELBOW = (505.0, 880.0)
REST_WRIST = (550.0, 1080.0)
NECK = (528.0, 486.0)

HERO = dict(
    chapan="#3F7B61", back="#2F634D", arm="#4C8A6E", ikat_l="#6FA586", ikat_g="#C7A548", trim="#BE8642",
    belt="#B4473B", collar="#E8E1D3", skin="#EBC8A2", skin_d="#D8B089", hair="#2E231D", eye="#191614",
    doppi="#1D2427", pods="#E8E1D3", rim="#E8E1D3", boot="#33241E", boot_far="#291D18", neck="#D8B089",
    ikat=True)

def friend_colors(night=0.0, backlit=0.0):
    """friend: one muted accent (dusty-blue chapan); everything else in the scene's dark silhouette tones"""
    dark = mix("#2E3C40", "#1A2433", night)
    mid = mix("#56696D", "#36455A", night)
    ch = mix("#6E8496", "#4F6377", night * 0.7)
    c = dict(chapan=ch, back=mix(ch, dark, 0.28), arm=mix(ch, "#8296A6", 0.25), ikat_l=ch, ikat_g=ch,
             trim=mix(ch, dark, 0.4), belt=mix(dark, ch, 0.25), collar=mid, skin=mid, skin_d=mix(mid, dark, 0.3),
             hair=dark, eye="#10171F", doppi=mix(dark, "#10171F", 0.5), pods=mix(dark, mid, 0.35), rim=mix(dark, mid, 0.5),
             boot=dark, boot_far=mix(dark, "#10171F", 0.4), neck=mix(mid, dark, 0.3), ikat=False)
    if backlit > 0:
        tgt = mix("#2E3C40", "#1A2433", night)
        c = {k: (mix(v, tgt, backlit * (0.55 if k in ("chapan", "arm", "back") else 0.8)) if isinstance(v, str) else v) for k, v in c.items()}
    return c

def silhouette_colors(c):
    return {k: (c if isinstance(v, str) else False) for k, v in HERO.items()}

# ---------------------------------------------------------------- reference shapes
BODY = [(415, 524), (465, 500), (540, 499), (583, 517), (613, 537), (647, 650), (650, 860), (657, 1100),
        (672, 1300), (686, 1427), (565, 1449), (437, 1449), (350, 1427), (368, 1300), (384, 1100), (391, 915),
        (395, 860), (393, 740), (397, 598)]
BACK = [(415, 524), (468, 524), (450, 600), (447, 860), (436, 1100), (422, 1300), (405, 1432), (350, 1427),
        (368, 1300), (384, 1100), (391, 915), (395, 860), (393, 740), (397, 598)]
TRIM_FRONT = [(583, 521), (608, 538), (641, 651), (644, 860), (651, 1100), (666, 1300), (680, 1426)]
HEM = [(350, 1428), (440, 1446), (565, 1446), (684, 1428)]
BELT = (382, 860, 657, 916)
TAIL = [(382, 906), (402, 914), (372, 1004), (351, 991)]
COLLAR = [(536, 488), (563, 486), (589, 508), (581, 553), (567, 521), (536, 505)]
DOPPI = [(456, 260), (529, 248), (600, 260), (616, 288), (619, 343), (437, 343), (440, 292)]
PODS = [((468, 307), (471, 294)), ((516, 300), (519, 286)), ((564, 300), (567, 286))]
HAIR = [(460, 356), (502, 356), (508, 384), (504, 410), (500, 440), (476, 468), (450, 438), (449, 380)]
NOSE = [(602, 390), (626, 428), (606, 443), (603, 450), (588, 446)]
FACE_C, FACE_R = (545.0, 423.0), 63.0
BOOT = [(490, 1446), (569, 1446), (569, 1640), (576, 1647), (590, 1660), (615, 1675), (620, 1700), (487, 1700), (489, 1680)]
SIT_LAP = [(391, 905), (380, 1010), (372, 1072), (382, 1094), (715, 1094), (745, 1078), (742, 1040), (700, 1000), (648, 930), (650, 905)]
SIT_HEM = [(380, 1092), (730, 1092)]

def _wind(pts, wind, y0=880.0, y1=1450.0, amp=46.0):
    if not wind: return pts
    out = []
    for x, y in pts:
        k = clamp01((y - y0) / (y1 - y0)) ** 1.5
        out.append((x + wind * amp * k, y - abs(wind) * 6 * k * k))
    return out

def _rot(p, c, ang):
    s, co = math.sin(math.radians(ang)), math.cos(math.radians(ang))
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * co - y * s, c[1] + x * s + y * co)

def arm_ik(target, bend=1.0, shoulder=SHOULDER, fs=1.0):
    """wrist target -> (elbow, wrist); bend=+1 keeps the elbow down/back (natural); fs<1 foreshortens the upper arm"""
    L1 = L_UP * fs
    sx, sy = shoulder; tx, ty = target
    dx, dy = tx - sx, ty - sy; d = math.hypot(dx, dy)
    d = min(max(d, abs(L1 - L_FORE) + 1), L1 + L_FORE - 0.5)
    base = math.atan2(dy, dx)
    off = math.acos(max(-1.0, min(1.0, (L1 ** 2 + d ** 2 - L_FORE ** 2) / (2 * L1 * d))))
    a = base + bend * off
    ex, ey = sx + L1 * math.cos(a), sy + L1 * math.sin(a)
    ang2 = math.atan2(ty - ey, tx - ex)
    return (ex, ey), (ex + L_FORE * math.cos(ang2), ey + L_FORE * math.sin(ang2))

def arm_fk(a1, a2, shoulder=SHOULDER):
    """angles in degrees from straight down, positive = forward (+x)"""
    sx, sy = shoulder
    ex, ey = sx + L_UP * math.sin(math.radians(a1)), sy + L_UP * math.cos(math.radians(a1))
    return (ex, ey), (ex + L_FORE * math.sin(math.radians(a2)), ey + L_FORE * math.cos(math.radians(a2)))

def _capsule(cv, a, b, ra, rb, c):
    dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    poly(cv, [(a[0] + nx * ra, a[1] + ny * ra), (b[0] + nx * rb, b[1] + ny * rb),
              (b[0] - nx * rb, b[1] - ny * rb), (a[0] - nx * ra, a[1] - ny * ra)], c)

def draw_arm(cv, C, elbow, wrist, hand="fist", far=False, finger_dir=None, finger_len=1.0, shoulder=SHOULDER, phone=None):
    sleeve = C["back"] if far else C["arm"]
    circle(cv, shoulder[0], shoulder[1], 48, sleeve)
    _capsule(cv, shoulder, elbow, 48, 45, sleeve)
    circle(cv, elbow[0], elbow[1], 45, sleeve)
    _capsule(cv, elbow, wrist, 45, 43, sleeve)
    dx, dy = wrist[0] - elbow[0], wrist[1] - elbow[1]; L = math.hypot(dx, dy) or 1
    ux, uy = dx / L, dy / L
    ang = math.degrees(math.atan2(uy, ux)) - 90
    if C.get("ikat") and not far:
        Lu = math.hypot(elbow[0] - shoulder[0], elbow[1] - shoulder[1]) or 1
        ux1, uy1 = (elbow[0] - shoulder[0]) / Lu, (elbow[1] - shoulder[1]) / Lu
        a1 = math.degrees(math.atan2(uy1, ux1)) - 90
        for f, cc, off in ((0.494, C["ikat_l"], 0),):
            px, py = shoulder[0] + ux1 * Lu * f - uy1 * off, shoulder[1] + uy1 * Lu * f + ux1 * off
            with xf(cv, px, py, 1, a1): diamond(cv, 0, 0, 11, 17, cc, 0.9)
        for f, cc, off in ((0.33, C["ikat_g"], 0), (0.69, C["ikat_l"], 0)):
            px, py = elbow[0] + ux * L * f - uy * off, elbow[1] + uy * L * f + ux * off
            with xf(cv, px, py, 1, ang): diamond(cv, 0, 0, 11, 17, cc, 0.9)
    hx, hy = wrist[0] + ux * HAND_OFF, wrist[1] + uy * HAND_OFF
    skin = C["skin_d"] if far else C["skin"]
    if phone is not None and not far:
        _phone(cv, hx, hy, ang, phone)
    # finger (behind the fist outline; for "shh" on top, across the lips)
    fd = finger_dir if finger_dir is not None else (ux, uy)
    fl = math.hypot(*fd) or 1; fx, fy = fd[0] / fl, fd[1] / fl
    if hand in ("point", "tap") and finger_len > 0:
        L2 = 50 * finger_len
        line(cv, [(hx, hy), (hx + fx * (26 + L2), hy + fy * (26 + L2))], skin, 17)
    # cuff (gold trim) and fist
    ellipse(cv, wrist[0] + ux * 4, wrist[1] + uy * 4, 47, 50, C["trim"] if not far else C["back"], 1, ang)
    oct_ = [(hx + 33 * math.cos(math.radians(ang + 22.5 + 45 * k)), hy + 33 * math.sin(math.radians(ang + 22.5 + 45 * k))) for k in range(8)]
    poly(cv, oct_, skin)
    if hand == "shh" and finger_len > 0:
        L2 = 62 * finger_len
        line(cv, [(hx + 4, hy - 10), (hx + 4 + fx * (20 + L2), hy - 10 + fy * (20 + L2))], skin, 19)
        line(cv, [(hx + 4 + fx * (20 + L2) - 6, hy - 10 + fy * (20 + L2) + 10), (hx + 4 + fx * (20 + L2) - 6, hy - 10 + fy * (20 + L2) + 26)], C["skin_d"], 3, 0.8)
    if phone is not None and not far:
        _phone(cv, hx, hy, ang, phone, front=True)
    return hx, hy

def _phone(cv, hx, hy, ang, glow_a, front=False):
    """flat dark phone held in the fist; faint glow"""
    with xf(cv, hx, hy, 1, ang + 90):
        if not front:
            if glow_a > 0: glow(cv, 18, -4, 110, "#F4EDDF", 0.30 * glow_a)
            return
        rrect(cv, -6, -34, 34, 62, 8, "#1F292C")
        if glow_a > 0: rrect(cv, -2, -30, 26, 54, 5, "#AFC2C4", 0.55 * glow_a)

def draw_head(cv, C, turn=0.0, eye="open", eye_dx=0.0):
    t = clamp01(turn)
    # hair at the nape (moves behind as the head turns toward camera)
    hx0 = 455
    hair = [(hx0 + (x - hx0) * (1 - 0.45 * t), y) for x, y in HAIR]
    circle(cv, FACE_C[0], FACE_C[1], FACE_R, C["skin"])
    poly(cv, hair, C["hair"])
    # nose: profile triangle that folds into the face as he turns
    k = 1 - 0.82 * t
    nose = [(FACE_C[0] + (x - FACE_C[0]) * (0.55 + 0.45 * k) - 10 * t, y) for x, y in NOSE]
    nose = [(x if x < 600 - 10 * t else 600 - 10 * t + (x - (600 - 10 * t)) * k, y) for x, y in nose]
    poly(cv, nose, C["skin"])
    # ear
    if t < 0.95: ellipse(cv, 516 - 24 * t, 412, 12.5 * (1 - 0.35 * t), 19, C["skin_d"], 1 - t)
    # eye(s)
    ex = 576 - 12 * t + eye_dx
    if eye == "open":
        ellipse(cv, ex, 392, 8.5, 9.5, C["eye"])
        if t > 0.05: ellipse(cv, 528 + 2 * (1 - t) + eye_dx * 0.6, 393, 8.0 * t, 9.0, C["eye"], t)
    elif eye == "closed":
        line(cv, [(ex - 9, 394), (ex + 9, 394)], C["eye"], 4)
    elif eye == "dollar":
        text(cv, "$", ex, 391, 30, "#C7A548", 1.0, tf="xb")
    # doppi
    poly(cv, DOPPI, C["doppi"])
    for (pc, kn) in PODS:
        dx = -10 * t
        ellipse(cv, pc[0] + dx, pc[1], 9.5, 16.5, C["pods"], 1, -20)
        circle(cv, kn[0] + dx, kn[1], 4, C["pods"])
    rrect(cv, 432, 342, 194, 12, 6, C["rim"])
    rrect(cv, 436, 353, 184, 3, 1.5, C["doppi"])

def draw_person(cv, x, y, s, C=HERO, facing=1, t=0.0, arm=None, arm_far=None, hand="fist", hand_far="fist",
                finger_dir=None, finger_len=1.0, turn=0.0, tilt=0.0, lean=0.0, walk=None, wind=0.0, sit=False,
                eye="open", phone=None, alpha=1.0, eye_dx=0.0, crop_below=None, scale_y=1.0, layer="all"):
    """
    x, y: screen position of the ground point between the feet; s: scale (1 = reference size, 1452 px tall).
    arm / arm_far: ('fk', a1, a2) or ('ik', (wx, wy), bend) in reference space; None = rest pose.
    Returns dict with screen positions of useful anchors (hand, head, shoulder).
    """
    gx, gy = GROUND
    m0 = cv.getTotalMatrix()
    cv.save()
    if alpha < 0.999: cv.saveLayerAlpha(None, int(255 * clamp01(alpha)))
    cv.translate(x, y); cv.scale(s * facing, s * scale_y)
    if lean: cv.rotate(lean)
    cv.translate(-gx, -gy)
    bob = 0.0; fb = nb = (0.0, 0.0)
    hem_sw = 0.0
    if walk is not None:
        ph = walk
        nb = (36 * math.sin(ph), -14 * max(0.0, math.cos(ph)))
        fb = (-36 * math.sin(ph) - 20, -14 * max(0.0, -math.cos(ph)))
        bob = -6 * abs(math.cos(ph)); hem_sw = 0.25 * math.sin(ph)
    else:
        fb = (-20.0, 0.0)
    if sit:
        cv.translate(0, 1700 - 1094)
    w_eff = wind + hem_sw
    hf = None
    # far arm (behind everything)
    if arm_far is not None and layer != "arm":
        el, wr = _arm_pts(arm_far)
        hf = draw_arm(cv, C, el, wr, hand_far, far=True)
    cv.translate(0, bob)
    if layer == "arm":
        el, wr = _arm_pts(arm)
        hx, hy = draw_arm(cv, C, el, wr, hand, finger_dir=finger_dir, finger_len=finger_len, phone=phone)
        cv.restore()
        if alpha < 0.999: cv.restore()
        return {}
    # boots
    if not sit:
        if crop_below is None or crop_below > 1446:
            with xf(cv, fb[0], fb[1]): poly(cv, BOOT, C["boot_far"])
            with xf(cv, nb[0], nb[1]): poly(cv, BOOT, C["boot"])
    # chapan
    if sit:
        spoly(cv, SIT_LAP, C["chapan"])
        poly(cv, [(560, 1080), (700, 1080), (742, 1094), (560, 1094)], C["boot"])
        body = [p for p in BODY if p[1] <= 915] + [(650, 916), (391, 916)]
        body = BODY[:7] + [(650, 915), (391, 915)] + BODY[-3:]
        poly(cv, body, C["chapan"])
        back = BACK[:4] + [(445, 915), (391, 915)] + BACK[-3:]
        poly(cv, back, C["back"])
        line(cv, SIT_HEM, C["trim"], 15)
        line(cv, TRIM_FRONT[:4] + [(645, 915)], C["trim"], 13)
        if C.get("ikat"):
            clip = path(body); cv.save(); cv.clipPath(clip, doAntiAlias=True); _ikat(cv, C, 0.0, ymax=915); cv.restore()
    else:
        body = _wind(BODY, w_eff); back = _wind(BACK, w_eff)
        bp = path(body)
        cv.drawPath(bp, paint(C["chapan"]))
        poly(cv, back, C["back"])
        if C.get("ikat"):
            cv.save(); cv.clipPath(bp, doAntiAlias=True); _ikat(cv, C, w_eff); cv.restore()
        line(cv, _wind(HEM, w_eff), C["trim"], 15)
        line(cv, _wind(TRIM_FRONT, w_eff), C["trim"], 13)
    # belt
    bx0, by0, bx1, by1 = BELT
    poly(cv, [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)], C["belt"])
    tail = TAIL if sit else [(px + (w_eff * 60 + 8 * math.sin(t * 5.3)) * clamp01((py - 905) / 100), py) for px, py in TAIL]
    poly(cv, tail, C["belt"])
    # neck + collar
    poly(cv, [(508, 470), (537, 470), (537, 503), (508, 503)], C["neck"])
    poly(cv, COLLAR, C["collar"])
    # head
    cv.save(); cv.translate(NECK[0], NECK[1]); cv.rotate(tilt); cv.translate(-NECK[0], -NECK[1])
    draw_head(cv, C, turn, eye, eye_dx)
    cv.restore()
    # near arm
    el, wr = _arm_pts(arm)
    if layer == "body":
        dx, dy = wr[0] - el[0], wr[1] - el[1]; L = math.hypot(dx, dy) or 1
        hx, hy = wr[0] + dx / L * HAND_OFF, wr[1] + dy / L * HAND_OFF
    else:
        hx, hy = draw_arm(cv, C, el, wr, hand, finger_dir=finger_dir, finger_len=finger_len, phone=phone)
    inv = skia.Matrix()
    m0.invert(inv)
    m = skia.Matrix.Concat(inv, cv.getTotalMatrix())      # rig space -> caller's local space
    cv.restore()
    if alpha < 0.999: cv.restore()
    def to_screen(p): pt = m.mapXY(p[0], p[1]); return (pt.x(), pt.y())
    return {"hand": to_screen((hx, hy)), "wrist": to_screen(wr), "head": to_screen((545, 400)),
            "top": to_screen((529, 250)), "eye": to_screen((576, 392)), "mouth": to_screen((600, 452)),
            "shoulder": to_screen(SHOULDER), "belt": to_screen((520, 888)),
            "hand_far": to_screen(hf) if hf else None, "finger": to_screen((hx, hy - 76)) if True else None}

def to_ref(px, py, x, y, s, facing=1):
    """screen point -> reference-space point for a person drawn at (x, y, s, facing) (no lean)"""
    return (GROUND[0] + (px - x) / (s * facing), GROUND[1] + (py - y) / s)

def _arm_pts(spec):
    if spec is None: return REST_ELBOW, REST_WRIST
    if spec[0] == "fk": return arm_fk(spec[1], spec[2])
    if spec[0] == "ik": return arm_ik(spec[1], spec[2] if len(spec) > 2 else 1.0)
    if spec[0] == "pts": return spec[1], spec[2]
    if spec[0] == "hand":   # IK so that the fist centre lands on the target
        tgt = spec[1]; bend = spec[2] if len(spec) > 2 else 1.0; fs = spec[3] if len(spec) > 3 else 1.0; wr = tgt
        for _ in range(6):
            el, wr2 = arm_ik(wr, bend, fs=fs)
            dx, dy = wr2[0] - el[0], wr2[1] - el[1]; L = math.hypot(dx, dy) or 1
            wr = (tgt[0] - dx / L * HAND_OFF, tgt[1] - dy / L * HAND_OFF)
        return arm_ik(wr, bend, fs=fs)
    raise ValueError(spec)

def _ikat(cv, C, wind, ymax=1460):
    """diamond lattice: gold columns x=436+92k, light columns offset by 46 / 32 px"""
    for i in range(-2, 7):
        x = 436 + 46 * i
        cc = C["ikat_g"] if i % 2 == 0 else C["ikat_l"]
        y = 548 + 32 * i
        while y > 520: y -= 64
        while y < ymax:
            skip = (i == -1 and y < 1320) or (i == 4 and y < 700)
            if y > 500 and not (860 - 20 < y < 916 + 20) and not skip:
                k = clamp01((y - 880) / 570) ** 1.5
                diamond(cv, x + wind * 46 * k, y, 11, 17, cc)
            y += 64

def person_size(s): return HEIGHT * s

# ---------------------------------------------------------------- simple silhouette people (crowds)
def draw_guest(cv, x, y, s, c, t=0.0, kind="doppi", sway=0.0, seated=True):
    """flat silhouette of a seated guest (upper body above the table line); (x, y) = seat point"""
    with xf(cv, x, y, s, sway):
        spoly(cv, [(-58, 0), (-62, -120), (-44, -210), (0, -232), (44, -212), (60, -120), (58, 0)], c)
        circle(cv, 0, -290, 52, c)
        if kind == "doppi":
            poly(cv, [(-50, -318), (-40, -352), (0, -360), (40, -352), (50, -318)], c)
        elif kind == "scarf":
            spoly(cv, [(-60, -280), (-52, -340), (0, -362), (52, -340), (64, -260), (40, -210), (-40, -210)], c)
