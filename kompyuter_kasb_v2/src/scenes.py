# The 13 scenes (v2: city street -> 1600s countryside -> 1940s hall -> city street). Morning palette throughout.
import json, math, os
import skia
from common import *
from style import P, Cam, sky, clouds, finish, rise
import env_city as EC
import env_country as EK
import env_1940 as E4
import icons
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


_FONT = {}


def font(path, size):
    key = (path, size)
    if key not in _FONT: _FONT[key] = skia.Font(skia.Typeface.MakeFromFile(path), size)
    return _FONT[key]


FONT_DISPLAY = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_BOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_SCRIPT = "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf"

# ---------------------------------------------------------------- hero
HS = 0.25
HX0, HY0 = 440.0, EC.HERO_Y
HALF = Arm(48, 150, "palm", 0.5, 0.62, 0.62)       # palm half raised (frame 0 / last frame)
STOP = Arm(62, 176, "palm", 1.0, 0.6, 0.45)
PRESENT = Arm(40, 116, "palm", 0.85, 0.72, 0.66)
HOLD_HAT = Arm(150, 255, "palm", 0.8, 0.6, 0.72)   # holding the doppi against the wind


def freeze_w(t):
    """scene 1: pedestrians, pigeons and clouds freeze 0.5-0.9 s"""
    if t < 0.5: return t
    if t < 0.9: return 0.5
    return t - 0.4


# ---------------------------------------------------------------- the present-day street (scenes 1, 12, 13)
W_LIFT12 = -3.85          # pigeons lift off when the paper plane is released (scene 12)


def pigeon_state(i, W):
    if W >= 0.15:
        return ("fly", W - 0.15)
    if W >= -0.9 or (W < W_LIFT12):
        return ("ground", 0.5 + 0.5 * math.sin(W * 7 + i * 1.3))
    if W < (SC_FRAME[13] - LAST - 0.5) / FPS:     # scene 12, after the release
        return ("fly", W - W_LIFT12)
    return ("fly", (-0.9 - W) * 1.4)        # scene 13: flying back in to land


def pedestrians(c, W):
    # woman with a handbag walking left on the near sidewalk; man with a briefcase far side; man entering from the left
    x1 = 900 - 75 * W
    EC.walker(c, x1, EC.NEAR_BACK + 22, 300, x1 / 34.0, P["l4"], "skirt", facing=-1)
    x2 = 120 + 55 * W
    EC.walker(c, x2, EC.SIDE_FAR[1] - 1, 150, x2 / 17.0, P["l3"], "coat")
    x3 = -60 + 85 * W
    if x3 > -80:
        EC.walker(c, x3, EC.NEAR_BACK + 30, 310, x3 / 36.0, P["l5"], "coat")


def street(c, cam, W, Wf=None, hero=None, after=None, rise_t=None, extra_far=None):
    """rise_t: seconds into the 'street rises back' transition (scene 12); None = fully built"""
    Wf = W if Wf is None else Wf
    def up(t0):
        return 0.0 if rise_t is None else (1 - rise(rise_t, t0)) * 900
    sky(c); clouds(c, Wf, cam)
    cam.begin(c, 0.15); EC.draw_modern_far(c, up(0.0)); c.restore()
    cam.begin(c, 0.3); EC.draw_blocks(c, "mid", P["l2"], up(0.08)); c.restore()
    cam.begin(c, 0.5); EC.draw_blocks(c, "near", P["l3"], up(0.16)); c.restore()
    if extra_far: extra_far(c)
    cam.begin(c, 1.0)
    EC.draw_ground(c, cam.x - 900, cam.x + 2000)
    c.save(); c.clipRect(skia.Rect.MakeLTRB(-3000, -3000, 5000, EC.NEAR_BACK + 6))
    c.translate(0, up(0.24))
    EC.street_tree(c, 70, W=W, seed=1); EC.modern_lamp(c, 250); EC.bus_stop(c, 690); EC.street_tree(c, 1070, W=W, seed=2)
    EC.modern_lamp(c, 1300)
    c.restore()
    if rise_t is None or rise_t > 0.7:
        pedestrians(c, Wf)
    if hero: hero(c)
    EC.draw_pigeons(c, pigeon_state, Wf)
    if after: after(c)
    EC.draw_planters(c, cam.x - 900, cam.x + 2000, W=W)
    c.restore()


def new_surface():
    s = skia.Surface(W, H); s.getCanvas().clear(col(P["sky_bot"])); return s


def hero_at(x, y, pose, s=HS, facing=1):
    return lambda c: draw_hero(c, x, y, s, facing, pose)


def s1(i):
    t = i / FPS
    lt, D = local(i, 1)
    Wf = freeze_w(t)
    cam = Cam(zoom=1.0 + 0.03 * smooth(lt / D), cx=HX0, cy=1100)
    u = ease_out(t / 0.5)
    turn = lerp(0.5, 0.72, u)
    farm = HALF.lerp(STOP, u)
    if t > 1.45:
        v = ease_io((t - 1.45) / 0.55)
        farm = STOP.lerp(PRESENT, v); turn = lerp(0.72, 0.62, v)
        if t > 2.0:
            w = math.sin((t - 2.0) * 3.2)
            farm = Arm(PRESENT.a1 + 3 * w, PRESENT.a2 + 7 * w, "palm", PRESENT.open, PRESENT.k, PRESENT.k1)
    pose = Pose(turn=turn, laptop=True, arm=HOLD, farm=farm)
    surf = new_surface()
    street(surf.getCanvas(), cam, t, Wf, hero=hero_at(HX0, HY0, pose))
    return finish(surf, cam)


# ---------------------------------------------------------------- scene 2: the street sinks into the past
def s2(i):
    lt, D = local(i, 2)
    W = 4.0 + lt
    y = -45 * math.sin(math.pi * clamp01(lt / 1.1)) + 28 * math.sin(math.pi * clamp01((lt - 1.0) / 1.3))
    cam = Cam(y=y, cx=HX0, cy=1100)
    sink = lambda t0: rise(lt, t0) * 900                       # modern layers go down
    up = lambda t0: (1 - rise(lt, t0)) * 900                   # old layers come up
    surf = new_surface(); c = surf.getCanvas()
    sky(c); clouds(c, W, cam)
    cam.begin(c, 0.15); EC.draw_modern_far(c, sink(0.05)); EC.draw_old_far(c, up(0.3)); c.restore()
    cam.begin(c, 0.3); EC.draw_blocks(c, "mid", P["l2"], sink(0.15)); EC.draw_old_offices(c, "mid", P["l2"], up(0.4)); c.restore()
    cam.begin(c, 0.5); EC.draw_blocks(c, "near", P["l3"], sink(0.25)); EC.draw_old_offices(c, "near", P["l3"], up(0.5)); c.restore()
    cam.begin(c, 1.0)
    EC.draw_ground(c, -900, 2000, dash_dy=sink(0.3) * 0.3, cobble=rise(lt, 0.6))
    c.save(); c.clipRect(skia.Rect.MakeLTRB(-3000, -3000, 5000, EC.NEAR_BACK + 6))
    c.save(); c.translate(0, sink(0.0))
    EC.street_tree(c, 70, W=W, seed=1); EC.modern_lamp(c, 250); EC.bus_stop(c, 690); EC.street_tree(c, 1070, W=W, seed=2)
    c.restore()
    c.save(); c.translate(0, up(0.6)); EC.iron_lamp(c, 180); EC.iron_lamp(c, 860); c.restore()
    c.restore()
    if lt > 1.0:                                              # an early-20th-century passer-by
        x = 1150 - 95 * (lt - 1.0) * 1.8
        EC.walker(c, x, EC.NEAR_BACK + 24, 305, x / 34.0, P["l4"], "hat", facing=-1)
    pose = Pose(turn=0.0, head_turn=0.08 * math.sin(lt * 2.5), tilt=10 * math.sin(math.pi * clamp01(lt / D)), sway=2 * math.sin(lt * 2))
    draw_hero(c, HX0, HY0, HS, 1, pose)
    c.save(); c.translate(0, sink(0.1) * 0.25); EC.draw_planters(c, -900, 2000, W=W, era=0); c.restore()
    if lt > 0.6:
        c.save(); c.translate(0, up(0.8) * 0.25); EC.draw_planters(c, -900, 2000, W=W, era=1); c.restore()
    c.restore()
    return finish(surf, cam)


# ---------------------------------------------------------------- scene 3: the office facade of human computers
def sheet_state(j, lt):
    rc = EC.window_rects()[2][2]
    t0 = 0.4 + 0.42 * j
    u = lt - t0
    if u < 0: return None
    x0, y0 = rc.right() - 20, rc.top() + 60 + 20 * hash01(j, 1)
    x = x0 + (60 + 50 * hash01(j, 2)) * u * (1 if j % 3 else -1.6) + 30 * math.sin(u * 2.4 + j)
    y = y0 + 55 * u + 40 * u * u - 30 * math.sin(u * 1.8)
    return x, y, u * 140 * (hash01(j, 3) - 0.5) + 20 * math.sin(u * 3 + j), clamp01(u / 0.2)


def s3(i):
    lt, D = local(i, 3)
    W = 6.4 + lt
    cam = Cam(zoom=1.0 + 0.12 * ease_io(lt / D), cx=540, cy=1010)
    surf = new_surface(); c = surf.getCanvas()
    sky(c); clouds(c, W, cam)
    cam.begin(c, 0.15); EC.draw_old_far(c, 0); c.restore()
    cam.begin(c, 1.0)
    EC.draw_facade(c, W, open_k=1.0)
    g = EC.FACADE[3]
    c.drawRect(skia.Rect.MakeLTRB(-900, g, 2000, g + 12), paint(P["l4"]))
    c.drawRect(skia.Rect.MakeLTRB(-900, g + 12, 2000, 2600), paint(P["l2"]))
    for yy in (1720, 1800, 1890):
        c.drawRect(skia.Rect.MakeLTRB(-900, yy, 2000, yy + 3), paint(mix(P["l2"], P["l3"], 0.35)))
    EC.iron_lamp(c, 980, base=g + 6, s=1.05)
    gk = ease_out_back(clamp01((lt - 0.35) / 0.5), 1.4)
    arm = Arm(lerp(A1_REST, 52, gk), lerp(A2_REST, 118, gk), "palm" if gk > 0.3 else "fist", clamp01(gk), 1.0)
    if lt > 0.85:
        w = math.sin((lt - 0.85) * 2.6)
        arm = Arm(52 + 4 * w, 118 + 7 * w, "palm", 1.0)
    draw_hero(c, 175, 1888, 0.24, 1, Pose(arm=arm, tilt=12 * smooth((lt - 0.4) / 0.6), sway=1.5 * math.sin(lt * 2)))
    for j in range(7):
        st = sheet_state(j, lt)
        if st: EC.sheet(c, st[0], st[1], st[2], 1.0, st[3])
    c.restore()
    return finish(surf, cam)


# ---------------------------------------------------------------- scenes 4-7: the 1600s countryside and the giant book
def country(c, cam, t, sink=(0, 0, 0, 0), book=None, hero=None, wind=1.0, after=None, grass_sink=0.0, blur=0.0):
    if blur > 0:
        c.saveLayer(None, skia.Paint(ImageFilter=skia.ImageFilters.Blur(blur, blur)))
    sky(c); clouds(c, t, cam)
    EK.draw_layers(c, cam, t, sink)
    cam.begin(c, 1.0)
    EK.draw_hill(c, sink[3]); EK.hill_grass(c, t, wind, sink[3])
    if book:
        c.save(); c.translate(0, sink[3]); book(c); c.restore()
    if blur > 0:
        c.restore(); c.restore(); c.saveLayer(None); cam.begin(c, 1.0)
    if hero: hero(c)
    if after: after(c)
    EK.grass(c, t, wind=wind, sink=grass_sink)
    c.restore()
    if blur > 0: c.restore()


def s4(i):
    lt, D = local(i, 4)
    W = 9.9 + lt
    cam = Cam(zoom=1.0 + 0.06 * ease_io(clamp01((lt - 0.8) / (D - 0.8))), cx=EK.BOOK_CX, cy=1050)
    surf = new_surface(); c = surf.getCanvas()
    fold = lambda t0: ease_in(clamp01((lt - t0) / 0.5))          # old offices fold down flat
    up = lambda t0: (1 - rise(lt, t0)) * 1000
    sky(c); clouds(c, W, cam)
    # 1. the early-20th-century street folds down
    if lt < 0.9:
        for f, key, colr, t0 in ((0.15, "far", P["l1"], 0.0), (0.3, "mid", P["l2"], 0.08), (0.5, "near", P["l3"], 0.16)):
            k = fold(t0)
            if k >= 1: continue
            cam.begin(c, f); c.translate(0, EC.HORIZON + 60); c.scale(1, 1 - k); c.translate(0, -(EC.HORIZON + 60))
            if key == "far": EC.draw_old_far(c)
            else: EC.draw_old_offices(c, key, colr)
            c.restore()
    # 2. the countryside rises, each layer at its own speed
    sink = (up(0.3), up(0.38), up(0.46), up(0.55))
    gone = fold(0.3)
    EK.draw_layers(c, cam, W, sink)
    cam.begin(c, 1.0)
    if gone < 1:
        c.save(); c.translate(0, gone * 700)
        EC.draw_ground(c, -900, 2000, cobble=1.0)
        c.save(); c.clipRect(skia.Rect.MakeLTRB(-3000, -3000, 5000, EC.NEAR_BACK + 6))
        c.translate(0, fold(0.05) * 600); EC.iron_lamp(c, 180); EC.iron_lamp(c, 860)
        c.restore(); c.restore()
    EK.draw_hill(c, sink[3]); EK.hill_grass(c, W, 1.0, sink[3])
    c.save(); c.translate(0, sink[3]); EK.draw_book(c, W, flip_rate=3.4 * rise(lt, 0.9, 0.3), flip_phase=lt); c.restore()
    wind = rise(lt, 0.8, 0.4)
    arm = REST.lerp(HOLD_HAT, ease_io(clamp01((lt - 0.75) / 0.35)))
    draw_hero(c, HX0, HY0, HS, 1, Pose(arm=arm, sway=-10 * wind + 3 * math.sin(lt * 9) * wind, tilt=-4 * wind))
    EK.grass(c, W, wind=0.2 + wind, sink=up(0.8) * 0.4)
    c.restore()
    return finish(surf, cam)


WORD = "computer"


def writing_fn(k):
    """the word writes itself letter by letter on the right page (italic wipe)"""
    f = font(FONT_SCRIPT, 96)

    def wr(c, spine, edge, base, hp):
        if k <= 0: return
        widths = f.getWidths(f.textToGlyphs(WORD))
        tot = sum(widths)
        x0 = spine + (edge - spine - tot) / 2
        y0 = base - hp * 0.5 + 30
        n = len(WORD)
        acc = 0.0
        for j, ch in enumerate(WORD):
            lk = clamp01(k * n - j)
            if lk <= 0: break
            c.save()
            cx0 = x0 + acc
            clip = skia.Path()
            wx = cx0 - 10 + (widths[j] + 22) * lk
            clip.addPoly([skia.Point(cx0 - 30, y0 - 90), skia.Point(wx + 18, y0 - 90), skia.Point(wx - 14, y0 + 40), skia.Point(cx0 - 30, y0 + 40)], True)
            c.clipPath(clip, doAntiAlias=True)
            c.drawString(ch, cx0, y0, f, paint(P["l5"]))
            c.restore()
            acc += widths[j]
        # a thin ink flourish under the word once written
        if k > 0.98:
            fl = skia.Path(); fl.moveTo(x0, y0 + 22); fl.cubicTo(x0 + tot * 0.3, y0 + 34, x0 + tot * 0.7, y0 + 10, x0 + tot + 10, y0 + 24)
            c.drawPath(fl, paint(P["l5"], style="stroke", width=2.5, cap="round"))
    return wr


def write_k(lt):
    return clamp01((lt - 0.4) / 1.5)


def s5(i):
    lt, D = local(i, 5)
    W = 12.3 + lt
    k = ease_io(lt / D)
    fx, fy = lerp(560, 640, k), lerp(1160, EK.BOOK_BASE - EK.BOOK_HP * 0.5, k)   # tilt from the hero up to the word
    cam = Cam(x=fx - 540, y=960 - fy, zoom=1.42, cx=540, cy=960)
    surf = new_surface(); c = surf.getCanvas()
    slow = 1 - smooth(lt / 0.45)
    phase = 0.45 * 3.4 * (1 - (1 - min(lt, 0.45) / 0.45) ** 2) / 2
    book = lambda cc: EK.draw_book(cc, W, flip_rate=3.4 * slow, flip_phase=phase, writing=writing_fn(write_k(lt)))
    hero = hero_at(HX0, HY0, Pose(arm=HOLD_HAT.lerp(REST, ease_io(lt / 0.5)), tilt=20 * ease_io((lt - 0.2) / 0.7),
                                  sway=-5 + 2 * math.sin(lt * 5)))
    country(c, cam, W, book=book, hero=hero, wind=0.6)
    return finish(surf, cam)


def s6(i):
    lt, D = local(i, 6)
    W = 14.7 + lt
    cam = Cam(zoom=1.0 + 0.04 * ease_io(lt / D), cx=540, cy=1000)
    g = ease_out_back(clamp01((lt - 0.1) / 0.4), 1.6)
    poke = max(0.0, math.sin(clamp01((lt - 0.45) / 1.5) * math.pi * 3)) if lt > 0.45 else 0.0
    cam.zoom += 0.012 * poke
    PT = Arm(14 + 3 * poke, 128, "pointat", 0.55 + 0.45 * poke, 0.42, 0.86)
    arm = REST.lerp(PT, g) if g < 1 else PT
    if g > 0.4: arm = Arm(arm.a1, arm.a2, "pointat", arm.open, arm.k, arm.k1)
    pose = Pose(turn=1.0, far_front=True, farm=Arm(4, 2), arm=arm, sway=2 * math.sin(lt * 2.2))
    surf = new_surface(); c = surf.getCanvas()
    lift = 0.5 + 0.5 * math.sin(lt * 2.6)
    bcam = Cam(x=-60, y=-80, zoom=1.25, cx=540, cy=1000)
    c.saveLayer(None, skia.Paint(ImageFilter=skia.ImageFilters.Blur(9, 9)))
    sky(c); clouds(c, W, bcam)
    EK.draw_layers(c, bcam, W)
    bcam.begin(c, 1.0); EK.draw_hill(c); EK.draw_book(c, W, lift_one=lift); c.restore()
    c.restore()
    cam.begin(c, 1.0)
    draw_hero(c, 540, 610 + 1451 * 1.45, 1.45, 1, pose)
    c.restore()
    return finish(surf, cam)


def s7(i):
    lt, D = local(i, 7)
    W = 17.0 + lt
    T_SLAM = 0.22
    shake = (0.0, 0.0)
    if T_SLAM <= lt < T_SLAM + 0.3:
        a = 3.0 * (1 - (lt - T_SLAM) / 0.3)
        shake = (a * math.sin(lt * 95), a * math.cos(lt * 71))
    dark = 0.16 if T_SLAM <= lt < T_SLAM + 0.2 else 0.0
    cam = Cam(zoom=1.0, cx=540, cy=1000, shake=shake, dark=dark)
    surf = new_surface(); c = surf.getCanvas()
    close = clamp01(lt / T_SLAM)
    book = lambda cc: EK.draw_book(cc, W, close=close if close < 1 else 1.0)
    hero = hero_at(HX0, HY0, Pose(arm=HOLD_HAT, sway=-12, tilt=8 * ease_io(lt / 0.6)))
    country(c, cam, W, book=book, hero=hero, wind=1.6, after=lambda cc: EK.loose_pages(cc, lt - T_SLAM + 0.02))
    return finish(surf, cam)


# ---------------------------------------------------------------- scenes 8-11: the 1940s hall
def s8_cam(lt):
    k = ease_io(clamp01((lt - 0.95) / 1.15))
    return E4.Cam3(x=lerp(-5.15, -2.6, k), h=lerp(9.0, 2.5, k), z=lerp(8.0 + 0.5 * lt, 1.0, k), pitch=lerp(-70, -6, k),
                   cy=lerp(960, 1000, k))


def s8(i):
    lt, D = local(i, 8)
    t = 18.3 + lt
    surf = new_surface(); c = surf.getCanvas()
    cam = s8_cam(lt)
    on = clamp01((lt - 1.4) / 0.4)
    blink = E4.lamp_default(t)
    E4.draw_hall(c, cam, t, lamp_fn=lambda k, r, q: blink(k, r, q) * on)
    return finish(surf, Cam())


WOMEN = [(0, 7, -7.6), (1, 7, -5.0), (2, 7, -2.4), (3, 7, 0.2), (1, 6, 2.8), (2, 6, 5.4)]   # (row, desk, panel x)


def woman_path(j, lt):
    ri, zi, tx = WOMEN[j]
    sx, sz = E4.DESK_ROWS_X[ri] + 0.4, E4.DESK_Z[zi] + 0.5
    tz = E4.WALL_Z - 0.6
    t0 = 0.15 + 0.12 * j
    dist = math.hypot(tx - sx, tz - sz)
    T = dist / 3.2
    u = clamp01((lt - t0) / T)
    x, z = lerp(sx, tx, u), lerp(sz, tz, u)
    return x, z, t0, T, (lt - t0) * 3.2 / 0.7 * math.pi if 0 < u < 1 else 0.0, u


def plug_time(j):
    x, z, t0, T, ph, u = woman_path(j, 0)
    return t0 + T + 0.25


def s9_walkers(lt):
    out = []
    for j in range(6):
        x, z, t0, T, ph, u = woman_path(j, lt)
        if lt < t0: continue
        pt = plug_time(j)
        reach = ease_io(clamp01((lt - (pt - 0.3)) / 0.3)) if lt > pt - 0.3 else 0.0
        if lt > pt + 0.3: reach = lerp(1.0, 0.75, ease_io((lt - pt - 0.3) / 0.4))
        colr = mix(E4.WOMAN, P["l5"], 0.25 * (j % 2))

        def drw(cc, ph=ph, reach=reach, colr=colr, pt=pt, lt=lt):
            hd = E4.walking_back(cc, colr, ph, reach)
            if lt >= pt - 0.05:                      # cable from her hand down to the plugboard
                cb = skia.Path(); cb.moveTo(hd[0], hd[1]); cb.cubicTo(hd[0] + 30, hd[1] + 40, hd[0] + 40, -60, hd[0] + 70, -40)
                cc.drawPath(cb, paint(P["l5"], style="stroke", width=4, cap="round"))
            if pt <= lt < pt + 0.2:
                gp = paint(P["lamp"], a=220 * (1 - (lt - pt) / 0.2)); gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8))
                cc.drawCircle(hd[0], hd[1], 12, gp)
        out.append((x, z, drw))
    return out


def s9_lamps(lt, t):
    blink = E4.lamp_default(t)

    def f(k, r, q):
        v = blink(k, r, q) * 0.42                   # the other rows dim slightly
        for j in range(6):
            pt = plug_time(j)
            if lt >= pt and r == 1 + j:
                v = max(v, clamp01((lt - pt) / 0.12))
        return v
    return f


def gone_desks(lt):
    """seats the six programmers left"""
    left = {(ri, zi): woman_path(j, lt)[2] for j, (ri, zi, tx) in enumerate(WOMEN)}
    return lambda ri, zi: (1.0 - clamp01((lt - left[(ri, zi)]) / 0.15)) if (ri, zi) in left else 1.0


def s9(i):
    lt, D = local(i, 9)
    t = 21.0 + lt
    surf = new_surface(); c = surf.getCanvas()
    cam = E4.Cam3(x=lerp(-3.0, 1.0, ease_io(lt / D)), h=2.1, z=20.5, pitch=-8, cy=900)
    E4.draw_hall(c, cam, t, lamp_fn=s9_lamps(lt, t), desk_alpha=gone_desks(lt), walkers=s9_walkers(lt))
    return finish(surf, Cam())


def standing_women(lt_after):
    return s9_walkers(9.0)


HERO_HALL = (2.0, 16.0)


def hero_billboard(cam, c, facing=-1):
    def fn():
        q = cam.proj(HERO_HALL[0], 0.0, HERO_HALL[1])
        if q is None: return
        s = E4.F / q[2] * 1.75 / 1451.0
        draw_hero(c, q[0], q[1], s, facing, Pose(turn=0.0, tilt=6, sway=1.5 * math.sin(q[2])))
    q = cam.proj(HERO_HALL[0], 0.0, HERO_HALL[1])
    return [(q[2] - 0.3, fn)] if q else []


def s10_cam(lt, D):
    u = ease_io(lt / D)
    return E4.Cam3(x=lerp(1.0, -4.0, u), h=lerp(2.1, 4.5, u), z=lerp(20.5, 2.0, u), pitch=lerp(-8, -14, u), cy=900)


def s10(i):
    lt, D = local(i, 10)
    t = 24.6 + lt
    surf = new_surface(); c = surf.getCanvas()
    cam = s10_cam(lt, D)
    left = gone_desks(9.0)
    order = sorted([(ri, zi) for ri in range(4) for zi in range(8)], key=lambda p: (-p[1], p[0]))
    fade_t = {p: 0.05 + 0.75 * n / len(order) for n, p in enumerate(order)}
    alpha = lambda ri, zi: min(left(ri, zi), 1.0 - clamp01((lt - fade_t[(ri, zi)]) / 0.12))
    flash = 1.0 + 0.5 * math.exp(-lt * 7)
    lamps = lambda k, r, q: clamp01(flash * (0.88 + 0.12 * math.sin(t * 7 + k + r)))
    E4.draw_hall(c, cam, t, lamp_fn=lamps, desk_alpha=alpha, walkers=standing_women(lt), extra3d=hero_billboard(cam, c))
    return finish(surf, Cam())


WORD_START = (-1.7, 1.0, 12.0)
WORD_END = (0.6, 2.55, E4.WALL_Z - 0.06)


def word_pos(lt):
    if lt < 0.5:
        k = ease_out(lt / 0.5)
        return (WORD_START[0], lerp(WORD_START[1], 3.4, k), WORD_START[2]), 0.0
    if lt < 1.55:
        k = ease_io((lt - 0.5) / 1.05)
        p0 = (WORD_START[0], 3.4, WORD_START[2]); p2 = WORD_END
        p1 = ((p0[0] + p2[0]) / 2, 5.2, (p0[2] + p2[2]) / 2)
        return tuple((1 - k) ** 2 * a + 2 * (1 - k) * k * b + k * k * cc for a, b, cc in zip(p0, p1, p2)), 0.0
    return WORD_END, clamp01((lt - 1.55) / 0.5)


def s11(i):
    lt, D = local(i, 11)
    t = 25.5 + lt
    surf = new_surface(); c = surf.getCanvas()
    k = ease_io(clamp01(lt / 1.9))
    cam = E4.Cam3(x=lerp(-4.0, 0.6, k), h=lerp(4.5, 2.4, k), z=lerp(2.0, 24.5, k), pitch=lerp(-14, -2, k), cy=lerp(900, 960, k))
    lamps = lambda kk, r, q: 0.88 + 0.12 * math.sin(t * 7 + kk + r)
    p, g = word_pos(lt)

    def word(cc):
        q = cam.proj(*p)
        if q is None: return
        sz = E4.F / q[2] * 0.62
        f = font(FONT_DISPLAY, max(8, int(sz)))
        wdt = f.measureText("COMPUTER")
        bounce = 1.0 + 0.1 * math.sin(clamp01((lt - 1.55) / 0.25) * math.pi) if lt > 1.55 else 1.0
        cc.save(); cc.translate(q[0], q[1]); cc.scale(bounce, bounce)
        if g > 0:
            gp = paint(P["accent"], a=210 * g); gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, sz * 0.25))
            cc.drawString("COMPUTER", -wdt / 2, sz * 0.36, f, gp)
        if 0.5 < lt < 1.6:
            q2 = cam.proj(*word_pos(lt - 0.1)[0])
            if q2:
                tp = paint(P["cream"], a=70); tp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 9))
                cc.drawString("COMPUTER", -wdt / 2 + (q2[0] - q[0]) * 0.6, sz * 0.36 + (q2[1] - q[1]) * 0.6, f, tp)
        hp = paint(P["l5"], a=110 * (1 - g)); hp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, max(2.0, sz * 0.12)))
        cc.drawString("COMPUTER", -wdt / 2, sz * 0.36, f, hp)
        cc.drawString("COMPUTER", -wdt / 2, sz * 0.36, f, paint(mix(P["cream"], P["accent"], g)))
        cc.restore()
    q = cam.proj(*p)
    extra = [((q[2] - 0.5) if q else 0, lambda: word(c))] + hero_billboard(cam, c)
    E4.draw_hall(c, cam, t, lamp_fn=lamps, desk_alpha=lambda ri, zi: 0.0, walkers=standing_women(lt), extra3d=extra)
    return finish(surf, Cam())


# ---------------------------------------------------------------- scene 12: back to the present, the paper plane
THROW = Arm(98, 128, "palm", 0.8, 1.0, 1.0)
T_REL = 0.85


def far_hand_world(hx, hy, arm, s=HS):
    sleeve, E, d1, n1, d2, n2 = arm_paths((SH_P[0] - 6, SH_P[1]), arm)
    return hx + (E[0] + d2[0] * 263 * arm.k - ROOT[0]) * s, hy + (E[1] + d2[1] * 263 * arm.k - ROOT[1]) * s


def plane_pos(lt, hand):
    if lt < T_REL: return hand[0], hand[1], -20
    v = lt - T_REL
    x = hand[0] + 330 * v + 70 * v * v
    y = hand[1] - 230 * v + 26 * math.sin(v * 3.4) - 20 * v * v
    vx = 330 + 140 * v; vy = -230 + 88 * math.cos(v * 3.4) - 40 * v
    return x, y, math.degrees(math.atan2(vy, vx))


def s12(i):
    lt, D = local(i, 12)
    W = (i - LAST) / FPS
    k = ease_io(clamp01((lt - T_REL) / (D - T_REL)))
    cam = Cam(x=230 * k, y=260 * k, zoom=1.0 + 0.05 * k, cx=540, cy=1100)
    a, b = T_REL - 0.35, T_REL
    if lt < a:
        farm = REST
    elif lt < b:
        farm = REST.lerp(THROW, ease_in((lt - a) / (b - a)))
        farm = Arm(farm.a1, farm.a2, "fist" if lt < b - 0.08 else "palm", farm.open, farm.k, farm.k1)
    else:
        farm = THROW.lerp(REST, ease_io((lt - b - 0.2) / 0.6)) if lt > b + 0.2 else THROW
    pose = Pose(turn=0.0, laptop=True, arm=HOLD, farm=farm, tilt=12 * ease_io((lt - T_REL) / 0.6))
    hand = far_hand_world(HX0, HY0, THROW)

    def plane(c):
        x, y, ang = plane_pos(lt, hand)
        if lt >= a:
            if lt >= T_REL:
                tr = skia.Path(); first = True
                for q in range(0, 30):
                    tt = lt - q * 0.04
                    if tt < T_REL: break
                    px, py, _ = plane_pos(tt, hand)
                    if first: tr.moveTo(px, py); first = False
                    else: tr.lineTo(px, py)
                c.drawPath(tr, paint(P["cream"], a=190, style="stroke", width=2.6, cap="round"))
            else:
                hx, hy = far_hand_world(HX0, HY0, farm)
                x, y = hx, hy
            icons.paper_plane(c, x, y, 30 if lt >= T_REL else 22, ang)

    surf = new_surface()
    street(surf.getCanvas(), cam, W, hero=hero_at(HX0, HY0, pose), after=plane, rise_t=lt)
    return finish(surf, cam)


# ---------------------------------------------------------------- scene 13: turn back to the frame-0 pose (loop)
TURN13 = 1.15


def pose13(i):
    lt, D = local(i, 13)
    n_turn = int(round(TURN13 * FPS))
    i0 = LAST - n_turn
    if i < i0:
        return Pose(turn=0.0, laptop=True, arm=HOLD, farm=REST, tilt=12 * (1 - ease_io(lt / 0.8)),
                    head_turn=0.18 * math.sin(clamp01(lt / 1.2) * math.pi))
    u = ease_io((i - i0) / float(n_turn))
    return Pose(turn=0.5 * u, laptop=True, arm=HOLD, farm=REST.lerp(HALF, u))


def s13(i):
    W = (i - LAST) / FPS
    cam = Cam(zoom=1.0, cx=HX0, cy=1100)
    surf = new_surface()
    street(surf.getCanvas(), cam, W, hero=hero_at(HX0, HY0, pose13(i)))
    return finish(surf, cam)


SCENE_FN = {1: s1, 2: s2, 3: s3, 4: s4, 5: s5, 6: s6, 7: s7, 8: s8, 9: s9, 10: s10, 11: s11, 12: s12, 13: s13}


def render_scene(i):
    return SCENE_FN[scene_at(i)](i)
