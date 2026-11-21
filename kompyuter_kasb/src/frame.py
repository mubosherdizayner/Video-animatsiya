# Frame compositor: camera, world drawing, water reflection, raster camera moves, overlays.
import math
import numpy as np
import skia
from common import *
import world as WD


class Cam:
    def __init__(self, x=0.0, y=0.0, zoom=1.0, cx=W / 2, cy=H / 2, rot=0.0, shake=(0.0, 0.0)):
        self.x, self.y, self.zoom, self.cx, self.cy, self.rot, self.shake = x, y, zoom, cx, cy, rot, shake

    def apply(self, c):
        c.translate(self.cx, self.cy); c.scale(self.zoom, self.zoom); c.translate(-self.cx, -self.cy + self.y)

    def sy(self, wy):
        return self.cy + self.zoom * (wy + self.y - self.cy)

    def sx(self, wx, f=1.0):
        return self.cx + self.zoom * (wx - self.x * f - self.cx)


def render_world(cam, draw_back, draw_front=None, water=None):
    """draw_back(c) draws everything above / reflected in the water (in world coords, camera applied).
    water: dict(t, pal, amp, sun_x(screen), glint, ...) or None. draw_front(c) draws after the water (camera applied)."""
    surf = skia.Surface(W, H)
    c = surf.getCanvas()
    c.clear(col("#F4EDDF"))
    c.save(); cam.apply(c); draw_back(c); c.restore()
    if water is not None:
        arr = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
        bank_s = cam.sy(WD.BANK)
        arr = WD.water_reflect(arr, bank_s, water["t"], water["pal"], water.get("amp", 1.0))
        img = skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType)
        c.drawImage(img, 0, 0)
    if draw_front is not None:
        c.save(); cam.apply(c); draw_front(c); c.restore()
    if cam.rot or cam.shake[0] or cam.shake[1]:
        img = surf.makeImageSnapshot()
        surf2 = skia.Surface(W, H); c2 = surf2.getCanvas()
        r = math.radians(abs(cam.rot))
        k = (math.cos(r) + math.sin(r) * H / W) if cam.rot else 1.0
        k = max(k, 1.0 + 2 * max(abs(cam.shake[0]), abs(cam.shake[1])) / W * 2)
        c2.translate(W / 2 + cam.shake[0], H / 2 + cam.shake[1]); c2.rotate(cam.rot); c2.scale(k, k); c2.translate(-W / 2, -H / 2)
        c2.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear))
        return surf2
    return surf
