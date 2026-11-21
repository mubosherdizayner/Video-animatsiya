# Paper plane (Instagram "send" style) and the vector ✈ / 👇 icons.
import math
import skia
from common import *


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
