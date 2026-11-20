# Script text per scene (subtitle source), on-screen text, gold accent words, poses.
SCENES = [
    (1, "Bitta osh. Oʻn toʻrt hudud. Hammasi: «Eng zoʻri bizniki!»", "14 TA «ENG ZOʻR» OSH?!", ["«ENG", "ZOʻR»"], "s1_r2c1"),
    (2, "Osh madaniyati Yunesko roʻyxatida — masala jiddiy!", "YUNESKO • 2016", ["YUNESKO"], "s1_r1c2"),
    (3, "Men xolis hakam boʻlishga qaror qildim.", "XOLIS HAKAM", ["HAKAM"], "s1_r2c2"),
    (4, "Toshkent oshi — hammasi aralash.", "TOSHKENT: ARALASH", ["ARALASH"], "s1_r2c3"),
    (5, "Samarqandda aralashtirilmaydi: guruch, sabzi, goʻsht — qavat-qavat.", "SAMARQAND: QAVAT-QAVAT", ["QAVAT-QAVAT"], "s1_r3c2"),
    (6, "Fargʻonada — devzira guruch, yogʻi moʻl.", "FARGʻONA: DEVZIRA", ["DEVZIRA"], "s2_r2c1"),
    (7, "Qolgan oʻn bitta hududning ham oʻz siri bor.", "+11 HUDUD", ["+11"], "s2_r1c2"),
    (8, "Lekin bir muammo chiqdi: hammasi eng zoʻri!", "HAMMASI ENG ZOʻR?!", ["ENG", "ZOʻR?!"], "s1_r2c4"),
    (9, "Aslida eng zoʻr osh... onamning oshi.", "ONAMNING OSHI", ["ONAMNING"], "s2_r2c4"),
    (10, "Lekin bu xolis emas.", "XOLIS EMAS...", ["EMAS..."], "s2_r2c2"),
    (11, "Shuning uchun hakam — siz!", "HAKAM — SIZ!", ["SIZ!"], "s1_r1c3"),
    (12, "Izohda yozing: qaysi viloyatdansiz", "IZOHDA YOZING", ["YOZING"], "s1_r3c1"),
    (13, "va qaysi viloyat oshi sizga yoqadi?", "VILOYAT + SEVIMLI OSH", ["SEVIMLI", "OSH"], "s1_r1c4"),
    (14, "Boshqa viloyatlik doʻstingizga yuboring — bahs boshlansin!", "DOʻSTINGIZGA YUBORING", ["YUBORING"], "s2_r1c4"),
]
REGIONS = ["Andijon", "Buxoro", "Jizzax", "Namangan", "Navoiy", "Qashqadaryo", "Qoraqalpogʻiston",
           "Sirdaryo", "Surxondaryo", "Toshkent viloyati", "Xorazm"]


def script_words():
    """subtitle tokens; a standalone dash is glued to the previous word"""
    out = []
    for sid, txt, *_ in SCENES:
        toks = []
        for t in txt.split():
            if t in ("—", "-", "–") and toks: toks[-1] += " " + t
            else: toks.append(t)
        for k, t in enumerate(toks):
            out.append({"scene": sid, "text": t, "first": k == 0})
    return out
