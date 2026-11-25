# Frame renderer: scene (cairo) -> grain/vignette -> on-screen text + karaoke subtitles (PIL) -> ffmpeg.
import sys, os, math, time, subprocess, functools
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import style as ST
from style import W, H, FPS, hx, clamp01, ease_out_back, ease
import timeline as TL
import scenes as SC
from script_data import ON_SCREEN

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(os.path.dirname(HERE), "fonts", "Nunito_900.ttf")
FONT_SUB = os.path.join(os.path.dirname(HERE), "fonts", "Nunito_800.ttf")

def C8(h): return tuple(int(v * 255 + 0.5) for v in hx(h))
INK = C8("#1F292C"); CREAM = C8("#F4EDDF"); HI = C8("#E1742F"); ICON = C8("#E7A05C")
NIGHT_SCENES = set(range(6, 15))

@functools.lru_cache(maxsize=64)
def font(path, size): return ImageFont.truetype(path, size)

# ------------------------------------------------------------------ Uzbek apostrophes: Nunito gives ʻ/ʼ wide side bearings; tighten them
APOS_TRIM = {"ʻ": 0.125, "ʼ": 0.075}   # trimmed from each side, as a fraction of the font size

def _runs(s):
    out, cur = [], ""
    for ch in s:
        if ch in APOS_TRIM:
            if cur: out.append(cur); cur = ""
            out.append(ch)
        else: cur += ch
    if cur: out.append(cur)
    return out

def uz_len(f, s):
    return f.getlength(s) - sum(2 * APOS_TRIM[c] * f.size for c in s if c in APOS_TRIM)

def uz_draw(d, xy, s, f, fill, anchor=None):
    x, y = xy
    if anchor == "mm":
        x -= uz_len(f, s) / 2; anchor = "lm"
    for r in _runs(s):
        if r in APOS_TRIM:
            tr = APOS_TRIM[r] * f.size
            d.text((x - tr, y), r, font=f, fill=fill, anchor=anchor)
            x += f.getlength(r) - 2 * tr
        else:
            d.text((x, y), r, font=f, fill=fill, anchor=anchor)
            x += f.getlength(r)

# ------------------------------------------------------------------ headline (on-screen text)
HEAD = {
    1: [[("90%", 1), (" — SOTADI", 0)]],
    2: [[("VOZ KECHDI", 0)]],
    3: [[("ORZULAR", 0)]],
    5: [[("OʻCHIRILDI", 0)]],
    6: [[("2", 1), ("-RAUND", 0)]],
    7: [[("+$1 000 000", 1)]],
    8: [[("EVAZIGA — ", 0), ("U", 1)]],
    9: [[("$0", 1)]],
    10: [[("$2 000 000", 1)]],
    11: [[("1-RAUNDDA — SIZ.", 0)], [("ENDI — ", 0), ("U?", 1)]],
    12: [[("IZOHDA:", 0)], [("1", 1), (" — QIZ · ", 0), ("2", 1), (" — PUL", 0)]],
    13: [[("UNGA YUBOR ", 0), ("@plane", 1)]],
    14: [[("NATIJA —", 0)], [("KEYINGI VIDEODA", 0)]],
}
# exact on-screen strings from the script (checked in QA)
HEAD_TEXT = {k: " ".join("".join(s for s, _ in line) for line in v).replace("@plane", "✈️") for k, v in HEAD.items()}

def plane_icon(size, col):
    im = Image.new("RGBA", (int(size * 1.25), int(size)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size / 24.0
    def P(pts): return [(x * s + 1, y * s + 1) for x, y in pts]
    dark = tuple(int(c * 0.78) for c in col[:3])
    d.polygon(P([(0, 11), (28, 1), (9, 15)]), fill=col)
    d.polygon(P([(9, 15), (28, 1), (13, 22)]), fill=dark)
    d.polygon(P([(9, 15), (13, 22), (8, 21)]), fill=dark)
    return im

@functools.lru_cache(maxsize=32)
def head_img(k):
    lines = HEAD[k]
    night = k in NIGHT_SCENES
    base = CREAM if night else INK
    accent = ICON if night else HI
    size = 98 if len(lines) == 1 and sum(len(s) for s, _ in lines[0]) <= 14 else 84
    f = font(FONT, size)
    rows = []
    for line in lines:
        segs = []
        for s, a in line:
            if s == "@plane":
                segs.append(plane_icon(int(size * 0.78), ICON + (255,)))
                continue
            im = Image.new("RGBA", (int(uz_len(f, s)) + 6, int(size * 1.3)), (0, 0, 0, 0))
            uz_draw(ImageDraw.Draw(im), (0, int(size * 0.1)), s, f, (accent if a else base) + (255,))
            segs.append(im)
        wsum = sum(s.width for s in segs); hh = max(s.height for s in segs)
        row = Image.new("RGBA", (wsum, hh), (0, 0, 0, 0)); x = 0
        for s in segs:
            row.alpha_composite(s, (x, (hh - s.height) // 2)); x += s.width
        rows.append(row)
    gap = int(size * 0.02)
    wmax = max(r.width for r in rows); htot = sum(r.height for r in rows) + gap * (len(rows) - 1)
    out = Image.new("RGBA", (wmax + 60, htot + 60), (0, 0, 0, 0)); y = 30
    for r in rows:
        out.alpha_composite(r, ((out.width - r.width) // 2, y)); y += r.height + gap
    # soft shadow for legibility
    a = out.getchannel("A")
    sh_col = (8, 12, 18) if night else (255, 252, 244)
    sh = Image.new("RGBA", out.size, sh_col + (0,)); sh.putalpha(a.point(lambda v: int(v * (0.55 if night else 0.5))))
    sh = sh.filter(ImageFilter.GaussianBlur(9 if night else 12))
    res = Image.new("RGBA", out.size, (0, 0, 0, 0)); res.alpha_composite(sh, (0, 4)); res.alpha_composite(out)
    return res

HEAD_Y = 330

def head_layer(img, k, i):
    if k not in HEAD: return None
    im = head_img(k)
    lf = i - TL.SC_FRAME[k]
    if k == 1:
        s = 1.0 + 0.012 * math.sin(i / FPS * 2.4); al = 1.0
    else:
        s = 0.86 + 0.14 * ease_out_back(clamp01(lf / 7.0), 2.0); al = clamp01((lf + 1) / 3.0)
    if k == 14 and i >= TL.wframe(TL.scene_words(14)[3]):
        s = 1.0; al = 1.0
    if abs(s - 1) > 0.003:
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    if al < 0.999:
        a = im.getchannel("A").point(lambda v: int(v * al)); im = im.copy(); im.putalpha(a)
    x = int(540 - im.width / 2); y = int(HEAD_Y - 30 - (im.height - 60) * 0.0 - 30 * s)
    img.alpha_composite(im, (x, max(0, y)))
    return (x, max(0, y), x + im.width, max(0, y) + im.height)

# ------------------------------------------------------------------ subtitles: one line at a time, current word highlighted
SUB_SIZE = 70
SUB_Y = 1475
SUB_MAXW = 840
PAD_X, PAD_Y = 34, 18

MAXC = 25
FORCE_BREAK = {(13, "qanday")}   # shot change inside scene 13

def build_lines():
    """phrase-aware chunking: split at punctuation, balance long phrases, merge short neighbours"""
    f = font(FONT_SUB, SUB_SIZE)
    def txt(ws): return " ".join(w["text"] for w in ws)
    def fits(ws): return len(txt(ws)) <= MAXC and len(ws) <= 5 and uz_len(f, txt(ws)) <= SUB_MAXW
    lines = []
    for k in TL.SC_IDS:
        ws = TL.scene_words(k)
        phrases, cur = [], []
        for w in ws:
            if (k, w["text"]) in FORCE_BREAK and cur:
                phrases.append(cur); cur = []
            cur.append(w)
            if w["text"].endswith((".", ",", "?", "!", ":", "—")):
                phrases.append(cur); cur = []
        if cur: phrases.append(cur)
        chunks = []
        for ph in phrases:
            if fits(ph): chunks.append(ph); continue
            n = 2
            while True:
                best = None
                import itertools
                for cuts in itertools.combinations(range(1, len(ph)), n - 1):
                    parts = [ph[i:j] for i, j in zip((0,) + cuts, cuts + (len(ph),))]
                    if all(fits(p) for p in parts):
                        sc = max(len(txt(p)) for p in parts)
                        if best is None or sc < best[0]: best = (sc, parts)
                if best: chunks.extend(best[1]); break
                n += 1
        merged = []
        for c in chunks:
            if merged and not txt(merged[-1]).endswith((".", "?", "!")) and fits(merged[-1] + c) and (k, c[0]["text"]) not in FORCE_BREAK:
                merged[-1] = merged[-1] + c
            else:
                merged.append(c)
        lines.extend(merged)
    return lines

LINES = build_lines()
LINE_FRAME = [TL.wframe(l[0]) for l in LINES]
WORD_FRAME = {id(w): TL.wframe(w) for w in TL.WORDS}

@functools.lru_cache(maxsize=256)
def line_img(li, active):
    f = font(FONT_SUB, SUB_SIZE)
    ws = LINES[li]
    sp = f.getlength(" ")
    widths = [uz_len(f, w["text"]) for w in ws]
    tw = sum(widths) + sp * (len(ws) - 1)
    asc, desc = f.getmetrics()
    th = asc + desc
    pw, ph = int(tw + 2 * PAD_X), int(th * 0.92 + 2 * PAD_Y)
    im = Image.new("RGBA", (pw + 20, ph + 20), (0, 0, 0, 0))
    plate = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(plate).rounded_rectangle((10, 10, 10 + pw, 10 + ph), radius=ph // 2.4, fill=CREAM + (int(255 * 0.85),))
    sh = Image.new("RGBA", im.size, (10, 14, 20, 0))
    ImageDraw.Draw(sh).rounded_rectangle((10, 14, 10 + pw, 14 + ph), radius=ph // 2.4, fill=(10, 14, 20, 60))
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    im.alpha_composite(sh); im.alpha_composite(plate)
    d = ImageDraw.Draw(im)
    x = 10 + PAD_X; y = 10 + PAD_Y - int(th * 0.04)
    for j, w in enumerate(ws):
        uz_draw(d, (x, y), w["text"], f, (HI if j == active else INK) + (255,))
        x += widths[j] + sp
    return im

def current_line(i):
    li = None
    for j, fr in enumerate(LINE_FRAME):
        if i >= fr: li = j
    return li

def sub_layer(img, i):
    li = current_line(i)
    if li is None: return None
    ws = LINES[li]
    act = 0
    for j, w in enumerate(ws):
        if i >= WORD_FRAME[id(w)]: act = j
    im = line_img(li, act)
    x = int(540 - im.width / 2); y = int(SUB_Y - im.height / 2)
    img.alpha_composite(im, (x, y))
    return (x + 10, y + 10, x + im.width - 10, y + im.height - 10)

def active_word(i):
    li = current_line(i)
    if li is None: return None
    act = None
    for w in LINES[li]:
        if i >= WORD_FRAME[id(w)]: act = w
    return act or LINES[li][0]

# ------------------------------------------------------------------ scene items placed as text (tags, bubble digits)
def items_layer(img, items):
    d = ImageDraw.Draw(img)
    for it in items:
        if it[0] in ("tag", "bubble"):
            _, txt, x, y, size = it
            if size < 4: continue
            f = font(FONT, max(4, int(size)))
            d.text((x, y), txt, font=f, fill=INK + (255,), anchor="mm")

# ------------------------------------------------------------------ frame
def scene_rgb(k, i, t):
    lt = t - TL.SC_START[k]
    D = TL.SC_END_FRAME[k] / FPS - TL.SC_START[k]
    hero = k in SC.HERO_SCENES or (k == 13 and t < TL.word_t(13, 5))
    ST.set_hero_frame(hero)
    surf, ctx = ST.new_surface()
    items = SC.SCENE_FN[k](ctx, t, max(0.0, lt), D) or []
    surf.flush()
    arr = ST.surface_rgb(surf)
    opts = {it[0]: it[1] for it in items if isinstance(it, tuple) and it[0].startswith("__")}
    return arr, items, opts, hero

XFADE_23 = [0.5, 0.7, 0.86]   # scene 2 -> 3: short dissolve into the flashback (scene 3 owns the frame from its first word)

def render_frame(i, overlays=True, return_parts=False):
    t = i / FPS
    k = TL.scene_at(i)
    arr, items, opts, hero = scene_rgb(k, i, t)
    if k == 3 and i - TL.SC_FRAME[3] < len(XFADE_23):
        a = XFADE_23[i - TL.SC_FRAME[3]]
        arr2, _, _, _ = scene_rgb(2, i, t)
        arr = arr * a + arr2 * (1 - a)
    out = ST.finish(arr, grey=opts.get("__grey__", 0.0), flash=opts.get("__flash__", 0.0))
    if return_parts:
        scene_only = out.copy()
    img = Image.fromarray(out, "RGB").convert("RGBA")
    boxes = {}
    if overlays:
        items_layer(img, items)
        boxes["head"] = head_layer(img, k, i)
        boxes["sub"] = sub_layer(img, i)
    res = np.asarray(img.convert("RGB"))
    if return_parts:
        return res, scene_only, boxes, hero
    return res

def _work(i):
    return i, render_frame(i).tobytes()

def main(out_video, procs=4, frames=None):
    idx = list(range(TL.N_FRAMES)) if frames is None else frames
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS), out_video]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with Pool(procs) as pool:
        for n, (i, b) in enumerate(pool.imap(_work, idx, chunksize=4)):
            p.stdin.write(b)
            if n % 100 == 0: print(f"frame {n}/{len(idx)}  {time.time() - t0:.1f}s", flush=True)
    p.stdin.close(); p.wait()
    print("done", round(time.time() - t0, 1), "s")

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
        for f in [int(x) for x in sys.argv[3].split(",")]:
            Image.fromarray(render_frame(f)).save(os.path.join(outdir, f"f{f:04d}.png"))
            print("saved", f, TL.scene_at(f))
    else:
        main(sys.argv[1])
