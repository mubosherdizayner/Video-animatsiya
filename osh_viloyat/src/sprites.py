# Cut every pose from the two character sheets, remove the light-grey background, keep the dark outline.
# Output: ../build/sprites/s{sheet}_r{row}c{col}.png (RGBA, upscaled x3) + meta.json
import numpy as np, sys, os, json
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "build", "sprites")
os.makedirs(OUT, exist_ok=True)
SHEETS = {1: ("sheet_1.png", 4, 3), 2: ("sheet_2.png", 4, 2)}
TOL = 16
UP = 3


def segments(p, thr, minlen=3):
    on = p > thr; segs = []; i = 0; n = len(p)
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]: j += 1
            if j - i >= minlen: segs.append([i, j])
            i = j
        else: i += 1
    return segs


def merge_to(segs, k):
    segs = [list(s) for s in segs]
    while len(segs) > k:
        gaps = [segs[i + 1][0] - segs[i][1] for i in range(len(segs) - 1)]
        i = int(np.argmin(gaps)); segs[i] = [segs[i][0], segs[i + 1][1]]; del segs[i + 1]
    return segs


def bg_model(im):
    """smooth background estimate (the sheet has a faint vignette): median of a coarse grid of border-ish samples"""
    h, w, _ = im.shape
    small = np.asarray(Image.fromarray(im.astype(np.uint8)).resize((w // 16, h // 16), Image.BOX)).astype(np.float32)
    # replace character pixels with neighbours via iterative median of "grey-ish" pixels
    g = small.mean(2); sat = small.max(2) - small.min(2)
    ok = (sat < 8) & (g > 200) & (g < 240)
    est = np.where(ok[..., None], small, np.nan)
    for _ in range(30):
        m = np.isnan(est[..., 0])
        if not m.any(): break
        pad = np.pad(est, ((1, 1), (1, 1), (0, 0)), constant_values=np.nan)
        nb = np.stack([pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]], 0)
        fill = np.nanmean(nb, 0)
        est[m] = fill[m]
    est = np.nan_to_num(est, nan=220.0)
    est = ndi.gaussian_filter(est, (2, 2, 0))
    return np.asarray(Image.fromarray(np.clip(est, 0, 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.int16)


meta = {}
for sid, (fn, nc, nr) in SHEETS.items():
    im = np.asarray(Image.open(os.path.join(ASSETS, fn)).convert("RGB")).astype(np.int16)
    bg = bg_model(im)
    d = np.abs(im - bg).max(2)
    fg = d > TOL
    rs = merge_to(segments(fg.mean(1), 0.002), nr)
    for ri, (r0, r1) in enumerate(rs, 1):
        band = fg[r0:r1]
        cs = merge_to(segments(band.mean(0), 0.0, 2), nc)
        for ci, (c0, c1) in enumerate(cs, 1):
            P = 8
            y0, y1 = max(r0 - P, 0), min(r1 + P, im.shape[0]); x0, x1 = max(c0 - P, 0), min(c1 + P, im.shape[1])
            cell = im[y0:y1, x0:x1]; dd = d[y0:y1, x0:x1]
            near = dd <= TOL
            # background candidates: neutral light pixels (grey sheet + the faint light halo around outlines)
            cf = cell.astype(np.int16)
            sat = cf.max(2) - cf.min(2); gray = cf.mean(2)
            cand = (near | ((sat < 20) & (gray > 182) & (gray < 249)))
            lab, n = ndi.label(cand)
            border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
            bgm = np.isin(lab, list(border))
            # enclosed holes of grey background (gap between arm and body)
            if n:
                sizes = ndi.sum(np.ones_like(dd), lab, index=np.arange(1, n + 1))
                for li, sz in enumerate(sizes, 1):
                    if li in border or sz < 25: continue
                    m = lab == li
                    flat = (dd[m] <= 9).mean()
                    if np.median(gray[m]) < 240 and flat > 0.45:
                        bgm |= m
            # drop antialias fringe, keep big components only
            bgg = ndi.binary_dilation(bgm, iterations=1)
            keep = ~bgg
            labk, nk = ndi.label(keep)
            if nk > 1:
                szk = ndi.sum(np.ones_like(dd), labk, index=np.arange(1, nk + 1))
                big = szk.max()
                for li, sz in enumerate(szk, 1):
                    if sz < max(30, big * 0.002): keep[labk == li] = False
            keep = ndi.binary_fill_holes(keep) & ~bgg | keep
            # soft edge: blend alpha by distance to bg colour on the fringe
            a8 = Image.fromarray((keep * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
            rgba = np.dstack([cell.astype(np.uint8), np.asarray(a8)])
            spr = Image.fromarray(rgba, "RGBA")
            bb = spr.getbbox()
            spr = spr.crop((max(bb[0] - 4, 0), max(bb[1] - 4, 0), min(bb[2] + 4, spr.width), min(bb[3] + 4, spr.height)))
            ow, oh = spr.size
            up = spr.convert("RGBa").resize((ow * UP, oh * UP), Image.LANCZOS).convert("RGBA")
            rgb = up.convert("RGB").filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2))
            al = up.getchannel("A").filter(ImageFilter.UnsharpMask(radius=1.5, percent=80, threshold=0))
            up = Image.merge("RGBA", (*rgb.split(), al))
            name = f"s{sid}_r{ri}c{ci}"
            up.save(os.path.join(OUT, name + ".png"))
            meta[name] = {"cell": [int(x1 - x0), int(y1 - y0)], "orig": [ow, oh], "up": [ow * UP, oh * UP],
                          "sheet_box": [int(x0 + bb[0]), int(y0 + bb[1]), int(x0 + bb[2]), int(y0 + bb[3])]}
            print(name, meta[name]["orig"])
json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)
print(len(meta), "sprites")
