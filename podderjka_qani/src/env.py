# Palettes and flat-silhouette environment primitives (layers, trees, houses, grass, birds, dust, text on objects).
import math, random, functools
from common import *

def P_(d): return {k: (hx(v) if isinstance(v, str) else v) for k, v in d.items()}

KUNDUZ = P_(dict(sky0="E4ECEA", sky1="F2F0E6", sun0="F3D9A0", sun1="EED29A", L1="C8D3C4", L2="A9B9A6", L3="869A86", L4="5D7060", L5="39473C",
                 win="5D7060", star="E4ECEA"))
SHOM = P_(dict(sky0="E9DEC6", sky1="F4EDDF", sun0="F2A55C", sun1="E1742F", L1="C6CEC9", L2="AEBBB8", L3="8C9FA1", L4="56696D", L5="2E3C40",
               win="56696D", star="E9DEC6"))
TUN = P_(dict(sky0="1F2A3A", sky1="3A4A5C", sun0="EDE6D2", sun1="E4DCC6", L1="4A5A6E", L2="36455A", L3="283547", L4="1A2433", L5="10171F",
              win="E7A05C", star="EDE6D2"))
CHOL = P_(dict(sky0="F1E2C6", sky1="F7EEDD", sun0="F0B866", sun1="EAAE5C", L1="E6CDA3", L2="D3B07F", L3="B48C62", L4="86654A", L5="5A4333",
               win="86654A", star="F1E2C6"))
CREAM_N = hx("F4EDDF"); NOTE = hx("EFE7D2"); NOTE_D = hx("D9CFB6")

def plerp(A, B, t):
    return {k: lerpc(A[k], B[k], t) for k in A}

# ---------------------------------------------------------------- small helpers
def sway_x(t, k=1.0, ph=0.0, f=0.55):
    return k * (math.sin(2 * math.pi * f * t + ph) + 0.35 * math.sin(2 * math.pi * f * 2.3 * t + ph * 1.7))

def ridge_pts(x0, x1, base, amp, seed, step=24, wl=(520, 230, 95), w=(0.6, 0.3, 0.1)):
    rnd = random.Random(seed); ph = [rnd.uniform(0, 6.28) for _ in wl]
    pts = []
    x = x0
    while x <= x1 + step:
        v = sum(wi * math.sin(2 * math.pi * x / L + p) for wi, L, p in zip(w, wl, ph))
        pts.append((x, base - amp * (0.5 + 0.5 * v)))
        x += step
    return pts

def ridge(cv, base, amp, col, seed, x0=-1800, x1=2900, bottom=3200, **kw):
    pts = ridge_pts(x0, x1, base, amp, seed, **kw)
    cv.poly(pts + [(x1 + 30, bottom), (x0, bottom)], col)
    return pts

def mountains(cv, base, amp, col, seed, x0=-1800, x1=2900, bottom=3200, sharp=1.0):
    """jagged far range: triangle peaks with soft shoulders"""
    rnd = random.Random(seed)
    pts = [(x0, base)]
    x = x0
    while x < x1:
        w = rnd.uniform(160, 340); h = amp * rnd.uniform(0.35, 1.0)
        pts += [(x + w * 0.42, base - h * 0.78), (x + w * 0.5, base - h), (x + w * 0.62, base - h * 0.74), (x + w, base - rnd.uniform(0, 0.25) * amp)]
        x += w
    cv.poly(pts + [(x1 + 30, bottom), (x0, bottom)], col)

def ground(cv, y, col, x0=-1800, x1=2900, bottom=3200):
    cv.rect(x0, y, x1, bottom, col)

def poplar(cv, x, base, h, w, col, sway=0.0):
    """terak: tall narrow lens canopy on a short trunk"""
    cv.rect(x - w * 0.07, base - h * 0.2, x + w * 0.07, base, col)
    pts = []
    for i in range(25):
        a = i / 24
        y = base - h * 0.12 - a * h * 0.88
        bulge = math.sin(math.pi * min(1, a * 1.05)) ** 0.8
        pts.append((x + w * 0.5 * bulge + sway * a * a, y))
    for i in range(24, -1, -1):
        a = i / 24
        y = base - h * 0.12 - a * h * 0.88
        bulge = math.sin(math.pi * min(1, a * 1.05)) ** 0.8
        pts.append((x - w * 0.5 * bulge + sway * a * a, y))
    cv.poly(pts, col)

def round_tree(cv, x, base, h, r, col, sway=0.0, seed=1, trunk_w=None, lumps=9):
    """tut / broad tree: lumpy canopy of overlapping discs on a forked trunk"""
    rnd = random.Random(seed)
    tw = trunk_w or r * 0.16
    cy = base - h + r * 0.75
    cv.poly([(x - tw, base), (x - tw * 0.6, cy + r * 0.2), (x + tw * 0.6, cy + r * 0.2), (x + tw, base)], col)
    cv.line([(x, cy + r * 0.5), (x - r * 0.45 + sway * 0.4, cy - r * 0.05)], col, tw * 0.9)
    cv.line([(x, cy + r * 0.45), (x + r * 0.5 + sway * 0.4, cy - r * 0.1)], col, tw * 0.8)
    for k in range(lumps):
        a = 2 * math.pi * k / lumps + rnd.uniform(-0.3, 0.3)
        rr = r * rnd.uniform(0.45, 0.62)
        d = r * rnd.uniform(0.42, 0.6)
        px = x + d * math.cos(a) * 1.25 + sway * (0.6 + 0.4 * math.sin(a))
        py = cy + d * math.sin(a) * 0.72
        cv.circle(px, py, rr, col)
    cv.circle(x + sway, cy, r * 0.72, col)

def bush(cv, x, base, w, h, col, sway=0.0, seed=3):
    rnd = random.Random(seed)
    for k in range(6):
        px = x + (k / 5 - 0.5) * w * 0.8 + sway * 0.5
        rr = h * rnd.uniform(0.45, 0.6)
        cv.circle(px, base - rr * 0.8, rr, col)
    cv.rect(x - w * 0.5, base - h * 0.3, x + w * 0.5, base + 2, col)

def saxaul(cv, x, base, k, col, t=0.0):
    sw = 3 * k * math.sin(t * 2.2)
    cv.poly([(x - 6 * k, base), (x - 2 * k, base - 40 * k), (x + 3 * k, base - 40 * k), (x + 7 * k, base)], col)
    for a, L in ((-60, 70), (-25, 85), (10, 80), (45, 65), (-95, 50), (80, 48)):
        r = math.radians(a - 90)
        p0 = (x, base - 30 * k)
        p1 = (x + L * k * math.cos(r) + sw, base - 30 * k + L * k * math.sin(r))
        cv.line([p0, p1], col, 4 * k)
        for j in range(5):
            q = (lerp(p0[0], p1[0], 0.4 + 0.15 * j), lerp(p0[1], p1[1], 0.4 + 0.15 * j))
            cv.circle(q[0] + sw * 0.5, q[1], (9 - j) * k, col)

def grass(cv, x0, x1, base, col, t, h=28.0, n=120, seed=5, wind=1.0, w=5.0, gust=0.0):
    rnd = random.Random(seed)
    for i in range(n):
        x = x0 + (x1 - x0) * (i + rnd.random()) / n
        hh = h * rnd.uniform(0.55, 1.15)
        ph = rnd.uniform(0, 6.28)
        bend = wind * (6 + 6 * math.sin(2 * math.pi * 0.7 * t + x * 0.01 + ph * 0.3)) * hh / 28 + gust * hh * 0.6
        ww = w * rnd.uniform(0.7, 1.2)
        cv.poly([(x - ww / 2, base + 2), (x + bend, base - hh), (x + ww / 2, base + 2)], col)

def reeds(cv, x0, x1, base, col, t, h=150.0, n=14, seed=8):
    rnd = random.Random(seed)
    for i in range(n):
        x = x0 + (x1 - x0) * (i + rnd.random() * 0.6) / n
        hh = h * rnd.uniform(0.6, 1.1)
        sw = 10 * math.sin(2 * math.pi * 0.45 * t + i * 0.9) * hh / h
        top = (x + sw, base - hh)
        mid = (x + sw * 0.35, base - hh * 0.5)
        cv.line([(x, base), mid, top], col, 3.0)
        if rnd.random() < 0.6:
            cv.capsule((top[0] + sw * 0.05, top[1] + 4), (top[0] + sw * 0.12, top[1] + 30), 4.5, 4.5, col)
        lf = rnd.choice((-1, 1))
        cv.poly([(x + sw * 0.2, base - hh * 0.3), (x + lf * 38 + sw * 0.7, base - hh * 0.55), (x + sw * 0.25, base - hh * 0.36)], col)

def house(cv, x0, x1, top, gnd, col, beam=None, wins=(), win_col=None, door=None, parapet=True):
    cv.rect(x0, top, x1, gnd + 2, col)
    if parapet: cv.rect(x0 - 6, top - 10, x1 + 6, top + 4, col)
    if beam is not None:
        for bx in range(int(x0) + 14, int(x1) - 6, 30):
            cv.rect(bx, top + 4, bx + 10, top + 12, beam)
    for (wx, wy, ww, wh) in wins:
        cv.rect(wx, wy, wx + ww, wy + wh, win_col or beam or col, r=2)
        cv.line([(wx + ww / 2, wy), (wx + ww / 2, wy + wh)], col, 2.2, caps=False)
    if door:
        dx, dw, dh, dcol = door
        cv.rect(dx, gnd - dh, dx + dw, gnd, dcol)

def darvoza(cv, cx, w, h, gnd, frame_col, leaf_col, stud_col, open_=0.0):
    """wooden gate: heavy frame, two leaves with diamond studs, little roof"""
    x0, x1 = cx - w / 2, cx + w / 2
    cv.rect(x0 - 14, gnd - h - 16, x1 + 14, gnd, frame_col)
    cv.rect(x0 - 26, gnd - h - 30, x1 + 26, gnd - h - 14, frame_col)
    cv.rect(x0, gnd - h, x1, gnd, leaf_col)
    cv.line([(cx, gnd - h), (cx, gnd)], frame_col, 3, caps=False)
    for j in range(4):
        yy = gnd - h * (0.18 + 0.22 * j)
        for xx in (x0 + w * 0.25, x1 - w * 0.25):
            cv.poly([(xx, yy - 7), (xx + 6, yy), (xx, yy + 7), (xx - 6, yy)], stud_col)

def cloud(cv, x, y, w, col, seed=2):
    rnd = random.Random(seed)
    h = w * 0.28
    cv.rect(x - w / 2, y - h * 0.35, x + w / 2, y + h * 0.15, col, r=h * 0.25)
    for k in range(5):
        px = x - w * 0.36 + k * w * 0.18
        rr = h * rnd.uniform(0.45, 0.8)
        cv.circle(px, y - rr * 0.35, rr, col)

# ---------------------------------------------------------------- birds
def bird_fly(cv, x, y, sc, flap, col, dir=1):
    span = 26 * sc; tip = -7 * sc * flap
    pts = [(x - span, y + tip - 2 * sc), (x - span * 0.45, y - 6 * sc - 2 * sc * flap), (x, y),
           (x + span * 0.45, y - 6 * sc - 2 * sc * flap), (x + span, y + tip - 2 * sc)]
    cv.line(pts, col, 3.4 * sc)

def bird_perch(cv, x, y, sc, col, dir=1, peck=0.0, kind="sparrow"):
    """small perched bird, y = feet level"""
    d = dir
    if kind == "crow": sc *= 1.6
    body = ellipse_pts(x, y - 9 * sc, 10 * sc, 7.5 * sc, 16, ang=-12 * d)
    cv.poly(body, col)
    hx_, hy_ = x + d * 8 * sc, y - 16 * sc + peck * 7 * sc
    cv.circle(hx_, hy_, 5.2 * sc, col)
    cv.poly([(hx_ + d * 4 * sc, hy_ - 2 * sc), (hx_ + d * (10 + 3 * (kind == "crow")) * sc, hy_ + 0.5 * sc), (hx_ + d * 4 * sc, hy_ + 2.2 * sc)], col)
    cv.poly([(x - d * 7 * sc, y - 11 * sc), (x - d * 20 * sc, y - 15 * sc), (x - d * 19 * sc, y - 9 * sc), (x - d * 6 * sc, y - 6 * sc)], col)
    cv.line([(x - 1.5 * sc, y - 3 * sc), (x - 2 * sc, y)], col, 1.4 * sc)
    cv.line([(x + 2 * sc, y - 3 * sc), (x + 2.5 * sc, y)], col, 1.4 * sc)

def flock(cv, t, items, col, flap_f=4.0):
    for (x, y, sc, ph) in items:
        bird_fly(cv, x, y, sc, math.sin(2 * math.pi * flap_f * t + ph), col)

# ---------------------------------------------------------------- particles
def dust(cv, t, n, region, col, seed=4, wind=(140, -10), size=(2, 6), alpha=170, life=2.2):
    x0, y0, x1, y1 = region
    rnd = random.Random(seed)
    for i in range(n):
        ph = rnd.random(); sx = rnd.uniform(x0, x1); sy = rnd.uniform(y0, y1)
        u = (t / life + ph) % 1.0
        x = sx + wind[0] * u * life + 20 * math.sin(6 * u + i)
        y = sy + wind[1] * u * life + 10 * math.sin(4 * u + i * 1.3)
        a = int(alpha * math.sin(math.pi * u))
        r = rnd.uniform(*size)
        cv.circle(x, y, r, col + (a,))

def dust_puff(cv, x, y, u, col, k=1.0, n=7, seed=1, alpha=200):
    """expanding ground puff, u in 0..1"""
    if u <= 0 or u >= 1: return
    rnd = random.Random(seed)
    a = int(alpha * (1 - u) ** 1.4)
    for i in range(n):
        ang = math.pi * (0.05 + 0.9 * i / max(1, n - 1))
        d = (20 + 90 * u ** 0.6) * k * rnd.uniform(0.7, 1.2)
        r = (10 + 26 * u ** 0.5) * k * rnd.uniform(0.7, 1.2)
        cv.circle(x - math.cos(ang) * d * 1.4, y - math.sin(ang) * d * 0.45, r, col + (a,))

def leaves(cv, t, n, region, col, seed=7, wind=(-60, 70), size=7.0, life=3.0):
    x0, y0, x1, y1 = region
    rnd = random.Random(seed)
    for i in range(n):
        ph = rnd.random(); sx = rnd.uniform(x0, x1); sy = rnd.uniform(y0, y1)
        u = (t / life + ph) % 1.0
        x = sx + wind[0] * u * life + 30 * math.sin(5 * u * life + i)
        y = sy + wind[1] * u * life
        ang = 200 * u * life + i * 40
        s = size * rnd.uniform(0.7, 1.2)
        a = int(255 * min(1, 4 * math.sin(math.pi * u)))
        cv.poly(ellipse_pts(x, y, s, s * 0.45, 8, ang=ang), col + (a,))

def ring(cv, x, y, rx, ry, col, width, alpha):
    if alpha <= 2 or rx <= 0.5: return
    a0 = cv.T(x - rx, y - ry); a1 = cv.T(x + rx, y + ry)
    cv.d.ellipse((a0[0], a0[1], a1[0], a1[1]), outline=tuple(col[:3]) + (int(alpha),), width=max(1, int(cv.S(width))))

def dashed(cv, pts, col, w, dash=14, gap=10, closed=True):
    P = pts + ([pts[0]] if closed else [])
    acc = 0.0; on = True; cur = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1]); pos = 0.0
        while pos < L:
            lim = (dash if on else gap) - acc
            step = min(lim, L - pos)
            pos += step; acc += step
            q = (a[0] + (b[0] - a[0]) * pos / L, a[1] + (b[1] - a[1]) * pos / L)
            if on: cur.append(q)
            if acc >= (dash if on else gap) - 1e-6:
                if on and len(cur) > 1: cv.line(cur, col, w)
                on = not on; acc = 0.0; cur = [q]
    if on and len(cur) > 1: cv.line(cur, col, w)

# ---------------------------------------------------------------- text painted on objects (world space)
@functools.lru_cache(maxsize=256)
def _text_img(text, px, col, path, track):
    f = font(path, max(4, px))
    asc, desc = f.getmetrics()
    w = int(f.getlength(text) + track * px * max(0, len(text) - 1)) + 8
    im = Image.new("RGBA", (w, asc + desc + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if track:
        x = 4
        for ch in text:
            d.text((x, 4), ch, font=f, fill=col); x += f.getlength(ch) + track * px
    else:
        d.text((4, 4), text, font=f, fill=col)
    bb = im.getbbox()
    return im.crop(bb) if bb else im

def wtext(cv, text, cx, cy, size, col, path=FONT_BLACK, ang=0.0, alpha=1.0, scale=1.0, track=0.0, maxw=None):
    px = int(round(size * cv.ez * cv.ss * scale))
    if px < 4: return
    col = tuple(col[:3]) + (255,)
    im = _text_img(text, px, col, path, track)
    if maxw:
        mw = maxw * cv.ez * cv.ss * scale
        if im.width > mw:
            im = im.resize((int(mw), max(1, int(im.height * mw / im.width))), Image.LANCZOS)
    if ang: im = im.rotate(ang, resample=Image.BICUBIC, expand=True)
    if alpha < 0.999:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    sx, sy = cv.T(cx, cy)
    cv.paste_rgba(im, sx - im.width / 2, sy - im.height / 2)

def heart_pts(cx, cy, r, n=40):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x = 16 * math.sin(a) ** 3
        y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((cx + x * r / 16, cy + y * r / 16))
    return pts
