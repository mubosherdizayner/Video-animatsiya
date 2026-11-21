# Muted silhouette people (18th-century Paris, chefs, crowd) — flat shapes, no outlines.
import math
from common import *

def person(cv, x, y, h, col, walk=0.0, phase=0.0, face=1, hunch=0.0, hat=None, hat_col=None,
           skirt=False, carry=None, carry_col=None, flag=None, arm=None, alpha=255):
    """x,y = feet center (world coords of the current layer); h = height"""
    c = col + (alpha,) if alpha < 255 else col
    s = h / 100.0
    def P(px, py): return (x + face * px * s, y + py * s)
    th = math.radians(24) * walk * math.sin(phase)
    hip = (0, -46 + 46 * (1 - math.cos(th)) * 0.3)
    hun = math.radians(28 * hunch)
    def up(px, py):
        # rotate upper body around hip by hunch (forward = +x)
        dx, dy = px - hip[0], py - hip[1]
        return (hip[0] + dx * math.cos(hun) - dy * math.sin(hun), hip[1] + dx * math.sin(hun) + dy * math.cos(hun))
    # legs
    for k, a in enumerate((th, -th)):
        if skirt: break
        fx, fy = hip[0] + 46 * math.sin(a), 0
        cv.capsule(P(*hip), P(fx, fy - 3), 4.2 * s, 3.8 * s, c)
        cv.poly([P(fx - 4, -6), P(fx + 8, -5), P(fx + 9, 0), P(fx - 4, 0)], c)
    # body (coat / dress)
    if skirt:
        body = [up(-9, -80), up(9, -80), up(11, -52), (16 + 3 * math.sin(phase) * walk, 0), (-16 + 3 * math.sin(phase) * walk, 0), up(-11, -52)]
    else:
        flare = 3 * walk * math.sin(phase * 2)
        body = [up(-9, -80), up(10, -80), up(12, -50), (14 + flare, -26), (-14 + flare, -26), up(-11, -50)]
    cv.poly([P(*p) for p in body], c)
    # head + neck
    hc = up(1.5, -90)
    cv.capsule(P(*up(0, -80)), P(*up(0.5, -85)), 3.6 * s, 3.4 * s, c)
    cv.circle(*P(*hc), 8.2 * s, c)
    # arms
    sw = 20 * walk * math.sin(phase + math.pi)
    if arm is None:
        hand = up(4 + sw * 0.6, -48)
        elbow = up(1 + sw * 0.25, -63)
    else:
        elbow, hand = up(*arm[0]), up(*arm[1])
    sh = up(0, -77)
    cv.capsule(P(*sh), P(*elbow), 3.8 * s, 3.4 * s, c)
    cv.capsule(P(*elbow), P(*hand), 3.4 * s, 3.0 * s, c)
    # hats
    if hat == "tricorn":
        hp = up(1.5, -97)
        cv.poly([P(hp[0] - 12, hp[1] + 2), P(hp[0] + 12, hp[1] + 2), P(hp[0] + 8, hp[1] - 4), P(hp[0], hp[1] - 9), P(hp[0] - 8, hp[1] - 4)], c)
    elif hat == "toque":
        hcol = (hat_col or MTN1) + ((alpha,) if alpha < 255 else ())
        hp = up(1.5, -96)
        cv.rect(*P(hp[0] - 7, hp[1] - 2), *P(hp[0] + 7, hp[1] + 3), hcol) if face > 0 else cv.rect(*P(hp[0] + 7, hp[1] - 2), *P(hp[0] - 7, hp[1] + 3), hcol)
        cv.poly([P(hp[0] - 7, hp[1]), P(hp[0] + 7, hp[1]), P(hp[0] + 9, hp[1] - 17), P(hp[0] - 9, hp[1] - 17)], hcol)
        for dx in (-6, 0, 6):
            cv.circle(*P(hp[0] + dx, hp[1] - 18), 5.2 * s, hcol)
    elif hat == "bonnet":
        hp = up(1.5, -92)
        cv.circle(*P(hp[0] - 2, hp[1] - 3), 9.5 * s, c)
    # carried things
    if carry == "bundle":
        cc = (carry_col or HOUSE) + ((alpha,) if alpha < 255 else ())
        b = up(-6, -66)
        cv.poly(ellipse_pts(*P(*b), 11 * s, 9 * s, 14), cc)
        cv.poly([P(b[0] - 3, b[1] - 9), P(b[0] + 3, b[1] - 9), P(b[0] + 1, b[1] - 14), P(b[0] - 1, b[1] - 14)], cc)
    if flag is not None:
        fcol, fph, kind = flag
        hand = up(6, -70)
        top = (hand[0] + 2, hand[1] - 58)
        cv.line([P(*hand), P(*top)], c, 1.8 * s)
        if kind == "banner":
            pts_t = [P(top[0] - 26 + j * 4, top[1] + 2 + 2.5 * math.sin(fph + j * 0.6)) for j in range(14)]
            pts_b = [P(top[0] - 26 + j * 4, top[1] + 16 + 2.5 * math.sin(fph + j * 0.6)) for j in range(14)][::-1]
        else:
            pts_t = [P(top[0] + j * 3.2, top[1] + 2 * math.sin(fph + j * 0.7) * (j / 8)) for j in range(9)]
            pts_b = [P(top[0] + j * 3.2, top[1] + 15 + 2 * math.sin(fph + j * 0.7) * (j / 8)) for j in range(9)][::-1]
        cv.poly(pts_t + pts_b, fcol + ((alpha,) if alpha < 255 else ()))

def seated(cv, x, y, h, col, hunch=0.0, sip=0.0, face=1):
    """seated cafe customer at a little round table (x,y = floor under the chair)"""
    s = h / 100.0
    def P(px, py): return (x + face * px * s, y + py * s)
    hun = math.radians(30 * hunch)
    hip = (0, -38)
    def up(px, py):
        dx, dy = px - hip[0], py - hip[1]
        return (hip[0] + dx * math.cos(hun) - dy * math.sin(hun), hip[1] + dx * math.sin(hun) + dy * math.cos(hun))
    # chair
    cv.rect(*P(-12, -40), *P(-9, 0), col) if face > 0 else cv.rect(*P(-9, -40), *P(-12, 0), col)
    cv.line([P(-12, -38), P(6, -38)], col, 2.5 * s)
    cv.line([P(-12, -64), P(-12, -38)], col, 2.5 * s)
    # legs (thigh forward, shin down)
    cv.capsule(P(-2, -38), P(14, -38), 5 * s, 4.5 * s, col)
    cv.capsule(P(14, -38), P(16, -2), 4.2 * s, 3.8 * s, col)
    # torso + head
    body = [up(-8, -40), up(8, -40), up(9, -66), up(-7, -68)]
    cv.poly([P(*p) for p in body], col)
    cv.circle(*P(*up(1.5, -77)), 7.5 * s, col)
    # table
    tx = 30
    cv.poly(ellipse_pts(*P(tx, -44), 13 * s, 2.6 * s, 16), col)
    cv.rect(*P(tx - 1.2, -44), *P(tx + 1.2, 0), col) if face > 0 else cv.rect(*P(tx + 1.2, -44), *P(tx - 1.2, 0), col)
    cv.poly(ellipse_pts(*P(tx, -1), 7 * s, 1.6 * s, 12), col)
    # arm with tiny cup: rests on table (sip=0) -> at mouth (sip=1)
    sh = up(1, -64)
    hand = (lerp(tx - 6, up(8, -73)[0], sip), lerp(-47, up(8, -73)[1], sip))
    elbow = (lerp(12, up(10, -56)[0], sip), lerp(-50, up(12, -56)[1], sip))
    cv.capsule(P(*sh), P(*elbow), 3.4 * s, 3.1 * s, col)
    cv.capsule(P(*elbow), P(*hand), 3.1 * s, 2.8 * s, col)
    cv.rect(*P(hand[0] - 2.5, hand[1] - 4), *P(hand[0] + 2.5, hand[1] + 1), col) if face > 0 else cv.rect(*P(hand[0] + 2.5, hand[1] - 4), *P(hand[0] - 2.5, hand[1] + 1), col)
    if sip < 0.5:
        cv.rect(*P(tx + 3, -50), *P(tx + 7, -45), col) if face > 0 else cv.rect(*P(tx + 7, -50), *P(tx + 3, -45), col)

def seated_cross(cv, x, y, h, col, sip=0.0, nod=0.0, face=1, hat=None):
    """customer sitting cross-legged on a tapchan (x,y = seat point); sip lifts a piala to the mouth"""
    s = h / 100.0
    def P(px, py): return (x + face * px * s, y + py * s)
    # folded legs
    cv.poly(ellipse_pts(*P(4, -8), 30 * s, 9 * s, 18), col)
    # torso (slight lean toward the table)
    lean = 6 + 3 * nod
    body = [P(-12, -10), P(14, -10), P(13 + lean * 0.6, -52), P(-6 + lean * 0.6, -58)]
    cv.poly(body, col)
    hc = P(4 + lean * 0.8 + 2 * nod, -68 + 2 * nod)
    cv.capsule(P(2 + lean * 0.6, -55), hc, 4.2 * s, 4 * s, col)
    cv.circle(*hc, 9.5 * s, col)
    if hat == "doppi":
        cv.rect(hc[0] - 9.5 * s, hc[1] - 13 * s, hc[0] + 9.5 * s, hc[1] - 5 * s, col)
    elif hat == "rumol":
        cv.poly([(hc[0] - 11 * s, hc[1] + 6 * s), (hc[0] - 11 * s, hc[1] - 6 * s), (hc[0], hc[1] - 12 * s),
                 (hc[0] + 11 * s, hc[1] - 6 * s), (hc[0] + 13 * s, hc[1] + 14 * s), (hc[0] - 14 * s, hc[1] + 16 * s)], col)
    # arm: rests on the knee (sip=0) -> piala at the mouth (sip=1)
    sh = P(6 + lean * 0.6, -50)
    hand = P(lerp(26, 14 + lean, sip), lerp(-14, -64, sip))
    elbow = P(lerp(20, 24, sip), lerp(-30, -46, sip))
    cv.capsule(sh, elbow, 3.6 * s, 3.2 * s, col)
    cv.capsule(elbow, hand, 3.2 * s, 3.0 * s, col)
    cv.poly(ellipse_pts(hand[0] + face * 3 * s, hand[1] - 3 * s, 4.2 * s, 3 * s, 10), col)

def cook(cv, x, y, h, col, stir=0.0, face=1):
    """oshpaz standing at the qozon with a long kapgir (ladle); stir in 0..1 cycles the ladle"""
    s = h / 100.0
    def P(px, py): return (x + face * px * s, y + py * s)
    for dx in (-5, 5):
        cv.capsule(P(dx, -44), P(dx * 1.1, -3), 4.4 * s, 4.0 * s, col)
    cv.poly([P(-11, -82), P(12, -82), P(16, -30), P(-15, -30)], col)
    hc = P(3, -92)
    cv.circle(*hc, 8.6 * s, col)
    cv.poly([P(-5, -99), P(9, -99), P(10, -112), P(-6, -112)], col)     # cook's cap
    cv.circle(*P(2, -113), 8 * s, col)
    a = 2 * math.pi * stir
    hand = P(30 + 6 * math.cos(a), -58 + 3 * math.sin(a))
    cv.capsule(P(4, -76), P(18, -62), 3.8 * s, 3.4 * s, col)
    cv.capsule(P(18, -62), hand, 3.4 * s, 3.0 * s, col)
    tip = (hand[0] + face * 34 * s + face * 8 * s * math.cos(a), hand[1] + 44 * s)
    cv.line([hand, tip], col, 2.6 * s)
    cv.poly(ellipse_pts(tip[0], tip[1], 7 * s, 3.5 * s, 10), col)
