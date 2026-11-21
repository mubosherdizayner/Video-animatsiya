# Scene script (voice text) — the single source for subtitles and scene timing.
SCENES = [
    (1, "To'xtang! «Restoran» avval joy emas,"),
    (2, "sho'rva nomi bo'lgan."),
    (3, "Frantsuzchada «restoran» — «tiklovchi»,"),
    (4, "ya'ni kuch beradigan quyuq bulyon."),
    (5, "Ko'pchilik ishonadi: restoranlarni inqilobdan keyin"),
    (6, "ishsiz qolgan oshpazlar ochgan."),
    (7, "Afsona!"),
    (8, "Birinchi restoranlar Parijda bir ming yetti yuz"),
    (9, "oltmishinchi yillarda ochilgan."),
    (10, "Inqilobdan o'nlab yil oldin."),
    (11, "Ular sog'liq do'koni edi,"),
    (12, "asosiy taomi — o'sha bulyon."),
    (13, "Taom nomi joyga o'tdi."),
    (14, "Ya'ni siz aslida sho'rvaga kirasiz."),
    (15, "Choyxona — choydan, oshxona — oshdan."),
    (16, "Yana qaysi joy nomi taomdan kelgan?"),
    (17, "Topib, izohda yozing!"),
]
KEYWORDS = {"restoran", "sho'rva", "tiklovchi", "bulyon", "afsona", "oltmishinchi", "o'nlab",
            "sog'liq", "sho'rvaga", "choyxona", "oshxona", "izohda"}
ON_SCREEN = {  # text, accent words (rendered in sun orange)
    1: ("Restoranni ichishgan!", ["ichishgan!"]),
    2: ("Restoranni ichishgan!", ["ichishgan!"]),
    3: ("restaurant = tiklovchi", ["tiklovchi"]),
    4: ("Parij, XVIII asr", ["XVIII"]),
    5: ("1789 — inqilob", ["1789"]),
    6: ("Ishsiz oshpazlar ochgan?", ["ochgan?"]),
    7: ("AFSONA", ["AFSONA"]),
    8: ("1760-yillar", ["1760-yillar"]),
    9: ("Birinchi restoranlar", ["restoranlar"]),
    10: ("1760-yillar → 1789", ["1760-yillar"]),
    11: ("Sog'liq do'koni", ["Sog'liq"]),
    12: ("Menyuda: bulyon", ["bulyon"]),
    13: ("Taom → joy", ["joy"]),
    14: ("Marhamat, sho'rvaga!", ["sho'rvaga!"]),
    15: ("Choy+xona · Osh+xona", ["Choy", "Osh"]),
    16: ("Yana qaysi?", ["qaysi?"]),
    17: ("Izohda yozing 👇", ["Izohda"]),
}
# Manual onsets (s) for mid-phrase words Whisper merged into a number token; probed by
# re-transcribing clips that start at candidate cut points + energy dips.
OVERRIDES = {(8, "bir"): 16.68, (8, "ming"): 16.88, (8, "yetti"): 17.01, (8, "yuz"): 17.69,
             (9, "oltmishinchi"): 17.95, (6, "ishsiz"): 12.21,
             (8, "restoranlar"): 15.69, (14, "aslida"): 27.58, (14, "siz"): 27.35}
