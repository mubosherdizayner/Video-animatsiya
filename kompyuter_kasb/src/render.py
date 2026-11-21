# Frame renderer: scene world + grain/vignette + headline + subtitles -> ffmpeg (h264, yuv420p, 30 fps).
import sys, os, time, subprocess
from multiprocessing import Pool
import numpy as np
import skia
from common import *
import world as WD
import scenes as SC
import text as TX


def render_frame(i):
    k = SC.scene_at(i)
    surf = SC.render_scene(i)
    c = surf.getCanvas()
    WD.overlays(c, grain=True, vignette=0.24 if k not in SC.TEXT_LIGHT else 0.3)
    TX.draw_headline(c, k, i - SC.SC_FRAME[k])
    TX.draw_subtitle(c, i)
    return surf


def frame_rgb(i):
    surf = render_frame(i)
    a = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    return np.ascontiguousarray(a[:, :, :3])


def _work(i):
    return i, frame_rgb(i).tobytes()


def main(out_video, procs=4):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-movflags", "+faststart", out_video]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with Pool(procs) as pool:
        for n, (i, b) in enumerate(pool.imap(_work, range(SC.N_FRAMES), chunksize=4)):
            p.stdin.write(b)
            if n % 100 == 0: print(f"frame {n}/{SC.N_FRAMES}  {time.time() - t0:.1f}s", flush=True)
    p.stdin.close(); p.wait()
    print("video done", time.time() - t0, "frames", SC.N_FRAMES)


if __name__ == "__main__":
    if sys.argv[1] == "stills":
        outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
        for f in [int(x) for x in sys.argv[3].split(",")]:
            render_frame(f).makeImageSnapshot().save(os.path.join(outdir, f"f{f:04d}.png"), skia.kPNG)
            print("saved", f, "scene", SC.scene_at(f))
    else:
        main(sys.argv[1])
