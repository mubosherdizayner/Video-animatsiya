# Render all frames (multiprocessing) -> h264 yuv420p, mux with the synthesized SFX (AAC).
import sys, os, time, subprocess
from multiprocessing import Pool
import scenes as SC
from script_data import N_FRAMES
from common import W, H, FPS, BUILD
import sfx

def _work(i):
    return i, SC.render_frame(i).tobytes()

def main(out_mp4, procs=4):
    silent = os.path.join(BUILD, "video_noaudio.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS), "-movflags", "+faststart", silent]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with Pool(procs) as pool:
        for n, (i, b) in enumerate(pool.imap(_work, range(N_FRAMES), chunksize=4)):
            p.stdin.write(b)
            if n % 120 == 0: print(f"frame {n}/{N_FRAMES}  {time.time() - t0:.0f}s", flush=True)
    p.stdin.close(); p.wait()
    wav, k = sfx.build(os.path.join(BUILD, "sfx.wav"))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{N_FRAMES / FPS:.4f}", "-movflags", "+faststart", out_mp4], check=True)
    print("done", round(time.time() - t0), "s ->", out_mp4)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(BUILD, "out.mp4"))
