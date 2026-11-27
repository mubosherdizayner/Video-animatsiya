import json, sys, numpy as np
from faster_whisper import WhisperModel
model_dir, audio, out = sys.argv[1:4]
m = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=4)
a = np.fromfile(audio, dtype=np.float32)
segs, info = m.transcribe(a, language="uz", word_timestamps=True, beam_size=5, vad_filter=False,
    initial_prompt="Lentada biri hype qilyapti, biri yomonlayapti. Instagram'da foydali narsa yo'q. Rahmat! layk")
res = []
for s in segs:
    for w in s.words:
        res.append({"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)})
json.dump(res, open(out, "w"), ensure_ascii=False, indent=0)
print(" ".join(f"{r['w']}[{r['s']:.2f}-{r['e']:.2f}]" for r in res))
