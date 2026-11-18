# Synthesised soft SFX + mix with the voice-over (ducked), output 48 kHz stereo wav.
import sys, math, wave, json
import numpy as np
from scenes import SC_START, SC_END_FRAME, SC_FRAME, scene_words, word_frame, fruit_rain, SLOTS, FLIP_ORDER, N_FRAMES, FPS, fruit_state
import scenes as SC

SR = 48000
rng = np.random.RandomState(7)

def env_ad(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)
    return e

def lowpass(x, fc):
    """time-varying one-pole lowpass; fc scalar or array"""
    fc = np.broadcast_to(np.asarray(fc, float), x.shape)
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.zeros_like(x); s = 0.0
    for i in range(len(x)):
        s = (1 - a[i]) * x[i] + a[i] * s; y[i] = s
    return y

def norm(x, peak=1.0):
    m = np.abs(x).max() + 1e-9
    return x / m * peak

def sine_sweep(f0, f1, dur, curve="exp"):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / dur) if curve == "exp" else f0 + (f1 - f0) * t / dur
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph)

def bell(f, dur=0.8, partials=((1, 1.0), (2.76, 0.35), (5.4, 0.12)), decay=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros(n)
    for m, a in partials:
        out += a * np.sin(2 * np.pi * f * m * t) * np.exp(-t / (decay / (1 + 0.6 * (m - 1))))
    out *= np.minimum(1, t / 0.004)
    return out

def whoosh(dur=0.26):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.randn(n)
    fc = 400 + 2600 * np.sin(np.pi * t / dur) ** 2
    y = lowpass(x, fc) - lowpass(x, fc * 0.25)
    y *= np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    return norm(y)

def tuk(f0=150, f1=55, dur=0.18):
    y = sine_sweep(f0, f1, dur) * env_ad(int(dur * SR), 0.002, 0.06)
    n = rng.randn(int(dur * SR)) * env_ad(int(dur * SR), 0.001, 0.008) * 0.3
    return norm(y + lowpass(n, 1200))

def rewind(dur=0.3):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 700 * (110 / 700) ** (t / dur) * (1 + 0.06 * np.sin(2 * np.pi * 18 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)
    y = lowpass(y, 2500) * np.sin(np.pi * t / dur) ** 0.7
    return norm(y)

def pop(dur=0.09):
    y = sine_sweep(620, 190, dur) * env_ad(int(dur * SR), 0.002, 0.03)
    return norm(y)

def ting():
    out = np.zeros(int(0.7 * SR))
    for k, f in enumerate((2093, 3136, 4186)):
        b = bell(f, 0.6, ((1, 1.0), (2.0, 0.15)), 0.22) * (0.8 ** k)
        o = int(k * 0.035 * SR); out[o:o + len(b)] += b[:len(out) - o]
    return norm(lowpass(out, 7000))

def swish(dur=0.32):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.randn(n)
    y = lowpass(x, 3200) - lowpass(x, 700)
    y *= np.sin(np.pi * t / dur) ** 2
    return norm(y)

def door_bell():
    a = bell(1318, 0.9, decay=0.4); b = bell(1046, 1.0, decay=0.45)
    out = np.zeros(int(1.2 * SR)); out[:len(a)] += a; o = int(0.14 * SR); out[o:o + len(b)] += b[:len(out) - o]
    return norm(lowpass(out, 6000))

def tick(f=1900, dur=0.03):
    y = np.sin(2 * np.pi * f * np.arange(int(dur * SR)) / SR) * env_ad(int(dur * SR), 0.001, 0.006)
    return norm(lowpass(y, 5000))

def flutter(dur=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.randn(n)
    y = (lowpass(x, 2600) - lowpass(x, 500)) * (0.55 + 0.45 * np.sin(2 * np.pi * 24 * t) ** 2)
    y *= np.sin(np.pi * t / dur) ** 1.2
    return norm(y)

def soft_ting():
    return norm(lowpass(bell(1760, 0.7, ((1, 1.0), (1.5, 0.3), (2.76, 0.15)), 0.28), 6500))

def drum_roll(dur):
    out = np.zeros(int(dur * SR) + SR // 4)
    t = 0.0; k = 0
    while t < dur - 0.04:
        prog = t / dur
        gap = 0.17 * (1 - prog) + 0.045 * prog
        th = tuk(110 + 40 * prog, 60, 0.12) * (0.35 + 0.65 * prog)
        o = int(t * SR); out[o:o + len(th)] += th[:len(out) - o]
        t += gap; k += 1
    return norm(out[:int(dur * SR)])

def chime():
    a = bell(1046, 1.1, ((1, 1.0), (2, 0.4), (3, 0.15), (4.2, 0.08)), 0.5)
    b = bell(1568, 1.0, ((1, 0.7), (2, 0.25)), 0.4)
    out = np.zeros(len(a)); out += a; o = int(0.03 * SR); out[o:o + len(b)] += b[:len(out) - o] * 0.6
    return norm(lowpass(out, 7000))

def boing(dur=0.28):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 180 + 260 * np.exp(-t / 0.05) * 0 + 160 * np.sin(np.pi * t / dur) + 30 * np.sin(2 * np.pi * 14 * t)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.004, 0.09)
    return norm(lowpass(y, 2500))

def bonk():
    n = int(0.22 * SR); t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * 520 * t) * 0.8 + np.sin(2 * np.pi * 830 * t) * 0.4) * np.exp(-t / 0.035)
    y += np.sin(2 * np.pi * 240 * t) * np.exp(-t / 0.06) * 0.6
    y *= np.minimum(1, t / 0.0015)
    return norm(lowpass(y, 3000))

def flip_tick():
    n = int(0.025 * SR)
    x = rng.randn(n) * env_ad(n, 0.0008, 0.004)
    return norm(lowpass(x, 3000) - lowpass(x, 900))

def ding_ding():
    a = bell(1568, 0.6, decay=0.25); b = bell(2093, 0.8, decay=0.3)
    out = np.zeros(int(1.0 * SR)); out[:len(a)] += a; o = int(0.13 * SR); out[o:o + len(b)] += b[:len(out) - o]
    return norm(lowpass(out, 7000))

def low_fall(dur=0.55):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 300 * (150 / 300) ** (t / dur) * (1 + 0.012 * np.sin(2 * np.pi * 6 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = (np.sin(ph) + 0.25 * np.sin(2 * ph)) * env_ad(n, 0.02, 0.3)
    return norm(lowpass(y, 1800))

def two_note():
    a = bell(784, 0.7, ((1, 1.0), (2, 0.3), (3, 0.1)), 0.3); b = bell(1175, 0.9, ((1, 1.0), (2, 0.3), (3, 0.1)), 0.38)
    out = np.zeros(int(1.2 * SR)); out[:len(a)] += a; o = int(0.16 * SR); out[o:o + len(b)] += b[:len(out) - o]
    return norm(lowpass(out, 6500))

def events():
    from lib import fruit_imgs
    SC.A.setdefault("fruits", fruit_imgs())
    S = SC_START
    ev = []
    def add(t, snd, db): ev.append((t, snd, db))
    add(0.0, whoosh(0.24), -18); add(0.26, tuk(), -17)
    add(S[2], rewind(0.3), -19)
    add(S[3] + 0.01, pop(), -18); add(S[3] + 0.28, ting(), -22)
    add(S[4] + 0.08, swish(0.5), -21)
    wq = [w for w in scene_words(4) if w["text"].startswith("oʻqigan")][0]
    add((word_frame(wq) + 4) / FPS, tuk(190, 90, 0.14), -18)
    add(S[5] + 0.03, door_bell(), -19)
    lit = [s for s in SLOTS if s["board"] == 1 and -120 < s["x"] < 380]
    for j in range(len(lit)):
        add(S[6] + 0.04 + j * (0.62 / max(1, len(lit) - 1)), tick(1700 + 120 * j), -26)
    add(S[7] + 0.16, flutter(0.3), -20); add(S[7] + 0.92, soft_ting(), -21)
    add(S[8], whoosh(0.2), -18); add(S[8] + 0.2, tuk(), -17)
    add(S[9], drum_roll(SC_END_FRAME[9] / FPS - S[9] - 0.05), -19)
    add(S[10] + 0.02, chime(), -19)
    n = 0
    for f in fruit_rain():
        st = None
        for tt in np.arange(0, 1.4, 1 / FPS):
            st = fruit_state(f, tt)
            if st and st[3]: add(S[10] + f["t0"] + st[3][0], boing(), -23); n += 1; break
        if n >= 6: break
    add(S[11] + 0.33, bonk(), -18)
    nfl = len(FLIP_ORDER)
    for j in range(nfl):
        add(S[12] + 0.12 + j * (1.05 / nfl) + 0.1, flip_tick(), -27)
    add(S[13], flutter(0.4), -21); add(S[13] + 0.45, ding_ding(), -20)
    add(S[14] + 0.05, low_fall(), -20)
    add(S[15] + 0.6, two_note(), -20)
    add(S[16] + 0.01, pop(), -18)
    add(S[17] + 0.08, whoosh(0.3), -19)
    add(S[18] + 0.25, pop(), -18)
    return ev

def read_wav(path):
    w = wave.open(path); n = w.getnframes(); ch = w.getnchannels()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32768
    if ch > 1: x = x.reshape(-1, ch).mean(1)
    return x, w.getframerate()

def main(voice_wav, out_wav, sfx_only_wav=None):
    v, sr = read_wav(voice_wav); assert sr == SR
    total = int(round(N_FRAMES / FPS * SR))
    voice = np.zeros(total); voice[:min(total, len(v))] = v[:total]
    vpk = np.abs(voice).max()
    sfx = np.zeros(total)
    for t, snd, db in events():
        o = int(round(t * SR))
        if o >= total: continue
        g = vpk * 10 ** (db / 20)
        seg = snd[:total - o] * g
        sfx[o:o + len(seg)] += seg
    # ducking: sidechain from voice envelope
    a = np.abs(voice)
    env = np.zeros(total); s = 0.0
    att = math.exp(-1 / (0.01 * SR)); rel = math.exp(-1 / (0.2 * SR))
    for i in range(0, total, 48):
        x = a[i:i + 48].max()
        s = (att if x > s else rel) * s + (1 - (att if x > s else rel)) * x
        env[i:i + 48] = s
    duck = 1 - 0.45 * np.clip(env / 0.08, 0, 1)
    mix = voice + sfx * duck
    pk = np.abs(mix).max()
    if pk > 0.97: mix = np.tanh(mix / 0.97 * 1.0) * 0.97 / np.tanh(1.0) if pk > 1.2 else mix * 0.97 / pk
    st = np.stack([mix, mix], 1)
    w = wave.open(out_wav, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()
    if sfx_only_wav:
        w = wave.open(sfx_only_wav, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(sfx * duck, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()
    rms = lambda x: 20 * math.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
    print(f"voice rms {rms(voice):.1f} dB, sfx rms {rms(sfx * duck):.1f} dB, voice peak {20*math.log10(vpk):.1f}, sfx peak {20*math.log10(np.abs(sfx*duck).max()):.1f}, events {len(events())}, dur {total/SR:.3f}s")

if __name__ == "__main__":
    main(*sys.argv[1:])
