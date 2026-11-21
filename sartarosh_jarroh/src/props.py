# Props drawn as vector shapes.
import math
from gfx import *

LEATHER = hx("8E2430"); LEATHER_D = hx("6E1A24"); CHROME = hx("C9D1D6"); CHROME_D = hx("8E9AA2")


# ---------------------------------------------------------------- barber pole
def _band(ctx, cx, r, yb, c, th0, th1, width, n=18):
    top, bot = [], []
    for i in range(n + 1):
        th = th0 + (th1 - th0) * i / n
        x = cx + r * math.sin(th)
        y = yb + c * th
        top.append((x, y))
        bot.append((x, y + width))
    poly(ctx, top + bot[::-1])


def pole(ctx, cx, y0, y1, R, phase, red_glow=0.0, white_dim=0.0, stripe_a=1.0, wood=0.0,
         wrap=0.0, wrap_phase=0.0, caps=1.0, glass=1.0):
    """helical red/white barber pole. phase in turns (stripes rise as phase grows)."""
    P = 2.6 * R                    # vertical pitch
    c = P / TAU
    red = mix(POLE_R, hx("FF4A5E"), red_glow)
    white = mix(WHITE, hx("B8B4AE"), white_dim)
    base = mix(white, WOOD, wood)
    # --- bandage ribbon, back half
    def ribbon(front):
        if wrap <= 0.001:
            return
        rr = R * (1 + 0.55 * wrap)
        c2 = c * 1.0
        ph = wrap_phase % 1.0
        k0 = int((y0 - y1) / P) - 2
        k1 = int((y1 - y0) / P) + 3
        for k in range(k0, k1 + 1):
            yb = y0 + (k - ph) * P
            if front:
                rng = (-PI / 2, PI / 2)
            else:
                rng = (PI / 2, 3 * PI / 2)
            ctx.save()
            ctx.rectangle(cx - rr - 40, y0 - 10, 2 * rr + 80, y1 - y0 + 20)
            ctx.clip()
            _band(ctx, cx, rr, yb, c2, rng[0], rng[1], P * 0.42)
            col = WHITE if front else hx("D9D4CC")
            fs(ctx, col, 4, alpha=min(1.0, wrap * 2.5))
            ctx.restore()
    ribbon(False)
    # --- cylinder
    body = lambda cc: cc.rectangle(cx - R, y0, 2 * R, y1 - y0)
    body(ctx)
    fill(ctx, base)
    ctx.save()
    body(ctx)
    ctx.clip()
    if stripe_a > 0.001:
        k0 = -2
        k1 = int((y1 - y0) / P) + 3
        for k in range(k0, k1):
            yb = y0 + (k - (phase % 1.0)) * P
            _band(ctx, cx, R, yb, c, -PI / 2, PI / 2, P / 2)
            fill(ctx, red, stripe_a * (1 - wood))
    if wood > 0:
        for k in range(7):
            xx = cx - R + (k + 0.5) * 2 * R / 7
            line(ctx, [(xx, y0), (xx + 4 * math.sin(k), y1)], color=WOOD_D, width=3, alpha=0.6 * wood)
    # cylinder shading
    g = cairo.LinearGradient(cx - R, 0, cx + R, 0)
    g.add_color_stop_rgba(0, 0, 0, 0, 0.30)
    g.add_color_stop_rgba(0.22, 1, 1, 1, 0.38 * glass)
    g.add_color_stop_rgba(0.34, 1, 1, 1, 0.0)
    g.add_color_stop_rgba(0.75, 0, 0, 0, 0.06)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.38)
    ctx.set_source(g)
    body(ctx)
    ctx.fill()
    if red_glow > 0:
        glow(ctx, cx, (y0 + y1) / 2, R * 3, hx("FF3B4E"), 0.25 * red_glow)
    ctx.restore()
    body(ctx)
    stroke_ol(ctx, 6)
    ribbon(True)
    # --- brass caps + ball
    if caps > 0.01:
        def cap(yc, h):
            def pth(cc):
                rrect(cc, cx - R * 1.22, yc - h / 2, R * 2.44, h, h * 0.3)
            cel(ctx, pth, BRASS, mul(BRASS, 0.75), d=(R * 0.5, 0), alpha=caps)
            line(ctx, [(cx - R * 1.0, yc - h * 0.15), (cx - R * 0.4, yc - h * 0.15)], color=WHITE, width=4, alpha=0.5 * caps)
        cap(y0 - R * 0.18, R * 0.42)
        cap(y1 + R * 0.18, R * 0.42)
        rb = R * 0.82
        cel(ctx, lambda cc: ellipse(cc, cx, y0 - R * 0.39 - rb, rb, rb), BRASS, mul(BRASS, 0.72), d=(rb * 0.3, rb * 0.25), alpha=caps)
        ellipse(ctx, cx - rb * 0.35, y0 - R * 0.39 - rb * 1.35, rb * 0.28, rb * 0.18, rot=-0.5)
        fill(ctx, WHITE, 0.7 * caps)


# ---------------------------------------------------------------- tools
def pliers(ctx, s=1.0, open_=0.10, glint=0.0, t=0.0):
    """pivot at origin, jaws toward -y, handles toward +y; total length ~ 330*s"""
    ctx.save()
    ctx.scale(s, s)
    for side in (-1, 1):
        ctx.save()
        ctx.rotate(side * open_)
        tube(ctx, [(0, 8), (side * 14, 100), (side * 30, 200)], 30, STEEL, ol=6)
        tube(ctx, [(side * 6, 30), (side * 22, 190)], 8, WHITE, ol=0, alpha=0.35)
        jp = [(side * 2, 14), (side * 20, -20), (side * 16, -90), (side * 4, -118), (0, -112), (0, 10)]
        poly(ctx, jp)
        fs(ctx, STEEL, 6)
        for k in range(5):
            y = -40 - k * 14
            line(ctx, [(side * 2, y), (side * 12, y - 4)], color=STEEL_D, width=3)
        ctx.restore()
    circle(ctx, 0, 0, 17)
    fs(ctx, STEEL_D, 6)
    circle(ctx, 0, 0, 6)
    fill(ctx, OL)
    if glint > 0:
        line(ctx, [(-14, -100), (-6, -30)], color=WHITE, width=7, alpha=glint)
        sparkle(ctx, -8, -112, 46 * glint + 10, alpha=glint, rot=t * 3)
        glow(ctx, -8, -112, 90, WHITE, 0.5 * glint)
    ctx.restore()


def scissors(ctx, s=1.0, open_=0.2):
    ctx.save()
    ctx.scale(s, s)
    for side in (-1, 1):
        ctx.save()
        ctx.rotate(side * open_)
        poly(ctx, [(side * 3, 6), (side * 9, -40), (side * 2, -92), (-side * 3, -40)])
        fs(ctx, STEEL, 5)
        tube(ctx, [(0, 6), (side * 10, 34)], 9, STEEL_D, ol=4)
        circle(ctx, side * 16, 50, 16)
        ctx.set_source_rgba(*OL, 1)
        ctx.set_line_width(olw(ctx, 14))
        ctx.stroke_preserve()
        ctx.set_source_rgba(*TEAL, 1)
        ctx.set_line_width(olw(ctx, 7))
        ctx.stroke()
        ctx.restore()
    circle(ctx, 0, 0, 6)
    fs(ctx, STEEL_D, 4)
    ctx.restore()


def tooth(ctx, x, y, s=1.0, rot=0.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(s, s)
    def pth(c):
        c.move_to(-30, -20)
        c.curve_to(-34, -48, -10, -50, 0, -38)
        c.curve_to(10, -50, 34, -48, 30, -20)
        c.curve_to(28, 0, 24, 14, 18, 44)
        c.curve_to(14, 54, 6, 50, 6, 36)
        c.curve_to(4, 20, -4, 20, -6, 36)
        c.curve_to(-6, 50, -14, 54, -18, 44)
        c.curve_to(-24, 14, -28, 0, -30, -20)
        c.close_path()
    cel(ctx, pth, WHITE, hx("DCE3E6"), d=(8, 4))
    ellipse(ctx, -14, -26, 6, 9, rot=0.3)
    fill(ctx, WHITE)
    ctx.restore()


def book(ctx, w=110, h=140, rot=0.0):
    ctx.save()
    ctx.rotate(rot)
    rrect(ctx, -w / 2 + 10, -h / 2 + 8, w, h, 8)
    fs(ctx, hx("EDE3CC"), 5)
    rrect(ctx, -w / 2, -h / 2, w, h, 8)
    fs(ctx, hx("5A3420"), 6)
    rrect(ctx, -w / 2 + 14, -h / 2 + 14, w - 28, h - 28, 6)
    stroke_ol(ctx, 3, color=GOLD)
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        poly(ctx, [(sx * w / 2, sy * h / 2), (sx * (w / 2 - 22), sy * h / 2), (sx * w / 2, sy * (h / 2 - 22))])
        fs(ctx, GOLD, 3)
    ctx.restore()


def bowl(ctx, x, y, s=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(-62, 0)
    ctx.curve_to(-58, 46, 58, 46, 62, 0)
    ctx.close_path()
    cel(ctx, lambda c: (c.move_to(-62, 0), c.curve_to(-58, 46, 58, 46, 62, 0), c.close_path()), BRASS, mul(BRASS, 0.75), d=(14, 0))
    ellipse(ctx, 0, 0, 62, 14)
    fs(ctx, mul(BRASS, 0.85), 5)
    ellipse(ctx, 0, 2, 48, 9)
    fill(ctx, hx("6E1B22"))
    ctx.restore()


def staff(ctx, x, y0, y1, r=26, rot=0.0):
    ctx.save()
    ctx.translate(x, (y0 + y1) / 2)
    ctx.rotate(rot)
    h = y1 - y0
    cel(ctx, lambda c: rrect(c, -r, -h / 2, 2 * r, h, r * 0.8), WOOD, WOOD_D, d=(r * 0.6, 0))
    for k in range(4):
        xx = -r * 0.6 + k * r * 0.4
        line(ctx, [(xx, -h / 2 + 20), (xx + 3, h / 2 - 20)], color=WOOD_D, width=3, alpha=0.7)
    ctx.restore()


def paper_plane(ctx, x, y, s=1.0, rot=0.0, alpha=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(s, s)
    poly(ctx, [(-50, 6), (56, -26), (-8, 34)])
    fs(ctx, hx("DDE6EA"), 5, alpha)
    poly(ctx, [(-50, 6), (56, -26), (-12, 2)])
    fs(ctx, WHITE, 5, alpha)
    poly(ctx, [(-12, 2), (56, -26), (-2, 18)])
    fs(ctx, hx("C2CFD5"), 4, alpha)
    ctx.restore()


def stool(ctx, x, y, s=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    for lx, ex in ((-70, -96), (70, 96), (0, 6)):
        tube(ctx, [(lx * 0.8, -20), (ex, 150)], 22, WOOD_D)
    ellipse(ctx, 0, 0, 120, 30)
    cel(ctx, lambda c: ellipse(c, 0, 0, 120, 30), WOOD, WOOD_D, d=(20, 0))
    ctx.rectangle(-120, 0, 240, 22)
    fs(ctx, WOOD_D, 5)
    ellipse(ctx, 0, 0, 120, 30)
    fs(ctx, WOOD, 6)
    ctx.restore()


# ---------------------------------------------------------------- barber chair (front)
def chair_back(ctx, cx, seat_y, s=1.0):
    ctx.save()
    ctx.translate(cx, seat_y)
    ctx.scale(s, s)
    cel(ctx, lambda c: rrect(c, -150, -400, 300, 420, 70), LEATHER, LEATHER_D, d=(26, 0))
    for yy in (-320, -230, -140):
        for xx in (-70, 0, 70):
            circle(ctx, xx, yy, 6)
            fill(ctx, LEATHER_D)
    cel(ctx, lambda c: rrect(c, -100, -470, 200, 90, 40), LEATHER, LEATHER_D, d=(16, 0))
    tube(ctx, [(0, -380), (0, -400)], 20, CHROME, ol=5)
    ctx.restore()


def chair_front(ctx, cx, seat_y, s=1.0, base_y=None):
    ctx.save()
    ctx.translate(cx, seat_y)
    ctx.scale(s, s)
    by = 300 if base_y is None else base_y
    # pedestal + base
    cel(ctx, lambda c: ellipse(c, 0, by, 170, 34), CHROME, CHROME_D, d=(30, -6))
    cel(ctx, lambda c: c.rectangle(-36, 60, 72, by - 60), CHROME, CHROME_D, d=(16, 0))
    # footrest
    cel(ctx, lambda c: rrect(c, -120, 200, 240, 28, 12), CHROME, CHROME_D, d=(20, 0))
    # seat
    cel(ctx, lambda c: rrect(c, -165, 10, 330, 62, 26), LEATHER, LEATHER_D, d=(30, 0))
    # armrests
    for side in (-1, 1):
        tube(ctx, [(side * 190, 40), (side * 190, -50)], 18, CHROME)
        cel(ctx, lambda c: rrect(c, side * 190 - 34, -90, 68, 44, 20), LEATHER, LEATHER_D, d=(10, 0))
    ctx.restore()


# ---------------------------------------------------------------- misc
def lamp(ctx, x, y_cord_top, y, t, on=1.0):
    line(ctx, [(x, y_cord_top), (x, y - 40)], color=OL, width=5)
    glow(ctx, x, y + 30, 260, hx("FFD58A"), 0.45 * on)
    ctx.move_to(x - 70, y + 20)
    ctx.curve_to(x - 60, y - 40, x + 60, y - 40, x + 70, y + 20)
    ctx.close_path()
    fs(ctx, GOLD, 6)
    ellipse(ctx, x, y + 22, 34, 12)
    fs(ctx, hx("FFF3C8"), 4)


def bottle(ctx, x, y, h, col):
    rrect(ctx, x - 16, y - h, 32, h, 8)
    fs(ctx, col, 5)
    rrect(ctx, x - 7, y - h - 22, 14, 24, 4)
    fs(ctx, OL, 0)
    ctx.rectangle(x - 9, y - h * 0.65, 18, h * 0.3)
    fill(ctx, WHITE, 0.8)


def hanging_sign(ctx, x, y, ang, s=1.0):
    """wooden sign on a bracket; (x,y) = bracket pivot; ang = swing angle (rad)"""
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.rotate(ang)
    for sx in (-70, 70):
        line(ctx, [(sx * 0.3, 0), (sx, 70)], color=hx("3A2A1E"), width=5)
    cel(ctx, lambda c: rrect(c, -110, 66, 220, 150, 16), WOOD, WOOD_D, d=(18, 0))
    rrect(ctx, -96, 80, 192, 122, 10)
    stroke_ol(ctx, 3, alpha=0.6)
    # scissors icon (left) + pliers icon (right)
    ctx.save()
    ctx.translate(-46, 152)
    ctx.rotate(0.35)
    scissors(ctx, s=0.55, open_=0.35)
    ctx.restore()
    ctx.save()
    ctx.translate(50, 150)
    ctx.rotate(-0.35)
    pliers(ctx, s=0.30, open_=0.12)
    ctx.restore()
    ctx.restore()


def splint(ctx, x0, x1, y, k_ties=0.0, t=0.0):
    """two wooden slats along a horizontal forearm (y = arm centre line) + cord ties"""
    for dy in (-66, 40):
        cel(ctx, lambda c: rrect(c, x0, y + dy, x1 - x0, 28, 10), hx("D9A56A"), hx("B07A44"), d=(0, -8))
        for k in range(3):
            line(ctx, [(x0 + 30 + k * 90, y + dy + 10), (x0 + 90 + k * 90, y + dy + 14)], color=hx("9A6334"), width=3, alpha=0.8)
    n = 3
    for i in range(n):
        a = clamp01(k_ties * n - i)
        if a <= 0:
            continue
        xx = x0 + (i + 0.7) * (x1 - x0) / (n + 0.4)
        tube(ctx, [(xx - 8, y - 70), (xx + 10, y - 70 + 140 * a)], 13, hx("F0DDB0"), ol=4)
        if a > 0.95:
            ellipse(ctx, xx - 16, y - 76, 14, 9)
            fs(ctx, hx("F0DDB0"), 4)
            ellipse(ctx, xx + 8, y - 78, 14, 9)
            fs(ctx, hx("F0DDB0"), 4)
