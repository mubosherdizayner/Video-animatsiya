# Props as flat silhouettes: taxi + roof sign, horse-drawn cab, taximeter, passengers, pigeons, street furniture.
import math, functools
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from gfx import Pen, hx, catmull, rot, capsule_pts, circle_pts, ACCENT, CREAM, INK, SS, mix
import hero as HR

FONT_XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_B = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FONT_BL = "/usr/share/fonts/opentype/inter/Inter-Black.otf"


@functools.lru_cache(maxsize=64)
def font(path, size): return ImageFont.truetype(path, int(size))


def A(c, a=255): return tuple(c[:3]) + (a,)


# ================================================================ TAXI (side view, faces +x, ground y=0)
TAXI_BODY = [(300, -42), (110, -42), (14, -46), (2, -64), (3, -98), (16, -124), (100, -134), (150, -142), (196, -206), (240, -229), (300, -237),
             (400, -236), (452, -227), (530, -160), (562, -148), (650, -136), (690, -120), (705, -94), (702, -62), (690, -46), (600, -42)]
TAXI_WIN_R = [(206, -204), (244, -223), (316, -228), (316, -160), (194, -160)]
TAXI_WIN_F = [(330, -228), (440, -226), (512, -162), (330, -160)]
TAXI_WHEELS = ((150, -62), (560, -62))
ROOF_MOUNT = (372, -237)


def draw_wheel(p, c, r, ang, tire, rim, hub=None, spokes=5):
    p.circle(c[0], c[1], r, tire)
    p.circle(c[0], c[1], r * 0.62, rim)
    for k in range(spokes):     # dark holes between spokes rotate with the wheel
        a = ang + 2 * math.pi * k / spokes
        pts = []
        for j in range(7):
            aa = a + 0.2 + 0.85 * j / 6
            pts.append((c[0] + r * 0.52 * math.cos(aa), c[1] + r * 0.52 * math.sin(aa)))
        for j in range(7):
            aa = a + 0.2 + 0.85 * (6 - j) / 6
            pts.append((c[0] + r * 0.2 * math.cos(aa), c[1] + r * 0.2 * math.sin(aa)))
        p.poly(pts, tire)
    p.circle(c[0], c[1], r * 0.12, hub or tire)


def draw_taxi(p, pal, wheel_ang=0.0, hero_pose=None, hero=True, point_down=0.0):
    body = A(pal['L'][4]); glass = A(pal['L'][3]); tire = A(mix(pal['L'][4], INK, 0.7)); rim = A(pal['L'][3])
    # glass first, then the hero clipped to the driver window, then the body (window holes are already glass)
    p.poly(TAXI_WIN_R, glass); p.poly(TAXI_WIN_F, glass)
    if hero:
        hp = Pen(p.w, p.h, p.s * 0.5, p.ox + p.s * 402 * p.fx, p.oy + p.s * -88, p.fx < 0, ss=p.ss)
        pose = dict(mode='sit', fa=(62, 30, 'fist'), ba=(60, 34, 'fist'), arms=True)
        if hero_pose: pose.update(hero_pose)
        if point_down > 0: pose['fa'] = None
        HR.draw_hero(hp, pose)
        mk = Pen(p.w, p.h, p.s, p.ox, p.oy, p.fx < 0, mode='L', ss=p.ss); mk.poly(TAXI_WIN_F, 255)
        from PIL import ImageChops
        hp.im.putalpha(ImageChops.multiply(hp.im.getchannel('A'), mk.im))
        p.im.alpha_composite(hp.im)
    # body with window holes: draw body, then re-cut the windows by drawing nothing -> use mask composite
    bp = Pen(p.w, p.h, p.s, p.ox, p.oy, p.fx < 0, ss=p.ss)
    bp.smooth(TAXI_BODY, body, 5)
    bp.poly([(t[0], t[1]) for t in TAXI_WIN_R], (0, 0, 0, 0)); bp.poly(TAXI_WIN_F, (0, 0, 0, 0))
    bp.poly([(316, -230), (330, -230), (330, -158), (316, -158)], body)                 # B pillar
    bp.poly([(518, -160), (546, -164), (548, -146), (522, -146)], body)                 # mirror
    bp.rrect(684, -110, 703, -92, 5, A(pal['L'][3]))                                   # headlight
    bp.rrect(2, -112, 14, -94, 4, A(pal['L'][3]))                                      # tail light
    for c in TAXI_WHEELS: draw_wheel(bp, c, 64, wheel_ang, tire, rim, A(pal['L'][4]))
    p.im.alpha_composite(bp.im)
    if point_down > 0:   # arm out of the window pointing down
        a = 20 + 15 * (1 - point_down)
        S = (402 + 8 * 0.5, -88 - 150 * 0.5 + 0)
        hp = Pen(p.w, p.h, p.s * 0.5, p.ox + p.s * 402 * p.fx, p.oy + p.s * -88, p.fx < 0, ss=p.ss)
        pd = point_down
        HR.draw_arm(hp, (4, -152), 62 + 12 * pd, 30 - 96 * pd, 'point' if pd > 0.5 else 'fist')
        p.im.alpha_composite(hp.im)


def taxi_sprite(scale, pal, wheel_ang=0.0, hero_pose=None, hero=True, point_down=0.0, flip=False):
    """returns (img, anchor_px of design origin (rear bottom at ground))"""
    padl, padt, padr, padb = 40, 330, 760, 30
    w, h = int((padl + padr) * scale), int((padt + padb) * scale)
    p = Pen(w, h, scale, padl * scale, padt * scale, flip)
    draw_taxi(p, pal, wheel_ang, hero_pose, hero, point_down)
    return p.result(), (padl * scale, padt * scale)


@functools.lru_cache(maxsize=8)
def roof_sign(scale, glow=0.0):
    """TAKSI roof sign: rounded accent pill with cream letters. Returns RGBA, centre-bottom anchor."""
    w, h = 128 * scale, 46 * scale
    pad = int(10 * scale)
    im = Image.new('RGBA', (int(w + 2 * pad), int(h + 2 * pad + 8 * scale)), (0, 0, 0, 0))
    p = Pen(im.width, im.height, scale, pad, pad)
    p.rrect(0, 0, 128, 46, 20, A(ACCENT))
    p.rect(40, 46, 88, 54, A(mix(ACCENT, INK, 0.45)))     # small base foot
    im = p.result()
    d = ImageDraw.Draw(im)
    f = font(FONT_XB, 27 * scale)
    tw = d.textlength("TAKSI", font=f)
    d.text((im.width / 2 - tw / 2, pad + 23 * scale), "TAKSI", font=f, fill=A(CREAM), anchor='lm')
    return im


# ================================================================ HORSE + CAB (side view, faces +x, ground y=0)
def leg_pts(top, a1, bend, L1, L2, w_top, front):
    d1 = (math.sin(math.radians(a1)), math.cos(math.radians(a1)))
    K = (top[0] + L1 * d1[0], top[1] + L1 * d1[1])
    a2 = a1 - bend if front else a1 + bend * 0.6
    d2 = (math.sin(math.radians(a2)), math.cos(math.radians(a2)))
    F = (K[0] + L2 * d2[0], K[1] + L2 * d2[1])
    return K, F, d2


def draw_horse(p, col, col_far, phase=0.0, walking=True, head=0.0, tail=0.0, shake=0.0):
    """phase: gait cycles (float). head: nod deg. shake: head shake amount (0..1)."""
    def leg(top, ph, front, c):
        s = math.sin(2 * math.pi * ph); cc = math.cos(2 * math.pi * ph)
        a1 = (16 * s if walking else 0) + (4 if front else -3)
        bend = (46 * max(0, cc) ** 1.3 if walking else 4)
        L1, L2 = (150, 140) if front else (165, 135)
        K, F, d2 = leg_pts(top, a1, bend, L1, L2, 50, front)
        p.capsule(top, K, 58 if not front else 50, 30, c)
        p.capsule(K, F, 26, 20, c)
        # hoof
        hf = (F[0] + d2[0] * 18, F[1] + d2[1] * 18)
        p.poly([(F[0] - 14, F[1] + 4), (F[0] + 14, F[1] + 4), (hf[0] + 18, hf[1] + 6), (hf[0] - 14, hf[1] + 6)], c)
    gy = 0
    # far legs (lighter), then body, then near legs
    leg((130, -320), phase + 0.5, False, col_far); leg((475, -315), phase + 0.75, True, col_far)
    # tail
    tw = 10 * math.sin(tail)
    p.poly(catmull([(70, -440), (40, -430), (18 + tw, -330), (6 + tw * 1.6, -230), (26 + tw * 1.4, -238), (48 + tw, -340), (80, -410)], 5), col)
    body = [(60, -435), (140, -458), (300, -447), (425, -455), (498, -478), (548, -440), (566, -365), (536, -292),
            (430, -276), (250, -270), (120, -290), (62, -330), (44, -390)]
    p.smooth(body, col, 5)
    # neck + head (rotates around the withers for nod / shake)
    piv = (520, -450)
    ang = math.radians(head + 9 * shake)
    R = lambda pts: [rot(q, ang, piv) for q in pts]
    neck = [(468, -470), (530, -560), (590, -650), (628, -682), (660, -672), (650, -600), (600, -500), (566, -400), (520, -420)]
    p.smooth(R(neck), col, 5)
    hd = [(622, -690), (648, -700), (690, -660), (742, -598), (766, -566), (758, -542), (728, -538), (690, -560), (650, -598), (624, -640)]
    p.smooth(R(hd), col, 5)
    p.poly(R([(626, -688), (634, -730), (648, -694)]), col)          # ear
    p.poly(R([(612, -680), (614, -718), (630, -688)]), col_far)
    # mane flick
    p.poly(R([(470, -472), (520, -548), (586, -652), (600, -640), (540, -540), (492, -460)]), col)
    leg((105, -330), phase, False, col); leg((500, -320), phase + 0.25, True, col)
    return R([(744, -566)])[0]       # mouth point (for reins)


def spoked_wheel(p, c, r, ang, col, spokes=12):
    p.poly(circle_pts(c[0], c[1], r, r, 64) , col)
    # punch holes between spokes with transparent wedges
    for k in range(spokes):
        a = ang + 2 * math.pi * k / spokes
        pts = []
        da = 2 * math.pi / spokes
        sw = 0.07 * 12 / spokes
        for j in range(6):
            aa = a + sw + (da - 2 * sw) * j / 5
            pts.append((c[0] + (r - 13) * math.cos(aa), c[1] + (r - 13) * math.sin(aa)))
        for j in range(6):
            aa = a + sw * 2.2 + (da - 4.4 * sw) * (5 - j) / 5
            pts.append((c[0] + 22 * math.cos(aa), c[1] + 22 * math.sin(aa)))
        p.poly(pts, (0, 0, 0, 0))


METER_BOX = (-268, -378, -164, -268)   # x0,y0,x1,y1 above the front wheel
METER_DIAL = (-216, -334, 30)


def draw_meter_on_cab(p, col, lid, t, needle=0.0, roll=0.0, scale_hint=1.0):
    x0, y0, x1, y1 = METER_BOX
    p.rect(x0 + 40, y1 - 4, x0 + 64, y1 + 30, col)                    # bracket down to the axle mount
    p.rrect(x0, y0, x1, y1, 10, col)
    p.rect(x0 + 6, y0 + 4, x1 - 6, y0 + 12, lid)
    cx, cy, r = METER_DIAL
    p.circle(cx, cy, r, A(CREAM))
    a = math.radians(-130 + 260 * (needle % 1.0))
    p.capsule((cx, cy), (cx + (r - 7) * math.sin(a), cy - (r - 7) * math.cos(a)), 5, 3, A(INK))
    p.circle(cx, cy, 4, A(ACCENT))
    # rolling digit wheels (accent strips only, never legible)
    for k in range(4):
        xx = x0 + 22 + k * 16
        p.rrect(xx, y1 - 30, xx + 12, y1 - 12, 3, A(mix(col, INK, 0.5)))
        ph = (roll * (1 + k * 0.7) + k * 0.37) % 1.0
        hgt = 6 + 5 * abs(math.sin(math.pi * ph))
        p.rrect(xx + 2, y1 - 21 - hgt / 2, xx + 10, y1 - 21 + hgt / 2, 2, A(ACCENT))


def draw_cab(p, pal, phase=0.0, wheel_ang=0.0, walking=True, hero_pose=None, meter=None, head=0.0, shake=0.0,
             hero=True, tail=0.0, sign=None):
    col = A(pal['L'][4]); far = A(mix(pal['L'][4], pal['L'][3], 0.45)); lid = A(pal['L'][3])
    # rear wheel far side + far shaft (lighter, behind)
    p.line([(-170, -318), (120, -340), (420, -370)], far, 12)
    # horse
    mouth = draw_horse(p, col, far, phase, walking, head, tail, shake)
    # carriage body
    hood = [(-892, -470), (-900, -560), (-870, -640), (-800, -676), (-720, -680), (-660, -650), (-636, -590), (-640, -470)]
    p.smooth(hood, col, 5)
    p.smooth([(-640, -476), (-636, -590), (-660, -646), (-700, -664), (-692, -600), (-676, -530), (-666, -476)], A(mix(pal['L'][4], pal['L'][3], 0.55)), 4)
    tub = [(-900, -480), (-908, -400), (-880, -320), (-820, -284), (-700, -276), (-600, -292), (-520, -330), (-460, -344),
           (-400, -330), (-362, -300), (-344, -330), (-352, -380), (-400, -420), (-480, -440), (-560, -452), (-640, -470), (-660, -486)]
    p.smooth(tub, col, 4)
    p.line([(-892, -436), (-700, -428), (-560, -412), (-430, -382)], A(mix(pal['L'][4], pal['L'][3], 0.5)), 7)
    p.rrect(-404, -612, -380, -572, 6, col); p.poly([(-400, -572), (-384, -572), (-392, -548)], col)   # coach lamp
    # box struts + driver's box + footboard + dash
    p.capsule((-352, -540), (-330, -300), 16, 16, col)
    p.capsule((-236, -540), (-262, -300), 16, 16, col)
    p.rrect(-372, -575, -214, -534, 10, col)
    p.rrect(-380, -600, -360, -540, 6, col)                    # box back rest
    p.line([(-214, -346), (-108, -356)], col, 14)
    p.line([(-108, -356), (-92, -420), (-96, -470)], col, 10)
    # near shaft + traces
    p.line([(-170, -300), (140, -322), (440, -356)], col, 13)
    # wheels (front small, rear big)
    spoked_wheel(p, (-206, -120), 120, wheel_ang * 1.33, col)
    spoked_wheel(p, (-730, -164), 164, wheel_ang, col)
    if meter is not None:
        draw_meter_on_cab(p, col, lid, 0, meter.get('needle', 0.0), meter.get('roll', 0.0))
    # hero on the box
    hand = None
    if hero:
        pose = dict(mode='sit', fa=(48, 38, 'fist'), ba=(44, 44, 'fist'))
        if hero_pose: pose.update(hero_pose)
        info = hero_on(p, -300, -568, 0.98, pose)
        if 'hand' in info and pose.get('reins', True):
            hx_, hy_ = info['hand']
            hand = (-300 + hx_ * 0.98, -568 + hy_ * 0.98)
            p.line([(hand[0] + 10, hand[1] + 6), (mouth[0] - 300, mouth[1] + 80), mouth], A(mix(pal['L'][4], INK, 0.3)), 5)
    return mouth


def hero_on(p, ox_d, oy_d, s_rel, pose, box=(-170, -360, 300, 250)):
    """draw the hero into a small sub-pen around him and composite it into parent pen p"""
    s = p.s * s_rel
    hx_, hy_ = p.ox + p.s * ox_d * p.fx, p.oy + p.s * oy_d
    xa, xb = sorted((hx_ + box[0] * s * p.fx, hx_ + box[2] * s * p.fx))
    x0, x1 = max(0, int(xa)), min(p.w, int(xb) + 1)
    y0, y1 = max(0, int(hy_ + box[1] * s)), min(p.h, int(hy_ + box[3] * s) + 1)
    if x1 <= x0 or y1 <= y0: return {}
    hp = Pen(x1 - x0, y1 - y0, s, hx_ - x0, hy_ - y0, p.fx < 0, ss=p.ss)
    info = HR.draw_hero(hp, pose)
    p.im.alpha_composite(hp.im, (x0 * p.ss, y0 * p.ss))
    return info


def cab_sprite(scale, pal, flip=False, **kw):
    padl, padt, padr, padb = 960, 900, 820, 40
    w, h = int((padl + padr) * scale), int((padt + padb) * scale)
    p = Pen(w, h, scale, padl * scale, padt * scale, flip)
    draw_cab(p, pal, **kw)
    return p.result(), (padl * scale, padt * scale)


# ================================================================ people, birds, street furniture
def draw_person(p, col, arm=0.0, walk=None, hat=False, cane=False, nod=0.0, arm2=None):
    """generic flat silhouette (faces +x). arm: raise amount 0..1 of the front arm. walk: phase."""
    ph = walk
    sw = 22 * math.sin(ph) if ph is not None else 0
    for ox in (-sw, sw):
        p.capsule((0, -300), (ox * 0.6, -150), 40, 32, col)
        p.capsule((ox * 0.6, -150), (ox, -16), 30, 24, col)
        p.poly([(ox - 16, -22), (ox + 26, -22), (ox + 34, 0), (ox - 16, 0)], col)
    coat = [(-38, -470), (34, -470), (44, -380), (40, -250), (44, -200) if hat else (38, -290), (-40, -200) if hat else (-38, -290), (-44, -380)]
    p.smooth(coat, col, 4)
    piv = (2, -480)
    R = lambda pts: [rot(q, math.radians(nod), piv) for q in pts]
    p.poly(R(circle_pts(4, -520, 34, 38, 28)), col)
    p.capsule(R([(0, -490)])[0], (0, -462), 26, 30, col)
    if hat:
        p.poly(R([(-46, -548), (54, -548), (52, -540), (-44, -540)]), col)
        p.poly(R([(-30, -548), (34, -548), (32, -628), (-28, -628)]), col)
    # arms
    a = 10 + 125 * arm
    d = (math.sin(math.radians(a)), math.cos(math.radians(a)))
    E = (6 + 110 * d[0], -455 + 110 * d[1])
    a2 = a + 25 * arm
    d2 = (math.sin(math.radians(a2)), math.cos(math.radians(a2)))
    Wr = (E[0] + 100 * d2[0], E[1] + 100 * d2[1])
    p.capsule((6, -455), E, 34, 28, col); p.capsule(E, Wr, 28, 22, col); p.circle(Wr[0] + d2[0] * 10, Wr[1] + d2[1] * 10, 15, col)
    if arm2 is not None:
        b = -10 + arm2
        d = (math.sin(math.radians(b)), math.cos(math.radians(b)))
        E2 = (-6 + 110 * d[0], -455 + 110 * d[1]); W2 = (E2[0] + 100 * d[0], E2[1] + 100 * d[1])
        p.capsule((-6, -455), E2, 34, 28, col); p.capsule(E2, W2, 28, 22, col)
    if cane:
        p.capsule((Wr[0] + 4, Wr[1] + 6), (Wr[0] + 50, 0), 9, 9, col)
        p.circle(Wr[0] + 2, Wr[1] + 2, 9, col)
    return Wr


def draw_pigeon_sit(p, x, y, s, col, bob=0.0):
    p.poly(catmull([(x - 14 * s, y - 6 * s), (x - 2 * s, y - 14 * s), (x + 10 * s, y - 13 * s + bob), (x + 13 * s, y - 20 * s + bob),
                    (x + 18 * s, y - 18 * s + bob), (x + 16 * s, y - 10 * s), (x + 10 * s, y), (x - 6 * s, y + 1 * s), (x - 22 * s, y - 2 * s)], 3), col)


def draw_pigeon_fly(p, x, y, s, col, flap, dirx=1):
    up = math.sin(flap)
    body = [(x - 16 * s * dirx, y), (x, y - 5 * s), (x + 14 * s * dirx, y - 4 * s), (x + 20 * s * dirx, y - 7 * s), (x + 18 * s * dirx, y + 1 * s), (x, y + 5 * s)]
    p.poly(catmull(body, 3), col)
    for k, sg in ((0, 1),):
        tip = (x - 4 * s * dirx, y - 26 * s * up)
        p.poly([(x - 6 * s * dirx, y - 1 * s), (x + 8 * s * dirx, y - 2 * s), (tip[0] + 6 * s * dirx, tip[1]), (tip[0] - 8 * s * dirx, tip[1] + 3 * s)], col)


def draw_bubble(p, cx, cy, w, h, col, tail=(0, 1), r=None):
    r = r or min(w, h) * 0.42
    p.rrect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, r, col)
    tx = cx + tail[0] * w * 0.22
    p.poly([(tx - 16, cy + h / 2 - 4), (tx + 16, cy + h / 2 - 4), (tx - 6 + tail[0] * 18, cy + h / 2 + 30)], col)
