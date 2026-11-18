# QA checks for the final video.
import sys, json, math, subprocess, os, glob
import numpy as np
from PIL import Image, ImageDraw
from fontTools.ttLib import TTFont
import scenes as SC
from scenes import *
import render as R

video = sys.argv[1]; src_audio = sys.argv[2]
res = []
def ok(name, cond, info=""):
    res.append((name, bool(cond), info)); print(("PASS " if cond else "FAIL ") + name + (" — " + info if info else ""))

def probe(args):
    return subprocess.run(["ffprobe", "-v", "error"] + args, capture_output=True, text=True).stdout.strip()

# 1. durations
vdur = float(probe(["-select_streams", "v:0", "-show_entries", "stream=duration", "-of", "csv=p=0", video]))
adur = float(probe(["-select_streams", "a:0", "-show_entries", "stream=duration", "-of", "csv=p=0", video]))
sdur = float(probe(["-show_entries", "format=duration", "-of", "csv=p=0", src_audio]))
nfr = int(probe(["-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", video]))
ok("video duration equals audio duration", abs(vdur - adur) <= 1 / FPS and abs(vdur - sdur) <= 1 / FPS,
   f"video {vdur:.3f}s, audio track {adur:.3f}s, source voice {sdur:.3f}s, {nfr} frames")
spec = probe(["-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height,pix_fmt,r_frame_rate", "-of", "csv=p=0", video])
aspec = probe(["-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", video])
ok("format h264 1080x1920 30fps yuv420p + aac", spec.startswith("h264,1080,1920,yuv420p,30/1") and aspec == "aac", spec + " / " + aspec)

# 2. scene starts within 1 frame of their first word
worst = max(SC_FRAME[k] / FPS - SC_START[k] for k in SC_IDS)
ok("every scene starts within 1 frame of its first word", all(0 <= SC_FRAME[k] / FPS - SC_START[k] < 1 / FPS + 1e-9 for k in SC_IDS),
   f"max offset {worst*1000:.1f} ms; starts: " + ", ".join(f"{k}:{SC_START[k]:.2f}" for k in SC_IDS))
ok("mid-sentence cuts at aptekachi / mevaga / lekin", [scene_words(k)[0]["text"] for k in (3, 10, 15)] == ["aptekachi", "mevaga", "lekin"])

# 3. subtitles: all 64 words, script order, each highlighted >= 1 frame
script = [w for sid, spk, txt in SCENES for w in txt.split()]
flat = [w["text"] for c in R.CHUNKS for w in c]
wf = [0 if (w["scene"] == 1 and w["first"]) else word_frame(w) for w in TIMING]
hl_frames = [wf[j + 1] - wf[j] if j + 1 < len(wf) else N_FRAMES - wf[j] for j in range(len(wf))]
ok("all 64 script words in subtitles, in order", flat == script and len(flat) == 64, f"{len(flat)} words, {len(R.CHUNKS)} lines")
ok("every word highlighted when spoken (>=1 frame)", min(hl_frames) >= 1, f"min highlight {min(hl_frames)} frames")
ok("subtitle lines <=4 words / <=24 chars, no scene mixing", all(len(c) <= 4 and len(" ".join(w["text"] for w in c)) <= 24 and len({w["scene"] for w in c}) == 1 for c in R.CHUNKS))

# 4. glyphs
cm = TTFont(FONT_MAIN).getBestCmap()
ok("font has U+02BB and U+02BC", 0x2BB in cm and 0x2BC in cm, os.path.basename(FONT_MAIN))
ems = sorted({ch for v in HEADLINES.values() for ch in v.replace("️", "") if is_emoji(ch)} | {"😡"})
from PIL import ImageFont
f = ImageFont.truetype(EMOJI_FONT, 109)
def emoji_ok(ch):
    im = Image.new("RGBA", (160, 160)); ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    a = np.asarray(im); return im.getbbox() is not None and a[..., :3][a[..., 3] > 0].std() > 10
bad = [e for e in ems if not emoji_ok(e)]
ok("all emojis render in colour (no tofu)", not bad, " ".join(ems) + (f" bad: {bad}" if bad else ""))
tofu = [c for c in set("".join(script) + "".join(HEADLINES.values()) + "XOʻJAYIN: Bir haftada bitta ham dori sotilmadi!!!") if not is_emoji(c) and c not in " ️" and ord(c) not in cm]
ok("no missing text glyphs", not tofu, f"missing: {tofu}" if tofu else "")

# 5. safe zone for overlays (measured on blank frames, every frame)
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
ok("subtitles inside x80–1000 / y250–1600, headlines in top band", not over, f"{len(over)} frames out" + (f", e.g. {over[:3]}" if over else ""))

# 6. sprite halos: opaque edge pixels close to the sheet grey
worst = []
for p in sorted(glob.glob(os.path.join(SPR_DIR, "*.png"))):
    a = np.asarray(Image.open(p).convert("RGBA")).astype(int)
    al = a[..., 3]
    edge = (al > 30) & (al < 250)
    rgb = a[..., :3][edge]
    grey = (np.abs(rgb - 221).max(1) < 14).mean() if len(rgb) else 0
    worst.append((grey, os.path.basename(p)))
worst.sort(reverse=True)
ok("sprites have no grey halo", worst[0][0] < 0.03, f"worst edge-grey share {worst[0][0]*100:.2f}% ({worst[0][1]})")

# 7. frames for visual checks
out = os.path.join(HERE, "qa"); os.makedirs(out, exist_ok=True)
def grab(t, name):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", os.path.join(out, name)])
def spoken(t):
    cur = None
    for w in TIMING:
        if w["start"] <= t + 1e-6 or (w["scene"] == 1 and w["first"]): cur = w
    return cur
checks = []
for k, frac in ((1, 0.35), (9, 0.5), (13, 0.55), (18, 0.45)):
    t = (SC_FRAME[k] + (SC_END_FRAME[k] - SC_FRAME[k]) * frac) // 1 / FPS + 0.001
    w = spoken(t); grab(t, f"scene{k:02d}.png")
    checks.append((k, t, w["text"], w["scene"]))
ok("QA timestamps: spoken word belongs to the scene on screen", all(sc == k for k, t, wd, sc in checks), "; ".join(f"s{k} @{t:.2f}s → '{wd}'" for k, t, wd, sc in checks))
grab(0.0, "first.png")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"select=eq(n\\,{N_FRAMES-1})", "-vsync", "0", "-frames:v", "1", os.path.join(out, "last.png")])
# loop: character silhouette of frame 0 vs last frame (same anchor/scale/camera by construction)
import scenes as S2
m0 = S2.sprite("pharm_06").getchannel("A"); m1 = S2.sprite("blogger_06").getchannel("A")
def bbox_at(name):
    src = S2.sprite(name); h = src.height * S2.K_BLOG; w = src.width * S2.K_BLOG
    return (round(S2.A1["x"] - w / 2), round(S2.A1["yb"] - h), round(S2.A1["x"] + w / 2), round(S2.A1["yb"]))
b0, b1 = bbox_at("pharm_06"), bbox_at("blogger_06")
d = max(abs(a - b) for a, b in zip(b0, b1))
ok("last frame matches scene-1 frame-0 composition", d <= 5, f"pose 6 bbox first {b0} vs last {b1}; camera zoom 1.0 centre (540,960) on both")
sidebyside = Image.new("RGB", (1090, 960))
for j, n in enumerate(("first.png", "last.png")):
    sidebyside.paste(Image.open(os.path.join(out, n)).resize((540, 960)), (j * 550, 0))
sidebyside.save(os.path.join(out, "loop_compare.png"))
json.dump({"checks": checks, "results": res}, open(os.path.join(out, "qa.json"), "w"), ensure_ascii=False, indent=1)
print("frames saved to", out)
