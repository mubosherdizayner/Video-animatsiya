# Props and backgrounds drawn in code, outlined flat style matching the character sheets.
import math, random, functools, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
from lib import *


# ---------------------------------------------------------------- ikat helpers
def ikatify(alpha, amp=6, band=3, seed=0, blur=1.4):
    """horizontal jagged feathering typical of ikat (abr) weaving; alpha is float array HxW"""
    rnd = np.random.RandomState(seed)
    out = np.zeros_like(alpha)
    h = alpha.shape[0]
    sh = 0
    for y in range(h):
        if y % band == 0: sh = rnd.randint(-amp, amp + 1)
        out[y] = np.roll(alpha[y], sh)
    im = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(blur))
    return np.asarray(im).astype(np.float32) / 255


def motif_layer(w, h, period_x=300, period_y=380, seed=3):
    """gold ikat motifs (almond / diamond with hooks) as alpha array, tileable horizontally with period_x"""
    c = SS(w, h, 1)
    for j, y in enumerate(range(-period_y, h + period_y, period_y // 2)):
        off = (period_x // 2) * (j % 2)
        for x in range(-period_x + off, w + period_x, period_x):
            cx, cy = x, y
            kind = (j % 4)
            if kind in (0, 2):
                # almond with inner diamond and side hooks
                pts = [(cx, cy - 120), (cx + 56, cy - 30), (cx + 40, cy + 60), (cx, cy + 112), (cx - 40, cy + 60), (cx - 56, cy - 30)]
                c.poly(pts, fill=None, outline=(255, 255, 255, 255), width=15)
                c.poly([(cx, cy - 46), (cx + 22, cy), (cx, cy + 46), (cx - 22, cy)], fill=(255, 255, 255, 255), outline=None, width=0)
                for sgn in (-1, 1):
                    c.arc((cx + sgn * 64 - 26, cy - 40, cx + sgn * 64 + 26, cy + 12), 0, 360, fill=(255, 255, 255, 255), width=9)
            else:
                # small flame / comb motif
                for k in range(3):
                    yy = cy - 50 + k * 50
                    c.poly([(cx - 34, yy), (cx, yy - 26), (cx + 34, yy), (cx, yy + 26)], fill=None, outline=(255, 255, 255, 255), width=9)
    a = np.asarray(c.result().getchannel("A")).astype(np.float32) / 255
    return ikatify(a, amp=7, band=3, seed=seed, blur=1.6)


def vgrad(w, h, stops):
    """vertical gradient from list of (pos 0..1, rgb)"""
    ys = np.linspace(0, 1, h)
    out = np.zeros((h, 3), np.float32)
    for c in range(3):
        out[:, c] = np.interp(ys, [s[0] for s in stops], [s[1][c] for s in stops])
    return np.repeat(out[:, None, :], w, axis=1)


def radial(w, h, cx, cy, r, power=1.6):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    return np.clip(1 - d, 0, 1) ** power


@functools.lru_cache(maxsize=4)
def bg_parts(kind="teal"):
    """(static base RGB float array of world size, motif alpha wide (tileable), vignette alpha)"""
    w, h = WW, WH
    if kind == "teal":
        base = vgrad(w, h, [(0, TEAL_TOP), (0.45, TEAL_MID), (0.62, (14, 84, 90)), (1, TEAL_BOT)])
        g = radial(w, h, M + 540, M + 820, 820)[..., None]
        base = base * (1 - 0.45 * g) + np.array([46, 150, 146], np.float32) * 0.45 * g
    else:
        raise ValueError(kind)
    mot = motif_layer(w + 300, h)
    vig = 1 - radial(w, h, M + 540, M + 900, 1250, 0.9)
    return base, mot, vig


def make_bg(kind="teal", scroll=0.0, motif_alpha=0.15):
    base, mot, vig = bg_parts(kind)
    w, h = WW, WH
    off = int(round(scroll)) % 300
    m = mot[:, off:off + w]
    gold = np.array([226, 178, 70], np.float32)
    out = base * (1 - motif_alpha * m[..., None]) + gold * motif_alpha * m[..., None]
    out = out * (1 - 0.55 * vig[..., None] ** 1.5)
    # floor below the table: darker
    fl = np.clip((np.arange(h) - (M + TABLE_BOTTOM - 40)) / 120, 0, 1)[:, None, None]
    out = out * (1 - 0.35 * fl)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


# ---------------------------------------------------------------- dasturxon (red-white atlas tablecloth on a low table)
def atlas_pattern(w, h, period=116, seed=5, yscale=1.0, phase=0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rnd = np.random.RandomState(seed)
    jit = np.repeat(rnd.randint(-5, 6, size=h // 3 + 2), 3)[:h].astype(np.float32)[:, None]
    xl = ((xx + phase + jit) % period) - period / 2
    yv = yy / yscale
    hw = 16 + 20 * np.abs(np.sin(yv * math.pi / 46))           # zigzag diamonds (flames)
    white = np.abs(xl) < hw
    edge = (np.abs(xl) < hw + 6) & ~white
    xl2 = ((xx + phase + period / 2 + jit * 0.6) % period) - period / 2
    hw2 = 5 + 6 * np.abs(np.sin(yv * math.pi / 23 + 1.0))
    small = np.abs(xl2) < hw2
    stripe = np.abs(np.abs(xl2) - 13) < 2.2
    col = np.zeros((h, w, 3), np.float32) + np.array(RED, np.float32)
    col[stripe] = (150, 16, 30)
    col[small] = (250, 238, 226)
    col[edge] = (244, 186, 70)
    col[white] = (252, 246, 238)
    # inner red dot in each white diamond
    dot = (np.abs(xl) < 5 + 4 * np.abs(np.sin(yv * math.pi / 46))) & white
    col[dot] = (210, 40, 54)
    return col


@functools.lru_cache(maxsize=4)
def table_img(width=WW, phase=0):
    """low table covered with the dasturxon; image covers y from TABLE_TOP-6 to TABLE_BOTTOM+30 (world)"""
    y0 = TABLE_TOP - 6
    h = TABLE_BOTTOM + 34 - y0
    top_h = TABLE_FRONT - TABLE_TOP
    front_h = TABLE_BOTTOM - TABLE_FRONT
    im = np.zeros((h, width, 4), np.float32)
    # top surface (compressed pattern, darker toward the back)
    tp = atlas_pattern(width, top_h, yscale=0.32, phase=phase)
    sh = np.linspace(0.78, 1.0, top_h)[:, None, None]
    im[6:6 + top_h, :, :3] = tp * sh
    im[6:6 + top_h, :, 3] = 255
    # front drape
    fp = atlas_pattern(width, front_h, phase=phase + 30)
    sh = np.linspace(0.92, 0.7, front_h)[:, None, None]
    im[6 + top_h:6 + top_h + front_h, :, :3] = fp * sh
    im[6 + top_h:6 + top_h + front_h, :, 3] = 255
    out = Image.fromarray(np.clip(im, 0, 255).astype(np.uint8), "RGBA")
    c = SS(width, h, 2)
    # gold trim near the bottom of the drape
    yb = 6 + top_h + front_h
    c.rect((-10, yb - 26, width + 10, yb), fill=GOLD, outline=OL, width=5)
    for x in range(-20, width + 40, 40):
        c.poly([(x, yb - 13), (x + 10, yb - 21), (x + 20, yb - 13), (x + 10, yb - 5)], fill=RED_D, outline=None, width=0)
    # tassels
    for k, x in enumerate(range(10, width, 46)):
        col = RED if k % 2 else GOLD
        c.poly([(x - 9, yb - 2), (x + 9, yb - 2), (x + 4, yb + 22), (x - 4, yb + 22)], fill=col, outline=OL, width=3.5)
        c.circle(x, yb + 4, 5, fill=GOLD_D, outline=None, width=0)
    # edges
    c.line([(-10, 6), (width + 10, 6)], fill=OL, width=6, round_caps=False)
    c.line([(-10, 6 + top_h), (width + 10, 6 + top_h)], fill=OL, width=8, round_caps=False)
    c.line([(-10, 6 + top_h + 4), (width + 10, 6 + top_h + 4)], fill=(255, 255, 255, 70), width=3, round_caps=False)
    deco = c.result()
    out.alpha_composite(deco)
    return out, y0


def table_shadow(width=WW):
    s = Image.new("RGBA", (width, 120), (0, 0, 0, 0))
    m = Image.new("L", s.size, 0)
    ImageDraw.Draw(m).rectangle((0, 20, width, 70), fill=120)
    s.putalpha(m.filter(ImageFilter.GaussianBlur(18)))
    return s


def draw_table(world, xoff=0, alpha=1.0):
    width = WW + 240
    phase = int(round(-xoff)) % 116
    img, y0 = table_img(width, phase)
    sh = table_shadow(WW)
    paste(world, sh, 0, M + TABLE_BOTTOM - 10)
    t = img.crop((0, 0, WW, img.height))
    if alpha < 1: t = with_alpha(t, alpha)
    paste(world, t, 0, M + y0)


# ---------------------------------------------------------------- lagan + osh
def _mound_mask(w, h, cx, cy, rxm, rym, mh, expo=0.6):
    pts = []
    n = 60
    for i in range(n + 1):
        x = -rxm + 2 * rxm * i / n
        u = max(0.0, 1 - (x / rxm) ** 2)
        pts.append((cx + x, cy - mh * u ** expo))
    pts += ell_pts(cx, cy, rxm, rym, 0, 180, 40)[::-1][::-1]
    return pts


def _grain(c, x, y, L, wdt, ang, col):
    dx, dy = math.cos(ang) * L / 2, math.sin(ang) * L / 2
    c.line([(x - dx, y - dy), (x + dx, y + dy)], fill=col, width=wdt)


def osh_pieces(seed, n_carrot=26, n_meat=7, n_pea=9):
    rnd = random.Random(seed)
    P = []
    for _ in range(n_carrot):
        P.append(dict(kind="carrot", az=rnd.uniform(0, 2 * math.pi), r=rnd.uniform(0.05, 0.85) ** 0.8,
                      ang=rnd.uniform(-0.9, 0.9), L=rnd.uniform(0.085, 0.13), Wd=rnd.uniform(0.018, 0.026)))
    for _ in range(n_meat):
        P.append(dict(kind="meat", az=rnd.uniform(0, 2 * math.pi), r=rnd.uniform(0.0, 0.55),
                      ang=rnd.uniform(-0.6, 0.6), L=rnd.uniform(0.075, 0.1), Wd=rnd.uniform(0.05, 0.065)))
    for _ in range(n_pea):
        P.append(dict(kind="pea", az=rnd.uniform(0, 2 * math.pi), r=rnd.uniform(0.1, 0.85), ang=0, L=0.025, Wd=0.025))
    return P


def draw_pieces(c, w, cx, cy, rxm, rym, mh, pieces, rot=0.0, expo=0.6, only=None):
    vis = []
    for p in pieces:
        if only and p["kind"] not in only: continue
        a = p["az"] + rot
        r = p["r"]
        x = cx + rxm * r * math.cos(a)
        depth = math.sin(a)           # +1 front, -1 back
        u = max(0.0, 1 - r * r)
        y = cy - mh * u ** expo + rym * r * depth * 0.9
        if depth < -0.35 and r > 0.45: continue
        vis.append((depth * r, x, y, p))
    vis.sort(key=lambda v: v[0])
    for _, x, y, p in vis:
        L, Wd = p["L"] * w, p["Wd"] * w
        if p["kind"] == "carrot":
            ang = p["ang"] + 0.5 * math.cos(p["az"] + rot)
            dx, dy = math.cos(ang) * L / 2, math.sin(ang) * L / 2
            c.line([(x - dx, y - dy), (x + dx, y + dy)], fill=OL, width=Wd + 4)
            c.line([(x - dx, y - dy), (x + dx, y + dy)], fill=CARROT, width=Wd)
            c.line([(x - dx * 0.7, y - dy * 0.7 - Wd * 0.18), (x + dx * 0.5, y + dy * 0.5 - Wd * 0.18)], fill=(255, 176, 90), width=max(1.5, Wd * 0.28))
        elif p["kind"] == "meat":
            pts = [(x + L / 2 * math.cos(t) * (1 + 0.12 * math.sin(3 * t + p["az"])), y + Wd / 2 * math.sin(t) * (1 + 0.1 * math.cos(2 * t)))
                   for t in np.linspace(0, 2 * math.pi, 22)]
            c.poly(pts, fill=MEAT, outline=OL, width=3.5)
            c.ellipse((x - L * 0.3, y - Wd * 0.38, x + L * 0.05, y - Wd * 0.05), fill=MEAT_L, outline=None, width=0)
        else:
            c.circle(x, y, L / 2, fill=(246, 222, 150), outline=OL, width=2.5)


def plate(c, w, cx, cy, deco_seed=0, inner=True):
    rx, ry = w / 2, w * 0.16
    # foot + side thickness
    c.ellipse((cx - rx * 0.5, cy + ry * 0.5, cx + rx * 0.5, cy + ry * 1.25), fill=(214, 222, 236), outline=OL, width=4.5)
    c.ellipse((cx - rx, cy - ry + w * 0.032, cx + rx, cy + ry + w * 0.032), fill=(196, 208, 228), outline=OL, width=5)
    c.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(250, 251, 253), outline=OL, width=5)
    # blue rim pattern
    c.ellipse((cx - rx * 0.965, cy - ry * 0.955, cx + rx * 0.965, cy + ry * 0.955), fill=None, outline=COBALT, width=max(2, w * 0.008))
    n = 18
    for i in range(n):
        a = 2 * math.pi * i / n
        px, py = cx + rx * 0.885 * math.cos(a), cy + ry * 0.885 * math.sin(a)
        if i % 2 == 0:
            s = w * 0.03
            pts = [(px + s * math.cos(a + k * math.pi / 2) * (1.0 if k % 2 == 0 else 0.55), py + s * 0.45 * math.sin(a + k * math.pi / 2) * (1.0 if k % 2 == 0 else 0.55)) for k in range(4)]
            c.poly(pts, fill=COBALT, outline=None, width=0)
        else:
            c.ellipse((px - w * 0.011, py - w * 0.006, px + w * 0.011, py + w * 0.006), fill=COBALT, outline=None, width=0)
    c.ellipse((cx - rx * 0.79, cy - ry * 0.79, cx + rx * 0.79, cy + ry * 0.79), fill=(238, 242, 250) if inner else None, outline=COBALT, width=max(2, w * 0.008))
    if inner:
        # centre medallion (visible on empty plates)
        c.ellipse((cx - rx * 0.3, cy - ry * 0.3, cx + rx * 0.3, cy + ry * 0.3), fill=None, outline=COBALT, width=max(2, w * 0.01))
        for i in range(8):
            a = 2 * math.pi * i / 8
            px, py = cx + rx * 0.5 * math.cos(a), cy + ry * 0.5 * math.sin(a)
            c.ellipse((px - w * 0.02, py - w * 0.01, px + w * 0.02, py + w * 0.01), fill=(70, 110, 200), outline=None, width=0)
        c.ellipse((cx - rx * 0.1, cy - ry * 0.1, cx + rx * 0.1, cy + ry * 0.1), fill=COBALT, outline=None, width=0)


def mound(c, w, cx, cy, kind="mixed", seed=1, rot=0.0, mh_mul=1.0, pieces=None, toppings=True):
    rx, ry = w / 2, w * 0.16
    rxm, rym = rx * 0.72, ry * 0.72
    mh = w * 0.22 * mh_mul
    base_col, dark, light = RICE, RICE_D, RICE_L
    if kind == "devzira":
        base_col, dark, light = (224, 158, 104), (186, 104, 66), (250, 206, 158)
    # rice dome on its own layer, clipped
    lw, lh = int(c.w), int(c.h)
    layer = SS(lw, lh, c.ss)
    pts = _mound_mask(lw, lh, cx, cy, rxm, rym, mh)
    layer.poly(pts, fill=base_col, outline=None, width=0)
    layer.ellipse((cx + rxm * 0.05, cy - mh * 0.9, cx + rxm * 1.25, cy + rym * 1.3), fill=dark, outline=None, width=0)
    layer.ellipse((cx - rxm * 0.85, cy - mh * 1.0, cx - rxm * 0.05, cy - mh * 0.35), fill=light, outline=None, width=0)
    rnd = random.Random(seed)
    ng = int(w * 1.1)
    for _ in range(ng):
        x = cx + rnd.uniform(-rxm, rxm)
        u = max(0.0, 1 - ((x - cx) / rxm) ** 2)
        ytop = cy - mh * u ** 0.6
        y = rnd.uniform(ytop, cy + rym * math.sqrt(u))
        L = w * (0.05 if kind == "devzira" else 0.03)
        col = light if rnd.random() < 0.5 else dark
        if kind == "devzira" and rnd.random() < 0.35: col = (176, 86, 52)
        _grain(layer, x, y, L, w * 0.009, rnd.uniform(-0.5, 0.5) + (0.3 if x > cx else -0.3), col)
        if kind == "devzira" and rnd.random() < 0.18:
            _grain(layer, x - 1, y - 1.5, L * 0.5, w * 0.004, 0.1, (255, 250, 236))
    mask = SS(lw, lh, c.ss); mask.poly(pts, fill=(255, 255, 255, 255), outline=None, width=0)
    layer.im.putalpha(ImageChops.multiply(layer.im.getchannel("A"), mask.im.getchannel("A")))
    c.im.alpha_composite(layer.im)
    c.poly(pts, fill=None, outline=OL, width=5)
    if toppings:
        P = pieces if pieces is not None else osh_pieces(seed, n_carrot=14 if kind == "devzira" else 26)
        draw_pieces(c, w, cx, cy, rxm, rym, mh, P, rot)
    return mh


@functools.lru_cache(maxsize=64)
def lagan_img(w=300, kind="mixed", seed=1, flag=0, top=None):
    """returns (img, ax, ay) where (ax, ay) is the rim centre. kind: mixed, devzira, empty, plate"""
    pad = 24 + (int(w * 0.34) if flag else 0)
    top_extra = int(w * 0.3) + (int(w * 0.2) if flag else 0)
    ry = w * 0.16
    cw, ch = w + 2 * pad, int(top_extra + ry * 2.5 + w * 0.06 + 24)
    cx, cy = cw / 2, top_extra + ry * 0.2
    c = SS(cw, ch, 3)
    plate(c, w, cx, cy, inner=kind in ("empty", "plate"))
    if kind in ("mixed", "devzira"):
        mound(c, w, cx, cy, kind, seed)
    im = c.result()
    if flag:
        side = 1 if flag > 0 else -1
        f = flag_img(int(w * 0.36), side)
        place_anchor(im, f, f.width / 2, f.height - 2, cx + side * w * 0.27, cy - w * 0.05, rot=-38 * side, world=False)
    return im, cx, cy


@functools.lru_cache(maxsize=8)
def flag_img(w=100, side=1):
    """small red flag on a stick; stick foot at bottom centre; cloth flies to the right (side=1) or left (-1)"""
    h = int(w * 1.15)
    c = SS(w * 2, h, 3)
    sx = w
    c.line([(sx, h - 2), (sx, 6)], fill=OL, width=w * 0.07 + 3)
    c.line([(sx, h - 2), (sx, 6)], fill=(214, 168, 110), width=w * 0.07)
    fw, fh = w * 0.98 * side, w * 0.42
    c.poly([(sx, 6), (sx + fw, 10), (sx + fw * 0.94, 6 + fh * 0.5), (sx + fw, 6 + fh), (sx, 6 + fh)], fill=RED, outline=OL, width=3)
    c.text((sx + fw * 0.47, 6 + fh * 0.5), "ENG ZOʻR!", w * 0.16, WHITE, font=FONT_MAIN)
    c.circle(sx, 6, w * 0.05, fill=GOLD, outline=OL, width=2)
    return c.result()


def flag_pole_img(w=100):
    return flag_img(w)


@functools.lru_cache(maxsize=16)
def label_card(text, w=300):
    h = int(w * 0.3)
    c = SS(w + 20, h + 30, 3)
    # little easel feet
    c.line([(w * 0.25, h), (w * 0.2, h + 24)], fill=OL, width=7)
    c.line([(w * 0.8, h), (w * 0.85, h + 24)], fill=OL, width=7)
    c.rect((6, 6, w + 6, h + 6), fill=CREAM, outline=OL, width=6, r=14)
    c.rect((6, 6, w + 6, 6 + h * 0.22), fill=RED, outline=OL, width=5, r=10)
    c.rect((16, 6 + h * 0.3, w - 4, h - 4), fill=None, outline=GOLD, width=3, r=8)
    im = c.result()
    sz = int(h * 0.48)
    t = plain_text(text, sz, (70, 28, 18))
    if t.width > w - 40:
        sz = int(sz * (w - 40) / t.width); t = plain_text(text, sz, (70, 28, 18))
    im.alpha_composite(t, (int(6 + (w - t.width) / 2), int(6 + h * 0.28 + (h * 0.72 - t.height) / 2)))
    return im


# ---------------------------------------------------------------- Samarqand layers (separate, unmixed)
@functools.lru_cache(maxsize=4)
def layer_imgs(w=320, seed=4):
    """rice layer, carrot layer, meat layer for a plate of width w; all share anchor = rim centre"""
    pad = 24
    top_extra = int(w * 0.42)
    ry = w * 0.16
    cw, ch = w + 2 * pad, int(top_extra + ry * 2.5 + w * 0.06 + pad)
    cx, cy = cw / 2, top_extra + ry * 0.2
    rxm, rym = w / 2 * 0.72, ry * 0.72
    out = {}
    # rice (plain golden rice dome, lower)
    c = SS(cw, ch, 3)
    mh = mound(c, w, cx, cy, "mixed", seed, mh_mul=0.8, toppings=False)
    out["rice"] = c.result()
    # carrot layer: orange cap sitting on the rice dome
    c = SS(cw, ch, 3)
    rnd = random.Random(seed + 1)
    cap_y = cy - mh * 0.55
    pts = _mound_mask(cw, ch, cx, cap_y + mh * 0.25, rxm * 0.8, rym * 0.75, mh * 0.62)
    c.poly(pts, fill=CARROT, outline=OL, width=5)
    c.ellipse((cx + rxm * 0.1, cap_y - mh * 0.35, cx + rxm * 0.85, cap_y + mh * 0.35), fill=CARROT_D, outline=None, width=0)
    for _ in range(40):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0, 0.85)
        x = cx + rxm * 0.78 * r * math.cos(a)
        u = max(0.0, 1 - r * r)
        y = cap_y + mh * 0.25 - mh * 0.62 * u ** 0.6 + rym * 0.7 * r * math.sin(a) * 0.6 + 6
        ang = rnd.uniform(-0.7, 0.7); L = w * rnd.uniform(0.08, 0.12)
        dx, dy = math.cos(ang) * L / 2, math.sin(ang) * L / 2
        c.line([(x - dx, y - dy), (x + dx, y + dy)], fill=CARROT_D, width=w * 0.024 + 3)
        c.line([(x - dx, y - dy), (x + dx, y + dy)], fill=(250, 150, 50), width=w * 0.02)
    c.poly(pts, fill=None, outline=OL, width=5)
    out["carrot"] = c.result()
    # meat layer: cluster of chunks on the very top
    c = SS(cw, ch, 3)
    top_y = cap_y - mh * 0.3
    P = []
    for i in range(7):
        a = 2 * math.pi * i / 7 + 0.4
        r = 0.55 if i else 0.0
        P.append(dict(kind="meat", az=a, r=r, ang=rnd.uniform(-0.5, 0.5), L=rnd.uniform(0.09, 0.11), Wd=rnd.uniform(0.06, 0.07)))
    draw_pieces(c, w, cx, top_y + mh * 0.12, rxm * 0.42, rym * 0.42, mh * 0.18, P)
    out["meat"] = c.result()
    c = SS(cw, ch, 3)
    plate(c, w, cx, cy, inner=True)
    out["plate"] = c.result()
    return out, cx, cy


# ---------------------------------------------------------------- devzira macro texture
@functools.lru_cache(maxsize=1)
def devzira_macro(w=1500, h=2400, seed=11):
    rnd = random.Random(seed)
    c = SS(w, h, 1, bg=(170, 92, 52, 255))
    for layer in range(3):
        n = 260
        for _ in range(n):
            x, y = rnd.uniform(-100, w + 100), rnd.uniform(-100, h + 100)
            L = rnd.uniform(230, 300); Wd = rnd.uniform(52, 62)
            a = rnd.uniform(-0.9, 0.9) + (math.pi / 2 if rnd.random() < 0.35 else 0)
            dx, dy = math.cos(a), math.sin(a)
            pts = []
            for k in range(40):
                t = 2 * math.pi * k / 40
                px = L / 2 * math.cos(t); py = Wd / 2 * math.sin(t) * (1 - 0.15 * abs(math.cos(t)) ** 3)
                pts.append((x + px * dx - py * dy, y + px * dy + py * dx))
            tone = rnd.uniform(0, 1)
            col = (int(232 - 30 * tone), int(186 - 60 * tone), int(142 - 52 * tone))
            c.poly(pts, fill=col, outline=OL, width=4)
            # rust streak along the grain (devzira's red-brown bran)
            for s_off in (-0.18, 0.12):
                c.line([(x - dx * L * 0.36 - dy * Wd * s_off, y - dy * L * 0.36 + dx * Wd * s_off),
                        (x + dx * L * 0.36 - dy * Wd * s_off, y + dy * L * 0.36 + dx * Wd * s_off)], fill=(186, 98, 60), width=Wd * 0.16)
            # oily highlight
            c.line([(x - dx * L * 0.25 - dy * Wd * -0.22, y - dy * L * 0.25 + dx * Wd * -0.22),
                    (x + dx * L * 0.1 - dy * Wd * -0.22, y + dy * L * 0.1 + dx * Wd * -0.22)], fill=(255, 250, 232), width=Wd * 0.12)
            c.circle(x + dx * L * 0.18 - dy * Wd * -0.2, y + dy * L * 0.18 + dx * Wd * -0.2, Wd * 0.07, fill=(255, 255, 255), outline=None, width=0)
    return c.result()


# ---------------------------------------------------------------- stamp / badge / kapgir / sparkles
@functools.lru_cache(maxsize=4)
def stamp_img(size=320):
    c = SS(size, size, 3)
    m = size / 2; R = m * 0.94
    pts = [(m + R * (1 + 0.045 * math.cos(28 * a)) / 1.045 * math.cos(a), m + R * (1 + 0.045 * math.cos(28 * a)) / 1.045 * math.sin(a))
           for a in np.linspace(0, 2 * math.pi, 280)]
    c.poly(pts, fill=GOLD, outline=OL, width=7)
    c.circle(m, m, R * 0.8, fill=(248, 206, 96), outline=GOLD_D, width=6)
    c.circle(m, m, R * 0.68, fill=None, outline=GOLD_D, width=3)
    for i in range(5):
        a = math.radians(-150 + 30 * i)
        sx, sy = m + R * 0.55 * math.cos(a), m + R * 0.55 * math.sin(a)
        star(c, sx, sy, R * 0.07, (150, 92, 20))
    c.line([(m - R * 0.45, m + R * 0.25), (m + R * 0.45, m + R * 0.25)], fill=GOLD_D, width=4)
    im = c.result()
    t = plain_text("YUNESKO", int(R * 0.34), (112, 58, 8))
    im.alpha_composite(t, (int(m - t.width / 2), int(m - t.height / 2 - R * 0.02)))
    t2 = plain_text("2016", int(R * 0.2), (150, 92, 20))
    im.alpha_composite(t2, (int(m - t2.width / 2), int(m + R * 0.34)))
    return im


def star(c, x, y, r, col, n=5, outline=None, width=0, inner=0.45, rot=-math.pi / 2):
    pts = []
    for i in range(2 * n):
        a = rot + math.pi * i / n
        rr = r if i % 2 == 0 else r * inner
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    c.poly(pts, fill=col, outline=outline, width=width)


@functools.lru_cache(maxsize=4)
def badge_img(size=170):
    c = SS(size, size * 1.3, 3)
    m = size / 2; R = m * 0.9
    # ribbon tails
    for sgn in (-1, 1):
        x0 = m + sgn * R * 0.35
        c.poly([(x0 - R * 0.22, m + R * 0.4), (x0 + R * 0.22, m + R * 0.4), (x0 + R * 0.2 + sgn * R * 0.1, size * 1.25),
                (x0 + sgn * R * 0.1, size * 1.12), (x0 - R * 0.2 + sgn * R * 0.1, size * 1.25)], fill=RED, outline=OL, width=4)
    pts = [(m + R * (1 + 0.06 * math.cos(20 * a)) / 1.06 * math.cos(a), m + R * (1 + 0.06 * math.cos(20 * a)) / 1.06 * math.sin(a))
           for a in np.linspace(0, 2 * math.pi, 200)]
    c.poly(pts, fill=GOLD, outline=OL, width=5)
    c.circle(m, m, R * 0.74, fill=CREAM, outline=GOLD_D, width=4)
    star(c, m, m - R * 0.38, R * 0.15, GOLD, outline=OL, width=2)
    im = c.result()
    t = plain_text("HAKAM", int(R * 0.36), (150, 20, 30))
    im.alpha_composite(t, (int(m - t.width / 2), int(m - t.height / 2 + R * 0.08)))
    return im


@functools.lru_cache(maxsize=4)
def kapgir_img(L=360, r=56):
    """flat perforated skimmer with a wooden handle. returns (img, pivot(x,y) = handle end, disc centre)"""
    w, h = int(L + 2 * r + 30), int(2 * r + 30)
    c = SS(w, h, 3)
    dx, dy = 15 + r, h / 2
    hx = w - 14
    c.line([(dx + r * 0.6, dy), (hx, dy)], fill=OL, width=r * 0.36 + 6)
    c.line([(dx + r * 0.6, dy), (hx, dy)], fill=(160, 100, 52), width=r * 0.36)
    c.line([(dx + r * 1.2, dy - r * 0.06), (hx - 10, dy - r * 0.06)], fill=(206, 150, 92), width=r * 0.09)
    c.circle(hx - 12, dy, r * 0.06, fill=OL, outline=None, width=0)
    c.circle(dx, dy, r, fill=(204, 210, 220), outline=OL, width=5)
    c.circle(dx, dy, r * 0.82, fill=None, outline=(160, 168, 182), width=3)
    for i in range(-2, 3):
        for j in range(-2, 3):
            if i * i + j * j <= 5:
                c.circle(dx + i * r * 0.28, dy + j * r * 0.28, r * 0.07, fill=(110, 118, 132), outline=None, width=0)
    c.arc((dx - r * 0.75, dy - r * 0.75, dx + r * 0.2, dy + r * 0.2), 190, 260, fill=(255, 255, 255), width=4)
    return c.result(), (hx, dy), (dx, dy)


@functools.lru_cache(maxsize=8)
def sparkle_img(size=60, col=GOLD_L):
    c = SS(size, size, 3)
    m = size / 2
    star(c, m, m, m * 0.95, col, n=4, outline=OL, width=size * 0.05, inner=0.32)
    c.circle(m, m, m * 0.14, fill=WHITE, outline=None, width=0)
    return c.result()


@functools.lru_cache(maxsize=4)
def heart_img(size=46, col=(236, 64, 92)):
    c = SS(size, size, 3)
    m = size / 2
    pts = []
    for t in np.linspace(0, 2 * math.pi, 60):
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((m + x * size / 38, m + y * size / 38 - 1))
    c.poly(pts, fill=col, outline=OL, width=size * 0.07)
    c.circle(m - size * 0.18, m - size * 0.16, size * 0.07, fill=(255, 200, 210), outline=None, width=0)
    return c.result()


@functools.lru_cache(maxsize=4)
def cloud_img(w=300):
    h = int(w * 0.62)
    c = SS(w, h, 3)
    blobs = [(0.28, 0.58, 0.2), (0.5, 0.42, 0.27), (0.72, 0.56, 0.21), (0.5, 0.66, 0.2), (0.36, 0.42, 0.17)]
    for bx, by, br in blobs:
        c.circle(w * bx, h * by, w * br, fill=(146, 152, 164), outline=OL, width=6)
    for bx, by, br in blobs:
        c.circle(w * bx, h * by, w * br - 3.5, fill=(146, 152, 164), outline=None, width=0)
    c.circle(w * 0.45, h * 0.36, w * 0.1, fill=(178, 184, 196), outline=None, width=0)
    c.rect((w * 0.2, h * 0.62, w * 0.82, h * 0.82), fill=(146, 152, 164), outline=None, width=0)
    c.line([(w * 0.12, h * 0.8), (w * 0.88, h * 0.8)], fill=OL, width=6)
    c.rect((w * 0.1, h * 0.81, w * 0.9, h), fill=(0, 0, 0, 0), outline=None, width=0)
    im = c.result()
    return im.crop((0, 0, w, int(h * 0.84)))


@functools.lru_cache(maxsize=2)
def logo_img(d=300):
    im = Image.open(os.path.join(ROOT, "assets", "logo.png")).convert("RGBA")
    im = im.resize((d, d), Image.LANCZOS)
    # soft drop shadow + gold ring
    pad = 30
    out = Image.new("RGBA", (d + 2 * pad, d + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", out.size, 0)
    ImageDraw.Draw(sh).ellipse((pad + 2, pad + 12, pad + d + 2, pad + d + 12), fill=150)
    shadow = Image.new("RGBA", out.size, (0, 0, 0, 255)); shadow.putalpha(sh.filter(ImageFilter.GaussianBlur(12)))
    out.alpha_composite(shadow)
    c = SS(out.width, out.height, 3)
    c.circle(out.width / 2, out.height / 2, d / 2 + 7, fill=GOLD, outline=OL, width=5)
    out.alpha_composite(c.result())
    out.alpha_composite(im, (pad, pad))
    return out


# ---------------------------------------------------------------- balance scale (drawn per frame)
def scale_img(beam_rot, t, w=470, mini=None):
    h = int(w * 0.8)
    c = SS(w, h, 2)
    px, py = w / 2, h * 0.16
    # post
    c.rect((px - 9, py, px + 9, h * 0.92), fill=GOLD, outline=OL, width=4)
    c.ellipse((px - 60, h * 0.88, px + 60, h * 0.98), fill=GOLD_D, outline=OL, width=4)
    c.circle(px, py - 8, 16, fill=GOLD_L, outline=OL, width=4)
    a = math.radians(beam_rot)
    L = w * 0.42
    ex = [(px - L * math.cos(a), py + L * math.sin(a)), (px + L * math.cos(a), py - L * math.sin(a))]
    c.line([ex[0], ex[1]], fill=OL, width=16)
    c.line([ex[0], ex[1]], fill=GOLD, width=10)
    for k, (x, y) in enumerate(ex):
        sw = 4 * math.sin(2 * math.pi * 1.3 * t + k)
        bx, by = x + sw, y + h * 0.36
        c.line([(x, y), (bx - 44, by)], fill=OL, width=3)
        c.line([(x, y), (bx + 44, by)], fill=OL, width=3)
        c.circle(x, y, 8, fill=GOLD_L, outline=OL, width=3)
        c.d.chord(c._b((bx - 62, by - 28, bx + 62, by + 34)), 0, 180, fill=GOLD, outline=OL, width=c._w(4))
        c.line([(bx - 62, by + 3), (bx + 62, by + 3)], fill=OL, width=4)
    im = c.result()
    if mini is not None:
        for k, (x, y) in enumerate(ex):
            sw = 4 * math.sin(2 * math.pi * 1.3 * t + k)
            paste(im, mini, x + sw - mini.width / 2, y + h * 0.36 - mini.height + 14)
    return im, (px, py)


# ---------------------------------------------------------------- phone UI and comment bubbles
def phone_panel(t, cursor_on=True, pressed=None, w=440, h=640):
    c = SS(w, h, 2)
    c.rect((6, 6, w - 6, h - 6), fill=(28, 30, 36), outline=OL, width=7, r=50)
    sx0, sy0, sx1, sy1 = 24, 54, w - 24, h - 26
    c.rect((sx0, sy0, sx1, sy1), fill=(246, 247, 250), outline=None, width=0, r=24)
    c.rect((w / 2 - 50, 22, w / 2 + 50, 36), fill=(60, 62, 70), outline=None, width=0, r=7)
    # header
    c.rect((sx0, sy0, sx1, sy0 + 62), fill=(232, 236, 242), outline=None, width=0, r=24)
    im0 = None
    # comment rows (placeholders)
    for k in range(3):
        y = sy0 + 92 + k * 74
        c.circle(sx0 + 40, y + 18, 20, fill=[(240, 170, 70), (90, 170, 150), (210, 110, 120)][k], outline=None, width=0)
        c.rect((sx0 + 72, y + 4, sx0 + 72 + [190, 230, 160][k], y + 18), fill=(200, 205, 214), outline=None, width=0, r=7)
        c.rect((sx0 + 72, y + 26, sx0 + 72 + [250, 170, 210][k], y + 38), fill=(220, 224, 230), outline=None, width=0, r=6)
    # input field
    fy = sy0 + 330
    c.rect((sx0 + 12, fy, sx1 - 12, fy + 64), fill=WHITE, outline=(40, 120, 230), width=4, r=32)
    c.circle(sx1 - 46, fy + 32, 22, fill=(40, 120, 230), outline=None, width=0)
    c.poly([(sx1 - 56, fy + 21), (sx1 - 33, fy + 32), (sx1 - 56, fy + 43), (sx1 - 52, fy + 32)], fill=WHITE, outline=None, width=0)
    if cursor_on:
        c.rect((sx0 + 34, fy + 14, sx0 + 39, fy + 50), fill=(30, 30, 40), outline=None, width=0)
    # keyboard
    ky = fy + 86
    rows = [10, 9, 7]
    kw = (sx1 - sx0 - 20) / 10
    idx = 0
    for r_, n in enumerate(rows):
        x0 = sx0 + 10 + (10 - n) * kw / 2
        for i in range(n):
            on = pressed is not None and idx in pressed
            c.rect((x0 + i * kw + 3, ky + r_ * 46, x0 + (i + 1) * kw - 3, ky + r_ * 46 + 38),
                   fill=(255, 214, 60) if on else (214, 218, 226), outline=None, width=0, r=6)
            idx += 1
    c.rect((sx0 + 10 + kw * 2, ky + 3 * 46, sx1 - 10 - kw * 2, ky + 3 * 46 + 34), fill=(214, 218, 226), outline=None, width=0, r=6)
    im = c.result()
    head = plain_text("Izohlar", 30, (40, 44, 54))
    im.alpha_composite(head, (int(sx0 + 22), int(sy0 + 31 - head.height / 2)))
    ph = plain_text("Izoh qoldiring...", 27, (150, 156, 168))
    im.alpha_composite(ph, (int(sx0 + 48), int(fy + 32 - ph.height / 2)))
    return im


@functools.lru_cache(maxsize=4)
def bubble_img(seed=0, w=420):
    h = 150
    t1 = plain_text("Viloyatingiz +", 38, (36, 30, 26))
    t2 = plain_text("sevimli osh", 38, (196, 40, 50))
    w = max(w, 118 + max(t1.width, t2.width) + 34)
    c = SS(w, h + 40, 3)
    c.rect((6, 6, w - 6, h), fill=WHITE, outline=OL, width=6, r=36)
    tail_x = w * 0.2
    c.poly([(tail_x - 26, h - 6), (tail_x + 4, h + 34), (tail_x + 22, h - 6)], fill=WHITE, outline=None, width=0)
    c.line([(tail_x - 26, h - 3), (tail_x + 4, h + 34), (tail_x + 22, h - 3)], fill=OL, width=6)
    cols = [(240, 170, 70), (90, 170, 150), (210, 110, 120)]
    c.circle(62, h / 2 + 3, 36, fill=cols[seed % 3], outline=OL, width=4)
    c.circle(62, h / 2 - 7, 13, fill=WHITE, outline=None, width=0)
    c.d.chord(c._b((62 - 22, h / 2 + 8, 62 + 22, h / 2 + 44)), 180, 360, fill=WHITE)
    im = c.result()
    im.alpha_composite(t1, (118, int(h / 2 - t1.height - 4)))
    im.alpha_composite(t2, (118, int(h / 2 + 8)))
    return im


# ---------------------------------------------------------------- warm home background (scene 9)
@functools.lru_cache(maxsize=1)
def home_bg():
    w, h = WW, WH
    base = vgrad(w, h, [(0, (120, 62, 30)), (0.35, (176, 98, 42)), (0.62, (150, 80, 36)), (0.64, (110, 56, 26)), (1, (70, 34, 18))])
    g = radial(w, h, M + 330, M + 520, 900, 1.2)[..., None]
    base = base * (1 - 0.5 * g) + np.array([255, 196, 110], np.float32) * 0.5 * g
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    # faint wall ornament band (gold ikat) on the wall
    mot = motif_layer(w + 300, h)[:, :w]
    a = np.asarray(im).astype(np.float32)
    a[..., :3] = a[..., :3] * (1 - 0.08 * mot[..., None]) + np.array([255, 214, 140]) * 0.08 * mot[..., None]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
    c = SS(w, h, 2)
    # arched window with panjara lattice
    wx0, wy0, wx1, wy1 = M + 70, M + 300, M + 430, M + 880
    arch = [(wx0, wy1), (wx0, wy0 + 160)] + ell_pts((wx0 + wx1) / 2, wy0 + 160, (wx1 - wx0) / 2, 170, 180, 360, 40) + [(wx1, wy1)]
    c.poly(arch, fill=(255, 236, 180), outline=(90, 46, 20), width=18)
    for k in range(-6, 8):
        x = wx0 + k * 52
        c.line([(x, wy1), (x + 360, wy1 - 360)], fill=(150, 82, 34), width=7)
        c.line([(x + 360, wy1), (x, wy1 - 360)], fill=(150, 82, 34), width=7)
        c.line([(x, wy1 - 300), (x + 360, wy1 - 660)], fill=(150, 82, 34), width=7)
        c.line([(x + 360, wy1 - 300), (x, wy1 - 660)], fill=(150, 82, 34), width=7)
    win = c.result()
    m2 = SS(w, h, 2); m2.poly(arch, fill=(255, 255, 255, 255), outline=None, width=0)
    win.putalpha(ImageChops.multiply(win.getchannel("A"), m2.result().getchannel("A")))
    c2 = SS(w, h, 2); c2.poly(arch, fill=None, outline=(90, 46, 20), width=20)
    c2.rect((wx0 - 30, wy1 - 6, wx1 + 30, wy1 + 26), fill=(120, 64, 28), outline=OL, width=5)
    im.alpha_composite(win); im.alpha_composite(c2.result())
    # floor: dasturxon spread in perspective
    return im


def beams(t, w=WW, h=WH):
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k in range(4):
        x0 = M + 110 + k * 85
        sway = 18 * math.sin(2 * math.pi * (t * 0.25 + k * 0.3))
        a = int(46 + 20 * math.sin(2 * math.pi * (t * 0.4 + k * 0.21)))
        d.polygon([(x0, M + 380), (x0 + 60, M + 380), (x0 + 620 + sway, M + 1500), (x0 + 380 + sway, M + 1500)], fill=(255, 230, 160, a))
    return lay.filter(ImageFilter.GaussianBlur(26))


@functools.lru_cache(maxsize=2)
def vignette_layer(strength=0.55, color=(30, 12, 4)):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - 540) / 700) ** 2 + ((yy - 900) / 1150) ** 2)
    a = np.clip((d - 0.55) / 0.6, 0, 1) ** 1.6 * strength
    im = Image.new("RGBA", (W, H), color + (0,))
    im.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    return im


@functools.lru_cache(maxsize=1)
def floor_cloth():
    """dasturxon spread on the floor in perspective (scene 9)"""
    w, h = 1300, 520
    pat = atlas_pattern(w, h, yscale=0.55)
    sh = np.linspace(0.62, 0.38, h)[:, None, None]
    im = Image.fromarray(np.clip(pat * sh, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    # trapezoid mask
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon([(w * 0.2, 0), (w * 0.8, 0), (w, h), (0, h)], fill=255)
    im.putalpha(m)
    c = SS(w, h, 2)
    c.poly([(w * 0.2, 2), (w * 0.8, 2), (w - 2, h - 2), (2, h - 2)], fill=None, outline=OL, width=7)
    c.line([(w * 0.2 + 18, 22), (w * 0.8 - 18, 22)], fill=GOLD, width=6)
    im.alpha_composite(c.result())
    return im


def steam_layer(t, cx, cy, w=360, n=3, alpha=0.55):
    lw, lh = int(w * 1.4), 520
    c = SS(lw, lh, 2)
    for k in range(n):
        x0 = lw / 2 + (k - (n - 1) / 2) * w * 0.26
        ph = t * 1.4 + k * 0.37
        prog = (ph % 1.0)
        pts = []
        for i in range(26):
            u = i / 25
            y = lh - 30 - u * (lh - 60)
            x = x0 + 26 * math.sin(2 * math.pi * (u * 1.3 - t * 0.9 + k * 0.3)) * (0.4 + u)
            pts.append((x, y))
        c.line(pts, fill=(255, 255, 255, int(255 * alpha)), width=14)
    im = c.result().filter(ImageFilter.GaussianBlur(5))
    # fade top and bottom
    g = np.linspace(0, 1, lh)
    fade = np.clip(np.minimum(g / 0.4, (1 - g) / 0.15), 0, 1)
    a = np.asarray(im.getchannel("A")).astype(np.float32) * fade[:, None]
    im.putalpha(Image.fromarray(a.astype(np.uint8)))
    return im, (cx - lw / 2, cy - lh + 30)
