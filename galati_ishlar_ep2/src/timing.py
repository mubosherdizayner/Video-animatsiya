"""Voice-over -> 8 clips + word timings + final scene timeline.
Usage: timing.py vo_raw.wav words_whisper.json outdir"""
import json, re, sys, difflib, os
import numpy as np, scipy.io.wavfile as wf
from data import VOICE_LINES, SCENES

HOP = 0.005
PRE, POST, FADE = 0.05, 0.12, 0.015
APOS = "ʻʼ'`‘’"

def norm(w):
    w = w.lower()
    for a in APOS: w = w.replace(a, "'")
    return re.sub(r"[^a-z']", "", w)
def fold(w):
    w = norm(w).replace("'", "")
    for a, b in (("kh", "h"), ("x", "h"), ("q", "k"), ("sh", "s"), ("ch", "c"), ("ng", "n")): w = w.replace(a, b)
    return re.sub(r"[aeiou]", "a", w)
def sim(a, b): return difflib.SequenceMatcher(None, fold(a), fold(b)).ratio()

def align(sw, tr):
    n, m = len(sw), len(tr); INF = 1e9
    D = np.full((n + 1, m + 1), INF); D[0, 0] = 0; B = {}
    for i in range(n + 1):
        for j in range(m + 1):
            if D[i, j] >= INF: continue
            c = D[i, j]; opts = []
            if i < n and j < m: opts.append((i + 1, j + 1, 1 - sim(sw[i], tr[j]["w"]), "11"))
            if i + 1 < n and j < m: opts.append((i + 2, j + 1, 1 - sim(sw[i] + sw[i + 1], tr[j]["w"]) + 0.3, "21"))
            if i < n: opts.append((i + 1, j, 0.9, "s0"))
            if j < m: opts.append((i, j + 1, 0.9, "0t"))
            for a, b, cost, k in opts:
                if c + cost < D[a, b]: D[a, b] = c + cost; B[(a, b)] = (i, j, k)
    path = []; a, b = n, m
    while (a, b) != (0, 0):
        i, j, k = B[(a, b)]; path.append((i, j, k)); a, b = i, j
    return path[::-1]

def runs(mask, min_len):
    out = []; i = 0; n = len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]: j += 1
            if (j - i) * HOP >= min_len: out.append((i * HOP, j * HOP))
            i = j
        else: i += 1
    return out

def main(wav, wjson, outdir):
    sr, x = wf.read(wav); x = x.astype(np.float32)
    hop = int(sr * HOP); n = len(x) // hop
    db = 20 * np.log10(np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1)) + 1e-9)
    mx = db.max(); rel = db - mx
    # 1) leading silence
    onset0 = float(np.argmax(rel > -40) * HOP)
    trim = False  # prep.py already trimmed any lead-in > 0.3 s before transcription
    print(f"leading silence {onset0:.3f}s")
    long_sil = runs(rel < -42, 0.15)
    gaps = runs(rel < -30, 0.03)
    deep = runs(rel < -42, 0.01)
    # 2) whisper words -> script words
    tr = json.load(open(wjson))
    sw = []
    for lid, spk, txt in VOICE_LINES:
        toks = [t for t in txt.split() if norm(t)]
        for k, t in enumerate(toks): sw.append(dict(line=lid, text=t, k=k))
    path = align([w["text"] for w in sw], tr)
    T = [None] * len(sw)
    for i, j, k in path:
        if k == "11" and sim(sw[i]["text"], tr[j]["w"]) > 0.35: T[i] = [tr[j]["s"], tr[j]["e"], "whisper"]
        elif k == "21" and sim(sw[i]["text"], tr[j]["w"]) >= 0.85:
            T[i] = [tr[j]["s"], tr[j]["e"], "whisper"]  # token is really the first word only; second is interpolated
        elif k == "21":
            s, e = tr[j]["s"], tr[j]["e"]; l1, l2 = len(norm(sw[i]["text"])), len(norm(sw[i + 1]["text"]))
            mid = s + (e - s) * l1 / (l1 + l2); T[i] = [s, mid, "split"]; T[i + 1] = [mid, e, "split"]
    # 3) sentence (clip) bounds from energy pauses between lines
    lines = {}
    for lid, _, _ in VOICE_LINES:
        idx = [i for i, w in enumerate(sw) if w["line"] == lid]
        known = [T[i] for i in idx if T[i]]
        lines[lid] = dict(idx=idx, ws=min(t[0] for t in known), we=max(t[1] for t in known))
    ids = [v[0] for v in VOICE_LINES]
    bounds = {}
    for a, b in zip(ids, ids[1:]):
        lo, hi = lines[a]["we"] - 0.35, lines[b]["ws"] + 0.6
        cand = [r for r in long_sil if r[1] > lo and r[0] < hi]
        r = max(cand, key=lambda r: r[1] - r[0])
        bounds[(a, b)] = r
    for k, lid in enumerate(ids):
        on = onset0 if k == 0 else bounds[(ids[k - 1], lid)][1]
        if k == len(ids) - 1:
            tail = [r for r in long_sil if r[0] > lines[lid]["we"] - 0.3]
            off = tail[0][0] if tail else len(x) / sr
        else: off = bounds[(lid, ids[k + 1])][0]
        lines[lid].update(on=on, off=off)
    # clip cut points: inside the pauses (never past the pause midpoint)
    for k, lid in enumerate(ids):
        L = lines[lid]
        c0 = max(L["on"] - PRE, 0.0)
        if k: c0 = max(c0, sum(bounds[(ids[k - 1], lid)]) / 2)
        c1 = L["off"] + POST
        if k < len(ids) - 1: c1 = min(c1, sum(bounds[(lid, ids[k + 1])]) / 2)
        else: c1 = min(c1, len(x) / sr)
        L.update(c0=c0, c1=c1)
    # 4) word timings inside each clip: clamp to speech, interpolate missing, snap onsets to energy gaps
    for lid in ids:
        L = lines[lid]; idx = L["idx"]
        for p, i in enumerate(idx):
            if T[i] is None: continue
            T[i][0] = min(max(T[i][0], L["on"]), L["off"]); T[i][1] = min(max(T[i][1], L["on"]), L["off"])
        T[idx[0]] = [L["on"], T[idx[0]][1] if T[idx[0]] else None, (T[idx[0]] or [0, 0, "interp"])[2] + "+onset"]
        last = T[idx[-1]]
        T[idx[-1]] = [last[0] if last else None, L["off"], (last or [0, 0, "interp"])[2] + "+offset"]
        # fill gaps: any word whose start is None or whose end is None
        p = 0
        while p < len(idx):
            i = idx[p]
            if T[i][0] is not None and T[i][1] is not None and "interp" not in T[i][2]: p += 1; continue
            q = p
            while q < len(idx) and (T[idx[q]][0] is None or T[idx[q]][1] is None or "interp" in T[idx[q]][2]): q += 1
            t0 = T[idx[p - 1]][1] if p else L["on"]
            t1 = T[idx[q]][0] if q < len(idx) else L["off"]
            if p < len(idx) and T[idx[p]][0] is not None and "interp" in T[idx[p]][2]: t0 = T[idx[p]][0]
            if q - 1 >= 0 and T[idx[q - 1]][1] is not None and "interp" in T[idx[q - 1]][2]: t1 = T[idx[q - 1]][1]
            chars = [len(norm(sw[idx[r]]["text"])) for r in range(p, q)]; tot = sum(chars); acc = 0
            for r, c in zip(range(p, q), chars):
                T[idx[r]] = [t0 + (t1 - t0) * acc / tot, t0 + (t1 - t0) * (acc + c) / tot, "interp"]; acc += c
            p = q
        # make contiguous & monotonic; snap internal word starts to the end of a nearby energy gap
        for p in range(1, len(idx)):
            i, h = idx[p], idx[p - 1]
            s = T[i][0]
            cands = [g for g in gaps if s - 0.12 <= g[1] <= s + 0.2 and g[1] > T[h][0] + 0.12 and g[1] < T[i][1] - 0.06]
            if cands:
                g = min(cands, key=lambda g: abs(g[1] - s))
                inner = [d for d in deep if d[0] >= g[0] - 0.005 and d[1] <= g[1] + 0.005]
                T[i][0] = (inner[-1][1] if inner else g[1]) - 0.005; T[i][2] += "+snap"
                T[h][1] = min(T[h][1], g[0] + 0.01) if g[0] > T[h][0] else T[h][1]
            if T[h][1] > T[i][0]: T[h][1] = T[i][0]
    # 5) timeline: place clips, extend/shift scenes, cut scenes on words
    scenes = [dict(s) for s in SCENES]
    shift = 0.0
    clips = []
    for si, sc in enumerate(scenes):
        sc["start"] += shift; sc["end"] += shift
        if sc.get("vl"):
            sc["vat"] += shift
            lid = sc["vl"]; L = lines[lid]; clen = L["c1"] - L["c0"]
            span = [s for s in scenes if s.get("vl") == lid or s.get("cont") == lid]
            last = span[-1]
            slot_end = last["end"] + (shift if last is not sc else 0.0)
            clip_end = sc["vat"] + clen
            if clips and sc["vat"] < clips[-1]["t1"]:
                raise SystemExit("clips overlap")
            ext = max(0.0, clip_end - slot_end)
            if ext > 0:
                print(f"line {lid}: clip {clen:.3f}s longer than slot by {ext:.3f}s -> extend scene {last['id']} and shift later scenes")
                last["extend"] = ext
            clips.append(dict(line=lid, src0=L["c0"], src1=L["c1"], t0=sc["vat"], t1=clip_end))
        # apply extension when we reach the last scene of the span
        if sc.get("extend"):
            sc["end"] += sc["extend"]; shift += sc["extend"]
    # word timeline
    words = []
    for c in clips:
        L = lines[c["line"]]
        for i in L["idx"]:
            w = sw[i]; s, e, how = T[i]
            words.append(dict(line=c["line"], k=w["k"], text=w["text"], src_s=round(s, 3), src_e=round(e, 3),
                              t0=round(c["t0"] + s - c["src0"], 3), t1=round(c["t0"] + e - c["src0"], 3), how=how))
    # scenes that start on a word
    for k, sc in enumerate(scenes):
        if sc.get("sow"):
            w = [w for w in words if w["line"] == sc["cont"] and norm(w["text"]) == norm(sc["sow"])][0]
            sc["start"] = w["t0"]; scenes[k - 1]["end"] = w["t0"]
    for sc in scenes:
        sc["start"] = round(sc["start"], 3); sc["end"] = round(sc["end"], 3)
    out = dict(trimmed=trim, leading_silence=round(onset0, 3), duration=scenes[-1]["end"],
               lines={str(k): {kk: (round(v, 3) if isinstance(v, float) else v) for kk, v in L.items() if kk != "idx"} for k, L in lines.items()},
               clips=clips, words=words, scenes=scenes)
    json.dump(out, open(os.path.join(outdir, "timing.json"), "w"), ensure_ascii=False, indent=1)
    for c in clips: print(f"clip {c['line']}: src {c['src0']:.3f}-{c['src1']:.3f} ({c['src1']-c['src0']:.3f}s) -> {c['t0']:.3f}-{c['t1']:.3f}")
    for w in words: print(f"  L{w['line']} {w['text']:<12} src {w['src_s']:6.3f}-{w['src_e']:6.3f}  t {w['t0']:6.3f}-{w['t1']:6.3f} {w['how']}")
    for sc in scenes: print(f"scene {sc['id']:>2} {sc['start']:6.3f}-{sc['end']:6.3f} frame {sc['frame']}")
    print("duration", out["duration"], "last word end", words[-1]["t1"])

if __name__ == "__main__":
    main(*sys.argv[1:4])
