from pathlib import Path
from unittest.mock import patch

import pytest

from noise_filter.tui.app import NoiseFilterApp
from noise_filter.tui.screens import InputScreen, FilterScreen, RunScreen
from noise_filter.presets import BUILTIN_PRESETS, FilterParams, build_filter_string


class TestE2ETUI:
    @pytest.mark.asyncio
    async def test_tui_launches_and_shows_preset_selector(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            preset_select = app.query_one("#preset-select")
            assert preset_select is not None
            assert str(preset_select.value).capitalize() in ["Medium", "Light", "Heavy", "Custom"]

    @pytest.mark.asyncio
    async def test_tui_shows_filter_preview_on_startup(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(RunScreen())
            await pilot.pause()
            preview = app.query_one("#filter-preview-string")
            text = preview.content
            assert "highpass" in text
            assert "afftdn" in text
            assert "anlmdn" in text
            assert "acompressor" in text
            assert "equalizer" in text
            assert "lowpass" in text

    @pytest.mark.asyncio
    async def test_preset_selector_updates_filter_preview(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            preset_select = app.query_one("#preset-select")
            preset_select.value = "light"
            await pilot.pause()
            app.push_screen(RunScreen())
            await pilot.pause()
            preview = app.query_one("#filter-preview-string")
            text = preview.content
            assert "highpass=f=80" in text
            assert "afftdn=nf=-20" in text

    @pytest.mark.asyncio
    async def test_heavy_preset_shows_correct_values_in_preview(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            preset_select = app.query_one("#preset-select")
            preset_select.value = "heavy"
            await pilot.pause()
            app.push_screen(RunScreen())
            await pilot.pause()
            preview = app.query_one("#filter-preview-string")
            text = preview.content
            assert "highpass=f=200" in text
            assert "afftdn=nf=-50" in text
            assert "anlmdn=s=12:p=0.005" in text
            assert "acompressor=threshold=-24dB:ratio=6" in text
            assert "equalizer=f=2500:t=q:w=1.5:g=6" in text
            assert "lowpass=f=7000" in text

    @pytest.mark.asyncio
    async def test_per_filter_input_updates_preview(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(FilterScreen())
            await pilot.pause()
            input_widget = app.query_one("#input-highpass_freq")
            input_widget.value = "200"
            await pilot.pause()
            app.push_screen(RunScreen())
            await pilot.pause()
            preview = app.query_one("#filter-preview-string")
            text = preview.content
            assert "highpass=f=200" in text

    @pytest.mark.asyncio
    async def test_run_button_exists(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(RunScreen())
            await pilot.pause()
            run_btn = app.query_one("#run-button")
            assert run_btn.label == "Run"

    @pytest.mark.asyncio
    async def test_tui_shows_all_slider_inputs(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(FilterScreen())
            await pilot.pause()
            for fname in [
                "highpass_freq", "afftdn_noise_floor", "anlmdn_strength",
                "anlmdn_power", "acompressor_threshold", "acompressor_ratio",
                "equalizer_freq", "equalizer_type", "equalizer_width",
                "equalizer_gain", "lowpass_freq",
            ]:
                w = app.query_one(f"#input-{fname}")
                assert w is not None, f"Missing input for {fname}"

    @pytest.mark.asyncio
    async def test_input_path_shown(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            inp = app.query_one("#input-path")
            assert inp is not None
            assert inp.placeholder == "/path/to/input.wav (or video file)"

    @pytest.mark.asyncio
    async def test_output_dir_input_exists(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            out = app.query_one("#output-dir-input")
            assert out is not None

    @pytest.mark.asyncio
    async def test_progress_bar_exists(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(RunScreen())
            await pilot.pause()
            pb = app.query_one("#progress-bar")
            assert pb is not None

    @pytest.mark.asyncio
    async def test_status_text_shown(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(RunScreen())
            await pilot.pause()
            st = app.query_one("#status-text")
            assert st is not None

    @pytest.mark.asyncio
    async def test_filter_preview_label_exists(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(RunScreen())
            await pilot.pause()
            lbl = app.query_one("#filter-preview-label")
            assert lbl is not None

    @pytest.mark.asyncio
    async def test_switch_presets_and_verify_preview_changes(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            ps = app.query_one("#preset-select")
            ps.value = "light"
            await pilot.pause()
            app.push_screen(RunScreen())
            await pilot.pause()
            text1 = app.query_one("#filter-preview-string").content
            app.pop_screen()
            await pilot.pause()
            ps = app.query_one("#preset-select")
            ps.value = "heavy"
            await pilot.pause()
            app.push_screen(RunScreen())
            await pilot.pause()
            text2 = app.query_one("#filter-preview-string").content
            assert text1 != text2
            assert "highpass=f=80" in text1
            assert "highpass=f=200" in text2

    @pytest.mark.asyncio
    async def test_custom_preset_shows_medium_fallback(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            ps = app.query_one("#preset-select")
            ps.value = "custom"
            await pilot.pause()
            app.push_screen(RunScreen())
            await pilot.pause()
            text = app.query_one("#filter-preview-string").content
            assert "highpass=f=120" in text

    @pytest.mark.asyncio
    async def test_user_input_overrides_preset_in_preview(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(FilterScreen())
            await pilot.pause()
            inp = app.query_one("#input-highpass_freq")
            inp.value = "180"
            await pilot.pause()
            app.push_screen(RunScreen())
            await pilot.pause()
            text = app.query_one("#filter-preview-string").content
            assert "highpass=f=180" in text
            assert "afftdn=nf=-30" in text

    @pytest.mark.asyncio
    async def test_run_button_triggers_status_update(self, tmp_path: Path):
        input_file = tmp_path / "test.wav"
        input_file.write_text("dummy")
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.input_file = str(input_file)
            app.query_one("#input-path").value = str(input_file)
            app.push_screen(RunScreen())
            await pilot.pause()
            with patch("noise_filter.tui.app.run_enhance") as mock_run:
                mock_run.return_value = {"output": str(tmp_path / "output_01.wav")}
                run_btn = app.query_one("#run-button")
                run_btn.press()
                await pilot.pause()
                status = app.query_one("#status-text")
                stext = status.content
                assert "Done" in stext or "Error" in stext or "Processing" in stext

    @pytest.mark.asyncio
    async def test_anlmdn_power_input_accepts_float(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(FilterScreen())
            await pilot.pause()
            inp = app.query_one("#input-anlmdn_power")
            inp.value = "0.005"
            await pilot.pause()
            app.push_screen(RunScreen())
            await pilot.pause()
            text = app.query_one("#filter-preview-string").content
            assert "anlmdn" in text

    @pytest.mark.asyncio
    async def test_equalizer_type_input_accepts_string(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(FilterScreen())
            await pilot.pause()
            inp = app.query_one("#input-equalizer_type")
            inp.value = "highshelf"
            await pilot.pause()
            app.push_screen(RunScreen())
            await pilot.pause()
            text = app.query_one("#filter-preview-string").content
            assert "equalizer" in text


class TestE2EFix003MultiScreenTUI:
    @pytest.mark.asyncio
    async def test_input_screen_renders(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, InputScreen)
            assert app.query_one("#input-path") is not None
            assert app.query_one("#preset-select") is not None
            assert app.query_one("#next-btn") is not None

    @pytest.mark.asyncio
    async def test_navigate_input_to_filter_screen(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            next_btn = app.query_one("#next-btn")
            next_btn.press()
            await pilot.pause()
            assert isinstance(app.screen, FilterScreen)

    @pytest.mark.asyncio
    async def test_navigate_filter_to_run_screen(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(FilterScreen())
            await pilot.pause()
            assert isinstance(app.screen, FilterScreen)
            next_btn = app.query_one("#next-btn-2")
            next_btn.press()
            await pilot.pause()
            assert isinstance(app.screen, RunScreen)

    @pytest.mark.asyncio
    async def test_navigate_back_filter_to_input_screen(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(FilterScreen())
            await pilot.pause()
            assert isinstance(app.screen, FilterScreen)
            back_btn = app.query_one("#back-btn")
            back_btn.press()
            await pilot.pause()
            assert isinstance(app.screen, InputScreen)

    @pytest.mark.asyncio
    async def test_navigate_back_run_to_filter_screen(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(FilterScreen())
            await pilot.pause()
            app.push_screen(RunScreen())
            await pilot.pause()
            assert isinstance(app.screen, RunScreen)
            back_btn = app.query_one("#back-btn-3")
            back_btn.press()
            await pilot.pause()
            assert isinstance(app.screen, FilterScreen)

    @pytest.mark.asyncio
    async def test_full_forward_navigation_all_screens(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, InputScreen)
            app.query_one("#next-btn").press()
            await pilot.pause()
            assert isinstance(app.screen, FilterScreen)
            app.query_one("#next-btn-2").press()
            await pilot.pause()
            assert isinstance(app.screen, RunScreen)

    @pytest.mark.asyncio
    async def test_full_backward_navigation_all_screens(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.query_one("#next-btn").press()
            await pilot.pause()
            assert isinstance(app.screen, FilterScreen)
            app.query_one("#next-btn-2").press()
            await pilot.pause()
            assert isinstance(app.screen, RunScreen)
            app.query_one("#back-btn-3").press()
            await pilot.pause()
            assert isinstance(app.screen, FilterScreen)
            app.query_one("#back-btn").press()
            await pilot.pause()
            assert isinstance(app.screen, InputScreen)

    @pytest.mark.asyncio
    async def test_filter_screen_renders_all_widgets(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(FilterScreen())
            await pilot.pause()
            assert app.query_one("#input-highpass_freq") is not None
            assert app.query_one("#input-lowpass_freq") is not None
            assert app.query_one("#back-btn") is not None
            assert app.query_one("#next-btn-2") is not None

    @pytest.mark.asyncio
    async def test_run_screen_renders_all_widgets(self):
        app = NoiseFilterApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(RunScreen())
            await pilot.pause()
            assert app.query_one("#run-button") is not None
            assert app.query_one("#filter-preview-string") is not None
            assert app.query_one("#back-btn-3") is not None
