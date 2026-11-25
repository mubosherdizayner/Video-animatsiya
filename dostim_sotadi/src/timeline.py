# Scene / word timing from the forced alignment (timing.json).
import json, os, math
from style import FPS
HERE = os.path.dirname(os.path.abspath(__file__))
_T = json.load(open(os.path.join(HERE, "timing.json")))
WORDS = _T["words"]
AUDIO_DUR = float(open(os.path.join(HERE, "audio_dur.txt")).read())
N_FRAMES = int(math.ceil(AUDIO_DUR * FPS - 1e-6))
SC_IDS = list(range(1, 15))

def wframe(w):
    """frame on which a word appears (first word of the video: frame 0)"""
    return 0 if w is WORDS[0] else int(round(w["start"] * FPS))

SC_START = {}
SC_FRAME = {}
for k in SC_IDS:
    w = next(x for x in WORDS if x["scene"] == k)
    SC_FRAME[k] = wframe(w)
    SC_START[k] = 0.0 if k == 1 else w["start"]
SC_END_FRAME = {k: (SC_FRAME[k + 1] if k < 14 else N_FRAMES) for k in SC_IDS}

def scene_words(k): return [w for w in WORDS if w["scene"] == k]

def word_t(k, i):
    """time of the frame on which the i-th word of scene k appears (word onset rounded to the frame grid),
    so scene events fire on the same frame as the subtitle highlight"""
    return wframe(scene_words(k)[i]) / FPS

def scene_at(i):
    cur = 1
    for k in SC_IDS:
        if i >= SC_FRAME[k]: cur = k
    return cur
