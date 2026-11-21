# Background sets (vector). All coordinates in 1080x1920 frame space unless noted.
import math, random
from gfx import *
import props as P

FLOOR_Y = 1270


def ikat_motif(ctx, x, y, s, col, alpha):
    """soft ikat flame/lozenge motif"""
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    for k, (w, h, a) in enumerate(((46, 120, 0.55), (30, 84, 0.8), (14, 40, 1.0))):
        ctx.move_to(0, -h)
        ctx.curve_to(w, -h * 0.35, w, h * 0.35, 0, h)
        ctx.curve_to(-w, h * 0.35, -w, -h * 0.35, 0, -h)
        ctx.close_path()
        fill(ctx, col if k != 1 else DTEAL, alpha * a)
    for dy in (-150, 150):
        poly(ctx, [(0, dy - 16), (10, dy), (0, dy + 16), (-10, dy)])
        fill(ctx, col, alpha)
    ctx.restore()


def barbershop(ctx, t, pole_phase, pole=True, mirror=True, lamps_on=1.0):
    # upper wall
    vgrad(ctx, -400, -400, 1880, 1420, [(0, TEAL), (1, DTEAL)])
    for r in range(4):
        for c in range(-1, 6):
            ikat_motif(ctx, c * 230 + (115 if r % 2 else 0), 160 + r * 270, 0.9, GOLD, 0.16)
    # wainscot
    ctx.rectangle(-400, 1010, 1880, FLOOR_Y - 1010)
    fill(ctx, hx("7A4A2A"))
    for x in range(-400, 1500, 150):
        rrect(ctx, x + 14, 1034, 122, FLOOR_Y - 1060, 10)
        fs(ctx, hx("6A3E22"), 3)
    ctx.rectangle(-400, 1000, 1880, 16)
    fs(ctx, GOLD, 4)
    # floor (wood planks, slight perspective)
    vgrad(ctx, -400, FLOOR_Y, 1880, 1000, [(0, hx("B9824E")), (1, hx("9C673A"))])
    vx, vy = 540, 640
    for k in range(-14, 16):
        xb = 540 + k * 120
        x0 = vx + (xb - vx) * (FLOOR_Y - vy) / (2100 - vy)
        line(ctx, [(x0, FLOOR_Y), (xb, 2100)], color=hx("8A5A32"), width=3, alpha=0.8)
    line(ctx, [(-400, FLOOR_Y), (1480, FLOOR_Y)], width=6)
    # warm light pools
    glow(ctx, 250, 260, 620, hx("FFC874"), 0.20 * lamps_on)
    glow(ctx, 830, 260, 620, hx("FFC874"), 0.20 * lamps_on)
    if mirror:
        mirror_frame(ctx, 330, 430, 560, 700)
    # counter
    cel(ctx, lambda c: rrect(c, 180, 1110, 760, 46, 10), hx("EFE6D6"), hx("D8CCB6"), d=(30, 0))
    ctx.rectangle(200, 1156, 720, 110)
    fs(ctx, hx("5E3720"), 6)
    for x, h_, col in ((300, 90, TEAL), (840, 100, hx("D7263D")), (885, 70, hx("2E7D4F")), (925, 110, GOLD)):
        P.bottle(ctx, x, 1110, h_, col)
    # right shelf
    ctx.rectangle(930, 700, 260, 20)
    fs(ctx, hx("6A3E22"), 5)
    for x, h_, col in ((970, 80, hx("F7F3EA")), (1015, 110, TEAL), (1060, 70, GOLD)):
        P.bottle(ctx, x, 700, h_, col)
    # lamps
    for lx in (250, 830):
        P.lamp(ctx, lx, -400, 170, t, lamps_on)
    if pole:
        shop_pole(ctx, pole_phase)


SHOP_POLE = dict(cx=222, y0=640, y1=1150, R=40)


def shop_pole(ctx, phase, **kw):
    p = SHOP_POLE
    # wall bracket
    for yy in (700, 1090):
        rrect(ctx, p["cx"] - 72, yy - 8, 50, 16, 6)
        fs(ctx, BRASS, 4)
    P.pole(ctx, p["cx"], p["y0"], p["y1"], p["R"], phase, **kw)


def mirror_frame(ctx, x, y, w, h, inner=None):
    """arched gold mirror; inner(ctx) draws reflection content clipped to the glass"""
    def arch(c, x0, y0, ww, hh):
        r = ww / 2
        c.move_to(x0, y0 + r)
        c.arc(x0 + r, y0 + r, r, PI, 2 * PI)
        c.line_to(x0 + ww, y0 + hh)
        c.line_to(x0, y0 + hh)
        c.close_path()
    cel(ctx, lambda c: arch(c, x - 26, y - 26, w + 52, h + 52), GOLD, mul(GOLD, 0.78), d=(18, 0))
    arch(ctx, x - 10, y - 10, w + 20, h + 20)
    stroke_ol(ctx, 3, alpha=0.6)
    ctx.save()
    arch(ctx, x, y, w, h)
    ctx.clip()
    vgrad(ctx, x, y, w, h, [(0, hx("CFE3DF")), (1, hx("94BBB6"))])
    if inner is not None:
        inner(ctx)
    for k, (ox, ww) in enumerate(((0.15, 60), (0.32, 24), (0.7, 40))):
        xx = x + w * ox
        poly(ctx, [(xx, y + h), (xx + ww, y + h), (xx + ww + 300, y), (xx + 300, y)])
        fill(ctx, WHITE, 0.16 if inner is None else 0.10)
    ctx.restore()
    arch(ctx, x, y, w, h)
    stroke_ol(ctx, 6)


# ---------------------------------------------------------------- medieval
def timber_house(ctx, x, y_ground, w, h, roof_h, plaster, seed=0, door=None, windows=True):
    rnd = random.Random(seed)
    beam = hx("4A3020")
    ctx.rectangle(x, y_ground - h, w, h)
    fs(ctx, plaster, 6)
    # beams
    for k in range(0, 4):
        yy = y_ground - h + k * h / 3
        ctx.rectangle(x, yy - 9, w, 18)
        fs(ctx, beam, 4)
    for k in range(0, 5):
        xx = x + k * w / 4
        ctx.rectangle(xx - 9, y_ground - h, 18, h)
        fs(ctx, beam, 4)
    for k in range(4):
        xa = x + k * w / 4
        yt = y_ground - h + (k % 3) * h / 3
        if rnd.random() < 0.6:
            line(ctx, [(xa + 10, yt + h / 3 - 10), (xa + w / 4 - 10, yt + 10)], color=beam, width=12)
    if windows:
        for k in range(2):
            wx = x + w * (0.22 + 0.5 * k)
            wy = y_ground - h + h / 3 * 0.35
            rrect(ctx, wx - 34, wy, 68, 74, 8)
            fs(ctx, hx("3E5560"), 5)
            line(ctx, [(wx, wy), (wx, wy + 74)], width=4)
            line(ctx, [(wx - 34, wy + 37), (wx + 34, wy + 37)], width=4)
    # roof
    poly(ctx, [(x - 40, y_ground - h + 4), (x + w / 2, y_ground - h - roof_h), (x + w + 40, y_ground - h + 4)])
    fs(ctx, hx("8A4A2E"), 6)
    for k in range(1, 5):
        yy = y_ground - h - roof_h * k / 5
        f = k / 5
        line(ctx, [(x - 40 + (w / 2 + 40) * f, yy + 4), (x + w + 40 - (w / 2 + 40) * f, yy + 4)], color=hx("6E3820"), width=4)


def cobbles(ctx, x0, x1, y0, y1, seed=1):
    vgrad(ctx, x0, y0, x1 - x0, y1 - y0, [(0, hx("A08F78")), (1, hx("8A7A64"))])
    rnd = random.Random(seed)
    y = y0 + 10
    row = 0
    while y < y1:
        hh = 26 + row * 5
        x = x0 - rnd.random() * 60
        while x < x1:
            ww = hh * (1.6 + rnd.random() * 0.8)
            rrect(ctx, x + 4, y + 3, ww - 8, hh - 6, hh * 0.4)
            fs(ctx, hx("B3A38A"), 3)
            x += ww
        y += hh
        row += 1


def street(ctx, t):
    """wide medieval street, world x from 0 to 1560"""
    vgrad(ctx, -200, -400, 2000, 1500, [(0, hx("F3E6C8")), (1, hx("E8D5AE"))])
    for cx, cy in ((300, 260), (980, 200), (1400, 300)):
        ellipse(ctx, cx + 20 * math.sin(t * 0.3 + cx), cy, 110, 34)
        fill(ctx, WHITE, 0.6)
    G = 1380
    timber_house(ctx, -60, G, 420, 760, 300, hx("EADCC0"), 1)
    timber_house(ctx, 420, G, 400, 820, 260, hx("E2D2B2"), 2)
    timber_house(ctx, 880, G, 520, 780, 320, hx("EEE0C4"), 3, windows=True)
    timber_house(ctx, 1460, G, 380, 720, 280, hx("E2D2B2"), 4)
    cobbles(ctx, -200, 2000, G, 2100)
    line(ctx, [(-200, G), (2000, G)], width=6)


SHOP_DOOR = dict(x=1060, y=940, w=170, h=440)


def street_door(ctx, open_=0.0):
    d = SHOP_DOOR
    x, y, w, h = d["x"], d["y"], d["w"], d["h"]
    # dark doorway
    rrect(ctx, x - 12, y - 12, w + 24, h + 12, 20)
    fs(ctx, hx("4A3020"), 6)
    ctx.rectangle(x, y, w, h)
    fill(ctx, hx("2A1A10"))
    # door leaf swinging inward-left (visible width shrinks)
    vis = w * (1 - 0.82 * open_)
    ctx.rectangle(x, y, vis, h)
    fs(ctx, WOOD, 6)
    for k in range(1, 4):
        line(ctx, [(x + vis * k / 4, y + 8), (x + vis * k / 4, y + h - 8)], color=WOOD_D, width=4)
    for yy in (y + 80, y + h - 90):
        ctx.rectangle(x, yy, vis, 16)
        fs(ctx, hx("3A3A3A"), 3)
    circle(ctx, x + vis - 26, y + h / 2, 10)
    fs(ctx, BRASS, 4)


def med_interior(ctx, t, window=True):
    vgrad(ctx, -300, -400, 1700, 1800, [(0, hx("E9DCC0")), (1, hx("D9C7A2"))])
    beam = hx("4A3020")
    for xx in (60, 540, 1020):
        ctx.rectangle(xx - 22, -400, 44, 1800)
        fs(ctx, beam, 5)
    ctx.rectangle(-300, 380, 1700, 40)
    fs(ctx, beam, 5)
    line(ctx, [(82, 420), (500, 1000)], color=beam, width=26)
    line(ctx, [(998, 420), (580, 1000)], color=beam, width=26)
    if window:
        rrect(ctx, 700, 520, 220, 260, 110)
        fs(ctx, hx("F7EEDC"), 6)
        line(ctx, [(810, 520), (810, 780)], width=6)
        line(ctx, [(700, 650), (920, 650)], width=6)
    # shelf with jars
    ctx.rectangle(110, 640, 330, 22)
    fs(ctx, WOOD_D, 5)
    for x, h_ in ((150, 70), (215, 96), (290, 60), (360, 84)):
        rrect(ctx, x - 26, 640 - h_, 52, h_, 14)
        fs(ctx, hx("B07A4A") if x % 2 else hx("8AA08A"), 5)
        rrect(ctx, x - 18, 640 - h_ - 14, 36, 16, 5)
        fs(ctx, WOOD_D, 4)
    # herbs hanging
    for k, x in enumerate((180, 260, 340)):
        line(ctx, [(x, 420), (x, 470 + 6 * math.sin(t * 2 + k))], width=4)
        ellipse(ctx, x + 3 * math.sin(t * 2 + k), 500, 20, 34)
        fs(ctx, hx("7A8A4A"), 4)
    # floor
    ctx.rectangle(-300, 1300, 1700, 900)
    fs(ctx, hx("8A6A48"), 6)
    for k in range(-3, 12):
        line(ctx, [(k * 120, 1300), (k * 150 - 200, 2100)], color=hx("6E5236"), width=4)


def stone_facade(ctx, t, door_angle=0.0, door_x=560, door_y=760, door_w=300, door_h=640, inside=None):
    """stone wall with a heavy arched door. door_angle: 0 = open (thin), 1 = shut"""
    vgrad(ctx, -300, -400, 1700, 1800, [(0, hx("CDBFA6")), (1, hx("B8A88C"))])
    rnd = random.Random(5)
    for r in range(26):
        y = -120 + r * 70
        off = (r % 2) * 70
        for c in range(-2, 10):
            x = c * 140 + off - 100
            rrect(ctx, x + 5, y + 5, 130, 60, 12)
            fs(ctx, mix(hx("D6C8AE"), hx("BFAE90"), rnd.random()), 3)
    # step
    rrect(ctx, door_x - door_w / 2 - 80, door_y + door_h - 10, door_w + 160, 60, 10)
    fs(ctx, hx("A8977A"), 6)
    ctx.rectangle(-300, door_y + door_h + 50, 1700, 900)
    fs(ctx, hx("9C8C70"), 6)

    def arch(c, x0, y0, w, h):
        r = w / 2
        c.move_to(x0, y0 + h)
        c.line_to(x0, y0 + r)
        c.arc(x0 + r, y0 + r, r, PI, 2 * PI)
        c.line_to(x0 + w, y0 + h)
        c.close_path()
    x0 = door_x - door_w / 2
    arch(ctx, x0 - 40, door_y - 40, door_w + 80, door_h + 40)
    fs(ctx, hx("A39274"), 6)
    arch(ctx, x0, door_y, door_w, door_h)
    fs(ctx, hx("24170E"), 6)
    if inside is not None:
        ctx.save()
        arch(ctx, x0, door_y, door_w, door_h)
        ctx.clip()
        inside(ctx)
        ctx.restore()
    return lambda: heavy_door(ctx, x0, door_y, door_w, door_h, door_angle, arch)


def heavy_door(ctx, x0, y0, w, h, ang, arch):
    """door hinged on the right edge; ang 0 = open (edge-on), 1 = shut"""
    vis = w * max(0.06, ang)
    ctx.save()
    arch(ctx, x0, y0, w, h)
    ctx.clip()
    xL = x0 + w - vis
    ctx.rectangle(xL, y0 - 10, vis, h + 20)
    fill(ctx, WOOD)
    for k in range(1, 5):
        xx = xL + vis * k / 5
        line(ctx, [(xx, y0), (xx, y0 + h)], color=WOOD_D, width=5)
    for yy in (y0 + 160, y0 + h - 140):
        ctx.rectangle(xL, yy, vis, 22)
        fs(ctx, hx("3A3A3A"), 3)
    if ang > 0.5:
        circle(ctx, xL + 40 * ang, y0 + h * 0.55, 18)
        ctx.set_source_rgba(*OL, 1)
        ctx.set_line_width(olw(ctx, 12))
        ctx.stroke_preserve()
        ctx.set_source_rgba(*BRASS, 1)
        ctx.set_line_width(olw(ctx, 6))
        ctx.stroke()
    ctx.restore()
    ctx.rectangle(xL, y0, vis, h)
    ctx.new_path()
    arch(ctx, x0, y0, w, h)
    stroke_ol(ctx, 6)


# ---------------------------------------------------------------- modern entrance (scene 8/9)
def entrance(ctx, t, pole_phase, pole_kw=None):
    vgrad(ctx, -400, -400, 1880, 1800, [(0, hx("2A7F7D")), (1, TEAL)])
    for r in range(5):
        for c in range(-1, 6):
            ikat_motif(ctx, c * 230 + (115 if r % 2 else 0), 120 + r * 280, 0.8, GOLD, 0.12)
    # glass door (left)
    rrect(ctx, 90, 560, 380, 860, 16)
    fs(ctx, hx("5E3720"), 6)
    rrect(ctx, 120, 590, 320, 800, 8)
    vgrad(ctx, 120, 590, 320, 800, [(0, hx("CFE6E4")), (1, hx("8DB6B3"))])
    rrect(ctx, 120, 590, 320, 800, 8)
    stroke_ol(ctx, 5)
    for k, (ox, ww) in enumerate(((0.1, 40), (0.3, 16))):
        xx = 120 + 320 * ox
        poly(ctx, [(xx, 1390), (xx + ww, 1390), (xx + ww + 200, 590), (xx + 200, 590)])
        fill(ctx, WHITE, 0.18)
    ctx.save()
    ctx.translate(280, 820)
    ctx.rotate(0.6)
    P.scissors(ctx, s=1.1, open_=0.4)
    ctx.restore()
    rrect(ctx, 400, 960, 18, 120, 8)
    fs(ctx, BRASS, 4)
    # awning
    for k in range(9):
        poly(ctx, [(60 + k * 110, 470), (170 + k * 110, 470), (160 + k * 110, 540), (70 + k * 110, 540)])
        fs(ctx, POLE_R if k % 2 == 0 else WHITE, 5)
    # sidewalk
    ctx.rectangle(-400, 1420, 1880, 700)
    fs(ctx, hx("B7AA98"), 6)
    for k in range(-4, 14):
        line(ctx, [(k * 160, 1420), (k * 190 - 120, 2100)], color=hx("9C8F7E"), width=4)
    # plant pot
    ctx.move_to(930, 1420)
    ctx.line_to(910, 1300)
    ctx.line_to(1050, 1300)
    ctx.line_to(1030, 1420)
    ctx.close_path()
    fs(ctx, hx("B5653A"), 6)
    for k in range(6):
        a = -PI / 2 + (k - 2.5) * 0.35 + 0.05 * math.sin(t * 1.5 + k)
        ellipse(ctx, 980 + 90 * math.cos(a), 1300 + 90 * math.sin(a), 22, 56, rot=a + PI / 2)
        fs(ctx, CHAPAN, 5)
    # pole on the wall right of the door
    for yy in (760, 1180):
        rrect(ctx, 600, yy - 9, 70, 18, 6)
        fs(ctx, BRASS, 4)
    kw = dict(pole_kw or {})
    if not kw.pop("skip", False):
        P.pole(ctx, 700, 720, 1220, 52, pole_phase, **kw)


def teal_ikat(ctx, t):
    vgrad(ctx, -300, -300, 1680, 2520, [(0, hx("1A6463")), (0.5, TEAL), (1, DTEAL)])
    for r in range(7):
        for c in range(-1, 6):
            x = c * 220 + (110 if r % 2 else 0)
            y = r * 320 - 40 + 12 * math.sin(t * 0.8 + c + r)
            ikat_motif(ctx, x, y, 1.0, GOLD, 0.22)
