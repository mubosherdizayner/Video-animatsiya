# Render frames (multiprocessing) -> ffmpeg h264; "stills" mode for spot checks.
import sys, os, time, subprocess
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenes as SC
from common import W, H, FPS

def _work(i):
    return i, SC.render_frame(i).tobytes()

def main(out_video, procs=4):
    idx = list(range(SC.N_FRAMES))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS), out_video]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with Pool(procs) as pool:
        for n, (i, b) in enumerate(pool.imap(_work, idx, chunksize=3)):
            p.stdin.write(b)
            if n % 90 == 0: print(f"frame {n}/{len(idx)}  {time.time() - t0:.0f}s", flush=True)
    p.stdin.close(); p.wait()
    print("done", round(time.time() - t0), "s")

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
        for tok in sys.argv[3].split(","):
            f = int(round(float(tok[:-1]) * FPS)) if tok.endswith("s") else int(tok)
            t0 = time.time()
            SC.render_frame(f).save(os.path.join(outdir, f"f{f:04d}.png"))
            print("saved", f, "scene", SC.scene_at(f), f"{time.time() - t0:.2f}s", flush=True)
    else:
        main(sys.argv[1])
