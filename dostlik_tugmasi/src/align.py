# Word timing: phrase onsets from the voice energy (pauses split the voice into the 25 punctuation phrases of
# the script), in-phrase word onsets from syllable peaks (when the count matches) or whisper + nearest energy dip.
import json, re, sys
import numpy as np
from scipy.signal import find_peaks

APOS = "ʻʼ'`‘’"
def norm(w):
    w = w.lower()
    for a in APOS: w = w.replace(a, "'")
    return re.sub(r"[^a-z']", "", w)
def syl(w):
    return max(1, len(re.findall("[aeiou]", norm(w).replace("'", ""))))

def energy_db(f32_16k):
    a = np.fromfile(f32_16k, dtype=np.float32); hop = 80; win = 320  # 5 ms hop, 20 ms window
    e = np.array([np.sqrt((a[i:i + win] ** 2).mean() + 1e-12) for i in range(0, len(a) - win, hop)])
    return 20 * np.log10(e), hop / 16000.0

def fold(w):
    w = norm(w).replace("o'", "o").replace("g'", "g").replace("'", "")
    for a, b in (("kh", "h"), ("x", "h"), ("q", "k"), ("sh", "s"), ("ch", "c"), ("ng", "n")): w = w.replace(a, b)
    return re.sub(r"[aeiou]", "a", w)
def sim(a, b):
    import difflib
    return difflib.SequenceMatcher(None, fold(a), fold(b)).ratio()
def dp_align(sw, tr):
    n, m = len(sw), len(tr); INF = 1e9
    D = np.full((n + 1, m + 1), INF); B = {}; D[0, 0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            if D[i, j] >= INF: continue
            c = D[i, j]; opts = []
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

# onsets checked by hand on the energy envelope where whisper drifts (seconds)
MANUAL = {("sen qolasan.", 1): 5.67, ("sen uning hayotidan o'chib ketasan.", 1): 8.05,
          ("Buni unga yubor...", 2): 22.77, ("izohlarda nechta odam \"bosadi\" deganini aytaman.", 4): 30.81}

def main(words_json, f32, out):
    from phrases import script_phrases, speech_phrases
    db, hop = energy_db(f32); mx = np.percentile(db, 99)
    k = np.hanning(9); k /= k.sum(); sm = np.convolve(db, k, mode="same")
    tr = [w for w in json.load(open(words_json)) if norm(w["w"])]
    sp = script_phrases(); ph, _ = speech_phrases(f32, len(sp))
    # whisper words in order -> script words in order (same count after merging split tokens like qo + 'yishdi)
    merged = []
    for w in tr:
        if merged and w["w"].startswith("'"): merged[-1] = {"w": merged[-1]["w"] + w["w"], "s": merged[-1]["s"], "e": w["e"]}
        else: merged.append(dict(w))
    flat = [w for p in sp for w in p]
    path = dp_align([w["text"] for w in flat], merged)
    for i, j, kind in path:
        if kind in ("11", "12"): flat[i]["ws"] = merged[j]["s"]
        elif kind == "21": flat[i]["ws"] = merged[j]["s"]; flat[i + 1]["ws"] = (merged[j]["s"] + merged[j]["e"]) / 2
    for i, w in enumerate(flat):
        if "ws" not in w: w["ws"] = flat[i - 1]["ws"] + 0.2
    res = []
    for (a, b), words in zip(ph, sp):
        i = int(a / hop)
        j = i
        while j > i - int(0.10 / hop) and sm[j - 1] > mx - 44: j -= 1   # include soft fricative onsets
        a = j * hop
        i0, i1 = int(a / hop), int(b / hop)
        seg = sm[i0:i1]
        pk, _ = find_peaks(seg, prominence=3, distance=int(0.09 / hop))
        nsyl = [syl(w["text"]) for w in words]
        phrase_txt = " ".join(w["text"] for w in words)
        onsets = [a]
        how = "whisper+dip"
        for wi in range(1, len(words)):
            # whisper is slightly early inside phrases: look for the closure/valley just around/after its estimate
            t = min(max(words[wi]["ws"], onsets[-1] + 0.12), b - 0.1)
            lo, hi = int((t - 0.06) / hop), int((t + 0.16) / hop)
            lo = max(lo, int((onsets[-1] + 0.1) / hop))
            v = lo + int(np.argmin(sm[lo:hi]))
            if sm[lo:hi].max() - sm[v] >= 4: t = v * hop + 0.015
            onsets.append(t)
        for wi, w in enumerate(words):
            key = (phrase_txt, wi)
            t = MANUAL.get(key, onsets[wi])
            w2 = {"scene": w["scene"], "text": w["text"], "first": w["first"], "start": round(t, 3), "how": "manual" if key in MANUAL else ("phrase" if wi == 0 else how)}
            res.append(w2)
        res[-1]["phrase_end"] = round(b, 3)
    res[0]["start"] = 0.0
    for k2, w in enumerate(res):
        nxt = res[k2 + 1]["start"] if k2 + 1 < len(res) else None
        w["end"] = round(w.get("phrase_end", nxt if nxt is not None else w["start"] + 0.3), 3)
        if "phrase_end" not in w and nxt is not None: w["end"] = round(nxt, 3)
    json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
    for w in res: print(f"{w['scene']:>2} {w['text']:<16} {w['start']:6.2f} {w['end']:6.2f} {w['how']}")

if __name__ == "__main__": main(*sys.argv[1:4])
