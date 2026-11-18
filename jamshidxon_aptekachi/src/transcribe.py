import json, sys
from faster_whisper import WhisperModel
model_dir, audio, out = sys.argv[1:4]
m = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=4)
res = []
import numpy as np
audio = np.fromfile(audio, dtype=np.float32)
for lang in ["uz"]:
    segs, info = m.transcribe(audio, language=lang, word_timestamps=True, beam_size=5, vad_filter=False,
        initial_prompt="Toʻxtang! Agar Jamshidxon Ziyoxonov bloger boʻlmaganida, aptekachi boʻlardi! farmatsevtikada dorixona vitamin mevaga sarflang mahalla")
    for s in segs:
        for w in s.words:
            res.append({"w": w.word, "s": w.start, "e": w.end, "p": w.probability})
json.dump(res, open(out, "w"), ensure_ascii=False, indent=0)
print(" ".join(f"{r['w']}[{r['s']:.2f}-{r['e']:.2f}]" for r in res))
