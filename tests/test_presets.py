import pytest

from noise_filter.presets import (
    FilterParams,
    BUILTIN_PRESETS,
    build_filter_string,
    merge_preset,
    clamp_value,
    clamp_params,
    VALID_EQUALIZER_TYPES,
    VALID_PRESET_NAMES,
)


class TestPresets:
    def test_light_preset_params(self):
        p = BUILTIN_PRESETS["light"]
        assert p.highpass_freq == 80
        assert p.afftdn_noise_floor == -20
        assert p.anlmdn_strength == 3
        assert p.anlmdn_power == 0.001
        assert p.acompressor_threshold == -12
        assert p.acompressor_ratio == 2.0
        assert p.equalizer_freq == 3000
        assert p.equalizer_type == "q"
        assert p.equalizer_width == 1.0
        assert p.equalizer_gain == 2
        assert p.lowpass_freq == 12000

    def test_light_filter_string(self):
        p = BUILTIN_PRESETS["light"]
        s = build_filter_string(p)
        assert "highpass=f=80" in s
        assert "afftdn=nf=-20" in s
        assert "anlmdn=s=3:p=0.001" in s
        assert "acompressor=threshold=-12dB:ratio=2" in s
        assert "g=2" in s
        assert "lowpass=f=12000" in s

    def test_medium_filter_string_exact(self):
        expected = "highpass=f=120,afftdn=nf=-30,anlmdn=s=7:p=0.002,acompressor=threshold=-18dB:ratio=3,equalizer=f=3000:t=q:w=1:g=4,lowpass=f=9000"
        p = BUILTIN_PRESETS["medium"]
        assert build_filter_string(p) == expected

    def test_heavy_filter_string(self):
        p = BUILTIN_PRESETS["heavy"]
        s = build_filter_string(p)
        assert "highpass=f=200" in s
        assert "afftdn=nf=-50" in s
        assert "anlmdn=s=12:p=0.005" in s
        assert "acompressor=threshold=-24dB:ratio=6" in s
        assert "equalizer=f=2500:t=q:w=1.5:g=6" in s
        assert "lowpass=f=7000" in s

    def test_filter_order(self):
        for name in ("light", "medium", "heavy"):
            s = build_filter_string(BUILTIN_PRESETS[name])
            parts = [p.split("=")[0] for p in s.split(",")]
            expected = ["highpass", "afftdn", "anlmdn", "acompressor", "equalizer", "lowpass"]
            assert parts == expected, f"{name}: {parts} != {expected}"

    def test_all_six_filters_present(self):
        for name in ("light", "medium", "heavy"):
            s = build_filter_string(BUILTIN_PRESETS[name])
            for fname in ("highpass", "afftdn", "anlmdn", "acompressor", "equalizer", "lowpass"):
                assert fname in s, f"{name} missing {fname}"

    def test_merge_preset_custom_no_overrides_falls_back_to_medium(self):
        p = merge_preset("custom")
        assert p.highpass_freq == 120

    def test_merge_preset_custom_with_override(self):
        p = merge_preset("custom", {"highpass_freq": 150})
        assert p.highpass_freq == 150
        assert p.afftdn_noise_floor == -30

    def test_merge_preset_partial_overrides(self):
        p = merge_preset("medium", {"highpass_freq": 100})
        assert p.highpass_freq == 100
        assert p.lowpass_freq == 9000

    def test_merge_preset_cli_overrides_config(self):
        p = merge_preset("medium", {"highpass_freq": 100, "afftdn_noise_floor": -40})
        assert p.highpass_freq == 100
        assert p.afftdn_noise_floor == -40

    def test_clamp_value_out_of_range(self):
        assert clamp_value("highpass_freq", 999) == 300
        assert clamp_value("highpass_freq", 5) == 20
        assert clamp_value("afftdn_noise_floor", 0) == -10
        assert clamp_value("afftdn_noise_floor", -100) == -80
        assert clamp_value("anlmdn_strength", 20) == 15
        assert clamp_value("anlmdn_strength", 0) == 1
        assert clamp_value("anlmdn_power", 3.0) == 0.100
        assert clamp_value("equalizer_gain", 50) == 20
        assert clamp_value("equalizer_gain", -50) == -20
        assert clamp_value("lowpass_freq", 99999) == 16000
        assert clamp_value("lowpass_freq", 100) == 4000

    def test_clamp_equalizer_type_invalid(self):
        assert clamp_value("equalizer_type", "notatype") == "q"
        assert clamp_value("equalizer_type", "lowshelf") == "lowshelf"

    def test_clamp_params(self):
        p = FilterParams(highpass_freq=999, lowpass_freq=100)
        clamp_params(p)
        assert p.highpass_freq == 300
        assert p.lowpass_freq == 4000

    def test_valid_preset_names(self):
        assert "light" in VALID_PRESET_NAMES
        assert "medium" in VALID_PRESET_NAMES
        assert "heavy" in VALID_PRESET_NAMES
        assert "custom" in VALID_PRESET_NAMES

    def test_build_filter_string_syntax(self):
        p = FilterParams()
        s = build_filter_string(p)
        import re
        assert re.search(r'highpass=f=\d+', s)
        assert re.search(r'afftdn=nf=-?\d+', s)
        assert re.search(r'anlmdn=s=\d+:p=[\d.]+', s)
        assert re.search(r'acompressor=threshold=-?\d+dB:ratio=[\d.]+', s)
        assert re.search(r'equalizer=f=\d+:t=\w+:w=[\d.]+:g=-?\d+', s)
        assert re.search(r'lowpass=f=\d+', s)
