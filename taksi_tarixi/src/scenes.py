# The 15 scenes. Each scene function returns the scene picture (RGBA, before grain/text/subtitles).
import os, math, json, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
from gfx import (W, H, FPS, Pen, mask_pen, hx, mix, lerp, clamp01, smooth, ease_out, ease_in, ease_io, ease_back, ramp,
                 PAL, pal_mix, ACCENT, CREAM, INK, sky, sun_img, comp, paste_color, zoom, desaturate, with_alpha,
                 catmull, circle_pts, rot)
from env import Env
import props as P
import hero as HR

HERE = os.path.dirname(os.path.abspath(__file__))
TM = json.load(open(os.path.join(HERE, 'timing.json'), encoding='utf-8'))
WORDS = TM['words']
SC_START = {int(k): v for k, v in TM['scene_start'].items()}
N_FRAMES = int(TM['audio_dur'] * FPS)
END_T = N_FRAMES / FPS


def fr(t): return int(round(t * FPS))


SC_FR = {k: fr(v) for k, v in SC_START.items()}
SC_END_FR = {k: (SC_FR[k + 1] if k < 15 else N_FRAMES) for k in SC_FR}
APOS = "ʻʼ'`‘’"


def nrm(s):
    s = s.lower()
    for a in APOS: s = s.replace(a, "'")
    return ''.join(c for c in s if c.isalpha() or c == "'")


def wt(scene, key):
    """frame-quantised start time of the first word in `scene` starting with key"""
    for w in WORDS:
        if w['scene'] == scene and nrm(w['text']).startswith(key): return fr(w['start']) / FPS
    raise KeyError((scene, key))


def scene_at(i):
    k = 1
    for s in sorted(SC_FR):
        if i >= SC_FR[s]: k = s
    return k


@functools.lru_cache(None)
def ENV(name):
    return {'A1': lambda: Env('A', 1.0, 1185, seed=3), 'A3': lambda: Env('A', 1.45, 1200, seed=7),
            'A13': lambda: Env('A', 1.3, 1210, seed=13), 'A14': lambda: Env('A', 2.0, 1480, seed=14),
            'A4': lambda: Env('A', 1.0, 1250, seed=3), 'B': lambda: Env('B', 1.0, 1250, seed=4),
            'B5': lambda: Env('B', 1.3, 1290, seed=6), 'B8': lambda: Env('B', 2.0, 1560, seed=8),
            'B9': lambda: Env('B', 1.25, 1300, seed=11), 'B12': lambda: Env('B', 1.5, 1330, seed=12),
            'B10': lambda: Env('B', 1.6, 1500, seed=10)}[name]()


A_ = lambda c, a=255: tuple(c[:3]) + (a,)


# ------------------------------------------------------------------ helpers
def rotate_about(im, ax, ay, deg):
    R = int(math.ceil(max(math.hypot(ax - cx, ay - cy) for cx in (0, im.width) for cy in (0, im.height)))) + 2
    c = Image.new('RGBA', (2 * R, 2 * R), (0, 0, 0, 0)); c.paste(im, (int(round(R - ax)), int(round(R - ay))))
    if abs(deg) > 0.01: c = c.convert('RGBa').rotate(deg, resample=Image.BILINEAR).convert('RGBA')
    return c, R


def put_sign(frame, s, cx, by, ang=0.0, sx=1.0, sy=1.0, alpha=1.0):
    """roof sign with its bottom-centre at (cx, by), rotated by ang degrees (ccw)"""
    sg = P.roof_sign(round(s, 3))
    pad = int(10 * s)
    if sx != 1.0 or sy != 1.0:
        sg = sg.resize((max(1, int(sg.width * sx)), max(1, int(sg.height * sy))), Image.BICUBIC)
    ax, ay = sg.width / 2, (pad + 54 * s) * sy
    im, R = rotate_about(sg, ax, ay, ang)
    if alpha < 1: im = with_alpha(im, alpha)
    comp(frame, im, (cx - R, by - R))


def put_taxi(frame, pal, x_rear, gy, s, wheel_ang=0.0, hero_pose=None, hero=True, point_down=0.0, sign=None):
    im, anc = P.taxi_sprite(s, pal, wheel_ang, hero_pose, hero, point_down)
    comp(frame, im, (x_rear - anc[0], gy - anc[1]))
    if sign is not None:
        put_sign(frame, s, x_rear + P.ROOF_MOUNT[0] * s + sign.get('dx', 0), gy + P.ROOF_MOUNT[1] * s - sign.get('lift', 0) + 2,
                 sign.get('ang', 0))


def put_cab(frame, pal, x, gy, s, **kw):
    im, anc = P.cab_sprite(s, pal, **kw)
    comp(frame, im, (x - anc[0], gy - anc[1]))


def put_hero(frame, pose, x, gy, s, flip=False):
    im, anc, info = HR.hero_sprite(pose, s, flip)
    comp(frame, im, (x - anc[0], gy - anc[1]))
    f = -1 if flip else 1
    if 'hand' in info:
        info['hand_px'] = (x + f * info['hand'][0] * s, gy + info['hand'][1] * s)
    return info


def put_person(frame, col, x, gy, s, flip=False, **kw):
    w, h = int(560 * s), int(720 * s)
    p = Pen(w, h, s, w / 2, 660 * s, flip)
    Wr = P.draw_person(p, A_(col), **kw)
    comp(frame, p.result(), (x - w / 2, gy - 660 * s))
    return (x + (-1 if flip else 1) * Wr[0] * s, gy + Wr[1] * s)


def ik2(S, T, L1, L2, prefer=1):
    """2-link IK in design convention (angle 0 = down, + = forward/+x). returns (a1, e)."""
    dx, dy = T[0] - S[0], T[1] - S[1]
    D = max(1e-3, min(math.hypot(dx, dy), L1 + L2 - 1e-3))
    base = math.degrees(math.atan2(dx, dy))
    c = (L1 * L1 + D * D - L2 * L2) / (2 * L1 * D)
    off = math.degrees(math.acos(max(-1, min(1, c))))
    a1 = base + prefer * off
    c2 = (L1 * L1 + L2 * L2 - D * D) / (2 * L1 * L2)
    e = -prefer * (180 - math.degrees(math.acos(max(-1, min(1, c2)))))
    return a1, e


def bubble(frame, cx, cy, w, h, glyph, scale=1.0, tail=(0, 1), gcol=INK, size=78):
    if scale <= 0.02: return
    S = 2
    bw, bh = int((w + 80) * scale), int((h + 90) * scale)
    p = Pen(bw, bh, scale, bw / 2, bh / 2 - 15 * scale)
    P.draw_bubble(p, 0, 0, w, h, A_(CREAM), tail)
    im = p.result()
    if glyph:
        d = ImageDraw.Draw(im)
        f = P.font(P.FONT_BL, size * scale)
        d.text((bw / 2, bh / 2 - 15 * scale), glyph, font=f, fill=A_(gcol), anchor='mm')
    comp(frame, im, (cx - bw / 2, cy - bh / 2 + 15 * scale))


def pop(t, t0, dur=0.15):
    """pop-in scale for something that appears at t0"""
    t0 = t0 - 1 / FPS
    if t < t0: return 0.0
    return max(0.35, ease_back(ramp(t, t0, t0 + dur), 2.2)) if t >= t0 + 1 / FPS else 0.0


def ring(frame, cx, cy, r, width, col, alpha):
    if alpha <= 0.01: return
    R = int(r + width + 4)
    p = mask_pen(2 * R, 2 * R)
    p.circle(R, R, r + width / 2, 255); p.circle(R, R, max(0, r - width / 2), 0)
    m = p.result().filter(ImageFilter.GaussianBlur(width * 0.35))
    paste_color(frame, col, m, (cx - R, cy - R), alpha)


def glow(frame, cx, cy, r, col, alpha):
    if alpha <= 0.01: return
    R = int(r * 1.6)
    p = mask_pen(2 * R, 2 * R); p.circle(R, R, r, 255)
    m = p.result().filter(ImageFilter.GaussianBlur(r * 0.45))
    paste_color(frame, col, m, (cx - R, cy - R), alpha)


# ------------------------------------------------------------------ Environment A street pieces
def lamp_screen(env, cam_x, cam_y):
    L = env.layers[3]; off = L.offset(cam_x); out = []
    for (lx, ly) in env.lamps:
        for dx in (-env.period, 0, env.period):
            sx = lx - off + dx
            if -800 < sx < W + 800: out.append((sx, ly + cam_y * L.par))
    return sorted(out)


def wire_y(posts, x, sag):
    for (x0, y0), (x1, y1) in zip(posts[:-1], posts[1:]):
        if x0 <= x <= x1:
            u = (x - x0) / (x1 - x0); return y0 + (y1 - y0) * u + sag * 4 * u * (1 - u)
    return posts[0][1] if posts else 0


def draw_wire(frame, env, pal, cam_x, cam_y):
    posts = lamp_screen(env, cam_x, cam_y)
    p = mask_pen(W, H)
    sag = 36 * env.sc
    for (x0, y0), (x1, y1) in zip(posts[:-1], posts[1:]):
        pts = [(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u + sag * 4 * u * (1 - u)) for u in np.linspace(0, 1, 18)]
        p.line(pts, 255, 3.2)
    paste_color(frame, pal['L'][3], p.result())
    return posts, sag


PIGEON_X = (560, 604, 650, 712, 778, 836)


def cam1(t): return 520 + 260 * t                 # scene 1 / 15 camera (truck right)


def taxi1_x(t): return 200 + 12 * t


def sign_state(tt):
    env = 1.0 if tt >= 0 else smooth((tt + 0.5) / 0.5)
    amp = (3 + 6 * clamp01(tt / 1.96)) * env
    ang = amp * math.sin(2 * math.pi * 3.1 * tt + 0.6)
    lift = (6 + 34 * clamp01(tt / 1.96) ** 1.5) * env if tt >= 0 else 6 * env
    return dict(ang=ang, lift=lift, dx=-5 * clamp01(tt / 1.96))


def fg_curb(frame, pal, cam_x, y=1800, par=1.5, sc=1.0):
    """nearest foreground: dark curb band + bollards drifting faster than the road"""
    col = mix(pal['L'][4], INK, 0.45)
    if y - 100 * sc >= H: return
    d = ImageDraw.Draw(frame)
    if y < H: d.rectangle((0, y, W, H), fill=col)
    per = 340 * sc; off = (cam_x * par) % per
    p = mask_pen(W, int(110 * sc))
    x = -off
    while x < W + per:
        p.rrect(x, 10 * sc, x + 34 * sc, 110 * sc, 14 * sc, 255)
        x += per
    paste_color(frame, col, p.result(), (0, y - 100 * sc))


def base_A(env, pal, t, cam_x, cam_y=0.0, sun=None, hooks=None, win_t=None, frozen=False):
    f = sky(pal)
    env.render(f, pal, t, cam_x, cam_y, hooks=hooks, sun=sun, win_t=win_t, frozen=frozen)
    return f


def draw_busstop(frame, pal, env, cam_x, cam_y, wx):
    L = env.layers[3]; sc = env.sc; off = L.offset(cam_x)
    x = wx - off; gy = L.y0 + env.L3_h - 26 * sc + cam_y * L.par
    if x > W + 50 or x < -500 * sc: return
    col = A_(pal['L'][3]); panel = A_(mix(pal['L'][3], pal['L'][2], 0.55))
    sc = sc * 0.72
    w, h = int(420 * sc), int(360 * sc)
    p = Pen(w, h, sc, 20 * sc, 340 * sc)
    p.rect(10, -270, 280, -70, panel)                      # back panel (glass)
    p.rect(0, -300, 10, 0, col); p.rect(280, -300, 290, 0, col)
    p.rrect(-20, -318, 320, -296, 6, col)                   # roof slab
    p.rect(50, -118, 240, -104, col); p.rect(60, -104, 68, 0, col); p.rect(222, -104, 230, 0, col)   # bench
    p.rect(348, -330, 356, 0, col); p.circle(352, -330, 24, col)                                   # stop sign pole
    comp(frame, p.result(), (x - 20 * sc, gy - 340 * sc))


# ================================================================== SCENES
def s01(i, t, lt, dur):
    env = ENV('A1'); pal = PAL['A']; cx = cam1(t)
    def h3(f):
        posts, sag = draw_wire(f, env, pal, cx, 0)
        p = mask_pen(W, 700)
        off0 = env.layers[3].offset(cam1(0)); off = env.layers[3].offset(cx)
        for k, px in enumerate(PIGEON_X):
            x = px + off0 - off
            y = wire_y(posts, x, sag)
            P.draw_pigeon_sit(p, x, y - 400, 1.05, 255, bob=2 * math.sin(t * 5 + k * 1.7) if k % 2 else 0)
        paste_color(f, pal['L'][4], p.result(), (0, 400))
    def h4(f):
        env.draw_dashes(f, pal['L'][3], cx)
        st = sign_state(t)
        put_taxi(f, pal, taxi1_x(t), 1225 + 1.2 * math.sin(t * 9), 0.95, (260 + 12) * t / (64 * 0.95), sign=st)
        fg_curb(f, pal, cx)
    return base_A(env, pal, t, cx, 0, sun=(630, 870 + 3 * t, 230), hooks={3: h3, 4: h4})


def s02(i, t, lt, dur):
    env = ENV('A1'); pal = PAL['A']
    t0 = SC_START[2]
    cx = cam1(t0) + 150 * lt - 30 * lt * lt
    cy = 160 + 250 * smooth(lt / dur)                  # tilt up: near layers sink more
    posts_box = {}
    def h3(f):
        posts, sag = draw_wire(f, env, pal, cx, cy)
        posts_box['p'] = (posts, sag)
        p = mask_pen(W, H)
        off0 = env.layers[3].offset(cam1(0)); offs = env.layers[3].offset(cam1(t0)); off = env.layers[3].offset(cx)
        for k, px in enumerate(PIGEON_X):
            x0 = px + off0 - offs
            y0 = wire_y(posts, x0, sag)
            d = max(0.0, lt - 0.03 * k)
            vx = (-260, 180, -120, 260, 120, 320)[k]; vy = (-520, -640, -700, -560, -760, -600)[k]
            x = x0 + vx * d; y = y0 + vy * d + 120 * d * d
            if d <= 0: P.draw_pigeon_sit(p, x, y, 1.05, 255)
            else: P.draw_pigeon_fly(p, x, y - 10, 1.05 + 0.25 * d, 255, d * 2 * math.pi * 7 + k, 1 if vx > 0 else -1)
        paste_color(f, pal['L'][4], p.result())
    sun = (600, 860, 240)
    def h4(f):
        env.draw_dashes(f, pal['L'][3], cx, cy)
        xr = taxi1_x(t0) + 110 * lt + 520 * lt * lt
        put_taxi(f, pal, xr, 1225 + cy, 0.95, (260 + 12) * t0 / (64 * 0.95) + (150 + 110 + 1000 * lt) * lt / 60)
        fg_curb(f, pal, cx, 1800 + cy * 1.4)
        # sign tears free and flies up through the sun, leaving the frame at the top
        st = sign_state(t0)
        sx0 = taxi1_x(t0) + P.ROOF_MOUNT[0] * 0.95 + st['dx']; sy0 = 1225 + 160 + P.ROOF_MOUNT[1] * 0.95 - st['lift']
        u = clamp01(lt / 1.45) ** 1.25
        P0 = (sx0, sy0); P1 = (sx0 + 30, sy0 - 360); P2 = (sun[0] - 60, sun[1] + 90); P3 = (sun[0] + 170, -260)
        bx = (1 - u) ** 3 * P0[0] + 3 * (1 - u) ** 2 * u * P1[0] + 3 * (1 - u) * u * u * P2[0] + u ** 3 * P3[0]
        by = (1 - u) ** 3 * P0[1] + 3 * (1 - u) ** 2 * u * P1[1] + 3 * (1 - u) * u * u * P2[1] + u ** 3 * P3[1]
        if by > -200:
            put_sign(f, 0.95 * (1 + 0.3 * u), bx, by - cy * 0.0, st['ang'] - 200 * u)
    return base_A(env, pal, t, cx, cy, sun=sun, hooks={3: h3, 4: h4})


def s03(i, t, lt, dur):
    env = ENV('A3'); pal = PAL['A']
    t0 = SC_START[3]; cx = 300 + 25 * lt
    tb1, tb2, tb3 = wt(3, 'birinchi'), wt(3, 'savol'), wt(3, 'qancha')
    def h3(f):
        draw_busstop(f, pal, env, cx, 0, env.layers[3].offset(300) - 70)
    def h4(f):
        env.draw_dashes(f, pal['L'][3], cx)
        put_taxi(f, pal, 230, 1232, 1.2, 0.4, hero=False)
        # passenger walks up from the left, then haggles
        u = clamp01((t - t0) / 1.0)
        px = lerp(-170, 330, ease_out(u) if u < 1 else 1)
        walking = u < 1
        arm = 0.0
        for tb in (tb1, tb3):
            if t >= tb - 0.1: arm = max(arm, smooth(ramp(t, tb - 0.1, tb + 0.05)) * (1 - smooth(ramp(t, tb + 0.9, tb + 1.2))))
        arm = max(arm, 0.75 * smooth(ramp(t, tb3 - 0.1, tb3 + 0.05)))
        put_person(f, pal['L'][3], px, 1262, 0.76, False, walk=(t * 7.5 if walking else None),
                   arm=arm * (0.85 + 0.15 * math.sin(t * 9)), nod=-4 * arm)
        # hero, facing the passenger
        g = smooth(ramp(t, tb2 - 0.12, tb2 + 0.03))
        a1 = lerp(8, 128, g) + 6 * g * math.sin(t * 8); e = lerp(14, -24, g)
        pose = dict(fa=(a1, e, 'flat' if g > 0.4 else 'open'), ba=(-6, 10, 'open'), nod=lerp(0, -4, g) + 2 * math.sin(t * 2),
                    breathe=0.5 + 0.5 * math.sin(t * 2.2))
        put_hero(f, pose, 760, 1262, 0.74, flip=True)
        # speech bubbles in turn: ? (passenger) -> ! (hero) -> ? (passenger)
        for (tb, tn, bx, by, g_, tail) in ((tb1, tb2, px + 30, 748, '?', (-0.2, 1)), (tb2, tb3, 735, 730, '!', (0.2, 1)),
                                            (tb3, 99, px + 30, 748, '?', (-0.2, 1))):
            if t >= tb:
                sc_ = pop(t, tb) * (1 - ease_in(ramp(t, tn, tn + 0.1)))
                bubble(f, bx, by, 112, 104, g_, sc_, tail)
    f = base_A(env, pal, t, cx, 0, sun=(900, 960 + 3 * lt, 260), hooks={3: h3, 4: h4})
    return zoom(f, 1 + 0.05 * smooth(lt / dur), 540, 1050)


def s04(i, t, lt, dur):
    """A -> B: camera trucks left (rewind), layers morph, palette crossfades, streaks."""
    eA, eB = ENV('A4'), ENV('B')
    p = clamp01(lt / dur); pal = pal_mix(p)
    cx = 3000 - 600 * lt - 380 * lt * lt
    f = sky(pal)
    sA = sun_img(PAL['A'], 230); sB = sun_img(PAL['B'], 180)
    sp = smooth(ramp(p, 0.1, 0.8))
    comp(f, with_alpha(sA, 1 - sp), (630 - sA.width / 2, 930 - sA.height / 2))
    comp(f, with_alpha(sB, sp), (740 - sB.width / 2, 1010 - sB.height / 2 - 30 * sp))
    m = [smooth(ramp(p, 0.08 + 0.09 * k, 0.43 + 0.09 * k)) for k in range(5)]
    for k in range(5):
        LA, LB = eA.layers[k], eB.layers[k]
        if m[k] < 1:
            LA.draw(f, pal['L'][k], cx, 0, 1 - m[k], t, win_rgb=pal['win'], sy=1 - 0.55 * m[k])
            if k == 3: eA.draw_poplars(f, pal['L'][3], cx, 0, t, (1 - m[k]))
        if m[k] > 0:
            LB.draw(f, pal['L'][k], cx, 0, m[k], t, sy=0.45 + 0.55 * m[k])
            if m[k] > 0.98 and hasattr(LB, 'winmask'):
                off = LB.offset(cx)
                wm = LB.winmask.crop((int(off), 0, int(off) + W, LB.winmask.height))
                f.paste(mix(pal['L'][k], pal['L'][k - 1], 0.5), (0, int(LB.y0)), wm)
            if k == 4:
                off = LB.offset(cx)
                sm = LB.stones.crop((int(off), 0, int(off) + W, LB.stones.height)).point(lambda v: int(v * 0.36 * m[4]))
                f.paste(pal['L'][3], (0, int(LB.y0)), sm)
        if k == 4:
            if m[4] < 1: eA.draw_dashes(f, pal['L'][3], cx, 0, 0.45 * (1 - m[4]))
            eB.draw_gaslamps(f, pal['L'][4], cx, 0, alpha=m[4]) if m[4] > 0 else None
    # vehicle: taxi (rolling backwards) -> horse cab
    mv = smooth(ramp(p, 0.42, 0.78))
    veh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if mv < 1:
        tx = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        put_taxi(tx, pal, 262, 1292, 0.8, -lt * 9)
        veh.alpha_composite(with_alpha(tx, 1 - mv))
    if mv > 0:
        cb = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        put_cab(cb, pal, 575, 1296, 0.38, phase=-lt * 1.6, wheel_ang=-lt * 6, meter=None)
        veh.alpha_composite(with_alpha(cb, mv))
    f.alpha_composite(veh)
    # rewind smear + streaks
    b = math.sin(math.pi * p) ** 1.5
    if b > 0.02:
        bl = f.resize((W // 12, H), Image.BILINEAR).resize((W, H), Image.BILINEAR)
        f = Image.blend(f, bl, 0.55 * b)
    rng = np.random.RandomState(3)
    d = ImageDraw.Draw(f, 'RGBA')
    for k in range(18):
        y = rng.uniform(260, 1750); L = rng.uniform(160, 520); sp_ = rng.uniform(2200, 3800); ph = rng.uniform(0, 1)
        x = ((lt * sp_ + ph * (W + L)) % (W + 2 * L)) - L
        a = int(255 * 0.38 * b * rng.uniform(0.6, 1))
        hgt = rng.uniform(2.5, 5)
        d.rounded_rectangle((x, y, x + L, y + hgt), radius=hgt / 2, fill=CREAM + (a,))
    return f


def s05(i, t, lt, dur):
    env = ENV('B5'); pal = PAL['B']; cx = 200 + 18 * lt
    t_h, t_y, t_k, t_o = wt(5, 'haydovchi'), wt(5, "yo'lovchi"), wt(5, 'kelishib'), wt(5, 'olgan')
    nod = -9 * math.sin(math.pi * clamp01((t - t_k) / 0.45)) if t >= t_k else 0.0
    def h3(f):
        env.draw_gaslamps(f, pal['L'][4], cx, 0, par=0.5, alpha=0.9)
    def h4(f):
        # passenger in a top hat with a cane, standing just behind the cab (by the door), talking up to the driver
        ga = smooth(ramp(t, t_y - 0.12, t_y + 0.05)) * (1 - 0.6 * smooth(ramp(t, t_k + 0.5, t_k + 0.9)))
        put_person(f, mix(pal['L'][4], pal['L'][3], 0.25), 500, 1306, 0.62, False, hat=True, cane=True,
                   arm=0.55 * ga + 0.1 * ga * math.sin(t * 8), nod=nod)
        gh = smooth(ramp(t, t_h - 0.12, t_h + 0.05)) * (1 - 0.7 * smooth(ramp(t, t_k + 0.4, t_k + 0.9)))
        a1 = lerp(48, 112, gh) + 7 * gh * math.sin(t * 7)
        pose = dict(fa=(a1, lerp(38, -12, gh), 'flat' if gh > 0.4 else 'fist'), ba=(44, 44, 'fist'), nod=nod,
                    breathe=0.5 + 0.5 * math.sin(t * 2), reins=gh < 0.3)
        shake = math.sin(2 * math.pi * 5 * (t - t_o)) * math.sin(math.pi * clamp01((t - t_o) / 0.6)) if t >= t_o else 0.0
        st = 0.0
        for th in (9.30, 9.62):
            if th <= t < th + 0.22: st = math.sin(math.pi * (t - th) / 0.22)
        put_cab(f, pal, 780, 1330, 0.6, phase=0.06 * st, walking=st > 0, hero_pose=pose, meter=None,
                head=2 * math.sin(t * 1.3), tail=t * 1.7, shake=shake)
    f = sky(pal)
    env.render(f, pal, t, cx, 0, hooks={3: h3, 4: h4}, sun=(880, 1040 - 8 * t, 170))
    return f


# --------------------------------------------------------------- scene 6: top-down, freeze, box drop
TD_S, TD_OX, TD_OY = 0.88, 1500 / 2 + 10, 2300 / 2 - 70 - 120


def _topdown_canvas(sat):
    pal = PAL['B']; CW, CH = 1500, 2300
    f = Image.new('RGBA', (CW, CH), A_(pal['L'][4]))
    # cobblestone rows seen from above
    p = mask_pen(CW, CH)
    y = 0; row = 0
    while y < CH:
        x = -(row % 2) * 34
        while x < CW:
            p.rrect(x + 4, y + 4, x + 64, y + 30, 10, 255); x += 68
        y += 36; row += 1
    paste_color(f, pal['L'][3], p.result(), (0, 0), 0.22)
    # curb + sidewalk strip on the left, a lamp and a pedestrian from above
    d = ImageDraw.Draw(f)
    d.rectangle((0, 0, 170, CH), fill=mix(pal['L'][3], pal['L'][2], 0.3)); d.rectangle((170, 0, 186, CH), fill=pal['L'][3])
    q = Pen(CW, CH, 1.0, 0, 0)
    q.circle(110, 520, 26, A_(pal['L'][4])); q.circle(110, 520, 12, A_(pal['L'][3]))
    q.circle(96, 1640, 34, A_(pal['L'][4])); q.circle(96, 1640, 21, A_(mix(pal['L'][4], INK, 0.3)))
    f.alpha_composite(q.result())
    # rig heading up (design +x -> screen up), scale 0.95, centred
    s, ox, oy = TD_S, TD_OX, TD_OY
    pen = Pen(CW, CH, s, ox, oy, rot_deg=-90)
    col = A_(pal['L'][4]); dark = A_(mix(pal['L'][4], INK, 0.35)); lite = A_(mix(pal['L'][4], pal['L'][3], 0.45))
    pen.line([(-170, -120), (500, -86)], dark, 12); pen.line([(-170, 120), (500, 86)], dark, 12)
    for (hx_, hy_) in ((480, -70), (480, 70), (120, -66), (120, 66)):       # hooves peeking out
        pen.ellipse(hx_, hy_, 26, 18, dark)
    pen.smooth([(40, -70), (160, -100), (330, -86), (470, -104), (560, -60), (580, 0), (560, 60), (470, 104), (330, 86),
                (160, 100), (40, 70), (10, 0)], dark, 5)                   # horse back (hips + shoulders)
    pen.capsule((520, 0), (700, 0), 96, 66, dark); pen.smooth([(690, -40), (760, -34), (830, -20), (846, 0), (830, 20), (760, 34), (690, 40)], dark, 4)
    pen.poly([(700, -26), (676, -52), (716, -32)], dark); pen.poly([(700, 26), (676, 52), (716, 32)], dark)
    pen.capsule((540, -6), (700, -4), 22, 18, A_(mix(pal['L'][4], INK, 0.55)))   # mane
    pen.capsule((30, 0), (-70, 10), 36, 18, dark)
    pen.rrect(-900, -152, -330, 152, 60, col)                               # carriage body
    pen.rrect(-915, -168, -640, 168, 80, lite)                              # folded hood
    pen.rrect(-560, -120, -380, 120, 30, A_(mix(pal['L'][4], pal['L'][3], 0.25)))   # passenger seat
    pen.rrect(-214, -100, -90, 100, 20, dark)                              # footboard / dash
    for (x, y, L_, w_) in ((-730, -186, 330, 26), (-730, 186, 330, 26), (-206, -172, 242, 22), (-206, 172, 242, 22)):
        pen.rrect(x - L_ / 2, y - w_ / 2, x + L_ / 2, y + w_ / 2, 8, A_(mix(pal['L'][4], INK, 0.55)))
    pen.rrect(-372, -112, -214, 112, 18, dark)                              # driver's box
    pen.rect(-236, 150, -196, 196, lite)                                    # meter mount (driver-side front wheel)
    f.alpha_composite(pen.result())
    hp = Pen(CW, CH, s, ox + 0 * s, oy + 300 * s, rot_deg=-90)              # hero on the box (design x=-300)
    HR.draw_hero_top(hp)
    hero_im = hp.result()
    f.alpha_composite(hero_im)
    if not sat: return f
    # chapan mask for "everything except the chapan desaturates"
    mp = Pen(CW, CH, s, ox, oy + 300 * s, rot_deg=-90)
    HR.draw_hero_top(mp, cm=HR.chapan_cmap())
    return f, mp.result().getchannel('A')


@functools.lru_cache(None)
def topdown_assets():
    f, cm = _topdown_canvas(True)
    g = desaturate(f, 0.4)
    g.paste(f, (0, 0), cm)          # chapan keeps its colour
    mount = (TD_OX + 176 * TD_S, TD_OY + 216 * TD_S)        # design (-216, +176) -> canvas
    return f, g, mount


def s06(i, t, lt, dur):
    f0, g0, mount = topdown_assets()
    tq = wt(6, 'quti')
    t_end = SC_START[7]
    freeze = smooth(ramp(lt, 0.0, 0.3)) * (1 - smooth(ramp(t, t_end - 0.35, t_end - 0.05)))
    img = Image.blend(f0, g0, freeze)
    ang = -7 + 9 * (lt / dur)                                       # very slow rotation
    intro = 1 - ease_out(ramp(lt, 0, 0.4))
    zm = 1.0 + 0.16 * intro
    ang += 10 * intro
    rim = img.rotate(ang, resample=Image.BILINEAR, center=(750, 1150))
    # camera shake after the landing
    sh = 0.0
    if t >= tq: sh = 4 * math.sin(2 * math.pi * 14 * (t - tq)) * (1 - clamp01((t - tq) / 0.25))
    cw, ch = W / zm, H / zm
    x0 = 750 - cw / 2 + sh; y0 = 1150 - ch / 2 + sh * 0.6
    f = rim.transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BILINEAR)
    def to_screen(px, py):
        a = math.radians(-ang)
        dx, dy = px - 750, py - 1150
        rx, ry = 750 + dx * math.cos(a) - dy * math.sin(a), 1150 + dx * math.sin(a) + dy * math.cos(a)
        return ((rx - x0) * zm, (ry - y0) * zm)
    mx, my = to_screen(*mount)
    # mist bands drift only when not frozen
    # the box: drops from the top of the frame and lands exactly on 'quti'
    fall = 0.32
    if t >= tq - fall:
        u = clamp01((t - (tq - fall)) / fall)
        by = lerp(-160, my, ease_in(u) if u < 1 else 1); bs = lerp(1.6, 1.0, ease_in(u))
        if t >= tq:
            k = t - tq; by = my - 10 * abs(math.sin(math.pi * clamp01(k / 0.16))) * (1 - clamp01(k / 0.16))
            bs = 1.0 + 0.06 * math.sin(math.pi * clamp01(k / 0.12))
        s = TD_S * zm * bs
        bw, bh = int(150 * s), int(130 * s)
        p = Pen(bw * 2, bh * 2, s, bw, bh, rot_deg=-ang)
        p.rrect(-56, -46, 56, 46, 12, A_(mix(PAL['B']['L'][4], INK, 0.25)))
        p.rect(-50, -40, 50, -32, A_(PAL['B']['L'][3]))
        p.circle(0, 4, 30, A_(CREAM)); p.capsule((0, 4), (16, -14), 5, 4, A_(INK)); p.circle(0, 4, 5, A_(ACCENT))
        im = p.result()
        if t < tq:   # soft shadow growing under the falling box
            glow(f, mx, my + 6, 60 * zm * (0.5 + 0.5 * u), INK, 0.25 * u)
        comp(f, im, (mx - bw, by - bh))
        if t >= tq:
            k = t - tq
            for j, dl in enumerate((0.0, 0.22)):
                kk = k - dl
                if kk >= 0:
                    ring(f, mx, my, 70 * zm + 160 * zm * ease_out(clamp01(kk / 0.7)), 14 * zm, ACCENT, 0.85 * (1 - clamp01(kk / 0.7)))
            glow(f, mx, my, 80 * zm, ACCENT, 0.22 * (1 - clamp01(k / 1.2)))
    return f


# --------------------------------------------------------------- scenes 7-12 (1891)
def s07(i, t, lt, dur):
    env = ENV('B'); pal = PAL['B']; cx = 900 + 30 * lt
    def h3(f):
        env.draw_gaslamps(f, pal['L'][4], cx, 0, par=0.5)
        for k, (x0, v) in enumerate(((120, 32), (760, -26), (930, 20))):
            x = x0 + v * lt
            q = Pen(W, 160, 0.2, x, 150, flip=v < 0, mode='L')
            P.draw_person(q, 255, walk=lt * 6 + k, hat=(k != 1), cane=(k == 0))
            paste_color(f, mix(pal['L'][3], pal['L'][4], 0.45), q.result(), (0, env.H0 - 150))
    def h4(f):
        midcol = mix(pal['L'][3], pal['L'][4], 0.5)
        mp = dict(pal); mp['L'] = list(pal['L']); mp['L'][4] = midcol; mp['L'][3] = mix(pal['L'][3], pal['L'][2], 0.4)
        for (x0, v, s, ph) in ((-60, 95, 0.21, 0.0), (1010, -70, 0.18, 0.4)):
            x = x0 + v * lt
            im, anc = P.cab_sprite(s, mp, flip=v < 0, phase=lt * 1.3 + ph, wheel_ang=abs(v) * lt / (160 * s) * (1 if v > 0 else -1),
                                   hero=False, meter=None, tail=lt * 3)
            comp(f, im, (x - anc[0], env.H0 + 36 - anc[1]))
        put_cab(f, pal, 610, 1318, 0.42, walking=False, meter={'needle': 0.0, 'roll': 0.0}, head=3 * math.sin(t * 1.6),
                tail=t * 2.0, hero_pose=dict(breathe=0.5 + 0.5 * math.sin(t * 2)))
    f = sky(pal)
    # pigeons flying across the sky
    def hsky(fr_):
        p = mask_pen(W, 700)
        for k in range(5):
            x = -80 + 230 * (lt + 0.13 * k) * 1.4 + 60 * k
            y = 380 - 30 * k + 20 * math.sin(lt * 3 + k)
            P.draw_pigeon_fly(p, x, y, 1.0, 255, lt * 2 * math.pi * 6 + k * 1.3, 1)
        paste_color(fr_, pal['L'][4], p.result(), (0, 380))
    env.render(f, pal, t, cx, 0, hooks={-1: hsky, 3: h3, 4: h4}, sun=(840, 730 - 18 * lt, 140))
    return zoom(f, 1 + 0.06 * smooth(lt / dur), 560, 1120)


def meter_closeup(f, s, ox, oy, needle, roll, flag_ang, pal, hand=None, wheel_ang=0.0, ss=2, flag_len=40):
    """close silhouette of the front wheel + taximeter (dark box, cream dial, flag lever)."""
    p = Pen(W, H, s, ox, oy, ss=ss)
    col = A_(pal['L'][4]); lid = A_(pal['L'][3]); dark = A_(mix(pal['L'][4], INK, 0.35))
    p.line([(-420, -296), (-170, -300), (300, -330)], col, 13)                      # shaft
    P.spoked_wheel(p, (-206, -120), 120, wheel_ang, col)
    x0, y0, x1, y1 = P.METER_BOX
    p.rect(x0 + 40, y1 - 4, x0 + 64, y1 + 30, col)
    # flag lever on top of the box (rotates down to start the meter)
    piv = (x1 - 22, y0 + 2)
    fa = math.radians(flag_ang)
    R = lambda pts: [rot(q, fa, piv) for q in pts]
    fl = flag_len
    p.poly(R([(piv[0] - 3, piv[1]), (piv[0] + 3, piv[1]), (piv[0] + 3, piv[1] - fl), (piv[0] - 3, piv[1] - fl)]), col)
    p.poly(R([(piv[0] - 2, piv[1] - fl), (piv[0] - 34, piv[1] - fl), (piv[0] - 34, piv[1] - fl + 24), (piv[0] - 2, piv[1] - fl + 24)]), col)
    p.poly(R([(piv[0] - 7, piv[1] - fl + 6), (piv[0] - 29, piv[1] - fl + 6), (piv[0] - 29, piv[1] - fl + 10), (piv[0] - 7, piv[1] - fl + 10)]), lid)
    p.rrect(x0, y0, x1, y1, 10, col)
    p.rect(x0 + 6, y0 + 4, x1 - 6, y0 + 12, lid)
    cx, cy, r = P.METER_DIAL
    p.circle(cx, cy, r, A_(CREAM))
    for k in range(11):
        a = math.radians(-130 + 26 * k)
        p.capsule((cx + (r - 3) * math.sin(a), cy - (r - 3) * math.cos(a)), (cx + (r - 8) * math.sin(a), cy - (r - 8) * math.cos(a)), 1.6, 1.6, A_(INK))
    a = math.radians(-130 + 260 * clamp01(needle))
    p.capsule((cx, cy), (cx + (r - 8) * math.sin(a), cy - (r - 8) * math.cos(a)), 3.4, 2, A_(INK))
    p.circle(cx, cy, 3.5, A_(ACCENT))
    for k in range(4):
        xx = x0 + 22 + k * 16
        p.rrect(xx, y1 - 30, xx + 12, y1 - 12, 3, dark)
    f.alpha_composite(p.result())
    # rolling digit strips (blurred, never legible)
    for k in range(4):
        xx = x0 + 22 + k * 16
        ph = roll * (1.0 + 0.9 * k) + 0.31 * k
        for j in range(2):
            yy = y1 - 30 + ((ph + j * 0.5) % 1.0) * 24 - 6
            if y1 - 30 <= yy <= y1 - 12 - 4:
                X0, Y0 = ox + s * (xx + 2), oy + s * yy
                d = ImageDraw.Draw(f)
                d.rounded_rectangle((X0, Y0, X0 + 8 * s, Y0 + 4 * s), radius=2 * s, fill=ACCENT)
    return p


def s08(i, t, lt, dur):
    env = ENV('B8'); pal = PAL['B']; cx = 400 + 14 * lt
    tf = wt(8, 'taksometrni')
    f = sky(pal)
    env.render(f, pal, t, cx, 0, sun=(880, 1180 - 10 * lt, 260))
    s = 4.0; ox, oy = 540 + 216 * s, 1050 + 323 * s
    k = ease_out(ramp(t, tf - 1 / FPS, tf + 0.18))
    flag = 95 * k                                      # the flag lever is pulled down exactly on 'taksometrni'
    needle = 0.02 + (0.16 * (t - tf - 0.1) if t > tf + 0.1 else 0)
    roll = max(0, t - tf - 0.1) * 1.8
    meter_closeup(f, s, ox, oy, needle, roll, flag, pal, flag_len=54)
    # the hero's hand (green sleeve, gold cuff) comes in from the right and pushes the flag down
    x0, y0, x1, y1 = P.METER_BOX
    piv = (ox + s * (x1 - 22), oy + s * (y0 + 2))
    ftop = rot((piv[0] - 14 * s, piv[1] - 46 * s), math.radians(flag), piv)
    reach = smooth(ramp(t, tf - 0.6, tf - 0.06)) * (1 - smooth(ramp(t, tf + 0.6, tf + 1.1)))
    if reach > 0.01 and not HR.HIDE:
        target = (ftop[0] + 36, ftop[1] - 4)
        start = (1400, 560)
        hxp = lerp(start[0], target[0], reach); hyp = lerp(start[1], target[1], reach)
        S = (hxp + 520, hyp - 120)
        d = (hxp - S[0], hyp - S[1]); L_ = math.hypot(*d); dn = (d[0] / L_, d[1] / L_)
        sp = Pen(W, H, 1.0, 0, 0, ss=2)
        sp.capsule(S, (hxp - dn[0] * 40, hyp - dn[1] * 40), 96, 86, A_(HR.C['CH']))
        sp.capsule((S[0] - 6, S[1] - 26), (hxp - dn[0] * 70 + 4, hyp - dn[1] * 70 - 26), 16, 14, A_(HR.C['CH_L']))
        sp.capsule((hxp - dn[0] * 66, hyp - dn[1] * 66), (hxp - dn[0] * 30, hyp - dn[1] * 30), 96, 100, A_(HR.C['GOLD']))
        hp = Pen(W, H, 3.4, hxp - dn[0] * 30, hyp - dn[1] * 30, ss=2)
        HR.draw_hand(hp, (0, 0), dn, 'flat', A_(HR.C['SKIN']))
        f.alpha_composite(sp.result()); f.alpha_composite(hp.result())
    return zoom(f, 1 + 0.05 * smooth(lt / dur), 540, 1000)


def s09(i, t, lt, dur):
    env = ENV('B9'); pal = PAL['B']
    v = 250; cx = 1200 + v * lt
    def h3(f): env.draw_gaslamps(f, pal['L'][4], cx, 0, par=0.5)
    def h4(f):
        bob = 2.0 * abs(math.sin(math.pi * lt * 2.0))
        put_cab(f, pal, 650, 1342 - bob, 0.55, phase=lt * 1.0, wheel_ang=v * lt / (164 * 0.55), walking=True,
                meter={'needle': 0.06 + 0.07 * lt, 'roll': lt * 1.6}, tail=lt * 4, head=3 * math.sin(lt * 2 * math.pi * 1.0),
                hero_pose=dict(breathe=0.5 + 0.5 * math.sin(t * 2), nod=1.5 * math.sin(lt * 2 * math.pi)))
    f = sky(pal)
    env.render(f, pal, t, cx, 0, hooks={3: h3, 4: h4}, sun=(820, 1060 - 10 * lt, 190))
    return f


@functools.lru_cache(maxsize=2)
def blurred_bg10():
    env = ENV('B10'); pal = PAL['B']
    f = sky(pal)
    env.render(f, pal, 21.0, 700, 0, sun=(800, 1120, 260))
    return f.filter(ImageFilter.GaussianBlur(9))


@functools.lru_cache(maxsize=1)
def digit_strip(size=118):
    f = P.font(P.FONT_XB, size)
    lh = int(size * 1.25)
    im = Image.new('RGBA', (int(size * 0.8), lh * 11), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k in range(11):
        d.text((im.width / 2, k * lh + lh / 2), str(k % 10), font=f, fill=A_(ACCENT), anchor='mm')
    return im, lh


def s10(i, t, lt, dur):
    pal = PAL['B']
    bg = blurred_bg10()
    sh = int(10 * lt)
    f = bg.crop((sh, 0, sh + W, H)) if sh else bg.copy()
    col = A_(pal['L'][4]); lid = A_(pal['L'][3])
    p = Pen(W, H, 1.0, 0, 0, ss=2)
    p.rrect(110, 600, 970, 1236, 46, col)
    p.rect(150, 622, 930, 640, lid)
    cx, cy, r = 540, 905, 252
    p.circle(cx, cy, r, A_(CREAM))
    for k in range(27):
        a = math.radians(-130 + 10 * k)
        big = k % 5 == 0
        p.capsule((cx + (r - 18) * math.sin(a), cy - (r - 18) * math.cos(a)),
                  (cx + (r - (52 if big else 36)) * math.sin(a), cy - (r - (52 if big else 36)) * math.cos(a)), 7 if big else 4.5, 4, A_(INK))
    # digit window inside the dial
    p.rrect(376, 1004, 704, 1104, 16, A_(mix(pal['L'][4], INK, 0.45)))
    frac = 0.12 + 0.30 * lt + 0.10 * lt * lt
    a = math.radians(-130 + 260 * min(0.97, frac))
    p.capsule((cx, cy), (cx + (r - 40) * math.sin(a), cy - (r - 40) * math.cos(a)), 15, 7, A_(INK))
    p.capsule((cx, cy), (cx - 40 * math.sin(a), cy + 40 * math.cos(a)), 15, 15, A_(INK))
    p.circle(cx, cy, 22, A_(ACCENT))
    f.alpha_composite(p.result())
    strip, lh = digit_strip()
    for k in range(4):
        wx = 392 + k * 78
        speed = (5.5 + 3.2 * k) * (1 + 1.2 * lt)          # digits per second, faster over time
        pos = (speed * lt + 0.37 * k + 0.5) % 10
        y = int(pos * lh)
        win = strip.crop((0, y, strip.width, y + lh)).resize((strip.width, lh))
        # vertical motion blur -> never legible
        bl = win.resize((5, 3), Image.BOX).resize((win.width, lh), Image.BICUBIC)     # pure rolling glow, no glyph shape survives
        bl = bl.filter(ImageFilter.GaussianBlur(6))
        bl = bl.resize((70, 96))
        comp(f, bl, (wx, 1006))
    return zoom(f, 1 + 0.035 * smooth(lt / dur), 540, 905)


def word_img(text, size, col=CREAM, shadow=True, font_path=None):
    fnt = P.font(font_path or P.FONT_BL, size)
    d0 = ImageDraw.Draw(Image.new('L', (1, 1)))
    bb = d0.textbbox((0, 0), text, font=fnt)
    pad = int(size * 0.35)
    w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new('L', (w, h), 0); ImageDraw.Draw(sh).text((pad - bb[0], pad - bb[1] + size * 0.05), text, font=fnt, fill=255)
        sh = sh.filter(ImageFilter.MaxFilter(int(size * 0.07) | 1)).filter(ImageFilter.GaussianBlur(size * 0.13))
        im.paste(A_(INK), (0, 0), sh.point(lambda v: int(min(255, v * 1.25) * 0.4)))
    ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), text, font=fnt, fill=A_(col))
    return im


def s11(i, t, lt, dur):
    env = ENV('B'); pal = PAL['B']; vcam = 110; cx = 2100 + vcam * lt
    t_ta, t_me = wt(11, 'takse'), wt(11, 'metron')
    t_end_word = [w for w in WORDS if w['scene'] == 11][-1]['end']
    t_merge = fr(t_end_word) / FPS
    def h3(f): env.draw_gaslamps(f, pal['L'][4], cx, 0, par=0.5)
    def h4(f):
        vx = 30
        put_cab(f, pal, 300 + vx * lt, 1312, 0.36, phase=lt * 1.05, wheel_ang=(vcam + vx) * lt / (164 * 0.36), walking=True,
                meter={'needle': 0.3 + 0.05 * lt, 'roll': lt * 2}, tail=lt * 3)
    f = sky(pal)
    env.render(f, pal, t, cx, 0, hooks={3: h3, 4: h4}, sun=(962, 640 - 14 * lt, 105))
    # sky words
    ym = 880
    mv = smooth(ramp(t, t_merge - 0.22, t_merge))
    if t >= t_ta and mv < 1:
        u = max(0.25, ease_out(ramp(t, t_ta - 1 / FPS, t_ta + 0.45)))
        im = word_img('TAXE', 104)
        x = lerp(255, 430, mv); y = lerp(ym + 140, ym, u)
        comp(f, with_alpha(im, u * (1 - mv)), (x - im.width / 2, y - im.height / 2))
    if t >= t_me and mv < 1:
        u = max(0.25, ease_out(ramp(t, t_me - 1 / FPS, t_me + 0.45)))
        im = word_img('METRON', 104)
        x = lerp(735, 640, mv); y = lerp(ym + 140, ym, u)
        comp(f, with_alpha(im, u * (1 - mv)), (x - im.width / 2, y - im.height / 2))
    if mv > 0:
        sc_ = 0.85 + 0.15 * ease_back(ramp(t, t_merge - 0.05, t_merge + 0.15), 2.5)
        im = word_img('TAXIMETER', 104)
        im = im.resize((int(im.width * sc_), int(im.height * sc_)), Image.BICUBIC)
        comp(f, with_alpha(im, mv), (540 - im.width / 2, ym - im.height / 2))
        if t >= t_merge: glow(f, 540, ym, 190, CREAM, 0.35 * (1 - clamp01((t - t_merge) / 0.4)))
    # the lost TAKSI sign falls back from the top toward the cab (snaps in scene 12)
    t_snap = SC_START[12]
    if t >= t_snap - 0.3:
        u = clamp01((t - (t_snap - 0.3)) / 0.3)
        tx = 300 + 30 * lt + (-216) * 0.36; ty = 1312 + (-378) * 0.36
        x = lerp(tx + 120, tx, u); y = lerp(-120, ty, ease_in(u))
        put_sign(f, lerp(0.75, 0.38, u), x, y, 40 * (1 - u) + 12 * math.sin(u * 9))
    return f


def s12(i, t, lt, dur):
    env = ENV('B12'); pal = PAL['B']; cx = 500 + 16 * lt
    t_h = wt(12, 'hisoblagichning')
    s = 0.75; ox, gy = 702, 1420
    bx = ox + P.METER_DIAL[0] * s; btop = gy + P.METER_BOX[1] * s
    def h3(f): env.draw_gaslamps(f, pal['L'][4], cx, 0, par=0.5)
    def h4(f):
        look = smooth(ramp(lt, 0.05, 0.3)) * (1 - 0.6 * smooth(ramp(lt, 1.4, 1.9)))
        put_cab(f, pal, ox, gy, s, walking=False, meter={'needle': 0.4, 'roll': 0.0}, tail=t * 2, head=2 * math.sin(t * 1.5),
                hero_pose=dict(nod=10 * look, breathe=0.5 + 0.5 * math.sin(t * 2)))
        # sign lands on the meter box exactly on «Taksi» (frame 0 of this scene): squash + settle
        k = lt
        sq = 1 + 0.16 * math.sin(math.pi * clamp01(k / 0.12)) * (1 if k < 0.12 else 0) - 0.07 * math.sin(math.pi * clamp01((k - 0.12) / 0.14)) * (k >= 0.12)
        put_sign(f, s, bx, btop + 2, 0, sx=2 - sq, sy=sq)
        ring(f, bx, btop - 22 * s, 60 + 150 * ease_out(clamp01(k / 0.6)), 12, ACCENT, 0.8 * (1 - clamp01(k / 0.6)))
        glow(f, bx, btop - 22 * s, 90, ACCENT, 0.3 * (1 - clamp01(k / 0.8)))
    f = sky(pal)
    env.render(f, pal, t, cx, 0, hooks={3: h3, 4: h4}, sun=(880, 1100 - 10 * lt, 200))
    # TAXIMETER above: METER fades out, TAXI stays and glows in accent
    fade = smooth(ramp(t, t_h, t_h + 0.45))
    a = word_img('TAXI', 112, mix(CREAM, ACCENT, fade)); b = word_img('METER', 112)
    pad = int(112 * 0.35)
    wa, wb = a.width - 2 * pad, b.width - 2 * pad
    total = wa + wb
    cxw = 540 + wb / 2 * fade * 0.0; y = 668
    xa = cxw - total / 2 - pad
    if fade > 0: glow(f, xa + a.width / 2, y, 150, ACCENT, 0.28 * fade * (0.85 + 0.15 * math.sin(t * 6)))
    comp(f, a, (xa, y - a.height / 2))
    comp(f, with_alpha(b, 1 - fade), (xa + wa, y - b.height / 2))
    z = 1 + 0.12 * ease_out(ramp(lt, 0, 0.35))
    return zoom(f, z, bx, btop - 20)


# --------------------------------------------------------------- scenes 13-15 (back to dusk)
def s13(i, t, lt, dur):
    env = ENV('A13'); p_ = smooth(ramp(lt, 0, 0.6)); pal = pal_mix(1 - p_)
    cx = 600 + 22 * lt
    ty = wt(13, 'yuboring')
    def h3(f):
        draw_busstop(f, pal, env, cx, 0, env.layers[3].offset(600) + 120)
        # distant pair haggling by a car (far sidewalk)
        far = mix(pal['L'][3], pal['L'][2], 0.35)
        im, anc = P.taxi_sprite(0.3, dict(pal, L=[pal['L'][0], pal['L'][1], pal['L'][2], mix(far, pal['L'][2], 0.4), far]), 0, hero=False)
        comp(f, im, (850 - anc[0], 1192 - anc[1]))
        put_person(f, far, 900, 1196, 0.2, False, arm=0.5 + 0.5 * math.sin(t * 5))
        put_person(f, far, 975, 1196, 0.2, True, arm=0.5 + 0.5 * math.sin(t * 5 + 2), hat=False)
    def h4(f):
        env.draw_dashes(f, pal['L'][3], cx)
        put_taxi(f, pal, -300, 1236, 1.1, 0.4, hero=False, sign=dict(lift=0, ang=0))
        # hero folds a sheet, then throws a paper airplane exactly on 'yuboring'
        th = smooth(ramp(t, ty - 0.12, ty)) ; back = smooth(ramp(t, ty - 0.45, ty - 0.12)) * (1 - th)
        a1 = lerp(52, 128, th) - 30 * back; e = lerp(58, -6, th) + 30 * back
        pose = dict(fa=(a1, e, 'fist'), ba=(46, 62, 'fist'), breathe=0.5 + 0.5 * math.sin(t * 2.2),
                    nod=-3 * th)
        info = put_hero(f, pose, 610, 1262, 0.74)
        hxp, hyp = info.get('hand_px', (0, 0))
        if t < ty and 'hand_px' in info:
            fold = smooth(ramp(t, SC_START[13] + 0.7, ty - 0.35))
            col = mix(CREAM, ACCENT, smooth(ramp(t, ty - 0.6, ty - 0.3)))
            draw_plane_or_sheet(f, hxp + 22, hyp - 6, fold, col, 1.0)
    f = base_A(env, pal, t, cx, 0, sun=(900, 950 + 4 * lt, 270), hooks={3: h3, 4: h4})
    if t >= ty:     # airplane flight toward the distant pair, out of frame
        u = clamp01((t - ty) / 0.75)
        st = put_hero_hand_pos_13(ty)
        x = lerp(st[0] + 22, 1200, ease_in(u) * 0.6 + u * 0.4); y = st[1] - 6 - 260 * math.sin(math.pi * u * 0.7) + 60 * u
        if x < W + 120: draw_plane_or_sheet(f, x, y, 1.0, ACCENT, lerp(1.25, 0.55, u), ang=-14 + 20 * u)
    return f


@functools.lru_cache(None)
def put_hero_hand_pos_13(ty):
    th = 1.0; a1 = lerp(52, 128, th); e = lerp(58, -6, th)
    E, Wr, d2 = HR.arm_points((2, -452), a1, e)
    return (610 + (Wr[0] + d2[0] * 2) * 0.74, 1262 + (Wr[1] + d2[1] * 2) * 0.74)


def draw_plane_or_sheet(f, x, y, fold, col, s, ang=0.0):
    """fold 0 = flat sheet, 1 = paper airplane (flat shapes)"""
    p = Pen(int(220 * s), int(160 * s), s, 110 * s, 80 * s, rot_deg=ang)
    if fold < 1:
        w = lerp(70, 20, fold); h = lerp(90, 30, fold)
        p.poly([(-w / 2, -h / 2), (w / 2, -h / 2 + 8 * fold), (w / 2 + 30 * fold, 0), (w / 2, h / 2 - 8 * fold), (-w / 2, h / 2)], A_(col))
    else:
        p.poly([(-46, -4), (52, -2), (-30, -34)], A_(col))
        p.poly([(-46, -4), (52, -2), (-20, 16)], A_(mix(col, INK, 0.25)))
        p.poly([(-46, -4), (52, -2), (-34, 4)], A_(mix(col, CREAM, 0.15)))
    comp(f, p.result(), (x - 110 * s, y - 80 * s))


def icon_handshake(p, cx, cy, s, col, bg):
    """flat handshake: two cuffs meeting, clasped hands (finger gaps in the background colour)"""
    X = lambda x: cx + x * s; Y = lambda y: cy + y * s
    p.rrect(X(-66), Y(-20), X(-44), Y(18), 4 * s, col); p.rrect(X(44), Y(-20), X(66), Y(18), 4 * s, col)
    p.poly([(X(-42), Y(-18)), (X(-6), Y(-26)), (X(26), Y(-12)), (X(20), Y(2)), (X(-6), Y(-6)), (X(-18), Y(16)), (X(-42), Y(16))], col)
    p.poly([(X(42), Y(-18)), (X(14), Y(-22)), (X(-14), Y(-4)), (X(-22), Y(12)), (X(-8), Y(26)), (X(22), Y(24)), (X(42), Y(14))], col)
    for k in range(3):
        xx = -10 + k * 11
        p.rect(X(xx), Y(8 + k * 2), X(xx + 2.6), Y(24), bg)


def icon_dial(p, cx, cy, s, col, bg):
    p.circle(cx, cy, 38 * s, col); p.circle(cx, cy, 27 * s, bg)
    p.capsule((cx, cy), (cx + 16 * s, cy - 14 * s), 6 * s, 5 * s, col); p.circle(cx, cy, 6 * s, col)
    p.rrect(cx - 6 * s, cy - 50 * s, cx + 6 * s, cy - 38 * s, 3 * s, col)


AB = dict(x0=578, y0=842, bw=482, bh=356, rows=(96, 266))     # bubble box and row centres (bubble coords)


def ab_bubble(f, t, t_in, t_a, t_b):
    sc_ = pop(t, t_in, 0.18)
    if sc_ <= 0.02: return None
    bw, bh = AB['bw'], AB['bh']
    img = Image.new('RGBA', (bw + 120, bh + 120), (0, 0, 0, 0))
    p = Pen(img.width, img.height, 1.0, 60, 60, ss=2)
    p.rrect(0, 0, bw, bh, 52, A_(CREAM))
    p.poly([(4, 22), (4, 92), (-58, 30)], A_(CREAM))                  # tail toward the hero's face
    hiA = max(0.5, smooth(ramp(t, t_a, t_a + 0.12))) * (t >= t_a) * (1 - smooth(ramp(t, t_b - 1 / FPS, t_b + 0.1)))
    hiB = max(0.5, smooth(ramp(t, t_b, t_b + 0.12))) * (t >= t_b)
    rows = ((AB['rows'][0], 'A', 'Savdo', hiA, 'hand'), (AB['rows'][1], 'B', 'Hisoblagich', hiB, 'dial'))
    for (ry, L, label, hi, ic) in rows:
        if hi > 0.01:
            p.rrect(16, ry - 74, bw - 16, ry + 74, 40, A_(mix(CREAM, ACCENT, 0.24 * hi)))
        p.circle(62, ry, 34, A_(mix(INK, ACCENT, hi)))
        bgc = A_(mix(CREAM, ACCENT, 0.24 * hi))
        if ic == 'hand': icon_handshake(p, 146, ry, 0.76, A_(ACCENT), bgc)
        else: icon_dial(p, 146, ry, 0.8, A_(ACCENT), bgc)
    im = p.result()
    d = ImageDraw.Draw(im)
    for (ry, L, label, hi, ic) in rows:
        d.text((60 + 62, 60 + ry + 2), L, font=P.font(P.FONT_BL, 40), fill=A_(CREAM), anchor='mm')
        d.text((60 + 196, 60 + ry), label, font=P.font(P.FONT_XB, 52 if label == 'Savdo' else 44), fill=A_(INK), anchor='lm')
    if sc_ != 1: im = im.resize((max(1, int(im.width * sc_)), max(1, int(im.height * sc_))), Image.BICUBIC)
    cx, cy = AB['x0'] + bw / 2, AB['y0'] + bh / 2
    comp(f, im, (cx - im.width / 2, cy - im.height / 2))
    return {'A': (AB['x0'], AB['y0'] + AB['rows'][0]), 'B': (AB['x0'], AB['y0'] + AB['rows'][1])}


def s14(i, t, lt, dur):
    env = ENV('A14'); pal = PAL['A']; cx = 400 + 18 * lt
    t_in, t_a, t_b = wt(14, 'siz'), wt(14, 'savdolashasizmi'), wt(14, 'hisoblagich')
    f = base_A(env, pal, t, cx, 0, sun=(880, 1180 + 3 * lt, 330))
    hx0, gy, s = 150, 2020, 2.2                     # waist-up, side view, hero on the left
    S = (2, -452)                                   # front shoulder (design units)
    turn = smooth(ramp(t, t_in, t_in + 0.35)) * 0.3     # gentle turn toward the camera (face stays readable)
    rest = (12, 24)
    def aim(row):
        """elbow stays low by the body; the wrist stops just left of the option row; the finger points at it"""
        tx = (AB['x0'] - 10 - hx0) / s - 50; ty = (AB['y0'] + AB['rows'][row] - gy) / s
        return ik2(S, (tx, ty), 118, 104, prefer=-1)
    aA, aB = aim(0), aim(1)
    gA = smooth(ramp(t, t_a - 0.16, t_a)); gB = smooth(ramp(t, t_b - 0.16, t_b))
    a1 = lerp(lerp(rest[0], aA[0], gA), aB[0], gB); e = lerp(lerp(rest[1], aA[1], gA), aB[1], gB)
    pointing = gA > 0.5
    hdir = (1.0, -0.04) if pointing else None
    pose = dict(fa=(a1, e, 'point' if pointing else 'open'), ba=(-4, 12, 'open'), turn=turn, hand_dir=hdir,
                nod=-2 * turn + 1.2 * math.sin(t * 2.4), breathe=0.5 + 0.5 * math.sin(t * 2.0))
    info = put_hero(f, pose, hx0, gy, s)
    ab_bubble(f, t, t_in, t_a, t_b)
    if pointing and 'hand' in info:      # the pointing finger stays in front of the bubble edge
        hp = Pen(W, H, s, hx0, gy, ss=2)
        HR.draw_hand(hp, info['hand'], info['hand_dir'], 'point', A_(HR.C['SKIN']))
        f.alpha_composite(hp.result())
    return zoom(f, 1 + 0.04 * smooth(lt / dur), 540, 900)


def s15(i, t, lt, dur):
    env = ENV('A1'); pal = PAL['A']
    tt = t - END_T                     # 0 at the loop point (= frame 0)
    cx = cam1(tt)
    t0 = SC_START[15]
    u = clamp01((t - t0) / (END_T - t0))
    xr = 200 + 12 * tt - 470 * (1 - ease_out(u))
    pd = smooth(ramp(t, t0, t0 + 0.12))
    def h3(f): draw_wire(f, env, pal, cx, 0)
    def h4(f):
        env.draw_dashes(f, pal['L'][3], cx)
        st = sign_state(tt)
        dist = 272 * tt + 980 * (1 - ease_out(u))
        put_taxi(f, pal, xr, 1225 + 1.2 * math.sin(t * 9), 0.95, (272 * tt - 470 * (1 - ease_out(u))) / 60.8, sign=st,
                 point_down=pd)
        fg_curb(f, pal, cx)
    return base_A(env, pal, t, cx, 0, sun=(630, 870 + 3 * tt, 230), hooks={3: h3, 4: h4})


SCENE_FN = {1: s01, 2: s02, 3: s03, 4: s04, 5: s05, 6: s06, 7: s07, 8: s08, 9: s09, 10: s10, 11: s11, 12: s12,
            13: s13, 14: s14, 15: s15}


def render_scene(i):
    k = scene_at(i)
    t = i / FPS
    lt = t - SC_START[k] if k > 1 else t
    dur = SC_END_FR[k] / FPS - SC_START[k]
    return k, SCENE_FN[k](i, t, max(0.0, lt), dur)
