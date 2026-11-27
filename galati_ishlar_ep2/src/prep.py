"""Decode the voice-over to 48 kHz mono float WAV; trim lead-in silence if it is longer than 0.3 s."""
import sys, subprocess, numpy as np, scipy.io.wavfile as wf
src, out = sys.argv[1:3]
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-ac", "1", "-ar", "48000", "-c:a", "pcm_f32le", out], check=True)
sr, x = wf.read(out); x = x.astype(np.float32)
hop = int(sr * 0.005); n = len(x) // hop
db = 20 * np.log10(np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1)) + 1e-9)
onset = float(np.argmax(db > db.max() - 40) * 0.005)
if onset > 0.3:
    cut = int((onset - 0.05) * sr); wf.write(out, sr, x[cut:]); print(f"lead-in silence {onset:.3f}s -> trimmed {onset-0.05:.3f}s")
else:
    print(f"lead-in silence {onset:.3f}s <= 0.3s -> no trim")
