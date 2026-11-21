# Scenes 1 (hook), 20 (CTA / loop), 2 (bus stop), 3 (steppe road), 4 (billboard).
import math, random
from base import *

K = KUNDUZ

# ================================================================ mahalla street (scenes 1 and 20 share it)
FAR_G = 1000.0          # far sidewalk / house base
NEAR_G = 1205.0         # near kerb
HERO_X, HERO_Y, HERO_S = 540.0, 1290.0, 1.6
CAM1 = (540.0, HERO_Y - 363 * HERO_S + 360 / 3.1, 3.1)        # scene 1 framing (waist-up, front)
CAM20 = (540.0, 960.0, 1.0)

def street_world(cv, wt, bubble=None):
    """wt = world time (continuous through the loop point: scene 1 uses t, scene 20 uses t - TOTAL)"""
    cv.layer(1.0)
    sky(cv, K["sky0"], K["sky1"], 0, 1250)
    cv.layer(0.05)
    draw_sun(cv, 860, 200, 100, K["sun0"], K["sun1"])
    if bubble: bubble(cv)
    cv.layer(0.12)
    flock(cv, wt, [(250 + 18 * wt, 400, 0.7, 0.0), (310 + 18 * wt, 370, 0.55, 1.7)], K["L3"])
    cv.layer(0.15)
    mountains(cv, 890, 230, K["L1"], seed=31)
    cv.layer(0.28)
    ridge(cv, 955, 55, K["L2"], seed=7)
    # terak row
    cv.layer(0.4)
    rnd = random.Random(5)
    x = -520
    while x < 1640:
        h = rnd.uniform(270, 390); w = rnd.uniform(46, 64)
        poplar(cv, x, FAR_G + 30, h, w, K["L3"], sway=sway_x(wt, 7, x * 0.01, 0.5))
        x += rnd.uniform(62, 92)
    cv.rect(-1400, FAR_G + 20, 2600, 1400, K["L3"])
    # far side of the street: flat-roofed houses, darvoza, dog asleep in the shade
    cv.layer(0.5)
    L4, L5 = K["L4"], K["L5"]
    for (x0, x1, top) in ((-560, -170, 840), (-150, 260, 865), (260, 620, 845), (820, 1180, 855), (1200, 1560, 870)):
        house(cv, x0, x1, top, FAR_G, L4, beam=L5, wins=[(x0 + 50, top + 52, 34, 46), (x1 - 84, top + 52, 34, 46)], win_col=L5)
    cv.rect(610, FAR_G - 120, 840, FAR_G, L4)             # wall around the gate
    darvoza(cv, 712, 132, 168, FAR_G, L5, lerpc(L4, L5, 0.62), L4)
    # shade strip along the wall + the dog
    cv.poly([(-200, FAR_G - 4), (600, FAR_G - 4), (640, FAR_G + 26), (-240, FAR_G + 26)], L5 + (60,))
    dog_sleep(cv, 330, FAR_G + 8, 0.92, L5, wt)
    cv.rect(-1400, FAR_G, 2600, 3200, lerpc(K["L2"], K["L3"], 0.35))       # road
    cv.rect(-1400, FAR_G, 2600, FAR_G + 14, L4)
    for xx in range(-1400, 2600, 160):
        cv.rect(xx, 1110, xx + 80, 1117, lerpc(K["L2"], K["L1"], 0.5))
    cv.layer(1.0)
    cv.rect(-1400, NEAR_G, 2600, 3200, L4)
    cv.rect(-1400, NEAR_G, 2600, NEAR_G + 10, L5)
    for xx in range(-1400, 2600, 210):
        cv.line([(xx, NEAR_G + 10), (xx - 60, 2000)], lerpc(L4, L5, 0.45), 2.2, caps=False)

def bench(cv, x0, x1, seat_y, col):
    cv.rect(x0, seat_y - 6, x1, seat_y + 10, col, r=3)
    for lx in (x0 + 24, x1 - 24):
        cv.rect(lx - 7, seat_y, lx + 7, HERO_Y, col)
    cv.rect(x0 + 10, seat_y - 96, x1 - 10, seat_y - 80, col, r=3)
    for lx in (x0 + 30, x1 - 30):
        cv.rect(lx - 5, seat_y - 96, lx + 5, seat_y, col)

def knock_hero(cv, tl, e=1.0, base_kw=None):
    """front hero knocking; e blends from base_kw pose (e=0) to the knock pose (e=1)"""
    rA, lA, aR, aL = knock_arms(tl)
    kw = dict(yaw=1.0, eye_k=1.5, eye_hl=True, head_tilt=-3 * math.sin(2 * math.pi * 2 * tl), legs="sit_f", rise=1.0)
    if base_kw and e < 1:
        b = base_kw
        def mixarm(A, B):
            return (_lv2(A[0], B[0], e), _lv2(A[1], B[1], e))
        kw.update(rise=e, head_tilt=lerp(b.get("head_tilt", 0), kw["head_tilt"], e))
        kw["rarm"] = mixarm(b["rarm"], rA); kw["larm"] = mixarm(b["larm"], lA)
        kw["rshape"] = b.get("rshape", "fist") if e < 0.5 else "fist"
        kw["lshape"] = b.get("lshape") if e < 0.5 else None
        aR *= e; aL *= e
    else:
        kw["rarm"] = rA; kw["larm"] = lA
    r = hero(cv, HERO_X, HERO_Y, HERO_S, **kw)
    out = []
    for (pos, a) in ((r["hand"], aR), (r["lhand"], aL)):
        rr = 8.5 * HERO_S * (1 + 0.6 * a)
        if e > 0.3: fist_front(cv, pos[0], pos[1] - 4 * a, rr)
        out.append(cv.to_screen(*pos))
    return out

def _lv2(a, b, t): return (lerp(a[0], b[0], t), lerp(a[1], b[1], t))

def ripples(cv, tl, fists_screen, t_from=-1e9):
    """white rings on the glass at each knock (screen space)"""
    cv.screen()
    for tk in knock_times(max(t_from, tl - 0.75), tl):
        if tk < t_from: continue
        u = (tl - tk) / 0.75
        if not (0 <= u < 1): continue
        j = int(round(tk / 0.25)) % 2
        x, y = fists_screen[j]
        r = 18 + 175 * u ** 0.6
        ring(cv, x, y, r, r, (255, 255, 255), 5 - 3 * u, 215 * (1 - u) ** 1.6)
        ring(cv, x, y, r * 0.62, r * 0.62, (255, 255, 255), 3, 120 * (1 - u) ** 2)

def s1(cv, lt, D, t):
    tl = t
    push = 1 + 0.04 * ease_io(lt / D)
    cv.oy = bump(tl, knock_times(0, tl), amp=4.0, decay=0.05, freq=22)
    cv.ox = 0.6 * cv.oy
    cv.set_cam(CAM1[0], CAM1[1], CAM1[2] * push)
    street_world(cv, tl)
    cv.layer(1.0)
    bench(cv, 372, 718, HERO_Y - 92 * HERO_S, K["L5"])
    fists = knock_hero(cv, tl)
    ripples(cv, tl, fists, t_from=0.0)
    cv.screen(); glass_glare(cv, 150 + 320 * tl)
    return dict(obunachi=1.0)

def s20(cv, lt, D, t):
    tl = t - TOTAL_T                       # negative: continuous into frame 0
    e = smooth(D - 0.5, D - 1.0 / FPS, lt)
    cam = zoom_cam(CAM20, CAM1, e)
    cv.set_cam(*cam)
    # comment bubble cloud above the hero (fades during the final push-in)
    form = smooth(0.15, 1.1, lt)
    def bubble(cv_):
        cv_.layer(0.3)
        a = 1 - e
        if a <= 0.01: return
        col = lerpc(K["sky1"], (255, 255, 255), 0.55) + (int(255 * a),)
        cx, cy = 560 + 6 * math.sin(lt * 1.3), 470
        rnd = random.Random(3)
        # irregular cloud lumps tighten into a rounded bubble
        for k_ in range(8):
            ang = 2 * math.pi * k_ / 8
            rr = lerp(rnd.uniform(60, 95), 92, form)
            d_ = lerp(rnd.uniform(90, 130), 60, form)
            cv_.circle(cx + d_ * math.cos(ang) * 1.5, cy + d_ * math.sin(ang) * 0.75, rr, col)
        cv_.rect(cx - lerp(170, 150, form), cy - 70, cx + lerp(170, 150, form), cy + 70, col, r=60)
        tail = [(cx - 40, cy + 70), (cx + 10, cy + 70), (cx - 70, cy + 70 + 70 * form)]
        cv_.poly(tail, col)
        if form > 0.5:
            for j in range(3):
                bb = abs(math.sin(2 * math.pi * 1.6 * lt - j * 0.9)) * 16
                cv_.circle(cx - 60 + 60 * j, cy - bb + 4, 15, K["L5"] + (int(255 * a * smooth(0.5, 0.8, form)),))
    street_world(cv, tl, bubble=bubble)
    cv.layer(1.0)
    bench(cv, 372, 718, HERO_Y - 92 * HERO_S, K["L5"])
    base_kw = dict(rarm=RA["chest"], rshape="flat", larm=((40, -206), (34, -160)), head_tilt=4 * math.sin(lt * 1.7) - 4)
    if e <= 0:
        hero(cv, HERO_X, HERO_Y, HERO_S, yaw=1.0, legs="sit_f", rise=0.0, eye_k=1.25, **base_kw)
        fists = None
    else:
        fists = knock_hero(cv, tl, e, base_kw=base_kw)
    if e > 0:
        cv.screen(); glass_glare(cv, 150 + 320 * tl, alpha=e)
    return dict(obunachi=e, bubble_form=form)

TOTAL_T = 38.0

# ================================================================ scene 2: bus stop
def s2(cv, lt, D, t):
    u = lt / D
    cv.set_cam(lerp(470, 640, ease_io(u)), 960, 1.0)
    cv.layer(1.0); sky(cv, K["sky0"], K["sky1"], 0, 1100)
    cv.layer(0.12); mountains(cv, 900, 210, K["L1"], seed=12)
    cv.layer(0.3)
    rnd = random.Random(9); x = -500
    while x < 1900:
        poplar(cv, x, 1000, rnd.uniform(240, 340), rnd.uniform(44, 60), K["L2"], sway=sway_x(lt, 6, x * 0.02))
        x += rnd.uniform(70, 110)
    cv.rect(-1500, 990, 2800, 3000, K["L2"])
    cv.layer(0.55)
    for (x0, x1, top) in ((-400, -40, 930), (0, 380, 950), (600, 980, 935), (1040, 1400, 955), (1440, 1800, 930)):
        mid = lerpc(K["L3"], K["L4"], 0.5)
        house(cv, x0, x1, top, 1100, K["L3"], beam=mid, wins=[(x0 + 50, top + 46, 30, 40), (x1 - 80, top + 46, 30, 40)], win_col=mid)
    cv.rect(-1500, 1100, 2800, 3000, lerpc(K["L2"], K["L3"], 0.4))
    cv.layer(1.0)
    G = 1270.0
    L4, L5 = K["L4"], K["L5"]
    # bus stop shelter (behind the hero)
    sx = 860; SG = G - 54
    cv.rect(sx - 10, 930, sx + 360, 952, L5, r=4)
    for px in (sx + 10, sx + 330):
        cv.rect(px - 7, 940, px + 7, SG, L5)
    cv.rect(sx + 26, 970, sx + 316, 1100, L5 + (150,))
    cv.rect(sx + 40, 1120, sx + 300, 1134, L5); cv.rect(sx + 60, 1134, sx + 72, SG, L5); cv.rect(sx + 268, 1134, sx + 280, SG, L5)
    cv.rect(sx - 70, 880, sx - 62, SG, L5); cv.circle(sx - 66, 880, 34, L5)
    cv.rect(sx - 84, 868, sx - 48, 892, lerpc(L4, K["L3"], 0.5), r=6)
    # sidewalk (where people walk) and kerb
    cv.rect(-1500, G - 66, 2800, 3000, L4)
    cv.rect(-1500, G - 4, 2800, G + 8, L5)
    cv.rect(-1500, G + 8, 2800, 3000, lerpc(L4, L5, 0.35))
    for xx in range(-1500, 2800, 240):
        cv.rect(xx, G + 300, xx + 120, G + 308, lerpc(L4, K["L3"], 0.6))
    # passers-by (behind the hero, left -> right, nobody turns; the middle one slows and glances)
    walkers = [(-260, 300, "cap", "pants"), (-620, 330, "scarf", "skirt"), (-980, 290, "doppi", "coat")]
    for i, (x0, v, hat, dress) in enumerate(walkers):
        if i == 1:
            pos = _integ_slow(lt)
            xs = x0 + v * pos
            look = smooth(0.8, 0.95, lt) * (1 - smooth(1.25, 1.4, lt))
            ph = 2 * math.pi * 1.7 * pos
            walk = 0.45 + 0.55 * (1 - 0.75 * math.exp(-((lt - 1.05) / 0.32) ** 2))
        else:
            xs = x0 + v * lt; look = 0.0; ph = 2 * math.pi * 1.7 * lt + i; walk = 1.0
        person(cv, xs + 540, G - 36, 0.82, lerpc(L5, L4, 0.25), dir=1, walk=walk, phase=ph, look=look, hat=hat, dress=dress)
    # hero at the kerb, holding up the heart balloon
    hx_, hs = 520, 1.0
    bob = math.sin(2 * math.pi * 0.9 * lt)
    r = hero(cv, hx_, G, hs, dir=-1, rarm=((22, -330), (16, -404)), rshape="fist", head_tilt=-6, look=-0.3)
    hand = r["hand"]
    bx = hand[0] - 40 + 22 * math.sin(2 * math.pi * 0.55 * lt); by = hand[1] - 230 + 12 * bob
    cv.line([hand, ((hand[0] + bx) / 2 + 10 * math.sin(lt * 3), (hand[1] + by) / 2), (bx, by + 40)], hx("E8E1D3"), 2.2)
    cv.poly(heart_pts(bx, by, 52), ACCENT)
    cv.poly(ellipse_pts(bx - 22, by - 16, 9, 14, 12, ang=30), lerpc(ACCENT, (255, 240, 225), 0.45))
    cv.poly([(bx - 6, by + 44), (bx + 6, by + 44), (bx, by + 52)], ACCENT)
    leaves(cv, lt, 9, (-400, 1050, 900, 1450), L5, seed=4, wind=(330, 40), size=8, life=2.4)
    return {}

def _integ_slow(lt):
    # integral of the walker-1 speed factor (1 - 0.75 * gauss) -> position stays continuous
    n = 40; acc = 0.0; dt = lt / n if lt > 0 else 0
    for i in range(n):
        x = (i + 0.5) * dt
        acc += (1 - 0.75 * math.exp(-((x - 1.05) / 0.32) ** 2)) * dt
    return acc

# ================================================================ scene 3: kneeling on the steppe road
def s3(cv, lt, D, t):
    u = ease_io(lt / D)
    G = 1290.0
    cv.set_cam(lerp(560, 480, u), lerp(960, G - 320 / 1.55, u), lerp(1.0, 1.55, u))
    cv.layer(1.0); sky(cv, K["sky0"], K["sky1"], 0, 1100)
    cv.layer(0.05); draw_sun(cv, 820, 330, 95, K["sun0"], K["sun1"])
    cv.layer(0.1); mountains(cv, 960, 250, K["L1"], seed=44)
    cv.layer(0.25); ridge(cv, 1040, 70, K["L2"], seed=3, wl=(800, 300, 120))
    cv.layer(0.5)
    ridge(cv, 1130, 40, K["L3"], seed=5, wl=(900, 400, 150))
    grass(cv, -600, 1700, 1130, K["L3"], lt, h=22, n=110, seed=2, wind=1.6)
    # fence with a crow
    cv.layer(0.75)
    fy = 1215
    for px in range(-500, 1800, 190):
        cv.rect(px - 6, fy - 140, px + 6, fy, K["L4"])
    for wy in (fy - 118, fy - 70):
        cv.line([(-520, wy), (1820, wy + 6)], K["L4"], 2.0, caps=False)
    post = (-500 + 190 * 7, fy - 140)
    tc = 0.55
    if lt < tc:
        bird_perch(cv, post[0], post[1] - 1, 1.1, K["L5"], dir=-1, peck=0.5 * abs(math.sin(lt * 9)), kind="crow")
    else:
        v = lt - tc
        bird_fly(cv, post[0] + 240 * v + 60 * v * v, post[1] - 150 * v - 120 * v * v, 1.7 + 0.5 * v, math.sin(2 * math.pi * 5 * v), K["L5"])
    # dirt road
    cv.layer(1.0)
    cv.rect(-1500, G - 60, 2800, 3000, lerpc(K["L2"], K["L3"], 0.3))
    cv.rect(-1500, G - 60, 2800, G - 50, K["L3"])
    for xx in range(-1500, 2800, 120):
        cv.poly(ellipse_pts(xx + 40, G + 60 + 22 * math.sin(xx), 34, 5, 10), lerpc(K["L2"], K["L3"], 0.55))
    # hero kneeling, palms together, rocking
    rock = math.sin(2 * math.pi * 1.25 * lt)
    hero(cv, 470, G, 1.05, legs="kneel", bow=4 + 4 * rock, head_tilt=-8 + 3 * rock,
         rarm=((46, -232), (64, -270)), larm=((48, -234), (64, -270)), rshape="flat", lshape="flat", rangle=-80)
    dust(cv, lt, 26, (-500, 1050, 900, 1350), lerpc(K["L2"], K["L1"], 0.4), seed=11, wind=(420, -30), size=(3, 9), alpha=150, life=1.6)
    cv.layer(1.25)
    grass(cv, -400, 1500, 1800, K["L5"], lt, h=70, n=46, seed=9, wind=2.2, w=9)
    return {}

# ================================================================ scene 4: billboard with the PODPISKA button
def s4(cv, lt, D, t):
    u = ease_io(lt / D)
    cv.set_cam(560, lerp(990, 900, u), 1.0)
    cv.layer(1.0); sky(cv, K["sky0"], K["sky1"], -200, 1300)
    cv.layer(0.1)
    cloud(cv, 220 + 14 * lt, 330, 260, lerpc(K["sky1"], (255, 255, 255), 0.4))
    cloud(cv, 900 + 10 * lt, 210, 200, lerpc(K["sky1"], (255, 255, 255), 0.3), seed=6)
    cv.layer(0.25)
    rnd = random.Random(2); x = -300
    while x < 1500:
        poplar(cv, x, 1330, rnd.uniform(180, 260), rnd.uniform(36, 50), K["L2"], sway=sway_x(lt, 5, x * 0.03))
        x += rnd.uniform(55, 85)
    cv.rect(-1000, 1310, 2400, 3000, K["L2"])
    cv.layer(0.5)
    for (x0, x1, top) in ((-200, 160, 1250), (240, 520, 1270), (880, 1260, 1260)):
        house(cv, x0, x1, top, 1380, K["L3"], beam=lerpc(K["L3"], K["L4"], 0.5))
    cv.rect(-1000, 1380, 2400, 3000, K["L3"])
    cv.layer(1.0)
    L4, L5 = K["L4"], K["L5"]
    G = 1300.0
    cv.rect(-1000, G, 2400, 3000, L4)
    # billboard
    bx0, bx1, by0, by1 = 300, 1000, 300, 690
    for px in (420, 860):
        cv.rect(px - 14, by1 - 10, px + 14, G, L5)
        cv.line([(px - 14, by1 + 110), (px + 50, by1 + 10)], L5, 7)
    cv.rect(bx0 - 10, by0 - 10, bx1 + 10, by1 + 10, L5, r=8)
    cv.rect(bx0 + 10, by0 + 10, bx1 - 10, by1 - 10, lerpc(L5, L4, 0.35), r=6)
    cv.rect(bx0 + 40, by1 + 6, bx1 - 40, by1 + 16, L5)
    pulse = 1 + 0.035 * math.sin(2 * math.pi * 1.6 * lt)
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    bw, bh = 520 * pulse, 190 * pulse
    cv.rect(cx - bw / 2, cy - bh / 2 + 12, cx + bw / 2, cy + bh / 2 + 12, lerpc(ACCENT, L5, 0.55), r=bh / 2)
    cv.rect(cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2, ACCENT, r=bh / 2)
    cv.rect(cx - bw / 2 + 30, cy - bh / 2 + 14, cx + bw / 2 - 30, cy - bh / 2 + 34, lerpc(ACCENT, (255, 236, 220), 0.25), r=10)
    wtext(cv, "PODPISKA", cx, cy + 4, 86 * pulse, CREAM_N, FONT_BLACK, track=0.02)
    # sparrows on the top edge
    for i, (sx_, ph) in enumerate(((360, 0.0), (430, 1.3), (900, 2.2))):
        hop = max(0, math.sin(2 * math.pi * 1.1 * lt + ph)) ** 6 * 14 if i == 1 else 0
        bird_perch(cv, sx_, by0 - 10 - hop, 1.0, L5, dir=1 if i < 2 else -1, peck=max(0, math.sin(2 * math.pi * 1.7 * lt + ph)) ** 4)
    # hero: points at the button, then turns and points at the viewer
    turn = smooth(0.85, 1.15, lt)
    hs = 1.35; HX = 300
    if turn < 1:
        up_arm = ((36, -318), (70, -372))
        r = hero(cv, HX, G, hs, dir=1, yaw=0.0, hyaw=turn, rarm=up_arm, rshape="point", rangle=-58, head_tilt=-14 * (1 - turn))
    else:
        k = smooth(1.15, 1.3, lt)
        r = hero(cv, HX, G, hs, dir=1, yaw=1.0, rarm=((-52, -250), (-26, -270)), rshape="fist", eye_k=1.2,
                 head_tilt=2 * math.sin(lt * 4))
        hp = r["hand"]
        rr = 8.5 * hs * (1 + 0.7 * k)
        fist_front(cv, hp[0], hp[1], rr)
        cv.circle(hp[0] + rr * 0.15, hp[1] - rr * 0.1, rr * 0.42, Q.SKIN)
        cv.circle(hp[0] + rr * 0.15, hp[1] - rr * 0.1, rr * 0.2, Q.SKIN_D)
    return {}

POP_T4 = 1.15
