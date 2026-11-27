"""Synthesise the soft sound effects in code, duck them under the voice and write the final mix.
Usage: python sfx.py WORK_DIR VOICE_FILE OUT_WAV"""
import json, math, subprocess, sys
import numpy as np
from scipy.signal import butter, sosfilt, lfilter
from scipy.ndimage import uniform_filter1d

SR = 48000
work, voice_path, out_wav = sys.argv[1:4]
TM = json.load(open(f"{work}/timing.json"))
W = TM["words"]; NF = TM["nframes"]; FPS = TM["fps"]
def wd(si, i): return [w for w in W if w["sent"] == si][i]
rng = np.random.default_rng(7)

def tvec(d): return np.arange(int(d * SR)) / SR
def dec(t, tau): return np.exp(-t / tau)
def att(t, a): return np.clip(t / a, 0, 1)
def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)
def lp(x, fc, order=2): return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x)
def norm(x): return x / (np.abs(x).max() + 1e-9)

def s_accent():
    t = tvec(0.9)
    x = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((523.25, 1), (659.25, .7), (783.99, .5), (1046.5, .18)))
    x = x * dec(t, 0.28) * att(t, 0.006) + 0.6 * np.sin(2 * np.pi * 110 * t) * dec(t, 0.05) * att(t, 0.004)
    return norm(x)
def s_knock():
    t = tvec(0.25)
    x = (np.sin(2 * np.pi * 1250 * t) * dec(t, 0.018) + .6 * np.sin(2 * np.pi * 2450 * t) * dec(t, 0.010)
         + .8 * np.sin(2 * np.pi * 520 * t) * dec(t, 0.035))
    x = x * att(t, 0.0015) + 0.3 * bp(rng.standard_normal(len(t)), 2000, 8000) * dec(t, 0.002)
    return norm(x)
def s_thud():
    t = tvec(0.45); f = 60 + 40 * np.exp(-t / 0.05)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * dec(t, 0.12) * att(t, 0.003)
    x += 0.5 * lp(rng.standard_normal(len(t)), 700) * dec(t, 0.025) + 0.15 * bp(rng.standard_normal(len(t)), 1000, 3000) * dec(t, 0.012)
    return norm(x)
def s_whoosh(d=0.55):
    t = tvec(d); n = rng.standard_normal(len(t)); y = np.zeros_like(n); zi = None; blk = 256
    for i in range(0, len(n), blk):
        u = i / len(n); fc = 500 + 1700 * math.sin(math.pi * min(1, u * 1.25)) ** 1.5
        b, a = butter(2, [fc * 0.7, fc * 1.35], "band", fs=SR)
        if zi is None: zi = np.zeros(max(len(a), len(b)) - 1)
        y[i:i + blk], zi = lfilter(b, a, n[i:i + blk], zi=zi)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.6
    return norm(y * env)
def s_tick():
    t = tvec(0.04)
    return norm((np.sin(2 * np.pi * 3200 * t) + .3 * np.sin(2 * np.pi * 6400 * t)) * dec(t, 0.006) * att(t, 0.0008))
def s_bell():
    t = tvec(1.8)
    x = sum(a * np.sin(2 * np.pi * 1046.5 * r * t) * dec(t, d) for r, a, d in ((1, 1, 1.0), (2.0, .35, .6), (2.76, .25, .45), (4.07, .1, .3)))
    return norm(x * att(t, 0.004))
def s_boop():
    t = tvec(0.2); f = 340 + 220 * np.exp(-t / 0.05)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return norm((np.sin(ph) + .2 * np.sin(2 * ph)) * np.sin(np.pi * np.clip(t / 0.2, 0, 1)) ** 0.7)
def s_clap():
    t = tvec(0.15); n = rng.standard_normal(len(t))
    x = bp(n, 1200, 5000) * dec(t, 0.010) + .7 * np.sin(2 * np.pi * 1900 * t) * dec(t, 0.022) + .6 * np.sin(2 * np.pi * 950 * t) * dec(t, 0.035)
    return norm(x * att(t, 0.001))
def s_wood():
    t = tvec(0.12)
    return norm((np.sin(2 * np.pi * 1700 * t) * dec(t, 0.03) + .5 * np.sin(2 * np.pi * 2900 * t) * dec(t, 0.015)) * att(t, 0.001))
def s_tap():
    t = tvec(0.15)
    x = np.sin(2 * np.pi * 420 * t) * dec(t, 0.045) + .5 * np.sin(2 * np.pi * 1250 * t) * dec(t, 0.02)
    x = x * att(t, 0.002) + 0.2 * bp(rng.standard_normal(len(t)), 2000, 6000) * dec(t, 0.003)
    return norm(x)
def s_boing():
    t = tvec(0.65); f = 210 * (1 + 0.45 * np.exp(-5 * t) * np.sin(2 * np.pi * 10 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return norm((np.sin(ph) + .25 * np.sin(2 * ph)) * dec(t, 0.22) * att(t, 0.005))

# ------------------------------------------------------------------ voice
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", voice_path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
voice = np.frombuffer(raw, np.float32).astype(np.float64)
N = int(round(NF / FPS * SR)); voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]
vpk = np.abs(voice).max()
sfx = np.zeros(N)
EVENTS = []
def add(x, t0, db, name):
    i = int(round(t0 * SR)); x = x * vpk * 10 ** (db / 20)
    j = min(N, i + len(x)); sfx[i:j] += x[: j - i]; EVENTS.append((name, round(t0, 3), db))

add(s_accent(), 0.0, -16, "accent")
# swipe rustle while the feed scrolls (follows the scroll speed)
stop = wd(0, 5)["end"]; t = np.arange(int(stop * SR)) / SR
spd = (1 - t / stop) ** 1.5
rust = bp(rng.standard_normal(len(t)), 2200, 7000) * spd * (0.75 + 0.25 * np.sin(2 * np.pi * 13 * t + 2 * np.sin(2 * np.pi * 3 * t)))
add(norm(rust) * 0.5, 0.0, -22, "rustle")
tk = wd(1, 0)["start"]; add(s_knock(), tk, -15, "knock1"); add(s_knock(), tk + 0.2, -16, "knock2")
add(s_thud(), wd(2, 4)["start"], -23, "stamp")
add(s_whoosh(), wd(3, 6)["start"] - 0.03, -16, "whoosh")
t0, te = wd(4, 0)["start"], wd(4, 3)["end"]; last = 0
for ms in range(int((te - t0) * 1000) + 1):
    u = ms / 1000 / (te - t0); n = int(round(250 * (1 - (1 - u) ** 2.2)))
    if n // 25 > last: last = n // 25; add(s_tick(), t0 + ms / 1000, -23, "tick")
add(s_bell(), te, -26, "bell")
add(s_boop(), wd(6, 2)["start"], -20, "boop")
add(s_clap(), wd(7, 4)["start"], -16, "clapper")
add(s_wood(), wd(8, 0)["start"], -18, "switchA"); add(s_wood(), wd(8, 2)["start"], -18, "switchB")
add(s_tap(), wd(9, 0)["start"], -16, "tap")
add(s_boing(), wd(10, 1)["start"], -20, "boing")

# ducking: sfx -6 dB while the voice is active
env = np.sqrt(uniform_filter1d(voice ** 2, int(0.02 * SR)))
ref = np.percentile(env[env > 1e-4], 90)
act = np.clip(env / (0.25 * ref), 0, 1)
k_up, k_dn = math.exp(-1 / (0.01 * SR)), math.exp(-1 / (0.25 * SR))
g = np.empty_like(act); s = 0.0
for i, a in enumerate(act):
    s = a + (s - a) * (k_up if a > s else k_dn); g[i] = s
duck = 1 - 0.5 * g
mix = voice + sfx * duck
pk = np.abs(mix).max()
if pk > 0.99: mix *= 0.99 / pk
pre = f"{work}/mix_pre.wav"
import wave
with wave.open(pre, "wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
# loudness: two-pass loudnorm to -14 LUFS / -1.5 dBTP (linear, keeps the voice/sfx balance)
m = subprocess.run(["ffmpeg", "-hide_banner", "-i", pre, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                   capture_output=True, text=True).stderr
js = json.loads(m[m.rindex("{"): m.rindex("}") + 1])
# loudness: gain towards -15 LUFS, transparent look-ahead limiter at -1.5 dBFS, exact length kept
gain_db = -15.0 - float(js["input_i"])
tmp = f"{work}/mix_lim.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af",
                f"volume={gain_db:.2f}dB,alimiter=limit=0.84:attack=5:release=80:level=disabled", "-ar", str(SR), tmp], check=True)
with wave.open(tmp, "rb") as rf:
    lim = np.frombuffer(rf.readframes(rf.getnframes()), np.int16)
lim = np.pad(lim, (0, max(0, N - len(lim))))[:N]
with wave.open(out_wav, "wb") as wf:
    wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(np.repeat(lim, 2).tobytes())
print("gain dB", round(gain_db, 2), "input LUFS", js["input_i"])
# stats for QA
win = int(0.05 * SR)
def rms_db(x): return 20 * math.log10(math.sqrt(np.mean(x ** 2)) + 1e-12)
rep = []
for name, t0, db in EVENTS:
    if name == "tick": continue
    i = int(t0 * SR); a, b = max(0, i - win), min(N, i + 6 * win)
    rep.append((name, t0, round(rms_db(voice[a:b]) - rms_db((sfx * duck)[a:b]), 1)))
json.dump(dict(events=EVENTS, voice_minus_sfx_db=rep, loudnorm_in=js, gain_db=gain_db), open(f"{work}/sfx_report.json", "w"), indent=1)
print("voice - sfx (dB RMS around each event):", rep)
