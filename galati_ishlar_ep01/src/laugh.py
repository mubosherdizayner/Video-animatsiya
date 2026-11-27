# Synthesized laughter of the four 12-year-old boys (scene 4, F10), made on the user's request.
# Source-filter model: Rosenberg glottal pulses with jitter/shimmer + aspiration noise,
# child vowel formants (cascade resonators), "h" onsets, falling pitch through each bout,
# inhalations at the end, small-room reverb. kulgi.mp3, if attached, is used instead.
import math
import numpy as np
from scipy import signal

SR = 48000

# child (≈12 y) vowel formants (Hz) and bandwidths
VOWELS = {
    "a": ((1000, 1550, 3000, 4200), (110, 140, 220, 300)),
    "e": ((620, 2350, 3300, 4400), (100, 150, 230, 300)),
    "i": ((420, 2900, 3700, 4600), (90, 160, 250, 320)),
    "o": ((660, 1050, 2900, 4100), (110, 130, 220, 300)),
    "ae": ((850, 1900, 3100, 4300), (110, 150, 220, 300)),
}

# the four friends, left to right in F10:
#   Mubosher (hearty "ha-ha"), Sardor (youngest, giggly "hi-hi"), Doniyor (the joker, belly "ho-ha"),
#   Botir (serious, short chuckle)
BOYS = [
    dict(name="Mubosher", pan=-0.55, f0=(330, 255), rate=4.3, n=7, start=0.06, vowels="aaaea", gain=1.0, second=2),
    dict(name="Sardor", pan=-0.18, f0=(455, 360), rate=4.9, n=8, start=0.12, vowels="iieii", gain=0.85, second=3),
    dict(name="Doniyor", pan=0.20, f0=(285, 215), rate=3.9, n=7, start=0.02, vowels="oaaoa", gain=1.1, second=2),
    dict(name="Botir", pan=0.55, f0=(305, 265), rate=4.6, n=4, start=0.38, vowels="eaeae", gain=0.7, second=0),
]

LAUGH_MAX = 2.6          # last call starts by then; the laugh is over before scene 5 (3.0 s window)

def call_schedule(seed=21):
    """per boy: list of calls (time from the laugh start, amplitude, f0, vowel) + inhalations"""
    rng = np.random.default_rng(seed)
    out = []
    for b in BOYS:
        calls, inh = [], []
        t = b["start"]
        def bout(t, n, a0, f_hi, f_lo):
            cs = []
            for k in range(n):
                x = k / max(1, n - 1)
                amp = a0 * (0.55 + 0.45 * min(1, k / 1.5)) * (1 - 0.55 * x ** 1.3) * rng.uniform(0.85, 1.1)
                f0 = (f_hi + (f_lo - f_hi) * x) * rng.uniform(0.96, 1.05)
                v = b["vowels"][int(rng.integers(len(b["vowels"])))]
                cs.append((t, amp, f0, v))
                t += (1 / b["rate"]) * rng.uniform(0.92, 1.1) * (1 + 0.15 * x)   # slows down as breath runs out
            return cs, t
        cs, t = bout(t, b["n"], b["gain"], *b["f0"])
        calls += cs
        inh.append((t + 0.02, 0.55 * b["gain"]))
        t += 0.30
        if b["second"]:
            cs, t = bout(t, b["second"], 0.6 * b["gain"], b["f0"][1] * 1.08, b["f0"][1] * 0.95)
            calls += cs
        calls = [c for c in calls if c[0] <= LAUGH_MAX]
        inh = [i for i in inh if i[0] <= LAUGH_MAX - 0.25]
        out.append(dict(boy=b, calls=calls, inhales=inh))
    return out

def resonator(F, B):
    r = math.exp(-math.pi * B / SR); th = 2 * math.pi * F / SR
    a = [1, -2 * r * math.cos(th), r * r]
    return [sum(a)], a                     # unity gain at DC (Klatt cascade)

def tract(x, vowel, shift=1.0):
    Fs, Bs = VOWELS[vowel]
    y = x
    for F, Bw in zip(Fs, Bs):
        b, a = resonator(F * shift, Bw)
        y = signal.lfilter(b, a, y)
    return y

def glottal(f0_curve, rng, oq=0.62, sk=0.72, jitter=0.012, shimmer=0.08):
    """Rosenberg flow derivative with jitter and shimmer; f0_curve is per-sample Hz"""
    n = len(f0_curve)
    jit = 1 + jitter * signal.lfilter([0.02], [1, -0.98], rng.standard_normal(n)) * 7
    ph = np.cumsum(f0_curve * jit) / SR
    cyc = np.floor(ph); p = ph - cyc
    tp, tn = oq * sk, oq * (1 - sk)
    flow = np.where(p < tp, 0.5 * (1 - np.cos(np.pi * p / tp)),
                    np.where(p < tp + tn, np.cos(np.pi * (p - tp) / (2 * tn)), 0.0))
    sh = 1 + shimmer * rng.standard_normal(int(cyc[-1]) + 2)
    flow = flow * sh[cyc.astype(int)]
    d = np.diff(flow, prepend=0.0)
    return d / (np.abs(d).max() + 1e-9), flow

def one_call(amp, f0, vowel, rng, dur=None):
    dur = dur or rng.uniform(0.11, 0.15)
    h = rng.uniform(0.03, 0.05)                     # breathy "h" onset
    n, nh = int((dur + 0.06) * SR), int(h * SR)
    t = np.arange(n) / SR
    # pitch: quick rise into the vowel then a fall (laugh "ha" contour)
    tv = np.clip((t - h) / dur, 0, 1)
    f = f0 * (1 + 0.06 * np.sin(np.pi * np.clip(tv * 1.6, 0, 1)) - 0.12 * tv)
    src, flow = glottal(f, rng)
    venv = np.clip((t - h * 0.8) / 0.012, 0, 1) * np.exp(-np.clip(t - h, 0, None) * rng.uniform(9, 13))
    venv *= np.clip((dur + h + 0.03 - t) / 0.03, 0, 1)
    asp = rng.standard_normal(n)
    asp = signal.lfilter([1, -0.6], [1], asp)       # brighter breath
    henv = np.exp(-((t - h * 0.6) / (h * 0.6)) ** 2) * 0.9 + 0.12 * venv
    exc = src * venv + asp * (henv * 0.20 + 0.28 * venv * (0.4 + flow))   # pulsed aspiration = breathy laugh
    y = tract(exc, vowel, rng.uniform(0.97, 1.04))
    y = y / (np.abs(y).max() + 1e-9)
    return y * amp

def inhale(amp, rng, dur=0.34):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    y = tract(x, "i", 1.05) * 0.7 + signal.lfilter(*signal.butter(2, [1200, 4200], "band", fs=SR), x) * 0.3
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.4
    # a faint voiced squeak in the middle of the in-breath
    sq = np.sin(2 * np.pi * np.cumsum(np.full(n, 620.0) * (1 + 0.1 * t / dur)) / SR) * np.exp(-((t - dur * 0.55) / (dur * 0.15)) ** 2) * 0.15
    y = y / (np.abs(y).max() + 1e-9) * env + sq
    return y * amp * 0.28

def room_ir(rt=0.38, seed=5):
    rng = np.random.default_rng(seed)
    n = int(rt * SR)
    ir = rng.standard_normal(n) * np.exp(-6.9 * np.arange(n) / n)
    ir = signal.lfilter(*signal.butter(2, 5000, "low", fs=SR), ir)
    for d, g in ((0.007, 0.5), (0.013, 0.35), (0.019, 0.3), (0.027, 0.22)):   # early reflections of a small room
        ir[int(d * SR)] += g * np.abs(ir).max() * 4
    return ir / np.sqrt(np.sum(ir ** 2))

def synth(seed=21):
    """-> (L, R) float arrays, laugh starting at 0"""
    rng = np.random.default_rng(seed + 1)
    sched = call_schedule(seed)
    total = 3.0
    n = int(total * SR)
    L, R = np.zeros(n), np.zeros(n)
    for s in sched:
        b = s["boy"]
        mono = np.zeros(n)
        for t0, amp, f0, v in s["calls"]:
            y = one_call(amp, f0, v, rng)
            i = int(t0 * SR); mono[i:i + len(y)] += y[:n - i]
        for t0, amp in s["inhales"]:
            y = inhale(amp, rng)
            i = int(t0 * SR); mono[i:i + len(y)] += y[:n - i]
        mono *= b["gain"]
        gl, gr = math.cos((b["pan"] + 1) * math.pi / 4), math.sin((b["pan"] + 1) * math.pi / 4)
        d = int(abs(b["pan"]) * 0.0004 * SR)          # tiny inter-channel delay for width
        L += np.roll(mono, d if b["pan"] > 0 else 0) * gl
        R += np.roll(mono, d if b["pan"] < 0 else 0) * gr
    ir = room_ir()
    wet = 0.22
    L = L * (1 - wet) + signal.fftconvolve(L, ir)[:n] * wet
    R = R * (1 - wet) + signal.fftconvolve(R, np.roll(ir, 37))[:n] * wet
    hp = signal.butter(2, 90, "high", fs=SR, output="sos"); lp = signal.butter(4, 9000, "low", fs=SR, output="sos")
    L = signal.sosfilt(lp, signal.sosfilt(hp, L)); R = signal.sosfilt(lp, signal.sosfilt(hp, R))
    m = max(np.abs(L).max(), np.abs(R).max())
    return L / m, R / m

if __name__ == "__main__":
    import sys
    from scipy.io import wavfile
    L, R = synth()
    wavfile.write(sys.argv[1], SR, (np.stack([L, R], 1) * 0.5).astype(np.float32))
    for s in call_schedule():
        print(s["boy"]["name"], [round(c[0], 2) for c in s["calls"]], "inhale", [round(i[0], 2) for i in s["inhales"]])
