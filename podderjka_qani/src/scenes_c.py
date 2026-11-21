# Scenes 11 (choyxona whisper), 12 (karnay on the hilltop), 13 (paper planes, SHOM -> TUN), 14 (night wedding cha-cha).
import math, random
from base import *
from script_data import CHA_F, SCENES
import overlay as OV

S = SHOM; N = TUN

def teapot(cv, cx, cy, k, col):
    cv.poly(ellipse_pts(cx, cy - 16 * k, 24 * k, 18 * k, 22), col)
    cv.rect(cx - 13 * k, cy - 4 * k, cx + 13 * k, cy, col)
    cv.rect(cx - 10 * k, cy - 38 * k, cx + 10 * k, cy - 30 * k, col)
    cv.circle(cx, cy - 41 * k, 4 * k, col)
    cv.poly([(cx + 18 * k, cy - 12 * k), (cx + 40 * k, cy - 32 * k), (cx + 43 * k, cy - 28 * k), (cx + 22 * k, cy - 4 * k)], col)
    cv.line([(cx - 20 * k, cy - 26 * k), (cx - 34 * k, cy - 20 * k), (cx - 22 * k, cy - 6 * k)], col, 4 * k)

def sori(cv, x0, x1, top, gnd, col, rail=True):
    cv.rect(x0, top, x1, top + 18, col)
    for lx in (x0 + 16, x1 - 16, (x0 + x1) / 2):
        cv.rect(lx - 9, top, lx + 9, gnd, col)
    if rail:
        cv.rect(x0, top - 80, x0 + 10, top, col); cv.rect(x1 - 10, top - 80, x1, top, col)
        cv.rect(x0, top - 84, x1, top - 74, col)
        for bx in range(int(x0) + 36, int(x1) - 16, 36): cv.rect(bx - 3, top - 76, bx + 3, top, col)

# ================================================================ scene 11: whispering at the choyxona
def s11(cv, lt, D, t):
    cv.set_cam(655, 1051, 1.28 + 0.08 * ease_io(lt / D))
    cv.layer(1.0); sky(cv, S["sky0"], S["sky1"], 0, 1150)
    cv.layer(0.08); draw_sun(cv, 870, 900, 150, S["sun0"], S["sun1"])
    cv.layer(0.18); mountains(cv, 1000, 140, S["L1"], seed=111)
    cv.layer(0.35)
    rnd = random.Random(2)
    for i in range(8):
        round_tree(cv, -250 + i * 230, 1060, rnd.uniform(220, 280), rnd.uniform(80, 100), S["L2"], sway=sway_x(lt, 4, i), seed=i + 40)
    cv.rect(-1500, 1050, 2800, 3000, S["L2"])
    # choyxona building with arches
    cv.layer(0.6)
    L3, L4, L5 = S["L3"], S["L4"], S["L5"]
    cv.rect(-200, 860, 1300, 1150, L3)
    cv.rect(-220, 840, 1320, 870, L3)
    for i in range(7):
        ax = -120 + i * 200
        cv.rect(ax, 940, ax + 120, 1150, L4)
        cv.poly(ellipse_pts(ax + 60, 940, 60, 50, 20, 180, 360), L4)
    for i in range(10):
        lx = -100 + i * 150
        sw = 4 * math.sin(lt * 2 + i)
        cv.line([(lx, 870), (lx + sw * 0.3, 900)], L4, 2)
        cv.poly(ellipse_pts(lx + sw * 0.3, 912, 10, 14, 10), lerpc(L4, S["sun0"], 0.25))
    cv.rect(-1500, 1150, 2800, 3000, L3)
    cv.layer(1.0)
    G = 1290.0
    cv.rect(-1500, 1230, 2800, 3000, L4)
    # so'ri with three men around a teapot
    top = G - 125
    sori(cv, 470, 1060, top, G, L5)
    lean = 14 * smooth(0.25, 0.9, lt)
    bob = [math.sin(lt * 3 + i) * 1.5 for i in range(3)]
    person(cv, 600, top, 0.8, L5, dir=-1, pose="sit_cross", hat="doppi", lean=-lean - 4, look=0.0, head_dy=bob[0])
    person(cv, 930, top, 0.8, L5, dir=-1, pose="sit_cross", hat="cap", lean=-lean * 0.7, head_dy=bob[1])
    person(cv, 770, top + 6, 0.84, L5, dir=-1, pose="sit_cross", hat="doppi", lean=-lean * 0.85, look=1.0 * smooth(0.2, 0.5, lt), head_dy=bob[2])
    cv.rect(700, top - 40, 860, top - 26, L5)
    teapot(cv, 770, top - 40, 1.15, L5)
    # hero leans in from the side, hand cupped at his mouth
    lean_in = smooth(0.0, 0.5, lt)
    r = hero(cv, 360, G, 1.25, dir=1, bow=6 + 12 * lean_in, rarm=((40, -262), (30, -318)), rshape="flat", rangle=-100,
             head_tilt=4, look=1.0)
    # steam curls into little speech bubbles
    sp = (770 + 46, top - 40 - 38)
    def steam_fn(d, tf, k):
        for j in range(3):
            v = ((lt * 0.75 + j / 3) % 1.0)
            x = sp[0] - 30 * v + 14 * math.sin(v * 9 + j)
            y = sp[1] - 300 * v
            a = int(200 * math.sin(math.pi * min(1, v * 1.2)))
            w_ = 18 + 40 * v; h_ = 12 + 26 * v
            p0 = tf(x - w_, y - h_); p1 = tf(x + w_, y + h_)
            d.rounded_rectangle((p0[0], p0[1], p1[0], p1[1]), radius=h_ * k, outline=CREAM_N + (a,), width=max(1, int(4 * k)))
            q = tf(x - w_ * 0.3, y + h_); q2 = tf(x - w_ * 0.55, y + h_ + 16); q3 = tf(x - w_ * 0.05, y + h_)
            d.line([q, q2, q3], fill=CREAM_N + (a,), width=max(1, int(4 * k)))
    cv.soft((sp[0] - 150, sp[1] - 360, sp[0] + 120, sp[1] + 40), steam_fn, blur=0.6, scale=0.5)
    Q.draw_steam(cv, lambda p: p, sp[0] - 6, sp[1] + 4, 1.0, lt, scale=0.9, opacity=0.5, height=60)
    pss_pos = cv.to_screen(770, top - 250)
    pop = ease_out_back(clamp01((lt - 0.3) / 0.25))
    def screen(img):
        if pop > 0.01:
            OV.paste_center(img, OV.bubble_img("pss..."), pss_pos[0], pss_pos[1], scale=max(0.05, pop), alpha=min(1, pop))
    return dict(screen=screen)

# ================================================================ scene 12: karnay on the hilltop
RINGS12 = [0.36 + 0.17 * i for i in range(9)]
def s12(cv, lt, D, t):
    blow = smooth(0.25, 0.4, lt)
    sh = 3.5 * blow * (math.sin(lt * 61) + 0.6 * math.sin(lt * 37))
    cv.ox, cv.oy = sh, 0.7 * sh
    cv.set_cam(540, 1000, 1.0)
    cv.layer(1.0); sky(cv, S["sky0"], S["sky1"], -100, 1150)
    cv.layer(0.08); draw_sun(cv, 760, 1090, 230, S["sun0"], S["sun1"])
    cv.layer(0.15); mountains(cv, 1110, 120, S["L1"], seed=121)
    cv.layer(0.3); ridge(cv, 1150, 40, S["L2"], seed=12, wl=(900, 300, 140))
    # valley mahalla roofs with pigeons
    cv.layer(0.5)
    L3, L4, L5 = S["L3"], S["L4"], S["L5"]
    rnd = random.Random(12)
    roofs = []
    x = -400
    while x < 1700:
        w = rnd.uniform(120, 220); top = 1180 + rnd.uniform(-30, 30)
        house(cv, x, x + w, top, 1400, L3, beam=L4, parapet=True)
        roofs.append((x + w * 0.5, top - 10))
        x += w + rnd.uniform(10, 40)
    cv.rect(-1500, 1330, 2800, 3000, L3)
    # pigeons: sit on roofs, scatter when the sound rings reach them
    for i, (rx, ry) in enumerate(roofs[::2]):
        for j in range(2):
            px_ = rx + (j - 0.5) * 40
            tr = 0.55 + abs(px_ - 330) / 1300
            v = lt - tr
            if v < 0:
                bird_perch(cv, px_, ry, 0.9, L4, dir=1 if j else -1, peck=max(0, math.sin(lt * 5 + i + j)) ** 3)
            else:
                dx = (1 if px_ > 330 else -1) * (160 * v + 50 * v * v)
                bird_fly(cv, px_ + dx, ry - 260 * v - 90 * v * v, 0.9 + 0.3 * v, math.sin(2 * math.pi * 6 * v + i), L4)
    # near hill + hero with karnay
    cv.layer(1.0)
    G = 1200.0
    hill = [(-400, 1400), (-300, G + 30), (60, G + 6), (330, G), (560, G + 20), (820, G + 90), (1100, 1280), (1500, 1400)]
    cv.poly(hill + [(1500, 3000), (-400, 3000)], L5)
    grass(cv, -200, 900, G + 12, L5, lt, h=26, n=60, seed=3, wind=1.2)
    hs = 1.15
    ang = math.radians(-34 - 3 * blow)
    mouth = (30, -318)
    Lk = 440
    bell = (mouth[0] + Lk * math.cos(ang), mouth[1] + Lk * math.sin(ang))
    def along(u): return (mouth[0] + (bell[0] - mouth[0]) * u, mouth[1] + (bell[1] - mouth[1]) * u)
    r = hero(cv, 330, G, hs, dir=1, rarm=((40, -246), along(0.30)), larm=((26, -250), along(0.17)), rshape="fist",
             head_tilt=-18 * 0.6, bow=-4)
    L = r["L"]
    GOLD_L = lerpc(Q.GOLD, (255, 230, 180), 0.3)
    m0 = L(mouth); b0 = L(bell)
    cv.line([m0, b0], Q.GOLD, 7.5 * hs)
    cv.line([L(along(0.02)), L(along(0.98))], GOLD_L, 2.2 * hs, caps=False)
    perp = (-math.sin(ang), math.cos(ang))
    bw = 46
    bpts = [L((bell[0] - 40 * math.cos(ang) + perp[0] * 6, bell[1] - 40 * math.sin(ang) + perp[1] * 6)),
            L((bell[0] + perp[0] * bw, bell[1] + perp[1] * bw)), L((bell[0] - perp[0] * bw, bell[1] - perp[1] * bw)),
            L((bell[0] - 40 * math.cos(ang) - perp[0] * 6, bell[1] - 40 * math.sin(ang) - perp[1] * 6))]
    cv.poly(bpts, Q.GOLD)
    for u in (0.25, 0.5, 0.75):
        p = L(along(u)); cv.circle(p[0], p[1], 6 * hs, Q.GOLD)
    # sound rings from the bell
    a0 = math.degrees(ang)
    for tr in RINGS12:
        v = lt - tr
        if v <= 0: continue
        R = 40 + 620 * v
        al = int(200 * max(0, 1 - v / 0.9))
        if al <= 2: continue
        bb = (b0[0] - R, b0[1] - R, b0[0] + R, b0[1] + R)
        p0 = cv.T(bb[0], bb[1]); p1 = cv.T(bb[2], bb[3])
        cv.d.arc((p0[0], p0[1], p1[0], p1[1]), start=a0 - 55, end=a0 + 55, fill=L3 + (al,), width=max(1, int(cv.S(8 - 4 * v))))
    xayp = ease_out_back(clamp01((lt - 0.36) / 0.22))
    def screen(img):
        if xayp > 0.01:
            jit = 4 * blow * math.sin(lt * 47)
            OV.paste_center(img, OV.big_word("XAYP!", 190), 560 + jit, 470, scale=max(0.05, xayp), alpha=min(1, xayp * 1.5), ang=6)
    return dict(screen=screen)

# ================================================================ scene 13: paper planes, dusk turns to night
PLANES13 = (0.15, 0.62, 1.08)
def paper_plane(cv, x, y, k, col, ang=0.0, roll=0.0):
    w = 1 - 0.5 * abs(roll)
    pts = [(x + 60 * k, y), (x - 40 * k, y - 26 * k * w), (x - 22 * k, y + 2 * k), (x - 40 * k, y + 12 * k)]
    fold = [(x + 60 * k, y), (x - 22 * k, y + 2 * k), (x - 40 * k, y + 12 * k)]
    if ang: pts = [rot(p, ang, (x, y)) for p in pts]; fold = [rot(p, ang, (x, y)) for p in fold]
    cv.poly(pts, col)
    cv.poly(fold, lerpc(col[:3], (150, 150, 140), 0.35) + ((col[3],) if len(col) > 3 else ()))

def s13(cv, lt, D, t):
    b = smooth(0.05, D - 0.05, lt)
    P = plerp(S, N, b)
    cv.set_cam(560, lerp(1010, 880, ease_io(lt / D)), 1.0)
    top = lerpc(S["sky0"], N["sky0"], b ** 0.7)
    GLOW = hx("E6B48A")
    bot = lerpc(S["sky1"], GLOW, smooth(0.0, 0.5, b)) if b < 0.5 else lerpc(GLOW, N["sky1"], smooth(0.5, 1.0, b))
    cv.layer(1.0); sky(cv, top, bot, 0, 1150)
    # stars appear
    rnd = random.Random(5)
    sa = smooth(0.35, 1.0, b)
    if sa > 0.01:
        cv.layer(0.02)
        for i in range(46):
            x, y = rnd.uniform(-60, 1140), rnd.uniform(0, 760)
            tw = 0.6 + 0.4 * math.sin(lt * 3 + i)
            cv.circle(x, y, rnd.uniform(1.4, 3.0), N["sun0"] + (int(230 * sa * tw),))
    # setting sun
    cv.layer(0.08)
    sy = lerp(980, 1120, b)
    if b < 0.95:
        draw_sun(cv, 300, sy, 150, S["sun0"], S["sun1"], alpha=1 - smooth(0.5, 0.95, b))
    cv.layer(0.15); mountains(cv, 1020, 130, P["L1"], seed=131)
    cv.layer(0.35)
    rnd2 = random.Random(13)
    x = -400
    while x < 1700:
        w = rnd2.uniform(110, 200); top = 1040 + rnd2.uniform(-30, 30)
        house(cv, x, x + w, top, 1200, P["L2"], beam=None)
        if rnd2.random() < 0.2:
            cv.poly(ellipse_pts(x + w / 2, top, w * 0.3, w * 0.28, 18, 180, 360), P["L2"])
        x += w + rnd2.uniform(5, 30)
    cv.rect(-1500, 1190, 2800, 3000, P["L2"])
    cv.rect(940, 860, 976, 1050, P["L2"]); cv.rect(930, 840, 986, 870, P["L2"])
    # mid roofs with windows lighting up one by one
    cv.layer(0.6)
    rnd3 = random.Random(31)
    x = -300; wi = 0
    while x < 1600:
        w = rnd3.uniform(170, 260); top = 1110 + rnd3.uniform(-20, 30)
        cv.rect(x, top, x + w, 1300, P["L3"]); cv.rect(x - 6, top - 10, x + w + 6, top + 4, P["L3"])
        for k in range(int(w // 70)):
            wx = x + 30 + k * 70; wy = top + 40
            ton = 0.15 + 0.11 * ((wi * 7) % 13)
            lit = smooth(ton, ton + 0.12, lt) * smooth(0.2, 0.6, b)
            col = lerpc(P["L4"], N["win"], lit)
            cv.rect(wx, wy, wx + 30, wy + 40, col, r=2)
            wi += 1
        x += w + rnd3.uniform(10, 30)
    cv.rect(-1500, 1290, 2800, 3000, P["L3"])
    # near roofs below (the planes glide over them) + the hero's rooftop
    cv.layer(0.85)
    rnd4 = random.Random(7); x = 560
    while x < 1900:
        w = rnd4.uniform(200, 300); top = 1330 + rnd4.uniform(-20, 30)
        cv.rect(x, top, x + w, 3000, P["L4"]); cv.rect(x - 6, top - 10, x + w + 6, top + 4, P["L4"])
        for kk in range(int(w // 90)):
            wx = x + 40 + kk * 90; ton = 0.5 + 0.23 * ((kk + int(x)) % 5)
            cv.rect(wx, top + 60, wx + 34, top + 108, lerpc(P["L5"], N["win"], smooth(ton, ton + 0.1, lt) * smooth(0.3, 0.7, b)), r=2)
        x += w + rnd4.uniform(0, 20)
    cv.layer(1.0)
    roof = 1260.0
    cv.rect(-600, roof, 620, 3000, P["L5"]); cv.rect(-620, roof - 16, 640, roof + 4, P["L5"])
    for bx in range(-560, 600, 34): cv.rect(bx, roof + 4, bx + 10, roof + 12, P["L4"])
    # throw cycle
    hs = 1.2
    arm = ((-14, -260), (-40, -300))
    for tt in PLANES13:
        v = lt - (tt - 0.22)
        if 0 <= v < 0.42:
            if v < 0.22:
                e = ease_io(v / 0.22); arm = ((lerp(-4, -20, e), -262), (lerp(10, -50, e), lerp(-150, -312, e)))
            else:
                e = ease_out((v - 0.22) / 0.2); arm = ((lerp(-20, 50, e), lerp(-262, -300, e)), (lerp(-50, 100, e), lerp(-312, -350, e)))
    r = hero(cv, 220, roof, hs, dir=1, rarm=arm, rshape="flat", head_tilt=-10, look=0.6)
    L = r["L"]
    for i, tt in enumerate(PLANES13):
        v = lt - tt
        if v < -0.22: continue
        if v < 0:
            hp = r["hand"]; paper_plane(cv, hp[0], hp[1] - 6, 0.45, NOTE + (255,), ang=-10)
            continue
        k = 0.45 + 1.4 * v ** 1.3
        x = L((100, -350))[0] + 470 * v + 90 * v * v
        y = L((100, -350))[1] - 120 * v + 260 * v * v * 0.6 + 14 * math.sin(v * 5 + i)
        paper_plane(cv, x, y, k, NOTE + (255,), ang=-8 + 10 * math.sin(v * 3 + i), roll=0.4 * math.sin(v * 4 + i))
    return {}

# ================================================================ scene 14: night wedding, three cha-cha steps
def cha_local():
    s14 = SCENES[13]
    return [(f - s14["f0"]) / FPS for f in CHA_F]

def s14(cv, lt, D, t):
    chas = cha_local()
    pre = 1.0 / FPS
    cv.oy = bump(lt + pre * 0.5, chas, amp=8, decay=0.06, freq=14)
    cv.set_cam(540, 980, 1.0)
    cv.layer(1.0); sky(cv, N["sky0"], N["sky1"], 0, 1150)
    rnd = random.Random(14)
    cv.layer(0.02)
    for i in range(60):
        x, y = rnd.uniform(-60, 1140), rnd.uniform(0, 900)
        tw = 0.55 + 0.45 * math.sin(lt * 2.5 + i * 1.7)
        cv.circle(x, y, rnd.uniform(1.4, 3.0), N["star"] + (int(220 * tw),))
    cv.layer(0.04); draw_sun(cv, 800, 330, 88, N["sun0"], N["sun1"])
    cv.layer(0.2); ridge(cv, 1030, 80, N["L1"], seed=141, wl=(800, 300, 120))
    cv.layer(0.4)
    for i in range(7):
        round_tree(cv, -200 + i * 240, 1110, rnd.uniform(260, 330), rnd.uniform(90, 120), N["L2"], sway=sway_x(lt, 4, i), seed=i + 70)
    cv.rect(-1500, 1100, 2800, 3000, N["L2"])
    # house with lit windows behind the courtyard
    cv.layer(0.6)
    cv.rect(-200, 930, 1300, 1190, N["L3"]); cv.rect(-220, 912, 1320, 940, N["L3"])
    for i in range(6):
        wx = -80 + i * 230
        cv.rect(wx, 990, wx + 60, 1070, lerpc(N["L4"], N["win"], 0.8), r=3)
    cv.rect(-1500, 1180, 2800, 3000, N["L3"])
    # back row of guests clapping in a circle
    cv.layer(0.8)
    L4, L5 = N["L4"], N["L5"]
    for i, gx in enumerate(range(-80, 1200, 150)):
        cl = (lt * 2.1 + i * 0.13) % 1.0
        person(cv, gx, 1215, 0.78, L4, dir=1 if gx < 540 else -1, clap=cl + 1e-4, hat=("doppi", "scarf", "cap")[i % 3],
               dress="skirt" if i % 3 == 1 else "coat", look=0.0)
    cv.layer(1.0)
    cv.rect(-1500, 1235, 2800, 3000, L4)
    # big trees left/right with string lights
    round_tree(cv, -60, 1270, 980, 260, L5, sway=sway_x(lt, 8, 0.3), seed=141, trunk_w=40)
    round_tree(cv, 1150, 1270, 940, 250, L5, sway=sway_x(lt, 8, 1.3), seed=142, trunk_w=40)
    flash = sum(math.exp(-(lt - c) / 0.14) for c in chas if lt >= c - 1e-6)
    for (a, b_, sag, n) in (((40, 640), (1040, 620), 120, 16), ((60, 760), (1020, 760), 90, 14)):
        pts = []
        for j in range(n + 1):
            u = j / n
            pts.append((lerp(a[0], b_[0], u), lerp(a[1], b_[1], u) + sag * 4 * u * (1 - u) + 3 * math.sin(lt * 2 + j)))
        cv.line(pts, L5, 2.2)
        def glow_fn(d, tf, k):
            for j, p in enumerate(pts[1:-1]):
                br = 0.55 + 0.25 * math.sin(lt * 5 + j * 1.3) + 0.5 * min(1, flash)
                q = tf(p[0], p[1] + 10); rr = (18 + 10 * min(1, flash)) * k
                d.ellipse((q[0] - rr, q[1] - rr, q[0] + rr, q[1] + rr), fill=N["win"] + (int(110 * min(1, br)),))
        cv.soft((a[0] - 40, min(a[1], b_[1]) - 40, b_[0] + 40, max(a[1], b_[1]) + sag + 60), glow_fn, blur=9, scale=0.35)
        for j, p in enumerate(pts[1:-1]):
            br = min(1, 0.6 + 0.3 * math.sin(lt * 5 + j * 1.3) + 0.6 * min(1, flash))
            cv.circle(p[0], p[1] + 10, 6.5, lerpc(lerpc(N["win"], L5, 0.35), lerpc(N["win"], (255, 236, 200), 0.5), br))
    # the hero dances: bounce, then three cha steps (step, hip turn, raised hand)
    hs = 1.2; HX = 540; G = 1270.0
    k = sum(1 for c in chas if lt >= c - 1e-6)
    if k == 0:
        bob = abs(math.sin(2 * math.pi * 1.6 * lt))
        kw = dict(walk=0.35, phase=2 * math.pi * 1.6 * lt, rarm=((30, -230), (40, -280 - 8 * bob)), rshape="fist", head_tilt=4 * math.sin(lt * 10), lean=4 * math.sin(2 * math.pi * 1.6 * lt))
        Y = G - 6 * bob
    else:
        c = chas[k - 1]
        e = ease_out(clamp01((lt - c + pre) / 0.1))
        side = 1 if k % 2 else -1
        fwd = 34 * e * side
        legs = dict(hip_y=-170, chains=[((-3, -170), (lerp(0, -10, e) - fwd * 0.3, -86), (-fwd * 0.9 - 6, 0), 0.0, True),
                                        ((3, -170), (lerp(0, 18, e) + fwd * 0.4, -88), (fwd + 8, 0), 0.0, False)])
        up_r = ((34, -300), (58, -370)); up_l = ((-24, -300), (-40, -366))
        rest_r = ((30, -230), (40, -280)); rest_l = ((-6, -210), (8, -150))
        def mix(a_, b2, ee): return ((lerp(a_[0][0], b2[0][0], ee), lerp(a_[0][1], b2[0][1], ee)), (lerp(a_[1][0], b2[1][0], ee), lerp(a_[1][1], b2[1][1], ee)))
        ra = mix(rest_r, up_r, e) if k in (1, 3) else rest_r
        la = mix(rest_l, up_l, e) if k in (2, 3) else rest_l
        kw = dict(legs=legs, rarm=ra, larm=la, rshape="open" if k in (1, 3) else "fist", lshape="open" if k in (2, 3) else None,
                  lean=10 * side * e, head_tilt=-6 * side * e)
        Y = G
    hero(cv, HX, Y, hs, dir=1, **kw)
    # front row of guests (partly out of frame)
    cv.layer(1.15)
    for i, gx in enumerate((-40, 260, 840, 1130)):
        cl = (lt * 2.1 + 0.5 + i * 0.11) % 1.0
        person(cv, gx, 1640, 1.25, L5, dir=1 if gx < 540 else -1, clap=cl + 1e-4, hat=("cap", "doppi", "scarf", "doppi")[i])
    # a paper plane from the rooftop glides across the top
    cv.layer(0.5)
    v = lt / D
    paper_plane(cv, lerp(-120, 1200, v), 300 + 60 * math.sin(v * 3), 0.8, NOTE + (235,), ang=-4 + 6 * math.sin(v * 5))
    pops = [ease_out_back(clamp01((lt - c + pre) / 0.16)) if lt >= c - 1e-6 else 0.0 for c in chas]
    def screen(img):
        for j, (pp, (x, y)) in enumerate(zip(pops, ((270, 520), (540, 430), (810, 520)))):
            if pp > 0.01:
                OV.paste_center(img, OV.big_word("CHA!", 120), x, y, scale=max(0.05, pp), alpha=min(1, pp * 1.4), ang=(-8, 4, -4)[j])
    return dict(screen=screen)
