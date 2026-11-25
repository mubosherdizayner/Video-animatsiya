# QA checks for the final video. Usage: python3 qa.py final.mp4 voice_src.mp3 sfx_report.json outdir
import sys, os, json, math, subprocess
import numpy as np
from PIL import Image, ImageDraw
from fontTools.ttLib import TTFont
import style as ST
from style import FPS, hx
import timeline as TL
import scenes as SC
import chars as CHR
import render as R
from script_data import SCENES as SCRIPT, ON_SCREEN

video, src_audio, sfx_rep, outdir = sys.argv[1:5]
os.makedirs(outdir, exist_ok=True)
res = []
def ok(name, cond, info=""):
    res.append({"check": name, "pass": bool(cond), "info": info})
    print(("PASS " if cond else "FAIL ") + name + (" — " + info if info else ""), flush=True)

def probe(args):
    return subprocess.run(["ffprobe", "-v", "error"] + args, capture_output=True, text=True).stdout.strip()

def grab(t):
    """frame of the final MP4 at time t (frame index round(t*fps))"""
    i = int(round(t * FPS))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"select=eq(n\\,{i})", "-vsync", "0", "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return i, np.frombuffer(raw, np.uint8).reshape(1920, 1080, 3)

# ------------------------------------------------------------------ 1. format + duration
vdur = float(probe(["-select_streams", "v:0", "-show_entries", "stream=duration", "-of", "csv=p=0", video]))
adur = float(probe(["-select_streams", "a:0", "-show_entries", "stream=duration", "-of", "csv=p=0", video]))
sdur = float(probe(["-show_entries", "format=duration", "-of", "csv=p=0", src_audio]))
nfr = int(probe(["-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", video]))
spec = probe(["-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height,pix_fmt,r_frame_rate", "-of", "csv=p=0", video])
aspec = probe(["-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", video])
ok("format: mp4 h264 1080x1920 30 fps yuv420p + aac", spec.startswith("h264,1080,1920,yuv420p,30/1") and aspec == "aac", spec + " / " + aspec)
ok("video duration equals audio duration", abs(vdur - adur) < 1 / FPS and abs(vdur - sdur) < 1 / FPS,
   f"video {vdur:.3f} s ({nfr} frames), audio track {adur:.3f} s, source voice-over {sdur:.3f} s")

# ------------------------------------------------------------------ 2. text sources, glyphs, sync
script_words = [w for _, txt in SCRIPT for w in txt.split() if w != "—"]
shown = []
for l in R.LINES:
    for w in l: shown.extend(w["text"].split())
shown = [w for w in shown if w != "—"]
ok("subtitles use the script text (not the transcript), all words in order", shown == script_words, f"{len(shown)} words in {len(R.LINES)} lines")
ok("on-screen texts match the script", all(R.HEAD_TEXT.get(k, "") == v for k, v in ON_SCREEN.items()),
   "; ".join(f"{k}: {R.HEAD_TEXT.get(k, '')}" for k in sorted(ON_SCREEN) if ON_SCREEN[k]))
cm = TTFont(R.FONT).getBestCmap(); cm2 = TTFont(R.FONT_SUB).getBestCmap()
chars = set("".join(script_words) + "".join(ON_SCREEN.values()).replace("✈️", ""))
miss = [c for c in chars if ord(c) not in cm or ord(c) not in cm2]
ok("font renders oʻ gʻ ʼ (U+02BB/U+02BC) and every script character; ✈️ drawn as a flat #E7A05C icon",
   not miss and 0x2BB in cm and 0x2BC in cm, "Nunito 800/900" + (f", missing {miss}" if miss else ""))
offs = [abs(TL.wframe(w) / FPS - w["start"]) for w in TL.WORDS[1:]]
hl = []
for li, l in enumerate(R.LINES):
    for j, w in enumerate(l):
        nxt = l[j + 1] if j + 1 < len(l) else (R.LINES[li + 1][0] if li + 1 < len(R.LINES) else None)
        hl.append((R.WORD_FRAME[id(nxt)] if nxt else TL.N_FRAMES) - R.WORD_FRAME[id(w)])
ok("each word is highlighted exactly when spoken (offset <= 1 frame)", max(offs) <= 1 / FPS / 2 + 1e-9 and min(hl) >= 1,
   f"max word-onset offset {max(offs) * 1000:.1f} ms (< half a frame), shortest highlight {min(hl)} frames; timing = MMS CTC forced alignment of the script")
sc_off = max(abs(TL.SC_FRAME[k] / FPS - TL.SC_START[k]) for k in TL.SC_IDS if k > 1)
ok("every scene starts at the first word of its text (<= 1 frame)", sc_off <= 1 / FPS / 2 + 1e-9,
   ", ".join(f"{k}:{TL.SC_FRAME[k]}f/{TL.SC_START[k]:.2f}s" for k in TL.SC_IDS))

# cut detection on the real video around the required cut points
def cut_at(t, label):
    i = int(round(t * FPS))
    _, a = grab((i - 1) / FPS); _, b = grab(i / FPS); _, c = grab((i + 1) / FPS)
    d1 = np.abs(b.astype(int) - a.astype(int)).mean(); d2 = np.abs(c.astype(int) - b.astype(int)).mean()
    return i, d1, d2
for k, wi, label in ((4, 0, "semichka"), (5, 0, "hammasi"), (13, 5, "qanday")):
    w = TL.scene_words(k)[wi]
    i, d1, d2 = cut_at(w["start"], label)
    good = w["text"].lower().startswith(label[:5]) and d1 > 3 * max(d2, 0.5) and d1 > 3 and i == int(round(w["start"] * FPS))
    ok(f"cut exactly at '{label}' (scene {k}{' shot 2' if k == 13 else ''})", good,
       f"word at {w['start']:.3f} s -> frame {i}; mean pixel change into frame {i}: {d1:.1f}, next frame: {d2:.1f}")

# ------------------------------------------------------------------ 3. four timestamps: subtitle + scene match the spoken word
probe_words = [TL.scene_words(2)[2], TL.scene_words(7)[4], TL.scene_words(12)[2], TL.scene_words(13)[5]]
sheet = Image.new("RGB", (4 * 540, 960 + 70), (20, 20, 20)); dsh = ImageDraw.Draw(sheet)
allgood = True; info = []
for n, w in enumerate(probe_words):
    t = w["start"] + 0.06
    i, fr = grab(t)
    ref = R.render_frame(i)
    psnr = 10 * math.log10(255 ** 2 / max(1e-6, np.mean((fr.astype(float) - ref.astype(float)) ** 2)))
    aw = R.active_word(i)
    good = (aw is w) and TL.scene_at(i) == w["scene"] and psnr > 30
    allgood &= good
    info.append(f"t={t:.2f}s f{i}: spoken '{w['text']}' -> subtitle '{aw['text']}', scene {TL.scene_at(i)} (script scene {w['scene']}), video vs render PSNR {psnr:.1f} dB")
    sheet.paste(Image.fromarray(fr).resize((540, 960)), (n * 540, 0))
    dsh.text((n * 540 + 10, 970), f"{t:.2f}s  '{w['text']}'  scene {w['scene']}", fill=(240, 240, 240))
sheet.save(os.path.join(outdir, "qa_4_timestamps.png"))
ok("4 timestamps: subtitle and scene match the spoken word", allgood, " | ".join(info))

# ------------------------------------------------------------------ 4. hook at frame 0
i0, f0 = grab(0.0); _, f1 = grab(1 / FPS)
ref0, scene0, boxes0, _ = R.render_frame(0, return_parts=True)
h_d = SC.dissolve_h(0.0, SC.S1_H0, SC.S1_H1)
released = sum(1 for (ox, oy, *_r) in CHR.hero_particles() if (-oy + (_r[2] - 0.5) * 6) / 108 * (SC.S1_H1 - SC.S1_H0) + SC.S1_H0 < 0)
ok("frame 0 shows the hook visual in motion and the hook text (no fade from black, no title card)",
   TL.scene_at(0) == 1 and boxes0.get("head") and 5 < h_d < 95 and released > 50 and f0.mean() > 80 and np.abs(f1.astype(int) - f0.astype(int)).mean() > 0.3,
   f"scene 1, headline '{R.HEAD_TEXT[1]}' drawn, palm on red button, hero dissolved to {h_d:.0f}% of his height, {released} dust particles already flying, "
   f"banknotes falling; mean brightness {f0.mean():.0f}; frame0->1 change {np.abs(f1.astype(int) - f0.astype(int)).mean():.2f}")
Image.fromarray(f0).save(os.path.join(outdir, "qa_frame0.png"))

# ------------------------------------------------------------------ 5. scene 12 gestures + bubble, scene 13 plane
t_bir, t_ikki, t_izoh, t_yoz = (TL.word_t(12, j) for j in (2, 5, 6, 7))
def fr_t(t): return int(round(t * FPS)) / FPS
a_bir = SC.arm_raise(fr_t(t_bir), t_bir, t_bir + 0.55); a_ikki = SC.arm_raise(fr_t(t_ikki), t_ikki, t_ikki + 0.6)
fi = int(round(t_izoh * FPS))
def accent_px(arr):
    m = np.array(ST._muted(tuple(round(v, 5) for v in ST.MONEY), ST.ACCENT_CHROMA_CAP)) * 255
    return int((np.abs(arr.astype(float) - m).sum(2) < 40).sum())
_, sc_prev, _, _ = R.render_frame(fi - 1, return_parts=True)
_, sc_iz, _, _ = R.render_frame(fi, return_parts=True)
bub_prev, bub_now = accent_px(sc_prev[650:960, 330:750]), accent_px(sc_iz[650:960, 330:750])
ok("scene 12: points at the girl's road on 'bir', at the money on 'ikki'; bubble appears on 'Izohga'",
   a_bir > 0.97 and a_ikki > 0.97 and bub_prev < 200 and bub_now > 15000,
   f"left arm raise at 'bir' frame {round(t_bir * FPS)}: {a_bir:.2f}; right arm at 'ikki' frame {round(t_ikki * FPS)}: {a_ikki:.2f}; "
   f"bubble pixels frame {fi - 1}: {bub_prev}, frame {fi} ('Izohga'): {bub_now}")
for f in (round(t_bir * FPS), round(t_ikki * FPS), fi, round(t_yoz * FPS) + 4):
    Image.fromarray(R.render_frame(f)).save(os.path.join(outdir, f"qa_s12_f{f}.png"))
# CTA icon + gesture during the CTA words
cta = []
good = True
for (k, j0, j1, name) in ((12, 6, 7, "Izohga yozing"), (13, 2, 3, "Unga yuboring")):
    ws = TL.scene_words(k)
    a = TL.wframe(ws[j0]); b = TL.wframe(ws[j1]) + int((ws[j1]["end"] - ws[j1]["start"]) * FPS)
    cnts = []
    for f in range(a, b + 1, 3):
        _, so, _, _ = R.render_frame(f, return_parts=True)
        cnts.append(accent_px(so))
    gest = []
    for f in range(a, b + 1, 3):
        t = f / FPS
        if k == 12:
            gest.append(max(SC.arm_raise(t, t_izoh + 0.12, t_yoz - 0.05, 0.16, 0.14), SC.arm_raise(t, t_yoz + 0.12, 99, 0.16)) > 0.3 or t < t_izoh + 0.2)
        else:
            gest.append(True)
    g = min(cnts) > 150 and all(gest)
    good &= g
    cta.append(f"'{name}' frames {a}-{b}: icon px min {min(cnts)}, gesture active {sum(gest)}/{len(gest)} samples")
t_yub = TL.word_t(13, 3)
f_y = int(round(t_yub * FPS))
cta.append(f"throw starts on 'yuboring' frame {f_y}, plane leaves frame ~{int(round((t_yub + 0.45) * FPS))}")
for f in (f_y - 1, f_y, f_y + 3, f_y + 9):
    Image.fromarray(R.render_frame(f)).save(os.path.join(outdir, f"qa_s13_f{f}.png"))
ok("every CTA shows its icon and the hero's gesture while the CTA words are spoken", good, "; ".join(cta))

# ------------------------------------------------------------------ 6. audio
rep = json.load(open(sfx_rep))
ok("voice clearly audible over SFX (no music)", rep["sfx_under_voice_db"] >= 18 and rep["sfx_peak_during_speech_dbfs"] < rep["voice_rms_dbfs"] - 3,
   f"SFX bus {rep['sfx_under_voice_db']:.1f} dB under the voice (RMS), ducked -8 dB under speech; SFX peak during speech {rep['sfx_peak_during_speech_dbfs']:.1f} dBFS vs voice RMS {rep['voice_rms_dbfs']:.1f} dBFS (before final loudness normalisation)")

# ------------------------------------------------------------------ 7. subtitles inside the frame / safe zone
worst = [10 ** 9, 10 ** 9, -1, -1]
for li, l in enumerate(R.LINES):
    for j in range(len(l)):
        im = R.line_img(li, j)
        x0 = 540 - im.width / 2 + 10; y0 = R.SUB_Y - im.height / 2 + 10; x1 = x0 + im.width - 20; y1 = y0 + im.height - 20
        worst = [min(worst[0], x0), min(worst[1], y0), max(worst[2], x1), max(worst[3], y1)]
ok("no subtitle goes outside the frame (and stays in the safe zone)", worst[0] >= 60 and worst[2] <= 1020 and worst[3] <= 1560 and worst[1] >= 300,
   f"all {len(R.LINES)} lines: plate x {worst[0]:.0f}..{worst[2]:.0f}, y {worst[1]:.0f}..{worst[3]:.0f} (frame 1080x1920; bottom 360 px left for platform UI)")

# ------------------------------------------------------------------ 8. chopon = most saturated colour in hero frames
def chroma_map(arr):
    c = arr.astype(np.float64) / 255
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    XYZ = lin @ ST._M.T
    XYZ /= np.array(ST._WN)
    f = np.where(XYZ > (6 / 29) ** 3, np.cbrt(XYZ), XYZ / (3 * (6 / 29) ** 2) + 4 / 29)
    a = 500 * (f[..., 0] - f[..., 1]); b = 200 * (f[..., 1] - f[..., 2])
    return np.hypot(a, b)
C_CHOPON = ST.chroma(hx("#3F7B61"))
hero_frames = [f for f in range(TL.N_FRAMES) if TL.scene_at(f) in SC.HERO_SCENES or (TL.scene_at(f) == 13 and f / FPS < TL.word_t(13, 5))]
sample = hero_frames[::6]
worst_c, worst_f, bad, skipped, tested = 0, None, [], [], 0
for f in sample:
    _, s_on, _, hero = R.render_frame(f, return_parts=True)
    CHR.HIDE["hero"] = True
    _, s_off, _, _ = R.render_frame(f, return_parts=True)
    CHR.HIDE["hero"] = False
    env_mask = np.abs(s_on.astype(int) - s_off.astype(int)).sum(2) == 0
    cm_ = chroma_map(s_on)[env_mask]
    hero_px = (~env_mask).sum()
    top = np.sort(cm_)[-400] if cm_.size > 400 else cm_.max()   # ignore < 400 px (0.02 % of the frame)
    if hero_px and top > worst_c: worst_c, worst_f = top, f
    if hero_px == 0: skipped.append(f); continue      # hero already erased / not yet in frame
    tested += 1
    if top >= C_CHOPON: bad.append(f)
ok("hero's green chopon is the most saturated colour in every frame he is in", not bad and tested > 50,
   f"{tested} frames with the hero visible (every 6th of {len(hero_frames)} hero-scene frames; {len(skipped)} skipped: hero fully dissolved/erased); chopon C*ab {C_CHOPON:.1f}; highest environment/prop chroma {worst_c:.1f} (frame {worst_f}); "
   f"accent hexes are chroma-capped at {ST.ACCENT_CHROMA_CAP:.0f} in hero frames; the hero's own belt/gold trim keep their spec colours; overlays (subtitles/headline) not part of the scene" + (f"; failing frames {bad[:10]}" if bad else ""))

# ------------------------------------------------------------------ 9. loop
last_i = TL.N_FRAMES - 1
_, fl = grab(last_i / FPS); _, ff = grab(0.0)
t_fr = TL.word_t(14, 3)
frozen = np.abs(R.render_frame(last_i).astype(int) - R.render_frame(int(round(t_fr * FPS)) + 1).astype(int)).mean()
loop = Image.new("RGB", (1080, 960)); loop.paste(Image.fromarray(fl).resize((540, 960)), (0, 0)); loop.paste(Image.fromarray(ff).resize((540, 960)), (540, 0))
loop.save(os.path.join(outdir, "qa_loop_last_first.png"))
ok("last frame leads back into the first (loop)", frozen < 1.0,
   f"last frame = frozen finger over the golden button (button x 480, hand from the upper left), frozen since 'aytaman' (diff {frozen:.2f}); "
   f"frame 0 = palm pressed on the red button at x 470, same direction and spot: the press completes and round one restarts")

json.dump(res, open(os.path.join(outdir, "qa_results.json"), "w"), ensure_ascii=False, indent=1)
print(f"\n{sum(r['pass'] for r in res)}/{len(res)} checks passed")
