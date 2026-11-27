# Audio: voice lines placed at their voice_start, sfx and an analog-synth drone
# synthesized in code, ducking under speech, final mix (48 kHz stereo, 50.0 s).
import json, sys, os
import numpy as np
from scipy import signal
from scipy.io import wavfile
from config import *
import cues as C

N = int(round(DURATION * SR))
rng = np.random.default_rng(1980)

def db(x): return 10 ** (x / 20)

def sec(t): return int(round(t * SR))

def lp(x, f, order=4): return signal.sosfilt(signal.butter(order, f, "low", fs=SR, output="sos"), x)
def hp(x, f, order=2): return signal.sosfilt(signal.butter(order, f, "high", fs=SR, output="sos"), x)
def bp(x, f1, f2, order=2): return signal.sosfilt(signal.butter(order, [f1, f2], "band", fs=SR, output="sos"), x)

def noise(d): return rng.standard_normal(sec(d))

def tvec(d): return np.arange(sec(d)) / SR

def fade(x, fi=0.01, fo=0.01):
    x = x.copy(); a, b = sec(fi), sec(fo)
    if a: x[:a] *= np.linspace(0, 1, a)
    if b: x[-b:] *= np.linspace(1, 0, b)
    return x

def mx(*xs):
    n = max(len(x) for x in xs); out = np.zeros(n)
    for x in xs: out[:len(x)] += x
    return out

def norm_peak(x, peak_db):
    m = np.abs(x).max()
    return x * (db(peak_db) / m) if m > 0 else x

def norm_rms(x, rms_db):
    r = np.sqrt(np.mean(x ** 2))
    return x * (db(rms_db) / r) if r > 0 else x

def reverb(x, rt=0.6, wet=0.25, tone=3000):
    n = sec(rt)
    ir = rng.standard_normal(n) * np.exp(-6.9 * np.arange(n) / n)
    ir = lp(ir, tone)
    ir /= np.sqrt(np.sum(ir ** 2))
    y = signal.fftconvolve(x, ir)
    out = np.zeros(len(y)); out[:len(x)] += x * (1 - wet)
    return out + y * wet

class Bus:
    def __init__(self):
        self.L = np.zeros(N); self.R = np.zeros(N)
    def add(self, t, x, pan=0.0, gain=1.0):
        i = sec(t)
        if i < 0: x = x[-i:]; i = 0
        x = x[:max(0, N - i)] * gain
        gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        self.L[i:i + len(x)] += x * gl * np.sqrt(2)
        self.R[i:i + len(x)] += x * gr * np.sqrt(2)
    def add_st(self, t, l, r, gain=1.0):
        i = sec(t); l = l[:N - i] * gain; r = r[:N - i] * gain
        self.L[i:i + len(l)] += l; self.R[i:i + len(r)] += r

# ---------------------------------------------------------------------------
# sound sources
def thump(f=70, d=0.35, click=0.3):
    t = tvec(d)
    body = np.sin(2 * np.pi * (f + 40 * np.exp(-t * 30)) * t) * np.exp(-t * 11)
    tr = lp(noise(d), 1500) * np.exp(-t * 60) * click
    return fade(body + tr, 0.002, 0.03)

def metal(freqs=(182, 297, 471, 733), d=0.7, decay=6.0):
    t = tvec(d)
    x = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * np.exp(-t * decay * (1 + i * 0.4)) / (1 + i)
            for i, f in enumerate(freqs))
    return fade(x, 0.002, 0.05)

def alarm_pulse(strength=1.0):
    d = 0.42; t = tvec(d)
    f = 560 - 120 * np.minimum(t / 0.35, 1)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.25 * np.sin(2 * ph)) * np.minimum(t / 0.03, 1) * np.exp(-t * 5.5)
    return fade(lp(x, 1400), 0.002, 0.06) * strength

def footstep(level=1.0, bright=1500):
    d = 0.12; t = tvec(d)
    x = np.sin(2 * np.pi * 95 * t) * np.exp(-t * 45) + 0.5 * lp(noise(d), bright) * np.exp(-t * 70)
    return fade(x, 0.001, 0.02) * level

def wind(d, lo=150, hi=900, rate=0.18):
    x = bp(noise(d), lo, hi)
    t = tvec(d)
    m = 0.55 + 0.45 * np.sin(2 * np.pi * rate * t + 1.3) * np.sin(2 * np.pi * rate * 0.37 * t + 0.4)
    return x * m

def hum(d, f0=50, harm=(1, 0.5, 0.3, 0.12), jitter=0.002):
    t = tvec(d)
    x = sum(a * np.sin(2 * np.pi * f0 * (k + 1) * t * (1 + jitter * np.sin(2 * np.pi * 0.3 * t))) for k, a in enumerate(harm))
    return x

def buzz(d, f0=100):
    t = tvec(d)
    saw = 2 * ((f0 * t) % 1.0) - 1
    return lp(saw, 700, 2) * 0.6 + 0.4 * np.sin(2 * np.pi * f0 * t)

def click(level=1.0, f=1800, d=0.035):
    t = tvec(d)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 260) + 0.6 * lp(noise(d), 4000) * np.exp(-t * 400)
    return lp(fade(x, 0.0005, 0.005), 3500) * level

def rustle(d):
    t = tvec(d)
    x = bp(noise(d), 700, 3200)
    gate = np.zeros_like(t)
    for _ in range(int(d * 22)):
        c = rng.uniform(0, d); w = rng.uniform(0.01, 0.05)
        gate += rng.uniform(0.3, 1) * np.exp(-((t - c) / w) ** 2)
    return x * np.minimum(gate, 1.2) * np.minimum(1, np.minimum(t, d - t) / 0.05)

def tick(level=1.0, f=2600):
    d = 0.02; t = tvec(d)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 500) + 0.4 * bp(noise(d), 1500, 4000) * np.exp(-t * 700)
    return lp(x, 4200) * level

def breath(d=0.9, lo=350, hi=1800, inhale=True):
    t = tvec(d)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** (1.5 if inhale else 0.8)
    return bp(noise(d), lo, hi) * env

def skid(d=0.35):
    t = tvec(d)
    x = bp(noise(d), 500, 2400) * np.exp(-t * 3) * np.minimum(t / 0.02, 1)
    return fade(lp(x, 2000), 0.005, 0.08)

def creak(d=0.8):
    t = tvec(d)
    rate = 55 + 60 * np.sin(np.pi * t / d) ** 2 + 10 * np.sin(2 * np.pi * 3 * t)
    ph = np.cumsum(rate) / SR
    imp = np.zeros_like(t)
    idx = np.where(np.diff(np.floor(ph)) > 0)[0]
    imp[idx] = rng.uniform(0.5, 1.0, len(idx))
    x = bp(imp, 500, 900, 2) + 0.6 * bp(imp, 1100, 1500, 2)
    return fade(lp(x, 2200), 0.05, 0.12)

def wet_breath(d=1.3):
    t = tvec(d)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.2
    gurgle = 0.6 + 0.4 * (np.sin(2 * np.pi * 23 * t + 3 * np.sin(2 * np.pi * 4 * t)) > 0.3)
    x = bp(noise(d), 120, 650) * env * gurgle + 0.3 * np.sin(2 * np.pi * 62 * t) * env
    return lp(x, 900)

# ---------------------------------------------------------------------------
def build_voice(timing):
    x, sr = read_voice()
    v = np.zeros(N)
    for line, L in timing["lines"].items():
        a, b = LINE_CUTS[int(line)]
        seg = x[int(round(a * SR)):int(round(b * SR))].astype(np.float64)
        seg = fade(seg, 0.006, 0.02)
        # per-line loudness match (narrator lines are much quieter than the shouted lines)
        env = np.abs(signal.hilbert(seg))
        act = seg[lp(env, 20) > 0.1 * lp(env, 20).max()]
        target = {3: -19.5, 4: -19.0}.get(int(line), -20.0)
        seg = seg * db(target) / np.sqrt(np.mean(act ** 2))
        i = sec(L["voice_start"])
        v[i:i + len(seg)] += seg
    return v

def read_voice():
    sr, x = wavfile.read(VOICE_WAV)
    x = x.astype(np.float64)
    if x.ndim > 1: x = x.mean(1)
    if np.abs(x).max() > 2: x /= 32768
    assert sr == SR
    return x, sr

def P(x, peak_db):
    """transient at an absolute peak level (dBFS)"""
    return norm_peak(x, peak_db)

def R(x, rms_db):
    """bed at an absolute RMS level (dBFS)"""
    return norm_rms(x, rms_db)

def build_sfx():
    S = Bus()
    # 0-3 s hook: one accented soft alarm pulse at 0.0, then pulses synced to the red lamp; quick footsteps
    for k, t in enumerate(C.ALARM_TIMES):
        S.add(t, reverb(P(alarm_pulse(), -14 if k == 0 else -18), 0.9, 0.3), pan=-0.1)
    for k, t in enumerate(np.arange(0.06, 2.95, 0.27)):
        S.add(t, reverb(P(footstep(), -19 - 7 * t / 3.0), 0.7, 0.3), pan=0.15 * (-1) ** k)
    # scene 1: low night wind (F02), lift hum (F03)
    w = fade(R(wind(2.7), -36), 0.25, 0.5); S.add_st(3.0, w, np.roll(w, 900))
    S.add(5.5, fade(R(lp(hum(3.9, 50) + 0.04 * noise(3.9), 400), -36), 0.3, 0.4))
    # scene 2: heavy door clunk, whoosh + soft dull thud, electric flicker buzz
    S.add(C.DOOR_SHUT, reverb(P(mx(thump(62, 0.5, 0.25), 0.5 * metal()), -10), 0.8, 0.3))
    wh = bp(noise(0.24), 250, 1100) * np.sin(np.pi * np.linspace(0, 1, sec(0.24))) ** 2
    S.add(C.CREATURE_LAND - 0.2, P(wh, -20), pan=0.1)
    S.add(C.CREATURE_LAND, reverb(P(thump(55, 0.45, 0.15), -12), 0.7, 0.25))
    d = 14.0 + D1 - C.F06_T0
    tt = C.F06_T0 + tvec(d)
    gate = signal.lfilter([0.02], [1, -0.98], np.array([C.f06_lamp(t) for t in tt]))
    S.add(C.F06_T0, fade(R(buzz(d), -33) * gate, 0.02, 0.2))
    for s, v in C.F06_STEPS[1:]:
        S.add(C.F06_T0 + s, P(click(1, 1500), -26))
    # scene 3: quiet bulb hum, paper rustle
    S.add(14.0 + D1, fade(R(lp(hum(4.5, 100, (1, 0.3, 0.1)), 500), -40), 0.3, 0.3))
    S.add(14.55 + D1, P(rustle(0.5), -25), pan=-0.2)
    S.add(15.55 + D1, P(rustle(0.7), -24), pan=0.1)
    # scene 4: laughter only from kulgi.mp3 (never synthesized)
    if KULGI and os.path.exists(KULGI):
        S.add(20.0 + D1, P(load_kulgi(KULGI), -12))
    # scene 5: bike chain ticking, light night wind, lamp buzz with flicker clicks
    t0 = 23.0 + D1
    for t in np.arange(t0 + 0.05, 28.0, 1 / 7.5):
        S.add(t, P(tick(1, 1900), -25 - rng.uniform(0, 4)), pan=-0.1)
    w = fade(R(wind(28.0 - t0, 180, 1000, 0.25), -35), 0.4, 0.4); S.add_st(t0, w, np.roll(w, 700))
    d = 2.5; tt = 25.5 + tvec(d)
    gate = signal.lfilter([0.05], [1, -0.95], np.array([C.f12_lamp(t) for t in tt]))
    S.add(25.5, fade(R(buzz(d, 120), -37) * gate, 0.2, 0.2), pan=0.3)
    for a, b in C.F12_OFF:
        S.add(a, P(click(1, 1400), -23), pan=0.3); S.add(b, P(click(1, 1600), -23), pan=0.3)
    # scene 6: soft tire skid and fall thump at 30.0, fast footsteps and breathing
    S.add(C.FALL_T - 0.22, P(skid(0.3), -21))
    S.add(C.FALL_T, P(mx(thump(75, 0.4, 0.3), 0.35 * metal((420, 655, 1010), 0.5, 9)), -11))
    for k, t in enumerate(np.arange(31.55, 33.0, 0.19)):
        S.add(t, P(footstep(1, 1200), -19), pan=0.2 * (-1) ** k)
    for k, t in enumerate(np.arange(31.5, 33.0, 0.36)):
        S.add(t, P(breath(0.3, 500, 2000, k % 2 == 0), -25))
    # scene 7: door creak, clock ticking, shed door closing softly, quiet breathing
    S.add(33.02, reverb(P(creak(0.85), -21), 0.6, 0.25), pan=0.25)
    for k, t in enumerate(np.arange(33.1, 37.0, 0.5)):
        S.add(t, reverb(P(tick(1, 2300 if k % 2 else 1700), -27), 0.5, 0.3), pan=-0.35)
    S.add(C.SHED_DOOR_T, P(mx(thump(110, 0.3, 0.2), 0.25 * metal((380, 870, 1290), 0.25, 18)), -16))
    for k, t in enumerate(np.arange(35.2, 37.0, 0.62)):
        S.add(t, P(breath(0.5, 400, 1600, k % 2 == 0), -30))
    # scene 8: low wet breath at 38.0, bulb click off at 39.5, then silence
    S.add(C.WET_BREATH_T, reverb(P(wet_breath(1.3), -15), 0.5, 0.2))
    S.add(C.LIGHT_OFF_T, P(click(1, 1300, 0.05), -15))
    # scene 9: bulb click on at 41.0 with hum
    S.add(C.LIGHT_ON_T, P(click(1, 1500, 0.05), -15))
    S.add(C.LIGHT_ON_T + 0.02, fade(R(lp(hum(2.0, 100, (1, 0.35, 0.1)), 500), -39), 0.05, 0.4))
    # wheel freewheel: one tick per pawl step, ticking slows and stops with the wheel
    PAWL = 18
    tt = np.arange(sec(C.WHEEL_T0), sec(C.WHEEL_STOP + 0.05), 48) / SR
    steps = np.floor(np.array([C.wheel_angle(t) for t in tt]) * PAWL)
    for i in np.where(np.diff(steps) > 0)[0]:
        t = tt[i + 1]
        S.add(t, P(tick(1, 2100), -25 - 5 * (1 - min(1, C.wheel_speed(t)))), pan=0.15)
    # last shot: street-lamp click off
    S.add(C.LAMP_OFF_T, P(click(1, 1200, 0.05), -18), pan=-0.1)
    return S

def load_kulgi(path):
    import subprocess
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    return fade(norm_peak(x, -3), 0.02, 0.3)

def build_music():
    """Low 1980s analog-synth drone (detuned saws through a slowly moving low-pass)."""
    t = np.arange(N) / SR
    def saw(f, ph=0.0):
        return 2 * ((f * t + ph) % 1.0) - 1
    vib = 1 + 0.002 * np.sin(2 * np.pi * 0.21 * t)
    base = 0.5 * (saw(55.0 * vib) + saw(55.35 * vib, 0.3)) + 0.35 * saw(82.41 * vib, 0.6) + 0.6 * np.sin(2 * np.pi * 27.5 * t)
    # time-varying low-pass: blocks with interpolated cutoff
    out = np.zeros(N); blk = 2400; zi = None
    def cutoff(tc):
        c = 180
        if tc > 23.0 + D1: c += 260 * C.smooth((tc - 23.0 - D1) / 4.6)
        if tc > 28.0: c += 250 * C.smooth((tc - 28.0) / 2.5)
        return c + 40 * np.sin(2 * np.pi * 0.07 * tc)
    for i in range(0, N, blk):
        sos = signal.butter(2, cutoff(i / SR), "low", fs=SR, output="sos")
        if zi is None: zi = signal.sosfilt_zi(sos) * 0
        out[i:i + blk], zi = signal.sosfilt(sos, base[i:i + blk], zi=zi)
    pad = 0.12 * np.sin(2 * np.pi * 220 * t * vib) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * t))
    tension = 0.10 * np.sin(2 * np.pi * 233.08 * t)          # minor-second rub for the re-hook
    y = out + pad + tension * np.clip((t - 37.0) / 2.0, 0, 1)
    # unit RMS everywhere (0.5 s running RMS), so the level shape below is absolute dBFS
    from scipy.ndimage import uniform_filter1d
    y = y / np.sqrt(uniform_filter1d(y ** 2, sec(0.5)) + 1e-9)
    # level shape (dB): quiet bed -> slow rise from scene 5 -> swell in 6 -> cut at 39.5 -> quiet return at 41.0
    g = np.zeros(N)
    for i in range(0, N, 480):
        tc = i / SR
        lv = -31.0
        if tc >= 23.0 + D1: lv += 4 * C.smooth((tc - 23.0 - D1) / 4.6)
        if tc >= 28.0: lv += 3 * C.smooth((tc - 28.0) / 1.5)
        if tc >= 33.0: lv -= 1.5 * C.smooth((tc - 33.0) / 1.0)
        if tc >= 37.0: lv += 1.5 * C.smooth((tc - 37.0) / 2.0)
        if tc >= C.LIGHT_OFF_T: lv = -120
        if tc >= C.LIGHT_ON_T: lv = -34 - 30 * (1 - C.smooth((tc - C.LIGHT_ON_T) / 1.2))
        if tc >= 49.6: lv -= 40 * C.smooth((tc - 49.6) / 0.4)
        g[i:i + 480] = db(lv)
    g = signal.lfilter([0.01], [1, -0.99], g)
    # hard cut at the light-out (10 ms), no smoothing tail
    cut = sec(C.LIGHT_OFF_T)
    g[cut:cut + sec(0.01)] *= np.linspace(1, 0, sec(0.01))
    g[cut + sec(0.01):sec(C.LIGHT_ON_T)] = 0
    y = y * g
    l = y; r = np.roll(y, 240) * 0.98 + 0.02 * y
    return l, r

def duck_env(v, depth_db=-8.0):
    a = np.abs(v)
    att, rel = np.exp(-1 / (0.02 * SR)), np.exp(-1 / (0.30 * SR))
    env = np.zeros_like(a); e = 0.0
    # look-ahead 30 ms so the duck is in place at the first syllable
    la = sec(0.03)
    a = np.concatenate([a[la:], np.zeros(la)])
    for i in range(0, len(a), 64):
        x = a[i:i + 64].max()
        e = att * e + (1 - att) * x if x > e else rel ** 64 * e + (1 - rel ** 64) * x
        env[i:i + 64] = e
    thr = 0.02
    on = np.clip(env / thr, 0, 1)
    on = signal.lfilter([0.002], [1, -0.998], on)
    return db(depth_db * np.clip(on * 1.2, 0, 1))

def limiter(x, ceiling_db=-1.0, look=0.004, release=0.08):
    """Look-ahead peak limiter on a (n,) or (n,2) signal."""
    from scipy.ndimage import minimum_filter1d
    pk = np.abs(x) if x.ndim == 1 else np.abs(x).max(1)
    need = np.minimum(1.0, db(ceiling_db) / np.maximum(pk, 1e-9))
    la = sec(look)
    need = minimum_filter1d(need, 2 * la + 1, origin=0)
    rel = np.exp(-1 / (release * SR))
    g = np.empty_like(need); e = 1.0
    for i in range(0, len(need), 32):
        m = need[i:i + 32].min()
        e = m if m < e else rel ** 32 * e + (1 - rel ** 32) * m
        g[i:i + 32] = e
    g = np.minimum(g, need)
    out = x * (g if x.ndim == 1 else g[:, None])
    return np.clip(out, -db(ceiling_db), db(ceiling_db))

def compressor(x, thr_db=-26, ratio=2.5, att=0.008, rel=0.15):
    a = np.abs(x)
    ka, kr = np.exp(-1 / (att * SR)), np.exp(-1 / (rel * SR))
    env = np.empty_like(a); e = 0.0
    for i in range(0, len(a), 32):
        v = np.sqrt(np.mean(a[i:i + 32] ** 2))
        e = ka ** 32 * e + (1 - ka ** 32) * v if v > e else kr ** 32 * e + (1 - kr ** 32) * v
        env[i:i + 32] = e
    lv = 20 * np.log10(np.maximum(env, 1e-9))
    over = np.maximum(0, lv - thr_db)
    return x * db(-over * (1 - 1 / ratio))

def lufs(stereo):
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        wavfile.write(f.name, SR, stereo.astype(np.float32))
        r = subprocess.run(["ffmpeg", "-hide_banner", "-i", f.name, "-af", "ebur128", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    import re
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])

TARGET_LUFS = -16.0

def main(timing_json, outdir):
    timing = json.load(open(timing_json))
    os.makedirs(outdir, exist_ok=True)
    voice = build_voice(timing)
    voice = compressor(voice, -28, 2.5)
    voice = voice * db(-16.5) / np.sqrt(np.mean(voice[np.abs(voice) > 0.003] ** 2))
    voice = limiter(voice, -1.5)
    S = build_sfx()
    ml, mr = build_music()
    g = duck_env(voice, -9.0)
    gs = duck_env(voice, -7.0)
    sfx = np.stack([S.L, S.R], 1) * gs[:, None]
    mus = np.stack([ml, mr], 1) * g[:, None]
    mix = limiter(voice[:, None] + sfx + mus, -1.0)
    print("integrated loudness", round(lufs(mix), 1), "LUFS")
    wavfile.write(os.path.join(outdir, "mix.wav"), SR, mix.astype(np.float32))
    wavfile.write(os.path.join(outdir, "stem_voice.wav"), SR, voice.astype(np.float32))
    wavfile.write(os.path.join(outdir, "stem_bg.wav"), SR, (sfx + mus).astype(np.float32))
    wavfile.write(os.path.join(outdir, "stem_sfx.wav"), SR, sfx.astype(np.float32))
    wavfile.write(os.path.join(outdir, "stem_music.wav"), SR, mus.astype(np.float32))
    print("mix written", mix.shape, "peak", round(float(np.abs(mix).max()), 3))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
