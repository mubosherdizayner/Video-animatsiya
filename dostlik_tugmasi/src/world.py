# Environments (layered silhouettes, sky, sun / moon) and props, all flat shapes.
import math
import numpy as np
import skia
from gfx import *

DUSK = dict(sky0="#E9DEC6", sky1="#F4EDDF", sun0="#F2A55C", sun1="#E1742F",
            L=["#C6CEC9", "#AEBBB8", "#8C9FA1", "#56696D", "#2E3C40"], glow="#E58A3C")
NIGHT = dict(sky0="#1F2A3A", sky1="#3A4A5C", sun0="#EDE6D2", sun1="#EDE6D2",
             L=["#4A5A6E", "#36455A", "#283547", "#1A2433", "#10171F"], glow="#E7A05C")

def pal(n=0.0, warm=0.0):
    p = {k: (mix(DUSK[k], NIGHT[k], n) if isinstance(DUSK[k], str) else [mix(a, b, n) for a, b in zip(DUSK[k], NIGHT[k])]) for k in DUSK}
    if warm > 0:
        p["sky0"] = mix(p["sky0"], "#EFB27C", warm); p["sky1"] = mix(p["sky1"], "#F6C9A0", warm)
        p["L"] = [mix(c, "#B5785A", warm * (0.35 - 0.06 * i)) for i, c in enumerate(p["L"])]
        p["sun0"] = mix(p["sun0"], "#EE8E48", warm); p["sun1"] = mix(p["sun1"], "#D9612A", warm)
    p["n"] = n
    return p

# ---------------------------------------------------------------- camera with parallax
class Cam:
    def __init__(self, cx=540.0, cy=960.0, z=1.0, rot=0.0, shake=(0.0, 0.0)):
        self.cx, self.cy, self.z, self.rot, self.shake = cx, cy, z, rot, shake

class at_layer:
    """with at_layer(cv, cam, p): draw a layer whose parallax factor is p (0 = sky, 1 = action plane)"""
    def __init__(self, cv, cam, p=1.0): self.cv, self.cam, self.p = cv, cam, p
    def __enter__(self):
        cv, c, p = self.cv, self.cam, self.p
        cv.save()
        cv.translate(540 + c.shake[0], 960 + c.shake[1])
        if c.rot: cv.rotate(c.rot)
        z = 1 + (c.z - 1) * p
        cv.scale(z, z)
        cv.translate(-(540 + (c.cx - 540) * p), -(960 + (c.cy - 960) * p))
    def __exit__(self, *e): self.cv.restore()

# ---------------------------------------------------------------- sky, sun, moon, stars
def sky(cv, P, top=-1400, bot=3400, horizon=1150):
    vgrad(cv, (-2500, top, 3600, horizon), P["sky0"], P["sky1"])
    cv.drawRect(skia.Rect.MakeLTRB(-2500, horizon - 1, 3600, bot), paint(P["sky1"]))
    if top < -100:
        cv.drawRect(skia.Rect.MakeLTRB(-2500, -3000, 3600, top + 1), paint(P["sky0"]))

_BLOTS = [(-0.35, -0.30, 0.42, 0), (0.30, -0.10, 0.36, 1), (-0.10, 0.35, 0.40, 2), (0.42, 0.42, 0.30, 0),
          (-0.45, 0.25, 0.28, 1), (0.05, -0.05, 0.30, 2), (0.15, -0.55, 0.25, 1)]

def sun(cv, x, y, r, P, t=0.0, a=1.0):
    """big flat disc with soft watercolor blotches inside"""
    with layer_alpha(cv, a):
        glow(cv, x, y, r * 1.9, P["sun0"], 0.20)
        cv.save()
        cp = skia.Path(); cp.addCircle(x, y, r); cv.clipPath(cp, doAntiAlias=True)
        vgrad(cv, (x - r, y - r, x + r, y + r), P["sun0"], P["sun1"])
        tints = [mix(P["sun0"], "#FFFFFF", 0.22), mix(P["sun1"], "#B8461E", 0.18), mix(P["sun0"], P["sun1"], 0.5)]
        for k, (bx, by, br, ti) in enumerate(_BLOTS):
            dx = 0.04 * math.sin(t * 0.35 + k * 1.7); dy = 0.04 * math.cos(t * 0.3 + k)
            circle(cv, x + (bx + dx) * r, y + (by + dy) * r, br * r, tints[ti], 0.28, blur=r * 0.12)
        cv.restore()

def moon(cv, x, y, r, P, t=0.0, a=1.0):
    with layer_alpha(cv, a):
        glow(cv, x, y, r * 2.6, "#EDE6D2", 0.16)
        cv.save(); cp = skia.Path(); cp.addCircle(x, y, r); cv.clipPath(cp, doAntiAlias=True)
        circle(cv, x, y, r, "#EDE6D2")
        for k, (bx, by, br, ti) in enumerate(_BLOTS[:5]):
            circle(cv, x + bx * r, y + by * r, br * r, ["#DCD3BC", "#F6F1E4", "#D5CCB4"][ti], 0.45, blur=r * 0.14)
        cv.restore()

_STARS = np.random.default_rng(5).random((90, 4))
def stars(cv, t, a=1.0, x0=-300, x1=1400, y0=-600, y1=900):
    if a <= 0.01: return
    for k, (u, v, s, ph) in enumerate(_STARS):
        tw = 0.55 + 0.45 * math.sin(t * (1.3 + 2.2 * s) + ph * 6.28)
        circle(cv, x0 + u * (x1 - x0), y0 + v * (y1 - y0), 1.6 + 2.4 * s, "#EDE6D2", a * tw * (0.5 + 0.5 * s))

# ---------------------------------------------------------------- hills & grass
class Hill:
    """ridge y(x) = base - sum of gaussian bumps - small sines"""
    def __init__(self, base, bumps=(), seed=0, rough=10.0):
        self.base, self.bumps = base, list(bumps)
        r = np.random.default_rng(seed)
        self.waves = [(rough * r.uniform(0.5, 1.0), 2 * math.pi / r.uniform(160, 420), r.uniform(0, 6.28)) for _ in range(3)]
    def y(self, x):
        v = self.base
        for cx, w, h in self.bumps: v -= h * math.exp(-((x - cx) / w) ** 2)
        for a, k, ph in self.waves: v -= a * math.sin(k * x + ph)
        return v

def hill(cv, H_, c, x0=-1600, x1=2800, step=14, bottom=3600, a=1.0):
    pts = [(x, H_.y(x)) for x in range(int(x0), int(x1) + step, step)]
    pts += [(x1, bottom), (x0, bottom)]
    cv.drawPath(path(pts), paint(c, a))

def grass(cv, H_, c, t, x0, x1, step=20, hmin=16, hmax=40, wind=1.0, seed=1, a=1.0):
    r = np.random.default_rng(seed)
    pth = skia.Path()
    x = x0
    while x < x1:
        y = H_.y(x) + 3
        for b in range(3):
            bx = x + r.uniform(-7, 7); h = r.uniform(hmin, hmax); lean = r.uniform(-0.3, 0.3)
            sw = wind * (6 + 0.35 * h) * math.sin(t * 2.1 + bx * 0.017 + b) + wind * 0.25 * h
            pth.moveTo(bx - 3.2, y); pth.lineTo(bx + h * lean + sw, y - h); pth.lineTo(bx + 3.2, y); pth.close()
        x += step * r.uniform(0.7, 1.3)
    cv.drawPath(pth, paint(c, a))

def steppe_layers(cv, cam, P, t, near=None, mid=None, wind=1.0, sun_xy=None, sun_r=230, moon_xy=None, sky_h=1150,
                  extra_far=None, star_a=None):
    """sky + sun/moon + 4 hazy hill layers; returns nothing. `near` is drawn by the caller (action plane)."""
    with at_layer(cv, cam, 0.0):
        sky(cv, P, horizon=sky_h)
        sa = P["n"] if star_a is None else star_a
        if sa > 0.01: stars(cv, t, sa)
    if sun_xy is not None and P["n"] < 0.999:
        with at_layer(cv, cam, 0.06): sun(cv, sun_xy[0], sun_xy[1], sun_r, P, t, 1 - P["n"])
    if moon_xy is not None and P["n"] > 0.001:
        with at_layer(cv, cam, 0.06): moon(cv, moon_xy[0], moon_xy[1], 110, P, t, P["n"])
    L = P["L"]
    with at_layer(cv, cam, 0.15): hill(cv, Hill(1010, [(-200, 400, 60), (700, 500, 90), (1600, 380, 50)], 1, 14), L[0])
    if extra_far: extra_far(cv)
    with at_layer(cv, cam, 0.3): hill(cv, Hill(1065, [(200, 330, 70), (1100, 420, 80), (2000, 300, 40)], 2, 12), L[1])
    with at_layer(cv, cam, 0.5):
        h3 = mid or Hill(1130, [(-100, 300, 50), (650, 360, 80), (1500, 300, 60)], 3, 10)
        hill(cv, h3, L[2]); grass(cv, h3, L[2], t, -1200, 2400, 34, 8, 18, wind * 0.6, 3)
    with at_layer(cv, cam, 0.75):
        h4 = Hill(1205, [(300, 280, 55), (1150, 300, 70), (-500, 260, 40), (2000, 300, 50)], 4, 8)
        hill(cv, h4, L[3]); grass(cv, h4, L[3], t, -1400, 2600, 26, 10, 24, wind * 0.8, 4)

# ---------------------------------------------------------------- props
def pedestal(cv, x, y, s, c, top_c=None):
    """short dark stone pedestal; (x, y) = ground centre; returns top-centre y"""
    w0, w1, h = 150 * s, 118 * s, 128 * s
    poly(cv, [(x - w0 / 2, y + 4), (x + w0 / 2, y + 4), (x + w1 / 2, y - h), (x - w1 / 2, y - h)], c)
    rrect(cv, x - w1 / 2 - 12 * s, y - h - 16 * s, w1 + 24 * s, 20 * s, 6 * s, top_c or mix(c, "#FFFFFF", 0.08))
    return y - h - 16 * s

def button(cv, x, y, s, t, glow_a=1.0, press=0.0, pulse=True):
    """big round red button sitting on (x, y); press 0..1 sinks it"""
    k = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 1.1) if pulse else 0.6
    if glow_a > 0:
        glow(cv, x, y - 30 * s, (150 + 40 * k) * s, "#E58A3C", (0.55 + 0.35 * k) * glow_a)
    rrect(cv, x - 70 * s, y - 22 * s, 140 * s, 24 * s, 10 * s, "#7E3A2E")          # ring/base
    h = (44 - 30 * press) * s
    poly(cv, [(x - 56 * s, y - 14 * s), (x + 56 * s, y - 14 * s), (x + 56 * s, y - 14 * s - h), (x - 56 * s, y - 14 * s - h)], "#A9432F")
    ellipse(cv, x, y - 14 * s - h, 56 * s, 22 * s, "#C8553D")
    ellipse(cv, x - 16 * s, y - 18 * s - h, 22 * s, 7 * s, "#D9735A", 0.8)
    return y - 14 * s - h

CASH = "#80A287"; CASH_D = "#6F9077"; CASH_EDGE = "#D7E6D2"; CASH_FACE = "#B3CDB0"; CASH_INK = "#4E6B55"

def cash_stack(cv, x, y, s, n, t=0.0, seed=0):
    """n cash bundles stacked; (x, y) = bottom centre. Light dollar-green notes, paper edges, gold band with '$'
    (the green stays less saturated than the hero's chapan; the eye-catch comes from value, gold and sparkle)."""
    bw, bh = 128 * s, 24 * s
    for i in range(n):
        yy = y - (i + 1) * (bh + 2 * s)
        off = ((i * 37 + seed * 13) % 11 - 5) * s
        x0 = x - bw / 2 + off
        rrect(cv, x0, yy, bw, bh, 4 * s, CASH if i % 2 == 0 else CASH_D)
        for j in (1, 2):
            line(cv, [(x0 + 5 * s, yy + j * bh / 3), (x0 + bw - 5 * s, yy + j * bh / 3)], CASH_EDGE, 1.6 * s, 0.6)
        rrect(cv, x0 + 3 * s, yy + 2 * s, bw - 6 * s, 3 * s, 1.5 * s, CASH_EDGE, 0.75)          # top paper edge
        rrect(cv, x - 15.5 * s + off, yy - 1 * s, 31 * s, bh + 2 * s, 3.5 * s, CASH_EDGE)     # cream rim keeps gold off the green
        rrect(cv, x - 13 * s + off, yy - 1 * s, 26 * s, bh + 2 * s, 3 * s, "#C7A548")        # gold band
        text(cv, "$", x + off, yy + bh / 2, bh * 0.72, "#7A6424")
    if n > 0:
        # the top note shows its face: oval emblem + corner marks
        yy = y - n * (bh + 2 * s); off = (((n - 1) * 37 + seed * 13) % 11 - 5) * s
        ellipse(cv, x - 36 * s + off, yy + bh / 2, 13 * s, 8 * s, CASH_FACE)
        ellipse(cv, x + 36 * s + off, yy + bh / 2, 13 * s, 8 * s, CASH_FACE)

def banknote(cv, x, y, s, rot, flip, a=1.0):
    """single flat note fluttering (flip = x-scale from turning in the air)"""
    with xf(cv, x, y, s, rot, sx=s * max(0.15, abs(flip))):
        with layer_alpha(cv, a):
            rrect(cv, -60, -28, 120, 56, 6, CASH if flip >= 0 else CASH_D)
            cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(-52, -20, 52, 20), 4, 4), paint(CASH_EDGE, 0.8, stroke=3))
            ellipse(cv, 0, 0, 16, 16, CASH_FACE)
            text(cv, "$", 0, 0, 24, CASH_INK)
            rrect(cv, -46, -6, 12, 12, 3, CASH_EDGE); rrect(cv, 34, -6, 12, 12, 3, CASH_EDGE)

def sparkle(cv, x, y, r, a=1.0, c="#FFF6DC"):
    if a <= 0.01 or r <= 0.5: return
    k = r * 0.22
    poly(cv, [(x, y - r), (x + k, y - k), (x + r, y), (x + k, y + k), (x, y + r), (x - k, y + k), (x - r, y), (x - k, y - k)], c, a)

def coin(cv, x, y, r, spin=0.0, a=1.0):
    """gold coin with rim, embossed '$' and a glint when it faces the camera"""
    cs = math.cos(spin); sx = max(0.12, abs(cs))
    with xf(cv, x, y, 1, 0, None):
        ellipse(cv, 0, 0, r * sx, r, "#A88A38", a)
        ellipse(cv, -r * 0.06 * sx, -r * 0.04, r * sx * 0.88, r * 0.88, "#D6B54F", a)
        if sx > 0.45:
            with xf(cv, 0, 0, 1, 0, sx=sx):
                text(cv, "$", 0, 0, r * 1.05, "#A88A38", a * 0.85)
        ellipse(cv, -r * 0.35 * sx, -r * 0.42, r * 0.22 * sx, r * 0.13, "#F6E7A8", a * 0.9)
    if sx > 0.9: sparkle(cv, x + r * 0.5, y - r * 0.6, r * 0.7 * (sx - 0.9) * 10, a)

def chain(cv, pts, s, c="#C7A548", a=1.0):
    """flat gold chain along a polyline: alternating flat / edge-on links"""
    total = 0; segs = []
    for p, q in zip(pts[:-1], pts[1:]):
        L = math.hypot(q[0] - p[0], q[1] - p[1]); segs.append((p, q, L)); total += L
    step = 17 * s; d = 0.0; i = 0
    while d < total:
        acc = 0
        for p, q, L in segs:
            if acc + L >= d:
                u = (d - acc) / L if L else 0; x = p[0] + (q[0] - p[0]) * u; y = p[1] + (q[1] - p[1]) * u
                ang = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])); break
            acc += L
        with xf(cv, x, y, 1, ang):
            if i % 2 == 0:
                cv.drawOval(skia.Rect.MakeLTRB(-12 * s, -7 * s, 12 * s, 7 * s), paint(c, a, stroke=4.5 * s))
            else:
                rrect(cv, -12 * s, -2.5 * s, 24 * s, 5 * s, 2.5 * s, mix(c, "#8C7430", 0.35), a)
        d += step; i += 1

def sag(p, q, depth, n=24):
    return [(p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n + depth * math.sin(math.pi * k / n)) for k in range(n + 1)]

def phone_plate(cv, x, y, w, h, a=1.0, scale=1.0):
    """floating cream rounded plate (app content stand-in); returns local drawing frame origin"""
    with xf(cv, x, y, scale):
        with layer_alpha(cv, a):
            plate(cv, -w / 2, -h / 2, w, h, 34, 0.85)

def strike(cv, x0, y0, x1, y1, prog, w=12, a=1.0):
    if prog <= 0: return
    line(cv, [(x0, y0), (x0 + (x1 - x0) * prog, y0 + (y1 - y0) * prog)], "#C8553D", w, a)

def avatar(cv, x, y, r, letter=None, hero=False, a=1.0):
    circle(cv, x, y, r, "#8C9FA1" if not hero else "#E9DEC6", a)
    if letter: text(cv, letter, x, y, r * 1.05, "#F4EDDF", a)
    if hero:
        cv.save(); cp = skia.Path(); cp.addCircle(x, y, r); cv.clipPath(cp, doAntiAlias=True)
        from hero import draw_person, HERO
        k = 1.25 * r / 238.0
        draw_person(cv, x - 20 * k, y + 0.12 * r + 1320 * k, k, HERO, turn=0.0, alpha=a)
        cv.restore()

def waveform(cv, x, y, w, h, c, t=0.0, a=1.0, n=22):
    bw = w / n
    for k in range(n):
        v = 0.25 + 0.75 * abs(math.sin(k * 1.7) * math.cos(k * 0.6 + 0.4))
        hh = h * v
        rrect(cv, x + k * bw + bw * 0.2, y - hh / 2, bw * 0.6, hh, bw * 0.3, c, a)

def bubble(cv, x, y, w, h, a=1.0, scale=1.0, tail=-1, c=CREAM, ca=0.92):
    """speech bubble centred at x,y; tail toward bottom-left (-1) / bottom-right (+1) / none (0)"""
    with xf(cv, x, y, scale):
        with layer_alpha(cv, a):
            rrect(cv, -w / 2, -h / 2, w, h, min(h / 2, 34), c, ca)
            if tail:
                tx = -w * 0.22 * (-tail)
                poly(cv, [(tx - 16, h / 2 - 2), (tx + 16, h / 2 - 2), (tx - 6 * tail * -1 + 0, h / 2 + 24)], c, ca)

def typing_dots(cv, x, y, t, a=1.0, s=1.0):
    for k in range(3):
        ph = (t * 2.2 - k * 0.22) % 1.0
        b = math.sin(ph * math.pi) if ph < 1 else 0
        circle(cv, x + (k - 1) * 30 * s, y - 8 * s * b, 10 * s, "#1F292C", a * (0.35 + 0.65 * b))

def repost_icon(cv, x, y, r, c="#E58A3C", a=1.0, rot=0.0, w=None):
    """two curved arrows forming a circle"""
    w = w or r * 0.28
    with xf(cv, x, y, 1, rot):
        with layer_alpha(cv, a):
            for k in range(2):
                cv.save(); cv.rotate(180 * k)
                rect = skia.Rect.MakeLTRB(-r, -r, r, r)
                p = skia.Path(); p.addArc(rect, 200, 120)
                cv.drawPath(p, paint(c, 1, stroke=w))
                ang = math.radians(320); hx, hy = r * math.cos(ang), r * math.sin(ang)
                tx, ty = -math.sin(ang), math.cos(ang)  # tangent (clockwise)
                nx, ny = math.cos(ang), math.sin(ang)
                hl = w * 1.5
                poly(cv, [(hx + tx * hl * 1.25, hy + ty * hl * 1.25), (hx + nx * hl, hy + ny * hl), (hx - nx * hl, hy - ny * hl)], c)
                cv.restore()

def padlock(cv, x, y, s, c="#2E3C40", shackle_open=0.0):
    sh = skia.Path(); r = 26 * s
    oy = -14 * s * shackle_open
    sh.addArc(skia.Rect.MakeLTRB(x - r, y - 64 * s + oy, x + r, y - 12 * s + oy), 180, 180)
    cv.drawPath(sh, paint(c, 1, stroke=12 * s, cap="butt"))
    line(cv, [(x - r, y - 38 * s + oy), (x - r, y - 14 * s)], c, 12 * s, cap="butt")
    line(cv, [(x + r, y - 38 * s + oy), (x + r, y - 18 * s + oy)], c, 12 * s, cap="butt")
    rrect(cv, x - 40 * s, y - 20 * s, 80 * s, 62 * s, 10 * s, c)
    circle(cv, x, y + 6 * s, 7 * s, "#C7A548")
    poly(cv, [(x - 3 * s, y + 8 * s), (x + 3 * s, y + 8 * s), (x + 2 * s, y + 24 * s), (x - 2 * s, y + 24 * s)], "#C7A548")

def paper_plane(cv, x, y, s, rot=0.0, fold=1.0, c="#E58A3C", a=1.0):
    """fold 0 = flat square sheet, 1 = folded plane (side view, nose to +x)"""
    sheet = [(-46, -46), (46, -46), (46, 46), (-46, 46)]
    wing = [(-58, -6), (62, 0), (-58, -40), (-40, -6)]
    body = [(-58, -6), (62, 0), (-50, 14)]
    with xf(cv, x, y, s, rot):
        with layer_alpha(cv, a):
            f = smooth(fold)
            if f < 0.999:
                pts = [(sx + (wx - sx) * f, sy + (wy - sy) * f) for (sx, sy), (wx, wy) in zip(sheet, wing)]
                poly(cv, pts, mix(c, "#F2B07A", 0.25 * (1 - f)))
                if f > 0.3:
                    poly(cv, body, mix(c, "#B8642A", 0.45), smooth((f - 0.3) / 0.7))
            else:
                poly(cv, body, mix(c, "#B8642A", 0.45))
                poly(cv, wing, c)

# ---------------------------------------------------------------- mahalla / town pieces
def wall(cv, x0, x1, top, bot, c, seed=0):
    r = np.random.default_rng(seed); pts = []
    x = x0
    while x < x1:
        pts.append((x, top + r.uniform(-4, 4))); x += 60
    pts.append((x1, top))
    p = skia.Path(); p.moveTo(x0, bot)
    for q in pts: p.lineTo(*q)
    p.lineTo(x1, bot); p.close()
    cv.drawPath(p, paint(c))
    rrect(cv, x0 - 6, top - 12, x1 - x0 + 12, 16, 8, c)

def gate(cv, x, bot, w, h, c, plank, glow_a=0.0):
    p = skia.Path(); p.moveTo(x - w / 2, bot); p.lineTo(x - w / 2, bot - h + w * 0.25)
    p.quadTo(x, bot - h - w * 0.18, x + w / 2, bot - h + w * 0.25); p.lineTo(x + w / 2, bot); p.close()
    cv.drawPath(p, paint(c))
    line(cv, [(x, bot - h + 14), (x, bot)], plank, 5)
    for k in (-1, 1):
        for j in range(3):
            line(cv, [(x + k * (14 + j * w * 0.13), bot - h + w * 0.3), (x + k * (14 + j * w * 0.13), bot - 10)], plank, 3, 0.7)
        circle(cv, x + k * 10, bot - h * 0.45, 4, plank)

def house(cv, x, bot, w, h, c, roof_c=None, windows=(), win_c=None, win_a=0.0):
    rrect(cv, x, bot - h, w, h, 3, c)
    rrect(cv, x - 14, bot - h - 14, w + 28, 18, 4, roof_c or c)
    for (wx, wy, ww, wh) in windows:
        rrect(cv, x + wx, bot - h + wy, ww, wh, 4, mix(c, "#000000", 0.25))
        if win_a > 0:
            glow(cv, x + wx + ww / 2, bot - h + wy + wh / 2, ww * 2.2, win_c or "#E7A05C", 0.35 * win_a)
            rrect(cv, x + wx, bot - h + wy, ww, wh, 4, win_c or "#E7A05C", win_a)

def poplar(cv, x, bot, h, w, c, t=0.0, wind=1.0, seed=0):
    sw = wind * 6 * math.sin(t * 1.4 + seed)
    pts = [(x - 4, bot), (x - w * 0.42, bot - h * 0.25), (x - w * 0.5 + sw * 0.3, bot - h * 0.55),
           (x - w * 0.28 + sw * 0.7, bot - h * 0.85), (x + sw, bot - h), (x + w * 0.28 + sw * 0.7, bot - h * 0.85),
           (x + w * 0.5 + sw * 0.3, bot - h * 0.55), (x + w * 0.42, bot - h * 0.25), (x + 4, bot)]
    spoly(cv, pts, c)

def round_tree(cv, x, bot, r, c, trunk=None):
    line(cv, [(x, bot), (x, bot - r * 1.2)], trunk or c, r * 0.16, cap="butt")
    for dx, dy, rr in ((0, -1.6, 1.0), (-0.65, -1.2, 0.72), (0.65, -1.25, 0.75), (0, -2.2, 0.7)):
        circle(cv, x + dx * r, bot + dy * r, rr * r, c)

def dome_skyline(cv, x, bot, s, c):
    rrect(cv, x - 120 * s, bot - 150 * s, 240 * s, 150 * s, 2, c)
    ellipse(cv, x, bot - 150 * s, 95 * s, 110 * s, c)
    line(cv, [(x, bot - 255 * s), (x, bot - 290 * s)], c, 6 * s)
    rrect(cv, x + 170 * s, bot - 430 * s, 50 * s, 430 * s, 6 * s, c)
    rrect(cv, x + 160 * s, bot - 450 * s, 70 * s, 26 * s, 8 * s, c)
    ellipse(cv, x + 195 * s, bot - 452 * s, 30 * s, 24 * s, c)

def street_lamp(cv, x, bot, h, c, on=1.0, t=0.0):
    line(cv, [(x, bot), (x, bot - h)], c, 10, cap="butt")
    p = skia.Path(); p.moveTo(x, bot - h); p.quadTo(x + 10, bot - h - 40, x + 60, bot - h - 34)
    cv.drawPath(p, paint(c, 1, stroke=8))
    lx, ly = x + 64, bot - h - 22
    if on > 0:
        glow(cv, lx, ly + 10, 190, "#E7A05C", 0.55 * on)
    poly(cv, [(lx - 22, ly - 14), (lx + 22, ly - 14), (lx + 14, ly + 6), (lx - 14, ly + 6)], c)
    ellipse(cv, lx, ly + 8, 13, 6, mix("#5A5040", "#F4D9A8", on))

def suri(cv, x, bot, w, s, c, rail=True, top_view=0.0, mat=None):
    """so'ri: raised wooden platform with low rails; (x, bot) = ground under its front-left leg; returns seat y"""
    hgt = 120 * s; th = 22 * s
    for lx in (x + 14 * s, x + w - 26 * s):
        rrect(cv, lx, bot - hgt, 14 * s, hgt, 3, c)
    depth = top_view * 170 * s
    if depth > 0:
        poly(cv, [(x, bot - hgt), (x + w, bot - hgt), (x + w + depth * 0.25, bot - hgt - depth), (x + depth * 0.25, bot - hgt - depth)], mix(c, "#FFFFFF", 0.06))
        if mat: poly(cv, [(x + 30 * s, bot - hgt - 8 * s), (x + w - 30 * s, bot - hgt - 8 * s), (x + w - 30 * s + depth * 0.22, bot - hgt - depth + 18 * s), (x + 30 * s + depth * 0.22, bot - hgt - depth + 18 * s)], mat)
    rrect(cv, x, bot - hgt - th, w, th, 4, c)
    if rail:
        rh = 64 * s
        rrect(cv, x, bot - hgt - th - rh, 10 * s, rh, 3, c)
        rrect(cv, x + w - 10 * s, bot - hgt - th - rh, 10 * s, rh, 3, c)
        rrect(cv, x + depth * 0.25, bot - hgt - th - rh - depth, w, 9 * s, 3, c) if depth > 0 else None
        line(cv, [(x + 5 * s, bot - hgt - th - rh), (x + 5 * s + depth * 0.25, bot - hgt - th - rh - depth)], c, 8 * s) if depth > 0 else None
        for k in range(1, 5):
            px = x + k * w / 5
            if depth > 0: rrect(cv, px + depth * 0.25, bot - hgt - th - rh - depth, 6 * s, rh, 2, c)
    return bot - hgt - th

def bus_shelter(cv, x, bot, w, h, c, c2):
    rrect(cv, x - 20, bot - h - 26, w + 40, 26, 6, c)
    rrect(cv, x, bot - h, 14, h, 3, c); rrect(cv, x + w - 14, bot - h, 14, h, 3, c)
    rrect(cv, x + 14, bot - h + 30, w - 28, h * 0.62, 4, c2)
    rrect(cv, x + w * 0.12, bot - h * 0.34, w * 0.76, 14, 4, c)
    for lx in (x + w * 0.16, x + w * 0.84 - 10):
        rrect(cv, lx, bot - h * 0.34, 10, h * 0.34, 2, c)
    rrect(cv, x + w * 0.62, bot - h + 50, 90, 56, 8, mix(c2, "#F4EDDF", 0.25))

def bus(cv, x, bot, s, c, win):
    rrect(cv, x, bot - 230 * s, 620 * s, 200 * s, 26 * s, c)
    for k in range(6):
        rrect(cv, x + (40 + k * 92) * s, bot - 205 * s, 70 * s, 62 * s, 8 * s, win)
    for wx in (110, 480):
        circle(cv, x + wx * s, bot - 30 * s, 40 * s, mix(c, "#000000", 0.3))

def string_lights(cv, pts, t, n_per=7, sag_d=60, a=1.0, wire="#10171F"):
    bulbs = []
    for p, q in zip(pts[:-1], pts[1:]):
        sw = 6 * math.sin(t * 1.3 + p[0] * 0.01)
        curve = [(x, y + sw * math.sin(math.pi * k / 24)) for k, (x, y) in enumerate(sag(p, q, sag_d))]
        line(cv, curve, wire, 3)
        for k in range(1, n_per):
            u = k / n_per; i = int(u * 24)
            bulbs.append(curve[i])
    for k, (x, y) in enumerate(bulbs):
        f = 0.85 + 0.15 * math.sin(t * 3 + k * 1.3)
        glow(cv, x, y + 10, 34, "#E7A05C", 0.55 * f * a)
        circle(cv, x, y + 9, 7, "#F2C38A", a)

def chair(cv, x, bot, s, c):
    """side-view chair; back on the left; (x, bot) = ground under the front leg"""
    rrect(cv, x - 90 * s, bot - 110 * s, 100 * s, 14 * s, 4 * s, c)
    rrect(cv, x - 4 * s, bot - 110 * s, 10 * s, 110 * s, 3, c)
    rrect(cv, x - 90 * s, bot - 250 * s, 12 * s, 250 * s, 3, c)
    rrect(cv, x - 94 * s, bot - 252 * s, 24 * s, 76 * s, 6 * s, c)

def confetti(cv, t, t0, seed=9, n=60, a=1.0, x0=80, x1=1000, y0=-80, colors=("#E58A3C", "#C7A548", "#F4EDDF", "#8C9FA1")):
    if t < t0: return
    r = np.random.default_rng(seed); dt = t - t0
    for k in range(n):
        x = r.uniform(x0, x1); v = r.uniform(260, 520); ph = r.uniform(0, 6.28); dl = r.uniform(0, 0.4)
        if dt < dl: continue
        tt = dt - dl
        y = y0 + v * tt + r.uniform(-60, 60)
        xx = x + 30 * math.sin(tt * 3 + ph)
        with xf(cv, xx, y, 1, (tt * 300 + ph * 57) % 360, sx=abs(math.cos(tt * 5 + ph))):
            rrect(cv, -7, -12, 14, 24, 3, colors[k % len(colors)], a)
