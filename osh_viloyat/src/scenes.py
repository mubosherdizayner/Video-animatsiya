# The 14 scenes. Each returns (world canvas, camera params, screen-space post function or None).
import math, random, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from lib import *
from props import *
from timeline import S, SF, DUR, SC, T, IDS, REGIONS, N_FRAMES, FPS as TFPS

HERO_YB, HERO_H = 1330, 780
HERO_X = 285                     # hero body x in scenes 1 and 14 (loop match; leaves the centre free for the logo)
TOWER_X = 780
CAM1 = dict(ax=560, ay=900)      # scene-1 camera anchor (also used for the loop push-in in scene 14)
FALL = 0.55                      # lagan fall time (s); first one lands at 0.15 s
TOWER_STEP = 60
WOB = [0, 10, -8, 12, -6, 9, -11, 7, -5, 10, -3, 6]
FALL_Y0 = -110


def fall_curve(p):
    """falling with an initial downward speed (it was dropped from high above the frame)"""
    p = clamp01(p)
    return 0.5 * p + 0.5 * p * p


@functools.lru_cache(maxsize=1)
def teal_bg():
    return make_bg("teal")


def W0():
    return teal_bg().copy()


def hero(world, pose, t, x, yb=HERO_YB, h=HERO_H, ax=0.5, amp=1.0, seed=0, sx=1.0, sy=1.0, rot=0.0, dy=0.0):
    isx, isy, irot, idy = idle(t, seed, amp)
    draw_hero(world, pose, x, yb + idy + dy, h, ax=ax, sx=isx * sx, sy=isy * sy, rot=irot + rot)
    return dict(sx=isx * sx, sy=isy * sy, rot=irot + rot, yb=yb + idy + dy)


def lagan_at(world, im_ax_ay, x, y, sx=1.0, sy=1.0, rot=0.0, alpha=1.0, scale=1.0):
    im, ax, ay = im_ax_ay
    place_anchor(world, im, ax, ay, x, y, scale=scale, sx=sx, sy=sy, rot=rot, alpha=alpha)


# ================================================================ scene 1 — hook: lagan tower
N_TOWER = 11
def tower_state(t):
    """list of (k, x, y, sx, sy, rot) for lagans visible at time t (s, absolute in scene 1)"""
    out = []
    landed = [k for k in range(N_TOWER) if 0.15 + 0.4 * k <= t]
    last = max(landed) if landed else None
    lean_q = t - (0.15 + 0.4 * last) if last is not None else 0
    for k in range(N_TOWER):
        tl = 0.15 + 0.4 * k
        if t < tl - FALL: break
        y_land = PLATE_Y - k * TOWER_STEP
        x = TOWER_X + WOB[k]
        if t < tl:
            p = (t - (tl - FALL)) / FALL
            y = lerp(FALL_Y0, y_land, fall_curve(p))
            out.append((k, x, y, 1.0, 1.0, 7 * (1 - p) * (1 if k % 2 else -1)))
        else:
            q = t - tl
            d = damped(q, 3.2, 8)
            sy = 1 - 0.16 * d if q < 0.6 else 1
            sx = 1 + 0.10 * d if q < 0.6 else 1
            # whole tower sways after each landing (higher lagans move more)
            sway = 9 * dsin(lean_q, 2.2, 3.5) * (k / max(1, N_TOWER - 1)) if last is not None else 0
            out.append((k, x + sway, y_land, sx, sy, -sway * 0.15))
    return out


def falling_lagan(world, t_rel):
    """the lagan of frame 0: t_rel = time since it started falling"""
    p = clamp01(t_rel / FALL)
    y = lerp(FALL_Y0, PLATE_Y, fall_curve(p))
    lagan_at(world, lagan_img(300, "mixed", 101, -1), TOWER_X + WOB[0], y, rot=7 * (1 - p) * -1)


def scene1(t, lt, dur):
    world = W0()
    tw = tower_state(lt)
    last_land = max([0.15 + 0.4 * k for k in range(N_TOWER) if 0.15 + 0.4 * k <= lt], default=-9)
    q = lt - last_land
    # hero: shocked, trembles and flinches at each landing
    tremble = 1.2 * math.sin(2 * math.pi * 7 * lt)
    hop = -12 * max(0.0, dsin(q, 3, 9))
    flinch = 1 - 0.04 * max(0.0, damped(q, 3, 10))
    hero(world, SC[1]["pose"], lt, HERO_X, ax=0.55, amp=1.2, rot=tremble * 0.6, dy=hop, sy=flinch, sx=2 - flinch)
    draw_table(world)
    for k, x, y, sx, sy, rot in tw:
        lagan_at(world, lagan_img(300, "mixed", 101 + k, -1 if k % 2 == 0 else 1), x, y, sx=sx, sy=sy, rot=rot)
    sc = 1.15 - 0.15 * ease_in_out_sine(lt / dur)
    shake = 7 * dsin(q, 11, 16) if q < 0.4 else 0
    cam = dict(scale=sc, ax=CAM1["ax"], ay=CAM1["ay"], tx=shake * 0.6, ty=shake)
    return world, cam, None


# ================================================================ scene 2 — UNESCO stamp
def scene2(t, lt, dur):
    world = W0()
    Ti = T(2, "yunesko") - S[2]
    pose = SC[2]["pose"]
    wag = 2.2 * math.sin(2 * math.pi * 2.2 * lt) * (1 if lt < Ti + 0.6 else 0.4)
    hero(world, pose, lt, 300, ax=0.42, seed=2, rot=wag)
    draw_table(world)
    LX = 770
    lagan_at(world, lagan_img(340, "mixed", 7, 0), LX, PLATE_Y)
    sx_, sy_ = LX - 70, PLATE_Y + 18
    st = stamp_img(300)
    ta = Ti - 0.38
    q = lt - Ti
    if lt >= ta:
        if lt < Ti:
            p = (lt - ta) / (Ti - ta)
            e = ease_in_cubic(p)
            scl = lerp(1.25, 0.72, e); y = lerp(sy_ - 520, sy_, e); rot = lerp(-34, -14, e)
            place(world, st, sx_, y, scale=scl, rot=rot, alpha=clamp01(p / 0.3))
        else:
            d = damped(q, 3.5, 9)
            place(world, st, sx_, sy_, scale=0.72, sx=1 + 0.16 * d, sy=1 - 0.16 * d, rot=-14)
            # sparkle burst
            if q < 0.9:
                for j in range(12):
                    a = 2 * math.pi * j / 12 + 0.2
                    r = 60 + 300 * ease_out_cubic(q / 0.75) * (0.8 + 0.3 * (j % 3) / 2)
                    s = (0.5 + 0.5 * (j % 2)) * (1 - q / 0.9)
                    if s > 0.05:
                        place(world, sparkle_img(70), sx_ + r * math.cos(a), sy_ - 20 + r * math.sin(a) * 0.8, scale=s, rot=q * 200)
    # camera: quick push-in on the stamp at impact, then settle
    if q < 0:
        sc = 1.0 + 0.02 * clamp01(lt / max(0.01, Ti))
    elif q < 0.12:
        sc = 1.02 + 0.14 * ease_out_cubic(q / 0.12)
    else:
        sc = 1.05 + 0.11 * (1 - ease_in_out(clamp01((q - 0.12) / 0.7)))
    shake = 8 * dsin(q, 12, 18) if 0 <= q < 0.35 else 0
    cam = dict(scale=sc, ax=sx_, ay=sy_ - 120, tx=shake * 0.5, ty=shake)
    return world, cam, None


# ================================================================ scene 3 — the judge
def kapgir_angle(lt, taps, up=-30.0, down=20.4):
    a = up + 3 * math.sin(2 * math.pi * 1.1 * lt)
    for i, tp in enumerate(taps):
        if tp - 0.2 <= lt < tp:
            a0 = up if i == 0 else up + 6
            return lerp(a0, down, ease_in_cubic((lt - (tp - 0.2)) / 0.2))
        if tp <= lt < tp + 0.07:
            return down - 2 * math.sin(math.pi * (lt - tp) / 0.07)
        if tp + 0.07 <= lt < tp + 0.32:
            return lerp(down, up + (6 if i == 0 else -6), ease_out_cubic((lt - tp - 0.07) / 0.25))
    if lt >= taps[-1] + 0.32: return up - 6 + 2 * math.sin(2 * math.pi * 1.1 * lt)
    if lt >= taps[0] + 0.32: return up + 6
    return a


def scene3(t, lt, dur):
    world = W0()
    pose = SC[3]["pose"]
    taps = [T(3, "xolis") - S[3], T(3, "hakam") - S[3]]
    tb = T(3, "bo") - S[3]
    HX, HYB, HH = 400, 1420, 900
    st = hero(world, pose, lt, HX, yb=HYB, h=HH, ax=0.55, amp=0.7, seed=3)
    # badge pops onto the chest
    if lt >= tb:
        p = lt - tb
        bx, by = hero_point(pose, 0.585, 0.5, HX, st["yb"], HH, ax=0.55, sx=st["sx"], sy=st["sy"], rot=st["rot"])
        s = ease_out_back(clamp01(p / 0.3), 2.6)
        place(world, badge_img(170), bx, by + 18, scale=0.95 * s, rot=8 * math.sin(2 * math.pi * 1.3 * lt) * math.exp(-p * 2))
    draw_table(world)
    # kapgir gavel
    kimg, piv, disc = kapgir_img(360, 56)
    ang = kapgir_angle(lt, taps)
    PX, PY = 1000, 990
    place_anchor(world, kimg, piv[0], piv[1], PX, PY, rot=-ang)
    # impact puffs
    for tp in taps:
        q = lt - tp
        if 0 <= q < 0.35:
            L = piv[0] - disc[0]
            hx = PX - L * math.cos(math.radians(20.4)); hy = PY + L * math.sin(math.radians(20.4)) + 40
            for j in range(6):
                a = math.pi + math.pi * j / 5
                r = 40 + 110 * ease_out_cubic(q / 0.3)
                place(world, sparkle_img(46, WHITE), hx + r * math.cos(a), hy + r * math.sin(a) * 0.5, scale=1 - q / 0.35)
    sc = 1.0 + 0.08 * ease_in_out_sine(lt / dur)
    shake = 0
    for tp in taps:
        if 0 <= lt - tp < 0.3: shake = 6 * dsin(lt - tp, 12, 16)
    cam = dict(scale=sc, ax=520, ay=900, ty=shake)
    return world, cam, None


# ================================================================ scene 4 — Tashkent: stirred
def stir_lagan(w, rot, seed=9):
    pad = 24
    top_extra = int(w * 0.3)
    ry = w * 0.16
    cw, ch = w + 2 * pad, int(top_extra + ry * 2.5 + w * 0.06 + 24)
    cx, cy = cw / 2, top_extra + ry * 0.2
    c = SS(cw, ch, 2)
    plate(c, w, cx, cy, inner=False)
    P = stir_pieces()
    mh = mound(c, w, cx, cy, "mixed", seed, rot=rot, pieces=P)
    return c.result(), cx, cy, mh


@functools.lru_cache(maxsize=1)
def stir_pieces():
    return osh_pieces(9, n_carrot=30, n_meat=8, n_pea=10)


def scene4(t, lt, dur):
    pose = SC[4]["pose"]
    ox = 560 * (1 - ease_out_cubic(lt / 0.5))
    world = make_bg("teal", scroll=-ox * 0.35) if ox > 0.5 else W0()
    hero(world, pose, lt, 790 + ox, ax=0.52, seed=4, rot=1.5 * math.sin(2 * math.pi * 1.6 * lt))
    draw_table(world, xoff=ox)
    LX, w = 320 + ox, 420
    phi = 2 * math.pi * 0.95 * max(0.0, lt - 0.25)
    im, ax, ay, mh = stir_lagan(w, phi * 0.9)
    paste(world, im, LX + M - ax, PLATE_Y + M - ay)
    # kapgir stirring along an ellipse on top of the mound
    kimg, piv, disc = kapgir_img(360, 56)
    dx = LX + 80 * math.cos(phi); dy = PLATE_Y - mh * 0.62 + 20 * math.sin(phi)
    place_anchor(world, kimg, disc[0], disc[1], dx, dy, rot=128 + 6 * math.sin(phi), scale=0.95)
    lc = label_card("TOSHKENT", 330)
    place(world, lc, LX, PLATE_Y + 112, rot=2 * math.sin(lt * 3))
    # steam wisps
    st, (sx_, sy_) = steam_layer(lt, LX + 60, PLATE_Y - mh, w * 0.7, 2, 0.25)
    paste(world, st, sx_ + M, sy_ + M)
    cam = dict(scale=1.0 + 0.03 * ease_in_out_sine(lt / dur), ax=540, ay=950)
    return world, cam, None


# ================================================================ scene 5 — Samarkand: layers
def scene5(t, lt, dur):
    world = W0()
    pose = SC[5]["pose"]
    trig = [T(5, "guruch") - S[5], T(5, "sabzi") - S[5], T(5, "go") - S[5]]
    laugh = -7 * abs(math.sin(2 * math.pi * 3.0 * lt))
    hero(world, pose, lt, 800, ax=0.55, seed=5, dy=laugh, rot=1.2 * math.sin(2 * math.pi * 3.0 * lt))
    draw_table(world)
    LX, w = 320, 420
    L, cx, cy = layer_imgs(w)
    place_anchor(world, L["plate"], cx, cy, LX, PLATE_Y)
    DROP = 0.13
    for name, tt in zip(("rice", "carrot", "meat"), trig):
        q = lt - tt
        if q < 0: continue
        if q < DROP:
            y = PLATE_Y - 300 * (1 - (q / DROP) ** 2)
            place_anchor(world, L[name], cx, cy, LX, y)
        else:
            d = damped(q - DROP, 3.5, 10)
            place_anchor(world, L[name], cx, cy, LX, PLATE_Y, sx=1 + 0.08 * d, sy=1 - 0.1 * d)
    lc = label_card("SAMARQAND", 330)
    place(world, lc, LX, PLATE_Y + 112)
    n = sum(clamp01((lt - tt) / 0.35) for tt in trig)
    cam = dict(scale=1.0 + 0.012 * n + 0.02 * lt / dur, ax=420, ay=1000, ty=22 * n)
    return world, cam, None


# ================================================================ scene 6 — Fergana: devzira macro then pull-back
def scene6(t, lt, dur):
    pose = SC[6]["pose"]
    A_END, B_END = 0.85, 1.35
    LX, w = 300, 420
    world = W0()
    period = 0.52
    ph = (lt % period) / period
    jump = -150 * math.sin(math.pi * ph)
    land = 1 - 0.06 * max(0.0, 1 - min(ph, 1 - ph) / 0.12)
    hero(world, pose, lt, 760, h=700, ax=0.52, seed=6, dy=jump, sy=land, sx=2 - land, rot=3 * math.sin(2 * math.pi * lt / period))
    draw_table(world)
    im, ax, ay = lagan_img(w, "devzira", 21, 0)
    paste(world, im, LX + M - ax, PLATE_Y + M - ay)
    mound_top = PLATE_Y - w * 0.22
    # oil glisten sweep over the mound
    sw = (lt * 0.9) % 1.0
    g = Image.new("RGBA", (int(w * 0.8), int(w * 0.26)), (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    gx = -60 + sw * (g.width + 120)
    gd.polygon([(gx, 0), (gx + 26, 0), (gx - 14, g.height), (gx - 40, g.height)], fill=(255, 255, 230, 120))
    g = g.filter(ImageFilter.GaussianBlur(5))
    paste(world, g, LX + M - g.width / 2, mound_top + M + 4)
    lc = label_card("FARGʻONA", 330)
    place(world, lc, LX, PLATE_Y + 112)
    if lt < A_END:
        cam = dict(scale=1.0, ax=540, ay=960)
    else:
        p = ease_in_out_sine((lt - A_END) / (B_END - A_END))
        my = PLATE_Y - w * 0.09
        cam = dict(scale=lerp(6.0, 1.0, p), ax=LX, ay=my, tx=lerp(540 - LX, 0, p), ty=lerp(960 - my, 0, p))

    def post(frame):
        XF = 0.2
        if lt >= A_END + XF: return
        mac = devzira_macro()
        a = 1.0 if lt < A_END else 1 - ease_in_out(clamp01((lt - A_END) / XF))
        s = 1.0 + 0.06 * min(lt, A_END) / A_END
        if lt > A_END: s *= lerp(1.0, 0.6, clamp01((lt - A_END) / XF))
        cw, ch = int(W / s), int(H / s)
        x0 = int(200 + 60 * min(lt, A_END)); y0 = int(60 + 40 * min(lt, A_END))
        crop = mac.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BICUBIC)
        # shine sweep (diagonal light band)
        sp = clamp01((lt - 0.12) / 0.6)
        if 0 < sp < 1:
            band = Image.new("L", (W, H), 0)
            bd = ImageDraw.Draw(band)
            cx = -400 + sp * (W + 800)
            bd.polygon([(cx, 0), (cx + 160, 0), (cx - 560, H), (cx - 720, H)], fill=150)
            band = band.filter(ImageFilter.GaussianBlur(40))
            crop = Image.composite(Image.new("RGB", (W, H), (255, 246, 220)), crop.convert("RGB"), band).convert("RGBA")
        if a < 1:
            crop = with_alpha(crop.convert("RGBA"), a)
        frame.paste(crop, (0, 0), crop.convert("RGBA"))
    return world, cam, post


# ================================================================ scene 7 — 11 more regions
@functools.lru_cache(maxsize=24)
def region_card(name, front=True, w=440, h=56, hi=False):
    c = SS(w + 12, h + 12, 3)
    if front:
        c.rect((6, 6, w + 6, h + 6), fill=CREAM, outline=GOLD if hi else OL, width=7 if hi else 5, r=14)
        c.rect((6, 6, 30, h + 6), fill=RED, outline=OL, width=4, r=10)
    else:
        c.rect((6, 6, w + 6, h + 6), fill=GOLD, outline=OL, width=5, r=14)
        c.rect((18, 14, w - 6, h - 2), fill=None, outline=GOLD_D, width=3, r=8)
        star(c, w / 2 + 6, h / 2 + 6, h * 0.28, GOLD_L, outline=OL, width=2)
    im = c.result()
    if front:
        sz = 40
        t = plain_text(name, sz, (56, 26, 16))
        while t.width > w - 70: sz -= 1; t = plain_text(name, sz, (56, 26, 16))
        im.alpha_composite(t, (int(38 + (w - 38 - t.width) / 2), int(6 + (h - t.height) / 2)))
    return im


CARD_X, CARD_Y0, CARD_STEP = 742, 470, 61


def card_times():
    t0, step = 0.1, 0.19
    return [t0 + j * step for j in range(len(REGIONS))], step


def scene7(t, lt, dur):
    pose = SC[7]["pose"]
    world = make_bg("teal", scroll=lt * 360)
    times, step = card_times()
    # flip-board of 11 region cards (behind the runner, right side)
    for j, name in enumerate(REGIONS):
        y = CARD_Y0 + j * CARD_STEP
        p = (lt - times[j]) / 0.12
        cur = times[j] <= lt < times[j] + step
        if p <= 0:
            place(world, region_card(name, False), CARD_X, y)
        elif p < 0.5:
            place(world, region_card(name, False), CARD_X, y, sy=max(0.02, math.cos(math.pi * p)))
        elif p < 1:
            place(world, region_card(name, True, hi=True), CARD_X, y, sy=max(0.02, -math.cos(math.pi * p)))
        else:
            pop = 1 + 0.06 * damped(lt - times[j] - 0.12, 3, 9) if lt - times[j] < 0.5 else 1
            place(world, region_card(name, True, hi=cur), CARD_X, y, scale=pop)
    # runner
    ph = 2 * math.pi * 3.3 * lt
    bob = -16 * abs(math.sin(ph))
    sq = 1 + 0.03 * math.cos(2 * ph)
    hero(world, pose, lt, 280, h=640, ax=0.55, amp=0.4, seed=7, dy=bob, sy=sq, sx=2 - sq, rot=-3 + 2 * math.sin(ph))
    # speed lines behind him
    for j in range(5):
        y = 760 + j * 70
        x1 = 40 + ((lt * 900 + j * 137) % 260)
        c_a = int(150 * (1 - ((lt * 900 + j * 137) % 260) / 260))
        ln = Image.new("RGBA", (170, 12), (255, 255, 255, 0))
        ImageDraw.Draw(ln).rounded_rectangle((0, 0, 169, 11), radius=6, fill=(255, 255, 255, c_a))
        paste(world, ln, M + x1 - 120, M + y)
    draw_table(world, xoff=-lt * 950)
    cam = dict(scale=1.0, ax=540, ay=960)
    return world, cam, None


# ================================================================ scene 8 — re-hook: all are the best
@functools.lru_cache(maxsize=2)
def plate_tower(n=8, w=220):
    im, ax, ay = lagan_img(w, "empty", 3, 0)
    step = 30
    hgt = im.height + step * n
    out = Image.new("RGBA", (im.width + 20, hgt), (0, 0, 0, 0))
    for k in range(n):
        dx = [0, 4, -3, 5, -4, 2, -2, 3, 0, -3][k % 10]
        out.alpha_composite(im, (10 + dx, hgt - im.height - k * step))
    return out


@functools.lru_cache(maxsize=1)
def cool_bg():
    return grade(teal_bg(), sat=0.35, mul=(0.78, 0.9, 1.08), add=(6, 10, 22))


def scene8(t, lt, dur):
    world = cool_bg().copy()
    pose = SC[8]["pose"]
    shrug = -10 * max(0.0, math.sin(2 * math.pi * 1.4 * lt)) * (1 if lt < 2.4 else 0.4)
    # empty plate towers (graded cool)
    for x, n, ph in ((150, 9, 0.0), (930, 10, 1.3)):
        pt = plate_tower(n)
        sway = 2.0 * math.sin(2 * math.pi * 0.7 * lt + ph)
        place_anchor(world, grade(pt, 0.4, (0.85, 0.92, 1.05)), pt.width / 2, pt.height - 40, x, PLATE_Y + 40, rot=sway)
    hero(world, pose, lt, 540, h=640, ax=0.5, seed=8, dy=shrug)
    tbl = Image.new("RGBA", world.size, (0, 0, 0, 0))
    draw_table(tbl)
    world.alpha_composite(grade(tbl, 0.35, (0.8, 0.9, 1.06), (4, 8, 18)))
    # balance scale above his head: wobbles and settles perfectly level
    beam = 13 * damped(lt, 0.9, 1.7) if lt < 2.9 else 0.0
    mini = grade(lagan_img(110, "mixed", 5, 0)[0], 0.5, (0.9, 0.95, 1.05))
    sc_im, (ppx, ppy) = scale_img(beam, lt, 430, mini)
    place_anchor(world, sc_im, sc_im.width / 2, sc_im.height * 0.95, 540, 712 + 4 * math.sin(2 * math.pi * 0.8 * lt))
    # dutch tilt: quick 5 degrees, hold, back to level
    if lt < 0.14: rot = 5 * ease_out_cubic(lt / 0.14)
    elif lt < 0.7: rot = 5
    else: rot = 5 * (1 - ease_in_out(clamp01((lt - 0.7) / 0.45)))
    cam = dict(scale=1.0 + 0.04 * ease_out_cubic(lt / 0.3), ax=540, ay=900, rot=rot, fill=(40, 60, 70))
    return world, cam, None


# ================================================================ scene 9 — payoff: mother's osh
def scene9(t, lt, dur):
    world = home_bg().copy()
    world.alpha_composite(beams(lt))
    fc = floor_cloth()
    paste(world, fc, M + 540 - fc.width / 2, M + 1180)
    pose = SC[9]["pose"]
    hero(world, pose, lt, 520, yb=1300, h=660, ax=0.45, amp=0.6, seed=9)
    # steaming home lagan in front of him
    LX, LY, w = 540, 1330, 400
    im, ax, ay = lagan_img(w, "mixed", 31, 0)
    paste(world, im, LX + M - ax, LY + M - ay)
    st, (sx_, sy_) = steam_layer(lt, LX, LY - w * 0.22, w, 3, 0.6)
    paste(world, st, sx_ + M, sy_ + M)
    # tiny hearts rising
    rnd = random.Random(9)
    for j in range(7):
        t0 = j * 0.42
        q = (lt - t0) % 2.9
        if lt < t0: continue
        x = LX + rnd.uniform(-170, 170) + 22 * math.sin(2 * math.pi * (q * 0.8 + j * 0.3))
        y = LY - w * 0.2 - 40 - q * 190
        a = clamp01(q / 0.3) * clamp01((2.4 - q) / 0.6)
        if a > 0.02:
            place(world, heart_img(46), x, y, scale=0.6 + 0.25 * (j % 3) / 2 + 0.1 * math.sin(q * 6), alpha=a, rot=10 * math.sin(q * 3 + j))
    # dust motes in the light
    for j in range(14):
        x = 200 + (j * 97 + lt * 18) % 560; y = 450 + (j * 151 - lt * 26) % 700
        place(world, soft_ellipse(8, 8, (255, 240, 200), 0.8, 2), x, y)
    sc = 1.0 + 0.09 * ease_in_out_sine(lt / dur)
    cam = dict(scale=sc, ax=530, ay=1020, fill=(70, 34, 18))

    def post(frame):
        frame.alpha_composite(vignette_layer(0.6)) if frame.mode == "RGBA" else None
    return world, cam, post


# ================================================================ scene 10 — but that is not impartial
def scene10(t, lt, dur):
    world = W0()
    pose = SC[10]["pose"]
    st = hero(world, pose, lt, 540, h=760, ax=0.5, amp=0.5, seed=10, rot=-1.5)
    draw_table(world)
    # small grey cloud above his head with drizzle
    hx, hy = hero_point(pose, 0.45, 0.0, 540, st["yb"], 760, ax=0.5, sx=st["sx"], sy=st["sy"], rot=st["rot"])
    p = ease_out_back(clamp01(lt / 0.3), 2.0)
    cx, cy = hx + 10 * math.sin(2 * math.pi * 0.6 * lt), hy - 62 + 6 * math.sin(2 * math.pi * 1.1 * lt)
    if p > 0.02:
        for j in range(6):
            q = (lt * 2.2 + j / 6) % 1.0
            x = cx - 90 + j * 36
            y = cy + 40 + q * 120
            ln = Image.new("RGBA", (10, 34), (0, 0, 0, 0))
            ImageDraw.Draw(ln).rounded_rectangle((1, 1, 8, 32), radius=4, fill=(150, 196, 230, int(220 * (1 - q) * clamp01(lt / 0.4))))
            paste(world, ln, M + x, M + y)
        place(world, cloud_img(300), cx, cy, scale=0.8 * p)
    cam = dict(scale=1.02, ax=540, ay=900, rot=0.9 * math.sin(2 * math.pi * lt / 1.5), tx=6 * math.sin(2 * math.pi * lt / 1.9))
    return world, cam, None


# ================================================================ scene 11 — so the judge is you
def scene11(t, lt, dur):
    world = W0()
    pose = SC[11]["pose"]
    HX = 470
    st = hero(world, pose, lt, HX, h=780, ax=0.4, seed=11)
    draw_table(world)
    bx, by = hero_point(pose, 0.40, 0.5, HX, st["yb"], 780, ax=0.4, sx=st["sx"], sy=st["sy"], rot=st["rot"])
    TF = 0.3
    if lt < TF:
        place(world, badge_img(170), bx, by + 18, scale=0.95, rot=4 * math.sin(lt * 9))
    sc = 1.0 + 0.22 * ease_out_cubic(lt / 0.55)
    cam = dict(scale=sc, ax=HX, ay=760)

    def post(frame):
        if lt < TF: return
        q = (lt - TF) / 0.75
        if q > 1: return
        # start: chest position in screen space; fly toward the viewer (centre, growing)
        x0 = cam["ax"] + (bx - cam["ax"]) * sc; y0 = cam["ay"] + (by + 18 - cam["ay"]) * sc
        e = ease_in_cubic(q)
        x = lerp(x0, 540, ease_out_cubic(q)); y = lerp(y0, 900, ease_out_cubic(q))
        s = 0.95 * sc * (1 + 7 * e)
        a = 1 - clamp01((q - 0.65) / 0.35)
        b = badge_img(170)
        bb = b.resize((max(1, int(b.width * s)), max(1, int(b.height * s))), Image.BICUBIC)
        if a < 1: bb = with_alpha(bb, a)
        bb = bb.rotate(-8 * e, resample=Image.BICUBIC, expand=True)
        paste(frame, bb, x - bb.width / 2, y - bb.height / 2)
    return world, cam, post


# ================================================================ scene 12 — write in the comments
def click_times(dur):
    return [0.55 + 0.14 * j for j in range(int((dur - 0.75) / 0.14))]


def scene12(t, lt, dur):
    world = W0()
    pose = SC[12]["pose"]
    HX = 290
    st = hero(world, pose, lt, HX, h=780, ax=0.5, seed=12)
    draw_table(world)
    phx, phy = hero_point(pose, 0.69, 0.42, HX, st["yb"], 780, ax=0.5, sx=st["sx"], sy=st["sy"], rot=st["rot"])
    PX, PY = 742, 790
    p = ease_out_back(clamp01((lt - 0.05) / 0.35), 1.6)
    clicks = click_times(dur)
    pressed = set()
    rnd = random.Random(12)
    keys = [rnd.randrange(26) for _ in clicks]
    for c_t, kk in zip(clicks, keys):
        if c_t <= lt < c_t + 0.09: pressed.add(kk)
    cursor = (int(lt * 2.4) % 2 == 0)
    panel = phone_panel(lt, cursor, pressed)
    if p > 0.01:
        # zoom cone from the hero's phone to the enlarged screen
        cone = Image.new("RGBA", world.size, (0, 0, 0, 0))
        cx0, cy0 = PX - panel.width / 2 * p, PY - panel.height / 2 * p
        cx1, cy1 = PX + panel.width / 2 * p, PY + panel.height / 2 * p
        ImageDraw.Draw(cone).polygon([(phx + M, phy + M), (cx0 + M + 20, cy0 + M + 30), (cx0 + M + 20, cy1 + M - 30)], fill=(255, 255, 255, int(60 * clamp01(p))))
        world.alpha_composite(cone)
        x = lerp(phx, PX, clamp01(p)); y = lerp(phy, PY, clamp01(p))
        place(world, panel, x, y, scale=max(0.05, p), rot=1.5 * math.sin(2 * math.pi * 0.7 * lt))
    sc = 1.0 + 0.07 * ease_in_out_sine(lt / dur)
    cam = dict(scale=sc, ax=PX, ay=PY)
    return world, cam, None


# ================================================================ scene 13 — bubbles with the template
BUBBLES = [((738, 560), "qaysi"), ((770, 780), "oshi"), ((742, 1000), "yoqadi")]


def scene13(t, lt, dur):
    world = W0()
    pose = SC[13]["pose"]
    hero(world, pose, lt, 290, h=760, ax=0.5, seed=13, rot=1.5 * math.sin(2 * math.pi * 0.9 * lt))
    draw_table(world)
    for j, ((bx, by), wd) in enumerate(BUBBLES):
        tb = T(13, wd) - S[13]
        q = lt - tb
        if q < 0: continue
        s = ease_out_back(clamp01(q / 0.28), 2.4)
        b = bubble_img(j, 450)
        place(world, b, bx, by + 6 * math.sin(2 * math.pi * 0.8 * lt + j), scale=s)
    sc = 1.08 - 0.08 * ease_in_out_sine(lt / dur)
    cam = dict(scale=sc, ax=520, ay=860)
    return world, cam, None


# ================================================================ scene 14 — send to a friend (+ seamless loop)
LOGO_POS = (540, 950)
LOGO_D = 250


def scene14(t, lt, dur):
    world = W0()
    pose = SC[14]["pose"]
    hero(world, pose, lt, HERO_X, ax=0.6, seed=14, rot=2.4 * math.sin(2 * math.pi * 1.7 * lt))
    draw_table(world)
    tf = dur - 0.4                 # the frame-0 lagan starts falling 0.4 s before the end
    if lt >= tf:
        falling_lagan(world, lt - tf)
    # camera: slight drift, then push to the frame-0 framing (scale 1.15, same anchor)
    drift = 1.0 + 0.012 * math.sin(2 * math.pi * lt / 3.4)
    if lt < tf:
        sc = drift; tx = 5 * math.sin(2 * math.pi * lt / 2.8)
    else:
        p = ease_in_out_sine((lt - tf) / (dur - tf - 1.0 / 30))
        drift_end = 1.0 + 0.012 * math.sin(2 * math.pi * tf / 3.4)
        sc = lerp(drift_end, 1.15, clamp01(p)); tx = lerp(5 * math.sin(2 * math.pi * tf / 2.8), 0, clamp01(p))
    cam = dict(scale=sc, ax=CAM1["ax"], ay=CAM1["ay"], tx=tx)
    return world, cam, None


SCENE_FN = {1: scene1, 2: scene2, 3: scene3, 4: scene4, 5: scene5, 6: scene6, 7: scene7, 8: scene8,
            9: scene9, 10: scene10, 11: scene11, 12: scene12, 13: scene13, 14: scene14}
