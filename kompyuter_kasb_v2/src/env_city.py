# City environments: present-day street, the early-20th-century street that replaces it, the office facade.
# Each layer is a flat silhouette in the fixed morning palette; layers can sink / rise for era changes.
import math
import skia
from common import *
from style import P, HORIZON, stroke_path, rise

# ground lines
SIDE_FAR = (HORIZON, 1205.0)
ROAD = (1205.0, 1335.0)
CURB = (1335.0, 1347.0)
NEAR_BACK = 1352.0           # back edge of the near sidewalk (street furniture stands here)
HERO_Y = 1410.0              # hero feet on the near sidewalk

_C = {}


def cached(key, fn):
    if key not in _C: _C[key] = fn()
    return _C[key]


# ---------------------------------------------------------------- present-day skyline layers
def _towers():
    body = skia.Path(); glaze = skia.Path()
    x = -900; k = 0
    while x < 2700:
        w = 70 + 80 * hash01(k, 11); top = 650 + 260 * hash01(k, 12)
        body.addRect(skia.Rect.MakeLTRB(x, top, x + w, HORIZON + 60))
        r = hash01(k, 13)
        if r > 0.66:                                    # stepped crown
            body.addRect(skia.Rect.MakeLTRB(x + w * 0.2, top - 40, x + w * 0.8, top))
            body.addRect(skia.Rect.MakeLTRB(x + w * 0.45, top - 95, x + w * 0.55, top - 40))
        elif r > 0.4:                                   # slanted roof
            body.addPoly([skia.Point(x, top), skia.Point(x + w, top - 45), skia.Point(x + w, top)], True)
        for j in range(1, int(w // 18)):
            glaze.addRect(skia.Rect.MakeLTRB(x + j * 18, top + 12, x + j * 18 + 2, HORIZON + 60))
        x += w + 16 + 60 * hash01(k, 14); k += 1
    return body, glaze


def _blocks(seed, y_top0, y_var, wmin, wvar, gap, win_w, win_h, lit_p):
    body = skia.Path(); win = skia.Path(); lit = skia.Path()
    x = -900; k = 0
    while x < 2700:
        w = wmin + wvar * hash01(seed, k, 1); top = y_top0 + y_var * hash01(seed, k, 2)
        body.addRect(skia.Rect.MakeLTRB(x, top, x + w, HORIZON + 80))
        body.addRect(skia.Rect.MakeLTRB(x - 4, top - 8, x + w + 4, top + 2))
        nx = max(1, int((w - 16) // (win_w + 10))); ny = max(1, int((HORIZON - top - 20) // (win_h + 12)))
        for a in range(nx):
            for b in range(ny):
                wx = x + 12 + a * (w - 24) / nx; wy = top + 16 + b * (win_h + 12)
                rr = skia.Rect.MakeLTRB(wx, wy, wx + win_w, wy + win_h)
                (lit if hash01(seed, k, a, b) < lit_p else win).addRect(rr)
        x += w + gap * (0.5 + hash01(seed, k, 3)); k += 1
    return body, win, lit


def modern_layers():
    return cached("modern", lambda: dict(far=_towers(), mid=_blocks(3, 900, 120, 150, 90, 30, 14, 10, 0.0),
                                         near=_blocks(7, 985, 110, 170, 110, 26, 18, 14, 0.08)))


def draw_modern_far(c, dy=0.0):
    body, glaze = modern_layers()["far"]
    c.save(); c.translate(0, dy)
    c.drawPath(body, paint(P["l1"])); c.drawPath(glaze, paint(mix(P["l1"], P["l2"], 0.35)))
    c.restore()


def draw_blocks(c, key, colr, dy=0.0):
    body, win, lit = modern_layers()[key]
    c.save(); c.translate(0, dy)
    c.drawPath(body, paint(colr)); c.drawPath(win, paint(mix(colr, P["l4"], 0.22)))
    c.drawPath(lit, paint(P["glow"]))
    c.restore()


# ---------------------------------------------------------------- early-20th-century skyline layers
def _old_far():
    body = skia.Path()
    x = -900; k = 0
    while x < 2700:
        w = 90 + 70 * hash01(k, 21); top = 880 + 120 * hash01(k, 22)
        body.addRect(skia.Rect.MakeLTRB(x, top, x + w, HORIZON + 60))
        r = hash01(k, 23)
        if r < 0.35:                                     # pitched roof
            body.addPoly([skia.Point(x - 6, top), skia.Point(x + w / 2, top - 46), skia.Point(x + w + 6, top)], True)
        elif r < 0.55:                                   # chimneys
            for j in range(2):
                cx = x + w * (0.25 + 0.5 * j)
                body.addRect(skia.Rect.MakeLTRB(cx - 7, top - 58, cx + 7, top))
        elif r < 0.7:                                    # water tower on legs
            cx = x + w / 2
            body.addRect(skia.Rect.MakeLTRB(cx - 22, top - 70, cx + 22, top - 30))
            body.addPoly([skia.Point(cx - 26, top - 70), skia.Point(cx, top - 92), skia.Point(cx + 26, top - 70)], True)
            for s in (-1, 1): body.addRect(skia.Rect.MakeLTRB(cx + s * 16 - 2, top - 30, cx + s * 16 + 2, top))
        elif r < 0.8:                                    # clock tower
            cx = x + w / 2
            body.addRect(skia.Rect.MakeLTRB(cx - 20, top - 130, cx + 20, top))
            body.addPoly([skia.Point(cx - 24, top - 130), skia.Point(cx, top - 175), skia.Point(cx + 24, top - 130)], True)
        x += w + 10 + 40 * hash01(k, 24); k += 1
    return body


def _old_offices(seed, top0, var, floors_px, wmin, wvar):
    body = skia.Path(); win = skia.Path(); trim = skia.Path()
    x = -900; k = 0
    while x < 2700:
        w = wmin + wvar * hash01(seed, k); top = top0 + var * hash01(seed, k, 1)
        body.addRect(skia.Rect.MakeLTRB(x, top, x + w, HORIZON + 80))
        trim.addRect(skia.Rect.MakeLTRB(x - 6, top - 10, x + w + 6, top + 4))            # cornice
        nx = max(2, int(w // 30)); fl = int((HORIZON - top - 10) // floors_px)
        for b in range(fl):
            wy = top + 16 + b * floors_px
            trim.addRect(skia.Rect.MakeLTRB(x, wy - 8, x + w, wy - 5))                   # string course
            for a in range(nx):
                wx = x + 10 + a * (w - 20) / nx + ((w - 20) / nx - 13) / 2
                win.addRect(skia.Rect.MakeLTRB(wx, wy, wx + 13, wy + floors_px * 0.7))  # tall narrow windows
        x += w + 4 + 18 * hash01(seed, k, 2); k += 1
    return body, win, trim


def old_layers():
    return cached("old", lambda: dict(far=_old_far(), mid=_old_offices(5, 930, 60, 58, 150, 90),
                                      near=_old_offices(9, 975, 50, 66, 170, 100)))


def draw_old_far(c, dy=0.0):
    c.save(); c.translate(0, dy); c.drawPath(old_layers()["far"], paint(P["l1"])); c.restore()


def draw_old_offices(c, key, colr, dy=0.0, lit=0.0):
    body, win, trim = old_layers()[key]
    c.save(); c.translate(0, dy)
    c.drawPath(body, paint(colr)); c.drawPath(trim, paint(mix(colr, P["l4"], 0.3)))
    c.drawPath(win, paint(mix(mix(colr, P["l4"], 0.35), P["glow"], lit)))
    c.restore()


# ---------------------------------------------------------------- ground
def draw_ground(c, x0, x1, era=0.0, dash_dy=0.0, cobble=0.0):
    """era 0 = asphalt road with lane dashes, cobble 1 = cobbled road"""
    c.drawRect(skia.Rect.MakeLTRB(x0, SIDE_FAR[0], x1, SIDE_FAR[1]), paint(P["l2"]))
    c.drawRect(skia.Rect.MakeLTRB(x0, SIDE_FAR[1] - 4, x1, SIDE_FAR[1]), paint(P["l3"]))
    c.drawRect(skia.Rect.MakeLTRB(x0, ROAD[0], x1, ROAD[1]), paint(P["l3"]))
    if dash_dy < 200:
        c.save(); c.clipRect(skia.Rect.MakeLTRB(x0, ROAD[0], x1, ROAD[1]))
        dp = paint(P["l2"])
        x = x0 - (x0 % 150)
        while x < x1:
            c.drawRect(skia.Rect.MakeLTRB(x, 1266 + dash_dy, x + 80, 1274 + dash_dy), dp); x += 150
        c.restore()
    if cobble > 0:
        c.save(); c.clipRect(skia.Rect.MakeLTRB(x0, ROAD[0], x1, ROAD[1]))
        cp = paint(mix(P["l3"], P["l4"], 0.35), a=255 * cobble)
        rows = 7
        for r in range(rows):
            y = ROAD[0] + 8 + r * 18 + (1 - cobble) * 140
            off = (r % 2) * 14
            x = x0 - (x0 % 28) - off
            while x < x1:
                c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(x, y, x + 22, y + 11), 4, 4), cp); x += 28
        c.restore()
    c.drawRect(skia.Rect.MakeLTRB(x0, CURB[0], x1, CURB[1]), paint(P["l4"]))
    c.drawRect(skia.Rect.MakeLTRB(x0, CURB[1], x1, 2600), paint(P["l2"]))
    jp = paint(mix(P["l2"], P["l3"], 0.35))
    for y in (1395, 1470, 1580, 1730, 1900):
        c.drawRect(skia.Rect.MakeLTRB(x0, y, x1, y + 3), jp)
    for i, (ya, yb) in enumerate(((1347, 1395), (1398, 1470), (1473, 1580), (1583, 1730), (1733, 1900))):
        step = 110 + i * 60
        x = x0 - (x0 % step) + (i % 2) * step / 2
        while x < x1:
            c.drawRect(skia.Rect.MakeLTRB(x, ya, x + 3, yb), jp); x += step


def draw_planters(c, x0, x1, top=1790.0, W=0.0, era=0.0):
    """nearest ground layer: a low planter wall with a clipped hedge (modern) or a stone kerb with railings (old)"""
    dk = paint(P["l5"]); md = paint(P["l4"])
    if era < 0.5:
        hd = skia.Path()
        x = x0 - (x0 % 46)
        while x < x1:
            hd.addCircle(x, top - 6 + 6 * math.sin(x * 0.07), 34 + 6 * hash01(int(x), 3)); x += 46
        hd.addRect(skia.Rect.MakeLTRB(x0, top - 6, x1, top + 40))
        c.save(); c.translate(1.5 * math.sin(W * 1.3), 0); c.drawPath(hd, md); c.restore()
        c.drawRect(skia.Rect.MakeLTRB(x0, top + 30, x1, 2600), dk)
    else:
        c.drawRect(skia.Rect.MakeLTRB(x0, top + 30, x1, 2600), dk)
        c.drawRect(skia.Rect.MakeLTRB(x0, top - 40, x1, top - 32), dk)
        x = x0 - (x0 % 26)
        while x < x1:
            c.drawRect(skia.Rect.MakeLTRB(x, top - 34, x + 4, top + 30), dk)
            c.drawPath(poly([(x - 3, top - 40), (x + 2, top - 52), (x + 7, top - 40)]), dk); x += 26


# ---------------------------------------------------------------- street furniture (near layer)
def modern_lamp(c, x, base=NEAR_BACK, colr=None, s=1.0):
    p = paint(colr or P["l5"])
    c.drawRect(skia.Rect.MakeLTRB(x - 6 * s, base - 600 * s, x + 6 * s, base), p)
    c.drawRect(skia.Rect.MakeLTRB(x - 12 * s, base - 40 * s, x + 12 * s, base), p)
    a = skia.Path(); a.moveTo(x, base - 590 * s); a.quadTo(x + 10 * s, base - 640 * s, x + 80 * s, base - 640 * s)
    c.drawPath(stroke_path(a, 9 * s), p)
    c.drawPath(rrect(x + 50 * s, base - 650 * s, x + 128 * s, base - 632 * s, 6 * s), p)


def iron_lamp(c, x, base=NEAR_BACK, colr=None, s=1.0, glow=0.0):
    p = paint(colr or P["l5"])
    c.drawPath(rrect(x - 18 * s, base - 46 * s, x + 18 * s, base, 6 * s), p)          # plinth
    c.drawRect(skia.Rect.MakeLTRB(x - 10 * s, base - 70 * s, x + 10 * s, base - 44 * s), p)
    c.drawPath(poly([(x - 7 * s, base - 70 * s), (x + 7 * s, base - 70 * s), (x + 4 * s, base - 440 * s), (x - 4 * s, base - 440 * s)]), p)
    for yy in (180, 300):
        c.drawPath(rrect(x - 9 * s, base - yy * s - 6 * s, x + 9 * s, base - yy * s + 6 * s, 4 * s), p)
    c.drawRect(skia.Rect.MakeLTRB(x - 34 * s, base - 452 * s, x + 34 * s, base - 444 * s), p)   # cross bar
    for sgn in (-1, 1):
        sc = skia.Path(); sc.moveTo(x, base - 420 * s); sc.quadTo(x + sgn * 26 * s, base - 424 * s, x + sgn * 30 * s, base - 446 * s)
        c.drawPath(stroke_path(sc, 4 * s), p)
    # lantern
    c.drawPath(poly([(x - 20 * s, base - 456 * s), (x + 20 * s, base - 456 * s), (x + 26 * s, base - 516 * s), (x - 26 * s, base - 516 * s)]), p)
    c.drawPath(poly([(x - 14 * s, base - 462 * s), (x + 14 * s, base - 462 * s), (x + 18 * s, base - 508 * s), (x - 18 * s, base - 508 * s)]),
               paint(mix(P["l2"], P["glow"], glow)))
    c.drawRect(skia.Rect.MakeLTRB(x - 1.5 * s, base - 508 * s, x + 1.5 * s, base - 462 * s), p)
    c.drawPath(poly([(x - 32 * s, base - 514 * s), (x + 32 * s, base - 514 * s), (x, base - 548 * s)]), p)
    c.drawCircle(x, base - 554 * s, 6 * s, p)


def street_tree(c, x, base=NEAR_BACK, s=1.0, W=0.0, seed=1):
    c.drawPath(poly([(x - 9 * s, base), (x - 6 * s, base - 260 * s), (x + 6 * s, base - 260 * s), (x + 10 * s, base)]), paint(P["l5"]))
    cr = skia.Path()
    for i in range(9):
        a = 2 * math.pi * i / 9 + hash01(seed, i)
        cr.addCircle(x + 95 * s * math.cos(a) * (0.6 + 0.3 * hash01(seed, i, 2)),
                     base - 360 * s + 80 * s * math.sin(a) * (0.6 + 0.3 * hash01(seed, i, 3)), 62 * s)
    cr.addCircle(x, base - 360 * s, 85 * s)
    c.save(); c.rotate(0.8 * math.sin(W * 1.1 + seed), x, base - 260 * s)
    c.drawPath(cr, paint(P["l4"]))
    c.restore()
    c.drawRect(skia.Rect.MakeLTRB(x - 40 * s, base - 4, x + 40 * s, base + 4), paint(P["l3"]))     # tree grate


def bus_stop(c, x, base=NEAR_BACK, s=1.0):
    fr = paint(P["l4"]); dk = paint(P["l5"])
    c.drawRect(skia.Rect.MakeLTRB(x, base - 330 * s, x + 250 * s, base - 314 * s), dk)              # roof
    c.drawPath(poly([(x - 10 * s, base - 330 * s), (x + 260 * s, base - 330 * s), (x + 250 * s, base - 344 * s), (x, base - 344 * s)]), dk)
    for px in (6, 244):
        c.drawRect(skia.Rect.MakeLTRB(x + px * s - 5 * s, base - 316 * s, x + px * s + 5 * s, base), dk)
    c.drawRect(skia.Rect.MakeLTRB(x + 12 * s, base - 300 * s, x + 238 * s, base - 40 * s), paint(P["l3"], a=150))   # glass
    c.drawRect(skia.Rect.MakeLTRB(x + 12 * s, base - 300 * s, x + 238 * s, base - 292 * s), fr)
    c.drawRect(skia.Rect.MakeLTRB(x + 30 * s, base - 270 * s, x + 110 * s, base - 120 * s), fr)        # ad panel
    c.drawRect(skia.Rect.MakeLTRB(x + 40 * s, base - 96 * s, x + 220 * s, base - 84 * s), dk)          # bench
    for bx in (60, 200):
        c.drawRect(skia.Rect.MakeLTRB(x + bx * s - 3 * s, base - 86 * s, x + bx * s + 3 * s, base), dk)
    c.drawRect(skia.Rect.MakeLTRB(x + 286 * s, base - 300 * s, x + 292 * s, base), dk)                 # sign pole
    c.drawCircle(x + 289 * s, base - 300 * s, 26 * s, dk)
    c.drawCircle(x + 289 * s, base - 300 * s, 16 * s, fr)


# ---------------------------------------------------------------- people + pigeons
def walker(c, x, y, h, phase, colr, kind="coat", facing=1, alpha=1.0):
    """muted pedestrian silhouette walking; (x, y) = feet; h = height"""
    s = h / 300.0
    c.save(); c.translate(x, y); c.scale(s * facing, s)
    p = paint(colr, a=255 * alpha)
    sw = math.sin(phase)
    for sg in (1, -1):                                      # legs
        a = 0.36 * sw * sg
        hip = (0, -140)
        foot = (hip[0] + 140 * math.sin(a), hip[1] + 140 * math.cos(a))
        lg = skia.Path(); lg.moveTo(*hip); lg.lineTo(*foot)
        c.drawPath(stroke_path(lg, 20), p)
        c.drawPath(rrect(foot[0] - 10, foot[1] - 8, foot[0] + 22, foot[1] + 2, 5), p)
    if kind == "skirt":
        c.drawPath(poly([(-22, -210), (22, -210), (40, -110), (-38, -110)]), p)
    if kind == "hat":                                       # long coat, early 20th century
        c.drawPath(poly([(-26, -236), (26, -236), (38, -96), (-36, -96)]), p)
    c.drawPath(rrect(-24, -240, 24, -130, 16), p)          # torso
    c.drawRect(skia.Rect.MakeLTRB(-7, -262, 7, -236), p)
    c.drawCircle(2, -275, 21, p)
    if kind == "skirt":
        c.drawCircle(-14, -282, 11, p)                      # hair bun
    if kind == "hat":
        c.drawPath(rrect(-30, -292, 34, -284, 3), p); c.drawPath(rrect(-17, -312, 21, -286, 7), p)
    for sg in (-1, 1):                                      # arms
        a = 0.42 * sw * sg
        sh = (0, -228)
        hd = (sh[0] + 104 * math.sin(a), sh[1] + 104 * math.cos(a))
        ar = skia.Path(); ar.moveTo(*sh); ar.lineTo(*hd)
        c.drawPath(stroke_path(ar, 15), p)
        if sg == 1 and kind in ("coat", "hat"):           # briefcase
            c.drawPath(rrect(hd[0] - 22, hd[1] - 4, hd[0] + 26, hd[1] + 38, 5), p)
        if sg == 1 and kind == "skirt":                    # handbag
            c.drawPath(rrect(hd[0] - 14, hd[1] - 2, hd[0] + 16, hd[1] + 26, 8), p)
    c.restore()


def pigeon_ground(c, x, y, s, peck, colr):
    c.save(); c.translate(x, y); c.scale(s, s)
    p = paint(colr)
    c.drawPath(oval(0, -14, 19, 11), p)
    c.drawPath(poly([(-16, -18), (-34, -24), (-30, -12)]), p)
    hy = -26 + 10 * peck
    c.drawCircle(15 + 4 * peck, hy, 7.5, p)
    c.drawPath(poly([(20 + 4 * peck, hy - 2), (28 + 4 * peck, hy + 1), (20 + 4 * peck, hy + 3)]), p)
    for lx in (-3, 5): c.drawRect(skia.Rect.MakeLTRB(lx, -4, lx + 2.5, 0), p)
    c.restore()


def bird_path(flap, sz):
    p = skia.Path()
    wy = -sz * 0.55 * flap
    p.moveTo(0, 0)
    p.quadTo(-sz * 0.5, wy - sz * 0.15, -sz, wy * 1.1 + sz * 0.1)
    p.quadTo(-sz * 0.45, wy * 0.4 + sz * 0.05, 0, sz * 0.18)
    p.quadTo(sz * 0.45, wy * 0.4 + sz * 0.05, sz, wy * 1.1 + sz * 0.1)
    p.quadTo(sz * 0.5, wy - sz * 0.15, 0, 0)
    p.close()
    return p


PIGEONS = [(600 + 34 * i + 20 * hash01(i, 1), HERO_Y + 45 + 30 * hash01(i, 2)) for i in range(6)]


def pigeon_fly_pos(i, u):
    hx, hy = PIGEONS[i]
    d = 1 if i % 3 else -0.4
    return hx + (230 + 80 * hash01(i, 4)) * u * d + 30 * u * u, hy - 420 * u + 55 * u * u


def draw_pigeons(c, state_fn, W, colr=None):
    """state_fn(i, W) -> ('ground', peck) | ('fly', u)"""
    colr = colr or P["l5"]
    for i in range(len(PIGEONS)):
        st = state_fn(i, W)
        if st[0] == "ground":
            hx, hy = PIGEONS[i]
            c.save(); c.translate(hx, hy)
            if i % 2: c.scale(-1, 1)
            pigeon_ground(c, 0, 0, 1.0, st[1], colr)
            c.restore()
        else:
            u = st[1]
            x, y = pigeon_fly_pos(i, u)
            k = clamp01(u / 0.12)
            c.save(); c.translate(x, y)
            if i % 3 == 0: c.scale(-1, 1)
            c.drawPath(bird_path(math.sin(u * 22 + i), 26 * (0.7 + 0.3 * k)), paint(colr))
            c.restore()


# ---------------------------------------------------------------- the old office facade (scene 3)
FACADE = (70.0, 600.0, 1010.0, 1650.0)        # l, t, r, ground line
WIN_COLS, WIN_ROWS = 3, 3


def window_rects():
    l, t, r, g = FACADE
    out = []
    ww, wh = 168, 238
    for row in range(WIN_ROWS):
        for colm in range(WIN_COLS):
            cx = l + (r - l) * (colm + 0.5) / WIN_COLS
            y = t + 70 + row * 300
            out.append((row, colm, skia.Rect.MakeLTRB(cx - ww / 2, y, cx + ww / 2, y + wh)))
    return out


def calculator_machine(c, x, y, s, crank, colr):
    """mechanical desk calculator with a turning crank; (x, y) = bottom-left"""
    p = paint(colr)
    c.drawPath(poly([(x, y), (x + 60 * s, y), (x + 52 * s, y - 30 * s), (x + 6 * s, y - 34 * s)]), p)
    c.drawRect(skia.Rect.MakeLTRB(x + 4 * s, y - 44 * s, x + 46 * s, y - 32 * s), p)
    cx, cy = x + 62 * s, y - 22 * s
    c.drawCircle(cx, cy, 6 * s, p)
    hx, hy = cx + 16 * s * math.cos(crank), cy + 16 * s * math.sin(crank)
    a = skia.Path(); a.moveTo(cx, cy); a.lineTo(hx, hy)
    c.drawPath(stroke_path(a, 4 * s), p)
    c.drawCircle(hx, hy, 4.5 * s, p)


def clerk(c, x, y, s, t, colr, seed, machine=False):
    """seated office 'computer' bent over a desk (side view); (x, y) = desk-top level, figure faces right"""
    p = paint(colr)
    c.save(); c.translate(x, y); c.scale(s, s)
    c.drawRect(skia.Rect.MakeLTRB(-20, -2, 92, 8), p)                       # desk top
    c.drawRect(skia.Rect.MakeLTRB(80, 8, 88, 70), p)
    c.drawRect(skia.Rect.MakeLTRB(-60, 20, -26, 28), p)                     # chair seat
    c.drawRect(skia.Rect.MakeLTRB(-60, -40, -54, 28), p)                    # chair back
    c.save(); c.rotate(24 + 4 * math.sin(t * 2 + seed))
    c.drawPath(rrect(-40, -64, -8, 22, 14), p)                              # torso, bent forward
    c.restore()
    c.drawCircle(-2 + 3 * math.sin(t * 2 + seed), -66, 13, p)              # head
    c.drawCircle(-14, -72, 7, p)                                            # bun / hair
    if machine:
        calculator_machine(c, 18, -2, 0.9, t * 9 + seed, colr)
        hx, hy = 18 + 62 * 0.9 + 16 * 0.9 * math.cos(t * 9 + seed), -2 - 22 * 0.9 + 16 * 0.9 * math.sin(t * 9 + seed)
    else:
        c.drawRect(skia.Rect.MakeLTRB(14, -6, 62, -2), paint(P["glow"]))     # paper
        hx, hy = 30 + 14 * math.sin(t * 7 + seed), -10 + 2 * math.sin(t * 15 + seed)
        pen = skia.Path(); pen.moveTo(hx, hy); pen.lineTo(hx + 8, hy - 14)
        c.drawPath(stroke_path(pen, 2.5), p)
    a = skia.Path(); a.moveTo(-14, -48); a.quadTo(10, -26, hx, hy)
    c.drawPath(stroke_path(a, 10), p)
    c.restore()


def draw_facade(c, t, open_k=1.0):
    l, tp, r, g = FACADE
    c.drawRect(skia.Rect.MakeLTRB(-400, tp + 40, l - 14, g), paint(P["l2"]))           # neighbours
    c.drawRect(skia.Rect.MakeLTRB(r + 14, tp + 90, 1600, g), paint(P["l2"]))
    for nx in (-200, -60, r + 60, r + 200):
        for row in range(3):
            c.drawRect(skia.Rect.MakeLTRB(nx, tp + 150 + row * 300, nx + 90, tp + 330 + row * 300), paint(mix(P["l2"], P["l4"], 0.25)))
    c.drawRect(skia.Rect.MakeLTRB(l, tp, r, g), paint(P["l3"]))
    dk = paint(P["l4"])
    c.drawRect(skia.Rect.MakeLTRB(l - 16, tp - 22, r + 16, tp + 8), dk)                # cornice
    for k in range(int((r - l) // 30)):
        c.drawRect(skia.Rect.MakeLTRB(l + 8 + k * 30, tp + 8, l + 22 + k * 30, tp + 20), dk)   # dentils
    for row in range(1, WIN_ROWS + 1):
        c.drawRect(skia.Rect.MakeLTRB(l - 6, tp + 40 + row * 300 - 28, r + 6, tp + 40 + row * 300 - 18), dk)
    # ground floor: door + two shop windows
    cxm = (l + r) / 2
    c.drawPath(rrect(cxm - 70, g - 230, cxm + 70, g, 0), dk)
    c.drawRect(skia.Rect.MakeLTRB(cxm - 60, g - 220, cxm + 60, g), paint(P["l5"]))
    for sx in (l + 60, r - 260):
        c.drawRect(skia.Rect.MakeLTRB(sx, g - 200, sx + 200, g - 40), dk)
        c.drawRect(skia.Rect.MakeLTRB(sx + 10, g - 190, sx + 190, g - 50), paint(P["glow"]))
    for row, colm, rc in window_rects():
        c.drawRect(rc.makeOutset(10, 10), dk)                                      # frame
        c.drawRect(rc, paint(P["glow"]))                                           # lit interior
        c.save(); c.clipRect(rc)
        seed = row * 3 + colm
        clerk(c, rc.left() + 72, rc.bottom() - 58, 1.0, t, P["l5"], seed, machine=(seed in (1, 5, 6)))
        c.restore()
        c.drawRect(skia.Rect.MakeLTRB(rc.left(), rc.top() + 92, rc.right(), rc.top() + 100), dk)       # transom bar
        c.drawRect(skia.Rect.MakeLTRB(rc.left() - 14, rc.bottom() + 8, rc.right() + 14, rc.bottom() + 20), dk)  # sill
    # the open window (top right): casement swung outwards
    row, colm, rc = window_rects()[2]
    ang = 0.75 * open_k
    w = rc.width() / 2 * math.cos(ang)
    c.drawPath(poly([(rc.right(), rc.top()), (rc.right() + w, rc.top() - 26 * math.sin(ang)),
                     (rc.right() + w, rc.bottom() + 26 * math.sin(ang)), (rc.right(), rc.bottom())]), dk)


def sheet(c, x, y, ang, s=1.0, alpha=1.0, scribble=True):
    c.save(); c.translate(x, y); c.rotate(ang); c.scale(s, s)
    c.drawRect(skia.Rect.MakeLTRB(-22, -28, 22, 28), paint(P["glow"], a=255 * alpha))
    if scribble:
        sp = paint(P["l4"], a=200 * alpha)
        for k in range(5):
            c.drawRect(skia.Rect.MakeLTRB(-15, -19 + k * 9, -15 + 14 + 14 * hash01(k, x // 1), -16 + k * 9), sp)
    c.restore()
