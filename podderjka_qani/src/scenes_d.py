# Scenes 15 (desert road), 16 (BACHKANA! freeze), 17 (cotton field antics), 18 (tractors, laughing), 19 (haystack, notes).
import math, random
import numpy as np
from PIL import Image
from base import *
from script_data import SCENES
import overlay as OV
from scenes_b import note_rect

C = CHOL; K = KUNDUZ

# ================================================================ scene 15: desert road, tracking shot
V15 = 255.0
D15 = (SCENES[14]["f1"] - SCENES[14]["f0"]) / FPS

def dunes(cv, base, amp, col, seed, wl=(900, 420)):
    rnd = random.Random(seed); ph = [rnd.uniform(0, 6.28) for _ in wl]
    pts = []
    for x in range(-1600, 4200, 30):
        v = 0
        for L, p in zip(wl, ph):
            s_ = math.sin(2 * math.pi * x / L + p)
            v += (s_ if s_ > 0 else s_ * 0.55) / len(wl)
        pts.append((x, base - amp * (0.5 + 0.5 * v)))
    cv.poly(pts + [(4200, 3200), (-1600, 3200)], col)

def desert_world(cv, te, hero_fn=None, frozen=False):
    X = 300 + V15 * te
    cv.set_cam(X + 140, 960, 1.0)
    cv.layer(1.0); sky(cv, C["sky0"], C["sky1"], 0, 1100)
    cv.layer(0.03); draw_sun(cv, 300 + V15 * D15 * 0.03 + 560, 360, 110, C["sun0"], C["sun1"])
    cv.layer(0.1); dunes(cv, 1010, 150, C["L1"], 3, wl=(1300, 600))
    cv.layer(0.25); dunes(cv, 1075, 100, C["L2"], 5, wl=(1000, 450))
    # caravan of camels far away
    cv.layer(0.45)
    dunes(cv, 1150, 60, C["L3"], 8, wl=(900, 380))
    for i in range(3):
        cx = 1500 - 40 * te - i * 150
        camel(cv, cx, 1132, 0.55, C["L4"], te, dir=-1, phase=2 * math.pi * 0.9 * te + i * 1.3)
    cv.layer(0.7)
    cv.rect(-1600, 1195, 4200, 3200, C["L3"])
    for sx_ in range(-600, 3800, 520):
        saxaul(cv, sx_, 1200, 0.75, C["L4"], te + sx_)
    # road
    cv.layer(1.0)
    G = 1285.0
    cv.rect(-1600, 1236, 5200, 3200, lerpc(C["L3"], C["L4"], 0.3))
    cv.rect(-1600, 1240, 5200, 1318, C["L4"])
    for dx in range(-1600, 5200, 120):
        cv.rect(dx, 1276, dx + 60, 1282, C["L2"])
    # road sign QORAQALPOG‘ISTON (passes by)
    sxw = 1150
    for px in (sxw - 150, sxw + 150):
        cv.rect(px - 7, 960, px + 7, 1240, C["L5"])
    panel = hx("4F5B4B")
    cv.rect(sxw - 230, 870, sxw + 230, 1010, C["L5"], r=10)
    cv.rect(sxw - 222, 878, sxw + 222, 1002, panel, r=8)
    cv.rect(sxw - 212, 888, sxw + 212, 992, lerpc(panel, CREAM_N, 0.12), r=6)
    cv.rect(sxw - 206, 894, sxw + 206, 986, panel, r=5)
    wtext(cv, "QORAQALPOG‘ISTON", sxw - 6, 924, 40, ACCENT, FONT_BLACK, maxw=380)
    cv.poly([(sxw + 40, 954), (sxw + 150, 954), (sxw + 150, 944), (sxw + 182, 962), (sxw + 150, 980), (sxw + 150, 970), (sxw + 40, 970)], ACCENT)
    if hero_fn: hero_fn(cv, X, G)
    # fast foreground sand with stones
    cv.layer(1.45)
    rnd = random.Random(15)
    cv.rect(-2000, 1640, 6000, 3200, C["L4"])
    for i in range(40):
        x = -1200 + i * 170 + rnd.uniform(-40, 40)
        cv.poly(ellipse_pts(x, 1650 + rnd.uniform(-10, 4), rnd.uniform(16, 40), rnd.uniform(8, 16), 12, 180, 360), C["L5"])
    grass(cv, -1500, 5000, 1648, C["L5"], te, h=40, n=70, seed=4, wind=0.8, w=7)

def tugun_hero(cv, X, G, hs, walk, phase, extra=None):
    th = math.radians(20) * walk * math.sin(phase)
    dyb = 175 - 175 * math.cos(th)
    def L(p): return (X + p[0] * hs, G + (p[1] + dyb) * hs)
    sway = 3 * math.sin(phase)
    stick_a, stick_b = (32, -300), (-118, -368 + sway)
    knot = (stick_b[0] + 4, stick_b[1] + 34)
    cloth, cloth_d = hx("9E4A3E"), hx("843B31")
    cv.poly(ellipse_pts(*L(knot), 34 * hs, 30 * hs, 20), cloth)
    cv.poly(ellipse_pts(*L((knot[0] + 4, knot[1] + 8)), 26 * hs, 18 * hs, 16, 0, 180), cloth_d)
    for (ox, oy) in ((-14, -8), (8, -14), (16, 6), (-6, 12), (-20, 10)):
        cv.circle(*L((knot[0] + ox, knot[1] + oy)), 3.2 * hs, hx("E8E1D3"))
    cv.poly([L((stick_b[0] - 8, stick_b[1] + 4)), L((stick_b[0] + 2, stick_b[1] - 12)), L((stick_b[0] + 12, stick_b[1] + 4))], cloth)
    kw = dict(walk=walk, phase=phase, rarm=((40, -246), (32, -300)), rshape="fist")
    if extra: kw.update(extra)
    r = hero(cv, X, G, hs, dir=1, **kw)
    cv.line([L((stick_a[0] + 18, stick_a[1] + 8)), L(stick_b)], hx("3B2E26"), 4.5 * hs)
    cv.circle(*r["hand"], 8.5 * hs, Q.SKIN)
    return r

def s15(cv, lt, D, t):
    def hf(cv_, X, G):
        ph = 2 * math.pi * 1.9 * lt
        tugun_hero(cv_, X, G, 1.15, 1.0, ph)
        for k in range(6):
            tk = k / (1.9 * 2) + 0.12
            v = lt - tk
            if 0 <= v < 0.45:
                dust_puff(cv_, X + V15 * (tk - lt) + 10, G, v / 0.45, C["L2"], k=0.35, seed=k, alpha=160)
    desert_world(cv, lt, hf)
    def post(img):
        a = np.asarray(img).copy()
        rows = np.arange(980, 1240)
        sh = np.round(2.2 * np.sin(rows * 0.21 + lt * 9) * np.sin(rows * 0.047 + lt * 2.3)).astype(int)
        for r_, s_ in zip(rows, sh):
            if s_: a[r_] = np.roll(a[r_], s_, axis=0)
        return Image.fromarray(a)
    return dict(post=post)

# ================================================================ scene 16: freeze + BACHKANA! stamp
def s16(cv, lt, D, t):
    sh = 22 * math.exp(-lt / 0.09) * math.sin(2 * math.pi * 11 * lt)
    cv.ox, cv.oy = sh, -0.5 * sh
    te = D15
    turn = smooth(0.25, 0.95, lt)
    def hf(cv_, X, G):
        ph = 2 * math.pi * 1.9 * te
        tugun_hero(cv_, X, G, 1.15, 1.0, ph, extra=dict(hyaw=turn, head_tilt=7 * turn, eye_k=1.15 + 0.15 * turn))
        for j, dx in enumerate((-260, -120, 0, 140, 280)):
            dust_puff(cv_, X + dx, G + 4, clamp01(lt / 0.75), C["L1"], k=0.9, seed=j + 3, alpha=210, n=8)
        if turn > 0.6:
            # embarrassed sweat drop
            hx_, hy_ = X + 22 * 1.15, G - 352 * 1.15
            a = int(230 * smooth(0.6, 0.8, turn))
            cv_.poly([(hx_, hy_ - 16), (hx_ + 9, hy_ + 2)] + ellipse_pts(hx_, hy_ + 4, 9, 9, 12, -10, 190) + [(hx_ - 9, hy_ + 2)], hx("E4ECEA") + (a,))
    desert_world(cv, te, hf, frozen=True)
    stamp = clamp01((lt + 1.0 / FPS) / 0.12)
    sc = lerp(1.9, 1.0, ease_out(stamp))
    def screen(img):
        OV.paste_center(img, OV.big_word("BACHKANA!", 150, halo_col=hx("F7EEDD")), 540 + sh * 0.5, 560, scale=sc, alpha=min(1, stamp * 1.3), ang=8)
    return dict(screen=screen, no_plate=True)

# ================================================================ cotton field (17, 18)
def cotton_row(cv, x0, x1, base, k, col, boll, t, seed):
    rnd = random.Random(seed)
    x = x0
    while x < x1:
        w = 44 * k * rnd.uniform(0.8, 1.2); h = 46 * k * rnd.uniform(0.8, 1.15)
        sw = 2 * math.sin(t * 2 + x * 0.01) * k
        for j in range(4):
            cv.circle(x + (j - 1.5) * w * 0.32 + sw, base - h * (0.45 + 0.25 * (j % 2)), w * 0.34, col)
        cv.rect(x - w * 0.5, base - h * 0.4, x + w * 0.5, base + 2, col)
        for j in range(3):
            cv.circle(x + rnd.uniform(-0.4, 0.4) * w + sw, base - h * rnd.uniform(0.45, 0.95), 6.5 * k, boll)
        x += w * 0.95

def cotton_field(cv, t, wide=False):
    cv.layer(1.0); sky(cv, K["sky0"], K["sky1"], 0, 1100)
    cv.layer(0.04); draw_sun(cv, 820, 280, 95, K["sun0"], K["sun1"])
    cv.layer(0.12); mountains(cv, 960, 200, K["L1"], seed=171)
    cv.layer(0.3)
    rnd = random.Random(17); x = -700
    while x < 2200:
        poplar(cv, x, 1040, rnd.uniform(200, 280), rnd.uniform(40, 54), K["L2"], sway=sway_x(t, 5, x * 0.02))
        x += rnd.uniform(60, 95)
    cv.rect(-2000, 1030, 3200, 3000, K["L2"])
    boll = hx("EEF0E8")
    cv.layer(0.5); cotton_row(cv, -900, 2300, 1090, 0.55, K["L3"], lerpc(boll, K["L3"], 0.3), t, 1)
    cv.rect(-2000, 1088, 3200, 3000, lerpc(K["L2"], K["L3"], 0.5))
    cv.layer(0.7); cotton_row(cv, -900, 2300, 1150, 0.75, lerpc(K["L3"], K["L4"], 0.4), lerpc(boll, K["L3"], 0.15), t, 2)
    cv.rect(-2000, 1148, 3200, 3000, K["L3"])

def s17(cv, lt, D, t):
    cv.set_cam(540, 960, 1.0)
    cotton_field(cv, lt)
    # donkey + two goats at the field edge, staring at the hero
    cv.layer(0.7)
    L4 = K["L4"]; L5 = K["L5"]
    quadruped(cv, 120, 1160, 0.95, L4, lt, kind="donkey", dir=1, head_look=0.0)
    quadruped(cv, 250, 1166, 0.95, L4, lt + 0.7, kind="goat", dir=1)
    quadruped(cv, 330, 1170, 0.8, L4, lt + 1.4, kind="goat", dir=1, graze=0.2 * (1 + math.sin(lt * 2)))
    cv.layer(1.0)
    G = 1290.0
    cv.rect(-2000, 1210, 3200, 3000, lerpc(K["L3"], K["L4"], 0.5))
    cotton_row(cv, -400, 1500, 1235, 1.0, L4, hx("EEF0E8"), lt, 3)
    cv.rect(-2000, 1232, 3200, 3000, L4)
    # phone on a tripod, REC
    px, py = 880, 1060
    for dx in (-50, 0, 50):
        cv.line([(px, py + 40), (px + dx, G)], L5, 5)
    cv.rect(px - 6, py + 20, px + 6, py + 50, L5)
    cv.rect(px - 16, py - 60, px + 16, py + 24, L5, r=6)
    blink = 1.0 if (lt * 2.0) % 1.0 < 0.65 else 0.25
    cv.circle(px - 40, py - 74, 9, ACCENT + (int(255 * blink),))
    wtext(cv, "REC", px + 2, py - 74, 26, ACCENT, FONT_BLACK, alpha=blink)
    # hero antics
    hs = 1.15; X = 480
    if lt < 0.6:
        hop = abs(math.sin(2 * math.pi * 1.8 * lt))
        legs = dict(hip_y=-175, chains=[((-3, -175), (-30, -110), (-74, -120 + 10 * hop), 0, True), ((3, -175), (5, -88), (6, 0), 0, False)])
        r = hero(cv, X, G - 40 * hop, hs, dir=1, legs=legs, rarm=((30, -250), (66, -300)), larm=((-30, -250), (-62, -290)),
                 rshape="open", lshape="open", head_tilt=-6 * hop, lean=-4)
    elif lt < 1.15:
        u = (lt - 0.6) / 0.55
        if u < 0.25: dr, yaw = 1, u * 4
        elif u < 0.5: dr, yaw = -1, (0.5 - u) * 4
        elif u < 0.75: dr, yaw = -1, (u - 0.5) * 4
        else: dr, yaw = 1, (1 - u) * 4
        r = hero(cv, X, G, hs, dir=dr, yaw=yaw, rarm=((60, -280), (100, -300)) if yaw < 0.5 else ((-70, -270), (-110, -290)),
                 larm=((-50, -280), (-90, -300)) if yaw < 0.5 else ((70, -270), (110, -290)), rshape="open", lshape="open")
    elif lt < 1.7:
        w_ = math.sin(2 * math.pi * 3.2 * lt)
        r = hero(cv, X, G - 8 * abs(w_), hs, dir=1, yaw=1.0, rarm=((-64, -300), (-70 + 22 * w_, -372)), larm=((64, -300), (70 + 22 * w_, -372)),
                 rshape="open", lshape="open", eye_k=1.3, head_tilt=5 * w_)
    else:
        sk = math.sin(2 * math.pi * 5 * lt)
        r = hero(cv, X, G, hs, dir=1, yaw=1.0, rarm=((-56, -290), (-28, -332)), larm=((56, -290), (30, -332)), rshape="open", lshape="open",
                 eye_k=1.7, eye_hl=True, head_tilt=12 * sk, shake=sk * 0.8)
    return {}

def tractor(cv, x, base, k, col, win, t, dir=1, puff_col=None):
    d = dir
    def P(px, py): return (x + d * px * k, base + py * k)
    R = 105; r = 58
    cv.poly([P(-150, -150), P(150, -150), P(170, -100), P(160, -40), P(-160, -40)], col)          # body + hood
    cv.poly([P(-160, -150), P(-160, -330), P(-20, -330), P(10, -150)], col)                        # cabin
    cv.poly([P(-138, -300), P(-40, -300), P(-20, -180), P(-138, -180)], win)                       # cabin window
    cv.circle(*P(-110, -R), R * k, col); cv.circle(*P(-110, -R), R * 0.42 * k, win)
    cv.circle(*P(-110, -R), R * 0.2 * k, col)
    cv.circle(*P(120, -r), r * k, col); cv.circle(*P(120, -r), r * 0.4 * k, win); cv.circle(*P(120, -r), r * 0.18 * k, col)
    cv.rect(*P(60, -250), *P(76, -150), col) if d > 0 else cv.rect(*P(76, -250), *P(60, -150), col)
    stack = P(68, -250)
    if puff_col:
        for j in range(5):
            u = ((t * 0.9 + j / 5) % 1.0)
            cv.circle(stack[0] + d * (14 * u + 8 * math.sin(u * 6 + j)) * k, stack[1] - 150 * u * k, (8 + 26 * u) * k, puff_col + (int(170 * (1 - u) * min(1, u * 6)),))
    return P(-90, -330)

def s18(cv, lt, D, t):
    cv.set_cam(lerp(430, 700, ease_io(lt / D)), 960, 0.92)
    cotton_field(cv, lt + 3, wide=True)
    cv.layer(0.15)
    for i, (sx_, sy_) in enumerate(((-200, 420), (-60, 330), (90, 460))):
        stork(cv, sx_ + 330 * lt + 200 * i, sy_ - 20 * lt, 0.9, K["L4"], lt, dir=1, ph=i * 1.1)
    cv.layer(0.7)
    tractor(cv, 1120, 1160, 0.72, lerpc(K["L3"], K["L4"], 0.6), K["L3"], lt, dir=-1, puff_col=hx("E4E8E2"))
    cv.layer(1.0)
    G = 1290.0
    cv.rect(-2000, 1210, 3200, 3000, lerpc(K["L3"], K["L4"], 0.5))
    cotton_row(cv, -800, 2000, 1235, 1.0, K["L4"], hx("EEF0E8"), lt, 4)
    cv.rect(-2000, 1232, 3200, 3000, K["L4"])
    roof = tractor(cv, 470, G, 1.15, K["L5"], K["L4"], lt, dir=1, puff_col=hx("E4E8E2"))
    shake = math.sin(2 * math.pi * 7 * lt)
    hero(cv, roof[0] + 20, roof[1] - 3 * abs(shake), 1.0, dir=1, head_tilt=-26 + 4 * shake, rarm=((26, -214), (20, -196)), rshape="flat",
         larm=((-22, -250), (-36, -296 + 6 * shake)), lshape="fist", bow=-6, shake=0.3 * shake)
    return {}

# ================================================================ scene 19: notes thrown from the haystack
NOTE19, NOTE19_D = hx("DCD3B6"), hx("A99F80")
def note_rect19(cv, cx, cy, w, h, ang):
    pts = [rot(p, ang, (cx, cy)) for p in [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]]
    cv.poly(pts, NOTE19)
    a, b = rot((cx - w * 0.2, cy - h / 2), ang, (cx, cy)), rot((cx - w * 0.2, cy + h / 2), ang, (cx, cy))
    cv.line([a, b], NOTE19_D, max(2.0, w * 0.07), caps=False)
    c = rot((cx + w * 0.18, cy), ang, (cx, cy))
    cv.circle(c[0], c[1], max(2.0, h * 0.26), NOTE19_D)
THROWS19 = (0.15, 1.1)
def s19(cv, lt, D, t):
    u = ease_io(lt / D)
    cv.set_cam(580, lerp(930, 900, u), lerp(1.0, 1.1, u))
    cv.layer(1.0); sky(cv, K["sky0"], K["sky1"], -100, 1150)
    cv.layer(0.04); draw_sun(cv, 840, 330, 100, K["sun0"], K["sun1"])
    cv.layer(0.12); mountains(cv, 1060, 170, K["L1"], seed=191)
    cv.layer(0.3)
    rnd = random.Random(19); x = -600
    while x < 2000:
        round_tree(cv, x, 1130, rnd.uniform(160, 220), rnd.uniform(60, 80), K["L2"], sway=sway_x(lt, 4, x), seed=int(x) + 900)
        x += rnd.uniform(120, 200)
    cv.rect(-2000, 1120, 3200, 3000, K["L2"])
    cv.layer(0.6)
    cv.rect(-2000, 1200, 3200, 3000, K["L3"])
    for px in range(-500, 1800, 210):
        cv.rect(px - 5, 1110, px + 5, 1205, K["L3"])
    cv.line([(-520, 1130), (1820, 1136)], K["L3"], 2.0, caps=False)
    cv.layer(1.0)
    G = 1300.0
    L4, L5 = K["L4"], K["L5"]
    cv.rect(-2000, 1250, 3200, 3000, L4)
    # haystack
    hx0 = 560; hw = 250; hh = 330
    stack = [(hx0 - hw, G)] + [(hx0 + hw * math.cos(a), G - hh * math.sin(a) ** 0.8) for a in [math.pi * (1 - i / 30) for i in range(31)]] + [(hx0 + hw, G)]
    cv.poly(stack, L5)
    for j in range(9):
        a0 = math.pi * (0.15 + 0.08 * j)
        cv.line([(hx0 + hw * 0.8 * math.cos(a0), G - hh * 0.8 * math.sin(a0) ** 0.8), (hx0 + hw * 0.95 * math.cos(a0 + 0.05), G - 10)],
                lerpc(L5, L4, 0.5), 2.2, caps=False)
    cv.rect(hx0 - 4, G - hh - 60, hx0 + 4, G - hh + 20, L5)
    # hero on top: slow-motion throws
    hs = 1.1; X = hx0 - 20; Y = G - hh + 10
    arm = ((-20, -250), (-40, -200))
    for tt in THROWS19:
        v = lt - tt
        if 0 <= v < 0.8:
            if v < 0.3:
                e = ease_io(v / 0.3); arm = ((lerp(-20, -40, e), lerp(-250, -270, e)), (lerp(-40, -80, e), lerp(-200, -250, e)))
            else:
                e = ease_out((v - 0.3) / 0.5); arm = ((lerp(-40, 50, e), lerp(-270, -310, e)), (lerp(-80, 100, e), lerp(-250, -370, e)))
    r = hero(cv, X, Y, hs, dir=1, rarm=arm, rshape="open" if any(0.45 < lt - tt < 1.0 for tt in THROWS19) else "fist", head_tilt=-10,
             larm=((22, -250), (40, -300)), lshape="fist")
    Lh = r["L"]
    # notes fly off like a flock of birds, catching the light
    for ti, tt in enumerate(THROWS19):
        rel = tt + 0.45
        rnd2 = random.Random(50 + ti)
        for i in range(22):
            v = lt - rel - rnd2.uniform(0, 0.4)
            if v < 0: continue
            v *= 0.62                                   # slow motion
            o = Lh((100, -370))
            vx = rnd2.uniform(260, 820); vy = -rnd2.uniform(20, 520)
            x = o[0] + vx * v + 40 * math.sin(v * 6 + i)
            y = o[1] + vy * v + 120 * v * v + 25 * math.sin(v * 8 + i * 1.7)
            ang = 40 * math.sin(v * 5 + i) + 60 * v
            flash = max(0, math.sin(v * 9 + i * 2.3)) ** 8
            k_ = rnd2.uniform(0.6, 0.95)
            hh_ = 40 * k_ * (0.35 + 0.65 * abs(math.cos(v * 7 + i)))
            note_rect19(cv, x, y, 92 * k_, hh_, ang)
            if flash > 0.05:
                cv.poly(ellipse_pts(x, y, 34 * k_, hh_ * 0.35, 10, ang=ang), (255, 255, 250, int(220 * flash)))
    cv.layer(1.25)
    grass(cv, -300, 1500, 1840, L5, lt, h=80, n=40, seed=19, wind=1.6, w=10)
    return {}
