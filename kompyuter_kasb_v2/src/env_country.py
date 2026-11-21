# Early-1600s countryside: rolling field layers, dirt path, distant trees and houses, a low hill with a giant open book.
import math
import numpy as np
import skia
from common import *
from style import P, stroke_path

BOOK_CX, BOOK_BASE = 640.0, 1302.0
BOOK_WP, BOOK_HP = 330.0, 640.0           # one page width / page height: ~2x the hero = a two-storey house
HILL_TOP = 1306.0
HERO_X, HERO_Y = 440.0, 1410.0            # the hero stands at the book's foot (same spot as on the street)


def _ridge(x0, x1, base, amp, freq, seed, step=8):
    xs = np.arange(x0, x1 + step, step, dtype=float)
    y = base - amp * (0.55 * np.sin(xs * freq + seed) + 0.3 * np.sin(xs * freq * 2.3 + seed * 1.7) + 0.15 * np.sin(xs * freq * 5.1 + seed))
    return xs, y


def _fill(xs, ys, bottom=2600.0):
    p = skia.Path(); p.moveTo(float(xs[0]), bottom)
    for x, y in zip(xs, ys): p.lineTo(float(x), float(y))
    p.lineTo(float(xs[-1]), bottom); p.close(); return p


_C = {}


def layers():
    if _C: return _C
    xs, ys = _ridge(-900, 2400, 1085, 30, 0.004, 1.0)
    _C["far"] = _fill(xs, ys)
    deco = skia.Path(); deco2 = skia.Path()
    for k in range(26):                                    # distant trees and small houses on the horizon
        x = -800 + k * 125 + 50 * hash01(k, 1)
        y = float(np.interp(x, xs, ys)) + 4
        if hash01(k, 2) < 0.4:
            deco.addRect(skia.Rect.MakeLTRB(x, y - 26, x + 34, y))
            deco.addPoly([skia.Point(x - 5, y - 26), skia.Point(x + 17, y - 44), skia.Point(x + 39, y - 26)], True)
        else:
            deco.addCircle(x, y - 26, 16 + 8 * hash01(k, 3)); deco.addRect(skia.Rect.MakeLTRB(x - 2, y - 14, x + 2, y))
    _C["far_deco"] = deco
    xs2, ys2 = _ridge(-900, 2400, 1150, 34, 0.0032, 4.0)
    _C["mid"] = _fill(xs2, ys2)
    for k in range(14):
        x = -700 + k * 230 + 80 * hash01(k, 5)
        y = float(np.interp(x, xs2, ys2)) + 6
        if hash01(k, 6) < 0.5:
            deco2.addRect(skia.Rect.MakeLTRB(x, y - 34, x + 46, y))
            deco2.addPoly([skia.Point(x - 6, y - 34), skia.Point(x + 23, y - 58), skia.Point(x + 52, y - 34)], True)
            deco2.addRect(skia.Rect.MakeLTRB(x + 34, y - 62, x + 41, y - 44))
        else:
            for j in range(3):
                deco2.addCircle(x + j * 26, y - 30 - 6 * j % 2, 20); deco2.addRect(skia.Rect.MakeLTRB(x + j * 26 - 2, y - 14, x + j * 26 + 2, y))
    _C["mid_deco"] = deco2
    xs3, ys3 = _ridge(-900, 2400, 1215, 26, 0.0026, 2.2)
    _C["field"] = _fill(xs3, ys3)
    rows = skia.Path()
    for r in range(9):
        y0 = 1240 + r * 34 + r * r * 3
        q = skia.Path(); q.moveTo(-900, y0)
        for x in range(-900, 2401, 60): q.lineTo(x, y0 + 8 * math.sin(x * 0.003 + r))
        rows.addPath(stroke_path(q, 2.5 + r * 0.35))
    _C["rows"] = rows
    hill = skia.Path(); hill.moveTo(-60, 1520)
    hill.cubicTo(180, 1330, 420, HILL_TOP - 4, BOOK_CX, HILL_TOP - 6)
    hill.cubicTo(860, HILL_TOP - 4, 1060, 1330, 1260, 1480); hill.lineTo(1260, 2600); hill.lineTo(-60, 2600); hill.close()
    _C["hill"] = hill
    path = skia.Path(); path.moveTo(-60, 1920)
    path.cubicTo(220, 1780, 160, 1600, 330, 1500); path.cubicTo(420, 1450, 400, 1430, HERO_X + 10, HERO_Y + 6)
    _C["path"] = path
    return _C


def draw_layers(c, cam, t, sink=(0, 0, 0, 0)):
    """sink: per-layer downward offsets (far, mid, field, hill) for the era change"""
    L = layers()
    cam.begin(c, 0.12); c.translate(0, sink[0])
    c.drawPath(L["far"], paint(P["l1"])); c.drawPath(L["far_deco"], paint(P["l2"])); c.restore()
    cam.begin(c, 0.25); c.translate(0, sink[1])
    c.drawPath(L["mid"], paint(P["l2"])); c.drawPath(L["mid_deco"], paint(P["l1"])); c.restore()
    cam.begin(c, 0.45); c.translate(0, sink[2])
    c.drawPath(L["field"], paint(P["l3"])); c.drawPath(L["rows"], paint(mix(P["l3"], P["l4"], 0.25))); c.restore()


def draw_hill(c, sink=0.0):
    L = layers()
    c.save(); c.translate(0, sink)
    c.drawPath(L["hill"], paint(P["l4"]))
    c.drawPath(stroke_path(L["path"], 46), paint(P["l3"]))
    c.drawPath(stroke_path(L["path"], 30), paint(P["l2"]))
    c.restore()


def grass(c, t, y0=1840.0, x0=-300, x1=1400, wind=1.0, sink=0.0, alpha=1.0):
    p = paint(P["l5"], a=255 * alpha)
    c.save(); c.translate(0, sink)
    c.drawRect(skia.Rect.MakeLTRB(x0, y0 + 20, x1, 2600), p)
    for k in range(int((x1 - x0) / 13)):
        x = x0 + k * 13 + 6 * hash01(k, 7)
        h = 50 + 60 * hash01(k, 8)
        bend = (10 + 18 * wind) * math.sin(t * (2.2 + 1.4 * wind) + k * 0.4) + 14 * wind
        b = skia.Path(); b.moveTo(x - 5, y0 + 24); b.quadTo(x + bend * 0.3, y0 - h * 0.5, x + bend, y0 - h)
        b.quadTo(x + bend * 0.2 + 3, y0 - h * 0.45, x + 5, y0 + 24); b.close()
        c.drawPath(b, p)
    c.restore()


def hill_grass(c, t, wind=1.0, sink=0.0):
    p = paint(P["l4"])
    c.save(); c.translate(0, sink)
    for k in range(70):
        x = 120 + k * 15
        y = HILL_TOP - 4 + 0.00016 * (x - BOOK_CX) ** 2 + 2
        if y > 1480: continue
        h = 16 + 16 * hash01(k, 9)
        bend = (6 + 10 * wind) * math.sin(t * 3 + k * 0.6) + 6 * wind
        b = skia.Path(); b.moveTo(x - 3, y + 4); b.quadTo(x + bend * 0.3, y - h * 0.5, x + bend, y - h); b.lineTo(x + 3, y + 4); b.close()
        c.drawPath(b, p)
    c.restore()


# ---------------------------------------------------------------- the giant book
def _page_quad(spine_x, edge_x, base, hp, lift, sag=16.0):
    """page from the spine to edge_x; lift curls it up; top/bottom edges sag towards the spine"""
    p = skia.Path()
    top, bot = base - hp, base
    mx = (spine_x + edge_x) / 2
    p.moveTo(spine_x, top + sag)
    p.quadTo(mx, top - lift * 0.8 - 6, edge_x, top - lift)
    p.lineTo(edge_x, bot - lift * 0.6)
    p.quadTo(mx, bot - lift * 0.3 + 4, spine_x, bot)
    p.close()
    return p


def _page_lines(c, x0, x1, base, hp, colr, n=17, skip=()):
    for k in range(n):
        if k in skip: continue
        y = base - hp + 70 + k * (hp - 110) / n
        l = x0 + 34 if x0 < x1 else x0 - 34
        r = x1 - 30 if x0 < x1 else x1 + 30
        ln = abs(r - l) * (0.75 + 0.25 * hash01(k, x0 // 1))
        a, b = (l, l + ln) if l < r else (l - ln, l)
        c.drawRect(skia.Rect.MakeLTRB(a, y, b, y + 3), paint(colr))


def draw_book(c, t, flip_rate=0.0, flip_phase=0.0, close=0.0, scale=1.0, cx=BOOK_CX, base=BOOK_BASE, lift_one=0.0,
              writing=None):
    """flip_rate: pages per second flipping right->left; close 0..1 slams the right half shut over the left"""
    wp, hp = BOOK_WP * scale, BOOK_HP * scale
    cover = paint(P["l5"]); page = paint(P["glow"]); edge = paint(P["l1"]); lines = mix(P["l2"], P["l3"], 0.3)
    # base cover (left half always open)
    c.drawPath(rrect(cx - wp - 18, base - hp - 14, cx + 4, base + 16, 10), cover)
    c.drawRect(skia.Rect.MakeLTRB(cx - 12, base - hp - 20, cx + 12, base + 20), cover)          # spine
    c.drawPath(_page_quad(cx, cx - wp, base, hp, 0), page)
    c.drawPath(_page_quad(cx, cx - wp + 6, base, hp, 0), edge if False else page)
    _page_lines(c, cx, cx - wp, base, hp, lines)
    if close < 1:
        ang = math.pi * ease_in(close)                                   # right half swings over
        ex = cx + wp * math.cos(ang)
        lift = 70 * math.sin(ang)
        if ang < math.pi / 2:
            c.drawPath(rrect(cx - 4, base - hp - 14, cx + (wp + 18) * math.cos(ang), base + 16, 10), cover)
            c.drawPath(_page_quad(cx, ex, base, hp, lift), page)
            if close == 0:
                skip = tuple(range(3, 9)) if writing is not None else ()
                _page_lines(c, cx, ex, base, hp, lines, skip=skip)
                if writing is not None: writing(c, cx, ex, base, hp)
        else:
            c.drawPath(_page_quad(cx, ex, base, hp, lift), page)
            q = _page_quad(cx, cx + (wp + 18) * math.cos(ang), base + 6, hp + 20, lift)
            c.drawPath(q, cover)
    else:
        c.drawPath(rrect(cx - wp - 22, base - hp - 18, cx + 6, base + 18, 10), cover)          # closed: cover on top
        c.drawRect(skia.Rect.MakeLTRB(cx - wp - 22, base - 8, cx + 6, base + 2), paint(mix(P["l5"], P["glow"], 0.25)))
    # pages flipping (right -> left), several in flight
    if flip_rate > 0 and close == 0:
        n = 4
        for k in range(n):
            ph = (flip_phase * flip_rate + k / n) % 1.0
            ang = math.pi * smooth(ph)
            ex = cx + wp * math.cos(ang)
            lift = 90 * math.sin(ang)
            pg = _page_quad(cx, ex, base, hp, lift)
            c.drawPath(pg, page)
            c.drawPath(stroke_path(pg, 3), edge)
    if lift_one > 0 and close == 0:
        ang = math.pi * 0.16 * lift_one
        ex = cx + wp * math.cos(ang)
        pg = _page_quad(cx, ex, base, hp, 40 * lift_one)
        c.drawPath(pg, page); c.drawPath(stroke_path(pg, 3), edge)


# ---------------------------------------------------------------- loose pages forming an arrow
ARROW = [(230 + k * 62, 660, 0.0) for k in range(8)] + [(790, 660, 0.0)]
for k in range(1, 4):
    ARROW.append((790 - k * 50, 660 - k * 50, 45.0))
    ARROW.append((790 - k * 50, 660 + k * 50, -45.0))


def loose_pages(c, u, cx=BOOK_CX, base=BOOK_BASE):
    """u = seconds since the slam: pages burst up, then settle into an arrow pointing right"""
    if u <= 0: return
    p = paint(P["glow"]); e = paint(P["l2"])
    for i, (tx, ty, ta) in enumerate(ARROW):
        sx, sy = cx - 140 + 280 * hash01(i, 1), base - 260 - 120 * hash01(i, 2)
        bx, by = sx + (hash01(i, 3) - 0.5) * 500, sy - 420 - 260 * hash01(i, 4)
        k1 = ease_out(clamp01(u / 0.35))
        k2 = ease_io(clamp01((u - 0.22) / 0.6))
        x = lerp(lerp(sx, bx, k1), tx, k2)
        y = lerp(lerp(sy, by, k1), ty, k2)
        ang = lerp(lerp(0, 380 * (hash01(i, 5) - 0.5), k1), ta, k2) + 6 * math.sin(u * 7 + i) * k2
        sc = lerp(0.4, 1.0, k1)
        c.save(); c.translate(x, y); c.rotate(ang); c.scale(sc, sc * (0.6 + 0.4 * abs(math.cos(u * 9 + i))) if k2 < 1 else sc)
        c.drawRect(skia.Rect.MakeLTRB(-27, -20, 27, 20), e)
        c.drawRect(skia.Rect.MakeLTRB(-25, -18, 25, 18), p)
        c.restore()
