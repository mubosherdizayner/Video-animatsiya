# Bake the edge_fallback sticker outline into every sheet sprite (sprites/ -> sprites_st/)
import json, os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import lib
src = json.load(open("sprites/meta.json"))
os.makedirs("sprites_st", exist_ok=True)
STAND = {"bobur": 1180.0, "cust": 1428.0}        # 4x content height of the standing pose 1 on each sheet
meta = {}
for name, m in src.items():
    im = Image.open(f"sprites/{name}.png").convert("RGBA")
    who = name.split("_")[0]
    s = lib.STD_H / STAND[who]                     # display scale for a 1000 px tall character
    st, pad = lib.sticker(im, lib.STICKER_PX / s, 4.0 / s, 6.0 / s)
    st.save(f"sprites_st/{name}.png")
    meta[name] = {"w": im.width, "h": im.height, "pad": pad, "cell_h": m["cell"][1] * 4 / 4 * 1.0, "stand_h": STAND[who]}
    # cell_h is in original sheet px; display limit is 5x that
json.dump(meta, open("sprites_st/meta.json", "w"), indent=1)
print(len(meta), "sticker sprites")
