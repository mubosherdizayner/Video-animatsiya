"""Word timestamps: faster-whisper (language uz). Fallback if the model cannot load:
sentences from energy pauses, words spread by character count.  Usage: transcribe.py model_dir vo.wav out.json"""
import json, sys
import numpy as np, scipy.io.wavfile as wf, scipy.signal as ss
model_dir, audio, out = sys.argv[1:4]
sr, x = wf.read(audio); x = x.astype(np.float32)


def fallback():
    from data import VOICE_LINES
    hop = int(sr * 0.005); n = len(x) // hop
    db = 20 * np.log10(np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, 1)) + 1e-9); db -= db.max()
    sil = db < -42; segs = []; i = 0; start = None
    while i < n:
        if not sil[i] and start is None: start = i
        if sil[i] and start is not None:
            j = i
            while j < n and sil[j]: j += 1
            if (j - i) * 0.005 >= 0.25 or j == n: segs.append([start * 0.005, i * 0.005]); start = None
            i = j; continue
        i += 1
    if start is not None: segs.append([start * 0.005, n * 0.005])
    while len(segs) > len(VOICE_LINES):        # merge across the shortest pauses
        k = int(np.argmin([segs[i + 1][0] - segs[i][1] for i in range(len(segs) - 1)]))
        segs[k] = [segs[k][0], segs[k + 1][1]]; del segs[k + 1]
    res = []
    for (a, b), (_, _, txt) in zip(segs, VOICE_LINES):
        toks = [t for t in txt.split() if any(c.isalpha() for c in t)]
        L = [len(t) for t in toks]; tot = sum(L); acc = 0
        for t, l in zip(toks, L):
            res.append({"w": t, "s": round(a + (b - a) * acc / tot, 3), "e": round(a + (b - a) * (acc + l) / tot, 3), "p": 0.0}); acc += l
    return res


try:
    from faster_whisper import WhisperModel
    m = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=4)
    x16 = ss.resample_poly(x, 1, sr // 16000).astype(np.float32) if sr != 16000 else x
    segs, info = m.transcribe(x16, language="uz", word_timestamps=True, beam_size=5, vad_filter=False,
        initial_prompt="Sardor yoʻqolgan tongda oʻrmondan bir qiz chiqdi. Rustam! Ukang qani? Opa, bolalar shunaqa. Isming nima, qizim? Allo, bolalar uyimi? bazadan. Uni toping. Davomi bor, obuna boʻling.")
    res = [{"w": w.word, "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)} for s in segs for w in s.words]
    src = "faster-whisper"
except Exception as e:
    print("whisper unavailable (", e, ") -> energy/character fallback")
    res = fallback(); src = "fallback"
json.dump(res, open(out, "w"), ensure_ascii=False, indent=0)
print(src + ":", " ".join(f"{r['w']}[{r['s']:.2f}-{r['e']:.2f}]" for r in res))
