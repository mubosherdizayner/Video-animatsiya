# Scene logic: every scene draws its world, applies the camera and returns a 1080x1920 RGB frame.
import math, json, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageEnhance
from lib import *
from worlds import *
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

def scene_at_frame(i):
    cur = SC_IDS[0]
    for k in SC_IDS:
        if i >= SC_FRAME[k]: cur = k
    return cur

# ---------------------------------------------------------------- motion helpers
def talk_sy(i, k):
    """scale-y talk bob 1.00->1.03 over 3 frames at every word onset (speaker scenes only)"""
    if SPEAKER[k] == "HIKOYACHI": return 1.0
    best = None
    for w in scene_words(k):
        f = word_frame(w)
        if f <= i: best = f
    if best is None: return 1.0
    d = i - best
    if d < 3: return 1.0 + 0.03 * (d / 2.0 if d <= 2 else 1)
    if d < 6: return 1.03 - 0.03 * (d - 2) / 3.0
    return 1.0

def breathe(t, amp=0.006, per=1.7, ph=0.0):
    return 1.0 + amp * math.sin(2 * math.pi * t / per + ph)

def shake_xy(f, amp, n=6, seed=0):
    """deterministic shake for frames 0..n, zero at f<=0 and f>=n"""
    if f <= 0 or f >= n: return 0.0, 0.0
    rnd = random.Random(seed * 1000 + int(f))
    k = 1 - f / n
    return amp * k * rnd.choice([-1, 1]) * rnd.uniform(0.6, 1.0), amp * k * rnd.choice([-1, 1]) * rnd.uniform(0.6, 1.0)

def camera(world, ox, oy, cx, cy, z, rot=0.0, shx=0.0, shy=0.0):
    th = math.radians(rot)
    c, s = math.cos(th), math.sin(th)
    a, b = c / z, s / z
    d, e = -s / z, c / z
    X0, Y0 = 540 + shx, 960 + shy
    cc = cx - ox - a * X0 - b * Y0
    ff = cy - oy - d * X0 - e * Y0
    return world.transform((W, H), Image.AFFINE, (a, b, cc, d, e, ff), resample=Image.BICUBIC, fillcolor=(20, 20, 24))

def motion_blur_cam(world, ox, oy, cxs, cy, z, rot=0.0):
    acc = None
    for cx in cxs:
        im = np.asarray(camera(world, ox, oy, cx, cy, z, rot)).astype(np.float32)
        acc = im if acc is None else acc + im
    return Image.fromarray((acc / len(cxs)).astype(np.uint8))

# ---------------------------------------------------------------- assets (built once before forking)
A = {}
K_BLOG = 1250 / sprite("pharm_06").height      # scale used at the loop anchor
A1 = dict(x=480, yb=1770)                       # scene-1 / last-frame anchor
ZB = 0.8                                        # blogger-set base zoom (1000 px tall character)

def build_assets():
    A["ph_boxes"] = pharmacy_back("boxes")
    A["ph_fruits"] = pharmacy_back("fruits")
    A["ph_none"] = pharmacy_back("none")
    A["counter"] = counter_layer()
    A["bell"] = bell_img()
    A["door"] = {k: door_panel(k / 10) for k in range(11)}
    A["sign_d"] = sign_img("DORIXONA")
    A["sign_m"] = sign_img("MEVA", icon="apple")
    A["blog"] = blogger_back()
    A["phone"], A["phone_x"], A["phone_y"] = phone_tripod()
    ww = window_wall(); A["win_wall"] = ww
    A["street_win"] = street_img(WIN[2] - WIN[0], WIN[3] - WIN[1], seed=9).convert("RGBA")
    A["win_frame"], A["wf_x"], A["wf_y"] = window_frame()
    A["hand_fan"] = customer_hand_fan()
    A["stack"] = banknote_stack(300)
    A["gold"] = golden_box(150, 180)
    A["apple_big"] = apple(78)
    A["apple"] = apple(58)
    A["fruits"] = fruit_imgs()
    A["sparkle"] = sparkle(70)
    A["sparkle_w"] = sparkle(56, col=(255, 255, 255))
    A["diploma"] = diploma_paper(420, 300)
    A["roll"] = scroll_roll(300, 22)
    A["stamp"] = check_stamp(190)
    A["register"] = cash_register(230, 190)
    A["cobweb"] = cobweb(150)
    A["calendar_base"] = calendar_img(19)
    A["cal_pages"] = [calendar_img(d, page_only=True) for d in range(12, 19)]
    A["notif"] = notification_bubble("XOʻJAYIN:", "Bir haftada bitta ham dori sotilmadi!!! 😡", w=940)
    A["comment"] = comment_bubble(420, 250)
    A["card"] = mystery_card(440, 580)
    A["card_title"] = [text_img(s, 58, fill=YELLOW, stroke=8) for s in ("AGAR BLOGER", "BOʻLMAGANIDA")]
    A["basket"] = fruit_basket(190)
    # glow for lit boxes
    g = Image.new("L", (260, 260), 0); ImageDraw.Draw(g).ellipse((40, 40, 220, 220), fill=255)
    g = g.filter(ImageFilter.GaussianBlur(28))
    glow = Image.new("RGBA", (260, 260), (255, 246, 190, 0)); glow.putalpha(g.point(lambda v: int(v * 0.85)))
    A["glow"] = glow
    # pharmacy composite with sign + counter at 1300 (most scenes)
    A["ph_std"] = ph_world("ph_boxes", sign="sign_d", counter_y=1300)
    # hue-shifted jogger copies (scene 15)
    jog = []
    for name, hue, mir in (("cust_10", 215, False), ("cust_07", 348, True), ("cust2_02", 282, False), ("cust_10", None, True)):
        src = sprite(name)
        im = src if hue is None else hue_shift_green(src, hue, 1.0, 0.95 if hue != 348 else 0.8)
        jog.append((name, im, mir))
    A["joggers"] = jog
    # pre-rendered headlines
    A["head"] = {k: headline_img(v) for k, v in HEADLINES.items()}

def ph_world(back, sign="sign_d", counter_y=1300, register_x=None):
    im = A[back].copy().convert("RGBA")
    if sign: im.alpha_composite(A[sign], (240 - PH_OX, 480 - PH_OY))
    im.alpha_composite(A["door"][0], (1390 - PH_OX, 740 - PH_OY))
    b = A["bell"]; im.alpha_composite(b, (1790 - b.width // 2 - PH_OX, 762 - PH_OY))
    if counter_y is not None:
        im.alpha_composite(A["counter"], (COUNTER_X - PH_OX, counter_y - PH_OY))
    return im.convert("RGB")

def spotlight(img, ox, oy, centre, radius):
    a = np.asarray(img).astype(np.float32)
    h, w, _ = a.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = centre[0] - ox, centre[1] - oy
    d = np.sqrt((xx - cx) ** 2 + ((yy - cy) * 0.8) ** 2)
    spot = np.clip(1 - (d - radius) / 260, 0, 1)
    spot = spot * spot * (3 - 2 * spot)
    m = 0.4 + 0.6 * spot
    warm = np.stack([1.0 + 0.0 * spot, 1.0 - 0.06 * spot, 1.0 - 0.16 * spot], -1)
    out = a * m[..., None] * warm
    # vignette
    vx = (xx / w - 0.5); vy = (yy / h - 0.5)
    vig = 1 - 0.35 * np.clip((vx ** 2 + vy ** 2) * 3.2, 0, 1)
    out *= vig[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

def headline_img(text):
    emoji_only = all(is_emoji(ch) or ch in " \ufe0f" for ch in text)
    size = 150 if emoji_only else 80
    words = text.split()
    full = text_img(text, size, stroke=9, shadow=0.55)
    if full.width <= 860:
        return [full], size
    best = None
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        ia, ib = text_img(a, size, stroke=9, shadow=0.55), text_img(b, size, stroke=9, shadow=0.55)
        m = max(ia.width, ib.width)
        if best is None or m < best[0]: best = (m, a, b)
    m, a, b = best
    sz = size if m <= 860 else int(size * 860 / m)
    return [text_img(a, sz, stroke=9, shadow=0.55), text_img(b, sz, stroke=9, shadow=0.55)], sz

# ---------------------------------------------------------------- common pharmacy helpers
def jam(canvas, pose, x, yb, h, i, k, t, ox=PH_OX, oy=PH_OY, mirror=False, extra_sy=1.0, sx=1.0, rot=0.0, freeze=False, still=False):
    name = spr_name("pharm", pose) if isinstance(pose, int) else pose
    sy = (1.0 if freeze else talk_sy(i, k) * breathe(t)) * extra_sy
    draw_char(canvas, name, x, yb, h, ox, oy, sx=sx, sy=sy, mirror=mirror, rot=rot)

def blogger(canvas, pose, x, yb, i, k, t, sx=1.0, rot=0.0, extra_sy=1.0):
    name = spr_name("blogger", pose)
    h = sprite(name).height * K_BLOG
    draw_char(canvas, name, x, yb, h, BL_OX, BL_OY, sx=sx, sy=breathe(t) * extra_sy, rot=rot)

def counter_on(canvas, y, ox=PH_OX, oy=PH_OY):
    paste(canvas, A["counter"], COUNTER_X - ox, y - oy)

def puff_screen(frame, p, cx=540, cy=1080, size=880):
    im = smoke_puff(p, size=size)
    if im is None: return
    frame.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)

def flash(frame, alpha, col=(255, 255, 255)):
    if alpha <= 0.003: return frame
    return Image.blend(frame, Image.new("RGB", frame.size, col), min(1, alpha))

def vhs(frame, p, seed):
    """rewind look: RGB offset + displaced horizontal bands + scanlines; p 0->1 (effect fades)"""
    k = 1 - p
    a = np.asarray(frame).astype(np.int16).copy()
    rnd = random.Random(seed)
    dx = int(16 * k) + 2
    r = np.roll(a[..., 0], dx, axis=1); b = np.roll(a[..., 2], -dx, axis=1)
    a[..., 0] = r; a[..., 2] = b
    for _ in range(int(9 * k) + 2):
        y0 = rnd.randint(0, H - 60); hh = rnd.randint(8, 70); sh = rnd.randint(-60, 60)
        a[y0:y0 + hh] = np.roll(a[y0:y0 + hh], int(sh * k), axis=1)
    # tracking band
    by = int((1 - p) * H * 1.2 - 100) % H
    a[by:by + 70] = np.clip(a[by:by + 70] * 0.6 + 90 + np.random.RandomState(seed).randint(0, 80, (min(70, H - by), W, 1)), 0, 255)
    a[::4] = (a[::4] * (1 - 0.22 * k)).astype(np.int16)
    for _ in range(int(14 * k)):
        y = rnd.randint(0, H - 3)
        a[y:y + 2, :] = np.clip(a[y:y + 2, :] + 110, 0, 255)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def sparkles(canvas, pts, t, ox, oy, scale=1.0, seed=0):
    for j, (x, y) in enumerate(pts):
        ph = t * 5 + j * 1.7
        s = (0.55 + 0.45 * math.sin(ph)) * scale
        if s <= 0.05: continue
        sp = A["sparkle"] if j % 2 == 0 else A["sparkle_w"]
        place(canvas, sp, x, y, scale=s, rot=(t * 90 + j * 40) % 90, ox=ox, oy=oy)

# ---------------------------------------------------------------- scenes
def s1(i, k, t, lf, lt, dur):
    world = A["ph_s1"].copy()
    freeze = 8 <= lf < 14
    p = ease_out_cubic(lf / 8.0)
    jam(world, 6, A1["x"], A1["yb"], 1250, i, k, t, freeze=freeze or lf == 0, extra_sy=1.0)
    counter_on(world, 1560)
    # customer hand with banknotes, frozen mid-reach
    hf = A["hand_fan"]
    reach = ease_out_cubic(min(lf, 8) / 8.0)
    hs = 1.12
    hx, hy = -140 + 40 * reach, 1300 - 30 * reach
    hand = hf.resize((int(hf.width * hs), int(hf.height * hs)), Image.LANCZOS)
    paste(world, hand, hx - PH_OX, hy - PH_OY)
    if lf < 14:
        z = 1.0 + 0.12 * p; cx = 540 - 20 * p; cy = 960 - 40 * p
    else:
        q = (lt - 14 / FPS)
        z = 1.12 + 0.03 * q; cx = 520 + 10 * q; cy = 920 - 10 * q
    sx_, sy_ = shake_xy(lf, 6, 7, seed=1)
    fr = camera(world, PH_OX, PH_OY, cx, cy, z, 0, sx_, sy_)
    if 8 <= lf < 13: fr = flash(fr, 0.38 * (1 - (lf - 8) / 5))
    return fr

def s2(i, k, t, lf, lt, dur):
    world = A["blog"].copy()
    blogger(world, 3, 540, A1["yb"], i, k, t)
    paste(world, A["phone"], A["phone_x"] - BL_OX, A["phone_y"] - BL_OY)
    z = ZB * (1 + 0.06 * ease_in_out_sine(lt / dur))
    cx = 540 + 14 * math.sin(2 * math.pi * lt / 2.6); cy = 670 + 6 * math.sin(2 * math.pi * lt / 1.9)
    fr = camera(world, BL_OX, BL_OY, cx, cy, z, 0.5 * math.sin(2 * math.pi * lt / 2.8))
    if lt < 0.3:
        fr = vhs(fr, lt / 0.3, seed=i)
    rem = SC_END_FRAME[k] - i
    if rem <= 3: puff_screen(fr, 0.2 * (4 - rem) / 4, 560, 1180)
    return fr

def s3(i, k, t, lf, lt, dur):
    world = A["ph_nocounter"].copy()
    jam(world, 7, 540, 1700, 1000, i, k, t)
    counter_on(world, 1300)
    if lt > 0.22:
        tx, ty = sprite_point("pharm_07", 0.16, 0.36, 540, 1700, 1000)
        sparkles(world, [(tx - 70, ty - 60), (tx + 60, ty - 90), (tx - 40, ty + 50), (tx + 80, ty + 10)], lt, PH_OX, PH_OY, scale=min(1, (lt - 0.22) / 0.15))
    q = clamp01(lt / 0.55)
    z = 1.15 - 0.15 * ease_out_back(q, 2.2)
    fr = camera(world, PH_OX, PH_OY, 540, 1000 - 20 * q, z)
    # smoke puff already covering at cut, then clears
    pp = 0.2 + 0.8 * clamp01((lf) / 14.0) if lf >= 6 else 0.2 + 0.0 * lf
    if lf < 6: pp = 0.2 + 0.35 * lf / 6
    else: pp = 0.55 + 0.45 * clamp01((lf - 6) / 8.0)
    puff_screen(fr, pp, 560, 1180)
    return fr

def s4(i, k, t, lf, lt, dur):
    world = A["ph_nocounter"].copy()
    jx, jy, jh = 410, 1700, 1000
    jam(world, 3, jx, jy, jh, i, k, t)
    counter_on(world, 1300)
    # diploma unrolls above the open palm
    px, py = sprite_point("pharm_03", 0.9, 0.38, jx, jy, jh)
    dcx, dcy = px + 40, py - 250 + 10 * math.sin(lt * 3.2)
    pr = ease_out_cubic(clamp01((lt - 0.08) / 0.55))
    dip = A["diploma"]
    wv = max(2, int(dip.width * pr))
    crop = dip.crop(((dip.width - wv) // 2, 0, (dip.width + wv) // 2, dip.height))
    paste(world, crop, dcx - wv / 2 - PH_OX, dcy - dip.height / 2 - PH_OY)
    roll = A["roll"]
    for sgn in (-1, 1):
        paste(world, roll, dcx + sgn * wv / 2 - roll.width / 2 - PH_OX, dcy - roll.height / 2 - PH_OY)
    # stamp on the word "oʻqigan"
    wq = [w for w in scene_words(k) if w["text"].startswith("oʻqigan")][0]
    sf = i - word_frame(wq)
    if sf >= 0:
        st = A["stamp"]
        if sf < 4: sc = lerp(2.2, 1.0, ease_in_cubic(sf / 4)); sqx = sqy = 1; al = clamp01(sf / 2 + 0.3)
        else:
            e = math.exp(-(sf - 4) / 3.0); sc = 1.0; sqx = 1 + 0.18 * e * math.cos((sf - 4) * 0.9); sqy = 1 - 0.18 * e * math.cos((sf - 4) * 0.9); al = 1
        place(world, st, dcx + 120, dcy + 70, scale=sc, sx=sqx, sy=sqy, alpha=al, ox=PH_OX, oy=PH_OY)
    q = ease_in_out_sine(lt / dur)
    fr = camera(world, PH_OX, PH_OY, lerp(540, 610, q), lerp(960, 900, q), 1.0 + 0.10 * q)
    return fr

def s5(i, k, t, lf, lt, dur):
    world = A["ph_nocounter_nodoor"].copy()
    # door panel swings open
    op = ease_out_cubic(clamp01(lt / 0.35))
    paste(world, A["door"][int(round(op * 10))], 1390 - PH_OX, 740 - PH_OY)
    b = A["bell"]
    place(world, b, 1790, 762 + b.height / 2, rot=28 * damped(lt, 3.2, 3.2), ox=PH_OX, oy=PH_OY)
    jam(world, 1, 330, 1700, 1000, i, k, t)
    counter_on(world, 1300)
    # customer hops in from the door to the counter
    p = clamp01((lt - 0.05) / 1.0)
    pe = ease_out_cubic(p)
    x = lerp(1620, 840, pe); yb = lerp(1735, 1880, pe); h = lerp(800, 950, pe)
    hop = abs(math.sin(math.pi * 3 * p)) if p < 1 else 0
    land = 0.0
    if p < 1:
        ph = (3 * p) % 1
        if ph < 0.12 or ph > 0.95: land = 1.0
    sq = 1 - 0.05 * land
    sh = soft_shadow(h * 0.5, h * 0.06, 0.25)
    paste(world, sh, x - sh.width / 2 - PH_OX, yb - sh.height / 2 - PH_OY)
    draw_char(world, "cust_02", x, yb - 70 * hop, h, PH_OX, PH_OY, sx=1 + 0.04 * land, sy=sq * talk_sy(i, k) * breathe(t, ph=1))
    cx = lerp(1350, 600, ease_in_out(clamp01((lt - 0.1) / 1.05)))
    return camera(world, PH_OX, PH_OY, cx, 960, 1.0)

def s6(i, k, t, lf, lt, dur):
    world = A["ph_nocounter"].copy()
    # boxes light up one after another, left -> right, toward his palm
    lit = [s for s in SLOTS if s["board"] == 1 and -120 < s["x"] < 380]
    lit = sorted(lit, key=lambda s: s["x"])
    for j, s in enumerate(lit):
        t0 = 0.04 + j * (0.62 / max(1, len(lit) - 1))
        if lt >= t0:
            e = clamp01((lt - t0) / 0.08)
            x, y, it = slot_pos(s)
            g = A["glow"]
            gs = (s["w"] * 2.6) / g.width * (0.9 + 0.1 * math.sin(lt * 9 + j))
            place(world, g, x + it.width / 2, y + it.height / 2, scale=gs, alpha=1.0 * e, ox=PH_OX, oy=PH_OY)
            place(world, g, x + it.width / 2, y + it.height / 2, scale=gs * 0.7, alpha=0.8 * e, ox=PH_OX, oy=PH_OY)
            br = ImageEnhance.Brightness(it).enhance(1.0 + 0.35 * e)
            paste(world, br, x - PH_OX, y - PH_OY)
    jam(world, 3, 720, 1700, 1000, i, k, t, mirror=True)
    counter_on(world, 1300)
    q = ease_in_out(lt / dur)
    return camera(world, PH_OX, PH_OY, lerp(400, 560, q), 990, 1.06)

def s7(i, k, t, lf, lt, dur):
    world = A["ph_nocounter"].copy()
    jam(world, 1, 330, 1700, 1000, i, k, t)
    counter_on(world, 1300)
    # golden box glides from the top shelf to the counter
    gb = A["gold"]
    gp = clamp01((lt - 0.42) / 0.5)
    if gp <= 0:
        gx, gy = 470, 860 - gb.height / 2
    else:
        e = ease_in_out(gp)
        gx = lerp(470, 420, e); gy = lerp(860 - gb.height / 2, 1312 - gb.height / 2, e) - 120 * math.sin(math.pi * e)
    gsq = 1.0
    if gp >= 1:
        dtl = lt - 0.92; gsq = 1 - 0.12 * math.exp(-dtl * 14) * math.cos(dtl * 30)
    place(world, gb, gx, gy + gb.height / 2 * (1 - gsq), sx=2 - gsq, sy=gsq, ox=PH_OX, oy=PH_OY)
    sparkles(world, [(gx - 70, gy - 80), (gx + 80, gy - 40), (gx + 40, gy + 90)], lt, PH_OX, PH_OY, scale=0.7)
    # banknote stack slaps on the counter
    stk = A["stack"]
    slap_t = 0.22
    if lt < slap_t:
        e = ease_in_cubic(lt / slap_t); sy_ = 1.0; sx2 = 1.0
        sy0 = lerp(1080, 1312, e)
    else:
        d = lt - slap_t; sy0 = 1312
        sy_ = 1 - 0.22 * math.exp(-d * 12) * math.cos(d * 28); sx2 = 2 - sy_
    place(world, stk, 640, sy0 - stk.height / 2 * sy_, sx=sx2, sy=sy_, ox=PH_OX, oy=PH_OY)
    # customer in front
    sh = soft_shadow(475, 57, 0.25); paste(world, sh, 840 - sh.width / 2 - PH_OX, 1880 - sh.height / 2 - PH_OY)
    draw_char(world, "cust_07", 840, 1880, 950, PH_OX, PH_OY, sy=talk_sy(i, k) * breathe(t, ph=1))
    bump = 0.05 * math.exp(-max(0, lt - slap_t) * 7) if lt >= slap_t else 0
    sx_, sy2 = shake_xy(i - (SC_FRAME[k] + int(slap_t * FPS)), 4, 5, seed=7)
    return camera(world, PH_OX, PH_OY, 560 + 8 * math.sin(lt * 2), 960, 1.0 + bump + 0.02 * lt / dur, 0, sx_, sy2)

def s8(i, k, t, lf, lt, dur):
    world = A["ph_nocounter"].copy()
    freeze = 6 <= lf < 12
    pz = ease_out_cubic(min(lf, 6) / 6)
    jam(world, 6, 360, 1700, 1000, i, k, t, mirror=True, freeze=freeze)
    counter_on(world, 1300)
    gb = A["gold"]
    gx = lerp(450, 380, pz)
    paste(world, gb, gx - gb.width / 2 - PH_OX, 1312 - gb.height - PH_OY)
    stk = A["stack"]
    sxp = lerp(660, 590, pz)
    paste(world, stk, sxp - stk.width / 2 - PH_OX, 1312 - stk.height - PH_OY)
    sh = soft_shadow(475, 57, 0.25); paste(world, sh, 840 - sh.width / 2 - PH_OX, 1880 - sh.height / 2 - PH_OY)
    draw_char(world, "cust_01", 840, 1880, 950, PH_OX, PH_OY, sy=1.0 if freeze else breathe(t, ph=1), rot=0 if freeze else 0)
    rot = -1.5
    if lf < 6:
        cxa = lerp(1250, 560, ease_out_cubic(lf / 6)); cxb = lerp(1250, 560, ease_out_cubic((lf + 0.9) / 6))
        cxs = [lerp(cxa, cxb, q / 5) for q in range(6)]
        return motion_blur_cam(world, PH_OX, PH_OY, cxs, 960, 0.96, rot)
    sx_, sy_ = shake_xy(lf - 6, 6, 6, seed=8)
    drift = max(0, lf - 12) / FPS
    return camera(world, PH_OX, PH_OY, 560 + 25 * drift, 960, 0.96 + 0.03 * drift, rot, sx_, sy_)

def s9(i, k, t, lf, lt, dur):
    kdark = clamp01(lf / 6)
    world = Image.blend(A["ph9_bright_nc"], A["ph9_dark_nc"], kdark) if kdark < 1 else A["ph9_dark_nc"].copy()
    jam(world, 4, 520, 1830, 1150, i, k, t)
    if kdark >= 1: paste(world, A["counter_dark"], COUNTER_X - PH_OX, 1420 - PH_OY)
    else:
        cd = Image.blend(A["counter"], A["counter_dark"], kdark); paste(world, cd, COUNTER_X - PH_OX, 1420 - PH_OY)
    # warm beam
    if kdark > 0:
        beam = A["beam"]; paste(world, with_alpha(beam, kdark), 520 - beam.width / 2 - PH_OX, -120 - PH_OY)
    # customer leaning in at the right edge
    ce = ease_out_cubic(clamp01(lt / 0.45))
    draw_char(world, "cust_01", lerp(1350, 1120, ce), 1960, 1050, PH_OX, PH_OY, rot=5.0 * ce, sy=breathe(t, ph=2))
    q = ease_in_out_sine(lt / dur)
    return camera(world, PH_OX, PH_OY, lerp(540, 530, q), lerp(960, 1000, q), 1.0 + 0.15 * q)

FRUIT_RAIN = None
def fruit_rain():
    global FRUIT_RAIN
    if FRUIT_RAIN is None:
        rnd = random.Random(10)
        names = ["apple", "pomeg", "grapes", "apricot"]
        xs = [-60, 90, 230, 680, 820, 960, 1100, 160, 760, 1020, 20, 900]
        out = []
        for j, x in enumerate(xs):
            out.append(dict(name=names[j % 4], x=x + rnd.uniform(-20, 20), t0=0.04 + j * 0.055 + rnd.uniform(0, 0.03),
                            sc=rnd.uniform(0.85, 1.1), spin=rnd.uniform(-260, 260), vx=rnd.uniform(-60, 60)))
        FRUIT_RAIN = out
    return FRUIT_RAIN

def fruit_state(f, lt, floor=1312):
    g = 5200.0
    tt = lt - f["t0"]
    if tt < 0: return None
    im = A["fruits"][f["name"]]
    r = im.height * f["sc"] * 0.36
    y0 = -200.0; v = 300.0
    yb = floor - r
    # analytic bounce sequence
    t_hit = (-v + math.sqrt(v * v + 2 * g * (yb - y0))) / g
    if tt < t_hit:
        return f["x"] + f["vx"] * tt, y0 + v * tt + 0.5 * g * tt * tt, f["spin"] * tt, None
    vb = (v + g * t_hit) * 0.42
    t2 = tt - t_hit
    hits = [t_hit]
    tb = 2 * vb / g
    if t2 < tb:
        y = yb - (vb * t2 - 0.5 * g * t2 * t2)
        return f["x"] + f["vx"] * (t_hit + t2 * 0.4), y, f["spin"] * (t_hit + t2 * 0.3), hits
    vb2 = vb * 0.4; t3 = t2 - tb; tb2 = 2 * vb2 / g
    hits.append(t_hit + tb)
    xr = f["x"] + f["vx"] * (t_hit + tb * 0.4)
    if t3 < tb2:
        return xr, yb - (vb2 * t3 - 0.5 * g * t3 * t3), f["spin"] * (t_hit + tb * 0.3), hits
    hits.append(t_hit + tb + tb2)
    return xr, yb, f["spin"] * (t_hit + tb * 0.3), hits

def s10(i, k, t, lf, lt, dur):
    kb = clamp01(lf / 4)
    if kb < 1:
        world = Image.blend(A["ph9_dark_nc1300"], A["ph_nocounter"], kb)
    else:
        world = A["ph_nocounter"].copy()
    jx, jy, jh = 430, 1700, 1000
    jam(world, 3, jx, jy, jh, i, k, t)
    counter_on(world, 1300)
    px, py = sprite_point("pharm_03", 0.9, 0.37, jx, jy, jh)
    ap = A["apple_big"]
    s_ap = ease_out_back(clamp01(lt / 0.2), 2.4)
    place(world, ap, px + 6, py - ap.height * 0.36 * s_ap, scale=max(0.01, s_ap), rot=4 * math.sin(lt * 6), ox=PH_OX, oy=PH_OY)
    if lt > 0.12:
        sparkles(world, [(px - 90, py - 160), (px + 80, py - 200), (px + 110, py - 60)], lt, PH_OX, PH_OY, scale=0.8)
    shake = 0.0
    for f in fruit_rain():
        st = fruit_state(f, lt)
        if st is None: continue
        x, y, rot, hits = st
        im = A["fruits"][f["name"]]
        place(world, im, x, y, scale=f["sc"], rot=rot, ox=PH_OX, oy=PH_OY)
        if hits:
            for hh in hits[:2]:
                d = lt - f["t0"] - hh
                if 0 <= d < 0.12: shake = max(shake, 4 * (1 - d / 0.12) * (1 if hh == hits[0] else 0.5))
    z = 1.2 - 0.2 * ease_out_back(clamp01(lt / 0.35), 2.0)
    rnd = random.Random(i)
    return camera(world, PH_OX, PH_OY, 540, 960, z, 0, rnd.uniform(-1, 1) * shake, rnd.uniform(-1, 1) * shake)

def s11(i, k, t, lf, lt, dur):
    world = A["ph_std"].copy()
    hit_t = 0.33
    hx, hy = sprite_point("cust_05", 0.5, 0.035, 540, 2030, 1400)
    ap = A["apple"]
    r = ap.height * 0.36
    sq = 0.0
    if lt >= hit_t:
        d = lt - hit_t
        sq = math.exp(-d * 9) * math.cos(d * 26)
    draw_char(world, "cust_05", 540, 2030, 1400, PH_OX, PH_OY, sx=1 + 0.04 * max(0, sq), sy=(1 - 0.05 * max(0, sq)) * talk_sy(i, k) * breathe(t, ph=1))
    if lt < hit_t:
        e = (lt / hit_t) ** 2
        ax, ay, arot = hx + 10, lerp(-150, hy - r + 4, e), 0
        place(world, ap, ax, ay, rot=arot, ox=PH_OX, oy=PH_OY)
    else:
        d = lt - hit_t
        ax = hx + 10 + 520 * d; ay = hy - r + 4 - 950 * d + 0.5 * 4200 * d * d
        if ay < 2300:
            place(world, ap, ax, ay, rot=-420 * d, sx=1 + 0.15 * math.exp(-d * 30), sy=1 - 0.15 * math.exp(-d * 30), ox=PH_OX, oy=PH_OY)
        if d < 0.5:
            for j in range(3):
                a = d * 7 + j * 2.09
                place(world, A["sparkle"], hx + 130 * math.cos(a), hy - 40 + 40 * math.sin(a), scale=0.7 * (1 - d / 0.5), rot=d * 200, ox=PH_OX, oy=PH_OY)
    pz = ease_out_cubic(clamp01(lf / 6))
    sx_, sy_ = shake_xy(i - (SC_FRAME[k] + int(hit_t * FPS) + 1), 5, 6, seed=11)
    return camera(world, PH_OX, PH_OY, 540, lerp(960, 900, pz), 1.0 + 0.12 * pz + 0.02 * lt, 0, sx_, sy_)

FLIP_ORDER = sorted(SLOTS, key=lambda s: (s["board"], s["x"]))
def s12(i, k, t, lf, lt, dur):
    world = A["ph_none_nosign"].copy()
    n = len(FLIP_ORDER)
    for j, s in enumerate(FLIP_ORDER):
        t0 = 0.12 + j * (1.05 / n)
        p = clamp01((lt - t0) / 0.2)
        fruit = p >= 0.5
        x, y, it = slot_pos(s, fruit=fruit)
        sxv = abs(math.cos(math.pi * p))
        if sxv < 0.04: continue
        cx = x + it.width / 2
        place(world, it, cx, y + it.height / 2, sx=sxv, ox=PH_OX, oy=PH_OY)
    # sign flickers, then MEVA
    pattern = [1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0]
    fl0 = int(0.8 * FPS)
    rel = lf - fl0
    if rel < 0: sg = A["sign_d"]; al = 1
    elif rel < len(pattern) * 2:
        on = pattern[rel // 2]
        sg = A["sign_d"] if rel < len(pattern) else A["sign_m"]; al = 1.0 if on else 0.25
    else: sg = A["sign_m"]; al = 1
    paste(world, with_alpha(sg, al), 240 - PH_OX, 480 - PH_OY)
    jam(world, 2, 540, 1700, 1000, i, k, t)
    counter_on(world, 1300)
    q = ease_out_cubic(lt / dur)
    return camera(world, PH_OX, PH_OY, 540, lerp(900, 960, q), 1.3 - 0.3 * q)

def s13(i, k, t, lf, lt, dur):
    world = A["dusty_nc"].copy()
    # calendar with pages flying off
    cal = A["calendar_base"]; cx0, cy0 = 850, 400
    paste(world, cal, cx0 - PH_OX, cy0 - PH_OY)
    pages = A["cal_pages"]
    for j in reversed(range(len(pages))):
        if lt < j * 0.05: paste(world, pages[j], cx0 - PH_OX, cy0 - PH_OY)
    for j, pg in enumerate(pages):
        d = lt - j * 0.05
        if d < 0 or d > 0.5: continue
        e = d / 0.5
        place(world, pg, cx0 + pg.width / 2 - 520 * e - 60 * j * e, cy0 + pg.height / 2 - 300 * e + 600 * e * e, scale=1 + 0.5 * e,
              rot=60 * e * (1 if j % 2 else -1), alpha=1 - e ** 2, ox=PH_OX, oy=PH_OY)
    jam(world, 9, 480, 1760, 1000, i, k, t)
    counter_on(world, 1300)
    reg = A["register"]; paste(world, reg, 930 - PH_OX, 1310 - reg.height + 8 - PH_OY)
    cw = A["cobweb"].transpose(Image.FLIP_LEFT_RIGHT); paste(world, cw, 930 + reg.width - cw.width + 6 - PH_OX, 1310 - reg.height - 4 - PH_OY)
    dust(world, lt, PH_OX, PH_OY, seed=13)
    q = ease_in_out_sine(lt / dur)
    fr = camera(world, PH_OX, PH_OY, lerp(560, 520, q), lerp(960, 1010, q), 1.0 + 0.1 * q)
    nt = 0.45
    if lt >= nt:
        s = ease_out_back(clamp01((lt - nt) / 0.28), 2.0)
        notif(fr, s, 1.0)
    return fr

def notif(fr, s, al):
    nb = A["notif"]
    if s <= 0.02: return
    im = nb.resize((max(1, int(nb.width * s)), max(1, int(nb.height * s))), Image.LANCZOS)
    if al < 1: im = with_alpha(im, al)
    y = 470 + nb.height / 2
    fr.paste(im, (int(540 - im.width / 2), int(y - im.height / 2)), im)

DUST = None
def dust(world, lt, ox, oy, seed=0):
    global DUST
    if DUST is None:
        rnd = random.Random(seed)
        DUST = [(rnd.uniform(-300, 1400), rnd.uniform(300, 1700), rnd.uniform(3, 8), rnd.uniform(0, 6.28)) for _ in range(46)]
    d = ImageDraw.Draw(world, "RGBA")
    for x, y, r, ph in DUST:
        xx = x + 30 * math.sin(lt * 0.8 + ph) - ox; yy = y + 20 * math.sin(lt * 0.6 + ph * 1.3) + 25 * lt - oy
        d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(255, 250, 235, 110))

def s14(i, k, t, lf, lt, dur):
    world = A["dusty_nc"].copy()
    paste(world, A["calendar_base"], 850 - PH_OX, 400 - PH_OY)
    jam(world, 8, 540, 1760, 1000, i, k, t)
    counter_on(world, 1300)
    reg = A["register"]; paste(world, reg, 930 - PH_OX, 1310 - reg.height + 8 - PH_OY)
    cw = A["cobweb"].transpose(Image.FLIP_LEFT_RIGHT); paste(world, cw, 930 + reg.width - cw.width + 6 - PH_OX, 1310 - reg.height - 4 - PH_OY)
    dust(world, lt + 2.5, PH_OX, PH_OY, seed=13)
    q = ease_in_out_sine(lt / dur)
    fr = camera(world, PH_OX, PH_OY, lerp(500, 600, q), 990, 1.06)
    if lt < 0.3:
        e = clamp01(lt / 0.3)
        notif(fr, 1 - ease_in_cubic(e) * 0.98, 1 - e)
    return fr

def s15(i, k, t, lf, lt, dur):
    world = A["win_wall"].copy()
    # window content: street + joggers
    x0, y0, x1, y1 = WIN
    cont = A["street_win"].copy()
    gy = (y1 - y0) * 0.8 + 26
    for j, (name, im, mir) in enumerate(A["joggers"]):
        hh = 470 * (1.0 if name != "cust2_02" else 1.05) * (0.96 + 0.04 * (j % 2))
        xj = 330 + 470 * (lt - 0.45) - j * 290
        if xj < -300 or xj > cont.width + 300: continue
        bounce = abs(math.sin(2 * math.pi * 2.3 * lt + j * 1.3))
        wav = 4.0 * math.sin(2 * math.pi * 2.8 * lt + j) if name != "cust2_02" else 2.0 * math.sin(2 * math.pi * 2.3 * lt)
        yb = gy - 16 * bounce
        sh = soft_shadow(hh * 0.4, hh * 0.05, 0.22); paste(cont, sh, xj - sh.width / 2, gy - sh.height / 2)
        draw_char(cont, name, xj, yb, hh, 0, 0, mirror=mir, rot=wav, sy=1 + 0.03 * bounce, img=im, max_check=False)
        # basket near the lower hand
        hp = {"cust_10": (0.62, 0.53), "cust_07": (0.84, 0.58), "cust2_02": (0.22, 0.5)}[name]
        bx, by = sprite_point(name, hp[0], hp[1], xj, yb, hh, mirror=mir)
        bk = A["basket"]
        place(cont, bk, bx, by + bk.height * 0.25, scale=0.62, rot=wav * 0.5)
    paste(world, cont, x0 - WN_OX, y0 - WN_OY)
    paste(world, A["win_frame"], A["wf_x"] - WN_OX, A["wf_y"] - WN_OY)
    pe = ease_in_out(clamp01(lt / 0.6))
    cx = lerp(1640, 590, pe) + 40 * clamp01((lt - 0.6) / 1.5)
    par = (cx - 590) * 0.35
    jam(world, 7, 120 - par, 1960, 1250, i, k, t, ox=WN_OX, oy=WN_OY, mirror=True)
    fr = camera(world, WN_OX, WN_OY, cx, 960, 1.0)
    rem = SC_END_FRAME[k] - i
    if rem <= 3: puff_screen(fr, 0.2 * (4 - rem) / 4, 560, 1180)
    return fr

def s16(i, k, t, lf, lt, dur):
    world = A["blog"].copy()
    x, yb = A1["x"] + 40, A1["yb"]
    rot = 1.6 * math.sin(2 * math.pi * 5 * lt) * clamp01((lt - 0.2) / 0.2)
    blogger(world, 10, x, yb, i, k, t, rot=rot)
    name = "blogger_10"; h = sprite(name).height * K_BLOG
    px, py = sprite_point(name, 0.12, 0.33, x, yb, h)
    ap = A["apple"]
    place(world, ap, px + 4, py - 40, scale=1.15, rot=-rot, ox=BL_OX, oy=BL_OY)
    paste(world, A["phone"], A["phone_x"] - BL_OX, A["phone_y"] - BL_OY)
    q = clamp01(lt / 0.6)
    z = ZB * (1.12 - 0.12 * ease_out_back(q, 2.0))
    fr = camera(world, BL_OX, BL_OY, 540, 670, z)
    if lf < 6: pp = 0.2 + 0.35 * lf / 6
    else: pp = 0.55 + 0.45 * clamp01((lf - 6) / 8.0)
    puff_screen(fr, pp, 560, 1180)
    return fr

def s17(i, k, t, lf, lt, dur):
    world = A["blog"].copy()
    x, yb = 470, A1["yb"]
    cp = ease_out_back(clamp01((lt - 0.08) / 0.45), 1.4)
    cx_card = lerp(1560, 905, cp); cy_card = 935
    card = A["card"]
    place(world, card, cx_card, cy_card, rot=lerp(-12, 4, cp), ox=BL_OX, oy=BL_OY)
    tp = ease_out_back(clamp01((lt - 0.4) / 0.35), 2.0)
    if tp > 0.02:
        for j, tim in enumerate(A["card_title"]):
            place(world, tim, cx_card, cy_card - card.height / 2 - 150 + j * 70, scale=max(0.02, tp), ox=BL_OX, oy=BL_OY)
    blogger(world, 8, x, yb, i, k, t)
    paste(world, A["phone"], A["phone_x"] + 170 - BL_OX, A["phone_y"] - BL_OY)
    q = ease_in_out_sine(lt / dur)
    return camera(world, BL_OX, BL_OY, 540, 670 + 20 * q, ZB * (1 + 0.06 * q))

def s18(i, k, t, lf, lt, dur):
    world = A["blog"].copy()
    last = N_FRAMES - 1
    mstart = last - 15
    mp = ease_in_out(clamp01((i - mstart) / 15.0))
    final_pose = i >= mstart
    if final_pose:
        name = "blogger_06"; h = sprite(name).height * K_BLOG
        sy = 1.0 if i == last else breathe(t) * (1 - 0 * mp)
        if i >= last - 1: sy = 1.0
        draw_char(world, name, A1["x"], A1["yb"], h, BL_OX, BL_OY, sy=sy)
    else:
        blogger(world, 7, A1["x"], A1["yb"], i, k, t)
    # comment bubble beside him
    cbp = ease_out_back(clamp01((lt - 0.25) / 0.3), 2.2)
    if final_pose: cbp *= 1 - ease_in_cubic(clamp01((i - mstart) / 8.0))
    if cbp > 0.02:
        cb = A["comment"]
        place(world, cb, 905, 690 + 8 * math.sin(lt * 3), scale=cbp, ox=BL_OX, oy=BL_OY)
    ph = A["phone"]
    paste(world, ph, A["phone_x"] + 60 + 420 * mp - BL_OX, A["phone_y"] - BL_OY)
    zb = ZB * (1 + 0.012 * math.sin(2 * math.pi * lt / 1.6))
    cyb = 670 + 8 * math.sin(2 * math.pi * lt / 1.3)
    z = lerp(zb, 1.0, mp); cx = 540; cy = lerp(cyb, 960, mp)
    if i == last: z, cx, cy = 1.0, 540, 960
    return camera(world, BL_OX, BL_OY, cx, cy, z)

SCENE_FN = {1: s1, 2: s2, 3: s3, 4: s4, 5: s5, 6: s6, 7: s7, 8: s8, 9: s9, 10: s10, 11: s11, 12: s12, 13: s13, 14: s14, 15: s15, 16: s16, 17: s17, 18: s18}

def build_more():
    A["ph_s1"] = ph_world("ph_boxes", sign="sign_d", counter_y=None)
    A["ph_nocounter"] = A["ph_s1"]
    nd = A["ph_boxes"].copy().convert("RGBA"); nd.alpha_composite(A["sign_d"], (240 - PH_OX, 480 - PH_OY))
    A["ph_nocounter_nodoor"] = nd.convert("RGB")
    A["ph_none_nosign"] = (lambda im: (im.alpha_composite(A["door"][0], (1390 - PH_OX, 740 - PH_OY)), im.alpha_composite(A["bell"], (1790 - A["bell"].width // 2 - PH_OX, 762 - PH_OY)), im.convert("RGB"))[-1])(A["ph_none"].copy().convert("RGBA"))
    br = ph_world("ph_boxes", sign="sign_d", counter_y=None)
    A["ph9_bright_nc"] = br
    A["ph9_dark_nc"] = spotlight(br, PH_OX, PH_OY, (520, 1150), 470)
    A["ph9_dark_nc1300"] = A["ph9_dark_nc"]
    # darkened counter for scene 9 (as part of the background)
    cnt = A["counter"]
    a = np.asarray(cnt).astype(np.float32); a[..., :3] *= 0.55
    A["counter_dark"] = Image.fromarray(a.astype(np.uint8), "RGBA")
    beam = Image.new("L", (900, 1500), 0)
    ImageDraw.Draw(beam).polygon([(380, 0), (520, 0), (900, 1500), (0, 1500)], fill=70)
    beam = beam.filter(ImageFilter.GaussianBlur(40))
    bm = Image.new("RGBA", beam.size, (255, 226, 160, 0)); bm.putalpha(beam)
    A["beam"] = bm
    dusty = ph_world("ph_fruits", sign="sign_m", counter_y=None)
    gray = ImageEnhance.Color(dusty).enhance(0.55)
    tint = Image.new("RGB", dusty.size, (196, 184, 160))
    A["dusty_nc"] = Image.blend(gray, tint, 0.18)

def init():
    build_assets()
    build_more()
