#!/usr/bin/env bash
# Full pipeline: timestamps -> alignment -> render -> sfx mix -> mux -> QA
set -euo pipefail
cd "$(dirname "$0")/src"
WHISPER=${WHISPER_MODEL:-/tmp/claude-0/models/large-v3}   # Systran/faster-whisper-large-v3
ALIGNER=${ALIGNER_MODEL:-/tmp/claude-0/models/mms-fa}     # MahmoudAshraf/mms-300m-1130-forced-aligner
mkdir -p ../build
if [ "${SKIP_TIMING:-0}" != "1" ]; then
  python3 transcribe.py "$WHISPER" ../assets/voice.mp3 words_raw.json
  python3 align.py words_raw.json ../assets/voice.mp3 timing_whisper.json
  python3 fa.py "$ALIGNER" ../assets/voice.mp3 timing_whisper.json timing.json
fi
python3 render.py ../build/video_noaudio.mp4
python3 sfx.py ../build/mix.wav sfx_stats.json
ffmpeg -v error -y -i ../build/video_noaudio.mp4 -i ../build/mix.wav -map 0:v -map 1:a -c:v copy \
  -c:a aac -b:a 192k -movflags +faststart ../sartarosh_jarroh.mp4
python3 qa.py ../sartarosh_jarroh.mp4 ../build/qa
