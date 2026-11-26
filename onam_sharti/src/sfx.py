# Soft synthesized SFX for the key actions only, ducked under the voice; mixed to 48 kHz stereo WAV.
import sys, json, wave
import numpy as np
from scipy.signal import butter, sosfilt, resample_poly
from timeline import *
import scenes as SC

SR = 48000
rs = np.random.RandomState(7)
def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, fc, order=2): return sosfilt(butter(order, fc, btype="low", fs=SR, output="sos"), x)
def hp(x, fc, order=2): return sosfilt(butter(order, fc, btype="high", fs=SR, output="sos"), x)
def norm(x): return x / (np.sqrt(np.mean(x ** 2)) + 1e-9)       # unit RMS
def env(n, a, d):
    t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)
def fade(n, fi, fo):
    e = np.ones(n); a = int(fi * SR); b = int(fo * SR)
    if a: e[:a] = np.sin(np.linspace(0, np.pi / 2, a)) ** 2
    if b: e[-b:] = np.cos(np.linspace(0, np.pi / 2, b)) ** 2
    return e

def soft_accent():            # warm low thump, no click
    n = int(1.2 * SR); t = np.arange(n) / SR
    f = 46 + 44 * np.exp(-t / 0.12)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.012, 0.35)
    y += 0.25 * lp(rs.randn(n), 400) * env(n, 0.01, 0.12)
    return norm(lp(y, 900))
def cloth(dur=0.34):
    n = int(dur * SR); y = bp(rs.randn(n), 700, 3200)
    am = np.zeros(n)
    for k in range(5):
        c = rs.uniform(0.02, dur - 0.08); w = rs.uniform(0.03, 0.08)
        am += np.exp(-((np.arange(n) / SR - c) / w) ** 2)
    return norm(lp(y * am * fade(n, 0.02, 0.1), 3500))
def flutter(dur=0.9):
    n = int(dur * SR); t = np.arange(n) / SR
    y = bp(rs.randn(n), 350, 1800) * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 7.5 * t)))
    return norm(y * np.sin(np.pi * t / dur) ** 2)
def leaf_rustle(dur=1.3):
    n = int(dur * SR); t = np.arange(n) / SR
    y = 0.4 * bp(rs.randn(n), 1500, 5000)
    for k in range(int(dur * 22)):
        c = int(rs.uniform(0, n - 400)); L = rs.randint(80, 300)
        y[c:c + L] += rs.randn(L) * np.exp(-np.arange(L) / (L / 4)) * rs.uniform(0.5, 1.5)
    y = lp(hp(y, 900), 5500)
    return norm(y * np.sin(np.pi * t / dur) ** 1.5)
def whoosh(dur=0.8, lo=250, hi=2400):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rs.randn(n); out = np.zeros(n); seg = 2400
    for s0 in range(0, n, seg):
        c = lo + (hi - lo) * np.sin(np.pi * min(1, (s0 + seg / 2) / n)) ** 2
        out[s0:s0 + seg] = bp(x[max(0, s0 - 2000):s0 + seg], c * 0.5, c * 1.4)[-len(out[s0:s0 + seg]):]
    return norm(lp(out, 4000) * np.sin(np.pi * t / dur) ** 1.8)
def fire(dur):
    n = int(dur * SR)
    bed = lp(rs.randn(n), 700) * 0.5
    y = bed.copy()
    for k in range(int(dur * 11)):
        c = int(rs.uniform(0, n - 600)); L = rs.randint(60, 500)
        y[c:c + L] += rs.randn(L) * np.exp(-np.arange(L) / (L / 5)) * rs.uniform(0.6, 2.2)
    return norm(lp(hp(y, 120), 4200) * fade(n, 0.35, 0.5))
def hum(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * 55 * t) + 0.45 * np.sin(2 * np.pi * 110 * t + 0.3) + 0.15 * np.sin(2 * np.pi * 165 * t)
    y *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.7 * t)
    e = np.minimum(1, t / 0.4) * np.clip((dur - t) / (dur * 0.55), 0, 1) ** 1.5
    return norm(lp(y * e, 400))
def wind(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    y = bp(rs.randn(n), 200, 1200) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.6 * t + 1.0))
    return norm(y * fade(n, 0.4, 0.5))
def paper(dur=0.45):
    n = int(dur * SR); y = np.zeros(n)
    for k in range(18):
        c = int(rs.uniform(0, n - 500)); L = rs.randint(100, 450)
        y[c:c + L] += bp(rs.randn(L + 200), 1800, 6000)[200:] * np.exp(-np.arange(L) / (L / 3))
    return norm(lp(y, 6500) * fade(n, 0.03, 0.1))

def build(voice):
    n = len(voice)
    L_ = np.zeros(n); R_ = np.zeros(n)
    def add(sig, t0, gain_db, pan=0.0):
        i0 = int(t0 * SR); g = 10 ** (gain_db / 20)
        seg = sig[:max(0, n - i0)] * g
        L_[i0:i0 + len(seg)] += seg * np.sqrt(0.5 * (1 - pan)); R_[i0:i0 + len(seg)] += seg * np.sqrt(0.5 * (1 + pan))
    S = SC_START; E = SC_END
    tm = word(3, "moliyaviy"); td = word(4, "shart"); ty = word(12, "yuboring")
    ev = [  # (signal, start, dB relative to the sfx reference level, pan, label)
        (soft_accent(), 0.0, 0, 0.0, "0.0 s soft low accent"),
        (cloth(), SC.T_FREEZE - 0.02, -2, -0.3, "0.7 s cloth rustle"),
        (flutter(0.9), S[2] + 0.25, -6, 0.3, "scene 2 wing flutter"),
        (leaf_rustle(1.3), tm + 0.55, -4, 0.0, "scene 3 leaf rustle"),
        (whoosh(0.95, 200, 1800), td + 0.05, -3, 0.2, "scene 4 airy whoosh"),
        (fire(E[5] - S[5]), S[5], -4, -0.3, "scene 5 fire crackle"),
        (hum(1.7), S[6], 0, 0.0, "scene 6 low deep hum"),
        (wind(E[8] - S[8]), S[8], -4, 0.0, "scene 8 soft wind"),
        (paper(0.45), S[12] + 0.15, -4, 0.0, "scene 12 paper rustle"),
        (whoosh(0.55, 400, 2600), ty, -2, 0.4, "scene 12 throw whoosh"),
    ]
    rw = whoosh(SC.ROT1 - SC.ROT0 + 0.1, 300, 2200)
    tt = np.arange(len(rw)) / SR
    ev.append((rw * (0.75 + 0.25 * np.sin(2 * np.pi * 3.2 * tt)), SC.ROT0, -2, 0.0, "scene 13 rotating whoosh"))
    for sig, t0, g, pan, _ in ev: add(sig, t0, g, pan)
    return L_, R_, [(lab, round(t0, 3), g) for _, t0, g, _, lab in ev]

def main(voice_wav, out_wav, report):
    w = wave.open(voice_wav); sr = w.getframerate(); v = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    if w.getnchannels() == 2: v = v.reshape(-1, 2).mean(1)
    if sr != SR: v = resample_poly(v, SR, sr)
    total = int(round(N_FRAMES / FPS * SR))
    v = np.concatenate([v, np.zeros(max(0, total - len(v)))])[:total]
    v = v / (np.abs(v).max() + 1e-9) * 0.89            # peak -1 dBFS
    # voice activity envelope (50 ms RMS, smoothed) for ducking
    win = int(0.05 * SR); rms = np.sqrt(np.convolve(v ** 2, np.ones(win) / win, mode="same"))
    act = np.clip((20 * np.log10(rms + 1e-9) + 45) / 20, 0, 1)
    act = np.convolve(act, np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
    duck = 1 - 0.5 * act                                 # up to -6 dB under speech
    voice_rms = np.sqrt(np.mean(v[act > 0.5] ** 2))
    ref = voice_rms * 10 ** (-18 / 20)                   # SFX reference: 18 dB below the voice
    Ls, Rs, evs = build(v)
    Ls *= ref * duck; Rs *= ref * duck
    L_ = v * np.sqrt(0.5) * 1.41 + Ls; R_ = v * np.sqrt(0.5) * 1.41 + Rs
    pk = max(np.abs(L_).max(), np.abs(R_).max())
    if pk > 0.97: L_ /= pk / 0.97; R_ /= pk / 0.97
    st = np.stack([L_, R_], 1)
    with wave.open(out_wav, "wb") as o:
        o.setnchannels(2); o.setsampwidth(2); o.setframerate(SR); o.writeframes((st * 32767).astype(np.int16).tobytes())
    sfx = np.sqrt(Ls ** 2 + Rs ** 2)
    def db(x): return 20 * np.log10(x + 1e-12)
    info = dict(events=evs, voice_rms_db=round(db(voice_rms), 1), sfx_peak_rms_db=None)
    seg = int(0.4 * SR)
    peaks = [np.sqrt(np.mean(sfx[i:i + seg] ** 2)) for i in range(0, len(sfx) - seg, seg // 2)]
    info["sfx_loudest_400ms_rms_db"] = round(db(max(peaks)), 1)
    info["sfx_below_voice_db"] = round(db(voice_rms) - db(max(peaks)), 1)
    json.dump(info, open(report, "w"), indent=1)
    print(json.dumps(info, indent=1))

if __name__ == "__main__": main(*sys.argv[1:4])
