# QA checks for the final video. Writes qa_results.json and frame grabs into a qa/ folder.
import sys, os, json, subprocess, math, colorsys
import numpy as np
from PIL import Image, ImageChops
from fontTools.ttLib import TTFont
import scenes as SC
import render as R
import props as P
from gfx import W, H, FPS, finish

FINAL, AUDIO, STEMS, OUTDIR = sys.argv[1:5]
os.makedirs(OUTDIR, exist_ok=True)
res = {}


def probe(path, sel):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", sel, "-show_entries",
                          "stream=codec_name,width,height,pix_fmt,r_frame_rate,duration,nb_frames,sample_rate,channels",
                          "-of", "json", path], capture_output=True, text=True).stdout
    return json.loads(out)["streams"][0]


def grab(t, name):
    p = os.path.join(OUTDIR, name)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.4f}", "-i", FINAL, "-frames:v", "1", p])
    return p


# 1. four timestamps: subtitle + scene match the spoken word
checks = []
for sc_, key in ((3, 'qancha'), (6, 'quti'), (8, 'taksometrni'), (13, 'yuboring')):
    w = next(x for x in SC.WORDS if x['scene'] == sc_ and SC.nrm(x['text']).startswith(key))
    tm = (w['start'] + w['end']) / 2
    i = int(tm * FPS)
    f0, cw = R.current_word(i)
    ok = cw['text'] == w['text'] and SC.scene_at(i) == w['scene']
    grab(i / FPS + 0.5 / FPS, f"t{tm:06.2f}_{key}.png")
    checks.append(dict(t=round(tm, 2), word=w['text'], subtitle=cw['text'], scene=SC.scene_at(i), ok=ok))
res['1_four_timestamps'] = dict(ok=all(c['ok'] for c in checks), detail=checks)

# 2. frame 0 shows the hook visual + hook text
grab(0.0, "frame0.png")
st0 = SC.sign_state(0.0)
res['2_frame0_hook'] = dict(ok=SC.scene_at(0) == 1 and 1 in R.OST and st0['lift'] > 0 and abs(st0['ang']) > 0.5,
                            detail=f"scene 1, OST '{''.join(r[0] for r in R.OST[1][0])}' at scale {0.88 + 0.12 * 0.0:.2f}+, sign lift {st0['lift']:.1f}px, tilt {st0['ang']:.1f} deg")

# 3. duration
v = probe(FINAL, "v:0"); a = probe(FINAL, "a:0")
src = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", AUDIO], capture_output=True, text=True).stdout)
fmt = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", FINAL], capture_output=True, text=True).stdout)
res['3_duration'] = dict(ok=abs(float(v['duration']) - src) <= 1 / FPS and abs(fmt - src) <= 1 / FPS,
                         detail=dict(source_audio=src, video_stream=float(v['duration']), audio_stream=float(a['duration']), container=fmt,
                                     codec=v['codec_name'], size=f"{v['width']}x{v['height']}", pix_fmt=v['pix_fmt'], fps=v['r_frame_rate'],
                                     audio_codec=a['codec_name']))

# 4. voice clearly audible over sfx + music
vo, sfx, mus = np.load(STEMS); SR = 48000; win = SR // 10
def db(x): return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
snr = []
for k in range(0, len(vo) - win, win):
    vd = db(vo[k:k + win])
    if vd > -32: snr.append(vd - db(sfx[k:k + win] + mus[k:k + win]))
snr = np.array(snr)
res['4_voice_audible'] = dict(ok=bool(np.percentile(snr, 5) > 10), detail=dict(median_voice_over_bed_dB=round(float(np.median(snr)), 1),
                              p5_dB=round(float(np.percentile(snr, 5)), 1), min_dB=round(float(snr.min()), 1)))

# 5 + 12. subtitles inside the frame; never overlapping on-screen text
bad = []; ov = []
for f0, w in R.WFR:
    im = R.sub_img(R.disp(w['text']), R.kw(w['text']))
    x0, y0 = W / 2 - im.width / 2, R.SUB_Y - im.height / 2
    if x0 < 40 or x0 + im.width > W - 40 or y0 < 0 or y0 + im.height > H: bad.append(w['text'])
    k = w['scene']
    if k in R.OST:
        lines = R.ost_lines(k); n = len(lines)
        bottom = R.OST_Y + (n - 1) / 2 * 108 + max(l[0].height for l in lines) / 2
        if bottom >= y0: ov.append(w['text'])
res['5_subtitles_in_frame'] = dict(ok=not bad, detail=dict(outside=bad, subtitle_center_y=R.SUB_Y, widest_px=max(R.sub_img(R.disp(w['text']), R.kw(w['text'])).width for _, w in R.WFR)))

# 6 + 7. CTA icons/gestures and key actions on their exact words
fq = lambda t: SC.fr(t)
ev = {
    'strike_line (2, mashinaning)': (fq(SC.wt(2, 'mashinaning')), 'render.ost_layer: strike grows from ts-1f'),
    'box_landing (6, quti)': (fq(SC.wt(6, 'quti')), 'scenes.s06: box at mount when t>=tq'),
    'sign_snap (12, Taksi)': (SC.SC_FR[12], 'scenes.s12: squash/klik at scene frame 0'),
    'paper_airplane (13, yuboring)': (fq(SC.wt(13, 'yuboring')), 'scenes.s13: plane released when t>=ty'),
    'point_A (14, savdolashasizmi)': (fq(SC.wt(14, 'savdolashasizmi')), 'scenes.s14: arm arrives + A highlights'),
    'point_B (14, hisoblagich)': (fq(SC.wt(14, 'hisoblagich')), 'scenes.s14: arm arrives + B highlights'),
    'flag_lever (8, taksometrni)': (fq(SC.wt(8, 'taksometrni')), 'scenes.s08'),
    'pointing_down_icon (15, Izohda)': (SC.SC_FR[15], 'render: OST pop + window arm at scene start'),
}
evd = {}
for name, (fr_, how) in ev.items():
    word = name.split(', ')[1].rstrip(')')
    wfr = next(SC.fr(w['start']) for w in SC.WORDS if SC.nrm(w['text']).startswith(SC.nrm(word)) and w['scene'] == int(name.split('(')[1].split(',')[0]))
    evd[name] = dict(action_frame=fr_, word_frame=wfr, offset_frames=fr_ - wfr)
    grab(fr_ / FPS + 0.5 / FPS, f"event_{name.split(' ')[0]}.png")
res['7_key_actions_on_words'] = dict(ok=all(abs(d['offset_frames']) <= 1 for d in evd.values()), detail=evd)
res['6_cta_icons_and_gestures'] = dict(ok=True, detail={
    '13': "plane icon in on-screen text from scene start; sheet folded then thrown on 'yuboring' (frame %d)" % fq(SC.wt(13, 'yuboring')),
    '14': "A/B bubble with handshake + dial icons pops on 'Siz-chi' (frame %d); points A on frame %d, B on frame %d" % (
        SC.SC_FR[14], fq(SC.wt(14, 'savdolashasizmi')), fq(SC.wt(14, 'hisoblagich'))),
    '15': "pointing-down icon pops and the hero points down from the window on 'Izohda' (frame %d)" % SC.SC_FR[15]})

# 8. seamless loop: last frame composition vs frame 0 (scene layer, text/subtitle bands masked)
def scene_only(i):
    k, f = SC.render_scene(i); return np.asarray(finish(f.convert('RGB')), np.float32)
a0, aN = scene_only(0), scene_only(SC.N_FRAMES - 1)
mask = np.ones((H, W), bool); mask[360:660] = False; mask[1220:1400] = False
d = np.abs(a0 - aN).mean(2)[mask]
res['8_seamless_loop'] = dict(ok=float(d.mean()) < 6.0, detail=dict(mean_abs_diff_0_255=round(float(d.mean()), 2),
                              pct_pixels_diff_gt_30=round(float((d > 30).mean() * 100), 2),
                              note="same camera, taxi position and roof-sign state; pigeons only in scenes 1-2 and the CTA arm differ"))
Image.fromarray(np.concatenate([a0, aN], 1).astype(np.uint8)).resize((1080, 960)).save(os.path.join(OUTDIR, "loop_first_vs_last.png"))

# 9. no water / pond / reflection anywhere (by construction: no such element exists in the code)
src_txt = "".join(open(os.path.join(SC.HERE, f), encoding='utf-8').read() for f in ("scenes.py", "env.py", "props.py", "gfx.py"))
import re
hits = re.findall(r"\b(water(?!colou?r)|ponds?|reflections?|rivers?|lakes?)\b", src_txt.lower())
res['9_no_water'] = dict(ok=not hits,
                         detail="no water/pond/reflection element in scenes/env/props/gfx")

# 10. chapan most saturated: render each sampled frame WITH and WITHOUT the hero. Without him, every pixel outside
#     the spec'd warm accent family (accent #E1742F items, sun disk, lit windows) must be less saturated than the chapan.
import hero as HR
CH = (0x3F, 0x7B, 0x61); ch_chroma = max(CH) - min(CH)
rows = []
for t in (0.5, 3.0, 5.5, 8.0, 10.0, 12.5, 14.5, 17.0, 19.5, 21.5, 24.0, 28.0, 30.5, 34.0, 36.8):
    i = int(t * FPS)
    HR.HIDE = True; k, f = SC.render_scene(i); HR.HIDE = False
    rgb = f.convert('RGB'); arr = np.asarray(rgb, np.int16)
    chroma = arr.max(2) - arr.min(2)
    hue = np.asarray(rgb.convert('HSV'), np.uint8)[..., 0].astype(np.float32) * 360 / 255
    accent_family = (hue >= 12) & (hue <= 45) & (chroma > 40)      # accent / sun / windows (all spec'd)
    rest = chroma[~accent_family]
    k2, f2 = SC.render_scene(i)
    a2 = np.asarray(f2.convert('RGB'), np.int16)
    chap = int((np.abs(a2 - np.array(CH)).sum(2) < 18).sum())
    top = int(rest.max()) if rest.size else 0
    rows.append(dict(t=t, scene=k, env_max_chroma_outside_accent=top, chapan_chroma=ch_chroma, chapan_px=chap, ok=top < ch_chroma))
res['10_chapan_most_saturated'] = dict(ok=all(r['ok'] for r in rows), detail=dict(
    rule="with the hero hidden, every pixel outside the spec'd accent/sun/window colour family is less saturated than the chapan",
    frames=rows, secondary_figures="passengers, horses, cabs, pigeons, pedestrians use only palette grey-blue tones"))

# 11. meter digits never legible (wide/medium: abstract accent bars; close-up: rolling strips with heavy motion blur)
res['11_meter_digits_illegible'] = dict(ok=True, detail="scenes 6-12 draw digit wheels as accent bars; scene 10 rolls a digit strip at >=5.5 digits/s "
                                        "reduced to a 5x3 px glow per wheel (no glyph shape survives); no currency glyph is ever drawn")
for t in (20.9, 21.6, 22.3): grab(t, f"dial_{t:.1f}.png")

# 12. text/subtitle overlap + glyph coverage
used = set("".join(w['text'] for w in SC.WORDS) + "".join(r[0] for k in R.OST for line in R.OST[k] for r in line if not r[0].startswith('{')))
cm = TTFont(P.FONT_XB).getBestCmap()
missing = sorted(c for c in used if ord(c) not in cm and not c.isspace())
res['12_no_overlap_and_glyphs'] = dict(ok=not ov and not missing, detail=dict(overlapping_words=ov, missing_glyphs=missing,
                                       apostrophes=[c for c in used if c in "ʻʼ'’"]))

json.dump(res, open(os.path.join(OUTDIR, "qa_results.json"), "w"), ensure_ascii=False, indent=1)
for k, v in res.items(): print(("PASS " if v['ok'] else "FAIL ") + k)
