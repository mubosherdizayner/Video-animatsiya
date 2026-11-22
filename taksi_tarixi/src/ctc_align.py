# CTC forced alignment of the script text to the voice-over with the MMS-300m forced-aligner
# (wav2vec2) implemented in plain NumPy (no torch available). Gives character-level onsets (20 ms frames).
import json, re, sys, math
import numpy as np
from scipy.special import erf
from safetensors.numpy import safe_open

def gelu(x): return 0.5 * x * (1 + erf(x / math.sqrt(2)))
def ln(x, w, b, eps=1e-5):
    m = x.mean(-1, keepdims=True); v = ((x - m) ** 2).mean(-1, keepdims=True)
    return (x - m) / np.sqrt(v + eps) * w + b

class W2V:
    def __init__(self, path):
        f = safe_open(path, "np"); self.t = {k: f.get_tensor(k).astype(np.float32) for k in f.keys()}
    def g(self, k): return self.t[k]
    def __call__(self, wav):
        x = ((wav - wav.mean()) / np.sqrt(wav.var() + 1e-7)).astype(np.float32)[:, None]   # [T, C]
        ks, ss = [10, 3, 3, 3, 3, 2, 2], [5, 2, 2, 2, 2, 2, 2]
        for i, (k, s) in enumerate(zip(ks, ss)):
            p = f"wav2vec2.feature_extractor.conv_layers.{i}."
            w = self.g(p + "conv.weight")                       # [out, in, k]
            win = np.lib.stride_tricks.sliding_window_view(x, k, axis=0)[::s]   # [T', in, k]
            x = win.reshape(win.shape[0], -1) @ w.reshape(w.shape[0], -1).T + self.g(p + "conv.bias")
            x = gelu(ln(x, self.g(p + "layer_norm.weight"), self.g(p + "layer_norm.bias")))
        p = "wav2vec2.feature_projection."
        x = ln(x, self.g(p + "layer_norm.weight"), self.g(p + "layer_norm.bias"))
        x = x @ self.g(p + "projection.weight").T + self.g(p + "projection.bias")
        # positional conv (weight norm, dim=2), groups=16, k=128, pad=64, drop last frame
        p = "wav2vec2.encoder.pos_conv_embed.conv."
        gw = self.g(p + "parametrizations.weight.original0"); v = self.g(p + "parametrizations.weight.original1")
        w = gw * v / np.sqrt((v ** 2).sum(axis=(0, 1), keepdims=True))
        T = x.shape[0]; xp = np.pad(x, ((64, 64), (0, 0))); outs = []
        for gi in range(16):
            xg = xp[:, gi * 64:(gi + 1) * 64]
            win = np.lib.stride_tricks.sliding_window_view(xg, 128, axis=0)[:T]          # [T, 64in, 128]
            wg = w[gi * 64:(gi + 1) * 64]                                                 # [64out, 64in, 128]
            outs.append(win.reshape(T, -1) @ wg.reshape(64, -1).T)
        pos = gelu(np.concatenate(outs, 1) + self.g(p + "bias"))
        x = x + pos
        H = 16; D = 64
        for L in range(24):
            p = f"wav2vec2.encoder.layers.{L}."
            h = ln(x, self.g(p + "layer_norm.weight"), self.g(p + "layer_norm.bias"))
            q = (h @ self.g(p + "attention.q_proj.weight").T + self.g(p + "attention.q_proj.bias")) / math.sqrt(D)
            k = h @ self.g(p + "attention.k_proj.weight").T + self.g(p + "attention.k_proj.bias")
            vv = h @ self.g(p + "attention.v_proj.weight").T + self.g(p + "attention.v_proj.bias")
            q = q.reshape(T, H, D).transpose(1, 0, 2); k = k.reshape(T, H, D).transpose(1, 0, 2); vv = vv.reshape(T, H, D).transpose(1, 0, 2)
            a = q @ k.transpose(0, 2, 1); a -= a.max(-1, keepdims=True); a = np.exp(a); a /= a.sum(-1, keepdims=True)
            o = (a @ vv).transpose(1, 0, 2).reshape(T, H * D)
            x = x + o @ self.g(p + "attention.out_proj.weight").T + self.g(p + "attention.out_proj.bias")
            h = ln(x, self.g(p + "final_layer_norm.weight"), self.g(p + "final_layer_norm.bias"))
            h = gelu(h @ self.g(p + "feed_forward.intermediate_dense.weight").T + self.g(p + "feed_forward.intermediate_dense.bias"))
            x = x + h @ self.g(p + "feed_forward.output_dense.weight").T + self.g(p + "feed_forward.output_dense.bias")
        x = ln(x, self.g("wav2vec2.encoder.layer_norm.weight"), self.g("wav2vec2.encoder.layer_norm.bias"))
        lg = x @ self.g("lm_head.weight").T + self.g("lm_head.bias")
        lg -= lg.max(-1, keepdims=True)
        return lg - np.log(np.exp(lg).sum(-1, keepdims=True))      # log-probs [T, V]

APOS = "ʻʼ'`‘’ʹ′"
def chars(word, vocab):
    w = word.lower()
    for a in APOS: w = w.replace(a, "'")
    return [c for c in w if c in vocab and c not in "<>"]

def forced_align(lp, tokens, blank=0):
    """Viterbi CTC alignment. Returns for each token (start_frame, end_frame)."""
    T = lp.shape[0]; S = 2 * len(tokens) + 1
    ext = [blank if s % 2 == 0 else tokens[s // 2] for s in range(S)]
    NEG = -1e18; dp = np.full((T, S), NEG); bp = np.zeros((T, S), np.int32)
    dp[0, 0] = lp[0, blank]; dp[0, 1] = lp[0, ext[1]]
    for t in range(1, T):
        prev = dp[t - 1]
        c0 = prev; c1 = np.concatenate([[NEG], prev[:-1]]); c2 = np.concatenate([[NEG, NEG], prev[:-2]])
        allow2 = np.array([s % 2 == 1 and s >= 2 and ext[s] != ext[s - 2] for s in range(S)])
        c2 = np.where(allow2, c2, NEG)
        stack = np.stack([c0, c1, c2]); arg = stack.argmax(0)
        dp[t] = stack.max(0) + lp[t, ext]; bp[t] = arg
    s = S - 1 if dp[T - 1, S - 1] > dp[T - 1, S - 2] else S - 2
    path = [0] * T
    for t in range(T - 1, -1, -1):
        path[t] = s; s -= bp[t, s]
    spans = {}
    for t, s in enumerate(path):
        if s % 2 == 1:
            i = s // 2
            if i not in spans: spans[i] = [t, t]
            spans[i][1] = t
    return [spans.get(i) for i in range(len(tokens))]

if __name__ == "__main__":
    model_dir, wav16, words_json, out = sys.argv[1:5]
    vocab = json.load(open(model_dir + "/vocab.json"))
    wav = np.fromfile(wav16, dtype=np.float32)
    import os, time
    cache = out + ".lp.npy"
    if os.path.exists(cache): lp = np.load(cache)
    else:
        t0 = time.time(); lp = W2V(model_dir + "/model.safetensors")(wav); np.save(cache, lp); print("model", time.time() - t0)
    words = json.load(open(words_json))
    toks = []; owner = []
    for wi, w in enumerate(words):
        txt = w["text"]
        if w["scene"] == 7 and False: pass
        cs = chars(txt, vocab)
        for c in cs: toks.append(vocab[c]); owner.append(wi)
    spans = forced_align(lp, toks)
    stride = 320 / 16000
    res = []
    for wi, w in enumerate(words):
        idx = [i for i, o in enumerate(owner) if o == wi]
        sp = [spans[i] for i in idx if spans[i]]
        s = sp[0][0] * stride; e = (sp[-1][1] + 1) * stride
        res.append(dict(w, ctc_start=round(s, 3), ctc_end=round(e, 3)))
    json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
    for r in res: print(f"{r['scene']:>2} {r['text']:<18} whisper {r['start']:6.2f}  ctc {r['ctc_start']:6.2f}-{r['ctc_end']:6.2f}  d={r['ctc_start']-r['start']:+.2f}")
