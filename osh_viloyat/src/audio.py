# Synthesised SFX + doira/dutor music loop, ducked under the voice-over; writes a 48 kHz stereo mix (pre-loudnorm).
import sys, math, wave, json
import numpy as np
from scipy.signal import lfilter, butter, sosfilt
from timeline import S, DUR, T, N_FRAMES, AUDIO_DUR, IDS
import scenes as SCN

SR = 48000
SFX_TRIM = 10.0     # dB: puts sfx peaks ~18-20 dB under voice peaks
MUSIC_TRIM = 5.0    # dB: compensates ducking so integrated music sits ~26-28 LU under the voice (below the sfx)
rng = np.random.RandomState(7)


# ---------------------------------------------------------------- dsp helpers
def lp(x, fc, order=2):
    sos = butter(order, min(fc, SR * 0.45), "low", fs=SR, output="sos"); return sosfilt(sos, x)
def hp(x, fc, order=2):
    sos = butter(order, fc, "high", fs=SR, output="sos"); return sosfilt(sos, x)
def bp(x, f0, f1, order=2):
    sos = butter(order, [f0, f1], "band", fs=SR, output="sos"); return sosfilt(sos, x)
def env(n, a=0.004, d=0.15):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)
def norm(x, peak=1.0):
    return x / (np.abs(x).max() + 1e-9) * peak
def sweep(f0, f1, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)
def fades(x, fi=0.005, fo=0.02):
    n = len(x); a, b = int(fi * SR), int(fo * SR)
    if a: x[:a] *= np.linspace(0, 1, a)
    if b: x[-b:] *= np.linspace(1, 0, b)
    return x


# ---------------------------------------------------------------- sfx (all soft, low-passed, no piercing highs)
def soft_thud(dur=0.22):
    n = int(dur * SR)
    y = sweep(120, 52, dur) * env(n, 0.003, 0.07)
    y += lp(rng.randn(n), 600) * env(n, 0.001, 0.012) * 0.25
    return norm(lp(y, 900))

def accent():
    """soft hook accent: low swell + warm plucked fifth"""
    n = int(0.9 * SR); t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * 73.4 * t) + 0.5 * np.sin(2 * np.pi * 110 * t)) * env(n, 0.008, 0.35)
    y += 0.35 * np.sin(2 * np.pi * 293.7 * t) * env(n, 0.004, 0.25)
    y += lp(rng.randn(n), 2500) * env(n, 0.002, 0.05) * 0.15
    return norm(lp(y, 2500))

def stamp_tap():
    n = int(0.25 * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * 180 * t) * env(n, 0.001, 0.05) + lp(rng.randn(n), 1800) * env(n, 0.0008, 0.018) * 0.6
    return norm(lp(y, 2200))

def wood_knock(f=520):
    n = int(0.18 * SR); t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * f * t) * 0.8 + np.sin(2 * np.pi * f * 2.3 * t) * 0.25) * env(n, 0.0008, 0.035)
    y += bp(rng.randn(n), 600, 2400) * env(n, 0.0005, 0.006) * 0.4
    return norm(lp(y, 3200))

def sizzle(dur, seed=0):
    r = np.random.RandomState(seed)
    n = int(dur * SR)
    x = bp(r.randn(n), 1800, 5200, 2) * 0.35
    # crackles
    for _ in range(int(dur * 26)):
        o = r.randint(0, n - 600)
        c = bp(r.randn(500), 1500, 4000) * env(500, 0.0003, 0.002) * r.uniform(0.4, 1.0)
        x[o:o + 500] += c
    x *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.7 * np.arange(n) / SR)
    return fades(norm(lp(x, 6000)), 0.15, 0.25)

def pop():
    n = int(0.12 * SR)
    y = sweep(520, 210, 0.12) * env(n, 0.002, 0.03)
    return norm(lp(y, 2400))

def whoosh(dur=0.3, f0=500, f1=2200):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.randn(n)
    shape = np.sin(np.pi * t / dur) ** 2
    y = bp(x, f0, f1) * shape
    return norm(lp(y, 3000))

def creak(dur=1.2):
    n = int(dur * SR); t = np.arange(n) / SR
    # slow friction pulses through a woody resonance
    rate = 18 + 10 * np.sin(2 * np.pi * 0.8 * t)
    ph = np.cumsum(rate) / SR
    pulses = (np.sin(2 * np.pi * ph) > 0.92).astype(float)
    y = bp(pulses + rng.randn(n) * 0.02, 300, 1200)
    y *= np.exp(-t / 0.9)
    return norm(lp(y, 1600))

def wobble(dur=1.6):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 160 + 25 * np.sin(2 * np.pi * 2.2 * t) * np.exp(-t / 0.6)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.02, 0.5)
    return norm(lp(y, 900))

def warm_chime():
    n = int(1.8 * SR); t = np.arange(n) / SR
    y = np.zeros(n)
    for f, a, d in ((587.3, 1.0, 0.45), (880, 0.5, 0.35), (1174.7, 0.22, 0.25), (293.7, 0.4, 0.5)):
        y += a * np.sin(2 * np.pi * f * t) * env(n, 0.006, d)
    return norm(lp(y, 3000))

def womp():
    out = np.zeros(int(0.9 * SR))
    for k, (f0, f1) in enumerate(((220, 205), (174, 140))):
        n = int(0.38 * SR) if k == 0 else int(0.5 * SR)
        y = sweep(f0, f1, n / SR)
        y = (y + 0.3 * np.sign(y) * np.abs(y) ** 3) * env(n, 0.01, 0.2 if k == 0 else 0.3)
        o = int(k * 0.3 * SR); out[o:o + n] += y
    return norm(lp(out, 1200))

def key_click():
    n = int(0.03 * SR)
    y = bp(rng.randn(n), 1200, 3800) * env(n, 0.0004, 0.004)
    return norm(lp(y, 4500))

def bubble_pop():
    n = int(0.14 * SR)
    y = sweep(380, 900, 0.14) * env(n, 0.003, 0.04)
    return norm(lp(y, 2600))


def events():
    ev = []
    def add(t, snd, db): ev.append((t, snd, db))
    # 1 hook
    add(0.0, accent(), -24)
    for k in range(SCN.N_TOWER):
        add(0.15 + 0.4 * k, soft_thud(), -24)
    # 2 stamp
    add(T(2, "yunesko"), stamp_tap(), -18)
    # 3 two knocks
    add(T(3, "xolis"), wood_knock(520), -19); add(T(3, "hakam"), wood_knock(470), -19)
    # 4 sizzle while stirring
    add(S[4] + 0.2, sizzle(DUR[4] - 0.2, 1), -29)
    # 5 three pops when the layers land
    for wd in ("guruch", "sabzi", "go"):
        add(T(5, wd) + 0.13, pop(), -19)
    # 6 oil sizzle
    add(S[6] + 0.05, sizzle(DUR[6] - 0.05, 2), -25)
    # 7 whoosh per card
    times, step = SCN.card_times()
    for tt in times:
        add(S[7] + tt, whoosh(0.16, 700, 2600), -28)
    # 8 creak + wobble of the scale
    add(S[8] + 0.05, creak(1.4), -26); add(S[8] + 0.05, wobble(1.8), -28)
    # 9 warm chime on «onamning»
    add(T(9, "onamning"), warm_chime(), -24)
    # 10 womp
    add(S[10] + 0.15, womp(), -20)
    # 11 swoosh as the badge flies
    add(S[11] + 0.3, whoosh(0.45, 300, 2000), -23)
    # 12 keyboard clicks
    for c in SCN.click_times(DUR[12]):
        add(S[12] + c, key_click(), -27)
    # 13 bubble pops
    for (_, wd) in SCN.BUBBLES:
        add(T(13, wd), bubble_pop(), -20)
    # 14 whoosh on the logo + on the falling lagan (no landing thud)
    add(S[14] + 0.15, whoosh(0.35, 400, 2400), -22)
    add(S[14] + DUR[14] - 0.4, whoosh(0.4, 300, 1600), -23)
    return ev


# ---------------------------------------------------------------- music: doira frame drum + plucked dutor
BARS = 18

def pluck(f, dur, bright=0.5, decay=0.995):
    n = int(dur * SR)
    N = max(2, int(round(SR / f)))
    exc = np.zeros(n)
    burst = lp(rng.randn(N), 1200 + 3000 * bright)
    exc[:N] = burst * np.hanning(N)
    a = np.zeros(N + 2); a[0] = 1; a[N] = -decay / 2; a[N + 1] = -decay / 2
    y = lfilter([1.0], a, exc)
    y *= np.minimum(1, (n - np.arange(n)) / (0.03 * SR))
    return lp(y, 2600 + 1500 * bright)

def dum():
    n = int(0.35 * SR)
    y = sweep(95, 58, 0.35) * env(n, 0.002, 0.11) + lp(rng.randn(n), 400) * env(n, 0.001, 0.01) * 0.3
    return lp(y, 700)

def tak():
    n = int(0.12 * SR); t = np.arange(n) / SR
    y = bp(rng.randn(n), 900, 3200) * env(n, 0.0006, 0.02) + 0.4 * np.sin(2 * np.pi * 420 * t) * env(n, 0.001, 0.03)
    return lp(y, 4200)

def zil():
    """soft jingle of the doira rings (kept low-passed)"""
    n = int(0.16 * SR); t = np.arange(n) / SR
    y = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in (3100, 3730, 4410, 5230)) * env(n, 0.002, 0.045)
    return lp(y, 5200) * 0.35


def music(total_n, s8, s9, s10):
    bar = total_n / SR / BARS
    e8 = bar / 8
    out_d = np.zeros(total_n + SR); out_m = np.zeros(total_n + SR)
    D, Tk, Z = dum(), tak(), zil()
    def put(buf, t, snd, g):
        o = int(round(t * SR))
        if o >= len(buf): return
        seg = snd[:len(buf) - o] * g; buf[o:o + len(seg)] += seg
    # doira pattern per bar (eighths): D . t t D . t z(+t)
    pat = [("D", 1.0), None, ("T", 0.6), ("T", 0.45), ("D", 0.85), None, ("T", 0.6), ("TZ", 0.5)]
    for b in range(BARS):
        for j, p in enumerate(pat):
            if not p: continue
            t = b * bar + j * e8
            kind, g = p
            if "D" in kind: put(out_d, t, D, g)
            if "T" in kind: put(out_d, t, Tk, g * 0.55)
            if "Z" in kind or j in (2, 6): put(out_d, t, Z, g * 0.6)
    # dutor: D-minor/phrygian flavoured melody, 2-bar phrases, + drone (D3, A3)
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    D4, E4, F4, G4, A4, Bb4, C5, D5, Eb4 = 62, 64, 65, 67, 69, 70, 72, 74, 63
    phrases = [
        [A4, None, G4, A4, Bb4, A4, G4, F4, G4, None, F4, Eb4, F4, None, D4, None],
        [D4, F4, G4, A4, None, A4, Bb4, A4, G4, F4, E4, F4, D4, None, None, None],
        [A4, C5, Bb4, A4, G4, None, A4, G4, F4, G4, A4, None, G4, F4, E4, None],
        [F4, E4, D4, F4, G4, None, F4, E4, D4, None, E4, F4, D4, None, None, None],
    ]
    for b in range(0, BARS, 2):
        ph = phrases[(b // 2) % len(phrases)]
        for j, m in enumerate(ph):
            if m is None: continue
            t = b * bar + j * e8
            put(out_m, t, pluck(hz(m), 0.9, 0.55), 0.55)
            if j % 4 == 0: put(out_m, t + 0.012, pluck(hz(m + 12), 0.6, 0.3), 0.12)
    for b in range(BARS):
        for j in (0, 4):
            t = b * bar + j * e8
            put(out_m, t, pluck(hz(50), 1.3, 0.25, 0.997), 0.32)
            put(out_m, t + 0.01, pluck(hz(57), 1.2, 0.25, 0.997), 0.22)
    out_d, out_m = out_d[:total_n], out_m[:total_n]
    tt = np.arange(total_n) / SR
    # scene 8: comic pause (music cut 0.5 s)
    g = np.ones(total_n)
    cut = (tt >= s8) & (tt < s8 + 0.5)
    g[cut] = 0.0
    ramp = (tt >= s8 + 0.5) & (tt < s8 + 0.6)
    g[ramp] = (tt[ramp] - s8 - 0.5) / 0.1
    pre = (tt >= s8 - 0.02) & (tt < s8)
    g[pre] = (s8 - tt[pre]) / 0.02
    # scene 9: softer and warmer (drums mostly out, low-passed dutor)
    warm = ((tt >= s9) & (tt < s10)).astype(float)
    wsm = np.convolve(warm, np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")
    m_warm = lp(out_m, 1100)
    melody = out_m * (1 - wsm) + m_warm * wsm * 0.8
    drums = out_d * (1 - 0.8 * wsm)
    return (melody + drums * 0.8) * g


# ---------------------------------------------------------------- mix
def read_wav(path):
    w = wave.open(path); n = w.getnframes(); ch = w.getnchannels()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32768
    if ch > 1: x = x.reshape(-1, ch).mean(1)
    return x, w.getframerate()


def write_wav(path, x, ch=2):
    w = wave.open(path, "wb"); w.setnchannels(ch); w.setsampwidth(2); w.setframerate(SR)
    if ch == 2: x = np.stack([x, x], 1)
    w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()


def db(x): return 20 * math.log10(x + 1e-12)


def main(voice_wav, out_wav, stems_prefix=None):
    v, sr = read_wav(voice_wav); assert sr == SR
    total = len(v)                              # keep the exact voice-over length
    voice = v.copy()
    # speech-active RMS of the voice
    blk = int(0.05 * SR)
    r = np.sqrt(np.convolve(voice ** 2, np.ones(blk) / blk, mode="same"))
    active = r > 10 ** (-40 / 20)
    v_rms = np.sqrt(np.mean(voice[active] ** 2))
    # voice envelope for ducking
    env_v = np.zeros(total); s = 0.0
    att, rel = math.exp(-1 / (0.008 * SR / 48)), math.exp(-1 / (0.25 * SR / 48))
    a = np.abs(voice)
    for i in range(0, total, 48):
        x = a[i:i + 48].max()
        c = att if x > s else rel
        s = c * s + (1 - c) * x
        env_v[i:i + 48] = s
    speech = np.clip(env_v / 0.06, 0, 1)
    # sfx bus
    sfx = np.zeros(total)
    for t, snd, d in events():
        o = int(round(t * SR))
        if o >= total: continue
        seg = snd[:total - o]
        g = v_rms * 10 ** ((d + SFX_TRIM) / 20) / (np.sqrt(np.mean(snd ** 2)) + 1e-9) * 0.5
        sfx[o:o + len(seg)] += seg * g
    sfx *= 1 - 0.5 * speech                     # duck ~6 dB under speech
    # music bus at ~ -26 dB under the voice, ducked further under speech
    mus = music(total, S[8], S[9], S[10])
    m_rms = np.sqrt(np.mean(mus[mus != 0] ** 2))
    mus = mus / m_rms * v_rms * 10 ** ((-26 + MUSIC_TRIM) / 20)
    mus *= 1 - 0.55 * speech
    mix = voice + sfx + mus
    pk = np.abs(mix).max()
    if pk > 0.98: mix *= 0.98 / pk
    write_wav(out_wav, mix)
    if stems_prefix:
        write_wav(stems_prefix + "_voice.wav", voice, 1); write_wav(stems_prefix + "_sfx.wav", sfx, 1); write_wav(stems_prefix + "_music.wav", mus, 1)
    rms = lambda x: db(np.sqrt(np.mean(x ** 2)))
    print(f"voice(active) {db(v_rms):.1f} dBFS | sfx rms {rms(sfx):.1f} | music rms {rms(mus):.1f} | dur {total / SR:.3f}s | events {len(events())}")


if __name__ == "__main__":
    main(*sys.argv[1:])
