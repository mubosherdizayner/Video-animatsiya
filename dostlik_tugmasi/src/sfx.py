# Soft synthesized SFX (no downloads) for the key actions of each scene, mixed well below the voice
# (event peaks about -18 dB under the voice peak, ticks lower) and ducked a further 6 dB under speech.
import sys, math, wave, subprocess, json
import numpy as np
from scipy.signal import butter, sosfilt
import scenes as SC
from scenes import SC_START, wtt, timer_steps, T13

SR = 48000
rng = np.random.default_rng(7)

def env(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)
def lp(x, fc, order=2): return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x)
def hp(x, fc, order=2): return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)
def bp(x, f0, f1, order=2): return sosfilt(butter(order, [f0, f1], "band", fs=SR, output="sos"), x)
def norm(x, peak=1.0): return x / (np.abs(x).max() + 1e-9) * peak
def sweep(f0, f1, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)

def boom():
    d = 1.6; x = sweep(70, 38, d) * env(int(d * SR), 0.01, 0.45)
    x += 0.25 * lp(rng.normal(0, 1, int(d * SR)), 180) * env(int(d * SR), 0.005, 0.25)
    return norm(lp(x, 400))
def tick(f=1900, d=0.05):
    n = int(d * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) * env(n, 0.001, 0.008) + 0.5 * np.sin(2 * np.pi * f * 0.5 * t) * env(n, 0.001, 0.012)
    return norm(lp(x, 3500))
def bell(f, d=0.7, decay=0.25):
    n = int(d * SR); t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t / (decay / (1 + 0.7 * (m - 1)))) for m, a in ((1, 1), (2.76, 0.3), (5.4, 0.1)))
    return x * np.minimum(1, t / 0.003)
def jingle():
    out = np.zeros(int(0.6 * SR))
    for k in range(4):
        b = bell(rng.uniform(2400, 3600), 0.5, 0.12) * rng.uniform(0.5, 1.0)
        o = int(rng.uniform(0, 0.09) * SR); out[o:o + len(b)] += b[:len(out) - o]
    return norm(lp(out, 6000))
def pop():
    d = 0.09; return norm(sweep(700, 220, d) * env(int(d * SR), 0.002, 0.03))
def heartbeat():
    out = np.zeros(int(0.7 * SR))
    for o, a in ((0.0, 1.0), (0.24, 0.7)):
        d = 0.18; x = sweep(75, 45, d) * env(int(d * SR), 0.004, 0.05) * a
        i = int(o * SR); out[i:i + len(x)] += x
    return norm(lp(out, 250))
def click():
    d = 0.06; n = int(d * SR)
    x = hp(rng.normal(0, 1, n), 1200) * env(n, 0.0005, 0.006) + 0.6 * np.sin(2 * np.pi * 900 * np.arange(n) / SR) * env(n, 0.001, 0.01)
    return norm(lp(x, 5000))
def whoosh(d=0.35, f_lo=300, f_hi=2600, rise=False):
    n = int(d * SR); t = np.arange(n) / SR
    x = rng.normal(0, 1, n)
    shape = np.sin(np.pi * t / d) ** 2 if not rise else (t / d) ** 2 * np.exp(-((t / d) - 1) ** 2 * 0) * np.minimum(1, (d - t) / 0.06)
    y = bp(x, f_lo, f_hi) * shape
    return norm(y)
def dissolve(d=1.4):
    n = int(d * SR); t = np.arange(n) / SR
    y = bp(rng.normal(0, 1, n), 900, 5000) * np.sin(np.pi * t / d) ** 1.5
    sparkle = np.zeros(n)
    for k in range(18):
        b = bell(rng.uniform(2500, 4500), 0.25, 0.05) * rng.uniform(0.1, 0.3)
        o = int(rng.uniform(0, d - 0.25) * SR); sparkle[o:o + len(b)] += b
    return norm(y * 0.8 + sparkle)
def thud():
    d = 0.5; x = sweep(110, 50, d) * env(int(d * SR), 0.003, 0.09)
    x += 0.4 * lp(rng.normal(0, 1, int(d * SR)), 600) * env(int(d * SR), 0.001, 0.03)
    return norm(lp(x, 900))
def blip_cut():
    t1 = np.arange(int(0.09 * SR)) / SR
    a = np.sin(2 * np.pi * 1320 * t1) * env(len(t1), 0.003, 0.06)
    t2 = np.arange(int(0.05 * SR)) / SR
    b = np.sin(2 * np.pi * 1760 * t2) * env(len(t2), 0.003, 0.2)
    b *= np.minimum(1, (len(t2) - np.arange(len(t2))) / (0.004 * SR))     # abrupt cut-off
    return norm(np.concatenate([a, np.zeros(int(0.03 * SR)), b]))
def crowd(d):
    n = int(d * SR); t = np.arange(n) / SR
    x = lp(rng.normal(0, 1, n), 500, 4)
    murmur = 0.6 + 0.4 * lp(np.abs(rng.normal(0, 1, n)), 4)
    murmur = murmur / murmur.max()
    y = x * murmur
    # muffled doira
    for k in np.arange(0.1, d, 0.36):
        dd = 0.14; ii = int(k * SR)
        hit = sweep(130, 80, dd) * env(int(dd * SR), 0.002, 0.04) * (1.0 if int(k / 0.36) % 3 == 0 else 0.55)
        y[ii:ii + len(hit)] += 1.6 * hit[:max(0, n - ii)] * np.std(y) * 3
    fade = np.clip(1 - (t / d) ** 1.4, 0, 1) * np.minimum(1, t / 0.15)
    return norm(lp(y, 700) * fade)
def shh():
    d = 0.6; n = int(d * SR); t = np.arange(n) / SR
    return norm(bp(rng.normal(0, 1, n), 2500, 6500) * np.sin(np.pi * t / d) ** 2)
def padlock():
    out = np.zeros(int(0.25 * SR))
    for o, f in ((0.0, 1500), (0.07, 2100)):
        c = click(); i = int(o * SR); out[i:i + len(c)] += c * (1 if f == 1500 else 0.7)
    return norm(out)
def tap():
    d = 0.08; n = int(d * SR)
    x = sweep(380, 160, d) * env(n, 0.001, 0.02) + 0.3 * lp(rng.normal(0, 1, n), 2000) * env(n, 0.0005, 0.004)
    return norm(x)

def events():
    E = []   # (time, sound, gain_dB relative to the voice peak)
    E.append((0.0, boom(), -18))
    # clock ticks on each timer step; in scene 12 the ticking speeds up instead
    for s in timer_steps():
        if s < SC_START[12] - 0.05: E.append((s, tick(), -27))
    t = SC_START[12]; iv = 0.5
    while t < SC_START[13] - 0.04:
        E.append((t, tick(2000 + 200 * (0.5 - iv)), -26)); t += iv; iv = max(0.12, iv * 0.82)
    E.append((T13, tick(1700), -24))
    for o in (0.15, 0.45, 0.8, 1.15, 1.45): E.append((SC_START[2] + o, jingle(), -22))
    E.append((wtt(3, "sen"), pop(), -20))
    E.append((SC_START[4] + 0.05, heartbeat(), -18)); E.append((SC_START[4] + 0.85, heartbeat(), -19))
    t_press = SC_START[5] + 0.16
    E.append((t_press, click(), -18)); E.append((t_press + 0.3, dissolve(1.5), -22))
    E.append((SC_START[6] + 0.12, thud(), -18))
    E.append((wtt(7, "yo"), whoosh(0.28), -21)); E.append((wtt(8, "yo"), whoosh(0.28), -21))
    E.append((SC_START[9] + 0.15, tick(1500), -22)); E.append((SC_START[9] + 0.65, tick(1500), -22))
    E.append((SC_START[10] + 0.02, blip_cut(), -21))
    d11 = SC_START[12] - 0.35 - SC_START[11]
    E.append((SC_START[11], crowd(d11), -24))
    E.append((SC_START[13] + 0.15, shh(), -26))
    E.append((wtt(14, "yubor"), whoosh(0.45, 400, 3000), -20))
    E.append((wtt(15, "aniq") - 0.45, whoosh(0.6, 250, 2200, rise=True), -23))
    E.append((wtt(15, "repost"), pop(), -19))
    E.append((SC_START[16] + 0.02, padlock(), -20))
    E.append((SC_START[17] + 0.16, tap(), -19))
    return E

def main(voice_src, out_wav, report=None):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", voice_src, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    voice = np.frombuffer(raw, np.float32).astype(np.float64)
    n = len(voice)
    vpeak = np.abs(voice).max()
    sfx = np.zeros(n + SR * 2)
    log = []
    for t, snd, gdb in events():
        i = int(round(t * SR)); g = vpeak * 10 ** (gdb / 20)
        sfx[i:i + len(snd)] += snd * g
        log.append({"t": round(t, 3), "gain_db": gdb, "dur": round(len(snd) / SR, 3)})
    sfx = sfx[:n]
    # duck under speech: voice envelope (10 ms attack, 180 ms release)
    a = np.abs(voice); env_v = np.zeros(n); e = 0.0
    att, rel = math.exp(-1 / (0.010 * SR)), math.exp(-1 / (0.180 * SR))
    blk = 48
    for k in range(0, n, blk):
        v = a[k:k + blk].max()
        c = att if v > e else rel
        e = c ** blk * e + (1 - c ** blk) * v
        env_v[k:k + blk] = e
    speaking = np.clip((20 * np.log10(env_v / vpeak + 1e-9) + 36) / 10, 0, 1)
    duck = 10 ** (-6 * speaking / 20)
    sfx *= duck
    mix = voice + sfx
    peak = np.abs(mix).max()
    if peak > 0.97: mix *= 0.97 / peak
    st = np.repeat((mix * 32767).astype(np.int16)[:, None], 2, axis=1)
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
    # levels for QA
    def rms_db(x): return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
    vr = rms_db(voice[np.abs(voice) > vpeak * 0.02]); sr_ = rms_db(sfx[np.abs(sfx) > 1e-5])
    sp = 20 * np.log10(np.abs(sfx).max() / vpeak)
    info = {"voice_rms_db": round(vr, 1), "sfx_rms_db": round(sr_, 1), "sfx_peak_rel_voice_peak_db": round(sp, 1),
            "voice_minus_sfx_rms_db": round(vr - sr_, 1), "events": log, "samples": n}
    if report: json.dump(info, open(report, "w"), indent=1)
    print({k: v for k, v in info.items() if k != "events"})

if __name__ == "__main__":
    main(*sys.argv[1:4])
