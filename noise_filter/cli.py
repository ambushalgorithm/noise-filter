import sys
from pathlib import Path
from typing import Optional

import click

from .config import load_config
from .presets import merge_preset, build_filter_string, VALID_PRESET_NAMES
from .subprocess import run_enhance


@click.command()
@click.argument("input", required=False, default=None)
@click.option("--preset", "-p", default="medium", show_default=True,
              type=click.Choice(["light", "medium", "heavy", "custom"]),
              help="Preset profile")
@click.option("--highpass-freq", type=int, default=None, help="Highpass cutoff frequency in Hz")
@click.option("--afftdn-noise-floor", type=int, default=None, help="AFFTDN noise floor in dB")
@click.option("--anlmdn-strength", type=int, default=None, help="ANLMDN strength")
@click.option("--anlmdn-power", type=float, default=None, help="ANLMDN power")
@click.option("--acompressor-threshold", type=int, default=None, help="Compressor threshold in dB")
@click.option("--acompressor-ratio", type=float, default=None, help="Compressor ratio")
@click.option("--equalizer-freq", type=int, default=None, help="EQ center frequency in Hz")
@click.option("--equalizer-type", type=str, default=None, help="EQ filter type")
@click.option("--equalizer-width", type=float, default=None, help="EQ Q factor width")
@click.option("--equalizer-gain", type=int, default=None, help="EQ gain in dB")
@click.option("--lowpass-freq", type=int, default=None, help="Lowpass cutoff frequency in Hz")
@click.option("--output-dir", "-o", type=str, default=None, help="Output directory")
@click.option("--tui", is_flag=True, default=False, help="Launch Textual TUI")
def main(input, preset, highpass_freq, afftdn_noise_floor, anlmdn_strength,
         anlmdn_power, acompressor_threshold, acompressor_ratio,
         equalizer_freq, equalizer_type, equalizer_width, equalizer_gain,
         lowpass_freq, output_dir, tui):
    if tui:
        launch_tui()
        return

    if input is None:
        click.echo("Error: INPUT argument is required (or use --tui to launch TUI)", err=True)
        raise SystemExit(1)

    config = load_config()

    overrides = {}
    override_map = {
        "highpass_freq": highpass_freq,
        "afftdn_noise_floor": afftdn_noise_floor,
        "anlmdn_strength": anlmdn_strength,
        "anlmdn_power": anlmdn_power,
        "acompressor_threshold": acompressor_threshold,
        "acompressor_ratio": acompressor_ratio,
        "equalizer_freq": equalizer_freq,
        "equalizer_type": equalizer_type,
        "equalizer_width": equalizer_width,
        "equalizer_gain": equalizer_gain,
        "lowpass_freq": lowpass_freq,
    }
    for k, v in override_map.items():
        if v is not None:
            overrides[k] = v

    if preset == "custom":
        cfg_overrides = config.get("override", {})
        merged = {k: v for k, v in cfg_overrides.items() if v is not None}
        merged.update(overrides)
        params = merge_preset("custom", merged)
    else:
        params = merge_preset(preset, overrides if overrides else None)

    filter_string = build_filter_string(params)
    out_path = Path(output_dir) if output_dir else None
    input_path = Path(input).expanduser().resolve()

    result = run_enhance(input_path, filter_string, out_path)
    click.echo(f"Enhanced output: {result['output']}")
    if result.get('vocals_stem'):
        click.echo(f"Vocals stem: {result['vocals_stem']}")
    if result.get('instrumental_stem'):
        click.echo(f"Instrumental stem: {result['instrumental_stem']}")


def launch_tui():
    from .tui.app import NoiseFilterApp
    NoiseFilterApp().run()
