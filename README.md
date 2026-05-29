# 🎤 Noise Filter

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Linux | macOS](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS-lightgrey)](https://github.com/ambushalgorithm/noise-filter)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/Tests-109%2F109%20passing-green)](tests/)
[![FFmpeg 4.4+](https://img.shields.io/badge/FFmpeg-4.4%2B-lightgrey)](https://ffmpeg.org/)

> 🎯 **Extract vocals → enhance → export.** A dual-interface voice enhancement tool that separates vocals from any audio/video, runs them through a professional-grade 6-filter FFmpeg chain, and outputs pristine WAV files — automatically named and never overwritten.

It ships in **two forms**:

- 🐍 **`noise-filter` (Python CLI)** — Click CLI + Textual TUI with preset profiles, per-filter overrides, and TOML config
- 🐚 **`./noise-filter` (Bash script)** — standalone Bash script with zero Python dependencies

Both share the same backend pipeline: `audio-separator` for vocals extraction → FFmpeg 6-filter chain → auto-named output.

---

## ✨ Features

- 🎤 **Voice extraction** — isolates vocals from any audio/video using `audio-separator` (BS-Roformer model)
- 🔧 **6-filter FFmpeg chain** — `highpass` → `afftdn` → `anlmdn` → `acompressor` → `equalizer` → `lowpass`
- 🎚️ **4 built-in presets** — Light, Medium (default), Heavy, and Custom (user-defined)
- 🎛️ **Per-filter overrides** — CLI flags and TUI inputs fine-tune individual parameters
- ⚙️ **TOML configuration** — persistent user settings at `~/.config/noise-filter/config.toml`
- 🔢 **Auto-incrementing output** — never overwrites files; produces `_VOICE_ENHANCED_01.wav`, `_02`, etc.
- 🖥️ **Dual interface** — full-featured Python CLI + TUI, or zero-dependency Bash script
- 🍏🐧 **Cross-platform** — tested on Linux (x86_64), macOS Intel, and macOS Apple Silicon

---

## 📋 Table of Contents

- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Usage](#-usage)
- [Preset Reference](#-preset-reference)
- [Configuration](#-configuration)
- [How It Works](#-how-it-works)
- [Cross-Platform Compatibility](#-cross-platform-compatibility)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)
- [License](#-license)

---

## 📦 Prerequisites

| Tool | Version | Installation |
|------|---------|-------------|
| [FFmpeg](https://ffmpeg.org/) | 4.4+ | `apt install ffmpeg` (Debian) / `brew install ffmpeg` (macOS) |
| [FFprobe](https://ffmpeg.org/ffprobe.html) | (ships with FFmpeg) | included with FFmpeg |
| [audio-separator](https://github.com/nomadkaraoke/python-audio-separator) | latest | see [Installation](#-installation) |

FFmpeg 4.4+ is required for the `anlmdn` audio filter. Most distribution packages and Homebrew builds satisfy this.

For the Python CLI/TUI, you also need **Python 3.11+** with `pip`.

---

## 🚀 Installation

### 🐚 Quick Start (Bash Script)

The `./noise-filter` Bash script has no Python dependencies — only FFmpeg and `audio-separator` are required.

```bash
# Install FFmpeg
sudo apt install ffmpeg        # Linux
brew install ffmpeg            # macOS

# Install audio-separator in a virtual environment
python3 -m venv ~/.venvs/audio-separator
~/.venvs/audio-separator/bin/pip install audio-separator

# Download and use the script
git clone https://github.com/ambushalgorithm/noise-filter.git
cd noise-filter
./noise-filter recording.mkv
```

### 🐍 Python Package

```bash
# FFmpeg and audio-separator still required (see above)
pip install noise-filter

# Or from source
git clone https://github.com/ambushalgorithm/noise-filter.git
cd noise-filter
pip install -e .
```

Dependencies installed automatically: `click`, `toml`, `textual`, `platformdirs`.

### ✅ Verifying Installation

```bash
# Bash script
./noise-filter --help

# Python CLI
noise-filter --help

# Python TUI
noise-filter --tui
```

---

## 🎮 Usage

### 🖥️ Basic CLI Usage

```bash
noise-filter [OPTIONS] [INPUT]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--preset` | `-p` | Preset profile: `light`, `medium`, `heavy`, `custom` (default: `medium`) |
| `--highpass-freq` | | Highpass cutoff in Hz (20–300) |
| `--afftdn-noise-floor` | | AFFTDN noise floor in dB (-80 to -10) |
| `--anlmdn-strength` | | ANLMDN strength (1–15) |
| `--anlmdn-power` | | ANLMDN power (0.001–0.100) |
| `--acompressor-threshold` | | Compressor threshold in dBFS (-60 to 0) |
| `--acompressor-ratio` | | Compressor ratio (1.0–20.0) |
| `--equalizer-freq` | | EQ center frequency in Hz (20–20000) |
| `--equalizer-type` | | EQ filter type (`q`, `lowshelf`, `highshelf`, `lowpass`, `highpass`) |
| `--equalizer-width` | | EQ Q factor width (0.1–10.0) |
| `--equalizer-gain` | | EQ gain in dB (-20 to +20) |
| `--lowpass-freq` | | Lowpass cutoff in Hz (4000–16000) |
| `--output-dir` | `-o` | Output directory (default: same directory as input) |
| `--tui` | | Launch Textual TUI |

**Examples:**

```bash
# Process with medium preset (default)
noise-filter recording.wav

# Light preset — minimal processing for clean audio
noise-filter -p light podcast.wav

# Heavy preset — aggressive noise reduction
noise-filter -p heavy outdoor-recording.mkv

# Custom preset with per-filter override
noise-filter -p heavy --highpass-freq 150 --equalizer-gain 4 meeting.mkv

# Specify output directory
noise-filter input.mp4 -o ~/enhanced/

# Custom output filename via the Bash script
./noise-filter input.wav -o my-custom-name.wav
```

### 🎚️ Presets

Four presets control all 6 filters simultaneously:

| Preset | Best for |
|--------|----------|
| `light` | Already-clean audio (quiet room, good mic) — preserves natural timbre |
| `medium` | General-purpose voice enhancement (podcasts, meetings, voiceovers) — matches original `./noise-filter` defaults |
| `heavy` | Poor recording conditions (outdoor, cafe, construction noise) — may sound processed |
| `custom` | User-defined values from config file `[override]` section |

> 💡 **Tip:** CLI flags override the preset for individual parameters. **Precedence:** CLI flags > config file > built-in preset defaults.

### 🎛️ Per-Filter Overrides

Any filter parameter can be overridden on the command line:

```bash
noise-filter --preset light --highpass-freq 100 --equalizer-gain 3 input.wav
```

This uses the Light preset but with a 100 Hz highpass (instead of 80) and +3 dB EQ gain (instead of +2).

### ⚙️ Config File

Persistent configuration at `~/.config/noise-filter/config.toml` (Linux) or `~/Library/Application Support/noise-filter/config.toml` (macOS):

```toml
# Override individual preset values
[presets.light]
highpass_freq = 100

# Custom preset parameters (used with --preset custom)
[override]
highpass_freq = 150
acompressor_ratio = 4.0

[defaults]
selected_preset = "heavy"
```

See [Configuration](#-configuration) for the full schema.

### 🖥️ TUI (Terminal UI)

Launch with:

```bash
noise-filter --tui
```

The TUI has **3 screens** with forward/back navigation:

1. **📂 Input & Preset** — Input file path, output directory, preset selector dropdown, "Next →" button
2. **🎛️ Filter Parameters** — All 11 per-filter parameter inputs with live filter chain preview, "← Back" and "Next →" buttons
3. **▶️ Run & Results** — Filter chain preview string, Run button, progress bar, status/output text, "← Back" button

### 🐚 Using the Bash Script Directly

The Bash script offers a lightweight alternative with no Python dependency:

```bash
./noise-filter <input> [options]

Options:
  -o <path>    Custom output file path
  --force      Overwrite existing output
  --help       Show usage
```

The script uses the same medium preset defaults as `noise-filter --preset medium`.

When run, it produces three files in the output directory:
- **Enhanced WAV** — noise-reduced vocals (auto-named)
- **Vocals stem** — raw vocals extraction (copied from separator)
- **Instrumental stem** — remaining audio (copied from separator, if available)

### 📁 Output Files

For an input file named `Screen-2026-04-24_10-54-42.mkv`, the pipeline produces:

| File | Description |
|------|-------------|
| `Screen-2026-04-24_10-54-42_VOCALS_model_bs_roformer_ep_317_sdr_12.wav` | 🎤 Extracted vocals stem |
| `Screen-2026-04-24_10-54-42_INSTRUMENTALS_model_bs_roformer_ep_317_sdr_12.wav` | 🎵 Remaining instrumental stem |
| `Screen-2026-04-24_10-54-42_VOICE_ENHANCED_01.wav` | ✨ Final enhanced output |

> 🔒 The enhanced output filename auto-increments: `_VOICE_ENHANCED_01.wav`, `_02.wav`, `_03.wav` — existing files are **never overwritten**.

---

## 📊 Preset Reference

| Filter | param | ☀️ Light | 🌤️ Medium | 🌩️ Heavy |
|--------|-------|:--------:|:----------:|:--------:|
| highpass | f (Hz) | 80 | 120 | 200 |
| afftdn | nf (dB) | -20 | -30 | -50 |
| anlmdn | s | 3 | 7 | 12 |
| anlmdn | p | 0.001 | 0.002 | 0.005 |
| acompressor | threshold (dB) | -12 | -18 | -24 |
| acompressor | ratio | 2:1 | 3:1 | 6:1 |
| equalizer | f (Hz) | 3000 | 3000 | 2500 |
| equalizer | type | q | q | q |
| equalizer | w (Q) | 1.0 | 1.0 | 1.5 |
| equalizer | g (dB) | +2 | +4 | +6 |
| lowpass | f (Hz) | 12000 | 9000 | 7000 |

**FFmpeg filter strings:**

```
☀️ light:  highpass=f=80,afftdn=nf=-20,anlmdn=s=3:p=0.001,acompressor=threshold=-12dB:ratio=2,equalizer=f=3000:t=q:w=1:g=2,lowpass=f=12000
🌤️ medium: highpass=f=120,afftdn=nf=-30,anlmdn=s=7:p=0.002,acompressor=threshold=-18dB:ratio=3,equalizer=f=3000:t=q:w=1:g=4,lowpass=f=9000
🌩️ heavy:  highpass=f=200,afftdn=nf=-50,anlmdn=s=12:p=0.005,acompressor=threshold=-24dB:ratio=6,equalizer=f=2500:t=q:w=1.5:g=6,lowpass=f=7000
```

---

## ⚙️ Configuration

### 📁 File Location

| Platform | Path |
|----------|------|
| 🐧 Linux | `~/.config/noise-filter/config.toml` |
| 🍏 macOS | `~/Library/Application Support/noise-filter/config.toml` |
| 📂 Fallback (XDG) | `$XDG_CONFIG_HOME/noise-filter/config.toml` |

### 📝 Schema

```toml
# Built-in preset overrides (optional — overrides individual default values)
[presets.light]
highpass_freq = 80
afftdn_noise_floor = -20
# ... all 11 filter parameters (see Preset Reference table)

[presets.medium]
highpass_freq = 120
# ...

[presets.heavy]
highpass_freq = 200
# ...

# Custom preset — activated with --preset custom
# Partial overrides: unspecified params fall back to medium preset defaults
[override]
highpass_freq = 150
equalizer_gain = 4
# null or omitted keys inherit from the preset

[defaults]
selected_preset = "medium"   # or "light", "heavy", "custom"
# output_dir = "~/enhanced"  # optional default output directory
# force = false              # whether to overwrite without prompting
```

### 📐 Precedence

```
🥇 CLI flags  >  🥈 [override] section  >  🥉 preset definition  >  built-in defaults
```

### ✅ Parameter Validation

- All numeric values are clamped to their documented min/max ranges
- `equalizer_type` must be one of: `q`, `lowshelf`, `highshelf`, `lowpass`, `highpass`
- Invalid values fall back to defaults with a warning
- Missing or empty config file uses built-in defaults (medium preset)

---

## 🔧 How It Works

```
INPUT (audio or video)
    │
    ▼
┌─────────────────────────────┐
│ ffprobe stream detection    │  🔍 Identifies audio & video streams
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ ffmpeg audio extraction     │  🎞️ (video inputs only) Extract PCM
│ pcm_s16le / 48 kHz / mono   │  audio stream to temp file
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ audio-separator             │  🎤 BS-Roformer model separates into
│ vocals stem extraction      │  Vocals + Instrumental stems
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ ffmpeg 6-filter chain       │  🔧 highpass → afftdn → anlmdn →
│                             │  acompressor → equalizer → lowpass
└─────────────────────────────┘
    │
    ▼
OUTPUT: _VOICE_ENHANCED_NN.wav   ✨
+ _VOCALS_.wav (copied to output dir)        🎤
+ _INSTRUMENTALS_.wav (copied to output dir) 🎵
```

**Key design decisions:**

- 🏗️ Pipe-free architecture uses temp files for reliability
- 🔒 6-filter order is immutable — all presets use the same chain with different parameters
- 📋 Vocal stem copied to output directory alongside enhanced result
- 🔢 Auto-incrementing filenames prevent accidental overwrites
- 🧹 Temp directory cleaned up on success, error, or Ctrl+C

---

## 🖥️ Cross-Platform Compatibility

| Capability | 🐧 Linux (x86_64) | 🍏 macOS Intel (x86_64) | 🍎 macOS Apple Silicon (arm64) |
|------------|:-----------------:|:-----------------------:|:-----------------------------:|
| FFmpeg 4.4+ | ✅ `apt`/`dnf`/`pacman` | ✅ `brew` | ✅ `brew` |
| audio-separator | ✅ | ✅ | ✅ |
| Python 3.11+ | ✅ | ✅ | ✅ |
| Bash script | ✅ | ✅ | ✅ |
| CLI / TUI | ✅ | ✅ | ✅ |
| Large files (>1 GB) | ✅ | ✅ | ✅ |

---

## 📂 Project Structure

```
noise-filter/
├── noise-filter              # 🐚 Bash script — original voice enhancement engine
├── noise_filter/              # 🐍 Python package — CLI + TUI wrapper
│   ├── __init__.py
│   ├── cli.py                 # 🖥️ Click CLI entry point
│   ├── config.py              # ⚙️ TOML config loading (XDG paths)
│   ├── presets.py             # 🎚️ Built-in presets + filter string construction
│   ├── subprocess.py          # 🔧 ffmpeg/audio-separator subprocess orchestration
│   └── tui/
│       ├── __init__.py
│       ├── app.py             # 🖥️ Textual TUI app (3-screen navigation)
│       └── screens.py         # 📂 InputScreen, 🎛️ FilterScreen, ▶️ RunScreen
├── tests/                     # 🧪 pytest test suite (109 tests)
├── pyproject.toml             # 📦 Python package configuration
├── README.md
└── LICENSE                    # 📄 MIT License
```

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- 🛠️ Development setup
- 🧪 Running tests (`pytest`)
- 📐 Code style guidelines
- 🔀 Pull request process

---

## 📄 License

MIT — see [LICENSE](LICENSE). Free to use, modify, and distribute.
