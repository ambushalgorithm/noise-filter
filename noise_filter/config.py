import os
import platform
import warnings
from pathlib import Path
from typing import Optional

import toml

from .presets import FilterParams, BUILTIN_PRESETS, clamp_value, VALID_EQUALIZER_TYPES, VALID_PRESET_NAMES


def get_config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "noise-filter"
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "noise-filter"
    return Path.home() / ".config" / "noise-filter"


def get_config_path() -> Path:
    return get_config_dir() / "config.toml"


def parse_preset_section(data: dict) -> Optional[FilterParams]:
    if not data:
        return None
    kwargs = {}
    for field_name in (
        "highpass_freq", "afftdn_noise_floor", "anlmdn_strength", "anlmdn_power",
        "acompressor_threshold", "acompressor_ratio", "equalizer_freq",
        "equalizer_type", "equalizer_width", "equalizer_gain", "lowpass_freq",
    ):
        if field_name in data:
            val = data[field_name]
            if val is None:
                continue
            val = clamp_value(field_name, val)
            kwargs[field_name] = val
    if not kwargs:
        return None
    return FilterParams(**kwargs)


def load_config(config_path: Optional[Path] = None) -> dict:
    result = {
        "presets": {"light": None, "medium": None, "heavy": None},
        "override": {},
        "defaults": {"selected_preset": "medium"},
    }
    if config_path is None:
        config_path = get_config_path()
    if not config_path.exists():
        return result
    try:
        raw = toml.load(str(config_path))
    except Exception as e:
        warnings.warn(f"Failed to parse config at {config_path}: {e}")
        return result
    if "presets" in raw:
        for name in ("light", "medium", "heavy"):
            if name in raw["presets"]:
                parsed = parse_preset_section(raw["presets"][name])
                if parsed is not None:
                    result["presets"][name] = parsed
    if "override" in raw:
        result["override"] = {}
        for field_name in (
            "highpass_freq", "afftdn_noise_floor", "anlmdn_strength", "anlmdn_power",
            "acompressor_threshold", "acompressor_ratio", "equalizer_freq",
            "equalizer_type", "equalizer_width", "equalizer_gain", "lowpass_freq",
        ):
            if field_name in raw["override"]:
                val = raw["override"][field_name]
                if val is not None:
                    result["override"][field_name] = val
    if "defaults" in raw:
        sp = raw["defaults"].get("selected_preset", "medium")
        if sp in VALID_PRESET_NAMES:
            result["defaults"]["selected_preset"] = sp
    return result
