# Cover image (1080x1920) in the video's style: the same hero in the choyxona courtyard,
# steam from his kosa forming "restaurant", big title kept inside the 3:4 / 4:5 grid-safe area.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
from common import *
import world_choyxona as WC
import world_pool as WP
from hero import draw_hero, draw_steam, RA
import scenes as SC

CAM = (430.0, 962.0, 1.75)
TE = 7.3                     # a calm moment of the loop (leaves mid-air, guests sipping)
X = 392.0

def title_block():
    size = 138
    l1 = text_runs([("Restoranni", INK)], size, FONT_BLACK)
    l2 = text_runs([("ichishgan!", ACCENT)], size, FONT_BLACK)
    lh = int(size * 1.04)
    w = max(l1.width, l2.width)
    im = Image.new("RGBA", (w, lh + l2.height), (0, 0, 0, 0))
    im.alpha_composite(l1, ((w - l1.width) // 2, 0)); im.alpha_composite(l2, ((w - l2.width) // 2, lh))
    if im.width > 960:
        s = 960 / im.width; im = im.resize((960, int(im.height * s)), Image.LANCZOS)
    return glow(im, CREAM, 18, strength=3.2, spread=15)

def kicker():
    size = 50
    t = text_runs([("Bu soʻz qayerdan ", INK), ("chiqqan?", ACCENT)], size, FONT_BLACK)
    padx, pady = 40, 20
    w, h = t.width + 2 * padx, int(size * 1.0) + 2 * pady
    pill = Image.new("RGBA", (w + 30, h + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(pill)
    d.rounded_rectangle((15, 22, 15 + w, 22 + h), radius=h // 2, fill=(20, 28, 30, 60))
    pill = pill.filter(ImageFilter.GaussianBlur(7))
    d = ImageDraw.Draw(pill)
    d.rounded_rectangle((15, 15, 15 + w, 15 + h), radius=h // 2, fill=CREAM + (int(255 * 0.9),))
    f = font(FONT_BLACK, size); asc, _ = f.getmetrics()
    pill.alpha_composite(t, (15 + padx - 4, 15 + (h - int(size * 0.73)) // 2 - (4 + asc - int(size * 0.73))))
    return pill

def main(out_png):
    P = SC.P_ENV
    cv = Canvas(); cv.set_cam(*CAM)
    info = {}
    def hero_fn(c):
        c.layer(1.0)
        info.update(draw_hero(c, X, WP.BANK_Y, 1.0, yaw=1.0, rarm=RA["stop"], rshape="open", steam_t=TE))
    def w(sx, sy): return (CAM[0] + (sx - 540) / CAM[2], CAM[1] + (sy - 960) / CAM[2])
    sx_, sy_ = w(560, 992)
    WC.draw_choyxona(cv, TE, P, hero_fn=hero_fn, sun=(sx_, sy_, 388 / CAM[2]))
    bx, by = info["bowl_top"]
    draw_steam(cv, lambda q: q, bx, by, 1.0, TE * 1.6, scale=1.8, opacity=0.6, height=165)
    img = cv.result()
    cv.layer(1.0)
    img = WP.reflect(img, cv, TE, P, sun_x=660.0)
    cvs = Canvas.__new__(Canvas); cvs.ss = 1; cvs.cam = CAM; cvs.layer(1.0); cvs.ox = cvs.oy = 0
    img = SC.steam_word(img, cvs, 1.0, TE, *w(560, 748), scale=0.86)
    img = apply_grain(img).convert("RGBA")
    tb = title_block()
    img.alpha_composite(tb, (540 - tb.width // 2, 445 - tb.height // 2))
    kp = kicker()
    img.alpha_composite(kp, (540 - kp.width // 2, 1625 - kp.height // 2))
    img = img.convert("RGB")
    img.save(out_png)
    img.save(out_png.replace(".png", ".jpg"), quality=92, optimize=True)
    print("saved", out_png)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "restoran_shorva_cover.png"))
