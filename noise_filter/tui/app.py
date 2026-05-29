import threading
from pathlib import Path

from textual.app import App
from textual.screen import Screen
from textual.widgets import Button, Label, Input, ProgressBar

from ..presets import FilterParams, BUILTIN_PRESETS, build_filter_string, clamp_params
from ..config import load_config
from ..subprocess import run_enhance
from .screens import InputScreen, FilterScreen, RunScreen

PARAM_NAMES = (
    "highpass_freq", "afftdn_noise_floor", "anlmdn_strength", "anlmdn_power",
    "acompressor_threshold", "acompressor_ratio", "equalizer_freq",
    "equalizer_type", "equalizer_width", "equalizer_gain", "lowpass_freq",
)


class NoiseFilterApp(App):
    CSS = """
    #input-container { height: 1fr; padding: 1; }
    #sliders { height: auto; padding: 1; border: solid $primary; margin-top: 1; }
    .slider-row { height: 3; margin-bottom: 1; }
    .slider-label { width: 28; padding-top: 1; }
    .slider-input { width: 10; }
    #filter-preview { height: 3; padding: 1; border: solid $accent; margin-top: 1; }
    #filter-preview-label { text-style: bold; }
    #filter-preview-string { color: $text-secondary; }
    #progress-area { height: auto; padding: 1; margin-top: 1; }
    #run-button { width: 20; }
    #status-text { margin-top: 1; }
    #input-path { margin-bottom: 1; }
    #nav-buttons { height: auto; padding: 1; }
    #output-dir-label { margin-top: 1; }
    """

    def get_default_screen(self) -> InputScreen:
        return InputScreen()

    @property
    def default_screen(self) -> Screen:
        return self.screen

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.input_file = ""
        self.output_dir = ""
        self.current_preset = self.config["defaults"].get("selected_preset", "medium")
        self.filter_overrides: dict[str, str] = {}

    def update_preview(self):
        try:
            fs = build_filter_string(self._resolve_params())
            self.query_one("#filter-preview-string", Label).update(fs)
        except Exception:
            pass

    def _resolve_params(self) -> FilterParams:
        preset_name = self.current_preset
        overrides = {}
        for fname in PARAM_NAMES:
            val = self.filter_overrides.get(fname, "").strip()
            if val:
                try:
                    if fname in ("anlmdn_power", "acompressor_ratio", "equalizer_width"):
                        overrides[fname] = float(val)
                    elif fname == "equalizer_type":
                        overrides[fname] = val
                    else:
                        overrides[fname] = int(val)
                except ValueError:
                    pass

        if preset_name == "custom":
            merged = dict(self.config.get("override", {}))
            merged.update(overrides)
            base = FilterParams()
            for k, v in merged.items():
                if v is not None and hasattr(base, k):
                    setattr(base, k, v)
        else:
            base = FilterParams(
                **{f.name: getattr(BUILTIN_PRESETS[preset_name], f.name)
                   for f in FilterParams.__dataclass_fields__.values()}
            )
            for k, v in overrides.items():
                if v is not None and hasattr(base, k):
                    setattr(base, k, v)
        clamp_params(base)
        return base

    def run_processing(self):
        input_path = self.input_file.strip()
        if not input_path:
            try:
                self.query_one("#status-text", Label).update("Please specify an input file path.")
            except Exception:
                pass
            return
        inp = Path(input_path).expanduser()
        if not inp.exists():
            try:
                self.query_one("#status-text", Label).update(f"Input file not found: {input_path}")
            except Exception:
                pass
            return

        out_dir = self.output_dir.strip()
        output_dir = Path(out_dir).expanduser() if out_dir else None
        filter_string = build_filter_string(self._resolve_params())
        status = self.query_one("#status-text", Label)
        progress = self.query_one("#progress-bar", ProgressBar)
        run_btn = self.query_one("#run-button", Button)

        run_btn.disabled = True
        status.update("Processing...")

        def worker():
            try:
                result = run_enhance(inp, filter_string, output_dir)
                self.call_from_thread(lambda: status.update(f"Done! Output: {result['output']}"))
                self.call_from_thread(lambda: setattr(progress, 'progress', 100))
            except Exception as e:
                self.call_from_thread(lambda: status.update(f"Error: {e}"))
            finally:
                self.call_from_thread(lambda: setattr(run_btn, 'disabled', False))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
