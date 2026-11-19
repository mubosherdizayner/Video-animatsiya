# Transcribe every pause-bounded speech interval on its own (decides which words belong to which interval)
import json, sys
import numpy as np
from faster_whisper import WhisperModel
from align import speech_intervals
model_dir, audio, db_npy, dur_txt, out = sys.argv[1:6]
m = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=4)
a = np.fromfile(audio, dtype=np.float32)
iv = speech_intervals(np.load(db_npy), min_pause=0.1, dur=float(open(dur_txt).read()))
res = []
for t0, t1 in iv:
    p0, p1 = max(0, t0 - 0.06), t1 + 0.06
    segs, info = m.transcribe(a[int(p0 * 16000):int(p1 * 16000)], language="uz", word_timestamps=True, beam_size=5,
                              vad_filter=False, condition_on_previous_text=False)
    ws = [{"w": w.word, "s": round(w.start + p0, 3), "e": round(w.end + p0, 3), "p": round(w.probability, 3)} for s in segs for w in s.words]
    res.append({"iv": [t0, t1], "words": ws})
    print(f"[{t0:5.2f}-{t1:5.2f}]", " ".join(w["w"] for w in ws), flush=True)
json.dump(res, open(out, "w"), ensure_ascii=False, indent=0)
