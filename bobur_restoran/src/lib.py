# Shared helpers: easing, supersampled drawing, sprites, text with emoji, props.
import math, os, json, functools, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(os.path.dirname(HERE), "fonts")
FONT_MAIN = os.path.join(FONT_DIR, "Nunito_900Black.ttf")
FONT_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

W, H, FPS = 1080, 1920, 30
OL = (42, 26, 18)
WHITE = (255, 255, 255)
GREEN = (46, 173, 91)
APPLE = (229, 56, 59)
NAVY = (30, 36, 51)
RING = (255, 244, 214)
YELLOW = (255, 214, 10)
SKIN = (231, 151, 109)
SKIN_D = (205, 120, 82)
GOLD = (222, 170, 60)
# palette from the brief
R_GOLD = (233, 180, 76)      # restaurant gold #E9B44C
CURTAIN = (155, 29, 32)      # #9B1D20
CLOTH = (255, 244, 224)      # #FFF4E0
WOOD = (139, 90, 43)         # #8B5A2B
SPOT = (255, 241, 184)       # #FFF1B8
TILE = (244, 247, 248)       # #F4F7F8
STEEL = (201, 209, 214)      # #C9D1D6
RICE = (242, 193, 78)        # #F2C14E
CARROT = (242, 140, 40)      # #F28C28
MEAT = (122, 62, 43)         # #7A3E2B
DREAM = (205, 180, 246)      # #CDB4F6
SOLD = (214, 40, 40)         # #D62828
BLUSH = (242, 160, 160)      # #F2A0A0
BURGUNDY = (122, 31, 43)     # #7A1F2B
NAVY_V = (35, 48, 90)        # #23305A

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
    def chord(self, box, a0, a1, fill=None, outline=None, width=0):
        self.d.chord(self._b(box), a0, a1, fill=fill, outline=outline, width=self._w(width) if width else 0)
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

# ---------------------------------------------------------------- sprites (sheet poses with sticker outline baked in)
SPR_ST = os.path.join(HERE, "sprites_st")
_SPR = {}
META = json.load(open(os.path.join(SPR_ST, "meta.json"))) if os.path.exists(os.path.join(SPR_ST, "meta.json")) else {}
def sprite(name):
    if name not in _SPR:
        _SPR[name] = Image.open(os.path.join(SPR_ST, name + ".png")).convert("RGBA")
    return _SPR[name]
def spr_name(who, pose): return f"{who}_{pose:02d}"
def content_h(name): return META[name]["h"]          # height of the sprite content (4x px), without sticker pad

STICKER_PX = 8.0      # white outline width in the final frame, for a 1000 px tall character
STD_H = 1000.0
def sticker(img, r, shadow_off=4.0, shadow_blur=6.0, shadow_alpha=0.25):
    """white sticker outline (round dilation) + soft drop shadow under an RGBA image; pads by r+blur"""
    import cv2
    pad = int(math.ceil(r + shadow_blur * 2 + shadow_off + 2))
    w, h = img.size
    a = np.zeros((h + 2 * pad, w + 2 * pad), np.uint8)
    a[pad:pad + h, pad:pad + w] = np.asarray(img.getchannel("A"))
    rr = max(1, int(round(r)))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rr + 1, 2 * rr + 1))
    d = cv2.dilate((a > 110).astype(np.uint8) * 255, k)
    d = cv2.GaussianBlur(d, (0, 0), 0.7)
    sh = np.roll(d, int(round(shadow_off)), axis=0).astype(np.float32)
    sh = cv2.GaussianBlur(sh, (0, 0), shadow_blur / 2.0) * shadow_alpha
    out = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32)
    # shadow (black) then white outline then the image
    out[..., 3] = sh
    wa = d.astype(np.float32)
    out[..., :3] = out[..., :3] * (1 - wa[..., None] / 255) + 255 * (wa[..., None] / 255)
    out[..., 3] = wa + out[..., 3] * (1 - wa / 255)
    src = np.zeros_like(out); src[pad:pad + h, pad:pad + w] = np.asarray(img).astype(np.float32)
    sa = src[..., 3:4] / 255
    out_a = out[..., 3:4] / 255
    na = sa + out_a * (1 - sa)
    rgb = (src[..., :3] * sa + out[..., :3] * out_a * (1 - sa)) / np.maximum(na, 1e-6)
    res = np.concatenate([rgb, na * 255], -1)
    return Image.fromarray(np.clip(res, 0, 255).astype(np.uint8), "RGBA"), pad

def draw_char(canvas, name, x, y_bottom, h, ox=0, oy=0, sx=1.0, sy=1.0, rot=0.0, mirror=False,
              alpha=1.0, darken=1.0):
    """sheet sprite, bottom-centre anchored. h = displayed height of the character content (no pad)."""
    src = sprite(name); m = META[name]
    s = h / m["h"]
    assert h * sy <= m["cell_h"] * 5.0 + 1, (name, h, m["cell_h"] * 5)
    assert 0.94 <= sx <= 1.06 and 0.94 <= sy <= 1.06 and abs(rot) <= 6.0, (name, sx, sy, rot)
    tw, th = src.width * s * sx, src.height * s * sy
    t = src.resize((max(1, int(round(tw))), max(1, int(round(th)))), Image.LANCZOS if s * sx < 1 else Image.BICUBIC)
    if mirror: t = t.transpose(Image.FLIP_LEFT_RIGHT)
    if darken < 0.999: t = shade(t, darken)
    if alpha < 0.999: t = with_alpha(t, alpha)
    pad = m["pad"]
    bx = x - ox - t.width / 2
    by = y_bottom - oy - (m["h"] + pad) * s * sy        # content bottom sits at y_bottom
    if abs(rot) > 0.05:
        piv = (t.width / 2, (m["h"] + pad) * s * sy)
        big = Image.new("RGBA", (t.width * 2, t.height * 2), (0, 0, 0, 0))
        big.paste(t, (int(t.width - piv[0]), int(t.height - piv[1])))
        r = big.rotate(rot, resample=Image.BICUBIC, center=(t.width, t.height))
        paste(canvas, r, x - ox - t.width, y_bottom - oy - t.height)
        return
    paste(canvas, t, bx, by)

def sprite_point(name, fx, fy, x, y_bottom, h, mirror=False, sx=1.0, sy=1.0):
    """world position of fractional point (fx, fy) of the sprite CONTENT drawn with draw_char"""
    m = META[name]; s = h / m["h"]
    cw, ch = m["w"] * s * sx, m["h"] * s * sy
    if mirror: fx = 1 - fx
    return x - cw / 2 + fx * cw, y_bottom - ch + fy * ch

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

