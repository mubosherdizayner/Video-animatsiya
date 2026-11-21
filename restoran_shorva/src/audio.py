# Code-synthesized SFX + Karplus-Strong dutor-style music bed, mixed under the voice with ducking.
import sys, os, json, math, subprocess, wave
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenes as SC
from common import BUILD

SR = 48000
rng = np.random.RandomState(11)

def db(x): return 10 ** (x / 20)
def env_exp(n, a=0.004, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)
def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos"); return signal.sosfilt(sos, x)
def lp(x, fc, order=2):
    sos = signal.butter(order, fc, btype="low", fs=SR, output="sos"); return signal.sosfilt(sos, x)
def hp(x, fc, order=2):
    sos = signal.butter(order, fc, btype="high", fs=SR, output="sos"); return signal.sosfilt(sos, x)
def norm(x, peak=1.0): return x / (np.abs(x).max() + 1e-9) * peak
def sweep(f0, f1, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / dur); return np.sin(2 * np.pi * np.cumsum(f) / SR)
def partials(freqs, amps, dur, decays):
    n = int(dur * SR); t = np.arange(n) / SR; out = np.zeros(n)
    for f, a, d in zip(freqs, amps, decays): out += a * np.sin(2 * np.pi * f * t + rng.rand() * 6) * np.exp(-t / d)
    return out * np.minimum(1, t / 0.002)

# ---------------------------------------------------------------- sfx
def thump():
    n = int(0.45 * SR)
    y = sweep(95, 42, 0.45) * env_exp(n, 0.006, 0.12)
    y += lp(rng.randn(n), 300) * env_exp(n, 0.002, 0.03) * 0.5
    return norm(lp(y, 900))
def glass_tick():
    y = partials([2650, 3980, 5310], [1, 0.45, 0.2], 0.5, [0.12, 0.07, 0.05])
    return norm(lp(y, 6000)) * 0.8
def whoosh(dur=0.7, lo=300, hi=2600):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.randn(n)
    y = bp(x, lo, hi) * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2.2
    y2 = bp(x, lo * 0.6, hi * 0.4)
    return norm(y + 0.5 * y2 * np.sin(np.pi * t / dur) ** 3)
def clink(f=3100):
    y = partials([f, f * 1.52, f * 2.31], [1, 0.5, 0.25], 0.4, [0.09, 0.06, 0.04])
    return norm(lp(y, 7000))
def murmur(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(9):
        x = bp(rng.randn(n), 180 + 40 * k, 520 + 60 * k)
        am = 0.5 + 0.5 * np.sin(2 * np.pi * (2.1 + 0.37 * k) * t + k) * np.sin(2 * np.pi * (0.4 + 0.11 * k) * t + 2 * k)
        out += x * np.clip(am, 0, 1) ** 2
    out = lp(out, 900)
    return norm(out * np.minimum(1, t / 0.8) * np.minimum(1, (dur - t) / 0.8))
def step():
    n = int(0.12 * SR)
    y = lp(rng.randn(n), 700) * env_exp(n, 0.002, 0.025) + 0.6 * sweep(120, 60, 0.12) * env_exp(n, 0.002, 0.03)
    return norm(y)
def paper_tear(dur=0.42):
    n = int(dur * SR); t = np.arange(n) / SR
    crack = (rng.rand(n) < 0.012).astype(float) * rng.rand(n)
    crack = np.convolve(crack, np.exp(-np.arange(200) / 30.0), mode="same")
    y = bp(rng.randn(n) * (0.3 + crack * 3), 900, 4200)
    y *= np.minimum(1, t / 0.02) * np.exp(-np.maximum(0, t - 0.25) / 0.08)
    return norm(lp(y, 5000))
def rewind(dur=0.5):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 1400 * (160 / 1400) ** (t / dur) * (1 + 0.08 * np.sin(2 * np.pi * 22 * t))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    nz = bp(rng.randn(n), 600, 3000)
    y = (0.35 * lp(tone, 2500) + 0.65 * nz) * np.sin(np.pi * t / dur) ** 1.2
    return norm(y)
def pop():
    y = sweep(520, 170, 0.08) * env_exp(int(0.08 * SR), 0.002, 0.025); return norm(lp(y, 2500))
def door_bell():
    a = partials([1760, 1760 * 2.71, 1760 * 4.1], [1, 0.3, 0.12], 0.9, [0.35, 0.15, 0.08])
    b = partials([2093, 2093 * 2.71], [0.8, 0.25], 0.9, [0.3, 0.12])
    out = np.zeros(int(1.1 * SR)); out[:len(a)] += a; o = int(0.13 * SR); out[o:o + len(b)] += b[:len(out) - o]
    t = np.arange(len(out)) / SR
    return norm(lp(out * (1 + 0.15 * np.sin(2 * np.pi * 9 * t)), 6000))
def chime():
    out = np.zeros(int(1.2 * SR))
    for k, f in enumerate((1318.5, 1568.0, 1975.5)):
        b = partials([f, f * 2.0], [1, 0.18], 1.0, [0.45, 0.2]) * (0.85 ** k)
        o = int(k * 0.07 * SR); out[o:o + len(b)] += b[:len(out) - o]
    return norm(lp(out, 6500))
def creak(dur=0.65):
    n = int(dur * SR); t = np.arange(n) / SR
    rate = 38 + 28 * np.sin(np.pi * t / dur) + 6 * np.sin(2 * np.pi * 3 * t)
    ph = np.cumsum(rate) / SR
    pulses = (np.diff(np.floor(ph), prepend=0) > 0).astype(float)
    y = np.convolve(pulses, np.exp(-np.arange(300) / 40.0) * np.sin(np.arange(300) * 2 * np.pi * 900 / SR), mode="same")
    y = bp(y, 350, 1600) * np.sin(np.pi * t / dur) ** 0.8
    return norm(y)
def hiss(dur=1.1):
    n = int(dur * SR); t = np.arange(n) / SR
    y = bp(rng.randn(n), 2500, 7500) * np.sin(np.pi * t / dur) ** 1.5
    return norm(y)
def lid_clink():
    a = clink(2300); b = clink(2650)
    out = np.zeros(int(0.6 * SR)); out[:len(a)] += a; o = int(0.11 * SR); out[o:o + len(b)] += 0.7 * b[:len(out) - o]
    return norm(out)
def ding():
    return norm(lp(partials([1318.5, 2637, 3955], [1, 0.22, 0.08], 1.0, [0.4, 0.18, 0.08]), 6000))

def build_sfx(n):
    T = SC.T
    ev = []   # (time, sound, gain_db)
    ev += [(0.0, thump(), -2), (SC.T_FREEZE - 0.01, glass_tick(), -9)]
    ev += [(T[2] - 0.05, whoosh(0.95, 250, 2200), -6)]
    ev += [(T[4] + 1.0, clink(3300), -8)]
    ev += [(T[5] + 0.1, murmur(SC.dur(5) + 0.4), -15)]
    for j in range(3):
        for s in range(6):
            tt = T[6] + 0.28 * j + 0.12 + s * 0.3
            if tt < T[7] - 0.05: ev.append((tt, step(), -13 - 2 * j))
    ev += [(T[7] + 0.08, paper_tear(), -5)]
    ev += [(T[8] + 0.22, rewind(), -7)]
    for lt in SC.LIGHT_TIMES: ev.append((T[9] + lt, pop(), -9))
    ev += [(T[11] + 0.6, door_bell(), -10)]
    ev += [(T[12] + 1.2, clink(2900), -8)]
    ev += [(T[13] + 0.08, whoosh(0.8, 400, 3000), -8), (T[13] + 1.0, chime(), -9)]
    ev += [(T[14] + 0.1, hiss(1.2), -16), (T[14] + 0.95, creak(), -8)]
    ev += [(T[15] + 0.08, lid_clink(), -8)]
    ev += [(T[16] + 0.06, ding(), -9)]
    ev += [(T[17], thump(), -2)]
    out = np.zeros(n)
    for t0, snd, g in ev:
        o = int(round(t0 * SR))
        if o >= n: continue
        m = min(len(snd), n - o)
        out[o:o + m] += snd[:m] * db(g)
    return out, ev

# ---------------------------------------------------------------- music (Karplus-Strong dutor + pad)
A3 = 220.0
def note_hz(semi): return A3 * 2 ** (semi / 12)
PENTA = [0, 3, 5, 7, 10]          # A minor pentatonic

def ks_pluck(f, dur, bright=0.55, seed=0):
    r = np.random.RandomState(seed)
    n = int(dur * SR); N = int(SR / f)
    buf = r.uniform(-1, 1, N)
    buf = lp(np.concatenate([buf, buf]), 2000 + 4000 * bright)[N:]
    out = np.zeros(n); idx = 0
    decay = 0.996
    for i in range(n):
        v = buf[idx]; out[i] = v
        nxt = buf[(idx + 1) % N]
        buf[idx] = decay * (0.5 * (v + nxt)); idx = (idx + 1) % N
    out *= np.minimum(1, np.arange(n) / (0.002 * SR))
    return out

def dutor(f, dur, seed):
    a = ks_pluck(f, dur, 0.55, seed); b = ks_pluck(f * 1.004, dur, 0.45, seed + 1)
    body = bp(a + 0.8 * b, 150, 3200)
    return body + 0.25 * lp(a, 600)

def pad(freqs, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.12):
            ph = 2 * np.pi * f * (1 + det / 100) * t
            out += np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)
    out = lp(out, 1100)
    att = np.minimum(1, t / 0.9); rel = np.minimum(1, (dur - t) / 0.9)
    return out * att * rel

def build_music(n):
    bpm = 80; beat = 60 / bpm; eighth = beat / 2
    out = np.zeros(n + SR * 3)
    chords = [(0, [0, 7, 12, 15]), (-5, [-5, 2, 7, 10]), (-7, [-7, 0, 5, 8]), (-2, [-2, 5, 10, 14])]
    patt = [0, 2, 4, 2, 3, 4, 2, 1]
    bar = 4 * beat
    nb = int(np.ceil(n / SR / bar)) + 1
    cache = {}
    for b in range(nb):
        root, ch = chords[(b // 2) % len(chords)]
        t0 = b * bar
        o = int(t0 * SR)
        p = pad([note_hz(s - 12) for s in ch[:3]], bar * 1.02)
        out[o:o + len(p)] += p[:len(out) - o] * 0.10
        scale = [root + s for s in PENTA] + [root + 12 + s for s in PENTA]
        for k in range(8):
            if (b + k) % 7 == 6: continue
            semi = scale[(patt[k] + (b % 2) * 2) % len(scale)]
            f = note_hz(semi)
            key = round(f, 2)
            if key not in cache: cache[key] = dutor(f, 1.6, int(f))
            pl = cache[key] * (0.9 if k % 2 == 0 else 0.65)
            oo = int((t0 + k * eighth) * SR)
            out[oo:oo + len(pl)] += pl[:len(out) - oo]
        bassf = note_hz(root - 24)
        bkey = ("b", round(bassf, 2))
        if bkey not in cache: cache[bkey] = lp(ks_pluck(bassf, 2.5, 0.2, 7), 400)
        out[o:o + len(cache[bkey])] += cache[bkey][:len(out) - o] * 0.9
    out = out[:n]
    t = np.arange(n) / SR
    out *= np.minimum(1, t / 0.2)
    return out

# ---------------------------------------------------------------- mix
def voice_env(v):
    e = np.abs(v)
    e = lp(e, 12)
    e = e / (np.percentile(e, 99) + 1e-9)
    act = np.clip((e - 0.04) / 0.12, 0, 1)
    # attack fast, release ~250 ms
    a_att, a_rel = math.exp(-1 / (0.02 * SR)), math.exp(-1 / (0.25 * SR))
    out = np.zeros_like(act); s = 0.0
    for i in range(0, len(act), 48):
        x = act[i:i + 48].max()
        s = (a_att if x > s else a_rel) ** 48 * (s - x) + x
        out[i:i + 48] = s
    return out

def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)

def main():
    raw = os.path.join(BUILD, "voice_raw.mp3")
    v48 = os.path.join(BUILD, "voice48.f32")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-ac", "1", "-ar", str(SR), "-f", "f32le", v48], check=True)
    v = np.fromfile(v48, dtype=np.float32).astype(np.float64)
    n = len(v)
    # voice: speech-active RMS to -17 dBFS
    act = voice_env(v)
    sp = v[act > 0.5]
    v *= db(-17 - rms_db(sp))
    sfx, ev = build_sfx(n)
    mus = build_music(n)
    # levels: sfx peaks ~ -18 dB below voice peak, music RMS ~ -28 dBFS (-5 dB more under speech)
    vpk = np.abs(v).max()
    sfx *= vpk * db(-18) / (np.abs(sfx).max() + 1e-9)
    mus *= db(-28 - rms_db(mus))
    duck_s = db(-6) ** act
    duck_m = db(-5) ** act
    sfx *= duck_s; mus *= duck_m
    L = v + sfx + mus * 0.95
    R = v + sfx + mus * 1.05
    st = np.stack([L, R], 1)
    pk = np.abs(st).max()
    if pk > db(-1.0): st *= db(-1.0) / pk
    out = os.path.join(BUILD, "mix.wav")
    with wave.open(out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype("<i2").tobytes())
    # stems for QA
    np.save(os.path.join(BUILD, "stems.npy"), np.stack([v, sfx, mus]).astype(np.float32))
    print("voice speech rms", round(rms_db(sp * db(-17 - rms_db(sp))), 1), "dBFS; sfx peak", round(20 * np.log10(np.abs(sfx).max()), 1),
          "; music rms", round(rms_db(mus), 1), "; events", len(ev), "; dur", n / SR)

if __name__ == "__main__":
    main()
