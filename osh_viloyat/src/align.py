# Align script words (subtitle source) to faster-whisper word timestamps, then refine onsets from audio energy.
# Fallback (no transcript): split sentences by energy pauses and spread words by character count.
import json, re, difflib, sys, os
import numpy as np
from script_data import script_words

APOS = "ʻʼ'`‘’ʹ′"
SIL_DB = -54.0      # absolute level (dBFS, 10 ms RMS) treated as silence
HOP = 0.005


def norm(w):
    w = w.lower()
    for a in APOS: w = w.replace(a, "'")
    return re.sub(r"[^a-z'ğı]", "", w.replace("ğ", "g").replace("ı", "i"))


def fold(w):
    w = norm(w).replace("o'", "o").replace("g'", "g").replace("'", "")
    w = w.replace("kh", "h").replace("x", "h").replace("q", "k").replace("sh", "s").replace("ch", "c").replace("ng", "n")
    w = w.replace("j", "c")
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
            if i < n and j < m: opts.append((i + 1, j + 1, 1 - sim(sw[i], tr[j]['w']), '11'))
            if i + 1 < n and j < m: opts.append((i + 2, j + 1, 1 - sim(sw[i] + sw[i + 1], tr[j]['w']) + 0.3, '21'))
            if i < n and j + 1 < m: opts.append((i + 1, j + 2, 1 - sim(sw[i], tr[j]['w'] + tr[j + 1]['w']) + 0.3, '12'))
            if i < n: opts.append((i + 1, j, 0.9, 's0'))
            if j < m: opts.append((i, j + 1, 0.9, '0t'))
            for a, b, cost, k in opts:
                if c + cost < D[a, b]: D[a, b] = c + cost; B[(a, b)] = (i, j, k)
    path = []; a, b = n, m
    while (a, b) != (0, 0):
        i, j, k = B[(a, b)]; path.append((i, j, k)); a, b = i, j
    return path[::-1]


def silence_runs(db, min_len=0.06):
    sil = db < SIL_DB; runs = []; i = 0; n = len(sil)
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]: j += 1
            if (j - i) * HOP >= min_len: runs.append((i * HOP, j * HOP))
            i = j
        else: i += 1
    return runs


def energy_fallback(sw, db):
    """split into sentences by long pauses, spread words by character count"""
    runs = [r for r in silence_runs(db, 0.14)]
    speech = []; t = 0.0
    for a, b in runs:
        if a > t + 0.05: speech.append((t, a))
        t = b
    if len(db) * HOP > t + 0.05: speech.append((t, len(db) * HOP))
    sents = []; cur = []
    for w in sw:
        cur.append(w)
        if re.search(r"[.!?:…»]$", w["text"]): sents.append(cur); cur = []
    if cur: sents.append(cur)
    # merge speech islands to match sentence count
    while len(speech) > len(sents):
        gaps = [speech[i + 1][0] - speech[i][1] for i in range(len(speech) - 1)]
        i = int(np.argmin(gaps)); speech[i] = (speech[i][0], speech[i + 1][1]); del speech[i + 1]
    times = []
    for (a, b), sent in zip(speech, sents):
        L = [len(norm(w["text"])) + 1 for w in sent]; tot = sum(L); t = a
        for l in L: times.append([t, t + (b - a) * l / tot, "energy"]); t += (b - a) * l / tot
    return times


CTC_BIAS = 0.025   # MMS CTC emits the first character ~25 ms after the acoustic onset (measured at pause onsets)


def main(words_json, db_npy, out, ctc_json=None):
    sw = script_words()
    db = np.load(db_npy)
    if not os.path.exists(words_json):
        times = energy_fallback(sw, db)
    else:
        tr = json.load(open(words_json))
        path = align([w['text'] for w in sw], tr)
        times = [None] * len(sw)
        for i, j, k in path:
            if k == '11' and sim(sw[i]['text'], tr[j]['w']) > 0.3: times[i] = [tr[j]['s'], tr[j]['e'], 'w']
            elif k == '21':
                s, e = tr[j]['s'], tr[j]['e']; l1, l2 = len(norm(sw[i]['text'])), len(norm(sw[i + 1]['text']))
                mid = s + (e - s) * l1 / (l1 + l2); times[i] = [s, mid, 'split']; times[i + 1] = [mid, e, 'split']
            elif k == '12': times[i] = [tr[j]['s'], tr[j + 1]['e'], 'w2']
        for i in range(len(sw)):
            if times[i] is None:
                p = max([k for k in range(i) if times[k]], default=None); q = min([k for k in range(i + 1, len(sw)) if times[k]], default=None)
                t0 = times[p][1] if p is not None else 0.0; t1 = times[q][0] if q is not None else t0 + 0.5
                cnt = (q if q is not None else len(sw)) - (p if p is not None else -1) - 1; pos = i - (p if p is not None else -1)
                ds = (t1 - t0) / cnt
                times[i] = [t0 + ds * (pos - 1), t0 + ds * pos, 'interp']
    # --- replace whisper timings by CTC forced-alignment timings where available (tighter, same script words)
    if ctc_json and os.path.exists(ctc_json):
        cw = json.load(open(ctc_json))["words"]
        assert [c["text"] for c in cw] == [w["text"] for w in sw]
        ctc_end = [c["e"] for c in cw]
        for k, c in enumerate(cw):
            dev = c["s"] - times[k][0]
            times[k] = [max(0.0, c["s"] - CTC_BIAS), c["e"], f"ctc(w{dev:+.2f})"]
    else:
        ctc_end = [t[1] for t in times]
    # --- onset refinement from the energy envelope (5 ms hop)
    sm = np.convolve(db, np.ones(3) / 3, mode="same")

    def rise_point(j):
        """walk back from the end of a quiet stretch to where the sound starts leaving the floor"""
        k = j
        while k > 0 and sm[k - 1] > -56 and j - k < 8: k -= 1
        return k * HOP

    quiet = sm < -44
    for k in range(1, len(sw)):
        s, e, how = times[k]
        prev_s = times[k - 1][0]
        # 1) a quiet stretch (pause, dash pause, stop closure) just before the CTC onset -> onset where sound resumes
        # (the quiet stretch must come after the previous word's last emitted character: no stop closures inside it)
        lo = max(int((s - 0.15) / HOP), int((prev_s + 0.12) / HOP), int((ctc_end[k - 1] - 0.03) / HOP))
        hi = int((s + 0.03) / HOP)
        best = None; i = lo
        while i < hi:
            if quiet[i]:
                j = i
                while j < len(quiet) and quiet[j]: j += 1
                if (j - i) * HOP >= 0.035 and j <= hi + 6: best = j
                i = j
            else: i += 1
        if best is not None:
            times[k][0] = rise_point(best); times[k][2] = how + '+quiet'
            continue
        # 2) connected speech: snap to a clear energy dip within +-40 ms
        i0, i1 = max(int((s - 0.04) / HOP), int((prev_s + 0.08) / HOP) + 1), int((s + 0.04) / HOP)
        if i1 > i0:
            seg = sm[i0:i1]; im = i0 + int(np.argmin(seg))
            left = sm[max(0, im - 30):im].max() if im > 0 else sm[im]
            right = sm[im:im + 30].max()
            if min(left, right) - sm[im] >= 8:
                times[k][0] = im * HOP; times[k][2] = how + '+dip'
    for k in range(1, len(sw)):
        if times[k - 1][1] > times[k][0]: times[k - 1][1] = times[k][0]
    times[0][0] = 0.0
    for k, w in enumerate(sw):
        w['start'], w['end'], w['how'] = round(times[k][0], 3), round(times[k][1], 3), times[k][2]
    json.dump(sw, open(out, 'w'), ensure_ascii=False, indent=1)
    for w in sw: print(f"{w['scene']:>2} {w['text']:<22} {w['start']:6.3f} {w['end']:6.3f} {w['how']}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
