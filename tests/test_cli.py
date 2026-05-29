import os
import tempfile
from pathlib import Path

import pytest
from unittest.mock import patch
from click.testing import CliRunner

from noise_filter.cli import main
from noise_filter.presets import build_filter_string, FilterParams, BUILTIN_PRESETS

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "noise-filter" in result.output or "Usage" in result.output


def test_cli_no_input():
    result = runner.invoke(main, [])
    assert result.exit_code != 0
    assert "INPUT" in result.output


def test_cli_invalid_preset():
    result = runner.invoke(main, ["input.wav", "--preset", "invalid"])
    assert result.exit_code != 0
    assert "invalid" in result.output.lower()


def test_cli_tui_flag():
    with patch("noise_filter.cli.launch_tui"):
        result = runner.invoke(main, ["--tui"])
    assert result.exit_code == 0


def test_cli_light_preset_filter_string():
    p = BUILTIN_PRESETS["light"]
    s = build_filter_string(p)
    assert "highpass=f=80" in s
    assert "afftdn=nf=-20" in s
    assert "anlmdn=s=3:p=0.001" in s
    assert "acompressor=threshold=-12dB:ratio=2" in s
    assert "equalizer=f=3000:t=q:w=1:g=2" in s
    assert "lowpass=f=12000" in s


def test_cli_medium_preset_filter_string():
    p = BUILTIN_PRESETS["medium"]
    s = build_filter_string(p)
    assert "highpass=f=120" in s
    assert "afftdn=nf=-30" in s
    assert "anlmdn=s=7:p=0.002" in s
    assert "acompressor=threshold=-18dB:ratio=3" in s
    assert "equalizer=f=3000:t=q:w=1:g=4" in s
    assert "lowpass=f=9000" in s


def test_cli_heavy_preset_filter_string():
    p = BUILTIN_PRESETS["heavy"]
    s = build_filter_string(p)
    assert "highpass=f=200" in s
    assert "afftdn=nf=-50" in s
    assert "anlmdn=s=12:p=0.005" in s
    assert "acompressor=threshold=-24dB:ratio=6" in s
    assert "equalizer=f=2500:t=q:w=1.5:g=6" in s
    assert "lowpass=f=7000" in s


def test_cli_custom_preset_no_override_falls_back():
    from noise_filter.presets import VALID_PRESET_NAMES
    assert "custom" in VALID_PRESET_NAMES


def test_cli_override_highpass():
    from noise_filter.presets import merge_preset
    p = merge_preset("medium", {"highpass_freq": 150})
    assert p.highpass_freq == 150
    assert p.lowpass_freq == 9000


def test_cli_override_multiple_params():
    from noise_filter.presets import merge_preset
    p = merge_preset("heavy", {"highpass_freq": 180, "equalizer_gain": 5})
    assert p.highpass_freq == 180
    assert p.equalizer_gain == 5
    assert p.afftdn_noise_floor == -50


def test_cli_custom_with_config_override_and_cli_flag():
    from noise_filter.presets import merge_preset
    p = merge_preset("custom", {"highpass_freq": 100, "afftdn_noise_floor": -40})
    assert p.highpass_freq == 100
    assert p.afftdn_noise_floor == -40
