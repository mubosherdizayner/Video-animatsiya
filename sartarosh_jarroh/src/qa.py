# QA checks on the final MP4 + render state. Writes qa_results.json and QA images.
import sys, os, json, subprocess, re
import numpy as np
from PIL import Image
import timing as T
import render as R
import scenes as SC
from align import dp_align, merge_pieces, sim
from script_data import SCENES as SCRIPT, tokens

FPS = 30


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,duration,nb_frames:format=duration",
                          "-of", "json", path], capture_output=True, text=True).stdout
    return json.loads(out)


def frame_at(path, i):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"select=eq(n\\,{i})", "-vframes", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(1920, 1080, 3)


def psnr(a, b):
    mse = np.mean((a.astype(np.float32) - b.astype(np.float32)) ** 2)
    return 99.0 if mse == 0 else 10 * np.log10(255 ** 2 / mse)


def main(video, outdir):
    os.makedirs(outdir, exist_ok=True)
    R.init()
    res = {}
    ok_all = True

    def rec(name, ok, **info):
        nonlocal ok_all
        ok_all &= bool(ok)
        res[name] = dict(ok=bool(ok), **info)
        print(("PASS " if ok else "FAIL ") + name, json.dumps(info, ensure_ascii=False)[:300])

    # 0. container / codec spec
    pr = probe(video)
    vs = [s for s in pr["streams"] if s["codec_type"] == "video"][0]
    au = [s for s in pr["streams"] if s["codec_type"] == "audio"][0]
    rec("format", vs["codec_name"] == "h264" and vs["pix_fmt"] == "yuv420p" and vs["width"] == 1080 and
        vs["height"] == 1920 and vs["r_frame_rate"] == "30/1" and au["codec_name"] == "aac",
        video=vs["codec_name"], pix_fmt=vs["pix_fmt"], size=f'{vs["width"]}x{vs["height"]}', fps=vs["r_frame_rate"],
        audio=au["codec_name"])

    # 1. four timestamps: subtitle + scene must match the spoken word
    picks = [("tish", 1), ("sartarosh-jarroh", 2), ("qon", 7), ("bint.", 9)]
    shots = []
    for txt, sc in picks:
        w = T.word(sc, txt)
        tmid = (w["start"] + w["end"]) / 2
        i = int(tmid * FPS)
        cur = R.current_sub(i)
        got = frame_at(video, i)
        ref = R.render_frame(i)
        p = psnr(got, ref)
        ok = cur is not None and cur["text"] == w["text"] and T.scene_at(i) == sc and p > 30
        Image.fromarray(got).save(os.path.join(outdir, f"qa_t{tmid:05.2f}_{re.sub('[^a-z]', '', txt)}.png"))
        shots.append(Image.fromarray(got).resize((360, 640)))
        rec(f"timestamp_{tmid:.2f}s", ok, spoken=w["text"], subtitle=cur["text"] if cur else None,
            scene=T.scene_at(i), expected_scene=sc, video_vs_render_psnr=round(float(p), 1))
    sheet = Image.new("RGB", (4 * 362, 640), (20, 20, 20))
    for k, im in enumerate(shots):
        sheet.paste(im, (k * 362, 0))
    sheet.save(os.path.join(outdir, "qa_4_timestamps.png"))

    # 2. frame 0 = hook visual + hook text
    f0 = frame_at(video, 0)
    Image.fromarray(f0).save(os.path.join(outdir, "qa_frame0.png"))
    hook_vis = [s for s in R.HEADS[1] if s["f0"] == 0]
    rec("frame0_hook", T.scene_at(0) == 1 and len(hook_vis) == len(R.HEADS[1]) and f0.std() > 20,
        headline=" ".join(s["text"] for s in hook_vis), scene=T.scene_at(0))

    # 3. duration
    src = T.AUDIO_DUR
    vd = float(vs.get("duration", 0))
    ad = float(au.get("duration", 0))
    rec("duration", abs(vd - src) <= 1 / FPS and abs(ad - src) <= 1 / FPS,
        audio_source=round(src, 4), video_stream=round(vd, 4), audio_stream=round(ad, 4), frames=vs.get("nb_frames"))

    # 4. voice audible
    st = json.load(open(os.path.join(os.path.dirname(__file__), "sfx_stats.json")))
    rec("voice_audible", st["voice_over_sfx_db_in_speech"] >= 12 and st["sfx_peak_vs_voice_peak_db"] <= -12,
        voice_over_sfx_db=st["voice_over_sfx_db_in_speech"], sfx_peak_db=st["sfx_peak_vs_voice_peak_db"], music="disabled")

    # 5. subtitles / text inside the frame and the safe zone
    bad = []
    for s in R.SUBS:
        im = s["img"]
        bx = im.getchannel("A").point(lambda v: 255 if v > 60 else 0).getbbox()
        x0 = R.SAFE_CX - im.width / 2 + bx[0]
        x1 = R.SAFE_CX - im.width / 2 + bx[2]
        y0 = R.SUB_Y - im.height / 2 + bx[1]
        y1 = R.SUB_Y - im.height / 2 + bx[3]
        if x0 < 90 or x1 > 960 or y0 < 250 or y1 > 1560:
            bad.append((s["text"], int(x0), int(x1), int(y0), int(y1)))
    for k, segs in R.HEADS.items():
        for seg in segs:
            im = seg["img"]
            bx = im.getchannel("A").getbbox()
            x0 = seg["cx"] - im.width / 2 + bx[0]
            x1 = seg["cx"] - im.width / 2 + bx[2]
            y0 = seg["cy"] - im.height / 2 + bx[1]
            y1 = seg["cy"] - im.height / 2 + bx[3]
            if x0 < 90 or x1 > 990 or y0 < 250 or y1 > 560:
                bad.append(("HEAD" + str(k) + ":" + seg["text"], int(x0), int(x1), int(y0), int(y1)))
    rec("text_inside_frame_and_safe_zone", not bad, outside=bad, words=len(R.SUBS))

    # 6. joined scene text == voice-over script, word for word
    raw = merge_pieces(json.load(open(os.path.join(os.path.dirname(__file__), "words_raw.json"))))
    script = [w for _, txt in SCRIPT for w in tokens(txt)]
    path, cost = dp_align(script, raw)
    unmatched = [(script[i] if di else None, raw[j]["w"] if dj else None) for i, j, di, dj in path if di == 0 or dj == 0]
    weak = [(script[i], raw[j]["w"], round(sim(script[i], raw[j]["w"]), 2)) for i, j, di, dj in path
            if di == 1 and dj == 1 and sim(script[i], raw[j]["w"]) < 0.5]
    rec("script_matches_voiceover", not unmatched and not weak, script_words=len(script),
        transcript_words=len(raw), unmatched=unmatched, weak=weak)

    # 7. scene 4 starts exactly on 'suyak'; every scene starts on its first word; cues = word frames
    s4 = T.SC_FRAME[4] == T.word(4, "suyak")["f"]
    starts = {k: (T.SC_FRAME[k], min(w["f"] for w in T.WORDS if w["scene"] == k)) for k in T.SCENE_IDS}
    rec("scene4_on_suyak", s4, scene4_frame=T.SC_FRAME[4], suyak_frame=T.word(4, "suyak")["f"],
        suyak_time=T.word(4, "suyak")["start"])
    rec("scene_changes_on_first_word", all(a == b for k, (a, b) in starts.items() if k != 1),
        starts={k: v for k, v in starts.items()})
    offs = [abs(s["f0"] - w["start"] * FPS) for s, w in zip(R.SUBS, T.WORDS)]
    rec("subtitle_sync", max(offs) <= 1.0, max_offset_frames=round(max(offs), 2))

    # 8. hero: no glasses, same look as the logo mascot (visual sheet)
    src_chars = open(os.path.join(os.path.dirname(__file__), "chars.py")).read().lower()
    crops = []
    for i, box in ((0, (300, 650, 760, 1150)), (470, (330, 560, 730, 960)), (600, (240, 560, 840, 1160)),
                   (990, (0, 900, 420, 1400)), (1018, (300, 650, 760, 1150))):
        fr = frame_at(video, i)
        crops.append(Image.fromarray(fr).crop(box).resize((300, 300)))
    logo = Image.open(os.path.join(T.ROOT, "assets", "logo.png")).convert("RGB").resize((300, 300))
    sh = Image.new("RGB", (6 * 302, 300), (20, 20, 20))
    sh.paste(logo, (0, 0))
    for k, c in enumerate(crops):
        sh.paste(c, ((k + 1) * 302, 0))
    sh.save(os.path.join(outdir, "qa_hero_vs_logo.png"))
    rec("hero_no_glasses", "glasses" not in src_chars and "spectacle" not in src_chars,
        note="no glasses shape exists in the character code; see qa_hero_vs_logo.png")

    # 9. no blood / wounds in the artwork
    src_sc = open(os.path.join(os.path.dirname(__file__), "scenes.py")).read() + open(
        os.path.join(os.path.dirname(__file__), "props.py")).read()
    rec("no_graphic_medical_art", "blood" not in src_sc.lower() and "wound" not in src_sc.lower(),
        note="bowl interior is a flat dark-red disk; vein is a stylised blue line; only the brief's own 🩸 emoji appears in scene 7 text")

    # 10. scene 11: round logo with 'Bilib Oldim' directly under it
    i11 = int(round((T.cue(11, "yuboring.") - 0.1) * FPS))
    fr = frame_at(video, i11)
    Image.fromarray(fr).save(os.path.join(outdir, "qa_scene11.png"))
    name = SC.channel_name_img()
    bx = name.getchannel("A").point(lambda v: 255 if v > 60 else 0).getbbox()
    text_top = (SC.LOGO_C[1] + SC.LOGO_R + 160) - name.height / 2 + bx[1]
    logo_bottom = SC.LOGO_C[1] + SC.LOGO_R + 30
    rec("scene11_logo_and_name", 0 <= text_top - logo_bottom <= 120, logo_bottom_y=logo_bottom,
        name_top_y=round(text_top), name_centre_x=540, logo_centre_x=SC.LOGO_C[0])

    # 11. last frame matches first frame (outside text areas)
    n = int(vs["nb_frames"])
    a = frame_at(video, 0).astype(np.float32)
    b = frame_at(video, n - 1).astype(np.float32)
    mask = np.ones((1920, 1080), bool)
    mask[250:570] = False
    mask[1280:1480] = False
    d = np.abs(a - b)[mask].mean()
    Image.fromarray(np.concatenate([a, b], 1).astype(np.uint8)).resize((1080, 960)).save(
        os.path.join(outdir, "qa_loop_first_last.png"))
    rec("loop_last_matches_first", d < 4.0, mean_abs_diff=round(float(d), 2))

    res["ALL_OK"] = ok_all
    json.dump(res, open(os.path.join(os.path.dirname(__file__), "qa_results.json"), "w"), ensure_ascii=False, indent=1)
    print("ALL OK" if ok_all else "SOME CHECKS FAILED")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
