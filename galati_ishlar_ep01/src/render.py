# Frame renderer: the Google Flow frames animated in code (camera moves, local
# warps, light effects), hook / CTA text, one-line karaoke subtitles -> ffmpeg.
import os, sys, json, math, subprocess, time
from functools import lru_cache
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import *
import cues as C

SK = 1.35                                  # upscaled source = output * SK
SW, SH = int(W * SK), int(H * SK)          # 1458 x 2592
OW, OH = 756, 1344                         # original Flow frame size
LR = 4                                     # low-res factor for light masks
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf"
FONT_BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"

def rgbf(c): return np.array(c, np.float32) / 255.0

# ---------------------------------------------------------------------------
# helpers
def noise1(t, seed=0.0, f=1.0):
    """smooth pseudo-random signal in [-1, 1]"""
    return (math.sin(2 * math.pi * (0.71 * f * t + seed)) * 0.5 + math.sin(2 * math.pi * (1.37 * f * t + 2.1 * seed + 0.3)) * 0.3
            + math.sin(2 * math.pi * (2.93 * f * t + 3.7 * seed + 1.1)) * 0.2)

def hash01(i, seed=0):
    x = math.sin(i * 12.9898 + seed * 78.233) * 43758.5453
    return x - math.floor(x)

def flick(t, rate=14.0, seed=0, depth=0.5, p=0.15):
    """random flicker: mostly 1, occasional dips"""
    i = int(t * rate)
    return 1.0 - depth * (hash01(i, seed) < p) * hash01(i, seed + 5)

def cam_matrix(z, cx, cy, r=0.0, dx=0.0, dy=0.0):
    """affine output(u,v) -> upscaled-source pixel; cx, cy normalized source center"""
    s = SK / z
    # clamp the center so the view stays inside the frame
    m = 0.5 / z * (1 + abs(r) * 1.9)
    cx = min(max(cx, m), 1 - m); cy = min(max(cy, m * 0.98), 1 - m * 0.98)
    c, sn = math.cos(r), math.sin(r)
    u0, v0 = W / 2 + dx, H / 2 + dy
    a, b, d, e = s * c, -s * sn, s * sn, s * c
    return np.array([[a, b, cx * SW - a * u0 - b * v0], [d, e, cy * SH - d * u0 - e * v0]], np.float64)

def to_screen(M, xn, yn):
    Mi = cv2.invertAffineTransform(M)
    x, y = xn * SW, yn * SH
    return Mi[0, 0] * x + Mi[0, 1] * y + Mi[0, 2], Mi[1, 0] * x + Mi[1, 1] * y + Mi[1, 2]

_UV = None
def uv():
    global _UV
    if _UV is None:
        u, v = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
        _UV = (u, v)
    return _UV

def full_map(M):
    u, v = uv()
    X = (M[0, 0] * u + M[0, 1] * v + M[0, 2]).astype(np.float32)
    Y = (M[1, 0] * u + M[1, 1] * v + M[1, 2]).astype(np.float32)
    return X, Y

_LG = None
def lowgrid():
    global _LG
    if _LG is None:
        u, v = np.meshgrid(np.arange(W // 8, dtype=np.float32) * 8 + 4, np.arange(H // 8, dtype=np.float32) * 8 + 4)
        _LG = (u, v)
    return _LG

def glow_map(points):
    """sum of gaussian blobs in screen space: points [(x, y, sigma_px, amp)] -> (H, W) float32"""
    u, v = lowgrid()
    g = np.zeros_like(u)
    for x, y, s, a in points:
        g += a * np.exp(-((u - x) ** 2 + (v - y) ** 2) / (2 * s * s))
    return cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)

def add_glow(img, points, color, k=1.0):
    g = glow_map(points)
    img += g[..., None] * rgbf(color)[None, None, :] * k

def warp_mask(mask_lr, M):
    """low-res source mask (SH/LR, SW/LR) -> screen"""
    return cv2.warpAffine(mask_lr, M / LR, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_REPLICATE)

def pend_warp(X, Y, anchor, tip, radius, theta):
    """rotate a hanging cord+bulb around its anchor by theta (soft capsule mask), in source px"""
    ax, ay = anchor[0] * SW, anchor[1] * SH
    tx, ty = tip[0] * SW, tip[1] * SH
    vx, vy = tx - ax, ty - ay; L2 = vx * vx + vy * vy
    pr = np.clip(((X - ax) * vx + (Y - ay) * vy) / L2, 0, 1.15)
    dx, dy = X - (ax + pr * vx), Y - (ay + pr * vy)
    dist = np.sqrt(dx * dx + dy * dy)
    rr = radius * SW
    w = np.clip(1.5 - dist / rr, 0, 1) * np.clip(pr * 3.0, 0, 1)
    w = w * w * (3 - 2 * w)
    ang = -theta * w
    c, s = np.cos(ang), np.sin(ang)
    rx, ry = X - ax, Y - ay
    return (ax + c * rx - s * ry).astype(np.float32), (ay + s * rx + c * ry).astype(np.float32)

def blob_shift(X, Y, cx, cy, rx, ry, ddx, ddy, rot=0.0, pivot=None):
    """move/rotate a soft elliptical region of the source (inverse warp)"""
    px, py = cx * SW, cy * SH
    w = np.clip(1.0 - (((X - px) / (rx * SW)) ** 2 + ((Y - py) / (ry * SH)) ** 2), 0, 1)
    w = w * w * (3 - 2 * w)
    X2 = X - ddx * SW * w; Y2 = Y - ddy * SH * w
    if rot:
        qx, qy = (pivot[0] * SW, pivot[1] * SH) if pivot else (px, py)
        a = -rot * w; c, s = np.cos(a), np.sin(a)
        rx_, ry_ = X2 - qx, Y2 - qy
        X2 = qx + c * rx_ - s * ry_; Y2 = qy + s * rx_ + c * ry_
    return X2.astype(np.float32), Y2.astype(np.float32)

def rect_soft(X, Y, x0, y0, x1, y1, f):
    wx = np.clip(np.minimum(X / SW - x0, x1 - X / SW) / f, 0, 1)
    wy = np.clip(np.minimum(Y / SH - y0, y1 - Y / SH) / f, 0, 1)
    w = wx * wy
    return w * w * (3 - 2 * w)

# ---------------------------------------------------------------------------
# source images and prepared data
def load_src(key):
    im = cv2.imread(os.path.join(FRAMES_DIR, key + ".jpg"), cv2.IMREAD_COLOR)[:, :, ::-1]
    return np.ascontiguousarray(im)

@lru_cache(maxsize=None)
def SRC(key):
    return cv2.resize(load_src(key), (SW, SH), interpolation=cv2.INTER_LANCZOS4)

def up(img_o):
    return cv2.resize(img_o, (SW, SH), interpolation=cv2.INTER_LANCZOS4 if img_o.ndim == 3 else cv2.INTER_LINEAR)

def lr(img_o):
    return cv2.resize(img_o, (SW // LR, SH // LR), interpolation=cv2.INTER_AREA)

@lru_cache(maxsize=None)
def PREP(key):
    o = load_src(key).astype(np.float32) / 255
    d = {}
    if key == "F02":                          # one lit window that flickers
        r, g, b = o[..., 0], o[..., 1], o[..., 2]
        warm = ((r > 0.55) & (r - b > 0.2)).astype(np.float32)
        yy, xx = np.mgrid[0:OH, 0:OW]
        near = (((xx / OW - 0.545) / 0.03) ** 2 + ((yy / OH - 0.455) / 0.02) ** 2) < 1
        m = cv2.dilate(warm * near, np.ones((5, 5), np.uint8))
        d["win"] = lr(cv2.GaussianBlur(m, (0, 0), 2.5))
    if key == "F03":                          # red-lit surfaces
        r, g, b = o[..., 0], o[..., 1], o[..., 2]
        red = np.clip((r - np.maximum(g, b) - 0.08) / 0.25, 0, 1)
        d["red"] = lr(cv2.GaussianBlur(red, (0, 0), 3))
    if key == "F05":                          # creature layer + clean plate
        lum = o.max(2)
        yy, xx = np.mgrid[0:OH, 0:OW]
        reg = (xx > 0.26 * OW) & (xx < 0.74 * OW) & (yy > 0.05 * OH) & (yy < 0.565 * OH)
        r, g = o[..., 0], o[..., 1]
        m = (((lum < 0.30) | ((r > 0.35) & (r > 1.8 * g))) & reg).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        m = cv2.dilate(m, np.ones((5, 5), np.uint8))
        im8 = (o * 255).astype(np.uint8)
        plate = cv2.inpaint(im8, m, 9, cv2.INPAINT_TELEA)
        plate = cv2.GaussianBlur(plate, (0, 0), 1.2)
        d["plate"] = up(plate)
        d["cmask"] = up(cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.5))
    if key == "F12":                          # street-lamp cone
        yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
        lx, ly = 0.63 * OW, 0.115 * OH
        t = np.clip((yy - ly) / (0.55 * OH - ly), 0, 1)
        half = 0.04 * OW + t * 0.34 * OW
        cone = np.clip(1 - np.abs(xx - lx) / half, 0, 1) * (yy > ly - 20) * (1 - t) ** 0.6
        head = np.exp(-(((xx - lx) / (0.10 * OW)) ** 2 + ((yy - ly) / (0.05 * OH)) ** 2))
        d["cone"] = lr(np.clip(cv2.GaussianBlur(cone, (0, 0), 12) + head, 0, 1))
    if key == "F13":                          # bicycle headlight beam
        lum = o.mean(2)
        yy, xx = np.mgrid[0:OH, 0:OW]
        reg = (xx > 0.40 * OW) & (yy > 0.58 * OH) & (yy < 0.86 * OH)
        base = cv2.GaussianBlur(lum, (0, 0), 40)
        beam = np.clip((cv2.GaussianBlur(lum, (0, 0), 6) - 0.16) / 0.25, 0, 1) * reg
        d["beam"] = lr(cv2.GaussianBlur(beam.astype(np.float32), (0, 0), 8))
    if key == "F18":                          # red eyes masked out for the fade-in
        r, g, b = o[..., 0], o[..., 1], o[..., 2]
        yy, xx = np.mgrid[0:OH, 0:OW]
        near = np.zeros((OH, OW), bool)
        for ex, ey in ((0.695, 0.321), (0.755, 0.321)):
            near |= ((xx / OW - ex) ** 2 + (yy / OH - ey) ** 2 * (OH / OW) ** 2) < 0.03 ** 2
        m = (((r > 0.25) & (r > 1.6 * g)) & near).astype(np.uint8)
        m = cv2.dilate(m, np.ones((7, 7), np.uint8))
        im8 = (o * 255).astype(np.uint8)
        d["plate"] = up(cv2.inpaint(im8, m, 6, cv2.INPAINT_TELEA))
        d["emask"] = up(cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.5))
    if key in ("F20", "F21"):
        d["wheel"] = Wheel(key, o)
    return d

# ---------------------------------------------------------------------------
# spinning wheel: rim-preserving polar rotation around the hub, fork stays in front
class Wheel:
    PARAMS = {
        # hub (orig px), ellipse through the spoke ends ((cx,cy),(full w,h),angle), static polygons
        "F21": dict(hub=(378, 712), ell=((385.4, 714.4), (535.4, 834.7), 0.756),
                    static=[[(148, 228), (186, 400), (232, 522), (276, 612), (312, 672), (332, 700), (352, 700), (334, 642),
                             (304, 580), (270, 480), (246, 400), (226, 300), (220, 228)],
                            [(20, 676), (330, 700), (334, 736), (20, 708)],
                            [(205, 236), (300, 236), (300, 372), (205, 372)]]),
        "F20": dict(hub=(541, 884), ell=((540.9, 889.2), (113.4, 170.1), 112.0),
                    static=[[(440, 830), (470, 842), (500, 856), (525, 870), (548, 876), (550, 906), (530, 906), (505, 894),
                             (480, 881), (455, 869), (438, 862)],
                            [(450, 912), (536, 890), (538, 902), (454, 926)],
                            [(426, 836), (462, 846), (472, 900), (470, 945), (442, 955), (426, 905)]]),
    }

    def __init__(self, key, o):
        p = self.PARAMS[key]
        f = SW / OW
        (ecx, ecy), (ew, eh), ang = p["ell"]
        self.c = np.array([ecx, ecy]) * f
        self.a, self.b = ew / 2 * f, eh / 2 * f
        self.th = math.radians(ang)
        self.h = np.array(p["hub"], np.float64) * f
        R = max(self.a, self.b) * 1.08
        x0, y0 = int(max(0, self.c[0] - R)), int(max(0, self.c[1] - R))
        x1, y1 = int(min(SW, self.c[0] + R)), int(min(SH, self.c[1] + R))
        self.box = (x0, y0, x1, y1)
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
        dx, dy = xx - self.h[0], yy - self.h[1]
        self.alpha = np.arctan2(dy, dx)
        self.rad = np.sqrt(dx * dx + dy * dy)
        self.rho = self.rad / self.R(self.alpha)
        w = np.clip((1.035 - self.rho) / 0.06, 0, 1)
        self.w = (w * w * (3 - 2 * w)).astype(np.float32)
        st = np.zeros((OH, OW), np.uint8)
        for poly in p["static"]:
            cv2.fillPoly(st, [np.array(poly, np.int32)], 1)
        st = cv2.GaussianBlur(st.astype(np.float32), (0, 0), 1.2)
        self.static = up(st)[y0:y1, x0:x1]
        # clean plate: static parts replaced from the same radius, 90 degrees round the wheel
        src = SRC(key)[y0:y1, x0:x1].astype(np.float32)
        mx_, my_ = self.sample_map(math.pi / 2)
        alt = cv2.remap(src, mx_, my_, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        sm = np.clip(cv2.dilate(self.static, np.ones((9, 9), np.uint8)) * 1.5, 0, 1)[..., None]
        self.clean = (src * (1 - sm) + alt * sm).astype(np.float32)

    def R(self, alpha):
        ca, sa = np.cos(alpha), np.sin(alpha)
        c, s = math.cos(-self.th), math.sin(-self.th)
        qx = c * (self.h[0] - self.c[0]) - s * (self.h[1] - self.c[1])
        qy = s * (self.h[0] - self.c[0]) + c * (self.h[1] - self.c[1])
        dx = c * ca - s * sa; dy = s * ca + c * sa
        A = (dx / self.a) ** 2 + (dy / self.b) ** 2
        B = 2 * (qx * dx / self.a ** 2 + qy * dy / self.b ** 2)
        Cc = (qx / self.a) ** 2 + (qy / self.b) ** 2 - 1
        return (-B + np.sqrt(B * B - 4 * A * Cc)) / (2 * A)

    def sample_map(self, phi):
        a2 = self.alpha - phi
        r2 = self.rho * self.R(a2)
        x0, y0 = self.box[0], self.box[1]
        return ((self.h[0] + r2 * np.cos(a2) - x0).astype(np.float32),
                (self.h[1] + r2 * np.sin(a2) - y0).astype(np.float32))

    def apply(self, src_full, turns, speed):
        """src_full: upscaled source (uint8) -> copy with the wheel rotated by `turns` revolutions"""
        x0, y0, x1, y1 = self.box
        phi = 2 * math.pi * turns
        blur = 2 * math.pi * speed / (2 * FPS)          # half-frame shutter
        k = int(min(10, max(1, math.ceil(blur / 0.025))))
        acc = None
        for i in range(k):
            ph = phi - blur * (i / max(1, k - 1) if k > 1 else 0)
            mx_, my_ = self.sample_map(ph)
            s = cv2.remap(self.clean, mx_, my_, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            acc = s if acc is None else acc + s
        rot = acc / k
        orig = src_full[y0:y1, x0:x1].astype(np.float32)
        w = self.w[..., None] * (1 - self.static[..., None])
        out = src_full.copy()
        out[y0:y1, x0:x1] = np.clip(orig * (1 - w) + rot * w, 0, 255).astype(np.uint8)
        return out

# ---------------------------------------------------------------------------
# grades / overlays
_VIG = None
def vignette(strength):
    global _VIG
    if _VIG is None:
        u, v = uv()
        r = np.sqrt(((u - W / 2) / (W / 2)) ** 2 * 0.8 + ((v - H / 2) / (H / 2)) ** 2)
        _VIG = np.clip(r / 1.25, 0, 1) ** 2.2
    return 1 - strength * _VIG

_GRAIN = None
def grain(i, amp):
    global _GRAIN
    if _GRAIN is None:
        rs = np.random.default_rng(7)
        g = rs.standard_normal((H // 2 + 64, W // 2 + 64)).astype(np.float32)
        _GRAIN = cv2.GaussianBlur(g, (0, 0), 0.6)
    ox, oy = int(hash01(i, 1) * 64), int(hash01(i, 2) * 64)
    g = _GRAIN[oy:oy + H // 2, ox:ox + W // 2]
    return cv2.resize(g, (W, H), interpolation=cv2.INTER_NEAREST)[..., None] * amp

_FOG = None
def fog_tex():
    global _FOG
    if _FOG is None:
        rs = np.random.default_rng(3)
        acc = np.zeros((H // 4, W // 2), np.float32)
        for sc, a in ((64, 1.0), (24, 0.5), (10, 0.25)):
            n = rs.random(((H // 4) // sc + 3, (W // 2) // sc + 3)).astype(np.float32)
            acc += a * cv2.resize(n, (W // 2, H // 4), interpolation=cv2.INTER_CUBIC)
        acc = (acc - acc.min()) / (acc.max() - acc.min())
        _FOG = np.concatenate([acc, acc[:, ::-1]], 1)            # tileable horizontally
    return _FOG

def fog(img, t, alpha, y0=0.35, y1=1.0, speed=40.0, color=(0.55, 0.62, 0.70)):
    tex = fog_tex()
    off = int(t * speed) % tex.shape[1]
    band = np.roll(tex, -off, axis=1)[:, :W // 2]
    band = cv2.resize(band, (W, H), interpolation=cv2.INTER_LINEAR)
    v = uv()[1] / H
    ramp = np.clip((v - y0) / 0.15, 0, 1) * np.clip((y1 - v) / 0.1, 0, 1)
    a = (alpha * band * ramp)[..., None]
    img[:] = img * (1 - a) + np.array(color, np.float32) * a

def grade(img, kind):
    if kind == "evening":
        img *= np.array([0.86, 0.79, 0.72], np.float32)
    elif kind == "night":
        lum = img @ np.array([0.3, 0.59, 0.11], np.float32)
        img[:] = img * 0.6 + lum[..., None] * 0.4
        img *= np.array([0.30, 0.36, 0.50], np.float32)
        img += rgbf(SHADOW1) * 0.12
    return img

# ---------------------------------------------------------------------------
# shots
def lerp(a, b, x): return a + (b - a) * x

def shake(t, amp, rot_deg=0.0, f=1.0, seed=0.0):
    return (amp * noise1(t, seed, f), amp * noise1(t, seed + 3.3, f * 1.1), math.radians(rot_deg) * noise1(t, seed + 7.7, f * 0.9))

def impulse(t, t0, amp, dur=0.3, f=14.0):
    if t < t0: return 0.0, 0.0
    x = (t - t0) / dur
    if x > 1.5: return 0.0, 0.0
    e = math.exp(-3.5 * x)
    return amp * e * math.sin(2 * math.pi * f * (t - t0)), amp * 0.7 * e * math.cos(2 * math.pi * f * 1.3 * (t - t0))

class Shot:
    key = None
    grade = None
    grain_amp = 0.022
    vig = 0.45
    def __init__(self, t0, t1): self.t0, self.t1 = t0, t1
    def u(self, t): return C.clamp01((t - self.t0) / (self.t1 - self.t0))
    def cam(self, t): return dict(z=1.06, cx=0.5, cy=0.5)
    def source(self, t): return SRC(self.key)
    warp = None
    def light(self, t, img, M): pass

    def render(self, t, i):
        cp = self.cam(t)
        M = cam_matrix(cp.get("z", 1.06), cp.get("cx", 0.5), cp.get("cy", 0.5), cp.get("r", 0.0), cp.get("dx", 0.0), cp.get("dy", 0.0))
        src = self.source(t)
        if self.warp is not None:
            X, Y = full_map(M)
            X, Y = self.warp(t, X, Y)
            out = cv2.remap(src, X, Y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        else:
            out = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
        img = out.astype(np.float32) * (1 / 255)
        self.M = M
        self.light(t, img, M)
        if self.grade: grade(img, self.grade)
        img *= vignette(self.vig)[..., None]
        img += grain(i, self.grain_amp)
        return img

# --- 0  hook: red alarm corridor, scientist running to the lift ----------------
class S_F01(Shot):
    key = "F01"
    def cam(self, t):
        u = self.u(t)
        k = 0.75 * u + 0.25 * u * u
        dx, dy, r = shake(t, 6, 0.35, 1.8, 0.2)
        bob = 3 * math.sin(2 * math.pi * 3.6 * t)
        return dict(z=1.08 + 0.30 * k, cx=lerp(0.56, 0.655, k), cy=lerp(0.53, 0.575, k), r=r, dx=dx, dy=dy + bob)
    def warp(self, t, X, Y):
        u = self.u(t)
        run = 0.5 + 0.5 * math.sin(2 * math.pi * 3.6 * t)
        return blob_shift(X, Y, 0.615, 0.64, 0.085, 0.075, 0.016 * u, -0.022 * u - 0.003 * run)
    def light(self, t, img, M):
        p = C.alarm(t)
        img *= 0.58 + 0.42 * p
        x1, y1 = to_screen(M, 0.463, 0.152); x2, y2 = to_screen(M, 0.684, 0.468)
        add_glow(img, [(x1, y1, 150, 0.55 * p), (x1, y1, 45, 0.9 * p), (x2, y2, 70, 0.45 * p)], ALARM)

# --- 1  base exterior: push-in, fog, one window flickers --------------------
class S_F02(Shot):
    key = "F02"
    def cam(self, t):
        k = C.smooth(self.u(t))
        dx, dy, r = shake(t, 1.5, 0.05, 0.5, 1.0)
        return dict(z=lerp(1.06, 1.17, k), cx=lerp(0.55, 0.60, k), cy=lerp(0.50, 0.47, k), dx=dx, dy=dy)
    def light(self, t, img, M):
        g = flick(t, 13, 4, 0.9, 0.22)
        m = warp_mask(PREP("F02")["win"], M)
        img *= (1 - m * (1 - g) * 0.85)[..., None]
        fog(img, t, 0.20, 0.45, 1.0, 55)
        fog(img, t * 1.7 + 3, 0.10, 0.30, 0.9, 35)

# --- 1  lift interior: handheld, red light flashing through the doors -------
class S_F03(Shot):
    key = "F03"
    def cam(self, t):
        k = C.smooth(self.u(t))
        dx, dy, r = shake(t, 8, 0.5, 1.6, 2.0)
        return dict(z=lerp(1.10, 1.16, k), cx=lerp(0.50, 0.48, k), cy=lerp(0.50, 0.47, k), r=r, dx=dx, dy=dy)
    def light(self, t, img, M):
        f = (0.5 + 0.5 * math.sin(2 * math.pi * 1.6 * (t - 5.5) + 1.2)) ** 2
        m = warp_mask(PREP("F03")["red"], M)
        img *= (1 + m * (0.75 * f - 0.4))[..., None]
        x, y = to_screen(M, 0.12, 0.45)
        add_glow(img, [(x, y, 380, 0.22 * f)], ALARM)

# --- 2  lift doors close on the scientist -------------------------------------
class S_F04(Shot):
    key = "F04"
    def cam(self, t):
        k = C.smooth(self.u(t))
        jx, jy = impulse(t, C.DOOR_SHUT, 12, 0.3)
        dx, dy, r = shake(t, 1.5, 0.05, 0.6, 3.0)
        return dict(z=lerp(1.06, 1.13, k), cx=0.5, cy=lerp(0.50, 0.49, k), dx=dx + jx, dy=dy + jy)
    def q(self, t):
        x = C.clamp01((t - C.DOOR_CLOSE_T0) / (C.DOOR_SHUT - C.DOOR_CLOSE_T0))
        return x * x * (1.6 - 0.6 * x)          # accelerates, ends hard
    def warp(self, t, X, Y):
        q = self.q(t)
        f = SW / OW
        L0, LG, RG, R0, MID = 160 * f, 347 * f, 410 * f, 597 * f, 378.5 * f
        cl = LG + (MID - LG) * q; cr = RG - (RG - MID) * q
        band = (Y > 298 * f) & (Y < 1126 * f)
        Xn = X.copy()
        left = band & (X >= L0) & (X < cl)
        Xn[left] = L0 + (X[left] - L0) * (LG - L0) / (cl - L0)
        right = band & (X > cr) & (X <= R0)
        Xn[right] = R0 - (R0 - X[right]) * (R0 - RG) / (R0 - cr)
        if q >= 0.999:
            gap = band & (X >= cl) & (X <= cr)
            Xn[gap] = LG
        return Xn, Y
    def light(self, t, img, M):
        img *= 1 - 0.06 * self.q(t)

# --- 2  something black drops from the ceiling hatch ---------------------------
class S_F05(Shot):
    key = "F05"
    def cam(self, t):
        k = C.smooth(self.u(t))
        jx, jy = impulse(t, C.CREATURE_LAND, 20, 0.35, 11)
        dx, dy, r = shake(t, 3, 0.2, 1.2, 4.0)
        return dict(z=lerp(1.08, 1.14, k), cx=0.5, cy=lerp(0.47, 0.45, k), r=r, dx=dx + jx, dy=dy + jy)
    def offset(self, t):
        x = C.clamp01((t - C.CREATURE_DROP) / (C.CREATURE_LAND - C.CREATURE_DROP))
        return -0.20 * SH * (1 - x) ** 1.3
    def source(self, t):
        d = PREP("F05")
        o = self.offset(t)
        if o == 0:
            return SRC("F05")
        src = SRC("F05").astype(np.float32); plate = d["plate"].astype(np.float32)
        m = d["cmask"]
        out = plate.copy()
        k = 6; v = 0.20 * SH * 1.3 / (C.CREATURE_LAND - C.CREATURE_DROP) / (2 * FPS) * (1 - C.clamp01((t - C.CREATURE_DROP) / 0.1)) ** 0.3
        acc = np.zeros_like(out); macc = np.zeros(m.shape, np.float32)
        for j in range(k):
            oo = int(round(o - v * j / k))
            Ms = np.float32([[1, 0, 0], [0, 1, oo]])
            acc += cv2.warpAffine(src * m[..., None], Ms, (SW, SH))
            macc += cv2.warpAffine(m, Ms, (SW, SH))
        acc /= k; macc /= k
        clip = (np.arange(SH) > 0.068 * SH).astype(np.float32)[:, None]
        macc *= clip; acc *= clip[..., None]
        out = out * (1 - macc[..., None]) + acc
        return np.clip(out, 0, 255).astype(np.uint8)
    def light(self, t, img, M):
        o = self.offset(t) / SH
        g = 0.65 if C.CREATURE_DROP <= t < C.CREATURE_LAND + 0.06 else 1.0
        img *= g
        pul = 0.75 + 0.25 * math.sin(2 * math.pi * 1.3 * t)
        pts = []
        for ex in (0.457, 0.52):
            x, y = to_screen(M, ex, 0.318 + o)
            if y > to_screen(M, 0.5, 0.068)[1]:
                pts += [(x, y, 26, 0.55 * pul), (x, y, 8, 1.0 * pul)]
        if pts: add_glow(img, pts, EYES)
        x, y = to_screen(M, 0.86, 0.32)
        add_glow(img, [(x, y, 90, 0.10 * flick(t, 9, 2, 0.6, 0.2))], LAMP)

# --- 2  empty lift, lamp flickers then holds ------------------------------------
class S_F06(Shot):
    key = "F06"
    def cam(self, t):
        k = C.smooth(self.u(t))
        dx, dy, r = shake(t, 1.5, 0.05, 0.5, 5.0)
        return dict(z=lerp(1.05, 1.11, k), cx=0.52, cy=lerp(0.50, 0.46, k), dx=dx, dy=dy)
    def light(self, t, img, M):
        g = C.f06_lamp(t)
        img *= 0.22 + 0.78 * g
        x, y = to_screen(M, 0.60, 0.18)
        add_glow(img, [(x, y, 240, 0.22 * g), (x, y, 60, 0.35 * g)], (205, 235, 225))

# --- 3  basement: four friends at the game, the bulb sways --------------------
def swing_light(img, M, bulb, theta, k=0.22, sig=(0.42, 0.55), floor_y=0.62):
    bx, by = to_screen(M, bulb[0] + 0.55 * math.sin(theta), floor_y)
    u, v = lowgrid()
    g = np.exp(-(((u - bx) / (sig[0] * W)) ** 2 + ((v - by) / (sig[1] * H)) ** 2))
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
    img *= (1 - k + 2 * k * g)[..., None]

class S_F07(Shot):
    key = "F07"
    def theta(self, t): return math.radians(6.5) * math.sin(2 * math.pi * (t - self.t0) / 1.7 + 0.6)
    def cam(self, t):
        k = C.smooth(self.u(t))
        dx, dy, r = shake(t, 1.5, 0.05, 0.5, 6.0)
        return dict(z=1.22, cx=lerp(0.41, 0.59, k), cy=0.55, dx=dx, dy=dy)
    def warp(self, t, X, Y):
        return pend_warp(X, Y, (0.522, 0.088), (0.505, 0.215), 0.05, self.theta(t))
    def light(self, t, img, M):
        th = self.theta(t)
        swing_light(img, M, (0.505, 0.21), th, 0.18)
        x, y = to_screen(M, 0.505 + 0.127 * math.sin(th) * 0.9, 0.205)
        add_glow(img, [(x, y, 130, 0.22), (x, y, 30, 0.35)], LAMP)

# --- 3  Doniyor shows the Dev card ------------------------------------------------
class S_F08(Shot):
    key = "F08"; grade = "evening"
    def cam(self, t):
        k = C.smooth(self.u(t))
        dx, dy, r = shake(t, 1.5, 0.05, 0.6, 7.0)
        return dict(z=lerp(1.06, 1.22, k), cx=lerp(0.50, 0.47, k), cy=lerp(0.50, 0.46, k), dx=dx, dy=dy)
    def warp(self, t, X, Y):
        x = t - self.t0
        rot = math.radians(2.6) * math.sin(2 * math.pi * 3.1 * x) * (0.6 + 0.4 * math.sin(2 * math.pi * 0.7 * x))
        w = rect_soft(X, Y, 0.215, 0.45, 0.585, 0.815, 0.035)
        px, py = 0.355 * SW, 0.505 * SH
        a = -rot * w
        c, s = np.cos(a), np.sin(a)
        dyy = 0.004 * SH * math.sin(2 * math.pi * 3.1 * x + 1.0) * w
        rx, ry = X - px, Y - py - dyy
        return (px + c * rx - s * ry).astype(np.float32), (py + s * rx + c * ry).astype(np.float32)
    def light(self, t, img, M):
        th = math.radians(4) * math.sin(2 * math.pi * (t - 14.4 - D1) / 1.7 + 0.6)
        swing_light(img, M, (0.5, 0.2), th, 0.10, (0.5, 0.6), 0.55)

# --- 4  Sardor: "Qochaman!" ------------------------------------------------------
class S_F09(Shot):
    key = "F09"; grade = "evening"
    def cam(self, t):
        k = C.ease_out(self.u(t) * 1.15)
        dx, dy, r = shake(t, 1.2, 0.05, 0.6, 8.0)
        return dict(z=lerp(1.04, 1.30, k), cx=lerp(0.50, 0.45, k), cy=lerp(0.48, 0.40, k), dx=dx, dy=dy)

# --- 4  everyone laughs ---------------------------------------------------------------
class S_F10(Shot):
    key = "F10"; grade = "evening"
    BOYS = [(0.18, 0.50, 0.16, 0.20, 0.0, 4.3), (0.39, 0.53, 0.11, 0.15, 1.7, 4.9),
            (0.61, 0.48, 0.13, 0.19, 0.6, 3.9), (0.83, 0.50, 0.14, 0.19, 2.4, 4.6)]
    def cam(self, t):
        k = C.smooth(self.u(t))
        dx, dy, r = shake(t, 1.5, 0.08, 0.7, 9.0)
        return dict(z=lerp(1.06, 1.12, k), cx=0.5, cy=lerp(0.52, 0.50, k), dx=dx, dy=dy + 2 * math.sin(2 * math.pi * 2.2 * t))
    def warp(self, t, X, Y):
        x = t - self.t0
        for cx, cy, rx, ry, ph, f in self.BOYS:
            b = abs(math.sin(2 * math.pi * f * x / 2 + ph)) * 0.007 * min(1, x / 0.25)
            X, Y = blob_shift(X, Y, cx, cy, rx, ry, 0.0, -b)
        return X, Y
    def light(self, t, img, M):
        th = math.radians(5) * math.sin(2 * math.pi * (t - self.t0) / 1.9 + 1.0)
        swing_light(img, M, (0.5, 0.15), th, 0.12, (0.5, 0.6), 0.55)

# --- 5  night street: tracking with the bike, walls slide past ---------------
class S_F11(Shot):
    key = "F11"
    VP = (0.62, 0.585)
    def cam(self, t):
        dx, dy, r = shake(t, 2.5, 0.12, 1.1, 10.0)
        return dict(z=1.20, cx=lerp(0.50, 0.53, self.u(t)), cy=0.57, r=r, dx=dx, dy=dy + 1.5 * math.sin(2 * math.pi * 3.0 * t))
    def warp(self, t, X, Y):
        u = self.u(t)
        vx, vy = self.VP[0] * SW, self.VP[1] * SH
        dxs, dys = (X - vx) / SW, (Y - vy) / SH
        r = np.sqrt(dxs * dxs + (dys * 1.0) ** 2)
        s = 1 + (0.11 * u - 0.03) * np.clip(r / 0.6, 0, 1.3) ** 1.4
        # Sardor and the bike stay with the camera
        bx, by = 0.37 * SW, 0.71 * SH
        wb = np.clip(1 - (((X - bx) / (0.16 * SW)) ** 2 + ((Y - by) / (0.15 * SH)) ** 2), 0, 1)
        wb = wb * wb * (3 - 2 * wb)
        s = s * (1 - wb) + wb
        bob = 0.0025 * SH * math.sin(2 * math.pi * 3.0 * t) * wb
        return (vx + (X - vx) * s).astype(np.float32), (vy + (Y - vy) * s - bob).astype(np.float32)
    def light(self, t, img, M):
        x, y = to_screen(M, 0.376, 0.676)
        f = 0.8 + 0.2 * flick(t, 16, 11, 0.7, 0.3)
        add_glow(img, [(x, y, 70, 0.30 * f), (x, y, 18, 0.55 * f)], LAMP)
        x, y = to_screen(M, 0.655, 0.245)
        add_glow(img, [(x, y, 120, 0.10)], LAMP)

# --- 5  street lamp flickers three times, Sardor glances back ----------------
class S_F12(Shot):
    key = "F12"
    def cam(self, t):
        k = C.smooth(self.u(t))
        dx, dy, r = shake(t, 2.0, 0.1, 1.0, 11.0)
        return dict(z=lerp(1.06, 1.15, k), cx=lerp(0.52, 0.56, k), cy=lerp(0.48, 0.42, k), r=r, dx=dx, dy=dy + 1.5 * math.sin(2 * math.pi * 2.6 * t))
    def lamp(self, t):
        a = C.f12_lamp(t); b = C.f12_lamp(t - 1 / FPS)
        return 0.7 * a + 0.3 * b
    def warp(self, t, X, Y):
        turn = C.smooth((t - 26.95) / 0.35)
        return blob_shift(X, Y, 0.585, 0.37, 0.15, 0.115, 0.010 * turn, 0.0, math.radians(-4.0) * turn, (0.60, 0.47))
    def light(self, t, img, M):
        g = self.lamp(t)
        m = warp_mask(PREP("F12")["cone"], M)
        img *= (0.45 + 0.55 * g) * (1 - 0.45 * m * (1 - g))[..., None]
        x, y = to_screen(M, 0.632, 0.112)
        add_glow(img, [(x, y, 200, 0.18 * g), (x, y, 45, 0.45 * g)], LAMP)

# --- 6  the tall dark figure in the road ----------------------------------------
class S_F13(Shot):
    key = "F13"
    def cam(self, t):
        k = C.smooth(self.u(t))
        dx, dy, r = shake(t, 2.0, 0.1, 1.0, 12.0)
        return dict(z=lerp(1.05, 1.30, k), cx=lerp(0.50, 0.60, k), cy=lerp(0.55, 0.43, k), r=r, dx=dx, dy=dy)
    def light(self, t, img, M):
        j = 1 + 0.22 * noise1(t, 4.0, 9.0) + 0.1 * (flick(t, 20, 13, 1, 0.12) - 1)
        m = warp_mask(PREP("F13")["beam"], M)
        img *= (1 + m * (j - 1) * 1.6)[..., None]
        pul = 0.75 + 0.25 * math.sin(2 * math.pi * 1.1 * t)
        pts = []
        for ex in (0.632, 0.648):
            x, y = to_screen(M, ex, 0.324)
            pts += [(x, y, 9, 0.28 * pul), (x, y, 3.5, 0.7 * pul)]
        add_glow(img, pts, EYES)

# --- 6  Sardor falls (day frame graded to night) ----------------------------------
class S_F14(Shot):
    key = "F14"; grade = "night"; vig = 0.6
    def cam(self, t):
        x = t - self.t0
        tilt = math.radians(7) * (1 - C.ease_out(x / 0.35)) - math.radians(1.5) * math.sin(min(x, 1.2) * 4) * math.exp(-x * 2)
        jx, jy = impulse(t, self.t0 + 0.02, 22, 0.4, 9)
        dx, dy, r = shake(t, 4, 0.2, 1.6, 13.0)
        return dict(z=lerp(1.20, 1.13, C.ease_out(self.u(t))), cx=0.52, cy=lerp(0.52, 0.55, self.u(t)), r=tilt + r, dx=dx + jx, dy=dy + jy)

# --- 6  running to the gate, the bike left behind (day frame graded to night) -----
class S_F15(Shot):
    key = "F15"; grade = "night"; vig = 0.6
    def cam(self, t):
        k = C.smooth(self.u(t))
        dx, dy, r = shake(t, 3, 0.15, 1.4, 14.0)
        step = 5 * abs(math.sin(2 * math.pi * 2.6 * t))
        return dict(z=1.24, cx=lerp(0.44, 0.60, k), cy=0.52, r=r, dx=dx, dy=dy - step)

# --- 7  the empty house -------------------------------------------------------------
class S_F16(Shot):
    key = "F16"
    def cam(self, t):
        k = C.smooth(self.u(t))
        dx, dy, r = shake(t, 1.2, 0.04, 0.5, 15.0)
        return dict(z=lerp(1.24, 1.05, k), cx=lerp(0.68, 0.52, k), cy=lerp(0.47, 0.50, k), dx=dx, dy=dy)
    def light(self, t, img, M):
        f = flick(t, 10, 21, 0.25, 0.2)
        x, y = to_screen(M, 0.39, 0.60)
        add_glow(img, [(x, y, 170, 0.12 * f), (x, y, 40, 0.22 * f)], LAMP)
        img *= 0.93 + 0.07 * f

# --- 7  Sardor hides in the shed --------------------------------------------------------
class S_F17(Shot):
    key = "F17"
    def cam(self, t):
        k = C.smooth(self.u(t))
        dx, dy, r = shake(t, 1.0, 0.04, 0.5, 16.0)
        return dict(z=lerp(1.05, 1.22, k), cx=lerp(0.52, 0.54, k), cy=lerp(0.50, 0.58, k), dx=dx, dy=dy)
    def warp(self, t, X, Y):
        th = math.radians(2.0) * math.sin(2 * math.pi * (t - self.t0) / 2.1)
        return pend_warp(X, Y, (0.668, 0.0), (0.672, 0.17), 0.04, th)
    def light(self, t, img, M):
        f = flick(t, 15, 31, 0.35, 0.18)
        img *= 0.86 + 0.14 * f
        x, y = to_screen(M, 0.672, 0.165)
        add_glow(img, [(x, y, 150, 0.16 * f), (x, y, 30, 0.35 * f)], LAMP)

# --- 8  two red eyes behind Sardor, the light goes out -----------------------------------
class S_F18(Shot):
    key = "F18"
    EYES_N = ((0.695, 0.321), (0.755, 0.321))
    def cam(self, t):
        k = C.smooth(C.clamp01((t - 37.0) / 2.5))
        dx, dy, r = shake(t, 0.8, 0.03, 0.4, 17.0)
        return dict(z=lerp(1.05, 1.13, k), cx=lerp(0.56, 0.62, k), cy=lerp(0.50, 0.45, k), dx=dx, dy=dy)
    def eyes(self, t):
        a = C.smooth((t - 37.5) / 1.0)
        pul = 1.0 if t < 38.5 else 0.82 + 0.18 * math.cos(2 * math.pi * 1.1 * (t - 38.5))
        return a, pul
    def source(self, t):
        a, pul = self.eyes(t)
        d = PREP("F18")
        if a >= 1 and pul >= 0.999: return SRC("F18")
        m = d["emask"][..., None] * (1 - a * pul)
        src = SRC("F18").astype(np.float32)
        return (src * (1 - m) + d["plate"].astype(np.float32) * m).astype(np.uint8)
    def light(self, t, img, M):
        a, pul = self.eyes(t)
        pts = []
        for ex, ey in self.EYES_N:
            x, y = to_screen(M, ex, ey)
            pts += [(x, y, 40, 0.30 * a * pul), (x, y, 12, 0.6 * a * pul)]
        add_glow(img, pts, EYES)
        x, y = to_screen(M, 0.20, 0.655)
        add_glow(img, [(x, y, 160, 0.10)], LAMP)

class S_BLACK(Shot):
    key = None
    def render(self, t, i):
        img = np.zeros((H, W, 3), np.float32)
        if t < C.LIGHT_OFF_T + C.EYES_HOLD:
            M = cam_matrix(**S_F18(37.0, 39.5).cam(C.LIGHT_OFF_T))
            pts = []
            for ex, ey in S_F18.EYES_N:
                x, y = to_screen(M, ex, ey)
                pts += [(x, y, 34, 0.35), (x, y, 10, 0.9), (x, y, 4, 1.2)]
            add_glow(img, pts, EYES)
        img += grain(i, 0.010)
        return img

# --- 9  the light comes back: the shed is empty -----------------------------------------
class S_F19(Shot):
    key = "F19"
    def theta(self, t):
        x = t - self.t0
        return math.radians(8.0) * math.exp(-x / 2.2) * math.sin(2 * math.pi * x / 1.35 + 0.9)
    def cam(self, t):
        k = C.smooth(self.u(t))
        dx, dy, r = shake(t, 1.0, 0.04, 0.5, 18.0)
        return dict(z=lerp(1.05, 1.11, k), cx=0.5, cy=lerp(0.48, 0.50, k), dx=dx, dy=dy)
    def warp(self, t, X, Y):
        return pend_warp(X, Y, (0.522, 0.165), (0.519, 0.345), 0.05, self.theta(t))
    def light(self, t, img, M):
        g = C.f19_bulb(t)
        th = self.theta(t)
        swing_light(img, M, (0.52, 0.34), th, 0.24, (0.40, 0.45), 0.66)
        img *= 0.10 + 0.90 * g
        x, y = to_screen(M, 0.519 + 0.18 * math.sin(th), 0.335)
        add_glow(img, [(x, y, 170, 0.20 * g), (x, y, 40, 0.40 * g)], LAMP)

# --- 9/10  the bike in the street: front wheel still spinning, then stops ---------
class S_F20(Shot):
    key = "F20"
    def cam(self, t):
        if t < 45.0 - D5:
            k = C.smooth(C.clamp01((t - 43.0) / 1.5))
            return dict(z=lerp(1.06, 1.12, k), cx=lerp(0.55, 0.60, k), cy=lerp(0.56, 0.60, k))
        k = C.smooth(C.clamp01((t - (47.5 - D5)) / 3.0))
        return dict(z=lerp(1.10, 1.20, k), cx=lerp(0.58, 0.64, k), cy=lerp(0.58, 0.63, k))
    def source(self, t):
        return PREP("F20")["wheel"].apply(SRC("F20"), C.wheel_angle(t), C.wheel_speed(t))
    def light(self, t, img, M):
        g = C.f20_lamp(t)
        x, y = to_screen(M, 0.515, 0.163)
        if g < 1:
            m = glow_map([(x, y + 0.20 * H, 0.30 * W, 1.0)])
            img *= (1 - 0.55 * (1 - g) * np.clip(m, 0, 1))[..., None]
            img *= 0.55 + 0.45 * g
        hum = 0.92 + 0.08 * flick(t, 12, 41, 0.6, 0.2)
        add_glow(img, [(x, y, 130, 0.20 * g * hum), (x, y, 30, 0.45 * g * hum)], LAMP)
        img *= C.end_darken(t)

class S_F21(Shot):
    key = "F21"
    def cam(self, t):
        k = C.smooth(self.u(t))
        dx, dy, r = shake(t, 1.0, 0.03, 0.4, 19.0)
        return dict(z=lerp(1.06, 1.11, k), cx=lerp(0.50, 0.49, k), cy=lerp(0.50, 0.52, k), dx=dx, dy=dy)
    def source(self, t):
        return PREP("F21")["wheel"].apply(SRC("F21"), C.wheel_angle(t), C.wheel_speed(t))
    def light(self, t, img, M):
        sp = min(1.0, C.wheel_speed(t) / 1.0)       # dynamo headlamp follows the wheel
        x, y = to_screen(M, 0.405, 0.0)
        add_glow(img, [(x, y, 200, 0.12 + 0.15 * sp), (x, y, 50, 0.2 + 0.25 * sp)], LAMP)

SHOT_CLASSES = {k[2:]: v for k, v in globals().items() if k.startswith("S_")}

def build_shots():
    out = []
    for key, a, b, sid in shot_list():
        out.append((a, b, sid, SHOT_CLASSES[key](a, b)))
    return out

SHOTS = build_shots()

def shot_at(t):
    for a, b, sid, s in SHOTS:
        if a - 1e-9 <= t < b - 1e-9:
            return s, sid
    return SHOTS[-1][3], SHOTS[-1][2]

# ---------------------------------------------------------------------------
# text
@lru_cache(maxsize=None)
def font(size, path=FONT):
    return ImageFont.truetype(path, size)

SUB_SIZE = 74
SUB_Y = 1400            # plate centre (Reels safe zone: above the caption/UI band)
SUB_MAXW = 772         # plate <= 840 px: stays left of the Reels action column
PADX, PADY = 34, 20

def text_w(s, size, path=FONT):
    return font(size, path).getlength(s)

def load_timing():
    tj = json.load(open(os.path.join(WORK, "timing.json")))
    return tj

def build_chunks(tj):
    """one-line chunks: split at sentence ends, then a DP per sentence -> fewest plates,
    no plate ending on a short word (keeps "hech kim" together), balanced widths"""
    gap = text_w(" ", SUB_SIZE)
    def width(ws): return sum(text_w(x["text"], SUB_SIZE) for x in ws) + gap * (len(ws) - 1)
    chunks = []
    for line, L in sorted(tj["lines"].items(), key=lambda kv: int(kv[0])):
        sent, cur = [], []
        for w in L["words"]:
            cur.append(w)
            if w["text"].rstrip()[-1:] in ".!?—": sent.append(cur); cur = []
        if cur: sent.append(cur)
        for sw in sent:
            n = len(sw); best = {0: (0.0, [])}
            for j in range(1, n + 1):
                for i in range(max(0, j - 3), j):
                    if i not in best: continue
                    seg = sw[i:j]; wd = width(seg)
                    if wd > SUB_MAXW and j - i > 1: continue
                    pen = 100.0
                    if j < n and len(seg[-1]["text"].strip(".,!?—")) <= 4: pen += 60
                    pen += (wd / SUB_MAXW) ** 2 * 5
                    c = best[i][0] + pen
                    if j not in best or c < best[j][0]: best[j] = (c, best[i][1] + [seg])
            chunks += best[n][1]
    return chunks

def chunk_windows(tj, chunks):
    scene_end = {s["line"]: s["end"] for s in SCENES if s["line"]}
    res = []
    for ci, ch in enumerate(chunks):
        line = None
        for ln, L in tj["lines"].items():
            if ch[0] in L["words"]: line = int(ln)
        L = tj["lines"][str(line)]
        f0 = fr(ch[0]["start"])
        nxt = chunks[ci + 1] if ci + 1 < len(chunks) else None
        if nxt is not None and nxt[0] in L["words"]:
            f1 = fr(nxt[0]["start"])
        else:
            f1 = min(fr(L["words"][-1]["end"] + 0.15), fr(scene_end[line]))
        res.append((f0, f1, ch))
    return res

PAUSE_HIDE = 0.5
_SUBCACHE = {}
def sub_image(ch, active):
    key = (tuple(w["text"] for w in ch), active)
    if key in _SUBCACHE: return _SUBCACHE[key]
    f = font(SUB_SIZE)
    gap = f.getlength(" ")
    ws = [f.getlength(w["text"]) for w in ch]
    tw = sum(ws) + gap * (len(ch) - 1)
    asc, desc = f.getmetrics()
    th = asc + desc
    pw, ph = int(tw + 2 * PADX), int(th + 2 * PADY)
    im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=26, fill=SHADOW1 + (int(255 * 0.75),))
    x = PADX
    for k, w in enumerate(ch):
        col = ALARM if k == active else TEXT
        d.text((x, PADY), w["text"], font=f, fill=col + (255,))
        x += ws[k] + gap
    arr = np.asarray(im).astype(np.float32) / 255
    _SUBCACHE[key] = arr
    return arr

def blit(img, rgba, cx, cy):
    h, w = rgba.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xb <= xa or yb <= ya: return
    s = rgba[ya - y0:yb - y0, xa - x0:xb - x0]
    a = s[..., 3:4]
    img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - a) + s[..., :3] * a

def subtitle_box(ch):
    a = sub_image(ch, 0)
    h, w = a.shape[:2]
    return (W / 2 - w / 2, SUB_Y - h / 2, W / 2 + w / 2, SUB_Y + h / 2)

_TITLE = {}
def title_image(lines, size, glow_rgb, glow_a, path=FONT_BLACK, spacing=1.08):
    key = (tuple(lines), size, glow_rgb, round(glow_a, 2))
    if key in _TITLE: return _TITLE[key]
    f = font(size, path)
    asc, desc = f.getmetrics()
    lh = int((asc + desc) * spacing)
    tw = int(max(f.getlength(l) for l in lines))
    pad = 70
    im = Image.new("L", (tw + 2 * pad, lh * len(lines) + 2 * pad), 0)
    d = ImageDraw.Draw(im)
    for k, l in enumerate(lines):
        d.text(((im.width - f.getlength(l)) / 2, pad + k * lh), l, font=f, fill=255)
    a = np.asarray(im).astype(np.float32) / 255
    g = np.asarray(im.filter(ImageFilter.GaussianBlur(22))).astype(np.float32) / 255
    g2 = np.asarray(im.filter(ImageFilter.GaussianBlur(7))).astype(np.float32) / 255
    glow = np.clip((g * 1.6 + g2 * 0.6) * glow_a, 0, 1)
    rgb = np.zeros(a.shape + (3,), np.float32)
    rgb[:] = rgbf(glow_rgb)
    rgb = rgb * glow[..., None] * (1 - a[..., None]) + rgbf(TEXT) * a[..., None]
    alpha = np.clip(a + glow * (1 - a), 0, 1)
    out = np.concatenate([rgb / np.maximum(alpha[..., None], 1e-6), alpha[..., None]], 2)
    _TITLE[key] = out
    return out

HOOK_LINES = ["Bu bazada", "nima bor?"]
HOOK_SIZE = 138
HOOK_Y = 560
CTA_LINES = ["Davomi bor"]
CTA_SIZE = 150
CTA_Y = 820

def hook_box():
    a = title_image(HOOK_LINES, HOOK_SIZE, ALARM, 0.8)
    h, w = a.shape[:2]
    return (W / 2 - w / 2 + 70, HOOK_Y - h / 2 + 70, W / 2 + w / 2 - 70, HOOK_Y + h / 2 - 70)

class Overlay:
    def __init__(self):
        self.tj = load_timing()
        self.chunks = build_chunks(self.tj)
        self.win = chunk_windows(self.tj, self.chunks)
        dav = [w for w in self.tj["lines"]["5"]["words"] if w["script"].startswith("Davomi")][0]
        self.cta_f = fr(dav["start"])

    def apply(self, img, i):
        t = i / FPS
        if i < fr(3.0):                                      # hook text, visible from frame 0
            p = C.alarm(t)
            ga = round(0.55 + 0.35 * p, 2)
            blit(img, title_image(HOOK_LINES, HOOK_SIZE, ALARM, ga), W / 2, HOOK_Y)
        if i >= self.cta_f:                                  # "Davomi bor" from the spoken word "Davomi"
            k = C.clamp01((i - self.cta_f) / 6)
            a = title_image(CTA_LINES, CTA_SIZE, ALARM, 0.75)
            if k < 1:
                sc = 1.10 - 0.10 * C.ease_out(k)
                a = cv2.resize(a, None, fx=sc, fy=sc, interpolation=cv2.INTER_LINEAR)
            blit(img, a, W / 2, CTA_Y)
        for f0, f1, ch in self.win:
            if f0 <= i < f1:
                act = 0
                for k, w in enumerate(ch):
                    if i >= fr(w["start"]): act = k
                if not self.in_pause(i):
                    blit(img, sub_image(ch, act), W / 2, SUB_Y)
                break
        return img

    def in_pause(self, i):
        """inside a pause of >= 0.5 s between two words of a line (shown only while someone speaks)"""
        for L in self.tj["lines"].values():
            ws = L["words"]
            for a, b in zip(ws, ws[1:]):
                if b["start"] - a["end"] >= PAUSE_HIDE and fr(a["end"] + 0.12) <= i < fr(b["start"]):
                    return True
        return False

OVL = None
def render_frame(i):
    global OVL
    if OVL is None: OVL = Overlay()
    t = i / FPS
    s, sid = shot_at(t)
    img = s.render(t, i)
    img = OVL.apply(img, i)
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)

def main(out_mp4, audio_wav, workers=4, frames=None):
    from multiprocessing import Pool
    n = NFRAMES if frames is None else frames
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", audio_wav, "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-maxrate", "12M", "-bufsize", "24M",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
           "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", str(SR),
           "-t", f"{DURATION:.3f}", "-movflags", "+faststart", out_mp4]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with Pool(workers) as pool:
        for k, fr_ in enumerate(pool.imap(render_frame, range(n), chunksize=6)):
            p.stdin.write(fr_.tobytes())
            if k % 150 == 0: print(f"frame {k}/{n}  {time.time() - t0:.0f}s", flush=True)
    p.stdin.close(); p.wait()
    print("done", out_mp4, f"{time.time() - t0:.0f}s")

def preview(times, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for t in times:
        i = fr(t)
        Image.fromarray(render_frame(i)).save(os.path.join(out_dir, f"t{t:06.2f}.png"))

if __name__ == "__main__":
    if sys.argv[1] == "preview":
        preview([float(x) for x in sys.argv[3:]], sys.argv[2])
    else:
        main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 4)
