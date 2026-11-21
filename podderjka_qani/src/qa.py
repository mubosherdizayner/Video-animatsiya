# QA checks from the brief, run on the encoded MP4.  python3 qa.py ../podderjka_qani.mp4
import sys, os, json, subprocess, math
import numpy as np
from PIL import Image, ImageDraw
from common import FPS, W, H, BUILD, ACCENT, hx
from script_data import SCENES, WORDS, N_FRAMES, TOTAL, CHA_F, LINES
import overlay as OV
import qahramon as Q

def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,duration,nb_frames,sample_rate,channels",
                          "-show_entries", "format=duration", "-of", "json", path], capture_output=True, text=True).stdout
    return json.loads(out)

_CACHE = {}
def load_frames(path, idx):
    """decode the video once, keep only the requested frame indices"""
    want = set(idx) - set(_CACHE)
    if not want: return
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = W * H * 3; i = 0; last = max(want)
    while i <= last:
        b = p.stdout.read(n)
        if len(b) < n: break
        if i in want: _CACHE[i] = np.frombuffer(b, np.uint8).reshape(H, W, 3)
        i += 1
    p.stdout.close(); p.kill()

def frame(path, f):
    if f not in _CACHE: load_frames(path, [f])
    return _CACHE[f]

# ---------------------------------------------------------------- subtitle word boxes (same layout code as overlay.plate_img)
def word_boxes(scene_id):
    line = LINES[scene_id - 1]; toks = line.split(" ")
    f = OV.font(OV.SUB_FONT, OV.SUB_SIZE)
    rows = OV._split_lines(toks, f)
    sp = f.getlength(" ")
    widths = [sum(f.getlength(toks[i]) for i in r) + sp * (len(r) - 1) for r in rows]
    tw = max(widths); scale = min(1.0, (OV.SUB_MAXW - 64) / tw)
    im = OV.plate_img(scene_id, -1)
    x0 = 540 - im.width / 2 + 16 + 32; y0 = OV.SUB_CY - im.height / 2 + 16 + 20
    boxes = {}
    for li, r in enumerate(rows):
        x = (tw - widths[li]) / 2
        for i in r:
            w = f.getlength(toks[i])
            boxes[i] = (x0 + x * scale, y0 + li * OV.LINE_H * scale, x0 + (x + w) * scale, y0 + (li + 1) * OV.LINE_H * scale)
            x += w + sp
    return boxes

def accent_mask(a):
    d = np.abs(a.astype(int) - np.array(ACCENT)).sum(2)
    return d < 60

def highlighted_word(img, scene_id):
    m = accent_mask(img)
    best, bi = 0, None
    for i, (x0, y0, x1, y1) in word_boxes(scene_id).items():
        c = m[int(y0):int(y1), int(x0):int(x1)].sum()
        if c > best: best, bi = c, i
    return bi, int(best)

def main(path):
    R = {}
    pr = probe(path)
    need = {0, N_FRAMES - 1}
    for w in (WORDS[1], WORDS[22], WORDS[50], WORDS[-2]): need.add((w["f0"] + w["f1"]) // 2)
    for w in WORDS:
        if w["scene"] != 16 and w["idx"] > 0: need |= {w["f0"] - 1, w["f0"]}
    need |= set(range(SCENES[13]["f0"], SCENES[13]["f1"]))
    need |= set(range(0, N_FRAMES, 20))
    load_frames(path, need)
    vs = [s for s in pr["streams"] if s["codec_type"] == "video"][0]
    au = [s for s in pr["streams"] if s["codec_type"] == "audio"][0]
    vdur = float(vs.get("duration", pr["format"]["duration"])); adur = float(au.get("duration", 0))
    R["format"] = dict(video=f'{vs["codec_name"]} {vs["width"]}x{vs["height"]} {vs["pix_fmt"]} {vs["r_frame_rate"]}', frames=int(vs.get("nb_frames", 0)),
                       audio=f'{au["codec_name"]} {au["sample_rate"]} Hz {au["channels"]} ch', video_s=vdur, audio_s=adur)
    R["format"]["ok"] = (vs["codec_name"] == "h264" and vs["pix_fmt"] == "yuv420p" and vs["width"] == 1080 and vs["height"] == 1920
                         and vs["r_frame_rate"] == "30/1" and au["codec_name"] == "aac")
    # 1) 4 timestamps: scene + highlighted subtitle word match the timing
    checks = []
    for w in (WORDS[1], WORDS[22], WORDS[50], WORDS[-2]):
        f = (w["f0"] + w["f1"]) // 2
        img = frame(path, f)
        sid = [s["id"] for s in SCENES if s["f0"] <= f < s["f1"]][0]
        hi, px = highlighted_word(img, sid)
        Image.fromarray(img).save(os.path.join(BUILD, f"qa_f{f:04d}.png"))
        checks.append(dict(frame=f, t=round(f / FPS, 3), expected_scene=w["scene"], scene=sid, expected_word=w["word"],
                           highlighted=LINES[sid - 1].split(" ")[hi] if hi is not None else None, ok=(sid == w["scene"] and hi == w["idx"])))
    # word-onset precision: highlight switches exactly on each word's first frame (all words with a plate)
    onset = []
    for w in WORDS:
        if w["scene"] == 16 or w["idx"] == 0: continue
        a = frame(path, w["f0"] - 1); b = frame(path, w["f0"])
        ha, _ = highlighted_word(a, w["scene"]); hb, _ = highlighted_word(b, w["scene"])
        onset.append(ha == w["idx"] - 1 and hb == w["idx"])
    R["timestamps"] = dict(samples=checks, word_onsets_exact=f"{sum(onset)}/{len(onset)}", ok=all(c["ok"] for c in checks) and all(onset))
    # 2) frame 0 shows the hook visual + hook text
    f0 = frame(path, 0)
    top = f0[220:305, 340:740]
    cream = (np.abs(top.astype(int) - np.array(hx("F4EDDF"))).sum(2) < 40).mean()
    acc0 = accent_mask(top).sum()
    green = (np.abs(f0.astype(int) - np.array(Q.CHAPAN)).sum(2) < 45).mean()
    hi0, _ = highlighted_word(f0, 1)
    R["frame0"] = dict(obunachi_plate_cream_frac=round(float(cream), 3), accent_zero_px=int(acc0), chapan_frac=round(float(green), 3),
                       first_word_highlighted=(hi0 == 0), ok=bool(cream > 0.3 and acc0 > 50 and green > 0.05 and hi0 == 0))
    Image.fromarray(f0).save(os.path.join(BUILD, "qa_frame0.png"))
    # 3) cha steps on the cha syllables: each step's motion starts exactly on its cha frame
    #    (diff between frame c-1 and c is the largest in c-2..c+2 and the frames before it are calm)
    s14 = SCENES[13]
    hero_box = (slice(820, 1300), slice(380, 720))
    dif = {}
    for f in range(s14["f0"] + 1, s14["f1"]):
        dif[f] = float(np.abs(frame(path, f)[hero_box].astype(int) - frame(path, f - 1)[hero_box].astype(int)).mean())
    med = float(np.median(list(dif.values())))
    per = []
    for c in CHA_F:
        win = {f: dif[f] for f in range(c - 2, c + 3) if f in dif}
        onset = max(win, key=win.get)
        calm_before = dif.get(c - 1, 0) < 0.4 * dif[c]
        per.append(dict(cha_frame=c, onset_frame=onset, jump=round(dif[c], 2), before=round(dif.get(c - 1, 0), 2), ok=onset == c and calm_before))
    R["cha"] = dict(cha_s=[round(f / FPS, 3) for f in CHA_F], steps=per, median_motion=round(med, 2), ok=all(p["ok"] for p in per))
    # 4) last frame matches frame 0 (loop)
    fl = frame(path, N_FRAMES - 1)
    mask = np.ones((H, W), bool); x0, y0, x1, y1 = [int(v) for v in OV.plate_box(20)]
    mask[min(y0, int(OV.plate_box(1)[1])) - 10:max(y1, int(OV.plate_box(1)[3])) + 10, :] = False
    d_all = float(np.abs(fl.astype(int) - f0.astype(int)).mean())
    d_vis = float(np.abs(fl.astype(int) - f0.astype(int))[mask].mean())
    R["loop"] = dict(mean_abs_diff_full=round(d_all, 2), mean_abs_diff_outside_subtitle=round(d_vis, 2), ok=d_vis < 6.0)
    Image.fromarray(np.concatenate([f0, fl], 1)).resize((1080, 960)).save(os.path.join(BUILD, "qa_loop_pair.png"))
    # 5) colour: saturated pixels belong to the hero palette or the accent family (sample every 20th frame)
    hero_cols = [Q.CHAPAN, Q.CHAPAN_D, Q.CHAPAN_L, Q.IKAT1, Q.IKAT2, Q.GOLD, Q.BELT, Q.SKIN, Q.SKIN_D, hx("9E4A3E"), hx("843B31")]
    acc_cols = [ACCENT, hx("F2A55C"), hx("F0B866"), hx("E7A05C"), hx("F3D9A0"), hx("EAAE5C"), hx("EED29A")]
    tot = 0; on_hero = 0; on_acc = 0; other = 0
    worst = (0, None)
    for f in range(0, N_FRAMES, 20):
        a = frame(path, f).astype(int)
        sub = np.ones((H, W), bool)
        bx = [int(v) for v in OV.plate_box([s["id"] for s in SCENES if s["f0"] <= f < s["f1"]][0])]
        sub[bx[1]:bx[3], bx[0]:bx[2]] = False
        px = a[sub]
        chroma = px.max(1) - px.min(1)
        sat = px[chroma > 70]
        if len(sat) == 0: continue
        dh = np.min(np.stack([np.abs(sat - np.array(c)).sum(1) for c in hero_cols]), 0)
        da = np.min(np.stack([np.abs(sat - np.array(c)).sum(1) for c in acc_cols]), 0)
        h_ = dh < 70; a_ = (~h_) & (da < 90)
        o_ = ~(h_ | a_)
        tot += len(sat); on_hero += h_.sum(); on_acc += a_.sum(); other += o_.sum()
        if o_.mean() > worst[0]: worst = (float(o_.mean()), f)
    R["colour"] = dict(saturated_px=int(tot), hero_palette=round(on_hero / max(1, tot), 4), accent_family=round(on_acc / max(1, tot), 4),
                       other=round(other / max(1, tot), 4), worst_frame=worst[1], ok=bool(other / max(1, tot) < 0.02))
    # 6) duration
    R["duration"] = dict(video_s=vdur, audio_s=adur, target_s=TOTAL, ok=abs(vdur - TOTAL) < 1 / FPS and abs(adur - TOTAL) < 0.03)
    # 7) audio: no vocal track (user's decision) -> SFX bus level
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "48000", "-f", "s16le", "-"], capture_output=True).stdout
    pcm = np.frombuffer(raw, np.int16).astype(float) / 32768
    peak = 20 * math.log10(np.abs(pcm).max() + 1e-9); rms = 20 * math.log10(np.sqrt((pcm ** 2).mean()) + 1e-9)
    R["audio"] = dict(note="no vocal track used (user decision); SFX only, kept low so a vocal added later stays on top",
                      sfx_peak_dbfs=round(peak, 1), sfx_rms_dbfs=round(rms, 1), ok=peak < -12)
    # 8) subtitles / on-screen text inside the frame and the platform safe zone
    boxes = {s["id"]: OV.plate_box(s["id"]) for s in SCENES if s["id"] != 16}
    bad = {k: v for k, v in boxes.items() if not (60 <= v[0] and v[2] <= 1020 and 220 <= v[1] and v[3] <= 1560)}
    R["subtitles_in_frame"] = dict(plate_x=[round(min(v[0] for v in boxes.values())), round(max(v[2] for v in boxes.values()))],
                                   plate_y=[round(min(v[1] for v in boxes.values())), round(max(v[3] for v in boxes.values()))],
                                   outside=list(bad), ok=not bad)
    R["all_ok"] = all(v["ok"] for v in R.values() if isinstance(v, dict) and "ok" in v)
    with open(os.path.join(BUILD, "qa_results.json"), "w") as fh: json.dump(R, fh, indent=1, ensure_ascii=False, default=str)
    print(json.dumps(R, indent=1, ensure_ascii=False, default=str))

if __name__ == "__main__":
    main(sys.argv[1])
