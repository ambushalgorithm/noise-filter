# Contributing to Noise Filter

Thank you for considering contributing! This document covers the development workflow, setup, testing, and code style guidelines.

---

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)
- [Issue Templates](#issue-templates)

---

## Development Setup

### Prerequisites

- **FFmpeg 4.4+** — required by both the Python CLI (`noise-filter`) and the Bash script (`./noise-filter`)
  - Linux: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`
- **Python 3.11+** — for the CLI/TUI package
- **audio-separator** — for vocals stem extraction

### Clone and Install

```bash
git clone https://github.com/anomalyco/noise-filter.git
cd noise-filter

# Install the Python package in editable mode
pip install -e .

# Verify installation
noise-filter --help
```

### audio-separator Setup

The project expects `audio-separator` at `~/.venvs/audio-separator/bin/audio-separator`. For development without the real tool, a mock script is available:

```bash
mkdir -p ~/.venvs/audio-separator/bin
# The mock creates a silent WAV file and simulates the BS-Roformer output naming
```

The mock is found automatically by `find_audio_separator()` in `noise_filter/subprocess.py`. If the real `audio-separator` is on your `PATH`, it will be used instead.

### Running the Bash Script

The `./noise-filter` Bash script has no Python dependencies:

```bash
./noise-filter --help
```

---

## Project Structure

```
noise-filter/
├── noise-filter              # Bash script — voice enhancement engine
├── noise_filter/              # Python package
│   ├── cli.py                 # Click CLI entry point
│   ├── config.py              # TOML config loading
│   ├── presets.py             # Built-in presets + filter construction
│   ├── subprocess.py          # ffmpeg/audio-separator calls
│   └── tui/                   # Textual TUI
│       ├── app.py             # App with 3-screen navigation
│       └── screens.py         # InputScreen, FilterScreen, RunScreen
├── tests/                     # pytest test suite
│   ├── test_cli.py            # CLI unit tests
│   ├── test_config.py         # Config unit tests
│   ├── test_e2e_cli.py        # CLI end-to-end tests
│   ├── test_e2e_config.py     # Config end-to-end tests
│   ├── test_e2e_tui.py        # TUI end-to-end tests
│   ├── test_presets.py        # Preset/filter string tests
│   ├── test_enhance_voice.sh  # Bash script unit tests
│   └── test_e2e_enhance_voice.sh  # Bash script integration tests
├── pyproject.toml
└── ...
```

---

## Running Tests

### Python Tests

```bash
# Run all Python tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_presets.py

# Run a specific test
pytest tests/test_presets.py::TestPresets::test_medium_filter_string_exact -v

# Run with warnings shown
pytest -v -W all

# Run non-TUI tests only (TUI tests require a display server)
pytest --ignore=tests/test_e2e_tui.py
```

### Bash Script Tests

```bash
# ShellCheck lint (install via apt/brew: shellcheck)
shellcheck noise-filter

# Unit tests
bash tests/test_enhance_voice.sh

# Integration tests (requires ffmpeg and audio-separator)
bash tests/test_e2e_enhance_voice.sh
```

### Test Structure

| Suite | File | What it covers |
|-------|------|----------------|
| CLI unit | `test_cli.py` | Argument parsing, option handling |
| Config unit | `test_config.py` | TOML loading, path resolution, validation |
| CLI E2E | `test_e2e_cli.py` | Full CLI pipeline with mock audio |
| Config E2E | `test_e2e_config.py` | Config file read/write, override resolution |
| TUI E2E | `test_e2e_tui.py` | Screen navigation, widget interaction |
| Presets | `test_presets.py` | FilterParams, merge/build, clamp, ranges |
| Bash unit | `test_enhance_voice.sh` | Argument parsing, error handling |
| Bash E2E | `test_e2e_enhance_voice.sh` | Full pipeline via Bash script |

---

## Code Style

### Python

- **PEP 8** — follow standard Python style
- **Type hints** — use `typing` annotations for all function signatures
- **Line length** — 100 characters maximum
- **Imports** — standard library first, then third-party, then local (separated by blank lines)
- **Docstrings** — use for public functions and classes
- **Naming** — `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants

```python
# Good
from pathlib import Path
from typing import Optional

import click

from .config import load_config


def process_file(path: Path, preset: str = "medium") -> Optional[str]:
    """Process an audio file with the given preset."""
    ...
```

### Shell (noise-filter)

- **Google Shell Style Guide** — see https://google.github.io/styleguide/shellguide.html
- Use `command -v` (not `which`) for dependency checks
- Print error messages to stderr (`>&2`)
- Use numeric exit codes (0 = success, 1 = error)
- Quote all variable expansions (`"$var"`)
- Use `set -euo pipefail` at the top of scripts

### TUI (Textual)

- Follow existing patterns in `noise_filter/tui/`
- Screen classes in `screens.py`, app logic in `app.py`
- Use CSS-in-Python for widget styling within the App class
- Navigation uses `push_screen` / `pop_screen` (see import at top of `app.py`)

---

## Pull Request Process

1. **Fork** the repository and create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make your changes**, keeping them focused on a single concern.

3. **Write or update tests** — aim for >90% coverage on new code.

4. **Run the tests** to ensure nothing is broken:
   ```bash
   pytest
   shellcheck noise-filter
   ```

5. **Commit** with a descriptive message:
   ```bash
   git commit -am "feat: add highpass frequency override to TUI"
   ```

6. **Push** and open a pull request:
   ```bash
   git push origin feature/my-feature
   ```

7. In the PR description, include:
   - What the change does
   - Why it's needed
   - How it was tested
   - Any breaking changes

### PR Guidelines

- Keep PRs small and focused — one feature or fix per PR
- Update documentation (README, CONTRIBUTING) if behavior changes
- Add or update tests for all new or modified functionality
- Ensure CI passes (all tests, linting)

---

## Issue Templates

When filing a bug report or feature request, include:

- **Bug reports**: steps to reproduce, expected vs actual behavior, environment details (OS, FFmpeg version, Python version)
- **Feature requests**: use case, desired behavior, any relevant alternatives

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
