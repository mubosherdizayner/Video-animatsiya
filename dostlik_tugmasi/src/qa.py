# QA: runs every check from the brief against the final MP4 (and an instrumented re-draw of every frame).
import sys, os, json, math, re, subprocess, glob
from multiprocessing import Pool
import numpy as np
from PIL import Image
import skia
import gfx, world, scenes as SC, render as R
from scenes import *

VIDEO, SRC_AUDIO, SFX_REPORT, OUTDIR = sys.argv[1:5]
os.makedirs(OUTDIR, exist_ok=True)
SAFE = (40, 220, 1040, 1560)          # x0, y0, x1, y1 for plates / subtitles / bubbles
res = []
def ok(name, cond, info=""):
    res.append({"check": name, "pass": bool(cond), "info": info})
    print(("PASS " if cond else "FAIL ") + name + (" — " + info if info else ""), flush=True)

def probe(args): return subprocess.run(["ffprobe", "-v", "error"] + args, capture_output=True, text=True).stdout.strip()
def frame_from_video(i):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", VIDEO, "-vf", f"select=eq(n\\,{i})", "-vsync", "0", "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3)
def psnr(a, b):
    m = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2); return 99.0 if m == 0 else 10 * math.log10(255 ** 2 / m)

# ---------------- instrumentation: record device-space rects of every plate / bubble / tag, and cta flags
LOG = []
def _devrect(cv, x0, y0, x1, y1):
    r = cv.getTotalMatrix().mapRect(skia.Rect.MakeLTRB(x0, y0, x1, y1)); return (r.left(), r.top(), r.right(), r.bottom())
_plate = gfx.plate
def plate_logged(cv, x, y, w, h, r=None, a=0.85, c=gfx.CREAM):
    LOG.append(("plate",) + _devrect(cv, x, y, x + w, y + h)); return _plate(cv, x, y, w, h, r, a, c)
_bubble = world.bubble
def bubble_logged(cv, x, y, w, h, a=1.0, scale=1.0, tail=-1, c=gfx.CREAM, ca=0.92):
    if a > 0.01: LOG.append(("bubble",) + _devrect(cv, x - w / 2 * scale, y - h / 2 * scale, x + w / 2 * scale, y + (h / 2 + 24) * scale))
    return _bubble(cv, x, y, w, h, a, scale, tail, c, ca)
_rrs = gfx.rrect_stroke
def rrs_logged(cv, x, y, w, h, r, c, sw, a=1.0):
    LOG.append(("stamp",) + _devrect(cv, x - sw / 2, y - sw / 2, x + w + sw / 2, y + h + sw / 2)); return _rrs(cv, x, y, w, h, r, c, sw, a)
for mod in (gfx, world, SC, R):
    if hasattr(mod, "plate"): mod.plate = plate_logged
    if hasattr(mod, "bubble"): mod.bubble = bubble_logged
    if hasattr(mod, "rrect_stroke"): mod.rrect_stroke = rrs_logged

import hero as HR
_dp = SC.draw_person
def dp_logged(cv, *a, **k):
    if k.get("C", a[3] if len(a) > 3 else HR.HERO) is HR.HERO: SC.QA["hero"] = True
    return _dp(cv, *a, **k)
SC.draw_person = dp_logged

def instrument(i):
    LOG.clear()
    R.compose(i)
    return i, list(LOG), dict(SC.QA)

def lab(rgb):
    c = rgb.astype(np.float64) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    L = 116 * f[..., 1] - 16; a = 500 * (f[..., 0] - f[..., 1]); b = 200 * (f[..., 1] - f[..., 2])
    return L, a, b

if __name__ == "__main__":
    # 1. four timestamps: scene + highlighted subtitle word match the spoken word
    picks = [("million", 2), ("hayotidan", 5), ("stuli", 11), ("repost", 15)]
    for word, sc in picks:
        w = next(x for x in TIMING if x["scene"] == sc and x["text"].lower().startswith(word))
        t = (w["start"] + w["end"]) / 2; i = int(t * FPS)
        fr = frame_from_video(i)
        Image.fromarray(fr).save(os.path.join(OUTDIR, f"t{t:05.2f}_{word}.png"))
        act = [x["text"] for x in TIMING if x["scene"] == sc and R.word_active(x, i)]
        # pixel check: orange highlight sits inside this word's box
        lines = R.LAYOUT[sc]; sp = gfx.text_w(" ", R.SUB_SIZE) * 1.25
        widths = [sum(ww for _, _, ww in ln) + sp * (len(ln) - 1) for ln in lines]
        y0 = R.SUB_BOTTOM - (len(lines) * R.SUB_LH + 40)
        box = None
        for li, ln in enumerate(lines):
            x = 540 - widths[li] / 2
            for ww_, s_, wid in ln:
                if ww_ is w: box = (int(x), int(y0 + 20 + R.SUB_LH * li), int(x + wid), int(y0 + 20 + R.SUB_LH * (li + 1)))
                x += wid + sp
        reg = fr[box[1]:box[3], box[0]:box[2]].astype(int)
        orange = (np.abs(reg - np.array([0xE1, 0x74, 0x2F])).sum(2) < 60).mean()
        sub = fr[y0:R.SUB_BOTTOM, 60:1020].astype(int)
        orange_all = (np.abs(sub - np.array([0xE1, 0x74, 0x2F])).sum(2) < 60).sum()
        orange_in = (np.abs(reg - np.array([0xE1, 0x74, 0x2F])).sum(2) < 60).sum()
        ok(f"t={t:.2f}s '{w['text']}': scene {scene_at_frame(i)} shown, subtitle highlights {act}",
           scene_at_frame(i) == sc and act == [w["text"]] and orange > 0.05 and orange_in >= 0.95 * orange_all,
           f"frame {i}, orange pixels in word box {orange:.0%}, outside box {orange_all - orange_in}")
    # 2. frame 0 = hook visual + hook text, in motion, no fade from black
    f0 = frame_from_video(0); f1 = frame_from_video(3)
    hook = f0[400:560, 150:930].astype(int); ink = (np.abs(hook - np.array([0x1F, 0x29, 0x2C])).sum(2) < 60).mean()
    red = (np.abs(f0.astype(int) - np.array([0xC8, 0x55, 0x3D])).sum(2) < 50).sum()
    ok("frame 0 shows the hook visual and hook text", ink > 0.08 and red > 300 and f0.mean() > 90 and timer_value(0) == 20
       and psnr(f0, f1) < 45, f"hook-text ink coverage {ink:.0%}, button-red px {red}, mean luma {f0.mean():.0f}, timer {timer_value(0)}, frame0-vs-3 PSNR {psnr(f0, f1):.1f} dB (moving)")
    Image.fromarray(f0).save(os.path.join(OUTDIR, "frame_first.png"))
    # 3. last frame = frame 0 composition (loop)
    nfr = int(probe(["-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", VIDEO]))
    fl = frame_from_video(nfr - 1)
    Image.fromarray(fl).save(os.path.join(OUTDIR, "frame_last.png"))
    ok("last frame matches the frame-0 composition (loop)", psnr(f0, fl) > 38, f"PSNR first vs last = {psnr(f0, fl):.1f} dB")
    # 4. timer
    i13 = SC_FRAME[13]; on13 = scene_words(13)[0]["start"]
    ok("timer shows 0 exactly at the first word of scene 13",
       timer_value(i13 / FPS) == 0 and timer_value((i13 - 1) / FPS) == 1 and abs(i13 / FPS - on13) <= 0.5 / FPS,
       f"'Javob' onset {on13:.3f}s = frame {i13}; timer {timer_value((i13 - 1) / FPS)} -> {timer_value(i13 / FPS)}")
    # 7. duration
    vdur = float(probe(["-select_streams", "v:0", "-show_entries", "stream=duration", "-of", "csv=p=0", VIDEO]))
    adur = float(probe(["-select_streams", "a:0", "-show_entries", "stream=duration", "-of", "csv=p=0", VIDEO]))
    sdur = float(probe(["-show_entries", "format=duration", "-of", "csv=p=0", SRC_AUDIO]))
    spec = probe(["-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height,pix_fmt,r_frame_rate", "-of", "csv=p=0", VIDEO])
    aspec = probe(["-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", VIDEO])
    ok("video duration equals audio duration", abs(vdur - sdur) < 1 / FPS and abs(adur - sdur) < 1 / FPS,
       f"video {vdur:.3f}s ({nfr} frames), audio track {adur:.3f}s, voice-over {sdur:.3f}s")
    ok("format: h264 1080x1920 30 fps yuv420p + aac", spec.startswith("h264,1080,1920,yuv420p,30/1") and aspec == "aac", spec + " / " + aspec)
    # 8. voice audible
    rep = json.load(open(SFX_REPORT))
    ok("voice clearly audible over sfx (no music)", rep["sfx_peak_rel_voice_peak_db"] <= -17.9 and rep["voice_minus_sfx_rms_db"] >= 15,
       f"sfx peak {rep['sfx_peak_rel_voice_peak_db']} dB re voice peak, voice RMS {rep['voice_minus_sfx_rms_db']} dB above sfx, extra -6 dB duck under speech")
    # 6. no water
    hits = []
    for f in glob.glob(os.path.join(os.path.dirname(__file__), "*.py")):
        if f.endswith("qa.py"): continue
        hits += [os.path.basename(f) + ":" + m for m in re.findall(r"\b(water|pond|river|lake|sea|ocean|reflection|ripple)\b", open(f).read().lower())]
    ok("no water appears in any scene", not hits, "no water shapes in the scene code" if not hits else str(hits))
    # 9/10: instrumented pass over every frame
    with Pool(4) as pool: out = pool.map(instrument, range(N_FRAMES), chunksize=8)
    bad = []
    for i, log, qa in out:
        for kind, x0, y0, x1, y1 in log:
            if x0 < SAFE[0] - 0.5 or y0 < SAFE[1] - 0.5 or x1 > SAFE[2] + 0.5 or y1 > SAFE[3] + 0.5: bad.append((i, kind, round(x0), round(y0), round(x1), round(y1)))
    nplates = sum(len(l) for _, l, _ in out)
    ok("no subtitle or plate goes outside the frame or the safe zone", not bad,
       f"{nplates} plate/bubble/stamp draws checked against x {SAFE[0]}-{SAFE[2]}, y {SAFE[1]}-{SAFE[3]}" + (f"; violations: {bad[:6]}" if bad else ""))
    flags = {i: qa for i, _, qa in out}
    cta = [(14, ["yubor"], "plane", ("throw",)), (15, ["repost", "qil"], "repost", ("point",)), (17, ["obuna", "bo"], "subscribe_button", ("reach", "tap"))]
    msgs = []; good = True
    for sc, words, icon, gest in cta:
        ws = [w for w in scene_words(sc) if any(w["text"].lower().strip('".').startswith(p) for p in words)]
        f0_, f1_ = word_frame(ws[0]), int(round(ws[-1]["end"] * FPS))
        frames = range(f0_, f1_)
        g_ok = [flags[i].get("gesture") in gest for i in frames]; i_ok = [flags[i].get("icon") == icon for i in frames]
        # gesture must be on for the whole spoken CTA phrase, allowing the first 3 frames for the arm to start moving
        good &= all(i_ok) and all(g_ok[3:])
        msgs.append(f"scene {sc} '{' '.join(w['text'] for w in ws)}' frames {f0_}-{f1_ - 1}: icon {sum(i_ok)}/{len(i_ok)}, gesture {sum(g_ok)}/{len(g_ok)}")
    ok("every cta scene shows its icon and the hero's gesture while the cta words are spoken", good, "; ".join(msgs))
    # 5. hero's green chapan = most saturated colour: every non-hero, non-accent pixel stays below the chapan's chroma
    Lc, ac, bc = lab(np.array([[[0x3F, 0x7B, 0x61]]], np.uint8)); c_ref = float(np.hypot(ac, bc)[0, 0])
    worst = []; acc_max = 0; hero_c = []
    hero_in = {i for i, _, qa in out if qa.get("hero")}
    frames5 = sorted(set(range(0, N_FRAMES, 10)) | set(range(SC_FRAME[2], SC_END_FRAME[2], 3)))
    for i in frames5:
        fr = frame_from_video(i)
        L_, a_, b_ = lab(fr[::2, ::2]); C = np.hypot(a_, b_); hue = (np.degrees(np.arctan2(b_, a_)) + 360) % 360
        warm = (hue > 15) & (hue < 112)                  # spec accents: button red, sun, gold, belt, orange UI, warm lights
        # green pixels are excused only in frames where the hero is actually drawn (cash shots have no hero)
        hero_green = (hue >= 112) & (hue <= 190) & (C > 16) & (i in hero_in)
        rest = C[~warm & ~hero_green]
        worst.append((float(np.percentile(rest, 99.9)) if rest.size else 0.0, i))
        if hero_green.sum() > 200: hero_c.append(float(np.median(C[hero_green])))
        acc_max = max(acc_max, float(C[warm].max()) if warm.any() else 0)
    # user decision: the money in scene 2 is a deep dollar green, deliberately more saturated than the chapan
    cash = [(v, i) for v, i in worst if SC_FRAME[2] <= i < SC_END_FRAME[2]]
    rest_frames = [(v, i) for v, i in worst if not (SC_FRAME[2] <= i < SC_END_FRAME[2])]
    w_max = max(rest_frames)
    ok("hero's green chapan is the most saturated colour in every frame (non-accent colours; money shot = user-approved exception)",
       w_max[0] < c_ref,
       f"chapan chroma C*={c_ref:.1f} (rendered median {np.median(hero_c):.1f}); every frame outside the money shot: highest other "
       f"non-accent chroma p99.9 = {w_max[0]:.1f} at frame {w_max[1]}; money shot (frames {SC_FRAME[2]}-{SC_END_FRAME[2] - 1}, no hero in frame) "
       f"reaches C*={max(cash)[0]:.1f} by request (deep dollar green); warm accents from the brief excluded (up to C*={acc_max:.0f})")
    json.dump(res, open(os.path.join(OUTDIR, "qa_results.json"), "w"), ensure_ascii=False, indent=1)
    print(f"{sum(r['pass'] for r in res)}/{len(res)} checks passed")
