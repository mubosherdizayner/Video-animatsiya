# Soft synthesized SFX (no downloads) + mix with the voice-over, ducked under speech. Output: 48 kHz stereo wav.
import sys, json, math, wave, subprocess
import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt
import timeline as TL
from timeline import word_t, SC_START
import scenes as SC

SR = 48000
rng = np.random.RandomState(7)
DUR = TL.N_FRAMES / 30.0
N = int(round(DUR * SR))

def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype="low", fs=SR, output="sos"), x)
def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype="high", fs=SR, output="sos"), x)
def norm(x, peak=1.0):
    return x / (np.abs(x).max() + 1e-9) * peak
def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)
def fades(x, fi=0.02, fo=0.05):
    n = len(x); a = int(fi * SR); b = int(fo * SR)
    if a: x[:a] *= np.linspace(0, 1, a)
    if b: x[-b:] *= np.linspace(1, 0, b)
    return x

# ------------------------------------------------------------------ sound designs (all soft, band-limited)
def whoosh(dur=0.7):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.randn(n)
    y = bp(x, 300, 2400) * np.sin(np.pi * t / dur) ** 2
    return norm(lp(y, 3000))

def rustle(dur):
    n = int(dur * SR)
    x = rng.randn(n)
    grains = np.zeros(n)
    for _ in range(int(dur * 40)):
        p = rng.randint(0, n - 2000); L = rng.randint(300, 1800)
        grains[p:p + L] += np.hanning(L) * rng.uniform(0.3, 1.0)
    y = bp(x, 2000, 6500) * (0.25 + grains)
    return norm(fades(lp(y, 7000), 0.3, 0.5))

def wind(dur, lo=150, hi=900, wob=0.25, seed=1):
    r = np.random.RandomState(seed)
    n = int(dur * SR); t = np.arange(n) / SR
    x = r.randn(n)
    y = bp(x, lo, hi)
    m = 0.6 + wob * np.sin(2 * np.pi * 0.35 * t + 1) + 0.15 * np.sin(2 * np.pi * 0.9 * t)
    return norm(fades(y * m, 0.4, 0.5))

def crack():
    n = int(0.05 * SR)
    x = rng.randn(n) * env(n, 0.0008, 0.008)
    y = bp(x, 1500, 5000) + 0.3 * np.sin(2 * np.pi * 900 * np.arange(n) / SR) * env(n, 0.0005, 0.006)
    return norm(y)

def swish(dur=0.32, lo=800, hi=4000):
    n = int(dur * SR); t = np.arange(n) / SR
    y = bp(rng.randn(n), lo, hi) * np.sin(np.pi * t / dur) ** 2
    return norm(y)

def thunder(dur=2.4):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.randn(n)
    y = lp(x, 140, 4) * (np.minimum(1, t / 0.06) * np.exp(-t / 0.9)) * (1 + 0.4 * np.sin(2 * np.pi * 3.1 * t))
    y += 0.25 * lp(rng.randn(n), 600) * env(n, 0.004, 0.12)
    return norm(fades(y, 0.005, 0.4))

def tick(f=1700):
    n = int(0.05 * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t) * env(n, 0.0008, 0.010) + 0.2 * bp(rng.randn(n), 2000, 5000) * env(n, 0.0005, 0.004)
    return norm(lp(y, 5000))

def pluck(f=196.0, dur=1.6):
    """Karplus-Strong soft string"""
    n = int(dur * SR); L = int(SR / f)
    buf = lp(rng.randn(L), 2500); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % L]
        buf[i % L] = 0.996 * 0.5 * (buf[i % L] + buf[(i + 1) % L])
    return norm(fades(lp(out, 3000), 0.002, 0.3))

def chime(f=1318.5, dur=1.6):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.zeros(n)
    for m, a, d in ((1, 1.0, 0.6), (2.0, 0.25, 0.35), (2.76, 0.12, 0.25), (1.5, 0.2, 0.4)):
        y += a * np.sin(2 * np.pi * f * m * t) * np.exp(-t / d)
    y *= np.minimum(1, t / 0.003)
    y2 = np.zeros(n); o = int(0.09 * SR); y2[o:] = 0.6 * y[:n - o] * 0.8
    return norm(lp(y + y2, 6000))

def low_tone(f=110.0, dur=2.2):
    n = int(dur * SR); t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)) * np.minimum(1, t / 0.35) * np.exp(-t / 1.2)
    return norm(fades(y, 0.01, 0.5))

def pop():
    n = int(0.09 * SR); t = np.arange(n) / SR
    f = 520 * (170 / 520) ** (t / 0.09)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.03)
    return norm(y)

# ------------------------------------------------------------------ event list (time, sound, gain dB)
def events():
    ev = []
    ev.append((0.0, whoosh(0.7), -2))                                         # scene 1 accent at 0.0 s
    ev.append((0.05, rustle(SC_START[2] - 0.05), -8))                         # light dust rustle
    ev.append((SC_START[2] - 0.1, wind(SC_START[3] - SC_START[2] + 0.4, 180, 900, seed=2), -6))   # light wind
    ev.append((SC_START[3] - 0.1, wind(SC_START[4] - SC_START[3] + 0.3, 120, 600, 0.15, seed=3), -8))  # evening breeze
    # seed cracks at the crack moment of each eating cycle in scene 4 (hero + friend)
    for off in (0.0, 0.55):
        c = math.floor((SC_START[4] + off) / SC.EAT_P)
        while True:
            tc = c * SC.EAT_P - off + 0.52 * SC.EAT_P
            if tc >= SC_START[5] - 0.05: break
            if tc >= SC_START[4]:
                ev.append((tc, crack(), -6 if off == 0 else -9))
            c += 1
    # soft erase swish while the eraser passes (scene 5)
    for k in range(4):
        ev.append((SC_START[5] + 0.22 + k * 0.27, swish(0.26, 1200, 5000), -8))
    ev.append((SC_START[6], thunder(2.4), -1))                                 # soft low rumble on the lightning cut
    # counter ticks as the second pile grows
    t0 = word_t(7, 4)
    for k in range(1, 11):
        ev.append((t0 + 1.7 * (k - 0.5) / 10, tick(1500 + 40 * k), -10))
    ev.append((word_t(8, 4) + 0.2, pluck(), -3))                              # thread tightens
    ev.append((SC_START[9] + 0.2, wind(SC_START[10] - SC_START[9], 250, 1600, 0.45, seed=4), -2))  # wind gust
    ev.append((SC_START[10] + 0.05, chime(), -8))                             # coin chime
    w11 = wind(0.9, 180, 900, 0.1, seed=5); w11 *= np.linspace(1, 0, len(w11)) ** 1.5
    ev.append((SC_START[11], w11, -8))                                        # wind fades to silence
    ev.append((SC_START[11] + 0.7, low_tone(), -5))                           # one soft low tone
    ev.append((word_t(12, 6), pop(), -4))                                     # bubble pop on "Izohga"
    ev.append((word_t(13, 3) + 0.03, swish(0.34, 700, 3500), -4))             # paper swish on the throw
    ev.append((word_t(13, 5) + 0.6, swish(0.22, 900, 3500), -12))             # plane lands in his hand
    # timer ticks until the freeze
    t_app = SC_START[14] + 0.3
    k = 0
    while t_app + 0.25 * k < word_t(14, 3) - 0.01:
        ev.append((t_app + 0.25 * k, tick(2200 if k % 2 else 1900), -9)); k += 1
    return ev

def load_voice(path):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    v = np.frombuffer(pcm, np.float32).astype(np.float64)
    out = np.zeros(N); out[:min(N, len(v))] = v[:N]
    return out

def main(voice_path, out_wav, report_json=None):
    v = load_voice(voice_path)
    sfx = np.zeros(N)
    for (t, snd, g) in events():
        i = int(round(t * SR))
        if i >= N: continue
        m = min(len(snd), N - i)
        sfx[i:i + m] += snd[:m] * 10 ** (g / 20)
    # level: SFX bus sits 18 dB under the voice (RMS of speech vs RMS of active SFX)
    def rms(x): return np.sqrt(np.mean(x ** 2) + 1e-12)
    venv = np.sqrt(lp(v ** 2, 8) .clip(0))
    speech = venv > venv.max() * 0.08
    v_rms = rms(v[speech])
    act = np.abs(sfx) > 1e-4
    s_rms = rms(sfx[act])
    sfx *= (v_rms * 10 ** (-18 / 20)) / s_rms
    # duck under speech: up to -8 dB while the voice is talking (smoothed)
    duck_env = np.clip(venv / (venv.max() * 0.25), 0, 1)
    duck_env = sosfiltfilt(butter(1, 6, btype="low", fs=SR, output="sos"), duck_env)
    gain = 10 ** (-8 * np.clip(duck_env, 0, 1) / 20)
    sfx_d = sfx * gain
    mix = v + sfx_d
    pk = np.abs(mix).max()
    if pk > 0.97: mix *= 0.97 / pk
    st = np.stack([mix, mix], 1)
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())
    rep = {"voice_rms_dbfs": 20 * math.log10(v_rms), "sfx_rms_dbfs": 20 * math.log10(rms(sfx_d[act])),
           "sfx_under_voice_db": 20 * math.log10(v_rms / rms(sfx_d[act])),
           "sfx_peak_during_speech_dbfs": 20 * math.log10(np.abs(sfx_d[speech]).max() + 1e-12),
           "n_events": len(events()), "duration_s": N / SR}
    if report_json: json.dump(rep, open(report_json, "w"), indent=1)
    print(rep)

if __name__ == "__main__":
    main(*sys.argv[1:4])
