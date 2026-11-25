# Word-level timestamps from the voice-over (faster-whisper).
import json, sys, subprocess
import numpy as np
from faster_whisper import WhisperModel
model_dir, audio_path, out = sys.argv[1:4]
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", audio_path, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.float32).copy()
m = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=4)
segs, info = m.transcribe(audio, language="uz", word_timestamps=True, beam_size=5, vad_filter=False,
    initial_prompt="Toʻqson foiz odam aytdi: doʻstingiz sizni million dollarga sotadi. Semichka chaqib oʻtirgan kechalaringiz. Izohga yozing.")
res = []
for s in segs:
    for w in s.words:
        res.append({"w": w.word, "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)})
json.dump(res, open(out, "w"), ensure_ascii=False, indent=0)
print(" ".join(f"{r['w']}[{r['s']:.2f}-{r['e']:.2f}]" for r in res))
