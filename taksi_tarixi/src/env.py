# Environments as stacks of flat parallax silhouette layers.
#  A: modern Uzbek city street at dusk (SHOM)    B: old European street, 1891 morning (TONG)
import math, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from gfx import (W, H, Pen, mask_pen, paste_color, comp, hx, mix, sky, sun_img, cloud_mask, catmull, circle_pts,
                 smooth, clamp01, SS)
import props as P


class Layer:
    """mask covering [0, period+W) horizontally, top at y0 (frame coords at cam_y=0)."""

    def __init__(self, mask, idx, par, y0, period, win=None, win_col=None):
        self.mask, self.idx, self.par, self.y0, self.period = mask, idx, par, y0, period
        self.win, self.win_col = win, win_col     # windows: list of (x,y,w,h,t_on) in mask coords

    def offset(self, cam_x): return (cam_x * self.par) % self.period

    def draw(self, frame, color, cam_x, cam_y=0.0, alpha=1.0, t=0.0, win_rgb=None, win_alpha=0.6, sy=1.0):
        off = self.offset(cam_x)
        m = self.mask.crop((int(off), 0, int(off) + W, self.mask.height))
        y = self.y0 + cam_y * self.par
        if sy != 1.0:     # vertical squash/grow from the layer bottom (morph)
            nh = max(1, int(m.height * sy)); m = m.resize((W, nh), Image.BILINEAR); y += self.mask.height - nh
        if alpha < 1: m = m.point(lambda v: int(v * alpha))
        frame.paste(color, (0, int(y), W, int(y) + m.height), m)
        if self.win and win_rgb is not None and sy == 1.0:
            wm = Image.new('L', (W, self.mask.height), 0); d = ImageDraw.Draw(wm)
            a = int(255 * win_alpha * alpha)
            for (x, yy, w, h, ton) in self.win:
                if ton > t: continue
                xx = x - off
                if xx < -w or xx > W: continue
                fade = min(1.0, (t - ton) / 0.25)
                d.rectangle((xx, yy, xx + w - 1, yy + h - 1), fill=int(a * fade))
            frame.paste(win_rgb, (0, int(y), W, int(y) + wm.height), wm)


def _wrap_draw(pen_fn, period, x, w):
    """draw a shape at x and its wrapped copies so the strip tiles seamlessly"""
    for dx in (-period, 0, period):
        if x + dx + w >= 0 and x + dx <= period + W: pen_fn(x + dx)


class Env:
    def __init__(self, kind, sc=1.0, H0=1185, seed=1, period=None, opts=()):
        self.kind, self.sc, self.H0, self.opts = kind, sc, H0, set(opts)
        self.rng = np.random.RandomState(seed)
        self.period = period or int(2700 * sc)
        self.layers = []
        self.poplars = []; self.lamps = []
        (self._build_A if kind == 'A' else self._build_B)()

    # ----------------------------------------------------------- A: dusk city
    def _build_A(self):
        sc, H0, rng, per = self.sc, self.H0, self.rng, self.period
        # L0: distant low skyline
        top = int(H0 - 300 * sc); h = int(H0 + 40 - top)
        p = mask_pen(per + W, h)
        x = -50
        while x < per:
            w = rng.uniform(90, 220) * sc; hh = rng.uniform(80, 230) * sc
            def f(xx, w=w, hh=hh):
                p.rect(xx, h - 40 - hh, xx + w, h, 255)
                if rng.rand() < 0.3: p.rect(xx + w * 0.4, h - 40 - hh - 40 * sc, xx + w * 0.46, h, 255)
            _wrap_draw(f, per, x, w); x += w * rng.uniform(0.55, 1.0)
        self.layers.append(Layer(p.result(), 0, 0.05, top, per))
        # L1, L2: apartment blocks with windows
        for idx, (par, hmin, hmax, wmin, wmax, gap) in ((1, (0.13, 300, 520, 120, 210, 60)), (2, (0.26, 190, 380, 170, 280, 120))):
            top = int(H0 - hmax * sc - 20); h = int(H0 + 30 - top) + 500
            p = mask_pen(per + W, h); wins = []
            x = rng.uniform(0, 80)
            while x < per - wmin * sc:
                w = rng.uniform(wmin, wmax) * sc; hh = rng.uniform(hmin, hmax) * sc
                bx = x; by = h - 530 - hh
                floors = int(hh / (34 * sc)); cols = max(2, int(w / (30 * sc)))
                ww, wh = 12 * sc, 14 * sc
                cell = []
                for fl in range(1, floors):
                    for c in range(cols):
                        wx = bx + (c + 0.5) * w / cols - ww / 2; wy = by + fl * hh / floors - wh / 2 + 6 * sc
                        if wy + wh > h - 534: continue
                        cell.append((wx, wy))
                def f(xx, w=w, hh=hh, by=by, bx=bx):
                    p.rect(xx, by, xx + w, h, 255)
                    p.rect(xx - 2, h - 520, xx + w + gap * sc * 1.2, h, 255)
                    p.rect(xx + w * 0.15, by - 14 * sc, xx + w * 0.32, by + 1, 255)     # roof box
                _wrap_draw(f, per, bx, w)
                for (wx, wy) in cell:
                    if rng.rand() < 0.42:
                        ton = rng.uniform(-14, 46)
                        for dx in (0, per):
                            if wx + dx < per + W: wins.append((int(wx + dx), int(wy), max(2, int(ww)), max(2, int(wh)), ton))
                x += w + rng.uniform(0.2, 1.0) * gap * sc
            self.layers.append(Layer(p.result(), idx, par, top, per, wins))
        # L3: sidewalk strip + lamp posts (poplars are dynamic)
        top = int(H0 - 560 * sc); h = int(H0 + 8 - top) + 500
        p = mask_pen(per + W, h)
        p.rect(0, h - 500 - 26 * sc, per + W, h, 255)                            # sidewalk strip (+ ground below)
        x = 60 * sc; k = 0
        while x < per:
            if k % 2 == 0:      # street lamp: pole + arm + head
                def f(xx):
                    b = h - 500
                    p.rect(xx - 4 * sc, b - 26 * sc - 380 * sc, xx + 4 * sc, b, 255)
                    p.line([(xx, b - 400 * sc), (xx + 40 * sc, b - 418 * sc), (xx + 70 * sc, b - 414 * sc)], 255, 6 * sc)
                    p.rrect(xx + 52 * sc, b - 418 * sc, xx + 92 * sc, b - 404 * sc, 6 * sc, 255)
                _wrap_draw(f, per, x - 10, 110 * sc)
                self.lamps.append((x - 10, top + h - 500 - 398 * sc))
            else:
                self.poplars.append((x, rng.uniform(380, 520) * sc, rng.uniform(48, 64) * sc, rng.uniform(0, 6.28)))
            x += rng.uniform(150, 230) * sc; k += 1
        if 'busstop' in self.opts:
            bx = self.opts_busstop_x if hasattr(self, 'opts_busstop_x') else per * 0.0 + 200 * sc
        self.layers.append(Layer(p.result(), 3, 0.55, top, per))
        self.L3_top, self.L3_h = top, h - 500
        # L4: road
        top = int(H0 - 4); h = H - top + 300
        p = mask_pen(per + W, h); p.rect(0, 0, per + W, h, 255)
        self.layers.append(Layer(p.result(), 4, 1.0, top, per))
        # lane dashes (drawn per frame at parallax 1.0)
        self.dash_y = H0 + 230 * sc

    # ----------------------------------------------------------- B: 1891 morning street
    def _build_B(self):
        sc, H0, rng, per = self.sc, self.H0, self.rng, self.period
        # L0: hazy far rooftops (+ a dome)
        top = int(H0 - 300 * sc); h = int(H0 + 40 - top)
        p = mask_pen(per + W, h)
        x = -40
        while x < per:
            w = rng.uniform(80, 170) * sc; hh = rng.uniform(70, 170) * sc; rf = rng.uniform(30, 80) * sc
            def f(xx, w=w, hh=hh, rf=rf):
                p.poly([(xx, h), (xx, h - 40 - hh), (xx + w / 2, h - 40 - hh - rf), (xx + w, h - 40 - hh), (xx + w, h)], 255)
            _wrap_draw(f, per, x, w); x += w * rng.uniform(0.7, 1.0)
        def dome(xx):
            p.ellipse(xx, h - 40 - 210 * sc, 70 * sc, 60 * sc, 255); p.rect(xx - 70 * sc, h - 40 - 210 * sc, xx + 70 * sc, h, 255)
            p.rect(xx - 3 * sc, h - 40 - 300 * sc, xx + 3 * sc, h - 40 - 260 * sc, 255)
        _wrap_draw(dome, per, per * 0.62, 150 * sc)
        self.layers.append(Layer(p.result(), 0, 0.05, top, per))
        # L1: distant rooftops + one tall spire
        top = int(H0 - 720 * sc); h = int(H0 + 30 - top)
        p = mask_pen(per + W, h)
        x = -40
        while x < per:
            w = rng.uniform(110, 200) * sc; hh = rng.uniform(150, 260) * sc; rf = rng.uniform(60, 120) * sc
            def f(xx, w=w, hh=hh, rf=rf):
                p.poly([(xx, h), (xx, h - 30 - hh), (xx + w * 0.5, h - 30 - hh - rf), (xx + w, h - 30 - hh), (xx + w, h)], 255)
                p.rect(xx + w * 0.7, h - 30 - hh - rf * 0.7, xx + w * 0.78, h - 30 - hh, 255)
            _wrap_draw(f, per, x, w); x += w * rng.uniform(0.75, 1.05)
        def spire(xx):
            b = h - 30
            p.rect(xx - 50 * sc, b - 380 * sc, xx + 50 * sc, b, 255)
            p.rect(xx - 38 * sc, b - 470 * sc, xx + 38 * sc, b - 380 * sc, 255)
            p.poly([(xx - 40 * sc, b - 470 * sc), (xx, b - 680 * sc), (xx + 40 * sc, b - 470 * sc)], 255)
            p.rect(xx - 2 * sc, b - 700 * sc, xx + 2 * sc, b - 670 * sc, 255)
        _wrap_draw(spire, per, per * 0.28, 110 * sc)
        self.layers.append(Layer(p.result(), 1, 0.12, top, per))
        # L2 / L3: townhouses with steep roofs & chimneys, window shapes in a lighter tone
        for idx, par, hmin, hmax in ((2, 0.24, 300, 380), (3, 0.45, 360, 470)):
            top = int(H0 - (hmax + 260) * sc); h = int(H0 + 20 - top) + 400
            p = mask_pen(per + W, h); wp = mask_pen(per + W, h)
            x = rng.uniform(-30, 30)
            while x < per:
                w = rng.uniform(150, 230) * sc; hh = rng.uniform(hmin, hmax) * sc; rf = rng.uniform(110, 190) * sc
                floors = 3 if hh < 350 * sc else 4; cols = 3 if w > 185 * sc else 2
                ch = [(rng.uniform(0.15, 0.8), rng.uniform(40, 80) * sc) for _ in range(rng.randint(1, 3))]
                def f(xx, w=w, hh=hh, rf=rf, floors=floors, cols=cols, ch=ch):
                    b = h - 420
                    for (cx, cl) in ch:
                        cxp = xx + w * cx; yy = b - hh - rf * (1 - abs(cx - 0.5) * 2) * 0.85
                        p.rect(cxp - 9 * sc, yy - cl, cxp + 9 * sc, b - hh, 255)
                    p.poly([(xx - 6 * sc, b - hh), (xx + w / 2, b - hh - rf), (xx + w + 6 * sc, b - hh)], 255)
                    p.rect(xx, b - hh, xx + w, h, 255)
                    fh = hh / (floors + 0.4)
                    for fl in range(floors):
                        for c in range(cols):
                            wx = xx + (c + 0.5) * w / cols; wy = b - hh + fl * fh + fh * 0.25
                            wp.rrect(wx - 11 * sc, wy, wx + 11 * sc, wy + fh * 0.5, 6 * sc, 255)
                    # dormer window in the roof
                    wp.poly([(xx + w / 2 - 12 * sc, b - hh - rf * 0.25), (xx + w / 2, b - hh - rf * 0.45), (xx + w / 2 + 12 * sc, b - hh - rf * 0.25)], 255)
                _wrap_draw(f, per, x, w + 10 * sc); x += w + rng.uniform(0, 24) * sc
            L = Layer(p.result(), idx, par, top, per)
            L.winmask = wp.result()
            self.layers.append(L)
        # L4: cobblestone road (+ curb). Gas lamps are drawn per frame at parallax 0.85.
        top = int(H0 - 4); h = H - top + 300
        p = mask_pen(per + W, h); p.rect(0, 0, per + W, h, 255)
        stones = mask_pen(per + W, h)
        y = 34 * sc; row = 0; rh = 15 * sc
        while y < h:
            sw = (46 + row * 3.2) * sc; gap = 9 * sc; xo = (row % 2) * sw * 0.5 - sw
            xs = xo
            while xs < per + W:
                stones.rrect(xs + gap / 2, y, xs + sw - gap / 2, y + rh, min(rh, sw) * 0.4, 255)
                xs += sw
            y += rh + (10 + row * 1.6) * sc; rh = (15 + row * 1.9) * sc; row += 1
        L = Layer(p.result(), 4, 1.0, top, per)
        L.stones = stones.result()
        self.layers.append(L)
        self.gaslamps = [(x, ) for x in np.arange(120, per, 520) * sc]

    # ----------------------------------------------------------- per frame
    def draw_poplars(self, frame, color, cam_x, cam_y, t, alpha=1.0, frozen=False):
        L = self.layers[3]; off = L.offset(cam_x)
        y0 = L.y0 + cam_y * L.par
        band_top = int(y0); bh = int(L.mask.height) - (500 if self.kind == 'A' else 0)
        p = mask_pen(W, bh)
        b = bh - 20 * self.sc
        for (x, hh, ww, ph) in self.poplars:
            for dx in (0, self.period, -self.period):
                xx = x - off + dx
                if xx < -ww - 40 or xx > W + ww + 40: continue
                sway = 0 if frozen else 1
                amp = (7 + 4 * math.sin(ph)) * self.sc
                s = sway * amp * math.sin(t * 1.4 + ph)
                pts = []
                N = 14
                for k in range(N + 1):              # flame-shaped crown, top sways more
                    v = k / N; yy = b - 40 * self.sc - v * hh
                    wv = ww * (math.sin(math.pi * (0.08 + 0.92 * v)) ** 0.9) * (1 - 0.45 * v)
                    pts.append((xx + s * v * v - wv / 2, yy))
                right = [(xx + s * (k / N) ** 2 + ww * (math.sin(math.pi * (0.08 + 0.92 * k / N)) ** 0.9) * (1 - 0.45 * k / N) / 2,
                          b - 40 * self.sc - k / N * hh) for k in range(N, -1, -1)]
                p.poly(pts + right, 255)
                p.rect(xx - 5 * self.sc, b - 60 * self.sc, xx + 5 * self.sc, bh, 255)
        m = p.result()
        if alpha < 1: m = m.point(lambda v: int(v * alpha))
        frame.paste(color, (0, band_top, W, band_top + bh), m)

    def draw_dashes(self, frame, color, cam_x, cam_y=0.0, alpha=0.45):
        d = ImageDraw.Draw(frame, 'RGBA')
        sc = self.sc; per = 260 * sc; off = cam_x % per
        y = self.dash_y + cam_y
        x = -off
        while x < W:
            d.rectangle((x, y, x + 120 * sc, y + 9 * sc), fill=tuple(color) + (int(255 * alpha),))
            x += per

    def draw_gaslamps(self, frame, color, cam_x, cam_y=0.0, par=0.85, alpha=1.0):
        sc = self.sc; per = 640 * sc; off = (cam_x * par) % per
        p = mask_pen(W, int(560 * sc)); top = int(self.H0 + 20 * sc - 560 * sc + cam_y * par)
        x = 180 * sc - off
        while x < W + 100 * sc:
            b = 560 * sc
            p.rect(x - 5 * sc, b - 430 * sc, x + 5 * sc, b, 255)
            p.rect(x - 12 * sc, b - 40 * sc, x + 12 * sc, b, 255)
            p.poly([(x - 22 * sc, b - 430 * sc), (x + 22 * sc, b - 430 * sc), (x + 16 * sc, b - 495 * sc), (x - 16 * sc, b - 495 * sc)], 255)
            p.poly([(x - 26 * sc, b - 495 * sc), (x + 26 * sc, b - 495 * sc), (x, b - 525 * sc)], 255)
            p.rect(x - 14 * sc, b - 440 * sc, x + 14 * sc, b - 425 * sc, 255)
            x += per
        m = p.result()
        if alpha < 1: m = m.point(lambda v: int(v * alpha))
        frame.paste(color, (0, top, W, top + m.height), m)

    def draw_mist(self, frame, pal, t, cam_x, cam_y=0.0, ys=(-420, -230, -90), alpha=1.0, frozen_t=None):
        tt = t if frozen_t is None else frozen_t
        m = mist_mask(self.sc)
        a = pal['mist_a'] * alpha
        if a <= 0.01: return
        for k, yy in enumerate(ys):
            off = int((tt * (14 + 9 * k) + cam_x * (0.2 + 0.12 * k)) % m.width)
            band = Image.new('L', (W, m.height))
            band.paste(m.crop((off, 0, min(m.width, off + W), m.height)), (0, 0))
            if off + W > m.width: band.paste(m.crop((0, 0, off + W - m.width, m.height)), (m.width - off, 0))
            band = band.point(lambda v: int(v * a))
            frame.paste(pal['mist'], (0, int(self.H0 + yy * self.sc - m.height / 2 + cam_y * 0.3)), band)

    def render(self, frame, pal, t, cam_x, cam_y=0.0, hooks=None, sun=None, clouds=True, alphas=None, frozen=False,
               win_t=None, sy=None):
        """draw sky->sun->layers->ground. hooks: {layer_idx: fn(frame)} called after that layer."""
        hooks = hooks or {}
        if sun is not None:     # (cx, cy, r)
            s = sun_img(pal, sun[2]); comp(frame, s, (sun[0] - s.width / 2, sun[1] - s.height / 2 + cam_y * 0.03))
        if clouds and self.kind == 'A':
            for k, (cx, cy, cw, chh, sp) in enumerate(((180, -760, 300, 34, 9), (760, -640, 420, 40, 6), (520, -900, 240, 28, 12))):
                m = cloud_mask(int(cw * self.sc), int(chh * self.sc), k + 3)
                x = (cx + (0 if frozen else t * sp) - cam_x * 0.03) % (W + cw * self.sc) - cw * self.sc
                frame.paste(pal['cloud'], (int(x), int(self.H0 + cy * self.sc + cam_y * 0.04), int(x) + m.width, int(self.H0 + cy * self.sc + cam_y * 0.04) + m.height),
                            m.point(lambda v: int(v * 0.75)))
        if -1 in hooks: hooks[-1](frame)
        for L in self.layers:
            a = 1.0 if alphas is None else alphas[L.idx]
            s_y = 1.0 if sy is None else sy[L.idx]
            if a <= 0.003: continue
            col = pal['L'][L.idx]
            L.draw(frame, col, cam_x, cam_y, a, t if win_t is None else win_t, win_rgb=pal['win'] if self.kind == 'A' else None, sy=s_y)
            if self.kind == 'B' and hasattr(L, 'winmask') and s_y == 1.0:
                off = L.offset(cam_x)
                wm = L.winmask.crop((int(off), 0, int(off) + W, L.winmask.height))
                wc = mix(pal['L'][L.idx], pal['L'][L.idx - 1], 0.5)
                if a < 1: wm = wm.point(lambda v: int(v * a))
                frame.paste(wc, (0, int(L.y0 + cam_y * L.par)), wm)
            if self.kind == 'B' and L.idx == 4 and s_y == 1.0:
                off = L.offset(cam_x)
                sm = L.stones.crop((int(off), 0, int(off) + W, L.stones.height)).point(lambda v: int(v * 0.36 * a))
                frame.paste(pal['L'][3], (0, int(L.y0 + cam_y * L.par)), sm)
            if self.kind == 'A' and L.idx == 3:
                self.draw_poplars(frame, col, cam_x, cam_y, t, a * (1.0 if s_y == 1.0 else s_y), frozen)
            if self.kind == 'B' and L.idx in (1, 2) and not hooks.get('nomist'):
                self.draw_mist(frame, pal, t, cam_x, cam_y, ys=((-470,) if L.idx == 1 else (-300, -150)), alpha=a,
                               frozen_t=(0 if frozen else None))
            if L.idx in hooks: hooks[L.idx](frame)


@functools.lru_cache(maxsize=4)
def mist_mask(sc):
    rng = np.random.RandomState(5)
    w = int(2400); h = int(150 * sc)
    p = mask_pen(w, h)
    x = 0
    while x < w:
        bw = rng.uniform(260, 620); bh = rng.uniform(0.35, 0.8) * h
        p.rrect(x, h / 2 - bh / 2, min(w, x + bw), h / 2 + bh / 2, bh / 2, 255)
        x += bw + rng.uniform(40, 240)
    return p.result().filter(ImageFilter.GaussianBlur(6 * sc))
