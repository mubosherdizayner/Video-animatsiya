# Re-transcribe each pause-delimited phrase separately: phrase onsets come from audio energy,
# word times inside a phrase come from faster-whisper word_timestamps on that phrase only.
import json, sys
import numpy as np
from faster_whisper import WhisperModel
model_dir, audio, out = sys.argv[1:4]
SR = 16000
x = np.fromfile(audio, dtype=np.float32)
db = np.load("env_db.npy"); hop = 0.005
mx = db.max(); sil = db < mx - 40
runs = []; i = 0; n = len(sil)
while i < n:
    if sil[i]:
        j = i
        while j < n and sil[j]: j += 1
        if (j - i) * hop >= 0.04: runs.append((i * hop + 0.01, j * hop + 0.01))
        i = j
    else: i += 1
json.dump(runs, open("silence_runs.json", "w"))
pauses = [r for r in runs if r[1] - r[0] >= 0.2]
# phrases = speech between long pauses
edges = [0.0] + [v for r in pauses for v in r] + [len(x) / SR]
phrases = [(edges[k], edges[k + 1]) for k in range(0, len(edges) - 1, 2) if edges[k + 1] - edges[k] > 0.1]
m = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=4)
res = []
for a, b in phrases:
    pa, pb = max(0, a - 0.05), min(len(x) / SR, b + 0.05)
    seg = np.concatenate([np.zeros(int(0.3 * SR), np.float32), x[int(pa * SR):int(pb * SR)], np.zeros(int(0.3 * SR), np.float32)])
    segs, info = m.transcribe(seg, language="uz", word_timestamps=True, beam_size=5, vad_filter=False,
                              condition_on_previous_text=False)
    ws = [w for s in segs for w in s.words]
    for w in ws:
        res.append({"w": w.word, "s": round(pa - 0.3 + w.start, 3), "e": round(pa - 0.3 + w.end, 3),
                    "p": round(w.probability, 3), "ph": [round(a, 3), round(b, 3)]})
    print(f"[{a:6.2f}-{b:6.2f}] " + " ".join(f"{w.word.strip()}({pa-0.3+w.start:.2f})" for w in ws), flush=True)
json.dump(res, open(out, "w"), ensure_ascii=False, indent=0)
