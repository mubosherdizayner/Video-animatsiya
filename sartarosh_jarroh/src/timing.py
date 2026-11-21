# Word / scene timing in frames (from timing.json, produced by transcribe.py -> align.py -> fa.py)
import json, os, subprocess
from gfx import FPS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AUDIO = os.path.join(ROOT, "assets", "voice.mp3")
WORDS = json.load(open(os.path.join(HERE, "timing.json")))


def _dur():
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", AUDIO],
                         capture_output=True, text=True).stdout
    return float(out.strip())


AUDIO_DUR = _dur()
N_FRAMES = int(round(AUDIO_DUR * FPS))
for w in WORDS:
    w["f"] = int(round(w["start"] * FPS))
SCENE_IDS = sorted({w["scene"] for w in WORDS})
SC_FRAME = {}
for k in SCENE_IDS:
    SC_FRAME[k] = min(w["f"] for w in WORDS if w["scene"] == k)
SC_FRAME[1] = 0  # hook: frame 0 already belongs to scene 1
SC_END = {k: (SC_FRAME[k + 1] if k + 1 in SC_FRAME else N_FRAMES) for k in SCENE_IDS}


def norm(s):
    return "".join(ch for ch in s.lower().replace("ʻ", "'").replace("ʼ", "'") if ch.isalnum() or ch == "'")


def word(scene, text, nth=0):
    hits = [w for w in WORDS if w["scene"] == scene and norm(w["text"]) == norm(text)]
    return hits[nth]


def cue(scene, text, nth=0):
    """time (s) of the frame on which the named word starts"""
    return word(scene, text, nth)["f"] / FPS


def scene_at(i):
    k = SCENE_IDS[0]
    for s in SCENE_IDS:
        if i >= SC_FRAME[s]:
            k = s
    return k


def scene_start(k):
    return SC_FRAME[k] / FPS


def scene_end(k):
    return SC_END[k] / FPS
