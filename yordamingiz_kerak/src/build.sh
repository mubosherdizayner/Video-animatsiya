#!/usr/bin/env bash
# Rebuild the video. VIDEO_IN must hold voice.mp3 and frames/ (the 23 uploaded frames, unzipped);
# VIDEO_WORK is a scratch folder. Needs: ffmpeg, faster-whisper (large-v3), transformers+torch (MMS aligner).
set -euo pipefail
SRC=$(cd "$(dirname "$0")" && pwd)
: "${VIDEO_IN:?}"; : "${VIDEO_WORK:?}"; : "${WHISPER_MODEL:?}"; : "${MMS_MODEL:?}"
cd "$VIDEO_WORK"
ffmpeg -v error -y -i "$VIDEO_IN/voice.mp3" -ac 1 -ar 16000 -f f32le v16.f32
python3 "$SRC/transcribe.py" "$WHISPER_MODEL" v16.f32 words_raw.json            # faster-whisper word timestamps
python3 "$SRC/align_mms.py" "$SRC" "$MMS_MODEL" v16.f32 words_mms.json         # script words, CTC forced alignment
python3 "$SRC/timing.py" "$VIDEO_WORK"                                         # energy refinement, scenes, lip-sync
python3 "$SRC/sfx.py" "$VIDEO_WORK" "$VIDEO_IN/voice.mp3" mix.wav               # synthesized sfx, ducking, loudness
python3 "$SRC/render.py" video video_silent.mp4                                 # frames -> h264
ffmpeg -v error -y -i video_silent.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 \
       -movflags +faststart -shortest final.mp4
python3 "$SRC/qa.py" "$VIDEO_WORK" final.mp4 "$VIDEO_IN/voice.mp3"
