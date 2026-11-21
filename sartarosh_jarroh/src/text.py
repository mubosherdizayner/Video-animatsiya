# Text rendering (PIL): heavy rounded font with outline, colour emoji, glyph coverage check.
import os, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_MAIN = os.path.join(os.path.dirname(HERE), "fonts", "Nunito-Black.ttf")
FONT_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
OUTLINE = (43, 27, 18)


@functools.lru_cache(maxsize=None)
def cmap(path):
    return TTFont(path).getBestCmap()


def is_emoji(ch):
    o = ord(ch)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF


def covers(path, s):
    cm = cmap(path)
    return all(ord(ch) in cm for ch in s if not is_emoji(ch) and ch not in " ️")


def pick_font(s):
    return FONT_MAIN if covers(FONT_MAIN, s) else FONT_FALLBACK


@functools.lru_cache(maxsize=256)
def font(path, size):
    return ImageFont.truetype(path, size)


def runs(s):
    s = s.replace("️", "")
    out = []
    for ch in s:
        e = is_emoji(ch)
        if out and out[-1][0] == e and not e:
            out[-1][1] += ch
        else:
            out.append([e, ch])
    return out


@functools.lru_cache(maxsize=64)
def emoji_img(ch, size, stroke):
    f = font(EMOJI_FONT, 109)
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((80, 80), ch, font=f, embedded_color=True, anchor="mm")
    im = im.crop(im.getbbox())
    s = size / max(im.width, im.height)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    pad = stroke + 2
    big = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    big.alpha_composite(im, (pad, pad))
    a = big.getchannel("A").point(lambda v: 255 if v > 40 else 0).filter(ImageFilter.MaxFilter(2 * stroke + 1))
    base = Image.new("RGBA", big.size, OUTLINE + (255,))
    base.putalpha(a)
    base.alpha_composite(big)
    return base


def text_line(s, size, fill=(255, 255, 255), stroke=8, stroke_fill=OUTLINE):
    """RGBA image of one line (text + emoji). Height = font line box."""
    path = pick_font(s)
    f = font(path, size)
    asc, desc = f.getmetrics()
    h = asc + desc + 2 * stroke
    parts = []
    for e, chunk in runs(s):
        if e:
            parts.append(emoji_img(chunk, int(size * 0.92), max(4, stroke - 2)))
        else:
            w = int(f.getlength(chunk)) + 2 * stroke
            im = Image.new("RGBA", (w + 4, h), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((stroke + 2, stroke), chunk, font=f, fill=fill + (255,),
                                    stroke_width=stroke, stroke_fill=stroke_fill + (255,))
            parts.append(im)
    W_ = sum(p.width for p in parts) - (len(parts) - 1) * stroke
    out = Image.new("RGBA", (max(1, W_), h), (0, 0, 0, 0))
    x = 0
    cap_mid = stroke + asc - size * 0.36  # visual centre of capitals
    for p in parts:
        y = 0 if p.height == h else int(cap_mid - p.height / 2)
        out.alpha_composite(p, (x, max(0, y)))
        x += p.width - stroke
    return out


def with_shadow(im, off=7, blur=8, alpha=0.45):
    pad = blur * 2 + off
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (20, 12, 6, 255))
    sh.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    out.alpha_composite(sh, (pad, pad + off))
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(im, (pad, pad))
    return out


def composite(frame, im, cx, cy, scale=1.0, alpha=1.0):
    """alpha-composite RGBA PIL image onto float RGB numpy frame, centred at (cx,cy)"""
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    x0 = int(round(cx - im.width / 2))
    y0 = int(round(cy - im.height / 2))
    H, W = frame.shape[:2]
    xa, ya = max(0, x0), max(0, y0)
    xb, yb = min(W, x0 + im.width), min(H, y0 + im.height)
    if xb <= xa or yb <= ya:
        return (x0, y0, x0 + im.width, y0 + im.height)
    sub = a[ya - y0:yb - y0, xa - x0:xb - x0]
    al = sub[..., 3:4] / 255.0 * alpha
    frame[ya:yb, xa:xb] = frame[ya:yb, xa:xb] * (1 - al) + sub[..., :3] * al
    return (x0, y0, x0 + im.width, y0 + im.height)
