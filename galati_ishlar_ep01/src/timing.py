# Word timing: faster-whisper word timestamps per line clip -> aligned to the
# script words -> onsets snapped to the audio energy envelope -> timeline times.
# Fallback (model cannot load): pauses from audio energy, words spread by length.
import json, re, sys, difflib, os
import numpy as np
from config import *

APOS = "ʻʼ'`‘’"

def uz(word):
    """Typeset an ASCII-apostrophe Uzbek word with oʻ / gʻ / ʼ."""
    w = re.sub(r"([oOgG])'", lambda m: m.group(1) + "ʻ", word)
    return w.replace("'", "ʼ")

def script_words(line):
    toks = SCRIPT[line][1].split()
    out = []
    for t in toks:
        if out and not re.search(r"\w", t):      # "—" belongs to the previous word
            out[-1] += " " + t
        else:
            out.append(t)
    return out

CYR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюяәөүұқғңһіў",
               ["a","b","v","g","d","e","yo","j","z","i","y","k","l","m","n","o","p","r","s","t","u","f","x","ts","ch","sh","sh","","i","","e","yu","ya","a","o","u","u","q","g'","ng","h","i","o'"]))

def norm(w):
    w = "".join(CYR.get(ch, ch) for ch in w.lower())
    for a in APOS: w = w.replace(a, "'")
    w = w.replace("1980", "birmingtoqqizyuzsakson")
    return re.sub(r"[^a-z']", "", w)

def fold(w):
    w = norm(w).replace("o'", "o").replace("g'", "g").replace("'", "")
    for a, b in (("kh", "h"), ("x", "h"), ("q", "k"), ("sh", "s"), ("ch", "c"), ("ng", "n"), ("g", "k"), ("d", "t")):
        w = w.replace(a, b)
    return re.sub(r"[aeiouy]", "a", w)

def sim(a, b):
    return difflib.SequenceMatcher(None, fold(a), fold(b)).ratio()

def align(sw, tr):
    """DP alignment allowing 1:1, 2:1 (two script words in one token) and 1:k (k<=3)."""
    n, m = len(sw), len(tr)
    INF = 1e9
    D = np.full((n + 1, m + 1), INF); D[0, 0] = 0; B = {}
    for i in range(n + 1):
        for j in range(m + 1):
            if D[i, j] >= INF: continue
            c = D[i, j]; opts = []
            for k in (1, 2, 3):
                if i < n and j + k <= m:
                    joined = "".join(t["w"] for t in tr[j:j + k])
                    opts.append((i + 1, j + k, 1 - sim(sw[i], joined) + 0.25 * (k - 1), ("1", k)))
            if i + 1 < n and j < m:
                opts.append((i + 2, j + 1, 1 - sim(sw[i] + sw[i + 1], tr[j]["w"]) + 0.25, ("2", 1)))
            if i < n: opts.append((i + 1, j, 0.9, ("s", 0)))
            if j < m: opts.append((i, j + 1, 0.9, ("t", 1)))
            for a, b, cost, kind in opts:
                if c + cost < D[a, b]:
                    D[a, b] = c + cost; B[(a, b)] = (i, j, kind)
    path = []; a, b = n, m
    while (a, b) != (0, 0):
        i, j, kind = B[(a, b)]; path.append((i, j, kind)); a, b = i, j
    return path[::-1]

def energy_db(x, sr, hop=0.005, win=0.02):
    h, w = int(hop * sr), int(win * sr)
    n = max(1, (len(x) - w) // h)
    idx = np.arange(n)[:, None] * h + np.arange(w)[None, :]
    rms = np.sqrt((x[idx] ** 2).mean(1) + 1e-12)
    return 20 * np.log10(rms)

def silence_runs(db, hop=0.005, th=40, min_len=0.06):
    sil = db < db.max() - th
    runs, i, n = [], 0, len(sil)
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]: j += 1
            if (j - i) * hop >= min_len: runs.append((i * hop + 0.01, j * hop + 0.01))
            i = j
        else:
            i += 1
    return runs

def read_wav_f32(path):
    from scipy.io import wavfile
    sr, x = wavfile.read(path)
    x = x.astype(np.float32)
    if x.ndim > 1: x = x.mean(1)
    if np.abs(x).max() > 2: x /= 32768.0
    return x, sr

def whisper_words(model_dir, x16, cuts):
    from faster_whisper import WhisperModel
    m = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=4)
    res = {}
    for line, (a, b) in cuts.items():
        pad = np.zeros(int(0.3 * 16000), np.float32)
        clip = np.concatenate([pad, x16[int(a * 16000):int(b * 16000)], pad])
        segs, _ = m.transcribe(clip, language="uz", word_timestamps=True, beam_size=5,
                               vad_filter=False, condition_on_previous_text=False,
                               initial_prompt="Oʻzbek tilida, lotin alifbosida yozilgan hikoya.")
        res[line] = [{"w": w.word.strip(), "s": max(0.0, w.start - 0.3), "e": max(0.0, w.end - 0.3)}
                     for s in segs for w in s.words]
    return res

def fallback_words(x, sr, cuts):
    """Energy-pause segmentation, words spread by character count."""
    res = {}
    for line, (a, b) in cuts.items():
        sw = script_words(line)
        L = sum(len(norm(w)) or 1 for w in sw); t = 0.0; dur = b - a; out = []
        for w in sw:
            d = dur * (len(norm(w)) or 1) / L
            out.append({"w": w, "s": t, "e": t + d}); t += d
        res[line] = out
    return res

def refine_tokens(words, a):
    """Refine whisper token onsets on the energy envelope (global threshold):
    a) onset falls in / just before a pause -> token starts where the pause ends
    b) otherwise snap to a clear energy valley next to the whisper onset."""
    words = [dict(w) for w in words]
    for i in range(1, len(words)):
        s0, e0 = words[i]["s"], words[i]["e"]
        fa, fb = a + s0, a + e0
        prev = a + words[i - 1]["s"]
        hit = [r for r in GRUNS if (r[0] - 0.05 <= fa <= r[1] or fa <= r[0] <= fa + 0.15)
               and r[1] < fb - 0.05 and r[1] > prev + 0.08]
        if hit:
            r1 = max(r[1] for r in hit)
            # speech nucleus after the pause: first frame above (max - 30 dB), 20 ms lead
            k0 = int(r1 / 0.005); k1 = k0 + 50
            up = np.where(GDB[k0:k1] > GDB.max() - 30)[0]
            ns = max(r1, (k0 + up[0]) * 0.005 + 0.01 - 0.02) - a if len(up) else r1 - a
        else:
            i0 = int(max(fa - 0.08, prev + 0.08) / 0.005); i1 = int((fa + 0.12) / 0.005)
            w0, w1 = int(fa / 0.005), max(int(fb / 0.005), int(fa / 0.005) + 2)
            ns = s0
            if i1 > i0:
                k = i0 + int(np.argmin(GDB[i0:i1]))
                if GDB[k] < np.median(GDB[w0:w1]) - 10: ns = k * 0.005 + 0.01 - a
        words[i]["s"] = ns
        if words[i - 1]["e"] > ns: words[i - 1]["e"] = ns
    return words

def main(model_dir, out_json):
    x, sr = read_wav_f32(VOICE_WAV)
    x16 = x[::3].astype(np.float32)          # 48k -> 16k (energy content is speech band; whisper is robust)
    try:
        import scipy.signal as sps
        x16 = sps.resample_poly(x, 1, 3).astype(np.float32)
    except Exception:
        pass
    method = "faster-whisper word_timestamps"
    try:
        tr = whisper_words(model_dir, x16, LINE_CUTS)
    except Exception as e:
        print("whisper unavailable:", e, "-> fallback")
        tr = fallback_words(x, sr, LINE_CUTS); method = "fallback: energy pauses + char spread"
    out = {"method": method, "lines": {}}
    global GDB, GRUNS
    GDB = energy_db(x, sr); GRUNS = silence_runs(GDB, th=40, min_len=0.05)
    for line, (a, b) in LINE_CUTS.items():
        seg = x[int(a * sr):int(b * sr)]
        db = energy_db(seg, sr)
        runs = silence_runs(db)
        sw = script_words(line)
        words = refine_tokens(tr[line], a)
        path = align(sw, words)
        times = [None] * len(sw)
        for i, j, (kind, k) in path:
            if kind == "1":
                times[i] = [words[j]["s"], words[j + k - 1]["e"]]
            elif kind == "2":
                s, e = words[j]["s"], words[j]["e"]
                l1, l2 = len(norm(sw[i])), len(norm(sw[i + 1]))
                mid = s + (e - s) * l1 / (l1 + l2)
                times[i] = [s, mid]; times[i + 1] = [mid, e]
        for i in range(len(sw)):                 # interpolate any unmatched word
            if times[i] is None:
                p = max([q for q in range(i) if times[q]], default=None)
                nx = min([q for q in range(i + 1, len(sw)) if times[q]], default=None)
                t0 = times[p][1] if p is not None else 0.0
                t1 = times[nx][0] if nx is not None else (b - a)
                times[i] = [t0, t1]
        times[0][0] = 0.0
        # speech end of the clip
        loud = np.where(db > db.max() - 45)[0]
        speech_end = min(b - a, (loud[-1] + 1) * 0.005 + 0.02) if len(loud) else b - a
        times[-1][1] = speech_end
        for i in range(len(sw) - 1):             # contiguous highlighting
            times[i][1] = max(times[i][1], times[i + 1][0]) if times[i + 1][0] - times[i][1] < 0.6 else times[i][1]
        vs = VOICE_START[line]
        out["lines"][line] = {
            "speaker": SCRIPT[line][0], "voice_start": vs, "cut": [a, b], "clip_dur": round(b - a, 3),
            "words": [{"text": uz(w), "script": w, "start": round(vs + times[i][0], 3), "end": round(vs + times[i][1], 3),
                       "src": [round(a + times[i][0], 3), round(a + times[i][1], 3)]} for i, w in enumerate(sw)],
            "whisper": [t["w"] for t in words],
        }
    json.dump(out, open(out_json, "w"), ensure_ascii=False, indent=1)
    for line, L in out["lines"].items():
        a, b = L["cut"]; seg = x[int(a * sr):int(b * sr)]
        print("   silences(clip s):", [(round(r0, 2), round(r1, 2)) for r0, r1 in silence_runs(energy_db(seg, sr))])
        print(f"line {line} @ {L['voice_start']:.2f}s  ({L['clip_dur']:.2f}s)  whisper: {' '.join(L['whisper'])}")
        for w in L["words"]:
            print(f"   {w['text']:<18} {w['start']:7.3f} {w['end']:7.3f}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
