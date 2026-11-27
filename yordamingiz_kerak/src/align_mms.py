"""CTC forced alignment of the script words with the MMS aligner model (20 ms frames)."""
import json, re, sys, numpy as np, torch
from transformers import Wav2Vec2ForCTC
sys.path.insert(0, sys.argv[1]); from script_data import SENTENCES, SPOKEN
model_dir, audio, out = sys.argv[2:5]
vocab = json.load(open(model_dir + "/vocab.json"))
m = Wav2Vec2ForCTC.from_pretrained(model_dir).eval()
a = np.fromfile(audio, dtype=np.float32)
x = torch.from_numpy((a - a.mean()) / (a.std() + 1e-7))[None]
with torch.inference_mode():
    lp = torch.log_softmax(m(x).logits[0], -1).numpy()
T = lp.shape[0]; fr = len(a) / 16000 / T
words = []
for si, s in enumerate(SENTENCES):
    for wi, w in enumerate(s.split()):
        key = re.sub(r"[^a-z']", "", w.lower().replace("’", "'"))
        sp = SPOKEN.get(key.strip("'"), key).strip("'")
        toks = [vocab[c] for c in sp if c in vocab]
        words.append(dict(sent=si, idx=wi, text=w, toks=toks))
tok = []; owner = []
for k, w in enumerate(words):
    for t in w["toks"]: tok.append(t); owner.append(k)
# CTC Viterbi over extended sequence (blank between tokens)
ext = [0]; eo = [-1]
for t, o in zip(tok, owner): ext += [t, 0]; eo += [o, -1]
S_ = len(ext); NEG = -1e18
D = np.full((T, S_), NEG); B = np.zeros((T, S_), np.int8)
D[0, 0] = lp[0, ext[0]]; D[0, 1] = lp[0, ext[1]]
for t in range(1, T):
    prev = D[t - 1]
    c0 = prev; c1 = np.r_[NEG, prev[:-1]]; c2 = np.r_[NEG, NEG, prev[:-2]]
    ok2 = np.array([s >= 2 and ext[s] != 0 and ext[s] != ext[s - 2] for s in range(S_)])
    c2 = np.where(ok2, c2, NEG)
    st = np.stack([c0, c1, c2]); arg = st.argmax(0)
    D[t] = st[arg, np.arange(S_)] + lp[t, ext]; B[t] = arg
s = S_ - 1 if D[-1, -1] > D[-1, -2] else S_ - 2
path = [0] * T
for t in range(T - 1, -1, -1):
    path[t] = s; s -= int(B[t, s])
for k, w in enumerate(words):
    fs = [t for t in range(T) if eo[path[t]] == k]
    w["s"] = round(fs[0] * fr, 3); w["e"] = round((fs[-1] + 1) * fr, 3)
    w["conf"] = round(float(np.mean([lp[t, ext[path[t]]] for t in fs])), 2)
    del w["toks"]
json.dump(words, open(out, "w"), ensure_ascii=False, indent=1)
for w in words: print(f'{w["sent"]:2d} {w["text"]:16s} {w["s"]:6.2f} {w["e"]:6.2f} {w["conf"]}')
