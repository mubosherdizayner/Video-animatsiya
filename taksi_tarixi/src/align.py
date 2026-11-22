# Align script words (subtitle source) to whisper word timestamps, then refine onsets with audio energy.
import json, re, difflib, sys, wave
import numpy as np
from script_data import SCENES
APOS = "ʻʼ'`‘’ʹ′"
def norm(w):
    w = w.lower()
    for a in APOS: w = w.replace(a, "'")
    return re.sub(r"[^a-z']", "", w)
def fold(w):
    w = norm(w).replace("o'", "o").replace("g'", "g").replace("'", "")
    for a, b in (("kh", "h"), ("x", "h"), ("q", "k"), ("sh", "s"), ("ch", "c"), ("ng", "n")): w = w.replace(a, b)
    return re.sub(r"[aeiouı]", "a", w)
def sim(a, b): return difflib.SequenceMatcher(None, fold(a), fold(b)).ratio()

def script_words():
    sw = []
    for sid, txt in SCENES:
        toks = [t for t in txt.split() if norm(t)]          # drop standalone dashes
        for k, w in enumerate(toks): sw.append({"scene": sid, "text": w, "first": k == 0})
    return sw

def dp_align(a, tr):
    n, m = len(a), len(tr); INF = 1e9
    D = np.full((n + 1, m + 1), INF); B = {}; D[0, 0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            if D[i, j] >= INF: continue
            c = D[i, j]; opts = []
            if i < n and j < m: opts.append((i + 1, j + 1, 1 - sim(a[i], tr[j]['w']), '11'))
            if i + 1 < n and j < m: opts.append((i + 2, j + 1, 1 - sim(a[i] + a[i + 1], tr[j]['w']) + 0.3, '21'))
            if i < n and j + 1 < m: opts.append((i + 1, j + 2, 1 - sim(a[i], tr[j]['w'] + tr[j + 1]['w']) + 0.3, '12'))
            if i < n: opts.append((i + 1, j, 0.9, 's0'))
            if j < m: opts.append((i, j + 1, 0.9, '0t'))
            for x, y, cost, k in opts:
                if c + cost < D[x, y]: D[x, y] = c + cost; B[(x, y)] = (i, j, k)
    path = []; x, y = n, m
    while (x, y) != (0, 0):
        i, j, k = B[(x, y)]; path.append((i, j, k)); x, y = i, j
    return path[::-1]

def energy_db(wav_path, hop=0.005):
    w = wave.open(wav_path); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    h = int(sr * hop); win = h * 4
    n = len(x) // h
    e = np.array([np.sqrt(np.mean(x[max(0, i * h - win // 2): i * h + win // 2] ** 2) + 1e-10) for i in range(n)])
    return 20 * np.log10(e), hop

def main(raw_json, clip_json, wav, out):
    tr = json.load(open(raw_json)); clip = json.load(open(clip_json))
    # replace the digit tokens ("1", ".891", "-ci", "yili") with the word-form re-transcription of that span
    c0, c1 = clip[0]['s'], clip[-1]['e']
    tr = [t for t in tr if not (c0 - 0.05 <= t['s'] < c1 - 0.05)] + clip
    tr.sort(key=lambda t: t['s'])
    sw = script_words()
    path = dp_align([w['text'] for w in sw], tr)
    times = [None] * len(sw)
    for i, j, k in path:
        if k == '11' and sim(sw[i]['text'], tr[j]['w']) > 0.3: times[i] = [tr[j]['s'], tr[j]['e'], 'm']
        elif k == '21':
            s, e = tr[j]['s'], tr[j]['e']; l1, l2 = len(norm(sw[i]['text'])), len(norm(sw[i + 1]['text']))
            mid = s + (e - s) * l1 / (l1 + l2); times[i] = [s, mid, 'split']; times[i + 1] = [mid, e, 'split']
        elif k == '12': times[i] = [tr[j]['s'], tr[j + 1]['e'], 'm2']
    for i in range(len(sw)):                                   # interpolate unmatched (by character count)
        if times[i] is None: print("UNMATCHED", sw[i]['text'])
    for i in range(len(sw)):
        if times[i] is None:
            p = i - 1; q = i
            while q < len(sw) and times[q] is None: q += 1
            t0 = times[p][1] if p >= 0 else 0.0; t1 = times[q][0] if q < len(sw) else t0 + 0.6
            L = [len(norm(sw[k]['text'])) for k in range(i, q)]; acc = 0
            for k in range(i, q):
                a = t0 + (t1 - t0) * acc / sum(L); acc += L[k - i]; b = t0 + (t1 - t0) * acc / sum(L)
                times[k] = [a, b, 'interp']
    # energy refinement: a word that follows a pause starts where the pause ends
    db, hop = energy_db(wav); mx = np.percentile(db, 99); sil = db < mx - 34
    runs = []; i = 0; n = len(sil)
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]: j += 1
            if (j - i) * hop >= 0.07: runs.append((i * hop, j * hop))
            i = j
        else: i += 1
    for k in range(len(sw)):
        s, e, how = times[k]
        prev_s = times[k - 1][0] if k else -1
        cands = [r for r in runs if s - 0.4 <= r[1] <= s + 0.40 and r[1] < e - 0.08 and r[1] > prev_s + 0.12]
        if cands:
            ns = min(cands, key=lambda r: abs(r[1] - s))[1]
            times[k][0] = round(ns, 3); times[k][2] = how + '+snap'
            if k and times[k - 1][1] > ns: times[k - 1][1] = ns
    times[0][0] = 0.0
    for k, w in enumerate(sw): w['start'], w['end'], w['how'] = round(times[k][0], 3), round(times[k][1], 3), times[k][2]
    json.dump(sw, open(out, 'w'), ensure_ascii=False, indent=1)
    for w in sw: print(f"{w['scene']:>2} {w['text']:<22} {w['start']:6.2f} {w['end']:6.2f} {w['how']}")
    json.dump({"runs": runs}, open(out.replace('.json', '_runs.json'), 'w'))
if __name__ == "__main__": main(*sys.argv[1:5])
