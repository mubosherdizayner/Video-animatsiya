# Script <-> transcript alignment and word timing.
#  1. speech intervals = audio between energy pauses (>= 0.1 s, 38 dB below peak)
#  2. faster-whisper transcribes every interval on its own (transcribe_iv.py) -> words tagged with their interval
#  3. the 74 script words are matched in order to the transcript words (lowercase, punctuation and ... — stripped,
#     apostrophes unified, Cyrillic transliterated, difflib similarity in an order-preserving DP)
#  4. a script word inherits the interval of its matched transcript word (unmatched: interpolated from neighbours)
#  5. inside an interval the first word starts at the pause end, the last ends at the next pause; inner
#     boundaries come from whisper (matched words) or a character-count split, then snap to the nearest energy dip
import json, re, difflib, sys
import numpy as np
from script_data import SCENES

APOS = "ʻʼ'`‘’ʹ′"
CYR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюяқғҳўі", ["a", "b", "v", "g", "d", "e", "yo", "j", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u", "f", "x", "ts", "ch", "sh", "sh", "", "i", "", "e", "yu", "ya", "q", "g'", "h", "o'", "i"]))
def translit(w):
    return "".join(CYR.get(ch, ch) for ch in w.lower())
def norm(w):
    w = translit(w)
    for a in APOS: w = w.replace(a, "'")
    w = w.replace("...", "").replace("—", "").replace("ı", "i").replace("ö", "o").replace("ç", "ch")
    return re.sub(r"[^a-z']", "", w)
def fold(w):
    w = norm(w).replace("o'", "o").replace("g'", "g").replace("'", "")
    w = w.replace("kh", "h").replace("x", "h").replace("q", "k").replace("sh", "s").replace("ch", "c").replace("ng", "n")
    return re.sub(r"[aeiou]", "a", w)
def sim(a, b): return difflib.SequenceMatcher(None, fold(a), fold(b)).ratio()

def align(sw, tr):
    n, m = len(sw), len(tr)
    INF = 1e9; D = np.full((n + 1, m + 1), INF); B = {}
    D[0, 0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            if D[i, j] >= INF: continue
            c = D[i, j]; opts = []
            if i < n and j < m: opts.append((i + 1, j + 1, 1 - sim(sw[i], tr[j]["w"]), "11"))
            if i + 1 < n and j < m: opts.append((i + 2, j + 1, 1 - sim(sw[i] + sw[i + 1], tr[j]["w"]) + 0.3, "21"))
            if i < n and j + 1 < m: opts.append((i + 1, j + 2, 1 - sim(sw[i], tr[j]["w"] + tr[j + 1]["w"]) + 0.3, "12"))
            if i + 1 < n and j + 1 < m: opts.append((i + 2, j + 2, 1 - sim(sw[i] + sw[i + 1], tr[j]["w"] + tr[j + 1]["w"]) + 0.25, "22"))
            if i < n: opts.append((i + 1, j, 0.9, "s0"))
            if j < m: opts.append((i, j + 1, 0.9, "0t"))
            for a, b, cost, k in opts:
                if c + cost < D[a, b]: D[a, b] = c + cost; B[(a, b)] = (i, j, k)
    path = []; a, b = n, m
    while (a, b) != (0, 0):
        i, j, k = B[(a, b)]; path.append((i, j, k)); a, b = i, j
    return path[::-1]

def speech_intervals(db, hop=0.005, rel=38, min_pause=0.1, dur=None):
    mx = db.max(); sil = db < mx - rel
    runs = []; i = 0; n = len(sil)
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]: j += 1
            if (j - i) * hop >= min_pause: runs.append((i * hop + 0.005, j * hop + 0.005))
            i = j
        else: i += 1
    iv = []; t = 0.0
    for a, b in runs:
        if a - t > 0.05: iv.append([t, a])
        t = b
    if dur and dur - t > 0.05: iv.append([t, dur])
    return iv

def main(iv_json, db_npy, out):
    ivt = json.load(open(iv_json))
    tr = []
    for j, blk in enumerate(ivt):
        for w in blk["words"]:
            tr.append(dict(w, iv=j))
    sw = []
    for sid, spk, txt in SCENES:
        for k, w in enumerate(txt.split()): sw.append({"scene": sid, "speaker": spk, "text": w, "first": k == 0})
    path = align([w["text"] for w in sw], tr)
    tm = [None] * len(sw)   # (iv, whisper start, whisper end, how)
    for i, j, k in path:
        if k == "11" and sim(sw[i]["text"], tr[j]["w"]) > 0.35: tm[i] = [tr[j]["iv"], tr[j]["s"], tr[j]["e"], "m"]
        elif k == "21":
            s, e = tr[j]["s"], tr[j]["e"]; l1, l2 = len(norm(sw[i]["text"])), len(norm(sw[i + 1]["text"]))
            mid = s + (e - s) * l1 / (l1 + l2)
            tm[i] = [tr[j]["iv"], s, mid, "split"]; tm[i + 1] = [tr[j]["iv"], mid, e, "split"]
        elif k == "12" and tr[j]["iv"] == tr[j + 1]["iv"]: tm[i] = [tr[j]["iv"], tr[j]["s"], tr[j + 1]["e"], "m2"]
        elif k == "22" and tr[j]["iv"] == tr[j + 1]["iv"]:   # e.g. "Bo burakia" -> "Bobur aka": re-split the span by characters
            s, e = tr[j]["s"], tr[j + 1]["e"]; l1, l2 = len(norm(sw[i]["text"])), len(norm(sw[i + 1]["text"]))
            mid = s + (e - s) * l1 / (l1 + l2)
            tm[i] = [tr[j]["iv"], s, mid, "split"]; tm[i + 1] = [tr[j]["iv"], mid, e, "split"]
    for i in range(len(sw)):   # unmatched -> interval of neighbours, no whisper time
        if tm[i] is None:
            p = max([q for q in range(i) if tm[q]], default=None); q = min([q for q in range(i + 1, len(sw)) if tm[q]], default=None)
            ivp = tm[p][0] if p is not None else 0
            ivq = tm[q][0] if q is not None else ivp
            tm[i] = [ivp if (ivp == ivq or sw[i]["first"] is False) else ivq, None, None, "interp"]
    db = np.load(db_npy); hop = 0.005
    def dip(t, rad=0.04):
        a, b = int((t - rad) / hop), int((t + rad) / hop) + 1
        seg = db[max(a, 0):b]
        if len(seg) < 3: return t
        sm = np.convolve(seg, np.ones(3) / 3, mode="same")
        idx = (np.arange(len(seg)) + max(a, 0)) * hop
        return float(idx[int(np.argmin(sm + 60 * np.abs(idx - t)))])
    res = [None] * len(sw)
    for j, blk in enumerate(ivt):
        ks = [k for k in range(len(sw)) if tm[k][0] == j]
        if not ks: continue
        a, b = blk["iv"]
        cl = [max(2, len(norm(sw[k]["text"]))) for k in ks]
        bounds = [a]
        for q in range(1, len(ks)):
            k = ks[q]
            frac = sum(cl[:q]) / sum(cl)
            tc = a + (b - a) * frac
            tw = tm[k][1] if tm[k][1] is not None and tm[k][3] != "split" else None
            if tm[k][3] == "split" and tm[k][1] is not None: tw = tm[k][1]
            t = tw if tw is not None and a + 0.05 < tw < b - 0.05 else tc
            bounds.append(dip(t))
        bounds.append(b)
        for q in range(1, len(bounds)):        # keep monotone with >= 2 frames per word
            bounds[q] = max(bounds[q], bounds[q - 1] + 0.067) if q < len(bounds) - 1 else bounds[q]
        for q, k in enumerate(ks):
            res[k] = [round(bounds[q], 3), round(bounds[q + 1], 3), tm[k][3] + "+iv"]
    res[0][0] = 0.0
    for k, w in enumerate(sw):
        w["start"], w["end"], w["how"] = res[k]
        w["iv"] = tm[k][0]
    json.dump(sw, open(out, "w"), ensure_ascii=False, indent=1)
    for w in sw: print(f"{w['scene']:>2} {w['text']:<20} {w['start']:6.2f} {w['end']:6.2f}  iv{w['iv']:<3} {w['how']}")
    assert all(sw[k]["start"] >= sw[k - 1]["start"] for k in range(1, len(sw)))

if __name__ == "__main__": main(*sys.argv[1:4])
