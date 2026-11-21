# Synthesized sound effects (no downloads) + voice mix with ducking -> mix.wav
import sys, subprocess, json
import numpy as np
from scipy import signal
import timing as T
from timing import cue

SR = 44100
rng = np.random.default_rng(7)


def env_ad(n, a, d):
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)
    return e


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="high", fs=SR, output="sos"), x)


def norm(x):
    return x / (np.max(np.abs(x)) + 1e-9)


def whoosh(dur=0.25):
    n = int(dur * SR)
    noise = rng.normal(0, 1, n)
    # sweep: crossfade through 4 bands low -> high
    bands = [(250, 600), (500, 1200), (900, 2200), (1600, 3600)]
    out = np.zeros(n)
    pos = np.linspace(0, len(bands) - 1, n)
    for k, (lo, hi) in enumerate(bands):
        w = np.clip(1 - np.abs(pos - k), 0, 1)
        out += bp(noise, lo, hi) * w
    e = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
    return norm(out * e)


def tink():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1500 * t) + 0.25 * np.sin(2 * np.pi * 3000 * t)
    return norm(x * env_ad(n, 0.002, 0.07))


def pop():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    f = 900 * np.exp(-t / 0.04) + 220
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * env_ad(n, 0.003, 0.04)
    return norm(x)


def tuk():
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 190 * t) * env_ad(n, 0.001, 0.03) + 0.5 * np.sin(2 * np.pi * 430 * t) * env_ad(n, 0.001, 0.015)
    x += 0.3 * lp(rng.normal(0, 1, n), 1500) * env_ad(n, 0.0005, 0.006)
    return norm(x)


def creak(dur=0.5, rate=38.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    wob = rate * (1 + 0.35 * np.sin(2 * np.pi * 2.2 * t) + 0.15 * np.sin(2 * np.pi * 5.3 * t))
    ph = np.cumsum(wob) / SR
    pulses = (np.sin(2 * np.pi * ph) > 0.92).astype(float)
    noise = lp(rng.normal(0, 1, n), 900)
    x = lp(pulses * 1.0 + 0.25 * noise, 700)
    e = np.sin(np.pi * np.linspace(0, 1, n)) ** 0.8
    return norm(x * e)


def thud():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 80 * np.exp(-t / 0.2) + 45
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.003, 0.12)
    x += 0.35 * lp(rng.normal(0, 1, n), 300) * env_ad(n, 0.001, 0.05)
    return norm(x)


def pshh():
    n = int(0.45 * SR)
    x = hp(lp(rng.normal(0, 1, n), 6000), 1400)
    e = env_ad(n, 0.05, 0.14)
    return norm(x * e)


def heartbeat():
    n = int(0.7 * SR)
    out = np.zeros(n)
    for off, g in ((0.0, 1.0), (0.26, 0.75)):
        m = int(0.25 * SR)
        t = np.arange(m) / SR
        x = np.sin(2 * np.pi * (60 * np.exp(-t / 0.3) + 8) * t) * env_ad(m, 0.004, 0.08) * g
        k = int(off * SR)
        out[k:k + m] += x
    return norm(out)


def ding():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1320 * t) + 0.35 * np.sin(2 * np.pi * 2640 * t)
    return norm(x * env_ad(n, 0.004, 0.6 / 3))  # ~600 ms audible decay


def tick():
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 2800 * t) * 0.6 + np.sin(2 * np.pi * 1200 * t)) * env_ad(n, 0.0005, 0.006)
    return norm(x)


# relative level (dB vs. the -18 dB base) to compensate perceived loudness
EVENTS = None


def events():
    f_w = int(round(cue(8, "Isboti") * 30)) + 3
    return [
        ("whoosh", 0.0, whoosh(), 0),
        ("tink", cue(1, "To'xtang!"), tink(), -2),
        ("creak", T.scene_start(2) + 0.05, creak(0.55, 34), 0),
        ("pop", cue(3, "sug'urgan"), pop(), 0),
        ("tuk", cue(4, "suyak"), tuk(), 2),
        ("tuk", cue(4, "yaralarni"), tuk(), 2),
        ("thud", cue(5, "ko'rmagan"), thud(), 4),
        ("pshh", cue(6, "Bugun"), pshh(), -2),
        ("heartbeat", cue(7, "qon"), heartbeat(), 5),
        ("whoosh", f_w / 30, whoosh(), 0),
        ("ding", cue(9, "Qizil"), ding(), -3),
        ("ding", cue(9, "Oq"), ding(), -3),
        ("creak", cue(10, "qisgan"), creak(0.45, 46), 0),
        ("pop", cue(11, "Buni"), pop(), 0),
        ("tick", cue(12, "«o'tiring»"), tick(), -2),
        ("tick", cue(12, "desa..."), tick(), -2),
    ]


def load_voice():
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", T.AUDIO, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.float32).astype(np.float64)


def main(out_wav, out_json):
    voice = load_voice()
    n_total = int(round(T.N_FRAMES / 30 * SR))
    v = np.zeros(n_total)
    v[:min(len(voice), n_total)] = voice[:n_total]
    vpk = np.max(np.abs(v))
    sfx = np.zeros(n_total)
    log = []
    for name, t0, x, rel in events():
        g = vpk * 10 ** ((-18 + rel) / 20)
        k = int(round(t0 * SR))
        m = min(len(x), n_total - k)
        sfx[k:k + m] += x[:m] * g
        log.append(dict(name=name, t=round(t0, 3), level_db=-18 + rel))
    # ducking: extra -6 dB on sfx while the voice is active
    win = int(0.05 * SR)
    venv = np.sqrt(np.convolve(v ** 2, np.ones(win) / win, mode="same"))
    active = venv > vpk * 0.03
    duck = np.where(active, 10 ** (-6 / 20), 1.0)
    duck = np.convolve(duck, np.ones(win) / win, mode="same")
    sfx_d = sfx * duck
    mix = v + sfx_d
    pk = np.max(np.abs(mix))
    if pk > 0.98:
        mix *= 0.98 / pk
    import wave
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    # stats for QA: voice vs sfx energy inside speech
    sp = active
    v_rms = np.sqrt(np.mean(v[sp] ** 2))
    s_rms = np.sqrt(np.mean(sfx_d[sp] ** 2)) + 1e-12
    s_pk_db = 20 * np.log10(np.max(np.abs(sfx_d)) / vpk + 1e-12)
    stats = dict(events=log, voice_over_sfx_db_in_speech=round(20 * np.log10(v_rms / s_rms), 1),
                 sfx_peak_vs_voice_peak_db=round(s_pk_db, 1), mix_seconds=round(n_total / SR, 4))
    json.dump(stats, open(out_json, "w"), indent=1)
    print(json.dumps({k: v for k, v in stats.items() if k != "events"}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
