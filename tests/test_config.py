import os
import tempfile
from pathlib import Path

import pytest

from noise_filter.config import get_config_dir, get_config_path, load_config, parse_preset_section
from noise_filter.presets import FilterParams, BUILTIN_PRESETS


def test_get_config_dir_default():
    d = get_config_dir()
    assert d.name == "noise-filter"


def test_get_config_dir_xdg():
    with tempfile.TemporaryDirectory() as td:
        os.environ["XDG_CONFIG_HOME"] = td
        d = get_config_dir()
        assert str(d) == str(Path(td) / "noise-filter")
    os.environ.pop("XDG_CONFIG_HOME", None)


def test_get_config_path():
    p = get_config_path()
    assert p.name == "config.toml"


def test_missing_config_uses_defaults():
    config = load_config(Path("/nonexistent/path/config.toml"))
    assert config["presets"]["light"] is None
    assert config["presets"]["medium"] is None
    assert config["presets"]["heavy"] is None
    assert config["defaults"]["selected_preset"] == "medium"
    assert config["override"] == {}


def test_empty_config_uses_defaults():
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "config.toml"
        cfg.write_text("")
        config = load_config(cfg)
        assert config["presets"]["light"] is None
        assert config["defaults"]["selected_preset"] == "medium"


def test_full_config_parsed():
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "config.toml"
        cfg.write_text("""
[presets.light]
highpass_freq = 80
afftdn_noise_floor = -20
anlmdn_strength = 3
anlmdn_power = 0.001
acompressor_threshold = -12
acompressor_ratio = 2.0
equalizer_freq = 3000
equalizer_type = "q"
equalizer_width = 1.0
equalizer_gain = 2
lowpass_freq = 12000

[presets.medium]
highpass_freq = 120
afftdn_noise_floor = -30
anlmdn_strength = 7
anlmdn_power = 0.002
acompressor_threshold = -18
acompressor_ratio = 3.0
equalizer_freq = 3000
equalizer_type = "q"
equalizer_width = 1.0
equalizer_gain = 4
lowpass_freq = 9000

[defaults]
selected_preset = "light"
""")
        config = load_config(cfg)
        light = config["presets"]["light"]
        assert light is not None
        assert light.highpass_freq == 80
        assert light.equalizer_gain == 2
        medium = config["presets"]["medium"]
        assert medium is not None
        assert medium.lowpass_freq == 9000
        assert config["defaults"]["selected_preset"] == "light"


def test_partial_config_falls_back():
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "config.toml"
        cfg.write_text("""
[presets.light]
highpass_freq = 80
""")
        config = load_config(cfg)
        light = config["presets"]["light"]
        assert light is not None
        assert light.highpass_freq == 80


def test_invalid_value_clamped():
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "config.toml"
        cfg.write_text("""
[presets.light]
highpass_freq = 99999
""")
        config = load_config(cfg)
        light = config["presets"]["light"]
        assert light is not None
        assert light.highpass_freq == 300


def test_override_section():
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "config.toml"
        cfg.write_text("""
[override]
highpass_freq = 150
""")
        config = load_config(cfg)
        assert config["override"]["highpass_freq"] == 150
        assert "afftdn_noise_floor" not in config["override"]


def test_invalid_selected_preset_defaults():
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "config.toml"
        cfg.write_text("""
[defaults]
selected_preset = "invalid"
""")
        config = load_config(cfg)
        assert config["defaults"]["selected_preset"] == "medium"


def test_xdg_config_path():
    with tempfile.TemporaryDirectory() as td:
        os.environ["XDG_CONFIG_HOME"] = td
        p = get_config_path()
        assert str(p) == str(Path(td) / "noise-filter" / "config.toml")
        os.environ.pop("XDG_CONFIG_HOME", None)


def test_config_override_custom_preset_none():
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "config.toml"
        cfg.write_text("[override]\n")
        config = load_config(cfg)
        assert config["override"] == {}


def test_config_malformed_toml():
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "config.toml"
        cfg.write_text("[[[invalid toml")
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            config = load_config(cfg)
        assert config["presets"]["light"] is None
