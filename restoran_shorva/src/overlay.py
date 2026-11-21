# On-screen headline text (upper third) and one-word subtitle pills (safe zone, y≈1380).
import json, re, functools
from PIL import Image, ImageDraw, ImageFilter
from common import *
from script_data import ON_SCREEN, KEYWORDS

HEAD_SIZE = 80
HEAD_CY = 425
HEAD_MAXW = 920
SUB_SIZE = 74
SUB_CY = 1380
SUB_MAXW = 1080 - 2 * 120

def _norm(w):
    w = w.lower()
    for a in "ʻʼ'`‘’": w = w.replace(a, "'")
    return re.sub(r"[^a-z']", "", w)

def _runs_for(line, accents):
    runs = []
    toks = line.split(" ")
    for i, tk in enumerate(toks):
        acc = any(tk == a or tk.rstrip("!?.,") == a.rstrip("!?.,") for a in accents) or any(tk.startswith(a) and "+" in tk for a in accents)
        if "+" in tk:   # "Choy+xona": accent the first part
            a, b = tk.split("+", 1)
            runs.append((uz(a), ACCENT if a in accents else INK)); runs.append(("+" + uz(b), INK))
        else:
            runs.append((uz(tk), ACCENT if acc else INK))
        if i < len(toks) - 1: runs.append((" ", INK))
    return runs

@functools.lru_cache(maxsize=32)
def headline_img(k):
    text, accents = ON_SCREEN[k]
    lines = [text]
    im = text_runs(_runs_for(text, accents), HEAD_SIZE, FONT_BLACK)
    if HEAD_MAXW < im.width <= HEAD_MAXW * HEAD_SIZE / 70:   # fits on one line at >= 70 px
        return glow(im.resize((HEAD_MAXW, int(im.height * HEAD_MAXW / im.width)), Image.LANCZOS), CREAM, 13, strength=2.6, spread=9)
    if im.width > HEAD_MAXW:
        ws = text.split(" "); best = None
        for c in range(1, len(ws)):
            a, b = " ".join(ws[:c]), " ".join(ws[c:])
            d = abs(len(a) - len(b))
            if best is None or d < best[0]: best = (d, [a, b])
        lines = best[1]
    imgs = [text_runs(_runs_for(l, accents), HEAD_SIZE, FONT_BLACK) for l in lines]
    lh = int(HEAD_SIZE * 1.12)
    wmax = max(i.width for i in imgs)
    canvas = Image.new("RGBA", (wmax, lh * (len(imgs) - 1) + imgs[-1].height), (0, 0, 0, 0))
    for j, i in enumerate(imgs):
        canvas.alpha_composite(i, ((wmax - i.width) // 2, j * lh))
    if canvas.width > HEAD_MAXW:
        s = HEAD_MAXW / canvas.width
        canvas = canvas.resize((int(canvas.width * s), int(canvas.height * s)), Image.LANCZOS)
    return glow(canvas, CREAM, 13, strength=2.6, spread=9)

def paste_center(frame, im, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if alpha < 0.999:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    frame.paste(im, (int(round(cx - im.width / 2)), int(round(cy - im.height / 2))), im)

def draw_headline(frame, k, lf, pop=True, alpha=1.0, cy=HEAD_CY, scale_extra=1.0):
    im = headline_img(k)
    s = 1.0
    if pop: s = 0.92 + 0.08 * ease_out(lf / 6.0)
    paste_center(frame, im, 540, cy, s * scale_extra, alpha)
    return im

# ---------------------------------------------------------------- subtitles
def sub_text(w):
    t = w.rstrip(",.:;")
    return uz(t)

@functools.lru_cache(maxsize=128)
def pill_img(text, key):
    col = ACCENT if key else INK
    im = text_runs([(text, col)], SUB_SIZE, FONT_BLACK)
    bb = im.getbbox()
    f = font(FONT_BLACK, SUB_SIZE); asc, desc = f.getmetrics()
    padx, pady = 36, 20
    th = int(SUB_SIZE * 0.98)
    pw, ph = bb[2] - bb[0] + 2 * padx, th + 2 * pady
    if pw > SUB_MAXW:
        s = SUB_MAXW / pw
        im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS); bb = im.getbbox()
        pw, ph = bb[2] - bb[0] + 2 * padx, int(th * s) + 2 * pady
    sh = 14
    out = Image.new("RGBA", (pw + 2 * sh, ph + 2 * sh + 6), (0, 0, 0, 0))
    shadow = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((sh, sh + 6, sh + pw, sh + ph + 6), radius=ph // 2, fill=(20, 28, 30, 70))
    out.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(7)))
    pill = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle((sh, sh, sh + pw, sh + ph), radius=ph // 2, fill=CREAM + (int(255 * 0.85),))
    out.alpha_composite(pill)
    # vertically center the cap-height of the text in the pill
    cap_top = 4 + asc - int(SUB_SIZE * 0.73)
    ty = sh + (ph - int(SUB_SIZE * 0.73)) // 2 - cap_top
    # x-height-centred looks better for lowercase-only words
    out.alpha_composite(im, (sh + padx - bb[0], ty))
    return out

def is_key(w):
    return _norm(w) in KEYWORDS

def draw_subtitle(frame, word, lf):
    im = pill_img(sub_text(word), is_key(word))
    s = 0.95 + 0.05 * ease_out(lf / 3.0)
    paste_center(frame, im, 540, SUB_CY, s)
    return im.size
