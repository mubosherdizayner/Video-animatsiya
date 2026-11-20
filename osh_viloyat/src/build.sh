#!/usr/bin/env bash
# Full pipeline: poses -> timestamps -> frames -> audio -> master/mux -> QA
# usage: src/build.sh <voice.mp3> <work_dir> [whisper_model_dir] [mms_onnx_model]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(dirname "$HERE")
VOICE=$1; WORK=$2; WHISPER=${3:-}; MMS=${4:-}
mkdir -p "$WORK" "$ROOT/build"
cd "$HERE"

# 1) cut all poses from the two sheets (grey background removed, outline kept)
python3 sprites.py "$ROOT/build/sprites"

# 2) audio prep (no leading-silence trim needed: speech starts at 0.045 s < 0.3 s)
ffmpeg -v error -y -i "$VOICE" -ac 1 -ar 48000 "$WORK/voice48.wav"
ffmpeg -v error -y -i "$VOICE" -ac 1 -ar 16000 -f f32le "$WORK/voice16.f32"
python3 -c "import wave;w=wave.open('$WORK/voice48.wav');print(w.getnframes()/w.getframerate())" > audio_dur.txt
python3 - "$WORK/voice48.wav" "$ROOT/build/voice_db.npy" <<'EOF'
import sys, wave, numpy as np
w = wave.open(sys.argv[1]); sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32768.
hop, win = int(0.005 * sr), int(0.010 * sr)
n = (len(x) - win) // hop
np.save(sys.argv[2], np.array([10 * np.log10(np.mean(x[i * hop:i * hop + win] ** 2) + 1e-12) for i in range(n)]))
EOF

# 3) word timestamps: faster-whisper (uz, word_timestamps) -> script alignment -> CTC forced-alignment + energy refinement
if [ -n "$WHISPER" ]; then python3 transcribe.py "$WHISPER" "$WORK/voice16.f32" words_raw.json; fi
if [ -n "$MMS" ]; then python3 ctc_align.py "$MMS" "$WORK/voice16.f32" ctc_words.json; fi
python3 align.py words_raw.json "$ROOT/build/voice_db.npy" words.json ctc_words.json

# 4) frames, 5) audio, 6) master + mux
python3 render.py "$ROOT/build/video_noaudio.mp4"
python3 audio.py "$WORK/voice48.wav" "$ROOT/build/mix_raw.wav" "$ROOT/build/stem"
./master.sh "$ROOT/build/mix_raw.wav" "$ROOT/build/video_noaudio.mp4" "$ROOT/eng_zor_osh.mp4"

# 7) QA
python3 qa.py "$ROOT/eng_zor_osh.mp4" "$ROOT/build/qa" "$ROOT/build/stem"
