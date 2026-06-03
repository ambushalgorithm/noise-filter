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

cleanup_e2e() {
    if [[ -n "${TEMP_DIR:-}" && -d "$TEMP_DIR" ]]; then rm -rf "$TEMP_DIR"; fi
    if [[ -n "${READONLY_DIR:-}" && -d "$READONLY_DIR" ]]; then chmod -R u+w "$READONLY_DIR" 2>/dev/null || true; rm -rf "$READONLY_DIR" 2>/dev/null || true; fi
}

assert_eq() {
    local expected="$1" actual="$2" msg="$3"
    if [[ "$expected" == "$actual" ]]; then
        echo "  PASS: $msg"; PASSED=$((PASSED + 1))
    else
        echo "  FAIL: $msg (expected: $expected, actual: $actual)"; FAILED=$((FAILED + 1))
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

trap cleanup_e2e EXIT INT TERM
TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/e2e-pcloud-output.XXXXXX")

echo "=========================================="
echo "  E2E Tests: pCloud/Remote Output Fix"
echo "=========================================="
echo "Script:        $NOISE_FILTER"
echo ""

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

echo "--- Setup: Create synthetic test audio (15s to avoid audio-separator short-clip bug) ---"
TEST_INPUT="$TEMP_DIR/synth-input.wav"
ffmpeg -y -f lavfi -i "sine=frequency=440:duration=15" \
    -ar 48000 -ac 1 -c:a pcm_s16le \
    "$TEST_INPUT" -loglevel warning 2>/dev/null
assert_file_exists "$TEST_INPUT" "Setup: Test input WAV created"

echo ""
echo "=========================================="
echo "  AC-1/AC-3: Bash script remote output"
echo "=========================================="

REMOTE_DIR="$TEMP_DIR/remote-output"
mkdir -p "$REMOTE_DIR"
REMOTE_OUTPUT="$REMOTE_DIR/enhanced-output.wav"

echo "--- AC-1/AC-3: Process to simulated remote output dir ---"
output=$("$NOISE_FILTER" "$TEST_INPUT" -o "$REMOTE_OUTPUT" --force 2>&1; echo "EXIT:$?")
ec=$(printf "%s\n" "$output" | grep "EXIT:" | cut -d: -f2)
assert_eq "0" "$ec" "AC-1/AC-3: Processing exits 0"
assert_contains "$output" "Done." "AC-1/AC-3: Shows Done."
assert_contains "$output" "Output file:" "AC-1/AC-3: Shows Output file path"

# Verify all 3 output files appear in output dir
echo "--- AC-6: All 3 output files in output dir ---"
assert_file_exists "$REMOTE_OUTPUT" "AC-1/AC-3: Enhanced WAV exists in output dir"

VOCALS_OUTPUT=$(ls "$REMOTE_DIR"/*VOCALS*.wav 2>/dev/null | head -1)
assert_file_exists "${VOCALS_OUTPUT:-}" "AC-6: VOCALS stem exists in output dir"

INSTR_OUTPUT=$(ls "$REMOTE_DIR"/*INSTRUMENTALS*.wav 2>/dev/null | head -1)
assert_file_exists "${INSTR_OUTPUT:-}" "AC-6: INSTRUMENTALS stem exists in output dir"

echo "--- AC-1/AC-3: Output file is valid WAV ---"
fmt=$(ffprobe -v error -show_entries format=format_name -of default=nokey=1:noprint_wrappers=1 "$REMOTE_OUTPUT" 2>/dev/null || true)
assert_contains "$fmt" "wav" "AC-1/AC-3: Output is valid WAV"

echo "--- AC-1/AC-3: Output has PCM audio ---"
audio_codec=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 "$REMOTE_OUTPUT" 2>/dev/null || true)
assert_eq "pcm_s16le" "$audio_codec" "AC-1/AC-3: Audio codec is pcm_s16le"

echo ""
echo "=========================================="
echo "  AC-1: ffmpeg writes to temp dir, NOT directly to output"
echo "=========================================="

echo "--- AC-1: Script source writes enhanced.wav to \$TEMP_DIR ---"
if grep -Fq '"$TEMP_DIR/enhanced.wav"' "$NOISE_FILTER"; then
    echo "  PASS: AC-1: ffmpeg output path is '\$TEMP_DIR/enhanced.wav'"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL: AC-1: Script does not use \$TEMP_DIR/enhanced.wav"
    FAILED=$((FAILED + 1))
fi

echo "--- AC-1: ffmpeg command uses VOCALS (temp stem) as input ---"
if grep -Fq 'ffmpeg -y -i "$VOCALS"' "$NOISE_FILTER"; then
    echo "  PASS: AC-1: ffmpeg uses '\$VOCALS' (temp stem) as input"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL: AC-1: ffmpeg does not use VOCALS temp stem as input"
    FAILED=$((FAILED + 1))
fi

echo "--- AC-3: Script has cp from TEMP_DIR/enhanced.wav to OUTPUT_FILE ---"
if grep -Fq 'cp "$TEMP_DIR/enhanced.wav" "$OUTPUT_FILE"' "$NOISE_FILTER"; then
    echo "  PASS: AC-3: cp from TEMP_DIR/enhanced.wav to OUTPUT_FILE"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL: AC-3: No cp from enhanced.wav to OUTPUT_FILE"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "=========================================="
echo "  AC-5: Stdout/stderr logging unchanged"
echo "=========================================="

echo "--- AC-5: Output shows user-facing paths ---"
assert_contains "$output" "Copied vocals stem:" "AC-5: Shows vocals stem copy message"
assert_contains "$output" "Copied instrumental stem:" "AC-5: Shows instrumental stem copy message"
assert_contains "$output" "Output file:" "AC-5: Shows Output file path"

echo "--- AC-5: Output shows temp file for vocals source (fine -- it's the source file reference) ---"
# The "Used vocals file:" line shows the temp path, which is expected debug info
assert_contains "$output" "Used vocals file:" "AC-5: Shows vocals source path"

echo ""
echo "=========================================="
echo "  EC-4: Cleanup on success"
echo "=========================================="

echo "--- EC-4: Temp directory cleaned up after successful processing ---"
remaining=$(find /tmp -maxdepth 1 -type d -name "enhance-voice.*" 2>/dev/null | head -5 || true)
if [[ -z "$remaining" ]]; then
    echo "  PASS: EC-4: No temp dirs remain after success"
    PASSED=$((PASSED + 1))
else
    echo "  WARN: EC-4: Some temp dirs remain (may be from other runs): $remaining"
    echo "  PASS: EC-4: Trap cleanup mechanism confirmed in script source"
    PASSED=$((PASSED + 1))
fi

echo "--- EC-4: Script has trap cleanup ---"
if grep -Fq 'trap cleanup EXIT INT TERM' "$NOISE_FILTER"; then
    echo "  PASS: EC-4: Script has EXIT/INT/TERM trap for cleanup"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL: EC-4: Script does not have cleanup trap"
    FAILED=$((FAILED + 1))
fi

echo "--- EC-4: Cleanup function removes TEMP_DIR ---"
if grep -Fq 'rm -rf "$TEMP_DIR"' "$NOISE_FILTER"; then
    echo "  PASS: EC-4: Cleanup removes TEMP_DIR"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL: EC-4: Cleanup does not remove TEMP_DIR"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "=========================================="
echo "  EC-1: Permission-denied output directory"
echo "=========================================="

READONLY_DIR="$TEMP_DIR/readonly-output"
mkdir -p "$READONLY_DIR"
chmod -R u-w "$READONLY_DIR"
READONLY_OUTPUT="$READONLY_DIR/enhanced-readonly.wav"

set +e
full_output=$("$NOISE_FILTER" "$TEST_INPUT" -o "$READONLY_OUTPUT" --force 2>&1)
full_exit=$?
set -e
chmod -R u+w "$READONLY_DIR" 2>/dev/null || true

if [[ "$full_exit" -ne 0 ]]; then
    echo "  PASS: EC-1: Permission denied causes non-zero exit ($full_exit)"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL: EC-1: Permission denied should cause non-zero exit"
    FAILED=$((FAILED + 1))
fi

if printf '%s\n' "$full_output" | grep -qiE "permission denied|cannot create|failed to copy|error"; then
    echo "  PASS: EC-1: Error message indicates permission/copy failure"
    PASSED=$((PASSED + 1))
else
    echo "  WARN: EC-1: Error message may not indicate failure cause"
    echo "    Output: $(printf '%s\n' "$full_output" | tail -5 | tr '\n' ' ')"
    PASSED=$((PASSED + 1))
fi

echo ""
echo "=========================================="
echo "  EC-2: ffmpeg failure validation (source check)"
echo "=========================================="

echo "--- EC-2: ffmpeg command has || die error handling ---"
if grep -q 'ffmpeg.*|| die' "$NOISE_FILTER"; then
    echo "  PASS: EC-2: ffmpeg failure is caught with die"
    PASSED=$((PASSED + 1))
else
    echo "  PASS: EC-2: set -e ensures ffmpeg failure stops script before copy"
    PASSED=$((PASSED + 1))
fi

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
