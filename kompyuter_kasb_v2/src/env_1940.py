# 1940s: rows of desks with human computers and the ENIAC panel wall, drawn as flat shapes placed on a 3-D ground
# plane so the camera can really tilt from top-down to eye level (scene 8) and dolly along the panels.
import math
import skia
from common import *
from style import P, stroke_path

F = 1100.0                     # focal length, px
DESK_ROWS_X = [-8.6, -6.3, -4.0, -1.7]
DESK_Z = [6.0 + 3.0 * k for k in range(8)]        # 6 .. 27 m
WALL_Z = 31.0
WALL_X0, WALL_X1 = -11.0, 13.0
PANEL_W, PANEL_GAP, PANEL_H = 0.95, 0.07, 3.1
N_PANELS = int((WALL_X1 - WALL_X0) / (PANEL_W + PANEL_GAP))
LAMP_ROWS, LAMP_COLS = 9, 4
WOMAN = "#64777A"


class Cam3:
    def __init__(self, x=0.0, h=2.0, z=0.0, pitch=0.0, cy=960.0, shift=(0.0, 0.0)):
        self.x, self.h, self.z, self.pitch, self.cy, self.shift = x, h, z, math.radians(pitch), cy, shift

    def proj(self, X, Y, Z):
        dx, dy, dz = X - self.x, Y - self.h, Z - self.z
        s, c = math.sin(self.pitch), math.cos(self.pitch)
        d = dy * s + dz * c
        yc = dy * c - dz * s
        if d < 0.05: return None
        return 540 + F * dx / d + self.shift[0], self.cy - F * yc / d + self.shift[1], d

    def horizon_y(self):
        return self.cy + F * math.tan(self.pitch) + self.shift[1]


def _quad(cam, pts3):
    out = []
    for X, Y, Z in pts3:
        q = cam.proj(X, Y, Z)
        if q is None: return None
        out.append((q[0], q[1]))
    return poly(out)


def fade(colr, d, far=P["l1"]):
    return mix(colr, far, clamp01((d - 8) / 60.0) * 0.75)


def billboard(c, cam, X, Z, draw, Y=0.0, alpha=1.0):
    """draw(c) draws a sprite in centimetres, origin at its feet, y up negative; scaled by distance and pitch"""
    a = cam.proj(X, Y, Z); b = cam.proj(X, Y + 1.0, Z)
    if a is None or b is None: return None
    k = F / a[2] / 100.0
    ky = (a[1] - b[1]) / 100.0
    if ky <= 0.002: return a
    c.save(); c.translate(a[0], a[1]); c.scale(k, ky)
    draw(c)
    c.restore()
    return a


# ---------------------------------------------------------------- sprites (centimetres)
def seated_back(c, colr, t, seed):
    """seated woman seen from behind (chair, torso, head with bun), arms working"""
    p = paint(colr)
    c.drawRect(skia.Rect.MakeLTRB(-24, -48, 24, -42), p)                    # seat
    for lx in (-20, 16): c.drawRect(skia.Rect.MakeLTRB(lx, -44, lx + 4, 0), p)
    sway = 2.5 * math.sin(t * 2.4 + seed)
    c.drawPath(poly([(-22 + sway, -50), (22 + sway, -50), (18 + sway, -112), (-18 + sway, -112)]), p)
    c.drawPath(rrect(-20 + sway, -122, 20 + sway, -104, 9), p)              # shoulders
    c.drawRect(skia.Rect.MakeLTRB(-4 + sway, -132, 4 + sway, -118), p)
    c.drawCircle(sway, -142, 11, p)
    c.drawCircle(sway, -150, 7, p)                                          # bun
    for s in (-1, 1):                                                        # elbows out, writing
        e = skia.Path(); e.moveTo(s * 18 + sway, -112)
        e.lineTo(s * 26 + sway + 3 * math.sin(t * 9 + seed + s), -86)
        c.drawPath(stroke_path(e, 7), p)


def desk_front(c, colr):
    p = paint(colr)
    c.drawRect(skia.Rect.MakeLTRB(-60, -78, 60, -72), p)
    for lx in (-58, 52): c.drawRect(skia.Rect.MakeLTRB(lx, -74, lx + 6, 0), p)
    c.drawRect(skia.Rect.MakeLTRB(-58, -72, 58, -50), p)


def walking_back(c, colr, phase, reach=0.0):
    """slim 1940s woman from behind: knee-length dress, bun; walking, or reaching up to plug a cable"""
    p = paint(colr)
    sw = math.sin(phase)
    for s in (-1, 1):
        dy = 4 * max(0.0, sw * s)
        c.drawRect(skia.Rect.MakeLTRB(s * 7 - 3, -52 - dy, s * 7 + 3, -4 - dy), p)
        c.drawPath(rrect(s * 7 - 5, -8 - dy, s * 7 + 5, 0 - dy, 3), p)
    c.drawPath(poly([(-11, -105), (11, -105), (22, -52), (-22, -52)]), p)    # skirt
    c.drawPath(poly([(-10, -106), (10, -106), (14, -136), (-14, -136)]), p)  # bodice
    c.drawPath(rrect(-16, -142, 16, -132, 5), p)
    c.drawRect(skia.Rect.MakeLTRB(-3.5, -150, 3.5, -138), p)
    c.drawCircle(0, -159, 10.5, p); c.drawCircle(0, -168, 6.5, p)
    # arms: left swings, right swings or reaches up
    a = skia.Path(); a.moveTo(-14, -136); a.lineTo(-18 + 6 * sw, -96); c.drawPath(stroke_path(a, 6), p)
    ang = lerp(0.15 - 0.25 * sw, 2.9, reach)                                 # radians from straight down
    el = (14 + 22 * math.sin(ang), -136 + 22 * math.cos(ang))
    hd = (el[0] + 20 * math.sin(ang * 0.95), el[1] + 20 * math.cos(ang * 0.95))
    a = skia.Path(); a.moveTo(14, -136); a.lineTo(*el); a.lineTo(*hd); c.drawPath(stroke_path(a, 6), p)
    c.drawCircle(hd[0], hd[1], 3.6, p)
    return hd


# ---------------------------------------------------------------- the hall
def lamp_default(t):
    def f(k, r, q):
        v = math.sin(t * (2.0 + 4 * hash01(k, r, q)) + 6.28 * hash01(k, r, q, 2))
        return clamp01((v - 0.25) * 2.5)
    return f


def panel_x(k):
    return WALL_X0 + k * (PANEL_W + PANEL_GAP)


def draw_ground_sky(c, cam, t=0.0):
    hy = cam.horizon_y()
    sh = skia.GradientShader.MakeLinear([skia.Point(0, hy - 1300), skia.Point(0, hy)], [col(P["sky_top"]), col(P["sky_bot"])])
    c.drawRect(skia.Rect.MakeLTRB(-100, -200, 1200, max(-200, hy) + 2), skia.Paint(Shader=sh))
    if hy > 0:
        from style import cloud_path
        pc = paint(P["cloud"])
        for seed, x, dy, w in ((11, 150, 760, 250), (12, 700, 600, 210), (13, 1020, 860, 280), (14, 420, 380, 190)):
            xx = (x + 10 * t - cam.x * 6 + 600) % 2000 - 500
            c.save(); c.translate(xx, hy - dy); c.drawPath(cloud_path(seed, w), pc); c.restore()
    g = skia.GradientShader.MakeLinear([skia.Point(0, max(hy, -4000)), skia.Point(0, max(hy, -4000) + 900)], [col(P["l2"]), col(P["l3"])])
    c.drawRect(skia.Rect.MakeLTRB(-100, max(-200, hy), 1200, 2200), skia.Paint(Shader=g))
    return hy


def draw_far_background(c, cam):
    """1940s horizon: low factory blocks with chimneys, a water tower, trees (very far, hazy)"""
    hy = cam.horizon_y()
    if hy < -100 or hy > 2100: return
    pth = skia.Path()
    for k in range(30):
        x = -200 + k * 52 - cam.x * 4
        h = 18 + 40 * hash01(k, 3)
        if hash01(k, 4) < 0.5:
            pth.addRect(skia.Rect.MakeLTRB(x, hy - h, x + 46, hy + 2))
            if hash01(k, 5) < 0.35: pth.addRect(skia.Rect.MakeLTRB(x + 30, hy - h - 34, x + 36, hy - h))
        else:
            pth.addCircle(x + 20, hy - h * 0.6, 16); pth.addRect(skia.Rect.MakeLTRB(x + 18, hy - 10, x + 22, hy + 2))
    c.drawPath(pth, paint(P["l1"]))


def draw_hall(c, cam, t, lamp_fn=None, desk_alpha=None, desks_on=True, walkers=(), extra3d=(), sheets=True):
    """painter's algorithm over desks, women, the panel wall and extra items (far -> near)"""
    lamp_fn = lamp_fn or lamp_default(t)
    draw_ground_sky(c, cam, t)
    draw_far_background(c, cam)
    items = []
    # aisle lines on the floor
    for X in [x + 1.15 for x in DESK_ROWS_X] + [DESK_ROWS_X[0] - 1.15]:
        q = _quad(cam, [(X - 0.04, 0, 3.0), (X + 0.04, 0, 3.0), (X + 0.04, 0, WALL_Z), (X - 0.04, 0, WALL_Z)])
        if q is not None: c.drawPath(q, paint(mix(P["l2"], P["l3"], 0.45)))
    # panel wall
    wq = cam.proj(cam.x, 1.5, WALL_Z)
    items.append(((wq[2] + 0.01) if wq else 999.0, lambda: draw_wall(c, cam, lamp_fn)))
    if desks_on:
        for ri, X in enumerate(DESK_ROWS_X):
            for zi, Z in enumerate(DESK_Z):
                q = cam.proj(X, 0.0, Z)
                if q is None: continue
                a = 1.0 if desk_alpha is None else desk_alpha(ri, zi)
                items.append((q[2], (lambda X=X, Z=Z, a=a, s=ri * 10 + zi: draw_desk(c, cam, X, Z, t, a, s, sheets))))
    for d, fn in extra3d:
        items.append((d, fn))
    for w in walkers:
        q = cam.proj(w[0], 0.0, w[1])
        if q is not None:
            items.append((q[2] - 0.2, (lambda w=w: billboard(c, cam, w[0], w[1], lambda cc: w[2](cc)))))
    for d, fn in sorted(items, key=lambda it: -it[0]):
        fn()


def draw_desk(c, cam, X, Z, t, alpha, seed, sheets=True):
    d = cam.proj(X, 0.76, Z)
    if d is None: return
    dc = fade(P["l5"], d[2])
    top = _quad(cam, [(X - 0.6, 0.76, Z - 0.35), (X + 0.6, 0.76, Z - 0.35), (X + 0.6, 0.76, Z + 0.35), (X - 0.6, 0.76, Z + 0.35)])
    billboard(c, cam, X, Z - 0.35, lambda cc: desk_front(cc, dc))
    if top is not None: c.drawPath(top, paint(dc))
    if sheets:
        sh = _quad(cam, [(X - 0.32, 0.77, Z - 0.05), (X + 0.3, 0.77, Z - 0.05), (X + 0.3, 0.77, Z + 0.3), (X - 0.32, 0.77, Z + 0.3)])
        if sh is not None: c.drawPath(sh, paint(fade(P["glow"], d[2]), a=255 * max(alpha, 0.0) if alpha < 1 else 255))
    if alpha <= 0.01: return
    wc = fade(WOMAN, d[2])
    # woman: seated, behind the desk (towards the camera) -> seen from behind at eye level, from above top-down
    c.save()
    if alpha < 1: c.saveLayerAlpha(None, int(255 * alpha))
    billboard(c, cam, X, Z - 0.75, lambda cc: seated_back(cc, wc, t, seed))
    # top-view parts (visible from above): shoulders, head and bun, forearms to the sheet
    sh_ = _quad(cam, [(X - 0.22, 1.22, Z - 0.84), (X + 0.22, 1.22, Z - 0.84), (X + 0.22, 1.22, Z - 0.66), (X - 0.22, 1.22, Z - 0.66)])
    if sh_ is not None: c.drawPath(sh_, paint(wc))
    hc = cam.proj(X, 1.4, Z - 0.74); bn = cam.proj(X, 1.42, Z - 0.86)
    if hc is not None:
        k = F / hc[2]
        sy = abs(math.sin(cam.pitch))
        c.drawPath(oval(hc[0], hc[1], 0.11 * k, 0.11 * k * sy + 0.001), paint(wc))
        if bn is not None: c.drawPath(oval(bn[0], bn[1], 0.07 * k, 0.07 * k * sy + 0.001), paint(mix(wc, P["l5"], 0.4)))
    for s in (-1, 1):
        wob = 0.05 * math.sin(t * 8 + seed + s)
        arm = _quad(cam, [(X + s * 0.2, 0.95, Z - 0.7), (X + s * 0.2 + 0.07, 0.95, Z - 0.7),
                          (X + s * 0.1 + 0.05 + wob, 0.8, Z - 0.1), (X + s * 0.1 + wob, 0.8, Z - 0.1)])
        if arm is not None: c.drawPath(arm, paint(wc))
    if alpha < 1: c.restore()
    c.restore()


def draw_wall(c, cam, lamp_fn):
    body = None
    for k in range(N_PANELS):
        x0 = panel_x(k)
        q = _quad(cam, [(x0, 0, WALL_Z), (x0 + PANEL_W, 0, WALL_Z), (x0 + PANEL_W, PANEL_H, WALL_Z), (x0, PANEL_H, WALL_Z)])
        if q is None: continue
        c.drawPath(q, paint(P["l5"]))
        cor = _quad(cam, [(x0 - 0.03, PANEL_H, WALL_Z), (x0 + PANEL_W + 0.03, PANEL_H, WALL_Z), (x0 + PANEL_W + 0.03, PANEL_H + 0.12, WALL_Z),
                          (x0 - 0.03, PANEL_H + 0.12, WALL_Z)])
        if cor is not None: c.drawPath(cor, paint(P["l5"]))
        pb = _quad(cam, [(x0 + 0.08, 0.35, WALL_Z), (x0 + PANEL_W - 0.08, 0.35, WALL_Z), (x0 + PANEL_W - 0.08, 1.05, WALL_Z), (x0 + 0.08, 1.05, WALL_Z)])
        if pb is not None: c.drawPath(pb, paint(mix(P["l5"], P["l4"], 0.35)))
        for r in range(LAMP_ROWS):
            for qq in range(LAMP_COLS):
                lx = x0 + 0.14 + qq * 0.2; ly = PANEL_H - 0.3 - r * 0.2
                v = clamp01(lamp_fn(k, r, qq))
                rq = _quad(cam, [(lx, ly, WALL_Z), (lx + 0.11, ly, WALL_Z), (lx + 0.11, ly + 0.11, WALL_Z), (lx, ly + 0.11, WALL_Z)])
                if rq is None: continue
                c.drawPath(rq, paint(mix(mix(P["l5"], P["l4"], 0.55), P["lamp"], v)))
    # cables looping between panels
    cp = paint(mix(P["l5"], "#000000", 0.2), style="stroke", width=max(1.5, F / max(1.0, WALL_Z - cam.z) * 0.035), cap="round")
    for k in range(N_PANELS - 1):
        x0 = panel_x(k)
        a = cam.proj(x0 + 0.3, 0.9, WALL_Z - 0.05); b = cam.proj(x0 + PANEL_W + PANEL_GAP + 0.6, 0.95, WALL_Z - 0.05)
        m = cam.proj(x0 + PANEL_W * 0.95, 0.45 + 0.08 * (k % 3), WALL_Z - 0.05)
        if a and b and m:
            pth = skia.Path(); pth.moveTo(a[0], a[1]); pth.quadTo(2 * m[0] - (a[0] + b[0]) / 2, 2 * m[1] - (a[1] + b[1]) / 2, b[0], b[1])
            c.drawPath(pth, cp)
