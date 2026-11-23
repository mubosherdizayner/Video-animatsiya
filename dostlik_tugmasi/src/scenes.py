# Timeline + the 17 scenes. Every scene draws its own world (no UI); render.py adds plates and subtitles.
import json, math, os
import numpy as np
import skia
from gfx import *
from world import *
from hero import *
from script_data import SCENES, uz, tokens

HERE = os.path.dirname(os.path.abspath(__file__))
TIMING = json.load(open(os.path.join(HERE, "timing.json")))
AUDIO_DUR = float(open(os.path.join(HERE, "audio_dur.txt")).read()) if os.path.exists(os.path.join(HERE, "audio_dur.txt")) else 34.0375
N_FRAMES = int(round(AUDIO_DUR * FPS))
SC_IDS = [sid for sid, _ in SCENES]
SC_START = {k: next(w["start"] for w in TIMING if w["scene"] == k) for k in SC_IDS}
SC_FRAME = {k: int(round(SC_START[k] * FPS)) for k in SC_IDS}
SC_FRAME[1] = 0
SC_END_FRAME = {k: (SC_FRAME[k + 1] if k + 1 in SC_FRAME else N_FRAMES) for k in SC_IDS}
T13 = SC_FRAME[13] / FPS            # timer reaches 0 exactly here

def scene_words(k): return [w for w in TIMING if w["scene"] == k]
def wt(k, i): return scene_words(k)[i]["start"]
def wtt(k, prefix):
    for w in scene_words(k):
        if w["text"].lower().strip('"“').startswith(prefix): return w["start"]
    raise KeyError(prefix)
def word_frame(w): return 0 if (w["scene"] == 1 and w["first"]) else int(round(w["start"] * FPS))
def scene_at_frame(i):
    k = 1
    for s in SC_IDS:
        if i >= SC_FRAME[s]: k = s
    return k

def timer_value(t):
    step = T13 / 20.0
    return int(max(0, min(20, 20 - math.floor(t / step + 1e-6))))
def timer_steps():
    step = T13 / 20.0
    return [k * step for k in range(1, 21)]

QA = {}      # per-frame flags read by qa.py (cta icon / gesture)

def wind_at(t): return 0.55 + 0.35 * math.sin(t * 0.9) + 0.12 * math.sin(t * 2.3)

# ---------------------------------------------------------------- common steppe pieces
NEAR1 = Hill(1262, [(620, 520, 62), (1700, 420, 105), (-300, 300, 30)], 7, 5)

def near_ground(cv, cam, P, t, H_, x0=-1400, x1=2800, wind=1.0, c=None):
    with at_layer(cv, cam, 1.0):
        hill(cv, H_, c or P["L"][4], x0, x1)
        grass(cv, H_, c or P["L"][4], t, x0, x1, 18, 14, 38, wind, 11)

def hook_text(cv, t, a=1.0):
    s = 1.0 + 0.015 * math.sin(t * 4.0)
    with xf(cv, 540, 470, s):
        text(cv, uz("1 TUGMA."), 0, -62, 104, INK, a)
        text(cv, uz("20 SONIYA."), 0, 62, 104, INK, a)

def reach_arm(person_xy, s, facing, target_screen, p, rest=("fk", -4, 12), bend=1.0):
    """interpolate between the rest arm and an IK reach toward a screen point"""
    rx, ry = to_ref(target_screen[0], target_screen[1], person_xy[0], person_xy[1], s, facing)
    e0, w0 = arm_fk(rest[1], rest[2])
    e1, w1 = arm_ik((rx, ry), bend)
    a0 = (math.atan2(e0[1] - SHOULDER[1], e0[0] - SHOULDER[0]), math.atan2(w0[1] - e0[1], w0[0] - e0[0]))
    a1 = (math.atan2(e1[1] - SHOULDER[1], e1[0] - SHOULDER[0]), math.atan2(w1[1] - e1[1], w1[0] - e1[0]))
    u = (lerp(a0[0], a1[0], p), lerp(a0[1], a1[1], p))
    el = (SHOULDER[0] + L_UP * math.cos(u[0]), SHOULDER[1] + L_UP * math.sin(u[0]))
    wr = (el[0] + L_FORE * math.cos(u[1]), el[1] + L_FORE * math.sin(u[1]))
    return ("pts", el, wr)

def angles_arm(a1, a2):
    return ("fk", a1, a2)

# ---------------------------------------------------------------- 1. hook: button in the steppe
PED1_X = 662
def steppe_button_world(cv, t, cam, P, reach_p, friend_extra=None, lean=0.0, eye="open", tag_a=1.0, show_tag=True):
    wind = wind_at(t)
    steppe_layers(cv, cam, P, t, wind=wind, sun_xy=(800, 985), sun_r=235)
    near_ground(cv, cam, P, t, NEAR1, wind=wind)
    with at_layer(cv, cam, 1.0):
        gy = NEAR1.y(PED1_X)
        top = pedestal(cv, PED1_X, gy + 6, 0.78, P["L"][4], mix(P["L"][4], "#8C9FA1", 0.25))
        btn_top = button(cv, PED1_X, top + 4, 0.78, t)
        fx, fy, fs = 482, NEAR1.y(482) + 8, 0.222
        tgt = (PED1_X - 34, btn_top - 52)
        r = draw_person(cv, fx, fy, fs, friend_colors(P["n"]), t=t, wind=wind * 0.7, lean=lean, eye=eye,
                        arm=reach_arm((fx, fy), fs, 1, tgt, reach_p), hand="point" if reach_p > 0.6 else "fist",
                        finger_dir=(1, 0.35), finger_len=clamp01((reach_p - 0.6) / 0.3))
        if show_tag: tag(cv, uz("DO'STING"), r["top"][0] + 6, r["top"][1] - 14, 30, tag_a)
        if friend_extra: friend_extra(cv, r, btn_top)
    return btn_top

def scene1(cv, t, lt, dur):
    P = pal(0)
    z = 1.0 + 0.16 * ease_io(lt / max(dur, 0.1))
    cam = Cam(lerp(540, 610, ease_io(lt / dur)), lerp(900, 1015, ease_io(lt / dur)), z)
    steppe_button_world(cv, t, cam, P, 0.22 + 0.5 * ease_out(lt / 2.6))
    hook_text(cv, t)

# ---------------------------------------------------------------- 2. one million
def scene2(cv, t, lt, dur):
    P = pal(0)
    u = ease_io(lt / dur)
    cam = Cam(lerp(640, 650, u), lerp(1075, 1005, u), lerp(1.62, 1.68, u))
    t_mil = wt(2, 2)
    def extra(cv, r, btn_top):
        pass
    wind = wind_at(t)
    steppe_layers(cv, cam, P, t, wind=wind, sun_xy=(800, 985), sun_r=235)
    with at_layer(cv, cam, 1.0):
        # warm gold glow grows behind the money as it rises
        grow = ease_out(lt / 1.0)
        pulse = 0.85 + 0.15 * math.sin(t * 6.0)
        glow(cv, 690, NEAR1.y(690) - 120, 330, "#E9B949", 0.55 * grow * pulse)
        glow(cv, 690, NEAR1.y(690) - 60, 190, "#F6D774", 0.45 * grow * pulse)
        # cash stacks rise from the ground behind the pedestal
        stacks = [(560, 7, 0.05), (742, 9, 0.18), (812, 6, 0.3), (612, 11, 0.42), (690, 13, 0.25)]
        for k, (sx, n_max, d0) in enumerate(stacks):
            n = int(round(n_max * ease_out((lt - d0) / 0.9)))
            if n > 0: cash_stack(cv, sx, NEAR1.y(sx) + 10, 0.55, n, t, k)
        # sparkles twinkling on the stack tops
        for k, (sx, n_max, d0) in enumerate(stacks):
            n = int(round(n_max * ease_out((lt - d0) / 0.9)))
            if n < 2: continue
            topy = NEAR1.y(sx) + 10 - n * (26 * 0.55 + 1.1)
            for j in range(2):
                ph = (t * 1.7 + k * 0.37 + j * 0.5) % 1.0
                sparkle(cv, sx + (j * 50 - 25) * 0.55 + 8 * math.sin(k + j), topy - 8 - 10 * j, 13 * math.sin(math.pi * ph), 0.95)
    near_ground(cv, cam, P, t, NEAR1, wind=wind)
    with at_layer(cv, cam, 1.0):
        gy = NEAR1.y(PED1_X)
        top = pedestal(cv, PED1_X, gy + 6, 0.78, P["L"][4], mix(P["L"][4], "#8C9FA1", 0.25))
        btn_top = button(cv, PED1_X, top + 4, 0.78, t)
        fx, fy, fs = 482, NEAR1.y(482) + 8, 0.222
        lean = 7 * ease_out((lt - 0.5) / 1.0)
        tgt = (PED1_X - 30, btn_top - 46)
        eye = "dollar" if (t >= t_mil and int((t - t_mil) * 6) % 3 != 2) else "open"
        r = draw_person(cv, fx, fy, fs, friend_colors(0), t=t, wind=wind * 0.7, lean=lean, eye=eye,
                        arm=reach_arm((fx, fy), fs, 1, tgt, 0.72 + 0.2 * ease_out(lt / 1.5)), hand="point",
                        finger_dir=(1, 0.35))
        if t >= t_mil + 0.15:
            k = (t - t_mil - 0.15)
            ex, ey = r["eye"]
            text(cv, "$", ex + 14 + 8 * k, ey - 22 - 14 * k, 20, "#C7A548", clamp01(1 - k / 0.9))
        tag(cv, "$1 000 000", PED1_X, btn_top - 58, 30, 1.0, pop_scale(lt - 0.12, 0.3))
    # coins rain (screen space, in front)
    rng = np.random.default_rng(21)
    for k in range(26):
        x = rng.uniform(180, 1000); v = rng.uniform(700, 1100); d0 = rng.uniform(0.0, 1.6); spin = rng.uniform(4, 9)
        tt = lt - d0
        if tt < 0: continue
        y = -40 + v * tt + 300 * tt * tt
        if y > 1310: continue
        coin(cv, x, y, rng.uniform(15, 23), spin * tt)
    # a few banknotes flutter down between the coins
    rng = np.random.default_rng(33)
    for k in range(9):
        x = rng.uniform(140, 960); d0 = rng.uniform(0.05, 1.3); v = rng.uniform(260, 380); ph = rng.uniform(0, 6.28)
        tt = lt - d0
        if tt < 0: continue
        y = -60 + v * tt
        if y > 1300: continue
        xx = x + 60 * math.sin(tt * 2.4 + ph)
        banknote(cv, xx, y, rng.uniform(0.75, 1.0), 25 * math.sin(tt * 3.1 + ph), math.cos(tt * 4.2 + ph))

# ---------------------------------------------------------------- 3. the hero on the next crest
HERO3_X = 1700
def scene3(cv, t, lt, dur):
    P = pal(0)
    u = ease_io(lt / 1.0)
    cam = Cam(lerp(660, HERO3_X - 40, u), lerp(1025, 965, u), lerp(1.45, 1.32, u))
    wind = wind_at(t)
    steppe_layers(cv, cam, P, t, wind=wind, sun_xy=(820, 985), sun_r=235)
    near_ground(cv, cam, P, t, NEAR1, wind=wind)
    with at_layer(cv, cam, 1.0):
        gy = NEAR1.y(PED1_X)
        top = pedestal(cv, PED1_X, gy + 6, 0.78, P["L"][4], mix(P["L"][4], "#8C9FA1", 0.25))
        btn_top = button(cv, PED1_X, top + 4, 0.78, t)
        draw_person(cv, 482, NEAR1.y(482) + 8, 0.222, friend_colors(0), t=t, wind=wind * 0.7, lean=7,
                    arm=reach_arm((482, NEAR1.y(482) + 8), 0.222, 1, (PED1_X - 30, btn_top - 46), 0.92), hand="point", finger_dir=(1, 0.35))
        hx, hy, hs = HERO3_X, NEAR1.y(HERO3_X) + 8, 0.24
        glow(cv, hx - 10, hy - 200, 260, "#F2A55C", 0.22)
        t_sen = wtt(3, "sen")
        turn = ease_io((t - (SC_START[3] + 0.55)) / 0.35)
        wave_p = ease_out((t - (SC_START[3] + 0.7)) / 0.35)
        osc = math.sin((t - SC_START[3]) * 9.0) * 22 * wave_p
        a1 = lerp(-4, 150, wave_p); a2 = lerp(12, 185 + osc, wave_p)
        r = draw_person(cv, hx, hy, hs, HERO, t=t, wind=wind, turn=turn, arm=("fk", a1, a2), hand="fist")
        tag(cv, uz("SEN"), r["top"][0], r["top"][1] - 16, 30, 1.0, pop_scale(t - t_sen, 0.3))

# ---------------------------------------------------------------- 4/5/6. two-shot, the press, the dissolve
H4 = Hill(1318, [(540, 560, 60), (-200, 300, 20)], 17, 4)
HX4, FX4, PX4, S4 = 255, 650, 872, 0.36
HH4 = (HX4 + 140, -262)   # hero hand: x, height above ground
FH4 = (FX4 - 120, -250)   # friend's far hand

def two_shot_world(cv, t, cam, P, sun_xy=(560, 980), sun_r=300, star_a=None):
    wind = wind_at(t)
    steppe_layers(cv, cam, P, t, wind=wind, sun_xy=sun_xy, sun_r=sun_r, star_a=star_a)
    near_ground(cv, cam, P, t, H4, wind=wind)
    return wind

def friend4(cv, t, P, wind, btn_top, press=0.0, backlit=0.0, chain_hand=True, hover=1.0):
    fx, fy = FX4, H4.y(FX4) + 10
    hover_y = btn_top - 70 + 60 * press
    tgt = (PX4 - 40, hover_y)
    rr = to_ref(FH4[0], H4.y(FX4) + FH4[1], fx, fy, S4)
    far = ("hand", rr, -1.0) if chain_hand else None
    return draw_person(cv, fx, fy, S4, friend_colors(P["n"], backlit), t=t, wind=wind * 0.7, lean=4,
                       arm=reach_arm((fx, fy), S4, 1, tgt, hover), hand="point", finger_dir=(0.45, 1), finger_len=0.9,
                       arm_far=far)

def hero4_arm(hx, hy):
    return ("hand", to_ref(HH4[0], H4.y(HX4) + HH4[1], hx, hy, S4), 1.0)

def scene4(cv, t, lt, dur):
    P = pal(0)
    cam = Cam(560, 995, 1.0 + 0.06 * lt / dur)
    wind = two_shot_world(cv, t, cam, P)
    with at_layer(cv, cam, 1.0):
        gy = H4.y(PX4)
        top = pedestal(cv, PX4, gy + 8, 1.0, P["L"][4], mix(P["L"][4], "#8C9FA1", 0.25))
        btn_top = button(cv, PX4, top + 4, 1.0, t)
        hx, hy = HX4, H4.y(HX4) + 10
        rh = draw_person(cv, hx, hy, S4, HERO, t=t, wind=wind, arm=hero4_arm(hx, hy), hand="fist", turn=0.0)
        # chain (behind the friend: he holds it in his far hand)
        fx, fy = FX4, H4.y(FX4) + 10
        fh = (FH4[0], H4.y(FX4) + FH4[1] + 10)
        sway = 6 * math.sin(t * 2.0)
        pts = sag(rh["hand"], fh, 60 + sway)
        chain(cv, pts, 1.0)
        mid = pts[len(pts) // 2]
        tag(cv, uz("DO'STLIK"), mid[0], mid[1] + 92, 26, 1.0, 1.0, pointer=False)
        line(cv, [mid, (mid[0], mid[1] + 34)], "#C7A548", 3)
        friend4(cv, t, P, wind, btn_top, hover=ease_out(0.6 + lt / 0.8))

class Dissolver:
    """hero -> flat square pixels drifting on the wind, feet first"""
    CELL = 9
    def __init__(self): self.cache = None
    def draw(self, cv, draw_fn, t, t0, t1, cam_xf):
        surf = skia.Surface(W, H); c2 = surf.getCanvas(); c2.clear(skia.ColorTRANSPARENT)
        c2.setMatrix(cam_xf)
        bbox = draw_fn(c2)
        img = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
        x0, y0, x1, y1 = [int(v) for v in bbox]
        x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(W, x1), min(H, y1)
        C = self.CELL
        gh, gw = (y1 - y0) // C + 1, (x1 - x0) // C + 1
        rng = np.random.default_rng(3)
        noise = rng.random((gh, gw))
        ys = y0 + np.arange(gh) * C; frac = (y1 - ys) / max(1, (y1 - y0))      # 0 at feet .. 1 at head
        td = t0 + (t1 - t0) * (0.85 * frac[:, None] + 0.15 * noise)
        gone = t >= td
        mask = np.ones((H, W), np.float32)
        out = img.copy()
        for gy in range(gh):
            for gx in range(gw):
                if gone[gy, gx]:
                    out[y0 + gy * C:y0 + gy * C + C, x0 + gx * C:x0 + gx * C + C, 3] = 0
        out[:, :, :3] = (out[:, :, :3].astype(np.float32) * (out[:, :, 3:4] > 0)).astype(np.uint8)
        cv.save(); cv.resetMatrix()
        cv.drawImage(skia.Image.fromarray(np.ascontiguousarray(out), colorType=skia.kRGBA_8888_ColorType), 0, 0)
        # particles
        for gy in range(gh):
            for gx in range(gw):
                if not gone[gy, gx]: continue
                px, py = x0 + gx * C + C // 2, y0 + gy * C + C // 2
                if py >= H or px >= W: continue
                a = img[py, px, 3]
                if a < 160: continue
                dt = t - td[gy, gx]
                life = 1.4
                if dt > life: continue
                n = noise[gy, gx]
                xx = px + (120 + 120 * n) * dt + 90 * dt * dt
                yy = py - (40 + 90 * n) * dt - 30 * dt * dt + 8 * math.sin(dt * 6 + n * 9)
                sz = C * (1.0 - 0.6 * dt / life)
                cc = img[py, px]
                p = skia.Paint(AntiAlias=True, Color=skia.ColorSetARGB(int(255 * (1 - dt / life) ** 1.2), int(cc[0]), int(cc[1]), int(cc[2])))
                cv.save(); cv.translate(xx, yy); cv.rotate(dt * 90 * (n - 0.5))
                cv.drawRect(skia.Rect.MakeXYWH(-sz / 2, -sz / 2, sz, sz), p); cv.restore()
        cv.restore()

DISS = Dissolver()

def scene5(cv, t, lt, dur):
    t_press = SC_START[5] + 0.16
    t_snap = t_press + 0.16
    d0, d1 = t_press + 0.3, SC_START[5] + dur - 0.25
    warm = 0.75 * ease_io((t - t_press - 0.1) / 1.6)
    P = pal(0, warm)
    shake = (0.0, 0.0)
    if 0 <= t - t_press < 0.25:
        k = (t - t_press) / 0.25; amp = 9 * (1 - k)
        shake = (amp * math.sin(k * 40), amp * math.cos(k * 33))
    cam = Cam(560, 995, 1.06 + 0.03 * lt / dur, 0.0, shake)
    wind = two_shot_world(cv, t, cam, P)
    press = ease_out((t - t_press + 0.12) / 0.12) * (1 - ease_io((t - t_press - 0.35) / 0.3))
    with at_layer(cv, cam, 1.0):
        gy = H4.y(PX4)
        top = pedestal(cv, PX4, gy + 8, 1.0, P["L"][4], mix(P["L"][4], "#8C9FA1", 0.25))
        flash = clamp01(1 - abs(t - t_press - 0.05) / 0.2)
        if flash > 0: glow(cv, PX4, top - 30, 380, "#E58A3C", 0.8 * flash)
        btn_top = button(cv, PX4, top + 4, 1.0, t, press=press)
        hx, hy = HX4, H4.y(HX4) + 10
        # chain: intact until the snap, then two halves fall
        fx, fy = FX4, H4.y(FX4) + 10
        fh = (FH4[0], H4.y(FX4) + FH4[1] + 10)
        hh = (HH4[0], H4.y(HX4) + HH4[1] + 10)
    cam_m = None
    def draw_hero(c2):
        with at_layer(c2, cam, 1.0):
            r = draw_person(c2, hx, hy, S4, HERO, t=t, wind=wind, arm=hero4_arm(hx, hy), hand="fist")
            if t < t_snap:
                chain(c2, sag(r["hand"], fh, 60 + 6 * math.sin(t * 2.0)), 1.0)
        # bbox in screen space
        z = cam.z
        sx0 = 540 + (hx - 200 - (540 + (cam.cx - 540))) * z + shake[0]
        sx1 = 540 + (hx + 260 - (540 + (cam.cx - 540))) * z + shake[0]
        sy0 = 960 + (hy - 560 - (960 + (cam.cy - 960))) * z + shake[1]
        sy1 = 960 + (hy + 8 - (960 + (cam.cy - 960))) * z + shake[1]
        return (sx0, sy0, sx1, sy1)
    if t < d0:
        draw_hero(cv)
    else:
        DISS.draw(cv, draw_hero, t, d0, d1, skia.Matrix())
    with at_layer(cv, cam, 1.0):
        if t >= t_snap:
            k = t - t_snap
            mid = ((hh[0] + fh[0]) / 2, (hh[1] + fh[1]) / 2 + 60)
            # friend's half swings down from his far hand
            ang = math.radians(100 + 25 * math.exp(-k * 2.5) * math.cos(k * 7))
            Lc = 120
            end = (fh[0] + Lc * math.cos(ang), fh[1] + Lc * math.sin(ang))
            chain(cv, sag(fh, end, 10, 12), 1.0)
            # hero's half falls (and is gone with him)
            if k < 0.9:
                fall = 0.5 * 1400 * k * k
                p0 = (hh[0], hh[1] + fall * 0.4); p1 = (mid[0] - 10, mid[1] + fall)
                chain(cv, sag(p0, p1, 20, 12), 1.0, a=clamp01(1 - k / 0.9))
            if k < 0.35:
                for j in range(8):
                    ang2 = j * 0.8 + 0.3
                    rr2 = 20 + 160 * k
                    circle(cv, mid[0] + rr2 * math.cos(ang2), mid[1] - 40 + rr2 * math.sin(ang2), 5 * (1 - k / 0.35), "#C7A548")
        friend4(cv, t, P, wind, btn_top, press=press, hover=1.0)

def scene6(cv, t, lt, dur):
    P = pal(0, 0.85)
    zoom = 1.0 + 0.02 * (1 - ease_out(lt / 0.25))
    cam = Cam(600, 930, 0.9 * zoom)
    wind = wind_at(t)
    steppe_layers(cv, cam, P, t, wind=wind, sun_xy=(640, 1000), sun_r=330)
    near_ground(cv, cam, P, t, H4, wind=wind)
    with at_layer(cv, cam, 1.0):
        gy = H4.y(PX4)
        top = pedestal(cv, PX4, gy + 8, 1.0, P["L"][4], mix(P["L"][4], "#8C9FA1", 0.25))
        btn_top = button(cv, PX4, top + 4, 1.0, t, glow_a=0.6)
        fx, fy = FX4, H4.y(FX4) + 10
        r = draw_person(cv, fx, fy, S4, friend_colors(0, 0.85), t=t, wind=wind * 0.7, lean=2,
                        arm=reach_arm((fx, fy), S4, 1, (PX4 - 40, btn_top - 60), 0.5), hand="fist")
        # broken chain pieces fall to the ground
        rng = np.random.default_rng(4)
        for k in range(7):
            x = FH4[0] - 60 + k * 30 + rng.uniform(-10, 10)
            yg = H4.y(x) - 4
            y_start = H4.y(FX4) + FH4[1] + rng.uniform(-20, 60)
            tt = lt - rng.uniform(0, 0.25)
            y = min(yg, y_start + 0.5 * 1500 * max(0, tt) ** 2)
            ang = rng.uniform(-40, 40) + (0 if y < yg else 80 * (k % 2))
            pts = [(x - 26, y), (x + 26, y)]
            with xf(cv, x, y, 1, ang): chain(cv, [(-24, 0), (24, 0)], 1.0)
    # stamp
    k = ease_out(lt / 0.16)
    sc = lerp(1.2, 1.0, k)
    a = clamp01(lt / 0.06)
    with xf(cv, 540, 690, sc, -8):
        with layer_alpha(cv, a):
            w = text_w("BUTUNLAY!", 112) + 80
            rrect_stroke(cv, -w / 2, -92, w, 184, 26, "#C8553D", 12)
            text(cv, "BUTUNLAY!", 0, 0, 112, "#C8553D")

# ---------------------------------------------------------------- 7. mahalla street, voice message
def mahalla_layers(cv, cam, P, t, lamp_on=1.0):
    L = P["L"]
    with at_layer(cv, cam, 0.0):
        sky(cv, P, horizon=1200)
    with at_layer(cv, cam, 0.06): sun(cv, 300, 990, 150, P, t)
    with at_layer(cv, cam, 0.2):
        dome_skyline(cv, 660, 1060, 0.62, L[0])
        for k, x in enumerate([-200, 60, 240, 900, 1100]):
            house(cv, x, 1075, 170 + 30 * (k % 2), 120 + 20 * k % 50, L[0])
        hill(cv, Hill(1070, [], 1, 2), L[0])
    with at_layer(cv, cam, 0.4):
        for k, x in enumerate(range(-300, 1500, 150)):
            poplar(cv, x + 40 * (k % 3), 1110, 300 + 60 * ((k * 7) % 3), 60, L[1], t, 1.0, k)
        for k, x in enumerate([-120, 200, 520, 880, 1180]):
            house(cv, x, 1135, 230, 150 + 25 * (k % 2), L[1], windows=[(40, 50, 40, 46), (140, 50, 40, 46)])
        hill(cv, Hill(1130, [], 2, 1), L[1])
    with at_layer(cv, cam, 0.65):
        wall(cv, -600, 1700, 1060, 1260, L[2], 3)
        for x in (-80, 520, 1120):
            gate(cv, x, 1230, 170, 200, mix(L[2], L[3], 0.45), mix(L[2], L[3], 0.85))
        round_tree(cv, 250, 1080, 70, L[2]); round_tree(cv, 850, 1080, 60, L[2])
    with at_layer(cv, cam, 0.85):
        street_lamp(cv, 905, 1330, 420, L[3], lamp_on, t)
        wall(cv, -600, 220, 1150, 1400, L[3], 5)
    with at_layer(cv, cam, 1.0):
        cv.drawRect(skia.Rect.MakeLTRB(-1500, 1338, 2600, 3600), paint(L[4]))

def scene7(cv, t, lt, dur):
    P = pal(0)
    cam = Cam(lerp(600, 540, lt / dur), 1010, 1.0)
    on = clamp01(lt / 0.45)
    flick = 1.0 if lt > 0.6 else (0.35 + 0.65 * (0.5 + 0.5 * math.sin(lt * 70)))
    mahalla_layers(cv, cam, P, t, on * flick)
    with at_layer(cv, cam, 1.0):
        sx, sb = 250, 1345
        seat = suri(cv, sx, sb, 600, 1.35, P["L"][4])
        hs = 0.5
        hx = 520
        r = draw_person(cv, hx, seat + 6, hs, HERO, t=t, sit=True, tilt=10 + 2 * math.sin(t * 1.5),
                        arm=("ik", (700, 900), 1.0), phone=0.8 + 0.2 * math.sin(t * 3))
    # floating voice-message plate
    t_strike = wtt(7, "yo")
    a = clamp01(lt / 0.2) * (1 - ease_in((t - t_strike - 0.45) / 0.35))
    sc = pop_scale(lt, 0.3) * (1 + 0.01 * math.sin(t * 3))
    y0 = 520 + 8 * math.sin(t * 2.0)
    if a > 0.01:
        with xf(cv, 540, y0, sc):
            with layer_alpha(cv, a):
                plate(cv, -360, -95, 720, 190, 40, 0.85)
                avatar(cv, -270, 0, 56, "D")
                text(cv, uz("DO'STIM"), -190, -40, 38, INK, 1, "left")
                poly(cv, [(-180, 12), (-180, 52), (-146, 32)], INK)
                waveform(cv, -120, 32, 380, 48, INK, t, 0.85)
                strike(cv, -380, 60, 380, -60, ease_out((t - t_strike) / 0.22), 14)

# ---------------------------------------------------------------- 8. bus stop, reels
def scene8(cv, t, lt, dur):
    P = pal(0)
    L = P["L"]
    cam = Cam(540, lerp(985, 975, lt / dur), 1.0)
    with at_layer(cv, cam, 0.0): sky(cv, P, horizon=1220)
    with at_layer(cv, cam, 0.06): sun(cv, 820, 1060, 170, P, t)
    with at_layer(cv, cam, 0.2): hill(cv, Hill(1150, [(300, 400, 40), (1100, 300, 30)], 8, 6), L[0])
    with at_layer(cv, cam, 0.35):
        # bus passes on the far road without stopping
        bx = lerp(-760, 1300, (t - SC_START[8] + 0.2) / 1.9)
        bus(cv, bx, 1178, 0.62, L[1], mix(L[1], "#F4EDDF", 0.35))
        cv.drawRect(skia.Rect.MakeLTRB(-1000, 1176, 2200, 1200), paint(L[1]))
    with at_layer(cv, cam, 0.55):
        for k in range(13):
            x = -260 + k * 115
            poplar(cv, x, 1210, 560 + 70 * ((k * 5) % 3), 92, L[2], t, 1.0, k)
        cv.drawRect(skia.Rect.MakeLTRB(-1000, 1200, 2200, 1240), paint(L[2]))
    with at_layer(cv, cam, 0.8):
        cv.drawRect(skia.Rect.MakeLTRB(-1000, 1236, 2200, 1290), paint(L[3]))
    with at_layer(cv, cam, 1.0):
        cv.drawRect(skia.Rect.MakeLTRB(-1500, 1290, 2600, 3600), paint(L[4]))
        bus_shelter(cv, 290, 1300, 560, 640, L[4], mix(L[4], L[3], 0.5))
        r = draw_person(cv, 560, 1302, 0.43, HERO, t=t, tilt=14 + 2 * math.sin(t * 1.3), wind=0.15 * math.sin(t),
                        arm=("ik", (690, 820), 1.0), phone=0.9 + 0.1 * math.sin(t * 4))
    t_strike = wtt(8, "yo")
    a = clamp01(lt / 0.2) * (1 - ease_in((t - t_strike - 0.4) / 0.35))
    sc = pop_scale(lt, 0.3)
    y0 = 520 + 8 * math.sin(t * 2.0)
    if a > 0.01:
        with xf(cv, 540, y0, sc):
            with layer_alpha(cv, a):
                plate(cv, -360, -110, 720, 220, 40, 0.85)
                rrect(cv, -330, -80, 150, 160, 22, "#8C9FA1")
                poly(cv, [(-275, -32), (-275, 32), (-222, 0)], "#F4EDDF")
                text(cv, uz("DO'STIM"), -150, -45, 40, INK, 1, "left")
                text(cv, "bu sen :D", -150, 25, 40, "#56696D", 1, "left", "b")
                strike(cv, -380, 80, 380, -80, ease_out((t - t_strike) / 0.22), 14)

# ---------------------------------------------------------------- 9/10. midnight courtyard
def courtyard(cv, cam, P, t, phone_glow=0.0, hero_turn=0.0):
    L = P["L"]
    with at_layer(cv, cam, 0.0):
        sky(cv, P, horizon=1000, top=-1500)
        stars(cv, t, P["n"], -200, 1300, -400, 820)
    with at_layer(cv, cam, 0.05): moon(cv, 790, 470, 120, P, t, P["n"])
    if P["n"] < 0.999:
        with at_layer(cv, cam, 0.05): sun(cv, 790, 980, 160, P, t, 1 - P["n"])
    with at_layer(cv, cam, 0.25):
        for k, x in enumerate([-250, 0, 280, 560, 860, 1120]):
            house(cv, x, 960, 260, 150 + 40 * (k % 3), L[0])
        poplar(cv, 470, 900, 380, 70, L[0], t, 0.4, 2); poplar(cv, 1010, 900, 330, 60, L[0], t, 0.4, 5)
        cv.drawRect(skia.Rect.MakeLTRB(-1500, 955, 2500, 1100), paint(L[0]))
    with at_layer(cv, cam, 0.5):
        for k, x in enumerate([-300, 40, 420, 760]):
            house(cv, x, 1060, 330, 170, L[1], windows=[(60, 50, 50, 56), (200, 50, 50, 56)],
                  win_a=(1.0 if k == 2 else 0.0) * P["n"], win_c="#E7A05C")
        cv.drawRect(skia.Rect.MakeLTRB(-1500, 1055, 2500, 1200), paint(L[1]))
    with at_layer(cv, cam, 0.8):
        round_tree(cv, 900, 1180, 110, L[2]); wall(cv, -500, 1700, 1120, 1300, L[2], 4)
    with at_layer(cv, cam, 1.0):
        cv.drawRect(skia.Rect.MakeLTRB(-1500, 1230, 2600, 3600), paint(L[3]))
        seat = suri(cv, 170, 1560, 760, 1.25, mix(L[4], L[2], 0.5), top_view=1.0, mat=mix(L[2], "#4A5A6E", 0.55 * P["n"] + 0.2), rail=False)
        # pillow
        spoly(cv, [(250, 1310), (330, 1290), (350, 1335), (262, 1352)], mix(L[4], "#4A5A6E", 0.5))
        # hero lying on his back (head left), turning onto his side
        rot = -90 - 10 * hero_turn
        with xf(cv, 760 + 10 * hero_turn, 1330 - 12 * hero_turn, 1, rot):
            arm = ("fk", lerp(18, 4, hero_turn), lerp(168, 14, hero_turn))
            draw_person(cv, 0, 0, 0.36, HERO, t=t, eye="open" if hero_turn < 0.5 else "closed", turn=0.0,
                        arm=arm, tilt=-8 * hero_turn)
        # phone lying beside him
        px, py = 300, 1398
        if phone_glow > 0: glow(cv, px, py, 150, "#F4EDDF", 0.35 * phone_glow)
        rrect(cv, px - 30, py - 12, 60, 24, 6, "#1F292C")
        if phone_glow > 0: rrect(cv, px - 26, py - 9, 52, 18, 4, "#AFC2C4", 0.6 * phone_glow)
    return (520, 1388)

def scene9(cv, t, lt, dur):
    n = ease_io(lt / 0.5)
    P = pal(n)
    cam = Cam(560, lerp(1080, 1110, lt / dur), lerp(1.0, 1.08, ease_io(lt / dur)))
    courtyard(cv, cam, P, t, phone_glow=0.45 + 0.15 * math.sin(t * 4))
    sc = pop_scale(lt - 0.15, 0.3)
    if lt > 0.15:
        with xf(cv, 540, 600, sc):
            plate(cv, -150, -62, 300, 124, 40, 0.85)
            text(cv, "00:00", 0, 0, 66, INK)

def scene10(cv, t, lt, dur):
    P = pal(1)
    t_yoq = wtt(10, "yo")
    turn = ease_io((t - t_yoq - 0.15) / 0.4)
    glow_a = 0.6 * (1 - ease_in((t - t_yoq - 0.05) / 0.2))
    drift = 6 * lt / dur
    cam = Cam(450 + drift, 1335, 1.85)
    ph = courtyard(cv, cam, P, t, phone_glow=glow_a + 0.25 * clamp01(lt / 0.2) * (1 - clamp01((t - t_yoq) / 0.2)), hero_turn=turn)
    # message bubble above the phone (screen space)
    bx, by = 400, 860
    a = clamp01(lt / 0.12) * (1 - ease_in((t - t_yoq - 0.4) / 0.3))
    if a > 0.01:
        bubble(cv, bx, by, 520, 140, a, pop_scale(lt, 0.3), tail=-1)
        with xf(cv, bx, by, pop_scale(lt, 0.3)):
            with layer_alpha(cv, a):
                text(cv, "chiqasanmi?", 0, 0, 62, INK)
                strike(cv, -250, 40, 250, -40, ease_out((t - t_yoq) / 0.2), 13)

# ---------------------------------------------------------------- 11. the wedding
def scene11(cv, t, lt, dur):
    P = pal(1)
    L = P["L"]
    u = ease_io(lt / dur)
    CHX = 600                      # the empty chair
    cam = Cam(lerp(560, CHX - 30, u), lerp(980, 1090, u), lerp(1.0, 1.85, u))
    with at_layer(cv, cam, 0.0):
        sky(cv, P, horizon=1000, top=-1500); stars(cv, t, 0.8, -200, 1300, -300, 700)
    with at_layer(cv, cam, 0.05): moon(cv, 860, 330, 80, P, t, 1.0)
    with at_layer(cv, cam, 0.3):
        for k, x in enumerate([-300, 60, 400, 760, 1080]):
            house(cv, x, 1000, 300, 230 + 30 * (k % 2), L[1], windows=[(60, 60, 46, 56), (190, 60, 46, 56)], win_a=0.7 if k in (1, 3) else 0, win_c="#E7A05C")
        round_tree(cv, 330, 880, 100, L[1]); round_tree(cv, 990, 900, 90, L[1])
        cv.drawRect(skia.Rect.MakeLTRB(-1500, 995, 2600, 1300), paint(L[1]))
    with at_layer(cv, cam, 0.7):
        for x in (40, 1040):
            line(cv, [(x, 1120), (x, 470)], L[3], 10, cap="butt")
        string_lights(cv, [(40, 480), (540, 610), (1040, 480)], t, 8, 70)
        string_lights(cv, [(40, 610), (540, 480), (1040, 610)], t + 1.3, 8, 60)
    with at_layer(cv, cam, 0.9):
        # guests seated along the far side of the long low table
        for k, x in enumerate(range(380, 1000, 92)):
            sway = 2.0 * math.sin(t * 1.6 + k * 1.1)
            draw_guest(cv, x, 1175, 0.46, L[4] if k % 2 else mix(L[4], L[3], 0.35), t, "doppi" if k % 3 else "scarf", sway)
        # doira player at the far end
        dx = 1030; hit = abs(math.sin(t * 5.5))
        draw_guest(cv, dx, 1175, 0.48, L[4], t, "doppi", 3 * math.sin(t * 3.2))
        cv.drawCircle(dx - 62, 1000 - 10 * hit, 40, paint(L[4], 1, stroke=9))
        circle(cv, dx - 62, 1000 - 10 * hit, 35, mix(L[4], "#36455A", 0.5))
        line(cv, [(dx - 20, 1060), (dx - 50, 1020 - 10 * hit)], L[4], 18)
    with at_layer(cv, cam, 1.0):
        cv.drawRect(skia.Rect.MakeLTRB(-1500, 1300, 2600, 3600), paint(L[3]))
        # dastarxon: long low table (top + cloth), dishes as small silhouettes
        rrect(cv, 330, 1168, 760, 26, 8, mix(L[3], "#4A5A6E", 0.45))
        cv.drawRect(skia.Rect.MakeLTRB(340, 1190, 1080, 1260), paint(L[4]))
        for k, x in enumerate(range(380, 1060, 62)):
            if k % 3 == 0: ellipse(cv, x, 1164, 24, 12, L[4])
            elif k % 3 == 1: circle(cv, x, 1158, 11, L[4])
            else: poly(cv, [(x - 12, 1168), (x, 1142), (x + 12, 1168)], L[4])
        for lx in (350, 1060): rrect(cv, lx, 1190, 16, 112, 3, L[4])
        # the empty chair right next to the hero, with its tag (warm rim from the string lights)
        glow(cv, CHX, 1170, 230, "#E7A05C", 0.22)
        with xf(cv, -3, -3): chair(cv, CHX + 50, 1302, 1.0, mix("#E7A05C", L[4], 0.55))
        chair(cv, CHX + 50, 1302, 1.0, "#3A4A5C")
        sw = 3 * math.sin(t * 1.7)
        with xf(cv, CHX - 34, 1068, 1, sw):
            line(cv, [(0, -20), (0, 14)], CREAM, 2.5, 0.9)
            tag(cv, uz("DO'STIM"), 0, 62, 26, 1.0, 1.0, pointer=False)
        hx = 300
        look = ease_io((lt - 1.0) / 0.6)
        draw_person(cv, hx, 1304, 0.40, HERO, t=t, tilt=lerp(0, 10, look), wind=0.12 * math.sin(t * 1.1),
                    arm=("fk", lerp(-4, 8, look), lerp(12, 30, look)))

# ---------------------------------------------------------------- 12. freeze over the button
def scene12(cv, t, lt, dur):
    P = pal(0)
    L = P["L"]
    cam = Cam(540, 960, 1.0)
    with at_layer(cv, cam, 0.0): sky(cv, P, horizon=1300)
    with at_layer(cv, cam, 0.05): sun(cv, 820, 1060, 330, P, t)
    with at_layer(cv, cam, 0.2): hill(cv, Hill(1180, [(200, 500, 90), (1100, 500, 60)], 2, 10), L[1])
    with at_layer(cv, cam, 0.5): hill(cv, Hill(1300, [(700, 500, 70)], 3, 6), L[2])
    with at_layer(cv, cam, 0.8): hill(cv, Hill(1460, [(300, 400, 70)], 4, 6), L[3])
    with at_layer(cv, cam, 1.0):
        s = 2.7
        cx, cy = 600, 1115
        rrect(cv, cx - 210, cy, 420, 900, 20, L[4])
        rrect(cv, cx - 236, cy - 30, 472, 56, 16, mix(L[4], "#8C9FA1", 0.25))
        top = button(cv, cx, cy - 26, s, t)
        # the friend's frozen hand, finger a hair above the button
        C = friend_colors(0)
        tip = (cx - 20, top - 42 * s / 2.7 - 6)
        with xf(cv, tip[0], tip[1], 1.0):
            # arm comes in from the upper left, finger points down-right onto the button
            fd = (0.42, 1.0); fl = math.hypot(*fd); ux, uy = fd[0] / fl, fd[1] / fl
            hand = (-ux * (26 + 50 + 4), -uy * (26 + 50 + 4))
            wr = (hand[0] - 0.55 * HAND_OFF, hand[1] - 0.84 * HAND_OFF)
            el = (wr[0] - 150, wr[1] - 150)
            draw_arm(cv, C, el, wr, "point", finger_dir=fd, finger_len=1.0, shoulder=(el[0] - 260, el[1] - 210))
    # big '?'
    bob = 10 * math.sin(t * 3.0)
    with xf(cv, 760, 560 + bob, pop_scale(lt, 0.35)):
        text(cv, "?", 0, 0, 300, "#E58A3C", 1, tf="xb")
    # comment prompt plate under the button
    s2 = pop_scale(lt - 0.2, 0.3)
    if lt > 0.2:
        with xf(cv, 540, 1288, s2):
            txt = uz("IZOHDA: 1 — BOSADI · 2 — BOSMAYDI")
            w = text_w(txt, 40) + 70
            plate(cv, -w / 2, -48, w, 96, 30, 0.88)
            text(cv, txt, 0, 0, 40, INK)

# ---------------------------------------------------------------- 13. shh
def scene13(cv, t, lt, dur):
    P = pal(0)
    L = P["L"]
    cam = Cam(540, 960, 1.0 + 0.05 * lt / dur)
    with at_layer(cv, cam, 0.0): sky(cv, P, horizon=1500)
    with at_layer(cv, cam, 0.1): sun(cv, 640, 720, 330, P, t)
    with at_layer(cv, cam, 0.3): hill(cv, Hill(1350, [(200, 400, 80), (1000, 400, 60)], 5, 8), L[0])
    with at_layer(cv, cam, 0.5): hill(cv, Hill(1480, [(800, 400, 80)], 6, 6), L[2])
    with at_layer(cv, cam, 0.9):
        hs = 1.22
        hx, hy = 520, 1290 + (1700 - 888) * hs
        turn = ease_io(lt / 0.3)
        up = ease_out((lt - 0.12) / 0.32)
        tgt_ref = (606, 492)
        rest_h = (562, 1134)
        arm = ("hand", (lerp(rest_h[0], tgt_ref[0], up), lerp(rest_h[1], tgt_ref[1], up)), 1.0, lerp(1.0, 0.5, up))
        draw_person(cv, hx, hy, hs, HERO, t=t, turn=turn, arm=arm, hand="shh" if up > 0.5 else "fist",
                    finger_dir=(0.05, -1), finger_len=clamp01((up - 0.5) / 0.4), wind=0.2 * math.sin(t))

# ---------------------------------------------------------------- 14. paper airplane across the valley
NEAR14 = Hill(1290, [(300, 380, 120), (1250, 520, -330)], 9, 4)
FAR14 = Hill(1130, [(1480, 330, 120), (900, 200, -40)], 10, 4)
def scene14(cv, t, lt, dur):
    P = pal(0)
    L = P["L"]
    t_yub = wtt(14, "yubor")
    t_land = t_yub + 1.15
    fly = clamp01((t - t_yub - 0.05) / (t_land - t_yub - 0.05))
    pan = ease_io((t - t_yub) / (t_land - t_yub + 0.3))
    cam = Cam(lerp(560, 1560, pan), 1010, 1.0)
    wind = wind_at(t)
    with at_layer(cv, cam, 0.0): sky(cv, P, horizon=1150)
    with at_layer(cv, cam, 0.06): sun(cv, 900, 1000, 230, P, t)
    with at_layer(cv, cam, 0.15): hill(cv, Hill(1030, [(500, 500, 80), (1400, 400, 70)], 1, 12), L[0])
    with at_layer(cv, cam, 0.3): hill(cv, Hill(1110, [(900, 400, 60), (1900, 300, 50)], 2, 10), L[1])
    with at_layer(cv, cam, 0.7):
        hill(cv, FAR14, L[3]); grass(cv, FAR14, L[3], t, 900, 2300, 22, 10, 26, wind, 5)
        fx, fy = 1480, FAR14.y(1480) + 6
        rf = draw_person(cv, fx, fy, 0.2, friend_colors(0, 0.9), facing=-1, t=t, wind=wind * 0.5,
                         arm=("fk", lerp(-4, 30, ease_out((t - t_land) / 0.3)) if t > t_land else -4, lerp(12, 60, ease_out((t - t_land) / 0.3)) if t > t_land else 12))
        fhand = rf["hand"]
    with at_layer(cv, cam, 1.0):
        hill(cv, NEAR14, L[4], -800, 2900); grass(cv, NEAR14, L[4], t, -800, 2900, 18, 14, 36, wind, 6)
        hx, hy, hs = 330, NEAR14.y(330) + 8, 0.25
        # fold (sheet in front of chest), wind-up, throw on "yubor"
        if t < t_yub - 0.18:
            arm = ("hand", (700, 830 + 10 * math.sin(t * 6)), 1.0)
        elif t < t_yub + 0.02:
            k = ease_io((t - (t_yub - 0.18)) / 0.2)
            arm = ("fk", lerp(60, 160, k), lerp(110, 200, k))
        else:
            k = ease_out((t - t_yub - 0.02) / 0.22)
            arm = ("fk", lerp(160, 75, k), lerp(200, 95, k))
        rh = draw_person(cv, hx, hy, hs, HERO, t=t, wind=wind, arm=arm, hand="fist", lean=-3 if t < t_yub else 4 * (1 - ease_out((t - t_yub) / 0.6)))
        QA["gesture"] = "fold" if t < t_yub - 0.18 else ("throw" if t < t_yub + 0.45 else "after")
        QA["icon"] = "plane" if t < t_land + 0.25 else "typing"
    # airplane
    with at_layer(cv, cam, 0.85 if fly > 0 else 1.0):
        if t < t_yub + 0.02:
            fold = clamp01((t - SC_START[14]) / 0.38)
            px, py = rh["hand"]
            if fly <= 0:
                # convert hand position (screen) into this layer: hand is in layer 1.0, plane in 1.0 here
                pass
            paper_plane(cv, px + 18, py - 26, 0.62, -8, fold)
    if t >= t_yub + 0.02:
        # flight path in screen space between hero hand and friend hand (both converted)
        def scr(layer_p, x, y):
            z = 1 + (cam.z - 1) * layer_p
            return (540 + (x - (540 + (cam.cx - 540) * layer_p)) * z, 960 + (y - (960 + (cam.cy - 960) * layer_p)) * z)
        hand_w = (hx + 120, hy - 300)
        a_pt = scr(1.0, hand_w[0], hand_w[1])
        b_pt = scr(0.7, fhand[0] - 0, fhand[1] - 30)
        u = ease_io(fly)
        x = lerp(a_pt[0], b_pt[0], u); y = lerp(a_pt[1], b_pt[1], u) - 260 * math.sin(math.pi * u)
        du = 0.01; x2 = lerp(a_pt[0], b_pt[0], min(1, u + du)); y2 = lerp(a_pt[1], b_pt[1], min(1, u + du)) - 260 * math.sin(math.pi * min(1, u + du))
        rot = math.degrees(math.atan2(y2 - y, x2 - x)) if fly < 0.999 else 8
        sc = lerp(0.6, 0.42, u)
        if t < t_land + 0.25:
            paper_plane(cv, x, y, sc, rot, 1.0, a=1 - clamp01((t - t_land) / 0.25))
        # trail
        for j in range(1, 7):
            uu = max(0, u - j * 0.035)
            xx = lerp(a_pt[0], b_pt[0], uu); yy = lerp(a_pt[1], b_pt[1], uu) - 260 * math.sin(math.pi * uu)
            if fly < 1: circle(cv, xx, yy, 4, "#F4EDDF", 0.5 * (1 - j / 7))
        if t >= t_land:
            sx, sy = scr(0.7, 1480, FAR14.y(1480) - 300)
            tag(cv, "YUBORILDI!", 540, 620, 44, 1.0, pop_scale(t - t_land, 0.3), pointer=False)
            if t >= t_land + 0.35:
                bt = t - t_land - 0.35
                bubble(cv, sx, sy - 40, 150, 76, clamp01(bt / 0.15), pop_scale(bt, 0.25), tail=1)
                with xf(cv, sx, sy - 40, pop_scale(bt, 0.25)):
                    typing_dots(cv, 0, 4, t, clamp01(bt / 0.15), 0.9)

# ---------------------------------------------------------------- 15. trust gauge, hug, repost
H15 = Hill(1300, [(330, 500, 60)], 12, 4)
GX, GY, GR = 650, 1150, 360
def gauge(cv, cx, cy, r, val, a=1.0):
    with layer_alpha(cv, a):
        p = skia.Path(); p.addArc(skia.Rect.MakeLTRB(cx - r, cy - r, cx + r, cy + r), 180, 180); p.close()
        cv.drawPath(p, paint(CREAM, 0.9))
        segs = 5
        for k in range(segs):
            a0 = 180 + k * 180 / segs + 1.5
            pp = skia.Path(); rr = r * 0.80
            pp.addArc(skia.Rect.MakeLTRB(cx - rr, cy - rr, cx + rr, cy + rr), a0, 180 / segs - 3)
            cv.drawPath(pp, paint(mix("#AEBBB8", "#E58A3C", k / (segs - 1)), 1, stroke=r * 0.14, cap="butt"))
        for lab, ang in (("BALKI", 155), ("ANIQ", 25)):
            ra = math.radians(180 + ang if False else ang)
            lx, ly = cx - r * 0.55 * math.cos(math.radians(ang)) * (-1), cy - r * 0.55 * math.sin(math.radians(ang))
            text(cv, lab, lx, ly, 32, INK)
        ang = math.radians(180 + 180 * val)
        line(cv, [(cx, cy), (cx + r * 0.66 * math.cos(ang), cy + r * 0.66 * math.sin(ang))], INK, 12)
        circle(cv, cx, cy, 20, INK)

def scene15(cv, t, lt, dur):
    P = pal(0)
    L = P["L"]
    t_aniq = wtt(15, "aniq"); t_rep = wtt(15, "repost")
    spin = ease_io((t - t_rep - 0.03) / 0.5)
    cam = Cam(540, 1000, 1.0, 360 * spin if 0 < spin < 1 else 0.0)
    wind = wind_at(t)
    with at_layer(cv, cam, 0.0): sky(cv, P, horizon=1150)
    with at_layer(cv, cam, 0.06): sun(cv, 170, 1080, 140, P, t)
    with at_layer(cv, cam, 0.15): hill(cv, Hill(1080, [(-100, 400, 50), (1200, 400, 60)], 1, 12), L[0])
    with at_layer(cv, cam, 0.3): hill(cv, Hill(1140, [(200, 330, 60), (1000, 420, 50)], 2, 10), L[1])
    rise = ease_out(lt / 0.7)
    val = 0.06 + 0.88 * ease_io((t - (t_aniq - 0.45)) / 0.6)
    with at_layer(cv, cam, 0.4):
        gy = GY + 420 * (1 - rise)
        gauge(cv, GX, gy, GR, val)
        if rise > 0.05:
            text(cv, "ISHONCHING QANCHA?", GX - 40, gy - GR - 56, 50, INK, rise)
    with at_layer(cv, cam, 0.5):
        h3 = Hill(1200, [(650, 360, 30)], 3, 8); hill(cv, h3, L[2]); grass(cv, h3, L[2], t, -1200, 2400, 30, 8, 18, wind * 0.6, 3)
    with at_layer(cv, cam, 0.75):
        h4 = Hill(1255, [(300, 280, 40), (1150, 300, 30)], 4, 6); hill(cv, h4, L[3]); grass(cv, h4, L[3], t, -1400, 2600, 24, 10, 24, wind * 0.8, 4)
    near_ground(cv, cam, P, t, H15, wind=wind)
    with at_layer(cv, cam, 1.0):
        hs = 0.30
        hx = 205; hy = H15.y(hx) + 10
        t_hug = SC_START[15] + 1.15
        walk_u = clamp01(lt / 1.15)
        fx = lerp(760, 352, walk_u)
        fy = H15.y(fx) + 10
        walking = walk_u < 1
        hug = ease_io((t - t_hug) / 0.3)
        point = ease_out((t - t_rep) / 0.18)
        Cf = friend_colors(0)
        hero_kwargs = dict(t=t, wind=wind, turn=0.25 * hug)
        if point > 0:
            h_arm = ("fk", lerp(70, 168, point), lerp(100, 182, point))
        else:
            h_arm = reach_arm((hx, hy), hs, 1, (fx + 4, fy - 330), hug)
        draw_person(cv, hx, hy, hs, HERO, arm=h_arm, layer="body", **hero_kwargs)
        f_arm = reach_arm((fx, fy), hs, -1, (hx - 4, hy - 330), hug)
        draw_person(cv, fx, fy, hs, Cf, facing=-1, t=t, wind=wind * 0.7, walk=(lt * 9.5 if walking else None),
                    arm=f_arm, lean=-3 * hug)
        draw_person(cv, hx, hy, hs, HERO, arm=h_arm, layer="arm", hand="point" if point > 0.5 else "fist",
                    finger_dir=(0.05, -1), finger_len=clamp01((point - 0.5) / 0.3), **hero_kwargs)
    QA["gesture"] = "point" if point > 0 else ("hug" if hug > 0 else "walk")
    QA["icon"] = "repost" if t >= t_rep else "gauge"
    if t >= t_rep:
        k = t - t_rep
        repost_icon(cv, 280, 600, 66 * pop_scale(k, 0.3), "#E58A3C", 1.0, -120 * ease_out(k / 0.6))
        confetti(cv, t, t_rep + 0.05, 9, 70)

# ---------------------------------------------------------------- 16. tomorrow: dome + lantern comments
def scene16(cv, t, lt, dur):
    t_izoh = wtt(16, "izoh")
    shot_b = t >= t_izoh
    if not shot_b:
        n = 0.7 * ease_io((t - SC_START[16]) / (t_izoh - SC_START[16]))
        P = pal(n)
        cam = Cam(560, 1040, 1.15)
        sun_y = lerp(1000, 1330, ease_in((t - SC_START[16]) / (t_izoh - SC_START[16])))
        wind = wind_at(t)
        steppe_layers(cv, cam, P, t, wind=wind, sun_xy=(700, sun_y), sun_r=200, moon_xy=None)
        near_ground(cv, cam, P, t, NEAR1, wind=wind)
        with at_layer(cv, cam, 1.0):
            gy = NEAR1.y(PED1_X)
            top = pedestal(cv, PED1_X, gy + 6, 0.78, P["L"][4], mix(P["L"][4], "#8C9FA1", 0.25))
            btn_top = button(cv, PED1_X, top + 4, 0.78, t, glow_a=0.5)
            # glass dome
            dr = 92
            p = skia.Path(); p.addArc(skia.Rect.MakeLTRB(PED1_X - dr, top - dr * 1.25, PED1_X + dr, top + dr * 0.75), 180, 180); p.close()
            cv.drawPath(p, paint("#E9F0EE", 0.30))
            cv.drawPath(p, paint("#F4EDDF", 0.7, stroke=4))
            pp = skia.Path(); pp.addArc(skia.Rect.MakeLTRB(PED1_X - dr * 0.75, top - dr * 1.05, PED1_X + dr * 0.75, top + dr * 0.5), 200, 50)
            cv.drawPath(pp, paint("#FFFFFF", 0.6, stroke=7))
            rrect(cv, PED1_X - dr - 6, top - 6, 2 * dr + 12, 12, 5, mix(P["L"][4], "#8C9FA1", 0.4))
            padlock(cv, PED1_X + 2, top + 30, 0.62, "#C7A548" if False else mix(P["L"][4], "#000000", 0.2), 1 - ease_out(lt / 0.12))
            tag(cv, "NATIJA ERTAGA", PED1_X, top - dr * 1.3, 30, 1.0, pop_scale(lt - 0.05, 0.3))
    else:
        lb = t - t_izoh
        P = pal(0.7 + 0.3 * ease_io(lb / 0.6))
        tilt = ease_io(lb / (SC_START[17] - t_izoh))
        cam = Cam(560, lerp(1040, 620, tilt), 1.15)
        wind = wind_at(t)
        steppe_layers(cv, cam, P, t, wind=wind, moon_xy=(820, 300), star_a=P["n"])
        with at_layer(cv, cam, 0.0): stars(cv, t, P["n"], -300, 1400, -1100, 200)
        near_ground(cv, cam, P, t, NEAR1, wind=wind)
        with at_layer(cv, cam, 1.0):
            gy = NEAR1.y(PED1_X)
            top = pedestal(cv, PED1_X, gy + 6, 0.78, P["L"][4], mix(P["L"][4], "#8C9FA1", 0.25))
            button(cv, PED1_X, top + 4, 0.78, t, glow_a=0.4)
        # lantern bubbles float up (screen space with a bit of camera parallax)
        rng = np.random.default_rng(16)
        for k in range(14):
            x = rng.uniform(130, 950); d0 = rng.uniform(-0.6, 2.4); v = rng.uniform(380, 560); s = rng.uniform(0.7, 1.15)
            tt = lb - d0
            y = 2000 - v * tt - 300 * tilt
            if y < -150 or y > 2050: continue
            xx = x + 26 * math.sin(tt * 1.6 + k)
            la = smooth((1440 - y) / 110) * smooth((y - 330) / 110)
            if la <= 0.01: continue
            with layer_alpha(cv, la):
                glow(cv, xx, y, 120 * s, "#E7A05C", 0.45)
                bubble(cv, xx, y, 110 * s, 96 * s, 1.0, 1.0, tail=-1 if k % 2 else 1)
                text(cv, "1" if k % 2 == 0 else "2", xx, y, 56 * s, INK)
        sc = pop_scale(lb - 0.1, 0.3)
        if lb > 0.1:
            with xf(cv, 540, 820, sc):
                txt = "BOSADI: ? · BOSMAYDI: ?"
                w = text_w(txt, 46) + 80
                plate(cv, -w / 2, -60, w, 120, 36, 0.92)
                text_runs(cv, [("BOSADI: ", INK), ("?", "#E1742F"), ("  ·  BOSMAYDI: ", INK), ("?", "#E1742F")], 0, 0, 46)

# ---------------------------------------------------------------- 17. subscribe
def scene17(cv, t, lt, dur):
    P = pal(1)
    L = P["L"]
    cam = Cam(540, 960, 1.0 + 0.03 * lt / dur)
    with at_layer(cv, cam, 0.0):
        sky(cv, P, horizon=1500); stars(cv, t, 1.0, -200, 1300, -300, 1300)
    with at_layer(cv, cam, 0.06): moon(cv, 260, 540, 120, P, t, 1.0)
    with at_layer(cv, cam, 0.3): hill(cv, Hill(1420, [(300, 400, 80), (1000, 400, 60)], 5, 8), L[1])
    with at_layer(cv, cam, 0.6): hill(cv, Hill(1560, [(700, 400, 70)], 6, 6), L[3])
    # profile plate (right)
    t_tap = SC_START[17] + 0.16
    press = ease_out((t - t_tap) / 0.08) * (1 - ease_io((t - t_tap - 0.22) / 0.2))
    px, py = 772, 930
    with xf(cv, px, py, pop_scale(lt + 0.25, 0.3)):
        plate(cv, -240, -260, 480, 520, 44, 0.9)
        avatar(cv, 0, -130, 92, hero=True)
        rrect(cv, -150, -12, 300, 26, 13, "#AEBBB8")
        rrect(cv, -110, 32, 220, 20, 10, "#C6CEC9")
        by = 150 + 8 * press
        if press > 0: glow(cv, 0, by, 260, "#E58A3C", 0.6 * press)
        rrect(cv, -190, by - 52, 380, 104, 52, mix("#E58A3C", "#C9702A", press))
        text(cv, uz("Obuna bo'ling"), 30, by, 44, "#F4EDDF")
    # hero close-up, side view, tapping
    with at_layer(cv, cam, 1.0):
        hs = 1.05
        hx, hy = 330, 1350 + (1700 - 888) * hs
        tgt_screen = (px - 262, py + 150 + 8 * press + 34)
        reach = ease_out((lt + 0.1) / 0.2) * (1 - ease_io((t - t_tap - 0.5) / 0.4))
        arm = reach_arm((hx, hy), hs, 1, tgt_screen, reach)
        QA["icon"] = "subscribe_button"
        QA["gesture"] = ("tap" if press > 0.05 else "reach") if reach > 0.3 else "rest"
        draw_person(cv, hx, hy, hs, HERO, t=t, turn=0.15, arm=arm, hand="point" if reach > 0.4 else "fist",
                    finger_dir=(1, 0.05), finger_len=clamp01((reach - 0.4) / 0.4), wind=0.15 * math.sin(t))

SCENE_FN = {1: scene1, 2: scene2, 3: scene3, 4: scene4, 5: scene5, 6: scene6, 7: scene7, 8: scene8, 9: scene9,
            10: scene10, 11: scene11, 12: scene12, 13: scene13, 14: scene14, 15: scene15, 16: scene16, 17: scene17}
