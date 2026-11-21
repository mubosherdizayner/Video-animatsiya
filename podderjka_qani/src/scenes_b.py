# Scenes 5 (park bench), 6 (river, the only water), 7 (crossroads), 8 (giant button), 9 (gift boxes), 10 (bazaar).
import math, random
from base import *

K = KUNDUZ; S = SHOM

# ================================================================ scene 5: park bench with an imagined girl
# seated girl facing +x, units relative to the seat (y=0 seat, +92 = ground), long hair down her back
GIRL = [(8, -178), (21, -173), (28, -160), (27, -147), (20, -139), (26, -128), (30, -100), (30, -40), (34, -14), (88, -14),
        (98, -8), (98, 0), (92, 8), (92, 86), (108, 90), (108, 96), (80, 96), (80, 10), (30, 8), (-24, 8), (-30, -30),
        (-28, -100), (-22, -130), (-14, -140), (-8, -176)]
GIRL_HAIR = [(-6, -178), (-26, -166), (-36, -132), (-40, -84), (-36, -48), (-22, -44)]

def s5(cv, lt, D, t):
    cv.set_cam(lerp(580, 535, ease_io(lt / D)), 960, 1.0)
    cv.layer(1.0); sky(cv, K["sky0"], K["sky1"], 0, 1100)
    cv.layer(0.15); ridge(cv, 930, 90, K["L1"], seed=21, wl=(700, 260, 100))
    cv.layer(0.3)
    rnd = random.Random(4)
    for i in range(9):
        x = -200 + i * 190 + rnd.uniform(-40, 40)
        round_tree(cv, x, 1020, rnd.uniform(200, 260), rnd.uniform(80, 110), K["L2"], sway=sway_x(lt, 4, i), seed=i)
    cv.rect(-1500, 1010, 2800, 3000, K["L2"])
    cv.layer(0.55)
    for i in range(5):
        x = 60 + i * 300
        round_tree(cv, x, 1120, 320, 130, K["L3"], sway=sway_x(lt, 6, i * 2), seed=10 + i)
    cv.rect(-1500, 1110, 2800, 3000, lerpc(K["L2"], K["L3"], 0.55))
    # path
    cv.poly([(-1500, 1180), (2800, 1180), (2800, 1220), (-1500, 1230)], lerpc(K["L2"], K["L1"], 0.4))
    cv.layer(1.0)
    G = 1290.0; L4, L5 = K["L4"], K["L5"]
    cv.rect(-1500, 1240, 2800, 3000, L4)
    # big tut tree (left, canopy over the bench)
    round_tree(cv, 120, G, 1000, 360, L5, sway=sway_x(lt, 10, 0.5, 0.4), seed=77, trunk_w=48, lumps=12)
    # long bench
    hs = 1.5; seat = G - 92 * hs
    cv.rect(200, seat - 8, 960, seat + 12, L5, r=4)
    cv.rect(214, seat - 150, 946, seat - 128, L5, r=4)
    cv.rect(214, seat - 100, 946, seat - 82, L5, r=4)
    for lx in (240, 580, 920):
        cv.rect(lx - 9, seat - 150, lx + 9, G, L5)
    # imagined girl: dashed cream outline, fading in and out, never solid
    ga = 0.3 + 0.5 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.9 * lt - 1.2))
    gx, gk = 800, hs
    pts = [(gx - p[0] * gk, seat + p[1] * gk) for p in GIRL]
    hair = [(gx - p[0] * gk, seat + p[1] * gk) for p in GIRL_HAIR]
    col = CREAM_N + (int(255 * ga),)
    dashed(cv, pts, col, 5.0, dash=18, gap=11)
    dashed(cv, hair, col, 5.0, dash=14, gap=10, closed=False)
    # hero: glances at the empty spot, then turns to the camera and shrugs
    turn = smooth(0.95, 1.25, lt); shrug = smooth(1.2, 1.45, lt) * (1 - 0.25 * smooth(1.7, 1.9, lt))
    nod = math.sin(2 * math.pi * 1.4 * lt) * (1 - turn)
    rest_r = ((34, -206), (58, -196)); rest_l = ((30, -206), (54, -198))
    up_r = ((48, -228), (78, -262)); up_l = ((-18, -226), (-6, -262))
    def mix(a, b, e): return ((lerp(a[0][0], b[0][0], e), lerp(a[0][1], b[0][1], e)), (lerp(a[1][0], b[1][0], e), lerp(a[1][1], b[1][1], e)))
    hero(cv, 340, G, hs, legs="sit", hyaw=turn, head_tilt=4 * nod - 6 * shrug, look=1.0 - turn,
         rarm=mix(rest_r, up_r, shrug), larm=mix(rest_l, up_l, shrug), rshape="flat" if shrug > 0.4 else "fist",
         lshape="flat" if shrug > 0.4 else None, rangle=-30, eye_k=1.15)
    leaves(cv, lt, 12, (-200, 300, 900, 1100), L4, seed=12, wind=(70, 90), size=9, life=3.4)
    cv.layer(1.25)
    grass(cv, -300, 1500, 1960, L5, lt, h=90, n=34, seed=15, wind=1.2, w=12)
    return {}

# ================================================================ scene 6: riverbank (water only here)
WL6 = 1110.0
def s6(cv, lt, D, t):
    cam = (lerp(520, 565, ease_io(lt / D)), 960, 1.0)
    cv.set_cam(*cam)
    cv.layer(1.0); sky(cv, K["sky0"], K["sky1"], 0, WL6)
    cv.layer(0.12); mountains(cv, 1040, 200, K["L1"], seed=61)
    cv.layer(0.35)
    rnd = random.Random(14); x = -400
    while x < 1700:
        if rnd.random() < 0.55:
            poplar(cv, x, WL6 - 18, rnd.uniform(200, 300), rnd.uniform(40, 56), K["L2"], sway=sway_x(lt, 5, x * 0.02))
        else:
            round_tree(cv, x, WL6 - 18, rnd.uniform(140, 190), rnd.uniform(60, 80), K["L2"], sway=sway_x(lt, 4, x), seed=int(x))
        x += rnd.uniform(60, 110)
    cv.rect(-1500, WL6 - 30, 2800, WL6 + 2, K["L3"])
    cv.layer(1.0)
    L4, L5 = K["L4"], K["L5"]
    # small bank far left + wooden jetty over the water
    cv.poly([(-600, WL6 + 2), (-600, WL6 - 30), (40, WL6 - 30), (120, WL6 - 10), (170, WL6 + 2)], L5)
    reeds(cv, 60, 190, WL6 + 2, L5, lt, h=170, n=7, seed=3)
    reeds(cv, 960, 1110, WL6 + 2, L4, lt, h=120, n=7, seed=5)
    deck = WL6 - 46
    cv.rect(-200, deck, 470, deck + 14, L5)
    for px in (40, 220, 400, 460):
        cv.rect(px - 7, deck + 10, px + 7, WL6 + 4, L5)
    hs = 1.25
    G = deck + 92 * hs                  # feet dangle below the deck edge
    jig = math.sin(2 * math.pi * 0.7 * lt)
    kick = math.sin(2 * math.pi * 1.1 * lt)
    r = hero(cv, 400, G, hs, legs="sit", rarm=((52, -205), (78, -228)), larm=((48, -206), (66, -214)), head_tilt=2 * jig,
             rshape="fist")
    hp = r["hand"]
    tip = (905 + 6 * jig, 560 + 10 * jig)
    back = (hp[0] - 70, hp[1] + 40)
    cv.line([back, hp, tip], hx("3B2E26"), 5)
    entry = (930, WL6)
    sag = [(tip[0] + (entry[0] - tip[0]) * u_, tip[1] + (entry[1] - tip[1]) * u_ + 30 * math.sin(math.pi * u_)) for u_ in (0, 0.25, 0.5, 0.75, 1)]
    cv.line(sag, CREAM_N + (200,), 1.6, caps=False)
    def under(cv2):
        # line + heart bait under the surface
        bait = (936 + 3 * math.sin(lt * 2.4), 1192 + 4 * math.sin(lt * 1.7))
        cv2.line([entry, bait], CREAM_N + (120,), 1.4, caps=False)
        cv2.poly(heart_pts(bait[0], bait[1] + 14, 15), ACCENT)
        # fish: swim up, sniff the bait, swim away
        for (t0, side, dy_, k_) in ((0.0, -1, 30, 1.0), (0.55, 1, 55, 0.85), (1.05, -1, 70, 0.9)):
            v = lt - t0
            if v < 0 or v > 1.4: continue
            approach = ease_out(min(1, v / 0.45)); leave = ease_in(max(0, (v - 0.8) / 0.6))
            fx = bait[0] + side * (360 * (1 - approach) + 34 * k_) + side * 520 * leave
            fy = bait[1] + dy_ * 0.4 + 18 * (1 - approach) + 12 * math.sin(v * 7) * (1 - leave) - 40 * leave
            sniff = 6 * math.sin(v * 22) if 0.45 < v < 0.8 else 0
            fdir = -side if leave <= 0 else side
            fish(cv2, fx + sniff * (-side), fy, k_, L5 + (150,), dir=fdir, t=v + t0)
        # ripple rings where the line enters
        for j in range(3):
            u_ = ((lt * 0.9 + j / 3) % 1.0)
            ring(cv2, entry[0], entry[1] + 3, 14 + 70 * u_, (14 + 70 * u_) * 0.18, CREAM_N, 2.0, 150 * (1 - u_))
    tint = lerpc(K["L2"], K["L3"], 0.5)
    post = lambda img: reflect(img, cv, lt, 24.0, sun_x=None, extra=under, water_y=WL6, tint=tint, mix0=0.42, streaks=0.8)
    return dict(post=post)

# ================================================================ scene 7: crossroads with the BACHKANA sign
def s7(cv, lt, D, t):
    cv.set_cam(540, 960, 1.0)
    cv.layer(1.0); sky(cv, K["sky0"], K["sky1"], 0, 1050)
    cv.layer(0.05); draw_sun(cv, 250, 330, 90, K["sun0"], K["sun1"])
    cv.layer(0.12); mountains(cv, 1010, 220, K["L1"], seed=71)
    cv.layer(0.3); ridge(cv, 1060, 50, K["L2"], seed=8, wl=(900, 330, 140))
    cv.layer(0.6)
    for px in range(-200, 1500, 260):
        cv.rect(px - 4, 960, px + 4, 1100, K["L3"]); cv.rect(px - 22, 968, px + 22, 974, K["L3"])
    cv.line([(-220, 972), (1520, 972)], K["L3"], 1.4, caps=False)
    cv.rect(-1500, 1090, 2800, 3000, K["L3"])
    grass(cv, -300, 1400, 1095, K["L3"], lt, h=18, n=80, seed=3, wind=1.4)
    cv.layer(1.0)
    G = 1290.0; L4, L5 = K["L4"], K["L5"]
    cv.rect(-1500, 1160, 2800, 3000, L4)
    road = lerpc(K["L2"], K["L3"], 0.45)
    cv.poly([(548, 1092), (560, 1092), (700, G - 40), (400, G - 40)], road)          # road into the distance
    cv.rect(-1500, G - 50, 2800, G + 60, road)                                      # crossing road
    for xx in range(-1500, 2800, 140):
        cv.poly(ellipse_pts(xx, G + 30 + 8 * math.sin(xx * 0.3), 28, 4, 8), lerpc(road, L4, 0.3))
    saxaul(cv, 150, 1200, 0.9, L5, lt); saxaul(cv, 960, 1180, 0.7, L5, lt + 1)
    # signpost: one arrow board pointing left
    px = 640
    cv.rect(px - 10, 820, px + 10, G - 40, L5)
    board = [(330, 870), (380, 830), (700, 830), (700, 910), (380, 910)]
    cv.poly(board, L5)
    cv.poly([(p[0] + (6 if p[0] > 400 else 8), p[1] + (6 if p[1] < 860 else -6)) for p in board], lerpc(L5, L4, 0.3))
    wtext(cv, "BACHKANA", 530, 871, 50, ACCENT, FONT_BLACK, track=0.02)
    # hero: walks in from the right, reads, shakes head, turns around, walks off
    if lt < 0.75:
        X = lerp(1180, 720, lt / 0.75); dr = -1; walk = 1.0; ph = 2 * math.pi * 1.8 * lt; tilt = 0; shake = 0
    elif lt < 1.4:
        X = 720; dr = -1; walk = 0.0; ph = 0
        tilt = -16 * smooth(0.75, 0.95, lt) * (1 - smooth(1.0, 1.1, lt))
        shake = math.sin(2 * math.pi * 4.5 * (lt - 1.0)) * 3.2 if 1.0 < lt < 1.36 else 0
    else:
        v = lt - 1.4
        X = 720 + 560 * max(0, v - 0.05); dr = 1; walk = min(1, v / 0.12)
        ph = 2 * math.pi * 1.8 * v; tilt = 0; shake = 0
    hero(cv, X, G, 1.0, dir=dr, walk=walk, phase=ph, head_tilt=tilt, shake=shake)
    tx = -120 + 760 * lt
    bounce = abs(math.sin(2 * math.pi * 1.4 * lt)) * 26
    tumbleweed(cv, tx, G + 10 - 30 - bounce, 30, L5, ang=lt * 420)
    dust(cv, lt, 10, (-200, 1180, 900, 1300), lerpc(K["L2"], K["L1"], 0.3), seed=5, wind=(300, -10), size=(2, 6), alpha=140, life=1.5)
    return {}

# ================================================================ scene 8: giant PODPISKA button in the field
BTN_X = 640.0; BTN_G = 1300.0
LAND8 = (0.80, 1.20, 1.55)

def _hero8(lt):
    """(X, Y, pose dict) of the running/jumping/stomping hero"""
    top0 = BTN_G - 600
    if lt < 0.4:
        X = lerp(-80, 260, lt / 0.4)
        return X, BTN_G, dict(walk=1.5, phase=2 * math.pi * 3.2 * lt, bow=8)
    if lt < LAND8[0]:
        u = (lt - 0.4) / (LAND8[0] - 0.4)
        X = lerp(260, 600, u)
        Y = lerp(BTN_G, top0 + _sink(lt), u) - 420 * 4 * u * (1 - u)
        tuck = dict(hip_y=-160, chains=[((-3, -160), (40, -110), (8, -40), 0, True), ((3, -160), (46, -104), (16, -36), 0, False)])
        return X, Y, dict(legs=tuck, rarm=((30, -300), (52, -360)), larm=((-20, -300), (-30, -360)), rshape="open", lshape="open")
    # stomping on top: small hops between landings
    k = 0
    for i, lt_ in enumerate(LAND8):
        if lt >= lt_: k = i
    nxt = LAND8[k + 1] if k + 1 < len(LAND8) else None
    Ytop = top0 + _sink(lt)
    X = 600
    if nxt is not None:
        u = (lt - LAND8[k]) / (nxt - LAND8[k])
        Y = Ytop - 110 * 4 * u * (1 - u)
    else:
        Y = Ytop
    squash = math.exp(-(lt - LAND8[k]) / 0.06)
    stomp = dict(hip_y=-175 + 30 * squash, chains=[((-3, -175 + 30 * squash), (16, -88 + 20 * squash), (-2, 0), 0, True),
                                                  ((3, -175 + 30 * squash), (20, -88 + 22 * squash), (6, 0), 0, False)])
    arms = ((-20, -300), (-28, -362)) if k % 2 == 0 else ((30, -300), (46, -362))
    return X, Y, dict(legs=stomp, rarm=arms, rshape="fist", head_tilt=-6)

def _sink(lt):
    n = sum(1 for x in LAND8 if lt >= x)
    s_ = 0.0
    for x in LAND8:
        if lt >= x: s_ += 14 * (1 - math.exp(-(lt - x) / 0.05))
    return s_

def s8(cv, lt, D, t):
    by = bump(lt, LAND8, amp=9, decay=0.07, freq=16)
    cv.oy = by
    cv.set_cam(560, 930, 1.0)
    cv.layer(1.0); sky(cv, K["sky0"], K["sky1"], 0, 1150)
    cv.layer(0.05); draw_sun(cv, 860, 250, 90, K["sun0"], K["sun1"])
    cv.layer(0.12); mountains(cv, 1060, 200, K["L1"], seed=81)
    cv.layer(0.3); ridge(cv, 1130, 60, K["L2"], seed=4, wl=(900, 300, 120))
    cv.layer(0.6); ridge(cv, 1210, 30, K["L3"], seed=9, wl=(1000, 400, 160))
    cv.layer(1.0)
    L4, L5 = K["L4"], K["L5"]
    cv.rect(-1500, 1240, 2800, 3000, L4)
    rings = [lt - x for x in LAND8 if lt >= x]
    for v in rings:
        rx = 330 + 1300 * v; a = 180 * max(0, 1 - v / 0.8)
        ring(cv, BTN_X, BTN_G + 6, rx, rx * 0.1, lerpc(L4, K["L2"], 0.6), 5, a)
    # grass behind/around the button with the ring wave
    def gust_at(x):
        g = 0.0
        for v in rings:
            R = 330 + 1300 * v
            g += math.exp(-((abs(x - BTN_X) - R) / 60) ** 2) * max(0, 1 - v / 0.8) * (1 if x > BTN_X else -1)
        return g
    rnd = random.Random(8)
    for i in range(170):
        x = -300 + 1700 * (i + rnd.random()) / 170
        hh = 34 * rnd.uniform(0.6, 1.2); base = 1250 + rnd.uniform(0, 70)
        bend = 6 * math.sin(2 * math.pi * 0.8 * lt + x * 0.01) + 26 * gust_at(x)
        cv.poly([(x - 3, base + 2), (x + bend, base - hh), (x + 3, base + 2)], lerpc(L4, L5, 0.4))
    # button
    sink = _sink(lt)
    bw = 640; capw = 520
    cv.rect(BTN_X - bw / 2, BTN_G - 120, BTN_X + bw / 2, BTN_G, L5, r=30)
    cv.poly(ellipse_pts(BTN_X, BTN_G - 120, bw / 2, 34, 40), lerpc(L5, L4, 0.3))
    top = BTN_G - 600 + sink
    cap_dark = lerpc(ACCENT, L5, 0.45)
    cv.rect(BTN_X - capw / 2, top + 40, BTN_X + capw / 2, BTN_G - 118, cap_dark, r=40)
    cv.rect(BTN_X - capw / 2, top, BTN_X + capw / 2, BTN_G - 150, ACCENT, r=60)
    cv.poly(ellipse_pts(BTN_X, top + 2, capw / 2 - 14, 26, 36), lerpc(ACCENT, (255, 232, 214), 0.22))
    wtext(cv, "PODPISKA", BTN_X, top + 260, 92, CREAM_N, FONT_BLACK, track=0.02)
    # sparrows burst from the grass at the first landing
    burst = lt - LAND8[0]
    rnd = random.Random(31)
    for i in range(11):
        x0 = rnd.uniform(-100, 1300); y0 = 1270 + rnd.uniform(0, 40)
        if burst < 0:
            continue
        vx = (x0 - BTN_X) / 520 * 260 + rnd.uniform(-60, 60); vy = -rnd.uniform(380, 620)
        x = x0 + vx * burst; y = y0 + vy * burst + 120 * burst * burst
        bird_fly(cv, x, y, rnd.uniform(0.7, 1.0), math.sin(2 * math.pi * 7 * burst + i), L5)
    X, Y, kw = _hero8(lt)
    hero(cv, X, Y, 0.62, dir=1, **kw)
    if lt >= LAND8[0]:
        for x in LAND8:
            v = lt - x
            if 0 <= v < 0.5: dust_puff(cv, 600, top, v / 0.5, CREAM_N, k=0.5, seed=int(x * 10), alpha=150)
    return {}

# ================================================================ scene 9: gift boxes on parachutes (SHOM courtyard)
BOXES9 = [  # (x, t_land, size, lands_in_hands)
    (250, 0.85, 64, False), (820, 1.05, 74, False), (560, 1.28, 70, True), (980, 1.45, 56, False), (120, 1.6, 60, False)]
G9 = 1290.0
def box_draw(cv, x, y, sz, col, rib, ang=0.0):
    pts = [(x - sz / 2, y - sz), (x + sz / 2, y - sz), (x + sz / 2, y), (x - sz / 2, y)]
    if ang: pts = [rot(p, ang, (x, y - sz / 2)) for p in pts]
    cv.poly(pts, col)
    c = (x, y - sz / 2)
    for a, b in (((x, y - sz), (x, y)), ((x - sz / 2, y - sz / 2), (x + sz / 2, y - sz / 2))):
        if ang: a, b = rot(a, ang, c), rot(b, ang, c)
        cv.line([a, b], rib, max(2.0, sz * 0.06), caps=False)
    top = rot((x, y - sz), ang, c) if ang else (x, y - sz)
    cv.poly(ellipse_pts(top[0] - sz * 0.14, top[1] - sz * 0.06, sz * 0.16, sz * 0.09, 10, ang=-20 + ang), rib)
    cv.poly(ellipse_pts(top[0] + sz * 0.14, top[1] - sz * 0.06, sz * 0.16, sz * 0.09, 10, ang=20 + ang), rib)

def s9(cv, lt, D, t):
    cv.set_cam(540, lerp(700, 960, ease_io(min(1, lt / 1.3))), 1.0)
    cv.layer(1.0); sky(cv, S["sky0"], S["sky1"], -300, 1150)
    cv.layer(0.1); draw_sun(cv, 690, 830, 170, S["sun0"], S["sun1"])
    cv.layer(0.15); mountains(cv, 1000, 150, S["L1"], seed=91)
    cv.layer(0.4)
    for (x0, x1, top) in ((-300, 100, 900), (160, 480, 930), (760, 1100, 910), (1150, 1500, 935)):
        house(cv, x0, x1, top, 1060, S["L3"], beam=S["L4"])
    round_tree(cv, 640, 1060, 300, 110, S["L3"], sway=sway_x(lt, 5, 1.0), seed=4)
    cv.layer(0.7)
    wall_top = 1050
    # neighbours peeking over the wall (rise up at different times)
    for i, (nx, t0, hat) in enumerate(((300, 0.3, "doppi"), (640, 0.6, "scarf"), (900, 0.9, "cap"))):
        rise = ease_out(clamp01((lt - t0) / 0.35)) * (0.85 + 0.15 * math.sin(lt * 3 + i))
        person(cv, nx, wall_top + 300 - 120 * rise, 0.95, S["L5"], dir=-1 if nx > 540 else 1, look=1.0, hat=hat, pose="stand",
               arms=[((26, -250), (40, -290 + 40 * (1 - rise))), ((30, -250), (48, -290 + 40 * (1 - rise)))])
    cv.rect(-1500, wall_top, 2800, 1300, S["L4"])
    cv.rect(-1500, wall_top - 12, 2800, wall_top + 4, lerpc(S["L4"], S["L5"], 0.5))
    cv.layer(1.0)
    L4, L5 = S["L4"], S["L5"]
    cv.rect(-1500, 1230, 2800, 3000, lerpc(L4, S["L3"], 0.35))
    # long shadows (sun behind, low)
    for (sx_, w_, ln) in ((110, 40, 520), (470, 26, 420), (900, 180, 300)):
        cv.poly([(sx_ - w_, G9), (sx_ + w_, G9), (sx_ + w_ * 1.6 - ln * 0.55, G9 + ln), (sx_ - w_ * 1.6 - ln * 0.62, G9 + ln)], L5 + (55,))
    # old tut tree + so'ri
    round_tree(cv, 110, G9, 900, 300, L5, sway=sway_x(lt, 8, 0.2, 0.4), seed=19, trunk_w=40, lumps=11)
    sx0, sx1, sy = 720, 1080, G9 - 120
    cv.rect(sx0, sy, sx1, sy + 20, L5)
    for lx in (sx0 + 14, sx1 - 14, (sx0 + sx1) / 2):
        cv.rect(lx - 8, sy, lx + 8, G9, L5)
    cv.rect(sx0, sy - 70, sx0 + 10, sy, L5); cv.rect(sx1 - 10, sy - 70, sx1, sy, L5); cv.rect(sx0, sy - 74, sx1, sy - 64, L5)
    for bx in range(sx0 + 40, sx1 - 20, 40): cv.rect(bx - 3, sy - 66, bx + 3, sy, L5)
    # hero looks up, then catches a box
    catch = smooth(1.0, 1.28, lt)
    hs = 1.2; HX = 470
    r = hero(cv, HX, G9, hs, dir=1, head_tilt=lerp(-20, -4, catch), rarm=((34, -236), (74, -252 + 12 * catch)),
             larm=((30, -238), (62, -254 + 12 * catch)), rshape="flat", lshape="flat", eye_k=1.15)
    hands = r["hand"]
    for i, (bx, tl_, sz, inhand) in enumerate(BOXES9):
        fall_v = 420.0
        if inhand:
            land_y = hands[1] + 6; bx = hands[0] - 10
        else:
            land_y = G9 + 10
        v = lt - tl_
        if v < 0:
            y = land_y + fall_v * v; ang = 8 * math.sin(lt * 3 + i)
            x = bx + 26 * math.sin(lt * 2.2 + i)
            # parachute
            cy_ = y - sz - 110
            cv.line([(x - sz * 0.45, y - sz), (x - 70, cy_)], CREAM_N + (160,), 1.5, caps=False)
            cv.line([(x + sz * 0.45, y - sz), (x + 70, cy_)], CREAM_N + (160,), 1.5, caps=False)
            cv.poly(ellipse_pts(x, cy_, 80, 50, 24, 180, 360), lerpc(S["L3"], S["L4"], 0.5))
            box_draw(cv, x, y, sz, L5, ACCENT, ang)
        else:
            if inhand:
                box_draw(cv, bx, land_y, sz, L5, ACCENT, 0)
            else:
                hop = 60 * math.exp(-v / 0.2) * abs(math.sin(math.pi * v / 0.22))
                box_draw(cv, bx, land_y - hop, sz, L5, ACCENT, 6 * math.sin(v * 10) * math.exp(-v / 0.3))
                # collapsed parachute
                cv.poly(ellipse_pts(bx - sz * 0.6 - 30 * min(1, v / 0.3), land_y - 6, 50 * min(1, v / 0.25) + 10, 10, 14, 180, 360), lerpc(S["L3"], S["L4"], 0.5))
    return {}

# ================================================================ scene 10: bazaar, banknote pile grows, wind takes a few
def stall(cv, x0, x1, gnd, h, col, seed=1, goods=True):
    cv.rect(x0, gnd - h, x0 + 10, gnd, col); cv.rect(x1 - 10, gnd - h, x1, gnd, col)
    aw = [(x0 - 26, gnd - h + 24), (x0 + 10, gnd - h - 40), (x1 - 10, gnd - h - 40), (x1 + 26, gnd - h + 24)]
    cv.poly(aw, col)
    n = int((x1 - x0 + 52) / 36)
    for i in range(n):
        cx = x0 - 26 + (i + 0.5) * (x1 - x0 + 52) / n
        cv.poly(ellipse_pts(cx, gnd - h + 24, (x1 - x0 + 52) / n / 2, 12, 10, 0, 180), col)
    cv.rect(x0 + 4, gnd - h * 0.42, x1 - 4, gnd, col)
    if goods:
        rnd = random.Random(seed)
        for i in range(int((x1 - x0) / 30)):
            cv.circle(x0 + 22 + i * 30 + rnd.uniform(-4, 4), gnd - h * 0.42 - rnd.uniform(8, 14), rnd.uniform(11, 17), col)

def note_rect(cv, cx, cy, w, h, ang=0.0, alpha=255):
    pts = [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]
    if ang: pts = [rot(p, ang, (cx, cy)) for p in pts]
    cv.poly(pts, NOTE + (alpha,))
    a, b = rot((cx - w * 0.18, cy - h / 2), ang, (cx, cy)), rot((cx - w * 0.18, cy + h / 2), ang, (cx, cy))
    cv.line([a, b], NOTE_D + (alpha,), max(1.5, w * 0.06), caps=False)
    c = rot((cx + w * 0.16, cy), ang, (cx, cy))
    cv.poly(ellipse_pts(c[0], c[1], h * 0.28, h * 0.28, 10), NOTE_D + (alpha,))

def s10(cv, lt, D, t):
    cv.set_cam(540, 960, 1.0 + 0.06 * ease_io(lt / D))
    cv.layer(1.0); sky(cv, S["sky0"], S["sky1"], 0, 1150)
    cv.layer(0.08); draw_sun(cv, 790, 860, 190, S["sun0"], S["sun1"])
    cv.layer(0.15); ridge(cv, 1000, 60, S["L1"], seed=101, wl=(800, 300, 120))
    cv.layer(0.35)
    for i in range(7):
        stall(cv, -260 + i * 250, -100 + i * 250, 1060, 130, S["L2"], seed=i)
    cv.rect(-1500, 1055, 2800, 3000, S["L2"])
    cv.layer(0.6)
    for i in range(6):
        stall(cv, -330 + i * 330, -120 + i * 330, 1160, 170, S["L3"], seed=20 + i)
    cv.rect(-1500, 1155, 2800, 3000, S["L3"])
    cv.layer(1.0)
    L4, L5 = S["L4"], S["L5"]
    G = 1290.0
    cv.rect(-1500, 1240, 2800, 3000, L4)
    hs = 1.3
    ty = G - 100 * hs
    # stall table
    cv.rect(420, ty, 900, ty + 16, L5)
    cv.rect(434, ty + 16, 886, G - 10, lerpc(L5, L4, 0.25))
    cv.rect(434, G - 14, 886, G, L5)
    for px in (440, 880):
        cv.rect(px - 10, ty - 220, px, ty, L5)
    cv.poly([(400, ty - 210), (920, ty - 210), (950, ty - 160), (370, ty - 160)], L5)
    # banknote stacks laid one by one
    cyc = 0.24
    n = min(6, int(max(0, lt - 0.05) / cyc) + 1)
    sh_ = 20
    for i in range(n):
        u = (lt - 0.05 - i * cyc) / 0.12
        drop = 18 * (1 - ease_out(clamp01(u)))
        for j in range(3):
            note_rect(cv, 640 + (i % 2) * 6 - 3 + j * 1.5, ty - sh_ * i - 6 - j * 5 - drop, 120, 8, 0)
        note_rect(cv, 640 + (i % 2) * 6, ty - sh_ * i - 20 - drop, 122, 10, 0)
    # hero lays the next stack: arm reaches to the pile each cycle
    ph = ((lt - 0.05) % cyc) / cyc
    reach = math.sin(math.pi * ph) if lt < 0.05 + 6 * cyc else 0.0
    pile_top = ty - sh_ * n
    r = hero(cv, 330, G, hs, dir=1, rarm=((40, -220 + 6 * reach), (lerp(56, 96 + 60 * 0, reach) + 40 * reach, -214 - 30 * reach)),
             rshape="flat", head_tilt=8, look=0.5)
    # wind lifts a few notes off the top
    for k, (t0, ph2) in enumerate(((1.0, 0.0), (1.15, 1.3), (1.32, 2.1), (1.45, 0.7))):
        v = lt - t0
        if v < 0: continue
        x = 660 + 240 * v + 160 * v * v + 30 * math.sin(v * 7 + ph2)
        y = pile_top - 10 - 220 * v + 40 * math.sin(v * 5 + ph2)
        note_rect(cv, x, y, 118, 46, ang=90 * v + 30 * math.sin(v * 9 + ph2), alpha=int(255 * max(0, 1 - v / 1.2)))
    # cat on the counter watching the notes
    look = smooth(1.0, 1.2, lt)
    cat_sit(cv, 845, ty, 1.2, L5, lt, dir=-1 if look < 0.5 else 1, look=look)
    return {}
