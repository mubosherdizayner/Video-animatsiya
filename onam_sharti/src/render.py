# Frame renderer: scene (+ dissolves) -> paper grain / vignette / imagined-future look -> word subtitle -> ffmpeg.
import sys, os, math, subprocess, time
from multiprocessing import Pool
import numpy as np
import skia
from style import *
import scenes as SC
from timeline import *
from script_data import KEY

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SUB_X = 470          # centre of the pill (safe zone: x <= 930)
SUB_SIZE = 78
SUB_MAXW = 820

def look_at(t):
    """imagined-future amount 0..1 (scenes 7-11), soft dissolve in/out"""
    a = ramp(t, SC_START[7], SC_START[7] + 0.45)
    b = 1 - ramp(t, SC.T_BACK0, SC.T_BACK1)
    return min(a, b)

def palette_u(t):
    return SC.palette_u(t) if hasattr(SC, "palette_u") else 0.0

_SURF = {}
def surface():
    if "s" not in _SURF:
        info = skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
        _SURF["s"] = skia.Surface.MakeRaster(info); _SURF["s2"] = skia.Surface.MakeRaster(info)
    return _SURF["s"], _SURF["s2"]

def draw_scene(surf, k, t):
    cv = surf.getCanvas(); cv.restoreToCount(1); cv.resetMatrix(); cv.clear(skia.Color4f(0, 0, 0, 1))
    n = cv.save()
    SC.SCENE_FN[k](cv, t)
    assert cv.getSaveCount() == n + 1, (k, t, cv.getSaveCount(), n)
    cv.restoreToCount(n)
    return np.asarray(surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3], np.float32) / 255

def compose(i):
    t = i / FPS
    k = scene_at(i)
    s1, s2 = surface()
    arr = draw_scene(s1, k, t)
    for (ka, kb, t0, t1) in getattr(SC, "DISSOLVES", []):
        if kb == k and t0 <= t < t1:
            prev = draw_scene(s2, ka, t)
            a = ease_io((t - t0) / (t1 - t0))
            arr = prev * (1 - a) + arr * a
    lk = look_at(t)
    arr = post(arr, grain=1.0 + 1.1 * lk, vig=1.0 + 0.9 * lk, sat=1.0 - 0.2 * lk)
    return np.clip(arr, 0, 1)

# ------------------------------------------------------------------ subtitles
_TF = {}
def typeface():
    if "tf" not in _TF: _TF["tf"] = skia.Typeface.MakeFromFile(FONT)
    return _TF["tf"]

def current_word(i):
    cur = None
    for w in TIMING:
        if i >= wframe(w): cur = w
    return cur

def sub_layer(word, i, u, y_center):
    """returns (rgba float array of a crop, x0, y0)"""
    if word is None: return None
    txt = word["text"]
    size = SUB_SIZE
    font = skia.Font(typeface(), size)
    tw = font.measureText(txt)
    while tw + 76 > SUB_MAXW: size -= 2; font = skia.Font(typeface(), size); tw = font.measureText(txt)
    d = i - wframe(word)
    sc = 0.9 + 0.1 * ease_out_back(clamp01((d + 1) / 3.0), 2.2)
    pw, ph = tw + 76, size * 1.36
    bw, bh = int(pw * 1.12 + 40), int(ph * 1.12 + 40)
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(bw, bh, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
    cv = surf.getCanvas(); cv.clear(skia.Color4f(0, 0, 0, 0))
    cv.translate(bw / 2, bh / 2); cv.scale(sc, sc)
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-pw / 2, -ph / 2 + 5, pw, ph), ph / 2, ph / 2), paint((0, 0, 0), 0.10, blur=8))
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-pw / 2, -ph / 2, pw, ph), ph / 2, ph / 2), paint(hx("#F4EDDF"), 0.85))
    col = pal(u)["sub_key"] if word["key"] else hx("#1F292C")
    p = skia.Paint(AntiAlias=True); p.setColor4f(skia.Color4f(*col, 1))
    m = font.getMetrics()
    cv.drawString(txt, -tw / 2, -(m.fAscent + m.fDescent) / 2, font, p)
    a = np.asarray(surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType), np.float32) / 255
    return a, int(round(SUB_X - bw / 2)), int(round(y_center - bh / 2))

def overlay(arr, layer):
    if layer is None: return arr
    a, x0, y0 = layer
    h, w = a.shape[:2]
    ys, xs = slice(max(0, y0), min(H, y0 + h)), slice(max(0, x0), min(W, x0 + w))
    sub = a[ys.start - y0:ys.stop - y0, xs.start - x0:xs.stop - x0]
    al = sub[..., 3:4]
    arr[ys, xs] = arr[ys, xs] * (1 - al) + sub[..., :3] * al   # toarray() returns un-premultiplied
    return arr

def render_frame(i):
    t = i / FPS
    arr = compose(i)
    w = current_word(i)
    y = SC.sub_y(i) if hasattr(SC, "sub_y") else 1430
    arr = overlay(arr, sub_layer(w, i, palette_u(t), y))
    return (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)

def _work(i): return i, render_frame(i).tobytes()

def main(out_video, procs=4, frames=None):
    idx = list(range(N_FRAMES)) if frames is None else frames
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS), out_video]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with Pool(procs) as pool:
        for n, (i, b) in enumerate(pool.imap(_work, idx, chunksize=2)):
            p.stdin.write(b)
            if n % 90 == 0: print(f"frame {n}/{len(idx)}  {time.time() - t0:.1f}s", flush=True)
    p.stdin.close(); p.wait()
    print("done", time.time() - t0)

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        from PIL import Image
        outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
        for f in [int(x) for x in sys.argv[3].split(",")]:
            t0 = time.time()
            Image.fromarray(render_frame(f)).save(os.path.join(outdir, f"f{f:04d}.png"))
            print("saved", f, scene_at(f), f"{time.time() - t0:.2f}s")
    else:
        main(sys.argv[1])
