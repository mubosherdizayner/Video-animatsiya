"""Render the 9:16 video frames.
Usage: python render.py video OUT.mp4      (silent video, frames piped to ffmpeg)
       python render.py frames F1 F2 ...    (PNG stills into $VIDEO_WORK/stills for checks)
Env: VIDEO_IN (folder with frames/ and voice), VIDEO_WORK (timing.json, mouth states, temp files)."""
import os, sys, math, json, glob, re, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from gfx import *
from mouth import states
from script_data import SENTENCES

IN = os.environ["VIDEO_IN"]; WORK = os.environ["VIDEO_WORK"]
TM = json.load(open(os.path.join(WORK, "timing.json")))
NF = TM["nframes"]; WORDS = TM["words"]; SCN = TM["scenes"]; MOUTH = TM["mouth"]

# ------------------------------------------------------------------ source frames
PATHS = {}
for fp in sorted(glob.glob(os.path.join(IN, "frames", "*.jpg")) + sorted(glob.glob(os.path.join(IN, "frames", "*.png")))):
    m = re.search(r"Frame_(\w+?)(?:_-_Variant_(\d))?_[0-9a-f]+\.(jpg|png)", os.path.basename(fp))
    if m: PATHS.setdefault(m.group(1), {})[m.group(2) or "0"] = fp
BASE_VARIANT = {"02": "1", "03": "2", "04": "1", "05": "1", "06": "1", "07": "1", "08": "1",
                "09a": "1", "09b": "1", "10": "2", "11": "1"}

def to_scene(im):
    im = im.convert("RGB").resize((W, H), Image.LANCZOS)
    return im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=35, threshold=2))

SRC = {}      # source-resolution numpy arrays (for masks)
BASE = {}     # scene-space PIL images: BASE[key] = (closed, open)
os.makedirs(os.path.join(WORK, "states"), exist_ok=True)
for k, b in BASE_VARIANT.items():
    pc, po = [os.path.join(WORK, "states", f"k{k}_{s}.png") for s in ("closed", "open")]
    if not (os.path.exists(pc) and os.path.exists(po)):
        c, o = states(k, b, PATHS[k]); c.save(pc); o.save(po)
    c, o = Image.open(pc).convert("RGB"), Image.open(po).convert("RGB")
    SRC[k] = np.asarray(c if b == "1" else o)
    BASE[k] = (to_scene(c), to_scene(o))
k01 = Image.open(PATHS["01"]["0"]).convert("RGB"); SRC["01"] = np.asarray(k01)
BASE["01"] = (to_scene(k01),) * 2

# ------------------------------------------------------------------ timeline helpers
def sent_words(si): return [w for w in WORDS if w["sent"] == si]
def word(si, i): return sent_words(si)[i]
def fr(t): return int(round(t * FPS))
T = dict(stop1=word(0, 5)["end"], knock=word(1, 0)["start"], yoq3=word(2, 4)["start"],
         quote=[word(3, i)["start"] for i in range(4)], yub=word(3, 6)["start"],
         s5=word(4, 0)["start"], ellik_end=word(4, 3)["end"], layk_end=word(6, 1)["end"],
         soram=word(6, 2)["start"], siz=word(7, 4)["start"], foyd=word(8, 0)["start"],
         kayf=word(8, 2)["start"], izohda=word(9, 0)["start"], onam=word(10, 1)["start"])
F_KAYF = word(8, 2)["f0"]
def scene_of(f):
    for s in SCN:
        if s["f0"] <= f < s["f1"]: return s
    return SCN[-1]
def mouth_state(f): return MOUTH[f] if f < len(MOUTH) else 0

# ------------------------------------------------------------------ camera + warp
GRID = 40
GXs = np.arange(0, W + 1, GRID); GYs = np.arange(0, H + 1, GRID)
GX, GY = np.meshgrid(GXs, GYs)
def clamp_cam(z, cx, cy):
    hx, hy = W / 2 / z, H / 2 / z
    return z, min(max(cx, hx), W - hx), min(max(cy, hy), H - hy)
def cam_focus(z, F):
    return clamp_cam(z, F[0] - (F[0] - W / 2) / z, F[1] - (F[1] - H / 2) / z)
def warp(img, cam, disps, t):
    z, cx, cy = cam
    xs = cx + (GX - W / 2) / z; ys = cy + (GY - H / 2) / z
    if not disps:
        return img.transform((W, H), Image.AFFINE, (1 / z, 0, cx - W / 2 / z, 0, 1 / z, cy - H / 2 / z), Image.BICUBIC)
    dx = np.zeros_like(xs); dy = np.zeros_like(ys)
    for fn in disps:
        a, b = fn(xs, ys, t); dx = dx + a; dy = dy + b
    sx = np.clip(xs - dx, 0, W - 0.01); sy = np.clip(ys - dy, 0, H - 0.01)
    data = []
    for j in range(len(GYs) - 1):
        for i in range(len(GXs) - 1):
            data.append(((int(GXs[i]), int(GYs[j]), int(GXs[i + 1]), int(GYs[j + 1])),
                         (sx[j, i], sy[j, i], sx[j + 1, i], sy[j + 1, i], sx[j + 1, i + 1], sy[j + 1, i + 1], sx[j, i + 1], sy[j, i + 1])))
    return img.transform((W, H), Image.MESH, data, Image.BICUBIC)

def band(v, a, b, fall):
    w = np.ones_like(v)
    w = np.where(v < a, 0.5 + 0.5 * np.cos(np.pi * np.clip((a - v) / fall, 0, 1)), w)
    w = np.where(v > b, 0.5 + 0.5 * np.cos(np.pi * np.clip((v - b) / fall, 0, 1)), w)
    return w
HERO = {"02": (90, 670, 200, None), "03": (150, 560, 225, 1060), "04": (130, 410, 480, 1000),
        "05": (260, 480, 580, 1220), "06": (90, 660, 120, None), "07": (40, 650, 240, None),
        "08": (80, 470, 295, 1180), "09a": (140, 600, 456, None), "09b": (110, 670, 488, None),
        "10": (120, 650, 85, None), "11": (120, 460, 430, 1170)}
def bob(key, amp=3.0, period=1.8):
    x0, x1, y0, y1 = [None if v is None else v * K for v in HERO[key]]
    def fn(xs, ys, t):
        wx = band(xs, x0, x1, 70)
        wy = band(ys, y0, 1e9, 70)
        if y1 is not None: wy = wy * np.clip((y1 - ys) / (y1 - y0), 0, 1) ** 0.8
        return 0.0, amp * math.sin(2 * math.pi * t / period) * wx * wy
    return fn

# ------------------------------------------------------------------ perspective helper
def persp_coeffs(dst, src):
    A, bb = [], []
    for (X, Y), (x, y) in zip(dst, src):
        A.append([X, Y, 1, 0, 0, 0, -X * x, -Y * x]); bb.append(x)
        A.append([0, 0, 0, X, Y, 1, -X * y, -Y * y]); bb.append(y)
    return tuple(np.linalg.solve(np.array(A, float), np.array(bb, float)))

# ------------------------------------------------------------------ scene 1: scrolling feed on k01's phone
Q01 = [sp(p) for p in [(230, 385), (500, 352), (565, 962), (285, 1000)]]       # TL TR BR BL (scene)
RW, RH = 390, 882
RECT = BASE["01"][0].transform((RW, RH), Image.QUAD, tuple(c for p in (Q01[0], Q01[3], Q01[2], Q01[1]) for c in p), Image.BICUBIC)
RECT_A = np.asarray(RECT).astype(np.float32)
C0, C1, ROW0, PER = 52, 830, 165, 578
V0, PW = 1800.0, 1.5
TLOOP = NF / FPS
S_HOOK0 = -V0 * T["stop1"] / (PW + 1)
VMIN = int(S_HOOK0 - V0 * 0.5) - 60; VMAX = C1 + 80
vv = np.arange(VMIN, VMAX)
src_rows = np.where((vv >= C0) & (vv < C1), vv,
           np.where(vv >= C1, ROW0 + np.mod(vv - 743, PER), ROW0 + np.mod(vv + 395 - ROW0, PER)))
TALL = RECT_A[np.clip(src_rows, 0, RH - 1)]
QX0, QY0 = int(min(p[0] for p in Q01)) - 2, int(min(p[1] for p in Q01)) - 2
QX1, QY1 = int(max(p[0] for p in Q01)) + 3, int(max(p[1] for p in Q01)) + 3
COEF01 = persp_coeffs([(x - QX0, y - QY0) for x, y in Q01], [(0, 0), (RW, 0), (RW, RH), (0, RH)])
mrect = Image.new("L", (RW, RH), 0); ImageDraw.Draw(mrect).rectangle([3, C0, RW - 4, C1 - 1], fill=255)
MASK01 = mrect.filter(ImageFilter.GaussianBlur(1.2)).transform((QX1 - QX0, QY1 - QY0), Image.PERSPECTIVE, COEF01, Image.BILINEAR)
def scroll_hook(t):
    if t >= T["stop1"]: return 0.0, 0.0
    r = 1 - t / T["stop1"]
    return -V0 * T["stop1"] / (PW + 1) * r ** (PW + 1), V0 * r ** PW
def scroll_end(t): return S_HOOK0 - V0 * (TLOOP - t), V0
def feed_paste(img, s, v):
    n = 9 if v > 40 else 1
    offs = [s] if n == 1 else s + v / 110.0 * np.linspace(-0.5, 0.5, n)
    ys = np.arange(C0, C1, dtype=np.float32)
    acc = np.zeros((C1 - C0, RW, 3), np.float32)
    for o in offs:
        rows = ys + o - VMIN; i0 = np.floor(rows).astype(int); w1 = (rows - i0)[:, None, None]
        i0 = np.clip(i0, 0, len(TALL) - 2)
        acc += TALL[i0] * (1 - w1) + TALL[i0 + 1] * w1
    rect = RECT_A.copy(); rect[C0:C1] = acc / len(offs)
    rim = Image.fromarray(np.clip(rect + .5, 0, 255).astype(np.uint8))
    wpd = rim.transform((QX1 - QX0, QY1 - QY0), Image.PERSPECTIVE, COEF01, Image.BICUBIC)
    img.paste(wpd, (QX0, QY0), MASK01)
FOC01 = sp((397, 676))

# ------------------------------------------------------------------ region cut-outs (bubble, panels)
def bright_mask(key, bbox, seed, lum=200, sat=48, dil=3):
    a = SRC[key].astype(np.int16); x0, y0, x1, y1 = bbox
    sub = a[y0:y1, x0:x1]; L = sub.mean(2); Sa = sub.max(2) - sub.min(2)
    cond = (L > lum) & (Sa < sat)
    lab, _ = ndi.label(cond); comp = lab == lab[seed[1] - y0, seed[0] - x0]
    comp = ndi.binary_fill_holes(ndi.binary_closing(comp, iterations=2))
    core = np.zeros(a.shape[:2], bool); core[y0:y1, x0:x1] = comp
    return core, ndi.binary_dilation(core, iterations=dil)
def scene_mask(m, blur=1.0):
    im = Image.fromarray((m * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    return im.filter(ImageFilter.GaussianBlur(blur)) if blur else im
def cutout(img, mask_L, box):
    c = img.crop(box).convert("RGBA"); c.putalpha(mask_L.crop(box)); return c
def bbox_of(m, pad=6):
    ys, xs = np.nonzero(np.asarray(m) > 8)
    return (max(0, xs.min() - pad), max(0, ys.min() - pad), min(W, xs.max() + pad), min(H, ys.max() + pad))

# k04 thought bubble (inflates)
_, m = bright_mask("04", (380, 395, 600, 545), (488, 470), lum=205, sat=40)
B04_MASK = scene_mask(m); B04_BOX = bbox_of(B04_MASK)
B04_ANCHOR = sp((488, 462))
# k09 panel halves
PANEL9 = {"09a": dict(bbox=(60, 120, 700, 500), div=380, seeds=((110, 160), (650, 160)),
                      head=(sp((416, 452)), (98 * K, 80 * K)),
                      tags=(sp((226, 0))[0], sp((532, 0))[0], 226)),
          "09b": dict(bbox=(85, 195, 670, 545), div=377, seeds=((130, 228), (630, 228)),
                      head=(sp((299, 510)), (92 * K, 70 * K)),
                      tags=(sp((237.5, 0))[0], sp((517, 0))[0], 322))}
for k, P in PANEL9.items():
    core_all = np.zeros(SRC[k].shape[:2], bool); halves = []
    for hi, seed in enumerate(P["seeds"]):
        core, dil = bright_mask(k, P["bbox"], seed, lum=200, sat=50, dil=4)
        xs = np.arange(SRC[k].shape[1])[None, :]
        side = (xs < P["div"] + 2) if hi == 0 else (xs > P["div"] - 2)
        halves.append(dil & side); core_all |= core
    P["half_masks"] = [scene_mask(h) for h in halves]
    P["half_boxes"] = [bbox_of(m_, 30) for m_ in P["half_masks"]]
    hc, hr = P["head"]
    yy, xx = np.mgrid[0:H, 0:W]
    ell = (((xx - hc[0]) / hr[0]) ** 2 + ((yy - hc[1]) / hr[1]) ** 2) < 1
    core_s = np.asarray(scene_mask(core_all, 0)) > 128
    P["head_mask"] = Image.fromarray(((ell & ~core_s) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1))
    gl = []
    for hm in P["half_masks"]:
        a = np.asarray(hm).astype(np.float32) / 255
        ring = ndi.gaussian_filter(ndi.binary_dilation(a > 0.5, iterations=14).astype(np.float32), 7) * (1 - a)
        g = Image.new("RGBA", (W, H), ACC + (0,)); g.putalpha(Image.fromarray((np.clip(ring * 1.6, 0, 1) * 200).astype(np.uint8)))
        gl.append(g)
    P["glow"] = gl
# k11 right bubble (squashes) + background plate + spoon
core11, m11 = bright_mask("11", (380, 240, 645, 495), (511, 336), lum=215, sat=40, dil=3)
B11_MASK = scene_mask(m11); B11_BOX = bbox_of(B11_MASK)
B11_TOP = sp((511, 249))
_a = SRC["11"].astype(np.float32); _w = (~ndi.binary_dilation(m11, iterations=6)).astype(np.float32)
_num = np.stack([ndi.gaussian_filter(_a[..., c] * _w, 14) for c in range(3)], -1); _den = ndi.gaussian_filter(_w, 14)[..., None] + 1e-4
_plate = np.where(_w[..., None] > 0, _a, _num / _den)
B11_PLATE = to_scene(Image.fromarray(np.clip(_plate, 0, 255).astype(np.uint8)))
_sa = SRC["11"].astype(np.int16)
_sp = np.zeros(_sa.shape[:2], bool)
_r, _g, _b = _sa[..., 0], _sa[..., 1], _sa[..., 2]
_sp[395:470, 405:470] = (((_r - _b) > 45) & (_r > _g) & (_sa.mean(2) < 200))[395:470, 405:470]
SPOON_MASK = scene_mask(ndi.binary_dilation(_sp, iterations=1))

# ------------------------------------------------------------------ texts & icons
APOS = "'’ʻʼ"
def norm(w): return re.sub(r"[^a-z']", "", "".join("'" if c in APOS else c for c in w.lower()))
ACCENT = {norm(x) for x in ["hype", "yomonlayapti", "yordamingiz", "yo'q", "yuboring", "ikki", "yuz", "ellik",
                            "Rahmat!", "layk", "siz", "Izohda", "onam"]}
def sub_text(w): return uz(re.sub(r"^[\"“]+|[\"”,.:;]+$", "", w))
def make_pill(text, color, size=88):
    blk = rich_block([[("t", text, color)]], size)
    if blk.width > 900: return make_pill(text, color, size * 0.92)
    pw, ph = blk.width + 2 * 46, int(size * 1.42)
    c = SS(pw, ph); c.rrect((0, 0, pw, ph), ph / 2, fill=CREAM + (217,))
    im = c.image(); f = font(FONT_XB, size); asc, desc = f.getmetrics()
    im.alpha_composite(blk, (46, int((ph - (asc + desc)) / 2 + size * 0.03)))
    return shadowed(im, radius=10, offset=(0, 5), alpha=55)
SUBS = [make_pill(sub_text(w["text"]), ACC if norm(w["text"]) in ACCENT else DARK) for w in WORDS]
def sub_visible(f):
    cur = None
    for k, w in enumerate(WORDS):
        if w["f0"] <= f: cur = k
    if cur is None: return None
    w = WORDS[cur]; nxt = WORDS[cur + 1] if cur + 1 < len(WORDS) else None
    hide = nxt["f0"] if nxt and nxt["start"] - w["end"] < 0.35 else fr(w["end"] + (0.25 if nxt else 0.1))
    if nxt: hide = min(hide, nxt["f0"])
    return cur if f < hide else None

D_, A_ = DARK, ACC
CARDS = {
    1: (card([[("t", "Yana", D_), ("t", "hype...", A_)], [("t", "yana", D_), ("t", "yomonlash", A_)]], 66), 540, 300),
    2: (card([[("t", "Sizdan", D_), ("t", "bitta", D_), ("t", "iltimos", A_)]], 62), 540, 245),
    3: (card([[("t", "Hype", D_), ("i", "cross", A_), ("t", "Yomonlash", D_), ("i", "cross", A_)]], 62), 540, 240),
    4: (card([[("i", "plane", A_), ("t", "Shunday", D_), ("t", uz("do'stingizga"), A_)]], 60), 540, 300),
    6: (card([[("t", "Rahmat!", A_)]], 56, pad=(28, 20), max_w=300), 172, 300),
    7: (card([[("t", "Layk", A_), ("t", "emas...", D_)]], 62), 540, 285),
    8: (card([[("t", "Keyingi", D_), ("t", "videoni", D_)], [("t", "SIZ", A_), ("t", "tanlaysiz", D_)]], 62), 540, 300),
    10: (card([[("t", "Izohda", A_)], [("t", "yozing", D_), ("i", "down", A_)]], 54, pad=(28, 20), max_w=310), 172, 300),
}
def stamp_text(w_, h_):
    im = Image.new("RGBA", (int(w_), int(h_)), (0, 0, 0, 0))
    f = font(FONT_BL, h_ * 0.56); txt = uz("YO'Q")
    d = ImageDraw.Draw(im); bw = f.getlength(txt)
    if bw > w_ * 0.78: f = font(FONT_BL, h_ * 0.56 * w_ * 0.78 / bw); bw = f.getlength(txt)
    asc, desc = f.getmetrics()
    d.text(((w_ - bw) / 2, (h_ - asc - desc * 0.4) / 2), txt, font=f, fill=(0xC0, 0x3B, 0x30, 235))
    rng = np.random.default_rng(3); a = np.asarray(im.split()[3]).astype(np.float32)
    noise = ndi.gaussian_filter(rng.random(a.shape), 0.8); a *= np.clip(0.55 + noise * 0.7, 0, 1)
    im.putalpha(Image.fromarray(a.astype(np.uint8))); return im
STAMP = dict(L=sp((328, 1085)), T=sp((468, 1032)), B=sp((391, 1122)))
STAMP_IM = stamp_text(math.dist(STAMP["L"], STAMP["T"]), math.dist(STAMP["L"], STAMP["B"]))
CHAIR = dict(TL=sp((488, 684)), TR=sp((711, 675)), BL=sp((484, 776)))
def siz_text():
    w_, h_ = math.dist(CHAIR["TL"], CHAIR["TR"]), math.dist(CHAIR["TL"], CHAIR["BL"])
    im = Image.new("RGBA", (int(w_), int(h_)), (0, 0, 0, 0)); f = font(FONT_BL, h_ * 0.62)
    asc, desc = f.getmetrics(); bw = f.getlength("SIZ"); d = ImageDraw.Draw(im)
    d.text(((w_ - bw) / 2, (h_ - asc - desc * 0.35) / 2), "SIZ", font=f, fill=ACC + (255,), stroke_width=3, stroke_fill=DARK + (255,))
    return im
SIZ_IM = siz_text()
PANEL5 = dict(TL=sp((135, 113)), TR=sp((639, 237)), BL=sp((125, 304)))
P5W, P5H = int(math.dist(PANEL5["TL"], PANEL5["TR"])), int(math.dist(PANEL5["TL"], PANEL5["BL"]))
def counter_im(n, color):
    im = Image.new("RGBA", (P5W, P5H), (0, 0, 0, 0)); f = font(FONT_BL, P5H * 0.62); s = str(n)
    asc, desc = f.getmetrics(); bw = f.getlength(s)
    ImageDraw.Draw(im).text(((P5W - bw) / 2, (P5H - asc - desc * 0.35) / 2), s, font=f, fill=color + (255,))
    return im
def tag_im(letter, label, sel):
    blk = rich_block([[("t", letter + ":", ACC), ("t", label, DARK)]], 40)
    w_, h_ = blk.width + 40, 58; c = SS(w_, h_)
    c.rrect((1.5, 1.5, w_ - 1.5, h_ - 1.5), h_ / 2, fill=WHITE + (255,), outline=(ACC if sel else DARK) + (255,), width=3.5)
    im = c.image(); im.alpha_composite(blk, (20, int((h_ - blk.height) / 2) + 1)); return im
TAGS = {(l, s): tag_im(l, lab, s) for l, lab in (("A", "Foydali"), ("B", "Kayfiyatli")) for s in (0, 1)}
QUOTE_WORDS = [uz("Instagram'da"), "foydali", "narsa", uz("yo'q")]
def quote_layout():
    lines = [[0], [1, 2], [3]]; size = 44
    while True:
        f = font(FONT_XB, size); sw = f.getlength(" ")
        widths = [sum(f.getlength(QUOTE_WORDS[i]) for i in ln) + sw * (len(ln) - 1) for ln in lines]
        if max(widths) <= 236: break
        size -= 1
    lh = size * 1.12; pos = {}
    cx, cy = B04_ANCHOR[0], B04_ANCHOR[1] + 4
    for li, ln in enumerate(lines):
        x = cx - widths[li] / 2; y = cy + (li - 1) * lh
        for i in ln:
            wd = f.getlength(QUOTE_WORDS[i]); pos[i] = (x + wd / 2, y); x += wd + sw
    ims = {i: rich_block([[("t", QUOTE_WORDS[i], DARK)]], size) for i in pos}
    return pos, ims
QPOS, QIMS = quote_layout()
CIRCLES = [(536, 136, 19), (643, 189, 15), (80, 209, 14), (91, 350, 25), (691, 344, 16), (222, 389, 11), (541, 445, 17),
           (648, 504, 24), (158, 428, 18), (252, 448, 16), (486, 488, 20), (197, 553, 17), (110, 585, 24),
           (542, 585, 20), (495, 637, 10), (612, 653, 24)]
def drift_circles(img, t):
    a = np.asarray(img).astype(np.float32); out = a.copy(); A = 7.0
    for i, (x, y, r) in enumerate(CIRCLES):
        X, Y, R = x * K, y * K, r * K
        ox = A * math.sin(2 * math.pi * t / (3.1 + 0.37 * i) + i * 1.7); oy = 0.8 * A * math.cos(2 * math.pi * t / (2.6 + 0.29 * i) + i * 0.9)
        m = R + 4 + 18 + A + 3
        x0, x1 = int(max(0, X - m)), int(min(W, X + m)); y0, y1 = int(max(0, Y - m)), int(min(H, Y + m))
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = np.hypot(xx - X - ox, yy - Y - oy)
        wgt = 1 - np.clip((d - (R + 4)) / 18, 0, 1); wgt = wgt * wgt * (3 - 2 * wgt)
        sy, sx = yy - oy * wgt, xx - ox * wgt
        for c in range(3):
            out[y0:y1, x0:x1, c] = ndi.map_coordinates(a[..., c], [sy, sx], order=1, mode="nearest")
    return Image.fromarray(np.clip(out + .5, 0, 255).astype(np.uint8))

# ------------------------------------------------------------------ scenes
def sc_u(s, t): return clamp01((t - s["start"]) / max(1e-3, s["f1"] / FPS - s["start"]))
def base(key, f): return BASE[key][mouth_state(f)].copy()

def scene1(f, t, s):
    img = base("01", 0); sc, v = scroll_hook(t); feed_paste(img, sc, v)
    z = 1 + 0.035 * e_sine(t / (s["f1"] / FPS))
    return img, cam_focus(z, FOC01), []

KNUCK = sp((195, 725))
def scene2(f, t, s):
    img = base("02", f); tk = T["knock"]; knocks = (tk, tk + 0.2)
    R = 200; c = SS(2 * R, 2 * R, 3); any_ring = False
    for kn in knocks:
        for j in range(3):
            tau = (t - kn - 0.06 * j) / 0.6
            if 0 <= tau < 1:
                r = 18 + 165 * e_out(tau); wd = 2 + 7 * (1 - tau); al = int(235 * (1 - tau) ** 1.3)
                c.ell((R - r, R - r, R + r, R + r), outline=(255, 255, 255, al), width=wd); any_ring = True
        tau = (t - kn) / 0.12
        if 0 <= tau < 1:
            g = 40 * (1 - tau); c.ell((R - g, R - g, R + g, R + g), fill=(255, 255, 255, int(150 * (1 - tau)))); any_ring = True
    if any_ring:
        im = c.image(); img.paste(im, (int(KNUCK[0] - R), int(KNUCK[1] - R)), im)
    z = 1 + 0.04 * e_out((t - tk) / 0.25) + 0.012 * sc_u(s, t)
    for kn in knocks:
        if t >= kn: z += 0.007 * math.exp(-(t - kn) * 22)
    return img, cam_focus(z, sp((390, 210))), [bob("02")]

def scene3(f, t, s):
    img = base("03", f); fy = fr(T["yoq3"])
    if f >= fy:
        sc = 0.8 + 0.2 * e_out((f - fy) / 6); al = clamp01((f - fy + 1) / 2)
        paste_affine(img, STAMP_IM, STAMP["L"], STAMP["T"], STAMP["B"], scale=sc, alpha=al)
    z = 1 + 0.04 * e_sine(sc_u(s, t))
    if t >= T["yoq3"]: z += 0.01 * math.exp(-(t - T["yoq3"]) * 14)
    return img, cam_focus(z, (540, 700)), [bob("03")]

PLANE = icon_plane(100)
HAND04, PHONE04, CTRL04 = sp((398, 703)), sp((514, 703)), sp((452, 610))
def bez(p0, p1, p2, u): return ((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0], (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1])
def scene4(f, t, s):
    img = base("04", f); f0 = s["f0"]
    infl = 1 + 0.3 * e_back((f - f0) / 8, 1.4)
    cut = cutout(img, B04_MASK, B04_BOX)
    ccx, ccy = (B04_BOX[0] + B04_BOX[2]) / 2, (B04_BOX[1] + B04_BOX[3]) / 2
    paste_center(img, cut, B04_ANCHOR[0] + (ccx - B04_ANCHOR[0]) * infl, B04_ANCHOR[1] + (ccy - B04_ANCHOR[1]) * infl, infl)
    for i, ts in enumerate(T["quote"]):
        fi = fr(ts)
        if f >= fi:
            px, py = QPOS[i]
            paste_center(img, QIMS[i], px, py + QIMS[i].height / 2 - 6, 0.8 + 0.2 * e_out((f - fi) / 6), clamp01((f - fi + 1) / 2))
    ty = T["yub"]; tau = (t - ty) / 0.5
    if 0 <= tau <= 1:
        u = e_io(tau)
        for gi, lag in enumerate((0.16, 0.10, 0.05)):
            if tau - lag > 0:
                gx, gy = bez(HAND04, CTRL04, PHONE04, e_io(tau - lag))
                ImageDraw.Draw(img).ellipse([gx - 3 + gi, gy - 3 + gi, gx + 3 - gi, gy + 3 - gi], fill=(255, 255, 255))
        x, y = bez(HAND04, CTRL04, PHONE04, u); x2, y2 = bez(HAND04, CTRL04, PHONE04, min(1, u + 0.02))
        ang = -math.degrees(math.atan2(y2 - y, x2 - x + 1e-6)) + 18
        paste_center(img, PLANE, x, y, (0.8 + 0.2 * e_out(tau * 3)) * (1 - 0.4 * tau), 1 if tau < 0.8 else (1 - tau) / 0.2, ang)
    tp = t - (ty + 0.5)
    if 0 <= tp < 0.35:
        c = SS(120, 120, 3); r = 12 + 45 * e_out(tp / 0.35)
        c.ell((60 - r, 60 - r, 60 + r, 60 + r), outline=ACC + (int(220 * (1 - tp / 0.35)),), width=5)
        im = c.image(); img.paste(im, (int(PHONE04[0] - 60), int(PHONE04[1] - 60)), im)
    def bounce(xs, ys, tt):
        tb = tt - (ty + 0.5)
        if tb < 0 or tb > 0.4: return 0.0, 0.0
        amp = -17 * math.sin(math.pi * tb / 0.2) if tb < 0.2 else -6 * math.sin(math.pi * (tb - 0.2) / 0.15) if tb < 0.35 else 0
        wx = band(xs, 480 * K, 680 * K, 50); wy = band(ys, 545 * K, 1e9, 40) * np.clip((800 * K - ys) / (255 * K), 0, 1)
        return 0.0, amp * wx * wy
    u = e_sine(sc_u(s, t)); z = 1.02 + 0.07 * u
    cam = clamp_cam(z, lerp(540, 680, u), lerp(960, 975, u))
    return img, cam, [bob("04"), bounce]

def scene5(f, t, s):
    img = drift_circles(base("05", f), t)
    t0, te = s["start"], T["ellik_end"]; uu = clamp01((t - t0) / (te - t0)); fe = fr(te)
    n = int(round(250 * (1 - (1 - uu) ** 2.2)))
    if f >= fe:
        paste_affine(img, counter_im(250, ACC), PANEL5["TL"], PANEL5["TR"], PANEL5["BL"], scale=1 + 0.12 * (1 - e_out((f - fe) / 6)))
    else:
        paste_affine(img, counter_im(n, DARK), PANEL5["TL"], PANEL5["TR"], PANEL5["BL"], scale=pop(f, s["f0"]))
    u = e_sine(sc_u(s, t)); z = 1.04 + 0.02 * u
    return img, clamp_cam(z, 540, lerp(H - H / 2 / z, H / 2 / z, u)), [bob("05")]

def scene6(f, t, s):
    img = base("06", f); t0 = s["start"]; PV = sp((380, 1300)); TOP = 130 * K
    def bow(xs, ys, tt):
        tau = tt - t0
        a = e_io(tau / 0.3) if tau < 0.45 else 1 - e_io((tau - 0.45) / 0.3)
        if a <= 0: return 0.0, 0.0
        wv = np.clip((PV[1] - ys) / (PV[1] - TOP), 0, 1); wh = band(xs, 90 * K, 660 * K, 80)
        th = math.radians(1.4) * a * wv
        rx, ry = xs - PV[0], ys - PV[1]
        dx = (rx * np.cos(th) - ry * np.sin(th) - rx); dy = (rx * np.sin(th) + ry * np.cos(th) - ry) + 15 * a * wv ** 1.5
        return dx * wh, dy * wh
    z = 1 + 0.03 * e_sine(sc_u(s, t))
    return img, cam_focus(z, sp((383, 430))), [bob("06"), bow]

HEART_IM = icon_heart(140)
def scene7(f, t, s):
    img = base("07", f); t0 = s["start"]; P0, P1 = sp((640, 520)), sp((300, 700))
    ta = T["layk_end"]; ts = T["soram"]
    u = e_io((t - t0) / max(0.3, ta - t0))
    x, y = lerp(P0[0], P1[0], u), lerp(P0[1], P1[1], u) - 40 * math.sin(math.pi * u)
    y += 5 * math.sin(2 * math.pi * (t - t0) * 1.6); ang = 8 * math.sin(2 * math.pi * (t - t0) * 0.9)
    if t >= ts:
        v = (t - ts) / 0.32; x -= 760 * e_in(v); ang += 25 * v
    if x > -150:
        paste_center(img, HEART_IM, x, y, pop(f, s["f0"]), 1.0, ang)
    z = 1 + 0.03 * e_sine(sc_u(s, t))
    return img, cam_focus(z, sp((370, 480))), [bob("07")]

def scene8(f, t, s):
    img = base("08", f); fs = fr(T["siz"])
    if f >= fs:
        paste_affine(img, SIZ_IM, CHAIR["TL"], CHAIR["TR"], CHAIR["BL"], scale=pop(f, fs), alpha=clamp01((f - fs + 1) / 2))
    z = 1 + 0.05 * e_sine(sc_u(s, t))
    return img, cam_focus(z, sp((597, 730))), [bob("08")]

def scene9(f, t, s):
    key = "09a" if f < F_KAYF else "09b"; sel = 0 if key == "09a" else 1
    img = base(key, f); P = PANEL9[key]; fsw = s["f0"] if sel == 0 else F_KAYF
    xa, xb, ty = P["tags"]; ty *= 1
    for hi, (xx, l) in enumerate(((xa, "A"), (xb, "B"))):
        paste_center(img, TAGS[(l, int(hi == sel))], xx, ty, pop(f, s["f0"]))
    k = e_out((f - fsw) / 6); sc = 1 + 0.05 * k
    box = P["half_boxes"][sel]; cut = cutout(img, P["half_masks"][sel], box)
    if k > 0:
        cut = Image.fromarray(np.dstack([np.clip(np.asarray(cut)[..., :3].astype(np.float32) * (1 + 0.06 * k) + 18 * k, 0, 255).astype(np.uint8),
                                         np.asarray(cut)[..., 3]]))
    orig = img.copy()
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    g = P["glow"][sel].crop(box); g.putalpha(g.split()[3].point(lambda v: int(v * k)))
    paste_center(img, g, cx, cy, sc); paste_center(img, cut, cx, cy, sc)
    img.paste(orig, (0, 0), P["head_mask"])
    z = 1 + 0.03 * e_sine(sc_u(s, t))
    return img, cam_focus(z, (540, 900)), [bob(key)]

COMMENT_IM = icon_comment(116); FTIP = sp((313, 847)); CMT = (FTIP[0] + 112, FTIP[1] + 12)
def scene10(f, t, s):
    img = base("10", f); fi = fr(T["izohda"])
    if f >= fi:
        tt = t - T["izohda"]; sc = pop(f, fi)
        for tp in (0.30, 0.62):
            if 0 <= tt - tp < 0.24: sc *= 1 + 0.13 * math.sin(math.pi * (tt - tp) / 0.24)
        paste_center(img, COMMENT_IM, CMT[0], CMT[1], sc)
    z = 1 + 0.04 * e_sine(sc_u(s, t))
    return img, cam_focus(z, (540, 1700)), [bob("10")]

BULB_IM, SUN_IM = icon_bulb(118), icon_sun(132)
BULB_P, SUN_P = sp((247, 282)), sp((511, 334))
def scene11(f, t, s):
    img = base("11", f); f0 = s["f0"]; sc = pop(f, f0)
    paste_center(img, BULB_IM, BULB_P[0], BULB_P[1], sc)
    tau = t - T["onam"]
    if 0 <= tau < 0.75:
        q = 0.085 * math.exp(-4.5 * tau) * math.sin(2 * math.pi * tau / 0.3)
        layer = img.copy(); paste_center(layer, SUN_IM, SUN_P[0], SUN_P[1], sc)
        cut = cutout(layer, B11_MASK, B11_BOX)
        img.paste(B11_PLATE.crop(B11_BOX), B11_BOX[:2], B11_MASK.crop(B11_BOX))
        sx_, sy_ = 1 + 0.5 * q, 1 - q
        cw, ch = cut.size; cut = cut.resize((max(1, int(cw * sx_)), max(1, int(ch * sy_))), Image.BICUBIC)
        bx = (B11_BOX[0] + B11_BOX[2]) / 2
        img.paste(cut, (int(round(bx - cut.width / 2)), int(round(B11_BOX[1] + (B11_TOP[1] - B11_BOX[1]) * (1 - sy_)))), cut)
        img.paste(BASE["11"][mouth_state(f)], (0, 0), SPOON_MASK)
    else:
        paste_center(img, SUN_IM, SUN_P[0], SUN_P[1], sc)
    te = (NF - 12) / FPS
    u = e_sine(clamp01((t - s["start"]) / max(0.1, te - s["start"])))
    z = 1.06 - 0.06 * u
    return img, cam_focus(z, (540, 900)), [bob("11")]

SCENE_FN = {1: scene1, 2: scene2, 3: scene3, 4: scene4, 5: scene5, 6: scene6, 7: scene7, 8: scene8,
            9: scene9, 10: scene10, 11: scene11}

# ------------------------------------------------------------------ loop ending: shrink into k01's phone
QA_ = math.dist(Q01[0], Q01[1]) / math.dist(Q01[0], Q01[3])
def end_transition(o11, f, t):
    p = (f - (NF - 12) + 1) / 12.0; e = e_io(p)
    img = base("01", 0); sc, v = scroll_end(t); feed_paste(img, sc, v)
    R = [(0, 0), (W, 0), (W, H), (0, H)]
    Qp = [(lerp(a[0], b[0], e), lerp(a[1], b[1], e)) for a, b in zip(R, Q01)]
    wf = lerp(1.0, QA_ / (W / H), e)
    srcr = [(W / 2 - W / 2 * wf, 0), (W / 2 + W / 2 * wf, 0), (W / 2 + W / 2 * wf, H), (W / 2 - W / 2 * wf, H)]
    x0, y0 = int(min(q[0] for q in Qp)), int(min(q[1] for q in Qp)); x1, y1 = int(math.ceil(max(q[0] for q in Qp))), int(math.ceil(max(q[1] for q in Qp)))
    co = persp_coeffs([(x - x0, y - y0) for x, y in Qp], srcr)
    wp = o11.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, co, Image.BICUBIC)
    al = 1 - e_io((p - 0.5) / 0.5)
    m = Image.new("L", ((x1 - x0) * 3, (y1 - y0) * 3), 0)
    ImageDraw.Draw(m).polygon([((x - x0) * 3, (y - y0) * 3) for x, y in Qp], fill=int(255 * al))
    m = m.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    if p > 0.02:   # soft shadow under the shrinking frame
        sh = Image.new("L", img.size, 0); ImageDraw.Draw(sh).polygon([(x, y + 10) for x, y in Qp], fill=int(90 * al))
        img.paste((20, 20, 20), (0, 0), sh.filter(ImageFilter.GaussianBlur(14)))
    img.paste(wp, (x0, y0), m)
    return img

# ------------------------------------------------------------------ frame
def render(f):
    t = f / FPS; s = scene_of(f)
    img, cam, disps = SCENE_FN[s["id"]](f, t, s)
    out = warp(img, cam, disps, t)
    if s["id"] in CARDS:
        im, cx, cy = CARDS[s["id"]]
        paste_center(out, im, cx, cy, pop(f, s["f0"]))
    if s["id"] == 11 and f >= NF - 12:
        out = end_transition(out, f, t)
    k = sub_visible(f)
    if k is not None:
        paste_center(out, SUBS[k], 540, 1350, 0.86 + 0.14 * e_out((f - WORDS[k]["f0"]) / 3))
    return out

def _bytes(f): return render(f).tobytes()

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "frames":
        os.makedirs(os.path.join(WORK, "stills"), exist_ok=True)
        for a in sys.argv[2:]:
            f = int(a); render(f).save(os.path.join(WORK, "stills", f"f{f:04d}.png")); print("saved", f)
    else:
        out = sys.argv[2]
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
               "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
               "-profile:v", "high", "-movflags", "+faststart", out]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        import multiprocessing as mp
        with mp.get_context("fork").Pool(4) as pool:
            for i, b in enumerate(pool.imap(_bytes, range(NF), chunksize=4)):
                p.stdin.write(b)
                if i % 60 == 0: print("frame", i, "/", NF, flush=True)
        p.stdin.close(); p.wait(); print("done", out)
