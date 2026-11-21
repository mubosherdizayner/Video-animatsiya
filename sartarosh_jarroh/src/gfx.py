# Core vector helpers (cairo): palette, easing, outlined + cel-shaded shapes,
# tubes (limbs), surfaces <-> numpy, colour effects (sepia, desaturate, grain).
import math, functools
import numpy as np
import cairocffi as cairo

W, H, FPS = 1080, 1920, 30
PI = math.pi
TAU = 2 * math.pi


def hx(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))


# ---- palette (brief)
TEAL = hx("1E6B6A"); DTEAL = hx("124A4A"); GOLD = hx("E0B04B"); CHAPAN = hx("2E7D4F")
SKIN = hx("D99A6C"); CHEEK = hx("E58A7A"); DOPPI = hx("1B1B1B"); SHIRT = hx("F7F3EA")
POLE_R = hx("D7263D"); WHITE = (1.0, 1.0, 1.0); BRASS = hx("C9A13B")
SEP_L = hx("D8B98C"); SEP_D = hx("6B4A2B"); OL = hx("2B1B12")
# derived
SKIN_D = hx("C07F55"); CHAPAN_D = hx("23633F"); TRIM = hx("7A3B1A"); STEEL = hx("B9C2C9"); STEEL_D = hx("7D8A94")
WOOD = hx("9A6334"); WOOD_D = hx("744722"); MOUTH = hx("7A1E22"); TONGUE = hx("E8737A")
SUBGOLD = hx("F2C14E")


def mul(c, f):
    return tuple(min(1.0, max(0.0, v * f)) for v in c)


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


# ---- easing
def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def lerp(a, b, t):
    return a + (b - a) * t


def eo(x):  # ease-out cubic
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ei(x):
    x = clamp01(x)
    return x ** 3


def eio(x):
    x = clamp01(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def eback(x, s=1.70158):
    x = clamp01(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def ramp(t, t0, dur):
    return clamp01((t - t0) / dur) if dur > 0 else float(t >= t0)


def bump(t, t0, t1):
    """0 -> 1 -> 0 smooth bump between t0 and t1"""
    if t <= t0 or t >= t1:
        return 0.0
    return math.sin(PI * (t - t0) / (t1 - t0))


def damp(t, freq=5.0, decay=5.0):
    if t < 0:
        return 0.0
    return math.exp(-decay * t) * math.sin(TAU * freq * t)


def blink(t, seed=0, period=3.1):
    """0..1 closedness; deterministic blinks ~ every period seconds (4-frame blink)"""
    off = (seed * 0.737) % 1.0 * period
    ph = (t + off) % period
    d = 0.14
    if ph < d:
        return math.sin(PI * ph / d)
    return 0.0


# ---- context helpers
def scale_of(ctx):
    m = ctx.get_matrix()
    return math.sqrt(abs(m.xx * m.yy - m.xy * m.yx))


def olw(ctx, px=6.0):
    return px / max(1e-6, scale_of(ctx))


def stroke_ol(ctx, px=6.0, color=OL, alpha=1.0, preserve=False):
    ctx.set_source_rgba(*color, alpha)
    ctx.set_line_width(olw(ctx, px))
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    if preserve:
        ctx.stroke_preserve()
    else:
        ctx.stroke()


def fill(ctx, color, alpha=1.0, preserve=False):
    ctx.set_source_rgba(*color, alpha)
    if preserve:
        ctx.fill_preserve()
    else:
        ctx.fill()


def fs(ctx, color, ol=6.0, alpha=1.0):
    """fill + outline the current path"""
    ctx.set_source_rgba(*color, alpha)
    if ol:
        ctx.fill_preserve()
        stroke_ol(ctx, ol, alpha=alpha)
    else:
        ctx.fill()


def cel(ctx, path, base, shade=None, d=(10, 8), ol=6.0, alpha=1.0):
    """two-tone cel shaded shape: path(ctx) builds the path. shade = bottom-right crescent"""
    path(ctx)
    fill(ctx, base, alpha)
    if shade is not None:
        ctx.save()
        path(ctx)
        ctx.clip()
        ctx.set_source_rgba(*shade, alpha)
        ctx.paint()
        ctx.translate(-d[0], -d[1])
        path(ctx)
        fill(ctx, base, alpha)
        ctx.restore()
    if ol:
        path(ctx)
        stroke_ol(ctx, ol, alpha=alpha)


# ---- paths
def ellipse(ctx, cx, cy, rx, ry, rot=0.0):
    ctx.save()
    ctx.translate(cx, cy)
    if rot:
        ctx.rotate(rot)
    ctx.scale(max(rx, 1e-3), max(ry, 1e-3))
    ctx.new_sub_path()
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.close_path()
    ctx.restore()


def circle(ctx, cx, cy, r):
    ctx.new_sub_path()
    ctx.arc(cx, cy, max(r, 1e-3), 0, TAU)
    ctx.close_path()


def rrect(ctx, x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -PI / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, PI / 2)
    ctx.arc(x + r, y + h - r, r, PI / 2, PI)
    ctx.arc(x + r, y + r, r, PI, 1.5 * PI)
    ctx.close_path()


def poly(ctx, pts, close=True):
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    if close:
        ctx.close_path()


def smooth(ctx, pts, closed=True, k=0.5):
    """Catmull-Rom through points -> cubic beziers"""
    n = len(pts)
    if n < 3:
        poly(ctx, pts, closed)
        return
    P = list(pts)
    ctx.move_to(*P[0])
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = P[(i - 1) % n] if (closed or i > 0) else P[i]
        p1 = P[i]
        p2 = P[(i + 1) % n]
        p3 = P[(i + 2) % n] if (closed or i + 2 < n) else P[(i + 1) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) * k / 3, p1[1] + (p2[1] - p0[1]) * k / 3)
        c2 = (p2[0] - (p3[0] - p1[0]) * k / 3, p2[1] - (p3[1] - p1[1]) * k / 3)
        ctx.curve_to(*c1, *c2, *p2)
    if closed:
        ctx.close_path()


def tube(ctx, pts, width, color, ol=6.0, alpha=1.0, cap=cairo.LINE_CAP_ROUND):
    def path():
        if len(pts) >= 3:
            smooth(ctx, pts, closed=False)
        else:
            poly(ctx, pts, close=False)
    ctx.set_line_cap(cap)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    if ol:
        path()
        ctx.set_source_rgba(*OL, alpha)
        ctx.set_line_width(width + 2 * olw(ctx, ol))
        ctx.stroke()
    path()
    ctx.set_source_rgba(*color, alpha)
    ctx.set_line_width(width)
    ctx.stroke()


def line(ctx, pts, color=OL, width=6.0, alpha=1.0, px=True, smooth_=False):
    if smooth_ and len(pts) >= 3:
        smooth(ctx, pts, closed=False)
    else:
        poly(ctx, pts, close=False)
    ctx.set_source_rgba(*color, alpha)
    ctx.set_line_width(olw(ctx, width) if px else width)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()


def glow(ctx, cx, cy, r, color, alpha=0.6):
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    g.add_color_stop_rgba(0, *color, alpha)
    g.add_color_stop_rgba(0.45, *color, alpha * 0.35)
    g.add_color_stop_rgba(1, *color, 0)
    ctx.set_source(g)
    circle(ctx, cx, cy, r)
    ctx.fill()


def vgrad(ctx, x, y, w, h, stops):
    g = cairo.LinearGradient(x, y, x, y + h)
    for off, c in stops:
        g.add_color_stop_rgba(off, *c, 1) if len(c) == 3 else g.add_color_stop_rgba(off, *c)
    ctx.set_source(g)
    ctx.rectangle(x, y, w, h)
    ctx.fill()


def sparkle(ctx, x, y, r, alpha=1.0, color=WHITE, rot=0.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    pts = []
    for i in range(8):
        a = i * PI / 4
        rr = r if i % 2 == 0 else r * 0.28
        pts.append((rr * math.sin(a), -rr * math.cos(a)))
    smooth(ctx, pts, closed=True, k=0.15)
    ctx.set_source_rgba(*color, alpha)
    ctx.fill_preserve()
    stroke_ol(ctx, 3, alpha=alpha * 0.9)
    ctx.restore()


# ---- surfaces
def surface(w=W, h=H):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(w), int(h))
    return s, cairo.Context(s)


def np_view(s):
    s.flush()
    return np.ndarray((s.get_height(), s.get_width(), 4), np.uint8, buffer=s.get_data(),
                      strides=(s.get_stride(), 4, 1))


def to_rgb(s):
    a = np_view(s)
    return a[..., [2, 1, 0]].astype(np.float32)


def from_rgb(rgb):
    """float/uint8 RGB (H,W,3) -> opaque cairo surface"""
    h, w = rgb.shape[:2]
    arr = np.empty((h, w, 4), np.uint8)
    c = np.clip(rgb, 0, 255).astype(np.uint8)
    arr[..., 0] = c[..., 2]
    arr[..., 1] = c[..., 1]
    arr[..., 2] = c[..., 0]
    arr[..., 3] = 255
    s = cairo.ImageSurface.create_for_data(memoryview(arr.reshape(-1)), cairo.FORMAT_ARGB32, w, h, w * 4)
    s._keep = arr
    return s


# ---- colour effects on float RGB arrays
_SEP_STOPS = [(0.0, hx("2B1B12")), (0.28, SEP_D), (0.72, SEP_L), (1.0, hx("F1E2C2"))]


@functools.lru_cache(maxsize=1)
def sepia_lut():
    lut = np.zeros((256, 3), np.float32)
    for i in range(256):
        v = i / 255
        for (o0, c0), (o1, c1) in zip(_SEP_STOPS, _SEP_STOPS[1:]):
            if o0 <= v <= o1:
                t = (v - o0) / (o1 - o0)
                lut[i] = [255 * (c0[k] + (c1[k] - c0[k]) * t) for k in range(3)]
                break
    return lut


def lum(rgb):
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


@functools.lru_cache(maxsize=4)
def grain_tex(seed, h=H, w=W):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (h // 2, w // 2)).astype(np.float32)
    # soft paper fibres: mix of fine + blurred noise
    from scipy.ndimage import gaussian_filter, zoom
    coarse = gaussian_filter(rng.normal(0, 1, (h // 8 + 2, w // 8 + 2)).astype(np.float32), 2.0)
    coarse = zoom(coarse, 4, order=1)[:h // 2, :w // 2]
    m = n * 0.6 + coarse * 2.2
    m = np.repeat(np.repeat(m, 2, 0), 2, 1)[:h, :w]
    return m


@functools.lru_cache(maxsize=2)
def vignette(h=H, w=W, strength=0.22):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x - w / 2) / (w * 0.62)) ** 2 + ((y - h / 2) / (h * 0.62)) ** 2)
    return (1 - strength * np.clip(d - 0.45, 0, 1) ** 1.5 / 0.55 ** 1.5).astype(np.float32)


def sepia(rgb, frame=0, amount=1.0, grain=1.0):
    lut = sepia_lut()
    l = lum(rgb)
    idx = np.clip(l, 0, 255).astype(np.uint8)
    sep = lut[idx]
    if grain:
        g = grain_tex((frame // 3) % 3, rgb.shape[0], rgb.shape[1])
        sep = sep + (g * 6.5 * grain)[..., None]
        sep = sep * vignette(rgb.shape[0], rgb.shape[1])[..., None]
    if amount >= 0.999:
        return sep
    return rgb + (sep - rgb) * amount


def desat(rgb, amount):
    l = lum(rgb)[..., None]
    return rgb + (l - rgb) * amount


def brightness(rgb, f):
    return rgb * f


def hblur(rgb, radius):
    """fast horizontal box blur (motion blur) via cumulative sums"""
    r = int(radius)
    if r < 1:
        return rgb
    pad = np.pad(rgb, ((0, 0), (r + 1, r), (0, 0)), mode="edge")
    c = np.cumsum(pad, axis=1, dtype=np.float32)
    out = (c[:, 2 * r + 1:, :] - c[:, :-2 * r - 1, :]) / (2 * r + 1)
    return out[:, :rgb.shape[1], :]
