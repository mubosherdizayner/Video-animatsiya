# The 14 scenes. Each draw function paints the frame with cairo and returns overlay items (texts placed in the scene).
import math, random
import cairo
from style import *
from style import _MUTE
from chars import *
from props import *
import timeline as TL

# ------------------------------------------------------------------ camera with parallax
class Cam:
    def __init__(self, z=1.0, vx=540.0, vy=960.0, sx=0.0, sy=0.0):
        self.z, self.vx, self.vy, self.sx, self.sy = z, vx, vy, sx, sy

def focus_cam(z, fx, fy, panx=0.0, pany=0.0, sx=0.0, sy=0.0):
    return Cam(z, fx - (fx - 540) / z + panx, fy - (fy - 960) / z + pany, sx, sy)

def lay(ctx, cam, d):
    ctx.identity_matrix()
    z = 1 + (cam.z - 1) * d
    vx = 540 + (cam.vx - 540) * d; vy = 960 + (cam.vy - 960) * d
    ctx.translate(540 + cam.sx, 960 + cam.sy); ctx.scale(z, z); ctx.translate(-vx, -vy)

def to_screen(cam, d, x, y):
    z = 1 + (cam.z - 1) * d
    vx = 540 + (cam.vx - 540) * d; vy = 960 + (cam.vy - 960) * d
    return (x - vx) * z + 540 + cam.sx, (y - vy) * z + 960 + cam.sy

def W_(k, i): return TL.word_t(k, i)

# ------------------------------------------------------------------ hero dust
def dissolve_h(t, t0, t1):
    """dissolve height in hero units (0 = feet .. 108 = gone)"""
    return clamp01((t - t0) / (t1 - t0)) * 108.0

def ragged(u, h):
    return h + 2.4 * math.sin(u * 1.7 + 3.0) + 1.6 * math.sin(u * 0.63 + 1.0)

def draw_dissolving_hero(ctx, x, y, s, facing, h_d, pose):
    if h_d >= 106: return
    ctx.save()
    pts = []
    for i in range(0, 41):
        u = -20 + i
        pts.append((x + facing * s * u, y - s * ragged(u, h_d)))
    ctx.move_to(x - 30 * s, y - 120 * s)
    ctx.line_to(x + 30 * s, y - 120 * s)
    if facing > 0: pts = pts[::-1]
    for p in pts: ctx.line_to(*p)
    ctx.close_path(); ctx.clip()
    hero_side(ctx, x, y, s, facing=facing, **pose)
    ctx.restore()

def draw_dust(ctx, x, y, s, facing, t, t0, t1, wind=1.0, amax=1.0, n=1500, fade=2.6):
    if HIDE["hero"]: return
    ps = hero_particles()
    span = t1 - t0
    for (ox, oy, col, sz, r1, r2, r3) in ps[:n]:
        h = -oy
        tr = t0 + (h + (r1 - 0.5) * 6) / 108 * span
        tau = t - tr
        if tau <= 0: continue
        life = fade + 1.6 * r2
        a = 1 - tau / life
        if a <= 0: continue
        px = x + facing * s * ox + wind * (70 * tau + 24 * tau * tau) * (0.7 + 0.6 * r3) + 9 * math.sin(tau * 2.3 + r2 * 6)
        py = y + s * oy - (26 * tau + 7 * tau * tau) * (0.4 + r3) + 6 * math.sin(tau * 3.1 + r1 * 6)
        q = s * 0.62 * sz * (1 - 0.45 * min(1, tau / life))
        rgb(ctx, col, amax * a * (0.75 + 0.25 * r1))
        ctx.rectangle(px - q / 2, py - q / 2, q, q); ctx.fill()

# ------------------------------------------------------------------ banknotes from the sky
def falling_notes(ctx, cam, t, col, n=16, seed=21, near=True):
    rnd = random.Random(seed)
    for i in range(n):
        d = rnd.uniform(0.35, 0.6) if not near else rnd.uniform(0.85, 1.15)
        lay(ctx, cam, d)
        w = (rnd.uniform(20, 30) if not near else rnd.uniform(38, 58))
        x0 = rnd.uniform(-60, 1140); v = rnd.uniform(55, 95) * (0.6 if not near else 1.0)
        rng_y = 1700
        y = (rnd.uniform(0, rng_y) + v * t) % rng_y - 160
        ph = rnd.uniform(0, 6.28); fs = rnd.uniform(1.6, 2.8)
        x = x0 + 34 * math.sin(t * 0.9 + ph)
        rot = 0.5 * math.sin(t * 1.1 + ph * 1.3)
        flip = math.cos(t * fs + ph)
        banknote(ctx, x, y, w, rot, flip, col, a=(0.75 if not near else 1.0))
    ctx.identity_matrix()

# ------------------------------------------------------------------ scene 1: hook, dawn hilltop, red button
S1_H0, S1_H1 = -1.3, 4.25  # dissolve start / end (global seconds)

def s1_ground(x): return 1300 + 0.00028 * (x - 520) ** 2 + 5 * math.sin(x * 0.011)

def draw_s1(ctx, t, lt, D):
    p = DAWN
    cam = focus_cam(1.04 + 0.09 * ease_io_sine(lt / max(D, 1e-3)), 520, 1200)
    sky(ctx, p)
    lay(ctx, cam, 0.05); disc(ctx, 790, 720 - 7 * t, 150, acc(p["disc0"]), acc(p["disc1"]), seed=4, t=t)
    lay(ctx, cam, 0.12); ridge(ctx, p["L"][0], 11, 38, 935)
    fog(ctx, 985, lighten(p["sky1"], 0.3), t, a=0.45, h=70, seed=1, speed=14)
    lay(ctx, cam, 0.22); ridge(ctx, p["L"][1], 12, 46, 1030)
    fog(ctx, 1075, lighten(p["sky1"], 0.3), t, a=0.42, h=70, seed=2, speed=18)
    falling_notes(ctx, cam, t, acc(MONEY), n=9, seed=31, near=False)
    lay(ctx, cam, 0.36); ridge(ctx, p["L"][2], 13, 40, 1120)
    fog(ctx, 1160, lighten(p["sky1"], 0.25), t, a=0.40, h=60, seed=3, speed=24)
    lay(ctx, cam, 0.55); ridge(ctx, p["L"][3], 14, 34, 1215)
    fog(ctx, 1245, lighten(p["sky1"], 0.2), t, a=0.38, h=55, seed=4, speed=30)
    # foreground hilltop
    lay(ctx, cam, 1.0)
    ridge(ctx, p["L"][4], 0, 0, 0, fn=s1_ground)
    grass(ctx, p["L"][4], s1_ground, -200, 1300, t, seed=3, density=0.12, wind=0.9)
    # pedestal + red button pressed by the friend's palm
    bx = 470
    top = pedestal(ctx, bx, s1_ground(bx) + 4, 96, 150, darken(p["L"][4], 0.08), seed=2)
    press = 0.9 + 0.05 * math.sin(t * 2.0)
    button(ctx, bx, top, 34, acc(RED_BTN), press=press)
    btn_top = top - 34 * (0.55 - 0.33 * press)
    fx, fs = 392, 3.3
    fy = s1_ground(fx)
    tgt = ((bx - 6 - fx) / fs, (btn_top - 3 - fy) / fs)
    friend_side(ctx, fx, fy, fs, darken(p["L"][4], 0.05), facing=1, lean=0,
                arm_n=("tgt", tgt, -1, "flat"), arm_f=("ang", -6, -12, "open"))
    # hero dissolving into dust from the feet up, dust drifting right
    hx_, hs = 628, 3.3
    hy = s1_ground(hx_)
    h_d = dissolve_h(t, S1_H0, S1_H1)
    draw_dissolving_hero(ctx, hx_, hy, hs, -1, h_d, dict(arm_n=("ang", 6, -8, "open"), arm_f=("ang", -4, -10, "open"), hem_flare=0.6 * math.sin(t * 2.6)))
    draw_dust(ctx, hx_, hy, hs, -1, t, S1_H0, S1_H1, wind=1.0)
    falling_notes(ctx, cam, t, acc(MONEY), n=8, seed=32, near=True)
    lay(ctx, cam, 1.0)
    fog(ctx, 1500, lighten(p["sky1"], 0.1), t, a=0.16, h=90, seed=6, speed=22)
    ctx.identity_matrix()
    return []

# ------------------------------------------------------------------ scene 2: wide, friend walks away with the sack
def s2_ground(x): return 1612 + 0.00011 * (x - 560) ** 2 + 5 * math.sin(x * 0.009 + 1)
def s2_slope(x): return 1215 + 22 * math.sin(x * 0.004 + 0.6) + 10 * math.sin(x * 0.011)

def road_band(ctx, pts_c, w0, w1, col, a=1.0):
    """band of varying width along a centreline"""
    n = len(pts_c)
    left, right = [], []
    for i, (x, y) in enumerate(pts_c):
        j0, j1 = max(0, i - 1), min(n - 1, i + 1)
        dx, dy = pts_c[j1][0] - pts_c[j0][0], pts_c[j1][1] - pts_c[j0][1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        w = (w0 + (w1 - w0) * i / (n - 1)) / 2
        left.append((x + nx * w, y + ny * w)); right.append((x - nx * w, y - ny * w))
    smooth_path(ctx, left + right[::-1], close=True); rgb(ctx, col, a); ctx.fill()

def bezier_pts(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        u = i / n; v = 1 - u
        out.append((v ** 3 * p0[0] + 3 * v * v * u * p1[0] + 3 * v * u * u * p2[0] + u ** 3 * p3[0],
                    v ** 3 * p0[1] + 3 * v * v * u * p1[1] + 3 * v * u * u * p2[1] + u ** 3 * p3[1]))
    return out

S2_ROAD = bezier_pts((610, 1660), (760, 1500), (330, 1430), (340, 1236), 40)   # down the far slope, away from us

def draw_s2(ctx, t, lt, D):
    p = DAWN
    u = lt / max(D, 1e-3)
    cam = focus_cam(1.02, 540, 1300, panx=30 - 60 * ease_io_sine(u))
    sky(ctx, p)
    lay(ctx, cam, 0.04); disc(ctx, 300, 640 - 7 * lt, 124, p["disc0"], p["disc1"], seed=7, t=t)
    lay(ctx, cam, 0.08)
    for i in range(8):   # flock crossing the far sky
        bx = -120 + (lt * 330 + i * 70 + (i % 3) * 25); by = 470 + 26 * math.sin(i * 1.7) + 8 * math.sin(lt * 2 + i)
        bird(ctx, bx, by, 1.25, p["L"][3], lt * 11 + i * 1.3, a=0.85)
    lay(ctx, cam, 0.1); ridge(ctx, p["L"][0], 21, 36, 880)
    fog(ctx, 915, lighten(p["sky1"], 0.3), t, a=0.45, h=60, seed=11, speed=12)
    lay(ctx, cam, 0.2); ridge(ctx, p["L"][1], 22, 42, 985)
    fog(ctx, 1025, lighten(p["sky1"], 0.3), t, a=0.4, h=60, seed=12, speed=16)
    lay(ctx, cam, 0.33); ridge(ctx, p["L"][2], 23, 34, 1110)
    fog(ctx, 1170, lighten(p["sky1"], 0.25), t, a=0.38, h=55, seed=13, speed=20)
    # the far slope with the road winding down it, and the friend walking away
    lay(ctx, cam, 0.75)
    ridge(ctx, p["L"][3], 0, 0, 0, fn=s2_slope)
    road_band(ctx, S2_ROAD, 150, 18, mix(p["L"][3], p["L"][1], 0.38))
    grass(ctx, p["L"][3], s2_slope, -200, 1300, t, seed=4, density=0.06, hmin=8, hmax=18, wind=1.1)
    k = 0.10 + 0.72 * ease_io_sine(0.05 + 0.95 * u)
    idx = k * (len(S2_ROAD) - 1)
    i0 = int(idx); fr = idx - i0
    a_, b_ = S2_ROAD[i0], S2_ROAD[min(i0 + 1, len(S2_ROAD) - 1)]
    fx, fy = a_[0] + (b_[0] - a_[0]) * fr, a_[1] + (b_[1] - a_[1]) * fr
    fs = 2.35 - 1.35 * (k - 0.1) / 0.72
    col = darken(p["L"][4], 0.05)
    def hold_sack(c, info):
        sack(c, -7.5, -83.5, 0.62, col, accent=MONEY)
    facing = -1 if (b_[0] - a_[0]) <= 0 else 1
    friend_side(ctx, fx, fy, fs, col, facing=facing, walk=lt * 7.2, arm_n=("tgt", (-3.5, -84.5), 1, "fist"),
                arm_f=("ang", 20 * math.sin(lt * 7.2), -14, "open"), hold=hold_sack)
    fog(ctx, 1500, lighten(p["sky1"], 0.2), t, a=0.22, h=60, seed=15, speed=26)
    # foreground hilltop where it happened: pedestal, pressed red button, the hero's last dust
    lay(ctx, cam, 1.0)
    ridge(ctx, p["L"][4], 0, 0, 0, fn=s2_ground)
    road_band(ctx, bezier_pts((660, 1990), (650, 1820), (600, 1700), (590, 1612), 12), 380, 150, mix(p["L"][4], p["L"][2], 0.4))
    grass(ctx, p["L"][4], s2_ground, -200, 1300, t, seed=5, density=0.11, hmin=18, hmax=44, wind=1.2)
    top = pedestal(ctx, 945, s2_ground(945) + 6, 82, 112, darken(p["L"][4], 0.08), seed=2)
    button(ctx, 945, top, 29, RED_BTN, press=0.9)
    rnd = random.Random(77)
    for i in range(170):
        ox = rnd.uniform(-30, 30); oy = rnd.uniform(-330, -10)
        sp = rnd.uniform(0.4, 1.0)
        x = 1000 + ox + (28 + 40 * sp) * (lt + 1.0) + 10 * math.sin(lt * 1.5 + i)
        y = s2_ground(1000) + oy - 22 * sp * (lt + 1.0) + 5 * math.sin(lt * 2 + i * 0.7)
        a = (0.8 * (1 - clamp01(lt / (D * rnd.uniform(0.55, 1.0))))) * rnd.uniform(0.5, 1)
        if a <= 0: continue
        c = rnd.choice([CH, CH_SH, IKAT1, IKAT2, SKIN, DOPPI, BOOT, BELT])
        q = rnd.uniform(2.2, 5.0)
        rgb(ctx, c, a); ctx.rectangle(x, y, q, q); ctx.fill()
    ctx.identity_matrix()
    return []

# ------------------------------------------------------------------ scene 3: flashback, hilltop above the mahalla
def s3_ground(x): return 1425 + 0.00009 * (x - 540) ** 2 + 4 * math.sin(x * 0.013)

def city(ctx, x0, x1, base, col, light, la, t, seed=5):
    rnd = random.Random(seed)
    x = x0
    while x < x1:
        w = rnd.uniform(18, 40); h = rnd.uniform(16, 60)
        rgb(ctx, col); ctx.rectangle(x, base - h, w, h + 30); ctx.fill()
        for j in range(rnd.randint(1, 3)):
            lx = x + rnd.uniform(3, w - 5); ly = base - rnd.uniform(5, h - 4)
            tw = 0.6 + 0.4 * math.sin(t * rnd.uniform(2, 4) + rnd.uniform(0, 6))
            rgb(ctx, light, la * tw); ctx.rectangle(lx, ly, 3.2, 3.2); ctx.fill()
        x += w + rnd.uniform(0, 8)

def draw_s3(ctx, t, lt, D):
    p = pal_mix(DAWN, DUSK, ease(lt / 1.35))
    cam = focus_cam(1.0 + 0.03 * ease_io_sine(lt / D), 540, 1250, panx=-12 * lt)
    sky(ctx, p)
    lay(ctx, cam, 0.04); disc(ctx, 470, 1005 + 14 * lt, 165, acc(p["disc0"]), acc(p["disc1"]), seed=9, t=t)
    lay(ctx, cam, 0.06)
    for i in range(6):   # birds flying home toward the sunset
        bx = 1150 - lt * 260 - i * 62; by = 700 + 30 * math.sin(i * 2.1) + i * 9
        bird(ctx, bx, by, 1.15, p["L"][3], lt * 12 + i, a=0.8)
    lay(ctx, cam, 0.1); ridge(ctx, p["L"][0], 31, 18, 1050)
    city(ctx, 640, 1010, 1052, mix(p["L"][0], p["L"][1], 0.6), acc(p["glow"]), 0.95, t)
    lay(ctx, cam, 0.18); ridge(ctx, p["L"][1], 32, 24, 1120)
    fog(ctx, 1110, lighten(p["sky1"], 0.2), t, a=0.3, h=40, seed=21, speed=10)
    lay(ctx, cam, 0.3)
    ridge(ctx, p["L"][2], 33, 10, 1230)
    flat_roofs(ctx, 1235, p["L"][2], acc(p["glow"]), 0.85 * ease(lt / 1.3), seed=6, scale=0.65, t=t)
    lay(ctx, cam, 0.5); ridge(ctx, p["L"][3], 34, 18, 1320)
    lay(ctx, cam, 1.0)
    ridge(ctx, p["L"][4], 0, 0, 0, fn=s3_ground)
    grass(ctx, p["L"][4], s3_ground, -200, 1300, t, seed=7, density=0.12, hmin=18, hmax=44, wind=1.0)
    friend_back(ctx, 405, s3_ground(405) + 2, 4.6, darken(p["L"][4], 0.08), sit=True)
    point = ease_out((lt - 0.2) / 0.7)
    hero_back_sit(ctx, 640, s3_ground(640) + 2, 4.6, point=point, t=t)
    grass(ctx, p["L"][4], lambda x: s3_ground(x) + 10, -200, 1300, t, seed=8, density=0.05, hmin=20, hmax=40, wind=1.0)
    ctx.identity_matrix()
    return []

# ------------------------------------------------------------------ scenes 4-5: mahalla yard, so'ri under the tree
SORI_Y = 1318
HERO4 = (330, 4.3); FRIEND4 = (572, 4.3)
EAT_P = 1.25

def eat_phase(t, off):
    return ((t + off) % EAT_P) / EAT_P

def hand_path(ph, mouth, plate):
    """0..1 cycle: rest at plate -> up to mouth -> back"""
    if ph < 0.18: k = 0.0
    elif ph < 0.42: k = ease((ph - 0.18) / 0.24)
    elif ph < 0.62: k = 1.0
    elif ph < 0.86: k = 1 - ease((ph - 0.62) / 0.24)
    else: k = 0.0
    return (plate[0] + (mouth[0] - plate[0]) * k, plate[1] + (mouth[1] - plate[1]) * k), k

def shells(ctx, t, t_scene0, off, x_mouth, y_mouth, x_land, col, seed):
    """shells: one per eating cycle since the scene started, falling then resting on the so'ri"""
    rnd = random.Random(seed)
    first = math.floor((t_scene0 + off) / EAT_P)
    last = math.floor((t + off) / EAT_P)
    for c in range(first - 3, last + 1):
        tc = c * EAT_P - off + 0.52 * EAT_P   # crack moment of cycle c
        dt = t - tc
        if dt < 0: continue
        r = random.Random(seed * 1000 + c)
        for j in range(2):
            dx = r.uniform(-14, 22); land = (x_land + dx, SORI_Y - 2)
            fall = min(1.0, dt / 0.42)
            x = x_mouth + (land[0] - x_mouth) * fall
            y = y_mouth + (land[1] - y_mouth) * (fall * fall)
            rot = r.uniform(0, 3) + dt * 6 * (1 - fall)
            fill_ellipse(ctx, x, y, 3.2, 1.6, col, 1.0, rot)

def draw_yard(ctx, t, cam, p, win_a, hero_mode="on", erase_x=None, erase_t=0.0, grey_shells=None):
    sky(ctx, p)
    lay(ctx, cam, 0.05); disc(ctx, 880, 1050 + 4 * (t - 9.7), 118, acc(p["disc0"]), acc(p["disc1"]), seed=12, t=t)
    lay(ctx, cam, 0.1); ridge(ctx, p["L"][0], 41, 14, 1095)
    lay(ctx, cam, 0.2)
    flat_roofs(ctx, 1180, p["L"][1], acc(p["glow"]), win_a, seed=9, scale=0.9, t=t)
    # yard wall + carved darvoza
    lay(ctx, cam, 0.45)
    rgb(ctx, p["L"][2]); ctx.rectangle(-300, 1140, 1700, 400); ctx.fill()
    rgb(ctx, darken(p["L"][2], 0.06)); ctx.rectangle(-300, 1132, 1700, 12); ctx.fill()
    darvoza(ctx, 772, 1442, 190, 270, p["L"][4], mix(p["L"][3], p["L"][4], 0.35))
    # big tree behind the so'ri
    lay(ctx, cam, 0.7)
    tree(ctx, 225, 1450, 3.1, p["L"][3], t, seed=3, wind=0.9, leaf_col=darken(p["L"][3], 0.08))
    # yard ground
    lay(ctx, cam, 1.0)
    rgb(ctx, mix(p["L"][3], p["L"][4], 0.25)); ctx.rectangle(-300, 1438, 1700, 700); ctx.fill()
    sori_col = mix(p["L"][3], p["L"][4], 0.55)
    sori(ctx, 112, 732, SORI_Y, 128, sori_col)
    # plate of sunflower seeds
    fill_ellipse(ctx, 452, SORI_Y - 3, 44, 7, mix(p["L"][2], p["L"][3], 0.4))
    rnd = random.Random(4)
    for i in range(14):
        fill_ellipse(ctx, 452 + rnd.uniform(-28, 28), SORI_Y - 6 - rnd.uniform(0, 4), 3.0, 1.6, p["L"][4], 1.0, rnd.uniform(0, 3))
    shell_c = mix(p["L"][2], p["L"][4], 0.55)
    # friend (silhouette) eating seeds, facing left
    fx, fs = FRIEND4
    fcol = p["L"][4]
    fph = eat_phase(t, 0.55)
    (hx2, hy2), kf = hand_path(fph, (5.6, -43.0), (13.0, -16.0))
    friend_side_sit(ctx, fx, SORI_Y, fs, fcol, facing=-1, arm_n=("tgt", (hx2, hy2), -1, "fist"), chew=kf * math.sin(t * 30) * 0.5)
    shells(ctx, t, 9.0, 0.55, fx - 6.8 * fs, SORI_Y - 42 * fs, fx - 40, shell_c, 2)
    # hero eating seeds, facing right
    hx_, hs = HERO4
    hph = eat_phase(t, 0.0)
    (hx1, hy1), kh = hand_path(hph, (6.0, -43.2), (13.0, -15.6))
    def draw_hero(c):
        hero_side_sit(c, hx_, SORI_Y, hs, facing=1, arm_n=("tgt", (hx1, hy1), -1, "fist"),
                      arm_f=("tgt", (10.0, -14.5), -1, "open"), chew=kh * math.sin(t * 30) * 0.5)
    if hero_mode == "on":
        draw_hero(ctx)
        shells(ctx, t, 9.0, 0.0, hx_ + 6.8 * hs, SORI_Y - 42 * hs, hx_ + 46, shell_c, 1)
    elif hero_mode == "erase":
        shells(ctx, min(t, 12.6), 9.0, 0.0, hx_ + 6.8 * hs, SORI_Y - 42 * hs, hx_ + 46, shell_c, 1)
        # what is left of the hero: the part right of the eraser edge
        ctx.save()
        e = erase_x
        ctx.move_to(e, 900)
        for i in range(0, 61):
            yy = 900 + i * 10
            ctx.line_to(e + 9 * math.sin(yy * 0.05 + 1.3) + 5 * math.sin(yy * 0.13), yy)
        ctx.line_to(1400, 1500); ctx.line_to(1400, 900); ctx.close_path(); ctx.clip()
        draw_hero(ctx)
        ctx.restore()
    else:
        shells(ctx, min(t, 12.6), 9.0, 0.0, hx_ + 6.8 * hs, SORI_Y - 42 * hs, hx_ + 46, shell_c, 1)
    # falling leaves
    lay(ctx, cam, 0.85)
    rnd = random.Random(9)
    for i in range(7):
        x0 = rnd.uniform(60, 640); sp = rnd.uniform(40, 70)
        y = (rnd.uniform(0, 900) + sp * t) % 900 + 700
        x = x0 + 30 * math.sin(t * 1.3 + i)
        leaf(ctx, x, y, 1.6, t * 2 + i, darken(p["L"][3], 0.1), 0.9)
    # cat walking past in front of the so'ri (right -> left)
    lay(ctx, cam, 1.0)
    cx = 880 - 200 * (t - 9.73)
    if -120 < cx < 1200:
        cat(ctx, cx, 1466, 2.8, p["L"][4], t, facing=-1)
    ctx.identity_matrix()

def draw_s4(ctx, t, lt, D):
    p = DUSK
    cam = focus_cam(1.26 + 0.04 * ease_io_sine(lt / D), 450, 1260, pany=120)
    draw_yard(ctx, t, cam, p, 0.95)
    return []

def draw_s5(ctx, t, lt, D):
    g = 0.22 + ease(lt / 1.4) * 0.6     # colour drains from the first frame of "hammasi"
    p = pal_grey(DUSK, 0.0)
    z = 1.37 + 0.09 * ease_io_sine(lt / D)   # punch-in on "hammasi", then a slow push-in
    cam = focus_cam(z, 430, 1260, pany=120)
    win_a = 0.95 - 0.8 * ease((lt - 0.3) / 1.2)
    e0, e1 = 0.22, 1.30
    ex = 262 + 220 * ease_io_sine((lt - e0) / (e1 - e0))
    mode = "erase" if lt < e1 + 0.02 else "off"
    # eraser edge in world coordinates of the foreground layer
    draw_yard(ctx, t, cam, p, win_a, hero_mode=mode, erase_x=ex)
    # eraser stroke: pale zig-zag scribble left behind the edge + crumbs
    lay(ctx, cam, 1.0)
    if e0 <= lt <= e1 + 0.9:
        fade = 1 - clamp01((lt - e1) / 0.9)
        x1 = ex if lt < e1 else 482
        paper = hx("#F4EDDF")
        pts = []
        x = 262.0; j = 0
        while x <= x1:
            pts.append((x, 1095 if j % 2 == 0 else 1335)); x += 34; j += 1
        pts.append((x1, 1095 if j % 2 == 0 else 1335))
        ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        for lw, aa in ((64, 0.07), (34, 0.07)):
            rgb(ctx, paper, aa * fade); ctx.set_line_width(lw); poly(ctx, pts, close=False); ctx.stroke()
        if lt < e1:
            rnd = random.Random(int(lt * 30) // 2)
            for i in range(22):
                cy = 1090 + rnd.uniform(0, 250); cx = ex + rnd.uniform(-12, 16)
                fill_ellipse(ctx, cx, cy + rnd.uniform(0, 40), rnd.uniform(1.4, 3.2), rnd.uniform(1.2, 2.2), paper, 0.5)
    ctx.identity_matrix()
    return [("__grey__", g)]

# ------------------------------------------------------------------ scene 6: lightning, golden button rises
def s6_ground(x): return 1470 + 0.00010 * (x - 540) ** 2 + 6 * math.sin(x * 0.01)

def storm_clouds(ctx, cam, t, p, flash, speed=40, y0=180, y1=900, n=9, seed=5, a=0.9):
    rnd = random.Random(seed)
    for i in range(n):
        d = rnd.uniform(0.05, 0.25)
        lay(ctx, cam, d)
        w = rnd.uniform(380, 700)
        x = (rnd.uniform(-400, 1500) - speed * t * rnd.uniform(0.6, 1.4)) % 2000 - 450
        y = rnd.uniform(y0, y1)
        c = mix(p["L"][rnd.choice([1, 2, 3])], hx("#C9CFD8"), 0.35 * flash)
        cloud(ctx, x, y, w, c, a * rnd.uniform(0.6, 0.95), seed=seed * 10 + i)
    ctx.identity_matrix()

def draw_s6(ctx, t, lt, D):
    p = NIGHT
    flash = 0.95 * math.exp(-lt / 0.10) + 0.45 * math.exp(-max(0, lt - 0.16) / 0.07) * (lt > 0.16)
    shx = 16 * math.sin(lt * 63) * math.exp(-lt * 9) if lt < 0.5 else 0
    shy = 11 * math.cos(lt * 51) * math.exp(-lt * 9) if lt < 0.5 else 0
    cam = focus_cam(1.0 + 0.04 * ease_io_sine(lt / D), 540, 1300, sx=shx, sy=shy)
    sky(ctx, p)
    lay(ctx, cam, 0.03); stars(ctx, t, hx("#EDE6D2"), n=30, y1=700, a=0.4)
    storm_clouds(ctx, cam, t, p, flash, speed=60, y0=150, y1=700, n=8, seed=6, a=0.95)
    if lt < 0.32:
        lay(ctx, cam, 0.08); lightning(ctx, 760, 120, 1180, hx("#F4EEDC"), 1 - lt / 0.32, seed=4)
    lay(ctx, cam, 0.15); ridge(ctx, mix(p["L"][0], hx("#8E9AAA"), 0.4 * flash), 61, 40, 1220)
    lay(ctx, cam, 0.3); ridge(ctx, mix(p["L"][1], hx("#8E9AAA"), 0.3 * flash), 62, 36, 1320)
    storm_clouds(ctx, cam, t, p, flash, speed=90, y0=760, y1=1050, n=6, seed=7, a=0.75)
    lay(ctx, cam, 0.55); ridge(ctx, mix(p["L"][2], hx("#8E9AAA"), 0.2 * flash), 63, 26, 1400)
    lay(ctx, cam, 1.0)
    # golden button rising out of the ground
    rise = ease_out((lt - 0.12) / 1.25)
    gx = 540; gy = s6_ground(gx)
    ped_h = 270; off = (1 - rise) * (ped_h + 130)
    ctx.save()
    ctx.rectangle(-200, -200, 1500, gy + 6 + 200); ctx.clip()
    glow(ctx, gx, gy - ped_h + off - 30, 330, GOLD_BTN, 0.35 * rise)
    top = pedestal(ctx, gx, gy + 8 + off, 210, ped_h, p["L"][3], seed=6)
    button(ctx, gx, top, 96, GOLD_BTN, press=0.0, glow_a=0.0)
    ctx.restore()
    ridge(ctx, p["L"][4], 0, 0, 0, fn=s6_ground)
    # soil crumbs pushed out while it rises
    if 0.1 < lt < 1.6:
        rnd = random.Random(3)
        for i in range(40):
            tt = lt - 0.12 - rnd.uniform(0, 0.8)
            if tt < 0: continue
            vx = rnd.uniform(-160, 160); vy = rnd.uniform(-260, -120)
            x = gx + rnd.uniform(-100, 100) + vx * tt; y = gy + vy * tt + 600 * tt * tt
            if y > gy + 10: continue
            fill_ellipse(ctx, x, y, 4, 3, p["L"][3])
    grass(ctx, p["L"][4], s6_ground, -200, 1300, t, seed=9, density=0.16, hmin=22, hmax=60, wind=1.6, gust=0.8, wmax=9)
    ctx.identity_matrix()
    return [("__flash__", min(0.92, flash))]

# ------------------------------------------------------------------ scenes 7-9 + 11-13: the fork in the road at night
FORK = dict(J=(540, 1330), L_end=(-200, 1172), R_end=(1360, 1172), lamp=(-250, 1176), girl=(-182, 1180),
            btn=(712, 1312), pile1=(820, 1318), pile2=(915, 1322), friend=(565, 1346), girl_s=2.2)

def fork_ground(ctx, cam, p, t, lay_d=1.0, horizon=1150, wind=1.0, gust=0.0, fk=FORK, still=False):
    lay(ctx, cam, lay_d)
    rgb(ctx, p["L"][3]); ctx.rectangle(-1500, horizon, 4000, 1200); ctx.fill()
    road = mix(p["L"][2], p["L"][3], 0.35)
    J = fk["J"]
    road_band(ctx, bezier_pts((J[0], 2050), (J[0] + 10, 1700), (J[0] - 10, 1500), J, 20), 520, 120, road)
    road_band(ctx, bezier_pts(J, (J[0] - 160, J[1] - 30), (fk["L_end"][0] + 240, fk["L_end"][1] + 25), fk["L_end"], 24), 120, 34, road)
    road_band(ctx, bezier_pts(J, (J[0] + 160, J[1] - 30), (fk["R_end"][0] - 240, fk["R_end"][1] + 25), fk["R_end"], 24), 120, 34, road)

def night_backdrop(ctx, cam, t, p, moon=(850, 600, 80), clouds=True, cloud_speed=14, horizon=1150, still_t=None):
    tt = t if still_t is None else still_t
    sky(ctx, p)
    lay(ctx, cam, 0.02); stars(ctx, tt, hx("#EDE6D2"), n=80, y1=horizon - 250, a=0.85)
    if moon:
        lay(ctx, cam, 0.03); glow(ctx, moon[0], moon[1], moon[2] * 3.2, hx("#EDE6D2"), 0.12)
        disc(ctx, moon[0], moon[1], moon[2], hx("#EDE6D2"), hx("#E2D9C2"), seed=14, t=tt)
    if clouds:
        rnd = random.Random(12)
        for i in range(5):
            lay(ctx, cam, 0.05)
            w = rnd.uniform(420, 640)
            x = (rnd.uniform(-300, 1400) + cloud_speed * tt * rnd.uniform(0.6, 1.3)) % 1900 - 400
            y = rnd.uniform(280, 560)
            cloud(ctx, x, y, w, p["L"][1], 0.42, seed=40 + i)
    lay(ctx, cam, 0.1); ridge(ctx, p["L"][0], 71, 30, horizon - 110, x0=-1500, x1=2600)
    lay(ctx, cam, 0.2); ridge(ctx, p["L"][1], 72, 26, horizon - 60, x0=-1500, x1=2600)
    lay(ctx, cam, 0.35); ridge(ctx, p["L"][2], 73, 14, horizon - 12, x0=-1500, x1=2600)
    ctx.identity_matrix()

def fork_props(ctx, cam, p, t, fk, piles=(1.0, 1.0), scatter=0.0, lamp_on=1.0, wind=0.3, girl_on=True, btn_glow=0.3,
               still=False, d=1.0, pile_glow=0.18):
    lay(ctx, cam, d)
    lx, ly = fk["lamp"]
    street_lamp(ctx, lx, ly, 300 * fk.get("lamp_s", 1.0), p["L"][4], acc(LAMP), on=lamp_on, t=(0 if still else t), glow_a=0.5)
    if girl_on:
        gx, gy = fk["girl"]
        girl(ctx, gx, gy, fk["girl_s"], p["L"][4], (0 if still else t), wind=wind, facing=1)
    bx, by = fk["btn"]
    top = pedestal(ctx, bx, by, 80 * fk.get("btn_s", 1.0), 104 * fk.get("btn_s", 1.0), p["L"][4], seed=8)
    button(ctx, bx, top, 36 * fk.get("btn_s", 1.0), acc(GOLD_BTN), glow_a=btn_glow, glow_c=acc(GOLD_BTN))
    ps = fk.get("pile_s", 1.0)
    if piles[0] > 0:
        money_pile(ctx, fk["pile1"][0], fk["pile1"][1], 88 * ps, acc(MONEY), grow=piles[0], seed=3, glow_a=pile_glow, scatter=scatter, t=t)
    if piles[1] > 0:
        money_pile(ctx, fk["pile2"][0], fk["pile2"][1], 88 * ps, acc(MONEY), grow=piles[1], seed=5, glow_a=pile_glow * piles[1], scatter=scatter * 0.95, t=t)
    return top

def draw_s7(ctx, t, lt, D):
    p = NIGHT
    cam = focus_cam(1.0 + 0.07 * ease_io_sine(lt / D), 640, 1200, panx=80)
    night_backdrop(ctx, cam, t, p)
    fork_ground(ctx, cam, p, t)
    grow2 = clamp01((t - W_(7, 4)) / 1.7)
    fork_props(ctx, cam, p, t, FORK, piles=(1.0, grow2), pile_glow=0.18 + 0.12 * grow2)
    lay(ctx, cam, 1.0)
    fx, fy = FORK["friend"]
    friend_side(ctx, fx, fy, 3.0, p["L"][4], facing=1, arm_n=("ang", 10 + 4 * math.sin(t * 1.5), -12, "open"),
                arm_f=("ang", -5, -8, "open"))
    grass(ctx, p["L"][4], lambda x: 1365 + 0.0 * x, -300, 1500, t, seed=11, density=0.05, wind=0.8)
    grass(ctx, p["L"][4], lambda x: 1900, -300, 1500, t, seed=12, density=0.06, hmin=40, hmax=90, wind=0.8, wmax=10)
    ctx.identity_matrix()
    return []

def draw_s8(ctx, t, lt, D):
    p = NIGHT
    u = ease_io_sine(lt / D)
    cam = focus_cam(1.0, 640, 1200, panx=80 - 560 * u)
    night_backdrop(ctx, cam, t, p)
    fork_ground(ctx, cam, p, t)
    fork_props(ctx, cam, p, t, FORK, piles=(1.0, 1.0), wind=0.35, pile_glow=0.26)
    lay(ctx, cam, 1.0)
    fx, fy = FORK["friend"]
    info = friend_side(ctx, fx, fy, 3.0, p["L"][4], facing=-1, arm_n=("ang", 24, -10, "open"), arm_f=("ang", -6, -8, "open"))
    wg = info["wrist_g"]
    hand_w = (fx - 3.0 * (wg[0] + 3.0), fy + 3.0 * (wg[1] + 1.0))
    # girl's hand (front, about waist height)
    gx, gy = FORK["girl"]; gs = FORK["girl_s"]
    hand_g = (gx + gs * 10.5, gy - gs * 50)
    # thread: draws itself from the friend toward the girl, then tightens (pluck on "sevgan")
    t_tight = W_(8, 4)
    draw_k = ease_out((lt - 0.15) / 1.1)
    sag = 120 * (1 - ease((t - t_tight + 0.25) / 0.45)) + 6
    wob = 10 * math.sin((t - t_tight) * 40) * math.exp(-max(0, t - t_tight - 0.2) * 5) * (t > t_tight - 0.05)
    if draw_k > 0:
        ex = hand_w[0] + (hand_g[0] - hand_w[0]) * draw_k
        ey = hand_w[1] + (hand_g[1] - hand_w[1]) * draw_k
        thread(ctx, hand_w, (ex, ey), sag * draw_k, THREAD, w=2.6, wob=wob)
    grass(ctx, p["L"][4], lambda x: 1365, -700, 1500, t, seed=11, density=0.05, wind=0.9)
    grass(ctx, p["L"][4], lambda x: 1900, -700, 1500, t, seed=12, density=0.06, hmin=40, hmax=90, wind=0.9, wmax=10)
    ctx.identity_matrix()
    return []

def flying_notes(ctx, t, t0, origin, n, col, seed, spread=60):
    rnd = random.Random(seed)
    for i in range(n):
        st = t0 + rnd.uniform(0, 1.6)
        tau = t - st
        if tau <= 0: continue
        x = origin[0] + rnd.uniform(-spread, spread) + tau * rnd.uniform(260, 520) + 60 * tau * tau
        y = origin[1] - rnd.uniform(0, 60) - tau * rnd.uniform(80, 220) + 30 * math.sin(tau * 4 + i)
        a = 1 - clamp01((tau - 0.9) / 0.9)
        if a <= 0: continue
        banknote(ctx, x, y, rnd.uniform(26, 40), tau * rnd.uniform(3, 7), math.cos(tau * rnd.uniform(6, 12) + i), col, a)

def draw_s9(ctx, t, lt, D):
    p = NIGHT
    z = 0.95 - 0.11 * ease_io_sine(lt / D)
    cam = focus_cam(z, 300, 1250, panx=-250)
    gust = ease((lt - 0.3) / 0.8)
    night_backdrop(ctx, cam, t, p, cloud_speed=14 + 60 * gust)
    fork_ground(ctx, cam, p, t)
    sc = ease((lt - 0.7) / 2.1)
    fork_props(ctx, cam, p, t, FORK, piles=(1.0, 1.0), scatter=sc, wind=0.35 + 0.65 * gust, pile_glow=0.26 * (1 - sc))
    lay(ctx, cam, 1.0)
    flying_notes(ctx, t, W_(9, 0) + 0.75, (FORK["pile1"][0] + 40, FORK["pile1"][1] - 40), 22, acc(MONEY), 5)
    fx, fy = FORK["friend"]
    friend_front(ctx, fx, fy, 3.0, p["L"][4], head_dir=-0.4 + 0.25 * math.sin(lt * 1.2))
    grass(ctx, p["L"][4], lambda x: 1365, -800, 1700, t, seed=11, density=0.05, wind=1.2, gust=0.9 * gust)
    grass(ctx, p["L"][4], lambda x: 1900, -800, 1700, t, seed=12, density=0.06, hmin=40, hmax=90, wind=1.2, gust=0.9 * gust, wmax=10)
    ctx.identity_matrix()
    return []

# ------------------------------------------------------------------ scenes 10 + 14: extreme close-up, finger over the golden button
def finger_hand(ctx, tip, col, rim, rim_a, ang=0.95, s=1.0):
    """big silhouette hand with an extended index finger; tip = fingertip position"""
    pieces = [
        lambda: rrect(ctx, -165, -19, 177, 38, 19),                                                     # index finger
        lambda: smooth_path(ctx, [(-150, -26), (-205, -40), (-290, -36), (-345, 0), (-320, 52), (-240, 62), (-160, 40)], close=True),
        lambda: ellipse(ctx, -168, 36, 25, 21), lambda: ellipse(ctx, -212, 50, 25, 21), lambda: ellipse(ctx, -256, 54, 25, 21),
        lambda: smooth_path(ctx, [(-250, -38), (-190, -46), (-150, -40), (-168, -26), (-236, -24)], close=True),   # thumb
        lambda: poly(ctx, [(-300, -38), (-900, -120), (-900, 170), (-300, 56)]),
    ]
    for (dx, dy, c, a) in ((-3.5, -3.5, rim, rim_a), (0, 0, col, 1.0)):
        ctx.save(); ctx.translate(tip[0] + dx, tip[1] + dy); ctx.rotate(ang); ctx.scale(s, s)
        ctx.push_group()
        for pc in pieces:
            ctx.new_path(); pc(); rgb(ctx, c); ctx.fill()
        ctx.pop_group_to_source(); ctx.paint_with_alpha(a)
        ctx.restore()

def draw_closeup(ctx, t, lt, D, cam, p, bcx, bcy, rx, tip, piles=True, pulse=0.0, still=False):
    sky(ctx, p)
    lay(ctx, cam, 0.03)
    glow(ctx, 900, 260, 520, hx("#EDE6D2"), 0.16)
    stars(ctx, t if not still else 0, hx("#EDE6D2"), n=40, y1=700, a=0.6)
    lay(ctx, cam, 0.12); ridge(ctx, p["L"][1], 81, 30, 1020)
    lay(ctx, cam, 0.25); ridge(ctx, p["L"][2], 82, 22, 1110)
    lay(ctx, cam, 1.0)
    # pedestal top (huge) and dome
    rgb(ctx, p["L"][4]); poly(ctx, [(bcx - rx * 1.9, bcy + 10), (bcx + rx * 1.9, bcy + 10), (bcx + rx * 2.3, 2100), (bcx - rx * 2.3, 2100)]); ctx.fill()
    rgb(ctx, hx("#EDE6D2"), 0.18); ctx.set_line_width(3); ctx.move_to(bcx - rx * 1.9, bcy + 10); ctx.line_to(bcx + rx * 1.9, bcy + 10); ctx.stroke()
    if piles:
        for j, (ox, sz) in enumerate(((rx * 1.38, rx * 0.95), (rx * 1.38, rx * 0.95))):
            ga = 0.22 + 0.16 * pulse
            money_pile(ctx, bcx + ox, bcy + 8 - j * rx * 0.62, sz, MONEY, glow_a=ga if j == 0 else 0, seed=3 + j)
    button(ctx, bcx, bcy, rx, GOLD_BTN, glow_a=0.22 + 0.06 * pulse, glow_c=GOLD_BTN, rim=(hx("#F4EEDC"), 0.35))
    finger_hand(ctx, tip, p["L"][4], hx("#EDE6D2"), 0.55, ang=0.95)
    ctx.identity_matrix()

def draw_s10(ctx, t, lt, D):
    p = NIGHT
    cam = focus_cam(1.0 + 0.05 * ease_io_sine(lt / D), 540, 1180)
    pulse = 0.5 + 0.5 * math.sin(lt * 3.2)
    bob = 10 * math.sin(lt * 2.4)
    draw_closeup(ctx, t, lt, D, cam, p, 470, 1290, 250, (468, 1060 + bob), piles=True, pulse=pulse)
    return []

def draw_s14(ctx, t, lt, D):
    p = NIGHT
    t_freeze = W_(14, 3)
    tf = min(t, t_freeze); ltf = tf - TL.SC_START[14]
    still = t >= t_freeze
    cam = focus_cam(1.0 + 0.06 * ease_io_sine(ltf / 2.1), 480, 1150)
    hes = 12 * math.sin(ltf * 5.0) * (0.6 + 0.4 * math.sin(ltf * 1.7)) - 18 * ease(ltf / 1.4)
    draw_closeup(ctx, tf, ltf, D, cam, p, 480, 1330, 330, (478, 1078 + hes), piles=False, pulse=0.5 + 0.5 * math.sin(ltf * 3.0), still=still)
    # timer appears and ticks (stepped hand)
    ta = ease_out_back((ltf - 0.2) / 0.3)
    if ta > 0:
        steps = math.floor(max(0, ltf - 0.3) / 0.25)
        frac = min(1.0, steps / 12.0 + 0.02)
        ctx.identity_matrix()
        ctx.save(); ctx.translate(838, 760); ctx.scale(ta, ta)
        timer_icon(ctx, 0, 0, 58, MONEY, frac, a=1.0)
        ctx.restore()
    return [("__still__", 1.0 if still else 0.0)]

# ------------------------------------------------------------------ scene 11: behind the friend, wind stops, hero-shaped dust drifts by
FORK11 = dict(J=(540, 1215), L_end=(120, 1092), R_end=(960, 1092), lamp=(96, 1098), girl=(150, 1102), girl_s=1.45, lamp_s=0.62,
              btn=(890, 1092), pile1=(955, 1097), pile2=(1010, 1100), btn_s=0.62, pile_s=0.58)

def draw_s11(ctx, t, lt, D):
    p = NIGHT
    still_k = ease(lt / 0.6)          # wind dies down
    wind = 0.8 * (1 - still_k)
    cam = focus_cam(1.0 + 0.08 * ease_io_sine(lt / D), 540, 1250)
    t_fr = TL.SC_START[11] + 0.6
    tt = t if lt < 0.6 else t_fr
    night_backdrop(ctx, cam, tt, p, horizon=1080, cloud_speed=14)
    fork_ground(ctx, cam, p, t, horizon=1078, fk=FORK11)
    fork_props(ctx, cam, p, tt, FORK11, piles=(1.0, 1.0), wind=0.15 * (1 - still_k), btn_glow=0.42, pile_glow=0.3, still=lt > 0.6)
    lay(ctx, cam, 1.0)
    friend_back(ctx, 540, 1450, 4.4, p["L"][4], sway=0)
    # hero-shaped dust drifting past on its own (the wind has stopped)
    ps = hero_particles()
    sx0 = -180 + 1460 * (lt / D)
    for (ox, oy, col, sz, r1, r2, r3) in ps[:1100]:
        loos = lt / D
        x = sx0 + 3.0 * ox + (r1 - 0.5) * 60 * loos + 6 * math.sin(lt * 1.3 + r2 * 9)
        y = 1440 + 3.0 * oy + (r3 - 0.5) * 40 * loos - 10 * loos * r2 + 4 * math.sin(lt * 1.7 + r1 * 7)
        q = 2.9 * sz
        rgb(ctx, mix(col, hx("#EDE6D2"), 0.3), 0.55 * (0.6 + 0.4 * r2)); ctx.rectangle(x, y, q, q); ctx.fill()
    grass(ctx, p["L"][4], lambda x: 1900, -300, 1400, tt, seed=12, density=0.05, hmin=40, hmax=90, wind=max(0.05, wind), wmax=10)
    ctx.identity_matrix()
    return []

# ------------------------------------------------------------------ scene 12: CTA - hero points at the girl's road (bir) and the money (ikki)
FORK12 = dict(J=(540, 1250), L_end=(130, 1105), R_end=(950, 1105), lamp=(104, 1112), girl=(160, 1116), girl_s=1.55, lamp_s=0.66,
              btn=(880, 1104), pile1=(948, 1108), pile2=(1006, 1112), btn_s=0.66, pile_s=0.62)

def arm_raise(t, t_full, t_down, up=0.22, down=0.22):
    return ease((t - (t_full - up)) / up) * (1 - ease((t - t_down) / down))

def draw_s12(ctx, t, lt, D):
    p = NIGHT
    cam = focus_cam(1.0 + 0.02 * ease_io_sine(lt / D), 540, 1250)
    night_backdrop(ctx, cam, t, p, horizon=1110, cloud_speed=10)
    fork_ground(ctx, cam, p, t, horizon=1108, fk=FORK12)
    fork_props(ctx, cam, p, t, FORK12, piles=(1.0, 1.0), wind=0.3, btn_glow=0.34, pile_glow=0.22)
    lay(ctx, cam, 1.0)
    grass(ctx, p["L"][4], lambda x: 1900, -300, 1400, t, seed=12, density=0.05, hmin=40, hmax=90, wind=0.6, wmax=10)
    t_bir, t_ikki, t_izoh, t_yoz = W_(12, 2), W_(12, 5), W_(12, 6), W_(12, 7)
    hx0, hy0, hs = 540, 1388, 4.4
    t_turn = TL.SC_START[12] + 0.78
    over = []
    if t < t_turn:
        k = ease_out((t - TL.SC_START[12]) / 0.78)
        x = 1010 + (hx0 - 1010) * k
        wp = (t - TL.SC_START[12]) * 10.0
        hero_side(ctx, x, hy0, hs, facing=-1, walk=wp,
                  arm_n=("ang", -18 * math.sin(wp), -10, "open"), arm_f=("ang", 18 * math.sin(wp), -14, "open"))
    else:
        sq = 1 - 0.18 * math.exp(-(t - t_turn) * 18)
        ctx.save(); ctx.translate(hx0, hy0); ctx.scale(sq, 1); ctx.translate(-hx0, -hy0)
        a_l = arm_raise(t, t_bir, t_bir + 0.55)              # point at the girl's road on "bir"
        a_r = arm_raise(t, t_ikki, t_ikki + 0.6)             # point at the money on "ikki"
        b_l = arm_raise(t, t_izoh + 0.12, t_yoz - 0.05, up=0.16, down=0.14)   # alternate between 1 and 2 on "Izohga yozing"
        b_r = arm_raise(t, t_yoz + 0.12, 99, up=0.16)
        def spec(a_pt, b_pt, rest):
            if b_pt > 0.01:
                return ("ang", rest + (158 - rest) * b_pt, -4 * b_pt, "point")
            return ("ang", rest + (110 - rest) * a_pt, -4 * a_pt, "point" if a_pt > 0.5 else "open")
        hero_front(ctx, hx0, hy0, hs, arm_l=spec(a_l, b_l, 8), arm_r=spec(a_r, b_r, 8), blink=(int(t * 30) % 97) < 3)
        ctx.restore()
        # number tags at the road ends
        for (tt, pos, txt) in ((t_bir, (160, 925), "1"), (t_ikki, (935, 985), "2")):
            if t >= tt - 1e-6:
                pk = 0.45 + 0.55 * ease_out_back((t - tt) / 0.2, 2.4)   # already visible on the word's frame
                ctx.save(); ctx.translate(*pos); ctx.scale(pk, pk)
                fill_ellipse(ctx, 0, 0, 34, 34, acc(MONEY))
                ctx.restore()
                over.append(("tag", txt, pos[0], pos[1], 44 * pk))
    # comment bubble on "Izohga"
    if t >= t_izoh - 1e-6:
        pk = min(1.0, 0.55 + 0.45 * ease_out_back((t - t_izoh) / 0.22, 2.2))
        speech_bubble(ctx, 540, 820, 360, 170, acc(MONEY), pop=pk)
        ctx.save(); ctx.translate(540, 820); ctx.scale(pk, pk)
        rgb(ctx, darken(acc(MONEY), 0.35)); ctx.rectangle(-2.5, -52, 5, 104); ctx.fill()
        ctx.restore()
        over.append(("bubble", "1", 540 - 85 * pk, 816, 104 * pk))
        over.append(("bubble", "2", 540 + 85 * pk, 816, 104 * pk))
    ctx.identity_matrix()
    return over

# ------------------------------------------------------------------ scene 13: CTA - paper airplane
def draw_s13(ctx, t, lt, D):
    p = NIGHT
    t_unga, t_yub, t_qan = W_(13, 2), W_(13, 3), W_(13, 5)
    if t < t_qan - 1e-6:
        # shot A: medium on the hero, folding and throwing the airplane
        cam = focus_cam(1.0 + 0.04 * ease_io_sine(lt / 2.5), 480, 1200)
        night_backdrop(ctx, cam, t, p, horizon=1160, cloud_speed=10, moon=(840, 420, 80))
        fk = dict(FORK12); fk.update(J=(700, 1250))
        fork_ground(ctx, cam, p, t, lay_d=0.6, horizon=1158, fk=dict(J=(760, 1250), L_end=(300, 1160), R_end=(1300, 1160)))
        lay(ctx, cam, 0.6)
        street_lamp(ctx, 150, 1196, 230, p["L"][4], acc(LAMP), on=1.0, t=t, glow_a=0.45)
        lay(ctx, cam, 1.0)
        rgb(ctx, mix(p["L"][3], p["L"][4], 0.5)); ctx.rectangle(-300, 1395, 1800, 700); ctx.fill()
        grass(ctx, mix(p["L"][3], p["L"][4], 0.5), lambda x: 1398, -300, 1400, t, seed=21, density=0.08, hmin=16, hmax=40, wind=0.6)
        hs = 4.6; hx_, hy_ = 430, 1400
        fold = ease((t - TL.SC_START[13] - 0.1) / 1.15)
        state = {}
        if t < t_unga:
            arm_n = ("tgt", (10.5, -64.0 + 1.5 * math.sin(t * 6) * (fold < 1)), -1, "fist")
            arm_f = ("tgt", (8.5, -62.5), -1, "fist")
        elif t < t_yub:
            k = ease((t - t_unga) / (t_yub - t_unga))
            arm_n = ("ang", 40 + (175 - 40) * k, -70 + 40 * k, "fist")      # wind-up: plane goes back over the shoulder
            arm_f = ("ang", 20 + 40 * k, -40, "open")
        else:
            k = ease_out((t - t_yub) / 0.16)
            arm_n = ("ang", 175 - (175 - 70) * k, -30 + 30 * k, "open")
            arm_f = ("ang", 60 - 50 * k, -40 + 30 * k, "open")
        def hold(c, info):
            if t < t_yub + 0.05:
                w = info["wrist"]; fa = info["fa"]
                if t < t_unga:
                    paper_plane(c, w[0] + 2.0, w[1] - 3.0, 0.42, -0.1, acc(MONEY), fold=fold)
                else:
                    paper_plane(c, w[0] + math.cos(fa) * 3, w[1] + math.sin(fa) * 3 - 2, 0.42, fa - 0.6, acc(MONEY), fold=1.0)
        info = hero_side(ctx, hx_, hy_, hs, facing=1, arm_n=arm_n, arm_f=arm_f, hold=hold, lean=(-4 if t > t_unga else 0))
        if t >= t_yub + 0.05:
            # released: flies to the right and out of frame
            tau = t - t_yub - 0.05
            x = hx_ + 4.6 * 12 + 1500 * tau + 600 * tau * tau
            y = hy_ - 4.6 * 96 - 520 * tau + 260 * tau * tau
            paper_plane(ctx, x, y, 2.4, -0.32 + 0.3 * tau, acc(MONEY), fold=1.0)
            # soft motion streaks
            rgb(ctx, acc(MONEY), 0.25 * (1 - clamp01(tau / 0.4)))
            ctx.set_line_width(3)
            for j in range(3):
                ctx.move_to(x - 40, y + (j - 1) * 10); ctx.line_to(x - 140 - 30 * j, y + (j - 1) * 10 + 40); ctx.stroke()
        ctx.identity_matrix()
        return [("__hero__", 1.0)]
    # shot B: wide on the fork, the plane lands in the friend's hand, he looks from the girl to the button and back
    lt2 = t - t_qan
    cam = focus_cam(1.0 + 0.03 * ease_io_sine(lt2 / 2.0), 540, 1250)
    night_backdrop(ctx, cam, t, p, horizon=1110, cloud_speed=10)
    fork_ground(ctx, cam, p, t, horizon=1108, fk=FORK12)
    fork_props(ctx, cam, p, t, FORK12, piles=(1.0, 1.0), wind=0.3, btn_glow=0.36, pile_glow=0.24)
    lay(ctx, cam, 1.0)
    grass(ctx, p["L"][4], lambda x: 1900, -300, 1400, t, seed=12, density=0.05, hmin=40, hmax=90, wind=0.6, wmax=10)
    fx, fy, fs = 540, 1380, 3.4
    t_land = t_qan + 0.78
    catch = ease((t - (t_land - 0.42)) / 0.42)
    arm_r = ("ang", 8 + (128 - 8) * catch, -30 * catch, "open")
    # head: follows the plane, freezes, then girl (left) -> button (right) -> back to the girl
    if t < t_land: hd = -0.5
    elif t < t_land + 0.18: hd = -0.5
    else:
        s1 = ease((t - (t_land + 0.18)) / 0.5)
        s2 = ease((t - (t_land + 0.95)) / 0.5)
        hd = -1.0 * (1 - s1) + 1.0 * s1
        hd = hd * (1 - s2) + (-1.0) * s2
        hd = min(hd, 1.0) if t >= t_land + 0.18 else -0.5
        if t < t_land + 0.18 + 0.001: hd = -0.5
    hand_pos = {}
    def hold(c, info):
        if 1 in info:
            hand_pos["w"] = info[1]["wrist"]
    info = friend_front(ctx, fx, fy, fs, p["L"][4], head_dir=hd, arm_l=("ang", 6, -4, "open"), arm_r=arm_r, hold=hold)
    w = info[1]["wrist"]
    hwx, hwy = fx + fs * w[0], fy + fs * w[1]
    if t < t_land:
        k = clamp01((t - t_qan) / (t_land - t_qan))
        e = ease_io_sine(k)
        x0, y0 = -80, 640
        x = x0 + (hwx + 10 - x0) * e
        y = y0 + (hwy - 22 - y0) * e - 120 * math.sin(math.pi * e)
        paper_plane(ctx, x, y, 2.3, 0.25 - 0.35 * e + 0.08 * math.sin(k * 12), acc(MONEY), fold=1.0)
    else:
        paper_plane(ctx, hwx + 10, hwy - 22, 2.3, -0.1, acc(MONEY), fold=1.0)
    ctx.identity_matrix()
    return [("__hero__", 0.0)]

SCENE_FN = {1: draw_s1, 2: draw_s2, 3: draw_s3, 4: draw_s4, 5: draw_s5, 6: draw_s6, 7: draw_s7, 8: draw_s8,
            9: draw_s9, 10: draw_s10, 11: draw_s11, 12: draw_s12, 13: draw_s13, 14: draw_s14}
HERO_SCENES = {1, 3, 4, 5, 12}
