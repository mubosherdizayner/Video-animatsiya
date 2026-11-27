#!/usr/bin/env bash
# Full pipeline: voice-over + frame_01..22.png -> galati_ishlar_ep2.mp4
# usage: run_all.sh voiceover.mp3 frames_dir whisper_model_dir work_dir
set -euo pipefail
VO="$1"; FR="$2"; MODEL="$3"; WK="$4"; SRC="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$WK"
missing=""
[ -f "$VO" ] || missing="$missing $VO"
for i in $(seq -w 1 22); do [ -f "$FR/frame_$i.png" ] || missing="$missing frame_$i.png"; done
if [ -n "$missing" ]; then echo "MISSING:$missing"; exit 1; fi
python3 "$SRC/prep.py" "$VO" "$WK/vo.wav"                                   # decode, trim lead-in > 0.3 s
python3 "$SRC/transcribe.py" "$MODEL" "$WK/vo.wav" "$WK/words_whisper.json"  # faster-whisper word timestamps (uz)
python3 "$SRC/timing.py" "$WK/vo.wav" "$WK/words_whisper.json" "$WK"         # 8 clips, word times, scene timeline
python3 "$SRC/audio.py" "$WK/vo.wav" "$WK/timing.json" "$WK/audio"           # voice + beds + sfx + music mix
python3 "$SRC/render.py" "$FR" "$WK/timing.json" "$WK/video.mp4"             # frames, camera, overlays, subtitles
ffmpeg -hide_banner -loglevel error -y -i "$WK/video.mp4" -i "$WK/audio/mix.wav" -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 192k -ar 48000 -movflags +faststart "$WK/galati_ishlar_ep2.mp4"
python3 "$SRC/qa.py" "$WK/galati_ishlar_ep2.mp4" "$WK/timing.json" "$FR" "$WK/audio" "$WK/video_textboxes.json" "$WK/vo.wav" "$WK/qa"
