# Flat silhouette people and animals (all in one dark tone per scene; no outlines).
import math, random
from common import *
from env import ellipse_pts

def person(cv, X, Y, k, col, dir=1, walk=0.0, phase=0.0, pose="stand", lean=0.0, look=0.0, hat="doppi",
           dress="coat", arms=None, clap=0.0, head_dy=0.0):
    """side-view silhouette; (X, Y) = ground point, k = scale (k=1 -> ~345 px tall).
    pose: stand | sit_cross (on the floor/so'ri);  look: 0 = profile, 1 = head turned to the viewer;
    lean: torso rotation (deg) around the hip;  arms: [(elbow, hand), (elbow, hand)] in body coords (before lean);
    clap: phase in 0..1 per clap (hands together at 0/1)."""
    d = dir
    def L(p): return (X + d * p[0] * k, Y + p[1] * k)
    def Lp(ps): return [L(p) for p in ps]
    th = math.radians(24) * walk * math.sin(phase)
    oy = 150.0 if pose == "sit_cross" else 0.0
    hipP = (0.0, -172.0 + oy)
    def B(p):
        q = (p[0], p[1] + oy)
        return rot(q, lean, hipP) if lean else q
    # legs
    if pose == "sit_cross":
        cv.poly(Lp(ellipse_pts(18, -16, 60, 17, 20)), col)
    else:
        for s_ in (1, -1):
            a = th * s_
            hp = (s_ * 3, -172)
            ft = (hp[0] + 160 * math.sin(a), -12)
            cv.capsule(L(hp), L(ft), 10.5 * k, 9 * k, col)
            cv.poly(Lp([(ft[0] - 8, -14), (ft[0] + 18, -10), (ft[0] + 20, 0), (ft[0] - 9, 0)]), col)
    # body
    if pose == "sit_cross":
        body = [(-22, -292), (22, -292), (30, -240), (30, -175), (34, -160), (-32, -160), (-30, -175), (-28, -240)]
    elif dress == "coat":
        body = [(-22, -292), (22, -292), (30, -240), (28, -175), (36, -78), (-36, -78), (-30, -175), (-28, -240)]
        if walk: body = [(x + (4 * walk * math.sin(phase * 2) if y > -150 else 0), y) for x, y in body]
    elif dress == "skirt":
        body = [(-20, -292), (20, -292), (27, -230), (24, -180), (44, -30), (-44, -30), (-24, -180), (-25, -230)]
    else:
        body = [(-22, -292), (22, -292), (28, -230), (24, -168), (-24, -168), (-28, -230)]
    cv.poly(Lp([B(p) for p in body]), col)
    # neck + head
    cv.poly(Lp([B(p) for p in [(-6, -304), (8, -304), (8, -288), (-6, -288)]]), col)
    hc = B((3 + 2 * (1 - look), -322 + head_dy))
    cv.poly(Lp(ellipse_pts(hc[0], hc[1], 17.5, 20.5, 20)), col)
    if look < 0.5:
        cv.poly(Lp([(hc[0] + 15, hc[1] - 6), (hc[0] + 22, hc[1] + 4), (hc[0] + 15, hc[1] + 9)]), col)
    if hat == "doppi":
        cv.poly(Lp([(hc[0] - 19, hc[1] - 12), (hc[0] - 18, hc[1] - 28), (hc[0] - 12, hc[1] - 37), (hc[0] + 12, hc[1] - 37), (hc[0] + 18, hc[1] - 28), (hc[0] + 20, hc[1] - 12)]), col)
    elif hat == "cap":
        cv.poly(Lp([(hc[0] - 19, hc[1] - 10), (hc[0] - 15, hc[1] - 30), (hc[0] + 14, hc[1] - 30), (hc[0] + 19, hc[1] - 12), (hc[0] + 36, hc[1] - 10), (hc[0] + 18, hc[1] - 6)]), col)
    elif hat == "scarf":
        cv.poly(Lp([(hc[0] - 22, hc[1] - 4), (hc[0] - 18, hc[1] - 26), (hc[0] + 2, hc[1] - 31), (hc[0] + 18, hc[1] - 22), (hc[0] + 20, hc[1] - 6),
                    (hc[0] - 4, hc[1] + 30), (hc[0] - 30, hc[1] + 46), (hc[0] - 30, hc[1] + 12)]), col)
    elif hat == "bun":
        cv.circle(*L((hc[0] - 16, hc[1] - 14)), 10 * k, col)
    # arms
    sh = B((2, -282))
    if arms is None:
        if pose == "sit_cross":
            arms = [((20, -205), (46, -172)), ((16, -206), (40, -170))]
        elif clap:
            c = abs(math.cos(math.pi * clap))          # 1 = hands together
            arms = [((26, -222), (46 - 14 * (1 - c), -252)), ((22, -224), (50 + 12 * (1 - c), -250))]
        else:
            sw = walk * 22 * math.sin(phase)
            arms = [((-2 + sw * 0.35, -210), (8 + sw, -146)), ((-2 - sw * 0.35, -210), (8 - sw, -146))]
    for (e, hnd) in arms:
        e, hnd = B(e), B(hnd)
        cv.capsule(L(sh), L(e), 10 * k, 9.5 * k, col)
        cv.capsule(L(e), L(hnd), 9.5 * k, 8.5 * k, col)
        cv.circle(*L(hnd), 8.5 * k, col)
    return dict(head=L(hc), hand=L(B(arms[0][1])))

# ---------------------------------------------------------------- animals
def dog_sleep(cv, x, y, k, col, t, dir=1):
    b = 1 + 0.045 * math.sin(2 * math.pi * 0.42 * t)
    d = dir
    cv.poly(ellipse_pts(x, y - 20 * k * b, 62 * k, 21 * k * b, 28), col)
    cv.poly(ellipse_pts(x - d * 34 * k, y - 22 * k * b, 26 * k, 22 * k * b, 18), col)
    hx_ = x + d * 52 * k; hy_ = y - 14 * k
    cv.poly(ellipse_pts(hx_, hy_, 20 * k, 13 * k, 16, ang=8 * d), col)
    cv.poly(ellipse_pts(hx_ + d * 18 * k, hy_ + 4 * k, 12 * k, 7 * k, 12), col)
    cv.poly([(hx_ - d * 6 * k, hy_ - 10 * k), (hx_ - d * 18 * k, hy_ - 2 * k + 3 * k * math.sin(t * 1.3)), (hx_ - d * 2 * k, hy_ + 2 * k)], col)
    tl = [(x - d * 60 * k, y - 10 * k), (x - d * 78 * k, y - 4 * k), (x - d * 70 * k, y + 1 * k), (x - d * 30 * k, y)]
    cv.poly(tl, col)

def cat_sit(cv, x, y, k, col, t, dir=1, look=0.0):
    d = dir
    cv.poly([(x - 18 * k, y), (x - 15 * k, y - 34 * k), (x - 4 * k, y - 52 * k), (x + 10 * k, y - 50 * k), (x + 18 * k, y - 26 * k), (x + 20 * k, y)], col)
    hx_, hy_ = x + d * (6 + 3 * look) * k, y - 60 * k
    cv.circle(hx_, hy_, 13 * k, col)
    for s_ in (-1, 1):
        cv.poly([(hx_ + s_ * 4 * k, hy_ - 9 * k), (hx_ + s_ * 12 * k, hy_ - 22 * k), (hx_ + s_ * 13 * k, hy_ - 6 * k)], col)
    sw = math.sin(2 * math.pi * 0.6 * t)
    tail = [(x - d * 16 * k, y - 2 * k), (x - d * 34 * k, y - 2 * k), (x - d * (44 + 4 * sw) * k, y - (12 + 8 * sw) * k), (x - d * (40 + 6 * sw) * k, y - (26 + 6 * sw) * k)]
    cv.line(tail, col, 6 * k)

def quadruped(cv, x, y, k, col, t, kind="donkey", dir=1, walk=0.0, phase=0.0, head_look=0.0, graze=0.0):
    d = dir
    if kind == "donkey":
        bl, bh, leg, neck, ear = 64, 30, 58, 1.0, 34
    elif kind == "goat":
        bl, bh, leg, neck, ear = 40, 20, 40, 0.7, 12
    else:
        bl, bh, leg, neck, ear = 64, 30, 58, 1.0, 10
    by = y - leg * k - bh * 0.5 * k
    cv.poly(ellipse_pts(x, by, bl * k, bh * k, 24), col)
    for i, fx in enumerate((-0.7, -0.5, 0.55, 0.72)):
        a = math.radians(18) * walk * math.sin(phase + (i % 2) * math.pi + (i // 2) * 0.6)
        hx0 = x + fx * bl * k
        top = (hx0, by + bh * 0.3 * k)
        ft = (hx0 + math.sin(a) * leg * k, y)
        cv.line([top, ft], col, (8 if kind != "goat" else 5.5) * k, caps=False)
        cv.rect(ft[0] - 4 * k, y - 6 * k, ft[0] + 4 * k, y, col)
    # neck + head
    nb = (x + d * bl * 0.75 * k, by - bh * 0.2 * k)
    hang = math.radians(-50 + 75 * graze)
    hl = (52 if kind != "goat" else 34) * neck * k
    hp = (nb[0] + d * hl * math.cos(hang) * 0.8, nb[1] + hl * math.sin(hang))
    cv.capsule(nb, hp, 15 * k if kind != "goat" else 9 * k, 11 * k if kind != "goat" else 7 * k, col)
    sz = 1.0 if kind != "goat" else 0.62
    if head_look > 0.5:
        cv.poly(ellipse_pts(hp[0], hp[1] + 6 * k, 16 * k * sz, 22 * k * sz, 16), col)
    else:
        cv.poly(ellipse_pts(hp[0] + d * 14 * k * sz, hp[1] + 8 * k * sz, 24 * k * sz, 12 * k * sz, 16, ang=35 * d), col)
    tw = 4 * math.sin(t * 2.0)
    if kind == "donkey":
        for s_ in (-1, 1):
            cv.poly([(hp[0] - 4 * k + s_ * 4 * k, hp[1] - 6 * k), (hp[0] + d * (s_ * 6 - 8) * k + tw * k * (s_ > 0), hp[1] - ear * k), (hp[0] + 6 * k + s_ * 4 * k, hp[1] - 4 * k)], col)
        cv.line([(x - d * bl * 0.95 * k, by - 4 * k), (x - d * (bl + 10) * k, by + (26 + 4 * math.sin(t * 3)) * k)], col, 4 * k)
    elif kind == "goat":
        cv.line([(hp[0], hp[1] - 6 * k), (hp[0] - d * 10 * k, hp[1] - 22 * k), (hp[0] - d * 18 * k, hp[1] - 18 * k)], col, 3.4 * k)
        cv.poly([(hp[0] + d * 6 * k, hp[1] + 12 * k), (hp[0] + d * 10 * k, hp[1] + 26 * k), (hp[0] + d * 13 * k, hp[1] + 12 * k)], col)
        cv.poly([(x - d * bl * 0.95 * k, by - 6 * k), (x - d * (bl + 8) * k, by - (16 + 4 * math.sin(t * 5)) * k), (x - d * bl * 0.8 * k, by - 12 * k)], col)

def camel(cv, x, y, k, col, t, dir=1, phase=0.0):
    d = dir
    leg = 92
    by = y - leg * k - 18 * k
    cv.poly(ellipse_pts(x, by, 62 * k, 26 * k, 24), col)
    cv.poly(ellipse_pts(x - d * 6 * k, by - 22 * k, 34 * k, 30 * k, 20, 180, 360), col)
    for i, fx in enumerate((-0.68, -0.48, 0.5, 0.7)):
        a = math.radians(16) * math.sin(phase + (i % 2) * math.pi + (i // 2) * 0.5)
        hx0 = x + fx * 62 * k
        knee = (hx0 + math.sin(a) * leg * 0.5 * k, by + leg * 0.5 * k)
        ft = (hx0 + math.sin(a) * leg * k * 0.9, y)
        cv.line([(hx0, by + 10 * k), knee, ft], col, 7 * k)
    nb = (x + d * 50 * k, by - 4 * k)
    bob = 4 * math.sin(phase * 2)
    n1 = (x + d * 86 * k, by + (10 + bob) * k)
    hp = (x + d * 100 * k, by - (40 - bob) * k)
    cv.line([nb, n1, hp], col, 15 * k)
    cv.poly(ellipse_pts(hp[0] + d * 10 * k, hp[1] + 2 * k, 18 * k, 9 * k, 14), col)
    cv.line([(x - d * 60 * k, by - 2 * k), (x - d * 70 * k, by + 30 * k)], col, 3.5 * k)

def stork(cv, x, y, k, col, t, dir=1, ph=0.0):
    d = dir
    f = math.sin(2 * math.pi * 1.6 * t + ph)
    cv.poly(ellipse_pts(x, y, 34 * k, 10 * k, 16), col)
    cv.line([(x + d * 30 * k, y - 2 * k), (x + d * 62 * k, y - 6 * k)], col, 5 * k)
    cv.circle(x + d * 64 * k, y - 7 * k, 6.5 * k, col)
    cv.line([(x + d * 68 * k, y - 7 * k), (x + d * 92 * k, y - 3 * k)], col, 3 * k)
    cv.line([(x - d * 30 * k, y + 2 * k), (x - d * 78 * k, y + 8 * k)], col, 3 * k)
    for s_ in (1, -1):
        tip = (x - d * 14 * k, y - s_ * 0 - 64 * k * f)
        cv.poly([(x - d * 16 * k, y - 2 * k), (x + d * 16 * k, y - 2 * k), (x + d * 4 * k, y - 66 * k * f), (x - d * 30 * k, y - 60 * k * f)], col)

def fish(cv, x, y, k, col, dir=1, t=0.0):
    d = dir
    wig = math.sin(t * 9) * 6
    cv.poly(ellipse_pts(x, y, 34 * k, 12 * k, 20), col)
    cv.poly([(x - d * 28 * k, y), (x - d * 50 * k, y - (14 - wig * 0.5) * k), (x - d * 46 * k, y + wig * 0.2 * k), (x - d * 50 * k, y + (14 + wig * 0.5) * k)], col)
    cv.poly([(x - d * 6 * k, y - 10 * k), (x - d * 2 * k, y - 20 * k), (x + d * 10 * k, y - 10 * k)], col)

def tumbleweed(cv, x, y, r, col, ang):
    for i in range(9):
        a = math.radians(ang + i * 40)
        p0 = (x + r * 0.9 * math.cos(a), y + r * 0.9 * math.sin(a))
        p1 = (x + r * 0.9 * math.cos(a + 2.4), y + r * 0.9 * math.sin(a + 2.4))
        mid = (x + r * 0.3 * math.cos(a + 1.2), y + r * 0.3 * math.sin(a + 1.2))
        cv.line([p0, mid, p1], col + (210,) if len(col) == 3 else col, max(1.5, r * 0.07))
    ring_pts = ellipse_pts(x, y, r, r, 24)
    cv.line(ring_pts + [ring_pts[0]], col, max(1.5, r * 0.08))
