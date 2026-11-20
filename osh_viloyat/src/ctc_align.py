# CTC forced alignment of the script text to the voice-over with the MMS-300m forced-aligner (ONNX, 20 ms frames).
# Used to tighten faster-whisper word timestamps. Output: list of {"text","s","e"} per script word.
import sys, json, re, math
import numpy as np
import onnxruntime as ort
from script_data import script_words

SR = 16000
VOCAB = {'<blank>': 0, '<pad>': 1, '</s>': 2, '<unk>': 3, 'a': 4, 'i': 5, 'e': 6, 'n': 7, 'o': 8, 'u': 9, 't': 10,
         's': 11, 'r': 12, 'm': 13, 'k': 14, 'l': 15, 'd': 16, 'g': 17, 'h': 18, 'y': 19, 'b': 20, 'p': 21,
         'w': 22, 'c': 23, 'v': 24, 'j': 25, 'z': 26, 'f': 27, "'": 28, 'q': 29, 'x': 30}


def clean(w):
    w = w.lower()
    for a in "ʻʼ‘’`": w = w.replace(a, "'")
    w = re.sub(r"[^a-z']", "", w)
    return w.strip("'") if not re.search(r"[og]'", w) else w


def emissions(session, wav, window=30, context=2):
    ctx = context * SR; win = window * SR
    ext = math.ceil(len(wav) / win) * win - len(wav)
    pad = np.pad(wav, (ctx, ctx + ext))
    nwin = (len(pad) - 2 * ctx) // win
    outs = []
    for i in range(nwin):
        x = pad[i * win: i * win + win + 2 * ctx][None].astype(np.float32)
        outs.append(session.run(["logits"], {"input_values": x})[0])
    em = np.concatenate(outs, 0)
    cf = int(context * 1000 / 20)
    em = em[:, cf:-cf + 1].reshape(-1, em.shape[-1])
    ef = int(ext / SR * 1000 / 20)
    if ef > 0: em = em[:-ef]
    em = em - em.max(-1, keepdims=True)
    em = em - np.log(np.exp(em).sum(-1, keepdims=True))
    stride = len(wav) / SR / em.shape[0]
    return em.astype(np.float32), stride


def viterbi(lp, tokens, blank=0):
    """standard CTC forced alignment; returns state path (index into extended label seq) per frame"""
    T = lp.shape[0]; L = len(tokens)
    ext = [blank]
    for t in tokens: ext += [t, blank]
    S = len(ext); ext = np.array(ext)
    NEG = -1e30
    dp = np.full(S, NEG); dp[0] = lp[0, ext[0]]; dp[1] = lp[0, ext[1]]
    bp = np.zeros((T, S), np.int16)
    can_skip = np.zeros(S, bool)
    for s in range(2, S):
        can_skip[s] = ext[s] != blank and ext[s] != ext[s - 2]
    for t in range(1, T):
        stay = dp
        prev1 = np.concatenate([[NEG], dp[:-1]])
        prev2 = np.where(can_skip, np.concatenate([[NEG, NEG], dp[:-2]]), NEG)
        stack = np.stack([stay, prev1, prev2])
        arg = stack.argmax(0)
        dp = stack[arg, np.arange(S)] + lp[t, ext]
        bp[t] = arg
    s = S - 1 if dp[S - 1] >= dp[S - 2] else S - 2
    path = np.zeros(T, np.int64)
    for t in range(T - 1, -1, -1):
        path[t] = s
        s -= bp[t, s]
    return path, ext


def main(model, audio_f32, out):
    wav = np.fromfile(audio_f32, dtype=np.float32)
    so = ort.SessionOptions(); so.intra_op_num_threads = 4
    sess = ort.InferenceSession(model, so, providers=["CPUExecutionProvider"])
    em, stride = emissions(sess, wav)
    print("frames", em.shape, "stride", stride)
    sw = script_words()
    toks = []; owner = []
    for wi, w in enumerate(sw):
        c = clean(w["text"])
        for ch in c:
            toks.append(VOCAB.get(ch, 3)); owner.append(wi)
    path, ext = viterbi(em, toks)
    # token index for each frame (state s odd -> token (s-1)//2)
    first = {}; last = {}
    for t, s in enumerate(path):
        if s % 2 == 1:
            k = (s - 1) // 2; wi = owner[k]
            first.setdefault(wi, t); last[wi] = t
    res = []
    for wi, w in enumerate(sw):
        res.append({"text": w["text"], "s": round(first[wi] * stride, 3), "e": round((last[wi] + 1) * stride, 3)})
    json.dump({"stride": stride, "words": res}, open(out, "w"), ensure_ascii=False, indent=0)
    for r in res: print(f"{r['text']:<22} {r['s']:7.3f} {r['e']:7.3f}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
