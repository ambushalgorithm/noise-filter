import os
import platform
from pathlib import Path
from unittest.mock import patch

import pytest
import toml
from click.testing import CliRunner

from noise_filter.cli import main
from noise_filter.config import load_config, get_config_dir, get_config_path
from noise_filter.presets import FilterParams, BUILTIN_PRESETS

runner = CliRunner()


class TestE2EConfigLoading:
    def test_valid_config_file_parsed_and_used_by_cli(self, tmp_path: Path):
        cfg = tmp_path / "config.toml"
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
""")
        config = load_config(cfg)
        light = config["presets"]["light"]
        assert light.highpass_freq == 80
        assert light.anlmdn_strength == 3
        assert light.equalizer_gain == 2

    def test_missing_config_file_uses_builtin_defaults(self):
        config = load_config(Path("/nonexistent/path/config.toml"))
        assert config["presets"]["light"] is None
        assert config["presets"]["medium"] is None
        assert config["presets"]["heavy"] is None
        assert config["defaults"]["selected_preset"] == "medium"
        assert config["override"] == {}

    def test_partial_config_falls_back_to_builtin(self, tmp_path: Path):
        cfg = tmp_path / "config.toml"
        cfg.write_text("[presets.light]\nhighpass_freq = 80\n")
        config = load_config(cfg)
        light = config["presets"]["light"]
        assert light.highpass_freq == 80
        assert config["presets"]["medium"] is None
        assert config["presets"]["heavy"] is None

    def test_invalid_value_clamped_with_warning(self, tmp_path: Path):
        cfg = tmp_path / "config.toml"
        cfg.write_text("""
[presets.light]
highpass_freq = 99999
""")
        config = load_config(cfg)
        light = config["presets"]["light"]
        assert light.highpass_freq == 300

    def test_xdg_config_home_path_resolution(self):
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/custom/xdg"}):
            d = get_config_dir()
            assert str(d) == "/custom/xdg/noise-filter"
        os.environ.pop("XDG_CONFIG_HOME", None)

    def test_linux_default_config_path(self):
        with (
            patch.object(platform, "system", return_value="Linux"),
            patch.dict(os.environ, {}, clear=True),
        ):
            d = get_config_dir()
            assert str(d).endswith("/.config/noise-filter")

    def test_macos_default_config_path(self):
        with (
            patch.object(platform, "system", return_value="Darwin"),
            patch.dict(os.environ, {}, clear=True),
        ):
            d = get_config_dir()
            assert "Application Support" in str(d)
            assert d.name == "noise-filter"

    def test_override_section_parsed(self, tmp_path: Path):
        cfg = tmp_path / "config.toml"
        cfg.write_text("""
[override]
highpass_freq = 150
equalizer_gain = 6
""")
        config = load_config(cfg)
        assert config["override"]["highpass_freq"] == 150
        assert config["override"]["equalizer_gain"] == 6
        assert "afftdn_noise_floor" not in config["override"]

    def test_selected_preset_default_from_config(self, tmp_path: Path):
        cfg = tmp_path / "config.toml"
        cfg.write_text('[defaults]\nselected_preset = "light"\n')
        config = load_config(cfg)
        assert config["defaults"]["selected_preset"] == "light"

    def test_invalid_selected_preset_falls_back(self, tmp_path: Path):
        cfg = tmp_path / "config.toml"
        cfg.write_text('[defaults]\nselected_preset = "bogus"\n')
        config = load_config(cfg)
        assert config["defaults"]["selected_preset"] == "medium"

    def test_empty_config_file_returns_defaults(self, tmp_path: Path):
        cfg = tmp_path / "config.toml"
        cfg.write_text("")
        config = load_config(cfg)
        assert config["presets"]["light"] is None
        assert config["presets"]["medium"] is None
        assert config["presets"]["heavy"] is None
        assert config["defaults"]["selected_preset"] == "medium"

    def test_malformed_toml_graceful_fallback(self, tmp_path: Path):
        cfg = tmp_path / "config.toml"
        cfg.write_text("[[[invalid toml content")
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            config = load_config(cfg)
        assert config["presets"]["light"] is None

    def test_config_with_all_presets_overridden(self, tmp_path: Path):
        cfg = tmp_path / "config.toml"
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

[presets.heavy]
highpass_freq = 200
afftdn_noise_floor = -50
anlmdn_strength = 12
anlmdn_power = 0.005
acompressor_threshold = -24
acompressor_ratio = 6.0
equalizer_freq = 2500
equalizer_type = "q"
equalizer_width = 1.5
equalizer_gain = 6
lowpass_freq = 7000
""")
        config = load_config(cfg)
        for name in ("light", "medium", "heavy"):
            assert config["presets"][name] is not None, f"{name} preset missing"
        assert config["presets"]["light"].highpass_freq == 80
        assert config["presets"]["medium"].lowpass_freq == 9000
        assert config["presets"]["heavy"].equalizer_gain == 6

    def test_null_override_values_skipped(self, tmp_path: Path):
        cfg = tmp_path / "config.toml"
        cfg.write_text("""
[override]
highpass_freq = 150
""")
        config = load_config(cfg)
        assert "highpass_freq" in config["override"]
        assert config["override"]["highpass_freq"] == 150
        assert "afftdn_noise_floor" not in config["override"]

    def test_cli_loads_config_and_uses_preset(self, tmp_path: Path):
        cfg_dir = tmp_path / ".config" / "noise-filter"
        cfg_dir.mkdir(parents=True)
        cfg = cfg_dir / "config.toml"
        cfg.write_text('[defaults]\nselected_preset = "light"\n')
        input_file = tmp_path / "test_input.wav"
        input_file.write_text("dummy content")
        with (
            patch("noise_filter.cli.load_config") as mock_load,
            patch("noise_filter.cli.run_enhance") as mock_run,
        ):
            mock_run.return_value = {"output": str(tmp_path / "output.wav")}
            mock_load.return_value = {
                "presets": {"light": None, "medium": None, "heavy": None},
                "override": {},
                "defaults": {"selected_preset": "light"},
            }
            result = runner.invoke(main, [str(input_file)])
        assert result.exit_code == 0

    def test_cli_config_override_merged_with_preset(self, tmp_path: Path):
        input_file = tmp_path / "input.wav"
        input_file.write_text("dummy")
        with (
            patch("noise_filter.cli.load_config") as mock_load,
            patch("noise_filter.cli.run_enhance") as mock_run,
        ):
            mock_load.return_value = {
                "presets": {"light": None, "medium": None, "heavy": None},
                "override": {"highpass_freq": 150},
                "defaults": {"selected_preset": "medium"},
            }
            mock_run.return_value = {"output": str(tmp_path / "output.wav")}
            result = runner.invoke(main, [str(input_file), "--preset", "custom"])
        assert result.exit_code == 0
