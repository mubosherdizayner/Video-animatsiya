# Match script words to whisper words (fuzzy, in order) and take only the times.
# Refinement: words after a pause start exactly at the pause end (audio energy);
# inner words snap to the nearest energy valley close to the whisper start.
import json, re, difflib, sys
import numpy as np
from script_data import script_words
APOS = "ʻʼ'`‘’ʹ′"
CYR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюяў", ["a","b","v","g","d","e","yo","j","z","i","y","k","l","m","n","o","p","r","s","t","u","f","x","ts","ch","sh","sh","","i","","e","yu","ya","o"]))
def norm(w):
    w = "".join(CYR.get(c, c) for c in w.lower())
    for a in APOS: w = w.replace(a, "'")
    return re.sub(r"[^a-z']", "", w)
def fold(w):
    w = norm(w).replace("o'", "o").replace("g'", "g").replace("'", "")
    for a, b in (("kh", "h"), ("x", "h"), ("q", "k"), ("sh", "s"), ("ch", "c"), ("ng", "n"), ("j", "c")):
        w = w.replace(a, b)
    return re.sub(r"[aeiou]", "a", w)
def sim(a, b): return difflib.SequenceMatcher(None, fold(a), fold(b)).ratio()

def align(sw, tr):
    n, m = len(sw), len(tr); INF = 1e9
    D = np.full((n + 1, m + 1), INF); B = {}; D[0, 0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            c = D[i, j]
            if c >= INF: continue
            opts = []
            if i < n and j < m: opts.append((i + 1, j + 1, 1 - sim(sw[i], tr[j]["w"]), "11"))
            if i + 1 < n and j < m: opts.append((i + 2, j + 1, 1 - sim(sw[i] + sw[i + 1], tr[j]["w"]) + 0.3, "21"))
            if i < n and j + 1 < m: opts.append((i + 1, j + 2, 1 - sim(sw[i], tr[j]["w"] + tr[j + 1]["w"]) + 0.15, "12"))
            if i < n: opts.append((i + 1, j, 0.9, "s0"))
            if j < m: opts.append((i, j + 1, 0.9, "0t"))
            for a, b, cost, k in opts:
                if c + cost < D[a, b]: D[a, b] = c + cost; B[(a, b)] = (i, j, k)
    path = []; a, b = n, m
    while (a, b) != (0, 0):
        i, j, k = B[(a, b)]; path.append((i, j, k)); a, b = i, j
    return path[::-1]

def valleys(db, hop=0.005, prom=4.0, span=0.10):
    sm = np.convolve(db, np.ones(5) / 5, mode="same"); w = int(span / hop); out = []
    for k in range(w, len(sm) - w):
        if sm[k] == sm[k - 2:k + 3].min():
            l, r = sm[k - w:k].max(), sm[k + 1:k + w + 1].max()
            if min(l, r) - sm[k] >= prom: out.append(round(k * hop + 0.01, 3))
    return out

def main(words_json, out):
    tr = json.load(open(words_json))
    sw = script_words()
    path = align([w["raw"] for w in sw], tr)
    T = [None] * len(sw)
    for i, j, k in path:
        if k == "11": T[i] = [tr[j]["s"], tr[j]["e"], "m", tr[j]["w"].strip()]
        elif k == "21":
            s, e = tr[j]["s"], tr[j]["e"]; l1, l2 = len(norm(sw[i]["raw"])), len(norm(sw[i + 1]["raw"]))
            mid = s + (e - s) * l1 / (l1 + l2); T[i] = [s, mid, "split", tr[j]["w"]]; T[i + 1] = [mid, e, "split", tr[j]["w"]]
        elif k == "12": T[i] = [tr[j]["s"], tr[j + 1]["e"], "m2", tr[j]["w"].strip() + tr[j + 1]["w"].strip()]
    assert all(T), [w["raw"] for w, t in zip(sw, T) if not t]
    for t in T: t.append(t[0])
    runs = json.load(open("silence_runs.json"))
    merged = []
    for a, b in runs:                      # merge runs split by a tiny blip (< 60 ms)
        if merged and a - merged[-1][1] < 0.06: merged[-1][1] = b
        else: merged.append([a, b])
    pauses = [r for r in merged if r[1] - r[0] >= 0.2]
    db = np.load("env_band_db.npy"); V = valleys(db)
    ends = [r[1] for r in merged if r[1] - r[0] >= 0.04]
    for k, w in enumerate(sw):
        s, e = T[k][0], T[k][1]
        if k == 0:
            T[k][0] = 0.0; T[k][2] += "+0"; continue
        # phrase-initial: a real pause overlapping the whisper start region
        pc = [p for p in pauses if p[0] <= s + 0.3 and s - 0.12 <= p[1] <= max(e + 0.05, s + 0.1) and p[1] > T[k - 1][0] + 0.15]
        if pc:
            T[k][0] = pc[-1][1]; T[k][2] += "+pause"; continue
        lo = max(s - 0.10, T[k - 1][0] + 0.12)
        cands = [(t, "run") for t in ends if lo <= t <= s + 0.18] + [(t, "valley") for t in V if lo <= t <= s + 0.18]
        if cands:
            t, how = min(cands, key=lambda c: abs(c[0] - (s + 0.03)))
            T[k][0] = t; T[k][2] += "+" + how
    # pass 2: inner words. target = mean(whisper start, syllable-proportional position in the phrase),
    # at least 0.12 s per syllable after the previous word, snapped to a nearby energy boundary.
    syl = [max(1, len(re.findall(r"[aeiou]", norm(w["raw"])))) for w in sw]
    heads = [k for k in range(len(sw)) if k == 0 or "+pause" in T[k][2]] + [len(sw)]
    for a, b in zip(heads, heads[1:]):
        p0 = T[a][0]
        p1 = min([p[0] for p in pauses if p[0] > T[b - 1][0]] or [T[b - 1][1]])
        tot = sum(syl[a:b]); per = (p1 - p0) / tot
        for k in range(a + 1, b):
            s = T[k][3 + 1] if False else T[k][0]
            sp = p0 + per * sum(syl[a:k])
            wh = T[k][4]
            tgt = 0.5 * wh + 0.5 * sp
            lo = T[k - 1][0] + 0.12 * syl[k - 1]
            hi = min([p[0] for p in pauses if p[0] > T[k - 1][0]] or [99]) - 0.1
            cands = [t for t in ends + V if lo <= t <= hi and abs(t - tgt) <= 0.14]
            t = min(cands, key=lambda c: abs(c - tgt)) if cands else max(lo, min(tgt, hi))
            T[k][0] = round(t, 3); T[k][2] = T[k][2].split("+")[0] + ("+snap" if cands else "+est")
    for k in range(len(sw)):
        if k + 1 < len(sw): T[k][1] = min(T[k][1], T[k + 1][0])
        T[k][1] = max(T[k][1], T[k][0] + 0.12)
    for k, w in enumerate(sw):
        w["start"], w["end"], w["how"], w["heard"] = round(T[k][0], 3), round(T[k][1], 3), T[k][2], T[k][3]
        w["whisper_start"] = T[k][4]
    json.dump(sw, open(out, "w"), ensure_ascii=False, indent=1)
    for w in sw:
        print(f"{w['scene']:>2} {w['text']:<20} {w['start']:6.2f} {w['end']:6.2f}  {w['how']:<12} whisper {w['whisper_start']:6.2f}")
if __name__ == "__main__": main(*sys.argv[1:3])
