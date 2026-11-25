# Minimalist silhouette style helpers (cairo): colours, palettes, sky, sun/moon disc, layered hills,
# fog, grass, paper grain, vignette.
import math, random, functools
import numpy as np
import cairo

W, H, FPS = 1080, 1920, 30

# ------------------------------------------------------------------ colour utils
def hx(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))

def lighten(c, t): return mix(c, (1, 1, 1), t)
def darken(c, t): return mix(c, (0, 0, 0), t)

def _lin(c): return [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
def _gam(c): return [12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055 for v in c]
_M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
_Mi = np.linalg.inv(_M)
_WN = (0.95047, 1.0, 1.08883)
def _f(t): return np.cbrt(t) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29
def _fi(t): return t ** 3 if t > 6 / 29 else 3 * (6 / 29) ** 2 * (t - 4 / 29)

def to_lab(c):
    X, Y, Z = _M @ np.array(_lin(c))
    fx, fy, fz = _f(X / _WN[0]), _f(Y / _WN[1]), _f(Z / _WN[2])
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)

def from_lab(L, a, b):
    fy = (L + 16) / 116; fx = fy + a / 500; fz = fy - b / 200
    X, Y, Z = _WN[0] * _fi(fx), _WN[1] * _fi(fy), _WN[2] * _fi(fz)
    rgb = _Mi @ np.array([X, Y, Z])
    return tuple(min(1.0, max(0.0, v)) for v in _gam(list(np.clip(rgb, 0, 1))))

def chroma(c):
    L, a, b = to_lab(c); return math.hypot(a, b)

# The hero's chopon (#3F7B61, CIELAB chroma 27.4) must stay the most saturated colour in every frame he is in.
# The script's accent hexes are all more saturated than that, so in hero frames they are drawn with their
# chroma capped below the chopon (same hue and lightness). Frames without the hero use the exact hexes.
ACCENT_CHROMA_CAP = 22.0
_MUTE = {"on": False}
def set_hero_frame(on): _MUTE["on"] = bool(on)

@functools.lru_cache(maxsize=512)
def _muted(c, cap):
    L, a, b = to_lab(c); C = math.hypot(a, b)
    if C <= cap: return c
    k = cap / C
    return from_lab(L, a * k, b * k)

def acc(c):
    """accent colour, chroma-capped in hero frames"""
    return _muted(tuple(round(v, 5) for v in c), ACCENT_CHROMA_CAP) if _MUTE["on"] else c

# ------------------------------------------------------------------ palettes
def P(sky0, sky1, disc0, disc1, layers, accent, glow):
    return {"sky0": hx(sky0), "sky1": hx(sky1), "disc0": hx(disc0), "disc1": hx(disc1),
            "L": [hx(c) for c in layers], "accent": hx(accent), "glow": hx(glow)}

DAWN = P("#F3E3D3", "#E6EDEF", "#F6C98A", "#F6C98A", ["#D5DDDA", "#B8C6C4", "#93A5A6", "#64777A", "#3C4B4F"], "#E7A05C", "#E7A05C")
DUSK = P("#E9DEC6", "#F4EDDF", "#F2A55C", "#E1742F", ["#C6CEC9", "#AEBBB8", "#8C9FA1", "#56696D", "#2E3C40"], "#E58A3C", "#E7A05C")
NIGHT = P("#1F2A3A", "#3A4A5C", "#EDE6D2", "#EDE6D2", ["#4A5A6E", "#36455A", "#283547", "#1A2433", "#10171F"], "#E7A05C", "#E7A05C")

def pal_mix(a, b, t):
    out = {}
    for k in a:
        if k == "L": out[k] = [mix(x, y, t) for x, y in zip(a[k], b[k])]
        else: out[k] = mix(a[k], b[k], t)
    return out

def pal_grey(p, t):
    """desaturate a palette toward grey by t"""
    def g(c):
        y = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
        return mix(c, (y, y, y), t)
    out = {}
    for k in p:
        out[k] = [g(c) for c in p[k]] if k == "L" else g(p[k])
    return out

RED_BTN = hx("#A9473C"); GOLD_BTN = hx("#C9A04A"); MONEY = hx("#E7A05C"); SCARF = hx("#D9AEB1")
THREAD = hx("#A9473C"); LAMP = hx("#E7A05C")

# ------------------------------------------------------------------ easing
def clamp01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def lerp(a, b, t): return a + (b - a) * t
def ease(x): x = clamp01(x); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp01(x); return 1 - (1 - x) ** 3
def ease_in(x): x = clamp01(x); return x ** 3
def ease_io_sine(x): x = clamp01(x); return -(math.cos(math.pi * x) - 1) / 2
def ease_out_back(x, s=1.7):
    x = clamp01(x) - 1; return x * x * ((s + 1) * x + s) + 1
def smoothstep(a, b, x): return ease((x - a) / (b - a)) if b != a else float(x >= a)

# ------------------------------------------------------------------ cairo basics
def new_surface(w=W, h=H):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    return s, cairo.Context(s)

def rgb(ctx, c, a=1.0):
    if a >= 0.999: ctx.set_source_rgb(*c)
    else: ctx.set_source_rgba(c[0], c[1], c[2], a)

def poly(ctx, pts, close=True):
    ctx.move_to(*pts[0])
    for p in pts[1:]: ctx.line_to(*p)
    if close: ctx.close_path()

def smooth_path(ctx, pts, close=False, tension=0.5):
    """Catmull-Rom through pts"""
    n = len(pts)
    if n < 3:
        poly(ctx, pts, close); return
    P_ = pts + pts[:3] if close else [pts[0]] + pts + [pts[-1]]
    if not close: ctx.move_to(*pts[0])
    else: ctx.move_to(*P_[1])
    rng = range(1, n + 1) if close else range(1, n)
    for i in rng:
        p0, p1, p2, p3 = P_[i - 1], P_[i], P_[i + 1], P_[i + 2] if i + 2 < len(P_) else P_[-1]
        c1 = (p1[0] + (p2[0] - p0[0]) * tension / 3, p1[1] + (p2[1] - p0[1]) * tension / 3)
        c2 = (p2[0] - (p3[0] - p1[0]) * tension / 3, p2[1] - (p3[1] - p1[1]) * tension / 3)
        ctx.curve_to(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    if close: ctx.close_path()

def ellipse(ctx, cx, cy, rx, ry, rot=0.0):
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(rot); ctx.scale(max(rx, 1e-3), max(ry, 1e-3))
    ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore()

def fill_ellipse(ctx, cx, cy, rx, ry, c, a=1.0, rot=0.0):
    ellipse(ctx, cx, cy, rx, ry, rot); rgb(ctx, c, a); ctx.fill()

def rrect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()

def glow(ctx, cx, cy, r, c, a=0.5):
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    g.add_color_stop_rgba(0, c[0], c[1], c[2], a)
    g.add_color_stop_rgba(0.35, c[0], c[1], c[2], a * 0.45)
    g.add_color_stop_rgba(1, c[0], c[1], c[2], 0)
    ctx.set_source(g); ctx.arc(cx, cy, r, 0, 2 * math.pi); ctx.fill()

# ------------------------------------------------------------------ sky, disc
def sky(ctx, p, y0=0, y1=H):
    g = cairo.LinearGradient(0, y0, 0, y1)
    g.add_color_stop_rgb(0, *p["sky0"]); g.add_color_stop_rgb(1, *p["sky1"])
    ctx.set_source(g); ctx.paint()

def disc(ctx, cx, cy, r, c0, c1, seed=3, t=0.0, alpha=1.0):
    """flat sun/moon disc with soft watercolour blotches inside"""
    ctx.save()
    ctx.arc(cx, cy, r, 0, 2 * math.pi); ctx.clip()
    g = cairo.LinearGradient(0, cy - r, 0, cy + r)
    g.add_color_stop_rgba(0, c0[0], c0[1], c0[2], alpha); g.add_color_stop_rgba(1, c1[0], c1[1], c1[2], alpha)
    ctx.set_source(g); ctx.paint()
    rnd = random.Random(seed)
    for k in range(9):
        ang = rnd.uniform(0, 6.28); d = rnd.uniform(0.1, 0.75) * r
        bx, by = cx + math.cos(ang + 0.05 * t) * d, cy + math.sin(ang + 0.05 * t) * d
        br = rnd.uniform(0.22, 0.5) * r
        tone = darken(c1, 0.10) if k % 2 else lighten(c0, 0.18)
        gg = cairo.RadialGradient(bx, by, 0, bx, by, br)
        a = rnd.uniform(0.10, 0.22) * alpha
        gg.add_color_stop_rgba(0, tone[0], tone[1], tone[2], a)
        gg.add_color_stop_rgba(0.6, tone[0], tone[1], tone[2], a * 0.6)
        gg.add_color_stop_rgba(1, tone[0], tone[1], tone[2], 0)
        ctx.set_source(gg); ctx.arc(bx, by, br, 0, 2 * math.pi); ctx.fill()
    ctx.restore()

# ------------------------------------------------------------------ hills / ridges
def ridge_y(x, seed, amp, base, freq=1.0):
    rnd = random.Random(seed)
    v = 0.0
    for k in range(4):
        f = freq * (0.0015 + 0.0028 * k) * rnd.uniform(0.7, 1.3)
        ph = rnd.uniform(0, 6.28)
        v += math.sin(x * f + ph) / (1 + 0.9 * k)
    return base - amp * v

def ridge(ctx, c, seed, amp, base, x0=-400, x1=W + 400, step=12, freq=1.0, a=1.0, bottom=H + 400, fn=None):
    ctx.move_to(x0, bottom)
    x = x0
    while x <= x1:
        y = fn(x) if fn else ridge_y(x, seed, amp, base, freq)
        ctx.line_to(x, y); x += step
    ctx.line_to(x1, bottom); ctx.close_path()
    rgb(ctx, c, a); ctx.fill()

def fog(ctx, y, c, t, a=0.35, h=120, seed=0, speed=12.0, n=6, x0=-300, x1=W + 300):
    """soft fog band built from wide radial blobs drifting sideways"""
    rnd = random.Random(seed)
    span = x1 - x0
    for k in range(n):
        bx = x0 + ((rnd.uniform(0, span) + speed * t * rnd.uniform(0.7, 1.3)) % span)
        by = y + rnd.uniform(-h * 0.25, h * 0.25)
        rx = rnd.uniform(260, 460); ry = h * rnd.uniform(0.55, 0.9)
        ctx.save(); ctx.translate(bx, by); ctx.scale(rx / ry, 1)
        g = cairo.RadialGradient(0, 0, 0, 0, 0, ry)
        aa = a * rnd.uniform(0.6, 1.0)
        g.add_color_stop_rgba(0, c[0], c[1], c[2], aa)
        g.add_color_stop_rgba(0.5, c[0], c[1], c[2], aa * 0.55)
        g.add_color_stop_rgba(1, c[0], c[1], c[2], 0)
        ctx.set_source(g); ctx.arc(0, 0, ry, 0, 2 * math.pi); ctx.fill(); ctx.restore()

def fog_band(ctx, y, h, c, a):
    g = cairo.LinearGradient(0, y - h, 0, y + h)
    g.add_color_stop_rgba(0, c[0], c[1], c[2], 0)
    g.add_color_stop_rgba(0.5, c[0], c[1], c[2], a)
    g.add_color_stop_rgba(1, c[0], c[1], c[2], 0)
    ctx.set_source(g); ctx.rectangle(-500, y - h, W + 1000, 2 * h); ctx.fill()

def grass(ctx, c, ground_fn, x0, x1, t, seed=1, density=0.09, hmin=14, hmax=38, wind=1.0, gust=0.0, a=1.0, wmax=7):
    """tufts of flat blades along a ground line, swaying in the wind"""
    rnd = random.Random(seed)
    n = int((x1 - x0) * density)
    rgb(ctx, c, a)
    for i in range(n):
        x = x0 + rnd.uniform(0, x1 - x0)
        y = ground_fn(x) + 2
        hh = rnd.uniform(hmin, hmax); ww = rnd.uniform(3, wmax)
        ph = rnd.uniform(0, 6.28)
        sway = (0.18 + 0.5 * gust) * wind * math.sin(t * (2.2 + 2.5 * gust) + x * 0.012 + ph) + 0.55 * gust + 0.12 * wind
        tipx = x + hh * math.sin(sway); tipy = y - hh * math.cos(sway)
        midx = x + hh * 0.5 * math.sin(sway * 0.5)
        ctx.move_to(x - ww / 2, y)
        ctx.curve_to(midx - ww * 0.3, y - hh * 0.5, tipx, tipy + hh * 0.2, tipx, tipy)
        ctx.curve_to(tipx, tipy + hh * 0.2, midx + ww * 0.3, y - hh * 0.5, x + ww / 2, y)
        ctx.close_path()
    ctx.fill()

# ------------------------------------------------------------------ post: grain + vignette
@functools.lru_cache(maxsize=1)
def grain_vignette():
    rs = np.random.RandomState(11)
    n = rs.randn(H // 2, W // 2).astype(np.float32)
    # soft paper fibres: blur a little by box filter, then upsample
    k = np.ones(3, np.float32) / 3
    n = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 1, n)
    n = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 0, n)
    n = np.repeat(np.repeat(n, 2, 0), 2, 1)
    fine = rs.randn(H, W).astype(np.float32) * 0.5
    g = (n * 0.8 + fine) / 1.3
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    vig = 1.0 - 0.20 * np.clip(d - 0.45, 0, None) ** 1.6 / (0.85 ** 1.6)
    vig = np.clip(vig, 0.78, 1.0)
    mul = (vig * (1.0 + 0.032 * g)).astype(np.float32)
    return mul[..., None]

def surface_rgb(surf):
    buf = surf.get_data()
    a = np.ndarray((H, W, 4), np.uint8, buf)
    return a[..., [2, 1, 0]].astype(np.float32)

def finish(arr, grey=0.0, flash=0.0, bright=1.0):
    """arr float32 HxWx3 (0..255) -> uint8 with grain + vignette"""
    if grey > 0:
        y = arr @ np.array([0.299, 0.587, 0.114], np.float32)
        arr = arr + (y[..., None] - arr) * grey
    if bright != 1.0: arr = arr * bright
    arr = arr * grain_vignette()
    if flash > 0:
        arr = arr + (np.float32(250) - arr) * flash
    return np.clip(arr, 0, 255).astype(np.uint8)
