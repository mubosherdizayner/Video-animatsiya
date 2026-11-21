# Scene texts exactly as in the brief (subtitle source; never the transcript).
SCENES = [
 (1,  "To'xtang! Sartaroshlar avval tish sug'urgan."),
 (2,  "O'rta asrlar Yevropasida ularni sartarosh-jarroh deyishgan."),
 (3,  "Ular tish sug'urgan,"),
 (4,  "suyak o'rnatgan, yaralarni davolagan."),
 (5,  "Shifokorlar esa jarrohlikni o'zlariga ep ko'rmagan."),
 (6,  "Bugun sartaroshga «ozroq oling» deysiz-a?"),
 (7,  "O'shanda esa sochdan tashqari qon ham olishgan."),
 (8,  "Ishonmayapsizmi? Isboti har kuni ko'zingiz oldida aylanadi."),
 (9,  "Qizil rang — qon. Oq rang — qonni to'xtatgan bint."),
 (10, "Ustunning o'zi esa qon olishda bemor qisgan tayoq ramzi."),
 (11, "Buni sartaroshingizga yuboring."),
 (12, "Keyingi safar u «o'tiring» desa..."),
]

def tokens(text):
    """split into subtitle words; '—' sticks to the next word, '...' to the previous."""
    raw = text.split()
    out = []
    carry = ""
    for w in raw:
        if w in ("—", "–"):
            carry = w + " "
            continue
        if w in ("...", "…") and out:
            out[-1] += w
            continue
        out.append(carry + w)
        carry = ""
    return out
