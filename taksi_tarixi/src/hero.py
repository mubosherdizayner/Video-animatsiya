# The hero: green satin ikat chapan, red sash, black Chust doppi with white pepper motifs.
# Design units: standing height 600, feet at y=0, facing +x. Drawn with gfx.Pen (scale/flip/rotate).
import math
from PIL import Image
from gfx import Pen, hx, catmull, capsule_pts, rot, SS

C = dict(SKIN=hx('#EBC8A2', 255), SKIN_D=hx('#D8B089', 255), HAIR=hx('#2E231D', 255), EYE=hx('#15191A', 255),
         CH=hx('#3F7B61', 255), CH_D=hx('#2F634D', 255), CH_L=hx('#4C8A6E', 255), IK1=hx('#6FA586', 255),
         IK2=hx('#C7A548', 255), GOLD=hx('#BE8642', 255), GOLD_D=hx('#9C6C35', 255), SASH=hx('#B4473B', 255),
         SASH_D=hx('#973A31', 255), COLLAR=hx('#E8E1D3', 255), DOPPI=hx('#1D2427', 255), WHITE=hx('#F1EEE6', 255),
         BOOT=hx('#33241E', 255), BOOT_D=hx('#281C17', 255))
NONE = (0, 0, 0, 0)
HIDE = False          # QA only: render a frame without the hero to measure the environment's saturation
CHAPAN_KEYS = ('CH', 'CH_D', 'CH_L', 'IK1', 'IK2', 'GOLD', 'GOLD_D')


def _rot_ellipse(cx, cy, ra, rb, ang, n=28):
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        x, y = ra * math.cos(a), rb * math.sin(a)
        pts.append((cx + x * math.cos(ang) - y * math.sin(ang), cy + x * math.sin(ang) + y * math.cos(ang)))
    return pts


def dirv(a_deg):
    a = math.radians(a_deg); return (math.sin(a), math.cos(a))


def arm_points(S, a1, e, L1=118, L2=104):
    d1 = dirv(a1); E = (S[0] + L1 * d1[0], S[1] + L1 * d1[1])
    d2 = dirv(a1 + e); Wr = (E[0] + L2 * d2[0], E[1] + L2 * d2[1])
    return E, Wr, d2


def draw_hand(p, Wr, d, kind, col):
    if HIDE: return
    n = (-d[1], d[0])
    ang = math.atan2(d[1], d[0])
    if kind == 'point':
        c = (Wr[0] + d[0] * 12, Wr[1] + d[1] * 12)
        p.poly(_rot_ellipse(c[0], c[1], 16, 13, ang), col)
        p.capsule((Wr[0] + d[0] * 18, Wr[1] + d[1] * 18), (Wr[0] + d[0] * 50, Wr[1] + d[1] * 50), 10, 8.5, col)
        p.capsule((c[0] + n[0] * 9, c[1] + n[1] * 9), (c[0] + n[0] * 11 + d[0] * 12, c[1] + n[1] * 11 + d[1] * 12), 8, 7, col)
    elif kind == 'fist':
        c = (Wr[0] + d[0] * 12, Wr[1] + d[1] * 12)
        p.poly(_rot_ellipse(c[0], c[1], 16, 14, ang), col)
    elif kind == 'flat':      # open palm, fingers together (raised hand / gesture)
        c = (Wr[0] + d[0] * 20, Wr[1] + d[1] * 20)
        p.poly(_rot_ellipse(c[0], c[1], 24, 12, ang), col)
        p.capsule((Wr[0] + n[0] * 8 + d[0] * 6, Wr[1] + n[1] * 8 + d[1] * 6),
                  (Wr[0] + n[0] * 18 + d[0] * 18, Wr[1] + n[1] * 18 + d[1] * 18), 8, 7, col)
    else:                     # relaxed open hand
        c = (Wr[0] + d[0] * 15, Wr[1] + d[1] * 15)
        p.poly(_rot_ellipse(c[0], c[1], 18, 13, ang), col)
        p.capsule((Wr[0] + n[0] * 9, Wr[1] + n[1] * 9), (Wr[0] + n[0] * 13 + d[0] * 14, Wr[1] + n[1] * 13 + d[1] * 14), 8, 7, col)


def draw_arm(p, S, a1, e, hand='open', back=False, cm=C, w=1.0):
    E, Wr, d2 = arm_points(S, a1, e)
    if HIDE: return Wr, d2
    sl = cm['CH_D'] if back else cm['CH']
    cuff = cm['GOLD_D'] if back else cm['GOLD']
    skin = cm['SKIN_D'] if back else cm['SKIN']
    p.capsule(S, E, 50 * w, 45 * w, sl)
    C0 = (Wr[0] - d2[0] * 2, Wr[1] - d2[1] * 2)
    p.capsule(E, C0, 45 * w, 50 * w, sl)
    if not back:   # light satin highlight along the sleeve top
        d1 = ((E[0] - S[0]) / 118, (E[1] - S[1]) / 118); n1 = (d1[1], -d1[0])
        p.capsule((S[0] + n1[0] * 13 + d1[0] * 10, S[1] + n1[1] * 13 + d1[1] * 10), (E[0] + n1[0] * 12, E[1] + n1[1] * 12), 9, 8, cm['CH_L'])
    p.capsule((Wr[0] - d2[0] * 16, Wr[1] - d2[1] * 16), C0, 50 * w, 52 * w, cuff)
    Wh = (Wr[0] + d2[0] * 2, Wr[1] + d2[1] * 2)
    draw_hand(p, Wh, d2, hand, skin)
    return Wh, d2


def pepper(p, cx, cy, s, col, flip=1):
    """white qalampir (pepper) motif of the Chust doppi"""
    left, right = [], []
    N = 9
    for k in range(N + 1):
        t = k / N
        x = cx + flip * s * (5 * math.sin(math.pi * t * 0.95) - 4 * t)
        y = cy - s * 24 * t
        w = s * 5.2 * math.sin(math.pi * min(1, t * 1.05)) ** 0.7 * (1 - 0.35 * t) + 0.4
        left.append((x - w, y)); right.append((x + w, y))
    p.poly(left + right[::-1], col)
    p.circle(cx + flip * s * (-3.4), cy - s * 26.5, s * 2.3, col)


STAND_CHAPAN = [(-44, -466), (-58, -432), (-61, -380), (-61, -320), (-70, -220), (-82, -120), (-74, -112),
                (60, -110), (68, -118), (58, -220), (50, -320), (53, -382), (47, -440), (30, -468), (0, -475)]
SIT_CHAPAN = [(-44, -166), (-58, -132), (-61, -80), (-62, -22), (-70, 8), (-50, 28), (40, 34), (96, 42), (112, 76),
              (116, 124), (176, 124), (172, 60), (162, 12), (142, -12), (100, -22), (52, -22), (53, -82), (47, -140), (30, -168), (0, -175)]
HEAD = [(-30, -530), (-27, -552), (-10, -566), (14, -566), (32, -552), (38, -535), (40, -524), (46, -514), (41, -508),
        (40, -498), (36, -487), (24, -479), (8, -477), (-4, -484), (-18, -494), (-28, -508)]


def draw_hero(p, pose=None, cm=C):
    """pose keys: mode('stand'|'sit'), fa=(a1,e,hand) front arm, ba=(a1,e,hand) back arm, nod (deg), turn (0..1),
    walk (phase rad or None), breathe (0..1), arms (False to skip arms)."""
    pose = pose or {}
    if HIDE: return {}
    mode = pose.get('mode', 'stand')
    dy = 300 if mode == 'sit' else 0             # upper body offset (sit: hips at y=0)
    br = pose.get('breathe', 0.0) * 2.0
    up = lambda pts: [(x, y + dy - br * (1 if y < -330 else 0)) for x, y in pts]
    S_f = (2, -452 + dy - br); S_b = (-14, -452 + dy - br)
    fa = pose.get('fa', (8, 14, 'open')); ba = pose.get('ba', (-6, 10, 'open'))
    turn = pose.get('turn', 0.0); nod = pose.get('nod', 0.0)
    # 1 back arm
    if pose.get('arms', True) and ba: draw_arm(p, S_b, ba[0], ba[1], ba[2], back=True, cm=cm)
    # 2 boots
    if mode == 'stand':
        ph = pose.get('walk')
        sw = 20 * math.sin(ph) if ph is not None else 0
        lift_f = max(0, math.sin(ph + math.pi / 2)) * 8 if ph is not None else 0
        lift_b = max(0, -math.sin(ph + math.pi / 2)) * 8 if ph is not None else 0
        for ox, lift, col in ((-14 - sw, lift_b, cm['BOOT_D']), (12 + sw, lift_f, cm['BOOT'])):
            shaft = [(ox - 22, -132), (ox + 10, -132), (ox + 12, -40), (ox - 20, -40)]
            foot = [(ox - 24, -50), (ox + 10, -50), (ox + 34, -34), (ox + 40, -12), (ox + 38, 0), (ox - 24, 0)]
            p.poly([(x, y - lift) for x, y in shaft], col); p.smooth([(x, y - lift) for x, y in foot], col, 4)
    else:
        for ox, col in ((-10, cm['BOOT_D']), (10, cm['BOOT'])):
            p.capsule((128 + ox, 60), (134 + ox, 196), 34, 32, col)
            p.smooth([(114 + ox, 186), (146 + ox, 184), (172 + ox, 200), (176 + ox, 214), (112 + ox, 216)], col, 4)
    # 3 chapan body
    body = up(STAND_CHAPAN) if mode == 'stand' else [(x, y - (br if y < -30 else 0)) for x, y in SIT_CHAPAN]
    bpts = catmull(body, 5)
    p.poly(bpts, cm['CH'])
    # shadow along the back, light along the chest (flat bands, clipped by drawing inside the body)
    if mode == 'stand':
        p.smooth(up([(-44, -462), (-58, -430), (-61, -320), (-72, -210), (-80, -124), (-56, -118), (-46, -230), (-42, -330), (-40, -440)]), cm['CH_D'], 4)
        p.smooth(up([(26, -462), (44, -440), (50, -382), (46, -340), (34, -380), (30, -440)]), cm['CH_L'], 4)
    else:
        p.smooth([(-44, -162), (-58, -130), (-62, -22), (-68, 6), (-46, 22), (-42, -30), (-40, -140)], cm['CH_D'], 4)
        p.smooth([(26, -162), (44, -140), (50, -82), (46, -40), (34, -80), (30, -140)], cm['CH_L'], 4)
        p.smooth([(60, -18), (120, -14), (152, -2), (120, 4), (60, 2)], cm['CH_L'], 4)
    # ikat rhombus columns, clipped to the body
    pat = Pen(p.w, p.h, p.s, p.ox, p.oy, p.fx < 0, math.degrees(p.r), ss=p.ss)
    y_top, y_bot = (-462, -112) if mode == 'stand' else (-162, 126)
    for k, xc in enumerate(range(-64, 196, 22)):
        col = cm['IK2'] if k % 2 else cm['IK1']
        if col[3] == 0: continue
        off = 15 if k % 2 else 0
        y = y_top + off
        while y < y_bot + 20:
            pat.poly([(xc, y - 11), (xc + 6.5, y), (xc, y + 11), (xc - 6.5, y)], col)
            pat.rect(xc - 1.6, y + 11, xc + 1.6, y + 19, col)
            y += 30
        if mode == 'sit':   # ikat over the thigh runs along the thigh
            pass
    mk = Pen(p.w, p.h, p.s, p.ox, p.oy, p.fx < 0, math.degrees(p.r), mode='L', ss=p.ss)
    mk.poly(bpts, 255)
    pal = pat.im.getchannel('A'); from PIL import ImageChops
    pat.im.putalpha(ImageChops.multiply(pal, mk.im))
    p.im.alpha_composite(pat.im)
    # gold trim: hem + front edge
    if mode == 'stand':
        p.poly(up([(-81, -124), (-74, -113), (60, -111), (67, -117), (66, -127), (-79, -136)]), cm['GOLD'])
        edge = up([(28, -466), (44, -440), (50, -382), (47, -320), (55, -220), (64, -118)])
        p.line(edge, cm['GOLD'], 9)
    else:
        p.poly([(116, 112), (176, 112), (176, 124), (116, 124)], cm['GOLD'])
        p.line([(28, -166), (44, -140), (50, -82), (50, -24), (100, -20), (148, -6), (166, 30), (172, 120)], cm['GOLD'], 9)
    # sash
    sy = -322 + dy
    sash = [(-60, sy - 15), (-20, sy - 17), (20, sy - 18), (50, sy - 18), (51, sy + 14), (20, sy + 16), (-20, sy + 17), (-60, sy + 15)]
    p.poly(sash, cm['SASH'])
    p.poly([(34, sy + 6), (52, sy + 8), (58, sy + 52), (44, sy + 56)], cm['SASH_D'])
    p.poly([(40, sy + 2), (52, sy + 4), (64, sy + 44), (52, sy + 48)], cm['SASH'])
    # neck + collar
    p.poly(up([(-4, -494), (22, -494), (27, -462), (-8, -462)]), cm['SKIN_D'])
    p.smooth(up([(4, -474), (30, -476), (40, -462), (28, -452), (8, -458)]), cm['COLLAR'], 3)
    # head (nod rotates around the neck)
    piv = (8, -484 + dy - br)
    R = lambda pts: [rot((x, y + dy - br), math.radians(nod), piv) for x, y in pts]
    head = [(x - (3 * turn if x > 36 else 0), y) for x, y in HEAD]
    p.smooth(R(head), cm['SKIN'], 5)
    hair = [(-31 + 5 * turn, -538), (-30 + 4 * turn, -512), (-24 + 4 * turn, -498), (-12 + 3 * turn, -490), (-6 - 2 * turn, -500), (-10 - 3 * turn, -522), (-16 - 3 * turn, -542)]
    p.smooth(R(hair), cm['HAIR'], 4)
    ex = 25 - 10 * turn
    p.poly(R(_rot_ellipse(ex, -531, 3.7, 4.7, 0)), cm['EYE'])
    # doppi
    dop = [(-34, -546), (37, -552), (34.5, -590), (30, -598), (-24, -594), (-29.5, -588)]
    p.smooth(R(dop), cm['DOPPI'], 3)
    p.poly(R([(-34.5, -545), (37.5, -551), (37, -559), (-33.6, -553.5)]), cm['WHITE'])
    pepper_pts = []
    pen_tmp = p
    cxp = 3 - 8 * turn
    pepper(_RotPen(p, R), cxp, -561, 1.0, cm['WHITE'])
    pepper(_RotPen(p, R), 31 - 4 * turn, -562, 0.55, cm['WHITE'], flip=-1)
    pepper(_RotPen(p, R), -27 + 3 * turn, -560, 0.5, cm['WHITE'])
    # front arm
    out = {}
    if pose.get('arms', True) and fa:
        out['hand'], out['hand_dir'] = draw_arm(p, S_f, fa[0], fa[1], fa[2], back=False, cm=cm)
    return out


class _RotPen:
    """applies an extra point transform before drawing to the wrapped pen"""
    def __init__(self, p, R): self.p, self.R = p, R
    def poly(self, pts, c): self.p.poly(self.R(pts), c)
    def circle(self, cx, cy, r, c):
        from gfx import circle_pts
        self.p.poly(self.R(circle_pts(cx, cy, r, r, 20)), c)


def hero_sprite(pose, scale, flip=False, pad=(270, 730, 330, 260), cm=C):
    """Render hero into an RGBA sprite. Returns (img, anchor) where anchor is the pixel of design (0,0)."""
    l, t, r, b = pad
    w, h = int((l + r) * scale), int((t + b) * scale)
    ox, oy = (r if flip else l) * scale, t * scale
    p = Pen(w, h, scale, ox, oy, flip)
    info = draw_hero(p, pose, cm)
    return p.result(), (ox, oy), info


def chapan_cmap():
    """color map that keeps only chapan colours (for the 'chapan stays saturated' mask)"""
    cm = {k: (NONE if k not in CHAPAN_KEYS else (255, 255, 255, 255)) for k in C}
    return cm


# ---------------------------------------------------------------- top-down hero (scene 6)
def draw_hero_top(p, arm=0.0, cm=C):
    """seen from above, facing +x: shoulders (chapan), arms forward holding reins, doppi top."""
    if HIDE: return
    # arms (sleeves) forward
    for sgn in (-1, 1):
        S = (0, sgn * 46); E = (60, sgn * 40); Wr = (112 + arm, sgn * 26)
        p.capsule(S, E, 44, 40, cm['CH_D'] if sgn < 0 else cm['CH'])
        p.capsule(E, Wr, 40, 44, cm['CH_D'] if sgn < 0 else cm['CH'])
        p.capsule((Wr[0] - 14, Wr[1]), Wr, 46, 46, cm['GOLD'])
        p.circle(Wr[0] + 14, Wr[1], 14, cm['SKIN'])
    # shoulders / back of chapan
    body = [(-40, -70), (20, -64), (34, -30), (36, 30), (20, 64), (-40, 70), (-58, 40), (-62, 0), (-58, -40)]
    p.smooth(body, cm['CH'], 5)
    for k, yy in enumerate(range(-56, 60, 22)):
        col = cm['IK2'] if k % 2 else cm['IK1']
        for xx in range(-50, 22, 26):
            p.poly([(xx - 10, yy), (xx, yy - 5), (xx + 10, yy), (xx, yy + 5)], col)
    p.smooth([(-60, -30), (-50, -62), (-34, -68), (-44, -30), (-46, 30), (-34, 68), (-50, 62), (-60, 30)], cm['CH_D'], 4)
    p.rect(-6, -68, 4, 68, cm['SASH'])
    # head: doppi from above (square with white border and peppers peeking at the sides)
    p.ellipse(8, 0, 30, 27, cm['SKIN_D'])
    p.circle(36, 0, 6, cm['SKIN'])
    sq = [(-22, -27), (34, -27), (34, 27), (-22, 27)]
    p.smooth([(-24, -29), (36, -29), (36, 29), (-24, 29)], cm['WHITE'], 2)
    p.smooth(sq, cm['DOPPI'], 2)
    for (cx, cy, a) in ((6, -21, 0), (6, 21, 180), (-16, 0, 90), (28, 0, -90)):
        pts = [(-3, 4), (0, -5), (3, 4)]
        p.poly([rot((cx + x, cy + y), math.radians(a), (cx, cy)) for x, y in pts], cm['WHITE'])
    p.rect(4, -1.2, 8, 1.2, cm['WHITE'])
