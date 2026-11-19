# Cover / preview image for the video (1080x1920), same sprites and flat style as the video.
import sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
from lib import *
from worlds import *

CW, CH = 1080, 1920
SPLIT = ((790, 0), (300, 1920))          # diagonal: left = blogger set, right = pharmacy

def split_x(y):
    (x0, y0), (x1, y1) = SPLIT
    return x0 + (x1 - x0) * (y - y0) / (y1 - y0)

def mask_left():
    m = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(m).polygon([(0, 0), SPLIT[0], SPLIT[1], (0, CH)], fill=255)
    return m

def dbl_text(text, size, fill, inner=OL, inner_w=12, outer=WHITE, outer_w=24, shadow=0.55):
    a = text_img(text, size, fill=outer, stroke=outer_w, stroke_fill=outer, shadow=shadow, shadow_off=(0, 10), shadow_blur=10)
    b = text_img(text, size, fill=fill, stroke=inner_w, stroke_fill=inner, shadow=0)
    out = a.copy()
    out.alpha_composite(b, ((a.width - b.width) // 2, (a.height - b.height) // 2 - 5))
    return out

def fit(im, maxw):
    if im.width <= maxw: return im
    s = maxw / im.width
    return im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)

def paste_c(canvas, im, cx, cy, rot=0.0):
    if rot: im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def speech_bubble(text, size=78):
    t = text_img(text, size, fill=OL, stroke=0, shadow=0)
    w, h = t.width + 90, t.height + 40
    c = SS(w + 20, h + 90, 3)
    c.rect((10, 10, w + 10, h + 10), fill=WHITE, outline=OL, width=8, r=46)
    c.poly([(w * 0.30, h + 4), (w * 0.22, h + 80), (w * 0.48, h + 4)], fill=WHITE, outline=None, width=0)
    c.line([(w * 0.30, h + 8), (w * 0.22, h + 80), (w * 0.48, h + 8)], fill=OL, width=8)
    im = c.result()
    im.alpha_composite(t, (int(10 + (w - t.width) / 2), int(10 + (h - t.height) / 2 + 4)))
    return im

def badge(text, w=250, h=96, col=APPLE):
    c = SS(w, h, 3)
    c.rect((6, 6, w - 6, h - 6), fill=col, outline=OL, width=7, r=22)
    c.rect((18, 16, w - 18, 30), fill=(255, 255, 255, 70), outline=None, width=0, r=8)
    im = c.result()
    t = text_img(text, 56, fill=WHITE, stroke=0, shadow=0)
    im.alpha_composite(t, (int((w - t.width) / 2), int((h - t.height) / 2 + 2)))
    return im

def main(out_png):
    # ---------------- background: blogger set (left) / pharmacy (right)
    blog = blogger_back()
    bx, by = 25, 400                                   # cover = world + (bx, by)
    left = blog.crop((-bx - BL_OX, -by - BL_OY, -bx - BL_OX + CW, -by - BL_OY + CH)).convert("RGBA")
    lc = SS(CW, CH, 2)
    lc.rect((0, 1600, CW, CH), fill=(22, 26, 38), outline=OL, width=6)
    lc.ellipse((-40, 1640, 520, 1790), fill=(52, 60, 90), outline=OL, width=6)
    lc.ellipse((10, 1660, 470, 1772), fill=None, outline=YELLOW, width=5)
    left.alpha_composite(lc.result())

    ph = pharmacy_back("boxes")
    px, py = 70, 130                                   # cover = world + (px, py)
    right = ph.crop((-px - PH_OX, -py - PH_OY, -px - PH_OX + CW, -py - PH_OY + CH)).convert("RGBA")

    cover = right.copy()
    cover.paste(left, (0, 0), mask_left())

    # ---------------- characters
    # blogger (shocked) on the left
    bl_x, bl_yb, bl_h = 235, 1715, 830
    sh = soft_shadow(bl_h * 0.42, bl_h * 0.05, 0.35)
    cover.alpha_composite(sh, (int(bl_x - sh.width / 2), int(bl_yb - sh.height / 2)))
    draw_char(cover, "blogger_05", bl_x, bl_yb, bl_h)

    # pharmacist (wink + thumbs up) on the right, behind the counter
    ph_x, ph_yb, ph_h = 735, 1830, 1110
    draw_char(cover, "pharm_07", ph_x, ph_yb, ph_h)

    # counter (right side only) with fruits on top
    cnt = counter_layer()
    clayer = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    clayer.alpha_composite(cnt, (int(split_x(1540) - 60), 1540))
    rm = ImageChops.invert(mask_left())
    clayer.putalpha(ImageChops.multiply(clayer.getchannel("A"), rm))
    cover.alpha_composite(clayer)

    fr = fruit_imgs()
    for name, x, s in (("grapes", 660, 1.05), ("apricot", 790, 0.95), ("pomeg", 905, 1.0), ("apple", 1020, 1.08)):
        im = fr[name]; im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        cover.alpha_composite(im, (int(x - im.width / 2), int(1556 - im.height * 0.86)))

    # floating golden medicine box + sparkles near the pharmacist
    gb = golden_box(120, 146)
    paste_c(cover, gb, 1000, 905, rot=-14)
    for (x, y, s) in ((930, 790, 0.9), (1048, 1030, 0.7), (520, 1250, 0.6), (1040, 1380, 0.55)):
        sp = sparkle(int(70 * s))
        paste_c(cover, sp, x, y, rot=15)

    # diagonal split stripe (drawn over the background, behind nothing important)
    stripe = SS(CW, CH, 2)
    (x0, y0), (x1, y1) = SPLIT
    stripe.line([(x0, y0 - 20), (x1, y1 + 20)], fill=OL, width=30, round_caps=False)
    stripe.line([(x0, y0 - 20), (x1, y1 + 20)], fill=YELLOW, width=16, round_caps=False)
    st = stripe.result()
    # stripe only where characters are not: redraw characters' alpha on top later -> mask out by character alpha
    char_mask = Image.new("L", (CW, CH), 0)
    tmp = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw_char(tmp, "pharm_07", ph_x, ph_yb, ph_h)
    draw_char(tmp, "blogger_05", bl_x, bl_yb, bl_h)
    tmp.alpha_composite(clayer)
    keep = ImageChops.invert(tmp.getchannel("A"))
    st.putalpha(ImageChops.multiply(st.getchannel("A"), keep))
    cover.alpha_composite(st)

    # ---------------- top darkening for title contrast
    grad = Image.new("L", (1, 760))
    for y in range(760):
        grad.putpixel((0, y), int(150 * (1 - y / 760) ** 1.6))
    g = Image.new("RGBA", (CW, 760), (16, 18, 28, 0)); g.putalpha(grad.resize((CW, 760)))
    cover.alpha_composite(g)

    # ---------------- text
    pill_t = text_img("AGAR BLOGER BOʻLMAGANIDA...", 50, fill=YELLOW, stroke=0, shadow=0)
    pw, phh = pill_t.width + 70, pill_t.height + 22
    pc = SS(pw, phh, 3)
    pc.rect((4, 4, pw - 4, phh - 4), fill=(20, 22, 32, 235), outline=YELLOW, width=5, r=phh / 2 - 4)
    pill = pc.result(); pill.alpha_composite(pill_t, (35, 11 + 2))
    paste_c(cover, pill, 540, 282)

    name = fit(dbl_text("JAMSHIDXON", 118, WHITE, outer=OL, outer_w=14, inner_w=12), 820)
    paste_c(cover, name, 520, 425, rot=-3)
    title = fit(dbl_text("APTEKACHI", 200, YELLOW, inner_w=14, outer_w=28), 860)
    paste_c(cover, title, 490, 590, rot=-3)
    pill_emoji = emoji_img("💊", 140)
    paste_c(cover, pill_emoji, 994, 548, rot=-18)

    # speech bubble for the shocked blogger
    sb = speech_bubble("MEN?! 😳", 74)
    paste_c(cover, sb, 245, 790, rot=4)

    # episode badge
    bd = badge("1-QISM")
    paste_c(cover, bd, 905, 1640, rot=-5)

    cover = cover.convert("RGB")
    cover.save(out_png)
    cover.save(out_png.replace(".png", ".jpg"), quality=95)
    # grid-crop preview (3:4 centre and 1:1 centre) for checking
    prev = Image.new("RGB", (CW // 2 * 3 + 40, CH // 2), (240, 240, 240))
    prev.paste(cover.resize((CW // 2, CH // 2)), (0, 0))
    c34 = cover.crop((0, (CH - 1440) // 2, CW, (CH + 1440) // 2)).resize((CW // 2, 720))
    prev.paste(c34, (CW // 2 + 20, (CH // 2 - 720) // 2))
    c11 = cover.crop((0, (CH - 1080) // 2, CW, (CH + 1080) // 2)).resize((CW // 2, CW // 2))
    prev.paste(c11, (CW + 40, (CH // 2 - CW // 2) // 2))
    prev.save(out_png.replace(".png", "_crops.png"))

if __name__ == "__main__":
    main(sys.argv[1])
