# Muted background props: supa with human calculators, cho't (abacus), ENIAC panels, 1940s women, paper plane.
import math
import skia
from common import *

PEOPLE = "#45575B"
PEOPLE2 = "#2E3C40"
PANEL = "#2E3C40"
LAMP = "#E7A05C"


def _sw(p, w):
    pt = skia.Paint(AntiAlias=True); pt.setStyle(skia.Paint.kStroke_Style); pt.setStrokeWidth(w)
    pt.setStrokeCap(skia.Paint.kRound_Cap); pt.setStrokeJoin(skia.Paint.kRound_Join)
    out = skia.Path(); pt.getFillPath(p, out); return out


# ------------------------------------------------------------------ supa + seated calculators
SUPA_HW = 205


def draw_supa_back(c, pal, sx, gy):
    """railing + platform (figures sit on top, drawn after)"""
    wood = paint(pal["near2"])
    top = gy - 74
    c.drawRect(skia.Rect.MakeLTRB(sx - SUPA_HW, top - 92, sx + SUPA_HW, top - 84), wood)        # back top rail
    for k in range(17):
        x = sx - SUPA_HW + 4 + k * (2 * SUPA_HW - 8) / 16.0
        c.drawRect(skia.Rect.MakeLTRB(x - 2.5, top - 86, x + 2.5, top), wood)
    for s in (-1, 1):
        c.drawRect(skia.Rect.MakeLTRB(sx + s * SUPA_HW - 6, top - 96, sx + s * SUPA_HW + 6, top), wood)


def draw_supa_front(c, pal, sx, gy):
    wood = paint(pal["near"])
    top = gy - 74
    c.drawRect(skia.Rect.MakeLTRB(sx - SUPA_HW - 8, top, sx + SUPA_HW + 8, top + 16), wood)
    c.drawRect(skia.Rect.MakeLTRB(sx - SUPA_HW + 10, top + 16, sx + SUPA_HW - 10, top + 24), paint(pal["near2"]))
    for x in (-SUPA_HW + 8, -70, 70, SUPA_HW - 8):
        c.drawRect(skia.Rect.MakeLTRB(sx + x - 8, top + 14, sx + x + 8, gy + 2), wood)


def seated_figure(c, x, y, colr, bend=0.0, arm=0.0, alpha=1.0, facing=1, hat=True):
    """cross-legged figure; (x, y) = seat point on the platform; ~150 px tall"""
    if alpha <= 0.003: return
    c.save(); c.translate(x, y); c.scale(facing, 1)
    p = paint(colr, a=255 * alpha)
    legs = rrect(-48, -26, 52, 2, 13)
    c.drawPath(legs, p)
    c.save(); c.rotate(18 + 14 * bend)      # torso leaning forward over the scroll
    torso = skia.Path()
    torso.moveTo(-30, -6); torso.lineTo(28, -6); torso.lineTo(22, -82); torso.quadTo(0, -100, -22, -84); torso.close()
    c.drawPath(torso, p)
    c.drawCircle(4, -104, 17, p)                                      # head
    if hat:
        c.drawPath(rrect(-12, -126, 20, -112, 5), paint(mix(colr, "#000000", 0.25), a=255 * alpha))
    c.restore()
    # arm reaching the scroll / abacus
    sx_, sy_ = rot(10, -72, math.radians(18 + 14 * bend))
    hx, hy = 62 + 10 * arm, -26 - 6 * arm
    a = skia.Path(); a.moveTo(sx_, sy_); a.quadTo((sx_ + hx) / 2 + 8, sy_ + 10, hx, hy)
    c.drawPath(_sw(a, 15), p)
    c.drawCircle(hx, hy, 8, p)
    c.restore()


def scroll(c, x, y, ln, colr, alpha=1.0):
    p = paint(colr, a=255 * alpha)
    c.drawRect(skia.Rect.MakeLTRB(x, y - 5, x + ln, y), p)
    c.drawCircle(x + ln, y - 6, 6.5, p)
    c.drawCircle(x, y - 6, 5.0, p)


def abacus(c, x, y, t, pal, alpha=1.0, seed=0):
    """standing cho't: wooden frame with 4 rods; beads (accent) slide over time. (x,y) = bottom-left"""
    wood = paint(pal["near"], a=255 * alpha)
    w, h = 62, 46
    c.drawRect(skia.Rect.MakeLTRB(x, y - h, x + w, y - h + 5), wood)
    c.drawRect(skia.Rect.MakeLTRB(x, y - 5, x + w, y), wood)
    c.drawRect(skia.Rect.MakeLTRB(x, y - h, x + 5, y), wood)
    c.drawRect(skia.Rect.MakeLTRB(x + w - 5, y - h, x + w, y), wood)
    bead = paint(LAMP, a=255 * alpha)
    for r in range(4):
        ry = y - h + 11 + r * 9
        c.drawRect(skia.Rect.MakeLTRB(x + 4, ry - 0.8, x + w - 4, ry + 0.8), paint(pal["near2"], a=255 * alpha))
        # beads: a group of 3 slides between left and right in steps
        ph = (t * 1.6 + hash01(seed, r) * 3) % 4.0
        k = smooth(clamp01(ph * 2.5)) if ph < 2 else 1 - smooth(clamp01((ph - 2) * 2.5))
        for b in range(3):
            bx = x + 10 + b * 7.5 + k * (w - 38)
            c.drawPath(oval(bx, ry, 3.9, 3.4), bead)


def calc_positions(sx):
    return [sx - 150, sx - 78, sx - 6, sx + 66, sx + 138]


def draw_calculators(c, pal, sx, gy, t, alphas=(1, 1, 1, 1, 1), paper=None, scrolls=True):
    top = gy - 74
    paper = paper or mix("#E8E1D3", pal["city"], 0.35)
    for j, x in enumerate(calc_positions(sx)):
        a = alphas[j]
        if a <= 0.003: continue
        colr = PEOPLE if j % 2 == 0 else mix(PEOPLE, PEOPLE2, 0.55)
        bend = 0.5 + 0.5 * math.sin(t * 2.2 + j * 1.3)
        seated_figure(c, x - 18, top, colr, bend=bend, arm=0.5 + 0.5 * math.sin(t * 3 + j), alpha=a, hat=j != 2)
        if scrolls:
            scroll(c, x + 18, top, 52, paper, alpha=a)
        if j in (1, 3):
            abacus(c, x + 26, top - 8, t, pal, alpha=a, seed=j)


# ------------------------------------------------------------------ ENIAC panel wall
PW, PH, PGAP = 98, 330, 6
ROWS, COLS = 9, 4


def panel_x(x0, k):
    return x0 + k * (PW + PGAP)


def lamp_rect(px, gy, r, cidx):
    x = px + 16 + cidx * 19
    y = gy - PH + 30 + r * 19
    return skia.Rect.MakeLTRB(x, y, x + 10, y + 10)


def draw_panels(c, x0, n, gy, lamp_fn, cables=True, lamp_glow=True):
    """lamp_fn(k, r, col) -> 0..1 brightness"""
    body = paint(PANEL)
    trim = paint(mix(PANEL, "#000000", 0.25))
    for k in range(n):
        px = panel_x(x0, k)
        c.drawRect(skia.Rect.MakeLTRB(px, gy - PH, px + PW, gy), body)
        c.drawRect(skia.Rect.MakeLTRB(px - 3, gy - PH - 10, px + PW + 3, gy - PH + 2), body)
        c.drawRect(skia.Rect.MakeLTRB(px + 8, gy - PH + 210, px + PW - 8, gy - 30), trim)      # plugboard
        for r in range(4):
            for q in range(5):
                c.drawCircle(px + 18 + q * 15.5, gy - PH + 228 + r * 18, 2.6, paint(mix(PANEL, "#8C9FA1", 0.35)))
    gp = paint(LAMP, a=110); gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6))
    off = paint("#1A2428")
    for k in range(n):
        px = panel_x(x0, k)
        for r in range(ROWS):
            for q in range(COLS):
                v = clamp01(lamp_fn(k, r, q))
                rc = lamp_rect(px, gy, r, q)
                if v < 0.02:
                    c.drawRect(rc, off)
                else:
                    if lamp_glow and v > 0.3:
                        gp.setAlphaf(0.45 * v); c.drawRect(rc.makeOutset(3, 3), gp)
                    c.drawRect(rc, paint(mix("#1A2428", LAMP, v)))
    if cables:
        cp = paint("#1A2428", style="stroke", width=4.5, cap="round")
        for k in range(n - 1):
            px = panel_x(x0, k)
            for j in range(2):
                a = skia.Path()
                x1 = px + 30 + j * 30; x2 = px + PW + PGAP + 26 + j * 34
                y1 = gy - PH + 232 + j * 30
                a.moveTo(x1, y1); a.cubicTo(x1 + 5, y1 + 70 + 20 * j, x2 - 5, y1 + 74 + 16 * j, x2, y1 + 12)
                c.drawPath(a, cp)


# ------------------------------------------------------------------ 1940s woman (side view, facing right)
def woman(c, x, gy, reach=0.0, colr=PEOPLE, alpha=1.0, step=0.0, h=232.0, facing=1):
    """slim 1940s woman, side view facing right; reach 0..1 raises the front arm to the plugboard.
    returns the hand position (world)"""
    s = h / 232.0
    c.save(); c.translate(x, gy); c.scale(s * facing, s)
    p = paint(colr, a=255 * alpha)
    for dx, ph in ((-7, 0), (5, math.pi)):                                   # legs + low heels
        sw = 3 * math.sin(step + ph)
        c.drawRect(skia.Rect.MakeLTRB(dx - 3.2 + sw, -80, dx + 3.2 + sw, -5), p)
        c.drawPath(rrect(dx - 4 + sw, -8, dx + 9 + sw, 0, 3), p)
    d = skia.Path()                                                          # knee-length A-line dress
    d.moveTo(-11, -128); d.lineTo(11, -128); d.lineTo(29, -78); d.quadTo(0, -72, -27, -78); d.close()
    c.drawPath(d, p)
    b = skia.Path()                                                          # fitted bodice, small puff shoulders
    b.moveTo(-10, -127); b.lineTo(10, -127); b.lineTo(14, -160); b.quadTo(15, -170, 6, -171)
    b.lineTo(-7, -171); b.quadTo(-16, -169, -14, -160); b.close()
    c.drawPath(b, p)
    c.drawRect(skia.Rect.MakeLTRB(-12, -131, 12, -125), paint(mix(colr, "#000000", 0.3), a=255 * alpha))   # belt
    c.drawRect(skia.Rect.MakeLTRB(-3.5, -180, 4, -169), p)                    # neck
    c.drawCircle(2, -190, 12.5, p)                                           # head
    c.drawCircle(-10, -195, 7.5, p)                                          # bun
    a = skia.Path(); a.moveTo(-6, -164); a.quadTo(-12, -140, -9, -112)        # back arm, hanging
    c.drawPath(_sw(a, 7), p)
    sh = (7, -164)
    ang = math.radians(lerp(6, 112, reach))
    el = (sh[0] + 29 * math.sin(ang), sh[1] + 29 * math.cos(ang))
    ang2 = math.radians(lerp(10, 92, reach))
    hd = (el[0] + 27 * math.sin(ang2), el[1] + 27 * math.cos(ang2))
    a = skia.Path(); a.moveTo(*sh); a.lineTo(*el); a.lineTo(*hd)
    c.drawPath(_sw(a, 7), p)
    c.drawCircle(hd[0], hd[1], 4.5, p)
    c.restore()
    return (x + hd[0] * s * facing, gy + hd[1] * s)


# ------------------------------------------------------------------ paper plane (Instagram "send" style)
def paper_plane(c, x, y, size, ang_deg, fill="#F4EDDF", fold="#C9C1AE", alpha=1.0):
    c.save(); c.translate(x, y); c.rotate(ang_deg); c.scale(size, size)
    p = skia.Path()
    p.moveTo(1.0, 0.0); p.lineTo(-0.85, -0.72); p.lineTo(-0.42, 0.02); p.lineTo(-0.85, 0.72); p.close()
    c.drawPath(p, paint(fill, a=255 * alpha))
    f = skia.Path(); f.moveTo(1.0, 0.0); f.lineTo(-0.42, 0.02); f.lineTo(-0.62, 0.38)
    c.drawPath(f, paint(fold, a=255 * alpha, style="stroke", width=0.07, cap="round"))
    c.restore()


def hand_down_icon(c, x, y, s, colr):
    """vector 👇: back of the hand, index finger pointing down, thumb and curled fingers; (x,y) = top-left, s = height"""
    k = s / 100.0
    c.save(); c.translate(x, y); c.scale(k, k)
    p = paint(colr)
    gap = paint(mix(colr, "#000000", 0.28))
    c.drawPath(rrect(22, 0, 66, 13, 4), p)                    # sleeve cuff
    c.drawPath(rrect(14, 16, 74, 60, 17), p)                  # back of the hand
    c.drawPath(rrect(0, 20, 20, 50, 9), p)                    # thumb
    for cx_, cy_ in ((48, 59), (60, 56), (71, 50)):           # curled fingers
        c.drawPath(oval(cx_, cy_, 8.5, 8.5), p)
    c.drawPath(rrect(20, 44, 40, 100, 10), gap)                # index finger (darker edge keeps it readable)
    c.drawPath(rrect(22, 44, 38, 98, 8), p)
    c.restore()


def plane_icon(c, x, y, s, colr):
    """vector ✈-style send icon; (x,y) = centre, s = height"""
    c.save(); c.translate(x, y); c.rotate(-28)
    paper_plane(c, 0, 0, s * 0.55, 0, fill=colr, fold=mix(colr, "#000000", 0.35))
    c.restore()
