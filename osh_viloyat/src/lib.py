# Shared helpers: easing, supersampled vector canvas, fonts/text, hero sprites, camera.
import math, os, json, functools, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPR_DIR = os.path.join(ROOT, "build", "sprites")
FONT_DIR = os.path.join(ROOT, "fonts")
FONT_MAIN = os.path.join(FONT_DIR, "Nunito-Black.ttf")
FONT_FALLBACK = os.path.join(FONT_DIR, "NotoSans-Bold.ttf")

W, H, FPS = 1080, 1920, 30
M = 140                       # world canvas margin (camera moves / tilts never show an edge)
WW, WH = W + 2 * M, H + 2 * M

# palette
OL = (34, 22, 16)
TEAL_TOP = (13, 78, 84)
TEAL_MID = (18, 98, 102)
TEAL_BOT = (7, 48, 54)
GOLD = (236, 184, 64)
GOLD_D = (178, 124, 30)
GOLD_L = (255, 222, 130)
CHAPAN = (24, 120, 96)
RED = (198, 32, 46)
RED_D = (140, 18, 30)
CREAM = (255, 246, 226)
WHITE = (255, 255, 255)
YELLOW = (255, 221, 0)
COBALT = (30, 72, 172)
RICE = (238, 188, 84)
RICE_D = (210, 148, 56)
RICE_L = (252, 222, 140)
CARROT = (244, 126, 32)
CARROT_D = (204, 86, 20)
MEAT = (124, 64, 38)
MEAT_L = (168, 98, 62)
TABLE_TOP, TABLE_FRONT, TABLE_BOTTOM = 1110, 1200, 1350
PLATE_Y = 1152               # rim centre of a lagan standing on the table


# ---------------------------------------------------------------- easing
def clamp01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def lerp(a, b, t): return a + (b - a) * t
def ease_out_cubic(x): x = clamp01(x); return 1 - (1 - x) ** 3
def ease_in_cubic(x): x = clamp01(x); return x ** 3
def ease_in_quad(x): x = clamp01(x); return x * x
def ease_in_out(x): x = clamp01(x); return 3 * x * x - 2 * x * x * x
def ease_in_out_sine(x): x = clamp01(x); return -(math.cos(math.pi * x) - 1) / 2
def ease_out_back(x, s=1.70158):
    x = clamp01(x); x -= 1; return x * x * ((s + 1) * x + s) + 1
def damped(t, freq=5.0, decay=7.0):
    if t < 0: return 0.0
    return math.exp(-decay * t) * math.cos(2 * math.pi * freq * t)
def dsin(t, freq=5.0, decay=7.0):
    if t < 0: return 0.0
    return math.exp(-decay * t) * math.sin(2 * math.pi * freq * t)


# ---------------------------------------------------------------- supersampled canvas
class SS:
    def __init__(self, w, h, ss=3, bg=(0, 0, 0, 0)):
        self.w, self.h, self.ss = int(math.ceil(w)), int(math.ceil(h)), ss
        self.im = Image.new("RGBA", (self.w * ss, self.h * ss), bg)
        self.d = ImageDraw.Draw(self.im)
    def _b(self, box): return [v * self.ss for v in box]
    def _p(self, pts): return [(x * self.ss, y * self.ss) for x, y in pts]
    def _w(self, w): return max(1, int(round(w * self.ss))) if w else 0
    def ellipse(self, box, fill=None, outline=OL, width=6):
        self.d.ellipse(self._b(box), fill=fill, outline=outline if width else None, width=self._w(width))
    def circle(self, cx, cy, r, **kw): self.ellipse((cx - r, cy - r, cx + r, cy + r), **kw)
    def rect(self, box, fill=None, outline=OL, width=6, r=0):
        if r > 0:
            self.d.rounded_rectangle(self._b(box), radius=r * self.ss, fill=fill, outline=outline if width else None, width=self._w(width))
        else:
            self.d.rectangle(self._b(box), fill=fill, outline=outline if width else None, width=self._w(width))
    def poly(self, pts, fill=None, outline=OL, width=6):
        self.d.polygon(self._p(pts), fill=fill, outline=outline if width else None, width=self._w(width))
    def line(self, pts, fill=OL, width=6, round_caps=True):
        p = self._p(pts)
        self.d.line(p, fill=fill, width=self._w(width), joint="curve")
        if round_caps:
            r = self._w(width) / 2
            for (x, y) in (p[0], p[-1]):
                self.d.ellipse((x - r, y - r, x + r, y + r), fill=fill)
    def arc(self, box, a0, a1, fill=OL, width=6):
        self.d.arc(self._b(box), a0, a1, fill=fill, width=self._w(width))
    def paste(self, img, x, y):
        im = img.resize((img.width * self.ss, img.height * self.ss), Image.LANCZOS)
        self.im.alpha_composite(im, (int(x * self.ss), int(y * self.ss)))
    def text(self, xy, s, size, fill, anchor="mm", font=None, stroke=0, stroke_fill=OL):
        f = get_font(font or FONT_MAIN, int(size * self.ss))
        w = text_width(s, f)
        asc, desc = f.getmetrics()
        x = xy[0] * self.ss - (w / 2 if anchor[0] == "m" else 0)
        y = xy[1] * self.ss + ((asc - desc) / 2 * 0.86 if anchor[1] == "m" else 0)
        draw_runs(self.d, x, y, s, f, fill, self._w(stroke) if stroke else 0, stroke_fill)
    def result(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


def ell_pts(cx, cy, rx, ry, a0=0, a1=360, n=72):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / (n - 1))),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / (n - 1)))) for i in range(n)]


@functools.lru_cache(maxsize=128)
def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.truetype(FONT_FALLBACK, size)


# ---------------------------------------------------------------- image ops
def shade(img, factor):
    a = np.asarray(img).astype(np.float32)
    a[..., :3] *= factor
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), img.mode)


def with_alpha(img, alpha):
    if alpha >= 0.999: return img
    im = img.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    return im


def paste(canvas, img, x, y):
    x, y = int(round(x)), int(round(y))
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + img.width, canvas.width), min(y + img.height, canvas.height)
    if x1 <= x0 or y1 <= y0: return
    if canvas.mode == "RGBA":
        canvas.alpha_composite(img.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))
    else:
        c = img.crop((x0 - x, y0 - y, x1 - x, y1 - y))
        canvas.paste(c, (x0, y0), c)


def place(canvas, img, cx, cy, scale=1.0, sx=1.0, sy=1.0, rot=0.0, alpha=1.0, world=True):
    """paste img centred at (cx, cy); world=True adds the canvas margin"""
    w, h = img.size
    nw, nh = max(1, int(round(w * scale * sx))), max(1, int(round(h * scale * sy)))
    t = img if (nw, nh) == (w, h) else img.resize((nw, nh), Image.LANCZOS if scale * sx < 1 else Image.BICUBIC)
    if abs(rot) > 0.05: t = t.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 0.999: t = with_alpha(t, alpha)
    o = M if world else 0
    paste(canvas, t, cx + o - t.width / 2, cy + o - t.height / 2)


def place_anchor(canvas, img, ax, ay, px, py, scale=1.0, sx=1.0, sy=1.0, rot=0.0, alpha=1.0, world=True):
    """paste img so that its pixel (ax, ay) lands on world (px, py); scale/rotate about that anchor"""
    w, h = img.size
    nw, nh = max(1, int(round(w * scale * sx))), max(1, int(round(h * scale * sy)))
    t = img if (nw, nh) == (w, h) else img.resize((nw, nh), Image.LANCZOS if scale * sx < 1 else Image.BICUBIC)
    ax2, ay2 = ax * nw / w, ay * nh / h
    if abs(rot) > 0.05:
        big = Image.new("RGBA", (int(2 * max(ax2, nw - ax2)) + 4, int(2 * max(ay2, nh - ay2)) + 4), (0, 0, 0, 0))
        ox, oy = big.width / 2 - ax2, big.height / 2 - ay2
        big.paste(t, (int(round(ox)), int(round(oy))))
        t = big.rotate(rot, resample=Image.BICUBIC, expand=True)
        ax2, ay2 = t.width / 2, t.height / 2
    if alpha < 0.999: t = with_alpha(t, alpha)
    o = M if world else 0
    paste(canvas, t, px + o - ax2, py + o - ay2)


def grade(img, sat=1.0, mul=(1, 1, 1), add=(0, 0, 0)):
    a = np.asarray(img).astype(np.float32)
    rgb = a[..., :3]
    g = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    rgb = g[..., None] + (rgb - g[..., None]) * sat
    rgb = rgb * np.array(mul, np.float32) + np.array(add, np.float32)
    a[..., :3] = rgb
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), img.mode)


def soft_ellipse(w, h, color, alpha, blur):
    im = Image.new("RGBA", (int(w + blur * 4), int(h + blur * 4)), color + (0,))
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).ellipse((blur * 2, blur * 2, blur * 2 + w, blur * 2 + h), fill=int(255 * alpha))
    im.putalpha(m.filter(ImageFilter.GaussianBlur(blur)))
    return im


# ---------------------------------------------------------------- text
APOS_CH = "ʻʼ"


def layout(text, f):
    """split text into drawable runs; the Uzbek ʻ / ʼ glyphs are drawn with tightened side bearings.
    returns ([(run, x)], width)"""
    em = f.size
    runs = []; x = 0.0; cur = ""
    for ch in text:
        if ch in APOS_CH:
            if cur: runs.append((cur, x)); x += f.getlength(cur); cur = ""
            runs.append((ch, x - 0.11 * em)); x += 0.25 * em
        else:
            cur += ch
    if cur: runs.append((cur, x)); x += f.getlength(cur)
    return runs, x


def draw_runs(d, x, y, text, f, fill, stroke=0, stroke_fill=OL, anchor="ls"):
    runs, w = layout(text, f)
    for r, rx in runs:
        d.text((x + rx, y), r, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)
    return w


def text_width(text, f): return layout(text, f)[1]

def text_img(text, size, fill=WHITE, stroke=10, stroke_fill=(24, 16, 12), font=None, shadow=0.45,
             shadow_off=(0, 7), shadow_blur=7, gold_words=(), gold=(255, 196, 40)):
    """single line; words listed in gold_words get the gold fill"""
    f = get_font(font or FONT_MAIN, size)
    words = text.split(" ")
    space = f.getlength(" ")
    asc, desc = f.getmetrics()
    pad = stroke + 6
    widths = [text_width(w, f) for w in words]
    Wt = int(sum(widths) + space * (len(words) - 1) + 2 * pad + 4)
    Ht = int(asc + desc + 2 * pad)
    im = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = pad
    for w, wd in zip(words, widths):
        col = gold if w in gold_words else fill
        draw_runs(d, x, pad + asc, w, f, col, stroke, stroke_fill)
        x += wd + space
    if shadow:
        sh = Image.new("RGBA", (im.width + 40, im.height + 40), (0, 0, 0, 0))
        blk = Image.new("RGBA", im.size, (0, 0, 0, 255)); blk.putalpha(im.getchannel("A").point(lambda v: int(v * shadow)))
        sh.alpha_composite(blk, (20 + shadow_off[0], 20 + shadow_off[1]))
        sh = sh.filter(ImageFilter.GaussianBlur(shadow_blur))
        sh.alpha_composite(im, (20, 20))
        im = sh
    return im


def plain_text(text, size, fill, font=None):
    f = get_font(font or FONT_MAIN, size)
    asc, desc = f.getmetrics()
    w = int(text_width(text, f)) + 8
    im = Image.new("RGBA", (w, asc + desc + 8), (0, 0, 0, 0))
    draw_runs(ImageDraw.Draw(im), 4, 4 + asc, text, f, fill)
    return im.crop(im.getbbox() or (0, 0, 1, 1))


# ---------------------------------------------------------------- hero sprites
_SPR = {}
def sprite(name):
    if name not in _SPR:
        _SPR[name] = Image.open(os.path.join(SPR_DIR, name + ".png")).convert("RGBA")
    return _SPR[name]


def draw_hero(canvas, name, x, yb, h, ax=0.5, sx=1.0, sy=1.0, rot=0.0, alpha=1.0, mirror=False):
    """hero crop with its full-body height h; the point at horizontal fraction ax on the bottom edge sits at (x, yb);
    squash/stretch (sx, sy) and tilt (deg, ccw) pivot around that bottom point"""
    src = sprite(name)
    base = h / src.height
    tw, th = max(1, int(round(src.width * base * sx))), max(1, int(round(src.height * base * sy)))
    t = src.resize((tw, th), Image.LANCZOS)
    if mirror: t = t.transpose(Image.FLIP_LEFT_RIGHT); ax = 1 - ax
    if alpha < 0.999: t = with_alpha(t, alpha)
    px = ax * tw
    if abs(rot) > 0.05:
        pad = Image.new("RGBA", (int(2 * max(px, tw - px)) + 2, th * 2), (0, 0, 0, 0))
        ox = int(round(pad.width / 2 - px))
        pad.paste(t, (ox, 0))
        r = pad.rotate(rot, resample=Image.BICUBIC, expand=True, center=(pad.width / 2, th))
        paste(canvas, r, x + M - r.width / 2, yb + M - r.height / 2)
        return
    paste(canvas, t, x + M - px, yb + M - th)


def hero_point(name, fx, fy, x, yb, h, ax=0.5, sx=1.0, sy=1.0, rot=0.0):
    """world position of sprite fraction (fx, fy) for a hero drawn with draw_hero"""
    src = sprite(name)
    base = h / src.height
    tw, th = src.width * base * sx, src.height * base * sy
    dx, dy = (fx - ax) * tw, (fy - 1) * th
    a = math.radians(rot)
    return x + dx * math.cos(a) + dy * math.sin(a), yb - dx * math.sin(a) + dy * math.cos(a)


def idle(t, seed=0, amp=1.0):
    """breathing / bounce / tilt for a standing hero -> (sx, sy, rot, dy)"""
    ph = seed * 1.7
    br = math.sin(2 * math.pi * t / 1.9 + ph)
    sy = 1 + 0.014 * amp * br
    sx = 1 - 0.008 * amp * br
    rot = 1.4 * amp * math.sin(2 * math.pi * t / 2.7 + ph)
    dy = -6 * amp * abs(math.sin(2 * math.pi * t / 1.25 + ph))
    return sx, sy, rot, dy


# ---------------------------------------------------------------- camera
def camera(world, scale=1.0, ax=540, ay=960, tx=0.0, ty=0.0, rot=0.0, fill=TEAL_BOT):
    """world canvas (with margin) -> 1080x1920 frame. screen = R*s*(w - a) + a + t"""
    a = math.radians(rot)
    c, s_ = math.cos(a), math.sin(a)
    inv = 1.0 / scale
    # w = a + inv * R(-rot) (p - a - t)
    # R(-rot) = [[c, s], [-s, c]] (screen y down, rot ccw positive on screen)
    A = inv * c; B = inv * s_; D = -inv * s_; E = inv * c
    C0 = ax - A * (ax + tx) - B * (ay + ty) + M
    F0 = ay - D * (ax + tx) - E * (ay + ty) + M
    return world.transform((W, H), Image.AFFINE, (A, B, C0, D, E, F0), resample=Image.BICUBIC, fillcolor=fill)


def new_world(bg):
    return bg.copy()
