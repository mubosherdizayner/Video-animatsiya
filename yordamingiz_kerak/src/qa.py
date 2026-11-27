"""QA: extract frames from the final MP4 and check timing, durations, levels, layout."""
import json, math, os, re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
work, final, voice = sys.argv[1:4]
TM = json.load(open(f"{work}/timing.json")); W = TM["words"]; FPS = 30
def grab(f):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", final, "-vf", f"select=eq(n\\,{f})", "-vframes", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return Image.frombytes("RGB", (1080, 1920), raw)
def dur(p, sel):
    return float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", sel, "-show_entries", "stream=duration",
                                 "-of", "csv=p=0", p], capture_output=True, text=True).stdout.split()[0])
res = {}
vd, ad, vo = dur(final, "v:0"), dur(final, "a:0"), dur(voice, "a:0")
res["duration"] = dict(video=vd, audio=ad, voiceover=vo, diff_frames=round(abs(vd - vo) * FPS, 2), ok=abs(vd - vo) < 1 / FPS)
rep = json.load(open(f"{work}/sfx_report.json"))
res["voice_over_sfx_min_db"] = min(r[2] for r in rep["voice_minus_sfx_db"])
M = TM["mouth"]; bad = []
for a, b in zip(W, W[1:]):
    if b["start"] - a["end"] > 0.2:
        f0, f1 = int(round(a["end"] * FPS)) + 2, int(round(b["start"] * FPS)) - 1
        if sum(M[f0:f1]): bad.append((a["text"], b["text"]))
runs = [len(m.group()) for m in re.finditer(r"0+|1+", "".join(map(str, M)))]
res["lipsync"] = dict(open_in_pauses=bad, min_state_frames=min(runs[1:-1]), open_frames_in_speech=sum(M))
res["subtitle_frames"] = [dict(word=w["text"], start=w["start"], frame=w["f0"], offset_frames=round(w["f0"] - w["start"] * FPS, 2)) for w in W]
res["max_sub_offset_frames"] = max(abs(x["offset_frames"]) for x in res["subtitle_frames"])
json.dump(res, open(f"{work}/qa.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in res.items() if k != "subtitle_frames"}, indent=1))
# frame sheet: frame 0 + 4 mid-word checks + CTA moments
picks = [("frame 0 (hook)", 0)]
for si, wi, lab in ((1, 1, "S2"), (2, 4, "S3"), (4, 3, "S5"), (7, 4, "S8"), (3, 6, "CTA S4"), (8, 2, "CTA S9"), (9, 0, "CTA S10")):
    w = [x for x in W if x["sent"] == si][wi]; f = int(round((w["start"] + w["end"]) / 2 * FPS))
    if lab.startswith("CTA S4"): f = int(round((w["start"] + 0.25) * FPS))
    picks.append((f"{lab} '{w['text']}' f{f}", f))
F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
tiles = []
for lab, f in picks:
    im = grab(f).resize((360, 640)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 360, 26], fill=(0, 0, 0)); d.text((6, 3), lab, fill=(255, 255, 0), font=F); tiles.append(im)
sheet = Image.new("RGB", (4 * 364, 2 * 644), "white")
for i, im in enumerate(tiles): sheet.paste(im, ((i % 4) * 364, (i // 4) * 644))
sheet.save(f"{work}/qa_sheet.jpg", quality=88)
