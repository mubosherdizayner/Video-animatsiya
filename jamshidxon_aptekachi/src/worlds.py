# Static backgrounds (drawn once, supersampled) for pharmacy, blogger set and window/street.
import random, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
from lib import *

# ---------------------------------------------------------------- street (used in door + window)
def street_img(w, h, seed=1):
    c = SS(w, h, 2, bg=(150, 210, 250, 255))
    # sky gradient
    for i in range(0, int(h * 0.62), 6):
        t = i / (h * 0.62)
        col = (int(lerp(130, 205, t)), int(lerp(200, 236, t)), int(lerp(250, 255, t)), 255)
        c.rect((0, i, w, i + 7), fill=col, outline=None, width=0)
    c.circle(w * 0.82, h * 0.12, h * 0.07, fill=(255, 236, 140), outline=None, width=0)
    c.circle(w * 0.82, h * 0.12, h * 0.05, fill=(255, 220, 90), outline=OL, width=4)
    # clouds
    for cx, cy, s in ((w * 0.2, h * 0.1, 1.0), (w * 0.55, h * 0.18, 0.75)):
        for dx, dy, r in ((-40, 0, 34), (0, -14, 44), (44, 0, 32)):
            c.circle(cx + dx * s, cy + dy * s, r * s, fill=(255, 255, 255), outline=None, width=0)
    # adobe walls
    gy = h * 0.8
    c.rect((-10, h * 0.42, w * 0.55, gy), fill=(233, 211, 174), outline=OL, width=6)
    c.rect((w * 0.5, h * 0.36, w + 10, gy), fill=(225, 200, 160), outline=OL, width=6)
    rnd = random.Random(seed)
    for k in range(18):
        x = rnd.uniform(0, w); y = rnd.uniform(h * 0.45, gy - 20)
        c.rect((x, y, x + rnd.uniform(26, 60), y + 14), fill=(214, 186, 140), outline=None, width=0, r=6)
    # wooden gate + small window
    c.rect((w * 0.64, h * 0.5, w * 0.8, gy), fill=(150, 92, 52), outline=OL, width=6, r=10)
    c.line([(w * 0.72, h * 0.5), (w * 0.72, gy)], fill=OL, width=4)
    c.circle(w * 0.705, h * 0.66, 6, fill=GOLD, outline=OL, width=2)
    c.circle(w * 0.735, h * 0.66, 6, fill=GOLD, outline=OL, width=2)
    c.rect((w * 0.12, h * 0.52, w * 0.27, h * 0.64), fill=(110, 170, 210), outline=OL, width=6, r=6)
    c.line([(w * 0.195, h * 0.52), (w * 0.195, h * 0.64)], fill=OL, width=4)
    # tree
    tx = w * 0.42
    c.rect((tx - 18, h * 0.38, tx + 18, gy), fill=(140, 90, 50), outline=OL, width=6)
    for dx, dy, r in ((0, 0.25, 0.15), (-0.09, 0.31, 0.11), (0.09, 0.31, 0.11), (0, 0.17, 0.11)):
        c.circle(tx + dx * w, dy * h, r * w, fill=(76, 170, 80), outline=OL, width=6)
    for dx, dy, r in ((0, 0.25, 0.15), (-0.09, 0.31, 0.11), (0.09, 0.31, 0.11), (0, 0.17, 0.11)):
        c.circle(tx + dx * w - r * w * 0.15, dy * h - r * w * 0.15, r * w * 0.75, fill=(96, 190, 96), outline=None, width=0)
    # ground / path
    c.rect((-10, gy, w + 10, h + 10), fill=(232, 214, 178), outline=OL, width=6)
    c.rect((-10, gy + 8, w + 10, gy + 22), fill=(212, 190, 150), outline=None, width=0)
    for k in range(10):
        x = rnd.uniform(0, w)
        c.poly([(x, gy + 4), (x + 8, gy - 22), (x + 16, gy + 4)], fill=(110, 180, 90), outline=None, width=0)
    return c.result().convert("RGB")

# ---------------------------------------------------------------- pharmacy
PH_OX, PH_OY, PH_W, PH_H = -340, -120, 2320, 2160
SHELF_X0, SHELF_X1 = -330, 1310
BOARDS = [860, 1090]
COUNTER_W, COUNTER_H = 1540, 500
COUNTER_X = -340

def make_slots(seed=7):
    rnd = random.Random(seed)
    slots = []
    for bi, by in enumerate(BOARDS):
        x = SHELF_X0 + 34
        k = 0
        while x < SHELF_X1 - 120:
            w = rnd.choice([92, 104, 116, 128])
            h = rnd.choice([118, 132, 146]) if bi == 0 else rnd.choice([120, 136, 150])
            kind = "bottle" if rnd.random() < 0.18 else "box"
            if kind == "bottle": w, h = 64, rnd.choice([110, 126])
            col = BOX_COLORS[(k * 3 + bi * 5 + rnd.randint(0, 7)) % len(BOX_COLORS)]
            slots.append(dict(x=x, y=by, w=w, h=h, kind=kind, col=col, style=rnd.randint(0, 5), board=bi, idx=len(slots)))
            x += w + (w * 0.18 if kind == "box" else 0) + rnd.choice([16, 22, 30])
            k += 1
    fr = ["apple", "grapes", "apricot", "pomeg"]
    for s in slots: s["fruit"] = fr[(s["idx"] * 7 + s["board"]) % 4]
    return slots
SLOTS = make_slots()

_ITEM_CACHE = {}
def slot_item(s, fruit=False):
    key = (s["idx"], fruit)
    if key not in _ITEM_CACHE:
        if fruit:
            im = fruit_imgs()[s["fruit"]]
            sz = min(s["w"] * 1.25, s["h"] * 1.05) * 1.05
            sc = sz / im.width
            _ITEM_CACHE[key] = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
        elif s["kind"] == "bottle":
            _ITEM_CACHE[key] = bottle(s["w"], s["h"], s["col"])
        else:
            _ITEM_CACHE[key] = med_box(s["w"], s["h"], s["col"], s["style"])
    return _ITEM_CACHE[key]

def slot_pos(s, fruit=False):
    """top-left (world) where the item image goes"""
    im = slot_item(s, fruit)
    if fruit:
        cx = s["x"] + s["w"] / 2
        return cx - im.width / 2, s["y"] - im.height * 0.86, im
    return s["x"] - 6, s["y"] - im.height + 6, im

def pharmacy_back(items="boxes"):
    """items: boxes | fruits | none"""
    w, h = PH_W, PH_H
    ox, oy = PH_OX, PH_OY
    c = SS(w, h, 2, bg=MINT + (255,))
    X = lambda x: x - ox; Y = lambda y: y - oy
    # wall stripes
    for x in range(-340, 2000, 150):
        c.rect((X(x), Y(100), X(x + 70), Y(1720)), fill=(216, 244, 234), outline=None, width=0)
    # ceiling band
    c.rect((0, 0, w, Y(110)), fill=PH_WHITE, outline=None, width=0)
    c.rect((0, Y(96), w, Y(124)), fill=GREEN, outline=OL, width=5)
    # wainscot
    c.rect((0, Y(1460), w, Y(1720)), fill=PH_WHITE, outline=OL, width=5)
    c.rect((0, Y(1460), w, Y(1480)), fill=MINT_D, outline=OL, width=4)
    # floor tiles
    c.rect((0, Y(1720), w, h), fill=(236, 247, 242), outline=OL, width=6)
    for x in range(-340, 2000, 160):
        c.line([(X(x), Y(1720)), (X(x - 60), h)], fill=(208, 232, 222), width=4)
    for y in (1800, 1900, 2010):
        c.line([(0, Y(y)), (w, Y(y))], fill=(208, 232, 222), width=4)
    # shelving back panel + uprights + boards
    c.rect((X(SHELF_X0 - 20), Y(690), X(SHELF_X1 + 20), Y(1320)), fill=(190, 230, 214), outline=OL, width=6)
    c.rect((X(SHELF_X0 - 34), Y(672), X(SHELF_X1 + 34), Y(700)), fill=(250, 246, 238), outline=OL, width=6, r=4)
    for by in BOARDS + [1300]:
        c.rect((X(SHELF_X0 - 20), Y(by), X(SHELF_X1 + 20), Y(by + 26)), fill=(250, 246, 238), outline=OL, width=6, r=3)
        c.rect((X(SHELF_X0 - 14), Y(by + 26), X(SHELF_X1 + 14), Y(by + 40)), fill=(160, 205, 190), outline=None, width=0)
    for ux in (SHELF_X0 - 20, 490, SHELF_X1 - 6):
        c.rect((X(ux), Y(690), X(ux + 26), Y(1320)), fill=(250, 246, 238), outline=OL, width=6)
    # door frame (x 1390..1850, y 740..1720) with street outside
    dx0, dy0, dx1, dy1 = 1390, 740, 1850, 1720
    st = street_img(dx1 - dx0, dy1 - dy0, seed=4)
    c.paste(st.convert("RGBA"), X(dx0), Y(dy0))
    c.rect((X(dx0 - 30), Y(dy0 - 30), X(dx1 + 30), Y(dy1)), fill=None, outline=OL, width=6)
    c.rect((X(dx0 - 26), Y(dy0 - 26), X(dx1 + 26), Y(dy0)), fill=PH_WHITE, outline=OL, width=5)
    c.rect((X(dx0 - 26), Y(dy0), X(dx0), Y(dy1)), fill=PH_WHITE, outline=OL, width=5)
    c.rect((X(dx1), Y(dy0), X(dx1 + 26), Y(dy1)), fill=PH_WHITE, outline=OL, width=5)
    # bell bracket
    c.line([(X(dx1 - 20), Y(dy0 - 14)), (X(dx1 - 20), Y(dy0 + 22)), (X(dx1 - 60), Y(dy0 + 22))], fill=OL, width=7)
    # small poster near door
    c.rect((X(1450), Y(360), X(1780), Y(620)), fill=(255, 255, 255), outline=OL, width=6, r=14)
    c.circle(X(1540), Y(490), 58, fill=APPLE, outline=OL, width=5)
    c.rect((X(1516), Y(470), X(1564), Y(510)), fill=(255, 255, 255), outline=None, width=0)
    c.rect((X(1530), Y(456), X(1550), Y(524)), fill=(255, 255, 255), outline=None, width=0)
    for k in range(3):
        c.line([(X(1620), Y(440 + k * 40)), (X(1740 - 30 * (k == 2)), Y(440 + k * 40))], fill=(180, 190, 200), width=14)
    # wall clock (left)
    c.circle(X(-120), Y(470), 86, fill=(255, 255, 255), outline=OL, width=7)
    c.line([(X(-120), Y(470)), (X(-120), Y(410))], fill=OL, width=7)
    c.line([(X(-120), Y(470)), (X(-80), Y(490))], fill=OL, width=7)
    im = c.result()
    if items != "none":
        for s in SLOTS:
            x, y, it = slot_pos(s, fruit=(items == "fruits"))
            im.alpha_composite(it, (int(x - ox), int(y - oy)))
    return im.convert("RGB")

def counter_layer():
    w, h = COUNTER_W, COUNTER_H
    c = SS(w + 20, h + 20, 2)
    c.rect((10, 60, w, h), fill=(242, 230, 212), outline=OL, width=7)
    pw = (w - 40) / 5
    for k in range(5):
        x = 30 + k * pw
        c.rect((x + 10, 110, x + pw - 14, h - 70), fill=(232, 213, 186), outline=OL, width=5, r=10)
        c.rect((x + 24, 124, x + pw - 28, 140), fill=(246, 236, 220), outline=None, width=0)
    c.rect((10, h - 50, w, h), fill=(159, 216, 195), outline=OL, width=6)
    c.rect((0, 10, w + 10, 66), fill=(255, 255, 255), outline=OL, width=7, r=10)
    c.rect((14, 52, w - 4, 64), fill=MINT_D, outline=None, width=0)
    return c.result()

def door_panel(open_amt=0.0):
    """glass door panel, hinge on the left; open_amt 0..1 narrows it (perspective swing)"""
    w0, h0 = 460, 980
    w = max(30, int(w0 * (1 - 0.78 * open_amt)))
    c = SS(w, h0, 2)
    c.rect((3, 3, w - 3, h0 - 3), fill=(250, 252, 250), outline=OL, width=6, r=6)
    g = (205, 235, 255, 120)
    c.rect((28 * w / w0 + 6, 40, w - 28 * w / w0 - 6, h0 * 0.62), fill=g, outline=OL, width=5, r=4)
    c.rect((28 * w / w0 + 6, h0 * 0.66, w - 28 * w / w0 - 6, h0 - 60), fill=g, outline=OL, width=5, r=4)
    c.line([(w * 0.25, 90), (w * 0.55, 60)], fill=(255, 255, 255, 200), width=10 * w / w0 + 2)
    c.line([(w * 0.22, 160), (w * 0.62, 110)], fill=(255, 255, 255, 160), width=6 * w / w0 + 1)
    c.rect((w - 60 * w / w0 - 12, h0 * 0.5, w - 40 * w / w0 - 6, h0 * 0.6), fill=(180, 186, 190), outline=OL, width=4, r=4)
    return c.result()

def bell_img():
    c = SS(90, 110, 3)
    c.line([(45, 0), (45, 22)], fill=OL, width=5)
    c.poly([(20, 80), (26, 40), (45, 22), (64, 40), (70, 80)], fill=(242, 190, 50), outline=OL, width=5)
    c.rect((12, 74, 78, 88), fill=(230, 170, 40), outline=OL, width=5, r=6)
    c.circle(45, 96, 10, fill=(200, 140, 30), outline=OL, width=4)
    return c.result()

# ---------------------------------------------------------------- blogger set
BL_OX, BL_OY, BL_W, BL_H = -260, -660, 1600, 3000
def blogger_back():
    w, h = BL_W, BL_H
    ox, oy = BL_OX, BL_OY
    X = lambda x: x - ox; Y = lambda y: y - oy
    base = Image.new("RGB", (w, h), NAVY)
    a = np.zeros((h, w, 3), np.float32) + np.array(NAVY, np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # ring-light glow on wall
    gx, gy = X(200), Y(640)
    d = np.sqrt((xx - gx) ** 2 + (yy - gy) ** 2)
    glow = np.exp(-(d / 620) ** 2) * 0.55 + np.exp(-((d - 300) / 90) ** 2) * 0.25
    a += glow[..., None] * (np.array(RING, np.float32) - a) * 0.9
    base = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    c = SS(w, h, 2)
    # acoustic panels
    for k, x in enumerate(range(380, 1400, 170)):
        c.rect((X(x), Y(260), X(x + 130), Y(1500)), fill=(255, 255, 255, 14), outline=(14, 18, 28, 255), width=4, r=10)
    # shelf with small items, right wall
    c.rect((X(760), Y(560), X(1260), Y(590)), fill=(60, 70, 96), outline=OL, width=5, r=4)
    c.rect((X(790), Y(470), X(860), Y(560)), fill=(255, 214, 10), outline=OL, width=5, r=6)
    c.rect((X(880), Y(440), X(930), Y(560)), fill=(229, 56, 59), outline=OL, width=5, r=6)
    c.circle(X(1010), Y(520), 40, fill=(46, 173, 91), outline=OL, width=5)
    c.rect((X(1080), Y(480), X(1200), Y(560)), fill=(90, 190, 230), outline=OL, width=5, r=8)
    # floor + rug
    c.rect((0, Y(1700), w, h), fill=(22, 26, 38, 255), outline=OL, width=6)
    c.ellipse((X(40), Y(1700), X(1040), Y(1900)), fill=(52, 60, 90), outline=OL, width=6)
    c.ellipse((X(110), Y(1725), X(970), Y(1875)), fill=None, outline=(255, 214, 10), width=5)
    # ring light stand
    rx, ry, R = 200, 640, 300
    c.line([(X(rx), Y(ry + R)), (X(rx), Y(1760))], fill=OL, width=22)
    c.line([(X(rx), Y(ry + R)), (X(rx), Y(1760))], fill=(80, 86, 100), width=12)
    for dx in (-110, 0, 110):
        c.line([(X(rx), Y(1690)), (X(rx + dx), Y(1790))], fill=OL, width=16)
    im = base.convert("RGBA"); im.alpha_composite(c.result())
    # ring glow tube
    g = Image.new("L", (w, h), 0); gd = ImageDraw.Draw(g)
    gd.ellipse((X(rx - R - 30), Y(ry - R - 30), X(rx + R + 30), Y(ry + R + 30)), outline=255, width=90)
    g = g.filter(ImageFilter.GaussianBlur(40))
    glow_l = Image.new("RGBA", (w, h), RING + (0,)); glow_l.putalpha(g.point(lambda v: int(v * 0.85)))
    im.alpha_composite(glow_l)
    c2 = SS(w, h, 2)
    c2.ellipse((X(rx - R), Y(ry - R), X(rx + R), Y(ry + R)), fill=None, outline=OL, width=64)
    c2.ellipse((X(rx - R + 7), Y(ry - R + 7), X(rx + R - 7), Y(ry + R - 7)), fill=None, outline=RING, width=50)
    c2.ellipse((X(rx - R + 18), Y(ry - R + 18), X(rx + R - 18), Y(ry + R - 18)), fill=None, outline=(255, 255, 255), width=18)
    # plant (left)
    px, py = -60, 1800
    for k, (dx, dy, ang) in enumerate(((-80, -260, -30), (0, -330, 0), (80, -260, 30), (-120, -150, -55), (120, -150, 55))):
        c2.ellipse((X(px + dx - 50), Y(py - 170 + dy), X(px + dx + 50), Y(py - 170 + dy + 190)), fill=(70, 170, 90), outline=OL, width=6)
        c2.line([(X(px + dx), Y(py - 160 + dy + 20)), (X(px + dx * 0.6), Y(py - 140 + dy + 170))], fill=(40, 120, 60), width=5)
    c2.poly([(X(px - 110), Y(py - 170)), (X(px + 110), Y(py - 170)), (X(px + 80), Y(py)), (X(px - 80), Y(py))], fill=(214, 110, 70), outline=OL, width=6)
    c2.rect((X(px - 124), Y(py - 196), X(px + 124), Y(py - 160)), fill=(230, 130, 86), outline=OL, width=6, r=6)
    im.alpha_composite(c2.result())
    return im.convert("RGB")

def phone_tripod():
    """foreground phone on tripod; returns (img, world_x_left, world_y_top)"""
    w, h = 420, 1300
    c = SS(w, h, 2)
    cx = 210
    for dx in (-170, 0, 170):
        c.line([(cx, 560), (cx + dx, h - 10)], fill=OL, width=22)
        c.line([(cx, 560), (cx + dx, h - 10)], fill=(70, 76, 90), width=12)
    c.rect((cx - 26, 430, cx + 26, 600), fill=(60, 66, 80), outline=OL, width=6, r=8)
    c.rect((cx - 60, 400, cx + 60, 440), fill=(60, 66, 80), outline=OL, width=6, r=8)
    # phone (back side, portrait)
    c.rect((cx - 112, 10, cx + 112, 420), fill=(42, 46, 58), outline=OL, width=8, r=34)
    c.rect((cx - 92, 32, cx - 12, 130), fill=(28, 30, 40), outline=OL, width=5, r=18)
    for (x, y) in ((cx - 72, 58), (cx - 72, 104), (cx - 34, 80)):
        c.circle(x, y, 15, fill=(70, 80, 110), outline=OL, width=4)
        c.circle(x - 4, y - 4, 4, fill=(200, 210, 255), outline=None, width=0)
    c.circle(cx + 70, 60, 14, fill=(255, 70, 70), outline=OL, width=4)
    c.rect((cx - 112, 10, cx - 98, 420), fill=(255, 255, 255, 30), outline=None, width=0, r=6)
    return c.result(), 1060 - 210, 1060

# ---------------------------------------------------------------- window world (scene 15)
WN_OX, WN_OY, WN_W, WN_H = -160, -120, 2240, 2160
WIN = (150, 560, 1010, 1440)  # glass area x0,y0,x1,y1
def window_wall():
    w, h = WN_W, WN_H
    ox, oy = WN_OX, WN_OY
    X = lambda x: x - ox; Y = lambda y: y - oy
    c = SS(w, h, 2, bg=MINT + (255,))
    for x in range(-160, 2100, 150):
        c.rect((X(x), Y(100), X(x + 70), Y(1720)), fill=(216, 244, 234), outline=None, width=0)
    c.rect((0, 0, w, Y(110)), fill=PH_WHITE, outline=None, width=0)
    c.rect((0, Y(96), w, Y(124)), fill=GREEN, outline=OL, width=5)
    c.rect((0, Y(1460), w, Y(1720)), fill=PH_WHITE, outline=OL, width=5)
    c.rect((0, Y(1720), w, h), fill=(236, 247, 242), outline=OL, width=6)
    # fruit shelf on the right
    x0, x1 = 1150, 2060
    c.rect((X(x0), Y(690), X(x1), Y(1460)), fill=(190, 230, 214), outline=OL, width=6)
    fr = fruit_imgs(); names = ["apple", "grapes", "apricot", "pomeg"]
    for bi, by in enumerate((900, 1160, 1420)):
        c.rect((X(x0 - 14), Y(by), X(x1 + 14), Y(by + 26)), fill=(250, 246, 238), outline=OL, width=6, r=3)
    im = c.result()
    k = 0
    for by in (900, 1160, 1420):
        x = x0 + 40
        while x < x1 - 120:
            f = fr[names[k % 4]]; s = 150 / f.width
            f2 = f.resize((int(f.width * s), int(f.height * s)), Image.LANCZOS)
            im.alpha_composite(f2, (int(X(x)), int(Y(by) - f2.height * 0.86)))
            x += 150; k += 1
    return im.convert("RGB")

def window_frame():
    """RGBA overlay: frame, mullion, glass reflections, sill (world coords at WN origin)"""
    x0, y0, x1, y1 = WIN
    fw = 40
    w, h = x1 - x0 + 2 * fw + 80, y1 - y0 + 2 * fw + 120
    c = SS(w, h, 2)
    ox, oy = x0 - fw - 40, y0 - fw - 20
    X = lambda x: x - ox; Y = lambda y: y - oy
    c.rect((X(x0 - fw), Y(y0 - fw), X(x1 + fw), Y(y0)), fill=PH_WHITE, outline=OL, width=6)
    c.rect((X(x0 - fw), Y(y0), X(x0), Y(y1)), fill=PH_WHITE, outline=OL, width=6)
    c.rect((X(x1), Y(y0), X(x1 + fw), Y(y1)), fill=PH_WHITE, outline=OL, width=6)
    c.rect((X((x0 + x1) / 2 - 14), Y(y0), X((x0 + x1) / 2 + 14), Y(y0 + (y1 - y0) * 0.42)), fill=PH_WHITE, outline=OL, width=5)
    c.rect((X(x0), Y(y0 + (y1 - y0) * 0.42 - 14), X(x1), Y(y0 + (y1 - y0) * 0.42 + 14)), fill=PH_WHITE, outline=OL, width=5)
    # reflections
    c.poly([(X(x0 + 60), Y(y1)), (X(x0 + 300), Y(y0)), (X(x0 + 380), Y(y0)), (X(x0 + 140), Y(y1))], fill=(255, 255, 255, 38), outline=None, width=0)
    c.poly([(X(x0 + 440), Y(y1)), (X(x0 + 640), Y(y0)), (X(x0 + 680), Y(y0)), (X(x0 + 480), Y(y1))], fill=(255, 255, 255, 30), outline=None, width=0)
    # sill
    c.rect((X(x0 - fw - 30), Y(y1), X(x1 + fw + 30), Y(y1 + 60)), fill=(250, 246, 238), outline=OL, width=7, r=6)
    c.rect((X(x0 - fw - 20), Y(y1 + 60), X(x1 + fw + 20), Y(y1 + 76)), fill=(170, 210, 196), outline=None, width=0)
    return c.result(), ox, oy
