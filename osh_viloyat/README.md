# «Eng zoʻr osh qaysi viloyatniki?» — 9:16 animated short

`eng_zor_osh.mp4`: 1080×1920, 30 fps, H.264 yuv420p + AAC, length = voice-over (40.28 s), −14 LUFS.

Every frame is drawn in code. The hero comes only from crops of the two character sheets. Props, backgrounds, text, SFX and music are all generated in code.

## Pipeline (`src/build.sh`)
| step | file | what it does |
|---|---|---|
| poses | `sprites.py` | crops all 20 grid cells from `assets/sheet_1.png` (3×4) and `assets/sheet_2.png` (2×4); removes the light-grey background and the light halo around the outline, including grey holes between arm and body; keeps the dark outline |
| timestamps | `transcribe.py` → `align.py` (+ `ctc_align.py`) | faster-whisper large-v3 (`language="uz"`, `word_timestamps=True`), then a DP alignment to the **script** words (subtitles always use the script text). Onsets are tightened with MMS CTC forced alignment (ONNX) and snapped to energy pauses/dips. Fallback: split sentences at energy pauses and spread words by character count |
| frames | `scenes.py`, `props.py`, `lib.py`, `render.py` | 14 scenes, a camera (scale / pan / tilt) over a world canvas with margin, on-screen text (pop-in), the logo in scene 14, karaoke subtitles (current word in yellow) |
| audio | `audio.py`, `master.sh` | soft synthesized SFX (≈ −20 dB under the voice), doira + plucked dutor loop (≈ −27 LU under the voice, cuts out for 0.5 s at scene 8, warmer in scene 9, 18 bars = exact loop length), both ducked under speech; limiter + two-pass loudnorm to −14 LUFS |
| QA | `qa.py` | writes `build/qa/qa_results.json` plus check frames |

Fonts: Nunito Black (on-screen text and subtitles), with Noto Sans Bold as fallback; both are OFL. The Uzbek `ʻ` (U+02BB) is drawn with tightened side bearings.
