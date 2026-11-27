"""Mouth states for lip-sync.
Each scene has two source frames: Variant 1 (mouth closed) and Variant 2 (mouth open). They are
different compositions, so the scene keeps ONE of them as its picture (the 'base') and the other
mouth state is made by taking the mouth from the other variant, aligning it on the face
(eye line + mouth position) and blending it into the base with a feathered ellipse and a smooth
colour-correction field. Nothing is redrawn: every pixel comes from the user's frames."""
import json, math, os, sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(HERE, "landmarks.json")))
TUNE = {"06": dict(mx=0.9), "08": dict(mx=0.9), "11": dict(mx=0.8), "03": dict(my=1.15), "10": dict(my=0.86, cy=-2, fe=0.2, ab=-8)}

def transplant(B, D, lb, ld, open_hw_hh_base, t):
    """B: base RGB float array, D: donor PIL image, lb/ld: [eyeL, eyeR, mouth] landmarks."""
    (bl, br, bm), (dl, dr, dm) = lb, ld
    bmid = np.add(bl, br) / 2; dmid = np.add(dl, dr) / 2
    bm = np.array(bm, float); dm = np.array(dm, float)
    bm_mask = bm.copy(); bm = bm + np.array([0.0, t.get("ab", 0.0)])  # closed lip line sits at the upper lip
    s_v = np.linalg.norm(bm - bmid) / np.linalg.norm(dm - dmid)
    s_e = np.linalg.norm(np.subtract(br, bl)) / np.linalg.norm(np.subtract(dr, dl))
    s = t.get("scale", 0.5 * (s_v + s_e))
    th = math.atan2(br[1] - bl[1], br[0] - bl[0]) - math.atan2(dr[1] - dl[1], dr[0] - dl[0])
    c, si = math.cos(-th) / s, math.sin(-th) / s
    coeffs = (c, -si, dm[0] - (c * bm[0] - si * bm[1]), si, c, dm[1] - (si * bm[0] + c * bm[1]))
    Wd, Hd = D.size
    Dw = np.asarray(D.transform((Wd, Hd), Image.AFFINE, coeffs, Image.BICUBIC)).astype(np.float32)
    ed = np.linalg.norm(np.subtract(br, bl))
    hw, hh = open_hw_hh_base
    ax = (hw + 0.16 * ed) * t.get("mx", 1.0); ay = (hh + 0.14 * ed) * t.get("my", 1.0)
    H, W = B.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = ((xx - bm_mask[0]) / ax) ** 2 + ((yy - bm_mask[1] - t.get("cy", 0)) / ay) ** 2
    mask = np.clip((1 - r) / t.get("fe", 0.35), 0, 1)
    lumB = B.mean(2); lumD = Dw.mean(2)
    wgt = ((r > 0.9) & (r < 2.2) & (lumB > 110) & (lumD > 110)).astype(np.float32)
    sig = 0.22 * ed
    den = gaussian_filter(wgt, sig) + 1e-6
    field = np.stack([gaussian_filter((B[..., k] - Dw[..., k]) * wgt, sig) / den for k in range(3)], -1)
    Dc = np.clip(Dw + field, 0, 255)
    return B * (1 - mask[..., None]) + Dc * mask[..., None], s

def states(k, base, paths):
    """Return (closed, open) PIL images in source resolution for scene frame key k."""
    V = {v: Image.open(paths[v]).convert("RGB") for v in "12"}
    t = TUNE.get(k, {})
    hw, hh = L[k]["dm"]            # open-mouth half size, measured in Variant 2
    other = "2" if base == "1" else "1"
    Bimg = V[base]
    B = np.asarray(Bimg).astype(np.float32)
    lb, ld = L[k][base], L[k][other]
    if base == "1":
        # open mouth (from V2) is scaled into V1: size in base coords = hw * scale
        _, s = transplant(B, V[other], lb, ld, (0, 0), t)
        out, _ = transplant(B, V[other], lb, ld, (hw * s, hh * s), t)
        made = Image.fromarray(np.clip(out + .5, 0, 255).astype(np.uint8))
        return Bimg, made
    out, _ = transplant(B, V[other], lb, ld, (hw, hh), t)
    made = Image.fromarray(np.clip(out + .5, 0, 255).astype(np.uint8))
    return made, Bimg
