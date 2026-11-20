# QA checks for the final MP4 (see the "qa" list of the brief). Writes qa_results.json and contact sheets.
import sys, os, json, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from lib import *
from timeline import WORDS, SC, SF, S, DUR, IDS, N_FRAMES, AUDIO_DUR, scene_at, wf, word, REGIONS
import render as R
import scenes as SCN
from props import logo_img

OUT = sys.argv[1]
QADIR = sys.argv[2]
STEMS = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(QADIR, exist_ok=True)
res = {}


def probe(path):
    j = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path]))
    return j


def frame_at(path, i):
    t = max(0.0, (i - 0.5) / 30)            # input seek keeps the first frame with pts >= t  ->  frame i
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", path, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    return Image.frombytes("RGB", (W, H), raw)


def lufs(path):
    o = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float([l for l in o.splitlines() if l.strip().startswith("I:")][-1].split()[1])
    P = float([l for l in o.splitlines() if l.strip().startswith("Peak:")][-1].split()[1])
    return I, P


def ok(name, cond, info):
    res[name] = {"pass": bool(cond), "info": info}
    print(("PASS " if cond else "FAIL ") + name + " — " + json.dumps(info, ensure_ascii=False))


# ---------------------------------------------------------------- container / output spec
pr = probe(OUT)
v = [s for s in pr["streams"] if s["codec_type"] == "video"][0]
a = [s for s in pr["streams"] if s["codec_type"] == "audio"][0]
vd, ad, fd = float(v["duration"]), float(a["duration"]), float(pr["format"]["duration"])
spec = dict(codec=v["codec_name"], pix_fmt=v["pix_fmt"], size=f'{v["width"]}x{v["height"]}', fps=v["r_frame_rate"],
            audio=a["codec_name"], frames=int(v.get("nb_frames", 0)))
ok("output_spec", spec["codec"] == "h264" and spec["pix_fmt"] == "yuv420p" and spec["size"] == "1080x1920" and spec["fps"] == "30/1" and spec["audio"] == "aac", spec)
ok("duration_equals_audio", abs(vd - AUDIO_DUR) <= 1 / 30 + 1e-3 and abs(ad - AUDIO_DUR) <= 1 / 30 + 1e-3,
   {"voice_over_s": round(AUDIO_DUR, 3), "video_stream_s": round(vd, 3), "audio_stream_s": round(ad, 3), "container_s": round(fd, 3)})
I, P = lufs(OUT)
ok("loudness_-14_LUFS", abs(I + 14) <= 0.5 and P <= -0.5, {"integrated_LUFS": I, "peak_dBFS": P})

# ---------------------------------------------------------------- sync: 4 timestamps, subtitle + scene match spoken word
def spoken_at(t):
    cur = None
    for w in WORDS:
        if w["start"] <= t: cur = w
    return cur


def highlighted_at(i):
    ci = R.current_chunk(i)
    ch = R.CHUNKS[ci]; cur = None
    for w in ch:
        if i >= (0 if (w["scene"] == 1 and w["first"]) else wf(w)): cur = w
    return cur, ch


picks = [word(2, "yunesko"), word(5, "sabzi"), word(9, "onamning"), word(13, "va")]
rows = []
for w in picks:
    i = wf(w) + 3                                          # 0.1 s into the word
    t = i / 30
    sp = spoken_at(t)
    hw, ch = highlighted_at(i)
    fr = frame_at(OUT, i)
    sub = np.asarray(fr.crop((0, R.SUB_CY - 70, W, R.SUB_CY + 70))).astype(int)
    yellow = int(((sub[..., 0] > 200) & (sub[..., 1] > 180) & (sub[..., 2] < 90)).sum())
    rows.append(dict(t=round(t, 3), frame=i, spoken=sp["text"], spoken_scene=sp["scene"], shown_scene=scene_at(i),
                     highlighted=hw["text"], line=" ".join(x["text"] for x in ch), yellow_px=yellow))
    fr.save(os.path.join(QADIR, f"sync_{i:04d}.png"))
ok("sync_4_timestamps", all(r["spoken"] == r["highlighted"] and r["spoken_scene"] == r["shown_scene"] and r["yellow_px"] > 300 for r in rows), rows)

# frame offsets of scene starts / word triggers vs. measured word onsets
offs = {}
for k in IDS:
    w0 = [x for x in WORDS if x["scene"] == k][0]
    offs[f"scene{k}"] = SF[k] - (0 if k == 1 else round(w0["start"] * 30))
for wd in ("guruch", "sabzi", "go"):
    tt = SCN.T(5, wd)
    offs[f"s5_{wd}"] = round(tt * 30) - round(word(5, wd)["start"] * 30)
offs["s9_text"] = R.ost_start_frame(9) - round(word(9, "onamning")["start"] * 30)
sub_off = max(abs(wf(w) - w["start"] * 30) for w in WORDS)
ok("sync_max_offset_1_frame", all(abs(x) <= 1 for x in offs.values()) and sub_off <= 1,
   {"trigger_offsets_frames": offs, "max_subtitle_offset_frames": round(sub_off, 2)})

# ---------------------------------------------------------------- frame 0 = hook
f0 = frame_at(OUT, 0)
f0.save(os.path.join(QADIR, "frame0000.png"))
arr = np.asarray(f0).astype(int)
txt = arr[220:450, 60:1020]
white = int(((txt.min(2) > 235)).sum()); gold = int(((txt[..., 0] > 220) & (txt[..., 1] > 160) & (txt[..., 2] < 90)).sum())
plate_px = int(((arr[350:800, 600:1000].min(2) > 230)).sum())
f1 = np.asarray(frame_at(OUT, 1)).astype(int)
motion = float(np.abs(f1 - arr).mean())
ok("frame0_hook", white > 5000 and gold > 2000 and plate_px > 2000 and motion > 0.5 and arr.mean() > 30,
   {"text_white_px": white, "text_gold_px": gold, "falling_lagan_px": plate_px, "mean_abs_diff_to_frame1": round(motion, 2), "black_frame": bool(arr.mean() <= 30)})

# ---------------------------------------------------------------- voice audible over sfx and music
if STEMS:
    vI, _ = lufs(STEMS + "_voice.wav"); sI, sP = lufs(STEMS + "_sfx.wav"); mI, mP = lufs(STEMS + "_music.wav")
    import wave
    def rd(p):
        w = wave.open(p); return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    vv, ss, mm = rd(STEMS + "_voice.wav"), rd(STEMS + "_sfx.wav"), rd(STEMS + "_music.wav")
    # per word: voice RMS vs (sfx+music) RMS inside the word
    worst = 99.0; worst_w = None
    for w in WORDS:
        a0, a1 = int(w["start"] * 48000), int(w["end"] * 48000)
        if a1 - a0 < 2400: continue
        vr = np.sqrt(np.mean(vv[a0:a1] ** 2)); br = np.sqrt(np.mean((ss[a0:a1] + mm[a0:a1]) ** 2)) + 1e-9
        d = 20 * math.log10(vr / br)
        if d < worst: worst, worst_w = d, w["text"]
    s8 = int(S[8] * 48000)
    cut = float(np.abs(mm[s8 + 480:s8 + 24000 - 480]).max())
    ok("voice_audible", vI - sI >= 18 and vI - mI >= 20 and worst >= 15,
       {"voice_LUFS": vI, "sfx_LUFS": sI, "music_LUFS": mI, "voice_minus_music_LU": round(vI - mI, 1),
        "worst_word_voice_over_bed_dB": round(worst, 1), "worst_word": worst_w, "music_peak_in_s8_cut": round(cut, 5)})

# ---------------------------------------------------------------- subtitles inside the frame / safe zone
boxes = []
for ci, ch in enumerate(R.CHUNKS):
    i = R.CH_F[ci]
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # worst case: the widest word active (scaled)
    for j in range(len(ch)):
        ii = (0 if (ch[j]["scene"] == 1 and ch[j]["first"]) else wf(ch[j])) + 2
        if ci + 1 < len(R.CH_F) and ii >= R.CH_F[ci + 1]: continue
        c2 = Image.new("RGBA", (W, H), (0, 0, 0, 0)); R.subtitle_layer(c2, ii)
        bb = c2.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
        if bb: boxes.append((ch[j]["text"], bb))
x0 = min(b[1][0] for b in boxes); x1 = max(b[1][2] for b in boxes); y0 = min(b[1][1] for b in boxes); y1 = max(b[1][3] for b in boxes)
ok("subtitles_inside_frame", x0 >= 40 and x1 <= W - 40 and y0 >= 0 and y1 <= 1560,
   {"union_bbox": [x0, y0, x1, y1], "chunks": len(R.CHUNKS), "safe_zone": "x 40..1040, y < 1560 (above bottom UI)"})

# ---------------------------------------------------------------- poses: right crop per scene, grey sheet bg removed
import re, inspect
src = inspect.getsource(SCN)
pose_use = {}
for k in IDS:
    fn = inspect.getsource(SCN.SCENE_FN[k])
    pose_use[k] = (f'SC[{k}]["pose"]' in fn, SC[k]["pose"])
leftover = {}
for k in IDS:
    name = SC[k]["pose"]
    im = np.asarray(sprite(name)).astype(int)
    al = im[..., 3]; rgb = im[..., :3]
    sat = rgb.max(2) - rgb.min(2); g = rgb.mean(2)
    greyish = (al > 200) & (sat < 10) & (np.abs(g - 221) < 7)
    # only count grey pixels touching transparency (true leftover background, not shading inside the cloth)
    from scipy import ndimage as ndi
    edge = ndi.binary_dilation(al < 20, iterations=3)
    lab, nl = ndi.label(greyish)
    blob = int(max(ndi.sum(greyish, lab, range(1, nl + 1)))) if nl else 0
    leftover[name] = (int((greyish & edge).sum()), blob)
ok("poses_and_bg_removed", all(u for u, _ in pose_use.values()) and max(v[0] for v in leftover.values()) < 400 and max(v[1] for v in leftover.values()) < 400,
   {"scene_pose": {k: p for k, (u, p) in pose_use.items()},
    "per_pose[grey_px_touching_transparency, largest_enclosed_grey_blob_px](x3 upscaled)": leftover})

# ---------------------------------------------------------------- oʻ / gʻ rendering
f = get_font(FONT_MAIN, 100)
from PIL import ImageFont
from fontTools.ttLib import TTFont
cmap = TTFont(FONT_MAIN).getBestCmap()
test = "Oʻn toʻrt · Fargʻona · yogʻi moʻl · doʻstingizga · OʻZ GʻOZ"
timg = text_img(test, 64)
bg = Image.new("RGB", (timg.width + 40, timg.height + 40), (13, 78, 84)); bg.paste(timg, (20, 20), timg); bg.save(os.path.join(QADIR, "uz_glyph_test.png"))
im = Image.new("L", (200, 200), 0); d = ImageDraw.Draw(im); draw_runs(d, 20, 150, "oʻ", f, 255)
ink = np.asarray(im)
cols = np.where(ink[:, 80:].max(0) > 0)[0]
mark_rows = np.where(ink[:, 80:].max(1) > 0)[0]
mark_above = mark_rows.max() < 150 - 30 if len(mark_rows) else False
ok("uz_okina_glyph", 0x2BB in cmap and len(cols) > 5 and mark_above,
   {"font": os.path.basename(FONT_MAIN), "U+02BB_in_cmap": 0x2BB in cmap, "glyph_drawn_as_raised_mark": bool(mark_above), "test_image": "uz_glyph_test.png"})

# ---------------------------------------------------------------- scene 7: 11 region cards readable
times, step = SCN.card_times()
i_last = SF[8] - 1
lt = (i_last - SF[7]) / 30
fr7 = frame_at(OUT, i_last); fr7.save(os.path.join(QADIR, "scene7_last.png"))
all_front = all(lt >= tt + 0.12 for tt in times)
hold = [round(min(lt - tt - 0.12, 99), 2) for tt in times]
sizes = []
for name in REGIONS:
    sz = 40
    while text_width(name, get_font(FONT_MAIN, sz)) > 440 - 70: sz -= 1
    sizes.append(sz)
ok("scene7_regions_readable", all_front and len(REGIONS) == 11 and min(sizes) >= 34 and max(times) - min(times) > 0,
   {"cards": len(REGIONS), "slot_s_each": step, "all_front_on_last_frame": all_front, "min_font_px": min(sizes),
    "last_card_visible_s": hold[-1], "image": "scene7_last.png"})

# ---------------------------------------------------------------- logo in scene 14
lx, ly = SCN.LOGO_POS
def ink_box(layer_fn, i):
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0)); layer_fn(c, i, 14)
    return c.getchannel("A").point(lambda v: 255 if v > 60 else 0).getbbox()
fi_settled = SF[14] + 30
logo_box = ink_box(R.logo_layer, fi_settled)
ost_box = ink_box(R.ost_layer, fi_settled)
sub_box = (x0, y0, x1, y1)
def inter(a, b): return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
fi = SF[14] + 30
fr14 = frame_at(OUT, fi); fr14.save(os.path.join(QADIR, "scene14_logo.png"))
crop = np.asarray(fr14.crop((int(lx - 60), int(ly - 60), int(lx + 60), int(ly + 60)))).astype(int)
ref = np.asarray(logo_img(SCN.LOGO_D).resize((SCN.LOGO_D + 60, SCN.LOGO_D + 60)).convert("RGB")).astype(int)
cc = ref.shape[0] // 2
diff = float(np.abs(crop - ref[cc - 60:cc + 60, cc - 60:cc + 60]).mean())
ok("scene14_logo_visible_no_overlap", not inter(logo_box, sub_box) and not inter(logo_box, ost_box) and diff < 25,
   {"logo_ink_box": list(logo_box), "subtitle_box": list(sub_box), "ost_ink_box": list(ost_box), "gap_text_to_logo_px": logo_box[1] - ost_box[3],
    "logo_pixels_match_mean_abs": round(diff, 1), "visible_from_s": round(S[14] + 0.6, 2)})

# ---------------------------------------------------------------- loop: last frame -> frame 0
fl = frame_at(OUT, N_FRAMES - 1); fl.save(os.path.join(QADIR, "frame_last.png"))
A0 = np.asarray(f0).astype(int); AL = np.asarray(fl).astype(int)
band = lambda A: A[1180:1400]                                   # table + floor band
d_table = float(np.abs(band(A0) - band(AL)).mean())
d_all = float(np.abs(A0 - AL).mean())
# typical consecutive-frame difference inside the video for reference
ref_d = float(np.mean([np.abs(np.asarray(frame_at(OUT, i)).astype(int) - np.asarray(frame_at(OUT, i + 1)).astype(int)).mean() for i in (50, 400, 1150)]))
s14_lt = (N_FRAMES - 1 - SF[14]) / 30
cam_last = SCN.scene14(0, s14_lt, DUR[14])[1]["scale"]
cam_0 = SCN.scene1(0, 0, DUR[1])[1]["scale"]
t_rel_last = s14_lt - (DUR[14] - 0.4); t_rel_0 = 0.4
ok("loop_seamless", d_table < 12 and abs(cam_last - cam_0) < 0.01 and abs((t_rel_0 - t_rel_last) - 1 / 30) < 1e-6,
   {"table_band_mean_abs_diff": round(d_table, 2), "whole_frame_mean_abs_diff": round(d_all, 2), "typical_consecutive_frame_diff": round(ref_d, 2),
    "camera_scale_last_vs_0": [round(cam_last, 4), round(cam_0, 4)], "falling_lagan_time_step_s": round(t_rel_0 - t_rel_last, 4),
    "no_landing_at_end": True})

# contact sheet of QA frames
names = ["frame0000.png"] + [f"sync_{r['frame']:04d}.png" for r in rows] + ["scene7_last.png", "scene14_logo.png", "frame_last.png"]
cw, chh = 270, 480
sheet = Image.new("RGB", (cw * 4, chh * 2), (0, 0, 0))
for k, n in enumerate(names):
    sheet.paste(Image.open(os.path.join(QADIR, n)).resize((cw, chh)), ((k % 4) * cw, (k // 4) * chh))
sheet.save(os.path.join(QADIR, "qa_sheet.png"))
json.dump(res, open(os.path.join(QADIR, "qa_results.json"), "w"), ensure_ascii=False, indent=1)
print("ALL PASS" if all(r["pass"] for r in res.values()) else "SOME CHECKS FAILED")
