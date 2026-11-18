# Shared helpers: easing, supersampled drawing, sprites, text with emoji, props.
import math, os, json, functools, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
SPR_DIR = os.path.join(HERE, "sprites")
FONT_DIR = os.path.join(os.path.dirname(HERE), "fonts")
FONT_MAIN = os.path.join(FONT_DIR, "Nunito_900Black.ttf")
FONT_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

W, H, FPS = 1080, 1920, 30
OL = (42, 26, 18)
WHITE = (255, 255, 255)
PH_WHITE = (247, 250, 248)
MINT = (207, 239, 227)
MINT_D = (178, 222, 205)
GREEN = (46, 173, 91)
APPLE = (229, 56, 59)
APRICOT = (244, 162, 97)
GRAPE = (123, 44, 191)
POMEG = (181, 23, 43)
NAVY = (30, 36, 51)
RING = (255, 244, 214)
YELLOW = (255, 214, 10)
SKIN = (231, 151, 109)
SKIN_D = (205, 120, 82)
CHAPAN = (30, 112, 84)
CHAPAN_D = (18, 82, 62)
TRIM_R = (170, 38, 32)
GOLD = (222, 170, 60)

# ---------------------------------------------------------------- easing
def clamp01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def lerp(a, b, t): return a + (b - a) * t
def ease_out_cubic(x): x = clamp01(x); return 1 - (1 - x) ** 3
def ease_in_cubic(x): x = clamp01(x); return x ** 3
def ease_in_out(x): x = clamp01(x); return 3 * x * x - 2 * x * x * x
def ease_in_out_sine(x): x = clamp01(x); return -(math.cos(math.pi * x) - 1) / 2
def ease_out_back(x, s=1.70158):
    x = clamp01(x); x -= 1; return x * x * ((s + 1) * x + s) + 1
def ease_out_elastic(x):
    x = clamp01(x)
    if x in (0, 1): return x
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi / 3)) + 1
def damped(t, freq=6.0, decay=6.0):
    """damped oscillation starting at 1 -> 0"""
    if t < 0: return 0.0
    return math.exp(-decay * t) * math.cos(2 * math.pi * freq * t)

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
    def pieslice(self, box, a0, a1, fill=None, outline=OL, width=6):
        self.d.pieslice(self._b(box), a0, a1, fill=fill, outline=outline if width else None, width=self._w(width))
    def paste(self, img, x, y):
        im = img.resize((img.width * self.ss, img.height * self.ss), Image.LANCZOS)
        self.im.alpha_composite(im, (int(x * self.ss), int(y * self.ss)))
    def text(self, xy, s, size, fill, anchor="mm", font=None, stroke=0, stroke_fill=OL):
        f = get_font(font or FONT_MAIN, int(size * self.ss))
        self.d.text((xy[0] * self.ss, xy[1] * self.ss), s, font=f, fill=fill, anchor=anchor,
                    stroke_width=self._w(stroke) if stroke else 0, stroke_fill=stroke_fill)
    def result(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)

def blob_pts(cx, cy, rx, ry, n=48, wob=0.0, seed=0, phase=0.0):
    rnd = random.Random(seed)
    ks = [(rnd.uniform(0, 6.28), rnd.uniform(-1, 1)) for _ in range(3)]
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        r = 1 + wob * sum(k[1] * math.sin((j + 2) * a + k[0] + phase) for j, k in enumerate(ks)) / 3
        pts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)))
    return pts

@functools.lru_cache(maxsize=64)
def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.truetype(FONT_FALLBACK, size)

# ---------------------------------------------------------------- image ops
def shade(img, factor):
    """multiply rgb (keeps alpha)"""
    a = np.asarray(img).astype(np.float32)
    a[..., :3] *= factor
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), img.mode)

def with_alpha(img, alpha):
    if alpha >= 0.999: return img
    im = img.copy()
    a = im.getchannel("A").point(lambda v: int(v * alpha))
    im.putalpha(a)
    return im

def soft_shadow(w, h, alpha=0.28, blur=None):
    im = Image.new("RGBA", (int(w * 1.6), int(h * 3)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((int(w * 0.3), int(h), int(w * 1.3), int(h * 2)), fill=(20, 15, 10, int(255 * alpha)))
    return im.filter(ImageFilter.GaussianBlur(blur or h * 0.35))

def paste(canvas, img, x, y):
    """alpha paste RGBA img at integer top-left on RGB/RGBA canvas"""
    x, y = int(round(x)), int(round(y))
    if canvas.mode == "RGBA":
        # clip
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + img.width, canvas.width), min(y + img.height, canvas.height)
        if x1 <= x0 or y1 <= y0: return
        canvas.alpha_composite(img.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))
    else:
        canvas.paste(img, (x, y), img)

def transform_img(img, sx=1.0, sy=1.0, rot=0.0, mirror=False, resample=Image.BICUBIC):
    """scale by (sx,sy) absolute px factor, rotate deg CCW; returns image + offset of original center"""
    w, h = img.size
    nw, nh = max(1, int(round(w * sx))), max(1, int(round(h * sy)))
    out = img.resize((nw, nh), Image.LANCZOS if (sx < 1 and sy < 1) else resample)
    if mirror: out = out.transpose(Image.FLIP_LEFT_RIGHT)
    if abs(rot) > 0.05:
        out = out.rotate(rot, resample=Image.BICUBIC, expand=True)
    return out

def place(canvas, img, cx, cy, scale=1.0, sx=1.0, sy=1.0, rot=0.0, mirror=False, alpha=1.0, ox=0, oy=0):
    """paste img centered at world (cx,cy); canvas origin offset (ox,oy)"""
    t = transform_img(img, scale * sx, scale * sy, rot, mirror)
    if alpha < 1: t = with_alpha(t, alpha)
    paste(canvas, t, cx - ox - t.width / 2, cy - oy - t.height / 2)

# ---------------------------------------------------------------- sprites
_SPR = {}
META = json.load(open(os.path.join(SPR_DIR, "meta.json")))
def sprite(name):
    if name not in _SPR:
        _SPR[name] = Image.open(os.path.join(SPR_DIR, name + ".png")).convert("RGBA")
    return _SPR[name]

POSE_FILE = {"blogger": "blogger", "pharm": "pharm", "cust": "cust", "cust2": "cust2"}
def spr_name(who, pose): return f"{who}_{pose:02d}"

def char_pixels_per_orig(name):
    return 4.0

def draw_char(canvas, name, x, y_bottom, h, ox=0, oy=0, sx=1.0, sy=1.0, rot=0.0, mirror=False,
              alpha=1.0, darken=1.0, img=None, max_check=True):
    """draw sprite with bottom-centre anchor. h = displayed height of the full sprite image."""
    src = img if img is not None else sprite(name)
    base = h / src.height
    if max_check and name in META:
        cell_h = META[name]["cell"][1]
        assert h * sy <= cell_h * 5.0 + 1, (name, h, cell_h * 5)
    tw, th = src.width * base * sx, src.height * base * sy
    t = src.resize((max(1, int(round(tw))), max(1, int(round(th)))), Image.LANCZOS if base * sx < 1 else Image.BICUBIC)
    if mirror: t = t.transpose(Image.FLIP_LEFT_RIGHT)
    if darken < 0.999: t = shade(t, darken)
    if alpha < 0.999: t = with_alpha(t, alpha)
    if abs(rot) > 0.05:
        # rotate about bottom centre
        pad = Image.new("RGBA", (t.width, t.height * 2), (0, 0, 0, 0))
        pad.paste(t, (0, 0))
        r = pad.rotate(rot, resample=Image.BICUBIC, expand=True, center=(t.width / 2, t.height))
        # centre of rotation in new image
        cxn, cyn = r.width / 2, r.height / 2
        # pivot was at (w/2, h) in pad whose centre is (w/2, h) -> pivot == pad centre
        paste(canvas, r, x - ox - cxn, y_bottom - oy - cyn)
        return
    paste(canvas, t, x - ox - t.width / 2, y_bottom - oy - t.height)

def sprite_point(name, fx, fy, x, y_bottom, h, mirror=False, sx=1.0, sy=1.0):
    """world position of a fractional point (fx,fy) of the sprite drawn with draw_char"""
    src = sprite(name)
    base = h / src.height
    tw, th = src.width * base * sx, src.height * base * sy
    if mirror: fx = 1 - fx
    return x - tw / 2 + fx * tw, y_bottom - th + fy * th

# ---------------------------------------------------------------- hue shift (scene 15 only)
def hue_shift_green(img, target_hue_deg, sat_mul=1.0, val_mul=1.0):
    a = np.asarray(img).astype(np.float32) / 255.0
    rgb = a[..., :3]
    mx = rgb.max(-1); mn = rgb.min(-1); d = mx - mn + 1e-6
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    sat = d / (mx + 1e-6)
    mask = (hue > 95) & (hue < 200) & (sat > 0.22) & (mx > 0.12) & (a[..., 3] > 0)
    m = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))
    mk = np.asarray(m).astype(np.float32)[..., None] / 255.0
    nh = np.full_like(hue, target_hue_deg) + (hue - 155) * 0.5
    nh = nh % 360
    s2 = np.clip(sat * sat_mul, 0, 1); v2 = np.clip(mx * val_mul, 0, 1)
    c = v2 * s2; hp = nh / 60; xx = c * (1 - np.abs(hp % 2 - 1)); z = np.zeros_like(c)
    conds = [(hp < 1), (hp < 2), (hp < 3), (hp < 4), (hp < 5), (hp >= 5)]
    vals = [(c, xx, z), (xx, c, z), (z, c, xx), (z, xx, c), (xx, z, c), (c, z, xx)]
    out = np.zeros_like(rgb)
    done = np.zeros(hue.shape, bool)
    for cond, (rr, gg, bb) in zip(conds, vals):
        sel = cond & ~done
        out[..., 0] = np.where(sel, rr, out[..., 0]); out[..., 1] = np.where(sel, gg, out[..., 1]); out[..., 2] = np.where(sel, bb, out[..., 2])
        done |= sel
    out += (v2 - c)[..., None]
    res = rgb * (1 - mk) + out * mk
    o = np.concatenate([res, a[..., 3:4]], -1)
    return Image.fromarray(np.clip(o * 255, 0, 255).astype(np.uint8), "RGBA")

# ---------------------------------------------------------------- text with emoji
def is_emoji(ch):
    o = ord(ch)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF or o in (0x2B50, 0x2B55)

@functools.lru_cache(maxsize=64)
def emoji_img(ch, size):
    try:
        f = ImageFont.truetype(EMOJI_FONT, 109)
        im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
        bb = im.getbbox()
        if not bb: raise ValueError("empty emoji")
        im = im.crop(bb)
        s = size / max(im.size)
        return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    except Exception:
        # flat fallback icon
        c = SS(size, size, 3)
        c.circle(size / 2, size / 2, size * 0.45, fill=YELLOW, outline=OL, width=size * 0.06)
        return c.result()

def text_img(text, size, fill=WHITE, stroke=8, stroke_fill=(26, 26, 26), font=None, shadow=0.5,
             shadow_off=(0, 6), shadow_blur=6, emoji_scale=1.12, tracking=0):
    font = font or FONT_MAIN
    f = get_font(font, size)
    text = text.replace("️", "")
    runs = []
    for ch in text:
        e = is_emoji(ch)
        if runs and runs[-1][0] == e and not e: runs[-1][1] += ch
        else: runs.append([e, ch])
    asc, desc = f.getmetrics()
    pad = stroke + 4
    widths = []
    for e, s in runs:
        widths.append(int(size * emoji_scale) + int(size * 0.08) if e else int(math.ceil(f.getlength(s))) + tracking * len(s))
    Wt = sum(widths) + 2 * pad + 4
    Ht = asc + desc + 2 * pad + int(size * 0.2)
    im = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = pad; base = pad + asc
    for (e, s), w in zip(runs, widths):
        if e:
            em = emoji_img(s, int(size * emoji_scale))
            cy = base - size * 0.36
            im.alpha_composite(em, (int(x + size * 0.04), int(cy - em.height / 2)))
        else:
            if tracking or ("ʻ" in s or "ʼ" in s):
                xx = x
                for ch in s:
                    d.text((xx, base), ch, font=f, fill=fill, anchor="ls", stroke_width=stroke, stroke_fill=stroke_fill)
                    adv = f.getlength(ch) + tracking
                    if ch in "ʻʼ": adv *= 0.8; xx -= size * 0.015
                    xx += adv
            else:
                d.text((x, base), s, font=f, fill=fill, anchor="ls", stroke_width=stroke, stroke_fill=stroke_fill)
        x += w
    bb = im.getbbox()
    if bb: im = im.crop((bb[0], 0, bb[2], Ht))
    if shadow:
        sh = Image.new("RGBA", (im.width + 40, im.height + 40), (0, 0, 0, 0))
        al = im.getchannel("A")
        blk = Image.new("RGBA", im.size, (0, 0, 0, 255)); blk.putalpha(al.point(lambda v: int(v * shadow)))
        sh.alpha_composite(blk, (20 + shadow_off[0], 20 + shadow_off[1]))
        sh = sh.filter(ImageFilter.GaussianBlur(shadow_blur))
        sh.alpha_composite(im, (20, 20))
        im = sh
    return im

# ---------------------------------------------------------------- props
def banknote(w=220, h=112, seed=0):
    c = SS(w + 10, h + 10, 3)
    c.rect((5, 5, w + 5, h + 5), fill=(160, 214, 140), outline=OL, width=5, r=10)
    c.rect((16, 16, w - 6, h - 6), fill=None, outline=(88, 150, 86), width=3, r=6)
    c.ellipse((w / 2 - 30 + 5, h / 2 - 30 + 5, w / 2 + 30 + 5, h / 2 + 30 + 5), fill=(122, 186, 110), outline=(70, 130, 70), width=3)
    c.ellipse((w / 2 - 12 + 5, h / 2 - 12 + 5, w / 2 + 12 + 5, h / 2 + 12 + 5), fill=(196, 232, 170), outline=None, width=0)
    for (x, y) in ((24, 24), (w - 14, 24), (24, h - 14), (w - 14, h - 14)):
        c.circle(x, y, 7, fill=(110, 175, 100), outline=None, width=0)
    return c.result()

def banknote_fan(n=5, spread=44):
    bn = banknote(240, 120)
    S_ = 520
    canvas = Image.new("RGBA", (S_, S_), (0, 0, 0, 0))
    for i in range(n):
        a = -spread / 2 + spread * i / (n - 1)
        r = bn.rotate(-a, resample=Image.BICUBIC, expand=True, center=(30, bn.height / 2))
        # pivot near left-centre of note -> place pivot at canvas (160, 300)
        big = Image.new("RGBA", (S_, S_), (0, 0, 0, 0))
        tmp = Image.new("RGBA", (bn.width * 3, bn.height * 3), (0, 0, 0, 0))
        tmp.paste(bn, (bn.width, bn.height))
        rr = tmp.rotate(a, resample=Image.BICUBIC, center=(bn.width + 30, bn.height * 1.5))
        big.alpha_composite(rr, (int(160 - bn.width - 30), int(300 - bn.height * 1.5)))
        canvas.alpha_composite(big)
    bb = canvas.getbbox()
    return canvas.crop(bb)

def banknote_stack(w=300, layers=9):
    lh = 9
    hh = 120 + layers * lh
    c = SS(w + 20, hh + 20, 3)
    for i in range(layers):
        y = 10 + 60 + (layers - 1 - i) * lh
        col = (150, 205, 130) if i % 2 else (170, 222, 150)
        c.rect((10, y, w + 10, y + 70), fill=col, outline=OL, width=4, r=8)
    top = 10
    c.rect((10, top, w + 10, top + 76), fill=(170, 222, 150), outline=OL, width=5, r=8)
    c.rect((22, top + 10, w - 2, top + 66), fill=None, outline=(88, 150, 86), width=3, r=5)
    c.ellipse((w / 2 - 16, top + 18, w / 2 + 36, top + 58), fill=(122, 186, 110), outline=(70, 130, 70), width=3)
    # paper band
    bx = w / 2 - 30
    c.rect((bx, top - 4, bx + 64, hh + 6), fill=(255, 236, 170), outline=OL, width=4, r=4)
    c.line([(bx + 12, top + 30), (bx + 52, top + 30)], fill=(220, 170, 70), width=4)
    return c.result()

def apple(r=60, leaf=True):
    s = r * 2.6
    c = SS(s, s, 3)
    cx, cy = s / 2, s / 2 + r * 0.15
    body = []
    for i in range(72):
        a = 2 * math.pi * i / 72
        rr = r * (1 - 0.13 * max(0, math.cos(a + math.pi / 2)) ** 6) * (1 + 0.04 * math.sin(2 * a))
        x = cx + rr * 1.06 * math.cos(a); y = cy + rr * math.sin(a)
        if math.sin(a) < -0.85: y += r * 0.18 * (abs(math.sin(a)) - 0.85) / 0.15
        body.append((x, y))
    c.poly(body, fill=APPLE, outline=OL, width=r * 0.1)
    c.pieslice((cx - r * 0.95, cy - r * 0.9, cx + r * 0.95, cy + r * 0.93), 10, 110, fill=(196, 36, 46), outline=None, width=0)
    c.poly(body, fill=None, outline=OL, width=r * 0.1)
    c.ellipse((cx - r * 0.62, cy - r * 0.62, cx - r * 0.25, cy - r * 0.18), fill=(255, 255, 255, 230), outline=None, width=0)
    c.line([(cx, cy - r * 0.75), (cx + r * 0.1, cy - r * 1.15)], fill=(110, 70, 40), width=r * 0.12)
    if leaf:
        lx, ly = cx + r * 0.12, cy - r * 1.0
        pts = [(lx, ly), (lx + r * 0.3, ly - r * 0.35), (lx + r * 0.75, ly - r * 0.3), (lx + r * 0.45, ly + r * 0.05)]
        c.poly(pts, fill=(63, 174, 74), outline=OL, width=r * 0.07)
    return c.result()

def pomegranate(r=58):
    s = r * 2.6
    c = SS(s, s, 3)
    cx, cy = s / 2, s / 2 + r * 0.12
    crown = [(cx - r * 0.3, cy - r * 0.8), (cx - r * 0.38, cy - r * 1.18), (cx - r * 0.15, cy - r * 0.98), (cx, cy - r * 1.25),
             (cx + r * 0.15, cy - r * 0.98), (cx + r * 0.38, cy - r * 1.18), (cx + r * 0.3, cy - r * 0.8)]
    c.poly(crown, fill=(150, 18, 36), outline=OL, width=r * 0.09)
    c.ellipse((cx - r, cy - r * 0.95, cx + r, cy + r * 0.95), fill=POMEG, outline=OL, width=r * 0.1)
    c.pieslice((cx - r * 0.9, cy - r * 0.85, cx + r * 0.9, cy + r * 0.88), 15, 105, fill=(140, 12, 32), outline=None, width=0)
    c.ellipse((cx - r, cy - r * 0.95, cx + r, cy + r * 0.95), fill=None, outline=OL, width=r * 0.1)
    c.ellipse((cx - r * 0.6, cy - r * 0.6, cx - r * 0.25, cy - r * 0.2), fill=(255, 210, 215, 230), outline=None, width=0)
    return c.result()

def apricot(r=50):
    s = r * 2.6
    c = SS(s, s, 3)
    cx, cy = s / 2, s / 2 + r * 0.1
    c.ellipse((cx - r * 1.02, cy - r * 0.95, cx + r * 1.02, cy + r * 0.95), fill=APRICOT, outline=OL, width=r * 0.11)
    c.pieslice((cx - r * 0.92, cy - r * 0.85, cx + r * 0.92, cy + r * 0.85), 0, 100, fill=(232, 128, 70), outline=None, width=0)
    c.ellipse((cx + r * 0.05, cy - r * 0.45, cx + r * 0.6, cy + r * 0.15), fill=(240, 120, 90, 120), outline=None, width=0)
    c.ellipse((cx - r * 1.02, cy - r * 0.95, cx + r * 1.02, cy + r * 0.95), fill=None, outline=OL, width=r * 0.11)
    c.arc((cx - r * 0.5, cy - r * 0.9, cx + r * 0.3, cy + r * 0.8), 200, 330, fill=OL, width=r * 0.07)
    c.ellipse((cx - r * 0.65, cy - r * 0.6, cx - r * 0.3, cy - r * 0.25), fill=(255, 255, 255, 220), outline=None, width=0)
    lx, ly = cx + r * 0.05, cy - r * 0.9
    c.poly([(lx, ly), (lx + r * 0.35, ly - r * 0.4), (lx + r * 0.7, ly - r * 0.3), (lx + r * 0.4, ly + r * 0.05)], fill=(63, 174, 74), outline=OL, width=r * 0.07)
    return c.result()

def grapes(r=60):
    s = r * 2.8
    c = SS(s, s, 3)
    cx, cy = s / 2, s / 2 + r * 0.1
    rr = r * 0.33
    rows = [(-0.9, 3), (-0.35, 4), (0.2, 3), (0.72, 2), (1.15, 1)]
    berries = []
    for ry, n in rows:
        for i in range(n):
            bx = cx + (i - (n - 1) / 2) * rr * 1.75
            by = cy + ry * r * 0.75
            berries.append((bx, by))
    c.line([(cx, cy - r * 1.0), (cx + r * 0.15, cy - r * 1.35)], fill=(110, 70, 40), width=r * 0.1)
    c.poly([(cx + r * 0.1, cy - r * 1.15), (cx + r * 0.6, cy - r * 1.45), (cx + r * 0.95, cy - r * 1.1), (cx + r * 0.4, cy - r * 0.95)], fill=(63, 174, 74), outline=OL, width=r * 0.07)
    for bx, by in berries:
        c.circle(bx, by, rr, fill=GRAPE, outline=OL, width=r * 0.07)
        c.circle(bx - rr * 0.35, by - rr * 0.35, rr * 0.28, fill=(200, 160, 240), outline=None, width=0)
    return c.result()

FRUITS = None
def fruit_imgs():
    global FRUITS
    if FRUITS is None:
        FRUITS = {"apple": apple(60), "pomeg": pomegranate(58), "grapes": grapes(60), "apricot": apricot(52)}
    return FRUITS

BOX_COLORS = [(66, 135, 245), (240, 90, 80), (255, 196, 61), (130, 90, 210), (46, 173, 140), (255, 140, 66), (236, 100, 160), (90, 190, 230)]
def med_box(w, h, color, style=0, side=True):
    sd = w * 0.18 if side else 0
    c = SS(w + sd + 12, h + sd * 0.6 + 12, 3)
    ox, oy = 6, 6 + sd * 0.6
    dark = tuple(int(v * 0.75) for v in color)
    if side:
        c.poly([(ox + w, oy), (ox + w + sd, oy - sd * 0.6), (ox + w + sd, oy + h - sd * 0.6), (ox + w, oy + h)], fill=dark, outline=OL, width=4)
        c.poly([(ox, oy), (ox + sd, oy - sd * 0.6), (ox + w + sd, oy - sd * 0.6), (ox + w, oy)], fill=tuple(min(255, int(v * 1.15)) for v in color), outline=OL, width=4)
    c.rect((ox, oy, ox + w, oy + h), fill=color, outline=OL, width=4.5, r=3)
    lw = w * 0.74
    lx, ly = ox + (w - lw) / 2, oy + h * 0.28
    lh = h * 0.42
    c.rect((lx, ly, lx + lw, ly + lh), fill=(255, 255, 255), outline=None, width=0, r=3)
    if style % 3 == 0:
        cs = min(lw, lh) * 0.32; mx, my = lx + lw / 2, ly + lh / 2
        c.rect((mx - cs * 0.35, my - cs, mx + cs * 0.35, my + cs), fill=GREEN, outline=None, width=0)
        c.rect((mx - cs, my - cs * 0.35, mx + cs, my + cs * 0.35), fill=GREEN, outline=None, width=0)
    elif style % 3 == 1:
        mx, my = lx + lw / 2, ly + lh / 2; pw = lw * 0.5; ph = lh * 0.42
        c.rect((mx - pw / 2, my - ph / 2, mx + pw / 2, my + ph / 2), fill=color, outline=OL, width=3, r=ph / 2)
        c.line([(mx, my - ph / 2), (mx, my + ph / 2)], fill=OL, width=3, round_caps=False)
    else:
        for k in range(3):
            yy = ly + lh * (0.25 + 0.25 * k)
            c.line([(lx + lw * 0.15, yy), (lx + lw * (0.85 - 0.2 * (k == 2)), yy)], fill=dark, width=max(2, lh * 0.09))
    c.rect((ox + w * 0.1, oy + h * 0.08, ox + w * 0.9, oy + h * 0.16), fill=tuple(min(255, int(v * 1.25)) for v in color), outline=None, width=0)
    return c.result()

def bottle(w, h, color):
    c = SS(w + 12, h + 12, 3)
    ox, oy = 6, 6
    neck = w * 0.42
    c.rect((ox + (w - neck) / 2, oy, ox + (w + neck) / 2, oy + h * 0.18), fill=(250, 250, 250), outline=OL, width=4, r=3)
    c.rect((ox, oy + h * 0.16, ox + w, oy + h), fill=color, outline=OL, width=4.5, r=w * 0.22)
    c.rect((ox + w * 0.12, oy + h * 0.42, ox + w * 0.88, oy + h * 0.78), fill=(255, 255, 255), outline=None, width=0, r=3)
    c.rect((ox + w * 0.18, oy + h * 0.25, ox + w * 0.3, oy + h * 0.38), fill=(255, 255, 255, 160), outline=None, width=0, r=3)
    return c.result()

def golden_box(w=170, h=210):
    sd = w * 0.2
    c = SS(w + sd + 14, h + sd * 0.6 + 14, 3)
    ox, oy = 7, 7 + sd * 0.6
    c.poly([(ox + w, oy), (ox + w + sd, oy - sd * 0.6), (ox + w + sd, oy + h - sd * 0.6), (ox + w, oy + h)], fill=(196, 140, 30), outline=OL, width=5)
    c.poly([(ox, oy), (ox + sd, oy - sd * 0.6), (ox + w + sd, oy - sd * 0.6), (ox + w, oy)], fill=(255, 226, 110), outline=OL, width=5)
    c.rect((ox, oy, ox + w, oy + h), fill=(242, 190, 50), outline=OL, width=6, r=4)
    c.poly([(ox + w * 0.1, oy + h), (ox + w * 0.45, oy), (ox + w * 0.62, oy), (ox + w * 0.27, oy + h)], fill=(255, 236, 150), outline=None, width=0)
    c.rect((ox, oy, ox + w, oy + h), fill=None, outline=OL, width=6, r=4)
    m = w * 0.5
    c.circle(ox + m, oy + h * 0.5, w * 0.27, fill=(255, 255, 255), outline=OL, width=4)
    cs = w * 0.15
    c.rect((ox + m - cs * 0.35, oy + h * 0.5 - cs, ox + m + cs * 0.35, oy + h * 0.5 + cs), fill=GREEN, outline=None, width=0)
    c.rect((ox + m - cs, oy + h * 0.5 - cs * 0.35, ox + m + cs, oy + h * 0.5 + cs * 0.35), fill=GREEN, outline=None, width=0)
    return c.result()

def sparkle(size=60, col=YELLOW):
    c = SS(size, size, 3)
    m = size / 2
    pts = []
    for i in range(8):
        a = math.pi / 4 * i - math.pi / 2
        r = m * 0.95 if i % 2 == 0 else m * 0.28
        pts.append((m + r * math.cos(a), m + r * math.sin(a)))
    c.poly(pts, fill=col, outline=OL, width=size * 0.06)
    c.circle(m, m, m * 0.16, fill=(255, 255, 255), outline=None, width=0)
    return c.result()

def smoke_puff(progress, size=820, seed=3):
    """progress 0..1 : grow 0-0.2, hold 0.2-0.55, dissipate 0.55-1"""
    rnd = random.Random(seed)
    c = SS(size * 1.7, size * 1.7, 2)
    m = size * 0.85
    puffs = [(rnd.uniform(-0.28, 0.28), rnd.uniform(-0.3, 0.3), rnd.uniform(0.16, 0.26)) for _ in range(14)]
    puffs.append((0, 0, 0.3))
    if progress < 0.2: g = ease_out_back(progress / 0.2, 2.0); fade = 1
    elif progress < 0.55: g = 1 + 0.06 * (progress - 0.2) / 0.35; fade = 1
    else:
        q = (progress - 0.55) / 0.45; g = 1.06 + 0.3 * q; fade = (1 - q) ** 2
    if fade <= 0.01: return None
    for k, (px, py, pr) in enumerate(puffs):
        rr = pr * size * g * (1 - 0.7 * (max(0, progress - 0.55) / 0.45) * (0.5 + 0.5 * (k % 3) / 2))
        if rr <= 2: continue
        x = m + px * size * g * (1 + 0.4 * max(0, progress - 0.55)); y = m + py * size * g * (1 + 0.4 * max(0, progress - 0.55))
        c.circle(x, y, rr, fill=(238, 240, 245), outline=OL, width=7)
    for k, (px, py, pr) in enumerate(puffs):
        rr = pr * size * g * (1 - 0.7 * (max(0, progress - 0.55) / 0.45) * (0.5 + 0.5 * (k % 3) / 2))
        if rr <= 2: continue
        x = m + px * size * g * (1 + 0.4 * max(0, progress - 0.55)); y = m + py * size * g * (1 + 0.4 * max(0, progress - 0.55))
        c.circle(x - rr * 0.1, y - rr * 0.12, rr * 0.86, fill=(255, 255, 255), outline=None, width=0)
    im = c.result()
    return with_alpha(im, fade)

def diploma_paper(w=420, h=300):
    c = SS(w, h, 3)
    c.rect((0, 6, w, h - 6), fill=(255, 243, 214), outline=OL, width=6, r=4)
    c.rect((18, 22, w - 18, h - 22), fill=None, outline=(214, 186, 120), width=4, r=3)
    cx = w / 2
    c.circle(cx, 86, 40, fill=(255, 255, 255), outline=GREEN, width=6)
    cs = 24
    c.rect((cx - cs * 0.35, 86 - cs, cx + cs * 0.35, 86 + cs), fill=GREEN, outline=None, width=0)
    c.rect((cx - cs, 86 - cs * 0.35, cx + cs, 86 + cs * 0.35), fill=GREEN, outline=None, width=0)
    for k, (a, b) in enumerate([(0.2, 0.8), (0.14, 0.86), (0.24, 0.76)]):
        y = 156 + k * 30
        c.line([(w * a, y), (w * b, y)], fill=(176, 168, 152), width=8)
    c.line([(w * 0.6, h - 52), (w * 0.84, h - 52)], fill=(150, 140, 130), width=5)
    c.circle(w * 0.24, h - 58, 22, fill=(220, 60, 60), outline=OL, width=4)
    return c.result()

def scroll_roll(h=300, r=22):
    c = SS(r * 2 + 8, h + 8, 3)
    c.rect((4, 4, 4 + r * 2, h + 4), fill=(236, 214, 165), outline=OL, width=6, r=r)
    c.line([(4 + r * 0.6, 20), (4 + r * 0.6, h - 12)], fill=(255, 245, 220), width=5)
    return c.result()

def check_stamp(size=200):
    c = SS(size, size, 3)
    m = size / 2
    c.circle(m, m, m * 0.92, fill=(255, 255, 255, 60), outline=(36, 150, 76), width=size * 0.07)
    c.circle(m, m, m * 0.74, fill=None, outline=(36, 150, 76), width=size * 0.025)
    c.line([(m - m * 0.42, m + m * 0.02), (m - m * 0.1, m + m * 0.35), (m + m * 0.48, m - m * 0.38)], fill=(36, 150, 76), width=size * 0.13)
    return c.result().rotate(-12, resample=Image.BICUBIC, expand=True)

def cash_register(w=230, h=190):
    c = SS(w + 12, h + 12, 3)
    ox, oy = 6, 6
    c.rect((ox + w * 0.18, oy, ox + w * 0.62, oy + h * 0.3), fill=(70, 80, 90), outline=OL, width=5, r=6)
    c.rect((ox + w * 0.23, oy + h * 0.06, ox + w * 0.57, oy + h * 0.22), fill=(120, 230, 160), outline=OL, width=3, r=3)
    c.poly([(ox + w * 0.05, oy + h * 0.32), (ox + w * 0.95, oy + h * 0.32), (ox + w, oy + h * 0.78), (ox, oy + h * 0.78)], fill=(170, 215, 200), outline=OL, width=5)
    for i in range(4):
        for j in range(2):
            x = ox + w * (0.18 + 0.18 * i); y = oy + h * (0.42 + 0.15 * j)
            c.rect((x, y, x + w * 0.12, y + h * 0.09), fill=(250, 250, 250), outline=OL, width=3, r=3)
    c.rect((ox, oy + h * 0.78, ox + w, oy + h), fill=(140, 190, 176), outline=OL, width=5, r=4)
    c.rect((ox + w * 0.42, oy + h * 0.86, ox + w * 0.58, oy + h * 0.92), fill=OL, outline=None, width=0, r=2)
    return c.result()

def cobweb(size=170):
    c = SS(size, size, 3)
    col = (235, 235, 235, 230)
    n = 6
    for i in range(n + 1):
        a = math.pi / 2 * i / n
        c.line([(0, 0), (size * math.cos(a), size * math.sin(a))], fill=col, width=2.2)
    for k in range(1, 5):
        r = size * k / 4.6
        pts = []
        for i in range(n + 1):
            a = math.pi / 2 * i / n
            rr = r * (0.92 if i % 2 else 1.0)
            pts.append((rr * math.cos(a), rr * math.sin(a)))
        c.line(pts, fill=col, width=2.0)
    return c.result()

def calendar_img(day, w=230, h=270, page_only=False):
    c = SS(w, h, 3)
    if not page_only:
        c.rect((0, 26, w, h), fill=(255, 255, 255), outline=OL, width=6, r=10)
    c.rect((6 if page_only else 0, 26, w - (6 if page_only else 0), h - (0 if not page_only else 0)), fill=(255, 255, 255), outline=OL, width=5, r=8)
    c.rect((0, 26, w, 92), fill=APPLE, outline=OL, width=6, r=8)
    for x in (w * 0.3, w * 0.7):
        c.rect((x - 7, 6, x + 7, 46), fill=(160, 160, 170), outline=OL, width=4, r=6)
    c.text((w / 2, 60), "NOYABR", 26, (255, 255, 255), font=FONT_MAIN)
    c.text((w / 2, 178), str(day), 110, (40, 40, 50), font=FONT_MAIN)
    return c.result()

def fruit_basket(w=200):
    h = w * 0.8
    c = SS(w, h, 3)
    fr = fruit_imgs()
    # handle
    c.arc((w * 0.15, -h * 0.25, w * 0.85, h * 0.75), 180, 360, fill=OL, width=w * 0.07)
    c.arc((w * 0.15, -h * 0.25, w * 0.85, h * 0.75), 180, 360, fill=(170, 110, 60), width=w * 0.04)
    # fruits peeking
    for name, fx, fs in (("grapes", 0.3, 0.45), ("apple", 0.62, 0.42), ("apricot", 0.45, 0.36)):
        im = fr[name]; s = (w * fs) / im.width
        im2 = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        c.paste(im2, w * fx - im2.width / 2, h * 0.5 - im2.height * 0.75)
    body = [(w * 0.04, h * 0.42), (w * 0.96, h * 0.42), (w * 0.84, h * 0.98), (w * 0.16, h * 0.98)]
    c.poly(body, fill=(196, 132, 70), outline=OL, width=w * 0.035)
    for k in range(1, 4):
        y = h * (0.42 + 0.14 * k)
        c.line([(w * (0.06 + 0.03 * k), y), (w * (0.94 - 0.03 * k), y)], fill=(150, 95, 45), width=w * 0.02)
    for k in range(1, 6):
        x = w * (0.04 + 0.92 * k / 6)
        c.line([(x, h * 0.44), (lerp(x, w / 2, 0.24), h * 0.96)], fill=(150, 95, 45), width=w * 0.018)
    c.rect((w * 0.02, h * 0.38, w * 0.98, h * 0.48), fill=(214, 150, 84), outline=OL, width=w * 0.03, r=h * 0.04)
    return c.result()

def comment_bubble(w=420, h=250):
    c = SS(w, h + 60, 3)
    c.rect((6, 6, w - 6, h), fill=(255, 255, 255), outline=OL, width=7, r=40)
    c.poly([(70, h - 8), (60, h + 50), (140, h - 8)], fill=(255, 255, 255), outline=None, width=0)
    c.line([(70, h - 4), (60, h + 50), (140, h - 2)], fill=OL, width=7)
    # @ icon
    c.circle(96, 104, 58, fill=(66, 135, 245), outline=OL, width=6)
    c.text((96, 100), "@", 78, (255, 255, 255), font=FONT_MAIN)
    for k, ww in enumerate((0.42, 0.32)):
        y = 78 + k * 52
        c.line([(176, y), (176 + w * ww, y)], fill=(190, 196, 205), width=20)
    # pencil
    px, py = w - 92, h - 70
    c.poly([(px - 60, py + 28), (px + 40, py - 72), (px + 66, py - 46), (px - 34, py + 54)], fill=YELLOW, outline=OL, width=5)
    c.poly([(px - 60, py + 28), (px - 34, py + 54), (px - 76, py + 70)], fill=(250, 214, 170), outline=OL, width=5)
    c.poly([(px + 40, py - 72), (px + 66, py - 46), (px + 78, py - 58), (px + 52, py - 84)], fill=(240, 120, 140), outline=OL, width=5)
    return c.result()

def mystery_card(w=440, h=580):
    c = SS(w, h, 3)
    c.rect((6, 6, w - 6, h - 6), fill=(255, 214, 10), outline=OL, width=8, r=40)
    c.rect((30, 30, w - 30, h - 30), fill=(255, 238, 150), outline=None, width=0, r=28)
    sil = (34, 30, 44)
    cx = w / 2
    c.ellipse((cx - 170, h * 0.58, cx + 170, h + 120), fill=sil, outline=None, width=0)
    c.circle(cx, h * 0.42, 118, fill=sil, outline=None, width=0)
    c.circle(cx - 118, h * 0.43, 26, fill=sil, outline=None, width=0)
    c.circle(cx + 118, h * 0.43, 26, fill=sil, outline=None, width=0)
    c.rect((30, h - 30 - 10, w - 30, h - 30), fill=None, outline=None, width=0)
    c.text((cx, h * 0.44), "?", 230, (255, 255, 255), font=FONT_MAIN, stroke=8, stroke_fill=OL)
    c.rect((6, 6, w - 6, h - 6), fill=None, outline=OL, width=8, r=40)
    im = c.result()
    # clip the silhouette to card rounded inner area
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((6, 6, w - 6, h - 6), radius=40, fill=255)
    im.putalpha(ImageChops.multiply(im.getchannel("A"), mask))
    return im

def notification_bubble(text_title, text_body, w=900):
    f_t = get_font(FONT_MAIN, 50); f_b = get_font(FONT_MAIN, 46)
    # wrap body
    words = text_body.split(); lines = []; cur = ""
    maxw = w - 210
    for wd in words:
        t = (cur + " " + wd).strip()
        if text_img(t, 46, fill=(40, 40, 50), stroke=0, shadow=0).width > maxw and cur:
            lines.append(cur); cur = wd
        else: cur = t
    lines.append(cur)
    h = 120 + 60 * len(lines) + 34
    c = SS(w, h + 20, 3)
    c.rect((6, 6, w - 6, h), fill=(255, 255, 255), outline=OL, width=7, r=44)
    c.rect((36, 36, 146, 146), fill=GREEN, outline=OL, width=5, r=28)
    c.rect((62, 64, 120, 108), fill=(255, 255, 255), outline=None, width=0, r=14)
    c.poly([(74, 104), (68, 124), (92, 106)], fill=(255, 255, 255), outline=None, width=0)
    im = c.result()
    tt = text_img(text_title, 50, fill=(200, 30, 40), stroke=0, shadow=0)
    im.alpha_composite(tt, (178, 34))
    y = 100
    for ln in lines:
        li = text_img(ln, 46, fill=(40, 40, 50), stroke=0, shadow=0)
        im.alpha_composite(li, (178, y)); y += 60
    # dot
    d = ImageDraw.Draw(im)
    d.text((w - 60, 46), "now", font=get_font(FONT_MAIN, 30), fill=(150, 150, 160), anchor="rm")
    return im

def sign_img(text="DORIXONA", w=600, h=170, icon="cross", on=1.0):
    c = SS(w, h, 3)
    c.rect((6, 6, w - 6, h - 6), fill=(255, 255, 255), outline=OL, width=7, r=24)
    c.rect((20, 20, w - 20, h - 20), fill=None, outline=GREEN, width=5, r=16)
    cx, cy = 92, h / 2
    if icon == "cross":
        c.circle(cx, cy, 52, fill=GREEN, outline=OL, width=5)
        cs = 32
        c.rect((cx - cs * 0.36, cy - cs, cx + cs * 0.36, cy + cs), fill=(255, 255, 255), outline=None, width=0)
        c.rect((cx - cs, cy - cs * 0.36, cx + cs, cy + cs * 0.36), fill=(255, 255, 255), outline=None, width=0)
        col = GREEN
    else:
        a = apple(40)
        c.paste(a, cx - a.width / 2, cy - a.height / 2)
        col = APPLE
    im = c.result()
    sz = 104
    t = text_img(text, sz, fill=col, stroke=0, shadow=0, tracking=2)
    avail = w - 215
    if t.width > avail:
        sz = int(sz * avail / t.width); t = text_img(text, sz, fill=col, stroke=0, shadow=0, tracking=2)
    im.alpha_composite(t, (int(158 + (w - 190 - t.width) / 2), int(h / 2 - t.height / 2 + 4)))
    return im

def customer_hand_fan():
    """foreground sleeve (green chapan, red trim) + hand holding a fan of banknotes, reaching up-right"""
    Wd, Hd = 640, 720
    fan = banknote_fan(5, 50)
    fan = fan.resize((int(fan.width * 1.3), int(fan.height * 1.3)), Image.LANCZOS)
    base = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0))
    base.alpha_composite(fan, (250, 10))
    # sleeve with clipped ikat stripes
    sl = [(-40, Hd + 40), (-40, Hd - 250), (250, 400), (400, 492), (190, Hd + 40)]
    c = SS(Wd, Hd, 2)
    c.poly(sl, fill=CHAPAN, outline=None, width=0)
    for k in range(9):
        x0 = -120 + k * 60
        c.line([(x0, Hd + 20), (x0 + 260, 470 + k * 10)], fill=(52, 140, 104), width=16)
        c.line([(x0 + 26, Hd + 20), (x0 + 270, 486 + k * 10)], fill=(214, 186, 92), width=4)
    sleeve = c.result()
    m = SS(Wd, Hd, 2); m.poly(sl, fill=(255, 255, 255, 255), outline=None, width=0)
    sleeve.putalpha(ImageChops.multiply(sleeve.getchannel("A"), m.result().getchannel("A")))
    base.alpha_composite(sleeve)
    c = SS(Wd, Hd, 2)
    c.poly(sl, fill=None, outline=OL, width=9)
    cuff = [(236, 378), (424, 476), (392, 546), (204, 446)]
    c.poly(cuff, fill=TRIM_R, outline=OL, width=8)
    c.line([(228, 402), (414, 500)], fill=GOLD, width=7)
    c.line([(216, 426), (402, 524)], fill=GOLD, width=4)
    # back of hand + curled fingers over the notes
    hx, hy = 400, 330
    c.ellipse((hx - 100, hy - 60, hx + 70, hy + 110), fill=SKIN, outline=OL, width=8)
    c.ellipse((hx - 135, hy - 95, hx - 35, hy - 5), fill=SKIN, outline=OL, width=8)   # thumb behind
    for k in range(4):
        fx = hx - 40 + k * 34; fy = hy - 60 + k * 26
        c.rect((fx - 6, fy - 30, fx + 74, fy + 26), fill=SKIN, outline=OL, width=7, r=28)
    c.ellipse((hx - 100, hy - 10, hx + 30, hy + 110), fill=SKIN, outline=None, width=0)
    c.arc((hx - 100, hy - 60, hx + 70, hy + 110), 100, 250, fill=OL, width=8)
    for k in range(3):
        fx = hx - 4 + k * 34; fy = hy - 40 + k * 26
        c.line([(fx + 34, fy + 2), (fx + 44, fy + 10)], fill=SKIN_D, width=4)
    base.alpha_composite(c.result())
    return base
