# Palettes, skia drawing helpers, sky / sun / moon, silhouette layer builders, paper grain and vignette.
import math, functools
import numpy as np
import skia

W, H, FPS = 1080, 1920, 30

def hx(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
def clamp01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def lerp(a, b, t): return a + (b - a) * t
def ease(x): x = clamp01(x); return x * x * (3 - 2 * x)
def ease_io(x): x = clamp01(x); return -(math.cos(math.pi * x) - 1) / 2
def ease_out(x): x = clamp01(x); return 1 - (1 - x) ** 3
def ease_in(x): x = clamp01(x); return x ** 3
def ease_out_back(x, s=1.7):
    x = clamp01(x) - 1; return x * x * ((s + 1) * x + s) + 1
def ramp(t, a, b): return clamp01((t - a) / (b - a)) if b > a else float(t >= a)

# ------------------------------------------------------------------ palettes
SHOM = dict(sky0=hx("#E9DEC6"), sky1=hx("#F4EDDF"), sun0=hx("#F2A55C"), sun1=hx("#E1742F"),
            L1=hx("#C6CEC9"), L2=hx("#AEBBB8"), L3=hx("#8C9FA1"), L4=hx("#56696D"), L5=hx("#2E3C40"),
            acc=hx("#E58A3C"), moon=hx("#EDE6D2"), sub_key=hx("#E1742F"))
TUN = dict(sky0=hx("#1F2A3A"), sky1=hx("#3A4A5C"), sun0=hx("#F2A55C"), sun1=hx("#E1742F"),
           L1=hx("#4A5A6E"), L2=hx("#36455A"), L3=hx("#283547"), L4=hx("#1A2433"), L5=hx("#10171F"),
           acc=hx("#E7A05C"), moon=hx("#EDE6D2"), sub_key=hx("#E7A05C"))
# derived ground tones (muted, never more saturated than the chapan)
SHOM.update(road=hx("#C8BEA9"), road_d=hx("#B1A997"), road_l=hx("#D6CDB9"), earth=hx("#C3B9A4"), earth_d=hx("#ADA593"),
            haze=mix(SHOM["L1"], SHOM["sky1"], 0.5), smoke=mix(SHOM["L1"], SHOM["sky1"], 0.3), win=hx("#E58A3C"),
            mid=mix(SHOM["L2"], SHOM["L3"], 0.5), mid2=mix(SHOM["L2"], SHOM["L3"], 0.8), glowc=hx("#F2A55C"))
TUN.update(road=hx("#334055"), road_d=hx("#2A3547"), road_l=hx("#3B495E"), earth=hx("#303C50"), earth_d=hx("#273244"),
           haze=mix(TUN["L1"], TUN["sky1"], 0.5), smoke=mix(TUN["L1"], TUN["sky1"], 0.45), win=hx("#E7A05C"),
           mid=mix(TUN["L2"], TUN["L3"], 0.5), mid2=mix(TUN["L2"], TUN["L3"], 0.8), glowc=hx("#E7A05C"))

def pal(u):
    """u=0 Shom, u=1 Tun"""
    u = clamp01(u)
    return {k: mix(SHOM[k], TUN[k], u) for k in SHOM}

HERO = dict(skin=hx("#EBC8A2"), skin_d=hx("#D8B089"), hair=hx("#2E231D"), eye=hx("#111111"),
            ch=hx("#3F7B61"), ch_d=hx("#2F634D"), ch_l=hx("#4C8A6E"), ikat1=hx("#6FA586"), ikat2=hx("#C7A548"),
            trim=hx("#BE8642"), belt=hx("#B4473B"), collar=hx("#E8E1D3"), doppi=hx("#1D2427"),
            doppi_w=hx("#EFEDE6"), boot=hx("#33241E"), boot_d=hx("#271B16"), trou=hx("#262A2D"), trou_d=hx("#1D2023"))
SCARF = hx("#9C7A72")

# ------------------------------------------------------------------ skia helpers
def paint(c, a=1.0, blur=0.0, stroke=None, cap=skia.Paint.kRound_Cap):
    p = skia.Paint(AntiAlias=True)
    p.setColor4f(skia.Color4f(c[0], c[1], c[2], a))
    if blur > 0: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke); p.setStrokeCap(cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    return p

def poly(pts, closed=True):
    p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    if closed: p.close()
    return p

def smooth(pts, closed=True, k=0.5):
    """Catmull-Rom spline through pts as cubic bezier path"""
    n = len(pts); p = skia.Path(); p.moveTo(*pts[0])
    rng_ = range(n) if closed else range(n - 1)
    for i in rng_:
        p0 = pts[(i - 1) % n] if (closed or i > 0) else pts[i]
        p1 = pts[i]; p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (closed or i + 2 < n) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) * k / 3, p1[1] + (p2[1] - p0[1]) * k / 3)
        c2 = (p2[0] - (p3[0] - p1[0]) * k / 3, p2[1] - (p3[1] - p1[1]) * k / 3)
        p.cubicTo(*c1, *c2, *p2)
    if closed: p.close()
    return p

def ell(cx, cy, rx, ry):
    p = skia.Path(); p.addOval(skia.Rect.MakeLTRB(cx - rx, cy - ry, cx + rx, cy + ry)); return p

def rrect(x0, y0, x1, y1, r):
    p = skia.Path(); p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(x0, y0, x1, y1), r, r)); return p

def limb(p0, p1, r0, r1):
    """tapered capsule from p0 (radius r0) to p1 (radius r1)"""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dy) or 1e-6
    ux, uy = dx / L, dy / L; nx, ny = -uy, ux
    pts = []
    a0 = math.atan2(ny, nx)
    for k in range(13):
        a = a0 + math.pi * k / 12
        pts.append((p0[0] + r0 * math.cos(a), p0[1] + r0 * math.sin(a)))
    for k in range(13):
        a = a0 + math.pi + math.pi * k / 12
        pts.append((p1[0] + r1 * math.cos(a), p1[1] + r1 * math.sin(a)))
    return poly(pts)

def fill(cv, path, c, a=1.0, blur=0.0):
    cv.drawPath(path, paint(c, a, blur))

def rot(p, ang, o=(0, 0)):
    c, s = math.cos(ang), math.sin(ang)
    x, y = p[0] - o[0], p[1] - o[1]
    return (o[0] + x * c - y * s, o[1] + x * s + y * c)

def polar(o, length, ang_from_down):
    """point at distance length from o, angle measured from straight down, positive toward +x"""
    return (o[0] + length * math.sin(ang_from_down), o[1] + length * math.cos(ang_from_down))

D2R = math.pi / 180

# ------------------------------------------------------------------ noise helpers
def vnoise1(x, seed=0):
    """smooth 1D value noise, x array"""
    x = np.asarray(x, float)
    i = np.floor(x).astype(int); f = x - i
    def h(n):
        n = (n * 374761393 + seed * 668265263) & 0xFFFFFFFF
        n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0
    a, b = h(i), h(i + 1); f = f * f * (3 - 2 * f)
    return a + (b - a) * f

def fbm1(x, seed=0, oct=4):
    v = 0; amp = 1; tot = 0
    for o in range(oct):
        v = v + amp * vnoise1(x * (2 ** o), seed + o * 17); tot += amp; amp *= 0.5
    return v / tot

def ridge_path(x0, x1, base, amp, scale, seed, bottom=4000, step=6, oct=4):
    xs = np.arange(x0, x1 + step, step)
    ys = base - amp * fbm1(xs / scale, seed, oct)
    pts = [(x0, bottom)] + list(zip(xs.tolist(), ys.tolist())) + [(x1, bottom)]
    return poly(pts)

# ------------------------------------------------------------------ sky, sun, moon, stars
def sky(cv, P, top=-2000, bot=4000, y0=0, y1=1300):
    p = skia.Paint()
    sh = skia.GradientShader.MakeLinear([skia.Point(0, y0), skia.Point(0, y1)],
                                        [skia.Color4f(*P["sky0"], 1).toColor(), skia.Color4f(*P["sky1"], 1).toColor()])
    p.setShader(sh)
    cv.drawRect(skia.Rect.MakeLTRB(-3000, top, 4000, bot), p)

@functools.lru_cache(maxsize=8)
def disc_image(kind, r):
    """large flat disc with soft watercolor blotches inside, returned as skia.Image (2r+pad square)"""
    pad = 8; S = int(2 * r + 2 * pad)
    surf = skia.Surface(S, S); cv = surf.getCanvas(); cv.clear(skia.Color4f(0, 0, 0, 0))
    c = (S / 2, S / 2)
    rs = np.random.RandomState(11 if kind == "sun" else 23)
    if kind == "sun":
        c0, c1 = SHOM["sun0"], SHOM["sun1"]
    else:
        c0, c1 = hx("#EDE6D2"), mix(hx("#EDE6D2"), hx("#C9C3B2"), 0.6)
    cv.save(); cv.clipPath(ell(c[0], c[1], r, r), doAntiAlias=True)
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, c[1] - r), skia.Point(0, c[1] + r)],
                [skia.Color4f(*c0, 1).toColor(), skia.Color4f(*c1, 1).toColor()]))
    cv.drawRect(skia.Rect.MakeWH(S, S), p)
    for k in range(16):  # watercolor blotches
        a = rs.uniform(0, 2 * math.pi); d = r * math.sqrt(rs.uniform(0, 0.85))
        bx, by = c[0] + d * math.cos(a), c[1] + d * math.sin(a)
        br = r * rs.uniform(0.12, 0.38)
        t = clamp01((by - (c[1] - r)) / (2 * r))
        base = mix(c0, c1, t)
        tone = mix(base, c1 if rs.rand() < 0.5 else c0, 0.55)
        if kind == "moon": tone = mix(base, hx("#BDB6A4"), rs.uniform(0.25, 0.6))
        pts = [(bx + br * (0.75 + 0.3 * rs.rand()) * math.cos(2 * math.pi * j / 9),
                by + br * (0.75 + 0.3 * rs.rand()) * math.sin(2 * math.pi * j / 9)) for j in range(9)]
        cv.drawPath(smooth(pts), paint(tone, rs.uniform(0.22, 0.45), blur=br * 0.35))
    # soft darker rim like a watercolor edge
    rim = skia.Paint(AntiAlias=True); rim.setStyle(skia.Paint.kStroke_Style); rim.setStrokeWidth(r * 0.08)
    rim.setColor4f(skia.Color4f(*(c1 if kind == "sun" else hx("#CFC8B6")), 0.35))
    rim.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, r * 0.03))
    cv.drawCircle(c[0], c[1], r - r * 0.02, rim)
    cv.restore()
    return surf.makeImageSnapshot()

def draw_disc(cv, kind, cx, cy, r, alpha=1.0, glow=0.0, glow_col=None):
    if glow > 0:
        gc = glow_col or (SHOM["sun0"] if kind == "sun" else hx("#EDE6D2"))
        cv.drawCircle(cx, cy, r * 1.25, paint(gc, 0.25 * glow * alpha, blur=r * 0.35))
    img = disc_image(kind, int(round(r)))
    p = skia.Paint(AntiAlias=True); p.setAlphaf(alpha)
    S = img.width()
    cv.drawImageRect(img, skia.Rect.MakeXYWH(cx - S / 2, cy - S / 2, S, S), skia.SamplingOptions(skia.FilterMode.kLinear), p)

STAR_RS = np.random.RandomState(5)
STARS = [(STAR_RS.uniform(-400, 1480), STAR_RS.uniform(-500, 1100), STAR_RS.uniform(1.4, 3.6), STAR_RS.uniform(0, 6.28),
          STAR_RS.uniform(1.2, 3.0)) for _ in range(140)]
def stars(cv, t, alpha, ymax=1000, col=None):
    if alpha <= 0.01: return
    col = col or hx("#EDE6D2")
    for x, y, r, ph, f in STARS:
        if y > ymax: continue
        tw = 0.65 + 0.35 * math.sin(t * f + ph)
        cv.drawCircle(x, y, r, paint(col, alpha * tw))

# ------------------------------------------------------------------ props
def bird(cv, x, y, s, flap, c, a=1.0, facing=-1):
    """small flapping bird silhouette; flap phase in radians"""
    w = math.sin(flap)
    tip = -7 * w
    pts = [(-11, tip), (-5, -2 - 2.2 * w), (0, 0), (5, -2 - 2.2 * w), (11, tip), (5, 1.2), (0, 2.2), (-5, 1.2)]
    pts = [(x + px * s * facing, y + py * s) for px, py in pts]
    cv.drawPath(smooth(pts, k=0.35), paint(c, a))
    cv.drawCircle(x + 1.6 * s * facing, y + 0.3 * s, 1.6 * s, paint(c, a))

def flock(cv, t, t0, t1, x0, x1, y, n, s, c, seed=3, a=1.0, speed_mul=1.0, facing=-1):
    rs = np.random.RandomState(seed)
    offs = [(rs.uniform(-120, 120), rs.uniform(-60, 60), rs.uniform(0, 6.28), rs.uniform(0.85, 1.15)) for _ in range(n)]
    u = (t - t0) / (t1 - t0)
    for dx, dy, ph, sc in offs:
        uu = u * sc
        X = lerp(x0, x1, uu) + dx; Y = y + dy + 12 * math.sin(uu * 6 + ph)
        bird(cv, X, Y, s * sc, t * 11 * speed_mul + ph, c, a, facing)

def poplar(cv, x, base, h, w, c, sway=0.0):
    pts = []
    n = 14
    for i in range(n + 1):
        f = i / n; yy = base - h * f
        ww = w * (math.sin(math.pi * min(1, f * 1.08)) ** 0.7) * (1 - 0.25 * f)
        pts.append((x + ww / 2 + sway * f * f, yy))
    for i in range(n, -1, -1):
        f = i / n; yy = base - h * f
        ww = w * (math.sin(math.pi * min(1, f * 1.08)) ** 0.7) * (1 - 0.25 * f)
        pts.append((x - ww / 2 + sway * f * f, yy))
    cv.drawPath(smooth(pts, k=0.6), paint(c))
    cv.drawRect(skia.Rect.MakeLTRB(x - w * 0.06, base - h * 0.08, x + w * 0.06, base + 4), paint(c))

def leafy_tree(cv, x, base, s, c, seed=1, sway=0.0, trunk_c=None):
    rs = np.random.RandomState(seed)
    tc = trunk_c or c
    tr = [(x - 9 * s, base), (x - 5 * s, base - 60 * s), (x - 14 * s, base - 110 * s), (x - 8 * s, base - 112 * s),
          (x + 1 * s, base - 72 * s), (x + 10 * s, base - 118 * s), (x + 16 * s, base - 114 * s), (x + 6 * s, base - 60 * s),
          (x + 10 * s, base)]
    cv.drawPath(poly(tr), paint(tc))
    cx, cy = x + sway * 0.5, base - 165 * s
    blobs = [(0, 0, 80), (-62, 18, 55), (62, 14, 58), (-30, -42, 55), (34, -44, 52), (0, 38, 60), (-80, 44, 36), (82, 42, 38)]
    for i, (bx, by, br) in enumerate(blobs):
        ph = rs.uniform(0, 6.28)
        cv.drawCircle(cx + bx * s + sway * (0.6 + 0.4 * math.sin(ph)), cy + by * s, br * s, paint(c))
    # small leaf bumps on the outline
    for k in range(26):
        a = rs.uniform(0, 2 * math.pi); d = rs.uniform(85, 110)
        cv.drawCircle(cx + d * s * math.cos(a) * 1.05 + sway, cy + d * s * math.sin(a) * 0.72 + 6 * s, rs.uniform(10, 18) * s, paint(c))

def flat_house(cv, x0, x1, base, h, c, parapet=True, win=None, win_col=None, win_a=0.0, chimney=None):
    cv.drawRect(skia.Rect.MakeLTRB(x0, base - h, x1, base + 2), paint(c))
    if parapet:
        cv.drawRect(skia.Rect.MakeLTRB(x0 - 6, base - h - 8, x1 + 6, base - h + 2), paint(c))
    if chimney:
        cx = chimney
        cv.drawRect(skia.Rect.MakeLTRB(cx - 7, base - h - 30, cx + 7, base - h), paint(c))
    if win and win_a > 0:
        for (wx0, wy0, wx1, wy1) in win:
            cv.drawRect(skia.Rect.MakeLTRB(wx0, wy0, wx1, wy1), paint(win_col, win_a))

def glow(cv, x, y, r, c, a):
    if a > 0.01: cv.drawCircle(x, y, r, paint(c, a, blur=r * 0.45))

def smoke(cv, x, y, t, c, a=0.5, s=1.0, drift=18.0, seed=0, rate=1.6, life=3.2):
    """flat soft smoke puffs rising from (x,y)"""
    rs = np.random.RandomState(seed)
    n = int(life * rate) + 2
    for k in range(n):
        age = ((t * rate + k + rs.rand() * 0.3) % n) / rate
        if age > life: continue
        f = age / life
        px = x + drift * age * s + 10 * s * math.sin(age * 1.7 + k)
        py = y - 75 * age * s
        r = (8 + 26 * f) * s
        al = a * (1 - f) ** 1.3 * min(1, f * 6)
        cv.drawCircle(px, py, r, paint(c, al, blur=r * 0.25))

# ------------------------------------------------------------------ post: paper grain + vignette
@functools.lru_cache(maxsize=1)
def post_maps():
    rs = np.random.RandomState(42)
    from scipy.ndimage import gaussian_filter
    fine = rs.randn(H, W).astype(np.float32)
    fine = gaussian_filter(fine, 0.7)
    fine /= fine.std()
    mott = gaussian_filter(rs.randn(H // 4, W // 4).astype(np.float32), 6)
    mott = np.kron(mott, np.ones((4, 4), np.float32))[:H, :W]
    mott = gaussian_filter(mott, 3); mott /= mott.std()
    fib = np.zeros((H, W), np.float32)   # faint paper fibres
    for _ in range(900):
        x, y = rs.randint(0, W), rs.randint(0, H); L = rs.randint(10, 40); a = rs.uniform(0, math.pi)
        xs = (x + np.arange(L) * math.cos(a)).astype(int); ys = (y + np.arange(L) * math.sin(a)).astype(int)
        m = (xs >= 0) & (xs < W) & (ys >= 0) & (ys < H)
        fib[ys[m], xs[m]] += rs.choice([-1, 1])
    fib = gaussian_filter(fib, 0.6); fib /= (np.abs(fib).max() + 1e-6)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.48) / (H * 0.6)) ** 2)
    vig = np.clip(r - 0.55, 0, None) ** 1.6
    return fine, mott, fib, vig.astype(np.float32)

def post(arr, grain=1.0, vig=1.0, sat=1.0):
    """arr float32 HxWx3 in 0..1 ; grain/vig multipliers (1 = base look)"""
    fine, mott, fib, vmap = post_maps()
    if sat != 1.0:
        g = (arr * np.array([0.299, 0.587, 0.114], np.float32)).sum(2, keepdims=True)
        arr = g + (arr - g) * sat
    tex = 0.026 * fine + 0.018 * mott + 0.03 * fib
    arr = arr * (1 + grain * tex[..., None])
    arr = arr * (1 - (0.55 * vig) * vmap[..., None])
    return arr
