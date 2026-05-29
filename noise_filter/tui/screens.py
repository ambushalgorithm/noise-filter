from textual.screen import Screen
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Select, Label, Input, ProgressBar, Header, Footer

from ..presets import VALID_PRESET_NAMES


class InputScreen(Screen):
    def compose(self):
        yield Header()
        with Vertical(id="input-container"):
            yield Input(placeholder="/path/to/input.wav (or video file)", id="input-path")
            yield Select(
                [(n.capitalize(), n) for n in VALID_PRESET_NAMES],
                prompt="Preset",
                id="preset-select",
                value="medium",
            )
            yield Label("Output directory (leave empty for same dir as input):", id="output-dir-label")
            yield Input(placeholder="", id="output-dir-input")
            yield Button("Next →", id="next-btn", variant="primary")
        yield Footer()

    def on_mount(self):
        app = self.app
        if app.input_file:
            self.query_one("#input-path", Input).value = app.input_file
        if app.output_dir:
            self.query_one("#output-dir-input", Input).value = app.output_dir
        if app.current_preset:
            self.query_one("#preset-select", Select).value = app.current_preset

    def on_input_changed(self, event: Input.Changed):
        eid = event.input.id
        if eid == "input-path":
            self.app.input_file = event.value
        elif eid == "output-dir-input":
            self.app.output_dir = event.value

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "preset-select":
            self.app.current_preset = event.value

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "next-btn":
            self.app.push_screen(FilterScreen())


class FilterScreen(Screen):
    def compose(self):
        yield Header()
        with Vertical(id="sliders"):
            yield Label("Per-Filter Parameters (empty = use preset default):")
            for fname, finfo in [
                ("highpass_freq", "Highpass Freq (Hz) [20-300]"),
                ("afftdn_noise_floor", "AFFTDN Noise Floor (dB) [-80..-10]"),
                ("anlmdn_strength", "ANLMDN Strength [1-15]"),
                ("anlmdn_power", "ANLMDN Power [0.001-0.100]"),
                ("acompressor_threshold", "AC Threshold (dB) [-60-0]"),
                ("acompressor_ratio", "AC Ratio [1-20]"),
                ("equalizer_freq", "EQ Freq (Hz) [20-20000]"),
                ("equalizer_type", "EQ Type (q/lowshelf/highshelf/lowpass/highpass)"),
                ("equalizer_width", "EQ Width (Q) [0.1-10.0]"),
                ("equalizer_gain", "EQ Gain (dB) [-20-20]"),
                ("lowpass_freq", "Lowpass Freq (Hz) [4000-16000]"),
            ]:
                with Horizontal(classes="slider-row"):
                    yield Label(finfo, classes="slider-label")
                    yield Input(placeholder="(preset default)", id=f"input-{fname}", classes="slider-input")
            with Horizontal(id="nav-buttons"):
                yield Button("← Back", id="back-btn", variant="default")
                yield Button("Next →", id="next-btn-2", variant="primary")
        yield Footer()

    def on_input_changed(self, event: Input.Changed):
        eid = event.input.id
        if eid and eid.startswith("input-"):
            fname = eid[len("input-"):]
            val = event.value.strip()
            if val:
                self.app.filter_overrides[fname] = val
            else:
                self.app.filter_overrides.pop(fname, None)
            self.app.update_preview()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "next-btn-2":
            self.app.push_screen(RunScreen())


class RunScreen(Screen):
    def compose(self):
        yield Header()
        with Vertical(id="run-container"):
            with Vertical(id="filter-preview"):
                yield Label("Filter Chain Preview:", id="filter-preview-label")
                yield Label("", id="filter-preview-string")
            with Horizontal(id="progress-area"):
                yield Button("Run", id="run-button", variant="primary")
                yield ProgressBar(total=100, id="progress-bar", show_eta=False)
            yield Label("", id="status-text")
            yield Button("← Back", id="back-btn-3", variant="default")
        yield Footer()

    def on_mount(self):
        self.app.update_preview()

    def on_show(self):
        self.app.update_preview()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "back-btn-3":
            self.app.pop_screen()
        elif event.button.id == "run-button":
            self.app.run_processing()
