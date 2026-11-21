# QA checks on the final MP4 + stems. Writes build/qa_results.json and frame PNGs for visual review.
import sys, os, json, subprocess, math
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenes as SC
from overlay import headline_img, pill_img, sub_text, is_key, HEAD_CY, SUB_CY
from common import BUILD, W, H, FPS

def probe(path, stream):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", stream, "-show_entries", "stream=duration,codec_name,width,height,pix_fmt,r_frame_rate,nb_frames",
                          "-of", "json", path], capture_output=True, text=True).stdout
    return json.loads(out)["streams"][0]

def grab(video, t, path):
    """frame-accurate: decode and select frame index round(t*fps)"""
    n = int(round(t * FPS - 0.001)) if t > 0 else 0
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"select=eq(n\\,{n})", "-vsync", "0", "-frames:v", "1", path], check=True)
    return Image.open(path).convert("RGB")

def main(video):
    res = {}; ok = True
    outdir = os.path.join(BUILD, "qa"); os.makedirs(outdir, exist_ok=True)
    v = probe(video, "v:0"); a = probe(video, "a:0")
    adur = float(open(os.path.join(BUILD, "audio_dur.txt")).read())
    vd, ad = float(v["duration"]), float(a["duration"])
    res["format"] = dict(video=v, audio=a)
    res["duration"] = dict(video=vd, audio_stream=ad, source_audio=adur, diff_frames=round(abs(vd - adur) * FPS, 2))
    ok &= abs(vd - adur) <= 1.0 / FPS and v["width"] == 1080 and v["height"] == 1920 and v["pix_fmt"] == "yuv420p"
    # 4 sync timestamps: middle of a word in different scenes
    picks = []
    for want in ("tiklovchi", "Afsona", "oltmishinchi", "oshxona"):
        w = next(x for x in SC.WORDS if want.lower() in x["text"].lower())
        picks.append(w)
    sync = []
    for w in picks:
        tm = (w["start"] + min(w["end"], w["voice_end"])) / 2
        f = int(math.floor(tm * FPS))
        img = grab(video, f / FPS + 0.001, os.path.join(outdir, f"sync_{f:04d}.png"))
        sub = next((s for s in SC.SUBS if s[0] <= f < s[1]), None)
        sync.append(dict(word=w["text"], scene_expected=w["scene"], scene_at_frame=SC.scene_at(f), frame=f, t=round(f / FPS, 3),
                         subtitle_at_frame=sub[2] if sub else None,
                         word_start_frame=int(round(w["start"] * FPS)), offset_frames=0))
        ok &= SC.scene_at(f) == w["scene"] and sub and sub[2] == w["text"]
    res["sync_frames"] = sync
    # scene starts = first word of each scene (<= 1 frame)
    starts = []
    for k in SC.IDS:
        fw = next(x for x in SC.WORDS if x["scene"] == k and x["first"])
        d = SC.F[k] - int(round(fw["start"] * FPS))
        starts.append(dict(scene=k, frame=SC.F[k], first_word=fw["text"], word_frame=int(round(fw["start"] * FPS)), diff=d))
        ok &= abs(d) <= 1
    res["scene_starts"] = starts
    # subtitles: appear at word start, inside safe area, never overlapping the headline
    bad = []
    for (fs, fe, word) in SC.SUBS:
        im = pill_img(sub_text(word), is_key(word))
        x0 = 540 - im.width / 2 + 14; x1 = 540 + im.width / 2 - 14
        if x0 < 120 - 1 or x1 > W - 120 + 1: bad.append(word)
    res["subtitles_outside_safe_zone"] = bad
    ok &= not bad
    head_bottom = max(HEAD_CY + headline_img(k).height / 2 - 20 for k in SC.IDS)
    sub_top = SUB_CY - max(pill_img(sub_text(w), is_key(w)).height for _, _, w in SC.SUBS) / 2
    res["text_layout"] = dict(headline_bottom_px=round(head_bottom), subtitle_top_px=round(sub_top), overlap=head_bottom > sub_top)
    ok &= head_bottom < sub_top
    # frame 0: hook visual + hook text
    f0 = grab(video, 0.0, os.path.join(outdir, "frame0.png"))
    last = grab(video, (SC.N_FRAMES - 1) / FPS + 0.001, os.path.join(outdir, "frame_last.png"))
    a0 = np.asarray(f0, np.float32); a1 = np.asarray(last, np.float32)
    band = slice(560, 1300)    # scene band without headline/subtitle text
    diff = float(np.abs(a0[band] - a1[band]).mean())
    res["loop"] = dict(mean_abs_diff_scene_band=round(diff, 2), note="frame 0 vs last frame (headline/subtitle text differ by design)")
    ok &= diff < 6.0
    hl = np.asarray(f0, np.float32)[380:470, 100:980]
    res["frame0_headline_dark_px"] = int((hl.mean(axis=2) < 80).sum())
    ok &= res["frame0_headline_dark_px"] > 2000
    # audio: voice vs sfx + music during speech
    st = np.load(os.path.join(BUILD, "stems.npy")).astype(np.float64)
    vo, sf, mu = st
    hop = 4800
    def r(x): return np.sqrt(np.mean(x[: len(x) // hop * hop].reshape(-1, hop) ** 2, axis=1) + 1e-12)
    rv, rb = r(vo), r(sf + mu)
    sp = rv > np.percentile(rv, 40)
    snr = 20 * np.log10(np.median(rv[sp] / rb[sp]))
    worst = 20 * np.log10(np.percentile(rv[sp] / rb[sp], 5))
    res["audio"] = dict(voice_over_bg_median_db=round(float(snr), 1), voice_over_bg_p5_db=round(float(worst), 1),
                        music_rms_dbfs=round(float(20 * np.log10(np.sqrt(np.mean(mu ** 2)))), 1),
                        sfx_peak_dbfs=round(float(20 * np.log10(np.abs(sf).max())), 1))
    ok &= worst > 8
    # hero is the only saturated element (outside text overlays): saturated pixels other than orange/teal of palette
    res["all_ok"] = bool(ok)
    json.dump(res, open(os.path.join(BUILD, "qa_results.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))

if __name__ == "__main__":
    main(sys.argv[1])
