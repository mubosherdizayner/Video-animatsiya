# Static backgrounds drawn once (supersampled): restaurant hall, exterior, kitchen, cash desk, blogger set.
import random, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
from lib import *

def wshade(c, f): return tuple(int(max(0, min(255, v * f))) for v in c)

def ikat_band(c, X, Y, x0, x1, y0, y1, base=(155, 29, 32)):
    c.rect((X(x0), Y(y0), X(x1), Y(y1)), fill=base, outline=OL, width=5)
    step = (y1 - y0) * 1.1
    x = x0
    k = 0
    while x < x1:
        cx, cy = x + step / 2, (y0 + y1) / 2
        hh = (y1 - y0) * 0.36
        c.poly([(X(cx - step * 0.42), Y(cy)), (X(cx), Y(cy - hh)), (X(cx + step * 0.42), Y(cy)), (X(cx), Y(cy + hh))],
               fill=(233, 180, 76) if k % 2 == 0 else (46, 120, 96), outline=None, width=0)
        c.poly([(X(cx - step * 0.2), Y(cy)), (X(cx), Y(cy - hh * 0.5)), (X(cx + step * 0.2), Y(cy)), (X(cx), Y(cy + hh * 0.5))],
               fill=(255, 244, 224), outline=None, width=0)
        x += step; k += 1
    c.rect((X(x0), Y(y0), X(x1), Y(y1)), fill=None, outline=OL, width=5)

# ---------------------------------------------------------------- restaurant hall
HL_OX, HL_OY, HL_W, HL_H = -520, -320, 2360, 2560
DOOR = (1240, 520, 1620, 1190)          # glass door (x0, y0, x1, y1)
BELL_XY = (1290, 548)
SPOTS = [(150, 70), (930, 70)]          # ceiling spotlight fixture positions
FLOOR_Y = 1180
def hall_back():
    w, h = HL_W, HL_H
    ox, oy = HL_OX, HL_OY
    X = lambda x: x - ox; Y = lambda y: y - oy
    a = np.zeros((h, w, 3), np.float32) + np.array(R_GOLD, np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # very subtle warm vertical gradient + soft chandelier glow
    a *= (1.04 - 0.1 * (yy / h))[..., None]
    d = np.sqrt((xx - X(540)) ** 2 + ((yy - Y(220)) * 1.2) ** 2)
    a += (np.exp(-(d / 700) ** 2) * 26)[..., None]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    c = SS(w, h, 2)
    # wallpaper: faint vertical stripes + small diamonds
    for x in range(-520, 1840, 120):
        c.rect((X(x), Y(-320), X(x + 46), Y(FLOOR_Y - 230)), fill=(255, 255, 255, 18), outline=None, width=0)
    for x in range(-460, 1840, 240):
        for y in range(-200, 900, 220):
            c.poly([(X(x), Y(y - 18)), (X(x + 14), Y(y)), (X(x), Y(y + 18)), (X(x - 14), Y(y))], fill=(200, 140, 50, 90), outline=None, width=0)
    # ikat border + wainscot
    ikat_band(c, X, Y, -520, 1840, FLOOR_Y - 270, FLOOR_Y - 220)
    c.rect((X(-520), Y(FLOOR_Y - 220), X(1840), Y(FLOOR_Y)), fill=WOOD, outline=OL, width=6)
    for x in range(-500, 1840, 170):
        c.rect((X(x + 18), Y(FLOOR_Y - 196), X(x + 150), Y(FLOOR_Y - 24)), fill=wshade(WOOD, 1.12), outline=wshade(WOOD, 0.7), width=4, r=8)
    # floor (wood planks with perspective)
    c.rect((X(-520), Y(FLOOR_Y), X(1840), Y(2240)), fill=(170, 108, 56), outline=OL, width=6)
    for k, y in enumerate([FLOOR_Y + 40, FLOOR_Y + 100, FLOOR_Y + 180, FLOOR_Y + 290, FLOOR_Y + 430, FLOOR_Y + 610, FLOOR_Y + 840]):
        c.line([(X(-520), Y(y)), (X(1840), Y(y))], fill=(140, 86, 42), width=4)
    for x in range(-1400, 2800, 160):
        c.line([(X(540 + (x - 540) * 0.32), Y(FLOOR_Y)), (X(x), Y(2240))], fill=(150, 94, 46), width=3)
    # red carpet runner toward the door
    c.poly([(X(1180), Y(FLOOR_Y + 8)), (X(1640), Y(FLOOR_Y + 8)), (X(1840), Y(1500)), (X(1100), Y(1500))], fill=wshade(CURTAIN, 1.05), outline=OL, width=5)
    c.line([(X(1200), Y(FLOOR_Y + 22)), (X(1130), Y(1486))], fill=GOLD, width=5)
    c.line([(X(1620), Y(FLOOR_Y + 22)), (X(1810), Y(1486))], fill=GOLD, width=5)
    # framed pictures: theatre masks, a plate of osh
    for (fx, fy, fw, fh, kind) in ((90, 330, 250, 300, "masks"), (720, 360, 280, 230, "osh"), (-380, 360, 230, 280, "film")):
        c.rect((X(fx), Y(fy), X(fx + fw), Y(fy + fh)), fill=(190, 130, 40), outline=OL, width=6, r=6)
        c.rect((X(fx + 22), Y(fy + 22), X(fx + fw - 22), Y(fy + fh - 22)), fill=(255, 244, 224), outline=OL, width=4)
        mx, my = fx + fw / 2, fy + fh / 2
        if kind == "masks":
            for dx, col, rot in ((-34, (255, 214, 10), 1), (34, (120, 180, 240), -1)):
                c.ellipse((X(mx + dx - 50), Y(my - 62), X(mx + dx + 50), Y(my + 62)), fill=col, outline=OL, width=4)
                for sg in (-1, 1): c.circle(X(mx + dx + sg * 18), Y(my - 18), 9, fill=OL, outline=None, width=0)
                if rot > 0: c.arc((X(mx + dx - 26), Y(my - 4), X(mx + dx + 26), Y(my + 36)), 10, 170, fill=OL, width=5)
                else: c.arc((X(mx + dx - 26), Y(my + 18), X(mx + dx + 26), Y(my + 50)), 190, 350, fill=OL, width=5)
        elif kind == "osh":
            c.ellipse((X(mx - 90), Y(my + 6), X(mx + 90), Y(my + 56)), fill=(255, 255, 255), outline=OL, width=4)
            c.pieslice((X(mx - 72), Y(my - 52), X(mx + 72), Y(my + 50)), 180, 360, fill=RICE, outline=OL, width=4)
            for k in range(5): c.line([(X(mx - 46 + k * 22), Y(my - 10 - (k % 2) * 10)), (X(mx - 36 + k * 22), Y(my - 24 - (k % 2) * 10))], fill=CARROT, width=7)
        else:
            c.circle(X(mx), Y(my), 70, fill=(60, 60, 70), outline=OL, width=4)
            for k in range(6):
                ang = k * math.pi / 3
                c.circle(X(mx + 40 * math.cos(ang)), Y(my + 40 * math.sin(ang)), 15, fill=(255, 244, 224), outline=None, width=0)
            c.circle(X(mx), Y(my), 10, fill=(255, 244, 224), outline=None, width=0)
    # glass door + frame
    x0, y0, x1, y1 = DOOR
    c.rect((X(x0 - 30), Y(y0 - 34), X(x1 + 30), Y(y1)), fill=wshade(WOOD, 0.9), outline=OL, width=6, r=6)
    c.rect((X(x0), Y(y0), X(x1), Y(y1)), fill=(196, 230, 250), outline=OL, width=6)
    c.rect((X(x0 + 26), Y(y0 + 26), X(x1 - 26), Y(y1 - 120)), fill=(214, 238, 252), outline=OL, width=4)
    c.poly([(X(x0 + 60), Y(y1 - 130)), (X(x0 + 190), Y(y0 + 30)), (X(x0 + 250), Y(y0 + 30)), (X(x0 + 120), Y(y1 - 130))], fill=(255, 255, 255, 90), outline=None, width=0)
    c.rect((X(x0 + 40), Y((y0 + y1) / 2 - 10), X(x0 + 70), Y((y0 + y1) / 2 + 90)), fill=GOLD, outline=OL, width=4, r=8)
    # truss bar for stage lights
    c.rect((X(-520), Y(20), X(1840), Y(48)), fill=(60, 60, 70), outline=OL, width=5)
    for x in range(-500, 1840, 60):
        c.line([(X(x), Y(22)), (X(x + 30), Y(46))], fill=(90, 90, 100), width=4)
    # chandelier
    cx = 540
    c.line([(X(cx), Y(-320)), (X(cx), Y(90))], fill=OL, width=6)
    c.ellipse((X(cx - 150), Y(130), X(cx + 150), Y(190)), fill=GOLD, outline=OL, width=6)
    c.ellipse((X(cx - 40), Y(80), X(cx + 40), Y(150)), fill=GOLD, outline=OL, width=6)
    c.poly([(X(cx - 30), Y(185)), (X(cx + 30), Y(185)), (X(cx), Y(250))], fill=GOLD, outline=OL, width=5)
    for dx in (-130, -65, 0, 65, 130):
        c.rect((X(cx + dx - 10), Y(104), X(cx + dx + 10), Y(150)), fill=(255, 250, 235), outline=OL, width=4, r=3)
        c.ellipse((X(cx + dx - 11), Y(70), X(cx + dx + 11), Y(106)), fill=(255, 236, 140), outline=OL, width=3)
    im.alpha_composite(c.result())
    # glow around the chandelier bulbs
    g = Image.new("L", (w, h), 0); gd = ImageDraw.Draw(g)
    for dx in (-130, -65, 0, 65, 130): gd.ellipse((X(cx + dx - 40), Y(48), X(cx + dx + 40), Y(128)), fill=200)
    g = g.filter(ImageFilter.GaussianBlur(26))
    gl = Image.new("RGBA", (w, h), (255, 244, 200, 0)); gl.putalpha(g.point(lambda v: int(v * 0.6)))
    im.alpha_composite(gl)
    return im.convert("RGB")

def spotlight_fixture(on=0.0):
    c = SS(170, 190, 3)
    c.rect((70, 0, 100, 40), fill=(70, 70, 80), outline=OL, width=5)
    c.poly([(30, 60), (140, 60), (160, 170), (10, 170)], fill=(50, 50, 60), outline=OL, width=6)
    c.rect((20, 40, 150, 72), fill=(70, 70, 80), outline=OL, width=6, r=8)
    lens = (lerp(120, 255, on), lerp(120, 248, on), lerp(130, 200, on))
    c.ellipse((14, 150, 156, 186), fill=tuple(int(v) for v in lens), outline=OL, width=6)
    return c.result()

def beam_img(length=1700, w0=90, w1=520, alpha=0.42):
    """soft light cone pointing down (+y); apex at (w1/2+20, 0)"""
    W_ = w1 + 40
    m = Image.new("L", (W_, length), 0)
    ImageDraw.Draw(m).polygon([(W_ / 2 - w0 / 2, 0), (W_ / 2 + w0 / 2, 0), (W_ / 2 + w1 / 2, length), (W_ / 2 - w1 / 2, length)], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(22))
    a = np.asarray(m).astype(np.float32) * alpha
    grad = np.linspace(1.0, 0.55, length)[:, None]
    a = a * grad
    im = Image.new("RGBA", (W_, length), SPOT + (0,)); im.putalpha(Image.fromarray(a.astype(np.uint8)))
    return im

def floor_pool(w=520, h=130, alpha=0.5):
    m = Image.new("L", (w + 80, h + 80), 0)
    ImageDraw.Draw(m).ellipse((40, 40, w + 40, h + 40), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(20))
    im = Image.new("RGBA", m.size, SPOT + (0,)); im.putalpha(m.point(lambda v: int(v * alpha)))
    return im

def curtain_strip(w=150, h=1920, side="L"):
    """red velvet curtain at a frame edge (screen-space), gathered with a gold tie-back"""
    c = SS(w + 40, h, 2)
    x0 = 0 if side == "L" else 40
    pts = []
    tie_y = 1180
    for y in range(0, h + 20, 20):
        if y < tie_y: ww = w - 40 * math.sin(math.pi * y / tie_y) * 0.5
        else: ww = w * (0.55 + 0.45 * min(1, (y - tie_y) / 600))
        pts.append(y and (y, ww) or (0, w))
    if side == "L":
        poly = [(x0, 0)] + [(x0 + ww, y) for y, ww in pts] + [(x0, h)]
    else:
        poly = [(x0 + w, 0)] + [(x0 + w - ww, y) for y, ww in pts] + [(x0 + w, h)]
    c.poly(poly, fill=CURTAIN, outline=None, width=0)
    # folds
    for k in range(4):
        fx = (0.18 + 0.22 * k)
        line = []
        for y, ww in pts:
            xx = x0 + ww * fx if side == "L" else x0 + w - ww * fx
            line.append((xx, y))
        c.line(line, fill=wshade(CURTAIN, 0.7), width=10)
        line2 = [(x + (6 if side == "L" else -6), y) for x, y in line]
        c.line(line2, fill=wshade(CURTAIN, 1.25), width=4)
    c.poly(poly, fill=None, outline=OL, width=6)
    # tie-back
    tx = x0 + w * 0.5 if side == "L" else x0 + w * 0.5
    c.rect((tx - w * 0.42, tie_y - 20, tx + w * 0.42, tie_y + 20), fill=GOLD, outline=OL, width=5, r=10)
    c.circle(tx + (w * 0.4 if side == "L" else -w * 0.4), tie_y + 40, 18, fill=GOLD, outline=OL, width=4)
    return c.result()

def valance(w=1080, h=130):
    c = SS(w, h + 40, 2)
    c.rect((-10, -10, w + 10, h - 30), fill=CURTAIN, outline=OL, width=6)
    n = 9
    for k in range(n):
        x0 = k * w / n
        c.pieslice((x0 - 4, h - 90, x0 + w / n + 4, h + 10), 0, 180, fill=CURTAIN, outline=OL, width=6)
    for k in range(n):
        x0 = k * w / n
        c.arc((x0 + 6, h - 80, x0 + w / n - 6, h - 4), 20, 160, fill=wshade(CURTAIN, 0.7), width=6)
    # gold fringe
    for k in range(n):
        x0 = k * w / n
        c.circle(x0, h - 36, 13, fill=GOLD, outline=OL, width=4)
    c.line([(0, h - 110), (w, h - 110)], fill=GOLD, width=8)
    return c.result()

# ---------------------------------------------------------------- tables, chairs, tableware
def table_img(w=470, top_h=None, drape=230, base_h=420):
    """round table seen from the front: cream cloth with scalloped hem, pedestal; anchor = floor centre"""
    th = top_h or w * 0.24
    Hh = base_h + th / 2 + 30
    c = SS(w + 40, Hh, 3)
    cx = (w + 40) / 2
    top_y = 20 + th / 2
    # pedestal + base
    c.rect((cx - 22, top_y + drape - 30, cx + 22, Hh - 30), fill=wshade(WOOD, 0.9), outline=OL, width=5)
    c.ellipse((cx - 110, Hh - 52, cx + 110, Hh - 12), fill=wshade(WOOD, 0.85), outline=OL, width=5)
    # cloth drape
    pts = [(cx - w / 2, top_y)]
    n = 7
    for k in range(n + 1):
        x = cx - w / 2 - 6 + (w + 12) * k / n
        pts.append((x, top_y + drape + (14 if k % 2 else 0)))
    pts.append((cx + w / 2, top_y))
    c.poly(pts, fill=wshade(CLOTH, 0.96), outline=OL, width=5)
    for k in range(1, n):
        x = cx - w / 2 + w * k / n
        c.line([(x, top_y + th * 0.4), (x + (k - n / 2) * 4, top_y + drape)], fill=wshade(CLOTH, 0.85), width=4)
    c.ellipse((cx - w / 2, 20, cx + w / 2, 20 + th), fill=CLOTH, outline=OL, width=6)
    c.ellipse((cx - w / 2 + 30, 32, cx + w / 2 - 30, 20 + th - 14), fill=None, outline=(240, 222, 190), width=4)
    return c.result(), cx, Hh - 20, top_y      # image, anchor x, anchor y (floor), table-top centre y

def chair_img(h=520, w=200, back=True):
    c = SS(w + 20, h + 20, 3)
    seat_y = h * 0.52
    if back:
        c.rect((10 + w * 0.08, 10, 10 + w * 0.92, seat_y), fill=wshade(WOOD, 1.08), outline=OL, width=5, r=26)
        c.rect((10 + w * 0.22, 34, 10 + w * 0.78, seat_y - 40), fill=CURTAIN, outline=OL, width=4, r=18)
    for x in (w * 0.12, w * 0.8):
        c.rect((10 + x, seat_y, 10 + x + w * 0.1, h + 8), fill=wshade(WOOD, 0.85), outline=OL, width=5, r=4)
    c.rect((10, seat_y - 10, w + 10, seat_y + 36), fill=WOOD, outline=OL, width=5, r=10)
    return c.result()

def plate_img(r=120, kind="empty"):
    c = SS(r * 2 + 30, r * 1.4 + 30, 3)
    cx, cy = r + 15, r * 0.4 + 40
    c.ellipse((cx - r, cy - r * 0.34, cx + r, cy + r * 0.34), fill=(255, 255, 255), outline=OL, width=5)
    c.ellipse((cx - r * 0.66, cy - r * 0.2, cx + r * 0.66, cy + r * 0.2), fill=(240, 244, 248), outline=(200, 206, 214), width=3)
    c.arc((cx - r * 0.92, cy - r * 0.3, cx + r * 0.92, cy + r * 0.3), 200, 260, fill=(255, 255, 255), width=4)
    return c.result(), cx, cy

def fork_img(L=150):
    c = SS(40, L + 20, 3)
    c.rect((14, 60, 26, L + 10), fill=STEEL, outline=OL, width=4, r=5)
    c.rect((6, 10, 34, 64), fill=STEEL, outline=OL, width=4, r=6)
    for x in (13, 20, 27): c.line([(x, 8), (x, 42)], fill=OL, width=3)
    return c.result()

def spoon_img(L=150):
    c = SS(44, L + 20, 3)
    c.rect((16, 50, 28, L + 10), fill=STEEL, outline=OL, width=4, r=5)
    c.ellipse((4, 6, 40, 64), fill=STEEL, outline=OL, width=4)
    c.ellipse((12, 14, 22, 30), fill=(255, 255, 255), outline=None, width=0)
    return c.result()

# ---------------------------------------------------------------- restaurant exterior
EX_OX, EX_OY, EX_W, EX_H = -340, -340, 1760, 2600
EX_DOOR = (575, 880, 885, 1520)
EX_SIGN = (390, 600, 1070, 800)
def exterior_back():
    w, h = EX_W, EX_H
    ox, oy = EX_OX, EX_OY
    X = lambda x: x - ox; Y = lambda y: y - oy
    a = np.zeros((h, w, 3), np.float32)
    yy = np.mgrid[0:h, 0:w][0].astype(np.float32)
    t = np.clip(yy / (h * 0.42), 0, 1)[..., None]
    a[:] = (1 - t) * np.array([92, 170, 235], np.float32) + t * np.array([190, 228, 250], np.float32)
    im = Image.fromarray(a.astype(np.uint8)).convert("RGBA")
    c = SS(w, h, 2)
    c.circle(X(1180), Y(-120), 95, fill=(255, 236, 140), outline=None, width=0)
    c.circle(X(1180), Y(-120), 70, fill=(255, 214, 80), outline=OL, width=5)
    for cx, cy, s in ((-80, -40, 1.0), (760, 40, 0.8), (260, -200, 0.7)):
        for dx, dy, r in ((-60, 0, 50), (0, -24, 66), (64, 0, 48), (20, 20, 50)):
            c.circle(X(cx + dx * s), Y(cy + dy * s), r * s, fill=(255, 255, 255), outline=None, width=0)
    # facade
    fx0, fx1, fy0, fy1 = -340, 1420, 300, 1560
    c.rect((X(fx0), Y(fy0), X(fx1), Y(fy1)), fill=(226, 196, 150), outline=OL, width=6)
    rnd = random.Random(4)
    for row, y in enumerate(range(fy0 + 20, fy1, 52)):
        off = 0 if row % 2 else 60
        for x in range(fx0 - 120 + off, fx1, 120):
            col = (214, 180, 132) if rnd.random() < 0.5 else (232, 204, 160)
            c.rect((X(x + 4), Y(y + 4), X(x + 116), Y(y + 48)), fill=col, outline=(196, 162, 118), width=3, r=4)
    c.rect((X(fx0), Y(fy0 - 40), X(fx1), Y(fy0 + 26)), fill=(196, 140, 80), outline=OL, width=6)
    c.rect((X(fx0), Y(fy0 + 26), X(fx1), Y(fy0 + 46)), fill=(160, 104, 56), outline=OL, width=4)
    # windows with warm light + striped awnings
    for wx0, wx1 in ((-260, 330), (1040, 1400)):
        c.rect((X(wx0 - 18), Y(900 - 18), X(wx1 + 18), Y(1340 + 18)), fill=(150, 96, 50), outline=OL, width=6, r=6)
        c.rect((X(wx0), Y(900), X(wx1), Y(1340)), fill=(255, 222, 140), outline=OL, width=5)
        c.rect((X(wx0), Y(1180), X(wx1), Y(1340)), fill=(250, 200, 110), outline=None, width=0)
        c.line([(X((wx0 + wx1) / 2), Y(900)), (X((wx0 + wx1) / 2), Y(1340))], fill=OL, width=5)
        # silhouettes of tables inside
        for tx in (wx0 + (wx1 - wx0) * 0.27, wx0 + (wx1 - wx0) * 0.73):
            c.ellipse((X(tx - 70), Y(1230), X(tx + 70), Y(1262)), fill=(232, 170, 90), outline=None, width=0)
            c.rect((X(tx - 8), Y(1250), X(tx + 8), Y(1340)), fill=(232, 170, 90), outline=None, width=0)
        c.poly([(X(wx0 + 30), Y(1340)), (X(wx0 + 150), Y(900)), (X(wx0 + 210), Y(900)), (X(wx0 + 90), Y(1340))], fill=(255, 255, 255, 70), outline=None, width=0)
        aw0 = 800
        n = int((wx1 - wx0 + 60) / 70)
        for k in range(n):
            xa = wx0 - 30 + k * (wx1 - wx0 + 60) / n
            xb = xa + (wx1 - wx0 + 60) / n
            c.poly([(X(xa), Y(aw0)), (X(xb), Y(aw0)), (X(xb + 6), Y(aw0 + 90)), (X(xa + 6), Y(aw0 + 90))], fill=CURTAIN if k % 2 == 0 else (255, 244, 224), outline=None, width=0)
        c.poly([(X(wx0 - 30), Y(aw0)), (X(wx1 + 30), Y(aw0)), (X(wx1 + 36), Y(aw0 + 90)), (X(wx0 - 24), Y(aw0 + 90))], fill=None, outline=OL, width=6)
        for k in range(n):
            xa = wx0 - 24 + k * (wx1 - wx0 + 60) / n
            c.pieslice((X(xa), Y(aw0 + 62), X(xa + (wx1 - wx0 + 60) / n), Y(aw0 + 118)), 0, 180, fill=CURTAIN if k % 2 == 0 else (255, 244, 224), outline=OL, width=4)
    # door
    x0, y0, x1, y1 = EX_DOOR
    c.rect((X(x0 - 36), Y(y0 - 36), X(x1 + 36), Y(y1)), fill=(120, 74, 38), outline=OL, width=6, r=8)
    c.rect((X(x0), Y(y0), X(x1), Y(y1)), fill=(255, 214, 140), outline=OL, width=6)
    c.rect((X(x0 + 24), Y(y0 + 24), X(x1 - 24), Y(y1 - 130)), fill=(255, 228, 160), outline=OL, width=4)
    c.poly([(X(x0 + 50), Y(y1 - 140)), (X(x0 + 170), Y(y0 + 30)), (X(x0 + 220), Y(y0 + 30)), (X(x0 + 100), Y(y1 - 140))], fill=(255, 255, 255, 110), outline=None, width=0)
    c.rect((X(x1 - 70), Y((y0 + y1) / 2), X(x1 - 42), Y((y0 + y1) / 2 + 110)), fill=GOLD, outline=OL, width=4, r=8)
    # step
    c.rect((X(x0 - 80), Y(y1 - 6), X(x1 + 80), Y(y1 + 40)), fill=(200, 196, 190), outline=OL, width=5, r=4)
    # sidewalk + curb + road
    c.rect((X(fx0), Y(fy1), X(fx1), Y(2100)), fill=(214, 210, 202), outline=OL, width=6)
    for y in (1640, 1760, 1920):
        c.line([(X(fx0), Y(y)), (X(fx1), Y(y))], fill=(190, 186, 178), width=4)
    for x in range(-340, 1420, 200):
        c.line([(X(x), Y(fy1)), (X(x - 80), Y(2100))], fill=(190, 186, 178), width=4)
    c.rect((X(fx0), Y(2100), X(fx1), Y(2140)), fill=(170, 166, 160), outline=OL, width=5)
    c.rect((X(fx0), Y(2140), X(fx1), Y(2260)), fill=(84, 88, 96), outline=OL, width=5)
    for x in range(-300, 1420, 260):
        c.rect((X(x), Y(2190), X(x + 130), Y(2206)), fill=(240, 240, 240), outline=None, width=0)
    im.alpha_composite(c.result())
    # warm light spill from the windows and door onto the sidewalk
    g = Image.new("L", (w, h), 0); gd = ImageDraw.Draw(g)
    for xa, xb in ((-260, 330), (575, 885), (1040, 1400)):
        gd.polygon([(X(xa), Y(1560)), (X(xb), Y(1560)), (X(xb + 80), Y(1800)), (X(xa - 80), Y(1800))], fill=120)
    g = g.filter(ImageFilter.GaussianBlur(40))
    gl = Image.new("RGBA", (w, h), (255, 220, 140, 0)); gl.putalpha(g.point(lambda v: int(v * 0.5)))
    im.alpha_composite(gl)
    return im.convert("RGB")

def potted_plant(h=420):
    w = h * 0.7
    c = SS(w, h, 3)
    cx = w / 2
    for k, (dx, dy, rr) in enumerate(((0, 0.28, 0.2), (-0.16, 0.36, 0.15), (0.16, 0.36, 0.15), (-0.08, 0.18, 0.13), (0.1, 0.2, 0.12))):
        c.circle(cx + dx * h, dy * h, rr * h, fill=(70, 168, 86), outline=OL, width=5)
    for k, (dx, dy, rr) in enumerate(((0, 0.28, 0.2), (-0.16, 0.36, 0.15), (0.16, 0.36, 0.15), (-0.08, 0.18, 0.13), (0.1, 0.2, 0.12))):
        c.circle(cx + dx * h - rr * h * 0.2, dy * h - rr * h * 0.2, rr * h * 0.6, fill=(98, 190, 104), outline=None, width=0)
    c.poly([(cx - h * 0.2, h * 0.55), (cx + h * 0.2, h * 0.55), (cx + h * 0.15, h - 6), (cx - h * 0.15, h - 6)], fill=(200, 100, 60), outline=OL, width=5)
    c.rect((cx - h * 0.23, h * 0.52, cx + h * 0.23, h * 0.6), fill=(220, 120, 76), outline=OL, width=5, r=6)
    return c.result()

def clapper_icon(s=120, open_ang=22, text=None):
    c = SS(s * 1.25, s * 1.15, 3)
    x0, y0 = s * 0.08, s * 0.38
    w, h = s * 1.05, s * 0.68
    c.rect((x0, y0, x0 + w, y0 + h), fill=(40, 40, 46), outline=OL, width=max(3, s * 0.045), r=s * 0.05)
    c.rect((x0, y0, x0 + w, y0 + h * 0.3), fill=(255, 255, 255), outline=OL, width=max(3, s * 0.04))
    for k in range(5):
        xa = x0 + k * w / 5
        c.poly([(xa + w * 0.04, y0), (xa + w * 0.14, y0), (xa + w * 0.08, y0 + h * 0.3), (xa - w * 0.02, y0 + h * 0.3)], fill=(40, 40, 46), outline=None, width=0)
    # hinged clapper arm
    a = math.radians(-open_ang)
    px, py = x0, y0
    L, T = w, h * 0.26
    def rp(x, y): return (px + x * math.cos(a) - y * math.sin(a), py + x * math.sin(a) + y * math.cos(a))
    arm = [rp(0, -T), rp(L, -T), rp(L, 0), rp(0, 0)]
    c.poly(arm, fill=(255, 255, 255), outline=OL, width=max(3, s * 0.04))
    for k in range(5):
        xa = k * L / 5
        c.poly([rp(xa + L * 0.04, -T), rp(xa + L * 0.14, -T), rp(xa + L * 0.08, 0), rp(xa - L * 0.02, 0)], fill=(40, 40, 46), outline=None, width=0)
    c.poly(arm, fill=None, outline=OL, width=max(3, s * 0.04))
    c.circle(px, py, s * 0.05, fill=(200, 200, 210), outline=OL, width=max(2, s * 0.03))
    im = c.result()
    if text:
        t = text_img(text, int(s * 0.16), fill=(255, 255, 255), stroke=0, shadow=0)
        maxw = w * 0.9
        if t.width > maxw: t = t.resize((int(maxw), int(t.height * maxw / t.width)), Image.LANCZOS)
        im.alpha_composite(t, (int(x0 + w / 2 - t.width / 2), int(y0 + h * 0.65 - t.height / 2)))
    return im

def restoran_sign(lit=1.0, w=680, h=200):
    """sign board above the door: RESTORAN + clapperboard icon; lit 0..1 (bulbs + text glow)"""
    c = SS(w, h, 3)
    c.rect((6, 6, w - 6, h - 6), fill=wshade((60, 30, 34), 1 + 0.2 * lit), outline=OL, width=7, r=26)
    c.rect((22, 22, w - 22, h - 22), fill=None, outline=GOLD, width=5, r=16)
    for k in range(14):
        x = 40 + k * (w - 80) / 13
        col = tuple(int(lerp(a, b, lit)) for a, b in zip((120, 100, 80), (255, 240, 170)))
        c.circle(x, 22, 9, fill=col, outline=OL, width=3)
        c.circle(x, h - 22, 9, fill=col, outline=OL, width=3)
    im = c.result()
    ic = clapper_icon(118, 24)
    im.alpha_composite(ic, (34, int(h / 2 - ic.height / 2 + 4)))
    tcol = tuple(int(lerp(a, b, lit)) for a, b in zip((150, 120, 70), (255, 222, 90)))
    t = text_img("RESTORAN", 104, fill=tcol, stroke=6, stroke_fill=OL, shadow=0)
    if t.width > w - 230: t = text_img("RESTORAN", int(104 * (w - 230) / t.width), fill=tcol, stroke=6, stroke_fill=OL, shadow=0)
    if lit > 0.05:
        gl = t.getchannel("A").filter(ImageFilter.GaussianBlur(14))
        gi = Image.new("RGBA", t.size, (255, 220, 120, 0)); gi.putalpha(gl.point(lambda v: int(v * 0.8 * lit)))
        im.alpha_composite(gi, (int(180 + (w - 200 - t.width) / 2), int(h / 2 - t.height / 2 + 4)))
    im.alpha_composite(t, (int(180 + (w - 200 - t.width) / 2), int(h / 2 - t.height / 2 + 4)))
    return im

def sold_sign(w=420, h=170):
    c = SS(w, h, 3)
    c.rect((6, 6, w - 6, h - 6), fill=SOLD, outline=OL, width=7, r=18)
    c.rect((20, 20, w - 20, h - 20), fill=None, outline=(255, 255, 255), width=5, r=10)
    im = c.result()
    t = text_img("SOTILDI", 96, fill=(255, 255, 255), stroke=6, stroke_fill=OL, shadow=0)
    if t.width > w - 50: t = t.resize((w - 50, int(t.height * (w - 50) / t.width)), Image.LANCZOS)
    im.alpha_composite(t, (int(w / 2 - t.width / 2), int(h / 2 - t.height / 2 + 4)))
    # tape corners
    for (x, y, r) in ((20, 14, -30), (w - 20, 14, 30)):
        tp = Image.new("RGBA", (90, 34), (255, 250, 220, 200))
        tp = tp.rotate(r, expand=True, resample=Image.BICUBIC)
        im.alpha_composite(tp, (int(x - tp.width / 2), int(y - tp.height / 2)))
    return im

# ---------------------------------------------------------------- kitchen
KT_OX, KT_OY, KT_W, KT_H = -340, -340, 1760, 2600
COUNTER_TOP = 1270
def kitchen_back():
    w, h = KT_W, KT_H
    ox, oy = KT_OX, KT_OY
    X = lambda x: x - ox; Y = lambda y: y - oy
    c = SS(w, h, 2, bg=TILE + (255,))
    for y in range(-340, 1300, 90):
        c.line([(0, Y(y)), (w, Y(y))], fill=(210, 220, 226), width=4)
    for x in range(-340, 1420, 90):
        c.line([(X(x), 0), (X(x), Y(1300))], fill=(210, 220, 226), width=4)
    # accent tile band
    c.rect((0, Y(820), w, Y(910)), fill=(150, 200, 220), outline=OL, width=4)
    for x in range(-340, 1420, 90):
        c.rect((X(x + 8), Y(828), X(x + 82), Y(902)), fill=(176, 216, 232) if (x // 90) % 2 else (130, 186, 210), outline=None, width=0)
    # hood above the stove
    c.poly([(X(-120), Y(380)), (X(420), Y(380)), (X(500), Y(620)), (X(-200), Y(620))], fill=STEEL, outline=OL, width=6)
    c.rect((X(-30), Y(-340), X(330), Y(380)), fill=wshade(STEEL, 0.94), outline=OL, width=6)
    c.rect((X(-200), Y(606), X(500), Y(640)), fill=wshade(STEEL, 0.85), outline=OL, width=5)
    # ladle rail with hanging ladles / spatula / whisk
    c.rect((X(700), Y(430), X(1280), Y(450)), fill=wshade(STEEL, 0.8), outline=OL, width=5, r=8)
    for k, x in enumerate(range(740, 1260, 110)):
        c.line([(X(x), Y(450)), (X(x), Y(480))], fill=OL, width=4)
        c.rect((X(x - 8), Y(470), X(x + 8), Y(720)), fill=STEEL, outline=OL, width=4, r=6)
        if k % 3 == 0: c.ellipse((X(x - 46), Y(700), X(x + 46), Y(770)), fill=STEEL, outline=OL, width=5)
        elif k % 3 == 1: c.rect((X(x - 34), Y(700), X(x + 34), Y(790)), fill=(60, 60, 66), outline=OL, width=5, r=8)
        else:
            for q in range(4): c.ellipse((X(x - 24 + q * 4), Y(680 + q * 6), X(x + 24 - q * 4), Y(790 - q * 2)), fill=None, outline=(120, 126, 134), width=4)
    # shelf with jars
    c.rect((X(700), Y(1000), X(1300), Y(1030)), fill=WOOD, outline=OL, width=5, r=4)
    for k, (x, col) in enumerate(((730, CARROT), (840, RICE), (950, (120, 170, 80)), (1060, (200, 60, 60)), (1170, (240, 220, 180)))):
        c.rect((X(x), Y(880), X(x + 80), Y(1000)), fill=col, outline=OL, width=5, r=12)
        c.rect((X(x - 6), Y(866), X(x + 86), Y(896)), fill=(170, 110, 60), outline=OL, width=4, r=6)
        c.rect((X(x + 14), Y(920), X(x + 66), Y(960)), fill=(255, 255, 255), outline=None, width=0, r=4)
    return c.result().convert("RGB")

def counter_front(w=1760, top=COUNTER_TOP, h=1400):
    c = SS(w, h, 2)
    c.rect((0, 40, w, h), fill=STEEL, outline=OL, width=6)
    for k in range(6):
        x = 30 + k * (w - 40) / 6
        c.rect((x + 10, 110, x + (w - 40) / 6 - 14, h - 40), fill=wshade(STEEL, 1.05), outline=wshade(STEEL, 0.75), width=4, r=10)
        c.rect((x + (w - 40) / 12 - 40, 150, x + (w - 40) / 12 + 40, 168), fill=wshade(STEEL, 0.7), outline=OL, width=3, r=6)
    c.rect((0, 0, w, 52), fill=(226, 232, 236), outline=OL, width=6)
    c.line([(10, 18), (w - 10, 18)], fill=(255, 255, 255), width=5)
    return c.result()

def stove_qozon():
    w, h = 520, 460
    c = SS(w, h, 2)
    c.rect((20, 330, w - 20, h - 10), fill=(60, 60, 66), outline=OL, width=6, r=8)
    for x in (110, w - 110):
        c.circle(x, 395, 26, fill=(200, 60, 40), outline=OL, width=5)
    # qozon (black cauldron) with osh
    c.ellipse((40, 150, w - 40, 250), fill=(30, 30, 34), outline=OL, width=7)
    c.pieslice((40, -60, w - 40, 340), 0, 180, fill=(34, 34, 38), outline=OL, width=7)
    c.ellipse((70, 158, w - 70, 236), fill=RICE, outline=OL, width=5)
    for k in range(9):
        x = 110 + k * 36
        c.line([(x, 190 + (k % 3) * 10), (x + 16, 178 + (k % 3) * 10)], fill=CARROT, width=8)
    for x in (150, 260, 360):
        c.circle(x, 200, 13, fill=MEAT, outline=OL, width=3)
    c.ellipse((40, 150, w - 40, 250), fill=None, outline=OL, width=7)
    for sg in (-1, 1):
        c.ellipse((w / 2 + sg * (w / 2 - 40) - 26, 190, w / 2 + sg * (w / 2 - 40) + 26, 230), fill=(30, 30, 34), outline=OL, width=5)
    c.arc((80, 240, w - 80, 320), 20, 160, fill=(80, 80, 90), width=6)
    return c.result()

def cutting_board(w=380, h=78):
    c = SS(w + 20, h + 20, 3)
    c.rect((10, 10, w + 10, h + 10), fill=(196, 138, 80), outline=OL, width=6, r=14)
    c.rect((10, 10, w + 10, h * 0.45 + 10), fill=(214, 160, 100), outline=None, width=0, r=12)
    c.rect((10, 10, w + 10, h + 10), fill=None, outline=OL, width=6, r=14)
    c.circle(w - 18, h * 0.5 + 10, 10, fill=(150, 100, 60), outline=OL, width=3)
    return c.result()

def onion_ring(r=26):
    c = SS(r * 2 + 12, r * 2 + 12, 3)
    c.circle(r + 6, r + 6, r, fill=None, outline=OL, width=r * 0.42)
    c.circle(r + 6, r + 6, r, fill=None, outline=(240, 226, 236), width=r * 0.24)
    return c.result()

def onion_whole(r=60):
    c = SS(r * 2.4, r * 2.6, 3)
    cx, cy = r * 1.2, r * 1.5
    c.ellipse((cx - r, cy - r * 0.95, cx + r, cy + r * 0.95), fill=(220, 160, 200), outline=OL, width=5)
    c.arc((cx - r * 0.6, cy - r * 0.9, cx + r * 0.6, cy + r * 0.9), 250, 290, fill=(190, 120, 170), width=4)
    c.poly([(cx - r * 0.16, cy - r * 0.9), (cx, cy - r * 1.4), (cx + r * 0.16, cy - r * 0.9)], fill=(110, 170, 80), outline=OL, width=4)
    return c.result()

def onion_half(r=60):
    c = SS(r * 2.4, r * 1.7, 3)
    cx, cy = r * 1.2, r * 0.85
    c.ellipse((cx - r, cy - r * 0.7, cx + r, cy + r * 0.7), fill=(246, 236, 242), outline=OL, width=5)
    for k in (0.75, 0.5, 0.25):
        c.ellipse((cx - r * k, cy - r * 0.7 * k, cx + r * k, cy + r * 0.7 * k), fill=None, outline=(206, 150, 196), width=4)
    return c.result()

# ---------------------------------------------------------------- cash desk
CD_OX, CD_OY, CD_W, CD_H = -340, -440, 1760, 2760
CD_TOP = 1290
def cashdesk_back():
    w, h = CD_W, CD_H
    ox, oy = CD_OX, CD_OY
    X = lambda x: x - ox; Y = lambda y: y - oy
    base = Image.new("RGB", (w, h), R_GOLD)
    c = SS(w, h, 2)
    for x in range(-340, 1420, 120):
        c.rect((X(x), 0, X(x + 46), Y(1700)), fill=(255, 255, 255, 18), outline=None, width=0)
    ikat_band(c, X, Y, -340, 1420, 1650, 1700)
    c.rect((X(-340), Y(1700), X(1420), Y(1900)), fill=WOOD, outline=OL, width=6)
    c.rect((X(-340), Y(1900), X(1420), Y(2320)), fill=(170, 108, 56), outline=OL, width=6)
    for y in (1950, 2030, 2140, 2280): c.line([(0, Y(y)), (w, Y(y))], fill=(140, 86, 42), width=4)
    # menu board on the wall (icons only)
    c.rect((X(470), Y(260), X(1130), Y(760)), fill=(50, 46, 44), outline=OL, width=8, r=12)
    c.rect((X(490), Y(280), X(1110), Y(740)), fill=None, outline=(140, 110, 70), width=5, r=8)
    for k in range(4):
        y = 340 + k * 105
        c.circle(X(540), Y(y), 26, fill=(RICE, CARROT, (200, 80, 60), (120, 170, 80))[k], outline=OL, width=4)
        c.line([(X(590), Y(y)), (X(880 - (k % 2) * 80), Y(y))], fill=(210, 205, 195), width=12)
        c.line([(X(960), Y(y)), (X(1060), Y(y))], fill=GOLD, width=12)
    # lamp
    c.line([(X(160), Y(-440)), (X(160), Y(360))], fill=OL, width=6)
    c.pieslice((X(60), Y(330), X(260), Y(470)), 180, 360, fill=CURTAIN, outline=OL, width=6)
    c.circle(X(160), Y(402), 16, fill=(255, 240, 180), outline=OL, width=4)
    base = base.convert("RGBA"); base.alpha_composite(c.result())
    return base.convert("RGB")

def cash_counter(w=1500, h=640):
    c = SS(w, h, 2)
    c.rect((0, 46, w, h), fill=WOOD, outline=OL, width=7)
    n = 5
    for k in range(n):
        x = 30 + k * (w - 40) / n
        c.rect((x + 10, 100, x + (w - 40) / n - 14, h - 50), fill=wshade(WOOD, 1.12), outline=wshade(WOOD, 0.7), width=5, r=12)
        c.rect((x + 40, 130, x + (w - 40) / n - 44, h - 80), fill=None, outline=wshade(WOOD, 0.85), width=4, r=8)
    c.rect((0, h - 40, w, h), fill=wshade(WOOD, 0.75), outline=OL, width=6)
    c.rect((0, 0, w, 60), fill=(150, 98, 50), outline=OL, width=7, r=8)
    c.line([(14, 18), (w - 14, 18)], fill=(190, 134, 76), width=6)
    return c.result()

def register_img(w=300, h=260):
    c = SS(w + 20, h + 20, 2)
    ox, oy = 10, 10
    c.rect((ox + w * 0.2, oy, ox + w * 0.62, oy + h * 0.3), fill=(80, 70, 66), outline=OL, width=6, r=8)
    c.rect((ox + w * 0.25, oy + h * 0.06, ox + w * 0.57, oy + h * 0.22), fill=(120, 230, 160), outline=OL, width=4, r=4)
    c.poly([(ox + w * 0.04, oy + h * 0.32), (ox + w * 0.96, oy + h * 0.32), (ox + w, oy + h * 0.76), (ox, oy + h * 0.76)], fill=(200, 60, 60), outline=OL, width=6)
    for i in range(4):
        for j in range(2):
            x = ox + w * (0.14 + 0.19 * i); y = oy + h * (0.4 + 0.16 * j)
            c.rect((x, y, x + w * 0.13, y + h * 0.1), fill=(250, 246, 236), outline=OL, width=4, r=4)
    c.rect((ox, oy + h * 0.76, ox + w, oy + h), fill=(170, 46, 46), outline=OL, width=6, r=6)
    c.rect((ox + w * 0.4, oy + h * 0.85, ox + w * 0.6, oy + h * 0.91), fill=OL, outline=None, width=0, r=3)
    # receipt printer on the right side
    c.rect((ox + w * 0.68, oy + h * 0.06, ox + w * 0.98, oy + h * 0.3), fill=(90, 90, 100), outline=OL, width=5, r=6)
    c.rect((ox + w * 0.72, oy + h * 0.04, ox + w * 0.94, oy + h * 0.1), fill=(30, 30, 34), outline=OL, width=3, r=2)
    return c.result()

def candy_bowl(r=90):
    c = SS(r * 2.4, r * 1.6, 3)
    cx = r * 1.2
    cols = [(230, 60, 80), (60, 150, 230), (255, 196, 40), (80, 190, 110), (200, 90, 220)]
    for k in range(9):
        x = cx - r * 0.7 + (k % 5) * r * 0.35; y = r * 0.45 - (k // 5) * r * 0.22 + (k % 2) * 6
        c.ellipse((x - r * 0.2, y - r * 0.13, x + r * 0.2, y + r * 0.13), fill=cols[k % 5], outline=OL, width=3)
        c.poly([(x - r * 0.2, y), (x - r * 0.34, y - r * 0.1), (x - r * 0.34, y + r * 0.1)], fill=cols[k % 5], outline=OL, width=3)
        c.poly([(x + r * 0.2, y), (x + r * 0.34, y - r * 0.1), (x + r * 0.34, y + r * 0.1)], fill=cols[k % 5], outline=OL, width=3)
    c.pieslice((cx - r, -r * 0.3 + r * 0.4, cx + r, r * 1.45), 0, 180, fill=(190, 230, 250, 200), outline=OL, width=5)
    c.line([(cx - r, r * 0.88 - 0.05), (cx + r, r * 0.88)], fill=OL, width=5)
    return c.result()

# ---------------------------------------------------------------- blogger set
BL_OX, BL_OY, BL_W, BL_H = -260, -660, 1600, 3000
def blogger_back():
    w, h = BL_W, BL_H
    ox, oy = BL_OX, BL_OY
    X = lambda x: x - ox; Y = lambda y: y - oy
    a = np.zeros((h, w, 3), np.float32) + np.array(NAVY, np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    gx, gy = X(200), Y(640)
    d = np.sqrt((xx - gx) ** 2 + (yy - gy) ** 2)
    glow = np.exp(-(d / 620) ** 2) * 0.55 + np.exp(-((d - 300) / 90) ** 2) * 0.25
    a += glow[..., None] * (np.array(RING, np.float32) - a) * 0.9
    base = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    c = SS(w, h, 2)
    for k, x in enumerate(range(380, 1400, 170)):
        c.rect((X(x), Y(260), X(x + 130), Y(1500)), fill=(255, 255, 255, 14), outline=(14, 18, 28, 255), width=4, r=10)
    c.rect((X(760), Y(560), X(1260), Y(590)), fill=(60, 70, 96), outline=OL, width=5, r=4)
    c.rect((X(790), Y(470), X(860), Y(560)), fill=(255, 214, 10), outline=OL, width=5, r=6)
    c.rect((X(880), Y(440), X(930), Y(560)), fill=(229, 56, 59), outline=OL, width=5, r=6)
    c.circle(X(1010), Y(520), 40, fill=(46, 173, 91), outline=OL, width=5)
    c.rect((X(1080), Y(480), X(1200), Y(560)), fill=(90, 190, 230), outline=OL, width=5, r=8)
    c.rect((0, Y(1700), w, h), fill=(22, 26, 38, 255), outline=OL, width=6)
    c.ellipse((X(40), Y(1700), X(1040), Y(1900)), fill=(52, 60, 90), outline=OL, width=6)
    c.ellipse((X(110), Y(1725), X(970), Y(1875)), fill=None, outline=(255, 214, 10), width=5)
    rx, ry, R = 200, 640, 300
    c.line([(X(rx), Y(ry + R)), (X(rx), Y(1760))], fill=OL, width=22)
    c.line([(X(rx), Y(ry + R)), (X(rx), Y(1760))], fill=(80, 86, 100), width=12)
    for dx in (-110, 0, 110):
        c.line([(X(rx), Y(1690)), (X(rx + dx), Y(1790))], fill=OL, width=16)
    im = base.convert("RGBA"); im.alpha_composite(c.result())
    g = Image.new("L", (w, h), 0); gd = ImageDraw.Draw(g)
    gd.ellipse((X(rx - R - 30), Y(ry - R - 30), X(rx + R + 30), Y(ry + R + 30)), outline=255, width=90)
    g = g.filter(ImageFilter.GaussianBlur(40))
    glow_l = Image.new("RGBA", (w, h), RING + (0,)); glow_l.putalpha(g.point(lambda v: int(v * 0.85)))
    im.alpha_composite(glow_l)
    c2 = SS(w, h, 2)
    c2.ellipse((X(rx - R), Y(ry - R), X(rx + R), Y(ry + R)), fill=None, outline=OL, width=64)
    c2.ellipse((X(rx - R + 7), Y(ry - R + 7), X(rx + R - 7), Y(ry + R - 7)), fill=None, outline=RING, width=50)
    c2.ellipse((X(rx - R + 18), Y(ry - R + 18), X(rx + R - 18), Y(ry + R - 18)), fill=None, outline=(255, 255, 255), width=18)
    px, py = -60, 1800
    for k, (dx, dy, ang) in enumerate(((-80, -260, -30), (0, -330, 0), (80, -260, 30), (-120, -150, -55), (120, -150, 55))):
        c2.ellipse((X(px + dx - 50), Y(py - 170 + dy), X(px + dx + 50), Y(py - 170 + dy + 190)), fill=(70, 170, 90), outline=OL, width=6)
        c2.line([(X(px + dx), Y(py - 160 + dy + 20)), (X(px + dx * 0.6), Y(py - 140 + dy + 170))], fill=(40, 120, 60), width=5)
    c2.poly([(X(px - 110), Y(py - 170)), (X(px + 110), Y(py - 170)), (X(px + 80), Y(py)), (X(px - 80), Y(py))], fill=(214, 110, 70), outline=OL, width=6)
    c2.rect((X(px - 124), Y(py - 196), X(px + 124), Y(py - 160)), fill=(230, 130, 86), outline=OL, width=6, r=6)
    im.alpha_composite(c2.result())
    return im.convert("RGB")

def phone_tripod():
    w, h = 420, 1300
    c = SS(w, h, 2)
    cx = 210
    for dx in (-170, 0, 170):
        c.line([(cx, 560), (cx + dx, h - 10)], fill=OL, width=22)
        c.line([(cx, 560), (cx + dx, h - 10)], fill=(70, 76, 90), width=12)
    c.rect((cx - 26, 430, cx + 26, 600), fill=(60, 66, 80), outline=OL, width=6, r=8)
    c.rect((cx - 60, 400, cx + 60, 440), fill=(60, 66, 80), outline=OL, width=6, r=8)
    c.rect((cx - 112, 10, cx + 112, 420), fill=(42, 46, 58), outline=OL, width=8, r=34)
    c.rect((cx - 92, 32, cx - 12, 130), fill=(28, 30, 40), outline=OL, width=5, r=18)
    for (x, y) in ((cx - 72, 58), (cx - 72, 104), (cx - 34, 80)):
        c.circle(x, y, 15, fill=(70, 80, 110), outline=OL, width=4)
        c.circle(x - 4, y - 4, 4, fill=(200, 210, 255), outline=None, width=0)
    c.circle(cx + 70, 60, 14, fill=(255, 70, 70), outline=OL, width=4)
    return c.result(), 1060 - 210, 1060

# ---------------------------------------------------------------- overlays / bubbles
def thought_bubble(w=520, h=400, icon=True):
    c = SS(w, h, 3)
    pts = blob_pts(w / 2, h / 2, w * 0.44, h * 0.4, n=90, wob=0.0)
    # scalloped cloud
    for k in range(14):
        a = 2 * math.pi * k / 14
        c.circle(w / 2 + w * 0.36 * math.cos(a), h / 2 + h * 0.3 * math.sin(a), min(w, h) * 0.16, fill=(255, 255, 255), outline=OL, width=6)
    c.ellipse((w * 0.12, h * 0.16, w * 0.88, h * 0.84), fill=(255, 255, 255), outline=None, width=0)
    im = c.result()
    if icon:
        # cloche + plate (restaurant hint)
        ic = SS(220, 170, 3)
        ic.ellipse((10, 120, 210, 160), fill=(255, 255, 255), outline=OL, width=5)
        ic.pieslice((34, 30, 186, 190), 180, 360, fill=STEEL, outline=OL, width=6)
        ic.line([(26, 110), (194, 110)], fill=OL, width=6)
        ic.circle(110, 26, 12, fill=STEEL, outline=OL, width=5)
        ic.arc((60, 52, 120, 112), 200, 260, fill=(255, 255, 255), width=6)
        ii = ic.result()
        im.alpha_composite(ii, (int(w / 2 - ii.width / 2), int(h / 2 - ii.height / 2 - 6)))
    return im

def lilac_cloud(r=70, seed=0):
    rnd = random.Random(seed)
    c = SS(r * 3, r * 2.2, 3)
    for k in range(5):
        x = r * 0.7 + k * r * 0.4; y = r * 1.1 + rnd.uniform(-0.25, 0.25) * r
        c.circle(x, y, r * rnd.uniform(0.45, 0.65), fill=DREAM, outline=wshade(DREAM, 0.78), width=4)
    for k in range(5):
        x = r * 0.7 + k * r * 0.4; y = r * 1.1
        c.circle(x - r * 0.08, y - r * 0.1, r * 0.35, fill=(226, 210, 252), outline=None, width=0)
    return c.result()

def phone_screen_bubble(w=420, h=560, pulse=0.0):
    c = SS(w, h + 60, 3)
    c.rect((8, 8, w - 8, h), fill=(255, 255, 255), outline=OL, width=8, r=46)
    c.poly([(60, h - 10), (30, h + 52), (130, h - 10)], fill=(255, 255, 255), outline=None, width=0)
    c.line([(60, h - 6), (30, h + 52), (130, h - 4)], fill=OL, width=8)
    # mini chat UI
    c.rect((36, 36, w - 36, 120), fill=(236, 240, 246), outline=None, width=0, r=24)
    c.circle(84, 78, 28, fill=(120, 120, 130), outline=OL, width=4)
    c.line([(130, 66), (300, 66)], fill=(180, 186, 196), width=14)
    c.line([(130, 94), (240, 94)], fill=(200, 206, 214), width=10)
    c.rect((60, 160, w - 120, 230), fill=(220, 236, 255), outline=None, width=0, r=22)
    c.rect((120, 250, w - 50, 320), fill=(255, 238, 200), outline=None, width=0, r=22)
    # send button (pulses)
    r = 78 * (1 + 0.08 * pulse)
    cx, cy = w / 2, h - 125
    c.circle(cx, cy, r + 14 * pulse, fill=(66, 135, 245, int(70 * pulse)), outline=None, width=0)
    c.circle(cx, cy, r, fill=(66, 135, 245), outline=OL, width=6)
    s = r * 0.55
    c.poly([(cx - s * 0.8, cy - s * 0.75), (cx + s * 0.95, cy), (cx - s * 0.8, cy + s * 0.75), (cx - s * 0.45, cy)], fill=(255, 255, 255), outline=OL, width=4)
    return c.result()

def paper_plane(s=150):
    c = SS(s * 1.3, s, 3)
    a = (s * 0.05, s * 0.45); b = (s * 1.25, s * 0.1); d = (s * 0.5, s * 0.92); e = (s * 0.42, s * 0.55)
    c.poly([a, b, e], fill=(255, 255, 255), outline=OL, width=5)
    c.poly([e, b, d], fill=(226, 232, 240), outline=OL, width=5)
    c.poly([e, b, (s * 0.55, s * 0.62)], fill=(200, 208, 220), outline=OL, width=4)
    return c.result()
