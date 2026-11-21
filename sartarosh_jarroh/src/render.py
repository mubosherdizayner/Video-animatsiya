# Frame renderer: scene art + on-screen headline + one-word subtitles -> ffmpeg (h264, yuv420p, 30 fps)
import sys, os, math, subprocess, time, re
from multiprocessing import Pool
import numpy as np
from gfx import W, H, FPS, clamp01, eo, ramp
import timing as T
import scenes as SC
import text as TX

SAFE_X0, SAFE_X1 = 90, 960
SAFE_CX = (SAFE_X0 + SAFE_X1) / 2
TEXT_MAXW = SAFE_X1 - SAFE_X0 - 20
SUB_Y = 1380
SUB_SIZE = 110
GOLD_WORDS = {"tish", "qon", "bint", "tayoq"}
GOLD_RGB = (0xF2, 0xC1, 0x4E)

# on-screen text: list of lines, each a list of (segment, cue word or None)
HEAD = {
    1: [[("QAYCHI EMAS —", None)], [("OMBUR?!", None)]],
    2: [[("O'RTA ASRLAR,", None)], [("YEVROPA", None)]],
    3: [[("🦷 TISH", None)]],
    4: [[("🦴 SUYAK", "suyak"), (" · 🩹 YARA", "yaralarni")]],
    5: [[("JARROHLIK?", None)], [("SHIFOKORLAR — YO'Q 🙅", None)]],
    6: [[("TANISH GAP-A? 😄", None)]],
    7: [[("SOCH ✂️ | QON 🩸", None)]],
    8: [[("ISBOT —", None)], [("SHU YERDA 👉", None)]],
    9: [[("QIZIL = QON", "Qizil")], [("· OQ = BINT", "Oq")]],
    10: [[("USTUN = TAYOQ", None)]],
    11: [[("SARTAROSHINGIZGA", None)], [("YUBORING 📩", None)]],
    12: [],
}
HEAD_CX = {7: 540}


def _key(s):
    return re.sub(r"[^a-z']", "", s.lower().replace("ʻ", "'").replace("ʼ", "'"))


def build_head():
    out = {}
    for k, lines in HEAD.items():
        n = len(lines)
        base = 104 if n == 1 else 96
        L = []
        for li, segs in enumerate(lines):
            imgs = [TX.text_line(s, base, stroke=8) for s, _ in segs]
            width = sum(im.width for im in imgs) - 8 * (len(imgs) - 1)
            sc = min(1.0, TEXT_MAXW / width)
            if sc < 1.0:
                size = int(base * sc)
                imgs = [TX.text_line(s, size, stroke=8) for s, _ in segs]
                width = sum(im.width for im in imgs) - 8 * (len(imgs) - 1)
            else:
                size = base
            cy = 400 if n == 1 else 400 + (li - 0.5) * 112
            cx = HEAD_CX.get(k, SAFE_CX)
            x = cx - width / 2
            for im, (s, cw) in zip(imgs, segs):
                f0 = T.SC_FRAME[k] if cw is None else T.word(k, cw)["f"]
                L.append(dict(img=im, cx=x + im.width / 2, cy=cy, f0=f0, text=s))
                x += im.width - 8
        out[k] = L
    return out


def build_subs():
    subs = []
    for idx, w in enumerate(T.WORDS):
        txt = w["text"]
        gold = _key(txt).strip("'") in GOLD_WORDS
        col = GOLD_RGB if gold else (255, 255, 255)
        im = TX.text_line(txt, SUB_SIZE, fill=col, stroke=10)
        if im.width > TEXT_MAXW:
            im = TX.text_line(txt, int(SUB_SIZE * TEXT_MAXW / im.width), fill=col, stroke=10)
        im = TX.with_shadow(im)
        nxt = T.WORDS[idx + 1]["f"] if idx + 1 < len(T.WORDS) else T.N_FRAMES
        subs.append(dict(img=im, f0=w["f"], f1=nxt, text=txt, gold=gold))
    return subs


HEADS = None
SUBS = None


def init():
    global HEADS, SUBS
    if HEADS is None:
        HEADS = build_head()
        SUBS = build_subs()


def head_layer(rgb, i, k):
    t = i / FPS
    t_stop, t_unf = T.cue(1, "To'xtang!"), T.cue(1, "Sartaroshlar")
    for seg in HEADS.get(k, []):
        d = i - seg["f0"]
        if d < 0:
            continue
        sc = 0.8 + 0.2 * eo(d / 5.0)
        bob = 3 * math.sin(t * 2.2 + seg["cx"] * 0.01)
        if k == 1 and t_stop <= t < t_unf + 0.3:   # hook text keeps moving during the freeze
            sc *= 1 + 0.03 * math.sin((t - t_stop) * 16)
            bob += 4 * math.sin((t - t_stop) * 11)
        TX.composite(rgb, seg["img"], seg["cx"], seg["cy"] + bob, sc)


def current_sub(i):
    cur = None
    for s in SUBS:
        if s["f0"] <= i < s["f1"]:
            cur = s
    return cur


def sub_layer(rgb, i):
    s = current_sub(i)
    if s is None:
        return None
    d = i - s["f0"]
    sc = 0.85 + 0.15 * eo(d / 4.0)
    return TX.composite(rgb, s["img"], SAFE_CX, SUB_Y, sc)


def render_frame(i):
    init()
    k = T.scene_at(i)
    t = i / FPS
    rgb = SC.SCENES[k](i, t).astype(np.float32)
    head_layer(rgb, i, k)
    sub_layer(rgb, i)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def _work(i):
    return i, render_frame(i).tobytes()


def main(out_video, procs=4):
    init()
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-movflags", "+faststart", out_video]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with Pool(procs, initializer=init) as pool:
        for n, (i, b) in enumerate(pool.imap(_work, range(T.N_FRAMES), chunksize=3)):
            p.stdin.write(b)
            if n % 100 == 0:
                print(f"frame {n}/{T.N_FRAMES}  {time.time() - t0:.0f}s", flush=True)
    p.stdin.close()
    p.wait()
    print(f"video done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    if sys.argv[1] == "stills":
        from PIL import Image
        outdir = sys.argv[2]
        os.makedirs(outdir, exist_ok=True)
        frames = [int(x) for x in sys.argv[3].split(",")]
        for f in frames:
            Image.fromarray(render_frame(f)).save(os.path.join(outdir, f"f{f:04d}.png"))
            print("saved", f, "scene", T.scene_at(f), flush=True)
    else:
        main(sys.argv[1])
