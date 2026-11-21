# Frame dispatcher: scene drawing -> grain/vignette -> subtitle plate + on-screen texts.
import math, importlib
from common import *
from script_data import SCENES, WORDS, N_FRAMES, TOTAL, scene_at, CHA_F
import overlay as OV

_MODS = {}
def _fn(sid):
    mod = "scenes_a" if sid in (1, 2, 3, 4, 20) else "scenes_b" if sid in (5, 6, 7, 8, 9, 10) else "scenes_c" if sid in (11, 12, 13, 14) else "scenes_d"
    if mod not in _MODS: _MODS[mod] = importlib.import_module(mod)
    return getattr(_MODS[mod], f"s{sid}")

def scene_info(sid):
    return SCENES[sid - 1]

def render_frame(f, with_text=True):
    sid = scene_at(f)
    sc = scene_info(sid)
    t = f / FPS
    lt = (f - sc["f0"]) / FPS
    D = (sc["f1"] - sc["f0"]) / FPS
    cv = Canvas(ss=SS)
    res = _fn(sid)(cv, lt, D, t) or {}
    img = cv.result()
    if res.get("post"): img = res["post"](img)
    img = apply_grain(img)
    if res.get("screen"): res["screen"](img)
    if with_text:
        if res.get("obunachi", 0) > 0.01:
            OV.paste_center(img, OV.obunachi_img(), 540, 262, alpha=res["obunachi"])
        if not res.get("no_plate"):
            OV.draw_subtitle(img, f, sid)
    return img
