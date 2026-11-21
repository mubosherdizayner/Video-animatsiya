# The 13 scenes. Each scene function maps a global frame index to a rendered world surface.
import json, math, os
import skia
from common import *
import world as WD
import frame as FR
import props as PR
from hero import *
from script_data import SCENES, ONSCREEN

HERE = os.path.dirname(os.path.abspath(__file__))
TIMING = json.load(open(os.path.join(HERE, "timing.json")))
AUDIO_DUR = float(open(os.path.join(HERE, "audio_dur.txt")).read())
N_FRAMES = int(round(AUDIO_DUR * FPS))
SC_IDS = [s[0] for s in SCENES]


def scene_words(k): return [w for w in TIMING if w["scene"] == k]


def word_frame(w): return int(round(w["start"] * FPS))


SC_START = {k: scene_words(k)[0]["start"] for k in SC_IDS}
SC_START[1] = 0.0
SC_FRAME = {k: int(round(SC_START[k] * FPS)) for k in SC_IDS}
SC_END_FRAME = {k: (SC_FRAME[k + 1] if k + 1 in SC_FRAME else N_FRAMES) for k in SC_IDS}
LAST = N_FRAMES - 1


def scene_at(i):
    for k in reversed(SC_IDS):
        if i >= SC_FRAME[k]: return k
    return 1


def local(i, k):
    return (i - SC_FRAME[k]) / FPS, (SC_END_FRAME[k] - SC_FRAME[k]) / FPS


TEXT_LIGHT = {7, 8, 9, 10, 11}

# ---------------------------------------------------------------- hero constants
HS = 0.25                                     # hero scale in wide shots (≈ 1/5.3 of the frame height)
HX0 = 430.0
HY0 = WD.ground_y(HX0) + 2
HALF = Arm(48, 150, "palm", 0.5, 0.62, 0.62)  # palm half raised (frame 0 / last frame)
STOP = Arm(62, 176, "palm", 1.0, 0.6, 0.45)   # full "stop" gesture
PRESENT = Arm(40, 116, "palm", 0.85, 0.72, 0.66)
POSE0 = dict(turn=0.5, laptop=True, arm=HOLD, farm=HALF)
SUN0 = (600.0, 820.0, 175.0)

# night set
SUPA_N = 420.0
PANEL_X0, PANEL_N = 700.0, 21
NGY = 1197.0
MOON = (650.0, 700.0, 96.0)
# dusk supa set
SUPA_D = 1540.0


def sun_dusk(W):
    return (SUN0[0], SUN0[1] + 5.0 * abs(W), SUN0[2])


def freeze_w(t):
    """scene 1: birds and leaves freeze mid-air 0.5-0.9 s"""
    if t < 0.5: return t
    if t < 0.9: return 0.5
    return t - 0.4


# ---------------------------------------------------------------- shared landscape drawing
def landscape(c, cam, pal, W, sun=None, glow=0.0, lit=0.0, moon=None, night=0.0, trees=((4, 95.0, 1.0),),
              ishkom=True, birds_w=None, leaves_w=None, near=None, hero=None, sun_alpha=1.0, sun_rot=None,
              bird_kw=None, stars=0.0, sky_extra=None, after_hero=None):
    WD.draw_sky(c, pal, glow=glow, sun=(sun[0] - cam.x * 0.03, sun[1], sun[2]) if sun else None)
    WD.draw_stars(c, stars, cam.x)
    if sun and sun_alpha > 0:
        WD.draw_sun(c, sun[0] - cam.x * 0.03, sun[1], sun[2], alpha=sun_alpha, rot_=(2 * W if sun_rot is None else sun_rot))
    if moon:
        WD.draw_moon(c, moon[0] - cam.x * 0.03, moon[1], moon[2], alpha=moon[3] if len(moon) > 3 else 1.0)
    if sky_extra: sky_extra(c)
    WD.draw_far(c, pal, cam.x, lit=lit)
    WD.draw_houses(c, pal, cam.x, lit=lit)
    if birds_w is not None:
        kw = dict(y0=590, x0=380, span=900)
        kw.update(bird_kw or {})
        c.save(); c.translate(-cam.x * 0.7, 0); WD.birds(c, pal, birds_w, **kw); c.restore()
    c.save(); c.translate(-cam.x, 0)
    WD.draw_ground(c, pal, cam.x - 900, cam.x + 2000)
    if ishkom:
        WD.draw_ishkom(c, pal, 830, 1150, WD.ground_y(900) + 6, 930)
    crowns = []
    for seed, x, s in trees:
        crowns.append(WD.draw_mulberry(c, pal, seed, x, WD.ground_y(x) + 5, s, W))
    if near: near(c)
    if hero: hero(c)
    if leaves_w is not None:
        for k, cr in enumerate(crowns):
            WD.falling_leaves(c, cr, leaves_w, WD.BANK + 160, seed=k + 1, s=1.0)
    if after_hero: after_hero(c)
    WD.draw_bank(c, pal, cam.x - 900, cam.x + 2000)
    c.restore()
    return crowns


def sunpath_front(cam, sun, W, strength=1.0):
    def f(c):
        c.save(); c.translate(-cam.x * 0.03, 0)
        WD.sun_path(c, sun[0], WD.BANK + 16, W, strength=strength)
        c.restore()
    return f


def hero_at(x, y, pose, s=HS, facing=1):
    def f(c):
        draw_hero(c, x, y, s, facing, pose)
    return f


# ---------------------------------------------------------------- scene 1: hook
def s1(i):
    t = i / FPS
    lt, D = local(i, 1)
    pal = WD.palette(0.0)
    Wf = freeze_w(t)
    cam = FR.Cam(zoom=1.0 + 0.03 * smooth(lt / D), cx=HX0, cy=1000)
    sun = sun_dusk(t)
    u = ease_out(t / 0.5)
    turn = lerp(0.5, 0.72, u)
    farm = HALF.lerp(STOP, u)
    if t > 1.45:
        v = ease_io((t - 1.45) / 0.55)
        farm = STOP.lerp(PRESENT, v)
        turn = lerp(0.72, 0.62, v)
        if t > 2.0:
            farm = Arm(PRESENT.a1 + 3 * math.sin((t - 2.0) * 3.2), PRESENT.a2 + 7 * math.sin((t - 2.0) * 3.2),
                       "palm", PRESENT.open, PRESENT.k, PRESENT.k1)
    pose = Pose(turn=turn, laptop=True, arm=HOLD, farm=farm)
    surf = FR.render_world(cam, lambda c: landscape(c, cam, pal, t, sun=sun, glow=0.9, lit=0.75, birds_w=Wf, leaves_w=Wf,
                                                    hero=hero_at(HX0, HY0, pose)),
                           sunpath_front(cam, sun, t), water=dict(t=t, pal=pal))
    return surf


# ---------------------------------------------------------------- scene 2: human calculators on the supa
def supa_set_dusk(c, pal, W, alphas=(1, 1, 1, 1, 1)):
    gy = WD.ground_y(SUPA_D) + 4
    WD.draw_mulberry(c, pal, 8, SUPA_D - 235, WD.ground_y(SUPA_D - 235) + 5, 0.86, W)
    PR.draw_supa_back(c, pal, SUPA_D, gy)
    PR.draw_calculators(c, pal, SUPA_D, gy, W, alphas)
    PR.draw_supa_front(c, pal, SUPA_D, gy)


def s2(i):
    lt, D = local(i, 2)
    W = 4.0 + lt
    pal = WD.palette(0.0)
    u = ease_io(lt / D)
    cam = FR.Cam(x=lerp(640, 1000, u), zoom=1.0 + 0.02 * u, cx=540, cy=1050)
    sun = sun_dusk(W * 0.2)
    hx = 760.0
    pose = Pose(turn=0.0, head_turn=0.12 * math.sin(lt * 2.0) ** 2, sway=2 * math.sin(lt * 2.4))
    surf = FR.render_world(cam, lambda c: landscape(c, cam, pal, W, sun=sun, glow=0.9, lit=0.75, birds_w=W, leaves_w=W,
                                                    near=lambda cc: supa_set_dusk(cc, pal, W),
                                                    hero=hero_at(hx, WD.ground_y(hx) + 2, pose, s=HS * 0.92)),
                           sunpath_front(cam, sun, W), water=dict(t=W, pal=pal))
    return surf


# ---------------------------------------------------------------- scene 3: "computer" was a job; digits become birds
DIGITS = ["2", "7", "+", "=", "9"]
_FONT = {}


def font(path, size):
    key = (path, size)
    if key not in _FONT:
        _FONT[key] = skia.Font(skia.Typeface.MakeFromFile(path), size)
    return _FONT[key]


FONT_DISPLAY = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_BOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def digit_state(j, lt):
    """digit j rises from scroll j, turns into a bird at ~y 820 and flies right across the sun"""
    t0 = 1.35 + 0.17 * j
    x0 = PR.calc_positions(SUPA_D)[j] + 44
    y0 = WD.ground_y(SUPA_D) + 4 - 74 - 12
    u = (lt - t0)
    if u < 0: return None
    rise = 1.25
    if u < rise:
        k = ease_io(u / rise)
        x = x0 + 30 * math.sin(u * 4 + j) + (1570 + (j - 2) * 30 - x0) * k
        y = y0 + (820 + 35 * (j - 2) * 0.6 - y0) * k
        return ("digit", x, y, 1.0, u)
    v = u - rise
    x = 1570 + (j - 2) * 30 + 150 * v + 40 * v * v
    y = 820 + 21 * (j - 2) - 30 * v
    return ("bird", x, y, min(1.0, v / 0.25), v)


def s3(i):
    lt, D = local(i, 3)
    W = 6.4 + lt
    pal = WD.palette(0.0)
    up = ease_io(clamp01((lt - 1.0) / (D - 1.0)))
    cam = FR.Cam(x=1000 + 18 * lt, y=330 * up, zoom=1.25, cx=540, cy=1150)
    sun = sun_dusk(W * 0.2)
    # hero walks in from the left, then gestures with an open hand towards the calculators
    x_start, x_end, T_walk = 1110.0, 1290.0, 1.25
    if lt < T_walk:
        k = lt / T_walk
        hx = lerp(x_start, x_end, k * (2 - k) * 0.5 + k * 0.5)
        dist = hx - x_start
        pose = Pose(walk=dist / 80.0 * math.pi, walk_amp=1.0 if k < 0.85 else (1 - k) / 0.15)
    else:
        hx = x_end
        g = ease_out_back((lt - T_walk) / 0.45, 1.4)
        gesture = Arm(lerp(A1_REST, 38, g), lerp(A2_REST, 80, g), "palm" if g > 0.35 else "fist", clamp01(g), 1.0)
        if lt > T_walk + 0.45:
            w = math.sin((lt - T_walk - 0.45) * 3.0)
            gesture = Arm(38 + 4 * w, 80 + 6 * w, "palm", 1.0)
        pose = Pose(arm=gesture, head_turn=0.0, tilt=14 * smooth((lt - 1.9) / 0.8))
    hy = WD.ground_y(hx) + 2

    def digits(c):
        f = font(FONT_BOLD, 54)
        for j, ch in enumerate(DIGITS):
            st = digit_state(j, lt)
            if st is None: continue
            kind, x, y, a, u = st
            if kind == "digit":
                fade_out = 1.0 - smooth((u - 1.0) / 0.25)
                sc = 0.5 + 0.5 * ease_out(u / 0.3)
                gp = paint("#E7A05C", a=120 * fade_out); gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 9))
                c.drawCircle(x, y - 18, 26 * sc, gp)
                c.save(); c.translate(x, y); c.scale(sc, sc)
                wdt = f.measureText(ch)
                c.drawString(ch, -wdt / 2, 0, f, paint("#E7A05C", a=255 * fade_out))
                c.restore()
                for s_ in range(3):                                     # spark trail
                    sy_ = y + 20 + 18 * s_ + 6 * math.sin(u * 20 + s_)
                    c.drawCircle(x + 6 * math.sin(u * 13 + s_ * 2), sy_, 3.2 - s_ * 0.8, paint("#F0A45E", a=200 * fade_out * (1 - s_ / 3)))
                if u > 1.0:
                    c.save(); c.translate(x, y - 16)
                    c.drawPath(WD.bird_path(math.sin(u * 14), 22 * smooth((u - 1.0) / 0.25)), paint(pal["bird"], a=255 * smooth((u - 1.0) / 0.25)))
                    c.restore()
            else:
                c.save(); c.translate(x, y - 16)
                c.drawPath(WD.bird_path(math.sin(u * 12 + j), 22), paint(pal["bird"]))
                c.restore()

    surf = FR.render_world(cam, lambda c: landscape(c, cam, pal, W, sun=sun, glow=0.9, lit=0.75, birds_w=W, leaves_w=W,
                                                    near=lambda cc: supa_set_dusk(cc, pal, W),
                                                    hero=hero_at(hx, hy, pose), after_hero=digits),
                           sunpath_front(cam, sun, W), water=dict(t=W, pal=pal))
    return surf


# ---------------------------------------------------------------- scene 4: rewind
SUN_MORNING = (560.0, 735.0, 185.0)


def sun_rewind(k):
    p0 = (SUN0[0], SUN0[1] + 30); p1 = (900.0, 470.0); p2 = SUN_MORNING[:2]
    x = (1 - k) ** 2 * p0[0] + 2 * (1 - k) * k * p1[0] + k * k * p2[0]
    y = (1 - k) ** 2 * p0[1] + 2 * (1 - k) * k * p1[1] + k * k * p2[1]
    return (x, y, lerp(SUN0[2], SUN_MORNING[2], k))


def streaks(c, lt, strength):
    if strength <= 0: return
    for j in range(14):
        sp = 2200 + 900 * hash01(j, 1)
        x = (hash01(j, 2) * 2400 + sp * lt) % 2600 - 700
        y = 120 + 1650 * hash01(j, 3)
        ln = 160 + 260 * hash01(j, 4)
        c.save(); c.translate(x, y); c.rotate(-3)
        g = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(ln, 0)], [col("#F4EDDF", 0), col("#F4EDDF", 150 * strength)])
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(0, -2.2, ln, 2.2), 2, 2), skia.Paint(Shader=g, AntiAlias=True))
        c.restore()


def s4(i):
    lt, D = local(i, 4)
    k = ease_io(lt / D)
    W = 7.0 - 3.2 * lt                       # time runs backwards
    pal = WD.palette(0.0)
    sun = sun_rewind(k)
    glow = lerp(0.9, 0.3, k)
    lit = lerp(0.75, 0.0, smooth(lt / (D * 0.7)))
    rot_ = -2.0 * math.sin(math.pi * clamp01(lt / D))
    cam = FR.Cam(zoom=1.0, cx=540, cy=1000, rot=rot_)
    hx = HX0 + 40 - 26 * lt                 # moon-walks backwards along the path
    pose = Pose(walk=-lt * 7.5, walk_amp=1.0)
    surf = FR.render_world(cam, lambda c: landscape(c, cam, pal, W, sun=sun, glow=glow, lit=lit, birds_w=W, leaves_w=W,
                                                    hero=hero_at(hx, WD.ground_y(hx) + 2, pose), sun_rot=2 * W),
                           sunpath_front(cam, sun, W, strength=lerp(1.0, 0.75, k)), water=dict(t=W, pal=pal))
    streaks(surf.getCanvas(), lt, smooth(lt / 0.2) * (1 - smooth((lt - D + 0.35) / 0.35)))
    return surf


# ---------------------------------------------------------------- scene 5: 1613 blooms inside the sun
def numerals_1613(c, sun, k):
    if k <= 0: return
    x, y, r = sun
    f = font(FONT_SERIF, 150)
    txt = "1613"
    wdt = f.measureText(txt)
    disk = circle(x, y, r)
    c.save(); c.clipPath(disk, doAntiAlias=True)
    blur = lerp(16, 1.4, ease_out(k))
    a = clamp01(k * 1.6)
    for dx, dy, colr, al, bl in ((0, 0, "#B4471E", 0.55, blur + 6), (0, 0, "#C4561F", 0.9, blur)):
        p = paint(colr, a=255 * a * al)
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, bl))
        sc = lerp(0.8, 1.0, ease_out(k))
        c.save(); c.translate(x, y + 52 * sc); c.scale(sc, sc)
        c.drawString(txt, -wdt / 2 + dx, dy, f, p)
        c.restore()
    # pooled darker rim of the watercolour stroke
    if k > 0.3:
        sc = lerp(0.8, 1.0, ease_out(k))
        p = paint("#9C3A16", a=110 * clamp01((k - 0.3) * 2), style="stroke", width=3.0)
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 1.6))
        c.save(); c.translate(x, y + 52 * sc); c.scale(sc, sc)
        c.drawString(txt, -wdt / 2, 0, f, p)
        c.restore()
    c.restore()


def s5(i):
    lt, D = local(i, 5)
    W = 3.0 + lt
    pal = WD.palette(0.0)
    sun = SUN_MORNING
    z = 1.0 + 0.1 * ease_io(lt / D)
    cam = FR.Cam(zoom=z, cx=sun[0], cy=sun[1] + 60)
    hx = 300.0
    pose = Pose(turn=0.0, tilt=17 * ease_io((lt - 0.25) / 0.7), sway=1.5 * math.sin(lt * 2))
    k = clamp01((lt - 0.2) / 1.2)

    def extra(c):
        numerals_1613(c, (sun[0] - cam.x * 0.03, sun[1], sun[2]), k)

    surf = FR.render_world(cam, lambda c: landscape(c, cam, pal, W, sun=sun, glow=0.3, lit=0.0, birds_w=W, leaves_w=W,
                                                    sky_extra=extra, hero=hero_at(hx, WD.BANK - 12, pose)),
                           sunpath_front(cam, sun, W, strength=0.7), water=dict(t=W, pal=pal))
    return surf


# ---------------------------------------------------------------- scene 6: front view, points at the viewer
def s6(i):
    lt, D = local(i, 6)
    W = 5.5 + lt
    pal = WD.palette(0.0)
    sun = SUN_MORNING
    u = ease_io(lt / D)
    g = ease_out_back(clamp01((lt - 0.1) / 0.4), 1.6)
    poke = max(0.0, math.sin(clamp01((lt - 0.45) / 1.5) * math.pi * 3)) if lt > 0.45 else 0.0
    cam = FR.Cam(x=45 * lt, zoom=1.0 + 0.045 * u + 0.012 * poke, cx=540, cy=1350)
    PT = Arm(14 + 3 * poke, 128, "pointat", 0.55 + 0.45 * poke, 0.42, 0.86)
    arm = REST.lerp(PT, g) if g < 1 else PT
    if g > 0.4 and arm.hand != "pointat":
        arm = Arm(arm.a1, arm.a2, "pointat", arm.open, arm.k, arm.k1)
    pose = Pose(turn=1.0, far_front=True, farm=Arm(4, 2), arm=arm, sway=2 * math.sin(lt * 2.2))

    def front(c):
        sunpath_front(cam, sun, W, 0.7)(c)
        c.drawRect(skia.Rect.MakeLTRB(-400, 1828, 1500, 2300), paint(pal["bank"]))
        c.drawRect(skia.Rect.MakeLTRB(-400, 1828, 1500, 1836), paint(mix(pal["bank"], pal["ground"], 0.6)))
        draw_hero(c, 540, 1842 + 2 * math.sin(lt * 2.2) * 0, 0.56, 1, pose)

    surf = FR.render_world(cam, lambda c: landscape(c, cam, pal, W, sun=sun, glow=0.3, lit=0.0, birds_w=W, leaves_w=W),
                           front, water=dict(t=W, pal=pal))
    return surf


# ---------------------------------------------------------------- scene 7: snap to night (re-hook)
def s7(i):
    lt, D = local(i, 7)
    W = 8.0 + lt
    n = smooth(lt / 0.3)
    pal = WD.palette(n)
    sun = (SUN_MORNING[0], SUN_MORNING[1] + 260 * n, SUN_MORNING[2])
    mk = ease_out(clamp01(lt / 1.1))
    moon = (MOON[0], lerp(980, MOON[1], mk), MOON[2], n)
    shake = (0.0, 0.0)
    if lt < 0.3:
        a = 3.0 * (1 - lt / 0.3)
        shake = (a * math.sin(lt * 95), a * math.cos(lt * 71))
    cam = FR.Cam(zoom=1.0 + 0.015 * lt / D, cx=540, cy=1000, shake=shake)
    lit = clamp01((lt - 0.12) / 0.45)
    pose = Pose(turn=0.0, tilt=12 * ease_io((lt - 0.2) / 0.6))
    surf = FR.render_world(cam, lambda c: landscape(c, cam, pal, W, sun=sun, sun_alpha=1 - n, glow=0.3 * (1 - n), lit=lit,
                                                    moon=moon, stars=n, birds_w=W, leaves_w=W,
                                                    hero=hero_at(HX0, HY0, pose)),
                           sunpath_front(cam, sun, W, strength=0.7 * (1 - n)), water=dict(t=W, pal=pal))
    return surf


# ---------------------------------------------------------------- night set: ENIAC + supa
def lamp_blink(t, base=0.35):
    def f(k, r, q):
        h1, h2 = hash01(k, r, q), hash01(k, r, q, 9)
        v = math.sin(t * (2.5 + 5 * h1) + h2 * 6.283)
        return clamp01((v - (1 - 2 * base)) * 3.0)
    return f


def night_set(c, pal, W, lamp_fn, supa_alphas=(1, 1, 1, 1, 1), extra=None, supa_scrolls=True):
    gy = NGY
    WD.draw_mulberry(c, pal, 6, SUPA_N - 90, WD.ground_y(SUPA_N - 90) + 5, 0.86, W)
    PR.draw_supa_back(c, pal, SUPA_N, gy)
    PR.draw_calculators(c, pal, SUPA_N, gy, W, supa_alphas, paper=mix("#E8E1D3", pal["city"], 0.45), scrolls=supa_scrolls)
    PR.draw_supa_front(c, pal, SUPA_N, gy)
    PR.draw_panels(c, PANEL_X0, PANEL_N, gy, lamp_fn)
    if extra: extra(c)


def night_landscape(c, cam, pal, W, near):
    landscape(c, cam, pal, W, moon=MOON, stars=1.0, lit=1.0, trees=(), ishkom=False, near=near)


def s8(i):
    lt, D = local(i, 8)
    W = 10.0 + lt
    pal = WD.palette(1.0)
    u = ease_io(lt / D)
    cam = FR.Cam(x=lerp(380, 760, u), zoom=1.1, cx=540, cy=1100)
    t = 20 + lt
    surf = FR.render_world(cam, lambda c: night_landscape(c, cam, pal, W, lambda cc: night_set(cc, pal, W, lamp_blink(t))),
                           None, water=dict(t=W, pal=pal))
    return surf


WOMEN_X = [PANEL_X0 + 70 + 118 * j for j in range(6)]


def plug_time(j): return 0.35 + 0.48 * j


def s9_lamps(lt, t):
    blink = lamp_blink(t, base=0.18)

    def f(k, r, q):
        v = blink(k, r, q) * 0.6
        for j in range(6):
            pt = plug_time(j)
            if lt >= pt and r == 1 + j:
                px = PR.panel_x(PANEL_X0, k) + 50
                d = abs(px - WOMEN_X[j]) / 900.0
                v = max(v, clamp01((lt - pt - d * 0.35) / 0.08))
        return v
    return f


def women_layer(lt, alpha=1.0):
    def f(c):
        for j, x in enumerate(WOMEN_X):
            pt = plug_time(j)
            reach = ease_io(clamp01((lt - (pt - 0.42)) / 0.42))
            if lt > pt + 0.25: reach = lerp(1.0, 0.82, ease_io((lt - pt - 0.25) / 0.4))
            colr = mix(PR.PEOPLE, "#6E8386", 0.35) if j % 2 == 0 else mix(PR.PEOPLE, "#6E8386", 0.2)
            hand = PR.woman(c, x, NGY + 4, reach=reach, colr=colr, alpha=alpha, h=226 + 10 * hash01(j, 4))
            # cable from the plugboard down to her hand
            sx_, sy_ = PR.panel_x(PANEL_X0, int((x - PANEL_X0) // (PR.PW + PR.PGAP)) + 1) + 20, NGY - PR.PH + 250
            cb = skia.Path(); cb.moveTo(sx_, sy_)
            cb.cubicTo(sx_ + 10, sy_ + 120, hand[0] + 10, hand[1] + 90, hand[0], hand[1])
            c.drawPath(cb, paint("#1A2428", a=255 * alpha, style="stroke", width=4, cap="round"))
            if pt <= lt < pt + 0.18:
                gp = paint("#E7A05C", a=200 * (1 - (lt - pt) / 0.18)); gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6))
                c.drawCircle(hand[0], hand[1], 10, gp)
    return f


def s9(i):
    lt, D = local(i, 9)
    W = 13.0 + lt
    pal = WD.palette(1.0)
    cam = FR.Cam(x=lerp(620, 700, ease_io(lt / D)), zoom=1.22, cx=540, cy=1080)
    t = 23 + lt
    lamps = s9_lamps(lt, t)
    surf = FR.render_world(cam, lambda c: night_landscape(c, cam, pal, W,
                                                          lambda cc: night_set(cc, pal, W, lamps, extra=women_layer(lt))),
                           None, water=dict(t=W, pal=pal))
    return surf


def all_lit(t, k0=1.0):
    def f(k, r, q):
        return clamp01(k0 * (0.86 + 0.14 * math.sin(t * 7 + k * 0.7 + r)))
    return f


def s10(i):
    lt, D = local(i, 10)
    W = 16.6 + lt
    pal = WD.palette(1.0)
    u = ease_io(lt / D)
    cam = FR.Cam(x=lerp(700, 80, u), zoom=lerp(1.22, 0.86, u), cx=540, cy=1100)
    t = 26 + lt
    alphas = [1 - smooth((lt - (0.08 + 0.15 * j)) / 0.16) for j in range(5)]
    flash = 1.0 + 0.6 * math.exp(-lt * 8)
    surf = FR.render_world(cam, lambda c: night_landscape(c, cam, pal, W, lambda cc: night_set(
        cc, pal, W, all_lit(t, flash), supa_alphas=alphas, extra=women_layer(9.0, alpha=1.0))), None, water=dict(t=W, pal=pal))
    return surf


# ---------------------------------------------------------------- scene 11: the word moves to the machine
WORD_TARGET = (PR.panel_x(PANEL_X0, 3) + 52, NGY - PR.PH + 122)


def word_state(lt):
    sx, sy = SUPA_N, NGY - 74 - 40
    if lt < 0.55:
        k = ease_out(lt / 0.55)
        return sx, lerp(sy, sy - 210, k), 0.6 + 0.4 * k, 0.0, k
    if lt < 1.55:
        k = ease_io((lt - 0.55) / 1.0)
        x0, y0 = sx, sy - 210
        x1, y1 = WORD_TARGET
        cx_, cy_ = (x0 + x1) / 2, min(y0, y1) - 230
        x = (1 - k) ** 2 * x0 + 2 * (1 - k) * k * cx_ + k * k * x1
        y = (1 - k) ** 2 * y0 + 2 * (1 - k) * k * cy_ + k * k * y1
        return x, y, 1.0 + 0.08 * math.sin(k * math.pi), 0.0, 1.0
    g = clamp01((lt - 1.55) / 0.5)
    bounce = 1.0 + 0.1 * math.sin(clamp01((lt - 1.55) / 0.25) * math.pi)
    return WORD_TARGET[0], WORD_TARGET[1], bounce, g, 1.0


def draw_word(c, lt):
    x, y, sc, g, a = word_state(lt)
    f = font(FONT_DISPLAY, 58)
    txt = "COMPUTER"
    wdt = f.measureText(txt)
    c.save(); c.translate(x, y); c.scale(sc, sc)
    if g > 0:
        gp = paint("#E1742F", a=210 * g); gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16))
        c.drawString(txt, -wdt / 2, 21, f, gp)
    if 0.5 < lt < 1.6:            # soft motion trail: a short blurred streak behind the word
        px, py, _, _, _ = word_state(lt - 0.12)
        tp = paint("#F4EDDF", a=70); tp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
        c.save(); c.translate((px - x) / sc * 0.6, (py - y) / sc * 0.6); c.drawString(txt, -wdt / 2, 21, f, tp); c.restore()
    c.drawString(txt, -wdt / 2, 21, f, paint(mix("#F4EDDF", "#E1742F", g), a=255 * a))
    c.restore()


def s11(i):
    lt, D = local(i, 11)
    W = 17.5 + lt
    pal = WD.palette(1.0)
    k = ease_io(clamp01(lt / 1.9))
    cam = FR.Cam(x=lerp(80, WORD_TARGET[0] - 540, k), zoom=lerp(0.86, 1.08, k), cx=540, cy=1100)
    t = 27 + lt
    surf = FR.render_world(cam, lambda c: night_landscape(c, cam, pal, W, lambda cc: night_set(
        cc, pal, W, all_lit(t), supa_alphas=(0, 0, 0, 0, 0), supa_scrolls=False,
        extra=lambda c3: (women_layer(9.0)(c3), draw_word(c3, lt)))), None, water=dict(t=W, pal=pal))
    return surf


# ---------------------------------------------------------------- scene 12: paper plane
THROW = Arm(98, 128, "palm", 0.8, 1.0, 1.0)


def plane_pos(lt, hand):
    t0 = 0.42
    if lt < t0: return hand[0], hand[1], -20, 1.0
    v = lt - t0
    x = hand[0] + 330 * v + 60 * v * v
    y = hand[1] - 210 * v + 22 * math.sin(v * 3.2) - 10 * v * v
    vx = 330 + 120 * v; vy = -210 + 70 * math.cos(v * 3.2) - 20 * v
    return x, y, math.degrees(math.atan2(vy, vx)), 1.0


def far_hand_world(hx, hy, arm, s=HS):
    sleeve, E, d1, n1, d2, n2 = arm_paths((SH_P[0] - 6, SH_P[1]), arm)
    hxr = E[0] + d2[0] * 263 * arm.k; hyr = E[1] + d2[1] * 263 * arm.k
    return hx + (hxr - ROOT[0]) * s, hy + (hyr - ROOT[1]) * s


def s12(i):
    lt, D = local(i, 12)
    W = (i - LAST) / FPS
    pal = WD.palette(0.0)
    sun = sun_dusk(W)
    k = ease_io(clamp01((lt - 0.4) / (D - 0.4)))
    cam = FR.Cam(x=200 * k, y=110 * k, zoom=1.0, cx=540, cy=1000)
    if lt < 0.42:
        farm = REST.lerp(THROW, ease_in(lt / 0.42) if lt > 0.12 else 0)
        farm = Arm(farm.a1, farm.a2, "fist" if lt < 0.3 else "palm", farm.open, farm.k, farm.k1)
        if lt < 0.12:
            farm = REST.lerp(Arm(-20, 30, "fist"), ease_io(lt / 0.12))
    else:
        farm = THROW.lerp(REST, ease_io((lt - 0.6) / 0.6)) if lt > 0.6 else THROW
    pose = Pose(turn=0.0, laptop=True, arm=HOLD, farm=farm, tilt=10 * ease_io((lt - 0.4) / 0.6))
    hand = far_hand_world(HX0, HY0, THROW)

    def plane(c):
        x, y, ang, a = plane_pos(lt, hand)
        if lt >= 0.42:
            tr = skia.Path(); first = True
            for q in range(0, 26):
                tt = lt - q * 0.05
                if tt < 0.42: break
                px, py, _, _ = plane_pos(tt, hand)
                if first: tr.moveTo(px, py); first = False
                else: tr.lineTo(px, py)
            c.drawPath(tr, paint("#F4EDDF", a=170, style="stroke", width=2.6, cap="round"))
        PR.paper_plane(c, x, y, 30 if lt >= 0.42 else 22, ang)

    surf = FR.render_world(cam, lambda c: landscape(c, cam, pal, W, sun=sun, glow=0.9, lit=0.75, birds_w=W, leaves_w=W,
                                                    hero=hero_at(HX0, HY0, pose), after_hero=plane),
                           sunpath_front(cam, sun, W), water=dict(t=W, pal=pal))
    return surf


# ---------------------------------------------------------------- scene 13: turn back to the frame-0 pose (loop)
TURN13 = 1.15


def pose13(i):
    lt, D = local(i, 13)
    n_turn = int(round(TURN13 * FPS))
    i0 = LAST - n_turn
    if i < i0:
        tilt = 10 * (1 - ease_io(lt / 0.8))
        return Pose(turn=0.0, laptop=True, arm=HOLD, farm=REST, tilt=tilt, head_turn=0.18 * math.sin(clamp01(lt / 1.2) * math.pi))
    u = ease_io((i - i0) / float(n_turn))
    return Pose(turn=0.5 * u, laptop=True, arm=HOLD, farm=REST.lerp(HALF, u))


def s13(i):
    W = (i - LAST) / FPS
    pal = WD.palette(0.0)
    sun = sun_dusk(W)
    cam = FR.Cam(zoom=1.0, cx=HX0, cy=1000)
    pose = pose13(i)
    surf = FR.render_world(cam, lambda c: landscape(c, cam, pal, W, sun=sun, glow=0.9, lit=0.75, birds_w=W, leaves_w=W,
                                                    hero=hero_at(HX0, HY0, pose)),
                           sunpath_front(cam, sun, W), water=dict(t=W, pal=pal))
    return surf


SCENE_FN = {1: s1, 2: s2, 3: s3, 4: s4, 5: s5, 6: s6, 7: s7, 8: s8, 9: s9, 10: s10, 11: s11, 12: s12, 13: s13}


def render_scene(i):
    return SCENE_FN[scene_at(i)](i)
