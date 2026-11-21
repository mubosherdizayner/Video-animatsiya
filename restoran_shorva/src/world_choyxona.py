# Choyxona-oshxona courtyard by a hovuz at dusk (hook / payoff / CTA world):
# far mountains + domes, ayvon with carved columns, lit panjara windows and lanterns,
# tapchans with tea-drinking customers, o'choq with a steaming sho'rva qozon and the oshpaz,
# a tut tree with orange leaves, bank and rippled water. Everything muted; only the hero is colored.
import math, random
from common import *
from world_pool import sky, birds, leaves_falling, giant_kosa, WATER_Y, BANK_Y
from people import seated_cross, cook
from hero import draw_steam

def _w(P, n): return 2 * math.pi * n / P          # loop-safe angular frequency

BIRDS_C = [(250, 470, 0.9, 0.4), (330, 420, 0.65, 1.7), (820, 520, 0.85, 2.4), (905, 470, 0.6, 0.9)]

def far(cv):
    cv.poly([(-60, 930), (80, 902), (200, 872), (320, 906), (470, 862), (600, 896), (760, 852), (900, 890), (1020, 868), (1140, 900),
             (1140, 1340), (-60, 1340)], MTN1)
    cv.poly([(-60, 978), (100, 952), (260, 970), (420, 942), (580, 964), (740, 936), (900, 960), (1060, 946), (1140, 962),
             (1140, 1340), (-60, 1340)], MTN2)
    c = CITY
    cv.rect(-60, 968, 1140, 1100, c)
    for (dx, r) in ((340, 46), (560, 34), (880, 58)):
        cv.rect(dx - r * 0.9, 950, dx + r * 0.9, 1000, c)
        cv.poly(ellipse_pts(dx, 952, r, r * 0.95, 22, 180, 360), c)
        cv.rect(dx - 2, 952 - r * 0.95 - 12, dx + 2, 952 - r * 0.95, c)
    cv.rect(1004, 880, 1022, 1000, c); cv.rect(999, 874, 1027, 892, c)
    cv.poly(ellipse_pts(1013, 876, 12, 10, 10, 180, 360), c)

def ayvon(cv, te, P):
    x0, x1 = 250, 1110
    cv.rect(x0, 1004, x1, 1258, GATE)                       # back wall in shade
    for wx in (330, 610, 890):                              # lit panjara windows
        flick = 0.93 + 0.07 * math.sin(_w(P, 9) * te + wx)
        col = lerpc(GATE, WIN, flick)
        cv.rect(wx - 42, 1066, wx + 42, 1196, col)
        cv.poly(ellipse_pts(wx, 1068, 42, 30, 16, 180, 360), col)
        lat = hx("4C5F63")
        for k in range(-3, 4): cv.rect(wx + k * 12 - 1.2, 1050, wx + k * 12 + 1.2, 1196, lat)
        for y in range(1080, 1196, 15): cv.rect(wx - 42, y - 1.2, wx + 42, y + 1.2, lat)
        cv.line(ellipse_pts(wx, 1068, 30, 20, 12, 180, 360), lat, 2.2, caps=False)
        cv.rect(wx - 52, 1196, wx + 52, 1206, GATE)
    cv.rect(x0 - 20, 974, x1 + 20, 1004, HOUSE)              # roof slab
    cv.rect(x0 - 24, 968, x1 + 24, 976, HOUSE)
    for bx in range(x0, x1, 38): cv.rect(bx, 1004, bx + 12, 1013, GATE)
    for cx in (262, 470, 678, 886, 1094):                    # carved wooden ustun
        cv.poly([(cx - 26, 1013), (cx + 26, 1013), (cx + 16, 1024), (cx + 20, 1031), (cx - 20, 1031), (cx - 16, 1024)], NEAR2)
        cv.rect(cx - 8, 1030, cx + 8, 1240, NEAR2)
        cv.poly([(cx - 8, 1172), (cx + 8, 1172), (cx + 12, 1188), (cx, 1206), (cx - 12, 1188)], NEAR2)
        cv.rect(cx - 15, 1238, cx + 15, 1262, NEAR2)
    for lx in (574, 990):                                   # hanging lanterns
        cv.line([(lx, 1013), (lx, 1040)], NEAR2, 2, caps=False)
        g = 0.8 + 0.2 * math.sin(_w(P, 7) * te + lx * 0.01)
        def halo(d, tf, k, lx=lx, g=g):
            a = tf(lx, 1060); r = 44 * k
            d.ellipse((a[0] - r, a[1] - r, a[0] + r, a[1] + r), fill=WIN + (int(120 * g),))
        cv.soft((lx - 50, 1010, lx + 50, 1110), halo, blur=12, scale=0.35)
        cv.poly([(lx - 14, 1042), (lx + 14, 1042), (lx + 17, 1060), (lx + 11, 1080), (lx - 11, 1080), (lx - 17, 1060)], NEAR2)
        cv.poly([(lx - 9, 1047), (lx + 9, 1047), (lx + 11, 1060), (lx + 7, 1075), (lx - 7, 1075), (lx - 11, 1060)], lerpc(GATE, WIN, g))

def tapchan(cv, x0, x1, top, te, P, guests):
    n1 = NEAR1
    cv.rect(x0, top, x1, top + 11, n1)
    for lx in (x0 + 8, x1 - 16): cv.rect(lx, top, lx + 8, 1262, n1)
    cv.rect(x0, top - 32, x1, top - 27, n1)                 # back rail
    for px in range(int(x0), int(x1) + 1, 36): cv.rect(px - 2, top - 32, px + 2, top, n1)
    mx = (x0 + x1) / 2
    cv.rect(mx - 34, top - 14, mx + 34, top - 10, n1)       # xontaxta
    cv.rect(mx - 30, top - 10, mx - 26, top, n1); cv.rect(mx + 26, top - 10, mx + 30, top, n1)
    cv.poly(ellipse_pts(mx - 6, top - 22, 9, 8, 12), n1)    # choynak
    cv.line([(mx + 2, top - 24), (mx + 10, top - 30)], n1, 2.4)
    cv.rect(mx - 9, top - 33, mx - 3, top - 29, n1)
    for dx in (14, 24): cv.rect(mx + dx - 3, top - 19, mx + dx + 3, top - 14, n1)
    for (gx, face, ph, hat) in guests:
        n = 3 + int(ph * 2) % 3
        sip = max(0.0, math.sin(_w(P, n) * te + ph * 6.28)) ** 1.6
        nod = 0.5 + 0.5 * math.sin(_w(P, n + 4) * te + ph * 3)
        seated_cross(cv, gx, top, 128, n1, sip=sip, nod=nod, face=face, hat=hat)

def ochoq(cv, te, P, steam=True, steam_t=0.0):
    cx = 150
    cv.poly([(60, 1262), (240, 1262), (226, 1206), (74, 1206)], GATE)          # clay hearth
    fl = 0.78 + 0.22 * math.sin(_w(P, 23) * te) * math.sin(_w(P, 13) * te + 1)
    fire = lerpc(GATE, WIN, fl)
    cv.poly([(124, 1262), (124, 1238)] + ellipse_pts(150, 1238, 26, 20, 12, 180, 360) + [(176, 1262)], fire)
    def glowfn(d, tf, k):
        a = tf(150, 1250); r = 70 * k
        d.ellipse((a[0] - r, a[1] - r * 0.5, a[0] + r, a[1] + r * 0.5), fill=WIN + (int(90 * fl),))
    cv.soft((80, 1215, 220, 1290), glowfn, blur=14, scale=0.35)
    cv.poly([(68, 1196)] + ellipse_pts(cx, 1196, 82, 30, 18, 0, 180) + [(232, 1196)], NEAR1)   # qozon body
    cv.poly(ellipse_pts(cx, 1196, 84, 10, 30), NEAR1)
    cv.poly(ellipse_pts(cx, 1197, 74, 6.5, 30), hx("4A5D61"))                                   # sho'rva surface
    for sx in (-1, 1):
        cv.line([(cx + sx * 82, 1200), (cx + sx * 98, 1194)], NEAR1, 5)
    if steam:
        draw_steam(cv, lambda q: q, cx, 1186, 1.0, steam_t, scale=2.6, opacity=0.5, height=95)

def tree(cv, sway=0.0):
    n1, n2 = NEAR1, NEAR2
    cv.poly([(-20, 1306), (18, 1306), (24, 1200), (40, 1100), (70, 1010), (52, 1004), (12, 1090), (-6, 1200)], n1)
    cv.poly([(30, 1090), (130, 1000), (142, 1010), (44, 1104)], n1)
    circles = [(-20, 900, 95), (70, 850, 90), (170, 880, 80), (250, 930, 66), (40, 960, 80), (140, 965, 70), (-60, 990, 60)]
    for i, (x, y, r) in enumerate(circles):
        cv.circle(x + sway * (y - 1100) / 300, y, r, n2 if i in (1, 3) else n1)
    rnd = random.Random(33)
    k = 0
    while k < 110:
        x, y = rnd.uniform(-140, 320), rnd.uniform(760, 1050)
        if not any((x - cx) ** 2 + (y - cy) ** 2 < (r - 6) ** 2 for cx, cy, r in circles): continue
        if rnd.random() > 0.35 + 0.6 * ((x + 140) / 460): continue
        cv.poly(ellipse_pts(x + sway * (y - 1100) / 300, y, rnd.uniform(4, 8), rnd.uniform(2.6, 4.4), 8, ang=rnd.uniform(0, 180)),
                LEAF1 if rnd.random() < 0.55 else LEAF2)
        k += 1

def courtyard(cv):
    cv.rect(-60, 1258, 1140, BANK_Y + 1, hx("3B4B50"))
    for y in (1272, 1289):
        cv.line([(-60, y), (1140, y)], hx("35454A"), 1.6, caps=False)
    for x in range(-60, 1140, 46):
        cv.line([(x, 1262), (x - 6, BANK_Y)], hx("35454A"), 1.4, caps=False)
    # rose bush on the right bank
    for (x, y, r) in ((1010, 1288, 26), (1045, 1280, 30), (1078, 1290, 24)):
        cv.circle(x, y, r, NEAR1)
    cv.rect(-60, BANK_Y, 1140, WATER_Y + 1, BANK)
    cv.rect(-60, BANK_Y, 1140, BANK_Y + 2.5, NEAR2)
    for x in range(0, 1100, 120):
        cv.line([(x, BANK_Y + 4), (x, WATER_Y)], hx("253034"), 1.6, caps=False)

def draw_choyxona(cv, te, P, kosa=None, hero_fn=None, leaves=True, people=True, steam_t=None):
    sky(cv)
    cv.layer(1.0)
    draw_sun(cv, 660, 700, 248)
    birds(cv, te, P, items=BIRDS_C)
    far(cv)
    ayvon(cv, te, P)
    if people:
        tapchan(cv, 520, 742, 1206, te, P, [(568, 1, 0.1, "doppi"), (700, -1, 0.55, "rumol")])
        tapchan(cv, 800, 1060, 1206, te, P, [(846, 1, 0.3, None), (930, 1, 0.8, "doppi"), (1018, -1, 0.65, "doppi")])
    courtyard(cv)
    ochoq(cv, te, P, steam_t=te if steam_t is None else steam_t)
    cook(cv, 252, 1262, 192, NEAR1, stir=(te * 2 * 7 / P) % 1.0, face=-1)
    tree(cv, sway=2.0 * math.sin(_w(P, 4) * te))
    if kosa: giant_kosa(cv, kosa["cx"], kosa["base"], kosa["k"], kosa.get("door", 0.0), te)
    if hero_fn: hero_fn(cv)
    if leaves: leaves_falling(cv, te, P, region=(-60, 300, 820, 1000), wind=26.0)
