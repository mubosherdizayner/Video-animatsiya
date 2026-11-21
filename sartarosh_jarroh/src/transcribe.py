import json, sys, subprocess
import numpy as np
from faster_whisper import WhisperModel
model_dir, audio_path, out = sys.argv[1:4]
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", audio_path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, dtype=np.float32)
m = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=4)
segs, info = m.transcribe(audio, language="uz", word_timestamps=True, beam_size=5, vad_filter=False,
    initial_prompt="To'xtang! Sartaroshlar avval tish sug'urgan. O'rta asrlar Yevropasida sartarosh-jarroh.")
res = []
for s in segs:
    for w in s.words:
        res.append({"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)})
json.dump(res, open(out, "w"), ensure_ascii=False, indent=0)
print(" ".join(f"{r['w']}[{r['s']:.2f}-{r['e']:.2f}]" for r in res))
