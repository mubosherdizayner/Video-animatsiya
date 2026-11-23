# Script text (subtitle source) for every scene, taken verbatim from the brief.
SCENES = [
    (1, "Do'stingning oldiga bitta tugma qo'yishdi."),
    (2, "Bossa — bir million dollar."),
    (3, "Bosmasa — sen qolasan."),
    (4, "Agar bossa..."),
    (5, "sen uning hayotidan o'chib ketasan."),
    (6, "Butunlay."),
    (7, "Ovozli xabar yo'q."),
    (8, "Reels jo'natish yo'q."),
    (9, "Yarim tunda..."),
    (10, "\"Chiqasanmi?\" Yo'q."),
    (11, "Hatto to'yingda ham uning stuli bo'sh qoladi."),
    (12, "Xo'sh... u bosarmidi?"),
    (13, "Javob berma."),
    (14, "Buni unga yubor... va qancha o'ylanib qolishini ko'r."),
    (15, "Agar u bosmasligini aniq bilsang — repost qil."),
    (16, "Ertaga... izohlarda nechta odam \"bosadi\" deganini aytaman."),
    (17, "Obuna bo'l, o'tkazib yuborma!"),
]

def uz(s):
    """ASCII apostrophes -> proper Uzbek letters: o' g' -> oʻ gʻ, other ' -> ʼ; straight quotes -> “ ”."""
    out = []
    for i, ch in enumerate(s):
        if ch == "'":
            prev = s[i - 1] if i else ""
            out.append("ʻ" if prev in "oOgG" else "ʼ")
        else:
            out.append(ch)
    s = "".join(out)
    res, open_q = [], True
    for ch in s:
        if ch == '"':
            res.append("“" if open_q else "”"); open_q = not open_q
        else:
            res.append(ch)
    return "".join(res)

def tokens(text):
    """Split on spaces; punctuation-only tokens (like the dash) stick to the previous word."""
    out = []
    for w in text.split():
        if out and not any(c.isalnum() for c in w):
            out[-1] += " " + w
        else:
            out.append(w)
    return out
