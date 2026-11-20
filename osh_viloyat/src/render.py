# Frame renderer: scene world -> camera -> post -> on-screen text + logo + karaoke subtitles -> ffmpeg (h264)
import sys, os, math, subprocess, time
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageFilter
from lib import *
from props import logo_img
import scenes as SCN
from timeline import WORDS, SC, SF, S, DUR, END_F, IDS, N_FRAMES, scene_at, scene_words, wf, word

# ---------------------------------------------------------------- layout (safe zones for TikTok / Reels / Shorts)
OST_CY = 330          # on-screen text centre (upper third, below the top UI)
OST_MAXW = 900
OST_MAXW_1 = 940     # single-line blocks may run a little wider
SUB_CY = 1452         # subtitle line centre (above the bottom caption/UI area)
SUB_SIZE = 74
SUB_MAXW = 860


# ---------------------------------------------------------------- on-screen text
def wrap(words, f, maxw):
    lines = [[]]
    for w in words:
        cand = lines[-1] + [w]
        if lines[-1] and text_width(" ".join(cand), f) > maxw: lines.append([w])
        else: lines[-1] = cand
    return [" ".join(l) for l in lines]


_OST = {}
def ost_block(k):
    if k in _OST: return _OST[k]
    txt, gold = SC[k]["ost"], SC[k]["gold"]
    # one line if it fits at >= 84 px, otherwise two lines at up to 100 px
    size = None
    for sz in range(100, 77, -2):
        f = get_font(FONT_MAIN, sz)
        if text_width(txt, f) <= OST_MAXW_1: size = sz; lines = [txt]; break
    if size is None:
        size = 100
        while True:
            f = get_font(FONT_MAIN, size)
            lines = wrap(txt.split(), f, OST_MAXW)
            if max(text_width(l, f) for l in lines) <= OST_MAXW and len(lines) <= 2: break
            size -= 4
    imgs = [text_img(l, size, stroke=11, gold_words=tuple(gold)) for l in lines]
    step = size * 1.08
    Wb = max(im.width for im in imgs); Hb = int(step * (len(imgs) - 1) + max(im.height for im in imgs))
    blk = Image.new("RGBA", (Wb, Hb), (0, 0, 0, 0))
    for j, im in enumerate(imgs):
        blk.alpha_composite(im, (int((Wb - im.width) / 2), int(j * step)))
    _OST[k] = blk
    return blk


def ost_start_frame(k):
    if k == 9: return wf(word(9, "onamning"))
    return SF[k]


def ost_layer(frame, i, k):
    f0 = ost_start_frame(k)
    if i < f0: return
    lf = i - f0
    if k == 1: lf += 5                       # hook text already on screen at frame 0
    s = 0.35 + 0.65 * ease_out_back(clamp01(lf / 9.0), 2.4)
    a = clamp01((lf + 1) / 3.0)
    blk = ost_block(k)
    bob = 3 * math.sin(2 * math.pi * (i / 30) / 1.6)
    im = blk if abs(s - 1) < 0.003 else blk.resize((max(1, int(blk.width * s)), max(1, int(blk.height * s))), Image.LANCZOS)
    if a < 1: im = with_alpha(im, a)
    paste(frame, im, 540 - im.width / 2, OST_CY + bob - im.height / 2)


# ---------------------------------------------------------------- logo (scene 14)
def logo_layer(frame, i, k):
    if k != 14: return
    lt = (i - SF[14]) / 30
    q = lt - 0.15
    if q < 0: return
    s = ease_out_back(clamp01(q / 0.45), 1.9) * (1 + 0.015 * math.sin(2 * math.pi * lt / 1.3))
    lg = logo_img(SCN.LOGO_D)
    im = lg.resize((max(1, int(lg.width * s)), max(1, int(lg.height * s))), Image.LANCZOS)
    paste(frame, im, SCN.LOGO_POS[0] - im.width / 2, SCN.LOGO_POS[1] - im.height / 2)


# ---------------------------------------------------------------- karaoke subtitles
def build_chunks():
    f = get_font(FONT_MAIN, SUB_SIZE)
    chunks = []
    for k in IDS:
        cur = []
        for w in scene_words(k):
            cand = cur + [w]
            txt = " ".join(x["text"] for x in cand)
            if cur and (text_width(txt, f) + 30 > SUB_MAXW or len(cand) > 4):
                chunks.append(cur); cur = [w]
            else:
                cur = cand
        if cur: chunks.append(cur)
    return chunks


CHUNKS = build_chunks()
CH_F = [0 if (c[0]["scene"] == 1 and c[0]["first"]) else wf(c[0]) for c in CHUNKS]
_WC = {}
def word_img(text, active, sq):
    key = (text, active, sq)
    if key not in _WC:
        size = int(round(SUB_SIZE * sq / 100))
        _WC[key] = text_img(text, size, fill=YELLOW if active else WHITE, stroke=9, shadow=0)
    return _WC[key]


def current_chunk(i):
    ci = None
    for j, f in enumerate(CH_F):
        if i >= f: ci = j
    return ci


def subtitle_layer(frame, i):
    ci = current_chunk(i)
    if ci is None: return
    ch = CHUNKS[ci]
    cur = None
    for w in ch:
        if i >= (0 if (w["scene"] == 1 and w["first"]) else wf(w)): cur = w
    imgs = []
    for w in ch:
        if w is cur:
            d = i - (0 if (w["scene"] == 1 and w["first"]) else wf(w))
            sq = int(round(100 * (1.0 + 0.07 * ease_out_back(clamp01((d + 1) / 3.0), 2.0))))
            imgs.append(word_img(w["text"], True, sq))
        else:
            imgs.append(word_img(w["text"], False, 100))
    gap = 6
    tot = sum(im.width for im in imgs) + gap * (len(imgs) - 1)
    hmax = max(im.height for im in imgs)
    line = Image.new("RGBA", (tot + 60, hmax + 60), (0, 0, 0, 0))
    x = 30
    base = word_img(ch[0]["text"], False, 100).height
    for im in imgs:
        line.alpha_composite(im, (int(x), int(30 + (hmax - im.height) / 2)))
        x += im.width + gap
    sh = Image.new("RGBA", line.size, (0, 0, 0, 255)); sh.putalpha(line.getchannel("A").point(lambda v: int(v * 0.55)))
    sh = sh.filter(ImageFilter.GaussianBlur(8))
    out = Image.new("RGBA", line.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 6)); out.alpha_composite(line)
    if out.width > W - 40:
        s = (W - 40) / out.width; out = out.resize((int(out.width * s), int(out.height * s)), Image.LANCZOS)
    paste(frame, out, 540 - out.width / 2, SUB_CY - out.height / 2)


# ---------------------------------------------------------------- frame
def render_frame(i):
    k = scene_at(i)
    t = i / 30
    lt = (i - SF[k]) / 30
    world, cam, post = SCN.SCENE_FN[k](t, lt, DUR[k])
    frame = camera(world, **cam).convert("RGBA")
    if post: post(frame)
    logo_layer(frame, i, k)
    ost_layer(frame, i, k)
    subtitle_layer(frame, i)
    return frame.convert("RGB")


def _work(i):
    return i, render_frame(i).tobytes()


def main(out_video, procs=4):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", "30", out_video]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with Pool(procs) as pool:
        for n, (i, b) in enumerate(pool.imap(_work, range(N_FRAMES), chunksize=3)):
            p.stdin.write(b)
            if n % 100 == 0: print(f"frame {n}/{N_FRAMES}  {time.time() - t0:.0f}s", flush=True)
    p.stdin.close(); p.wait()
    print("done", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    if sys.argv[1] == "stills":
        outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
        for f in [int(x) for x in sys.argv[3].split(",")]:
            t0 = time.time()
            render_frame(f).save(os.path.join(outdir, f"f{f:04d}.png"))
            print("saved", f, "scene", scene_at(f), f"{time.time() - t0:.2f}s")
    else:
        main(sys.argv[1])
