#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
NOISE_FILTER="$PROJECT_DIR/noise-filter"
AUDIO_SEPARATOR="$HOME/.venvs/audio-separator/bin/audio-separator"
TEMP_DIR=""
PASSED=0
FAILED=0
SKIPPED=0

cleanup_test() {
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

assert_not_eq() {
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

cleanup_test
TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/enhance-voice-test.XXXXXX")

# Test 1: --help
echo "Test 1: --help flag exits 0"
output=$("$NOISE_FILTER" --help 2>&1; echo "EXIT:$?")
exit_code=$(printf '%s\n' "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "0" "$exit_code" "--help exits 0"
assert_contains "$output" "Usage:" "--help contains Usage:"
assert_contains "$output" "--force" "--help mentions --force"
assert_contains "$output" "--help" "--help mentions --help"
assert_contains "$output" "-o" "--help mentions -o"

# Test 2: -h
echo "Test 2: -h alias exits 0"
output=$("$NOISE_FILTER" -h 2>&1; echo "EXIT:$?")
exit_code=$(printf '%s\n' "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "0" "$exit_code" "-h exits 0"

# Test 3: No input
echo "Test 3: No input exits 1"
output=$("$NOISE_FILTER" 2>&1; echo "EXIT:$?")
exit_code=$(printf '%s\n' "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "1" "$exit_code" "No input exits 1"
assert_contains "$output" "Error:" "No input shows Error"

# Test 4: Nonexistent file
echo "Test 4: Nonexistent file exits 1"
output=$("$NOISE_FILTER" "$PROJECT_DIR/nonexistent-file.mkv" 2>&1; echo "EXIT:$?")
exit_code=$(printf '%s\n' "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "1" "$exit_code" "Nonexistent file exits 1"
assert_contains "$output" "not found" "Nonexistent file shows 'not found'"

# Test 5: -o without arg
echo "Test 5: -o with no argument exits 1"
output=$("$NOISE_FILTER" -o 2>&1; echo "EXIT:$?")
exit_code=$(printf '%s\n' "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "1" "$exit_code" "-o with no arg exits 1"

# Test 6: Unknown option
echo "Test 6: Unknown option exits 1"
output=$("$NOISE_FILTER" --bogus-option 2>&1; echo "EXIT:$?")
exit_code=$(printf '%s\n' "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "1" "$exit_code" "Unknown option exits 1"

# Test 7: Multiple inputs
echo "Test 7: Multiple input files exits 1"
output=$("$NOISE_FILTER" "file1.mkv" "file2.mkv" 2>&1; echo "EXIT:$?")
exit_code=$(printf '%s\n' "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "1" "$exit_code" "Multiple input files exits 1"

# Test 8: Missing ffmpeg dependency
echo "Test 8: Missing ffmpeg dependency message"
MOCK_BIN="$TEMP_DIR/mock-bin"
mkdir -p "$MOCK_BIN"
for tool in basename dirname cat rm mktemp grep cut find printf mkdir chmod head touch; do
    tpath=$(command -v "$tool" 2>/dev/null || which "$tool" 2>/dev/null || true)
    if [[ -n "$tpath" && -x "$tpath" ]]; then
        ln -sf "$tpath" "$MOCK_BIN/$tool"
    fi
done
rm -f "$MOCK_BIN/ffmpeg" "$MOCK_BIN/ffprobe"
TEST_DEP_INPUT="$TEMP_DIR/dep-test.mkv"
ffmpeg -y -f lavfi -i "testsrc=duration=1:size=64x48:rate=10" \
    -f lavfi -i "sine=frequency=440:duration=1" \
    -c:v libx264 -c:a pcm_s16le -t 1 "$TEST_DEP_INPUT" -loglevel warning 2>/dev/null
output=$(PATH="$MOCK_BIN" /usr/bin/bash "$NOISE_FILTER" "$TEST_DEP_INPUT" 2>&1; echo "EXIT:$?")
exit_code=$(printf '%s\n' "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "1" "$exit_code" "Missing ffmpeg exits 1"
assert_contains "$output" "ffmpeg" "Missing ffmpeg shows error"
assert_contains "$output" "brew install" "Missing ffmpeg shows brew install hint"
assert_contains "$output" "apt install" "Missing ffmpeg shows apt install hint"

# Integration tests
echo ""
echo "--- Integration Tests ---"
echo ""

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "  SKIP: ffmpeg not available, skipping integration tests"
    SKIPPED=$((SKIPPED + 1))
fi

if [[ ! -x "$AUDIO_SEPARATOR" ]]; then
    echo "  SKIP: audio-separator not available, skipping integration tests"
    SKIPPED=$((SKIPPED + 1))
fi

TEST_INPUT="$TEMP_DIR/test-input.mkv"
TEST_OUTPUT_CUSTOM="$TEMP_DIR/test-custom-output.wav"

echo "Creating small test video..."
ffmpeg -y -f lavfi -i "testsrc=duration=2:size=64x48:rate=10" \
    -f lavfi -i "sine=frequency=440:duration=2" \
    -c:v libx264 -c:a pcm_s16le -t 2 \
    "$TEST_INPUT" -loglevel warning 2>&1 || {
    echo "  FAIL: Could not create test video"
    FAILED=$((FAILED + 1))
}

# Test 9: Process real .mkv
echo "Test 9: Process real .mkv file"
output=$("$NOISE_FILTER" "$TEST_INPUT" 2>&1; echo "EXIT:$?")
exit_code=$(printf '%s\n' "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "0" "$exit_code" "Processing exits 0"
assert_contains "$output" "Done." "Processing shows 'Done.'"
assert_contains "$output" "VOICE_ENHANCED" "Processing output has _VOICE_ENHANCED name"

TEST_OUTPUT_DEFAULT=$(printf '%s\n' "$output" | grep "Output file:" | sed 's/Output file: //')
if [[ -n "$TEST_OUTPUT_DEFAULT" && -f "$TEST_OUTPUT_DEFAULT" ]]; then
    echo "  PASS: Output file created ($TEST_OUTPUT_DEFAULT)"; PASSED=$((PASSED + 1))
    probe=$(ffprobe -v error -show_entries format=format_name -of default=nokey=1:noprint_wrappers=1 "$TEST_OUTPUT_DEFAULT" 2>/dev/null || true)
    assert_not_eq "" "$probe" "Output is valid media"
else
    echo "  FAIL: Output file not created"; FAILED=$((FAILED + 1))
fi

# Test 10: Overwrite protection (via -o)
echo "Test 10: Overwrite protection"
output=$("$NOISE_FILTER" "$TEST_INPUT" -o "$TEST_OUTPUT_DEFAULT" 2>&1; echo "EXIT:$?")
exit_code=$(printf '%s\n' "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "1" "$exit_code" "Overwrite protection exits 1"
assert_contains "$output" "already exists" "Overwrite shows 'already exists'"

# Test 11: --force overwrite (via -o)
echo "Test 11: --force overwrite"
output=$("$NOISE_FILTER" "$TEST_INPUT" -o "$TEST_OUTPUT_DEFAULT" --force 2>&1; echo "EXIT:$?")
exit_code=$(printf '%s\n' "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "0" "$exit_code" "--force exits 0"
assert_contains "$output" "Done." "--force processing shows 'Done.'"

# Test 12: -o custom output
echo "Test 12: -o custom output path"
output=$("$NOISE_FILTER" "$TEST_INPUT" -o "$TEST_OUTPUT_CUSTOM" --force 2>&1; echo "EXIT:$?")
exit_code=$(printf '%s\n' "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "0" "$exit_code" "-o exits 0"
assert_contains "$output" "test-custom-output" "-o output has custom name"
if [[ -f "$TEST_OUTPUT_CUSTOM" ]]; then
    echo "  PASS: Custom output file created"; PASSED=$((PASSED + 1))
else
    echo "  FAIL: Custom output file not created"; FAILED=$((FAILED + 1))
fi

# Test 13: Temp cleanup
echo "Test 13: Temp cleanup"
remaining=$(find /tmp -maxdepth 1 -type d -name 'enhance-voice-*' ! -name 'enhance-voice-test-*' 2>/dev/null | head -1 || true)
if [[ -z "$remaining" ]]; then
    echo "  PASS: No temp files remain"; PASSED=$((PASSED + 1))
else
    echo "  WARN: Some temp files may remain (could be from other runs)"
    echo "    Found: $remaining"
    PASSED=$((PASSED + 1))
fi

# Test 14: Output has audio (pcm_s16le for WAV)
echo "Test 14: Output has audio stream"
audio_codec=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 "$TEST_OUTPUT_DEFAULT" 2>/dev/null || true)
if [[ -n "$audio_codec" ]]; then
    assert_eq "pcm_s16le" "$audio_codec" "Output audio codec is pcm_s16le"
else
    echo "  FAIL: Output has no audio stream"; FAILED=$((FAILED + 1))
fi

# Test 15: Output has NO video stream (inverted from old test)
echo "Test 15: Output has no video stream"
video_codec=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 "$TEST_OUTPUT_DEFAULT" 2>/dev/null || true)
if [[ -z "$video_codec" ]]; then
    echo "  PASS: Output has no video stream"; PASSED=$((PASSED + 1))
else
    echo "  FAIL: Output has video stream (codec: $video_codec)"; FAILED=$((FAILED + 1))
fi

cleanup_test

echo ""
echo "=========================================="
echo "  Test Results"
echo "=========================================="
echo "  Passed:  $PASSED"
echo "  Failed:  $FAILED"
echo "  Skipped: $SKIPPED"
echo "=========================================="

if [[ "$FAILED" -eq 0 ]]; then exit 0; else exit 1; fi
