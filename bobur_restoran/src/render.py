# Frame renderer: scenes + headline + karaoke subtitles -> ffmpeg (h264 / yuv420p)
import sys, os, math, subprocess, time, json
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageFilter
import scenes as SC
from scenes import *

SUB_SIZE = 84
SUB_Y = 1480
SUB_MAXW = 900

def build_chunks():
    chunks = []
    for k in SC_IDS:
        ws = scene_words(k)
        cur = []
        for w in ws:
            cand = cur + [w]
            txt = " ".join(x["text"] for x in cand)
            wid = text_img(txt, SUB_SIZE, stroke=10, shadow=0).width
            if cur and (len(cand) > 4 or len(txt) > 24 or wid > SUB_MAXW / 1.08):
                chunks.append(cur); cur = [w]
            else:
                cur = cand
        if cur: chunks.append(cur)
    return chunks
CHUNKS = build_chunks()
def wframe(w): return 0 if (w["scene"] == 1 and w["first"]) else word_frame(w)
CH_FRAME = [wframe(c[0]) for c in CHUNKS]

_WCACHE = {}
def word_img(text, active, scale_q):
    key = (text, active, scale_q)
    if key not in _WCACHE:
        size = int(round(SUB_SIZE * scale_q / 100))
        _WCACHE[key] = text_img(text, size, fill=YELLOW if active else WHITE, stroke=max(8, int(10 * scale_q / 100)),
                                stroke_fill=(26, 26, 26), shadow=0)
    return _WCACHE[key]

def subtitle_layer(frame, i):
    if i >= SC.CUT_F: return                     # loop tail: the scene-1 composition, no stale text
    ci = None
    for j, f in enumerate(CH_FRAME):
        if i >= f: ci = j
    if ci is None: return
    ch = CHUNKS[ci]
    cur = None
    for w in ch:
        if i >= wframe(w): cur = w
    imgs = []
    for w in ch:
        if w is cur:
            d = i - wframe(w)
            sc = 1.0 + 0.08 * ease_out_back(clamp01(d / 3.0), 2.0)
            imgs.append(word_img(w["text"], True, int(round(sc * 100))))
        else:
            imgs.append(word_img(w["text"], False, 100))
    gap = 16
    tot = sum(im.width for im in imgs) + gap * (len(imgs) - 1)
    hmax = max(im.height for im in imgs)
    line = Image.new("RGBA", (tot + 60, hmax + 60), (0, 0, 0, 0))
    x = 30
    for im in imgs:
        line.alpha_composite(im, (int(x), int(30 + (hmax - im.height) / 2)))
        x += im.width + gap
    al = line.getchannel("A")
    sh = Image.new("RGBA", line.size, (0, 0, 0, 255)); sh.putalpha(al.point(lambda v: int(v * 0.5)))
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    out = Image.new("RGBA", line.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 7)); out.alpha_composite(line)
    if out.width > 1000:
        s = 1000 / out.width; out = out.resize((int(out.width * s), int(out.height * s)), Image.LANCZOS)
    a = 1.0
    if i >= SC.FLASH_F0: a = 1 - clamp01((i - SC.FLASH_F0 + 1) / (SC.CUT_F - SC.FLASH_F0 + 1))
    if a < 1: out = with_alpha(out, a)
    frame.paste(out, (int(540 - out.width / 2), int(SUB_Y - out.height / 2)), out)

def headline_layer(frame, i, k):
    if k not in A["head"] or i >= SC.CUT_F: return
    lines, size = A["head"][k]
    lf = i - SC_FRAME[k]
    q = clamp01(lf / 10.0)
    s = 0.3 + 0.7 * ease_out_back(q, 2.2)
    al = clamp01(lf / 3.0)
    if i >= SC.FLASH_F0: al *= 1 - clamp01((i - SC.FLASH_F0 + 1) / (SC.CUT_F - SC.FLASH_F0 + 1))
    if al <= 0.01 or s <= 0.02: return
    step = size * 1.08 * s
    n = len(lines)
    for j, im in enumerate(lines):
        im2 = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS) if abs(s - 1) > 0.004 else im
        if al < 1: im2 = with_alpha(im2, al)
        cy = 360 + (j - (n - 1) / 2) * step
        frame.paste(im2, (int(540 - im2.width / 2), int(cy - im2.height / 2)), im2)

def render_frame(i, overlays=True):
    k = scene_at_frame(i)
    lf = i - SC_FRAME[k]
    t = i / FPS
    lt = t - SC_START[k]
    dur = SC_END_FRAME[k] / FPS - SC_START[k]
    SC.FRAME_SPR.clear()
    fr = SCENE_FN[k](i, k, t, lf, max(0.0, lt), dur)
    if fr.mode != "RGB": fr = fr.convert("RGB")
    if overlays:
        headline_layer(fr, i, k)
        subtitle_layer(fr, i)
    return fr

def _work(i):
    SC.MAXDISP.clear()
    b = render_frame(i).tobytes()
    return i, b, dict(SC.MAXDISP)

def main(out_video, procs=4):
    SC.init()
    idx = list(range(N_FRAMES))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS), out_video]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    maxd = {}
    with Pool(procs) as pool:
        for n, (i, b, md) in enumerate(pool.imap(_work, idx, chunksize=2)):
            p.stdin.write(b)
            for kk, v in md.items(): maxd[kk] = max(maxd.get(kk, 0), v)
            if n % 60 == 0: print(f"frame {n}/{len(idx)}  {time.time() - t0:.1f}s", flush=True)
    p.stdin.close(); p.wait()
    json.dump(maxd, open(os.path.join(HERE, "max_display.json"), "w"), indent=1)
    print("done", time.time() - t0)

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        SC.init()
        outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
        for f in [int(x) for x in sys.argv[3].split(",")]:
            render_frame(f).save(os.path.join(outdir, f"f{f:04d}.png"))
            print("saved", f, scene_at_frame(f))
    else:
        main(sys.argv[1])
