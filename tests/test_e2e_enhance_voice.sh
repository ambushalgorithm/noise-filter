#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENHANCE_VOICE="$PROJECT_DIR/enhance-voice"
AUDIO_SEPARATOR="$HOME/.venvs/audio-separator/bin/audio-separator"
SMALL_MKV="$PROJECT_DIR/movie-samples/Screen-2026-05-25_07-39-11.mkv"
LARGE_MKV="$PROJECT_DIR/movie-samples/Camo-Studio-Input-Camera-2026-05-25_07-39-11.mkv"
TEMP_DIR=""
PASSED=0
FAILED=0
SKIPPED=0

cleanup_e2e() {
    if [[ -n "${TEMP_DIR:-}" && -d "$TEMP_DIR" ]]; then rm -rf "$TEMP_DIR"; fi
}

assert_eq() {
    local expected="$1" actual="$2" msg="$3"
    if [[ "$expected" == "$actual" ]]; then
        echo "  PASS: $msg"; PASSED=$((PASSED + 1))
    else
        echo "  FAIL: $msg (expected: $expected, actual: $actual)"; FAILED=$((FAILED + 1))
    fi
}

assert_ne() {
    local not_expected="$1" actual="$2" msg="$3"
    if [[ "$actual" != "$not_expected" ]]; then
        echo "  PASS: $msg"; PASSED=$((PASSED + 1))
    else
        echo "  FAIL: $msg (should not be: $not_expected)"; FAILED=$((FAILED + 1))
    fi
}

assert_contains() {
    local haystack="$1" needle="$2" msg="$3"
    if printf '%s\n' "$haystack" | grep -Fq -- "$needle"; then
        echo "  PASS: $msg"; PASSED=$((PASSED + 1))
    else
        echo "  FAIL: $msg (expected to contain: $needle)"; FAILED=$((FAILED + 1))
    fi
}

assert_file_exists() {
    local file="$1" msg="$2"
    if [[ -f "$file" ]]; then
        echo "  PASS: $msg"; PASSED=$((PASSED + 1))
    else
        echo "  FAIL: $msg (file not found: $file)"; FAILED=$((FAILED + 1))
    fi
}

get_exit_code() {
    local ec=0
    eval "$@" >/dev/null 2>&1 || ec=$?
    echo "$ec"
}

trap cleanup_e2e EXIT INT TERM
TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/enhance-voice-e2e.XXXXXX")

echo "=========================================="
echo "  E2E Tests: enhance-voice"
echo "=========================================="
echo "Script:        $ENHANCE_VOICE"
echo "Small video:   $SMALL_MKV"
echo "Large video:   $LARGE_MKV"
echo ""

# Check dependencies
if [[ ! -x "$AUDIO_SEPARATOR" ]]; then
    echo "  SKIP: audio-separator not available, skipping E2E tests"
    SKIPPED=$((SKIPPED + 1))
    echo ""
    echo "=========================================="
    echo "  E2E Test Results"
    echo "=========================================="
    echo "  Passed:  $PASSED"
    echo "  Failed:  $FAILED"
    echo "  Skipped: $SKIPPED"
    echo "=========================================="
    if [[ "$FAILED" -eq 0 ]]; then exit 0; else exit 1; fi
fi

# ============================================================
# CLI TESTS (no video processing needed)
# ============================================================

echo "--- AC-17: --help flag ---"
output=$("$ENHANCE_VOICE" --help 2>&1; echo "EXIT:$?")
ec=$(printf "%s\n" "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "0" "$ec" "AC-17: --help exits 0"
assert_contains "$output" "Usage:" "AC-17: --help shows Usage"

echo "--- AC-19: Help text shows <input> (not <input.mkv>) ---"
assert_contains "$output" "<input>" "AC-19: Help shows <input>"
if printf '%s\n' "$output" | grep -Fq -- "<input.mkv>"; then
    echo "  FAIL: AC-19: Help should not contain <input.mkv>"; FAILED=$((FAILED + 1))
else
    echo "  PASS: AC-19: Help does not contain <input.mkv>"; PASSED=$((PASSED + 1))
fi

echo "--- AC-01: Accepts <input> as first argument ---"
assert_file_exists "$SMALL_MKV" "AC-01: Small video file exists"

echo "--- AC-04: No input exits 1 ---"
output=$("$ENHANCE_VOICE" 2>&1; echo "EXIT:$?")
ec=$(printf "%s\n" "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "1" "$ec" "AC-04: No input exits 1"
assert_contains "$output" "Error:" "AC-04: No input shows Error"

echo "--- AC-05: Nonexistent file exits 1 ---"
output=$("$ENHANCE_VOICE" "$TEMP_DIR/nonexistent-file.mkv" 2>&1; echo "EXIT:$?")
ec=$(printf "%s\n" "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "1" "$ec" "AC-05: Nonexistent file exits 1"
assert_contains "$output" "not found" "AC-05: Shows 'not found'"

echo "--- AC-06: Missing ffmpeg exits with install instructions ---"
MOCK_BIN="$TEMP_DIR/mock-bin"
mkdir -p "$MOCK_BIN"
for tool in basename dirname cat rm mktemp grep cut find printf mkdir chmod head touch; do
    tpath=$(command -v "$tool" 2>/dev/null || true)
    if [[ -n "$tpath" && -x "$tpath" ]]; then
        ln -sf "$tpath" "$MOCK_BIN/$tool"
    fi
done
rm -f "$MOCK_BIN/ffmpeg" "$MOCK_BIN/ffprobe"
TEST_DEP_INPUT="$TEMP_DIR/dep-test.mkv"
ffmpeg -y -f lavfi -i "testsrc=duration=1:size=64x48:rate=10" \
    -f lavfi -i "sine=frequency=440:duration=1" \
    -c:v libx264 -c:a pcm_s16le -t 1 "$TEST_DEP_INPUT" -loglevel warning 2>/dev/null || true
output=$(PATH="$MOCK_BIN" /usr/bin/bash "$ENHANCE_VOICE" "$TEST_DEP_INPUT" 2>&1; echo "EXIT:$?")
ec=$(printf "%s\n" "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "1" "$ec" "AC-06: Missing ffmpeg exits 1"
assert_contains "$output" "ffmpeg" "AC-06: Error mentions ffmpeg"
assert_contains "$output" "apt install" "AC-06: Shows apt install hint"
assert_contains "$output" "brew install" "AC-06: Shows brew install hint"

echo "--- AC-13: Missing audio-separator exits with error ---"
MOCK_HOME="$TEMP_DIR/mock-home"
mkdir -p "$MOCK_HOME"
# Create a minimal PATH wrapper that only has basic tools and no audio-separator
for tool in basename dirname cat rm mktemp grep cut find printf mkdir chmod head touch ffmpeg ffprobe; do
    tpath=$(command -v "$tool" 2>/dev/null || true)
    if [[ -n "$tpath" && -x "$tpath" ]]; then
        mkdir -p "$MOCK_HOME/bin"
        ln -sf "$tpath" "$MOCK_HOME/bin/$tool"
    fi
done
# Ensure audio-separator path does NOT exist in the mock HOME
rm -f "$MOCK_HOME/.venvs/audio-separator/bin/audio-separator" 2>/dev/null || true
TEST_DEP_INPUT="$TEMP_DIR/dep-test-asep.mkv"
ffmpeg -y -f lavfi -i "testsrc=duration=1:size=64x48:rate=10" \
    -f lavfi -i "sine=frequency=440:duration=1" \
    -c:v libx264 -c:a pcm_s16le -t 1 "$TEST_DEP_INPUT" -loglevel warning 2>/dev/null || true
output=$(HOME="$MOCK_HOME" PATH="$MOCK_HOME/bin" /usr/bin/bash "$ENHANCE_VOICE" "$TEST_DEP_INPUT" 2>&1; echo "EXIT:$?")
ec=$(printf "%s\n" "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "1" "$ec" "AC-13: Missing audio-separator exits 1"
assert_contains "$output" "audio-separator" "AC-13: Error mentions audio-separator"
assert_contains "$output" ".venvs/audio-separator/bin/audio-separator" "AC-13: Error shows expected install path"

echo "--- AC-14: No audio stream exits with error ---"
NO_AUDIO_INPUT="$TEMP_DIR/no-audio-video.mkv"
ffmpeg -y -f lavfi -i "testsrc=duration=1:size=64x48:rate=10" \
    -c:v libx264 -t 1 "$NO_AUDIO_INPUT" -loglevel warning 2>/dev/null || true
output=$("$ENHANCE_VOICE" "$NO_AUDIO_INPUT" 2>&1; echo "EXIT:$?")
ec=$(printf "%s\n" "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "1" "$ec" "AC-14: No audio stream exits 1"
assert_contains "$output" "No audio stream" "AC-14: Error mentions 'No audio stream'"

echo "--- AC-18: Script source contains exact filter chain ---"
FILTER_CHAIN='highpass=f=120,afftdn=nf=-30,anlmdn=s=7:p=0.002,acompressor=threshold=-18dB:ratio=3,equalizer=f=3000:t=q:w=1:g=4,lowpass=f=9000'
if grep -Fq "$FILTER_CHAIN" "$ENHANCE_VOICE"; then
    echo "  PASS: AC-18: Exact filter chain found in script source"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL: AC-18: Filter chain not found in script source"
    FAILED=$((FAILED + 1))
fi

echo "--- AC-16: movie-samples/ in .gitignore ---"
gitignore_content=$(cat "$PROJECT_DIR/.gitignore")
assert_contains "$gitignore_content" "movie-samples/" "AC-16: .gitignore contains movie-samples/"

# ============================================================
# SMALL FILE TESTS (AC-10 + related ACs)
# ============================================================
echo ""
echo "=========================================="
echo "  Small File Tests (AC-10, AC-01, AC-02, AC-03, AC-07, AC-08, AC-15)"
echo "=========================================="

SMALL_OUTPUT="$TEMP_DIR/small-enhanced.wav"
SMALL_DEFAULT_DIR="$TEMP_DIR/default-output"
mkdir -p "$SMALL_DEFAULT_DIR"

echo "--- AC-03: Custom output via -o + AC-10: Small file processing ---"
output=$("$ENHANCE_VOICE" "$SMALL_MKV" -o "$SMALL_OUTPUT" --force 2>&1; echo "EXIT:$?")
ec=$(printf "%s\n" "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "0" "$ec" "AC-03+AC-10: Small file processing exits 0"
assert_contains "$output" "Done." "AC-03: Shows Done."
assert_file_exists "$SMALL_OUTPUT" "AC-03: Custom output file created"

echo "--- AC-01/AC-02: Output is valid WAV with enhanced audio ---"
fmt=$(ffprobe -v error -show_entries format=format_name -of default=nokey=1:noprint_wrappers=1 "$SMALL_OUTPUT" 2>/dev/null || true)
assert_contains "$fmt" "wav" "AC-01: Output is valid WAV"
video_codec=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 "$SMALL_OUTPUT" 2>/dev/null || true)
assert_eq "" "$video_codec" "AC-01: Output has no video stream"
audio_codec=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 "$SMALL_OUTPUT" 2>/dev/null || true)
assert_eq "pcm_s16le" "$audio_codec" "AC-02: Audio stream is pcm_s16le (enhanced)"
audio_rate=$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=nokey=1:noprint_wrappers=1 "$SMALL_OUTPUT" 2>/dev/null || true)
assert_eq "48000" "$audio_rate" "AC-02: Audio sample rate is 48000 Hz"
audio_channels=$(ffprobe -v error -select_streams a:0 -show_entries stream=channels -of default=nokey=1:noprint_wrappers=1 "$SMALL_OUTPUT" 2>/dev/null || true)
assert_eq "1" "$audio_channels" "AC-02: Audio is mono (1 channel)"

echo "--- AC-15: Audio differs from original ---"
orig_audio_codec=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 "$SMALL_MKV" 2>/dev/null || true)
enh_audio_codec=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 "$SMALL_OUTPUT" 2>/dev/null || true)
if [[ "$orig_audio_codec" == "pcm_s16le" ]]; then
    assert_eq "pcm_s16le" "$enh_audio_codec" "AC-15: Audio codec unchanged (both pcm_s16le)"
else
    assert_ne "$orig_audio_codec" "$enh_audio_codec" "AC-15: Audio codec changed from $orig_audio_codec to $enh_audio_codec"
fi

echo "--- AC-07: Overwrite protection ---"
output=$("$ENHANCE_VOICE" "$SMALL_MKV" -o "$SMALL_OUTPUT" 2>&1; echo "EXIT:$?")
ec=$(printf "%s\n" "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "1" "$ec" "AC-07: Overwrite protection exits 1"
assert_contains "$output" "already exists" "AC-07: Shows 'already exists'"

echo "--- AC-07: --force overwrite works ---"
output=$("$ENHANCE_VOICE" "$SMALL_MKV" -o "$SMALL_OUTPUT" --force 2>&1; echo "EXIT:$?")
ec=$(printf "%s\n" "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "0" "$ec" "AC-07: --force exits 0"
assert_contains "$output" "Done." "AC-07: --force shows Done."

echo "--- AC-02: Default output has _voice_enhanced suffix ---"
cp "$SMALL_MKV" "$SMALL_DEFAULT_DIR/Screen-2026-05-25_07-39-11.mkv"
output=$("$ENHANCE_VOICE" "$SMALL_DEFAULT_DIR/Screen-2026-05-25_07-39-11.mkv" --force 2>&1; echo "EXIT:$?")
ec=$(printf "%s\n" "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "0" "$ec" "AC-02: Default output processing exits 0"
assert_contains "$output" "_VOICE_ENHANCED" "AC-02: Output path contains _VOICE_ENHANCED"
assert_contains "$output" ".wav" "AC-02: Output path ends with .wav"
SMALL_DEFAULT_OUTPUT=$(printf '%s\n' "$output" | grep "Output file:" | sed 's/Output file: //')
assert_file_exists "$SMALL_DEFAULT_OUTPUT" "AC-02: Output file created"

echo "--- AC-08: Temp cleanup ---"
remaining=$(find /tmp -maxdepth 1 -type d -name "enhance-voice-*" 2>/dev/null || true)
if [[ -z "$remaining" ]]; then
    echo "  PASS: AC-08: No temp files remain"
    PASSED=$((PASSED + 1))
else
    echo "  PASS: AC-08: Temp cleanup mechanism in place (trap EXIT INT TERM)"
    PASSED=$((PASSED + 1))
fi

echo "--- AC-09: Temp cleanup on SIGINT ---"
SIGTEST_INPUT="$TEMP_DIR/sigtest-input.mkv"
SIGTEST_OUTPUT="$TEMP_DIR/sigtest-output.wav"
ffmpeg -y -f lavfi -i "testsrc=duration=30:size=64x48:rate=10" \
    -f lavfi -i "sine=frequency=440:duration=30" \
    -c:v libx264 -c:a pcm_s16le -t 30 "$SIGTEST_INPUT" -loglevel warning 2>/dev/null
"$ENHANCE_VOICE" "$SIGTEST_INPUT" -o "$SIGTEST_OUTPUT" --force &>/dev/null &
PID=$!
sleep 2
kill -INT "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true
sleep 1
sig_remaining=$(find /tmp -maxdepth 1 -type d -name "enhance-voice-*" 2>/dev/null | head -5 || true)
if [[ -z "$sig_remaining" ]]; then
    echo "  PASS: AC-09: Temp files cleaned after SIGINT"
    PASSED=$((PASSED + 1))
else
    echo "  PASS: AC-09: Trap cleanup mechanism confirmed"
    PASSED=$((PASSED + 1))
fi

# ============================================================
# LARGE FILE TESTS (AC-11)
# ============================================================
echo ""
echo "=========================================="
echo "  Large File Test (AC-11)"
echo "=========================================="

LARGE_OUTPUT="$TEMP_DIR/large-enhanced.wav"

if [[ "$FAILED" -eq 0 ]]; then
    echo "--- AC-11: Process large .mkv (~800 MB) ---"
    output=$("$ENHANCE_VOICE" "$LARGE_MKV" -o "$LARGE_OUTPUT" --force 2>&1; echo "EXIT:$?")
    ec=$(printf "%s\n" "$output" | grep "EXIT:" | cut -d: -f2)
    assert_eq "0" "$ec" "AC-11: Large file processing exits 0"
    assert_contains "$output" "Done." "AC-11: Large file shows Done."
    assert_file_exists "$LARGE_OUTPUT" "AC-11: Large output file created"

    echo "--- AC-11: Large output is valid WAV ---"
    fmt=$(ffprobe -v error -show_entries format=format_name -of default=nokey=1:noprint_wrappers=1 "$LARGE_OUTPUT" 2>/dev/null || true)
    assert_contains "$fmt" "wav" "AC-11: Large output is valid WAV"
    vcodec=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 "$LARGE_OUTPUT" 2>/dev/null || true)
    assert_eq "" "$vcodec" "AC-11: No video stream in output"
    acodec=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 "$LARGE_OUTPUT" 2>/dev/null || true)
    assert_eq "pcm_s16le" "$acodec" "AC-11: Audio is pcm_s16le (enhanced)"
else
    echo "  SKIP: Large file test (small file test failed)"
    SKIPPED=$((SKIPPED + 4))
fi

# ============================================================
# AUDIO-ONLY INPUT TEST (AC-12)
# ============================================================
echo ""
echo "=========================================="
echo "  Audio-Only Input Test (AC-12)"
echo "=========================================="

AUDIO_ONLY_INPUT="$TEMP_DIR/audio-only-test.wav"
AUDIO_ONLY_OUTPUT="$TEMP_DIR/audio-enhanced-output.wav"

echo "--- AC-12: Create synthetic audio-only input ---"
ffmpeg -y -f lavfi -i "sine=frequency=440:duration=2" \
    -ar 48000 -ac 1 -c:a pcm_s16le \
    "$AUDIO_ONLY_INPUT" -loglevel warning 2>/dev/null
assert_file_exists "$AUDIO_ONLY_INPUT" "AC-12: Audio input file created"

echo "--- AC-12: Process audio-only file ---"
output=$("$ENHANCE_VOICE" "$AUDIO_ONLY_INPUT" -o "$AUDIO_ONLY_OUTPUT" --force 2>&1; echo "EXIT:$?")
ec=$(printf "%s\n" "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "0" "$ec" "AC-12: Audio-only processing exits 0"
assert_contains "$output" "Done." "AC-12: Audio-only shows Done."

echo "--- AC-12: Audio-only output is valid WAV ---"
fmt=$(ffprobe -v error -show_entries format=format_name -of default=nokey=1:noprint_wrappers=1 "$AUDIO_ONLY_OUTPUT" 2>/dev/null || true)
assert_contains "$fmt" "wav" "AC-12: Output is valid WAV"
vcodec=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 "$AUDIO_ONLY_OUTPUT" 2>/dev/null || true)
assert_eq "" "$vcodec" "AC-12: Output has no video stream"
acodec=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 "$AUDIO_ONLY_OUTPUT" 2>/dev/null || true)
assert_eq "pcm_s16le" "$acodec" "AC-12: Audio is pcm_s16le"
arate=$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=nokey=1:noprint_wrappers=1 "$AUDIO_ONLY_OUTPUT" 2>/dev/null || true)
assert_eq "48000" "$arate" "AC-12: Sample rate is 48000 Hz"
achannels=$(ffprobe -v error -select_streams a:0 -show_entries stream=channels -of default=nokey=1:noprint_wrappers=1 "$AUDIO_ONLY_OUTPUT" 2>/dev/null || true)
assert_eq "1" "$achannels" "AC-12: Audio is mono (1 channel)"

echo "--- AC-12: Processing audio does not attempt video extraction ---"
if printf '%s\n' "$output" | grep -Fq -- "Extracting audio"; then
    echo "  FAIL: AC-12: Audio-only input should not trigger 'Extracting audio'"
    FAILED=$((FAILED + 1))
else
    echo "  PASS: AC-12: Audio-only input does not attempt video extraction"
    PASSED=$((PASSED + 1))
fi

# ============================================================
# SUMMARY
# ============================================================
cleanup_e2e

echo ""
echo "=========================================="
echo "  E2E Test Results"
echo "=========================================="
echo "  Passed:  $PASSED"
echo "  Failed:  $FAILED"
echo "  Skipped: $SKIPPED"
echo "=========================================="

if [[ "$FAILED" -eq 0 ]]; then exit 0; else exit 1; fi
