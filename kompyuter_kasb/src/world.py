# Landscape: layered silhouettes, sun/moon with watercolour stains, water reflection, paper grain, vignette.
import math, os
import numpy as np
import skia
from scipy.ndimage import gaussian_filter
from common import *

BANK = 1222.0                    # world y of the hovuz water line

PAL_DAY = dict(sky_top="#E9DEC6", sky_bot="#F4EDDF", far1="#C6CEC9", far2="#AEBBB8", city="#8C9FA1", city_d="#7F9395",
               house="#56696D", house_d="#4B5E62", gate="#45575B", near="#2E3C40", near2="#33444A", bank="#2A363A",
               ground="#3B4C52", path="#56696D", people="#45575B", people2="#2E3C40", water="#6E8386", bird="#2E3C40",
               win_off="#45575B", lamp_off="#25313A")
PAL_NIGHT = dict(sky_top="#2B3A44", sky_bot="#3E5059", far1="#53656D", far2="#4A5C64", city="#3E5059", city_d="#36474F",
                 house="#33454D", house_d="#2D3D44", gate="#2A393F", near="#1D282C", near2="#223036", bank="#172024",
                 ground="#26343A", path="#33454D", people="#4A5C64", people2="#33454D", water="#2E3F47", bird="#1D282C",
                 win_off="#2A393F", lamp_off="#1A2428")


def palette(n):
    return {k: mix(PAL_DAY[k], PAL_NIGHT[k], n) for k in PAL_DAY}


# ------------------------------------------------------------------ textures (numpy -> skia.Image)
def _img(a):
    a = np.ascontiguousarray(np.clip(a, 0, 255).astype(np.uint8))
    return skia.Image.fromarray(a, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)


def _ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def stain_texture(seed, layers, size=512):
    """watercolour blotches: soft fills with darker pooled rims"""
    rng = np.random.RandomState(seed)
    rgb = np.zeros((size, size, 3)); al = np.zeros((size, size))
    for (c, sig, thr, a) in layers:
        n = gaussian_filter(rng.randn(size, size), sig, mode="wrap"); n /= n.std() + 1e-9
        n2 = gaussian_filter(rng.randn(size, size), sig / 4, mode="wrap"); n += 0.18 * n2 / (n2.std() + 1e-9)
        m = _ss(thr, thr + 0.5, n)
        rim = _ss(thr - 0.02, thr + 0.06, n) - _ss(thr + 0.1, thr + 0.32, n)
        aa = a * np.clip(0.55 * m + 0.6 * np.clip(rim, 0, 1), 0, 1)
        cc = np.array(hexc(c)[:3], float)
        rgb = rgb * (1 - aa[..., None]) + cc * aa[..., None]
        al = al + aa * (1 - al)
    out = np.zeros((size, size, 4))
    out[..., :3] = np.where(al[..., None] > 1e-4, rgb / np.maximum(al[..., None], 1e-4), 0)
    out[..., 3] = al * 255
    return _img(out)


_TEX = {}


def tex(name):
    if name in _TEX: return _TEX[name]
    if name == "sun":
        t = stain_texture(11, [("#E1742F", 34, 0.55, 0.55), ("#F7C487", 26, 0.75, 0.5), ("#D9662A", 18, 1.15, 0.45),
                               ("#F2A55C", 40, 0.3, 0.35)])
    elif name == "moon":
        t = stain_texture(23, [("#D8CFBD", 30, 0.45, 0.55), ("#CBC3B1", 20, 0.9, 0.5), ("#FFFFFF", 36, 0.8, 0.35),
                               ("#BDB6A6", 14, 1.3, 0.35)])
    elif name == "grain":
        rng = np.random.RandomState(5)
        n = gaussian_filter(rng.randn(H, W), 0.6) * 1.0 + gaussian_filter(rng.randn(H, W), 2.5) * 2.2
        fib = gaussian_filter(rng.randn(H, W), (0.6, 9)) * 3.0
        v = 255 - np.clip(9 + 6 * n + 4 * fib, 0, 40)
        a = np.dstack([v, v, v * 0.985, np.full_like(v, 255)])
        t = _img(a)
    elif name == "num1613":
        t = None
    _TEX[name] = t
    return t


# ------------------------------------------------------------------ static silhouette paths (built once)
def _noise1(x, seed):
    # smooth 1-D value noise
    i = np.floor(x).astype(int); f = x - i
    h = lambda k: np.array([hash01(seed, kk) for kk in k])
    a, b = h(i), h(i + 1)
    f = f * f * (3 - 2 * f)
    return a + (b - a) * f


def _ridge(peaks, x0, x1, base, step, seed, jag):
    xs = np.arange(x0, x1 + step, step, dtype=float)
    y = np.full_like(xs, base)
    for px, py, w in peaks:
        d = np.abs(xs - px) / w
        prof = np.clip(1 - d, 0, None) ** 1.25
        y = np.minimum(y, base - (base - py) * prof)
    y -= jag * (0.6 * _noise1(xs / 37.0, seed) + 0.4 * _noise1(xs / 13.0, seed + 1) - 0.5) * (base - y) / 200
    return xs, y


def _ridge_path(xs, ys, bottom):
    p = skia.Path(); p.moveTo(xs[0], bottom)
    for x, y in zip(xs, ys): p.lineTo(float(x), float(y))
    p.lineTo(xs[-1], bottom); p.close(); return p


_P = {}


def paths():
    if _P: return _P
    xs, ys = _ridge([(-500, 760, 420), (-150, 700, 380), (230, 668, 360), (520, 860, 260), (930, 700, 360), (1250, 735, 330),
                     (1650, 690, 420), (2050, 745, 380), (2450, 700, 420), (2900, 730, 400), (3300, 690, 420)],
                    -1400, 3800, 1160, 5, 3, 60)
    _P["far1"] = _ridge_path(xs, ys, 1500)
    xs, ys = _ridge([(-380, 860, 300), (60, 830, 280), (360, 880, 240), (760, 845, 300), (1080, 870, 260), (1420, 835, 320),
                     (1800, 860, 300), (2200, 840, 330), (2600, 870, 300), (3000, 845, 330)],
                    -1400, 3800, 1160, 5, 9, 40)
    _P["far2"] = _ridge_path(xs, ys, 1500)
    _P["city"], _P["city_d"], _P["city_win"] = _city()
    _P["houses"], _P["houses_d"], _P["houses_win"], _P["gate"], _P["gate_d"] = _houses()
    return _P


def _city():
    body = skia.Path(); dark = skia.Path(); win = skia.Path()

    def minaret(cx, base, top, wb, wt):
        body.addPoly([skia.Point(cx - wb, base), skia.Point(cx - wt, top), skia.Point(cx + wt, top), skia.Point(cx + wb, base)], True)
        body.addRect(skia.Rect.MakeLTRB(cx - wt - 9, top - 8, cx + wt + 9, top + 2))      # muqarnas ledge
        body.addRect(skia.Rect.MakeLTRB(cx - wt - 3, top - 46, cx + wt + 3, top - 8))     # lantern
        body.addRect(skia.Rect.MakeLTRB(cx - wt - 7, top - 52, cx + wt + 7, top - 45))
        body.addOval(skia.Rect.MakeLTRB(cx - wt + 2, top - 70, cx + wt - 2, top - 36))   # cupola
        body.addRect(skia.Rect.MakeLTRB(cx - 1.5, top - 84, cx + 1.5, top - 66))
        for k in range(5):
            x = cx - wt + 5 + k * (2 * wt - 10) / 4.0
            win.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(x - 3, top - 38, x + 3, top - 16), 3, 3))
        for k in range(1, 6):        # decorative bands
            yy = top + (base - top) * k / 6.5
            w = wt + (wb - wt) * (yy - top) / (base - top)
            dark.addRect(skia.Rect.MakeLTRB(cx - w, yy, cx + w, yy + 4))

    def dome(cx, drum_top, base, r, ribs=True):
        body.addRect(skia.Rect.MakeLTRB(cx - r * 0.78, drum_top, cx + r * 0.78, base))
        body.addOval(skia.Rect.MakeLTRB(cx - r, drum_top - r * 1.15, cx + r, drum_top + r * 0.35))
        body.addRect(skia.Rect.MakeLTRB(cx - 2, drum_top - r * 1.15 - 22, cx + 2, drum_top - r * 1.0))
        body.addCircle(cx, drum_top - r * 1.15 - 22, 4)
        if ribs:
            for k in range(-3, 4):
                p = skia.Path(); x = cx + k * r * 0.27
                p.moveTo(cx + k * r * 0.05, drum_top - r * 1.12)
                p.quadTo(x + k * r * 0.08, drum_top - r * 0.6, x, drum_top + r * 0.2)
                dark.addPath(_stroke(p, 3.0))
        for k in range(4):
            x = cx - r * 0.6 + k * r * 0.4
            win.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(x - 4, drum_top + 14, x + 4, drum_top + 34), 4, 4))

    def portal(cx, base, top, hw):
        body.addRect(skia.Rect.MakeLTRB(cx - hw, top, cx + hw, base))
        for s in (-1, 1):
            gx = cx + s * (hw + 4)
            body.addRect(skia.Rect.MakeLTRB(gx - 9, top - 36, gx + 9, base))
            body.addRect(skia.Rect.MakeLTRB(gx - 12, top - 40, gx + 12, top - 34))
            body.addOval(skia.Rect.MakeLTRB(gx - 9, top - 58, gx + 9, top - 30))
        a = skia.Path(); aw = hw * 0.58
        a.moveTo(cx - aw, base); a.lineTo(cx - aw, top + 70)
        a.quadTo(cx - aw, top + 34, cx, top + 22); a.quadTo(cx + aw, top + 34, cx + aw, top + 70)
        a.lineTo(cx + aw, base); a.close()
        dark.addPath(a)
        dark.addRect(skia.Rect.MakeLTRB(cx - hw, top + 6, cx + hw, top + 12))
        win.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(cx - 10, base - 92, cx + 10, base - 56), 10, 10))

    def poplar(cx, base, h, w):
        body.addOval(skia.Rect.MakeLTRB(cx - w, base - h, cx + w, base - h * 0.08))
        body.addRect(skia.Rect.MakeLTRB(cx - 2, base - h * 0.2, cx + 2, base))

    for off in (0, 1700):
        minaret(760 + off, 1100, 640 + (40 if off else 0), 36, 25)
        dome(540 + off, 930, 1100, 72)
        portal(290 + off, 1100, 880, 82)
        dome(1010 + off, 980, 1100, 46)
        dome(-80 + off, 990, 1100, 40)
        body.addRect(skia.Rect.MakeLTRB(-300 + off, 1030, 1400 + off, 1100))
        for x in (110, 420, 640, 900, 1180, 1320):
            poplar(x + off, 1060, 150 + 40 * hash01(x, off), 17)
        for k in range(14):
            x = -260 + off + k * 120 + 40 * hash01(k, off, 3)
            body.addRect(skia.Rect.MakeLTRB(x, 1000 - 30 * hash01(k, off), x + 70 + 40 * hash01(k, 7), 1100))
    return body, dark, win


def _stroke(p, w):
    pt = skia.Paint(AntiAlias=True); pt.setStyle(skia.Paint.kStroke_Style); pt.setStrokeWidth(w)
    pt.setStrokeCap(skia.Paint.kRound_Cap)
    out = skia.Path(); pt.getFillPath(p, out); return out


def _houses():
    body = skia.Path(); dark = skia.Path(); win = skia.Path(); gate = skia.Path(); gdark = skia.Path()
    x = -700
    k = 0
    while x < 3600:
        w = 120 + 70 * hash01(k, 1); h = 70 + 45 * hash01(k, 2); base = 1170
        top = base - h
        body.addRect(skia.Rect.MakeLTRB(x, top, x + w, base))
        body.addRect(skia.Rect.MakeLTRB(x - 7, top - 9, x + w + 7, top + 2))              # flat roof slab
        for j in range(3):                                                                 # beams out of the side walls
            body.addRect(skia.Rect.MakeLTRB(x - 16, top + 3 + j * 7, x, top + 7 + j * 7))
            body.addRect(skia.Rect.MakeLTRB(x + w, top + 3 + j * 7, x + w + 16, top + 7 + j * 7))
        nb = int(w // 16)
        for j in range(nb):                                                                 # beam ends on the facade
            bx = x + 8 + j * (w - 16) / max(1, nb - 1)
            dark.addRect(skia.Rect.MakeLTRB(bx - 3, top + 3, bx + 3, top + 9))
        nw = 1 + int(w > 150)
        for j in range(nw):
            wx = x + w * (j + 1) / (nw + 1)
            win.addRect(skia.Rect.MakeLTRB(wx - 11, top + 24, wx + 11, top + 50))
        if k % 3 == 1:                                                                      # carved wooden gate
            gx = x + w * 0.5 + 18
            gate.addRect(skia.Rect.MakeLTRB(gx - 26, base - 62, gx + 26, base))
            gate.addRect(skia.Rect.MakeLTRB(gx - 32, base - 70, gx + 32, base - 61))
            gdark.addRect(skia.Rect.MakeLTRB(gx - 1, base - 60, gx + 1, base))
            for s in (-1, 1):
                for r in range(3):
                    cx, cy = gx + s * 13, base - 50 + r * 17
                    gdark.addPoly([skia.Point(cx, cy - 6), skia.Point(cx + 5, cy), skia.Point(cx, cy + 6), skia.Point(cx - 5, cy)], True)
        x += w + 20 + 50 * hash01(k, 3)
        k += 1
    return body, dark, win, gate, gdark


# ------------------------------------------------------------------ near-layer elements
def ground_y(x):
    return 1188 - 58 * math.exp(-((x - 430) / 300.0) ** 2) - 6 * math.sin(x / 140.0)


def draw_ground(c, pal, x0, x1):
    p = skia.Path(); p.moveTo(x0, 1300)
    xs = np.arange(x0, x1 + 10, 10)
    for x in xs: p.lineTo(float(x), ground_y(x))
    p.lineTo(x1, 1300); p.close()
    c.drawPath(p, paint(pal["ground"]))
    q = skia.Path(); q.moveTo(float(xs[0]), ground_y(xs[0]) + 4)
    for x in xs: q.lineTo(float(x), ground_y(x) + 4)
    c.drawPath(q, paint(pal["path"], style="stroke", width=7, cap="round"))


def draw_bank(c, pal, x0, x1):
    c.drawRect(skia.Rect.MakeLTRB(x0, BANK - 14, x1, BANK + 16), paint(pal["bank"]))
    c.drawRect(skia.Rect.MakeLTRB(x0, BANK - 14, x1, BANK - 10), paint(mix(pal["bank"], pal["ground"], 0.6)))
    x = x0 - (x0 % 70)
    pj = paint(mix(pal["bank"], "#000000", 0.25))
    while x < x1:
        c.drawRect(skia.Rect.MakeLTRB(x, BANK - 9, x + 2, BANK + 14), pj); x += 70


def tree_crown_blobs(seed, cx, cy, rx, ry, n=26):
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n + 0.4 * hash01(seed, i)
        rr = 0.62 + 0.3 * hash01(seed, i, 1)
        out.append((cx + rx * rr * math.cos(a), cy + ry * rr * math.sin(a) * 0.9, (0.33 + 0.2 * hash01(seed, i, 2)) * min(rx, ry)))
    out.append((cx, cy, 0.78 * min(rx, ry)))
    out.append((cx - rx * 0.3, cy + ry * 0.1, 0.6 * min(rx, ry)))
    out.append((cx + rx * 0.3, cy - ry * 0.05, 0.6 * min(rx, ry)))
    return out


_TREES = {}


def mulberry(seed, x, ybase, s):
    key = (seed, x, ybase, s)
    if key in _TREES: return _TREES[key]
    trunk = skia.Path()
    tw = 26 * s
    trunk.moveTo(x - tw * 1.3, ybase)
    trunk.cubicTo(x - tw, ybase - 120 * s, x - tw * 1.2, ybase - 230 * s, x - tw * 0.4, ybase - 330 * s)
    trunk.lineTo(x + tw * 0.5, ybase - 330 * s)
    trunk.cubicTo(x + tw * 0.9, ybase - 220 * s, x + tw * 0.8, ybase - 110 * s, x + tw * 1.4, ybase)
    trunk.close()
    for ang, ln in ((-0.9, 190), (-0.35, 170), (0.5, 200), (1.0, 150)):
        b = skia.Path(); bx, by = x, ybase - 300 * s
        ex, ey = bx + math.sin(ang) * ln * s, by - math.cos(ang) * ln * s
        b.moveTo(bx, by); b.quadTo(bx + math.sin(ang) * ln * 0.3 * s, by - ln * 0.6 * s, ex, ey)
        trunk.addPath(_stroke(b, 16 * s))
    crown = skia.Path()
    cy = ybase - 470 * s
    blobs = tree_crown_blobs(seed, x, cy, 260 * s, 190 * s)
    for bx, by, r in blobs:
        crown.addCircle(bx, by, r)
    crown = skia.Op(crown, skia.Path(), skia.PathOp.kUnion_PathOp)
    leaves = []
    for i in range(70):
        a = 2 * math.pi * hash01(seed, i, 5)
        rr = 0.55 + 0.5 * hash01(seed, i, 6)
        lx = x + 250 * s * rr * math.cos(a); ly = cy + 180 * s * rr * math.sin(a)
        leaves.append((lx, ly, hash01(seed, i, 7) * 360, i % 2))
    _TREES[key] = (trunk, crown, leaves, (x, cy, 250 * s, 180 * s))
    return _TREES[key]


def leaf_path(sz):
    p = skia.Path(); p.moveTo(-sz, 0); p.quadTo(0, -sz * 0.62, sz, 0); p.quadTo(0, sz * 0.62, -sz, 0); p.close(); return p


_LEAF = {}


def leaf(sz):
    k = round(sz, 1)
    if k not in _LEAF: _LEAF[k] = leaf_path(k)
    return _LEAF[k]


LEAF_COLS = ("#E58A3C", "#F0A45E")


def draw_mulberry(c, pal, seed, x, ybase, s, W, sway=1.0, leaf_scale=1.0):
    trunk, crown, leaves, (cx, cy, rx, ry) = mulberry(seed, x, ybase, s)
    c.drawPath(trunk, paint(pal["near"]))
    c.save()
    c.rotate(0.6 * sway * math.sin(W * 0.9 + seed), x, ybase - 300 * s)
    c.drawPath(crown, paint(pal["near"]))
    lp = [paint(LEAF_COLS[0]), paint(LEAF_COLS[1])]
    for lx, ly, rot_, k in leaves:
        c.save(); c.translate(lx, ly); c.rotate(rot_ + 8 * math.sin(W * 2 + lx))
        c.drawPath(leaf(9 * s * leaf_scale + 5), lp[k]); c.restore()
    c.restore()
    return (cx, cy, rx, ry)


def falling_leaves(c, crown, W, ground, n=12, seed=1, s=1.0, alpha=1.0, xdrift=40):
    cx, cy, rx, ry = crown
    for i in range(n):
        P = 4.5 + 3.0 * hash01(seed, i)
        u = ((W + P * hash01(seed, i, 2)) % P) / P
        x0 = cx + rx * (2 * hash01(seed, i, 3) - 1) * 0.85
        y0 = cy + ry * (0.2 + 0.5 * hash01(seed, i, 4))
        y = y0 + (ground - y0) * u
        x = x0 + xdrift * u * (1 if hash01(seed, i, 5) > 0.4 else -1) + 26 * math.sin(u * 9 + i)
        a = alpha * min(1.0, u * 12) * min(1.0, (1 - u) * 10)
        if a <= 0.01: continue
        c.save(); c.translate(x, y); c.rotate(u * 420 + 80 * i); c.scale(1.0, 0.55 + 0.45 * math.cos(u * 11 + i))
        c.drawPath(leaf(11 * s), paint(LEAF_COLS[i % 2], a=255 * a)); c.restore()


def draw_ishkom(c, pal, x0, x1, ybase, top):
    pp = paint(pal["near2"])
    posts = np.arange(x0, x1 + 1, 110)
    for x in posts:
        c.drawRect(skia.Rect.MakeLTRB(x - 6, top, x + 6, ybase), pp)
    c.drawRect(skia.Rect.MakeLTRB(x0 - 20, top - 8, x1 + 20, top + 6), pp)
    for x in posts[:-1]:
        q = skia.Path(); q.moveTo(x, top + 4); q.lineTo(x + 55, top + 50); q.lineTo(x + 110, top + 4)
        c.drawPath(q, paint(pal["near2"], style="stroke", width=5))
    vine = skia.Path()
    vine.addRect(skia.Rect.MakeLTRB(x0 - 30, top - 26, x1 + 30, top + 8))
    for i in range(int((x1 - x0) / 15) + 5):
        vx = x0 - 30 + i * 15
        vine.addCircle(vx, top - 22 + 14 * hash01(i, 9), 15 + 12 * hash01(i, 8))
        if hash01(i, 4) > 0.62:                      # hanging vine tendrils
            ln = 30 + 70 * hash01(i, 5)
            for k in range(4):
                vine.addCircle(vx + 6 * math.sin(k * 1.3 + i), top + 8 + ln * k / 3.0, 11 - 1.6 * k)
    c.drawPath(vine, paint(pal["near"]))
    gp = paint(mix(pal["near"], "#000000", 0.25))
    for i in range(int((x1 - x0) / 55)):
        gx = x0 + 25 + i * 55 + 20 * hash01(i, 2)
        g = skia.Path()
        for r in range(4):
            for k in range(4 - r):
                g.addCircle(gx + (k - (3 - r) / 2) * 7.5, top + 14 + r * 7.5, 4.6)
        c.drawPath(g, gp)


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


def birds(c, pal, W, n=7, cx=0.0, y0=650, speed=55.0, span=1500, sz=22, seed=3, dirn=1, alpha=1.0, x0=-200):
    for i in range(n):
        x = (hash01(seed, i) * span + speed * W * dirn) % span + x0 + cx
        y = y0 + 120 * hash01(seed, i, 2) + 10 * math.sin(W * 1.3 + i)
        flap = math.sin(W * 10 + i * 1.7)
        c.save(); c.translate(x, y)
        if dirn < 0: c.scale(-1, 1)
        c.drawPath(bird_path(flap, sz * (0.8 + 0.4 * hash01(seed, i, 3))), paint(pal["bird"], a=255 * alpha))
        c.restore()


# ------------------------------------------------------------------ sky, sun, moon
def draw_sky(c, pal, glow=0.0, sun=None, y_top=-600, y_bot=1500):
    sh = skia.GradientShader.MakeLinear([skia.Point(0, -200), skia.Point(0, BANK)],
                                         [col(pal["sky_top"]), col(pal["sky_bot"])])
    p = skia.Paint(Shader=sh)
    c.drawRect(skia.Rect.MakeLTRB(-3000, y_top, 5000, y_bot), p)
    if glow > 0 and sun is not None:
        sx, sy, r = sun
        g = skia.GradientShader.MakeRadial(skia.Point(sx, sy), r * 4.2,
                                           [col("#F2A55C", 150 * glow), col("#F2B678", 60 * glow), col("#F4EDDF", 0)],
                                           [0.0, 0.45, 1.0])
        c.drawRect(skia.Rect.MakeLTRB(-3000, y_top, 5000, y_bot), skia.Paint(Shader=g))


def draw_sun(c, x, y, r, alpha=1.0, rot_=0.0):
    if alpha <= 0: return
    a = 255 * alpha
    g = skia.GradientShader.MakeRadial(skia.Point(x, y), r * 1.6, [col("#F2A55C", 70 * alpha), col("#F2A55C", 0)], [0.6, 1.0])
    c.drawCircle(x, y, r * 1.6, skia.Paint(Shader=g, AntiAlias=True))
    sh = skia.GradientShader.MakeLinear([skia.Point(x, y - r), skia.Point(x, y + r)], [col("#F2A55C", a), col("#E1742F", a)])
    disk = circle(x, y, r)
    c.drawPath(disk, skia.Paint(Shader=sh, AntiAlias=True))
    c.save(); c.clipPath(disk, doAntiAlias=True)
    c.translate(x, y); c.rotate(rot_)
    pt = skia.Paint(); pt.setAlphaf(0.85 * alpha)
    c.drawImageRect(tex("sun"), skia.Rect.MakeLTRB(-r * 1.05, -r * 1.05, r * 1.05, r * 1.05),
                    skia.SamplingOptions(skia.FilterMode.kLinear), pt)
    c.restore()


def draw_moon(c, x, y, r, alpha=1.0):
    if alpha <= 0: return
    g = skia.GradientShader.MakeRadial(skia.Point(x, y), r * 3.0, [col("#F4EDDF", 60 * alpha), col("#F4EDDF", 0)], [0.3, 1.0])
    c.drawCircle(x, y, r * 3.0, skia.Paint(Shader=g, AntiAlias=True))
    disk = circle(x, y, r)
    c.drawPath(disk, paint("#F4EDDF", a=255 * alpha))
    c.save(); c.clipPath(disk, doAntiAlias=True)
    pt = skia.Paint(); pt.setAlphaf(0.9 * alpha)
    c.drawImageRect(tex("moon"), skia.Rect.MakeLTRB(x - r * 1.1, y - r * 1.1, x + r * 1.1, y + r * 1.1),
                    skia.SamplingOptions(skia.FilterMode.kLinear), pt)
    c.restore()


def draw_stars(c, alpha, cam_x=0):
    if alpha <= 0: return
    for i in range(40):
        x = (hash01(i, 1) * 1600 - 260) - cam_x * 0.02
        y = 60 + 700 * hash01(i, 2)
        tw = 0.55 + 0.45 * math.sin(i * 3.1)
        c.drawCircle(x, y, 1.6 + 1.4 * hash01(i, 3), paint("#F4EDDF", a=200 * alpha * tw))


# ------------------------------------------------------------------ layered landscape
def draw_far(c, pal, cam_x, lit=0.0):
    P = paths()
    c.save(); c.translate(-cam_x * 0.08, 0); c.drawPath(P["far1"], paint(pal["far1"])); c.restore()
    c.save(); c.translate(-cam_x * 0.15, 0); c.drawPath(P["far2"], paint(pal["far2"])); c.restore()
    c.save(); c.translate(-cam_x * 0.3, 0)
    c.drawPath(P["city"], paint(pal["city"])); c.drawPath(P["city_d"], paint(pal["city_d"]))
    c.drawPath(P["city_win"], paint(mix(pal["city_d"], "#E7A05C", lit)))
    c.restore()


def draw_houses(c, pal, cam_x, lit=0.0):
    P = paths()
    c.save(); c.translate(-cam_x * 0.55, 0)
    c.drawPath(P["houses"], paint(pal["house"])); c.drawPath(P["houses_d"], paint(pal["house_d"]))
    c.drawPath(P["houses_win"], paint(mix(pal["win_off"], "#E7A05C", lit)))
    c.drawPath(P["gate"], paint(pal["gate"])); c.drawPath(P["gate_d"], paint(mix(pal["gate"], "#000000", 0.25)))
    c.restore()


# ------------------------------------------------------------------ water (numpy) and screen overlays
def water_reflect(arr, bank_y, t, pal, amp=1.0, sun_x=None, sun_glint=0.0, rows_tint=0.8):
    """arr: HxWx4 uint8 RGBA (screen). Rows below bank_y become a rippled, tinted reflection."""
    Hh, Ww = arr.shape[:2]
    b = int(round(bank_y))
    if b >= Hh: return arr
    b = max(b, 1)
    ys = np.arange(b, Hh)
    d = (ys - b).astype(float)
    src = (2 * bank_y - ys + 2.0 * np.sin(d * 0.09 - t * 2.2) * amp).astype(int)
    src = np.clip(src, 0, b - 1)
    xs = np.arange(Ww)[None, :].astype(float)
    a_row = (1.2 + d * 0.016) * amp
    dx = a_row[:, None] * (np.sin(d[:, None] * 0.13 + t * 2.4) * 0.7 + 0.6 * np.sin(xs * 0.011 + d[:, None] * 0.045 - t * 1.3))
    sx = np.clip((xs + dx).astype(int), 0, Ww - 1)
    refl = arr[src[:, None], sx, :3].astype(np.float32)
    wc = np.array(pal["water"][:3], np.float32)
    k = (0.70 + 0.12 * np.exp(-d / 260.0))[:, None, None]
    refl = refl * k + wc * (1 - k) * rows_tint + refl * (1 - k) * (1 - rows_tint)
    # soft horizontal shimmer bands
    band = (0.5 + 0.5 * np.sin(d[:, None] * (0.16 + 0.0002 * d[:, None]) + t * 2.1 + np.sin(xs * 0.009 + t * 0.7 + d[:, None] * 0.01) * 2.2)) ** 14
    refl += band[..., None] * 12 * (0.5 + 0.5 * np.exp(-d / 400.0))[:, None, None]
    out = arr.copy()
    out[b:, :, :3] = np.clip(refl, 0, 255).astype(np.uint8)
    out[b:, :, 3] = 255
    return out


def sun_path(c, x, bank_y, t, strength=1.0, width=1.0, col1="#F2A55C", col2="#E1742F", ybot=1920):
    if strength <= 0: return
    y = bank_y + 6
    i = 0
    while y < ybot:
        d = y - bank_y
        w = (40 + d * 0.32) * width * (0.35 + 0.65 * hash01(i, 7))
        fl = 0.5 + 0.5 * math.sin(t * 5.0 + i * 1.9)
        off = (hash01(i, 3) - 0.5) * (30 + d * 0.25) * width + 8 * math.sin(t * 1.7 + i)
        a = 255 * strength * (0.35 + 0.55 * fl) * (1.0 - 0.45 * d / 700.0)
        hh = 3.0 + d * 0.012
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(x + off - w / 2, y, x + off + w / 2, y + hh), hh / 2, hh / 2),
                    paint(col1 if i % 3 else col2, a=a))
        y += 7 + d * 0.035
        i += 1


def overlays(c, grain=True, vignette=0.26):
    if grain:
        pt = skia.Paint(); pt.setBlendMode(skia.BlendMode.kMultiply)
        c.drawImage(tex("grain"), 0, 0, skia.SamplingOptions(), pt)
    if vignette > 0:
        g = skia.GradientShader.MakeRadial(skia.Point(W / 2, H * 0.47), H * 0.66,
                                           [col("#1A2124", 0), col("#1A2124", 0), col("#1A2124", 255 * vignette)], [0.0, 0.55, 1.0])
        c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=g))
