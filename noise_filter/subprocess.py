import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


def find_audio_separator() -> str:
    candidates = [
        os.path.expanduser("~/.venvs/audio-separator/bin/audio-separator"),
        shutil.which("audio-separator") or "",
    ]
    for c in candidates:
        if c and os.access(c, os.X_OK):
            return c
    raise FileNotFoundError(
        "audio-separator not found. Install it or check ~/.venvs/audio-separator/bin/audio-separator"
    )


def next_output_path(directory: Path, stem: str, ext: str) -> Path:
    n = 1
    while True:
        candidate = directory / f"{stem}_{n:02d}.{ext}"
        if not candidate.exists():
            return candidate
        n += 1


def run_enhance(input_path: Path, filter_string: str, output_dir: Optional[Path] = None) -> dict:
    for cmd in ("ffmpeg", "ffprobe"):
        if not shutil.which(cmd):
            raise FileNotFoundError(f"{cmd} is not installed")

    audio_separator = find_audio_separator()

    if output_dir is None:
        output_dir = input_path.parent.resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    input_path = input_path.expanduser().resolve()
    basename = input_path.stem

    has_video = bool(
        subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=index", "-of", "default=nokey=1:noprint_wrappers=1",
             str(input_path)],
            capture_output=True, text=True,
        ).stdout.strip()
    )

    audio_stream = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=index", "-of", "default=nokey=1:noprint_wrappers=1",
         str(input_path)],
        capture_output=True, text=True,
    ).stdout.strip()
    if not audio_stream:
        raise ValueError(f"No audio stream found in input: {input_path}")

    temp_dir = Path(tempfile.mkdtemp(prefix="noise-filter-"))

    try:
        if has_video:
            print("Extracting audio from video...", file=sys.stderr)
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(input_path), "-vn",
                 "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "1",
                 str(temp_dir / f"{basename}.wav"),
                 "-loglevel", "warning", "-stats"],
                check=True, capture_output=True, text=True,
            )
            audio_to_separate = temp_dir / f"{basename}.wav"
        else:
            audio_to_separate = input_path

        print("Running audio-separator to extract vocals stem...", file=sys.stderr)
        subprocess.run(
            [audio_separator, str(audio_to_separate),
             "--output_format", "wav", "--output_dir", str(temp_dir)],
            check=True, capture_output=True, text=True,
        )

        vocals = None
        instrumental = None
        for f in temp_dir.iterdir():
            if f.suffix == ".wav":
                if "(Vocals)" in f.name:
                    vocals = f
                elif "(Instrumental)" in f.name:
                    instrumental = f
        if vocals is None:
            candidates = sorted(temp_dir.glob("*Vocals*.wav"))
            if candidates:
                vocals = candidates[0]
        if vocals is None or not vocals.exists():
            raise FileNotFoundError("Could not find or create a vocals stem.")

        output_file = next_output_path(output_dir, f"{basename}_VOICE_ENHANCED", "wav")
        print("Enhancing voice...", file=sys.stderr)
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(vocals),
             "-af", filter_string,
             str(output_file), "-loglevel", "warning", "-stats"],
            check=True, capture_output=True, text=True,
        )

        stem_paths = {"vocals": str(vocals), "instrumental": str(instrumental) if instrumental else None}
        if instrumental:
            new_name = instrumental.name.replace("(Instrumental)", "INSTRUMENTALS")
            dest_instr = output_dir / new_name
            shutil.copy2(str(instrumental), str(dest_instr))
            stem_paths["instrumental"] = str(dest_instr)
        new_name = vocals.name.replace("(Vocals)", "VOCALS")
        dest_vocals = output_dir / new_name
        shutil.copy2(str(vocals), str(dest_vocals))
        stem_paths["vocals"] = str(dest_vocals)

        print("Done.", file=sys.stderr)
        print(f"Output file: {output_file}", file=sys.stderr)

        return {
            "output": str(output_file),
            "vocals_stem": stem_paths.get("vocals"),
            "instrumental_stem": stem_paths.get("instrumental"),
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
