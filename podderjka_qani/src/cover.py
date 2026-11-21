# Cover image (1080x1920) in the video's style: the hook moment — the hero knocking on the screen glass
# in the midday mahalla street, ripples on the glass, "0 OBUNACHI" badge and the title.
# Title, badge and hero face stay inside the 4:5 / 3:4 grid-safe area (y 285..1635).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFilter
from common import *
from base import *
import scenes_a as A
import overlay as OV

Z = 2.75
HEAD_Y = 800                                       # where the doppi top lands on the cover
CAM = (540.0, A.HERO_Y - 363 * A.HERO_S + (960 - HEAD_Y) / Z, Z)
TL = 0.0                                           # knock instant: right fist on the glass

def title_block():
    l1 = text_runs([("Akajon,", INK)], 100, FONT_BLACK)
    l2 = text_runs([("podderjka", ACCENT)], 156, FONT_BLACK)
    l3 = text_runs([("qani?", INK)], 138, FONT_BLACK)
    gap = [0, int(100 * 0.98), int(100 * 0.98 + 156 * 1.0)]
    w = max(l1.width, l2.width, l3.width)
    im = Image.new("RGBA", (w, gap[2] + l3.height), (0, 0, 0, 0))
    for l, y in zip((l1, l2, l3), gap):
        im.alpha_composite(l, ((w - l.width) // 2, y))
    if im.width > 900:
        s = 900 / im.width; im = im.resize((900, int(im.height * s)), Image.LANCZOS)
    return glow(im, CREAM, 18, strength=3.2, spread=15)

def pill(runs, size=50):
    t = text_runs(runs, size, FONT_BLACK)
    padx, pady = 40, 20
    w, h = t.width + 2 * padx, int(size * 1.0) + 2 * pady
    out = Image.new("RGBA", (w + 30, h + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((15, 22, 15 + w, 22 + h), radius=h // 2, fill=(20, 28, 30, 60))
    out = out.filter(ImageFilter.GaussianBlur(7))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((15, 15, 15 + w, 15 + h), radius=h // 2, fill=CREAM + (int(255 * 0.92),))
    f = font(FONT_BLACK, size); asc, _ = f.getmetrics()
    out.alpha_composite(t, (15 + padx - 4, 15 + (h - int(size * 0.73)) // 2 - (4 + asc - int(size * 0.73))))
    return out

def main(out_png):
    cv = Canvas(ss=3)
    cv.set_cam(*CAM)
    A.street_world(cv, TL)
    cv.layer(1.0)
    A.bench(cv, 372, 718, A.HERO_Y - 92 * A.HERO_S, KUNDUZ["L5"])
    fists = A.knock_hero(cv, TL)
    # ripples on the glass: the fresh knock + the one before it
    cv.screen()
    for (x, y), r, a, w in ((fists[0], 70, 210, 6), (fists[0], 128, 120, 4), (fists[1], 150, 90, 3.5)):
        ring(cv, x, y, r, r, (255, 255, 255), w, a)
    glass_glare(cv, 150)
    img = cv.result()
    img = apply_grain(img).convert("RGBA")
    badge = OV.obunachi_img()
    badge = badge.resize((int(badge.width * 1.25), int(badge.height * 1.25)), Image.LANCZOS)
    img.alpha_composite(badge, (540 - badge.width // 2, 318 - badge.height // 2))
    tb = title_block()
    img.alpha_composite(tb, (540 - tb.width // 2, 602 - tb.height // 2))
    kp = pill([("Shunchaki ", INK), ("podpiska", ACCENT), (" bos!", INK)], 52)
    img.alpha_composite(kp, (540 - kp.width // 2, 1560 - kp.height // 2))
    img = img.convert("RGB")
    img.save(out_png)
    img.save(out_png.replace(".png", ".jpg"), quality=92, optimize=True)
    print("saved", out_png)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "podderjka_qani_cover.png"))
