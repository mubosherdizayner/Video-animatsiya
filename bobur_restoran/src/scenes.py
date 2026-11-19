# Scene logic: each scene draws its world, applies the camera and returns a 1080x1920 RGB frame.
import math, json, os, random, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageEnhance
from lib import *
from worlds import *
from chars import *
from script_data import SCENES, HEADLINES

TIMING = json.load(open(os.path.join(HERE, "timing.json")))
AUDIO_DUR = float(open(os.path.join(HERE, "audio_dur.txt")).read())
N_FRAMES = int(math.ceil(AUDIO_DUR * FPS - 1e-6))
VIDEO_DUR = N_FRAMES / FPS

SC_START = {}
for w in TIMING:
    SC_START.setdefault(w["scene"], w["start"])
SC_START[1] = 0.0
SC_IDS = sorted(SC_START)
SC_FRAME = {k: int(math.ceil(SC_START[k] * FPS - 1e-6)) for k in SC_IDS}
SC_END_FRAME = {k: (SC_FRAME[SC_IDS[i + 1]] if i + 1 < len(SC_IDS) else N_FRAMES) for i, k in enumerate(SC_IDS)}
SPEAKER = {sid: spk for sid, spk, _ in SCENES}
def scene_words(k): return [w for w in TIMING if w["scene"] == k]
def word_frame(w): return int(math.ceil(w["start"] * FPS - 1e-6))
def word_t(k, prefix):
    w = [w for w in scene_words(k) if w["text"].lower().startswith(prefix.lower())][0]
    return word_frame(w) / FPS - SC_START[k]
LAST = N_FRAMES - 1
CUT_F = int(math.ceil(TIMING[-1]["end"] * FPS - 1e-6))       # loop cut: right after the last word ends
CUT_F = min(CUT_F, LAST - 4)
FLASH_F0 = CUT_F - 6

def scene_at_frame(i):
    cur = SC_IDS[0]
    for k in SC_IDS:
        if i >= SC_FRAME[k]: cur = k
    return cur

# ---------------------------------------------------------------- motion helpers
def talk_sy(i, k):
    """sheet sprite talk-bob: scale-y 1.00->1.03 over 3 frames at every word onset of a MIJOZ/BOBUR line"""
    if SPEAKER[k] not in ("MIJOZ", "BOBUR"): return 1.0
    best = None
    for w in scene_words(k):
        f = word_frame(w)
        if f <= i: best = f
    if best is None: return 1.0
    d = i - best
    if d <= 2: return 1.0 + 0.03 * d / 2.0
    if d < 6: return 1.03 - 0.03 * (d - 2) / 3.0
    return 1.0

def mouth_amt(i, k):
    """code-drawn waiter: opens at every word onset, closes between words (quantised)"""
    t = i / FPS
    cur = None
    for w in scene_words(k):
        if word_frame(w) <= i: cur = w
    if cur is None: return 0.0
    d = i - word_frame(cur)
    dur = max(0.1, cur["end"] - cur["start"])
    if t >= cur["end"] - 0.02: return 0.0
    if d == 0: return 0.5
    ph = (t - cur["start"]) / dur
    if ph < 0.7: return 1.0
    return round(max(0.0, 1 - (ph - 0.7) / 0.3) * 4) / 4

def blink_amt(t, seed=0):
    rnd = random.Random(seed)
    tb = rnd.uniform(0.6, 1.8)
    while tb < t + 1:
        d = t - tb
        if 0 <= d < 5 / FPS:
            return [0.5, 1.0, 1.0, 0.5, 0.15][int(d * FPS)]
        tb += rnd.uniform(2.0, 4.0)
    return 0.0

def breathe(t, amp=0.006, per=1.7, ph=0.0):
    return 1.0 + amp * math.sin(2 * math.pi * t / per + ph)

def shake_xy(f, amp, n=6, seed=0):
    if f <= 0 or f >= n: return 0.0, 0.0
    rnd = random.Random(seed * 1000 + int(f))
    k = 1 - f / n
    return amp * k * rnd.choice([-1, 1]) * rnd.uniform(0.6, 1.0), amp * k * rnd.choice([-1, 1]) * rnd.uniform(0.6, 1.0)

FRAME_SPR = []                 # (sprite name, world height) drawn in the current frame
MAXDISP = {}                   # sprite name -> max on-screen height (checked against the 5x limit)
def camera(world, ox, oy, cx, cy, z, rot=0.0, shx=0.0, shy=0.0):
    for name, h in FRAME_SPR:
        MAXDISP[name] = max(MAXDISP.get(name, 0), h * z)
    FRAME_SPR.clear()
    th = math.radians(rot)
    c, s = math.cos(th), math.sin(th)
    a, b = c / z, s / z
    d, e = -s / z, c / z
    X0, Y0 = 540 + shx, 960 + shy
    cc = cx - ox - a * X0 - b * Y0
    ff = cy - oy - d * X0 - e * Y0
    return world.transform((W, H), Image.AFFINE, (a, b, cc, d, e, ff), resample=Image.BICUBIC, fillcolor=(20, 20, 24))

def motion_blur_cam(world, ox, oy, cxs, cy, z, rot=0.0):
    spr = list(FRAME_SPR)
    acc = None
    for cx in cxs:
        FRAME_SPR[:] = spr
        im = np.asarray(camera(world, ox, oy, cx, cy, z, rot)).astype(np.float32)
        acc = im if acc is None else acc + im
    return Image.fromarray((acc / len(cxs)).astype(np.uint8))

def to_screen(x, y, cx, cy, z): return (540 + (x - cx) * z, 960 + (y - cy) * z)

# ---------------------------------------------------------------- sheet sprites
def HS(name, k=1.0): return META[name]["h"] / META[name]["stand_h"] * STD_H * k
def sheet(world, who, pose, x, yb, ox, oy, k=1.0, sx=1.0, sy=1.0, rot=0.0, mirror=False, darken=1.0):
    name = spr_name(who, pose); h = HS(name, k)
    draw_char(world, name, x, yb, h, ox, oy, sx=sx, sy=sy, rot=rot, mirror=mirror, darken=darken)
    FRAME_SPR.append((name, h * sy))
    return name, h

# ---------------------------------------------------------------- code-drawn characters (cached renders)
LOOKS = {"waiter": WAITER, "waiter2": WAITER2, "waiter3": WAITER3, "chef": CHEF, "cashier": CASHIER}
FOLDER = {}
def _folder(H):
    if H not in FOLDER: FOLDER[H] = folder_img(H)
    return FOLDER[H]

@functools.lru_cache(maxsize=256)
def person(look, H, key):
    P = json.loads(key)
    props = {}
    for side, spec in P.pop("props", {}).items():
        kind, layer = spec[0], spec[1]
        if kind == "tray": props[side] = (tray_draw(H), layer)
        elif kind.startswith("mask:"): props[side] = (mask_draw(H, kind[5:], float(spec[2]) if len(spec) > 2 else 1.0), layer)
        elif kind.startswith("knife:"): props[side] = (knife_draw(H, float(kind[6:])), layer)
        elif kind == "onion": props[side] = (onion_half_draw(H), layer)
    P["props"] = props
    fp = P.pop("folder", None)
    if fp is not None:
        sc, dx, dy, rot = fp
        def front(cv, H_, pts, sc=sc, dx=dx, dy=dy, rot=rot):
            fold, fx, fy = _folder(H_)
            f2 = fold
            if abs(sc - 1) > 1e-3 or abs(rot) > 0.1:
                f2 = fold.resize((int(fold.width * sc), int(fold.height * sc)), Image.LANCZOS).rotate(rot, resample=Image.BICUBIC, expand=False)
            (lx, ly), (rx, ry) = pts["L"], pts["R"]
            cv.paste(f2, (lx + rx) / 2 - f2.width / 2 + dx * H_, (ly + ry) / 2 - f2.height / 2 + dy * H_)
        P["front_prop"] = front
    return render_person(LOOKS[look], H, P)

def pkey(**P): return json.dumps(P, sort_keys=True)

def put_person(world, look, H, x, yb, ox, oy, scale=1.0, rot=0.0, **P):
    img, ax, ay, pts = person(look, H, pkey(**P))
    blit_person(world, img, ax, ay, x, yb, ox, oy, scale=scale, rot=rot)
    return pts

# ---------------------------------------------------------------- common effects
def flash(frame, alpha, col=(255, 255, 255)):
    if alpha <= 0.003: return frame
    return Image.blend(frame, Image.new("RGB", frame.size, col), min(1, alpha))

def vhs(frame, p, seed):
    k = 1 - p
    a = np.asarray(frame).astype(np.int16).copy()
    rnd = random.Random(seed)
    dx = int(16 * k) + 2
    r = np.roll(a[..., 0], dx, axis=1); b = np.roll(a[..., 2], -dx, axis=1)
    a[..., 0] = r; a[..., 2] = b
    for _ in range(int(9 * k) + 2):
        y0 = rnd.randint(0, H - 60); hh = rnd.randint(8, 70); sh = rnd.randint(-60, 60)
        a[y0:y0 + hh] = np.roll(a[y0:y0 + hh], int(sh * k), axis=1)
    by = int((1 - p) * H * 1.2 - 100) % H
    a[by:by + 70] = np.clip(a[by:by + 70] * 0.6 + 90 + np.random.RandomState(seed).randint(0, 80, (min(70, H - by), W, 1)), 0, 255)
    a[::4] = (a[::4] * (1 - 0.22 * k)).astype(np.int16)
    for _ in range(int(14 * k)):
        y = rnd.randint(0, H - 3)
        a[y:y + 2, :] = np.clip(a[y:y + 2, :] + 110, 0, 255)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def puff_screen(frame, p, cx=540, cy=1250, size=980):
    im = smoke_puff(p, size=size)
    if im is None: return
    frame.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)

def sparkles(canvas, pts, t, ox, oy, scale=1.0):
    for j, (x, y) in enumerate(pts):
        ph = t * 5 + j * 1.7
        s = (0.55 + 0.45 * math.sin(ph)) * scale
        if s <= 0.05: continue
        sp = A["sparkle"] if j % 2 == 0 else A["sparkle_w"]
        place(canvas, sp, x, y, scale=s, rot=(t * 90 + j * 40) % 90, ox=ox, oy=oy)

def dim(img, ox, oy, centre, radius, floor=0.4, warm=True, vignette=0.35, soft=260):
    a = np.asarray(img).astype(np.float32)
    h, w, _ = a.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = centre[0] - ox, centre[1] - oy
    d = np.sqrt((xx - cx) ** 2 + ((yy - cy) * 0.8) ** 2)
    spot = np.clip(1 - (d - radius) / soft, 0, 1)
    spot = spot * spot * (3 - 2 * spot)
    m = floor + (1 - floor) * spot
    out = a * m[..., None]
    if warm: out *= np.stack([1.0 + 0.0 * spot, 1.0 - 0.05 * spot, 1.0 - 0.14 * spot], -1)
    if vignette:
        vx = (xx / w - 0.5); vy = (yy / h - 0.5)
        out *= (1 - vignette * np.clip((vx ** 2 + vy ** 2) * 3.2, 0, 1))[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

def headline_img(text):
    emoji_only = all(is_emoji(ch) or ch in " ️" for ch in text)
    size = 150 if emoji_only else 80
    words = text.split()
    full = text_img(text, size, stroke=9, shadow=0.55)
    if full.width <= 900:
        return [full], size
    best = None
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        ia, ib = text_img(a, size, stroke=9, shadow=0.55), text_img(b, size, stroke=9, shadow=0.55)
        m = max(ia.width, ib.width)
        if best is None or m < best[0]: best = (m, a, b)
    m, a, b = best
    sz = size if m <= 900 else int(size * 900 / m)
    return [text_img(a, sz, stroke=9, shadow=0.55), text_img(b, sz, stroke=9, shadow=0.55)], sz

# ---------------------------------------------------------------- assets (built once before forking)
A = {}
TABLE_FLOOR = 1700
def build_assets():
    A["hall"] = hall_back()
    A["ext"] = exterior_back()
    A["kitchen"] = kitchen_back()
    A["cash"] = cashdesk_back()
    A["blog"] = blogger_back()
    A["phone"], A["phone_x"], A["phone_y"] = phone_tripod()
    A["spot_off"] = spotlight_fixture(0.0); A["spot_on"] = spotlight_fixture(1.0)
    A["beam"] = beam_img(1650, 90, 560, 0.42)
    A["pool"] = floor_pool(520, 130, 0.55)
    A["curtL"] = curtain_strip(112, 1960, "L"); A["curtR"] = curtain_strip(112, 1960, "R")
    A["valance"] = valance(1180, 140)
    A["table"] = table_img(470, drape=390)
    A["table_w"] = table_img(620, drape=390)
    A["table_s"] = table_img(380, drape=200, base_h=330)
    A["chair"] = chair_img(520, 200)
    A["chair_s"] = chair_img(420, 160)
    A["plate"] = plate_img(115)
    A["plate_big"] = plate_img(170)
    A["fork"] = fork_img(150); A["spoon"] = spoon_img(150)
    A["sign_on"] = restoran_sign(1.0); A["sign_off"] = restoran_sign(0.0); A["sign_mid"] = restoran_sign(0.45)
    A["sold"] = sold_sign()
    A["plant"] = potted_plant(430)
    A["sparkle"] = sparkle(70); A["sparkle_w"] = sparkle(56, col=(255, 255, 255))
    A["thought"] = thought_bubble(520, 400)
    A["clouds"] = [lilac_cloud(70 + 8 * (k % 3), seed=k) for k in range(7)]
    A["clapper_open"] = clapper_icon(300, 32, "KADR 1 · DUBL 1")
    A["clapper_shut"] = clapper_icon(300, 0, "KADR 1 · DUBL 1")
    A["qozon"] = stove_qozon()
    A["kcounter"] = counter_front()
    A["board"] = cutting_board(400, 70)
    A["onion"] = onion_whole(56); A["onion_half"] = onion_half(56); A["ring"] = onion_ring(24)
    A["ccounter"] = cash_counter(1560, 640)
    A["register"] = register_img(320, 270)
    A["candy"] = candy_bowl(80)
    A["comment"] = comment_bubble(420, 250)
    A["card"] = mystery_card(440, 580)
    A["card_title"] = [text_img(s, 60, fill=YELLOW, stroke=8) for s in ("AGAR BLOGER", "BOʻLMAGANIDA")]
    A["plane"] = paper_plane(150)
    A["bubble"] = {k: phone_screen_bubble(420, 560, k / 8) for k in range(9)}
    A["head"] = {k: headline_img(v) for k, v in HEADLINES.items()}
    # hall composites
    hall = A["hall"].copy().convert("RGBA")
    for x, flip in ((-60, False), (1040, False)):
        t, ax, ay, ty = A["table_s"]
        for dx in (-170, 170):
            ch = A["chair_s"]; paste(hall, ch, x + dx - ch.width / 2 - HL_OX, 1395 - ch.height - HL_OY)
        paste(hall, t, x - ax - HL_OX, 1420 - ay - HL_OY)
        pl, pcx, pcy = A["plate"]
        sm = pl.resize((int(pl.width * 0.6), int(pl.height * 0.6)), Image.LANCZOS)
        paste(hall, sm, x - sm.width / 2 - HL_OX, 1420 - (ay - ty) - sm.height * 0.45 - HL_OY)
    A["hall_bg"] = hall.convert("RGB")
    # exterior composite (plants baked)
    ext = A["ext"].copy().convert("RGBA")
    for x in (470, 990):
        p = A["plant"]; paste(ext, p, x - p.width / 2 - EX_OX, 1525 - p.height - EX_OY)
    A["ext_bg"] = ext.convert("RGB")
    # kitchen composite (stove + qozon)
    kt = A["kitchen"].copy().convert("RGBA")
    q = A["qozon"]; paste(kt, q, -70 - KT_OX, COUNTER_TOP + 20 - q.height - KT_OY)
    A["kitchen_bg"] = kt.convert("RGB")
    cd = A["cash"].copy().convert("RGBA")
    A["cash_bg"] = cd.convert("RGB")

# ---------------------------------------------------------------- hall helpers
def table_at(world, x, floor_y, ox, oy, which="table"):
    t, ax, ay, ty = A[which]
    paste(world, t, x - ax - ox, floor_y - ay - oy)
    return floor_y - (ay - ty)          # world y of the table-top centre

def table_top_y(which="table", floor_y=TABLE_FLOOR):
    t, ax, ay, ty = A[which]; return floor_y - (ay - ty)

def plate_at(world, x, top_y, ox, oy, which="plate", dy=0.0, rot=0.0):
    pl, pcx, pcy = A[which]
    if abs(rot) > 0.1:
        place(world, pl, x, top_y - 4 + dy, rot=rot, ox=ox, oy=oy)
    else:
        paste(world, pl, x - pcx - ox, top_y - pcy - 4 + dy - oy)

def curtains(frame, sway=0.0, t=0.0, valance_on=True, par=0.0):
    """screen-space theatre curtains at both frame edges + top valance"""
    for side in ("L", "R"):
        im = A["curt" + side]
        if abs(sway) > 0.01:
            amp = sway * 14 * math.sin(t * 2.4 + (0 if side == "L" else 1.3))
            im = im.transform(im.size, Image.AFFINE, (1, amp / im.height, -amp * 0.0, 0, 1, 0), resample=Image.BICUBIC)
        x = -34 + par if side == "L" else W - im.width + 34 + par
        frame.paste(im, (int(x), -20), im)
    if valance_on:
        v = A["valance"]
        frame.paste(v, (int(-50 + par * 0.5), -28), v)

def spots(world, on, ox, oy, aim=None):
    for j, (x, y) in enumerate(SPOTS):
        im = A["spot_on"] if on > 0.5 else A["spot_off"]
        paste(world, im, x - im.width / 2 - ox, y - oy)

def beam_to(world, src, dst, alpha, ox, oy):
    """light cone from src (fixture) to dst (floor target)"""
    if alpha <= 0.01: return
    bm = A["beam"]
    dx, dy = dst[0] - src[0], dst[1] - src[1]
    L = math.hypot(dx, dy)
    ang = math.degrees(math.atan2(dx, dy))
    b = bm.resize((bm.width, max(10, int(L))), Image.BICUBIC)
    big = Image.new("RGBA", (b.width * 3, b.height * 2 + 10), (0, 0, 0, 0))
    big.paste(b, (b.width, b.height))
    r = big.rotate(ang, resample=Image.BICUBIC, center=(b.width * 1.5, b.height))
    r = with_alpha(r, alpha)
    paste(world, r, src[0] - r.width / 2 - ox, src[1] - r.height / 2 - oy)
    pl = A["pool"]
    paste(world, with_alpha(pl, alpha), dst[0] - pl.width / 2 - ox, dst[1] - pl.height / 2 - oy)

def darken_img(img, f):
    if f >= 0.999: return img
    return Image.fromarray((np.asarray(img).astype(np.float32) * f).astype(np.uint8))

# ---------------------------------------------------------------- scene 1 (also the loop's last frame)
S1_W = dict(x=300, yb=1800)       # kneeling waiter
S1_B = dict(x=815, yb=1800)       # Bobur pose 5
KH = 0.92                         # hall scale: sheet sprites k, code-drawn characters H = 1000 * KH
HH = int(1000 * KH)
def waiter_kneel_P(mo, blink, fold_sc=1.0, t=0.0):
    return dict(pose="kneel", L=(0.12, -0.3), R=(0.36, -0.32), hkL="fist", hkR="fist",
                face=dict(eyes="sparkle", brows="sad", mouth="o" if mo > 0 else "smile", mo=mo, gaze=(0.5, -0.35), blink=blink),
                folder=[round(0.9 * fold_sc, 3), 0.03, -0.03, 0.0])

def s1_world(i, k, lf, t, still=False):
    world = A["hall_bg"].copy()
    spots(world, 0, HL_OX, HL_OY)
    # Bobur, shocked
    sy = 1.0 if still else breathe(t)
    sheet(world, "bobur", 5, S1_B["x"], S1_B["yb"], HL_OX, HL_OY, k=KH, sy=sy)
    # waiter: folder pops forward on "oling"
    fo = word_frame([w for w in scene_words(1) if w["text"].startswith("oling")][0]) - SC_FRAME[1]
    fs = 1.0
    if not still and lf >= fo:
        d = (lf - fo) / FPS
        fs = 1.0 + 0.14 * math.exp(-d * 7) * math.cos(d * 22)
    mo = 0.0 if still else mouth_amt(i, k)
    bl = 0.0 if still else blink_amt(t, 11)
    P = waiter_kneel_P(mo, bl, fs)
    pts = put_person(world, "waiter", HH, S1_W["x"], S1_W["yb"], HL_OX, HL_OY, **P)
    if not still:
        hx, hy = pts["head"]
        sparkles(world, [(S1_W["x"] + hx - 150, S1_W["yb"] + hy - 90), (S1_W["x"] + hx + 140, S1_W["yb"] + hy - 130)], t, HL_OX, HL_OY, scale=0.7)
    return world

def s1_cam(lf, lt):
    if lf <= 8:
        p = ease_out_cubic(lf / 8.0)
        return 1.0 + 0.10 * p, 540 + 12 * p, 960 + 40 * p
    q = lt - 8 / FPS
    return 1.10 + 0.025 * q, 552 + 5 * q, 1000 - 6 * q

def s1(i, k, t, lf, lt, dur):
    world = s1_world(i, k, lf, t, still=(lf == 0))
    z, cx, cy = s1_cam(lf, lt)
    fo = word_frame([w for w in scene_words(1) if w["text"].startswith("oling")][0]) - SC_FRAME[1]
    sx_, sy_ = shake_xy(lf - fo, 5, 6, seed=1)
    fr = camera(world, HL_OX, HL_OY, cx, cy, z, 0, sx_, sy_)
    curtains(fr, 0.0, t)
    return fr

def s1_frame0():
    """exact scene-1 frame-0 composition (used for the seamless loop)"""
    world = s1_world(0, 1, 0, 0.0, still=True)
    fr = camera(world, HL_OX, HL_OY, 540, 960, 1.0)
    curtains(fr, 0.0, 0.0)
    return fr

# ---------------------------------------------------------------- blogger set helpers
ZB = 0.8
BYB = 1770
def blogger(world, pose, x, i, k, t, rot=0.0, extra_sy=1.0, still=False):
    sy = (1.0 if still else breathe(t)) * extra_sy * talk_sy(i, k)
    return sheet(world, "bobur", pose, x, BYB, BL_OX, BL_OY, k=1.25, sy=sy, rot=rot)

def phone_on(world, dx=0):
    paste(world, A["phone"], A["phone_x"] + dx - BL_OX, A["phone_y"] - BL_OY)

def s2(i, k, t, lf, lt, dur):
    world = A["blog"].copy()
    blogger(world, 3, 540, i, k, t)
    phone_on(world)
    z = ZB * (1 + 0.06 * ease_in_out_sine(lt / dur))
    cx = 540 + 14 * math.sin(2 * math.pi * lt / 2.6); cy = 670 + 6 * math.sin(2 * math.pi * lt / 1.9)
    fr = camera(world, BL_OX, BL_OY, cx, cy, z, 0.5 * math.sin(2 * math.pi * lt / 2.8))
    if lt < 0.3: fr = vhs(fr, lt / 0.3, seed=i)
    return fr

def ripple(frame, p, t, amp=16):
    import cv2
    if p <= 0.01: return frame
    a = np.asarray(frame)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rho = np.maximum(np.abs(xx - 540) / 540, np.abs(yy - 960) / 960)
    front = 1 - 0.6 * p
    wgt = np.clip((rho - front) / 0.28, 0, 1) ** 1.3
    dx = amp * wgt * np.sin(yy * 0.022 + t * 7.0)
    dy = amp * 0.5 * wgt * np.sin(xx * 0.03 + t * 5.0)
    out = cv2.remap(a, xx + dx, yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # lilac tint at the rippling edges
    tint = (wgt * 0.25 * p)[..., None]
    out = out.astype(np.float32) * (1 - tint) + np.array(DREAM, np.float32) * tint
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

def warm(frame, k):
    if k <= 0.01: return frame
    a = np.asarray(frame).astype(np.float32)
    a *= np.array([1 + 0.07 * k, 1 + 0.015 * k, 1 - 0.08 * k], np.float32)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

THOUGHT_XY = (860, 330)
def s3(i, k, t, lf, lt, dur):
    world = A["blog"].copy()
    name, h = blogger(world, 4, 540, i, k, t)
    phone_on(world)
    hx, hy = sprite_point(name, 0.5, 0.18, 540, BYB, h)
    # lilac clouds swirl in, then gather into the thought bubble
    g = clamp01((lt - 0.05) / 0.75)
    for j, cl in enumerate(A["clouds"]):
        a0 = j * 2 * math.pi / 7 + lt * 2.6
        r = lerp(560, 120, ease_in_out(g))
        x = lerp(hx + r * math.cos(a0), THOUGHT_XY[0], ease_in_cubic(g))
        y = lerp(hy + 0.55 * r * math.sin(a0) - 60, THOUGHT_XY[1], ease_in_cubic(g))
        al = clamp01(lt / 0.2) * (1 - clamp01((g - 0.85) / 0.15))
        if al > 0.02: place(world, cl, x, y, scale=lerp(1.0, 0.5, g), alpha=al, ox=BL_OX, oy=BL_OY)
    bp = clamp01((lt - 0.55) / 0.3)
    if bp > 0:
        sc = ease_out_back(bp, 2.0)
        for q, (fx, rr) in enumerate(((0.25, 22), (0.5, 34))):
            px, py = lerp(hx + 70, THOUGHT_XY[0] - 120, fx), lerp(hy - 160, THOUGHT_XY[1] + 170, fx)
            c = SS(rr * 2 + 12, rr * 2 + 12, 3); c.circle(rr + 6, rr + 6, rr, fill=(255, 255, 255), outline=OL, width=5)
            place(world, c.result(), px, py, scale=clamp01(bp * 2 - q * 0.4), ox=BL_OX, oy=BL_OY)
        tb = A["thought"]
        place(world, tb, THOUGHT_XY[0], THOUGHT_XY[1] + 6 * math.sin(lt * 4), scale=0.85 * max(0.02, sc), ox=BL_OX, oy=BL_OY)
    z = ZB * (1 + 0.08 * ease_in_out_sine(lt / dur))
    cx = 540 + 10 * math.sin(lt * 2.2); cy = 660 + 10 * math.sin(lt * 1.7)
    fr = camera(world, BL_OX, BL_OY, cx, cy, z)
    fr = warm(fr, clamp01(lt / 0.6))
    fr = ripple(fr, clamp01(lt / 0.5), t)
    rem = SC_END_FRAME[k] - i
    if rem <= 3:
        sx, sy = to_screen(THOUGHT_XY[0], THOUGHT_XY[1], cx, cy, z)
        puff_screen(fr, 0.2 * (4 - rem) / 4, (sx + 560) / 2, (sy + 1300) / 2, 1050)
    return fr

# ---------------------------------------------------------------- exterior (scenes 4, 12, 13)
EB = dict(x=300, yb=1790)
def ext_world(sign="on", flicker=None):
    world = A["ext_bg"].copy()
    s = A["sign_" + sign]
    paste(world, s, EX_SIGN[0] - EX_OX, EX_SIGN[1] - EX_OY)
    return world

def s4(i, k, t, lf, lt, dur):
    lit_seq = [0, 0, 0, 0, 0, 0, 0, 0, 1, 0.2, 1, 0.45, 1, 1]
    lv = lit_seq[lf] if lf < len(lit_seq) else 1
    world = ext_world("on" if lv > 0.7 else ("mid" if lv > 0.3 else "off"))
    name, h = sheet(world, "bobur", 7, EB["x"], EB["yb"], EX_OX, EX_OY, sy=breathe(t))
    if lt > 0.25:
        tx, ty = sprite_point(name, 0.12, 0.43, EB["x"], EB["yb"], h)
        sparkles(world, [(tx - 80, ty - 70), (tx + 60, ty - 110), (tx - 60, ty + 60), (tx + 90, ty + 10)], lt, EX_OX, EX_OY, scale=min(1, (lt - 0.25) / 0.15))
    q = clamp01(lt / 0.55)
    z = 1.15 - 0.15 * ease_out_back(q, 2.2)
    fr = camera(world, EX_OX, EX_OY, 540, 1000 - 30 * q, z)
    if lf < 6: pp = 0.2 + 0.35 * lf / 6
    else: pp = 0.55 + 0.45 * clamp01((lf - 6) / 8.0)
    puff_screen(fr, pp, 560, 1250, 1050)
    return fr

# ---------------------------------------------------------------- scene 5: customer walks in
TA_X = 720
def door_open_layer(world, op, ox, oy):
    """doorway shows the bright street; the glass panel swings (narrows) on its left hinge"""
    x0, y0, x1, y1 = DOOR
    if op <= 0.01: return
    c = SS(x1 - x0, y1 - y0, 2)
    c.rect((0, 0, x1 - x0, y1 - y0), fill=(200, 232, 252), outline=OL, width=6)
    c.rect((0, (y1 - y0) * 0.72, x1 - x0, y1 - y0), fill=(214, 210, 202), outline=None, width=0)
    c.rect((40, (y1 - y0) * 0.35, 160, (y1 - y0) * 0.72), fill=(226, 196, 150), outline=OL, width=4)
    c.rect((0, 0, x1 - x0, y1 - y0), fill=None, outline=OL, width=6)
    paste(world, c.result(), x0 - ox, y0 - oy)
    wd = max(30, int((x1 - x0) * (1 - 0.8 * op)))
    p = SS(wd, y1 - y0, 2)
    p.rect((3, 3, wd - 3, y1 - y0 - 3), fill=(196, 230, 250), outline=OL, width=6)
    p.rect((wd * 0.08 + 4, 24, wd * 0.92 - 4, y1 - y0 - 120), fill=(214, 238, 252), outline=OL, width=4)
    p.rect((wd * 0.8 - 6, (y1 - y0) / 2 - 10, wd * 0.8 + 8, (y1 - y0) / 2 + 90), fill=GOLD, outline=OL, width=4, r=6)
    paste(world, p.result(), x0 - ox, y0 - oy)

def bell(world, ang, ox, oy):
    if "bell" not in A:
        c = SS(90, 120, 3)
        c.line([(45, 0), (45, 24)], fill=OL, width=5)
        c.poly([(18, 86), (24, 44), (45, 24), (66, 44), (72, 86)], fill=(242, 190, 50), outline=OL, width=5)
        c.rect((10, 80, 80, 94), fill=(230, 170, 40), outline=OL, width=5, r=6)
        c.circle(45, 102, 10, fill=(200, 140, 30), outline=OL, width=4)
        A["bell"] = c.result()
    b = A["bell"]
    big = Image.new("RGBA", (b.width * 2, b.height * 2), (0, 0, 0, 0)); big.paste(b, (b.width // 2, b.height))
    r = big.rotate(ang, resample=Image.BICUBIC, center=(b.width, b.height))
    paste(world, r, BELL_XY[0] - r.width / 2 - ox, BELL_XY[1] - r.height / 2 - oy)

def s5(i, k, t, lf, lt, dur):
    world = A["hall_bg"].copy()
    spots(world, 0, HL_OX, HL_OY)
    op = ease_out_cubic(clamp01(lt / 0.3)) * (1 - ease_in_out(clamp01((lt - 0.95) / 0.35)))
    door_open_layer(world, op, HL_OX, HL_OY)
    bell(world, 26 * damped(lt, 3.2, 3.0), HL_OX, HL_OY)
    # customer walks from the doorway to the table (perspective scale), then sits behind it
    p = clamp01((lt - 0.08) / 0.92)
    pe = ease_in_out(p)
    tt = table_top_y()
    seat_top = tt - 0.55 * HS("cust_02", KH)
    x = lerp(1430, TA_X, pe)
    sc = lerp(0.58, KH, pe)
    yb_walk = lerp(1205, seat_top + HS("cust_02", KH) - 40, pe)
    hop = abs(math.sin(math.pi * 4 * p)) * 40 * (1 - p) if p < 1 else 0
    sit = ease_out_back(clamp01((lt - 1.0) / 0.2), 1.5)
    yb = yb_walk - hop + 40 * sit
    sh_ = soft_shadow(300 * sc, 40 * sc, 0.22)
    if p < 0.98: paste(world, sh_, x - sh_.width / 2 - HL_OX, yb_walk + 40 * sit - sh_.height / 2 - HL_OY)
    sheet(world, "cust", 2, x, yb, HL_OX, HL_OY, k=sc, sy=talk_sy(i, k) * (1 - 0.03 * sit * (1 - clamp01((lt - 1.2) / 0.1))))
    table_at(world, TA_X, TABLE_FLOOR, HL_OX, HL_OY)
    for dx in (-150, 150):
        pass
    plate_at(world, TA_X - 30, tt, HL_OX, HL_OY)
    cx = lerp(1250, 700, ease_in_out(clamp01((lt - 0.05) / 1.05)))
    fr = camera(world, HL_OX, HL_OY, cx, 990, 0.92)
    curtains(fr, 0.0, t)
    return fr

# ---------------------------------------------------------------- scene 6: the waiters are actors
TRIO = [("waiter", 175, "smile"), ("waiter2", 545, "cry"), ("waiter3", 915, "wow")]
H6 = 860
def s6(i, k, t, lf, lt, dur):
    world = A["hall_bg"].copy()
    t_snap = word_t(6, "ofitsiant")
    t_akt = word_t(6, "aktyor")
    on = lt >= t_snap
    snap = clamp01((lt - t_snap) * FPS / 2)
    if on: world = darken_img(world, lerp(1.0, 0.72, clamp01((lt - t_snap) / 0.25)))
    spots(world, 1 if on else 0, HL_OX, HL_OY)
    # beams sweep from the floor edges onto the row
    if on:
        sw = ease_out_cubic(clamp01((lt - t_snap) / 0.5))
        for j, (sx, sy) in enumerate(SPOTS):
            tgt = (lerp(-250 if j == 0 else 1350, [175, 915][j], sw), 1760)
            beam_to(world, (sx, sy + 170), tgt, 0.9, HL_OX, HL_OY)
        beam_to(world, (540, -300), (545, 1760), 0.5 * sw, HL_OX, HL_OY)
    bow = 0.0
    if lt >= t_akt:
        bq = clamp01((lt - t_akt) / 0.5)
        bow = math.sin(math.pi * bq) * 0.02
    for j, (look, x, mask) in enumerate(TRIO):
        sway = 0.012 * math.sin(lt * 3 + j)
        if not on:
            face = dict(dx=0.05, gaze=(0.8, 0.0), mouth="smile", blink=blink_amt(t, 20 + j))
            P = dict(R=(0.3, -0.3), hkR="open", props={"R": ["tray", "over"]}, L=(-0.22, 0.0), face=face, head_dx=0.01, bob=round(-sway, 3))
        else:
            up = ease_out_back(clamp01((lt - t_snap) / 0.15), 2.0)
            mouth = {"smile": "grin", "cry": "sad", "wow": "o"}[mask]
            brows = {"smile": "up", "cry": "sad", "wow": "up"}[mask]
            ov = -0.02 * (1 - snap)
            face = dict(dx=ov, gaze=(0.0, 0.0), mouth=mouth, mo=0.6 if mouth in ("grin", "o") else 0.0, brows=brows, blink=blink_amt(t, 20 + j))
            P = dict(R=(0.3, -0.3), hkR="open", props={"R": ["tray", "over"], "L": ["mask:" + mask, "under", round(1.5 * up, 2)]},
                     L=(round(lerp(-0.22, -0.1, up), 3), round(lerp(0.0, -0.58, up), 3)), face=face, bob=round(-sway + bow, 3), head_dy=round(bow * 2, 3))
        put_person(world, look, H6, x, 1760, HL_OX, HL_OY, **P)
    q = ease_in_out_sine(lt / dur)
    fr = camera(world, HL_OX, HL_OY, lerp(470, 620, q), 1060, 0.86)
    curtains(fr, 1.0, t * 1.3, par=-12 * q)
    return fr

# ---------------------------------------------------------------- scene 7: side wide shot of the begging
S7 = dict(table=190, bob=940, w0=420, w1=610)
def s7(i, k, t, lf, lt, dur):
    world = A["hall_bg"].copy()
    spots(world, 0, HL_OX, HL_OY)
    fo = word_frame([w for w in scene_words(7) if w["text"].startswith("oling")][0]) - SC_FRAME[7]
    freeze = fo <= lf < fo + 6
    lt_e = (fo / FPS) if freeze else (lt if lf < fo else lt - 6 / FPS)
    tt = table_top_y()
    # customer: shrug at the table with an empty plate
    sheet(world, "cust", 8, S7["table"] - 10, tt - 0.55 * HS("cust_08", KH) + HS("cust_08", KH), HL_OX, HL_OY, k=KH, sy=1.0 if freeze else breathe(t, ph=1))
    table_at(world, S7["table"], TABLE_FLOOR, HL_OX, HL_OY)
    plate_at(world, S7["table"], tt, HL_OX, HL_OY)
    # Bobur shocked on the right
    sheet(world, "bobur", 5, S7["bob"], 1800, HL_OX, HL_OY, k=KH, sy=1.0 if freeze else breathe(t))
    # waiter walks in front of the customer, then drops to one knee before Bobur
    wp = clamp01((lt_e - 0.15) / 0.75)
    mo = 0.0 if freeze else mouth_amt(i, k)
    bl = 0.0 if freeze else blink_amt(t, 13)
    if lt_e < 0.95:
        x = lerp(S7["w0"], S7["w1"], ease_in_out(wp))
        P = dict(walk=round((lt_e * 2.2) % 1, 2), L=(-0.22, round(0.03 * math.sin(lt_e * 14), 3)), R=(0.22, round(-0.03 * math.sin(lt_e * 14), 3)),
                 face=dict(dx=0.04, gaze=(0.7, -0.2), mouth="o" if mo > 0 else "smile", mo=mo, brows="sad", blink=bl))
        put_person(world, "waiter", HH, x, 1800, HL_OX, HL_OY, **P)
    else:
        kq = clamp01((lt_e - 0.95) / 0.2)
        fs = 1.0 + 0.12 * (1 - kq)
        P = waiter_kneel_P(mo, bl, 1.0)
        P["L"] = (round(lerp(-0.1, 0.12, kq), 3), round(lerp(-0.1, -0.3, kq), 3)); P["R"] = (round(lerp(0.15, 0.36, kq), 3), round(lerp(-0.12, -0.32, kq), 3))
        put_person(world, "waiter", HH, S7["w1"], 1800 + 18 * (1 - ease_out_cubic(kq)), HL_OX, HL_OY, **P)
    z = 0.8
    if lf < 6:
        cxa = lerp(1500, 600, ease_out_cubic(lf / 6)); cxb = lerp(1500, 600, ease_out_cubic((lf + 0.9) / 6))
        fr = motion_blur_cam(world, HL_OX, HL_OY, [lerp(cxa, cxb, q / 5) for q in range(6)], 1040, z, -1.0)
    else:
        sx_, sy_ = shake_xy(lf - fo, 6, 6, seed=7) if lf >= fo else (0, 0)
        drift = (lf - 6) / FPS
        fr = camera(world, HL_OX, HL_OY, 600 + 12 * drift, 1040, z + 0.01 * drift, -1.0, sx_, sy_)
    curtains(fr, 0.0, t)
    if freeze and lf - fo < 3: fr = flash(fr, 0.25 * (1 - (lf - fo) / 3))
    return fr

# ---------------------------------------------------------------- scene 8: the chef cries on camera
CHEF_X, CHEF_FEET = 560, 1700
def steam(world, lt, ox, oy, x0=180, y0=1060):
    for j in range(5):
        ph = (lt * 0.6 + j / 5) % 1
        x = x0 + 40 * math.sin(ph * 6 + j) + (j - 2) * 30
        y = y0 - ph * 420
        r = 30 + ph * 50
        al = math.sin(math.pi * ph) * 0.6
        c = SS(r * 2 + 4, r * 2 + 4, 2); c.circle(r + 2, r + 2, r, fill=(255, 255, 255, 255), outline=None, width=0)
        place(world, c.result(), x, y, alpha=al, ox=ox, oy=oy)

def tear_streams(world, hx, hy, H, g, lt, ox, oy):
    """two comic tear streams arcing out of the eyes; g 0..1 growth"""
    for sgn in (-1, 1):
        ex, ey = hx + sgn * 0.074 * H, hy + 0.03 * H
        n = 16
        L = g
        pts = []
        for q in np.linspace(0, L, n):
            x = ex + sgn * (q * 330)
            y = ey - 40 * math.sin(math.pi * q * 0.9) * (1 if q < 0.5 else 1) + q * q * 520
            x += 6 * math.sin(lt * 20 + q * 9)
            pts.append((x, y))
        if len(pts) < 2 or L < 0.03: continue
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        x0, y0 = min(xs) - 60, min(ys) - 60
        c = SS(max(xs) - x0 + 60, max(ys) - y0 + 60, 2)
        loc = [(x - x0, y - y0) for x, y in pts]
        w = 24 + 14 * g
        c.line(loc, fill=OL, width=w + 12)
        c.line(loc, fill=(120, 196, 255), width=w)
        c.line([(x - 4, y - 5) for x, y in loc[:len(loc) * 2 // 3]], fill=(214, 240, 255), width=w * 0.3)
        lx, ly = loc[-1]
        c.circle(lx, ly + 6, w * 0.7, fill=(120, 196, 255), outline=OL, width=6)
        paste(world, c.result(), x0 - ox, y0 - oy)

def tear_drops(world, hx, hy, H, lt, ox, oy, n=3):
    for sgn in (-1, 1):
        for j in range(n):
            ph = (lt * 1.6 + j / n) % 1
            x = hx + sgn * (0.074 * H + 0.03 * H)
            y = hy + 0.05 * H + ph * 160
            c = SS(40, 54, 3)
            c.poly([(20, 2), (34, 30), (20, 50), (6, 30)], fill=(120, 196, 255), outline=OL, width=4)
            c.circle(20, 34, 13, fill=(120, 196, 255), outline=None, width=0)
            place(world, c.result(), x, y, alpha=1 - ph, ox=ox, oy=oy)

def s8(i, k, t, lf, lt, dur):
    world = A["kitchen_bg"].copy().convert("RGBA")
    steam(world, lt, KT_OX, KT_OY)
    t_cam = word_t(8, "kameraga")
    chops = [0.12, 0.45, 0.78]
    # knife height: raised, quick chop down at each chop time
    kh = 0.0
    for c0 in chops:
        d = lt - c0
        if -0.16 < d <= 0: kh = max(kh, ease_out_cubic((d + 0.16) / 0.16))
        elif 0 < d < 0.12: kh = max(kh, 1 - ease_in_cubic(d / 0.12))
    if lt > chops[-1] + 0.12: kh = 0.0
    kh_q = round(kh * 6) / 6
    turn = ease_in_out(clamp01((lt - t_cam) / 0.45))
    H_ = 1000
    face = dict(dy=round(0.03 * (1 - turn), 3), eyes="down" if turn < 0.5 else "normal", brows="sad",
                mouth="quiver" if turn > 0.3 else "sad", t=round(lt, 2) if turn > 0.3 else 0.0, blink=blink_amt(t, 31) if turn > 0.6 else 0.0)
    bx, by = -0.1, -0.5
    P = dict(R=(0.14, round(-0.53 - 0.13 * kh_q, 3)), L=(-0.16, -0.5), rel=False, hkR="fist", hkL="fist",
             props={"R": ["knife:%d" % int(195 - 25 * kh_q), "under"], "L": ["onion", "over"]}, face=face, head_dy=round(0.025 * (1 - turn), 3))
    pts = put_person(world, "chef", H_, CHEF_X, CHEF_FEET, KT_OX, KT_OY, **P)
    paste(world, A["kcounter"], -340 - KT_OX, COUNTER_TOP - 20 - KT_OY)
    b = A["board"]; paste(world, b, CHEF_X - 140 - b.width / 2 - KT_OX + 60, COUNTER_TOP - 52 - KT_OY)
    # arms again above the board (cropped below the counter line)
    Pa = dict(P); Pa["layer"] = "arms"
    img, ax, ay, _ = person("chef", H_, pkey(**Pa))
    cut = int(ay - (CHEF_FEET - (COUNTER_TOP - 140)))
    crop = img.crop((0, max(0, cut), img.width, img.height))
    paste(world, crop, CHEF_X - ax - KT_OX, CHEF_FEET - ay + max(0, cut) - KT_OY)
    # onion rings fly at each chop
    ring = A["ring"]
    for j, c0 in enumerate(chops):
        d = lt - c0
        if 0 <= d < 0.9:
            for q in range(3):
                vx = (-260 + 180 * q) * (1 + 0.3 * j); vy = -640 - 90 * q
                x = CHEF_X - 80 + vx * d; y = COUNTER_TOP - 70 + vy * d + 1500 * d * d
                place(world, ring, x, y, rot=(d * 600 + q * 50) % 360, scale=0.9 + 0.2 * q, alpha=clamp01(1.5 - d * 1.8), ox=KT_OX, oy=KT_OY)
    # tears: drops, then streams
    hx, hy = CHEF_X + pts["head"][0], CHEF_FEET + pts["head"][1] + 0.03 * H_ * (1 - turn)
    if lt > 0.3: tear_drops(world, hx, hy, H_, lt, KT_OX, KT_OY)
    g = clamp01((lt - 0.75) / 0.8)
    if g > 0: tear_streams(world, hx, hy, H_, g, lt, KT_OX, KT_OY)
    world = world.convert("RGB")
    sp = clamp01((lt - t_cam) / 0.35)
    if sp > 0:
        if "kdim" not in A:
            A["kdim"] = np.asarray(dim(Image.new("RGB", world.size, (255, 255, 255)), KT_OX, KT_OY, (CHEF_X, 900), 380, floor=0.6, vignette=0.3)).astype(np.float32) / 255
        m = 1 - sp * (1 - A["kdim"])
        world = Image.fromarray(np.clip(np.asarray(world).astype(np.float32) * m, 0, 255).astype(np.uint8))
    z = 1.0 + 0.12 * ease_in_out_sine(lt / dur)
    return camera(world, KT_OX, KT_OY, 560, 1000 - 60 * ease_in_out_sine(lt / dur), z)

# ---------------------------------------------------------------- scene 9: the cashier's monologue
REG_X = 40
def tape_path():
    sx, sy = REG_X + 10 + 320 * 0.83, CD_TOP + 20 - 270 + 10 + 270 * 0.06
    pts = [(sx, sy), (sx + 10, sy - 50), (sx + 60, sy - 80), (sx + 120, sy - 40), (sx + 150, sy + 60), (sx + 170, CD_TOP - 10),
           (sx + 200, CD_TOP + 60), (sx + 205, 1700), (sx + 200, 1880), (sx + 260, 1940), (sx + 520, 1955), (sx + 780, 1950), (sx + 900, 1925), (sx + 930, 1880),
           (sx + 880, 1850), (sx + 830, 1880)]
    # densify
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 12))
        for q in range(n): out.append((lerp(a[0], b[0], q / n), lerp(a[1], b[1], q / n)))
    out.append(pts[-1])
    return out
TAPE = None
def draw_tape(world, L, ox, oy):
    global TAPE
    if TAPE is None: TAPE = tape_path()
    acc = 0.0; pts = [TAPE[0]]
    for a, b in zip(TAPE[:-1], TAPE[1:]):
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        if acc + d > L:
            f = (L - acc) / d; pts.append((lerp(a[0], b[0], f), lerp(a[1], b[1], f))); break
        acc += d; pts.append(b)
    if len(pts) < 2: return
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, y0 = min(xs) - 70, min(ys) - 70
    c = SS(max(xs) - x0 + 70, max(ys) - y0 + 70, 2)
    loc = [(x - x0, y - y0) for x, y in pts]
    c.line(loc, fill=OL, width=78)
    c.line(loc, fill=(252, 252, 248), width=66)
    # grey "script" lines across the tape
    rnd = random.Random(5)
    acc = 0.0
    for a, b in zip(loc[:-1], loc[1:]):
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        if d < 1e-3: continue
        ux, uy = (b[0] - a[0]) / d, (b[1] - a[1]) / d
        nx, ny = -uy, ux
        s = acc
        while s < acc + d:
            if int(s) % 22 == 0 or (s - acc) < 1e-6 and False: pass
            s += 30
            if s > acc + d: break
            f = (s - acc) / d
            px, py = lerp(a[0], b[0], f), lerp(a[1], b[1], f)
            ln = rnd.uniform(0.35, 0.9) * 24
            c.line([(px - nx * 22, py - ny * 22), (px - nx * 22 + nx * ln * 1.8, py - ny * 22 + ny * ln * 1.8)], fill=(120, 126, 136), width=8)
        acc += d
    paste(world, c.result(), x0 - ox, y0 - oy)

def s9(i, k, t, lf, lt, dur):
    world = A["cash_bg"].copy().convert("RGBA")
    cc = A["ccounter"]; paste(world, cc, -120 - CD_OX, CD_TOP - 46 - CD_OY)
    r = A["register"]; paste(world, r, REG_X - CD_OX, CD_TOP + 20 - r.height - CD_OY)
    cb = A["candy"]; paste(world, cb, 960 - cb.width / 2 - CD_OX, CD_TOP + 26 - cb.height - CD_OY)
    draw_tape(world, 260 + 1650 * ease_out_cubic(clamp01(lt / 2.2)), CD_OX, CD_OY)
    # cashier on the counter, slow dramatic mime (not word-synced)
    mo = 0.5 + 0.5 * math.sin(2 * math.pi * lt / 0.9 - math.pi / 2)
    mo = round(mo * 4) / 4
    arm_up = 0.04 * math.sin(lt * 2.0)
    P = dict(L=(-0.02, -0.56), R=(0.3, round(-0.88 + arm_up, 3)), rel=False, hkL="open", hkR="open",
             face=dict(eyes="half", brows="up", mouth="open" if mo > 0.1 else "flat", mo=mo, gaze=(0.0, -0.4), blink=0.0),
             head_dx=0.0, bob=round(0.006 * math.sin(lt * 3), 3))
    put_person(world, "cashier", 1000, 640, CD_TOP + 14, CD_OX, CD_OY, rot=-2.0 * math.sin(lt * 1.6), **P)
    world = world.convert("RGB")
    q = ease_in_out_sine(clamp01(lt / dur))
    fr = camera(world, CD_OX, CD_OY, lerp(560, 600, q), lerp(1560, 660, q), lerp(1.12, 0.98, q), 0)
    curtains(fr, 0.0, t, valance_on=True)
    return fr

# ---------------------------------------------------------------- scene 10: angry customer
TB_X = 540
def s10(i, k, t, lf, lt, dur):
    world = A["hall_bg"].copy()
    spots(world, 0, HL_OX, HL_OY)
    t_hit = word_t(10, "keldim")
    tt = table_top_y()
    hdisp = HS("cust_12")
    top = tt - 0.66 * hdisp
    d = lt - t_hit
    drop = 0.0; sq = 1.0
    if -0.1 < d < 0: drop = -20 * (d + 0.1) / 0.1 * 0
    if d >= 0:
        drop = 44 * math.exp(-d * 9) * (1 if d > 0.03 else d / 0.03)
        sq = 1 - 0.05 * math.exp(-d * 10)
    shiver = 3 * math.sin(lt * 60) if d < 0 else 0
    sheet(world, "cust", 12, TB_X + shiver, top + hdisp + drop, HL_OX, HL_OY, sy=sq * talk_sy(i, k))
    table_at(world, TB_X, TABLE_FLOOR, HL_OX, HL_OY)
    jump = 0.0; rot = 0.0
    if d >= 0:
        jump = -120 * max(0, math.sin(math.pi * min(1, d / 0.32))) - 30 * max(0, math.sin(math.pi * min(1, max(0, d - 0.32) / 0.16)))
        rot = 18 * math.sin(d * 16) * math.exp(-d * 5)
    plate_at(world, TB_X, tt, HL_OX, HL_OY, dy=jump, rot=rot * 0.4)
    place(world, A["fork"], TB_X - 170, tt - 40 + jump * 1.2, rot=80 + rot * 2, ox=HL_OX, oy=HL_OY)
    place(world, A["spoon"], TB_X + 170, tt - 40 + jump * 1.1, rot=-80 - rot * 2.2, ox=HL_OX, oy=HL_OY)
    # red anger marks pop beside his head on the hit
    if d >= 0 and d < 0.6:
        if "anger" not in A:
            c = SS(130, 130, 3)
            for ang in (45, 135, 225, 315):
                r0, r1 = 18, 56
                ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                pts = [(65 + r0 * ca - 16 * sa, 65 + r0 * sa + 16 * ca), (65 + r1 * ca, 65 + r1 * sa), (65 + r0 * ca + 16 * sa, 65 + r0 * sa - 16 * ca)]
                c.line(pts, fill=OL, width=20); c.line(pts, fill=SOLD, width=11)
            A["anger"] = c.result()
        q = clamp01(d / 0.6)
        sc = ease_out_back(clamp01(d / 0.12), 2.5) * (1 - 0.3 * q)
        for j, sg in enumerate((-1, 1)):
            place(world, A["anger"], TB_X + sg * 190, top + 70 - 30 * q, scale=max(0.02, sc), rot=sg * 12, alpha=1 - q ** 2, ox=HL_OX, oy=HL_OY)
    pz = ease_out_cubic(clamp01(lt / 0.22))
    z = 1.0 + 0.12 * pz
    sx_, sy_ = shake_xy(i - (SC_FRAME[k] + int(round(t_hit * FPS))), 4, 6, seed=10)
    fr = camera(world, HL_OX, HL_OY, 540, lerp(960, 1080, pz), z, 0, sx_, sy_)
    curtains(fr, 0.0, t)
    return fr

# ---------------------------------------------------------------- scene 11: the food plays a role too
def osh_actor(eyes, blink, bow, carrot_bow, t):
    """plate of osh: rice mound (with eyes, blinks, bows), two carrot strips in bow ties"""
    Wd, Hd = 560, 460
    c = SS(Wd, Hd, 2)
    cx, base = Wd / 2, 360
    # carrots (behind the plate rim, standing on the rice at both sides)
    for sg in (-1, 1):
        ang = math.radians(sg * 8 + (-sg) * 0 + carrot_bow * 38 * (1 if sg < 0 else 1))
        x0, y0 = cx + sg * 175, base - 30
        L = 150
        ux, uy = math.sin(ang) * (-1 if sg > 0 else 1) * (1), -math.cos(ang)
        ux = math.sin(ang if sg < 0 else -ang) * -1 if False else (math.sin(ang) if sg < 0 else math.sin(ang))
        tip = (x0 + L * math.sin(ang) * (1 if sg < 0 else 1) * (-1 if sg > 0 else 1) * -1, y0 - L * math.cos(ang))
        tip = (x0 + L * math.sin(ang), y0 - L * math.cos(ang))
        c.line([(x0, y0), tip], fill=OL, width=44)
        c.line([(x0, y0), tip], fill=CARROT, width=32)
        for q in (0.3, 0.55, 0.8):
            px, py = lerp(x0, tip[0], q), lerp(y0, tip[1], q)
            c.line([(px - 10, py), (px + 6, py + 3)], fill=(200, 100, 20), width=4)
        # bow tie
        bx, by = lerp(x0, tip[0], 0.45), lerp(y0, tip[1], 0.45)
        c.poly([(bx, by), (bx - 24, by - 13), (bx - 24, by + 13)], fill=(30, 30, 34), outline=OL, width=4)
        c.poly([(bx, by), (bx + 24, by - 13), (bx + 24, by + 13)], fill=(30, 30, 34), outline=OL, width=4)
        c.circle(bx, by, 7, fill=(30, 30, 34), outline=OL, width=3)
        # tiny eyes on the carrot tip
        ex, ey = lerp(x0, tip[0], 0.82), lerp(y0, tip[1], 0.82)
        for dx in (-7, 7):
            c.circle(ex + dx, ey, 6, fill=(255, 255, 255), outline=OL, width=2.5)
            c.circle(ex + dx, ey + 1, 2.6, fill=OL, outline=None, width=0)
    # plate
    c.ellipse((cx - 250, base - 40, cx + 250, base + 70), fill=(255, 255, 255), outline=OL, width=6)
    c.ellipse((cx - 190, base - 22, cx + 190, base + 50), fill=(240, 244, 248), outline=(200, 206, 214), width=3)
    # rice mound (bows forward: squash + slight lean)
    mh = 200 * (1 - 0.18 * bow); mw = 190 * (1 + 0.05 * bow)
    top = base + 10 - mh
    lean = 26 * bow
    pts = []
    for q in np.linspace(0, math.pi, 40):
        x = cx - mw * math.cos(q)
        y = base + 10 - mh * math.sin(q) ** 0.85
        x += lean * math.sin(q) ** 2
        pts.append((x, y))
    c.poly(pts + [(cx + mw, base + 14), (cx - mw, base + 14)], fill=RICE, outline=OL, width=6)
    rnd = random.Random(3)
    for k_ in range(60):
        q = rnd.uniform(0.15, math.pi - 0.15); rr = rnd.uniform(0.15, 0.92)
        x = cx - mw * rr * math.cos(q) + lean * math.sin(q) ** 2
        y = base + 10 - mh * rr * math.sin(q) ** 0.85
        c.ellipse((x - 7, y - 3.5, x + 7, y + 3.5), fill=(252, 226, 140), outline=None, width=0)
    for k_ in range(8):
        q = rnd.uniform(0.3, math.pi - 0.3); rr = rnd.uniform(0.3, 0.85)
        x = cx - mw * rr * math.cos(q) + lean * math.sin(q) ** 2; y = base + 10 - mh * rr * math.sin(q) ** 0.85
        c.line([(x - 12, y + 5), (x + 12, y - 5)], fill=CARROT, width=9)
    for k_ in range(4):
        q = rnd.uniform(0.4, math.pi - 0.4); rr = rnd.uniform(0.2, 0.6)
        x = cx - mw * rr * math.cos(q) + lean * math.sin(q) ** 2; y = base + 10 - mh * rr * math.sin(q) ** 0.85
        c.circle(x, y, 13, fill=MEAT, outline=OL, width=3)
    if eyes > 0.02:
        ey = top + mh * 0.42 + 18 * bow
        for dx in (-48, 48):
            ex = cx + dx + lean * 0.9
            r = 30 * eyes
            if blink > 0.5:
                c.arc((ex - r, ey - r * 0.4, ex + r, ey + r * 0.6), 20, 160, fill=OL, width=6)
            else:
                c.circle(ex, ey, r, fill=(255, 255, 255), outline=OL, width=5)
                c.circle(ex, ey + 3 * bow, r * 0.48, fill=(18, 14, 14), outline=None, width=0)
                c.circle(ex - r * 0.2, ey - r * 0.22, r * 0.17, fill=(255, 255, 255), outline=None, width=0)
        if eyes > 0.6:
            c.arc((cx - 26 + lean, ey + 22, cx + 26 + lean, ey + 52), 20, 160, fill=OL, width=6)
            for dx in (-80, 80):
                c.ellipse((cx + dx + lean - 16, ey + 24, cx + dx + lean + 16, ey + 38), fill=BLUSH, outline=None, width=0)
    return c.result()

def s11(i, k, t, lf, lt, dur):
    world = A["hall_bg"].copy()
    spots(world, 0, HL_OX, HL_OY)
    tt = table_top_y("table_w")
    # customer shocked on the right, Bobur standing on the left
    hc = HS("cust_05")
    sheet(world, "cust", 5, 830, tt - 0.55 * hc + hc, HL_OX, HL_OY, sy=breathe(t, ph=1))
    table_at(world, 560, TABLE_FLOOR, HL_OX, HL_OY, "table_w")
    sheet(world, "bobur", 2, 150, 1800, HL_OX, HL_OY, sy=breathe(t) * talk_sy(i, k))
    eyes = ease_out_back(clamp01((lt - 0.55) / 0.2), 2.0)
    blink = 1.0 if 0.95 <= lt < 1.05 else 0.0
    bow = math.sin(math.pi * clamp01((lt - 1.12) / 0.45))
    cbow = math.sin(math.pi * clamp01((lt - 1.25) / 0.45))
    key = (round(eyes, 2), blink, round(bow, 2), round(cbow, 2))
    if A.get("osh_key") != key:
        A["osh_key"] = key; A["osh_img"] = osh_actor(*key, lt)
    oi = A["osh_img"]
    paste(world, oi, 560 - oi.width / 2 - HL_OX, tt - 360 - 4 - HL_OY)
    # clapperboard snaps shut in front of the plate, then flies off
    if lt < 0.75:
        shut = lt >= 0.18
        cl = A["clapper_shut"] if shut else A["clapper_open"]
        q = clamp01((lt - 0.4) / 0.35)
        sc = 0.9 if not shut else 0.9 * (1 + 0.06 * math.exp(-(lt - 0.18) * 20))
        place(world, cl, 560 + 700 * ease_in_cubic(q), tt - 170 - 200 * ease_in_cubic(q), scale=sc, rot=-30 * ease_in_cubic(q), ox=HL_OX, oy=HL_OY)
    # camera: push toward the plate, then pull back to show both
    if lt < 0.9:
        q = ease_in_out(lt / 0.9); z = lerp(1.0, 1.4, q); cx = lerp(540, 560, q); cy = lerp(1000, tt - 150, q)
    else:
        q = ease_in_out(clamp01((lt - 0.9) / 0.55)); z = lerp(1.4, 0.96, q); cx = lerp(560, 520, q); cy = lerp(tt - 150, 1010, q)
    fr = camera(world, HL_OX, HL_OY, cx, cy, z)
    curtains(fr, 0.0, t)
    return fr

# ---------------------------------------------------------------- scene 12: sold
def s12(i, k, t, lf, lt, dur):
    off = lt > 0.55
    fl = [1, 0, 1, 0.45, 0, 0.45, 0, 0]
    if 0.45 <= lt < 0.45 + len(fl) / FPS:
        lv = fl[int((lt - 0.45) * FPS)]
        sign = "on" if lv > 0.7 else ("mid" if lv > 0.3 else "off")
    else:
        sign = "on" if lt < 0.45 else "off"
    world = ext_world(sign)
    sheet(world, "bobur", 8, EB["x"], EB["yb"], EX_OX, EX_OY, sy=breathe(t))
    # SOTILDI flies in and sticks to the door with a squash
    so = A["sold"]
    tx, ty = (EX_DOOR[0] + EX_DOOR[2]) / 2, 1080
    fp = clamp01((lt - 0.05) / 0.3)
    if fp < 1:
        e = ease_in_cubic(fp)
        x, y, rot, sc = lerp(1500, tx, e), lerp(260, ty, e), lerp(-40, -6, e), lerp(0.7, 1.0, e)
        place(world, so, x, y, scale=sc, rot=rot, ox=EX_OX, oy=EX_OY)
    else:
        d = lt - 0.35
        sq = 1 - 0.2 * math.exp(-d * 10) * math.cos(d * 30)
        place(world, so, tx, ty, sx=2 - sq, sy=sq, rot=-6, ox=EX_OX, oy=EX_OY)
    q = ease_in_out_sine(lt / dur)
    return camera(world, EX_OX, EX_OY, 540, 970, 1.06 - 0.06 * q)

# ---------------------------------------------------------------- scene 13: dramatic pause
def s13(i, k, t, lf, lt, dur):
    world = ext_world("off")
    sheet(world, "bobur", 4, 540, 2130, EX_OX, EX_OY, k=1.27, sy=breathe(t, 0.008))
    p = clamp01(lt / 0.4)
    if "ext_dim" not in A:
        A["ext_dim"] = np.asarray(dim(Image.new("RGB", world.size, (255, 255, 255)), EX_OX, EX_OY, (540, 1250), 430, floor=0.4, vignette=0.4)).astype(np.float32) / 255
    m = 1 - p * (1 - A["ext_dim"])
    world = Image.fromarray(np.clip(np.asarray(world).astype(np.float32) * m, 0, 255).astype(np.uint8))
    q = ease_in_out_sine(lt / dur)
    fr = camera(world, EX_OX, EX_OY, 540, lerp(1180, 1060, q), 1.0 + 0.15 * q)
    rem = SC_END_FRAME[k] - i
    if rem <= 3: puff_screen(fr, 0.2 * (4 - rem) / 4, 560, 1150, 1100)
    return fr

# ---------------------------------------------------------------- scenes 14-17: back on the blogger set
def s14(i, k, t, lf, lt, dur):
    world = A["blog"].copy()
    rot = 1.8 * math.sin(2 * math.pi * 5 * lt) * clamp01((lt - 0.25) / 0.2)
    blogger(world, 10, 560, i, k, t, rot=rot)
    phone_on(world)
    q = clamp01(lt / 0.6)
    z = ZB * (1.12 - 0.12 * ease_out_back(q, 2.0))
    fr = camera(world, BL_OX, BL_OY, 540, 670, z)
    if lf < 6: pp = 0.2 + 0.35 * lf / 6
    else: pp = 0.55 + 0.45 * clamp01((lf - 6) / 8.0)
    puff_screen(fr, pp, 560, 1180, 1100)
    return fr

BUB_XY = (930, 820)
def s15(i, k, t, lf, lt, dur):
    world = A["blog"].copy()
    blogger(world, 9, 450, i, k, t)
    t_send = word_t(15, "yuboring")
    pin = ease_out_back(clamp01((lt - 0.1) / 0.35), 1.8)
    pulse = 0.5 + 0.5 * math.sin(lt * 9)
    if lt >= t_send: pulse = max(pulse, 1 - clamp01((lt - t_send) / 0.2))
    bub = A["bubble"][int(round(pulse * 8))]
    if pin > 0.02:
        place(world, bub, BUB_XY[0], BUB_XY[1] + 8 * math.sin(lt * 2.5), scale=0.9 * pin, ox=BL_OX, oy=BL_OY)
    if lt >= t_send:
        d = lt - t_send
        q = clamp01(d / 0.6)
        x0, y0 = BUB_XY[0], BUB_XY[1] + 150
        x = x0 + 900 * ease_in_cubic(q) + 60 * math.sin(q * 6)
        y = y0 - 1100 * ease_in_cubic(q) - 80 * math.sin(q * 3.1)
        # dashed trail
        for j in range(1, 9):
            qq = q - j * 0.035
            if qq <= 0: break
            tx = x0 + 900 * ease_in_cubic(qq) + 60 * math.sin(qq * 6); ty = y0 - 1100 * ease_in_cubic(qq) - 80 * math.sin(qq * 3.1)
            c = SS(26, 26, 2); c.circle(13, 13, 9, fill=(255, 255, 255, 220), outline=None, width=0)
            place(world, c.result(), tx, ty, alpha=1 - j / 9, ox=BL_OX, oy=BL_OY)
        if q < 1: place(world, A["plane"], x, y, scale=1.1 + 0.4 * q, rot=20 + 15 * q, ox=BL_OX, oy=BL_OY)
    phone_on(world, 260)
    q = ease_in_out_sine(lt / dur)
    return camera(world, BL_OX, BL_OY, 560, 680, ZB * (1 + 0.05 * q))

def s16(i, k, t, lf, lt, dur):
    world = A["blog"].copy()
    blogger(world, 7, 470, i, k, t, extra_sy=1.0)
    cbp = ease_out_back(clamp01((lt - 0.08) / 0.3), 2.2)
    if cbp > 0.02:
        place(world, A["comment"], 920, 760 + 8 * math.sin(lt * 3), scale=cbp * 1.0, ox=BL_OX, oy=BL_OY)
    phone_on(world, 260)
    cyb = 670 + 10 * math.sin(2 * math.pi * lt / 1.1)
    return camera(world, BL_OX, BL_OY, 560, cyb, ZB * (1 + 0.012 * math.sin(2 * math.pi * lt / 1.3)))

def s17(i, k, t, lf, lt, dur):
    if i >= CUT_F:
        fr = s1_frame0()
        fl = {0: 0.85, 1: 0.5, 2: 0.2}.get(i - CUT_F, 0.0)
        return flash(fr, fl)
    world = A["blog"].copy()
    cp = ease_out_back(clamp01((lt - 0.08) / 0.45), 1.4)
    cxc = lerp(1560, 905, cp); cyc = 960
    place(world, A["card"], cxc, cyc, rot=lerp(-12, 4, cp), ox=BL_OX, oy=BL_OY)
    tp = ease_out_back(clamp01((lt - 0.4) / 0.35), 2.0)
    if tp > 0.02:
        for j, tim in enumerate(A["card_title"]):
            place(world, tim, cxc, cyc - A["card"].height / 2 - 130 + j * 70, scale=max(0.02, tp), ox=BL_OX, oy=BL_OY)
    blogger(world, 8, 450, i, k, t)
    phone_on(world, 300)
    q = ease_in_out_sine(clamp01(lt / dur))
    fr = camera(world, BL_OX, BL_OY, 560, 670 + 20 * q, ZB * (1 + 0.06 * q))
    if i >= FLASH_F0:
        fr = flash(fr, ease_in_cubic((i - FLASH_F0 + 1) / (CUT_F - FLASH_F0 + 1)))
    return fr

SCENE_FN = {1: s1, 2: s2, 3: s3, 4: s4, 5: s5, 6: s6, 7: s7, 8: s8, 9: s9, 10: s10, 11: s11, 12: s12, 13: s13, 14: s14, 15: s15, 16: s16, 17: s17}

def init():
    build_assets()
