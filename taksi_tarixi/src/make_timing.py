# Final word timing: CTC forced-alignment onsets (whisper only seeds the order check). Writes timing.json.
import json, sys
words = json.load(open("words_ctc.json"))
AUDIO_DUR = float(open("audio_dur.txt").read())
out = []
for i, w in enumerate(words):
    s = 0.0 if i == 0 else w["ctc_start"]
    out.append({"scene": w["scene"], "text": w["text"], "start": round(s, 3), "end": round(w["ctc_end"], 3)})
for i in range(1, len(out)): assert out[i]["start"] > out[i - 1]["start"], out[i]
scenes = {}
for w in out: scenes.setdefault(w["scene"], w["start"])
json.dump({"audio_dur": AUDIO_DUR, "words": out, "scene_start": scenes}, open("timing.json", "w"), ensure_ascii=False, indent=1)
for k, v in scenes.items(): print(k, v)
