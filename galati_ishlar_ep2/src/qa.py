"""QA checks for the final MP4. Usage: qa.py final.mp4 timing.json frames_dir audio_dir textboxes.json vo.wav outdir"""
import json, sys, os, math, subprocess
import numpy as np, scipy.io.wavfile as wf, scipy.signal as ss
from PIL import Image, ImageDraw

FPS, W, H = 30, 1080, 1920
SAFE = (60, 210, 1020, 1560)


def fidx(t): return int(math.floor(t * FPS + 0.5))


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_frames,duration,sample_rate,channels,start_time",
                          "-show_entries", "format=duration", "-of", "json", path], capture_output=True, text=True).stdout
    return json.loads(out)


def frame_at(path, t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", path, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3)


def all_frames_small(path, w=54, h=96):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)


def lufs_blocks(x, sr, blk=0.4, hop=0.1):
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1, -1.99004745483398, 0.99007225036621]
    y = ss.lfilter(b2, a2, ss.lfilter(b1, a1, x, axis=0), axis=0)
    B, Hn = int(blk * sr), int(hop * sr)
    z = np.array([np.sum(np.mean(y[i:i + B] ** 2, 0)) for i in range(0, len(y) - B, Hn)])
    return -0.691 + 10 * np.log10(z + 1e-12)


def main(mp4, timing, frames_dir, audio_dir, boxes_json, vo, outdir):
    os.makedirs(outdir, exist_ok=True)
    T = json.load(open(timing)); SC = T["scenes"]; words = T["words"]
    res = []
    def check(name, ok, detail): res.append(dict(check=name, ok=bool(ok), detail=detail)); print(("PASS " if ok else "FAIL ") + name + " :: " + detail)

    # ---- format
    p = probe(mp4); v = [s for s in p["streams"] if s.get("width")][0]; a = [s for s in p["streams"] if s.get("sample_rate")][0]
    dur = float(p["format"]["duration"])
    check("format", v["codec_name"] == "h264" and v["width"] == 1080 and v["height"] == 1920 and v["pix_fmt"] == "yuv420p"
          and v["r_frame_rate"] == "30/1" and a["codec_name"] == "aac",
          f"{v['codec_name']} {v['width']}x{v['height']} {v['pix_fmt']} {v['r_frame_rate']} fps, audio {a['codec_name']} {a['sample_rate']} Hz {a['channels']}ch")

    # ---- source frame matcher
    srcs = {}
    for i in range(1, 23):
        im = Image.open(os.path.join(frames_dir, f"frame_{i:02d}.png")).convert("L")
        srcs[i] = im
    def best_match(fr):
        g = Image.fromarray(fr).convert("L")
        # compare against each source cropped by the scene's own scale range: use centre crops 1.08..1.8
        best = (-2, None)
        q = np.asarray(g.resize((54, 96), Image.BILINEAR), np.float32)[10:70]   # upper part, above subtitles
        q = (q - q.mean()) / (q.std() + 1e-6)
        for i, im in srcs.items():
            for s in (1.1, 1.2, 1.35, 1.65):
                for (u, vv) in ((0.5, 0.5), (0.4, 0.45), (0.6, 0.55), (0.5, 0.6), (0.4, 0.5)):
                    ww, hh = im.width / s, im.height / s
                    x0 = min(max(u * im.width - ww / 2, 0), im.width - ww); y0 = min(max(vv * im.height - hh / 2, 0), im.height - hh)
                    c = np.asarray(im.crop((x0, y0, x0 + ww, y0 + hh)).resize((54, 96), Image.BILINEAR), np.float32)[10:70]
                    c = (c - c.mean()) / (c.std() + 1e-6)
                    r = float((q * c).mean())
                    if r > best[0]: best = (r, i)
        return best

    def scene_at(t):
        n = fidx(t)
        for s in SC:
            if fidx(s["start"]) <= n < fidx(s["end"]): return s
        return SC[-1]

    def word_at(t):
        cur = None
        for w in words:
            if fidx(w["t0"]) <= fidx(t) and t <= w["t1"] + 0.6: cur = w
        return cur

    # ---- 1/2: frames at fixed times
    shots = []
    for t in (0.0, 7.5, 24.5, 44.0):
        fr = frame_at(mp4, t); Image.fromarray(fr).save(os.path.join(outdir, f"qa_{t:05.1f}.png"))
        s = scene_at(t); r, bi = best_match(fr); w = word_at(t)
        detail = f"t={t}: scene {s['id']} expects frame_{s['frame']:02d}, best image match frame_{bi:02d} (r={r:.2f})"
        ok = bi == s["frame"]
        if w:
            # amber pixels where the current word should be highlighted (subtitle band)
            band = fr[1330:1510].astype(int)
            amber = ((abs(band[..., 0] - 224) < 40) & (abs(band[..., 1] - 164) < 40) & (abs(band[..., 2] - 88) < 50)).sum()
            detail += f"; spoken word '{w['text']}' ({w['t0']:.2f}-{w['t1']:.2f}s), highlighted amber px={amber}"
            ok = ok and amber > 300
        check(f"frame@{t}s scene+subtitle", ok, detail)
        shots.append(fr)
    fr0 = shots[0]; fr1 = frame_at(mp4, 1 / FPS)
    hook = fr0[400:545, 200:880]; white = ((hook > 235).all(-1)).sum()
    motion = np.abs(fr0[600:1300].astype(int) - fr1[600:1300].astype(int)).mean()
    check("frame 0 = hook in motion + 'Bu qiz kim?'", white > 3000 and motion > 0.5,
          f"white text px in hook area={white}, mean abs diff frame0->frame1={motion:.2f}")
    sheet = Image.new("RGB", (4 * 360, 640))
    for k, fr in enumerate(shots): sheet.paste(Image.fromarray(fr).resize((360, 640)), (k * 360, 0))
    sheet.save(os.path.join(outdir, "qa_frames_sheet.jpg"), quality=88)

    # ---- 3: voice clips hold whole sentences
    sr, x = wf.read(vo); x = x.astype(np.float64)
    hop = int(sr * 0.005); n = len(x) // hop
    rel = 20 * np.log10(np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, 1)) + 1e-9); rel -= rel.max()
    bad = []
    for c in T["clips"]:
        L = T["lines"][str(c["line"])]
        e0 = rel[int(c["src0"] / 0.005):int(c["src0"] / 0.005) + 3].max()      # first 15 ms
        e1 = rel[int(c["src1"] / 0.005) - 3:int(c["src1"] / 0.005)].max()      # last 15 ms
        lw = [w for w in words if w["line"] == c["line"]]
        inside = all(c["src0"] <= w["src_s"] and w["src_e"] <= c["src1"] for w in lw)
        if not (e0 < -38 and e1 < -38 and inside and c["src0"] <= L["on"] - 0.02 and c["src1"] >= L["off"] + 0.05):
            bad.append((c["line"], round(e0, 1), round(e1, 1), inside))
    check("voice clips hold whole sentences", not bad,
          f"8 clips cut inside pauses (edges below -38 dB, all words inside, >=20 ms pre-roll, >=50 ms tail); problems={bad}")
    ov = [(a["line"], b["line"]) for a, b in zip(T["clips"], T["clips"][1:]) if a["t1"] > b["t0"]]
    check("clips never overlap", not ov, f"overlaps={ov}")

    # ---- decode final audio
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-f", "f32le", "-ac", "2", "-ar", "48000", "-"], capture_output=True).stdout
    m = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64); asr = 48000
    adur = len(m) / asr
    w = int(0.2 * asr); k = len(m) // w
    rms = 20 * np.log10(np.sqrt((m[:k * w] ** 2).mean(1).reshape(k, w).mean(1)) + 1e-12)
    pre = rms[: int((adur - 1.0) / 0.2)]
    check("no digital silence before final fade", pre.min() > -60,
          f"min RMS of any 200 ms window before the fade = {pre.min():.1f} dBFS (at {pre.argmin() * 0.2:.1f}s)")

    # ---- 4: silent scenes carry ambience + sfx
    meta = json.load(open(os.path.join(audio_dir, "audio_meta.json")))
    ev_t = [e[0] for e in meta["events"]]
    rows = []; okall = True
    for sid in (7, 8, 9, 10, 12, 16, 17, 18, 19, 20, 21, 22):
        s = [q for q in SC if q["id"] == sid][0]
        seg = m[int(s["start"] * asr):int(s["end"] * asr)]
        r = 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-12)
        ne = sum(1 for t in ev_t if s["start"] - 0.05 <= t < s["end"])
        need_ev = sid not in (10,)   # scene 10 asks only for room tone + fire crackle (bed)
        ok = r > -50 and (ne > 0 or not need_ev)
        okall &= ok; rows.append(f"{sid}:{r:.0f}dB/{ne}sfx")
    check("silent scenes have ambience + sfx", okall, "scene:rms/sfx-events " + ", ".join(rows))

    # ---- 5: fade
    def seg_db(a, b): s = m[int(a * asr):int(b * asr)]; return 20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-12)
    l0, l1, l2 = seg_db(adur - 1.25, adur - 1.05), seg_db(adur - 0.55, adur - 0.45), seg_db(adur - 0.03, adur)
    check("audio ends with >=1.0 s fade", l0 - l1 > 2 and l1 - l2 > 15 and l2 < -55,
          f"level before fade {l0:.1f} dB -> mid-fade {l1:.1f} dB -> last 30 ms {l2:.1f} dB")

    # ---- 6: duration
    last = max(w_["t1"] for w_ in words)
    check("duration", 49.0 <= dur <= 51.5 and dur >= last + 1.2 and abs(adur - dur) < 0.05,
          f"video {dur:.3f}s, audio {adur:.3f}s, last spoken word ends {last:.3f}s (+1.2 = {last + 1.2:.3f}s)")

    # ---- 7: voice vs everything else (K-weighted, during speech)
    st = {}
    for name in ("voice", "amb", "sfx", "music"):
        _, y = wf.read(os.path.join(audio_dir, f"stem_{name}.wav")); st[name] = y.astype(np.float64)
    lv = lufs_blocks(st["voice"], 48000); lo = lufs_blocks(st["amb"] + st["sfx"] + st["music"], 48000)
    lm = lufs_blocks(st["music"], 48000); ls_ = lufs_blocks(st["sfx"], 48000)
    act = lv > -35
    sp = lv > np.median(lv[act]) - 6          # 400 ms blocks that are mostly speech (not pause edges)
    d = lv[sp] - lo[sp]
    check("voice clearly above sfx + music", np.median(d) > 12 and np.percentile(d, 5) > 8,
          f"speech blocks ({sp.sum()}): voice - (amb+sfx+music) median {np.median(d):.1f} LU, 5th pct {np.percentile(d, 5):.1f} LU; "
          f"music median {np.median(lv[sp] - lm[sp]):.1f} LU under voice; sfx peak momentary {ls_.max():.1f} vs voice {lv.max():.1f} LUFS")

    # ---- 8: safe zone + image edges
    boxes = json.load(open(boxes_json))
    out = [(n, b) for n, bs in boxes.items() for b in bs if b[0] < SAFE[0] or b[1] < SAFE[1] or b[2] > SAFE[2] or b[3] > SAFE[3]]
    check("text inside safe zone", not out, f"{sum(len(b) for b in boxes.values())} text boxes checked against x{SAFE[0]}-{SAFE[2]}, y{SAFE[1]}-{SAFE[3]}; outside={out[:3]}")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import render
    render.init(frames_dir, timing)
    mins = 9; worst = None; edge = 0
    for nfr in range(int(round(T["duration"] * FPS))):
        s = render.scene_at(nfr)
        if s["frame"] is None: continue
        tl = nfr / FPS - s["start"]; d_ = s["end"] - s["start"]
        im = render.src(s["frame"]) if s["frame"] not in render._src else render._src[s["frame"]]
        c = render.cam_for(s["id"], tl, d_, im)
        if c.s < mins: mins, worst = c.s, nfr
        if c.x0 < -1e-6 or c.y0 < -1e-6 or c.x0 + W * c.k > c.iw + 1e-6 or c.y0 + H * c.k > c.ih + 1e-6: edge += 1
    check("no image edge visible", mins >= 1.08 and edge == 0, f"minimum camera scale {mins * 100:.1f}% (frame {worst}); crop windows outside image: {edge}")

    # ---- 9: Davomi bor / Obuna timing
    dav = [w_ for w_ in words if w_["line"] == 8][0]; obu = [w_ for w_ in words if w_["line"] == 8 and w_["text"].lower().startswith("obuna")][0]
    def first_with(pred):
        for nfr in sorted(int(k) for k in boxes):
            if any(pred(b) for b in boxes[str(nfr)]): return nfr
    f_dav = first_with(lambda b: 700 < (b[1] + b[3]) / 2 < 820 and b[2] - b[0] > 400)
    f_cta = first_with(lambda b: 860 < (b[1] + b[3]) / 2 < 950)
    check("'Davomi bor' on 'Davomi', icon on 'obuna'", f_dav == fidx(dav["t0"]) and f_cta == fidx(obu["t0"]),
          f"'Davomi' spoken {dav['t0']:.3f}s (frame {fidx(dav['t0'])}) -> text frame {f_dav}; 'obuna' spoken {obu['t0']:.3f}s (frame {fidx(obu['t0'])}) -> icon frame {f_cta}")

    # ---- sync: detected cuts vs planned scene starts, subtitle words
    sm = all_frames_small(mp4)
    diff = np.abs(np.diff(sm, axis=0)).mean((1, 2))
    planned = [fidx(s["start"]) for s in SC[1:] if not (s["frame"] == [q for q in SC if q["id"] == s["id"] - 1][0]["frame"])]
    planned += [fidx(SC[14]["start"])]  # scene 15 is a recrop of frame_14: still a hard cut
    planned = sorted(set(planned))
    det = []
    for pf in planned:
        win = diff[max(0, pf - 4):pf + 3]; det.append(max(0, pf - 4) + int(win.argmax()) + 1)
    offs = [d_ - p_ for d_, p_ in zip(det, planned)]
    check("scene cuts land on plan (<=1 frame)", max(abs(o) for o in offs) <= 1,
          f"{len(planned)} cuts, offsets in frames: {offs}")
    sow = [(s["id"], s["sow"], s["start"]) for s in SC if s.get("sow")]
    rows = []
    for sid, wtxt, st_ in sow:
        w_ = [q for q in words if q["text"].lower().startswith(wtxt.lower()[:4])][0]
        rows.append(f"scene {sid} '{wtxt}': cut frame {fidx(st_)} vs word frame {fidx(w_['t0'])}")
    check("starts_on_word cuts", all(fidx(s["start"]) == fidx([q for q in words if q["text"].lower().startswith(s["sow"].lower()[:4])][0]["t0"]) for s in SC if s.get("sow")), "; ".join(rows))
    json.dump(res, open(os.path.join(outdir, "qa_results.json"), "w"), ensure_ascii=False, indent=1)
    print(f"\n{sum(r['ok'] for r in res)}/{len(res)} checks passed")
    return all(r["ok"] for r in res)


if __name__ == "__main__":
    ok = main(*sys.argv[1:8]); sys.exit(0 if ok else 1)
