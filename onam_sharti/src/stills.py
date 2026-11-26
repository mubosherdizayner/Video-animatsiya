import sys
import scenes as SC, timeline as T
import render as R
from PIL import Image
SP = "/tmp/claude-0/-home-user-Video-animatsiya/93682b46-1593-5f43-b77a-7cce588d49e5/scratchpad/"
frames = [int(x) for x in sys.argv[1].split(",")]
name = sys.argv[2]
ims = [Image.fromarray(R.render_frame(f)).resize((540, 960)) for f in frames]
out = Image.new("RGB", (550 * len(ims), 960), "white")
for i, im in enumerate(ims): out.paste(im, (i * 550, 0))
out.save(SP + name + ".png"); print(SP + name + ".png")
