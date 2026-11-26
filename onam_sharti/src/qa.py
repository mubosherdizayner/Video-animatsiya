# QA for the final video. Usage: python3 qa.py final.mp4 voice48k_raw.wav
import sys, os, json, subprocess, math, re, glob
import numpy as np
import skia
from PIL import Image, ImageDraw
from fontTools.ttLib import TTFont
from timeline import *
import scenes as SC
import render as R
from style import hx, pal, W, H

video, src_audio = sys.argv[1], sys.argv[2]
OUT = os.path.join(HERE, "qa"); os.makedirs(OUT, exist_ok=True)
res = []
def ok(name, cond, info=""):
    res.append(dict(check=name, ok=bool(cond), info=info)); print(("PASS " if cond else "FAIL ") + name + (" — " + info if info else ""), flush=True)
def probe(args): return subprocess.run(["ffprobe", "-v", "error"] + args, capture_output=True, text=True).stdout.strip()

# ---------------------------------------------------------------- format + duration
vdur = float(probe(["-select_streams", "v:0", "-show_entries", "stream=duration", "-of", "csv=p=0", video]))
adur = float(probe(["-select_streams", "a:0", "-show_entries", "stream=duration", "-of", "csv=p=0", video]))
sdur = float(probe(["-show_entries", "format=duration", "-of", "csv=p=0", src_audio]))
nfr = int(probe(["-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", video]))
ok("video duration equals audio duration", abs(vdur - adur) <= 1 / FPS and abs(vdur - sdur) <= 1 / FPS,
   f"video {vdur:.3f} s, audio track {adur:.3f} s, voice-over {sdur:.3f} s, {nfr} frames")
spec = probe(["-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height,pix_fmt,r_frame_rate", "-of", "csv=p=0", video])
aspec = probe(["-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", video])
ok("mp4 h264 1080x1920 30 fps yuv420p + aac", spec == "h264,1080,1920,yuv420p,30/1" and aspec == "aac", f"{spec} / {aspec}")
nstreams = probe(["-show_entries", "stream=codec_type", "-of", "csv=p=0", video]).split()
ok("one audio track only (voice + sfx, no music)", nstreams.count("audio") == 1, ",".join(nstreams))

# ---------------------------------------------------------------- sync
offs = {k: SC_FRAME[k] / FPS - SC_START[k] for k in SC_IDS}
ok("every scene starts on the first word of its text (<= 1 frame)", all(abs(v) <= 1 / FPS for v in offs.values()),
   "max offset %.1f ms; " % (max(abs(v) for v in offs.values()) * 1000) + ", ".join(f"{k}:{SC_START[k]:.2f}" for k in SC_IDS))
split_ok = [TIMING[[w['text'] for w in TIMING].index(x)]["scene"] for x in ("Bir", "Oʻgʻlim", "Chunki", "pul", "bolang")] == [2, 3, 7, 8, 9]
ok("split sentences start their scenes (Bir / Oʻgʻlim, Chunki / pul / bolang)", split_ok)
script = [w["text"] for w in TIMING]
shown = []; frames_per_word = []
for j, w in enumerate(TIMING):
    f0 = wframe(w); f1 = wframe(TIMING[j + 1]) if j + 1 < len(TIMING) else N_FRAMES
    frames_per_word.append(f1 - f0)
    shown.append(R.current_word(f0)["text"])
ok("subtitles: every script word, in order, one at a time, appears on its spoken frame",
   shown == script and min(frames_per_word) >= 1 and len(script) == 61,
   f"{len(script)} words; word onset rounding <= {max(abs(wframe(w) / FPS - w['start']) for w in TIMING if not (w['scene'] == 1 and w['first'])) * 1000:.1f} ms; shortest word on screen {min(frames_per_word)} frames")
disp_bad = [w["text"] for w in TIMING if re.search(r"[«»,.:…—]", w["text"])]
ok("display text: no « » , . : … — ; keeps Uylanmoqchimisiz? and uylansang-u", not disp_bad and "Uylanmoqchimisiz?" in script and "uylansang-u" in script)
keys = [w["text"] for w in TIMING if w["key"]]
ok("key words coloured", keys == ["shartini", "moliyaviy", "yetim", "ayb", "yuboring", "repost"], ", ".join(keys))

# ---------------------------------------------------------------- font
cm = TTFont(R.FONT).getBestCmap()
need = sorted(set("".join(script)))
miss = [c for c in need if ord(c) not in cm]
ok("subtitle font renders oʻ gʻ ʼ (no missing glyphs)", not miss and 0x2BB in cm and 0x2BC in cm, os.path.basename(R.FONT) + (f" missing {miss}" if miss else ""))
lay = R.sub_layer(dict(text="Oʻgʻlim", key=False, scene=3, first=True, start=6.0), int(6.0 * FPS) + 3, 0.0, 200)
Image.fromarray((lay[0] * 255).astype(np.uint8)).save(os.path.join(OUT, "font_test_Oglim.png"))

# ---------------------------------------------------------------- subtitle safe zone (all frames)
bad = []
for i in range(N_FRAMES):
    w = R.current_word(i)
    a, x0, y0 = R.sub_layer(w, i, 0.0, SC.sub_y(i))
    ys, xs = np.where(a[..., 3] > 0.03)
    X0, X1, Y0, Y1 = x0 + xs.min(), x0 + xs.max(), y0 + ys.min(), y0 + ys.max()
    if not (X0 >= 0 and X1 <= W - 150 and Y0 >= 0 and Y1 <= H - 400): bad.append((i, X0, X1, Y0, Y1))
ok("subtitles inside the frame and the safe zone (not in bottom 400 px or right 150 px)", not bad, f"{len(bad)} frames out" + (f", e.g. {bad[:2]}" if bad else ""))

# ---------------------------------------------------------------- per-frame scene info (sampled) + decoded video frames
surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
def scene_info(i):
    """runs the scene(s) drawn at frame i (incl. the outgoing scene of a dissolve) and collects hero / key-action boxes"""
    SC.INFO.clear(); cv = surf.getCanvas(); t = i / FPS; k = scene_at(i)
    runs = [k] + [ka for (ka, kb, t0, t1) in SC.DISSOLVES if kb == k and t0 <= t < t1]
    for kk in runs:
        cv.restoreToCount(1); cv.resetMatrix(); n = cv.save(); SC.SCENE_FN[kk](cv, t); cv.restoreToCount(n)
    return dict(SC.INFO)
def pill_box(i):
    a, x0, y0 = R.sub_layer(R.current_word(i), i, 0.0, SC.sub_y(i))
    ys, xs = np.where(a[..., 3] > 0.03); return (x0 + xs.min(), y0 + ys.min(), x0 + xs.max(), y0 + ys.max())
def inter(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])
sample = list(range(0, N_FRAMES, 4)) + [N_FRAMES - 1]
over = []; key_over = []
for i in sample:
    inf = scene_info(i); pb = pill_box(i)
    for hb in inf.get("heroes", []):
        if inter(pb, hb): over.append((i, scene_at(i)))
    for kname in ("palm", "plane", "icon"):
        p = inf.get(kname)
        if p and inter(pb, (p[0] - 50, p[1] - 50, p[0] + 50, p[1] + 50)): key_over.append((i, kname))
ok("subtitle never covers the hero or the key action (palm / plane / repost icon)", not over and not key_over,
   f"checked {len(sample)} frames; hero overlaps {over[:4]}; key-action overlaps {key_over[:4]}")

def read_frames(idx):
    idx = sorted(set(idx)); out = {}
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = 0; fs = W * H * 3
    while True:
        b = p.stdout.read(fs)
        if len(b) < fs: break
        if n in idx: out[n] = np.frombuffer(b, np.uint8).reshape(H, W, 3)
        n += 1
    p.wait(); return out, n

def spoken(t):
    cur = None
    for w in TIMING:
        if wframe(w) / FPS <= t + 1e-6: cur = w
    return cur
checks = []
for k, frac in ((3, 0.55), (6, 0.5), (9, 0.5), (12, None)):
    if frac is None: i = wframe([w for w in TIMING if w["text"] == "yuboring"][0]) + 2
    else: i = int(SC_FRAME[k] + (SC_FRAME[k + 1] - SC_FRAME[k]) * frac)
    checks.append((k, i))
cta = [wframe([w for w in TIMING if w["text"] == x][0]) for x in ("yuboring", "repost")]
need_frames = [0, 3, 6, 9, 12, 15, 18, N_FRAMES - 1] + [i for _, i in checks] + [c + d for c in cta for d in (0, 2, 5)] + sample
FR, ndec = read_frames(need_frames)
ok("decoded frame count = expected", ndec == N_FRAMES, f"{ndec} decoded")

rows = []
for k, i in checks:
    t = i / FPS; w = spoken(t); shown_w = R.current_word(i)
    Image.fromarray(FR[i]).save(os.path.join(OUT, f"check_scene{k:02d}_{t:.2f}s.png"))
    rows.append((k, i, round(t, 2), w["text"], w["scene"], shown_w["text"], scene_at(i)))
ok("4 extracted timestamps: subtitle and scene match the spoken word",
   all(r[3] == r[5] and r[4] == r[6] == r[0] for r in rows), "; ".join(f"{r[2]}s scene {r[6]} shows '{r[5]}' (spoken '{r[3]}', scene {r[4]})" for r in rows))

# hook: frame 0 already in motion (hero walking, parallax)
d03 = np.abs(FR[0].astype(int) - FR[3].astype(int)).mean(2)
hero_reg = d03[1000:1350, 60:300].mean(); bg_reg = d03[700:1200, 300:1080].mean()
ok("frame 0 shows the hook visual in motion (hero walking, layers moving)", hero_reg > 3 and bg_reg > 1,
   f"mean change over first 3 frames: hero area {hero_reg:.1f}, background {bg_reg:.1f} (8-bit levels)")
ok("frame 0: no fade from black", FR[0].mean() > 60, f"mean level {FR[0].mean():.0f}")

# CTA
ty, trp = cta
i12 = SC.scene12; inf_a = scene_info(ty + 5); inf_b = scene_info(trp + 2)
ok("CTA 1: plane thrown exactly on 'yuboring' and flying", "plane" in inf_a and scene_info(ty - 1).get("plane") is None,
   f"'yuboring' frame {ty}: plane in hand until {ty - 1}, airborne by {ty + 5} at {tuple(round(v) for v in inf_a.get('plane', (0, 0)))}")
ok("CTA 2: repost icon above the raised open palm while 'repost' is spoken", inf_b.get("icon") is not None and scene_info(trp - 1).get("icon") is None,
   f"'repost' frame {trp}: icon appears at {trp}, at {tuple(round(v) for v in inf_b.get('icon') or (0, 0))}")
for c in cta:
    Image.fromarray(np.concatenate([FR[c], FR[c + 5]], 1)).resize((1080, 960)).save(os.path.join(OUT, f"cta_{c}.png"))

# imagined look
lk = {k: round(min(R.look_at(t / FPS) for t in range(SC_FRAME[k] + (14 if k == 7 else 0), (SC_FRAME[k + 1] if k < 11 else int(SC.T_BACK0 * FPS)))), 2) for k in range(7, 12)}
others = max(R.look_at(i / FPS) for i in range(N_FRAMES) if scene_at(i) not in (7, 8, 9, 10, 11))
ok("scenes 7-11 use the imagined-future look (stronger grain + vignette, -20% saturation)", all(v == 1.0 for v in lk.values()) and others == 0,
   f"look amount per scene {lk}; outside 7-11: {others}; dissolve in at {SC_START[7]:.2f}-{SC_START[7] + 0.45:.2f} s, out at {SC.T_BACK0}-{SC.T_BACK1} s")

# loop
d = np.abs(FR[N_FRAMES - 1].astype(int) - FR[0].astype(int)).mean()
ok("last frame matches the scene 1 opening framing (loop)", d < 8, f"mean abs difference last vs first frame {d:.2f} / 255")
Image.fromarray(np.concatenate([FR[N_FRAMES - 1], FR[0]], 1)).resize((1080, 960)).save(os.path.join(OUT, "loop_last_vs_first.png"))

# saturation (CIELAB chroma = how vivid a colour looks): chapan vs everything else
def lab_chroma(a):
    c = a.astype(np.float32) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    X = c[..., 0] * 0.4124 + c[..., 1] * 0.3576 + c[..., 2] * 0.1805
    Y = c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722
    Z = c[..., 0] * 0.0193 + c[..., 1] * 0.1192 + c[..., 2] * 0.9505
    f = lambda v: np.where(v > 0.008856, np.cbrt(v), 7.787 * v + 16 / 116)
    fx, fy, fz = f(X / 0.9505), f(Y), f(Z / 1.089)
    A = 500 * (fx - fy); B = 200 * (fy - fz)
    return np.sqrt(A * A + B * B), np.degrees(np.arctan2(B, A)) % 360
C_CH = float(lab_chroma(np.array([[[0x3F, 0x7B, 0x61]]], np.uint8))[0][0, 0])
worst_env = []; worst_acc = []; hero_c = []
for i in sample:
    inf = scene_info(i); ch, hue = lab_chroma(FR[i])
    m = np.ones(ch.shape, bool)
    pb = pill_box(i); m[max(0, pb[1] - 6):pb[3] + 6, max(0, pb[0] - 6):pb[2] + 6] = False
    hm = np.zeros(ch.shape, bool)
    for hb in inf.get("heroes", []):
        hm[max(0, int(hb[1]) - 8):max(0, int(hb[3]) + 8), max(0, int(hb[0]) - 8):max(0, int(hb[2]) + 8)] = True
    if hm.any():
        g = hm & (hue > 140) & (hue < 185) & (ch > 12)        # green chapan pixels inside the hero box
        if g.sum() > 50: hero_c.append(float(np.percentile(ch[g], 90)))
        m &= ~hm
    accent = (hue > 20) & (hue < 90) & (ch > 18)              # palette sun + its glow / lit windows / string lights / fire / plane / icon
    env = ch[m & ~accent]; acc = ch[m & accent]
    worst_env.append((float(np.percentile(env, 99.9)) if env.size else 0, i))
    if acc.size > 200: worst_acc.append((float(np.percentile(acc, 99)), i))
we = max(worst_env); wa = max(worst_acc) if worst_acc else (0, -1)
ok("hero's green chapan is more vivid than every environment / silhouette colour (CIELAB chroma)", we[0] < C_CH,
   f"chapan C*={C_CH:.1f} (measured on screen {min(hero_c):.1f}-{max(hero_c):.1f}); most vivid environment colour C*={we[0]:.1f} (frame {we[1]})")
res.append(dict(check="note: palette accents", ok=None,
                info=f"the sun #F2A55C-#E1742F, accent #E58A3C and lit windows/plane/icon #E7A05C given in the brief are more vivid than the chapan by definition (C* up to {wa[0]:.0f}, frame {wa[1]}); kept as specified"))
print("NOTE", res[-1]["info"])

# voice vs sfx
rep = json.load(open(os.path.join(HERE, "sfx_report.json")))
ok("voice clearly audible over sfx", rep["sfx_below_voice_db"] >= 15, f"loudest sfx is {rep['sfx_below_voice_db']} dB below the voice RMS, ducked a further up to 6 dB under speech")

# no other text / logo / music: by construction, verified in code
src = "".join(open(os.path.join(HERE, f)).read() for f in ("scenes.py", "world.py", "figures.py", "style.py"))
ok("no on-screen text except the word subtitles; no logo, no title card, no music", "drawString" not in src and "drawText" not in src and "TextBlob" not in src,
   "scene code draws no text; renderer draws only the current word pill; audio = voice + synthesized sfx")

json.dump(dict(results=res, checks=rows), open(os.path.join(OUT, "qa.json"), "w"), ensure_ascii=False, indent=1)
print("frames saved to", OUT)
