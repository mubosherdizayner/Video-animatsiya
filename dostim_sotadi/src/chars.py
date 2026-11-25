# Characters: the hero (only coloured element), the friend and the girl (flat silhouettes), cat, birds.
# Hero units: 100 u = full height (boot sole to doppi top); origin at the feet / seat, y grows downward.
import math, random
import cairo
from style import hx, mix, darken, lighten, rgb, poly, smooth_path, ellipse, fill_ellipse, rrect, acc

SKIN = hx("#EBC8A2"); SKIN_SH = hx("#D8B089"); HAIR = hx("#2E231D"); EYE = hx("#15110F")
CH = hx("#3F7B61"); CH_SH = hx("#2F634D"); CH_LI = hx("#4C8A6E")
IKAT1 = hx("#6FA586"); IKAT2 = hx("#C7A548"); TRIM = hx("#BE8642"); BELT = hx("#B4473B")
COLLAR = hx("#E8E1D3"); DOPPI = hx("#1D2427"); DOPPI_W = hx("#F1EEE6"); BOOT = hx("#33241E")
BOOT_F = darken(BOOT, 0.18)

D2R = math.pi / 180
HIDE = {"hero": False}   # QA only: render a frame without the hero to isolate his pixels

def dirv(a):
    """unit vector for an angle measured from straight down, positive = forward (+x)"""
    return math.sin(a), math.cos(a)

def ik(sx, sy, tx, ty, l1, l2, bend=1):
    dx, dy = tx - sx, ty - sy
    d = max(1e-6, math.hypot(dx, dy))
    dc = min(d, l1 + l2 - 1e-3)
    a = math.acos(max(-1, min(1, (l1 * l1 + dc * dc - l2 * l2) / (2 * l1 * dc))))
    base = math.atan2(dy, dx)
    ang = base - bend * a
    ex, ey = sx + l1 * math.cos(ang), sy + l1 * math.sin(ang)
    k = dc / d
    return (ex, ey), (sx + dx * k, sy + dy * k)

def limb(ctx, pts, w0, w1, c):
    """tapered limb through joint points"""
    rgb(ctx, c)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    n = len(pts) - 1
    for i in range(n):
        w = w0 + (w1 - w0) * (i / max(1, n - 1) if n > 1 else 0)
        ctx.set_line_width(w)
        ctx.move_to(*pts[i]); ctx.line_to(*pts[i + 1]); ctx.stroke()
    for i, p in enumerate(pts):
        w = w0 + (w1 - w0) * min(1, i / max(1, n))
        ctx.arc(p[0], p[1], w / 2, 0, 2 * math.pi); ctx.fill()

def hand(ctx, wx, wy, ang, kind="open", c=SKIN, s=1.0):
    """hand at wrist pointing along ang (radians, cairo atan2 frame)"""
    ctx.save(); ctx.translate(wx, wy); ctx.rotate(ang); ctx.scale(s, s)
    rgb(ctx, c)
    if kind == "point":
        ellipse(ctx, 1.9, 0, 2.2, 1.75); ctx.fill()
        rrect(ctx, 2.6, -1.25, 4.2, 1.15, 0.55); ctx.fill()
        ellipse(ctx, 2.2, 1.3, 1.0, 0.7); ctx.fill()
    elif kind == "flat":
        ellipse(ctx, 2.6, 0, 3.4, 1.35); ctx.fill()
    elif kind == "fist":
        ellipse(ctx, 1.8, 0, 2.0, 1.9); ctx.fill()
    else:
        ellipse(ctx, 2.2, 0, 2.6, 1.75); ctx.fill()
        ellipse(ctx, 3.6, -1.2, 1.3, 0.6, 0.3); ctx.fill()
    ctx.restore()

def arm(ctx, sh, spec, col, cuff=True, hand_c=SKIN, l1=16.5, l2=15.0, w0=6.6, w1=5.6, cuff_c=TRIM):
    """spec: ('ang', a_shoulder_deg, a_elbow_deg, hand_kind) or ('tgt', (x,y), bend, hand_kind)"""
    sx, sy = sh
    if spec[0] == "ang":
        a1 = spec[1] * D2R; a2 = a1 + spec[2] * D2R
        d1 = dirv(a1); el = (sx + d1[0] * l1, sy + d1[1] * l1)
        d2 = dirv(a2); wr = (el[0] + d2[0] * l2, el[1] + d2[1] * l2)
        kind = spec[3] if len(spec) > 3 else "open"
    else:
        el, wr = ik(sx, sy, spec[1][0], spec[1][1], l1, l2, spec[2])
        kind = spec[3] if len(spec) > 3 else "open"
    fa = math.atan2(wr[1] - el[1], wr[0] - el[0])
    # sleeve stops a bit before the wrist, then the cuff, then the hand
    cut = 2.2
    sw = (wr[0] - math.cos(fa) * cut, wr[1] - math.sin(fa) * cut)
    limb(ctx, [(sx, sy), el, sw], w0, w1, col)
    if cuff:
        rgb(ctx, cuff_c); ctx.set_line_cap(cairo.LINE_CAP_BUTT); ctx.set_line_width(w1 + 0.6)
        ctx.move_to(sw[0] - math.cos(fa) * 1.6, sw[1] - math.sin(fa) * 1.6); ctx.line_to(sw[0] + math.cos(fa) * 0.6, sw[1] + math.sin(fa) * 0.6); ctx.stroke()
    hand(ctx, sw[0] + math.cos(fa) * 0.3, sw[1] + math.sin(fa) * 0.3, fa, kind, hand_c)
    return {"elbow": el, "wrist": wr, "fa": fa, "tip": (wr[0] + math.cos(fa) * 4.5, wr[1] + math.sin(fa) * 4.5)}

# ------------------------------------------------------------------ hero pieces
def doppi(ctx, cx, cy, w=11.4, h=8.0, tilt=-4.0, front=False):
    """Chust doppi: black four-sided cap, white border, white pepper (qalampir) motifs. (cx,cy)=bottom centre"""
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(tilt * D2R)
    tw = w * 0.92
    pts = [(-w / 2, 0), (-tw / 2, -h + 0.9), (-tw / 2 + 0.9, -h), (tw / 2 - 0.9, -h), (tw / 2, -h + 0.9), (w / 2, 0)]
    poly(ctx, pts); rgb(ctx, DOPPI); ctx.fill()
    # white border
    poly(ctx, [(-w / 2, 0), (-w / 2 + 0.12, -1.15), (w / 2 - 0.12, -1.15), (w / 2, 0)]); rgb(ctx, DOPPI_W); ctx.fill()
    # pepper motifs (curved teardrops)
    rgb(ctx, DOPPI_W)
    cols = [-w * 0.27, w * 0.2] if not front else [-w * 0.3, 0, w * 0.3]
    for k, px in enumerate(cols):
        py = -h * 0.55
        ctx.save(); ctx.translate(px, py); ctx.rotate((25 if k % 2 == 0 else -25) * D2R)
        ctx.move_to(0, -2.4)
        ctx.curve_to(1.5, -1.6, 1.4, 1.2, 0.2, 2.5)
        ctx.curve_to(-0.2, 1.0, -1.1, -0.6, 0, -2.4)
        ctx.close_path(); ctx.fill()
        ctx.arc(0.1, -2.6, 0.45, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
    # small corner dots on the top edge
    for px in ([-tw / 2 + 1.1, tw / 2 - 1.1] if not front else [-tw / 2 + 1.1, 0, tw / 2 - 1.1]):
        ctx.arc(px, -h + 1.4, 0.35, 0, 2 * math.pi); ctx.fill()
    ctx.restore()

def ikat_fill(ctx, x0, x1, y0, y1, colw=4.4, dh=6.6, seed=0):
    """vertical ikat diamond columns inside the current clip"""
    k = 0
    x = x0
    while x < x1:
        c = IKAT2 if k % 3 == 1 else IKAT1
        rgb(ctx, c)
        off = (dh / 2) if k % 2 else 0
        y = y0 - dh + off
        while y < y1:
            hw = 0.7 if k % 3 == 1 else 0.95
            poly(ctx, [(x, y), (x + hw, y + dh * 0.3), (x, y + dh * 0.6), (x - hw, y + dh * 0.3)]); ctx.fill()
            y += dh
        x += colw; k += 1

def hero_head_side(ctx, hx_, hy, turn=0.0):
    # neck
    poly(ctx, [(hx_ - 2.4, hy + 5.2), (hx_ + 1.5, hy + 5.6), (hx_ + 1.6, hy + 9.4), (hx_ - 2.6, hy + 9.2)]); rgb(ctx, SKIN_SH); ctx.fill()
    # head + face profile
    fill_ellipse(ctx, hx_, hy, 5.4, 6.3, SKIN)
    rgb(ctx, SKIN)
    poly(ctx, [(hx_ + 4.9, hy - 1.6), (hx_ + 6.5, hy + 0.9), (hx_ + 4.9, hy + 1.6)]); ctx.fill()   # nose
    fill_ellipse(ctx, hx_ + 2.7, hy + 4.4, 2.6, 1.8, SKIN)                                    # chin / jaw
    # hair at the nape
    ctx.move_to(hx_ - 1.6, hy - 4.6)
    ctx.curve_to(hx_ - 5.0, hy - 4.8, hx_ - 6.3, hy - 1.0, hx_ - 5.6, hy + 2.6)
    ctx.curve_to(hx_ - 5.3, hy + 4.2, hx_ - 4.2, hy + 5.4, hx_ - 2.6, hy + 5.0)
    ctx.curve_to(hx_ - 2.2, hy + 2.2, hx_ - 1.4, hy - 1.6, hx_ - 1.6, hy - 4.6)
    ctx.close_path(); rgb(ctx, HAIR); ctx.fill()
    # small eye
    fill_ellipse(ctx, hx_ + 3.0, hy - 0.9, 0.72, 0.8, EYE)
    doppi(ctx, hx_ - 0.2, hy - 4.2, tilt=-5)

def hero_torso_side(ctx, ox, oy, hem_dx=0.0, hem_flare=0.0, lap=False):
    """chopon body (standing) ; ox,oy = hip reference so the body can be shifted for sitting"""
    def T(x, y): return (ox + x, oy + y)
    if not lap:
        pts = [T(-3.2, -29), T(-6.8, -24.5), T(-7.4, -16), T(-6.6, -6), T(-8.2, 2), T(-10.8 + hem_dx * 0.5 - hem_flare, 28.4),
               T(-3, 29.4), T(4, 29.4), T(9.6 + hem_dx + hem_flare, 28.4), T(7.6, 10), T(7.4, -2), T(7.7, -16), T(6.0, -24.2), T(3.6, -28.6)]
    else:
        pts = [T(-3.2, -29), T(-6.8, -24.5), T(-7.4, -16), T(-6.8, -6), T(-8.6, -1), T(-9.6, 5.2), T(-6, 8.2),
               T(6, 8.2), T(15.6, 7.6), T(16.4, 3.4), T(13.8, -0.6), T(7.2, -2.2), T(7.4, -6), T(7.7, -16), T(6.0, -24.2), T(3.6, -28.6)]
    # body
    poly(ctx, pts); rgb(ctx, CH); ctx.fill_preserve()
    ctx.save(); ctx.clip()
    # shadow on the back, light on the chest
    poly(ctx, [T(-12, -32), T(-3.6, -32), T(-3.0, -10), T(-4.6, 32), T(-14, 32)]); rgb(ctx, CH_SH); ctx.fill()
    ikat_fill(ctx, ox - 5.2, ox + 7.5, oy - 26, oy + 30)
    poly(ctx, [T(3.8, -27), T(6.4, -24), T(7.6, -12), T(6.0, -8), T(4.6, -20)]); rgb(ctx, CH_LI, 0.85); ctx.fill()
    # gold trim along front edge and hem (stroke clipped to the body)
    rgb(ctx, TRIM); ctx.set_line_width(2.6); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    if not lap:
        front = [T(9.6 + hem_dx + hem_flare, 28.4), T(7.6, 10), T(7.4, -2), T(7.7, -16), T(6.0, -24.2), T(3.6, -28.6)]
        poly(ctx, front, close=False); ctx.stroke()
        ctx.set_line_width(3.0)
        poly(ctx, [T(-10.8 + hem_dx * 0.5 - hem_flare, 28.4), T(-3, 29.4), T(4, 29.4), T(9.6 + hem_dx + hem_flare, 28.4)], close=False); ctx.stroke()
    else:
        front = [T(13.8, -0.6), T(7.2, -2.2), T(7.4, -6), T(7.7, -16), T(6.0, -24.2), T(3.6, -28.6)]
        poly(ctx, front, close=False); ctx.stroke()
        ctx.set_line_width(3.0)
        poly(ctx, [T(-9.6, 5.2), T(-6, 8.2), T(6, 8.2), T(15.6, 7.6), T(16.4, 3.4)], close=False); ctx.stroke()
    ctx.restore()
    # belt
    by = oy - 6.8
    poly(ctx, [T(-6.9, -7.0), T(7.5, -7.0), T(7.5, -3.2), T(-6.7, -3.2)]); rgb(ctx, BELT); ctx.fill()
    poly(ctx, [T(6.4, -4.6), T(8.6, -3.8), T(9.0, 2.6), T(7.4, 3.4), T(6.6, -1.0)]); rgb(ctx, darken(BELT, 0.1)); ctx.fill()
    # shirt collar
    poly(ctx, [T(0.6, -29.6), T(4.0, -29.2), T(4.8, -25.8), T(1.6, -26.6)]); rgb(ctx, COLLAR); ctx.fill()

def hero_side(ctx, x, y, s, facing=1, walk=None, arm_n=None, arm_f=None, hem_dx=0.0, hem_flare=0.0,
              lean=0.0, legs=None, hold=None, head_turn=0.0):
    """standing / walking hero in side view. (x,y) = feet on the ground; s = pixels per unit"""
    if HIDE["hero"]: return {"wrist": (0, 0), "wrist_g": (0, 0), "fa": 0, 1: {"wrist": (0, 0)}, -1: {"wrist": (0, 0)}}
    ctx.save(); ctx.translate(x, y); ctx.scale(s * facing, s)
    # legs
    if walk is not None:
        ph = walk
        a_n = 24 * math.sin(ph); a_f = 24 * math.sin(ph + math.pi)
        k_n = 38 * max(0.0, math.cos(ph)) ** 1.4; k_f = 38 * max(0.0, math.cos(ph + math.pi)) ** 1.4
        lg = ((a_n, k_n), (a_f, k_f))
        hem_dx += 2.2 * math.sin(ph)
    elif legs is not None:
        lg = legs
    else:
        lg = ((4, 0), (-4, 0))
    hip = (0.0, -50.0)
    L1, L2 = 25.5, 22.5
    feet = []
    for (a, k) in lg:
        d1 = dirv(a * D2R); kn = (hip[0] + d1[0] * L1, hip[1] + d1[1] * L1)
        d2 = dirv((a - k) * D2R); an = (kn[0] + d2[0] * L2, kn[1] + d2[1] * L2)
        feet.append((kn, an, a - k))
    low = max(f[1][1] for f in feet)
    dy = -(low + 3.6)  # sole touches y=0
    ctx.translate(0, dy)
    if lean: ctx.rotate(lean * D2R)
    arm_n = _g2l(arm_n, dy); arm_f = _g2l(arm_f, dy)
    sh_f = (-1.6, -73.2); sh_n = (-0.4, -73.6)
    # far arm
    if arm_f is not None:
        arm(ctx, sh_f, arm_f, CH_SH, hand_c=SKIN_SH, cuff_c=darken(TRIM, 0.15))
    # legs (far first)
    for idx in (1, 0):
        kn, an, sa = feet[idx]
        col = BOOT_F if idx == 1 else BOOT
        limb(ctx, [hip, kn, an], 7.6, 6.4, col)
        ctx.save(); ctx.translate(*an); ctx.rotate(-sa * D2R * 0.35)
        rgb(ctx, col)
        ctx.move_to(-3.4, -1.0); ctx.line_to(-3.6, 3.6); ctx.line_to(8.2, 3.6)
        ctx.curve_to(9.6, 3.6, 9.4, 0.8, 7.0, 0.2); ctx.line_to(2.6, -1.4); ctx.close_path(); ctx.fill()
        ctx.restore()
    hero_torso_side(ctx, 0, -50, hem_dx, hem_flare)
    hero_head_side(ctx, 1.6, -87.2, head_turn)
    info = {}
    if arm_n is not None:
        info = arm(ctx, sh_n, arm_n, CH)
        if hold: hold(ctx, info)
        info["wrist_g"] = (info["wrist"][0], info["wrist"][1] + dy)
    ctx.restore()
    return info

def _g2l(spec, dy):
    if spec is None or spec[0] != "tgt": return spec
    return ("tgt", (spec[1][0], spec[1][1] - dy)) + tuple(spec[2:])

def hero_side_sit(ctx, x, y, s, facing=1, arm_n=None, arm_f=None, hold=None, chew=0.0):
    """cross-legged on a flat surface (y = seat surface)"""
    if HIDE["hero"]: return {"wrist": (0, 0), "wrist_g": (0, 0), "fa": 0, 1: {"wrist": (0, 0)}, -1: {"wrist": (0, 0)}}
    ctx.save(); ctx.translate(x, y); ctx.scale(s * facing, s)
    oy = -10.0  # hip reference -> belt at about -16
    # boots peeking out at the front of the lap
    rgb(ctx, BOOT_F); poly(ctx, [(9.4, -1.6), (17.6, -1.2), (18.4, 1.6), (9.6, 1.8)]); ctx.fill()
    if arm_f is not None:
        arm(ctx, (-1.6, oy - 23.2), arm_f, CH_SH, hand_c=SKIN_SH, cuff_c=darken(TRIM, 0.15))
    hero_torso_side(ctx, 0, oy, lap=True)
    hero_head_side(ctx, 1.6, oy - 37.2 + chew * 0.25)
    info = {}
    if arm_n is not None:
        info = arm(ctx, (-0.4, oy - 23.6), arm_n, CH)
        if hold: hold(ctx, info)
    ctx.restore()
    return info

def hero_back_sit(ctx, x, y, s, point=0.0, t=0.0):
    """seen from behind, sitting cross-legged; point 0..1 raises the right arm toward the horizon"""
    if HIDE["hero"]: return {"wrist": (0, 0), "wrist_g": (0, 0), "fa": 0, 1: {"wrist": (0, 0)}, -1: {"wrist": (0, 0)}}
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    # lap spread (knees out to the sides)
    pts = [(-17, 0), (-16, -5.5), (-10.5, -9), (10.5, -9), (16, -5.5), (17, 0)]
    smooth_path(ctx, pts + [(0, 1.2)], close=True); rgb(ctx, CH_SH); ctx.fill()
    # back of the chopon
    back = [(-9.6, -9.5), (-10.4, -22), (-9.8, -36), (-7.0, -40.5), (-3.0, -42), (3.0, -42), (7.0, -40.5), (9.8, -36), (10.4, -22), (9.6, -9.5), (13, -1.4), (-13, -1.4)]
    poly(ctx, back); rgb(ctx, CH); ctx.fill_preserve()
    ctx.save(); ctx.clip()
    ikat_fill(ctx, -9.2, 10.5, -44, 2, colw=3.6)
    poly(ctx, [(-14, -44), (-6.5, -44), (-8.5, 0), (-14, 0)]); rgb(ctx, CH_SH, 0.75); ctx.fill()
    rgb(ctx, TRIM); ctx.set_line_width(3.0); poly(ctx, [(-13, -1.4), (13, -1.4)], close=False); ctx.stroke()
    ctx.restore()
    poly(ctx, [(-10.0, -18.6), (10.0, -18.6), (10.2, -15.0), (-10.2, -15.0)]); rgb(ctx, BELT); ctx.fill()
    # left arm resting
    arm(ctx, (-9.2, -37.5), ("ang", -10, 34, "open"), mix(CH, CH_SH, 0.5), hand_c=SKIN_SH, l1=15, l2=13.5, w0=6.2, w1=5.4)
    # head from behind
    fill_ellipse(ctx, 0, -48.6, 5.6, 6.2, SKIN)
    fill_ellipse(ctx, -5.4, -48.4, 1.0, 1.7, SKIN_SH); fill_ellipse(ctx, 5.4, -48.4, 1.0, 1.7, SKIN_SH)
    ctx.move_to(-5.4, -52.2); ctx.curve_to(-6.0, -47, -4.4, -43.2, 0, -42.6); ctx.curve_to(4.4, -43.2, 6.0, -47, 5.4, -52.2)
    ctx.close_path(); rgb(ctx, HAIR); ctx.fill()
    doppi(ctx, 0, -52.4, w=12.0, h=8.0, tilt=0, front=True)
    # right arm raising and pointing at the horizon
    p = point
    a_sh = lerp_ang(10, 122, p); a_el = lerp_ang(-34, 4, p)
    arm(ctx, (9.2, -37.5), ("ang", a_sh, a_el, "point" if p > 0.6 else "open"), CH, l1=15, l2=13.5, w0=6.2, w1=5.4)
    ctx.restore()

def lerp_ang(a, b, t): return a + (b - a) * t

def hero_front(ctx, x, y, s, arm_l=None, arm_r=None, blink=False, sway=0.0):
    """standing hero facing the camera. arm_l = screen-left arm spec (angles in screen terms: + = outward)"""
    if HIDE["hero"]: return {"wrist": (0, 0), "wrist_g": (0, 0), "fa": 0, 1: {"wrist": (0, 0)}, -1: {"wrist": (0, 0)}}
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    # legs / boots
    rgb(ctx, BOOT)
    for sx in (-1, 1):
        poly(ctx, [(sx * 1.2, -50), (sx * 6.2, -50), (sx * 6.0, -3.4), (sx * 1.6, -3.4)]); ctx.fill()
        poly(ctx, [(sx * 0.8, -4.2), (sx * 6.8, -4.2), (sx * 7.4, 0), (sx * 0.6, 0)]); ctx.fill()
    # chopon (closed, flared hem)
    body = [(-6.0, -78.4), (-10.6, -75.4), (-11.2, -62), (-10.2, -48), (-12.6, -21.6), (12.6, -21.6), (10.2, -48), (11.2, -62), (10.6, -75.4), (6.0, -78.4)]
    poly(ctx, body); rgb(ctx, CH); ctx.fill_preserve()
    ctx.save(); ctx.clip()
    ikat_fill(ctx, -11.4, 12.5, -80, -20, colw=3.6)
    poly(ctx, [(-14, -80), (-7.6, -80), (-8.6, -20), (-14, -20)]); rgb(ctx, CH_SH, 0.8); ctx.fill()
    # V neck shirt + front edge
    poly(ctx, [(-3.6, -79), (3.6, -79), (0.6, -66)]); rgb(ctx, COLLAR); ctx.fill()
    rgb(ctx, TRIM); ctx.set_line_width(1.5)
    poly(ctx, [(-3.6, -79), (0.6, -66), (1.6, -21.6)], close=False); ctx.stroke()
    poly(ctx, [(3.6, -79), (0.6, -66)], close=False); ctx.stroke()
    ctx.set_line_width(3.0); poly(ctx, [(-12.6, -21.6), (12.6, -21.6)], close=False); ctx.stroke()
    ctx.restore()
    poly(ctx, [(-10.4, -57.2), (10.4, -57.2), (10.3, -53.4), (-10.3, -53.4)]); rgb(ctx, BELT); ctx.fill()
    poly(ctx, [(-2.2, -54.2), (0.6, -53.6), (1.4, -46.4), (-1.6, -46.8)]); rgb(ctx, darken(BELT, 0.1)); ctx.fill()
    # neck + head
    poly(ctx, [(-2.2, -82), (2.2, -82), (2.6, -78.2), (-2.6, -78.2)]); rgb(ctx, SKIN_SH); ctx.fill()
    fill_ellipse(ctx, -5.5, -87.4, 1.0, 1.7, SKIN_SH); fill_ellipse(ctx, 5.5, -87.4, 1.0, 1.7, SKIN_SH)
    fill_ellipse(ctx, 0, -87.6, 5.5, 6.5, SKIN)
    rgb(ctx, HAIR)
    for sx in (-1, 1):
        poly(ctx, [(sx * 5.6, -91.6), (sx * 5.0, -86.4), (sx * 4.5, -91.4)]); ctx.fill()
    if blink:
        rgb(ctx, EYE); ctx.set_line_width(0.5)
        for ex in (-2.1, 2.1): ctx.move_to(ex - 0.8, -88.4); ctx.line_to(ex + 0.8, -88.4); ctx.stroke()
    else:
        for ex in (-2.1, 2.1): fill_ellipse(ctx, ex, -88.4, 0.7, 0.8, EYE)
    doppi(ctx, 0, -92.2, w=12.0, h=8.0, tilt=0, front=True)
    info = {}
    # arms: screen-left arm mirrors angles
    for side, spec in ((-1, arm_l), (1, arm_r)):
        if spec is None: spec = ("ang", 8, -6, "open")
        ctx.save(); ctx.scale(side, 1)
        r = arm(ctx, (8.6, -74.6), spec, CH if side > 0 else mix(CH, CH_SH, 0.35), l1=16.5, l2=15)
        ctx.restore()
        info[side] = r
    ctx.restore()
    return info

# ------------------------------------------------------------------ friend (flat silhouette)
def friend_side(ctx, x, y, s, col, facing=1, walk=None, arm_n=None, arm_f=None, head_dir=1.0, lean=0.0, legs=None, hold=None):
    ctx.save(); ctx.translate(x, y); ctx.scale(s * facing, s)
    if walk is not None:
        ph = walk
        lg = ((26 * math.sin(ph), 36 * max(0.0, math.cos(ph)) ** 1.4), (26 * math.sin(ph + math.pi), 36 * max(0.0, math.cos(ph + math.pi)) ** 1.4))
    elif legs is not None: lg = legs
    else: lg = ((3, 0), (-3, 0))
    hip = (0.0, -49.0); L1, L2 = 25.0, 23.0
    feet = []
    for (a, k) in lg:
        d1 = dirv(a * D2R); kn = (hip[0] + d1[0] * L1, hip[1] + d1[1] * L1)
        d2 = dirv((a - k) * D2R); an = (kn[0] + d2[0] * L2, kn[1] + d2[1] * L2)
        feet.append((kn, an, a - k))
    low = max(f[1][1] for f in feet)
    dy = -(low + 2.6)
    ctx.translate(0, dy)
    if lean: ctx.rotate(lean * D2R)
    arm_n = _g2l(arm_n, dy); arm_f = _g2l(arm_f, dy)
    info = {}
    if arm_f is not None:
        arm(ctx, (-1.2, -74), arm_f, col, cuff=False, hand_c=col, l1=17, l2=15.5, w0=6.0, w1=5.0)
    for kn, an, sa in feet:
        limb(ctx, [hip, kn, an], 8.4, 6.8, col)
        ctx.save(); ctx.translate(*an); ctx.rotate(-sa * D2R * 0.35); rgb(ctx, col)
        ctx.move_to(-3.0, -1.0); ctx.line_to(-3.2, 2.6); ctx.line_to(8.0, 2.6); ctx.curve_to(9.0, 2.6, 8.8, 0.4, 6.6, 0); ctx.line_to(2.4, -1.2); ctx.close_path(); ctx.fill()
        ctx.restore()
    # torso (shirt + jacket), a bit broader than the hero
    rgb(ctx, col)
    poly(ctx, [(-3.6, -80), (-8.0, -75), (-8.6, -62), (-7.4, -48), (-7.6, -44), (7.8, -44), (7.4, -50), (8.6, -63), (7.0, -74.6), (3.2, -80)]); ctx.fill()
    poly(ctx, [(-2.4, -83), (2.4, -83), (2.8, -78), (-2.8, -78)]); ctx.fill()
    friend_head(ctx, 0.8, -88.6, col, head_dir)
    if arm_n is not None:
        info = arm(ctx, (0.0, -74.4), arm_n, col, cuff=False, hand_c=col, l1=17, l2=15.5, w0=6.4, w1=5.4)
        if hold: hold(ctx, info)
        info["wrist_g"] = (info["wrist"][0], info["wrist"][1] + dy)
    ctx.restore()
    return info

def friend_head(ctx, hx_, hy, col, head_dir=1.0):
    """silhouette head; head_dir -1..1 moves the nose from left profile to right profile"""
    rgb(ctx, col)
    ellipse(ctx, hx_, hy, 5.6, 6.6); ctx.fill()
    d = max(-1, min(1, head_dir))
    if abs(d) > 0.15:
        sgn = 1 if d > 0 else -1; k = (abs(d) - 0.15) / 0.85
        nx = hx_ + sgn * (5.0 * k + 0.2)
        poly(ctx, [(nx, hy - 1.8), (nx + sgn * 1.8 * k, hy + 0.9), (nx, hy + 1.7)]); ctx.fill()
        ellipse(ctx, hx_ + sgn * 2.6 * k, hy + 4.6, 2.8, 2.0); ctx.fill()
    # short hair volume on top
    ellipse(ctx, hx_ - 0.6 * d, hy - 4.6, 5.9, 3.0); ctx.fill()

def friend_front(ctx, x, y, s, col, head_dir=0.0, arm_l=None, arm_r=None, hold=None):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    rgb(ctx, col)
    for sx in (-1, 1):
        poly(ctx, [(sx * 0.9, -48), (sx * 7.4, -48), (sx * 6.6, -2.6), (sx * 1.6, -2.6)]); ctx.fill()
        poly(ctx, [(sx * 0.9, -3.4), (sx * 7.6, -3.4), (sx * 8.0, 0), (sx * 0.6, 0)]); ctx.fill()
    poly(ctx, [(-5.4, -80.4), (-11.6, -76.6), (-12.0, -62), (-10.4, -46), (10.4, -46), (12.0, -62), (11.6, -76.6), (5.4, -80.4)]); ctx.fill()
    poly(ctx, [(-2.6, -84), (2.6, -84), (3.0, -79), (-3.0, -79)]); ctx.fill()
    friend_head(ctx, 0, -89.6, col, head_dir)
    info = {}
    for side, spec in ((-1, arm_l), (1, arm_r)):
        if spec is None: spec = ("ang", 6, -4, "open")
        ctx.save(); ctx.scale(side, 1)
        info[side] = arm(ctx, (9.8, -75.4), spec, col, cuff=False, hand_c=col, l1=17, l2=15.5, w0=6.4, w1=5.4)
        ctx.restore()
    if hold: hold(ctx, info)
    ctx.restore()
    return info

def friend_back(ctx, x, y, s, col, sit=False, sway=0.0, arm_r=None):
    """seen from behind"""
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s); rgb(ctx, col)
    if sit:
        smooth_path(ctx, [(-17.5, 0), (-16.4, -5.6), (-11, -9.4), (11, -9.4), (16.4, -5.6), (17.5, 0), (0, 1.2)], close=True); ctx.fill()
        poly(ctx, [(-11, -8.5), (-11.6, -24), (-10.8, -37), (-6.2, -41.5), (6.2, -41.5), (10.8, -37), (11.6, -24), (11, -8.5)]); ctx.fill()
        for sx in (-1, 1):
            ctx.save(); ctx.scale(sx, 1)
            arm(ctx, (9.4, -37.5), ("ang", 12, -28, "open"), col, cuff=False, hand_c=col, l1=15, l2=13.5, w0=6.2, w1=5.2)
            ctx.restore()
        poly(ctx, [(-2.6, -45), (2.6, -45), (3.0, -40), (-3.0, -40)]); ctx.fill()
        ellipse(ctx, 0, -49.6, 5.8, 6.6); ctx.fill(); ellipse(ctx, 0, -54.0, 5.9, 3.2); ctx.fill()
    else:
        for sx in (-1, 1):
            poly(ctx, [(sx * 0.9, -48), (sx * 7.4, -48), (sx * 6.8, -2.4), (sx * 1.8, -2.4)]); ctx.fill()
            poly(ctx, [(sx * 1.2, -3.2), (sx * 7.4, -3.2), (sx * 7.6, 0), (sx * 1.0, 0)]); ctx.fill()
        poly(ctx, [(-5.4, -80.4), (-11.6, -76.6), (-12.0, -62), (-10.4, -46), (10.4, -46), (12.0, -62), (11.6, -76.6), (5.4, -80.4)]); ctx.fill()
        poly(ctx, [(-2.6, -84), (2.6, -84), (3.0, -79), (-3.0, -79)]); ctx.fill()
        ellipse(ctx, 0, -89.6, 5.8, 6.6); ctx.fill(); ellipse(ctx, 0, -94.0, 5.9, 3.2); ctx.fill()
        for sx in (-1, 1):
            ctx.save(); ctx.scale(sx, 1)
            spec = arm_r if (sx > 0 and arm_r) else ("ang", 7 + sway, -5, "open")
            arm(ctx, (9.8, -75.4), spec, col, cuff=False, hand_c=col, l1=17, l2=15.5, w0=6.4, w1=5.4)
            ctx.restore()
    ctx.restore()

def friend_side_sit(ctx, x, y, s, col, facing=-1, arm_n=None, chew=0.0):
    ctx.save(); ctx.translate(x, y); ctx.scale(s * facing, s); rgb(ctx, col)
    smooth_path(ctx, [(-9.5, 0), (-9.8, -6), (-6, -10), (8, -8.6), (16.5, -7), (18, -2), (16, 1), (0, 1)], close=True); ctx.fill()
    poly(ctx, [(-3.6, -41.4), (-8.0, -36.4), (-8.6, -23), (-7.6, -8), (8.0, -8), (8.6, -24), (7.0, -36), (3.2, -41.4)]); ctx.fill()
    poly(ctx, [(-2.4, -44.4), (2.4, -44.4), (2.8, -39.4), (-2.8, -39.4)]); ctx.fill()
    friend_head(ctx, 0.8, -50.0 + chew * 0.25, col, 1.0)
    arm(ctx, (-1.0, -35.4), ("ang", 22, -60, "open"), col, cuff=False, hand_c=col, l1=15.5, l2=14, w0=6.0, w1=5.0)
    if arm_n is not None:
        arm(ctx, (0.0, -35.8), arm_n, col, cuff=False, hand_c=col, l1=15.5, l2=14, w0=6.2, w1=5.2)
    ctx.restore()

# ------------------------------------------------------------------ girl (silhouette, scarf tip = muted accent)
def girl(ctx, x, y, s, col, t, wind=0.3, facing=1):
    ctx.save(); ctx.translate(x, y); ctx.scale(s * facing, s); rgb(ctx, col)
    sw = math.sin(t * 2.0) * (0.6 + 2.4 * wind)
    # long dress
    smooth_path(ctx, [(-4.2, -70), (-7.4, -60), (-8.4, -40), (-11.2 - sw * 0.6, -6), (-12.2 - sw, 0), (12.0 - sw * 0.4, 0), (11.4 - sw * 0.3, -6), (8.6, -40), (7.4, -60), (4.2, -70)], close=True); ctx.fill()
    poly(ctx, [(-6.6, 0), (-2.8, 0), (-3.0, 1.8), (-6.8, 1.8)]); ctx.fill(); poly(ctx, [(2.4, 0), (6.2, 0), (6.4, 1.8), (2.6, 1.8)]); ctx.fill()
    # arms folded in front, slightly
    arm(ctx, (0.0, -66.5), ("ang", 6, 46, "open"), col, cuff=False, hand_c=col, l1=13, l2=10.5, w0=5.0, w1=4.2)
    # head + scarf (covers head and shoulders)
    ellipse(ctx, 0.6, -77.6, 5.6, 6.6); ctx.fill()
    smooth_path(ctx, [(-6.4, -78), (-5.8, -84.6), (0.6, -86.6), (6.4, -83.0), (7.2, -76.4), (5.6, -70.4), (8.2, -64), (-8.6, -62.6), (-6.8, -70)], close=True); ctx.fill()
    poly(ctx, [(6.2, -79.4), (8.2, -77.0), (6.4, -75.6)]); ctx.fill()     # nose under the scarf edge
    # scarf tail flowing behind (tip in muted pink)
    fl = math.sin(t * (3.0 + 4 * wind)) * (1.2 + 5 * wind); fl2 = math.sin(t * (3.0 + 4 * wind) + 1.1) * (1.0 + 4 * wind)
    tail = [(-5.6, -76), (-10.6 - 6 * wind, -73 + fl * 0.5), (-15.4 - 12 * wind, -68 + fl), (-18.6 - 16 * wind, -63.6 + fl2), (-14.6 - 12 * wind, -64 + fl * 0.8), (-9.6 - 5 * wind, -67.4 + fl * 0.4), (-6.2, -69)]
    smooth_path(ctx, tail, close=True); ctx.fill()
    tip = [(-15.0 - 12 * wind, -68.4 + fl), (-18.6 - 16 * wind, -63.6 + fl2), (-14.4 - 12 * wind, -63.6 + fl * 0.8), (-13.6 - 10.5 * wind, -66.4 + fl * 0.9)]
    poly(ctx, tip); rgb(ctx, acc(hx("#D9AEB1"))); ctx.fill()
    ctx.restore()

# ------------------------------------------------------------------ animals
def cat(ctx, x, y, s, col, t, facing=1):
    ctx.save(); ctx.translate(x, y); ctx.scale(s * facing, s); rgb(ctx, col)
    ph = t * 7.0
    ellipse(ctx, 0, -9.0, 9.6, 4.4); ctx.fill()
    for k, (lx, o) in enumerate(((-6.4, 0), (-4.2, math.pi), (5.0, math.pi), (7.0, 0))):
        a = 0.45 * math.sin(ph + o)
        ctx.set_line_width(1.9); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(lx, -7.6); ctx.line_to(lx + 5.6 * math.sin(a), -7.6 + 7.4 * math.cos(a)); ctx.stroke()
    ellipse(ctx, 10.6, -13.6, 3.8, 3.4); ctx.fill()
    poly(ctx, [(8.4, -15.6), (8.8, -19.6), (10.8, -16.6)]); ctx.fill(); poly(ctx, [(11.4, -16.6), (13.0, -19.8), (13.6, -15.6)]); ctx.fill()
    tw = math.sin(t * 2.2) * 2.4
    ctx.set_line_width(1.8)
    ctx.move_to(-9.0, -10.4); ctx.curve_to(-14, -12, -15 + tw, -18, -12 + tw, -22); ctx.stroke()
    ctx.restore()

def bird(ctx, x, y, s, col, ph, a=1.0):
    """flat bird seen from the side/back: two wings flapping"""
    f = math.sin(ph)
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s); rgb(ctx, col, a)
    wy = -5.0 * f
    ctx.move_to(-9, wy); ctx.curve_to(-5, wy * 0.5 - 1.6, -2, -1.6, 0, 0.4)
    ctx.curve_to(2, -1.6, 5, wy * 0.5 - 1.6, 9, wy)
    ctx.curve_to(5, wy * 0.4 + 0.4, 2, 1.6, 0, 2.2)
    ctx.curve_to(-2, 1.6, -5, wy * 0.4 + 0.4, -9, wy); ctx.close_path(); ctx.fill()
    ctx.restore()

# ------------------------------------------------------------------ hero dust particles
_SIL = None
def hero_particles(n=1500, seed=5):
    """origin points inside the standing hero silhouette with the colour of that body part"""
    global _SIL
    if _SIL is not None and len(_SIL) == n: return _SIL
    rnd = random.Random(seed)
    out = []
    while len(out) < n:
        y = -rnd.uniform(0, 100)
        if y > -22: hw, cx = 4.6, 1.5; cols = [BOOT, BOOT_F]
        elif y > -55: hw, cx = 8.5 + (-22 - y) * -0.06, -0.4; cols = [CH, CH, CH_SH, IKAT1, IKAT2, CH_LI]
        elif y > -58: hw, cx = 7.0, 0.3; cols = [BELT]
        elif y > -79: hw, cx = 7.4, 0.2; cols = [CH, CH_SH, IKAT1, CH, IKAT2]
        elif y > -92: hw, cx = 5.4, 1.4; cols = [SKIN, SKIN, SKIN_SH, HAIR]
        else: hw, cx = 5.6, 1.0; cols = [DOPPI, DOPPI, DOPPI_W]
        x = cx + rnd.uniform(-hw, hw)
        out.append((x, y, rnd.choice(cols), rnd.uniform(0.6, 1.5), rnd.random(), rnd.random(), rnd.random()))
    _SIL = out
    return out
