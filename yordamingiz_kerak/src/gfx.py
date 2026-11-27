# Drawing helpers: palette, easing, Uzbek apostrophes, supersampled vector icons, cards, pills.
import math, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
K = W / 756                      # source frame (756x1344) -> scene space (1080x1920)
BG = (0xED, 0xE3, 0xD3); DARK = (0x1F, 0x29, 0x2C); ACC = (0xE1, 0x74, 0x2F)
GREEN = (0x3F, 0x7B, 0x61); GOLD = (0xBE, 0x86, 0x42); RED = (0xB4, 0x47, 0x3B)
CREAM = (0xF4, 0xED, 0xDF); SKIN = (0xEB, 0xC8, 0xA2); WHITE = (255, 255, 255)
SKIN_D = (0xD6, 0xA9, 0x82); HEART = (0xD2, 0x4B, 0x3E); HEART_D = (0xA8, 0x36, 0x2E)
YEL = (0xF6, 0xC9, 0x45); YEL_D = (0xE8, 0xA8, 0x2E); BROWN = (0x5A, 0x3A, 0x22)
FONT_XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_BL = "/usr/share/fonts/opentype/inter/Inter-Black.otf"

def sp(p): return (p[0] * K, p[1] * K)

# ------------------------------------------------------------------ easing
def clamp01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def lerp(a, b, t): return a + (b - a) * t
def e_out(x): x = clamp01(x); return 1 - (1 - x) ** 3
def e_in(x): x = clamp01(x); return x ** 3
def e_io(x): x = clamp01(x); return x * x * (3 - 2 * x)
def e_sine(x): x = clamp01(x); return -(math.cos(math.pi * x) - 1) / 2
def e_back(x, s=1.9):
    x = clamp01(x) - 1; return x * x * ((s + 1) * x + s) + 1
def pop(f, f0, n=6, a=0.8):
    """overlay pop: scale a -> 1 over n frames starting at frame f0"""
    return a + (1 - a) * e_out((f - f0) / n)

# ------------------------------------------------------------------ text
def uz(text):
    """ASCII apostrophes -> Uzbek letters: o' g' use U+02BB, other ' (tutuq) uses U+02BC."""
    out = []
    for i, ch in enumerate(text):
        if ch in "'’`":
            prev = text[i - 1] if i else ""
            out.append("ʻ" if prev in "oOgG" else "ʼ")
        else: out.append(ch)
    return "".join(out)

@functools.lru_cache(maxsize=64)
def font(path, size): return ImageFont.truetype(path, int(size))

# ------------------------------------------------------------------ supersampled canvas
class SS:
    def __init__(self, w, h, ss=4):
        self.w, self.h, self.ss = int(math.ceil(w)), int(math.ceil(h)), ss
        self.im = Image.new("RGBA", (self.w * ss, self.h * ss), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
    def P(self, pts): return [(x * self.ss, y * self.ss) for x, y in pts]
    def B(self, b): return [v * self.ss for v in b]
    def poly(self, pts, fill=None, outline=None, width=0):
        self.d.polygon(self.P(pts), fill=fill)
        if outline and width:
            pp = self.P(pts) + [self.P(pts)[0]]
            self.d.line(pp, fill=outline, width=int(width * self.ss), joint="curve")
            for x, y in self.P(pts):
                r = width * self.ss / 2; self.d.ellipse([x - r, y - r, x + r, y + r], fill=outline)
    def ell(self, b, fill=None, outline=None, width=0):
        self.d.ellipse(self.B(b), fill=fill, outline=outline, width=int(width * self.ss))
    def rrect(self, b, r, fill=None, outline=None, width=0):
        self.d.rounded_rectangle(self.B(b), radius=r * self.ss, fill=fill, outline=outline, width=int(width * self.ss))
    def line(self, pts, fill, width):
        self.d.line(self.P(pts), fill=fill, width=int(width * self.ss), joint="curve")
        r = width * self.ss / 2
        for x, y in (self.P(pts)[0], self.P(pts)[-1]): self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill)
    def arc(self, b, a0, a1, fill, width):
        self.d.arc(self.B(b), a0, a1, fill=fill, width=int(width * self.ss))
    def image(self): return self.im.resize((self.w, self.h), Image.LANCZOS)

# ------------------------------------------------------------------ icons (flat, one cel tone, dark outline)
@functools.lru_cache(maxsize=32)
def icon_cross(sz, color=ACC):
    c = SS(sz, sz); w = sz * 0.2; m = sz * 0.2
    c.line([(m, m), (sz - m, sz - m)], color, w); c.line([(sz - m, m), (m, sz - m)], color, w)
    return c.image()

@functools.lru_cache(maxsize=32)
def icon_plane(sz, fill=WHITE, shade=(0xD9, 0xD4, 0xCB), outline=DARK):
    c = SS(sz, sz); s = sz; ow = max(2.0, sz * 0.05)
    T, N, Wb, F = (0.04 * s, 0.40 * s), (0.97 * s, 0.10 * s), (0.42 * s, 0.93 * s), (0.40 * s, 0.58 * s)
    c.poly([T, N, F], fill=fill, outline=outline, width=ow)
    c.poly([F, N, Wb], fill=shade, outline=outline, width=ow)
    c.poly([F, Wb, (0.30 * s, 0.70 * s)], fill=tuple(int(v * 0.85) for v in shade), outline=outline, width=ow)
    return c.image()

@functools.lru_cache(maxsize=32)
def icon_point_down(sz):
    c = SS(sz, sz); s = sz; ow = max(2.0, s * 0.055)
    shapes = [("r", (0.16, 0.02, 0.84, 0.50), 0.16), ("r", (0.40, 0.28, 0.62, 0.98), 0.11),
              ("r", (0.05, 0.14, 0.30, 0.40), 0.12)]
    for kind, b, r in shapes:   # silhouette outline first, then fill
        bb = (b[0] * s - ow, b[1] * s - ow, b[2] * s + ow, b[3] * s + ow); c.rrect(bb, r * s + ow, fill=DARK)
    for kind, b, r in shapes:
        c.rrect((b[0] * s, b[1] * s, b[2] * s, b[3] * s), r * s, fill=SKIN)
    for x in (0.62, 0.73):
        c.line([(x * s, 0.30 * s), (x * s, 0.46 * s)], SKIN_D, s * 0.035)
    c.line([(0.42 * s, 0.86 * s), (0.60 * s, 0.86 * s)], SKIN_D, s * 0.03)
    return c.image()

def _heart_pts(cx, cy, r, n=120):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x = 16 * math.sin(a) ** 3; y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((cx + x * r / 17, cy + y * r / 17))
    return pts

@functools.lru_cache(maxsize=8)
def icon_heart(sz):
    c = SS(sz, sz); r = sz * 0.47; cx, cy = sz / 2, sz * 0.50; ow = sz * 0.05
    pts = _heart_pts(cx, cy, r)
    c.poly(pts, fill=HEART, outline=DARK, width=ow)
    # cel shade on the lower right
    sh = SS(sz, sz); sh.poly(_heart_pts(cx, cy, r * 0.93), fill=HEART_D)
    cut = Image.new("L", sh.im.size, 0); ImageDraw.Draw(cut).polygon(
        [(sz * 0.30 * 4, sz * 4), (sz * 4, sz * 0.22 * 4), (sz * 4, sz * 4)], fill=255)
    sh.im.putalpha(Image.fromarray(np.minimum(np.asarray(sh.im.split()[3]), np.asarray(cut))))
    c.im.alpha_composite(sh.im)
    c.poly(pts, outline=DARK, width=ow)
    c.ell((sz * 0.22, sz * 0.22, sz * 0.36, sz * 0.36), fill=(255, 255, 255, 200))
    return c.image()

@functools.lru_cache(maxsize=8)
def icon_comment(sz):
    c = SS(sz, sz * 0.92); s = sz; ow = s * 0.055
    c.poly([(0.20 * s, 0.60 * s), (0.44 * s, 0.66 * s), (0.14 * s, 0.88 * s)], fill=WHITE, outline=DARK, width=ow)
    c.rrect((0.05 * s, 0.06 * s, 0.95 * s, 0.68 * s), 0.2 * s, fill=WHITE, outline=DARK, width=ow)
    c.poly([(0.22 * s, 0.60 * s), (0.42 * s, 0.62 * s), (0.17 * s, 0.82 * s)], fill=WHITE)
    for x in (0.30, 0.50, 0.70):
        c.ell(((x - 0.07) * s, 0.30 * s, (x + 0.07) * s, 0.44 * s), fill=ACC)
    return c.image()

@functools.lru_cache(maxsize=8)
def icon_bulb(sz):
    c = SS(sz, sz); s = sz; ow = s * 0.045
    c.ell((0.20 * s, 0.04 * s, 0.80 * s, 0.64 * s), fill=YEL, outline=BROWN, width=ow)
    c.arc((0.28 * s, 0.12 * s, 0.72 * s, 0.56 * s), 200, 260, (255, 248, 210), s * 0.05)
    c.rrect((0.36 * s, 0.60 * s, 0.64 * s, 0.88 * s), 0.05 * s, fill=(0xB7, 0xB2, 0xAA), outline=BROWN, width=ow)
    for y in (0.69, 0.78): c.line([(0.38 * s, y * s), (0.62 * s, y * s)], BROWN, s * 0.03)
    c.line([(0.44 * s, 0.94 * s), (0.56 * s, 0.94 * s)], BROWN, s * 0.06)
    c.line([(0.42 * s, 0.56 * s), (0.46 * s, 0.38 * s), (0.54 * s, 0.38 * s), (0.58 * s, 0.56 * s)], BROWN, s * 0.025)
    return c.image()

@functools.lru_cache(maxsize=8)
def icon_sun(sz):
    c = SS(sz, sz); s = sz; cx = cy = s / 2; ow = s * 0.04
    for i in range(12):
        a = 2 * math.pi * i / 12; b = 0.13
        p = [(cx + math.cos(a - b) * s * 0.30, cy + math.sin(a - b) * s * 0.30),
             (cx + math.cos(a) * s * 0.48, cy + math.sin(a) * s * 0.48),
             (cx + math.cos(a + b) * s * 0.30, cy + math.sin(a + b) * s * 0.30)]
        c.poly(p, fill=YEL_D, outline=BROWN, width=ow * 0.7)
    c.ell((cx - s * 0.29, cy - s * 0.29, cx + s * 0.29, cy + s * 0.29), fill=YEL, outline=BROWN, width=ow)
    for ex in (-0.10, 0.10):
        c.arc((cx + (ex - 0.05) * s, cy - 0.10 * s, cx + (ex + 0.05) * s, cy - 0.01 * s), 200, 340, BROWN, s * 0.03)
    c.arc((cx - 0.12 * s, cy - 0.06 * s, cx + 0.12 * s, cy + 0.15 * s), 20, 160, BROWN, s * 0.035)
    return c.image()

ICONS = {"cross": icon_cross, "plane": lambda sz: icon_plane(sz, fill=ACC, shade=(0xC2, 0x5E, 0x22)),
         "down": icon_point_down}

# ------------------------------------------------------------------ rich text lines
def rich_block(lines, size, path=FONT_XB, gap=0.18, align="center"):
    """lines: list of lists of (kind, value, color); kind 't' text or 'i' icon name.
    Returns RGBA image tightly around the text block."""
    f = font(path, size)
    asc, desc = f.getmetrics()
    lh = int(size * (1 + gap)); space = f.getlength(" ")
    widths = []
    for ln in lines:
        w = 0
        for i, (k, v, col) in enumerate(ln):
            w += f.getlength(v) if k == "t" else size * 0.95
            if i < len(ln) - 1: w += space
        widths.append(w)
    bw = int(math.ceil(max(widths))) + 4; bh = lh * (len(lines) - 1) + asc + desc
    im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for li, ln in enumerate(lines):
        x = (bw - widths[li]) / 2 if align == "center" else 0; y = li * lh
        for i, (k, v, col) in enumerate(ln):
            if k == "t":
                d.text((x, y), v, font=f, fill=col); x += f.getlength(v)
            else:
                isz = int(size * 0.95); ic = ICONS[v](isz)
                im.alpha_composite(ic, (int(x), int(y + asc - size * 0.80)))
                x += isz
            if i < len(ln) - 1: x += space
    return im

def shadowed(im, radius=14, offset=(0, 8), alpha=70):
    pad = radius * 3
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    a = Image.new("L", out.size, 0); a.paste(im.split()[3], (pad + offset[0], pad + offset[1]))
    a = a.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: v * alpha // 255)
    sh = Image.new("RGBA", out.size, (20, 25, 28, 0)); sh.putalpha(a)
    out.alpha_composite(sh); out.alpha_composite(im, (pad, pad))
    return out

def card(lines, size, pad=(38, 24), radius=30, fill=WHITE, opacity=255, outline=None, shadow=True, max_w=None, path=FONT_XB):
    blk = rich_block(lines, size, path)
    if max_w and blk.width + 2 * pad[0] > max_w:
        return card(lines, size * 0.94, pad, radius, fill, opacity, outline, shadow, max_w, path)
    w, h = blk.width + 2 * pad[0], blk.height + 2 * pad[1] + int(size * 0.06)
    c = SS(w, h); c.rrect((0, 0, w, h), min(radius, h / 2), fill=fill + (opacity,),
                          outline=outline, width=3 if outline else 0)
    im = c.image(); im.alpha_composite(blk, (pad[0], pad[1]))
    return shadowed(im) if shadow else im

def paste_center(dst, rgba, cx, cy, scale=1.0, alpha=1.0, angle=0.0):
    if scale <= 0.01 or alpha <= 0.003: return
    im = rgba
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, int(round(im.width * scale))), max(1, int(round(im.height * scale)))), Image.BICUBIC)
    if abs(angle) > 0.05: im = im.rotate(angle, Image.BICUBIC, expand=True)
    if alpha < 0.999:
        im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * alpha)))
    x, y = int(round(cx - im.width / 2)), int(round(cy - im.height / 2))
    dst.paste(im, (x, y), im)

def paste_affine(dst, src, P0, Pu, Pv, scale=1.0, alpha=1.0):
    """Map src (0,0)->P0, (w,0)->Pu, (0,h)->Pv, optional scale about src centre."""
    w, h = src.size
    ux, uy = (Pu[0] - P0[0]) / w, (Pu[1] - P0[1]) / w
    vx, vy = (Pv[0] - P0[0]) / h, (Pv[1] - P0[1]) / h
    # include scale about centre: q = c + s (p - c) in src space
    cxs, cys = w / 2, h / 2
    M = np.array([[ux * scale, vx * scale, 0], [uy * scale, vy * scale, 0], [0, 0, 1.0]])
    off = np.array(P0) + np.array([[ux, vx], [uy, vy]]) @ np.array([cxs * (1 - scale), cys * (1 - scale)])
    M[0, 2], M[1, 2] = off
    corners = M @ np.array([[0, w, w, 0], [0, 0, h, h], [1, 1, 1, 1.0]])
    x0, y0 = np.floor(corners[:2].min(1)).astype(int) - 2; x1, y1 = np.ceil(corners[:2].max(1)).astype(int) + 2
    Mi = np.linalg.inv(M)
    T = Mi @ np.array([[1, 0, x0], [0, 1, y0], [0, 0, 1.0]])
    out = src.transform((x1 - x0, y1 - y0), Image.AFFINE, tuple(T[0]) + tuple(T[1]), Image.BICUBIC)
    if alpha < 0.999: out.putalpha(out.split()[3].point(lambda v: int(v * alpha)))
    dst.paste(out, (int(x0), int(y0)), out)
