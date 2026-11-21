# Subtitle plate (full line, current word in accent) and screen-space on-screen texts.
import functools
from PIL import Image, ImageDraw, ImageFilter
from common import *
from script_data import SCENES, WORDS, LINES

PLATE = hx("F4EDDF"); TXT = hx("1F292C")
SUB_SIZE = 64
SUB_FONT = FONT_XBOLD
SUB_CY = 1392          # plate centre (safe zone: above the bottom UI, clear of the right-side buttons)
SUB_MAXW = 860
LINE_H = 80

def _split_lines(toks, f):
    full = " ".join(toks)
    if f.getlength(full) <= SUB_MAXW - 64: return [list(range(len(toks)))]
    best = None
    for c in range(1, len(toks)):
        a = f.getlength(" ".join(toks[:c])); b = f.getlength(" ".join(toks[c:]))
        sc = max(a, b)
        if best is None or sc < best[0]: best = (sc, c)
    c = best[1]
    return [list(range(c)), list(range(c, len(toks)))]

def _core(tok):
    """split token into (word, trailing punctuation)"""
    i = len(tok)
    while i > 0 and tok[i - 1] in ",.!?:;": i -= 1
    return tok[:i], tok[i:]

@functools.lru_cache(maxsize=256)
def plate_img(scene_id, cur_idx):
    line = LINES[scene_id - 1]
    toks = line.split(" ")
    f = font(SUB_FONT, SUB_SIZE)
    rows = _split_lines(toks, f)
    sp = f.getlength(" ")
    widths = [sum(f.getlength(toks[i]) for i in r) + sp * (len(r) - 1) for r in rows]
    tw = max(widths)
    scale = min(1.0, (SUB_MAXW - 64) / tw)
    padx, pady = 32, 20
    pw = int(tw * scale + 2 * padx); ph = int(LINE_H * scale * len(rows) + 2 * pady)
    sh = 16
    out = Image.new("RGBA", (pw + 2 * sh, ph + 2 * sh + 6), (0, 0, 0, 0))
    shadow = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((sh, sh + 6, sh + pw, sh + ph + 6), radius=30, fill=(20, 28, 30, 60))
    out.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
    pl = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(pl).rounded_rectangle((sh, sh, sh + pw, sh + ph), radius=30, fill=PLATE + (int(255 * 0.85),))
    out.alpha_composite(pl)
    # text at 1x scale then resized if needed
    tl = Image.new("RGBA", (int(tw) + 8, LINE_H * len(rows) + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(tl)
    asc, desc = f.getmetrics()
    cap = SUB_SIZE * 0.72
    for li, r in enumerate(rows):
        x = 4 + (tw - widths[li]) / 2
        base = 4 + li * LINE_H + (LINE_H + cap) / 2
        for j, i in enumerate(r):
            word, punct = _core(toks[i])
            col = ACCENT if i == cur_idx else TXT
            d.text((x, base), word, font=f, fill=col, anchor="ls"); x += f.getlength(word)
            if punct:
                d.text((x, base), punct, font=f, fill=TXT if i != cur_idx else ACCENT, anchor="ls"); x += f.getlength(punct)
            if j < len(r) - 1: x += sp
    if scale < 1: tl = tl.resize((int(tl.width * scale), int(tl.height * scale)), Image.LANCZOS)
    out.alpha_composite(tl, (sh + padx - int(4 * scale), sh + pady - int(4 * scale)))
    return out

def plate_box(scene_id):
    im = plate_img(scene_id, -1)
    return (540 - im.width / 2, SUB_CY - im.height / 2, 540 + im.width / 2, SUB_CY + im.height / 2)

def paste_center(frame, im, cx, cy, scale=1.0, alpha=1.0, ang=0.0):
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if ang:
        im = im.rotate(ang, resample=Image.BICUBIC, expand=True)
    if alpha < 0.999:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    frame.paste(im, (int(round(cx - im.width / 2)), int(round(cy - im.height / 2))), im)

def draw_subtitle(frame, f, scene_id):
    cur = -1
    for w in WORDS:
        if w["scene"] == scene_id and w["f0"] <= f: cur = w["idx"]
    paste_center(frame, plate_img(scene_id, cur), 540, SUB_CY)
    return cur

# ---------------------------------------------------------------- on-screen texts
@functools.lru_cache(maxsize=8)
def obunachi_img():
    f = font(FONT_BLACK, 46)
    t0, t1 = "0", " OBUNACHI"
    w = f.getlength(t0 + t1)
    padx, pady = 30, 16
    asc, desc = f.getmetrics()
    W_, H_ = int(w + 2 * padx), int(46 * 0.74 + 2 * pady + 6)
    sh = 12
    out = Image.new("RGBA", (W_ + 2 * sh, H_ + 2 * sh + 4), (0, 0, 0, 0))
    s = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(s).rounded_rectangle((sh, sh + 4, sh + W_, sh + H_ + 4), radius=H_ // 2, fill=(20, 28, 30, 55))
    out.alpha_composite(s.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((sh, sh, sh + W_, sh + H_), radius=H_ // 2, fill=PLATE + (int(255 * 0.9),))
    base = sh + H_ / 2 + 46 * 0.36
    d.text((sh + padx, base), t0, font=f, fill=ACCENT, anchor="ls")
    d.text((sh + padx + f.getlength(t0), base), t1, font=f, fill=TXT, anchor="ls")
    return out

@functools.lru_cache(maxsize=64)
def big_word(text, size, col=ACCENT, path=FONT_BLACK, halo=True, halo_col=None, track=0):
    im = text_runs([(text, col)], size, path, tracking=track)
    bb = im.getbbox(); im = im.crop(bb)
    if halo:
        im = glow(im, halo_col or PLATE, max(6, size // 9), strength=2.4, spread=max(3, (size // 14) | 1))
    return im

@functools.lru_cache(maxsize=16)
def bubble_img(text, size=40):
    f = font(FONT_BLACK, size)
    w = f.getlength(text)
    W_, H_ = int(w + 48), int(size * 1.35)
    out = Image.new("RGBA", (W_ + 20, H_ + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(out)
    d.rounded_rectangle((10, 10, 10 + W_, 10 + H_), radius=H_ // 2, fill=PLATE + (240,))
    d.polygon([(10 + W_ * 0.42, 8 + H_), (10 + W_ * 0.56, 8 + H_), (10 + W_ * 0.44, 10 + H_ + 22)], fill=PLATE + (240,))
    d.text((10 + W_ / 2, 10 + H_ / 2 + size * 0.05), text, font=f, fill=TXT, anchor="mm")
    return out
