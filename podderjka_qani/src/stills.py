# Render selected frames to PNG (and an optional contact sheet) for checks.
#   python3 stills.py OUTDIR 0,30,1139        (frame numbers, or seconds with an "s" suffix)
#   python3 stills.py OUTDIR scenes            (middle frame of every scene + sheet)
import sys, os, time
from multiprocessing import Pool
from PIL import Image
import scenes as SC
from script_data import SCENES
from common import FPS

def _one(args):
    f, out = args
    t0 = time.time()
    im = SC.render_frame(f)
    p = os.path.join(out, f"f{f:04d}.png"); im.save(p)
    return f, p, time.time() - t0

def main():
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    spec = sys.argv[2]
    if spec == "scenes" or spec.startswith("scenes:"):
        ids = [int(x) for x in spec.split(":")[1].split("-")] if ":" in spec else None
        fr = []
        for s in SCENES:
            if ids and not (ids[0] <= s["id"] <= ids[-1]): continue
            fr.append((s["f0"] + s["f1"]) // 2)
    else:
        fr = [int(round(float(x[:-1]) * FPS)) if x.endswith("s") else int(x) for x in spec.split(",")]
    with Pool(min(4, len(fr))) as pool:
        res = pool.map(_one, [(f, out) for f in fr])
    for f, p, dt in res: print(f, p, f"{dt:.2f}s")
    if len(res) > 1:
        ims = [Image.open(p).resize((270, 480), Image.LANCZOS) for _, p, _ in res]
        cols = min(5, len(ims)); rows = (len(ims) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 270, rows * 480), (255, 255, 255))
        for i, im in enumerate(ims): sheet.paste(im, ((i % cols) * 270, (i // cols) * 480))
        sheet.save(os.path.join(out, "sheet.png"))

if __name__ == "__main__":
    main()
