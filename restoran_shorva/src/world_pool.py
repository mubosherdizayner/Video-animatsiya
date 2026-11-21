# Pool-side dusk world from the reference: sky, sun, birds, mountains, minaret, peshtoq, houses,
# gate, ishkom, mulberry tree, bank, rippled reflection with sun path, falling leaves, giant kosa.
import math, random
import numpy as np
from PIL import Image, ImageFilter
from common import *

WATER_Y = 1340.0
BANK_Y = 1305.0

def sky(cv, top=SKY_TOP, bot=SKY_BOT, y0=0.0, y1=980.0, warm=0.0):
    """world-space vertical gradient over the whole canvas"""
    hs = cv.im.height
    ys = np.arange(hs, dtype=np.float32) / cv.ss
    wy = cv.ecy + (ys - 960 - cv.oy) / cv.ez
    t = np.clip((wy - y0) / (y1 - y0), 0, 1)[:, None]
    c0, c1 = np.array(top, np.float32), np.array(bot, np.float32)
    col = c0 * (1 - t) + c1 * t
    if warm > 0:
        w0, w1 = np.array(hx("EBC9A0"), np.float32), np.array(hx("F3D2AE"), np.float32)
        col = col * (1 - warm) + (w0 * (1 - t) + w1 * t) * warm
    colimg = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)[:, None, :].repeat(1, 1), "RGB")
    cv.im.paste(colimg.resize((cv.im.width, hs), Image.NEAREST), (0, 0))

BIRDS = [(330, 442, 1.0, 0.0), (432, 377, 0.72, 1.3), (700, 525, 0.95, 2.1), (770, 476, 0.74, 0.7), (880, 557, 0.6, 2.9)]
def birds(cv, te, P, color=hx("3A474B"), items=BIRDS, drift=1.0):
    for k, (bx, by, sc, ph) in enumerate(items):
        w = 2 * math.pi / P
        x = bx + drift * (14 * math.sin(w * 3 * te + ph) + 6 * math.sin(w * 7 * te + ph * 2))
        y = by + drift * (6 * math.sin(w * 5 * te + ph * 1.7))
        f = math.sin(2 * math.pi * (te * 1.6 + ph * 0.37))   # flap
        span = 26 * sc
        tip = -7 * sc * f
        pts = [(x - span, y + tip - 2 * sc), (x - span * 0.45, y - 6 * sc - 2 * sc * f), (x, y),
               (x + span * 0.45, y - 6 * sc - 2 * sc * f), (x + span, y + tip - 2 * sc)]
        cv.line(pts, color, 3.4 * sc)

MTN_BACK = [(-60, 905), (0, 900), (90, 870), (225, 828), (330, 862), (425, 846), (520, 880), (600, 846), (700, 870),
            (790, 820), (900, 858), (1000, 880), (1080, 872), (1140, 880)]
MTN_FRONT = [(-60, 965), (0, 960), (60, 948), (125, 928), (205, 950), (300, 936), (420, 918), (520, 950), (620, 938),
             (700, 926), (820, 946), (950, 930), (1080, 950), (1140, 955)]

def mountains(cv):
    cv.poly(MTN_BACK + [(1140, 1340), (-60, 1340)], MTN1)
    cv.poly(MTN_FRONT + [(1140, 1340), (-60, 1340)], MTN2)

def city(cv):
    c, cd = CITY, CITY_D
    # minaret (Kalon style)
    cv.poly([(205, 1160), (213, 750), (246, 750), (253, 1160)], c)
    cv.poly([(203, 752), (256, 752), (264, 738), (196, 738)], c)          # corbel
    cv.rect(197, 668, 263, 740, c)                                          # lantern
    cv.poly([(194, 672), (266, 672), (262, 660), (198, 660)], c)
    for wx in (212, 227, 242):
        cv.rect(wx - 3.5, 684, wx + 3.5, 712, MTN2, r=3)
    cv.poly(ellipse_pts(230, 662, 21, 18, 20, 180, 360), c)
    cv.rect(228.5, 632, 231.5, 646, c)
    for by in (905, 1010):
        cv.line([(208, by), (250, by)], hx("97A9AB"), 2.2)
    # small dome left
    cv.rect(95, 1045, 185, 1160, c)
    cv.poly(ellipse_pts(140, 1048, 46, 30, 24, 180, 360), c)
    cv.rect(138.5, 1008, 141.5, 1020, c)
    # arched building
    cv.rect(405, 1025, 486, 1160, c)
    cv.poly(ellipse_pts(445.5, 1026, 40.5, 42, 24, 180, 360), c)
    # peshtoq with guldasta
    cv.rect(612, 870, 760, 1160, c)
    cv.rect(585, 868, 614, 1160, c)
    cv.poly(ellipse_pts(599.5, 870, 14.5, 16, 14, 180, 360), c)
    cv.rect(760, 1000, 880, 1160, c)
    cv.poly(ellipse_pts(840, 1004, 62, 52, 26, 180, 360), c)
    # niche of the portal (pointed arch)
    arch = [(640, 1160), (640, 990)] + [(700 + 60 * math.cos(math.radians(a)), 990 + 0.0 - 60 * math.sin(math.radians(a)) * 0.9)
                                         for a in range(180, -1, -15)] + [(760, 1160)]
    cv.poly([(p[0] if p[0] <= 760 else 760, p[1]) for p in arch], cd)
    cv.poly([(560, 1160), (560, 1050), (612, 1050), (612, 1160)], c)
    cv.rect(-60, 1110, 1140, 1180, c)

def houses(cv, lit=1.0):
    h = HOUSE
    cv.rect(-60, 1118, 240, 1310, h)
    cv.rect(240, 1150, 1140, 1310, h)
    cv.rect(755, 1102, 1140, 1310, h)
    for x in range(-40, 240, 34): cv.rect(x, 1122, x + 12, 1128, GATE)
    for x in range(256, 545, 34): cv.rect(x, 1155, x + 12, 1161, GATE)
    for x in range(770, 1100, 34): cv.rect(x, 1106, x + 12, 1112, GATE)
    wc = lerpc(GATE, WIN, lit)
    cv.rect(128, 1182, 142, 1201, wc, r=2)
    cv.rect(788, 1176, 802, 1196, wc, r=2)
    # gate
    cv.rect(545, 1131, 705, 1150, GATE)
    cv.rect(558, 1145, 692, 1310, GATE)
    cv.poly(ellipse_pts(625, 1150, 67, 12, 20, 180, 360), GATE)
    cv.line([(625, 1150), (625, 1305)], hx("3B4C50"), 3)
    for gx in (590, 660):
        cv.circle(gx, 1225, 3, hx("3B4C50"))

def ishkom(cv):
    n1 = NEAR1
    cv.rect(30, 1062, 41, 1306, n1)
    cv.rect(205, 1062, 216, 1306, n1)
    cv.rect(-60, 1060, 264, 1071, n1)
    rnd = random.Random(4)
    for k in range(22):
        x = -50 + k * 15.5
        r = 10 + rnd.random() * 6
        cv.circle(x, 1058 + rnd.uniform(-3, 4), r, n1)
    cv.circle(255, 1062, 9, n1)
    for (gx, gy) in ((86, 1098), (150, 1100)):
        for j in range(11):
            row = int((math.sqrt(8 * j + 1) - 1) / 2)
            cx = gx + (j - row * (row + 1) / 2 - row / 2) * 7.5
            cv.circle(cx, gy + row * 7.5 - 6 + (j % 2), 4.2, n1)
        cv.line([(gx, gy - 24), (gx + 2, gy - 10)], n1, 2)

CANOPY = [(800, 962, 88), (840, 890, 80), (920, 850, 72), (985, 880, 80), (1040, 950, 82), (960, 960, 100),
          (880, 975, 95), (770, 1010, 55), (1045, 1030, 52), (1095, 900, 60)]
def _in_canopy(x, y, m=0):
    return any((x - cx) ** 2 + (y - cy) ** 2 < (r - m) ** 2 for cx, cy, r in CANOPY)

_LEAFDOTS = None
def leafdots():
    global _LEAFDOTS
    if _LEAFDOTS is None:
        rnd = random.Random(21); out = []
        while len(out) < 175:
            x, y = rnd.uniform(700, 1150), rnd.uniform(770, 1090)
            if not _in_canopy(x, y, 6): continue
            if rnd.random() > 0.45 + 0.5 * ((x - 700) / 450): continue   # denser on the sunlit side
            out.append((x, y, rnd.uniform(4, 8.5), rnd.uniform(2.6, 4.6), rnd.uniform(0, 180), LEAF1 if rnd.random() < 0.55 else LEAF2))
        _LEAFDOTS = out
    return _LEAFDOTS

def tree(cv, sway=0.0):
    cv.poly([(905, 1306), (912, 1250), (905, 1180), (889, 1120), (876, 1060), (896, 1060), (911, 1118), (934, 1182),
             (950, 1250), (965, 1306)], NEAR1)
    cv.poly([(897, 1100), (930, 1040), (944, 1046), (910, 1112)], NEAR1)
    for i, (cx, cy, r) in enumerate(CANOPY):
        cv.circle(cx + sway * (cy - 1100) / 300, cy, r, NEAR2 if i in (3, 9) else NEAR1)
    for (x, y, rx, ry, a, col) in leafdots():
        cv.poly(ellipse_pts(x + sway * (y - 1100) / 300, y, rx, ry, 8, ang=a), col)

def bank(cv):
    cv.rect(-60, BANK_Y, 1140, WATER_Y + 1, BANK)
    cv.rect(-60, BANK_Y, 1140, BANK_Y + 2.5, NEAR2)
    for x in range(0, 1100, 120):
        cv.line([(x, BANK_Y + 4), (x, WATER_Y)], hx("253034"), 1.6, caps=False)

def leaves_falling(cv, te, P, n=16, seed=7, region=(700, 1080, 860, 1060), floor=1330.0, wind=-28.0, up=False):
    rnd = random.Random(seed)
    for k in range(n):
        m = rnd.choice((5, 6, 7))
        per = P / m
        off = rnd.uniform(0, per)
        x0 = rnd.uniform(region[0], region[1]); y0 = rnd.uniform(region[2], region[3])
        vy = rnd.uniform(60, 95); amp = rnd.uniform(10, 26); fr = rnd.uniform(0.5, 0.9)
        rs = rnd.uniform(-160, 160); col = LEAF1 if k % 2 else LEAF2; sz = rnd.uniform(5.5, 8)
        u = (te + off) % per
        life = min(per * 0.95, (floor - y0) / vy) if not up else per * 0.95
        if u > life: continue
        y = y0 + vy * u if not up else y0 - vy * u
        x = x0 + wind * u + amp * math.sin(2 * math.pi * fr * u + k)
        fade = min(1.0, u / 0.25, (life - u) / 0.35)
        if fade <= 0: continue
        a = rs * u + 25 * math.sin(2 * math.pi * fr * u)
        c = col + (int(255 * fade),)
        cv.poly(ellipse_pts(x, y, sz, sz * 0.55, 10, ang=a), c)

def giant_kosa(cv, cx, base_y, k, door_open=0.0, t=0.0):
    """house-sized kosa (scale k = rim half-width / 22.5) with a carved wooden door"""
    rim_y = base_y - 25 * k
    pts_l, pts_r = [], []
    for i in range(17):
        v = i / 16
        hw = max(9.5 * k, 22.5 * k * math.sqrt(max(0, 1 - v * v)))
        pts_l.append((cx - hw, rim_y + v * 21 * k)); pts_r.append((cx + hw, rim_y + v * 21 * k))
    body = pts_l + [(cx - 9.5 * k, base_y), (cx + 9.5 * k, base_y)] + pts_r[::-1]
    cv.poly(body, BOWL)
    shade = pts_l + [(cx - 9.5 * k, base_y), (cx - 5 * k, base_y)] + [(x + 6 * k * (1 - abs(i - 8) / 16), y) for i, (x, y) in enumerate(pts_l)][::-1]
    cv.poly(shade, (214, 206, 190))
    band = pts_l[2:6] + pts_r[2:6][::-1]
    cv.poly(band, BOWL_BAND)
    for j in range(11):
        bx = cx - 18 * k + j * 3.6 * k
        cv.poly(ellipse_pts(bx, rim_y + 7.3 * k, 0.9 * k, 0.9 * k, 10), BOWL)
    cv.poly(ellipse_pts(cx, rim_y, 22.5 * k, 4.2 * k, 40), BOWL)
    cv.poly(ellipse_pts(cx, rim_y + 0.6 * k, 19.5 * k, 2.8 * k, 40), (201, 176, 132))
    # door (arched), opening = horizontal squash toward the hinge on the left
    dw, dh = 4.6 * k, 9.6 * k
    x0, y1 = cx - dw / 2, base_y
    inner = [(x0, y1), (x0, y1 - dh + dw / 2)] + ellipse_pts(cx, y1 - dh + dw / 2, dw / 2, dw / 2, 12, 180, 360) + [(x0 + dw, y1)]
    cv.poly(inner, lerpc(BANK, WIN, door_open * 0.85))
    if door_open > 0.02:
        # warm light spilling from the doorway
        cv.poly([(x0, y1), (x0 + dw, y1), (x0 + dw + 40 * door_open * k / 10, y1 + 2), (x0 - 10, y1 + 2)], WIN + (int(90 * door_open),))
    sq = 1 - 0.86 * door_open
    door = [(x0 + (px - x0) * sq, py) for px, py in inner]
    cv.poly(door, GATE)
    # carving on the door
    if sq > 0.25:
        for j in range(3):
            yy = y1 - dh * (0.25 + 0.25 * j)
            cv.poly([(x0 + dw * 0.5 * sq, yy - 0.9 * k), (x0 + dw * 0.7 * sq, yy), (x0 + dw * 0.5 * sq, yy + 0.9 * k), (x0 + dw * 0.3 * sq, yy)], hx("3A4A4E"))
    cv.circle(x0 + dw * 0.82 * sq, y1 - dh * 0.42, 0.45 * k, hx("2E3A3D"))
    return rim_y

def draw_pool(cv, te, P, tree_sway=True, kosa=None, leaves=True, hero_fn=None, birds_on=True):
    """kosa: dict(cx, base, k, door, t) or None; hero_fn(cv) draws the hero"""
    sky(cv)
    cv.layer(1.0)
    draw_sun(cv, 560, 640, 270)
    if birds_on: birds(cv, te, P)
    mountains(cv)
    city(cv)
    houses(cv)
    ishkom(cv)
    tree(cv, sway=(2.2 * math.sin(2 * math.pi * 4 * te / P)) if tree_sway else 0.0)
    bank(cv)
    if kosa: giant_kosa(cv, kosa["cx"], kosa["base"], kosa["k"], kosa.get("door", 0.0), te)
    if hero_fn: hero_fn(cv)
    if leaves: leaves_falling(cv, te, P)

# ---------------------------------------------------------------- water
WATER_TINT = np.array([98, 116, 120], np.float32)
_streaks = None
def _streak_list():
    global _streaks
    if _streaks is None:
        rnd = random.Random(12)
        _streaks = [(rnd.uniform(-50, 1130), rnd.uniform(WATER_Y + 8, 1915), rnd.uniform(30, 190), rnd.uniform(0, 6.28), rnd.choice((2, 3, 4)))
                    for _ in range(46)]
    return _streaks

def reflect(img, cv, te, P, sun_x=560.0, extra=None, water_y=WATER_Y, tint=None, mix0=0.47, streaks=1.0, depth_px=560.0, amp0=0.8):
    """img: 1x RGB frame with everything above the water drawn. Mirrors it below the waterline."""
    z = cv.ez
    wl = cv.to_screen(0, water_y)[1]
    tint = WATER_TINT if tint is None else np.array(tint, np.float32)
    if wl >= H - 1: return img
    arr = np.asarray(img).astype(np.float32)
    wl_i = int(math.ceil(wl))
    rows = np.arange(wl_i, H, dtype=np.float32)
    d = rows - wl
    dw = d / z
    w = 2 * math.pi / P
    band = np.floor(dw / 3.0) * 3.0
    amp = (amp0 + 0.03 * dw) * z
    dx = amp * (np.sin(band * 0.085 - w * 22 * te) + 0.55 * np.sin(band * 0.23 + w * 13 * te) + 0.3 * np.sin(band * 0.61 - w * 31 * te))
    src = np.clip(np.round(2 * wl - rows - 1).astype(int), 0, H - 1)
    cols = np.clip(np.round(np.arange(W)[None, :] - dx[:, None]).astype(int), 0, W - 1)
    refl = arr[src[:, None], cols]
    rimg = Image.fromarray(np.clip(refl, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6 * min(z, 1.6)))
    refl = np.asarray(rimg).astype(np.float32)
    depth = np.clip(dw / depth_px, 0, 1)[:, None, None]
    mix = mix0 + 0.08 * depth
    refl = refl * (1 - mix) + tint * mix
    refl *= (1.02 - 0.08 * depth)
    arr[wl_i:] = refl
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    # light ripple streaks + sun path
    cv2 = Canvas.__new__(Canvas); cv2.ss = 1; cv2.im = out; cv2.d = ImageDraw.Draw(out, "RGBA"); cv2.cam = cv.cam
    cv2.layer(1.0); cv2.ox, cv2.oy = cv.ox, cv.oy
    for (x, y, L, ph, m) in _streak_list():
        if streaks <= 0: break
        y = y - WATER_Y + water_y
        a = 0.5 + 0.5 * math.sin(w * m * 3 * te + ph)
        xx = x + 6 * math.sin(w * m * te + ph)
        cv2.line([(xx, y), (xx + L, y)], (196, 204, 200, int((60 * a + 15) * streaks)), 1.6, caps=False)
    for j in range(26):
        if sun_x is None: break
        y = water_y + 6 + j * 17 + 4 * math.sin(j * 1.7)
        if y > water_y + 470: break
        fall = 1 - (y - water_y) / 470
        half = (22 + 60 * (1 - fall) * 0.6) * (0.6 + 0.4 * math.sin(w * 18 * te + j * 2.3) ** 2)
        xx = sun_x + 18 * math.sin(j * 2.1 + w * 9 * te)
        cv2.line([(xx - half, y), (xx + half, y)], SUN_A + (int(120 * fall ** 1.3),), 2.4, caps=False)
    if extra: extra(cv2)
    return out
