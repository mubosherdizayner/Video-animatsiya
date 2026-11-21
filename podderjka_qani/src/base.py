# Shared scene utilities: hero wrapper, camera bumps, fist knock state, glass effects.
import math
from common import *
from env import *
from figures import *
from hero import draw_hero, RA
import qahramon as Q

def hero(cv, X, Y, s, **kw):
    cv.layer(1.0)
    return draw_hero(cv, X, Y, s, **kw)

def bump(t, times, amp=10.0, decay=0.09, freq=18.0):
    """damped vertical shake triggered at each time in `times` (0 at the trigger instant)"""
    y = 0.0
    for tk in times:
        u = t - tk
        if 0 <= u < 0.6:
            y += amp * math.exp(-u / decay) * math.sin(2 * math.pi * freq * u)
    return y

def zoom_cam(a, b, e):
    """interpolate (cx, cy, z) with geometric zoom"""
    z = math.exp(lerp(math.log(a[2]), math.log(b[2]), e))
    # keep the interpolation of the centre consistent with the zoom (screen-space feel)
    w = (1 / a[2] - 1 / z) / (1 / a[2] - 1 / b[2]) if abs(a[2] - b[2]) > 1e-6 else e
    return (lerp(a[0], b[0], w), lerp(a[1], b[1], w), z)

# ---------------------------------------------------------------- knocking on the screen glass (scene 1 / loop end)
KNOCK_P = 0.5      # each fist knocks every 0.5 s, fists alternate -> 4 knocks per second
def fist_amt(tl, off):
    u = ((tl - off) % KNOCK_P) / KNOCK_P
    if u < 0.4: return 1 - ease_out(u / 0.4)
    if u < 0.55: return 0.0
    return ease_in((u - 0.55) / 0.45)

def knock_arms(tl):
    aR = fist_amt(tl, 0.0); aL = fist_amt(tl, 0.25)
    def arm(a, sgn):
        e = (sgn * lerp(66, 58, a), lerp(-236, -248, a))
        h = (sgn * lerp(46, 36, a), lerp(-290, -300, a))
        return (e, h)
    return arm(aR, -1), arm(aL, 1), aR, aL

def knock_times(t0, t1):
    out = []
    k = math.ceil(t0 / 0.25 - 1e-9)
    while k * 0.25 <= t1 + 1e-9:
        out.append(k * 0.25); k += 1
    return out

def fist_front(cv, x, y, r):
    """fist seen from the front, pressed toward the glass (screen coords via current layer)"""
    cv.circle(x, y, r, Q.SKIN)
    cv.poly(ellipse_pts(x - r * 0.05, y + r * 0.42, r * 0.82, r * 0.46, 16), Q.SKIN_D + (110,))
    for k in (-0.45, 0.0, 0.45):
        cv.line([(x + k * r - r * 0.12, y - r * 0.25), (x + k * r + r * 0.12, y - r * 0.25)], Q.SKIN_D, r * 0.12)
    cv.line([(x - r * 0.55, y + r * 0.12), (x + r * 0.25, y + r * 0.2)], Q.SKIN_D, r * 0.11)

def glass_glare(cv, xc, alpha=1.0):
    if alpha <= 0.01: return
    def fn(d, tf, k):
        for (off, wdt, a) in ((0, 110, 20), (170, 40, 14)):
            x = xc + off
            pts = [tf(x - wdt / 2 + 700 * 0.42, -50), tf(x + wdt / 2 + 700 * 0.42, -50), tf(x + wdt / 2 - 1300 * 0.42, 2000), tf(x - wdt / 2 - 1300 * 0.42, 2000)]
            d.polygon(pts, fill=(255, 255, 255, int(a * alpha)))
    cv.soft((-700, -60, 1800, 1980), fn, blur=26, scale=0.2)
