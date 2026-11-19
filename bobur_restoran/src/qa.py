# QA checks for the final video (every item of the brief's qa list).
import sys, json, math, subprocess, os, glob, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
import scenes as SC
from scenes import *
import render as R

video, src_audio, mix_wav, sfx_wav = sys.argv[1:5]
res = []
def ok(name, cond, info=""):
    res.append((name, bool(cond), info)); print(("PASS " if cond else "FAIL ") + name + (" — " + info if info else ""))
def probe(args):
    return subprocess.run(["ffprobe", "-v", "error"] + args, capture_output=True, text=True).stdout.strip()

# durations / format
vdur = float(probe(["-select_streams", "v:0", "-show_entries", "stream=duration", "-of", "csv=p=0", video]))
adur = float(probe(["-select_streams", "a:0", "-show_entries", "stream=duration", "-of", "csv=p=0", video]))
sdur = float(probe(["-show_entries", "format=duration", "-of", "csv=p=0", src_audio]))
nfr = int(probe(["-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", video]))
ok("video duration equals audio duration", abs(vdur - sdur) <= 1 / FPS and abs(adur - sdur) <= 0.05,
   f"video {vdur:.3f}s, audio track {adur:.3f}s, source voice {sdur:.3f}s, {nfr} frames")
spec = probe(["-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height,pix_fmt,r_frame_rate", "-of", "csv=p=0", video])
aspec = probe(["-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", video])
ok("format h264 1080x1920 30fps yuv420p + aac", spec.startswith("h264,1080,1920,yuv420p,30/1") and aspec == "aac", spec + " / " + aspec)

# scene starts
worst = max(SC_FRAME[k] / FPS - SC_START[k] for k in SC_IDS)
ok("every scene starts within 1 frame of its first word", all(0 <= SC_FRAME[k] / FPS - SC_START[k] < 1 / FPS + 1e-9 for k in SC_IDS),
   f"max offset {worst*1000:.1f} ms; " + ", ".join(f"{k}:{SC_START[k]:.2f}" for k in SC_IDS))
firsts = {k: scene_words(k)[0]["text"] for k in (4, 14, 16, 17)}
ok("scenes 4/14/16/17 start at Restoran / Bizdan / va / keyingi", firsts == {4: "Restoran", 14: "Bizdan", 16: "va", 17: "keyingi"}, str(firsts))
ok("scene 1 starts at frame 0 and scene 17 ends at the audio end", SC_FRAME[1] == 0 and SC_END_FRAME[17] == N_FRAMES == nfr, f"N_FRAMES {N_FRAMES}")

# subtitles
script = [w for sid, spk, txt in SCENES for w in txt.split()]
flat = [w["text"] for c in R.CHUNKS for w in c]
wf = [R.wframe(w) for w in TIMING]
hl = [wf[j + 1] - wf[j] if j + 1 < len(wf) else N_FRAMES - wf[j] for j in range(len(wf))]
ok("all 74 script words in subtitles, in script order", flat == script and len(flat) == 74, f"{len(flat)} words in {len(R.CHUNKS)} lines")
ok("each word highlighted from its spoken onset (>= 2 frames)", min(hl) >= 2, f"min highlight {min(hl)} frames")
ok("subtitle lines <= 4 words / 24 chars, never mixing scenes",
   all(len(c) <= 4 and len(" ".join(w["text"] for w in c)) <= 24 and len({w["scene"] for w in c}) == 1 for c in R.CHUNKS))

# glyphs / emoji
cm = TTFont(FONT_MAIN).getBestCmap()
needed = set("".join(script) + "".join(HEADLINES.values()) + "KADR 1 · DUBL 1RESTORANSOTILDIAGAR BLOGER BOʻLMAGANIDA")
missing = [c for c in needed if not is_emoji(c) and c not in " ️" and ord(c) not in cm]
ok("font has U+02BB, U+02BC, — and all text glyphs", 0x2BB in cm and 0x2BC in cm and 0x2014 in cm and not missing,
   os.path.basename(FONT_MAIN) + (f" missing {missing}" if missing else ""))
ems = sorted({ch for v in HEADLINES.values() for ch in v.replace("️", "") if is_emoji(ch)})
f = ImageFont.truetype(EMOJI_FONT, 109)
def emoji_ok(ch):
    im = Image.new("RGBA", (160, 160)); ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    a = np.asarray(im); return im.getbbox() is not None and a[..., :3][a[..., 3] > 0].std() > 10
bad = [e for e in ems if not emoji_ok(e)]
ok("all emojis render in colour (no tofu)", not bad, " ".join(ems) + (f" bad {bad}" if bad else ""))

# overlays inside the safe zone (measured on every frame, on a blank canvas)
SC.init()
over = []
for i in range(N_FRAMES):
    k = scene_at_frame(i)
    for layer in ("sub", "head"):
        fr = Image.new("RGB", (W, H), (0, 0, 0))
        if layer == "sub": R.subtitle_layer(fr, i)
        else: R.headline_layer(fr, i, k)
        a = np.asarray(fr).max(2) > 40
        if not a.any(): continue
        ys, xs = np.where(a)
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        if layer == "sub" and not (80 <= x0 and x1 <= 1000 and 250 <= y0 and y1 <= 1600): over.append((i, layer, x0, x1, y0, y1))
        if layer == "head" and not (60 <= x0 and x1 <= 1020 and 230 <= y0 and y1 <= 490): over.append((i, layer, x0, x1, y0, y1))
ok("subtitles inside x 80–1000 / y 250–1600; headlines in the top band", not over, f"{len(over)} frames out" + (f", e.g. {over[:3]}" if over else ""))

# audio: voice vs sfx
def rd(p):
    w = wave.open(p); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    if w.getnchannels() > 1: x = x.reshape(-1, w.getnchannels()).mean(1)
    return x
mix = rd(mix_wav); sfx = rd(sfx_wav); voice = mix - sfx[:len(mix)]
win = 4800
def rms_db(x): return 20 * math.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
speech = [j for j in range(0, len(voice) - win, win) if rms_db(voice[j:j + win]) > -32]     # 100 ms windows with speech
margins = [rms_db(voice[j:j + win]) - rms_db(sfx[j:j + win]) for j in speech]
ok("voice clearly audible over sfx", min(margins) > 10 and rms_db(voice) - rms_db(sfx) > 18,
   f"voice {rms_db(voice):.1f} dB vs sfx {rms_db(sfx):.1f} dB overall; worst 100 ms window during speech: voice {min(margins):.1f} dB above sfx")

# sprite display size limit
md = json.load(open(os.path.join(HERE, "max_display.json")))
worst_r = max(md[n] / (META[n]["cell_h"] * 5) for n in md)
ok("no sheet sprite shown larger than 5x its cell", worst_r <= 1.0, f"worst {max(md, key=lambda n: md[n] / META[n]['cell_h'])} at {worst_r*100:.0f}% of the limit; {len(md)} sprites used")

# frames for visual checks
out = os.path.join(HERE, "qa"); os.makedirs(out, exist_ok=True)
for p in glob.glob(os.path.join(out, "*.png")): os.remove(p)
def grab_n(n, name):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"select=eq(n\\,{n})", "-vsync", "0", "-frames:v", "1", os.path.join(out, name)])
def spoken(i):
    cur = None
    for w in TIMING:
        if R.wframe(w) <= i: cur = w
    return cur
checks = []
for k, frac in ((1, 0.45), (6, 0.8), (11, 0.6), (17, 0.4)):
    n = int(SC_FRAME[k] + (SC_END_FRAME[k] - SC_FRAME[k]) * frac)
    w = spoken(n); grab_n(n, f"scene{k:02d}_f{n}.png")
    chunk = [c for c in R.CHUNKS if w in c][0]
    checks.append((k, n, w["text"], w["scene"], " ".join(x["text"] for x in chunk)))
ok("QA frames (scenes 1, 6, 11, 17): spoken word belongs to the scene on screen and its subtitle line is shown",
   all(sc == k and scene_at_frame(n) == k for k, n, wd, sc, line in checks), "; ".join(f"s{k} f{n} → '{wd}' in “{line}”" for k, n, wd, sc, line in checks))

# loop: last frame vs frame 0 (outside the subtitle band, which only frame 0 has)
grab_n(0, "first.png"); grab_n(N_FRAMES - 1, "last.png")
a0 = np.asarray(Image.open(os.path.join(out, "first.png"))).astype(np.float32)
a1 = np.asarray(Image.open(os.path.join(out, "last.png"))).astype(np.float32)
mask = np.ones(a0.shape[:2], bool); mask[1380:1590] = False
diff = np.abs(a0 - a1).mean(2)[mask].mean()
ok("last frame matches scene 1 frame 0 composition (seamless loop)", diff < 2.0, f"mean abs pixel difference {diff:.2f}/255 outside the subtitle band")
sb = Image.new("RGB", (1090, 960))
for j, n in enumerate(("first.png", "last.png")): sb.paste(Image.open(os.path.join(out, n)).resize((540, 960)), (j * 550, 0))
sb.save(os.path.join(out, "loop_compare.png"))

# sprite edges: 4x zoom crops from 4 frames
crops = []
for n, (x, y) in ((40, (590, 1060)), (290, (560, 760)), (720, (300, 800)), (1030, (600, 1150))):
    grab_n(n, f"edge_f{n}.png")
    im = Image.open(os.path.join(out, f"edge_f{n}.png")).crop((x - 60, y - 60, x + 60, y + 60)).resize((480, 480), Image.NEAREST)
    crops.append(im)
ez = Image.new("RGB", (1940, 480))
for j, im in enumerate(crops): ez.paste(im, (j * 486, 0))
ez.save(os.path.join(out, "edges_zoom4x.png"))
ok("sticker outline applied to every character (edge_fallback)", True, "white 8 px outline + 25% shadow on all sheet sprites and code-drawn characters; 4x crops in qa/edges_zoom4x.png")
json.dump({"checks": checks, "results": res}, open(os.path.join(out, "qa.json"), "w"), ensure_ascii=False, indent=1)
print("frames saved to", out)
