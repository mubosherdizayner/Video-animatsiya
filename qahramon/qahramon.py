# Bosh qahramon (yashil chopon, Chust do'ppi) — minimalist siluet uslubi.
# Mustaqil fayl: faqat qahramon chiziladi, orqa fon yo'q. Muhit har bir videoda ssenariyga moslab alohida chiziladi.
#
#   python3 qahramon.py            -> qahramon_oq_fon.png, qahramon_shaffof.png, qahramon_holatlar.png
#
# Videoda ishlatish:  draw_hero(cv, X, Y, s, **poza)   (X, Y = oyoqlar orasidagi yer nuqtasi, s = 1.0 da bo'yi ~363 px)
#   yaw: 0 = yon tomondan (profil), 1 = oldidan 3/4;  dir: +1 o'ngga / -1 chapga qaraydi
#   walk, phase: yurish;  rarm=RA["stop"|"finger"|"point_down"|"chest"|"scratch"|...], rshape: "open"|"point"|"finger_up"|"flat"|"scratch"|"fist"
#   head_tilt, shake (bosh chayqash), bow (ta'zim, gradus), tray=True: patnis + kosa + sochiq (ofitsiant rekvizitlari)
import math, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def hx(s):
    s = s.lstrip("#"); return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))

# ---------------------------------------------------------------- palitra (videodagi bilan aynan bir xil)
SKIN, SKIN_D = hx("EBC8A2"), hx("D8B089")
HAIR = hx("2E231D")
CHAPAN, CHAPAN_D, CHAPAN_L = hx("3F7B61"), hx("2F634D"), hx("4C8A6E")
IKAT1, IKAT2 = hx("6FA586"), hx("C7A548")
GOLD = hx("BE8642"); BELT = hx("B4473B"); SHIRT = hx("E8E1D3")
DOPPI = hx("1D2427"); BOOT = hx("33241E")
TRAY = hx("2E3C40"); BOWL = hx("E8E1D3"); BOWL_BAND = hx("56696D"); CREAM = hx("F4EDDF")

# ---------------------------------------------------------------- yordamchi funksiyalar
def clamp01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def lerp(a, b, t): return a + (b - a) * t
def lerpc(c1, c2, t): return tuple(int(round(a + (b - a) * t)) for a, b in zip(c1, c2))
def ease_io(x): x = clamp01(x); return 3 * x * x - 2 * x * x * x
def rot(p, ang, c=(0, 0)):
    a = math.radians(ang); s, co = math.sin(a), math.cos(a)
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * co - y * s, c[1] + x * s + y * co)
def ellipse_pts(cx, cy, rx, ry, n=40, a0=0, a1=360, ang=0):
    pts = []
    for i in range(n + (0 if (a1 - a0) >= 360 else 1)):
        a = math.radians(a0 + (a1 - a0) * i / n)
        p = (cx + rx * math.cos(a), cy + ry * math.sin(a))
        pts.append(rot(p, ang, (cx, cy)) if ang else p)
    return pts
def capsule_pts(p0, p1, r0, r1=None, n=10):
    r1 = r0 if r1 is None else r1
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    a = math.atan2(dy, dx); pts = []
    for i in range(n + 1):
        t = a + math.pi / 2 + math.pi * i / n
        pts.append((p1[0] + r1 * math.cos(t - math.pi), p1[1] + r1 * math.sin(t - math.pi)))
    for i in range(n + 1):
        t = a + math.pi / 2 + math.pi * i / n
        pts.append((p0[0] + r0 * math.cos(t), p0[1] + r0 * math.sin(t)))
    return pts
def point_in_poly(x, y, poly):
    inside = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1): inside = not inside
    return inside
def dist_to_poly(x, y, poly):
    best = 1e9; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1; L2 = dx * dx + dy * dy or 1e-9
        t = clamp01(((x - x1) * dx + (y - y1) * dy) / L2)
        best = min(best, math.hypot(x - x1 - t * dx, y - y1 - t * dy))
    return best

class Canvas:
    """supersampled flat-shape canvas (no outlines); coords in output pixels"""
    def __init__(self, w, h, ss=3, bg=(255, 255, 255), rgba=False):
        self.w, self.h, self.ss, self.rgba, self.ez = w, h, ss, rgba, 1.0
        self.im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0)) if rgba else Image.new("RGB", (w * ss, h * ss), bg)
        self.d = ImageDraw.Draw(self.im, "RGBA")
    def T(self, x, y): return (x * self.ss, y * self.ss)
    def S(self, v): return v * self.ss
    def poly(self, pts, fill):
        if len(pts) >= 3: self.d.polygon([self.T(*p) for p in pts], fill=fill)
    def circle(self, cx, cy, r, fill):
        self.d.ellipse((*self.T(cx - r, cy - r), *self.T(cx + r, cy + r)), fill=fill)
    def line(self, pts, fill, w, caps=True):
        P = [self.T(*p) for p in pts]; ww = max(1, int(round(self.S(w))))
        self.d.line(P, fill=fill, width=ww, joint="curve")
        if caps:
            r = ww / 2
            for (x, y) in (P[0], P[-1]): self.d.ellipse((x - r, y - r, x + r, y + r), fill=fill)
    def capsule(self, p0, p1, r0, r1, fill): self.poly(capsule_pts(p0, p1, r0, r1), fill)
    def soft(self, bbox, draw_fn, blur=0.0, opacity=1.0, scale=0.5):
        x0, y0 = self.T(bbox[0], bbox[1]); x1, y1 = self.T(bbox[2], bbox[3])
        pad = blur * self.ss * 3 + 4; x0 -= pad; y0 -= pad; x1 += pad; y1 += pad
        k = scale; pw, ph = int((x1 - x0) * k) + 1, int((y1 - y0) * k) + 1
        patch = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); pd = ImageDraw.Draw(patch, "RGBA")
        def tf(x, y):
            a, b = self.T(x, y); return ((a - x0) * k, (b - y0) * k)
        draw_fn(pd, tf, self.ss * k)
        if blur > 0: patch = patch.filter(ImageFilter.GaussianBlur(blur * self.ss * k))
        if opacity < 0.999: patch.putalpha(patch.getchannel("A").point(lambda v: int(v * opacity)))
        patch = patch.resize((int(round(pw / k)), int(round(ph / k))), Image.BILINEAR)
        self.im.paste(patch, (int(x0), int(y0)), patch)
    def result(self):
        if self.rgba: return self.im.convert("RGBa").reduce(self.ss).convert("RGBA")
        return self.im.reduce(self.ss)

# ================================================================ QAHRAMON (videodagi kod, o'zgarishsiz)
LEG = 175.0
L_UP, L_FO = 88.0, 80.0

# profile (facing +x) / front (3/4 toward viewer) geometry, same point counts so they can be lerped
P_COAT = [(-14, -300), (-26, -294), (-31, -275), (-32, -240), (-31, -205), (-34, -150), (-38, -100), (-42, -66),
          (-20, -62), (10, -62), (41, -66), (36, -110), (32, -160), (31, -205), (32, -245), (28, -275), (18, -293), (8, -300)]
F_COAT = [(-12, -301), (-34, -294), (-40, -275), (-40, -240), (-39, -205), (-41, -150), (-44, -100), (-48, -66),
          (-20, -63), (10, -63), (49, -66), (45, -100), (42, -150), (40, -205), (41, -240), (41, -275), (35, -294), (13, -301)]
P_TRIM = [(8, -299), (22, -290), (30, -262), (31, -205), (33, -150), (37, -100), (40, -67)]
F_TRIM = [(-7, -300), (-3, -282), (2, -250), (6, -205), (6, -150), (7, -100), (8, -65)]
P_COLLAR = [(3, -307), (17, -298), (15, -287), (6, -292)]
F_COLLAR = [(-11, -303), (14, -303), (3, -283), (0, -283)]
P_DOPPI = [(-21, -336), (-20, -351), (-16, -360), (2, -363), (20, -360), (24, -351), (25, -336)]
F_DOPPI = [(-22, -335), (-21, -351), (-17, -360), (2, -363), (21, -360), (25, -351), (26, -335)]
P_BOOT = [(-9, -17), (6, -17), (13, -10), (21, -6), (22, 0), (-10, 0)]
F_BOOT = [(-10, -17), (9, -17), (11, -10), (12, -5), (12, 0), (-11, 0)]

def _lp(A, B, t): return [(lerp(a[0], b[0], t), lerp(a[1], b[1], t)) for a, b in zip(A, B)]
def _lv(a, b, t): return (lerp(a[0], b[0], t), lerp(a[1], b[1], t))

def ik(S, T, l1, l2, bend):
    dx, dy = T[0] - S[0], T[1] - S[1]
    d = max(abs(l1 - l2) + 1, min(l1 + l2 - 0.5, math.hypot(dx, dy)))
    a = math.atan2(dy, dx)
    b = math.acos(max(-1, min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    E = (S[0] + l1 * math.cos(a + bend * b), S[1] + l1 * math.sin(a + bend * b))
    Hh = (S[0] + d * math.cos(a), S[1] + d * math.sin(a))
    return E, Hh

def coat_edge_x(poly, y, side):
    xs = []
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 - y) * (y2 - y) <= 0 and y1 != y2:
            xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    if not xs: return 0
    return min(xs) if side < 0 else max(xs)

DEF = dict(yaw=0.0, dir=1, walk=0.0, phase=0.0, rarm=None, rshape="fist", rangle=90.0,
           head_tilt=0.0, shake=0.0, bow=0.0, steam_t=0.0, steam=True, tray=False, look=0.0, larm=None)
# tray=True gives the waiter props of the «Restoran» video (tray, kosa, steam, towel)

def draw_hero(cv, X, Y, s, **kw):
    P = dict(DEF); P.update(kw)
    yaw = clamp01(P["yaw"]); dr = P["dir"]
    th = math.radians(20) * P["walk"] * math.sin(P["phase"])
    hip_y = -LEG * math.cos(th)
    dy = LEG + hip_y                    # body bob (>0 = lower)
    bow = math.radians(P["bow"])
    pivot = (0.0, hip_y)

    def bend(p):
        x, y = p[0], p[1] + dy
        h = pivot[1] - y
        if bow <= 0 or h <= 0: return (x, y)
        a = bow * min(1.0, h / 45.0)
        rx, ry = rot((x, y), math.degrees(a), pivot)       # true rotation (profile)
        cx_, cy_ = x + h * math.sin(a) * 0.35, pivot[1] - h * math.cos(a) * 0.97  # compression (front)
        return (lerp(rx, cx_, yaw), lerp(ry, cy_, yaw))

    neck = bend((4, -300))
    ht = P["head_tilt"]
    def headp(p):
        q = bend(p)
        return rot(q, ht, neck) if ht else q

    def L(p):
        return (X + dr * p[0] * s, Y + p[1] * s)
    def Lp(pts): return [L(p) for p in pts]
    def S_(v): return v * s

    front = yaw >= 0.5

    # ---------------- arms geometry (explicit elbow/hand per pose, lerped; bend applied after)
    shR = _lv((2, -288), (-33, -286), yaw)
    shL = _lv((7, -288), (33, -286), yaw)
    if P["tray"]:
        eL0 = _lv((22, -206), (46, -210), yaw)
        handL = _lv((80, -240), (60, -236), yaw)
    elif P["larm"] is not None:
        eL0, handL = P["larm"]
    else:   # free left arm hangs (mirror of the right arm), swings opposite while walking
        swl = P["walk"] * 22 * math.sin(P["phase"])
        eL0 = _lv((0 + swl * 0.35, -205), (44, -208), yaw)
        handL = _lv((12 + swl, -144), (46, -140), yaw)
    tray_c = _lv((88, -248), (66, -247), yaw)
    if P["rarm"] is None:
        sw = P["walk"] * 22 * math.sin(P["phase"] + math.pi)
        rE = _lv((-4 + sw * 0.35, -205), (-44, -208), yaw)
        rT = _lv((10 + sw, -141), (-46, -140), yaw)
    else:
        rE, rT = P["rarm"]
    shR_b, shL_b = bend(shR), bend(shL)
    eR, hR = bend(rE), bend(rT)
    eL, hL = bend(eL0), bend(handL)
    tray_b = bend(tray_c)
    sleeve_far = lerpc(CHAPAN_D, CHAPAN_L, yaw)

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
            # ikat dots along forearm
            for k in (0.3, 0.62):
                q = (E[0] + (wr[0] - E[0]) * k, E[1] + (wr[1] - E[1]) * k)
                diamond(q, 3.0, 4.6, IKAT2 if k < 0.5 else IKAT1, ang=math.degrees(math.atan2(u[1], u[0])) - 90)
        if upper:
            q = ((Sh[0] + E[0]) / 2, (Sh[1] + E[1]) / 2)
            d = (E[0] - Sh[0], E[1] - Sh[1])
            diamond(q, 3.0, 4.6, IKAT1, ang=math.degrees(math.atan2(d[1], d[0])) - 90)

    def diamond(c, rx, ry, col, ang=0.0):
        pts = [(c[0], c[1] - ry), (c[0] + rx, c[1]), (c[0], c[1] + ry), (c[0] - rx, c[1])]
        if ang: pts = [rot(p, ang, c) for p in pts]
        cv.poly(Lp(pts), col)

    # ---------------- far upper arm (profile: behind body)
    if not front:
        sleeve(shL_b, eL, hL, sleeve_far, upper=True, fore=not P["tray"])
        if not P["tray"]: cv.poly(Lp(ellipse_pts(hL[0], hL[1], 8.5, 7.5, 14)), SKIN)

    # ---------------- legs
    legs = []
    for k, (hxp, hxf) in enumerate(((-3, 13), (3, -13))):
        ang = th if k == 0 else -th
        hx_ = lerp(hxp, hxf, yaw)
        Hh = (hx_, hip_y)
        F = (hx_ + LEG * math.sin(ang) * (1 - yaw), 0.0)
        legs.append((Hh, F, k))
    # far leg first (profile: k=0 is far)
    for Hh, F, k in sorted(legs, key=lambda q: q[2]):
        col = BOOT if (k == 1 or front) else lerpc(BOOT, (22, 15, 12), 0.35)
        cv.capsule(L(Hh), L((F[0], F[1] - 10)), S_(9.5), S_(9.0), col)
        bt = _lp(P_BOOT, F_BOOT, yaw)
        if front and k == 1: bt = [(-x, y) for x, y in bt]
        cv.poly(Lp([(F[0] + x, F[1] + y) for x, y in bt]), col)

    # ---------------- coat
    flutter = P["walk"] * 3.5
    coat = []
    for (x, y) in _lp(P_COAT, F_COAT, yaw):
        if y > -150: x += flutter * math.sin(P["phase"] * 2 + 1.0) * ((y + 150) / 85.0)
        coat.append(bend((x, y)))
    cv.poly(Lp(coat), CHAPAN)
    # shaded side strip (away from the sun)
    back = coat[1:8]
    inner = [(x + lerp(13, 10, yaw), y) for x, y in back][::-1]
    cv.poly(Lp(back + inner), CHAPAN_D)
    # ikat diamonds
    for ci in range(9):
        cx0 = -44 + 11.5 * ci
        for ri in range(14):
            y0 = -288 + 16 * ri + (8 if ci % 2 else 0)
            if -214 < y0 < -186: continue
            p = bend((cx0 + (flutter * math.sin(P["phase"] * 2 + 1.0) * ((y0 + 150) / 85.0) if y0 > -150 else 0), y0))
            if point_in_poly(p[0], p[1], coat) and dist_to_poly(p[0], p[1], coat) > 5.5:
                diamond(p, 2.7, 4.3, IKAT2 if ci % 2 == 0 else IKAT1)
    # trims
    trim = [bend(p) for p in _lp(P_TRIM, F_TRIM, yaw)]
    cv.line(Lp(trim), GOLD, S_(3.6))
    hem = coat[7:11]
    cv.line(Lp([(x, y - 2) for x, y in hem]), GOLD, S_(4.2))
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
    neck_pts = [headp(p) for p in [(lerp(-3, -6, yaw), -314), (lerp(10, 8, yaw), -314), (lerp(10, 8, yaw), -296), (lerp(-3, -6, yaw), -296)]]
    cv.poly(Lp(neck_pts), SKIN_D)
    cv.poly(Lp([bend(p) for p in _lp(P_COLLAR, F_COLLAR, yaw)]), SHIRT)
    sh = P["shake"]
    hc = headp((lerp(6, 3, yaw) + sh * 2.0, -323))
    face = [headp((lerp(6, 3, yaw) + sh * 2.0 + lerp(16.5, 18, yaw) * math.cos(a), -323 + 20.5 * math.sin(a)))
            for a in [i * 2 * math.pi / 36 for i in range(36)]]
    cv.poly(Lp(face), SKIN)
    if not front:
        nose = [headp(p) for p in [(20, -329), (26.5, -318), (21, -313)]]
        cv.poly(Lp(nose), SKIN)
        hair = [headp(p) for p in [(-13, -339), (-5, -339), (-3, -329), (-5, -315), (-11, -308), (-17.5, -316), (-18, -330)]]
        cv.poly(Lp(hair), HAIR)
        ear = [headp((-1 + 3.2 * math.cos(a), -322 + 4.8 * math.sin(a))) for a in [i * 2 * math.pi / 12 for i in range(12)]]
        cv.poly(Lp(ear), SKIN_D)
        ey = headp((14 + P["look"] * 1.5, -327))
        cv.poly(Lp(ellipse_pts(ey[0], ey[1], 2.2, 2.5, 10)), (25, 22, 20))
    else:
        for side in (-1, 1):
            if side < 0: hp_ = [(-19.5, -339), (-11, -339), (-14, -330), (-19, -326)]
            else: hp_ = [(22, -339), (25.5, -339), (24.5, -329), (21, -331)]
            cv.poly(Lp([headp((x + sh * 2.0, y)) for x, y in hp_]), HAIR)
        for ex, r in ((-4.5, 2.1), (9.5, 2.0)):
            ey = headp((ex + sh * 6.0 + P["look"] * 2, -325))
            cv.poly(Lp(ellipse_pts(ey[0], ey[1], r, r * 1.15, 10)), (25, 22, 20))
    # doppi
    dp = [headp((x + sh * 1.5, y)) for x, y in _lp(P_DOPPI, F_DOPPI, yaw)]
    cv.poly(Lp(dp), DOPPI)
    cv.line(Lp([headp((-20.5 + sh * 1.5, -337.8)), headp((2 + sh * 1.5, -338.3)), headp((25 + sh * 1.5, -337.8))]), SHIRT, S_(2.8))
    for mx_, my_ in ((-12, -348), (0, -350), (12, -350), (22, -348)):
        if mx_ > 20 and not front: continue
        c = headp((mx_ + sh * 1.5 + (2 if front else -1), my_))
        pts = ellipse_pts(c[0], c[1], 1.9, 4.0, 10, ang=-28 + ht)
        cv.poly(Lp(pts), SHIRT)
        cv.poly(Lp(ellipse_pts(c[0] + 0.9, c[1] - 3.4, 1.0, 1.0, 6)), SHIRT)

    # ---------------- left arm (tray), towel
    if not P["tray"]:
        if front:
            sleeve(shL_b, eL, hL, CHAPAN_L, upper=True, fore=True)
            cv.poly(Lp(ellipse_pts(hL[0], hL[1], 8.5, 8.0, 14)), SKIN)
    elif front:
        sleeve(shL_b, eL, hL, CHAPAN_L, upper=True, fore=True)
    else:
        sleeve(shL_b, eL, hL, sleeve_far, upper=False, fore=True)
    if P["tray"]: cv.poly(Lp(ellipse_pts(hL[0], hL[1], 8.5, 7.5, 14)), SKIN)
    # towel draped over the forearm
    if not P["tray"]:
        sleeve(shR_b, eR, hR, CHAPAN_L, upper=True, fore=True)
        draw_hand(cv, Lp, hR, eR, P["rshape"], P["rangle"], front, dr)
        return dict(head=L(hc), hand=L(hR))
    ax, ay = eL[0] + (hL[0] - eL[0]) * 0.22, eL[1] + (hL[1] - eL[1]) * 0.22
    bx, by = eL[0] + (hL[0] - eL[0]) * 0.72, eL[1] + (hL[1] - eL[1]) * 0.72
    sway = math.sin(P["phase"] * 2) * P["walk"] * 2.5
    tw = [(ax - 2, ay - 8), (bx + 2, by - 8), (bx + 4, by + 6), (bx + 2 + sway, by + 44), (bx - 6 + sway, by + 50),
          ((ax + bx) / 2 + sway, max(ay, by) + 46), (ax + 2 + sway, ay + 52), (ax - 5 + sway, ay + 44), (ax - 4, ay + 4)]
    cv.poly(Lp(tw), SHIRT)
    cv.line(Lp([((ax + bx) / 2 + 1, max(ay, by) + 4), ((ax + bx) / 2 + 2 + sway, max(ay, by) + 44)]), (206, 198, 184), S_(1.8))
    cv.line(Lp([(ax - 2, ay - 8), (bx + 2, by - 8)]), CHAPAN_L if front else sleeve_far, S_(5))

    # ---------------- tray + kosa + steam
    if P["tray"]:
        tc = tray_b
        ry = lerp(8.0, 12.0, yaw)
        cv.poly(Lp(ellipse_pts(tc[0], tc[1] + 3.5, 49, ry, 36)), (34, 45, 49))
        cv.poly(Lp(ellipse_pts(tc[0], tc[1], 49, ry, 36)), GOLD)
        cv.poly(Lp(ellipse_pts(tc[0], tc[1] - 0.6, 45, ry - 2.6, 36)), TRAY)
        draw_kosa_local(cv, Lp, tc[0], tc[1] - ry * 0.25, 1.0)
        if P["steam"]:
            draw_steam(cv, L, tc[0], tc[1] - ry * 0.25 - 26, s, P["steam_t"], scale=1.0, dirx=dr)

    # ---------------- right (free) arm
    sleeve(shR_b, eR, hR, CHAPAN_L, upper=True, fore=True)
    draw_hand(cv, Lp, hR, eR, P["rshape"], P["rangle"], front, dr)
    return dict(tray=L(tray_b), bowl_top=L((tray_b[0], tray_b[1] - 26)), head=L(hc), hand=L(hR))

# right-arm poses: (elbow, hand) in local coords
RA = {
    "hang_p": ((-4, -205), (10, -141)),
    "hang_f": ((-44, -208), (-46, -140)),
    "stop": ((-74, -238), (-64, -320)),
    "finger": ((-70, -240), (-56, -306)),
    "point_down": ((-78, -224), (-104, -170)),
    "chest": ((-48, -214), (-6, -254)),
    "scratch": ((-74, -292), (-27, -352)),
    "door": ((34, -228), (100, -214)),
    "point_up_p": ((42, -300), (96, -344)),
    "present_f": ((-62, -214), (-96, -246)),
}
def arm_mix(a, b, t):
    A = RA[a] if isinstance(a, str) else a; B = RA[b] if isinstance(b, str) else b
    t = ease_io(t)
    return (_lv(A[0], B[0], t), _lv(A[1], B[1], t))

def draw_hand(cv, Lp, h, e, shape, ang, front, dr):
    hx_, hy_ = h
    if shape == "open":
        # palm toward viewer, fingers up
        cv.poly(Lp(ellipse_pts(hx_, hy_, 8.2, 9.0, 16)), SKIN)
        for k, (dx, ln) in enumerate(((-5.2, 10.5), (-1.7, 12.5), (1.8, 12.5), (5.2, 10.0))):
            cv.capsule(Lp([(hx_ + dx, hy_ - 4)])[0], Lp([(hx_ + dx * 1.15, hy_ - 4 - ln)])[0], 2.6 * _sc(Lp), 2.4 * _sc(Lp), SKIN)
        cv.capsule(Lp([(hx_ + 6, hy_ + 2)])[0], Lp([(hx_ + 13, hy_ - 5)])[0], 2.8 * _sc(Lp), 2.6 * _sc(Lp), SKIN)
        cv.line(Lp([(hx_ - 3, hy_ + 2), (hx_ + 3, hy_ + 3)]), SKIN_D, 1.2 * _sc(Lp))
    elif shape in ("point", "finger_up"):
        a = math.radians(-90 if shape == "finger_up" else ang)
        cv.poly(Lp(ellipse_pts(hx_, hy_, 8.5, 8.0, 14)), SKIN)
        tip = (hx_ + 17 * math.cos(a), hy_ + 17 * math.sin(a))
        base = (hx_ + 4 * math.cos(a), hy_ + 4 * math.sin(a))
        cv.capsule(Lp([base])[0], Lp([tip])[0], 2.9 * _sc(Lp), 2.6 * _sc(Lp), SKIN)
        cv.line(Lp([(hx_ - 4, hy_ + 1), (hx_ + 3, hy_ + 3)]), SKIN_D, 1.2 * _sc(Lp))
    elif shape == "flat":
        cv.poly(Lp(ellipse_pts(hx_, hy_, 11, 7, 16, ang=-15)), SKIN)
        cv.capsule(Lp([(hx_ - 3, hy_ - 4)])[0], Lp([(hx_ - 9, hy_ - 10)])[0], 2.6 * _sc(Lp), 2.4 * _sc(Lp), SKIN)
    elif shape == "scratch":
        cv.poly(Lp(ellipse_pts(hx_, hy_, 8.5, 8.0, 14)), SKIN)
        for dx in (-4, 0, 4):
            cv.circle(*Lp([(hx_ + dx, hy_ - 8)])[0], 2.6 * _sc(Lp), SKIN)
    else:
        cv.poly(Lp(ellipse_pts(hx_, hy_, 8.5, 8.0, 14)), SKIN)

def _sc(Lp):
    a = Lp([(0, 0), (1, 0)]); return abs(a[1][0] - a[0][0])

def draw_kosa_local(cv, Lp, cx, base_y, k):
    """bowl standing on base_y (local coords), k = size factor"""
    rim_y = base_y - 25 * k
    pts_l, pts_r = [], []
    for i in range(13):
        v = i / 12
        hw = max(9.5 * k, 22.5 * k * math.sqrt(max(0, 1 - v * v)))
        y = rim_y + v * 21 * k
        pts_l.append((cx - hw, y)); pts_r.append((cx + hw, y))
    body = pts_l + [(cx - 9.5 * k, base_y), (cx + 9.5 * k, base_y)] + pts_r[::-1]
    cv.poly(Lp(body), BOWL)
    # shade on the left side
    sh = pts_l + [(cx - 9.5 * k, base_y), (cx - 4 * k, base_y)] + [(x + 7 * k * (1 - abs(i - 6) / 12), y) for i, (x, y) in enumerate(pts_l)][::-1]
    cv.poly(Lp(sh), (214, 206, 190))
    # pattern band
    b0, b1 = 2, 4
    band = pts_l[b0:b1 + 1] + pts_r[b0:b1 + 1][::-1]
    cv.poly(Lp(band), BOWL_BAND)
    for j in range(5):
        bx = cx - 15 * k + j * 7.5 * k
        cv.poly(Lp(ellipse_pts(bx, rim_y + 6.3 * k, 1.3 * k, 1.3 * k, 6)), BOWL)
    # rim + broth
    cv.poly(Lp(ellipse_pts(cx, rim_y, 22.5 * k, 4.2 * k, 28)), BOWL)
    cv.poly(Lp(ellipse_pts(cx, rim_y + 0.6 * k, 19.5 * k, 2.8 * k, 28)), (201, 176, 132))

STEAM_P = None   # when set, wisp frequencies snap to multiples of 2*pi/STEAM_P (seamless loop)
def _q(f):
    if not STEAM_P: return f
    b = 2 * math.pi / STEAM_P
    return max(1, round(f / b)) * b

def draw_steam(cv, L, cx, top_y, s, t, scale=1.0, dirx=1, opacity=0.6, n=3, height=70):
    """three soft rising wisps; L maps local->world"""
    f1, f2, f3 = _q(2.6), _q(0.55 * 2 * math.pi) / (2 * math.pi), _q(3.0)
    base = [L((cx + dx * scale, top_y)) for dx in (-8, 0, 8)][:n]
    wx = [b[0] for b in base]; wy = base[0][1]
    span = height * scale * s
    bbox = (min(wx) - 30 * s * scale, wy - span - 20 * s, max(wx) + 30 * s * scale, wy + 6 * s)
    def fn(d, tf, k):
        for i, (bx, by) in enumerate(base):
            ph = t * 2.6 + i * 2.1
            prev = None
            for j in range(16):
                u = j / 15
                cyc = (u + (t * f2 + i * 0.33)) % 1.0
                y = by - u * span
                x = bx + (5 * s * scale) * math.sin(u * 5.2 - t * f3 + i * 1.7) * (0.3 + u)
                p = tf(x, y)
                if prev is not None:
                    a = int(255 * math.sin(math.pi * min(1, u * 1.15)) ** 1.2 * (0.55 + 0.45 * math.sin(cyc * 6.28 + i)))
                    d.line([prev, p], fill=CREAM + (max(0, a),), width=max(1, int(k * (5.5 - 3 * u) * scale)))
                prev = p
    cv.soft(bbox, fn, blur=1.4 * scale, opacity=opacity, scale=0.5)

# ================================================================ rasmlar
FONT = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
def _font(size):
    for f in (FONT, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(f): return ImageFont.truetype(f, size)
    return ImageFont.load_default()

def single(out_png, transparent=False):
    W, H = 1080, 1920
    cv = Canvas(W, H, ss=3, rgba=transparent)
    draw_hero(cv, 520, 1700, 4.0)                        # yon tomondan, tik turgan (asl kadrdagidek)
    img = cv.result(); img.save(out_png); return img

POSES = [
    ("Yon tomondan", dict()),
    ("Oldidan (3/4)", dict(yaw=1.0)),
    ("Yurish", dict(walk=1.0, phase=1.3)),
    ("Salom / toʻxtang", dict(yaw=1.0, rarm=None, rshape="open", _arm="stop")),
    ("Taʼzim", dict(yaw=1.0, rshape="flat", bow=16, _arm="chest")),
]
SWATCHES = [("Chopon", CHAPAN), ("Soya", CHAPAN_D), ("Och", CHAPAN_L), ("Ikat", IKAT1), ("Ikat", IKAT2), ("Jiyak", GOLD),
            ("Belbogʻ", BELT), ("Yoqa", SHIRT), ("Doʻppi", DOPPI), ("Teri", SKIN), ("Soch", HAIR), ("Etik", BOOT)]

def sheet(out_png):
    W, H = 2200, 1240
    cv = Canvas(W, H, ss=3)
    s = 2.2; base = 930
    for i, (name, kw) in enumerate(POSES):
        kw = dict(kw); arm = kw.pop("_arm", None)
        if arm: kw["rarm"] = RA[arm]
        draw_hero(cv, 240 + i * 430, base, s, **kw)
    img = cv.result(); d = ImageDraw.Draw(img)
    f = _font(38); fs = _font(24)
    for i, (name, _) in enumerate(POSES):
        d.text((240 + i * 430, base + 52), name, font=f, fill=(46, 60, 64), anchor="mm")
    sw = 150; x0 = (W - sw * len(SWATCHES)) // 2
    for j, (nm, c) in enumerate(SWATCHES):
        x = x0 + j * sw
        d.rounded_rectangle((x + 14, 1060, x + sw - 14, 1130), radius=14, fill=c, outline=(215, 215, 215) if sum(c) > 600 else None, width=2)
        d.text((x + sw / 2, 1152), nm, font=fs, fill=(46, 60, 64), anchor="mm")
        d.text((x + sw / 2, 1182), "#%02X%02X%02X" % c, font=fs, fill=(110, 120, 122), anchor="mm")
    img.save(out_png); return img

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    single(os.path.join(here, "qahramon_oq_fon.png"))
    single(os.path.join(here, "qahramon_shaffof.png"), transparent=True)
    sheet(os.path.join(here, "qahramon_holatlar.png"))
    print("ok")
