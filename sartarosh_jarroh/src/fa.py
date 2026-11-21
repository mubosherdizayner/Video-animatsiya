# Refine word onsets: CTC forced alignment of the *script* text against the audio
# (wav2vec2 MMS-300m forced-aligner, 20 ms frames).  Whisper timings (timing_whisper.json)
# are the coarse reference / fallback; the result is written to timing.json.
import json, re, sys, subprocess
import numpy as np

APOS = "ʻʼ'`‘’ʹ′"


def letters(w):
    w = w.lower()
    for a in APOS:
        w = w.replace(a, "'")
    return re.sub(r"[^a-z']", "", w)


def ctc_viterbi(logp, tokens, blank=0):
    """logp: T x V log-probs, tokens: list of ids -> per-token (first_frame, last_frame)"""
    T = logp.shape[0]
    L = len(tokens)
    S = 2 * L + 1
    ext = np.full(S, blank)
    ext[1::2] = tokens
    NEG = -1e18
    dp = np.full(S, NEG)
    dp[0] = logp[0, blank]
    dp[1] = logp[0, ext[1]]
    bp = np.zeros((T, S), dtype=np.int8)  # 0 stay, 1 from s-1, 2 from s-2
    allow2 = np.zeros(S, dtype=bool)
    for s in range(2, S):
        allow2[s] = ext[s] != blank and ext[s] != ext[s - 2]
    for t in range(1, T):
        stay = dp
        m1 = np.concatenate([[NEG], dp[:-1]])
        m2 = np.concatenate([[NEG, NEG], dp[:-2]])
        m2 = np.where(allow2, m2, NEG)
        stack = np.stack([stay, m1, m2])
        arg = np.argmax(stack, axis=0)
        dp = stack[arg, np.arange(S)] + logp[t, ext]
        bp[t] = arg
    s = S - 1 if dp[S - 1] > dp[S - 2] else S - 2
    path = [0] * T
    for t in range(T - 1, -1, -1):
        path[t] = s
        s -= int(bp[t, s])
    spans = [[None, None] for _ in range(L)]
    for t, s in enumerate(path):
        if s % 2 == 1:
            k = s // 2
            if spans[k][0] is None:
                spans[k][0] = t
            spans[k][1] = t
    return spans


def main(model_dir, audio_path, timing_in, timing_out):
    import torch
    from transformers import Wav2Vec2ForCTC
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", audio_path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, dtype=np.float32).copy()
    x = (x - x.mean()) / (x.std() + 1e-7)
    vocab = json.load(open(f"{model_dir}/vocab.json"))
    model = Wav2Vec2ForCTC.from_pretrained(model_dir).eval()
    torch.set_num_threads(4)
    with torch.inference_mode():
        logits = model(torch.from_numpy(x)[None]).logits[0]
        logp = torch.log_softmax(logits.float(), dim=-1).numpy()
    T = logp.shape[0]
    fdur = len(x) / 16000 / T  # ~0.02 s
    words = json.load(open(timing_in))
    toks, owner = [], []
    for i, w in enumerate(words):
        for ch in letters(w["text"]):
            toks.append(vocab[ch])
            owner.append(i)
    spans = ctc_viterbi(logp, toks, blank=vocab["<blank>"])
    first, last = {}, {}
    for k, (a, b) in enumerate(spans):
        i = owner[k]
        if a is None:
            continue
        first.setdefault(i, a)
        last[i] = b
    print(f"frames {T}, frame {fdur*1000:.1f} ms")
    ctc = []
    for i, w in enumerate(words):
        fs = first[i] * fdur
        fe = (last[i] + 1) * fdur
        w["whisper_start"] = w["start"]
        w["ctc_start"], w["ctc_end"] = round(fs, 3), round(fe, 3)
        ctc.append((fs, fe))
    json.dump([dict(w, start=w["ctc_start"], end=w["ctc_end"]) for w in words],
              open(timing_out.replace(".json", "_ctc.json"), "w"), ensure_ascii=False, indent=1)

    # ---- energy snap between previous word's last letter and this word's first letter
    from align import envelope
    db, hop, win = envelope(audio_path)
    off = win / 2
    t_of = lambda k: k * hop + off
    k_of = lambda t: max(0, min(len(db) - 1, int(round((t - off) / hop))))
    sm = np.convolve(db, np.ones(3) / 3, mode="same")
    sil_thr = np.percentile(db, 99) - 40
    for i, w in enumerate(words):
        fs, fe = ctc[i]
        pe = ctc[i - 1][1] if i else 0.0
        if abs(fs - w["whisper_start"]) > 0.6:
            raise SystemExit(f"CTC and whisper disagree grossly at {w['text']}")
        a, b = k_of(min(pe, fs) - 0.03), k_of(fs + 0.03)
        how = "ctc"
        start = fs
        seg = sm[a:b + 1]
        quiet = np.nonzero(db[a:b + 1] < sil_thr + 3)[0]
        if len(quiet) >= 10:  # a pause (>= 50 ms) -> onset where energy climbs out of it
            k1 = a + quiet[-1]
            while k1 < len(db) - 1 and db[k1] < sil_thr + 6:
                k1 += 1
            start, how = t_of(k1) - 0.005, "ctc+pause"
        elif len(seg) >= 3:
            km = a + int(np.argmin(seg))
            left = sm[max(0, km - 20):km + 1].max()
            right = sm[km:km + 20].max()
            depth = min(left, right) - sm[km]
            if depth >= 5:
                k1 = km
                while k1 < len(sm) - 1 and sm[k1] < sm[km] + 0.35 * depth:
                    k1 += 1
                start, how = t_of(k1) - 0.005, f"ctc+dip{depth:.0f}"
            elif fs - pe > 0.08:
                start, how = max(fs - 0.1, (pe + fs) / 2), "ctc+mid"
        start = min(start, fs + 0.03)
        if i:
            start = max(start, words[i - 1]["start"] + 0.08)
        if i == 0:
            start = max(0.0, start)
        w["start"], w["end"], w["how"] = round(start, 3), round(fe, 3), how
        print(f"{w['scene']:>2} {w['text']:<22} whisper {w['whisper_start']:6.3f}  ctc {fs:6.3f}  final {start:6.3f}  {how}")
    for i in range(1, len(words)):
        words[i - 1]["end"] = max(words[i - 1]["start"] + 0.05, min(words[i - 1]["end"], words[i]["start"]))
    json.dump(words, open(timing_out, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:5])
