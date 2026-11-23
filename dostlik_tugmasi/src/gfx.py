# Flat-silhouette drawing helpers on top of skia: colors, shapes, gradients, glows, text, cream plates,
# paper grain and vignette.
import math, functools
import numpy as np
import skia

W, H, FPS = 1080, 1920, 30
FONT_DIR = "/usr/share/fonts/opentype/inter/"
TF_XB = skia.Typeface.MakeFromFile(FONT_DIR + "Inter-ExtraBold.otf")
TF_B = skia.Typeface.MakeFromFile(FONT_DIR + "Inter-Bold.otf")
TF_BLACK = skia.Typeface.MakeFromFile(FONT_DIR + "Inter-Black.otf") or TF_XB

CREAM = "#F4EDDF"; INK = "#1F292C"; ACCENT = "#E58A3C"; HILITE = "#E1742F"
RED = "#C8553D"; GOLD = "#C7A548"; WARM = "#E7A05C"

# ---------------------------------------------------------------- math / easing
def clamp01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def lerp(a, b, t): return a + (b - a) * t
def smooth(t): t = clamp01(t); return t * t * (3 - 2 * t)
def ease_out(t): t = clamp01(t); return 1 - (1 - t) ** 3
def ease_in(t): t = clamp01(t); return t ** 3
def ease_io(t): t = clamp01(t); return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2
def ease_out_back(t, s=1.7):
    t = clamp01(t) - 1; return 1 + (s + 1) * t ** 3 + s * t ** 2
def ramp(t, a, b): return clamp01((t - a) / (b - a)) if b != a else (1.0 if t >= a else 0.0)

# ---------------------------------------------------------------- color
@functools.lru_cache(maxsize=4096)
def rgb(c):
    c = c.lstrip("#"); return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
def hexc(r, g, b): return "#%02X%02X%02X" % (int(round(r)), int(round(g)), int(round(b)))
def mix(c1, c2, t):
    a, b = rgb(c1), rgb(c2); t = clamp01(t)
    return hexc(*(a[i] + (b[i] - a[i]) * t for i in range(3)))
def col(c, a=1.0):
    r, g, b = rgb(c); return skia.ColorSetARGB(int(round(255 * clamp01(a))), r, g, b)

def paint(c, a=1.0, blur=0.0, stroke=0.0, cap="round"):
    p = skia.Paint(AntiAlias=True, Color=col(c, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap if cap == "round" else skia.Paint.kButt_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur > 0: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p

# ---------------------------------------------------------------- paths & shapes
def path(pts, close=True):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    if close: p.close()
    return p

def smooth_path(pts, close=True, tension=0.5):
    """Catmull-Rom through the points."""
    p = skia.Path(); n = len(pts)
    p.moveTo(*pts[0])
    rng = range(n) if close else range(n - 1)
    for i in rng:
        p0 = pts[(i - 1) % n] if (close or i > 0) else pts[0]
        p1 = pts[i]; p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (close or i + 2 < n) else pts[-1]
        c1 = (p1[0] + (p2[0] - p0[0]) * tension / 3, p1[1] + (p2[1] - p0[1]) * tension / 3)
        c2 = (p2[0] - (p3[0] - p1[0]) * tension / 3, p2[1] - (p3[1] - p1[1]) * tension / 3)
        p.cubicTo(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    if close: p.close()
    return p

def poly(cv, pts, c, a=1.0, blur=0.0):
    cv.drawPath(path(pts), paint(c, a, blur))

def spoly(cv, pts, c, a=1.0):
    cv.drawPath(smooth_path(pts), paint(c, a))

def line(cv, pts, c, w, a=1.0, cap="round"):
    cv.drawPath(path(pts, close=False), paint(c, a, stroke=w, cap=cap))

def circle(cv, x, y, r, c, a=1.0, blur=0.0):
    cv.drawCircle(x, y, r, paint(c, a, blur))

def ellipse(cv, x, y, rx, ry, c, a=1.0, rot=0.0, blur=0.0):
    if rot:
        cv.save(); cv.translate(x, y); cv.rotate(rot)
        cv.drawOval(skia.Rect.MakeLTRB(-rx, -ry, rx, ry), paint(c, a, blur)); cv.restore()
    else:
        cv.drawOval(skia.Rect.MakeLTRB(x - rx, y - ry, x + rx, y + ry), paint(c, a, blur))

def rrect(cv, x, y, w, h, r, c, a=1.0, blur=0.0):
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), paint(c, a, blur))

def rrect_stroke(cv, x, y, w, h, r, c, sw, a=1.0):
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), paint(c, a, stroke=sw))

def diamond(cv, x, y, hw, hh, c, a=1.0):
    poly(cv, [(x, y - hh), (x + hw, y), (x, y + hh), (x - hw, y)], c, a)

def vgrad(cv, rect, c_top, c_bot, a=1.0):
    x0, y0, x1, y1 = rect
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, y0), skia.Point(0, y1)], [col(c_top, a), col(c_bot, a)]))
    cv.drawRect(skia.Rect.MakeLTRB(x0, y0, x1, y1), p)

def glow(cv, x, y, r, c, a=1.0):
    """soft radial glow"""
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(x, y), max(r, 1), [col(c, a), col(c, a * 0.45), col(c, 0)], [0.0, 0.35, 1.0]))
    cv.drawCircle(x, y, r, p)

class layer_alpha:
    """with layer_alpha(cv, a): draw group with opacity"""
    def __init__(self, cv, a): self.cv, self.a = cv, a
    def __enter__(self):
        if self.a < 0.999: self.cv.saveLayerAlpha(None, int(255 * clamp01(self.a)))
        else: self.cv.save()
    def __exit__(self, *e): self.cv.restore()

class xf:
    """with xf(cv, tx, ty, s, rot): local transform"""
    def __init__(self, cv, tx=0, ty=0, s=1.0, rot=0.0, sx=None):
        self.cv, self.tx, self.ty, self.s, self.rot, self.sx = cv, tx, ty, s, rot, sx
    def __enter__(self):
        self.cv.save(); self.cv.translate(self.tx, self.ty)
        if self.rot: self.cv.rotate(self.rot)
        self.cv.scale(self.s if self.sx is None else self.sx, self.s)
    def __exit__(self, *e): self.cv.restore()

# ---------------------------------------------------------------- text
@functools.lru_cache(maxsize=256)
def font(size, tf="xb"):
    f = skia.Font({"xb": TF_XB, "b": TF_B, "black": TF_BLACK}[tf], size)
    f.setEdging(skia.Font.Edging.kAntiAlias); f.setSubpixel(True)
    return f

def text_w(s, size, tf="xb"): return font(size, tf).measureText(s)

def text(cv, s, x, y, size, c=INK, a=1.0, align="center", tf="xb"):
    """y = vertical center of cap height"""
    f = font(size, tf); w = f.measureText(s)
    if align == "center": x -= w / 2
    elif align == "right": x -= w
    cv.drawString(s, x, y + size * 0.36, f, paint(c, a))
    return w

def text_runs(cv, runs, x, y, size, a=1.0, align="center", tf="xb"):
    """runs = [(string, color), ...] laid out on one line"""
    tot = sum(text_w(s, size, tf) for s, _ in runs)
    if align == "center": x -= tot / 2
    for s, c in runs:
        x += text(cv, s, x, y, size, c, a, "left", tf)
    return tot

# ---------------------------------------------------------------- cream UI
def plate(cv, x, y, w, h, r=None, a=0.85, c=CREAM):
    rrect(cv, x, y, w, h, r if r is not None else min(h / 2, 30), c, a)

def tag(cv, s, cx, bottom, size=34, a=1.0, scale=1.0, c_text=INK, pointer=True):
    """small cream tag with a little pointer under it; bottom = pointer tip"""
    if a <= 0.01 or scale <= 0.01: return
    w = text_w(s, size) + size * 1.1; h = size * 1.75
    with xf(cv, cx, bottom, scale):
        with layer_alpha(cv, a):
            y0 = -h - (12 if pointer else 0)
            plate(cv, -w / 2, y0, w, h, h * 0.32, 0.92)
            if pointer: poly(cv, [(-11, y0 + h - 1), (11, y0 + h - 1), (0, 0)], CREAM, 0.92)
            text(cv, s, 0, y0 + h / 2, size, c_text)

def pop_scale(t, dur=0.3):
    """0 -> overshoot -> 1"""
    return ease_out_back(t / dur, 2.4) if t < dur else 1.0

# ---------------------------------------------------------------- paper grain + vignette (precomputed)
@functools.lru_cache(maxsize=1)
def grain_image():
    rng = np.random.default_rng(11)
    n = rng.normal(0, 1, (H, W)).astype(np.float32)
    # a touch of fibre: short horizontal smear + low-frequency blotches
    n = 0.6 * n + 0.4 * (np.roll(n, 1, 1) + np.roll(n, -1, 1)) / 2
    lo = rng.normal(0, 1, (H // 60 + 2, W // 60 + 2)).astype(np.float32)
    from scipy.ndimage import zoom, gaussian_filter
    lo = gaussian_filter(zoom(lo, 60, order=3)[:H, :W], 8)
    v = 128 + 15 * n + 9 * lo / (np.abs(lo).max() + 1e-6)
    v = np.clip(v, 0, 255).astype(np.uint8)
    rgba = np.dstack([v, v, v, np.full_like(v, 255)])
    return skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType)

def grain(cv, strength=0.55):
    p = skia.Paint(); p.setBlendMode(skia.BlendMode.kOverlay); p.setAlphaf(strength)
    cv.drawImage(grain_image(), 0, 0, skia.SamplingOptions(), p)

def vignette(cv, strength=0.30, c="#2A2118"):
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(W / 2, H * 0.47), H * 0.66,
                [col(c, 0), col(c, 0), col(c, strength * 0.55), col(c, strength)], [0.0, 0.55, 0.82, 1.0]))
    p.setBlendMode(skia.BlendMode.kMultiply)
    cv.drawRect(skia.Rect.MakeWH(W, H), p)
