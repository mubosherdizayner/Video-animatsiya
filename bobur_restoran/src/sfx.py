# Synthesised soft SFX (no downloads) + mix under the voice-over with ducking -> 48 kHz stereo wav.
import sys, math, wave
import numpy as np
from scipy.signal import lfilter
from scenes import SC_START, SC_END_FRAME, SC_FRAME, scene_words, word_frame, word_t, N_FRAMES, FPS
import scenes as SC

SR = 48000
rng = np.random.RandomState(7)

def env_ad(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)

def lowpass(x, fc):
    if np.ndim(fc) == 0:
        a = math.exp(-2 * math.pi * fc / SR)
        return lfilter([1 - a], [1, -a], x)
    fc = np.asarray(fc, float); y = np.zeros_like(x); s = 0.0
    al = np.exp(-2 * np.pi * fc / SR)
    for i in range(len(x)):
        s = (1 - al[i]) * x[i] + al[i] * s; y[i] = s
    return y

def bandpass(x, lo, hi): return lowpass(x, hi) - lowpass(x, lo)
def norm(x, peak=1.0): return x / (np.abs(x).max() + 1e-9) * peak

def sine_sweep(f0, f1, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)

def bell(f, dur=0.8, partials=((1, 1.0), (2.76, 0.35), (5.4, 0.12)), decay=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros(n)
    for m, a in partials:
        out += a * np.sin(2 * np.pi * f * m * t) * np.exp(-t / (decay / (1 + 0.6 * (m - 1))))
    return out * np.minimum(1, t / 0.004)

def mix_at(dst, src, t):
    o = int(t * SR); dst[o:o + len(src)] += src[:max(0, len(dst) - o)]

def whoosh(dur=0.26):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.randn(n)
    fc = 400 + 2400 * np.sin(np.pi * t / dur) ** 2
    y = lowpass(x, fc) - lowpass(x, fc * 0.25)
    return norm(y * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5)

def tuk(f0=150, f1=55, dur=0.18):
    y = sine_sweep(f0, f1, dur) * env_ad(int(dur * SR), 0.002, 0.06)
    nz = lowpass(rng.randn(int(dur * SR)) * env_ad(int(dur * SR), 0.001, 0.008), 1200) * 0.3
    return norm(y + nz)

def rewind(dur=0.3):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 700 * (110 / 700) ** (t / dur) * (1 + 0.06 * np.sin(2 * np.pi * 18 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)
    return norm(lowpass(y, 2500) * np.sin(np.pi * t / dur) ** 0.7)

def shimmer(dur=0.95):
    out = np.zeros(int(dur * SR) + SR // 2)
    notes = [523.25, 659.25, 783.99, 1046.5, 1318.5]
    for k, f in enumerate(notes):
        b = bell(f, 0.7, ((1, 1.0), (2.0, 0.12)), 0.3) * (0.75 + 0.06 * k)
        mix_at(out, b, k * dur / len(notes) * 0.8)
    n = len(out); t = np.arange(n) / SR
    out *= 0.7 + 0.3 * np.sin(2 * np.pi * 5.5 * t)
    return norm(lowpass(out, 6000))

def pop(dur=0.09):
    return norm(sine_sweep(620, 190, dur) * env_ad(int(dur * SR), 0.002, 0.03))

def ting():
    out = np.zeros(int(0.7 * SR))
    for k, f in enumerate((2093, 3136, 4186)):
        mix_at(out, bell(f, 0.6, ((1, 1.0), (2.0, 0.15)), 0.22) * (0.8 ** k), k * 0.035)
    return norm(lowpass(out, 7000))

def door_bell():
    out = np.zeros(int(1.2 * SR))
    mix_at(out, bell(1318, 0.9, decay=0.4), 0); mix_at(out, bell(1046, 1.0, decay=0.45), 0.14)
    return norm(lowpass(out, 6000))

def klak():
    n = int(0.12 * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.03) + 0.6 * bandpass(rng.randn(n), 600, 2500) * np.exp(-t / 0.008)
    return norm(lowpass(y * np.minimum(1, t / 0.001), 3500))

def chop():
    n = int(0.14 * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * 320 * t) * np.exp(-t / 0.025) + 0.5 * np.sin(2 * np.pi * 610 * t) * np.exp(-t / 0.015)
    y += 0.5 * bandpass(rng.randn(n), 400, 2200) * np.exp(-t / 0.01)
    return norm(lowpass(y * np.minimum(1, t / 0.0008), 3000))

def sigh(dur=0.8):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 260 * (170 / 260) ** (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = (np.sin(ph) + 0.3 * np.sin(2 * ph)) * np.sin(np.pi * t / dur) ** 1.5
    y += 0.15 * bandpass(rng.randn(n), 300, 1500) * np.sin(np.pi * t / dur) ** 2
    return norm(lowpass(y, 1600))

def reg_ding():
    out = np.zeros(int(1.0 * SR))
    mix_at(out, bell(1568, 0.8, ((1, 1.0), (2.0, 0.25), (3.0, 0.1)), 0.32), 0.0)
    return norm(lowpass(out, 7000))

def rustle(dur=1.4):
    n = int(dur * SR); t = np.arange(n) / SR
    x = bandpass(rng.randn(n), 1500, 6000)
    am = 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 7 * t + 2 * np.sin(2 * np.pi * 1.3 * t)))
    return norm(x * am * np.sin(np.pi * t / dur) ** 0.8)

def thump():
    n = int(0.3 * SR); t = np.arange(n) / SR
    y = sine_sweep(120, 48, 0.3) * np.exp(-t / 0.07) + 0.3 * lowpass(rng.randn(n), 500) * np.exp(-t / 0.02)
    return norm(lowpass(y * np.minimum(1, t / 0.002), 900))

def chak():
    n = int(0.1 * SR); t = np.arange(n) / SR
    y = bandpass(rng.randn(n), 900, 3800) * np.exp(-t / 0.012) + 0.5 * np.sin(2 * np.pi * 900 * t) * np.exp(-t / 0.015)
    return norm(y * np.minimum(1, t / 0.0006))

def claps(dur=0.9, n_cl=14):
    out = np.zeros(int(dur * SR) + SR // 4)
    for k in range(n_cl):
        tt = rng.uniform(0, dur * 0.85)
        m = int(0.05 * SR); t = np.arange(m) / SR
        c = bandpass(rng.randn(m), 700, 2600) * np.exp(-t / 0.012) * rng.uniform(0.5, 1.0)
        mix_at(out, c, tt)
    t = np.arange(len(out)) / SR
    return norm(lowpass(out, 3200) * np.clip(1.2 - t / dur, 0, 1))

def slap():
    n = int(0.16 * SR); t = np.arange(n) / SR
    y = bandpass(rng.randn(n), 250, 1800) * np.exp(-t / 0.025) + 0.6 * sine_sweep(200, 90, 0.16) * np.exp(-t / 0.04)
    return norm(lowpass(y * np.minimum(1, t / 0.001), 2200))

def low_fall(dur=0.55):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 330 * (160 / 330) ** (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return norm(lowpass((np.sin(ph) + 0.25 * np.sin(2 * ph)) * env_ad(n, 0.02, 0.3), 1800))

def drum_roll(dur):
    out = np.zeros(int(dur * SR) + SR // 4)
    t = 0.0
    while t < dur - 0.04:
        prog = t / dur
        mix_at(out, tuk(110 + 40 * prog, 60, 0.12) * (0.35 + 0.65 * prog), t)
        t += 0.17 * (1 - prog) + 0.045 * prog
    return norm(out[:int(dur * SR)])

def chime():
    out = np.zeros(int(1.2 * SR))
    mix_at(out, bell(1046, 1.1, ((1, 1.0), (2, 0.4), (3, 0.15), (4.2, 0.08)), 0.5), 0)
    mix_at(out, bell(1568, 1.0, ((1, 0.7), (2, 0.25)), 0.4) * 0.6, 0.03)
    return norm(lowpass(out, 7000))

def plane_whoosh(dur=0.55):
    n = int(dur * SR); t = np.arange(n) / SR
    fc = 900 + 3200 * (t / dur) ** 1.5
    y = lowpass(rng.randn(n), fc) - lowpass(rng.randn(n) * 0, 1)
    y = bandpass(y, 500, 6000) * np.sin(np.pi * t / dur) ** 1.6
    return norm(y)

def events():
    S = SC_START
    ev = []
    def add(t, snd, db): ev.append((t, snd, db))
    t_ol1 = word_t(1, "oling")
    add(0.0, whoosh(0.24), -27); add(t_ol1, tuk(), -19)
    add(S[2], rewind(0.3), -21)
    add(S[3] + 0.02, shimmer(0.9), -24)
    add(S[4] + 0.0, pop(), -19); add(S[4] + 0.28, ting(), -24)
    add(S[5] + 0.04, door_bell(), -26)
    ts = S[6] + word_t(6, "ofitsiant")
    add(ts, klak(), -19); add(ts + 0.07, klak(), -21)
    add(S[7], whoosh(0.22), -20); add(S[7] + word_t(7, "oling"), tuk(), -19)
    for c0 in (0.12, 0.45, 0.78): add(S[8] + c0, chop(), -19)
    add(S[8] + word_t(8, "kameraga") + 0.05, sigh(0.8), -24)
    add(S[9] + 0.02, reg_ding(), -22); add(S[9] + 0.15, rustle(1.6), -28)
    add(S[10] + word_t(10, "keldim"), thump(), -19)
    add(S[11] + 0.18, chak(), -19); add(S[11] + 1.15, claps(0.9), -25)
    add(S[12] + 0.35, slap(), -18); add(S[12] + 0.5, low_fall(), -23)
    add(S[13] + 0.02, drum_roll(SC_END_FRAME[13] / FPS - S[13] - 0.12), -25)
    add(S[14] - 0.03, pop(), -21); add(S[14] + 0.12, chime(), -28)
    add(S[15] + word_t(15, "yuboring"), plane_whoosh(0.55), -22)
    add(S[16] + 0.08, pop(), -19)
    add(S[17] + 0.08, whoosh(0.3), -22)
    return ev

def read_wav(path):
    w = wave.open(path); n = w.getnframes(); ch = w.getnchannels()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32768
    if ch > 1: x = x.reshape(-1, ch).mean(1)
    return x, w.getframerate()

def main(voice_wav, out_wav, sfx_only_wav=None):
    v, sr = read_wav(voice_wav); assert sr == SR
    total = len(v)                          # output length = the voice-over length exactly
    voice = v.copy()
    vpk = np.abs(voice).max()
    sfx = np.zeros(total)
    evs = events()
    for t, snd, db in evs:
        o = int(round(t * SR))
        if o >= total: continue
        seg = snd[:total - o] * vpk * 10 ** (db / 20)
        sfx[o:o + len(seg)] += seg
    a = np.abs(voice)
    env = np.zeros(total); s = 0.0
    att = math.exp(-1 / (0.01 * SR)); rel = math.exp(-1 / (0.2 * SR))
    for i in range(0, total, 48):
        x = a[i:i + 48].max()
        s = (att if x > s else rel) * s + (1 - (att if x > s else rel)) * x
        env[i:i + 48] = s
    duck = 1 - 0.65 * np.clip(env / 0.05, 0, 1)
    mix = voice + sfx * duck
    pk = np.abs(mix).max()
    if pk > 0.97: mix = mix * 0.97 / pk
    st = np.stack([mix, mix], 1)
    w = wave.open(out_wav, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()
    if sfx_only_wav:
        w = wave.open(sfx_only_wav, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(sfx * duck, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()
    rms = lambda x: 20 * math.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
    print(f"voice rms {rms(voice):.1f} dB, sfx rms {rms(sfx * duck):.1f} dB, voice peak {20*math.log10(vpk):.1f}, "
          f"sfx peak {20*math.log10(np.abs(sfx*duck).max()):.1f}, events {len(evs)}, dur {total/SR:.3f}s")

if __name__ == "__main__":
    main(*sys.argv[1:])
