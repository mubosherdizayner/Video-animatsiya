# Script text per scene (subtitle source). Scenes 2-3 and 7-9 split sentences.
SCENES = [
    (1, "Uylanmoqchimisiz? Avval onamning bitta shartini eshiting."),
    (2, "Bir kuni onam aytdilar:"),
    (3, "«O'g'lim, uylanishdan oldin moliyaviy ahvolingni yaxshilab ol.»"),
    (4, "«Boy bo'lib ketishing shart emas.»"),
    (5, "«Lekin yaxshi holatda bo'lishing shart.»"),
    (6, "Sababini eshitib, jim bo'lib qoldim."),
    (7, "«Chunki uylansang-u, ayoling sabrsiz bo'lib,"),
    (8, "pul deb ajrashib ketsa..."),
    (9, "bolang yetim bo'ladi.»"),
    (10, "«Kim aybli — muhim emas."),
    (11, "Muhimi, bolada ayb yo'q.»"),
    (12, "Uylanish arafasidagi do'stingizga yuboring."),
    (13, "Rozi bo'lsangiz, o'zingizda repost qiling."),
]
KEY = {1: "shartini", 3: "moliyaviy", 9: "yetim", 11: "ayb", 12: "yuboring", 13: "repost"}

def display(w):
    """script word -> on-screen word: drop « » , . : … ; keep ? and -; uzbek okina/apostrophe."""
    for c in "«»,.:…":
        w = w.replace(c, "")
    w = w.replace("o'", "oʻ").replace("O'", "Oʻ").replace("g'", "gʻ").replace("G'", "Gʻ").replace("'", "ʼ")
    return w

def script_words():
    out = []
    for sid, txt in SCENES:
        k = 0
        for w in txt.split():
            if w == "—":
                continue
            out.append({"scene": sid, "raw": w, "text": display(w), "first": k == 0,
                        "key": KEY.get(sid) is not None and display(w).lower() == KEY[sid]})
            k += 1
    return out
