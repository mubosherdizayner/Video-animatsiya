# Camera + environments (street, yard) built from layered flat silhouettes.
import math
import numpy as np
import skia
from style import *
from figures import *

class Cam:
    def __init__(self, x=0.0, y=0.0, z=1.0, rot=0.0, fx=W / 2, fy=H / 2, sx=0.0, sy=0.0):
        self.x, self.y, self.z, self.rot, self.fx, self.fy, self.sx, self.sy = x, y, z, rot, fx, fy, sx, sy
    def push(self, cv, d=1.0):
        cv.save()
        cv.translate(self.fx + self.sx, self.fy + self.sy)
        if self.rot: cv.rotate(self.rot)
        cv.scale(self.z, self.z)
        cv.translate(-self.fx - self.x * d, -self.fy - self.y * d)
    def to_screen(self, p, d=1.0):
        x = p[0] - self.x * d - self.fx; y = p[1] - self.y * d - self.fy
        x *= self.z; y *= self.z
        if self.rot:
            a = self.rot * D2R; x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        return (x + self.fx + self.sx, y + self.fy + self.sy)
    def to_world(self, sp, d=1.0):
        x = sp[0] - self.fx - self.sx; y = sp[1] - self.fy - self.sy
        if self.rot:
            a = -self.rot * D2R; x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        return (x / self.z + self.fx + self.x * d, y / self.z + self.fy + self.y * d)

# ------------------------------------------------------------------ shared pieces
def wall_band(cv, P, x0, x1, top, base, c=None, cap=True, seed=0):
    c = c or P["L3"]
    cv.drawRect(skia.Rect.MakeLTRB(x0, top, x1, base + 4), paint(c))
    if cap: cv.drawRect(skia.Rect.MakeLTRB(x0, top - 7, x1, top + 6), paint(P["L4"]))
    cv.drawRect(skia.Rect.MakeLTRB(x0, base - 18, x1, base + 4), paint(P["L4"], 0.55))
    rs = np.random.RandomState(seed)
    x = x0
    while x < x1:   # faint plaster patches
        w = rs.uniform(60, 160); h = rs.uniform(25, 70); y = rs.uniform(top + 20, base - 60)
        cv.drawPath(rrect(x, y, x + w, y + h, 10), paint(P["L4"], 0.10))
        x += rs.uniform(110, 260)

def ground_strip(cv, P, x0, x1, top, c, seed=0, tufts=True, bottom=4200):
    rs = np.random.RandomState(seed)
    xs = np.arange(x0, x1 + 8, 8)
    ys = top + 10 * fbm1(xs / 70.0, seed, 3)
    pts = [(x0, bottom)] + list(zip(xs.tolist(), ys.tolist())) + [(x1, bottom)]
    cv.drawPath(poly(pts), paint(c))
    if tufts:
        x = x0
        while x < x1:
            n = rs.randint(3, 7); base = top + 10 * float(fbm1(np.array([x / 70.0]), seed, 3)[0]) + 4
            for k in range(n):
                hgt = rs.uniform(14, 42); lean = rs.uniform(-10, 10)
                bx = x + k * rs.uniform(4, 8)
                cv.drawPath(poly([(bx - 3.5, base), (bx + lean, base - hgt), (bx + 3.5, base)]), paint(c))
            if rs.rand() < 0.35:
                r = rs.uniform(8, 18); cv.drawPath(ell(x + 30, base + 2, r * 1.4, r), paint(c))
            x += rs.uniform(60, 170)

def string_lights(cv, pts, t, c, n_per=7, sag=26, alpha=1.0, glow_a=0.0, seed=0, r=3.2, line_c=None):
    rs = np.random.RandomState(seed)
    for (a, b) in zip(pts, pts[1:]):
        path = skia.Path(); path.moveTo(*a)
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + sag * 2)
        path.quadTo(*mid, *b)
        if line_c is not None: cv.drawPath(path, paint(line_c, 0.8, stroke=1.4))
        for k in range(1, n_per + 1):
            u = k / (n_per + 1)
            x = (1 - u) ** 2 * a[0] + 2 * u * (1 - u) * mid[0] + u * u * b[0]
            y = (1 - u) ** 2 * a[1] + 2 * u * (1 - u) * mid[1] + u * u * b[1]
            tw = 0.62 + 0.38 * math.sin(t * rs.uniform(2.0, 4.5) + rs.uniform(0, 6.28))
            if glow_a > 0: cv.drawCircle(x, y, r * 3.2, paint(c, glow_a * tw, blur=r * 2.0))
            cv.drawCircle(x, y, r, paint(c, alpha * tw))

def tent(cv, x, base, P, t, lights=True, light_alpha=1.0, glow_a=0.0, c=None):
    c = c or P["mid"]
    w = 430; h = 300
    pk = [(x - w * 0.27, base - h), (x + w * 0.23, base - h - 16)]
    body = poly([(x - w / 2, base), (x - w / 2, base - h * 0.5), pk[0], (x - w * 0.02, base - h * 0.6),
                 pk[1], (x + w / 2, base - h * 0.5), (x + w / 2, base)])
    fill(cv, body, c)
    for pk_ in pk:
        cv.drawRect(skia.Rect.MakeLTRB(pk_[0] - 2.5, pk_[1] - 40, pk_[0] + 2.5, pk_[1]), paint(c))
        cv.drawPath(poly([(pk_[0], pk_[1] - 40), (pk_[0] + 22, pk_[1] - 33), (pk_[0], pk_[1] - 26)]), paint(c))
    poles = [x - w / 2 - 95, x + w / 2 + 85]
    for px in poles:
        cv.drawRect(skia.Rect.MakeLTRB(px - 3, base - h * 0.72, px + 3, base), paint(c))
    for k in range(12):
        xx = x - w / 2 + (k + 0.5) * w / 12
        cv.drawCircle(xx, base - h * 0.5 + 2, w / 24, paint(c))
    if lights:
        chains = [[(poles[0], base - h * 0.72), (pk[0][0], pk[0][1] - 40)],
                  [(pk[0][0], pk[0][1] - 40), (pk[1][0], pk[1][1] - 40)],
                  [(pk[1][0], pk[1][1] - 40), (poles[1], base - h * 0.72)],
                  [(poles[0], base - h * 0.72), (x - w * 0.02, base - h * 0.6), (poles[1], base - h * 0.72)]]
        for j, ch in enumerate(chains):
            string_lights(cv, ch, t, P["acc"], n_per=8, sag=16, alpha=light_alpha, glow_a=glow_a, seed=4 + j, r=4.2, line_c=c)

# ------------------------------------------------------------------ STREET (scenes 1, 12, 13)
GATE = (-120, 215)        # gate leaves x-span in layer d=0.85 coords
def street(cv, P, cam, t, u=0.0, sun=None, moon=None, star_a=0.0, win_a=0.0, birds=None, wind=0.0):
    # sky
    cam.push(cv, 0.0); sky(cv, P, y0=-100, y1=1000)
    if sun: draw_disc(cv, "sun", *sun, glow=0.6)
    stars(cv, t, star_a, ymax=820)
    if moon: draw_disc(cv, "moon", *moon, glow=0.9 * star_a + 0.2)
    if birds: birds(cv)
    cv.restore()
    # far hazy hills
    cam.push(cv, 0.03); fill(cv, ridge_path(-2500, 3500, 860, 170, 420, 7), P["haze"]); cv.restore()
    cam.push(cv, 0.06); fill(cv, ridge_path(-2500, 3500, 900, 95, 300, 3), P["L1"]); cv.restore()
    # L2: poplars + flat rooftops
    cam.push(cv, 0.16)
    rs = np.random.RandomState(21); x = -1800
    while x < 3200:
        if rs.rand() < 0.55:
            for k in range(rs.randint(2, 6)):
                poplar(cv, x + k * rs.uniform(26, 40), 935, rs.uniform(170, 300), rs.uniform(30, 46), P["L2"], sway=wind * 6 * math.sin(t * 1.3 + k))
            x += rs.uniform(150, 260)
        else:
            w = rs.uniform(90, 190); flat_house(cv, x, x + w, 935, rs.uniform(50, 110), P["L2"]); x += w + rs.uniform(10, 60)
    cv.restore()
    # mid: tent + houses + smoke
    cam.push(cv, 0.32)
    rs = np.random.RandomState(8); x = -1600
    while x < 3200:
        w = rs.uniform(110, 220)
        if not (600 < x < 1180): flat_house(cv, x, x + w, 985, rs.uniform(120, 175), P["mid"], chimney=x + w * 0.7 if rs.rand() < 0.3 else None)
        x += w + rs.uniform(30, 140)
    leafy_tree(cv, 1090, 985, 0.75, P["mid"], seed=2, sway=wind * 8 * math.sin(t))
    leafy_tree(cv, -380, 985, 0.7, P["mid"], seed=5)
    smoke(cv, 400, 820, t, P["smoke"], a=0.55, s=1.0, drift=22, seed=1)
    tent(cv, 880, 985, P, t, light_alpha=1.0, glow_a=0.35 * u + 0.12, c=mix(P["L1"], P["mid"], 0.35 + 0.4 * u))
    cv.restore()
    # houses behind the wall (windows above the wall line)
    cam.push(cv, 0.7)
    c = P["mid2"]
    for (x0, x1, top) in ((-700, -330, 760), (260, 640, 735), (1250, 1650, 770), (1950, 2350, 750), (-1400, -1000, 750)):
        cv.drawRect(skia.Rect.MakeLTRB(x0, top, x1, 1000), paint(c))
        cv.drawRect(skia.Rect.MakeLTRB(x0 - 16, top - 12, x1 + 16, top + 4), paint(P["L4"], 0.8))   # roof eave
        for wx in np.arange(x0 + 60, x1 - 60, 130):
            wx0, wx1, wy0, wy1 = wx, wx + 58, top + 50, top + 128
            cv.drawRect(skia.Rect.MakeLTRB(wx0 - 7, wy0 - 7, wx1 + 7, wy1 + 7), paint(P["L4"], 0.55))
            cv.drawRect(skia.Rect.MakeLTRB(wx0, wy0, wx1, wy1), paint(mix(P["L4"], c, 0.35)))
            if win_a > 0:
                glow(cv, (wx0 + wx1) / 2, (wy0 + wy1) / 2, 75, P["win"], 0.35 * win_a)
                cv.drawRect(skia.Rect.MakeLTRB(wx0, wy0, wx1, wy1), paint(P["win"], win_a))
            cv.drawRect(skia.Rect.MakeLTRB((wx0 + wx1) / 2 - 2.5, wy0, (wx0 + wx1) / 2 + 2.5, wy1), paint(P["L4"]))
            cv.drawRect(skia.Rect.MakeLTRB(wx0, (wy0 + wy1) / 2 - 2.5, wx1, (wy0 + wy1) / 2 + 2.5), paint(P["L4"]))
    cv.restore()
    # electricity pole + sagging wires
    cam.push(cv, 0.9)
    for px in (560, 1900, -800):
        cv.drawRect(skia.Rect.MakeLTRB(px - 7, 420, px + 7, 1206), paint(P["L4"]))
        cv.drawRect(skia.Rect.MakeLTRB(px - 46, 448, px + 46, 458), paint(P["L4"]))
    for dy_ in (0, 22):
        for a_, b_ in ((-800, 560), (560, 1900), (1900, 3240), (-2140, -800)):
            pth = skia.Path(); pth.moveTo(a_ + 40, 452 + dy_); pth.quadTo((a_ + b_) / 2, 560 + dy_, b_ - 40, 452 + dy_)
            cv.drawPath(pth, paint(P["L4"], 0.9, stroke=2.2))
    cv.restore()
    # street wall + gate
    cam.push(cv, 0.85)
    wall_band(cv, P, -2400, 3600, 905, 1205, seed=3)
    g0, g1 = GATE
    cv.drawRect(skia.Rect.MakeLTRB(g0 - 22, 790, g0, 1205), paint(P["L4"]))
    cv.drawRect(skia.Rect.MakeLTRB(g1, 790, g1 + 22, 1205), paint(P["L4"]))
    cv.drawPath(poly([(g0 - 52, 800), (g0 - 30, 760), (g1 + 30, 760), (g1 + 52, 800)]), paint(P["L5"]))
    cv.drawRect(skia.Rect.MakeLTRB(g0 - 40, 800, g1 + 40, 812), paint(P["L4"]))
    gm = (g0 + g1) / 2 - 10
    # left leaf (closed) with carved panels
    cv.drawRect(skia.Rect.MakeLTRB(g0, 812, gm, 1205), paint(P["L4"]))
    for r_ in range(3):
        for c_ in range(2):
            px0 = g0 + 16 + c_ * (gm - g0 - 16) / 2; px1 = px0 + (gm - g0 - 16) / 2 - 16
            py0 = 832 + r_ * 120; py1 = py0 + 100
            cv.drawPath(rrect(px0, py0, px1, py1, 6), paint(P["L5"], 0.45))
            cv.drawPath(rrect(px0 + 8, py0 + 8, px1 - 8, py1 - 8, 4), paint(P["L4"]))
    # right leaf open: dark doorway with a glimpse of the yard
    cv.drawRect(skia.Rect.MakeLTRB(gm, 812, g1, 1205), paint(P["L5"]))
    cv.drawRect(skia.Rect.MakeLTRB(gm + 18, 960, g1 - 14, 1160), paint(mix(P["L3"], P["L5"], 0.35)))
    if win_a > 0: cv.drawRect(skia.Rect.MakeLTRB(gm + 18, 960, g1 - 14, 1160), paint(P["win"], 0.22 * win_a))
    cv.drawRect(skia.Rect.MakeLTRB(gm, 1150, g1, 1205), paint(P["L5"]))
    cv.drawPath(poly([(g1, 812), (g1 + 30, 822), (g1 + 30, 1195), (g1, 1205)]), paint(P["L4"]))   # leaf swung out
    # lantern
    lx = gm
    cv.drawRect(skia.Rect.MakeLTRB(lx - 1.5, 812, lx + 1.5, 830), paint(P["L5"]))
    cv.drawPath(rrect(lx - 9, 828, lx + 9, 852, 4), paint(P["L5"]))
    if win_a > 0:
        glow(cv, lx, 842, 70, P["win"], 0.4 * win_a)
        cv.drawPath(rrect(lx - 6, 832, lx + 6, 849, 3), paint(P["win"], win_a))
    cv.restore()
    # road
    cam.push(cv, 1.0)
    cv.drawRect(skia.Rect.MakeLTRB(-2600, 1200, 3800, 1500), paint(P["road"]))
    cv.drawRect(skia.Rect.MakeLTRB(-2600, 1200, 3800, 1228), paint(P["road_d"]))
    for yb, cc, sd in ((1292, P["road_d"], 4), (1318, P["road_l"], 9), (1398, P["road_d"], 6), (1426, P["road_l"], 12)):
        xs = np.arange(-2600, 3800, 20)
        y_top = yb + 6 * fbm1(xs / 140.0, sd, 3) - 3
        y_bot = yb + 10 + 6 * fbm1(xs / 120.0, sd + 1, 3)
        cv.drawPath(poly(list(zip(xs.tolist(), y_top.tolist())) + list(zip(xs[::-1].tolist(), y_bot[::-1].tolist()))), paint(cc, 0.7))
    rs = np.random.RandomState(31)
    for k in range(160):
        x = rs.uniform(-2600, 3800); y = rs.uniform(1240, 1480)
        cv.drawPath(ell(x, y, rs.uniform(2, 6), rs.uniform(1.5, 3)), paint(P["road_d"], 0.8))
    cv.restore()

def branch(cv, P, x, y, s, t, wind=0.0, mirror=False, seed=4, c=None):
    """dark foreground mulberry branch hanging from the frame top"""
    c = c or P["L5"]
    rs = np.random.RandomState(seed)
    cv.save(); cv.translate(x, y); cv.scale(-s if mirror else s, s)
    sw = wind * 4 * math.sin(t * 1.7)
    pth = skia.Path(); pth.moveTo(40, -80); pth.cubicTo(-60, 40, -180, 90, -330 + sw, 230)
    cv.drawPath(pth, paint(c, stroke=16))
    pth2 = skia.Path(); pth2.moveTo(-120, 70); pth2.cubicTo(-150, 140, -170, 200, -175 + sw, 300)
    cv.drawPath(pth2, paint(c, stroke=8))
    for k in range(26):
        u_ = rs.uniform(0.15, 1.0)
        bx = -330 * u_ + rs.uniform(-40, 40) + sw * u_; by = 230 * u_ ** 0.9 + rs.uniform(-30, 50)
        a = rs.uniform(-60, 60) + 8 * math.sin(t * 2 + k) * (0.3 + wind)
        cv.save(); cv.translate(bx, by); cv.rotate(a)
        L = rs.uniform(26, 44)
        fill(cv, smooth([(0, 0), (L * 0.45, -L * 0.32), (L, 0), (L * 0.45, L * 0.32)], k=0.6), c)
        cv.restore()
    cv.restore()

def street_fg(cv, P, cam, t=0.0):
    cam.push(cv, 1.25); ground_strip(cv, P, -3000, 4200, 1486, P["L5"], seed=5); cv.restore()
    cam.push(cv, 1.4); branch(cv, P, 1120, -30, 1.25, t); cv.restore()

# ------------------------------------------------------------------ YARD, side view (scenes 2, 11-end)
SORI = dict(x0=200, x1=880, seat=1290)
def sori_back(cv, P, x0, x1, seat, s=1.0):
    c = P["L4"]
    cv.drawRect(skia.Rect.MakeLTRB(x0 + 10, seat - 78 * s, x1 - 10, seat - 70 * s), paint(c))
    for x in np.arange(x0 + 14, x1 - 8, 46 * s):
        cv.drawRect(skia.Rect.MakeLTRB(x - 3 * s, seat - 74 * s, x + 3 * s, seat), paint(c))
    for x in (x0 + 4, x1 - 4):
        cv.drawRect(skia.Rect.MakeLTRB(x - 6 * s, seat - 84 * s, x + 6 * s, seat), paint(c))
    cv.drawRect(skia.Rect.MakeLTRB(x0 + 6, seat - 10 * s, x1 - 6, seat + 2), paint(mix(P["L4"], P["L5"], 0.5)))   # rug

def sori_front(cv, P, x0, x1, seat, s=1.0, leg=110):
    c = P["L5"]
    cv.drawRect(skia.Rect.MakeLTRB(x0, seat, x1, seat + 28 * s), paint(c))
    for x in (x0 + 18 * s, (x0 + x1) / 2, x1 - 18 * s):
        cv.drawRect(skia.Rect.MakeLTRB(x - 11 * s, seat, x + 11 * s, seat + leg * s), paint(c))
    for x in (x0 + 4, x1 - 4):   # end railings
        cv.drawRect(skia.Rect.MakeLTRB(x - 6 * s, seat - 84 * s, x + 6 * s, seat), paint(c))
        cv.drawRect(skia.Rect.MakeLTRB(x - 10 * s if x < x1 - 10 else x - 40 * s, seat - 84 * s, x + 40 * s if x < x1 - 10 else x + 10 * s, seat - 76 * s), paint(c))

def hearth(cv, P, x, base, t, s=1.0, fire=1.0, smoke_a=0.5):
    """outdoor clay hearth (o'choq) with a qozon; fire + smoke"""
    c = P["L4"]
    fill(cv, smooth([(x - 70 * s, base), (x - 66 * s, base - 50 * s), (x - 40 * s, base - 62 * s), (x + 40 * s, base - 62 * s),
                     (x + 66 * s, base - 50 * s), (x + 70 * s, base)], k=0.4), c)
    # fire mouth
    fill(cv, rrect(x - 30 * s, base - 40 * s, x + 30 * s, base + 2, 14 * s), P["L5"])
    if fire > 0:
        for k in range(5):
            fx = x + (k - 2) * 11 * s
            hh = (20 + 12 * math.sin(t * (9 + k * 1.7) + k * 2.1) + 6 * math.sin(t * 23 + k)) * s
            fl = smooth([(fx - 7 * s, base - 2), (fx - 4 * s, base - hh * 0.55), (fx + math.sin(t * 7 + k) * 3 * s, base - hh),
                         (fx + 5 * s, base - hh * 0.5), (fx + 7 * s, base - 2)], k=0.5)
            fill(cv, fl, P["acc"], fire)
            fill(cv, ell(fx, base - 8 * s, 3.5 * s, hh * 0.25), P["sun0"], fire * 0.9)
        glow(cv, x, base - 20 * s, 90 * s, P["acc"], 0.28 * fire)
    # qozon (cauldron) + lid
    fill(cv, smooth([(x - 58 * s, base - 62 * s), (x - 48 * s, base - 96 * s), (x + 48 * s, base - 96 * s), (x + 58 * s, base - 62 * s),
                     (x, base - 52 * s)], k=0.35), P["L5"])
    fill(cv, smooth([(x - 52 * s, base - 96 * s), (x, base - 120 * s), (x + 52 * s, base - 96 * s)], k=0.5), P["L5"])
    fill(cv, ell(x, base - 122 * s, 7 * s, 4 * s), P["L5"])
    if smoke_a > 0: smoke(cv, x + 10 * s, base - 125 * s, t, P["smoke"], a=smoke_a, s=1.2 * s, drift=26, seed=3, rate=1.8, life=3.6)

def yard_side(cv, P, cam, t, sun=None, moon=None, star_a=0.0, win_a=0.0, birds=None, tau=None, fire=1.0, wind=0.0):
    tau = t if tau is None else tau
    cam.push(cv, 0.0); sky(cv, P, y0=-100, y1=1050)
    if sun: draw_disc(cv, "sun", *sun, glow=0.6)
    stars(cv, tau, star_a, ymax=900)
    if moon: draw_disc(cv, "moon", *moon[:3], alpha=moon[3] if len(moon) > 3 else 1.0, glow=0.9)
    if birds: birds(cv)
    cv.restore()
    cam.push(cv, 0.04); fill(cv, ridge_path(-2500, 3500, 960, 160, 380, 11), P["haze"]); cv.restore()
    cam.push(cv, 0.08); fill(cv, ridge_path(-2500, 3500, 1000, 70, 260, 12), P["L1"]); cv.restore()
    cam.push(cv, 0.14)
    rs = np.random.RandomState(41); x = -1500
    while x < 2800:
        if rs.rand() < 0.45:
            for k in range(rs.randint(2, 5)):
                poplar(cv, x + k * rs.uniform(26, 38), 1040, rs.uniform(170, 290), rs.uniform(30, 44), P["L2"])
            x += rs.uniform(140, 240)
        else:
            w = rs.uniform(100, 200); flat_house(cv, x, x + w, 1040, rs.uniform(60, 120), P["L2"]); x += w + rs.uniform(10, 60)
    cv.restore()
    cam.push(cv, 0.26)
    rs = np.random.RandomState(42); x = -1500
    while x < 2800:
        w = rs.uniform(130, 240); flat_house(cv, x, x + w, 1090, rs.uniform(110, 170), P["mid"]); x += w + rs.uniform(30, 120)
    cv.restore()
    # yard wall (far side) + the yard's own house + tree + hearth
    cam.push(cv, 0.45)
    wall_band(cv, P, -2000, 3000, 1040, 1160, c=P["mid2"], seed=6)
    cv.restore()
    cam.push(cv, 0.58)
    hx0, hx1, htop = 640, 1180, 840
    cv.drawRect(skia.Rect.MakeLTRB(hx0, htop, hx1, 1170), paint(P["L3"]))
    cv.drawRect(skia.Rect.MakeLTRB(hx0 - 26, htop - 16, hx1 + 26, htop + 6), paint(P["L4"]))
    cv.drawRect(skia.Rect.MakeLTRB(hx0 + 40, htop + 70, hx0 + 120, 1170), paint(P["L4"]))   # door
    wx0, wy0, wx1, wy1 = hx0 + 200, htop + 70, hx0 + 300, htop + 170
    cv.drawRect(skia.Rect.MakeLTRB(wx0 - 9, wy0 - 9, wx1 + 9, wy1 + 9), paint(P["L4"]))
    cv.drawRect(skia.Rect.MakeLTRB(wx0, wy0, wx1, wy1), paint(mix(P["L4"], P["L3"], 0.4)))
    if win_a > 0:
        glow(cv, (wx0 + wx1) / 2, (wy0 + wy1) / 2, 110, P["win"], 0.4 * win_a)
        cv.drawRect(skia.Rect.MakeLTRB(wx0, wy0, wx1, wy1), paint(P["win"], win_a))
    cv.drawRect(skia.Rect.MakeLTRB((wx0 + wx1) / 2 - 3, wy0, (wx0 + wx1) / 2 + 3, wy1), paint(P["L4"]))
    cv.drawRect(skia.Rect.MakeLTRB(wx0, (wy0 + wy1) / 2 - 3, wx1, (wy0 + wy1) / 2 + 3), paint(P["L4"]))
    leafy_tree(cv, 150, 1170, 1.35, P["L4"], seed=3, sway=wind * 10 * math.sin(tau * 1.4) + 3 * math.sin(tau * 0.9))
    hearth(cv, P, 520, 1170, tau, s=0.8, fire=fire, smoke_a=0.45)
    cv.restore()
    cam.push(cv, 1.0)
    cv.drawRect(skia.Rect.MakeLTRB(-2600, 1160, 3800, 4200), paint(P["earth"]))
    rs = np.random.RandomState(9)
    for k in range(40):
        x = rs.uniform(-1500, 2600); y = rs.uniform(1190, 1500); w = rs.uniform(60, 220)
        cv.drawPath(ell(x, y, w, w * 0.12), paint(P["earth_d"], 0.6))
    cv.restore()

def yard_fg(cv, P, cam, t, vine=True):
    cam.push(cv, 1.25); ground_strip(cv, P, -3000, 4200, 1500, P["L5"], seed=8); cv.restore()
    if vine:
        cam.push(cv, 1.4); branch(cv, P, -60, -40, 1.2, t, mirror=True, seed=7); cv.restore()

# ------------------------------------------------------------------ props for the CTA
def paper_plane(cv, x, y, s, ang, c, a=1.0):
    cv.save(); cv.translate(x, y); cv.rotate(ang); cv.scale(s, s)
    fill(cv, poly([(26, 0), (-22, -17), (-10, 1)]), c, a)
    fill(cv, poly([(26, 0), (-10, 1), (-16, 13)]), mix(c, (0.1, 0.1, 0.12), 0.28), a)
    fill(cv, poly([(26, 0), (-16, 13), (-6, 4)]), mix(c, (1, 1, 1), 0.15), a)
    cv.restore()

def repost_icon(cv, x, y, r, ang, c, a=1.0, glow_a=0.0):
    cv.save(); cv.translate(x, y); cv.rotate(ang); cv.scale(-1, 1)   # arrows run counter-clockwise
    if glow_a > 0: cv.drawCircle(0, 0, r * 1.5, paint(c, glow_a, blur=r * 0.6))
    sw = r * 0.27
    for k in range(2):
        cv.save(); cv.rotate(180 * k)
        pth = skia.Path(); pth.addArc(skia.Rect.MakeLTRB(-r, -r, r, r), 200, 125)
        cv.drawPath(pth, paint(c, a, stroke=sw, cap=skia.Paint.kButt_Cap))
        e = math.radians(325); ex, ey = r * math.cos(e), r * math.sin(e)
        tx, ty = -math.sin(e), math.cos(e)       # tangent (clockwise)
        nx, ny = math.cos(e), math.sin(e)
        L = r * 0.62
        fill(cv, poly([(ex + tx * L * 0.85, ey + ty * L * 0.85), (ex + nx * L * 0.62, ey + ny * L * 0.62), (ex - nx * L * 0.62, ey - ny * L * 0.62)]), c, a)
        cv.restore()
    cv.restore()
