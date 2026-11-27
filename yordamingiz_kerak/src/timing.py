"""Refine aligner word times with the voice energy, derive scenes and the per-frame mouth state."""
import json, sys, math, numpy as np
from scipy.ndimage import uniform_filter1d
work = sys.argv[1]; FPS = 30
a = np.fromfile(work + "/v16.f32", dtype=np.float32); SR = 16000
dur = len(a) / SR
W = json.load(open(work + "/words_mms.json"))
# 5 ms hop / 20 ms window energy for onsets
hop, win = 80, 320
fr = np.lib.stride_tricks.sliding_window_view(np.r_[np.zeros(win // 2), a, np.zeros(win)], win)[::hop]
db5 = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9); t5 = np.arange(len(db5)) * hop / SR
peak = np.percentile(db5, 99.5); thr = peak - 36
sil = db5 < thr
runs = []; i = 0
while i < len(sil):
    if sil[i]:
        j = i
        while j < len(sil) and sil[j]: j += 1
        if (j - i) * hop / SR >= 0.06: runs.append((t5[i], t5[min(j, len(t5) - 1)]))
        i = j
    else: i += 1
CTC_LAG = 0.025
for k, w in enumerate(W):
    s, e = w["s"], w["e"]
    ns = s - CTC_LAG; src = "ctc"
    prev_e = W[k - 1]["e"] if k else -1
    for a0, b0 in runs:            # word right after a pause between words: start = acoustic onset
        if s - 0.16 <= b0 <= s + 0.02 and a0 >= prev_e - 0.04: ns = b0; src = "onset"
    if k == 0: ns = min(ns, next((b for a_, b in runs if a_ <= 0.001), ns))
    ne = e
    for a0, b0 in runs:
        if e - 0.06 <= a0 <= e + 0.25: ne = a0; break
    w["start"], w["end"], w["src"] = round(max(ns, 0), 3), round(ne, 3), src
for k in range(len(W) - 1):          # keep order / no overlap
    W[k]["end"] = round(min(W[k]["end"], W[k + 1]["start"]), 3)
# scenes start at the first word of each sentence (scene 1 at 0)
nS = max(w["sent"] for w in W) + 1
scenes = []
for si in range(nS):
    ws = [w for w in W if w["sent"] == si]
    st = 0.0 if si == 0 else ws[0]["start"]
    scenes.append(dict(id=si + 1, start=st, f0=0 if si == 0 else int(round(st * FPS))))
NF = int(math.ceil(dur * FPS - 1e-6))
for si in range(nS):
    scenes[si]["f1"] = scenes[si + 1]["f0"] if si + 1 < nS else NF
for w in W: w["f0"] = int(round(w["start"] * FPS))
# ---- lip-sync: RMS in 10 ms windows, smoothed, per-frame decision with 2-frame minimum hold
n10 = len(a) // 160
rms = np.sqrt((a[: n10 * 160].reshape(-1, 160) ** 2).mean(1))
db10 = 20 * np.log10(rms + 1e-9)
sm = uniform_filter1d(db10, 3)                      # 30 ms smoothing
pk = np.percentile(sm, 99.5)
loc = np.array([sm[max(0, i - 10): i + 11].max() for i in range(len(sm))])   # +-120 ms local peak
open10 = (sm > pk - 30) & (sm > loc - 8.5)
mouth = np.zeros(NF, bool)
for f in range(NF):
    i0, i1 = int(f / FPS * 100), int((f + 1) / FPS * 100)
    seg = open10[i0:max(i1, i0 + 1)]
    mouth[f] = seg.mean() >= 0.5 if len(seg) else False
def min_hold(m, n=2):
    m = m.copy()
    for _ in range(3):
        f = 0
        while f < len(m):
            g = f
            while g < len(m) and m[g] == m[f]: g += 1
            if g - f < n and f > 0 and g < len(m): m[f:g] = not m[f]
            f = g
    return m
# pauses between words (>= 0.15 s) are always closed
for a_, b_ in zip(W, W[1:]):
    if b_["start"] - a_["end"] >= 0.15:
        mouth[int(math.ceil(a_["end"] * FPS)):int(math.floor(b_["start"] * FPS))] = False
mouth[: int(math.floor(W[0]["start"] * FPS))] = False
mouth[int(math.ceil(W[-1]["end"] * FPS)):] = False
mouth = min_hold(mouth, 2)
for a_, b_ in zip(W, W[1:]):
    if b_["start"] - a_["end"] >= 0.15:
        mouth[int(math.ceil(a_["end"] * FPS)):int(math.floor(b_["start"] * FPS))] = False
json.dump(dict(duration=dur, nframes=NF, fps=FPS, words=W, scenes=scenes, mouth=mouth.astype(int).tolist(),
               pauses=runs), open(work + "/timing.json", "w"), ensure_ascii=False, indent=1)
for w in W: print(f'{w["sent"]+1:2d} {w["text"]:16s} {w["s"]:6.2f}->{w["start"]:6.2f} ({w["src"]:5s}) end {w["end"]:6.2f} f{w["f0"]}')
print("scenes", [(s["id"], s["f0"], s["f1"]) for s in scenes]); print("frames", NF, "dur", dur)
runs_m = np.diff(np.r_[0, mouth.astype(int), 0]); print("mouth open runs:", (runs_m == 1).sum())
