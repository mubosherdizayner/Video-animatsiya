# Script text per scene (the subtitle source). Dash tokens are punctuation, not spoken words.
SCENES = [
    (1, "Toʻqson foiz odam aytdi: doʻstingiz sizni million dollarga sotadi."),
    (2, "Demak, doʻstingiz sizdan voz kechdi."),
    (3, "Birga koʻrgan orzularingiz,"),
    (4, "semichka chaqib oʻtirgan kechalaringiz —"),
    (5, "hammasi oʻchib ketdi."),
    (6, "Endi oʻyin qiyinlashadi."),
    (7, "Tugma yana doʻstingiz oldida. Bossa — yana bir million."),
    (8, "Lekin bu safar evaziga — sevgan qizi."),
    (9, "Qizni tanlasa — na doʻsti qoladi, na puli."),
    (10, "Pulni tanlasa — ikki million dollar."),
    (11, "Sizni sotgan odam — uni ham sotarmikan?"),
    (12, "Qizni tanlaydi — bir, pulni tanlaydi — ikki. Izohga yozing."),
    (13, "Ishonchingiz yoʻqmi? Unga yuboring va qanday reaksiya qilishini koʻring."),
    (14, "Natijani keyingi videoda aytaman."),
]
ON_SCREEN = {
    1: "90% — SOTADI", 2: "VOZ KECHDI", 3: "ORZULAR", 4: "", 5: "OʻCHIRILDI", 6: "2-RAUND",
    7: "+$1 000 000", 8: "EVAZIGA — U", 9: "$0", 10: "$2 000 000", 11: "1-RAUNDDA — SIZ. ENDI — U?",
    12: "IZOHDA: 1 — QIZ · 2 — PUL", 13: "UNGA YUBOR ✈️", 14: "NATIJA — KEYINGI VIDEODA",
}

def script_words():
    """spoken words in order; a dash is glued to the word before it for display"""
    out = []
    for sid, txt in SCENES:
        toks = txt.split()
        k = 0
        for t in toks:
            if t in ("—", "-", "–"):
                out[-1]["text"] += " —"
                continue
            out.append({"scene": sid, "text": t, "first": k == 0})
            k += 1
    return out
