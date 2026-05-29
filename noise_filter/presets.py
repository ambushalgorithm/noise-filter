import dataclasses
from dataclasses import dataclass
from typing import Optional


@dataclass
class FilterParams:
    highpass_freq: int = 120
    afftdn_noise_floor: int = -30
    anlmdn_strength: int = 7
    anlmdn_power: float = 0.002
    acompressor_threshold: int = -18
    acompressor_ratio: float = 3.0
    equalizer_freq: int = 3000
    equalizer_type: str = "q"
    equalizer_width: float = 1.0
    equalizer_gain: int = 4
    lowpass_freq: int = 9000


BUILTIN_PRESETS: dict[str, FilterParams] = {
    "light": FilterParams(
        highpass_freq=80,
        afftdn_noise_floor=-20,
        anlmdn_strength=3,
        anlmdn_power=0.001,
        acompressor_threshold=-12,
        acompressor_ratio=2.0,
        equalizer_freq=3000,
        equalizer_type="q",
        equalizer_width=1.0,
        equalizer_gain=2,
        lowpass_freq=12000,
    ),
    "medium": FilterParams(),
    "heavy": FilterParams(
        highpass_freq=200,
        afftdn_noise_floor=-50,
        anlmdn_strength=12,
        anlmdn_power=0.005,
        acompressor_threshold=-24,
        acompressor_ratio=6.0,
        equalizer_freq=2500,
        equalizer_type="q",
        equalizer_width=1.5,
        equalizer_gain=6,
        lowpass_freq=7000,
    ),
}

PARAM_RANGES: dict[str, dict] = {
    "highpass_freq": {"min": 20, "max": 300},
    "afftdn_noise_floor": {"min": -80, "max": -10},
    "anlmdn_strength": {"min": 1, "max": 15},
    "anlmdn_power": {"min": 0.001, "max": 0.100},
    "acompressor_threshold": {"min": -60, "max": 0},
    "acompressor_ratio": {"min": 1.0, "max": 20.0},
    "equalizer_freq": {"min": 20, "max": 20000},
    "equalizer_type": {"allowed": ["q", "lowshelf", "highshelf", "lowpass", "highpass"]},
    "equalizer_width": {"min": 0.1, "max": 10.0},
    "equalizer_gain": {"min": -20, "max": 20},
    "lowpass_freq": {"min": 4000, "max": 16000},
}

VALID_PRESET_NAMES = tuple(BUILTIN_PRESETS.keys()) + ("custom",)
VALID_EQUALIZER_TYPES = ["q", "lowshelf", "highshelf", "lowpass", "highpass"]


def clamp_value(name: str, value):
    if name == "equalizer_type":
        if value not in VALID_EQUALIZER_TYPES:
            return "q"
        return value
    r = PARAM_RANGES.get(name)
    if r is None:
        return value
    if "min" in r and "max" in r:
        if isinstance(value, float) and name in ("highpass_freq", "afftdn_noise_floor", "anlmdn_strength", "acompressor_threshold", "equalizer_freq", "equalizer_gain", "lowpass_freq"):
            value = round(value)
        if value < r["min"]:
            return r["min"]
        if value > r["max"]:
            return r["max"]
    return value


def clamp_params(params: FilterParams) -> FilterParams:
    for f in dataclasses.fields(params):
        if f.name == "equalizer_type":
            continue
        v = getattr(params, f.name)
        setattr(params, f.name, clamp_value(f.name, v))
    if params.equalizer_type not in VALID_EQUALIZER_TYPES:
        params.equalizer_type = "q"
    return params


def validate_params(params: FilterParams) -> list[str]:
    warnings = []
    for f in dataclasses.fields(params):
        v = getattr(params, f.name)
        clamped = clamp_value(f.name, v)
        if v != clamped:
            warnings.append(f"{f.name}={v} clamped to {clamped}")
            setattr(params, f.name, clamped)
    return warnings


def _format_number(v) -> str:
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def build_filter_string(params: FilterParams) -> str:
    return (
        f"highpass=f={params.highpass_freq},"
        f"afftdn=nf={params.afftdn_noise_floor},"
        f"anlmdn=s={params.anlmdn_strength}:p={_format_number(params.anlmdn_power)},"
        f"acompressor=threshold={params.acompressor_threshold}dB:ratio={_format_number(params.acompressor_ratio)},"
        f"equalizer=f={params.equalizer_freq}:t={params.equalizer_type}:w={_format_number(params.equalizer_width)}:g={params.equalizer_gain},"
        f"lowpass=f={params.lowpass_freq}"
    )


def merge_preset(preset_name: str, overrides: Optional[dict] = None) -> FilterParams:
    if preset_name == "custom":
        base = FilterParams()
    else:
        base = FilterParams(**{f.name: getattr(BUILTIN_PRESETS[preset_name], f.name) for f in dataclasses.fields(FilterParams)})
    if overrides:
        for k, v in overrides.items():
            if v is not None and hasattr(base, k):
                setattr(base, k, v)
    clamp_params(base)
    return base
