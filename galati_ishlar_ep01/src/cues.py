# Shared animation cues: the picture and the sound effects read the same curves.
import math
from config import D1, D5

def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x

def smooth(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)

def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3

def ease_in(x):
    x = clamp01(x)
    return x ** 3

# --- hook: red alarm lamp, ~2 pulses per second, bright at frame 0 ---------
ALARM_HZ = 2.0
def alarm(t):
    p = 0.5 + 0.5 * math.cos(2 * math.pi * ALARM_HZ * t)
    return p ** 1.6

ALARM_TIMES = [k / ALARM_HZ for k in range(6)]            # 0.0, 0.5, ... 2.5

# --- scene 2 ----------------------------------------------------------------
DOOR_CLOSE_T0 = 9.15 + D1        # door starts sliding
DOOR_SHUT = 10.8 + D1            # heavy clunk (brief: 10.8 s)
CREATURE_DROP = 11.0 + D1        # black shape drops (brief: 11.0 s)
CREATURE_LAND = CREATURE_DROP + 0.10
F06_T0 = 12.5 + D1
# lamp flicker in the empty lift: (start, gain) steps, then holds
F06_STEPS = [(0.00, 1.0), (0.10, 0.12), (0.17, 0.85), (0.24, 0.18), (0.40, 1.0), (0.47, 0.10),
             (0.62, 0.75), (0.67, 0.25), (0.74, 1.0)]
def f06_lamp(t):
    x = t - F06_T0
    g = 1.0
    for s, v in F06_STEPS:
        if x >= s: g = v
    return g

# --- scene 5: street lamp flickers off/on three times -------------------------
F12_OFF = [(25.80, 25.95), (26.30, 26.50), (26.95, 27.30)]
def f12_lamp(t):
    for a, b in F12_OFF:
        if a <= t < b:
            return 0.0
    return 1.0

# --- scene 6 ------------------------------------------------------------------
FALL_T = 30.0

# --- scene 7/8/9 --------------------------------------------------------------
SHED_DOOR_T = 34.95
WET_BREATH_T = 38.0
LIGHT_OFF_T = 39.5
EYES_HOLD = 0.3
LIGHT_ON_T = 41.0
def f19_bulb(t):
    x = t - LIGHT_ON_T
    if x < 0: return 0.0
    if 0.10 <= x < 0.14: return 0.35          # one quick stutter right after the click
    return 1.0

# --- wheel (F20 / F21 / F20): spins, slows, stops ---------------------------
WHEEL_T0 = 43.0
WHEEL_STOP = 48.3
WHEEL_W0 = 1.45            # rev/s at 43.0
WHEEL_P = 1.35
def wheel_speed(t):
    if t < WHEEL_T0: return WHEEL_W0
    if t >= WHEEL_STOP: return 0.0
    u = (t - WHEEL_T0) / (WHEEL_STOP - WHEEL_T0)
    return WHEEL_W0 * (1 - u) ** WHEEL_P

def wheel_angle(t):
    """Revolutions turned since WHEEL_T0 (closed form of the speed integral)."""
    T = WHEEL_STOP - WHEEL_T0
    u = clamp01((t - WHEEL_T0) / T)
    return WHEEL_W0 * T * (1 - (1 - u) ** (WHEEL_P + 1)) / (WHEEL_P + 1)

LAMP_OFF_T = 48.8          # street lamp goes out in the last shot
def f20_lamp(t):
    if t < LAMP_OFF_T - 0.12: return 1.0
    if t < LAMP_OFF_T - 0.08: return 0.2
    if t < LAMP_OFF_T - 0.03: return 0.9
    if t < LAMP_OFF_T: return 0.15
    return 0.0

def end_darken(t):
    """Frame gain for the last shot: darkens to near black by 50.0 s."""
    if t < LAMP_OFF_T: return 1.0
    return 1.0 - 0.93 * smooth((t - LAMP_OFF_T) / (49.95 - LAMP_OFF_T))
