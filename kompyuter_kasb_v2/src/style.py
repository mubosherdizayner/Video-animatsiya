# Style helpers (fixed for the whole video): morning palette, sky gradient, flat clouds, layered camera,
# paper grain, vignette. Environments themselves live in env.py.
import math
import numpy as np
import skia
from scipy.ndimage import gaussian_filter
from common import *

P = dict(sky_top="#F3E3D3", sky_bot="#E6EDEF", l1="#D5DDDA", l2="#B8C6C4", l3="#93A5A6", l4="#64777A", l5="#3C4B4F",
         glow="#F3E3D3", lamp="#E7A05C", accent="#E1742F", cloud="#F8F3EC", ink="#1F292C", cream="#F4EDDF")
HORIZON = 1180.0


class Cam:
    """layered camera: each layer gets its own parallax for pans (x) and push-ins (zoom)"""

    def __init__(self, x=0.0, y=0.0, zoom=1.0, cx=W / 2, cy=H / 2, rot=0.0, shake=(0.0, 0.0), dark=0.0):
        self.x, self.y, self.zoom, self.cx, self.cy, self.rot, self.shake, self.dark = x, y, zoom, cx, cy, rot, shake, dark

    def begin(self, c, f=1.0, fy=None):
        z = 1.0 + (self.zoom - 1.0) * (0.3 + 0.7 * f)
        c.save()
        c.translate(self.cx, self.cy); c.scale(z, z)
        c.translate(-self.cx - self.x * f, -self.cy + self.y * (f if fy is None else fy))

    def to_screen(self, x, y, f=1.0):
        z = 1.0 + (self.zoom - 1.0) * (0.3 + 0.7 * f)
        return self.cx + z * (x - self.x * f - self.cx), self.cy + z * (y + self.y - self.cy)


def sky(c, horizon=HORIZON):
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, horizon)], [col(P["sky_top"]), col(P["sky_bot"])])
    c.drawRect(skia.Rect.MakeLTRB(-4000, -3000, 6000, 4000), skia.Paint(Shader=sh))


_CLOUD = {}


def cloud_path(seed, w):
    key = (seed, round(w))
    if key in _CLOUD: return _CLOUD[key]
    p = skia.Path()
    n = 5 + int(3 * hash01(seed, 1))
    for i in range(n):
        u = (i + 0.5) / n
        r = w * (0.12 + 0.1 * math.sin(u * math.pi) + 0.05 * hash01(seed, i))
        p.addCircle(-w / 2 + u * w, -r * 0.55, r)
    p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(-w * 0.55, -w * 0.1, w * 0.55, 0), w * 0.05, w * 0.05))
    p = skia.Op(p, skia.Path(), skia.PathOp.kUnion_PathOp)
    clip = skia.Path(); clip.addRect(skia.Rect.MakeLTRB(-w, -w, w, 0))
    p = skia.Op(p, clip, skia.PathOp.kIntersect_PathOp)       # flat bottom
    _CLOUD[key] = p
    return p


CLOUDS = [(1, 160, 300, 260), (2, 640, 230, 200), (3, 980, 420, 300), (4, -260, 470, 230), (5, 1400, 260, 240),
          (6, 420, 640, 170), (7, 1800, 560, 210)]


def clouds(c, W, cam, dy=0.0, alpha=1.0, items=CLOUDS, speed=9.0):
    cam.begin(c, 0.04)
    pc = paint(P["cloud"], a=255 * alpha)
    for seed, x, y, w in items:
        xx = (x + speed * W * (0.7 + 0.6 * hash01(seed, 9)) + 600) % 2600 - 600
        c.save(); c.translate(xx, y + dy); c.drawPath(cloud_path(seed, w), pc); c.restore()
    c.restore()


_GRAIN = {}


def grain_image():
    if "g" not in _GRAIN:
        rng = np.random.RandomState(5)
        n = gaussian_filter(rng.randn(H, W), 0.6) * 1.0 + gaussian_filter(rng.randn(H, W), 2.5) * 2.2
        fib = gaussian_filter(rng.randn(H, W), (0.6, 9)) * 3.0
        v = 255 - np.clip(9 + 6 * n + 4 * fib, 0, 40)
        a = np.dstack([v, v, v * 0.985, np.full_like(v, 255)]).astype(np.uint8)
        _GRAIN["g"] = skia.Image.fromarray(np.ascontiguousarray(a), colorType=skia.kRGBA_8888_ColorType)
    return _GRAIN["g"]


def overlays(c, vignette=0.22):
    pt = skia.Paint(); pt.setBlendMode(skia.BlendMode.kMultiply)
    c.drawImage(grain_image(), 0, 0, skia.SamplingOptions(), pt)
    g = skia.GradientShader.MakeRadial(skia.Point(W / 2, H * 0.47), H * 0.66,
                                       [col("#1A2124", 0), col("#1A2124", 0), col("#1A2124", 255 * vignette)], [0.0, 0.55, 1.0])
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=g))


def finish(surf, cam):
    """raster camera effects: rotation / shake and the 'one tone darker' snap"""
    if cam.dark > 0:
        surf.getCanvas().drawRect(skia.Rect.MakeWH(W, H), paint("#1F292C", a=255 * cam.dark))
    if cam.rot or cam.shake[0] or cam.shake[1]:
        img = surf.makeImageSnapshot()
        s2 = skia.Surface(W, H); c2 = s2.getCanvas()
        r = math.radians(abs(cam.rot))
        k = (math.cos(r) + math.sin(r) * H / W) if cam.rot else 1.0
        k = max(k, 1.0 + 4 * max(abs(cam.shake[0]), abs(cam.shake[1])) / W)
        c2.translate(W / 2 + cam.shake[0], H / 2 + cam.shake[1]); c2.rotate(cam.rot); c2.scale(k, k); c2.translate(-W / 2, -H / 2)
        c2.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear))
        return s2
    return surf


def stroke_path(p, w):
    pt = skia.Paint(AntiAlias=True); pt.setStyle(skia.Paint.kStroke_Style); pt.setStrokeWidth(w)
    pt.setStrokeCap(skia.Paint.kRound_Cap); pt.setStrokeJoin(skia.Paint.kRound_Join)
    out = skia.Path(); pt.getFillPath(p, out); return out


def rise(t, t0, dur=0.6):
    """0 -> 1 ease over dur starting at t0 (era change layer motion)"""
    return ease_io(clamp01((t - t0) / dur))
