"""Video renderer for ep.2: animates frame_01..22 (camera crop moves) + code overlays + text.
Usage: render.py frames_dir timing.json out_video.mp4 [frame_list e.g. 0,225,735]"""
import json, sys, os, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
UP = 1.5                      # source pre-upscale factor (756x1344 -> 1134x2016)
SMIN = 1.08                   # never show the image edge
FONT_B = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FONT_XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_SB = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
AMBER = (224, 164, 88)        # #E0A458
NAME_C = (185, 195, 201)      # #B9C3C9
PLATE = (18, 22, 26, 178)     # rgba(18,22,26,0.7)
SAFE = (60, 210, 1020, 1560)  # x0, y0, x1, y1 for all text

FRAMES = None; T = None; SC = None


# ------------------------------------------------------------------ helpers
def clamp01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def lerp(a, b, t): return a + (b - a) * t
def smooth(x): x = clamp01(x); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp01(x); return 1 - (1 - x) ** 3
def ease_out_back(x, s=1.9): x = clamp01(x) - 1; return x * x * ((s + 1) * x + s) + 1
def uz(s): return s.replace("o'", "oʻ").replace("g'", "gʻ").replace("O'", "Oʻ").replace("G'", "Gʻ")


_src = {}
def src(i):
    if i not in _src:
        im = Image.open(os.path.join(FRAMES, f"frame_{i:02d}.png")).convert("RGB")
        im = im.resize((round(im.width * UP), round(im.height * UP)), Image.LANCZOS)
        _src[i] = im.filter(ImageFilter.UnsharpMask(2, 45, 2))
    return _src[i]


class Cam:
    def __init__(self, img, s, u, v):
        self.iw, self.ih = img.size
        s = max(s, SMIN); self.s = s
        u = min(max(u, 0.5 / s), 1 - 0.5 / s); v = min(max(v, 0.5 / s), 1 - 0.5 / s)
        ww = self.iw / s
        self.k = ww / W
        self.x0 = u * self.iw - ww / 2; self.y0 = v * self.ih - (self.ih / s) / 2
        self.img = img
    def render(self):
        return self.img.transform((W, H), Image.AFFINE, (self.k, 0, self.x0, 0, self.k, self.y0), resample=Image.BICUBIC)
    def xy(self, u, v): return ((u * self.iw - self.x0) / self.k, (v * self.ih - self.y0) / self.k)
    def ppu(self): return self.iw / self.k / W   # screen-width units per image-width unit (zoom)


_spr = {}
def blob(r, a, col, hard=0.0):
    """soft round sprite, radius r px, peak alpha a"""
    r = max(2, int(r)); a = round(a * 40) / 40; key = (r, a, col, hard)
    if key not in _spr:
        if a <= 0: _spr[key] = None; return None
        y, x = np.mgrid[-r:r + 1, -r:r + 1] / r
        d = np.sqrt(x * x + y * y)
        al = np.clip(1 - d, 0, 1) ** 1.6 if hard == 0 else np.clip((1 - d) / (1 - hard + 1e-6), 0, 1) ** 0.8
        arr = np.zeros(d.shape + (4,), np.uint8); arr[..., :3] = col; arr[..., 3] = (al * a * 255).astype(np.uint8)
        _spr[key] = Image.fromarray(arr, "RGBA")
    return _spr[key]


def paste(base, spr, x, y):
    if spr is None: return
    w, h = spr.size; x = int(round(x - w / 2)); y = int(round(y - h / 2))
    if x >= W or y >= H or x + w <= 0 or y + h <= 0: return
    cx0, cy0 = max(0, -x), max(0, -y); cx1, cy1 = min(w, W - x), min(h, H - y)
    if cx0 or cy0 or cx1 < w or cy1 < h: spr = spr.crop((cx0, cy0, cx1, cy1))
    base.alpha_composite(spr, dest=(x + cx0, y + cy0))


_fog = {}
def fog_tex(name):
    if name in _fog: return _fog[name]
    P = dict(  # height, colour, max alpha, edge pos, edge amp, softness, bottom fade, seed
        mist_low=(760, (206, 215, 221), 0.50, 0.32, 60, 120, False, 1),
        mist_mid=(620, (178, 192, 201), 0.30, 0.40, 50, 110, True, 2),
        mist_far=(520, (159, 176, 186), 0.26, 0.45, 40, 100, True, 3),
        mist_fast=(560, (214, 222, 227), 0.42, 0.40, 70, 110, False, 4),
        dust_low=(520, (150, 136, 118), 0.32, 0.40, 45, 110, False, 5),
        haze=(900, (196, 182, 160), 0.10, 0.25, 80, 220, True, 6),
    )[name]
    h, col, amax, edge, amp, soft, bfade, seed = P
    w = 2160; r = np.random.default_rng(seed)
    x = np.arange(w)
    ye = h * edge + sum(amp / k ** 0.7 * np.sin(2 * np.pi * k * x / w + r.uniform(0, 6.28)) for k in (1, 2, 3, 5, 8))
    yy = np.arange(h)[:, None].astype(np.float32)
    a = np.clip((yy - (ye - soft)) / (2 * soft), 0, 1); a = a * a * (3 - 2 * a)
    if bfade:
        b = np.clip((h - yy) / (h * 0.4), 0, 1); a *= b * b * (3 - 2 * b)
    n = sum(np.sin(2 * np.pi * k * x / w + r.uniform(0, 6.28))[None, :] * np.sin(yy / h * np.pi * (k % 3 + 1) + r.uniform(0, 6.28)) for k in (2, 3, 4, 6))
    a *= amax * (0.86 + 0.035 * n)
    arr = np.zeros((h, w * 2, 4), np.uint8)
    arr[..., :3] = col
    al = (np.clip(a, 0, 1) * 255).astype(np.uint8); arr[..., 3] = np.concatenate([al, al], 1)
    _fog[name] = Image.fromarray(arr, "RGBA")
    return _fog[name]


def fog_layer(base, name, y, speed, t, alpha=1.0):
    tex = fog_tex(name)
    if alpha < 0.999:
        key = (name, round(alpha, 2))
        if key not in _fog:
            t2 = tex.copy(); a = np.asarray(t2.getchannel("A"), np.float32) * alpha
            t2.putalpha(Image.fromarray(a.astype(np.uint8))); _fog[key] = t2
        tex = _fog[key]
    off = int((-speed * t) % 2160)
    crop = tex.crop((off, 0, off + W, tex.height))
    y = int(y)
    if y < 0: crop = crop.crop((0, -y, W, crop.height)); y = 0
    if y + crop.height > H: crop = crop.crop((0, 0, W, H - y))
    base.alpha_composite(crop, dest=(0, y))


def particles(base, cam, t, em):
    """steam / mist emitter attached to image space.
    em: dict(u,v, rate, life, rise (img-h/s), vx, size0, grow, alpha, col, sway, spread)"""
    rate, life = em["rate"], em["life"]
    k0 = math.floor((t - life) * rate); k1 = math.floor(t * rate)
    z = cam.ppu()
    for k in range(k0, k1 + 1):
        born = k / rate; a = t - born
        if a < 0 or a > life: continue
        r = np.random.default_rng(abs(k) * 7919 + em.get("seed", 0))
        q = a / life
        u = em["u"] + r.uniform(-1, 1) * em.get("spread", 0.01) + em.get("vx", 0) * a \
            + em.get("sway", 0.012) * math.sin(2 * math.pi * (0.35 * a + r.random())) * q
        v = em["v"] - em.get("rise", 0.05) * a
        x, y = cam.xy(u, v)
        rad = em["size0"] * (1 + em.get("grow", 1.6) * q) * z * r.uniform(0.8, 1.2)
        al = em["alpha"] * math.sin(math.pi * q) ** 1.3 * r.uniform(0.7, 1.0)
        paste(base, blob(rad, al, em.get("col", (236, 236, 232))), x, y)


def dust(base, t, n, col, seed, area=(0, 0, W, H), drift=(6, -4), size=(2, 5), amax=0.55):
    r = np.random.default_rng(seed)
    x0, y0, x1, y1 = area
    for i in range(n):
        px, py = r.uniform(x0, x1), r.uniform(y0, y1)
        sp = r.uniform(0.5, 1.5); ph = r.uniform(0, 6.28)
        x = x0 + (px - x0 + drift[0] * sp * t + 14 * math.sin(0.5 * t * sp + ph)) % max(1, x1 - x0)
        y = y0 + (py - y0 + drift[1] * sp * t + 10 * math.sin(0.37 * t * sp + ph * 1.3)) % max(1, y1 - y0)
        a = amax * (0.5 + 0.5 * math.sin(1.7 * t * sp + ph)) ** 2
        paste(base, blob(r.uniform(*size), a, col, 0.35), x, y)


def flick(t, seed=0, amt=1.0):
    return 1 + amt * (0.5 * math.sin(2 * math.pi * 7.3 * t + seed) + 0.3 * math.sin(2 * math.pi * 11.9 * t + 2 * seed)
                      + 0.2 * math.sin(2 * math.pi * 3.1 * t + 3 * seed))


# ------------------------------------------------------------------ grading
_g = {}
def grade(img, t, bright=1.0):
    if "vig" not in _g:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 * 0.8 + ((y - H / 2) / (H / 2)) ** 2)
        s = np.clip((d - 0.55) / 0.75, 0, 1)
        _g["vig"] = (1 - 0.30 * s * s * (3 - 2 * s))[..., None].astype(np.float32)
        r = np.random.default_rng(5)
        _g["grain"] = []
        for _ in range(6):   # soft 2-px film grain (half-res noise, bilinear up) - subtle and cheap to encode
            g = Image.fromarray(r.normal(0, 4.6, (H // 2, W // 2)).astype(np.float32), "F").resize((W, H), Image.BILINEAR)
            _g["grain"].append(np.asarray(g, np.float32)[..., None])
    a = np.asarray(img, np.float32)
    a = a * (_g["vig"] * bright) + _g["grain"][int(t * FPS) % 6]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


# ------------------------------------------------------------------ text
_f = {}
def font(path, size):
    if (path, size) not in _f: _f[(path, size)] = ImageFont.truetype(path, size)
    return _f[(path, size)]


def shadow_text(base, xy, txt, fnt, fill=(255, 255, 255, 255), anchor="mm", blur=10, sh_a=150, scale=1.0, alpha=1.0, boxes=None):
    if alpha <= 0.003: return
    l, t_, r, b = ImageDraw.Draw(base).textbbox(xy, txt, font=fnt, anchor=anchor)
    pad = blur * 3 + 10
    w, h = int(math.ceil(r - l)) + 2 * pad, int(math.ceil(b - t_)) + 2 * pad
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).text((pad, pad), txt, font=fnt, fill=255, anchor="lt")
    m = m.filter(ImageFilter.GaussianBlur(blur))
    sh = Image.new("RGBA", (w, h), (12, 16, 20, 0)); sh.putalpha(m.point(lambda v: int(v * sh_a / 255 * alpha)))
    lay.alpha_composite(sh, dest=(0, 4))
    d.text((pad, pad), txt, font=fnt, fill=fill[:3] + (int(fill[3] * alpha),), anchor="lt")
    if scale != 1.0:
        lay = lay.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.BICUBIC)
    cx, cy = (l + r) / 2, (t_ + b) / 2
    paste(base, lay, cx, cy)
    if boxes is not None: boxes.append((cx - (r - l) * scale / 2, cy - (b - t_) * scale / 2, cx + (r - l) * scale / 2, cy + (b - t_) * scale / 2))


SUB_SIZE, SUB_MAXW, SUB_BOTTOM = 60, 820, 1500
def best_split(disp, f, sp):
    """fewest display lines that fit SUB_MAXW; among those, balanced widths and breaks after punctuation"""
    import itertools
    n = len(disp); wl = [f.getlength(d) for d in disp]
    def width(a, b): return sum(wl[a:b]) + sp * (b - a - 1)
    for k in range(1, n + 1):
        best = None
        for cuts in itertools.combinations(range(1, n), k - 1):
            b = (0,) + cuts + (n,)
            ws = [width(b[i], b[i + 1]) for i in range(k)]
            if max(ws) > SUB_MAXW: continue
            cost = max(ws) - min(ws) + sum(0 if disp[c - 1][-1] in ",.!?—" else 260 for c in cuts)
            if best is None or cost < best[0]: best = (cost, b)
        if best: b = best[1]; return [list(range(b[i], b[i + 1])) for i in range(len(b) - 1)]
    return [[i] for i in range(n)]

_chunks = None
def sub_chunks():
    global _chunks
    if _chunks is not None: return _chunks
    from data import VOICE_LINES
    f = font(FONT_B, SUB_SIZE); sp = f.getlength(" ")
    _chunks = []
    for lid, spk, txt in VOICE_LINES:
        ws = [w for w in T["words"] if w["line"] == lid]
        toks = [uz(x) for x in txt.split()]
        # attach non-word tokens (the em dash) to the previous word's display text
        disp = []
        for tk in toks:
            if any(c.isalpha() for c in tk): disp.append(tk)
            else: disp[-1] += " " + tk
        assert len(disp) == len(ws), (disp, [w["text"] for w in ws])
        groups = best_split(disp, f, sp)
        for g in groups:
            words = [dict(text=disp[k], t0=ws[k]["t0"], t1=ws[k]["t1"], w=f.getlength(disp[k])) for k in g]
            _chunks.append(dict(line=lid, spk=spk, words=words, t0=words[0]["t0"], t1=words[-1]["t1"]))
    # end time of each chunk: next chunk start, or last word + 0.45 s
    for i, c in enumerate(_chunks):
        nxt = _chunks[i + 1]["t0"] if i + 1 < len(_chunks) else 1e9
        c["end"] = min(nxt, c["t1"] + 0.45) if (i + 1 < len(_chunks) and _chunks[i + 1]["line"] == c["line"]) else min(nxt, c["t1"] + 0.55)
        if i + 1 < len(_chunks) and _chunks[i + 1]["line"] == c["line"]: c["end"] = nxt
    return _chunks


def fidx(t): return int(math.floor(t * FPS + 0.5))


def draw_subs(base, n, boxes):
    f = font(FONT_B, SUB_SIZE); fn = font(FONT_SB, 30); sp = f.getlength(" ")
    for c in sub_chunks():
        if not (fidx(c["t0"]) <= n < fidx(c["end"])): continue
        t = n / FPS
        out_a = clamp01((c["end"] - t) / 0.15) if c["end"] - c["t1"] > 0.2 else 1.0
        tw = sum(w["w"] for w in c["words"]) + sp * (len(c["words"]) - 1)
        name = "" if c["spk"] == "HIKOYACHI" else c["spk"].upper()
        padx, pady = 34, 22
        line_h = 74; name_h = 40 if name else 0
        pw = max(tw, fn.getlength(name) if name else 0) + 2 * padx; ph = line_h + name_h + 2 * pady
        px0 = 540 - pw / 2; py0 = SUB_BOTTOM - ph
        rise = 8 * (1 - ease_out((n - fidx(c["t0"])) / 5)) if c["words"][0]["t0"] == c["t0"] else 0
        lay = Image.new("RGBA", (int(pw) + 2, int(ph) + 2), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.rounded_rectangle((0, 0, pw, ph), radius=26, fill=PLATE[:3] + (int(PLATE[3] * out_a),))
        if name:
            d.text((pw / 2, pady + 14), name, font=fn, fill=NAME_C + (int(255 * out_a),), anchor="mm")
        x = pw / 2 - tw / 2; y = pady + name_h + line_h / 2
        # current word = last word whose start has been reached (kept until the next word starts)
        started = [k for k, w in enumerate(c["words"]) if n >= fidx(w["t0"])]
        cur = started[-1] if started else -1
        if cur == len(c["words"]) - 1 and t > c["words"][cur]["t1"] + 0.15: cur = -1
        for k, w in enumerate(c["words"]):
            if n >= fidx(w["t0"]):
                col = AMBER if k == cur else (255, 255, 255)
                d.text((x, y), w["text"], font=f, fill=col + (int(255 * out_a),), anchor="lm")
            x += w["w"] + sp
        base.alpha_composite(lay, dest=(int(px0), int(py0 + rise)))
        boxes.append((px0, py0 + rise, px0 + pw, py0 + rise + ph))


def draw_cta(base, t, boxes):
    obuna = [w for w in T["words"] if w["line"] == 8 and w["text"].lower().startswith("obuna")][0]["t0"]
    n = fidx(t)
    if n < fidx(obuna): return
    p = (n - fidx(obuna)) / FPS
    sc = 0.55 + 0.45 * ease_out_back(p / 0.38)
    bw, bh = 330, 104
    lay = Image.new("RGBA", (bw + 60, bh + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sh = Image.new("L", lay.size, 0); ImageDraw.Draw(sh).rounded_rectangle((30, 36, 30 + bw, 36 + bh), 52, fill=120)
    sh = sh.filter(ImageFilter.GaussianBlur(10)); shi = Image.new("RGBA", lay.size, (10, 12, 14, 0)); shi.putalpha(sh)
    lay.alpha_composite(shi)
    d.rounded_rectangle((30, 30, 30 + bw, 30 + bh), 52, fill=AMBER + (255,))
    fo = font(FONT_XB, 50)
    tw = fo.getlength("Obuna"); pl = 44; gap = 22; total = pl + gap + tw
    x0 = 30 + bw / 2 - total / 2; cy = 30 + bh / 2
    d.rounded_rectangle((x0, cy - 5, x0 + pl, cy + 5), 3, fill=(255, 255, 255, 255))
    d.rounded_rectangle((x0 + pl / 2 - 5, cy - pl / 2, x0 + pl / 2 + 5, cy + pl / 2), 3, fill=(255, 255, 255, 255))
    d.text((x0 + pl + gap, cy + 2), "Obuna", font=fo, fill=(255, 255, 255, 255), anchor="lm")
    lay = lay.resize((int(lay.width * sc), int(lay.height * sc)), Image.BICUBIC)
    cx, cy2 = 540, 905
    paste(base, lay, cx, cy2)
    boxes.append((cx - bw * sc / 2, cy2 - bh * sc / 2, cx + bw * sc / 2, cy2 + bh * sc / 2))


# ------------------------------------------------------------------ scenes
def scene_at(n):
    for s in SC:
        if fidx(s["start"]) <= n < fidx(s["end"]): return s
    return SC[-1]


def cam_for(sid, tl, d, img):
    """returns Cam for scene id at local time tl (0..d)"""
    p = clamp01(tl / d)
    if sid == 1: return Cam(img, lerp(1.08, 1.16, tl / d), 0.5, 0.60)
    if sid == 2:
        bob = sum(0.006 * math.exp(-((tl - st - 0.06) / 0.09) ** 2) for st in (0.28, 1.05))
        return Cam(img, lerp(1.10, 1.20, p), lerp(0.52, 0.50, p), lerp(0.60, 0.66, p) + bob)
    if sid == 3:
        whip = 0.11 * (1 - ease_out(tl / 0.2))
        sway_u = 0.004 * math.sin(2 * math.pi * 0.7 * tl) + 0.002 * math.sin(2 * math.pi * 1.4 * tl + 1)
        sway_v = 0.003 * math.sin(2 * math.pi * 0.9 * tl + 2)
        return Cam(img, lerp(1.14, 1.17, p), 0.47 + whip + sway_u, 0.48 + sway_v)
    if sid == 4: return Cam(img, 1.08 + 0.10 * ease_out(tl / 0.9) + 0.02 * p, 0.47, 0.42)
    if sid == 5: return Cam(img, 1.15, lerp(0.42, 0.58, p), 0.52)
    if sid == 6: return Cam(img, lerp(1.35, 1.42, p), 0.5, 0.42)
    if sid == 7: return Cam(img, lerp(1.18, 1.22, p), lerp(0.40, 0.60, smooth(p * 0.9 + 0.05)), 0.50)
    if sid == 8: return Cam(img, 1.08 + 0.12 * ease_out(tl / 0.15) + 0.04 * p, lerp(0.45, 0.47, p), 0.42)
    if sid == 9: return Cam(img, lerp(1.10, 1.20, p), 0.58, 0.55)
    if sid == 10: return Cam(img, lerp(1.10, 1.25, p), 0.52, 0.52)
    if sid == 11: return Cam(img, lerp(1.10, 1.18, p), 0.5, 0.42)
    if sid == 12: return Cam(img, lerp(1.10, 1.135, p), 0.5, 0.45)
    if sid == 13: return Cam(img, 1.25, lerp(0.40, 0.60, smooth(p)), 0.50)
    if sid == 14: return Cam(img, lerp(1.08, 1.16, p), 0.5, lerp(0.62, 0.60, p))
    if sid == 15: return Cam(img, lerp(1.60, 1.72, p), lerp(0.40, 0.39, p), lerp(0.49, 0.47, p))
    if sid == 16: return Cam(img, lerp(1.10, 1.22, p), lerp(0.62, 0.70, p), lerp(0.52, 0.47, p))
    if sid == 18: return Cam(img, lerp(1.10, 1.22, p), 0.5, lerp(0.48, 0.45, p))
    if sid == 19: return Cam(img, lerp(1.12, 1.30, p), 0.5, 0.42)
    if sid == 20:
        sh = math.exp(-tl / 0.12) * (tl < 0.4)
        du = 0.016 * sh * math.sin(2 * math.pi * 23 * tl); dv = 0.012 * sh * math.sin(2 * math.pi * 17 * tl + 1)
        s = lerp(1.26, 1.10, ease_out((tl - 0.35) / 0.8)) - 0.01 * p
        return Cam(img, s, 0.45 + du, 0.58 + dv)
    if sid == 21: return Cam(img, lerp(1.12, 1.22, p), lerp(0.42, 0.52, p), lerp(0.55, 0.52, p))
    if sid == 22: return Cam(img, lerp(1.10, 1.18, p), 0.47, 0.48)
    if sid == 23: return Cam(img, lerp(1.10, 1.35, p), lerp(0.55, 0.59, p), lerp(0.52, 0.50, p))
    if sid == 24: return Cam(img, lerp(1.08, 1.16, p), 0.5, 0.60)
    raise ValueError(sid)


STEAM = dict(col=(238, 236, 230), rate=5.0, life=2.6, rise=0.06, size0=0.022, grow=2.2, alpha=0.16, sway=0.018, spread=0.012)
def emit(**kw):
    e = dict(STEAM); e.update(kw); return e


def overlays(base, sid, tl, d, t, cam):
    if sid in (1, 24):
        fog_layer(base, "mist_far", 820, -26, t, 0.9)
        fog_layer(base, "mist_mid", 1060, -48, t)
        fog_layer(base, "mist_low", 1260, -90, t)
        dust(base, t, 18, (225, 232, 236), 1, (0, 300, W, 1700), (-12, -3), (2, 4), 0.35)
    elif sid == 2:
        fog_layer(base, "mist_mid", 980, -60, t, 0.8)
        fog_layer(base, "mist_fast", 1380, -170, t)
    elif sid in (3, 4):
        dust(base, t, 22, (236, 226, 205), sid, (100, 200, 1000, 1400), (5, -3), (2, 4), 0.45)
    elif sid == 5:
        dust(base, t, 26, (240, 236, 222), 5, (300, 150, 1000, 1100), (4, 5), (2, 4), 0.5)
    elif sid == 6:
        dust(base, t, 14, (240, 232, 214), 6, (100, 150, 1000, 1200), (3, -2), (2, 4), 0.35)
    elif sid == 7:
        fog_layer(base, "mist_far", 380, -20, t, 0.7)
        particles(base, cam, tl, emit(u=0.72, v=0.47, seed=7))
        particles(base, cam, tl, emit(u=0.64, v=0.38, seed=8, alpha=0.10, rate=3))
    elif sid == 8:
        fog_layer(base, "mist_far", 300, -20, t, 0.6)
        particles(base, cam, tl, emit(u=0.50, v=0.40, seed=9, alpha=0.12))
    elif sid == 9:
        particles(base, cam, tl, emit(u=0.585, v=0.515, seed=10, size0=0.018, alpha=0.18, rise=0.05, life=2.2, rate=6))
        g = 0.20 * flick(t, 1, 0.12); x, y = cam.xy(0.34, 0.25)
        paste(base, blob(150 * cam.ppu(), g, (255, 196, 120)), x, y)
        dust(base, t, 14, (240, 214, 170), 9, (0, 150, W, 1300), (4, -2), (2, 4), 0.4)
    elif sid == 10:
        particles(base, cam, tl, emit(u=0.56, v=0.66, seed=11, size0=0.020, alpha=0.17, rise=0.05, life=2.2, rate=6))
        dust(base, t, 12, (240, 214, 170), 10, (0, 150, W, 1300), (4, -2), (2, 4), 0.35)
    elif sid == 11:
        for k, (u, v) in enumerate(((0.30, 0.12), (0.38, 0.22))):
            g = 0.22 * flick(t, 2 + k, 0.14); x, y = cam.xy(u, v)
            paste(base, blob(120 * cam.ppu(), g, (255, 196, 120)), x, y)
        particles(base, cam, tl, emit(u=0.49, v=0.615, seed=12, size0=0.012, alpha=0.13, rise=0.04, life=1.8, rate=5))
    elif sid == 12:
        x, y = cam.xy(0.5, 0.36)
        paste(base, blob(420, 0.10 * flick(t, 4, 0.35), (255, 190, 120)), x, y)
        dust(base, t, 10, (236, 222, 196), 12, (100, 100, 1000, 1300), (2, -2), (2, 3), 0.3)
    elif sid == 13:
        dust(base, t, 16, (240, 230, 210), 13, (0, 200, W, 1500), (5, -2), (2, 4), 0.4)
    elif sid == 14:
        fog_layer(base, "dust_low", 1180, -55, t, 0.9)
        dust(base, t, 30, (190, 176, 156), 14, (0, 700, W, 1800), (-25, -6), (2, 6), 0.45)
    elif sid == 15:
        fog_layer(base, "dust_low", 1300, -45, t, 0.7)
        fog_layer(base, "mist_far", 500, -20, t, 0.6)
        dust(base, t, 18, (190, 176, 156), 15, (0, 300, W, 1800), (-18, -4), (3, 7), 0.4)
    elif sid == 16:
        particles(base, cam, tl, emit(u=0.70, v=0.62, seed=16, col=(200, 210, 216), rate=3.0, life=3.2, rise=0.03,
                                      vx=-0.02, size0=0.06, grow=1.2, alpha=0.20, spread=0.10, sway=0.03))
        dust(base, t, 14, (220, 220, 214), 16, (500, 300, 1000, 1500), (-6, 2), (2, 4), 0.35)
    elif sid == 18:
        fog_layer(base, "haze", 500, -12, t, 1.0)
        dust(base, t, 30, (246, 236, 214), 18, (300, 200, 1050, 1500), (-5, 3), (2, 5), 0.55)
    elif sid == 19:
        x, y = cam.xy(0.5, 0.42)
        paste(base, blob(520, 0.07 * flick(t, 5, 0.6), (255, 200, 140)), x, y)
    elif sid == 20:
        fog_layer(base, "mist_far", 760, -40, t, 0.7)
        fog_layer(base, "dust_low", 1150, -80, t, 0.6)
        if tl > 0.08:   # dust burst from the impact point
            x0, y0 = cam.xy(0.36, 0.46)
            r = np.random.default_rng(20)
            for k in range(46):
                ang = r.uniform(-math.pi, 0.4); sp = r.uniform(150, 620); a = tl - 0.08 - r.uniform(0, 0.15)
                if a <= 0: continue
                dist = sp * (1 - math.exp(-a / 0.35)) * 0.35
                x = x0 + math.cos(ang) * dist; y = y0 + math.sin(ang) * dist + 40 * a * a
                al = 0.55 * math.exp(-a / 0.8)
                paste(base, blob(r.uniform(3, 11) * (1 + a), al, (176, 160, 138), 0.3), x, y)
    elif sid == 21:
        fog_layer(base, "mist_far", 700, -60, t, 0.8)
        fog_layer(base, "mist_mid", 1000, -130, t, 0.9)
        fog_layer(base, "mist_fast", 1350, -240, t, 0.9)
    elif sid == 22:
        dust(base, t, 10, (226, 220, 206), 22, (100, 100, 1000, 1700), (3, -2), (2, 4), 0.3)
    elif sid == 23:
        fog_layer(base, "haze", 300, -10, t, 0.8)
        dust(base, t, 16, (226, 222, 214), 23, (0, 200, W, 1600), (-4, 2), (2, 4), 0.4)


def frame(n):
    t = n / FPS
    s = scene_at(n); sid = s["id"]; tl = t - s["start"]; d = s["end"] - s["start"]
    boxes = []
    if s["frame"] is None:
        img = Image.new("RGB", (W, H), (0, 0, 0))
        base = img.convert("RGBA")
    else:
        sim = src(s["frame"])
        sub = []
        if sid == 3 and tl < 0.2: sub = [tl - k / FPS / 6 for k in range(6)]
        if sid == 8 and tl < 0.17: sub = [tl - k / FPS / 6 for k in range(6)]
        if sub:
            acc = sum(np.asarray(cam_for(sid, max(0, x), d, sim).render(), np.float32) for x in sub) / len(sub)
            img = Image.fromarray(acc.astype(np.uint8))
        else:
            img = cam_for(sid, tl, d, sim).render()
        cam = cam_for(sid, tl, d, sim)
        if sid == 22:
            rad = 14 * (1 - ease_out(tl / 0.9))
            if rad > 0.3: img = img.filter(ImageFilter.GaussianBlur(rad))
        base = img.convert("RGBA")
        overlays(base, sid, tl, d, t, cam)
    bright = 1.0
    if sid == 12: bright = flick(t, 7, 0.015)
    if sid == 19: bright = flick(t, 8, 0.02)
    if sid == 9 or sid == 11: bright = flick(t, 9, 0.008)
    out = grade(base.convert("RGB"), t, bright).convert("RGBA")
    # ---- text
    if t < 3.6:
        a = clamp01((3.6 - t) / 0.15)
        sc = 1.0 + 0.05 * (1 - ease_out(t / 0.6))
        shadow_text(out, (540, 470), "Bu qiz kim?", font(FONT_XB, 116), blur=14, sh_a=170, scale=sc, alpha=a, boxes=boxes)
    if s.get("tag"):
        p = tl - 0.1
        if 0 <= p <= 1.6:
            a = 0.7 * min(clamp01(p / 0.35), clamp01((1.6 - p) / 0.35))
            ft = font(FONT_SB, 40)
            ImageDraw.Draw(out)
            bar = Image.new("RGBA", (4, 40), AMBER + (int(255 * a / 0.7 * 0.9),)); out.alpha_composite(bar, dest=(96, 262))
            shadow_text(out, (116, 282), s["tag"], ft, fill=(255, 255, 255, 255), anchor="lm", blur=6, sh_a=120, alpha=a, boxes=boxes)
    if sid == 24:
        dav = [w for w in T["words"] if w["line"] == 8][0]["t0"]
        if n >= fidx(dav):
            p = (n - fidx(dav)) / FPS
            a = min(1.0, 0.55 + p / 0.12)
            shadow_text(out, (540, 760 + 10 * (1 - ease_out(p / 0.3))), "Davomi bor", font(FONT_XB, 104), blur=14, sh_a=170, alpha=a, boxes=boxes)
        draw_cta(out, t, boxes)
    draw_subs(out, n, boxes)
    return out.convert("RGB"), boxes


def init(frames_dir, timing):
    global FRAMES, T, SC
    FRAMES = frames_dir; T = json.load(open(timing)); SC = T["scenes"]


def _work(n):
    im, boxes = frame(n)
    return n, im.tobytes(), boxes


def main(frames_dir, timing, out, only=None):
    init(frames_dir, timing)
    total = int(round(T["duration"] * FPS))
    if only:
        os.makedirs(out, exist_ok=True)
        for n in only:
            im, b = frame(n); im.save(os.path.join(out, f"f{n:05d}.png")); print(n, b)
        return
    from multiprocessing import Pool
    ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "22",
                           "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    allboxes = {}
    with Pool(4, initializer=init, initargs=(frames_dir, timing)) as pool:
        for n, buf, boxes in pool.imap(_work, range(total), chunksize=6):
            ff.stdin.write(buf); allboxes[n] = boxes
            if n % 150 == 0: print("frame", n, "/", total, flush=True)
    ff.stdin.close(); ff.wait()
    json.dump(allboxes, open(os.path.splitext(out)[0] + "_textboxes.json", "w"))
    print("done", total, "frames")


if __name__ == "__main__":
    only = [int(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 else None
    main(sys.argv[1], sys.argv[2], sys.argv[3], only)
