# Align script words to Whisper words, then refine onsets with the audio energy envelope.
import json, re, difflib, sys
import numpy as np
from script_data import SCENES, OVERRIDES
APOS = "ʻʼ'`‘’ʹ′"
def norm(w):
    w = w.lower()
    for a in APOS: w = w.replace(a, "'")
    return re.sub(r"[^a-z0-9']", "", w)
def fold(w):
    w = norm(w).replace("o'", "o").replace("g'", "g").replace("'", "")
    for a, b in (("kh", "h"), ("x", "h"), ("q", "k"), ("sh", "s"), ("ch", "c"), ("ng", "n"), ("y", "i")):
        w = w.replace(a, b)
    return re.sub(r"[aeiou]", "a", w)
def sim(a, b): return difflib.SequenceMatcher(None, fold(a), fold(b)).ratio()

def dp_align(sw, tr):
    n, m = len(sw), len(tr); INF = 1e9
    D = np.full((n + 1, m + 1), INF); B = {}; D[0, 0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            c = D[i, j]
            if c >= INF: continue
            opts = []
            if i < n and j < m: opts.append((i + 1, j + 1, 1 - sim(sw[i], tr[j]["w"]), "11"))
            for k in (2, 3, 4):
                if i + k <= n and j < m: opts.append((i + k, j + 1, 1 - sim("".join(sw[i:i + k]), tr[j]["w"]) + 0.25 * (k - 1), f"{k}1"))
            if i < n and j + 1 < m: opts.append((i + 1, j + 2, 1 - sim(sw[i], tr[j]["w"] + tr[j + 1]["w"]) + 0.25, "12"))
            if i < n: opts.append((i + 1, j, 0.95, "s0"))
            if j < m: opts.append((i, j + 1, 0.6, "0t"))
            for a, b, cost, k in opts:
                if c + cost < D[a, b]: D[a, b] = c + cost; B[(a, b)] = (i, j, k)
    path = []; a, b = n, m
    while (a, b) != (0, 0):
        i, j, k = B[(a, b)]; path.append((i, j, k)); a, b = i, j
    return path[::-1]

def energy(path):
    a = np.fromfile(path, dtype=np.float32); hop, win = 80, 320
    idx = range(0, len(a) - win, hop)
    e = np.array([np.sqrt(np.mean(a[i:i + win] ** 2) + 1e-12) for i in idx])
    z = np.array([np.mean(np.abs(np.diff(np.sign(a[i:i + win])))) / 2 for i in idx])
    return 20 * np.log10(e), z, hop / 16000.0

def main(words_json, f32, out):
    tr = [w for w in json.load(open(words_json)) if norm(w["w"])]
    sw = []
    for sid, txt in SCENES:
        k = 0
        for w in txt.split():
            if not norm(w): continue  # dashes are not spoken
            sw.append({"scene": sid, "text": w, "first": k == 0}); k += 1
    path = dp_align([w["text"] for w in sw], tr)
    T = [None] * len(sw)
    for i, j, k in path:
        if k == "11": T[i] = [tr[j]["s"], tr[j]["e"], "m"]
        elif k[1] == "1" and k[0] in "234":
            n = int(k[0]); s, e = tr[j]["s"], tr[j]["e"]
            L = [len(norm(sw[i + q]["text"])) for q in range(n)]; acc = s
            for q in range(n):
                d = (e - s) * L[q] / sum(L); T[i + q] = [acc, acc + d, "split"]; acc += d
        elif k == "12": T[i] = [tr[j]["s"], tr[j + 1]["e"], "m2"]
    for i in range(len(sw)):
        if T[i] is None:
            p = max([q for q in range(i) if T[q]], default=None); nx = min([q for q in range(i + 1, len(sw)) if T[q]], default=None)
            t0 = T[p][1] if p is not None else 0.0; t1 = T[nx][0] if nx is not None else t0 + 0.4
            T[i] = [t0, t1, "interp"]
    db, zcr, hop = energy(f32); mx = np.percentile(db, 99)
    sil = db < mx - 38
    runs = []; i = 0
    while i < len(sil):
        if sil[i]:
            j = i
            while j < len(sil) and sil[j]: j += 1
            if (j - i) * hop >= 0.08: runs.append((i * hop, j * hop))
            i = j
        else: i += 1
    for k, w in enumerate(sw):
        s, e, how = T[k]
        key = (w["scene"], norm(w["text"]))
        if key in OVERRIDES:
            T[k][0] = OVERRIDES[key]; T[k][2] = "override"; continue
        prev_s = T[k - 1][0] if k else -1
        c = [r for r in runs if ((s - 0.2 <= r[1] <= s + 0.5 and r[1] < e - 0.06) or (s + 0.1 <= r[0] and r[1] < e - 0.15)) and r[1] > prev_s + 0.08]
        if c:
            T[k][0] = min(c, key=lambda r: abs(r[1] - s))[1]; T[k][2] = how + "+pause"; continue
        # fricative-initial words: onset = start of the high zero-crossing run
        if re.match(r"[«]?(s|sh|ch|f|z|x|h|ts)", w["text"].lower()):
            a0, a1 = int((s - 0.15) / hop), int((s + 0.12) / hop)
            hz = [q for q in range(a0, a1) if zcr[q] > 0.35 and (q == 0 or zcr[q - 1] <= 0.35)]
            if hz:
                q = min(hz, key=lambda q: abs(q * hop - s))
                if q * hop > prev_s + 0.08:
                    T[k][0] = q * hop; T[k][2] = how + "+fric"; continue
        # mid-speech: snap to a nearby energy dip
        a0, a1 = int((s - 0.07) / hop), int((s + 0.07) / hop)
        seg = db[a0:a1]
        if len(seg) > 3:
            jm = int(np.argmin(seg)); lo = seg[jm]
            ctx = db[max(0, a0 - 12):a1 + 12].max()
            if ctx - lo > 9:
                jj = a0 + jm
                while jj < len(db) - 1 and db[jj] < lo + 4: jj += 1
                if jj * hop > prev_s + 0.08: T[k][0] = jj * hop; T[k][2] = how + "+dip"
    T[0][0] = 0.0
    for k in range(len(sw) - 1):  # ends: next word start (for display), never overlap
        T[k][1] = min(max(T[k][1], T[k][0] + 0.05), T[k + 1][0])
    # speech end of each word (for hiding during long pauses): last voiced frame before next start
    for k, w in enumerate(sw):
        w["start"], w["end"], w["how"] = round(T[k][0], 3), round(T[k][1], 3), T[k][2]
        nxt = T[k + 1][0] if k + 1 < len(sw) else len(db) * hop
        r = [q for q in runs if w["start"] < q[0] < nxt and q[1] >= nxt - 0.02]
        w["voice_end"] = round(r[0][0] if r else nxt, 3)
    json.dump(sw, open(out, "w"), ensure_ascii=False, indent=1)
    for w in sw:
        print(f"{w['scene']:>2} {w['text']:<18} {w['start']:6.2f} {w['end']:6.2f} ve={w['voice_end']:6.2f} {w['how']}")
if __name__ == "__main__": main(*sys.argv[1:4])
