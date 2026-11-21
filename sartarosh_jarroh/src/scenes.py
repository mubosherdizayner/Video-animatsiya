# The 12 scenes. Each scene function takes (frame index i, time t) and returns a float32 RGB array.
import math, functools
import numpy as np
from gfx import *
import chars as C
import props as P
import sets as S
import timing as T
from timing import cue

F = FPS


def camera(ctx, z=1.0, cx=540.0, cy=960.0, rot=0.0, w=W, h=H):
    ctx.translate(w / 2, h / 2)
    if rot:
        ctx.rotate(rot)
    ctx.scale(z, z)
    ctx.translate(-cx, -cy)


def shake(i, f0, amp=10):
    k = i - f0
    seq = [(1.0, -0.6), (-0.8, 0.8), (0.6, -0.4), (-0.3, 0.2)]
    if 0 <= k < len(seq):
        return seq[k][0] * amp, seq[k][1] * amp
    return 0.0, 0.0


def pliers_prop(s=1.0, open_=0.08, glint=0.0, t=0.0, offset=34):
    def f(ctx):
        ctx.save()
        ctx.translate(0, offset)
        ctx.rotate(PI)
        P.pliers(ctx, s=s, open_=open_, glint=glint, t=t)
        ctx.restore()
    return f


def scissors_prop(s=0.9, open_=0.2, rot=0.0):
    def f(ctx):
        ctx.save()
        ctx.translate(0, 12)
        ctx.rotate(PI + rot)
        P.scissors(ctx, s=s, open_=open_)
        ctx.restore()
    return f


# =====================================================================  barbershop (scenes 1, 12)
HERO_SEAT = dict(x=500, y=1420, s=1.22)
SHOP_Z, SHOP_CX, SHOP_CY = 1.22, 590.0, 1040.0
SEAT_Y = HERO_SEAT["y"] + C.HIP_SIT * HERO_SEAT["s"]
BARB = dict(x=850, y=1440, s=1.2)


def barber_s1_pose(tb, t_real, t_unf, glint=0.0):
    """modern barber in scene 1. tb = (possibly frozen) background time"""
    u = eo((tb + 0.25) / 0.85)
    turn = lerp(0.35, -0.5, u)
    p = dict(BARB, seed=2, turn=turn, look=(lerp(0.3, -0.7, u), 0.0), brows="normal", mouth="smile",
             armR=dict(a=lerp(8, 34, u), e=lerp(-20, -104, u), hand="hold",
                       prop=pliers_prop(1.25, 0.10, glint, t_real, offset=40)),
             armL=dict(a=lerp(10, 26, u), e=lerp(-10, -40, u), hand="fist"))
    if t_unf is not None and t_real >= t_unf:
        tr = t_real - t_unf
        if tr < 0.5:
            k = eo(tr / 0.2)
            p.update(look=(lerp(-0.7, -0.6, k), lerp(0, 0.9, k)), tilt=-0.06 * k, brows="raised", mouth="o")
        else:
            k = eo((tr - 0.5) / 0.22)
            p.update(turn=lerp(-0.5, -0.05, k), look=(lerp(-0.6, 0, k), lerp(0.9, 0, k)),
                     tilt=-0.06 * (1 - k) - 0.05 * k * math.sin((tr - 0.5) * 9) * math.exp(-(tr - 0.5) * 2),
                     brows="confused", mouth="worried")
    return p


def hero_s1_pose(t, t_stop, t_unf):
    p = dict(HERO_SEAT, legs="sit", cape=True, seed=1, turn=0.35, look=(0.8, -0.3), brows="worried", mouth="o")
    if t < t_stop:
        return p
    k = eo(ramp(t, t_stop, 3 / F))
    p.update(turn=lerp(0.35, 0.0, k), look=(lerp(0.8, 0, k), lerp(-0.3, 0, k)), brows="angry",
             mouth="wide" if t < t_stop + 0.5 else "flat")
    # palm thrust toward camera
    out_k = eback(ramp(t, t_stop, 5 / F), 2.2)
    back_k = eio(ramp(t, 1.45, 0.3))
    reach = out_k * (1 - back_k)
    if reach > 0.01:
        wig = 0.07 * math.sin(t * 13) if t < t_unf else 0.03 * math.sin(t * 7)
        tgt = (lerp(420, 330, reach), lerp(1200, 1075, reach))
        a = C.ik("hero", p, -1, tgt, bend=-1)
        p["armL"] = dict(a=a["a"], e=a["e"], hand="open", habs=PI + wig, hs=lerp(1.0, 2.35, reach),
                         out=True, mirror=True, **{"from": (-112, -40)})
    if t >= t_unf:
        tr = t - t_unf
        if t < 1.6:
            p.update(brows="normal", mouth="smile")
        elif t < cue(1, "tish"):
            p.update(brows="smug", mouth="smirk", look=(0.0, 0.0))
        else:
            k2 = eo(ramp(t, cue(1, "tish"), 0.15))
            p.update(brows="raised", mouth="o", turn=0.25 * k2, look=(0.85 * k2, -0.5 * k2))
            if t > cue(1, "tish") + 0.45:
                p.update(mouth="smile_open", turn=0.0, look=(0, 0), brows="raised")
    return p


def draw_shop(ctx, tb, t, barber, hero, hero_mode="seated", extra_after=None):
    S.barbershop(ctx, tb, pole_phase=tb * 0.9)
    C.draw(ctx, "barber", barber, tb if barber.get("_freeze") else t)
    P.chair_back(ctx, 500, SEAT_Y)
    if hero is not None and hero_mode == "seated":
        C.draw(ctx, "hero", hero, t)
    P.chair_front(ctx, 500, SEAT_Y)
    if hero is not None and hero_mode == "front":
        C.draw(ctx, "hero", hero, t)
    if extra_after:
        extra_after(ctx)


def s1(i, t):
    t_stop, t_unf = cue(1, "To'xtang!"), cue(1, "Sartaroshlar")
    f_stop = int(round(t_stop * F))
    frozen = t_stop <= t < t_unf
    tb = t_stop if frozen else (t if t < t_stop else t - (t_unf - t_stop))
    glint = bump(t, cue(1, "tish"), cue(1, "tish") + 0.55)
    barber = barber_s1_pose(tb, t, t_unf if t >= t_unf else None, glint)
    if frozen:
        barber["blink"] = blink(tb, 2)
        barber["breathe"] = 0.0
    hero = hero_s1_pose(t, t_stop, t_unf)
    pz = 1 + 0.05 * eo(ramp(t, t_stop, 3 / F)) * (1 - eio(ramp(t, t_unf, 0.45)))
    sx, sy = shake(i, f_stop, 9)
    cx = SHOP_CX + 6 * math.sin(t * 0.7) + sx / SHOP_Z
    cy = SHOP_CY + sy / SHOP_Z
    pz = pz * SHOP_Z
    s, ctx = surface()
    camera(ctx, pz, cx, cy)
    barber["_freeze"] = frozen
    draw_shop(ctx, tb, t, {k: v for k, v in barber.items()}, hero)
    rgb = to_rgb(s)
    d = 0.5 * eo(ramp(t, t_stop, 2 / F)) * (1 - eo(ramp(t, t_unf, 4 / F)))
    if d > 0.001:
        ms, mctx = surface()
        camera(mctx, pz, cx, cy)
        C.draw(mctx, "hero", hero, t)
        mctx.set_operator(cairo.OPERATOR_DEST_OUT)
        P.chair_front(mctx, 500, SEAT_Y)
        m = np_view(ms)[..., 3:4].astype(np.float32) / 255.0
        rgb = rgb * m + desat(rgb, d) * (1 - m) * (1 - 0.06 * d)
    return rgb


# =====================================================================  scene 2: medieval street
def s2(i, t):
    t0 = T.scene_start(2)
    t_sj = cue(2, "sartarosh-jarroh")
    pan = eio(ramp(t, t0, (t_sj - t0) + 0.2))
    camx = lerp(380, 860, pan)
    s, ctx = surface()
    camera(ctx, 1.0, camx + 6 * math.sin(t), 960)
    S.street(ctx, t)
    door_open = eo(ramp(t, t0 + 0.05, 0.5)) * (1 - eio(ramp(t, t_sj + 1.1, 0.4)))
    S.street_door(ctx, door_open)
    # hanging sign
    swing = 0.04 * math.sin(t * 2.2) + 0.32 * damp(t - t_sj, 1.6, 2.2)
    line(ctx, [(1250, 880), (1395, 880)], color=hx("3A2A1E"), width=12)
    P.hanging_sign(ctx, 1340, 880, swing, s=0.95)
    # barber-surgeon steps out
    k = eo(ramp(t, t0 + 0.35, 0.9))
    sx = 1145
    sy = lerp(1395, 1540, k)
    sc = lerp(0.85, 1.08, k)
    walking = 0.0 < k < 1.0
    pose = dict(x=sx, y=sy, s=sc, seed=3, legs="walk" if walking else "stand", walk=t * 1.6,
                mouth="smile", brows="normal", turn=0.0)
    if t >= t_sj:
        b = bump(t, t_sj, t_sj + 0.9)
        pose.update(bob=18 * b, tilt=0.0, head_dy=20 * b, eyes="happy" if b > 0.3 else "normal", mouth="smile_open",
                    armL=dict(a=lerp(12, 22, b), e=lerp(-8, -118, b), hand="open"),
                    armR=dict(a=lerp(12, 70, b), e=lerp(-8, 30, b), hand="open"))
    if k < 0.25:  # still inside the dark doorway
        ctx.save()
        ctx.rectangle(1060, 940, 170, 440)
        ctx.clip()
        C.draw(ctx, "surgeon", dict(pose, alpha=1.0), t)
        ctx.restore()
    else:
        C.draw(ctx, "surgeon", pose, t)
    rgb = to_rgb(s)
    amt = eo(ramp(t, t0, 0.22))
    return sepia(rgb, i, amount=amt)


# =====================================================================  scene 3: tooth pull
def s3(i, t):
    t0 = T.scene_start(3)
    t_pop = cue(3, "sug'urgan")
    t_tish = cue(3, "tish")
    popped = t >= t_pop
    zp = 1.06 + 0.22 * eo(ramp(t, t_pop, 4 / F)) + 0.04 * ramp(t, t0, 1.4)
    s, ctx = surface()
    mouth_pt = (420, 1086)
    camera(ctx, zp, lerp(560, 470, eo(ramp(t, t_pop, 4 / F))), lerp(1000, 980, eo(ramp(t, t_pop, 4 / F))))
    S.med_interior(ctx, t)
    P.stool(ctx, 400, 1292, 0.75)
    tug = 0.0 if popped else (0.5 + 0.5 * math.sin((t - t0) * 16)) * (1.0 + 0.8 * bump(t, t_tish, t_tish + 0.3))
    pat = dict(x=400 + 6 * tug, y=1400, s=1.15, legs="sit", seed=4, turn=0.22, mouth="aah", brows="worried",
               sweat=1.0, look=(0.7, 0.2), tilt=-0.04 * tug,
               armL=dict(a=20, e=10, hand="fist"), armR=dict(a=22, e=8, hand="fist"))
    if popped:
        tp = t - t_pop
        pat.update(eyes="spiral", look=(tp * 3, 0), mouth="wide", tilt=0.12 * damp(tp, 2.5, 3.0), sweat=0.0,
                   brows="raised")
    C.draw(ctx, "patient", pat, t)
    # pliers from the mouth toward the surgeon
    back = 40 * eo(ramp(t, t_pop, 0.25)) if popped else 0.0
    phi = 0.10
    d = (math.cos(phi), math.sin(phi))
    jaw = (mouth_pt[0] + 6 * tug + back + 14, mouth_pt[1] - 6)
    sp = 0.95
    pivot = (jaw[0] + d[0] * 112 * sp, jaw[1] + d[1] * 112 * sp)
    th = math.atan2(-d[0], d[1])
    ctx.save()
    ctx.translate(*pivot)
    ctx.rotate(th)
    P.pliers(ctx, s=sp, open_=0.05 if not popped else 0.18)
    ctx.restore()
    g1 = (pivot[0] + d[0] * 120 * sp, pivot[1] + d[1] * 120 * sp)
    g2 = (pivot[0] + d[0] * 185 * sp, pivot[1] + d[1] * 185 * sp)
    sur = dict(x=800 + 10 * tug + back * 1.6, y=1400, s=1.2, flip=True, seed=5, legs="brace",
               brace=(120, -190, 205, -96), lean=-0.05 - 0.05 * tug, mouth="grit", brows="angry", turn=0.15)
    if popped:
        sur.update(mouth="o", brows="raised", lean=-0.12 * (1 - eo(ramp(t, t_pop + 0.2, 0.4))))
    aR = C.ik("surgeon", sur, 1, g1, bend=-1)
    aL = C.ik("surgeon", sur, -1, g2, bend=-1)
    sur["armR"] = dict(a=aR["a"], e=aR["e"], hand="fist")
    sur["armL"] = dict(a=aL["a"], e=aL["e"], hand="fist")
    C.draw(ctx, "surgeon", sur, t)
    if popped:
        tp = t - t_pop
        tx_ = mouth_pt[0] + 330 * tp
        ty_ = mouth_pt[1] - 1500 * tp + 1300 * tp * tp
        sc = 1.0 + 0.6 * eo(tp / 0.3)
        for k in range(5):
            a = k * TAU / 5 + tp * 4
            r = 70 + 90 * tp
            sparkle(ctx, tx_ + r * math.cos(a), ty_ + r * math.sin(a), 26 * (1 - clamp01(tp / 0.7)) + 6,
                    alpha=1 - clamp01(tp / 0.7), color=hx("FFF6D0"), rot=a)
        glow(ctx, tx_, ty_, 160, WHITE, 0.6)
        P.tooth(ctx, tx_, ty_, sc, rot=tp * 7)
        sparkle(ctx, tx_ + 40, ty_ - 50, 30, alpha=0.9, rot=tp * 5)
    else:
        P.tooth(ctx, jaw[0] - 6, jaw[1] + 2, 0.55, rot=0.2)
    return sepia(to_rgb(s), i)


# =====================================================================  scene 4: splint + bandage
def forearm(ctx, x0, x1, y, wdt=110, t=0.0, vein=0.0, sleeve_to=None):
    sl = sleeve_to if sleeve_to is not None else x0 + 220
    tube(ctx, [(x0, y + 10), (x1, y)], wdt, SKIN)
    ctx.save()
    ctx.rectangle(x0 - 200, y - 200, sl - x0 + 200, 400)
    ctx.clip()
    tube(ctx, [(x0, y + 10), (x1, y)], wdt + 16, hx("8C8A84"))
    ctx.restore()
    line(ctx, [(sl, y - wdt / 2 - 6), (sl, y + wdt / 2 + 8)], width=6)
    ctx.save()
    ctx.translate(x1 + 8, y)
    ctx.rotate(-PI / 2)
    ctx.scale(2.3, 2.3)
    C.hand(ctx, "fist", SKIN, SKIN_D, mirror=False)
    ctx.restore()


def s4(i, t):
    t_c1, t_c2 = cue(4, "suyak"), cue(4, "yaralarni")
    cut2 = t >= t_c2
    s, ctx = surface()
    lt = t - (t_c2 if cut2 else t_c1)
    z = (1.0 if not cut2 else 1.16) + 0.05 * eo(lt / 1.2)
    camera(ctx, z, 560 if not cut2 else 600, 1010 if not cut2 else 1090)
    S.med_interior(ctx, t, window=not cut2)
    ARM_Y = 1215
    sur = dict(x=640, y=1560, s=1.45, seed=5, mouth="flat", brows="focus", look=(-0.2, 0.7), tilt=0.05, parts="body")
    pat = dict(x=120, y=1580, s=1.45, seed=4, mouth="worried", brows="worried", sweat=1.0, turn=0.35, look=(0.8, 0.6),
               parts="body")
    C.draw(ctx, "surgeon", sur, t)
    C.draw(ctx, "patient", pat, t)
    # table
    cel(ctx, lambda c: c.rectangle(-300, 1180, 1700, 900), hx("6A4326"), hx("53331C"), d=(0, -26))
    line(ctx, [(-300, 1180), (1400, 1180)], width=6)
    for k in range(-2, 10):
        line(ctx, [(k * 160, 1186), (k * 175 - 60, 2100)], color=hx("4A2C16"), width=4, alpha=0.7)
    cloth = [(60, 1130), (980, 1110), (1040, 1330), (20, 1350)]
    cel(ctx, lambda c: smooth(c, cloth, True, 0.12), hx("56604F"), hx("454E40"), d=(0, -18))
    for k in range(6):
        line(ctx, [(120 + k * 150, 1140), (100 + k * 160, 1330)], color=hx("6B7662"), width=3, alpha=0.7)
    ws = 0.06 * math.sin(t * 3)
    if not cut2:
        forearm(ctx, 150, 800, ARM_Y)
        kt = ramp(t, t_c1 + 0.1, 0.95)
        P.splint(ctx, 380, 750, ARM_Y + 4, kt, t)
        n_t = min(2, int(kt * 3))
        xt = 380 + (n_t + 0.7) * 370 / 3.4
        ang = t * 9
        h1 = (xt - 70 + 14 * math.cos(ang), ARM_Y - 120 + 18 * math.sin(ang))
        h2 = (xt + 75 - 10 * math.cos(ang), ARM_Y - 112 + 14 * math.sin(ang + 1.5))
    else:
        forearm(ctx, 150, 800, ARM_Y)
        kb = ramp(t, t_c2, 1.25)
        xs, xc = 360, 360 + 360 * kb
        ang = (t - t_c2) * 13
        ry = 78 * math.sin(ang)
        roll_behind = math.cos(ang) < 0
        roll = (xc + 34, ARM_Y + ry)
        def draw_roll():
            ellipse(ctx, roll[0], roll[1], 34, 40)
            fs(ctx, WHITE, 6)
            for k in range(3):
                ctx.new_path()
                ctx.arc(roll[0], roll[1], 10 + k * 8, ang * 2 + k, ang * 2 + k + 3.6)
                stroke_ol(ctx, 2.5, alpha=0.7)
        if roll_behind:
            draw_roll()
            forearm(ctx, 150, 800, ARM_Y)
        # bandage turns
        ctx.save()
        ctx.rectangle(xs, ARM_Y - 70, max(0.0, xc - xs) + 10, 150)
        ctx.clip()
        tube(ctx, [(xs - 10, ARM_Y + 5), (xc + 10, ARM_Y + 2)], 118, hx("F3EFE6"))
        for k in range(0, 14):
            xx = xs + k * 34
            poly(ctx, [(xx, ARM_Y + 60), (xx + 22, ARM_Y + 60), (xx + 42, ARM_Y - 62), (xx + 20, ARM_Y - 62)])
            fill(ctx, hx("D8D2C6"), 0.9)
        ctx.restore()
        line(ctx, [(xc + 6, ARM_Y - 56), (roll[0], roll[1])], color=WHITE, width=22)
        line(ctx, [(xc + 6, ARM_Y - 56), (roll[0], roll[1])], color=OL, width=3, alpha=0.4)
        if not roll_behind:
            draw_roll()
        h1 = (roll[0] + 46, roll[1] - 40)
        h2 = (xs - 30, ARM_Y - 100)
    sur2 = dict(sur, parts="arms")
    aR = C.ik("surgeon", sur2, 1, h1, bend=1)
    aL = C.ik("surgeon", sur2, -1, h2, bend=-1)
    sur2["armR"] = dict(a=aR["a"], e=aR["e"], hand="fist")
    sur2["armL"] = dict(a=aL["a"], e=aL["e"], hand="open", hrot=ws)
    C.draw(ctx, "surgeon", sur2, t)
    return sepia(to_rgb(s), i)


# =====================================================================  scene 5: physician shuts the door
def s5(i, t):
    t0 = T.scene_start(5)
    t_j, t_o, t_k = cue(5, "jarrohlikni"), cue(5, "o'zlariga"), cue(5, "ko'rmagan")
    f_k = int(round(t_k * F))
    z = 1.0 + 0.08 * eio(ramp(t, t0, T.scene_end(5) - t0))
    sx, sy = shake(i, f_k, 12)
    s, ctx = surface()
    camera(ctx, z, 520 + sx, 1000 + sy)
    shut = ei(ramp(t, t_k, 3 / F))
    shut = shut - 0.06 * damp(t - t_k - 3 / F, 3.0, 6.0) if t > t_k + 3 / F else shut
    DX, DY, DW, DH = 700, 640, 340, 760

    def inside(c):
        vgrad(c, DX - DW / 2, DY, DW, DH, [(0, hx("3A2618")), (1, hx("1E140C"))])
        k_turn = eo(ramp(t, t_o, 0.25))
        k_back = eio(ramp(t, t_o + 0.15, 0.5))
        ph = dict(x=lerp(700, 735, k_back), y=1400 - 20 * k_back, s=lerp(1.12, 0.98, k_back), seed=6,
                  tilt=lerp(-0.08, -0.24, eo(ramp(t, t_j, 0.3))), eyes="half", brows="smug", mouth="hmph",
                  turn=-0.25, look=(-0.5, 0.5),
                  armL=dict(a=18, e=-118, hand="hold", prop=lambda cc: P.book(cc, 100, 128, 0.2)),
                  armR=dict(a=10, e=-6, hand="fist"))
        if k_turn > 0.5:
            ph.update(flip=True, turn=-0.7, look=(-1, 0))
        if t < t_j:
            ph.update(eyes="normal", look=(-0.6, 0.2), mouth="flat", brows="raised")
        C.draw(c, "physician", ph, t)
        c.rectangle(DX - DW, DY, 2 * DW, DH)
        fill(c, (0, 0, 0), 0.25 * k_back)
    door = S.stone_facade(ctx, t, door_angle=shut, door_x=DX, door_y=DY, door_w=DW, door_h=DH, inside=inside)
    door()
    if t >= t_k:
        tp = t - t_k
        for k in range(6):
            a = PI + k * PI / 5
            r = 40 + 260 * eo(tp / 0.6)
            ellipse(ctx, DX + r * math.cos(a) * 1.2, DY + DH - 10 + r * math.sin(a) * 0.25 - 10, 40 * (1 - tp / 0.8) + 4, 26 * (1 - tp / 0.8) + 3)
            fill(ctx, hx("E8DCC4"), max(0.0, 0.8 - tp))
    # barber-surgeon, left, holding pliers
    sh_k = eo(ramp(t, t_k + 0.08, 0.25))
    sur = dict(x=250, y=1560, s=1.18, seed=5, turn=0.4, look=(0.8, -0.2), mouth="smile_open", brows="raised",
               armR=dict(a=lerp(30, 55, 0.5 + 0.5 * math.sin(t * 2)), e=-40, hand="hold",
                         prop=pliers_prop(0.62, 0.08)),
               armL=dict(a=12, e=-8, hand="fist"))
    if t > t_j:
        sur.update(mouth="smile", brows="normal")
    if t >= t_k:
        sur.update(turn=lerp(0.4, 0.0, sh_k), look=(0, 0), mouth="flat", brows="worried", head_dy=10 * sh_k,
                   armL=dict(a=lerp(12, 58, sh_k), e=lerp(-8, -70, sh_k), hand="open", habs=PI * 0.92),
                   armR=dict(a=lerp(42, 58, sh_k), e=lerp(-40, -70, sh_k), hand="hold", prop=pliers_prop(0.62, 0.08)))
    C.draw(ctx, "surgeon", sur, t)
    return sepia(to_rgb(s), i)


# =====================================================================  scene 6: mirror, "ozroq oling"
def s6(i, t):
    t0 = T.scene_start(6)
    t_oz, t_d = cue(6, "«ozroq"), cue(6, "deysiz-a?")
    drift = lerp(-22, 22, eio(ramp(t, t0, T.scene_end(6) - t0)))
    s, ctx = surface()
    camera(ctx, 1.0, 540 + drift * 0.5, 960)
    vgrad(ctx, -300, -300, 1700, 2600, [(0, TEAL), (1, DTEAL)])
    for r in range(5):
        for c in range(-1, 6):
            S.ikat_motif(ctx, c * 230 + (115 if r % 2 else 0), 120 + r * 300, 0.9, GOLD, 0.15)

    def reflection(c):
        c.save()
        c.translate(-drift * 0.3, 0)
        vgrad(c, -200, 300, 1500, 1300, [(0, hx("2C7A77")), (1, hx("1B5655"))])
        glow(c, 300, 420, 420, hx("FFD58A"), 0.35)
        glow(c, 860, 420, 420, hx("FFD58A"), 0.35)
        c.rectangle(-200, 1250, 1500, 400)
        fill(c, hx("A9764A"))
        rrect(c, 880, 560, 170, 520, 12)  # door in the back
        fs(c, hx("5E3720"), 5)
        P.chair_back(c, 500, 1400 - 96 * 1.25, 1.0)
        nod = 0.10 * math.sin((t - t0) * 7) * ramp(t, t_oz - 0.3, 0.3)
        barb = dict(x=830, y=1470, s=1.2, seed=2, turn=-0.35, look=(-0.4, 0.2), mouth="smile", tilt=nod,
                    armR=dict(a=40, e=-80, hand="hold", prop=scissors_prop(0.8, 0.15)),
                    armL=dict(a=14, e=-6, hand="fist"))
        C.draw(c, "barber", barb, t)
        hp = dict(x=500, y=1400, s=1.25, legs="sit", cape=True, seed=1, mouth="smile_open", brows="normal",
                  look=(0.0, 0.0))
        pk = eo(ramp(t, t0 + 0.25, 0.3))
        jig = 0.06 * math.sin((t - t_oz) * 22) * bump(t, t_oz, t_oz + 0.4)
        if pk > 0:
            tgt = (lerp(400, 290, pk), lerp(1250, 1020, pk))
            a = C.ik("hero", hp, -1, tgt, bend=-1)
            hp["armL"] = dict(a=a["a"], e=a["e"], hand="pinch", habs=PI + jig, hs=1.6, out=True, mirror=True,
                              **{"from": (-112, -30)})
        if t >= t_oz:
            hp.update(brows="raised", look=(0.0, 0.0))
        if t >= t_d:
            w = bump(t, t_d, t_d + 0.55)
            hp.update(wink=(1, 1.0 if w > 0.25 else 0.0), mouth="smirk", brows="smug")
        C.draw(c, "hero", hp, t)
        P.chair_front(c, 500, 1400 - 96 * 1.25, 1.0, base_y=330)
        c.rectangle(-300, 0, 1700, 2000)
        fill(c, hx("CFE3DF"), 0.10)
        c.restore()
    S.mirror_frame(ctx, 90, 320, 900, 1130, inner=reflection)
    # counter
    cel(ctx, lambda c: rrect(c, 40, 1450, 1000, 50, 10), hx("EFE6D6"), hx("D8CCB6"), d=(30, 0))
    ctx.rectangle(60, 1500, 960, 500)
    fs(ctx, hx("5E3720"), 6)
    P.bottle(ctx, 860, 1450, 90, TEAL)
    P.bottle(ctx, 920, 1450, 120, GOLD)
    # foreground: back of the hero's head (over the shoulder)
    C.hero_back(ctx, 300 - drift * 0.6, 1760, 1.75, t)
    rgb = to_rgb(s)
    # 'Bugun' -> colour returns with a soft wipe (sepia -> colour)
    k = ramp(t, t0, 0.45)
    if k < 1:
        wx = lerp(-250, 1330, eio(k))
        xs = np.arange(W, dtype=np.float32)
        m = np.clip((xs - wx) / 220 + 0.5, 0, 1)[None, :, None]   # 1 = still sepia (right of wipe)
        rgb = rgb * (1 - m) + sepia(rgb, i) * m
    return rgb


# =====================================================================  scene 7: split screen
def hair_bits(ctx, t, t_start, origin):
    for n in range(40):
        ts = t_start + n * 0.07
        a = t - ts
        if a < 0 or a > 1.2:
            continue
        rx = ((n * 37) % 11 - 5) * 9
        x = origin[0] + rx + 30 * a + 8 * math.sin(a * 9 + n)
        y = origin[1] + 260 * a * a + 60 * a
        ang = n * 1.3 + a * 5
        line(ctx, [(x, y), (x + 14 * math.cos(ang), y + 14 * math.sin(ang))], color=hx("2A1A12"), width=4.5,
             alpha=1 - clamp01((a - 0.9) / 0.3))


def s7(i, t):
    t0 = T.scene_start(7)
    t_soch, t_qon = cue(7, "sochdan"), cue(7, "qon")
    z = 1.0 + 0.03 * eio(ramp(t, t0, T.scene_end(7) - t0))
    # ---- left half (colour, modern)
    sL, cL = surface(540, H)
    camera(cL, z * 1.12, 290, 1030, w=540)
    cL.save()
    cL.translate(-240, 0)
    S.barbershop(cL, t, pole_phase=t * 0.9, pole=False)
    cL.restore()
    P.chair_back(cL, 250, 1330, 1.0)
    hp = dict(x=250, y=1450, s=1.08, legs="sit", cape=True, seed=1, mouth="smile", brows="normal",
              turn=-0.12, look=(0.6, -0.4))
    C.draw(cL, "hero", hp, t)
    P.chair_front(cL, 250, 1330, 1.0)
    ear = (250 + 128 * 1.08, 1450 - (96 + 262) * 1.08 + 20)
    snip = 0.05 + 0.30 * (0.5 + 0.5 * math.sin(t * 34))
    bp = dict(x=540, y=1560, s=1.08, seed=2, turn=-0.5, look=(-0.6, 0.3), mouth="smile", brows="focus")
    a = C.ik("barber", bp, -1, (ear[0] + 70, ear[1] + 10), bend=1)
    bp["armL"] = dict(a=a["a"], e=a["e"], hand="hold", prop=scissors_prop(0.75, snip, rot=-0.5))
    C.draw(cL, "barber", bp, t)
    hair_bits(cL, t, t0 + 0.1, (ear[0] + 14, ear[1] + 30))
    left = to_rgb(sL)
    # ---- right half (sepia, medieval)
    sR, cR = surface(540, H)
    camera(cR, z * 1.28, 285, 1080, w=540)
    cR.save()
    cR.translate(-300, 0)
    S.med_interior(cR, t, window=False)
    cR.restore()
    P.stool(cR, 230, 1340, 0.72)
    pat = dict(x=230, y=1445, s=1.0, legs="sit", seed=4, turn=-0.35, look=(-0.8, -0.2), mouth="worried",
               brows="worried", sweat=1.0)
    P.staff(cR, 110, 860, 1470, r=20)
    a1 = C.ik("patient", pat, -1, (112, 1160), bend=1)
    pat["armL"] = dict(a=a1["a"], e=a1["e"], hand="grip", habs=PI / 2 * 0 + 0.0)
    a2 = C.ik("patient", pat, 1, (440, 1170), bend=-1)
    pat["armR"] = dict(a=a2["a"], e=a2["e"], hand="open")
    C.draw(cR, "patient", pat, t)
    sur = dict(x=560, y=1560, s=1.05, seed=5, turn=-0.45, look=(-0.7, 0.6), mouth="flat", brows="focus", flip=False)
    elbow = C.arm_geom(1, dict(C.ARM_DEF, **pat["armR"]), (0, 0))[0]
    shw = C.shoulder_world("patient", pat, 1)
    elbow_w = (shw[0] + elbow[0] * pat["s"], shw[1] + elbow[1] * pat["s"])
    bowl_pt = (elbow_w[0], elbow_w[1] + 70)
    a3 = C.ik("surgeon", sur, -1, (bowl_pt[0] + 30, bowl_pt[1] + 10), bend=1)
    sur["armL"] = dict(a=a3["a"], e=a3["e"], hand="fist")
    C.draw(cR, "surgeon", dict(sur, parts="body"), t)
    P.bowl(cR, bowl_pt[0], bowl_pt[1], 0.8)
    C.draw(cR, "surgeon", dict(sur, parts="arms"), t)
    right = sepia(to_rgb(sR), i)
    # brightness per cue
    kl = eo(ramp(t, t_soch, 0.2))
    kr = eo(ramp(t, t_qon, 0.2))
    lf = 1.0 + 0.10 * kl - 0.40 * kr
    rf = 1.0 - 0.38 * kl * (1 - kr) + 0.10 * kr
    lf += 0.04 * bump(t, t_qon, t_qon + 0.25) * 0
    rgb = np.concatenate([left * lf, right * rf], axis=1)
    # divider wiping in (top -> bottom)
    s, ctx = surface()
    k = eo(ramp(t, t0, 0.35))
    rrect(ctx, 532, -20, 16, 20 + 1940 * k, 6)
    fs(ctx, GOLD, 5)
    dv = np_view(s).astype(np.float32)
    a_ = dv[..., 3:4] / 255.0
    rgb = rgb * (1 - a_) + dv[..., [2, 1, 0]]
    return rgb


# =====================================================================  scene 8: "Ishonmayapsizmi?" + whip-pan
@functools.lru_cache(maxsize=1)
def blurred_shop():
    s, ctx = surface()
    camera(ctx, 1.7, 560, 760)
    S.barbershop(ctx, 0.0, 0.0, pole=False)
    from scipy.ndimage import gaussian_filter
    a = to_rgb(s)
    small = a[::4, ::4]
    small = gaussian_filter(small, sigma=(3.5, 3.5, 0))
    big = np.repeat(np.repeat(small, 4, 0), 4, 1)[:H, :W]
    return gaussian_filter(big, sigma=(2, 2, 0)).astype(np.float32)


def hero_closeup(i, t):
    t_i, t_b = cue(8, "Ishonmayapsizmi?"), cue(8, "Isboti")
    bg = blurred_shop()
    dx = int(10 * math.sin(t * 0.6))
    rgb = np.roll(bg, dx, axis=1)
    s, ctx = surface()
    tau = t - t_i
    shake_ = 0.42 * math.sin(TAU * 2.6 * tau) * math.exp(-1.6 * tau) if tau >= 0 else 0.0
    hp = dict(x=540, y=1900, s=2.25, seed=1, turn=shake_, look=(-shake_ * 0.4, 0), mouth="smirk", brows="smug",
              tilt=0.04 * math.sin(t * 1.3))
    if t >= t_b:
        k = eo(ramp(t, t_b, 3 / F))
        a = C.ik("hero", hp, 1, (lerp(720, 975, k), lerp(1520, 1235, k)), bend=1)
        hp["armR"] = dict(a=a["a"], e=a["e"], hand="point", hrot=0.0)
        hp.update(turn=0.35 * k, look=(0.9 * k, -0.1), mouth="smile_open", brows="raised")
    C.draw(ctx, "hero", hp, t)
    layer = np_view(s).astype(np.float32)
    al = layer[..., 3:4] / 255.0
    return rgb * (1 - al) + layer[..., [2, 1, 0]]


def entrance_shot(i, t, z=None, cy=None, extra=None):
    t_b = cue(8, "Isboti")
    s, ctx = surface()
    if z is None:
        k = eio(ramp(t, t_b + 0.3, T.scene_end(8) - t_b - 0.3))
        z, cy = lerp(1.25, 1.6, k), lerp(1000, 980, k)
    camera(ctx, z, lerp(640, 680, 0.5), cy)
    S.entrance(ctx, t, pole_phase=t * 0.8, pole_kw=extra)
    return to_rgb(s)


def s8(i, t):
    t_b = cue(8, "Isboti")
    f_b = int(round(t_b * F))
    f_w = f_b + 3            # whip starts 3 frames after the point begins
    k = i - f_w
    if k < 0:
        return hero_closeup(i, t)
    if k >= 6:
        return entrance_shot(i, t)
    u = eio((k + 1) / 6.0)
    A = hero_closeup(i, t)
    B = entrance_shot(i, t)
    off = int(u * W)
    out = np.empty_like(A)
    out[:, :W - off] = A[:, off:]
    out[:, W - off:] = B[:, :off]
    return hblur(out, 25 + 90 * math.sin(PI * (k + 0.5) / 6))


# =====================================================================  scene 9: pole close-up
POLE_W = dict(cx=700, y0=720, y1=1220, R=52)


def s9(i, t):
    t0 = T.scene_start(9)
    t_q, t_o = cue(9, "Qizil"), cue(9, "Oq")
    k = eio(ramp(t, t0, T.scene_end(9) - t0))
    z = 3.4
    cy = lerp(1110, 880, k)
    red = eo(ramp(t, t_q, 0.25)) * (1 - eo(ramp(t, t_o, 0.35)) * 0.85)
    wdim = red
    wrap = eo(ramp(t, t_o, 0.35)) * (1 - eio(ramp(t, t_o + 1.25, 0.55)))
    s, ctx = surface()
    camera(ctx, z, 700, cy)
    S.entrance(ctx, t, pole_phase=0.0, pole_kw=dict(skip=True))
    P.pole(ctx, 700, 720, 1220, 52, t * 0.8, red_glow=red, white_dim=wdim * (1 - wrap),
           wrap=wrap, wrap_phase=t * 2.2)
    if wrap > 0.05:
        for n in range(3):
            a = t * 3 + n * 2.1
            sparkle(ctx, 700 + 80 * math.cos(a), cy + 120 * math.sin(a * 0.7), 10 * wrap, alpha=wrap)
    return to_rgb(s)


# =====================================================================  scene 10: pole -> wooden staff -> pole
def s10(i, t):
    t0 = T.scene_start(10)
    t_q, t_r = cue(10, "qisgan"), cue(10, "ramzi.")
    back = eio(ramp(t, t_r, 0.45))
    fade = eio(ramp(t, t0, 0.55))
    wood = eio(ramp(t, t0 + 0.12, 0.6)) * (1 - back)
    stripe = (1 - fade) + fade * back
    caps = (1 - eio(ramp(t, t0, 0.45))) + back * eio(ramp(t, t_r + 0.1, 0.35))
    caps = clamp01(caps)
    sep_amt = eio(ramp(t, t0 + 0.2, 0.55)) * (1 - back)
    R = lerp(52, 30, wood)
    # camera: pull back during morph, slow push-in on the hand, pull back on morph back
    z0 = lerp(3.4, 2.5, eio(ramp(t, t0, 0.7)))
    z1 = z0 + 0.45 * eio(ramp(t, t0 + 0.8, t_r - t0 - 0.8))
    z = lerp(z1, 1.9, eio(ramp(t, t_r, 0.6)))
    cy = lerp(lerp(880, 990, eio(ramp(t, t0, 0.7))), 970, back)
    cx = lerp(700, 724, eio(ramp(t, t0 + 0.8, 1.5)) * (1 - back))
    s, ctx = surface()
    camera(ctx, z, cx, cy)
    S.entrance(ctx, t, pole_phase=0.0, pole_kw=dict(skip=True))
    if wood > 0.02:  # medieval room fades in behind the wooden staff
        ctx.save()
        ctx.identity_matrix()
        camera(ctx, 1.15 + 0.08 * (z - 1.9), 300, 960)
        ctx.push_group()
        S.med_interior(ctx, t, window=True)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(wood)
        ctx.restore()
    P.pole(ctx, 700, 720 - 120 * wood, 1220 + 200 * wood, R, t * 0.8 * (1 - wood), stripe_a=stripe, wood=wood,
           caps=caps, glass=1 - wood)
    # the patient's hand grips the staff
    hin = eo(ramp(t, t0 + 0.95, 0.55)) * (1 - eio(ramp(t, t_r, 0.3)))
    vein_pts = None
    if hin > 0.01:
        sq = bump(t, t_q, t_q + 0.55)
        shk = 1.4 * math.sin(t * 60) * (sq > 0.05)
        hx_, hy_ = 700 + 260 * (1 - hin) + shk, 1000
        sp = 1.0 - 0.10 * sq
        # forearm (sleeve + skin) coming from the right
        tube(ctx, [(hx_ + 60, hy_ + 4), (hx_ + 190, hy_ + 60), (hx_ + 420, hy_ + 150)], 66, SKIN)
        tube(ctx, [(hx_ + 300, hy_ + 108), (hx_ + 560, hy_ + 220)], 84, hx("8C8A84"))
        # back of the hand + fingers wrapped across the front of the staff
        cel(ctx, lambda c: rrect(c, hx_ + R * 0.25, hy_ - 40, 88, 82, 30), SKIN, SKIN_D, d=(8, 6), ol=6)
        for k in range(4):
            y = hy_ - 30 + k * 20 * sp + 3 * sq
            tube(ctx, [(hx_ + R * 0.95, y), (hx_ - R * 0.55, y + 1), (hx_ - R * 1.08, y + 3)], 19, SKIN, ol=4)
        tube(ctx, [(hx_ + R * 1.1, hy_ - 44), (hx_ + R * 0.1, hy_ - 46), (hx_ - R * 0.45, hy_ - 40)], 21, SKIN, ol=4)
        if sq > 0.05:
            for k in range(3):
                a = -0.9 + k * 0.6
                x0, y0 = hx_ + 105 * math.cos(a) + 40, hy_ - 10 + 90 * math.sin(a)
                line(ctx, [(x0, y0), (x0 + 22 * math.cos(a), y0 + 22 * math.sin(a))], width=6, alpha=sq)
            for k in range(2):
                yy = hy_ - 110 - k * 30
                line(ctx, [(hx_ - R - 18, yy), (hx_ - R - 34, yy - 8)], width=4, alpha=sq * 0.8)
                line(ctx, [(hx_ + R + 18, yy), (hx_ + R + 34, yy - 8)], width=4, alpha=sq * 0.8)
        vein = eo(ramp(t, t_q, 0.35))
        if vein > 0:
            pts = []
            n = 24
            for k in range(int(n * vein) + 1):
                u = k / n
                pts.append(ctx.user_to_device(lerp(hx_ + 120, hx_ + 330, u), lerp(hy_ + 30, hy_ + 118, u) + 6 * math.sin(u * 9)))
            if len(pts) >= 2:
                vein_pts = pts
    rgb = to_rgb(s)
    if sep_amt > 0.001:
        rgb = sepia(rgb, i, amount=sep_amt)
    if vein_pts is not None:  # the vein stays blue (drawn after the sepia grade)
        vs, vc = surface()
        line(vc, vein_pts, color=hx("2F6FB5"), width=9, smooth_=True)
        line(vc, vein_pts, color=hx("7FB2E8"), width=3, smooth_=True, alpha=0.8)
        lay = np_view(vs).astype(np.float32)
        al = lay[..., 3:4] / 255.0
        rgb = rgb * (1 - al) + lay[..., [2, 1, 0]]
    return rgb


# =====================================================================  scene 11: CTA logo
@functools.lru_cache(maxsize=1)
def logo_surface():
    from PIL import Image, ImageDraw
    im = Image.open(T.os.path.join(T.ROOT, "assets", "logo.png")).convert("RGBA")
    w, h = im.size
    mask = Image.new("L", (w * 4, h * 4), 0)
    ImageDraw.Draw(mask).ellipse((4 * 5, 4 * 5, 4 * (w - 5), 4 * (h - 5)), fill=255)
    mask = mask.resize((w, h), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    a[..., 3] = a[..., 3] * np.asarray(mask).astype(np.float32) / 255.0
    pm = a.copy()
    pm[..., :3] *= pm[..., 3:4] / 255.0
    bgra = np.empty((h, w, 4), np.uint8)
    bgra[..., 0] = pm[..., 2]
    bgra[..., 1] = pm[..., 1]
    bgra[..., 2] = pm[..., 0]
    bgra[..., 3] = pm[..., 3]
    s = cairo.ImageSurface.create_for_data(memoryview(bgra.reshape(-1)), cairo.FORMAT_ARGB32, w, h, w * 4)
    s._keep = bgra
    return s, w


LOGO_C = (540, 805)
LOGO_R = 240


def s11(i, t):
    t0 = T.scene_start(11)
    t_b, t_s, t_y = cue(11, "Buni"), cue(11, "sartaroshingizga"), cue(11, "yuboring.")
    z = 1.0 + 0.03 * eio(ramp(t, t0, T.scene_end(11) - t0))
    s, ctx = surface()
    camera(ctx, z, 540, 960)
    S.teal_ikat(ctx, t)
    # pop 0 -> 110 % -> 100 %
    u = ramp(t, t_b, 0.38)
    sc = 1.1 * eo(u / 0.6) if u < 0.6 else lerp(1.1, 1.0, eio((u - 0.6) / 0.4))
    if sc > 0.01:
        cx, cy = LOGO_C
        glow(ctx, cx, cy, LOGO_R * 1.7 * sc, GOLD, 0.35)
        # rotating red-white striped ring
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(sc, sc)
        r_in, r_out = LOGO_R + 8, LOGO_R + 30
        circle(ctx, 0, 0, r_out + 3)
        fill(ctx, OL)
        n = 36
        rot = t * 1.4
        for k in range(n):
            a0 = rot + k * TAU / n
            a1 = a0 + TAU / n
            ctx.new_path()
            ctx.arc(0, 0, r_out, a0, a1)
            ctx.arc_negative(0, 0, r_in, a1, a0)
            ctx.close_path()
            fill(ctx, POLE_R if k % 2 == 0 else WHITE)
        circle(ctx, 0, 0, r_in)
        fill(ctx, OL)
        ls, lw_ = logo_surface()
        k_ = (LOGO_R * 2) / lw_
        ctx.save()
        ctx.scale(k_, k_)
        ctx.translate(-lw_ / 2, -lw_ / 2)
        ctx.set_source_surface(ls, 0, 0)
        ctx.get_source().set_filter(cairo.FILTER_BEST)
        ctx.paint()
        ctx.restore()
        ctx.restore()
    # paper plane from the logo toward the upper right
    if t >= t_y:
        tp = ramp(t, t_y, 0.6)
        e = eio(tp)
        x0, y0 = LOGO_C[0] + 120, LOGO_C[1] - 60
        x1, y1 = 1000, 560
        px = lerp(x0, x1, e)
        py = lerp(y0, y1, e) - 120 * math.sin(PI * e)
        trail = []
        for k in range(14):
            ee = max(0.0, e - k * 0.03)
            trail.append((lerp(x0, x1, ee), lerp(y0, y1, ee) - 120 * math.sin(PI * ee)))
        ctx.save()
        ctx.set_dash([olw(ctx, 10), olw(ctx, 12)])
        line(ctx, trail, color=WHITE, width=5, alpha=0.8 * (1 - tp * 0.5))
        ctx.restore()
        P.paper_plane(ctx, px, py, 1.1 + 0.3 * e, rot=-0.55 + 0.3 * math.sin(PI * e), alpha=1 - clamp01((tp - 0.85) / 0.15))
    rgb = to_rgb(s)
    if t >= t_s:
        import text as TX
        d = i - int(round(t_s * F))
        sc = (0.8 + 0.2 * eo(d / 5.0)) * z
        TX.composite(rgb, channel_name_img(), 540, (LOGO_C[1] + LOGO_R + 160 - 960) * z + 960, sc)
    return rgb


@functools.lru_cache(maxsize=1)
def channel_name_img():
    import text as TX
    im = TX.text_line("Bilib Oldim", 132, fill=(255, 255, 255), stroke=11, stroke_fill=(0xE0, 0xB0, 0x4B))
    return TX.with_shadow(im, off=8, blur=10, alpha=0.5)


# =====================================================================  scene 12: back to the shop (loop)
def s12(i, t):
    t0 = T.scene_start(12)
    t_ot, t_d = cue(12, "«o'tiring»"), cue(12, "desa...")
    t_end = (T.N_FRAMES - 1) / F
    # target = scene 1 state one frame before frame 0  (seamless loop)
    tgt_t = -1.0 / F
    b1 = barber_s1_pose(tgt_t, tgt_t, None)
    h1 = hero_s1_pose(tgt_t, cue(1, "To'xtang!"), cue(1, "Sartaroshlar"))
    # barber: smiles, pliers hidden behind his back, gestures to the chair
    g = eo(ramp(t, t_ot, 0.25))
    turnb = eio(ramp(t, t_d, t_end - t_d))
    barber = dict(BARB, seed=2, turn=lerp(-0.25, -0.45, g), look=(-0.6, 0.1), mouth="smile_open", brows="raised",
                  armR=dict(a=8, e=-30, hand="fist", behind=True),
                  armL=dict(a=lerp(12, 62, g), e=lerp(-8, -12, g), hand="open" if g > 0.3 else "fist", hrot=-0.3 * g))
    if t >= t_d:
        k = turnb
        barber.update(turn=lerp(-0.45, b1["turn"], k), look=(lerp(-0.6, b1["look"][0], k), 0.0),
                      mouth="smile" if k > 0.5 else "smile_open", brows="normal" if k > 0.5 else "raised")
        if k > 0.35:
            kk = eo((k - 0.35) / 0.65)
            barber["armR"] = dict(a=lerp(10, b1["armR"]["a"], kk), e=lerp(-60, b1["armR"]["e"], kk), hand="hold",
                                  prop=pliers_prop(1.25, 0.10, 0.0, t, offset=40))
        barber["armL"] = dict(a=lerp(62, b1["armL"]["a"], k), e=lerp(-12, b1["armL"]["e"], k), hand="fist")
        if i == T.N_FRAMES - 1:
            barber = dict(b1)
    # hero walks in from the left, then hops into the chair
    walk_k = ramp(t, t0, t_d - t0)
    hx0 = lerp(-170, 360, eio(walk_k) * 0.15 + walk_k * 0.85)
    sit_k = eio(ramp(t, t_d, 0.28))
    hero_mode = "front"
    if sit_k <= 0:
        hero = dict(x=hx0, y=1640, s=1.22, legs="walk", walk=(t - t0) * 1.7, seed=1, turn=0.3, look=(0.7, -0.1),
                    mouth="smile_open", brows="raised")
    else:
        jx = lerp(360, HERO_SEAT["x"], sit_k)
        jy = lerp(1640, HERO_SEAT["y"], sit_k) - 110 * math.sin(PI * sit_k)
        hero = dict(x=jx, y=jy, s=1.22, legs="sit" if sit_k > 0.5 else "stand", seed=1, turn=lerp(0.3, h1["turn"], sit_k),
                    look=h1["look"], mouth="smile_open" if sit_k < 0.6 else h1["mouth"],
                    brows="raised" if sit_k < 0.6 else h1["brows"])
        hero_mode = "seated" if sit_k > 0.55 else "front"
    cape_k = eo(ramp(t, t_d + 0.2, 0.22))
    tc = t - (t_end - tgt_t)   # character clock: breathing/blinks land exactly on scene 1's at the loop point
    s, ctx = surface()
    camera(ctx, SHOP_Z, SHOP_CX + 6 * math.sin(tgt_t * 0.7) * turnb + 6 * math.sin(t * 0.7) * (1 - turnb), SHOP_CY)
    S.barbershop(ctx, t, pole_phase=(tgt_t + (t - t_end)) * 0.9)
    C.draw(ctx, "barber", barber, tc)
    P.chair_back(ctx, 500, SEAT_Y)
    if hero_mode == "seated":
        if cape_k < 1:
            C.draw(ctx, "hero", hero, tc)
        if cape_k > 0:
            hc = dict(hero, cape=True, alpha=cape_k)
            if i == T.N_FRAMES - 1:
                hc = dict(h1)
            C.draw(ctx, "hero", hc, tc)
    P.chair_front(ctx, 500, SEAT_Y)
    if hero_mode == "front":
        C.draw(ctx, "hero", hero, tc)
    if cape_k > 0 and cape_k < 1:
        for k in range(3):
            line(ctx, [(330 + k * 40, 1000 - 80 * cape_k), (300 + k * 40, 1080 - 80 * cape_k)], width=5, alpha=1 - cape_k)
    return to_rgb(s)


SCENES = {1: s1, 2: s2, 3: s3, 4: s4, 5: s5, 6: s6, 7: s7, 8: s8, 9: s9, 10: s10, 11: s11, 12: s12}
