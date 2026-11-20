# Timing: word onsets (script words) -> scene starts, frames.
import json, os, math
from script_data import SCENES, REGIONS

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
WORDS = json.load(open(os.path.join(HERE, "words.json")))
AUDIO_DUR = float(open(os.path.join(HERE, "audio_dur.txt")).read())
N_FRAMES = int(math.ceil(AUDIO_DUR * FPS - 1e-6))
IDS = [s[0] for s in SCENES]
SC = {s[0]: dict(text=s[1], ost=s[2], gold=s[3], pose=s[4]) for s in SCENES}


def wf(w): return int(round(w["start"] * FPS))


def scene_words(k): return [w for w in WORDS if w["scene"] == k]


def word(k, prefix, nth=0):
    c = [w for w in scene_words(k) if w["text"].lower().strip("«»!?.,:—- ").startswith(prefix.lower())]
    return c[nth]


S = {}        # scene start time (s) = first spoken word of the scene
SF = {}       # scene start frame
for k in IDS:
    w0 = scene_words(k)[0]
    SF[k] = 0 if k == 1 else wf(w0)
    S[k] = SF[k] / FPS
END_F = {k: (SF[IDS[i + 1]] if i + 1 < len(IDS) else N_FRAMES) for i, k in enumerate(IDS)}
DUR = {k: (END_F[k] - SF[k]) / FPS for k in IDS}


def scene_at(i):
    k = IDS[0]
    for kk in IDS:
        if i >= SF[kk]: k = kk
    return k


def T(k, prefix, nth=0):
    """frame-quantised onset time of a word"""
    return wf(word(k, prefix, nth)) / FPS
