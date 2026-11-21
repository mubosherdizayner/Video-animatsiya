# Align script words to faster-whisper words (fuzzy, in order), interpolate gaps, snap onsets to audio energy.
import json, re, difflib, sys
import numpy as np
from script_data import SCENES
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

UNITS = "nol bir ikki uch toʻrt besh olti yetti sakkiz toʻqqiz".split()
TENS = ["", "oʻn", "yigirma", "oʻttiz", "qirq", "ellik", "oltmish", "yetmish", "sakson", "toʻqson"]
def num_uz(n):
    out = []
    if n >= 1000: out += [UNITS[n // 1000], "ming"]; n %= 1000
    if n >= 100: out += [UNITS[n // 100], "yuz"]; n %= 100
    if n >= 10: out += [TENS[n // 10]]; n %= 10
    if n: out += [UNITS[n]]
    return out

def expand(tr):
    """spell out digit tokens so they align to the written-out number words (times re-interpolated later)"""
    out = []
    for t in tr:
        d = re.sub(r"\D", "", t["w"])
        if d:
            for x in num_uz(int(d)): out.append({"w": x, "s": t["s"], "e": t["e"], "p": t["p"], "num": True})
        else: out.append(t)
    return out

def align(sw, tr):
    n, m = len(sw), len(tr); INF = 1e9
    D = np.full((n + 1, m + 1), INF); B = {}; D[0, 0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            if D[i, j] >= INF: continue
            c = D[i, j]; opts = []
            if i < n and j < m: opts.append((i + 1, j + 1, 1 - sim(sw[i], tr[j]["w"]), "11"))
            if i + 1 < n and j < m: opts.append((i + 2, j + 1, 1 - sim(sw[i] + sw[i + 1], tr[j]["w"]) + 0.3, "21"))
            for k in (2, 3):
                if i < n and j + k - 1 < m:
                    opts.append((i + 1, j + k, 1 - sim(sw[i], "".join(t["w"] for t in tr[j:j + k])) + 0.15 * (k - 1), "1%d" % k))
            if i < n: opts.append((i + 1, j, 0.9, "s0"))
            if j < m: opts.append((i, j + 1, 0.9, "0t"))
            for a, b, cost, k in opts:
                if c + cost < D[a, b]: D[a, b] = c + cost; B[(a, b)] = (i, j, k)
    path = []; a, b = n, m
    while (a, b) != (0, 0):
        i, j, k = B[(a, b)]; path.append((i, j, k)); a, b = i, j
    return path[::-1]

def energy_db(wav):
    x = np.fromfile(wav, dtype=np.float32); sr = 16000; hop = 80; win = 400
    fr = [x[i:i + win] for i in range(0, len(x) - win, hop)]
    rms = np.array([np.sqrt(np.mean(f * f)) + 1e-9 for f in fr])
    return 20 * np.log10(rms), hop / sr

def main(words_json, wav, out):
    tr = expand(json.load(open(words_json)))
    sw = []
    for sid, txt in SCENES:
        for k, w in enumerate(txt.split()): sw.append({"scene": sid, "text": w, "first": k == 0})
    path = align([w["text"] for w in sw], tr)
    times = [None] * len(sw)
    for i, j, k in path:
        if k == "11" and tr[j].get("num"): times[i] = None      # spoken number: timing by interpolation
        elif k == "11" and sim(sw[i]["text"], tr[j]["w"]) > 0.3: times[i] = [tr[j]["s"], tr[j]["e"], "m"]
        elif k == "21":
            s, e = tr[j]["s"], tr[j]["e"]; l1, l2 = len(norm(sw[i]["text"])), len(norm(sw[i + 1]["text"]))
            mid = s + (e - s) * l1 / (l1 + l2); times[i] = [s, mid, "split"]; times[i + 1] = [mid, e, "split"]
        elif k[0] == "1" and k != "11": times[i] = [tr[j]["s"], tr[j + int(k[1]) - 1]["e"], "m" + k[1]]
    for i in range(len(sw)):                      # interpolate unmatched words between matched neighbours
        if times[i] is None:
            p = max([q for q in range(i) if times[q]], default=None)
            q = min([q for q in range(i + 1, len(sw)) if times[q]], default=None)
            t0 = times[p][1] if p is not None else 0.0
            t1 = times[q][0] if q is not None else t0 + 0.5
            grp = list(range((p if p is not None else -1) + 1, q if q is not None else len(sw)))
            L = [len(norm(sw[g]["text"])) for g in grp]; tot = sum(L)
            acc = t0
            for g, l in zip(grp, L):
                times[g] = [acc, acc + (t1 - t0) * l / tot, "interp"]; acc = times[g][1]
    db, hop = energy_db(wav); mx = db.max(); sil = db < mx - 36
    runs = []; i = 0; n = len(sil)
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]: j += 1
            if (j - i) * hop >= 0.05: runs.append((i * hop + 0.0125, j * hop + 0.0125))
            i = j
        else: i += 1
    for k, w in enumerate(sw):                    # snap onset to the end of a pause right before it
        s, e, how = times[k]
        prev_s = times[k - 1][0] if k else -1
        cands = [r for r in runs if s - 0.15 <= r[1] <= s + 0.3 and r[1] < e - 0.08 and r[1] > prev_s + 0.05]
        if cands:
            ns = min(cands, key=lambda r: abs(r[1] - s))[1]
            times[k][0] = ns; times[k][2] = how + "+snap"
            if k and times[k - 1][1] > ns: times[k - 1][1] = ns
    sm = np.convolve(db, np.ones(3) / 3, mode="same")
    for k, w in enumerate(sw):                    # interpolated words: move onset to the nearest energy dip
        if times[k][2] != "interp" or not times[k - 1][2].startswith("interp"): continue   # group's first word keeps its anchor
        s = times[k][0]; a, b = int(max(s - 0.12, times[k - 1][0] + 0.1) / hop), int((s + 0.14) / hop)
        j = a + int(np.argmin(sm[a:b])); ctx = sm[max(0, j - 12):j + 12].max()
        if ctx - sm[j] >= 6:
            ns = j * hop + 0.02
            if ns > times[k - 1][0] + 0.08 and ns < times[k][1] + 0.12:
                times[k][0] = ns; times[k][2] = "interp+dip"; times[k - 1][1] = ns
                times[k][1] = max(times[k][1], ns + 0.08)
                if k + 1 < len(sw) and times[k + 1][2] == "interp": times[k + 1][0] = max(times[k + 1][0], times[k][1])
    times[0][0] = 0.0
    for k, w in enumerate(sw): w["start"], w["end"], w["how"] = round(times[k][0], 3), round(times[k][1], 3), times[k][2]
    json.dump(sw, open(out, "w"), ensure_ascii=False, indent=1)
    for w in sw: print(f"{w['scene']:>2} {w['text']:<20} {w['start']:6.2f} {w['end']:6.2f} {w['how']}")
if __name__ == "__main__": main(*sys.argv[1:4])
