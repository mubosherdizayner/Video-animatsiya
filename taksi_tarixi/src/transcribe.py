import json, sys
import numpy as np
from faster_whisper import WhisperModel
model_dir, audio, out = sys.argv[1:4]
m = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=4)
audio = np.fromfile(audio, dtype=np.float32)
segs, info = m.transcribe(audio, language="uz", word_timestamps=True, beam_size=5, vad_filter=False,
    initial_prompt="Har kuni taksi deysiz. Hisoblagich, taksometr, Vilgelm Brun, takse, metron, savdolashasizmi.")
res = []
for s in segs:
    for w in s.words:
        res.append({"w": w.word, "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)})
json.dump(res, open(out, "w"), ensure_ascii=False, indent=0)
print(" ".join(f"{r['w']}[{r['s']:.2f}-{r['e']:.2f}]" for r in res))
