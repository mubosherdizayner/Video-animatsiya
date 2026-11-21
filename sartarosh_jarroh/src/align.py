# Align script words (scene text) to faster-whisper word timestamps, then refine
# each onset with the audio energy envelope.  Output: timing.json
import json, re, sys, difflib, subprocess
import numpy as np
from script_data import SCENES, tokens

APOS = "ʻʼ'`‘’ʹ′"


def norm(w):
    w = w.lower()
    for a in APOS:
        w = w.replace(a, "'")
    return re.sub(r"[^a-zçğ']", "", w)


def fold(w):
    w = norm(w).replace("ç", "ch").replace("ğ", "g")
    w = w.replace("o'", "o").replace("g'", "g").replace("'", "")
    w = w.replace("x", "h").replace("q", "k").replace("sh", "s").replace("ch", "c").replace("ng", "n")
    w = re.sub(r"[aeiouy]", "a", w)
    return w


def sim(a, b):
    return difflib.SequenceMatcher(None, fold(a), fold(b)).ratio()


def merge_pieces(tr):
    out = []
    for r in tr:
        if out and (r["w"].startswith("'") or r["w"].startswith("-")):
            out[-1] = dict(out[-1], w=out[-1]["w"] + r["w"], e=r["e"])
        else:
            out.append(dict(r))
    return out


def dp_align(sw, tr):
    n, m = len(sw), len(tr)
    INF = 1e9
    D = np.full((n + 1, m + 1), INF)
    B = {}
    D[0, 0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            c = D[i, j]
            if c >= INF:
                continue
            opts = []
            if i < n and j < m:
                opts.append((1, 1, 1 - sim(sw[i], tr[j]["w"])))
            if i + 1 < n and j < m:
                opts.append((2, 1, 1 - sim(sw[i] + sw[i + 1], tr[j]["w"]) + 0.25))
            if i < n and j + 1 < m:
                opts.append((1, 2, 1 - sim(sw[i], tr[j]["w"] + tr[j + 1]["w"]) + 0.25))
            if i < n and j + 2 < m:
                opts.append((1, 3, 1 - sim(sw[i], tr[j]["w"] + tr[j + 1]["w"] + tr[j + 2]["w"]) + 0.45))
            if i + 1 < n and j + 1 < m:
                opts.append((2, 2, 1 - sim(sw[i] + sw[i + 1], tr[j]["w"] + tr[j + 1]["w"]) + 0.1))
            if i < n:
                opts.append((1, 0, 0.95))
            if j < m:
                opts.append((0, 1, 0.95))
            for di, dj, cost in opts:
                if c + cost < D[i + di, j + dj]:
                    D[i + di, j + dj] = c + cost
                    B[(i + di, j + dj)] = (i, j, di, dj)
    path = []
    a, b = n, m
    while (a, b) != (0, 0):
        i, j, di, dj = B[(a, b)]
        path.append((i, j, di, dj))
        a, b = i, j
    return path[::-1], D[n, m]


def envelope(audio_path, hop=0.005, win=0.02):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", audio_path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, dtype=np.float32)
    sr = 16000
    h, w = int(hop * sr), int(win * sr)
    n = (len(x) - w) // h + 1
    rms = np.array([np.sqrt(np.mean(x[k * h:k * h + w] ** 2) + 1e-12) for k in range(n)])
    db = 20 * np.log10(rms + 1e-9)
    return db, hop, win


def main(words_raw, audio, out):
    tr = merge_pieces(json.load(open(words_raw)))
    sw = []
    for sid, txt in SCENES:
        for k, w in enumerate(tokens(txt)):
            sw.append({"scene": sid, "text": w, "first": k == 0})
    path, cost = dp_align([w["text"] for w in sw], tr)
    times = [None] * len(sw)
    for i, j, di, dj in path:
        if di == 0 or dj == 0:
            continue
        s, e = tr[j]["s"], tr[j + dj - 1]["e"]
        if di == 1:
            times[i] = [s, e, f"m{dj}"]
        elif di == 2 and dj == 2 and min(sim(sw[i]["text"], tr[j]["w"]), sim(sw[i + 1]["text"], tr[j + 1]["w"])) >= 0.6:
            times[i] = [tr[j]["s"], tr[j]["e"], "m1"]
            times[i + 1] = [tr[j + 1]["s"], tr[j + 1]["e"], "m1"]
        else:  # several script words in whisper span(s): split by letters
            ls = [len(norm(sw[i + q]["text"])) for q in range(di)]
            acc = s
            for q in range(di):
                d = (e - s) * ls[q] / sum(ls)
                times[i + q] = [acc, acc + d, "split"]
                acc += d
    # fill gaps by interpolation
    for i in range(len(sw)):
        if times[i] is None:
            p = max([k for k in range(i) if times[k]], default=None)
            q = min([k for k in range(i + 1, len(sw)) if times[k]], default=None)
            t0 = times[p][1] if p is not None else 0.0
            t1 = times[q][0] if q is not None else t0 + 0.5
            cnt = (q if q is not None else len(sw)) - (p if p is not None else -1) - 1
            pos = i - (p if p is not None else -1)
            ds = (t1 - t0) / cnt
            times[i] = [t0 + ds * (pos - 1), t0 + ds * pos, "interp"]

    # ---- energy refinement
    db, hop, win = envelope(audio)
    off = win / 2  # frame k covers [k*hop, k*hop+win] -> centre
    t_of = lambda k: k * hop + off
    k_of = lambda t: int(round((t - off) / hop))
    peak = np.percentile(db, 99)
    sil_thr = peak - 40
    sil = db < sil_thr
    runs = []
    k = 0
    while k < len(sil):
        if sil[k]:
            j = k
            while j < len(sil) and sil[j]:
                j += 1
            if (j - k) * hop >= 0.05:
                runs.append((t_of(k), t_of(j)))
            k = j
        else:
            k += 1
    sm = np.convolve(db, np.ones(3) / 3, mode="same")
    for idx, w in enumerate(sw):
        s, e, how = times[idx]
        prev_s = times[idx - 1][0] if idx else -1
        # 1) a pause overlapping the whisper start -> onset = end of the pause
        cands = [r for r in runs if r[0] - 0.05 <= s + 0.06 and s - 0.06 <= r[1] <= s + 0.40 and r[1] > prev_s + 0.08]
        if cands:
            ns = min(cands, key=lambda r: abs(r[1] - s))[1]
            # back off to where energy rises above (thr + 6dB) - real onset
            k0 = k_of(ns)
            while k0 < len(db) - 1 and db[k0] < sil_thr + 4:
                k0 += 1
            ns = t_of(k0) - 0.01
            times[idx][0] = ns
            times[idx][2] = how + "+pause"
        else:
            # 2) dip in energy near the boundary (consonant closure / word gap)
            a, b = k_of(s - 0.07), k_of(s + 0.07)
            a = max(a, 1)
            b = min(b, len(sm) - 2)
            if b > a:
                seg = sm[a:b + 1]
                km = a + int(np.argmin(seg))
                left = sm[max(0, km - 24):km + 1].max()
                right = sm[km:km + 24].max()
                depth = min(left, right) - sm[km]
                if depth >= 6 and t_of(km) > prev_s + 0.08:
                    # onset = where energy climbs out of the dip
                    k1 = km
                    while k1 < len(sm) - 1 and sm[k1] < sm[km] + 0.35 * depth:
                        k1 += 1
                    times[idx][0] = t_of(k1) - 0.01
                    times[idx][2] = how + f"+dip{depth:.0f}"
        if idx:
            times[idx - 1][1] = min(times[idx - 1][1], times[idx][0]) if times[idx - 1][1] > times[idx][0] else times[idx - 1][1]
    times[0][0] = max(0.0, times[0][0])
    for k, w in enumerate(sw):
        w["start"], w["end"], w["how"] = round(times[k][0], 3), round(times[k][1], 3), times[k][2]
    json.dump(sw, open(out, "w"), ensure_ascii=False, indent=1)
    print("align cost", round(cost, 2))
    for w in sw:
        print(f"{w['scene']:>2} {w['text']:<22} {w['start']:6.3f} {w['end']:6.3f} {w['how']}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
