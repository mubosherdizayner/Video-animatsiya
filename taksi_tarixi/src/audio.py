# Synthesised SFX + 96 BPM muted-pluck tick-tock music bed, ducked under the voice-over. 48 kHz stereo.
import sys, json, math, wave
import numpy as np
from scipy.signal import butter, sosfilt
import scenes as SC

SR = 48000
rng = np.random.RandomState(7)


def lp(x, fc, order=2): return sosfilt(butter(order, fc, 'low', fs=SR, output='sos'), x)
def hp(x, fc, order=2): return sosfilt(butter(order, fc, 'high', fs=SR, output='sos'), x)
def bp(x, f1, f2, order=2): return sosfilt(butter(order, [f1, f2], 'band', fs=SR, output='sos'), x)
def tt(d): return np.arange(int(d * SR)) / SR
def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)
def norm(x): return x / (np.abs(x).max() + 1e-9)


def sweep_noise(dur, f0, f1, q=0.6):
    """noise through a band-pass whose centre sweeps f0->f1 (block-wise), soft sine envelope"""
    n = int(dur * SR); x = rng.randn(n); out = np.zeros(n); blk = 1024
    for i in range(0, n, blk):
        u = i / n; fc = f0 * (f1 / f0) ** u
        seg = x[max(0, i - 2048):i + blk]
        y = bp(seg, max(40, fc * (1 - q / 2)), min(SR / 2 - 100, fc * (1 + q / 2)))
        out[i:i + blk] = y[-len(out[i:i + blk]):]
    return out


def whoosh(dur=0.7, f0=300, f1=1800):
    y = sweep_noise(dur, f0, f1, 0.9)
    t = tt(dur); e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return norm(lp(y * e, 3500))


def flutter(dur=0.6):
    t = tt(dur); y = bp(rng.randn(len(t)), 350, 2200)
    am = 0.5 + 0.5 * np.sin(2 * np.pi * 13 * t) ** 2
    return norm(y * am * np.exp(-t / 0.28) * np.minimum(1, t / 0.02))


def pup(f0=520, f1=330, dur=0.11):
    t = tt(dur); f = f0 * (f1 / f0) ** (t / dur)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.003, 0.035)
    return norm(lp(y, 2500))


def rewind(dur=1.5):
    t = tt(dur)
    y = sweep_noise(dur, 2400, 260, 0.8)
    f = 900 * (140 / 900) ** (t / dur) * (1 + 0.05 * np.sin(2 * np.pi * 9 * t))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    return norm(lp((y + tone) * e, 3000))


def knock(f=900, dec=0.03, noise=0.25):
    t = tt(0.16)
    y = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.52 * t)) * env(len(t), 0.0015, dec)
    y += noise * lp(rng.randn(len(t)), 2500) * env(len(t), 0.0005, 0.006)
    return y


def clipclop():
    a = knock(780, 0.028); b = knock(560, 0.034)
    out = np.zeros(int(0.32 * SR)); out[:len(a)] += a; o = int(0.13 * SR); out[o:o + len(b)] += 0.85 * b
    return norm(lp(out, 2600))


def tup():
    t = tt(0.3)
    f = 190 * (110 / 190) ** (t / 0.3)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.002, 0.09)
    y += 0.35 * np.sin(2 * np.pi * 520 * t) * env(len(t), 0.001, 0.025)
    y += 0.15 * lp(rng.randn(len(t)), 1500) * env(len(t), 0.0005, 0.01)
    return norm(lp(y, 1800))


def wind(dur=1.9):
    t = tt(dur); y = lp(rng.randn(len(t)), 700, 2)
    y = y * (0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * t + 1)) * np.sin(np.pi * t / dur) ** 1.2
    return norm(hp(y, 90))


def chiq():
    out = np.zeros(int(0.22 * SR))
    for k, (o, f, a) in enumerate(((0.0, 2100, 1.0), (0.055, 1500, 0.7))):
        t = tt(0.06)
        y = a * (np.sin(2 * np.pi * f * t) * env(len(t), 0.0008, 0.012) + 0.4 * bp(rng.randn(len(t)), 1200, 4000) * env(len(t), 0.0005, 0.004))
        i = int(o * SR); out[i:i + len(y)] += y
    return norm(lp(out, 4200))


def tick(f=1650, dec=0.014):
    t = tt(0.06)
    y = np.sin(2 * np.pi * f * t) * env(len(t), 0.0008, dec) + 0.2 * lp(rng.randn(len(t)), 3000) * env(len(t), 0.0004, 0.003)
    return lp(y, 3800)


def ding(f=1318.5):
    t = tt(1.4)
    y = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t / (0.55 / m ** 0.7)) for m, a in ((1, 1), (2.01, 0.25), (3.0, 0.08)))
    return norm(lp(y * np.minimum(1, t / 0.004), 6000))


def klik():
    t = tt(0.12)
    y = np.sin(2 * np.pi * 1800 * t) * env(len(t), 0.0006, 0.009) + 0.8 * np.sin(2 * np.pi * 210 * t) * env(len(t), 0.002, 0.035)
    return norm(lp(y, 4000))


def shuv(dur=0.38):
    y = sweep_noise(dur, 900, 3200, 0.7)
    t = tt(dur); e = np.minimum(1, t / 0.05) * np.exp(-np.maximum(0, t - 0.05) / 0.12)
    return norm(lp(y * e, 4500))


def engine(dur):
    t = tt(dur); f = 52 + 22 * (t / dur) ** 1.5
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = sum(np.sin(k * ph) / k for k in range(1, 7))
    y = lp(y * (1 + 0.15 * np.sin(2 * np.pi * 17 * t)), 380) * (t / dur) ** 1.3
    return norm(y)


# ------------------------------------------------------------------ music
def pluck(f, dur=0.32, dec=0.13):
    t = tt(dur)
    y = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t / (dec / m)) for m, a in ((1, 1.0), (2, 0.32), (3, 0.1)))
    return y * np.minimum(1, t / 0.003)


def music(total):
    n = int(total * SR); L = np.zeros(n); R = np.zeros(n)
    bpm = 96; beat = 60 / bpm; bar = 4 * beat
    nt = lambda m: 440 * 2 ** ((m - 69) / 12)
    prog = [(53, (72, 69)), (50, (69, 65)), (46, (65, 62)), (48, (67, 64))]      # F, Dm, Bb, C : (bass, (tick, tock))
    pads = [(65, 69, 72, 76), (62, 65, 69, 72), (62, 65, 70, 74), (64, 67, 72, 76)]
    k = 0; t0 = 0.0
    while t0 < total:
        ci = int(t0 // bar) % 4
        bass, (tk, tc) = prog[ci]
        # 8th-note tick-tock (muted plucks), alternate left/right
        for j in range(8):
            ts = t0 + j * beat / 2
            if ts >= total: break
            note = tk if j % 2 == 0 else tc
            amp = 0.55 if j % 2 == 0 else 0.42
            y = lp(pluck(nt(note), 0.3, 0.09 if j % 2 else 0.11), 1700) * amp
            i = int(ts * SR); m = min(len(y), n - i)
            pan = 0.35 if j % 2 == 0 else -0.35
            L[i:i + m] += y[:m] * (1 - pan) * 0.5; R[i:i + m] += y[:m] * (1 + pan) * 0.5
        # warm bass on beats 1 and 3
        for j in (0, 2):
            ts = t0 + j * beat
            if ts >= total: break
            tb = tt(1.2)
            yb = lp(np.sin(2 * np.pi * nt(bass - 12) * tb) + 0.3 * np.sin(4 * np.pi * nt(bass - 12) * tb), 300) * env(len(tb), 0.01, 0.55) * 0.9
            i = int(ts * SR); m = min(len(yb), n - i); L[i:i + m] += yb[:m] * 0.5; R[i:i + m] += yb[:m] * 0.5
        # soft pad across the bar
        tb = tt(bar + 0.4)
        pad = sum(np.sin(2 * np.pi * nt(p) * tb * (1 + d)) for p in pads[ci] for d in (-0.002, 0.002))
        pad = lp(pad, 1200) * np.minimum(1, tb / 0.35) * np.minimum(1, np.maximum(0, (bar + 0.4 - tb) / 0.4)) * 0.05
        i = int(t0 * SR); m = min(len(pad), n - i); L[i:i + m] += pad[:m] * 0.5; R[i:i + m] += pad[:m] * 0.5
        t0 += bar
    return np.stack([L, R], 1)


def place(buf, y, t, gain, pan=0.0):
    i = int(t * SR)
    if i >= len(buf): return
    m = min(len(y), len(buf) - i)
    buf[i:i + m, 0] += y[:m] * gain * (1 - pan) ** 0.5
    buf[i:i + m, 1] += y[:m] * gain * (1 + pan) ** 0.5


def rms_db(x): return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


def main(vo_wav, out_wav):
    w = wave.open(vo_wav); assert w.getframerate() == SR
    vo = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    total = len(vo) / SR
    # voice activity envelope for ducking
    a = np.abs(vo); e = np.zeros_like(a); s = 0.0
    at, rl = math.exp(-1 / (0.01 * SR)), math.exp(-1 / (0.3 * SR))
    blk = lp(a, 30, 1)
    pres = np.clip((20 * np.log10(np.abs(blk) + 1e-6) + 46) / 14, 0, 1)
    # smooth presence (attack fast, release slow) - block-wise for speed
    hop = 240; pr = pres[::hop].copy()
    for i in range(1, len(pr)):
        pr[i] = max(pr[i], pr[i - 1] * 0.93)
    pres = np.interp(np.arange(len(vo)), np.arange(len(pr)) * hop, pr)
    speech = vo[pres > 0.6]
    v_db = rms_db(speech)
    print("voice speech rms dB", round(v_db, 1))

    sfx = np.zeros((len(vo), 2))
    def S(y, t, rel_db=-17.0, pan=0.0):
        act = y[np.abs(y) > 0.05 * np.abs(y).max()]
        g = 10 ** ((v_db + rel_db - rms_db(act)) / 20)
        place(sfx, y, t, g, pan)
    wt = SC.wt; st = SC.SC_START
    S(whoosh(0.55, 500, 2200), 0.0, -19)                                    # hook accent at 0.0
    S(whoosh(0.8, 320, 2000), st[2] - 0.02, -18, 0.2)                       # sign flies off
    S(flutter(0.7), st[2] + 0.03, -21, -0.3)                                 # pigeons scatter
    for k in ('birinchi', 'savol', 'qancha'): S(pup(), wt(3, k), -18, -0.2 if k != 'savol' else 0.2)
    S(rewind(st[5] - st[4] + 0.1), st[4] - 0.05, -18)
    for t_ in (8.95, 9.30, 9.62, 10.55): S(clipclop(), t_, -20, 0.25)
    S(tup(), wt(6, 'quti'), -15)
    S(wind(st[8] - st[7]), st[7], -22)
    S(chiq(), wt(8, 'taksometrni'), -17, 0.15)
    tk = st[9]
    while tk < st[10]: S(tick(1650 if int(round((tk - st[9]) / 0.25)) % 2 == 0 else 1250), tk, -21, 0.15); tk += 0.25
    tk = st[10]; per = 0.22
    while tk < st[11]: S(tick(1650 if int(tk * 100) % 2 else 1300), tk, -20, 0.15); tk += per; per = max(0.07, per * 0.9)
    t_merge = SC.fr([w for w in SC.WORDS if w['scene'] == 11][-1]['end']) / SC.FPS
    S(ding(), t_merge, -19)
    S(whoosh(0.32, 1800, 600), st[12] - 0.3, -21)
    S(klik(), st[12], -16)
    S(shuv(), wt(13, 'yuboring'), -17, 0.3)
    S(pup(560, 360), wt(14, 'savdolashasizmi'), -18, 0.2); S(pup(600, 400), wt(14, 'hisoblagich'), -18, 0.2)
    S(engine(total - st[15]), st[15], -20)

    mus = music(total)
    m_db = rms_db(mus[int(2 * SR):int(30 * SR)].mean(1))
    mus *= 10 ** ((v_db - 25 - m_db) / 20)
    # short silence before the box lands (scene 6), then back
    tq = wt(6, 'quti'); t6 = st[6]
    tgrid = np.arange(len(vo)) / SR
    dip = 1 - 0.88 * np.clip((tgrid - t6) / 0.25, 0, 1) * (tgrid < tq) - 0.88 * (tgrid >= tq) * np.clip(1 - (tgrid - tq) / 0.6, 0, 1)
    duck_m = 1 - 0.5 * pres                      # about -6 dB more under speech
    duck_s = 1 - 0.3 * pres
    mix = np.stack([vo, vo], 1) + sfx * duck_s[:, None] + mus * (duck_m * dip)[:, None]
    pk = np.abs(mix).max()
    print("peak", round(20 * np.log10(pk), 2), "sfx rms", round(rms_db(sfx[np.abs(sfx).max(1) > 1e-4].mean(1)), 1),
          "music rms", round(rms_db(mus.mean(1)), 1))
    if pk > 0.97: mix *= 0.97 / pk
    out = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    ww = wave.open(out_wav, 'w'); ww.setnchannels(2); ww.setsampwidth(2); ww.setframerate(SR); ww.writeframes(out.tobytes()); ww.close()
    # stems for QA
    np.save(out_wav.replace('.wav', '_stems.npy'), np.stack([vo, (sfx * duck_s[:, None]).mean(1), (mus * (duck_m * dip)[:, None]).mean(1)]).astype(np.float32))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
