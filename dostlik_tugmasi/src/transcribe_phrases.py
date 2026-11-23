# Re-run faster-whisper on every speech phrase separately (tighter word timestamps inside each phrase).
import json, sys
import numpy as np
from faster_whisper import WhisperModel
from phrases import script_phrases, speech_phrases
model_dir, f32, out = sys.argv[1:4]
m = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=4)
audio = np.fromfile(f32, dtype=np.float32); SR = 16000
sp = script_phrases(); ph, _ = speech_phrases(f32, len(sp))
res = []
for (a, b), words in zip(ph, sp):
    pad0, pad1 = 0.25, 0.25
    i0 = max(0, int((a - pad0) * SR)); i1 = min(len(audio), int((b + pad1) * SR))
    clip = np.concatenate([np.zeros(int(0.3 * SR), np.float32), audio[i0:i1], np.zeros(int(0.5 * SR), np.float32)])
    off = i0 / SR - 0.3
    text = " ".join(w["text"] for w in words).replace("'", "ʻ")
    segs, info = m.transcribe(clip, language="uz", word_timestamps=True, beam_size=5, vad_filter=False,
                              initial_prompt=text, condition_on_previous_text=False)
    ws = [{"w": w.word, "s": round(w.start + off, 3), "e": round(w.end + off, 3)} for s in segs for w in s.words]
    res.append({"phrase": [a, b], "script": [w["text"] for w in words], "whisper": ws})
    print(f"{a:6.2f}-{b:6.2f} | " + " ".join(f"{w['w'].strip()}@{w['s']:.2f}" for w in ws))
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
