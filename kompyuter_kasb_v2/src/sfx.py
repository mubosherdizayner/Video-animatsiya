# Soft SFX synthesised in code, placed on key actions, ducked under the voice; output 48 kHz stereo wav.
import sys, json, wave
import numpy as np
from scipy.signal import butter, sosfilt
import scenes as SC

SR = 48000
rng = np.random.RandomState(11)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype="low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype="high", fs=SR, output="sos"), x)


def env(n, a, d, shape=1.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d) ** shape


def norm(x, peak=1.0):
    return x / (np.abs(x).max() + 1e-9) * peak


def tone(f, dur, partials=((1, 1.0),), decay=0.4, attack=0.004):
    n = int(dur * SR); t = np.arange(n) / SR
    y = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t / (decay / m ** 0.5)) for m, a in partials)
    return y * np.minimum(1, t / attack)


def accent():
    """soft mallet + warm bell: the hook / loop accent"""
    y = tone(196, 1.4, ((1, 1.0), (2, 0.35), (3.01, 0.12)), decay=0.55, attack=0.006)
    y += 0.45 * tone(587, 1.4, ((1, 1.0), (2.76, 0.2)), decay=0.35, attack=0.004)
    return norm(lp(y, 2400))


def wind(dur=0.8):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.randn(n)
    y = bp(x, 250, 1400) * np.sin(np.pi * t / dur) ** 2
    y = lp(y, 900 + 600 * 0)
    return norm(y)


def wood_click(f=1900):
    n = int(0.05 * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.006) + 0.6 * np.sin(2 * np.pi * f * 0.31 * t) * np.exp(-t / 0.012)
    y += 0.25 * bp(rng.randn(n), 1500, 5000) * np.exp(-t / 0.003)
    return norm(lp(y, 4500))


def rustle(dur=0.6):
    n = int(dur * SR); t = np.arange(n) / SR
    am = np.abs(lp(rng.randn(n), 30)); am = am / am.max()
    y = bp(rng.randn(n), 1800, 7000) * am * np.sin(np.pi * t / dur)
    return norm(y)


def flutter(dur=0.7):
    n = int(dur * SR); t = np.arange(n) / SR
    am = 0.5 + 0.5 * np.sin(2 * np.pi * 13 * t) ** 2
    y = bp(rng.randn(n), 300, 2200) * am * np.sin(np.pi * t / dur) ** 1.5
    return norm(y)


def rewind(dur=1.3):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.randn(n)
    out = np.zeros(n)
    blk = 960
    for s in range(0, n, blk):                       # band sweeps downwards while the level rises, then softly stops
        k = s / n
        fc = 2600 * (1 - k) + 350 * k
        seg = bp(x[max(0, s - 2000):s + blk], fc * 0.7, fc * 1.3)[-min(blk, n - s):]
        out[s:s + len(seg)] = seg
    y = out * (np.minimum(1, t / (dur * 0.7)) ** 1.5) * np.minimum(1, (dur - t) / 0.12)
    y += 0.3 * np.sin(2 * np.pi * (300 - 160 * t / dur) * t) * np.sin(np.pi * t / dur) ** 2
    return norm(lp(y, 3000))


def quill(dur=0.55):
    n = int(dur * SR); t = np.arange(n) / SR
    am = np.abs(np.sin(2 * np.pi * 7 * t)) ** 0.5 * (0.6 + 0.4 * np.abs(lp(rng.randn(n), 60)) / 0.05)
    am = np.clip(am, 0, 2)
    y = bp(rng.randn(n), 2500, 8000) * am * np.sin(np.pi * t / dur) ** 0.8
    return norm(y)


def bwom(dur=1.2):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 95 * (52 / 95) ** (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = (np.sin(ph) + 0.35 * np.sin(2 * ph)) * np.minimum(1, t / 0.03) * np.exp(-t / 0.45)
    return norm(lp(y, 700))


def relay():
    return norm(wood_click(2600) * 0.7 + 0.3 * np.pad(wood_click(1400), (0, 0)))


def plug():
    n = int(0.12 * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * 1150 * t) * np.exp(-t / 0.008) + 0.8 * np.sin(2 * np.pi * 160 * t) * np.exp(-t / 0.03)
    return norm(lp(y, 3500))


def chime():
    out = np.zeros(int(1.6 * SR))
    for k, f in enumerate((523.3, 659.3, 784.0, 1046.5)):
        b = tone(f, 1.2, ((1, 1.0), (2.0, 0.18), (3.0, 0.06)), decay=0.5)
        o = int(k * 0.12 * SR); out[o:o + len(b)] += b[:len(out) - o] * (0.8 + 0.1 * k)
    return norm(lp(out, 5000))


def whoosh(dur=0.7, up=False):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.randn(n); out = np.zeros(n); blk = 960
    for s in range(0, n, blk):
        k = s / n
        fc = (500 + 2200 * k) if up else (2200 - 1500 * k)
        seg = bp(x[max(0, s - 2000):s + blk], fc * 0.6, fc * 1.4)[-min(blk, n - s):]
        out[s:s + len(seg)] = seg
    return norm(out * np.sin(np.pi * t / dur) ** 2)


def thud():
    n = int(0.6 * SR); t = np.arange(n) / SR
    f = 120 * (55 / 120) ** (t / 0.6)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / 0.004) * np.exp(-t / 0.13)
    y += 0.2 * lp(rng.randn(n), 400) * np.exp(-t / 0.03)
    return norm(lp(y, 600))


def rumble(dur=2.0):
    n = int(dur * SR); t = np.arange(n) / SR
    y = lp(rng.randn(n), 140) * 6 + 0.5 * np.sin(2 * np.pi * 42 * t + 0.3 * np.sin(2 * np.pi * 0.7 * t))
    y *= np.sin(np.pi * t / dur) ** 1.2 * (0.8 + 0.2 * np.sin(2 * np.pi * 3.1 * t))
    return norm(lp(y, 220))


def pencil(dur=0.3):
    n = int(dur * SR); t = np.arange(n) / SR
    am = (0.5 + 0.5 * np.sin(2 * np.pi * 18 * t + 3 * np.sin(2 * np.pi * 4 * t))) ** 2
    y = bp(rng.randn(n), 2500, 6500) * am * np.sin(np.pi * t / dur) ** 0.7
    return norm(y)


def flutter_pages(dur=1.4, rate=11.0):
    out = np.zeros(int(dur * SR))
    k = 0
    while k / rate < dur - 0.08:
        b = rustle(0.07) * (0.7 + 0.3 * rng.rand()) * (1 - 0.6 * k / (rate * dur))
        o = int(k / rate * SR); out[o:o + len(b)] += b[:len(out) - o]; k += 1
    return norm(lp(out, 6000))


def book_thump():
    n = int(0.5 * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * np.cumsum(140 * (60 / 140) ** (t / 0.5)) / SR) * np.exp(-t / 0.09)
    y += 0.5 * bp(rng.randn(n), 400, 2500) * np.exp(-t / 0.025)
    return norm(lp(y, 1800))


def events():
    import scenes as SC
    s = SC.SC_START
    ev = [("accent", 0.0, accent(), 1.0),
          ("whoosh (turn)", 0.0, wind(0.9), 0.55),
          ("low rumble (layers sink / rise)", s[2] + 0.02, rumble(2.1), 0.75)]
    for j in range(6):
        ev.append(("pencil scratch", s[3] + 0.15 + j * 0.5 + 0.1 * rng.rand(), pencil(0.28 + 0.1 * rng.rand()), 0.4))
    ev.append(("paper rustle", s[3] + 0.42, rustle(0.8), 0.5))
    ev.append(("rewind whoosh", s[4] + 0.0, rewind(1.0), 0.75))
    ev.append(("page flutter", s[4] + 0.92, flutter_pages(1.45), 0.5))
    ev.append(("quill stroke", s[5] + 0.4, quill(1.45), 0.45))
    ev.append(("book thump", s[7] + 0.22, book_thump(), 0.9))
    ev.append(("bwom", s[7] + 0.22, bwom(1.1), 0.85))
    ev.append(("paper rustle", s[8] + 0.08, rustle(0.9), 0.45))
    for j in range(8):
        ev.append(("relay click", s[8] + 1.5 + j * 0.14 + 0.05 * rng.rand(), relay(), 0.33))
    for j in range(6):
        ev.append(("plug click", s[9] + SC.plug_time(j), plug(), 0.6))
    ev.append(("rising chime", s[10] + 0.02, chime(), 0.7))
    ev.append(("word whoosh", s[11] + 0.5, whoosh(0.9), 0.6))
    ev.append(("calm thud", s[11] + 1.55, thud(), 0.9))
    ev.append(("fyut swoosh", s[12] + SC.T_REL - 0.05, whoosh(0.4, up=True), 0.6))
    t_acc = (SC.LAST - int(round(SC.TURN13 * SC.FPS)) + 0.45 * SC.TURN13 * SC.FPS) / SC.FPS
    ev.append(("accent (loop)", t_acc, accent(), 1.0))
    return ev


def main(voice_wav, out_wav, out_json):
    import subprocess
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", voice_wav, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True).stdout
    v = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    n_out = int(round(SC.N_FRAMES / SC.FPS * SR))
    voice = np.zeros(n_out); voice[:min(len(v), n_out)] = v[:n_out]
    vpk = np.abs(voice).max()
    # speech activity -> ducking gain (6 dB under speech), smoothed
    blk = 480
    rms = np.sqrt(np.convolve(voice ** 2, np.ones(blk) / blk, mode="same"))
    act = (rms > vpk * 0.02).astype(float)
    act = np.convolve(act, np.ones(4800) / 4800, mode="same")
    duck = 1.0 - 0.5 * np.clip(act * 1.5, 0, 1)
    sfx = np.zeros(n_out)
    base = vpk * 10 ** (-18 / 20)                              # sfx peaks ~18 dB below the voice peak
    log = []
    for name, t0, y, g in events():
        i0 = int(t0 * SR)
        if i0 >= n_out: continue
        seg = y[:n_out - i0] * base * g
        sfx[i0:i0 + len(seg)] += seg
        log.append({"sfx": name, "t": round(t0, 3), "peak_db_vs_voice": round(20 * np.log10(base * g / vpk), 1)})
    sfx *= duck
    mixm = voice + sfx
    pk = np.abs(mixm).max()
    if pk > 0.97: mixm *= 0.97 / pk
    st = np.stack([mixm, mixm], 1)
    w = wave.open(out_wav, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()
    sfx_rms = np.sqrt(np.mean(sfx ** 2)) + 1e-12; v_rms = np.sqrt(np.mean(voice ** 2))
    json.dump({"events": log, "voice_to_sfx_rms_db": round(20 * np.log10(v_rms / sfx_rms), 1),
               "duration_s": n_out / SR}, open(out_json, "w"), indent=1)
    print("mix", out_wav, "voice/sfx rms dB", round(20 * np.log10(v_rms / sfx_rms), 1), "len", n_out / SR)


if __name__ == "__main__":
    main(*sys.argv[1:4])
