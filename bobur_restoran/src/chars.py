# Code-drawn rigged chibi characters in the sheet style: waiter (x3 variants), chef, cashier.
# Built from parts (legs, torso, arms with 2-bone IK, head, brows, eyes, mouth, props) so they can blink,
# talk and move their arms. Everything is drawn in local coords: origin at the feet centre, y up negative,
# H = standing height. The finished figure gets the same white sticker outline as the sheet sprites.
import math, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from lib import *

SHIRT = (250, 250, 247)
SHIRT_D = (222, 226, 230)
BLACK_V = (38, 36, 40)
TROUSER = (36, 36, 42)
SHOE = (26, 24, 26)
HAIR_BLACK = (34, 26, 24)
HAIR_BROWN = (110, 66, 38)
MOUTH_IN = (122, 30, 40)
TONGUE = (232, 110, 120)
BOW_RED = (206, 38, 44)
CHEF_W = (252, 252, 250)
CHEF_SH = (226, 230, 236)
CHECK_G = (120, 124, 132)
CHECK_L = (160, 164, 172)
BLOUSE = (252, 250, 248)
SKIRT = (40, 38, 54)
FOLDER = (150, 92, 48)

class Canvas:
    """SS canvas in character-local coordinates (origin at feet, units = px at standing height H)."""
    def __init__(self, H, ss=2, left=0.8, top=1.36, right=0.8, bottom=0.12):
        self.H = H
        self.ox, self.oy = left * H, top * H
        self.c = SS((left + right) * H, (top + bottom) * H, ss)
        self.ol = max(2.0, 0.0085 * H * 1.05)
    def T(self, pts): return [(x + self.ox, y + self.oy) for x, y in pts]
    def poly(self, pts, fill, outline=OL, width=None):
        self.c.poly(self.T(pts), fill=fill, outline=outline, width=self.ol if width is None else width)
    def ellipse(self, cx, cy, rx, ry, fill, outline=OL, width=None):
        self.c.ellipse((cx - rx + self.ox, cy - ry + self.oy, cx + rx + self.ox, cy + ry + self.oy), fill=fill,
                       outline=outline, width=self.ol if width is None else width)
    def circle(self, cx, cy, r, fill, outline=OL, width=None): self.ellipse(cx, cy, r, r, fill, outline, width)
    def line(self, pts, fill=OL, width=None):
        self.c.line(self.T(pts), fill=fill, width=self.ol if width is None else width)
    def tube(self, pts, w, fill):
        self.c.line(self.T(pts), fill=OL, width=w + 2 * self.ol)
        self.c.line(self.T(pts), fill=fill, width=w)
    def rect(self, x0, y0, x1, y1, fill, r=0, outline=OL, width=None):
        self.c.rect((x0 + self.ox, y0 + self.oy, x1 + self.ox, y1 + self.oy), fill=fill, outline=outline,
                    width=self.ol if width is None else width, r=r)
    def arc(self, cx, cy, rx, ry, a0, a1, fill=OL, width=None):
        self.c.arc((cx - rx + self.ox, cy - ry + self.oy, cx + rx + self.ox, cy + ry + self.oy), a0, a1, fill=fill,
                   width=self.ol if width is None else width)
    def paste(self, img, x, y): self.c.paste(img, x + self.ox, y + self.oy)
    def result(self): return self.c.result()

def ellipse_pts(cx, cy, rx, ry, n=40, a0=0, a1=360):
    return [(cx + rx * math.cos(math.radians(a)), cy + ry * math.sin(math.radians(a))) for a in np.linspace(a0, a1, n)]

def head_pts(hx, hy, a, b, n=64):
    """rounded-square chibi head (superellipse), chin slightly narrower"""
    pts = []
    for k in range(n):
        th = 2 * math.pi * k / n
        c, s = math.cos(th), math.sin(th)
        e = 2.0 / 2.5
        x = a * math.copysign(abs(c) ** e, c); y = b * math.copysign(abs(s) ** e, s)
        if y > 0: x *= 1 - 0.13 * (y / b) ** 2
        pts.append((hx + x, hy + y))
    return pts

def ik(sx, sy, tx, ty, l1, l2, bend=1):
    """2-bone IK: shoulder (sx,sy) -> target; returns elbow, hand (clamped to reach)"""
    dx, dy = tx - sx, ty - sy
    d = math.hypot(dx, dy)
    d = max(1e-3, min(d, (l1 + l2) * 0.999))
    a = math.atan2(dy, dx)
    cosb = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    b = math.acos(max(-1, min(1, cosb)))
    ea = a + bend * b
    ex, ey = sx + l1 * math.cos(ea), sy + l1 * math.sin(ea)
    hx, hy = sx + d * math.cos(a), sy + d * math.sin(a)
    return (ex, ey), (hx, hy)

# ---------------------------------------------------------------- face
def draw_face(cv, hx, hy, H, F, look):
    """F keys: dx (head turn), dy, blink 0..1, gaze (gx,gy), eyes ('normal','sparkle','half','down'),
    brows ('neutral','sad','up','angry','down'), mouth ('smile','open','o','quiver','flat','grin'), mo (open amount),
    t (time for quiver)"""
    fdx = F.get("dx", 0.0) * H; fdy = F.get("dy", 0.0) * H
    ex0 = 0.074 * H; ey = hy - 0.004 * H + fdy
    er = 0.051 * H
    blink = F.get("blink", 0.0)
    eyes = F.get("eyes", "normal")
    gx, gy = F.get("gaze", (0.0, 0.0))
    if look.get("cheeks", True):
        for sgn in (-1, 1):
            cv.ellipse(hx + fdx * 1.05 + sgn * 0.112 * H, hy + 0.066 * H + fdy, 0.031 * H, 0.02 * H, BLUSH, outline=None, width=0)
    for sgn in (-1, 1):
        ex = hx + fdx + sgn * ex0 * (1 - 0.25 * abs(F.get("dx", 0)) / 0.05 * (1 if sgn * F.get("dx", 0) < 0 else 0) if F.get("dx", 0) else 1)
        if blink > 0.6 or eyes == "closed":
            cv.arc(ex, ey + er * 0.1, er * 0.85, er * 0.55, 15, 165, width=cv.ol * 1.1)
            continue
        cv.circle(ex, ey, er, (255, 255, 255))
        pr = er * (0.64 if eyes == "sparkle" else 0.55)
        px, py = ex + gx * er * 0.42, ey + gy * er * 0.42
        if eyes == "down": py = ey + er * 0.35
        cv.circle(px, py, pr, (18, 14, 14), outline=None, width=0)
        cv.circle(px - pr * 0.36, py - pr * 0.4, pr * 0.34, (255, 255, 255), outline=None, width=0)
        if eyes == "sparkle":
            cv.circle(px + pr * 0.35, py + pr * 0.32, pr * 0.17, (255, 255, 255), outline=None, width=0)
            cv.circle(px + pr * 0.42, py - pr * 0.35, pr * 0.11, (255, 255, 255), outline=None, width=0)
        lid = blink if blink > 0 else 0.0
        if eyes in ("half", "down"): lid = max(lid, 0.5)
        if lid > 0.02:   # upper eyelid (skin) closing over the eye
            yy = ey - er + 2 * er * lid
            pts = ellipse_pts(ex, ey, er, er, 30, 180, 360)
            pts = [(x, min(y, yy)) for x, y in pts]
            cv.poly(pts + [(ex + er, yy), (ex - er, yy)], look["skin"], outline=None, width=0)
            cv.circle(ex, ey, er, None)
            cv.line([(ex - er * math.sqrt(max(0, 1 - ((yy - ey) / er) ** 2)), yy), (ex + er * math.sqrt(max(0, 1 - ((yy - ey) / er) ** 2)), yy)], width=cv.ol)
    # brows
    brows = F.get("brows", "neutral")
    bw = 0.017 * H
    for sgn in (-1, 1):
        ex = hx + fdx + sgn * ex0
        by = ey - er - 0.026 * H
        inner = (ex - sgn * 0.034 * H, by); outer = (ex + sgn * 0.038 * H, by)
        mid = (ex, by - 0.012 * H)
        if brows == "sad": inner = (inner[0], by - 0.024 * H); outer = (outer[0], by + 0.008 * H); mid = (ex, by - 0.01 * H)
        elif brows == "up": inner = (inner[0], by - 0.02 * H); outer = (outer[0], by - 0.014 * H); mid = (ex, by - 0.034 * H)
        elif brows == "angry": inner = (inner[0], by + 0.016 * H); outer = (outer[0], by - 0.014 * H); mid = (ex, by - 0.004 * H)
        elif brows == "down": inner = (inner[0], by + 0.01 * H); outer = (outer[0], by + 0.004 * H); mid = (ex, by + 0.0 * H)
        cv.line([inner, mid, outer], fill=look.get("brow", HAIR_BLACK), width=bw)
    # nose
    nx, ny = hx + fdx * 1.15, hy + 0.04 * H + fdy
    cv.arc(nx, ny, 0.016 * H, 0.012 * H, 20, 160, width=cv.ol * 0.85)
    if look.get("moustache"):
        mc = look["moustache"]
        pts = [(nx - 0.055 * H, ny + 0.035 * H), (nx - 0.03 * H, ny + 0.012 * H), (nx, ny + 0.02 * H), (nx + 0.03 * H, ny + 0.012 * H),
               (nx + 0.055 * H, ny + 0.035 * H), (nx + 0.02 * H, ny + 0.032 * H), (nx, ny + 0.036 * H), (nx - 0.02 * H, ny + 0.032 * H)]
        cv.poly(pts, mc, outline=OL, width=cv.ol * 0.7)
    # mouth
    mx, my = hx + fdx * 1.15, hy + 0.098 * H + fdy
    m = F.get("mouth", "smile"); mo = F.get("mo", 0.0)
    if mo > 0.05 or m in ("open", "o", "grin"):
        k = max(mo, 0.35 if m in ("open", "grin") else 0.25)
        if m == "o":
            rx, ry = 0.022 * H * (0.8 + 0.4 * k), 0.026 * H * (0.6 + 0.8 * k)
            cv.ellipse(mx, my, rx, ry, MOUTH_IN)
        else:
            rx = 0.04 * H; ry = 0.034 * H * k
            pts = [(mx - rx, my - ry * 0.25)] + [(mx + rx * math.cos(a), my - ry * 0.25 + ry * 1.25 * math.sin(a)) for a in np.linspace(0, math.pi, 18)][::-1][1:-1][::-1]
            pts = [(mx - rx, my - ry * 0.25), (mx + rx, my - ry * 0.25)] + [(mx + rx * math.cos(a), my - ry * 0.25 + ry * 1.25 * math.sin(a)) for a in np.linspace(0, math.pi, 18)]
            cv.poly(pts, MOUTH_IN)
            if k > 0.3:
                cv.ellipse(mx, my + ry * 0.62, rx * 0.5, ry * 0.32, TONGUE, outline=None, width=0)
                cv.poly(pts, None)
    elif m == "quiver":
        t = F.get("t", 0.0)
        pts = [(mx - 0.036 * H + 0.072 * H * q, my + 0.006 * H + 0.007 * H * math.sin(q * 9 + t * 40) - 0.012 * H * math.sin(math.pi * q)) for q in np.linspace(0, 1, 14)]
        cv.line(pts, width=cv.ol * 1.05)
    elif m == "flat":
        cv.line([(mx - 0.025 * H, my), (mx + 0.025 * H, my)], width=cv.ol)
    elif m == "sad":
        cv.arc(mx, my + 0.02 * H, 0.03 * H, 0.016 * H, 200, 340, width=cv.ol)
    else:
        cv.arc(mx, my - 0.012 * H, 0.036 * H, 0.022 * H, 25, 155, width=cv.ol * 1.05)

def draw_head(cv, H, hx, hy, look, F):
    a, b = 0.192 * H, 0.18 * H
    sk = look["skin"]
    fdx = F.get("dx", 0.0) * H
    # ears (the far ear hides when the head turns)
    for sgn in (-1, 1):
        hide = F.get("dx", 0.0) * sgn < -0.02
        if hide: continue
        exx = hx + sgn * (a * 0.98) + fdx * 0.2
        cv.ellipse(exx, hy + 0.012 * H, 0.032 * H, 0.043 * H, sk)
        cv.arc(exx - sgn * 0.004 * H, hy + 0.012 * H, 0.016 * H, 0.024 * H, 90 - sgn * 70, 270 - sgn * 70 if sgn > 0 else 270 + 70, width=cv.ol * 0.6)
    hair = look.get("hair", "short")
    hc = look.get("hair_col", HAIR_BLACK)
    if hair == "bun":
        cv.circle(hx + 0.01 * H, hy - b * 1.12, 0.07 * H, hc)
        cv.arc(hx + 0.01 * H, hy - b * 1.12, 0.045 * H, 0.04 * H, 200, 330, fill=(80, 64, 60), width=cv.ol * 0.6)
    if hair == "curly":
        for k in range(9):
            ang = math.radians(195 + k * 18.5)
            cv.circle(hx + a * 0.95 * math.cos(ang), hy + b * 0.9 * math.sin(ang) - 0.01 * H, 0.05 * H, hc)
    cv.poly(head_pts(hx, hy, a, b), sk)
    # hair cap
    if hair in ("short", "side", "bun", "curly", "chef"):
        top = [(hx + a * 1.02 * math.cos(math.radians(t)), hy + b * 1.03 * math.sin(math.radians(t))) for t in np.linspace(186, 354, 24)]
        if hair == "short":
            fr = [(hx + a * 0.98, hy - b * 0.35), (hx + a * 0.62, hy - b * 0.52), (hx + a * 0.45, hy - b * 0.4), (hx + a * 0.22, hy - b * 0.6),
                  (hx + 0.0, hy - b * 0.45), (hx - a * 0.25, hy - b * 0.62), (hx - a * 0.45, hy - b * 0.46), (hx - a * 0.7, hy - b * 0.58), (hx - a * 0.98, hy - b * 0.3)]
            spikes = [(hx - a * 0.4, hy - b * 1.12), (hx - a * 0.1, hy - b * 1.2), (hx + a * 0.25, hy - b * 1.16)]
            cv.poly(top + fr, hc)
            for sx_, sy_ in spikes:
                cv.poly([(sx_ - 0.04 * H, hy - b * 0.95), (sx_, sy_), (sx_ + 0.045 * H, hy - b * 0.96)], hc)
            cv.poly(top + fr, hc, outline=None, width=0)
        elif hair == "side":
            fr = [(hx + a * 0.99, hy - b * 0.25), (hx + a * 0.8, hy - b * 0.5), (hx + a * 0.2, hy - b * 0.58), (hx - a * 0.3, hy - b * 0.82),
                  (hx - a * 0.55, hy - b * 0.5), (hx - a * 0.85, hy - b * 0.42), (hx - a * 0.99, hy - b * 0.2)]
            cv.poly(top + fr, hc)
            cv.line([(hx - a * 0.32, hy - b * 1.0), (hx - a * 0.36, hy - b * 0.8)], fill=(80, 70, 70), width=cv.ol * 0.7)
            cv.arc(hx + a * 0.25, hy - b * 0.72, a * 0.5, b * 0.3, 190, 320, fill=(70, 60, 60), width=cv.ol * 0.6)
        elif hair == "curly":
            fr = [(hx + a * 0.99, hy - b * 0.3)] + [(hx + a * (0.75 - 0.3 * k), hy - b * (0.5 + 0.12 * (k % 2))) for k in range(6)] + [(hx - a * 0.99, hy - b * 0.3)]
            cv.poly(top + fr, hc)
            for k in range(5):
                cv.arc(hx - a * 0.6 + k * a * 0.3, hy - b * 0.75, 0.03 * H, 0.03 * H, 200, 340, fill=(80, 46, 26), width=cv.ol * 0.6)
        elif hair == "bun":
            fr = [(hx + a * 1.0, hy - b * 0.05), (hx + a * 0.85, hy - b * 0.45), (hx + a * 0.3, hy - b * 0.62), (hx, hy - b * 0.55),
                  (hx - a * 0.35, hy - b * 0.64), (hx - a * 0.85, hy - b * 0.45), (hx - a * 1.0, hy - b * 0.05)]
            cv.poly(top + fr, hc)
            cv.line([(hx, hy - b * 1.0), (hx, hy - b * 0.58)], fill=(70, 56, 52), width=cv.ol * 0.6)
        elif hair == "chef":
            for sgn in (-1, 1):
                cv.poly([(hx + sgn * a * 1.0, hy - b * 0.1), (hx + sgn * a * 0.98, hy - b * 0.6), (hx + sgn * a * 0.7, hy - b * 0.6), (hx + sgn * a * 0.8, hy - b * 0.2)], hc)
    draw_face(cv, hx, hy, H, F, look)
    if look.get("glasses"):
        fdy = F.get("dy", 0.0) * H
        for sgn in (-1, 1):
            ex = hx + fdx + sgn * 0.068 * H; ey = hy - 0.004 * H + fdy
            cv.circle(ex, ey, 0.058 * H, None, outline=(60, 40, 50), width=cv.ol * 0.9)
        cv.arc(hx + fdx, hy - 0.004 * H + fdy + 0.004 * H, 0.012 * H, 0.01 * H, 200, 340, fill=(60, 40, 50), width=cv.ol * 0.8)
    if look.get("toque"):
        tb = hy - b * 0.78
        cv.rect(hx - a * 0.86, tb - 0.075 * H, hx + a * 0.86, tb + 0.02 * H, CHEF_W, r=0.012 * H)
        puffs = [(-0.1, -0.16, 0.085), (0.0, -0.2, 0.095), (0.1, -0.16, 0.085), (-0.05, -0.26, 0.08), (0.06, -0.26, 0.08)]
        for px, py, pr in puffs:
            cv.circle(hx + px * H, tb + py * H, pr * H, CHEF_W)
        for px, py, pr in puffs:
            cv.circle(hx + px * H, tb + py * H, pr * H - cv.ol * 1.2, CHEF_W, outline=None, width=0)
        cv.rect(hx - a * 0.86, tb - 0.075 * H, hx + a * 0.86, tb + 0.02 * H, CHEF_W, r=0.012 * H)
        for k in range(1, 5):
            xx = hx - a * 0.86 + k * a * 1.72 / 5
            cv.line([(xx, tb - 0.065 * H), (xx, tb + 0.01 * H)], fill=CHEF_SH, width=cv.ol * 0.6)

# ---------------------------------------------------------------- body parts
def hand(cv, x, y, r, sk, kind="fist", ang=0.0, mirror=1):
    """mitten hand: 'fist', 'open' (palm with thumb), 'grip'"""
    if kind == "open":
        cv.ellipse(x, y, r * 1.05, r * 1.15, sk)
        tx, ty = x + mirror * r * 0.95 * math.cos(ang), y + r * 0.2
        cv.ellipse(tx, ty, r * 0.42, r * 0.3, sk)
        cv.ellipse(x, y, r * 1.05, r * 1.15, sk, outline=None, width=0)
        for k in (-1, 0, 1):
            cv.line([(x + k * r * 0.35, y - r * 0.95), (x + k * r * 0.33, y - r * 0.45)], width=cv.ol * 0.6)
    else:
        cv.circle(x, y, r, sk)
        cv.arc(x, y + r * 0.15, r * 0.55, r * 0.4, 200, 340, width=cv.ol * 0.6)

def legs_stand(cv, H, P, look):
    lw = 0.135 * H
    hip = -0.31 * H
    walk = P.get("walk", None)
    for sgn in (-1, 1):
        lift = 0.0
        if walk is not None:
            lift = max(0.0, math.sin(walk * 2 * math.pi + (0 if sgn < 0 else math.pi))) * 0.05 * H
        x = sgn * 0.07 * H
        if look.get("skirt"):
            cv.rect(x - 0.035 * H, hip + 0.08 * H, x + 0.035 * H, -0.05 * H - lift, look["skin"], r=0.02 * H)
            cv.ellipse(x + sgn * 0.012 * H, -0.035 * H - lift, 0.068 * H, 0.04 * H, SHOE)
        else:
            cv.rect(x - lw / 2, hip, x + lw / 2, -0.045 * H - lift, look.get("trouser", TROUSER), r=0.025 * H)
            if look.get("check"):
                for k in range(1, 6):
                    yy = hip + k * 0.05 * H
                    cv.line([(x - lw / 2 + cv.ol, yy), (x + lw / 2 - cv.ol, yy)], fill=CHECK_L, width=cv.ol * 0.5)
                for q in (-1, 1):
                    cv.line([(x + q * lw * 0.2, hip + cv.ol), (x + q * lw * 0.2, -0.05 * H - lift)], fill=CHECK_L, width=cv.ol * 0.5)
            cv.ellipse(x + sgn * 0.02 * H, -0.038 * H - lift, 0.09 * H, 0.046 * H, SHOE)
            cv.arc(x + sgn * 0.01 * H, -0.05 * H - lift, 0.04 * H, 0.016 * H, 200, 300, fill=(90, 90, 96), width=cv.ol * 0.5)

def legs_kneel(cv, H, P, look):
    """kneeling on the right knee: left foot flat in front, right knee on the floor (front view)"""
    tr = look.get("trouser", TROUSER)
    hip = -0.22 * H
    # right leg: knee on floor, shin goes back (hidden), knee bulge
    cv.poly([(0.02 * H, hip), (0.15 * H, hip), (0.16 * H, -0.03 * H), (0.13 * H, 0.0), (0.03 * H, 0.0), (0.0, -0.05 * H)], tr)
    cv.ellipse(0.09 * H, -0.03 * H, 0.075 * H, 0.04 * H, tr)
    cv.poly([(0.02 * H, hip), (0.15 * H, hip), (0.16 * H, -0.05 * H), (0.03 * H, -0.05 * H)], tr, outline=None, width=0)
    # left leg: thigh toward camera (foreshortened) + shin down to the foot
    cv.rect(-0.16 * H, hip - 0.01 * H, -0.02 * H, -0.12 * H, tr, r=0.05 * H)
    cv.rect(-0.145 * H, -0.16 * H, -0.035 * H, -0.04 * H, tr, r=0.025 * H)
    cv.rect(-0.16 * H, hip - 0.01 * H, -0.02 * H, -0.12 * H, tr, r=0.05 * H, outline=None, width=0)
    cv.arc(-0.09 * H, -0.13 * H, 0.06 * H, 0.03 * H, 20, 160, fill=(70, 70, 80), width=cv.ol * 0.5)
    cv.ellipse(-0.1 * H, -0.03 * H, 0.085 * H, 0.04 * H, SHOE)

def torso(cv, H, P, look, hip_y, sh_y):
    kind = look["outfit"]
    w_sh = look.get("w_sh", 0.18) * H; w_w = look.get("w_w", 0.18) * H
    top, bot = sh_y - 0.03 * H, hip_y + 0.02 * H
    if kind == "chef":
        body = [(-w_sh, top + 0.02 * H), (-w_sh * 1.05, top + 0.1 * H), (-w_w * 1.12, (top + bot) / 2 + 0.06 * H), (-w_w * 1.02, bot),
                (w_w * 1.02, bot), (w_w * 1.12, (top + bot) / 2 + 0.06 * H), (w_sh * 1.05, top + 0.1 * H), (w_sh, top + 0.02 * H), (0, top - 0.01 * H)]
        cv.poly(body, CHEF_W)
        # double-breasted flap + 2 rows of buttons
        cv.line([(-w_sh * 0.4, top + 0.02 * H), (w_sh * 0.25, top + 0.08 * H), (w_sh * 0.25, bot - 0.01 * H)], fill=CHEF_SH, width=cv.ol * 0.8)
        for col in (-0.12, 0.12):
            for k in range(3):
                cv.circle(col * H + 0.03 * H, top + 0.11 * H + k * 0.075 * H, 0.013 * H, (235, 235, 238), width=cv.ol * 0.6)
        cv.poly(body, None)
        # red neckerchief
        cv.poly([(-0.07 * H, top + 0.0 * H), (0.07 * H, top + 0.0 * H), (0.0, top + 0.08 * H)], BOW_RED)
        cv.circle(0, top + 0.012 * H, 0.025 * H, (180, 28, 36))
    elif kind == "waiter":
        body = [(-w_sh, top + 0.02 * H), (-w_w, bot), (w_w, bot), (w_sh, top + 0.02 * H), (0, top - 0.005 * H)]
        cv.poly(body, SHIRT)
        vest = look.get("vest", BLACK_V)
        vd = tuple(int(v * 0.75) for v in vest)
        for sgn in (-1, 1):
            vp = [(sgn * 0.035 * H, top + 0.0 * H), (sgn * w_sh * 0.92, top + 0.02 * H), (sgn * w_w * 1.0, bot - 0.005 * H),
                  (sgn * w_w * 0.45, bot + 0.035 * H), (sgn * 0.004 * H, bot + 0.005 * H), (sgn * 0.004 * H, top + 0.15 * H)]
            cv.poly(vp, vest)
            cv.line([(sgn * w_sh * 0.55, top + 0.18 * H), (sgn * w_sh * 0.85, top + 0.17 * H)], fill=vd, width=cv.ol * 0.7)
        for k in range(3):
            cv.circle(-0.012 * H, top + 0.19 * H + k * 0.05 * H, 0.01 * H, (220, 200, 120), width=cv.ol * 0.5)
        cv.poly([(-0.05 * H, top - 0.01 * H), (0.0, top + 0.035 * H), (0.05 * H, top - 0.01 * H)], SHIRT, width=cv.ol * 0.8)
        # bow tie
        by = top + 0.02 * H
        cv.poly([(0, by), (-0.055 * H, by - 0.025 * H), (-0.055 * H, by + 0.025 * H)], BOW_RED, width=cv.ol * 0.8)
        cv.poly([(0, by), (0.055 * H, by - 0.025 * H), (0.055 * H, by + 0.025 * H)], BOW_RED, width=cv.ol * 0.8)
        cv.circle(0, by, 0.016 * H, (176, 26, 32), width=cv.ol * 0.8)
    elif kind == "cashier":
        sk = SKIRT
        # skirt (knee-length) from the waist
        cv.poly([(-w_w * 0.98, hip_y - 0.03 * H), (w_w * 0.98, hip_y - 0.03 * H), (w_w * 1.18, hip_y + 0.13 * H), (-w_w * 1.18, hip_y + 0.13 * H)], sk)
        body = [(-w_sh * 0.95, top + 0.02 * H), (-w_w * 0.9, hip_y), (w_w * 0.9, hip_y), (w_sh * 0.95, top + 0.02 * H), (0, top - 0.005 * H)]
        cv.poly(body, BLOUSE)
        vest = look.get("vest", BURGUNDY)
        for sgn in (-1, 1):
            vp = [(sgn * 0.04 * H, top + 0.0 * H), (sgn * w_sh * 0.88, top + 0.02 * H), (sgn * w_w * 0.9, hip_y),
                  (sgn * 0.01 * H, hip_y), (sgn * 0.01 * H, top + 0.13 * H)]
            cv.poly(vp, vest)
        cv.poly([(-0.045 * H, top - 0.01 * H), (0.0, top + 0.03 * H), (0.045 * H, top - 0.01 * H)], BLOUSE, width=cv.ol * 0.8)
        for k in range(2):
            cv.circle(0, top + 0.08 * H + k * 0.05 * H, 0.008 * H, (230, 210, 150), width=cv.ol * 0.5)

def arm(cv, H, sh, target, look, sleeve, hand_kind="fist", bend=1, side=1, prop=None, hand_ang=0.0):
    l1, l2 = 0.15 * H, 0.14 * H
    (ex, ey), (hx, hy) = ik(sh[0], sh[1], target[0], target[1], l1, l2, bend)
    w = look.get("arm_w", 0.078) * H
    cv.tube([sh, (ex, ey), (hx, hy)], w, sleeve)
    if look["outfit"] in ("waiter", "cashier"):   # white cuff ring
        cx_, cy_ = lerp(ex, hx, 0.82), lerp(ey, hy, 0.82)
    if prop and prop[1] == "under": prop[0](cv, hx, hy)
    hand(cv, hx, hy, 0.047 * H, look["skin"], hand_kind, hand_ang, side)
    if prop and prop[1] == "over": prop[0](cv, hx, hy)
    return (hx, hy), (ex, ey)

# ---------------------------------------------------------------- full figure
def render_person(look, H, P, ss=2):
    """P: pose 'stand'|'kneel', walk phase, arm targets 'L'/'R' as (x,y) in H units (local), bend, hand kinds,
    face dict, head offset/tilt, props {'L': (fn, 'under'|'over'), 'R': ...}, 'front_prop' (drawn last).
    Returns sticker image and the feet anchor (px) inside it plus key points (local px)."""
    cv = Canvas(H, ss=ss, top=look.get("top", 1.36))
    pose = P.get("pose", "stand")
    bob = P.get("bob", 0.0) * H
    if pose == "kneel":
        hip_y = -0.22 * H + bob; sh_y = -0.49 * H + bob; head_y = -0.70 * H + bob
    else:
        wk = P.get("walk")
        wb = (abs(math.sin(wk * 2 * math.pi)) * -0.015 * H) if wk is not None else 0.0
        hip_y = -0.31 * H + bob + wb; sh_y = -0.60 * H + bob + wb; head_y = -0.815 * H + bob + wb
    if look["outfit"] == "chef": sh_y += 0.0
    sleeve = look.get("sleeve", SHIRT)
    w_sh = look.get("w_sh", 0.18) * H
    shL = (-w_sh * 0.94, sh_y + 0.02 * H); shR = (w_sh * 0.94, sh_y + 0.02 * H)
    tL = P.get("L", (-0.21, 0.0)); tR = P.get("R", (0.21, 0.0))
    tL = (tL[0] * H, sh_y + 0.02 * H + tL[1] * H + 0.27 * H) if P.get("rel", True) else (tL[0] * H, tL[1] * H)
    tR = (tR[0] * H, sh_y + 0.02 * H + tR[1] * H + 0.27 * H) if P.get("rel", True) else (tR[0] * H, tR[1] * H)
    props = P.get("props", {})
    # back props (e.g. tray behind the head)
    arms_only = P.get("layer") == "arms"
    if P.get("back_prop") and not arms_only: P["back_prop"](cv, H, shL, shR, head_y)
    if arms_only: pass
    elif pose == "kneel": legs_kneel(cv, H, P, look)
    else: legs_stand(cv, H, P, look)
    pts = {}
    behind = P.get("behind", ())      # arms drawn behind the torso
    for side, sh, tg in (("L", shL, tL), ("R", shR, tR)):
        if side in behind:
            pts[side], pts[side + "e"] = arm(cv, H, sh, tg, look, sleeve, P.get("hk" + side, "fist"), P.get("bend" + side, 1 if side == "L" else -1), -1 if side == "L" else 1, props.get(side))
    hx = P.get("head_dx", 0.0) * H; hy = head_y + P.get("head_dy", 0.0) * H
    if not arms_only:
        cv.rect(-0.05 * H, head_y + 0.13 * H, 0.05 * H, sh_y + 0.0 * H, look["skin"])
        torso(cv, H, P, look, hip_y, sh_y)
    if P.get("arms_over_head", False) and not arms_only:
        draw_head(cv, H, hx, hy, look, P.get("face", {}))
    for side, sh, tg in (("L", shL, tL), ("R", shR, tR)):
        if side not in behind:
            pts[side], pts[side + "e"] = arm(cv, H, sh, tg, look, sleeve, P.get("hk" + side, "fist"), P.get("bend" + side, 1 if side == "L" else -1), -1 if side == "L" else 1, props.get(side))
    if not P.get("arms_over_head", False) and not arms_only:
        draw_head(cv, H, hx, hy, look, P.get("face", {}))
    pts["head"] = (hx, hy)
    if P.get("front_prop"): P["front_prop"](cv, H, pts)
    im = cv.result()
    st, pad = sticker(im, STICKER_PX * H / STD_H, 4.0 * H / STD_H, 6.0 * H / STD_H)
    ax, ay = cv.ox + pad, cv.oy + pad
    return st, ax, ay, pts

def blit_person(world, img, ax, ay, x, yb, ox, oy, scale=1.0, rot=0.0, alpha=1.0):
    """paste a rendered person so its feet anchor lands at world (x, yb)"""
    im = img
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    axs, ays = ax * scale, ay * scale
    if abs(rot) > 0.05:
        big = Image.new("RGBA", (im.width * 2, im.height * 2), (0, 0, 0, 0))
        big.paste(im, (int(im.width - axs), int(im.height - ays)))
        im = big.rotate(rot, resample=Image.BICUBIC, center=(im.width, im.height))
        axs, ays = im.width / 2, im.height / 2
    if alpha < 1: im = with_alpha(im, alpha)
    paste(world, im, x - ox - axs, yb - oy - ays)

# ---------------------------------------------------------------- looks
WAITER = dict(outfit="waiter", skin=(222, 150, 104), hair="short", hair_col=HAIR_BLACK, vest=BLACK_V)
WAITER2 = dict(outfit="waiter", skin=(238, 172, 128), hair="curly", hair_col=HAIR_BROWN, vest=BURGUNDY, brow=(90, 52, 30))
WAITER3 = dict(outfit="waiter", skin=(200, 128, 86), hair="side", hair_col=HAIR_BLACK, vest=NAVY_V)
CHEF = dict(outfit="chef", skin=(228, 148, 102), hair="chef", hair_col=HAIR_BLACK, w_sh=0.21, w_w=0.23, toque=True,
            moustache=HAIR_BLACK, sleeve=CHEF_W, trouser=CHECK_G, check=True, arm_w=0.08, top=1.62)
CASHIER = dict(outfit="cashier", skin=(232, 160, 116), hair="bun", hair_col=(44, 30, 28), vest=BURGUNDY, glasses=True,
               skirt=True, w_sh=0.165, w_w=0.16, sleeve=BLOUSE, arm_w=0.07)

# ---------------------------------------------------------------- props held by the characters
def folder_img(H, open_k=0.0):
    """brown portfolio folder with a small cartoon portrait of the waiter on the cover"""
    w, h = 0.3 * H, 0.38 * H
    c = Canvas(H, ss=2, left=0.2, top=0.22, right=0.2, bottom=0.22)
    x0, y0 = -w / 2, -h / 2
    c.rect(x0, y0, x0 + w, y0 + h, FOLDER, r=0.02 * H)
    c.rect(x0 + 0.015 * H, y0, x0 + 0.04 * H, y0 + h, (120, 70, 36), r=0.006 * H, width=c.ol * 0.7)
    # portrait frame
    pw, ph = 0.18 * H, 0.2 * H
    px0, py0 = x0 + (w - pw) / 2 + 0.012 * H, y0 + 0.05 * H
    c.rect(px0, py0, px0 + pw, py0 + ph, (255, 242, 214), r=0.01 * H, width=c.ol * 0.8)
    cx_, cy_ = px0 + pw / 2, py0 + ph * 0.5
    s = 0.33
    c.circle(cx_, cy_, 0.17 * H * s, (222, 150, 104), width=c.ol * 0.6)
    c.c.poly(c.T([(cx_ - 0.17 * H * s, cy_ - 0.02 * H * s), (cx_ - 0.12 * H * s, cy_ - 0.15 * H * s), (cx_ + 0.12 * H * s, cy_ - 0.15 * H * s),
                  (cx_ + 0.17 * H * s, cy_ - 0.02 * H * s), (cx_, cy_ - 0.09 * H * s)]), fill=HAIR_BLACK, outline=None, width=0)
    for sg in (-1, 1):
        c.circle(cx_ + sg * 0.06 * H * s, cy_ + 0.0, 0.03 * H * s, (255, 255, 255), width=c.ol * 0.4)
        c.circle(cx_ + sg * 0.06 * H * s, cy_ + 0.0, 0.013 * H * s, OL, outline=None, width=0)
    c.arc(cx_, cy_ + 0.05 * H * s, 0.05 * H * s, 0.035 * H * s, 20, 160, width=c.ol * 0.5)
    c.poly([(cx_, cy_ + 0.2 * H * s), (cx_ - 0.06 * H * s, cy_ + 0.17 * H * s), (cx_ - 0.06 * H * s, cy_ + 0.23 * H * s)], BOW_RED, width=c.ol * 0.4)
    c.poly([(cx_, cy_ + 0.2 * H * s), (cx_ + 0.06 * H * s, cy_ + 0.17 * H * s), (cx_ + 0.06 * H * s, cy_ + 0.23 * H * s)], BOW_RED, width=c.ol * 0.4)
    # label lines (no readable text)
    for k, ww in enumerate((0.6, 0.42)):
        yy = py0 + ph + 0.035 * H + k * 0.03 * H
        c.line([(x0 + w * (0.5 - ww / 2) + 0.012 * H, yy), (x0 + w * (0.5 + ww / 2) + 0.012 * H, yy)], fill=(230, 196, 140), width=0.012 * H)
    im = c.result()
    return im, c.ox, c.oy      # centre of folder at (ox, oy) inside the image

def tray_draw(H, tilt=0.0):
    def fn(cv, hx, hy):
        r = 0.13 * H
        ty = hy - 0.045 * H
        cv.ellipse(hx, ty + 0.012 * H, r, r * 0.3, (150, 156, 164))
        cv.ellipse(hx, ty, r, r * 0.3, STEEL)
        cv.ellipse(hx, ty, r * 0.78, r * 0.22, (222, 228, 232), outline=(170, 176, 184), width=cv.ol * 0.5)
        cv.arc(hx - r * 0.3, ty - r * 0.05, r * 0.3, r * 0.1, 200, 300, fill=(255, 255, 255), width=cv.ol * 0.8)
        # a covered dish (cloche) on the tray
        cv.c.pieslice((hx - r * 0.45 + cv.ox, ty - r * 0.5 + cv.oy, hx + r * 0.45 + cv.ox, ty + r * 0.4 + cv.oy), 180, 360, fill=(232, 236, 240), outline=OL, width=cv.ol)
        cv.line([(hx - r * 0.5, ty - 0.005 * H), (hx + r * 0.5, ty - 0.005 * H)], width=cv.ol)
        cv.circle(hx, ty - r * 0.5, 0.014 * H, (232, 236, 240), width=cv.ol * 0.8)
        cv.arc(hx - r * 0.15, ty - r * 0.25, r * 0.2, r * 0.2, 200, 260, fill=(255, 255, 255), width=cv.ol * 0.8)
    return fn

def mask_draw(H, kind, up=1.0):
    """theatre mask on a stick, held in the fist (stick under the hand)"""
    def fn(cv, hx, hy):
        mx, my = hx + 0.0, hy - 0.2 * H * up
        cv.line([(hx, hy + 0.02 * H), (mx, my + 0.08 * H)], fill=OL, width=0.022 * H)
        cv.line([(hx, hy + 0.02 * H), (mx, my + 0.08 * H)], fill=(176, 120, 60), width=0.013 * H)
        col = {"smile": (255, 226, 120), "cry": (180, 210, 245), "wow": (255, 255, 255)}[kind]
        w, h = 0.11 * H, 0.13 * H
        pts = [(mx - w, my - h * 0.9), (mx - w * 0.3, my - h * 1.0), (mx, my - h * 0.86), (mx + w * 0.3, my - h * 1.0), (mx + w, my - h * 0.9),
               (mx + w * 1.02, my - h * 0.2), (mx + w * 0.7, my + h * 0.55), (mx, my + h * 0.95), (mx - w * 0.7, my + h * 0.55), (mx - w * 1.02, my - h * 0.2)]
        cv.poly(pts, col)
        for sg in (-1, 1):
            ex, ey = mx + sg * w * 0.45, my - h * 0.35
            if kind == "smile":
                cv.c.chord((ex - w * 0.26 + cv.ox, ey - h * 0.2 + cv.oy, ex + w * 0.26 + cv.ox, ey + h * 0.2 + cv.oy), 180, 360, fill=OL)
            elif kind == "cry":
                cv.c.chord((ex - w * 0.26 + cv.ox, ey - h * 0.1 + cv.oy, ex + w * 0.26 + cv.ox, ey + h * 0.26 + cv.oy), 0, 180, fill=OL)
                cv.line([(ex - sg * w * 0.25, ey - h * 0.22), (ex + sg * w * 0.2, ey - h * 0.32)], width=cv.ol * 0.9)
            else:
                cv.circle(ex, ey, w * 0.2, OL, outline=None, width=0)
        if kind == "smile":
            cv.c.chord((mx - w * 0.55 + cv.ox, my + h * 0.0 + cv.oy, mx + w * 0.55 + cv.ox, my + h * 0.65 + cv.oy), 0, 180, fill=OL)
            for sg in (-1, 1): cv.circle(mx + sg * w * 0.6, my + h * 0.05, w * 0.14, BLUSH, outline=None, width=0)
        elif kind == "cry":
            cv.c.chord((mx - w * 0.5 + cv.ox, my + h * 0.25 + cv.oy, mx + w * 0.5 + cv.ox, my + h * 0.8 + cv.oy), 180, 360, fill=OL)
            cv.ellipse(mx - w * 0.45, my + h * 0.05, w * 0.1, h * 0.13, (120, 190, 255), width=cv.ol * 0.6)
        else:
            cv.ellipse(mx, my + h * 0.42, w * 0.2, h * 0.24, OL, outline=None, width=0)
            for sg in (-1, 1): cv.line([(mx + sg * w * 0.3, my - h * 0.72), (mx + sg * w * 0.62, my - h * 0.78)], width=cv.ol * 0.9)
        cv.line([(mx - w * 1.0, my - h * 0.85), (mx - w * 1.25, my - h * 0.7), (mx - w * 1.1, my - h * 0.55)], fill=(214, 40, 40), width=cv.ol * 0.9)
        cv.line([(mx + w * 1.0, my - h * 0.85), (mx + w * 1.25, my - h * 0.7), (mx + w * 1.1, my - h * 0.55)], fill=(214, 40, 40), width=cv.ol * 0.9)
    return fn

def knife_draw(H, ang):
    """cartoon kitchen knife with a rounded tip, held in the fist; ang = blade direction (deg, 0 = right)"""
    def fn(cv, hx, hy):
        a = math.radians(ang)
        ux, uy = math.cos(a), math.sin(a); nx, ny = -uy, ux
        L, Wd = 0.2 * H, 0.05 * H
        b0 = (hx + ux * 0.03 * H, hy + uy * 0.03 * H)
        tip = (b0[0] + ux * L, b0[1] + uy * L)
        blade = [b0, (b0[0] + nx * Wd, b0[1] + ny * Wd), (tip[0] + nx * Wd * 0.6 - ux * Wd * 0.3, tip[1] + ny * Wd * 0.6 - uy * Wd * 0.3),
                 (tip[0] + nx * Wd * 0.25, tip[1] + ny * Wd * 0.25), tip]
        cv.poly(blade, (226, 232, 238))
        cv.line([(b0[0] + nx * Wd * 0.25 + ux * 0.02 * H, b0[1] + ny * Wd * 0.25 + uy * 0.02 * H), (tip[0] + nx * Wd * 0.3 - ux * 0.04 * H, tip[1] + ny * Wd * 0.3 - uy * 0.04 * H)],
                fill=(255, 255, 255), width=cv.ol * 0.7)
        hb = (hx - ux * 0.06 * H, hy - uy * 0.06 * H)
        cv.tube([hb, b0], 0.035 * H, (120, 72, 40))
    return fn

def onion_half_draw(H):
    def fn(cv, hx, hy):
        r = 0.065 * H
        cv.ellipse(hx, hy + 0.02 * H, r * 1.1, r, (240, 228, 236))
        for k in (0.72, 0.45, 0.2):
            cv.ellipse(hx, hy + 0.02 * H, r * 1.1 * k, r * k, None, outline=(196, 150, 190), width=cv.ol * 0.6)
    return fn
