# Flat-silhouette drawing engine: palettes, easing, supersampled pens, sky, sun, grain, vignette.
import math, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

W, H, FPS = 1080, 1920, 30
SS = 3                                   # supersampling factor for anti-aliased flat shapes


def hx(s, a=None):
    s = s.lstrip('#'); c = tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    return c if a is None else c + (a,)


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(min(len(a), len(b))))


def clamp01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def lerp(a, b, t): return a + (b - a) * t
def smooth(x): x = clamp01(x); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp01(x); return 1 - (1 - x) ** 3
def ease_in(x): x = clamp01(x); return x ** 3
def ease_io(x): x = clamp01(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def ease_back(x, s=1.9): x = clamp01(x) - 1; return 1 + (s + 1) * x ** 3 + s * x ** 2
def ramp(t, a, b): return clamp01((t - a) / (b - a)) if b != a else float(t >= a)


# ---------------------------------------------------------------- palettes
ACCENT = hx('#E1742F'); CREAM = hx('#F4EDDF'); INK = hx('#1F292C')
PAL = {
    'A': dict(sky0=hx('#E9DEC6'), sky1=hx('#F4EDDF'), sun0=hx('#F2A55C'), sun1=hx('#E1742F'),
              L=[hx(c) for c in ('#C6CEC9', '#AEBBB8', '#8C9FA1', '#56696D', '#2E3C40')],
              win=hx('#F2A55C'), mist=hx('#E6EDEF'), mist_a=0.0, cloud=hx('#F7F0E2')),
    'B': dict(sky0=hx('#F3E3D3'), sky1=hx('#E6EDEF'), sun0=hx('#F6C98A'), sun1=hx('#F1BA72'),
              L=[hx(c) for c in ('#D5DDDA', '#B8C6C4', '#93A5A6', '#64777A', '#3C4B4F')],
              win=hx('#F6C98A'), mist=hx('#E6EDEF'), mist_a=0.35, cloud=hx('#F7EEE6')),
}


def pal_mix(t):
    """t=0 -> SHOM (A), t=1 -> TONG (B)"""
    a, b = PAL['A'], PAL['B']
    if t <= 0: return a
    if t >= 1: return b
    out = {}
    for k in a:
        if k == 'L': out[k] = [mix(x, y, t) for x, y in zip(a[k], b[k])]
        elif isinstance(a[k], tuple): out[k] = mix(a[k], b[k], t)
        else: out[k] = lerp(a[k], b[k], t)
    return out


# ---------------------------------------------------------------- geometry helpers
def catmull(pts, n=6, closed=True):
    """Smooth closed/open polyline through control points (Catmull-Rom)."""
    P = list(pts); out = []
    m = len(P)
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0 = P[(i - 1) % m] if closed or i > 0 else P[0]
        p1 = P[i]; p2 = P[(i + 1) % m]
        p3 = P[(i + 2) % m] if closed or i + 2 < m else P[-1]
        for k in range(n):
            t = k / n; t2 = t * t; t3 = t2 * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    if not closed: out.append(P[-1])
    return out


def rot(p, a, c=(0, 0)):
    s, co = math.sin(a), math.cos(a); x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * co - y * s, c[1] + x * s + y * co)


def capsule_pts(p0, p1, w0, w1, n=10):
    """Tapered segment with round ends as polygon."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dy) or 1e-6
    ang = math.atan2(dy, dx); pts = []
    for k in range(n + 1):
        a = ang + math.pi / 2 + math.pi * k / n
        pts.append((p0[0] + w0 / 2 * math.cos(a), p0[1] + w0 / 2 * math.sin(a)))
    for k in range(n + 1):
        a = ang - math.pi / 2 + math.pi * k / n
        pts.append((p1[0] + w1 / 2 * math.cos(a), p1[1] + w1 / 2 * math.sin(a)))
    return pts


def circle_pts(cx, cy, rx, ry=None, n=40, a0=0.0):
    ry = rx if ry is None else ry
    return [(cx + rx * math.cos(a0 + 2 * math.pi * k / n), cy + ry * math.sin(a0 + 2 * math.pi * k / n)) for k in range(n)]


# ---------------------------------------------------------------- pens
class Pen:
    """Supersampled RGBA drawing canvas with an affine transform design->pixel.
    x_px = ox + s*(fx*x*cos(r) - y*sin(r)), y_px = oy + s*(fx*x*sin(r) + y*cos(r))"""

    def __init__(self, w, h, s=1.0, ox=0.0, oy=0.0, flip=False, rot_deg=0.0, mode='RGBA', ss=None):
        self.w, self.h = max(1, int(w)), max(1, int(h)); self.ss = ss or SS
        self.im = Image.new(mode, (self.w * self.ss, self.h * self.ss), (0, 0, 0, 0) if mode == 'RGBA' else 0)
        self.d = ImageDraw.Draw(self.im)
        self.s, self.ox, self.oy, self.fx = s, ox, oy, (-1 if flip else 1)
        self.r = math.radians(rot_deg); self.cr, self.sr = math.cos(self.r), math.sin(self.r)

    def T(self, p):
        x, y = p[0] * self.fx, p[1]
        X = x * self.cr - y * self.sr; Y = x * self.sr + y * self.cr
        return ((self.ox + self.s * X) * self.ss, (self.oy + self.s * Y) * self.ss)

    def poly(self, pts, c):
        if len(pts) >= 3: self.d.polygon([self.T(p) for p in pts], fill=c)

    def smooth(self, pts, c, n=6): self.poly(catmull(pts, n), c)
    def ellipse(self, cx, cy, rx, ry, c, a0=0.0): self.poly(circle_pts(cx, cy, rx, ry, 48, a0), c)
    def circle(self, cx, cy, r, c): self.ellipse(cx, cy, r, r, c)
    def capsule(self, p0, p1, w0, w1, c): self.poly(capsule_pts(p0, p1, w0, w1), c)
    def rect(self, x0, y0, x1, y1, c): self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], c)

    def rrect(self, x0, y0, x1, y1, r, c, n=8):
        pts = []
        for (cx, cy, a) in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
            for k in range(n + 1):
                aa = math.radians(a + 90 * k / n); pts.append((cx + r * math.cos(aa), cy + r * math.sin(aa)))
        self.poly(pts, c)

    def line(self, pts, c, w):
        for a, b in zip(pts[:-1], pts[1:]): self.capsule(a, b, w, w, c)

    def result(self):
        return self.im.resize((self.w, self.h), Image.BOX)   # premultiplied box filter for RGBA


def mask_pen(w, h, **kw): return Pen(w, h, mode='L', **kw)


def paste_color(frame, color, mask, xy=(0, 0), alpha=1.0):
    if alpha < 1.0: mask = mask.point(lambda v: int(v * alpha))
    if alpha <= 0.003: return
    frame.paste(color, (int(xy[0]), int(xy[1])) + (int(xy[0]) + mask.width, int(xy[1]) + mask.height), mask)


def with_alpha(im, a):
    if a >= 0.999: return im
    im = im.copy(); al = im.getchannel('A').point(lambda v: int(v * a)); im.putalpha(al); return im


def comp(frame, im, xy):
    """alpha-composite RGBA sprite at float position (rounded), clipped to frame"""
    x, y = int(round(xy[0])), int(round(xy[1]))
    if x >= frame.width or y >= frame.height or x + im.width <= 0 or y + im.height <= 0: return
    cx0, cy0 = max(0, -x), max(0, -y)
    cx1, cy1 = min(im.width, frame.width - x), min(im.height, frame.height - y)
    if cx0 or cy0 or cx1 < im.width or cy1 < im.height:
        im = im.crop((cx0, cy0, cx1, cy1)); x += cx0; y += cy0
    frame.alpha_composite(im, (x, y))


# ---------------------------------------------------------------- sky, sun, clouds, grain, vignette
@functools.lru_cache(maxsize=64)
def _grad_col(c0, c1, h, y0, y1):
    ys = np.arange(h, dtype=np.float32)
    t = np.clip((ys - y0) / max(1, (y1 - y0)), 0, 1)[:, None]
    col = np.array(c0, np.float32)[None] * (1 - t) + np.array(c1, np.float32)[None] * t
    return col


def sky(pal, w=W, h=H, y0=0, y1=1300):
    col = _grad_col(pal['sky0'], pal['sky1'], h, y0, y1)
    arr = np.repeat(col[:, None, :], w, axis=1).astype(np.uint8)
    return Image.fromarray(arr, 'RGB').convert('RGBA')


@functools.lru_cache(maxsize=16)
def sun_sprite(c0, c1, r, seed=3):
    """Flat sun disk with soft watercolor blotches inside (no outline)."""
    rng = np.random.RandomState(seed)
    S = 2 * r + 8
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    cx = cy = S / 2
    t = np.clip((yy - (cy - r)) / (2 * r), 0, 1)[..., None]
    col = np.array(c0, np.float32) * (1 - t) + np.array(c1, np.float32) * t
    # watercolor blotches: smooth low-frequency noise blobs
    blot = np.zeros((S, S), np.float32)
    for k in range(9):
        bx, by = cx + rng.uniform(-.6, .6) * r, cy + rng.uniform(-.6, .6) * r
        br = rng.uniform(.18, .42) * r; amp = rng.uniform(-1, 1)
        blot += amp * np.exp(-(((xx - bx) ** 2 + (yy - by) ** 2) / (2 * br * br)))
    blot = blot / (np.abs(blot).max() + 1e-6)
    col = col * (1 + 0.055 * blot[..., None])
    # soft ring of darker pigment at the inner edge (watercolor edge darkening)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    col = col * (1 - 0.035 * np.clip((d - 0.82 * r) / (0.18 * r), 0, 1)[..., None])
    a = np.clip(r - d + 0.5, 0, 1) * 255
    arr = np.dstack([np.clip(col, 0, 255), a]).astype(np.uint8)
    return Image.fromarray(arr, 'RGBA')


def sun_img(pal, r):
    return sun_sprite(pal['sun0'], pal['sun1'], int(r))


@functools.lru_cache(maxsize=32)
def cloud_mask(w, h, seed):
    rng = np.random.RandomState(seed)
    p = mask_pen(w, h)
    # thin flat cloud: a long rounded band with 2-3 bumps on top
    p.rrect(0, h * 0.55, w, h, h * 0.22, 255)
    for k in range(rng.randint(2, 4)):
        bx = rng.uniform(0.15, 0.75) * w; bw = rng.uniform(0.18, 0.35) * w
        p.rrect(bx, h * rng.uniform(0.15, 0.35), bx + bw, h * 0.9, h * 0.3, 255)
    return p.result()


@functools.lru_cache(maxsize=2)
def grain_layers(seed=11):
    rng = np.random.RandomState(seed)
    n = rng.normal(0, 1, (H, W)).astype(np.float32)
    n = np.array(Image.fromarray(np.clip(n * 40 + 128, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7)), np.float32) - 128
    # paper fibre: very low-frequency mottling
    lo = rng.normal(0, 1, (H // 24, W // 24)).astype(np.float32)
    lo = np.array(Image.fromarray(np.clip(lo * 40 + 128, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) - 128
    g = n * 0.13 + lo * 0.025
    pos = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert('RGB')
    neg = Image.fromarray(np.clip(-g, 0, 255).astype(np.uint8)).convert('RGB')
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    v = 1 - 0.16 * np.clip(d - 0.45, 0, 1) ** 1.6 / 0.55 ** 1.6
    vig = Image.fromarray(np.clip(v * 255, 0, 255).astype(np.uint8)).convert('RGB')
    return pos, neg, vig


def finish(frame_rgb):
    pos, neg, vig = grain_layers()
    f = ImageChops.multiply(frame_rgb, vig)
    f = ImageChops.add(f, pos); f = ImageChops.subtract(f, neg)
    return f


def zoom(frame, s, cx=W / 2, cy=H / 2):
    """camera push-in: scale >=1 around (cx,cy)"""
    if abs(s - 1) < 1e-4: return frame
    w, h = frame.width / s, frame.height / s
    x0 = cx - w * (cx / frame.width); y0 = cy - h * (cy / frame.height)
    return frame.transform(frame.size, Image.EXTENT, (x0, y0, x0 + w, y0 + h), Image.BILINEAR)


def desaturate(img, amount):
    g = img.convert('L').convert(img.mode)
    return Image.blend(img, g, amount)
