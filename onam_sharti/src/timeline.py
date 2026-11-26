# Scene timeline from word timestamps.
import json, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
TIMING = json.load(open(os.path.join(HERE, "timing.json")))
AUDIO_DUR = float(open(os.path.join(HERE, "audio_dur.txt")).read())
N_FRAMES = int(round(AUDIO_DUR * FPS))
SC_IDS = list(range(1, 14))
SC_START = {k: next(w["start"] for w in TIMING if w["scene"] == k) for k in SC_IDS}
SC_FRAME = {k: int(round(SC_START[k] * FPS)) for k in SC_IDS}
SC_START[1] = 0.0; SC_FRAME[1] = 0
SC_END = {k: (SC_FRAME[k + 1] / FPS if k < 13 else N_FRAMES / FPS) for k in SC_IDS}
def word(scene, text):
    for w in TIMING:
        if w["scene"] == scene and w["text"].lower().startswith(text.lower()): return w["start"]
    raise KeyError((scene, text))
def wframe(w): return 0 if (w["scene"] == 1 and w["first"]) else int(round(w["start"] * FPS))
def scene_at(i):
    k = 1
    for s in SC_IDS:
        if i >= SC_FRAME[s]: k = s
    return k
