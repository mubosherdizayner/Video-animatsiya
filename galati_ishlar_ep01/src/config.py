# G'alati ishlar — 1-qism. Shared configuration: timeline, frames, script, cut points.
import os

FPS = 30
W, H = 1080, 1920
DURATION = 50.0
NFRAMES = int(round(DURATION * FPS))
SR = 48000

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("GI_WORK", os.path.join(HERE, "..", "_work"))
FRAMES_DIR = os.environ.get("GI_FRAMES", os.path.join(WORK, "frames"))
VOICE_WAV = os.path.join(WORK, "audio", "voice48.wav")
KULGI = os.environ.get("GI_KULGI", "")          # path to kulgi.mp3 if the user attaches it

# Palette (light effects, overlays, subtitles only)
SHADOW1 = (0x0F, 0x1A, 0x24)
SHADOW2 = (0x1E, 0x2F, 0x3D)
LAMP = (0xE8, 0xB2, 0x5A)
ALARM = (0xD8, 0x36, 0x2F)
EYES = (0xFF, 0x3B, 0x1F)
TEXT = (0xF4, 0xF1, 0xEA)

# ---------------------------------------------------------------------------
# Lines cut from the single narrator file (seconds in the source file).
# Boundaries come from faster-whisper word timestamps refined on the audio
# energy envelope (see timing.py); trims remove leading/trailing silence and
# the breath before "Qochaman!".
LINE_CUTS = {
    1: (0.000, 6.120),
    2: (6.700, 8.740),
    3: (8.800, 11.450),
    4: (11.600, 12.460),
    5: (12.850, 17.880),
}

# Where each line's audio really ends (natural decay / breath), faded out with an
# equal-power curve so no word is clipped. Line 1 ends exactly at the scene-1 cut (9.4 s).
LINE_TAIL = {1: (6.200, 0.12), 2: (8.780, 0.06), 3: (11.500, 0.08), 4: (12.620, 0.15), 5: (18.000, 0.12)}

# Script (subtitle text source). Apostrophes are typeset as Uzbek oʻ / gʻ.
SCRIPT = {
    1: ("HIKOYACHI", "1980-yil. Tunqo'rg'on. Bu bazada nima qilishayotganini hech kim bilmasdi."),
    2: ("HIKOYACHI", "O'sha kecha nimadir tashqariga chiqdi."),
    3: ("DONIYOR", "Dev keldi! Nima qilasan, Sardor?"),
    4: ("SARDOR", "Qochaman!"),
    5: ("HIKOYACHI", "Ertasi kuni Sardorni hech kim topolmadi. Davomi bor — obuna bo'ling."),
}

# ---------------------------------------------------------------------------
# Timeline. Brief values, with the overflow rule applied:
#  * line 1 is 6.12 s but scene 1 has 5.8 s after its 3.2 s voice_start, so
#    scene 1 takes 0.4 s from the nearest silent scene (5); scenes 2-4 and
#    their voice_starts / sfx move +0.4 s, scene 5 is 0.4 s shorter.
#  * line 5 is 5.03 s but scene 10 has 4.8 s after 45.2 s, so scene 10
#    takes 0.5 s from the nearest silent scene (9); it starts at 44.5 s.
D1 = 0.4
D5 = 0.5

def _s(lst, d):
    return [(k, a + d, b + d) for k, a, b in lst]

SCENES = [
    # id, role, start, end, shots[(frame, t0, t1)], line, voice_start
    dict(id=0, role="hook", start=0.0, end=3.0, shots=[("F01", 0.0, 3.0)], line=None, vs=None),
    dict(id=1, role="body", start=3.0, end=9.0 + D1, shots=[("F02", 3.0, 5.5), ("F03", 5.5, 9.0 + D1)], line=1, vs=3.2),
    dict(id=2, role="body", start=9.0 + D1, end=14.0 + D1, shots=_s([("F04", 9.0, 11.0), ("F05", 11.0, 12.5), ("F06", 12.5, 14.0)], D1), line=2, vs=11.2 + D1),
    dict(id=3, role="body", start=14.0 + D1, end=18.5 + D1, shots=_s([("F07", 14.0, 15.5), ("F08", 15.5, 18.5)], D1), line=3, vs=15.6 + D1),
    dict(id=4, role="body", start=18.5 + D1, end=23.0 + D1, shots=_s([("F09", 18.5, 20.0), ("F10", 20.0, 23.0)], D1), line=4, vs=18.6 + D1),
    dict(id=5, role="body", start=23.0 + D1, end=28.0, shots=[("F11", 23.0 + D1, 25.5), ("F12", 25.5, 28.0)], line=None, vs=None),
    dict(id=6, role="body", start=28.0, end=33.0, shots=[("F13", 28.0, 30.0), ("F14", 30.0, 31.5), ("F15", 31.5, 33.0)], line=None, vs=None),
    dict(id=7, role="body", start=33.0, end=37.0, shots=[("F16", 33.0, 35.0), ("F17", 35.0, 37.0)], line=None, vs=None),
    dict(id=8, role="re_hook", start=37.0, end=41.0, shots=[("F18", 37.0, 39.5), ("BLACK", 39.5, 41.0)], line=None, vs=None),
    dict(id=9, role="payoff", start=41.0, end=45.0 - D5, shots=[("F19", 41.0, 43.0), ("F20", 43.0, 45.0 - D5)], line=None, vs=None),
    dict(id=10, role="cta", start=45.0 - D5, end=50.0, shots=[("F21", 45.0 - D5, 47.5 - D5), ("F20", 47.5 - D5, 50.0)], line=5, vs=45.2 - D5),
]

VOICE_START = {s["line"]: round(s["vs"], 3) for s in SCENES if s["line"]}

def shot_list():
    out = []
    for s in SCENES:
        for k, a, b in s["shots"]:
            out.append((k, round(a, 4), round(b, 4), s["id"]))
    return out

def fr(t):
    """Frame index at which an event at time t becomes visible."""
    return int(round(t * FPS))
