import json, sys
import numpy as np
from faster_whisper import WhisperModel
model_dir, audio, out = sys.argv[1:4]
m = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=4)
audio = np.fromfile(audio, dtype=np.float32)
res = []
segs, info = m.transcribe(audio, language="uz", word_timestamps=True, beam_size=5, vad_filter=False,
    initial_prompt="Bobur aka, meni vaynga oling! Agar Bobur Mansurov bloger boʻlmaganida kim boʻlardi? Restoran egasi! Oshpaz piyoz toʻgʻrab yigʻlaydi. Kassir monolog oʻqiydi.")
for s in segs:
    for w in s.words:
        res.append({"w": w.word, "s": w.start, "e": w.end, "p": w.probability})
json.dump(res, open(out, "w"), ensure_ascii=False, indent=0)
print(" ".join(f"{r['w']}[{r['s']:.2f}-{r['e']:.2f}]" for r in res))
