# The 13 scenes. Each scene function draws into a skia canvas for global time t.
import math
import numpy as np
import skia
from style import *
from figures import *
from figures import _legs_walk
from world import *
from timeline import *

INFO = {}        # per-frame info: hero bbox on screen, key action boxes (for subtitle placement + QA)

def _hbox(cam, info, d=1.0):
    x0, y0, x1, y1 = info["bbox"]
    pts = [cam.to_screen(p, d) for p in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
    box = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
    INFO.setdefault("heroes", []).append(box)
    return box

# ================================================================== scene 1 (hook) + loop end
S1 = 3.2                       # hero scale: ~323 px tall = 1/6 of the frame
WALK_T = 0.95
OMEGA = 2 * math.pi / WALK_T
V1 = 90.1 * S1                 # px/s, matches the stance-foot speed (no foot sliding)
HX0, HY = 150.0, 1335.0
T_FREEZE = 0.70
PH_FREEZE = -1.25
PH0 = PH_FREEZE - OMEGA * T_FREEZE

def hook_state(t):
    tw = min(t, T_FREEZE)
    hx_ = HX0 + V1 * tw
    ph = PH0 + OMEGA * tw
    return hx_, ph

def scene1(cv, t, u=0.0, loop_end=False):
    P = pal(u)
    hx_, ph = hook_state(t)
    camx = V1 * min(t, T_FREEZE)
    k = ease_out(ramp(t, T_FREEZE, T_FREEZE + 0.22))
    z = 1 + 0.05 * k + 0.014 * ease_io(ramp(t, 0.95, 4.2))
    dt = t - T_FREEZE
    shake = 7.0 * math.exp(-dt * 11) * math.sin(dt * 80) if dt > 0 else 0.0
    grab = (HX0 - 40, 1165)
    cam = Cam(x=camx, z=z, fx=grab[0], fy=grab[1], sx=shake, sy=0.45 * shake)
    def birds(c):
        flock(c, t, -0.5, 4.5, -150, 1250, 430, 3, 1.6, P["L4"], seed=2, facing=1)
    street(cv, P, cam, t, u=u, sun=(360, 700 + 3 * t, 200), birds=birds)
    # hero
    cam.push(cv, 1.0)
    frozen = t >= T_FREEZE
    pose = dict(walk=1.0, ph=ph, facing=1)
    if frozen:
        a = 27 * math.sin(ph); legs0 = _legs_walk(ph, 1.0)
        st = [(-11.0, 5.0), (9.0, 7.0)]
        e = ease_io(ramp(t, 1.7, 2.5))
        legs = [(lerp(l0[0], s_[0], e), lerp(l0[1], s_[1], e)) for l0, s_ in zip(legs0, st)]
        armN0 = (-20 * math.sin(ph) + 3, 18 + 8 * max(0, -math.sin(ph)))
        en = ease_io(ramp(t, 1.8, 2.6))
        pose.update(legs=legs, armN=(lerp(armN0[0], 4, en), lerp(armN0[1], 16, en)),
                    armF=(-36 - 5 * ease_out(ramp(t, 0.7, 0.85)), 8), handF="relax",
                    tugF=(-2.6 * ease_out(ramp(t, 0.7, 0.86)), 0.6), lean=-3.0 * ease_out(ramp(t, 0.7, 0.9)),
                    head=165 * ease_io(ramp(t, 1.0, 1.4)), tilt=6 * ease_io(ramp(t, 1.2, 1.6)),
                    breath=math.sin(t * 2.4))
    info = hero(cv, hx_, HY, S1, pose)
    # mother's arm enters from the left edge and grabs the sleeve at 0.7 s
    if t > T_FREEZE - 0.16:
        tgt = info["hand_f"]
        e = ease_out(ramp(t, T_FREEZE - 0.16, T_FREEZE))
        sh = (tgt[0] - 128 - 160 * (1 - e), tgt[1] - 50)
        aim = (lerp(sh[0] + 70, tgt[0] - 6, e), lerp(sh[1] + 30, tgt[1] - 6, e))
        if t >= T_FREEZE: aim = (tgt[0] - 7 - 1.5 * math.sin(t * 3), tgt[1] - 6)
        mother_arm_in(cv, sh[0], sh[1], aim, 4.2, P["L5"])
    cv.restore()
    street_fg(cv, P, cam, t)
    INFO["hero"] = _hbox(cam, info)
    return cam

def L(k, t): return t - SC_START[k]
def DUR(k): return SC_END[k] - SC_START[k]
T_BACK0 = 27.45            # imagined future dissolves back to reality inside scene 11
T_BACK1 = 27.95
ROT0 = 32.70               # scene 13 rotation start
ROT1 = (N_FRAMES - 1) / FPS
def palette_u(t):
    if t < SC_START[6]: return 0.0
    if t < SC_START[7]: return ease_io(ramp(t, SC_START[6] + 0.15, SC_END[6] - 0.25))
    if t < ROT0: return 1.0
    return 1.0 - ease_io(ramp(t, ROT0 + 0.05, ROT1 - 0.12))

def layer_alpha(cv, a):
    p = skia.Paint(); p.setAlphaf(clamp01(a)); cv.saveLayer(None, p)

# ================================================================== scene 2: yard, so'ri, side by side
YM = dict(mx=380, hx=720, seat=1290, sm=4.4, sh=4.6)
def sori_pair(cv, P, t, hero_head=0.0, hero_tilt=0.0, mother_tilt=0.0, hand_on=0.0, breath_t=None, hero_lean=0.0):
    bt = t if breath_t is None else breath_t
    sori_back(cv, P, SORI["x0"], SORI["x1"], YM["seat"])
    info = hero(cv, YM["hx"], YM["seat"], YM["sh"], dict(mode="sit", facing=-1, head=hero_head, tilt=hero_tilt,
                                                         breath=math.sin(bt * 2.2), lean=hero_lean))
    if hand_on > 0:
        sh = info["shoulder_n"]; tgt = (sh[0] - 2, sh[1] - 9 - 60 * (1 - hand_on))
        rest = (YM["mx"] + 19 * YM["sm"], YM["seat"] - 11 * YM["sm"])
        e = ease_io(hand_on)
        mother_sit(cv, YM["mx"], YM["seat"], YM["sm"], P["L5"], facing=1, tilt=mother_tilt,
                   arm_target=(lerp(rest[0], tgt[0], e), lerp(rest[1], tgt[1] + 60 * (1 - hand_on), e)))
    else:
        mother_sit(cv, YM["mx"], YM["seat"], YM["sm"], P["L5"], facing=1, tilt=mother_tilt)
    sori_front(cv, P, SORI["x0"], SORI["x1"], YM["seat"])
    return info

def scene2(cv, t):
    lt = L(2, t); P = pal(0)
    cam = Cam(x=lerp(60, -60, ease_io(lt / DUR(2))), z=1.3, fx=540, fy=1250)
    def birds(c):
        flock(c, t, SC_START[2] - 0.2, SC_END[2] + 0.2, 1250, -250, 500, 6, 1.7, P["L4"], seed=6, facing=-1)
    yard_side(cv, P, cam, t, sun=(790, 935, 160), birds=birds)
    cam.push(cv, 1.0)
    ta = word(2, "aytdilar")
    info = sori_pair(cv, P, t, hero_head=180 * (1 - ease_io(ramp(t, ta - 0.1, ta + 0.32))),
                     mother_tilt=-16 * (1 - ease_io(ramp(lt, 0.2, 0.6))) + 2.5 * math.sin(t * 9) * ramp(t, ta - 0.6, ta),)
    cv.restore()
    yard_fg(cv, P, cam, t)
    INFO["hero"] = _hbox(cam, info)

# ================================================================== close yard background (scenes 3 and 6)
def yard_close_bg(cv, P, cam, t, sun=None, moon=None, star_a=0.0, win_a=0.0, birds=None, wall_top=1300):
    cam.push(cv, 0.3); sky(cv, P, y0=-200, y1=wall_top)
    stars(cv, t, star_a, ymax=wall_top - 100)
    if moon: draw_disc(cv, "moon", moon[0], moon[1], moon[2], alpha=moon[3], glow=1.0)
    if birds: birds(cv)
    cv.restore()
    cam.push(cv, 0.32); fill(cv, ridge_path(-2000, 3200, wall_top - 110, 90, 340, 15), P["haze"]); cv.restore()
    cam.push(cv, 0.45)
    if sun: draw_disc(cv, "sun", *sun, glow=0.7)
    cv.restore()
    cam.push(cv, 0.38)
    rs = np.random.RandomState(51); x = -1500
    while x < 2600:
        if rs.rand() < 0.5 and not (180 < x < 680):
            for k in range(rs.randint(2, 4)):
                poplar(cv, x + k * 40, wall_top + 10, rs.uniform(260, 420), rs.uniform(46, 62), P["L2"])
            x += rs.uniform(200, 320)
        else:
            w = rs.uniform(160, 300); flat_house(cv, x, x + w, wall_top + 10, rs.uniform(80, 150), P["L2"]); x += w + rs.uniform(20, 80)
    cv.restore()
    cam.push(cv, 0.42)
    hx0, hx1, top = 760, 1240, wall_top - 210
    cv.drawRect(skia.Rect.MakeLTRB(hx0, top, hx1, wall_top + 10), paint(P["mid"]))
    cv.drawRect(skia.Rect.MakeLTRB(hx0 - 24, top - 16, hx1 + 24, top + 4), paint(P["L4"], 0.8))
    wx0, wy0, wx1, wy1 = hx0 + 90, top + 50, hx0 + 200, top + 165
    cv.drawRect(skia.Rect.MakeLTRB(wx0 - 9, wy0 - 9, wx1 + 9, wy1 + 9), paint(P["L4"], 0.8))
    cv.drawRect(skia.Rect.MakeLTRB(wx0, wy0, wx1, wy1), paint(mix(P["L4"], P["mid"], 0.4)))
    if win_a > 0:
        glow(cv, (wx0 + wx1) / 2, (wy0 + wy1) / 2, 120, P["win"], 0.45 * win_a)
        cv.drawRect(skia.Rect.MakeLTRB(wx0, wy0, wx1, wy1), paint(P["win"], win_a))
    cv.drawRect(skia.Rect.MakeLTRB((wx0 + wx1) / 2 - 3.5, wy0, (wx0 + wx1) / 2 + 3.5, wy1), paint(P["L4"]))
    cv.drawRect(skia.Rect.MakeLTRB(wx0, (wy0 + wy1) / 2 - 3.5, wx1, (wy0 + wy1) / 2 + 3.5), paint(P["L4"]))
    cv.restore()
    cam.push(cv, 0.5); wall_band(cv, P, -2000, 3200, wall_top, 4200, c=P["L3"], seed=12); cv.restore()

# ================================================================== scene 3: hand on shoulder, tilt to the empty palm
S3 = dict(hx=800, mx=450, seat=1760, sh=11.5, sm=11.5)
ARM3 = (-10, 100)
_DRY = {}
def _palm_world():
    if "p3" not in _DRY:
        sf = skia.Surface(64, 64)
        inf = hero(sf.getCanvas(), S3["hx"], S3["seat"], S3["sh"], dict(mode="sit", facing=-1, armN=ARM3, handN="palm_top"))
        T = inf["T"]; hx_, hy_ = inf["hand_n"]
        _DRY["p3"] = (hx_ - 3.5 * S3["sh"], hy_ - 0.5 * S3["sh"])
    return _DRY["p3"]

def scene3(cv, t):
    lt = L(3, t); P = pal(0)
    tm = word(3, "moliyaviy")
    e = ease_io(ramp(t, tm, tm + 0.45))
    palm = _palm_world()
    z1 = 1.35; f = (540, 960); target = (520, 1120)
    c1 = (palm[0] - f[0] - (target[0] - f[0]) / z1, palm[1] - f[1] - (target[1] - f[1]) / z1)
    c0 = (40.0, 305.0)
    z0 = 1.15 + 0.03 * ease_io(ramp(lt, 0, tm - SC_START[3]))
    cam = Cam(x=lerp(c0[0], c1[0], e), y=lerp(c0[1], c1[1], e), z=lerp(z0, z1, e), fx=f[0], fy=f[1])
    yard_close_bg(cv, P, cam, t, sun=(500, 1330, 230), wall_top=1330)
    cam.push(cv, 1.0)
    sori_back(cv, P, -100, 1200, S3["seat"], s=2.3)
    mother_sit(cv, S3["mx"], S3["seat"], S3["sm"], P["L5"], facing=1, tilt=2 + 3 * math.sin(t * 7) * ramp(t, word(3, "uylanishdan"), 9.6),
               draw_arm=False)
    ea = ease_io(ramp(t, tm - 0.3, tm + 0.2))
    armN = (lerp(14, ARM3[0], ea), lerp(55, ARM3[1], ea))
    info = hero(cv, S3["hx"], S3["seat"], S3["sh"], dict(mode="sit", facing=-1, head=0, armN=armN,
                handN="palm_top" if ea > 0.5 else "relax", tilt=18 * ease_io(ramp(t, tm - 0.1, tm + 0.4)) - 3 * ease_io(ramp(lt, 0.05, 0.4)),
                breath=math.sin(t * 2.2)))
    sh = info["shoulder_n"]
    settle = ease_out(ramp(lt, 0.0, 0.4))
    pat = 4 * math.sin(clamp01((lt - 0.45) / 0.5) * math.pi * 2) * (1 if 0.45 < lt < 0.95 else 0)
    mother_arm(cv, S3["mx"], S3["seat"], S3["sm"], 1, (sh[0] + 6, sh[1] - 16 - 30 * (1 - settle) - pat), P["L5"])
    sori_front(cv, P, -100, 1200, S3["seat"], s=2.3, leg=200)
    # dry leaf carried by the wind past the open palm
    lu = ramp(t, tm + 0.55, tm + 1.85)
    if 0 < lu < 1:
        lx = palm[0] - 600 + 1200 * lu
        ly = palm[1] - 80 + 40 * math.sin(lu * 7.5) - 30 * lu
        cv.save(); cv.translate(lx, ly); cv.rotate(lu * 720 + 30); cv.scale(1.0, 0.55 + 0.45 * math.cos(lu * 19))
        fill(cv, smooth([(-34, 0), (-12, -13), (24, -9), (36, 0), (24, 9), (-12, 13)], k=0.5), mix(P["L4"], hx("#6B5A4A"), 0.6))
        cv.drawPath(poly([(-46, 0), (30, 0)], closed=False), paint(mix(P["L5"], hx("#6B5A4A"), 0.4), stroke=2.5))
        cv.restore()
    cv.restore()
    cam.push(cv, 1.4); branch(cv, P, -60, -40, 1.3, t, mirror=True, seed=7, wind=0.6); cv.restore()
    INFO["hero"] = _hbox(cam, info)
    INFO["palm"] = cam.to_screen(palm)

# ================================================================== scene 4: from behind, the grand house appears and dissolves
def grand_house(cv, x, base, c, a):
    if a <= 0.01: return
    layer_alpha(cv, a)
    w = 640; h = 250
    cv.drawRect(skia.Rect.MakeLTRB(x - w / 2, base - h, x + w / 2, base), paint(c))
    cv.drawRect(skia.Rect.MakeLTRB(x - w / 2 - 14, base - h - 14, x + w / 2 + 14, base - h + 4), paint(c))
    cv.drawRect(skia.Rect.MakeLTRB(x - 120, base - h - 70, x + 120, base - h), paint(c))       # upper pavilion
    cv.drawPath(poly([(x - 140, base - h - 70), (x, base - h - 120), (x + 140, base - h - 70)]), paint(c))
    for side in (-1, 1):                                                                         # wings
        cv.drawRect(skia.Rect.MakeLTRB(x + side * w / 2 - (90 if side > 0 else 0), base - h - 40, x + side * w / 2 + (0 if side > 0 else 90), base), paint(c))
    lt_c = mix(c, (1, 1, 1), 0.28)
    for row in range(2):
        for k in range(9):
            wx = x - w / 2 + 40 + k * 68; wy = base - h + 40 + row * 100
            cv.drawPath(rrect(wx, wy, wx + 30, wy + 50, 12), paint(lt_c))
    for k in range(7):                                                                           # ayvon columns
        cx = x - 210 + k * 70; cv.drawRect(skia.Rect.MakeLTRB(cx - 5, base - 70, cx + 5, base), paint(lt_c))
    # high gate with an arch
    gx = x; cv.drawRect(skia.Rect.MakeLTRB(gx - 260, base - 40, gx + 260, base + 20), paint(c))
    cv.drawPath(poly([(gx - 70, base + 20), (gx - 70, base - 110), (gx, base - 160), (gx + 70, base - 110), (gx + 70, base + 20)]), paint(c))
    cv.drawRect(skia.Rect.MakeLTRB(gx - 82, base - 120, gx - 62, base + 20), paint(c))
    cv.drawRect(skia.Rect.MakeLTRB(gx + 62, base - 120, gx + 82, base + 20), paint(c))
    cv.restore()

def scene4(cv, t):
    lt = L(4, t); P = pal(0)
    cam = Cam(z=1 + 0.07 * ease_io(lt / DUR(4)), fx=540, fy=1080)
    cam.push(cv, 0.0); sky(cv, P, y0=-100, y1=1100); draw_disc(cv, "sun", 860, 1000, 150, glow=0.6); cv.restore()
    cam.push(cv, 0.03); fill(cv, ridge_path(-2000, 3000, 1080, 110, 420, 21), P["haze"]); cv.restore()
    td = word(4, "shart")
    a_in = ease_io(ramp(t, SC_START[4] + 0.05, SC_START[4] + 0.6)); a_out = ease_io(ramp(t, td, td + 0.85))
    a = a_in * (1 - a_out)
    cam.push(cv, 0.05)
    cv.save(); cv.translate(0, -30 * a_out)
    grand_house(cv, 540, 1075, mix(P["L1"], P["L2"], 0.45), a)
    cv.restore()
    if 0 < a_out < 1:   # dissolving specks drifting up and away
        rs = np.random.RandomState(3)
        for k in range(70):
            px = rs.uniform(220, 860); py = rs.uniform(800, 1070)
            d = ease_out(a_out) * rs.uniform(40, 160)
            al = (1 - a_out) * rs.uniform(0.3, 0.8) * a_out * 3
            cv.drawCircle(px + d * 0.8, py - d, rs.uniform(2, 5), paint(mix(P["L1"], P["L2"], 0.45), clamp01(al)))
    cv.restore()
    cam.push(cv, 0.07); fill(cv, ridge_path(-2000, 3000, 1120, 50, 260, 22), P["L1"]); cv.restore()
    cam.push(cv, 0.14)
    rs = np.random.RandomState(61); x = -900
    while x < 2000:
        w = rs.uniform(70, 150); flat_house(cv, x, x + w, 1150, rs.uniform(30, 80), P["L2"]); x += w + rs.uniform(5, 40)
        if rs.rand() < 0.3: poplar(cv, x, 1150, rs.uniform(120, 200), 28, P["L2"]); x += 30
    cv.restore()
    cam.push(cv, 0.26)
    rs = np.random.RandomState(62); x = -900
    while x < 2000:
        w = rs.uniform(110, 220); flat_house(cv, x, x + w, 1230, rs.uniform(50, 110), P["mid"], chimney=x + 30 if rs.rand() < 0.25 else None); x += w + rs.uniform(10, 50)
    smoke(cv, 300, 1150, t, P["smoke"], a=0.45, s=0.8, seed=5)
    cv.restore()
    cam.push(cv, 0.5)
    wall_band(cv, P, -1500, 2600, 1290, 1420, c=P["L3"], seed=14)
    leafy_tree(cv, 960, 1420, 1.25, P["L4"], seed=8, sway=3 * math.sin(t))
    cv.restore()
    cam.push(cv, 1.0)
    cv.drawRect(skia.Rect.MakeLTRB(-2000, 1410, 3000, 4200), paint(P["earth"]))
    cv.drawRect(skia.Rect.MakeLTRB(170, 1478, 900, 1506), paint(P["L5"]))
    for x in (190, 535, 880):
        cv.drawRect(skia.Rect.MakeLTRB(x - 12, 1478, x + 12, 1600), paint(P["L5"]))
    mother_back_sit(cv, 400, 1480, 5.0, P["L5"])
    info = hero_back_sit(cv, 650, 1480, 5.3, look=6 * math.sin(lt * 1.3))
    cv.restore()
    cam.push(cv, 1.25); ground_strip(cv, P, -3000, 4200, 1585, P["L5"], seed=9); cv.restore()
    INFO["hero"] = _hbox(cam, info)

# ================================================================== scene 5: high three-quarter view of the modest yard
def scene5(cv, t):
    lt = L(5, t); P = pal(0)
    e = ease_io(lt / DUR(5))
    cam = Cam(y=lerp(-50, 40, e), z=lerp(1.0, 1.07, e), fx=540, fy=1150)
    cam.push(cv, 0.2); sky(cv, P, y0=-100, y1=480); draw_disc(cv, "sun", 190, 390, 120, glow=0.6); cv.restore()
    cam.push(cv, 0.25); fill(cv, ridge_path(-1500, 2600, 470, 80, 300, 31), P["haze"]); cv.restore()
    cam.push(cv, 0.35)
    rs = np.random.RandomState(71)
    for row, (y0, col_top, col_front) in enumerate(((470, P["L1"], P["L2"]), (560, P["L2"], P["mid"]), (660, P["L2"], P["mid"]))):
        x = -300 + row * 37
        while x < 1500:
            w = rs.uniform(120, 260); d = rs.uniform(40, 70); hh = rs.uniform(26, 50)
            fill(cv, poly([(x, y0), (x + w, y0), (x + w + 20, y0 - d), (x + 20, y0 - d)]), col_top)
            cv.drawRect(skia.Rect.MakeLTRB(x, y0, x + w, y0 + hh), paint(col_front))
            if rs.rand() < 0.4:
                leafy_tree(cv, x + w + 30, y0 + hh, 0.45, P["L3"] if row == 2 else P["mid"], seed=row * 10 + int(x) % 7)
            x += w + rs.uniform(30, 90)
    cv.restore()
    cam.push(cv, 1.0)
    # yard walls
    fill(cv, poly([(30, 760), (1050, 760), (1050, 778), (30, 778)]), P["L2"])
    fill(cv, poly([(30, 778), (1050, 778), (1050, 808), (30, 808)]), P["L3"])
    fill(cv, poly([(-150, 1950), (30, 778), (52, 778), (-110, 1950)]), P["L2"])
    fill(cv, poly([(1230, 1950), (1050, 778), (1028, 778), (1190, 1950)]), P["L2"])
    fill(cv, poly([(52, 808), (1028, 808), (1190, 1950), (-110, 1950)]), P["earth"])
    rs = np.random.RandomState(72)
    for k in range(26):
        x = rs.uniform(80, 1000); y = rs.uniform(840, 1560); w = rs.uniform(50, 160)
        fill(cv, ell(x, y, w, w * 0.18), P["earth_d"], 0.6)
    for k in range(9):   # stepping stones from the gate to the door
        fill(cv, ell(lerp(560, 700, k / 8), lerp(1620, 1060, k / 8), 34 - k * 1.6, 13 - k * 0.5), P["earth_d"])
    # house (back right): roof top seen from above + facade
    hx0, hx1 = 520, 1000
    fill(cv, poly([(hx0 - 20, 850), (hx1 + 20, 850), (hx1 + 50, 740), (hx0 + 10, 740)]), P["L2"])
    fill(cv, poly([(hx0 - 20, 850), (hx1 + 20, 850), (hx1 + 20, 866), (hx0 - 20, 866)]), P["L4"])
    cv.drawRect(skia.Rect.MakeLTRB(hx0, 866, hx1, 1070), paint(P["L3"]))
    cv.drawRect(skia.Rect.MakeLTRB(hx0 + 40, 930, hx0 + 110, 1070), paint(P["L4"]))
    wx0, wy0, wx1, wy1 = 720, 920, 830, 1010
    tw = word(5, "yaxshi")
    win = clamp01((t - tw) / 0.25) * (0.85 + 0.15 * (1 if t - tw > 0.25 else math.sin((t - tw) * 60) ** 2))
    cv.drawRect(skia.Rect.MakeLTRB(wx0 - 8, wy0 - 8, wx1 + 8, wy1 + 8), paint(P["L4"]))
    cv.drawRect(skia.Rect.MakeLTRB(wx0, wy0, wx1, wy1), paint(mix(P["L4"], P["L3"], 0.4)))
    if win > 0:
        glow(cv, (wx0 + wx1) / 2, (wy0 + wy1) / 2, 110, P["acc"], 0.35 * win)
        cv.drawRect(skia.Rect.MakeLTRB(wx0, wy0, wx1, wy1), paint(P["acc"], win))
    cv.drawRect(skia.Rect.MakeLTRB((wx0 + wx1) / 2 - 3, wy0, (wx0 + wx1) / 2 + 3, wy1), paint(P["L4"]))
    cv.drawRect(skia.Rect.MakeLTRB(wx0, (wy0 + wy1) / 2 - 3, wx1, (wy0 + wy1) / 2 + 3), paint(P["L4"]))
    fill(cv, poly([(hx0, 1070), (hx1, 1070), (hx1 + 40, 1110), (hx0 + 30, 1110)]), P["earth_d"], 0.7)   # house shadow
    # tree (back left), seen from above
    cv.drawRect(skia.Rect.MakeLTRB(178, 900, 198, 1010), paint(P["L4"]))
    fill(cv, ell(200, 1010, 90, 22), P["earth_d"], 0.8)
    for (bx, by, br) in ((190, 860, 120), (110, 900, 70), (280, 890, 80), (150, 790, 80), (240, 800, 76)):
        cv.drawCircle(bx + 3 * math.sin(t * 1.1 + bx), by, br, paint(P["L4"]))
    # so'ri seen from above with the two small figures
    sx0, sx1, sy0, sy1 = 560, 930, 1300, 1400
    fill(cv, poly([(sx0, sy1), (sx1, sy1), (sx1 + 20, sy1 + 26), (sx0 + 20, sy1 + 26)]), P["L5"])
    for lx in (sx0 + 30, sx1 - 10):
        cv.drawRect(skia.Rect.MakeLTRB(lx - 8, sy1 + 20, lx + 8, sy1 + 60), paint(P["L5"]))
    fill(cv, poly([(sx0 + 40, sy0), (sx1 + 40, sy0), (sx1, sy1), (sx0, sy1)]), P["L4"])
    fill(cv, poly([(sx0 + 60, sy0 + 12), (sx1 + 22, sy0 + 12), (sx1 - 10, sy1 - 12), (sx0 + 24, sy1 - 12)]), mix(P["L4"], P["L5"], 0.4))
    fill(cv, ell(780, 1475, 220, 30), P["earth_d"], 0.7)
    mother_sit(cv, 660, 1372, 2.4, P["L5"], facing=1, tilt=2 * math.sin(t * 3))
    info = hero(cv, 830, 1372, 2.5, dict(mode="sit", facing=-1, head=0, breath=math.sin(t * 2.2)))
    # hearth with qozon, fire and smoke
    hearth(cv, P, 300, 1240, t, s=1.05, fire=1.0, smoke_a=0.0)
    smoke(cv, 310, 1110, t, mix(P["L2"], P["L3"], 0.5), a=0.6, s=1.6, drift=30, seed=3, rate=1.8, life=3.4)
    cv.restore()
    cam.push(cv, 1.2)
    rs = np.random.RandomState(73)
    fill(cv, poly([(-200, 1640), (1300, 1640), (1300, 4000), (-200, 4000)]), P["L5"])
    for k in range(18):
        bx = rs.uniform(-100, 1200); fill(cv, ell(bx, 1640, rs.uniform(40, 90), rs.uniform(30, 60)), P["L5"])
    cv.restore()
    INFO["hero"] = _hbox(cam, info)

# ================================================================== scene 6: sunset -> night, he lowers his head
def scene6(cv, t):
    lt = L(6, t); u = palette_u(t); P = pal(u)
    s0 = SC_START[6]
    tau = t - 0.5 * clamp01((t - (s0 + 0.45)) / 1.0) * 1.0   # half speed for ~1 s
    cam = Cam(z=1.1 + 0.05 * ease_io(lt / 2.6), fx=600, fy=1250)
    sun = (300, 1170 + 330 * ease_in(ramp(t, s0, s0 + 1.1)), 200) if t < s0 + 1.15 else None
    mo = ease_out(ramp(t, s0 + 0.7, s0 + 2.6))
    moon = (870, lerp(1060, 640, mo), 125, clamp01(mo * 2.5)) if mo > 0 else None
    def birds(c):
        flock(c, tau, s0 - 0.5, s0 + 3.5, 1150, -150, 700, 2, 1.8, P["L4"], seed=9, facing=-1, speed_mul=0.7)
    yard_close_bg(cv, P, cam, tau, sun=sun, moon=moon, star_a=ease_io(ramp(t, s0 + 1.0, s0 + 2.1)),
                  win_a=ease_io(ramp(t, s0 + 1.3, s0 + 1.8)), birds=birds)
    cam.push(cv, 1.0)
    sori_back(cv, P, -100, 1300, 1640, s=2.0)
    tj = word(6, "jim")
    info = hero(cv, 640, 1640, 9.5, dict(mode="sit", facing=-1, head=0, tilt=24 * ease_io(ramp(t, tj - 0.05, tj + 0.6)),
                                          lean=4 * ease_io(ramp(t, tj, tj + 0.7)), breath=math.sin(tau * 2.0)))
    sori_front(cv, P, -100, 1300, 1640, s=2.0, leg=200)
    cv.restore()
    cam.push(cv, 1.4); branch(cv, P, -60, -40, 1.3, tau, mirror=True, seed=7); cv.restore()
    INFO["hero"] = _hbox(cam, info)

# ================================================================== scene 7 (imagined): she looks at the empty palm, pulls her hand away
def scene7(cv, t):
    lt = L(7, t); P = pal(1)
    cam = Cam(x=lerp(-10, 25, lt / DUR(7)), z=1.0)
    cam.push(cv, 0.0); sky(cv, P, y0=-100, y1=1000); stars(cv, t, 1.0, ymax=760)
    draw_disc(cv, "moon", 185, 395, 105, glow=1.0); cv.restore()
    cam.push(cv, 0.05); fill(cv, ridge_path(-2000, 3000, 820, 90, 300, 41), P["L1"]); cv.restore()
    cam.push(cv, 0.15)
    for k, px in enumerate((-60, 10, 980, 1040, 1100)):
        poplar(cv, px, 900, 300 + 40 * (k % 2), 46, P["L2"])
    cv.restore()
    cam.push(cv, 0.45)
    hx0, hx1, top = 150, 1050, 760
    cv.drawRect(skia.Rect.MakeLTRB(hx0, top, hx1, 1400), paint(P["L3"]))
    cv.drawRect(skia.Rect.MakeLTRB(hx0 - 30, top - 20, hx1 + 30, top + 6), paint(P["L4"]))
    for (wx0, wx1) in ((230, 360), (840, 970)):
        glow(cv, (wx0 + wx1) / 2, 900, 140, P["win"], 0.45)
        cv.drawRect(skia.Rect.MakeLTRB(wx0 - 10, 830, wx1 + 10, 980), paint(P["L4"]))
        cv.drawRect(skia.Rect.MakeLTRB(wx0, 840, wx1, 970), paint(P["win"]))
        cv.drawRect(skia.Rect.MakeLTRB((wx0 + wx1) / 2 - 4, 840, (wx0 + wx1) / 2 + 4, 970), paint(P["L4"]))
        cv.drawRect(skia.Rect.MakeLTRB(wx0, 901, wx1, 909), paint(P["L4"]))
    cv.drawRect(skia.Rect.MakeLTRB(530, 1010, 680, 1400), paint(P["L4"]))
    cv.drawRect(skia.Rect.MakeLTRB(546, 1026, 664, 1400), paint(P["L5"]))
    cv.drawRect(skia.Rect.MakeLTRB(600, 1026, 606, 1400), paint(P["win"], 0.55))
    cv.restore()
    cam.push(cv, 1.0)
    cv.drawRect(skia.Rect.MakeLTRB(-2000, 1385, 3000, 4200), paint(P["earth"]))
    fill(cv, ell(540, 1392, 380, 18), P["earth_d"])
    tu = word(7, "uylansang"); ta = word(7, "ayoling"); ts = word(7, "sabrsiz")
    ep = ease_io(ramp(t, tu - 0.05, tu + 0.4))
    hinfo = hero(cv, 735, 1385, 5.0, dict(facing=-1, walk=0.0, legs=[(-4, 3), (5, 4)], head=0,
                 armN=(lerp(6, 62, ep), lerp(14, 38, ep)), handN="palm" if ep > 0.4 else "relax",
                 tilt=lerp(0, 10, ease_io(ramp(t, ts + 0.3, ts + 0.8))), breath=math.sin(t * 2.0)))
    hand_reach = (hinfo["hand_n"][0] - 40, hinfo["hand_n"][1] + 6)
    pull = ease_io(ramp(t, ts, ts + 0.5))
    tgt = (lerp(lerp(470, hand_reach[0], ease_io(ramp(lt, 0.1, 0.6))), 360, pull), lerp(lerp(1140, hand_reach[1], ease_io(ramp(lt, 0.1, 0.6))), 1040, pull))
    wife(cv, 350 - 14 * pull, 1385, 4.8, P["L5"], facing=1, tilt=14 * ease_io(ramp(t, ta - 0.1, ta + 0.35)) * (1 - 0.7 * pull) - 6 * pull,
         arm_target=tgt)
    cv.restore()
    cam.push(cv, 1.25); ground_strip(cv, P, -3000, 4200, 1500, P["L5"], seed=17); cv.restore()
    INFO["hero"] = _hbox(cam, hinfo)

# ================================================================== road fork (scenes 8, 10) and top-down (9)
def _road_poly(pts, w0, w1):
    """variable-width road along a polyline"""
    left, right = [], []
    n = len(pts)
    for i, p in enumerate(pts):
        a = pts[min(i + 1, n - 1)]; b = pts[max(i - 1, 0)]
        dx, dy = a[0] - b[0], a[1] - b[1]; Ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / Ln, dx / Ln
        w = lerp(w0, w1, i / (n - 1)) / 2
        left.append((p[0] + nx * w, p[1] + ny * w)); right.append((p[0] - nx * w, p[1] - ny * w))
    return poly(left + right[::-1])

def _bez(p0, p1, p2, n=40):
    return [((1 - u) ** 2 * p0[0] + 2 * u * (1 - u) * p1[0] + u * u * p2[0], (1 - u) ** 2 * p0[1] + 2 * u * (1 - u) * p1[1] + u * u * p2[1]) for u in np.linspace(0, 1, n)]

FORK_J = (540, 1250)
BR_L = ((540, 1250), (330, 1150), (40, 1098))
BR_R = ((540, 1250), (760, 1150), (1040, 1098))
def _on_branch(br, u):
    return _bez(*br, n=2)[0] if u <= 0 else ((1 - u) ** 2 * br[0][0] + 2 * u * (1 - u) * br[1][0] + u * u * br[2][0],
                                              (1 - u) ** 2 * br[0][1] + 2 * u * (1 - u) * br[1][1] + u * u * br[2][1])

def fork_wide(cv, P, cam, t, dust=0.0):
    cam.push(cv, 0.0); sky(cv, P, y0=-100, y1=1080); stars(cv, t, 1.0, ymax=950)
    draw_disc(cv, "moon", 800, 560, 115, glow=1.0); cv.restore()
    cam.push(cv, 0.04); fill(cv, ridge_path(-2000, 3000, 1060, 150, 360, 51), P["haze"]); cv.restore()
    cam.push(cv, 0.08); fill(cv, ridge_path(-2000, 3000, 1090, 70, 240, 52), P["L1"]); cv.restore()
    cam.push(cv, 0.14)
    fill(cv, ridge_path(-2000, 3000, 1110, 30, 200, 53), P["L2"])
    for px in (90, 130, 960, 1000, 1030): poplar(cv, px, 1100, 150, 30, P["L2"])
    cv.restore()
    cam.push(cv, 1.0)
    cv.drawRect(skia.Rect.MakeLTRB(-2000, 1092, 3000, 4200), paint(P["L3"]))
    rs = np.random.RandomState(81)
    for k in range(30):
        y = rs.uniform(1110, 1600); x = rs.uniform(-300, 1400); w = rs.uniform(60, 200) * (y - 1000) / 400
        fill(cv, ell(x, y, w, w * 0.08), P["L4"], 0.6)
    fill(cv, _road_poly(_bez((540, 2100), (540, 1600), FORK_J), 520, 120), P["road"])
    fill(cv, _road_poly(_bez(*BR_L), 120, 14), P["road"])
    fill(cv, _road_poly(_bez(*BR_R), 120, 14), P["road"])
    fill(cv, _road_poly(_bez((540, 2100), (540, 1600), (540, 1262)), 120, 22), P["road_d"], 0.5)
    cv.restore()

def dust_wind(cv, P, t, t0, amount, seed=4, y0=1150, y1=1500):
    rs = np.random.RandomState(seed)
    for k in range(60):
        ph = rs.uniform(0, 1); sp = rs.uniform(0.25, 0.5)
        u = (ph + (t - t0) * sp) % 1.0
        x = -100 + 1300 * u; base = rs.uniform(y0, y1)
        y = base - 90 * u * rs.uniform(0.3, 1.0) + 10 * math.sin(t * 3 + k)
        r = rs.uniform(3, 9) * (1 + u)
        al = amount * 0.45 * math.sin(math.pi * u)
        cv.drawCircle(x, y, r, paint(mix(P["road_l"], P["haze"], 0.5), clamp01(al), blur=r * 0.5))

def walker_on(br, u):
    p = _on_branch(br, u)
    s = lerp(2.75, 0.9, u)
    return p, s

def scene8(cv, t):
    lt = L(8, t); P = pal(1)
    cam = Cam(x=lerp(-15, 15, lt / DUR(8)))
    fork_wide(cv, P, cam, t)
    cam.push(cv, 1.0)
    uh = lerp(0.10, 0.52, lt / DUR(8)); uw = lerp(0.10, 0.50, lt / DUR(8))
    pw, sw = walker_on(BR_L, uw)
    wife(cv, pw[0], pw[1], sw, P["L5"], facing=-1, ph=lt * 6.6, walk=1.0)
    ph_, sh_ = walker_on(BR_R, uh)
    info = hero(cv, ph_[0], ph_[1], sh_, dict(facing=1, walk=0.9, ph=lt * 6.6 + 1.0))
    cv.restore()
    dust_wind(cv, P, t, SC_START[8], 1.6, y0=1120, y1=1420)
    INFO["hero"] = _hbox(cam, info)

def child_stand(cv, x, y, s, col, a=1.0):
    if a < 1: layer_alpha(cv, a)
    cv.save(); cv.translate(x, y); cv.scale(s, s)
    for fx in (-3.2, 3.2):
        fill(cv, limb((fx, -26), (fx * 1.1, -2), 3.0, 2.6), col)
        fill(cv, ell(fx * 1.2, -0.6, 3.4, 1.6), col)
    fill(cv, smooth([(-8.5, -50), (-10.5, -38), (-10.0, -24), (10.0, -24), (10.5, -38), (8.5, -50), (0, -52)], k=0.4), col)
    for sx in (-1, 1): fill(cv, limb((sx * 8.0, -48), (sx * 10.5, -28), 2.6, 2.2), col)
    fill(cv, limb((0, -56), (0, -50), 2.7, 3.0), col)
    fill(cv, ell(0, -63.5, 7.8, 8.4), col)
    fill(cv, smooth([(-7.5, -66), (-5, -72.5), (0, -73.4), (5, -72.6), (7.6, -67), (1, -70)], k=0.4), col)
    cv.restore()
    if a < 1: cv.restore()

def scene9(cv, t):
    lt = L(9, t); P = pal(1)
    z = lerp(1.45, 1.0, ease_out(lt / DUR(9)))
    cam = Cam(z=z, fx=540, fy=1000)
    cam.push(cv, 1.0)
    cv.drawRect(skia.Rect.MakeLTRB(-1500, -1500, 2600, 3600), paint(P["L4"]))
    rs = np.random.RandomState(91)
    for k in range(260):
        x = rs.uniform(-800, 1900); y = rs.uniform(-800, 2800); r = rs.uniform(3, 10)
        fill(cv, ell(x, y, r * 1.6, r), P["L5"], 0.55)
    for k in range(70):
        x = rs.uniform(-800, 1900); y = rs.uniform(-800, 2800)
        for j in range(4): cv.drawPath(poly([(x + j * 6 - 3, y), (x + j * 6 + rs.uniform(-6, 6), y - rs.uniform(10, 22)), (x + j * 6 + 3, y)]), paint(P["L5"], 0.7))
    stem = _bez((540, 2800), (540, 1800), (540, 1000))
    fill(cv, _road_poly(stem, 240, 220), P["road"])
    brl = _bez((540, 1000), (420, 620), (-600, -400)); brr = _bez((540, 1000), (660, 620), (1680, -400))
    fill(cv, _road_poly(brl, 220, 200), P["road"]); fill(cv, _road_poly(brr, 220, 200), P["road"])
    fill(cv, ell(540, 1000, 140, 140), P["road"])
    for b in (stem, brl, brr):
        for k in range(0, len(b) - 1, 3):
            fill(cv, ell(b[k][0] + 30, b[k][1], 10, 5), P["road_d"], 0.6)
    # parents walking away on the two branches, fading into haze
    fa = 1 - ease_io(ramp(t, SC_START[9] + 0.2, SC_START[9] + 1.3))
    for br, col in ((brl, P["L5"]), (brr, None)):
        i = int(lerp(14, 22, lt / DUR(9))); p = br[i]
        hd = math.degrees(math.atan2(br[i + 1][1] - p[1], br[i + 1][0] - p[0])) + 90
        if col is None:
            person_top(cv, p[0], p[1], 4.6, HERO["ch"], heading=hd, a=fa)
            fill(cv, ell(p[0], p[1], 13, 13), HERO["doppi"], fa)
        else:
            person_top(cv, p[0], p[1], 4.4, col, heading=hd, a=fa)
    # moonlight on the child + long shadow
    fill(cv, ell(540, 1000, 190, 150), P["moon"], 0.13, blur=40)
    fill(cv, ell(540, 1000, 110, 85), P["moon"], 0.12, blur=20)
    cv.save(); cv.translate(540, 1000); cv.skew(-0.9, 0); cv.scale(1, -0.55)
    child_stand(cv, 0, 0, 3.0, P["L5"], a=0.55); cv.restore()
    child_stand(cv, 540, 1000, 3.0, P["L5"])
    cv.restore()
    # haze at the far ends
    p = skia.Paint()
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, 760)],
                [skia.Color4f(*P["haze"], 0.75).toColor(), skia.Color4f(*P["haze"], 0.0).toColor()]))
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, 760), p)
    INFO["hero"] = None

def scene10(cv, t):
    lt = L(10, t); P = pal(1)
    cam = Cam(x=lerp(10, -15, lt / DUR(10)), z=1.03)
    fork_wide(cv, P, cam, t)
    cam.push(cv, 1.0)
    stop = ease_out(ramp(lt, 0.0, 0.45))
    da = 1 - ease_io(ramp(t, word(10, "muhim") - 0.1, word(10, "emas") + 0.3))
    uh = lerp(0.60, 0.64, stop); uw = lerp(0.58, 0.62, stop)
    pw, sw = walker_on(BR_L, uw); ph_, sh_ = walker_on(BR_R, uh)
    if da > 0.01:
        layer_alpha(cv, da)
        wife(cv, pw[0], pw[1], sw, P["L5"], facing=-1, ph=lt * 6.6 * (1 - stop), walk=1 - stop)
        hero(cv, ph_[0], ph_[1], sh_, dict(facing=1, walk=0.9 * (1 - stop), ph=lt * 6.6 * (1 - stop) + 1.0, head=150 * stop))
        cv.restore()
        if da < 1:
            rs = np.random.RandomState(5)
            for (px, py, s_) in ((pw[0], pw[1], sw), (ph_[0], ph_[1], sh_)):
                for k in range(16):
                    d = (1 - da) * rs.uniform(10, 50)
                    cv.drawCircle(px + rs.uniform(-12, 12) * s_ + d * 0.6, py - rs.uniform(10, 95) * s_ - d, rs.uniform(1.5, 3), paint(P["haze"], da * 0.8))
    fill(cv, ell(540, 1262, 70, 12), P["moon"], 0.12, blur=8)
    child_stand(cv, 540, 1262, 2.1, P["L5"])
    cv.restore()
    INFO["hero"] = None

# ================================================================== scene 11: child looks at us, then back to reality
def reality_sori(cv, t, lift_t0):
    P = pal(1)
    cam = Cam(z=1.22, fx=560, fy=1160, x=10 * math.sin(t * 0.4))
    yard_side(cv, P, cam, t, moon=(880, 560, 120), star_a=1.0, win_a=1.0, fire=0.6)
    cam.push(cv, 1.0)
    lift = ease_io(ramp(t, lift_t0, lift_t0 + 0.45))
    info = sori_pair(cv, P, t, hero_head=0, hero_tilt=24 * (1 - lift), mother_tilt=4,
                     hand_on=ease_io(ramp(t, lift_t0 + 0.15, lift_t0 + 0.7)), hero_lean=4 * (1 - lift))
    cv.restore()
    yard_fg(cv, P, cam, t)
    return cam, info

def scene11(cv, t):
    lt = L(11, t); P = pal(1)
    a = ease_io(ramp(t, T_BACK0, T_BACK1))
    if a < 1:
        cam = Cam(z=1 + 0.05 * ease_io(lt / 1.9), fx=540, fy=1100)
        cam.push(cv, 0.3); sky(cv, P, y0=-200, y1=1400); stars(cv, t, 1.0, ymax=1500)
        draw_disc(cv, "moon", 540, 930, 330, glow=1.2); cv.restore()
        cam.push(cv, 0.6); fill(cv, ridge_path(-1000, 2200, 1500, 90, 260, 61), P["L2"]); cv.restore()
        tb = word(11, "bolada")
        turn = ease_io(ramp(t, tb - 0.15, tb + 0.35))
        cam.push(cv, 1.0)
        child_front(cv, 540, 1720, 12.5, P["L5"], turn=turn, eye_col=P["moon"], eye_a=0.85)
        cv.restore()
    if a > 0:
        layer_alpha(cv, a)
        cam, info = reality_sori(cv, t, T_BACK1 - 0.15)
        cv.restore()
        INFO["hero"] = _hbox(cam, info)
    else:
        INFO["hero"] = None

# ================================================================== scenes 12-13: the gate at night, CTA
C12 = dict(x=-406.7, y=165.0, z=1.5)
HX12 = 60.0
def cam12(extra_x=0.0, extra_y=0.0):
    return Cam(x=C12["x"] + extra_x, y=C12["y"] + extra_y, z=C12["z"])

def scene12(cv, t):
    lt = L(12, t); P = pal(1)
    ty = word(12, "yuboring")
    fl = ramp(t, ty + 0.05, ty + 0.9)
    cam = cam12(extra_x=40 * ease_io(fl), extra_y=-15 * ease_io(fl))
    street(cv, P, cam, t, u=1.0, moon=(720, 560, 110), star_a=1.0, win_a=1.0)
    cam.push(cv, 1.0)
    lift = ease_io(ramp(lt, 0.15, 0.6))
    wind_ = ease_io(ramp(t, ty - 0.35, ty - 0.02))
    thr = ease_out(ramp(t, ty, ty + 0.16))
    armN = (lerp(lerp(6, 70, lift), 40, wind_), lerp(lerp(14, 70, lift), 110, wind_))
    armN = (lerp(armN[0], 150, thr), lerp(armN[1], 10, thr))
    info = hero(cv, HX12, HY, S1, dict(facing=1, walk=0.0, legs=[(5 * thr, 4), (-6, 5)], head=0, tilt=-8 * lift - 10 * ease_io(fl),
                                       armN=armN, handN="fist", breath=math.sin(t * 2), lean=-3 * wind_ + 5 * thr))
    hn = info["hand_n"]
    if t < ty + 0.12:
        paper_plane(cv, hn[0] + 6, hn[1] - 10, 1.35, -25 - 25 * wind_, P["acc"])
    else:
        u = ease_in(ramp(t, ty + 0.12, ty + 0.95)) * 0.6 + ramp(t, ty + 0.12, ty + 0.95) * 0.4
        p0 = (hn[0] + 6, hn[1] - 10)
        pts = ((info["T"]((22, -120))), (700, 700), (1000, 380))
        x = (1 - u) ** 2 * pts[0][0] + 2 * u * (1 - u) * pts[1][0] + u * u * pts[2][0]
        y = (1 - u) ** 2 * pts[0][1] + 2 * u * (1 - u) * pts[1][1] + u * u * pts[2][1]
        ang = math.degrees(math.atan2(-(1 - u) * pts[0][1] + (1 - 2 * u) * pts[1][1] + u * pts[2][1], -(1 - u) * pts[0][0] + (1 - 2 * u) * pts[1][0] + u * pts[2][0]))
        paper_plane(cv, x, y + 6 * math.sin(t * 9), 1.35, ang + 4 * math.sin(t * 7), P["acc"])
        INFO["plane"] = cam.to_screen((x, y))
    cv.restore()
    street_fg(cv, P, cam, t)
    INFO["hero"] = _hbox(cam, info)

def scene13_state(cv, t, rot_extra=None):
    P = pal(palette_u(t))
    tr = word(13, "repost")
    cam = cam12(extra_x=40, extra_y=-15)
    street(cv, P, cam, t, u=palette_u(t), moon=(720, 560, 110), star_a=1 - ramp(t, ROT0, ROT1), win_a=1 - ramp(t, ROT0, ROT1))
    cam.push(cv, 1.0)
    look = ease_io(ramp(t, SC_START[13] + 0.2, SC_START[13] + 0.7))
    low = ease_io(ramp(t, SC_START[13] + 0.05, SC_START[13] + 0.5))
    opn = ease_io(ramp(t, tr - 0.55, tr - 0.15))
    up = ease_io(ramp(t, tr + 0.04, tr + 0.32))
    armN = (lerp(lerp(150, 8, low), 68, opn), lerp(lerp(10, 15, low), 22, opn))
    armN = (lerp(armN[0], 150, up), lerp(armN[1], 6, up))
    info = hero(cv, HX12, HY, S1, dict(facing=1, walk=0.0, legs=[(-4, 3), (5, 4)], head=lerp(0, 70, look) - 40 * up,
                                       tilt=lerp(-14, 0, look) - 10 * up, armN=armN, handN="palm" if opn > 0.3 else "relax",
                                       breath=math.sin(t * 2)))
    cv.restore()
    street_fg(cv, P, cam, t)
    hn = cam.to_screen(info["hand_n"])
    return cam, info, hn

def scene13(cv, t):
    tr = word(13, "repost")
    rot = -360 * ease_io(ramp(t, ROT0, ROT1))          # counter-clockwise, like the repost arrows
    sw = ease_io(ramp(t, ROT0 + 0.26, ROT0 + 0.5))     # content swap hidden inside the spin
    cv.save()
    cv.translate(W / 2, H / 2); cv.rotate(rot); cv.translate(-W / 2, -H / 2)
    nb = len(INFO.get("heroes", []))
    cam, info, hn = scene13_state(cv, t)
    INFO["hero"] = _hbox(cam, info)
    if sw > 0:
        layer_alpha(cv, sw)
        cv.drawRect(skia.Rect.MakeLTRB(-2000, -2000, 3000, 4000), paint((0, 0, 0)))
        c1 = scene1(cv, t - N_FRAMES / FPS, u=palette_u(t))
        cv.restore()
    def rbox(b):
        a = math.radians(rot); pts = []
        for (x, y) in ((b[0], b[1]), (b[2], b[1]), (b[0], b[3]), (b[2], b[3])):
            x -= W / 2; y -= H / 2
            pts.append((x * math.cos(a) - y * math.sin(a) + W / 2, x * math.sin(a) + y * math.cos(a) + H / 2))
        return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
    hs = INFO.get("heroes", [])
    INFO["heroes"] = hs[:nb] + [rbox(b) for b in hs[nb:]]
    # repost icon above the open palm, lifted up, spinning with the scene
    ia = ease_out_back(ramp(t, tr, tr + 0.16), 2.0)
    if ia > 0:
        icon_p = (hn[0] + 4, hn[1] - 58 - 10 * ease_io(ramp(t, tr, tr + 0.3)))
        fade = 1 - ease_io(ramp(t, ROT0 + 0.3, ROT0 + 0.55))
        repost_icon(cv, icon_p[0], icon_p[1], 40 * ia, -200 * ease_in(ramp(t, tr + 0.1, ROT0 + 0.2)), pal(1)["acc"], a=fade, glow_a=0.35 * fade)
        INFO["icon"] = icon_p if fade > 0.5 else None
    cv.restore()

# ================================================================== registry, dissolves, subtitle placement
SCENE_FN = {1: scene1, 2: scene2, 3: scene3, 4: scene4, 5: scene5, 6: scene6, 7: scene7, 8: scene8, 9: scene9,
            10: scene10, 11: scene11, 12: scene12, 13: scene13}
DISSOLVES = [(6, 7, SC_START[7], SC_START[7] + 0.45)]
SUB_Y = {1: 1430, 2: 1440, 3: 400, 4: 520, 5: 1450, 6: 780, 7: 660, 8: 1440, 9: 1440, 10: 1440, 11: 440, 12: 1455, 13: 1455}
def sub_y(i):
    return SUB_Y[scene_at(i)]
