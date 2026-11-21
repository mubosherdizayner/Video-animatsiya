# Shared helpers: palette, easing, supersampled camera canvas, soft patches, text, grain.
import math, os, functools, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "build")
W, H, FPS = 1080, 1920, 30
SS = 2

def hx(s, a=None):
    s = s.lstrip("#"); c = tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    return c if a is None else c + (int(round(a * 255)),)

# ---------------------------------------------------------------- palette
SKY_TOP, SKY_BOT = hx("E9DEC6"), hx("F4EDDF")
SUN_A, SUN_B = hx("F2A55C"), hx("E1742F")
MTN1, MTN2 = hx("C6CEC9"), hx("AEBBB8")
CITY = hx("8C9FA1"); CITY_D = hx("7F9396")
HOUSE = hx("56696D"); GATE = hx("45575B")
NEAR1, NEAR2 = hx("2E3C40"), hx("33444A")
BANK = hx("2A363A")
LEAF1, LEAF2 = hx("E58A3C"), hx("F0A45E")
WIN = hx("E7A05C")
CREAM = hx("F4EDDF"); INK = hx("1F292C"); ACCENT = hx("E1742F")
# hero
SKIN, SKIN_D = hx("EBC8A2"), hx("D8B089")
HAIR = hx("2E231D")
CHAPAN, CHAPAN_D, CHAPAN_L = hx("3F7B61"), hx("2F634D"), hx("4C8A6E")
IKAT1, IKAT2 = hx("6FA586"), hx("C7A548")
GOLD = hx("BE8642"); BELT = hx("B4473B"); SHIRT = hx("E8E1D3")
DOPPI = hx("1D2427"); BOOT = hx("33241E")
TRAY = hx("2E3C40"); BOWL = hx("E8E1D3"); BOWL_BAND = hx("56696D")

# ---------------------------------------------------------------- easing
def clamp01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def lerp(a, b, t): return a + (b - a) * t
def lerpc(c1, c2, t): return tuple(int(round(a + (b - a) * t)) for a, b in zip(c1, c2))
def ease_out(x): x = clamp01(x); return 1 - (1 - x) ** 3
def ease_in(x): x = clamp01(x); return x ** 3
def ease_io(x): x = clamp01(x); return 3 * x * x - 2 * x * x * x
def ease_io5(x):
    x = clamp01(x); return 16 * x ** 5 if x < 0.5 else 1 - (-2 * x + 2) ** 5 / 2
def ease_out_back(x, s=1.70158):
    x = clamp01(x) - 1; return x * x * ((s + 1) * x + s) + 1
def smooth(a, b, x): return ease_io((x - a) / (b - a)) if b != a else float(x >= a)
def seg(t, a, b): return clamp01((t - a) / (b - a)) if b != a else float(t >= a)

def rot(p, ang, c=(0, 0)):
    a = math.radians(ang); s, co = math.sin(a), math.cos(a)
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * co - y * s, c[1] + x * s + y * co)

def ellipse_pts(cx, cy, rx, ry, n=40, a0=0, a1=360, ang=0):
    pts = []
    for i in range(n + (0 if (a1 - a0) >= 360 else 1)):
        a = math.radians(a0 + (a1 - a0) * i / n)
        p = (cx + rx * math.cos(a), cy + ry * math.sin(a))
        pts.append(rot(p, ang, (cx, cy)) if ang else p)
    return pts

def capsule_pts(p0, p1, r0, r1=None, n=10):
    r1 = r0 if r1 is None else r1
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dy) or 1e-6
    a = math.atan2(dy, dx); pts = []
    for i in range(n + 1):
        t = a + math.pi / 2 + math.pi * i / n
        pts.append((p1[0] + r1 * math.cos(t - math.pi), p1[1] + r1 * math.sin(t - math.pi)))
    for i in range(n + 1):
        t = a + math.pi / 2 + math.pi * i / n
        pts.append((p0[0] + r0 * math.cos(t), p0[1] + r0 * math.sin(t)))
    return pts

def point_in_poly(x, y, poly):
    inside = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xi: inside = not inside
    return inside

def dist_to_poly(x, y, poly):
    best = 1e9; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1; L2 = dx * dx + dy * dy or 1e-9
        t = clamp01(((x - x1) * dx + (y - y1) * dy) / L2)
        best = min(best, math.hypot(x - x1 - t * dx, y - y1 - t * dy))
    return best

# ---------------------------------------------------------------- camera canvas
class Canvas:
    """RGB supersampled canvas; world coords -> screen through a 2D camera with parallax layers."""
    def __init__(self, ss=SS, bg=(0, 0, 0), rgba=False):
        self.ss = ss; self.rgba = rgba
        self.im = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0)) if rgba else Image.new("RGB", (W * ss, H * ss), bg)
        self.d = ImageDraw.Draw(self.im, "RGBA")
        self.cam = (540.0, 960.0, 1.0)
        self.layer(1.0)
        self.ox, self.oy = 0.0, 0.0   # screen-space shake offset

    def set_cam(self, cx, cy, z):
        self.cam = (cx, cy, z); self.layer(self._p)

    def layer(self, p):
        self._p = p
        cx, cy, z = self.cam
        self.ecx = 540 + (cx - 540) * p
        self.ecy = 960 + (cy - 960) * p
        self.ez = 1 + (z - 1) * p
        return self

    def T(self, x, y):
        return ((540 + (x - self.ecx) * self.ez + self.ox) * self.ss,
                (960 + (y - self.ecy) * self.ez + self.oy) * self.ss)

    def S(self, v): return v * self.ez * self.ss
    def screen(self):
        """identity camera (coords = screen px), keeps shake"""
        self._p = None; self.ecx, self.ecy, self.ez = 540.0, 960.0, 1.0
        return self
    def to_screen(self, x, y):
        a, b = self.T(x, y); return a / self.ss, b / self.ss

    def poly(self, pts, fill):
        if len(pts) >= 3: self.d.polygon([self.T(*p) for p in pts], fill=fill)
    def ellipse(self, cx, cy, rx, ry, fill):
        x0, y0 = self.T(cx - rx, cy - ry); x1, y1 = self.T(cx + rx, cy + ry)
        if x1 - x0 >= 0.5 and y1 - y0 >= 0.5: self.d.ellipse((x0, y0, x1, y1), fill=fill)
    def circle(self, cx, cy, r, fill): self.ellipse(cx, cy, r, r, fill)
    def rect(self, x0, y0, x1, y1, fill, r=0):
        a, b = self.T(x0, y0); c, d = self.T(x1, y1)
        a, c = min(a, c), max(a, c); b, d = min(b, d), max(b, d)
        if c - a < 0.5 or d - b < 0.5: return
        if r > 0: self.d.rounded_rectangle((a, b, c, d), radius=self.S(r), fill=fill)
        else: self.d.rectangle((a, b, c, d), fill=fill)
    def line(self, pts, fill, w, caps=True):
        P = [self.T(*p) for p in pts]; ww = max(1, int(round(self.S(w))))
        self.d.line(P, fill=fill, width=ww, joint="curve")
        if caps:
            r = ww / 2
            for (x, y) in (P[0], P[-1]): self.d.ellipse((x - r, y - r, x + r, y + r), fill=fill)
    def capsule(self, p0, p1, r0, r1, fill): self.poly(capsule_pts(p0, p1, r0, r1), fill)

    def paste_rgba(self, img, sx, sy):
        """paste RGBA image (already in supersampled pixels) at supersampled pixel pos"""
        x, y = int(round(sx)), int(round(sy))
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + img.width, self.im.width), min(y + img.height, self.im.height)
        if x1 <= x0 or y1 <= y0: return
        crop = img.crop((x0 - x, y0 - y, x1 - x, y1 - y))
        self.im.paste(crop, (x0, y0), crop)

    def soft(self, bbox, draw_fn, blur=0.0, opacity=1.0, scale=0.5):
        """draw into an RGBA patch covering world bbox (at reduced res), blur, composite"""
        x0, y0 = self.T(bbox[0], bbox[1]); x1, y1 = self.T(bbox[2], bbox[3])
        pad = blur * self.ss * self.ez * 3 + 4
        x0 -= pad; y0 -= pad; x1 += pad; y1 += pad
        x0, y0 = max(x0, -50), max(y0, -50)
        x1, y1 = min(x1, self.im.width + 50), min(y1, self.im.height + 50)
        if x1 - x0 < 2 or y1 - y0 < 2: return
        k = scale
        pw, ph = int((x1 - x0) * k) + 1, int((y1 - y0) * k) + 1
        patch = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        pd = ImageDraw.Draw(patch, "RGBA")
        def tf(x, y):
            a, b = self.T(x, y); return ((a - x0) * k, (b - y0) * k)
        draw_fn(pd, tf, self.ez * self.ss * k)
        if blur > 0: patch = patch.filter(ImageFilter.GaussianBlur(blur * self.ez * self.ss * k))
        if opacity < 0.999:
            a = patch.getchannel("A").point(lambda v: int(v * opacity)); patch.putalpha(a)
        if k != 1: patch = patch.resize((int(round(pw / k)), int(round(ph / k))), Image.BILINEAR)
        self.paste_rgba(patch, x0, y0)

    def result(self):
        if self.rgba:
            return self.im.convert("RGBa").reduce(self.ss).convert("RGBA") if self.ss > 1 else self.im
        return self.im.reduce(self.ss) if self.ss > 1 else self.im

# ---------------------------------------------------------------- noise
def value_noise(w, h, cell, seed):
    rng = np.random.RandomState(seed)
    gw, gh = w // cell + 3, h // cell + 3
    g = rng.rand(gh, gw).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((gw * cell, gh * cell), Image.BICUBIC)
    return np.asarray(im, dtype=np.float32)[:h, :w] / 255.0

def fractal_noise(w, h, seed, cells=(160, 80, 40, 20), amps=(0.5, 0.25, 0.15, 0.1)):
    out = np.zeros((h, w), np.float32)
    for i, (c, a) in enumerate(zip(cells, amps)):
        out += a * value_noise(w, h, c, seed + i * 17)
    return out / sum(amps)

@functools.lru_cache(maxsize=1)
def grain_vignette():
    rng = np.random.RandomState(3)
    g = rng.randn(H, W).astype(np.float32)
    g = np.asarray(Image.fromarray(np.clip(g * 40 + 128, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), np.float32)
    g = (g - 128) / 40.0
    fib = fractal_noise(W, H, 11, (60, 20, 8), (0.5, 0.3, 0.2)) - 0.5
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    vig = 1 - 0.16 * np.clip(r - 0.55, 0, 1) ** 1.6 * 2.2
    mult = (1 + 0.034 * g + 0.03 * fib) * vig
    return mult[..., None].astype(np.float32)

def apply_grain(img):
    a = np.asarray(img, np.float32) * grain_vignette()
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

# ---------------------------------------------------------------- sun texture
@functools.lru_cache(maxsize=1)
def sun_texture(R=560):
    n = 2 * R
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    d = np.sqrt((xx - R + 0.5) ** 2 + (yy - R + 0.5) ** 2)
    t = (yy / n)[..., None]
    base = np.array(SUN_A, np.float32) * (1 - t) + np.array(SUN_B, np.float32) * t
    blot = fractal_noise(n, n, 5, (180, 90, 45, 22), (0.45, 0.3, 0.17, 0.08))
    blot2 = fractal_noise(n, n, 9, (120, 60), (0.6, 0.4))
    k = (blot - 0.5) * 2.2
    col = base * (1 + 0.075 * k[..., None]) + np.array([10, 4, -4], np.float32) * (blot2[..., None] - 0.5) * 2.5
    # soft watercolor rim: slightly darker pigment pooling near the edge
    rim = np.clip((d - R * 0.9) / (R * 0.1), 0, 1)
    col = col * (1 - 0.05 * rim[..., None])
    alpha = np.clip(R - d + 0.5, 0, 1) * 255
    rgba = np.dstack([np.clip(col, 0, 255), alpha]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")

_sun_cache = {}
def draw_sun(cv, cx, cy, r):
    sx, sy = cv.T(cx, cy); rr = cv.S(r)
    size = max(2, int(round(rr * 2)))
    key = size
    if key not in _sun_cache:
        if len(_sun_cache) > 6: _sun_cache.clear()
        _sun_cache[key] = sun_texture().resize((size, size), Image.LANCZOS)
    cv.paste_rgba(_sun_cache[key], sx - size / 2, sy - size / 2)

# ---------------------------------------------------------------- text
FONT_BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
FONT_XBOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_BOLD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

@functools.lru_cache(maxsize=64)
def font(path, size): return ImageFont.truetype(path, int(size))

def uz(s):
    """typographic Uzbek apostrophes: o' g' -> oʻ gʻ, other ' -> ʼ"""
    out = []
    for i, ch in enumerate(s):
        if ch in "'’‘`":
            prev = s[i - 1] if i else ""
            out.append("ʻ" if prev in "oOgG" else "ʼ")
        else: out.append(ch)
    return "".join(out)

def is_emoji(ch): return ord(ch) >= 0x1F000

@functools.lru_cache(maxsize=8)
def emoji_img(ch, size):
    f = ImageFont.truetype(EMOJI, 109)
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    bb = im.getbbox(); im = im.crop(bb)
    s = size / 109 * 1.0
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)

def text_runs(runs, size, path=FONT_BLACK, tracking=0):
    """runs: list of (text, color). returns RGBA image tightly sized to the line (with ascent padding)."""
    f = font(path, size)
    asc, desc = f.getmetrics()
    pieces = []; x = 0
    for txt, col in runs:
        for ch_group in _split_emoji(txt):
            if is_emoji(ch_group[0]):
                im = emoji_img(ch_group, int(size * 1.05)); pieces.append(("img", x, im)); x += im.width + 4
            else:
                w = f.getlength(ch_group) + tracking * len(ch_group)
                pieces.append(("txt", x, ch_group, col)); x += w
    Wd, Hd = int(math.ceil(x)) + 8, asc + desc + 8
    im = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for p in pieces:
        if p[0] == "img":
            im.alpha_composite(p[2], (int(p[1]) + 4, int(4 + asc - p[2].height * 0.92)))
        else:
            if tracking:
                xx = p[1] + 4
                for ch in p[2]:
                    d.text((xx, 4 + asc), ch, font=f, fill=p[3], anchor="ls"); xx += f.getlength(ch) + tracking
            else:
                d.text((p[1] + 4, 4 + asc), p[2], font=f, fill=p[3], anchor="ls")
    return im

def _split_emoji(s):
    out, cur = [], ""
    for ch in s:
        if is_emoji(ch) or ch == "️":
            if cur: out.append(cur); cur = ""
            if ch != "️": out.append(ch)
        else: cur += ch
    if cur: out.append(cur)
    return out

def glow(img, color, radius, strength=1.0, spread=1):
    """soft colored halo behind an RGBA image"""
    pad = int(radius * 3)
    big = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    big.alpha_composite(img, (pad, pad))
    a = big.getchannel("A")
    if spread > 1: a = a.filter(ImageFilter.MaxFilter(spread | 1))
    a = a.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: min(255, int(v * strength)))
    halo = Image.new("RGBA", big.size, color + (0,)); halo.putalpha(a)
    halo.alpha_composite(big)
    return halo
