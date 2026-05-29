import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from noise_filter.cli import main
from noise_filter.presets import (
    FilterParams,
    BUILTIN_PRESETS,
    build_filter_string,
    merge_preset,
)

runner = CliRunner()


class TestE2ECLIPresets:
    LIGHT_EXPECTED = "highpass=f=80,afftdn=nf=-20,anlmdn=s=3:p=0.001,acompressor=threshold=-12dB:ratio=2,equalizer=f=3000:t=q:w=1:g=2,lowpass=f=12000"
    MEDIUM_EXPECTED = "highpass=f=120,afftdn=nf=-30,anlmdn=s=7:p=0.002,acompressor=threshold=-18dB:ratio=3,equalizer=f=3000:t=q:w=1:g=4,lowpass=f=9000"
    HEAVY_EXPECTED = "highpass=f=200,afftdn=nf=-50,anlmdn=s=12:p=0.005,acompressor=threshold=-24dB:ratio=6,equalizer=f=2500:t=q:w=1.5:g=6,lowpass=f=7000"

    def test_light_preset_exact_filter_string(self):
        p = BUILTIN_PRESETS["light"]
        assert build_filter_string(p) == self.LIGHT_EXPECTED

    def test_medium_preset_exact_filter_string(self):
        p = BUILTIN_PRESETS["medium"]
        assert build_filter_string(p) == self.MEDIUM_EXPECTED

    def test_heavy_preset_exact_filter_string(self):
        p = BUILTIN_PRESETS["heavy"]
        assert build_filter_string(p) == self.HEAVY_EXPECTED

    def test_per_filter_override_merges_correctly(self):
        p = merge_preset("medium", {"highpass_freq": 150, "equalizer_gain": 5})
        assert p.highpass_freq == 150
        assert p.equalizer_gain == 5
        assert p.afftdn_noise_floor == -30
        assert p.lowpass_freq == 9000

    def test_partial_override_inherits_rest_from_preset(self):
        p = merge_preset("heavy", {"highpass_freq": 180})
        assert p.highpass_freq == 180
        assert p.equalizer_gain == 6
        assert p.afftdn_noise_floor == -50
        assert p.anlmdn_strength == 12

    def test_custom_preset_empty_override_falls_back_to_medium(self):
        p = merge_preset("custom")
        assert p.highpass_freq == 120
        assert p.equalizer_gain == 4

    def test_custom_preset_with_override(self):
        p = merge_preset("custom", {"highpass_freq": 150, "lowpass_freq": 10000})
        assert p.highpass_freq == 150
        assert p.lowpass_freq == 10000
        assert p.equalizer_gain == 4

    def test_cli_flag_overrides_config_value(self, tmp_path: Path):
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
            result = runner.invoke(main, [str(input_file), "--highpass-freq", "100"])
        assert result.exit_code == 0

    def test_filter_order_is_always_correct(self):
        for name in ("light", "medium", "heavy"):
            s = build_filter_string(BUILTIN_PRESETS[name])
            parts = [p.split("=")[0] for p in s.split(",")]
            expected = ["highpass", "afftdn", "anlmdn", "acompressor", "equalizer", "lowpass"]
            assert parts == expected, f"{name}: order mismatch"

    def test_all_six_filters_present_in_string(self):
        for name in ("light", "medium", "heavy"):
            s = build_filter_string(BUILTIN_PRESETS[name])
            for fname in ("highpass", "afftdn", "anlmdn", "acompressor", "equalizer", "lowpass"):
                assert fname in s, f"{name} missing {fname}"

    def test_filter_string_ffmpeg_syntax_colon_separated(self):
        import re
        for name in ("light", "medium", "heavy"):
            s = build_filter_string(BUILTIN_PRESETS[name])
            filters = s.split(",")
            assert len(filters) == 6
            for f in filters:
                assert "=" in f, f"Missing = in filter: {f}"
                parts = f.split("=", 1)
                assert len(parts[1]) > 0, f"Empty value in {f}"
            assert re.search(r"highpass=f=\d+", s)
            assert re.search(r"afftdn=nf=-?\d+", s)
            assert re.search(r"anlmdn=s=\d+:p=[\d.]+", s)
            assert re.search(r"acompressor=threshold=-?\d+dB:ratio=[\d.]+", s)
            assert re.search(r"equalizer=f=\d+:t=\w+:w=[\d.]+:g=-?\d+", s)
            assert re.search(r"lowpass=f=\d+", s)

    def test_override_clamping_prevents_invalid_values(self):
        p = merge_preset("medium", {"highpass_freq": 999, "lowpass_freq": 50})
        assert p.highpass_freq == 300
        assert p.lowpass_freq == 4000

    def test_cli_invocation_successful_with_mock_subprocess(self, tmp_path: Path):
        input_file = tmp_path / "test.wav"
        input_file.write_text("dummy")
        with patch("noise_filter.cli.run_enhance") as mock_run:
            mock_run.return_value = {"output": str(tmp_path / "output_VOICE_ENHANCED_01.wav")}
            result = runner.invoke(main, [str(input_file), "--preset", "light"])
        assert result.exit_code == 0
        assert "Enhanced output" in result.output

    def test_heavy_preset_params_via_cli(self, tmp_path: Path):
        input_file = tmp_path / "input.wav"
        input_file.write_text("dummy")
        with patch("noise_filter.cli.run_enhance") as mock_run:
            mock_run.return_value = {"output": str(tmp_path / "output.wav")}
            result = runner.invoke(main, [str(input_file), "--preset", "heavy"])
        assert result.exit_code == 0

    def test_custom_preset_with_cli_flags(self, tmp_path: Path):
        input_file = tmp_path / "input.wav"
        input_file.write_text("dummy")
        with (
            patch("noise_filter.cli.run_enhance") as mock_run,
        ):
            mock_run.return_value = {"output": str(tmp_path / "output.wav")}
            result = runner.invoke(main, [
                str(input_file), "--preset", "custom",
                "--highpass-freq", "150", "--equalizer-gain", "5",
            ])
        assert result.exit_code == 0

    def test_output_naming_increments_correctly(self, tmp_path: Path):
        stem = "test_VOICE_ENHANCED"
        from noise_filter.subprocess import next_output_path
        p1 = next_output_path(tmp_path, stem, "wav")
        assert p1.name == "test_VOICE_ENHANCED_01.wav"
        p1.write_text("1")
        p2 = next_output_path(tmp_path, stem, "wav")
        assert p2.name == "test_VOICE_ENHANCED_02.wav"
        p2.write_text("2")
        p3 = next_output_path(tmp_path, stem, "wav")
        assert p3.name == "test_VOICE_ENHANCED_03.wav"

    def test_run_enhance_returns_output_with_stems(self, tmp_path: Path):
        input_file = tmp_path / "input.wav"
        input_file.write_text("dummy")
        from noise_filter.subprocess import run_enhance
        with (
            patch("noise_filter.subprocess.shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("noise_filter.subprocess.find_audio_separator", return_value="/usr/bin/audio-separator"),
            patch("noise_filter.subprocess.subprocess.run") as mock_run,
            patch("noise_filter.subprocess.shutil.copy2"),
            patch("noise_filter.subprocess.tempfile.mkdtemp", return_value=str(tmp_path / "temp")),
        ):
            (tmp_path / "temp").mkdir(exist_ok=True)
            vocals_file = tmp_path / "temp" / "input_(Vocals).wav"
            vocals_file.write_text("vocals")
            instr_file = tmp_path / "temp" / "input_(Instrumental).wav"
            instr_file.write_text("instr")

            def fake_run(args, **kwargs):
                from subprocess import CompletedProcess
                if "ffprobe" in str(args):
                    return CompletedProcess(args, 0, stdout="1\n", stderr="")
                return CompletedProcess(args, 0, stdout="", stderr="")

            mock_run.side_effect = fake_run
            result = run_enhance(input_file, "highpass=f=120", tmp_path)
        assert "output" in result
        assert "vocals_stem" in result
        assert "instrumental_stem" in result

    def test_cli_rejects_invalid_preset_name(self):
        result = runner.invoke(main, ["input.wav", "--preset", "bogus"])
        assert result.exit_code != 0
        assert "bogus" in result.output.lower()

    def test_cli_requires_input_argument(self):
        result = runner.invoke(main, ["--preset", "light"])
        assert result.exit_code != 0
        assert "INPUT" in result.output


class TestE2EFix001TildeExpansion:
    def test_cli_expands_tilde_in_input_path(self, tmp_path: Path):
        with patch("noise_filter.cli.run_enhance") as mock_run:
            mock_run.return_value = {"output": str(tmp_path / "output_01.wav")}
            result = runner.invoke(main, ["~/test.wav"])
        assert result.exit_code == 0
        args, _ = mock_run.call_args
        input_path_arg = args[0]
        assert "~" not in str(input_path_arg)
        assert Path(input_path_arg).is_absolute()

    def test_expanded_path_resolves_to_absolute(self, tmp_path: Path):
        from pathlib import Path as P
        expanded = P("~/test.wav").expanduser()
        assert expanded.is_absolute()
        assert "~" not in str(expanded)

    def test_subprocess_expands_tilde_in_input_path(self, tmp_path: Path):
        from noise_filter.subprocess import run_enhance
        input_file = tmp_path / "test.wav"
        input_file.write_text("dummy")
        with (
            patch("noise_filter.subprocess.shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("noise_filter.subprocess.find_audio_separator", return_value="/usr/bin/audio-separator"),
            patch("noise_filter.subprocess.subprocess.run") as mock_run,
            patch("noise_filter.subprocess.shutil.copy2"),
            patch("noise_filter.subprocess.tempfile.mkdtemp", return_value=str(tmp_path / "temp")),
            patch.dict("os.environ", {"HOME": str(tmp_path)}),
        ):
            (tmp_path / "temp").mkdir(exist_ok=True)
            (tmp_path / "temp" / "test_(Vocals).wav").write_text("vocals")
            (tmp_path / "temp" / "test_(Instrumental).wav").write_text("instr")

            def fake_run(args, **kwargs):
                from subprocess import CompletedProcess
                cmd = str(args)
                if "ffprobe" in cmd and "v:0" in cmd:
                    return CompletedProcess(args, 0, stdout="", stderr="")
                if "ffprobe" in cmd and "a:0" in cmd:
                    return CompletedProcess(args, 0, stdout="1\n", stderr="")
                return CompletedProcess(args, 0, stdout="", stderr="")

            mock_run.side_effect = fake_run
            result = run_enhance(Path("~/test.wav"), "highpass=f=120", tmp_path)
        assert "output" in result
        assert "test_VOICE_ENHANCED" in str(result["output"])

    def test_cli_outputs_all_three_paths(self, tmp_path: Path):
        input_file = tmp_path / "test.wav"
        input_file.write_text("dummy")
        with patch("noise_filter.cli.run_enhance") as mock_run:
            mock_run.return_value = {
                "output": str(tmp_path / "output_01.wav"),
                "vocals_stem": str(tmp_path / "test_VOCALS_01.wav"),
                "instrumental_stem": str(tmp_path / "test_INSTRUMENTALS_01.wav"),
            }
            result = runner.invoke(main, [str(input_file)])
        assert result.exit_code == 0
        assert "Enhanced output" in result.output
        assert "Vocals stem" in result.output
        assert "Instrumental stem" in result.output


class TestE2EFix002FilenamePrefix:
    def test_video_input_uses_basename_for_temp_audio(self, tmp_path: Path):
        from noise_filter.subprocess import run_enhance
        input_file = tmp_path / "my_video.mkv"
        input_file.write_text("dummy")
        with (
            patch("noise_filter.subprocess.shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("noise_filter.subprocess.find_audio_separator", return_value="/usr/bin/audio-separator"),
            patch("noise_filter.subprocess.subprocess.run") as mock_run,
            patch("noise_filter.subprocess.shutil.copy2"),
            patch("noise_filter.subprocess.tempfile.mkdtemp", return_value=str(tmp_path / "temp")),
        ):
            (tmp_path / "temp").mkdir(exist_ok=True)
            (tmp_path / "temp" / "my_video_(Vocals).wav").write_text("vocals")
            (tmp_path / "temp" / "my_video_(Instrumental).wav").write_text("instr")

            def fake_run(args, **kwargs):
                from subprocess import CompletedProcess
                cmd = str(args)
                if "ffprobe" in cmd and "v:0" in cmd:
                    return CompletedProcess(args, 0, stdout="1\n", stderr="")
                if "ffprobe" in cmd and "a:0" in cmd:
                    return CompletedProcess(args, 0, stdout="1\n", stderr="")
                return CompletedProcess(args, 0, stdout="", stderr="")

            mock_run.side_effect = fake_run
            result = run_enhance(input_file, "highpass=f=120", tmp_path)
        assert "output" in result
        assert "my_video_VOICE_ENHANCED" in result["output"]
        assert "my_video" in result["vocals_stem"]

    def test_audio_separator_receives_basename_named_file_for_video(self, tmp_path: Path):
        from noise_filter.subprocess import run_enhance
        input_file = tmp_path / "sample.mkv"
        input_file.write_text("dummy")
        separator_called_with = []

        with (
            patch("noise_filter.subprocess.shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("noise_filter.subprocess.find_audio_separator", return_value="/usr/bin/audio-separator"),
            patch("noise_filter.subprocess.subprocess.run") as mock_run,
            patch("noise_filter.subprocess.shutil.copy2"),
            patch("noise_filter.subprocess.tempfile.mkdtemp", return_value=str(tmp_path / "temp")),
        ):
            (tmp_path / "temp").mkdir(exist_ok=True)
            (tmp_path / "temp" / "sample_(Vocals).wav").write_text("vocals")
            (tmp_path / "temp" / "sample_(Instrumental).wav").write_text("instr")

            def fake_run(args, **kwargs):
                from subprocess import CompletedProcess
                cmd = str(args)
                if "audio-separator" in cmd:
                    separator_called_with.append(args)
                if "ffprobe" in cmd and "v:0" in cmd:
                    return CompletedProcess(args, 0, stdout="1\n", stderr="")
                if "ffprobe" in cmd and "a:0" in cmd:
                    return CompletedProcess(args, 0, stdout="1\n", stderr="")
                return CompletedProcess(args, 0, stdout="", stderr="")

            mock_run.side_effect = fake_run
            run_enhance(input_file, "highpass=f=120", tmp_path)
        assert len(separator_called_with) == 1
        sep_args = separator_called_with[0]
        sep_input = [a for a in sep_args if "sample.wav" in str(a)]
        assert len(sep_input) > 0, f"audio-separator should receive sample.wav, got {sep_args}"

    def test_stem_output_contains_original_filename(self, tmp_path: Path):
        from noise_filter.subprocess import run_enhance
        input_file = tmp_path / "original_name.mkv"
        input_file.write_text("dummy")
        with (
            patch("noise_filter.subprocess.shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("noise_filter.subprocess.find_audio_separator", return_value="/usr/bin/audio-separator"),
            patch("noise_filter.subprocess.subprocess.run") as mock_run,
            patch("noise_filter.subprocess.shutil.copy2"),
            patch("noise_filter.subprocess.tempfile.mkdtemp", return_value=str(tmp_path / "temp")),
        ):
            (tmp_path / "temp").mkdir(exist_ok=True)
            (tmp_path / "temp" / "original_name_(Vocals).wav").write_text("vocals")
            (tmp_path / "temp" / "original_name_(Instrumental).wav").write_text("instr")

            def fake_run(args, **kwargs):
                from subprocess import CompletedProcess
                cmd = str(args)
                if "ffprobe" in cmd and "v:0" in cmd:
                    return CompletedProcess(args, 0, stdout="1\n", stderr="")
                if "ffprobe" in cmd and "a:0" in cmd:
                    return CompletedProcess(args, 0, stdout="1\n", stderr="")
                return CompletedProcess(args, 0, stdout="", stderr="")

            mock_run.side_effect = fake_run
            result = run_enhance(input_file, "highpass=f=120", tmp_path)
        # The copied stems should retain the original filename prefix
        assert "original_name" in result["vocals_stem"]
        assert "original_name" in result["instrumental_stem"]

    def test_audio_input_preserves_filename_prefix(self, tmp_path: Path):
        from noise_filter.subprocess import run_enhance
        input_file = tmp_path / "recording.wav"
        input_file.write_text("dummy")
        with (
            patch("noise_filter.subprocess.shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("noise_filter.subprocess.find_audio_separator", return_value="/usr/bin/audio-separator"),
            patch("noise_filter.subprocess.subprocess.run") as mock_run,
            patch("noise_filter.subprocess.shutil.copy2"),
            patch("noise_filter.subprocess.tempfile.mkdtemp", return_value=str(tmp_path / "temp")),
        ):
            (tmp_path / "temp").mkdir(exist_ok=True)
            (tmp_path / "temp" / "recording_(Vocals).wav").write_text("vocals")
            (tmp_path / "temp" / "recording_(Instrumental).wav").write_text("instr")

            def fake_run(args, **kwargs):
                from subprocess import CompletedProcess
                cmd = str(args)
                if "ffprobe" in cmd and "v:0" in cmd:
                    return CompletedProcess(args, 0, stdout="", stderr="")
                if "ffprobe" in cmd and "a:0" in cmd:
                    return CompletedProcess(args, 0, stdout="1\n", stderr="")
                return CompletedProcess(args, 0, stdout="", stderr="")

            mock_run.side_effect = fake_run
            result = run_enhance(input_file, "highpass=f=120", tmp_path)
        assert "recording_VOICE_ENHANCED" in result["output"]
        assert "recording" in result["vocals_stem"]
