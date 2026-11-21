# Shared helpers: colours, easing, skia path helpers.
import math
import skia

W, H, FPS = 1080, 1920, 30


def hexc(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def col(c, a=None):
    """skia colour int from (r,g,b[,a]) or '#rrggbb'"""
    if isinstance(c, str):
        c = hexc(c)
    r, g, b = [int(round(max(0, min(255, v)))) for v in c[:3]]
    aa = c[3] if len(c) > 3 else 255
    if a is not None:
        aa = a
    return skia.Color(r, g, b, int(round(max(0, min(255, aa)))))


def mix(c1, c2, t):
    if isinstance(c1, str): c1 = hexc(c1)
    if isinstance(c2, str): c2 = hexc(c2)
    t = max(0.0, min(1.0, t))
    return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(3)) + (255,)


def paint(c, a=None, aa=True, style=None, width=None, cap=None, join=None):
    p = skia.Paint(AntiAlias=aa, Color=col(c, a))
    if style == "stroke":
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(width or 1)
        if cap == "round": p.setStrokeCap(skia.Paint.kRound_Cap)
        if join == "round": p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def clamp01(x): return max(0.0, min(1.0, x))
def lerp(a, b, t): return a + (b - a) * t
def lerp_pts(A, B, t): return [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for a, b in zip(A, B)]
def smooth(t): t = clamp01(t); return t * t * (3 - 2 * t)
def smoother(t): t = clamp01(t); return t * t * t * (t * (6 * t - 15) + 10)
def ease_out(t): t = clamp01(t); return 1 - (1 - t) ** 3
def ease_in(t): t = clamp01(t); return t ** 3
def ease_io(t): t = clamp01(t); return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2
def ease_out_back(t, s=1.7):
    t = clamp01(t); t -= 1
    return t * t * ((s + 1) * t + s) + 1
def seg(t, a, b): return clamp01((t - a) / (b - a)) if b > a else (1.0 if t >= b else 0.0)


def poly(pts, close=True):
    p = skia.Path()
    p.addPoly([skia.Point(float(x), float(y)) for x, y in pts], close)
    return p


def circle(x, y, r):
    p = skia.Path(); p.addCircle(float(x), float(y), float(r)); return p


def oval(cx, cy, rx, ry):
    p = skia.Path(); p.addOval(skia.Rect.MakeLTRB(cx - rx, cy - ry, cx + rx, cy + ry)); return p


def rrect(l, t, r, b, rad):
    p = skia.Path(); p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(l, t, r, b), rad, rad)); return p


def union(*paths):
    out = paths[0]
    for p in paths[1:]:
        out = skia.Op(out, p, skia.PathOp.kUnion_PathOp)
    return out


def smooth_path(pts, close=True, tension=0.5):
    """Catmull-Rom through points -> cubic path"""
    p = skia.Path()
    n = len(pts)
    if n < 3:
        return poly(pts, close)
    p.moveTo(*pts[0])
    rng = range(n) if close else range(n - 1)
    for i in rng:
        p0 = pts[(i - 1) % n] if (close or i > 0) else pts[i]
        p1 = pts[i]; p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (close or i + 2 < n) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) * tension / 3, p1[1] + (p2[1] - p0[1]) * tension / 3)
        c2 = (p2[0] - (p3[0] - p1[0]) * tension / 3, p2[1] - (p3[1] - p1[1]) * tension / 3)
        p.cubicTo(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    if close: p.close()
    return p


def rot(x, y, a):
    c, s = math.cos(a), math.sin(a)
    return x * c - y * s, x * s + y * c


def hash01(*a):
    v = 0
    for x in a:
        v = (v * 1000003) ^ int(x * 7919 + 17)
        v &= 0xFFFFFFFF
    v = (v ^ (v >> 13)) * 0x5bd1e995 & 0xFFFFFFFF
    v ^= v >> 15
    return (v & 0xFFFFFF) / float(0xFFFFFF)
