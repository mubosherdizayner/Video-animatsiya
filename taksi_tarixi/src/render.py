# Frame renderer: scene -> grain/vignette -> on-screen text -> one-word subtitles -> ffmpeg (h264, yuv420p)
import sys, os, math, subprocess, time
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFilter
from gfx import W, H, FPS, Pen, hx, mix, clamp01, ease_back, ease_out, ramp, smooth, ACCENT, CREAM, INK, finish, with_alpha, comp
import scenes as SC
import props as P
from script_data import KEYWORDS

C_ = CREAM; A_C = ACCENT
OST = {
    1: [[("TAKSI ", C_), ("=", A_C), (" mashina?", C_)]],
    3: [[("«Qancha boʻladi?»", C_)]],
    5: [[("Narx ", C_), ("=", A_C), (" kelishuv", C_)]],
    6: [[("Bitta quti", C_)]],
    7: [[("1891", C_)]],
    8: [[("Vilgelm Brun · taksometr", C_)]],
    9: [[("masofa · vaqt", C_)]],
    10: [[("=", A_C), (" narx", C_)]],
    11: [[("Taxe ", C_), ("=", A_C), (" toʻlov", C_)], [("metron ", C_), ("=", A_C), (" oʻlchov", C_)]],
    12: [[("TAXImeter ", C_), ("→", A_C), (" TAXI", C_)]],
    13: [[("{plane}", A_C), (" Doʻstingizga yuboring", C_)]],
    14: [[("A yoki B?", C_)]],
    15: [[("Izohda yozing ", C_), ("{hand}", A_C)]],
}
OST_Y = 500          # 26 % of height
OST_SIZE = {7: 150}
SUB_Y = 1306         # 68 % of height
SUB_SIZE = 84


def icon(name, size, col):
    s = size / 100
    w, h = int(120 * s), int(120 * s)
    p = Pen(w, h, s, w / 2, h / 2, ss=3)
    c = tuple(col) + (255,)
    if name == 'plane':
        p.poly([(-50, 4), (52, -30), (-26, 36)], c)
        p.poly([(-50, 4), (52, -30), (-14, -2)], tuple(mix(col, INK, 0.25)) + (255,))
        p.poly([(-14, -2), (52, -30), (-4, 30)], tuple(mix(col, CREAM, 0.2)) + (255,))
    else:   # pointing-down hand (back of the hand, index finger down, knuckles folded, thumb on the side)
        p.rrect(-30, -40, 28, 14, 14, c)
        p.capsule((-15, 6), (-15, 58), 21, 18, c)
        for k in range(3):
            p.circle(1 + k * 11, 15, 8.5, c)
        p.capsule((-28, -18), (-40, 6), 15, 12, c)
        p.rrect(-34, -58, 32, -42, 5, tuple(mix(col, INK, 0.3)) + (255,))
    return p.result()


def runs_img(runs, size):
    fnt = P.font(P.FONT_XB, size)
    d0 = ImageDraw.Draw(Image.new('L', (1, 1)))
    asc, desc = fnt.getmetrics()
    widths = []
    for txt, col in runs:
        widths.append(size * 1.1 if txt.startswith('{') else d0.textlength(txt, font=fnt))
    pad = int(size * 0.4)
    w = int(sum(widths)) + 2 * pad; h = asc + desc + 2 * pad
    txt_l = Image.new('RGBA', (w, h), (0, 0, 0, 0)); sh = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(txt_l); ds = ImageDraw.Draw(sh)
    x = pad; boxes = []
    for (txt, col), tw in zip(runs, widths):
        if txt.startswith('{'):
            ic = icon(txt.strip('{}'), size * 0.95, col)
            iy = int(pad + asc * 0.55 - ic.height / 2)
            txt_l.alpha_composite(ic, (int(x + (tw - ic.width) / 2), iy))
            sh.paste(255, (int(x + (tw - ic.width) / 2), iy + int(size * 0.05)), ic.getchannel('A'))
        else:
            d.text((x, pad), txt, font=fnt, fill=tuple(col) + (255,))
            ds.text((x, pad + size * 0.05), txt, font=fnt, fill=255)
        boxes.append((x, x + tw)); x += tw
    k = int(size * 0.07) | 1
    sh = sh.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.GaussianBlur(size * 0.13))
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.paste(tuple(INK) + (255,), (0, 0), sh.point(lambda v: int(min(255, v * 1.25) * 0.4)))
    out.alpha_composite(txt_l)
    return out, boxes, pad + asc * 0.62


_CACHE = {}
def ost_lines(k):
    if k not in _CACHE:
        lines = []
        for runs in OST[k]:
            size = OST_SIZE.get(k, 92 if len(OST[k]) == 1 else 84)
            im, boxes, ym = runs_img(runs, size)
            while im.width > 1010:
                size -= 4; im, boxes, ym = runs_img(runs, size)
            lines.append((im, boxes, ym))
        _CACHE[k] = lines
    return _CACHE[k]


def place_lines(frame, lines, scale, alpha=1.0, y=OST_Y):
    n = len(lines); step = 108
    for j, (im, boxes, ym) in enumerate(lines):
        im2 = im
        if abs(scale - 1) > 0.003: im2 = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
        if alpha < 1: im2 = with_alpha(im2, alpha)
        cy = y + (j - (n - 1) / 2) * step
        comp(frame, im2, (W / 2 - im2.width / 2, cy - im2.height / 2))


def ost_layer(frame, i, k, t):
    t0 = SC.SC_START[k]
    if k == 2:
        ts = SC.wt(2, 'mashinaning')
        L1 = ost_lines(1)
        if t < ts + 0.45:
            im, boxes, ym = L1[0]
            img = im.copy()
            if t >= ts:      # accent strike line through "mashina"
                d = ImageDraw.Draw(img)
                fnt = P.font(P.FONT_XB, 92)
                x0 = boxes[2][0] + ImageDraw.Draw(Image.new('L', (1, 1))).textlength(" ", font=fnt)
                x1 = x0 + ImageDraw.Draw(Image.new('L', (1, 1))).textlength("mashina", font=fnt)
                u = ease_out(ramp(t, ts - 1 / FPS, ts + 0.17))
                yy = ym + 2
                d.rounded_rectangle((x0 - 6, yy - 7, x0 - 6 + (x1 - x0 + 12) * u, yy + 7), radius=7, fill=tuple(ACCENT) + (255,))
            a = 1 - clamp01((t - (ts + 0.35)) / 0.1)
            place_lines(frame, [(img, boxes, ym)], 1.0, a)
        if t >= ts + 0.4:
            if 'q2' not in _CACHE: _CACHE['q2'] = [runs_img([("TAKSI ", C_), ("=", A_C), (" ?", C_)], 92)]
            sc = 0.6 + 0.4 * ease_back(ramp(t, ts + 0.4, ts + 0.55), 2.2)
            place_lines(frame, _CACHE['q2'], sc)
        return
    if k not in OST: return
    if k == 1: sc = 0.88 + 0.12 * ease_back(ramp(t, -0.05, 0.12), 2.2)
    else: sc = 0.6 + 0.4 * ease_back(ramp(t, SC.SC_FR[k] / FPS, SC.SC_FR[k] / FPS + 0.15), 2.2)
    lines = ost_lines(k)
    if k == 15:   # the pointing hand bounces
        im, boxes, ym = lines[0]
        place_lines(frame, [(im, boxes, ym)], sc)
        return
    place_lines(frame, lines, sc)


# ------------------------------------------------------------- subtitles: one word at a time
def kw(text):
    return SC.nrm(text) in KEYWORDS


def disp(text):
    return text.rstrip(',.:;')


_SUB = {}
def sub_img(text, key):
    if (text, key) not in _SUB:
        fnt = P.font(P.FONT_XB, SUB_SIZE)
        d0 = ImageDraw.Draw(Image.new('L', (1, 1)))
        bb = d0.textbbox((0, 0), text, font=fnt, anchor='ls')
        asc, desc = fnt.getmetrics()
        tw = d0.textlength(text, font=fnt)
        padx, pady = 42, 22
        w = int(tw + 2 * padx); h = int(asc * 0.78 + desc * 0.55 + 2 * pady + 6)
        S = 3
        pill = Image.new('L', (w * S, h * S), 0)
        ImageDraw.Draw(pill).rounded_rectangle((0, 0, w * S - 1, h * S - 1), radius=h * S / 2, fill=255)
        pill = pill.resize((w, h), Image.BOX)
        pad = 24
        out = Image.new('RGBA', (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        shadow = Image.new('L', out.size, 0); shadow.paste(pill, (pad, pad + 6))
        shadow = shadow.filter(ImageFilter.GaussianBlur(9))
        out.paste(tuple(INK) + (255,), (0, 0), shadow.point(lambda v: int(v * 0.22)))
        out.paste(tuple(CREAM) + (255,), (pad, pad), pill.point(lambda v: int(v * 0.85)))
        d = ImageDraw.Draw(out)
        col = ACCENT if key else INK
        base = pad + pady + asc * 0.78 + 1
        d.text((pad + padx, base), text, font=fnt, fill=tuple(col) + (255,), anchor='ls')
        _SUB[(text, key)] = out
    return _SUB[(text, key)]


WFR = [(SC.fr(w['start']), w) for w in SC.WORDS]


def current_word(i):
    cur = None
    for f0, w in WFR:
        if f0 <= i: cur = (f0, w)
        else: break
    return cur


def sub_layer(frame, i):
    cw = current_word(i)
    if not cw: return None
    f0, w = cw
    im = sub_img(disp(w['text']), kw(w['text']))
    sc = 0.93 + 0.07 * ease_out(clamp01((i - f0 + 1) / 3))
    if sc < 0.999: im = im.resize((int(im.width * sc), int(im.height * sc)), Image.BICUBIC)
    x, y = W / 2 - im.width / 2, SUB_Y - im.height / 2
    comp(frame, im, (x, y))
    return (x, y, x + im.width, y + im.height)


def render_frame(i):
    k, f = SC.render_scene(i)
    f = finish(f.convert('RGB')).convert('RGBA')
    t = i / FPS
    ost_layer(f, i, k, t)
    sub_layer(f, i)
    return f.convert('RGB')


def _work(i): return i, render_frame(i).tobytes()


def main(out_video, procs=4, frames=None):
    idx = list(range(SC.N_FRAMES)) if frames is None else frames
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS), out_video]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with Pool(procs) as pool:
        for n, (i, b) in enumerate(pool.imap(_work, idx, chunksize=2)):
            p.stdin.write(b)
            if n % 100 == 0: print(f"frame {n}/{len(idx)}  {time.time() - t0:.1f}s", flush=True)
    p.stdin.close(); p.wait()
    print("done", time.time() - t0)


if __name__ == "__main__":
    if sys.argv[1] == "stills":
        outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
        for x in sys.argv[3].split(","):
            f = int(round(float(x[:-1]) * FPS)) if x.endswith('s') else int(x)
            t0 = time.time()
            render_frame(f).save(os.path.join(outdir, f"f{f:04d}.png"))
            print("saved", f, SC.scene_at(f), f"{time.time() - t0:.2f}s", flush=True)
    else:
        main(sys.argv[1])
