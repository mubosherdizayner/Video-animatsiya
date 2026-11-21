# Scene timeline: timing from words.json, per-scene world frames, transitions, overlays.
import json, math, functools, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage
from common import *
import world_pool as WP
import world_paris as WPa
import world_mahalla as WM
import hero as HR
from hero import draw_hero, RA, arm_mix, draw_steam, _lv
from people import person
from overlay import draw_headline, draw_subtitle, headline_img, paste_center, HEAD_CY
from script_data import SCENES

WORDS = json.load(open(os.path.join(BUILD, "words.json")))
AUDIO_DUR = float(open(os.path.join(BUILD, "audio_dur.txt")).read())
N_FRAMES = int(math.floor(AUDIO_DUR * FPS + 1e-6))
END = N_FRAMES / FPS
T_LAST = (N_FRAMES - 1) / FPS
T = {}
for w in WORDS:
    if w["first"] and w["scene"] not in T: T[w["scene"]] = w["start"]
T[1] = 0.0
IDS = sorted(T)
F = {k: int(round(T[k] * FPS)) for k in IDS}
def scene_at(i):
    k = 1
    for kk in IDS:
        if i >= F[kk]: k = kk
    return k
def dur(k): return (F[k + 1] / FPS if k + 1 in F else END) - T[k]

T_FREEZE = 0.42
def te(t):
    if t < T_FREEZE: return t
    if t < T[2]: return T_FREEZE
    return t - (T[2] - T_FREEZE)
P_ENV = te(END)
HR.STEAM_P = P_ENV
BANK_Y = 1305.0

# ---------------------------------------------------------------- hero in the pool world
def auto_arm(yaw, walk, phase):
    sw = walk * 22 * math.sin(phase + math.pi)
    return (_lv((-4 + sw * 0.35, -205), (-44, -208), yaw), _lv((10 + sw, -141), (-46, -140), yaw))

def hero_pool(t):
    """returns (X, kwargs) for scenes 1-3, 14, 17"""
    if t < T[4]:
        a = clamp01(t / 0.3)
        X = lerp(366, 392, ease_out(a))
        walk = 1 - ease_io(a); ph = math.pi / 2 + math.pi / 2 * ease_io(a)
        yaw = smooth(0.18, 0.40, t)
        raise_ = smooth(0.20, T_FREEZE, t)
        arm = arm_mix(auto_arm(yaw, walk, ph), "stop", raise_)
        shape = "open" if raise_ > 0.35 else "fist"
        kw = dict(yaw=yaw, walk=walk, phase=ph)
        if t >= T_FREEZE and t < T[2]:
            b = 1.5 * math.sin(2 * math.pi * 0.9 * (t - T_FREEZE))
            arm = (arm[0], (arm[1][0], arm[1][1] + b))
        if t >= T[2]:
            lo = smooth(T[2], T[2] + 0.35, t)
            arm = arm_mix("stop", "hang_f", lo)
            shape = "open" if lo < 0.55 else "fist"
            kw["head_tilt"] = -5 * smooth(T[2] + 0.4, T[2] + 0.9, t)
        kw.update(rarm=arm, rshape=shape)
        return X, kw
    if T[14] <= t < T[15]:
        u = t - T[14]
        if u < 0.95:
            X = lerp(392, 600, u / 0.95 * 0.85 + 0.15 * ease_out(u / 0.95))
            walk = 1 - smooth(0.8, 0.95, u); ph = 2 * math.pi * 1.85 * u + 0.4
        else:
            X = 600; walk = 0.0; ph = 0.0
        yaw = smooth(1.30, 1.50, u)
        arm = auto_arm(0, walk, ph)
        shape = "fist"
        if u >= 0.9:
            arm = arm_mix(auto_arm(0, 0, 0), "door", smooth(0.9, 1.08, u))
        if u >= 1.28:
            arm = arm_mix("door", "chest", smooth(1.28, 1.6, u)); shape = "flat" if u > 1.45 else "fist"
        bow = 18 * smooth(1.55, 1.95, u) - 3 * smooth(2.25, 2.5, u)
        return X, dict(yaw=yaw, walk=walk, phase=ph, rarm=arm, rshape=shape, bow=bow)
    if t >= T[17]:
        u = t - T[17]; D = T_LAST - T[17]
        v = smooth(D - 0.5, D, u)
        tap = 5 * math.sin(2 * math.pi * 2.2 * u) * smooth(0.25, 0.45, u) * (1 - v)
        pd = RA["point_down"]
        pd = (pd[0], (pd[1][0], pd[1][1] + tap))
        arm0 = arm_mix("hang_f", pd, smooth(0.0, 0.28, u))
        yaw = 1 - v; walk = v; ph = math.pi / 2
        arm = arm_mix(arm0, auto_arm(yaw, walk, ph), v)
        X = lerp(392, 366, ease_io(v))
        shape = "point" if v < 0.5 and u > 0.08 else "fist"
        return X, dict(yaw=yaw, walk=walk, phase=ph, rarm=arm, rshape=shape, rangle=100)
    return 392, dict(yaw=1.0)

def cam_pool(t):
    if t < T[2]:
        u = ease_io(t / T[2]); return (lerp(540, 528, u), lerp(960, 985, u), lerp(1.0, 1.04, u))
    if t < T[3]:
        u = t - T[2]; e = ease_io5(clamp01(u / 1.05))
        c0, c1 = cam_pool(T[2] - 1e-6), (458.0, 975.0, 2.5)
        return (lerp(c0[0], c1[0], e), lerp(c0[1], c1[1], e), lerp(c0[2], c1[2], e))
    if t < T[4] + 1:
        u = ease_io((t - T[3]) / dur(3)); return (458.0, lerp(975, 950, u), lerp(2.5, 2.62, u))
    if T[14] <= t < T[15]:
        u = ease_io((t - T[14]) / dur(14)); return (lerp(585, 540, u), lerp(1060, 960, u), lerp(1.1, 1.0, u))
    return (540.0, 960.0, 1.0)

KOSA = dict(cx=720.0, base=BANK_Y, k=13.0)

def pool_frame(t, blur=0.0, extra=None, kosa=None):
    tev = te(t)
    cam = cam_pool(t)
    X, kw = hero_pool(t)
    info = {}
    def hero_fn(c):
        c.layer(1.0); info.update(draw_hero(c, X, BANK_Y, 1.0, steam_t=tev, **kw))
    if blur <= 0:
        cv = Canvas(); cv.set_cam(*cam)
        WP.draw_pool(cv, tev, P_ENV, kosa=kosa, hero_fn=hero_fn)
        if kosa:
            draw_kosa_steam(cv, kosa, tev)
        if extra: extra(cv, info)
        img = cv.result()
        cv.layer(1.0)
        img = WP.reflect(img, cv, tev, P_ENV)
        return img, info
    cv = Canvas(); cv.set_cam(*cam)
    WP.draw_pool(cv, tev, P_ENV, hero_fn=None, leaves=False)
    img = cv.result()
    cv.layer(1.0)
    img = WP.reflect(img, cv, tev, P_ENV)
    img = img.filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(img).astype(np.float32)
    a = a * (1 - 0.10 * min(1, blur / 6)) + np.array(MTN2, np.float32) * 0.10 * min(1, blur / 6)
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    lay = Canvas(rgba=True); lay.set_cam(*cam)
    hero_fn(lay)
    WP.leaves_falling(lay, tev, P_ENV)
    if extra: extra(lay, info)
    top = lay.result()
    img = img.convert("RGBA"); img.alpha_composite(top)
    return img.convert("RGB"), info

def draw_kosa_steam(cv, kosa, tev):
    k = kosa["k"]; rim = kosa["base"] - 25 * k
    def L(p): return p
    draw_steam(cv, L, kosa["cx"], rim - 4, 1.0, tev, scale=k / 3.2, opacity=0.55, height=60)

# ---------------------------------------------------------------- steam word "restaurant"
WORD_ZREF = 2.62
WORD_WORLD_SIZE = 50.0
@functools.lru_cache(maxsize=1)
def word_base():
    px = WORD_WORLD_SIZE * WORD_ZREF
    im = text_runs([("restaurant", (255, 255, 255))], px, FONT_XBOLD, tracking=px * 0.02)
    pad = 120
    big = Image.new("L", (im.width + 2 * pad, im.height + 2 * pad), 0)
    big.paste(im.getchannel("A"), (pad, pad))
    M = np.asarray(big, np.float32) / 255.0
    h, w = M.shape
    n1 = fractal_noise(w * 2, h * 2, 41, (90, 45, 22), (0.55, 0.3, 0.15))
    n2 = fractal_noise(w * 2, h * 2, 43, (90, 45, 22), (0.55, 0.3, 0.15))
    return M, n1, n2

def steam_word(frame, cv, p, t, wx, wy, fade=1.0, rise=0.0):
    """formation progress p (0..1); world center (wx, wy). frame: 1x RGB PIL image (modified)"""
    if p <= 0.001 or fade <= 0.001: return frame
    M, n1, n2 = word_base()
    h, w = M.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ep = ease_out(p)
    A = lerp(46, 2.6, ep)
    ox, oy = int(t * 22) % w, int(t * 31) % h
    dx = (n1[(yy.astype(int) + oy) % (2 * h), (xx.astype(int) + ox) % (2 * w)] - 0.5) * 2 * A
    dy = (n2[(yy.astype(int) + oy) % (2 * h), (xx.astype(int) + ox) % (2 * w)] - 0.5) * 2 * A
    cxw, cyw = w / 2, h / 2
    sx = lerp(0.22, 1.0, ep)
    src_x = cxw + (xx - cxw) / sx + dx
    src_y = yy + dy + (1 - ep) * h * 0.55
    W2 = ndimage.map_coordinates(M, [src_y, src_x], order=1, mode="constant")
    rev = np.clip((yy - (h * (1.15 - 1.4 * ep))) / (h * 0.25) + 0.5, 0, 1)
    W2 = W2 * rev
    sig = lerp(9.0, 2.0, ep)
    W2 = ndimage.gaussian_filter(W2, sig)
    shadow = ndimage.gaussian_filter(W2, 12)
    a_core = np.clip(W2 * 1.25, 0, 1) * 0.95 * fade * clamp01(p * 3)
    a_sh = np.clip(shadow * 1.2, 0, 1) * 0.30 * fade * clamp01(p * 3)
    rgba = np.zeros((h, w, 4), np.float32)
    # composite core over shadow (premultiplied)
    shc = np.array(HOUSE, np.float32); cc = np.array(CREAM, np.float32)
    out_a = a_core + a_sh * (1 - a_core)
    col = (cc[None, None] * a_core[..., None] + shc[None, None] * (a_sh * (1 - a_core))[..., None]) / np.maximum(out_a[..., None], 1e-4)
    rgba[..., :3] = col; rgba[..., 3] = out_a * 255
    im = Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA")
    scale = cv.ez / WORD_ZREF
    im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.BILINEAR)
    sx_, sy_ = cv.to_screen(wx, wy - rise)
    frame = frame.convert("RGBA")
    frame.alpha_composite(im, (int(sx_ - im.width / 2), int(sy_ - im.height / 2))) if (0 <= int(sx_ - im.width / 2) and 0 <= int(sy_ - im.height / 2)) else _ac(frame, im, sx_, sy_)
    return frame.convert("RGB")

def _ac(frame, im, cx, cy):
    x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    x0, y0 = max(0, x), max(0, y)
    crop = im.crop((x0 - x, y0 - y, min(im.width, frame.width - x), min(im.height, frame.height - y)))
    frame.alpha_composite(crop, (x0, y0))

WORD_W = (458.0, 900.0)

def scene_1(t):
    img, _ = pool_frame(t); return img

def scene_2(t):
    u = t - T[2]
    p = smooth(0.12, 1.25, u)
    def extra(cv, info):
        if 0.0 < u < 1.4:
            bx, by = info["bowl_top"]
            def L(q): return q
            draw_steam(cv, L, bx, by, 1.0, te(t) * 1.6, scale=1.5, opacity=0.65 * (1 - smooth(1.0, 1.4, u)), height=95)
    img, info = pool_frame(t, extra=extra)
    cv = Canvas.__new__(Canvas); cv.ss = 1; cv.cam = cam_pool(t); cv.layer(1.0); cv.ox = cv.oy = 0
    return steam_word(img, cv, p, t, *WORD_W)

def scene_3(t):
    u = t - T[3]
    blur = 6.5 * smooth(0.0, 0.5, u)
    img, info = pool_frame(t, blur=blur)
    cv = Canvas.__new__(Canvas); cv.ss = 1; cv.cam = cam_pool(t); cv.layer(1.0); cv.ox = cv.oy = 0
    shimmer = 1.0 + 0.0 * u
    return steam_word(img, cv, 1.0, t, WORD_W[0], WORD_W[1], rise=14 * ease_io(u / dur(3)))

# ---------------------------------------------------------------- Paris
def lit_state(t):
    L = {}
    if t < T[8]:
        L = dict(A=1.0, A_door=1.0, B=0.0, B2=0.0, C=0.0)
    elif t < T[9]:
        u = t - T[8]; d = 1 - smooth(0.3, 1.4, u)
        L = dict(A=d, A_door=d, B=0.0, B2=0.0, C=0.0)
    elif t < T[10]:
        u = t - T[9]
        L = dict(A=smooth(0.1, 0.25, u), A_door=smooth(0.3, 0.45, u), B=smooth(0.55, 0.7, u), B2=smooth(0.8, 0.95, u), C=smooth(1.05, 1.2, u))
    else:
        L = dict(A=1.0, A_door=1.0, B=1.0, B2=1.0, C=1.0)
    return L
LIGHT_TIMES = [0.1, 0.3, 0.55, 0.8, 1.05]

def sip_curve(u, up, down):
    return smooth(up, up + 0.3, u) - smooth(down - 0.3, down, u)

def paris_state(t):
    st = dict(t=t, lit=lit_state(t), lamps=1.0)
    # sun, warmth, crowd
    st["sun_y"] = 700 if t < T[8] else lerp(700, 520, ease_io((t - T[8]) / 1.8))
    if t < T[5]: st["warm"] = 0.0
    elif t < T[8]: st["warm"] = 0.6 * smooth(T[5], T[5] + 2.2, t)
    else: st["warm"] = 0.6 * (1 - smooth(T[8], T[8] + 1.8, t))
    if T[5] <= t < T[8] + 1.2:
        st["crowd"] = smooth(T[5], T[5] + 0.4, t) * (1 - smooth(T[8], T[8] + 1.0, t))
        st["crowd_t"] = t - T[5]
    # cafe customers
    if st["lit"]["A"] > 0.5:
        if t < T[5]:
            u = t - T[4]
            hun = 0.8 * (1 - smooth(1.85, 2.3, u))
            sips = [sip_curve(u, 0.15, 1.0), sip_curve(u, 0.5, 1.45), sip_curve(u, 0.9, 1.8)]
        else:
            u = t - T[5]
            hun = 0.0
            sips = [max(0, math.sin(2 * math.pi * (0.35 * u + k * 0.37))) ** 2 for k in range(3)]
        st["sippers"] = (hun, sips)
    if t >= T[9]:
        st["plaques"] = smooth(T[9] + 0.35, T[9] + 1.2, t)
    if T[6] <= t < T[8]:
        st["doorC"] = smooth(T[6] + 1.55, T[6] + 1.85, min(t, T[7] - 0.001))
    if t >= T[11]:
        st["doorB"] = smooth(T[11] + 0.55, T[11] + 0.8, t)
    if t >= T[12]:
        st["hand_bowl"] = (smooth(T[12] + 0.4, T[12] + 1.2, t), t)
    if t >= T[13]:
        u = t - T[13]
        st["fasciaB_text"] = 1.0 if u >= 1.0 else 0.0
        st["fasciaB_glow"] = math.sin(math.pi * clamp01((u - 1.0) / 0.55)) if u >= 1.0 else 0.0
    return st

def cam_paris(t):
    if t < T[5]:
        u = ease_io((t - T[4]) / dur(4)); return (lerp(420, 760, u), 1180.0, 1.0)
    if t < T[6]:
        u = ease_io((t - T[5]) / dur(5)); return (lerp(760, 880, u), lerp(1180, 1070, u), 1.0)
    if t < T[8]:
        u = ease_io((t - T[6]) / dur(6)); return (lerp(1750, 2020, u), 1180.0, 1.0)
    if t < T[9]:
        u = ease_io((t - T[8]) / dur(8)); return (900.0, 1180.0, lerp(1.12, 1.0, u))
    if t < T[10]:
        u = ease_io((t - T[9]) / dur(9)); return (lerp(900, 1180, u), 1180.0, 1.0)
    if t < T[11]:
        u = ease_io((t - T[10]) / dur(10)); return (1180.0, 1180.0, lerp(1.0, 0.93, u))
    if t < T[12]:
        u = ease_io((t - T[11]) / dur(11)); return (1255.0, 1420.0, lerp(1.62, 1.74, u))
    if t < T[13]:
        u = ease_io((t - T[12]) / dur(12)); return (lerp(1255, 1222, u), 1420.0, 1.74)
    u = ease_io((t - T[13]) / dur(13)); return (1222.0, lerp(1420, 1345, u), 1.74)

def chefs_post(t):
    u = t - T[6]
    def post(cv):
        cx, cy, z = cv.cam
        ecx_mid = 540 + (cx - 540) * WPa.P_MID
        ecy_mid = 960 + (cy - 960) * WPa.P_MID
        gate_sx = 540 + (1260 - ecx_mid)
        gate_sy = 960 + (WPa.MID_BASE - ecy_mid)
        door_sx = 540 + (2245 - cx); door_sy = 960 + (WPa.NEAR_BASE + 20 - cy)
        street_y = 960 + (WPa.NEAR_BASE + 92 - cy)
        cv.screen()
        for j in range(3):
            v = u - 0.28 * j
            if v < 0: continue
            if v < 0.85:
                e = ease_io(v / 0.85)
                x = lerp(gate_sx + (j - 1) * 22, gate_sx + 70 + j * 18, e)
                y = lerp(gate_sy - 4, street_y - j * 6, e)
                h = lerp(118, 205, e)
                al = int(255 * clamp01(v / 0.18))
            else:
                w_ = clamp01((v - 0.85) / 0.9)
                tx = door_sx - 12 - j * 78
                x = lerp(gate_sx + 70 + j * 18, tx, ease_io(w_))
                y = lerp(street_y - j * 6, door_sy if j == 0 else street_y - j * 6 - 20 * w_, ease_io(w_))
                h = lerp(205, 200, w_); al = 255
            arm = None
            if j == 0 and v > 1.55:
                rr = smooth(1.55, 1.75, v)
                arm = ((lerp(1, 12, rr), lerp(-63, -64, rr)), (lerp(4, 30, rr), lerp(-48, -60, rr)))
            walking = 1.0 if (v < 1.7 or j > 0) else 1 - smooth(1.7, 1.85, v)
            person(cv, x, y, h, NEAR2, walk=walking, phase=v * 11 + j, face=1, hat="toque", hat_col=MTN1,
                   carry="bundle", carry_col=CITY, arm=arm, alpha=al)
        cv.layer(1.0)
    return post

def s11_post(t):
    u = t - T[11]
    def post(cv):
        cv.layer(1.0)
        for j, (t0, x0) in enumerate(((0.0, 1030), (0.6, 960))):
            v = u - t0
            if v < 0: continue
            if v < 0.85:
                x = lerp(x0, 1285, v / 0.85); y = 1652; al = 255; h = 212
            else:
                e = clamp01((v - 0.85) / 0.25)
                if e >= 1: continue
                x = 1285; y = lerp(1652, 1606, e); al = int(255 * (1 - e)); h = 212 * (1 - 0.08 * e)
            person(cv, x, y, h, NEAR2, walk=0.7, phase=v * 7.5 + j, face=1, hunch=0.85, hat="tricorn" if j == 0 else "bonnet",
                   skirt=(j == 1), alpha=al)
    return post

def s12_post(t):
    u = t - T[12]
    def post(cv):
        cv.layer(1.0)
        for j, (t0, x1, face) in enumerate(((0.1, 1600, 1), (0.75, 960, -1))):
            v = u - t0
            if v < 0: continue
            if v < 0.25:
                e = v / 0.25; x = 1285; y = lerp(1606, 1652, e); al = int(255 * e); h = lerp(196, 214, e)
            else:
                x = lerp(1285, x1, clamp01((v - 0.25) / 1.1)); y = 1652 + 6 * j; al = 255; h = 214
            person(cv, x, y, h, NEAR2, walk=1.0, phase=v * 12 + j, face=face, hunch=-0.05, hat="tricorn" if j == 0 else None, alpha=al)
    return post

LETTERS = "RESTAURANT"
def s13_post(t):
    u = t - T[13]
    def post(cv):
        cv.layer(1.0)
        if u >= 1.05: return
        fx0, fy0, fx1, fy1 = WPa.NEAR["B"]["fascia"]
        fcx, fcy = (fx0 + fx1) / 2, (fy0 + fy1) / 2
        f = font(FONT_BLACK, 30); trk = 30 * 0.06
        widths = [f.getlength(c) + trk for c in LETTERS]; tot = sum(widths)
        xs = []; acc = fcx - tot / 2
        for wv in widths: xs.append(acc + wv / 2); acc += wv
        bx, by = 1105, 1440
        for j, ch in enumerate(LETTERS):
            v = (u - 0.06 - j * 0.045) / 0.78
            if v <= 0: continue
            v = clamp01(v); e = ease_io(v)
            tx, ty = xs[j], fcy
            c1 = (lerp(bx, tx, 0.3) - 30, min(by, ty) - 150)
            x = (1 - e) ** 2 * bx + 2 * (1 - e) * e * c1[0] + e * e * tx
            y = (1 - e) ** 2 * by + 2 * (1 - e) * e * c1[1] + e * e * ty
            size = lerp(18, 30, e)
            blur = lerp(5, 0.3, e)
            px = cv.S(size)
            im = text_runs([(ch, CREAM)], px, FONT_BLACK)
            if blur > 0.4: im = im.filter(ImageFilter.GaussianBlur(cv.S(blur) * 0.5))
            a = 0.92 * clamp01(v * 4)
            im.putalpha(im.getchannel("A").point(lambda q: int(q * a)))
            rr = 14 * math.sin(v * 6.28) * (1 - e)
            if abs(rr) > 0.5: im = im.rotate(rr, resample=Image.BICUBIC, expand=True)
            sx, sy = cv.T(x, y + math.sin(v * 9 + j) * 6 * (1 - e))
            cv.paste_rgba(im, sx - im.width / 2, sy - im.height / 2)
        # steam rising from the bowl while letters leave
        if u < 1.0:
            draw_steam(cv, lambda q: q, bx, by - 8, 1.0, t * 1.4, scale=1.1, opacity=0.6 * (1 - smooth(0.7, 1.0, u)), height=60)
    return post

def paris_frame(t, st=None, cam=None):
    st = st or paris_state(t)
    st["cam"] = cam or cam_paris(t)
    if T[6] <= t < T[7] + 0.0001: st["post"] = chefs_post(t)
    elif T[11] <= t < T[12]: st["post"] = s11_post(t)
    elif T[12] <= t < T[13]: st["post"] = s12_post(t)
    elif T[13] <= t < T[14]: st["post"] = s13_post(t)
    if T[12] <= t < T[14] and st.get("hand_bowl"):
        pass
    cv = Canvas()
    WPa.draw_paris(cv, st)
    if T[12] <= t < T[13] and st["hand_bowl"][0] > 0.2:
        cv.layer(1.0)
        draw_steam(cv, lambda q: q, 1105, 1528 - 70 * ease_io(st["hand_bowl"][0]) - 12, 1.0, t, scale=1.0, opacity=0.55, height=55)
    img = cv.result()
    cv.layer(1.0)
    img = WP.reflect(img, cv, t, 33.0, sun_x=None, water_y=WPa.NEAR_BASE + 46, tint=(40, 52, 56), mix0=0.74, streaks=0.35,
                     depth_px=380, amp0=0.5)
    return img

def scene_paris(t): return paris_frame(t)

# ---------------------------------------------------------------- scene 7: tear
def jag_line(seed=3):
    rnd = random.Random(seed); pts = []
    y = -40
    while y < H + 60:
        pts.append((540 + 38 * math.sin(y * 0.006 + 0.8) + rnd.uniform(-16, 16), y)); y += rnd.uniform(18, 34)
    return pts
JAG = jag_line()

@functools.lru_cache(maxsize=1)
def paper_halves():
    paper = paris_frame(T[7] - 1.0 / FPS).convert("RGBA")
    halves = []
    for side in (-1, 1):
        m = Image.new("L", (W, H), 0); d = ImageDraw.Draw(m)
        poly = ([(-50, -50)] + JAG + [(-50, H + 60)]) if side < 0 else ([(W + 50, -50)] + JAG + [(W + 50, H + 60)])
        d.polygon(poly, fill=255)
        im = paper.copy(); im.putalpha(m)
        e = Image.new("RGBA", (W, H), (0, 0, 0, 0)); de = ImageDraw.Draw(e)
        de.line([(x + side * -2, y) for x, y in JAG], fill=CREAM + (255,), width=7)
        e.putalpha(Image.fromarray(np.minimum(np.asarray(e.getchannel("A")), np.asarray(m))))
        im.alpha_composite(e)
        halves.append(im)
    return halves

def scene_7(t):
    u = t - T[7]
    base = paris_frame(T[8], st=s8_state0(), cam=cam_paris(T[8]))
    img = base.convert("RGBA")
    if u < 0.16:
        paper = paris_frame(T[7] - 1.0 / FPS).convert("RGBA")
        img = paper
        crack = clamp01((u - 0.06) / 0.1)
        if crack > 0:
            d = ImageDraw.Draw(img)
            n = int(len(JAG) * crack)
            if n > 1: d.line(JAG[:n], fill=CREAM + (255,), width=4)
    else:
        v = clamp01((u - 0.16) / 0.62); e = v * v
        for side, im in zip((-1, 1), paper_halves()):
            ang = side * -11 * e
            dx, dy = side * 170 * e, 1100 * e
            rim = im.rotate(ang, resample=Image.BICUBIC, center=(540 + side * 270, 960), translate=(dx, dy))
            sh = Image.new("RGBA", rim.size, (0, 0, 0, 0))
            sh.putalpha(rim.getchannel("A").point(lambda q: int(q * 0.35)).filter(ImageFilter.GaussianBlur(14)))
            sh = sh.transform(sh.size, Image.AFFINE, (1, 0, side * 14, 0, 1, -12))
            img.alpha_composite(sh)
            img.alpha_composite(rim)
    # hero slides in (front layer)
    cv = Canvas(rgba=True); cv.screen()
    sl = ease_out(clamp01(u / 0.22))
    X = lerp(1260, 845, sl)
    sh_amt = math.sin(2 * math.pi * 3.2 * (u - 0.22)) * (1 - smooth(0.7, 1.0, u)) if u > 0.22 else 0.0
    draw_hero(cv, X, 1880, 1.32, yaw=1.0, dir=-1, rarm=RA["finger"], rshape="finger_up", shake=sh_amt, steam_t=te(t),
              walk=0.0)
    img.alpha_composite(cv.result())
    return img.convert("RGB")

def s8_state0():
    st = paris_state(T[8]); return st

def scene_8(t):
    u = t - T[8]
    img = paris_frame(t)
    # hero slides out to the right; leaves drift upward (rewind)
    cv = Canvas(rgba=True); cv.screen()
    if u < 0.32:
        X = lerp(845, 1300, ease_in(u / 0.32))
        draw_hero(cv, X, 1880, 1.32, yaw=1.0, dir=-1, rarm=RA["finger"], rshape="finger_up", steam_t=te(t))
    WP.leaves_falling(cv, u, 2.7, n=9, seed=19, region=(80, 1000, 1500, 1880), wind=10, up=True)
    img = img.convert("RGBA"); img.alpha_composite(cv.result())
    return ribbon_rewind(img.convert("RGB"), u)

def scene_9(t): return paris_frame(t)

def scene_10(t):
    return ribbon_span(paris_frame(t), t - T[10])

# ---------------------------------------------------------------- ribbons
RIB_Y = 650
@functools.lru_cache(maxsize=64)
def label_img(text, size, col=INK):
    return glow(text_runs([(text, col)], size, FONT_BLACK), CREAM, 9, strength=2.4, spread=7)

def _rib_canvas():
    cv = Canvas(rgba=True); cv.screen(); return cv

def ribbon_rewind(img, u):
    cv = _rib_canvas()
    g = ease_out(clamp01(u / 0.28))
    x0, x1 = 540 - 400 * g, 540 + 400 * g
    halo(cv, x0, x1)
    cv.line([(x0, RIB_Y), (x1, RIB_Y)], BANK, 11)
    for xx in (x0, x1): cv.rect(xx - 2.5, RIB_Y - 16, xx + 2.5, RIB_Y + 16, BANK)
    m = ease_io(clamp01((u - 0.3) / 1.3))
    mx = lerp(880, 220, m)
    year = int(round(lerp(1789, 1760, m)))
    out = img.convert("RGBA")
    if g > 0.6:
        cv.circle(mx, RIB_Y, 19, CREAM); cv.circle(mx, RIB_Y, 13, ACCENT)
        cv.line([(mx, RIB_Y), (lerp(880, mx, 1.0), RIB_Y)], ACCENT, 5)
        if m > 0.02: cv.line([(mx, RIB_Y), (880, RIB_Y)], ACCENT + (150,), 4)
    out.alpha_composite(cv.result())
    if g > 0.6:
        txt = "1760-yillar" if m >= 0.999 else str(year)
        li = label_img(txt, 50)
        paste_center(out, li, min(max(mx, li.width / 2 + 30), 1050 - li.width / 2), RIB_Y + 62)
    return out.convert("RGB")

def halo(cv, x0, x1):
    def fn(d, tf, k):
        a, b = tf(x0 - 20, RIB_Y - 22), tf(x1 + 20, RIB_Y + 22)
        d.rounded_rectangle((a[0], a[1], b[0], b[1]), radius=20 * k, fill=CREAM + (150,))
    cv.soft((x0 - 30, RIB_Y - 30, x1 + 30, RIB_Y + 30), fn, blur=9, scale=0.35)

def ribbon_span(img, u):
    cv = _rib_canvas()
    g = ease_out(clamp01(u / 0.22))
    s = ease_io(clamp01((u - 0.1) / 1.1))
    xL, xR = lerp(470, 190, s), lerp(610, 890, s)
    a0, a1 = 540 - (540 - xL + 30) * g, 540 + (xR + 30 - 540) * g
    halo(cv, a0, a1)
    cv.line([(a0, RIB_Y), (a1, RIB_Y)], BANK, 11)
    out = img.convert("RGBA")
    if g > 0.5:
        cv.line([(xL, RIB_Y), (xR, RIB_Y)], ACCENT, 5)
        for yr in (1765, 1770, 1775, 1780, 1785):
            tv = clamp01((u - 0.75 - (yr - 1765) * 0.012) / 0.18)
            if tv <= 0: continue
            xx = xL + (xR - xL) * (yr - 1760) / 29
            hh = (15 if yr % 10 == 0 else 9) * ease_out(tv)
            cv.rect(xx - 2.5, RIB_Y - hh, xx + 2.5, RIB_Y + hh, BANK)
        for xx in (xL, xR):
            cv.circle(xx, RIB_Y, 19, CREAM); cv.circle(xx, RIB_Y, 13, ACCENT)
    out.alpha_composite(cv.result())
    if g > 0.5:
        for txt, xx in (("1760-yillar", xL), ("1789", xR)):
            li = label_img(txt, 46)
            paste_center(out, li, min(max(xx, li.width / 2 + 24), 1056 - li.width / 2), RIB_Y + 58)
        for yr in (1770, 1780):
            tv = clamp01((u - 0.85 - (yr - 1770) * 0.02) / 0.2)
            if tv > 0:
                li = label_img(str(yr), 28)
                paste_center(out, li, xL + (xR - xL) * (yr - 1760) / 29, RIB_Y - 40, alpha=tv)
    return out.convert("RGB")

# ---------------------------------------------------------------- scene 14 (giant kosa)
def scene_14(t):
    u = t - T[14]
    kosa = dict(KOSA); kosa["door"] = smooth(1.0, 1.35, u)
    img, _ = pool_frame(t, kosa=kosa)
    return img

# ---------------------------------------------------------------- mahalla (15, 16)
def hero_mahalla(t):
    if t < T[16]:
        u = t - T[15]
        X = 640
        if u < 1.32:
            dr, yaw = -1, 1 - smooth(0.0, 0.18, u)
            arm = arm_mix(RA["hang_p"], "point_up_p", smooth(0.05, 0.3, u)) if u < 1.15 else arm_mix("point_up_p", "hang_p", smooth(1.15, 1.32, u))
            shape = "point" if 0.18 < u < 1.22 else "fist"
            yaw = max(yaw, smooth(1.2, 1.32, u))
        else:
            dr = 1; yaw = 1 - smooth(1.36, 1.52, u)
            arm = arm_mix(RA["hang_p"], "point_up_p", smooth(1.45, 1.7, u))
            shape = "point" if u > 1.6 else "fist"
            if yaw > 0.5: arm = RA["hang_f"]
        return X, dict(dir=dr, yaw=yaw, rarm=arm, rshape=shape, rangle=-40)
    u = t - T[16]
    yaw = smooth(0.0, 0.2, u)
    sc = smooth(0.2, 0.5, u)
    arm = arm_mix(auto_arm(yaw, 0, 0), "scratch", sc)
    wig = 3.5 * math.sin(2 * math.pi * 5 * u) * smooth(0.45, 0.6, u)
    arm = (arm[0], (arm[1][0] + wig, arm[1][1] + abs(wig) * 0.4))
    return 640, dict(dir=1, yaw=yaw, rarm=arm, rshape="scratch" if sc > 0.5 else "fist", head_tilt=-9 * smooth(0.25, 0.6, u))

def cam_mahalla(t):
    if t < T[16]:
        u = ease_io((t - T[15]) / dur(15)); return (lerp(470, 760, u), 1215.0, 1.08)
    u = ease_out((t - T[16]) / dur(16) * 1.25); return (lerp(760, 960, u), lerp(1215, 1200, u), lerp(1.08, 1.2, u))

def mahalla_frame(t):
    st = dict(t=t, cam=cam_mahalla(t))
    u15 = t - T[15]
    st["signA"] = smooth(0.08, 0.3, u15); st["litA"] = st["signA"]
    st["signB"] = smooth(B_LIGHT - T[15], B_LIGHT - T[15] + 0.22, u15); st["litB"] = st["signB"]
    if t >= T[16]:
        u = t - T[16]
        st["q"] = ease_out_back(clamp01((u - 0.05) / 0.25)) * (0.75 + 0.25 * math.cos(2 * math.pi * 1.6 * max(0, u - 0.3)))
    X, kw = hero_mahalla(t)
    info = {}
    def hf(cv):
        cv.layer(1.0); info.update(draw_hero(cv, X, 1640, 1.0, steam_t=t, **kw))
    st["hero_fn"] = hf
    cv = Canvas()
    WM.draw_mahalla(cv, st)
    img = cv.result()
    cv.layer(1.0)
    img = WP.reflect(img, cv, t, 33.0, sun_x=None, water_y=WM.WATER_M, mix0=0.5, streaks=0.8)
    return img

B_LIGHT = next(w["start"] for w in WORDS if w["scene"] == 15 and w["text"].lower().startswith("oshxona"))

def scene_17(t):
    img, _ = pool_frame(t); return img

SCENE_FN = {1: scene_1, 2: scene_2, 3: scene_3, 4: scene_paris, 5: scene_paris, 6: scene_paris, 7: scene_7, 8: scene_8,
            9: scene_9, 10: scene_10, 11: scene_paris, 12: scene_paris, 13: scene_paris, 14: scene_14,
            15: mahalla_frame, 16: mahalla_frame, 17: scene_17}

# ---------------------------------------------------------------- steam wipes
WIPES = {4: dict(pre=8, post=14, origin=(540, 760)), 14: dict(pre=8, post=14, origin=(450, 1000)),
         15: dict(pre=6, post=10, origin=(560, 980)), 17: dict(pre=8, post=14, origin=(560, 1240))}

@functools.lru_cache(maxsize=4)
def wipe_fields(seed):
    n = fractal_noise(W // 4, H // 4, seed, (60, 30, 14, 7), (0.45, 0.3, 0.15, 0.1))
    shade = fractal_noise(W // 4, H // 4, seed + 5, (40, 18), (0.6, 0.4))
    return n, shade

def steam_cover(img, amount, origin, seed=61):
    if amount <= 0.001: return img
    n, shade = wipe_fields(seed)
    yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
    d = np.sqrt((xx * 4 - origin[0]) ** 2 + (yy * 4 - origin[1]) ** 2) / 1500.0
    f = (1 - d) * 0.55 + n * 0.45
    th = 1 - amount * 1.25
    m = np.clip((f - th) / 0.10, 0, 1)
    mi = Image.fromarray((m * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    sh = Image.fromarray(((shade - 0.5) * 255 + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    M = np.asarray(mi, np.float32)[..., None] / 255.0
    S = (np.asarray(sh, np.float32)[..., None] - 128) / 128.0
    steam = np.array(CREAM, np.float32)[None, None] * (1 + 0.045 * S) - np.array([6, 6, 4], np.float32) * np.clip(-S, 0, 1)
    a = np.asarray(img, np.float32)
    out = a * (1 - M * 0.97) + steam * M * 0.97
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

def cool_grade(img, k):
    a = np.asarray(img, np.float32)
    lum = a.mean(axis=2, keepdims=True)
    b = a * (1 - 0.45 * k) + lum * 0.45 * k
    b *= np.array([1 - 0.1 * k, 1 - 0.02 * k, 1 + 0.1 * k], np.float32)
    return Image.fromarray(np.clip(b, 0, 255).astype(np.uint8))

def shake(img, u):
    if u >= 0.3: return img
    k = 1 - u / 0.3
    ox = 8 * math.sin(2 * math.pi * 13 * u) * k
    oy = 5 * math.sin(2 * math.pi * 17 * u + 1.3) * k
    big = img.resize((int(W * 1.02), int(H * 1.02)), Image.BILINEAR)
    x0 = int((big.width - W) / 2 - ox); y0 = int((big.height - H) / 2 - oy)
    return big.crop((x0, y0, x0 + W, y0 + H))

def world_frame(i):
    t = i / FPS
    k = scene_at(i)
    img = SCENE_FN[k](t)
    nk = k + 1
    if nk in WIPES and i >= F[nk] - WIPES[nk]["pre"]:
        wp = WIPES[nk]
        img = steam_cover(img, 0.9 * ease_in((i - (F[nk] - wp["pre"]) + 1) / wp["pre"]), wp["origin"], seed=61 + nk)
    if k in WIPES and i < F[k] + WIPES[k]["post"]:
        wp = WIPES[k]
        img = steam_cover(img, 0.9 * (1 - ease_out((i - F[k] + 1) / (wp["post"] + 1))), (540, 960), seed=71 + k)
    if k == 7:
        u = t - T[7]
        if i - F[7] <= 6: img = cool_grade(img, 1.0 if i - F[7] < 5 else 0.5)
        img = shake(img, u)
    return img

# ---------------------------------------------------------------- overlays
def subtitle_schedule():
    out = []
    for j, w in enumerate(WORDS):
        fs = int(round(w["start"] * FPS))
        if j + 1 < len(WORDS):
            nx = WORDS[j + 1]["start"]
            fe = int(round(nx * FPS))
            if nx - w["voice_end"] > 0.4: fe = int(round(w["voice_end"] * FPS))
        else:
            fe = N_FRAMES
        out.append((fs, fe, w["text"]))
    return out
SUBS = subtitle_schedule()

def overlays(img, i):
    k = scene_at(i); lf = i - F[k]
    if k == 7 and lf < 7:
        # strike through the previous claim (5 frames), it lifts away, then AFSONA pops
        im6 = headline_img(6)
        a = 1 - clamp01((lf - 4) / 3)
        cy6 = HEAD_CY - 30 * clamp01((lf - 4) / 3)
        sc6 = 1.0 - 0.08 * clamp01((lf - 4) / 3)
        paste_center(img, im6, 540, cy6, sc6, a)
        prog = clamp01((lf + 1) / 5)
        d = ImageDraw.Draw(img, "RGBA")
        wv = (im6.width - 70) * sc6
        x0 = 540 - wv / 2
        lines_y = [cy6] if im6.height < 150 else [cy6 - 44 * sc6, cy6 + 46 * sc6]
        for ly in lines_y:
            d.line([(x0, ly + 4), (x0 + wv * prog, ly - 2)], fill=ACCENT + (int(255 * a),), width=10)
        if lf >= 6: draw_headline(img, 7, lf - 6)
    elif k == 7:
        draw_headline(img, 7, lf - 6)
    elif k in (1, 2):
        draw_headline(img, k, lf, pop=False)
    else:
        draw_headline(img, k, lf)
    for (fs, fe, word) in SUBS:
        if fs <= i < fe:
            draw_subtitle(img, word, i - fs); break
    return img

def render_frame(i):
    img = world_frame(i)
    img = apply_grain(img)
    return overlays(img, i)
