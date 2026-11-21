# On-screen headline (upper third) and karaoke subtitles (one phrase line, spoken word highlighted).
import math
import skia
from common import *
from scenes import TIMING, SC_IDS, SC_FRAME, SC_END_FRAME, N_FRAMES, scene_words, word_frame, font, FONT_DISPLAY, FONT_BOLD
import icons as PR
from script_data import ONSCREEN

INK, CREAM, ACCENT = "#1F292C", "#F4EDDF", "#E1742F"

# ------------------------------------------------------------------ headline
HEAD_CY, HEAD_MAXW = 440, 940
ACCENT_WORDS = {1: {"ODAM?"}, 2: {"OLDIN"}, 3: {"LAVOZIM"}, 4: {"ORQAGA…"}, 5: {"1613"}, 6: {"HAM?"}, 7: {"QIZIGʻI", "→"},
                8: {"1945"}, 9: {"6"}, 11: {"COMPUTER"}, 12: {"✈"}, 13: {"IZOHDA", "👇"}}
ICONS = {"✈", "👇"}


def head_tokens(k):
    s = ONSCREEN.get(k, "")
    return [w for w in s.upper().split()] if s else []


def layout_head(k, size):
    f = font(FONT_DISPLAY, size)
    sp = f.measureText(" ")
    toks = head_tokens(k)
    widths = [size * 1.0 if t in ICONS else f.measureText(t) for t in toks]
    lines, cur, cw = [], [], 0.0
    for t, w in zip(toks, widths):
        add = w + (sp if cur else 0)
        if cur and cw + add > HEAD_MAXW:
            lines.append((cur, cw)); cur, cw = [(t, w)], w
        else:
            cur.append((t, w)); cw += add
    if cur: lines.append((cur, cw))
    return lines, sp


def fit_head(k):
    best = None
    for nl in (1, 2, 3):
        for size in (104, 96, 88, 82, 76, 70, 64):
            if nl == 1 and size < 76: break
            lines, sp = layout_head(k, size)
            if len(lines) == nl:
                return size, lines, sp
    return 62, *layout_head(k, 62)


_HEAD = {}


def head_layout(k):
    if k not in _HEAD:
        _HEAD[k] = fit_head(k)
    return _HEAD[k]


def head_bbox(k):
    size, lines, sp = head_layout(k)
    lh = size * 1.08
    tot = lh * len(lines)
    top = HEAD_CY - tot / 2
    w = max(wd for _, wd in lines) if lines else 0
    return (540 - w / 2, top - size * 0.05, 540 + w / 2, top + tot + size * 0.05)


def draw_headline(c, k, lf):
    toks = head_tokens(k)
    if not toks: return
    size, lines, sp = head_layout(k)
    base = INK                       # one morning palette: dark text everywhere
    halo = "#F4EDDF"
    f = font(FONT_DISPLAY, size)
    if k == 1:                       # hook text is fully visible at frame 0 (no fade-in)
        sc, al = 1.0 + 0.012 * math.sin(lf / FPS * 4.0), 1.0
    else:
        sc = 0.82 + 0.18 * ease_out_back(clamp01(lf / 9.0), 2.0)
        al = clamp01(lf / 4.0)
    lh = size * 1.08
    tot = lh * len(lines)
    y0 = HEAD_CY - tot / 2 + size * 0.80
    c.save(); c.translate(540, HEAD_CY); c.scale(sc, sc); c.translate(-540, -HEAD_CY)
    for li, (ln, lw) in enumerate(lines):
        x = 540 - lw / 2
        y = y0 + li * lh
        for t, w in ln:
            colr = ACCENT if t in ACCENT_WORDS.get(k, set()) else base
            if t == "✈":
                PR.plane_icon(c, x + w / 2, y - size * 0.36, size * 0.95, ACCENT)
            elif t == "👇":
                PR.hand_down_icon(c, x + w * 0.12, y - size * 0.86, size * 1.0, ACCENT)
            else:
                hp = paint(halo, a=150 * al); hp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 12))
                c.drawString(t, x, y, f, hp)
                c.drawString(t, x, y, f, paint(colr, a=255 * al))
            x += w + sp
    c.restore()


# ------------------------------------------------------------------ subtitles
SUB_SIZE, SUB_CY, SUB_MAXW = 56, 1480, 900
PAD_X, PAD_Y = 30, 20


def _w(text):
    return font(FONT_BOLD, SUB_SIZE).measureText(text)


def chunk_scene(ws):
    """split one scene's words into phrase lines of 3-5 words that fit 900 px (pill included)"""
    n = len(ws)
    INF = 1e9
    best = [INF] * (n + 1); prev = [0] * (n + 1); best[0] = 0
    for j in range(1, n + 1):
        for i in range(max(0, j - 5), j):
            line = " ".join(w["text"] for w in ws[i:j])
            if _w(line) + 2 * PAD_X > SUB_MAXW: continue
            cnt = j - i
            cost = (0 if cnt >= 3 else (3 - cnt) * 6.0) + (0 if ws[j - 1]["text"][-1] in ",.!?" or j == n else 0.8)
            cost += 0.2 * abs(cnt - 4)
            if best[i] + cost < best[j]: best[j] = best[i] + cost; prev[j] = i
    out, j = [], n
    while j > 0:
        i = prev[j]; out.append(ws[i:j]); j = i
    return out[::-1]


CHUNKS = []
for k in SC_IDS:
    CHUNKS += chunk_scene(scene_words(k))
CH_FRAME = [0 if ch[0] is TIMING[0] else word_frame(ch[0]) for ch in CHUNKS]


def wf(w):
    return 0 if w is TIMING[0] else word_frame(w)


def active_chunk(i):
    ci = None
    for j, f in enumerate(CH_FRAME):
        if i >= f: ci = j
    return ci


def sub_box(ch):
    line = " ".join(w["text"] for w in ch)
    tw = _w(line)
    h = SUB_SIZE * 1.0 + 2 * PAD_Y
    return (540 - tw / 2 - PAD_X, SUB_CY - h / 2, 540 + tw / 2 + PAD_X, SUB_CY + h / 2)


def draw_subtitle(c, i):
    ci = active_chunk(i)
    if ci is None: return None
    ch = CHUNKS[ci]
    cur = None
    for w in ch:
        if i >= wf(w): cur = w
    f = font(FONT_BOLD, SUB_SIZE)
    l, t, r, b = sub_box(ch)
    lf = i - CH_FRAME[ci]
    sc = 1.0 if ci == 0 else 0.94 + 0.06 * ease_out(clamp01(lf / 3.0))
    c.save(); c.translate(540, SUB_CY); c.scale(sc, sc); c.translate(-540, -SUB_CY)
    sh = paint("#1A2124", a=60); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(l, t + 6, r, b + 6), (b - t) / 2, (b - t) / 2), sh)
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(l, t, r, b), (b - t) / 2, (b - t) / 2), paint(CREAM, a=round(255 * 0.85)))
    x = l + PAD_X
    base_y = SUB_CY + SUB_SIZE * 0.36
    sp = f.measureText(" ")
    for w in ch:
        colr = ACCENT if w is cur else INK
        c.drawString(w["text"], x, base_y, f, paint(colr))
        x += f.measureText(w["text"]) + sp
    c.restore()
    return (l, t, r, b), (cur["text"] if cur else None)
