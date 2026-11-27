# QA for the final MP4: every check from the brief, written to qa_results.json
import json, os, sys, subprocess, re
import numpy as np
import cv2
from scipy.io import wavfile
from config import *
import render as R

def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout

def probe(mp4):
    j = json.loads(sh(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-count_frames", "-of", "json", mp4]))
    v = [s for s in j["streams"] if s["codec_type"] == "video"][0]
    a = [s for s in j["streams"] if s["codec_type"] == "audio"][0]
    return j["format"], v, a

def frame_at(mp4, i):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-vf", f"select=eq(n\\,{i})", "-vframes", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3)

def psnr(a, b):
    m = np.mean((a.astype(np.float32) - b.astype(np.float32)) ** 2)
    return 99.0 if m == 0 else 10 * np.log10(255 ** 2 / m)

def edges(g):
    g = cv2.GaussianBlur(g, (0, 0), 1.0)
    return np.sqrt(cv2.Sobel(g, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(g, cv2.CV_32F, 0, 1) ** 2)

LOWSRC = {}
def classify_cam(img, t, ignore=()):
    """which Flow frame is on screen: each candidate is warped with the camera the renderer
    uses at time t and compared on edge structure (robust to light effects and grades)"""
    s, _ = R.shot_at(t)
    cp = s.cam(t)
    M = R.cam_matrix(cp.get("z", 1.06), cp.get("cx", 0.5), cp.get("cy", 0.5), cp.get("r", 0.0), cp.get("dx", 0.0), cp.get("dy", 0.0))
    Ml = M.copy(); Ml[:, 2] /= 4
    g = edges(cv2.cvtColor(cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY).astype(np.float32))
    m = np.ones_like(g, bool)
    for y0, y1 in ignore: m[y0 // 4:y1 // 4] = False
    best = None
    for k in [f"F{n:02d}" for n in range(1, 22)]:
        if k not in LOWSRC:
            LOWSRC[k] = cv2.cvtColor(cv2.resize(R.SRC(k), (R.SW // 4, R.SH // 4), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY).astype(np.float32)
        ref = edges(cv2.warpAffine(LOWSRC[k], Ml, (W // 4, H // 4), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT))
        a, b = g[m] - g[m].mean(), ref[m] - ref[m].mean()
        r = float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-6))
        if best is None or r > best[1]: best = (k, r)
    return best

TEXT_BANDS = ((330, 790), (1320, 1480), (700, 940))

THUMBS = None
def classify(img):
    """which Flow frame is on screen (max normalized correlation on small grayscale thumbnails)"""
    global THUMBS
    if THUMBS is None:
        THUMBS = {}
        for k in [f"F{n:02d}" for n in range(1, 22)]:
            o = R.load_src(k)
            h, w = o.shape[:2]
            c = o[int(h * 0.06):int(h * 0.94), int(w * 0.06):int(w * 0.94)]
            THUMBS[k] = cv2.resize(cv2.cvtColor(c, cv2.COLOR_RGB2GRAY), (36, 64), interpolation=cv2.INTER_AREA).astype(np.float32)
    g = cv2.resize(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY), (36, 64), interpolation=cv2.INTER_AREA).astype(np.float32)
    g[38:52] = np.nan          # ignore the subtitle band
    best = None
    for k, t in THUMBS.items():
        m = ~np.isnan(g)
        a, b = g[m] - g[m].mean(), t[m] - t[m].mean()
        r = float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-6))
        if best is None or r > best[1]: best = (k, r)
    return best

def spoken_at(tj, t):
    """word being spoken at t, judged from timing.json alone: from its onset to its end
    (+0.12 s release), or up to the next word when the gap is shorter than 0.5 s"""
    for L in tj["lines"].values():
        ws = L["words"]
        for k, w in enumerate(ws):
            nxt = ws[k + 1]["start"] if k + 1 < len(ws) else None
            end = w["end"] + 0.15 if nxt is None else (nxt if nxt - w["end"] < 0.5 else w["end"] + 0.12)
            if w["start"] <= t < end: return w["text"]
    return None

def expected_at(t):
    for k, a, b, sid in shot_list():
        if a <= t + 1e-9 < b: return k, sid
    return shot_list()[-1][0], 10

def main(mp4, out_json):
    res = {"checks": []}
    def check(name, ok, detail):
        res["checks"].append({"check": name, "pass": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name + " — " + (detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False, default=float)))

    tj = json.load(open(os.path.join(WORK, "timing.json")))
    fmt, v, a = probe(mp4)
    nf = int(v.get("nb_read_frames", 0))
    vd = float(v["duration"]); ad = float(a["duration"]); fd = float(fmt["duration"])
    ok = (nf == NFRAMES and abs(vd - 50.0) < 1e-3 and abs(fd - 50.0) < 0.03 and abs(ad - 50.0) < 0.03
          and v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p" and a["codec_name"] == "aac"
          and v["width"] == W and v["height"] == H and v["r_frame_rate"] == "30/1")
    check("duration 50.0 s, 1080x1920, 30 fps, h264/yuv420p, aac", ok,
          dict(frames=nf, video_s=vd, audio_s=ad, container_s=fd, v=v["codec_name"], pix=v["pix_fmt"], fps=v["r_frame_rate"], a=a["codec_name"]))

    # --- frame 0: hook visual in motion + hook text
    f0, f1 = frame_at(mp4, 0), frame_at(mp4, 3)
    cls0 = classify_cam(f0, 0.0, TEXT_BANDS)
    hx0, hy0, hx1, hy1 = [int(x) for x in R.hook_box()]
    reg = f0[hy0:hy1, hx0:hx1].astype(np.int32)
    txt = int(((reg[..., 0] > 225) & (reg[..., 1] > 215) & (reg[..., 2] > 205)).sum())
    motion = float(np.abs(f0.astype(np.int16) - f1.astype(np.int16)).mean())
    check("frame 0.0 s shows F01 in motion with \"Bu bazada nima bor?\"", cls0[0] == "F01" and txt > 5000 and motion > 1.0,
          dict(frame0_is=cls0[0], corr=round(cls0[1], 3), hook_text_px=txt, motion_frame0_to_3=round(motion, 2)))

    # --- QA frames: scene + subtitle vs spoken word
    ovl = R.Overlay()
    shots_dir = os.path.join(os.path.dirname(out_json), "qa_frames"); os.makedirs(shots_dir, exist_ok=True)
    rows = []
    allok = True
    for t in (1.0, 6.0, 16.5, 38.5, 48.5):
        i = fr(t)
        img = frame_at(mp4, i)
        cv2.imwrite(os.path.join(shots_dir, f"qa_{t:05.1f}s.png"), img[:, :, ::-1])
        exp_k, sid = expected_at(t)
        got = classify_cam(img, t, TEXT_BANDS)
        ref = R.render_frame(i)
        p = psnr(img, ref)
        spoken = spoken_at(tj, t)
        shown, active = None, None
        for f0_, f1_, ch in ovl.win:
            if f0_ <= i < f1_ and not ovl.in_pause(i):
                shown = " ".join(w["text"] for w in ch)
                act = 0
                for k, w in enumerate(ch):
                    if i >= fr(w["start"]): act = k
                active = ch[act]["text"]
        ok = got[0] == exp_k and p > 30 and (active == spoken)
        allok &= ok
        rows.append(dict(t=t, scene=sid, frame_expected=exp_k, frame_seen=got[0], psnr_vs_renderer=round(p, 1),
                         spoken=spoken, subtitle=shown, highlighted=active))
    check("QA frames 1.0/6.0/16.5/38.5/48.5: scene and subtitle match the spoken word", allok, rows)

    # --- every shot change lands on its start frame (and the frame before still shows the previous shot)
    bad = []; sl = shot_list()
    for n, (k, a_, b_, sid) in enumerate(sl):
        i = fr(a_)
        prev_k = sl[n - 1][0] if n else None
        img = frame_at(mp4, i)
        got = ("BLACK", 1.0) if k == "BLACK" and img.mean() < 8 else classify_cam(img, a_, TEXT_BANDS)
        if prev_k is None:
            pb = None
        else:
            imb = frame_at(mp4, i - 1)
            pb = ("BLACK", 1.0) if prev_k == "BLACK" and imb.mean() < 8 else classify_cam(imb, (i - 1) / FPS, TEXT_BANDS)
        if got[0] != k or (pb is not None and pb[0] != prev_k):
            bad.append(dict(shot=k, t=a_, seen=got[0], frame_before=pb and pb[0], expected_before=prev_k))
    check("scene changes at their start times", not bad, bad or f"all {len(sl)} shots start on their frame; the frame before shows the previous shot")

    # --- voice line starts (cross-correlation of each cut line against the decoded MP4 audio)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    mix = np.frombuffer(raw, np.float32).astype(np.float64)
    vr, src = wavfile.read(VOICE_WAV); src = src.astype(np.float64)
    if src.ndim > 1: src = src.mean(1)
    rows = []; ok = True
    for ln, L in sorted(tj["lines"].items(), key=lambda kv: int(kv[0])):
        a0, b0 = LINE_CUTS[int(ln)]
        tpl = src[int(a0 * SR):int(min(b0, a0 + 0.8) * SR)]
        vs = L["voice_start"]
        lo, hi = int((vs - 0.25) * SR), int((vs + 0.25) * SR) + len(tpl)
        seg = mix[lo:hi]
        c = np.correlate(seg, tpl, "valid")
        nrm = np.sqrt(np.convolve(seg ** 2, np.ones(len(tpl)), "valid")) * np.sqrt((tpl ** 2).sum()) + 1e-9
        k = int(np.argmax(c / nrm))
        got = (lo + k) / SR
        off = (got - vs) * FPS
        ok &= abs(off) <= 1.0
        rows.append(dict(line=int(ln), voice_start=vs, measured=round(got, 4), offset_frames=round(off, 3)))
    check("every voice line starts at its voice_start (±1 frame)", ok, rows)

    # --- word highlight frames
    bad = []
    for f0_, f1_, ch in ovl.win:
        for k, w in enumerate(ch):
            fi = fr(w["start"])
            if not (f0_ <= fi < f1_): bad.append(w["text"]); continue
            act = max(j for j, x in enumerate(ch) if fi >= fr(x["start"]))
            if act != k: bad.append(w["text"])
    check("each word is highlighted on the frame it is spoken", not bad, bad or "all words: highlight frame = round(start x 30)")

    # --- subtitle text equals script text
    def plain(s): return s.replace("ʻ", "'").replace("ʼ", "'")
    ok = True; det = {}
    for ln in sorted(tj["lines"], key=int):
        shown = " ".join(" ".join(w["text"] for w in ch) for f0_, f1_, ch in ovl.win if ch[0] in tj["lines"][ln]["words"])
        ok &= plain(shown) == SCRIPT[int(ln)][1]
        det[ln] = shown
    yr = [w for w in tj["lines"]["1"]["words"] if w["text"].startswith("1980")][0]
    ok &= yr["text"] == "1980-yil."
    det["1980-yil"] = f"one word {yr['start']:.2f}-{yr['end']:.2f} s (whisper: {' '.join(tj['lines']['1']['whisper'][:3])})"
    check("subtitle text equals the script word for word; \"1980-yil\" is one word", ok, det)

    # --- voice clearly audible
    d = os.path.join(WORK, "audio")
    _, vo = wavfile.read(os.path.join(d, "stem_voice.wav")); _, bg = wavfile.read(os.path.join(d, "stem_bg.wav"))
    bg = bg.mean(1)
    rows = []; ok = True
    for ln, L in sorted(tj["lines"].items(), key=lambda kv: int(kv[0])):
        i0, i1 = int(L["words"][0]["start"] * SR), int(L["words"][-1]["end"] * SR)
        rv = 20 * np.log10(np.sqrt(np.mean(vo[i0:i1] ** 2)) + 1e-9)
        rb = 20 * np.log10(np.sqrt(np.mean(bg[i0:i1] ** 2)) + 1e-9)
        ok &= rv - rb >= 15
        rows.append(dict(line=int(ln), voice_rms_db=round(rv, 1), music_sfx_rms_db=round(rb, 1), margin_db=round(rv - rb, 1)))
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", subprocess.run(["ffmpeg", "-hide_banner", "-i", mp4, "-af", "ebur128", "-f", "null", "-"],
                                                         capture_output=True, text=True).stderr)[-1]
    check("voice clearly audible over sfx and music (>= 15 dB)", ok, dict(lines=rows, integrated_lufs=float(lufs)))

    # --- safe zone
    boxes = [R.subtitle_box(ch) for _, _, ch in ovl.win]
    SAFE = (60, 220, 960, 1500)       # left, top, right (clear of the Reels action column), bottom (above caption/UI)
    worst = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
    hb = R.hook_box()
    ok = worst[0] >= SAFE[0] and worst[1] >= SAFE[1] and worst[2] <= SAFE[2] and worst[3] <= SAFE[3] \
        and hb[0] >= 0 and hb[2] <= W and hb[1] >= SAFE[1]
    check("no subtitle outside the frame or the safe zone", ok,
          dict(subtitle_extent=[round(x) for x in worst], safe_zone=SAFE, hook_box=[round(x) for x in hb]))

    # --- "Davomi bor" on the spoken word
    dav = [w for w in tj["lines"]["5"]["words"] if w["script"].startswith("Davomi")][0]
    fi = fr(dav["start"])
    a_, b_ = frame_at(mp4, fi - 1), frame_at(mp4, fi)
    y0 = R.CTA_Y - 90; y1 = R.CTA_Y + 90
    def white(img): r = img[y0:y1].astype(np.int32); return int(((r[..., 0] > 225) & (r[..., 1] > 215) & (r[..., 2] > 205)).sum())
    ok = ovl.cta_f == fi and white(a_) < 500 and white(b_) > 3000
    check("\"Davomi bor\" appears exactly when \"Davomi\" is spoken", ok,
          dict(davomi_spoken=dav["start"], frame=fi, text_px_before=white(a_), text_px_on=white(b_), stays_to="50.0 s"))

    # --- laughter
    kul = bool(KULGI and os.path.exists(KULGI))
    src_txt = open(os.path.join(HERE, "audio.py")).read()
    ok = ("laugh" not in src_txt.replace("laughter only from kulgi.mp3", "").replace("never synthesized", "")) and not kul
    check("no synthesized laughter; laughter only from kulgi.mp3", ok,
          "kulgi.mp3 not attached -> scene 4 has no laughter sound" if not kul else "kulgi.mp3 used at 20.4 s")
    res["all_pass"] = all(c["pass"] for c in res["checks"])
    json.dump(res, open(out_json, "w"), ensure_ascii=False, indent=1, default=float)
    print("ALL PASS" if res["all_pass"] else "SOME CHECKS FAILED")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
