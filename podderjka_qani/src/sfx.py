# Code-synthesized soft SFX for the key actions only (no downloads, no music).
# No vocal track is used, so nothing is ducked; the SFX bus sits low (peaks around -16 dBFS) so a vocal
# added on top later stays ~20 dB louder.
import os, json, math, wave
import numpy as np
from scipy import signal
from common import BUILD, FPS
from script_data import SCENES, TOTAL, CHA_F

SR = 48000
rng = np.random.RandomState(7)

def db(x): return 10 ** (x / 20)
def env(n, a=0.004, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)
def bp(x, lo, hi, order=2): return signal.sosfilt(signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, fc, order=2): return signal.sosfilt(signal.butter(order, fc, btype="low", fs=SR, output="sos"), x)
def hp(x, fc, order=2): return signal.sosfilt(signal.butter(order, fc, btype="high", fs=SR, output="sos"), x)
def norm(x, peak=1.0): return x / (np.abs(x).max() + 1e-9) * peak
def sweep(f0, f1, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / dur); return np.sin(2 * np.pi * np.cumsum(f) / SR)

# ---------------------------------------------------------------- sounds (all soft: low-passed, no sharp transients)
def glass_knock():
    n = int(0.16 * SR); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 210 * t) * env(n, 0.002, 0.03)
    tok = bp(rng.randn(n), 900, 2600) * env(n, 0.001, 0.012)
    ring_ = np.sin(2 * np.pi * 1850 * t) * env(n, 0.002, 0.04) * 0.12
    return norm(lp(0.9 * body + 0.6 * tok + ring_, 3200))

def soft_accent():
    n = int(0.9 * SR); t = np.arange(n) / SR
    y = sweep(120, 70, 0.9) * env(n, 0.01, 0.25) + 0.25 * np.sin(2 * np.pi * 440 * t) * env(n, 0.03, 0.3)
    return norm(lp(y, 1500))

def step(dark=700):
    n = int(0.12 * SR)
    y = lp(rng.randn(n), dark) * env(n, 0.003, 0.025) + 0.5 * sweep(110, 60, 0.12) * env(n, 0.002, 0.03)
    return norm(y)

def sand_step():
    n = int(0.16 * SR)
    grains = (rng.rand(n) < 0.05).astype(float) * rng.rand(n)
    y = bp(rng.randn(n) * 0.4 + grains * 2.5, 700, 3800) * env(n, 0.01, 0.05)
    return norm(lp(y, 4200) + 0.3 * lp(rng.randn(n), 300) * env(n, 0.005, 0.03))

def wind(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.randn(n)
    sw = 0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * t) * np.sin(2 * np.pi * 0.23 * t + 1)
    y = bp(x, 250, 1400) * sw
    fade = np.minimum(1, t / 0.4) * np.minimum(1, (dur - t) / 0.5)
    return norm(lp(y, 1200) * fade)

def pop():
    n = int(0.09 * SR)
    return norm(lp(sweep(480, 190, 0.09) * env(n, 0.003, 0.03), 2200))

def bloop(f0=380):
    n = int(0.25 * SR)
    return norm(lp(sweep(f0, f0 * 2.1, 0.25) * env(n, 0.004, 0.06), 2000))

def water_bed(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    y = bp(rng.randn(n), 300, 1500) * (0.6 + 0.4 * np.sin(2 * np.pi * 1.3 * t))
    return norm(lp(y, 1600) * np.minimum(1, t / 0.4) * np.minimum(1, (dur - t) / 0.4))

def thump():
    n = int(0.42 * SR)
    y = sweep(92, 44, 0.42) * env(n, 0.006, 0.11) + 0.35 * lp(rng.randn(n), 260) * env(n, 0.003, 0.03)
    return norm(lp(y, 800))

def thud():
    n = int(0.22 * SR)
    y = sweep(140, 70, 0.22) * env(n, 0.003, 0.05) + 0.4 * lp(rng.randn(n), 500) * env(n, 0.002, 0.02)
    return norm(lp(y, 1200))

def rustle(dur=0.3):
    n = int(dur * SR); t = np.arange(n) / SR
    crack = (rng.rand(n) < 0.02).astype(float) * rng.rand(n)
    crack = np.convolve(crack, np.exp(-np.arange(120) / 20.0), mode="same")
    y = bp(rng.randn(n) * 0.35 + crack * 2.5, 1200, 5000) * np.sin(np.pi * t / dur) ** 1.2
    return norm(lp(y, 5200))

def swell(dur=1.0):
    """mellow karnay-like swell: odd harmonics, slow attack, heavy low-pass"""
    n = int(dur * SR); t = np.arange(n) / SR
    f = 233.1 * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.33 * np.sin(3 * ph) + 0.14 * np.sin(5 * ph) + 0.4 * np.sin(2 * ph)
    e = np.minimum(1, t / 0.18) ** 2 * np.minimum(1, (dur - t) / 0.35)
    return norm(lp(y * e, 1300, order=4))

def whoosh(dur=0.55, lo=300, hi=2200):
    n = int(dur * SR); t = np.arange(n) / SR
    y = bp(rng.randn(n), lo, hi) * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2.2
    return norm(lp(y, 2600))

def clap():
    n = int(0.14 * SR)
    burst = np.zeros(n)
    for k, o in enumerate((0, 0.006, 0.013)):
        i = int(o * SR); m = n - i
        burst[i:] += rng.randn(m) * env(m, 0.0008, 0.012) * (1 - 0.2 * k)
    tail = rng.randn(n) * env(n, 0.002, 0.05) * 0.4
    return norm(lp(bp(burst + tail, 700, 3500), 3800))

def engine(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    chug = (0.5 + 0.5 * np.sin(2 * np.pi * 14 * t)) ** 3
    y = lp(rng.randn(n), 160) * 3 + np.sin(2 * np.pi * 42 * t) * 0.5
    y = y * (0.35 + 0.65 * chug)
    return norm(lp(y, 380) * np.minimum(1, t / 0.3) * np.minimum(1, (dur - t) / 0.4))

def flutter(dur=0.6):
    n = int(dur * SR); t = np.arange(n) / SR
    rate = 26 + 6 * np.sin(2 * np.pi * 2 * t)
    am = (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(rate) / SR)) ** 2
    y = bp(rng.randn(n), 900, 4200) * am * np.sin(np.pi * t / dur) ** 1.3
    return norm(lp(y, 4500))

# ---------------------------------------------------------------- event list
def S(i): return SCENES[i - 1]["start"]

def events():
    ev = []
    def add(t, snd, g, name): ev.append((round(t, 4), snd, g, name))
    # 1: soft accent at 0.0 + a soft glass knock on every knock (4 per second)
    add(0.0, soft_accent(), -10, "accent")
    k = 0
    while k * 0.25 < SCENES[0]["end"] - 0.05:
        add(k * 0.25, glass_knock(), -6 - 2 * (k % 2), "glass knock"); k += 1
    # 2: soft footsteps of the passers-by
    for j in range(6):
        add(S(2) + 0.12 + j * 0.29, step(), -15 - 3 * (j % 2), "footstep")
    # 3: soft wind
    add(S(3), wind(SCENES[2]["end"] - S(3) + 0.2), -14, "wind")
    # 4: pop when he points at the viewer
    add(S(4) + 1.15, pop(), -8, "pop")
    # 6: soft water ripple
    add(S(6), water_bed(SCENES[5]["end"] - S(6)), -24, "water bed")
    for j, o in enumerate((0.2, 0.75, 1.3)):
        add(S(6) + o, bloop(360 + 60 * j), -16, "ripple")
    # 7: soft footsteps of the hero
    for o in (0.05, 0.33, 0.61, 1.5, 1.78):
        add(S(7) + o, step(600), -13, "footstep")
    # 8: soft thump on each landing
    for o in (0.80, 1.20, 1.55):
        add(S(8) + o, thump(), -6, "landing thump")
    # 9: soft thud as boxes land
    for o, g in ((0.85, -10), (1.05, -10), (1.28, -14), (1.45, -11), (1.6, -12)):
        add(S(9) + o, thud(), g, "box thud")
    # 10: soft paper rustle
    for i in range(6):
        add(S(10) + 0.05 + i * 0.24, rustle(0.2), -16, "paper rustle")
    add(S(10) + 1.0, rustle(0.6), -14, "paper rustle (wind)")
    # 12: short soft swell
    add(S(12) + 0.34, swell(1.0), -9, "karnay swell")
    # 13: soft whoosh per plane
    for o in (0.15, 0.62, 1.08):
        add(S(13) + o, whoosh(0.6), -12, "plane whoosh")
    # 14: soft clap on each cha
    for f in CHA_F:
        add(f / FPS, clap(), -9, "cha clap")
    # 15: footsteps on sand
    for j in range(9):
        add(S(15) + 0.12 + j / 3.8, sand_step(), -14, "sand step")
    # 16: one soft low thump
    add(S(16), thump(), -4, "freeze thump")
    # 18: soft engine idle
    add(S(18), engine(SCENES[17]["end"] - S(18)), -15, "engine idle")
    # 19: paper flutter
    for o in (0.6, 1.55):
        add(S(19) + o, flutter(0.8), -13, "paper flutter")
    return ev

def build(out_wav):
    n = int(round(TOTAL * SR))
    mix = np.zeros(n)
    ev = events()
    for t0, snd, g, name in ev:
        o = int(round(t0 * SR))
        if o >= n: continue
        m = min(len(snd), n - o)
        mix[o:o + m] += snd[:m] * db(g)
    # bus: gentle low-pass, peak at -16 dBFS
    mix = lp(mix, 9000)
    mix = mix / (np.abs(mix).max() + 1e-9) * db(-16)
    # tiny fades so frame 0 / loop point have no click
    f = int(0.004 * SR); mix[:f] *= np.linspace(0, 1, f); mix[-f:] *= np.linspace(1, 0, f)
    st = np.stack([mix, mix], 1)
    pcm = np.clip(st * 32767, -32768, 32767).astype(np.int16)
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    log = [dict(t=t0, name=name, gain_db=g) for t0, _, g, name in ev]
    with open(os.path.join(BUILD, "sfx_log.json"), "w") as fh: json.dump(log, fh, indent=1)
    return out_wav, len(ev)

if __name__ == "__main__":
    p, k = build(os.path.join(BUILD, "sfx.wav"))
    print(p, k, "events")
