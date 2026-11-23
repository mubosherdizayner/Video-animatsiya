# Split the voice into speech phrases at pauses, and the script into phrases at punctuation.
import numpy as np
from align import energy_db
from script_data import SCENES, tokens
PUNCT = (".", ",", "?", "!", "…", "—", "?”", ".”")
def script_phrases():
    out, cur = [], []
    for sid, txt in SCENES:
        for k, w in enumerate(tokens(txt)):
            cur.append({"scene": sid, "text": w, "first": k == 0})
            if w.rstrip("”\"").endswith((".", ",", "?", "!", "—")) or w.endswith("..."):
                out.append(cur); cur = []
    if cur: out.append(cur)
    return out
def speech_phrases(f32, n_expected, min_pause=0.10, rel=30):
    db, hop = energy_db(f32); mx = np.percentile(db, 99)
    sm = np.convolve(db, np.ones(3) / 3, mode="same")
    sil = sm < mx - rel
    runs = []; i = 0; n = len(sil)
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]: j += 1
            runs.append((i * hop + 0.01, j * hop + 0.01)); i = j
        else: i += 1
    lead = runs[0] if runs and runs[0][0] < 0.02 else None
    inner = [r for r in runs if r is not lead and r[1] < len(sil) * hop - 0.02]
    inner = sorted(inner, key=lambda r: r[1] - r[0], reverse=True)[:n_expected - 1]
    inner.sort()
    start = lead[1] if lead else 0.0
    ph = []
    for r in inner:
        ph.append((round(start, 3), round(r[0], 3))); start = r[1]
    end = runs[-1][0] if runs and runs[-1][1] >= len(sil) * hop - 0.02 else len(sil) * hop
    ph.append((round(start, 3), round(end, 3)))
    return ph, inner
if __name__ == "__main__":
    sp = script_phrases(); print(len(sp))
    ph, inner = speech_phrases("../build/voice16k.f32", len(sp))
    for (a, b), words in zip(ph, sp):
        print(f"{a:6.2f}-{b:6.2f}  " + " ".join(w["text"] for w in words))
    print("shortest kept pause", min(r[1] - r[0] for r in inner))
