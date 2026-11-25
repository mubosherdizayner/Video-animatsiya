# Word timing: CTC forced alignment of the SCRIPT text (MMS-300m forced aligner, ONNX) on the voice-over.
# faster-whisper word timestamps (words.json) are kept as a cross-check; the script text is never replaced.
import json, sys, re, subprocess
import numpy as np
import onnxruntime as ort
from script_data import script_words

def norm_chars(w):
    w = w.lower()
    for a in "ʻʼ'`‘’—":
        w = w.replace(a, "")
    return re.sub(r"[^a-z]", "", w)

def load_audio(path):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32).copy()

def emissions(model_path, x):
    xn = (x - x.mean()) / np.sqrt(x.var() + 1e-7)
    so = ort.SessionOptions(); so.intra_op_num_threads = 4
    s = ort.InferenceSession(model_path, so, providers=["CPUExecutionProvider"])
    inp = {s.get_inputs()[0].name: xn[None, :].astype(np.float32)}
    if len(s.get_inputs()) > 1:
        inp[s.get_inputs()[1].name] = np.ones((1, len(xn)), np.int64)
    logits = s.run(None, inp)[0][0]
    lp = logits - logits.max(1, keepdims=True)
    lp = lp - np.log(np.exp(lp).sum(1, keepdims=True))
    return lp

def ctc_align(lp, tokens, blank=0):
    """Viterbi forced alignment; returns per-token (first_frame, last_frame)"""
    T, N = lp.shape[0], len(tokens)
    S = 2 * N + 1
    ext = [blank] * S
    for i, t in enumerate(tokens): ext[2 * i + 1] = t
    ext = np.array(ext)
    NEG = -1e18
    dp = np.full((T, S), NEG); bp = np.zeros((T, S), np.int8)
    dp[0, 0] = lp[0, ext[0]]; dp[0, 1] = lp[0, ext[1]]
    can2 = np.zeros(S, bool)
    for s in range(2, S):
        can2[s] = ext[s] != blank and ext[s] != ext[s - 2]
    for t in range(1, T):
        prev = dp[t - 1]
        c0 = prev
        c1 = np.concatenate([[NEG], prev[:-1]])
        c2 = np.where(can2, np.concatenate([[NEG, NEG], prev[:-2]]), NEG)
        st = np.stack([c0, c1, c2])
        k = st.argmax(0)
        dp[t] = st[k, np.arange(S)] + lp[t, ext]
        bp[t] = k
    s = S - 1 if dp[T - 1, S - 1] > dp[T - 1, S - 2] else S - 2
    path = np.zeros(T, int)
    for t in range(T - 1, -1, -1):
        path[t] = s
        s -= int(bp[t, s])
    spans = [[None, None] for _ in range(N)]
    for t, s in enumerate(path):
        if s % 2 == 1:
            i = s // 2
            if spans[i][0] is None: spans[i][0] = t
            spans[i][1] = t
    return spans

def main(model_path, audio_path, words_json, out):
    vocab = json.load(open(model_path.rsplit("/onnx/", 1)[0] + "/vocab.json"))
    x = load_audio(audio_path)
    lp = emissions(model_path, x)
    T = lp.shape[0]; fdur = len(x) / 16000 / T
    sw = script_words()
    toks, owner = [], []
    for i, w in enumerate(sw):
        for ch in norm_chars(w["text"]):
            toks.append(vocab[ch]); owner.append(i)
    spans = ctc_align(lp, toks)
    for i, w in enumerate(sw):
        idx = [k for k, o in enumerate(owner) if o == i]
        w["start"] = round(spans[idx[0]][0] * fdur, 3)
        w["end"] = round((spans[idx[-1]][1] + 1) * fdur, 3)
    # refine onsets: a voiced stop / weak fricative is emitted by CTC a little after its acoustic start.
    # If the 120 ms before the CTC onset holds a closure or pause, move the onset to where energy rises out of it.
    hop = 0.005; win = 320
    e = np.array([np.sqrt(np.mean(x[i:i + win] ** 2) + 1e-12) for i in range(0, len(x) - win, int(hop * 16000))])
    db = 20 * np.log10(e); db -= db.max()
    for i, w in enumerate(sw):
        s0 = w["start"]; a = max(0, int((s0 - 0.12) / hop)); b = int(s0 / hop) + 1
        if i:  # never before the previous word's end
            a = max(a, int(sw[i - 1]["end"] / hop))
        if b - a < 3: continue
        seg = db[a:b]; m = int(seg.argmin()); mn = seg[m]
        if mn > -38: continue           # no closure / pause: keep the CTC onset
        k = next((j for j in range(m, len(seg)) if seg[j] > mn + 10), None)
        if k is not None:
            w["ctc_start"] = s0
            w["start"] = round(min(s0, (a + k) * hop + win / 32000), 3)
    # cross-check against whisper
    wh = json.load(open(words_json))
    for i, w in enumerate(sw):
        near = min(wh, key=lambda r: abs(r["s"] - w["start"]))
        w["whisper_start"] = near["s"]
    json.dump({"frame_dur": fdur, "words": sw}, open(out, "w"), ensure_ascii=False, indent=1)
    for w in sw:
        print(f"{w['scene']:>2} {w['text']:<18} {w['start']:6.3f} {w['end']:6.2f} ctc {w.get('ctc_start', w['start']):6.2f} whisper {w['whisper_start']:6.2f}  d={w['start']-w['whisper_start']:+.2f}")

if __name__ == "__main__":
    main(*sys.argv[1:5])
