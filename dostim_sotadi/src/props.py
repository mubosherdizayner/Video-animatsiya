# Flat props for the silhouette world.
import math, random
import cairo
from style import (hx, mix, darken, lighten, rgb, poly, smooth_path, ellipse, fill_ellipse, rrect, glow, acc,
                   clamp01, ease, ease_out, ease_out_back)

def pedestal(ctx, x, y, w, h, col, seed=1):
    """rough stone block; (x,y) = bottom centre"""
    rnd = random.Random(seed)
    j = lambda: rnd.uniform(-0.04, 0.04) * w
    pts = [(x - w * 0.62 + j(), y), (x - w * 0.5 + j(), y - h * 0.55), (x - w * 0.46 + j(), y - h + j() * 0.3),
           (x + w * 0.46 + j(), y - h + j() * 0.3), (x + w * 0.52 + j(), y - h * 0.5), (x + w * 0.64 + j(), y)]
    poly(ctx, pts); rgb(ctx, col); ctx.fill()
    # top slab lip
    poly(ctx, [(x - w * 0.56, y - h + 2), (x - w * 0.52, y - h - h * 0.09), (x + w * 0.52, y - h - h * 0.09), (x + w * 0.56, y - h + 2)])
    rgb(ctx, lighten(col, 0.08)); ctx.fill()
    return y - h - h * 0.09

def button(ctx, x, y, rx, col, press=0.0, glow_a=0.0, glow_c=None, rim=None):
    """dome button on a flat collar; (x,y) = collar top centre"""
    if glow_a > 0:
        glow(ctx, x, y - rx * 0.3, rx * 3.2, glow_c or col, glow_a)
    ry = rx * (0.55 - 0.33 * press)
    collar = darken(col, 0.45)
    ellipse(ctx, x, y + rx * 0.06, rx * 1.28, rx * 0.26); rgb(ctx, collar); ctx.fill()
    ctx.save()
    ctx.rectangle(x - rx * 2, y - rx * 2, rx * 4, rx * 2 + 0.5); ctx.clip()
    ellipse(ctx, x, y, rx, ry); rgb(ctx, col); ctx.fill()
    # flat shade on the lower-right half of the dome
    ellipse(ctx, x + rx * 0.18, y + ry * 0.05, rx * 0.86, ry * 0.82); rgb(ctx, darken(col, 0.13)); ctx.fill()
    ellipse(ctx, x - rx * 0.08, y - ry * 0.12, rx * 0.84, ry * 0.8); rgb(ctx, col); ctx.fill()
    ellipse(ctx, x - rx * 0.36, y - ry * 0.52, rx * 0.26, ry * 0.16, -0.25); rgb(ctx, lighten(col, 0.3), 0.8); ctx.fill()
    ctx.restore()
    if rim is not None:
        ctx.save(); ctx.rectangle(x - rx * 2, y - rx * 2, rx * 4, rx * 2); ctx.clip()
        ctx.set_line_width(max(1.5, rx * 0.05))
        ellipse(ctx, x, y, rx, ry); ctx.set_source_rgba(rim[0][0], rim[0][1], rim[0][2], rim[1]); ctx.stroke()
        ctx.restore()

def banknote(ctx, x, y, w, rot, flip, col, a=1.0):
    """flat banknote; flip -1..1 squashes it like a fluttering sheet"""
    h = w * 0.48
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(max(0.08, abs(flip)), 1)
    rgb(ctx, col if flip > 0 else darken(col, 0.12), a)
    ctx.rectangle(-w / 2, -h / 2, w, h); ctx.fill()
    rgb(ctx, darken(col, 0.2), a * 0.9)
    ellipse(ctx, 0, 0, h * 0.3, h * 0.3); ctx.fill()
    ctx.rectangle(-w / 2 + w * 0.07, -h / 2 + h * 0.14, w * 0.13, h * 0.72); ctx.fill()
    ctx.rectangle(w / 2 - w * 0.2, -h / 2 + h * 0.14, w * 0.13, h * 0.72); ctx.fill()
    ctx.restore()

def money_pile(ctx, x, y, size, col, grow=1.0, seed=3, glow_a=0.0, scatter=0.0, t=0.0):
    """stack of banknote bricks; (x,y) bottom centre; grow 0..1 builds it up layer by layer"""
    if glow_a > 0:
        glow(ctx, x, y - size * 0.4, size * 1.8, col, glow_a)
    rnd = random.Random(seed)
    bw, bh = size * 0.42, size * 0.15
    layers = [(4, 0), (3, 1), (2, 2), (1, 3)]
    total = sum(n for n, _ in layers)
    k = 0
    side = darken(col, 0.22); top = col; band = darken(col, 0.38)
    for n, row in layers:
        for i in range(n):
            k += 1
            g = clamp01(grow * total - (k - 1))
            if g <= 0: continue
            bx = x + (i - (n - 1) / 2) * bw * 1.02 + rnd.uniform(-2, 2)
            by = y - row * bh * 1.02
            drop = (1 - ease_out(g)) * size * 1.2
            ox = oy = 0.0; rot = 0.0; al = 1.0
            if scatter > 0:
                s = clamp01(scatter * 1.6 - rnd.uniform(0, 0.6))
                ox = s * s * size * rnd.uniform(4, 9); oy = -s * size * rnd.uniform(0.6, 2.4) + math.sin(t * 6 + k) * 4 * s
                rot = s * rnd.uniform(-2, 2); al = 1 - clamp01(s * 1.1 - 0.1)
                if al <= 0: continue
            ctx.save(); ctx.translate(bx + ox, by - drop + oy); ctx.rotate(rot)
            rgb(ctx, side, al); ctx.rectangle(-bw / 2, -bh, bw, bh); ctx.fill()
            rgb(ctx, top, al); ctx.rectangle(-bw / 2, -bh, bw, bh * 0.4); ctx.fill()
            rgb(ctx, band, al); ctx.rectangle(-bw * 0.12, -bh, bw * 0.24, bh); ctx.fill()
            ctx.restore()

def sack(ctx, x, y, s, col, accent=None):
    """money sack (silhouette), (x,y) = neck tie point"""
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s); rgb(ctx, col)
    ctx.move_to(-3, 0); ctx.curve_to(-14, 4, -18, 22, -10, 30); ctx.curve_to(-4, 34, 10, 34, 15, 28)
    ctx.curve_to(22, 18, 12, 4, 3, 0); ctx.close_path(); ctx.fill()
    poly(ctx, [(-5, -5), (-1, 1), (1, 1), (5, -5), (0, -2)]); ctx.fill()
    if accent:
        rgb(ctx, accent)
        for (ax, ay, r) in ((-5, -6, 0.5), (3.5, -6.5, -0.4)):
            ctx.save(); ctx.translate(ax, ay); ctx.rotate(r); ctx.rectangle(-3, -1.5, 6, 3); ctx.fill(); ctx.restore()
    ctx.restore()

def tree(ctx, x, y, s, col, t, seed=2, wind=1.0, leaf_col=None):
    """large flat tree: trunk + canopy of overlapping blobs that sway"""
    rnd = random.Random(seed)
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    rgb(ctx, col)
    poly(ctx, [(-9, 0), (-6, -60), (-14, -92), (-10, -94), (-2, -70), (2, -96), (6, -96), (5, -66), (16, -90), (20, -88), (8, -56), (9, 0)]); ctx.fill()
    blobs = [(rnd.uniform(-70, 70), rnd.uniform(-170, -95), rnd.uniform(28, 46)) for _ in range(16)]
    for i, (bx, by, br) in enumerate(blobs):
        sway = math.sin(t * 1.3 + i * 0.7) * 2.2 * wind * (1 + (-by - 95) / 80)
        ox = sway + math.sin(t * 0.7 + i) * 0.8
        rgb(ctx, col if i % 3 else (leaf_col or col))
        ellipse(ctx, bx + ox, by, br * 1.1, br * 0.92); ctx.fill()
    ctx.restore()

def leaf(ctx, x, y, s, rot, col, a=1.0):
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(s, s); rgb(ctx, col, a)
    ctx.move_to(-4, 0); ctx.curve_to(-2, -2.6, 2, -2.6, 4, 0); ctx.curve_to(2, 2.6, -2, 2.6, -4, 0); ctx.fill(); ctx.restore()

def sori(ctx, x0, x1, y, depth, col, rail=True):
    """wooden so'ri platform: (x0..x1) at surface height y; legs down by depth"""
    rgb(ctx, col)
    th = 16
    ctx.rectangle(x0, y, x1 - x0, th); ctx.fill()
    for lx in (x0 + 10, (x0 + x1) / 2, x1 - 26):
        ctx.rectangle(lx, y + th, 16, depth - th); ctx.fill()
    if rail:
        ry = y - 92
        ctx.rectangle(x0 + 4, ry, x1 - x0 - 8, 10); ctx.fill()
        for px in range(int(x0 + 6), int(x1 - 6), 46):
            ctx.rectangle(px, ry, 8, 92); ctx.fill()
        ctx.rectangle(x1 - 14, ry, 10, 92); ctx.fill()

def darvoza(ctx, x, y, w, h, col, panel):
    """carved double gate with arch beam; (x,y) bottom-left"""
    rgb(ctx, col)
    ctx.rectangle(x - 26, y - h - 46, w + 52, 46); ctx.fill()                       # top beam
    poly(ctx, [(x - 36, y - h - 46), (x + w / 2, y - h - 92), (x + w + 36, y - h - 46)]); ctx.fill()
    ctx.rectangle(x - 26, y - h - 46, 26, h + 46); ctx.fill(); ctx.rectangle(x + w, y - h - 46, 26, h + 46); ctx.fill()
    ctx.rectangle(x, y - h, w, h); ctx.fill()
    # carved panels (lighter insets with a diamond/rosette)
    for i in range(2):
        lx = x + 12 + i * (w / 2)
        for j in range(3):
            py = y - h + 16 + j * (h - 24) / 3
            pw, ph = w / 2 - 24, (h - 24) / 3 - 14
            rgb(ctx, panel); rrect(ctx, lx, py, pw, ph, 6); ctx.fill()
            rgb(ctx, col)
            cx, cy = lx + pw / 2, py + ph / 2
            poly(ctx, [(cx, cy - ph * 0.34), (cx + pw * 0.26, cy), (cx, cy + ph * 0.34), (cx - pw * 0.26, cy)]); ctx.fill()
    ctx.rectangle(x + w / 2 - 3, y - h, 6, h); ctx.fill()

def flat_roofs(ctx, base_y, col, win_col, win_a, seed=4, x0=-200, x1=1300, scale=1.0, t=0.0):
    rnd = random.Random(seed)
    x = x0
    while x < x1:
        w = rnd.uniform(110, 210) * scale; h = rnd.uniform(70, 140) * scale
        rgb(ctx, col); ctx.rectangle(x, base_y - h, w, h + 400); ctx.fill()
        ctx.rectangle(x - 6 * scale, base_y - h - 8 * scale, w + 12 * scale, 9 * scale); ctx.fill()
        nw = rnd.randint(1, 3)
        for k in range(nw):
            if rnd.random() < 0.25: continue
            wx = x + w * (k + 0.5) / nw - 9 * scale; wy = base_y - h * 0.62
            fl = 1.0 + 0.06 * math.sin(t * 3 + x * 0.1 + k)
            rgb(ctx, win_col, min(1, win_a * fl)); ctx.rectangle(wx, wy, 18 * scale, 24 * scale); ctx.fill()
        x += w + rnd.uniform(-10, 40) * scale

def street_lamp(ctx, x, y, h, col, light, on=1.0, t=0.0, glow_a=0.55):
    rgb(ctx, col)
    ctx.rectangle(x - 4, y - h, 8, h); ctx.fill()
    poly(ctx, [(x - 12, y), (x + 12, y), (x + 6, y - 18), (x - 6, y - 18)]); ctx.fill()
    ctx.rectangle(x - 3, y - h - 6, 40, 6); ctx.fill()
    lx, ly = x + 34, y - h + 8
    fl = on * (0.9 + 0.06 * math.sin(t * 13.0) + 0.04 * math.sin(t * 31.0 + 1.3))
    if fl > 0.01:
        glow(ctx, lx, ly + 10, 260, light, glow_a * fl)
        # light cone to the ground
        g = cairo.LinearGradient(0, ly, 0, y + 20)
        g.add_color_stop_rgba(0, light[0], light[1], light[2], 0.22 * fl); g.add_color_stop_rgba(1, light[0], light[1], light[2], 0.0)
        ctx.set_source(g); poly(ctx, [(lx - 10, ly + 6), (lx + 10, ly + 6), (lx + 90, y + 24), (lx - 90, y + 24)]); ctx.fill()
    rgb(ctx, col); poly(ctx, [(lx - 16, ly + 2), (lx + 16, ly + 2), (lx + 9, ly - 12), (lx - 9, ly - 12)]); ctx.fill()
    rgb(ctx, mix(col, light, 0.85 * fl + 0.1)); ellipse(ctx, lx, ly + 6, 9, 5); ctx.fill()
    return lx, ly

def thread(ctx, p0, p1, sag, col, w=2.2, a=1.0, wob=0.0):
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + sag
    rgb(ctx, col, a); ctx.set_line_width(w); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(*p0); ctx.curve_to(p0[0] + (mx - p0[0]) * 0.9, my + wob, p1[0] + (mx - p1[0]) * 0.9, my - wob, *p1); ctx.stroke()

def cloud(ctx, x, y, w, col, a, seed=0):
    rnd = random.Random(seed)
    rgb(ctx, col, a)
    for k in range(7):
        bx = x + rnd.uniform(-0.45, 0.45) * w; by = y + rnd.uniform(-0.12, 0.08) * w
        r = rnd.uniform(0.12, 0.24) * w
        ellipse(ctx, bx, by, r * 1.5, r * 0.75); ctx.fill()
    ellipse(ctx, x, y + 0.08 * w, w * 0.55, w * 0.1); ctx.fill()

def stars(ctx, t, col, n=70, y1=900, seed=8, a=1.0):
    rnd = random.Random(seed)
    for k in range(n):
        x = rnd.uniform(-100, 1180); y = rnd.uniform(-50, y1); r = rnd.uniform(1.0, 2.6)
        tw = 0.55 + 0.45 * math.sin(t * rnd.uniform(1.5, 3.5) + rnd.uniform(0, 6.3))
        rgb(ctx, col, a * tw * rnd.uniform(0.5, 1.0)); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()

def lightning(ctx, x, y0, y1, col, a, seed=3, w=7):
    rnd = random.Random(seed)
    pts = [(x, y0)]; y = y0; cx = x
    while y < y1:
        y += rnd.uniform(40, 90); cx += rnd.uniform(-55, 55); pts.append((cx, min(y, y1)))
    ctx.set_line_join(cairo.LINE_JOIN_MITER)
    for lw, aa in ((w * 5, 0.18), (w * 2.2, 0.4), (w, 1.0)):
        rgb(ctx, col, a * aa); ctx.set_line_width(lw); poly(ctx, pts, close=False); ctx.stroke()
    bx, by = pts[len(pts) // 2]
    rgb(ctx, col, a * 0.8); ctx.set_line_width(w * 0.6)
    ctx.move_to(bx, by); ctx.line_to(bx + 70, by + 60); ctx.line_to(bx + 50, by + 140); ctx.stroke()

def paper_plane(ctx, x, y, s, rot, col, fold=1.0, a=1.0):
    """flat paper airplane pointing +x. fold 0 = flat sheet, 1 = plane"""
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(s, s)
    dark = darken(col, 0.25)
    if fold < 0.999:
        f = ease(fold)
        # sheet morphs: square -> folded triangle -> plane
        sq = [(-10, -10), (10, -10), (10, 10), (-10, 10)]
        pl = [(-12, -2), (14, 0), (-12, 5), (-6, 1)]
        pts = [(sq[i][0] + (pl[i][0] - sq[i][0]) * f, sq[i][1] + (pl[i][1] - sq[i][1]) * f) for i in range(4)]
        poly(ctx, pts); rgb(ctx, col, a); ctx.fill()
        if f > 0.3:
            poly(ctx, [(-12 * f, 0), (14 * f, 0), (-8 * f, 6 * f)]); rgb(ctx, dark, a * (f - 0.3) / 0.7); ctx.fill()
    else:
        poly(ctx, [(-12, -2), (14, 0), (-12, 5), (-6, 1)]); rgb(ctx, col, a); ctx.fill()
        poly(ctx, [(-12, -9), (14, 0), (-6, 1)]); rgb(ctx, lighten(col, 0.12), a); ctx.fill()
        poly(ctx, [(-6, 1), (14, 0), (-9, 7)]); rgb(ctx, dark, a); ctx.fill()
    ctx.restore()

def speech_bubble(ctx, x, y, w, h, col, pop=1.0, tail_dx=0.0):
    """rounded bubble centred at (x,y) with a tail pointing down"""
    s = ease_out_back(pop, 2.2)
    if s <= 0.01: return
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    rgb(ctx, col)
    rrect(ctx, -w / 2, -h / 2, w, h, h * 0.42); ctx.fill()
    poly(ctx, [(tail_dx - 26, h / 2 - 4), (tail_dx + 14, h / 2 - 4), (tail_dx - 18, h / 2 + 40)]); ctx.fill()
    ctx.restore()

def timer_icon(ctx, x, y, r, col, frac, a=1.0, ticks=12):
    ctx.save(); ctx.translate(x, y)
    rgb(ctx, col, a); ctx.set_line_width(r * 0.16)
    ctx.arc(0, 0, r, 0, 2 * math.pi); ctx.stroke()
    ctx.rectangle(-r * 0.22, -r * 1.42, r * 0.44, r * 0.26); ctx.fill()
    ctx.set_line_width(r * 0.12); ctx.move_to(r * 0.7, -r * 0.88); ctx.line_to(r * 0.9, -r * 1.08); ctx.stroke()
    # remaining time wedge
    rgb(ctx, col, a * 0.45)
    ctx.move_to(0, 0); ctx.arc(0, 0, r * 0.74, -math.pi / 2 + 2 * math.pi * frac, 1.5 * math.pi); ctx.close_path(); ctx.fill()
    # hand
    ang = -math.pi / 2 + 2 * math.pi * frac
    rgb(ctx, col, a); ctx.set_line_width(r * 0.13); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(0, 0); ctx.line_to(math.cos(ang) * r * 0.7, math.sin(ang) * r * 0.7); ctx.stroke()
    ctx.arc(0, 0, r * 0.12, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
