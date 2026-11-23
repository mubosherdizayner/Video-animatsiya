# Frame renderer: scene -> vignette -> top plate + timer -> subtitles -> paper grain; loop cross-dissolve at the end.
import sys, os, math, subprocess, time
from multiprocessing import Pool
import numpy as np
import skia
from gfx import *
import scenes as SC
from scenes import *

SUB_SIZE = 60
SUB_LH = 76
SUB_BOTTOM = 1530
SUB_MAXW = 880
TOP_Y, TOP_H = 236, 92
FADE_FR = 15                     # last 0.5 s: dissolve back to frame 0

def layout(k):
    ws = scene_words(k)
    lines, cur, curw = [], [], 0.0
    sp = text_w(" ", SUB_SIZE)
    for w in ws:
        s = uz(w["text"]); ww = text_w(s, SUB_SIZE)
        if cur and curw + sp + ww > SUB_MAXW - 64:
            lines.append(cur); cur, curw = [], 0.0
        cur.append((w, s, ww)); curw += (sp if len(cur) > 1 else 0) + ww
    if cur: lines.append(cur)
    return lines
LAYOUT = {k: layout(k) for k in SC_IDS}

def word_active(w, i):
    f = word_frame(w)
    if i < f: return False
    nxt = [x2 for x2 in TIMING if x2["start"] > w["start"]]
    if nxt and i >= word_frame(nxt[0]): return False
    return i < int(round((w["end"] + 0.10) * FPS))

def subtitles(cv, i, k):
    """one phrase per scene; each word appears on the frame it is spoken; the spoken word is highlighted.
    Lines keep their final positions; the cream plate grows with the revealed words."""
    lines = LAYOUT[k]
    sp = text_w(" ", SUB_SIZE) * 1.25
    widths = [sum(ww for _, _, ww in ln) + sp * (len(ln) - 1) for ln in lines]
    y0 = SUB_BOTTOM - (len(lines) * SUB_LH + 40)
    items = []          # (line, x, w, string, word, frame)
    for li, ln in enumerate(lines):
        x = 540 - widths[li] / 2
        for w, s, ww in ln:
            items.append((li, x, ww, s, w, word_frame(w))); x += ww + sp
    shown = [it for it in items if i >= it[5]]
    if not shown: return
    last_li = max(it[0] for it in shown)
    xl = min(it[1] for it in shown)
    xr = 0.0
    for li, x, ww, s, w, f in shown:
        xr = max(xr, x + ww)
    px0, px1 = xl - 32, xr + 32
    plate(cv, px0, y0, px1 - px0, 40 + SUB_LH * (last_li + 1), 30, 0.85)
    for li, x, ww, s, w, f in shown:
        act = word_active(w, i)
        pop = 1.0 + 0.04 * (1 - ease_out((i - f) / 3.0)) if act else 1.0
        cy = y0 + 20 + SUB_LH * li + SUB_LH / 2
        with xf(cv, x + ww / 2, cy, pop):
            text(cv, s, 0, 0, SUB_SIZE, HILITE if act else INK)

def top_plate(cv, i, a=1.0):
    if a <= 0.01: return
    t = i / FPS
    v = timer_value(t)
    runs = [("BOSSA: ", INK), ("$1 000 000", GOLD), ("  ·  BOSMASA: ", INK), ("SEN", "#3F7B61")]
    size = 38
    tw = sum(text_w(s, size) for s, _ in runs)
    badge_r = 36
    pw = tw + 48 + badge_r * 2 + 26
    x0 = 540 - pw / 2
    with layer_alpha(cv, a):
        plate(cv, x0, TOP_Y, pw, TOP_H, TOP_H / 2, 0.85)
        text_runs(cv, runs, x0 + 30, TOP_Y + TOP_H / 2, size, 1.0, "left")
        bx, by = x0 + pw - badge_r - 12, TOP_Y + TOP_H / 2
        # pop on each step
        steps = timer_steps()
        last = max([s for s in steps if s <= t + 1e-6], default=None)
        k = (t - last) if last is not None else 1.0
        sc = 1.0 + 0.16 * (1 - ease_out(k / 0.25))
        with xf(cv, bx, by, sc):
            circle(cv, 0, 0, badge_r, ACCENT)
            frac = v / 20.0
            pth = skia.Path(); rr = badge_r - 5
            pth.addArc(skia.Rect.MakeLTRB(-rr, -rr, rr, rr), -90, 360 * frac)
            cv.drawPath(pth, paint(CREAM, 0.55, stroke=3.5))
            text(cv, str(v), 0, 0, 34, CREAM)

def top_alpha(i):
    end13 = SC_END_FRAME[13]
    if i < end13 - 9: return 1.0
    if i < end13: return 1.0 - (i - (end13 - 9) + 1) / 9.0
    return 0.0

def compose(i):
    surf = skia.Surface(W, H)
    cv = surf.getCanvas(); cv.clear(skia.ColorWHITE)
    k = scene_at_frame(i)
    t = i / FPS
    lt = t - SC_FRAME[k] / FPS
    dur = (SC_END_FRAME[k] - SC_FRAME[k]) / FPS
    cv.save()
    SC.QA.clear()
    SCENE_FN[k](cv, t, max(0.0, lt), dur)
    cv.restore()
    vignette(cv, 0.30 if k not in (9, 10, 11, 16, 17) else 0.38)
    top_plate(cv, i, top_alpha(i))
    subtitles(cv, i, k)
    grain(cv, 0.5)
    return surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)

_F0 = None
def render_frame(i):
    global _F0
    img = compose(i)
    start = N_FRAMES - FADE_FR
    if i >= start:
        if _F0 is None: _F0 = compose(0)
        b = (i - start + 1) / FADE_FR
        b = smooth(b) if i < N_FRAMES - 1 else 1.0
        img = (img.astype(np.float32) * (1 - b) + _F0.astype(np.float32) * b + 0.5).astype(np.uint8)
    return img

def _work(i):
    return i, render_frame(i)[:, :, :3].tobytes()

def main(out_video, procs=4):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-movflags", "+faststart", out_video]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with Pool(procs) as pool:
        for n, (i, b) in enumerate(pool.imap(_work, range(N_FRAMES), chunksize=3)):
            p.stdin.write(b)
            if n % 60 == 0: print(f"frame {n}/{N_FRAMES}  {time.time() - t0:.1f}s", flush=True)
    p.stdin.close(); p.wait()
    print("done", N_FRAMES, "frames", round(time.time() - t0, 1), "s")

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        from PIL import Image
        outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
        for f in [int(x) for x in sys.argv[3].split(",")]:
            t0 = time.time()
            Image.fromarray(render_frame(f)[:, :, :3].copy()).save(os.path.join(outdir, f"f{f:04d}.png"))
            print("saved", f, "scene", scene_at_frame(f), f"{time.time() - t0:.2f}s")
    else:
        main(sys.argv[1])
