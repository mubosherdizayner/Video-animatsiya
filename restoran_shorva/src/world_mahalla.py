# Mahalla street at dusk: mountains, far dome/minaret, flat-roofed paxsa houses with protruding beams,
# ishkom, choyxona / oshxona with signs that light up, a third empty sign with "?".
import math, random
from common import *
from world_pool import sky, birds
from world_paris import _sign_text

GROUND = 1600.0
WATER_M = 1660.0
SIGNS = {"A": (330, 1262), "B": (790, 1262), "C": (1250, 1262)}
SIGN_W, SIGN_H = 320, 80

def _teapot(cv, cx, cy, k, col):
    cv.poly(ellipse_pts(cx, cy + 3 * k, 15 * k, 12 * k, 20), col)
    cv.rect(cx - 9 * k, cy - 12 * k, cx + 9 * k, cy - 6 * k, col)
    cv.circle(cx, cy - 14 * k, 3 * k, col)
    cv.poly([(cx + 12 * k, cy + 2 * k), (cx + 26 * k, cy - 10 * k), (cx + 28 * k, cy - 7 * k), (cx + 14 * k, cy + 8 * k)], col)
    cv.line([(cx - 13 * k, cy - 3 * k), (cx - 22 * k, cy + 1 * k), (cx - 14 * k, cy + 9 * k)], col, 3.2 * k)

def _qozon(cv, cx, cy, k, col):
    cv.poly([(cx - 24 * k, cy - 6 * k)] + ellipse_pts(cx, cy - 6 * k, 24 * k, 20 * k, 18, 0, 180) + [(cx + 24 * k, cy - 6 * k)], col)
    cv.rect(cx - 28 * k, cy - 9 * k, cx + 28 * k, cy - 5 * k, col)
    for sx in (-1, 1):
        cv.line([(cx + sx * 24 * k, cy - 4 * k), (cx + sx * 31 * k, cy - 1 * k)], col, 3 * k)
    cv.poly(ellipse_pts(cx, cy - 14 * k, 18 * k, 5 * k, 16, 180, 360), col)
    cv.circle(cx, cy - 19 * k, 2.6 * k, col)

def sign(cv, key, lit, text=None, icon=None, q=0.0, t=0.0):
    cx, cy = SIGNS[key]
    x0, y0, x1, y1 = cx - SIGN_W / 2, cy - SIGN_H / 2, cx + SIGN_W / 2, cy + SIGN_H / 2
    # brackets
    for bx in (x0 + 40, x1 - 40):
        cv.line([(bx, y0 - 30), (bx, y0)], NEAR1, 3, caps=False)
    if lit > 0.01:
        def halo(d, tf, k):
            a0 = tf(x0 - 26, y0 - 26); a1 = tf(x1 + 26, y1 + 26)
            d.rounded_rectangle((a0[0], a0[1], a1[0], a1[1]), radius=30 * k, fill=WIN + (int(150 * lit),))
        cv.soft((x0 - 30, y0 - 30, x1 + 30, y1 + 30), halo, blur=14, opacity=1.0, scale=0.35)
    board = lerpc(NEAR2, WIN, lit)
    cv.rect(x0, y0, x1, y1, board, r=8)
    cv.rect(x0 + 6, y0 + 6, x1 - 6, y1 - 6, lerpc(NEAR1, hx("EDAA66"), lit), r=5)
    ink = lerpc(hx("4A5C60"), BANK, lit)
    if text:
        ix = x0 + 42
        if icon == "teapot": _teapot(cv, ix, cy + 2, 0.95, ink)
        elif icon == "qozon": _qozon(cv, ix, cy + 6, 0.9, ink)
        _sign_text(cv, text, cx + 30, cy + 1, 35, ink, 1.0)
    if q > 0.01:
        def qglow(d, tf, k):
            a = tf(cx, cy)
            r = 46 * k
            d.ellipse((a[0] - r, a[1] - r, a[0] + r, a[1] + r), fill=ACCENT + (int(170 * q),))
        cv.soft((cx - 50, cy - 50, cx + 50, cy + 50), qglow, blur=12, scale=0.35)
        _sign_text(cv, "?", cx, cy + 2, 66, ACCENT, q, FONT_BLACK)

def house(cv, x0, x1, top, col=HOUSE, beams=True, door=None, wins=(), lit=0.0):
    cv.rect(x0, top, x1, GROUND + 2, col)
    cv.rect(x0 - 6, top - 10, x1 + 6, top + 4, col)
    if beams:
        for bx in range(int(x0) + 14, int(x1) - 6, 30):
            cv.rect(bx, top + 4, bx + 10, top + 12, GATE)
            cv.rect(bx - 2, top + 2, bx + 12, top + 5, GATE)
    for (wx, wy, ww, wh) in wins:
        cv.rect(wx, wy, wx + ww, wy + wh, lerpc(GATE, WIN, lit), r=2)
        cv.line([(wx + ww / 2, wy), (wx + ww / 2, wy + wh)], col, 2.2, caps=False)
    if door:
        dx, dw, dh = door
        cv.rect(dx - 6, GROUND - dh - 6, dx + dw + 6, GROUND, NEAR2)
        cv.rect(dx, GROUND - dh, dx + dw, GROUND, GATE)
        cv.line([(dx + dw / 2, GROUND - dh), (dx + dw / 2, GROUND)], hx("3A4A4E"), 2.2, caps=False)
        for j in range(3):
            yy = GROUND - dh * (0.25 + 0.25 * j)
            for xx in (dx + dw * 0.25, dx + dw * 0.75):
                cv.poly([(xx, yy - 6), (xx + 5, yy), (xx, yy + 6), (xx - 5, yy)], hx("3A4A4E"))

def draw_mahalla(cv, st):
    cv.set_cam(*st["cam"])
    t = st.get("t", 0.0)
    cv.layer(1.0)
    sky(cv)
    cv.layer(0.12)
    draw_sun(cv, 820, 720, 230)
    cv.layer(0.15)
    birds(cv, t, 33.0, items=[(300, 520, 0.9, 0.2), (380, 470, 0.65, 1.4), (980, 560, 0.7, 2.6)])
    cv.layer(0.25)
    pts = [(-900, 990), (-600, 940), (-300, 905), (0, 950), (250, 890), (520, 935), (760, 880), (1050, 940), (1350, 900), (1700, 950), (2200, 930)]
    cv.poly(pts + [(2200, 1700), (-900, 1700)], MTN1)
    pts2 = [(-900, 1040), (-500, 1000), (-150, 1020), (150, 985), (450, 1025), (760, 990), (1100, 1030), (1400, 995), (1800, 1030), (2200, 1010)]
    cv.poly(pts2 + [(2200, 1700), (-900, 1700)], MTN2)
    cv.layer(0.45)
    c = CITY
    cv.rect(-900, 1150, 2400, 1700, c)
    cv.rect(160, 960, 196, 1160, c); cv.rect(152, 930, 204, 968, c); cv.poly(ellipse_pts(178, 932, 22, 18, 14, 180, 360), c)
    cv.rect(560, 1060, 720, 1160, c); cv.poly(ellipse_pts(640, 1062, 70, 60, 24, 180, 360), c); cv.rect(637, 990, 643, 1004, c)
    cv.rect(980, 1020, 1100, 1160, c); cv.poly(ellipse_pts(990, 1020, 12, 14, 10, 180, 360), c)
    cv.rect(1300, 1090, 1420, 1160, c); cv.poly(ellipse_pts(1360, 1092, 52, 40, 20, 180, 360), c)
    cv.layer(0.7)
    for (x0, x1, top) in ((-500, -120, 1150), (-120, 200, 1190), (380, 720, 1165), (860, 1160, 1180), (1360, 1700, 1160), (1700, 2000, 1200)):
        house(cv, x0, x1, top, col=hx("62767A"), wins=[(x0 + 40, top + 50, 26, 38), (x1 - 70, top + 50, 26, 38)], lit=0.6)
    cv.layer(1.0)
    cv.rect(-900, GROUND, 2600, WATER_M + 1, BANK)
    cv.rect(-900, GROUND, 2600, GROUND + 3, NEAR2)
    for x in range(-900, 2600, 120):
        cv.line([(x, GROUND + 6), (x, WATER_M)], hx("253034"), 1.6, caps=False)
    # near buildings: choyxona (A), oshxona (B), the third (C)
    house(cv, 150, 510, 1175, door=(300, 70, 160), wins=[(180, 1340, 56, 84), (424, 1340, 56, 84)], lit=st.get("litA", 0.0))
    house(cv, 620, 960, 1185, door=(758, 70, 160), wins=[(650, 1340, 56, 84), (876, 1340, 56, 84)], lit=st.get("litB", 0.0))
    house(cv, 1080, 1420, 1180, door=(1215, 70, 160), wins=[(1110, 1340, 56, 84), (1336, 1340, 56, 84)], lit=0.0)
    sign(cv, "A", st.get("signA", 0.0), "CHOYXONA", "teapot", t=t)
    sign(cv, "B", st.get("signB", 0.0), "OSHXONA", "qozon", t=t)
    sign(cv, "C", 0.0, None, None, q=st.get("q", 0.0), t=t)
    # ishkom in front on the left
    n1 = NEAR1
    for px in (-170, 40):
        cv.rect(px, 1150, px + 12, GROUND + 18, n1)
    cv.rect(-260, 1146, 90, 1158, n1)
    rnd = random.Random(14)
    for k in range(24):
        cv.circle(-250 + k * 14.5, 1144 + rnd.uniform(-3, 4), 11 + rnd.random() * 6, n1)
    for gx in (-110, -30):
        for j in range(10):
            row = int((math.sqrt(8 * j + 1) - 1) / 2)
            cv.circle(gx + (j - row * (row + 1) / 2 - row / 2) * 7.5, 1178 + row * 7.5, 4.2, n1)
    if st.get("hero_fn"): st["hero_fn"](cv)
    cv.layer(1.0)
