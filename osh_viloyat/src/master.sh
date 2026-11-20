#!/usr/bin/env bash
# master the mix to -14 LUFS integrated (true peak <= -1 dBTP) and mux with the rendered video
set -euo pipefail
RAW=$1; VID=$2; OUT=$3
TMP=$(dirname "$OUT")/_lim.wav
ffmpeg -v error -y -i "$RAW" -af "alimiter=limit=0.708:attack=5:release=60:level=disabled" -ar 48000 "$TMP"
J=$(ffmpeg -hide_banner -nostats -i "$TMP" -af loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
mi=$(echo "$J" | python3 -c "import sys,json;print(json.load(sys.stdin)['input_i'])")
mtp=$(echo "$J" | python3 -c "import sys,json;print(json.load(sys.stdin)['input_tp'])")
mlra=$(echo "$J" | python3 -c "import sys,json;print(json.load(sys.stdin)['input_lra'])")
mth=$(echo "$J" | python3 -c "import sys,json;print(json.load(sys.stdin)['input_thresh'])")
off=$(echo "$J" | python3 -c "import sys,json;print(json.load(sys.stdin)['target_offset'])")
ffmpeg -v error -y -i "$VID" -i "$TMP" -map 0:v:0 -map 1:a:0 -c:v copy \
  -af "loudnorm=I=-14:TP=-1.0:LRA=11:measured_I=$mi:measured_TP=$mtp:measured_LRA=$mlra:measured_thresh=$mth:offset=$off:linear=true,aresample=48000" \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart "$OUT"
rm -f "$TMP"
