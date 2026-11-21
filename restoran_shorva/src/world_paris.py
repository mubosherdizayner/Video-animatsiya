# 18th-century Paris street at dusk: far hazy hill with rooftops + dome (crowd on the ridge),
# mid row of mansard facades with a palace gate, near storefronts with glowing windows, lamps.
import math, random
from common import *
from people import person, seated
from world_pool import sky, birds

P_FAR, P_MID, P_SUN = 0.25, 0.55, 0.12
MID_BASE = 1520.0
NEAR_BASE = 1600.0

def ridge_y(x): return 905 + 12 * math.sin(x / 260.0) + 6 * math.sin(x / 97.0 + 1)

def _far(cv, st):
    cv.layer(P_FAR)
    xs = list(range(-1400, 3400, 40))
    cv.poly([(x, ridge_y(x)) for x in xs] + [(3400, 1700), (-1400, 1700)], MTN1)
    # crowd marching on the ridge (left -> right)
    ca = st.get("crowd", 0.0)
    if ca > 0.01:
        tt = st.get("crowd_t", 0.0)
        rnd = random.Random(5)
        for k in range(30):
            bx = -260 + k * 34 + rnd.uniform(-8, 8) + 38 * tt
            h = rnd.uniform(40, 50)
            ph = tt * 7 + k * 1.3
            fl = None
            if k % 5 == 1: fl = (CITY, tt * 6 + k, "flag")
            elif k % 7 == 3: fl = (CITY, tt * 5 + k, "banner")
            person(cv, bx, ridge_y(bx) + 2, h, CITY, walk=1.0, phase=ph, face=1, hat="tricorn" if k % 3 == 0 else None,
                   flag=fl, alpha=int(255 * ca))
    # far rooftops band with chimneys + dome
    rnd = random.Random(8)
    x = -1400
    while x < 3400:
        w = rnd.uniform(70, 150); top = rnd.uniform(958, 1010)
        cv.rect(x, top, x + w + 1, 1700, MTN2)
        cv.poly([(x - 4, top + 2), (x + w + 4, top + 2), (x + w - 10, top - 20), (x + 10, top - 20)], MTN2)
        for c in range(rnd.randint(1, 3)):
            cxp = x + rnd.uniform(14, w - 14)
            cv.rect(cxp, top - 20 - rnd.uniform(10, 22), cxp + 7, top - 15, MTN2)
        x += w
    dx = 1580
    cv.rect(dx - 70, 930, dx + 70, 1060, MTN2)
    cv.poly(ellipse_pts(dx, 932, 66, 70, 30, 180, 360), MTN2)
    cv.rect(dx - 9, 846, dx + 9, 868, MTN2)
    cv.poly([(dx - 4, 846), (dx + 4, 846), (dx, 826)], MTN2)
    cv.rect(dx - 110, 990, dx + 110, 1060, MTN2)

BUILD_MID = None
def _mid_buildings():
    global BUILD_MID
    if BUILD_MID is None:
        rnd = random.Random(31); out = []; x = -900
        while x < 3400:
            w = rnd.uniform(220, 300)
            if 1040 < x + w / 2 < 1480:   # courtyard in front of the palace gate
                x = 1480; continue
            out.append((x, w, rnd.uniform(990, 1035), rnd.choice((CITY, hx("889B9D"), hx("90A3A5")))))
            x += w + rnd.uniform(0, 6)
        BUILD_MID = out
    return BUILD_MID

def _mid(cv, st):
    cv.layer(P_MID)
    for (x, w, top, col) in _mid_buildings():
        eave = top + 66
        cv.rect(x, eave, x + w, MID_BASE + 2, col)
        cv.poly([(x - 6, eave), (x + w + 6, eave), (x + w - 14, top), (x + 14, top)], CITY_D)
        cv.rect(x - 8, eave - 2, x + w + 8, eave + 7, CITY_D)
        nd = int((w - 40) // 58)
        for j in range(nd):
            dxp = x + 34 + j * ((w - 68) / max(1, nd - 1)) if nd > 1 else x + w / 2
            cv.rect(dxp - 9, top + 24, dxp + 9, eave - 6, col)
            cv.poly(ellipse_pts(dxp, top + 24, 9, 9, 10, 180, 360), col)
            cv.rect(dxp - 5, top + 28, dxp + 5, eave - 10, CITY_D)
        cv.rect(x + w * 0.2, top - 26, x + w * 0.2 + 16, top + 4, CITY_D)
        cv.rect(x + w * 0.75, top - 20, x + w * 0.75 + 14, top + 4, CITY_D)
        ncol = int((w - 30) // 46)
        for r in range(5):
            wy = eave + 34 + r * 78
            if wy + 44 > MID_BASE - 30: break
            for cidx in range(ncol):
                wx = x + 22 + cidx * ((w - 44) / max(1, ncol - 1)) if ncol > 1 else x + w / 2
                cv.rect(wx - 9, wy, wx + 9, wy + 44, CITY_D)
        cv.line([(x, eave + 12), (x, MID_BASE)], CITY_D, 2, caps=False)
    # palace gate (ornate silhouette)
    g = GATE; gx = 1260.0
    for px in (gx - 112, gx + 112):
        cv.rect(px - 16, 1255, px + 16, MID_BASE + 2, g)
        cv.rect(px - 21, 1245, px + 21, 1258, g)
        cv.poly(ellipse_pts(px, 1232, 11, 13, 12), g)
        cv.rect(px - 7, 1240, px + 7, 1247, g)
        cv.poly([(px - 3, 1220), (px + 3, 1220), (px, 1206)], g)
    for bx in range(int(gx - 92), int(gx + 96), 13):
        topy = 1300 - 46 * math.cos((bx - gx) / 96 * math.pi / 2)
        cv.line([(bx, topy), (bx, MID_BASE)], g, 3.2, caps=False)
        cv.poly([(bx - 3, topy + 2), (bx + 3, topy + 2), (bx, topy - 9)], g)
    cv.line([(gx - 96, 1335), (gx + 96, 1335)], g, 4, caps=False)
    cv.line([(gx - 96, 1470), (gx + 96, 1470)], g, 4, caps=False)
    cv.poly(ellipse_pts(gx, 1232, 22, 16, 16), g)
    cv.poly([(gx - 30, 1238), (gx + 30, 1238), (gx + 20, 1252), (gx - 20, 1252)], g)
    for sx in (-1, 1):
        wx0 = gx + sx * 128
        cv.rect(min(wx0, wx0 + sx * 110), 1430, max(wx0, wx0 + sx * 110), MID_BASE + 2, g)
        for k in range(9):
            xx = wx0 + sx * (6 + k * 12)
            cv.line([(xx, 1395), (xx, 1432)], g, 2.4, caps=False)
        cv.line([(wx0, 1397), (wx0 + sx * 110, 1397)], g, 2.4, caps=False)
    # mid street (seen through gaps)
    cv.rect(-1400, MID_BASE, 3600, 2300, hx("6F8386"))

# ---------------------------------------------------------------- near layer
NEAR = {
    "A": dict(x0=-300, x1=760, top=1150, win=(140, 1300, 560, 1560), door=(600, 1385, 690, 1600), fascia=(140, 1244, 700, 1284)),
    "B": dict(x0=960, x1=1520, top=1170, win=(1010, 1385, 1200, 1560), win2=(1370, 1385, 1490, 1560), door=(1240, 1385, 1330, 1600),
              fascia=(1172, 1292, 1398, 1346)),
    "C": dict(x0=2080, x1=2700, top=1160, win=(2340, 1385, 2600, 1560), door=(2200, 1385, 2290, 1600), fascia=(2165, 1300, 2325, 1346)),
}

def _window(cv, box, lit, panes=3, inner=None):
    x0, y0, x1, y1 = box
    cv.rect(x0 - 8, y0 - 8, x1 + 8, y1 + 6, GATE)
    cv.rect(x0, y0, x1, y1, lerpc(hx("3E4F53"), WIN, lit))
    if inner: inner()
    for k in range(1, panes):
        xx = x0 + (x1 - x0) * k / panes
        cv.rect(xx - 3, y0, xx + 3, y1, HOUSE)
    ty = y0 + (y1 - y0) * 0.2
    cv.rect(x0, ty - 2.5, x1, ty + 2.5, HOUSE)

def plaque(cv, cx, cy, alpha, w=128, h=30, size=19):
    if alpha <= 0.01: return
    a = int(255 * alpha)
    cv.rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, hx("E8E1D3") + (a,), r=3)
    _sign_text(cv, "RESTAURANT", cx, cy, size, INK, alpha)

_txt_cache = {}
def _sign_text(cv, text, cx, cy, size, col, alpha, font_path=None):
    px = cv.S(size)
    key = (text, int(px), col, font_path)
    if key not in _txt_cache:
        if len(_txt_cache) > 60: _txt_cache.clear()
        _txt_cache[key] = text_runs([(text, col)], px, font_path or FONT_BLACK, tracking=px * 0.06)
    im = _txt_cache[key]
    if alpha < 0.999:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    sx, sy = cv.T(cx, cy)
    cv.paste_rgba(im, sx - im.width / 2, sy - im.height / 2 - px * 0.08)

def _bowl_icon(cv, cx, cy, k, col, steam_t=0.0):
    cv.poly([(cx - 22 * k, cy - 4 * k)] + ellipse_pts(cx, cy - 4 * k, 22 * k, 16 * k, 16, 0, 180) + [(cx + 22 * k, cy - 4 * k)], col)
    cv.rect(cx - 9 * k, cy + 11 * k, cx + 9 * k, cy + 15 * k, col)
    for j, dx in enumerate((-9, 0, 9)):
        pts = [(cx + dx * k + 3 * k * math.sin(u * 3 + steam_t * 4 + j), cy - 10 * k - u * 22 * k) for u in [i / 8 for i in range(9)]]
        cv.line(pts, col, 2.6 * k)

def _near(cv, st):
    cv.layer(1.0)
    lit = st.get("lit", {})
    # street (near)
    cv.rect(-1400, NEAR_BASE, 3600, NEAR_BASE + 46, hx("3B4B50"))
    cv.rect(-1400, NEAR_BASE + 46, 3600, 2300, BANK)
    for r in range(7):
        y = NEAR_BASE + 64 + r * r * 9 + r * 26
        off = (r % 2) * 30
        for x in range(-1400 + off, 3600, 60):
            cv.line([(x, y), (x + 44, y)], NEAR1, 2.0 + r * 0.25, caps=False)
    for key in ("A", "B", "C"):
        b = NEAR[key]
        cv.rect(b["x0"], b["top"], b["x1"], NEAR_BASE + 2, HOUSE)
        cv.rect(b["x0"] - 10, b["top"] - 6, b["x1"] + 10, b["top"] + 20, GATE)
        for wx in range(int(b["x0"]) + 40, int(b["x1"]) - 30, 90):
            cv.rect(wx, b["top"] + 40, wx + 34, b["top"] + 92, GATE)
        fx0, fy0, fx1, fy1 = b["fascia"]
        cv.rect(fx0, fy0, fx1, fy1, GATE)
    # A: big window with cafe customers
    A = NEAR["A"]
    def sippers():
        if st.get("sippers") is None: return
        hun, sips = st["sippers"]
        for k, sx in enumerate((205, 335, 465)):
            seated(cv, sx, 1560, 150, NEAR2, hunch=hun, sip=sips[k], face=1 if k != 1 else -1)
    _window(cv, A["win"], lit.get("A", 0.0), panes=3, inner=sippers)
    dx0, dy0, dx1, dy1 = A["door"]
    cv.rect(dx0 - 6, dy0 - 40, dx1 + 6, dy1, GATE)
    cv.rect(dx0 + 6, dy0 - 32, dx1 - 6, dy0 - 8, lerpc(hx("3E4F53"), WIN, lit.get("A_door", 0.0)))
    cv.rect(dx0 + 4, dy0, dx1 - 4, dy1, hx("3B4B50"))
    # B: restaurant door (scene 11-13)
    B = NEAR["B"]
    def hand_bowl():
        hb = st.get("hand_bowl")
        if hb is None: return
        lift, steam_t = hb
        bx, by = 1105, 1528 - 70 * ease_io(lift)
        cv.capsule((1178, 1556), (bx + 30, by + 26), 9, 9, NEAR2)
        cv.capsule((bx + 30, by + 26), (bx + 6, by + 10), 9, 8, NEAR2)
        cv.poly([(bx - 26, by - 4)] + ellipse_pts(bx, by - 4, 26, 19, 16, 0, 180) + [(bx + 26, by - 4)], BOWL)
        cv.rect(bx - 10, by + 13, bx + 10, by + 17, BOWL)
        cv.poly(ellipse_pts(bx, by - 4, 26, 5, 20), BOWL)
        cv.poly(ellipse_pts(bx, by - 3.5, 22, 3.4, 20), (201, 176, 132))
        cv.rect(bx - 24, by + 2, bx + 24, by + 6, BOWL_BAND)
    _window(cv, B["win"], lit.get("B", 0.0), panes=2, inner=hand_bowl)
    _window(cv, B["win2"], lit.get("B2", 0.0), panes=2)
    dx0, dy0, dx1, dy1 = B["door"]
    cv.rect(dx0 - 8, dy0 - 10, dx1 + 8, dy1, GATE)
    op = st.get("doorB", 0.0)
    cv.rect(dx0, dy0, dx1, dy1, lerpc(hx("2B383C"), WIN, 0.75 * op))
    cv.rect(dx0, dy0, dx0 + (dx1 - dx0) * (1 - 0.8 * op), dy1, hx("3B4B50"))
    cv.circle(dx0 + (dx1 - dx0) * (1 - 0.8 * op) - 10, 1495, 3, GATE)
    # blade sign with steaming bowl icon
    cv.line([(1172, 1226), (1240, 1226)], NEAR1, 4, caps=False)
    cv.line([(1176, 1226), (1176, 1236)], NEAR1, 2, caps=False)
    cv.line([(1226, 1226), (1226, 1236)], NEAR1, 2, caps=False)
    sw = 2.0 * math.sin(st.get("t", 0) * 1.7)
    cv.poly([(1164 + sw, 1236), (1238 + sw, 1236), (1238 - sw * 0.3, 1288), (1164 - sw * 0.3, 1288)], hx("E8E1D3"))
    _bowl_icon(cv, 1201, 1268, 0.85, GATE, st.get("t", 0))
    # fascia text on B (scene 13)
    fx0, fy0, fx1, fy1 = B["fascia"]
    fg = st.get("fasciaB_glow", 0.0)
    if fg > 0.01:
        cv.rect(fx0, fy0, fx1, fy1, WIN + (int(255 * fg),))
    if st.get("fasciaB_text", 0.0) > 0.01:
        _sign_text(cv, "RESTAURANT", (fx0 + fx1) / 2, (fy0 + fy1) / 2, 30, lerpc(CREAM, INK, fg), st["fasciaB_text"])
    # C: chef door + window
    C = NEAR["C"]
    _window(cv, C["win"], lit.get("C", 0.0), panes=3)
    dx0, dy0, dx1, dy1 = C["door"]
    cv.rect(dx0 - 8, dy0 - 10, dx1 + 8, dy1, GATE)
    op = st.get("doorC", 0.0)
    cv.rect(dx0, dy0, dx1, dy1, lerpc(hx("2B383C"), WIN, 0.6 * op))
    cv.rect(dx0, dy0, dx0 + (dx1 - dx0) * (1 - 0.8 * op), dy1, hx("3B4B50"))
    # plaques (scene 9)
    pa = st.get("plaques", 0.0)
    plaque(cv, 645, 1316, clamp01(pa * 2))
    plaque(cv, 2245, 1323, clamp01(pa * 2 - 1))
    # lamps
    for lx in (840, 1590, 2010, -120):
        cv.rect(lx - 5, 1300, lx + 5, NEAR_BASE + 58, NEAR1)
        cv.rect(lx - 12, NEAR_BASE + 46, lx + 12, NEAR_BASE + 60, NEAR1)
        cv.poly([(lx - 18, 1262), (lx + 18, 1262), (lx + 12, 1300), (lx - 12, 1300)], NEAR1)
        cv.poly([(lx - 12, 1268), (lx + 12, 1268), (lx + 8, 1294), (lx - 8, 1294)], lerpc(hx("3E4F53"), WIN, st.get("lamps", 1.0)))
        cv.poly([(lx - 22, 1264), (lx + 22, 1264), (lx, 1244)], NEAR1)

def draw_paris(cv, st):
    cam = st["cam"]; cv.set_cam(*cam)
    cv.layer(1.0)
    sky(cv, warm=st.get("warm", 0.0))
    cv.layer(P_SUN)
    draw_sun(cv, 760, st.get("sun_y", 700), 190)
    cv.layer(0.15)
    birds(cv, st.get("t", 0.0), 33.0, items=[(260, 560, 0.8, 0.3), (330, 520, 0.6, 1.1), (900, 600, 0.7, 2.2)], drift=1.0)
    _far(cv, st)
    _mid(cv, st)
    if st.get("mid_extra"): st["mid_extra"](cv)
    _near(cv, st)
    cv.layer(1.0)
    if st.get("post"): st["post"](cv)
    cv.layer(1.0)
