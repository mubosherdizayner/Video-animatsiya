# QA checks for the final video. Usage: python3 qa.py <video.mp4> <voice.mp3> <outdir>
import sys, os, json, subprocess
import numpy as np
import skia
from PIL import Image
from fontTools.ttLib import TTFont
import scenes as SC
import text as TX
import render as R
from hero import draw_hero, Pose, C as HC

video, voice, outdir = sys.argv[1:4]
os.makedirs(outdir, exist_ok=True)
res = []


def ok(name, cond, info=""):
    res.append({"check": name, "pass": bool(cond), "info": info})
    print(("PASS " if cond else "FAIL ") + name + (" — " + info if info else ""), flush=True)


def probe(args):
    return subprocess.run(["ffprobe", "-v", "error"] + args, capture_output=True, text=True).stdout.strip()


_DEC = {}


def decode_frame(idx):
    """exact frame by index (decodes the whole stream once and caches the needed frames)"""
    if idx in _DEC: return _DEC[idx]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"select=eq(n\\,{idx})", "-vsync", "0",
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    _DEC[idx] = np.frombuffer(raw, np.uint8).reshape(1920, 1080, 3)
    return _DEC[idx]


def render_rgb(idx):
    return R.frame_rgb(idx)


# 1. format and duration -------------------------------------------------------------------------
spec = probe(["-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height,pix_fmt,r_frame_rate", "-of", "csv=p=0", video])
aspec = probe(["-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", video])
ok("format: mp4 h264 1080x1920 30 fps yuv420p + aac", spec == "h264,1080,1920,yuv420p,30/1" and aspec == "aac", f"{spec} / {aspec}")
vdur = float(probe(["-select_streams", "v:0", "-show_entries", "stream=duration", "-of", "csv=p=0", video]))
adur = float(probe(["-select_streams", "a:0", "-show_entries", "stream=duration", "-of", "csv=p=0", video]))
sdur = float(probe(["-show_entries", "format=duration", "-of", "csv=p=0", voice]))
ok("video duration equals audio duration", abs(vdur - adur) <= 1 / SC.FPS and abs(vdur - sdur) <= 1 / SC.FPS,
   f"video {vdur:.3f}s, audio track {adur:.3f}s, voice-over {sdur:.4f}s ({SC.N_FRAMES} frames)")

# 2. sync: scene changes and word onsets within 1 frame -----------------------------------------------
worst_sc = max(abs(SC.SC_FRAME[k] / SC.FPS - SC.SC_START[k]) for k in SC.SC_IDS) * SC.FPS
worst_w = max(abs(TX.wf(w) / SC.FPS - (0.0 if w is SC.TIMING[0] else w["start"])) for w in SC.TIMING) * SC.FPS
ok("scene changes on the first word of each scene (≤1 frame)", worst_sc <= 1.0,
   f"max offset {worst_sc:.2f} frames; starts " + ", ".join(f"{k}:{SC.SC_START[k]:.2f}s" for k in SC.SC_IDS))
ok("each subtitle word highlighted when spoken (≤1 frame)", worst_w <= 1.0, f"max offset {worst_w:.2f} frames over {len(SC.TIMING)} words")
script = [w for _, t in SC.SCENES for w in t.split()]
flat = [w["text"] for ch in TX.CHUNKS for w in ch]
ok("subtitles use the script text, all words in order", flat == script, f"{len(flat)} words in {len(TX.CHUNKS)} phrase lines")

# 3. four extracted frames: subtitle word and scene match the spoken word ------------------------------
probe_words = ["kasb", "Soʻz", "Eng", "Dasturchi"]
sheet = []
for pw in probe_words:
    w = next(x for x in SC.TIMING if x["text"].startswith(pw))
    idx = TX.wf(w) + 2
    spoken = [x for x in SC.TIMING if (0 if x is SC.TIMING[0] else x["start"]) <= idx / SC.FPS][-1]
    r = TX.draw_subtitle(skia.Surface(1080, 1920).getCanvas(), idx)
    shown = r[1] if r else None
    sc = SC.scene_at(idx)
    dec = decode_frame(idx); ren = render_rgb(idx)
    mse = np.mean((dec.astype(float) - ren.astype(float)) ** 2); psnr = 10 * np.log10(255 ** 2 / max(mse, 1e-9))
    # the highlighted word must be visible: accent orange pixels inside the subtitle pill
    l, t, rr, b = [int(v) for v in r[0]]
    pill = dec[t:b, l:rr].astype(int)
    orange = (np.abs(pill - np.array([225, 116, 47])).sum(2) < 60).sum()
    Image.fromarray(dec).save(os.path.join(outdir, f"probe_{idx:04d}.png"))
    sheet.append(Image.fromarray(dec).resize((360, 640)))
    ok(f"frame {idx} ({idx / SC.FPS:.2f}s): subtitle + scene match the spoken word",
       shown == spoken["text"] and sc == spoken["scene"] and psnr > 30 and orange > 200,
       f"spoken '{spoken['text']}' (scene {spoken['scene']}), highlighted '{shown}', scene shown {sc}, "
       f"decoded-vs-render PSNR {psnr:.1f} dB, accent px {orange}")
s = Image.new("RGB", (360 * 4, 640), "white")
for j, im in enumerate(sheet): s.paste(im, (j * 360, 0))
s.save(os.path.join(outdir, "probe_sheet.png"))

# 4. frame 0 already shows the hook visual + hook text ------------------------------------------------
f0 = decode_frame(0)
x0, y0, x1, y1 = [int(v) for v in TX.head_bbox(1)]
ink = (np.abs(f0[y0:y1, x0:x1].astype(int) - np.array([31, 41, 44])).sum(2) < 40).sum()
acc = (np.abs(f0[y0:y1, x0:x1].astype(int) - np.array([225, 116, 47])).sum(2) < 40).sum()
hero_px = (np.abs(f0[700:1200, 300:600].astype(int) - np.array([63, 123, 97])).sum(2) < 30).sum()
lum = f0.mean()
ok("frame 0 shows the hook visual and hook text (no fade-in)", ink > 3000 and acc > 3000 and hero_px > 1500 and lum > 120,
   f"headline ink px {ink}, accent px {acc}, hero chapan px {hero_px}, mean luminance {lum:.0f}")

# 5. audio: voice clearly audible over sfx -------------------------------------------------------------
log = json.load(open(os.path.join(SC.HERE, "sfx_log.json")))
peaks = [e["peak_db_vs_voice"] for e in log["events"]]
ok("voice clearly audible over sfx (no music)", log["voice_to_sfx_rms_db"] >= 15 and max(peaks) <= -17.9,
   f"voice/sfx RMS {log['voice_to_sfx_rms_db']} dB, loudest sfx peak {max(peaks)} dB vs voice peak, {len(peaks)} sfx events")

# 6/7. subtitle bounds and headline/subtitle separation -------------------------------------------------
boxes = [TX.sub_box(ch) for ch in TX.CHUNKS]
inside = all(b[0] >= 60 and b[2] <= 1020 and b[1] >= 0 and b[3] <= 1920 and (b[2] - b[0]) <= 900 + 1 for b in boxes)
ok("no subtitle goes outside the frame (max width 900, 60 px side margin)", inside,
   f"widest pill {max(b[2] - b[0] for b in boxes):.0f}px, x range {min(b[0] for b in boxes):.0f}-{max(b[2] for b in boxes):.0f}, "
   f"centre y {TX.SUB_CY}")
hb = [TX.head_bbox(k) for k in SC.SC_IDS if TX.head_tokens(k)]
gap = min(b[1] for b in boxes) - max(h[3] for h in hb)
in_third = all(h[1] >= 300 and h[3] <= 580 for h in hb)
ok("on-screen text never overlaps the subtitles; headline sits in the upper third", gap > 0 and in_third,
   f"lowest headline bottom {max(h[3] for h in hb):.0f}px, highest subtitle top {min(b[1] for b in boxes):.0f}px, gap {gap:.0f}px")

# 8. hero matches the reference (colours + proportions) --------------------------------------------------
ref = np.array(Image.open(os.path.join(SC.HERE, "reference_hero.png")).convert("RGBA"))
sf = skia.Surface(1080, 1920); cc = sf.getCanvas(); cc.clear(skia.Color(0, 0, 0, 0))
draw_hero(cc, 520, 1699, 1.0, 1, Pose())
mine = sf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
ma, mb = ref[:, :, 3] > 128, mine[:, :, 3] > 128
iou = (ma & mb).sum() / (ma | mb).sum()
cm = (np.abs(ref[:, :, :3].astype(int) - mine[:, :, :3].astype(int)).sum(2)[ma & mb] < 30).mean()
hgt_ref = np.nonzero(ma.any(1))[0]; hgt_me = np.nonzero(mb.any(1))[0]
ok("hero colours and proportions match the reference image", iou > 0.98 and cm > 0.95 and abs(len(hgt_ref) - len(hgt_me)) <= 3,
   f"side-view silhouette IoU {iou:.4f}, colour match {cm:.4f}, height {len(hgt_me)} vs {len(hgt_ref)} px")
both = np.zeros((1920, 2160, 4), np.uint8); both[:, :1080] = ref; both[:, 1080:] = mine
bg = Image.new("RGBA", (2160, 1920), (255, 255, 255, 255)); bg.alpha_composite(Image.fromarray(both))
bg.convert("RGB").crop((300, 200, 1860, 1750)).resize((780, 775)).save(os.path.join(outdir, "hero_vs_reference.png"))

# 9. seamless loop: last frame matches frame 0 ------------------------------------------------------------
w0 = SC.render_scene(0).makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
wl = SC.render_scene(SC.LAST).makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
world_diff = np.abs(w0.astype(int) - wl.astype(int)).max()
dl = decode_frame(SC.LAST)
mask = np.ones((1920, 1080), bool)
for k in (1, 13):
    a, b_, c_, d = [int(v) for v in TX.head_bbox(k)]; mask[max(0, b_ - 30):d + 30, :] = False
for ch in (TX.CHUNKS[0], TX.CHUNKS[-1]):
    a, b_, c_, d = [int(v) for v in TX.sub_box(ch)]; mask[b_ - 20:d + 20, :] = False
vd = np.abs(f0.astype(int) - dl.astype(int)).sum(2)[mask]
noise = np.abs(f0.astype(int) - render_rgb(0).astype(int)).sum(2)[mask]      # h264 noise baseline
ok("last frame matches frame 0 (pose, framing, sun, colours) for a seamless loop",
   world_diff == 0 and vd.mean() <= 2 * noise.mean() + 0.5,
   f"world render (before text) max pixel diff {world_diff}; decoded first vs last outside text {vd.mean():.2f}/765 "
   f"vs h264 noise baseline {noise.mean():.2f}/765")
Image.fromarray(np.concatenate([f0, dl], 1)).resize((1080, 960)).save(os.path.join(outdir, "loop_first_last.png"))

# 10. Uzbek characters render correctly ------------------------------------------------------------------
chars = set("".join(w["text"] for w in SC.TIMING)) | set("".join(" ".join(TX.head_tokens(k)) for k in SC.SC_IDS)) - TX.ICONS
missing = {}
for path in (SC.FONT_BOLD, SC.FONT_DISPLAY):
    cm_ = TTFont(path).getBestCmap()
    miss = sorted(ch for ch in chars if ch.strip() and ord(ch) not in cm_ and ch not in "✈👇")
    tf = skia.Typeface.MakeFromFile(path)
    gl = skia.Font(tf, 40).textToGlyphs("oʻ gʻ ʼ ' Toʻxtang maʼnoda QIZIGʻI DOʻSTINGIZGA")
    missing[os.path.basename(path)] = (miss, int((np.array(gl) == 0).sum()))
special = [c_ for c_ in "ʻʼ'\"" if c_ in chars]
ok("oʻ gʻ ʼ and ' render correctly in subtitles and on-screen text",
   all(not m[0] and m[1] == 0 for m in missing.values()) and "ʻ" in chars and "ʼ" in chars,
   f"glyph check {missing}; special marks used: {' '.join(special)}")
sf = skia.Surface(1080, 300); cc = sf.getCanvas(); cc.clear(skia.Color(244, 237, 223))
cc.drawString("Toʻxtang!  qizigʻi  maʼnoda  \"computer\"", 30, 110, SC.font(SC.FONT_BOLD, 56), skia.Paint(Color=skia.Color(31, 41, 44), AntiAlias=True))
cc.drawString("ENG QIZIGʻI →  DOʻSTINGIZGA", 30, 230, SC.font(SC.FONT_DISPLAY, 70), skia.Paint(Color=skia.Color(225, 116, 47), AntiAlias=True))
sf.makeImageSnapshot().save(os.path.join(outdir, "glyph_test.png"), skia.kPNG)

# 11. every scene moves: no two consecutive identical frames ------------------------------------------------
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", "scale=270:480", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                     capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, 480, 270).astype(np.int16)
dif = np.abs(np.diff(fr, axis=0)).mean((1, 2))
per = {k: float(dif[SC.SC_FRAME[k]:SC.SC_END_FRAME[k] - 1].min()) for k in SC.SC_IDS}
ok("every scene has movement (no static frames)", min(dif) > 0.05,
   f"min mean frame-to-frame change {min(dif):.2f}/255; per scene min " + ", ".join(f"{k}:{v:.2f}" for k, v in per.items()))

json.dump(res, open(os.path.join(outdir, "qa_results.json"), "w"), ensure_ascii=False, indent=1)
print(f"\n{sum(r['pass'] for r in res)}/{len(res)} checks passed")
