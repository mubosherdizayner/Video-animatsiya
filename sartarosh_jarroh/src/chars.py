# Chibi characters drawn as vector shapes (cairo). Local coords: feet centre at (0,0),
# y down; standing height ~560 units at s=1; head(+cap) ~ 45-48 % of height.
import math
from gfx import *

HIP_STAND, HIP_SIT = -140.0, -96.0
SH = -150.0          # shoulder line relative to hip
NECK2HEAD = 112.0    # neck -> head centre
UL, FL = 76.0, 72.0  # upper / fore arm length

LOOKS = {
    "hero": dict(wf=1.0, skin=SKIN, head="doppi", facial=None, outfit="chapan",
                 legs=hx("35302E"), shoes=hx("2A1E18"), brow=OL, nose="small"),
    "barber": dict(wf=1.0, skin=SKIN, head="short", facial="beard", outfit="barber",
                   legs=hx("2F3B4C"), shoes=hx("1E1E1E"), brow=hx("2A1A12"), nose="small"),
    "surgeon": dict(wf=1.2, skin=SKIN, head="feltcap", facial="mustache", outfit="surgeon",
                    legs=hx("5C4030"), shoes=hx("3A2414"), brow=hx("3A2414"), nose="round"),
    "physician": dict(wf=1.05, skin=SKIN, head="roundhat", facial="goatee", outfit="robe",
                      legs=hx("2A1E18"), shoes=hx("2A1E18"), brow=hx("6E6458"), nose="big"),
    "patient": dict(wf=0.95, skin=SKIN, head="messy", facial=None, outfit="tunic",
                    legs=hx("6E6253"), shoes=hx("4A3422"), brow=hx("4A3020"), nose="small"),
}

ARM_DEF = dict(a=12, e=-8, hand="fist", hrot=0.0, prop=None, behind=False, hs=1.0, mirror=None, out=False, habs=None)
POSE_DEF = dict(x=0, y=0, s=1.0, flip=False, rot=0.0, lean=0.0, bob=0.0, sx=1.0, legs="stand",
                walk=0.0, brace=None, tilt=0.0, turn=0.0, look=(0.0, 0.0), blink=None, wink=None,
                brows="normal", mouth="smile_open", eyes="normal", cape=False, seed=0, sweat=0.0,
                head_dy=0.0, armL=None, armR=None, out=None, breathe=1.0, alpha=1.0, parts="all")


# ---------------------------------------------------------------- hands
def hand(ctx, kind, skin, shade, mirror=False):
    ctx.save()
    if mirror:
        ctx.scale(-1, 1)
    sk = lambda f, d=(4, 3), o=5: cel(ctx, f, skin, shade, d=d, ol=o)
    if kind in ("fist", "hold"):
        sk(lambda c: ellipse(c, 0, 20, 25, 23))
        sk(lambda c: ellipse(c, 17, 9, 10, 14, rot=-0.5), d=(2, 2), o=4)
        for x0 in (-12, -2, 9):
            line(ctx, [(x0, 33), (x0 + 1, 39)], width=3)
    elif kind == "open":
        for fx, ang, ln in ((-15, -0.20, 28), (-5, -0.06, 34), (5, 0.06, 35), (15, 0.19, 30)):
            tube(ctx, [(fx * 0.9, 28), (fx + math.sin(ang) * ln, 28 + math.cos(ang) * ln)], 13, skin, ol=4)
        tube(ctx, [(15, 14), (33, 30)], 14, skin, ol=4)
        sk(lambda c: rrect(c, -22, 2, 44, 40, 16))
        line(ctx, [(-10, 26), (0, 30), (10, 25)], width=2.5, alpha=0.55, smooth_=True)
    elif kind == "point":
        tube(ctx, [(-8, 28), (-9, 70)], 13, skin, ol=4)
        sk(lambda c: ellipse(c, 0, 20, 25, 22))
        sk(lambda c: ellipse(c, 17, 9, 10, 14, rot=-0.5), d=(2, 2), o=4)
        line(ctx, [(2, 36), (3, 41)], width=3)
        line(ctx, [(12, 34), (12, 39)], width=3)
    elif kind == "pinch":
        tube(ctx, [(-10, 26), (-10, 62)], 13, skin, ol=4)
        tube(ctx, [(14, 14), (12, 50)], 14, skin, ol=4)
        sk(lambda c: ellipse(c, -2, 20, 22, 20))
    elif kind == "grip":  # wrapped around a vertical staff, fingers visible as bands
        sk(lambda c: rrect(c, -27, 0, 54, 46, 18))
        for k in range(4):
            line(ctx, [(-22, 8 + k * 10), (20, 9 + k * 10)], width=3)
    ctx.restore()


# ---------------------------------------------------------------- face parts
def eye(ctx, x, y, rx, ry, look, cl, style="normal", side=1):
    if style == "spiral":
        ctx.save()
        ellipse(ctx, x, y, rx, ry)
        fs(ctx, WHITE, 5)
        pts = []
        for k in range(40):
            a = k * 0.42 + look[0] * 6
            r = 2 + k * 0.62 * rx / 30
            pts.append((x + r * math.cos(a), y + r * math.sin(a) * ry / rx))
        line(ctx, pts, width=4)
        ctx.restore()
        return
    if style == "happy" or cl > 0.75:
        # closed: happy arc (^) or blink line
        if style == "happy":
            line(ctx, [(x - rx * 0.8, y + 6), (x, y - ry * 0.45), (x + rx * 0.8, y + 6)], width=7, smooth_=True)
        else:
            line(ctx, [(x - rx * 0.85, y + 2), (x, y + ry * 0.22), (x + rx * 0.85, y + 2)], width=7, smooth_=True)
        return
    sq = 1 - 0.9 * cl
    ellipse(ctx, x, y, rx, ry * sq)
    fs(ctx, WHITE, 6)
    ctx.save()
    ellipse(ctx, x, y, rx, ry * sq)
    ctx.clip()
    pr = rx * 0.55
    px, py = x + look[0] * rx * 0.36, y + look[1] * ry * 0.34 + 2
    circle(ctx, px, py, pr)
    fill(ctx, hx("1B1B1B"))
    circle(ctx, px + pr * 0.38, py - pr * 0.42, pr * 0.32)
    fill(ctx, WHITE)
    circle(ctx, px - pr * 0.35, py + pr * 0.4, pr * 0.13)
    fill(ctx, WHITE)
    ctx.restore()
    if style == "half":  # heavy upper lid (smug)
        ctx.save()
        ellipse(ctx, x, y, rx + 5, ry * sq + 5)
        ctx.clip()
        ctx.rectangle(x - rx - 8, y - ry - 8, 2 * rx + 16, ry * 0.95 + 8)
        fill(ctx, SKIN)
        ctx.restore()
        line(ctx, [(x - rx - 2, y - ry * 0.1), (x + rx + 2, y - ry * 0.04)], width=7)


def brows(ctx, tx, style, color, lift=0.0, side_scale=(1, 1)):
    shapes = {
        "normal": [(18, -40), (44, -50), (70, -42)],
        "raised": [(18, -50), (44, -62), (70, -53)],
        "angry": [(16, -32), (44, -42), (70, -52)],
        "worried": [(16, -52), (44, -46), (70, -36)],
        "smug": [(18, -48), (46, -55), (72, -45)],
        "focus": [(16, -36), (44, -44), (70, -44)],
    }
    for side in (-1, 1):
        st = style
        if style == "confused":
            st = "raised" if side > 0 else "angry"
        pts = [(tx + side * x * side_scale[0 if side < 0 else 1], y - lift) for x, y in shapes[st]]
        tube(ctx, pts, 11, color, ol=0)


def mouth(ctx, tx, kind, y=58):
    if kind in ("smile_open", "laugh", "grin_open"):
        big = 1.15 if kind == "laugh" else 1.0
        def path(c):
            c.move_to(tx - 50 * big, y - 12)
            c.curve_to(tx - 18, y - 5, tx + 18, y - 5, tx + 50 * big, y - 12)
            c.curve_to(tx + 48 * big, y + 44 * big, tx - 48 * big, y + 44 * big, tx - 50 * big, y - 12)
            c.close_path()
        path(ctx)
        fill(ctx, MOUTH)
        ctx.save()
        path(ctx)
        ctx.clip()
        ellipse(ctx, tx, y + 38 * big, 30 * big, 16 * big)
        fill(ctx, TONGUE)
        ctx.rectangle(tx - 60, y - 20, 120, 18)
        fill(ctx, WHITE)
        ctx.restore()
        path(ctx)
        stroke_ol(ctx, 6)
    elif kind == "smile":
        line(ctx, [(tx - 32, y - 4), (tx, y + 14), (tx + 32, y - 4)], width=7, smooth_=True)
    elif kind == "smirk":
        line(ctx, [(tx - 26, y + 6), (tx + 8, y + 10), (tx + 34, y - 6)], width=7, smooth_=True)
    elif kind == "o":
        ellipse(ctx, tx, y + 8, 13, 16)
        fs(ctx, MOUTH, 5)
    elif kind == "wide":
        ellipse(ctx, tx, y + 14, 28, 32)
        fs(ctx, MOUTH, 6)
        ctx.save()
        ellipse(ctx, tx, y + 14, 28, 32)
        ctx.clip()
        ellipse(ctx, tx, y + 40, 20, 12)
        fill(ctx, TONGUE)
        ctx.restore()
        ellipse(ctx, tx, y + 14, 28, 32)
        stroke_ol(ctx, 6)
    elif kind == "aah":  # patient, mouth wide open for the tooth
        ellipse(ctx, tx, y + 18, 34, 38)
        fs(ctx, MOUTH, 6)
        ctx.save()
        ellipse(ctx, tx, y + 18, 34, 38)
        ctx.clip()
        ellipse(ctx, tx, y + 48, 24, 14)
        fill(ctx, TONGUE)
        ctx.restore()
        ellipse(ctx, tx, y + 18, 34, 38)
        stroke_ol(ctx, 6)
    elif kind == "flat":
        line(ctx, [(tx - 20, y + 6), (tx + 20, y + 6)], width=7)
    elif kind == "worried":
        line(ctx, [(tx - 28, y + 10), (tx - 14, y + 2), (tx, y + 10), (tx + 14, y + 2), (tx + 28, y + 10)], width=6, smooth_=True)
    elif kind == "grit":
        rrect(ctx, tx - 30, y - 4, 60, 28, 10)
        fs(ctx, WHITE, 6)
        line(ctx, [(tx - 30, y + 10), (tx + 30, y + 10)], width=3)
    elif kind == "hmph":
        line(ctx, [(tx - 18, y + 4), (tx + 4, y + 0), (tx + 22, y + 6)], width=7, smooth_=True)


def doppi(ctx, tx):
    def path(c):
        c.move_to(-114, -60)
        c.curve_to(-60, -50, 60, -50, 114, -60)
        c.line_to(98, -140)
        c.curve_to(96, -154, 86, -160, 70, -161)
        c.curve_to(22, -165, -22, -165, -70, -161)
        c.curve_to(-86, -160, -96, -154, -98, -140)
        c.close_path()
    cel(ctx, path, DOPPI, hx("101010"), d=(-8, 0), ol=0)
    ctx.save()
    path(ctx)
    ctx.clip()
    off = tx * 0.9
    # soft top-left sheen
    ellipse(ctx, -50 + off * 0.5, -128, 40, 14, rot=-0.15)
    fill(ctx, WHITE, 0.08)
    # bottom band
    ctx.move_to(-130, -72)
    ctx.curve_to(-60, -60, 60, -60, 130, -72)
    ctx.set_source_rgba(*GOLD, 1)
    ctx.set_line_width(5)
    ctx.stroke()
    # small triangles along bottom band
    for k in range(-6, 7):
        x = k * 20 + off % 20
        y = -76 + abs(x) * 0.06
        poly(ctx, [(x - 6, y), (x + 6, y), (x, y - 9)])
        fill(ctx, GOLD)
    # big zigzag with diamonds
    pts = []
    for k in range(-7, 8):
        x = k * 26 + off
        pts.append((x, -90 if k % 2 else -124))
    poly(ctx, pts, close=False)
    ctx.set_line_width(5)
    ctx.set_line_join(cairo.LINE_JOIN_MITER)
    ctx.stroke()
    for k in range(-7, 8):
        x = k * 26 + off
        cy = -110 if k % 2 else -104
        y = cy
        poly(ctx, [(x, y - 8), (x + 6, y), (x, y + 8), (x - 6, y)])
        ctx.set_source_rgba(*GOLD, 1)
        ctx.fill()
    # top band line + dots
    ctx.move_to(-120, -138)
    ctx.line_to(120, -138)
    ctx.set_line_width(4)
    ctx.stroke()
    for k in range(-8, 9):
        circle(ctx, k * 14 + off % 14, -149, 3)
        ctx.fill()
    ctx.restore()
    path(ctx)
    stroke_ol(ctx, 6)


def head(ctx, kind, L, p, t):
    turn = p["turn"]
    tx = turn * 26
    skin = L["skin"]
    rx, ry = 124, 112
    # ---- ears
    for side in (-1, 1):
        ex = side * (rx - 6) - turn * 18
        sc = 1 - 0.5 * max(0, turn * side)
        cel(ctx, lambda c: ellipse(c, ex, 10, 21 * sc, 27), skin, SKIN_D, d=(4, 3))
        line(ctx, [(ex - side * 4 * sc, -2), (ex + side * 6 * sc, 8), (ex - side * 2 * sc, 20)], width=3.5, smooth_=True)
    # ---- back hair
    if L["head"] == "feltcap":
        for side in (-1, 1):
            cel(ctx, lambda c: ellipse(c, side * 104 - turn * 10, -22, 30, 42), hx("5A3A22"), None)
    if L["head"] == "roundhat":
        for side in (-1, 1):
            cel(ctx, lambda c: ellipse(c, side * 108 - turn * 10, -16, 26, 40), hx("BDB6AA"), None)
    # ---- skull
    cel(ctx, lambda c: ellipse(c, 0, 0, rx, ry), skin, SKIN_D, d=(14, 10))
    # ---- facial hair under features
    if L["facial"] == "beard":
        def bpath(c):
            c.move_to(-118 + tx * 0.3, 4)
            c.curve_to(-114, 86, -60, 128, tx, 130)
            c.curve_to(60, 128, 114, 86, 118 + tx * 0.3, 4)
            c.curve_to(104, 44, 66, 96, tx, 100)
            c.curve_to(-66, 96, -104, 44, -118 + tx * 0.3, 4)
            c.close_path()
        cel(ctx, bpath, hx("3A2416"), hx("2A190F"), d=(6, 4), ol=5)
    if L["facial"] == "goatee":
        cel(ctx, lambda c: poly(c, [(tx - 30, 96), (tx + 30, 96), (tx + 6, 140), (tx - 4, 140)]), hx("BDB6AA"), None, ol=5)
    # ---- cheeks
    for side in (-1, 1):
        ellipse(ctx, side * 80 + tx * 0.85, 46, 23, 15)
        fill(ctx, CHEEK, 0.85)
    # ---- eyes
    cl = p["blink"]
    for side in (-1, 1):
        far = max(0.0, turn * side * -1)  # shrinks the eye we turn away from
        ex = side * 45 + tx * 1.1
        rxe = 31 * (1 - 0.22 * far)
        c2 = cl
        if p["wink"] is not None and p["wink"][0] == side:
            c2 = p["wink"][1]
        style = p["eyes"]
        if style == "half" or style == "spiral":
            eye(ctx, ex, 6, rxe, 34, p["look"], c2, style, side)
        elif style == "happy":
            eye(ctx, ex, 6, rxe, 34, p["look"], 1, "happy", side)
        else:
            if c2 > 0.75 and p["wink"] is not None and p["wink"][0] == side:
                eye(ctx, ex, 6, rxe, 34, p["look"], 1, "happy", side)
            else:
                eye(ctx, ex, 6, rxe, 34, p["look"], c2, "normal", side)
    # ---- brows
    brows(ctx, tx * 1.1, p["brows"], L["brow"])
    # ---- nose
    nk = L["nose"]
    if nk == "big":
        cel(ctx, lambda c: ellipse(c, tx * 1.2, 22, 15, 21, rot=-0.2), skin, SKIN_D, d=(3, 3), ol=5)
    elif nk == "round":
        cel(ctx, lambda c: ellipse(c, tx * 1.2, 26, 17, 13), skin, SKIN_D, d=(3, 3), ol=5)
    else:
        ellipse(ctx, tx * 1.2, 34, 11, 8)
        fill(ctx, SKIN_D)
        ctx.new_path()
        ctx.arc(tx * 1.2, 32, 10, 0.25 * PI, 0.75 * PI)
        stroke_ol(ctx, 4)
    # ---- mouth + mustache
    my = 70 if L["facial"] == "mustache" else 64
    mouth(ctx, tx * 1.05, p["mouth"], my)
    if L["facial"] == "mustache":
        for side in (-1, 1):
            def mpath(c, side=side):
                c.move_to(tx, 34)
                c.curve_to(tx + side * 26, 26, tx + side * 58, 32, tx + side * 74, 46)
                c.curve_to(tx + side * 80, 54, tx + side * 72, 64, tx + side * 62, 58)
                c.curve_to(tx + side * 44, 52, tx + side * 24, 56, tx, 52)
                c.close_path()
            cel(ctx, mpath, hx("4A2E1A"), hx("372112"), d=(0, -4), ol=5)
    if p["sweat"] > 0:
        a = p["sweat"]
        sx = 104 + tx * 0.4
        ctx.move_to(sx, -50)
        ctx.curve_to(sx + 16, -24, sx + 18, -10, sx, -6)
        ctx.curve_to(sx - 18, -10, sx - 16, -24, sx, -50)
        ctx.close_path()
        fs(ctx, hx("BFE6F2"), 4, alpha=a)
    # ---- headwear
    hk = L["head"]
    if hk == "doppi":
        doppi(ctx, tx)
    elif hk == "short":
        def hpath(c):
            c.move_to(-120, -18)
            c.curve_to(-126, -90, -70, -128, tx * 0.3, -126)
            c.curve_to(80, -128, 128, -92, 120, -18)
            c.curve_to(110, -50, 96, -66, 70, -74)
            c.curve_to(30, -60, -20, -88, -60, -78)
            c.curve_to(-96, -70, -110, -46, -120, -18)
            c.close_path()
        cel(ctx, hpath, hx("2A1A12"), hx("1A0F09"), d=(8, -6), ol=6)
        line(ctx, [(-40, -110), (10, -118), (50, -108)], color=hx("5A3A28"), width=5, alpha=0.8, smooth_=True)
    elif hk == "feltcap":
        def cpath(c):
            c.move_to(-102, -58)
            c.curve_to(-104, -150, 104, -150, 102, -58)
            c.curve_to(40, -74, -40, -74, -102, -58)
            c.close_path()
        cel(ctx, cpath, hx("7A3E2C"), hx("5C2C1E"), d=(10, 6))
        ctx.move_to(-100, -66)
        ctx.curve_to(-40, -82, 40, -82, 100, -66)
        stroke_ol(ctx, 5, color=hx("A8693F"))
    elif hk == "roundhat":
        cel(ctx, lambda c: ellipse(c, 0, -118, 112, 56), DOPPI, hx("101010"), d=(-6, 6))
        cel(ctx, lambda c: ellipse(c, 0, -72, 128, 26), hx("262626"), None)
        ellipse(ctx, -30, -140, 36, 12, rot=-0.2)
        fill(ctx, WHITE, 0.08)
    elif hk == "messy":
        pts = []
        for k in range(13):
            a = PI + k * PI / 12
            r = 118 if k % 2 == 0 else 136
            pts.append((r * math.cos(a) * 1.02, r * math.sin(a) * 0.9 - 6))
        pts += [(104, -40), (60, -64), (0, -70), (-60, -64), (-104, -40)]
        cel(ctx, lambda c: smooth(c, pts, True, 0.35), hx("6A4A30"), hx("4E3420"), d=(8, -4))


# ---------------------------------------------------------------- body parts
def arm_geom(side, arm, sh_pt):
    a = math.radians(arm["a"])
    f = a + math.radians(arm["e"])
    ux, uy = side * math.sin(a), math.cos(a)
    fx, fy = side * math.sin(f), math.cos(f)
    e = (sh_pt[0] + ux * UL, sh_pt[1] + uy * UL)
    w = (e[0] + fx * FL, e[1] + fy * FL)
    return e, w, (fx, fy)


def draw_arm(ctx, kind, L, side, arm, sh_pt, out_d, name):
    e, w, (fx, fy) = arm_geom(side, arm, sh_pt)
    skin = L["skin"]
    o = L["outfit"]
    start = sh_pt if not arm.get("from") else arm["from"]
    pts = [start, e, w] if not arm.get("from") else [arm["from"], w]
    if o == "chapan":
        tube(ctx, pts, 42, CHAPAN)
        # cuff trim
        cx, cy = w[0] - fx * 10, w[1] - fy * 10
        tube(ctx, [(w[0] - fx * 18, w[1] - fy * 18), (cx, cy)], 44, TRIM, ol=5, cap=cairo.LINE_CAP_BUTT)
        line(ctx, [(w[0] - fx * 18, w[1] - fy * 18), (cx, cy)], color=GOLD, width=3)
    elif o == "barber":
        tube(ctx, pts, 32, skin)
        tube(ctx, [pts[0], (pts[0][0] * 0.55 + e[0] * 0.45, pts[0][1] * 0.55 + e[1] * 0.45)], 46, WHITE)
    elif o == "surgeon":
        tube(ctx, pts, 40, hx("7A4E2D"))
        tube(ctx, [(w[0] - fx * 26, w[1] - fy * 26), (w[0] - fx * 8, w[1] - fy * 8)], 30, skin, ol=5)
    elif o == "robe":
        tube(ctx, pts, 46, hx("7E1F23"))
        tube(ctx, [(w[0] - fx * 16, w[1] - fy * 16), (w[0] - fx * 2, w[1] - fy * 2)], 58, hx("5E1418"), ol=5, cap=cairo.LINE_CAP_BUTT)
    elif o == "tunic":
        tube(ctx, pts, 38, hx("8C8A84"))
    # hand
    ctx.save()
    ctx.translate(*w)
    th = arm["habs"] if arm.get("habs") is not None else math.atan2(-fx, fy) + arm["hrot"]
    ctx.rotate(th)
    s = arm["hs"]
    ctx.scale(s, s)
    mir = arm["mirror"]
    if mir is None:
        mir = (math.cos(th) * (-side)) < 0
    if arm["prop"] is not None and arm["hand"] == "hold":
        ctx.save()
        ctx.translate(0, 20)
        arm["prop"](ctx)
        ctx.restore()
    hand(ctx, arm["hand"], skin, SKIN_D, mirror=mir)
    if arm["prop"] is not None and arm["hand"] != "hold":
        ctx.save()
        ctx.translate(0, 20)
        arm["prop"](ctx)
        ctx.restore()
    if out_d is not None:
        out_d[name] = ctx.user_to_device(0, 20)
    ctx.restore()


def legs(ctx, L, p, hip_y, t):
    lc, sc = L["legs"], L["shoes"]
    wf = L["wf"]
    mode = p["legs"]
    if L["outfit"] == "robe":
        for side in (-1, 1):
            cel(ctx, lambda c: ellipse(c, side * 46, -12, 40, 18), sc, None)
        return
    if mode == "sit":
        for side in (-1, 1):
            tube(ctx, [(side * 44 * wf, hip_y + 34), (side * 46 * wf, -26)], 46, lc)
            cel(ctx, lambda c: ellipse(c, side * 48 * wf, hip_y + 18, 40, 30), lc, mul(lc, 0.8), d=(4, 4))
            cel(ctx, lambda c: ellipse(c, side * 50 * wf, -14, 38, 19), sc, None)
        return
    for side in (-1, 1):
        lift, fwd = 0.0, 0.0
        if mode == "walk":
            ph = p["walk"] * TAU + (0 if side < 0 else PI)
            lift = max(0.0, math.sin(ph)) * 30
            fwd = math.cos(ph) * 14
        hx_ = side * 40 * wf
        fx_ = side * 44 * wf + fwd
        if mode == "brace" and side == 1 and p["brace"] is not None:
            kx, ky, fx2, fy2 = p["brace"]
            tube(ctx, [(hx_, hip_y + 10), (kx, ky), (fx2, fy2 - 16)], 48, lc)
            cel(ctx, lambda c: ellipse(c, fx2 + 8, fy2 - 8, 42, 18), sc, None)
            continue
        tube(ctx, [(hx_, hip_y + 10), (fx_, -24 - lift)], 48, lc)
        cel(ctx, lambda c: ellipse(c, fx_ + side * 6, -14 - lift, 40, 19), sc, None)


def torso(ctx, L, p, t):
    o = L["outfit"]
    wf = L["wf"]
    W1 = 88 * wf
    if o == "robe":
        hem = -8 - HIP_STAND + 4
        pts = [(-40, SH - 4), (-W1, SH + 12), (-W1 - 14, SH + 70), (-W1 - 40, hem - 6), (-W1 - 30, hem + 4),
               (0, hem + 8), (W1 + 30, hem + 4), (W1 + 40, hem - 6), (W1 + 14, SH + 70), (W1, SH + 12), (40, SH - 4)]
        body = lambda c: smooth(c, pts, True, 0.25)
        cel(ctx, body, hx("7E1F23"), hx("5E1418"), d=(22, 0))
        ctx.save()
        body(ctx)
        ctx.clip()
        for xx in (-60, -20, 25, 70):
            line(ctx, [(xx * 0.6, SH + 40), (xx, hem)], color=hx("5E1418"), width=4, alpha=0.7)
        ctx.rectangle(-200, hem - 18, 400, 30)
        fill(ctx, GOLD, 0.9)
        ctx.restore()
        body(ctx)
        stroke_ol(ctx, 6)
        rrect(ctx, -46, SH - 14, 92, 26, 12)
        fs(ctx, SHIRT, 5)
        return
    if o in ("surgeon", "tunic"):
        col = hx("7A4E2D") if o == "surgeon" else hx("8C8A84")
        shd = mul(col, 0.78)
        hem = 56
        pts = [(-38, SH - 4), (-W1, SH + 12), (-W1 - 10, SH + 60), (-W1 - 16, hem - 10), (-W1 - 10, hem),
               (0, hem + 6), (W1 + 10, hem), (W1 + 16, hem - 10), (W1 + 10, SH + 60), (W1, SH + 12), (38, SH - 4)]
        cel(ctx, lambda c: smooth(c, pts, True, 0.25), col, shd, d=(18, 0))
        # neck opening
        poly(ctx, [(-24, SH - 4), (0, SH + 28), (24, SH - 4)])
        fs(ctx, mul(L["skin"], 0.92), 5)
        if o == "surgeon":
            ap = [(-62 * wf, SH + 36), (62 * wf, SH + 36), (72 * wf, hem + 40), (0, hem + 48), (-72 * wf, hem + 40)]
            cel(ctx, lambda c: smooth(c, ap, True, 0.15), hx("A87440"), hx("86592F"), d=(12, 0))
            for side in (-1, 1):
                line(ctx, [(side * 50 * wf, SH + 38), (side * 30, SH - 2)], color=hx("86592F"), width=9)
            ctx.save()
            ctx.set_dash([olw(ctx, 6), olw(ctx, 6)])
            rrect(ctx, -54 * wf, SH + 48, 108 * wf, hem + 30 - (SH + 48), 18)
            stroke_ol(ctx, 2.5, alpha=0.6)
            ctx.restore()
            # pocket with a tool
            rrect(ctx, -30, -40, 60, 40, 8)
            fs(ctx, hx("94632F"), 4)
        else:
            rrect(ctx, -W1 - 6, -16, 2 * W1 + 12, 16, 6)
            fs(ctx, hx("A08A60"), 4)
        return
    if o == "barber":
        hem = 16
        pts = [(-40, SH - 4), (-W1, SH + 12), (-W1 - 8, SH + 60), (-W1 - 6, hem), (W1 + 6, hem), (W1 + 8, SH + 60), (W1, SH + 12), (40, SH - 4)]
        cel(ctx, lambda c: smooth(c, pts, True, 0.25), WHITE, hx("E3E0DA"), d=(16, 0))
        ctx.arc(0, SH - 6, 26, 0.1 * PI, 0.9 * PI)
        stroke_ol(ctx, 5)
        ap = [(-58, SH + 34), (58, SH + 34), (70, 96), (0, 102), (-70, 96)]
        cel(ctx, lambda c: smooth(c, ap, True, 0.12), hx("1E1E1E"), hx("121212"), d=(10, 0))
        for side in (-1, 1):
            line(ctx, [(side * 50, SH + 36), (side * 30, SH - 4)], color=hx("1E1E1E"), width=8)
        rrect(ctx, 14, SH + 70, 36, 34, 6)
        fs(ctx, hx("2C2C2C"), 4)
        rrect(ctx, 20, SH + 52, 8, 30, 3)  # comb in pocket
        fs(ctx, TEAL, 3)
        return
    # ---- hero chapan
    hem = 40
    pts = [(-40, SH - 4), (-W1, SH + 10), (-W1 - 12, SH + 54), (-W1 - 22, hem - 14), (-W1 - 20, hem),
           (0, hem + 6), (W1 + 20, hem), (W1 + 22, hem - 14), (W1 + 12, SH + 54), (W1, SH + 10), (40, SH - 4)]
    body = lambda c: smooth(c, pts, True, 0.25)
    cel(ctx, body, CHAPAN, CHAPAN_D, d=(20, 0))
    ctx.save()
    body(ctx)
    ctx.clip()
    # ikat lozenges
    for row in range(5):
        for col in range(-3, 4):
            cx = col * 52 + (26 if row % 2 else 0)
            cy = SH + 30 + row * 40
            poly(ctx, [(cx, cy - 22), (cx + 13, cy), (cx, cy + 22), (cx - 13, cy)])
            fill(ctx, DTEAL, 0.55)
            poly(ctx, [(cx, cy - 11), (cx + 6, cy), (cx, cy + 11), (cx - 6, cy)])
            fill(ctx, GOLD, 0.75)
    for xx in range(-110, 120, 22):
        line(ctx, [(xx, SH), (xx + 6, hem + 10)], color=hx("4FA06A"), width=2, alpha=0.35)
    ctx.restore()
    body(ctx)
    stroke_ol(ctx, 6)
    # shirt panel + embroidery
    sp = [(-34, SH - 2), (-42, hem + 4), (42, hem + 4), (34, SH - 2)]
    poly(ctx, sp)
    fs(ctx, SHIRT, 5)
    line(ctx, [(0, SH + 12), (0, SH + 70)], color=GOLD, width=4)
    for k in range(4):
        y = SH + 20 + k * 14
        poly(ctx, [(0, y - 5), (5, y), (0, y + 5), (-5, y)])
        fill(ctx, GOLD)
    # front trims
    for side in (-1, 1):
        tp = [(side * 34, SH - 2), (side * 52, SH - 2), (side * 62, hem + 4), (side * 42, hem + 4)]
        poly(ctx, tp)
        fs(ctx, TRIM, 5)
        line(ctx, [(side * 43, SH + 6), (side * 47, SH + 40), (side * 50, SH + 80), (side * 53, SH + 120), (side * 52, hem - 2)],
             color=GOLD, width=3, smooth_=True)
        for k in range(7):
            y = SH + 14 + k * 26
            x = side * (43 + (y - SH) * 0.06)
            poly(ctx, [(x, y - 5), (x + 4, y), (x, y + 5), (x - 4, y)])
            fill(ctx, GOLD)
    # hem trim
    ctx.save()
    body(ctx)
    ctx.clip()
    ctx.rectangle(-200, hem - 14, 400, 30)
    fill(ctx, TRIM)
    line(ctx, [(-200, hem - 6), (200, hem - 6)], color=GOLD, width=3)
    ctx.restore()
    body(ctx)
    stroke_ol(ctx, 6)
    # stand collar
    rrect(ctx, -38, SH - 20, 76, 26, 10)
    fs(ctx, SHIRT, 5)
    pz = [(-30 + k * 7.5, SH - 7 + (4 if k % 2 else -4)) for k in range(9)]
    line(ctx, pz, color=GOLD, width=3)


def cape(ctx, t):
    pts = [(-44, SH - 8), (-104, SH + 14), (-150, SH + 80), (-170, 52), (-120, 64), (-60, 58), (0, 68),
           (60, 58), (120, 64), (170, 52), (150, SH + 80), (104, SH + 14), (44, SH - 8)]
    path = lambda c: smooth(c, pts, True, 0.3)
    cel(ctx, path, SHIRT, hx("DCD6CA"), d=(24, 0))
    for xx, yy in ((-90, 40), (-30, 50), (40, 48), (100, 40)):
        line(ctx, [(xx * 0.55, SH + 60), (xx, yy)], color=hx("C9C2B4"), width=3.5, alpha=0.8)
    rrect(ctx, -48, SH - 22, 96, 24, 10)
    fs(ctx, SHIRT, 5)
    circle(ctx, 30, SH - 10, 6)
    fs(ctx, TEAL, 3)


# ---------------------------------------------------------------- full character
def draw(ctx, kind, pose, t=0.0):
    p = dict(POSE_DEF)
    p.update(pose)
    L = LOOKS[kind]
    armL = dict(ARM_DEF)
    armL.update(p["armL"] or {})
    armR = dict(ARM_DEF)
    armR.update(p["armR"] or {})
    if p["blink"] is None:
        p["blink"] = blink(t, p["seed"])
    br = math.sin(TAU * (t + p["seed"] * 0.41) / 3.0) * p["breathe"]
    ctx.save()
    ctx.translate(p["x"], p["y"])
    ctx.rotate(p["rot"])
    ctx.scale(p["s"] * (-1 if p["flip"] else 1) * p["sx"], p["s"])
    if p["alpha"] < 1:
        ctx.push_group()
    hip_y = HIP_SIT if p["legs"] == "sit" else HIP_STAND
    bob = p["bob"]
    if p["legs"] == "walk":
        bob -= abs(math.sin(p["walk"] * TAU)) * 10
    parts = p["parts"]
    if parts != "arms":
        legs(ctx, L, p, hip_y, t)
    ctx.save()
    ctx.translate(0, hip_y + bob)
    ctx.rotate(p["lean"])
    ctx.scale(1, 1 + 0.010 * br)
    out_d = p["out"]
    sh_y = SH + 20
    shL = (-(L["wf"] * 84), sh_y)
    shR = ((L["wf"] * 84), sh_y)
    if armL["behind"] and parts != "body":
        draw_arm(ctx, kind, L, -1, armL, shL, out_d, "handL")
    if armR["behind"] and parts != "body":
        draw_arm(ctx, kind, L, 1, armR, shR, out_d, "handR")
    if parts != "arms":
        if p["cape"]:
            cape(ctx, t)
        else:
            torso(ctx, L, p, t)
    ctx.save()
    ctx.translate(0, SH - 4 - 1.5 * br + p["head_dy"])
    ctx.rotate(p["tilt"])
    ctx.translate(0, -NECK2HEAD + 4)
    if parts != "arms":
        head(ctx, kind, L, p, t)
    if out_d is not None:
        out_d["head"] = ctx.user_to_device(0, 0)
    ctx.restore()
    for arm, side, shp, nm in ((armL, -1, shL, "handL"), (armR, 1, shR, "handR")):
        if arm["behind"] or parts == "body":
            continue
        if p["cape"] and not arm["out"]:
            continue
        draw_arm(ctx, kind, L, side, arm, shp, out_d, nm)
    ctx.restore()
    if p["alpha"] < 1:
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(p["alpha"])
    ctx.restore()


def hero_back(ctx, x, y, s, t, tilt=0.0):
    """over-the-shoulder: back of the hero's head (doppi) + caped shoulders. (x,y)=neck"""
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    br = math.sin(TAU * t / 3.0)
    pts = [(-60, -10), (-160, 20), (-250, 120), (-280, 400), (280, 400), (250, 120), (160, 20), (60, -10)]
    cel(ctx, lambda c: smooth(c, pts, True, 0.3), SHIRT, hx("DCD6CA"), d=(30, 0))
    line(ctx, [(-60, 60), (-120, 300)], color=hx("C9C2B4"), width=4)
    line(ctx, [(40, 70), (90, 300)], color=hx("C9C2B4"), width=4)
    rrect(ctx, -56, -26, 112, 30, 12)
    fs(ctx, SHIRT, 5)
    ctx.translate(0, -112 - 2 * br)
    ctx.rotate(tilt)
    for side in (-1, 1):
        cel(ctx, lambda c: ellipse(c, side * 116, 14, 21, 27), SKIN, SKIN_D, d=(4, 3))
    cel(ctx, lambda c: ellipse(c, 0, 0, 122, 108), SKIN, SKIN_D, d=(16, 6))
    # nape shadow
    ellipse(ctx, 0, 70, 70, 30)
    fill(ctx, SKIN_D, 0.35)
    doppi(ctx, 0)
    ctx.restore()


def shoulder_world(kind, pose, side):
    p = dict(POSE_DEF); p.update(pose)
    L = LOOKS[kind]
    hip_y = HIP_SIT if p["legs"] == "sit" else HIP_STAND
    lx = side * L["wf"] * 84
    ly = hip_y + p["bob"] + SH + 20
    fsg = -1 if p["flip"] else 1
    return (p["x"] + fsg * p["s"] * p["sx"] * lx, p["y"] + p["s"] * ly)


def ik(kind, pose, side, target, bend=1):
    """arm angles (deg) so that the wrist of arm `side` (-1 = screen-left arm) reaches world target"""
    p = dict(POSE_DEF); p.update(pose)
    sx, sy = shoulder_world(kind, pose, side)
    fsg = -1 if p["flip"] else 1
    vx = (target[0] - sx) / (p["s"] * p["sx"]) * fsg
    vy = (target[1] - sy) / p["s"]
    d = max(1e-3, math.hypot(vx, vy))
    d2 = min(d, UL + FL - 0.5)
    adir = math.atan2(side * vx, vy)
    cosA = (UL * UL + d2 * d2 - FL * FL) / (2 * UL * d2)
    A = math.acos(max(-1.0, min(1.0, cosA)))
    au = adir + bend * A
    ex, ey = side * math.sin(au) * UL, math.cos(au) * UL
    f = math.atan2(side * (vx - ex), (vy - ey))
    return dict(a=math.degrees(au), e=math.degrees(f - au))
