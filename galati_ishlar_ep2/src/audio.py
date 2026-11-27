"""Audio for ep.2: voice clips + ambience beds + synthesized sfx + dark ambient music, all in numpy.
Usage: audio.py vo.wav timing.json outdir"""
import json, sys, os, math
import numpy as np, scipy.io.wavfile as wf, scipy.signal as ss

SR = 48000
RNG = np.random.default_rng(27)


def db(x): return 10 ** (x / 20)
def n_(t): return int(round(t * SR))
def tt(n): return np.arange(n) / SR


def white(n, seed=None):
    r = np.random.default_rng(seed) if seed is not None else RNG
    return r.standard_normal(n).astype(np.float64)


def pink(n, seed=None):
    x = np.fft.rfft(white(n, seed)); f = np.fft.rfftfreq(n, 1 / SR); f[0] = f[1]
    y = np.fft.irfft(x / np.sqrt(f), n); return y / (np.std(y) + 1e-12)


def brown(n, seed=None):
    x = np.fft.rfft(white(n, seed)); f = np.fft.rfftfreq(n, 1 / SR); f[0] = f[1]
    y = np.fft.irfft(x / f, n); y = hp(y, 20); return y / (np.std(y) + 1e-12)


def _sos(kind, f, order=2):
    return ss.butter(order, f, btype=kind, fs=SR, output="sos")
def lp(x, f, o=2): return ss.sosfilt(_sos("lowpass", f, o), x)
def hp(x, f, o=2): return ss.sosfilt(_sos("highpass", f, o), x)
def bp(x, f1, f2, o=2): return ss.sosfilt(_sos("bandpass", [f1, f2], o), x)


def reson(x, f, q):
    b, a = ss.iirpeak(f, q, fs=SR); return ss.lfilter(b, a, x)


def smooth_noise(n, rate_hz, seed=None):
    """slow random control signal in ~[-1, 1]"""
    k = max(4, int(n / SR * rate_hz) + 4)
    r = np.random.default_rng(seed)
    pts = r.uniform(-1, 1, k)
    x = np.linspace(0, k - 3, n)
    i = np.floor(x).astype(int); f = x - i; f = f * f * (3 - 2 * f)
    return pts[i] * (1 - f) + pts[i + 1] * f


def env_exp(n, tau): return np.exp(-tt(n) / tau)


def addp(*sigs):
    """sum signals of different lengths (zero-padded)"""
    out = np.zeros(max(len(x) for x in sigs))
    for x in sigs: out[:len(x)] += x
    return out


def norm_peak(x, peak_db):
    m = np.max(np.abs(x)) + 1e-12; return x / m * db(peak_db)


def norm_rms(x, rms_db):
    r = np.sqrt(np.mean(x ** 2)) + 1e-12; return x / r * db(rms_db)


# ------------------------------------------------------------------ sfx library (mono, short)
def thump(f=70, dur=0.35, tau=0.09, click=0.25, seed=None, fall=1.4):
    n = n_(dur); t = tt(n)
    fr = f * (1 + (fall - 1) * np.exp(-t / 0.03))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    body = np.sin(ph) * np.exp(-t / tau)
    nz = lp(white(n, seed), 900) * np.exp(-t / 0.012) * click
    return body + nz


def swell(dur=3.2):
    n = n_(dur); t = tt(n)
    e = np.where(t < 0.9, 0.45 + 0.55 * np.sin(np.pi / 2 * t / 0.9), np.exp(-(t - 0.9) / 0.7))
    x = 0.6 * np.sin(2 * np.pi * 49 * t) + 0.35 * np.sin(2 * np.pi * 73.5 * t + 1) + 0.5 * lp(white(n, 1), 160, 4)
    return x * e


def leaf_step(seed=0):
    n = n_(0.32); t = tt(n); r = np.random.default_rng(seed)
    imp = np.zeros(n)
    k = r.integers(0, n_(0.16), 60) + r.integers(0, n_(0.04), 60)
    imp[np.clip(k, 0, n - 1)] = r.uniform(-1, 1, 60)
    crunch = bp(imp, 500, 2600) * 3 + 0.4 * bp(white(n, seed), 300, 1800) * np.exp(-t / 0.06)
    squish = lp(white(n, seed + 9), 500) * np.exp(-t / 0.05) * 0.8
    return addp(lp((crunch + squish) * np.exp(-t / 0.11), 3200), 0.5 * thump(85, 0.32, 0.05, 0, seed))


def wood_step(seed=0, heavy=False):
    f = 72 if heavy else 105
    x = thump(f, 0.4 if heavy else 0.25, 0.08 if heavy else 0.045, 0.35, seed)
    x = x + 0.35 * reson(white(len(x), seed + 3) * np.exp(-tt(len(x)) / 0.02), 180 if heavy else 260, 6)
    x = x + 0.25 * reson(white(len(x), seed + 4) * np.exp(-tt(len(x)) / 0.015), 420, 5)
    return lp(x, 1800)


def creak(dur=0.7, f0=520, low=False, seed=0):
    n = n_(dur); t = tt(n); r = np.random.default_rng(seed)
    rate = (22 if low else 38) + (10 if low else 18) * np.sin(np.pi * t / dur) + 4 * smooth_noise(n, 25, seed)
    ph = np.cumsum(rate) / SR
    imp = np.diff(np.floor(ph), prepend=0) * r.uniform(0.6, 1.0, n)
    res = [f0 * 0.5, f0, f0 * 1.63] if not low else [f0 * 0.45, f0 * 0.8, f0 * 1.3]
    y = sum(reson(imp, f, 18) / (k + 1) for k, f in enumerate(res))
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.7
    return lp(y * e, 2200)


def clock_tick(tock=False, seed=0):
    n = n_(0.08); t = tt(n)
    x = reson(white(n, seed) * np.exp(-t / 0.003), 1150 if not tock else 900, 9) * np.exp(-t / 0.02)
    return lp(addp(x, 0.5 * thump(220, 0.08, 0.012, 0, seed)), 3000)


def clink(parts, tau=0.18, seed=0, gain=1.0):
    n = n_(tau * 4); t = tt(n); r = np.random.default_rng(seed)
    x = sum(np.sin(2 * np.pi * f * t + r.uniform(0, 6)) * np.exp(-t / (tau / (1 + k * 0.6))) / (k + 1)
            for k, f in enumerate(parts))
    x += 0.3 * bp(white(n, seed), 1500, 4000) * np.exp(-t / 0.002)
    return lp(x, 4200) * gain


def spoon_clinks():
    a = clink([1320, 2870, 4100], 0.14, 1); b = clink([1290, 2810, 4060], 0.12, 2) * 0.7
    out = np.zeros(len(a) + n_(0.16)); out[:len(a)] += a; out[n_(0.16):n_(0.16) + len(b)] += b; return out


def rustle(dur=0.5, seed=0):
    n = n_(dur); t = tt(n)
    g = (smooth_noise(n, 60, seed) > 0.1) * 1.0
    g = lp(g, 120)
    x = bp(white(n, seed), 500, 2600) * (0.3 + g) * np.sin(np.pi * t / dur) ** 0.8
    return lp(x, 3000)


def sting():
    n = n_(2.6); t = tt(n)
    x = 0
    for f in (55.0, 58.27, 82.41, 87.31):
        for k in range(1, 7):
            x = x + np.sin(2 * np.pi * f * k * t * (1 + 0.0015 * (k % 2))) / k
    e = np.minimum(t / 0.05, 1) * np.exp(-t / 0.9)
    return lp(x * e, 380, 4)


def lagan_set():
    knock = 0.8 * thump(150, 0.25, 0.04, 0.5, 4) + 0.4 * reson(white(n_(0.25), 5) * np.exp(-tt(n_(0.25)) / 0.01), 420, 8)
    ring = clink([980, 1620, 2450], 0.22, 6, 0.35)
    out = np.zeros(max(len(knock), len(ring))); out[:len(knock)] += knock; out[:len(ring)] += ring; return out


def dial_clicks(dur=0.45, n_clicks=6):
    n = n_(dur + 0.05); out = np.zeros(n)
    for k in range(n_clicks):
        c = reson(white(n_(0.03), 20 + k) * np.exp(-tt(n_(0.03)) / 0.0025), 1700, 7) + 0.6 * reson(
            white(n_(0.03), 40 + k) * np.exp(-tt(n_(0.03)) / 0.003), 650, 5)
        p = n_(k * dur / n_clicks); out[p:p + len(c)] += c * (0.85 + 0.15 * (k % 2))
    whirr = lp(np.sign(np.sin(2 * np.pi * 14 * tt(n))) * 0.1, 400) * np.sin(np.pi * tt(n) / (dur + 0.05))
    return lp(out + whirr, 3500)


def engine(dur, seed=0):
    n = n_(dur); t = tt(n)
    f = 24 + 1.2 * smooth_noise(n, 2, seed)
    ph = 2 * np.pi * np.cumsum(f) / SR
    pulses = np.maximum(np.sin(ph), 0) ** 6
    x = lp(pulses - pulses.mean(), 160, 4) + 0.25 * lp(brown(n, seed), 90)
    return x


def gravel(dur=0.7, density=900, seed=0, decay=True):
    n = n_(dur); t = tt(n); r = np.random.default_rng(seed)
    cnt = int(density * dur); k = r.integers(0, n, cnt)
    imp = np.zeros(n); imp[k] = r.uniform(-1, 1, cnt) * (np.exp(-t[k] / (dur * 0.45)) if decay else 1)
    x = bp(imp, 450, 2600) * 2.0 + 0.4 * lp(white(n, seed + 1), 300) * (np.exp(-t / (dur * 0.4)) if decay else 1)
    return lp(x, 3000) * np.minimum(t / 0.01, 1)


def car_door(seed=0):
    x = addp(thump(62, 0.5, 0.11, 0.3, seed), 0.45 * thump(140, 0.3, 0.05, 0, seed + 1))
    latch = reson(white(n_(0.04), seed + 2) * np.exp(-tt(n_(0.04)) / 0.004), 900, 6) * 0.5
    x[:len(latch)] += latch; return lp(x, 2000)


def gravel_step(seed=0):
    return addp(gravel(0.18, 1400, seed), 0.5 * thump(90, 0.18, 0.04, 0, seed))


def boom():
    n = n_(3.0); t = tt(n)
    f = 34 + 30 * np.exp(-t / 0.12)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.9)
    x += 0.7 * lp(white(n, 77), 110, 4) * np.exp(-t / 0.5)
    return lp(x, 160, 4) * np.minimum(t / 0.004, 1)


def heartbeat(n_beats=3, period=0.88):
    out = np.zeros(n_(n_beats * period + 0.5))
    for k in range(n_beats):
        a = thump(55, 0.25, 0.06, 0.05, k); b = thump(47, 0.28, 0.07, 0.05, k + 10) * 0.75
        p = n_(k * period); out[p:p + len(a)] += a * (0.8 + 0.2 * k / max(1, n_beats - 1))
        q = p + n_(0.27); out[q:q + len(b)] += b * (0.8 + 0.2 * k / max(1, n_beats - 1))
    return lp(out, 150)


def rumble_rise(dur):
    n = n_(dur); t = tt(n)
    return lp(brown(n, 31), 90, 4) * (t / dur) ** 1.5


def whoosh(dur=0.65, seed=5):
    n = n_(dur); t = tt(n); x = white(n, seed); y = np.zeros(n)
    fc = 250 + 1100 * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    blk = 480
    for i in range(0, n, blk):
        c = fc[min(i + blk // 2, n - 1)]
        sos = ss.butter(2, [c * 0.6, c * 1.5], btype="bandpass", fs=SR, output="sos")
        seg = x[max(0, i - 2048):i + blk]
        y[i:i + blk] = ss.sosfilt(sos, seg)[-len(x[i:i + blk]):]
    return y * np.sin(np.pi * t / dur) ** 1.5


def wall_thud(seed=0):
    x = addp(thump(52, 0.7, 0.16, 0.5, seed, fall=1.8), 0.5 * thump(110, 0.4, 0.07, 0, seed + 1))
    return lp(x, 700)


def clatter(seed=0):
    r = np.random.default_rng(seed); out = np.zeros(n_(1.0))
    for k in range(8):
        base = r.uniform(850, 1500)
        c = clink([base, base * 2.31, base * 3.7], r.uniform(0.05, 0.11), seed + k, 0.4 + 0.6 * r.random())
        p = n_(r.uniform(0, 0.55)); c = c[:len(out) - p]; out[p:p + len(c)] += c * (1 - p / len(out))
    return lp(out, 3800)


def run_steps(dur=2.0, period=0.27, seed=0):
    out = np.zeros(n_(dur + 0.3)); k = 0
    while k * period < dur:
        s = addp(lp(white(n_(0.08), seed + k), 900) * env_exp(n_(0.08), 0.015), 0.6 * thump(95, 0.08, 0.02, 0, k))
        p = n_(k * period); out[p:p + len(s)] += s * (1 - k * period / dur) ** 1.3; k += 1
    return out


def drip():
    n = n_(0.25); t = tt(n)
    f = 330 + 520 * (1 - np.exp(-t / 0.02))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.045) * np.minimum(t / 0.002, 1)
    return lp(x, 2500)


def suck(dur=0.55):
    """reverse swell: air pulled in before the push (rises, ends abruptly at the cut)"""
    n = n_(dur); t = tt(n)
    e = (t / dur) ** 2.2
    nz = lp(pink(n, 501), 900) * e
    tone = np.sin(2 * np.pi * np.cumsum(40 + 50 * (t / dur) ** 2) / SR) * e
    x = nz + 0.8 * tone
    x[-n_(0.004):] *= np.linspace(1, 0, n_(0.004))
    return x


def sub_hit():
    n = n_(1.6); t = tt(n)
    f = 30 + 55 * np.exp(-t / 0.05)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.45)
    x += 0.6 * lp(white(n, 502), 220, 4) * np.exp(-t / 0.08)
    return lp(x, 300) * np.minimum(t / 0.002, 1)


def debris_rain(dur=1.4, seed=503):
    r = np.random.default_rng(seed); out = np.zeros(n_(dur + 0.3))
    for k in range(16):
        p = n_(r.uniform(0.0, dur) ** 1.4 / dur ** 0.4)
        if r.random() < 0.5:
            c = thump(r.uniform(140, 260), 0.12, 0.02, 0.4, k)               # wood bits / clods
        else:
            c = clink([r.uniform(700, 1100), r.uniform(1500, 2100)], 0.05, k, 0.5)   # small shards, low and short
        c = c[:len(out) - p]; out[p:p + len(c)] += c * r.uniform(0.3, 1.0) * (1 - p / len(out))
    return lp(out, 3000)


def rumble_tail(dur=1.8):
    n = n_(dur); t = tt(n)
    return lp(brown(n, 504), 120, 4) * np.exp(-t / 0.6) * np.minimum(t / 0.02, 1)


def pop():
    n = n_(0.14); t = tt(n)
    f = 260 + 340 * np.exp(-t / 0.02)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.035) * np.minimum(t / 0.002, 1)
    return lp(x + 0.2 * lp(white(n, 3), 1500) * np.exp(-t / 0.004), 2500)


def receiver():
    x = rustle(0.3, 12) * 0.6
    tap = thump(260, 0.1, 0.015, 0.2, 13) * 0.6
    out = np.zeros(n_(0.4)); out[:len(x)] += x; out[n_(0.22):n_(0.22) + len(tap)] += tap; return out


def fire_crackle(n, seed=0, rate=7.0):
    r = np.random.default_rng(seed); out = np.zeros(n)
    cnt = int(n / SR * rate)
    for p in r.integers(0, n - n_(0.05), cnt):
        L = n_(r.uniform(0.004, 0.02))
        c = bp(white(L, int(p) % 100000), 700, 3200) * env_exp(L, L / SR / 3)
        out[p:p + L] += c * r.uniform(0.15, 1.0) ** 2
    return lp(out, 3500)


# ------------------------------------------------------------------ beds (stereo, full length)
def bed_forest(n):
    ch = []
    for s in (1, 2):
        g = 0.55 + 0.45 * (0.5 + 0.5 * smooth_noise(n, 0.35, 100 + s)) ** 1.5
        x = bp(pink(n, 10 + s), 180, 900) * g + 0.5 * lp(pink(n, 20 + s), 250) * (0.7 + 0.3 * g)
        ch.append(x)
    return norm_rms(np.stack(ch, 1), -32)


def bed_street(n):
    ch = []
    for s in (1, 2):
        g = 0.4 + 0.6 * (0.5 + 0.5 * smooth_noise(n, 0.5, 200 + s)) ** 2
        x = bp(pink(n, 30 + s), 140, 700) * g + 0.7 * lp(brown(n, 40 + s), 120)
        ch.append(x)
    return norm_rms(np.stack(ch, 1), -33)


def bed_room(n, seed=50, level=-44):
    ch = [lp(brown(n, seed + s), 260) + 0.35 * bp(pink(n, seed + 5 + s), 200, 1400) for s in (1, 2)]
    return norm_rms(np.stack(ch, 1), level)


def bed_office(n):
    x = bed_room(n, 60, -40)
    ticks = np.zeros(n); k = 0
    while n_(k * 1.0 + 0.13) + n_(0.08) < n:
        c = clock_tick(k % 2 == 1, k); p = n_(k * 1.0 + 0.13); ticks[p:p + len(c)] += c; k += 1
    ticks = norm_peak(ticks, -29)
    return x + np.stack([ticks, ticks * 0.9], 1)


def bed_choyxona(n):
    x = bed_room(n, 70, -40)
    fire = [lp(brown(n, 80 + s), 180) + 0.5 * bp(pink(n, 85 + s), 150, 700) * (0.8 + 0.2 * smooth_noise(n, 3, 87 + s)) for s in (1, 2)]
    fire = norm_rms(np.stack(fire, 1), -40)
    cr = [norm_peak(fire_crackle(n, 90 + s, 10.0), -28) for s in (1, 2)]
    return x + fire + np.stack(cr, 1)


def bed_void(n):
    return norm_rms(np.stack([lp(brown(n, 95 + s), 80, 4) for s in (1, 2)], 1), -48)


BED_GAIN = dict(forest=1.0, street=1.0, house=2.0, office=2.0, choyxona=5.0, void=0.0)


# ------------------------------------------------------------------ music
def additive(freqs, t, harms=6, roll=1.3, detune=0.0018, seed=0):
    r = np.random.default_rng(seed); x = np.zeros_like(t)
    for f in freqs:
        for d in (-detune, detune):
            for k in range(1, harms + 1):
                x += np.sin(2 * np.pi * f * (1 + d) * k * t + r.uniform(0, 6.28)) / k ** roll
    return x


def music(n, scenes, speech_env):
    t = tt(n)
    dark = additive([73.42, 110.0, 146.83, 174.61], t, 6, 1.4, seed=1)
    dark = lp(dark, 520, 4) * (0.8 + 0.2 * np.sin(2 * np.pi * t / 9.0))
    warm = additive([174.61, 220.0, 293.66], t, 3, 1.8, 0.0012, seed=2)
    warm = lp(warm, 900, 2) * (0.85 + 0.15 * np.sin(2 * np.pi * t / 7.0))
    drone = additive([36.71, 73.42], t, 3, 1.2, 0.001, seed=3)
    drone = lp(drone, 200, 4)
    dark, warm, drone = norm_rms(dark, -20), norm_rms(warm, -22), norm_rms(drone, -20)
    S = {s["id"]: s for s in scenes}

    def ramp(a, b, w=1.0):  # 1 between a..b with soft edges
        return np.clip(np.minimum((t - a) / w + 0.5, (b - t) / w + 0.5), 0, 1)

    warm_w = ramp(S[9]["start"], S[12]["end"], 1.2)
    dark_w = 1 - 0.85 * warm_w
    # drone grows from scene 16, rises through 18-19, stays to the end
    drone_w = 0.25 + 0.75 * np.clip((t - S[16]["start"]) / 2.0, 0, 1)
    drone_w += 0.6 * np.clip((t - S[18]["start"]) / (S[19]["end"] - S[18]["start"]), 0, 1) * (t < S[20]["end"])
    pad = dark * dark_w + warm * warm_w * 0.9 + drone * drone_w
    # scene 17: only the low drone
    blk = ramp(S[17]["start"], S[17]["end"], 0.15)
    pad = pad * (1 - blk) + drone * 1.2 * blk
    # 60 bpm pulse from scene 14 to the end of scene 21
    pulse = np.zeros(n); p0, p1 = S[14]["start"], S[21]["end"]
    k = 0
    while p0 + k < p1:
        b = thump(48, 0.6, 0.16, 0.0, k, fall=1.6); q = n_(p0 + k); pulse[q:q + len(b)] += b[:max(0, n - q)]; k += 1
    pulse = norm_peak(lp(pulse, 140), -14) * ramp(p0 + 0.5, p1, 1.0)
    breath = 1 + 0.12 * ((t >= p0) & (t <= p1)) * np.cos(2 * np.pi * (t - p0))
    m = pad * breath + np.stack([pulse])[0]
    m = norm_rms(m, -20)
    duck = 1 - (1 - db(-6)) * speech_env
    out = np.stack([m * duck, np.roll(m, 240) * duck], 1)
    return out


# ------------------------------------------------------------------ dynamics / loudness
def compress(x, thr_db=-14, ratio=3.0, att=0.004, rel=0.08):
    a = np.abs(x); fr = 48; m = len(a) // fr + 1
    pk = np.pad(a, (0, m * fr - len(a))).reshape(m, fr).max(1)
    env = np.zeros(m); ca, cr = math.exp(-fr / SR / att), math.exp(-fr / SR / rel)
    for i in range(m):
        p = env[i - 1] if i else 0.0
        env[i] = pk[i] + (p - pk[i]) * (ca if pk[i] > p else cr)
    lvl = 20 * np.log10(env + 1e-9)
    gdb = np.where(lvl > thr_db, (thr_db - lvl) * (1 - 1 / ratio), 0.0)
    g = np.interp(np.arange(len(x)), np.arange(m) * fr + fr / 2, db(gdb))
    return x * g


def lufs(x):
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1, -1.99004745483398, 0.99007225036621]
    y = ss.lfilter(b2, a2, ss.lfilter(b1, a1, x, axis=0), axis=0)
    blk, hopn = n_(0.4), n_(0.1)
    z = np.array([np.sum(np.mean(y[i:i + blk] ** 2, 0)) for i in range(0, len(y) - blk, hopn)])
    l = -0.691 + 10 * np.log10(z + 1e-12)
    z = z[l > -70]; L = -0.691 + 10 * np.log10(np.mean(z))
    z2 = z[(-0.691 + 10 * np.log10(z)) > L - 10]
    return -0.691 + 10 * np.log10(np.mean(z2))


def limit(x, ceil_db=-1.5, look=0.005, rel=0.06):
    from scipy.ndimage import minimum_filter1d
    c = db(ceil_db); pk = np.max(np.abs(x), 1)
    g = np.minimum(1.0, c / (pk + 1e-12))
    L = n_(look); g = minimum_filter1d(g, 2 * L + 1)
    sm = ss.lfilter([1 - math.exp(-1 / (rel * SR))], [1, -math.exp(-1 / (rel * SR))], g)
    g = np.minimum(g, sm)  # fast attack via min, smooth release
    g = minimum_filter1d(g, 2 * L + 1)
    g = ss.lfilter([1 - math.exp(-1 / (0.002 * SR))], [1, -math.exp(-1 / (0.002 * SR))], g[::-1])[::-1]
    y = x * g[:, None]
    return np.clip(y, -c, c)


# ------------------------------------------------------------------ main
def main(vo, timing, outdir):
    T = json.load(open(timing)); scenes = T["scenes"]
    dur = math.floor(T["duration"] * 30 + 0.5) / 30   # frame-aligned length (30 fps)
    n = n_(dur)
    sr, v = wf.read(vo); v = v.astype(np.float64); assert sr == SR
    v = hp(v, 60)
    v = compress(v / np.max(np.abs(v)) * db(-3), -18, 3.0)
    # ---- voice clips (15 ms fades) placed on the timeline
    voice = np.zeros(n)
    for c in T["clips"]:
        seg = v[n_(c["src0"]):n_(c["src1"])].copy()
        f = n_(0.015); w = np.sin(np.linspace(0, np.pi / 2, f)) ** 2
        seg[:f] *= w; seg[-f:] *= w[::-1]
        p = n_(c["t0"]); voice[p:p + len(seg)] += seg
    act = voice[np.abs(voice) > 0.02]
    vrms = np.sqrt(np.mean(act ** 2)); voice *= db(-18) / vrms
    # speech envelope for ducking (attack 60 ms, release 350 ms)
    fr = n_(0.01); m = len(voice) // fr
    e = np.sqrt(np.mean(voice[:m * fr].reshape(m, fr) ** 2, 1)); on = (e > db(-40)).astype(float)
    g = np.zeros(m); a_at, a_rel = math.exp(-1 / 6), math.exp(-1 / 35)
    for i in range(m):
        prev = g[i - 1] if i else 0.0
        g[i] = on[i] + (prev - on[i]) * (a_at if on[i] > prev else a_rel)
    speech_env = np.interp(np.arange(n), np.arange(m) * fr + fr / 2, g)

    # ---- ambience beds with 0.4 s crossfades at cuts
    beds = dict(forest=bed_forest, street=bed_street, house=lambda n: bed_room(n, 50, -39), office=bed_office,
                choyxona=bed_choyxona, void=bed_void)
    amb = np.zeros((n, 2)); t = tt(n)
    for loc, fn in beds.items():
        w = np.zeros(n)
        for s in scenes:
            if s["loc"] != loc: continue
            a, b = s["start"], s["end"]
            wa = 1.0 if a <= 0 else np.clip((t - (a - 0.2)) / 0.4, 0, 1)
            wb = 1.0 if b >= dur - 1e-6 else np.clip(((b + 0.2) - t) / 0.4, 0, 1)
            w = np.maximum(w, np.minimum(wa, wb))
        if w.max() > 0: amb += fn(n) * w[:, None] * db(BED_GAIN[loc])
    S = {s["id"]: s for s in scenes}
    # scene 17: everything but the drone pulls right down (never to silence)
    blk = np.clip(np.minimum((t - S[17]["start"]) / 0.05, (S[17]["end"] - t) / 0.3), 0, 1)
    amb *= (1 - 0.75 * blk)[:, None]
    amb *= (1 - (1 - db(-8)) * speech_env)[:, None]
    c20 = S[20]["start"]
    dip = np.clip((t - (c20 - 0.45)) / 0.45, 0, 1) * (t < c20 + 0.1) + (t >= c20 + 0.1) * np.clip(1 - (t - (c20 + 0.1)) / 0.7, 0, 1)
    dipg = 1 - (1 - db(-10)) * dip
    amb *= dipg[:, None]

    # ---- sfx events (absolute times from scene starts)
    def at(sid, dt): return S[sid]["start"] + dt
    ev = []  # (time, signal, peak_db, pan)
    ev += [(0.0, swell(), -19, 0)]
    for k, dt in enumerate((0.28, 1.05)): ev.append((at(2, dt), leaf_step(k), -24, -0.15 + 0.3 * k))
    for k, dt in enumerate((0.0, 0.17, 0.33, 0.5)): ev.append((at(3, dt), wood_step(k), -25, 0.1))
    ev.append((at(3, 0.05), lp(addp(thump(68, 0.45, 0.1, 0.3, 5), 0.3 * creak(0.35, 420, True, 6)), 900), -21, -0.2))
    ev.append((at(4, 0.15), creak(0.75, 480, False, 7), -27, 0.2))
    ev.append((at(5, 0.45), spoon_clinks(), -28, 0.25))
    ev.append((at(7, 11.6 - 10.4), rustle(0.55, 8), -25, -0.1))
    ev.append((at(8, 0.0), thump(80, 0.3, 0.06, 0.4, 9), -21, 0))
    ev.append((at(8, 0.04), sting(), -20, 0))
    ev.append((at(9, 15.6 - 15.0), lagan_set(), -24, 0.1))
    ev.append((at(12, 0.75), clock_tick(False, 3), -33, 0.3))
    ev.append((at(13, 0.0), dial_clicks(0.45, 6), -27, -0.3))
    ev.append((at(13, 0.4), receiver(), -30, -0.3))
    eng_d = S[15]["end"] - S[14]["start"] + 0.4
    e_sig = engine(eng_d, 3); te = tt(len(e_sig))
    e_sig *= np.clip(te / 1.0, 0, 1) * np.where(te > S[14]["end"] - S[14]["start"], 0.55, 1.0) * np.clip((eng_d - te) / 0.4, 0, 1)
    ev.append((at(14, 0.0), e_sig, -22, 0))
    ev.append((at(14, 0.05), gravel(0.8, 900, 11), -24, 0.1))
    ev.append((at(14, 0.95), car_door(12), -21, -0.25))
    ev.append((at(14, 1.5), car_door(13), -22, 0.3))
    for k, dt in enumerate((0.25, 0.85, 1.45)): ev.append((at(15, dt), gravel_step(20 + k), -26, -0.1 + 0.1 * k))
    ev.append((at(16, 0.1), creak(1.3, 300, True, 21), -25, -0.1))
    ev.append((S[17]["start"], boom(), -17, 0))
    for k, dt in enumerate((0.2, 0.9, 1.6)): ev.append((at(18, dt), wood_step(30 + k, True), -23, 0.1 - 0.1 * k))
    ev.append((at(19, 0.0), rumble_rise(S[19]["end"] - S[19]["start"] + 0.1), -22, 0))
    ev.append((at(19, 0.15), heartbeat(2, 0.9), -20, 0))
    ev.append((at(20, 0.0) - 0.55, suck(0.55), -22, 0))
    ev.append((at(20, 0.0), whoosh(0.6), -23, -0.2))
    ev.append((at(20, 0.10), sub_hit(), -15, 0))
    ev.append((at(20, 0.14), rumble_tail(1.8), -22, 0))
    ev.append((at(20, 0.45), debris_rain(1.3), -29, -0.1))
    ev.append((at(20, 0.12), wall_thud(40), -19, -0.15))
    ev.append((at(20, 0.30), wall_thud(41), -21, 0.15))
    ev.append((at(20, 0.22), clatter(42), -27, 0.2))
    ev.append((at(21, 0.0), run_steps(2.0, 0.27, 50), -25, 0.1))
    ev.append((at(22, 0.35), drip(), -27, 0))
    ev.append((at(22, 0.35), thump(50, 0.6, 0.15, 0.0, 60), -20, 0))
    obuna = [w for w in T["words"] if w["line"] == 8 and w["text"].lower().startswith("obuna")][0]["t0"]
    ev.append((obuna, pop(), -26, 0))
    sfx = np.zeros((n, 2))
    for t0, sig, pk, pan in ev:
        sig = norm_peak(sig, pk); p = n_(t0); sig = sig[:max(0, n - p)]
        l, r = math.cos((pan + 1) * math.pi / 4) * math.sqrt(2), math.sin((pan + 1) * math.pi / 4) * math.sqrt(2)
        sfx[p:p + len(sig), 0] += sig * l; sfx[p:p + len(sig), 1] += sig * r
    sfx *= (1 - (1 - db(-6)) * speech_env)[:, None]

    mus = music(n, scenes, speech_env) * db(-24) * dipg[:, None]  # pad RMS -20 dBFS -> about -44 dBFS, ~26 dB under the -18 dBFS voice

    vo2 = np.stack([voice, voice], 1)
    mix = vo2 + amb + sfx + mus
    # ending: after the last word keep wind + drone, fade everything over the last 1.0 s
    fade = np.clip((dur - t) / 1.0, 0, 1); fade = np.sin(fade * np.pi / 2) ** 2
    mix *= fade[:, None]
    # loudness: -15 LUFS integrated, lookahead limiter at -1.5 dBFS
    L0 = lufs(mix); gain = db(-15.0 - L0)
    mix = limit(mix * gain, -1.5)
    print(f"loudness before {L0:.1f} LUFS, gain {20*np.log10(gain):+.1f} dB, after {lufs(mix):.1f} LUFS")
    os.makedirs(outdir, exist_ok=True)
    wf.write(os.path.join(outdir, "mix.wav"), SR, mix.astype(np.float32))
    for name, x in (("voice", vo2), ("amb", amb), ("sfx", sfx), ("music", mus)):
        wf.write(os.path.join(outdir, f"stem_{name}.wav"), SR, (x * gain * fade[:, None]).astype(np.float32))
    json.dump(dict(gain=float(gain), events=[(round(a, 3), b) for a, _, b, _ in ev]), open(os.path.join(outdir, "audio_meta.json"), "w"))
    print("mix written", mix.shape, "gain", gain)


if __name__ == "__main__":
    main(*sys.argv[1:4])
