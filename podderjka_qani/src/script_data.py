# Script lines (subtitle source) and the timing built from them.
# No vocal track is used for this video: word times come from the text itself — each scene gets a sung-length
# slot, and words inside it are spread by syllable count (+ a short breath after commas), snapped to frames.
import json, os, re
from common import FPS, BUILD

LINES = [
    "Akajon, podderjka qani?",
    "Yo bitta layk jalkami?",
    "Iltimos, qiynama mani,",
    "Shunchaki podpiska bos!",
    "Qiz bo‘lmasa bo‘lmaydimi?",
    "Xayp qilmasam yemaydimi?",
    "Bachkana bo‘lib ketmasindan,",
    "Shunchaki podpiska bos!",
    "Gift qilishim kerakmi?",
    "Pul qo‘yishim kerakmi?",
    "Kimnidir g‘iybat qilib,",
    "xayp qilishim kerakmi?",
    "Nima qilsam bosasiz",
    "samolyotcha-cha-cha?",
    "Yo pishkon boraymi qora xalpoqqacha?",
    "Bachkana!",
    "Bachkana, bachkana qiliqlar qilib,",
    "Traktorlarim ustidan kulib,",
    "Pulim ko‘pligini maqtanib chiqsam,",
    "Komment yozasizmi, ey xoli gapirsam?",
]
# scene slots in seconds (sum = 38.0 s)
DUR = [1.9, 1.8, 1.9, 1.8, 1.9, 1.9, 1.9, 1.8, 1.7, 1.7, 1.7, 1.7, 1.8, 2.0, 2.4, 1.2, 2.2, 2.0, 2.2, 2.5]
TOTAL = sum(DUR)
N_FRAMES = int(round(TOTAL * FPS))

VOW = "aeiouAEIOU"
def syllables(w):
    w = w.replace("o‘", "o").replace("g‘", "g").replace("ʻ", "")
    n = sum(1 for ch in w if ch in VOW)
    return max(1, n)

def build():
    words = []
    t0 = 0.0
    scenes = []
    for si, (line, D) in enumerate(zip(LINES, DUR)):
        f_start = int(round(t0 * FPS)); f_end = int(round((t0 + D) * FPS))
        toks = line.split(" ")
        tail = min(0.35, 0.16 * D) if len(toks) > 1 else 0.15
        weights = []
        for tk in toks:
            wgt = syllables(tk) + 0.35
            if tk.endswith(","): wgt += 0.5
            weights.append(wgt)
        span = D - tail
        acc = 0.0; tot = sum(weights)
        for j, (tk, wg) in enumerate(zip(toks, weights)):
            ws = t0 + span * acc / tot
            we = t0 + span * (acc + wg) / tot
            acc += wg
            fs = int(round(ws * FPS)); fe = int(round(we * FPS))
            if j == 0: fs = f_start
            words.append(dict(scene=si + 1, idx=j, word=tk, start=round(fs / FPS, 4), end=round(fe / FPS, 4), f0=fs, f1=fe))
        scenes.append(dict(id=si + 1, text=line, start=round(f_start / FPS, 4), end=round(f_end / FPS, 4), f0=f_start, f1=f_end))
        t0 += D
    # cha beats (scene 14): no vocal -> fallback rule: last 3/6 of the word split evenly
    w14 = [w for w in words if w["scene"] == 14][0]
    D14 = w14["end"] - w14["start"]
    cha = [round(w14["start"] + D14 * k / 6, 4) for k in (3, 4, 5)]
    cha_f = [int(round(c * FPS)) for c in cha]
    return dict(total=TOTAL, n_frames=N_FRAMES, scenes=scenes, words=words, cha=cha, cha_f=cha_f,
                method="text-timed (no vocal track): scene slots + syllable-weighted word spread, frame-snapped")

TIMING = build()
SCENES = TIMING["scenes"]
WORDS = TIMING["words"]
CHA_F = TIMING["cha_f"]

def scene_at(f):
    for s in SCENES:
        if s["f0"] <= f < s["f1"]: return s["id"]
    return SCENES[-1]["id"]

def word_at(f):
    """index of the current (highlighted) word in its scene line"""
    sid = scene_at(f)
    cur = None
    for w in WORDS:
        if w["scene"] == sid and w["f0"] <= f: cur = w
    return sid, cur

if __name__ == "__main__":
    with open(os.path.join(BUILD, "timing.json"), "w") as fh:
        json.dump(TIMING, fh, ensure_ascii=False, indent=1)
    for s in SCENES: print(s["id"], s["start"], s["end"], s["text"])
    print("cha", TIMING["cha"], TIMING["cha_f"], "total", TOTAL, N_FRAMES)
